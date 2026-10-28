#!/usr/bin/env python3
"""Upload several large images at once and report peak resident memory.

A subprocess so the figure is this work's peak and not the test suite's. Prints
one line of JSON on stdout.

The question is whether anything holds every image in memory at the same time:
intake decodes, sanitises and stores, and doing that for four 4 MiB uploads
concurrently is the shape a room photographing a wall produces.
"""
import base64
import concurrent.futures
import json
import resource
import secrets
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from genai_server.service import Service
from genai_server.validation import Problem

UPLOADS = 4


def big_png(width=1100, height=1100):
    """Noise, so it does not compress away and the payload is genuinely large."""
    def chunk(kind, data):
        return (struct.pack('>I', len(data)) + kind + data
                + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff))
    raw = bytearray()
    for row in range(height):
        raw.append(0)
        raw.extend(secrets.token_bytes(3 * width))
    return (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(bytes(raw), 1))
            + chunk(b'IEND', b''))


def main():
    directory = Path(sys.argv[1])
    service = Service(directory / 'state.sqlite3')
    sid, token = secrets.token_hex(16), secrets.token_urlsafe(32)
    service.create_session({'session_id': sid, 'title': 'Wall', 'owner_name': 'F',
                            'owner_token': token})

    def cmd(op, payload=None):
        return service.command(sid, token, secrets.token_hex(16), op, payload or {})['result']

    version = service.snapshot(sid, token)['session']['policy_version']
    cmd('consent.acknowledge', {'policy_version': version})
    cmd('session.activate', {'policy_version': version,
                             'expected_session_revision': service.snapshot(sid, token)['session']['revision']})

    payload = base64.b64encode(big_png()).decode()
    encoded_mib = len(payload) / 1024 / 1024

    def upload(_):
        try:
            cmd('source.image', {'mime': 'image/png', 'base64': payload,
                                 'regions': [{'id': 'region_001', 'box': [0, 0, 1, 1]}]})
            return True
        except Problem:
            # A capacity refusal is a correct outcome, not a memory result.
            return False

    with concurrent.futures.ThreadPoolExecutor(max_workers=UPLOADS) as pool:
        accepted = sum(pool.map(upload, range(UPLOADS)))

    peak_kib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(json.dumps({'uploaded': accepted, 'attempted': UPLOADS,
                      'encoded_mib': round(encoded_mib, 2),
                      'peak_mib': round(peak_kib / 1024)}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
