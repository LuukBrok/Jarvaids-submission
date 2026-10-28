# Week 4 midpoint submission

**Group 3** *tentative* · Luuk Brok · Pieter Borst · Julie van Veelen · Roselique van den Brink

Two deliverables. **A** is the annotated Week 3 material with the group's
one-page summary. **B** is the seven-minute design proposal: the deck, the live
demo, and the documents the deck cites.

Both are built by `deliverables/week4-midpoint/package.sh`, run from the
repository root on the group's own machine. The script writes to
`.local/submission/<timestamp>/` and gathers the raw material at run time from
wherever it then sits. It is a script rather than a list of steps because most
of deliverable A is not in git, so packaging is a hand copy under time pressure,
and a script says out loud what it could not find instead of leaving a silent
hole. Every file below is listed with what it is; the zip also carries
`CONTENTS.md`, generated at run time, which lists what was actually included on
the day and what was absent.

---

## Deliverable A: annotated Week 3 material

Submitted as `deliverable-A.zip`.

| File in the zip | What it is |
|---|---|
| `CONTENTS.md` | Generated when the zip was built: every file in it, and every expected item that was absent. The authority on what this zip actually holds |
| `annotations/INDEX.md` | Every Week 3 artefact, where it is, whether it was read here, which annotation file covers it, and whether the group has edited that file yet |
| `annotations/GAPS.md` | The record of what the Week 3 material does not contain, one line per artefact type the brief names |
| `annotations/interviews-mapit-report.md` | 10 annotations on the MapIt report and its manifest. The interviews are reached through this report, not through the transcripts |
| `annotations/frameit.md` | 11 annotations on the three FrameIt files: the interview, the redacted conversation and the tool summary |
| `annotations/flipchart.md` | 12 annotations on the two flip-chart photographs of 11 September and the typed notes taken from them |
| `annotations/group-summaries.md` | 11 annotations on the group's one-page summary V2 and on the Dutch week 3 summary |
| `one-page summary V2.md` | The group's own one page of what Week 3 taught us. Placed at the top of the zip as well as in its original folder, so it does not have to be hunted for |
| `raw/week3/flipchart/flipchart-1-opportunity-and-evidence.jpeg` | Photograph of the first flip-chart sheet, opportunity and evidence |
| `raw/week3/flipchart/flipchart-2-proposed-tool-and-questions.jpeg` | Photograph of the second sheet, the proposed tool and the open questions |
| `raw/week3/flipchart/structured-brainstorm-notes.md` | The typed version of those two sheets. It is a tidied version, not a transcription: it carries material that is on neither sheet, which `flipchart.md` annotation C10 records |
| `raw/week3/interviews/`, `raw/week3/mapit/`, `raw/week3/frameit/` | The intended homes of the recordings, transcripts, MapIt outputs and FrameIt conversations. Empty in the repository; the material is copied in on the group's machine before the zip is built, and the script reports each one that is still empty |
| `week 3 materials/` | The three recordings, three transcripts, the MapIt report in four formats, `manifest.json`, the three FrameIt files, the Dutch summary and the session photograph, copied straight through if that folder is in the checkout at packaging time. Not in this branch, by design: see below |

## Deliverable B: the design proposal

Submitted as `deliverable-B/` and as `deliverable-B.zip`, the same content.

| File | What it is |
|---|---|
| `SUBMISSION.md` | This file, copied in so the folder reads on its own if it is detached from the rest |
| `slides/index.html` | The deck, ten slides at 1920x1080, opens in a browser with no build step and no network |
| `slides/NOTES.md` | Presenter notes, one block per slide with a time target; the targets sum to under seven minutes |
| `slides/deck.pdf` | The deck printed, ten pages, for the case where the browser will not co-operate in the room |
| `demo/RUNBOOK.md` | The exact live sequence, what is said out loud, and what to do when a step fails |
| `demo/start.sh` | Brings the backend and the static client up from cold and seeds one active session |
| `demo/step.sh` | Drives the journey over HTTP if the browser dies mid-demo |
| `demo/stop.sh` | Stops whatever `start.sh` started |
| `demo/make_wall.py` | Draws `wall.png`, the synthetic sticky-note wall used when no real photograph is to hand |
| `demo/wall.png` | That wall, ready to upload during the demo |
| `demo/shots.mjs` | Takes the fallback screenshots, so they can be regenerated rather than kept by hand |
| `demo/fallback/01-typed-note.png` to `05-drag.png` | Five screenshots of the journey: a typed note, the marked wall, the provisional readings, an accepted note, a drag on the canvas. The fallback for a demo that will not start |
| `documentation/stack.md` | Every component named on slide 8, labelled built or candidate or proposed, with licence and how to try it. The copy of record when somebody asks "which model" |
| `documentation/flowchart.md` | The product and the F1.1 to F6.6 numbering the deck cites |
| `documentation/pipelines.md` | The pipelines behind slides 6 and 7, stage by stage. Every number in it is a proposal |

