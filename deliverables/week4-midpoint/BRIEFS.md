# Briefs for the builder

One brief per workstream in `PLAN.md`. Each is written to be handed to an agent
as-is. Each ends with the checks Fable runs on the result, so the builder knows
what "done" is measured against before starting.

Every brief inherits these, and they are checked, not requested:

- Read `AGENTS.md` first. No em dashes anywhere. British spelling. Every rule
  carries its reason.
- Nothing invented. A finding without an artefact behind it is not a finding.
  A number without the command that produced it is not a number.
- Anything an AI wrote that the group has not yet edited is labelled as such.
  That includes annotations, the summary and speaker notes.
- Commit on the current branch with a message that says what was built and
  what was not. Do not push. Do not touch `app/`.

---

## Brief W4: the slide deck

**Build** `deliverables/week4-midpoint/slides/index.html`: eight slides, one
`<section>` each, keyboard-navigable (arrow keys, space), full-screen in a
browser, and `deck.pdf` printed from it via headless Chromium at
`/opt/pw-browsers/chromium-1194/chrome-linux/chrome`, one slide per page.

**Use the design system, not a template.** Link
`../../../app/design-system/spec/exemplars/_base.css` for tokens and type. Two
typefaces, ink ladder, white ground, hairlines, one accent, no shadows, no
gradients. Run `./app/design-system/spec/audit.sh` from the repo root and it
must stay clean: the slides are code and the audit sees them.

**Content** is fixed by the table in `PLAN.md` W4. Slide 3 gets a clearly
marked placeholder block until W3 delivers findings; do not fill it from
imagination. Slide 5 embeds the journey diagram: take it from
`deliverables/documentation/flowchart.html` (it is inline SVG in the design
system already) rather than redrawing it. Slide 7 is a title and one line;
the demo happens in the client, not on the slide.

**Speaker notes** in `slides/NOTES.md`: per slide, the opening sentence, the
closing sentence, the timing target from the plan, and at most three bullets
between. Written to be spoken, not read.

**Title slide** carries `GROUP NUMBER` and `NAMES` as visible placeholders
until they are supplied. Make them ugly on purpose so they cannot be missed.

**Checks Fable runs:**
- `index.html` renders in headless Chromium with zero console errors and zero
  failed requests, at 1920x1080 and at 1280x720.
- Exactly eight `<section>` elements; arrow keys move between them.
- `deck.pdf` exists and has eight pages.
- `audit.sh` clean.
- Every F-number on slide 5 exists in `flowchart.md`.
- `NOTES.md` has eight entries whose timing targets sum to at most 7:00.
- No em dash in any file under `slides/`.

---

## Brief W5: the demo runbook and start script

**Build** `deliverables/week4-midpoint/demo/start.sh`, `demo/RUNBOOK.md`, and
`demo/fallback/` with one screenshot per demo step.

`start.sh`, from a cold start: starts the backend on 3000 with
`--allow-origin http://127.0.0.1:5173` and a fresh data directory under
`.local/demo/`; starts `app/client/serve.py` on 5173; creates a session via the
API, acknowledges agreement and activates capture for the facilitator; prints
the client URL and the one join code for a second device. Idempotent: running
it twice gives a fresh session, not an error. Under thirty seconds.

Seed nothing else. The presenter types the first note live; that is the point
of step 1.

`RUNBOOK.md`: the five steps from `PLAN.md` W5, each with what to click, what
to say, and what the audience should see change. Plus the sentence that names
the synthetic adapter, verbatim, so it is said once and the same way every time.
Plus the fallback procedure: which window, which screenshot.

`fallback/`: screenshots taken from the real client for every step, at
1280x800, using Playwright from the scratchpad
(`/tmp/claude-0/-home-user-GenAI/db4d8e14-4f99-5208-b0b1-60ea9d551511/scratchpad/node_modules`,
Chromium at the path above). Use a real photograph of sticky notes for step 2
if one is available in `evidence/raw/week3/flipchart/` by then; otherwise a
generated one from `evaluation/` and say which in the runbook.

**Checks Fable runs:**
- `start.sh` from a clean `.local/demo/` reaches a printed URL in under 30 s.
- Opening that URL shows an active session with agreement already given.
- Running `start.sh` again produces a different session id.
- `fallback/` has at least five screenshots and each is under 400 KB.
- `RUNBOOK.md` contains the adapter sentence and the fallback procedure.

---

## Brief W2: annotations. Starts when `evidence/raw/week3/` has content.

**Build** one file per artefact in `deliverables/week4-midpoint/annotations/`,
plus `GAPS.md` and `INDEX.md`, exactly as `PLAN.md` W2 lays out.

