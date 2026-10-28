# Backend work, cut into chunks

## Current team priorities, 14 October 2026

Start with [the team plan](../docs/team-plan.md) for the four current packages,
owners, dependencies and the shared localhost delivery. The 5 October list
below is a historical technical snapshot, not the current priority order.
In particular, real local transcription now runs in the integrated localhost
prototype; see [LOCAL-FEATURES.md](../LOCAL-FEATURES.md) and the latest
[build evidence](../app/server/BUILD-STATUS.md). Check old open items against
current code before starting them.

## Start here: what is actually open, 5 October 2026

The 16 September warning that this list overstated its open work is resolved.
Every unticked item was checked against the code and tests on 5 October. Items
that were done got a dated evidence note naming the tests; items with any clause
missing stayed open. 113 open boxes became 81, and seven of those are the
reusable completion checklist, not work. One tick was wrong: J02/INT04, because
`1e999` still returned HTTP 500. That is now fixed. Several entries were
duplicates of later ticks, and they now point to those ticks. The sections below are kept as history. Plan from this list.

**Small code work an agent can do without a decision.** Each is a test, or a
test plus a small guard.

- Untested caps: `session_capacity`, `participant_capacity`,
  `invitation_capacity`, `request_capacity` (H03). A heartbeat actually extends
  the lease (H03).
- Lifecycle tests: a viewer can pause (E03); activate, heartbeat and join are
  refused after close (E05); withdrawal cancels jobs (A08); consent ignores a
  supplied `actor_id` (A06); a removed actor's `author_id` survives on records
  (A04); withdraw and remove still work at caps (E06); repeated sweeps write one
  `lease_expired` event (E02).
- Overlapping edit, undo and cancel under barriers, with no duplicate events (H05).
- Media and crop from the wrong session (D04); a non-author adding a full-image
  region to someone else's photo, with a mutant (D05).
- Extraction contract: missing and duplicate region IDs, source text that tries
  to issue instructions, and a version on the adapter output schema (F03).
- A write during a snapshot read (C04); a route-by-role matrix (J04).
- Deterministic export bytes and filenames (I05); reasons for omitted records (I03).
- ~~The client never calls `setVisibility`/`setOnline`~~ Done 6 October:
  `app/client/app.mjs` binds both to the page's visibility and connectivity
  events (G04). Sleep and real backgrounding on a phone are still untested (INT05).
- The instance lock is untested (L01); `/ready` does not report migration or
  fixture-versus-live capability (L03).

**Needs a group decision first.** Code before the decision would be a guess.

- F01: what decisions, actions and questions are as records, including dissent,
  unknown owners and supersession. This is the meeting-minutes half of the product.
- INT07 (client): whether a reload may keep credentials, and where.
- Retention: how long deletion receipts, versions and events are kept (K03, K06).
- Provider and budget before any paid OCR or speech call (F04, INT10).
- Whether an evidence bundle is ever released beside the output-only export (I02).
- Whether writing back to an external board is in scope at all (I06).

**Needs devices, hardware or people.** No amount of code closes these.

- A real phone and a shared screen on the intended network (INT06, L05).
- Any number from a machine other than the development container (INT09, L04, L06).
- A held-out wall, transcribed by hand, run through the tool with corrections
  counted (F05, M03, M04, INT11). `gaps.md` G4 calls this the cheapest change
  to the project's evidence.
- A first real speech-to-text run. On 5 October the cloud container's network
  policy refused `huggingface.co`, so `LocalWhisperTranscriber` has still never
  run. It needs that host allowed, or a team laptop.

> Current integration: H and B/C landed through PRs #12 and #14. PR #13 adds
> A/E/D. The older defect descriptions below are historical context; consult
> the appended INT01-INT13 concerns, coverage matrix and build status for
> remaining work and the combined verification evidence.

At the original review baseline, the backend at `app/server` ran with 56
passing tests. That historical baseline implemented the review
and consent spine well: optimistic concurrency, idempotency, worker
re-validation and restart recovery all held up under concurrent and SIGKILL
testing. What follows is what it does not do, cut so two people can work at once
without fighting over the same file.

The original findings below were reproduced during the earlier review. The expanded
delivery contract distinguishes later reproductions from inspection concerns and
planned requirements; neither a task nor a passing test count proves readiness.

## Inventory after H/B/C, with integrated A/E/D

Reviewed main `0fe7b083007f0656b654034d88bcfc1330eacbc4` plus PR #13's
combined candidate. The PR records the resulting merge commit for final readback.

| Area | Present in the combined backend | Still requires evidence or implementation |
| --- | --- | --- |
| H: invariants | Portable named refusal guards retained alongside new guards | Human review, CI and operational fault exercises |
| A: lifecycle | Independent invitation redemption, consent/roster revisions, stale activation refusal, bounded stop controls | Real-device joining, client controls, recovery and legacy credential provenance |
| B: board | Canonical positions, independent position revisions and atomic moves | Collision policy and larger forms/clusters |
| C: sync | Transaction write descriptors, delta reads, gzip and keep-alive | Positioned-board 5 KiB target, concurrent pagination and bounded cascade/resync |
| D: media | Pixel decoding, orientation, sanitisation, authorised crops, immutable deduplication | Live-room fidelity, visible-identity handling and independent evidence bundles |
| E: execution | Killable fixture worker, deadlines/cancellation, bounded queues and completed-result cache | Crash-durable provider reconciliation, paid-call limits and actual OCR quality |
| Clients/operations | CLI and JavaScript mechanism clients; Swift core with explicit uncompiled status | Connected browser app, Swift compilation, phones, deployment and CI |

Combined evidence: 164 tests passed, 13 focused sync tests passed after the final
transport assertion adjustment, and all 64 named guard mutants were caught.
The positioned benchmark intentionally reports a failing budget. Bash audit
remains unavailable on this Windows environment. These are mechanism checks,
not a product-readiness certificate. Requirements below retain their original
IDs; the appended INT concerns state the remaining acceptance work.

## Who takes what, and why

Almost every chunk touches `genai_server/service.py`, so splitting by topic
would put both parties in the same functions. The split is by **table** instead,
which gives a real seam.

**Codex owns the session and actor half:** who is in a session, what state it is
in, and what is allowed to enter it. It wrote this code.

**Claude owns the record and event half:** what is on the canvas, and how
clients hear about it.

`service.py` is 642 lines and both halves live in it. The seam is real but it is
not a file boundary, so whoever lands second will merge.

## Sequencing

1. **H lands first and alone.** It touches no production code and it blocks
   nobody, and both halves rewrite logic the current suite cannot protect.
2. Then **A, D, E** (Codex) and **B, C** (Claude) run in parallel.
3. **F and G wait.** F is the largest and is where a native client pays off.

---

## H. Test safety net (Claude), done

**Why first.** Four injected mutations left all 45 tests green, including
deleting the credential check on the deletion receipt and the guard that stops
the last facilitator demoting themselves out of the session. `job.cancel` and
`session.heartbeat` appear zero times in either test file. Any chunk below
rewrites logic the suite does not currently protect.

`tests/mutation_check.py` is the acceptance criterion: it removes one guard at a
time and reports any whose removal the suite does not notice.

**Done when** `python3 tests/mutation_check.py` exits 0, and any guard added
later comes with a mutant in the same commit.

**Done.** `tests/test_guards.py` holds one test per mutant and the harness exits
0. Three of the ten tests passed against the mutated source on the first
attempt and had to be rewritten, which is worth knowing before you write the
next one: lowering a cap on the instance shadows the class constant a mutant
edits, and asserting that a job ends `failed` proves nothing when both branches
fail it. The rule that came out of it: watch each new test go red before
believing it.

---

## A. Identity and consent (Codex)

- `participant.invite` takes the invitee's bearer token **from the facilitator**,
  so one person mints, transmits and retains every attendee's credential and can
  send `consent.acknowledge` on their behalf. The F6.1 consent log therefore
  proves only that whoever held the token acknowledged. Replace with a join code
  the participant's own client redeems for a token it generates.
- **No `participant.remove` exists**, so a credential cannot be revoked.
  Demoting to viewer keeps full read access. Add it: deleting the `actors` row
  invalidates the token, because `_auth` joins on it.
- `consent.withdraw` does not exist, and `members[]` carries a version integer
  with no `agreed_at`.
- The server refuses to bind anything but loopback and `client.mjs` refuses
  non-loopback URLs, so **a phone cannot reach it**, which is F1.4's premise.
  Add a bind-address option.

**Done when** a participant's credential never exists on the facilitator's
device, someone who leaves can be cut off, and a phone on the same network can
reach the server.

