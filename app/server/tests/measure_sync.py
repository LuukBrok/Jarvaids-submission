#!/usr/bin/env python3
"""What does one acceptance cost each connected client?

Chunk C set a budget: accepting a proposal moves under 5 KB to each connected
client. The number it replaced was a measurement of the old behaviour, 427 KB at
the record ceiling, because events named no records and a client had no way to
refetch anything smaller than the whole session.

This measures the budget the way C06 asks: event plus the refetch it forces, for
one named fixture, with compressed and uncompressed bytes reported separately.

    python3 tests/measure_sync.py

It goes over real HTTP against a real server, so the numbers include headers and
framing. What it does NOT measure: a remote network, more than one machine, or
any client's rendering. Latency here is loopback on one box and is reported only
to show the transport is not the constraint; do not quote it as a user-facing
number.

The fixture is named so the number can be reproduced and argued with:

    WALL-12   a wall of 12 typed notes, each accepted, plus one relationship
              item over two of them, then one more proposal accepted while
              seven clients hold cursors. Roughly a quarter of the record cap.

    CEILING   the same shape at the 1000-record cap (320 notes, three records
              each), which is where the
              427 KB figure came from.
"""
import gzip
import http.client
import json
import secrets
import statistics
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from genai_server.http import LocalServer
from genai_server.service import Service

CLIENTS = 7


class Client:
    """One connection, kept open, reporting the bytes it moved."""

    def __init__(self, port, sid, token):
        self.conn = http.client.HTTPConnection('127.0.0.1', port, timeout=30)
        self.sid, self.token, self.received = sid, token, 0

    def call(self, method, path, body=None, gzipped=True):
        headers = {'Content-Type': 'application/json', 'X-Request-ID': secrets.token_hex(16),
                   'Authorization': 'Bearer ' + self.token,
                   'Accept-Encoding': 'gzip' if gzipped else 'identity'}
        self.conn.request(method, path, None if body is None else json.dumps(body), headers)
        response = self.conn.getresponse()
        raw = response.read()
        # Header bytes count: they are on the wire whether or not we like it.
        head = sum(len(k) + len(v) + 4 for k, v in response.getheaders()) + 17
        self.received += len(raw) + head
        if response.getheader('Content-Encoding') == 'gzip':
            raw = gzip.decompress(raw)
        return response.status, json.loads(raw) if raw else None

    def cmd(self, op, payload=None):
        payload=dict(payload or {})
        if op=='session.activate':
            snapshot=self.call('GET',f'/api/sessions/{self.sid}')[-1]
            payload['expected_session_revision']=snapshot['session']['revision']
        status, body = self.call('POST', f'/api/sessions/{self.sid}/commands',
                                 {'operation': op, 'payload': payload or {}})
        if status != 200:
            raise RuntimeError('%s failed: %s' % (op, body))
        return body['result']


def build(client, notes):
    """The fixture. Returns the proposal that will be accepted while measured."""
    version = client.call('GET', f'/api/sessions/{client.sid}')[1]['session']['policy_version']
    client.cmd('consent.acknowledge', {'policy_version': version})
    client.cmd('session.activate', {'policy_version': version})
    items = []
    for index in range(notes):
        proposal = client.cmd('source.text', {'text': 'Wall note %d, about the onboarding flow' % index})['proposal']
        items.append(client.cmd('proposal.review', {'proposal_id': proposal['id'],
                                                    'expected_revision': proposal['revision'],
                                                    'decision': 'accept'})['item'])
    relationship = client.cmd('proposal.create', {
        'proposal_kind': 'relationship', 'text': 'These two are the same complaint',
        'refs': [{'id': i['id'], 'revision': i['revision']} for i in items[:2]]})
    client.cmd('proposal.review', {'proposal_id': relationship['id'],
                                   'expected_revision': relationship['revision'], 'decision': 'accept'})
    return client.cmd('source.text', {'text': 'The note whose acceptance is being measured'})['proposal']


