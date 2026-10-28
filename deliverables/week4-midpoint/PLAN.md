# Week 4 plan: two deliverables by Wednesday 23 September

Written Tuesday evening. Presentation is tomorrow, in class. The working window
is one hour fifteen tonight, one rehearsal tomorrow morning.

Roles: **the group** supplies material, makes every judgement call, and
presents. **Opus** builds everything else from this plan. **Fable** wrote the
plan and checks the pieces against it.

Two deliverables, from the brief:

- **A.** Annotated Week 3 materials plus a one-page summary of what we learned
  and take forward. Raw material, annotations and summary submitted together.
  Gaps noted, never recreated.
- **B.** A seven-minute design proposal: what and for whom, value and rationale,
  how it would work. Slides plus a live demo. A design proposal, not a product
  demo: the flowchart and worked examples carry it, the running client is one
  illustration inside it.

---

## What is true right now, so nobody plans against a wrong picture

- The repository holds two flip-chart photographs and their typed notes from
  Week 3, and nothing else from that week. Interviews, MapIt outputs and FrameIt
  conversations exist, arrive in about thirty minutes, and the group's own
  expectation is that they are thin. Plan accordingly: **W2 annotates whatever
  arrives, W3 and slide 3 lean on the concept's reasoning where the material
  is thin, and GAPS.md says so.** Nothing in W2 or W3 starts until they land.
- The client works end to end in a browser: session, agreement, typed and
  photographed capture, review with correction, canvas drag, export. Verified
  by `app/client/tests/journey.mjs`.
- The photograph path reads notes with a **labelled synthetic adapter**. A
  photographed wall comes back as "FIXTURE ONLY, sample note 1; no OCR
  performed." No handwriting recognition has ever run in this project. The
  live demo must say so out loud, once, and move on. In a design proposal that
  is a strength: the flow is real, the reading is a stand-in, and the audience
  is told which is which.
- Speech is designed (F1.2 in the flowchart) and not built. It is presented as
  the designed next step with its consent question attached, not as a feature.
- The midpoint `report.md` in this folder already states what is and is not
  established. It is source material for the slides, not a deliverable itself.

---

## Workstreams

### W1. Materials intake. Group. Blocking.

Put every Week 3 artefact into `evidence/raw/week3/`, one subfolder per kind:

    evidence/raw/week3/interviews/     recordings, transcripts, notes
    evidence/raw/week3/mapit/          whatever MapIt produced
    evidence/raw/week3/frameit/        every conversation, including retries
                                       and any use of the fallback prompt
    evidence/raw/week3/flipchart/      the two photographs already in
                                       "meeting notes/", copied here

`evidence/raw/` is gitignored, on purpose: identifiable material never enters
the public repository. The deliverable is submitted as a zip from this folder,
not through git. Filenames should say what the thing is and when it was made.

If a named artefact does not exist, do not make one. Write its name in
`deliverables/week4-midpoint/annotations/GAPS.md` with one line on why. The
brief asks for exactly that.

**Done when:** the folders exist with whatever is real in them, and GAPS.md
lists whatever is not.

### W2. Annotation pass. Opus drafts, group decides. Depends on W1.

One markdown file per source artefact in
`deliverables/week4-midpoint/annotations/`, named after the artefact.

Layout of each file, so original and comment can never be confused:

- The original, quoted verbatim in a blockquote, or for a recording a table of
  timestamps with a short description of what is said at each.
- Under each passage, a comment block headed **AI draft, pending group edit**.
- Every comment says which of the brief's four it is: useful, surprising,
  unclear, unconvincing. And which verdict: keep, question, reject.
- No comment invents a fact about the material. If a passage is ambiguous, the
  comment says it is ambiguous and what the two readings are.

The group then goes through each file and does one of three things to every
draft: keeps it, rewrites it in their own words, or deletes it. When they are
done they change the heading to **Group comment**. Any draft still marked AI
draft at submission is submitted as an AI draft, labelled. That is honest and
the brief permits it; passing off a draft as the group's view is not.

Also in this folder: `GAPS.md` from W1, and `INDEX.md` listing every artefact,
its annotation file, and whether the annotation was edited by the group.

**Done when:** every artefact in `evidence/raw/week3/` has an annotation file,
GAPS.md is complete, and INDEX.md is accurate.

