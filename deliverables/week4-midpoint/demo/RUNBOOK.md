# Demo runbook, Jarvaids midpoint

For the person running the demo, who is not the person presenting. Read it
once the night before and once in the morning. The lines under **Say** are the
actual words, and the presenter says them while the demo runner drives.

## What is on the screen, and what it is not

The demo is the real client on the real backend. Everything the room sees
happen, happens: a session is created, agreement is recorded, a note is typed,
a picture is uploaded through the browser's own file picker, readings come back
provisional, a person corrects, accepts and rejects them, and a drag lands on
the server as a position change without review.

Two things are stand-ins, and each is labelled on screen so a projector cannot
turn them into evidence:

| Stand-in | How it is labelled |
|---|---|
| The reading of each marked note. The only extraction adapter is a fixture; no handwriting recognition has ever run in this project | The review row is dashed and reads "Read by fixture, not yet accepted. Stand-in reading: no handwriting recognition ran" |
| The wall itself, `wall.png`, drawn by `make_wall.py` | Its bottom edge says "Drawn stand-in wall for the demo. Not a photograph of a real session" |

The wall is drawn rather than photographed because the reading is a stand-in
whatever the picture is, so a real photograph would prove nothing extra and
would put real handwriting and a real room into the repository.

This is a design proposal, not a product demo. The demo exists to make one rule
visible: nothing a model made reaches the board as the team's work until a
person accepts it, and moving a note is not accepting it. Five steps, then stop.

## Before the room

1. Open a terminal in the repository root. Run:

   ```sh
   bash deliverables/week4-midpoint/demo/start.sh
   ```

2. Read the block it prints. You want `client up on http://127.0.0.1:5173/client/`
   and `state: active`.
3. Open the client URL in the browser that will be on the projector. Do not
   press Start yet: the room should see the session being made.
4. Have `deliverables/week4-midpoint/demo/wall.png` visible in a file manager
   window, so the file picker in step 2 is one click, not a search.
5. Open a second browser window with the five images in `fallback/` already
   loaded, in order. This is the fallback window. Put it on the second desktop.
6. Browser zoom at 125 percent or more. The client is laid out for a laptop,
   the room is looking at a projector.

## What is in this folder

| File | What it does |
|---|---|
| `start.sh` | Cold start: clears the ports, fresh data directory, backend on 3000, client on 5173, one seeded session as proof, prints what you need |
| `stop.sh` | Stops everything `start.sh` started |
| `wall.png`, `make_wall.py` | The drawn wall the demo uploads, and the script that draws it |
| `fallback/` | Five captures of the real client doing the five steps below, at 1280x800 |
| `shots.mjs` | Retakes `fallback/` from the running client. Run it after any client change |
| `step.sh <1..5>` | Terminal-only fallback that drives the seeded session over HTTP if the browser is the thing that died |

## The steps

### Step 0: the session starts. Live.

**Do.** Press **Start** in the client. Press **I agree** when the agreement
appears, then **Start capture**. The header reads `active`.

**Say.** "The session is made in front of you. Nothing is recorded until
everyone in the room has agreed, and the agreement is the first thing the
record contains."

### Step 1: a typed note goes to Review, not to the canvas. Live.

**Do.** On **Capture**, type `Onboarding loses people at step three` and press
**Add**. Open **Review**. The note is there, plain, with "Typed by a
person, not yet accepted". Open **Canvas**: it is empty.

**Say.** "A note somebody typed still goes through review before it is on the
board, because the board is the team's record and nothing enters it unread. But
it is not drawn as a guess, because a person wrote it."

**Fallback.** `fallback/01-typed-note.png`.

### Step 2: the wall is photographed and three notes marked. Live.

**Do.** On **Capture**, press the photo control and pick `wall.png` from the
file picker. Drag a box around each of the three top notes. The counter reads
`3 marked`. Press **Send for reading**.

**Say.** "Now the wall. Somebody marks the notes they want read. The photograph
goes to the server, which strips its metadata and keeps only the pixels and the
marked regions."

