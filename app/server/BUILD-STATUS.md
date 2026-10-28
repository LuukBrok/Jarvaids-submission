# Automatic workspace trial, 20 October 2026

This entry supersedes older manual marking/acceptance statements below for the
PC launcher. Candidate: `feature/automatic-workspace`, based on main `d27917a`.
Luuk requested these changes after the integrated trial and supplied the failed
close-voting ASR strings. WP1 and the shared summary bridge remain missing.

Executed on this Windows PC with Python 3.12.10, installed Pillow, Node 24.19
and local Chrome:

- Backend: 613 discovered tests, 611 passed and two explicitly skipped.
- JavaScript: 265 passed. Schema registry, proposal coverage, HTTP client and
  sync-budget checks passed; the positioned example stayed below 5 KB/client.
- 298 named guards passed across 13 harnesses, including five new automatic
  intake guards. Each must fail its named assertion; import errors do not count.
  Calendar review-mode guard patterns were updated for the explicit automatic
  mode condition and all 21 still failed their intended tests when removed.
- All 19 browser journeys passed. The new automatic journey runs at 1440 and
  400 px: photo selection with no boxes, immediate typed/photo notes, correction,
  photo undo/restoration, shared collectors, poll auto-open/finish and one counted
  identified vote, growing long cards, collapsed details, no errors/failed
  requests/horizontal overflow. Desktop and phone screenshots were inspected.
  The older poll journey now pans the canvas to controls instead of relying on
  internal card scrolling; its manual review-mode trial also passed both sizes.
- One actual configured Claude photo-reader call through the isolated service
  path detected all three notes on a generated fictional wall and preserved all
  six lines exactly. All three notes applied automatically with source crops and
  no human acceptance. Reported usage: 2291 input and 214 output tokens; adapter
  list-price estimate USD 0.013444, not a billing statement. The test session was
  deleted afterwards; generated evidence/results remain ignored under
  `.local/automatic-provider/`. No user meeting photos were used.
- The real call first exposed HTTP 400 because the provider rejects `maxItems`
  in output schemas. The schema now uses ordinary arrays; local validation still
  enforces at most 60 distinct note IDs, four finite box coordinates and bounds.
  A regression test covers the provider-compatible schema shape.
- The actual PC launcher passed startup on spare ports 3011/5181 with automatic
  mode, the real photo configuration, installed Whisper/speaker runtime and
  wake-word manifest. Its test servers stopped afterwards.
- Bash is unavailable on this PC. The 12 Bash audit regex rules were reproduced
  in Python without violations and the 52 contrast pairs passed. The actual
  Bash audit remains a GitHub CI check; its result is not inferred locally.

This proves the integration and one clear synthetic wall, not broad handwriting,
overlap or meeting-room speech accuracy. Capture agreement remains; ordinary
content acceptance is removed in automatic mode. Automatically applied content
retains source/model labels, editing and supported undo, without invented human
acceptance. Legacy review mode remains available for compatibility.

---

# Backend build status, 16 September 2026

> Latest integrated evidence is in [CLIENT-PLUMBING.md](CLIENT-PLUMBING.md):
> 237 backend tests, 38 client tests and 143 named guards passed after integrating
> PR18. Positioned-board sync measured 1662 B compressed per client. Runtime and
> prior follow-up documents retain their historical evidence. Results below
> describe the earlier H/B/C plus A/E/D integration.

A/E/D implementation integrated with B/C main `0fe7b083007f0656b654034d88bcfc1330eacbc4`, after H was merged. See the pull request for the published candidate commit. Provider selection remains open; every extraction used a clearly labelled fixture, never live OCR.

## Executed verification

| Command/check | Observed result |
| --- | --- |
| `python -m unittest discover -s tests` | 164 tests passed in 43.702 seconds, Windows / Python 3.14 / installed Pillow 12.0.0 |
| Focused sync suite after final transport assertion adjustment | 13 tests passed in 1.831 seconds |
| `python tests/mutation_check.py` | 47 service/position/transport guards caught by their named behavioural tests |
| `python tests/isolated_mutation_check.py` | 8 isolation guards caught; real subprocesses, including hangs and cancellation |
| `python tests/media_mutation_check.py` | 9 media guards caught, using valid synthetic PNG/JPEG/APNG and malformed pixel data |
| `node tests/client-unit.mjs` | Passed LAN crypto without randomUUID, explicit LAN origin validation and immutable control envelope |
| `python demo.py --url http://127.0.0.1:8878` | Passed real CLI agreement, typed review/retry, edit/undo, isolated image fixture, export/close/delete |
| `node tests/client-smoke.mjs http://127.0.0.1:8878` | Passed real HTTP client creation, retry, review, conflict, events, export and deletion |
| `tests/test_runtime_journey.py`, included above | Real CLI process: independent guest join, image intake, isolated fixture, authorised crop, acceptance, immutable export, nonpersistent snapshot export, withdrawal and deletion |
| Repository contrast checker | 105 pairs across four schemes passed |
| Repository Bash design audit | **Not run successfully:** Bash could not start because of a Windows signal-pipe access error. No passing audit claim. |