Read every artefact in full before writing a word. For a recording without a
transcript, listen if a transcript cannot be produced locally with what is on
this machine; if neither is possible, the annotation is a timestamped note of
what could be determined and GAPS.md records the limitation.

Each comment carries two labels: one of useful, surprising, unclear,
unconvincing; and one of keep, question, reject. Every comment block is headed
**AI draft, pending group edit**. Do not soften a judgement because it is
unflattering to the material: an unconvincing interview answer, labelled
unconvincing, is exactly what the brief asks for.

`GAPS.md`: every artefact type the brief names that is absent or partial, one
line each, with what was expected and what exists instead.

**Checks Fable runs:**
- Every file in `evidence/raw/week3/` has a row in INDEX.md and an annotation
  file, or a line in GAPS.md, never neither.
- Every comment block has both labels and the draft heading.
- Original text is only ever inside blockquotes or timestamp tables.
- No comment asserts something about the material that the quoted passage
  above it does not contain.

---

## Brief W3: the one-page summary. Starts when W2 is substantially done.

**Build** `deliverables/week4-midpoint/summary.md` and `summary.pdf`, following
`PLAN.md` W3. Every finding names the annotation file it comes from. Where the
material is thin, say so and lean on `ideation/concepts/001-jarvaids-meeting-assistant.md`
for what we take forward, marking those points as reasoning rather than
evidence.

Render the PDF from a small HTML page in the design system, headless Chromium,
A4. If it runs to two pages, cut, do not shrink the type below 11pt.

**Checks Fable runs:**
- `summary.pdf` is exactly one page at A4.
- Every finding has a source in `annotations/` or is marked as reasoning.
- The four sections from the plan are present in order.
- Marked as AI draft until the group edits it.

---

## Brief W6: packaging. Starts when W2, W3 and W4 exist.

**Build** `deliverables/week4-midpoint/package.sh` producing
`deliverable-A.zip` (raw materials, annotations, summary) and
`deliverable-B/` (slides, NOTES.md, demo folder), plus `SUBMISSION.md` at the
top listing contents and gaps.

**Checks Fable runs:**
- Unzip into an empty directory; every path SUBMISSION.md names exists.
- The zip contains nothing from `.git`, `node_modules` or `.local`.
- Running `package.sh` twice gives identical listings.

## W4b. The "how" slides, in detail. Opus builds. Depends on W4.

**Why this exists.** The user reviewed the W4 deck and asked for the "how it
would work" part to be specific: do we draw boxes around the physical sticky
notes, which model reads them, what the speech path looks like end to end, and
which dependencies, software and APIs are involved, by name. Slides 5 and 6
today say none of that, while `deliverables/documentation/pipelines.md`
already holds it stage by stage. The deck must draw on that document, not
invent a second one.

**The line that must never blur.** Two kinds of statement go on these slides,
and every box must be visibly one or the other:

- **Built today.** True of the repository as it stands, verified below.
- **Proposed.** From `pipelines.md`, where "every number in it is a proposal",
  or a named candidate technology that has not been run here. A candidate is
  a candidate: never a result, never a measurement.

Naming a model we have never run is a design decision and belongs on a design
proposal. Presenting it as though it had been run is the failure the product's
own rule exists to prevent. Where a choice is open, say it is open and say
what test decides it.

**Built today, verified (do not restate differently):**

- Server: Python 3.11, standard library HTTP server, SQLite via `sqlite3`,
  Pillow to decode, strip and re-encode photographs. No framework. 247 tests,
  147 mutation guards.
- Client: plain ES modules, no build step, served by `app/client/serve.py`;
  delta sync by bounded polling (decision log: polling, not WebSocket).
  Playwright drives the journey test only.
- Photograph path: **a person drags a box around each note in the browser**;
  the boxes are stored normalised; the server strips metadata and re-encodes
  the pixels; an `Extractor` protocol receives the image and the boxes; the
  only implementation is `FixtureExtractor` (provider `fixture`, model
  `synthetic-v1`, `synthetic: true`), and `/health` reports `live_ocr: false`.
  No handwriting recognition has ever run in this project.
- Review: correct in place, accept, reject; anything not written by a person
  is drawn provisional; a drag is `item.place` with no review.
- Export: JSON and Markdown. No PNG, no PDF, no board push.
- Speech: nothing. No audio capture, no transcription, no diarisation.
- Before any paid adapter is added, `API.md` requires deadlines, idempotency
  keys, hard cost limits and remote cancellation; no provider or price has
  been selected.

**Proposed, from `pipelines.md` (cite its section, use its numbers as
proposals):**

