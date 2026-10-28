# Pipeline design and process decisions

Date: 2026-09-15. Status: **proposed implementation baseline, pending team review**.
These are concrete choices for the next prototype, not claims that a prototype or
user study exists. They resolve the alternatives in `pipelines.html` for one build.
The broader eight-pipeline map remains the exploration space. Jarvaids is a working name.

## D01: Build one complete capture-to-review slice

Start with typed notes and photo intake → separate note proposals → crop-backed
correction → explicit acceptance → deterministic placement → export → deletion.
Use a simple local canvas to test this slice. External board write-back gets a
separate one-day feasibility spike before promising continuity with the team's board.
This chooses concept 001's capture hypothesis over the brainstorm's all-in-one assistant.
Manual entry must remain usable with every model disconnected.

Defer continuous audio, voice commands, automatic form selection, rolling minutes,
cross-session search and proactive ideation. They remain evaluation tracks, not MVP
dependencies. A photo-only trial cannot validate meeting recall or live facilitation.
The alternative is an audio-first slice; choose it only if observation shows capture
is not the costly task. Exit evidence: the same wall is corrected and exported faster
than the manual baseline without worse content fidelity (evaluation protocol G2).

## D02: Separate requesting from committing

Participants may upload, type, ask and propose arrangements. The facilitator may
accept shared AI proposals, change session policy and export. Everyone may stop
capture. An uploader can correct their own unaccepted extraction; a participant
requests changes to accepted shared content through a proposal. The facilitator role
is explicitly transferred, never inferred from voice identity or the first reconnect.
Typed requests with explicit selected item IDs are the initial command interface.

Use session-scoped guest credentials with role checks on the server; possession of
a shared viewing link does not grant write or export permission. Check permissions
again at commit, including after role transfer. Test forged roles and cross-session IDs.
This adds review work and can bottleneck the facilitator: measure queue age and
abandoned proposals before expanding participant commit rights.

## D03: Review is a transaction, not a border style

Proposal states: `queued → processing → needs_review → accepted | rejected`.
Also allow `failed`, `cancelled`, and `stale`; retries create attempts of the same
request. Acceptance records actor, source revisions and expected canvas version.
A conflict makes the proposal stale and requires an updated preview; no automatic
rebase of semantic edits. Only deterministic placement of an unchanged proposal may
be recalculated, and its new placement must be previewed before acceptance.

An accepted item keeps its AI origin and review history. Acceptance means a person
reviewed it, not that its content is objectively true. Editing does not implicitly
accept. Undo is a compensating operation against affected item revisions; if another
person has subsequently edited them, offer a conflict preview rather than erase work.
Do not expire unnoticed proposals into acceptance. Keep unresolved proposals in the
review queue and explicitly label or exclude them at export.

## D04: Preserve source identity through corrections

Each item stores `item_id`, `revision`, `source_refs[]`, `origin`, `review_state` and
`created_by`. A source reference includes source ID, revision and a crop rectangle
or transcript time range. A derived claim stores all its source references; a single
causation ID cannot describe a summary assembled from many inputs.

Source correction creates a revision and marks dependent proposals stale. Accepted
derived claims are flagged "source changed, review again"; no silent rewriting.
Deleted sources are unavailable to retrieval and mark affected citations unavailable.
Confidence is optional, model-specific metadata; an LLM's self-score is not a calibrated
probability and must never independently authorize an operation or establish consensus.
This requires a dependency index; test a note correction reaching both a layout and export.

## D05: Keep one service and a transactional session log

Use one server process, a persistent transactional store and ordinary worker functions
for the first slice. Do not introduce a broker or independently deployed agents yet.
Assign sequence numbers and commit state plus its event in the same transaction.
The three agent boxes in the flowchart describe responsibilities, not required services.

Event envelope: `event_id`, `schema_version`, `session_id`, `seq`, `request_id`,
`actor_id`, `type`, `occurred_at`, `source_refs[]`, `causation_id`, `policy_version`,
`payload_ref`, `producer_version`. Media time is optional and records clock origin
and uncertainty; timestamps from separate devices are not assumed synchronized.

Deduplicate transport retries by `(session_id, actor_id, request_id, operation)`.
An intentional repeated action gets a new request ID even when text is identical.
Text similarity within eight seconds may suggest "already running" but must not
silently swallow a different selection or a deliberate repeat. Persist the result
against the key so retries after process restart return the same outcome.

Deterministic replay reuses recorded outputs and verifies state. Model comparison is
a separate evaluation run using approved retained inputs; it must not publish canvas
mutations, exports or deletions. It is impossible to re-run ASR after its audio was
deleted. Never extend raw retention to preserve replay convenience.

## D06: Consent and deletion apply to every derived store

Record agreement before enabling capture through an explicit non-recording setup
step. Do not record agreement before agreement has enabled recording. Starting,
pausing and resuming require the current participant/policy state; a new participant
pauses capture until the room's agreement is current. Push-to-talk still captures
people and does not remove this gate.

Proposed prototype policy: raw audio excluded from backups; deletion at close with
the existing 60-second target. A renewable session lease identifies abandoned sessions;
check expiry at least once per minute. Define abandonment as 5 minutes without a
heartbeat and target deletion within 60 seconds after that. These replace the ambiguous
hourly sweep promise and require measurement under process failure before field use.
Image retention remains configurable before capture; no indefinite "keep longer" switch.

