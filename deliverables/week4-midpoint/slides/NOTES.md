# Speaker notes, week 4 midpoint deck

Draft written by the coordinator for the group to edit. Rehearse once and
change any sentence that does not sound like you.

## Practical

- Nineteen slides. The targets below add up to 7:00, which is the limit, so
  aim to finish the rehearsal at 6:30.
- Two presenters. One presents slides 1 to 17 and 19. The second runs the
  demonstration on slide 18, following `demo/RUNBOOK.md`.
- The readings shown in the demonstration come from a placeholder adapter.
  Say so once, on slide 14, and once at the start of the demonstration. Do
  not give an accuracy figure; none has been measured.
- On the flowchart slides, press Z or click the diagram to show it on the
  whole screen. Escape returns to the slide.
- If someone asks which model would be used, refer them to
  `documentation/stack.md`, section 2. It lists the candidates, their
  licences and the test that would decide between them.
- The counts on slide 17 (254 tests, 150 guards, 13 audit checks, 105
  contrast pairs) come from `AGENTS.md`.

## Slide 1, title. 0:10

Introduce the group and the project name. Read the sentence on the slide.
Mention that the wall shown is a drawing made for the demonstration, not a
photograph of a real session.

## Slide 2, project background. 0:20

Design teams in working sessions produce a lot of material that is not
recorded. The three problems on the slide come from the concept document. A
remark from earlier in the session cannot be found again. The wall is
photographed but the notes are rarely typed up. The board survives, but the
reasoning behind it does not.

## Slide 3, users and context. 0:15

The users named in the brainstorm notes: designers, technical participants
in multidisciplinary teams, and Master's students in design programmes. The
context is a meeting or brainstorm session that combines spoken discussion,
sketches, sticky notes and photographs. Two to eight people, one to two
hours, one facilitator, a shared screen.

## Slide 4, product concept. 0:25

The concept from the brainstorm notes. The tool listens to the discussion
and takes photographs of the wall, sketches and screens as input, together
with typed notes and voice commands. From that it keeps a structured visual
overview on the digital whiteboard during the meeting: themes and clusters,
decisions and actions, open questions, and the notes from the wall. On
request it answers questions about the meeting so far and suggests next
steps. The point of doing this during the meeting rather than after is that
the overview can be corrected while the people who said the words are still
in the room.

## Slide 5, features. 0:30

Eight features, each with its function numbers from the flowchart and its
current status. Live transcription with speaker labels. Voice commands such
as "summarise this" or "add this to the planning", carried out on the
whiteboard. Photographs of the wall become individual notes. A live overview
of themes, decisions, actions and open questions, laid out rather than
listed. Questions about the meeting, answered with the moment cited.
Everything the tool adds is provisional until a participant accepts it, and
corrections are recorded. Consent before capture, audio deleted afterwards.
Export of the canvas and minutes, and a push to Miro or FigJam.

Two of the eight are built, with the photograph reader as a placeholder.
Transcription is plumbing. The rest is proposed.

## Slide 6, voice commands. 0:25

An example of how a command would work. A participant says "add this to the
planning". The command interpreter first decides whether the sentence was
addressed to the tool at all, since most sentences in a meeting are not.
It then works out which operation is meant and which items "this" refers
to, using the canvas and the last minute of speech. It proposes one change
to the whiteboard, drawn as provisional, and a participant confirms it. If
the reference is ambiguous the tool asks rather than guesses. This pipeline
is designed in the pipelines document and has not been built.

## Slide 7, findings from week 3. 0:20

Four findings from the week 3 material. Generic AI feedback was found
unhelpful; specific feedback on a named element was useful. Simulated
interviewees answered differently from real ones, so simulated interviews
are not treated as evidence. The MapIt report presented one interviewee's
view as a group conclusion, so its findings are cited with care. In the
FrameIt conversation the group asked for a live overview in which AI
suggestions are visibly distinct from what was said.

The interviews are cited through the MapIt report and the group's own
summary, not from the transcripts.

## Slide 8, design question. 0:20

Read the question. It combines the concept, the week 3 findings and the
flowchart. The second half of the question, keeping the team's work distinct
from what a model proposed, is the principle on the next slide.

