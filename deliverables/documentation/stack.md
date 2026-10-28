# The stack: what is built, and the candidates for the rest

**Verify the version and the licence before installing anything named here.** A
name on a slide is not a dependency pin. Versions and licences below are as the
coordinator recalled them in September 2026, they were not read off a package
index by a machine, and a licence can change between releases. Check each one
against its own repository before it enters `requirements.txt` or a lock file.

**What this is:** the copy of record behind slides 6, 7 and 8 of the week 4
midpoint deck. Slide 8 draws this as one picture and cites this file in small
text; this file carries the names, the reasons, the gate tests and the things
deliberately not chosen. It is a companion to
`deliverables/documentation/pipelines.md`, which holds the stages, and to
`deliverables/documentation/flowchart.md`, which defines the F-numbers.

**Status:** the F1.1 to F1.3 audio slice landed on 22 September 2026, and it is
plumbing with a synthetic transcriber, not transcription: a server contract, a
browser chunker and a fixture adapter, with the Whisper wrapper written and
never run. Everything else below is a proposal, apart from the rows marked
built today. Nothing in the candidate column has been run in this project. No accuracy, latency or cost
figure here was measured; every number is cited to the section of
`pipelines.md` that proposes it.

---

## 1 The stack diagram, transcribed

This is the drawing on slide 8 of the deck, written out. Kind tags are given in
brackets. A box drawn with a **solid** outline is built today. A box drawn with
a **dashed** outline is a candidate nobody here has run, which includes every
box where a model would run. An arrow means **uses**, and it points from the
user to the thing used.

**Band 1, browser client.** Five boxes in a row.

1. **Client: plain ES modules, no build step** (Client). Built. Served by
   `app/client/serve.py`.
2. **Hand-drawn note boxes, review, accept** (Human). Built. A person drags a
   box around each note, corrects a reading in place, accepts or rejects.
3. **getUserMedia and an AudioWorklet** (Client). Built, in
   `capture-audio.mjs`, and never exercised in a browser: only the DOM-free
   `Chunker` class has been unit tested.
4. **Voice activity: energy threshold in the browser** (Client). Built. Silero
   VAD through `onnxruntime-web` is the candidate that would replace it.
5. **Layout: d3-force, ELK or dagre** (Client). Candidate.

Two solid arrows run down into band 2, one from box 1 and one from box 4.

**Band 2, transport.** Two boxes.

1. **HTTP and JSON: board polling and audio chunks** (Server). Built. An audio
   chunk travels as a `source.audio` command with base64 PCM16, over the same
   HTTP path as everything else, not over a socket.
2. **WebSocket for audio only, the websockets library** (Server). Candidate.

Two arrows run down into band 3, one solid and one dashed.

**Band 3, our server.** Five boxes in a row.

1. **Python 3.11, standard library HTTP server** (Server). Built.
2. **Consent gate, retention, secure_delete** (Guardrail). Built.
3. **SQLite: the event log and FTS5** (State). Built.
4. **Pillow: decode, strip, re-encode** (Server). Built.
5. **OpenCV, and sqlite-vec** (Server). Candidate.

An arrow runs down from box 1 into band 4 box 1. A dashed arrow runs down from
box 5 into band 4 box 5.

**Band 4, adapters and models.** Five boxes in a row.

1. **Extractor protocol, FixtureExtractor** (Server). Built. Provider
   `fixture`, model `synthetic-v1`, `synthetic: true`.
2. **FixtureTranscriber: synthetic text, tested** (Server). Built. Provider
   `fixture`, model `synthetic-v1`, `synthetic: true`, and it is the default
   adapter, so the demo produces synthetic text unless something else is
   configured.
3. **LocalWhisperTranscriber wraps faster-whisper** (Model). Written, never
   run: never constructed, never called, no weights and no `faster-whisper`
   install in the environment it was written in.
4. **Image models: SAM 2, Florence-2, Qwen2.5-VL 7B, TrOCR, PaddleOCR**
   (Model). Candidate, for segmentation and reading.
