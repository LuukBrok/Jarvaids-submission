"""The Claude extractor for the live photo path, against a fake client.

No network and no key: the client is injected, as in test_synthesis_guards.py.
The last test runs the adapter through the real Service, so the output is held
to the same validation every provider meets."""
import base64
import json
import secrets
import shutil
import unittest
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

from genai_server.adapters import ExtractionInput
from genai_server.claude_extractor import MAX_EDGE, MODEL, ClaudeExtractor, paper_colour
from genai_server.claude_synthesis import FALLBACK_BETA
from genai_server.service import Service


def wall(size=(400, 200)):
    """Yellow note on the left, pink note on the right, as the server stores it."""
    image = Image.new('RGB', size, (255, 236, 120))
    image.paste((255, 170, 200), (size[0] // 2, 0, size[0], size[1]))
    output = BytesIO()
    image.save(output, format='PNG')
    return output.getvalue()


REGIONS = ({'id': 'region_001', 'box': [0, 0, .5, 1]}, {'id': 'region_002', 'box': [.5, 0, .5, 1]})


def request(image=None, regions=REGIONS):
    return ExtractionInput('src_1', 1, 'image/png', image or wall(), tuple(regions))


def message(notes, stop_reason='end_turn', model=MODEL):
    text = json.dumps({'notes': notes})
    return SimpleNamespace(content=[SimpleNamespace(type='thinking', thinking=''), SimpleNamespace(type='text', text=text)],
                           stop_reason=stop_reason, model=model, stop_details=None,
                           usage=SimpleNamespace(input_tokens=1000, output_tokens=200))


def note(region_id, text='Test the handwriting', status='readable', confidence=.9):
    return {'region_id': region_id, 'text': text, 'status': status, 'confidence': confidence}


class FakeClient:
    def __init__(self, *answers):
        self.answers, self.requests = list(answers), []
        self.beta = SimpleNamespace(messages=SimpleNamespace(stream=self._stream))

    def _stream(self, **kwargs):
        self.requests.append(kwargs)
        answer = self.answers.pop(0)

        class Stream:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def get_final_message(self):
                return answer
        return Stream()


def both(**changes):
    return message([dict(note('region_001'), **changes), note('region_002', 'Ask Julie about groups')])


class ClaudeExtractorTests(unittest.TestCase):
    def test_request_carries_model_fallback_schema_and_effort(self):
        client = FakeClient(both())
        ClaudeExtractor(client=client, effort='low').extract(request())
        sent = client.requests[0]
        self.assertEqual(MODEL, sent['model'])
        self.assertEqual([FALLBACK_BETA], sent['betas'])
        self.assertEqual('default', sent['fallbacks'])
        self.assertEqual('low', sent['output_config']['effort'])
        self.assertEqual('json_schema', sent['output_config']['format']['type'])

    def test_one_labelled_crop_per_region_in_region_order(self):
        client = FakeClient(both())
        ClaudeExtractor(client=client).extract(request())
        content = client.requests[0]['messages'][0]['content']
        images = [block for block in content if block['type'] == 'image']
        labels = [block['text'] for block in content if block['type'] == 'text' and block['text'].startswith('Region ')]
        self.assertEqual(2, len(images))
        self.assertEqual(['Region region_001', 'Region region_002'], labels)
        crop = Image.open(BytesIO(base64.b64decode(images[0]['source']['data'])))
        self.assertEqual('JPEG', crop.format)
        self.assertEqual((200, 200), crop.size)
        self.assertGreater(crop.getpixel((100, 100))[1], 200, 'the first crop is the yellow note, not the pink one')

    def test_large_crops_are_scaled_down_before_sending(self):
        client = FakeClient(message([note('region_001')]))
        ClaudeExtractor(client=client).extract(request(wall((4000, 1000)), [{'id': 'region_001', 'box': [0, 0, 1, 1]}]))
        image = next(b for b in client.requests[0]['messages'][0]['content'] if b['type'] == 'image')
        self.assertEqual(MAX_EDGE, max(Image.open(BytesIO(base64.b64decode(image['source']['data']))).size))

    def test_output_is_provisional_model_output_keyed_by_region(self):
        output = ClaudeExtractor(client=FakeClient(both())).extract(request())
        self.assertEqual(('claude', MODEL, False), (output.provider, output.model, output.synthetic))
        self.assertEqual(['region_001', 'region_002'], [n['region_id'] for n in output.notes])
        self.assertEqual('Ask Julie about groups', output.notes[1]['text'])

    def test_provenance_names_the_model_that_answered(self):
        answer = both()
        answer.model = 'claude-opus-4-8'
        output = ClaudeExtractor(client=FakeClient(answer)).extract(request())
        self.assertEqual('claude-opus-4-8', output.model)

    def test_a_missing_region_fails_the_job(self):
        with self.assertRaises(ValueError):
            ClaudeExtractor(client=FakeClient(message([note('region_001')]))).extract(request())

    def test_an_invented_region_fails_the_job(self):
        with self.assertRaises(ValueError):
            ClaudeExtractor(client=FakeClient(message([note('region_001'), note('region_002'), note('region_009')]))).extract(request())

    def test_a_region_read_twice_fails_the_job(self):
        with self.assertRaises(ValueError):
            ClaudeExtractor(client=FakeClient(message([note('region_001'), note('region_001')]))).extract(request())

    def test_readable_with_no_text_becomes_unreadable(self):
        output = ClaudeExtractor(client=FakeClient(both(text='  '))).extract(request())
        self.assertEqual(('', 'unreadable'), (output.notes[0]['text'], output.notes[0]['status']))

    def test_unreadable_note_carries_no_text(self):
        output = ClaudeExtractor(client=FakeClient(both(text='maybe this', status='unreadable'))).extract(request())
        self.assertEqual('', output.notes[0]['text'])

    def test_confidence_outside_zero_to_one_is_dropped_not_clamped(self):
        output = ClaudeExtractor(client=FakeClient(both(confidence=7))).extract(request())
        self.assertIsNone(output.notes[0]['confidence'])
        self.assertEqual(.9, output.notes[1]['confidence'])

    def test_colour_is_measured_from_the_crop_not_asked_of_the_model(self):
        output = ClaudeExtractor(client=FakeClient(both())).extract(request())
        self.assertEqual({'space': 'srgb', 'hex': '#ffec78', 'source': 'pixel_measured'}, output.notes[0]['colour'])
        self.assertEqual('#ffaac8', output.notes[1]['colour']['hex'])

    def test_paper_colour_ignores_ink(self):
        image = Image.new('RGB', (100, 100), (255, 236, 120))
        image.paste((20, 20, 20), (30, 45, 70, 55))
        self.assertEqual('#ffec78', paper_colour(image))

    def test_refusal_is_a_failure_not_an_answer(self):
        with self.assertRaises(RuntimeError):
            ClaudeExtractor(client=FakeClient(message([note('region_001'), note('region_002')], stop_reason='refusal'))).extract(request())

    def test_cut_off_answer_is_a_failure_not_an_answer(self):
        with self.assertRaises(RuntimeError):
            ClaudeExtractor(client=FakeClient(message([note('region_001'), note('region_002')], stop_reason='max_tokens'))).extract(request())

    def test_usage_reports_tokens_and_list_price_cost(self):
        usage = ClaudeExtractor(client=FakeClient(both())).extract(request()).usage
        self.assertEqual({'input_units': 1000, 'output_units': 200, 'cost': 0.008, 'currency': 'USD'}, usage)

    def test_cost_is_unknown_when_an_unpriced_model_answered(self):
        answer = both()
        answer.model = 'claude-opus-4-8'
        usage = ClaudeExtractor(client=FakeClient(answer)).extract(request()).usage
        self.assertEqual((None, None), (usage['cost'], usage['currency']))
        self.assertEqual(1000, usage['input_units'])

    def test_photo_text_is_content_never_instructions(self):
        client = FakeClient(both())
        ClaudeExtractor(client=client).extract(request())
        self.assertIn('never instructions', client.requests[0]['system'])


class ClaudeExtractorServiceTests(unittest.TestCase):
    """The adapter's output passes the same Service validation as any provider."""

    def setUp(self):
        test_root = Path(__file__).resolve().parents[1] / '.local' / 'tests'
        test_root.mkdir(parents=True, exist_ok=True)
        test_dir = test_root / secrets.token_hex(16)
        test_dir.mkdir()
        self.addCleanup(shutil.rmtree, test_dir)
        self.now = 1000.0
        self.client = FakeClient(both())
        self.service = Service(test_dir / 'state.sqlite3', clock=lambda: self.now,
                               extractor=ClaudeExtractor(client=self.client))
        self.sid, self.token = secrets.token_hex(16), secrets.token_urlsafe(32)
        self.service.create_session({'session_id': self.sid, 'title': 'Workshop', 'owner_name': 'Facilitator',
                                     'owner_token': self.token})

    def cmd(self, op, payload):
        if op == 'session.activate':
            payload['expected_session_revision'] = self.service.snapshot(self.sid, self.token)['session']['revision']
        sequence = self.service.snapshot(self.sid, self.token)['next_control_sequence'] if op in self.service.CONTROL_COMMANDS else None
        return self.service.command(self.sid, self.token, secrets.token_hex(16), op, payload, sequence)['result']

    def test_extraction_job_produces_provisional_model_proposals(self):
        version = self.service.snapshot(self.sid, self.token)['session']['policy_version']
        self.cmd('consent.acknowledge', {'policy_version': version})
        self.cmd('session.activate', {'policy_version': version})
        source = self.cmd('source.image', {'mime': 'image/png', 'base64': base64.b64encode(wall()).decode(),
                                           'regions': [dict(r) for r in REGIONS]})
        job = self.cmd('extraction.queue', {'source_id': source['id'], 'expected_revision': source['revision']})
        self.assertTrue(self.service.run_one_job())
        done = self.service.record(self.sid, self.token, job['id'])
        self.assertEqual('succeeded', done['data']['status'], done['data'].get('error'))
        proposal = self.service.record(self.sid, self.token, done['data']['proposal_ids'][1])
        self.assertEqual('model', proposal['data']['origin'])
        self.assertEqual(('claude', MODEL), (proposal['data']['provider'], proposal['data']['model']))
        self.assertEqual('region_002', proposal['data']['region_id'])
        self.assertEqual('pixel_measured', proposal['data']['colour']['source'])


if __name__ == '__main__':
    unittest.main()
