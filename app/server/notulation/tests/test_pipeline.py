"""Behaviour of the rolling-minutes pipeline, end to end, with no network.

Three things this is specifically here to prove, because they are the
feature the user asked for and F2.1 names as the risk: a topic is not
summarised as concluded while the model says it is still running, a topic
revisited later updates its own section instead of opening a second one, and
an open question that gets answered later is shown retired, never silently
dropped.
"""
import json
import tempfile
import unittest
from pathlib import Path

from notulation.pipeline import (FixtureNotulationModel, ModelResult, blocks_from_boundaries, check_block,
                                 detect_boundaries, main, run, to_markdown)


def segment(id_, start, end, text, speaker=None):
    item = {'id': id_, 'start': start, 'end': end, 'text': text}
    if speaker:
        item['speaker'] = speaker
    return item


def encoded_transcript(segments):
    return json.dumps({'segments': [{'start': s['start'], 'end': s['end'], 'text': s['text']} for s in segments]}).encode()


# A ten-second gap is one silence boundary (pipelines.md 6.3); each block's
# text is kept short and topic-distinct so a human reading the test can see
# why a boundary was expected.
PAYWALL = [segment('t1', 0.0, 2.0, 'Should the paywall sit before or after onboarding.'),
           segment('t2', 2.0, 4.0, 'Before onboarding, people will not pay for something unproven.'),
           segment('t3', 4.0, 6.0, 'Agreed, paywall goes after onboarding for now.')]
ONBOARDING = [segment('t4', 16.0, 18.0, 'Onboarding should be three screens, not five.'),
              segment('t5', 18.0, 20.0, 'Three screens, agreed, ship that for the pilot.')]
PAYWALL_REVISIT = [segment('t6', 30.0, 32.0, 'Actually revisiting the paywall, marketing wants it on open.'),
                   segment('t7', 32.0, 34.0, 'Fine, paywall moves back to before onboarding, final answer.')]

SEGMENTS = PAYWALL + ONBOARDING + PAYWALL_REVISIT


def answer(topic, concluded, summary, continues=None, decisions=(), actions=(), add=(), retire=()):
    return {'topic': topic, 'concluded': concluded, 'continues_topic': continues, 'summary': list(summary),
            'decisions': list(decisions), 'actions': list(actions), 'open_questions_add': list(add),
            'open_questions_retire': list(retire)}


class Scripted:
    """A model that answers each block from a queue, and records what it was sent."""
    name = 'scripted'

    def __init__(self, answers):
        self.answers, self.sent = list(answers), []

    def summarize_block(self, block, context, repair):
        self.sent.append((block, context, repair))
        reply = self.answers.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return ModelResult(reply, 'scripted', 'scripted-v1', True, {'input_tokens': 10, 'output_tokens': 5})


class BoundaryTests(unittest.TestCase):
    def test_long_silence_is_a_boundary(self):
        boundaries = detect_boundaries(SEGMENTS)
        indices = [b['index'] for b in boundaries]
        # The gap before t4 (16.0 - 6.0 = 10s) and before t6 (30.0 - 20.0 = 10s)
        # are both over the 8s silence threshold.
        self.assertIn(3, indices)
        self.assertIn(5, indices)
        self.assertEqual('silence', next(b['reason'] for b in boundaries if b['index'] == 3))

    def test_a_tiny_block_from_a_lexical_shift_boundary_is_folded_into_the_block_before_it(self):
        # No silence here (0.5s gap): a one-word interjection with no
        # vocabulary in common with what came before trips the lexical-shift
        # check on its own, and is too small to be its own topic.
        segments = PAYWALL + [segment('t4', 6.5, 7.0, 'Hm.')]
        boundaries = detect_boundaries(segments)
        self.assertEqual('lexical_shift', boundaries[-1]['reason'])
        blocks = blocks_from_boundaries(segments, boundaries)
        self.assertEqual(1, len(blocks))
        self.assertEqual(['t1', 't2', 't3', 't4'], [s['id'] for s in blocks[0][0]])

    def test_a_tiny_block_opened_by_silence_alone_stands_on_its_own(self):
        # An 8s+ pause is trusted even for a short topic: a quick decision
        # followed by silence must not be erased by the tiny-block fold, even
        # when a lexical shift at the same cut is reported as the dominant
        # reason (both can be true of the same boundary at once).
        segments = PAYWALL + [segment('t4', 16.0, 16.5, 'Noted.')]
        boundaries = detect_boundaries(segments)
        self.assertTrue(boundaries[-1]['silence'])
        blocks = blocks_from_boundaries(segments, boundaries)
        self.assertEqual(2, len(blocks))
        self.assertEqual(['t4'], [s['id'] for s in blocks[1][0]])

    def test_each_block_carries_the_boundary_that_opened_it(self):
        boundaries = detect_boundaries(SEGMENTS)
        blocks = blocks_from_boundaries(SEGMENTS, boundaries)
        self.assertEqual(3, len(blocks))
        self.assertIsNone(blocks[0][1])
        self.assertEqual(3, blocks[1][1]['index'])
        self.assertEqual(5, blocks[2][1]['index'])