- Image, section 2, twelve stages S1 to S12. The box question, answered on
  the slide: today a person draws them; proposed is automatic segmentation
  (HSV region proposals for saturated rectangles first, then an instance
  segmentation model or a vision-language model asked for bounding boxes),
  with hand-drawn boxes kept as the correction path. Reading is one vision
  model call per crop, batched. Progressive reveal: geometry at about 3.5 s,
  text by about 7.6 s for 30 notes. The gate before building it: ten real
  photographs through two or three vision models, 80 percent separated and
  80 percent read, measured separately. Break-even is roughly under 30
  percent of notes needing correction.
- Audio, section 1, nine stages S1 to S9: `getUserMedia` 16 kHz mono, 20 ms
  frames; high-pass and level; a Silero-class VAD in WASM on the client;
  chunk on 400 ms silence with a 12 s hard cut; binary websocket; a Whisper
  large-v3-turbo or medium class model on our own server (F6.2: audio does
  not leave it); speaker embedding plus online clustering; glossary
  normalisation; partial then final segment on the bus. 2.7 s median to a
  final segment, provisional caption inside 700 ms.
- Command, section 3: push-to-talk, wake phrase or typed; an LLM constrained
  to a closed set of operations with structured output; a confidence gate
  with thresholds in a table, not a prompt; referent ranking in code first.
- Answers, section 5: keyword search plus vector search over 30 s windows
  with a small embedding model; a two-hour meeting is about fifteen thousand
  words, so it fits in memory.
- Export, section 7: PNG and PDF, then an optional push to Miro or FigJam
  with an id map so a second push updates rather than duplicates. F5.3: spend
  one day against the real API before committing.

**Candidate names the slides may carry, each labelled candidate:** for the
Whisper class model, `faster-whisper` (CTranslate2) or `whisper.cpp`; Silero
VAD; `pyannote.audio` for diarisation; OpenCV for HSV proposals, contours and
the homography; for the handwriting reading, to be compared in the gate test:
a hosted vision-language model (Claude, GPT-4o or Gemini class), a local
open-weights one (Qwen2-VL class), and a classic OCR baseline (TrOCR or
PaddleOCR); any structured-output LLM API for intent and slots; a small local
embedding model (bge-small class) with SQLite FTS5 for keywords; Miro REST API
v2 for the board push, noting that Figma's REST API does not write canvas
content, so FigJam would mean a plugin, to be verified. One open decision to
state plainly: audio stays on our server by design (F6.2); whether a
photograph may go to a hosted vision model is undecided and is a consent
question, not a technical one.

**The layout, ten slides, seven minutes:**

| # | Slide | Target |
|---|---|---|
| 1 | Jarvaids, the one sentence | 0:20 |
| 2 | What, and for whom | 0:40 |
| 3 | What Week 3 told us (placeholder stays until the summary exists) | 0:40 |
| 4 | Value, and the rule everything follows from | 0:40 |
| 5 | How: the journey (existing diagram, shorter talk) | 0:30 |
| 6 | How: a wall becomes notes. Built column and proposed column; the box question answered; the reading candidates; the gate numbers | 0:50 |
| 7 | How: speech, end to end. The nine stages condensed, the named stack, a banner that none of it is built, the latency line | 0:40 |
| 8 | The stack, named: one table, component by component, built today against proposed. The "it answers, it does not volunteer" argument survives here as a short strip, because it is the reason the command and suggestion stages are shaped as they are | 0:40 |
| 9 | Live demo | 1:20 |
| 10 | The riskiest assumption, and the next step | 0:30 |

Sum 6:50. The old slide 6 content is folded into slide 8 and slide 4's notes;
its honesty footer about the fixture adapter moves to slide 6, where the
reading is discussed.

**Constraints.** Same file, same stage, same design system as W4:
`deliverables/week4-midpoint/slides/index.html`, 1920x1080 sections,
`_base.css` linked, the three diagram tokens for human, model and guardrail,
dashed outline wherever a model runs. British spelling, no em dashes. Every
F-number cited must exist in `flowchart.md`. Do not touch `app/`, `demo/` or
anything outside `slides/` and the W4 rows of `PLAN.md`. Do not commit: the
integration is reviewed and committed by the coordinator.

**Done when, and Fable checks each:**

1. Ten `<section>` elements; headless render at 1920x1080 with zero console
   errors and zero failed requests; screenshots of slides 6, 7 and 8 read
   back for overflow and legibility at the back of a room.
2. `deck.pdf` reprinted, ten pages.
3. `app/design-system/spec/audit.sh deliverables/week4-midpoint/slides` clean;
   no em dash in any changed file.
4. Every model, library and API name on a slide sits in a cell or box labelled
   built or candidate or proposed; none appears next to a number that reads as
   a measurement.