5. **Intent: Llama 3.x, Qwen2.5, vLLM** (Model). Candidate.

Two dashed arrows run down from boxes 4 and 5 into the gate below. Nothing
runs from boxes 2 or 3 into it, because F6.2 keeps the audio on our server by
design.

**The gate**, one box spanning the full width. **Consent gate: may a
photograph, or a transcript, leave our server at all?** (Guardrail). An open
decision, and not a technical one. Two dashed arrows run down from it into
band 5.

**Band 5, outside our server.** Two boxes.

1. **Hosted vision and language: Claude through the Anthropic Messages API,
   GPT-4o, Gemini** (Model). Candidate. A model runs, and the photograph
   leaves.
2. **Miro REST API v2, sticky notes with an id map** (Server to hosted).
   Candidate. F5.3 asks for one day against the real API first.

Nothing in band 5 is reachable until the gate above it is answered, which is
the reason the gate is drawn as a band of its own rather than as a note.

---

## 2 The candidates, and how to try each one

One row per stage. **Why this one** is the reason it is first choice, because a
row without a reason gets swapped out by the next person who has an opinion.
**How to try it** is the smallest real step: the package to install, or the
call to make.

| Stage, F-number, pipelines.md section | Candidate | Runs | Why this one, and what decides it | How to try it |
|---|---|---|---|---|
| Audio capture, F1.1, section 1 S1 to S2 | Browser `getUserMedia` plus an `AudioWorklet`. **Built** in `app/server/capture-audio.mjs`, and never exercised in a browser | Client | No dependency at all, it is the platform, so there is nothing to license or ship | It is written: `startCapture` in `capture-audio.mjs`. Serve `demo-audio.html` over HTTP on your own machine and allow the microphone. It will not run in a headless session, which is why it is untested |
| Voice activity, F1.1, section 1 S3 | **Built today: an energy threshold**, per frame, in `capture-audio.mjs`. The candidate that would replace it is Silero VAD, ONNX weights, in the browser through `onnxruntime-web`, which the `@ricky0123/vad-web` package wraps | Client | The energy gate is the documented cheap fallback and it is named as one, so nobody mistakes it for a model. Silero is small enough to run per frame in WASM, MIT licence, and it would stop us transcribing a noisy empty room | `npm i @ricky0123/vad-web`, or load the ONNX file with `onnxruntime-web` and feed it the same frames the energy gate reads. Tune it against a real room recording, which is the step that has not happened |
| Audio transport, section 1 S5 | **Built today over HTTP**: one endpointed chunk goes up as a `source.audio` command with base64 PCM16, capacity capped, and comes back as one `transcript_segment` record. The candidate is a WebSocket, with the `websockets` library on the Python side since the standard library has none | Server | HTTP was enough for one chunk every few seconds and it reuses the consent gate, the capacity cap and the provenance the other source types already have. A socket becomes worth its own code path only when the two-lane caption strip needs one | `pip install websockets`, one endpoint that accepts binary frames, bounded queue, backpressure to the client. Measure the HTTP path first: it may already be fast enough for a single lane |
| Speech to text, F1.2 and F6.2, section 1 S6 | **Built today: `FixtureTranscriber`**, the default adapter, deterministic, offline and visibly synthetic, which proves the plumbing and no transcription at all. **Written and never run: `LocalWhisperTranscriber`**, which wraps `faster-whisper`. Behind it: Whisper large-v3-turbo weights (MIT) run with `faster-whisper` (CTranslate2) on one GPU, `whisper.cpp` for a CPU or Apple silicon fallback at lower accuracy, and streaming through `whisper_streaming` or WhisperLive | Server, local | Whisper is the multilingual option, which matters because this room mixes Dutch and English inside one sentence. NVIDIA Parakeet and Canary are faster and English-centred, so they lose the case we actually have | `pip install faster-whisper`, load `large-v3-turbo`, feed it an 8 second chunk, ask for word timings; word timings are what citations in F6.3 need |
| Speaker separation, F1.3, section 1 S7 | **Built today: per-connection attribution.** The speaker is whoever's credential sent the chunk, recorded as `attribution: per_connection`, and it is not diarisation. The candidate is `pyannote.audio` 3.x, MIT code with gated weights on Hugging Face whose terms must be accepted, and `diart` for the online, streaming variant | Server, local | Per-connection is free and honest about being crude, and it is right whenever one person has one device. It fails the moment two people share a laptop, which is most of a workshop. `pyannote.audio` is the only open option with a credible overlap story, and overlap is what a design meeting is made of | `pip install pyannote.audio`, accept the model terms on Hugging Face, run the diarisation pipeline over the same chunk and align the labels to the word timings |
| Wake phrase, F2.5, section 3 S1 | openWakeWord (Apache 2.0). Picovoice Porcupine as the commercial alternative | Client | Only worth having if the observation test says push-to-talk is not enough, and a false accept costs more than a missed wake | `pip install openwakeword` for a first bench, then port to the browser. Do the observation test first, it is cheaper than either |
| Photograph preparation, F1.4, section 2 S2 | Browser Canvas API for orientation and downscale. `exifr` if EXIF orientation must be read by hand | Client | No server dependency, and the GPS is stripped before the bytes leave the phone rather than after they arrive | Draw the image to a canvas at a long edge of 2048, export at quality 0.8, upload. `npm i exifr` only if the orientation tag misbehaves |
| Image sanitising, section 2 S3 | Pillow | Server | **Built today.** It decodes, orients and re-encodes to clean PNG pixels, which drops metadata as a side effect of re-encoding rather than as a promise | Already in `app/server`. See `BUILD-STATUS.md` for the tested version |
| Quality gate and rectification, section 2 S4 to S5 | OpenCV: variance of the Laplacian for blur, contour detection plus `findHomography` and `warpPerspective` for the wall plane | Server | Classical, no model, fast, and the homography is what maps a note back onto the original photograph, which is what makes a correction checkable against the picture | `pip install opencv-python-headless`, threshold the Laplacian variance for blur, find the dominant quad, warp it flat |
| Note segmentation, F1.5, section 2 S6 | First OpenCV HSV thresholding for saturated rectangles. Then Segment Anything 2 (SAM 2, Apache 2.0, Meta) for masks from box or point prompts, or Florence-2 (MIT, Microsoft) asked for "sticky note" as open-vocabulary detection. An Ultralytics YOLO fine-tune is the last resort, because it needs a labelled set and its licence is AGPL | Server, local | HSV is free and works on a clean wall, so it is what to try first. Today a person draws the boxes, **built**, and that stays as the correction path whatever wins | Threshold in HSV, take contours above a minimum area, compare the count against a hand count on ten photographs. Only reach for SAM 2 or Florence-2 if that count is wrong |
| Handwriting reading, F1.6, section 2 S8 | Three kinds, to compare in the gate test: a hosted vision-language model (Claude through the Anthropic Messages API, GPT-4o, or Gemini), a local open-weights one (Qwen2.5-VL 7B, Apache 2.0), and a classic OCR baseline (TrOCR handwritten, MIT; PaddleOCR, Apache 2.0). Cloud OCR services (Azure AI Vision Read, Google Cloud Vision document text, AWS Textract) are the fourth kind if the first three fail on handwriting | Server or hosted | Nobody knows which reads a marker pen on yellow paper best, so the gate test decides rather than an opinion. Hosted means the photograph leaves our server, which is the open consent decision above | Crop thirty notes once, then send the same thirty crops to each candidate and score them by hand. One afternoon, and it settles the argument |
| Colour and clustering, section 2 S9 to S10 | NumPy median hue. DBSCAN from scikit-learn, or twenty lines of code | Server | No model, and a guess presented as a guess: proximity clustering is cheap to redo when the team regroups by hand | Median the interior hue ignoring the outer fifteen percent, then cluster centroids with a radius set as a multiple of the median note width |
| Intent and slots, F2.6, section 3 S4 to S5 | An LLM with schema-constrained output: Anthropic Messages API tool use or OpenAI structured outputs when hosted. Locally Llama 3.x or Qwen2.5 served by vLLM or Ollama with JSON-schema constrained decoding, through `outlines` or llama.cpp grammars. Pydantic holds the schema on the Python side | Server or hosted | The closed enum is the design, not the model, so any of these can be held to it and the one that wins is the cheapest that holds | Define the operation enum as a Pydantic model, ask for structured output, and reject anything outside the enum in code rather than in the prompt |
| Retrieval, F2.7, section 5 S3 | SQLite FTS5 for keywords, **already the database we run**. `sqlite-vec` (Apache 2.0) for vectors so the index stays inside the same file. Embeddings from `multilingual-e5-small` or `bge-m3` through `sentence-transformers`, multilingual because the room speaks two languages | Server, local | About fifteen thousand words per meeting, so there is no infrastructure problem and no vector database to run or back up | Turn on FTS5 over the transcript table first and see how far keywords alone get. Add `sqlite-vec` and embeddings only if that falls short |
| Layout, F3.3, section 4 S6 | Deterministic code seeded from item ids. `d3-force` for clusters, ELK (Eclipse Layout Kernel) or `dagre` for flows and hierarchies | Client | A model never emits geometry, which is rule B in `pipelines.md`, and a seeded layout is reproducible, so the same board lays out the same way twice | `npm i d3-force`, seed positions from a hash of the item id so the result is stable, then run the simulation to rest |
| Session sync, F4.2 | Bounded polling over HTTP and JSON | Client and server | **Built today.** The decision log says why not WebSocket for this: a board change is an event, not a stream, and polling degrades gracefully on venue wifi | Already in `app/server` and `app/client`. `tests/measure_sync.py` holds it under 5 KB a client |
| Canvas export, F5.1, section 7 S4 to S5 | Playwright headless Chromium: the same renderer for PNG at 2x, and `page.pdf` for the PDF | Server | Playwright is already in the tree for the journey test, so the export adds no new dependency, only a second render path to keep in step | Point Playwright at the canvas route, screenshot at `deviceScaleFactor: 2`, then `page.pdf` for the document. Pin the fonts into the render environment |
| Board push, F5.3, section 7 S7 | Miro REST API v2, `POST /v2/boards/{board_id}/sticky_notes`, with a stored id map. Figma's REST API does not write canvas content, so FigJam would need a FigJam plugin, run from inside the board | Server to hosted | Miro is the only one of the two that can be written from a server at all, which decides it before any preference does. F5.3 already says to spend one day against the real API before committing | Create a board by hand, push ten notes, then push the same ten again and check the id map updates rather than duplicating. To verify |
| Consent, retention, deletion, F6.1 and F6.6 | The server's own consent gate, session close and `secure_delete` | Server | **Built today.** It cannot be a library, because the rule it enforces is specific to this product: until the flag is set the bus accepts no capture event at all | Already in `app/server`. See `API.md` and the deletion receipt tests |
| Hardware for the local models | One machine with a GPU of about 8 GB or more, for Whisper turbo plus a 7B vision model in 4-bit. CPU-only runs `whisper.cpp` small or medium at lower accuracy | Server | A proposal, and the one nobody has tested: nothing here has been measured on any hardware but this container | Borrow a machine for an afternoon, run the speech gate test and the reading gate test on it, and write down what it actually did |

