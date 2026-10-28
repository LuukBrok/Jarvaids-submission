# UX inventory and analysis of the browser client, 18 October 2026

Step 4 of the plan agreed after PR #38: look at everything before redesigning
anything. **Analysis only.** Nothing here has been changed in the client, and
the recommendations are for the team to choose from, not decisions.

Made by Pieter with Claude Code. Every screen and state was walked through in
a real browser (Playwright, Chromium) at 1440 x 900 and 400 x 860, against a
local server reading photos with Claude (PR #38 branch). Findings are checked
against the design system's own rules in `app/design-system/spec/`, cited as
`file:line`, and against the client code in `app/client/`. Line numbers in `app.mjs`
refer to the PR #38 branch, which these screenshots were taken on.

**Not covered:** a second person joining from another device, screen readers,
real speech (the server ran the fixture transcriber, so the transcript shows
"FIXTURE ONLY"), a projector, and any user other than us.

## Overall impression

The client is honest and careful about provenance: anything a model made is
dashed violet and labelled, and its details name the model, its confidence
scale, the measured paper colour and the photo crop. That part matches the
spec and is worth keeping as it is.

The problem is everything around it. The product's two inputs, photographing
the wall and listening, are either hidden one click deep or misleading about
their state; review asks people to accept text without showing the evidence;
accepted notes pile up in one column with no structure; and on a phone the
main tasks sit below the canvas, with no touch target at the size the spec
requires. The flow follows the server's commands, not a person's job in a
meeting.

## 1. Inventory

| # | Screen or state | How you get there | Screenshot |
|---|---|---|---|
| 1 | Start or join | Opening the app | [01](ux-inventory/01-start-empty.png), phone [40](ux-inventory/40-phone-start.png) |
| 2 | Agreement before capture | After Start or Join | [02](ux-inventory/02-consent-before-agree.png) |
| 3 | Workspace, empty | After Start capture | [04](ux-inventory/04-workspace-empty.png) |
| 4 | Rail: Review, Transcript, Speakers, Add | Rail tabs | [21](ux-inventory/21-transcript-while-listening.png) |
| 5 | Add: type a note, photograph the wall, invite | Rail tab "Add" | [07](ux-inventory/07-rail-add.png) |
| 6 | Marking notes on a photo | Add, choose a file, drag | [10](ux-inventory/10-photo-marked.png) |
| 7 | Readings on the canvas | After Send for reading | [11](ux-inventory/11-canvas-after-reading.png) |
| 8 | Review queue | Rail tab "Review" | [12](ux-inventory/12-review-rail-readings.png) |
| 9 | Note details, in place | "Show details" on a note | [13](ux-inventory/13-note-details-open.png) |
| 10 | Accepted notes, not placed | After accepting | [15](ux-inventory/15-all-accepted-not-placed.png) |
| 11 | Selection and proposed group | Click, shift-click, name, Propose | [18](ux-inventory/18-group-proposed.png) |
| 12 | List view | "List" | [19](ux-inventory/19-list-view.png) |
| 13 | Listening and transcript | "Listen" in the bar | [21](ux-inventory/21-transcript-while-listening.png) |
| 14 | Speakers: enrol a voice | Rail tab "Speakers" | not kept |
| 15 | Export and delete session | "Export" in the bar | not kept: showed an invitation code |
| 16 | Paused | "Stop capture" | phone [27](ux-inventory/27-phone-workspace.png) |
| 17 | Phone width | 400 px | [27](ux-inventory/27-phone-workspace.png) |

### The main jobs, counted

| Job | Steps today | Where it hurts |
|---|---|---|
| Start a session that captures | Fill 3 fields (one is a server URL), Start, I agree, Start capture | Nobody can see who else has agreed |
| Photo of the wall to accepted notes | Add tab, choose file, drag a box per note in a 311 px wide panel, Send, notice the Review count, open Review, Accept each note | 8 steps plus one drag per note; no "reading" state; the crop is not shown at review |
| Speech to notes | Listen; then nothing reaches the canvas | The organise step does not exist ([proposal](proposal-organise-step.md)) |
| Arrange accepted notes | Drag each note out of "Not placed yet" | No layout, no use of the measured paper colour |
| Make a group | Select 2+, type a name, Propose group, open Review, Accept group | The facilitator reviews their own grouping |
| Invite someone | Add tab, Create an invitation, read out a 100-character string; they type it plus the server URL | No copy button; shown even when creating it failed |

## 2. Findings

Severity: **critical** blocks or misleads the main job; **moderate** costs time
or trust; **minor** is polish. Each has the spec rule it is judged against.

### Critical

**C1. The two inputs are hard to find, and photo marking happens in a 311 px
panel.** Photographing the wall sits under the rail tab "Add", below a typed
note and above "Invite someone" ([07](ux-inventory/07-rail-add.png)). Marking
happens on a 311 x 415 px preview ([10](ux-inventory/10-photo-marked.png)),
where a note is about 60 px wide and the boxes overlap neighbours. There is no
"Uploading" or "Reading notes" state and no screen to confirm what was found.
Spec: phone capture is one shutter, then "Uploading", "Reading notes", and
"Here is what we found" (`touch.md:388-459`).
*Recommendation:* "Photograph the wall" as a primary action in the session
bar, opening a full-width marking view; the model proposes the boxes and a
person adjusts them (the next WP4 step); a visible waiting state per photo.

**C2. Review asks for acceptance without the evidence.** The rail says
"Evidence first, conclusion second", but a reading's card shows only the
text, its kind and a confidence ([12](ux-inventory/12-review-rail-readings.png)).
The crop it was read from exists, but only inside "Show details" on the
canvas. Spec: review shows evidence above the conclusion (`patterns.md:87-98`).
*Recommendation:* the crop above the editable text in every reading's review
card; for speech, the quoted segment.

**C3. "Recording" is shown while nothing is being recorded.** The bar says
"Recording" whenever the session is active; audio only flows after a separate
"Listen", and a hidden tab stops listening without a message (`app.mjs:600`).
There is no timer. In a product whose rule is honesty about what was made and
captured, this is the one place the screen says something untrue. Spec: the
capturing state is a pulsing dot, "Recording" and a timer
(`accessibility.md:211-212`).
*Recommendation:* one capture indicator that reflects the microphone, with a
timer; "Session active" and "Recording" as different words.

**C4. Agreement is a button, nobody can see who agreed, and withdrawal is
promised but missing.** "I agree" is a primary button that stays primary after
use, and the next action, "Start capture", is secondary with no reason why it
is disabled ([02](ux-inventory/02-consent-before-agree.png)). The text says
"You can withdraw at any time", but no control exists (`consent.withdraw` is
only in the command list, `app.mjs:82`). Spec: one consent row per person with
Agreed, Not yet or Withdrawn, a gate naming who has not agreed, withdrawal in
one click (`patterns.md:112-118`, `components.md:266-273`).
*Recommendation:* a checkbox "I agree to this session being recorded", a row
per person, Start capture enabled with "Waiting for Sam to agree" until then,
and a Withdraw control in the bar.

**C5. Accepted notes pile up in one column.** Everything lands under "Not
placed yet" in a single column in the middle of an empty canvas
([15](ux-inventory/15-all-accepted-not-placed.png)), and "Fit" changes nothing.
The paper colour is measured for every photo note and shown only in details;
the canvas does not look like the wall it came from.
*Recommendation:* depends on the organise step (proposal, links 2 and 3); in
the meantime, a simple machine placement in a grid by source photo, as a
`placement` proposal, and the paper colour on the note.

**C6. On a phone, the main tasks are below the canvas and every target is too
small.** The rail stacks under a 62vh board, so photographing or reviewing
needs a scroll past it ([27](ux-inventory/27-phone-workspace.png)); the bar
wraps to two rows. Every control measured under 44 px, down to "Review" at
32 x 12 px and "Show details" at 59 x 17 px. The client loads only `_base.css`,
not `grid.css` (`index.html:11`), so the `.jv-hit` helpers that grow hit areas
never apply. Notes are draggable on a phone and Canvas is the default view.
Spec: 44 px both ways (`touch.md:304-319`); on a phone the board is read-only
and List is the default (`touch.md:470-495`).
*Recommendation:* load `grid.css` and apply `.jv-hit`; a phone layout where
the capture action and the review queue come first.

### Moderate

**M1. One global message line, never dismissed, that moves the page.** Every
message goes to one line above the canvas. It stays until the next server
command and pushes the whole layout down when it appears
([10](ux-inventory/10-photo-marked.png): "Mark at least one note…" still shown
after marking). Two messages are shown even when the action failed: "Added to
the canvas" after a failed add (`app.mjs:690-695`, the error is swallowed) and
an invitation code after a failed invite (`app.mjs:724-731`). Spec: problems
as a hairline banner saying what broke and what still works
(`components.md:275-290`), errors next to their field (`controls.md:477-482`).

**M2. The rail is a four-option segmented control used as navigation, and it
wraps at 1440 px** ("Add" drops to a second row, [04](ux-inventory/04-workspace-empty.png)).
Spec: a segmented control has at most 3 options and switches views of the
same content; screens use underline tabs (`patterns.md:156-158`).

**M3. "Stop capture" is red, unconfirmed and actually pauses.** It sends
`session.pause` (`app.mjs:684`) with danger styling and no confirmation.
Nothing ends a session. Spec: Stop opens a confirmation saying what is kept and
deleted; danger styling only inside a confirmation (`components.md:186-187`,
`components.md:141`).

**M4. Export is a modal that also deletes the session.** The only modal the
spec allows is a confirmation (`components.md:292`); "Delete this session" sits
inside "Export". Exporting takes two clicks (create, then download).

**M5. Opening a note's details zooms the whole canvas out to 45%**, leaving
the details unreadable ([13](ux-inventory/13-note-details-open.png)).

**M6. Wrong or missing reasons.** A mistyped invitation reports "Could not
reach the server" (`app.mjs:760`). Disabled controls (Start capture, Add,
Record sample, Propose group) give no reason beside them; Propose group's
reason is only a `title=` tooltip. Spec: a disabled control states its reason
(`components.md:143-144`); `title=` is not a tooltip (`controls.md:200`).