Guard tests are not just a green count: wrong-test failures and infrastructure errors are rejected. Scratch trees isolate mutations from original source. The crop pre-authority mutant initially survived because post-render authority still denied the response; a dedicated test now proves unauthorised callers cannot trigger decoding. No passing result is claimed for arbitrary malformed provider code, device usability or AI quality.

## Review and acceptance scope

A second agent inspected identity/lifecycle transitions, completion caching, image sanitisation and crop access, and independently reproduced two defects during development: capture after a failed lease-pause write and delayed activation overriding a pause. Both now refuse with the expected error in independent probes. It also supplied isolated execution, media guard and real HTTP journey checks. Human line-by-line review remains pending.

The [requirement matrix](ADE-COVERAGE.md) distinguishes implemented mechanisms from unverified deployment/product claims. Notably:

- Phone/firewall connectivity, Swift compilation, frontend interactions and user evaluation were not performed.
- No paid provider, remote network timeout, billing reconciliation or actual handwriting quality was tested.
- Fault tests use SQLite failures and controlled barriers, not physical disk-full or power-loss experiments.
- Ordinary quotas, bounded control replay and queue fairness are tested. No throughput, latency percentile or hardware memory benchmark is claimed.
- Migrated credentials are preserved and legacy agreement timestamps remain unknown until renewed. Device redemption is not real identity verification.
- Output export references depend on the retained session. Source evidence, downloaded-copy deletion and external backup restoration are separate concerns.

## API compatibility

This is a deliberate API change: participant credentials are no longer supplied by the facilitator, activation/close and roster changes use explicit revisions, and stop/control commands use actor-scoped control sequences. Schema 5 converges both published histories by inspecting actual tables: B/C version 2 positions and A/E/D consent/media/control versions 2-4. Migration/restart tests preserve B/C coordinates and A/E/D invitations. Current/history/retry media payloads are sanitised; undecodable legacy images become unavailable. See API.md before connecting a client.

B/C position and event changes are included. The user authorised merging after combined integration; these automated results do not substitute for the outstanding device and product evidence.

## Combined verification and sync limit

All 64 named guards pass: 47 service/position/transport, 8 isolated execution and 9 media. The portable checker runs a complete baseline before targeted mutants; the keep-alive test now explicitly asserts malformed response status when draining is removed, so a decoder exception cannot masquerade as a behavioural kill. Windows test fixtures close SQLite handles and use workspace directories.

The real CLI demo and JavaScript HTTP smoke passed against the combined runtime on port 8878. The JavaScript journey additionally checks delta record count, cursor and actor control sequence. No live provider was used.

`python tests/measure_sync.py --ceiling` passed its unpositioned synthetic fixtures: 41 records used 1662 bytes/client, 965 used 1665 bytes/client. Seven loopback clients; commit times 8/11 ms and slowest client 4/9 ms are local observations only.

`python tests/measure_sync.py --positioned` correctly exited 1: 965 records with 321 positioned items used 8308 bytes/client, exceeding the 5 KiB target. Each delta still includes the complete board order. This is an open C06 performance gap, not a passing scaling claim. A second agent independently reproduced the same issue on a 400-position fixture.

**Superseded on 16 September by INT13:** the board order left the delta, and `tests/measure_sync.py` now runs the positioned fixture by default and passes at about 1660 bytes per client. The paragraph above is kept as the record of the defect; the number in it is no longer current.

Legacy event rows without transaction write descriptors trigger a full record refetch in delta. New pause events preserve policy/proposals and name only actual cancellation writes. Existing Swift verification remains unchanged from main and explicitly uncompiled; current API compatibility needs a separate client pass.

Migration support covers the published schema histories. The follow-up adds preflight for partial layouts, columns and integrity constraints before writes; see FOLLOWUP-STATUS.md for the current scope and remaining physical/data-integrity limits.

## F1.1-F1.3 audio (2026-09-22)

Added `source.audio`, `transcript_segment` records with provenance, and `capture-audio.mjs` (browser chunker). Scope cuts against pipelines.md section 1, each with cost stated in decisions/decision-log.md: single-lane transcription (no fast-caption lane), per-connection speaker attribution (no embedding/clustering diarisation), and an energy-threshold VAD (no Silero WASM VAD).

Actually run in this session:

- Full Python suite: 244 tests (237 plus 7 new), passing.
- `tests/mutation_check.py`: 62/62 service guards caught by name, including the 3 new audio guards (consent gate, capacity cap, gap-not-dropped).
- `tests/schema_mutation_check.py`, `tests/media_mutation_check.py`, `tests/isolated_mutation_check.py`, `tests/runtime_mutation_check.py`: unchanged 12/12, 9/9, 8/8, 10/10, since audio adds no schema migration (`transcript_segment` reuses the existing generic `records` table) and touches no media/isolation/runtime code.
- `python3 .github/scripts/check_schema_versions.py`: consistent, unaffected.
- `python3 tests/measure_sync.py`: unaffected, both fixtures still under budget.
- `python3 tests/client_http_check.py`: passing.
- `node --test tests/capture-audio-unit.mjs`: 4/4 passing (the DOM-free `Chunker`: endpoint on 400ms silence, hard cut at 12s, minimum-duration floor, base64 round-trip).
- `./app/design-system/spec/audit.sh` and `contrast-check.py`: passing, unaffected (no UI touched).