The markdown twins of the documentation are submitted, not the HTML ones: they
carry the same content at a fraction of the size, and they are what the deck
cites.

---

## What is missing, and why

The full record is `annotations/GAPS.md` in deliverable A, one line per artefact
type the brief names. It is not repeated here, because two copies of the same
list drift and nobody diffs them. Condensed:

- **The interview recordings, transcripts and the MapIt session photograph exist
  but were not read for these annotations.** They carry identifiers, so they
  were not opened and they do not enter the public repository. The interviews
  are annotated through the MapIt report and the group's own summaries instead,
  which `interviews-mapit-report.md` states at its top. They are submitted from
  the group's machine.
- **No interview notes and no consent records were found.** Nothing records what
  the interviewers noticed at the time, independently of the recordings, and the
  group should confirm the consent records exist before submitting.
- **The MapIt material is partial.** Only the markdown report and the manifest
  were read; the other three formats are exports of the same report. Four
  uploads in `manifest.json` are marked cancelled with no reason recorded, so it
  cannot be told whether material was lost.
- **The FrameIt record is partial.** The conversation copy is hand-redacted
  rather than mechanically exported, because the export failed for want of a
  Python runtime. No retry and no use of the fallback prompt is recorded, so
  either none happened or the record of it is missing.
- **Two things cannot be traced.** The source behind finding 8 of the Dutch
  summary, a separate conversation about learning a 3D modelling tool, is not in
  the folder; and version 1 of the one-page summary is absent, so what the group
  changed between the versions cannot be seen.
- **The flip chart is the one complete item**, with one caveat: the typed file
  adds material that is on neither sheet.
- **Nothing from Week 3 other than the flip chart is in `evidence/raw/week3/`
  yet.** The material is on the `main` branch under `week 3 materials/`, where a
  decision about it is still open. Deliverable A is submitted as a zip from
  `evidence/raw/`, so the group moves it there before packaging.

Nothing absent has been recreated. The brief asks for the gap to be noted
instead, and a reconstructed artefact would be indistinguishable from a real one
six months from now, which is the failure this whole project is about.

## How this was made

This is a course project assessed partly on traceability of AI involvement, so
the split is stated rather than implied.

**AI-drafted, and labelled as such in the artefact itself:**

- **The annotations.** All four files, `INDEX.md` and `GAPS.md` were drafted by
  an AI agent. Every one carries the heading **AI draft, pending group edit**,
  and every row of the index says the group has not edited it yet. Anything
  still marked that way at submission is submitted as an AI draft. That is
  honest and the brief permits it; presenting a draft as the group's view is not.
- **The "how" slides and `documentation/stack.md`.** Slides 6, 7 and 8 and the
  stack document were AI-built from `pipelines.md` and from the repository as it
  stands. Every name on them sits in a cell labelled built, candidate or
  proposed. No model named there has ever been run in this project, no number
  on them is a measurement, and the versions and licences in `stack.md` are to
  be verified before anything is installed.
- **The demo scripts** in `demo/`, and `package.sh` and this file.

**The group's own work:**

- **The one-page summary** of Week 3, written by the group.
- **The flip chart**, made in the room on 11 September, photographed and typed
  up by the group.
- **The interviews**, arranged, conducted and recorded by the group.
- **Every judgement call**, including which annotations survive, what goes on
  slide 3, and what the proposal claims.

**What review actually happened:** the AI-drafted material was directed by the
group and checked by the repository's automated checks. It has not been read
line by line by the group. Where that is still true at submission, the artefact
says so on its own face rather than only here.

**The raw Week 3 material is submitted from the group's own machine, never from
the repository:** recordings, transcripts and consent records stay in
`evidence/raw/`, which is gitignored, and `package.sh` copies them at run time
without ever writing them into the working tree.
