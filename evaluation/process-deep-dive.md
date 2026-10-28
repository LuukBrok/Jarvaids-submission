# Process deep dive: opportunities, flaws and alternative solutions

2026-09-15 · proposed process design · reviewed PR head
`14a3fa615c6d590e83804c0b07c0275d9eabaf09` and its repository sources.

## What changes in this pass

The previous pass chose a first slice and named cross-cutting contracts. This pass
expands the actual network into **70 nodes, 134 directed connections and nine
walkthroughs**, including optional future pipelines. It separates the work of the
participant, facilitator, model, state service, export worker and research team.
Every node has inputs, outputs, a guard, a failure response and a measure.

[Open the process explorer](../deliverables/documentation/process-network.html).
Its source is [structured JSON](../deliverables/documentation/process-network.json).
The diagram is a process specification, not executable orchestration; edges show
conditional handoffs, dependencies, control, observation and lifecycle obligations.
Cycles are intentional review/recovery loops, not permission to retry indefinitely.

**Assessment:** the strongest opportunity is to preserve the route from messy source
material to a usable, checked artifact. The greatest risk is losing meaning at a
handoff while each individual stage appears to succeed. The network therefore gives
coverage review, source revisions, disagreement, release checks and recovery explicit
places. Additional model stages alone would not resolve those problems.

No user study, model benchmark, live board integration or runtime reliability test was
performed. Existing evidence files are templates. Findings below distinguish source
contradictions, missing process contracts and hypotheses requiring research. Suggested
options are design proposals, not measured winners. The design system is out of scope.

## Where the work really happens

| Phase | Human job | System job | Artifact passed forward | Failure cost |
|---|---|---|---|---|
| Frame | Name a costly task and valid baseline | Record protocol and allowed data | Task plus trial boundary | Optimizing a task nobody needs |
| Prepare | Agree participation, roles, retention and devices | Enforce current session policy | Active, versioned session | Capture outside the agreed boundary |
| Capture | Choose source, redact, retake or type | Admit bounded input and preserve identity | Source with revision and expiry | Missing or unusable evidence |
| Interpret | Correct boundaries and illegible text | Propose extracted text and structure | Unaccepted proposal with source links | Fluent but incorrect material |
| Review | Check meaning and choose an action | Show source and detect stale revisions | Explicit review result | Review backlog or false acceptance |
| Commit | Resolve conflicts where necessary | Atomically persist change and history | Shared current revision | Duplicate actions or lost human edits |
| Recall/reason | Ask a bounded question; resolve disputes | Retrieve evidence including contradiction | Qualified answer/decision candidate | False attribution or consensus |
| Release | Choose scope and review sensitive content | Freeze, render, reconcile and deliver | Artifact plus coverage manifest | Durable release of wrong content |
| Close | Stop, resume deliberately, or end | Cancel late work, purge and verify | Accurate lifecycle state | Resurrection or false deletion claim |
| Learn | Interpret evidence and choose next scope | Capture content-minimized measures | A decision supported by a trial | Expanding an unproven product |

## Detailed findings and solution space

Priority P1 blocks the affected trial or trustworthy outcome. P2 blocks a benefit
claim or a later extension. Each recommendation includes a simpler and a more capable
alternative; choosing the more capable option requires evidence for its extra work.

### F01 · P2 — Product focus remains a hypothesis, not an established user need

**Evidence:** concept 001 prioritizes photo capture; the brainstorm prioritizes live
visual thinking; P3 calls commands core. `evidence/synthesis.md` contains no observations.
D01's photo-first choice is a sensible experiment, but could miss the real opportunity.
Network: S01, I11, X03.

- **A — Capture-first:** solve retyping/placement. Most bounded end-to-end test; weaker
  differentiation if manual capture is already cheap.
- **B — Recall-first:** explicit question over an approved transcript. Tests lost
  rationale directly; depends on transcript quality and source support.
- **C — Facilitator-assist:** human-operated simulation of commands and arrangement
  before automation. Tests demand with little implementation, but operator behavior
  can inflate perceived capability.

**Recommend:** keep A as the build slice and run C as an observation method; promote B
only when recall failures are observed. Compare complete task effort and errors against
current practice. Do not use request frequency alone: one critical recall may be more
valuable than ten cosmetic arrangement requests. Opportunity: find the high-cost moment,
then attach automation to it instead of offering all eight pipelines at once.

### F02 · P1 — The agreement boundary must precede capture and survive session changes

