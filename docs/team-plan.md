# Integration result, 27 October 2026

The combined local snapshot now connects Rosalique's topic summary design and
pipeline, Julie's summary-to-sticky bridge and Pieter's newer interface/calendar
work. [The integration report](../INTEGRATION-20261027.md) names source revisions.
The fictional MP3/photo trial completed, with operator recoveries and remaining
limits recorded in [the trial report](../VOICE-AND-MP3-TEST-20261027.md).
[The tutor guide](../TUTOR-DEMO.md) provides completed-test, archive and fresh-tool
links. The older plans below remain a dated record of the team's decisions.

# Team plan: four work packages and a shared delivery

**Post-trial update, 20 October 2026:** Luuk requested automatic photo region
detection, immediate input application without acceptance, broader command
phrasing and simple growing result cards. WP3/WP4 integration implements these
changes. The PC launcher selects real photo reading and automatic workspace mode.
Original evidence, edit/undo and capture agreement remain. See
[the updated trial](../COMPLETE-LOCAL-TEST.md) and [phrase catalogue](COMMAND-PHRASES.md).

**Integration, 20 October 2026:** Luuk authorised combining all available branches
and publishing one localhost release. WP3 poll/to-do/requirements/calendar execution
is ported into the current main canvas, preserving WP4 real photo reading and the
new drawing/review tools. Julie's summary exploration is available as a separate
local companion; the main-session bridge remains missing. Luuk confirmed that
Rosalique's WP1 implementation is still missing. Use
[the complete trial](../COMPLETE-LOCAL-TEST.md) and current BUILD-STATUS results.


**WP3 progress, 19 October 2026:** voice polling is implemented on
`feature/voice-polls`. The recognised command creates a canvas draft, confirmation
opens it, and speaker-attributed choices, corrections and acceptance use the
existing session store and sync. The full browser journey uses scripted adapters;
Luuk subsequently reported a successful live voting trial and confirmed voice
closing. Multi-person accuracy and latency remain unmeasured. Listen now starts
wake-word recognition without an additional checkbox. This branch is published
separately for the joint integration with the newer main client. See
[the poll guide](voice-polls.md) and `app/server/BUILD-STATUS.md`. Polling uses
the original transcript and shares provider configuration without waiting for
WP1's overview. Phase one on `feature/voice-todo-lists` adds whole-meeting to-do
collection and review; [its guide](voice-todo-lists.md) has the trial script.
Luuk reported a successful to-do microphone trial and requested phase two.
Requirements/wishes now build on that version; [their guide](voice-requirements.md)
has the next trial. Luuk reported that list worked; a subsequent natural-phrasing
issue in poll/to-do creation was fixed and Luuk reported the retest worked.
Automated browser checks exercise all three together. His requested side-by-side
command layout is implemented with readable focus and preserved hand placements.
Luuk confirmed that layout worked and requested the calendar. Phase three on
`feature/voice-calendar` adds date-based day/week/month/year views, unscheduled
items, capture-time/time-zone date resolution, shared to-do IDs and explicit
review of AI changes to accepted task details. See [the calendar guide](voice-calendar.md).
Pause for the calendar microphone trial before claiming live quality.
Combining these branches with the newer main client remains separate. The dated baseline
and live-demonstration checkboxes below remain historical or incomplete.

Updated 14 October 2026 from Luuk's team messages of that date. This is the
current source of truth for priorities, ownership and planning. The existing
flowchart defines the wider product; this plan selects what the team works on
now. A planned task or checkbox is not evidence that a feature works.

## People and priorities

| Package | Owner | Work agreed by the team | Dependencies |
|---|---|---|---|
| WP1: transcript to overview | Rosalique | Turn a transcript into an LLM-generated summary, structure or overview of a brainstorm | Provide output examples to Julie and Luuk |
| WP2: overview to canvas | Julie | Turn the generated overview into actual canvas objects, especially sticky notes, building on her existing canvas work | Consume WP1 output; coordinate canvas creation with WP3 and photo input with WP4 |
| WP3: commands to actions | Luuk | Connect the eight recognised commands to actual backend actions and visible canvas results | Use WP1 generation where needed and WP2 canvas operations |
| WP4: physical notes to canvas | Pieter | Read photographs of physical sticky notes, including handwriting, and integrate them into the same canvas as the other inputs | Coordinate the extracted-note output and integration with Julie and Rosalique |
| WP5: integration and delivery | Everyone | Assemble a coherent, presentable and submittable version and demonstrate it on localhost | Bring together WP1 to WP4; document incomplete parts honestly |

