"""Install or run the localhost prototype, with local speech and optional cloud interpretation."""
import argparse
import json
import hashlib
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.request import ProxyHandler, build_opener
import venv
import webbrowser
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def runtime_default():
    # Keep dependencies off the long OneDrive project path: ONNX package
    # filenames otherwise exceed Windows' legacy path-length limit.
    if os.name == 'nt':
        return Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local')) / 'JarvaidsLiveTest'
    return Path(os.environ.get('XDG_CACHE_HOME', Path.home() / '.cache')) / 'jarvaids-live-test'


def python_at(runtime):
    return runtime / 'venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def checked(args, **options):
    subprocess.run([str(a) for a in args], check=True, **options)


def install_wakeword_package(package, runtime):
    target = runtime / 'models/wakeword'
    with zipfile.ZipFile(package) as archive:
        manifest = json.loads(archive.read('manifest.json'))
        assets = []
        for key in ('keyword', 'melspectrogram', 'embedding'):
            entry = manifest['assets'][key]
            name = entry['file']
            if Path(name).name != name or '/' in name or '\\' in name or not name.endswith('.onnx'):
                raise ValueError('Invalid wake-word asset path.')
            payload = archive.read(name)
            if hashlib.sha256(payload).hexdigest() != entry['sha256']:
                raise ValueError('Wake-word asset checksum mismatch.')
            assets.append((name, payload))
        target.mkdir(parents=True, exist_ok=True)
        for name, payload in assets:
            (target / name).write_bytes(payload)
        (target / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')


def setup(runtime, wakeword_package=None):
    if sys.version_info < (3, 12):
        raise SystemExit('The full speaker runtime requires Python 3.12 or newer; use the tested Python 3.12 setup.')
    runtime.mkdir(parents=True, exist_ok=True)
    python = python_at(runtime)
    venv.EnvBuilder(with_pip=True).create(runtime / 'venv')
    checked([python, '-m', 'pip', 'install', '-r', ROOT / 'app/server/requirements.txt',
             '-r', ROOT / 'app/server/requirements-whisper.txt',
             '-r', ROOT / 'app/server/requirements-claude.txt'])
    checked([python, '-m', 'pip', 'install', 'torch==2.14.1',
             '--index-url', 'https://download.pytorch.org/whl/cpu'])
    checked([python, '-m', 'pip', 'install', 'librosa==1.0.0', 'scipy==1.18.1',
             'webrtcvad-wheels==2.0.14.post1', 'typing'])
    # Windows wheel supplies the same webrtcvad import without a C++ build.
    # Resemblyzer's old dependency name still requests a source-only package,
    # so install its explicitly provided runtime dependencies first.
    checked([python, '-m', 'pip', 'install', '--no-deps', 'resemblyzer==0.1.4', 'openwakeword==0.6.0'])
    checked([python, '-c', 'from resemblyzer import VoiceEncoder; VoiceEncoder(device="cpu"); print("Speaker encoder ready.")'])
    if wakeword_package:
        install_wakeword_package(wakeword_package, runtime)
    model = runtime / 'models/whisper-base'
    # Download weights once. The subsequent start command only loads this
    # directory; it does not implicitly fall back to a fixture transcriber.
    checked([python, '-c',
        "from huggingface_hub import snapshot_download; "
        "from faster_whisper import WhisperModel; import sys; "
        "snapshot_download('Systran/faster-whisper-base',local_dir=sys.argv[1],"
        "allow_patterns=['config.json','model.bin','tokenizer.json','vocabulary.*']); "
        "WhisperModel(sys.argv[1],device='cpu',compute_type='int8',cpu_threads=2); "
        "print('Speech model ready.')", model])
    print('Setup complete. Run Start Jarvaids.cmd, or: python tools/local_test.py start')


def port_available(port):
    with socket.socket() as sock:
        try:
            sock.bind(('127.0.0.1', port))
        except OSError:
            raise SystemExit(f'Port {port} is already in use. Stop the previous test first.')


def start(args, runtime):
    python = python_at(runtime)
    model = runtime / 'models/whisper-base'
    if not python.is_file() or not (model / 'model.bin').is_file():
        raise SystemExit('Run Setup Jarvaids.cmd first, or: python tools/local_test.py setup')
    if args.api_port == args.client_port:
        raise SystemExit('API and client ports must be different.')
    port_available(args.api_port)
    port_available(args.client_port)
    data = args.data_dir.resolve()
    data.mkdir(parents=True, exist_ok=True)
    origin = f'http://127.0.0.1:{args.client_port}'
    backend = [python, '-u', '-m', 'genai_server', '--port', str(args.api_port),
               '--data-dir', str(data), '--allow-origin', origin,
               '--transcriber', 'local-whisper', '--whisper-model-size', str(model),
               '--whisper-language', args.language, '--whisper-cpu-threads', '2']
    backend += ['--speaker-id', 'resemblyzer']
    backend += ['--poll-ai', args.poll_ai]
    backend += ['--command-ai', args.command_ai]
    local_summary_ready=(ROOT/'.local/ollama/models/manifests/registry.ollama.ai/library/gemma3/4b').is_file()
    summary_mode=('ollama' if local_summary_ready else 'claude') if args.summary_ai=='auto' else args.summary_ai
    backend += ['--summary-ai', summary_mode]
    backend += ['--automatic-workspace']
    # Whole-wall detection sends the sanitised photograph to the configured reader.
    backend += ['--extractor', args.photo_reader]
    manifest = args.wakeword_manifest or runtime / 'models/wakeword/manifest.json'
    if manifest.is_file():
        backend += ['--wakeword-manifest', str(manifest.resolve())]
    elif args.wakeword_manifest:
        raise SystemExit('The requested wake-word manifest is missing.')
    children = []
    streams = []
    options = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
    try:
        portable=ROOT / '.local/ollama/runtime/ollama.exe'
        if summary_mode == 'ollama' and portable.is_file():
            try:
                with socket.create_connection(('127.0.0.1',11434),timeout=1): pass
            except OSError:
                ollama_env=os.environ.copy()
                ollama_env.update(OLLAMA_HOST='127.0.0.1:11434',OLLAMA_MODELS=str(ROOT/'.local/ollama/models'),OLLAMA_NO_CLOUD='1')
                stream=(data/'ollama.log').open('w',encoding='utf-8');streams.append(stream)
                children.append(subprocess.Popen([str(portable),'serve'],cwd=ROOT,env=ollama_env,stdout=stream,stderr=stream,**options))
        for name, command, cwd in [
            ('backend', backend, ROOT / 'app/server'),
            ('client', [python, '-u', 'serve.py', '--port', str(args.client_port)], ROOT / 'app/client')]:
            stream = (data / f'{name}.log').open('w', encoding='utf-8')
            streams.append(stream)
            children.append(subprocess.Popen([str(a) for a in command], cwd=cwd,
                                             stdout=stream, stderr=stream, **options))
        opener = build_opener(ProxyHandler({}))
        deadline = time.monotonic() + 60
        while True:
            if any(child.poll() is not None for child in children):
                raise RuntimeError(f'A server stopped during startup. See logs in {data}')
            try:
                with opener.open(f'http://127.0.0.1:{args.api_port}/ready', timeout=2) as response:
                    ready = json.load(response)['status'] == 'ready'
                with opener.open(origin + '/client/', timeout=2) as response:
                    ready = ready and response.status == 200
                if ready:
                    break
            except OSError:
                pass
            if time.monotonic() >= deadline:
                raise RuntimeError(f'Startup timed out. See logs in {data}')
            time.sleep(.2)
        url = origin + '/client/' + (f'?api=http://127.0.0.1:{args.api_port}' if args.api_port != 3000 else '')
        # For a custom API port, the visible setup form still lets the user
        # choose its server; the default matches the product's setup field.
        print(f'Jarvaids ready: {url}', flush=True)
        print(f'API: http://127.0.0.1:{args.api_port}; language: {args.language}', flush=True)
        print('Agree > Start capture > Listen. Stop both servers with Ctrl+C.', flush=True)
        print(f'Test checklist: {ROOT / "COMPLETE-LOCAL-TEST.md"}', flush=True)
        print(f"Julie companion prototype: {origin}/explorations/jarvaids-live-canvas/", flush=True)
        if args.check:
            print('Startup check passed; stopping both test servers.', flush=True)
            return
        if not args.no_browser:
            webbrowser.open(url)
        while all(child.poll() is None for child in children):
            time.sleep(.5)
        raise RuntimeError(f'A server stopped. See logs in {data}')
    except KeyboardInterrupt:
        print('\nStopping Jarvaids.')
    finally:
        for child in children:
            if child.poll() is None:
                if os.name == 'nt':
                    # The Windows venv redirector owns another Python process.
                    # Stop only this launcher's child tree, so no server is orphaned.
                    subprocess.run(['taskkill', '/PID', str(child.pid), '/T', '/F'],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    child.terminate()
        for child in children:
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
        for stream in streams:
            stream.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['setup', 'start'])
    parser.add_argument('--runtime-dir', type=Path, default=runtime_default())
    parser.add_argument('--data-dir', type=Path, default=ROOT / '.local/live-test')
    parser.add_argument('--language', default='nl')
    parser.add_argument('--api-port', type=int, default=3000)
    parser.add_argument('--client-port', type=int, default=5173)
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--check', action='store_true', help='Verify startup, then stop both servers.')
    parser.add_argument('--poll-ai', choices=['off', 'auto', 'claude'], default='auto',
                        help='auto uses cloud poll interpretation when configured; off disables cloud polling only.')
    parser.add_argument('--command-ai', choices=['off', 'auto', 'claude'], default='auto',
                        help='auto enables list/calendar interpretation from meeting text when configured; off disables this cloud path.')
    parser.add_argument('--summary-ai', choices=['off','ollama','claude','auto'], default='auto')
    parser.add_argument('--wakeword-package', type=Path, help='Install a local trained-model ZIP during setup.')
    parser.add_argument('--wakeword-manifest', type=Path, help='Optional custom detector manifest for startup.')
    parser.add_argument('--photo-reader', choices=['fixture', 'claude'], default='claude',
                        help='claude detects and reads all sticky notes; needs ANTHROPIC_API_KEY in .env.')
    args = parser.parse_args()
    try:
        if args.command == 'setup':
            setup(args.runtime_dir.resolve(), args.wakeword_package)
        else:
            start(args, args.runtime_dir.resolve())
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        raise SystemExit(str(error))


if __name__ == '__main__':
    main()