class GateTests(unittest.TestCase):
    def test_a_well_formed_answer_passes(self):
        value, errors = check_block(answer('paywall', True, ['Paywall goes after onboarding.']), PAYWALL, [], set())
        self.assertEqual([], errors)
        self.assertEqual('paywall', value['topic'])

    def test_concluded_must_be_a_boolean(self):
        data = answer('paywall', 'yes', ['x'])
        _, errors = check_block(data, PAYWALL, [], set())
        self.assertTrue(any('Concluded' in e for e in errors))

    def test_continues_topic_must_be_a_known_topic(self):
        data = answer('paywall', True, ['x'], continues='onboarding')
        _, errors = check_block(data, PAYWALL, ['something else'], set())
        self.assertTrue(any('continues_topic' in e for e in errors))

    def test_continues_topic_naming_a_known_topic_is_accepted(self):
        data = answer('paywall', True, ['x'], continues='onboarding')
        value, errors = check_block(data, PAYWALL, ['onboarding'], set())
        self.assertEqual([], errors)
        self.assertEqual('onboarding', value['continues_topic'])

    def test_summary_needs_at_least_one_bullet(self):
        _, errors = check_block(answer('paywall', True, []), PAYWALL, [], set())
        self.assertTrue(any('Summary' in e for e in errors))

    def test_decision_quote_must_appear_in_cited_segments(self):
        decisions = [{'segment_ids': ['t3'], 'text': 'Paywall after onboarding', 'quote': 'ships on Tuesday'}]
        _, errors = check_block(answer('paywall', True, ['x'], decisions=decisions), PAYWALL, [], set())
        self.assertTrue(any('quote is not in the segments' in e for e in errors))

    def test_decision_citing_a_segment_that_does_not_exist_is_refused(self):
        decisions = [{'segment_ids': ['t99'], 'text': 'Paywall after onboarding', 'quote': 'agreed'}]
        _, errors = check_block(answer('paywall', True, ['x'], decisions=decisions), PAYWALL, [], set())
        self.assertTrue(any('do not exist' in e for e in errors))

    def test_a_correctly_quoted_decision_is_kept(self):
        decisions = [{'segment_ids': ['t3'], 'text': 'Paywall after onboarding',
                      'quote': 'paywall goes after onboarding'}]
        value, errors = check_block(answer('paywall', True, ['x'], decisions=decisions), PAYWALL, [], set())
        self.assertEqual([], errors)
        self.assertEqual(1, len(value['decisions']))

    def test_open_question_retire_must_name_a_known_id(self):
        _, errors = check_block(answer('paywall', True, ['x'], retire=['q7']), PAYWALL, [], set())
        self.assertTrue(any('do not exist' in e for e in errors))

    def test_open_question_retire_naming_a_known_id_is_accepted(self):
        value, errors = check_block(answer('paywall', True, ['x'], retire=['q1']), PAYWALL, [], {'q1'})
        self.assertEqual([], errors)
        self.assertEqual(['q1'], value['open_questions_retire'])

    def test_action_owner_is_optional_and_never_invented_by_the_gate(self):
        actions = [{'segment_ids': ['t3'], 'task': 'Update the spec', 'quote': 'agreed'}]
        value, errors = check_block(answer('paywall', True, ['x'], actions=actions), PAYWALL, [], set())
        self.assertEqual([], errors)
        self.assertIsNone(value['actions'][0]['owner'])


