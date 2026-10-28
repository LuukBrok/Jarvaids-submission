# Data pipelines: every stage, its model, its latency and its failure

**What this is:** how each piece of Jarvaids would actually run: eight pipelines, stage by stage, with the data shape moving between stages, where a model sits and where none is needed, a latency budget for a live meeting, what breaks and what happens then, what it costs, and what gets cut first.
**Generated from:** `deliverables/documentation/pipelines.html`, which is the rendered version of this same content.
**Diagrams:** the fourteen diagrams in the HTML are inline SVG. They are transcribed here as text. Open the HTML if you want to see them drawn.

GenAI course · ideation 001 · Jarvaids · companion to the flowchart

The flowchart says what Jarvaids does. This says how each piece runs: stage by stage, with the data shape moving between stages, where a model sits and where none is needed, a latency budget for a live meeting, what breaks and what happens then, what it costs, and what gets cut first. Written for whoever picks up a pipeline and has to build it.

- **Companion to:** deliverables/documentation/flowchart.html
- **Cross-referenced by:** the F-numbers from that file
- **Status:** draft for team review, every number in it is a proposal
- **Offline:** single file, no internet needed

**Companion file:** this document implements the F-numbers defined in `deliverables/documentation/flowchart.md` (F1.1 to F6.6). Every pipeline section lists the F-numbers it covers, and the flowchart is where those numbers are defined, along with the user journey and the system architecture they sit in.

## How to read the diagrams

Every box is white, with what kind of thing it is written on its top edge as a tag. Three of those kinds also carry a colour: a person acting, a model running, and a hard limit nothing may cross. The colour is only there to let you find them across the whole drawing; the tag says the same thing in words, so nothing is lost without it. The dashed edge is unchanged and still means a model runs here, so what comes out of it is provisional until a person accepts it.

The diagrams in this file have been transcribed to text. Each one is given as a list of boxes with their kind tag, their description, and, where the source shows them, the model tag and the latency figure, followed by the connections between the boxes with their direction and any label on the connector. Purely visual scaffolding (band rectangles, wrap-around rails, arrow geometry) is described only where it carries meaning.

Two encodings from the drawing are worth stating here, because they are the ones that carry meaning rather than decoration. **A dashed outline on a box means a model runs at that stage, so its output is provisional until a person accepts it.** That is the central rule of the product and it is repeated in the text of every diagram below. The colour carried by the Human, Model and Guardrail boxes is not reproduced, because the source says the tag on the box says the same thing in words, so nothing is lost without it.

## 0 · Read me

**How to read this, and what it is for**

The flowchart says what Jarvaids does. This file says how each piece of it would actually run: the stages, the data shape moving between them, where a model sits, what it costs, how long it takes, and what happens when it breaks. It is written for the person who has just picked up one of these pipelines and has to build it on Monday.

### A The eight pipelines, and how they connect

Two pipelines are **continuous**: they run from the moment consent is logged until the session ends, whether or not anyone interacts with the tool. Four are **event driven**: they only fire when something happens. Two are **terminal**: they run once, at the end. That difference is the single biggest driver of cost, because a continuous pipeline is billed by the meeting-minute and an event-driven one is billed by the event.

**Diagram: map of the eight pipelines, grouped by continuous, event driven and terminal.** Three groups side by side, with the event bus underneath all of them and the consent gate underneath that. A box drawn with a dashed outline is a Model box: a model runs there, so what leaves it is provisional until a person accepts it.

**Group 1, continuous:** runs all meeting, cost scales with minutes.

1. **1 · Audio** (Pipeline). Room sound to speaker-tagged transcript segments on the bus.
2. **6 · Notulation** (Pipeline). Rolling minutes, decisions, actions, open questions.

An arrow runs from Audio down into Notulation. A note under the group reads: "Between them these two are roughly 80% of the running cost of a session. Everything else is rounding error by comparison."

**Group 2, event driven:** fires on an upload, a command or a question.

1. **2 · Image** (Pipeline). A photograph of a wall to separate, placed notes.
2. **3 · Command** (Pipeline). An utterance to one validated canvas operation.
3. **4 · Visualisation** (Pipeline). A set of items to a chosen form, laid out.
4. **5 · Question answering** (Pipeline).

Two dashed arrows run from the Audio box across into this group, one into Command and one into Question answering, labelled: "the transcript feeds the notulator, the command interpreter and the answerer".

**Group 3, terminal:** runs once, after the room has stopped talking.

1. **7 · Export** (Pipeline). Canvas to PNG and PDF, minutes to text, optional board push.
2. **8 · Retention and deletion** (Guardrail). Audio gone, transcript anonymised, on a timer.

A note under the group reads: "Pipeline 8 is the only one that cannot be cut. Without it there is no permission to record anyone."

**Underneath all three groups: the event bus** (State). "The event bus sits under all eight. One ordered, replayable log per session. Every pipeline reads from it and writes back to it. Nothing calls anything else directly." Arrows run down into it from the continuous group and from the terminal group.

**Underneath the bus: the consent gate** (Guardrail), fed by an arrow from the bus. "Consent gate: until the flag is set, the bus accepts no capture event at all, from any pipeline."

| Pipeline | Trigger | Model cost shape | Blocking? | F-numbers |
|---|---|---|---|---|
| 1 Audio | Continuous while consent holds | Per audio minute, the dominant cost | Yes, everything downstream waits on it | F1.1, F1.2, F1.3, F6.2 |
| 2 Image | A photograph is uploaded | Per image, then per note crop | No, but the uploader is standing there watching | F1.4, F1.5, F1.6 |
| 3 Command | Wake phrase, push-to-talk or typed | Per command, or per segment if always listening | Yes, the room is waiting | F2.5, F2.6, F4.3 |
| 4 Visualisation | An accepted command, or an idle nudge | Per invocation, scales with item count | Yes, and visibly | F3.2, F3.3, F3.4 |
| 5 Question answering | Someone asks | Per question, plus a cheap continuous index | Yes, someone is waiting to read it out | F2.7, F6.3 |
| 6 Notulation | A timer and a topic boundary | Per tick, for the whole meeting | No | F2.1, F2.2, F2.3, F2.4 |
| 7 Export | Someone presses export | None, or one summarising call | No, the meeting is over | F5.1, F5.2, F5.3 |
| 8 Retention | Session close, and a sweep | None | No | F6.1, F6.6 |

### B The rules every pipeline obeys

- **Nothing runs before the consent flag is set.** Not the microphone, not a model call, not a photograph upload. The consent gate is a precondition on the bus, not a screen people click past. F6.1.
- **A model never emits geometry, and never emits an action.** Models emit structured proposals. Deterministic code turns a proposal into pixels or into a canvas mutation. This is what keeps the failure surface finite and testable.
- **Everything carries provenance.** Producer, model version, source span, timestamp, confidence. If a stage cannot say where its output came from, the output does not get written. F6.3.
- **Every stage has a defined behaviour when the stage below it is slow or absent.** Not a try or catch that logs and moves on: a named fallback that the room can see. F6.4.
- **Degrade loudly.** A visible queue badge, a visible gap marker in the transcript, a visible "running on the small model" label. The worst failure in a live meeting is a silent one, because people keep trusting the output.

### C Where the honest doubt sits

Three of these eight are ordinary engineering: export, retention, and most of the event bus. Three are hard but known: audio, notulation, question answering. Two contain a genuinely unsolved problem each, and those two are where the project will either be interesting or fall over:

- **Referent resolution in the command pipeline.** Working out that "those three" means note 14, note 19 and note 22 requires the canvas, the last minute of speech and the shared screen's selection state at once, and there is no clean fallback other than asking the room. See pipeline 3.
- **Form selection in the visualisation pipeline.** Choosing a timeline over a cluster is the whole claim of the tool. If it defaults to clustering, Jarvaids is a notes app with a nicer background. See pipeline 4.

> **The scope problem, restated in pipeline terms** (flagged as a warning in the source)
>
> Concept 001 already says this is three products. Mapping the pipelines makes it concrete: pipeline 1 alone is a speech product, pipeline 2 alone is a document-capture product, and pipelines 3 and 4 together are a diagramming product. Each has a different riskiest assumption and a different test.
>
> Nothing in this document argues for building all eight. It argues for knowing what each would cost before choosing. The **what could be cut** box at the end of every section is the real deliverable here: it is a pre-agreed retreat path, written down while nobody is under deadline pressure and therefore still honest.
>

## 1 · Audio

**1 · Audio: room sound to transcript segments**

The continuous one. It starts when consent is logged and does not stop. Every other pipeline except the image one is downstream of this, so its latency is everyone's latency and its errors are everyone's errors. Concept 001 calls transcription plumbing rather than a feature, which is right about its value and wrong about its risk: it is the plumbing that the whole building sits on.

**Functionalities covered (from the flowchart):** F1.1 Live audio capture, F1.2 Speech to text, F1.3 Speaker separation, F6.2 Local processing, F6.4 Degradation behaviour.

Kind tags used in this diagram: **Client** = Client, in the browser; **Server** = Server code, no model; **Model** = A model runs here; **State** = Writes to shared state; **Guardrail** = Guardrail, can stop the pipeline; **Human** = A human decides.

**Diagram: audio pipeline stage rail.** Nine stages in one chain, S1 to S9, each feeding the next. The rail wraps onto a second row after S5, marked "continues", which is layout only and not a branch. Each stage carries a kind tag, a description, a model tag and a latency figure. A stage tagged Model is drawn with a dashed outline: a model runs there, so its output is provisional until a person accepts it.

1. **S1 Capture** (Client). getUserMedia, 16 kHz mono, 20 ms frames. No model. 20 ms.
2. **S2 Condition** (Client). High-pass, level meter, clipping and floor check. No model. 5 ms.
3. **S3 Voice activity** (Model). Speech or not, per frame, on the client. Model: tiny VAD. 30 ms.
4. **S4 Chunk and endpoint** (Client). Cut on 400 ms silence, hard cut at 12 s. No model. 400 ms.
5. **S5 Transport** (Server). Binary websocket, bounded queue. No model. 30 ms.
6. **S6 Transcribe** (Model). Whisper class model on our own server. Model: local ASR. 1.2 to 3 s.
7. **S7 Diarise** (Model). Embed and cluster, who spoke this. Model: speaker model. 150 ms.
8. **S8 Normalise** (Server). Language tag, glossary, casing, punctuation. No model. 50 ms.
9. **S9 Emit** (State). Partial then final segment on the bus. No model. 20 ms.

### 1.1 Stage by stage

| # | Stage | Data in | Data out | Model | Target |
|---|---|---|---|---|---|
| S1 | Microphone capture | Room sound | Float32 PCM, 16 kHz mono, 20 ms frames, with a session-relative media timestamp on every frame | None. An AudioWorklet and a ring buffer | 20 ms |
| S2 | Signal conditioning | PCM frames | Same frames, plus RMS level, clipping flag and an estimated noise floor | None. A high-pass at 80 Hz and arithmetic | 5 ms |
| S3 | Voice activity detection | PCM frames plus noise floor | Speech or silence per frame, and from that an utterance start and end | A tiny VAD, Silero class, in WASM on the client. Small enough that it is not really a model call | 30 ms |
| S4 | Chunking and endpointing | Frame-level speech flags | An audio chunk of 0.6 to 12 s with t_start, t_end, an idempotency key over the bytes, and a flag saying whether it ended on silence or a hard cut | None, but this is where the design decisions are | 400 ms of trailing silence, by definition |
| S5 | Transport | Audio chunk | The same chunk, server side, with an arrival sequence number | None. A binary websocket, bounded queue, backpressure signal to the client | 30 ms on a local network |
| S6 | Speech to text | Audio chunk | Text, word-level timings, per-word log probability, detected language | Local ASR, Whisper large-v3-turbo or medium on a single GPU. This is the model the concept stands or falls on | 1.2 to 3 s for an 8 s chunk |
| S7 | Speaker diarisation | Audio chunk plus the running speaker embedding store | A speaker label per word range, with a confidence, and a flag when two speakers overlap | A speaker embedding model plus online clustering. Not an LLM | 150 ms |
| S8 | Normalisation | Raw ASR text | Cased, punctuated text with a language tag per segment, domain terms corrected against a session glossary | None. Rules plus a glossary. Whisper already emits punctuation | 50 ms |
| S9 | Emit to the bus | Normalised segment | transcript.segment.partial, superseded later by transcript.segment.final, written to the transcript store | None | 20 ms |

