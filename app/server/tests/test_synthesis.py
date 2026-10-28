"""Behaviour of the batch synthesis pipeline, end to end, with no network."""
import json
import tempfile
import unittest
from pathlib import Path

from genai_server.claude_synthesis import FALLBACK_BETA, MODEL, SCHEMAS, ClaudeSynthesisModel
from genai_server.synthesis import (FixtureSynthesisModel, ModelFailure, SynthesisError, check_claims,
                                    check_photo_notes, load_whisper, main, run, to_markdown)
from test_synthesis_guards import FakeClient, SEGMENTS, Scripted, jpeg, message, structure

OPENAI_WHISPER = {'text': '...', 'language': 'en', 'segments': [
    {'id': 0, 'seek': 0, 'start': 0.0, 'end': 4.0, 'text': ' We should test the handwriting first.'},
    {'id': 1, 'seek': 0, 'start': 4.0, 'end': 4.5, 'text': '   '},
    {'id': 2, 'seek': 0, 'start': 4.5, 'end': 9.0, 'text': ' Agreed, Sam will photograph the wall on Friday.',
     'speaker': 'SPEAKER_01'}]}


def encoded(value):
    return json.dumps(value).encode()


class WhisperInputTests(unittest.TestCase):
    def test_openai_whisper_output_is_read_and_empty_segments_skipped(self):
        segments, skipped = load_whisper(encoded(OPENAI_WHISPER))
        self.assertEqual(['t1', 't2'], [s['id'] for s in segments])
        self.assertEqual(1, skipped)
        self.assertEqual('We should test the handwriting first.', segments[0]['text'])
        self.assertEqual('SPEAKER_01', segments[1]['speaker'])

    def test_a_bare_segment_list_is_read(self):
        segments, _ = load_whisper(encoded([{'start': 1, 'end': 2, 'text': 'hello'}]))
        self.assertEqual([{'id': 't1', 'start': 1.0, 'end': 2.0, 'text': 'hello'}], segments)

    def test_malformed_transcripts_are_refused(self):
        for raw in (b'not json', encoded({'text': 'no segments'}), encoded([{'start': 'a', 'end': 1, 'text': 'x'}]),
                    encoded([{'start': True, 'end': 1, 'text': 'x'}]), encoded([{'start': 0, 'end': 1}])):
            with self.assertRaises(SynthesisError):
                load_whisper(raw)


class GateTests(unittest.TestCase):
    def test_quote_check_ignores_case_punctuation_and_spacing(self):
        kept, errors = check_claims({'claims': [{'text': 'Sam photographs the wall', 'kind': 'action',
                                                 'segment_ids': ['t2'], 'quote': 'agreed  SAM will photograph'}]},
                                    SEGMENTS)
        self.assertEqual([], errors)
        self.assertEqual(1, len(kept))

    def test_a_quote_may_span_the_segments_it_cites(self):
        kept, errors = check_claims({'claims': [{'text': 'Test then photograph', 'kind': 'point',
                                                 'segment_ids': ['t2', 't1'], 'quote': 'first. Agreed, Sam'}]},
                                    SEGMENTS)
        self.assertEqual([], errors)
        self.assertEqual(['t1', 't2'], kept[0]['segment_ids'])

    def test_note_marked_readable_must_have_text(self):
        kept, errors = check_photo_notes({'notes': [{'text': ' ', 'colour': 'pink', 'reading': 'readable'}]})
        self.assertEqual([], kept)
        self.assertEqual(1, len(errors))


