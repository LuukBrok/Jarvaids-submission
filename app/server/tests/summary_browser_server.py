"""Local HTTP/store journey with an explicitly scripted summary adapter."""
import argparse
from pathlib import Path
import threading
from genai_server.service import Service
from genai_server.http import LocalServer
from tests.test_summaries import ScriptedSummary

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--data-dir', type=Path, required=True)
    parser.add_argument('--origin', required=True)
    args = parser.parse_args()
    service = Service(args.data_dir / 'summary.sqlite3', automatic_workspace=True, summary_model=ScriptedSummary())
    server = LocalServer(('127.0.0.1', args.port), service, [args.origin])
    stop = threading.Event()
    def worker():
        while not stop.is_set():
            service.run_one_summary_job(); stop.wait(.05)
    thread = threading.Thread(target=worker, daemon=True); thread.start()
    try: server.serve_forever(poll_interval=.1)
    finally: stop.set(); server.server_close(); thread.join(1)