Not run, not verified:

- `node --test --test-isolation=none tests/client-transport-unit.mjs tests/session-sync-unit.mjs`: fails in this sandbox with `node: bad option: --test-isolation=none` on Node v22.22.2. Reproduced identically against a clean stash of the pre-existing main branch, so this is a sandbox/Node-version issue, not a regression from this change.
- Real ASR quality. `FixtureTranscriber` (default adapter) is synthetic, deterministic and offline, exactly like `FixtureExtractor` for images: it proves the plumbing (consent gate, provenance, gap-on-failure), not transcription accuracy.
- `LocalWhisperTranscriber` (wraps faster-whisper): written but never constructed or called in this session. No GPU, no model weights, no faster-whisper install in this environment.
- The getUserMedia/AudioWorklet half of `capture-audio.mjs` (`startCapture`): needs a real browser with microphone access; not exercised. Only the pure `Chunker` class was unit tested.
- Real speaker diarisation, mixed-language handling, and the level-meter/queue-badge UI pipelines.md's failure-mode table describes: none of that UI exists yet; this slice is server contract plus a capture module, not the meeting-room screen.

## 5 October 2026: F02 confidence and colour, a parser defect, and the list reconciled

Run in the cloud development container: Linux 6.18, Python 3.11, Pillow 12.0.0
installed for the run (it was missing, which first made 19 test modules error
on import), Node 22.22.

| Check | Result |
| --- | --- |
| `python3 -m unittest discover -s tests` | 262 tests passed (254 before: six F02 tests, two J02 tests) |
| `tests/mutation_check.py` | 72/72 service guards caught by name, six of them new: `note-confidence-range`, `note-colour-shape`, `edited-text-drops-confidence`, `overflowing-number`, `overflowing-integer`, `nesting-depth` |
| media, isolated, schema, runtime harnesses | 9/9, 8/8, 12/12, 10/10, unchanged |
| `tests/client_http_check.py` | passed |
| `check_schema_versions.py`, `check_proposal.py`, audit, contrast | passed |
| `tests/measure_sync.py` | WALL-12 1658 B, POSITIONED 1670 to 1671 B compressed a client across runs; the two new null keys cost about 3 B |
| Node unit tests with `--test-isolation=none` | **not run**: Node 22 rejects the flag. The same 42 tests pass without it, which is weaker, because isolation is the point of the flag |
| `tests/client_mutation_check.py` | **not run**, same cause. CI runs both on Node 24 |
| `LocalWhisperTranscriber` | **still never run.** The container's network policy refused `huggingface.co` (HTTP 403 at the proxy), so no weights could be fetched |

The parser defect: `1e999` is legal JSON, is not the literal `Infinity`, parsed
to inf and returned HTTP 500 at the idempotency fingerprint. It is now a 400
`invalid_json` with no state change. Checking the fix turned up the same defect
spelled differently: a 400-digit integer has no exponent, so it goes through
`parse_int`, and `math.isfinite` raised OverflowError on it in the region-box
validator. The parser now refuses any integer too large for a float too. The 16 September tick on J02 had claimed
non-finite numbers were already refused.

No live provider was enabled. F02 is a contract the fixture exercises with null
values and test adapters exercise with made-up ones; no real model has produced a
confidence or a colour in this project.


## Combined local browser test, 12 October 2026

The workspace and transcript backend are combined in one tree, with silence no-ops and the browser speech debounce. Windows Python 3.12: setup installed dependencies and Whisper Base successfully in a short temporary runtime; the launcher started both real servers, checked API readiness and client HTTP 200, then stopped both with --check. 58 Node tests passed. Backend discovery ran 293 entries: 292 passed and test_operations failed to import the Unix-only resource module on Windows. This is not a passing full-suite result. Schema and proposal checks passed. Full mutation suites, a human microphone run of this combined tree, the browser journey and other operating systems remain unverified. No model weights, recordings or credentials are included. See LOCAL-TEST.md for defaults and remaining product limitations.
A further direct check of this combined Service with the fresh real Whisper runtime passed: silent audio created no record and a synthetic spoken test sentence produced a final non-synthetic transcript. This is mechanism verification, not human speech accuracy.

## Workspace command indicators, 13 October 2026

The workspace now renders the backend voice_command metadata with provisional badges, request-specific feedback and a latest-message live region. Capture IDs and monotonic recording timestamps allow the existing split-command recogniser to operate in the workspace. 11 Node audio/feedback/context tests and 22 recognition tests pass. Synthetic UI Chrome checks at 1440/400 px pass with zero browser errors, failed requests or horizontal overflow; screenshots inspected. This validates display and recording metadata, not human ASR accuracy or execution. Command execution and automatic canvas content remain unimplemented.
Live localhost verification in English mode also passed with a synthetically spoken request: Whisper produced Hey Jarvis, make a summary, and the stored voice_command was recognised with intent summary. The live static server returned the updated indicator renderer. Temporary verification session deleted; no human microphone accuracy claim.

## Canonical activation display, 13 October 2026