class RunTests(unittest.TestCase):
    def test_wall_and_room_agreeing_become_one_point_with_both_sources(self):
        model = Scripted(
            photo=[{'notes': [{'text': 'Test handwriting first', 'colour': 'yellow', 'reading': 'readable'}]}],
            transcript=[{'claims': [
                {'text': 'Test the handwriting first', 'kind': 'point', 'segment_ids': ['t1'],
                 'quote': 'test the handwriting first'},
                {'text': 'Sam photographs the wall on Friday', 'kind': 'action', 'segment_ids': ['t2'],
                 'quote': 'Sam will photograph the wall on Friday'}]}],
            reconcile=[{'points': [
                {'text': 'Test handwriting first', 'claim_ids': ['p1.1', 'c1'], 'conflict': ''},
                {'text': 'Sam photographs the wall on Friday', 'claim_ids': ['c2'], 'conflict': ''}]}],
            structure=[structure([{'label': 'Next steps', 'point_ids': ['n1', 'n2']}],
                                 [{'from': 'n1', 'to': 'n2', 'label': 'then'}], 'flow')])
        document = run([('wall.jpg', jpeg())], ('t.json', encoded(OPENAI_WHISPER)), model)
        first, second = document['points']
        self.assertEqual('photo+speech', first['support'])
        self.assertEqual(['photo', 'speech'], [s['kind'] for s in first['sources']])
        self.assertEqual(['Test handwriting first', 'Test the handwriting first'], first['source_texts'])
        self.assertEqual(('speech', 'action'), (second['support'], second['kind']))
        self.assertEqual(['SPEAKER_01'], second['sources'][0]['speakers'])
        self.assertEqual('flow', document['structure']['form'])
        self.assertTrue(document['provisional'])
        self.assertEqual([], document['warnings'])
        self.assertEqual(4, document['usage']['calls'])

    def test_conflict_is_kept_not_settled(self):
        model = Scripted(transcript=[{'claims': [
            {'text': 'Friday', 'kind': 'point', 'segment_ids': ['t2'], 'quote': 'on Friday'}]}],
            reconcile=[{'points': [{'text': 'When to photograph', 'claim_ids': ['c1'],
                                    'conflict': 'The wall says Monday, the room said Friday.'}]}],
            structure=[structure([{'label': 'A', 'point_ids': ['n1']}])])
        document = run([], ('t.json', encoded(OPENAI_WHISPER)), model)
        self.assertEqual('The wall says Monday, the room said Friday.', document['points'][0]['conflict'])
        self.assertIn('Conflict:', to_markdown(document))

    def test_claims_that_fail_after_repair_are_reported_and_the_rest_kept(self):
        good = {'text': 'Test first', 'kind': 'point', 'segment_ids': ['t1'], 'quote': 'test the handwriting'}
        bad = {'text': 'Alex owns it', 'kind': 'action', 'segment_ids': ['t2'], 'quote': 'Alex will'}
        model = Scripted(transcript=[{'claims': [good, bad]}, {'claims': [good, bad]}],
                         reconcile=[{'points': [{'text': 'Test first', 'claim_ids': ['c1'], 'conflict': ''}]}],
                         structure=[structure([{'label': 'A', 'point_ids': ['n1']}])])
        document = run([], ('t.json', encoded(OPENAI_WHISPER)), model)
        self.assertEqual(['c1'], [c['id'] for c in document['claims']])
        self.assertEqual(1, len(document['rejected']))
        self.assertTrue(any('left out' in w for w in document['warnings']))

    def test_a_failed_repair_call_keeps_what_the_first_answer_got_right(self):
        good = {'text': 'Test first', 'kind': 'point', 'segment_ids': ['t1'], 'quote': 'test the handwriting'}
        bad = {'text': 'Alex owns it', 'kind': 'action', 'segment_ids': ['t2'], 'quote': 'Alex will'}
        model = Scripted(transcript=[{'claims': [good, bad]}, ModelFailure('overloaded')],
                         reconcile=[{'points': [{'text': 'Test first', 'claim_ids': ['c1'], 'conflict': ''}]}],
                         structure=[structure([{'label': 'A', 'point_ids': ['n1']}])])
        document = run([], ('t.json', encoded(OPENAI_WHISPER)), model)
        self.assertEqual(['c1'], [c['id'] for c in document['claims']])
        self.assertEqual(1, len(document['rejected']))

    def test_failed_reconcile_falls_back_to_separate_points(self):
        model = Scripted(photo=[{'notes': [{'text': 'A', 'colour': 'blue', 'reading': 'readable'},
                                           {'text': 'B', 'colour': 'blue', 'reading': 'partial'}]}],
                         reconcile=[ModelFailure('overloaded')],
                         structure=[structure([{'label': 'X', 'point_ids': ['n1', 'n2']}])])
        document = run([('wall.jpg', jpeg())], None, model)
        self.assertEqual(['A', 'B'], [p['text'] for p in document['points']])
        self.assertTrue(document['gates'][1]['fallback'])
        self.assertTrue(any('nothing merged' in w for w in document['warnings']))

    def test_failed_structure_falls_back_to_an_unorganised_list(self):
        model = Scripted(photo=[{'notes': [{'text': 'A', 'colour': 'blue', 'reading': 'readable'}]}],
                         reconcile=[{'points': [{'text': 'A', 'claim_ids': ['p1.1'], 'conflict': ''}]}],
                         structure=[{'form': 'pie'}, {'form': 'pie'}])
        document = run([('wall.jpg', jpeg())], None, model)
        self.assertEqual(('ordered', True), (document['structure']['form'], document['structure']['fallback']))
        self.assertEqual([['n1']], [g['point_ids'] for g in document['structure']['groups']])

    def test_fixture_output_says_it_is_synthetic(self):
        document = run([('wall.jpg', jpeg())], ('t.json', encoded(OPENAI_WHISPER)), FixtureSynthesisModel())
        self.assertTrue(document['synthetic'])
        self.assertIn('SYNTHETIC', to_markdown(document))
        self.assertEqual(4, len(document['points']))

    def test_nothing_to_read_is_refused(self):
        with self.assertRaises(SynthesisError):
            run([], None, FixtureSynthesisModel())


