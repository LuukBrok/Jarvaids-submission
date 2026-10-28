"""Calendar/date/shared-task contracts with scripted models, never live quality evidence."""
from datetime import datetime, timezone
import base64
from types import SimpleNamespace
import json
import unittest
from genai_server.calendar_dates import resolve_date, resolve_time, local_day, zone_name
from genai_server.calendar_model import CALENDAR_SCHEMA, CALENDAR_SYSTEM, validate_calendar
from genai_server.document_model import ClaudeDocumentModel
from genai_server.poll_model import PollOutput
from genai_server.validation import Problem
from genai_server.service import Service
from genai_server.voice_commands import recognise_command
from tests import test_documents as documents


def event(**changes):
    return {'op': 'add', 'entry_id': '', 'task_id': '', 'text': 'Prototype review', 'date_phrase': 'tomorrow',
        'date_quote': 'tomorrow', 'time_phrase': '', 'done': False, 'done_quote': '', 'evidence': None, **changes}


class ScriptModel(documents.ScriptModel):
    def interpret(self, request):
        output = super().interpret(request)
        if request['document_type'] == 'calendar':
            output.data.setdefault('focus', {'view': '', 'phrase': '', 'source_id': ''})
        return output


class CalendarTests(unittest.TestCase):
    cmd = documents.DocumentTests.cmd
    active = documents.DocumentTests.active
    records = documents.DocumentTests.records
    utter = documents.DocumentTests.utter
    process = documents.DocumentTests.process
    doc_cmd = documents.DocumentTests.doc_cmd

    def setUp(self):
        documents.DocumentTests.setUp(self)
        self.model = ScriptModel(); self.service.document_model = self.model
        self.now = datetime(2026, 10, 19, 12, tzinfo=timezone.utc).timestamp()
        with self.service.db.transaction() as c:
            c.execute('UPDATE sessions SET created=?,expires=?,lease=? WHERE id=?', (self.now, self.now+86400, self.now+300, self.sid))
            self.service._new(c, self.sid, 'session_clock', {'timezone': 'Europe/Amsterdam'})

    def doc(self):
        return [d for d in self.records('command_document') if d['data']['document_type'] == 'calendar'][-1]

    def events(self):
        return [e for e in self.records('command_entry') if e['data']['entry_type'] == 'calendar_event']

    def task(self):
        return [e for e in self.records('command_entry') if e['data']['entry_type'] == 'task'][0]

    def create(self, phrase='Hey Jarvaids, make an agenda.'):
        self.utter(phrase); return self.doc()

    def seeded(self):
        source = self.utter('The prototype review is tomorrow at 2 pm.')
        self.create(); self.process(changes=[event(time_phrase='2 pm', evidence=[{'source_id': source['id'], 'quote': source['data']['text']}])])
        return self.events()[0]

    def process_for(self, document_type, **result):
        docs = {doc['id']: doc['data']['document_type'] for doc in self.records('command_document')}
        while True:
            queued = [work for work in self.records('command_work') if work['data']['status'] == 'queued']
            self.assertTrue(queued)
            if docs[queued[0]['data']['document_id']] == document_type:
                return self.process(**result)
            self.process()

    def todo(self):
        self.utter('Hey Jarvaids, make a to-do list.'); self.process_for('todo')
        self.utter('I will interview students by tomorrow.')
        self.process_for('todo', changes=[documents.patch(text='Interview students', classification='agreed',
            commitment_quote='I will interview students', owner_speaker_id=self.profiles[0]['id'],
            owner_quote='I will interview students', deadline='tomorrow', deadline_quote='tomorrow')])
        return self.task()

    def edit(self, entry, **changes):
        value = {key: entry['data'][key] for key in ('text', 'date', 'time', 'done')}
        return self.doc_cmd('calendar.entry.edit', entry_id=entry['id'], expected_entry_revision=entry['revision'],
            task_id='', value={**value, **changes}, removed=False)

    def test_voice_creation_history_and_default_current_month(self):
        self.seeded(); doc = self.doc()['data']; entry = self.events()[0]['data']
        self.assertEqual(('calendar', 'month', '2026-10-19', 'Europe/Amsterdam'),
            (doc['document_type'], doc['calendar_view'], doc['calendar_date'], doc['timezone']))
        self.assertEqual(('2026-10-20', '14:00', 'tomorrow'), (entry['date'], entry['time'], entry['date_phrase']))
        self.assertEqual(2, len(self.model.requests[-1]['lines']))

    def test_requested_period_and_view_changes_do_not_change_content(self):
        self.create('Hey Jarvaids, make a calendar for next week.'); self.process()
        self.assertEqual(('week', '2026-10-26'), (self.doc()['data']['calendar_view'], self.doc()['data']['calendar_date']))
        for view in ('day', 'week', 'month', 'year'):
            self.utter('Hey Jarvaids, show '+view+' view.')
            self.assertEqual(view, self.doc()['data']['calendar_view'])
        self.assertEqual([], self.events())

    def test_unscheduled_events_have_no_invented_date(self):
        self.create(); self.process(); self.utter('We should have a design review.')
        self.process(changes=[event(date_phrase='', date_quote='')])
        self.assertEqual('', self.events()[0]['data']['date'])

    def test_ambiguous_dates_remain_unscheduled_with_question(self):
        self.create(); self.process(); self.utter('The prototype review is next Friday.')
        self.process(changes=[event(date_phrase='next Friday', date_quote='next Friday')])
        self.assertEqual('', self.events()[0]['data']['date'])
        self.assertIn('upcoming', self.events()[0]['data']['clarification'])

    def test_unstated_date_and_invented_evidence_are_rejected(self):
        self.create(); self.process(); self.utter('The prototype review has no date yet.')
        self.process(changes=[event()])
        self.assertEqual([], self.events())
        self.utter('The prototype review is tomorrow.')
        self.process(changes=[event(evidence=[{'source_id': 'invented', 'quote': 'tomorrow'}])])
        self.assertEqual([], self.events())

    def test_date_is_anchored_to_source_not_worker_execution_day(self):
        self.now = datetime(2026, 10, 19, 22, 0, 5, tzinfo=timezone.utc).timestamp()
        captured = self.now-10
        with self.service.db.transaction() as c:
            c.execute('UPDATE sessions SET created=?,expires=?,lease=? WHERE id=?', (captured-60, self.now+86400, self.now+300, self.sid))
        source = self.utter('The prototype review is tomorrow.')
        # The captured chunk ended before local midnight; ASR completed after it.
        with self.service.db.transaction() as c:
            source = self.service._get(c, self.sid, source['id'], 'transcript_segment')
            self.service._save(c, self.sid, source, {**source['data'], 'captured_at_utc_ms': int(captured*1000)})
        self.create(); self.process(changes=[event(evidence=[{'source_id': source['id'], 'quote': source['data']['text']}])])
        self.assertEqual('2026-10-20', self.events()[0]['data']['date'])

    def test_event_identity_correction_and_removal(self):
        entry = self.seeded(); self.utter('Actually the prototype review is Friday.')
        self.process(changes=[event(op='update', entry_id=entry['id'], date_phrase='Friday', date_quote='Friday')])
        self.assertEqual((entry['id'], '2026-10-23'), (self.events()[0]['id'], self.events()[0]['data']['date']))
        self.utter('Cancel the prototype review.')
        self.process(changes=[event(op='remove', entry_id=entry['id'], date_phrase='Friday', date_quote='')])
        self.assertTrue(self.events()[0]['data']['removed'])

    def test_unknown_event_identity_is_rejected(self):
        self.create(); self.process(); self.utter('The review is tomorrow.')
        self.process(changes=[event(op='update', entry_id='unknown')])
        self.assertEqual([], self.events())

    def test_manual_event_edit_survives_inflight_response(self):
        entry = self.seeded(); self.utter('The prototype review is Friday.')
        def late(request):
            self.edit(entry, date='2026-10-22')
            return {'changes': [event(op='update', entry_id=entry['id'], date_phrase='Friday', date_quote='Friday')]}
        self.model.results.append(late); self.service.run_one_document_job()
        self.assertEqual('2026-10-22', self.events()[0]['data']['date'])
        self.assertEqual('stale', self.records('command_work')[-1]['data']['status'])

    def test_manual_event_creation_uses_the_supplied_date_and_time(self):
        self.create(); self.process()
        self.doc_cmd('calendar.entry.edit', entry_id='', task_id='', removed=False,
            value={'text': 'Team lunch', 'date': '2026-10-22', 'time': '12:30', 'done': False, 'date_changed': True})
        self.assertEqual(1, len(self.events()))
        entry = self.events()[0]['data']
        self.assertEqual(('Team lunch', '2026-10-22', '12:30', 'human'), (entry['text'], entry['date'], entry['time'], entry['origin']))

    def note(self, value='Book the lab for user tests'):
        proposal = self.cmd('source.text', {'text': value})['proposal']
        return self.cmd('proposal.review', {'proposal_id': proposal['id'], 'expected_revision': proposal['revision'], 'decision': 'accept'})['item']

    def add_from_note(self, note_id, date='2026-10-22'):
        return self.doc_cmd('calendar.entry.edit', entry_id='', task_id='', removed=False, note_id=note_id,
            value={'text': 'Book the lab for user tests', 'date': date, 'time': '', 'done': False, 'date_changed': True})

    def test_manual_event_from_a_note_keeps_its_note_link_through_edit_and_removal(self):
        self.create(); self.process(); note = self.note()
        self.add_from_note(note['id'])
        entry = self.events()[0]
        self.assertEqual((note['id'], '2026-10-22', [], 'human'),
            (entry['data'].get('note_id'), entry['data']['date'], entry['data']['source_refs'], entry['data']['origin']))
        self.edit(entry, date='2026-10-23')
        entry = self.events()[0]
        self.assertEqual((note['id'], '2026-10-23'), (entry['data'].get('note_id'), entry['data']['date']))
        value = {key: entry['data'][key] for key in ('text', 'date', 'time', 'done')}
        self.doc_cmd('calendar.entry.edit', entry_id=entry['id'], expected_entry_revision=entry['revision'],
            task_id='', value={**value, 'date_changed': False}, removed=True)
        self.assertEqual((note['id'], True), (self.events()[0]['data'].get('note_id'), self.events()[0]['data']['removed']))

    def test_calendar_note_link_must_name_a_note_on_the_canvas(self):
        self.create(); self.process()
        undone = self.note('An idea we dropped')
        self.cmd('item.undo', {'item_id': undone['id'], 'expected_revision': undone['revision'], 'restore_revision': 0})
        shape = self.cmd('canvas.create', {'kind': 'shape', 'data': {'shape': 'rect', 'tone': 'accent', 'text': 'Box'},
            'x': 0, 'y': 0, 'w': 100, 'h': 80})['item']
        for target in (undone['id'], shape['id'], self.doc()['id']):
            with self.assertRaises(Problem) as caught:
                self.add_from_note(target)
            self.assertEqual('calendar_note', caught.exception.code)
        self.assertEqual([], self.events())

    def test_calendar_note_link_is_only_set_on_a_new_event(self):
        task = self.todo(); self.create(); self.process(); note = self.note()
        self.add_from_note(note['id']); entry = self.events()[0]
        other = self.note('Another note')
        value = {key: entry['data'][key] for key in ('text', 'date', 'time', 'done')}
        with self.assertRaises(Problem) as caught:
            self.doc_cmd('calendar.entry.edit', entry_id=entry['id'], expected_entry_revision=entry['revision'],
                task_id='', value={**value, 'date_changed': False}, removed=False, note_id=other['id'])
        self.assertEqual('calendar_note', caught.exception.code)
        with self.assertRaises(Problem) as caught:
            self.doc_cmd('calendar.entry.edit', entry_id='', task_id=task['id'], expected_task_revision=self.task()['revision'],
                value={'text': task['data']['text'], 'date': '2026-10-22', 'time': '', 'done': False}, removed=False, note_id=other['id'])
        self.assertEqual('calendar_note', caught.exception.code)
        self.assertEqual(note['id'], self.events()[0]['data'].get('note_id'))
        self.assertNotIn('note_id', self.task()['data'])

    def test_stale_manual_event_revision_does_not_replace_newer_date(self):
        entry = self.seeded(); self.edit(entry, date='2026-10-22')
        with self.assertRaises(Problem): self.edit(entry, date='2026-10-23')
        self.assertEqual('2026-10-22', self.events()[0]['data']['date'])

    def test_older_capture_cannot_overwrite_newer_event(self):
        entry = self.seeded(); self.utter('The review is Friday.', stamp=9000)
        self.process(changes=[event(op='update', entry_id=entry['id'], date_phrase='Friday', date_quote='Friday')])
        self.utter('The review is tomorrow.', stamp=8000)
        self.process(changes=[event(op='update', entry_id=entry['id'])])
        self.assertEqual('2026-10-23', self.events()[0]['data']['date'])

    def test_calendar_links_existing_task_id_and_updates_both_views(self):
        task = self.todo(); self.create(); self.process()
        self.assertEqual([task['id']], self.doc()['data']['task_ids'])
        self.assertEqual('2026-10-20', self.task()['data']['deadline_date'])
        self.utter('The student interviews are due Friday.')
        self.process_for('calendar', changes=[event(op='update', task_id=task['id'], text=task['data']['text'], date_phrase='Friday', date_quote='Friday')])
        self.assertEqual((task['id'], 'Friday', '2026-10-23'),
            (self.task()['id'], self.task()['data']['deadline'], self.task()['data']['deadline_date']))
        self.assertEqual(1, len([e for e in self.records('command_entry') if e['data']['entry_type'] == 'task']))

    def test_new_todo_tasks_attach_to_collecting_calendar(self):
        self.create(); self.process(); task = self.todo()
        # Each source queues one job per collecting type; drain the scripted no-op batches.
        while any(w['data']['status'] == 'queued' for w in self.records('command_work')):
            self.process()
        self.assertIn(task['id'], self.doc()['data']['task_ids'])

    def test_unknown_shared_task_cannot_be_scheduled(self):
        self.create(); self.process(); self.utter('The interviews are due tomorrow.')
        self.process(changes=[event(op='update', task_id='not-a-task')])
        self.assertEqual([], self.events())
        self.assertEqual([], self.doc()['data']['task_ids'])

    def test_manual_calendar_task_completion_is_shared_and_revision_checked(self):
        task = self.todo(); self.create(); self.process()
        args = {'entry_id': '', 'task_id': task['id'], 'expected_task_revision': self.task()['revision'],
            'value': {'text': task['data']['text'], 'date': '2026-10-23', 'time': '', 'done': True}, 'removed': False}
        self.doc_cmd('calendar.entry.edit', **args)
        self.assertTrue(self.task()['data']['done'])
        self.assertEqual('2026-10-23', self.task()['data']['deadline_date'])
        with self.assertRaises(Problem): self.doc_cmd('calendar.entry.edit', **args)

    def test_accepting_calendar_confirms_visible_shared_tasks(self):
        task = self.todo(); self.create(); self.process(); self.doc_cmd('document.close'); self.doc_cmd('document.accept')
        self.assertEqual('accepted', self.task()['data']['status'])
        self.assertEqual(task['id'], self.doc()['data']['linked_snapshot'][0]['id'])

    def accepted_task_change(self):
        task = self.todo(); self.create(); self.process(); self.doc_cmd('document.close'); self.doc_cmd('document.accept')
        self.doc_cmd('document.reopen')
        while any(w['data']['status'] == 'queued' for w in self.records('command_work')): self.process()
        self.utter('The student interviews are due Friday.')
        # The still-collecting to-do list is queued first, followed by the calendar.
        self.process(); self.process_for('calendar', changes=[event(op='update', task_id=task['id'], text=task['data']['text'], date_phrase='Friday', date_quote='Friday')])
        changes = self.records('command_task_change')
        self.assertEqual(1, len(changes))
        return task, changes[0]

    def test_ai_cannot_replace_accepted_shared_task_without_review(self):
        task, change = self.accepted_task_change()
        self.assertEqual('2026-10-20', self.task()['data']['deadline_date'])
        self.assertEqual('pending', change['data']['state'])
        self.doc_cmd('calendar.task.resolve', change_id=change['id'], expected_change_revision=change['revision'], accept=True)
        self.assertEqual((task['id'], '2026-10-23'), (self.task()['id'], self.task()['data']['deadline_date']))
        self.assertEqual('accepted', self.task()['data']['status'])

    def test_stale_task_proposal_requires_fresh_review(self):
        task, change = self.accepted_task_change()
        with self.service.db.transaction() as c:
            current = self.service._get(c, self.sid, task['id'], 'command_entry')
            self.service._save(c, self.sid, current, {**current['data'], 'text': 'A human corrected this task'})
        with self.assertRaises(Problem):
            self.doc_cmd('calendar.task.resolve', change_id=change['id'], expected_change_revision=change['revision'], accept=True)
        self.assertEqual('A human corrected this task', self.task()['data']['text'])

    def test_pending_task_proposal_blocks_whole_calendar_acceptance(self):
        _, change = self.accepted_task_change(); self.doc_cmd('document.close')
        with self.assertRaises(Problem): self.doc_cmd('document.accept')
        self.doc_cmd('calendar.task.resolve', change_id=change['id'], expected_change_revision=change['revision'], accept=False)
        self.doc_cmd('document.accept')
        self.assertEqual('accepted', self.doc()['data']['state'])

    def test_close_accept_reopen_cancel_and_unrelated_transcript(self):
        self.seeded(); self.utter('Hey Jarvaids, close the agenda.')
        self.utter('We can discuss lunch now.')
        self.assertFalse(self.service.run_one_document_job())
        self.utter('Hey Jarvaids, accept the calendar.')
        self.assertEqual('accepted', self.doc()['data']['state'])
        self.utter('Hey Jarvis, reopen the agenda.')
        self.assertEqual('collecting', self.doc()['data']['state'])
        self.utter('Hey Jarvaids, cancel the agenda.')
        self.assertEqual('cancelled', self.doc()['data']['state'])

    def test_repeated_creation_and_removed_event_do_not_duplicate(self):
        entry = self.seeded(); self.create(); self.process()
        self.assertEqual(1, len(self.events()))
        self.doc_cmd('calendar.entry.edit', entry_id=entry['id'], task_id='', expected_entry_revision=entry['revision'],
            value={key: entry['data'][key] for key in ('text', 'date', 'time', 'done')}, removed=True)
        self.utter('The prototype review is tomorrow.'); self.process(changes=[event()])
        self.assertEqual(1, len(self.events()))
        self.assertTrue(self.events()[0]['data']['removed'])

    def test_calendar_output_cannot_be_synthetic(self):
        self.create(); self.process(); self.utter('The review is tomorrow.')
        original = self.model.interpret; self.model.results.append({'changes': [event()]})
        def synthetic(request):
            output = original(request); return PollOutput(output.data, output.provider, output.model, output.usage, synthetic=True)
        self.model.interpret = synthetic; self.service.run_one_document_job()
        self.assertEqual([], self.events())

    def test_view_commands_work_after_acceptance_without_reopening(self):
        self.seeded(); self.doc_cmd('document.close'); self.doc_cmd('document.accept')
        self.utter('Hey Jarvaids, show year view.')
        self.assertEqual(('accepted', 'year'), (self.doc()['data']['state'], self.doc()['data']['calendar_view']))

    def test_time_zone_create_replay_is_checked(self):
        body = {'session_id': 'a'*32, 'owner_token': 'b'*40, 'owner_name': 'Test', 'title': 'Clock', 'timezone': 'Europe/Amsterdam'}
        self.service.create_session(body); self.assertTrue(self.service.create_session(body)['replayed'])
        with self.assertRaises(Problem): self.service.create_session({**body, 'timezone': 'UTC'})

    def test_voice_view_survives_delayed_period_interpretation(self):
        self.create(); self.process(); source = self.utter('Show the calendar for next month.')
        def late(request):
            self.utter('Hey Jarvaids, show week view.')
            return {'focus': {'view': 'month', 'phrase': 'next month', 'source_id': source['id']}}
        self.model.results.append(late); self.service.run_one_document_job()
        self.assertEqual('week', self.doc()['data']['calendar_view'])

    def test_duplicate_shared_proposals_from_collectors_are_one_review(self):
        task, change = self.accepted_task_change()
        doc = self.doc()
        with self.service.db.transaction() as c:
            s, _ = self.service._auth(c, self.sid, self.token)
            entry = self.service._get(c, self.sid, task['id'], 'command_entry')
            values = {**change['data']['values'], 'deadline_anchor': self.now+100}
            self.service._propose_task_change(c, s, doc, entry, values, change['data']['source_refs'], {})
        self.assertEqual(1, len(self.records('command_task_change')))

    def test_out_of_session_capture_clock_is_rejected_before_transcription(self):
        # These document-test profiles have no acoustic embedding. This probe
        # exercises the real audio boundary without enrolling a voice.
        with self.service.db.transaction() as c:
            c.execute("DELETE FROM records WHERE session_id=? AND kind='speaker_profile'", (self.sid,))
        original = self.service.transcriber
        calls = []
        class Counted:
            def transcribe(_, request):
                calls.append(request)
                return original.transcribe(request)
        self.service.transcriber = Counted()
        for instant in (self.now+301, self.now-301):
            with self.assertRaises(Problem):
                self.cmd('source.audio', {'mime': 'audio/pcm16', 'base64': base64.b64encode(b'\x00\x01'*16000).decode(),
                    'ended_reason': 'silence', 'captured_at_utc_ms': int(instant*1000)})
        self.assertEqual([], calls)

    def test_shared_task_revision_is_checked_after_interpretation(self):
        task = self.todo(); self.create(); self.process(); self.utter('The interviews are due Friday.')
        self.process_for('todo')
        def late(request):
            with self.service.db.transaction() as c:
                current = self.service._get(c, self.sid, task['id'], 'command_entry')
                self.service._save(c, self.sid, current, {**current['data'], 'text': 'Human corrected task'})
            return {'changes': [event(op='update', task_id=task['id'], text=task['data']['text'], date_phrase='Friday', date_quote='Friday')]}
        self.model.results.append(late); self.service.run_one_document_job()
        self.assertEqual('Human corrected task', self.task()['data']['text'])

    def test_todo_ai_also_proposes_instead_of_replacing_calendar_accepted_task(self):
        task = self.todo(); self.create(); self.process(); self.doc_cmd('document.close'); self.doc_cmd('document.accept')
        self.utter('The interviews are due Friday.')
        self.process_for('todo', changes=[documents.patch(op='update', entry_id=task['id'], text=task['data']['text'],
            owner='Julie', deadline='Friday', deadline_quote='Friday', classification='agreed')])
        self.assertEqual('tomorrow', self.task()['data']['deadline'])
        self.assertEqual(1, len(self.records('command_task_change')))

    def test_calendar_and_uncertain_work_survive_service_restart(self):
        entry = self.seeded(); self.utter('The prototype review is Friday.')
        with self.service.db.transaction() as c:
            work = self.service._list(c, self.sid, 'command_work')[-1]
            self.service._save(c, self.sid, work, {**work['data'], 'status': 'running'})
        self.service = Service(self.path, clock=lambda: self.now, document_model=self.model)
        self.service.recover_document_jobs()
        self.assertEqual('Europe/Amsterdam', self.doc()['data']['timezone'])
        self.assertEqual((entry['id'], '2026-10-20'), (self.events()[0]['id'], self.events()[0]['data']['date']))
        self.assertEqual('uncertain', self.records('command_work')[-1]['data']['status'])
        self.assertFalse(self.service.run_one_document_job())

    def test_manual_todo_completion_does_not_reanchor_original_relative_deadline(self):
        task = self.todo(); self.create(); self.process()
        self.now += 86400
        with self.service.db.transaction() as c:
            c.execute('UPDATE sessions SET expires=?,lease=? WHERE id=?', (self.now+86400, self.now+300, self.sid))
        doc = next(d for d in self.records('command_document') if d['data']['document_type'] == 'todo')
        value = {key: task['data'][key] for key in ('text', 'owner', 'deadline', 'classification', 'done')}
        self.cmd('document.entry.edit', {'document_id': doc['id'], 'expected_revision': doc['revision'],
            'entry_id': task['id'], 'task': {**value, 'done': True}, 'removed': False})
        self.assertTrue(self.task()['data']['done'])
        self.assertEqual('2026-10-20', self.task()['data']['deadline_date'])


