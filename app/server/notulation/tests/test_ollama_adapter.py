"""OllamaNotulationModel against a mocked urllib, no real Ollama server needed.

This cloud session cannot reach a user's local `ollama serve`, so these tests
are the only verification this adapter gets here: the request shape (model,
schema, messages) and the response/error handling, never a real local model's
actual summarisation quality.
"""
import json
import unittest
import urllib.error
from unittest.mock import MagicMock, patch

from genai_server.synthesis import ModelFailure, SynthesisError
from notulation.claude_adapter import SCHEMA, SYSTEM
from notulation.ollama_adapter import OllamaNotulationModel

BLOCK = [{'id': 't1', 'start': 0.0, 'end': 2.0, 'text': 'Paywall goes after onboarding.', 'speaker': 'SPEAKER_00'}]
CONTEXT = {'known_topics': ['onboarding'], 'open_questions': [{'id': 'q1', 'text': 'Who owns pricing copy?'}]}
ANSWER = {'topic': 'paywall', 'concluded': True, 'continues_topic': None,
          'summary': ['Paywall ships after onboarding.'], 'decisions': [], 'actions': [],
          'open_questions_add': [], 'open_questions_retire': []}


def fake_response(body):
    response = MagicMock()
    response.read.return_value = json.dumps(body).encode('utf-8')
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    return response


class OllamaAdapterTests(unittest.TestCase):
    def test_missing_model_is_refused_without_any_network_call(self):
        with patch('urllib.request.urlopen') as urlopen:
            with self.assertRaises(SynthesisError):
                OllamaNotulationModel(None)
            urlopen.assert_not_called()

    def test_successful_call_sends_the_shared_system_prompt_and_schema(self):
        model = OllamaNotulationModel('llama3.1', host='http://127.0.0.1:11434')
        with patch('urllib.request.urlopen') as urlopen:
            urlopen.return_value = fake_response(
                {'message': {'content': json.dumps(ANSWER)}, 'prompt_eval_count': 120, 'eval_count': 40})
            result = model.summarize_block(BLOCK, CONTEXT, None)
        request = urlopen.call_args[0][0]
        self.assertEqual('http://127.0.0.1:11434/api/chat', request.full_url)
        sent = json.loads(request.data)
        self.assertEqual('llama3.1', sent['model'])
        self.assertEqual(SCHEMA, sent['format'])
        self.assertEqual(SYSTEM, sent['messages'][0]['content'])
        self.assertIn('transcript_block', sent['messages'][1]['content'])
        self.assertIn('onboarding', sent['messages'][1]['content'])
        self.assertEqual(ANSWER, result.data)
        self.assertEqual('ollama', result.provider)
        self.assertEqual('llama3.1', result.model)
        self.assertEqual({'input_tokens': 120, 'output_tokens': 40}, result.usage)

    def test_a_repair_round_includes_the_previous_answer_and_errors(self):
        model = OllamaNotulationModel('llama3.1')
        repair = {'previous': {'topic': 'x'}, 'errors': ['Summary needs at least one non-empty bullet.']}
        with patch('urllib.request.urlopen') as urlopen:
            urlopen.return_value = fake_response({'message': {'content': json.dumps(ANSWER)}})
            model.summarize_block(BLOCK, CONTEXT, repair)
        sent = json.loads(urlopen.call_args[0][0].data)
        self.assertIn('failed these checks', sent['messages'][1]['content'])
        self.assertIn('Summary needs at least one non-empty bullet', sent['messages'][1]['content'])

    def test_connection_refused_is_a_synthesis_error_naming_ollama_serve(self):
        model = OllamaNotulationModel('llama3.1')
        with patch('urllib.request.urlopen', side_effect=urllib.error.URLError('connection refused')):
            with self.assertRaises(SynthesisError) as ctx:
                model.summarize_block(BLOCK, CONTEXT, None)
        self.assertIn('ollama serve', str(ctx.exception))

    def test_unpulled_model_404_is_a_synthesis_error_naming_ollama_pull(self):
        model = OllamaNotulationModel('not-pulled')
        error = urllib.error.HTTPError('url', 404, 'Not Found', {}, None)
        error.read = lambda: b'model not found'
        with patch('urllib.request.urlopen', side_effect=error):
            with self.assertRaises(SynthesisError) as ctx:
                model.summarize_block(BLOCK, CONTEXT, None)
        self.assertIn('ollama pull', str(ctx.exception))

    def test_other_http_error_is_a_model_failure_not_an_abort(self):
        model = OllamaNotulationModel('llama3.1')
        error = urllib.error.HTTPError('url', 500, 'Internal Server Error', {}, None)
        error.read = lambda: b'boom'
        with patch('urllib.request.urlopen', side_effect=error):
            with self.assertRaises(ModelFailure):
                model.summarize_block(BLOCK, CONTEXT, None)

    def test_timeout_is_a_model_failure(self):
        model = OllamaNotulationModel('llama3.1')
        with patch('urllib.request.urlopen', side_effect=TimeoutError('timed out')):
            with self.assertRaises(ModelFailure):
                model.summarize_block(BLOCK, CONTEXT, None)

    def test_non_json_answer_is_a_model_failure(self):
        model = OllamaNotulationModel('llama3.1')
        with patch('urllib.request.urlopen') as urlopen:
            urlopen.return_value = fake_response({'message': {'content': 'not json'}})
            with self.assertRaises(ModelFailure):
                model.summarize_block(BLOCK, CONTEXT, None)

    def test_missing_message_content_is_a_model_failure(self):
        model = OllamaNotulationModel('llama3.1')
        with patch('urllib.request.urlopen') as urlopen:
            urlopen.return_value = fake_response({'done': True})
            with self.assertRaises(ModelFailure):
                model.summarize_block(BLOCK, CONTEXT, None)


if __name__ == '__main__':
    unittest.main()
