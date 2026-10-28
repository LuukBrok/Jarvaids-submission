#!/usr/bin/env python3
"""One meaning per schema version, checked structurally.

The behaviour of the migration chain is covered by tests: `test_combined_migration.py`
walks both published version-2 histories, and `test_media.py` covers an
unsupported version and an interrupted migration. This checks the thing no
single-branch test can, because it is not a property of one branch.

Two branches each added a migration, each numbered it version 2, and each was
green on its own. The collision only existed in the union. What catches that is
not a test, it is making the number impossible to claim twice without a merge
conflict: `SCHEMA_VERSIONS` in db.py is the registry, and this asserts the
migration chain agrees with it.

    python3 .github/scripts/check_schema_versions.py
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
DB = ROOT / 'app' / 'server' / 'genai_server' / 'db.py'


def fail(message):
    print('FAIL: %s' % message)
    return 1


def main():
    source = DB.read_text(encoding='utf-8')
    problems = 0

    registry = {int(n) for n in re.findall(r'^\s{4}(\d+): ', source, re.M)}
    if not registry:
        return fail('SCHEMA_VERSIONS not found in db.py. It is the registry this checks against.')

    # Every version the chain writes must be claimed in the registry, and no
    # number may be written by two different migrations.
    written = re.findall(r'PRAGMA user_version\s*=\s*(\d+)', source)
    counts = {}
    for value in written:
        counts[int(value)] = counts.get(int(value), 0) + 1

    duplicated = sorted(v for v, n in counts.items() if n > 1)
    if duplicated:
        problems += fail('these versions are written by more than one migration: %s. '
                         'Each number means one schema.' % duplicated)

    unclaimed = sorted(set(counts) - registry)
    if unclaimed:
        problems += fail('the chain writes %s, which SCHEMA_VERSIONS does not describe. '
                         'Claim the number there first.' % unclaimed)

    unused = sorted(registry - set(counts))
    if unused:
        problems += fail('SCHEMA_VERSIONS describes %s, but no migration writes it.' % unused)

    # The accepted set has to admit every version in the registry and nothing
    # beyond it, or an unknown database is either rejected wrongly or, worse,
    # accepted and misread.
    accepted = re.search(r'version not in \(([\d,\s]+)\)', source)
    if not accepted:
        problems += fail('could not find the accepted-version check in db.py.')
    else:
        allowed = {int(n) for n in accepted.group(1).split(',') if n.strip()}
        expected = registry | {0}
        if allowed != expected:
            problems += fail('db.py accepts %s but SCHEMA_VERSIONS plus a fresh database is %s.'
                             % (sorted(allowed), sorted(expected)))

    if problems:
        print('\nA schema version is a promise about what is on disk. Two meanings for '
              'one number is not a merge conflict, it is a database read as the wrong shape.')
        return 1

    print('Schema versions consistent: %s, current %d.' % (sorted(registry), max(registry)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
