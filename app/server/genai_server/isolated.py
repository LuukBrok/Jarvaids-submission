"""Killable offline adapter calls. Adapter selection is trusted server configuration.

The child receives one bounded JSON request and returns one bounded JSON result.
No source text or provider exception is written to operational logs. Each call has
its own process because timing out a Python thread does not stop that thread.
Adapters must not launch detached child processes; remote providers also need
their own network timeouts and accounting for calls whose outcome is unknown.
"""
import base64
import importlib
import json
import math
import os
import subprocess
import sys
import threading
import time

from .adapters import ExtractionInput, ExtractionOutput

MAX_INPUT = 8 * 1024 * 1024
MAX_OUTPUT = 1024 * 1024


class IsolatedFailure(RuntimeError):
    """Safe category only, never a provider's exception or source material."""


class IsolatedExtractor:
    def __init__(self, name, module='genai_server.adapters', factory='FixtureExtractor',
                 configuration=None, timeout_seconds=30, cancel_event=None):
        if not math.isfinite(timeout_seconds) or not 0 < timeout_seconds <= 60:
            raise ValueError('Use a finite total timeout between zero and 60 seconds.')
        self.name = name
        self.module = module
        self.factory = factory
        self.configuration = configuration or {}
        self.timeout_seconds = timeout_seconds
        self.cancel_event = cancel_event

    def _check_cancelled(self):
        if self.cancel_event is not None and self.cancel_event.is_set():
            raise IsolatedFailure('adapter_cancelled')

    def extract(self, request):
        self._check_cancelled()
        payload = json.dumps({
            'module': self.module, 'factory': self.factory, 'configuration': self.configuration,
            'request': {'source_id': request.source_id, 'source_revision': request.source_revision,
                        'mime': request.mime, 'image': base64.b64encode(request.image_bytes).decode('ascii'),
                        'regions': request.regions},
        }, ensure_ascii=True, allow_nan=False).encode('utf-8')
        if len(payload) > MAX_INPUT:
            raise IsolatedFailure('adapter_input_limit')
        environment = os.environ.copy()
        # Spawned tests and locally configured adapters need the same import roots.
        environment['PYTHONPATH'] = os.pathsep.join(str(p) for p in sys.path if p)
        environment['PYTHONDONTWRITEBYTECODE'] = '1'
        kwargs = {'creationflags': subprocess.CREATE_NO_WINDOW} if sys.platform == 'win32' else {}
        started = time.monotonic()
        process = subprocess.Popen([sys.executable, '-m', 'genai_server.isolated'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            env=environment, **kwargs)
        received = bytearray()
        finished = threading.Event()
        failed = threading.Event()

        def write_input():
            try:
                process.stdin.write(payload)
                process.stdin.close()
            except (OSError, ValueError):
                failed.set()

        def read_output():
            try:
                while True:
                    chunk = process.stdout.read(65536)
                    if not chunk:
                        break
                    if len(received) + len(chunk) > MAX_OUTPUT:
                        failed.set()
                        break
                    received.extend(chunk)
            except (OSError, ValueError):
                failed.set()
            finally:
                finished.set()

        writer = threading.Thread(target=write_input, daemon=True)
        reader = threading.Thread(target=read_output, daemon=True)
        writer.start()
        reader.start()
        try:
            while not finished.wait(.02):
                self._check_cancelled()
                if failed.is_set():
                    raise IsolatedFailure('adapter_protocol_failed')
                if time.monotonic() - started >= self.timeout_seconds:
                    raise IsolatedFailure('adapter_timeout')
            if failed.is_set():
                raise IsolatedFailure('adapter_output_limit')
            self._check_cancelled()
            while process.poll() is None:
                self._check_cancelled()
                remaining = self.timeout_seconds - (time.monotonic() - started)
                if remaining <= 0:
                    raise IsolatedFailure('adapter_timeout')
                try:
                    process.wait(timeout=min(.02, remaining))
                except subprocess.TimeoutExpired:
                    pass
            if time.monotonic() - started >= self.timeout_seconds:
                raise IsolatedFailure('adapter_timeout')
            if process.returncode:
                raise IsolatedFailure('adapter_process_failed')
            try:
                result = json.loads(received)
                if set(result) != {'notes', 'provider', 'model', 'synthetic', 'usage'}:
                    raise ValueError('Invalid envelope')
                return ExtractionOutput(notes=tuple(result['notes']), provider=result['provider'],
                    model=result['model'], synthetic=result['synthetic'], usage=result['usage'])
            except (ValueError, TypeError, KeyError):
                raise IsolatedFailure('adapter_protocol_failed') from None
        finally:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)
            writer.join(timeout=1)
            reader.join(timeout=1)
            process.stdin.close()
            process.stdout.close()


def _child():
    """No child traceback or incidental print output can become a result."""
    result_stream = sys.stdout.buffer
    with open(os.devnull, 'w') as quiet:
        sys.stdout = quiet
        sys.stderr = quiet
        try:
            raw = sys.stdin.buffer.read(MAX_INPUT + 1)
            if len(raw) > MAX_INPUT:
                return 2
            envelope = json.loads(raw)
            adapter = getattr(importlib.import_module(envelope['module']), envelope['factory'])(**envelope['configuration'])
            item = envelope['request']
            request = ExtractionInput(item['source_id'], item['source_revision'], item['mime'],
                base64.b64decode(item['image'], validate=True), tuple(item['regions']))
            result = adapter.extract(request)
            # Validate in the service too, where identities and source references exist.
            if type(result.notes) not in (tuple, list) or len(result.notes) > 60:
                return 2
            value = {'notes': result.notes, 'provider': result.provider, 'model': result.model,
                     'synthetic': result.synthetic, 'usage': result.usage}
            # Incremental encoding bounds the serialised buffer before writing it.
            encoded = bytearray()
            for piece in json.JSONEncoder(ensure_ascii=True, allow_nan=False).iterencode(value):
                chunk = piece.encode('utf-8')
                if len(encoded) + len(chunk) > MAX_OUTPUT:
                    return 2
                encoded.extend(chunk)
            result_stream.write(encoded)
            result_stream.flush()
            return 0
        except BaseException:
            return 2


if __name__ == '__main__':
    raise SystemExit(_child())
