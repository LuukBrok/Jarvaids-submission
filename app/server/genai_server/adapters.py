"""Provider boundary. The only bundled adapter is explicitly synthetic and offline."""
import math
from dataclasses import dataclass
from typing import Protocol


def _post_multipart(base_url,path,fields,file_bytes,provider,timeout_seconds):
    """Shared by every adapter that calls a local HTTP transcription server
    (Vibe's Sona API, whisper.cpp's server): builds one multipart/form-data
    body with a WAV file plus simple text fields, posts it, and turns any
    failure into a TranscriptionFailure carrying that server's own error
    body where there is one, rather than each adapter reimplementing the
    same request/error handling with its own small differences to drift."""
    import urllib.request,urllib.error,json,secrets
    boundary=secrets.token_hex(16)
    body=bytearray()
    for name,value in fields.items():
        if value is None:continue
        body+=(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n').encode()
    body+=(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="chunk.wav"\r\n'
           f'Content-Type: audio/wav\r\n\r\n').encode()
    body+=file_bytes
    body+=f'\r\n--{boundary}--\r\n'.encode()
    req=urllib.request.Request(base_url.rstrip('/')+path,data=bytes(body),
        headers={'Content-Type':f'multipart/form-data; boundary={boundary}'},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=timeout_seconds) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        # The server's own error body (Vibe's ErrorModel, or whisper.cpp
        # server's own JSON error) says whether this is a bad field name, a
        # model problem, or something else; without it a 4xx/5xx is
        # indistinguishable from the server being unreachable.
        try:detail=exc.read().decode('utf-8','replace')[:500]
        except Exception:detail='(could not read error body)'
        raise TranscriptionFailure(f'{provider}_http_{exc.code}: {detail}') from exc
    except (urllib.error.URLError,TimeoutError,json.JSONDecodeError,OSError) as exc:
        raise TranscriptionFailure(f'{provider}_unreachable') from exc


def _strip_non_speech_tags(text):
    """Whisper-family models (this is not whisper.cpp-specific: OpenAI's own
    whisper and faster-whisper do it too) sometimes emit a bracketed or
    parenthesised annotation instead of real words on a non-speech chunk,
    e.g. '[BLANK_AUDIO]', '[SILENCE]', '(silence)', '[MUSIC]'. Without this,
    such a chunk looks exactly like a real transcribed sentence in the room,
    which a real user's own whisper.cpp run showed happening: '[BLANK_AUDIO]'
    rendered on screen as if someone had said it."""
    import re
    stripped=text.strip()
    # One or more bracketed/parenthesised tags, each optionally followed by
    # sentence punctuation whisper.cpp's punctuation restoration sometimes
    # adds ('(silence).', not just '(silence)'), and optionally repeated
    # ('(silence) (silence)' on a longer quiet chunk). A real user's own
    # run showed the plain '(silence)' case still leaking through as if it
    # were spoken, because the first version of this only matched one bare
    # tag with nothing else in the string.
    if re.fullmatch(r'(?:[\[(][A-Za-z _-]+[\])][.,!?]*\s*)+',stripped):
        return ''
    return stripped


def _pcm16_to_wav_bytes(chunk_bytes,sample_rate):
    """Both real transcriber adapters below need one chunk as a WAV file,
    since that is what their respective libraries/APIs accept; binding this
    in one place means the two adapters cannot silently drift on channel
    count or sample width."""
    import io,wave
    buf=io.BytesIO()
    with wave.open(buf,'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(sample_rate)
        w.writeframes(chunk_bytes)
    return buf.getvalue()


@dataclass(frozen=True)
class ExtractionInput:
    source_id: str
    source_revision: int
    mime: str
    image_bytes: bytes
    regions: tuple


@dataclass(frozen=True)
class ExtractionOutput:
    notes: tuple
    provider: str
    model: str
    synthetic: bool
    usage: dict


class Extractor(Protocol):
    name: str
    def extract(self, request: ExtractionInput) -> ExtractionOutput: ...


class FixtureExtractor:
    name='fixture'

    def extract(self,request):
        return ExtractionOutput(
            notes=tuple({'region_id':r['id'],'text':f'FIXTURE ONLY, sample note {i+1}; no OCR performed.',
                         'status':'readable'} for i,r in enumerate(request.regions)),
            provider='fixture',model='synthetic-v1',synthetic=True,
            usage={'input_units':0,'output_units':0,'cost':None,'currency':None})


# Pipeline 1 (audio). See deliverables/documentation/pipelines.md section 1 and
# flowchart.md F1.1-F1.3. Shipped scope is single-lane: no fast/slow two-lane
# split (see decisions/decision-log.md), so one call here stands for stages
# S6 (transcribe) and S7 (diarise, per-connection fallback) together.


@dataclass(frozen=True)
class TranscriptionInput:
    chunk_bytes: bytes
    sample_rate: int
    duration_ms: int
    ended_reason: str  # 'silence' (S4 endpoint) or 'hard_cut' (S4 12s cap)
    speaker_actor_id: str  # per-connection attribution; see decision-log


@dataclass(frozen=True)
class TranscriptionOutput:
    text: str
    confidence: float
    provider: str
    model: str
    synthetic: bool
    usage: dict


class Transcriber(Protocol):
    name: str
    def transcribe(self, request: TranscriptionInput) -> TranscriptionOutput: ...


class TranscriptionFailure(Exception):
    """Raised by a transcriber that cannot produce text for a chunk.

    The caller (Service._source_audio) must turn this into a visible gap
    marker rather than dropping the chunk, per F6.4 (degrade loudly).
    """


class FixtureTranscriber:
    """Deterministic, offline, no audio decoding. The default adapter, same
    role as FixtureExtractor for images: it proves the pipeline's plumbing
    (consent gate, provenance, gap handling) without claiming any ASR
    accuracy. Never mistake a passing test against this for verified
    transcription quality."""
    name='fixture'

    def transcribe(self,request):
        if not request.chunk_bytes:
            raise TranscriptionFailure('empty_chunk')
        return TranscriptionOutput(
            text=f'FIXTURE ONLY, {request.duration_ms} ms of audio; no ASR performed.',
            confidence=0.0,provider='fixture',model='synthetic-v1',synthetic=True,
            usage={'input_units':0,'output_units':0,'cost':None,'currency':None})


class LocalWhisperTranscriber:
    """Real local ASR boundary (S6), matching F6.2: audio never leaves this
    process. Wraps faster-whisper (CTranslate2 Whisper) if it is installed;
    raises at construction otherwise so a caller falls back explicitly
    rather than silently running the fixture under a real-sounding name.

    NOT exercised in this repository's CI: no GPU/model weights are
    available in the sandbox this was built in. See BUILD-STATUS.md."""
    name='local-whisper'

    def __init__(self,model_size='medium',device='cpu',compute_type='int8',language=None,cpu_threads=0):
        """language: an ISO 639-1 code ('en', 'nl', ...) to pin, or None to
        auto-detect per chunk. pipelines.md S6 wants mixed Dutch/English in
        the same sentence, which needs auto-detection, but auto-detection
        needs several seconds of audio to be reliable and each chunk here is
        0.6-12s in isolation, with no memory of the language spoken in the
        previous chunk. On a short, single-language recording this makes
        auto-detect worse than useless: it can flip language mid-meeting and
        every wrong guess mistranscribes the whole chunk, not just a word.
        Pinning a language is the fix for that case; it is a real loss of
        the documented mixed-language goal, which is why it defaults to
        auto-detect rather than silently narrowing to one language."""
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError(
                'faster-whisper is not installed; construct FixtureTranscriber '
                'instead, or install faster-whisper to use local ASR.') from exc
        # cpu_threads=0 is faster-whisper's own "let it choose" default, which
        # on a modest laptop can mean one inference call claims every core,
        # starving the HTTP server's own threads (other commands, and the
        # page's own snapshot polling, both saw connection failures/timeouts
        # from exactly this on a real user's machine). Capping it trades some
        # per-chunk speed for the server staying responsive to everything
        # else while a chunk transcribes.
        self._model=WhisperModel(model_size,device=device,compute_type=compute_type,cpu_threads=cpu_threads)
        self._model_size=model_size
        self._language=language

    def transcribe(self,request):
        import io
        buf=io.BytesIO(_pcm16_to_wav_bytes(request.chunk_bytes,request.sample_rate))
        # vad_filter runs faster-whisper's own (Silero) VAD over the chunk
        # first and skips the non-speech parts. This module's own VAD
        # (capture-audio.mjs) is a crude energy gate, so chunks still carry
        # real silence/noise padding at their edges, which is exactly what
        # makes Whisper-class models hallucinate plausible-sounding text
        # from nothing. condition_on_previous_text=False stops a bad guess
        # early in a chunk being fed back in as context for the rest of it,
        # which is how one hallucination compounds into a longer one.
        # Supply the product name as vocabulary, without priming an activation
        # sentence. Silero still rejects non-speech before decoding it.
        segments,info=self._model.transcribe(buf,language=self._language,
            vad_filter=True,condition_on_previous_text=False,word_timestamps=True,
            hotwords='Jarvaids')
        segments=list(segments)
        text=_strip_non_speech_tags(' '.join(s.text.strip() for s in segments))
        if not text:
            raise TranscriptionFailure('no_speech_detected')
        return TranscriptionOutput(
            text=text,confidence=float(getattr(info,'language_probability',0.0) or 0.0),
            provider='faster-whisper',model=self._model_size,synthetic=False,
            usage={'input_units':request.duration_ms,'output_units':len(text),'cost':None,'currency':None,
                'words':[{'start':float(w.start),'end':float(w.end),'word':w.word}
                         for segment in segments for w in (getattr(segment,'words',None) or [])]})


class VibeTranscriber:
    """Calls a locally-running Vibe app (github.com/thewh1teagle/vibe) instead
    of running a model in this process. Vibe exposes an OpenAI-compatible
    'Sona API' server (its Settings > API Server panel, started by hand) at
    a per-launch port on 127.0.0.1 only, so F6.2 (audio never leaves this
    machine) still holds: it is a second local process, not a network
    service. Vibe's own transcription engine (whisper.cpp, not faster-
    whisper) and its own model/settings decide accuracy; this adapter only
    shapes the request and reads back {"text": ...} from its
    POST /v1/audio/transcriptions.

    NOT exercised in this repository: it depends on Vibe being installed,
    running and reachable on the machine this server runs on, none of which
    exists in any sandbox this was built in. See BUILD-STATUS.md."""
    name='vibe'

    def __init__(self,base_url,model,language=None,timeout_seconds=60):
        """base_url: Vibe's own API URL, e.g. 'http://127.0.0.1:56985' from
        its Settings panel; it changes every time Vibe's server is
        (re)started, so there is no usable default. model: the model name
        Vibe already has loaded (its own Settings/Models screen), required
        by Vibe's API and passed straight through, not validated here."""
        require_url=(base_url or '').strip()
        if not require_url.startswith('http://127.0.0.1:') and not require_url.startswith('http://localhost:'):
            raise ValueError(
                "vibe base_url must be a loopback address (http://127.0.0.1:<port>), "
                "matching F6.2: this adapter must never send audio off-machine.")
        self._base_url=require_url.rstrip('/')
        self._model=model
        self._language=language
        self._timeout=timeout_seconds

    def transcribe(self,request):
        wav=_pcm16_to_wav_bytes(request.chunk_bytes,request.sample_rate)
        fields={'model':self._model,'response_format':'json'}
        if self._language:fields['language']=self._language
        payload=_post_multipart(self._base_url,'/v1/audio/transcriptions',fields,wav,'vibe',self._timeout)
        text=_strip_non_speech_tags(payload.get('text') or '')
        if not text:
            raise TranscriptionFailure('no_speech_detected')
        return TranscriptionOutput(
            text=text,confidence=0.0,provider='vibe',model=self._model,synthetic=False,
            usage={'input_units':request.duration_ms,'output_units':len(text),'cost':None,'currency':None})


# F1.3 opt-in voice identification. See decisions/decision-log.md for why this
# is additive to the per-connection fallback above rather than a replacement,
# and for the embedding library choice and its stated performance cost. This
# is speaker verification/identification (one embedding per chunk, compared
# by cosine similarity to a small set of enrolled profiles), not unsupervised
# diarisation: pipelines.md's S7 already names clustering-based diarisation as
# the harder, out-of-scope problem, and the task this module serves (enrolled
# people, one device, "who is this voice closest to") does not need it.


@dataclass(frozen=True)
class EmbeddingOutput:
    vector: tuple  # fixed-length tuple of floats, JSON-safe without a numpy
                   # dependency leaking out of this module into service.py
    provider: str
    model: str
    synthetic: bool


class SpeakerIdentificationFailure(Exception):
    """Raised by a SpeakerIdentifier that cannot produce an embedding for a
    chunk (bad/empty audio, model error). The caller must treat this as a
    degraded signal, never a crash: service.py's _identify_speaker logs it
    and returns 'unidentified', and _source_audio still stores the chunk's
    transcript either way (constraint F6.4, same rule TranscriptionFailure
    follows above). Enrollment (speaker.enroll) is different: a person is
    deliberately recording one clip right now, so a failure there is
    surfaced as a rejected request (Problem), not swallowed, so they know
    to retake it.
    """


class SpeakerIdentifier(Protocol):
    name: str
    def embed(self, chunk_bytes: bytes, sample_rate: int) -> EmbeddingOutput: ...


# Prototype operating point, not a calibrated accuracy guarantee. The first
# laptop trial rejected every clip at 0.75 (observed best scores 0.44-0.72).
# Accept clearer matches from 0.65, but require separation from the next voice
# so lowering the cutoff does not simply choose a name for ambiguous audio.
SPEAKER_MATCH_THRESHOLD = 0.65
SPEAKER_MATCH_MARGIN = 0.08


def _cosine_similarity(a, b):
    """Pure arithmetic, no model: lets the matching/threshold logic below be
    unit tested with plain injected vectors, never a real embedding model."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def match_speaker(vector, profiles, threshold=SPEAKER_MATCH_THRESHOLD, margin=SPEAKER_MATCH_MARGIN):
    """The whole of F1.3's opt-in voice-ID decision in one pure function.

    `profiles` is an iterable of (profile_id, name, embedding) triples: the
    session's enrolled speaker_profile records. Returns
    (profile_id, name, confidence) for the best-scoring profile once its
    score is at or above `threshold` and exceeds the runner-up by `margin`,
    or (None, None, best_score_seen)
    otherwise, best_score_seen included so the caller can still show a real
    number for 'why didn't this match', never a wrong guess presented with
    confidence (F6.3/F1.3's own stated risk: a mislabel is worse than no
    label at all).

    No profiles at all is not a special case needing its own branch: the
    loop simply never improves on (None, None, 0.0), so it already returns
    the correct 'nothing to compare against' answer for free.
    """
    best_id, best_name, best_score = None, None, 0.0
    runner_up = 0.0
    for profile_id, name, embedding in profiles:
        score = _cosine_similarity(vector, embedding)
        if score > best_score:
            runner_up = best_score
            best_id, best_name, best_score = profile_id, name, score
        else:
            runner_up = max(runner_up, score)
    if best_score >= threshold and best_score - runner_up >= margin:
        return best_id, best_name, best_score
    return None, None, best_score


class FixtureSpeakerIdentifier:
    """Deterministic, offline, claims no real voice signal. Same role as
    FixtureTranscriber: it proves the enrollment/matching plumbing (consent
    gate, provenance, the fixed point where _source_audio asks 'does this
    chunk match anyone enrolled') without claiming any real speaker-ID
    accuracy. Every embedding is the same all-zero vector, so
    match_speaker's cosine similarity is always exactly 0.0 (an all-zero
    vector has no direction to be similar to anything, by construction, not
    by coincidence of a threshold) and every chunk comes back unidentified
    once any profile has been enrolled. Never mistake a passing test against
    this for verified speaker-ID accuracy."""
    name = 'fixture'
    _DIMENSIONS = 256  # arbitrary; only has to match itself

    def embed(self, chunk_bytes, sample_rate):
        if not chunk_bytes:
            raise SpeakerIdentificationFailure('empty_chunk')
        return EmbeddingOutput(vector=tuple(0.0 for _ in range(self._DIMENSIONS)),
            provider='fixture', model='synthetic-v1', synthetic=True)


class ResemblyzerSpeakerIdentifier:
    """Real embedding boundary, wrapping Resemblyzer
    (github.com/resemble-ai/Resemblyzer): a small LSTM-based voice encoder
    (256-dim d-vector style embedding) built specifically for speaker
    verification/diarisation on CPU, not a full diarisation toolkit with its
    own VAD/segmentation/clustering pipeline bolted on (pyannote.audio and
    similar were considered and rejected for exactly that extra weight; see
    decisions/decision-log.md). Chosen over those as the lighter-weight
    option for the stated task (compare one chunk to a handful of enrolled
    profiles), not as the lightest possible option in the abstract: it still
    depends on PyTorch for inference, which this codebase otherwise avoids
    (faster-whisper above uses CTranslate2, not full PyTorch), and that is a
    real added cost on top of ASR already running on the same CPU, which is
    why --speaker-id defaults to 'fixture' and this adapter is opt-in,
    exactly like --transcriber local-whisper above.

    The Windows local test exercises the actual encoder and an enrolment/
    matching HTTP journey with synthetic speech. Human multiple-speaker
    accuracy and overlapping speech remain unverified; see BUILD-STATUS.md."""
    name = 'resemblyzer'

    def __init__(self):
        try:
            from resemblyzer import VoiceEncoder
        except ImportError as exc:
            raise RuntimeError(
                'resemblyzer is not installed; construct FixtureSpeakerIdentifier '
                'instead, or install resemblyzer (see requirements-speaker-id.txt) '
                'to use real voice identification.') from exc
        # device='cpu' is explicit, not Resemblyzer's own default: F6.2 says
        # local-only, and leaving this to whatever device the library
        # auto-detects risks silently trying CUDA on a machine that may not
        # have it reliably configured.
        import torch
        torch.set_num_threads(2)
        self._encoder = VoiceEncoder(device='cpu')

    def embed(self, chunk_bytes, sample_rate):
        if not chunk_bytes:
            raise SpeakerIdentificationFailure('empty_chunk')
        try:
            import numpy as np
            from resemblyzer import preprocess_wav
            # PCM16 bytes -> float32 in [-1, 1], same conversion
            # _pcm16_to_wav_bytes's consumers need, done directly as an array
            # here because Resemblyzer's own preprocess_wav takes a waveform
            # array (or a file path), not a WAV-file byte string.
            samples = np.frombuffer(chunk_bytes, dtype='<i2').astype(np.float32) / 32768.0
            wav = preprocess_wav(samples, source_sr=sample_rate)
            if len(wav) < 12800:
                raise SpeakerIdentificationFailure('Not enough clear speech. Record a longer sample with only this speaker.')
            vector = self._encoder.embed_utterance(wav)
        except SpeakerIdentificationFailure:
            raise
        except Exception as exc:
            # Resemblyzer's own preprocessing can refuse a chunk that is all
            # silence or too short to extract a stable embedding from; that
            # is a normal, expected outcome for some chunks, not a reason to
            # take down transcription for the rest of the session (F6.4).
            raise SpeakerIdentificationFailure(f'resemblyzer_failed: {exc}') from exc
        return EmbeddingOutput(vector=tuple(float(x) for x in vector),
            provider='resemblyzer', model='voice-encoder', synthetic=False)

    def identify_words(self, raw, sample_rate, words, profiles, threshold):
        """Attribute short speech windows, rather than mixing six seconds of voices."""
        duration = len(raw) / (sample_rate * 2)
        windows = {}
        labelled = []
        for word in words:
            middle = (word['start'] + word['end']) / 2
            key = int(middle / .8)
            if key not in windows:
                centre = key * .8 + .4
                start = max(0, min(centre - .9, duration - 1.8))
                end = min(duration, start + 1.8)
                try:
                    out = self.embed(raw[int(start*sample_rate)*2:int(end*sample_rate)*2], sample_rate)
                    pid, name, confidence = match_speaker(out.vector, profiles, threshold, margin=.04)
                    windows[key] = {'status':'matched' if pid else 'unidentified',
                        'profile_id':pid,'name':name,'confidence':confidence,'provider':out.provider,
                        'model':out.model,'synthetic':out.synthetic,
                        'reason':None if pid else 'ambiguous_or_short_window'}
                except SpeakerIdentificationFailure:
                    windows[key] = {'status':'unidentified','profile_id':None,'name':None,
                        'confidence':0.0,'provider':self.name,'model':'voice-encoder',
                        'synthetic':False,'reason':'insufficient_speech'}
            labelled.append((word, windows[key]))
        utterances=[]
        for pair in labelled:
            if not utterances or pair[0]['start']-utterances[-1][-1][0]['end']>.5 or utterances[-1][-1][0]['word'].rstrip().endswith(('.', '?', '!')):
                utterances.append([])
            utterances[-1].append(pair)
        labelled=[]
        for utterance in utterances:
            anchors=[pair for pair in utterance if pair[1]['profile_id'] is not None]
            identities={pair[1]['profile_id'] for pair in anchors}
            unknown=[pair for pair in utterance if pair[1]['profile_id'] is None]
            # Extend a clear single-speaker utterance over a short boundary word,
            # such as 'I', rather than losing first-person task ownership.
            fill=len(identities)==1 and len(anchors)>=2 and len(unknown)<=max(1,len(utterance)//4) and sum(w['end']-w['start'] for w,_ in unknown)<=.6
            for word,match in utterance:
                if fill and match['profile_id'] is None:
                    match={**anchors[0][1],'reason':'short_boundary_continuation'}
                labelled.append((word,match))
        turns = []
        for word, match in labelled:
            identity = match['profile_id']
            if turns and turns[-1]['speaker_match']['profile_id'] == identity:
                turns[-1]['text'] += word['word']
                turns[-1]['end'] = word['end']
            else:
                turns.append({'text':word['word'],'start':word['start'],'end':word['end'],
                              'speaker_match':dict(match)})
        # ASR may spell a name as connected letter tokens. A window boundary
        # inside H-R-V-D must not turn one spoken name into two transcript rows.
        import re
        merged=[]
        for turn in turns:
            if (merged and merged[-1]['speaker_match']['profile_id'] is None
                    and turn['speaker_match']['profile_id'] is not None
                    and turn['text'].lstrip().startswith('-')
                    and re.fullmatch(r'\s*[A-Za-z](?:[.\s-]*[A-Za-z])*\s*',merged[-1]['text'])
                    and turn['start']-merged[-1]['end']<=.5):
                previous=merged.pop()
                turn={**turn,'text':previous['text']+turn['text'],'start':previous['start'],
                      'speaker_match':{**turn['speaker_match'],'reason':'joined_spelled_name'}}
            merged.append(turn)
        return merged


class WhisperCppServerTranscriber:
    """Calls a locally-running whisper.cpp server (whisper-server.exe from
    ggerganov/whisper.cpp's own releases) instead of running a model in this
    process. Started by hand, e.g.
    'whisper-server.exe -m Models\\ggml-medium.bin -l en --port 8080', with
    the model already loaded before this server ever calls it, unlike Vibe's
    API where the model name travels with every request. Only a loopback
    base_url is accepted, matching F6.2, same as VibeTranscriber.

    NOT exercised in this repository: it depends on whisper-server.exe
    running and reachable on the machine this server runs on, which exists
    only on a real user's machine. See BUILD-STATUS.md."""
    name='whispercpp-server'

    def __init__(self,base_url,language=None,timeout_seconds=60):
        require_url=(base_url or '').strip()
        if not require_url.startswith('http://127.0.0.1:') and not require_url.startswith('http://localhost:'):
            raise ValueError(
                "whispercpp base_url must be a loopback address (http://127.0.0.1:<port>), "
                "matching F6.2: this adapter must never send audio off-machine.")
        self._base_url=require_url.rstrip('/')
        self._language=language
        self._timeout=timeout_seconds

    def transcribe(self,request):
        wav=_pcm16_to_wav_bytes(request.chunk_bytes,request.sample_rate)
        fields={'response_format':'json','temperature':'0.0'}
        if self._language:fields['language']=self._language
        payload=_post_multipart(self._base_url,'/inference',fields,wav,'whispercpp',self._timeout)
        text=_strip_non_speech_tags(payload.get('text') or '')
        if not text:
            raise TranscriptionFailure('no_speech_detected')
        return TranscriptionOutput(
            text=text,confidence=0.0,provider='whisper.cpp',model='server',synthetic=False,
            usage={'input_units':request.duration_ms,'output_units':len(text),'cost':None,'currency':None})