---

## 3 The gate tests that decide the candidates

Each of these is a threshold agreed **before** the test, which is the point of
writing them down: a number agreed afterwards is a number interpreted into a
success. All five are from the unknowns table at the end of `pipelines.md`.

| What it decides | The test | The threshold, agreed in advance |
|---|---|---|
| Speech to text, and with it everything downstream of it | Record ten minutes of a real session, hand-correct three two-minute samples, count word error rate. Half a day | Under 15 percent overall and under 10 percent on names, decisions and jargon. Over 25 percent and the concept changes shape |
| Handwriting reading, and note segmentation, counted separately | Photograph a real wall ten times at real angles and lighting, run it through two or three vision models | 80 percent on both, counted separately. Separation below 80 is fatal, reading below 80 is survivable because the crop is still there |
| Speaker separation, and whether the tool may ever say a name | Hand-label ten minutes of a real recording and compare | Diarisation error rate under 20 percent with overlap included. Above that, the tool stops using names and says "someone" |
| Whether the command pipeline is the core at all | Sit in on two real sessions with a wizard-of-oz button and count how often someone would have pressed it. No code | Fewer than three in an hour means the command pipeline is not the core, whatever the demo looks like |
| Referent resolution, the hardest unsolved piece | Build 30 referent cases by hand from one real transcript and canvas state, score by hand. An afternoon | 80 percent. Below that, confirm-always is the only safe mode and the interaction is redesigned around selection |