class DateTests(unittest.TestCase):
    anchor = datetime(2026, 10, 19, 23, 30, tzinfo=timezone.utc).timestamp()

    def test_relative_dates_use_session_zone_and_calendar_days(self):
        self.assertEqual('2026-10-21', resolve_date('tomorrow', self.anchor, 'Europe/Amsterdam')[0])
        self.assertEqual('2026-10-20', resolve_date('tomorrow', self.anchor, 'UTC')[0])
        dst = datetime(2026, 10, 24, 22, 30, tzinfo=timezone.utc).timestamp()
        self.assertEqual('2026-10-26', resolve_date('tomorrow', dst, 'Europe/Amsterdam')[0])

    def test_ambiguous_dates_and_weeks_stay_undated(self):
        for phrase in ('03/04', 'next Friday', 'next week', 'soon', '2026-02-30'):
            with self.subTest(phrase=phrase):
                resolved, question = resolve_date(phrase, self.anchor, 'Europe/Amsterdam')
                self.assertEqual('', resolved); self.assertTrue(question)

    def test_explicit_dates_weekdays_and_requested_periods(self):
        self.assertEqual('2026-10-23', resolve_date('Friday', self.anchor, 'Europe/Amsterdam')[0])
        self.assertEqual('2026-10-23', resolve_date('23 October 2026', self.anchor, 'Europe/Amsterdam')[0])
        self.assertEqual('2026-10-23', resolve_date('October 23, 2026', self.anchor, 'Europe/Amsterdam')[0])
        self.assertEqual(('2026-11-06',''), resolve_date('the 6th of November, 2026', self.anchor, 'Europe/Amsterdam'))
        self.assertEqual(('2026-11-02',''), resolve_date('the 2nd of November', self.anchor, 'Europe/Amsterdam'))
        self.assertEqual('2026-11-01', resolve_date('next month', self.anchor, 'Europe/Amsterdam', period=True)[0])
        self.assertEqual('2027-01-01', resolve_date('next year', self.anchor, 'Europe/Amsterdam', period=True)[0])

    def test_time_and_unknown_zone_validation(self):
        self.assertEqual(('14:30', ''), resolve_time('2:30 pm'))
        self.assertTrue(resolve_time('3 oclock')[1])
        self.assertTrue(resolve_time('25:00')[1])
        with self.assertRaises(Problem): zone_name('Imaginary/Room')


