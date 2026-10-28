"""Claude adapter for overview.py's topic tracking.

Optional like claude_synthesis.py in app/server/genai_server: the anthropic
package and ANTHROPIC_API_KEY are only required when --provider claude is
actually chosen, so --provider fixture and --provider ollama need neither.
The instructions and schema themselves live in prompts.py, shared with
ollama_overview.py, so the two adapters cannot drift apart.

What leaves the machine: the chunk's text (the transcript being summarised)
and the titles/summaries of topics opened or closed so far. No audio, no
photographs: this prototype starts from a transcript that already exists.
"""
import json
import os

from prompts import SCHEMA, SYSTEM, build_body

MODEL = 'claude-opus-5-5'
FALLBACK_BETA = 'server-side-fallback-2026-07-01'
MAX_TOKENS = 8000


def load_env_key(path='.env'):
    """Reads ANTHROPIC_API_KEY from a local .env without overriding an
    already-set environment variable, same rule as claude_synthesis.py."""
    if os.environ.get('ANTHROPIC_API_KEY'):
        return
    try:
        lines = open(path, encoding='utf-8').read().splitlines()
    except OSError:
        return
    for line in lines:
        key, _, value = line.strip().partition('=')
        if key.strip() == 'ANTHROPIC_API_KEY' and value.strip():
            os.environ['ANTHROPIC_API_KEY'] = value.strip().strip('"\'')
            return


class ClaudeOverviewError(Exception):
    pass


def make_claude_provider(model=None, effort='medium', max_tokens=MAX_TOKENS, client=None, repo_root_env=None):
    """Returns a provider callable for overview.generate_overview(): reads the
    key, builds the client once, and does the repair-on-failure retry that
    verify_quotes' drops would otherwise silently eat (one retry, then the
    chunk's quotes that still fail are simply dropped by the caller, as
    SYNTHESIS.md's gates do)."""
    load_env_key(repo_root_env or '.env')
    load_env_key('../../../.env')  # also try the repository root's .env, same key, never overridden
    if client is None:
        try:
            import anthropic
        except ImportError as exc:
            raise ClaudeOverviewError('The anthropic package is not installed: pip install -r requirements.txt') from exc
        if not os.environ.get('ANTHROPIC_API_KEY'):
            raise ClaudeOverviewError('ANTHROPIC_API_KEY is not set; put it in .env, never in the repository.')
        client = anthropic.Anthropic()
    import anthropic as anthropic_module
    abort = (anthropic_module.AuthenticationError, anthropic_module.PermissionDeniedError,
             anthropic_module.BadRequestError, anthropic_module.NotFoundError)
    failure = (anthropic_module.APIStatusError, anthropic_module.APIConnectionError)

    def _call(content):
        try:
            with client.beta.messages.stream(
                    model=model or MODEL, max_tokens=max_tokens, system=SYSTEM,
                    messages=[{'role': 'user', 'content': content}],
                    output_config={'effort': effort, 'format': {'type': 'json_schema', 'schema': SCHEMA}},
                    betas=[FALLBACK_BETA], fallbacks='default') as stream:
                message = stream.get_final_message()
        except abort as exc:
            raise ClaudeOverviewError('%s from the API: %s' % (type(exc).__name__, exc)) from exc
        except failure as exc:
            raise ClaudeOverviewError('%s (temporary, retry the run)' % type(exc).__name__) from exc
        if message.stop_reason == 'refusal':
            raise ClaudeOverviewError('the model refused to answer this chunk')
        if message.stop_reason == 'max_tokens':
            raise ClaudeOverviewError('answer cut off at max_tokens; raise --chunk-chars down or max_tokens up')
        text = next((block.text for block in message.content if block.type == 'text'), None)
        data = json.loads(text)
        usage = {'input_tokens': message.usage.input_tokens, 'output_tokens': message.usage.output_tokens}
        return data, usage

    def provider(chunk, open_topics, closed_topics):
        body = build_body(chunk, open_topics, closed_topics)
        data, usage = _call([{'type': 'text', 'text': body}])
        return data['touched_topics'], usage

    return provider
