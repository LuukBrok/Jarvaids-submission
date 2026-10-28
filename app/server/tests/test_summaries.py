"""Fictional meeting checks for persistence, source gates and protected edits."""
import secrets
import tempfile
import unittest
from pathlib import Path
from genai_server.service import Service
from genai_server.validation import Problem
from genai_server.summary_model import validate_result


class ScriptedSummary:
    name = 'Scripted test adapter'
    model = 'fixture'
    synthetic = True

    def __init__(self): self.calls = 0; self.fail = False; self.callback = None

    def process(self, request):
        self.calls += 1
        if self.callback: self.callback()
        if self.fail: raise RuntimeError('scripted failure')
        line = request['lines'][0]
        evidence = [{'source_id': line['id'], 'quote': line['text']}]
        return {'theme': 'Design', 'title': 'Prototype approach', 'description': 'Prototype choices',
            'summary': line['text'], 'evidence': evidence,
            'decisions': [{'text': line['text'], 'evidence': evidence}], 'action_items': [], 'open_questions': []}


class SummaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='jv-summary-')
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'session.sqlite3'
        self.model = ScriptedSummary()
        self.service = Service(self.path, automatic_workspace=True, summary_model=self.model)
        self.sid, self.token = secrets.token_hex(16), secrets.token_urlsafe(32)
        self.service.create_session({'session_id': self.sid, 'owner_token': self.token,
            'owner_name': 'Test facilitator', 'title': 'Fictional integration test'})
        self.cmd('consent.acknowledge', {'policy_version': 1})
        self.cmd('session.activate', {'policy_version': 1, 'expected_session_revision': self.snapshot()['session']['revision']})

    def snapshot(self): return self.service.snapshot(self.sid, self.token)
    def records(self, kind): return [r for r in self.snapshot()['records'] if r['kind'] == kind]
    def cmd(self, operation, payload=None):
        sequence = self.snapshot()['next_control_sequence'] if operation in self.service.CONTROL_COMMANDS else None
        return self.service.command(self.sid, self.token, secrets.token_hex(16), operation, payload or {}, sequence)['result']
    def say(self, words='We decided to build the prototype offline.'):
        return self.cmd('source.text', {'text': words})
    def flush(self): self.cmd('summary.flush'); return self.service.run_one_summary_job()

    def test_persisted_overview_reuses_note_and_keeps_placement(self):
        self.say(); self.assertTrue(self.flush())
        topic = self.records('summary_topic')[0]; nid = topic['data']['note_id']
        self.cmd('item.place', {'placements': [{'id': nid, 'x': 120, 'y': 90,
            'expected_position_revision': self.service.record(self.sid, self.token, nid)['position']['revision']}], 'origin': 'human'})
        self.say('We also decided to interview students.'); self.flush()
        self.assertEqual(1, len(self.records('summary_topic')))
        topic = self.records('summary_topic')[0]
        self.assertEqual(nid, topic['data']['note_id']); self.assertEqual(2, len(topic['data']['entries']))
        note = self.service.record(self.sid, self.token, nid)
        self.assertEqual((120, 90), (note['position']['x'], note['position']['y']))
        self.assertTrue(note['data']['automatic']); self.assertNotIn('accepted_by', note['data'])
        self.service = Service(self.path, automatic_workspace=True, summary_model=self.model)
        self.assertEqual(2, len(self.records('summary_topic')[0]['data']['entries']))
        self.assertFalse(self.service.run_one_summary_job()); self.assertEqual(2, self.model.calls)

    def test_failure_blocks_later_batches_and_retry_preserves_sources(self):
        self.say(); self.model.fail = True; self.flush()
        work = self.records('summary_work')[0]
        self.assertEqual('error', work['data']['status']); self.assertFalse(self.records('summary_topic'))
        self.say('We will test it tomorrow.'); self.cmd('summary.flush')
        self.service.run_one_summary_job(); self.assertEqual(1, self.model.calls)
        self.model.fail = False
        self.cmd('summary.retry', {'work_id': work['id'], 'expected_revision': work['revision']})
        self.service.run_one_summary_job(); self.service.run_one_summary_job()
        self.assertEqual(2, len(self.records('summary_topic')[0]['data']['entries']))

    def test_pause_during_model_call_cannot_publish(self):
        self.say(); self.model.callback = lambda: self.cmd('session.pause')
        self.flush()
        self.assertFalse(self.records('summary_topic'))
        self.assertEqual('error', self.records('summary_work')[0]['data']['status'])

    def test_deletion_during_model_call_leaves_no_summary(self):
        self.say(); self.model.callback = lambda: self.service.delete_session(self.sid, self.token)
        self.flush()
        with self.service.db.transaction() as c:
            self.assertEqual(0, c.execute('SELECT count(*) FROM records WHERE session_id=?', (self.sid,)).fetchone()[0])

    def test_manual_correction_is_not_overwritten(self):
        self.say(); self.flush(); topic = self.records('summary_topic')[0]
        note = self.service.record(self.sid, self.token, topic['data']['note_id'])
        self.cmd('item.edit', {'item_id': note['id'], 'expected_revision': note['revision'],
            'text': 'Our corrected heading', 'refs': note['data']['refs']})
        self.say('The new discussion continues on the prototype.'); self.flush()
        self.assertEqual('Our corrected heading', self.service.record(self.sid, self.token, note['id'])['data']['text'])
        self.assertEqual(2, len(self.records('summary_topic')[0]['data']['entries']))

    def test_summary_address_flushes_short_tail_without_becoming_summary_content(self):
        self.say(); self.say('Hey Jarvaids, make a summary.')
        self.assertTrue(self.service.run_one_summary_job())
        self.assertEqual(1, len(self.records('summary_topic')[0]['data']['entries'][0]['source_refs']))

    def test_word_threshold_waits_until_sentence_boundary(self):
        self.say('a word ' * 31); self.assertFalse(self.service.run_one_summary_job())
        self.assertEqual(0, self.model.calls)
        self.say('A complete sentence.'); self.assertTrue(self.service.run_one_summary_job())

    def test_fallback_cap_handles_unpunctuated_speech(self):
        self.say('words ' * 101); self.assertTrue(self.service.run_one_summary_job())

    def test_agenda_survives_restart_and_disable_prevents_calls(self):
        self.cmd('summary.configure', {'agenda': ['Pricing', 'Testing'], 'enabled': False})
        self.say('Pricing should remain affordable.'); self.assertFalse(self.service.run_one_summary_job())
        self.assertEqual(['Pricing', 'Testing'], self.records('summary_state')[0]['data']['agenda'])
        self.assertEqual(0, self.model.calls)

    def test_invented_quote_or_owner_is_rejected(self):
        request = {'lines': [{'id': 'a', 'text': 'We will test this tomorrow.'}]}
        result = self.model.process({'lines': [{'id': 'a', 'text': 'We will test this tomorrow.'}]})
        result['evidence'][0]['quote'] = 'Something never said'
        with self.assertRaises(Problem): validate_result(result, request)
        result = self.model.process({'lines': [{'id': 'a', 'text': 'We will test this tomorrow.'}]})
        result['action_items'] = [{'text': 'Test this', 'owner': 'Invented person', 'evidence': result['evidence']}]
        with self.assertRaises(Problem): validate_result(result, request)

    def test_first_person_owner_uses_verified_speaker_without_rewriting_quote(self):
        line={'id':'a','text':'I will interview six students.','speaker':'Roselique','speaker_verified':True}
        result=self.model.process({'lines':[line]})
        result['action_items']=[{'text':'Interview six students','owner':'Roselique','evidence':result['evidence']}]
        self.assertEqual('Roselique',validate_result(result,{'lines':[line]})['action_items'][0]['owner'])
        for changed in ({'speaker_verified':False},{'speaker':'Unknown speaker'},{'speaker':'Pieter'}):
            with self.subTest(changed=changed),self.assertRaises(Problem):
                validate_result(result,{'lines':[{**line,**changed}]})
        for words in ('I need an extra day to contact the room manager.','That changes the deadline of my existing task.'):
            own={**line,'text':words};action=self.model.process({'lines':[own]})
            action['action_items']=[{'text':'Contact room manager','owner':'Roselique','evidence':action['evidence']}]
            self.assertEqual('Roselique',validate_result(action,{'lines':[own]})['action_items'][0]['owner'])
        collective={**line,'text':'We should test the prototype.'};action=self.model.process({'lines':[collective]})
        action['action_items']=[{'text':'Test prototype','owner':'Roselique','evidence':action['evidence']}]
        with self.assertRaises(Problem):validate_result(action,{'lines':[collective]})

    def test_restart_running_job_requires_explicit_retry(self):
        self.say(); self.model.fail = True; self.flush()
        with self.service.db.transaction() as c:
            work = self._work(c)
            self.service._save(c, self.sid, work, {**work['data'], 'status': 'running'})
        self.service.recover_summary_jobs()
        self.assertEqual('error', self.records('summary_work')[0]['data']['status'])
        self.assertFalse(self.service.run_one_summary_job())

    def test_switch_to_cloud_pauses_and_renews_agreement(self):
        self.model.local = False
        self.service = Service(self.path, automatic_workspace=True, summary_model=self.model)
        session = self.snapshot()['session']
        self.assertEqual('paused', session['state'])
        self.assertEqual(2, session['policy_version'])

    def test_summary_export_contains_full_detail(self):
        self.say(); self.flush()
        data = self.cmd('export.create', {'include_unresolved': True})['data']
        self.assertIn('Decision:', data['markdown'])
        self.assertIn('We decided to build the prototype offline', data['markdown'])
        note=self.records('item')[0]
        self.cmd('item.edit',{'item_id':note['id'],'expected_revision':note['revision'],
            'text':'Manually corrected summary heading','refs':note['data']['refs']})
        exported=self.cmd('export.create',{'include_unresolved':True})['data']
        self.assertIn('Manually corrected summary heading',exported['markdown'])
        self.assertEqual('Manually corrected summary heading',next(r for r in exported['records'] if r['id']==note['id'])['data']['text'])

    def _work(self, c): return self.service._list(c, self.sid, 'summary_work')[0]
