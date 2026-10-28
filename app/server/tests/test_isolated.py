"""Real subprocess tests, including a hung call and a subsequent healthy call."""
import os
import json
import subprocess
import sys
import threading
import time
import unittest

from genai_server.adapters import ExtractionInput, ExtractionOutput
from genai_server.isolated import IsolatedExtractor, IsolatedFailure


class HangingAdapter:
    def extract(self, request):
        while True:
            time.sleep(1)


class ClosedOutputAdapter:
    def extract(self, request):
        os.close(1)
        while True:
            time.sleep(1)


class FailingAdapter:
    def extract(self, request):
        print('PRIVATE_SOURCE_SENTINEL')
        raise RuntimeError('PRIVATE_CREDENTIAL_SENTINEL')


class NoisyAdapter:
    def extract(self, request):
        for _ in range(17):
            os.write(1, b'x' * 65536)
        return ExtractionOutput((), 'fixture', 'test', True, {})


class OversizedAdapter:
    def extract(self, request):
        return ExtractionOutput(({'text': 'x' * (2 * 1024 * 1024)},), 'fixture', 'test', True, {})


class TooManyNotesAdapter:
    def extract(self, request):
        return ExtractionOutput(tuple({} for _ in range(61)), 'fixture', 'test', True, {})


class IsolatedTests(unittest.TestCase):
    def request(self):
        return ExtractionInput('source_001', 1, 'image/png', b'synthetic',
                               ({'id': 'region_001', 'box': [0, 0, 1, 1]},))

    def adapter(self, factory, timeout=3):
        return IsolatedExtractor('fixture', module=__name__, factory=factory, timeout_seconds=timeout)

    def test_fixture_runs_offline_in_child(self):
        result = IsolatedExtractor('fixture').extract(self.request())
        self.assertTrue(result.synthetic)
        self.assertEqual('fixture', result.provider)
        self.assertEqual('region_001', result.notes[0]['region_id'])

    def test_hung_child_is_killed_and_next_call_progresses(self):
        started = time.monotonic()
        with self.assertRaisesRegex(IsolatedFailure, 'adapter_timeout'):
            self.adapter('HangingAdapter', timeout=.5).extract(self.request())
        self.assertLess(time.monotonic() - started, 2)
        result = IsolatedExtractor('fixture').extract(self.request())
        self.assertEqual('fixture', result.provider)

    def test_source_and_exception_text_are_not_exposed(self):
        with self.assertRaises(IsolatedFailure) as caught:
            self.adapter('FailingAdapter').extract(self.request())
        self.assertNotIn('PRIVATE_', str(caught.exception))
        self.assertEqual('adapter_process_failed', str(caught.exception))

    def test_native_output_is_bounded_and_child_terminated(self):
        with self.assertRaisesRegex(IsolatedFailure, 'adapter_output_limit'):
            self.adapter('NoisyAdapter').extract(self.request())

    def test_oversized_result_is_refused(self):
        with self.assertRaisesRegex(IsolatedFailure, 'adapter_process_failed'):
            self.adapter('OversizedAdapter').extract(self.request())

    def test_input_limit_prevents_starting_adapter(self):
        request = ExtractionInput('source_001', 1, 'image/png', b'x' * (7 * 1024 * 1024), ())
        with self.assertRaisesRegex(IsolatedFailure, 'adapter_input_limit'):
            IsolatedExtractor('fixture').extract(request)

    def test_child_refuses_overlong_input_even_with_valid_json(self):
        envelope = {'module':'genai_server.adapters', 'factory':'FixtureExtractor', 'configuration':{},
                    'request':{'source_id':'source_001','source_revision':1,'mime':'image/png','image':'','regions':[]}}
        payload = json.dumps(envelope).encode()
        payload += b' ' * (8 * 1024 * 1024 + 1 - len(payload))
        result = subprocess.run([sys.executable, '-m', 'genai_server.isolated'], input=payload,
                                capture_output=True, timeout=5)
        self.assertEqual(2, result.returncode)
        self.assertEqual(b'', result.stdout)

    def test_note_count_is_bounded_in_child(self):
        with self.assertRaisesRegex(IsolatedFailure, 'adapter_process_failed'):
            self.adapter('TooManyNotesAdapter').extract(self.request())

    def test_cancellation_stops_hung_child_before_timeout(self):
        for factory in ('HangingAdapter', 'ClosedOutputAdapter'):
            with self.subTest(factory=factory):
                cancelled = threading.Event()
                timer = threading.Timer(.25, cancelled.set)
                adapter = IsolatedExtractor('fixture', module=__name__, factory=factory,
                                            timeout_seconds=1, cancel_event=cancelled)
                timer.start()
                try:
                    with self.assertRaisesRegex(IsolatedFailure, 'adapter_cancelled'):
                        adapter.extract(self.request())
                finally:
                    timer.cancel()
                    timer.join()

    def test_timeout_must_be_finite_and_bounded(self):
        for value in (0, -1, float('nan'), float('inf'), 61):
            with self.subTest(value=value), self.assertRaises(ValueError):
                IsolatedExtractor('fixture', timeout_seconds=value)
