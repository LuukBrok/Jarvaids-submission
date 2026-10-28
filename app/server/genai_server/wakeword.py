"""Ephemeral F2.5 detection. No audio, commands or detections enter SQLite."""
import base64
from dataclasses import dataclass, field
import hashlib
import json
import math
from pathlib import Path
import secrets
import threading
import time

from .validation import Problem, fields, ident, integer, require


BATCH_BYTES = 10240  # 320 ms, 16 kHz, signed little-endian PCM16, mono.


def create_engine(assets):
    """Construct the optional engine with explicit offline feature assets."""
    from openwakeword.model import Model
    return Model(wakeword_models=[assets['keyword']], inference_framework='onnx',
                 melspec_model_path=assets['melspectrogram'],
                 embedding_model_path=assets['embedding'])


class LocalDetector:
    """All three assets are explicit, hash-checked local files; never download."""

    def __init__(self, manifest_path):
        try:
            from importlib.metadata import version
            import numpy as np
            if version('openwakeword') != '0.6.0':
                raise ValueError('Unsupported runtime')
            path = Path(manifest_path).resolve()
            manifest = json.loads(path.read_text(encoding='utf-8'))
            if manifest['phrase'] != 'Hey Jarvaids' or manifest['pronunciation'] != 'Hey Jar-vaydz':
                raise ValueError('Wrong phrase')
            if manifest['engine_version'] != '0.6.0':
                raise ValueError('Wrong engine')
            assets = {}
            for key in ('keyword', 'melspectrogram', 'embedding'):
                entry = manifest['assets'][key]
                asset = (path.parent / entry['file']).resolve()
                if not asset.is_relative_to(path.parent) or asset.suffix != '.onnx':
                    raise ValueError('Invalid asset path')
                if not entry['licence'] or not entry['source']:
                    raise ValueError('Missing provenance')
                if hashlib.sha256(asset.read_bytes()).hexdigest() != entry['sha256']:
                    raise ValueError('Asset checksum mismatch')
                assets[key] = str(asset)
            self.model = create_engine(assets)
            self.key = Path(assets['keyword']).stem
            self.np = np
            # Exercise decoding and inference now, not after microphone activation.
            self.predict(bytes(BATCH_BYTES))
            self.model.reset()
        except Exception:
            raise Problem(503, 'wakeword_unavailable',
                          'Custom wake-word model unavailable. Check local model setup.') from None

    def predict(self, raw):
        samples = self.np.frombuffer(raw, dtype='<i2').astype(self.np.int16, copy=False)
        # This candidate model scored quiet fan-like noise above 0.99 on the
        # user's PC. Never normalise that noise into a wake-word event.
        level = math.sqrt(sum(float(v) * float(v) for v in samples) / len(samples))
        if level < 180:
            self.model.reset()
            return 0.0
        return max(float(self.model.predict(samples[i:i + 1280])[self.key])
                   for i in range(0, len(samples), 1280))


@dataclass
class Stream:
    id: str
    owner: str
    authority: tuple
    touched: float
    detector: object = None
    next_sequence: int = 0
    previous_hash: str = ''
    previous_result: dict = field(default_factory=dict)
    last_detection: float = float('-inf')
    busy: bool = False