class CalendarAdapterTests(unittest.TestCase):
    def validate(self, **changes):
        patch = event(**{'evidence': [{'source_id': 'source', 'quote': 'The review is tomorrow.'}], **changes})
        return validate_calendar({'changes': [patch], 'focus': {'view': '', 'phrase': '', 'source_id': ''}},
            {'lines': [{'id': 'source', 'text': 'The review is tomorrow.', 'instant': DateTests.anchor}],
             'entries': [], 'tasks': [], 'timezone': 'Europe/Amsterdam'})

    def test_invented_calendar_quotation_is_rejected(self):
        with self.assertRaises(Problem):
            self.validate(evidence=[{'source_id': 'source', 'quote': 'The secret review is tomorrow.'}])

    def test_unknown_shared_task_is_rejected_before_application(self):
        with self.assertRaises(Problem): self.validate(op='update', task_id='unknown')

    def test_calendar_uses_typed_schema_and_prompt(self):
        calls = []
        def create(**kwargs):
            calls.append(kwargs)
            return SimpleNamespace(stop_reason='end_turn', model='scripted', usage=SimpleNamespace(input_tokens=1, output_tokens=2),
                content=[SimpleNamespace(type='text', text=json.dumps({'changes': [], 'prompt': '', 'needs_clarification': False,
                    'resolutions': [], 'focus': {'view': '', 'phrase': '', 'source_id': ''}}))])
        ClaudeDocumentModel(client=SimpleNamespace(messages=SimpleNamespace(create=create))).interpret({'document_type': 'calendar'})
        self.assertEqual(CALENDAR_SCHEMA, calls[0]['output_config']['format']['schema'])
        self.assertEqual(CALENDAR_SYSTEM, calls[0]['system'])

    def test_calendar_aliases_and_lifecycle_keep_address_requirement(self):
        for noun in ('agenda', 'calendar', 'visual calendar'):
            self.assertEqual('planning', recognise_command('Hey Jarvaids, let us make a '+noun)['intent'])
        for action in ('close', 'accept', 'reopen', 'cancel'):
            heard = recognise_command('Hey Jarvaids, '+action+' the agenda.')
            self.assertEqual(action, heard['document_action'])
            self.assertIsNone(recognise_command(action+' the agenda.'))
