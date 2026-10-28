#!/usr/bin/env bash
# Bring the demo up from cold: backend on 3000, static client on 5173 if one
# exists, then seed one active session over HTTP and print what the presenter
# needs. Nothing under app/ is written to; the only thing this script creates is
# a fresh directory under .local/demo/.
#
# Why a script and not a list of commands in the runbook: the demo is live in
# front of a room, and a typed command is a chance to typo a port or forget the
# data directory. One command that either prints a URL or prints why it cannot
# is the whole point.
set -euo pipefail

SERVER_PORT=3000
CLIENT_PORT=5173
CLIENT_URL="http://127.0.0.1:${CLIENT_PORT}/client/"
SERVER_URL="http://127.0.0.1:${SERVER_PORT}"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${HERE}/../../.." && pwd)"
STAMP="$(date +%Y%m%d-%H%M%S)"
DATA_DIR="${ROOT}/.local/demo/${STAMP}"

# curl and urllib must not be sent through an HTTP proxy to reach loopback. Some
# machines set http_proxy globally; a proxied 127.0.0.1 request fails in a way
# that reads like the server is down, which is the worst thing to debug live.
export no_proxy="127.0.0.1,localhost,::1${no_proxy:+,${no_proxy}}"
export NO_PROXY="${no_proxy}"
CURL=(curl --silent --show-error --noproxy '*' --max-time 5)

say() { printf '%s\n' "$*"; }
fail() { printf 'start.sh: %s\n' "$*" >&2; exit 1; }

# --- 1. clear the ports -----------------------------------------------------
# Only our own processes are killed. A listener that is not ours is somebody's
# editor or another project, and killing it on a shared laptop minutes before a
# demo is worse than stopping with a message the presenter can act on.
listeners() {
  if command -v lsof >/dev/null 2>&1; then
    lsof -ti "tcp:$1" -sTCP:LISTEN 2>/dev/null || true
  elif command -v fuser >/dev/null 2>&1; then
    fuser "$1/tcp" 2>/dev/null | tr -s ' ' '\n' | sed '/^$/d' || true
  fi
}

reclaim_port() {
  local port="$1" pattern="$2" pid cmdline
  for pid in $(listeners "${port}"); do
    cmdline="$(tr '\0' ' ' < "/proc/${pid}/cmdline" 2>/dev/null || true)"
    if printf '%s' "${cmdline}" | grep -q "${pattern}"; then
      kill "${pid}" 2>/dev/null || true
      say "  reclaimed port ${port} from pid ${pid}"
    else
      fail "port ${port} is held by pid ${pid} (${cmdline:-unknown}), which this script did not start. Stop it yourself, then run start.sh again."
    fi
  done
  # Give a killed process a moment to release the socket before rebinding.
  local waited=0
  while [ -n "$(listeners "${port}")" ] && [ "${waited}" -lt 50 ]; do
    sleep 0.1
    waited=$((waited + 1))
  done
  [ -z "$(listeners "${port}")" ] || fail "port ${port} did not free up."
}

say "Jarvaids demo, cold start"
say "-----------------------"
reclaim_port "${SERVER_PORT}" 'genai_server'
reclaim_port "${CLIENT_PORT}" 'serve\.py'

# --- 2. fresh data directory ------------------------------------------------
# A new directory per run is what makes this idempotent: run it twice and the
# second run is as clean as the first, with a different session id, rather than
# rehearsing against yesterday's half-closed session.
mkdir -p "${DATA_DIR}"
# .local is not in the repository's ignore file, and adding it there would mean
# editing a tracked file outside this folder. An ignore file inside .local keeps
# the demo's scratch data out of git status without touching anything tracked.
printf '*\n' > "${ROOT}/.local/.gitignore"
say "  data directory ${DATA_DIR#"${ROOT}/"}"

# --- 3. backend -------------------------------------------------------------
(
  cd "${ROOT}/app/server"
  nohup python3 -m genai_server \
    --port "${SERVER_PORT}" \
    --data-dir "${DATA_DIR}" \
    --allow-origin "${CLIENT_URL%/client/}" \
    > "${DATA_DIR}/server.log" 2>&1 &
  printf '%s\n' "$!" > "${DATA_DIR}/server.pid"
)
SERVER_PID="$(cat "${DATA_DIR}/server.pid")"

wait_for() {
  local url="$1" label="$2" tries=0
  until "${CURL[@]}" --output /dev/null "${url}" 2>/dev/null; do
    tries=$((tries + 1))
    [ "${tries}" -lt 100 ] || fail "${label} did not answer at ${url}. See ${DATA_DIR}/server.log"
    sleep 0.2
  done
}
wait_for "${SERVER_URL}/health" "backend"
say "  backend up on ${SERVER_URL} (pid ${SERVER_PID})"

