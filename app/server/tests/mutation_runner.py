"""The one place a mutant is actually run.

There are three mutation harnesses, for the service, for media decoding and for
the isolated adapter subprocess. They differ in which file they mutate, which
tests they run and how long they wait. Everything else was the same forty lines
copied three times, which is the failure mode AGENTS.md opens on: two copies of
one thing drift within a week, and nobody diffs them.

What the copies agreed on, and what is preserved here:

- The mutation happens in a throwaway copy of the tree, never in the working
  one. A harness that edits the real file and restores it in a `finally` leaves
  the source mutated when the process is killed, which happened once.
- No bytecode cache. A `.pyc` is validated on source mtime and size, and these
  runs rewrite sources in a loop.
- An error is not a kill. A mutant that makes the suite crash, fail to import
  or collect nothing has not shown that a guard matters; only a named
  assertion failing shows that. Counting a crash as a kill is how a mutation
  harness starts lying.
"""
import os
import re
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FAILED = re.compile(r'^FAIL: (\w+) ', re.M)
ERRORED = re.compile(r'^ERROR: (\w+) ', re.M)


class InfrastructureError(RuntimeError):
    """The run said nothing about the guard, so no verdict can be read from it."""


def run(target=None, source=None, pattern=None, killed_by=None, timeout=180, scratch_name='mutation-runs'):
    """Run the suite against a disposable copy of the tree.

    `target` is a path under genai_server/ to overwrite with `source`; omit both
    for a baseline run. `pattern` narrows discovery to one test file and
    `killed_by` to one test. Returns (passed, failing test names).
    """
    scratch_root = ROOT / '.local' / scratch_name
    scratch_root.mkdir(parents=True, exist_ok=True)
    scratch = scratch_root / secrets.token_hex(16)
    scratch.mkdir()
    try:
        for directory in ('genai_server', 'tests'):
            shutil.copytree(ROOT / directory, scratch / directory,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        if source is not None:
            (scratch / 'genai_server' / target).write_text(source, encoding='utf-8')
        environment = os.environ.copy()
        environment['PYTHONDONTWRITEBYTECODE'] = '1'
        environment.pop('PYTHONPATH', None)
        command = [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests']
        if pattern:
            command += ['-p', pattern]
        if killed_by:
            command += ['-k', killed_by]
        done = subprocess.run(command, cwd=scratch, capture_output=True, text=True,
                              env=environment, timeout=timeout)
        output = done.stdout + done.stderr
        if ERRORED.search(output) or not re.search(r'Ran [1-9]\d* tests?\b', output):
            raise InfrastructureError(
                'Suite infrastructure/test error, not a behavioural kill:\n' + output)
        return done.returncode == 0, set(FAILED.findall(output))
    finally:
        if not scratch.resolve().is_relative_to(scratch_root.resolve()):
            raise RuntimeError('Unsafe scratch cleanup path.')
        shutil.rmtree(scratch, ignore_errors=True)


def check_one_target(target, mutants, pattern, timeout, label):
    """The shape both single-file harnesses use: one file, one test file, each
    mutant killed by the assertion it names.

    `mutants` are (name, killed_by, old, new). Raises on any survivor, so a
    caller is a list of mutants and one call.
    """
    path = ROOT / 'genai_server' / target
    original = path.read_text(encoding='utf-8')
    for name, _, old, _ in mutants:
        if original.count(old) != 1:
            raise RuntimeError('Guard pattern must match exactly once: ' + name)

    passed, _ = run(pattern=pattern, timeout=timeout, scratch_name=label + '-mutations')
    if not passed:
        raise RuntimeError('Baseline failed before any mutation.')
    print('baseline: passed', flush=True)

    for name, killed_by, old, new in mutants:
        passed, failing = run(target=target, source=original.replace(old, new, 1),
                              pattern=pattern, killed_by=killed_by, timeout=timeout,
                              scratch_name=label + '-mutations')
        if passed or killed_by not in failing:
            raise RuntimeError('Named guard survived or failed for another reason: ' + name)
        print(name + ': caught by ' + killed_by, flush=True)

    if path.read_text(encoding='utf-8') != original:
        raise RuntimeError('Original source changed concurrently.')
    print('All %d %s guards caught by their named assertions.' % (len(mutants), label))
    return 0


def check_multi_target(mutants, pattern, timeout, label, noun=None):
    """The shape the schema and runtime harnesses use: mutants that name their
    own target file, because a guard can span two modules.

    `mutants` are (name, target, old, new, killed_by), matching the order those
    harnesses already declared them in, so folding them onto this runner moved
    no mutant text.
    """
    originals = {}
    for name, target, old, _, _ in mutants:
        source = originals.setdefault(target, (ROOT / 'genai_server' / target).read_text(encoding='utf-8'))
        if source.count(old) != 1:
            raise RuntimeError('Mutation must match exactly once: %s in %s' % (name, target))

    passed, _ = run(pattern=pattern, timeout=timeout, scratch_name=label + '-mutations')
    if not passed:
        raise RuntimeError('Baseline failed before any mutation.')

    for name, target, old, new, killed_by in mutants:
        passed, failing = run(target=target, source=originals[target].replace(old, new, 1),
                              pattern=pattern, killed_by=killed_by, timeout=timeout,
                              scratch_name=label + '-mutations')
        if passed or killed_by not in failing:
            raise RuntimeError(name + ' did not fail its named assertion')
        print(name + ': caught by ' + killed_by, flush=True)

    for target, source in originals.items():
        if (ROOT / 'genai_server' / target).read_text(encoding='utf-8') != source:
            raise RuntimeError('Original source changed concurrently: ' + target)
    print('All %d %s guards caught.' % (len(mutants), noun or label))
    return 0



# JavaScript uses TAP rather than unittest text; both require named assertion failures.
def _run_javascript(directory, filename, name=None):
    args=['node','--test','--test-isolation=none','--test-reporter=tap','--test-timeout=2000']
    if name: args += ['--test-name-pattern=^'+re.escape(name)+'$']
    args += ['tests/'+filename]
    return subprocess.run(args,cwd=directory,capture_output=True,text=True,encoding='utf-8',timeout=30)

def check_javascript(cases):
    scratch=ROOT/'.local/client-mutations';scratch.mkdir(parents=True,exist_ok=True)
    directory=scratch/secrets.token_hex(16)
    directory.mkdir()
    try:
        (directory/'tests').mkdir()
        modules=['client.mjs','session-sync.mjs']
        tests=['client-transport-unit.mjs','session-sync-unit.mjs']
        originals={name:(ROOT/name).read_text(encoding='utf-8') for name in modules}
        for name,text in originals.items(): (directory/name).write_text(text,encoding='utf-8')
        for name in tests: shutil.copyfile(ROOT/'tests'/name,directory/'tests'/name)
        for filename in tests:
            baseline=_run_javascript(directory,filename)
            if baseline.returncode: raise RuntimeError('Baseline failed: '+baseline.stdout+baseline.stderr)
        for label,module,name,old,new in cases:
            source=originals[module]
            if source.count(old)!=1: raise RuntimeError('Mutation anchor not unique: '+label)
            (directory/module).write_text(source.replace(old,new),encoding='utf-8')
            filename='client-transport-unit.mjs' if module=='client.mjs' else 'session-sync-unit.mjs'
            result=_run_javascript(directory,filename,name)
            (directory/module).write_text(source,encoding='utf-8')
            if result.returncode == 0 or 'code: \'ERR_ASSERTION\'' not in result.stdout or '# fail 1' not in result.stdout or '# tests 1' not in result.stdout or not re.search(r'^not ok 1 - '+re.escape(name)+r'$',result.stdout,re.M):
                raise RuntimeError('SURVIVED OR INFRASTRUCTURE FAILURE: '+label+'\n'+result.stdout+result.stderr)
            print('KILLED: '+label+' / '+name)
    finally:
        assert directory.resolve().is_relative_to(scratch.resolve())
        shutil.rmtree(directory)
    print(f'PASS: {len(cases)} named client guard mutations, each caught by its specified assertion test.')

