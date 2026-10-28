# Combined local speech configuration

Use [LOCAL-TEST.md](../../LOCAL-TEST.md) for the reproducible live test.
The launcher selects real local Whisper Base, Dutch and two CPU threads;
plain CLI startup still defaults to synthetic fixture transcription for tests.
The fixture-only boundaries below describe that default mode.

# Jarvaids pipeline backend

An offline prototype for independent joining, capture, source evidence, provisional proposals, human review, correction, export and deletion. The extraction adapter is a labelled synthetic fixture. No OCR or paid model calls occur.

## Run

From `app/server`, using Python 3.11+ (tested on Windows with Python 3.14):

```sh
python -m pip install -r requirements.txt
python -m genai_server --port 3000 --data-dir .local --allow-origin http://localhost:5173
```

Pillow is the only third-party runtime dependency. The installed Pillow 12.0.0 was exercised offline; installation can require package access, but operation never downloads assets. No model account or key is needed. Keep `.local/` out of source control.

## Try the live transcript demo in a browser

`demo-audio.html` is a minimal harness for F1.1-F1.3 (live capture, speech to
text, speaker separation), not the product UI. It needs an actual browser and
microphone, so it will not run inside a headless session; run it on your own
machine.

```sh
# terminal 1: the API server, allowing the static page's own origin
python -m genai_server --port 3000 --data-dir .local --allow-origin http://127.0.0.1:5173

# terminal 2: the client's static server, which serves the whole app/ folder so
# the page can reach the design system's stylesheet (browsers refuse
# getUserMedia and ES module imports from file://)
python3 ../client/serve.py --port 5173
```

Then open `http://127.0.0.1:5173/server/demo-audio.html`, allow microphone access,
and speak. Open the same URL in a second tab with a different name to see a
second speaker attributed separately, per the per-connection diarisation
fallback in `decisions/decision-log.md`. `FixtureTranscriber` is the default
adapter, so text will be synthetic unless a real `LocalWhisperTranscriber` is
configured; see `genai_server/adapters.py`.

Loopback is the default. To bind explicitly on a trusted development LAN:

```sh
python -m genai_server --bind 0.0.0.0 --advertise-host 192.168.1.20 --port 3000 --allow-origin http://192.168.1.20:5173
```