def measure(name, notes, port, service, positioned=False):
    sid, token = secrets.token_hex(16), secrets.token_urlsafe(32)
    service.create_session({'session_id': sid, 'title': name, 'owner_name': 'Facilitator',
                            'owner_token': token})
    author = Client(port, sid, token)
    proposal = build(author, notes)
    if positioned:
        items=[r for r in service.snapshot(sid,token)['records'] if r['kind']=='item']
        for offset in range(0,len(items),60):
            author.cmd('item.place',{'placements':[{'id':r['id'],'x':index*10,'y':20,'expected_position_revision':0}
                for index,r in enumerate(items[offset:offset+60],offset)]})

    watchers = [Client(port, sid, token) for _ in range(CLIENTS)]
    cursors = []
    for watcher in watchers:
        cursors.append(watcher.call('GET', f'/api/sessions/{sid}/events?after=0')[1]['current_seq'])
        watcher.received = 0

    start = time.monotonic()
    author.cmd('proposal.review', {'proposal_id': proposal['id'],
                                   'expected_revision': proposal['revision'], 'decision': 'accept'})
    commit = time.monotonic() - start

    # What each client does on waking: read the events it has not seen, then
    # refetch exactly the records those events named.
    latencies, cascade = [], 0
    for watcher, cursor in zip(watchers, cursors):
        began = time.monotonic()
        events = watcher.call('GET', f'/api/sessions/{sid}/events?after={cursor}')[1]['events']
        delta = watcher.call('GET', f'/api/sessions/{sid}?since_seq={cursor}')[1]
        latencies.append(time.monotonic() - began)
        cascade = max(cascade, sum(len(e['data']['records']) for e in events))
        assert delta['current_seq'] > cursor

    plain = Client(port, sid, token)
    plain.call('GET', f'/api/sessions/{sid}/events?after=0', gzipped=False)
    plain.received = 0
    plain.call('GET', f'/api/sessions/{sid}', gzipped=False)
    full = plain.received

    uncompressed = Client(port, sid, token)
    uncompressed.received = 0
    uncompressed.call('GET', f'/api/sessions/{sid}/events?after={cursors[0]}', gzipped=False)
    uncompressed.call('GET', f'/api/sessions/{sid}?since_seq={cursors[0]}', gzipped=False)

    records = len(service.snapshot(sid, token)['records'])
    return {'fixture': name, 'records': records, 'recipients': len(watchers),
            'cascade': cascade, 'per_client_gzip': statistics.mean(w.received for w in watchers),
            'per_client_plain': uncompressed.received, 'full_reload_plain': full,
            'commit_ms': commit * 1000, 'p95_ms': max(latencies) * 1000}


def main():
    root=Path(__file__).resolve().parents[1]/'.local'/'tests';root.mkdir(parents=True,exist_ok=True)
    directory = root / secrets.token_hex(16);directory.mkdir()
    service = Service(directory / 'state.sqlite3')
    server = LocalServer(('127.0.0.1', 0), service)
    port = server.server_port
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        # POSITIONED runs by default and CEILING is the optional one, which is
        # the opposite of how this started. A board where nothing has been
        # placed is not a board, and gating the realistic fixture behind a flag
        # is how the delta grew to 8183 B per client without anyone noticing.
        rows = [measure('WALL-12', 12, port, service),
                measure('POSITIONED', 320, port, service, positioned=True)]
        if '--ceiling' in sys.argv:
            rows.append(measure('CEILING', 320, port, service))
    finally:
        server.shutdown()

    print('%-9s %8s %6s %8s %11s %11s %12s' %
          ('fixture', 'records', 'recip', 'cascade', 'gzip/client', 'plain/client', 'full reload'))
    for row in rows:
        print('%-9s %8d %6d %8d %10.0f B %10.0f B %10.0f B' %
              (row['fixture'], row['records'], row['recipients'], row['cascade'],
               row['per_client_gzip'], row['per_client_plain'], row['full_reload_plain']))
    print()
    for row in rows:
        verdict = 'under' if row['per_client_gzip'] < 5120 else 'OVER'
        print('%-9s %s the 5 KB budget at %.0f B compressed per client. '
              'Commit %.0f ms, slowest client %.0f ms, loopback, one machine.'
              % (row['fixture'], verdict, row['per_client_gzip'], row['commit_ms'], row['p95_ms']))
    print('\nLatency is loopback on one box and says only that transport is not '
          'the constraint. It is not a user-facing number.')
    return 0 if all(r['per_client_gzip'] < 5120 for r in rows) else 1


if __name__ == '__main__':
    sys.exit(main())