5. `NOTES.md` rewritten for ten slides with targets summing to 7:00 or under,
   and the "say once" line about the stand-in reading placed on slide 6 and
   on slide 9.
6. `PLAN.md` W4 table updated to the ten-slide layout with the same targets.

### W4b amendment: name real solutions, draw the stack, and document it

The user's review of the W4b brief: candidates are fine, it is a proposal, but
name actual existing solutions on the slides, draw the stack so it is clear
what uses what, and document the candidates so the team can go and use them.
Three additions to W4b, same constraints, same acceptance checks plus three.

**1. The candidate list.** These are the names to use, on the slides and in
the document, each labelled candidate. Versions and licences are as the
coordinator recalls them in September 2026 and the document must say "verify
the version and licence before installing" once at the top, because a name in
a slide is not a dependency pin. Where two candidates are listed, the first is
the one to try first and the reason is given.

| Stage (F-number, pipelines.md section) | Candidate | Runs | Why this one, and what decides it |
|---|---|---|---|
| Audio capture, F1.1 (1, S1 to S2) | Browser `getUserMedia` plus an `AudioWorklet` | Client | No dependency at all; it is the platform |
| Voice activity, F1.1 (1, S3) | Silero VAD, ONNX weights, in the browser through `onnxruntime-web` (the `@ricky0123/vad-web` package wraps exactly this) | Client | Small enough to run per frame in WASM; MIT licence |
| Audio transport (1, S5) | WebSocket; on the Python side the `websockets` library, since the standard library has none | Server | The one place the built polling sync is not enough: audio is continuous |
| Speech to text, F1.2 and F6.2 (1, S6) | Whisper large-v3-turbo weights (MIT) run with `faster-whisper` (CTranslate2) on one GPU; `whisper.cpp` for a CPU or Apple silicon fallback at lower accuracy; streaming through `whisper_streaming` or WhisperLive | Server, local | Whisper is the multilingual option, which matters for Dutch and English in one sentence; NVIDIA Parakeet or Canary are faster but English-centred. The gate test in pipelines.md Unknowns decides: under 15 percent word error rate |
| Speaker separation, F1.3 (1, S7) | `pyannote.audio` 3.x (MIT code; gated weights on Hugging Face, terms must be accepted); `diart` for the online, streaming variant | Server, local | Gate: diarisation error rate under 20 percent with overlap, or the tool stops using names |
| Wake phrase, F2.5 (3, S1) | openWakeWord (Apache 2.0); Picovoice Porcupine as the commercial alternative | Client | Only if the observation test says push-to-talk is not enough |
| Photograph preparation, F1.4 (2, S2) | Browser Canvas API for orientation and downscale; `exifr` if EXIF orientation must be read by hand | Client | No server dependency; GPS is stripped before upload |
| Image sanitising (2, S3) | Pillow | Server | **Built today** |
| Quality gate and rectification (2, S4 to S5) | OpenCV: variance of the Laplacian for blur, contour detection plus `findHomography` and `warpPerspective` for the wall plane | Server | Classical, no model, fast; the homography is what maps a note back onto the original photograph |
| Note segmentation, F1.5 (2, S6) | First OpenCV HSV thresholding for saturated rectangles; then Segment Anything 2 (SAM 2, Apache 2.0, Meta) for masks from box or point prompts, or Florence-2 (MIT, Microsoft) asked for "sticky note" as open-vocabulary detection; a Ultralytics YOLO fine-tune is the last resort because it needs a labelled set and its licence is AGPL | Server, local | Gate: 80 percent of notes correctly separated on ten real photographs. Today a person draws the boxes, **built**, and that stays as the correction path |
| Handwriting reading, F1.6 (2, S8) | To compare in the gate test, three kinds: a hosted vision-language model (Claude through the Anthropic Messages API, GPT-4o, or Gemini), a local open-weights one (Qwen2.5-VL 7B, Apache 2.0), and a classic OCR baseline (TrOCR handwritten, MIT; PaddleOCR, Apache 2.0). Cloud OCR services (Azure AI Vision Read, Google Cloud Vision document text, AWS Textract) are the fourth kind if the first three fail on handwriting | Server or hosted | Gate: 80 percent of notes correctly read, counted separately from separation. Hosted means the photograph leaves our server, which is the open consent decision |
| Colour and clustering (2, S9 to S10) | NumPy median hue; DBSCAN from scikit-learn, or twenty lines of code | Server | No model |
| Intent and slots, F2.6 (3, S4 to S5) | An LLM with schema-constrained output: Anthropic Messages API tool use or OpenAI structured outputs when hosted; locally Llama 3.x or Qwen2.5 served by vLLM or Ollama with JSON-schema constrained decoding (`outlines`, or llama.cpp grammars). Pydantic holds the schema on the Python side | Server or hosted | The closed enum is the design; any of these can be held to it |
| Retrieval, F2.7 (5, S3) | SQLite FTS5 for keywords, **already the database we run**; `sqlite-vec` (Apache 2.0) for vectors so the index stays in the same file; embeddings from `multilingual-e5-small` or `bge-m3` through `sentence-transformers`, multilingual because the room speaks two languages | Server, local | About fifteen thousand words per meeting; no vector database needed |
| Layout, F3.3 (4, S6) | Deterministic code seeded from item ids; `d3-force` for clusters, ELK (Eclipse Layout Kernel) or `dagre` for flows and hierarchies | Client | A model never emits geometry, pipelines.md rule B |
| Session sync, F4.2 | Bounded polling over HTTP and JSON | Client and server | **Built today**; decision log says why not WebSocket for this |
| Canvas export, F5.1 (7, S4 to S5) | Playwright headless Chromium: the same renderer for PNG at 2x and `page.pdf` for PDF | Server | Playwright is already in the tree for the journey test |
| Board push, F5.3 (7, S7) | Miro REST API v2, `POST /v2/boards/{board_id}/sticky_notes`, with a stored id map. Figma's REST API does not write canvas content, so FigJam would need a FigJam plugin (Plugin API) run from inside the board | Server to hosted | F5.3: one day against the real API before committing. To verify |
| Consent, retention, deletion, F6.1 and F6.6 | The server's own consent gate, session close and `secure_delete` | Server | **Built today** |
| Hardware for the local models | One machine with a GPU of about 8 GB or more for Whisper turbo plus a 7B vision model in 4-bit; CPU-only runs `whisper.cpp` small or medium at lower accuracy | Server | A proposal; nothing has been measured on any hardware but this container |