### 1.2 Chunking, which is the decision that matters

Whisper class models want 5 to 30 seconds of context to punctuate and disambiguate well, and the room wants text on screen in under a second. Those pull in opposite directions and the chunking strategy is where the trade is made. Three options, all defensible:

- **Fixed windows with overlap.** 8 second windows, 1.5 second overlap, stitched by aligning the overlap. Simple, predictable cost, but it cuts words in half and the stitch is fiddly.
- **Silence endpointing.** Cut when the VAD reports 400 ms of trailing silence, hard cut at 12 seconds so a monologue still produces output. Better text, but latency depends on how the person speaks, and someone who does not pause produces 12 second blocks.
- **Both, in two lanes.** A small fast model on short windows for the live caption strip, and a large model on endpointed utterances for the transcript of record, which supersedes the fast text a second or two later.

The two-lane version is what this document assumes, because it is the only one that gives both a responsive caption and a good transcript. It also doubles the ASR cost, which is the reason it is first on the cut list below. **What would decide it:** measure how much worse the small model is on your actual room recordings. If the gap is small, run one lane on the small model and stop paying twice.

**Diagram: two lane transcription, fast provisional text superseded by an accurate final segment.** Four boxes in one chain, A to D, each feeding the next. A box tagged Model is drawn with a dashed outline: a model runs there, so its output is provisional until a person accepts it.

1. **A Fast lane** (Model). Small model, 2 s windows, no overlap. Model: small ASR. About 600 ms.
2. **B Caption strip** (Client). Grey, provisional, word by word. No model. Instant.
3. **C Slow lane** (Model). Large model on the endpointed utterance. Model: large ASR. 1.2 to 3 s.
4. **D Supersede** (State). Final segment replaces the provisional text. No model. 20 ms.

### 1.3 Latency budget

Measured from the moment a speaker stops talking to the moment a final, speaker-tagged segment is on the bus. The caption strip is much faster than this and is what the room actually perceives.

| # | Stage | Time |
|---|---|---|
| 1 | Endpoint wait, 400 ms of silence | 400 ms |
| 2 | Transport and queue | 60 ms |
| 3 | Transcription of an 8 s chunk | 2 s |
| 4 | Diarisation | 150 ms |
| 5 | Normalisation and emit | 70 ms |

**Total** 2.7 s to a final segment at the median, budget 5 s at the 95th percentile. Provisional caption text inside 700 ms.

**While waiting the room sees:** grey provisional words appearing as they are spoken, firming up to black when the final segment lands, and a queue-depth badge when the server is behind

### 1.4 Failure modes

The rule for this pipeline: there is no state in which it produces nothing and says nothing. Silence from the audio pipeline is always reported as silence from the audio pipeline, never left to look like silence in the room.

| Failure | What the room sees | Fallback |
|---|---|---|
| One laptop microphone, eight people, and the far end of the table is below the noise floor | Nothing. The far speaker simply does not appear in the transcript, which is the dangerous part | The level meter from S2 is the guard. If a session runs for five minutes with a channel level under threshold, say so out loud on the canvas: the room is only being half heard. Offer phones as extra capture devices, and keep typed input (F1.7) one click away. |
| Two people talk over each other, which is what a design meeting is | A merged, half-wrong segment | S7 flags the overlap. An overlapping segment is marked low confidence, gets no speaker attribution at all rather than a wrong one, and is excluded from decision and action extraction in pipeline 6. It stays in the transcript, it just does not get promoted into claims. |
| Dutch and English inside one sentence | The model locks onto one language and transliterates the other into nonsense | Run language detection per chunk. If the chunk is mixed, force the multilingual path, tag the segment mixed, and lower its weight for entity extraction. There is no clean fix here: accept a worse transcript on mixed segments and make sure the tools downstream know it is worse. |
| The GPU queue grows and transcription falls behind real time | Live captions lag further and further behind the speaker | Automatic model tier drop at a queue depth over roughly 5 chunks: large to medium to small. Show a badge naming the tier. Falling behind quietly is the failure that destroys trust, falling behind visibly is a tolerable one. |
| The capture client loses network for 40 seconds | A gap | Ring-buffer 60 seconds of audio locally and upload on reconnect. If the gap exceeds the buffer, write an explicit gap marker into the transcript with its duration. Never close a gap silently, because every consumer downstream will treat missing text as nothing having been said. |
| Diarisation attributes a sentence to the wrong person | A quote under the wrong name, which is the single most damaging error the tool can make | Never show a name until a speaker label is above threshold and has been confirmed once by a human. Until then, Speaker 2. Question answering refuses to attribute rather than guessing, see pipeline 5. |
| Someone withdraws consent mid-session | Capture stops | Hard stop at S1, in-flight buffers discarded, a visible confirmation. Handled in pipeline 8. |

#### Cost drivers

- **ASR compute per audio minute** is the whole cost. A 90 minute meeting is 90 minutes of GPU whatever anyone says or does.
- **VAD gating is the main lever.** A meeting is typically 60 to 75 percent speech, so transcribing only detected speech saves a quarter to a third outright.
- **The two-lane design doubles it** for the part of the meeting that contains speech.
- **Diarisation** adds roughly 5 to 10 percent on top of ASR. Cheap relative to the risk it carries.
- **Word timings** are nearly free from the ASR, and they are what citations in pipeline 5 need. Keep them.

#### What could be cut, in order

- **The fast lane.** Lose the live caption strip, keep an accurate transcript arriving two seconds late. Halves the cost. Test whether anyone looks at the caption strip before paying for it.
- **Diarisation.** Replace with per-device attribution: whoever's phone was the loudest source gets the label. Cruder, free, and honest about being crude. This weakens F1.3 and with it the question "what did Sanne say", which is one of the three seconds the concept is aimed at, so cutting it is a concept-level decision and not an optimisation.
- **Model size.** Medium instead of large, at a real accuracy cost on Dutch.
- **Continuous capture itself.** The last retreat is push-to-talk transcription only: nothing is recorded unless someone holds a button. That kills the notulation pipeline and most of the question answering one, and turns Jarvaids into a capture-and-layout tool. It is a smaller product, but it is a product, and it removes the consent problem almost entirely.

## 2 · Image

**2 · Image: a photographed wall to separate, placed notes**

Concept 001 makes this the core, and names its riskiest assumption here: that handwriting on sticky notes, photographed under room lighting at an angle, can be read well enough to be worth correcting. If it cannot, correcting the output costs more than retyping and the feature has negative value. That test comes before this pipeline gets built, not after.

**Functionalities covered (from the flowchart):** F1.4 Photograph intake, F1.5 Note segmentation, F1.6 Handwriting reading, F3.1 Canvas data model, F3.5 Provisional styling, F6.3 Citation to source, F6.5 Correction capture.

Kind tags used in this diagram: **Client** = Client, in the browser; **Server** = Server code, no model; **Model** = A model runs here; **State** = Writes to shared state; **Guardrail** = Guardrail, can stop the pipeline; **Human** = A human decides.

**Diagram: image pipeline stage rail, twelve stages from phone camera to placed notes.** Twelve stages in one chain, S1 to S12, each feeding the next. The rail wraps onto a new row after S4 and again after S8, marked "continues", which is layout only and not a branch. A stage tagged Model is drawn with a dashed outline: a model runs there, so its output is provisional until a person accepts it.

1. **S1 Shoot** (Client). Phone camera via the join link, no login. No model. Human time.
2. **S2 Prepare** (Client). Orient by EXIF, strip GPS, downscale to 2048. No model. 300 ms.
3. **S3 Upload** (Server). Signed URL, original kept for correction. No model. 1 to 4 s.
4. **S4 Quality gate** (Guardrail). Blur, exposure, size. Retake now or never. No model. 100 ms.
5. **S5 Rectify** (Server). Find the wall plane, warp out the angle. No model. 150 ms.
6. **S6 Segment notes** (Model). Split the wall into individual quads. Model: vision. 200 to 600 ms.
7. **S7 Crop and normalise** (Server). Warp each note upright, white balance. No model. 100 ms.
8. **S8 Read** (Model). Handwriting to text, per note, batched. Model: vision. 1.5 to 6 s.
9. **S9 Colour** (Server). Median hue mapped to a palette name. No model. 10 ms.
10. **S10 Cluster** (Server). Group by proximity, then by colour. No model. 20 ms.
11. **S11 Score** (Server). Per-note confidence, crop kept attached. No model. 10 ms.
12. **S12 Place** (State). Provisional items on the canvas, dashed. No model. 50 ms.

### 2.1 Stage by stage

| # | Stage | Data in | Data out | Model | Target |
|---|---|---|---|---|---|
| S1 | Photograph | A wall, a sketch, a screen | A JPEG in the phone browser | None | Human time. The real problem is nobody remembers to do it |
| S2 | Client preparation | Raw JPEG, often 8 to 12 MP | JPEG, long edge 2048 px, quality 0.8, rotation applied from EXIF then EXIF discarded apart from orientation, GPS removed before the bytes leave the phone | None | 300 ms |
| S3 | Upload and store the original | Prepared JPEG | image_id, the original bytes in session blob storage, an image.uploaded event | None | 1 to 4 s on venue wifi. Usually the slowest stage in the pipeline |
| S4 | Quality gate | Stored image | Pass, or a retake prompt naming the reason | None. Variance of the Laplacian for blur, a histogram for exposure, pixels-per-note estimate for resolution | 100 ms |
| S5 | Rectification | Image | A perspective-corrected image plus the homography, so every later coordinate can be mapped back to the original photograph | None in the first version: contour detection for the dominant quad. A segmentation model is the upgrade if that fails often | 150 ms |
| S6 | Note segmentation | Rectified image | A list of quads, one per candidate note, in rectified coordinates | Vision. Start with HSV region proposals for saturated rectangles, which is free and works on clean walls, and fall back to an instance segmentation model or a VLM asked for bounding boxes | 200 to 600 ms |
| S7 | Crop and normalise | Quads plus image | One upright, white-balanced crop per note, typically 300 by 300 px | None | 100 ms for 30 notes |
| S8 | Handwriting recognition | Crops | Text per note, with a confidence | Vision. One call per crop is the accurate option; a grid of 9 crops in one call is roughly nine times cheaper and measurably worse at keeping text matched to the right cell | 1.5 to 6 s for 30 notes, depending on batching |
| S9 | Colour extraction | Crop interior | A palette name, yellow, pink, blue, green, orange, white, plus the raw hue | None. Median hue, ignoring the outer 15 percent of the crop so the marker ink and shadow do not skew it | 10 ms |
| S10 | Spatial clustering | Note centroids and sizes | Cluster ids, from density clustering with the neighbourhood radius set as a multiple of the median note width so it scales with how far away the photograph was taken | None | 20 ms |
| S11 | Confidence and provenance | Everything above | Per note: text confidence, crop quality, image_id, quad, homography. Anything under threshold is placed with the crop shown instead of the text | None | 10 ms |
| S12 | Place on the canvas | Scored notes | Provisional canvas items in a block that does not overlap anything human-placed, plus an image.notes.extracted event | None. Placement uses the collision logic from pipeline 4 | 50 ms |

### 2.2 Progressive reveal, and why it is worth the extra work

The naive build waits for every stage and then shows 30 finished notes after 15 seconds. The better build shows the geometry as soon as segmentation is done, at roughly 3 seconds: 30 correctly positioned, correctly coloured grey rectangles, filling in with text one by one as recognition returns. Same total time, completely different experience, because the person who took the photograph can see immediately whether the split was right, which is the thing they can still fix by taking a better photograph while they are standing there.

It also changes what a slow or failed recognition stage means. With progressive reveal, a total failure of S8 leaves a correctly laid out wall of images that someone can type into. Without it, a total failure of S8 leaves a spinner.

### 2.3 Latency budget

For a photograph of a wall with about 30 notes, taken on a phone on ordinary venue wifi.

| # | Stage | Time |
|---|---|---|
| 1 | Client prepare and downscale | 300 ms |
| 2 | Upload | 2.5 s |
| 3 | Quality gate and rectify | 250 ms |
| 4 | Segmentation | 400 ms |
| 5 | Crops | 100 ms |
| 6 | Handwriting recognition, 30 notes | 4 s |
| 7 | Colour, cluster, score, place | 90 ms |

