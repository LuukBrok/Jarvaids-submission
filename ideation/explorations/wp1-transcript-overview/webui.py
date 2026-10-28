"""A localhost browser UI for overview.py: paste a transcript, watch it
process chunk by chunk, read the result as topic cards instead of raw
Markdown or JSON.

Not a preview of the final Jarvaids UI (that is Julie's canvas, WP2); this is
a convenience front end for *this* prototype, so it is quicker to check a
real run than reading a .overview.md file, and so a non-technical teammate
can try it without the command line. Built on the standard library's
http.server, the same choice app/server/genai_server/http.py already made,
rather than adding a web framework dependency for a demo.

Binds to 127.0.0.1 only: this is a single-user local tool, not something to
expose on a network. No CSRF/auth hardening beyond that, unlike the real
server, because nothing but your own browser on your own machine ever talks
to it.

Run:
    python3 webui.py
    (open the printed http://127.0.0.1:8765/ in a browser)
"""
import argparse
import html
import json
import threading
import traceback
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

from overview import fixture_provider, generate_overview, parse_transcript_text, render_html_fragment, render_markdown

JOBS = {}
JOBS_LOCK = threading.Lock()

_CSS = """
:root { color-scheme: light dark; }
body { font-family: system-ui, sans-serif; max-width: 860px; margin: 0 auto; padding: 16px 20px 60px;
       line-height: 1.5; }
h1 { font-size: 1.4rem; }
.banner { background: #fff3cd; color: #664d03; border: 1px solid #ffe69c; border-radius: 8px; padding: 10px 14px;
          margin-bottom: 20px; }
form { display: grid; gap: 12px; margin-bottom: 24px; }
textarea { width: 100%; min-height: 260px; font-family: ui-monospace, Consolas, monospace; font-size: 0.85rem;
           box-sizing: border-box; padding: 8px; }
.row { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }
.row label { display: flex; flex-direction: column; gap: 4px; font-size: 0.85rem; }
input, select { padding: 6px; font-size: 0.9rem; }
button { padding: 8px 18px; font-size: 1rem; cursor: pointer; align-self: start; }
#log { background: #111; color: #0f0; font-family: ui-monospace, Consolas, monospace; font-size: 0.8rem;
       padding: 10px; border-radius: 6px; max-height: 240px; overflow-y: auto; white-space: pre-wrap; }
.topic { border: 1px solid #ccc; border-radius: 8px; padding: 12px 16px; margin-bottom: 14px; }
.topic header { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.topic h2 { font-size: 1.05rem; margin: 0; flex: 1; }
.badge { font-size: 0.72rem; padding: 2px 8px; border-radius: 99px; border: 1px solid #999; white-space: nowrap; }
.badge.closed { background: #d4edda; color: #155724; border-color: #a3cfab; }
.badge.open { background: #fff3cd; color: #664d03; border-color: #ffe69c; }
.badge.reopened { background: #d1e7ff; color: #0b3d91; border-color: #a8c8f0; }
.summary { white-space: pre-wrap; }
.source, .usage { color: #666; font-size: 0.85rem; }
details.notes { color: #a00; font-size: 0.85rem; }
footer.links a { margin-right: 14px; }
"""


def _page(title, body):
    """Builds a full page via plain string concatenation, never %-formatting
    or .format(): the CSS above is full of literal `%` and `{` characters
    (100%, border-radius: 8px { ... }), either of which breaks those."""
    return ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">\n'
           '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
           '<title>' + html.escape(title) + '</title>\n<style>' + _CSS + '</style></head><body>\n'
           + body + '\n</body></html>')


