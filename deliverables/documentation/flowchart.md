# During-meeting AI assistant: flowchart and functionalities

**What this is:** the working map of Jarvaids, a during-meeting AI assistant: the journey a design team goes through, the system underneath it, and every functionality broken out and numbered (F1.1 to F6.6) so work can be divided.
**Generated from:** `deliverables/documentation/flowchart.html`, which is the rendered version of this same content.
**Diagrams:** the two diagrams in the HTML are inline SVG. They are transcribed here as text. Open the HTML if you want to see them drawn.

GenAI course · ideation 001 · Jarvaids

A during-meeting tool that takes the minutes and organises the meeting *visually*, with voice and photographs as input, onto a shared canvas. This file is the working map of what the thing does: the journey the team goes through, the system underneath it, and every functionality broken out so work can be divided.

- **Source:** whiteboard notes 1 & 2, concept ideation/concepts/001
- **Form factor:** website, not an app
- **Status:** draft for team review
- **Offline:** single file, no internet needed

**Companion file:** `deliverables/documentation/pipelines.md` takes the F-numbers defined in section 3 below and says how each one would actually run, stage by stage, with models, latency budgets, failure modes and costs.

## Expandable sticky-note overview, planned

The overview shows main points as collapsed sticky notes. Open a note in place
to inspect supporting detail and session sources, then collapse it to resume
scanning. AI groups, orders and connects notes by meaning; team adjustments
take priority. Expansion changes local spacing, not saved positions or review
state. Provisional content and relationships stay visibly provisional.

Each main topic, subject or choice can have a distinct sticky-note colour. Notes in the same group share it, with visible group labels and an overview key. AI assignments are provisional and team-adjustable; colours stay consistent as notes expand or new content arrives. Topic fills never replace provenance boundaries or review labels.

F3.8 adds this behaviour to the product vision. The existing capture-first
milestone remains distinct. See [the interaction contract](../../app/design-system/spec/expandable-notes.md)
for review, accessibility, collision and future data requirements.

## How to read the diagrams

Every box is white, with what kind of thing it is written on its top edge as a tag. Three of those kinds also carry a colour: a person acting, a model running, and a hard limit nothing may cross. The colour is only there to let you find them across the whole drawing; the tag says the same thing in words, so nothing is lost without it. The dashed edge is unchanged and still means a model runs here, so what comes out of it is provisional until a person accepts it.

The diagrams in this file have been transcribed to text. Each one is given as a list of boxes with their kind tag, their description, and, where the source shows them, the model tag and the latency figure, followed by the connections between the boxes with their direction and any label on the connector. Purely visual scaffolding (band rectangles, wrap-around rails, arrow geometry) is described only where it carries meaning.

Two encodings from the drawing are worth stating here, because they are the ones that carry meaning rather than decoration. **A dashed outline on a box means a model runs at that stage, so its output is provisional until a person accepts it.** That is the central rule of the product and it is repeated in the text of every diagram below. The colour carried by the Human, Model and Guardrail boxes is not reproduced, because the source says the tag on the box says the same thing in words, so nothing is lost without it.

## 1 · User journey

**What the team actually does**

The whole point sits in the middle band. Similar programs work *after* the meeting; this one works *during* it, which means the loop repeats continuously while people are talking, and the canvas is already finished when the meeting ends.

Kind tags used in this diagram: **Step** = A step the team takes; **Input** = Input from the room; **Model** = AI does the work; **Canvas** = Shared canvas; **State** = Stored state; **Human** = Human stays in control; **Guardrail** = A hard limit nothing crosses.

**Diagram: user journey, before, during and after the meeting.** Three bands stacked top to bottom, with the flow running Before, then During, then After. Kind tags are given in brackets. A box drawn with a dashed outline is a Model box: a model runs there, so what leaves it is provisional until a person accepts it.

**Band 1, before the meeting.** Four boxes in a row, each feeding the next: 1 to 2 to 3 to 4.

1. **1 · Create session** (Step). Open the website. No install, no account for guests. Get a join link.
2. **2 · Consent round** (Guardrail). Everyone in the room agrees out loud. Logged. Nothing is captured before this.
3. **3 · Choose the canvas** (Step). Blank, or a starting layout: cluster, timeline, matrix, flow. Drop in the agenda.
4. **4 · Team joins** (Step). Canvas on the shared screen, link on everyone's phone for taking photographs.

