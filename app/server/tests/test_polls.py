"""Synthetic contract tests, not evidence of room speech or LLM accuracy."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import secrets
import threading
import unittest
from types import SimpleNamespace

from genai_server.poll_model import ClaudePollModel, PollModelFailure, PollOutput, SCHEMA
from genai_server.service import Service
from genai_server.validation import Problem
from genai_server.voice_commands import recognise_command
from tests import test_service as service_tests


def answer(action='ignore', **changes):
    return {'action': action, 'question': '', 'options': [], 'option_id': '',
            'prompt': '', 'quote': '', 'source_ids': [], **changes}


class ScriptModel:
    name = 'test-double'

    def __init__(self):
        self.results, self.requests = [], []

    def interpret(self, request):
        self.requests.append(deepcopy(request))
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        result = deepcopy(result)
        if result.get('action') != 'ignore':
            result.setdefault('source_ids', [request['current']['id']])
            result.setdefault('quote', request['current']['text'])
        result = answer(**result)
        return PollOutput(result, 'test-double', 'scripted-contract-only', {'input_tokens': 10, 'output_tokens': 10})


class PollTests(unittest.TestCase):
    cmd = service_tests.ServiceTests.cmd
    active = service_tests.ServiceTests.active

    def setUp(self):
        service_tests.ServiceTests.setUp(self)
        self.model = ScriptModel()
        self.service.poll_model = self.model
        self.active()
        self.tick = 0
        with self.service.db.transaction() as c:
            self.profiles = [self.service._new(c, self.sid, 'speaker_profile',
                {'name': name, 'embedding': [1, 0], 'provenance': {'synthetic': False}}) for name in ('Julie', 'Pieter', 'Luuk')]

    def records(self, kind):
        return [r for r in self.service.snapshot(self.sid, self.token)['records'] if r['kind'] == kind]

    def poll(self):
        return self.records('poll')[-1]

    def poll_cmd(self, op, **extra):
        p = self.poll()
        return self.cmd(op, {'poll_id': p['id'], 'expected_revision': p['revision'], **extra})

    def utter(self, value, speaker=0, synthetic=False, stamp=None):
        self.tick += 1000
        with self.service.db.transaction() as c:
            s, a = self.service._auth(c, self.sid, self.token)
            source = self.service._new(c, self.sid, 'transcript_segment', {
                'text': value, 'status': 'final', 'voice_command': recognise_command(value, synthetic=synthetic),
                'created_at': self.now, 'capture_id': 'room_microphone', 'captured_at_ms': self.tick if stamp is None else stamp,
                'speaker_actor_id': a['id'], 'author_id': a['id'],
                'speaker_profile_id': self.profiles[speaker]['id'] if speaker is not None else None,
                'attribution': 'voice_identified' if speaker is not None else 'unidentified',
                'provenance': {'synthetic': synthetic, 'speaker': {'synthetic': False}},
            })
            self.service._poll_heard(c, s, a, source)
            self.service._event(c, self.sid, a['id'], 'test.audio', {})
        return source

    def process(self, **result):
        self.model.results.append(result or {'action': 'ignore'})
        self.assertTrue(self.service.run_one_poll_job())

    def draft(self):
        self.utter('Salad, sandwiches or fries for lunch. Hey Jarvaids, make a voting list.')
        self.process(action='draft', question='What should we have for lunch?', options=['Salad', 'Sandwiches', 'Fries'])
        return self.poll()

    def opened(self):
        self.draft()
        self.utter('Yes, start voting.')
        self.process(action='confirm')
        self.assertEqual('open', self.poll()['data']['state'])

    def test_command_required_and_fixtures_never_start_polls(self):
        self.utter('I vote for salad.')
        self.utter('Hey Jarvaids, make a voting list.', synthetic=True)
        self.assertEqual([], self.records('poll'))

    def test_draft_then_confirmation_never_creates_a_ballot(self):
        self.opened()
        self.assertEqual([], self.records('poll_ballot'))
        self.assertEqual(1, len(self.records('poll')))
        self.utter('Hey Jarvaids, make a voting list.')
        self.assertEqual(1, len(self.records('poll')))

    def test_clear_choices_change_and_withdraw_without_double_counting(self):
        self.opened()
        for value, speaker, choice in [('Sandwiches for me.', 0, 'option_02'), ('Fries.', 1, 'option_03'),
                                       ('Actually salad instead.', 0, 'option_01')]:
            self.utter(value, speaker)
            self.process(action='select', option_id=choice)
        ballots = self.records('poll_ballot')
        self.assertEqual(2, len(ballots))
        self.assertEqual({'option_01', 'option_03'}, {b['data']['option_id'] for b in ballots})
        self.utter('Remove my vote.', 0)
        self.process(action='remove')
        self.assertEqual(1, sum(b['data']['option_id'] is not None for b in self.records('poll_ballot')))

    def test_unknown_speaker_never_enters_tally_and_can_be_corrected(self):
        self.opened()
        self.utter('Fries for me.', None)
        self.process(action='select', option_id='option_03')
        self.assertEqual([], self.records('poll_ballot'))
        work = self.records('poll_work')[-1]
        self.assertEqual('clarify', work['data']['status'])
        self.poll_cmd('poll.resolve', work_id=work['id'], dismiss=False,
                      speaker_profile_id=self.profiles[2]['id'], option_id='option_03')
        self.assertEqual('human', self.records('poll_ballot')[0]['data']['origin'])

    def test_ambiguous_reply_needs_review_and_same_speaker_followup_resolves(self):
        self.opened()
        self.utter('Anything except salad.', 0)
        self.process(action='clarify', prompt='Sandwiches or fries?')
        self.assertEqual([], self.records('poll_ballot'))
        self.utter('Sandwiches.', 0)
        self.process(action='select', option_id='option_02')
        self.assertEqual('resolved', self.records('poll_work')[-2]['data']['status'])

    def test_followup_can_reference_own_older_clarification_evidence(self):
        self.opened()
        unclear = self.utter('Anything except salad.', 0)
        self.process(action='clarify', prompt='Sandwiches or fries?')
        for _ in range(5):
            self.utter('Unrelated discussion.', 1)
            self.process(action='ignore')
        reply = self.utter('Sandwiches.', 0)
        self.process(action='select', option_id='option_02', source_ids=[unclear['id'], reply['id']])
        self.assertEqual('option_02', self.records('poll_ballot')[0]['data']['option_id'])

    def test_unknown_option_and_invented_quote_are_not_applied(self):
        self.opened()
        self.utter('Sandwiches.', 0)
        self.process(action='select', option_id='option_99')
        self.assertEqual([], self.records('poll_ballot'))
        self.assertEqual('error', self.records('poll_work')[-1]['data']['status'])
        self.utter('Maybe.', 0)
        self.process(action='select', option_id='option_02', quote='I definitely vote sandwiches')
        self.assertEqual([], self.records('poll_ballot'))

    def test_invented_draft_choices_are_rejected_before_display(self):
        self.utter('Hey Jarvaids, make a voting list.')
        self.process(action='draft', question='Lunch?', options=['Invented salad', 'Invented fries'])
        self.assertEqual([], self.poll()['data']['options'])
        self.assertEqual('error', self.records('poll_work')[-1]['data']['status'])

    def test_synthetic_model_output_never_becomes_a_vote(self):
        self.opened()
        self.utter('Fries.', 0)
        self.model.interpret = lambda req: PollOutput(answer('select', option_id='option_03',
            quote='Fries.', source_ids=[req['current']['id']]), 'fixture', 'fake', {}, True)
        self.assertTrue(self.service.run_one_poll_job())
        self.assertEqual([], self.records('poll_ballot'))

    def test_no_retroactive_votes_and_late_preopening_capture_is_ignored(self):
        self.utter('Salad.', 0)
        self.draft()
        self.poll_cmd('poll.confirm')
        before = len(self.records('poll_work'))
        self.utter('Salad.', 0, stamp=1000)
        self.assertEqual(before, len(self.records('poll_work')))
        self.assertEqual([], self.records('poll_ballot'))

    def test_manual_edit_invalidates_inflight_model_response(self):
        self.utter('Hey Jarvaids, make a voting list.')
        entered, release = threading.Event(), threading.Event()
        def blocked(req):
            entered.set(); release.wait(5)
            return PollOutput(answer('draft', question='Old question?', options=['Old A', 'Old B'],
                source_ids=[req['current']['id']]), 'test', 'test', {})
        self.model.interpret = blocked
        with ThreadPoolExecutor() as pool:
            task = pool.submit(self.service.run_one_poll_job)
            self.assertTrue(entered.wait(3))
            self.poll_cmd('poll.edit', question='Human question?', options=['A', 'B'])
            release.set(); task.result(5)
        self.assertEqual('Human question?', self.poll()['data']['question'])
        self.assertEqual('stale', self.records('poll_work')[0]['data']['status'])

    def test_pause_invalidates_work_and_never_calls_provider(self):
        self.draft()
        self.poll_cmd('poll.confirm')
        self.utter('Fries.', 0)
        self.cmd('session.pause')
        calls = len(self.model.requests)
        self.assertTrue(self.service.run_one_poll_job())
        self.assertEqual(calls, len(self.model.requests))
        self.assertEqual([], self.records('poll_ballot'))

    def test_failed_call_is_visible_and_not_automatically_retried(self):
        self.utter('Hey Jarvaids, make a voting list.')
        self.model.results.append(PollModelFailure('test failure'))
        self.assertTrue(self.service.run_one_poll_job())
        self.assertFalse(self.service.run_one_poll_job())
        work = self.records('poll_work')[0]
        self.assertEqual('error', work['data']['status'])
        with self.assertRaises(Problem):
            self.poll_cmd('poll.retry', work_id=work['id'], acknowledge_unknown_cost=False)
        self.poll_cmd('poll.retry', work_id=work['id'], acknowledge_unknown_cost=True)
        self.assertEqual('queued', self.records('poll_work')[0]['data']['status'])

    def test_closing_drains_prior_replies_and_requires_review(self):
        self.opened()
        self.utter('Fries.', 0)
        self.poll_cmd('poll.close')
        with self.assertRaises(Problem):
            self.poll_cmd('poll.finalise')
        self.process(action='select', option_id='option_03')
        self.poll_cmd('poll.finalise')
        self.assertEqual('closed', self.poll()['data']['state'])
        self.assertEqual(1, self.poll()['data']['counts']['option_03'])
        self.assertEqual('accepted', self.records('poll_ballot')[0]['data']['status'])
        with self.assertRaises(Problem):
            self.poll_cmd('poll.vote', speaker_profile_id=self.profiles[0]['id'], option_id='option_02')

    def test_unresolved_reply_blocks_finalisation_until_explicitly_excluded(self):
        self.opened()
        self.utter('Not salad.', 0)
        self.process(action='clarify', prompt='Which remaining choice?')
        self.poll_cmd('poll.close')
        with self.assertRaises(Problem): self.poll_cmd('poll.finalise')
        work = self.records('poll_work')[-1]
        self.poll_cmd('poll.resolve', work_id=work['id'], dismiss=True)
        self.poll_cmd('poll.finalise')
        self.assertEqual(0, sum(self.poll()['data']['counts'].values()))

    def test_manual_correction_wins_over_earlier_queued_vote(self):
        self.opened()
        self.utter('Fries.', 0)
        self.poll_cmd('poll.vote', speaker_profile_id=self.profiles[0]['id'], option_id='option_01')
        self.process(action='select', option_id='option_03')
        self.assertEqual('option_01', self.records('poll_ballot')[0]['data']['option_id'])
        self.assertEqual('stale', self.records('poll_work')[-1]['data']['status'])

    def test_capture_order_prevents_late_older_reply_overwriting_newer_choice(self):
        self.opened()
        self.utter('Fries.', 0, stamp=10000)
        self.process(action='select', option_id='option_03')
        self.utter('Sandwiches.', 0, stamp=9000)
        self.process(action='select', option_id='option_02')
        self.assertEqual('option_03', self.records('poll_ballot')[0]['data']['option_id'])

    def test_restart_recovers_running_call_as_uncertain(self):
        self.utter('Hey Jarvaids, make a voting list.')
        with self.service.db.transaction() as c:
            work = self.service._list(c, self.sid, 'poll_work')[0]
            self.service._save(c, self.sid, work, {**work['data'], 'status': 'running'})
        restarted = Service(self.path, clock=lambda: self.now, poll_model=self.model)
        restarted.recover_poll_jobs()
        self.assertFalse(restarted.run_one_poll_job())
        self.assertEqual('uncertain', self.records('poll_work')[0]['data']['status'])

    def test_enabling_cloud_for_old_session_requires_fresh_agreement(self):
        old = self.service.snapshot(self.sid, self.token)
        restarted = Service(self.path, clock=lambda: self.now, poll_model=self.model)
        current = restarted.snapshot(self.sid, self.token)
        self.assertEqual('paused', current['session']['state'])
        self.assertGreater(current['session']['policy_version'], old['session']['policy_version'])
        self.assertNotEqual(current['session']['policy_version'], current['members'][0]['consent_version'])

    def test_cloud_setting_change_is_not_reapplied_on_every_restart(self):
        first = Service(self.path, clock=lambda: self.now, poll_model=self.model)
        version = first.snapshot(self.sid, self.token)['session']['policy_version']
        second = Service(self.path, clock=lambda: self.now, poll_model=self.model)
        self.assertEqual(version, second.snapshot(self.sid, self.token)['session']['policy_version'])
        third = Service(self.path, clock=lambda: self.now)
        self.assertGreater(third.snapshot(self.sid, self.token)['session']['policy_version'], version)

    def test_poll_can_move_without_accepting_meaning(self):
        self.draft()
        p = self.poll()
        self.cmd('item.place', {'placements': [{'id': p['id'], 'x': 400, 'y': 50, 'expected_position_revision': 0}]})
        self.assertEqual('draft', self.poll()['data']['state'])
        self.assertEqual(400, self.poll()['position']['x'])

    def test_typed_notes_do_not_trigger_a_poll(self):
        self.cmd('source.text', {'text': 'Hey Jarvaids, make a voting list.'})
        self.assertEqual([], self.records('poll'))

    def test_voice_close_and_accept_require_addressed_control(self):
        self.opened()
        self.utter('Maybe close voting later.')
        self.process(action='ignore')
        self.assertEqual('open', self.poll()['data']['state'])
        self.utter('Hey Jarvaids, close voting.')
        self.assertEqual('closing', self.poll()['data']['state'])
        self.utter('Hey Jarvaids, accept voting results.')
        self.assertEqual('closed', self.poll()['data']['state'])

    def test_binary_options_are_allowed_but_negated_requests_are_not(self):
        heard = recognise_command('Hey Jarvaids, make a poll with yes or no.')
        self.assertEqual('voting', heard['intent'])
        self.assertIsNone(recognise_command('Hey Jarvaids, do not make a poll with yes or no.')['intent'])


class PollAdapterTests(unittest.TestCase):
    def test_structured_request_has_no_retries_or_freeform_result(self):
        calls = []
        def create(**kw):
            calls.append(kw)
            return SimpleNamespace(stop_reason='end_turn', model='test-returned-model',
                content=[SimpleNamespace(type='text', text=__import__('json').dumps(answer()))],
                usage=SimpleNamespace(input_tokens=2, output_tokens=3))
        model = ClaudePollModel(client=SimpleNamespace(messages=SimpleNamespace(create=create)), model='test-requested-model')
        output = model.interpret({'current': {'text': 'meeting data'}})
        self.assertEqual('json_schema', calls[0]['output_config']['format']['type'])
        self.assertEqual(SCHEMA, calls[0]['output_config']['format']['schema'])
        self.assertEqual('test-returned-model', output.model)
        self.assertEqual(1, len(calls))

    def test_provider_exception_text_is_not_exposed(self):
        def create(**kw): raise RuntimeError('SECRET AND PRIVATE TRANSCRIPT')
        model = ClaudePollModel(client=SimpleNamespace(messages=SimpleNamespace(create=create)))
        try:
            model.interpret({})
        except PollModelFailure as error:
            self.assertNotIn('SECRET', str(error))
        else:
            self.fail('Provider failure should be visible.')