**Fallback.** `fallback/02-wall-marked.png`.

### Step 3: the readings come back provisional. Live, and the honest moment.

**Do.** Open **Review**. Three new rows, each dashed, each labelled "Read by
fixture, not yet accepted. Stand-in reading: no handwriting recognition ran".

**Say, exactly once, and then move on:**

> The reading you are seeing is a stand-in; no handwriting recognition has run
> yet. The flow around it is real and is what we are showing.

Do not expand on it, do not apologise for it, and do not answer a question about
recognition accuracy with a number. If asked: "we have not measured that,
because we have not run it."

**Say, then.** "What matters is the dashed edge. Anything a model made is drawn
so that it can never be mistaken for something the team made. That is the
product's one rule, and the interface enforces it rather than promising it."

**Fallback.** `fallback/03-readings-provisional.png`.

### Step 4: a person corrects, accepts and rejects. Live.

**Do.** In the first dashed row, replace the text with `Onboarding loses people
at step 3` and press **Accept**. In the next dashed row press **Reject**. In
the typed row press **Accept**. Open **Canvas**: two notes, one marked "read
from a photograph", one marked "typed". The rejected one is nowhere.

**Say.** "Correcting before accepting is the normal path, not an exception.
Until the person pressed Accept, the reading was a claim; now it is the team's
note, and the record keeps that it started as a claim. The rejected one never
reached the board."

**Fallback.** `fallback/04-accepted.png`.

### Step 5: a drag. Moving is not agreeing. Live.

**Do.** Drag the photographed note somewhere else on the canvas. Let go.

**Say.** "Moving a note changes where it is, not what it means. That went
straight to the server as a position change, with no review, because dragging
something into a group is not the same as agreeing with it. Position and
content are separate revisions on purpose."

**Fallback.** `fallback/05-drag.png`.

**Stop here.** Export and delete exist and work, and are not worth the seconds.
Hand back to the presenter.

## Fallback procedure

**The rule: if anything fails, switch windows and narrate. Never debug in front
of the room.**

A browser with an error in it is four minutes of silence and the class watches
you type. The fallback window costs five seconds and the presenter keeps talking.

- **Which window.** The second window, holding `fallback/` at 1280x800, in
  numerical order. It is open before you start, not opened when you need it.
- **What you say when you switch.** "The demo machine is having a moment, so
  here is the same step, captured from the client this morning." Then carry on
  with the same words from the step you were on.
- **What you do not say.** Anything beginning with "it worked this morning".
- **If the browser died but the terminal is alive**, `step.sh 1` through `5`
  drive the seeded session over HTTP and print the records. It is a worse show
  than the screenshots and a better one than nothing, and it proves the server
  is real if anyone doubts the captures.
- **After the session.** The log is in `.local/demo/<timestamp>/server.log`.
  Read it afterwards, not then.

### What the fallback images are

Captures of the real client, driven by `shots.mjs` through the same five steps
on its own backend, at 1280x800. They are not drawings and their content is
what the client showed. The session id and timestamps in them are from whenever
`shots.mjs` last ran, which is why it is rerun after any client change: a stale
fallback shows a screen the client no longer has.

## Pre-flight, tomorrow morning

Allow fifteen minutes. Do it in this order and tick each line.

- [ ] `rm -rf .local/demo` then `bash deliverables/week4-midpoint/demo/start.sh`.
      It prints `client up` and `state: active` in a few seconds.
- [ ] Run `start.sh` again without cleaning. It reclaims both ports, prints a
      **different** session id, and does not error.
- [ ] Open the client URL. Walk steps 0 to 5 end to end, out loud, at
      presentation pace, with the presenter saying the lines. Time it: the deck
      gives this 1:30.
- [ ] Say the step 3 sentence out loud once. It should take one breath.
- [ ] Open the five fallback images in the second window, in order, and leave
      them open.
- [ ] Check the browser zoom from the back of the room.
- [ ] `bash deliverables/week4-midpoint/demo/stop.sh`, then start again clean for
      the real thing.