## D. Image safety and evidence (Codex)

- Images are stored and served **verbatim**, so EXIF and GPS survive, and
  `media()` calls only `_auth` with **no role check**, so any viewer can
  download every original photograph for the session's life.
- Validation checks signature, header dimensions and size only. A PNG with a
  megabyte of arbitrary bytes after `IEND` passes and is served back as
  `image/png`.
- `_save` writes the full record JSON **including image base64** into `versions`
  on every revision, while the image quota counts current sources only. Measured:
  one 1 MiB image plus 8 region edits produced 12.5 MB in `versions` while the
  quota still read 1 MB.
- There is no crop endpoint, so the review queue must fetch a 2 MB photograph
  per note and composite the crop client-side.

**Done when** a photo's GPS never survives intake, `media` is author-or-
facilitator, and the review screen fetches a crop.

## E. Session lifecycle (Codex)

Higher priority than it looks: this is what users hit in normal use, not under
stress.

- **`_revoke` is one blunt instrument fired by three unrelated events.** A missed
  heartbeat, a roster change and an invite all bump `policy_version`, invalidate
  every acknowledgement and stale every pending proposal. So a facilitator who
  steps out for six minutes returns to a paused session where all eight people
  must re-read the agreement, and **inviting one latecomer stops the meeting**.
  Split it: a lease expiry should pause capture and cancel in-flight jobs, and
  must not touch consent or proposals.
- `session.pause` is **not idempotent** and has **no role check**: five calls
  from a viewer took `policy_version` from 2 to 7. It also bypasses both the
  request cap and the storage budget.
- `session.close` is **irreversible and unguarded**. A facilitator on a stale
  view ends the meeting for everyone with no conflict detection.
- Roster commands have **no optimistic concurrency**: two facilitators editing
  roles silently lose one another's updates with no 409.
- `export.create` is refused by exactly the capacity errors whose stated remedy
  is "export or delete", because it is not in `CONTROL_COMMANDS`.

**Done when** a latecomer joining does not stop the meeting, a facilitator
stepping out does not reset the room, and export works at the cap.

## B. Position model (Claude), core done

The biggest frontend blocker, and worse than the missing transcription because
transcription is honestly declared absent whereas placement looks present.

- **An item has no position.** Coordinates live only inside accepted `placement`
  items. Reproduced: two contradictory placements for the same two items, both
  `status: accepted`, one at (0,0) and one at (500,500), with no field ordering
  them. The API cannot answer "where is this item".
- Moving an item costs **a new proposal, a facilitator decision and two
  records**, and a participant **cannot commit their own drag**.
  `spec/canvas-layout.md` says the item lands where it was dropped.
- **Editing a note's text stales its position**, so correcting a bad read knocks
  the item out of the layout.
- No clusters, hulls, forms, size, z-order or board extent.

**Done when** "where is item X" has exactly one answer and a participant can
move their own note without review.

**Done**, both of them. Position lives in a `positions` table, one row per
record, and `item.place` moves one to 60 records atomically with no review.
Clusters, hulls and forms are not done; they are B06 and were always staged
after basic positions.

## C. Event fidelity and sync (Claude), core done

- `_result_ids` only extracts an id when the handler returns a record, so
  **accept, edit, correct and undo emit events naming no records**. A client
  cannot refetch what changed and must reload everything: measured 427 KB at the
  record ceiling, p95 654 ms at seven clients, which is outside the sub-second
  budget on transport alone.
- The transitive invalidation cascade emits **no event of its own**.
- No delta snapshot, no gzip, HTTP/1.0 so no keep-alive.

**Done when** accepting a proposal moves under 5 KB to each connected client.

**Done**, measured rather than asserted: 1613 B gzipped per client at 41
records and 1623 B at 965, against 402513 B to reload the session at the
ceiling. `tests/measure_sync.py` reproduces it.

## F. Capture domain (later)

No transcript, segment, speaker, decision, action or question record kinds. No
confidence or colour anywhere, though the exemplars show percentages and F1.5
makes colour the grouping signal. **Add confidence and colour to the extraction
contract now**, while the only implementation is a fixture and the contract is
free to change.

## G. Client library (later)

`client.mjs` has no timeouts, no `AbortSignal`, no event-subscription helper, no
heartbeat ticker and no types. Every screen would otherwise rewrite the same
glue.

---

## Before touching any of this

`app/server/API.md` contradicts the live payloads in **nine places**. Shape code
against the running server:

```sh
cd app/server && python3 -m genai_server --port 8801 --data-dir /tmp/x
```

Four confirmed: proposals carry `status` not `state`; the snapshot key is
`members` not `actors`; an unknown field returns **422** where the docs say 400;
and `participant.invite` bumps `policy_version`, so the documented flow of
acknowledge, invite, activate cannot succeed.

Update `AGENTS.md`'s backend section when a chunk lands, or it becomes the stale
instruction file it warns about.

---

## Expanded delivery contract, 16 September 2026

This section extends A through H without reassigning their owners. I through M
make cross-cutting work explicit; their owners are **unassigned** until agreed.
Adding a task does not authorise starting every extension at once. The first
pilot remains typed/photo capture, human review, arrangement, export and deletion.
All checkboxes are open requirements, not completed work.

### Evidence and confidence

Baseline: main `3c0e3b5aec97fcab4b4e65f0524f30d315fead4d`. Its 45 tests
passed, but all ten supplied mutations survived in a scratch copy: receipt
credential, last facilitator, record cap, image-byte cap, duplicate reference,
terminal cancellation, pagination, purge verification, recovery-attempt cap and
adapter change. Mutations were unchanged; the subprocess environment was adapted
for Windows. Rerun against the exact candidate SHA; these are historical results.

Seven additional synthetic probes confirmed these groups of behaviour:

| ID | Reproduced result | Follow-up |
|---|---|---|
| R1 | Rejecting the job-success event write strands a job in running even after the store fault is removed | E07 |
| R2 | A blocked adapter remains running after 61 seconds and a maintenance sweep | E08 |
| R3 | Failed purge of an expired session blocks a snapshot of another unexpired session | E09 |
| R4 | Lone Unicode surrogate and numeric overflow return HTTP 500; placement id as a list raises TypeError | J02 |
| R5 | Mixed export contains two records but manifest.included lists one; typed source evidence is absent | I01/I02 |
| R6 | Twelve fresh heartbeats append twelve retry rows despite request and content caps | E06 |

The seven probes include six domain probes and an additional HTTP probe for R4.
A passing reproduction confirms a defect, not product acceptance. Store faults
used temporary SQLite triggers, not a physically full disk. Fair scheduling,
billing after cancellation and tombstone growth below are inspection concerns,
not measured failures. No live provider, phone, Swift build or user study was tested.

### Delivery order

| Stage | Work | Dependency / evidence |
|---|---|---|
| 0 | H | Before production refactors; intended behavioural mutations caught |
| 1 | A/E and B/C | Existing parallel ownership; coordinate shared schema/service changes |
| 1 | J contract foundation; K migration design | Agree interfaces before incompatible writes |
| 2 | D | A access rules and K migration; sanitised media and authorised crops |
| 2 | I | C snapshot semantics, D evidence policy and E resource rules |
| 2 | G minimum integration support; L local/LAN readiness | Stable A/E/C/J contracts; device claims separately tested |
| 3 | M manual/fixture pilot | Earlier pilot requirements demonstrated |
| Later | F, larger forms and remote deployment | Explicit scope choice, pilot evidence and provider readiness |

### H. Test safety net, expanded (Claude)