class RunTests(unittest.TestCase):
    def test_two_unrelated_topics_become_two_sections(self):
        model = Scripted([
            answer('paywall', True, ['Paywall goes after onboarding.']),
            answer('onboarding', True, ['Three screens for the pilot.']),
            # Third block never reached in this test; see the circling-back test.
        ])
        document = run(('t.json', encoded_transcript(PAYWALL + ONBOARDING)), model)
        self.assertEqual(['paywall', 'onboarding'], [s['topic'] for s in document['sections']])
        self.assertEqual(2, document['usage']['calls'])

    def test_circling_back_merges_into_the_existing_section_and_rewrites_its_summary(self):
        model = Scripted([
            answer('paywall', True, ['Paywall goes after onboarding.']),
            answer('onboarding', True, ['Three screens for the pilot.']),
            answer('paywall', True, ['Paywall moves back to before onboarding, final answer.'], continues='paywall'),
        ])
        document = run(('t.json', encoded_transcript(SEGMENTS)), model)
        self.assertEqual(2, len(document['sections']))
        paywall = next(s for s in document['sections'] if s['topic'] == 'paywall')
        # The latest decision replaces the earlier running note; both are not
        # shown side by side, which is the behaviour the user asked for.
        self.assertEqual(['Paywall moves back to before onboarding, final answer.'], paywall['summary'])
        self.assertEqual(2, len(paywall['blocks']))

    def test_circling_back_by_an_exact_repeated_topic_label_merges_even_without_continues_topic(self):
        model = Scripted([
            answer('paywall', True, ['First pass.']),
            answer('onboarding', True, ['Three screens.']),
            answer('paywall', True, ['Final answer.']),  # continues_topic left null
        ])
        document = run(('t.json', encoded_transcript(SEGMENTS)), model)
        self.assertEqual(2, len(document['sections']))

    def test_an_open_question_opened_then_retired_is_shown_retired_not_removed(self):
        opened = [{'segment_ids': ['t1'], 'text': 'Who signs off on the paywall position?', 'quote': 'paywall sit'}]
        model = Scripted([
            answer('paywall', True, ['Paywall goes after onboarding.'], add=opened),
            answer('onboarding', True, ['Three screens for the pilot.']),
            answer('paywall', True, ['Final answer.'], continues='paywall', retire=['q1']),
        ])
        document = run(('t.json', encoded_transcript(SEGMENTS)), model)
        self.assertEqual(1, len(document['open_questions']))
        self.assertEqual('retired', document['open_questions'][0]['status'])

    def test_a_block_that_fails_its_gate_falls_back_without_inventing_content(self):
        # _gated allows one repair attempt per block, so a block stuck
        # failing its gate consumes two scripted answers before it falls back.
        model = Scripted([{'topic': 'paywall'}, {'topic': 'paywall'},
                          answer('onboarding', True, ['Three screens for the pilot.'])])
        document = run(('t.json', encoded_transcript(PAYWALL + ONBOARDING)), model)
        self.assertEqual(2, len(document['sections']))
        self.assertEqual([], document['sections'][0]['summary'])
        self.assertTrue(document['warnings'])

    def test_a_topic_not_yet_concluded_is_shown_running_not_summarised_as_decided(self):
        model = Scripted([answer('paywall', False, ['Still discussing, nothing decided yet.'])])
        document = run(('t.json', encoded_transcript(PAYWALL)), model)
        self.assertFalse(document['sections'][0]['concluded'])
        self.assertEqual([], document['sections'][0]['decisions'])

    def test_fixture_model_runs_offline_and_produces_provisional_sections(self):
        document = run(('t.json', encoded_transcript(SEGMENTS)), FixtureNotulationModel())
        self.assertTrue(document['synthetic'])
        self.assertTrue(document['provisional'])
        self.assertTrue(document['sections'])

    def test_empty_transcript_is_refused(self):
        from genai_server.synthesis import SynthesisError
        with self.assertRaises(SynthesisError):
            run(('t.json', encoded_transcript([])), FixtureNotulationModel())


class MarkdownTests(unittest.TestCase):
    def test_an_unconcluded_section_is_labelled_still_running(self):
        document = run(('t.json', encoded_transcript(PAYWALL)),
                       Scripted([answer('paywall', False, ['Still discussing.'])]))
        text = to_markdown(document)
        self.assertIn('still running', text)

    def test_a_decision_shows_its_grounding_quote(self):
        decisions = [{'segment_ids': ['t3'], 'text': 'Paywall after onboarding',
                      'quote': 'paywall goes after onboarding'}]
        document = run(('t.json', encoded_transcript(PAYWALL)),
                       Scripted([answer('paywall', True, ['x'], decisions=decisions)]))
        text = to_markdown(document)
        self.assertIn('paywall goes after onboarding', text)


class CLITests(unittest.TestCase):
    def test_cli_writes_json_and_markdown_with_the_fixture_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            transcript_path = Path(tmp) / 'meeting.json'
            transcript_path.write_bytes(encoded_transcript(SEGMENTS))
            out = Path(tmp) / 'out.json'
            code = main(['--transcript', str(transcript_path), '--out', str(out)])
            self.assertEqual(0, code)
            document = json.loads(out.read_text())
            self.assertTrue(document['sections'])
            self.assertTrue(out.with_suffix('.md').exists())

    def test_output_inside_the_tracked_repository_is_refused(self):
        from genai_server.synthesis import REPO_ROOT
        with tempfile.TemporaryDirectory() as tmp:
            transcript_path = Path(tmp) / 'meeting.json'
            transcript_path.write_bytes(encoded_transcript(SEGMENTS))
            inside_repo = REPO_ROOT / 'app' / 'server' / 'should_not_write_here.json'
            with self.assertRaises(SystemExit):
                main(['--transcript', str(transcript_path), '--out', str(inside_repo)])


if __name__ == '__main__':
    unittest.main()