Explicit direct-address alternatives, including observed Jarvan's and Jarveds, are recognised and displayed as Hey Jarvaids. Original ASR text remains stored, with canonical display supplied as optional correction metadata. UI disclosure exposes the original words. 25 recognition and 42 service tests plus 11 Node checks pass; Chrome checks at 1440/400 px pass with screenshots inspected. A live synthetic spoken request also verifies unchanged raw ASR and canonical display metadata. Uncertain phrases are not corrected; human speech accuracy remains unverified.

## Full implemented-feature local test, 13 October 2026

Speaker enrolment and real CPU Resemblyzer matching are integrated into the workspace. The optional acoustic detector, HTTP routes, lifecycle invalidation, original tests and training resources are retained alongside transcript-based command recognition. The launcher enables real speakers and detects an installed custom manifest. Setup uses tested Python 3.12, CPU Torch 2.14.1, Resemblyzer 0.1.4 and a Windows webrtcvad-wheels module; pip can report the legacy webrtcvad distribution name as missing although the actual embedding import/path succeeds.

Live HTTP verification with synthetic speech passed: non-fixture speaker profile, named real transcript, summary recognition, canonical activation display, plus actual custom detector start/batch/stop. Real encoder and trained detector load and run locally. The full suite ran 326 entries: 325 pass, one existing test_operations import needs the Unix-only resource module unavailable on Windows. 29 dedicated wake-word tests and 19 Node audio/wake-word tests pass. Speaker enrolment/cancellation and label UI, plus command UI, pass in Chrome at 1440/400 px with screenshots inspected and no errors/failed requests/overflow. Human multiple-speaker matching, overlapping speech separation, trained detector accuracy, complete mutation suites and other OS setups remain unverified. Custom weights and all session/voice data stay out of Git.

Speaker matching repair, 2026-10-13: 14 adapter tests and 42 service tests passed. Speaker enrolment/browser regression passed at 1440px and 400px, including matched and unknown labels and the voice-matching caption, with zero console errors, failed requests or horizontal overflow. Real human accuracy still needs a new laptop trial; prior audio was not retained, so historical unknown rows are not relabelled.
Full backend discovery after this repair: 327 tests passed; test_operations could not import because Windows lacks the Unix resource module (328 entries total). The sandboxed attempt encountered filesystem restrictions; the reported results are from the subsequent unrestricted test run.

Sentence and activation repair, 2026-10-13: 13 capture/context/sentence tests, 26 command tests and 42 service tests passed. Browser regression at 1440px and 400px verified joined sentence text, canonical activation, voting feedback and original-ASR disclosure without console errors, failed requests or overflow. Real local Whisper Base transcribed the existing synthetic test clip as Hey Jarvaids, make a summary and recognised summary. This does not establish human-room accuracy. Incorporated the upstream 3fcf420 shared CPU model lock.

## Batch synthesis (2026-10-13)

Added `genai_server/synthesis.py` and the optional `genai_server/claude_synthesis.py`: photographs and a Whisper JSON transcript to a provisional proposal file, outside the server. What it does, what leaves the machine and what is not built are in [SYNTHESIS.md](SYNTHESIS.md).

Run in a Linux container, Python 3.13, Node 22.22:

- Full Python suite: 300 tests (254 plus 46 new), passing.
- `tests/synthesis_mutation_check.py`: 26/26 guards caught by name. The other Python harnesses unchanged and passing: 66 service, 9 media, 8 isolation, 12 schema, 10 runtime.
- `audit.sh`, `contrast-check.py`, `client_http_check.py`, `check_schema_versions.py`, `check_proposal.py`, `measure_sync.py` (1666 B a client): passing, unaffected.
- The adapter against the real `anthropic` 1.13.0 SDK in a separate virtual environment, network mocked: request body and beta header as intended, streamed answer parsed, 400/401 stop the run, 429/529 fail the step.

Not run, not verified:

- `client_mutation_check.py` and the `node --test --test-isolation=none` units: `bad option` on Node 22.22, as before. CI runs them on Node 24.
- **Any call to the real Anthropic API.** Reading, merging and form-choice quality, and the cost guess in SYNTHESIS.md, are unmeasured.

Main publication, 2026-10-13: the user confirmed the live sentence/activation repair worked on their laptop. Merged current main (2366da7), retaining batch synthesis. Before publication, 374 runnable backend tests passed; the Unix resource-limit module is now explicitly skipped on Windows. Design audit (13 checks), contrast, schema registry, proposal coverage, media/isolation/schema/runtime/synthesis/client mutation guards, 42 client transport/sync/order tests, real HTTP journey and sync budget checks passed. Browser sentence/command regression passed at 1440px and 400px after the merge. Mutation harnesses used a short temporary source path to avoid Windows path-length errors.
Publication follow-up: only the two resource-dependent storage/memory checks are skipped on Windows; portable connection and on-disk deletion tests remain enabled. The complete backend mutation baseline passed after this change. All 72 service guards were caught across the initial 68 successful guards and the four portable guards rerun after narrowing those skips.

## WP3 voice polls, 19 October 2026

Candidate: feature/voice-polls, based on f9e2b26. Python 3.12.14 and Node 24.19.0
on Windows. The app and API run on localhost; optional cloud interpretation sends
bounded transcript text, not audio or voice embeddings. See docs/voice-polls.md.

