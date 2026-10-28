# Current integrated browser client

Use [the complete localhost trial](../../COMPLETE-LOCAL-TEST.md) for the current
Windows launcher, all available functions, missing WP1 and group microphone script.
[LOCAL-FEATURES.md](../../LOCAL-FEATURES.md) is the current inventory. The sections
below retain the older fixture journey as development history; their statements
about missing speech, shapes, live photo reading and command execution are
superseded by the integrated trial and current source.

# Combined live-test mode

For real Dutch transcription, use the setup and start commands in
[LOCAL-TEST.md](../../LOCAL-TEST.md). The older commands below intentionally
start fixture mode; historical fixture-only statements describe that mode.
The combined launcher enables Whisper, keeps image extraction synthetic,
and does not turn transcript lines into canvas notes automatically.

# The Jarvaids client

The first thing in this project a person can use. Everything else verifies a
mechanism; this is the mechanism with a person in front of it.

## Running it

Two terminals, because it is two processes on purpose.

```sh
# 1. the backend
cd app/server
python3 -m genai_server --port 3000 --data-dir .local --allow-origin http://127.0.0.1:5173

# 2. the client
cd app/client
python3 serve.py --port 5173
```

Then open <http://127.0.0.1:5173/client/>.

The `--allow-origin` is not optional and not a formality. The backend refuses
origins it was not told about, which is why opening `index.html` from disk does
not work: a `file://` page has the origin `null`.

## What it does

One workspace: a canvas you can pan and zoom, with a rail beside it for review,
the live transcript and adding things. Start a session, agree, start capture,
then:

- **Listen.** The bar's Listen button sends the room's audio in short chunks;
  each becomes a line in the Transcript tab. The only transcriber is a labelled
  stand-in, so the lines say `FIXTURE ONLY` and the tab says no speech
  recognition ran.
- **Photograph the wall** (Add tab), mark the notes, send it. Each reading lands
  on the canvas dashed and labelled Provisional, naming the adapter.
- **Type a note** (Add tab). It lands on the canvas with a plain border and
  "not yet reviewed": a person wrote it, so it is not a guess, but nobody has
  accepted it.
- **Review** a note from its own button or the Review tab. Correct the text,
  then accept or reject. Accepting turns it solid.
- **Show details** on any note: who wrote or read it, confidence and paper
  colour (or "Not measured"), who accepted it, how it was placed, and the crop
  of the photograph it came from.
- **Group** notes: click one, shift-click more, name the group, Propose group.
  The hull is dashed until a facilitator accepts the group in Review. After
  that, dragging a note into the hull adds it and dragging it out removes it.
- **List** view shows the same notes and groups as rows, for small screens and
  for reading without the canvas.
- **Export** from the bar: JSON and Markdown, downloaded with the session's
  credential. Delete is in the same dialog, behind a second button.
- **Stop capture** is always on the bar. It pauses the room for everyone and
  stops listening.

Three product rules are enforced on screen rather than assumed, because they
are the ones a user interface quietly breaks:

- **Anything a model made is drawn as provisional**: dashed violet stroke and a
  Provisional label, text never greyed. That covers readings and proposed
  groups. Nothing a model made is rendered the way accepted work is rendered.
- **Moving a note is not agreeing with it.** A drag goes straight to
  `item.place` with no review. Review is for meaning.
- **Opening details changes only your screen.** Notes below an open one are
  pushed down by display offsets recomputed from saved positions, never sent to
  the server. Moving an open or pushed note is refused until details are
  closed, so an offset can never be saved as a move.

## Ten-minute click-through

For a person checking the app before it is shown to anyone. Run both servers as
above, open <http://127.0.0.1:5173/client/> in Chrome, and do these in order.
Each line says what you should see; anything else is a bug worth writing down.

1. **Start**, then **I agree**, then **Start capture**. The bar says Recording.
2. **Add** tab: type "Onboarding loses people at step three", **Add**. A note
   appears on the canvas with a plain border and "not yet reviewed".
3. Click **Review** on that note. The Review tab opens with it highlighted.
   Change "three" to "two", **Accept**. The note turns solid ink and keeps "two".
4. **Add** tab: choose any photo, drag a box over part of it, **Send for
   reading**. Within a second or two a dashed note marked **Provisional**
   appears, reading "FIXTURE ONLY".
5. **Show details** on it. You should see "Stand-in reading", Confidence and
   Paper colour "Not measured", and the cropped part of your photo. Notes below
   it move down. **Hide details** puts them back.
6. Try to drag the note while its details are open: it refuses and says why.
7. Reject the stand-in in Review. Type and accept a second note.
8. Click one accepted note, shift-click the other, type "Onboarding" in the
   group box, **Propose group**. A dashed hull appears. Accept it in Review: the
   hull turns solid and both notes say "Onboarding".
