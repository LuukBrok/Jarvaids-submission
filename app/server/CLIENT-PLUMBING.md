# Client plumbing, 16 September 2026

Integrated with main `51bae3b10bd8deefcbf0625ccce52dc2f88755e1`, including
the new derived board ordering and cascade resynchronisation contract. The shared
mutation runner now handles both Python assertions and named Node TAP assertions;
CI runs the client unit/mutation/HTTP checks and the previously omitted schema
and runtime guard harnesses.
The publishing pull request records the exact candidate and merged-tree readback.
This package supplies executable browser/Node logic without a UI or new dependency.

## Transport contract

`client.mjs` preserves the existing call signatures and adds a trailing
`{signal, timeoutMs}` option to requests. The default total deadline is 10 seconds,
including response decoding; overrides are integer milliseconds from 1 to 120000.
Constructor `fetchImpl` permits deterministic connection-failure testing.

- `intent(operation, payload, {controlSequence})` freezes the serialised command,
  request ID and origin/session/client ownership. Submit the original object to
  the same client. Payload edits cannot change a retry. No automatic write retry,
  request-ID replacement or revision rebase occurs.
- A pre-aborted request never dispatches. An in-flight timeout, cancellation,
  network failure or unreadable write response has `outcome: "unknown"`.
  `not_sent` describes a request prevented locally. `response_received` means a
  readable response was observed, not that an earlier uncertain attempt failed.
  `ApiError` retains status/code/details. `RequestError` uses fixed messages that
  do not expose network exception text or credentials.
- Read failures before headers are also unknown. Read-only snapshot export does
  not become an uncertain mutation merely because its HTTP verb is POST.
  Server 5xx writes and expired control replay remain uncertain.
- Authenticated 401 revokes the client, including when its error body stalls.
  Session expiry/deletion and a successful facilitator deletion receipt also
  terminate it. Invalid invitation 401 and missing-media 410 do not revoke it.
- `onState(listener)` observes terminal changes, returns an unsubscribe function
  and does not fire immediately. Terminal states clear the private token, abort
  peer requests, revoke owned URLs and refuse future requests and intents.
  Late responses cannot repopulate the client. `dispose()` is idempotent.
- `createMediaUrl(blob)` tracks at most 16 URLs; `revokeMediaUrl(url)` releases
  capacity. Disposal/revocation clears these URLs. Caller-held Blob objects,
  downloaded exports, copied snapshots and already-dispatched request bodies
  cannot be erased by this library.
- `readiness()` returns the 503 not-ready body for display, without credentials.
  `diagnostics()` uses current facilitator authority. The future UI must keep
  null observations and truncated attention lists explicit.

Creation and joining are explicit calls rather than queued commands. If their
acknowledgement is lost, retain the same client credentials, session ID and exact
fields for a deliberate retry. Never generate a new device token as an automatic
recovery action. Credentials, invitations and intents are memory-only. There is
no persistent outbox, reload recovery, name-based identity reset or storage of
source material in browser storage.

## Session connection

`session-sync.mjs` exports `SessionConnection` and `ConnectionError`.

```js
const connection = new SessionConnection(client, {
  onUpdate: snapshot => renderSession(snapshot),
  onAttention: event => showAttention(event),
});
await connection.start();
// Enable only after the facilitator explicitly chooses to keep capture alive.
connection.enableHeartbeat();
// A user stop action awaits the server acknowledgement before showing paused.
await connection.pause();
```

The rendering callbacks above are application hooks, not implemented UI functions.
The host must forward actual `visibilitychange`, `online` and `offline` events
with `setVisibility(!document.hidden)` and `setOnline(navigator.onLine)`, including
initial values before starting. Browser online state is advisory; failed requests
still back off. Remove host listeners during teardown, then dispose both the
connection and the client. Connection disposal does not dispose a shared client.