**M7. A person reviews their own grouping.** Grouping two notes the facilitator
already accepted takes five steps, the last being to accept their own proposal
([18](ux-inventory/18-group-proposed.png)). The provisional rule exists for
what a model made. *Question for the team:* should a person's own grouping
skip review, as dragging already does?

**M8. Inviting someone is slow and fragile.** The invitation is a 100-character
string with no copy button or QR code, under "Add", and the joiner also has to
type the server URL.

**M9. The transcript panel shows developer options.** "Also test the custom
wake-word detector", "Whisper originally heard", no gap rows for failed
transcription, and a scroller inside the scrolling rail. Spec: gaps are rows
(`patterns.md:67-69`), one scroller per screen (`forbidden.md:82`).

**M10. The start screen asks for a server URL** and gives Start and Join equal
weight, although most people will join ([01](ux-inventory/01-start-empty.png)).

### Minor

- The list view keeps the zoom controls, showing a disabled "25%" ([19](ux-inventory/19-list-view.png)); proposed groups appear only as a footnote line there.
- The reader is named in lower case ("Read by claude").
- The photo input is the browser's unstyled "Choose File".
- The canvas hint is cut off at 900 px high.
- Copy that differs from `copy.md:24-57`: "Start" (Start session), "Add" (Add note), "meeting" (session), "board" (canvas), "Processing", "unresolved".
- Accepting several items quickly gave one 409 Conflict in the console; cause not investigated.

