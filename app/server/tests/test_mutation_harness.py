"""The guard checker must distinguish an assertion failure from broken execution.

Patches `mutation_runner`, which is where the subprocess now lives: the three
harnesses shared forty identical lines and now share one implementation, so
these properties are tested once rather than for the service harness alone.
"""
import subprocess
import unittest
from unittest.mock import patch

import mutation_check as checker
import mutation_runner


class HarnessTests(unittest.TestCase):
    def test_source_is_copied_and_runtime_environment_is_preserved(self):
        original = checker.TARGET.read_bytes()
        def completed(args, **kwargs):
            self.assertNotEqual(checker.ROOT, kwargs['cwd'])
            self.assertEqual('scratch-only', (kwargs['cwd'] / 'genai_server/service.py').read_text())
            self.assertEqual('inherited', kwargs['env']['HARNESS_TEST_MARKER'])
            self.assertEqual(180, kwargs['timeout'])
            self.assertIn('-B', args)
            return subprocess.CompletedProcess(args, 0, '', 'Ran 56 tests\nOK\n')
        with patch.dict('os.environ', {'HARNESS_TEST_MARKER': 'inherited'}), patch.object(mutation_runner.subprocess, 'run', completed):
            self.assertEqual((True, set()), checker.run_suite('scratch-only'))
        self.assertEqual(original, checker.TARGET.read_bytes())

    def test_import_error_is_not_a_behavioural_kill(self):
        result = subprocess.CompletedProcess([], 1, '', 'ERROR: test_guard (unittest.loader)\nRan 1 tests\nFAILED (errors=1)')
        with patch.object(mutation_runner.subprocess, 'run', return_value=result):
            with self.assertRaisesRegex(RuntimeError, 'infrastructure'):
                checker.run_suite()

    def test_assertion_failure_keeps_the_intended_name(self):
        result = subprocess.CompletedProcess([], 1, '', 'FAIL: test_guard (guards.Tests)\nRan 1 test\nFAILED (failures=1)')
        with patch.object(mutation_runner.subprocess, 'run', return_value=result):
            self.assertEqual((False, {'test_guard'}), checker.run_suite())

    def test_timeout_does_not_mutate_original_source(self):
        original = checker.TARGET.read_bytes()
        with patch.object(mutation_runner.subprocess, 'run', side_effect=subprocess.TimeoutExpired('python', 180)):
            with self.assertRaises(subprocess.TimeoutExpired):
                checker.run_suite('scratch-only')
        self.assertEqual(original, checker.TARGET.read_bytes())