**Evidence:** concept 001 asks for agreement on the record, while the pipeline's
shared gate disallows capture before agreement. P2's accidental-personal-data fallback
asks the uploader to review after upload, which is too late to prevent that upload.
Network: S03–S06, I02, L01–L03.

- **A — Explicit roster and non-recording agreement:** facilitator checks each person;
  late arrival pauses recording. Simple, but relies on noticing physical arrivals.
- **B — Per-participant join/acknowledgement:** stronger identity and change visibility;
  creates phone/setup friction and still misses unregistered people entering a room.
- **C — No live capture:** use approved, redacted files and typed notes. Narrowest
  collection surface; cannot validate live recording value.

**Recommend:** A plus a visible anyone-can-pause control, with C for early mechanics.
Add local crop/redaction before upload and check remote processing permission before
model dispatch. Never infer that push-to-talk removes participant constraints. Validate
late arrival, offline Stop and pending job revocation. These are product/process
requirements; the teaching team's policy still has to be established for real trials.

### F03 · P1 — Facilitator-only commits can replace AI risk with a human bottleneck

**Evidence:** U.2 leaves roles open; D02 selects facilitator commits. No measured review
capacity supports that choice. Network: S04, C05, R02–R04.

- **A — Single reviewer:** clear responsibility, simple conflict model; slowest when
  many participants submit material at once.
- **B — Delegated ownership:** uploaders review their own text; facilitator reviews
  shared relationships and decisions. Spreads work but requires scope-aware authority.
- **C — Two-person review for consequential claims:** stronger independent checking;
  too expensive for every sticky note and vulnerable to superficial agreement.

**Recommend:** start with A, then compare B if queue age or facilitator effort dominates.
Use C only for named decisions/owners in a later track. Role transfer must invalidate
old pending authority; authority is checked at commit, not just request time. Measure
incorrect accepts alongside throughput: a fast queue can be a rubber-stamping queue.
Opportunity: assign review by consequence and authorship, not merely model confidence.

### F04 · P1 — A reviewer cannot correct a note the system never detected

**Evidence:** P2 moves segmentation to recognition and provisional placement. Its
progressive reveal shows detected rectangles, but lacks an explicit coverage review.
Global 2048px resizing can also destroy small handwriting before per-note inspection.
Network: I03, I06–I08.

- **A — Show source overlay with add/split/merge:** inexpensive human repair, including
  missing notes; depends on someone checking the whole photo.
- **B — Multi-scale/tiled detection:** preserves small-note detail; adds coordinate
  transforms and duplicate-boundary reconciliation.
- **C — Guided capture of smaller regions:** reduces difficult input; adds capture
  effort and can lose relationships between regions.

**Recommend:** A first, with C offered on unreadable regions; evaluate B only on failures
that remain costly. Preserve source-to-crop transforms and stable region IDs. Test
white notes, overlap, cropped edges, glare and dense walls. Report recall over all
ground-truth notes, not text accuracy only on detected notes. Opportunity: coverage
review may save more work than increasing OCR confidence on the easiest crops.

### F05 · P2 — Cheap batches and visual grouping can silently corrupt identity or meaning

**Evidence:** P2/S8 asserts a nine-crop grid is roughly nine times cheaper and measurably
worse without a benchmark. S9/S10 infer color and proximity before semantic review.
There is no evidence that a wall's colors denote themes rather than authors or voting.
Network: I09–I10.

- **A — One region per request:** clean attribution and isolated retry; more request
  overhead and potentially more cost.
- **B — Indexed batches with a strict region-ID response:** efficient if measured;
  requires checking missing, extra and transposed IDs, not just valid JSON.
- **C — Classical OCR first, model escalation on difficult crops:** bounds model use;
  can miss errors confidently classified as easy.

**Recommend:** benchmark A and B on identical held-out walls; retry only failed regions
with bounded attempts. Treat C as a separate comparison. Store observed color/location
without assigning meaning until a person defines it. Score crop-to-text swaps and
semantic grouping errors separately. Do not claim a batching cost ratio from call count
alone; image size, tokens, provider billing and correction effort all matter.

### F06 · P1 for audio — Plausible transcription errors propagate further than visible gaps

**Evidence:** P1 depends on one room microphone and proposes a loudest-phone attribution
fallback. Loudness is not identity. Overlapping chunks and separate device clocks can
duplicate words or attach evidence to the wrong time. Network: A02–A06.