**Total** about 7.6 s to full text, with correct geometry visible at 3.5 s. Budget 20 s at the 95th percentile, and above that it must still be showing partial results rather than a spinner.

**While waiting the room sees:** their own photograph, then grey placed rectangles in the right shape and colour, then text arriving note by note

### 2.4 Failure modes

| Failure | What the room sees | Fallback |
|---|---|---|
| Glare from a window or ceiling light wipes out a strip of the wall | Notes missing from that strip, silently | The quality gate cannot see this reliably. What can: compare the note count to the cluster geometry and flag a suspicious gap, and always show the original photograph next to the extracted block so a human can see what is missing. Assume this will happen and design for noticing it, not for preventing it. |
| Notes overlap each other, or are stuck at an angle | Two notes merged into one, or one split into two | Merged and split notes are both correctable by hand in one gesture, so make split and merge a first-class canvas action rather than something you have to undo and retype. Keep the crop attached so the correction is done against the picture. |
| Handwriting is genuinely illegible, or it is a drawing not words | Confident nonsense, which is worse than nothing | Threshold on the recognition confidence. Below it, place the crop as an image item with no text at all and a tap-to-type affordance. An unreadable note that shows its own photograph is honest and still useful; an unreadable note rendered as plausible words poisons every summary downstream. |
| Someone photographs a laptop screen with an email or a personal calendar on it | Personal data uploaded and possibly exported | Photographs never auto-commit. The uploader sees the extracted block first and presses place. This costs one tap and it is the only defence there is. Retention treats image originals as a separate tier, see pipeline 8. |
| Wifi in the room is slow and the 2 MB upload takes 30 seconds | Somebody standing holding a phone, waiting | Show the upload progress on the shared canvas, not only on the phone, so the room knows a photograph is coming. Queue and retry on failure. Consider a second downscale tier, 1280 px, chosen automatically when the first upload is slow. |
| The vision model reads a note but assigns the text to the wrong crop when batching | Text scrambled across notes, and it looks plausible | This is the specific cost of batching. Mitigate by putting a printed index in each cell of the batch grid and rejecting any response whose indices are not a permutation of what was sent. If the rejection rate is over a few percent, stop batching and pay for single calls. |
| Clustering by proximity is simply wrong, because the team grouped by meaning and not by position | Groups the team does not recognise | Proximity is a guess and must be presented as one. Draw the cluster hulls provisionally and make regrouping a drag. Never let a cluster id from this stage feed a summary before a human has accepted it. |

#### Cost drivers

- **Vision calls per note** dominate. 30 notes is 30 calls unless they are batched, and a workshop wall gets photographed maybe five or ten times in a session.
- **Batching is the big lever and it is not free:** roughly nine times cheaper per note, and it introduces the cell-mismatch failure above. That trade should be measured, not assumed.
- **Image size.** Vision pricing is usually by image tiles, so the 2048 px downscale in S2 is a cost decision as much as a bandwidth one.
- **Storing originals** for the whole retention window, which is small in money and significant in privacy.
- **Stages S4, S5, S7, S9, S10, S11 need no model at all.** Most of this pipeline is classical image processing, which is worth saying out loud because it is where the reliability comes from.

#### What could be cut, in order

- **Handwriting recognition.** Keep segmentation, cropping, colour and clustering, and place each note as its own small image. The wall is now digitised, positioned and groupable, just not searchable. That is most of the value of F1.4 and F1.5 at none of the risk of F1.6, and it is the version to build first precisely because it works whatever the week 1 test says.
- **Rectification.** Ask people to stand square to the wall. Free, slightly worse, and a sentence of instruction rather than a stage.
- **Clustering.** Place the notes in the grid they were photographed in and let the team group them. Proximity clustering is a guess anyway.
- **Automatic segmentation.** The floor of this pipeline is one photograph placed on the canvas as a single image. Even that beats nothing, because the photograph is at least on the board with the rest of the meeting instead of in somebody's camera roll.

> **The number that decides this pipeline**
>
> Retyping one sticky note from a legible crop takes about four seconds. Correcting a wrong machine reading takes about the same, plus the time to notice it is wrong, which is the expensive part. So the break-even is not 100 percent accuracy, it is roughly: **the feature wins if the fraction of notes needing correction is below about 30 percent and the wrong ones are obvious at a glance.** Concept 001 proposes 80 percent correct on ten photographs as the gate, which is consistent with that. Agree it before the test, and measure separation accuracy and text accuracy separately, because a pipeline that splits the wall correctly and reads it badly is fixable and one that splits it wrongly is not.
>

## 3 · Command

**3 · Command: an utterance to one validated canvas operation**

This is the pipeline with the most ways to be wrong and the fewest ways to hide it, because every one of its errors happens on a shared screen in front of everybody. It is also the one the team's notes call core. Two of its stages are ordinary classification work and one of them, referent resolution, is genuinely hard and has no good fallback other than asking a human.

**Functionalities covered (from the flowchart):** F2.5 Command detection, F2.6 Intent parsing, F4.3 Roles, F3.4 Non-destructive insertion, F3.7 Undo, F6.4 Degradation behaviour.

Kind tags used in this diagram: **Client** = Client, in the browser; **Server** = Server code, no model; **Model** = A model runs here; **State** = Writes to shared state; **Guardrail** = Guardrail, can stop the pipeline; **Human** = A human decides.

**Diagram: command pipeline stage rail.** Nine stages in one chain, S1 to S9, each feeding the next. The rail wraps onto a second row after S5, marked "continues", which is layout only and not a branch. A stage tagged Model is drawn with a dashed outline: a model runs there, so its output is provisional until a person accepts it.

1. **S1 Address** (Client). Push-to-talk, wake phrase, or typed. Model: keyword spot. 50 ms.
2. **S2 Isolate** (Server). Pull the utterance out of the transcript. No model. 400 ms.
3. **S3 Was it for us?** (Model). Addressed to the tool, or to a colleague. Model: classifier. 200 to 500 ms.
4. **S4 Intent** (Model). One of a closed set of operations. Model: LLM. Latency shared with S5.
5. **S5 Slots** (Model). Form, axis labels, time range, count. Model: LLM. 400 to 900 ms.
6. **S6 Referents** (Model). Which items does "those three" mean. Model: rank, then LLM. 50 to 600 ms.
7. **S7 Confidence gate** (Guardrail). Act, preview, or ask. Never guess. No model. 5 ms.
8. **S8 Permission** (Guardrail). Role check, and the destructive split. No model. 5 ms.
9. **S9 Dispatch** (State). One validated command event on the bus. No model. 20 ms.

### 3.1 Stage by stage

| # | Stage | Data in | Data out | Model | Target |
|---|---|---|---|---|---|
| S1 | Addressing | A button press, a wake phrase, or typed text | A marker on the timeline saying a command may start here | Keyword spotting only if a wake phrase is used, a small on-device model. Push-to-talk and typing need no model at all | 50 ms |
| S2 | Utterance isolation | Transcript segments around the marker | The candidate command text, plus the preceding 30 seconds of transcript as context | None. It reuses pipeline 1, so there is no extra transcription cost | Bounded by the endpoint wait in pipeline 1 |
| S3 | Addressed classification | Candidate text plus context | A probability that this was said to the tool rather than to a person in the room | A small classifier or a cheap LLM call. Skipped entirely when the route was push-to-talk or typing, because those already answered the question | 200 to 500 ms |
| S4 | Intent classification | Candidate text | Exactly one operation from a closed set: cluster, timeline, matrix, flow, hierarchy, split, merge, label, summarise, answer, undo, delete, capture, export | LLM, constrained to the enum. The closed set is the point: it makes the failure space finite | Shared call with S5 |
| S5 | Slot filling | Candidate text plus canvas summary | Operation arguments: form, axis labels, time range, group count, target region | Same LLM call, structured output against a schema | 400 to 900 ms together with S4 |
| S6 | Referent resolution | Slots, canvas state, current selection, last 60 s of transcript | A concrete set of item ids, or an explicit ambiguous result | Ranking in code first over four candidate sources. Only if the top candidates are close does it cost an LLM call | 50 ms when the ranking is decisive, 600 ms when it is not |
| S7 | Confidence gate | Intent confidence, referent confidence, operation class | One of three routes: execute, preview, or ask | None. A table of thresholds, which is deliberate: this rule must be readable and changeable without touching a prompt | 5 ms |
| S8 | Permission | Route plus the speaker role | Allowed or refused, with a reason shown | None. F4.3, and the open question of who may command it lives here | 5 ms |
| S9 | Dispatch | A validated command | command.accepted on the bus with an idempotency key, consumed by pipeline 4 or pipeline 5 | None | 20 ms |

### 3.2 The three routes in, and the fork nobody has decided yet

There are three ways an instruction can reach S2, and they have wildly different costs and error profiles. This is a real fork in the design, not an implementation detail:

- **Push-to-talk.** Hold a button on the shared screen or a phone. Near-perfect precision, zero model cost for addressing, and it makes the tool feel like an instrument rather than an eavesdropper. The cost is that someone must remember it exists, and in a flowing workshop nobody does.
- **Wake phrase.** A small keyword model runs continuously on the client. Cheap in tokens, natural to use, and it introduces a false-accept rate that is small per utterance and not small over a two hour meeting.
- **Always listening.** Every transcript segment goes through the addressed classifier. This is the most natural interaction and by far the most expensive: it turns an event-driven pipeline into a continuous one, running hundreds of classifications per meeting, and it makes the false-accept problem permanent.

**What would decide it:** count how often a facilitator would actually want to address the tool in a real session. The team's own open question is whether anyone will address it at all. If the answer is five or ten times an hour, push-to-talk is plainly right and the wake phrase is an expensive convenience. If it is every other minute, the argument flips. That is an afternoon of observation with a stopwatch, and it should happen before a line of S3 is written.

### 3.3 The confidence gate and the destructive split

**Diagram: the confidence gate, three routes depending on confidence and whether the operation is destructive.**

Start: **Parsed command** (Model, dashed outline: a model produced it, so it is provisional). Carries intent confidence, referent confidence, operation class. It feeds into the gate.

**Is it destructive?** (Guardrail). Delete, overwrite, move human work.

From the gate, three routes:

1. Labelled **yes**, to **Always ask** (Human). Targets highlighted, an explicit yes needed, whatever the confidence was.
2. Labelled **no**, splitting three ways by confidence:
   - **Execute, with undo** (Server). Both confidences over 0.85. Targets flash first, then it acts.
   - **Preview, provisionally** (Model, dashed outline). 0.55 to 0.85. It is built, dashed, and one tap accepts or clears it.
   - **Ask** (Human). Under 0.55, or referents ambiguous. "These three?"

All four routes converge on one box, **Whatever the route** (State): "The operation is written as one event with an idempotency key. It is reversible for the whole session, not one step. It carries who asked, what was heard, and which items it resolved to, so a wrong action can be explained afterwards."

Two notes sit beside the diagram:

- "The thresholds are guesses. They are written here as numbers so that a session can be replayed against different values and the right ones argued from data rather than from taste."
- "Note what is missing: there is no route where the tool acts on a low-confidence parse. The worst outcome available to this pipeline is that it asks a question nobody wanted."

### 3.4 Referent resolution, the weak point

"Put those three on a timeline" carries no information about which three. Four candidate sources, ranked in code:

- **The current selection** on the shared screen. Strongest signal when it exists, and it usually does not, because nobody selects things in a workshop.
- **Items named in the last 60 seconds of transcript,** matched against item text. Strong when people say the words on the notes, which they often do.
- **Items created or touched most recently.** Weak but cheap, and it covers "put that on the board".
- **Topic match** between the current transcript window and item text, via the same index pipeline 5 uses. Broad, and it produces plausible wrong answers, which is the worst kind.

The ranking is deterministic. The LLM only gets involved when the top candidates are within a margin of each other, and even then it is asked to choose between a shortlist rather than to pick from the whole canvas. That containment is what makes this stage debuggable.

**Being honest about it:** there is no fallback here that keeps the interaction feeling magic. Either it resolves confidently, or it asks, and asking three times in a row makes the tool feel broken even though it is behaving correctly. The design mitigation is to make asking cheap and physical: highlight the candidates on the canvas and let someone tap, rather than reading a question out loud. **The test that would settle it** is in the unknowns section: 30 hand-built referent cases from a real transcript, scored by hand, with 80 percent agreed as the bar in advance.

