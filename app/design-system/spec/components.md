# Components

Anatomies. This file describes what each component is made of, in tokens, so
that two people building the same component separately end up with the same
thing. Nothing here is a code snippet to paste; it is the contract the code has
to meet. `exemplars/_base.css` is the browser implementation of these
anatomies.

Order: the canvas item first, because it is the component this product is
actually about. Everything else after.

Two rules run through every anatomy below, and each carries its reason here
once:

- **Never a fill and a line on the same element.** A surface is told apart by
  tone or by a line. Both together say the same thing twice and read as a box
  drawn on the page.
- **Only floating surfaces have a shadow.** Menus, popovers, the dialog and the
  session bar once the page scrolls. A shadow says "this is above the page and
  will go away", which is false of everything in the page.

---

## 1. Canvas item

The single most important component in Jarvaids. It is a thing on the board: a
sticky note read from a photograph, a decision extracted from speech, a typed
note, a cluster label, a timeline marker.

**The one distinction the whole design system exists to make: did the team
make or agree this, or did the model propose it?** Get this wrong and nothing
else matters.

There are three provenance states, and each uses exactly one instrument:
a tone, a dashed line, or a solid line.

### Accepted

```
fill          --color-surface-sunken            (a TONAL FILL)
line          none
radius        --radius-md
padding       --spacing-3
kind line     label, --color-ink-muted, above the text
text          body, --color-ink
meta line     meta, --color-ink-muted: source and time
```

A tonal fill and no line. It looks settled, because it is: it has joined the
page. The fill is the ground one tonal step down, never a status colour.

### Provisional: model-made, not yet accepted

```
fill          none
line          --line-provisional (1px) DASHED --color-status-provisional
              (the accent); --dash-provisional (4 4) in SVG
radius        --radius-md
padding       --spacing-3
badge         top of the note, inside it: the dashed-ring glyph and the word
              "Proposed", label, in --color-status-provisional
text          body, --color-ink            ← full strength, NOT greyed
meta line     meta: what it came from, and its confidence if the model has one
actions       Review · Edit · Reject on the collapsed overview
              Accept (primary) · Edit · Reject in full-content review
              always reachable by keyboard and visible on touch
```

Four rules that are easy to get wrong:

1. **The dash is the primary signal**, not the colour. The provisional colour
   is the accent, so colour cannot tell a provisional note from an accent
   button at all; the dash, the dashed-ring glyph and the word "Proposed" do.
   They survive colour blindness and a projector washing out.
2. **The text is not greyed out.** A provisional item is unreviewed, not
   unimportant. Greying it makes it harder to read, which makes it harder to
   review, which is the opposite of the goal.
3. **No fill.** A provisional note sits directly on the ground. A fill would
   make it look settled, and a fill plus the dashed line would be two
   instruments on one element.
4. **A provisional item never moves or overwrites anything the team placed by
   hand** (F3.4). Violating this once loses the room permanently.

### A person's typed note, not yet reviewed

```
fill          none
line          --line-boundary (1px) SOLID --color-hairline-strong
radius        --radius-md
padding       --spacing-3
word          "Not yet reviewed", meta, --color-ink-muted
text          body, --color-ink
```

A solid line and no fill. A person made it, so it is never drawn like model
output; the team has not agreed it yet, so it is not drawn as accepted. The
solid edge is `--color-hairline-strong` at 3.41:1 because it carries meaning
(1.4.11). It takes no status glyph: it is not one of the six statuses, it is a
person's own work waiting for the room.

### The other three states

| State | Line | Badge | When |
|---|---|---|---|
| **Waiting** | 1px dashed `--color-status-waiting` | half-filled ring + "Queued" | The model is behind and this item is a placeholder for something coming (F6.4). It has a size and a position but no content yet: skeleton lines in `--color-surface-sunken`. |
| **Unreadable** | 1px dashed `--color-status-failed` | ring with a bar + "Unreadable" | The handwriting could not be read (F1.6). The item shows the photograph crop and an empty field ready to be typed into. It is a request for help, not an error message. |
| **Selected** | the item's own state, plus a `--line-focal` 2px `--color-accent` ring at 2px offset | unchanged | Direct manipulation (F3.6). Selection is the accent because selecting is an action. |