9. Drag one note far out of the hull. It leaves the group. Drag it back in.
10. Zoom with the − and + buttons, ctrl and scroll, or a pinch; pan by dragging
    empty canvas. **Fit** brings everything back.
11. **List**: the same notes, under "Group · Onboarding".
12. **Listen** and allow the microphone. Talk, pause, talk. The Transcript tab
    fills with stand-in lines under your name. **Stop listening**.
13. **Export**, **Create an export**, open both downloads. Your accepted notes
    are in them.
14. **Stop capture**. The bar says Paused, a banner offers Resume.
15. Shrink the window to phone width. Nothing scrolls sideways.

## What it is not

- **No build step, no framework, no runtime dependency.** It loads
  `../server/client.mjs`, `../server/session-sync.mjs` and
  `../server/capture-audio.mjs` as plain ES modules, and the design system's
  stylesheet as plain CSS. Playwright appears in `package.json` only to drive
  the journey test in a real browser.
- **Not a second implementation of the protocol.** `session-sync.mjs` owns the
  delta protocol, resync and board order. `board.mjs` draws; it does not decide
  what the server knows.
- **Not evidence of anything about AI quality.** The only extraction and
  transcription adapters are labelled synthetic fixtures. No handwriting or
  speech recognition has ever run in this project.
- **Not Miro.** No shapes, connectors, templates, live cursors or multi-select
  drag. One note moves at a time. Other screens see a change on their next
  poll, about once a second.
- **Not yet in it, each for a stated reason:**
  - *Summaries.* A collapsed note shows its full text, because the server has
    no separate summary and expandable-notes.md forbids cutting text off and
    calling it a summary. Details show provenance only.
  - *Topic colours.* Notes are white. The planned topic palette needs its own
    contrast and colour-vision testing first (expandable-notes.md).
  - *Turning transcript lines into notes, decisions or actions.* That is F01,
    which waits on a group decision about what those records are.
  - *Moving a note with the keyboard.* Notes are reachable by keyboard through
    their buttons and the list view, but moving one needs a pointer (M02).
  - *The layout engine.* Nothing places notes automatically; unplaced notes
    wait in a "Not placed yet" column until someone drags them. Unplaced poll,
    to-do, requirements and calendar objects instead share a top-aligned horizontal row;
    this local display arrangement writes no positions. New commands focus at
    readable scale, with horizontal panning on narrow screens. Hand placements
    remain exact, and the explicit Fit control still fits the whole canvas.
- **Audio uses ScriptProcessorNode**, which browsers have deprecated in favour
  of AudioWorklet. It works in current Chrome and logs a warning, not an error.
  The first browser run of `capture-audio.mjs` found it asked for a 320-sample
  block, which no browser accepts; it now takes 1024-sample blocks and re-cuts
  them into 20 ms frames.

## The test

```sh
node --test tests/board-unit.mjs   # the board's pure rules, in Node, in a second
node tests/journey.mjs             # the whole workspace, in a real browser
```

`board-unit.mjs` covers what the canvas and the list both show, group
membership, the provisional rule and the width steps; each was seen to fail
against a deliberately broken copy before it was trusted.

The journey starts both servers itself and drives a real browser through the
workspace: agreement before capture, a typed note reviewed from the canvas with
a correction, a photographed reading drawn provisional and naming its adapter,
details that open without saving anything, a proposed group accepted, a drag at
reduced zoom that the server agrees with and that leaves the group, pan and
zoom, the list view, listening with a fake microphone, an invitation, both
exports downloaded with the credential, stop capture, phone width, and no
console errors anywhere. Set `SCREENSHOTS=<dir>` to keep screenshots, and
`CHROMIUM_PATH` to use a browser Playwright did not install. It skips with a
message if Playwright is not installed, because a missing browser is not a
broken client.

It exists because the client's first three defects were all invisible to
assertions:

1. a favicon request no one wrote, 404ing into the console
2. `session-sync.mjs` defaulting to bare `setTimeout`, which is fine under Node
   and throws `Illegal invocation` in a browser, because a timer called without
   `window` as its receiver is a detached method. The library had only ever
   been run under Node
3. a rule in `client.css` that painted the active tab's label in ink on the
   design system's ink background: a solid black block with invisible text

Two of those three needed a screenshot or a console to see, which is why
`AGENTS.md` asks for both and why this test checks both.


## Voice calendar candidate

After the reported successful requirements trial, `feature/voice-calendar` adds
agenda/calendar execution with day/week/month/year views, Unscheduled and shared
to-do deadlines/completion. See [the trial and integration guide](../../docs/voice-calendar.md).
The session setup defaults its editable IANA time zone from the browser. A
calendar has a wider canvas object; narrow screens keep readable scale and pan,
while List view provides the same editors, evidence and review controls. Accepted
shared-task changes require explicit review. Scripted browser checks passed at
1440/400 px; actual microphone quality and phone hardware remain unverified.