### 3.5 Latency budget

From the moment the speaker stops to the moment something visibly happens. The layout itself comes from pipeline 4 and is counted there.

| # | Stage | Time |
|---|---|---|
| 1 | Endpoint wait, shared with pipeline 1 | 400 ms |
| 2 | Transcription of the command | 700 ms |
| 3 | Addressed classification | 300 ms |
| 4 | Intent plus slots, one call | 650 ms |
| 5 | Referent resolution | 200 ms |
| 6 | Gate, permission, dispatch | 30 ms |

**Total** 2.3 s to the targets lighting up on the canvas, budget 4 s at the 95th percentile. The full result including layout lands around 5 to 6 s.

**While waiting the room sees:** a listening indicator the moment the button is pressed, the heard text appearing as it is transcribed, then the resolved items flashing on the canvas before anything changes

### 3.6 Failure modes

| Failure | What the room sees | Fallback |
|---|---|---|
| False accept: someone says "let us put those three on a timeline" to a colleague and the tool does it | An uninvited change to the board, which is the failure that gets the tool switched off | Push-to-talk as the default route in any room with more than four people. Everything the tool does appears provisionally first, so a false accept is a ghost to dismiss and not a change to undo. A visible "I heard:..." line so the room can see what it thought it was told. |
| False reject: the wake phrase is missed in a noisy room | Nothing happens, the tool feels dead, and the person repeats themselves louder | A visible listening indicator so it is obvious whether it heard anything at all, plus the typed command bar as a permanently available route. A tool that quietly ignores people is worse than a tool that visibly fails. |
| Right intent, wrong referents: it groups notes 3, 4 and 5 instead of 14, 19 and 22 | The right shape built from the wrong content, which looks correct at a glance | Always highlight the resolved items on the shared screen before acting, for about a second, even on the execute route. This is cheap and it turns a silent wrong answer into a visible one. Below the referent confidence threshold, ask: "these three?" with them lit up. |
| The room repeats the command because nothing happened fast enough, and now there are two | Two timelines | An idempotency key over the normalised command text plus a speaker plus an 8 second window. The second command is recognised as a repeat and drops. See the cross-cutting section. |
| Two people command it at once | A race, and whichever finishes last wins | Commands serialise through a single queue per session. The second one is shown queued rather than being silently dropped or silently interleaved. |
| The command arrives with a transcription error in the key noun: "cluster the red ones" heard as "cluster the bread ones" | A confident action on nothing | Referent resolution simply fails to find anything and the gate routes to ask. This is the case for putting referent resolution after intent rather than inside it: a failure to resolve is a clean, detectable failure. |
| A destructive command with high confidence: "delete all of that" | Work disappears | Destructive operations never take the execute route regardless of confidence. They always confirm, and they are always undoable for the whole session, not just for one step. F3.7. |

#### Cost drivers

- **Frequency, not size.** A command is a few hundred tokens. Ten commands a meeting is nothing next to the audio pipeline.
- **Unless the addressed classifier runs on everything.** Always-listening turns this into hundreds of calls per session and makes it the second largest token cost in the system. That single design choice moves this pipeline by two orders of magnitude.
- **The canvas summary sent as context** for slot filling grows with the board. Cap it: send item ids and short labels, not full content, and never send the transcript.
- **S1, S2, S7, S8 and S9 need no model.** So does most of S6.

#### What could be cut, in order

- **The wake phrase and the addressed classifier.** Keep push-to-talk and the typed command bar. This removes the entire false-accept class of failure, removes a continuous cost, and costs one button press. It is the cut this document would actually recommend making first, not last.
- **Automatic referent resolution.** Replace with: select on the canvas, then speak. Less impressive, dramatically more reliable, and it matches how people use every other board tool.
- **The intent set.** Shrink from fourteen operations to four: cluster, timeline, summarise, answer. Each operation removed is a whole class of misparse removed with it.
- **Spoken commands altogether.** The floor is a typed command bar, which is F1.7 wearing a different hat and is the fallback for everything in this pipeline.

## 4 · Visualisation

**4 · Visualisation: a set of items to a chosen form, laid out**

This is the pipeline that decides whether Jarvaids is a different kind of tool or a notes app with a canvas background. It is also where the strongest architectural rule in the system lives: the model chooses meaning, the code chooses geometry. A model that emits coordinates cannot be tested, cannot be made deterministic, and will eventually put a box on top of somebody's work.

Topic and choice colours, planned: Each main topic, subject or choice can have a distinct sticky-note colour. Notes in the same group share it, with visible group labels and an overview key. AI assignments are provisional and team-adjustable; colours stay consistent as notes expand or new content arrives. Topic fills never replace provenance boundaries or review labels. Planned F3.8: the overview uses collapsed sticky-note main points with supporting detail and session sources available in place. AI organises incoming notes automatically as provisional structure, preserving accepted arrangements and team adjustments; conflicting regroupings require review. This is future product behaviour, not a change to the capture-first milestone or a claim that automatic organisation is implemented. Expansion is a local viewing action with no model call, shared-position write or acceptance. Review exposes the complete proposed content and evidence before Accept is available.

See [the expandable-note contract](../../app/design-system/spec/expandable-notes.md) for source attribution, temporary spacing, fixed-axis anchors, accessibility and export requirements.

**Functionalities covered (from the flowchart):** F3.1 Canvas data model, F3.2 Form selection, F3.3 Automatic layout, F3.4 Non-destructive insertion, F3.5 Provisional styling, F3.6 Direct manipulation, F3.8 Expandable sticky notes, F6.5 Correction capture.

Kind tags used in this diagram: **Client** = Client, in the browser; **Server** = Server code, no model; **Model** = A model runs here; **State** = Writes to shared state; **Guardrail** = Guardrail, can stop the pipeline; **Human** = A human decides.

**Diagram: visualisation pipeline stage rail.** Ten stages in one chain, S1 to S10, each feeding the next. The rail wraps onto a second row after S5, marked "continues", which is layout only and not a branch. A stage tagged Model is drawn with a dashed outline: a model runs there, so its output is provisional until a person accepts it.

1. **S1 Select content** (Server). Which items are in scope for this call. No model. 20 ms.
2. **S2 Read features** (Server). Dates, ordinals, pairs, colours, counts. No model. 30 ms.
3. **S3 Choose a form** (Model). Rules first, model only for the rest. Model: LLM. 0 to 800 ms.
4. **S4 Generate structure** (Model). Main points, detail and relations. Never pixels. Model: LLM. 1 to 3 s.
5. **S5 Validate** (Guardrail). Schema, ids exist, one repair retry. No model. 10 ms.
6. **S6 Lay out** (Server). Deterministic engine per form, seeded. No model. 50 to 200 ms.
7. **S7 Avoid collisions** (Server). Human items are immovable obstacles. No model. 30 ms.
8. **S8 Style as provisional** (Server). Dashed, labelled, with source and time. No model. 5 ms.
9. **S9 Commit** (State). Canvas patch with provenance, streamed. No model. 20 ms.
10. **S10 Accept or reject** (Human). And the correction is logged as evidence. No model. Human time.

### 4.1 Stage by stage

| # | Stage | Data in | Data out | Model | Target |
|---|---|---|---|---|---|
| S1 | Content selection | A referent set from pipeline 3, a canvas selection, or a topic slice from the transcript | Item ids, main points, supporting text and source references, capped at 60 items | None | 20 ms |
| S2 | Feature extraction | The item set | Counts of items carrying a parseable date, an ordinal, a causal verb, a two-way opposition, an existing colour grouping, plus text length statistics | None. Regular expressions and counting, and it is the stage that makes the next one cheap | 30 ms |
| S3 | Form selection | Features, and the command if there was one | One of cluster, timeline, matrix, flow, hierarchy, plus a reason string that is shown to the user | LLM, but only on the residual. If the command named a form, obey it. If over 60 percent of items carry a date, timeline. If the features are flat, ask the model | 0 ms when a rule fires, 800 ms when it does not |
| S4 | Structure generation | Items plus the chosen form | Source-linked main points and supporting detail, plus labelled groups or choices, axes, parents and rank. Preserve qualifications and disagreements. Colour keys come from a stable palette mapping, never invented model colour codes. No coordinates anywhere | LLM with a strict output schema. This is the only stage in the pipeline where a model touches the content | 1 to 3 s for 30 items |
| S5 | Validation | Model output | Validated, or one repair attempt, or a fallback to the original arrangement or a simple ordered set without invented relationships | None. Schema and source-reference checks, every id must exist, every item assigned exactly once, group count within bounds; validation is not human acceptance | 10 ms |
| S6 | Layout | Validated structure | Coordinates and sizes for every item and every group frame. Force-directed for clusters, a scaled axis for timelines, a grid for matrices, a layered graph for flows, a tidy tree for hierarchies | None. Deterministic, seeded from the item ids so the same input always produces the same picture | 50 to 200 ms |
| S7 | Collision avoidance | Coordinates plus the current canvas occupancy | Coordinates translated into the nearest free region large enough to hold the block, with the canvas extended rather than anything human-placed being moved | None. An occupancy grid at about 20 px | 30 ms |
| S8 | Provisional styling | Placed block | Topic fills from a stable group mapping, group labels and a key; independent dashed boundaries, neutral-backed Provisional labels and source handles | None. F3.5, the cheapest trust mechanism in the tool | 5 ms |
| S9 | Commit | Styled block | A canvas patch against a version number, provenance on every item, streamed to every connected screen | None | 20 ms |
| S10 | Accept, edit or reject | A human | Review full main points, detail and evidence before accepting content. Review arrangements separately; neither expansion nor layout acceptance accepts child claims. Log corrections for F6.5 | None | Human time |

### 4.2 Form selection: rules first, model for the remainder

A purely model-driven choice is impossible to debug and drifts between runs. A purely rule-driven choice is rigid but honest. The split proposed here is rules for the cases that have a clear signal, model for the ones that do not:

**Diagram: form selection decision path, explicit command, then feature rules, then the model as the last resort.**

Start: **Item set** (Server), plus features from S2. It feeds three routes, tried in this order:

1. **Command named it** (Server). "on a timeline". Obey, and do not second guess.
2. **A feature rule fires** (Server). Over 60% carry a date or an ordinal, or the items already carry two colours used as an opposition.
3. **Nothing fires** (Model, dashed outline: a model runs here, so its output is provisional). Ask the model, with the features as evidence and a required one-line reason.

All three routes converge on **Chosen form** (State): with the reason kept, shown to the user, and logged for the form distribution check.

That feeds one more box: **And a way out** (Human). Five buttons on the toolbar that recast the same items into another form in one click. If people use these more than the automatic choice, that is the finding.

A note sits under the diagram: "The reason string is not decoration. It is the only way anyone can argue with the choice afterwards, and the only way to tell a good choice from a lucky one."

### 4.3 Latency budget

The latency figures below predate F3.8 summary and detail generation; they are not measurements or promises for the expanded concept. Re-measure that work when implemented.

For 30 items, from the accepted command to a finished block on every screen. This budget follows on from pipeline 3, so the room has already been waiting about two seconds when it starts.

| # | Stage | Time |
|---|---|---|
| 1 | Selection and features | 50 ms |
| 2 | Form selection, model path | 800 ms |
| 3 | Structure generation | 2.2 s |
| 4 | Validation | 10 ms |
| 5 | Layout | 120 ms |
| 6 | Collision and styling | 35 ms |
| 7 | Commit and render | 120 ms |

**Total** 3.3 s here, so roughly 5.5 s from the end of the spoken command. Budget 8 s at the 95th percentile.

**While waiting the room sees:** a ghost frame in the shape of the chosen form appearing within about 500 ms, in the place the block will land, with the item count on it. The room watches it fill rather than watching a spinner somewhere else

### 4.4 Failure modes