Replace the example address with the server's actual address. Allowed Host values and browser origins are exact, even under wildcard binding. HTTP does not encrypt bearer credentials. Socket and Host tests are not proof of phone/firewall connectivity. Public deployment needs a supported application server, TLS, operational ownership and stronger identity infrastructure; see Python's [HTTP server documentation](https://docs.python.org/3/library/http.server.html).

## Verify

```sh
python -m unittest discover -s tests
python tests/mutation_check.py
python tests/isolated_mutation_check.py
python tests/media_mutation_check.py
python demo.py --url http://127.0.0.1:3000
node tests/client-smoke.mjs http://127.0.0.1:3000
```

The suite includes a real CLI-process HTTP journey and subprocess termination tests. Guard checkers run a clean baseline, mutate scratch copies, require the named test to fail, and refuse infrastructure errors as evidence. The original tree is never the mutation target.

## Integration

Use [API.md](API.md) and [client.mjs](client.mjs). Credentials remain in the caller's memory and never enter URLs. A lost credential has no recovery flow.

1. Create the session and acknowledge the policy.
2. A facilitator issues a single-use invitation. Each participant redeems it with a credential generated on their own device and current-policy acknowledgement.
3. Activate using the displayed session revision. Add typed material or an image with regions expressed in the oriented image coordinate space.
4. Show source evidence beside provisional proposals. Full images and crops are available only to the current uploader-participant or a facilitator.
5. Edit and accept with displayed record revisions. Preserve edits on conflicts and require renewed human intent.
6. Stop capture through pause or withdrawal. Late admission does not reset the room; lease expiry preserves agreement and proposals. Reconnect never silently activates capture.
7. Export with an explicit unresolved-content choice. At logical storage caps, use `export-snapshot`, which returns one consistent download without adding stored export or retry records.
8. Close with a session revision, then delete separately when intended.

Control commands use an actor-scoped sequence in addition to the immutable request ID. Read `next_control_sequence` from the snapshot, allocate one intent at a time, and keep that sequence for retries. Simultaneous clients may conflict. After a replay expires, refresh rather than assuming the earlier action failed. See the exact control list in API.md.

## Storage and evidence decisions

| Decision | Reason and cost |
| --- | --- |
| SQLite, one instance owner | Atomic records/events and predictable rollback. This is not a distributed service. |
| Independent invitation redemption | The facilitator no longer routinely receives participant credentials. A code does not prove real-world identity or prevent deliberate self-redemption. |
| Separate session, roster and event revisions | Heartbeats do not make administrative decisions stale. Clients must handle several explicit concurrency tokens. |
| Bounded control replay ledger | Stop commands remain available at logical content caps. Only the latest 128 control responses per actor are retained; older outcomes require resynchronisation. |
| One sanitised media payload per session/digest | Region history does not multiply image bytes. The original file is intentionally discarded. |
| Full PNG/JPEG decode and fresh PNG encoding | Removes EXIF/GPS/comments/appended bytes. Applies EXIF orientation, flattens transparency on white and discards ICC profiles, interpreting RGB values as sRGB. ICC-managed colour fidelity is not promised. |
| Author/facilitator crops | Review evidence does not become an unrestricted full-image proxy. Unrelated participants and viewers cannot fetch arbitrary crops. |
| Killable fixture subprocess | A hanging adapter releases the worker after its total deadline or cancellation. Process startup has a cost; remote providers still need network deadlines and billing reconciliation. |
| Bounded retained completion results | Transient completion-store failure retries the validated result without another extraction. Retention is in memory, so a process crash can lose that result. |

Pixel decoding and orientation use [Pillow Image](https://pillow.readthedocs.io/en/stable/reference/Image.html) and [ImageOps](https://pillow.readthedocs.io/en/stable/reference/ImageOps.html). Removing metadata does not anonymise visible names, faces or handwriting.

## Limits and failure behaviour

- 4 MiB input and sanitised output per image, 20 megapixels, dimensions at most 12000, and 60 regions/references. Unsupported multiframe or undecodable images are rejected.
- 20 MiB stored media, 1000 records and 10000 ordinary command results per session. Ordinary content/history/media has a 64 MiB logical budget. Invitation records are capped at 128; current membership at eight; control responses at 128 per current actor and 2048 bytes each. These are logical store bounds, not a total SQLite-file or filesystem cap.
- At most five queued/running jobs per session and 32 per instance. Claims rotate between sessions. Queue deadlines are reconciled independently of callbacks. Runtime isolation uses at most 30 seconds per call, reduced to the remaining job deadline.
- A failed purge remains pending, expired content stays inaccessible, and unrelated sessions continue. Physical database failure can still prevent all operations; export cannot recover unreadable storage.
- Pause, withdrawal, removal, close and invitation revocation use the bounded control reserve. Role changes and renewed agreement use ordinary quotas, which bounds repeated acknowledgement/withdrawal and promotion/demotion histories. Heartbeats are coalesced and emit no events.
- Retention defaults to 24 hours, configurable from 60 seconds to seven days. Heartbeats do not extend retention. Closed sessions permit reads, export and deletion, not renewed capture.
- Deletion covers records, versions, events, ordinary/control retry results, actors, invitations, media and retained completion results. In-flight adapters are cancelled; external provider work may have already incurred cost. Downloaded copies, operating-system snapshots, backups and process-memory forensic recovery are outside the deletion claim.
- Schema migrations 1 through 4 are ordered and transactional. Legacy media in current records, history and retry responses is sanitised; undecodable legacy media becomes explicitly unavailable. Legacy regions are transformed for EXIF orientation. Existing credentials are preserved; legacy acknowledgement timestamps remain unknown until renewed.
- Export is an output-only release. Manifest IDs/revisions match included records; source references need the retained session and do not become a standalone evidence bundle. Exports are not anonymised.

## Scope that remains separate

No live OCR, transcription, automatic region detection, layout/collision engine, external board synchronisation, identity recovery or public hosting has been enabled. Record geometry and richer event synchronisation remain the other workstream's responsibility. Mechanism tests do not establish AI quality, user benefit, phone connectivity or Swift compilation.

See [BUILD-STATUS.md](BUILD-STATUS.md) for exact verification and remaining limits. The course decision and AI-use logs record review honestly.

## Combined B/C integration

This candidate includes main `0fe7b083007f0656b654034d88bcfc1330eacbc4`: independent board positions, transaction write descriptors, delta snapshots and HTTP/1.1 gzip transport. See API.md for `item.place` and `since_seq`. Schema 5 inspects actual tables to distinguish the two historical version 2 meanings and preserves both histories. The combined tests include migration restart and retained B/C coordinates.

The populated-board sync budget is still open: the complete board order travels with each delta. `python tests/measure_sync.py --positioned` intentionally exits 1 when its measured response exceeds 5 KiB; this is a recorded performance gap, not a green acceptance check.

## Recovery and release decisions

Interrupted claimed jobs now fail with an uncertain outcome, never automatic
re-extraction. A deliberate retry requires the previous job ID and explicit
uncertain-cost acknowledgement; see API.md. Returned usage is retained even if
cancellation or storage limits discard proposals. This does not enable a paid
provider or supply provider-specific billing guarantees.

Lost sole-facilitator credentials cannot be reset. Another current facilitator
may revoke the lost membership and issue a fresh invitation, whose new actor
must independently acknowledge the policy. Choose secure client credential
storage before a pilot.

Exports are output-only releases: selected text stays readable offline, while
source evidence links require the retained session. They are not anonymised.
No evidence bundle or automatic redaction is implied.

## Runtime visibility

Use `GET /ready` to distinguish a responsive HTTP server from progressing worker
and maintenance loops with an available store transaction. A 503 includes safe
check states; `/health` remains liveness only. Current facilitators can read
`GET /api/sessions/{sid}/diagnostics` for bounded queue, failure and logical-storage
metrics. Diagnostics do not modify session state or reveal source content.

Read [RUNTIME-OPERATIONS.md](RUNTIME-OPERATIONS.md) before interpreting these
signals as recovery instructions. The store probe is not a physical disk or
backup test; future provider failures and real-device behaviour remain separate.

## Client plumbing

Use [CLIENT-PLUMBING.md](CLIENT-PLUMBING.md) for total request deadlines,
immutable retries, credential/URL cleanup and the new SessionConnection polling
and opt-in heartbeat layer. It includes the synthetic two-client HTTP journey,
named guard mutations and the explicit boundary between local stop and server
pause. The browser workflow and real-device acceptance remain open.
