"""Automatic intake contracts using fake providers, never OCR accuracy claims."""
import base64
from copy import deepcopy
import unittest

from genai_server.claude_extractor import ClaudeExtractor
from genai_server.adapters import ExtractionInput, ExtractionOutput
from genai_server.service import Service
from genai_server.voice_commands import COMMAND_EXAMPLES, CALENDAR_VIEW_EXAMPLES, lifecycle_examples, recognise_command
from tests.test_claude_extractor import FakeClient, message, note, wall
from tests import test_service as service_tests
from tests import test_polls as poll_tests
from tests import test_documents as document_tests
from tests.test_documents import patch


class AutomaticIntakeTests(unittest.TestCase):
    cmd = service_tests.ServiceTests.cmd
    active = service_tests.ServiceTests.active

    def setUp(self):
        service_tests.ServiceTests.setUp(self)
        self.service.automatic_workspace = True
        self.active()

    def records(self, kind):
        return [r for r in self.service.snapshot(self.sid,self.token)['records'] if r['kind']==kind]

    def test_typed_note_is_immediate_editable_and_undoable_without_human_acceptance(self):
        result=self.cmd('source.text',{'text':'Keep the interface simple'})
        items=self.records('item')
        self.assertEqual(1,len(items))
        item=items[0]
        self.assertTrue(item['data'].get('automatic'))
        self.assertNotIn('accepted_by',item['data'])
        self.assertEqual(result['proposal']['data']['item_id'],item['id'])
        self.assertEqual('human',item['data']['origin'])
        updated=self.cmd('item.edit',{'item_id':item['id'],'expected_revision':item['revision'],
            'text':'Keep it readable','refs':item['data']['refs']})['item']
        undone=self.cmd('item.undo',{'item_id':item['id'],'expected_revision':updated['revision'],'restore_revision':0})
        self.assertEqual('undone',undone['item']['data']['status'])

    def test_existing_waiting_inputs_are_applied_once_and_synced_on_restart(self):
        self.service.automatic_workspace=False
        self.cmd('source.text',{'text':'Already waiting'})
        before=self.service.snapshot(self.sid,self.token)['session']['seq']
        self.service=Service(self.path,clock=lambda:self.now,automatic_workspace=True)
        self.assertEqual(1,len(self.records('item')))
        self.assertNotIn('accepted_by',self.records('item')[0]['data'])
        events=self.service.events(self.sid,self.token,before)['events']
        self.assertTrue(any(e['type']=='workspace.input_applied' and e['data']['records'] for e in events))
        self.service=Service(self.path,clock=lambda:self.now,automatic_workspace=True)
        self.assertEqual(1,len(self.records('item')))

    def test_startup_never_applies_changed_source_references(self):
        self.service.automatic_workspace=False
        result=self.cmd('source.text',{'text':'Original text'})
        with self.service.db.transaction() as c:
            source=result['source']
            self.service._save(c,self.sid,source,{**source['data'],'text':'Changed without updating proposal'})
        self.service=Service(self.path,clock=lambda:self.now,automatic_workspace=True)
        self.assertEqual([],self.records('item'))

    def read_wall(self, answers):
        self.service.extractor=ClaudeExtractor(client=FakeClient(message(answers)))
        source=self.cmd('source.image',{'mime':'image/png','base64':base64.b64encode(wall()).decode()})
        job=self.cmd('extraction.queue',{'source_id':source['id'],'expected_revision':source['revision']})
        self.assertTrue(self.service.run_one_job())
        return self.records('job')[-1],source

    def test_whole_wall_adds_separate_notes_with_real_crop_refs_and_no_review_queue(self):
        job,source=self.read_wall([{**note('region_001','One\nTwo'),'box':[0,0,.5,1]},
            {**note('region_002','Drie'),'box':[.5,0,.5,1]}])
        self.assertEqual('succeeded',job['data']['status'])
        items=self.records('item')
        self.assertEqual(['One\nTwo','Drie'],[r['data']['text'] for r in items])
        self.assertEqual([], [p for p in self.records('proposal') if p['data']['status']=='needs_review'])
        for item in items:
            self.assertEqual('model',item['data']['origin'])
            self.assertNotIn('accepted_by',item['data'])
            ref=item['data']['refs'][0]
            self.assertEqual(2,ref['revision'])
            mime,data=self.service.crop(self.sid,self.token,source['id'],ref['revision'],item['data']['region_id'])
            self.assertEqual('image/png',mime);self.assertGreater(len(data),0)

    def test_invalid_detected_boxes_never_commit_items(self):
        for box in ([.9,0,.5,1], [0,0,0,1], [0,0,float('nan'),1]):
            with self.subTest(box=box):
                job,_=self.read_wall([{**note('region_001'),'box':box}])
                self.assertEqual('failed',job['data']['status'])
                self.assertEqual([],self.records('item'))

    def test_empty_wall_succeeds_without_inventing_a_note(self):
        job,_=self.read_wall([])
        self.assertEqual('succeeded',job['data']['status'])
        self.assertEqual([],self.records('item'))

    def test_detection_schema_avoids_array_bounds_rejected_by_live_provider(self):
        client=FakeClient(message([]))
        ClaudeExtractor(client=client).extract(ExtractionInput('source_001',1,'image/png',wall(),()))
        schema=client.requests[0]['output_config']['format']['schema']
        self.assertNotIn('maxItems',str(schema),'Live API rejected maxItems; enforce bounds locally')
        self.assertNotIn('minItems',str(schema),'Local validation owns array size')

    def test_parent_rejects_invalid_detection_even_if_adapter_omits_validation(self):
        class Unchecked:
            name='unchecked'
            def extract(self,request):
                return ExtractionOutput(({**note('region_001'),'box':[.9,0,.5,1]},),self.name,'test-only',False,{})
        self.service.extractor=Unchecked()
        source=self.cmd('source.image',{'mime':'image/png','base64':base64.b64encode(wall()).decode()})
        self.cmd('extraction.queue',{'source_id':source['id'],'expected_revision':source['revision']})
        self.service.run_one_job()
        self.assertEqual('failed',self.records('job')[-1]['data']['status'])
        self.assertEqual([],self.records('item'))

    def test_detector_rejects_duplicate_ids_and_more_than_sixty_notes(self):
        for answers in ([{**note('region_001'),'box':[0,0,.5,1]}]*2,
                [{**note(f'region_{i:03}'),'box':[0,0,1,1]} for i in range(61)]):
            failed=False
            try: ClaudeExtractor(client=FakeClient(message(answers))).extract(
                ExtractionInput('source_001',1,'image/png',wall(),()))
            except Exception: failed=True
            self.assertTrue(failed,'Invalid detections must be refused, not silently collapsed')

    def test_unreadable_note_is_visible_with_gap_and_source(self):
        job,_=self.read_wall([{**note('region_001','',status='unreadable'),'box':[0,0,1,1]}])
        self.assertEqual('succeeded',job['data']['status'])
        self.assertEqual('Unreadable note',self.records('item')[0]['data']['text'])
        self.assertEqual('unreadable',self.records('item')[0]['data']['reading_status'])

    def test_automatic_photo_capacity_is_terminal_and_never_partially_applied(self):
        self.service.MAX_RECORDS=len(self.service.snapshot(self.sid,self.token)['records'])+5
        self.service.extractor=ClaudeExtractor(client=FakeClient(message([
            {**note('region_001'),'box':[0,0,.5,1]},{**note('region_002'),'box':[.5,0,.5,1]}])))
        source=self.cmd('source.image',{'mime':'image/png','base64':base64.b64encode(wall()).decode()})
        self.cmd('extraction.queue',{'source_id':source['id'],'expected_revision':source['revision']})
        try:self.service.run_one_job()
        except Exception:pass  # The contract is a terminal job, never a stranded running one.
        job=self.records('job')[-1]
        self.assertEqual('failed',job['data']['status'])
        self.assertEqual('record_capacity',job['data']['error'])
        self.assertEqual([],self.records('item'))