**2. The stack diagram, on slide 8.** Inline SVG in the deck, drawn with the
same tokens and conventions as the journey diagram on slide 5: solid outline
for built, dashed outline wherever a model runs, the human, model and
guardrail colours, an arrow means "uses" and points from the user to the used.
Bands top to bottom:

1. Browser client (built): capture, hand-drawn boxes, review, canvas, export.
   Beside it, proposed client pieces: `AudioWorklet`, Silero VAD, layout
   engine.
2. Transport: HTTP and JSON with polling (built); WebSocket for audio only
   (proposed).
3. Server (built): standard library HTTP, service and consent gate, SQLite
   with the event log and FTS5, Pillow. Proposed beside it: OpenCV, the
   `websockets` library, `sqlite-vec`.
4. Adapters and models: the `Extractor` protocol (built) with the fixture
   adapter (built) and the reading candidates (proposed, dashed); the audio
   pipeline (proposed, dashed): `faster-whisper`, `pyannote.audio`; the
   segmentation candidates (proposed, dashed); the LLM stages (proposed,
   dashed).
5. Outside our server (proposed, behind the consent gate drawn as a
   guardrail): hosted vision and language APIs; Miro REST API v2.

Every box carries its name and one of the words built or candidate. The
diagram must be legible from the back of a room, so at most about twenty
boxes; group candidates into one box per stage with the names inside.

**3. The document.** `deliverables/documentation/stack.md`, Markdown, no
HTML twin. Title it "The stack: what is built, and the candidates for the
rest". Contents, in this order: the "verify before installing" line; a text
transcription of the stack diagram in the same style flowchart.md uses (boxes
with their kind, then the connections); the candidate table above, expanded
with one line per row on how to try it (the package to install or the API to
call, and the F-number it serves); the gate tests that decide each candidate,
cited to pipelines.md Unknowns; and a closing section listing what is
deliberately not chosen and why. The document is the copy of record; the
slide cites it in small text, and PLAN.md W4 and NOTES.md point at it so the
presenter can answer "which model" with a page reference.

**Extra acceptance checks, Fable verifies each:**

7. Every name on slides 6 to 8 appears in `stack.md`, and every name in
   `stack.md` is in the table above or is a platform API such as
   `getUserMedia`. No name on a slide is missing from the document.
8. The stack diagram renders inside the 1920x1080 stage with nothing
   clipped, and its screenshot has been read back.
9. `stack.md` has no em dash, British spelling, and each row carries its
   reason.

## W4d. The deck as a presentation, not a document. Opus builds. Supersedes the layout of W4, W4b and W4c; keeps their facts.

**Why.** The user reviewed the ten-slide PDF: far too much text, no
hierarchy, nothing legible from the back of a room. They are right, and the
deck breaks the rules the project's own design reference sets
(`decisions/design-reference-rondesignlab.md`, section 7): the number is the
design, one idea per slide, the object gets half the viewport, a saturation
budget, the artefact shown as itself. The facts on the slides are right and
stay. The words move to `NOTES.md`, where the presenter reads them; the
slides carry what the room reads.

