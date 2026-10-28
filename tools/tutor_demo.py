"""Three repeatable localhost links for a tutor demonstration. No dependencies.

The completed-session link is a GET-only local reader. Its owner credential
stays in the ignored private session file and is never put in a URL or page.
Fresh meetings use the ordinary client and its normal agreement/capture flow.
"""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
from urllib.error import HTTPError
from urllib.parse import unquote, urlsplit
from urllib.request import ProxyHandler, Request, build_opener
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
API = 'http://127.0.0.1:3000'
CLIENT = 'http://127.0.0.1:5173'
PORT = 5174
LINKS = (f'http://127.0.0.1:{PORT}/completed/',
         f'http://127.0.0.1:{PORT}/showcase/', CLIENT + '/client/')
OPENER = build_opener(ProxyHandler({}))


def safe_file(base, name):
    """Resolve only files under the named public tree, never private siblings."""
    if any(part in ('..', '.') or part.startswith('.') for part in name.split('/')):
        return None
    target = (base / (name or 'index.html')).resolve()
    return target if target.is_relative_to(base.resolve()) and target.is_file() else None


class DemoServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, root=ROOT, api=API):
        if address[0] != '127.0.0.1':
            raise ValueError('The demo reader binds to 127.0.0.1 only.')
        self.root, self.api = Path(root), api
        super().__init__(address, Handler)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, status, body, content_type='text/html; charset=utf-8'):
        payload = body.encode('utf-8') if isinstance(body, str) else body
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.end_headers()
        self.wfile.write(payload)

    def boundary(self):
        port = self.server.server_port
        allowed = {f'127.0.0.1:{port}', f'localhost:{port}'}
        if self.headers.get('Host') not in allowed:
            self.reply(403, 'Use the localhost demo address.')
            return False
        origin = self.headers.get('Origin')
        if origin is not None and origin not in {f'http://{host}' for host in allowed}:
            self.reply(403, 'This origin cannot read the local demo.')
            return False
        return True

    def credentials(self):
        config = json.loads((self.server.root / '.local/watch-test/private-session.json').read_text(encoding='utf-8'))
        if not re.fullmatch(r'[0-9a-f]{32}', config['session_id']):
            raise ValueError('Invalid local demo session ID.')
        return config

    def do_GET(self):
        if not self.boundary():
            return
        route = urlsplit(self.path)
        path = unquote(route.path)
        if path == '/tutor-health':
            self.reply(200, json.dumps({'service': 'jarvaids-tutor-demo'}), 'application/json')
            return
        if path == '/':
            self.reply(200, '<!doctype html><meta charset="utf-8"><title>Jarvaids tutor links</title>'
                       '<h1>Jarvaids tutor links</h1><ol>'
                       '<li><a href="/completed/">Completed repair-cafe test</a></li>'
                       '<li><a href="/showcase/">Inputs, outputs and screenshots</a></li>'
                       f'<li><a href="{CLIENT}/client/">Fresh, empty working tool</a></li></ol>'
                       '<p>Recording starts only after agreement, Start capture and Listen. '
                       'If the PC restarts, run Open Tutor Demo.cmd first.</p>')
            return
        if path in ('/completed', '/completed/'):
            try:
                config = self.credentials()
            except (OSError, ValueError, KeyError):
                self.reply(404, 'The private completed-test connection is unavailable. '
                           '<a href="/showcase/">Open the saved showcase</a>.')
                return
            html = (self.server.root / 'app/client/index.html').read_text(encoding='utf-8')
            html = html.replace('<head>', '<head><base href="/client/">', 1)
            script = '''<script type="module">
import {connectSession} from '/client/app.mjs';
import {GenAIClient} from '/server/client.mjs';
const localRead = (url, options) => {
  const target = new URL(url);
  return fetch('/completed-api' + target.pathname + target.search, options);
};
try {
  await connectSession(new GenAIClient({baseUrl:location.origin,
    sessionId:SESSION_ID, token:'local-read-only-view', fetchImpl:localRead}));
  document.title='Jarvaids | Completed repair-cafe test';
  document.getElementById('tab-overview').click();
  document.getElementById('zoom-fit').click();
} catch {
  const message=document.createElement('p');
  message.textContent='The completed session is unavailable or its retention has expired. Open the saved showcase using the link below.';
  const link=document.createElement('a');link.href='/showcase/';link.textContent='Open saved showcase';
  document.getElementById('screen-setup').prepend(message,link);
}
</script>'''.replace('SESSION_ID', json.dumps(config['session_id']))
            self.reply(200, html.replace('</body>', script + '</body>'))
            return
        if path.startswith('/completed-api/'):
            try:
                config = self.credentials()
                target = path[len('/completed-api'):]
                session = '/api/sessions/' + config['session_id']
                if target != '/ready' and target != session and not target.startswith(session + '/'):
                    self.reply(403, 'Only the completed test can be read here.')
                    return
                if any(part in ('.', '..') for part in target.split('/')):
                    self.reply(403, 'Invalid read path.')
                    return
                request = Request(self.server.api + target + ('?' + route.query if route.query else ''),
                                  headers={'Authorization': 'Bearer ' + config['owner_token']})
                try:
                    response = OPENER.open(request, timeout=15)
                except HTTPError as error:
                    response = error
                with response:
                    self.reply(response.status, response.read(), response.headers.get('Content-Type', 'application/json'))
            except (OSError, ValueError, KeyError):
                self.reply(503, '{"error":{"code":"demo_unavailable","message":"Start Open Tutor Demo.cmd or use the saved showcase."}}', 'application/json')
            return
        if path.startswith('/showcase/'):
            base = self.server.root / 'evidence/raw/Jarvaids-showcase-20261027'
            name = path[len('/showcase/'):]
        elif path.startswith(('/client/', '/server/', '/design-system/')):
            base, name = self.server.root / 'app', path.lstrip('/')
        else:
            self.reply(404, 'Not found.')
            return
        file = safe_file(base, name)
        if file is None:
            self.reply(404, 'Not found.')
            return
        content_type = 'text/javascript' if file.suffix == '.mjs' else mimetypes.guess_type(file)[0] or 'application/octet-stream'
        self.reply(200, file.read_bytes(), content_type)

    def do_POST(self):
        if self.boundary():
            self.close_connection = True
            self.reply(405, 'The completed-test link is read-only. Use the fresh tool for a new meeting.')

    do_PUT = do_POST
    do_PATCH = do_POST
    do_DELETE = do_POST