- [x] **H01** Protect all ten supplied mutants with relevant behavioural assertions. Confirm guard removal changes the intended assertion, not merely syntax/import success. *Done. Each mutant names the test that must fail, and the harness reports `CAUGHT BY THE WRONG TEST` when some other test goes red instead, which is a kill by accident. That check was itself verified by pointing a mutant at the wrong test and watching the harness exit 1.*
- [x] **H02** *Verified against the code on 5 October 2026: `tests/mutation_runner.py` runs in a scratch copy with the inherited environment, `-B`, a timeout, and refuses an error as a kill; `test_source_is_copied_and_runtime_environment_is_preserved`, `test_import_error_is_not_a_behavioural_kill`, `test_timeout_does_not_mutate_original_source`. The JavaScript path has no self-test of its own.* Make the runner portable and isolated: preserve required environment, use scratch source/databases, prevent stale bytecode, impose timeouts and restore files on interruption. Infrastructure failure must not count as a caught mutant. *Open, and the interruption case is real: the harness mutates `service.py` in place and restores in a `finally`, which a killed process never reaches. It happened once. Recovery is `git checkout app/server/genai_server/service.py` plus deleting `service.py.mutation-backup`. Mutating a scratch copy of the tree would remove the failure mode instead of documenting it. The env is pinned to `PATH=/usr/bin:/bin`, which is not portable to Windows.*
- [ ] **H03** Cover cancellation, heartbeat renewal/expiry, wrong receipt credentials, last-facilitator transitions, pagination boundaries, all quotas and recovery-attempt limits. *Partly: all but heartbeat renewal/expiry and the session-byte quota are covered by `tests/test_guards.py`.*
- [x] **H04** Add a mutant with every new guard. Refactored patterns must fail loudly when unmatched, and be updated rather than silently removed. *Mechanism done: every `old` must match `service.py` exactly once and the harness refuses to run otherwise. The habit is a rule in `AGENTS.md`, which no tool can enforce.*
- [ ] **H05** Use controlled barriers for overlapping accept/edit/undo/cancel/remove operations; assert valid outcomes and no duplicate records/events.
- [ ] **H06** Record fixtures, clock, commands, runtime and candidate SHA. Separate mechanism tests from AI-quality and user-benefit evidence.

**Done:** baseline and mutation checker pass, and every intended mutation is
caught for its behavioural reason. H is not certification of all future work.

### A. Identity and consent, expanded (Codex)

- [x] **A01** *Verified against the code on 5 October 2026: `_invite` and `join`; `test_legacy_invitation_credential_payload_is_rejected`, `test_expired_invitation_creates_no_member`, `test_join_retry_is_bound_to_exact_credential_and_payload`, and the HTTP join test.* Replace facilitator-supplied bearer tokens with single-use expiring invitations. Participant clients generate and submit their own credential directly. Explicitly reject the old sharing payload.
- [x] **A02** *Verified against the code on 5 October 2026: `test_invitation_is_scoped_to_its_session`, `test_concurrent_redemption_has_one_member`, expiry, revocation, consumption and changed-payload tests.* Redeem atomically; test expiry, revocation, wrong session, consumption, concurrent redemption and changed retry payload. Same-intent retry returns the same membership; another credential cannot recover it.
- [ ] **A03** Keep credentials out of facilitator-visible output, members, events, exports and logs. Persist hashes; define invitation replay without storing a reusable plaintext capability in a generic retry cache.
- [ ] **A04** Add participant.remove. Revoke reads, writes, media/crops and cached replay immediately; recheck worker authority before commit. Retain historical actor IDs as provenance.
- [x] **A05** *Verified against the code on 5 October 2026: `test_last_facilitator_cannot_be_removed`, `test_the_only_facilitator_cannot_demote_themselves`, `test_stale_roster_action_has_no_effect`, `test_concurrent_roster_writes_have_one_winner`.* Protect the last facilitator on removal/demotion. Administrative changes require expected roster revisions; simultaneous stale changes return 409.
- [ ] **A06** Add agreed_at, withdrawn_at and acknowledged policy version. Consent commands target the authenticated actor, never a supplied actor ID. Retries must not fabricate new consent transitions.
- [x] **A07** *Verified against the code on 5 October 2026: `test_invitation_and_join_preserve_active_room`, `test_join_requires_current_policy`. No command changes the policy version mid-session, so "stale policy" is tested as a version mismatch only.* Pending invitations are not admitted members. Active-session admission includes current-policy acknowledgement; stale policy requires fresh agreement. A late invitation must not interrupt existing work.
- [ ] **A08** Withdrawal pauses capture and cancels capture jobs while preserving other members' acknowledgement. Define reactivation and subsequent departure explicitly.
- [x] **A09** *Verified against the code on 5 October 2026: loopback default in `__main__.py`; `test_local_only_binding`, `test_lan_host_configuration_remains_exact`, `test_dns_rebinding_host_rejected`, `test_allowed_origin_and_preflight`. A real phone is INT06, still open.* Keep loopback default and add explicit LAN bind/advertised hosts. Preserve exact Host/Origin checks under 0.0.0.0. Permit configured client origins without embedded credentials/path/query/fragment.
- [x] **A10** *Verified against the code on 5 October 2026: no recovery, stated in API.md; `test_lost_credentials_cannot_be_reset_by_reusing_name_or_session_id`, `test_remaining_facilitator_can_reinvite_without_inheriting_agreement`.* Define lost-credential recovery or its absence. Device-mediated acknowledgement is not proof of real identity: a join code alone cannot stop deliberate self-redemption by a facilitator.

**Done:** normal joining never gives the facilitator the participant credential;
removed actors fail at every boundary. Demonstrate phone connectivity separately
from socket binding. Plain LAN HTTP is not encrypted remote deployment.

### E. Session lifecycle and recovery, expanded (Codex)

- [ ] **E01** Define distinct transitions for invitation, admission, role change, explicit pause, lease expiry, withdrawal and close, with named effects on jobs, agreement and proposals.
- [ ] **E02** Lease expiry pauses/cancels once without changing policy, acknowledgement timestamps or proposal revisions. Heartbeat renewal never reactivates capture.
- [ ] **E03** Repeated pause is a state-preserving no-op. Preserve the product decision that every authenticated member, including a viewer, may stop capture. Missing facilitator-only restriction is not itself a defect; repeated policy/history mutation is.
- [ ] **E04** Separate session, roster and event revisions. Noisy heartbeat counters must not cause administrator conflicts. Stale close/roster actions fail without side effects.
- [ ] **E05** Keep close terminal unless reopening is explicitly designed. Specify closed-session allowed operations and retry semantics; reconnect must not revive recording.
- [ ] **E06** Bound control storage: coalesce lease writes/no-ops and define replay retention/resync. Preserve pause/withdraw/remove/close/delete at caps. Test long sequences of fresh intents, not only one request.
- [x] **E07** *Verified against the code on 5 October 2026: `pending_completions` and deadline reconciliation in `sweep`; `test_completion_store_recovers_without_another_extraction`, `test_complete_store_outage_still_retains_result_for_recovery`, `test_maintenance_expires_running_jobs_without_callback`. Crash durability is INT10.* Recover stranded running jobs in-process after completion-store failure. Prefer expiring claims and reconciliation over a new queue service now. Replaying a captured result differs from repeating a paid call.
- [ ] **E08** Reconcile deadlines independently of callbacks. Add connect/read/total timeouts and killable isolation where needed. A future timeout does not stop its underlying thread. Another session must progress after an adapter hangs.
- [x] **E09** *Verified against the code on 5 October 2026: per-session try/except in `sweep`; `test_one_failed_purge_does_not_block_another_session`. Faults are SQLite-injected only.* Isolate purge failures per session. Expired content stays inaccessible; safe failure state and retries remain visible while unrelated sessions operate.
- [x] **E10** *Verified against the code on 5 October 2026: `test_failed_claim_is_atomic_and_can_retry`, `test_rollback_does_not_publish_ghost_record_descriptors`, `test_lost_completion_acknowledgement_does_not_duplicate_results`, `test_real_process_exit_after_provider_success_requires_acknowledged_retry`. Faults are synthetic.* Inject failures before/after claim, during proposal/event writes and after commit before acknowledgement. Assert bounded retries, no partial/duplicate effects and recovery both with and without restart.
- [ ] **E11** Test multi-session fairness, queue saturation and cancellation priority. Define per-session/instance limits and backpressure; measure queue age before claiming acceptable throughput.
- [ ] **E12** Export must work at logical caps through a bounded reserve or snapshot streaming agreed with I. Unlimited control exemption alone is insufficient. Physical write failure needs an honest recoverable error.

**Done:** attendance changes do not reset the room, stop actions remain available,
jobs recover while the process stays alive, and one session's failure is isolated.

### D. Image safety and evidence, expanded (Codex)