FORM_BODY = """
<h1>Transcript overview (WP1 prototype, F2.1)</h1>
<p class="banner">Model-made content. Provisional until a person accepts it (CLAUDE.md).
This local page is a convenience front end for overview.py, not the product's actual UI.</p>
<form method="post" action="/run">
<label>Transcript text (paste it, or the "HH:MM --&gt; HH:MM Speaker N" export, or synthesis.py-style segment JSON)
<textarea name="transcript" required placeholder="Paste your transcript here..."></textarea></label>
<div class="row">
<label>Provider
<select name="provider">
<option value="fixture">fixture (offline, mechanics only)</option>
<option value="ollama">ollama (local model)</option>
<option value="claude">claude (API key required)</option>
</select></label>
<label>Model (claude/ollama only)
<input name="model" placeholder="e.g. llama3.1"></label>
<label>Ollama host
<input name="ollama_host" placeholder="http://localhost:11434"></label>
<label>Chunk size (characters)
<input name="chunk_chars" type="number" value="3000" min="200" step="100"></label>
</div>
<button type="submit">Generate overview</button>
</form>
"""

FORM_PAGE = _page('Transcript overview (WP1 prototype)', FORM_BODY)

JOB_BODY_TEMPLATE = """
<h1>Processing __SOURCE__</h1>
<p><a href="/">&larr; back</a></p>
<div id="log">starting...</div>
<div id="result"></div>
<script>
const jobId = __JOB_ID__;
async function poll() {
  const r = await fetch('/job/' + jobId + '/status');
  const data = await r.json();
  document.getElementById('log').textContent = data.log.join('\\n');
  document.getElementById('log').scrollTop = document.getElementById('log').scrollHeight;
  if (data.state === 'done') {
    document.getElementById('result').innerHTML =
      '<p class="links"><a href="/job/' + jobId + '/overview.md">Download .md</a> &middot; ' +
      '<a href="/job/' + jobId + '/state.json">Download .json</a></p>' + data.result_html;
  } else if (data.state === 'error') {
    document.getElementById('result').innerHTML =
      '<p class="banner" style="background:#f8d7da;color:#842029;border-color:#f1aeb5;">' +
      'Failed: ' + data.error + '</p>';
  } else {
    setTimeout(poll, 800);
  }
}
poll();
</script>
"""


def _job_page(source, job_id):
    body = JOB_BODY_TEMPLATE.replace('__SOURCE__', html.escape(source)).replace('__JOB_ID__', json.dumps(job_id))
    return _page('Processing...', body)


def _new_job(source):
    job_id = uuid.uuid4().hex[:12]
    with JOBS_LOCK:
        JOBS[job_id] = {'state': 'running', 'log': ['queued'], 'source': source, 'result_html': None,
                        'markdown': None, 'json': None, 'error': None}
    return job_id


def _log(job_id, line):
    with JOBS_LOCK:
        JOBS[job_id]['log'].append(line)


def _run_job(job_id, transcript_text, provider_name, model, ollama_host, chunk_chars):
    try:
        turns = parse_transcript_text(transcript_text)
        if not turns:
            raise ValueError('No turns found in the pasted transcript.')
        if provider_name == 'fixture':
            provider = fixture_provider
        elif provider_name == 'ollama':
            from ollama_overview import make_ollama_provider
            provider = make_ollama_provider(model=model or None, host=ollama_host or None)
        else:
            from claude_overview import make_claude_provider
            provider = make_claude_provider(model=model or None)

        def report(event):
            if event['type'] == 'chunk_start':
                _log(job_id, 'Chunk %d/%d: calling %s...' % (event['index'] + 1, event['total'], provider_name))
            else:
                line = ('Chunk %d/%d: done in %.1fs, touched %d topic(s)'
                       % (event['index'] + 1, event['total'], event['elapsed'], event['topics_touched']))
                if event['notes']:
                    line += ' (%d quote(s) dropped, see notes below)' % len(event['notes'])
                _log(job_id, line)

        topics, chunks, notes, usage = generate_overview(turns, provider, chunk_chars=chunk_chars,
                                                          on_progress=report)
        source = 'pasted transcript'
        md = render_markdown(topics, chunks, notes, usage, source, len(turns))
        html_fragment = render_html_fragment(topics, chunks, notes, usage, source, len(turns))
        state_json = json.dumps({'topics': [
            {'id': t.id, 'title': t.title, 'status': t.status, 'summary': t.summary,
             'first_chunk': t.first_chunk, 'reopened': t.reopened, 'quotes': t.quotes}
            for t in sorted(topics.values(), key=lambda t: t.first_chunk)], 'usage': usage}, indent=2,
            ensure_ascii=False)
        with JOBS_LOCK:
            JOBS[job_id].update(state='done', result_html=html_fragment, markdown=md, json=state_json)
        _log(job_id, 'Done: %d topic(s) from %d chunk(s).' % (len(topics), len(chunks)))
    except Exception as exc:  # noqa: BLE001 - reported to the browser, not swallowed
        with JOBS_LOCK:
            JOBS[job_id]['state'] = 'error'
            JOBS[job_id]['error'] = str(exc)
        _log(job_id, 'ERROR: %s' % exc)
        traceback.print_exc()