# --- 4. static client -------------------------------------------------------
# app/client/serve.py serves the repository's app/ directory on 5173 so the
# browser has an origin the backend was told to accept. The else branch stays
# because a checkout without the client (an older branch, a partial copy) must
# say so plainly: a runbook that silently assumes a URL is how a demo dies in
# front of a room.
CLIENT_PID=""
if [ -f "${ROOT}/app/client/serve.py" ]; then
  (
    cd "${ROOT}/app/client"
    nohup python3 serve.py --port "${CLIENT_PORT}" \
      > "${DATA_DIR}/client.log" 2>&1 &
    printf '%s\n' "$!" > "${DATA_DIR}/client.pid"
  )
  CLIENT_PID="$(cat "${DATA_DIR}/client.pid")"
  wait_for "http://127.0.0.1:${CLIENT_PORT}/" "client"
  say "  client up on ${CLIENT_URL} (pid ${CLIENT_PID})"
else
  say "  client NOT started: app/client/serve.py does not exist on this branch."
fi

# --- 5. seed one active session --------------------------------------------
# Command shapes follow app/server/API.md and app/server/demo.py: activation
# needs the session revision it saw, and an invitation needs the roster
# revision, so each one reads the snapshot immediately before it writes.
SEED_JSON="${DATA_DIR}/seed.json"
python3 - "${SERVER_URL}" "${SEED_JSON}" <<'PY'
import json, secrets, sys
from urllib.error import HTTPError
from urllib.request import Request, ProxyHandler, build_opener

base, out = sys.argv[1], sys.argv[2]
opener = build_opener(ProxyHandler({}))
token, sid = secrets.token_urlsafe(32), secrets.token_hex(16)
prefix = f'/api/sessions/{sid}'

def call(method, path, body=None, key=None):
    headers = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}
    if key:
        headers['X-Request-ID'] = key
    data = json.dumps(body).encode() if body is not None else None
    request = Request(base + path, data=data, headers=headers, method=method)
    try:
        with opener.open(request, timeout=10) as response:
            return json.loads(response.read())
    except HTTPError as error:
        payload = json.loads(error.read())
        raise SystemExit('seeding failed at %s %s: %s' % (method, path, payload['error']['code']))

def command(operation, payload):
    return call('POST', prefix + '/commands', {'operation': operation, 'payload': payload},
                secrets.token_hex(16))

health = call('GET', '/health')
assert health['adapter'] == 'fixture' and not health['live_ocr'], 'expected the fixture adapter'

call('POST', '/api/sessions', {'session_id': sid, 'owner_token': token,
                               'owner_name': 'Facilitator', 'title': 'Wall review'})
command('consent.acknowledge', {'policy_version': 1})
command('session.activate', {'policy_version': 1,
                             'expected_session_revision': call('GET', prefix)['session']['revision']})
invitation = secrets.token_urlsafe(32)
invited = command('participant.invite', {
    'invitation': invitation, 'role': 'participant', 'expires_seconds': 3600,
    'expected_roster_revision': call('GET', prefix)['session']['roster_revision']})['result']

session = call('GET', prefix)['session']
assert session['state'] == 'active', 'seeded session is %s, not active' % session['state']
with open(out, 'w') as handle:
    json.dump({'session_id': sid, 'owner_token': token, 'invitation': invitation,
               'invitation_id': invited.get('id') or invited.get('invitation_id'),
               'state': session['state'], 'adapter': health['adapter']}, handle, indent=2)
PY

SESSION_ID="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["session_id"])' "${SEED_JSON}")"
OWNER_TOKEN="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["owner_token"])' "${SEED_JSON}")"
INVITATION="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["invitation"])' "${SEED_JSON}")"

say ""
say "Ready."
say "  client URL        ${CLIENT_URL}"
if [ -z "${CLIENT_PID}" ]; then
  say "                    (not serving yet: no app/client/serve.py on this branch)"
fi
say "  backend           ${SERVER_URL}   health: ${SERVER_URL}/health"
say "  session id        ${SESSION_ID}"
say "  session title     Wall review   owner: Facilitator   state: active"
say "  owner token       ${OWNER_TOKEN}"
say "  invitation        ${INVITATION}"
say "  adapter           fixture, live_ocr false. Readings are stand-ins."
say ""
say "How the presenter enters the session:"
if [ -n "${CLIENT_PID}" ]; then
  say "  Open the client URL and press its own Start button, live, so the room sees"
  say "  the session being made. Nothing is pasted. The seeded session above is only"
  say "  the proof that the backend answers, and is what step.sh drives if the browser dies."
else
  say "  There is no browser client on this branch, so nobody enters anything yet."
  say "  What is above is a real, active, seeded session on the real backend."
  say "  RUNBOOK.md says what can and cannot be shown until the client lands."
fi
say ""
say "  stop everything:  bash ${HERE#"${ROOT}/"}/stop.sh"
say "  logs:             ${DATA_DIR#"${ROOT}/"}/server.log"
