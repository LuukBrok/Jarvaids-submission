import base64
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import secrets
import struct
import shutil
import threading
import unittest
import zlib

from genai_server.adapters import ExtractionOutput, FixtureExtractor
from genai_server.service import Service
from genai_server.validation import Problem


def png():
    def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b'\x00\xff\xff\xff'))+chunk(b'IEND',b'')


class BlockingAdapter(FixtureExtractor):
    def __init__(self):self.started=threading.Event();self.release=threading.Event()
    def extract(self,request):
        self.started.set()
        if not self.release.wait(5):raise RuntimeError('test timeout')
        return super().extract(request)


class ServiceTests(unittest.TestCase):
    def setUp(self):
        test_root=Path(__file__).resolve().parents[1]/'.local'/'tests'
        test_root.mkdir(parents=True,exist_ok=True)
        test_dir=test_root/secrets.token_hex(16)
        test_dir.mkdir()
        assert test_dir.resolve().is_relative_to(test_root.resolve())
        self.addCleanup(shutil.rmtree,test_dir)
        self.path=test_dir/'state.sqlite3';self.now=1000.0
        self.service=Service(self.path,clock=lambda:self.now)
        self.sid=secrets.token_hex(16);self.token=secrets.token_urlsafe(32)
        self.created=self.service.create_session({'session_id':self.sid,'title':'Workshop','owner_name':'Facilitator','owner_token':self.token})

    def cmd(self,op,payload=None,token=None,key=None):
        payload=dict(payload or {})
        if op=='session.activate':payload.setdefault('expected_session_revision',self.service.snapshot(self.sid,self.token)['session']['revision'])
        if op=='participant.role':payload.setdefault('expected_roster_revision',self.service.snapshot(self.sid,self.token)['session']['roster_revision'])
        if op=='session.close':payload.setdefault('expected_session_revision',self.service.snapshot(self.sid,self.token)['session']['revision'])
        key=key or secrets.token_hex(16);sequence=None
        if op in self.service.CONTROL_COMMANDS:
            if not hasattr(self,'control_intents'):self.control_intents={}
            sequence=self.control_intents.setdefault(key,self.service.snapshot(self.sid,token or self.token)['next_control_sequence'])
        return self.service.command(self.sid,token or self.token,key,op,payload or {},sequence)['result']

    def invite(self,token):
        capability=secrets.token_urlsafe(32)
        self.cmd('participant.invite',{'invitation':capability,'expected_roster_revision':self.service.snapshot(self.sid,self.token)['session']['roster_revision']})
        return self.service.join(self.sid,{'invitation':capability,'token':token,'name':'Guest','policy_version':1})

    def active(self,tokens=()):
        version=self.service.snapshot(self.sid,self.token)['session']['policy_version']
        for token in (self.token,*tokens):self.cmd('consent.acknowledge',{'policy_version':version},token)
        self.cmd('session.activate',{'policy_version':version})

    def typed(self,value='A source note'):
        return self.cmd('source.text',{'text':value})

    def accept(self,proposal):
        return self.cmd('proposal.review',{'proposal_id':proposal['id'],'expected_revision':proposal['revision'],'decision':'accept'})['item']

    def image(self,count=2):
        return self.cmd('source.image',{'mime':'image/png','base64':base64.b64encode(png()).decode(),
             'regions':[{'id':f'region_{i:03}','box':[i/count,0,1/count,1]} for i in range(count)]})

    def queue(self,source):
        return self.cmd('extraction.queue',{'source_id':source['id'],'expected_revision':source['revision']})

    def problem(self,code,call):
        with self.assertRaises(Problem) as ctx:call()
        self.assertEqual(code,ctx.exception.code)
        return ctx.exception

    def test_capture_requires_agreement(self):
        self.problem('capture_inactive',lambda:self.typed())
        self.problem('agreement_incomplete',lambda:self.cmd('session.activate',{'policy_version':1}))
        self.assertEqual([],self.service.snapshot(self.sid,self.token)['records'])
        self.active();self.assertEqual('needs_review',self.typed()['proposal']['data']['status'])

    def test_typed_accept_reject_export_restart(self):
        self.active();one=self.typed();item=self.accept(one['proposal']);two=self.typed('Discard me')
        self.cmd('proposal.review',{'proposal_id':two['proposal']['id'],'expected_revision':1,'decision':'reject'})
        export=self.cmd('export.create',{'include_unresolved':False})
        self.assertEqual([item['id']],[r['id'] for r in export['data']['records']])
        restarted=Service(self.path,clock=lambda:self.now)
        self.assertEqual('accepted',restarted.record(self.sid,self.token,item['id'])['data']['status'])

    def test_summary_bridge_creates_positioned_provisional_notes(self):
        self.active()
        existing=self.typed('Existing note')['proposal']
        self.cmd('item.place',{'placements':[{'id':existing['id'],'x':40,'y':60,
            'expected_position_revision':0}],'origin':'human'})
        result=self.cmd('summary.to_stickies',{'summary':
            '- We decided the prototype must work offline.\n'
            '- Risk: people may mistake AI output for accepted work.\n'
            '- Investigate arrows between related notes.'})
        self.assertEqual(3,result['count'])
        self.assertEqual('summary',result['source']['data']['type'])
        self.assertEqual('model',result['source']['data']['origin'])
        position=self.service.record(self.sid,self.token,existing['id'])['position']
        self.assertEqual((40.0,60.0),(position['x'],position['y']))
        proposals=result['proposals']
        self.assertTrue(all(p['data']['status']=='needs_review' and p['data']['origin']=='model' for p in proposals))
        self.assertTrue(all(p['data']['summary_title']==p['data']['text'] for p in proposals))
        self.assertTrue(all(self.service.record(self.sid,self.token,p['id'])['position']['hand_placed'] is False for p in proposals))
        self.assertGreater(min(self.service.record(self.sid,self.token,p['id'])['position']['x'] for p in proposals),360)

    def test_summary_bridge_is_not_a_transcript_summariser(self):
        self.active()
        result=self.cmd('summary.to_stickies',{'summary':'One supplied conclusion.'})
        self.assertEqual(1,result['count'])
        self.assertFalse(any(r['kind']=='transcript_segment' for r in self.service.snapshot(self.sid,self.token)['records']))

    def test_request_deduplication_and_changed_intent(self):
        self.active();key=secrets.token_hex(16)
        a=self.cmd('source.text',{'text':'same'},key=key)
        b=self.cmd('source.text',{'text':'same'},key=key)
        self.assertEqual(a,b)
        self.problem('idempotency_conflict',lambda:self.cmd('source.text',{'text':'different'},key=key))
        c=self.cmd('source.text',{'text':'same'})
        self.assertNotEqual(a['source']['id'],c['source']['id'])
        self.service=Service(self.path,clock=lambda:self.now)
        self.assertEqual(a,self.cmd('source.text',{'text':'same'},key=key))

    def test_two_simultaneous_accepts_commit_once(self):
        self.active();proposal=self.typed()['proposal']
        def work():
            try:return self.accept(proposal)['id']
            except Problem as e:return e.code
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:work(),range(2)))
        self.assertEqual(1,results.count('stale_revision'))
        self.assertEqual(1,len([r for r in self.service.snapshot(self.sid,self.token)['records'] if r['kind']=='item']))

    def test_source_correction_stales_proposals_and_accepted_derivatives(self):
        self.active();first=self.typed();item=self.accept(first['proposal'])
        relationship=self.cmd('proposal.create',{'proposal_kind':'relationship','text':'A grouping','refs':[{'id':item['id'],'revision':1}]})
        group=self.accept(relationship)
        changed=self.cmd('source.correct',{'source_id':first['source']['id'],'expected_revision':1,'text':'Corrected source'})
        self.assertIn(item['id'],changed['invalidated']);self.assertIn(group['id'],changed['invalidated'])
        for rid in (item['id'],group['id']):self.assertEqual('stale',self.service.record(self.sid,self.token,rid)['data']['status'])
        self.assertEqual('A source note',self.service.record(self.sid,self.token,first['source']['id'],1)['data']['text'])

    def test_refresh_stale_proposal_preserves_origin(self):
        self.active();created=self.typed();p=created['proposal'];source=created['source']
        self.cmd('source.correct',{'source_id':source['id'],'expected_revision':1,'text':'Corrected'})
        current=self.service.record(self.sid,self.token,p['id'])
        self.problem('stale_proposal',lambda:self.accept(current))
        refreshed=self.cmd('proposal.edit',{'proposal_id':p['id'],'expected_revision':current['revision'],'text':'Corrected',
            'refs':[{'id':source['id'],'revision':2}]})
        item=self.accept(refreshed);self.assertEqual('human',item['data']['origin'])
        self.assertEqual('Corrected',item['data']['text'])

    def test_layout_acceptance_moves_the_item_without_changing_it(self):
        self.active();source=self.typed();item=self.accept(source['proposal'])
        p=self.cmd('proposal.create',{'proposal_kind':'placement','text':'Place to the right','refs':[{'id':item['id'],'revision':1}],
            'positions':[{'id':item['id'],'x':100,'y':200}]})
        accepted=self.cmd('proposal.review',{'proposal_id':p['id'],'expected_revision':p['revision'],'decision':'accept'})
        # An accepted arrangement writes coordinates onto the item it names and
        # creates no record of its own, so there is nothing to contradict.
        self.assertNotIn('item',accepted)
        self.assertEqual([{'id':item['id'],'x':100.0,'y':200.0,'w':None,'h':None,'revision':1,'hand_placed':True,
                           'placed_by':self.service.snapshot(self.sid,self.token)['actor_id']}],accepted['placements'])
        moved=self.service.record(self.sid,self.token,item['id'])
        self.assertEqual((item['revision'],item['data']),(moved['revision'],moved['data']))
        self.assertEqual({'x':100.0,'y':200.0},{k:moved['position'][k] for k in ('x','y')})
        pending=self.typed()['proposal']
        self.problem('invalid_reference',lambda:self.cmd('proposal.create',{'proposal_kind':'relationship','text':'Group pending',
             'refs':[{'id':pending['id'],'revision':1}]}))

    def test_undo_rejects_stale_client_and_preserves_history(self):
        self.active();first=self.typed();item=self.accept(first['proposal'])
        edited=self.cmd('item.edit',{'item_id':item['id'],'expected_revision':1,'text':'Human edit','refs':item['data']['refs']})['item']
        self.problem('stale_revision',lambda:self.cmd('item.undo',{'item_id':item['id'],'expected_revision':1,'restore_revision':0}))
        self.assertEqual('Human edit',self.service.record(self.sid,self.token,item['id'])['data']['text'])
        undone=self.cmd('item.undo',{'item_id':item['id'],'expected_revision':edited['revision'],'restore_revision':1})['item']
        self.assertEqual('A source note',undone['data']['text'])
        self.assertEqual(3,undone['revision'])
        self.assertEqual('Human edit',self.service.record(self.sid,self.token,item['id'],2)['data']['text'])

    def test_reference_cycle_rejected(self):
        self.active();a=self.accept(self.typed()['proposal'])
        b=self.accept(self.cmd('proposal.create',{'proposal_kind':'content','text':'Derived','refs':[{'id':a['id'],'revision':1}]}))
        self.problem('cyclic_reference',lambda:self.cmd('item.edit',{'item_id':a['id'],'expected_revision':1,'text':'Cycle',
             'refs':[{'id':b['id'],'revision':1}]}))

    def test_join_preserves_current_roster_ack_and_member_can_pause(self):
        self.active();guest=secrets.token_urlsafe(32)
        self.invite(guest)
        snap=self.service.snapshot(self.sid,self.token);version=snap['session']['policy_version']
        self.assertEqual('active',snap['session']['state'])
        self.assertEqual(1,version)
        self.cmd('session.pause',token=guest)
        self.assertEqual('paused',self.service.snapshot(self.sid,self.token)['session']['state'])

    def test_permissions_and_export_cache_after_demotion(self):
        guest=secrets.token_urlsafe(32);who=self.invite(guest)
        self.active((guest,));p=self.cmd('source.text',{'text':'Guest note'},guest)['proposal']
        self.problem('forbidden',lambda:self.cmd('proposal.review',{'proposal_id':p['id'],'expected_revision':1,'decision':'accept'},guest))
        self.cmd('participant.role',{'actor_id':who['actor_id'],'role':'facilitator'})
        key=secrets.token_hex(16);export=self.cmd('export.create',{'include_unresolved':True},guest,key)
        self.cmd('participant.role',{'actor_id':who['actor_id'],'role':'viewer'})
        self.problem('forbidden',lambda:self.cmd('export.create',{'include_unresolved':True},guest,key))
        self.problem('forbidden',lambda:self.service.record(self.sid,guest,export['id']))
        self.problem('forbidden',lambda:self.cmd('source.text',{'text':'Viewer cannot write'},guest))

    def test_cross_session_source_and_credentials_rejected(self):
        self.active();first=self.typed()
        other_sid=secrets.token_hex(16);other_token=secrets.token_urlsafe(32)
        self.service.create_session({'session_id':other_sid,'title':'Other','owner_name':'Other','owner_token':other_token})
        self.problem('unauthorized',lambda:self.service.snapshot(self.sid,other_token))
        self.problem('not_found',lambda:self.service.record(other_sid,other_token,first['source']['id']))
        self.problem('not_found',lambda:self.service.command(other_sid,other_token,new_key(),'proposal.create',{
            'proposal_kind':'content','text':'Leak','refs':[{'id':first['source']['id'],'revision':1}]}))

    def test_fixture_extraction_and_manual_region_repair(self):
        self.active();source=self.image()
        repaired=self.cmd('source.regions',{'source_id':source['id'],'expected_revision':1,
            'regions':[{'id':'region_new','box':[0,0,1,1]}]})['source']
        job=self.queue(repaired);self.assertTrue(self.service.run_one_job())
        done=self.service.record(self.sid,self.token,job['id'])
        self.assertEqual('succeeded',done['data']['status']);self.assertTrue(done['data']['synthetic'])
        self.assertEqual(1,len(done['data']['proposal_ids']))
        p=self.service.record(self.sid,self.token,done['data']['proposal_ids'][0])
        item=self.accept(p)
        self.assertEqual('fixture',item['data']['origin']);self.assertIn('no OCR performed',item['data']['text'])
        self.assertEqual('region_new',item['data']['region_id'])
        self.assertNotIn('base64',source['data'])

    def test_queue_capacity(self):
        self.active();source=self.image()
        for _ in range(self.service.MAX_JOBS):self.queue(source)
        self.problem('queue_full',lambda:self.queue(source))
        self.assertEqual(5,len([r for r in self.service.snapshot(self.sid,self.token)['records'] if r['kind']=='job']))

    def test_late_result_after_pause_cannot_commit(self):
        self.active();source=self.image();job=self.queue(source);adapter=BlockingAdapter();self.service.extractor=adapter
        thread=threading.Thread(target=self.service.run_one_job);thread.start();self.assertTrue(adapter.started.wait(2))
        self.cmd('session.pause');adapter.release.set();thread.join(3);self.assertFalse(thread.is_alive())
        result=self.service.record(self.sid,self.token,job['id'])
        self.assertEqual('cancelled',result['data']['status'])
        self.assertEqual([], [r for r in self.service.snapshot(self.sid,self.token)['records'] if r['kind']=='proposal'])

    def test_late_result_after_delete_cannot_resurrect(self):
        self.active();job=self.queue(self.image());adapter=BlockingAdapter();self.service.extractor=adapter
        thread=threading.Thread(target=self.service.run_one_job);thread.start();self.assertTrue(adapter.started.wait(2))
        self.service.delete_session(self.sid,self.token);adapter.release.set();thread.join(3)
        self.assertFalse(thread.is_alive());self.assertEqual('deleted',self.service.snapshot(self.sid,self.token)['state'])
        with self.service.db.transaction() as c:self.assertEqual(0,c.execute('SELECT count(*) FROM records').fetchone()[0])

    def test_source_revision_cancels_pending_job(self):
        self.active();source=self.image();job=self.queue(source)
        self.cmd('source.regions',{'source_id':source['id'],'expected_revision':1,'regions':[{'id':'new_area','box':[0,0,1,1]}]})
        self.assertFalse(self.service.run_one_job())
        self.assertEqual('cancelled',self.service.record(self.sid,self.token,job['id'])['data']['status'])

    def test_bad_adapter_output_is_atomic_and_error_safe(self):
        class Bad(FixtureExtractor):
            def extract(self,request):return ExtractionOutput(({'region_id':'foreign_id','text':'SECRET-OUTPUT','status':'readable'},),'fixture','bad',True,{})
        self.active();job=self.queue(self.image());self.service.extractor=Bad();self.service.run_one_job()
        snap=self.service.snapshot(self.sid,self.token)
        self.assertNotIn('SECRET-OUTPUT',json.dumps(snap))
        self.assertEqual('failed',self.service.record(self.sid,self.token,job['id'])['data']['status'])
        self.assertFalse(any(r['kind']=='proposal' for r in snap['records']))

    def test_job_deadline_and_startup_recovery(self):
        self.active();job=self.queue(self.image())
        with self.service.db.transaction() as c:
            r=self.service._get(c,self.sid,job['id']);d=r['data'];d.update(status='running',attempts=1)
            self.service._save(c,self.sid,r,d)
        self.service.recover_jobs();self.assertEqual('failed',self.service.record(self.sid,self.token,job['id'])['data']['status'])
        self.now+=61;self.service.run_one_job()
        self.assertEqual('interrupted_unknown_outcome',self.service.record(self.sid,self.token,job['id'])['data']['error'])

    def test_closed_session_and_replayed_close(self):
        self.active();self.accept(self.typed()['proposal']);key=new_key()
        payload={'expected_session_revision':self.service.snapshot(self.sid,self.token)['session']['revision']}
        closed=self.cmd('session.close',payload,key=key);self.assertEqual(closed,self.cmd('session.close',payload,key=key))
        self.problem('session_closed',lambda:self.typed())
        self.assertEqual(1,len(self.cmd('export.create',{'include_unresolved':False})['data']['records']))

    def test_export_is_frozen_and_escapes_html(self):
        self.active();first=self.typed('<script>alert(1)</script> [click](https://invalid.example)');item=self.accept(first['proposal'])
        export=self.cmd('export.create',{'include_unresolved':False})
        self.cmd('item.edit',{'item_id':item['id'],'expected_revision':1,'text':'Later edit','refs':item['data']['refs']})
        saved=self.service.record(self.sid,self.token,export['id'])
        self.assertNotIn('Later edit',saved['data']['markdown']);self.assertNotIn('<script>',saved['data']['markdown'])
        self.assertIn('&lt;script&gt;',saved['data']['markdown'])
        self.assertTrue(saved['data']['records'][0]['data']['text'].startswith('<script>'))

    def test_export_marks_and_excludes_unresolved_explicitly(self):
        self.active();p=self.typed()['proposal']
        excluded=self.cmd('export.create',{'include_unresolved':False})
        self.assertEqual([p['id']],excluded['data']['manifest']['omitted_ids'])
        included=self.cmd('export.create',{'include_unresolved':True})
        self.assertIn('needs_review',included['data']['markdown'])
        self.assertEqual(1,len(included['data']['records']))

    def test_delete_purges_all_content_and_survives_restart(self):
        self.active();sentinel='PRIVATE_SENTINEL_'+new_key();self.accept(self.typed(sentinel)['proposal'])
        self.cmd('export.create',{'include_unresolved':True});self.service.delete_session(self.sid,self.token)
        self.assertEqual('deleted',Service(self.path).snapshot(self.sid,self.token)['state'])
        with self.service.db.transaction() as c:
            for table in ('actors','records','versions','requests','events'):
                self.assertEqual(0,c.execute(f'SELECT count(*) FROM {table} WHERE session_id=?',(self.sid,)).fetchone()[0])
        self.assertNotIn(sentinel.encode(),self.path.read_bytes())
        self.assertTrue(self.service.delete_session(self.sid,self.token)['replayed'])

    def test_expiry_purges_and_lease_expiry_pauses(self):
        self.active();self.typed();self.now+=301
        self.assertEqual('paused',self.service.snapshot(self.sid,self.token)['session']['state'])
        self.now+=86400
        self.assertEqual('deleted',self.service.snapshot(self.sid,self.token)['state'])

    def test_unknown_fields_and_nonfinite_positions_rejected(self):
        self.active();self.problem('unknown_fields',lambda:self.cmd('source.text',{'text':'test','role':'facilitator'}))
        self.problem('unknown_operation',lambda:self.service.command(self.sid,self.token,new_key(),[],{}))
        self.problem('invalid_object',lambda:self.service.command(self.sid,self.token,new_key(),'source.text',[]))

    def test_rollback_includes_request_event_and_records(self):
        self.active();before=self.service.snapshot(self.sid,self.token)
        self.service.MAX_SESSION_BYTES=1
        self.problem('storage_capacity',lambda:self.typed())
        after=self.service.snapshot(self.sid,self.token)
        self.assertEqual(before,after)

    def test_events_have_ordered_cursors_without_source_text(self):
        self.active();self.typed('PRIVATE_SOURCE_TEXT');events=self.service.events(self.sid,self.token)
        seqs=[e['seq'] for e in events['events']];self.assertEqual(list(range(1,len(seqs)+1)),seqs)
        self.assertNotIn('PRIVATE_SOURCE_TEXT',json.dumps(events))
        self.assertEqual([],self.service.events(self.sid,self.token,events['next_after'])['events'])

    def test_manual_crop_transcription_without_adapter(self):
        self.active();source=self.image(1)
        proposal=self.cmd('proposal.create',{'proposal_kind':'content','text':'Human read the crop','region_id':'region_000',
            'refs':[{'id':source['id'],'revision':1}]})
        item=self.accept(proposal)
        self.assertEqual('human_transcribed',item['data']['reading_status'])
        self.assertEqual('human',item['data']['origin'])

    def test_unreadable_crop_requires_human_transcription(self):
        class Unreadable(FixtureExtractor):
            def extract(self,request):return ExtractionOutput(tuple({'region_id':r['id'],'text':'','status':'unreadable'} for r in request.regions),'fixture','unreadable-v1',True,{})
        self.active();source=self.image(1);job=self.queue(source);self.service.extractor=Unreadable();self.service.run_one_job()
        done=self.service.record(self.sid,self.token,job['id'])
        p=self.service.record(self.sid,self.token,done['data']['proposal_ids'][0])
        self.problem('unreadable_content',lambda:self.accept(p))
        fixed=self.cmd('proposal.edit',{'proposal_id':p['id'],'expected_revision':p['revision'],'text':'Manually transcribed','refs':p['data']['refs']})
        item=self.accept(fixed);self.assertEqual('fixture',item['data']['origin'])
        self.assertEqual('human_transcribed',item['data']['reading_status'])

    def test_removed_crop_cannot_be_rebound_by_text_edit(self):
        self.active();source=self.image(1)
        p=self.cmd('proposal.create',{'proposal_kind':'content','text':'Crop text','region_id':'region_000','refs':[{'id':source['id'],'revision':1}]})
        self.cmd('source.regions',{'source_id':source['id'],'expected_revision':1,'regions':[{'id':'replacement','box':[0,0,1,1]}]})
        stale=self.service.record(self.sid,self.token,p['id'])
        self.problem('invalid_region',lambda:self.cmd('proposal.edit',{'proposal_id':p['id'],'expected_revision':stale['revision'],
            'text':'New','refs':[{'id':source['id'],'revision':2}]}))

    def test_accepted_crop_edit_checks_region_binding(self):
        self.active();source=self.image(1)
        p=self.cmd('proposal.create',{'proposal_kind':'content','text':'Crop text','region_id':'region_000','refs':[{'id':source['id'],'revision':1}]})
        item=self.accept(p);other=self.typed()['source']
        self.problem('invalid_region',lambda:self.cmd('item.edit',{'item_id':item['id'],'expected_revision':1,
            'text':'Changed','refs':[{'id':other['id'],'revision':1}]}))
        self.assertEqual(1,self.service.record(self.sid,self.token,item['id'])['revision'])

    def test_storage_limit_does_not_block_pause_or_close(self):
        self.active();self.typed();self.service.MAX_SESSION_BYTES=1;self.service.MAX_REQUESTS=1
        self.assertEqual('paused',self.cmd('session.pause')['state'])
        self.assertEqual('closed',self.cmd('session.close')['state'])
        self.assertEqual('deleted',self.service.delete_session(self.sid,self.token)['state'])

    def test_job_completion_over_budget_has_no_partial_proposals(self):
        self.active();job=self.queue(self.image());self.service.MAX_SESSION_BYTES=1;self.service.run_one_job()
        done=self.service.record(self.sid,self.token,job['id'])
        self.assertEqual('failed',done['data']['status']);self.assertEqual('storage_capacity',done['data']['error'])
        self.assertFalse(any(r['kind']=='proposal' for r in self.service.snapshot(self.sid,self.token)['records']))


    # F1.1-F1.3 audio capture. Single-lane by design; see
    # decisions/decision-log.md for the two-lane and diarisation cuts.
    def pcm16(self,duration_ms=800):
        return base64.b64encode(b'\x00\x01'*int(16000*duration_ms/1000)).decode()

    def audio(self,duration_ms=800,ended_reason='silence'):
        return self.cmd('source.audio',{'mime':'audio/pcm16','base64':self.pcm16(duration_ms),'ended_reason':ended_reason})

    def test_audio_capture_requires_active_session(self):
        from unittest.mock import patch
        with patch.object(self.service.transcriber,'transcribe',wraps=self.service.transcriber.transcribe) as transcribe:
            self.problem('capture_inactive',lambda:self.audio())
            transcribe.assert_not_called()

    def test_audio_capture_produces_a_provenanced_transcript_segment(self):
        self.active();segment=self.audio()
        self.assertEqual('transcript_segment',segment['kind'])
        d=segment['data']
        self.assertEqual('final',d['status'])
        self.assertIn('FIXTURE ONLY',d['text'])
        self.assertEqual('fixture',d['provenance']['producer'])
        self.assertTrue(d['provenance']['synthetic'])
        self.assertIn('checksum',d['provenance'])
        # F1.3, per-connection fallback: the speaker is the sending actor.
        self.assertEqual(self.service.snapshot(self.sid,self.token)['actor_id'],d['speaker_actor_id'])
        self.assertEqual('per_connection',d['attribution'])

    def test_audio_capture_rejects_bad_ended_reason(self):
        self.active()
        self.problem('invalid_ended_reason',lambda:self.cmd('source.audio',
            {'mime':'audio/pcm16','base64':self.pcm16(800),'ended_reason':'whenever'}))

    def test_audio_chunk_duration_must_fit_the_endpointing_budget(self):
        self.active()
        self.problem('invalid_duration',lambda:self.cmd('source.audio',
            {'mime':'audio/pcm16','base64':self.pcm16(100),'ended_reason':'silence'}))

    def test_no_speech_does_not_create_a_transcript_or_event_and_retry_is_safe(self):
        from genai_server.adapters import TranscriptionFailure
        class Silence:
            name='local-whisper'
            calls=0
            def transcribe(self,request):
                self.calls+=1
                raise TranscriptionFailure('no_speech_detected')
        transcriber=Silence()
        self.service.transcriber=transcriber
        self.active()
        before=self.service.snapshot(self.sid,self.token)
        body={'mime':'audio/pcm16','base64':self.pcm16(800),'ended_reason':'silence'}
        result=self.cmd('source.audio',body,key='silent_audio_001')
        self.assertEqual({'status':'no_speech'},result)
        after=self.service.snapshot(self.sid,self.token)
        self.assertEqual(before['records'],after['records'])
        self.assertEqual(before['session']['seq'],after['session']['seq'])
        self.cmd('source.audio',body,key='silent_audio_001')
        self.assertEqual(1,transcriber.calls)

    def test_activation_display_correction_keeps_original_asr_evidence(self):
        from genai_server.adapters import TranscriptionOutput
        class MisheardName:
            name='test-asr'
            def transcribe(self,request):
                return TranscriptionOutput("Hey Jarvan's, make a summary.",.8,
                    'test-asr','test',False,{})
        self.service.transcriber=MisheardName()
        self.active()
        record=self.audio()
        self.assertEqual("Hey Jarvan's, make a summary.",record['data']['text'])
        self.assertEqual('Hey Jarvaids, make a summary.',record['data']['activation_correction']['text'])
        self.assertEqual('summary',record['data']['voice_command']['intent'])
        stored=self.service.snapshot(self.sid,self.token)['records']
        self.assertTrue(any(r['id']==record['id'] and r['data']==record['data'] for r in stored))

    def test_audio_capacity_can_actually_bind(self):
        """Lowering MAX_AUDIO_CHUNKS on the instance shadows the class
        constant a mutant would edit (same shadowing note as
        test_the_image_budget_can_actually_bind), so the class constant is
        checked directly: it must stay below the session record cap or it can
        never be the binding limit."""
        self.assertLessEqual(Service.MAX_AUDIO_CHUNKS,Service.MAX_RECORDS)

    def test_audio_capacity_binds(self):
        self.active();self.service.MAX_AUDIO_CHUNKS=1
        self.audio()
        self.problem('audio_capacity',lambda:self.audio())

    def test_a_failing_transcriber_writes_a_visible_gap_not_a_silent_drop(self):
        from genai_server.adapters import TranscriptionFailure
        class AlwaysFails:
            name='broken'
            def transcribe(self,request):raise TranscriptionFailure('boom')
        self.service.transcriber=AlwaysFails()
        self.active();segment=self.audio()
        self.assertEqual('gap',segment['data']['status'])
        self.assertIsNone(segment['data']['text'])
        self.assertEqual('broken',segment['data']['provenance']['producer'])

    def test_audio_capacity_can_actually_bind(self):
        """Lowering MAX_AUDIO_CHUNKS on the instance shadows the class
        constant a mutant would edit (same shadowing note as
        test_the_image_budget_can_actually_bind), so the class constant is
        checked directly: it must stay below the session record cap or it can
        never be the binding limit."""
        self.assertLessEqual(Service.MAX_AUDIO_CHUNKS,Service.MAX_RECORDS)

    def test_audio_capacity_binds(self):
        self.active();self.service.MAX_AUDIO_CHUNKS=1
        self.audio()
        self.problem('audio_capacity',lambda:self.audio())


def new_key():return secrets.token_hex(16)


if __name__=='__main__':unittest.main()
