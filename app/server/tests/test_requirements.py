"""Scripted requirement contracts, not measurements of live interpretation quality."""
import json
import unittest
from types import SimpleNamespace
from genai_server.document_model import ClaudeDocumentModel, REQUIREMENTS_SCHEMA, REQUIREMENTS_SYSTEM
from genai_server.poll_model import PollOutput
from genai_server.service import Service
from genai_server.validation import Problem
from genai_server.voice_commands import recognise_command
from tests import test_documents as document_tests


def proposal(**changes):
    return {'op': 'add', 'entry_id': '', 'text': 'Work offline', 'category': 'requirement',
        'basis': 'stated', 'stated_quote': 'must work offline', 'conflict': '', 'evidence': None, **changes}


class RequirementsTests(unittest.TestCase):
    setUp = document_tests.DocumentTests.setUp
    cmd = document_tests.DocumentTests.cmd
    active = document_tests.DocumentTests.active
    records = document_tests.DocumentTests.records
    doc = document_tests.DocumentTests.doc
    entries = document_tests.DocumentTests.entries
    doc_cmd = document_tests.DocumentTests.doc_cmd
    utter = document_tests.DocumentTests.utter
    process = document_tests.DocumentTests.process

    def create(self):
        self.utter('Hey Jarvaids, make a list of requirements and wishes.')
        return self.doc()

    def criterion(self):
        source = self.utter('It must work offline.')
        self.create()
        self.process(changes=[proposal(evidence=[{'source_id': source['id'], 'quote': source['data']['text']}])])
        return self.entries()[0]

    def edit(self, entry, **changes):
        task = {key: entry['data'][key] for key in ('text', 'category', 'basis', 'conflict')}
        return self.doc_cmd('document.entry.edit', entry_id=entry['id'], task={**task, **changes}, removed=False)

    def test_creation_requires_real_addressed_command(self):
        self.utter('We need a list of requirements.')
        self.utter('Hey Jarvaids, make a list of requirements.', synthetic=True)
        self.cmd('source.text', {'text': 'Hey Jarvaids, make a list of requirements.'})
        self.assertEqual([], self.records('command_document'))
        self.create()
        self.assertEqual('requirements', self.doc()['data']['document_type'])
        self.assertEqual(['todo', 'requirements', 'calendar'], self.service.snapshot(self.sid, self.token)['session']['command_ai']['types'])

    def test_history_explicit_wishes_and_inferred_suggestions(self):
        source = self.utter('It must work offline. We would prefer a green case. People struggle to read it.')
        self.create()
        evidence = [{'source_id': source['id'], 'quote': source['data']['text']}]
        self.process(changes=[proposal(evidence=evidence),
            proposal(text='A green case', category='wish', stated_quote='prefer a green case', evidence=evidence),
            proposal(text='Readable display', category='clarification', basis='inferred', stated_quote='', evidence=evidence)])
        self.assertEqual(['requirement', 'wish', 'clarification'], [e['data']['category'] for e in self.entries()])
        self.assertEqual('inferred', self.entries()[-1]['data']['basis'])
        self.assertTrue(all(e['data']['source_refs'] for e in self.entries()))

    def test_inference_cannot_become_a_requirement(self):
        self.create(); self.process()
        self.utter('People struggle to read it.')
        self.process(changes=[proposal(text='Readable display', basis='inferred', stated_quote='')])
        self.assertEqual([], self.entries())
        self.assertEqual('error', self.records('command_work')[-1]['data']['status'])

    def test_stated_criterion_requires_explicit_quote(self):
        self.create(); self.process(); self.utter('It must work offline.')
        self.process(changes=[proposal(stated_quote='')])
        self.assertEqual([], self.entries())

    def test_synthetic_criteria_cannot_become_live_entries(self):
        self.create(); self.process(); self.utter('It must work offline.')
        original = self.model.interpret
        self.model.results.append({'changes': [proposal()]})
        def synthetic(request):
            output = original(request)
            return PollOutput(output.data, output.provider, output.model, output.usage, synthetic=True)
        self.model.interpret = synthetic
        self.service.run_one_document_job()
        self.assertEqual([], self.entries())

    def test_invented_numeric_targets_are_rejected(self):
        self.create(); self.process()
        for target in ('Respond within 2 seconds', 'Respond within two seconds', 'Weigh under 10kg'):
            self.utter('It must respond quickly.')
            self.process(changes=[proposal(text=target, stated_quote='must respond quickly')])
            self.assertEqual([], self.entries())

    def test_stated_numeric_target_is_preserved(self):
        self.create(); self.process(); self.utter('It must weigh under 2 kg.')
        self.process(changes=[proposal(text='Weigh under 2 kg', stated_quote='must weigh under 2 kg')])
        self.assertEqual('Weigh under 2 kg', self.entries()[0]['data']['text'])

    def test_invented_evidence_is_rejected(self):
        self.create(); self.process(); source = self.utter('It must work offline.')
        request = {'document_type': 'requirements', 'lines': [{'id': source['id'], 'text': source['data']['text']}],
                   'entries': [], 'unresolved': []}
        data = {'changes': [proposal(stated_quote='must send email', evidence=[{'source_id': source['id'], 'quote': 'It must send email.'}])],
                'prompt': '', 'needs_clarification': False, 'resolutions': []}
        with self.assertRaises(Problem):
            self.service._document_validate(PollOutput(data, 'scripted', 'test', {}), request)

    def test_unknown_entry_cannot_be_updated(self):
        self.create(); self.process(); self.utter('It must work offline.')
        self.process(changes=[proposal(op='update', entry_id='unknown')])
        self.assertEqual([], self.entries())

    def test_conflicts_are_retained_and_block_acceptance_until_reviewed(self):
        entry = self.criterion()
        self.utter('It must always use the cloud.')
        self.process(changes=[proposal(text='Always use the cloud', category='clarification',
            stated_quote='must always use the cloud', conflict='Conflicts with Work offline.')])
        self.assertEqual(2, len(self.entries()))
        self.doc_cmd('document.close')
        with self.assertRaises(Problem) as caught: self.doc_cmd('document.accept')
        self.assertEqual('document_conflict', caught.exception.code)
        self.edit(self.entries()[-1], text='Cloud access is optional', category='wish', conflict='')
        self.doc_cmd('document.accept')
        self.assertEqual('accepted', self.doc()['data']['state'])
        self.assertEqual(entry['id'], self.entries()[0]['id'])

    def test_ai_cannot_hide_or_clear_a_conflict(self):
        self.create(); self.process(); self.utter('It must always use the cloud.')
        self.process(changes=[proposal(text='Always use the cloud', conflict='Conflicts with offline use.',
            category='clarification', stated_quote='must always use the cloud')])
        entry = self.entries()[0]
        self.utter('We still prefer offline use.')
        self.process(changes=[proposal(op='update', entry_id=entry['id'], text=entry['data']['text'],
            category='clarification', stated_quote='prefer offline use', conflict='')])
        self.assertTrue(self.entries()[0]['data']['conflict'])

    def test_conflict_cannot_be_hidden_in_requirement_section(self):
        self.create(); self.process(); self.utter('It must work offline.')
        self.process(changes=[proposal(conflict='Conflicts with cloud-only operation.')])
        self.assertEqual([], self.entries())

    def test_voice_reclassification_correction_removal_keep_identity(self):
        entry = self.criterion()
        self.utter('Actually offline use is a wish, not a requirement.')
        self.process(changes=[proposal(op='update', entry_id=entry['id'], category='wish', stated_quote='offline use is a wish')])
        self.assertEqual((entry['id'], 'wish'), (self.entries()[0]['id'], self.entries()[0]['data']['category']))
        self.utter('Remove the offline wish.')
        self.process(changes=[proposal(op='remove', entry_id=entry['id'], category='wish', stated_quote='Remove the offline wish')])
        self.assertTrue(self.entries()[0]['data']['removed'])

    def test_manual_correction_survives_delayed_ai_reply(self):
        entry = self.criterion(); self.utter('It must work online.')
        def late(request):
            self.edit(entry, text='Optional offline use', category='wish')
            return {'changes': [proposal(op='update', entry_id=entry['id'], text='Work online', stated_quote='must work online')]}
        self.model.results.append(late); self.service.run_one_document_job()
        self.assertEqual('Optional offline use', self.entries()[0]['data']['text'])
        self.assertEqual('stale', self.records('command_work')[-1]['data']['status'])

    def test_ambiguity_requires_review_and_retry_is_explicit(self):
        self.create(); self.process(); self.utter('Change that one.')
        self.process(needs_clarification=True, prompt='Which criterion should change?')
        self.utter('Hey Jarvis, close the requirements and wishes.')
        with self.assertRaises(Problem): self.doc_cmd('document.accept')
        work = self.records('command_work')[-1]
        with self.assertRaises(Problem): self.doc_cmd('document.retry', work_id=work['id'], acknowledge_unknown_cost=False)
        self.doc_cmd('document.retry', work_id=work['id'], acknowledge_unknown_cost=True); self.process()
        self.doc_cmd('document.accept')
        self.assertEqual('accepted', self.doc()['data']['state'])

    def test_closed_unaccepted_list_does_not_stop_transcript_or_todo_commands(self):
        self.criterion(); self.utter('Hey Jarvaids, close the requirements list.')
        doc = self.doc(); before = len(self.records('transcript_segment'))
        self.utter('We can discuss the next topic now.')
        self.cmd('source.text', {'text': 'A separate note during the meeting.'})
        self.utter('Hey Jarvaids, make a to-do list.')
        self.assertEqual(before + 2, len(self.records('transcript_segment')))
        self.assertEqual('active', self.service.snapshot(self.sid, self.token)['session']['state'])
        self.assertEqual(['reviewing', 'collecting'], [d['data']['state'] for d in self.records('command_document')])
        saved = next(d for d in self.records('command_document') if d['id'] == doc['id'])
        self.assertEqual('reviewing', saved['data']['state'])

    def test_independent_collectors_and_targeted_voice_lifecycle(self):
        self.criterion(); self.utter('Hey Jarvaids, make a to-do list.'); self.process()
        self.utter('Hey Jarvaids, close the requirements and wishes.')
        self.assertEqual(['reviewing', 'collecting'], [d['data']['state'] for d in self.records('command_document')])
        self.utter('Hey Jarvaids, accept the requirements and wishes.')
        self.assertEqual(['accepted', 'collecting'], [d['data']['state'] for d in self.records('command_document')])
        self.utter('Hey Jarvaids, reopen the requirements and wishes.')
        self.assertEqual(['collecting', 'collecting'], [d['data']['state'] for d in self.records('command_document')])
        self.utter('Hey Jarvaids, cancel the requirements and wishes.')
        self.assertEqual(['cancelled', 'collecting'], [d['data']['state'] for d in self.records('command_document')])

    def test_repeated_creation_deduplicates_and_refreshes(self):
        self.criterion(); self.create(); self.process()
        self.assertEqual(1, len(self.records('command_document')))
        self.assertEqual(1, len(self.entries()))
        self.assertEqual(2, self.doc()['data']['focus_request'])

    def test_acceptance_freezes_until_explicit_reopening(self):
        self.criterion(); self.utter('Hey Jarvaids, close the requirements.')
        self.utter('We have moved on.')
        self.assertFalse(self.service.run_one_document_job())
        self.utter('Hey Jarvaids, accept the requirements.')
        self.utter('It must work online.')
        self.assertFalse(self.service.run_one_document_job())
        self.utter('Hey Jarvaids, reopen the requirements.')
        self.assertEqual('collecting', self.doc()['data']['state'])
        self.assertIsNotNone(self.doc()['data']['accepted_snapshot'])

    def test_new_types_require_updated_agreement_for_old_sessions(self):
        self.criterion()
        with self.service.db.transaction() as c:
            marker = self.service._new(c, self.sid, 'command_policy', {'whole_meeting_text': True, 'types': ['todo']})
        restarted = Service(self.path, clock=lambda: self.now, document_model=self.model)
        self.assertEqual('paused', restarted.snapshot(self.sid, self.token)['session']['state'])

    def test_restart_preserves_review_and_never_repeats_uncertain_work(self):
        self.create()
        with self.service.db.transaction() as c:
            work = self.service._list(c, self.sid, 'command_work')[0]
            self.service._save(c, self.sid, work, {**work['data'], 'status': 'running'})
        self.service.recover_document_jobs()
        self.assertEqual('uncertain', self.records('command_work')[0]['data']['status'])
        self.assertFalse(self.service.run_one_document_job())