The break-even that sits under the reading gate is worth stating on its own,
because it is what makes 80 percent a sensible bar rather than an arbitrary
one: retyping a note from a legible crop takes about four seconds, correcting a
wrong reading takes about the same plus the time to notice it is wrong, so the
feature wins if fewer than roughly 30 percent of notes need correction and the
wrong ones are obvious at a glance. That reasoning is in `pipelines.md`
section 2.

---

## 4 What is deliberately not chosen, and why

- **No paid provider, and no price.** `API.md` requires deadlines, idempotency
  keys, hard cost limits and remote cancellation before any paid adapter is
  added, and none of that is built. Choosing a provider now would be choosing
  before the guard that makes the choice safe exists.
- **No framework, on either side.** The server is the Python standard library
  and SQLite, the client is plain ES modules with no build step. The reason is
  that every dependency has to open offline and survive a marker being handed
  to the next team, and a build step is a thing that breaks on somebody else's
  machine six months from now.
- **No WebSocket, for the board or for audio.** The decision log holds the
  board half: a board change is an event and polling degrades gracefully on
  venue wifi. Audio now rides the same HTTP path, one endpointed chunk per
  request, because that reused the consent gate and the provenance record
  instead of building a second way in. The WebSocket in the diagram stays a
  candidate, and it earns its place when the two-lane caption strip needs it.