### W3. One-page summary. Done by the group on 22 September; nothing is drafted here.

**Superseded.** The group wrote its own one-page summary,
`one-page summary V2.md`, in its own voice and from the transcripts the
agents may not read. It says what this section asked for: what was learned,
and what is taken forward. `decisions/decision-log.md` records the choice
not to write a second one; `package.sh` copies the group's summary into
deliverable A from wherever it sits. The original brief is kept below as the
record of what was asked.

`deliverables/week4-midpoint/summary.md`, and a rendered `summary.pdf` or
`summary.html` that is genuinely one page.

Content, in this order:

1. What we set out to learn in Week 3, in two lines.
2. What we learned, as five to seven findings, each pointing at the artefact
   it came from. Findings only, not activities.
3. What we take forward into the proposal, and what we drop, with a reason.
4. What was missing or weak, taken from GAPS.md.

Free format per the brief. If a sketch or diagram says it better than prose,
use one, but the page must still read on its own. One page is a hard limit:
at 11pt, that is about 450 words plus one small figure.

**Done when:** it fits on one page, every finding traces to an artefact, and
the group has read it and changed at least the things they disagree with.

### W4. Presentation. Built by the coordinator, group presents.

Nineteen slides in seven minutes. Each slide has a chapter label, a plain
heading naming its subject, one visual or one short paragraph, and a footer
with the source and the page number. Headings describe; they do not argue.
The explanation is in `slides/NOTES.md`. The product concept, the features
and the voice-command example come from the structured brainstorm notes of
11 September. The two flowcharts from `documentation/flowchart.html` are
slides, with the journey's middle band enlarged; pressing Z shows a flowchart
on the whole screen. Targets sum to 7:00.

| # | Slide | Target | What the room sees |
|---|---|---|---|
| 1 | Title | 0:10 | The drawn wall, the one-sentence description, the group |
| 2 | Project background | 0:20 | The three recurring problems, numbered |
| 3 | Users and context | 0:15 | The wall, one facilitator, six participants |
| 4 | Product concept | 0:25 | Input, overview, on request: three bands of boxes |
| 5 | Features | 0:30 | Eight cards, each with its F-numbers and status |
| 6 | Voice commands | 0:25 | The six steps from a spoken sentence to a confirmed change |
| 7 | Findings from week 3 | 0:20 | Four findings, each with its source |
| 8 | Design question | 0:20 | The question as a quotation |
| 9 | Provisional output | 0:20 | Two notes at poster scale, one dashed, one solid |
| 10 | User journey | 0:15 | The journey flowchart, whole |
| 11 | User journey, during the meeting | 0:25 | The middle band of the journey, enlarged |
| 12 | System architecture | 0:20 | The architecture flowchart |
| 13 | Functions in scope | 0:20 | Six tiles with counts and a status dot per function |
| 14 | From photograph to notes | 0:30 | Three captures of the client |
| 15 | Speech pipeline | 0:15 | Nine stages, three dashed |
| 16 | Technology stack | 0:15 | Five bands of boxes, solid or dashed, the consent gate |
| 17 | Repository and verification | 0:15 | The seven checks, four counts |
| 18 | Live demonstration | 1:00 | A provisional note at poster scale; the demo runs on the other screen |
| 19 | Riskiest assumption and next steps | 0:20 | Three figures: 10, 80 percent, 80 percent |

When somebody asks "which model", the answer is a page reference:
`deliverables/documentation/stack.md`, section 2, which carries the candidate,
the reason it is first choice and how to try it. Do not answer it from memory
on the day, because a name said aloud without its licence and its gate test is
exactly the claim this deck exists to avoid.

Design constraints for the slides, so they look like the project and not like
a template: the design system's two typefaces and ink ladder, white ground,
hairlines not fills, one accent. The flowchart and pipelines pages already
render in that system and can be screenshotted or embedded directly.

Format, decided: **one HTML deck in the design system**, presented
full-screen from the browser, with a PDF exported alongside as the safe copy.
It needs no software on the class machine and it looks like the project. Source
in `deliverables/week4-midpoint/slides/`, `index.html` plus `deck.pdf`.