**The five rules for every slide.** Measured, not judged:

1. **At most 45 words on the slide**, sources line included. Everything else
   goes to the notes for that slide.
2. **Nothing smaller than 28 px** except the one-line sources footer, which
   may be 24 px. Headline 96 to 128 px in the signal face. Supporting lines
   36 to 44 px in the reading face.
3. **One headline of at most nine words** that is the idea, not a label.
   "Who draws the box? Today, a person." not "How: a wall becomes notes".
4. **One visual, at least 40 percent of the stage area**, on every slide
   except the title and the demo title. A visual is a photograph, a screen
   capture of the real client, the drawn wall, the note component at poster
   scale, a diagram of at most nine boxes, or one number set enormous.
5. **The saturation budget**: at most two coloured surfaces per slide; the
   rest is the stage and ink. Accent only on the thing the eye should land on.

**Composition.** 1920x1080, 120 px margins, the stage tinted with the
existing `--color-surface-sunken` rather than pure white (the design
reference: nothing is pure white), no shadows, no gradients, tokens only,
radius from the scale. Type in the two faces. Dashed outline wherever a model
runs; solid for built; the two must be tellable apart at 640 px wide.

**Slide by slide.** Timings unchanged from W4b.

| # | Headline (at most nine words) | The visual | What else, at most |
|---|---|---|---|
| 1 | Jarvaids | The drawn wall (`demo/wall.png`) or the note component at poster scale | The one sentence, the group line |
| 2 | Three seconds every design meeting loses | The three seconds as three enormous numbered lines, nothing else | Who: design teams, two to eight people, a wall |
| 3 | What Week 3 told us | Four cards, each a two-tone label: a phrase in bold (at most eight words) and its source muted beneath | Nothing else. The reasoning is in the notes |
| 4 | Provisional until a person accepts it | Two notes at poster scale side by side: one dashed (read by a model, not yet accepted), one solid (accepted), drawn exactly as the client draws them | One line: moving is not agreeing |
| 5 | Before, during, after | The journey as three bands with at most three boxes each, the current SVG simplified, band labels at 44 px | The F-numbers move to the notes |
| 6 | Who draws the box? Today, a person. | Three real client captures side by side from `demo/fallback/`: `02-wall-marked.png`, `03-readings-provisional.png`, `04-accepted.png`, each with a three-word caption | One line: proposed, the machine proposes and the hand-drawn box stays as the correction. One line of numbers: ten photographs, 80 percent separated, 80 percent read. Candidate names only in the sources footer, pointing at `stack.md` |
| 7 | Nine stages. Three are models. None has run. | The nine stages as one horizontal rail of nine labelled circles, two words each, three of them dashed | One banner line stating exactly what exists: a server contract, a browser chunker, a synthetic transcriber; the Whisper wrapper written, never run. One number: 2.7 s, labelled a proposed budget |
| 8 | Built, and candidate | The stack as five bands of at most three boxes each, names only, solid or dashed, the consent gate as one bar across | Sources footer pointing at `stack.md`. The "it answers, it does not volunteer" strip moves to slide 4's notes |
| 9 | Live demo | The note component at poster scale, dashed, with "read by fixture, not yet accepted" as its label | The one sentence about what the room will see |
| 10 | Can a real wall be read well enough? | Three numbers enormous: 10, 80%, 80%, each with a three-word label | One line: speech next, gated on consent |

**Facts that must survive from W4b and W4c**, in the notes if not on the
slide: the box question answered; the reading candidates by name; the gate
test; the speech banner as corrected in W4c (plumbing exists, no recognition
has run, Whisper wrapper never run, per-connection attribution not
diarisation); every name on a slide present in `stack.md`; the stand-in
sentence on slides 6 and 9; no accuracy number anywhere.

**Done when, Fable measures each with a script, not by eye:**

1. Word count per slide, counted from the rendered text, at most 45.
2. Smallest rendered font size per slide at least 28 px, footer excepted.
3. On slides 2 to 8 and 10, one element or group covers at least 40 percent
   of the stage area.
4. All ten slides screenshotted at 1920 wide and again downscaled to 640
   wide, and the 640 versions read back: every headline and every number
   legible, dashed and solid tellable apart.
5. Ten sections, zero console errors, PDF of ten pages, `audit.sh` clean on
   `slides/`, no em dash, NOTES.md targets summing to 7:00 or under and
   carrying every fact removed from a slide.

## W7. Two documents of record: the proposal by function, and how we work. Opus builds. Independent of W4d.