def available(url):
    try:
        with OPENER.open(url, timeout=2) as response:
            return response.status == 200
    except (OSError, ValueError):
        return False


def open_tabs():
    for url in LINKS:
        webbrowser.open_new_tab(url)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    if available(f'http://127.0.0.1:{PORT}/tutor-health'):
        if not args.no_browser:
            open_tabs()
        return
    data = ROOT / '.local/tutor-demo'
    data.mkdir(parents=True, exist_ok=True)
    child, stream = None, None
    try:
        if not (available(API + '/ready') and available(CLIENT + '/client/')):
            for port in (3000, 5173):
                with socket.socket() as probe:
                    if probe.connect_ex(('127.0.0.1', port)) == 0:
                        raise SystemExit('A partly running localhost instance occupies a required port. '
                                         'Close its launcher, then run Open Tutor Demo.cmd again.')
            stream = (data / 'services.log').open('w', encoding='utf-8')
            options = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
            child = subprocess.Popen([sys.executable, '-u', str(ROOT / 'tools/local_test.py'), 'start',
                                      '--language', 'en', '--summary-ai', 'claude', '--no-browser'],
                                     cwd=ROOT, stdout=stream, stderr=stream, **options)
            deadline = time.monotonic() + 90
            while not (available(API + '/ready') and available(CLIENT + '/client/')):
                if child.poll() is not None or time.monotonic() >= deadline:
                    raise SystemExit(f'Startup failed. See {data / "services.log"}')
                time.sleep(.2)
        with DemoServer(('127.0.0.1', PORT)) as server:
            print('Tutor demo ready. Keep this launcher running.', flush=True)
            for url in LINKS:
                print(url, flush=True)
            if not args.no_browser:
                open_tabs()
            server.serve_forever(poll_interval=.2)
    except KeyboardInterrupt:
        pass
    finally:
        if child is not None and child.poll() is None:
            if os.name == 'nt':
                subprocess.run(['taskkill', '/PID', str(child.pid), '/T', '/F'],
                               creationflags=subprocess.CREATE_NO_WINDOW, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                child.terminate()
            child.wait(timeout=10)
        if stream:
            stream.close()


if __name__ == '__main__':
    main()
