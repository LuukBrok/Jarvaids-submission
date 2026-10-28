#!/usr/bin/env bash
# Drive one demo step against the session start.sh seeded. Usage: step.sh 1..5
#
# One command per step, and the step number is the only thing the presenter has
# to remember. The output is printed wide and plainly because it is read from
# the back of a room, not scrolled through.
#
# Nothing under app/ is written to. State between steps lives in the run's own
# data directory next to the seed.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${HERE}/../../.." && pwd)"
export no_proxy="127.0.0.1,localhost,::1${no_proxy:+,${no_proxy}}"
export NO_PROXY="${no_proxy}"

STEP="${1:-}"
case "${STEP}" in
  1|2|3|4|5) ;;
  *) printf 'usage: step.sh <1..5>   (run start.sh first)\n' >&2; exit 2 ;;
esac

SEED="$(ls -1dt "${ROOT}"/.local/demo/*/seed.json 2>/dev/null | head -1 || true)"
[ -n "${SEED}" ] || { printf 'step.sh: no seeded session. Run start.sh first.\n' >&2; exit 1; }

python3 - "${SEED}" "${STEP}" <<'PY'
import base64, json, os, secrets, struct, sys, time, zlib
from urllib.error import HTTPError
from urllib.request import Request, ProxyHandler, build_opener

seed_path, step = sys.argv[1], int(sys.argv[2])
seed = json.load(open(seed_path))
state_path = os.path.join(os.path.dirname(seed_path), 'state.json')
state = json.load(open(state_path)) if os.path.exists(state_path) else {}

base = 'http://127.0.0.1:3000'
opener = build_opener(ProxyHandler({}))
token, sid = seed['owner_token'], seed['session_id']
prefix = '/api/sessions/' + sid

def call(method, path, body=None, key=None):
    headers = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}
    if key:
        headers['X-Request-ID'] = key
    data = json.dumps(body).encode() if body is not None else None
    try:
        with opener.open(Request(base + path, data=data, headers=headers, method=method), timeout=10) as r:
            return json.loads(r.read())
    except HTTPError as error:
        payload = json.loads(error.read())
        raise SystemExit('step %d failed at %s %s: %s' % (step, method, path, payload['error']['code']))

def command(operation, payload):
    return call('POST', prefix + '/commands', {'operation': operation, 'payload': payload},
                secrets.token_hex(16))['result']

def need(key):
    if key not in state:
        raise SystemExit('step %d needs step %d to have run first.' % (step, {'source': 2, 'job': 3, 'proposal': 3, 'item': 4}.get(key, step - 1)))
    return state[key]

def show(label, value):
    print('  %-22s %s' % (label, value))

def png(width, height, rgb):
    """A tiny valid PNG, built here so the demo needs no image file on disk."""
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    raw = b''.join(b'\x00' + bytes(rgb) * width for _ in range(height))
    return (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))

if step == 1:
    print('Step 1: a typed note reaches the board.')
    text = os.environ.get('NOTE', 'Onboarding is the real bottleneck')
    result = command('source.text', {'text': text})
    state['typed_proposal'] = {'id': result['proposal']['id'], 'revision': result['proposal']['revision']}
    show('typed', text)
    show('source record', '%s rev %s' % (result['source']['id'], result['source']['revision']))
    show('proposal record', '%s rev %s' % (result['proposal']['id'], result['proposal']['revision']))
    show('proposal state', result['proposal']['data'].get('state', 'pending'))
    print('  The note and the claim about it are two records. Nothing is on the board yet.')

elif step == 2:
    print('Step 2: the wall is photographed.')
    image = png(64, 48, (245, 222, 120))
    result = command('source.image', {'mime': 'image/png', 'base64': base64.b64encode(image).decode(),
                                      'regions': [{'id': 'yellow_note_1', 'box': [0.05, 0.05, 0.4, 0.4]},
                                                  {'id': 'yellow_note_2', 'box': [0.5, 0.5, 0.4, 0.4]}]})
    state['source'] = {'id': result['id'], 'revision': result['revision']}
    show('source record', '%s rev %s' % (result['id'], result['revision']))
    show('sanitised size', '%sx%s' % (result['data'].get('width'), result['data'].get('height')))
    show('regions marked', len(result['data'].get('regions', [])))
    show('original bytes kept', 'no, re-encoded as clean pixels')

elif step == 3:
    print('Step 3: the reading comes back.')
    source = need('source')
    job = command('extraction.queue', {'source_id': source['id'], 'expected_revision': source['revision']})
    show('job', '%s %s' % (job['id'], job['data']['status']))
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        current = call('GET', prefix + '/records/' + job['id'])
        if current['data']['status'] not in ('queued', 'running'):
            break
        time.sleep(0.15)
    show('job finished', current['data']['status'])
    if current['data']['status'] != 'succeeded':
        raise SystemExit('extraction did not succeed; switch to the fallback window.')
    first = call('GET', prefix + '/records/' + current['data']['proposal_ids'][0])
    state['proposal'] = {'id': first['id'], 'revision': first['revision']}
    print()
    show('reading', first['data']['text'])
    show('synthetic', first['data'].get('synthetic'))
    show('origin', first['data'].get('origin'))
    print()
    print('  SAY NOW, ONCE:')
    print('  "The reading you are seeing is a stand-in; no handwriting recognition has run')
    print('   yet. The flow around it is real and is what we are showing."')

elif step == 4:
    print('Step 4: a person accepts it.')
    proposal = need('proposal')
    result = command('proposal.review', {'proposal_id': proposal['id'],
                                         'expected_revision': proposal['revision'], 'decision': 'accept'})
    item = result['item']
    state['item'] = {'id': item['id'], 'revision': item['revision']}
    show('proposal now', result['proposal']['data'].get('state', 'accepted'))
    show('item created', '%s rev %s' % (item['id'], item['revision']))
    show('item text', item['data']['text'])
    show('refs back to source', json.dumps(item['data'].get('refs')))
    print('  Acceptance is the only thing that moved it across, and the claim is still on file.')

elif step == 5:
    print('Step 5: the item is moved, and the board is exported.')
    item = need('item')
    placed = command('item.place', {'placements': [
        {'id': item['id'], 'x': 320, 'y': 180, 'expected_position_revision': 0}]})['placements'][0]
    after = call('GET', prefix + '/records/' + item['id'])
    show('moved to', '%s, %s' % (placed['x'], placed['y']))
    show('position revision', '0 -> %s' % placed['revision'])
    show('content revision', '%s, unchanged' % after['revision'])
    show('hand placed', placed.get('hand_placed'))
    export = command('export.create', {'include_unresolved': True})
    show('export', export['id'])
    show('unresolved in export', export['data']['manifest']['unresolved_count'])
    print('  Where it is and what it means are separate revisions, on purpose.')

json.dump(state, open(state_path, 'w'), indent=2)
PY