- [x] **D01** *Verified against the code on 5 October 2026: `media.sanitise`; `test_intake_strips_metadata_and_appended_bytes`, `test_clean_pixels_do_not_carry_exif_or_appended_sentinels`, the size and dimension limit tests, `test_valid_crc_does_not_substitute_for_pixel_decoding`. The GPS sentinel is an EXIF text tag, not a real GPS block.* Fully decode/re-encode PNG/JPEG offline from pixels. Remove EXIF/GPS/comments/appended bytes. Bound compressed/output bytes, pixels and dimensions; reject corruption, decompression abuse and unsupported multiframe content.
- [ ] **D02** Apply orientation before defining crop coordinates. Return sanitised dimensions and define alpha/colour-profile conversion. Test rotated photographs against intended evidence.
- [x] **D03** *Verified against the code on 5 October 2026: stored once per session by digest; `test_region_history_and_duplicates_store_one_media_payload`, `test_the_image_budget_can_actually_bind`.* Store immutable sanitised media once, referenced by source versions. Account for media, histories and caches; repeated region edits must not multiply image payloads.
- [ ] **D04** Full images are author-or-facilitator under current authority. Test viewer, unrelated participant, removed/demoted actor, wrong session and historical access.
- [ ] **D05** Add bounded crop access naming source, revision and region. Define reviewer access. Arbitrary rectangles or a user-created full-image region must not bypass original-image restrictions.
- [x] **D06** *Verified against the code on 5 October 2026: `db._migrate_media`; `test_legacy_originals_are_removed_from_history_and_retry_results`, `test_invalid_legacy_bytes_are_unavailable_and_not_retained`, `test_interrupted_media_migration_rolls_back_and_restarts`.* Migrate existing images, including originals embedded in versions/cache. Define invalid-legacy-data handling and transaction/restart behaviour. Old endpoints must not keep serving unsanitised originals.
- [ ] **D07** Include media/crop caches in retention/purge verification. Test orphan cleanup, duplicate media, interruption and deletion while a crop is prepared.
- [x] **D08** *Verified against the code on 5 October 2026: `test_unreadable_crop_requires_human_transcription` keeps fixture origin after a human edit; the export manifest states no redaction, checked in `test_output_release_opens_after_delete_and_manifest_matches_in_both_modes`.* Preserve provenance through human correction. Re-encoding does not anonymise visible names, faces or handwriting.

**Done:** metadata/sentinels do not survive stored/served bytes, history does not
duplicate images, and clients fetch authorised revision-correct crops. Depends on K.

### B. Position model, expanded (Claude)

- [x] **B01** One authoritative position and explicit position revision per item; reconcile contradictory legacy placements. *Position and its own revision counter live in a `positions` table keyed by record. Schema 1 to 2 folds accepted placement items in on open, in rowid order so the last accepted arrangement wins, and marks them superseded rather than deleting the evidence.*
- [x] **B02** Permit authorised participant movement without content acceptance. Define ownership for accepted machine-origin notes; test stale and simultaneous drags. *Any editor moves any item or proposal, no review, and the mover is recorded. Ownership is `hand_placed` per `spec/canvas-layout.md`: a person creating, dragging, accepting or editing makes it theirs permanently, and a `machine` placement onto it is refused 409. Stale drags are 409 `stale_position` carrying the current revision.*
- [x] **B03** Separate geometry/content revision semantics so spelling corrections preserve position while genuine structural dependencies still invalidate. *Two counters, never mixed. A move writes no record, so it bumps no revision and stales nothing. A text edit invalidates dependent relationships as before and leaves the position untouched.*
- [x] **B04** Define atomic multi-item moves, undo conflicts, z-order ties, board extent and bounded coordinates/sizes. Undo cannot erase somebody else's later movement. *One command, up to 60 records, validated in full before anything is written. Undo restores text only, because position is not versioned. `board_order` is model-placed, then hand-placed, then most recently touched, ties on record id. Coordinates bounded to ±100000. No size is stored: `spec/canvas-layout.md` derives item width from text length in three steps, so a stored size would be a second answer to a question the text already answers.*
- [~] **B05** Preview automatic layouts, preserve provenance/content and enforce collision/visibility rules; distinguish generated and manual geometry. *Done on the server's side of the line, and the rest is blocked on a decision rather than on effort. Generated and manual geometry are distinguished by `origin` and `hand_placed`; a placement preview goes through review and never touches the content it arranges; a `machine` placement onto a hand-placed record is refused, which is the rule that protects a person's work. Collision and visibility, §4, are not enforced and cannot be without storing a rendered box per item: width follows from text length in three steps, but height follows from wrapping, which is a rendering fact the server does not have. That spec's own first paragraph puts the layout engine in the client. Whoever picks this up is choosing to store geometry, which reverses the B04 decision not to; the cost is a second answer to a question the text already half answers.*
- [x] **B06** Stage clusters/hulls/forms after basic positions; specify membership, empty groups and delete/undo behaviour. *Clusters only; timeline, flow, hierarchy and matrix are refused, not stubbed. A cluster is a `relationship` proposal with `form: cluster`, so it goes through review: a grouping is a claim about meaning, and a direct-write command would have exempted the model's groupings from the rule the product turns on. Membership is by reference, so two clients cannot disagree about who is in a group; the hull is drawn client-side and never stored. `cluster.membership` moves items with no review, like `item.place`. Capped at 24, where the spec says it stops being a form; the 9-item reading threshold is left to the layout engine, because refusing a person's grouping of twelve is the server arguing with the person holding the pen. Two things the spec does not settle, decided and argued in API.md: an item is in at most one cluster, because a hull 12px outside its members cannot give 24px clearance to an item inside another hull; and emptying a cluster undoes it rather than deleting it, because what the meeting grouped is evidence.*

**Done:** current position has exactly one answer; moving content never implies
agreement with its meaning.

### C. Event fidelity and sync, expanded (Claude)

- [x] **C01** Emit complete changed IDs/revisions for commands, cascades, jobs and lifecycle. State/events commit atomically. *Collected on the transaction as writes happen, so a handler cannot forget. Events carry `records` as `{id, kind, revision}`, plus `state` and `policy_version` on every event. Same transaction as the write, so state and event commit together.*
- [x] **C02** Define cursor order, duplicate handling, pagination, gaps, future/invalid cursors, retention and full resync. *`?since_seq=N` reads records and cursor in one transaction. `since_seq=0` is a full resync, so there is one code path. A future cursor is 409 `cursor_ahead` carrying `current_seq`. Retention is untouched, because nothing prunes events yet: that is the honest gap, and a session that ran long enough to want pruning would hit the storage budget first.* Snapshot and cursor must describe one consistent point.
- [x] **C03** *Verified against the code on 5 October 2026: `test_removed_actor_loses_every_read_and_cached_command`, `test_demotion_rechecks_cached_mutations_and_evidence_authority`, `test_demoted_facilitator_cannot_replay_export_or_read_its_history`. The italic note on this line saying removal does not exist is out of date.* Targeted deltas/refetch respect changed authority during replay/subscription; removed actors cannot keep receiving records. *Partly: every delta re-authenticates, so a role change applies immediately. Removal cannot be honoured because `participant.remove` does not exist yet, which is A04. The idempotency cache also still replays a stored result to its original author regardless of later authority.*
- [ ] **C04** Test writes during snapshot/pagination and large invalidation cascades, with no missed changes or resurrected content. *Cascades are covered by `tests/test_sync.py`. Concurrent writes during pagination are not tested: `BEGIN IMMEDIATE` makes each read atomic, but that is an argument, not a test.*
- [x] **C05** Evaluate compression/persistent transport with framing, limits, bounded buffering and slow clients; optimisation must not weaken validation. *gzip above 1 KiB when asked for, HTTP/1.1 keep-alive. Keep-alive needed a body drain: a 404 on a POST left its body to be parsed as the next request. Slow clients are bounded by the existing 10 second socket timeout and 16 slots, not by anything new. No validation was relaxed.*
- [x] **C06** *Verified against the code on 5 October 2026: `tests/measure_sync.py` reports named fixtures, compressed and raw bytes and recipients, and exits non-zero over budget; POSITIONED measured 1667 B a client in this container.* Measure the under-5-KB target as event plus required refetch for a named representative acceptance fixture. State compressed/uncompressed bytes, recipients, cascade size and latency separately; define a bound/resync policy for larger cascades. *Partly demonstrated by WALL-12 and CEILING; reopened as a complete requirement because no cascade bound/resync switch is enforced, and those fixtures do not position their notes. The integration review measured a one-record change on POSITIONED-400 at 8613 gzip bytes for the delta alone; see INT13. Preserve the earlier measurements as fixture-specific evidence, not a general flat-cost claim.*

**Done:** representative acceptance meets its measured budget and clients recover
from gaps while observing every relevant invalidation.

### F. Capture domain and providers, expanded (later)

