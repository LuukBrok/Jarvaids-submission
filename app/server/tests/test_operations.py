"""INT09: what happens when the machine, rather than the request, is the problem.

Three things nothing exercised. Each is cheap to test and expensive to discover
in a meeting.

**Idle connections holding slots.** Keep-alive made a slot last a whole
connection rather than a single request, so a browser that connects and goes
quiet holds one until its socket times out. With sixteen slots and eight
participants on two devices each, that ceiling is reachable in a real room, not
only under attack. The bound is only worth having if it releases.

**A write that genuinely fails.** Existing store-fault coverage uses SQLite
triggers, which is a fault the database reports. This uses RLIMIT_FSIZE, so the
write fails at the operating system, closer to a disk that is actually full. The
promise in the storage error message is that no partial change was saved, and a
promise in a message is not a tested promise.

**Memory under concurrent images.** Several 4 MiB uploads at once, measured
rather than assumed.

The numbers these record are from one container and are not hardware evidence
for a team's laptops; `tests/measure_operations.py` prints what it ran on.
"""
import http.client
import json
import unittest
try:
    import resource
except ImportError:
    resource = None
import secrets
import shutil
import subprocess
import sys
import threading
from pathlib import Path

from genai_server.http import LocalServer
from genai_server.service import Service


class SlotPressureTests(unittest.TestCase):
    """Two slots rather than sixteen, so the ceiling is reachable in a test.
    The bound is the subject, not the number."""

    def setUp(self):
        root = Path(__file__).resolve().parents[1] / '.local' / 'http-tests'
        root.mkdir(parents=True, exist_ok=True)
        directory = root / secrets.token_hex(16)
        directory.mkdir()
        self.addCleanup(shutil.rmtree, directory)
        self.service = Service(directory / 'state.sqlite3')
        self.server = LocalServer(('127.0.0.1', 0), self.service, slots=2, idle_timeout=1)
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       kwargs={'poll_interval': .02}, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)
        self.open = []

    def stop(self):
        for conn in self.open:
            conn.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)

    def connect(self):
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        self.open.append(conn)
        return conn

    def health(self, conn):
        conn.request('GET', '/health')
        response = conn.getresponse()
        response.read()
        return response.status

    def test_a_connection_that_goes_idle_still_gives_its_slot_back(self):
        """The failure this rules out: two people leave a tab open, the room
        fills the slots, and nothing recovers without restarting the server."""
        held = [self.connect() for _ in range(self.server.slot_count)]
        for conn in held:
            self.assertEqual(200, self.health(conn), 'each connection is served')

        # Every slot is now held by an idle keep-alive connection.
        refused = self.connect()
        refused.request('GET', '/health')
        self.assertEqual(503, refused.getresponse().status,
                         'the ceiling must be refused, not queued indefinitely')

        # The idle timeout is what frees them. Without it the server is wedged.
        deadline = threading.Event()
        for _ in range(60):
            deadline.wait(0.25)
            fresh = self.connect()
            try:
                fresh.request('GET', '/health')
                if fresh.getresponse().status == 200:
                    break
            except (http.client.HTTPException, OSError):
                pass
            fresh.close()
        else:
            self.fail('no slot came back after the idle timeout')

    def test_a_refused_connection_does_not_leak_a_slot(self):
        """A 503 that consumed a slot would turn one burst into a dead server."""
        held = [self.connect() for _ in range(self.server.slot_count)]
        for conn in held:
            self.health(conn)
        for _ in range(5):
            refused = self.connect()
            refused.request('GET', '/health')
            self.assertEqual(503, refused.getresponse().status)
            refused.close()

        held[0].close()
        for _ in range(40):
            threading.Event().wait(0.25)
            fresh = self.connect()
            try:
                fresh.request('GET', '/health')
                if fresh.getresponse().status == 200:
                    return
            except (http.client.HTTPException, OSError):
                pass
            fresh.close()
        self.fail('closing a held connection did not free its slot')