Verified:

- Backend discovery: 405 entries, 403 pass and 2 existing Unix-resource-dependent
  checks skipped on Windows. The final stale-reply feedback refinement also
  passes all 26 polling tests separately.
- All eight mutation harnesses pass: 72 service, 9 media, 8 isolation, 12 schema,
  10 runtime, 26 synthesis, 45 client and 7 polling guards. The seven polling
  mutations were rerun after the final feedback refinement and all were caught
  by their named assertions. Disposable short source paths avoid Windows path
  limits; no mutation edits the working source.
- 43 client transport/sync/order/poll units and 8 board units pass. Real CLI HTTP
  client journey, schema registry and proposal checks pass. Sync stays below
  5 KB compressed per client on the existing fixtures: 1776 B and 1787 B on this
  machine. These are transport measurements, not speech or AI response latency.
- Design audit (13 checks) and contrast pass. Existing command and speaker Chrome
  regressions pass at 1440/400 px, as does the new complete poll HTTP/browser
  journey: recognised command/replay, draft, voice confirmation, multiple votes,
  changed vote, unknown-speaker correction, accepted tie, reconnect persistence
  and a binary poll. No console/page errors, failed requests or horizontal body
  overflow. Screenshots were inspected under .local/poll-ui/.
- CLI live-launcher configuration, private .env loading and provider request shape
  have synthetic contract coverage. New cloud configuration pauses old active
  sessions and requires updated agreement. The default CLI stays offline.

Limits: the browser journey uses explicitly scripted transcription, embedding
and interpretation test doubles. It does not establish real microphone, enrolled
speaker or LLM accuracy. No project API key was supplied, no real API request
was made, and the live speech runtime is not installed by this work. Run Setup
Jarvaids.cmd from this checkout and configure .env for the real group trial.
API latency/cost and overlapping-speaker behaviour are unmeasured. Polls persist
in the session; existing output-only note exports do not yet include poll records.
Earlier sandbox/temp failures are not counted as passing runs; the results above
come from normal localhost/temp access and a short code-only verification copy.

## Automatic wake-word startup follow-up, 19 October 2026

Listen now starts the acoustic detector alongside transcript recognition without
an additional checkbox. If custom weights are absent, the status reports this
and transcript commands remain usable. A refused microphone releases the detector.
No server API or storage schema changed.

The new Chrome journey passes at 1440 and 400 px with scripted detector replies
and a fake microphone: automatic startup, stop, missing-model fallback and
microphone refusal. Screenshots in `.local/wakeword-listen-ui/` were inspected;
no page/console errors, failed requests or horizontal overflow. Poll and command
browser regressions also pass at both widths. These tests establish wiring,
not acoustic accuracy. Luuk separately reported that his real voting trial went
well and that voice closing worked; group accuracy, latency and cost are unmeasured.

Backend discovery passed again: 405 entries, 403 passing and two existing
Windows resource skips. The 28 focused audio/wake-word/board tests and 43 client
transport/sync/order/poll tests pass, as do the CLI HTTP journey, schema registry,
proposal check, sync budget, 13 design checks and contrast. The first service
mutation baseline hit Windows socket error 10053 in the existing connection-slot
pressure test; the full discovery run passed. All seven other mutation harnesses
passed. The isolated service retry then passed all 72 named mutations. Together,
the eight harnesses caught all 189 existing guards. The earlier interrupted
baseline is recorded as an infrastructure failure, not a behavioural result.

This branch is being shared separately from the newer main interface for the
team's planned integration. The poll guide lists the shared files and repeat
journey needed after combining the branches.

## Voice to-do documents, 19 October 2026

Phase one of Luuk's approved command-document plan is implemented on
`feature/voice-todo-lists`. Whole-meeting original transcript batches create a
provisional task list and live speech continues collection. Stable tasks support
suggested/agreed classification, stated owner/deadline, completion, correction,
manual editing, evidence, voice close/accept/reopen/cancel and placement. Separate
document/entry/work records prepare shared calendar references without enabling
requirements/wishes or calendar execution yet. See docs/voice-todo-lists.md.

Final verification:

- Backend discovery: 437 entries, 435 passed and two existing Windows resource
  skips. The 32 new document/adapter cases also run through the mutation baseline.
- All nine mutation harnesses passed: 189 existing guards plus 21 named document
  guards, 210 total. Each new mutant failed its named assertion. Guards cover
  addressed/fixture gating, whole-history scope, source quotes, field evidence,
  actual speaker identity, manual priority, capture ordering, synthetic output,
  pending/incomplete acceptance, retry acknowledgement, consent, authority before
  and after the call, source revision, batch size, removed tasks and strict input.
- 71 client/transport/sync/order/poll/audio/wake-word/board units passed. The real
  CLI HTTP journey, schema registry and proposal checks passed. Existing sync
  fixtures measured 1832 and 1834 B compressed per client, below 5 KB; this is
  transport evidence for those fixtures, not a benchmark of large to-do lists.