**Why.** The user wants every function from the initial brief documented with
who it is for and where each one stands, and a plain account of how the
repository is set up: GitHub, automation, checks, the design system, the
agent workflow and the logs. Both exist in pieces across the tree; neither
exists as one page a reader can start from. Two documents, each binding to
its sources rather than copying them, because two copies drift.

### W7a. `deliverables/documentation/proposal.md`

Title: "Jarvaids: what it is, who it is for, and where every function stands".

1. **What it is**, in the concept's own words: one paragraph from
   `ideation/concepts/001-jarvaids-meeting-assistant.md`, cited.
2. **Who it is for, and when.** Design teams in a working session, two to
   eight people, a wall, one to two hours; the facilitator and the
   participants as the two roles (F4.3); the three seconds the concept aims
   at, quoted. What the Week 3 material adds: `annotations/INDEX.md` closing
   section, cited by item number.
3. **The rule everything follows from**, one paragraph, citing
   `flowchart.md` and forbidden.md rules 16 to 18.
4. **Every function, with its status.** One table, thirty-seven rows, one per
   F-number in `flowchart.md` (F1.1 to F6.6), columns: F-number, function (the
   flowchart's short name only, not its description, so the table binds to
   the flowchart rather than copying it), who it serves (facilitator,
   participant, the room, the record), AI or not (from the flowchart),
   status today, and the evidence for that status (a file, a test name, a
   BUILD-STATUS section or a decision-log row). Status is one of exactly
   four words: **built** (runs in the repository and is tested), **plumbing**
   (the contract and tests exist, the model or the device path does not),
   **proposed** (designed in `pipelines.md`, nothing runs), **open** (a
   decision the team has not made). Establish each status from the code and
   the documents, never from memory: `app/server/README.md`, `API.md`,
   `BUILD-STATUS.md`, `app/client/README.md`, `decisions/gaps.md`,
   `decisions/decision-log.md`, `stack.md`. No handwriting recognition and
   no speech recognition has run; nothing that depends on either is built.
5. **Counts** at the end of the table: how many of each status, and the
   sentence that the counts are read from the table, not the other way
   round.
6. **What is deliberately not chosen**, pointing at `stack.md` section 4
   rather than repeating it.

A check script next to it, `check_proposal.py` in the same folder, that
fails if any F-number in `flowchart.md` is missing from the table, if any
F-number in the table is not in `flowchart.md`, or if a status is not one of
the four words. Run it and include its output in the report. Add the one
line to `AGENTS.md`'s "Before you finish" block so it runs with the rest.

### W7b. `deliverables/documentation/how-we-work.md`

Title: "How this repository works: setup, automation, checks, design system,
agents and logs". Written from the files, each section naming the file it
describes so a reader can open it. Sections:

1. **The shape of the repository.** The top-level folders and what each is
   for, from `AGENTS.md` "Where things are". Prefer `.md` twins over `.html`.
2. **Branches and pull requests.** `main` protected as described in
   `.github/BRANCH-PROTECTION.md` (say plainly that the protection itself
   needs an administrator to switch on and whether it is on, which you can
   check with the GitHub tools if available, otherwise say it is unverified);
   feature branches per agent or person; pull requests as the only route in;
   the branch naming seen in `git branch -r`.
3. **What runs on every push and pull request.** `.github/workflows/verify.yml`
   job by job: design-system (the 13-check audit, the contrast check over
   every pair in every scheme, the generated contrast table), house-style
   (no em dashes in what the branch changed), backend (Python 3.11 to 3.13,
   the suite, five mutation harnesses, "nothing was left mutated"),
   sync-budget, schema (one meaning per schema version), client (Node 24,
   contract and lifecycle tests, named guard mutations, real HTTP
   journeys), browser (the client journey in a real Chromium). For each: what
   it catches and the accident that caused it where `AGENTS.md` records one.
4. **Before the push.** `.githooks/pre-push` and how it is enabled; the
   "Before you finish" command block in `AGENTS.md`.
5. **The mutation discipline.** `tests/mutation_runner.py`: every guard names
   the test that kills it, an error is not a kill, the counts (read them from
   `AGENTS.md`, do not restate from memory).
6. **The design system.** `app/design-system/`: tokens, the two faces, the
   spec files by name with one line each, `forbidden.md` as the list of
   thirty rules with their reasons, the exemplars, `audit.sh` and
   `contrast-check.py`, the `CLAUDE-fragment.md` that any agent generating UI
   reads first, and the pending revision (`decisions/design-reference-rondesignlab.md`
   section 7) as the direction of travel, not as done.
7. **How agents work here.** `AGENTS.md` as the single brief and why there
   is no second copy; briefs and plans under `deliverables/week4-midpoint/`;
   the coordinator-and-builder split; the rule that a builder's report is
   verified by the coordinator before anything is committed; worktree
   isolation and its trap (branches from `main`).