- [ ] **F01** Define transcript/segment/speaker/decision/action/question lifecycles, source spans, correction, dissent, unknown owners/dates and supersession.
- [x] **F02** *Done 5 October 2026: optional, nullable `confidence` (0 to 1, model-specific) and `colour` (sRGB hex with a named source) on extraction notes, validated, carried to the item, confidence cleared when a person retypes the text. The fixture sends null for both. No database migration: records are JSON, so the "explicit schema revision" is the API contract in API.md, not `SCHEMA_VERSIONS`. Five tests in `test_guards.py`, three mutants.* Add optional confidence/colour at an explicit schema revision. Confidence is nullable/model-specific, never acceptance authority; colour has a source/space definition. Do not fabricate either in fixtures.
- [ ] **F03** Version prompts/adapters/output schemas. Require region coverage or explicit unreadable/missing results; test extra/duplicate IDs and source content trying to issue instructions.
- [ ] **F04** Before live calls, specify timeout/retry/cancellation/budget/idempotency. Record incurred or unknown cost when output is discarded; cancelled paid work is not automatically free.
- [ ] **F05** Evaluate held-out walls and abstention before audio expansion. Audio needs separate gap/overlap/identity/withdrawal evidence.

**Done:** each enabled capability has fidelity, cost and failure evidence.
Schema preparation does not authorise live capture or all domain extensions.

### G. Client library, expanded (minimum integration first)

- [ ] **G01** Types and executable contract fixtures, including unknown enums and errors; supported clients actually compiled/tested. Swift remains unverified until built.
- [x] **G02** *Verified against the code on 5 October 2026: `client.mjs` intents and deadlines, with the transport unit tests for uncertain retry, body-decoding timeout, in-flight cancellation and foreign intents.* Timeout/AbortSignal with uncertain-outcome semantics; client abort is not proof of server rollback. Preserve immutable retry intent.
- [x] **G03** *Verified against the code on 5 October 2026: `session-sync.mjs`, with unit tests for bounded backoff, truncated deltas, cascade resync, terminal state and deleted snapshots.* Bounded subscription/reconnect, cursor retention, deduplication, resync and teardown. Revocation must stop automatic retry.
- [ ] **G04** Heartbeat lifecycle for background/sleep/offline; suspended timers cannot be assumed to run. Reconnect never silently reactivates capture.
- [ ] **G05** Credential storage/loss/join/revocation/deletion behaviour; no secrets in URLs/logs/exports; dispose media Blob URLs/caches.
- [ ] **G06** Exercise real-client join, agreement, intake, conflict, crop, reconnect, export, close and deletion with providers unavailable.

### I. Export integrity and evidence release (owner unassigned)

- [x] **I01** *Verified against the code on 5 October 2026: `_export` manifest; `test_output_release_opens_after_delete_and_manifest_matches_in_both_modes`.* Manifest enumerates every included ID/kind/revision. Assert exact manifest/payload set equality in all inclusion modes.
- [x] **I02** *Verified against the code on 5 October 2026: output-only chosen and logged in the decision log on 16 September; `release_kind` and `references_require_session` are tested by the same test after deletion. An evidence bundle stays a separate decision.* Choose output-only, evidence bundle or separate releases. Label server-dependent references; test opening after session deletion. Adding excerpts/crops is a release decision, not an automatic fix.
- [ ] **I03** Freeze inclusion/redaction before release. Distinguish unresolved questions from unreviewed claims; preserve stale/machine-origin labels and omission reasons.
- [ ] **I04** Coordinate bounded exports at logical caps with E. Define interrupted download, retention and authority after role changes/close.
- [ ] **I05** Verify Markdown escaping, JSON text, filenames and deterministic output. Do not claim initials anonymise free text; downloaded copies remain outside deletion.
- [ ] **I06** External board write-back waits for verified operation markers, read-back reconciliation and lost-acknowledgement/partial-success handling. Unknown outcomes cannot trigger blind duplicates.

**Done:** release inventory matches bytes and evidence-availability promises
remain true after the server session is deleted.

### J. API contracts and validation (owner unassigned)

- [ ] **J01** Reconcile prose with captured payloads: members/status, 422, invitation/version changes, command envelopes and error details. Keep examples executable.
- [x] **J02** *Done 5 October 2026. The 16 September tick below was premature: `1e999` is not the literal `Infinity`, parsed to inf and returned HTTP 500. Fixed in `parse_json` with a finite `parse_float`, and a `parse_int` that refuses integers too large for a float, which raised OverflowError in the region-box validator; `test_a_number_too_large_for_a_float_is_a_client_error` and `test_deeply_nested_json_is_a_client_error`, three mutants. Duplicate keys and oversized bodies were already tested in `test_http.py`.* Validate Unicode scalars, finite parsed numbers, ranges and nested types before hashing/set use. HTTP cases include lone surrogates, 1e999, list IDs, deep nesting, duplicate keys and oversized input; return specific client errors without state changes.
- [ ] **J03** Version compatibility for A/B/D and supported clients; reject obsolete semantics explicitly.
- [ ] **J04** Route/command role matrix includes unauthenticated, wrong-session, viewer, participant, facilitator, removed/demoted actors, histories, media, exports, cached replies and late callbacks.
- [ ] **J05** Define each concurrency token and retry guarantee. Validate error contracts; an error after durable commit must not falsely promise rollback.

**Done:** examples are tested and invalid client values do not escape as internal exceptions.

### K. Schema, storage and deletion (owner unassigned; needed by A/D)

- [x] **K01** *Verified against the code on 5 October 2026: `tests/test_schema_integrity.py` (17 tests, including `test_unknown_version_is_refused`, `test_all_published_and_interrupted_stages_restart`).* Ordered migrations with unsupported-version rejection; test empty/existing/partial/invalid legacy databases and interruption/restart.
- [x] **K02** *Verified against the code on 5 October 2026: `SCHEMA_VERSIONS` registry and `check_schema_versions.py` in CI. Backup recovery is described, not exercised.* Agree unique migration IDs across A/D and B/C. Describe rewritten/lost data and recovery options; preserve unrelated work.
- [ ] **K03** Account for media, versions, events, retries, exports and receipts at session/instance level. Define retention/compaction without silently breaking references or idempotency.
- [ ] **K04** Test write errors, locking, rollback and orphan cleanup. Logical quotas do not simulate physical disk recovery.
- [ ] **K05** Add every new store/cache to purge verification; expose incomplete deletion and retry. Backups/restoration/downloaded copies need separate policies.
- [ ] **K06** Bound tombstone/receipt retention while preventing late recreation, premature ID reuse and forgotten retry protection.

**Done:** migrations preserve intended evidence, deletion covers owned stores and
growth/recovery boundaries are explicit.

### L. Runtime, observability and deployment (owner unassigned)

- [ ] **L01** Offline runtime after installation; record supported platforms/dependencies, startup/shutdown and instance-lock behaviour. No hidden runtime asset fetches.
- [ ] **L02** Safe queue age/depth, quota, purge and migration diagnostics with correlation IDs but no credentials/source material.
- [ ] **L03** Distinguish health from readiness: writable store, completed migration, responsive worker and accurate fixture/live capability.
- [ ] **L04** Test clean shutdown and abrupt termination during claim/write/delete; document startup-recovery limits.
- [ ] **L05** LAN bind/Host/Origin/firewall/device checks and encryption limits. Public deployment separately requires a supported server, TLS, authentication, rate/resource controls and operational ownership.
- [ ] **L06** Measure concurrent latency/fairness/memory/disk with fixture/hardware stated; separate provider, queue and human-review waiting.

### M. Integration and product evidence (owner unassigned)

- [ ] **M01** Full manual journey covers independent join, agreement, capture, correction, review, movement, conflicts, reconnect, export, withdrawal/removal and deletion.
- [ ] **M02** Keyboard/touch access, clear provisional/stale labels, evidence beside claims, retained conflict edits and discoverable stop controls.
- [ ] **M03** Compare total effort and final fidelity against manual work: include setup, review, layout/export repair and failure recovery, not only extraction speed.
- [ ] **M04** Held-out sessions/walls, counterbalanced order, predeclared scoring, failures and denominators. Synthetic tests cannot substitute for user evaluation.
- [ ] **M05** Track implemented, mechanism-tested, integration-tested, device-tested and user-evaluated separately. One green column is not global verification.

### Common completion checklist

- [ ] Bounded failure/recovery behaviour for the stated contract.
- [ ] Authority, revision, retry, malformed input and rollback tests for every changed command.
- [ ] Async boundaries tested before/after claim, during execution, before commit and after commit before acknowledgement where relevant.
- [ ] Meaningful assertions and matching guard mutants verified against the integrated candidate.
- [ ] Repository audit, contrast, backend suite and mutation checks run; unavailable checks reported honestly.
- [ ] API/client compatibility, known-problems section of AGENTS.md and both traceability logs updated when behaviour actually lands.
- [ ] Current main incorporated; exact commands, SHA, results and limitations in the PR.

Planning may continue while H is pending. Production refactors retain H-first.
Merging this document does not mark its requirements implemented or tested.