- The 13 design audit checks and contrast passed. Chrome to-do tests at 1440 and
  400 px passed history older than two minutes, command replay, named assignments,
  deadlines, changes/completion, unknown-owner clarification and a spoken answer,
  manual edits, focus/caret preservation, merging an AI deadline into an unsaved
  text edit, actual drag persistence, List view, voice lifecycle and reconnect.
  Screenshots under `.local/document-ui/` were inspected; no page/console errors,
  failed requests or horizontal body overflow. Poll, transcript-command and
  automatic wake-word browser regressions also passed at both widths.
- The existing user-installed local speech/speaker runtime restarted successfully.
  /ready returned ready and the client returned HTTP 200, with both poll and
  whole-meeting document interpretation configured. No new cloud generation was
  requested by automated verification.

The first broad suite found the expected committed snapshot mismatch after
adding `session.command_ai`; the fixture was regenerated with its existing
generator. The final complete suite passed. Earlier socket-pressure failures in
the historical logs are not reported as passing runs.

Limits: browser speech, voice and AI replies were scripted test doubles. Real
to-do interpretation, group microphone accuracy, latency and cost await Luuk's
trial. Dates are retained as spoken phrases until the calendar phase. Semantic
interpretation is not guaranteed by quote validation. Output-only note exports
do not include command documents yet. The newer main interface remains a
separate integration task. Do not start requirements/wishes before the trial.

## Voice requirements and wishes, 19 October 2026

Luuk reported the to-do microphone trial worked well, retained the acceptance
step with review allowed later, and requested the next command. The tested
`feature/voice-todo-lists` commit `ddbdc4e` was published to origin. Phase two on
`feature/voice-requirements` adds typed criteria and three sections using shared
whole-meeting original-transcript work, history, sync and canvas placement.
Calendar execution and integration with the newer main canvas remain deferred.
See [the requirements trial](../../docs/voice-requirements.md).

Final candidate verification, Windows, Python 3.12 and Node 24:

- Full backend discovery: 460 entries, 458 passed and two existing Windows resource
  skips. The 23 requirements/adapter cases use scripted responses. The full run
  emits connection-reset tracebacks from deliberate socket-pressure cases but
  completes successfully; these are not evidence of a speech/AI quality failure.
- All ten mutation harnesses passed: 189 earlier guards, 21 shared document guards
  and 11 requirements guards, 221 total. New guards cover criterion identity,
  synthetic output, inferred classification, numeric targets, stated/quoted
  evidence, conflict placement/resolution/acceptance, type-targeted lifecycle
  and selecting the provider schema. Each mutant failed its named assertion.
- 71 client/audio/wake-word/board/transport/sync/order/poll units passed, plus the
  client unit script, CLI HTTP journey, schema registry and proposal check.
  Existing sync fixtures used 1837 and 1851 B compressed per client, below 5 KB.
  These are fixture transport measurements, not a large-criteria benchmark.
- All 13 design audit checks and all 105 contrast pairs passed.
- Chrome requirements tests passed at 1440 and 400 px: original history older than
  two minutes, command replay, requirements/wishes/inference, flagged conflicts,
  manual text and section edits, evidence, dirty text/focus/caret preservation,
  spoken reclassification, ambiguous references, visible validation failure and
  explicit retry, real drag persistence, List view, title editing, deferred
  acceptance while a to-do list starts, acceptance, reopen/cancel and reconnect.
  Screenshots in `.local/requirements-ui/` were inspected. No page/console errors,
  failed requests or horizontal body overflow. Existing to-do and poll browser
  journeys passed at both widths too. A dropdown labelling issue found by the
  browser was fixed with an explicit accessible field label.
- The existing local Whisper/speaker runtime was restarted with both command AI
  paths configured. `/ready` returned ready and the client returned HTTP 200.
  No new live cloud generation was requested during automated verification.

An early criterion-evidence mutant was masked by the separate stated-quote
check. Its test now isolates quote validation directly, and the mutant fails its
named assertion. The older creation-guard mutant needed a default type after the
new typed dispatch; its original runtime error was not counted as a kill. All
final harness results above passed after those test corrections. The deterministic
ordering fixture was regenerated for the new capability metadata.

Limits: scripted speech/voice/AI establish wiring, not interpretation accuracy.
The requirements microphone trial is pending; stop here before calendar work.
Numeric checks cover digits and common English number words, not every semantic
quantity/unit or language. Quote validation cannot prove correct interpretation
or complete conflict detection. Both active collectors can incur separate calls
for a batch before the model ignores unrelated speech. Exports still omit command
documents, and full browser reload loses the existing in-memory login. No real
phone/network, overlapping-speaker, latency or cost evaluation is claimed.

## Conversational command repair, 19 October 2026

Luuk reported requirements worked but polls and to-do objects did not appear.
His screenshot showed the intact transcript "Hey Jarvaids, let's make a voting
list" with unsupported-command feedback. The deterministic recogniser accepted
"make a voting list" and "let's vote" but omitted "let's make". This was a
recognition gap, not a one-feature-at-a-time restriction or an AI extraction error.