Pieter takes WP4 because the group considers it the hardest package. These are
collaborating work packages, not isolated products: discuss dependencies during
the work instead of waiting for final integration. Owners coordinate their
package; ownership does not prevent helping each other.

## Timing and submission

- **Now through Tuesday morning, 20 October 2026:** make substantial progress
  on all four packages and bring runnable progress, examples and blockers.
  This is the next integration checkpoint, not a promise that everything will
  be finished.
- **Tuesday morning:** proposed joint session to combine the available work
  and make a presentable/submittable version. The earlier suggestion assumed
  a presentation or submission the following week; the exact format and
  subsequent sessions remain to be agreed.
- **Confirmed submission wording:** Wednesday of course week 9, on
  **Brightspace**. The calendar date, submission time and required files have
  not been supplied. Check Brightspace and record them here; do not interpret
  course week 9 as ISO calendar week 9 or silently equate it with next Wednesday.
- **After submission:** Gred has offered an informal session to look at and
  discuss the project. The team sees this as useful; no appointment is booked.
- **Demonstration target:** the integrated product runs on **localhost**.
  Use [LOCAL-TEST.md](../LOCAL-TEST.md) as the existing run route.

## Starting point on main

Baseline inspected: `ad0e17b`, 14 October 2026. See
[LOCAL-FEATURES.md](../LOCAL-FEATURES.md) for the feature inventory and
[BUILD-STATUS.md](../app/server/BUILD-STATUS.md) for verification evidence.

- A browser canvas, notes, groups, review, photo intake and export already exist.
- Real local transcription and speaker matching are integrated. This does not
  establish human-room accuracy or separation of overlapping voices.
- Eight voice-command types are recognised and displayed. **Recognition does
  not yet execute an action or generate canvas content.**
- A separate batch synthesis workflow already produces a provisional proposal
  from photographs and a transcript. It has a fixture and an optional provider
  adapter; it does not write a live session. Read
  [SYNTHESIS.md](../app/server/SYNTHESIS.md) before building a parallel pipeline.
  Real provider quality and cost have not been verified.
- The live photo-reading path is synthetic. Real handwriting recognition and
  integration of that output remain work for WP4.

Check the current branch and code before treating this snapshot as current.
Older gap analyses remain useful history, but their statements that no speech
recognition has run no longer describe the localhost baseline.

## Work package checklists

These are coordination and demonstration checks for the agreed scope, not a
new API specification. The owners choose the implementation together.

### WP1: Rosalique, transcript to summary / structure / overview

- [ ] Turn a brainstorm transcript into a useful LLM-generated overview.
- [ ] Keep the input traceable so the team can inspect omissions or inventions.
- [ ] Share an input and output example with Julie and Luuk early, so WP2 and
  WP3 can proceed before live generation is integrated.
- [ ] Evaluate with brainstorm video/audio, for example a suitable YouTube
  session, and/or fictional transcripts. Record the source and distinguish
  synthetic material from real sessions.

The immediate package starts from a transcript; reuse the existing speech path
when evaluating from audio instead of rebuilding transcription by default.

### WP2: Julie, overview to canvas objects

- [ ] Convert a generated overview into real sticky notes and any needed groups
  on the existing canvas.
- [ ] Test independently with LLM-generated summaries of fictional brainstorms.
- [ ] Confirm that note content, grouping and source references survive the
  backend-to-canvas path and remain available for human review.
- [ ] Share the supported input example and creation route with the other
  owners so commands and photo-derived notes reach the same workspace.

### WP3: Luuk, recognised commands to backend actions

Connect recognised requests to execution and visible results using the existing
backend and canvas. Start from
[VOICE-COMMANDS.md](../app/server/VOICE-COMMANDS.md),
`app/server/genai_server/voice_commands.py`, the service and the client.
The list below tracks **execution**, not recognition:

| Agreed command | Execution and canvas result demonstrated |
|---|---|
| Summarize | [ ] |
| Visualize | [ ] |
| Compare | [ ] |
| Vote | [ ] |
| Suggestion | [ ] |
| To do list | [ ] |
| List of requirements / wishes | [ ] |
| Planning / agenda | [ ] |