## Post-integration concerns and follow-up tasks, 16 September 2026

These tasks append to the existing A-M list. Existing owners remain unchanged;
unassigned work is not automatically assigned by this inventory. Status is open
until the stated evidence is recorded. The A/E/D and B/C test counts were measured
on different branches and must not be added together as a combined pass.

### Before merging the combined backend

- [x] **INT01, K01/K02, integration gate:** *Superseded: the structural preflight landed and is ticked under "Assigned follow-up implementation". Backup and recovery remain open under the pilot entry below.* Reconcile the schema collision.
  B/C uses version 2 for positions; A/E/D uses version 2 for invitations, then
  versions 3/4 for media and control replay. Identify supported layouts from
  their tables/columns, reject unknown or incomplete layouts clearly, and
  migrate fresh, legacy v1, B/C v2 and A/E/D v2/v3/v4 databases into one
  documented schema. Verify records, independent credentials, positions,
  sanitised media, retry protection and deletion survive. Do not reinterpret a
  schema solely because its version integer matches. Published-history and restart
  fixtures now pass; broader damaged/partial-schema validation remains open.
- [x] **INT02, A04/C01-C04/J03/J04, integration gate:** *Superseded: ticked under "Assigned follow-up implementation". What remains is tracked in the pilot entry below.* Exercise joining,
  acceptance, movement, correction, pause, withdrawal and removal through
  full/delta snapshots and paginated events on the combined version. Recheck
  authority on removed/demoted clients and cached replies. Ensure transactional
  change tracking survives rollback and does not publish records that were never
  committed. Preserve source/content/position revision meanings.
- [~] **INT03, H02/H04/L01, integration gate:** *Harness half done: all five harnesses now share one runner, `tests/mutation_runner.py`, preserving every named mutation and their exact output, verified byte-identical before and after. 95 guards: 56 service, 12 schema, 10 runtime, 9 media, 8 isolation. Database and HTTP guards are covered by the service harness, which resolves a mutant to whichever of service.py, http.py or db.py holds it. The CLI and JavaScript journeys, and inspecting a merged tree for dropped files, are not done.* Preserve both sets of named
  guard mutations in the portable scratch runner, including database and HTTP
  guards. Run the combined suite, media/isolation guards, CLI and JavaScript
  journeys against one candidate. Confirm HTTP/1.1 body draining, bounded slots,
  gzip and connection reuse preserve A's Host/Origin/body checks. Repeat the
  sync measurement and report its fixture and byte accounting. Record the
  resulting main commit and inspect the merged tree for dropped files.

### Before a real-team pilot

- [x] **INT04, J02, confirmed validation defect:** *Closed 5 October 2026 with the overflow and depth tests; see J02.* A JSON session title
  containing a lone Unicode surrogate returned HTTP 500 on A/E/D candidate
  `3928eff5936c5cfeb6b6cc59e68fb3fef0ca3bd2`. Validate Unicode scalar strings
  and finite numbers before encoding/persistence; cover invalid nested ID
  types, overflow, depth and duplicate keys through HTTP. Completion evidence:
  specific client errors with unchanged state and named refusal tests.
- [ ] **INT05, G01-G06/M01/M02, client integration:** Update actual client
  consumers for independent join, session/roster/position revisions,
  actor-scoped control sequences, changed-record events and delta resync.
  Exercise simultaneous tabs, stale edits, lost acknowledgements, expired
  control replay, sleep/reconnect and credential revocation. Show a usable stop
  action and retained conflict edits. A Python/JavaScript mechanism test does
  not verify the browser UI or the uncompiled Swift decoder. Inventory of
  main `0fe7b083` found only `.gitkeep` under `app/client/`; the design-system
  exemplars are not a connected application.
- [ ] **INT06, A09/L05, device and transport:** Demonstrate independent joining,
  upload, stop and reconnect on a real phone and shared screen, including
  firewall/origin configuration. Loopback remains the default. Explicit LAN
  HTTP is unencrypted; choose and test a transport appropriate to the pilot
  before carrying real sensitive material. Public hosting requires a separate
  deployment review.
- [x] **INT07, A06/A10/G05, identity and recovery:** *Superseded: decided and ticked under "Assigned follow-up implementation". Reload behaviour in the client is a separate open row.* Document that invitation
  redemption proves control of a device credential, not a person's identity.
  Use fresh sessions to test the new independent-join flow; migrating old
  credentials cannot make previously shared tokens secret again. Decide lost
  facilitator-credential recovery versus explicitly unrecoverable sessions,
  with tests ensuring recovery cannot impersonate another participant's consent.
- [x] **INT08, I01-I05/D08, evidence release:** *Superseded: output-only chosen and ticked under "Assigned follow-up implementation". An evidence bundle needs its own decision.* Choose output-only export,
  a separately approved evidence bundle, or both. Current source references
  require the retained session and break after deletion. Test opening the
  intended release without that server, exact manifest inclusion, unresolved
  labels and explicit redaction. Metadata removal does not remove visible names
  or faces; downloaded copies remain outside server deletion.
- [ ] **INT09, L01/L03/L04/L06/K03-K06, operations:** Run the repository audit in
  a supported environment and establish repeatable CI. The Windows Bash
  signal-pipe failure is an unavailable check, not a pass. Exercise abrupt
  shutdown, physical storage failure/recovery, receipt growth, concurrent
  image/crop memory use, idle keep-alive slot pressure and queue latency on
  named hardware. Health should distinguish a listening socket from a writable
  store and responsive worker. No `.github/` workflow was present in the
  inspected main `0fe7b083` tree.

### Before enabling a live provider or expanding scope

- [ ] **INT10, E07/E08/F04/K04, crash and cost semantics:** Completed extraction
  results currently survive transient store faults in bounded memory but are
  not crash-durable. Choose durable result/claim reconciliation or explicitly
  require manual retry after uncertain outcomes. Test death after provider
  success but before durable commit. Define connect/read/total deadlines,
  provider idempotency, retry limits and known/unknown incurred cost; local
  process cancellation does not prove that an external paid call was cancelled.
- [ ] **INT11, F03/F05/M03-M05, value and fidelity:** Evaluate held-out walls,
  corrections, abstention and source coverage against manual work. Count setup,
  review, repair and export effort. Keep all fixture output labelled synthetic;
  current passing tests establish no OCR accuracy, savings or live-room value.
- [ ] **INT12, B05/B06/C04/C06, remaining board/sync work:** Keep collision
  rules, larger forms/clusters and large-cascade behaviour explicit. Test
  concurrent changes during delta pagination, define a bounded forced-resync
  policy, and prevent layout proposals from overwriting hand-placed work.
  Representative under-5-KB acceptance evidence does not bound every cascade.

- [x] **INT13, C06/L06, confirmed positioned-board delta growth:** *All four conditions met, see "Confirmed defects" below. Budget and ordering fixed, and the cascade bound has since landed; the authoritative entry is under "Confirmed defects" below. `board_order` is a pure function of positions the client already holds, so the delta no longer sends it; the snapshot still does. POSITIONED went from 8183 B to 1655 B per client, flat against WALL-12's 1649 B at 41 records. POSITIONED now runs by default and CEILING is the optional fixture, because a realistic fixture behind a flag is one nobody runs. Two tests, one comparing an identical edit at two board sizes so it asserts flatness rather than a number, one rebuilding the order client-side from deltas across a move and an edit. Original finding below.*
- [x] ~~**INT13 as reported:**~~ The combined
  pre-merge review seeded 400 accepted synthetic items with canonical positions,
  then changed one item's text. `delta` returned one changed record but all 400
  board-order IDs: 15260 JSON bytes and 8613 gzip bytes, excluding events and
  HTTP headers. The existing CEILING fixture fills records without positioning
  its notes and misses this dimension. The new `measure_sync.py --positioned` reproduces the gap with 321
  positioned items: 8308 bytes per client including events and HTTP headers,
  against 1665 bytes for the unpositioned fixture. Choose incremental ordering reconstructed from changed positions,
  or an explicit bounded full-resync policy, and verify the client's ordering
  after concurrent moves and content edits. Report this requirement partial
  until the intended populated-board budget is met or deliberately revised.

Detailed implementation evidence remains in
[the backend coverage matrix](../app/server/ADE-COVERAGE.md) and
[build status](../app/server/BUILD-STATUS.md). These follow-ups refine existing
requirements; they do not certify all H/K/L/M work or reopen already demonstrated
A/E/D mechanisms without a failing reproduction.

## Open issues after the main review, 16 September 2026