- **A — One local mic, unknown speakers by default:** simplest, candid limits; weak
  distant/overlapping speech and no reliable person-specific recall.
- **B — Per-person push-to-talk:** better association and cleaner audio; changes meeting
  behavior and misses uninvoked discussion.
- **C — Multiple synchronized tracks plus diarisation:** richer evidence; more setup,
  synchronization, echo and retention complexity.

**Recommend:** compare A/B before attempting C. Keep speaker uncertainty independent
from text uncertainty; a human confirming one sample cannot validate every future
speaker assignment. Hand-label negation, names and decisions as well as overall word
error rate. Test duplicate overlap, delayed chunks and source corrections reaching
answers/minutes. Audio remains an extension, not a dependency of photo capture.

### F07 · P1 — A source can change after its descendants look finished

**Evidence:** X.1 has a causation ID but no complete many-source dependency contract;
P5 uses indexes, P6 rolling state and P7 snapshots. D04 begins to resolve this, but needs
transitive invalidation and output-specific states. Network: R08, Q01, E02.

- **A — Invalidate an entire session's derived outputs:** simple and conservative;
  expensive and disruptive after small corrections.
- **B — Track source revision dependencies per claim/item:** targeted invalidation;
  requires a maintained dependency index and handling merged sources.
- **C — Immutable snapshots only:** reproducible historical answers; users can easily
  mistake a historically correct answer for a current one.

**Recommend:** B for current material plus C for exported artifacts. A is a safe fallback
when dependencies are incomplete. Mark stale immediately; recompute only on request or
at a deliberate checkpoint. Do not quietly regenerate a previously accepted decision.
Test a corrected speaker label used by two claims and an export. Opportunity: show
what changed and why the earlier conclusion needs review, not just a generic warning.

### F08 · P2 — Clarification can be technically correct and operationally unusable

**Evidence:** P3 resolves "those three" from speech, selection and canvas; confidence
thresholds are guesses. Repeated clarification interrupts the workshop. Network: C01–C05.

- **A — Explicit selection plus direct controls:** deterministic targets; less natural
  than voice but a strong baseline.
- **B — Typed/push-to-talk requests with a visible target preview:** expressive, bounded
  ambiguity; one extra review step.
- **C — Ambient command detection and inferred references:** lowest invocation effort;
  highest false-action, attribution and privacy exposure.

**Recommend:** A/B, with at most one clarification before falling back to selection.
Evaluate C only if the invocation burden demonstrably blocks use. Authorization cannot
depend on inferred speaker identity or a confidence score. Compare total command time,
wrong targets, false invocations and abandoned requests. Offer a direct action when
the user would otherwise have to explain the same intention twice.

### F09 · P1 — Acceptance conflates several independent judgments

**Evidence:** P2 inserts provisional items, P4 groups/places them and P7 asks how to
handle remaining provisional content. One accepted flag cannot express that text is
checked while grouping is disputed. Network: R01–R07, V05.

- **A — Single proposal acceptance:** minimal implementation; hides which aspect was
  checked and promotes child content accidentally.
- **B — Separate content, relationship and placement decisions:** clearer semantics;
  more state and review controls.
- **C — Keep everything as immutable suggestions until final export review:** little
  shared mutation risk; pushes the entire burden to the end.

**Recommend:** B with small, explicit review units. A layout acceptance must not accept
its children; an accepted OCR reading does not validate a generated causal link.
Reject, edit and undo must preserve original output and current revisions. Test a
two-reviewer race and an undo after another person's edit. Opportunity: make each
approval mean something sufficiently precise to be useful in evaluation and export.

### F10 · P1 — The real queue is often waiting for a person

**Evidence:** P2/P6 can create proposals continuously; the original latency budgets
mainly count model and code time. D07 bounds machine jobs but not review debt.
Network: R02, X01.

- **A — FIFO review:** predictable and easy to explain; trivial notes can delay a
  consequential decision.
- **B — Consequence/age prioritization with an intake ceiling:** controls review debt;
  needs transparent prioritization and no starvation of low-priority items.
- **C — Session checkpoints:** pause generation at agenda boundaries and review in
  batches; fewer interruptions but delayed value.

**Recommend:** compare B/C against A. Never silently discard low-ranked proposals.
Illustration, not measurement: 30 notes × 12 seconds of review = 6 reviewer-minutes;
a two-second OCR improvement cannot offset that workload. Stability requires accepted
review arrival rate below sustainable review completion rate over time. Measure
correction time, false acceptance, queue age and unresolved-at-close separately.
Opportunity: reduce unnecessary proposals and reveal only what requires a decision.