- [ ] Agree with Julie and Rosalique what each command should produce and what
  session content it uses before changing their shared interfaces.
- [ ] Show recognised request, backend action and resulting canvas content in
  one local journey. Preserve the original transcript and provisional status.
- [ ] Check that repeated polling or delivery cannot repeat the same action.
- [ ] Report unsupported requests and failed actions visibly instead of
  displaying recognition as successful execution.

### WP4: Pieter, photographs and handwriting to the shared canvas

- [x] Read physical sticky-note photographs, including handwritten text.
  Evidence: 12 of 13 real handwritten notes exact, [photo-reading-2026-10-18](../evaluation/test-cases/photo-reading-2026-10-18.md), PR #38.
- [ ] Develop and evaluate with fictional photographs of brainstorm notes
  where useful; synthetic success is not real-handwriting validation.
- [x] Preserve the photo/region reference and expose uncertain or unreadable
  text for correction rather than guessing it as fact. Evidence: `[?]` on a
  cut-off note and an unreadable status waiting for typing,
  [PHOTO-READING.md](../app/server/PHOTO-READING.md), PR #38.
- [ ] Bring the extracted notes into the same canvas as speech-derived and
  typed input, coordinating shared topics and possible duplicates with WP1/WP2.

Here, the team's word "training" includes testing and iterating on examples,
prompts and integrations. It does not commit the team to fine-tuning a model.

### WP5: everyone, joint integration and hand-in

- [ ] Bring each package's branch/commit, reproducible example, run steps,
  current result and blocker to the Tuesday checkpoint.
- [ ] Merge compatible contributions into one version and run a combined
  localhost journey across the available input and command paths.
- [ ] Make the demonstration presentable, with reliable startup, a clear
  scenario and explicit labels for fixtures and unfinished functionality.
- [ ] Record which results came from fictional examples, actual model calls
  and human trials; keep the AI-use and decision logs current.
- [ ] Confirm the week-9 Wednesday date, time and hand-in requirements on
  Brightspace, then prepare and submit the required artefacts there.
- [ ] Arrange the optional discussion with Gred after submission.

## How to coordinate changes

1. Start from current `main`, read this plan and identify the package owner.
   Make feature branches and pull requests small enough to combine.
2. Exchange one minimal example at each handoff: transcript to overview
   (WP1/WP2), command to generated content and canvas action (WP3/WP1/WP2),
   photo to extracted notes and canvas objects (WP4/WP2).
3. Record the actual input/output shape and source references in the relevant
   API or package documentation when agreed. This plan deliberately does not
   invent a second schema alongside the existing service and synthesis schemas.
4. Coordinate shared-file edits, especially `genai_server/service.py` and the
   canvas client. Discuss a changed interface with its consumers before merging
   it so independently developed work still fits together.
5. In a pull request, name the package, dependencies, what works, how to
   reproduce it, and what remains unverified. Update this plan when ownership,
   timing or scope changes, and tick a task only with linked evidence.

For all packages, generated meaning stays visibly provisional until human
acceptance. Keep secrets and raw identifiable recordings/transcripts out of
tracked files. Use synthetic fixtures to unblock development, label them
honestly, and retain the existing consent, provenance and review rules.

## Brief for a teammate's AI assistant

> Read `AGENTS.md`, `docs/team-plan.md`, `LOCAL-TEST.md` and
> `LOCAL-FEATURES.md` on the current branch first. The four current owners are
> Rosalique (transcript to overview), Julie (overview to canvas), Luuk (commands
> to backend/canvas actions) and Pieter (physical sticky-note photos and
> handwriting to the same canvas). Everyone owns integration and submission.
> Make progress for Tuesday morning, 20 October; submission is Wednesday of
> course week 9 on Brightspace, with the precise deadline still to confirm.
> The demo runs on localhost. Build on existing code, coordinate interfaces,
> and distinguish recognition, generation, execution and human acceptance.
> Report the package, changed interfaces, reproducible result and blockers.

This context is available to assistants through the repository; it does not
automatically update an already-running chat or a teammate's older checkout.
Pull the updated main branch or merge it into ongoing feature branches, and
give an existing AI session the brief above.