The recogniser now removes explicit conversational build framing before matching,
while retaining the original transcript. Twelve new phrasing subcases failed
before the fix and pass afterwards; all 27 voice-command tests pass, including
negated/deferred/compound refusals, required direct address and existing let's vote.
Final backend discovery: 461 entries, 459 passed and two existing Windows skips.
Client contracts (43 units), the client HTTP journey, schema/proposal checks and
sync budget pass. Sync fixtures measured 1837/1849 B compressed per client.
The design audit and contrast checks pass. Chrome at 1440 and 400 px now creates
requirements, a to-do list and a poll together using let's-make phrasing and records
a named ballot while requirements await/receive review. The journey also retains
evidence, corrections, conflicts, dragging, retries and reopening checks. Screenshots
were inspected, with no page/console errors, failed requests or horizontal overflow.

The local server restarted with the repair; /ready is ready and the client returns
HTTP 200. Browser speech/voice/AI are scripted test doubles, not a microphone
accuracy result. Luuk's live retest of the phrasing fix remains pending. Calendar
work has not started. No new cloud generation was requested during verification.

All ten mutation harnesses were rerun after this repair and passed, protecting
all 221 named guards. No acceptance, attribution or authority guard was relaxed.

## Side-by-side command canvas, 19 October 2026

Luuk reported the conversational command repair worked and requested neighbouring
command objects rather than a vertical stack. Unplaced polls and command documents
now share chronological, top-aligned columns with the existing 24 px gap. Saved
positions remain exact. Ordinary unplaced notes retain their old lane. This is a
local presentation rule and issues no placement or acceptance operations.

Automatic focus shows neighbouring command headings when body text remains at
least 12 px at the resulting scale. Otherwise it focuses the new object at a
readable width and leaves neighbours reachable by panning. Long lists no longer
cause automatic full-height fitting, and ordinary sync preserves pan/zoom. Explicit
Fit still fits the whole board. Focus requested while Canvas is hidden is deferred
until it becomes visible. The latest new command takes precedence when several
arrive together. List view retains its linear presentation.

Verification: 461 backend entries, 459 passed and two existing Windows skips;
12 board/order unit tests and the client/HTTP/sync/schema/proposal checks pass.
Existing sync fixtures used 1838/1852 B compressed per client. The 13 design audit
checks and all 105 contrast pairs pass. Chrome layout checks at 1440 and 400 px
verify three top-aligned columns despite a tall task list, readable automatic zoom,
deferred focus, stable camera on sync, panning, exact hand coordinates, no automatic
writes, and no page/console errors, failed requests or horizontal body overflow.
Screenshots in `.local/command-layout-ui/` were inspected. Requirements, to-do and
poll HTTP/browser journeys also pass at both widths, including dragging and review.
Browser speech/voice/AI are scripted and layout records are explicitly synthetic.
No actual phone or new live-model quality measurement is claimed.

The running static server returns the new canvas module. Reloading the page loads
this frontend change; no backend restart, session migration or content change is
needed. Luuk's live layout review is still pending. On phones, columns require
horizontal panning; long lists still need vertical panning or List view.

All ten repository mutation harnesses also passed for this layout candidate,
protecting all 221 existing named guards. No new backend operations were added.


## Voice calendar candidate, 19 October 2026

WP3 phase three is on `feature/voice-calendar`, continuing the reported successful
requirements/layout trial. The original transcript drives a date-based calendar
with day/week/month/year views, unscheduled entries, source evidence, source-time
and IANA-zone date resolution, manual/voice corrections and the shared review
lifecycle. Canonical to-do IDs link deadline/completion across views. Accepted
task changes become explicit, revision-checked proposals in either collector.
Completing a task later does not re-anchor an unchanged relative deadline.

Executed on Windows with the bundled Python runtime, Node 24.19 and Chrome:

- Full backend: **501 entries, 499 passed, two existing Windows skips**. This
  includes 40 calendar/date/provider/shared-task cases and restart persistence.
- All eleven mutation harnesses passed, **242 named guards**, including 21 new
  calendar guards. They require a named behavioural assertion, not an import or
  runtime error. The final manual-date fix also passed document/calendar harnesses.
- 43 client/transport/sync/order/poll units, 28 audio/wake-word/board units and the
  legacy client script passed, alongside the HTTP journey, sync budget and
  schema/proposal checks. Sync measured 1852 B (WALL-12) and 1869 B (positioned)
  compressed per client on this one loopback machine, below 5 KB.
- Calendar, requirements, to-do, poll and command-column Chrome journeys passed
  at **1440 and 400 px**. Calendar coverage includes history, all views, period
  navigation without content writes, evidence, undated/ambiguous entries, voice
  date correction, manual creation/editing with draft/focus preservation, actual
  persisted dragging, shared accepted-task review and completion, deferred
  acceptance, voice lifecycle, visible invalid-output failure/explicit retry and
  reconnect. Screenshots were inspected; no console errors, failed requests or
  horizontal page overflow. Speech, speaker and interpretation replies were
  scripted doubles; the browser did not establish live microphone/model quality.
- All 13 design checks and 105 contrast pairs passed. tzdata 2026.5 was installed
  in the existing live environment and Europe/Amsterdam resolution checked offline.
  The standard setup installs the dependency from requirements.txt.

Windows sandbox socket/process restrictions initially blocked complete server and
browser runs; the successful runs used approved local test access. An initial
new mutation test hit a deliberately incomplete test voice profile rather than
the guard; its fixture was corrected and every named mutant was then observed
failing its intended assertion. Browser fixtures were corrected to keep ordering,
failure injection and asynchronous UI waits independent across sessions/widths.
Code-only short-path verification copies avoid the existing Windows SQLite path
length limitation. No raw session material or secrets were copied into them.

