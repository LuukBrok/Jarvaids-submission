"""Run the dependency-free clients against a disposable actual CLI server."""
import subprocess
import sys
from pathlib import Path
from test_runtime_journey import RuntimeJourneyTests

ROOT = Path(__file__).resolve().parents[1]


def main():
    case = RuntimeJourneyTests()
    try:
        case.setUp()
        for command in ([sys.executable, 'demo.py', '--url', case.base],
                        ['node', 'tests/client-smoke.mjs', case.base],
                        ['node', 'tests/client-plumbing-smoke.mjs', case.base]):
            result = subprocess.run(command, cwd=ROOT, capture_output=True,
                                    text=True, encoding='utf-8', timeout=45)
            print(result.stdout, end='')
            if result.returncode:
                print(result.stderr, file=sys.stderr)
                raise RuntimeError('Client HTTP journey failed.')
    finally:
        case.doCleanups()


if __name__ == '__main__':
    main()