Speaker notes go in `slides/NOTES.md`: one short paragraph per slide, the
sentence to open on, the sentence to close on, and the timing target. The
presenter rehearses from these once tomorrow morning, timed.

**Done when:** nineteen slides exist, NOTES.md matches them, and a timed
read-through comes in under seven minutes.

### W5. Demo runbook. Opus builds. Independent of W1.

`deliverables/week4-midpoint/demo/RUNBOOK.md` and a `demo/start.sh`.

The script starts the backend and the client server with the right
`--allow-origin`, seeds a session with agreement already given and capture
active, and prints the URL to open. Nothing the presenter has to type live
except what the audience should see them type.

The demo sequence, in this order, because it makes the product's rule visible:

1. Type one note. It goes to Review, not to the canvas. Say why.
2. Photograph the wall (a prepared photograph on the demo laptop, uploaded
   through the real file picker). Mark three notes. Send. They arrive in
   Review, dashed, labelled with the adapter that produced them. Say, once:
   the reading is a stand-in, no handwriting recognition has run; the flow is
   what is being shown.
3. Correct one reading in place, accept it, reject one. Watch the canvas.
4. Drag a note. Say: moving is not agreeing, no review, that is the rule again.
5. Stop there. Export and delete are not worth the seconds.

Fallback, because live demos fail: `demo/fallback/` holds screenshots of every
step above, taken from the real client, and the presenter has them open in a
second window. If anything fails, switch windows and narrate the screenshots.
Nobody in the audience will mind. Everybody will mind a presenter debugging.

A second, smaller fallback: the recorded output of `app/client/tests/journey.mjs`
proves it ran, if anyone asks afterwards.

**Done when:** `start.sh` brings up a seeded session from a cold start in under
thirty seconds on the demo laptop, the sequence has been run through twice
without a hitch, and the fallback screenshots exist and are current.

### W6. Packaging. Opus. Depends on W2, W3, W4.

One zip for deliverable A, built by a script so it is reproducible:
`evidence/raw/week3/` plus `deliverables/week4-midpoint/annotations/` plus the
summary. One folder for deliverable B: the slide file, NOTES.md, the demo
folder. A `SUBMISSION.md` at the top listing what is in each and what is
missing, copied from GAPS.md.

**Done when:** the zip opens on a machine that has never seen the repository
and everything in SUBMISSION.md is actually in it.

---

## Order of work for the one hour fifteen

```
0:00  Opus: W4 slide skeleton and W5 start.sh, in parallel. Neither needs
      the materials.
0:30  Materials land. Opus: W2 on whatever arrived.
0:45  Opus: W5 runbook and fallback screenshots done.
0:55  Opus: W3 summary draft from the annotations so far.
1:05  Group: read the annotations and the summary. Keep, rewrite, delete.
1:10  Opus: slide 3 filled from the summary. W6 package.
1:15  Everything exists. Whatever the group has not edited is labelled as an
      AI draft, and that is what gets submitted if nothing changes.

Wed am  One timed rehearsal from NOTES.md. Run the demo twice from cold.
```

The critical path is W1. If materials arrive late, W2 and W3 shrink to what
arrived, and GAPS.md grows. That is the brief's own instruction and it is fine.

## What is deliberately not in this plan

- Recovering the three interrupted agents' uncommitted work (evaluation
  apparatus, speech path, list reconciliation). It is safe in their worktrees
  and it has nothing to do with Wednesday. Thursday.
- Any new backend or client feature. Nothing built tonight can be rehearsed
  tomorrow.
- Fabricated findings. If Week 3 produced little, the summary says so and the
  presentation leans on the concept's reasoning instead. The brief does not
  reward pretending.

## Decisions taken tonight

| Question | Decision |
|---|---|
| Slide format | HTML deck in the design system, PDF alongside |
| Materials | Group drops them into `evidence/raw/week3/` in about thirty minutes; expected to be thin |
| Presenters | One presenter for slides 1 to 6 and 8, a second runs the demo, so a demo hiccup cannot derail the narrative |
| Group number and names on the title slide | Group 3 (tentative, not yet fixed by the course). Luuk Brok, Pieter Borst, Julie van Veelen, Roselique van den Brink |
| Demo laptop | Whoever runs the demo owns the laptop; `start.sh` is tested on it tomorrow morning, not tonight |