class AutomaticPollTests(unittest.TestCase):
    cmd=poll_tests.PollTests.cmd;active=poll_tests.PollTests.active;records=poll_tests.PollTests.records
    poll=poll_tests.PollTests.poll;poll_cmd=poll_tests.PollTests.poll_cmd;utter=poll_tests.PollTests.utter;process=poll_tests.PollTests.process;draft=poll_tests.PollTests.draft

    def setUp(self):
        poll_tests.PollTests.setUp(self);self.service.automatic_workspace=True

    def test_definition_opens_without_confirmation_and_close_finishes_without_acceptance(self):
        self.draft()
        self.assertEqual('open',self.poll()['data']['state'])
        self.utter('I vote for salad')
        self.process(action='select',option_id=self.poll()['data']['options'][0]['id'])
        self.utter('Hey Jarvaids, close to voting list')
        poll=self.poll()
        self.assertEqual('closed',poll['data']['state'])
        self.assertEqual(1,sum(poll['data']['counts'].values()))
        self.assertNotIn('accepted_by',poll['data'])

    def test_closing_drains_queued_votes_before_finishing(self):
        self.draft();self.utter('I vote for salad')
        self.utter('Hey Jarvaids, clothe voting')
        self.assertEqual('closing',self.poll()['data']['state'])
        self.process(action='select',option_id=self.poll()['data']['options'][0]['id'])
        self.assertEqual('closed',self.poll()['data']['state'])
        self.assertEqual(1,sum(self.poll()['data']['counts'].values()))

    def test_unclear_reply_is_excluded_from_tally_without_blocking_finish(self):
        self.draft();self.utter('Maybe salad',speaker=None)
        self.process(action='select',option_id=self.poll()['data']['options'][0]['id'])
        self.utter('Hey Jarvaids, finish the poll')
        self.assertEqual('closed',self.poll()['data']['state'])
        self.assertEqual(0,sum(self.poll()['data']['counts'].values()))
        self.assertTrue(any(w['data']['status']=='clarify' for w in self.records('poll_work')))
        work=next(w for w in self.records('poll_work') if w['data']['status']=='clarify')
        self.poll_cmd('poll.resolve',work_id=work['id'],dismiss=False,
            speaker_profile_id=self.profiles[0]['id'],option_id=self.poll()['data']['options'][0]['id'])
        self.assertEqual('closed',self.poll()['data']['state'])
        self.assertEqual(1,sum(self.poll()['data']['counts'].values()))
        self.assertNotIn('accepted_by',self.poll()['data'])