### F11 · P1 — A transaction log does not automatically make a reconnect safe

**Evidence:** X.4 says reconnect is not a special case. A client can miss events, receive
an acknowledgement late or recover a stale snapshot. External writes are outside the
local transaction. Network: R05–R06, L07.

- **A — One service with transactional state/event/result writes:** smallest coherent
  prototype; one local failure domain and explicit recovery still required.
- **B — Transactional outbox plus workers:** records outgoing work before dispatch;
  adds worker reconciliation but survives process boundaries.
- **C — Separate event broker/services:** independent scaling and isolation; highest
  coordination and deployment cost for the current project.

**Recommend:** A now; add B for external board operations. Do not add C without a measured
capacity or isolation need. Detect gaps in sequence, resync from a named snapshot and
reapply subsequent events. Client "saved" means durable acknowledgement, not local
optimism. SQLite's atomic transactions support the local all-or-nothing choice, not a
claim of atomic writes to an external board. [SQLite transactional documentation](https://www.sqlite.org/transactional.html).

### F12 · P1 — Retrying can multiply both the workload and the effect

**Evidence:** X.3 originally deduplicates commands by text/window; X.5 promises bounded
queues without a complete saturation policy. A lost acknowledgement does not establish
that a job failed. Network: I04, A02, S05.

- **A — Fail fast with manual retry:** simple, visible; makes the participant manage
  transient errors.
- **B — Durable request IDs, payload fingerprint and bounded backoff:** safer automatic
  retries; needs stored outcomes and a deadline.
- **C — Adaptive scheduling and provider/model switching:** greater resilience under
  load; can change output quality, policy applicability and comparison validity.

**Recommend:** B with A for validation/permission errors. Same key with different payload
must be rejected, not treated as a successful retry. Automatic retries reuse identity,
obey a total deadline and stop on cancellation; a conscious new attempt is separate.
Record provider/model changes explicitly. This follows the intent distinction in
[AWS's idempotent API guidance](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/).
Test timeouts before and after commit, not only clean failures.

### F13 · P1 — Deletion is a graph operation, not a folder cleanup

**Evidence:** P8's five tiers omit explicit queue payloads, derived indexes and event
bodies; X.4 promotes full replay. A delayed worker can recreate deleted material.
Network: L02, L04–L07 and every lifecycle edge.

- **A — Session-level purge with raw tiers excluded from backups:** easy to reason
  about; removes shared work when selective deletion is infeasible.
- **B — Dependency-directed selective purge:** preserves unrelated content; source
  mixtures and derived claims make verification difficult.
- **C — Short-lived raw processing with only reviewed outputs retained:** reduces
  exposure; restricts later correction and model comparison.

**Recommend:** A plus C for the prototype; B only after reliable derivation coverage.
Deletion first denies reads/writes, then purges and verifies each configured store.
Late jobs must check the tombstone before any write. Distinguish access revoked,
purge pending and purge verified. W3C PROV's entities, activities and derivations are
a useful conceptual basis for those dependencies; full RDF adoption is unnecessary.
[W3C PROV overview](https://www.w3.org/TR/prov-overview/). Test restart and restore, and
state clearly which downloaded/external copies are outside the service's control.

### F14 · P2 — A plausible diagram can impose meaning that was never discussed

**Evidence:** P4's form selector uses dates/colors; the flowchart labels layout as AI
even though most geometry is deterministic. Five output forms do not demonstrate value.
Network: V01–V05.

- **A — Preserve original arrangement plus a list:** strongest evidence fidelity;
  may retain a confusing board.
- **B — Human-selected form with deterministic layout:** saves placement work while
  keeping the structural decision human; some manual effort remains.
- **C — Model proposes structure with alternatives and relation-level evidence:**
  potentially more assistance; greater risk of unsupported causality or lost dissent.

**Recommend:** B against A, then test C on tasks where B fails. Require valid time data
for a timeline and named axes for a matrix; leave unmatched items visible. Grouping by
color must not become an inferred opposition. Measure retrieval/comprehension accuracy,
omitted minority notes and unsupported relations, not form distribution or aesthetics.
Opportunity: offer two evidence-preserving structures to compare rather than announce
one "correct" visual answer.

### F15 · P1 for answers — Valid citations and early streaming do not establish truth

**Evidence:** P5/S6 validates source IDs and quote string matching, while its latency
section streams the answer before the final checks. A quote can be exact but attached
to the wrong subject, negation or conclusion. Network: Q01–Q06.

- **A — Extractive source snippets:** minimal unsupported paraphrase; less concise.
- **B — Sentence buffering with support/contradiction checks before release:** balances
  readability and control; delays first meaningful output.
- **C — Generate plus separate verifier:** can catch additional errors; adds cost and
  correlated model failures, so it cannot guarantee truth.

**Recommend:** A as baseline, B as the next variant; C only if independently scored
benefit warrants it. Check freshness and speaker identity separately. Do not show an
unchecked clause and rely on removing it later. Include contrary evidence and use
"not found in available material" instead of claiming the event never happened.
Test negation, retracted decisions, plausible wrong speakers and genuine no-answer
cases. Semantic support still requires evidence-based evaluation and human review.

### F16 · P2 — A passing pilot can be created by the evaluation design itself

**Evidence:** the original unknowns suggest repeated photographs of one wall and give
some thresholds without definitions. G2 improves this, but study order, scoring and
decision ownership still need execution. Network: S02, X02–X04.

- **A — Synthetic adversarial fixtures:** cheap, repeatable mechanism tests; cannot
  establish real-team benefit.
- **B — Held-out, varied real walls with counterbalanced manual/assisted tasks:** useful
  feasibility evidence; limited generalization and possible learning effects.
- **C — Multiple natural sessions with a comparative protocol:** strongest ecological
  validity; higher recruitment, consent and confounding costs.

**Recommend:** A → B → C only after earlier gates. Split by wall/session, not crop;
include failed trials and denominators. Track independently scored final fidelity and
total work, not corrections alone. A threshold must be set before viewing results and
owned by the team. Compare uncertainty and condition-specific failures; an average
can hide a feature that works only for neat English handwriting under bright light.

### F17 · P1 for minutes — Silence is not consensus; a decision can be reversed

**Evidence:** P6 uses silence/conclusion windows and compressed running state. This can
close a topic while objections remain or overwrite a later reversal. Network: M01–M04.

- **A — Manual "record this decision" with linked sources:** strongest intent signal;
  extra facilitator action and missed unmarked decisions.
- **B — Automatic candidates with proposed/contested/confirmed/superseded states:**
  more coverage; requires deliberate confirmation and disagreement retention.
- **C — End-of-session synthesis reviewed against source episodes:** fewer live
  interruptions; may recreate the post-meeting labor the tool aims to reduce.

**Recommend:** B with A as a direct shortcut; compare C if nobody uses live minutes.
Silence can trigger candidate extraction, never confirmation. Keep unknown owner and
deadline blank. Reopen a topic and link a later decision as superseding the earlier
one, retaining the rationale. Test sarcasm, proposals, dissent, reassigned actions
and retracted dates. Opportunity: preserve how a decision changed rather than merely
make a shorter summary.

### F18 · P1 — Export turns temporary uncertainty into durable authority

**Evidence:** P7 freezes a snapshot, then asks about unresolved items and name choices.
It does not specify how post-snapshot edits or free-text/image redaction alter that
snapshot. Initials are not a comprehensive content-release check. Network: E01–E05.

- **A — Accepted content only, with omission manifest:** clearer release; can exclude
  useful unresolved questions if the rule is too broad.
- **B — Reviewed mixed export with durable state labels and coverage manifest:** richer
  meeting record; demands careful rendering and release review.
- **C — Internal review bundle followed by a separate external artifact:** strongest
  audience separation; more artifacts and handoff effort.

**Recommend:** B internally, C when the audience changes. Let the person choose the
inclusion/redaction plan, then freeze the final manifest. Distinguish unresolved
questions (legitimate content) from unreviewed claims. Record source revisions,
coverage-through time, omissions and missing citations. Test stale snapshots, hidden
free-text names, missing images and policy revocation while an export is rendering.

### F19 · P1 for integration — Partial external success is neither success nor failure

**Evidence:** P7/S7 promises resumable board push with an ID map. If the provider creates
an item but the response is lost before the ID is stored, the map is insufficient.
Network: E06–E08.

- **A — Downloadable artifact only:** reliable boundary and simplest prototype;
  weakens the claim of preserving work in the team's existing board.
- **B — Create-only push with stable operation markers and read-back reconciliation:**
  useful integration if supported; requires a capability spike and per-item journal.
- **C — Bidirectional synchronized board:** supports ongoing work; adds external edits,
  conflict resolution and permissions far beyond one export.

**Recommend:** A as fallback; B only after verifying the provider's actual marker,
read-back and retry capabilities. Defer C. If reconciliation cannot determine whether
creation occurred, show unknown outcome and ask for targeted resolution; do not blindly
retry. Test partial batch, rate limit, permission loss, moved/deleted remote items and
lost success response. No current provider capability or price is assumed here.

## Common contracts the network requires

### 1. Separate the lifecycles

| Object | States that matter | Transition that must not happen |
|---|---|---|
| Session | Draft, ready, active, paused, closed | Paused → active without current agreement |
| Job | Queued, running, succeeded, failed, cancelled, expired | Cancelled → committed via a late callback |
| Source | Current revision, superseded revision, unavailable, purged | Purged → readable after restore |
| Proposal | Needs review, accepted, rejected, stale | Editing or layout approval → implicit factual acceptance |
| Decision claim | Proposed, contested, confirmed, superseded | Silence or score threshold → confirmed consensus |
| Release | Preparing, ready, delivered, partial, failed, revoked locally | Unknown external outcome → blind duplicate creation |
| Deletion | Access revoked, purge pending, partial failure, verified | Timer elapsed → "deleted" without store verification |

The session state, job state and source state are orthogonal. A paused session may
still allow manual work under policy; a closed session may still have deletion pending.
Avoid one global "done" flag that hides those differences.

### 2. A handoff must carry enough context to reject stale work

Minimum request fields: session ID, actor ID, request ID, payload fingerprint, schema
version, current policy version, operation, source references and expected target
revisions. The server supplies durable sequence and outcome; model output supplies
neither authority nor truth. Same request identity with a changed payload is an error.

A source reference names the source revision and crop/time span. A relationship names
both endpoint revisions and the evidence for the relationship itself. The fact that
two endpoint notes exist does not prove a causal connection between them.

### 3. Recovery has a deadline and a destination

Each worker needs a retryable-error set, max attempts, total deadline, cancellation
check and terminal visible result. Proposed starting policy: at most two automatic
retries for eligible transient local/model failures, with backoff; no retry for
invalid schema, revoked policy or stale acceptance. Tune against the target environment.
External unknown outcomes go to reconciliation, not ordinary retry. Audio saturation
goes to visible stop/gap, not an unbounded backlog. User clarification goes to direct
selection after one unsuccessful exchange. Human review has no fabricated deadline;
it remains unresolved until accepted/rejected or explicitly excluded.

### 4. Measure the complete cost, including cleanup

`Total task effort = setup + capture + waiting that blocks work + source correction
+ review + arrangement correction + export repair + failure recovery`.
Measure elapsed time and active human time separately; parallel work cannot simply be
summed as elapsed duration. End-to-end latency is not the sum of stage p95s, and a fast
first token is not a fast checked answer. Record provider use with dated measured rates
once selected, plus device/storage cost where material. No cost/performance numbers in
this report are empirical outcomes.

## Opportunity order and alternative build sequences

| Sequence | Build order | Best when | Main drawback | Exit before more scope |
|---|---|---|---|---|
| Recommended capture slice | Manual path → photo coverage → source review → reliable local export → lifecycle recovery | Retyping/capture is observed as costly | Does not establish recall benefit | G1 mechanisms and G2 corrected-output advantage |
| Recall slice | Approved transcript → extractive search → checked answer → source revisions → optional live ASR | Lost rationale is the costly moment | Transcript acquisition may dominate | Answer support and retrieval task advantage |
| Live facilitation slice | Human-operated simulation → explicit commands → deterministic arrangements → selective automation | Teams demonstrably invoke the tool in-session | Highest interaction and interruption risk | Command completion, no wrong-target actions and preserved meaning |

Across sequences, prioritize: **coverage and correction**, **precise acceptance**,
**recoverable release**, then **additional inference**. Do not build every detailed
node merely because it now appears in the network. Core/extension labels describe the
proposed implementation sequence, not importance or permanent exclusion.

## Verification performed for this artifact

The accompanying validator checks node/edge identity, required node contracts, route
continuity, connectivity, flaw references and deterministic regeneration. Browser
checks of the explorer are recorded separately in the PR; they verify the documentation
tool, not the proposed product. G0–G4 and the process failure scenarios remain unrun
against a product implementation.