- **No vector database.** Fifteen thousand words per meeting fits in memory and
  fits in the SQLite file we already write. A separate index is a second thing
  to keep fresh, back up and delete on request, for no measured gain.
- **No Ultralytics YOLO fine-tune, unless the others fail.** It needs a
  labelled set we do not have, and its licence is AGPL, which is a decision
  about the whole project rather than about one stage.
- **No FigJam push in the first version.** Figma's REST API does not write
  canvas content, so it would mean a plugin running inside the board, which is
  a second delivery mechanism for one destination. Miro first, and only after
  the day of real API work F5.3 asks for.
- **No proactive suggestion.** F2.8 and F4.4 are left open on purpose. The
  anchoring risk named in concept 001 has not been tested, and adding
  suggestion later means one new trigger into the visualisation pipeline and
  nothing else, so leaving it out is cheap and reversible.
- **No handwriting recognition, and no speech recognition.** The only
  `Extractor` implementation is `FixtureExtractor` and the default
  `Transcriber` is `FixtureTranscriber`. Both return visibly synthetic text,
  and `/health` reports `live_ocr: false`. What the audio slice added is
  plumbing that can be trusted to carry a real transcriber later: a consent
  gate, a capacity cap, provenance on every segment and a marked gap when a
  stage fails. It is not transcription, and `LocalWhisperTranscriber` has never
  been constructed. Nothing in this document should be read as a result. Where
  a number appears, it is a proposal from `pipelines.md`, and the section it
  came from is named beside it.
