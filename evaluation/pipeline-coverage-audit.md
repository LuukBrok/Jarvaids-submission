# Pipeline breadth and depth audit

Reviewed 2026-09-15 against main commit `3fa335acadd526fb3c20e81f0b8262a0ea610551`.
Scope: flowchart, pipeline document, concept 001, brainstorm notes, decision/evidence
templates and app directory. This is document verification, not a running-system audit.
The client and server contain placeholders; evaluation findings and evidence synthesis
are templates. No measured accuracy, latency, task benefit or deployment readiness is established.

## Assessment

Breadth is strong at the processing-stage level: eight pipelines cover capture,
commands, visualization, answers, minutes, export and retention. Depth is strongest
in stage inputs/outputs, failure narratives and explicit retreat options. The document
already identifies scope and provisional-review risks; repeating those is not new evidence.

The weak point is the contract between paths. Typed input, session authority, source
revision propagation, data release and test execution have less detail than ASR and
model selection. Eight named pipelines are not eight implemented or validated capabilities.
The decision baseline adds bounded choices and the protocol adds observable gates.
Both remain proposals until reviewed and implemented.

## Full functional spread

Depth labels: **specified** = stages/fallbacks described; **partial** = a feature or
dependency exists but important lifecycle/contract detail is absent; **deferred** =
deliberately excluded from the proposed first slice. No row means runtime-verified.

| Function IDs | Existing coverage and gap | First-slice disposition / verification |
|---|---|---|
| F1.1–F1.3 audio, ASR, speakers | Specified P1; far-field identity and error propagation unmeasured | Deferred; local processing, saturation and attribution tests before enabling |
| F1.4–F1.6 photo, split, OCR | Specified P2; break-even guessed and dataset correlated | Core; D01/D04, G2 disjoint walls and total correction time |
| F1.7 typed input | Partial; called first fallback but no equivalent pipeline | Core; same validation, identity, review and export path as photo items |
| F2.1–F2.4 minutes, decisions, actions, questions | Specified P6; silence and low edit rates do not establish agreement | Deferred; explicit claim verification and source revisions required |
| F2.5–F2.6 detection and intent | Specified P3; confidence thresholds uncalibrated, referents ambiguous | Explicit typed selection only; D02/D05/D08, T03/T06/T08 |
| F2.7 grounded answers | Specified P5; source presence alone does not establish support | Deferred; source-support scoring, unknown-speaker and contradiction cases |
| F2.8 suggestions | Deliberately no pipeline, despite flowchart toggle | Deferred; separate fixation study, not a latent enabled feature |
| F3.1 model and F3.4 insertion | Partial shared-state contract; stale semantic rebase unspecified | Core; D03–D05, T04/T10 |
| F3.2–F3.3 form and layout | Specified P4; five forms do not establish usefulness; AI label conflicts with deterministic geometry | Human-selected layout; D09/G3 before automatic choice |
| F3.5 review and F3.7 undo | Partial; styling/inverse patch do not handle acceptance or later edits | Core; D03, T04/T05/T12 |
| F3.6 direct manipulation | Partial; large front-end task not given a pipeline | Minimal edit/move required; preserve revisions and keyboard path T14 |
| F4.1–F4.3 join, sync, roles | Partial; link/replay cannot alone establish authorization | Core; D02/D05, T03/T06/T07 |
| F4.4 modes | Partial; quiet mode and idle-trigger layout conflict | Explicit requests only; deferred suggestion mode |
| F4.5 agenda | Feature named, no explicit stage owner or contract | Deferred; manual agenda labels before inferred ones |
| F5.1–F5.2 export | Specified P7; unresolved items and incomplete evidence need durable labels | Core canvas export; minutes deferred; D03/D06, T12 |
| F5.3 external board | Adapter named; no verified provider capability or effort | Time-boxed feasibility spike; local export does not validate board continuity |
| F5.4 archive | Partial; listed in P5 but cross-session behavior not scoped | Deferred; no cross-session retrieval in first slice |
| F6.1–F6.2 consent/locality | Specified gate but recorded-consent bootstrap and remote text path unresolved | D06/D08, G0/T01/T02; raw audio locality alone is insufficient |
| F6.3–F6.4 citations/degradation | Specified across paths; late source edits and bounded saturation lack contracts | D04/D07, T09/T10 |
| F6.5 corrections | Log proposed; every edit currently counted as correction | D10 edit taxonomy and independently scored final artifact |
| F6.6 deletion | Specified P8; payload log, derived indexes, restoration and deadlines incomplete | D06, T11; no retention extension for replay |