8. **The logs.** `decisions/ai-use-log.md` (one row per work package, honest
   about what review happened), `decisions/decision-log.md` (every closed
   option with its reason), `decisions/gaps.md`, `decisions/backend-chunks.md`.
9. **Privacy and secrets.** `.env`, `evidence/raw/` and the recorded
   exception in `AGENTS.md`.
10. **Numbers**, one small table, each read from a file named in the row:
    tests, guards, audit checks, contrast pairs, schema versions, F-numbers,
    commits on the branch.

Both documents: British spelling, no em dashes, every rule with its reason,
nothing stated that a named file does not support. Report the files
written, the check script's output, the status counts, anything you could
not verify (say so in the document too), and the numbers table.

## W4e. Three more slides, and thirteen in seven minutes. Amends W4d.

**Why.** The user would rather have more clear slides than fewer cramped
ones, and wants the deck to cover who it is for, what it does (the whole
function list), and how the repository is run. Same five rules as W4d,
measured the same way.

**The order becomes thirteen slides.** Timings sum to 7:00.

| # | Headline (at most nine words) | The visual | Target |
|---|---|---|---|
| 1 | Jarvaids | as W4d | 0:15 |
| 2 | Three seconds every design meeting loses | as W4d | 0:30 |
| 3 | Two to eight people, one wall, one facilitator | Who it is for: a row of figures at a wall drawn from the design system's diagram tokens, or the drawn wall with the two roles labelled | 0:25 |
| 4 | Thirty-seven functions in six groups | Six tiles (F1 Capture, F2 Understanding, F3 Visualisation, F4 Session, F5 Output, F6 Trust) each with its count and a small status strip of dots: solid for built, half for plumbing, dashed for proposed, empty for open, read from `proposal.md`'s table when it exists, otherwise from the same sources it uses | 0:40 |
| 5 | What Week 3 told us | as W4d slide 3 | 0:30 |
| 6 | Provisional until a person accepts it | as W4d slide 4 | 0:35 |
| 7 | Before, during, after | as W4d slide 5 | 0:20 |
| 8 | Who draws the box? Today, a person. | as W4d slide 6 | 0:45 |
| 9 | Nine stages. Three are models. None has run. | as W4d slide 7 | 0:30 |
| 10 | Built, and candidate | as W4d slide 8 | 0:30 |
| 11 | Every push runs 7 jobs before it lands | How we work: a horizontal rail, push, hook, seven CI jobs as seven labelled circles, main; beneath it four enormous numbers read from `AGENTS.md`: tests, guards, audit checks, contrast pairs | 0:35 |
| 12 | Live demo | as W4d slide 9 | 1:15 |
| 13 | Can a real wall be read well enough? | as W4d slide 10 | 0:30 |

Slide 4's status dots and slide 11's numbers must be read from
`proposal.md` and `AGENTS.md` when those exist, and the sources footer says
so. If `proposal.md` is not yet written when you reach slide 4, build the
tiles from `flowchart.md`'s six tables and `BUILD-STATUS.md`, and say in the
report which source you used. `NOTES.md` and the `PLAN.md` W4 table follow
the thirteen rows. All W4d acceptance checks apply to thirteen slides.

## W4f. Register. Amends W4d and W4e. Applied by the coordinator.

The user reviewed the thirteen-slide deck: the layout was right and the
writing was not. Headlines were slogans, footers were asides, the notes were
stage directions, and numbers were used as headings. Two documents from
another course were given as the register to match: chapter labels, plain
section headings ("Project Background, Client and Scope", "Central Design
Question"), and body text in declarative sentences that explain.

Rules, replacing W4d rule 3 and the W4e headlines:

1. A heading names the subject of the slide. "Users and context", "Speech
   pipeline", "Design question". No claim, no question, no number as a
   headline, no wordplay.
2. A chapter label above the heading (Introduction, Research, Problem
   framing, Design principle, Design, Implementation, Demonstration, Next
   steps) and a footer with the source and the page number.
3. Body text, where there is any, is one short paragraph of plain declarative
   sentences, at most 75 words, saying what the slide shows. No exhortation,
   no evaluation of the group's own work, no "honest moment".
4. Speaker notes are the explanation in the same register: what to say,
   in sentences, without "open" and "close" lines or instructions on tone.
5. The two flowcharts from `documentation/flowchart.html` are slides, with
   the middle band of the journey enlarged on its own slide, because the
   room found them the clearest thing in the earlier deck.

W4d rules 2, 4 and 5 stand: nothing under 28 px except the footer, one
visual per slide where there is one, at most two coloured surfaces.