The band then feeds down into band 2.

**Band 2, during the meeting: this loop runs continuously.**

Input from the room, four boxes stacked on the left:

1. **Speech** (Input). Everything anyone says.
2. **Photographs** (Input). Sticky walls, sketches, screens.
3. **Spoken commands** (Input). "Put those three on a timeline."
4. **Typed notes and questions** (Input). For whoever does not want to talk.

All four feed rightwards into the AI layer. The arrows land on the boundary of the AI layer as a whole, at staggered heights, rather than on any one agent.

The AI layer, labelled "AI layer: three agents, one orchestrator", is drawn as a dashed enclosure around three Model boxes:

1. **Agent 1 · Notulator** (Model). Keeps the running record: what was said, decided, left open.
2. **Agent 2 · Command interpreter** (Model). Spots that something was asked of it, and what exactly.
3. **Agent 3 · Visualiser** (Model). Turns content into a layout. Not text in a box: a visual conclusion, placed right away.

Below the AI layer:

- **Session state** (State). Transcript, people, decisions, open questions, and the canvas itself. Two arrows run between the AI layer and session state, one down and one up: the AI layer writes to it and reads back from it.

To the right of the AI layer:

- **The live visual canvas** (Canvas). Main points appear as expandable sticky notes while the session runs. Open a note for detail and sources; AI output stays provisional until reviewed. An arrow runs from the AI layer into this box.

  Inside the canvas box, four sample items sit in a row, each feeding the next left to right, showing how one turns into the next:
  1. "note from the wall", drawn solid.
  2. "what was said", drawn solid.
  3. "grouped by the AI", drawn dashed.
  4. "laid out as a timeline, waiting to be accepted", drawn dashed.

  Three captions sit inside the canvas box: "solid = made by the team · dashed = made by the AI, not accepted yet", "clusters, timelines, matrices, flows: laid out, not just listed", and "sticky notes: topic colours and labels, expand for detail and sources".

- **Accept, edit, reject, move** (Human). Nothing the AI made becomes the team's work until someone says so. An arrow runs down into it from the canvas, and a dashed arrow runs from it back into the AI layer.
- **Ask it something, mid-meeting** (Human). "What did Sanne say about the paywall?" It answers live, and cites the moment it came from so the answer can be checked. An arrow runs leftwards from this box into the AI layer, and a line runs down from it into the feedback loop below.

A long dashed arrow loops from the bottom of the during band back up into the AI layer, labelled: "corrections teach the session, and the loop runs again, every few seconds, all meeting long".

A note sits under the band: "Open question from the notes: does it volunteer suggestions, or only answer when asked? Drawn here as answer-on-request, with a facilitator toggle for proactive suggestions, so the anchoring risk stays something the team can test rather than assume."

The band then feeds down into band 3.

**Band 3, after the meeting.** Four boxes in a row, each feeding the next: 5 to 6 to 7 to 8.

5. **5 · It is already done** (Canvas). No one photographs the wall and retypes it. The canvas is the minutes.
6. **6 · Export** (Step). PNG, PDF, or push into Miro or FigJam so it lands where the team already works.
7. **7 · Searchable record** (Step). Transcript, decisions and actions with timestamps, linked to canvas items.
8. **8 · Audio deleted** (Guardrail). Retention agreed up front. Transcript anonymised before it leaves the session.

> **The three seconds this is designed for**
>
> - **“What did she say about that, twenty minutes ago?”** and nobody can find it.
> - **The wall is full and someone has to photograph and retype it,** which takes an hour or does not happen.
> - **The meeting ends and the board is a graveyard:** the artefacts survive, the reasoning does not.
>

## 2 · System architecture

**What sits underneath it**

Read top to bottom: the browser captures, the server turns raw input into events, the orchestrator decides what each event means and who handles it, three agents do the specialised work, and everything lands in shared state that streams straight back to the canvas. The bottom band is not a stage, it applies to every stage above it.

Kind tags used in this diagram: **Client** = Client; **Pipeline** = Server & pipelines; **Server** = Server code, no model; **Model** = Agents & orchestration; **State** = State; **Guardrail** = Cross-cutting guardrails.

**Diagram: system architecture, client, server pipelines, orchestrator, three agents, state and guardrails.** Five bands stacked top to bottom, each feeding down into the next: Client, then Server, then Orchestrator, then Agents, then Shared state, with a cross-cutting band at the bottom that is not a stage. A box drawn with a dashed outline is a Model box: a model runs there, so what leaves it is provisional until a person accepts it.