Selected and provisional compose: a selected provisional item has a 1px dashed
accent line *and* a 2px solid accent ring outside it. They are the same hue,
so they are told apart by weight, by style and by the 2px gap between them,
never merged into one line.

### Photograph provenance

An item read from a photograph keeps a source handle when collapsed (F1.5,
F1.6), with its crop and source access in the expanded detail or full review.
The photograph stays attached for the life of the session so a bad read can be
checked against the original rather than argued about.

**The paper colour is a small swatch on the note, never its fill.** The
colour is evidence of where the note came from, so it is shown, small, beside
the source handle. As a fill it would put a second hue on the screen and make
two notes on two papers look like two kinds of thing.

### Expandable notes, planned (F3.8)

Content items use the [expandable-note contract](expandable-notes.md): a
concise main point with essential status and source handle when collapsed,
supporting detail and evidence in the same note when expanded. The provenance
states above apply in both views. The planned topic fills in that contract
conflict with the one-hue rule; until it is revised, topic is carried by the
group label and the group panel, never by a note fill. Current exemplars
remain baseline screens; this behaviour is not yet implemented.

---

## 2. Status glyph

```
size        16px, shaped, in the status colour (currentColor)
gap to word 6px
word        label, 12/16 weight 500, in the status colour
```

| Status | Glyph |
|---|---|
| capturing | a filled disc, beside a running timer |
| provisional | a dashed ring |
| accepted | a ring with a tick |
| waiting | a half-filled ring |
| failed | a ring with a bar |
| off | a pair of bars |

**Always a glyph and a word.** There is no glyph-only status, no colour-only
status, no status carried by a row's background. The six shapes are distinct
in greyscale, which is the test: print the strip without colour and every
status must still be nameable. The glyphs are drawn at a 1.5px stroke, the
same as the system's icons, because a 1px ring at 16px breaks up on a
projector.

The capturing glyph does not pulse. It used to; nothing in this system loops
any more, because a looping mark in the corner of a room screen pulls every
eye in the room to it every two seconds. The disc, the word "Recording" and the
running timer carry the state on their own.

## 3. Status chip

A glyph plus a word on the status's own wash, for when a status needs to be
found rather than read.

```
background  --color-status-*-wash
text        --color-status-*, label
padding     --spacing-1 --spacing-2
radius      --radius-full
```

Chips are for list rows and item badges. Never more than one chip per row.

---

## 4. Buttons

Four variants. One primary per view. At a desk a control is `--target-desk`
32px; in room mode and on a coarse pointer it is `--target-room` 44px. A form's
primary action may be large, 40px (48px in room mode). A compact item action is
28px at a desk and 44px on touch or in room mode. Never interleave heights in
one row.

| Variant | Anatomy | For |
|---|---|---|
| **Primary** | `--color-accent` fill, `--color-ink-inverse` label, no line, `--radius-sm`, weight 500 | The one main action in a view: Start session, Accept, Export. |
| **Secondary** | `--color-ink-wash` fill, `--color-ink` label, **no line**; hover `--color-ink-fill` | The action beside the primary one. |
| **Quiet** | no fill, no line, `--color-ink-secondary` label; hover `--color-ink-wash` | Actions in a row: Edit, Reject, Dismiss. It has a hit area; it is not a bare text link. |
| **Danger** | quiet, with a `--color-status-failed` label; hover `--color-status-failed-wash`. A failed **fill** only inside the confirmation dialog | Only for the irreversible: End session, Delete session. |

- Secondary is a tone, not an outline: a filled button with a border is a fill
  and a line on one element.
- Disabled: `opacity: 0.45`, `cursor: not-allowed`, and **the reason is stated
  next to it**. A disabled button with no explanation is a dead end.
- Every button has a focus ring. Removing it is a WCAG 2.4.7 failure.
- Buttons press: `transform: scale(0.97)` on `:active`, over `--motion-fast`.
  Transform only, so it never shifts the row.

## 5. Form field

One anatomy. There is no second field style.