| Failure | What the room sees | Fallback |
|---|---|---|
| Everything becomes a cluster | A list with extra steps, which is exactly what F3.2 names as the failure mode | Instrument it. Log the chosen form on every invocation and look at the distribution after a session. If clusters are over about half, the form selection is not working and the honest response is to remove the automatic choice and put five buttons on the toolbar instead. |
| The layout is unstable: running it twice on the same content gives two different pictures | Items jumping around, which is disorienting on a shared screen and reads as the tool being unsure | Seed the layout deterministically from item ids, sort inputs stably, and never re-run a layout that is already on screen unless the content changed. A layout that moves for no reason costs more trust than a mediocre layout that stays put. |
| The new block lands on top of work the team placed by hand | A violation of F3.4, which the flowchart says loses the room permanently | S7 treats human items as immovable. If there is genuinely no free region, extend the canvas and scroll to the new block rather than compressing anything. Never negotiate with this rule. |
| The model returns structure that does not validate: invented ids, items assigned twice, twelve groups for eight items | Nothing, if it is handled; nonsense, if it is not | Schema validation, one repair retry with the errors fed back, then retain the original arrangement or a simple ordered set without inferred relationships. A degraded but correct picture beats a clever broken one. |
| Labels do not fit the boxes | Text spilling over the edges, which makes the whole thing look amateur | Measure and wrap the complete main point. Supporting detail opens through an explicit control, never hover alone. Grow the note and use temporary local spacing without changing saved positions; keep fixed semantic axis markers anchored. |
| Too many items: someone asks it to lay out the whole board | A slow call and an unreadable wall of boxes | Cap at 60. Above the cap, first group into themes and lay out the themes, with the items inside collapsed. Say what was done rather than silently truncating. |
| The form is right and the content assignment is wrong: the timeline is real but three items are in the wrong month | Very hard to spot, because it looks finished | No automated defence. What helps: each item keeps a visible link to the transcript moment or note crop it came from, so an assignment can be checked in one click, and the whole block stays provisional until a human accepts it. |

#### Cost drivers

- **Structure generation scales with items times tokens.** 30 short notes is small; 30 paragraphs of transcript is not. Send labels, not bodies.
- **Invocation frequency is the thing to control.** Re-laying out on every canvas change would be ruinous and pointless. This runs on an explicit command, or on an idle trigger with a floor of a couple of minutes between runs.
- **Form selection is nearly free when the rules fire,** which is the reason for doing the feature extraction in code first.
- **Seven of the ten stages need no model.** All of the layout, all of the collision logic, all of the styling and committing. The visual quality of this tool is mostly ordinary geometry code, and it is worth budgeting engineering time accordingly.

#### What could be cut, in order

- **Model-driven form selection.** Rules plus five toolbar buttons. The human picks the form, the machine does the placing. This keeps the actual work saved, which is arranging 30 items neatly, and drops the part that is hardest to defend.
- **Structure generation for anything but clustering.** Group by colour and proximity from the image pipeline, or by topic from the transcript, with no model at all.
- **Flows and hierarchies.** Both are layout engines of their own, both are the least asked for, and each is a week.
- **Automatic invocation.** The floor is: nothing happens unless someone asks for it. That is a smaller tool and a much easier one to trust.

> **The uncomfortable possibility**
>
> A rules-only version of this pipeline, where a human picks the form from a toolbar and the machine only does layout and collision avoidance, might well test better than the model version: faster, deterministic, no wrong-form failures, and the human keeps the interesting decision. If that turns out to be true it is a finding worth reporting rather than a defeat, because it locates precisely where the model earns its place in this tool and where it does not. It would also mean the AI in the visualisation pipeline sits in S4 only, and F3.2 becomes a no.
>

## 5 · Answers

**5 · Question answering: "what did she say about the paywall?"**

One of the three seconds the concept is aimed at. The engineering is the best understood of any pipeline here, and the design work is almost entirely in what it does when the evidence is thin. A confident wrong answer mid-meeting is worse than no answer, and that is a design property, not a model property: the refusal has to be a rule in the code, not a line in a prompt.

**Functionalities covered (from the flowchart):** F2.7 Grounded question answering, F6.3 Citation to source, F5.4 Searchable archive, F1.3 Speaker separation, as a dependency.

Kind tags used in this diagram: **Client** = Client, in the browser; **Server** = Server code, no model; **Model** = A model runs here; **State** = Writes to shared state; **Guardrail** = Guardrail, can stop the pipeline; **Human** = A human decides.

**Diagram: question answering pipeline stage rail.** Eight stages in one chain, S1 to S8, each feeding the next. The rail wraps onto a second row after S4, marked "continues", which is layout only and not a branch. A stage tagged Model is drawn with a dashed outline: a model runs there, so its output is provisional until a person accepts it.

1. **S1 Trigger** (Client). Typed question, or intent=answer. No model. 0 ms.
2. **S2 Understand** (Model). Rewrite into a self-contained query. Model: small LLM. 300 ms.
3. **S3 Retrieve** (Server). Keyword and vector, plus the entity index. Model: embeddings. 80 ms.
4. **S4 Rerank** (Model). Top twelve down to top five. Optional. Model: reranker. 300 ms.
5. **S5 Answer** (Model). Grounded, with span ids required. Model: LLM. 1 to 3 s.
6. **S6 Bind citations** (Server). Span ids back to real timestamps, verified. No model. 30 ms.
7. **S7 Refuse if thin** (Guardrail). No evidence means no answer. A code rule. No model. 5 ms.
8. **S8 Show** (State). Provisional card that jumps to the moment. No model. 20 ms.

### 5.1 Stage by stage

| # | Stage | Data in | Data out | Model | Target |
|---|---|---|---|---|---|
| S1 | Trigger | A typed question, or a command with intent answer | The raw question plus who asked and when | None | 0 ms |
| S2 | Query understanding | Question plus the last two minutes of transcript plus the entity index | A self-contained query with pronouns resolved, plus optional filters: a time range, a speaker, an agenda item | A small LLM. "What did she say about that" is useless without this stage | 300 ms |
| S3 | Retrieval | Rewritten query | Top twelve candidate spans, each a 30 second transcript window, plus any directly matching entities: decisions, actions, open questions | Hybrid: keyword search, which needs no model, and vector search over rolling windows, which needs a small embedding model running continuously | 80 ms. A ninety minute meeting is only about twelve thousand words, so this is all in memory |
| S4 | Reranking | Candidates | Top five | A cross-encoder or a cheap LLM. Optional, and the first thing to cut | 300 ms |
| S5 | Grounded generation | Query plus five spans | An answer in which every sentence carries the id of the span it came from, plus a direct quotation where one exists | LLM at low temperature, with the instruction that unsupported sentences must not be written. The instruction is not the safeguard, S6 and S7 are | 1 to 3 s, streamed |
| S6 | Citation binding | Answer plus span ids | Each citation resolved to a timestamp and a speaker label. Any sentence with an invalid id is dropped. Any quotation that does not string-match the transcript is dropped | None, and it must be code and not a prompt, because this is the stage that turns "trust me" into "check me" | 30 ms |
| S7 | Refusal check | Retrieval scores plus surviving citations | Either an answer, or an explicit "that is not in this session", with the nearest few moments offered anyway so the person can judge for themselves | None. A threshold on the best retrieval score and a requirement that at least one citation survived S6 | 5 ms |
| S8 | Present | Answer plus citations | A provisional card on the canvas. Clicking a citation scrolls the transcript to that moment, and plays the audio if it still exists | None | 20 ms |

### 5.2 The index, which is smaller than people expect

A two hour meeting is roughly fifteen thousand words. That is a small enough corpus that keyword search over it is instant and an embedding index over 30 second windows is a few hundred vectors. There is no infrastructure problem here. The two things that do need care:

- **Window overlap.** Windows of 30 seconds with 10 seconds of overlap, so an answer that straddles a boundary is not lost. Cheap insurance.
- **The entity index is a separate leg, not a document store.** Decisions, action items and open questions from pipeline 6 are looked up directly by name rather than retrieved by similarity, because "what did we decide about onboarding" should hit a decision record, not a passage that happens to contain the word onboarding.

### 5.3 Latency budget

Someone has asked out loud and the room is waiting, often because they intend to read the answer aloud. Streaming matters more here than total time.

| # | Stage | Time |
|---|---|---|
| 1 | Query understanding | 300 ms |
| 2 | Retrieval | 80 ms |
| 3 | Reranking | 300 ms |
| 4 | Generation to the first token | 600 ms |
| 5 | Generation to the last token | 1.8 s |
| 6 | Citation binding and render | 60 ms |

**Total** 3.1 s to a complete answer, 1.3 s to the first word on screen. Budget 6 s at the 95th percentile.

**While waiting the room sees:** the rewritten question echoed back so they can see it was understood, then the answer streaming word by word with citation markers appearing as they are validated

### 5.4 Failure modes

| Failure | What the room sees | Fallback |
|---|---|---|
| The answer genuinely is not in the session | A refusal | This is the correct behaviour, and it has to be enforced in code at S7. A model told to refuse in a prompt will still produce a confident answer some of the time, and mid-meeting that is worse than silence. |
| The answer is in the session but the transcription got the key word wrong, so retrieval finds nothing | A refusal that looks like the discussion never happened | The nastiest failure in this pipeline because it is invisible. Mitigations: fuzzy and phonetic matching in the keyword leg, and always showing the nearest moments even on a refusal so a person can recognise what the machine could not. Worth saying plainly: the quality ceiling of this pipeline is the quality of pipeline 1. |
| Diarisation was wrong, so the answer attributes a statement to the wrong person | "Sanne said X" when Sanne did not | Never attribute unless the speaker label is above threshold. Otherwise "someone said, at 14:32". The citation still lets anyone check. An unattributed correct quote is useful; an attributed wrong one is a problem between colleagues. |
| The answer paraphrases in a way that changes the meaning | A plausible summary that nobody in the room said | Show the quotation next to the paraphrase by default, not behind a click. If there is no quotation, there is no answer. |
| Someone asks a question the tool should not answer: an opinion, a prediction, something about a person | A confident overreach | Scope check at S2. This tool answers questions about what happened in this session. Anything else gets a refusal with that sentence as the reason. |
| The retrieval index is behind because the audio pipeline is queued | An answer that omits the last two minutes, which is often exactly what was asked about | Report the index freshness on the answer card: "answering from the session up to 14:31, two minutes behind". Never answer as if the index is current when it is not. |
| Two plausible and contradictory moments in the transcript | One of them, presented as the answer | Prefer showing both with their timestamps over choosing. A meeting that contradicted itself is a fact about the meeting, and flattening it is a real loss. |

#### Cost drivers

- **Per question, and questions are rare.** Even twenty questions in a session is small next to the audio pipeline.
- **The continuous embedding of transcript windows** is the only always-on cost here, and it is tiny: a few hundred short embeddings per meeting.
- **Reranking doubles the number of calls** for a modest gain on a corpus this small. First thing to cut.
- **Context size in S5** is bounded by design at five spans. Resist the urge to send the whole transcript because it fits: it makes citations worse, not better.

#### What could be cut, in order

- **Reranking.** Go straight from retrieval to generation with the top five.
- **The embedding leg.** Keyword search plus a good query rewrite covers most real questions on a single meeting transcript, and it removes an index to keep fresh.
- **Query understanding.** Require self-contained questions. Noticeably worse to use, since "what did she say about that" is exactly how people ask, but it is a stage and a call removed.
- **The whole pipeline.** The floor is a searchable transcript with a text box, which is not AI at all and still solves a real part of the first of the three seconds. Worth knowing that the non-AI version of this feature is genuinely useful, because it sets the bar the AI version has to beat.

## 6 · Minutes

**6 · Notulation: the rolling minutes loop**

The second continuous pipeline, and the second largest cost in the system, because it runs on a timer whether or not anything is happening. Its central design problem is stated in F2.1: summarising too early flattens a discussion that has not concluded. Almost everything below is arranged around not doing that.

**Functionalities covered (from the flowchart):** F2.1 Rolling minutes, F2.2 Decision extraction, F2.3 Action items and owners, F2.4 Open question tracking, F4.5 Agenda anchoring, F6.3 Citation to source.

Kind tags used in this diagram: **Client** = Client, in the browser; **Server** = Server code, no model; **Model** = A model runs here; **State** = Writes to shared state; **Guardrail** = Guardrail, can stop the pipeline; **Human** = A human decides.

**Diagram: notulation pipeline stage rail.** Nine stages in one chain, S1 to S9, each feeding the next. The rail wraps onto a second row after S5, marked "continues", which is layout only and not a branch. A stage tagged Model is drawn with a dashed outline: a model runs there, so its output is provisional until a person accepts it.