**Band 1, client: browser, nothing to install.** Four boxes in a row.

1. **Microphone capture** (Client). Continuous room audio, chunked and streamed. Visible recording indicator that cannot be hidden.
2. **Photograph upload** (Client). Phone camera or drag-and-drop. Any participant, no login, via the session join link.
3. **Command bar** (Client). Type, or push-to-talk. The same commands the speech path recognises, for noisy rooms.
4. **Canvas renderer** (Client). Live, multi-user, pan and zoom. Expand or collapse sticky notes locally; drag, edit, delete and undo shared content.

Feeds down into band 2.

**Band 2, server: raw input becomes ordered events.** Four boxes in a row.

1. **Audio pipeline** (Pipeline). Voice detection, chunking, local speech-to-text, speaker labels. Audio does not leave the server.
2. **Image pipeline** (Pipeline). Deskew, crop, split a wall into individual notes, read the handwriting, keep the original.
3. **Session and identity** (Server). Join links, roles (facilitator vs participant), and the consent flag that unlocks capture.
4. **Event bus** (Server). One ordered stream of what happened. Everything downstream reads from it, replayable.

Feeds down into the orchestrator.

**Orchestrator** (Model), one box spanning the full width. Classifies every event (is this just talk, a command, a question, or an image?), routes it to the agent that handles it, enforces the guardrails below, and merges the results back into one coherent canvas instead of three competing ones.

Feeds down into band 3.

**Band 3, agents: division of labour.** Three boxes in a row.

1. **1 · Notulator** (Model). Rolling minutes from the transcript. Pulls out decisions, action items, open questions and who said what. Runs constantly, never interrupts. Everything it writes keeps a timestamp back into the transcript.
2. **2 · Command interpreter** (Model). Decides whether something said in the room was addressed to the tool. Parses it into one canvas operation: cluster, compare, sequence, split, summarise, answer. Ambiguity gets a confirmation, never a guess.
3. **3 · Visualiser** (Model). Chooses the form (cluster, timeline, matrix, flow) and lays it out with real placement, not a list. This is the part that makes it a visual conclusion instead of minutes in a different font.

Feeds down into band 4.

**Band 4, shared state: the single source of truth.** Three boxes in a row.

1. **Transcript store** (State). Timestamped, speaker-tagged, searchable. The thing every citation points back into.
2. **Canvas model** (State). Sticky notes with main points and supporting detail, links, clusters, saved positions, and provenance. Expansion is local view state.
3. **Entity index** (State). People, topics, decisions, open questions. What makes "who objected and why" answerable.

A long dashed arrow runs from the right-hand edge of this band all the way back up to the client band, labelled: "state streams back to every connected screen".

Feeds down into band 5.

**Band 5, cross-cutting: applies to every layer above, not a stage.** Four boxes in a row.

1. **Consent gate** (Guardrail). No microphone, no camera, no model call until agreement is logged. Anyone can stop it.
2. **Provenance on everything** (Guardrail). Every item knows its maker and its source. AI output is never indistinguishable from the team's.
3. **Failure behaviour** (Guardrail). Slow: queue it and say so. Down: capture keeps running, visuals catch up. Never a silent gap.
4. **Retention** (Guardrail). Audio deleted after the session. Transcripts anonymised before they leave the raw folder.

> **Why three agents rather than one prompt**
>
> - **Different clocks.** The notulator runs constantly on a rolling window. The command interpreter only fires when addressed. The visualiser fires on demand and is expensive. One chain would make all three run at the slowest and priciest rate.
> - **Different failure modes.** A bad layout is annoying; a bad command is destructive. They need different confirmation thresholds, which is hard to express inside a single prompt.
> - **The honest counter-argument:** three agents means orchestration, ordering and merge conflicts to build, and that is real work. If the week’s tests show a single chain is fast enough, collapse it. Decide on measurement, not on the diagram.
>

## 3 · Functionalities

**Every functionality, broken out**

Six groups, numbered so they can be referenced in the decision log, in issues, and when dividing work (“I’ll take F3.2”). The *AI?* column is the course’s question: remove the model and does this function still exist? Where the answer is no, that is where the design work is.

### F1 Capture (getting the room into the system)

