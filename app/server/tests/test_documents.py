"""Synthetic document contracts. They do not measure real speech or AI accuracy."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
import json
import threading
import unittest

from genai_server.document_model import ClaudeDocumentModel, SCHEMA
from genai_server.poll_model import PollOutput, PollModelFailure
from genai_server.service import Service
from genai_server.validation import Problem
from genai_server.voice_commands import recognise_command
from tests import test_service as service_tests


def patch(**changes):
    return {'op': 'add', 'entry_id': '', 'text': 'Interview students', 'owner': '',
        'owner_speaker_id': '', 'deadline': '', 'classification': 'suggested', 'done': False,
        'owner_quote': '', 'deadline_quote': '', 'commitment_quote': '', 'completion_quote': '',
        'evidence': None, **changes}


class ScriptModel:
    name = 'test-double'

    def __init__(self):
        self.results, self.requests = [], []

    def interpret(self, request):
        self.requests.append(deepcopy(request))
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        if callable(result):
            result = result(request)
        result = {'changes': [], 'prompt': '', 'needs_clarification': False, 'resolutions': [], **deepcopy(result)}
        for change in result['changes']:
            if change['evidence'] is None:
                line = request['lines'][-1]
                change['evidence'] = [{'source_id': line['id'], 'quote': line['text']}]
        return PollOutput(result, 'test-double', 'scripted-contract-only', {'input_tokens': 10, 'output_tokens': 10})


class DocumentTests(unittest.TestCase):
    cmd = service_tests.ServiceTests.cmd
    active = service_tests.ServiceTests.active

    def setUp(self):
        service_tests.ServiceTests.setUp(self)
        self.model = ScriptModel(); self.service.document_model = self.model
        self.active(); self.stamp = 0
        with self.service.db.transaction() as c:
            self.profiles = [self.service._new(c, self.sid, 'speaker_profile', {
                'name': name, 'provenance': {'synthetic': False}}) for name in ('Julie', 'Pieter')]

    def records(self, kind):
        return [r for r in self.service.snapshot(self.sid, self.token)['records'] if r['kind'] == kind]

    def doc(self):
        return self.records('command_document')[-1]

    def entries(self):
        return self.records('command_entry')

    def doc_cmd(self, op, **extra):
        doc = self.doc()
        return self.cmd(op, {'document_id': doc['id'], 'expected_revision': doc['revision'], **extra})

    def utter(self, value, speaker=0, synthetic=False, stamp=None, metadata=None):
        self.stamp += 1000
        with self.service.db.transaction() as c:
            s, a = self.service._auth(c, self.sid, self.token)
            source = self.service._new(c, self.sid, 'transcript_segment', {
                'text': value, 'status': 'final', 'voice_command': metadata or recognise_command(value, synthetic=synthetic),
                'created_at': self.now, 'capture_id': 'room_microphone',
                'captured_at_ms': self.stamp if stamp is None else stamp, 'speaker_actor_id': a['id'], 'author_id': a['id'],
                'speaker_profile_id': self.profiles[speaker]['id'] if speaker is not None else None,
                'attribution': 'voice_identified' if speaker is not None else 'unidentified',
                'provenance': {'synthetic': synthetic, 'speaker': {'synthetic': False}},
            })
            self.service._document_heard(c, s, a, source)
            self.service._event(c, self.sid, a['id'], 'test.audio', {})
        return source

    def create(self):
        self.utter('Hey Jarvaids, make a to-do list.')
        return self.doc()

    def process(self, **result):
        self.model.results.append(result)
        self.assertTrue(self.service.run_one_document_job())

    def task(self):
        self.create(); self.process()
        self.utter('Maybe we could interview students.')
        self.process(changes=[patch()])
        return self.entries()[0]

    def edit_task(self, entry, **changes):
        value = {key: entry['data'][key] for key in ('text', 'owner', 'deadline', 'classification', 'done')}
        return self.doc_cmd('document.entry.edit', entry_id=entry['id'], task={**value, **changes}, removed=False)

    def test_addressed_command_required_and_fixtures_do_not_start_lists(self):
        self.utter('We need a to-do list.')
        self.utter('Hey Jarvaids, make a to-do list.', synthetic=True)
        self.utter('Hey Jarvaids, make a to-do list.', synthetic=True,
                   metadata=recognise_command('Hey Jarvaids, make a to-do list.'))
        self.cmd('source.text', {'text': 'Hey Jarvaids, make a to-do list.'})
        self.assertEqual([], self.records('command_document'))

    def test_whole_history_is_batched_without_a_two_minute_cutoff(self):
        self.service.DOCUMENT_BATCH_LINES = 2
        earlier = self.utter('Maybe we could interview students.', stamp=1)
        self.utter('Other discussion.', stamp=500000)
        self.create()
        self.assertEqual(2, len(self.records('command_work')))
        self.process(changes=[patch(evidence=[{'source_id': earlier['id'], 'quote': earlier['data']['text']}])])
        self.process()
        self.assertEqual(3, sum(len(r['lines']) for r in self.model.requests))
        self.assertEqual('suggested', self.entries()[0]['data']['classification'])

    def test_named_owner_and_deadline_require_stated_quotes(self):
        self.create(); self.process()
        self.utter('Julie will prepare the questions by Friday.')
        self.process(changes=[patch(text='Prepare the questions', owner='Julie', owner_quote='Julie',
            deadline='Friday', deadline_quote='Friday', classification='agreed', commitment_quote='Julie will prepare the questions')])
        entry = self.entries()[0]['data']
        self.assertEqual(('Julie', 'Friday', 'agreed'), (entry['owner'], entry['deadline'], entry['classification']))

    def test_unknown_speaker_cannot_become_a_named_owner(self):
        self.create(); self.process(); self.utter('I will interview students.', speaker=None)
        self.process(changes=[patch(owner_speaker_id=self.profiles[0]['id'], owner_quote='I will')])
        self.assertEqual([], self.entries())
        self.assertEqual('error', self.records('command_work')[-1]['data']['status'])

    def test_first_person_assignment_uses_actual_identified_profile(self):
        self.create(); self.process(); self.utter('I will interview students.', speaker=1)
        self.process(changes=[patch(owner_speaker_id=self.profiles[1]['id'], owner_quote='I will',
            classification='agreed', commitment_quote='I will interview students')])
        self.assertEqual('Pieter', self.entries()[0]['data']['owner'])

    def test_missing_details_are_valid_and_never_filled_automatically(self):
        entry = self.task()['data']
        self.assertEqual(('', '', False), (entry['owner'], entry['deadline'], entry['done']))

    def test_invented_evidence_is_rejected(self):
        self.create(); self.process(); source = self.utter('Maybe we could interview students.')
        self.process(changes=[patch(evidence=[{'source_id': source['id'], 'quote': 'Invented words never spoken'}])])
        self.assertEqual([], self.entries())
        self.assertEqual('error', self.records('command_work')[-1]['data']['status'])

    def test_invented_owner_deadline_commitment_and_completion_are_rejected(self):
        for change in (dict(owner='Julie', owner_quote='Maybe'), dict(deadline='Friday', deadline_quote='Maybe'),
                       dict(classification='agreed'), dict(done=True)):
            with self.subTest(change=change):
                request = {'lines': [{'id': 'source_123', 'text': 'Maybe we could interview students.', 'speaker_id': None}],
                           'entries': [], 'unresolved': []}
                result = patch(**change, evidence=[{'source_id': 'source_123', 'quote': 'Maybe we could interview students.'}])
                output = PollOutput({'changes': [result], 'needs_clarification': False, 'prompt': '', 'resolutions': []}, 'test', 'test', {})
                with self.assertRaises(Problem): self.service._document_validate(output, request)

    def test_completion_updates_same_task_and_unrelated_speech_is_ignored(self):
        entry = self.task(); self.utter('I have finished interviewing students.')
        self.process(changes=[patch(op='update', entry_id=entry['id'], done=True, completion_quote='finished interviewing students')])
        self.utter('The weather is nice.'); self.process()
        self.assertEqual(1, len(self.entries()))
        self.assertTrue(self.entries()[0]['data']['done'])

    def test_clarification_can_be_resolved_by_a_current_spoken_reply(self):
        self.task(); self.utter('I can do that one.', speaker=None)
        self.process(needs_clarification=True, prompt='Who will interview students?')
        prior = self.records('command_work')[-1]
        source = self.utter('Julie will interview students.')
        self.process(resolutions=[{'work_id': prior['id'], 'source_id': source['id'], 'quote': source['data']['text']}])
        self.assertEqual('resolved', self.records('command_work')[-2]['data']['status'])

    def test_manual_edit_rejects_inflight_response(self):
        entry = self.task(); self.utter('Actually interview teachers instead.')
        started, release = threading.Event(), threading.Event()
        def block(request):
            started.set(); self.assertTrue(release.wait(5))
            return {'changes': [patch(op='update', entry_id=entry['id'], text='Interview teachers')]}
        self.model.results.append(block)
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self.service.run_one_document_job)
            self.assertTrue(started.wait(5)); self.edit_task(entry, text='Interview designers'); release.set()
            self.assertTrue(future.result())
        self.assertEqual('Interview designers', self.entries()[0]['data']['text'])
        self.assertEqual('stale', self.records('command_work')[-1]['data']['status'])

    def test_manual_edit_wins_over_earlier_queued_changes(self):
        entry = self.task(); self.utter('Actually interview teachers instead.')
        self.edit_task(entry, text='Interview designers')
        self.process(changes=[patch(op='update', entry_id=entry['id'], text='Interview teachers')])
        self.assertEqual('Interview designers', self.entries()[0]['data']['text'])

    def test_older_capture_cannot_overwrite_a_later_change(self):
        entry = self.task(); self.utter('Interview teachers instead.', stamp=9000)
        self.process(changes=[patch(op='update', entry_id=entry['id'], text='Interview teachers')])
        self.utter('Interview designers instead.', stamp=8000)
        self.process(changes=[patch(op='update', entry_id=entry['id'], text='Interview designers')])
        self.assertEqual('Interview teachers', self.entries()[0]['data']['text'])

    def test_repeated_creation_refreshes_one_list_and_duplicate_adds_are_ignored(self):
        self.task(); self.utter('Hey Jarvaids, make a to-do list.'); self.process(changes=[patch()])
        self.assertEqual(1, len(self.records('command_document')))
        self.assertEqual(1, len(self.entries()))
        self.assertEqual(2, self.doc()['data']['focus_request'])

    def test_voice_close_drains_work_then_accepts_and_reopens(self):
        self.create(); self.process(); self.utter('Maybe we could interview students.')
        self.utter('Hey Jarvis, close the to-do list.')
        self.assertEqual('reviewing', self.doc()['data']['state'])
        self.utter('Hey Jarvaids, accept the to-do list.')
        self.assertEqual('reviewing', self.doc()['data']['state'])
        self.process(changes=[patch()])
        self.utter('Hey Jarvaids, accept the to-do list.')
        self.assertEqual('accepted', self.doc()['data']['state'])
        self.utter('I finished everything.')
        self.assertFalse(self.service.run_one_document_job())
        self.utter('Hey Jarvaids, reopen the to-do list.')
        self.assertEqual('collecting', self.doc()['data']['state'])
        self.assertIsNotNone(self.doc()['data']['accepted_snapshot'])

    def test_cancellation_blocks_late_interpretations(self):
        self.create(); self.process(); self.utter('Maybe we could interview students.')
        def cancel(request):
            self.doc_cmd('document.cancel')
            return {'changes': [patch()]}
        self.model.results.append(cancel)
        self.service.run_one_document_job()
        self.assertEqual([], self.entries())
        self.assertEqual('cancelled', self.doc()['data']['state'])

    def test_synthetic_output_is_not_a_live_task(self):
        self.create(); self.process(); self.utter('Maybe we could interview students.')
        original = self.model.interpret
        self.model.results.append({'changes': [patch()]})
        def synthetic(request):
            output = original(request)
            return PollOutput(output.data, output.provider, output.model, output.usage, synthetic=True)
        self.model.interpret = synthetic; self.service.run_one_document_job()
        self.assertEqual([], self.entries())

    def test_restart_marks_running_work_uncertain_and_never_repeats_it(self):
        self.create()
        with self.service.db.transaction() as c:
            work = self.service._list(c, self.sid, 'command_work')[0]
            self.service._save(c, self.sid, work, {**work['data'], 'status': 'running'})
        self.service.recover_document_jobs()
        self.assertEqual('uncertain', self.records('command_work')[0]['data']['status'])
        self.assertFalse(self.service.run_one_document_job())

    def test_error_requires_explicit_cost_acknowledgement_to_retry(self):
        self.create(); self.model.results.append(RuntimeError('PRIVATE SOURCE AND KEY'))
        self.service.run_one_document_job(); work = self.records('command_work')[0]
        self.assertNotIn('PRIVATE', work['data']['error'])
        with self.assertRaises(Problem):
            self.doc_cmd('document.retry', work_id=work['id'], acknowledge_unknown_cost=False)
        self.doc_cmd('document.retry', work_id=work['id'], acknowledge_unknown_cost=True)
        self.process()
        self.assertEqual('done', self.records('command_work')[0]['data']['status'])

    def test_capacity_is_visible_and_incomplete_acceptance_needs_acknowledgement(self):
        self.service.MAX_DOCUMENT_WORK = 0; self.create()
        self.assertEqual(1, self.doc()['data']['uncovered'])
        self.doc_cmd('document.close')
        with self.assertRaises(Problem): self.doc_cmd('document.accept')
        self.doc_cmd('document.accept', acknowledge_incomplete=True)
        self.assertEqual('accepted', self.doc()['data']['state'])

    def test_list_can_move_and_stale_edits_are_refused(self):
        self.create(); doc = self.doc()
        self.cmd('item.place', {'placements': [{'id': doc['id'], 'x': 400, 'y': 50, 'expected_position_revision': 0}]})
        self.assertEqual('collecting', self.doc()['data']['state'])
        self.assertEqual(400, self.doc()['position']['x'])
        self.doc_cmd('document.edit', title='Actions')
        with self.assertRaises(Problem):
            self.cmd('document.edit', {'document_id': doc['id'], 'expected_revision': doc['revision'], 'title': 'Old edit'})

    def test_enabling_whole_meeting_cloud_text_requires_new_agreement(self):
        self.create(); before = self.service.snapshot(self.sid, self.token)['session']['policy_version']
        service = Service(self.path, clock=lambda: self.now, document_model=self.model)
        snapshot = service.snapshot(self.sid, self.token)
        self.assertEqual('paused', snapshot['session']['state'])
        self.assertGreater(snapshot['session']['policy_version'], before)
        self.assertTrue(snapshot['session']['command_ai']['whole_meeting_text'])

    def test_other_document_types_are_not_enabled_yet(self):
        self.utter('Hey Jarvaids, make a summary.')
        self.assertEqual([], self.records('command_document'))
        with self.assertRaises(Problem): self.cmd('document.create', {'document_type': 'unsupported'})

    def test_pausing_before_claim_prevents_a_provider_call(self):
        self.create(); self.cmd('session.pause')
        self.assertTrue(self.service.run_one_document_job())
        self.assertEqual([], self.model.requests)

    def test_pausing_during_interpretation_prevents_committing_output(self):
        self.create()
        def pause(request):
            self.cmd('session.pause')
            return {'changes': [patch()]}
        self.model.results.append(pause); self.service.run_one_document_job()
        self.assertEqual([], self.entries())
        self.assertEqual('stale', self.records('command_work')[0]['data']['status'])

    def test_transcript_change_during_interpretation_is_not_committed(self):
        self.create()
        def correct(request):
            with self.service.db.transaction() as c:
                source = self.service._get(c, self.sid, request['lines'][0]['id'], 'transcript_segment')
                self.service._save(c, self.sid, source, {**source['data'], 'text': 'Corrected source text.'})
            return {'changes': [patch()]}
        self.model.results.append(correct); self.service.run_one_document_job()
        self.assertEqual([], self.entries())
        self.assertEqual('uncertain', self.records('command_work')[0]['data']['status'])

    def test_oversized_transcript_line_is_not_sent_to_the_provider(self):
        self.utter('x' * (self.service.DOCUMENT_BATCH_CHARS + 1)); self.create()
        self.service.run_one_document_job()
        self.assertEqual([], self.model.requests)
        self.assertEqual('stale', self.records('command_work')[0]['data']['status'])

    def test_missing_ai_allows_manual_tasks_and_explicit_partial_acceptance(self):
        self.service.document_model = None; self.create()
        self.assertEqual('error', self.records('command_work')[0]['data']['status'])
        self.doc_cmd('document.entry.edit', entry_id='', task={'text': 'Review the prototype',
            'owner': '', 'deadline': '', 'classification': 'agreed', 'done': False}, removed=False)
        self.doc_cmd('document.close')
        with self.assertRaises(Problem): self.doc_cmd('document.accept')
        self.doc_cmd('document.resolve', work_id=self.records('command_work')[0]['id'])
        with self.assertRaises(Problem): self.doc_cmd('document.accept')
        self.doc_cmd('document.accept', acknowledge_incomplete=True)
        self.assertEqual('accepted', self.entries()[0]['data']['status'])
        self.assertEqual('human', self.entries()[0]['data']['origin'])

    def test_removed_tasks_are_not_recreated_by_old_additions(self):
        entry = self.task()
        task = {key: entry['data'][key] for key in ('text', 'owner', 'deadline', 'classification', 'done')}
        self.doc_cmd('document.entry.edit', entry_id=entry['id'], task=task, removed=True)
        self.utter('Maybe we could interview students.'); self.process(changes=[patch()])
        self.assertEqual(1, len(self.entries()))
        self.assertTrue(self.entries()[0]['data']['removed'])

    def test_new_task_identifier_and_removal_are_strict(self):
        self.create()
        task = {'text': 'Review the prototype', 'owner': '', 'deadline': '', 'classification': 'suggested', 'done': False}
        for value in (None, False, [], {}):
            with self.subTest(entry_id=value):
                with self.assertRaises(Problem):
                    self.doc_cmd('document.entry.edit', entry_id=value, task=task, removed=False)
        with self.assertRaises(Problem):
            self.doc_cmd('document.entry.edit', entry_id='', task=task, removed=True)


class DocumentAdapterTests(unittest.TestCase):
    def test_structured_output_and_actual_usage_are_retained(self):
        calls = []
        def create(**kwargs):
            calls.append(kwargs)
            return SimpleNamespace(stop_reason='end_turn', model='test-returned', content=[SimpleNamespace(type='text', text=json.dumps({
                'changes': [], 'prompt': '', 'needs_clarification': False, 'resolutions': []}))],
                usage=SimpleNamespace(input_tokens=2, output_tokens=3))
        output = ClaudeDocumentModel(client=SimpleNamespace(messages=SimpleNamespace(create=create))).interpret({'lines': []})
        self.assertEqual(SCHEMA, calls[0]['output_config']['format']['schema'])
        self.assertEqual({'input_tokens': 2, 'output_tokens': 3}, output.usage)

    def test_provider_exceptions_are_safe(self):
        def create(**kwargs): raise RuntimeError('PRIVATE SOURCE AND KEY')
        model = ClaudeDocumentModel(client=SimpleNamespace(messages=SimpleNamespace(create=create)))
        with self.assertRaises(PollModelFailure) as caught: model.interpret({})
        self.assertNotIn('PRIVATE', str(caught.exception))