The existing localhost runtime is restarted with calendar support. No new live
cloud generation or actual agenda microphone trial was requested by the agent.
Luuk should now follow [the microphone script](../../docs/voice-calendar.md).
Group recognition/date quality, latency, cost, actual phone connectivity and
integration with the newer main canvas remain unverified. No human line-by-line
review or GitHub publication of this calendar branch is claimed.
## Canvas object model, server half, 18 October 2026

Schema 6 (nullable `w` and `h` on positions), `canvas.create`, `canvas.update`, `canvas.remove`, canvas proposals and sizes on `item.place`, per `docs/specs/2026-10-18-canvas-object-model.md`. Run on Windows 11, Python 3.14.0 from the repository virtual environment, Node 22.23.

| Check | Result |
| --- | --- |
| `python -m unittest discover -s tests` | 471 tests (401 before, 70 new in `test_canvas_objects.py`), all passing on the final run; one earlier run hit the known Windows socket flake `test_a_refused_connection_does_not_leak_a_slot` (`ConnectionAbortedError`) |
| `tests/mutation_check.py` | 113/113 service guards caught by name, 41 of them new canvas and size guards |
| schema, runtime harnesses | 12/12, 10/10, unchanged |
| `tests/client_http_check.py` | passed |
| `node --test` over the three client units, without `--test-isolation` | 42/42; the isolation flag is a `bad option` on Node 22.23 |
| `check_schema_versions.py` | consistent, versions 1 to 6 |
| `tests/measure_sync.py` | WALL-12 1657 B, POSITIONED 1667 B compressed a client (1653 B and 1667 B on the commit before, same machine) |

Not run here: the media, isolated, synthesis, extractor and client mutation harnesses (no change to their targets), and any browser journey: the client half of the spec is separate work.


## Complete localhost integration, 20 October 2026

Candidate: feature/complete-localhost-test, combining main e762a5d and
feature/voice-calendar 6ff00fe. Luuk authorised the integration and publication.
The current main canvas, drawing/quote/parked/strip tools and real photo reader
are retained, with polling, to-dos, requirements and calendar ported into them.
Julie's existing exploration is served as a separate companion. Luuk confirmed
that Roselique's WP1 is still missing; no live overview bridge is claimed.

Executed on this Windows PC with Python 3.12.10, Node 24.19.0 and Chrome:

- Backend: 594 tests, OK with two documented Windows/platform skips.
- JavaScript: 265 tests passed; contrast is included (52 contrast test cases).
- All 12 mutation harnesses passed: 113 service, 9 media, 8 isolation, 12 schema,
  10 runtime, 27 synthesis, 9 real-photo adapter, 45 JavaScript, 7 poll,
  21 document, 11 requirement and 21 calendar guards (293 total).
- Real local client HTTP journey, schema registry and proposal coverage passed.
  Sync fixtures passed at 1866/1880 compressed bytes per client on this machine.
- Local Whisper Base plus real Resemblyzer launcher startup/readiness passed on
  custom ports 3010/5180, with cloud interpretation explicitly off. Both servers
  stopped afterwards. The user's existing wake-word package was installed locally
  with its asset checksums verified; weights are not committed. This startup
  check does not establish wake-word human accuracy.
- All 18 browser journeys passed on this PC, including the final rerun after
  restoring the disabled state of Pause before activation. Command journeys run
  at 1440 and 400 px; the existing projector/canvas/header checks also exercise
  1920 px. The combined requirements journey creates a typed/accepted note, a
  shape and a synthetic photo reading in the same stored session as requirements,
  a to-do collector and a voted poll, then checks a second credential-based view.
  Desktop/mobile screenshots were inspected. No console errors, unexpected
  failed requests or horizontal body overflow were found in the journeys.
- Bash is not installed on this PC, so the actual Bash design audit is not claimed
  as locally run. Its 12 regex rules were reproduced in Python without violations;
  the separate contrast tests passed. GitHub CI retains the actual Bash audit.

GitHub PR #45 also passed its actual Bash design-system and contrast jobs;
remaining CI jobs are checked before merge.

Integration repairs include command cards counted in the empty state, list/draft
focus preservation, scrollable cards above the dock, current design tokens,
explicit agreement text, configured-detector availability without an intentional
503, merged worker/provider configuration and a custom-port URL that selects its
API. Test readiness responses are consumed, and Windows browser tests use the
actual interpreter with standard-library precedence so stopping a test cannot
leave the virtual-environment redirector's server behind. The deterministic
board-order fixture was regenerated after adding detector availability.

No live microphone, real provider call or group-quality benchmark was performed
by this automated integration run. Existing reported microphone/photo trials are
historical evidence. The full new group trial, exports omitted from command
documents, private-key/model setup, separate synthesis and missing paths are
spelled out in COMPLETE-LOCAL-TEST.md. Real photo reading remains explicitly
selected by its separate launcher, and the standard launcher uses a labelled
photo fixture. Secrets and private sessions remain local.