class Handler(BaseHTTPRequestHandler):
    server_version = 'wp1-overview-webui/1'

    def log_message(self, fmt, *args):
        pass  # the browser-visible job log already gives feedback; keep the console quiet

    def _send(self, status, body, content_type='text/html; charset=utf-8'):
        encoded = body.encode('utf-8') if isinstance(body, str) else body
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):
        if self.path == '/':
            self._send(200, FORM_PAGE)
        elif self.path.startswith('/job/') and self.path.endswith('/status'):
            job_id = self.path.split('/')[2]
            with JOBS_LOCK:
                job = JOBS.get(job_id)
            if job is None:
                self._send(404, '{}', 'application/json')
                return
            self._send(200, json.dumps({'state': job['state'], 'log': job['log'],
                                        'result_html': job['result_html'], 'error': job['error']}),
                      'application/json')
        elif self.path.startswith('/job/') and self.path.endswith('/overview.md'):
            job_id = self.path.split('/')[2]
            with JOBS_LOCK:
                job = JOBS.get(job_id)
            if job is None or job['markdown'] is None:
                self._send(404, 'Not found')
                return
            self._send(200, job['markdown'], 'text/markdown; charset=utf-8')
        elif self.path.startswith('/job/') and self.path.endswith('/state.json'):
            job_id = self.path.split('/')[2]
            with JOBS_LOCK:
                job = JOBS.get(job_id)
            if job is None or job['json'] is None:
                self._send(404, 'Not found')
                return
            self._send(200, job['json'], 'application/json')
        elif self.path.startswith('/job/'):
            job_id = self.path.split('/')[2]
            with JOBS_LOCK:
                job = JOBS.get(job_id)
            if job is None:
                self._send(404, 'Unknown job')
                return
            self._send(200, _job_page(job['source'], job_id))
        elif self.path == '/favicon.ico':
            self._send(204, '')
        else:
            self._send(404, 'Not found')

    def do_POST(self):
        if self.path != '/run':
            self._send(404, 'Not found')
            return
        length = int(self.headers.get('Content-Length', 0))
        if length <= 0 or length > 10 * 1024 * 1024:
            self._send(400, 'Missing or oversized body (10 MB limit)')
            return
        body = self.rfile.read(length).decode('utf-8', errors='replace')
        fields = parse_qs(body)
        transcript_text = (fields.get('transcript') or [''])[0]
        provider_name = (fields.get('provider') or ['fixture'])[0]
        model = (fields.get('model') or [''])[0]
        ollama_host = (fields.get('ollama_host') or [''])[0]
        try:
            chunk_chars = int((fields.get('chunk_chars') or ['3000'])[0])
        except ValueError:
            chunk_chars = 3000
        if not transcript_text.strip():
            self._send(400, 'Paste a transcript first.')
            return

        job_id = _new_job('pasted transcript, %d char(s)' % len(transcript_text))
        thread = threading.Thread(target=_run_job, args=(job_id, transcript_text, provider_name, model,
                                                          ollama_host, chunk_chars), daemon=True)
        thread.start()
        self.send_response(303)
        self.send_header('Location', '/job/%s' % job_id)
        self.send_header('Content-Length', '0')
        self.end_headers()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args(argv)
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    print('Open http://127.0.0.1:%d/ in a browser. Ctrl+C to stop.' % args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