| ID | Function | What it does | AI? | Main risk |
|---|---|---|---|---|
| F1.1 | Live audio capture | Continuous room audio from one device, chunked and streamed, with a recording indicator nobody can hide. | No | One laptop mic in a room of eight. Far speakers drop out. |
| F1.2 | Speech to text | Transcription running during the meeting, not after. Dutch and English, often in the same sentence. | Yes | Accuracy in a live room with overlap, accents and jargon. This is the riskiest assumption in the whole tool. |
| F1.3 | Speaker separation | Who said which line, so “what did she say” is answerable at all. | Yes | Degrades badly when people talk over each other, which is what design meetings are. |
| F1.4 | Photograph intake | Any participant photographs the wall, a sketch or a screen from their phone, no login. | No | Nobody remembers to do it. Needs a prompt from the tool. |
| F1.5 | Note segmentation | Splits a photograph of a sticky wall into individual notes, keeping colour and physical grouping as signal. | Yes | Angle, glare, overlap. Grouping by proximity is a guess. |
| F1.6 | Handwriting reading | Reads what is on each note, in mixed handwriting and mixed languages. | Yes | If correcting the output costs more than retyping, the feature is negative value. Test before building. |
| F1.7 | Typed input | Notes and questions typed by anyone, for quiet participants and noisy rooms. | No | None. Build it first, it is the fallback for everything above. |

### F2 Understanding (agent 1 and agent 2)

| ID | Function | What it does | AI? | Main risk |
|---|---|---|---|---|
| F2.1 | Rolling minutes | A running summary that stays current through the meeting rather than appearing at the end. | Yes | Summarising too early flattens a discussion that has not concluded yet. |
| F2.2 | Decision extraction | Spots when the room actually decided something, and records the reasoning, not only the outcome. | Yes | Teams rarely say “we have decided”. Detecting agreement is genuinely hard. |
| F2.3 | Action items and owners | Pulls out who agreed to do what, by when. | Yes | Inventing an owner is worse than leaving it blank. |
| F2.4 | Open question tracking | Keeps a visible list of what was raised and never resolved. | Yes | Grows unbounded and becomes noise unless it is pruned. |
| F2.5 | Command detection | Decides whether a sentence was addressed to the tool at all. Wake word, or push-to-talk. | Yes | False positives act on the canvas uninvited. False negatives make it feel dead. Named in the notes as core. |
| F2.6 | Intent parsing | Turns a recognised command into exactly one canvas operation, with the right items selected. | Yes | “Those three” means nothing without knowing what is on screen and what was just discussed. |
| F2.7 | Grounded question answering | Answers a question from the session so far, live, citing the moment the answer came from. | Yes | A confident wrong answer mid-meeting is worse than no answer. Citation is the mitigation. |
| F2.8 | Live suggestions | Offers ideas and prompts unasked, while the team is still diverging. | Yes | Anchoring. An AI suggestion on the board mid-divergence narrows the space and carries authority a half-formed human idea does not. Put behind a facilitator toggle so it can be tested rather than assumed. |

### F3 Visualisation (agent 3, the part that makes it not a notes app)

| ID | Function | What it does | AI? | Main risk |
|---|---|---|---|---|
| F3.1 | Canvas data model | Sticky-note main points and supporting detail, links, clusters, saved positions and provenance. Disclosure is local view state. | No | Getting it wrong early makes every later feature expensive. Design this first. |
| F3.2 | Form selection | Picks the right shape for the content: cluster, timeline, matrix, flow, hierarchy. | Yes | Defaulting to a cluster every time is the failure mode. That is a list with extra steps. |
| F3.3 | Automatic layout | Organises notes by meaning using appropriate groups, order and connections; preserves team adjustments. AI meaning stays provisional. | Yes | Ugly or overlapping layout destroys trust faster than a wrong summary does. |
| F3.4 | Non-destructive insertion | New AI output never moves or overwrites what the team placed by hand. | No | Violating this once loses the room permanently. |
| F3.5 | Provisional styling | AI-made items look visibly different until accepted. | No | Cheap to build, and the single strongest trust mechanism in the tool. |
| F3.6 | Direct manipulation | Move, edit, regroup, correct connections and delete by hand. Team adjustments take priority over automatic organisation. | No | Substantial front-end work. Easy to underestimate. |
| F3.7 | Undo | One step back from anything the AI did, at any time. | No | Non-negotiable. Without it nobody will let it touch a live board. |
| F3.8 | Expandable sticky notes | Topic-coloured main points unfold in place into supporting detail and session sources. Group labels and a key accompany stable colours. Temporary spacing preserves saved arrangement; expansion and colour changes never accept content. | No | Hidden qualifications, overlap and accidental acceptance. Review the complete proposal before accepting. |