class RequirementsAdapterTests(unittest.TestCase):
    def test_requirements_use_their_own_prompt_and_schema(self):
        calls = []
        def create(**kwargs):
            calls.append(kwargs)
            return SimpleNamespace(stop_reason='end_turn', model='scripted', usage=SimpleNamespace(input_tokens=1, output_tokens=2),
                content=[SimpleNamespace(type='text', text=json.dumps({'changes': [], 'prompt': '', 'needs_clarification': False, 'resolutions': []}))])
        model = ClaudeDocumentModel(client=SimpleNamespace(messages=SimpleNamespace(create=create)))
        model.interpret({'document_type': 'requirements', 'lines': []})
        self.assertEqual(REQUIREMENTS_SYSTEM, calls[0]['system'])
        self.assertEqual(REQUIREMENTS_SCHEMA, calls[0]['output_config']['format']['schema'])

    def test_lifecycle_phrases_need_addressing_and_target_requirements(self):
        for verb, action in [('close', 'close'), ('accept', 'accept'), ('reopen', 'reopen'), ('cancel', 'cancel')]:
            heard = recognise_command('Hey Jarvis, '+verb+' the list of requirements and wishes.')
            self.assertEqual(('requirements', action), (heard.get('intent'), heard.get('document_action')))
            self.assertIsNone(recognise_command(verb+' the requirements.'))