This is the current action queue for main
`6a85911905a58e7ffd1864af0a95ccfe4b7ca35a`, after H/B/C and A/E/D merged.
It refines the existing INT and A-M requirements rather than creating duplicate
issue IDs. Earlier "before merging" wording describes the historical integration
plan. Owners remain as assigned above; otherwise ownership is unassigned.

### Confirmed defects: address first

- [x] **J02 / INT04: reject malformed Unicode at the API boundary.** *Done. Two causes, neither in the validators. A lone surrogate survives `json.loads` and dies at the idempotency fingerprint, which encodes the whole body before any handler sees a field, so it is rejected across the whole body including keys: 400 `invalid_json`. An id of `[1]` reached a set membership test in `item.place` before validation, and a list is unhashable: `ident` now runs first, 422 `invalid_id`. Non-finite numbers were said to be already 400 and pinned by a test; that was only true of the literals `NaN` and `Infinity`. `1e999` still returned 500 until 5 October, see J02. Seven real-HTTP tests assert the refusal and that state is unchanged, one asserts accents, emoji and raw UTF-8 still work, and two mutants cover both guards.*
  Reproduced again on merged main: a lone-surrogate session title returns HTTP
  500 `internal_error`. Validate strings before encoding or persistence and
  return a specific client error. Extend coverage to the other J02 malformed
  inputs, including non-finite numbers and invalid nested ID types.
  **Complete when:** real HTTP tests show the expected client errors, no state
  changes and a named behavioural mutant that proves the new guard matters.
- [x] **C06 / INT13: bound sync traffic on a populated board.** *All four
  conditions met. Original finding and the evidence for each below.*
  The post-merge positioned fixture measured 8312 compressed bytes per client
  for 965 records with 321 positioned items, over the 5 KiB target. WALL-12
  measured 1662 bytes. These include events and required refetch, and are
  loopback observations. A delta still includes the complete board order.
  Consider incremental order updates reconstructed from changed positions,
  or an explicit bounded resync policy with a documented budget exception.
  **Complete when:** the positioned fixture meets the agreed budget, concurrent
  moves/edits preserve ordering, and larger cascades have a tested bound or
  resync path. A failing budget check must remain visible until then.
  - [x] **Budget met.** A delta no longer carries `board_order`. It is a pure
    function of `hand_placed`, `placed_at` and id, all of which already arrive
    on each record's position, so the client derives it; the snapshot still
    sends it. POSITIONED went from 8183 to 1655 bytes per client, against
    WALL-12's 1649 at 41 records, so the cost is flat in board size again.
  - [x] **Ordering preserved.** `test_a_client_can_rebuild_board_order_from_deltas_alone`
    rebuilds the order from deltas alone across a move and a content edit and
    compares it to the server's snapshot order.
  - [x] **Cascade bound.** Done. Past half the session's records the delta
    answers `resync_required` with no records: the snapshot is then at most
    twice the bytes, in one request, with no merge to get wrong. `since_seq=0`
    therefore always resyncs, so every client exercises that branch on its
    first call instead of meeting it during a rare cascade. The boundary is
    probed on both sides.
  - [x] **The check stays visible.** `measure_sync.py` exits non-zero over
    budget, runs the positioned fixture by default rather than behind a flag,
    and is a required check in CI. The flag is why this went unnoticed.

### Before a real-team pilot

- [ ] **K01/K02 / INT01: validate partial and damaged database layouts.** *Partly, 5 October 2026: structural validation and interruption/restart are done (K01). Backup and recovery instructions have not been exercised, so this stays open.*
  Both published histories migrate to schema 5, but a claimed version 5 with
  missing tables is not proactively rejected at startup.
  **Complete when:** table/column validation refuses unsupported layouts
  clearly, interruption/restart preserves supported data, and backup/recovery
  instructions are exercised. Passing published-history fixtures alone does
  not close this issue.
- [ ] **C03/C04/J04 / INT02: finish concurrent sync and authority coverage.** *Partly, 5 October 2026: C03 is done. Open: no test writes while a snapshot is being read (C04), and there is no route-by-role matrix (J04).*
  Participant removal now exists; the older C03 claim that it is absent is
  superseded. Keep the remaining requirement open for the combined route,
  replay and pagination matrix.
  **Complete when:** removed/demoted actors, cached responses, late callbacks,
  rollback and writes during pagination are exercised without missed changes,
  restored withdrawn content or renewed access.
- [ ] **G01-G06/M01/M02 / INT05: connect and verify actual clients.** *5 October 2026: the "placeholder" sentence is out of date, `app/client/` is a working browser client driven by `journey.mjs`. Still open: join, conflict, reconnect, sleep and revocation in the real UI, and Swift.*
  The browser application directory contains only a placeholder; the Swift
  core remains uncompiled. CLI and JavaScript mechanism tests are insufficient.
  **Complete when:** supported clients build and complete independent join,
  agreement, capture, review, movement, conflict, reconnect, export, stop and
  deletion, with visible provisional states and retained conflict edits.
- [ ] **A09/L05 / INT06: verify phones and shared-screen transport.**
  **Complete when:** a real phone and shared screen complete joining, upload,
  stop and sleep/reconnect on the intended network; Host/Origin/firewall
  configuration and the chosen encryption boundary are documented and tested.
- [x] **A06/A10/G05 / INT07: decide credential loss and identity handling.** *Verified 5 October 2026 in automated tests, not on a device: `test_lost_credentials_cannot_be_reset_by_reusing_name_or_session_id`, `test_remaining_facilitator_can_reinvite_without_inheriting_agreement`, and the join and revocation tests.*
  Invitation redemption proves device-credential control, not personal identity;
  migration cannot undo earlier token sharing.
  **Complete when:** fresh-session joining and revocation are demonstrated,
  lost facilitator access has an explicit recovery or unrecoverable policy,
  and recovery cannot supply another participant's agreement.
- [x] **I01-I05/D08 / INT08: settle evidence release and export independence.** *Verified 5 October 2026: `test_output_release_opens_after_delete_and_manifest_matches_in_both_modes`. Visible names and faces are not redacted, and the manifest says so.*
  Source references currently depend on the retained session.
  **Complete when:** the chosen output-only or evidence-bundle contract is
  labelled accurately, exports are opened without the original session,
  manifest contents match released bytes, and redaction/deletion limits are
  demonstrated. Visible names and faces need separate treatment from metadata.
- [~] **K03-K06/L01-L06 / INT09: establish operational evidence and CI.**
  The repository has no CI workflow; the Bash audit could not start in this
  Windows environment. Physical storage failure, receipt growth, concurrent
  media memory pressure and idle connection-slot pressure remain unverified.
  **Complete when:** a supported environment runs the audit and repeatable CI,
  readiness checks store/worker health, and named-hardware shutdown, recovery,
  retention and resource-pressure exercises record their results.
  - [x] **CI, and the audit in a supported environment.**
    `.github/workflows/verify.yml`, seven jobs, green on main at `51bae3b`. The
    audit runs on ubuntu-latest, the backend suite and all five mutation
    harnesses on Python 3.11, 3.12 and 3.13, plus the sync budget and the schema
    version check. A `Nothing was left mutated` step fails the build if a
    harness leaves a source file edited.
  - [x] **Idle connection-slot pressure.** Untested until now, and it was the
    likeliest of these to bite: keep-alive made a slot last a whole connection,
    so eight people on two devices each reaches the ceiling of 16 in an ordinary
    room. At the ceiling a new connection gets 503, and a slot comes back after
    the 10 second idle timeout, measured at 10.0s. Three mutants cover the
    ceiling, the release and the timeout. `LocalServer` now takes `slots` and
    `idle_timeout` so the bound can be reached in a test with two slots rather
    than sixteen.
  - [x] **A write that fails at the operating system.** Existing store-fault
    coverage uses SQLite triggers, which is a fault the database reports. This
    uses `RLIMIT_FSIZE` in a subprocess, so the kernel refuses the write.
    Result: the session is unchanged and still readable, which is what the
    storage error message already promised in words.
  - [x] **Concurrent media memory pressure.** Four simultaneous uploads of
    4.62 MiB each peak at 85 MiB resident, so nothing holds every image at once.
  - [x] **Receipt growth, and deletion on disk.** Five sessions created, filled
    and deleted leave five session rows of about 96 bytes each and no content
    rows. The file does not shrink: freed pages stay in it. Worth knowing, and
    it raised the question nothing had asked, so it is now a test: after
    deletion the session's text appears **zero** times in the raw database file,
    because `secure_delete` overwrites the freed pages. A mutant turning that
    pragma off fails the test.
  - [ ] **Named hardware other than this container.** Everything above is one
    4-core Xeon container with 16 GiB, Linux 6.18, Python 3.11.
    `tests/measure_operations.py` prints the machine alongside every number and
    has to be re-run on a team laptop before any of it is quoted as hardware
    evidence.
  - [ ] **Abrupt shutdown and recovery on named hardware**, and readiness under
    a genuinely failing store rather than a size-capped one.

