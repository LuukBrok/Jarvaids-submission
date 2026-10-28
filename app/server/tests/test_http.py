import http.client
import json
from pathlib import Path
import secrets
import shutil
import threading
import unittest

from genai_server.http import LocalServer
from genai_server.service import Service


class HTTPTests(unittest.TestCase):
    def setUp(self):
        root=Path(__file__).resolve().parents[1]/'.local'/'http-tests';root.mkdir(parents=True,exist_ok=True)
        self.directory=root/secrets.token_hex(16);self.directory.mkdir()
        assert self.directory.resolve().is_relative_to(root.resolve())
        self.addCleanup(shutil.rmtree,self.directory)
        self.service=Service(self.directory/'state.sqlite3')
        self.server=LocalServer(('127.0.0.1',0),self.service,origins=['http://localhost:5173'])
        self.thread=threading.Thread(target=self.server.serve_forever,kwargs={'poll_interval':.02},daemon=True);self.thread.start()
        self.addCleanup(self.stop)
        self.sid=secrets.token_hex(16);self.token=secrets.token_urlsafe(32)

    def stop(self):self.server.shutdown();self.server.server_close();self.thread.join(2)

    def request(self,method,path,body=None,headers=None,raw=None):
        conn=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=3)
        payload=raw if raw is not None else json.dumps(body).encode() if body is not None else None
        h={'Content-Type':'application/json','Authorization':'Bearer '+self.token,**(headers or {})}
        try:
            conn.request(method,path,body=payload,headers=h);res=conn.getresponse();data=res.read()
            return res.status,dict(res.getheaders()),json.loads(data) if res.getheader('Content-Type','').startswith('application/json') else data
        finally:conn.close()

    def create(self):
        return self.request('POST','/api/sessions',{'session_id':self.sid,'owner_token':self.token,'title':'API workshop','owner_name':'Owner'})

    def command(self,operation,payload,key=None):
        payload=dict(payload)
        if operation=='session.activate':payload.setdefault('expected_session_revision',self.service.snapshot(self.sid,self.token)['session']['revision'])
        key=key or secrets.token_hex(16);body={'operation':operation,'payload':payload}
        if operation in self.service.CONTROL_COMMANDS:
            if not hasattr(self,'control_intents'):self.control_intents={}
            body['control_sequence']=self.control_intents.setdefault(key,self.service.snapshot(self.sid,self.token)['next_control_sequence'])
        return self.request('POST',f'/api/sessions/{self.sid}/commands',body,{'X-Request-ID':key})

    def activate(self):
        self.assertEqual(201,self.create()[0])
        self.assertEqual(200,self.command('consent.acknowledge',{'policy_version':1})[0])
        self.assertEqual(200,self.command('session.activate',{'policy_version':1})[0])

    def test_full_http_workflow_with_idempotency_download_and_delete(self):
        self.activate();key=secrets.token_hex(16)
        status,headers,data=self.command('source.text',{'text':'A real typed note'},key)
        self.assertEqual(200,status);self.assertEqual('no-store',headers['Cache-Control'])
        proposal=data['result']['proposal'];source=data['result']['source']
        self.assertTrue(self.command('source.text',{'text':'A real typed note'},key)[2]['replayed'])
        status,_,accepted=self.command('proposal.review',{'proposal_id':proposal['id'],'expected_revision':1,'decision':'accept'})
        self.assertEqual(200,status)
        status,_,export=self.command('export.create',{'include_unresolved':False});eid=export['result']['id']
        status,headers,markdown=self.request('GET',f'/api/sessions/{self.sid}/exports/{eid}?format=markdown')
        self.assertEqual(200,status);self.assertIn(b'A real typed note',markdown);self.assertIn('attachment',headers['Content-Disposition'])
        events=self.request('GET',f'/api/sessions/{self.sid}/events?after=0')[2]
        self.assertGreater(events['current_seq'],0)
        self.assertEqual(200,self.request('DELETE',f'/api/sessions/{self.sid}')[0])
        self.assertEqual('deleted',self.request('GET',f'/api/sessions/{self.sid}')[2]['state'])
        self.assertEqual(401,self.request('GET',f'/api/sessions/{self.sid}/records/{source["id"]}')[0])

    def test_join_without_facilitator_credential_and_revoke_access(self):
        self.activate();capability=secrets.token_urlsafe(32);guest=secrets.token_urlsafe(32)
        status,_,issued=self.command('participant.invite',{'invitation':capability,'expected_roster_revision':1})
        self.assertEqual(200,status)
        status,_,joined=self.request('POST',f'/api/sessions/{self.sid}/join',
            {'invitation':capability,'token':guest,'name':'Guest','policy_version':1},{'Authorization':''})
        self.assertEqual(200,status)
        self.assertEqual(200,self.request('GET',f'/api/sessions/{self.sid}',headers={'Authorization':'Bearer '+guest})[0])
        status,_,_=self.command('participant.remove',{'actor_id':joined['actor_id'],'expected_roster_revision':3})
        self.assertEqual(200,status)
        self.assertEqual(401,self.request('GET',f'/api/sessions/{self.sid}',headers={'Authorization':'Bearer '+guest})[0])

    def test_lan_host_configuration_remains_exact(self):
        configured=LocalServer(('0.0.0.0',0),self.service,advertised_hosts=['192.0.2.1'])
        try:
            self.assertIn(f'192.0.2.1:{configured.server_port}',configured.allowed_hosts)
            self.assertNotIn(f'evil.example:{configured.server_port}',configured.allowed_hosts)
            self.assertNotIn(f'0.0.0.0:{configured.server_port}',configured.allowed_hosts)
        finally:configured.server_close()
        for origin in ('https://user:secret@example.com','https://example.com/path','https://example.com?x=1','https://example.com#fragment'):
            with self.assertRaises(ValueError):LocalServer(('127.0.0.1',0),self.service,origins=[origin])

    def test_health_is_explicit_about_fixture(self):
        status,_,body=self.request('GET','/health');self.assertEqual(200,status)
        self.assertEqual('fixture',body['adapter']);self.assertFalse(body['live_ocr'])

    def test_health_reports_a_real_reader_as_live(self):
        class Reader:name='claude'
        self.service.extractor=Reader()
        status,_,body=self.request('GET','/health');self.assertEqual(200,status)
        self.assertEqual('claude',body['adapter']);self.assertTrue(body['live_ocr'])

    def test_disallowed_browser_origin_cannot_create(self):
        status,headers,body=self.request('POST','/api/sessions',{},headers={'Origin':'https://untrusted.example'})
        self.assertEqual(403,status);self.assertNotIn('Access-Control-Allow-Origin',headers)
        self.assertEqual('origin_denied',body['error']['code'])

    def test_allowed_origin_and_preflight(self):
        status,headers,_=self.request('OPTIONS','/api/sessions',headers={'Origin':'http://localhost:5173'})
        self.assertEqual(204,status);self.assertEqual('http://localhost:5173',headers['Access-Control-Allow-Origin'])
        self.assertIn('X-Request-ID',headers['Access-Control-Allow-Headers'])

    def test_dns_rebinding_host_rejected(self):
        self.assertEqual(403,self.request('GET','/health',headers={'Host':'attacker.example'})[0])

    def test_missing_credentials_rejected(self):
        self.create()
        self.assertEqual(401,self.request('GET',f'/api/sessions/{self.sid}',headers={'Authorization':''})[0])

    def test_invalid_json_and_duplicate_keys_rejected(self):
        for raw in (b'not json',b'{"x":1,"x":2}',b'{"x":NaN}',b'{"x":Infinity}',b'\xff'):
            self.assertEqual(400,self.request('POST','/api/sessions',raw=raw)[0])

    def test_json_type_validation_is_not_internal_error(self):
        self.create()
        for body in ([],{}, {'operation':[],'payload':{}},{'operation':'source.text','payload':[]}):
            code=self.request('POST',f'/api/sessions/{self.sid}/commands',body,{'X-Request-ID':secrets.token_hex(16)})[0]
            self.assertIn(code,(404,422))

    def test_command_key_and_unknown_fields_required(self):
        self.create()
        status,_,body=self.request('POST',f'/api/sessions/{self.sid}/commands',{'operation':'session.pause','payload':{}})
        self.assertEqual(422,status);self.assertEqual('invalid_id',body['error']['code'])
        self.assertEqual(422,self.command('session.pause',{'unexpected':True})[0])

    def test_json_content_type_and_body_limit(self):
        self.assertEqual(415,self.request('POST','/api/sessions',{},headers={'Content-Type':'text/plain'})[0])
        self.assertEqual(413,self.request('POST','/api/sessions',raw=b'{}',headers={'Content-Length':str(7*1024*1024)})[0])

    def test_strict_cursors_and_routes(self):
        self.create()
        self.assertEqual(400,self.request('GET',f'/api/sessions/{self.sid}/events?after=-1')[0])
        self.assertEqual(400,self.request('GET',f'/api/sessions/{self.sid}/events?after=1&after=2')[0])
        self.assertEqual(404,self.request('GET','/missing')[0])

    def test_local_only_binding(self):
        with self.assertRaises(ValueError):LocalServer(('0.0.0.0',0),self.service)


if __name__=='__main__':unittest.main()