```
line         --line-boundary solid --color-hairline-strong   ← 3.41:1, 1.4.11
fill         none
radius       --radius-sm
height       40px at a desk, 44px on a coarse pointer
padding      0 --spacing-3
text         body; 16px on a coarse pointer (touch.md § 3)
label        label above the field, --color-ink-secondary, sentence case,
             always a real <label>
hint         meta below, --color-ink-muted
```

A field is the one place a line marks an edge: it is a place you type into,
and an edge you can type into must be seen.

States:

- hover: line `--color-ink`
- focus: the 2px accent ring from `grid.css`, line stays
- invalid: line `--color-status-failed`, **only after the field has been
  touched**, never on an idle empty field
- disabled: `opacity: 0.45`

Placeholders are not labels. A field without a visible label is a field that
becomes unlabelled the moment someone types in it.

## 6. Session bar

Sticky to the top of every screen where a session is live. At least 56px tall.

```
fill        --color-surface-float
shadow      --elevation-sm, once the page scrolls under it
line        none

[capturing glyph + "Recording" + timer (figure, tabular)]  ·  [mode segmented:
Quiet | Active]  ·  [N present]  ·  [spacer]  ·  [Undo]  ·  [Consent record]  ·
[End session]
```

- Never scrolls away, never collapses to an icon, never hides (F1.1, F6.1).
- It floats, so it is white with a shadow, not a line under it: the shadow
  appears only when content passes beneath, which is the one moment the bar is
  actually above something.
- When capture is paused the glyph is the off pair of bars, the word is
  "Paused", and the timer stops. The bar stays.
- **Undo is here, always** (F3.7), as a quiet button. It is the session-wide
  half of undo; the other half is in place on the row that changed.
- "End session" opens the confirmation (§ 14), stating the consequence in one
  sentence and one detail line: what is deleted, what is kept (F6.6).

## 7. Segmented control

Switches between views of the same content. Never for navigation, never for
multi-select.

```
track     --color-ink-wash fill, no line, --radius-sm, 2px padding
option    --radius-xs, body, target height minus 4px
chosen    --color-ink fill, --color-ink-inverse label, weight 500
```

Chosen is ink, not accent. **Action is accent, state is ink.** A selected
segment is a state.

## 8. Tabs

Navigation between sections. Underline, not a pill.

```
tab        body, --color-ink-secondary, target height
chosen     --color-ink label, weight 500, 2px --color-ink underline
row        sits on a 1px --color-hairline, and IS the section's separator
```

The chosen tab is a state, so its underline is ink, not the accent. The tab row
is the hairline under the page head. Do not draw a second one.

## 9. Row list

`.jv-rows`. The default way to show a list of anything.

```
row       padding-block --spacing-3, border-bottom 1px --color-hairline
last row  no line
hover     --color-ink-wash, only if the row is interactive
selected  --color-accent-wash, and no line
```

- Selected is a tint and nothing else: a tint plus a left border would be a
  fill and a line on one element.
- An expandable row is a `<button>` spanning the row, and detail opens inline
  below it. Never in an extra column, never in a modal.
- **Undo is in place.** A row that a person or the model just changed offers
  Undo on the row itself, for as long as the change is the latest one, as well
  as in the session bar. This is what replaces a toast.
- **Rows are body text** except for machine fields. Rule T2 in
  `typography.md`.
- Column headers are labels, in the header once.

## 10. Transcript line

A row list with a fixed anatomy, because it is the densest thing in the
product.

```
[timestamp: figure, tabular, accent, clickable]
[speaker: body 500, or muted with a dashed-ring glyph and "Speaker is a guess"
 if uncertain (F1.3)]
[the line: body, .jv-prose]
```

- The currently-playing line carries `--color-accent-wash`, and no line.
- A gap the model could not transcribe is its own row: the failed glyph, the
  word "Gap", and the time range. Shown, never skipped.
- Search matches are marked with `<mark>` on `--color-accent-wash`, not a
  colour change on the text.

## 11. Answer panel

Where the model answers a question asked mid-meeting (F2.7).

```
[the answer, body, .jv-prose]
[hairline]
[label "From"] [citation timestamps, figure, accent, clickable]
```

**An answer without citations does not render.** If the model cannot point at
a moment, the panel shows one sentence instead: "I cannot find that in this
session." A confident wrong answer mid-meeting costs more than no answer.

