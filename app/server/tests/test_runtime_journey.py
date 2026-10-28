"""Synthetic HTTP journey against the actual configured server and worker process."""
import base64
from io import BytesIO
import json
import os
from pathlib import Path
import queue
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, build_opener, ProxyHandler

from PIL import Image


class RuntimeJourneyTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        scratch = self.root / '.local/runtime-journeys'
        scratch.mkdir(parents=True, exist_ok=True)
        self.directory = scratch / secrets.token_hex(16)
        self.directory.mkdir()
        def cleanup():
            assert self.directory.resolve().is_relative_to(scratch.resolve())
            shutil.rmtree(self.directory)
        self.addCleanup(cleanup)
        environment = os.environ.copy()
        environment['PYTHONDONTWRITEBYTECODE'] = '1'
        kwargs = {'creationflags':subprocess.CREATE_NO_WINDOW} if sys.platform == 'win32' else {}
        self.process = subprocess.Popen([sys.executable, '-m', 'genai_server', '--port', '0',
            '--data-dir', str(self.directory)], cwd=self.root, env=environment,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, **kwargs)
        def stop():
            if self.process.poll() is None:
                self.process.kill()
            self.process.communicate(timeout=5)
        self.addCleanup(stop)
        started = queue.Queue()
        def first_line():
            started.put(self.process.stdout.readline())
        reader = threading.Thread(target=first_line, daemon=True)
        reader.start()
        try:
            line = started.get(timeout=10)
        except queue.Empty:
            self.fail('Server did not announce its bound address within ten seconds.')
        match = re.search(r'bound to (127\.0\.0\.1:\d+)', line)
        self.assertIsNotNone(match, 'Server failed before announcing its bound address.')
        self.base = 'http://' + match.group(1)
        self.opener = build_opener(ProxyHandler({}))
        self.sid = secrets.token_hex(16)
        self.host = secrets.token_urlsafe(32)
        self.path = '/api/sessions/' + self.sid

    def request(self, method, path, body=None, token=None, key=None, raw=False, status=200):
        headers = {}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        if key:
            headers['X-Request-ID'] = key
        if body is not None:
            headers['Content-Type'] = 'application/json'
        request = Request(self.base + path, method=method, headers=headers,
                          data=None if body is None else json.dumps(body).encode())
        try:
            response = self.opener.open(request, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            data = response.read()
            self.assertEqual(status, response.status, data.decode(errors='replace')[:500])
        return data if raw else json.loads(data)

    def snapshot(self, token=None):
        return self.request('GET', self.path, token=token or self.host)

    def command(self, operation, payload=None, token=None):
        token = token or self.host
        envelope = {'operation': operation, 'payload': payload or {}}
        if operation in {'session.pause', 'session.close', 'session.heartbeat',
                         'participant.remove', 'consent.withdraw', 'invitation.revoke'}:
            envelope['control_sequence'] = self.snapshot(token)['next_control_sequence']
        return self.request('POST', self.path + '/commands', envelope, token,
                            key=secrets.token_hex(16))['result']

    def test_join_capture_review_export_withdraw_delete_over_http(self):
        health = self.request('GET', '/health')
        self.assertEqual('fixture', health['adapter'])
        self.assertFalse(health['live_ocr'])
        self.request('POST', '/api/sessions', {'session_id':self.sid, 'owner_token':self.host,
            'owner_name':'Synthetic host', 'title':'Synthetic runtime journey'}, status=201)
        self.command('consent.acknowledge', {'policy_version':1})
        capability = secrets.token_urlsafe(32)
        self.command('participant.invite', {'invitation':capability,
            'expected_roster_revision':self.snapshot()['session']['roster_revision']})
        guest = secrets.token_urlsafe(32)
        self.request('POST', self.path + '/join', {'invitation':capability, 'token':guest,
            'name':'Synthetic participant', 'policy_version':1})
        self.assertNotIn(guest, json.dumps(self.snapshot()))
        self.command('session.activate', {'policy_version':1,
            'expected_session_revision':self.snapshot()['session']['revision']})
        pixels = BytesIO()
        Image.new('RGB', (8, 4), 'blue').save(pixels, format='PNG')
        source = self.command('source.image', {'mime':'image/png',
            'base64':base64.b64encode(pixels.getvalue()).decode(),
            'regions':[{'id':'region_001','box':[0,0,.5,1]}]}, token=guest)
        job = self.command('extraction.queue', {'source_id':source['id'], 'expected_revision':1}, token=guest)
        deadline = time.monotonic() + 10
        while True:
            current = self.request('GET', self.path + '/records/' + job['id'], token=guest)
            if current['data']['status'] not in ('queued', 'running'):
                break
            if time.monotonic() >= deadline:
                self.fail('Configured worker did not complete the fixture within ten seconds.')
            time.sleep(.05)
        self.assertEqual('succeeded', current['data']['status'])
        proposal_id = current['data']['proposal_ids'][0]
        proposal = self.request('GET', self.path + '/records/' + proposal_id, token=guest)
        self.assertEqual('needs_review', proposal['data']['status'])
        self.assertEqual('fixture', proposal['data']['origin'])
        self.assertTrue(proposal['data']['synthetic'])
        crop = self.request('GET', self.path + '/sources/' + source['id'] + '/regions/region_001?revision=1',
                            token=guest, raw=True)
        with Image.open(BytesIO(crop)) as image:
            self.assertEqual((4, 4), image.size)
        accepted = self.command('proposal.review', {'proposal_id':proposal_id,
            'expected_revision':proposal['revision'], 'decision':'accept'})
        self.assertEqual('accepted', accepted['item']['data']['status'])
        exported = self.command('export.create', {'include_unresolved':False})
        download = self.request('GET', self.path + '/exports/' + exported['id'], token=self.host)
        self.assertIn(accepted['item']['id'], [row['id'] for row in download['records']])
        self.command('source.text', {'text':'Synthetic unresolved note'}, token=guest)
        before = self.snapshot()
        snapshot_export = self.request('POST', self.path + '/export-snapshot',
            {'include_unresolved':True}, token=self.host)
        self.assertEqual({(r['id'], r['kind'], r['revision']) for r in snapshot_export['records']},
                         {(r['id'], r['kind'], r['revision']) for r in snapshot_export['manifest']['included']})
        self.assertGreaterEqual(len(snapshot_export['records']), 2)
        self.assertEqual(before, self.snapshot())
        self.command('consent.withdraw', token=guest)
        self.assertEqual('paused', self.snapshot()['session']['state'])
        self.assertEqual('accepted', self.request('GET', self.path + '/records/' + accepted['item']['id'],
                                                token=self.host)['data']['status'])
        self.request('DELETE', self.path, token=self.host)
        self.assertEqual('deleted', self.snapshot()['state'])
        denied = self.request('GET', self.path, token=guest, status=401)
        self.assertEqual('unauthorized', denied['error']['code'])
