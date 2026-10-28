import base64
from concurrent.futures import ThreadPoolExecutor
import http.client
import json
import secrets
import threading
import unittest

from genai_server.http import LocalServer
from genai_server.validation import Problem
from genai_server.wakeword import BATCH_BYTES, LocalDetector
import test_service


class Detector:
    def __init__(self):
        self.score = 0.9
        self.calls = 0
        self.during = lambda: None

    def predict(self, raw):
        self.calls += 1
        self.during()
        return self.score


class WakewordTests(unittest.TestCase):
    setUp = test_service.ServiceTests.setUp
    cmd = test_service.ServiceTests.cmd
    active = test_service.ServiceTests.active
    invite = test_service.ServiceTests.invite
    problem = test_service.ServiceTests.problem

    def prepare(self):
        self.detector = Detector()
        self.service.wakewords.factory = lambda: self.detector
        self.service.wakewords.clock = lambda: self.now

    def start(self):
        self.stream = self.service.wakeword(self.sid, self.token, 'start', {})['stream_id']
        return self.stream

    def batch(self, sequence=0, token=None, stream=None, raw=None):
        return self.service.wakeword(self.sid, token or self.token, 'batch', {
            'stream_id':stream or self.stream, 'sequence':sequence,
            'base64':base64.b64encode(raw if raw is not None else bytes(BATCH_BYTES)).decode()})

    def caught(self, call):
        try:
            call()
            return False
        except Problem:
            return True

    def test_snapshot_reports_configured_detector_without_loading_it(self):
        self.assertFalse(self.service.snapshot(self.sid,self.token)['session']['wakeword_available'])
        self.service.wakewords.factory = lambda: (_ for _ in ()).throw(AssertionError('Do not load a detector for a snapshot'))
        self.assertTrue(self.service.snapshot(self.sid,self.token)['session']['wakeword_available'])

    def test_requires_active_session(self):
        self.prepare()
        self.cmd('consent.acknowledge',{'policy_version':1})
        self.assertTrue(self.caught(self.start))

    def test_requires_facilitator(self):
        self.prepare(); guest = secrets.token_urlsafe(32); self.invite(guest); self.active((guest,))
        self.assertTrue(self.caught(lambda:self.service.wakeword(self.sid,guest,'start',{})))

    def test_requires_current_agreement(self):
        self.prepare(); self.active()
        with self.service.db.transaction() as c:
            c.execute('UPDATE actors SET consent_version=0')
        self.assertTrue(self.caught(self.start))

    def test_missing_model_is_unavailable(self):
        self.active()
        self.problem('wakeword_unavailable', self.start)
        self.problem('wakeword_unavailable', lambda:LocalDetector(self.path.parent/'missing.json'))
        self.assertEqual({},self.service.wakewords.streams)

    def test_loading_failure_releases_capacity(self):
        self.prepare(); self.active()
        def fail(): raise ValueError('private model path')
        self.service.wakewords.factory = fail
        for _ in range(6):
            error=self.problem('wakeword_unavailable',self.start)
            self.assertNotIn('private',str(error))
        self.assertEqual({},self.service.wakewords.streams)

    def test_duplicate_returns_same_detection_without_inference(self):
        self.prepare(); self.active(); self.start()
        before=self.service.snapshot(self.sid,self.token)
        first=self.batch(); second=self.batch()
        self.assertEqual(first['detection'],second['detection'])
        self.assertTrue(second['replayed'])
        self.assertEqual(1,self.detector.calls)
        self.assertEqual(before,self.service.snapshot(self.sid,self.token))

    def test_cooldown_and_idle_expiry(self):
        self.prepare(); self.active(); self.start()
        self.assertIsNotNone(self.batch()['detection'])
        self.now += 2.9
        self.assertIsNone(self.batch(1)['detection'])
        self.now += 0.1
        self.assertIsNotNone(self.batch(2)['detection'])
        self.now += 5
        self.assertTrue(self.caught(lambda:self.batch(3)))

    def test_sequence_gap_and_changed_retry_reset(self):
        self.prepare(); self.active(); self.start(); self.batch()
        self.assertTrue(self.caught(lambda:self.batch(2)))
        self.assertEqual({},self.service.wakewords.streams)
        self.start(); self.batch()
        self.assertTrue(self.caught(lambda:self.batch(raw=b'\1'*BATCH_BYTES)))

    def test_oversized_audio_never_reaches_detector(self):
        self.prepare(); self.active(); self.start()
        self.assertTrue(self.caught(lambda:self.batch(raw=bytes(BATCH_BYTES+2))))
        self.assertEqual(0,self.detector.calls)

    def test_wrong_pcm_size_never_reaches_detector(self):
        self.prepare(); self.active(); self.start()
        # Both 10240 and 10241 bytes encode to 13656 base64 characters.
        self.assertTrue(self.caught(lambda:self.batch(raw=bytes(BATCH_BYTES+1))))
        self.assertEqual(0,self.detector.calls)

    def test_other_session_cannot_use_stream(self):
        self.prepare(); self.active(); self.start()
        old=self.sid; old_token=self.token
        self.sid=secrets.token_hex(16); self.token=secrets.token_urlsafe(32)
        self.service.create_session({'session_id':self.sid,'title':'Other meeting','owner_name':'Facilitator','owner_token':self.token})
        self.active()
        self.assertTrue(self.caught(self.batch))
        self.sid=old; self.token=old_token
        self.assertEqual(0,self.detector.calls)

    def test_one_stream_per_session(self):
        self.prepare(); self.active(); self.start()
        self.assertTrue(self.caught(self.start))

    def test_owner_cannot_be_impersonated_by_another_facilitator(self):
        self.prepare(); guest=secrets.token_urlsafe(32); joined=self.invite(guest)
        self.cmd('participant.role',{'actor_id':joined['actor_id'],'role':'facilitator'})
        self.active((guest,)); self.start()
        self.problem('forbidden',lambda:self.batch(token=guest))
        self.assertEqual(0,self.detector.calls)

    def test_pause_revokes_stream_and_audio_is_not_replayed(self):
        self.prepare(); self.active(); self.start(); self.batch()
        self.cmd('session.pause')
        self.assertEqual({},self.service.wakewords.streams)
        self.active()
        self.assertTrue(self.caught(self.batch))

    def test_close_withdraw_delete_and_demote_clear_streams(self):
        self.prepare(); guest=secrets.token_urlsafe(32); joined=self.invite(guest)
        self.cmd('participant.role',{'actor_id':joined['actor_id'],'role':'facilitator'})
        self.active((guest,)); self.start()
        self.cmd('participant.role',{'actor_id':self.created['actor_id'],'role':'participant'},token=guest)
        self.assertEqual({},self.service.wakewords.streams)
        self.cmd('participant.role',{'actor_id':self.created['actor_id'],'role':'facilitator'},token=guest)
        self.start(); self.cmd('consent.withdraw',token=guest)
        self.assertEqual({},self.service.wakewords.streams)
        self.active((guest,)); self.start(); self.cmd('session.close')
        self.assertEqual({},self.service.wakewords.streams)
        self.service.delete_session(self.sid,self.token)
        self.assertEqual({},self.service.wakewords.streams)

    def test_post_inference_authority_is_rechecked(self):
        self.prepare(); self.active(); self.start()
        # Direct DB change isolates the post-inference guard from lifecycle invalidation.
        def revoke():
            with self.service.db.transaction() as c:
                c.execute("UPDATE sessions SET state='paused'")
        self.detector.during=revoke
        self.assertTrue(self.caught(self.batch))

    def test_stop_during_inference_does_not_block_database_or_release_detection(self):
        self.prepare(); self.active(); self.start()
        entered=threading.Event(); release=threading.Event()
        self.detector.during=lambda:(entered.set(),release.wait(3))
        with ThreadPoolExecutor() as pool:
            result=pool.submit(lambda:self.caught(self.batch))
            self.assertTrue(entered.wait(2))
            self.cmd('session.pause')
            release.set()
            self.assertTrue(result.result(timeout=3))

    def test_explicit_stop_during_inference_discards_result(self):
        self.prepare(); self.active(); self.start()
        self.detector.during=lambda:self.service.wakeword(self.sid,self.token,'stop',{'stream_id':self.stream})
        self.assertTrue(self.caught(self.batch))

    def test_inference_failure_and_invalid_score_reset(self):
        self.prepare(); self.active(); self.start()
        self.detector.score=float('nan')
        self.assertTrue(self.caught(self.batch))
        self.assertEqual({},self.service.wakewords.streams)

    def test_capacity_is_four(self):
        self.prepare(); self.active()
        registry=self.service.wakewords
        authority=('owner',1,1)
        for index in range(4):
            registry.start(str(index),authority,lambda:authority)
        self.assertTrue(self.caught(lambda:registry.start('overflow',authority,lambda:authority)))
        registry.invalidate('0')
        registry.start('replacement',authority,lambda:authority)
        self.assertEqual(4,len(registry.streams))

    def test_second_batch_is_refused_during_inference(self):
        self.prepare(); self.active(); self.start()
        results=[]
        def nested():
            self.detector.during=lambda:None
            results.append(self.caught(self.batch))
        self.detector.during=nested
        self.batch()
        self.assertEqual(results,[True])

    def test_http_contract_and_origin(self):
        self.prepare(); self.active()
        server=LocalServer(('127.0.0.1',0),self.service,['http://localhost:5173'])
        thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
        try:
            conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=2)
            headers={'Authorization':'Bearer '+self.token,'Content-Type':'application/json','Origin':'http://localhost:5173'}
            path='/api/sessions/'+self.sid+'/wakeword/'
            conn.request('POST',path+'start','{}',headers); response=conn.getresponse()
            result=json.loads(response.read()); self.assertEqual(200,response.status)
            body=json.dumps({'stream_id':result['stream_id'],'sequence':0,'base64':base64.b64encode(bytes(BATCH_BYTES)).decode()})
            conn.request('POST',path+'batch',body,headers); response=conn.getresponse()
            self.assertEqual(200,response.status); self.assertIsNotNone(json.loads(response.read())['detection'])
            conn.request('POST',path+'batch',body,dict(headers,Origin='https://wrong.example'))
            response=conn.getresponse(); response.read(); self.assertEqual(403,response.status)
            conn.request('POST',path+'batch',' '*16001,headers)
            response=conn.getresponse(); response.read(); self.assertEqual(413,response.status)
            conn.close()
        finally:
            server.shutdown(); server.server_close(); thread.join()
