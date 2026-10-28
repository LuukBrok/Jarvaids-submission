"""Ollama adapter for overview.py's topic tracking: a local model instead of
an API key. Runs against a local Ollama server (the Windows/Mac/Linux app, or
`ollama serve`), so nothing leaves the machine it runs on and there is no key
and no per-call cost. The instructions and schema are shared with
claude_overview.py via prompts.py, so the two adapters cannot drift apart.

Needs only the standard library: no extra `pip install` for this path.
See README.md for the PowerShell setup (install Ollama, `ollama pull`, run).
"""
import json
import urllib.error
import urllib.request

from prompts import SCHEMA, SYSTEM, build_body

DEFAULT_HOST = 'http://localhost:11434'
DEFAULT_MODEL = 'llama3.1'
DEFAULT_NUM_CTX = 8192
DEFAULT_TIMEOUT = 600  # local CPU inference on a long chunk can be slow


class OllamaOverviewError(Exception):
    pass


def make_ollama_provider(model=None, host=None, num_ctx=DEFAULT_NUM_CTX, timeout=DEFAULT_TIMEOUT):
    """Returns a provider callable for overview.generate_overview(). Unlike
    the Claude adapter there is no repair-on-failure retry here: a local
    model that cannot hold the schema is more likely to need a smaller
    --chunk-chars or a bigger model than a second try at the same prompt."""
    base = (host or DEFAULT_HOST).rstrip('/')
    chosen_model = model or DEFAULT_MODEL

    def _call(body_text):
        payload = json.dumps({
            'model': chosen_model,
            'messages': [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': body_text}],
            'format': SCHEMA,
            'stream': False,
            'options': {'num_ctx': num_ctx, 'temperature': 0},
        }).encode('utf-8')
        request = urllib.request.Request(base + '/api/chat', data=payload,
                                         headers={'Content-Type': 'application/json'}, method='POST')
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode('utf-8', errors='replace')
            if exc.code == 404:
                raise OllamaOverviewError(
                    'Ollama returned 404 for model %r: pull it first with `ollama pull %s`. %s'
                    % (chosen_model, chosen_model, detail)) from exc
            raise OllamaOverviewError('Ollama returned HTTP %d: %s' % (exc.code, detail)) from exc
        except urllib.error.URLError as exc:
            raise OllamaOverviewError(
                'Could not reach Ollama at %s (%s). Is it installed and running? On Windows it normally '
                'runs in the background after install; otherwise start it with `ollama serve` in another '
                'PowerShell window.' % (base, exc.reason)) from exc
        try:
            parsed = json.loads(raw)
        except ValueError as exc:
            raise OllamaOverviewError('Ollama response was not JSON: %r' % raw[:500]) from exc
        content = parsed.get('message', {}).get('content', '')
        try:
            data = json.loads(content)
        except ValueError as exc:
            raise OllamaOverviewError(
                'The model did not answer with valid JSON for the schema; try a smaller --chunk-chars, a '
                'different --model, or check the Ollama version supports structured outputs (0.5+). '
                'Got: %r' % content[:500]) from exc
        usage = {'input_tokens': parsed.get('prompt_eval_count', 0), 'output_tokens': parsed.get('eval_count', 0)}
        return data, usage

    def provider(chunk, open_topics, closed_topics):
        data, usage = _call(build_body(chunk, open_topics, closed_topics))
        touched = data.get('touched_topics', [])
        return touched, usage

    return provider