## 12. Consent row

One per person present (F6.1).

```
[name, body] [spacer] [status glyph + word: Agreed / Not yet / Withdrawn]
[time agreed, meta muted]
```

Agreement comes before capture: nothing is recorded until every person present
has agreed. Withdrawal is one click, takes effect immediately, and is logged.
There is no confirmation on withdrawing consent: adding friction to someone
withdrawing consent is the wrong side to put friction on.

## 13. Degradation banner

A hairline row, not a toast, not a modal (F6.4).

```
border-bottom 1px --color-hairline
padding --spacing-3 0
[status glyph + word] [one sentence, body] [optional quiet action]
```

- `waiting` for degraded: "The model is about 40 seconds behind. Capture is
  still running." Capture continuing is the important half of that sentence.
- `failed` for blocking: "Transcription has stopped. Audio is still being
  recorded." Again, what still works comes second, in the same sentence.

Never a spinner, never a full-screen block, never silent. The meeting does not
stop.

## 14. Confirmation dialog

**The only modal in the product.** Used for exactly two things: **End
session** and **Delete session**. Both are irreversible, and Undo cannot reach
them.

```
fill      --color-surface-float
shadow    --elevation-lg
radius    --radius-lg
padding   --spacing-5
width     at most 480px, and the viewport minus 32px
backdrop  ink at 40%

[title, the title role]
[one sentence of consequence, body]
[one detail line, meta muted]
[Cancel (secondary)] [the action (danger, filled)]
```

Not used for: rejecting an item, rejecting a cluster, removing an item,
pausing capture. Each of those is reversible with Undo, in place on the row
and in the session bar, and a confirmation on a reversible action trains people
to click through the confirmations that matter.

Escape closes. Focus is trapped and restored. Overlays never stack.

## 15. Empty state

One sentence, meta muted, naming the next action. That is the entire
component. No illustration, no heading, no button unless the action is
genuinely one click away.

## 16. Skeleton

`--color-surface-sunken` blocks mirroring the real layout, on first load only.
**They do not pulse or shimmer**: a still block says "coming" as clearly as a
moving one and does not pull the room's eye. Never used for a refresh of
already-visible content: content that flickers to skeleton and back reads as a
bug.

---

## 17. Group panel

A cluster of notes on the canvas, or a group of related controls in a rail.

```
fill        --color-surface-sunken
line        none
radius      --radius-md
padding     --spacing-3
heading     label or title, above the members, inside the panel
```

Tone groups, so the panel draws no border. **Open question:** an accepted note
is also `--color-surface-sunken`, so an accepted note inside a group panel has
no tonal step of its own. Until that is decided, inside a panel the accepted
note is told apart by the space around it and by the absence of a dashed or
solid line; do not add a border to it to compensate, which would break the
fill-or-line rule.

## 18. Side panel

The rail beside the canvas, `--layout-rail` 384px. **Non-modal.** It does not
trap focus, it does not dim the canvas, and the canvas stays operable while it
is open, because the meeting goes on while someone reads the transcript.

## 19. Menu and popover

Floating surfaces.

```
fill      --color-surface-float
shadow    --elevation-md
radius    --radius-md
line      none
padding   --spacing-1 (menu), --spacing-3 (popover)
```

They float, so they carry a shadow and no line: a border around a white panel
over a near-white ground is a box, and the shadow is what says the panel is
above the page and will close. Anatomies and behaviour are in `controls.md`.

---

## Deliberately not in this system

Listing these so nobody spends a day building one and then has it rejected.

- Cards with shadows in the page. A note is a tonal fill or a line, never a
  card floating above the canvas.
- Toasts. State changes are shown where the thing is, and Undo is in place on
  the row and in the session bar.
- Modals for anything except the confirmation dialog. Export is a page, not a
  modal; the side panel is non-modal.
- A floating canvas toolbar. Item actions live on the item.
- Bulk accept. See `patterns.md`.
- Drag-to-reorder in list views. The canvas is the place where things move.
- An avatar photograph. People are initials in an `--radius-sm` square on
  `--color-surface-sunken`, label.
- Dark mode. See `forbidden.md` for why, and what it would take.