## 3. What works and should stay

- **Provenance rendering**: dashed violet with a "Provisional" badge for model
  output, solid for accepted, a third look for typed but not reviewed. Clear
  at a glance and consistent across canvas, list and rail.
- **Note details**: who read it and with which model, confidence "on the
  model's own scale", the measured paper colour and the crop. Exactly the
  evidence the review card is missing.
- **Copy** that says what happens next and what still works ("Nothing new is
  being captured. The canvas and review still work.").
- Text can be corrected in the review card before accepting.
- A list view exists, and nothing scrolls sideways at 400 px.

## 4. Direction for the redesign

Ordered by what unblocks the most, for the team to choose from:

1. **Restructure around the meeting's flow: capture, organise, review.**
   The bar carries the two inputs ("Photograph the wall", "Listen") and an
   honest capture status; "Organise" becomes the step that turns captured
   material into structure (the proposal for Tuesday); review becomes a
   focused queue with the evidence in every card.
2. **Fix the honesty problems first** (C3, C4, M1's false success messages):
   they are small, and they contradict the product's own core rule.
3. **A full-width photo flow** with proposed boxes and a "what we found" step.
4. **Phone as a capture device**, per `touch.md`: shutter first, list by
   default, read-only board, 44 px targets.
5. **Layout on the canvas** by group and source, with paper colours, once the
   organise step produces groups.

## 5. Questions for the team

1. Who owns the redesign, and does it start before or after the organise step
   is agreed on Tuesday?
2. Should a person's own grouping go through review (M7)?
3. Is the phone a capture device for everyone in the room, or only the
   facilitator's camera?
4. Should Start and Join be one screen, given most people join?