class AutomaticDocumentTests(unittest.TestCase):
    cmd=document_tests.DocumentTests.cmd;active=document_tests.DocumentTests.active;records=document_tests.DocumentTests.records
    doc=document_tests.DocumentTests.doc;entries=document_tests.DocumentTests.entries;doc_cmd=document_tests.DocumentTests.doc_cmd
    utter=document_tests.DocumentTests.utter

    def setUp(self):
        document_tests.DocumentTests.setUp(self);self.service.automatic_workspace=True

    def test_close_needs_no_acceptance_and_new_command_can_create_next_list(self):
        self.utter('We should interview students')
        self.utter('Hey Jarvaids, make a to do list')
        self.model.results.append({'changes':[patch()]})
        self.assertTrue(self.service.run_one_document_job())
        self.assertEqual('Interview students',self.entries()[0]['data']['text'])
        self.utter('Hey Jarvaids, close the task list')
        self.assertEqual('reviewing',self.doc()['data']['state'])
        self.assertNotIn('accepted_by',self.doc()['data'])
        self.utter('Hey Jarvaids, create a task list')
        self.assertEqual(2,len(self.records('command_document')))
        self.assertEqual('collecting',self.doc()['data']['state'])

    def test_typed_commands_and_discussion_use_the_same_collectors(self):
        self.cmd('source.text',{'text':'We should interview students'})
        result=self.cmd('source.text',{'text':'Hey Jarvaids, make a task list'})
        self.assertIn('command',result)
        self.assertNotIn('proposal',result)
        self.model.results.append({'changes':[patch()]})
        self.assertTrue(self.service.run_one_document_job())
        self.assertEqual('Interview students',self.entries()[0]['data']['text'])
        self.cmd('source.text',{'text':'Hey Jarvaids, close the task list'})
        self.assertEqual('reviewing',self.doc()['data']['state'])


class PhraseCatalogueTests(unittest.TestCase):
    def test_ten_phrasings_for_each_creation_and_lifecycle_command(self):
        for intent,phrases in COMMAND_EXAMPLES.items():
            self.assertEqual(10,len(set(phrases)))
            for phrase in phrases:
                with self.subTest(phrase=phrase):
                    heard=recognise_command('Hey Jarvaids, could you please '+phrase+'?')
                    self.assertEqual(('recognised',intent),(heard['status'],heard['intent']))
        for (intent,field,action),phrases in lifecycle_examples().items():
            self.assertEqual(10,len(set(phrases)))
            for phrase in phrases:
                with self.subTest(phrase=phrase):
                    heard=recognise_command('Hey Jarvaids, please '+phrase+'.')
                    self.assertEqual((intent,action),(heard['intent'],heard.get(field)))

    def test_observed_close_voting_mishearings_and_direct_address(self):
        for phrase in ('close to voting list','clothe voting','no voting','news voting'):
            self.assertEqual('close',recognise_command('Hey Jarvaids, '+phrase)['poll_action'])
            self.assertIsNone(recognise_command('Someone said '+phrase))
        for phrase in ('do not close voting','close voting and create a task list','stop making polls'):
            self.assertEqual('unsupported',recognise_command('Hey Jarvaids, '+phrase)['status'])

    def test_ten_phrasings_for_each_calendar_view(self):
        for unit,phrases in CALENDAR_VIEW_EXAMPLES.items():
            self.assertEqual(10,len(set(phrases)))
            for phrase in phrases:
                with self.subTest(phrase=phrase):
                    heard=recognise_command('Hey Jarvaids, '+phrase)
                    self.assertEqual(('planning','view',unit),
                        (heard['intent'],heard.get('document_action'),heard.get('calendar_view')))
