#!/usr/bin/env python3
"""Operational numbers, and the machine they came from.

INT09 asks for shutdown, recovery, retention and resource-pressure exercises to
record their results on named hardware. This records them and names the machine,
which is the part that matters: the same script on a five-year-old laptop will
print different numbers, and a figure without its machine is not evidence.

    python3 tests/measure_operations.py

Nothing here asserts. The refusals these numbers describe are tested in
`tests/test_operations.py`; this exists so the numbers can be quoted and
re-measured rather than remembered.
"""
import json
import platform
import secrets
import shutil
import subprocess
import sqlite3
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import http.client

from genai_server.http import LocalServer
from genai_server.service import Service


def machine():
    """What this ran on. Read from the system rather than declared."""
    facts = {'python': platform.python_version(),
             'system': '%s %s' % (platform.system(), platform.release()),
             'machine': platform.machine()}
    try:
        for line in Path('/proc/cpuinfo').read_text().splitlines():
            if line.startswith('model name'):
                facts['cpu'] = line.split(':', 1)[1].strip()
                break
        facts['cpus'] = sum(1 for line in Path('/proc/cpuinfo').read_text().splitlines()
                            if line.startswith('processor'))
        for line in Path('/proc/meminfo').read_text().splitlines():
            if line.startswith('MemTotal'):
                facts['memory_mib'] = int(line.split()[1]) // 1024
                break
    except OSError:
        facts['cpu'] = 'unknown'
    return facts


def slot_recovery():
    """How long a slot stays held by a connection that went quiet.

    At the shipped settings, not the test's reduced ones, because the question
    is what a real room would see.
    """
    directory = Path(tempfile.mkdtemp())
    service = Service(directory / 'state.sqlite3')
    server = LocalServer(('127.0.0.1', 0), service)
    thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .02}, daemon=True)
    thread.start()
    held = []
    try:
        for _ in range(server.slot_count):
            conn = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
            conn.request('GET', '/health')
            conn.getresponse().read()
            held.append(conn)

        refused = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
        refused.request('GET', '/health')
        status = refused.getresponse().status
        refused.close()

        began = time.monotonic()
        recovered = None
        while time.monotonic() - began < server.idle_timeout * 3:
            probe = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
            try:
                probe.request('GET', '/health')
                if probe.getresponse().status == 200:
                    recovered = time.monotonic() - began
                    probe.close()
                    break
            except (http.client.HTTPException, OSError):
                pass
            probe.close()
            time.sleep(0.2)
        return {'slots': server.slot_count, 'idle_timeout_s': server.idle_timeout,
                'status_at_ceiling': status,
                'recovery_s': None if recovered is None else round(recovered, 1)}
    finally:
        for conn in held:
            conn.close()
        server.shutdown()
        server.server_close()
        thread.join(2)
        shutil.rmtree(directory, ignore_errors=True)


def retained_after_deletion():
    """What a deleted session leaves behind, per session, for ever.

    The purge empties every content table, and the sessions row stays so the
    facilitator's receipt can still be read. That row is the growth: it is
    bounded per session but never reclaimed, so it is worth knowing its size.
    """
    directory = Path(tempfile.mkdtemp())
    try:
        path = directory / 'state.sqlite3'
        service = Service(path)
        sessions = 5
        for _ in range(sessions):
            sid, token = secrets.token_hex(16), secrets.token_urlsafe(32)
            service.create_session({'session_id': sid, 'title': 'Workshop',
                                    'owner_name': 'F', 'owner_token': token})

            def cmd(op, payload=None):
                return service.command(sid, token, secrets.token_hex(16), op, payload or {})['result']

            version = service.snapshot(sid, token)['session']['policy_version']
            cmd('consent.acknowledge', {'policy_version': version})
            cmd('session.activate', {'policy_version': version,
                                     'expected_session_revision': service.snapshot(sid, token)['session']['revision']})
            for index in range(20):
                cmd('source.text', {'text': 'Note %d of a meeting that is over' % index})
            service.delete_session(sid, token)

        with sqlite3.connect(path) as conn:
            rows = conn.execute('SELECT count(*) FROM sessions').fetchone()[0]
            retained = conn.execute(
                'SELECT coalesce(sum(length(CAST(id AS BLOB))+length(CAST(title AS BLOB))'
                '+length(CAST(coalesce(deletion_hash,"") AS BLOB))),0) FROM sessions').fetchone()[0]
            leftover = {table: conn.execute('SELECT count(*) FROM %s' % table).fetchone()[0]
                        for table in ('records', 'versions', 'events', 'requests', 'actors',
                                      'positions', 'media')}
        return {'sessions_deleted': sessions, 'session_rows_kept': rows,
                'receipt_bytes_total': retained,
                'receipt_bytes_each': round(retained / max(rows, 1)),
                'content_rows_left': leftover,
                'file_bytes': path.stat().st_size}
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def child(script, *args):
    done = subprocess.run([sys.executable, '-B', str(Path(__file__).resolve().parent / script), *args],
                          capture_output=True, text=True, timeout=300,
                          cwd=Path(__file__).resolve().parents[1])
    if done.returncode:
        return {'error': (done.stdout + done.stderr).strip().splitlines()[-1:]}
    return json.loads(done.stdout.strip().splitlines()[-1])


def main():
    facts = machine()
    print('Measured on')
    for key in sorted(facts):
        print('  %-12s %s' % (key, facts[key]))

    print('\nConnection slots under keep-alive')
    slots = slot_recovery()
    print('  %d slots, %ds idle timeout. At the ceiling a new connection gets %s.'
          % (slots['slots'], slots['idle_timeout_s'], slots['status_at_ceiling']))
    print('  A slot came back after %s seconds of idleness.'
          % ('no' if slots['recovery_s'] is None else slots['recovery_s']))

    print('\nMemory under concurrent image intake')
    directory = Path(tempfile.mkdtemp())
    try:
        memory = child('memory_pressure_child.py', str(directory))
        print('  %s of %s uploads of %s MiB each, peak RSS %s MiB.'
              % (memory.get('uploaded'), memory.get('attempted'),
                 memory.get('encoded_mib'), memory.get('peak_mib')))
    finally:
        shutil.rmtree(directory, ignore_errors=True)

    print('\nA write that fails at the operating system')
    failure = child('storage_failure_child.py')
    if 'error' in failure:
        print('  could not run: %s' % failure['error'])
    else:
        print('  Write refused by the kernel: %s. Session unchanged: %s. Still readable: %s.'
              % (failure['write_failed'], failure['before'] == failure['after'], failure['readable']))

    print('\nWhat a deleted session leaves behind')
    kept = retained_after_deletion()
    print('  %d sessions created, filled and deleted.' % kept['sessions_deleted'])
    print('  %d session rows kept, about %d bytes each, for the deletion receipt.'
          % (kept['session_rows_kept'], kept['receipt_bytes_each']))
    print('  Content rows left: %s' % ', '.join('%s %d' % (k, v) for k, v in sorted(kept['content_rows_left'].items())))
    print('  Database file after all five deletions: %d bytes.' % kept['file_bytes'])
    print('  The file does not shrink: freed pages stay in it, overwritten rather than')
    print('  returned to the filesystem. That the words are really gone from those bytes')
    print('  is asserted in test_deleted_words_are_not_left_in_the_database_file.')

    print('\nThese are one container, not the team\'s hardware. Re-run this on the '
          'machine a claim is being made about.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
