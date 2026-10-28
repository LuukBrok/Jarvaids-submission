"""Post-merge authority, recovery and portable-output acceptance evidence."""
import base64
import concurrent.futures
import json
import secrets
import sqlite3
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
import unittest
from unittest.mock import patch

from genai_server.service import Service
from genai_server.validation import Problem
import test_membership as membership
from test_recovery import CountingFixture
from test_service import png


class FollowupContracts(unittest.TestCase):
    setUp=membership.MembershipTests.setUp
    command=membership.MembershipTests.command
    active=membership.MembershipTests.active
    snap=membership.MembershipTests.snap
    invite=membership.MembershipTests.invite
    join=membership.MembershipTests.join
    refuses=membership.MembershipTests.refuses

    def guest(self):
        invitation,_=self.invite()
        body,joined=self.join(invitation)
        return body,joined['actor_id']

    def picture(self,token=None):
        return self.command('source.image',{'mime':'image/png','base64':base64.b64encode(png()).decode(),
            'regions':[{'id':'region_001','box':[0,0,1,1]}]},token=token)

    def test_removed_actor_loses_every_read_and_cached_command(self):
        self.active();body,aid=self.guest();token=body['token']
        source=self.picture(token);key=secrets.token_hex(16)
        payload={'text':'Guest contribution'}
        self.command('source.text',payload,token=token,key=key)
        self.assertEqual('image/png',self.service.media(self.sid,token,source['id'])[0])
        self.command('participant.remove',{'actor_id':aid,'expected_roster_revision':self.snap()['session']['roster_revision']})
        reads={
            'snapshot':lambda:self.service.snapshot(self.sid,token),
            'delta':lambda:self.service.delta(self.sid,token,0),
            'events':lambda:self.service.events(self.sid,token),
            'record':lambda:self.service.record(self.sid,token,source['id']),
            'history':lambda:self.service.record(self.sid,token,source['id'],1),
            'media':lambda:self.service.media(self.sid,token,source['id']),
            'crop':lambda:self.service.crop(self.sid,token,source['id'],1,'region_001'),
            'export':lambda:self.service.export_snapshot(self.sid,token,{'include_unresolved':True}),
            'cached command':lambda:self.service.command(self.sid,token,key,'source.text',payload),
            'new command':lambda:self.service.command(self.sid,token,secrets.token_hex(16),'source.text',payload),
        }
        before=self.snap()
        for route,read in reads.items():
            with self.subTest(route=route):self.refuses('unauthorized',read)
        self.refuses('membership_removed',lambda:self.service.join(self.sid,body))
        self.assertEqual(before,self.snap())

    def test_demotion_rechecks_cached_mutations_and_evidence_authority(self):
        self.active();body,aid=self.guest();token=body['token'];source=self.picture(token)
        payload={'text':'Earlier authorised write'};key=secrets.token_hex(16)
        self.command('source.text',payload,token=token,key=key)
        self.command('participant.role',{'actor_id':aid,'role':'viewer','expected_roster_revision':self.snap()['session']['roster_revision']})
        for read in (lambda:self.service.command(self.sid,token,key,'source.text',payload),
                     lambda:self.service.media(self.sid,token,source['id']),
                     lambda:self.service.crop(self.sid,token,source['id'],1,'region_001')):
            self.refuses('forbidden',read)
        self.assertEqual(aid,self.service.delta(self.sid,token,0)['actor_id'])
        self.assertTrue(self.service.events(self.sid,token)['events'])

    def test_demoted_facilitator_cannot_replay_export_or_read_its_history(self):
        self.active();body,aid=self.guest();token=body['token']
        self.command('participant.role',{'actor_id':aid,'role':'facilitator','expected_roster_revision':self.snap()['session']['roster_revision']})
        key=secrets.token_hex(16);payload={'include_unresolved':True}
        exported=self.command('export.create',payload,token=token,key=key)
        self.command('participant.role',{'actor_id':aid,'role':'viewer','expected_roster_revision':self.snap()['session']['roster_revision']})
        self.refuses('forbidden',lambda:self.service.command(self.sid,token,key,'export.create',payload))
        for revision in (None,1):self.refuses('forbidden',lambda:self.service.record(self.sid,token,exported['id'],revision))
        # Read through a cursor rather than from 0. A delta whose changed set is
        # more than half the session answers resync_required instead of records,
        # and from 0 that is always true. The subject here is the authority
        # filter on a delta, so the session is given enough records for the
        # export to be a small change in it.
        for n in range(4):self.command('source.text',{'text':f'Filler {n}'})
        cursor=self.service.events(self.sid,self.token)['current_seq']
        self.command('export.create',{'include_unresolved':True})
        delta=self.service.delta(self.sid,token,cursor)
        self.assertNotIn('resync_required',delta)
        record=next(r for r in delta['records'] if r['data'].get('manifest'))
        self.assertEqual({'manifest'},set(record['data']))

    def test_writes_between_event_pages_are_not_lost_or_duplicated(self):
        self.active()
        for n in range(205):self.command('source.text',{'text':f'Original {n}'})
        first=self.service.events(self.sid,self.token)
        self.assertTrue(first['has_more'])
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            futures=[pool.submit(self.command,'source.text',{'text':f'Concurrent {n}'}) for n in range(5)]
            for future in futures:future.result(timeout=10)
        events=list(first['events']);after=first['next_after']
        while True:
            page=self.service.events(self.sid,self.token,after);events.extend(page['events']);after=page['next_after']
            if not page['has_more']:break
        self.assertEqual(list(range(1,page['current_seq']+1)),[e['seq'] for e in events])
        delta=self.service.delta(self.sid,self.token,first['current_seq'])
        self.assertEqual(10,len(delta['records']))
        self.assertEqual(page['current_seq'],delta['current_seq'])

    def test_rollback_does_not_publish_ghost_record_descriptors(self):
        self.active();before=self.snap();cursor=before['session']['seq']
        with self.service.db.transaction() as c:
            c.execute("CREATE TRIGGER reject_text BEFORE INSERT ON events WHEN NEW.type='source.text' BEGIN SELECT RAISE(ABORT,'fault'); END")
        with self.assertRaises(sqlite3.Error):self.command('source.text',{'text':'Must roll back'})
        with self.service.db.transaction() as c:c.execute('DROP TRIGGER reject_text')
        self.assertEqual(before,self.snap())
        self.assertEqual([],self.service.delta(self.sid,self.token,cursor)['records'])
        written=self.command('source.text',{'text':'Committed'})
        described=self.service.events(self.sid,self.token,cursor)['events'][0]['data']['records']
        self.assertEqual({written['source']['id'],written['proposal']['id']},{r['id'] for r in described})

    def test_lost_credentials_cannot_be_reset_by_reusing_name_or_session_id(self):
        before=self.snap();replacement=secrets.token_urlsafe(32)
        self.refuses('session_exists',lambda:self.service.create_session(dict(session_id=self.sid,owner_token=replacement,owner_name='Host',title='Test')))
        self.refuses('unauthorized',lambda:self.service.snapshot(self.sid,replacement))
        self.assertEqual(before,self.snap())

    def test_remaining_facilitator_can_reinvite_without_inheriting_agreement(self):
        self.active();body,aid=self.guest()
        self.command('participant.remove',{'actor_id':aid,'expected_roster_revision':self.snap()['session']['roster_revision']})
        invitation,_=self.invite()
        self.refuses('missing_fields',lambda:self.service.join(self.sid,{'invitation':invitation,'token':secrets.token_urlsafe(32),'name':'Guest'}))
        newbody,newmember=self.join(invitation)
        self.assertNotEqual(aid,newmember['actor_id']);self.assertNotEqual(body['token'],newbody['token'])
        self.refuses('unauthorized',lambda:self.service.snapshot(self.sid,body['token']))
        serialised=json.dumps(self.snap())
        for secret in (self.token,body['token'],newbody['token'],invitation):self.assertNotIn(secret,serialised)

    def test_output_release_opens_after_delete_and_manifest_matches_in_both_modes(self):
        self.active();typed=self.command('source.text',{'text':'Accepted <script> [link](url)'})
        accepted=self.command('proposal.review',{'proposal_id':typed['proposal']['id'],'expected_revision':1,'decision':'accept'})
        self.command('source.text',{'text':'Unreviewed claim'})
        downloads=[]
        for include in (False,True):
            for data in (self.service.export_snapshot(self.sid,self.token,{'include_unresolved':include}),
                         self.command('export.create',{'include_unresolved':include})['data']):
                saved=json.loads(json.dumps(data));manifest=saved['manifest']
                expected=[{k:r[k] for k in ('id','kind','revision')} for r in saved['records']]
                self.assertEqual(expected,manifest['included'])
                self.assertEqual('output_only',manifest['release_kind'])
                self.assertTrue(manifest['output_readable_offline']);self.assertTrue(manifest['references_require_session'])
                self.assertFalse(manifest['source_evidence_included']);self.assertFalse(manifest['redaction_applied'])
                self.assertTrue(all(r['kind'] in ('item','proposal') for r in saved['records']))
                self.assertEqual(2 if include else 1,len(saved['records']))
                self.assertNotIn('<script>',saved['markdown']);self.assertIn('&lt;script&gt;',saved['markdown'])
                for secret in (self.token,'base64','token_hash'):self.assertNotIn(secret,json.dumps(saved))
                downloads.append(saved)
        self.service.delete_session(self.sid,self.token)
        for saved in downloads:
            self.assertIn('Accepted',saved['markdown'])
            self.assertEqual('accepted',saved['records'][0]['data']['status'])
            self.assertIn('session deletion',saved['manifest']['evidence_availability'])
        self.refuses('unauthorized',lambda:self.service.record(self.sid,self.token,typed['source']['id']))

    def test_restart_after_provider_success_does_not_repeat_unknown_outcome(self):
        self.active();source=self.picture();job=self.command('extraction.queue',{'source_id':source['id'],'expected_revision':1})
        adapter=CountingFixture();self.service.extractor=adapter
        with patch.object(self.service,'_complete_job',side_effect=sqlite3.OperationalError('store unavailable')):
            self.service.run_one_job()
        self.assertEqual(1,adapter.calls);self.assertEqual(1,len(self.service.pending_completions))
        restarted=Service(self.service.db.path,extractor=adapter,clock=lambda:self.now)
        restarted.recover_jobs();restarted.recover_jobs();self.service=restarted
        self.assertFalse(restarted.run_one_job());self.assertEqual(1,adapter.calls)
        data=restarted.record(self.sid,self.token,job['id'])['data']
        self.assertEqual('failed',data['status']);self.assertEqual('interrupted_unknown_outcome',data['error'])
        self.assertEqual('unknown',data['usage_status']);self.assertIsNone(data['usage'])
        self.assertEqual([], [r for r in self.snap()['records'] if r['kind']=='proposal'])
        events=self.service.events(self.sid,self.token)['events']
        self.assertEqual(1,sum(e['type']=='job.recovered' for e in events))

    def uncertain_job(self):
        self.active();source=self.picture();job=self.command('extraction.queue',{'source_id':source['id'],'expected_revision':1})
        with self.service.db.transaction() as c:
            r=self.service._get(c,self.sid,job['id']);r['data'].update(status='running',attempts=1)
            self.service._save(c,self.sid,r,r['data'])
        self.service.recover_jobs();return source,job

    def test_uncertain_retry_requires_specific_explicit_acknowledgement(self):
        source,job=self.uncertain_job();payload={'source_id':source['id'],'expected_revision':1}
        for extra in ({},{'retry_of':job['id']},{'retry_of':job['id'],'acknowledge_uncertain_cost':False},
                      {'retry_of':secrets.token_hex(16),'acknowledge_uncertain_cost':True},
                      {'retry_of':job['id'],'acknowledge_uncertain_cost':1}):
            self.refuses('uncertain_retry_requires_acknowledgement',lambda:self.command('extraction.queue',{**payload,**extra}))
        key=secrets.token_hex(16);intent={**payload,'retry_of':job['id'],'acknowledge_uncertain_cost':True}
        retry=self.command('extraction.queue',intent,key=key)
        self.assertEqual(retry,self.command('extraction.queue',intent,key=key))
        self.assertEqual(job['id'],retry['data']['retry_of']);self.assertTrue(retry['data']['uncertain_cost_acknowledged'])
        adapter=CountingFixture();self.service.extractor=adapter;self.service.run_one_job()
        self.assertEqual(1,adapter.calls);self.assertEqual('succeeded',self.service.record(self.sid,self.token,retry['id'])['data']['status'])
        self.assertEqual('failed',self.service.record(self.sid,self.token,job['id'])['data']['status'])

    def test_retry_acknowledgement_cannot_name_an_unrelated_source(self):
        source,job=self.uncertain_job();other=self.picture()
        self.refuses('invalid_retry',lambda:self.command('extraction.queue',{'source_id':other['id'],'expected_revision':1,
            'retry_of':job['id'],'acknowledge_uncertain_cost':True}))

    def test_startup_preserves_unclaimed_queued_jobs(self):
        self.active();source=self.picture();job=self.command('extraction.queue',{'source_id':source['id'],'expected_revision':1})
        self.service.recover_jobs();self.service.run_one_job()
        self.assertEqual('succeeded',self.service.record(self.sid,self.token,job['id'])['data']['status'])

    def test_real_process_exit_after_provider_success_requires_acknowledged_retry(self):
        self.active();source=self.picture();job=self.command('extraction.queue',{'source_id':source['id'],'expected_revision':1})
        marker=self.service.db.path.parent/'provider-completed.txt'
        script='''import os,sys
from pathlib import Path
from genai_server.service import Service
from genai_server.adapters import FixtureExtractor
class Adapter(FixtureExtractor):
 def extract(self,request):
  result=super().extract(request)
  with open(sys.argv[2],'w') as marker:
   marker.write('provider completed once');marker.flush();os.fsync(marker.fileno())
  return result
s=Service(sys.argv[1],extractor=Adapter(),clock=lambda:1000)
s._complete_job=lambda *args:os._exit(77)
s.run_one_job()
'''
        process=subprocess.run([sys.executable,'-c',script,str(self.service.db.path),str(marker)],
            cwd=Path(__file__).resolve().parents[1],capture_output=True,timeout=15)
        self.assertEqual(77,process.returncode,process.stderr.decode(errors='replace'))
        self.assertEqual('provider completed once',marker.read_text())
        adapter=CountingFixture();self.service=Service(self.service.db.path,extractor=adapter,clock=lambda:self.now)
        self.service.recover_jobs();self.assertFalse(self.service.run_one_job());self.assertEqual(0,adapter.calls)
        self.refuses('uncertain_retry_requires_acknowledgement',lambda:self.command('extraction.queue',{'source_id':source['id'],'expected_revision':1}))
        self.assertEqual('unknown',self.service.record(self.sid,self.token,job['id'])['data']['execution_outcome'])

    def test_startup_deadline_or_lease_cleanup_cannot_erase_claim_uncertainty(self):
        for delay in (61,301):
            with self.subTest(delay=delay):
                self.command('consent.acknowledge',{'policy_version':1})
                self.command('session.activate',{'policy_version':1})
                source=self.picture();job=self.command('extraction.queue',{'source_id':source['id'],'expected_revision':1})
                with self.service.db.transaction() as c:
                    record=self.service._get(c,self.sid,job['id']);record['data'].update(status='running',attempts=1)
                    self.service._save(c,self.sid,record,record['data'])
                self.now+=delay
                self.service=Service(self.service.db.path,clock=lambda:self.now);self.service.recover_jobs()
                data=self.service.record(self.sid,self.token,job['id'])['data']
                self.assertEqual('interrupted_unknown_outcome',data['error'])
                self.command('session.activate',{'policy_version':1})
                self.refuses('uncertain_retry_requires_acknowledgement',lambda:self.command('extraction.queue',{'source_id':source['id'],'expected_revision':1}))

    def test_cancelled_output_keeps_reported_usage_without_publishing_proposals(self):
        self.active();source=self.picture();job=self.command('extraction.queue',{'source_id':source['id'],'expected_revision':1})
        case=self
        class ReportedCostFixture(CountingFixture):
            def extract(self,request):
                result=super().extract(request)
                case.command('session.pause')
                return replace(result,usage={'input_units':1,'output_units':1,'cost':0.25,'currency':'EUR'})
        self.service.extractor=ReportedCostFixture();self.service.run_one_job()
        data=self.service.record(self.sid,self.token,job['id'])['data']
        self.assertEqual('cancelled',data['status']);self.assertEqual('reported',data['usage_status'])
        self.assertEqual(0.25,data['usage']['cost']);self.assertEqual('completed',data['execution_outcome'])
        self.assertEqual([], [r for r in self.snap()['records'] if r['kind']=='proposal'])

    def test_storage_rejection_keeps_reported_attempt_usage(self):
        self.active();source=self.picture();job=self.command('extraction.queue',{'source_id':source['id'],'expected_revision':1})
        class ReportedCostFixture(CountingFixture):
            def extract(self,request):
                return replace(super().extract(request),usage={'cost':0.25,'currency':'EUR'})
        self.service.extractor=ReportedCostFixture()
        with patch.object(self.service,'_budget',side_effect=Problem(429,'storage_capacity','Synthetic storage budget')):
            self.service.run_one_job()
        data=self.service.record(self.sid,self.token,job['id'])['data']
        self.assertEqual('failed',data['status']);self.assertEqual('storage_capacity',data['error'])
        self.assertEqual('reported',data['usage_status']);self.assertEqual(0.25,data['usage']['cost'])
        self.assertEqual([], [r for r in self.snap()['records'] if r['kind']=='proposal'])
