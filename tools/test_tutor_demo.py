"""Local reader boundaries, credential isolation and public file routing."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

from tutor_demo import DemoServer

SID = 'a' * 32
SECRET = 'private-owner-' + 'b' * 50


class Backend(BaseHTTPRequestHandler):
    requests = []

    def log_message(self, *args):
        pass

    def do_GET(self):
        self.requests.append((self.path, self.headers.get('Authorization')))
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"session":{"state":"closed"}}')


class TutorDemoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        for name in ('.local/watch-test', 'app/client', 'evidence/raw/Jarvaids-showcase-20261027'):
            (root / name).mkdir(parents=True)
        (root / '.local/watch-test/private-session.json').write_text(json.dumps({'session_id': SID, 'owner_token': SECRET}))
        (root / 'app/client/index.html').write_text('<html><head></head><body>native client</body></html>')
        (root / 'app/client/app.mjs').write_text('export const client=true;')
        (root / 'evidence/raw/Jarvaids-showcase-20261027/index.html').write_text('saved showcase')
        Backend.requests = []
        self.api = ThreadingHTTPServer(('127.0.0.1', 0), Backend)
        self.server = DemoServer(('127.0.0.1', 0), root, f'http://127.0.0.1:{self.api.server_port}')
        self.threads = [threading.Thread(target=s.serve_forever, daemon=True) for s in (self.api, self.server)]
        for thread in self.threads:
            thread.start()
        self.base = f'http://127.0.0.1:{self.server.server_port}'
        self.opener = build_opener(ProxyHandler({}))

    def tearDown(self):
        for server in (self.server, self.api):
            server.shutdown()
            server.server_close()
        for thread in self.threads:
            thread.join()
        self.temp.cleanup()

    def get(self, path, headers=None, method='GET'):
        try:
            response = self.opener.open(Request(self.base + path, headers=headers or {}, method=method), timeout=3)
        except HTTPError as error:
            response = error
        with response:
            return response.status, response.read().decode('utf-8')

    def test_native_completed_page_connects_without_exposing_owner_credential(self):
        code, html = self.get('/completed/')
        self.assertEqual(code, 200)
        self.assertIn('<base href="/client/">', html)
        self.assertIn('connectSession', html)
        self.assertIn(SID, html)
        self.assertNotIn(SECRET, html)
        self.assertNotIn('localStorage', html)

    def test_read_forwarding_is_limited_to_one_session_and_uses_private_credential(self):
        code, body = self.get(f'/completed-api/api/sessions/{SID}?since_seq=7')
        self.assertEqual(code, 200)
        self.assertEqual(Backend.requests, [(f'/api/sessions/{SID}?since_seq=7', 'Bearer ' + SECRET)])
        self.assertNotIn(SECRET, body)
        self.assertEqual(self.get('/completed-api/api/sessions/' + 'c' * 32)[0], 403)
        self.assertEqual(len(Backend.requests), 1)

    def test_all_mutation_methods_are_refused_before_forwarding(self):
        for method in ('POST', 'DELETE', 'PATCH', 'PUT'):
            self.assertEqual(self.get(f'/completed-api/api/sessions/{SID}/commands', method=method)[0], 405)
        self.assertEqual(Backend.requests, [])

    def test_private_files_and_traversal_are_not_public(self):
        for path in ('/.local/watch-test/private-session.json', '/client/../../.local/watch-test/private-session.json',
                     '/showcase/%2e%2e/%2e%2e/.local/watch-test/private-session.json'):
            code, body = self.get(path)
            self.assertEqual(code, 404)
            self.assertNotIn(SECRET, body)
        self.assertEqual(self.get('/client/app.mjs')[0], 200)
        self.assertEqual(self.get('/showcase/'), (200, 'saved showcase'))

    def test_foreign_host_and_origin_are_refused(self):
        self.assertEqual(self.get('/completed/', {'Host': 'example.com'})[0], 403)
        self.assertEqual(self.get('/completed/', {'Origin': 'https://example.com'})[0], 403)
        self.assertEqual(Backend.requests, [])


if __name__ == '__main__':
    unittest.main()
