#!/usr/bin/env python3
"""Serve the client over HTTP so a browser will talk to the backend.

Opening index.html from disk does not work, and the reason is worth knowing:
a file:// page has the origin `null`, and the backend refuses origins it was
not told about, deliberately. So the client needs an origin, which means a
server, even though it is only static files.

Two processes, on purpose. The backend serving its own client would give the
API surface a second job and a second set of paths to get wrong, for the
convenience of not opening one more terminal.

    python3 serve.py --port 5173

Then, in another terminal, tell the backend to accept this origin:

    cd ../server
    python3 -m genai_server --port 3000 --allow-origin http://127.0.0.1:5173

It serves the repository's `app/` directory rather than just this folder,
because the client imports `../server/client.mjs` and links the design
system's stylesheet. One copy of each, not three.
"""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


class Handler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        prefix = '/explorations/jarvaids-live-canvas/'
        route = urlsplit(path).path
        if route.startswith(prefix):
            name = route[len(prefix):] or 'index.html'
            if name in ('index.html', 'teammate-audio-inline.js', 'README.md'):
                return str(ROOT.parent / 'ideation/explorations/jarvaids-live-canvas' / name)
        return super().translate_path(path)

    extensions_map = {**SimpleHTTPRequestHandler.extensions_map,
                      '.mjs': 'text/javascript', '.js': 'text/javascript',
                      '.css': 'text/css', '.woff2': 'font/woff2'}

    def end_headers(self):
        # A local development server, not a host. Say so in the headers rather
        # than letting anything cache a half-built client.
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def log_message(self, *args):
        pass  # paths can carry session ids


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=5173)
    parser.add_argument('--bind', default='127.0.0.1')
    args = parser.parse_args()
    if args.bind != '127.0.0.1':
        # The backend makes the same refusal for the same reason: this is
        # unencrypted HTTP carrying meeting content.
        raise SystemExit('This server binds to 127.0.0.1 only.')
    server = ThreadingHTTPServer((args.bind, args.port), partial(Handler, directory=str(ROOT)))
    print(f'Client at http://{args.bind}:{server.server_port}/client/')
    print(f'Start the backend with: --allow-origin http://{args.bind}:{server.server_port}')
    try:
        server.serve_forever(poll_interval=.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