Stop revokes the capture policy version, cancels jobs, discards buffers and rejects
late results under the old version. Stop and deletion are distinct visible states.
For a whole-session deletion request, disable access first, then purge media, event
payloads, derived text, search/embedding stores, caches, exports still controlled by
the service and identifier mappings. Keep only a content-free deletion receipt.
Restore jobs must apply tombstones before exposing any restored data.

For the prototype, propose whole-session deletion when selective removal cannot be
verified. The teaching team must resolve the research policy before real recordings;
this document is an implementation proposal, not evidence of that approval. An export
already downloaded cannot be recalled: disclose the boundary before exporting.

## D07: Bound work and make saturation actionable

Initial tunable limits: two active image jobs per session, five queued image requests,
one active shared mutation and ten queued mutation requests. Reject excess before
accepting its payload, show the reason and offer retry; preserve manual editing.
Apply per-session byte and pixel limits before decoding images, and record limits
in configuration. Choose those limits after testing the target device, before release.

For the deferred audio track: cap unprocessed audio at 30 seconds. First indicate lag
and try the configured lower tier; at capacity stop intake and insert a timed capture
gap. Do not silently discard old audio or buffer indefinitely. Resume explicitly when
healthy. Pending changes cancelled by consent revocation cannot later commit.
Track end-to-end p50/p95 latency including queue and review time separately; stage
budgets alone cannot establish whether a live interaction is usable.

## D08: Validate structure and scope before interpreting content

Photo text and transcript text are data, including text that says "ignore your rules"
or "delete the board". Only an authenticated explicit request can propose an operation.
Validate operation allowlists, field types, size limits, source membership, permissions
and expected revisions in code. Model output cannot supply executable code or arbitrary
URLs to fetch. Escape note content in HTML previews and exports.

Choose model/provider versions through a separate permitted-data benchmark; this
decision set makes no current pricing or API capability claims. No raw recording may
go to a third-party ASR. The team must explicitly decide whether transcript/image
content may leave the host before enabling any remote model path.

## D09: Compare useful structures; do not force variety

Keep a list and original spatial arrangement as baselines. Offer a cluster only when
grouping helps a named task, a timeline when temporal ordering is supported, and a
matrix only when both axes have defined meanings. Unplaced/undated items remain visible.
The number of output forms is not quality. Preserve disagreement and minority notes;
measure source coverage and relationship accuracy as well as task completion time.
For the first slice the human chooses the form; automated selection needs G3 evidence.

## D10: Decide from evidence at explicit gates

Use G0–G4 in the evaluation protocol. A named team member must own each gate before
testing; no individual has been assigned by this document. Freeze dataset IDs, prompt
versions, thresholds and comparison conditions before measuring. Log failures and
negative findings alongside successes. Keep held-out cases separate from prompt tuning.
Classify edits as correction, elaboration, preference or uncertain; an edit count is
not an error rate. Report participant/session counts and limitations with every result.
Revisit these decisions after the first end-to-end trial, not after building all eight
pipelines. See the breadth audit for coverage and the issue backlog.

## D11: Expandable notes and organisation with team control

Approved product direction, 22 September 2026; implementation remains future work.
The overview uses collapsed main points, with in-place expansion for supporting
detail and session evidence. AI may organise incoming notes automatically as
provisional structure. Preserve accepted arrangements and team adjustments;
conflicting regroupings require review. This extends D09 without making form
selection a dependency of the D01 capture-first milestone.

D02 and D03 still govern acceptance of shared meaning. Publishing a provisional
arrangement is not accepting it. Review must show the complete summary, detail
and evidence before Accept is available; a collapsed overview offers Review.
Opening detail never changes review state or invokes a model. Temporary display
spacing is local and never writes shared positions. D04 source corrections and
deletion also apply to summaries and supporting detail.

Future data requirements reuse existing identity, provenance, revisions and
relationships; this documentation change adds no API fields or migrations.
See [the interaction contract](../app/design-system/spec/expandable-notes.md).

Alternatives were a separate detail panel, floating detail, and team-only layout.
In-place expansion preserves the sticky-note interaction; automatic organisation
reduces manual sorting. Costs are summary fidelity checks, full-content review,
local spacing, accessibility and explicit overview versus complete exports.

## D12: Topic and choice colours on sticky notes

Approved direction, 23 September 2026. Each main topic, subject or choice may
have a distinct note fill; same-group notes share it. A label on every note and
a labelled overview key keep grouping readable without colour. AI proposes the
grouping, and the team can change membership or colour; overrides and stable
mappings survive new content, expansion and export.

This replaces white-only content items with a planned categorical note palette,
separate from state colours and the action accent. Status stays explicit through
strokes and labels; neither a colour change nor accepting a group accepts its
content. Source photograph colour is independent evidence. Future data work needs
a shared group-to-colour mapping, not a new local expansion state.

Alternative: preserve white notes and show grouping only through spatial layout.
Colour supports scanning across the overview, at the cost of a palette, contrast
testing, a key and neutral fallback when colours run out. This is a documentation
change, not a shipped palette or UI. See [the full contract](../app/design-system/spec/expandable-notes.md).
