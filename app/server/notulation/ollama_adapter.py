"""Ollama adapter for the rolling minutes in pipeline.py.

Optional, the same role claude_adapter.py plays for Anthropic, but for a
locally-run model instead of a hosted one: nothing leaves the machine Ollama
runs on. Uses only the standard library (`urllib`), so there is no extra
package to install; the only requirement is `ollama serve` reachable at
`--ollama-host` (default `http://127.0.0.1:11434`) with `--model` already
pulled (`ollama pull <name>`).

The system prompt and JSON schema are shared with claude_adapter.py rather
than duplicated: the task is the same regardless of which model answers it,
only how the call is made differs. Ollama enforces the schema itself
(grammar-constrained decoding, not the model's own judgement), and the
answer is checked again by check_block in pipeline.py regardless, for the
same reason claude_adapter.py's structured output still is: a schema can say
"a list of segment ids" but not "ids that exist in this block" or "a quote
that is really there".
"""
import json
import urllib.error
import urllib.request

from .claude_adapter import DATA_RULE, SCHEMA, SYSTEM, _data, _repair_text
from .pipeline import ModelResult
from genai_server.synthesis import ModelFailure, SynthesisError

DEFAULT_HOST = 'http://127.0.0.1:11434'
DEFAULT_TIMEOUT = 300


class OllamaNotulationModel:
    name = 'ollama'

    def __init__(self, model, host=DEFAULT_HOST, timeout=DEFAULT_TIMEOUT):
        if not model:
            raise SynthesisError('--model is required for --provider ollama: name a model you have pulled, '
                                 'e.g. `ollama pull llama3.1` then --model llama3.1.')
        self.model, self.host, self.timeout = model, host.rstrip('/'), timeout

    def summarize_block(self, block, context, repair):
        lines = [{'id': s['id'], 'start': round(s['start'], 1), 'speaker': s.get('speaker', ''), 'text': s['text']}
                 for s in block]
        text = (DATA_RULE + '\n\n' + _data('transcript_block', lines) + '\n'
                + _data('known_topics', context['known_topics']) + '\n'
                + _data('open_questions', context['open_questions']) + _repair_text(repair))
        payload = json.dumps({
            'model': self.model,
            'messages': [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': text}],
            'format': SCHEMA,
            'stream': False,
            'options': {'temperature': 0},
        }).encode('utf-8')
        request = urllib.request.Request(self.host + '/api/chat', data=payload,
                                         headers={'Content-Type': 'application/json'}, method='POST')
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode('utf-8', 'replace')
            if exc.code == 404:
                raise SynthesisError('Ollama does not have model "%s" pulled. Run `ollama pull %s` first. (%s)'
                                     % (self.model, self.model, detail)) from exc
            raise ModelFailure('Ollama returned HTTP %d: %s' % (exc.code, detail)) from exc
        except urllib.error.URLError as exc:
            raise SynthesisError('Could not reach Ollama at %s: %s. Is `ollama serve` running on this machine?'
                                 % (self.host, exc.reason)) from exc
        except TimeoutError as exc:
            raise ModelFailure('Ollama request timed out after %ds' % self.timeout) from exc
        answer = (body.get('message') or {}).get('content')
        if not isinstance(answer, str):
            raise ModelFailure('Ollama answer had no message content')
        try:
            data = json.loads(answer)
        except (TypeError, ValueError) as exc:
            raise ModelFailure('answer was not JSON') from exc
        usage = {'input_tokens': body.get('prompt_eval_count') or 0, 'output_tokens': body.get('eval_count') or 0}
        return ModelResult(data, 'ollama', self.model, False, usage)
