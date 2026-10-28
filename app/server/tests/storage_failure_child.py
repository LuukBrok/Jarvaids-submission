#!/usr/bin/env python3
"""Make a write fail at the operating system, and report what survived.

A subprocess because RLIMIT_FSIZE cannot be raised once lowered. Prints one
line of JSON on stdout for the parent test to read.

Closer to a full disk than a SQLite trigger is: the kernel refuses the write,
so SQLite meets the failure the way it would on a disk with nothing left.
"""
import json
import resource
import secrets
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from genai_server.service import Service
from genai_server.validation import Problem


def snapshot_shape(service, sid, token):
    snapshot = service.snapshot(sid, token)
    return sorted((r['id'], r['revision']) for r in snapshot['records'])


def main():
    directory = Path(tempfile.mkdtemp())
    try:
        service = Service(directory / 'state.sqlite3')
        sid, token = secrets.token_hex(16), secrets.token_urlsafe(32)
        service.create_session({'session_id': sid, 'title': 'Workshop',
                                'owner_name': 'Facilitator', 'owner_token': token})

        def cmd(op, payload=None):
            return service.command(sid, token, secrets.token_hex(16), op, payload or {})['result']

        version = service.snapshot(sid, token)['session']['policy_version']
        cmd('consent.acknowledge', {'policy_version': version})
        cmd('session.activate', {'policy_version': version,
                                 'expected_session_revision': service.snapshot(sid, token)['session']['revision']})
        for index in range(5):
            cmd('source.text', {'text': 'Note %d before the disk fills' % index})

        before = snapshot_shape(service, sid, token)
        size = (directory / 'state.sqlite3').stat().st_size

        # Soft limit only, hard limit left alone: a lowered hard limit cannot be
        # raised again, so capping both would make the cleanup below fail.
        # Just above the current file, so the next growth is refused by the kernel.
        _, hard = resource.getrlimit(resource.RLIMIT_FSIZE)
        resource.setrlimit(resource.RLIMIT_FSIZE, (size + 4096, hard))

        write_failed = False
        for index in range(200):
            try:
                cmd('source.text', {'text': 'Note %d, written against a full disk. %s'
                                    % (index, 'x' * 2000)})
            except Problem:
                # A refusal the service understands is not the failure being
                # provoked here; keep going until the kernel refuses.
                continue
            except Exception:
                write_failed = True
                break

        readable = True
        after = before
        try:
            after = snapshot_shape(service, sid, token)
        except Exception:
            readable = False

        print(json.dumps({'write_failed': write_failed, 'before': before,
                          'after': after, 'readable': readable}))
        return 0
    finally:
        resource.setrlimit(resource.RLIMIT_FSIZE, resource.getrlimit(resource.RLIMIT_FSIZE)[1:] * 2)
        shutil.rmtree(directory, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
