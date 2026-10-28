import argparse
import os
from pathlib import Path
import threading
import sys

from .http import LocalServer
from .service import Service
from .isolated import IsolatedExtractor
from .wakeword import LocalDetector
from .adapters import FixtureTranscriber, LocalWhisperTranscriber, VibeTranscriber, WhisperCppServerTranscriber
from .adapters import FixtureSpeakerIdentifier, ResemblyzerSpeakerIdentifier, SPEAKER_MATCH_THRESHOLD
from .poll_model import configured_poll_model
from .document_model import configured_document_model


class InstanceLock:
    """OS-held lock released on crash; stops competing startup recovery workers."""
    def __init__(self,path):
        self.file=Path(path).open('a+b')
        try:
            self.file.seek(0,2)
            if self.file.tell()==0:
                self.file.write(b'0');self.file.flush()
            self.file.seek(0)
            if sys.platform=='win32':
                import msvcrt
                msvcrt.locking(self.file.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.file,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:
            self.file.close();raise RuntimeError('Another server owns this data directory.')

    def close(self):self.file.close()


def main():
    parser=argparse.ArgumentParser(description='Run the offline/local GenAI backend prototype.')
    parser.add_argument('--port',type=int,default=3000)
    parser.add_argument('--bind',default='127.0.0.1')
    parser.add_argument('--advertise-host',action='append',default=[])
    parser.add_argument('--data-dir',type=Path,default=Path('.local'))
    parser.add_argument('--allow-origin',action='append',default=[])
    parser.add_argument('--transcriber',choices=['fixture','local-whisper','vibe','whispercpp'],default='fixture',
        help='fixture (default): deterministic placeholder text, no audio decoded. '
             'local-whisper: real ASR via faster-whisper, on this machine only (F6.2). '
             'First use downloads model weights and needs internet once; after that it is offline. '
             "vibe: call a locally-running Vibe app's own API Server (Settings > API Server, "
             'Start server) instead of running a model here; needs --vibe-url and --vibe-model. '
             'whispercpp: call a locally-running whisper-server.exe (ggerganov/whisper.cpp); '
             'needs --whispercpp-url.')
    parser.add_argument('--whisper-model-size',default='medium',
        help='tiny/base/small/medium/large-v3 etc. Smaller is faster but less accurate; '
             'tiny or base are the ones worth trying on a laptop CPU.')
    parser.add_argument('--whisper-device',default='cpu',help='cpu, or cuda if a GPU/CUDA toolkit is available.')
    parser.add_argument('--whisper-compute-type',default='int8',help='faster-whisper compute_type, e.g. int8 on CPU.')
    parser.add_argument('--whisper-language',default=None,
        help="ISO 639-1 code, e.g. 'en' or 'nl', to pin transcription to one language. "
             'Default: auto-detect per chunk, which pipelines.md wants for mixed-language '
             'meetings but is unreliable on short chunks in a single-language room, since '
             'each chunk guesses fresh with no memory of the last one. Pin this if words '
             'come out in the wrong language or jumbled. Also used for --transcriber vibe.')
    parser.add_argument('--vibe-url',default=None,
        help="Vibe's own API URL, shown in its Settings > API Server panel once you click "
             "Start server, e.g. http://127.0.0.1:56985. It changes every time Vibe's server "
             'is (re)started, so there is no default; loopback addresses only (F6.2).')
    parser.add_argument('--vibe-model',default=None,
        help='The model name Vibe already has loaded (its own Settings/Models screen). '
             'Passed straight through to Vibe, not validated here.')
    parser.add_argument('--vibe-timeout-seconds',type=int,default=60,
        help='How long to wait for one chunk from Vibe before treating it as a gap.')
    parser.add_argument('--whispercpp-url',default=None,
        help='whisper-server.exe\'s URL, e.g. http://127.0.0.1:8080 (its own --host/--port, '
             'default port 8080). Loopback addresses only (F6.2). Start it yourself first, '
             'e.g. "whisper-server.exe -m Models\\ggml-medium.bin -l en --port 8080".')
    parser.add_argument('--whispercpp-timeout-seconds',type=int,default=60,
        help='How long to wait for one chunk from whisper-server.exe before treating it as a gap.')
    parser.add_argument('--whisper-cpu-threads',type=int,default=0,
        help='0 (default): faster-whisper picks, which can claim every CPU core for one '
             'chunk and make the server briefly unresponsive to everything else, including '
             "this page's own polling. Set it to something like 2 or 4 if the page shows "
             '"Connection failed" or "Request timed out" while transcribing, at some cost '
             'to per-chunk speed.')
    parser.add_argument('--speaker-id',choices=['fixture','resemblyzer'],default='fixture',
        help='F1.3 opt-in voice identification, additive to the per-connection fallback. '
             'fixture (default): no profile ever matches, so capture behaves exactly as it '
             'did before this feature existed. resemblyzer: real CPU voice embeddings via '
             'the Resemblyzer library, a real added cost (pulls in PyTorch) on top of ASR '
             'already running on this machine; see requirements-speaker-id.txt and '
             'decisions/decision-log.md before enabling it on modest hardware.')
    parser.add_argument('--speaker-match-threshold',type=float,default=SPEAKER_MATCH_THRESHOLD,
        help=f'Cosine similarity an enrolled profile must reach to be named rather than '
             f'left unidentified (default {SPEAKER_MATCH_THRESHOLD}, an uncalibrated prototype '
             'setting). A lead over the runner-up is also required. Only used with --speaker-id resemblyzer.')
    parser.add_argument('--wakeword-manifest',type=Path,default=None)
    parser.add_argument('--automatic-workspace',action='store_true',help='Apply notes and command results without routine review.')
    parser.add_argument('--poll-ai',choices=['off','auto','claude'],default='off',
        help='Live poll interpretation: off (offline default), or Claude with ANTHROPIC_API_KEY from the repository .env. Sends relevant transcript text, never audio.')
    parser.add_argument('--command-ai',choices=['off','auto','claude'],default='off',
        help='List/calendar interpretation from the original meeting transcript. Uses the existing repository .env key; sends text, never audio.')
    parser.add_argument('--extractor',choices=['fixture','claude'],default='fixture',
        help='fixture (default): "FIXTURE ONLY" text for every marked region, nothing leaves the machine. '
             'claude: read each marked region with Claude. Sends the region crops to Anthropic; '
             'needs requirements-claude.txt and ANTHROPIC_API_KEY in the repository .env.')
    parser.add_argument('--extractor-effort',choices=['low','medium','high'],default='low',
        help="Claude's effort for reading notes (default low, a guess to be measured against medium). "
             'Higher effort reads more carefully and takes longer; a job has 60 seconds.')
    parser.add_argument('--summary-ai',choices=['off','ollama','claude'],default='off')
    parser.add_argument('--summary-model',default='gemma3:4b')
    args=parser.parse_args()
    args.data_dir.mkdir(parents=True,exist_ok=True)
    lock=InstanceLock(args.data_dir/'server.lock')
    if args.transcriber=='local-whisper':
        try:
            transcriber=LocalWhisperTranscriber(model_size=args.whisper_model_size,
                device=args.whisper_device,compute_type=args.whisper_compute_type,
                language=args.whisper_language,cpu_threads=args.whisper_cpu_threads)
        except RuntimeError as exc:
            lock.close();raise SystemExit(f'--transcriber local-whisper: {exc}')
    elif args.transcriber=='vibe':
        if not args.vibe_url or not args.vibe_model:
            lock.close();raise SystemExit('--transcriber vibe requires --vibe-url and --vibe-model.')
        try:
            transcriber=VibeTranscriber(base_url=args.vibe_url,model=args.vibe_model,
                language=args.whisper_language,timeout_seconds=args.vibe_timeout_seconds)
        except ValueError as exc:
            lock.close();raise SystemExit(f'--transcriber vibe: {exc}')
    elif args.transcriber=='whispercpp':
        if not args.whispercpp_url:
            lock.close();raise SystemExit('--transcriber whispercpp requires --whispercpp-url.')
        try:
            transcriber=WhisperCppServerTranscriber(base_url=args.whispercpp_url,
                language=args.whisper_language,timeout_seconds=args.whispercpp_timeout_seconds)
        except ValueError as exc:
            lock.close();raise SystemExit(f'--transcriber whispercpp: {exc}')
    else:
        transcriber=FixtureTranscriber()
    if args.speaker_id=='resemblyzer':
        try:
            speaker_identifier=ResemblyzerSpeakerIdentifier()
        except RuntimeError as exc:
            lock.close();raise SystemExit(f'--speaker-id resemblyzer: {exc}')
    else:
        speaker_identifier=FixtureSpeakerIdentifier()
    wakeword_factory=(lambda:LocalDetector(args.wakeword_manifest)) if args.wakeword_manifest else None
    poll_model,poll_notice=configured_poll_model(args.poll_ai,Path(__file__).resolve().parents[3]/'.env')
    document_model,document_notice=configured_document_model(args.command_ai,Path(__file__).resolve().parents[3]/'.env')
    if args.extractor=='claude':
        from .claude_synthesis import load_env_key
        load_env_key(Path(__file__).resolve().parents[3]/'.env')
        try:
            import anthropic  # noqa: F401  checked here so a missing package fails at startup, not per job
        except ImportError:
            lock.close();raise SystemExit('--extractor claude: pip install -r app/server/requirements-claude.txt')
        if not os.environ.get('ANTHROPIC_API_KEY'):
            lock.close();raise SystemExit('--extractor claude: put ANTHROPIC_API_KEY in the repository .env.')
        extractor=IsolatedExtractor('claude',module='genai_server.claude_extractor',factory='ClaudeExtractor',
            configuration={'effort':args.extractor_effort},timeout_seconds=60)
    else:
        extractor=IsolatedExtractor('fixture')
    from .summary_model import OllamaSummaryModel, ClaudeSummaryModel
    if args.summary_ai=='claude':
        from .claude_synthesis import load_env_key
        load_env_key(Path(__file__).resolve().parents[3]/'.env')
        summary_model=ClaudeSummaryModel()
    else:summary_model=OllamaSummaryModel(args.summary_model) if args.summary_ai=='ollama' else None
    service=Service(args.data_dir/'genai.sqlite3',extractor=extractor,automatic_workspace=args.automatic_workspace,
        transcriber=transcriber,speaker_identifier=speaker_identifier,
        speaker_match_threshold=args.speaker_match_threshold,wakeword_factory=wakeword_factory,
        poll_model=poll_model,poll_notice=poll_notice,document_model=document_model,document_notice=document_notice,summary_model=summary_model)
    service.recover_summary_jobs()
    service.recover_jobs();service.recover_poll_jobs();service.recover_document_jobs()
    server=LocalServer((args.bind,args.port),service,args.allow_origin,args.advertise_host)
    stop=threading.Event()
    def worker():
        try:
            while not stop.is_set():
                service.runtime.begin('worker')
                try:
                    worked=service.run_one_job();service.runtime.succeeded('worker')
                except Exception:
                    service.runtime.failed('worker')
                    # Never print provider/source-bearing exceptions to operational logs.
                    print('Worker iteration failed; pending state retained.',file=sys.stderr);worked=False
                stop.wait(.05 if worked else .5)
        finally:service.runtime.stopped('worker')
    thread=threading.Thread(target=worker,name='extraction-worker',daemon=True);thread.start()
    def poll_worker():
        while not stop.is_set():
            try:worked=service.run_one_poll_job()
            except Exception:
                print('Poll worker could not store an outcome. It will not repeat a running API call.',file=sys.stderr)
                worked=False
            stop.wait(.05 if worked else .5)
    poll_thread=threading.Thread(target=poll_worker,name='poll-worker',daemon=True);poll_thread.start()
    def document_worker():
        while not stop.is_set():
            try:worked=service.run_one_document_job()
            except Exception:
                print('Document worker could not store an outcome. Running API calls will not be repeated.',file=sys.stderr)
                worked=False
            stop.wait(.05 if worked else .5)
    document_thread=threading.Thread(target=document_worker,name='document-worker',daemon=True);document_thread.start()
    def summary_worker():
        while not stop.is_set():
            try: worked=service.run_one_summary_job()
            except Exception:
                print('Summary worker could not save an outcome. Review its pending batch.',file=sys.stderr)
                worked=False
            stop.wait(.1 if worked else 1)
    summary_thread=threading.Thread(target=summary_worker,name='summary-worker',daemon=True);summary_thread.start()
    def maintenance():
        try:
            while not stop.is_set():
                service.runtime.begin('maintenance')
                try:
                    service.sweep();service.runtime.succeeded('maintenance')
                except Exception:
                    service.runtime.failed('maintenance')
                    print('Lifecycle sweep failed; will retry.',file=sys.stderr)
                stop.wait(1)
        finally:service.runtime.stopped('maintenance')
    maintenance_thread=threading.Thread(target=maintenance,name='lifecycle-worker',daemon=True);maintenance_thread.start()
    print(f'GenAI backend bound to {args.bind}:{server.server_port}',flush=True)
    print(f'Image adapter: {args.extractor}. Transcriber: {args.transcriber}. Speaker ID: {args.speaker_id}. '
          f'Poll AI: {"cloud text interpretation enabled" if poll_model else poll_notice}. '
          f'Document AI: {"whole-meeting text interpretation enabled" if document_model else document_notice}. '
          + ('Photo regions are sent to Anthropic. ' if args.extractor == 'claude' else 'Photo reader is a labelled fixture. ')
          + 'HTTP traffic is not encrypted.', flush=True)
    try:server.serve_forever(poll_interval=.2)
    except KeyboardInterrupt:pass
    finally:
        stop.set();service.runtime.stopped('worker');service.runtime.stopped('maintenance')
        server.server_close();thread.join(timeout=2);maintenance_thread.join(timeout=2);poll_thread.join(timeout=22);document_thread.join(timeout=22);summary_thread.join(timeout=2);lock.close()


if __name__=='__main__':main()
