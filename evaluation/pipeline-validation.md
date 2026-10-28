# Pipeline verification protocol

Status: test plan; **no empirical results yet**. Date: 2026-09-15.
Decision baseline: [D01–D10](../decisions/pipeline-decisions.md).
All numerical gates below are proposed pilot criteria, not measured performance.
Assign a responsible team member and freeze criteria before collecting results.

## G0 — Establish the allowed trial and the current workflow

Owner role: research lead. Observe or simulate the existing capture/retyping task;
document task boundaries, interruptions, equipment and what counts as an accepted
export. Confirm participant and teaching-team requirements before collecting real
recordings. Synthetic cases can validate mechanics but cannot demonstrate real-team
benefit. Record provider/data permissions before sending source material off-host.

Exit: written trial protocol, retention settings, baseline task, assigned owner and
permitted dataset. If unavailable, continue only with synthetic material and label it.

## G1 — Mechanisms must survive failure

Owner role: engineering lead. Run these scenarios against the eventual prototype;
their presence here is not a passing test result.

| ID | Trigger | Required observable result |
|---|---|---|
| T01 | Upload/record before agreement | No media accepted and no model invoked |
| T02 | Withdraw while image/model job is in flight | Capture stops; old-policy result cannot appear later |
| T03 | Retry identical request after reconnect/restart | Exactly one outcome; deliberate new request still runs |
| T04 | Accept a proposal after its source/canvas changed | Stale state and new preview; no overwritten work |
| T05 | Undo after a second person edits affected items | Conflict preview; later human work preserved |
| T06 | Revoke participant role while request waits | Commit denied by current server permissions |
| T07 | Ask for an item from another session | No data or mutation crosses the session boundary |
| T08 | Source note contains a command or HTML markup | Treated as content; no operation or script executes |
| T09 | Queue saturation and model outage | Bounded resources; visible retry/failure; manual entry usable |
| T10 | Correct source used by two derived items | Both dependencies flagged; no silently current citation |
| T11 | Delete session, restart, then restore a test backup | Payloads remain unavailable; no resurrection or replay publication |
| T12 | Export while review/minutes are incomplete | Explicit unresolved/coverage state in preview and export |
| T13 | Re-run stored outputs vs re-run models | First reproduces state; second stays in isolated evaluation storage |
| T14 | Keyboard-only intake, correction, acceptance and export | All steps operable; focus retained; status announced |

Exit: all applicable scenarios pass with evidence and build version. T11 inspects all
configured stores and logs, not just a filesystem search. Deferred audio scenarios
must pass before audio is enabled; do not count them as passing in a photo-only build.

## G2 — Does capture save effort after correction?

Owner role: research lead, with an independent scorer. Use at least ten distinct walls
or compositions spanning glare, angle, overlap, mixed handwriting, Dutch/English and
long/short notes. Repeated photos of one wall are correlated examples, not ten
independent walls. Split by wall/session before tuning; reserve unseen walls for evaluation.
Record notes per condition and mark unsupported conditions instead of hiding them in
an average. This is a small feasibility pilot, not population-level validation.

Compare manual retyping/placement with assisted extraction/review on comparable walls,
counterbalancing order and avoiding memorization of the same wall. Measure from task
start to a checked export, including upload, waiting, correction and retries. Preserve
failed trials. Independently label note boundaries and text; adjudicate disagreements.

- Segmentation precision = matched predicted notes / all predicted notes.
- Segmentation recall = matched ground-truth notes / all ground-truth notes.
- Match one-to-one using a predeclared overlap criterion; report split/merge errors.
- Text fidelity = correctly transcribed notes / matched notes, with a documented
  normalization policy. Also report fully correct notes / all ground-truth notes.
- Record missed notes, invented notes, unresolved crops and corrections left in export.
- Report per-wall time ratio and median/range, plus each difficult condition.

Proposed proceed gate: at least 80% segmentation precision AND recall, at least 80%
matched-note text fidelity, median total task time at most 80% of manual, and final
content error rate no worse than manual. Critical invented decisions or owners stop
promotion. If a condition fails, restrict supported capture conditions or improve and
retest held-out material. Do not declare segmentation failure intrinsically unfixable.
The older four-seconds-per-note estimate and 30% correction rule are hypotheses;
observed total task time decides whether the tool helps.

## G3 — Does structure preserve meaning and help a task?

Owner role: design/research lead. Compare original arrangement, plain list,
human-selected layout and automated form selection on the same source sets, with
order counterbalanced. Ask participants to find a concern, identify a decision and
recover its rationale. Use independently checked answers, not preference alone.
Report completion time, answer accuracy, omitted notes, unsupported relationships,
minority/disagreement preservation and changes needed to keep the result.

Proposed gate to enable automated form choice: at least 20% median task-time gain over
the best simpler baseline without lower answer accuracy or invented relationships.
Report sample size and uncertainty; inconclusive results retain human selection.
Do not reward the model merely for distributing outputs over five visual forms.
Test proactive ideation separately only after capture value is demonstrated; measure
idea breadth and fixation with a defined coding scheme, not satisfaction alone.

## G4 — Operate a complete session, then choose the next slice

Owner role: facilitator with engineering observer. Run intake → review → accepted
artifact → export → deletion with 2–8 simulated clients first, then permitted teams.
Record model-off completion, queue age, repeated requests, unresolved proposals,
facilitator review minutes, actual payload/token use, peak storage and p50/p95 latency.
For small samples report each run instead of a misleading stable percentile estimate.

Exit: G1 still passes, G2 benefit survives end-to-end use, and the facilitator can
finish review within the allotted task time. If over half of proposals remain unresolved,
redesign review before adding features. Record the operating cost with dated provider
rates only after a provider is chosen; do not invent a cost ceiling for the team.
Then choose exactly one next track: board integration, recall or live command handling.

## Result record required for every gate

`date, gate_id, owner, build_ref, dataset_ids, synthetic_or_real, participant_count,
session_count, device, model_version, prompt_version, settings, baseline,
metric_numerator, metric_denominator, per_condition_results, failures,
exclusions_and_reasons, conclusion, next_decision`.

Keep identifying source material out of Git. Store only approved de-identified
evidence or synthetic fixtures. An empty result is "not run", never zero errors.