1. **S1 Buffer** (Server). Collect final transcript segments, bounded. No model. Continuous.
2. **S2 Topic boundary** (Server). Long silence, agenda change, lexical shift. No model. 20 ms.
3. **S3 Has it concluded?** (Model). The stage that stops it summarising too early. Model: small LLM. 300 ms.
4. **S4 Update the summary** (Model). Tier A extends, tier B rewrites. Model: LLM. 1.5 to 5 s.
5. **S5 Decisions** (Model). Must quote the sentence, or no record. Model: LLM. Latency shared.
6. **S6 Actions** (Model). Owner only if named or self-committed. Model: LLM. Latency shared.
7. **S7 Open questions** (Model). Add, and crucially, retire when answered. Model: LLM. Latency shared.
8. **S8 Anchor to the agenda** (Server). Or to an explicit off-agenda bucket. Model: similarity. 30 ms.
9. **S9 Emit** (State). Minutes patch, and offer canvas items. No model. 20 ms.

### 6.1 Stage by stage

| # | Stage | Data in | Data out | Model | Target |
|---|---|---|---|---|---|
| S1 | Segment buffer | Final transcript segments from pipeline 1 | A bounded buffer: the current topic block, plus the running summary state capped at about 800 words | None | Continuous |
| S2 | Topic boundary detection | Buffer | A candidate boundary with a confidence | None. Cheap signals: silence over 8 seconds, an agenda item change, a speaker turn that coincides with a sharp lexical shift | 20 ms |
| S3 | Conclusion detection | The current block | Concluded, or still running | A small LLM looking for closing markers, agreement from more than one speaker, and the absence of new claims for about 45 seconds. This stage exists only to protect against the failure named in F2.1 | 300 ms |
| S4 | Summary update | Block plus running state | Updated bullets. Tier A extends the running list every 90 seconds. Tier B rewrites the whole block when it concludes and replaces tier A’s bullets for it | LLM. Two different prompts and two different cadences | 1.5 s for tier A, up to 5 s for tier B |
| S5 | Decision extraction | Concluded block | Zero or more decisions, each carrying the sentence that constitutes it, a timestamp, a confidence, and the alternatives if they were voiced | LLM with a strict schema. No quote means no decision, enforced in code | Shared call with S4 tier B |
| S6 | Action extraction | Concluded block | Zero or more actions: task, owner, due date. Owner is filled only when explicitly named, or when a speaker committed themselves and the speaker label is reliable. Otherwise unassigned, visibly | LLM, same call | Shared |
| S7 | Open question tracking | Block plus the existing open list | Additions, and retirements where later transcript answered an existing question | LLM, same call. The retirement half is the part everyone forgets and F2.4 names as the risk | Shared |
| S8 | Agenda anchoring | Block plus agenda | An agenda item id, or the off-agenda bucket | None. Similarity against agenda item text, with a threshold below which it refuses to assign | 30 ms |
| S9 | Emit | All of the above | A minutes patch on the bus, rendered in the minutes panel, with decisions and actions offered as canvas items the team can place | None | 20 ms |

### 6.2 Two tiers, two cadences

One summarisation loop cannot serve both purposes. A frequent loop keeps the panel alive and produces shallow, churning text. An infrequent loop produces good minutes and a panel that looks broken. So: two.

**Diagram: notulation cadence, frequent tier A ticks and tier B rewrites at topic boundaries.** A timeline drawn as three stacked lanes over the same twelve minutes.

**Lane 1, the transcript:** twelve minutes of it, divided by two boundary lines into three topics, left to right: "topic: onboarding", "topic: the paywall", "topic: next steps".

**Lane 2, tier A, every 90 seconds:** eight evenly spaced tick marks across the full twelve minutes. Caption: "cheap, append only. Notes so far, styled as notes and not as conclusions".

**Lane 3, tier B, on a topic boundary:** three blocks, aligned to the three topics, with arrows dropping from each topic boundary in lane 1 down into lane 3.

1. Block 1, solid: "rewrite block 1, extract decisions and actions".
2. Block 2, solid: "rewrite block 2".
3. Block 3, drawn dashed to mark it as not yet settled: "still running, nothing extracted yet".

Caption: "a full rewrite of the block, and the only place decisions and actions are extracted".

Two notes sit under the diagram:

- "The third block has not concluded, so it has a tier A running note and no decisions. That gap is deliberate: the panel showing nothing decided yet is correct, and a panel that filled it in would be the failure mode F2.1 warns about."
- "90 seconds is a guess. So is 8 seconds of silence as a boundary. Both are written down here so they can be tested rather than defended."

### 6.3 Window sizes, stated as the guesses they are

| Parameter | Proposed value | Why this value | What would change it |
|---|---|---|---|
| Tier A cadence | 90 seconds | Slow enough that the panel is not churning, fast enough that someone glancing at it sees something recent | Count how often people actually glance at the panel. If it is never, the cadence is irrelevant and the tier should go |
| Tier A window | The last 3 minutes of transcript, about 450 words, plus the running state | Enough context to extend a bullet list without re-reading the meeting | If bullets repeat each other, the window is too short and the state summary is doing too little work |
| Tier B window | The whole concluded block, typically 5 to 15 minutes, 800 to 2200 words | A topic is the natural unit of a decision | Blocks over 20 minutes should split on a secondary boundary, or the summary flattens |
| Running state cap | About 800 words | Keeps the per-call cost flat instead of growing with meeting length | If the last hour is being lost, raise the cap or summarise the state itself |
| Silence boundary | 8 seconds | Long enough to be a real pause in a meeting rather than someone thinking | Measure the silence distribution in a real recording before trusting this |
| Conclusion wait | 45 seconds with no new claims | Deliberately conservative, because being late is cheap and being early is not | If the minutes are consistently a topic behind, shorten it and accept more corrections |

### 6.4 Latency budget

Nothing here blocks a person, so the budget is about freshness rather than responsiveness. The number that matters is how far behind the panel is allowed to get before it says so.

| # | Stage | Time |
|---|---|---|
| 1 | Waiting for the topic to conclude | 45 s |
| 2 | Boundary and conclusion checks | 320 ms |
| 3 | Tier B rewrite and extraction | 4 s |
| 4 | Anchoring and emit | 50 ms |

**Total** about 50 s from the real end of a topic to full minutes for it, of which 45 s is a deliberate wait. Tier A is 1.5 s every 90 s.

**While waiting the room sees:** nothing, which is the point. The panel updates quietly. When the pipeline falls more than two minutes behind, it says so on the panel rather than looking current

### 6.5 Failure modes

| Failure | What the room sees | Fallback |
|---|---|---|
| It summarises a discussion that has not finished | The minutes panel confidently states a conclusion the room has not reached, which can actually change what the room decides next | S3 is the defence, and the rule when S3 is unsure is to wait. Late minutes are recoverable, wrong minutes are not, and premature minutes on a shared screen are worse than either because they anchor the discussion. Tier A output is explicitly styled as notes so far rather than conclusions. |
| A decision is invented from a discussion of a decision | A decision record for something nobody agreed | The quote requirement, enforced in code: an extracted decision with no verbatim sentence in the transcript is dropped before it is ever shown. This turns a hallucination into an omission, which is the trade to want. |
| An owner is invented for an action item | Someone finds out in the export that they own something | Owner stays empty unless it was named or self-committed with a reliable speaker label. F2.3 says it directly: inventing an owner is worse than leaving it blank. An unassigned action is a prompt to the room; a wrongly assigned one is a small betrayal. |
| Summary drift over two hours: tier A extends an append-only list that slowly accumulates errors | Minutes that are subtly wrong in a way nobody can point at | Tier B rewriting on every topic boundary is the reset. If two hours pass with no boundary detected, force a full re-summarisation on a timer, and treat the absence of boundaries as its own signal that something is wrong. |
| The open question list grows to forty items | Noise that nobody reads, which is the failure F2.4 names | Retirement in S7, plus a cap: show the ten most recent and most referenced, with the rest behind a count. A list nobody reads is the same as no list, at full cost. |
| Agenda anchoring forces a fit onto a meeting that has drifted | Structure imposed on a discussion that did not have it | An explicit off-agenda bucket and a similarity threshold. Drift is information about the meeting. Recording it as drift is more useful than filing it under the wrong heading. |
| The model is slow or unavailable for ten minutes | A stale minutes panel | This pipeline is not user-blocking, so it queues. The panel shows how far behind it is rather than looking current. When it catches up, it runs tier B over the whole gap rather than replaying every tier A tick. |

#### Cost drivers

- **It runs on a timer for the whole meeting.** Ninety minutes at one tier A tick every 90 seconds is 60 calls, plus roughly 8 to 12 tier B calls. This is the second largest running cost after ASR, and unlike ASR it is entirely within the design’s control.
- **Context growth is the trap.** Resending a growing transcript makes the last call of a long meeting cost many times the first. Capping the running state at a fixed size keeps the per-call cost flat, and that single decision is worth more than any prompt tuning.
- **Tier B calls are large but rare.** They are the good value in this pipeline.
- **S1, S2, S8 and S9 need no model at all.**

#### What could be cut, in order

- **Tier A entirely.** Summarise only at topic boundaries. The panel updates every five or ten minutes instead of every ninety seconds, the minutes get better, and the cost falls by roughly two thirds. This is a strong candidate for the default rather than the fallback.
- **Open question tracking.** The retirement logic is most of the work and the list is the least read part of the panel.
- **Agenda anchoring.** Most meetings drift and the bucket ends up doing the work anyway.
- **Live minutes altogether.** The floor is one summarisation pass at the end of the meeting, which is what every existing tool does. That is worth naming clearly, because the during-the-meeting claim is the whole differentiator: if the rolling panel is cut, Jarvaids is an after-the-meeting product wearing a canvas.

## 7 · Export

**7 · Export: getting it out of the tool**

The least interesting pipeline and the one most likely to be the thing that makes people use the tool again, because it is the visible proof that the meeting produced something. There is no model in it anywhere. The only real design work is in two prompts to the human, about unaccepted items and about names, and both of them are about what leaves the room.

**Functionalities covered (from the flowchart):** F5.1 Canvas export, F5.2 Minutes export, F5.3 Board integration, F6.3 Citation to source, F6.6 Retention and deletion.

Kind tags used in this diagram: **Client** = Client, in the browser; **Server** = Server code, no model; **Model** = A model runs here; **State** = Writes to shared state; **Guardrail** = Guardrail, can stop the pipeline; **Human** = A human decides.

**Diagram: export pipeline stage rail.** Eight stages in one chain, S1 to S8, each feeding the next. The rail wraps onto a second row after S4, marked "continues", which is layout only and not a branch. No stage in this rail runs a model.

1. **S1 Freeze** (Server). Snapshot the canvas at one version. No model. 50 ms.
2. **S2 Resolve provisional** (Human). Include, exclude, or keep them marked. No model. Human time.
3. **S3 Choose anonymity** (Guardrail). Names, initials, or role labels. No model. Human time.
4. **S4 Render PNG** (Server). The same renderer, headless, at 2x. No model. 2 to 6 s.
5. **S5 Build PDF** (Server). Vector canvas, then the minutes pages. No model. 1 to 3 s.
6. **S6 Write minutes** (Server). Markdown, every claim with its timestamp. No model. 200 ms.
7. **S7 Push to a board** (Server). Miro or FigJam, with an id map kept. No model. 20 to 90 s.
8. **S8 Deliver** (State). Download or link, and an audit record. No model. 100 ms.

### 7.1 Stage by stage

| # | Stage | Data in | Data out | Model | Target |
|---|---|---|---|---|---|
| S1 | Freeze | Live canvas model | An immutable snapshot at a version number. Everything downstream reads the snapshot, so a late edit cannot half-appear in an export | None | 50 ms |
| S2 | Resolve provisional items | Snapshot | A decision about the items nobody accepted: include them, exclude them, or include them still visibly marked as machine-made. Default is the third | None. And it must be a question, because silently promoting unaccepted AI output to finished work breaks the promise F3.5 makes | Human time |
| S3 | Anonymisation choice | Snapshot plus speaker labels | Real names, initials, or role labels throughout the export | None. This belongs at export and not only at retention, because the export is the thing that leaves the room | Human time |
| S4 | Canvas to PNG | Snapshot | A raster image at 2x, tiled if the canvas is larger than a sensible single image | None. Either the same renderer in a headless browser, which is consistent and needs a browser in the deployment, or serialising the client scene graph, which is free and fiddly about fonts | 2 to 6 s |
| S5 | PDF | Snapshot plus minutes | Page one the canvas as vector where possible, then the minutes, then an appendix of source photographs | None | 1 to 3 s |
| S6 | Minutes to text | Minutes state from pipeline 6 | Markdown: decisions, actions, open questions, each with a timestamp that links back into the transcript, and attribution only where confidence allowed it | None | 200 ms |
| S7 | Board push | Snapshot | Items created on a Miro or FigJam board, with a stored id map so a second push updates instead of duplicating | None. Rate-limit aware, resumable | 20 to 90 s for 100 items |
| S8 | Deliver | Artefacts | Files, or a link, plus an append-only audit record of who exported what, when, and under which retention policy | None | 100 ms |