class ClaudeAdapterTests(unittest.TestCase):
    def test_request_uses_structured_output_and_refusal_fallback(self):
        client = FakeClient(message('{"points": []}'))
        result = ClaudeSynthesisModel(client=client).reconcile([{'id': 'c1', 'text': 'x'}], None)
        request = client.requests[0]
        self.assertEqual(MODEL, request['model'])
        self.assertEqual([FALLBACK_BETA], request['betas'])
        self.assertEqual('default', request['fallbacks'])
        self.assertEqual(SCHEMAS['reconcile'], request['output_config']['format']['schema'])
        self.assertEqual('medium', request['output_config']['effort'])
        self.assertNotIn('thinking', request)
        self.assertEqual(({'points': []}, False), (result.data, result.synthetic))
        self.assertEqual({'input_tokens': 100, 'output_tokens': 50}, result.usage)

    def test_repair_sends_the_previous_answer_and_the_failed_checks(self):
        client = FakeClient(message('{"claims": []}'))
        ClaudeSynthesisModel(client=client).extract_claims(
            SEGMENTS, {'previous': {'claims': ['old']}, 'errors': ['Claim 0 quote is not in the segments it cites.']})
        text = client.requests[0]['messages'][0]['content'][0]['text']
        self.assertIn('<failed_checks>', text)
        self.assertIn('Claim 0 quote is not in the segments it cites.', text)

    def test_photo_goes_as_a_base64_image_block(self):
        client = FakeClient(message('{"notes": []}'))
        ClaudeSynthesisModel(client=client).read_photo(b'\xff\xd8jpeg', 'image/jpeg', None)
        block = client.requests[0]['messages'][0]['content'][0]
        self.assertEqual(('image', 'image/jpeg', '/9hqcGVn'),
                         (block['type'], block['source']['media_type'], block['source']['data']))

    def test_answer_that_is_not_json_is_a_failure(self):
        with self.assertRaises(ModelFailure):
            ClaudeSynthesisModel(client=FakeClient(message('not json'))).reconcile([], None)

    def test_every_schema_is_closed(self):
        def walk(schema):
            if schema.get('type') == 'object':
                self.assertFalse(schema['additionalProperties'])
                self.assertEqual(sorted(schema['properties']), sorted(schema['required']))
                for child in schema['properties'].values():
                    walk(child)
            if schema.get('type') == 'array':
                walk(schema['items'])
        for schema in SCHEMAS.values():
            walk(schema)


class CommandLineTests(unittest.TestCase):
    def test_fixture_run_writes_json_and_markdown(self):
        with tempfile.TemporaryDirectory() as directory:
            photo, transcript = Path(directory) / 'wall.jpg', Path(directory) / 'meeting.json'
            photo.write_bytes(jpeg())
            transcript.write_bytes(encoded(OPENAI_WHISPER))
            out = Path(directory) / 'out' / 'result.json'
            code = main(['--photo', str(photo), '--transcript', str(transcript), '--out', str(out)])
            self.assertEqual(0, code)
            document = json.loads(out.read_text(encoding='utf-8'))
            self.assertEqual('jarvaids.synthesis/1', document['schema'])
            self.assertTrue(out.with_suffix('.md').read_text(encoding='utf-8').startswith('# Synthesis proposal'))

    def test_bad_input_exits_non_zero_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            transcript = Path(directory) / 'meeting.json'
            transcript.write_bytes(b'not json')
            out = Path(directory) / 'result.json'
            self.assertEqual(1, main(['--transcript', str(transcript), '--out', str(out)]))
            self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