### F4 Session and collaboration (more than one person in the room)

| ID | Function | What it does | AI? | Main risk |
|---|---|---|---|---|
| F4.1 | Create and join | A session is a link. Guests need no account. | No | None, but it gates everything else. Build early. |
| F4.2 | Live multi-user view | Shared screen plus phones, all in sync, sub-second. | No | Real-time sync is the classic underestimate. |
| F4.3 | Roles | Facilitator can steer the tool and change modes; participants can add and ask. | No | Open question from the notes: anyone commands it (chaos) or only the facilitator (bottleneck). |
| F4.4 | Mode switch | Quiet mode (listens only) versus active mode (may suggest). Facilitator-controlled, visible to the room. | No | Makes F2.8 testable instead of a permanent argument. |
| F4.5 | Agenda anchoring | Links what is being said to the agenda item it belongs to. | Yes | Meetings drift. Forcing structure onto drift produces confident nonsense. |

### F5 Output (it has to leave the tool)

| ID | Function | What it does | AI? | Main risk |
|---|---|---|---|---|
| F5.1 | Canvas export | PNG and PDF of the finished canvas, straight after the meeting. | No | Low. Ship it early, it is the visible proof the tool did something. |
| F5.2 | Minutes export | Decisions, actions and open questions as text, each linked to its moment. | No | Low. |
| F5.3 | Board integration | Push the result into Miro or FigJam, where the team already works. | No | API cost and effort may exceed the value. Check the API before committing to it. |
| F5.4 | Searchable archive | Past sessions stay queryable after the fact. | Yes | Scope creep. This is where the tool quietly becomes the post-meeting product it was meant not to be. |

### F6 Trust, consent and failure (the part that decides whether anyone uses it)

| ID | Function | What it does | AI? | Main risk |
|---|---|---|---|---|
| F6.1 | Consent gate | Recorded, logged agreement from everyone present before any capture starts. Anyone can stop it mid-session. | No | A hard gate. Unsettled, and the tool cannot be tested with real teams at all. |
| F6.2 | Local processing | Audio is transcribed on our own server, not sent to a third-party speech API. | No | Local models are slower and less accurate. A real trade-off against F1.2, not a free win. |
| F6.3 | Citation to source | Every claim points to session evidence, accessible from its expanded note. Unavailable sources remain labelled rather than invented. | No | Cheap, and it turns “trust me” into “check me”. |
| F6.4 | Degradation behaviour | Model slow: queue and show it. Model down: capture keeps running, visuals catch up later. Never a silent gap. | No | The assessment asks how the design handles unreliability, not whether it is reliable. |
| F6.5 | Correction capture | When a human fixes AI output, the correction is recorded as evidence, not just applied. | No | This is the evaluation data. Without it there is nothing to measure against a baseline. |
| F6.6 | Retention and deletion | Audio deleted after the session; transcripts anonymised before leaving the raw folder. | No | Must be automatic. A manual step will be skipped. |

> **Open questions, carried over from the notes**
>
> - **Is this too wide?** Six groups here are realistically three products: speech recognition, physical-to-digital capture, and grounded retrieval and layout. The notes propose a core of accurate live transcription plus command recognition turning into visuals. Concept 001 proposes a different core: sticky-note capture plus board write-back. These are not the same cut and one of them has to win.
> - **Does it volunteer, or only answer?** The notes want live suggestions. Concept 001 argues against them on anchoring grounds. F4.4 keeps both alive as a switch, but someone still has to decide what the default is.
> - **Who may command it?** Anyone is chaos, only the facilitator is a bottleneck. See F4.3.
> - **Miro or FigJam, or neither?** Decide on API access and cost, not on preference. See F5.3.
> - **Does it speak?** Voice output interrupts a meeting. Text on the shared canvas probably wins.
> - **Riskiest assumption, still untested:** that live transcription and handwriting reading are accurate enough under real room conditions to be worth correcting. Agree a number before testing, not after.
>

---

- Jarvaids: flowchart and functionalities
- Drafted from the team’s whiteboard notes
- Print or save as PDF to hand around: all three views print