### 7.2 Latency budget

The meeting is over, so nobody is blocked in the way they are during a session. The thing to avoid is a silent spinner after the room has emptied, because that is when people close the tab and the whole session is lost to them.

| # | Stage | Time |
|---|---|---|
| 1 | Freeze and prompts | 300 ms |
| 2 | PNG render | 3.5 s |
| 3 | PDF assembly | 1.8 s |
| 4 | Minutes to Markdown | 200 ms |
| 5 | Delivery | 200 ms |

**Total** about 6 s for PNG, PDF and minutes together. A board push adds 20 to 90 s and is shown as its own progress list.

**While waiting the room sees:** a per-artefact progress list, each line ticking off as it finishes, so a slow board push does not make the finished PNG look stuck behind it

### 7.3 Failure modes

| Failure | What the room sees | Fallback |
|---|---|---|
| Headless rendering produces a different picture from the screen: missing fonts, clipped edges | An export that does not look like what the meeting saw | Pin the fonts into the render environment and make a pixel comparison against the client render part of the build checks. If it cannot be made reliable, serialise from the client instead and accept the fiddliness. |
| The canvas is far larger than any sensible page | Either an unreadable thumbnail or a two hundred megabyte file | Offer both: fit to page, and tiled at readable scale. Show the page count before rendering. Never silently choose. |
| The Miro or FigJam API rate limits, or authorisation expires halfway through a push | Half a board, and a second attempt that duplicates the first half | The id map makes the push resumable and idempotent. Never retry a push without it. F5.3 already flags that this integration may cost more than it is worth, and the honest way to find out is to spend one day against the real API before committing. |
| The export contains something the room did not intend: a photograph of a laptop screen, a name someone wanted left out | Data leaving the room that cannot be recalled | S2 and S3 are the only guards, and they have to be before the file exists, not after. An export cannot be withdrawn. This is the stage where the retention policy stops being a promise and becomes a fact. |
| Someone exports mid-meeting and treats it as final | A partial record circulating as the minutes | Stamp the export with the session time it was taken at and whether the session was still running. Cheap, and it stops a draft being mistaken for a record. |
| The minutes are exported while pipeline 6 is still behind | Minutes missing the last ten minutes, which is usually where the decisions are | Block the export on a catch-up, or stamp the export with how far the minutes reached. Never export a summary that silently stops early. |

#### Cost drivers

- **No model calls at all,** unless a one-off end-of-meeting summarisation is added, which properly belongs to pipeline 6.
- **A headless browser in the deployment** is the real cost: memory, cold starts, and a second rendering path to keep in step with the first.
- **Board integration is engineering time, not runtime cost.** Estimate it against the real API before committing, as F5.3 says.
- **Storage** of exported artefacts, bounded by the retention policy in pipeline 8.

#### What could be cut, in order

- **The board push.** Highest effort, most external dependency, least certain value. Concept 001 makes board write-back part of the core, so cutting it is a concept-level decision rather than a technical one, and it should be made against a day of real API work and not against a guess.
- **PDF.** PNG plus a Markdown file covers most of what people do with this.
- **Server-side rendering.** A client-side export of the visible canvas is a fraction of the work.
- **Nothing below that.** PNG plus Markdown is the floor and it should be built in the first week, because it is what makes every test session produce an artefact worth looking at.

## 8 · Retention

**8 · Retention and deletion**

The only pipeline on this page with nothing to cut. The course restricts recording people, concept 001 calls this a hard gate, and the gate is real: if this is not built and working, Jarvaids cannot be tested with a real team at all and the evaluation falls back to synthetic material, which weakens every claim the project makes. It is also, unlike the rest of this document, mostly unglamorous plumbing across five different stores.

**Functionalities covered (from the flowchart):** F6.1 Consent gate, F6.2 Local processing, F6.5 Correction capture, F6.6 Retention and deletion.

Kind tags used in this diagram: **Client** = Client, in the browser; **Server** = Server code, no model; **Model** = A model runs here; **State** = Writes to shared state; **Guardrail** = Guardrail, can stop the pipeline; **Human** = A human decides.

**Diagram: retention and deletion pipeline stage rail.** Eight stages in one chain, S1 to S8, each feeding the next. The rail wraps onto a second row after S4, marked "continues", which is layout only and not a branch. A stage tagged Model is drawn with a dashed outline: a model runs there, so its output is provisional until a person accepts it.

1. **S1 Set the policy** (Guardrail). At consent time, as data the stores read. No model. Once.
2. **S2 Tier the stores** (Server). Five tiers, five different lifetimes. No model. Continuous.
3. **S3 Stop on request** (Guardrail). Anyone can halt it, mid-sentence. No model. Under 1 s.
4. **S4 Close the session** (Guardrail). Audio deleted by a job, never by a person. No model. Under 60 s.
5. **S5 Sweep** (Server). Catch sessions that crashed and never closed. No model. Hourly.
6. **S6 Anonymise** (Model). Pseudonyms, then a human review pass. Model: NER, then human. Minutes.
7. **S7 Release the evidence** (Server). Corrections log out, identifiers left behind. No model. Once.
8. **S8 Delete on request** (Guardrail). Everything goes, a tombstone stays. No model. Under 24 h.

### 8.1 Stage by stage

| # | Stage | Data in | Data out | Model | Target |
|---|---|---|---|---|---|
| S1 | Policy at consent | The consent round | A policy record: audio retention, transcript retention, whether image originals are kept, who may export, and for how long. Stored as data that every store reads, not as a setting somebody remembers | None | Once, before capture |
| S2 | Tiered storage | Everything the system produces | Five tiers with different lifetimes: audio chunks, image originals, identified transcript, anonymised transcript, canvas and minutes. Each tier carries its own expiry | None | Continuous |
| S3 | Revocation mid-session | Anyone saying stop, or pressing stop | Capture halted at the microphone, in-flight buffers discarded, a visible confirmation on the shared screen | None | Under 1 second, and it must be visibly instant |
| S4 | Session close | Session end | Audio deleted, by the close job. Not by a human, and not by a button someone has to remember | None | Within 60 seconds of close, with a visible confirmation to whoever is still there |
| S5 | Orphan sweep | All sessions | Sessions that crashed or were abandoned without closing get the same treatment on a timer. This is the real failure mode: not a delete that fails, a close that never happens | None | Hourly |
| S6 | Anonymisation | Identified transcript | Speaker names replaced with stable pseudonyms, personal names in the body flagged, roles kept. Then a human review pass before the file is allowed to leave evidence/raw/ | Named entity recognition, and then a person. Automatic scrubbing of a meeting transcript misses things and pretending otherwise is the risk | Minutes, including the human part |
| S7 | Evidence release | Correction log and anonymised transcript | What a human changed about machine output, anonymised, which is the measurement data F6.5 exists to produce | None | Once per session |
| S8 | Delete on request | A request | Canvas, transcript, images and the id map removed. A tombstone record remains saying a session existed and was deleted, because an audit trail with holes in it is not an audit trail | None | Within 24 hours |

### 8.2 The five tiers, and when each one dies

| Tier | Contains | Lives for | Leaves the session? |
|---|---|---|---|
| Audio chunks | Raw room sound | Until the session closes, and at most 60 minutes if it does not | Never. It never reaches a third party and never reaches the repository |
| Image originals | Photographs of walls, sketches and sometimes screens | 7 days by default, so a bad reading can still be corrected against the picture, and longer only if the team asks | Only inside an export, and only if the team includes them |
| Identified transcript | Text with real speaker names | Session plus 7 days, in evidence/raw/, which is gitignored | Never, in that form |
| Anonymised transcript | Text with stable pseudonyms | Project lifetime | Yes, after a human review pass. This is the only text tier that may |
| Canvas, minutes, correction log | The work, and what humans changed about machine output | Project lifetime | Yes. The correction log is the evaluation evidence F6.5 exists to produce |

### 8.3 Timing

Deletion is not a live operation, but two of its timings are user-facing and both matter more than their size suggests.

| # | Stage | Time |
|---|---|---|
| 1 | Stop request to the microphone actually stopping | 800 ms |
| 2 | Session close to audio deleted | 60 s |
| 3 | Sweep interval for orphaned sessions | 3600 s |

**Total** stop is under a second and visible. Audio is gone within a minute of close, or within an hour if the session never closed properly.

**While waiting the room sees:** a recording indicator that cannot be hidden while it runs, and an explicit "audio deleted" confirmation when it stops. A promise nobody can see being kept is not a promise

### 8.4 Failure modes

| Failure | What the room sees | Fallback |
|---|---|---|
| A session crashes and never closes, so its audio is never deleted | Nothing, which is precisely the problem | The hourly sweep, keyed on the policy expiry and not on a close event. Deletion must never depend on the happy path running to the end. |
| Backups keep what the delete removed | Nothing, until somebody asks the awkward question | Pick one and write it down: either the raw tiers are excluded from backup entirely, or the backup retention is shorter than the shortest tier. There is no third option that keeps the promise made in the consent round. |
| Automatic anonymisation misses a name in the body of the transcript | A name in a file that was promised not to contain one | A human review pass before release, and the file stays in the gitignored folder until that pass happens. Be honest in the write-up: this is partly a process control, not a technical one, and processes get skipped under deadline. |
| Someone withdraws consent after the meeting, when their contributions are already on the canvas and in the minutes | An unresolved question | Genuinely unresolved in this design. Removing one speaker from a transcript makes the rest incoherent, and removing their canvas items removes work the team did together. The options are: delete the whole session, or anonymise that speaker retrospectively and keep the content. This needs an answer from the teaching team before the first recorded session, not after it. |
| An export has already left the room when a deletion is requested | Nothing can be done about that copy | The guard has to be before the export, at S2 and S3 of pipeline 7. Say so in the consent round rather than implying that deletion reaches everywhere, because it does not. |
| The retention promise is made in the interface and not implemented in the stores | A tool that lies | Every store reads the policy record. The test for this is deliberately blunt: run a session, close it, and grep the disk for the audio. If it is there, the feature does not exist, whatever the screen says. |

#### Cost drivers

- **Almost no runtime cost.** Storage for a few tiers and a periodic job.
- **The engineering cost is larger than it looks:** expiry plumbing across five stores, a sweep, an audit log, and a delete path that actually reaches everything. Budget days, not hours.
- **The human review pass in S6 is the ongoing cost,** and it is a person’s time per session.

#### What could be cut

- **Nothing.** This is the gate.
- The only defensible reduction is to reduce what is captured in the first place. Push-to-talk capture, with no continuous recording, removes most of this pipeline by removing most of the data. That is a real option and it is worth pricing against the features it costs, rather than treating continuous recording as a given.
- If the schedule slips and something has to give, the correct thing to give is a feature elsewhere, not a tier here.

## X · Event bus

**Cross-cutting: the event bus, ordering, idempotency and replay**

Every pipeline above reads from and writes to one ordered log per session. Nothing calls anything else directly. That costs a layer of indirection and buys three things the project actually needs: reconnection without special cases, an explanation for every action after the fact, and the ability to re-run a whole session offline against a different model, which is how the evaluation gets done without recording more people.

**Functionalities covered (from the flowchart):** F4.1 Create and join, F4.2 Live multi-user view, F6.3 Citation to source, F6.4 Degradation behaviour, F6.5 Correction capture.

**Diagram: the event bus, producers append to one ordered log, consumers read from it, the canvas is a fold over it.** Three lanes stacked top to bottom: producers, the log, consumers.

**Lane 1, producers.** Six boxes in a row, each with an arrow running down into the log.

1. **audio pipeline** (Pipeline).
2. **image pipeline** (Pipeline).
3. **command pipeline** (Pipeline).
4. **human edits** (Human).
5. **consent and stop** (Guardrail).
6. **agent outputs** (Model).

