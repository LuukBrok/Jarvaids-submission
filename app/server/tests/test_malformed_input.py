"""J02 / INT04: malformed input gets a specific refusal, never a 500.

Three inputs returned HTTP 500 `internal_error` on merged main, which tells a
client nothing about which field was wrong and implies the outcome may be
uncertain when in fact nothing was written.

Two separate causes, and neither is in the validators:

  A lone surrogate survives `json.loads`, because `"\\ud800"` is a legal JSON
  escape. Nothing complains until something encodes the string, and the first
  thing that does is the idempotency fingerprint, which encodes the whole body
  before any handler or validator sees a field.

  An id of `[1]` reached a set membership test in `item.place` before it was
  validated, and a list is unhashable, so `not in seen` raised TypeError.

State must be unchanged after each refusal, which is the part that matters: a
500 saying the outcome is uncertain, over a request that wrote nothing, teaches
clients to retry things that never happened.
"""
import http.client
import json
import secrets
import shutil
import threading
import unittest
from pathlib import Path

from genai_server.http import LocalServer
from genai_server.service import Service
from genai_server.validation import Problem, text


class MalformedHTTPTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1] / '.local' / 'http-tests'
        root.mkdir(parents=True, exist_ok=True)
        directory = root / secrets.token_hex(16)
        directory.mkdir()
        self.addCleanup(shutil.rmtree, directory)
        self.service = Service(directory / 'state.sqlite3')
        self.server = LocalServer(('127.0.0.1', 0), self.service)
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       kwargs={'poll_interval': .02}, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)
        self.sid = secrets.token_hex(16)
        self.token = secrets.token_urlsafe(32)
        self.conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        self.addCleanup(self.conn.close)

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)

    def post(self, path, body):
        """Body as text, so a test can send JSON no encoder would produce."""
        headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + self.token,
                   'X-Request-ID': secrets.token_hex(16)}
        self.conn.request('POST', path, body.encode('utf-8'), headers)
        response = self.conn.getresponse()
        raw = response.read()
        return response.status, json.loads(raw) if raw else None

    def get(self, path):
        self.conn.request('GET', path, None, {'Authorization': 'Bearer ' + self.token})
        response = self.conn.getresponse()
        return response.status, json.loads(response.read() or b'null')

    def create(self, title='"Workshop"'):
        return self.post('/api/sessions',
                         '{"session_id":"%s","owner_token":"%s","title":%s,"owner_name":"Owner"}'
                         % (self.sid, self.token, title))

    def command(self, body):
        return self.post('/api/sessions/%s/commands' % self.sid, body)

    def activate(self):
        self.assertEqual(201, self.create()[0])
        self.assertEqual(200, self.command(
            '{"operation":"consent.acknowledge","payload":{"policy_version":1}}')[0])
        revision = self.get('/api/sessions/%s' % self.sid)[1]['session']['revision']
        self.assertEqual(200, self.command(json.dumps({
            'operation': 'session.activate',
            'payload': {'policy_version': 1, 'expected_session_revision': revision}})[0:])[0])

    # kills: surrogate-rejected

    def test_a_lone_surrogate_in_a_title_is_a_client_error(self):
        status, body = self.create('"Wall \\ud800 here"')
        self.assertEqual(400, status)
        self.assertEqual('invalid_json', body['error']['code'])
        # 401, not 404: authentication runs before existence, so the API does
        # not reveal whether a session id is real. Either way nothing was
        # created, which is the point here.
        self.assertEqual(401, self.get('/api/sessions/%s' % self.sid)[0],
                         'the refused session must not exist')

    def test_a_lone_surrogate_anywhere_in_the_body_is_refused(self):
        """Including in a key, and in a field no validator would ever read. The
        fingerprint encodes the whole body, so per-field checks would not be
        enough even if every field had one."""
        self.activate()
        for body in ('{"operation":"source.text","payload":{"text":"note \\udfff end"}}',
                     '{"operation":"source.text","payload":{"text":"ok","\\udfff":1}}',
                     '{"operation":"source.\\udc00","payload":{"text":"ok"}}'):
            status, problem = self.command(body)
            self.assertEqual((400, 'invalid_json'), (status, problem['error']['code']), body)
        self.assertEqual([], self.records(), 'nothing was written by any refusal')

    def test_valid_unicode_is_untouched(self):
        """The refusal has to be narrow. Accents, an emoji as a surrogate pair,
        and the same text sent as raw UTF-8 all have to survive, or the fix is
        worse than the defect."""
        self.activate()
        for body in ('{"operation":"source.text","payload":{"text":"caf\\u00e9 na\\u00efve"}}',
                     '{"operation":"source.text","payload":{"text":"note \\ud83d\\ude00 end"}}',
                     json.dumps({'operation': 'source.text',
                                 'payload': {'text': 'café 😀 naïve'}}, ensure_ascii=False)):
            self.assertEqual(200, self.command(body)[0], body)
        self.assertEqual(['café naïve', 'note 😀 end', 'café 😀 naïve'], self.records())

    # kills: placement-id-type

    def test_an_id_of_the_wrong_type_is_a_client_error(self):
        """A list is unhashable, so the set test raised TypeError before the id
        was ever validated."""
        self.activate()
        for value in ('[1]', '{"a":1}', '5', 'null'):
            status, problem = self.command(
                '{"operation":"item.place","payload":{"placements":[{"id":%s,"x":0,"y":0,'
                '"expected_position_revision":0}]}}' % value)
            self.assertEqual((422, 'invalid_id'), (status, problem['error']['code']), value)

    def test_a_non_finite_number_is_still_a_client_error(self):
        """Already handled at the parser, and pinned here so the surrogate work
        above cannot quietly remove it."""
        self.assertEqual(400, self.create('"T"')[0] and self.post(
            '/api/sessions', '{"session_id":"%s","owner_token":"%s","title":"T",'
            '"owner_name":"F","retention_seconds":Infinity}'
            % (secrets.token_hex(16), secrets.token_urlsafe(32)))[0])

    # kills: overflowing-number

    def test_a_number_too_large_for_a_float_is_a_client_error(self):
        """`1e999` is legal JSON and is not the literal `Infinity`, so the
        parser's constant hook never saw it. It parsed to inf, passed the
        handler's type checks, and died at the idempotency fingerprint, which
        refuses non-finite numbers: HTTP 500 over a request that wrote nothing.
        Found by reconciling the J02 tick against the code on 5 October."""
        self.activate()
        before = self.get('/api/sessions/%s' % self.sid)[1]
        for body in ('{"operation":"consent.acknowledge","payload":{"policy_version":1e999}}',
                     '{"operation":"item.place","payload":{"placements":[{"id":"a","x":1e999,"y":0,'
                     '"expected_position_revision":0}]}}',
                     '{"operation":"source.text","payload":{"text":"note"},"extra":-1e999}',
                     # An integer with no exponent goes through parse_int, not
                     # parse_float, and math.isfinite raises OverflowError on it.
                     '{"operation":"source.image","payload":{"mime":"image/png","base64":"AA==",'
                     '"regions":[{"id":"region_aa","box":[1%s,0,1,1]}]}}' % ('0' * 400)):
            status, problem = self.command(body)
            self.assertEqual((400, 'invalid_json'), (status, problem['error']['code']), body)
        after = self.get('/api/sessions/%s' % self.sid)[1]
        self.assertEqual(before['session'], after['session'])
        self.assertEqual(before['records'], after['records'])

    def test_deeply_nested_json_is_a_client_error(self):
        """Five thousand nested arrays fit easily under the body limit and blow
        Python's recursion limit inside the parser. That is caught and refused,
        and this pins it, because the catch is one word in an except tuple."""
        self.activate()
        before = self.get('/api/sessions/%s' % self.sid)[1]
        depth = 5000
        status, problem = self.command('{"operation":"source.text","payload":{"text":"note"},"extra":%s%s}'
                                       % ('[' * depth, ']' * depth))
        self.assertEqual((400, 'invalid_json'), (status, problem['error']['code']))
        self.assertEqual(before['records'], self.get('/api/sessions/%s' % self.sid)[1]['records'])

    # kills: nesting-depth
    def test_nesting_past_the_stated_limit_is_a_client_error(self):
        """A hundred levels is far below any recursion limit, so only the stated
        depth limit refuses it, on every Python version."""
        self.activate()
        depth = 100
        status, problem = self.command('{"operation":"source.text","payload":{"text":"note"},"extra":%s%s}'
                                       % ('[' * depth, ']' * depth))
        self.assertEqual((400, 'invalid_json'), (status, problem['error']['code']))

    def records(self):
        snapshot = self.get('/api/sessions/%s' % self.sid)[1]
        return [r['data']['text'] for r in snapshot['records'] if r['kind'] == 'source']


class ValidatorTests(unittest.TestCase):
    """The same rule for callers that never pass through HTTP, such as the
    demo script and `create_session` called directly."""

    def test_text_refuses_an_unpaired_surrogate(self):
        with self.assertRaises(Problem) as caught:
            text('a \ud800 b', 'title')
        self.assertEqual((422, 'invalid_text'), (caught.exception.status, caught.exception.code))

    def test_text_accepts_everything_that_can_be_written_out(self):
        for value in ('café', 'note 😀 end', 'ascii', 'ελληνικά', '日本語'):
            self.assertEqual(value, text(value, 'title'))


if __name__ == '__main__':
    unittest.main()