| Behaviour | Contract and reason |
| --- | --- |
| Polling | Default one second, no overlapping current reads; exponential jittered retry bounded at 30 seconds. Cursor advances only after applying a complete validated response. Invalid/future cursors and reconnect request a full snapshot. |
| Cache | Defaults to 1000 records and 16 MiB of UTF-8 JSON. Changed records and board ordering derived from their positions are applied together. Full snapshots replace the cache; oversized or partial responses leave the last good state and surface attention. Copies returned to callers cannot mutate internal state. |
| Timer limits | Polling minimum 100 ms and heartbeat minimum one second; maximum configured timers five minutes. Request deadlines additionally match the transport's 120-second integer bound. These are protective limits, not measured capacity recommendations. |
| Heartbeat | Default 30 seconds, explicitly enabled only for a confirmed active facilitator. Hidden, offline, stopped, demoted or failed sync disables it. Returning to the foreground never re-enables it automatically. No heartbeat activates capture. |
| Control lane | One in-flight control, no backlog. Pause, close, heartbeat, removal, withdrawal and invitation revocation share the current actor sequence. Ordinary commands use retained client intents directly. |
| Uncertain control | Retains the original intent and blocks new controls/automatic heartbeat. `retryPendingControl()` explicitly resends it. `pendingControl` exposes the retained operation and intent. A conflict requests a fresh snapshot and renewed intent; it never silently rebases. |
| Explicit pause | Disables heartbeat immediately. It may supersede an uncertain heartbeat after a fresh snapshot, preserving the displaced intent in an attention event. Raced sequences surface a failure, never false success. Other uncertain controls require explicit reconciliation. |
| Local stop | `stop()` cancels local work and ignores late responses. It does not promise server pause or roll back an in-flight write. A server lease can remain live until explicit pause or expiry. |
| Revocation | Terminal client notifications stop polling and clear the connection's cache and pending control. Caller-held snapshot copies remain the caller's responsibility. |

`discardPendingControl()` explicitly returns the unresolved intent and requires
fresh state before another control. Discarding is not evidence that the action
failed. It should be offered only with an explanation in the eventual UI.

## Executable evidence

Validation results are recorded after the final source freeze below. Tests use
synthetic content only. Node tests run with `--test-isolation=none` because this
Windows sandbox denies the test runner's child-process spawn with EPERM; the
modules are tested in process and the real backend runs as a separate CLI process.

```sh
node --test --test-isolation=none tests/client-transport-unit.mjs tests/session-sync-unit.mjs
python tests/client_mutation_check.py
python tests/client_http_check.py
```

The real HTTP journey creates two independent clients, checks derived board
ordering after a move and full resynchronisation, loses an acknowledgement
only after reading the server's committed response, retries the same intent,
reconnects a participant, replays a control, pauses and observes removal revocation.
This establishes protocol behaviour. It is not a physical network-loss, browser
background-throttling or real-phone test.

## Remaining acceptance work

- Build the first browser workflow: independent join/agreement, typed capture,
  provisional review, pause, export and deletion. Bind attention states to clear
  retry/reconciliation choices and preserve unsent edits on conflicts.
- Decide reload credential handling and any persistent outbox separately, with
  retention, device loss and explicit recovery expectations. Current reload loses
  in-memory credentials and unresolved intents.
- Exercise real phone, shared display, cross-origin requests, backgrounding,
  screen lock, Wi-Fi interruption and visible lease expiry. Node fetch does not
  enforce browser CORS and mocks do not demonstrate browser timer behaviour.
- Preserve the integrated INT13 derived ordering and cascade resync fixtures
  when changing server cursor semantics. Large cascades take a fresh snapshot;
  incomplete responses never advance the saved cursor.
- Measure large-session memory, convergence latency and mobile energy use. Cache
  limits are deliberate defaults, not calibrated device budgets. Responses are
  decoded before cache validation; this is not a streaming response-size limit.
- Keep live-provider deadlines, idempotency, spending caps and reconciliation open.
  All extraction remains synthetic; no model selection is needed for this layer.

## Final integrated candidate results

Windows, Python 3.14, Pillow 12.0.0 and Node 24.11.1. Tested against the complete
backend sources from PR18/main `51bae3b10bd8deefcbf0625ccce52dc2f88755e1`
plus this client package; the PR identifies the published commit. Historical
results in earlier status documents are not additional tests in these totals.

| Check | Observed result |
| --- | --- |
| Backend suite | 237 tests passed in 70.105 seconds |
| Client unit suites | 38 tests passed: 16 transport and 22 connection tests |
| Legacy client unit check | Passed, including LAN crypto and origin validation |
| Python named guards | 98 caught: 59 service, 12 schema, 8 isolation, 9 media, 10 runtime |
| JavaScript named guards | 45 caught by their specified assertion test; collection, syntax and runner timeout failures do not count |
| Actual CLI and HTTP journeys | Demo, original client journey and two-client plumbing journey all passed |
| Sync budget | WALL-12 1647 B and POSITIONED 1662 B compressed per client, seven loopback clients; both under 5 KB |
| Schema registry | Versions 1 through 5 agree with the migration chain |
| Contrast | 105 pairs across four schemes passed against current main tokens/checker |
| Bash design audit | Unavailable locally: Bash is not on this Windows PATH; no passing local claim |
| Browser/device/Swift | Not verified; no UI was added and the Swift core remains uncompiled |

The workflow now runs the new client checks on Node 24 and the existing backend
matrix, including schema/runtime guard harnesses. A workflow definition is not
proof of its remote result; check the publishing PR's actual run status.