**Lane 2, the log** (State): "One ordered, append-only log per session." Inside it, six sample entries in sequence order, left to right, then a note:

1. seq 118, transcript.final
2. seq 119, image.uploaded
3. seq 120, command.accepted
4. seq 121, canvas.patch
5. seq 122, human.moved
6. seq 123, minutes.patch
7. Note: "seq assigned server side, never by the producer"

Four arrows run down from the log into the consumers.

**Lane 3, consumers.** Four boxes in a row.

1. canvas model, a fold over every patch so far.
2. notulator, reads transcript events on its own clock.
3. retrieval index, embeds rolling windows.
4. connected screens, catching up from a seq.

**Underneath, one box spanning the full width** (Server): "Two clocks, and confusing them is a real bug. Every consumer is independently idempotent. Media time, milliseconds from session start, is what citations and transcripts order by. Sequence number is what canvas mutations order by."

### X.1 What every event carries

| Field | What it is | Why it is there |
|---|---|---|
| event_id | A UUID minted by the producer | Deduplication, and something to point at in a bug report |
| session_id | Which meeting | Every query, every store and every delete is scoped by it |
| seq | A monotonic integer per session, assigned by the bus and never by the producer | Total order for anything that mutates canvas state. Clients reconnect by asking for everything after a seq |
| media_time_ms | Milliseconds from session start | The clock for citations and transcripts. Every participant’s wall clock is wrong, and this one is not |
| producer | Which pipeline and which model version | You cannot compare two sessions run on different model versions unless the events say which was which |
| causation_id | The event this one was caused by | Turns "why did it build that timeline" into a chain that can be read: command, referents, structure, patch |
| idempotency_key | A deterministic hash of the meaningful content | The defence against a repeated command creating two timelines, and against a retried upload creating two walls of notes |
| confidence | Where the producer has one | Consumers downstream need to know how much to trust an input, and a missing confidence is treated as low, not as high |

### X.2 Ordering

- **Total order per session, assigned server side.** Producers do not number their own events, because six pipelines on different machines cannot agree on a counter.
- **Two clocks, deliberately.** Canvas mutations order by sequence number, because what matters is what happened after what. Transcripts and citations order by media time, because what matters is when it was said. A photograph that uploads slowly arrives late in sequence and belongs early in media time, and both facts are correct.
- **Canvas patches carry the version they expect.** A patch against a stale version is rebased if it can be, and rejected if it cannot. It is never applied blindly, because that is how an AI block lands on top of work a human just moved, which is the one thing F3.4 says must never happen.

### X.3 Idempotency

Delivery is at least once, so every consumer must tolerate seeing the same event twice. Saying this out loud matters, because the alternative is discovering it during a live session. The keys:

- **Audio chunks:** a hash of the bytes plus the start time. A retried upload after a network wobble does not produce a doubled sentence.
- **Commands:** normalised text, plus speaker, plus an 8 second window. This is what stops the room getting two timelines because somebody repeated themselves when nothing happened fast enough.
- **Photographs:** a hash of the image bytes. The same wall photographed twice on purpose is a different image and should produce a second block; the same upload retried is not.
- **Canvas patches:** the patch id, plus the expected version.

### X.4 Replay, and why it is the evaluation strategy

The canvas at any moment is a fold over the log. That gives four things:

- **Reconnection is not a special case.** A screen that drops off asks for everything after the last sequence number it saw, which is most of what F4.1 and F4.2 need: a session is a link, and a link that reconnects cleanly is a session that survives a phone going to sleep.
- **"Why did it do that" is answerable** by following causation ids back from the patch to the utterance.
- **A recorded session can be re-run offline** against a different model, a different chunk size or a different confidence threshold, and the outputs compared. This is the cheapest evaluation instrument the project has, and it only exists if the log is complete from the start. Retrofitting it later means re-recording people.
- **The correction log is a view over the same stream,** so F6.5 comes almost free: a human edit that follows an AI patch on the same items is a correction, and it can be counted without anyone building a separate feature for it.

### X.5 Backpressure, and what gets dropped

Every pipeline gets a bounded queue and a stated drop policy, because an unbounded queue is a way of failing later and less legibly.

| Pipeline | Queue behaviour | What the room sees |
|---|---|---|
| Audio | Never drops. It queues, and it drops model tier instead | A badge showing how far behind transcription is, and which tier it is running |
| Image | Queues. Uploads retry | Upload progress on the shared canvas, not just on the phone |
| Command | Serialises. Duplicates within the window collapse | Queued commands shown in order, not silently interleaved |
| Visualisation | Supersedes. A newer request for the same items cancels the older one | The ghost frame updates rather than two blocks appearing |
| Notulation | Coalesces. Ten skipped ticks become one larger summarisation | How far behind the minutes are |
| Question answering | Rejects when overloaded rather than queueing, because a stale answer to a live question is worthless | A refusal with a reason, immediately |

> **The honest counter-argument**
>
> A course prototype does not need an event bus. Direct calls between five modules would work, ship faster, and be easier for five people to understand. The reason to build the log anyway is narrow and specific: without it there is no replay, and without replay the only way to evaluate a change is to record another meeting with real people, which is the most expensive and most restricted thing this project can do. If the team decides not to build the bus, the thing to preserve is the append-only log of inputs and outputs, even as a file. That is the part that is doing the work.
>

## ? · Unknowns

**What we do not know yet**

Everything on this page is a proposal, and proposals in a document look more settled than they are. This section lists the assumptions that would change the design if they turned out false, with a test for each that costs an afternoon or less. The thresholds are the important column: agreeing a number before running a test is what stops the result being interpreted into a success afterwards.

| Assumption | Why it matters | Cheap test | Threshold, agreed before the test |
|---|---|---|---|
| Live transcription is accurate enough in a real room with one laptop microphone | Pipelines 3, 5 and 6 all sit on top of it. If the transcript is poor, everything above it is confidently wrong | Record 10 minutes of a real session. Hand-correct three two-minute samples and count word error rate. Half a day | Under 15 percent word error rate overall, and under 10 percent on names, decisions and jargon. Over 25 percent and the concept has to change shape |
| Handwriting on photographed sticky notes can be read well enough to be worth correcting | Concept 001 already names this as the riskiest assumption in the project | Photograph a real wall ten times from real angles and lighting. Run it through two or three vision models. Count separately: notes correctly separated, and notes correctly read | 80 percent on both, measured separately. Separation below 80 is fatal, reading below 80 is survivable because the crop is still there |
| Speaker separation works well enough for "what did she say" to be answerable | It is one of the three seconds the whole concept is aimed at | Hand-label ten minutes of a real recording and compare | Diarisation error rate under 20 percent with overlap included. Above that, the tool stops using names entirely and says "someone" |
| Anyone will actually address the tool mid-meeting | If nobody does, pipeline 3 is the wrong core and the effort belongs in pipelines 2 and 6 | Sit in on two real sessions with a wizard-of-oz button. Count how many times someone would have pressed it. No code at all | Fewer than three in an hour means the command pipeline is not the core, whatever the demo looks like |
| Referent resolution can work often enough to feel like magic rather than like an interrogation | It is the single hardest unsolved piece in the design, see pipeline 3 | Build 30 referent cases by hand from one real transcript and canvas state. Score resolution by hand. An afternoon | 80 percent. Below that, confirmation-always is the only safe mode, and the interaction needs redesigning around selection instead of speech |
| An automatically chosen form beats a plain list | It is the whole claim that Jarvaids is not a notes app | On paper: show two teams the same twelve items as an automatic cluster, as a timeline, and as a list. Ask which they would keep and why. No code | Agree in advance what a win looks like. If the list wins, that is the finding and it is worth more than a working demo |
| Anyone reads the rolling minutes panel during the meeting | Pipeline 6 is the second largest running cost in the system and it exists for this panel | Observe one session and count glances per ten minutes | If it is near zero, cut tier A and summarise at the end. Decide the number before watching, not after |
| The room will wait for a response before repeating themselves | It sets the latency budget for pipelines 3 and 4, which currently assume about two seconds | Stopwatch and a confederate pretending to be the tool. Time how long before someone repeats the command | Guessed at 2 seconds. If it is really 1.2, the budgets in pipelines 3 and 4 do not hold and the interaction needs a faster acknowledgement |
| The cost per meeting is acceptable | It decides which cuts happen, and it decides whether the tool could exist outside a course project | Estimate from the cost sections here, then instrument one real session and compare estimate to actual | Agree a number per 90 minute meeting before measuring. If the real figure is several times the estimate, find out which stage before changing anything |
| A real team will agree to be recorded | Everything in the evaluation depends on it. Without it the project runs on synthetic material and every claim is weaker | Ask three teams, before building anything | Two of three saying yes is enough to proceed. Zero means the push-to-talk-only variant becomes the plan, not the fallback |
| Progressive reveal in the image pipeline is worth the extra engineering | It is a real amount of front-end work for something that changes perception rather than outcome | A click-through prototype with two timings. Ten people, five minutes each | Agree what a meaningful preference is. A small preference does not justify the work |
| People will accept or reject provisional items rather than ignoring them | The entire trust model in F3.5 assumes provisional means temporary. If nobody clears them, the canvas fills with dashed ghosts and the distinction stops meaning anything | One session. Count accepted, rejected and still-provisional-at-the-end | If more than half are still provisional at the end, the model is wrong and provisional items need to expire or to be gathered somewhere rather than sitting on the board |

### U.1 Numbers in this document that are guesses

Stated plainly so they can be argued with. None of these came from a measurement:

- **400 ms** of trailing silence as an endpoint, and **12 s** as a hard cut.
- **8 s** windows with **1.5 s** overlap in the fixed-window option.
- **0.85 and 0.55** as the confidence band edges in the command gate.
- **8 s** as the duplicate-command window.
- **60 items** as the visualisation cap.
- **60 percent** of items carrying a date as the timeline rule.
- **90 s** tier A cadence, **45 s** conclusion wait, **8 s** silence boundary, **800 words** of running state.
- **30 s** retrieval windows with **10 s** overlap, and **12 then 5** candidates.
- **7 days** for image originals, **60 s** for audio deletion after close.
- **2048 px** long edge for uploaded photographs.

Every one of them is cheap to vary once the event log exists, because a recorded session can be replayed against a different value without recording anyone again. That is the main practical reason the bus is worth building.

### U.2 Things this document does not answer

- **Who may command the tool.** F4.3 is still open. Anyone is chaos, only the facilitator is a bottleneck, and pipeline 3 has a permission stage waiting for the answer.
- **Whether it volunteers suggestions.** F2.8 and F4.4. No pipeline here implements proactive suggestion, deliberately, because the anchoring risk in concept 001 has not been tested. Adding it later means a new trigger into pipeline 4 and nothing else, so leaving it out is cheap and reversible.
- **What happens when a participant withdraws consent after the session,** when their words are already in the minutes and their ideas are already on the canvas. Named in pipeline 8 as unresolved. It needs an answer from the teaching team before the first recorded session.
- **Which of the three products this is.** The cut lists in each section are written so that this can be decided late, but it still has to be decided, and the flowchart already says the notes and concept 001 do not agree on where the core is.

> **The three weakest points in the design, named** (flagged as a warning in the source)
>
> - **Everything sits on one microphone.** Pipelines 3, 5 and 6 are all downstream of pipeline 1, and pipeline 1 is one laptop in a room of eight people who talk over each other in two languages. A poor transcript does not produce visible errors, it produces plausible ones, and there is no stage anywhere below that can detect an error made above it. The design mitigates this with confidence flags and citations, and mitigation is not the same as a fix.
> - **Referent resolution has no good fallback.** "Those three" is the natural way to speak and the hardest thing in this system to resolve. The only safe behaviour is to ask, and asking repeatedly makes a tool that is behaving correctly feel broken. Every other hard stage here degrades into something useful; this one degrades into an interrogation.
> - **Provisional styling is doing more work than it can carry.** F3.5 is called the strongest trust mechanism in the tool, and the whole design leans on it: false accepts are fine because they are provisional, wrong layouts are fine because they are provisional, wrong readings are fine because they are provisional. That only holds while provisional means temporary. If a canvas ends a meeting with forty dashed items nobody cleared, the distinction has quietly stopped meaning anything and every failure it was absorbing is back. Nobody has tested whether people clear them.
>

---

- Jarvaids: data pipelines
- Read with the flowchart, the F-numbers match
- Print or save as PDF, every section prints