## Prioritized implementation issue drafts

These are reviewable backlog entries, not already filed GitHub issues. Priority 1
blocks the relevant trial; priority 2 blocks a defensible benefit claim or later scope.

### P1 — Define session authority and consent transitions

Evidence: flowchart F4.1/F4.3 and pipeline U.2 leave command ownership open; the
concept asks for agreement "on the record" while P1 forbids capture before agreement.
Implement D02/D06. Acceptance: T01/T02/T06/T07 pass, a new participant pauses capture,
and unauthorized participants cannot export or accept by altering a client request.

### P1 — Make review, correction and undo revision-aware

Evidence: P2/S12 inserts proposals, P7 resolves provisional output, X.2 permits
unspecified rebasing. No common accepted-item/source revision contract is defined.
Implement D03/D04. Acceptance: T04/T05/T10 pass for two simultaneous clients;
accepted output retains origin and stale source warnings survive export.

### P1 — Reconcile replay with deletion and late worker results

Evidence: X.4 promises complete log replay; P8 lists five storage tiers without
explicit event-payload/index purge. Its hourly sweep cannot establish every orphan
deletion deadline unless expiry and abandonment detection are defined.
Implement D05/D06. Acceptance: T02/T11/T13 pass with a forced crash and a restored
test backup; no source payload is retained in the deletion receipt.

### P1 — Bound queue saturation and deduplicate intent correctly

Evidence: X.5 calls all queues bounded while audio "never drops"; X.3 collapses
normalized text/speaker/window without selected items or explicit request identity.
Implement D05/D07. Acceptance: T03/T09 pass; repeated transport requests produce one
result, intentional identical requests with different selections both execute.

### P1 — Validate source content and model proposals at the boundary

Evidence: P3 depends on model-parsed operations and P2 imports arbitrary note content;
the shared rules do not define an executable boundary for instruction-like source text.
Implement D08. Acceptance: T07/T08 pass, and invalid source IDs or operation types
cannot enter shared state even when a model returns syntactically valid JSON.

### P2 — Replace guessed break-even with a held-out baseline study

Evidence: P2's four-second estimate and 30% correction rule are unsupported; U.0
suggests ten photographs of one wall. Evaluation folders have no recorded results.
Run G2. Acceptance: publish approved per-wall numerators/denominators, final artifact
errors and total task time, including failures and difficult conditions. No invented results.

### P2 — Test form utility and review burden before expanding

Evidence: P4's variety claim and U.0's preference/glance tests cannot show task benefit;
X.4 equates edits with corrections. Implement D09/D10 and run G3/G4. Acceptance:
compare simpler baselines, preserve minority material, classify edits and report review time.

### P2 — Verify external-board continuity independently

Evidence: concept 001 makes board write-back core; P7 allows cutting it, and the app
contains no integration. Acceptance: a time-boxed spike records actual access,
create/update behavior, provenance preservation, retry behavior, export limitations
and dated cost evidence before a provider is selected. Failure changes the product claim.

## Critical limits of this review

No models, users, APIs or live sessions were benchmarked. The existing numerical
budgets remain hypotheses. The design system is outside this review. Screen behavior and assistive-technology
support need runtime testing. The current work makes decisions and tests concrete; it does not
turn design documentation into an implemented prototype.

## Expanded process analysis

The [process deep dive](process-deep-dive.md) extends this inventory with 70 nodes, 134 connections and 19 flaws/opportunities, each comparing three solutions. The [interactive network](../deliverables/documentation/process-network.html) exposes the contract and failure/recovery connections of each node. This additional detail is a design specification, not evidence of implementation maturity.
