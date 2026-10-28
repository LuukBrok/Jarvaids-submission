"""Run the combined localhost checks; logs stay private under .local/verification."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from local_test import python_at, runtime_default

if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = Path(__file__).resolve().parents[1]
GUARDS = ['mutation', 'media_mutation', 'isolated_mutation', 'schema_mutation',
          'runtime_mutation', 'synthesis_mutation', 'extractor_mutation',
          'client_mutation', 'poll_mutation', 'document_mutation',
          'requirements_mutation', 'calendar_mutation', 'automatic_mutation', 'summary_mutation']
BROWSERS = ['summary-browser', 'command-menu-browser', 'journey', 'command-recognition-browser', 'speaker-enrollment-browser',
            'wakeword-listen-browser', 'canvas-objects-browser',
            'canvas-objects-server-browser', 'canvas-browser', 'header-browser',
            'rail-browser', 'strip-browser', 'quote-browser', 'parked-browser',
            'threads-browser', 'poll-browser', 'document-browser',
            'requirements-browser', 'command-layout-browser', 'calendar-browser', 'automatic-workspace-browser']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('suite', choices=['backend', 'guards', 'contracts', 'browser', 'all'])
    parser.add_argument('--python', type=Path, default=python_at(runtime_default()))
    parser.add_argument('--only', nargs='+', help='Run only these named checks within the selected suite.')
    args = parser.parse_args()
    python = args.python.resolve()
    if not python.is_file():
        parser.error('Run Setup Jarvaids.cmd first, or select the test runtime with --python.')
    logs = ROOT / '.local/verification' / args.suite
    logs.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1', JARVAIDS_TEST_PYTHON=str(python))
    env['PATH'] = str(python.parent) + os.pathsep + env['PATH']
    if os.name == 'nt':
        # A venv's Windows redirector launches another python.exe; terminating
        # that redirector leaves its HTTP server holding the port/database.
        details = json.loads(subprocess.check_output([str(python), '-c',
            'import json,sys,site,sysconfig;print(json.dumps([sys._base_executable,[sysconfig.get_path("stdlib"),*site.getsitepackages()]]))'], text=True))
        env['JARVAIDS_TEST_PYTHON'] = details[0]
        env['PYTHONPATH'] = os.pathsep.join(details[1] + ([env['PYTHONPATH']] if env.get('PYTHONPATH') else []))

    checks = []
    # Mutation scratch paths under a long OneDrive checkout exceed Windows' SQLite
    # filename limit. Copy code only, never .env, recordings or session databases.
    target = Path(tempfile.mkdtemp(prefix='jvc-'))
    shutil.copytree(ROOT / 'app', target / 'app', ignore=shutil.ignore_patterns(
        '.local', '__pycache__', '*.pyc', 'node_modules', '.venv', 'venv', 'wakeword-training'))
    for part in ['.github/scripts', 'deliverables/documentation']:
        shutil.copytree(ROOT / part, target / part)
    (logs / 'snapshot.txt').write_text(str(target), encoding='utf-8')
    print(f'Code-only snapshot: {target}', flush=True)
    server = target / 'app/server'
    if args.suite in ('backend', 'all'):
        checks.append(('backend', [str(python), '-B', '-m', 'unittest', 'discover', '-s', 'tests'], server))
    if args.suite in ('guards', 'all'):
        checks.extend((name, [str(python), '-B', f'tests/{name}_check.py'], server) for name in GUARDS)
    if args.suite in ('contracts', 'all'):
        units = sorted((ROOT / 'app/client/tests').glob('*-unit.mjs'))
        units += sorted((ROOT / 'app/server/tests').glob('*-unit.mjs'))
        checks.append(('javascript-units', ['node', '--test', '--test-isolation=none', *map(str, units)], ROOT))
        checks.extend((name, [str(python), '-B', filename], cwd) for name, filename, cwd in [
            ('client-http', 'tests/client_http_check.py', server),
            ('sync-budget', 'tests/measure_sync.py', server),
            ('schema', '.github/scripts/check_schema_versions.py', target),
            ('proposal', 'deliverables/documentation/check_proposal.py', target)])
    if args.suite in ('browser', 'all'):
        checks.extend((name, ['node', f'app/client/tests/{name}.mjs'], ROOT) for name in BROWSERS)
    if args.only:
        unknown = set(args.only) - {check[0] for check in checks}
        if unknown:
            parser.error('Unknown checks for this suite: ' + ', '.join(sorted(unknown)))
        checks = [check for check in checks if check[0] in args.only]
    results = []
    for name, command, cwd in checks:
        print(f'Running {name}...', flush=True)
        try:
            result = subprocess.run(command, cwd=cwd, env=env, capture_output=True,
                                    text=True, encoding='utf-8', errors='replace', timeout=1200)
            output = result.stdout + result.stderr
            code = result.returncode
            if name in BROWSERS and 'SKIP:' in output:
                code = 1
        except (OSError, subprocess.TimeoutExpired) as error:
            output, code = str(error), 1
        (logs / f'{name}.log').write_text(output, encoding='utf-8')
        results.append({'check': name, 'exit_code': code})
        (logs / 'results.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
        print(f'{name}: {"PASS" if code == 0 else "FAIL"}', flush=True)
        if code:
            print(output[-3000:], flush=True)
    print(f'Logs: {logs}\nCode-only verification snapshot: {target}', flush=True)
    return int(any(result['exit_code'] for result in results))


if __name__ == '__main__':
    sys.exit(main())