class WakewordStreams:
    """Never call database code while holding this registry's lock.

    Lifecycle operations can revoke a stream during inference. Occupied inference
    slots remain occupied until the call returns, even if its stream is revoked.
    """
    MAX_STREAMS = 4
    IDLE_SECONDS = 5
    COOLDOWN_SECONDS = 3

    def __init__(self, factory=None, clock=time.monotonic, threshold=0.5):
        if not math.isfinite(threshold) or not 0 < threshold <= 1:
            raise ValueError('Wake-word threshold must be in (0, 1].')
        self.factory = factory
        self.clock = clock
        self.threshold = threshold
        self.lock = threading.RLock()
        self.streams = {}
        self.slots = threading.BoundedSemaphore(self.MAX_STREAMS)

    def expire(self):
        with self.lock:
            for sid, stream in list(self.streams.items()):
                if self.clock() - stream.touched >= self.IDLE_SECONDS:
                    del self.streams[sid]

    def invalidate(self, sid, owner=None):
        with self.lock:
            stream = self.streams.get(sid)
            if stream and (owner is None or stream.owner == owner):
                del self.streams[sid]

    def _current(self, sid, stream):
        self.expire()
        require(self.streams.get(sid) is stream, 'wakeword_stopped',
                'Detection stopped. Start a fresh stream explicitly.', 409)

    def start(self, sid, authority, authorize):
        require(self.factory is not None, 'wakeword_unavailable',
                'Wake-word detection is not configured; meeting capture remains available.', 503)
        with self.lock:
            self.expire()
            require(sid not in self.streams, 'wakeword_busy', 'This session already has a microphone stream.', 409)
            require(len(self.streams) < self.MAX_STREAMS and self.slots.acquire(blocking=False),
                    'wakeword_capacity', 'Wake-word detection is at capacity.', 429)
            stream = Stream(secrets.token_hex(16), authority[0], authority, self.clock(), busy=True)
            self.streams[sid] = stream
        try:
            stream.detector = self.factory()
            require(authorize() == authority, 'wakeword_stopped', 'Session changed while loading detection.', 409)
            with self.lock:
                self._current(sid, stream)
                stream.busy = False
                return {'stream_id': stream.id, 'sample_rate': 16000, 'batch_samples': 5120,
                        'next_sequence': 0, 'phrase': 'Hey Jarvaids'}
        except Exception as error:
            with self.lock:
                if self.streams.get(sid) is stream:
                    del self.streams[sid]
            if isinstance(error, Problem):
                raise
            raise Problem(503, 'wakeword_unavailable', 'Custom detector could not be loaded.') from None
        finally:
            self.slots.release()

    def stop(self, sid, owner, stream_id):
        ident(stream_id)
        with self.lock:
            stream = self.streams.get(sid)
            if stream and stream.id == stream_id:
                require(stream.owner == owner, 'forbidden', 'Only the stream owner can stop this stream.', 403)
                del self.streams[sid]
        return {'stopped': True}

    def batch(self, sid, authority, body, authorize):
        fields(body, ('stream_id', 'sequence', 'base64'))
        ident(body['stream_id'])
        sequence = integer(body['sequence'], 'sequence', 0, 2**31 - 1)
        encoded = body['base64']
        require(type(encoded) is str and len(encoded) == 13656, 'invalid_audio', 'Send exactly 320 ms of PCM16 audio.')
        try:
            raw = base64.b64decode(encoded, validate=True)
        except (ValueError, TypeError):
            raise Problem(422, 'invalid_audio', 'Audio must be valid base64.') from None
        require(len(raw) == BATCH_BYTES, 'invalid_audio', 'Send exactly 5120 mono PCM16 samples.')
        checksum = hashlib.sha256(raw).hexdigest()
        with self.lock:
            self.expire()
            stream = self.streams.get(sid)
            require(stream is not None and stream.id == body['stream_id'], 'wakeword_stopped', 'Start a fresh stream.', 409)
            require(stream.owner == authority[0], 'forbidden', 'This microphone belongs to another facilitator.', 403)
            if stream.authority != authority:
                del self.streams[sid]
                raise Problem(409, 'wakeword_stopped', 'Session changed. Start a fresh stream.')
            require(not stream.busy, 'wakeword_busy', 'Only one batch may be in flight.', 409)
            if sequence == stream.next_sequence - 1 and checksum == stream.previous_hash:
                return dict(stream.previous_result, replayed=True)
            if sequence != stream.next_sequence:
                del self.streams[sid]
                raise Problem(409, 'wakeword_sequence', 'Audio gap or conflicting retry. Start a fresh stream.')
            require(self.slots.acquire(blocking=False), 'wakeword_capacity', 'Detector is busy.', 429)
            stream.busy = True
            stream.touched = self.clock()
        try:
            score = float(stream.detector.predict(raw))
            require(math.isfinite(score) and 0 <= score <= 1, 'wakeword_failed', 'Detector returned an invalid score.', 503)
            require(authorize() == authority, 'wakeword_stopped', 'Session changed during detection.', 409)
            with self.lock:
                self._current(sid, stream)
                detection = None
                if score >= self.threshold and self.clock() - stream.last_detection >= self.COOLDOWN_SECONDS:
                    stream.last_detection = self.clock()
                    detection = {'id': secrets.token_hex(16), 'phrase': 'Hey Jarvaids'}
                result = {'stream_id': stream.id, 'sequence': sequence, 'detection': detection, 'replayed': False}
                stream.next_sequence += 1
                stream.previous_hash, stream.previous_result = checksum, result
                stream.busy = False
                return result
        except Exception as error:
            with self.lock:
                if self.streams.get(sid) is stream:
                    del self.streams[sid]
            if isinstance(error, Problem):
                raise
            raise Problem(503, 'wakeword_failed', 'Detection interrupted. Start a fresh stream.') from None
        finally:
            self.slots.release()
