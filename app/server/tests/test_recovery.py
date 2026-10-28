import base64
import secrets
import sqlite3
import threading
import time
from contextlib import contextmanager
import unittest
from unittest.mock import patch
import test_membership as helpers
import test_service as sources
from genai_server.adapters import FixtureExtractor
from genai_server.isolated import IsolatedExtractor


class CountingFixture(FixtureExtractor):
    def __init__(self):self.calls=0
    def extract(self,request):
        self.calls+=1
        return super().extract(request)


class RecoveryTests(unittest.TestCase):
    setUp=helpers.MembershipTests.setUp
    command=helpers.MembershipTests.command
    active=helpers.MembershipTests.active
    snap=helpers.MembershipTests.snap
    refuses=helpers.MembershipTests.refuses

    def queue(self):
        source=self.command('source.image',{'mime':'image/png','base64':base64.b64encode(sources.png()).decode(),
            'regions':[{'id':'region_001','box':[0,0,1,1]}]})
        return self.command('extraction.queue',{'source_id':source['id'],'expected_revision':1})

    def test_completion_store_recovers_without_another_extraction(self):
        self.active();job=self.queue();adapter=CountingFixture();self.service.extractor=adapter
        with self.service.db.transaction() as c:
            c.execute("CREATE TRIGGER fail_completion BEFORE INSERT ON events WHEN NEW.type='job.succeeded' BEGIN SELECT RAISE(ABORT,'fault'); END")
        self.service.run_one_job()
        self.assertEqual('running',self.service.record(self.sid,self.token,job['id'])['data']['status'])
        self.assertEqual(1,adapter.calls)
        self.assertEqual([], [r for r in self.snap()['records'] if r['kind']=='proposal'])
        with self.service.db.transaction() as c:c.execute('DROP TRIGGER fail_completion')
        self.service.run_one_job()
        self.assertEqual('succeeded',self.service.record(self.sid,self.token,job['id'])['data']['status'])
        self.assertEqual(1,adapter.calls)
        self.assertEqual(1,len([r for r in self.snap()['records'] if r['kind']=='proposal']))
        self.assertEqual({},self.service.pending_completions)

    def test_one_failed_purge_does_not_block_another_session(self):
        self.active();self.command('source.text',{'text':'Expired source'})
        other_sid,other_token=secrets.token_hex(16),secrets.token_urlsafe(32)
        self.service.create_session({'session_id':other_sid,'owner_token':other_token,'owner_name':'Other','title':'Other'})
        with self.service.db.transaction() as c:
            c.execute('UPDATE sessions SET expires=? WHERE id=?',(self.now-1,self.sid))
            c.execute("CREATE TRIGGER fail_purge BEFORE DELETE ON records BEGIN SELECT RAISE(ABORT,'fault'); END")
        try:other=self.service.snapshot(other_sid,other_token)
        except Exception as error:self.fail('Unrelated session was blocked: '+type(error).__name__)
        self.assertEqual('draft',other['session']['state'])
        self.refuses('session_expired',lambda:self.snap())
        self.assertEqual('maintenance_retry_pending',self.service.maintenance_failures[self.sid])
        with self.service.db.transaction() as c:c.execute('DROP TRIGGER fail_purge')
        self.service.sweep()
        self.assertEqual('deleted',self.snap()['state'])
        self.assertNotIn(self.sid,self.service.maintenance_failures)

    def test_pause_during_failed_completion_prevents_late_proposals(self):
        self.active();job=self.queue()
        with self.service.db.transaction() as c:
            c.execute("CREATE TRIGGER fail_completion BEFORE INSERT ON events WHEN NEW.type='job.succeeded' BEGIN SELECT RAISE(ABORT,'fault'); END")
        self.service.run_one_job()
        self.command('session.pause')
        with self.service.db.transaction() as c:c.execute('DROP TRIGGER fail_completion')
        self.service.run_one_job()
        self.assertEqual('cancelled',self.service.record(self.sid,self.token,job['id'])['data']['status'])
        self.assertEqual([], [r for r in self.snap()['records'] if r['kind']=='proposal'])

    def test_failed_lease_pause_cannot_allow_capture_or_heartbeat(self):
        self.active()
        with self.service.db.transaction() as c:
            c.execute("CREATE TRIGGER fail_pause BEFORE UPDATE OF state ON sessions WHEN NEW.state='paused' BEGIN SELECT RAISE(ABORT,'fault'); END")
        self.now+=301
        self.refuses('lease_expired',lambda:self.command('source.text',{'text':'must not enter'}))
        self.refuses('lease_expired',lambda:self.command('session.heartbeat'))
        self.assertEqual([],self.snap()['records'])

    def test_delayed_activation_cannot_override_pause(self):
        self.active();revision=self.snap()['session']['revision']
        self.command('session.pause')
        self.refuses('stale_activation',lambda:self.command('session.activate',{'policy_version':1,'expected_session_revision':revision}))
        self.assertEqual('paused',self.snap()['session']['state'])

    def test_delete_clears_retained_completion_output(self):
        self.active();self.queue()
        with self.service.db.transaction() as c:
            c.execute("CREATE TRIGGER fail_completion BEFORE INSERT ON events WHEN NEW.type='job.succeeded' BEGIN SELECT RAISE(ABORT,'fault'); END")
        self.service.run_one_job()
        self.assertEqual(1,len(self.service.pending_completions))
        self.service.delete_session(self.sid,self.token)
        self.assertEqual({},self.service.pending_completions)

    def test_failed_claim_is_atomic_and_can_retry(self):
        self.active();job=self.queue();adapter=CountingFixture();self.service.extractor=adapter
        with self.service.db.transaction() as c:
            c.execute("CREATE TRIGGER fail_claim BEFORE INSERT ON events WHEN NEW.type='job.started' BEGIN SELECT RAISE(ABORT,'fault'); END")
        with self.assertRaises(sqlite3.Error):self.service.run_one_job()
        self.assertEqual(0,adapter.calls)
        self.assertEqual('queued',self.service.record(self.sid,self.token,job['id'])['data']['status'])
        with self.service.db.transaction() as c:c.execute('DROP TRIGGER fail_claim')
        self.service.run_one_job();self.assertEqual(1,adapter.calls)

    def test_lost_completion_acknowledgement_does_not_duplicate_results(self):
        self.active();job=self.queue();adapter=CountingFixture();self.service.extractor=adapter
        original=self.service.db.transaction;failed=[False]
        @contextmanager
        def uncertain():
            lose_ack=False
            with original() as c:
                yield c
                if not failed[0] and c.execute("SELECT 1 FROM events WHERE type='job.succeeded'").fetchone():lose_ack=True
            if lose_ack:
                failed[0]=True
                raise sqlite3.OperationalError('Synthetic lost acknowledgement after commit')
        self.service.db.transaction=uncertain
        self.service.run_one_job();self.service.run_one_job()
        self.assertEqual(1,adapter.calls)
        self.assertEqual('succeeded',self.service.record(self.sid,self.token,job['id'])['data']['status'])
        self.assertEqual(1,len([r for r in self.snap()['records'] if r['kind']=='proposal']))

    def test_sessions_receive_round_robin_claims(self):
        self.active();first=self.queue();second=self.queue()
        original_sid,original_token=self.sid,self.token
        self.now+=1;self.sid,self.token=secrets.token_hex(16),secrets.token_urlsafe(32)
        self.service.create_session({'session_id':self.sid,'owner_token':self.token,'owner_name':'Other','title':'Other'})
        self.active();other=self.queue();other_sid,other_token=self.sid,self.token
        self.sid,self.token=original_sid,original_token
        self.service.run_one_job();self.service.run_one_job()
        self.assertEqual('succeeded',self.service.record(other_sid,other_token,other['id'])['data']['status'])
        self.assertEqual('queued',self.service.record(self.sid,self.token,second['id'])['data']['status'])

    def test_instance_queue_limit_is_distinct_from_session_limit(self):
        self.active();self.service.MAX_INSTANCE_JOBS=1;self.queue()
        self.refuses('instance_queue_full',lambda:self.queue())

    def test_maintenance_expires_running_jobs_without_callback(self):
        self.active();job=self.queue()
        with self.service.db.transaction() as c:
            record=self.service._get(c,self.sid,job['id']);record['data']['status']='running'
            self.service._save(c,self.sid,record,record['data'])
        self.now+=61;self.service.sweep()
        self.assertEqual('failed',self.service.record(self.sid,self.token,job['id'])['data']['status'])

    def test_complete_store_outage_still_retains_result_for_recovery(self):
        self.active();job=self.queue();original=self.service.db.transaction;service=self.service
        @contextmanager
        def unavailable():
            raise sqlite3.OperationalError('Store unavailable')
            yield
        class StoreFailureAdapter(CountingFixture):
            def extract(self,request):
                result=super().extract(request)
                service.db.transaction=unavailable
                return result
        adapter=StoreFailureAdapter();service.extractor=adapter
        try:service.run_one_job()
        finally:service.db.transaction=original
        self.assertEqual(1,len(service.pending_completions))
        service.run_one_job()
        self.assertEqual(1,adapter.calls)
        self.assertEqual('succeeded',service.record(self.sid,self.token,job['id'])['data']['status'])

    def test_delete_before_failed_completion_cannot_retain_output(self):
        self.active();self.queue()
        def deleted_then_failed(*args):
            self.service.delete_session(self.sid,self.token)
            raise sqlite3.OperationalError('Failure after deletion')
        with patch.object(self.service,'_complete_job',deleted_then_failed):self.service.run_one_job()
        self.assertEqual({},self.service.pending_completions)
        self.assertEqual({},self.service.executions)

    def test_completion_checks_lease_even_when_pause_write_fails(self):
        self.active();self.now+=250;job=self.queue();adapter=sources.BlockingAdapter();self.service.extractor=adapter
        worker=threading.Thread(target=self.service.run_one_job);worker.start()
        self.assertTrue(adapter.started.wait(2))
        with self.service.db.transaction() as c:
            c.execute("CREATE TRIGGER fail_pause BEFORE UPDATE OF state ON sessions WHEN NEW.state='paused' BEGIN SELECT RAISE(ABORT,'fault'); END")
        self.now+=51;self.service.sweep();adapter.release.set();worker.join(3)
        self.assertFalse(worker.is_alive())
        self.assertEqual('cancelled',self.service.record(self.sid,self.token,job['id'])['data']['status'])
        self.assertEqual([], [r for r in self.snap()['records'] if r['kind']=='proposal'])

    def test_committed_cancel_stops_running_isolated_adapter(self):
        self.active();job=self.queue()
        self.service.extractor=IsolatedExtractor('fixture',module='test_isolated',factory='HangingAdapter',timeout_seconds=5)
        worker=threading.Thread(target=self.service.run_one_job);worker.start()
        try:
            deadline=time.monotonic()+2
            while time.monotonic()<deadline:
                current=self.service.record(self.sid,self.token,job['id'])
                if current['data']['status']=='running':break
                time.sleep(.01)
            self.assertEqual('running',current['data']['status'])
            self.command('job.cancel',{'job_id':job['id'],'expected_revision':current['revision']})
            worker.join(1)
            self.assertFalse(worker.is_alive(),'Committed cancellation did not release the worker')
        finally:worker.join(6)
        self.assertEqual('cancelled',self.service.record(self.sid,self.token,job['id'])['data']['status'])

    def test_removed_author_cannot_commit_inflight_output(self):
        self.active();capability=secrets.token_urlsafe(32);guest=secrets.token_urlsafe(32)
        self.command('participant.invite',{'invitation':capability,'expected_roster_revision':self.snap()['session']['roster_revision']})
        joined=self.service.join(self.sid,{'invitation':capability,'token':guest,'name':'Guest','policy_version':1})
        source=self.command('source.image',{'mime':'image/png','base64':base64.b64encode(sources.png()).decode(),
            'regions':[{'id':'region_001','box':[0,0,1,1]}]},token=guest)
        job=self.command('extraction.queue',{'source_id':source['id'],'expected_revision':1},token=guest)
        adapter=sources.BlockingAdapter();self.service.extractor=adapter
        worker=threading.Thread(target=self.service.run_one_job);worker.start()
        try:
            self.assertTrue(adapter.started.wait(2))
            self.command('participant.remove',{'actor_id':joined['actor_id'],'expected_roster_revision':self.snap()['session']['roster_revision']})
        finally:adapter.release.set();worker.join(3)
        self.assertFalse(worker.is_alive())
        self.assertEqual('cancelled',self.service.record(self.sid,self.token,job['id'])['data']['status'])
        self.assertEqual([], [r for r in self.snap()['records'] if r['kind']=='proposal'])