class StorageFailureTests(unittest.TestCase):
    """A write that fails at the operating system, not at a SQLite trigger."""

    @unittest.skipIf(resource is None, "Unix resource limits are unavailable on this platform")
    def test_a_real_write_failure_saves_no_partial_state(self):
        """Runs in a subprocess because RLIMIT_FSIZE cannot be raised again
        once lowered, and killing this interpreter's ability to write files
        would take the rest of the suite with it.

        What is asserted is the promise the storage error already makes in
        words: no partial change was saved.
        """
        script = Path(__file__).resolve().parent / 'storage_failure_child.py'
        done = subprocess.run([sys.executable, '-B', str(script)],
                              capture_output=True, text=True, timeout=120,
                              cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(0, done.returncode,
                         'child reported:\n' + done.stdout + done.stderr)
        report = json.loads(done.stdout.strip().splitlines()[-1])
        self.assertTrue(report['write_failed'], 'the cap did not actually stop a write')
        self.assertEqual(report['before'], report['after'],
                         'a failed write left the session changed')
        self.assertTrue(report['readable'], 'the session was unreadable after a failed write')


class DeletionOnDiskTests(unittest.TestCase):
    """The deletion promise, checked in the file's bytes rather than in a query.

    A purge that empties every table still leaves the pages on disk unless the
    database overwrites them, and the file does not shrink either way. Reading
    the rows back proves the rows are gone; it does not prove the words are.
    This reads the raw file.
    """

    def test_deleted_words_are_not_left_in_the_database_file(self):
        root = Path(__file__).resolve().parents[1] / '.local' / 'tests'
        root.mkdir(parents=True, exist_ok=True)
        directory = root / secrets.token_hex(16)
        directory.mkdir()
        self.addCleanup(shutil.rmtree, directory)

        path = directory / 'state.sqlite3'
        service = Service(path)
        sid, token = secrets.token_hex(16), secrets.token_urlsafe(32)
        marker = 'CONFIDENTIAL' + secrets.token_hex(8).upper()
        service.create_session({'session_id': sid, 'title': 'Workshop',
                                'owner_name': 'Facilitator', 'owner_token': token})

        def cmd(op, payload=None):
            return service.command(sid, token, secrets.token_hex(16), op, payload or {})['result']

        version = service.snapshot(sid, token)['session']['policy_version']
        cmd('consent.acknowledge', {'policy_version': version})
        cmd('session.activate', {'policy_version': version,
                                 'expected_session_revision': service.snapshot(sid, token)['session']['revision']})
        for index in range(10):
            cmd('source.text', {'text': '%s note %d about a named person' % (marker, index)})

        self.assertGreater(path.read_bytes().count(marker.encode()), 0,
                           'the marker should be in the file before deletion')

        service.delete_session(sid, token)

        self.assertEqual(0, path.read_bytes().count(marker.encode()),
                         'deleted text is still readable in the database file')
        # The file does not shrink, and that is expected: the pages are freed
        # and overwritten, not returned to the filesystem. Worth stating so
        # nobody reads the unchanged file size as a failed deletion.
        self.assertGreater(path.stat().st_size, 0)


class MemoryTests(unittest.TestCase):
    @unittest.skipIf(resource is None, "Unix resource memory metrics are unavailable on this platform")
    def test_concurrent_image_uploads_stay_within_a_stated_ceiling(self):
        """Not a tuned number: it is roughly an order of magnitude above what
        four 4 MiB uploads need, so it catches something holding every image in
        memory at once while not failing on ordinary variation."""
        root = Path(__file__).resolve().parents[1] / '.local' / 'http-tests'
        root.mkdir(parents=True, exist_ok=True)
        directory = root / secrets.token_hex(16)
        directory.mkdir()
        self.addCleanup(shutil.rmtree, directory)

        script = Path(__file__).resolve().parent / 'memory_pressure_child.py'
        done = subprocess.run([sys.executable, '-B', str(script), str(directory)],
                              capture_output=True, text=True, timeout=300,
                              cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(0, done.returncode, done.stdout + done.stderr)
        report = json.loads(done.stdout.strip().splitlines()[-1])
        self.assertGreater(report['uploaded'], 0, 'nothing was uploaded')
        self.assertLess(report['peak_mib'], 1024,
                        'peak RSS %d MiB for %d concurrent uploads'
                        % (report['peak_mib'], report['uploaded']))


if __name__ == '__main__':
    unittest.main()