### Before live providers or broader board features

- [ ] **E07/E08/F04/K04 / INT10: decide crash and paid-call semantics.**
  Completed results retained in memory survive transient store failures, but
  not process loss. Killing a local worker does not prove remote billing stops.
  **Complete when:** durable reconciliation or explicit manual-retry semantics,
  provider deadlines/idempotency, limits and known/unknown cost are tested
  across provider success followed by local failure.
- [ ] **F03/F05/M03-M05 / INT11: demonstrate fidelity and useful time savings.**
  **Complete when:** held-out wall evaluation measures coverage, corrections,
  abstention and total setup/review/repair/export effort against manual work.
  Fixture output must remain synthetic; current tests establish no OCR quality.
- [ ] **B05/B06/C04/C06 / INT12: finish board layout and cascade behaviour.**
  **Complete when:** collision/visibility rules, clusters/forms, empty groups,
  deletion/undo and concurrent cascade/resync behaviour are specified and
  tested while preserving hand-placed geometry and content provenance.

### Evidence already recorded, not new open defects

The combined mutation/transport integration and tree-readback work in INT03 was
performed for PR #13: all 64 named guards passed before merging, all 144 file
blobs matched the expected merged tree, and all 164 tests passed again on the
verified main contents in 35.873 seconds. JavaScript unit checks also passed.
These results do not close the remaining INT01/INT02 subclaims or the pilot
issues above. No backend tests were rerun solely for this documentation update.

[Post-merge verification and review](https://github.com/ptborst/GenAI/pull/13).

## Assigned follow-up implementation, 16 September 2026

The agreed split assigns INT02, INT07, INT10, the remaining INT01 and INT08 to
the backend lifecycle workstream. The other workstream retains INT13, INT12,
INT03 harness consolidation, INT04 validation and CI. The following status
supersedes earlier descriptions that those mechanisms are entirely absent.

- [x] **INT01, supported-schema preflight:** Reject partial/unsupported declared
  layouts before writes, including keys/uniqueness, nullability/defaults and
  foreign keys. Preserve both published histories and interrupted migration
  stages. This is structural validation, not row repair or physical recovery.
- [x] **INT02, backend authority and event acceptance:** Removal/demotion is
  checked on reads, media/crops, export/history and cached mutations. Writes
  between event pages and rolled-back writes are exercised. Client subscriptions
  and wider layout cascades remain under INT05 and the other workstream's INT12.
- [x] **INT07, identity and loss decision:** No reset by name or session ID;
  lost sole-facilitator access is unrecoverable. A remaining facilitator may
  remove the old actor and re-invite; the new actor explicitly acknowledges the
  current policy. Historical agreement is not inherited.
- [x] **INT08, output-only release contract:** New manifests explicitly state
  offline readability, server-dependent evidence and absence of redaction.
  Both inclusion modes match released records and downloaded outputs remain
  readable after deletion. Evidence bundles require a separate release decision.
- [ ] **INT10, live-provider completion remains open:** The local crash/retry
  path is implemented and tested: claimed jobs never requeue automatically,
  uncertainty survives expiry cleanup, explicit retry acknowledgement is
  required, and known returned usage survives discarded proposals. Complete
  provider-specific connect/read/total deadlines, idempotency, remote cost
  reconciliation and hard spending limits before enabling a paid adapter.

Validation is recorded in [follow-up status](../app/server/FOLLOWUP-STATUS.md).
No physical phone, human identity verification, live OCR or user evaluation is
claimed by these completed mechanism/decision rows. Existing owners and the
paused homework work remain unchanged.

## Runtime observability follow-up, 16 September 2026

- [x] **L02, bounded diagnostic API:** Current facilitators can inspect queue
  counts/age, at most 20 attention jobs with safe reason codes, uncertain outcomes,
  retained completion counts and logical payload bytes. Metrics are read-only,
  hide names/source material/credentials and keep null observations explicit.
- [x] **L03, readiness separate from liveness:** `/ready` requires successful and
  recent worker/maintenance progress, a bounded existing-store transaction probe,
  and no pending completion/cleanup faults. A missing database is not recreated.
  `/health` remains HTTP liveness; real CLI startup and failure states are tested.
- [ ] **L03/L04/L06, operational acceptance:** Calibrate stall thresholds on named
  hardware; test physical storage exhaustion, OS I/O stalls, power loss and
  recovery. A SQLite write-lock probe does not prove durable writes or free disk
  capacity. Concurrent latency/memory and backup/restore evidence remain open.
- [ ] **G06/M01, client use of diagnostics:** Add bounded polling/backoff and show
  null/truncated observations honestly in the real client. No UI or real-device
  acceptance is claimed by these backend routes.

Current evidence and response interpretation are in
[RUNTIME-OPERATIONS.md](../app/server/RUNTIME-OPERATIONS.md). CI and mutation
harness consolidation remain with the other workstream; the additional runtime
harness must be preserved when they are combined.
## Client plumbing follow-up, 16 September 2026

- [x] **G02/G05/INT05, transport and immutable retries:** Total deadlines include
  response decoding; cancellation preserves uncertain write outcomes. Retained
  intents bind exact command bytes and request IDs to their originating client.
  Explicit retry, revocation and late-response suppression have named guard tests.
- [x] **G03/G04/INT05, synchronisation and control lifecycle:** Bounded polling,
  full resynchronisation, one in-flight control, uncertain intent retention and
  explicit pause are implemented. Foreground/connectivity return never activates
  capture or automatically restores heartbeat. Real HTTP two-client mechanics
  and deterministic race tests are recorded in CLIENT-PLUMBING.md.
- [x] **G06/M01, diagnostic transport:** Readiness preserves the not-ready body;
  facilitator diagnostics are callable. Null/truncated interpretation is documented.
- [ ] **G06/M01, diagnostic and uncertainty UI:** Display stale data, null readings,
  partial attention lists, retry/discard choices and acknowledged server pause.
  A transport response alone does not close the user-facing acceptance claim.
- [ ] **INT05/INT06, real browser and device lifecycle:** Bind initial/event-driven
  visibility and connectivity state; test CORS, mobile backgrounding, screen lock,
  Wi-Fi loss and shared-display convergence. Local stop does not send server pause.
- [ ] **INT07, reload and credential retention decision:** Memory-only credentials
  and intents disappear on reload. Decide recovery expectations and any protected
  persistence before claiming a usable long-running client. No identity reset exists.
- [x] **INT12/INT13, current delta integration:** Derive board ordering from
  merged positions and follow the normal cascade resync response without skipping
  a cursor. Preserve these executable fixtures for future server contract changes.
- [ ] **G01, remaining contract breadth:** Typed public declarations, unknown enum
  presentation and the uncompiled Swift client remain outside this JavaScript
  mechanism package. A passing JavaScript journey does not close them.

PR18 supplied clusters, cascade bounds, malformed-input validation and the
shared mutation runner. This package integrates those changes and adds client
checks plus missing schema/runtime guard jobs to CI. Geometry and the broader
real-client journey remain open. Homework remains paused. No UI, real phone, live provider or human acceptance is
claimed by these completed plumbing mechanisms.

Integrated candidate evidence: 237 backend tests, 38 client tests and all 143
named guards passed. CLI, JavaScript and two-client real HTTP journeys passed;
POSITIONED measured 1662 B compressed per client. Current results supersede the
historical statement above that those journeys have not been performed, while
real browser/device acceptance remains open. See CLIENT-PLUMBING.md and the
publishing PR for exact candidate and merged-tree verification.

## Future product work: expandable sticky notes (22 September 2026)

F3.8 adds separate main-point and supporting-detail representations to the planned
canvas. Reuse item IDs, source attribution, review history, positions and links;
design any contract extension in a future implementation change. Current API
payloads, schemas and completed B/C work are unchanged. Disclosure and local
spacing belong to the view, not item.place or the shared revision stream.
See [the interaction contract](../app/design-system/spec/expandable-notes.md).

Future delivery includes summary fidelity and full-content review, in-place
expansion with local collision handling, accessible list/touch access, meaningful
provisional organisation that preserves team adjustments, and overview/complete
export behaviour. These are unimplemented requirements, not completed backend
tasks or a replacement for the existing milestone order.