## Slide 9, provisional output. 0:20

Anything a model produces is marked provisional until a participant accepts
it. On screen, a provisional note has a dashed edge and a line naming its
source. Accepting, correcting or rejecting a note is done by a participant.
Moving a note on the canvas does not count as accepting it, because
arranging notes is not the same as agreeing with their content.

## Slide 10, user journey. 0:15

This is the journey diagram from the documentation. Three bands: before the
meeting, during the meeting, after the meeting. Before: a session is
created, everyone in the room agrees to recording, the canvas is chosen and
the team joins. After: the canvas is the record, it can be exported, and
audio is deleted. The middle band is on the next slide.

## Slide 11, user journey, during the meeting. 0:25

Input from the room is on the left: speech, photographs, spoken commands and
typed notes. Three agents in the middle: one keeps the running record, one
interprets commands, one lays out the canvas. The canvas is on the right,
with the two actions participants take: accept, edit, reject or move; and
ask a question about the session so far. Dashed boxes are where a model
runs. The loop repeats during the meeting.

## Slide 12, system architecture. 0:20

Five layers. The client is a browser page with nothing to install. The
server turns input into ordered events. An orchestrator routes each event to
one of three agents. Shared state holds the transcript, the canvas model and
an entity index. The guardrails at the bottom apply to every layer: consent,
provenance on every item, behaviour on failure, and retention. The agent
boxes describe responsibilities, not separate services.

## Slide 13, functions in scope. 0:20

The flowchart defines thirty-seven functions in six groups. Each has a
status. Built means it runs in the repository and is tested. Plumbing means
the contract and tests exist but the model does not. Proposed means it is
designed and nothing runs. Open means the team has not decided. Sixteen are
built, five are plumbing, fourteen are proposed and two are open. Everything
that depends on speech or handwriting recognition is plumbing or proposed.

## Slide 14, from photograph to notes. 0:30

The three captures are from the client. A participant marks each note on
the photograph. The server stores the marked regions and sends them to an
adapter. The only adapter in the repository is a placeholder: it returns a
fixed text and no handwriting recognition has been run. Each reading comes
back for review, where a participant corrects, accepts or rejects it.
Accepted notes reach the canvas.

The proposed next step is automatic segmentation and reading, with the
hand-drawn box kept as the way to correct a wrong split. The candidate
models are listed in `stack.md`.

## Slide 15, speech pipeline. 0:15

Nine stages are designed in the pipelines document; three involve a model.
What exists: a server contract for audio, a browser chunker and a
placeholder transcriber. A wrapper for a local Whisper model is written and
has not been run. Speaker separation is currently attribution by connection,
not diarisation. No speech recognition has been run in this project.

## Slide 16, technology stack. 0:15

Solid boxes are in the repository: a plain browser client, HTTP and JSON,
Python with SQLite, Pillow for images, and the two placeholder adapters.
Dashed boxes are candidates that have not been run. The consent gate sits
between the server and anything hosted: nothing leaves the server unless
that has been agreed. Names, licences and reasons are in `stack.md`.

## Slide 17, repository and verification. 0:15

Every push runs seven checks before it can be merged: the design audit,
house style, the backend suite with mutation guards, the sync budget, the
schema registry, the client tests, and a browser journey. The counts on the
slide are from `AGENTS.md`. A description of the setup is in
`how-we-work.md`.

## Slide 18, live demonstration. 1:00

Hand over to the second presenter. The sequence is in `demo/RUNBOOK.md`:
a note is typed and appears in review; the wall is photographed and three
notes are marked; the readings arrive for review; one is corrected and
accepted, one rejected; an accepted note is moved on the canvas.

Say once, when the readings arrive: the readings are placeholders, no
handwriting recognition has been run, and the workflow around them is what
is being shown.

## Slide 19, riskiest assumption and next steps. 0:20

The first test is whether notes on a real wall can be read well enough to be
worth correcting. Ten photographs of real walls, through two or three vision
models. Two thresholds, agreed before the test: 80 percent of notes
correctly separated and 80 percent correctly read. Speech capture follows,
subject to consent from everyone present.
