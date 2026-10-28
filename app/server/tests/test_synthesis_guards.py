"""One named test per synthesis guard. tests/synthesis_mutation_check.py removes
each guard in turn and requires the test named here to fail, not error."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image

from genai_server import synthesis
from genai_server.claude_synthesis import MODEL, ClaudeSynthesisModel, load_env_key
from genai_server.synthesis import (FixtureSynthesisModel, Ledger, ModelFailure, ModelResult, BudgetExceeded,
                                    check_claims, check_reconcile, check_structure, load_whisper, output_allowed,
                                    prepare_photo, run)

SEGMENTS = [{'id': 't1', 'start': 0.0, 'end': 4.0, 'text': 'We should test the handwriting first.'},
            {'id': 't2', 'start': 4.0, 'end': 9.0, 'text': 'Agreed, Sam will photograph the wall on Friday.'}]
CLAIMS = [{'id': 'p1.1', 'text': 'Test handwriting', 'kind': 'point', 'sources': [{'kind': 'photo'}]},
          {'id': 'c1', 'text': 'Test the handwriting first', 'kind': 'point', 'sources': [{'kind': 'speech'}]},
          {'id': 'c2', 'text': 'Photograph the wall', 'kind': 'action', 'sources': [{'kind': 'speech'}]}]
POINTS = [{'id': 'n1'}, {'id': 'n2'}, {'id': 'n3'}]


def jpeg(size=(40, 20), orientation=None, gps=False):
    exif = Image.Exif()
    if orientation:
        exif[0x0112] = orientation
    if gps:
        exif[0x8825] = {1: 'N', 2: (52.0, 5.0, 0.0)}
    output = BytesIO()
    image = Image.new('RGB', size, 'yellow')
    image.paste((0, 0, 255), (0, 0, size[0] // 2, size[1]))
    image.save(output, format='JPEG', exif=exif.tobytes())
    return output.getvalue()


def structure(groups, relations=(), form='cluster'):
    return {'form': form, 'reason': 'Because.', 'groups': groups, 'relations': list(relations)}


class Scripted:
    """A model that answers each step from a queue, and records what it was sent."""
    name = 'scripted'

    def __init__(self, **answers):
        self.answers, self.sent = {k: list(v) for k, v in answers.items()}, []

    def _next(self, step, *args):
        self.sent.append((step,) + args)
        answer = self.answers[step].pop(0)
        if isinstance(answer, Exception):
            raise answer
        return ModelResult(answer, 'scripted', 'scripted-v1', True, {'input_tokens': 10, 'output_tokens': 5})

    def read_photo(self, image, mime, repair):
        return self._next('photo', image, repair)

    def extract_claims(self, segments, repair):
        return self._next('transcript', segments, repair)

    def reconcile(self, claims, repair):
        return self._next('reconcile', claims, repair)

    def structure(self, points, form, repair):
        return self._next('structure', points, repair)


def message(text, stop='end_turn', model=MODEL):
    return SimpleNamespace(content=[SimpleNamespace(type='thinking', thinking=''), SimpleNamespace(type='text', text=text)],
                           stop_reason=stop, model=model, stop_details=None,
                           usage=SimpleNamespace(input_tokens=100, output_tokens=50))


class FakeClient:
    def __init__(self, *replies):
        self.replies, self.requests = list(replies), []
        self.beta = SimpleNamespace(messages=SimpleNamespace(stream=self._stream))

    def _stream(self, **request):
        self.requests.append(request)
        reply = self.replies.pop(0)

        class Stream:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def get_final_message(self):
                return reply
        return Stream()


class SynthesisGuardTests(unittest.TestCase):
    # Phase 1 gates

    def test_claim_quote_must_appear_in_cited_segments(self):
        kept, errors = check_claims({'claims': [
            {'text': 'Owner is Alex', 'kind': 'action', 'segment_ids': ['t2'], 'quote': 'Alex will do it'}]}, SEGMENTS)
        self.assertEqual([], kept)
        self.assertEqual(1, len(errors))

    def test_claim_must_cite_segments_that_exist(self):
        kept, errors = check_claims({'claims': [
            {'text': 'Test first', 'kind': 'point', 'segment_ids': ['t1', 't99'], 'quote': 'test the handwriting'}]},
            SEGMENTS)
        self.assertEqual([], kept)
        self.assertIn('t99', errors[0])

    def test_segment_that_ends_before_it_starts_is_refused(self):
        with self.assertRaises(synthesis.SynthesisError):
            load_whisper(json.dumps({'segments': [{'start': 5, 'end': 2, 'text': 'backwards'}]}))

    # Phase 2 gate

    def test_reconcile_refuses_a_dropped_claim(self):
        merged, errors = check_reconcile({'points': [
            {'text': 'Test handwriting first', 'claim_ids': ['p1.1', 'c1'], 'conflict': ''}]}, CLAIMS)
        self.assertIsNone(merged)
        self.assertTrue(any('c2' in e for e in errors))

    def test_reconcile_refuses_a_claim_counted_twice(self):
        merged, errors = check_reconcile({'points': [
            {'text': 'A', 'claim_ids': ['p1.1', 'c1'], 'conflict': ''},
            {'text': 'B', 'claim_ids': ['c1', 'c2'], 'conflict': ''}]}, CLAIMS)
        self.assertIsNone(merged)

    def test_reconcile_refuses_an_invented_claim(self):
        merged, errors = check_reconcile({'points': [
            {'text': 'A', 'claim_ids': ['p1.1', 'c1', 'c2', 'c7'], 'conflict': ''}]}, CLAIMS)
        self.assertIsNone(merged)

    def test_support_comes_from_sources_not_the_model(self):
        self.assertEqual('speech', synthesis.support_of([{'kind': 'speech'}, {'kind': 'speech'}]))
        self.assertEqual('photo+speech', synthesis.support_of([{'kind': 'photo'}, {'kind': 'speech'}]))

    # Phase 3 gate

    def test_structure_refuses_a_dropped_point(self):
        value, errors = check_structure(structure([{'label': 'A', 'point_ids': ['n1', 'n2']}]), POINTS)
        self.assertIsNone(value)

    def test_structure_refuses_a_point_in_two_groups(self):
        value, errors = check_structure(structure([{'label': 'A', 'point_ids': ['n1', 'n2']},
                                                   {'label': 'B', 'point_ids': ['n2', 'n3']}]), POINTS)
        self.assertIsNone(value)

    def test_relation_must_join_existing_points(self):
        value, errors = check_structure(structure([{'label': 'A', 'point_ids': ['n1', 'n2', 'n3']}],
                                                  [{'from': 'n1', 'to': 'n9', 'label': 'leads to'}], 'flow'), POINTS)
        self.assertIsNone(value)

    def test_named_form_is_not_overridden(self):
        value, errors = check_structure(structure([{'label': 'A', 'point_ids': ['n1', 'n2', 'n3']}]), POINTS,
                                        form='timeline')
        self.assertIsNone(value)

    def test_group_cannot_exceed_the_server_cluster_cap(self):
        points = [{'id': 'n%d' % i} for i in range(1, 26)]
        value, errors = check_structure(structure([{'label': 'All', 'point_ids': [p['id'] for p in points]}]), points)
        self.assertIsNone(value)

    # Running

    def test_gate_repairs_once_then_falls_back(self):
        bad = {'points': []}
        model = Scripted(transcript=[{'claims': [
            {'text': 'Test first', 'kind': 'point', 'segment_ids': ['t1'], 'quote': 'test the handwriting'}]}],
            reconcile=[bad, bad, bad], structure=[structure([{'label': 'A', 'point_ids': ['n1']}])])
        transcript = json.dumps({'segments': [{'start': 0, 'end': 4, 'text': SEGMENTS[0]['text']}]})
        document = run([], ('t.json', transcript.encode()), model)
        calls = [s for s in model.sent if s[0] == 'reconcile']
        self.assertEqual(2, len(calls))
        self.assertIsNotNone(calls[1][2])
        self.assertEqual(['Claims appear in no point: c1.'], calls[1][2]['errors'])
        self.assertEqual(1, len(document['points']))

    def test_budget_stops_before_the_next_call(self):
        ledger = Ledger(15)
        result = ModelResult({}, 'x', 'y', True, {'input_tokens': 10, 'output_tokens': 5})
        ledger.call('one', lambda: result)
        called = []
        with self.assertRaises(BudgetExceeded):
            ledger.call('two', lambda: called.append(1) or result)
        self.assertEqual([], called)

    def test_unreadable_note_is_flagged_not_merged(self):
        model = Scripted(photo=[{'notes': [{'text': '', 'colour': 'pink', 'reading': 'unreadable'},
                                           {'text': 'Ask users', 'colour': 'yellow', 'reading': 'readable'}]}],
                         reconcile=[{'points': [{'text': 'Ask users', 'claim_ids': ['p1.2'], 'conflict': ''}]}] * 2,
                         structure=[structure([{'label': 'A', 'point_ids': ['n1']}])] * 2)
        document = run([('wall.jpg', jpeg())], None, model)
        self.assertEqual(['p1.2'], [c['id'] for c in document['claims']])
        self.assertTrue(any('unreadable' in w for w in document['warnings']))

    def test_over_sixty_points_are_not_sent_to_structure(self):
        segments = [{'start': i, 'end': i + 1, 'text': 'point number %d' % i} for i in range(61)]
        model = FixtureSynthesisModel()
        sent = []
        original = model.structure
        model.structure = lambda *a: sent.append(1) or original(*a)
        document = run([], ('t.json', json.dumps(segments).encode()), model)
        self.assertEqual([], sent)
        self.assertTrue(document['structure']['fallback'])

    def test_output_must_stay_out_of_tracked_files(self):
        root = Path(tempfile.gettempdir()) / 'repo'
        self.assertFalse(output_allowed(root / 'app' / 'result.json', root))
        self.assertTrue(output_allowed(root / 'evidence' / 'raw' / 'result.json', root))

    # What leaves the machine

    def test_photo_sent_to_a_model_carries_no_exif(self):
        image, _, _ = prepare_photo(jpeg(gps=True))
        with Image.open(BytesIO(image)) as sent:
            self.assertEqual(0, len(sent.getexif()))

    def test_iphone_mpo_photo_is_read_from_its_primary_image(self):
        photo, preview, output = Image.new('RGB', (40, 20), 'yellow'), Image.new('RGB', (10, 5), 'red'), BytesIO()
        photo.save(output, format='MPO', save_all=True, append_images=[preview])
        try:
            _, width, height = prepare_photo(output.getvalue())
        except synthesis.SynthesisError as exc:
            self.fail('an iPhone photo was refused: %s' % exc)
        self.assertEqual((40, 20), (width, height))

    def test_photo_orientation_is_applied_before_sending(self):
        image, width, height = prepare_photo(jpeg((40, 20), orientation=6))
        self.assertEqual((20, 40), (width, height))

    def test_model_receives_the_prepared_photo_not_the_original(self):
        model = Scripted(photo=[{'notes': []}])
        run([('wall.jpg', jpeg(gps=True))], None, model)
        with Image.open(BytesIO(model.sent[0][1])) as sent:
            self.assertEqual(0, len(sent.getexif()))

    def test_env_key_never_overrides_the_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / '.env'
            path.write_text('ANTHROPIC_API_KEY=from-file\n', encoding='utf-8')
            with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'from-environment'}):
                load_env_key(path)
                self.assertEqual('from-environment', os.environ['ANTHROPIC_API_KEY'])

    def test_adapter_errors_are_reported_not_raised_when_run_as_a_module(self):
        # The transcript is unreadable, so no API call can happen even on a
        # machine with a key in .env and the package installed.
        with tempfile.TemporaryDirectory() as directory:
            transcript = Path(directory) / 'meeting.json'
            transcript.write_bytes(b'not json')
            environment = {k: v for k, v in os.environ.items() if k != 'ANTHROPIC_API_KEY'}
            done = subprocess.run([sys.executable, '-m', 'genai_server.synthesis', '--provider', 'claude',
                                   '--transcript', str(transcript), '--out', str(Path(directory) / 'r.json')],
                                  cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True,
                                  env=environment, timeout=60)
            self.assertEqual(1, done.returncode)
            self.assertNotIn('Traceback', done.stderr)
            self.assertTrue(done.stderr.startswith('synthesis: '))

    # Claude adapter

    def test_refusal_is_a_failure_not_an_answer(self):
        model = ClaudeSynthesisModel(client=FakeClient(message('{"points": []}', stop='refusal')))
        with self.assertRaises(ModelFailure) as caught:
            model.reconcile([], None)
        self.assertIn('refused', str(caught.exception))

    def test_cut_off_answer_is_a_failure_not_an_answer(self):
        model = ClaudeSynthesisModel(client=FakeClient(message('{"points": []}', stop='max_tokens')))
        with self.assertRaises(ModelFailure) as caught:
            model.reconcile([], None)
        self.assertIn('max_tokens', str(caught.exception))

    def test_provenance_names_the_model_that_answered(self):
        model = ClaudeSynthesisModel(client=FakeClient(message('{"points": []}', model='fallback-model')))
        self.assertEqual('fallback-model', model.reconcile([], None).model)


if __name__ == '__main__':
    unittest.main()
