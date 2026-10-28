# Canvas layout

`dataviz.md` says how a cluster, a timeline, a matrix, a flow and a hierarchy
are **drawn**. `components.md` § 1 says what one item is **made of**. Neither
says where anything **goes**, and `grid.css` hands the question off in a
comment: "Free positioning lives in the application's own layout engine
(F3.3); this only establishes the surface and its edge."

This file is that layout engine's contract. It exists because F3.3's stated
risk is "ugly or overlapping layout destroys trust faster than a wrong summary
does", and because F3.4 says only what a new item must **not** do (never move
or overwrite a hand-placed item) and never says where it **does** go. A rule
phrased only as a prohibition is not implementable.

Everything here is measured in the existing `--spacing-*` rhythm. No new token
is proposed; see § 11.

Two definitions used throughout:

- **Hand-placed.** An item a person created, dragged, accepted or edited. Once
  a person touches an item, it is hand-placed for the rest of the session and
  F3.4 protects it permanently.
- **Model-placed.** An item the layout engine positioned that no person has
  touched yet. Provisional styling and model placement usually travel together
  but they are separate facts: a provisional item a person has dragged is
  hand-placed and still provisional.

---

## 1. Item sizing

### Width: three steps, not free

An item takes one of three outer widths:

| Step | Outer width | Used when the text is |
|---|---|---|
| Narrow | 160px | up to 24 characters |
| Default | 224px | 25 to 90 characters |
| Wide | 288px | more than 90 characters |

Reasons. A board of freely-sized boxes reads as ragged even when nothing
overlaps, and ragged is the exact failure F3.3 names. Three steps give the
board a rhythm without forcing every note to the same shape. The Wide step is
288px minus 2 × `--spacing-3` of padding minus 2 × `--line-provisional`, so
about 262px of measure, which at `--text-body` 14/20 Archivo is roughly 37
characters a line. That is deliberately short of the 45 to 75 characters that
suits running prose: a canvas item is a note, read in a glance from across a
room, not a paragraph, and a short measure means a fixed and predictable
number of wrapped lines. `--layout-reading-max` governs prose and does not
apply to items.

Layout dimensions are literals on purpose. `forbidden.md` exempts them: "Layout
dimensions are exempt: `width: 400px` ... are content decisions and are
allowed." All three sit on the 8px rhythm (20, 28 and 36 steps).

The character thresholds are measured on the rendered text, not on the source
string, so a note in Dutch with long compounds steps up correctly.

### Collapsed and expanded sizing, planned (F3.8)

The width steps above apply to the main point rather than the complete supporting
text. Legacy items without a separate main point keep their full text. Minimum
height remains 96px; grow to fit the complete main point, essential status,
source handle and disclosure control. Do not silently truncate the main point.

Expanding unfolds supporting detail downward in the same note at its current
width. Full text wraps, including long unbreakable tokens. No fixed-height clipping
or hover-only access. Long detail can extend the pannable surface; it does not
exclude an otherwise useful main point from the overview.

This supersedes the old provisional-text truncation ban, accepted eight-line
More rule and 24-line exclusion. Collapsing detail is permitted for overview,
but complete proposed content and evidence must be displayed in review before
Accept is available. This separates scanning from reviewing rather than asking
a person to accept hidden text.

See [expandable notes](expandable-notes.md) for the full interaction contract.
Expansion anchors, temporary local spacing, fixed-axis detail lanes and collapse
restoration are display geometry only. They never update saved positions.
These behaviours are planned, not implemented by the existing layout primitives.

### Items with no text yet

A `waiting` placeholder (F6.4) and an `unreadable` item (F1.6) take the
Default step at the minimum height, 224 × 96. They keep full size deliberately:
both are requests, and a request shrunk to fit its empty content is a request
nobody notices.

---

## 2. Separation

All of these are minimums measured between drawn edges, stroke to stroke.

| Between | Gap | Reason |
|---|---|---|
| Two items in the same form | `--spacing-4` (16px) | Two 1px dashed lines closer than this read as one texture at projector distance, and the board's job is to be legible in a glance. |
| An item and its own cluster hull | `--spacing-3` (12px) | The hull is the group's panel, drawn 12px outside the bounding box of its members: a `--color-surface-sunken` tone for an accepted group, a dashed accent line with no fill for a proposed one. Tight enough to read as containment, loose enough that a proposed hull is not mistaken for a second line on the outer items. |
| An item and a hull it does not belong to | `--spacing-5` (24px) | Twice the inside inset, so "beside the group" and "in the group" are distinguishable without reading the label. |
| Two forms (cluster to cluster, cluster to timeline, and so on) | `--spacing-7` (48px) | The gap between forms must be visibly larger than any gap inside a form, or the reader cannot tell where one claim stops and the next starts. 48px is the first token that is three times the within-form gap. |
| Any item and the board's edge | `--spacing-5` (24px) | The board has no frame, but an item touching the edge of the visible board reads as clipped even when it is complete. |
| Two items along a timeline spine | `--spacing-4` (16px) horizontally | Same reason as within a form. Ordering is carried by position on the spine, not by the size of the gap, so gaps are not proportional to elapsed time unless the content actually carried times. |
| An item and a flow or hierarchy connector it is not attached to | `--spacing-3` (12px) | A connector passing 4px from an item looks attached to it. |

No new token is needed for any of this. The candidate considered and rejected
was a placement lattice value: the 8px spacing rhythm already is the lattice,
and adding `--layout-canvas-grid: 8px` would name the same number twice.

---

## 3. Placement policy

Every new item has an **anchor**: one point on the board that says where it
belongs. Placement is then a deterministic scan outward from the anchor.

### Anchors by origin

| Origin | Anchor | Reason |
|---|---|---|
| **Speech** (F1.2, F2.1) | The form the content belongs to, taken as the last item placed in that form. If the model chose a form that does not exist yet, the anchor is the bottom-left corner of the bounding box of everything already on the board. If the board is empty, the anchor is the board's top-left inner corner plus `--spacing-5`. | Spoken content arrives in sequence, so it should land after what it follows, and a board fills the way a page fills. |
| **Photograph** (F1.4, F1.5, F1.6) | The whole photograph lands as **one block**, placed once, anchored at the bottom-left of the existing content. Inside the block, notes keep their relative positions from the wall, scaled to the three width steps and the § 2 gaps. | F1.5 keeps physical colour and proximity as grouping signal. Re-sorting the notes throws that signal away, and it is the only grouping evidence the photograph carried. A note that was top-left on the wall is top-left in the block. |
| **Command** (F2.5, F2.6) | The named selection. "Put those three on a timeline" builds the form at the bounding box of the three items. | The room said which items. Placing the result anywhere else makes the room hunt for what it just asked for. |
| **Typed input** (F1.7) | The board position the person's cursor last touched; from a phone, the same anchor as speech. | Typed input is a person's item. It is hand-placed from the moment it exists, drawn with a solid `--color-hairline-strong` line and no fill and the words "Not yet reviewed" until the room reviews it, and it never carries provisional styling. |
| **Live suggestion** (F2.8, Active mode only) | The item or form the suggestion is about. If it is about nothing in particular, it is not placed on the board; it goes to the rail. | An unanchored suggestion floating on a shared board carries authority it has not earned. F4.4 exists so the room can test this, not so the model can drift. |

### The scan

The board is a lattice of 8px cells. A candidate origin is any lattice point.
A candidate **collides** if the item's rectangle, grown on all four sides by
the § 2 minimum for that relationship, overlaps any item rectangle, any hull,
any spine, any connector or any label backing.

Candidates are ordered by cost and the first non-colliding candidate wins:

```
cost = euclidean distance from the anchor
     + 48  if the candidate's top edge is above the anchor's top edge
     + 96  if the candidate's left edge is left of the anchor's left edge
ties broken by smaller y, then by smaller x
```

Reasons. New material arrives after existing material, and in this product's
languages "after" reads as down and then right, so a bare distance metric that
put a new item above and to the left of its anchor would be placing a later
thing in an earlier position. The penalties are asymmetric because leftward is
the stronger violation of reading order than upward. 48 and 96 are the
`--spacing-7` and two-times-`--spacing-7` values used as cost weights, not as
distances, so the numbers stay in the system's vocabulary.

The scan is deterministic: the same board and the same anchor always produce
the same position. That matters for F6.5, because a layout that cannot be
reproduced cannot be evaluated, and for F3.7, because undo has to put things
back exactly.

### What the scan may never do

- **Automatic placement never moves a hand-placed item.** F3.4, without exception, including
  when a command names that item: a command may draw a form around hand-placed
  items and may connect them, and it may not reposition them. If the form
  genuinely requires a new arrangement, the model says so in the rail and asks
  (F2.6 already sends ambiguity to a confirmation rather than a guess).
- **It may reposition a model-placed item**, but only one that no person has
  touched and only within the same layout pass. Reason: otherwise the first
  guess of the meeting permanently owns the best space on the board, and every
  later, better-evidenced item is pushed to the margin. Anything moved this way
  is one undo step (F3.7).
- **It never animates existing items out of the way.** `interaction.md`:
  "Nothing moves on the canvas that the user did not move." A new item fades in
  over `--motion-base` at its final position and nothing else changes.

---

User-triggered F3.8 expansion is a narrow exception for temporary display
spacing, not automatic placement. It may offset neighbours locally, including
hand-placed notes, without changing their saved positions or semantic anchors.
No AI arrival may trigger this exception.

## 4. Collision

### The scan finds no free space

Spatially this cannot happen, because the addressable board is larger than the
viewport and grows in 320px increments in the direction of the scan (§ 6).
What can happen is that the first free position is **useless**: too far from
its own anchor to be read as belonging to it.

The rule: **if the winning candidate's origin is more than one viewport width
or height from the anchor, do not place it.** The item goes to the review queue
instead, and the board's edge affordance (§ 6) increments. An item placed a
screen away from its own context is not a visual conclusion, it is a lost item,
and F3.3's risk is trust rather than pixels.

### A person drags an item onto another

- **The item lands exactly where it was dropped.** No snapping away, no
  rejection of the drop, no reflow of the neighbours. F3.6 says the canvas is a
  real canvas; a canvas that argues with the person holding the pen is a
  render, not a board.
- **Overlap is permitted, and only ever between hand-placed items.** People
  stack things, cover things and half-hide things on purpose, and that is
  information. The model never creates an overlap.
- **The dragged item wins.** Board z-order, innermost to outermost: model-placed
  items, then hand-placed items, then the most recently touched item on top.
  This is a local order inside the board layer only. It does not touch the
  fixed page z-order in `patterns.md` (content 0, sticky headers 10, session
  bar 30, popovers 40, dialogs 50); the whole board is content 0.
- **Dropping onto a cluster joins it only if the item's centre falls inside the
  hull.** Overlapping the hull is not enough. A note nudged up against a group
  is beside the group, and guessing otherwise silently rewrites what the person
  meant.
- Joining or leaving a cluster re-draws the hull over `--motion-base`. The
  hull is the only thing that moves, because the hull is the only thing that
  changed.

### Snapping

While dragging, an item snaps to the 8px lattice and to the edges of items
within 8px. Snapping is to alignment only, never to a slot, and it is
suspended while `Alt` is held so exact placement stays possible. Reason: a
board where nothing lines up looks careless at projector distance, and a board
that forces things into slots is a diagramming tool rather than a whiteboard.

---

## 5. Label collision

### Two cluster labels

A cluster label is a label at the hull's top-left by default: inside the
panel for an accepted group, and on the dashed line on a `--color-canvas`
backing for a proposed one (`dataviz.md`). If two labels' backings
would overlap, the **later-created** cluster's label moves round its own hull,
tested in this order: top-left, top-right, bottom-left, bottom-right.

If all four positions collide, the two clusters are too close to both be named.
That is not a label problem, it is a § 2 problem: increase the between-form gap
to `--spacing-7` and re-run the scan for the later cluster. Two groups that
cannot both carry a name are either one group or they are badly placed, and in
both cases the fix is upstream of the label.

A label is never rotated, never drawn at an angle and never shrunk below the
label size. `typography.md`: nothing renders below 12px.

### A label longer than its item or hull

- **Cluster labels wrap to two lines at the label size, then truncate with an
  ellipsis.** The full text is the element's accessible name and its title.
  Truncation is allowed here, unlike on an item, because a cluster label names
  a group whose members are visible directly beneath it: the evidence for the
  name is on screen. An item's text is the evidence.
- A label never grows the hull. Sizing a group to fit its name makes the
  group's size mean nothing.
- A label longer than 48 characters is a sentence, not a name. The model
  shortens it and the full text moves to the cluster's meta line.

### Dense timeline ticks

- **Ticks are always all drawn.** A tick is a data point.
- **Tick labels thin out.** Keep the first label, the last label, and every
  nth in between such that no two label boxes are closer than 44px. 44px is the
  touch target minimum already used across the system, and it is comfortably
  above the width at which two labels read as one string.
- Labels are never rotated. Rotated type at projector distance is unreadable,
  and there is no rotated type anywhere else in this product.
- **Tick labels sit below the spine.** `dataviz.md` puts items above the spine
  with a 1px drop line, so labels below the spine cannot collide with an item
  or with a drop line, at any density.
- If thinning leaves only the first and last labels and the ticks still touch,
  the timeline holds too many points for its width: it widens on the
  addressable board rather than compressing, and § 6 pan makes the rest
  reachable.

---

## 6. Overflow past the board edge

### The choice: pan

The board pans. It does not scroll and it does not reflow.

- **Reflow is unavailable on this board, permanently.** Reflowing means moving
  items when the viewport changes size, and the items it would move include
  hand-placed ones. That is F3.4 broken by the layout engine itself, which is
  the one thing F3.4 exists to prevent.
- **Scroll is wrong for the content.** A scrollbar says there is a top and a
  bottom and a reading order down the page. The board's meaning is relative
  position in two dimensions with no origin. A scrollbar also lives at the very
  edge of the frame, which is exactly where a projector crops and where nobody
  in the room is looking.
- **Pan is what the product already assumes.** The architecture describes the
  canvas renderer as "live, multi-user, pan and zoom", and `patterns.md`
  already says the board below 1024 is pannable. This makes that consistent
  above 1024 rather than adding something new.

`.jv-board` keeps `overflow: hidden` exactly as written in `grid.css`. The
board element is the viewport; panning is a transform on an inner layer inside
it. **No change to `grid.css` is required by this file.**

Mechanics: space-drag, middle-button drag, two-finger trackpad. Arrow keys pan
by 64px, `Shift` plus arrow by 320px. No inertia and no rubber-band bounce.
Momentum panning on a shared screen makes the room seasick and makes it hard
for a facilitator to land precisely on the thing they are talking about.

### The edge, without a shadow

Shadows belong only to surfaces that float above the page, and the board is
the page, not something above it; gradients are forbidden outright. So the edge
is built from vocabulary that already exists: a tick and a label on a
`--color-canvas` backing, which is exactly how a proposed cluster's label sits
on its hull.

On each edge that has content beyond it:

- **Ticks.** A 1px `--color-hairline-strong` tick, 8px long, drawn inward from
  the board's edge at the cross-axis centre of each off-screen item, clamped to
  the edge's length and capped at 12 ticks. Same tick vocabulary as a timeline.
  The ticks say how much is out there and roughly where.
- **A label** in `--color-ink-muted` on a `--color-canvas` backing, sitting at
  the midpoint of that edge, reading the count and the direction in sentence
  case: "4 more" with a 16px inline arrow. On a coarse pointer and in room
  mode the label's hit area is 44px tall, via `.jv-hit`.
- **The label is a real `<button>`** in tab order. Activating it pans to the
  nearest off-screen item and gives it selection. That is currently the only
  way a keyboard user finds off-screen content, which is a mitigation, not a
  solution, and it belongs on the list of honest limitations the README already
  keeps about the board and the keyboard.
- Ticks and label appear and disappear over `--motion-fast`. They are never
  animated otherwise and they never pulse.

### Above and below 1024

- **Above 1024** (the room screen and the facilitator's laptop): pan as above,
  plus zoom, plus direct manipulation (F3.6).
- **Below 1024**: `patterns.md` says the board is "read-only and pannable".
  That stands and this file adds two things to it. One-finger drag pans, since
  nothing on the board is draggable at this width and the gesture is free.
  Pinch zooms, snapping to the nearest level on release (§ 7). The board opens
  at **Fit**, not at 100%: a phone in this product is a viewfinder onto a board
  built on the room screen (F1.4), and opening at 100% in an arbitrary corner
  of someone else's board is disorienting.
- Edge ticks and the edge label are identical at both widths. The affordance
  should not have to be relearned when the same person picks up their phone.

---

## 7. Zoom

**Zoom exists.** Four discrete levels, no continuous zoom:

| Level | Scale | Keyboard |
|---|---|---|
| Fit | computed, clamped to 25% to 100% | `0` |
| Half | 50% | `-` from 100% |
| Actual | 100% | `1` |
| Close | 150% | `=` from 100% |

Discrete rather than continuous because a shared screen needs a size two people
can agree on and return to. "Put it back" is one keystroke; from continuous
zoom it is a negotiation. Pinch and trackpad zoom are continuous under the
finger and snap to the nearest level on release.

The control is a quiet button in the session bar showing the current level,
opening a popover listing the four levels with their shortcuts as labels. It is in the session bar and not over the board, because a floating
canvas toolbar is forbidden in `patterns.md`. Shortcuts are shown rather than
hidden in a help modal, per `interaction.md`.

### What scales and what does not

- **Geometry scales.** Positions, item sizes, hull shapes, spine lengths. This
  is a CSS transform, which `forbidden.md` explicitly permits as a computed
  value, so no arbitrary font size or dimension is introduced and no audit
  finding is created by it.
- **Strokes do not scale.** `--line-boundary`, `--line-provisional` and
  `--dash-provisional` are drawn in screen space at every level
  (`vector-effect: non-scaling-stroke` on SVG strokes). At 50% a scaled 4 4
  dash becomes 2 2 and reads as a solid line at projector distance, which
  would erase the single distinction the whole system exists to make. The
  provisional distinction survives zoom or zoom does not ship.
- **Type never renders below its token size.** `typography.md` makes the 12px
  floor a hard rule, so type is not scaled down; roles drop out instead, in a
  stated order. Room mode is a different thing: it scales every size up by 1.5
  before any zoom applies, so at 50% zoom in room mode a label is still 18px.

### Type by role, per level

| Level | Label (kind line, cluster label) | Body (item text) | Meta (source, time, confidence) |
|---|---|---|---|
| 150% | scaled | scaled | scaled |
| 100% | as specified | as specified | as specified |
| 50% | **kind tab not drawn**; a cluster label stays, at its unscaled 12px | drawn at unscaled `--text-body`, first line only | not drawn |
| Fit below 50% | not drawn | not drawn | not drawn |

Display, heading, title and figures do not appear on the board at all. Every
figure in this product lives in the session bar or a panel head, neither of
which zooms, so there is no row for them.

At **50%** an item is its fill or its line, its badge glyph, and one line of
its text at full size: a **reduced item**. The line keeps its true width and
dash and the fill keeps its tone, so proposed versus accepted is still
readable. The kind line and the meta line would have to render below the 12px
floor, so they are not drawn at all rather than drawn illegibly.

That one line of text is clipped at the item's scaled width, and clipping text
on a provisional item is exactly what § 1 forbids. The resolution:

> **Accept is disabled at 50% and at Fit below 100%.** The button carries its
> reason beside it: "Zoom in to accept." Reduced items are for finding your way
> round the board, not for reviewing it.

This uses the existing rule from `components.md` § 4, that a disabled control
states its reason, rather than inventing anything. It also keeps § 1 intact: a
provisional item's text never truncates **in any view where it can be
accepted**.

At **Fit below 50%** an item is a mark: a 16px square at `--radius-xs` carrying
the item's own form, a tonal fill, a solid line or a dashed line, and nothing
else. The board shows a label counting what is on it. Below 50% nothing on an item is readable, and
drawing unreadable text is a claim that it could be read.

Fit is clamped at 25% at the bottom. Below that, marks are smaller than the
8px lattice and the board becomes texture. 25% is a guess. **Test:** project a
board of 40 items at 25%, 20% and 15% and ask a reader to count the dashed
items. The floor is where that count stops being reliable.

---

## 8. Density limits

All three numbers below are guesses. They are stated as numbers anyway,
because "as many as look right" is not implementable, and the test for each is
given.

### Items per cluster: 9

Above 9 items a hull stops reading as a group and starts reading as a region.
9 is three rows of three at the Default width step, which occupies roughly half
a 1280 × 800 board at 100%.

Above 9, the model sub-divides into sub-clusters or re-runs form selection
(F3.2). It does not simply keep adding. If it cannot find a sub-division, the
cluster is over-broad and its label is a guess, which is the F3.2 failure mode
that `dataviz.md` already names: "a cluster of everything is a list with extra
steps."

**Test:** project clusters of 6, 9, 12 and 15 at 4 metres and ask a reader to
name the group in one phrase. The limit is where the naming slows down or the
answers stop agreeing.

### More than 24 items in one form becomes a list

Above 24 items the model does not draw the form. The content goes to the rail
as a review-queue entry carrying one sentence: "Too many items to lay out. 31
notes from this photograph are in the queue." A person then accepts them in
batches and the board fills at the pace a person can follow.

Reason: 24 items in one hull is a list that has been drawn badly, and it is
also 24 dashed strokes arriving at once, which turns the board into the colour
field that `components.md` § 1 is written to prevent.

**Test:** the same projected naming test at 16, 24 and 32 items.

### About 40 items on the board before auto-placement stops

At 100% on a 1280 × 800 board with the § 2 gaps, roughly 40 Default-width
items fill the viewport. Above that the model stops auto-placing **new forms**
and queues them instead. Existing forms keep receiving items.

The board itself does not stop working, it pans. But a board that cannot be
taken in from across the room has stopped being a shared screen, and the whole
premise of this product is a thing the room glances at.

**Test:** count items on the board at the point in a real session where people
stop looking up at it.

---

## 9. Degenerate cases

**A cluster of one.** No hull is drawn. One item is not a group, and a hull
round one item makes a grouping claim the content does not support. If the
model produced a label for it, that label becomes the item's kind line, a label.
A cluster of one is also a signal that form selection (F3.2) went wrong, and it
is logged as such for F6.5.

**An empty matrix quadrant.** The quadrant stays, drawn, with its label
corner label, holding nothing. An empty quadrant is a finding: nothing scored
high on both axes, and that is frequently the most useful thing a matrix says.
Never re-scale the axes to hide it, never redraw the matrix as a list, never
shade it. `dataviz.md` already forbids quadrant fills because shading is a
judgement the tool does not get to make; deleting half the claim because it is
empty is the same judgement made by omission.

**A timeline with two points.** Draw it. Two points is a legitimate before and
after. The spine does **not** run the width of the board: it spans the two
items plus `--spacing-5` at each end. A spine longer than its content implies a
duration nobody stated. With exactly two points and no stated interval, the
ticks carry the two labels and no times, because inventing an interval is
inventing data.

**A form the model proposed that turns out to hold nothing.** It depends who
asked.

- If the form came from a **command** (F2.5, F2.6), the room asked for it and
  is waiting. The failure is shown in the side panel with the `failed` glyph and one
  sentence naming what was attempted: "Could not build a timeline from those
  three. None of them carried a time." Never a silent nothing: the room is
  looking at the board expecting a change.
- If the form was the model's **own idea** (F2.8, Active mode), it is dropped
  in the layout pass and nothing is shown. Principle 6, "never a silent gap",
  is about content the room produced, not about the model's own discarded
  scaffolding. Reporting every abandoned idea is noise dressed as honesty.

**An item whose handwriting could not be read** (F1.6) keeps the full Default
size, 224 × 96, with the photograph crop and an empty field. It is a request
for help and shrinking it to fit its empty content hides the request.

---

## 10. Deliberately not specified

Listed so the next reader can tell a decision from an oversight.

- **Simultaneous drag by two people** (F4.2). Two people dragging the same item
  is a synchronisation problem, and specifying a visual for a conflict before
  the sync model exists would be inventing a resolution rule in a layout file.
  Named as open.
- **Tidy-up or auto-arrange of a board a person has arranged.** Absent on
  purpose, and it should stay absent: a Tidy button that moves hand-placed
  items is F3.4 broken with a friendly label on it.
- **Connector routing round obstacles** in flows and hierarchies. `dataviz.md`
  specifies 1px orthogonal connectors and says nothing about what happens when
  one must cross an item. Interim rule, so implementation is not blocked:
  connectors pass **under** items, never round them and never over them. A
  connector that detours implies a relationship the detour invented, and a
  connector drawn over an item hides content. Proper routing is open work.
- **Item aspect ratio for a photograph crop placed on the board** rather than
  in a meta line. Not needed by any of the five screens yet.
- **Keyboard traversal of the board.** The README already carries this as an
  honest limitation. The edge-label button in § 6 is one small step, not a
  solution, and it should not be read as closing the gap.
- **Layout for a printed board** beyond `grid.css`'s `break-inside: avoid`.
  F5.1 exports a rendered board; how a board wider than a page is paginated is
  an export question, not a layout one.
- **Densities and sizes at 4K or at a wall display.** One breakpoint, and this
  system already states that the tablet case is unhandled for the same reason.

---

## 11. Tokens

No new token is proposed by this file. Everything above binds to existing
names: the `--spacing-*` rhythm for every gap, `--color-hairline-strong` for
edge ticks, `--color-canvas` for label backings, `--color-surface-sunken` for an
accepted group's panel, `--color-ink-muted` for the
edge label, `--line-boundary` and `--line-provisional` and `--dash-provisional`
for strokes that must not scale, `--radius-xs` for a mark at Fit,
`--motion-fast` for the edge affordance and `--motion-base` for a hull
redrawing.

Two candidates were considered and rejected:

1. `--layout-canvas-grid: 8px` for the placement lattice. Rejected: the
   spacing rhythm is already 8px and naming the same number twice invites the
   two to drift apart.
2. A zoom-level set as tokens. Rejected: zoom levels are scale factors applied
   as transforms, which `forbidden.md` treats as computed values, not as design
   values that the system needs to hold constant.

The three item widths, the 96px minimum height, the 44px label spacing and the
64px and 320px pan steps are layout dimensions, which `forbidden.md` exempts
from the literal ban. All sit on the 4px rhythm.

---

## 12. What this file contradicts or supersedes

Stated explicitly so the integration is not left to be discovered.

1. **The `.jv-board` comment in `grid.css`**: "Free positioning lives in
   the application's own layout engine (F3.3); this only establishes the
   surface and its edge." Still true of the CSS. No longer true of the system:
   this file is that engine's contract. **No CSS change is required**, because
   pan is a transform on an inner layer and `overflow: hidden` is what makes
   the board a viewport rather than a clipper.
2. **`.jv-board { overflow: hidden }`** previously meant, in practice, that an
   item past the edge was silently lost. It now means the board clips its
   viewport while the content pans inside it, with § 6's ticks and label saying
   there is more. Same declaration, a different guarantee behind it.
3. **`patterns.md` § 1**, "the board is read-only and pannable" below 1024, is
   extended rather than changed: pinch zoom is added, and the board opens at
   Fit rather than at 100%.
4. **`components.md` § 1** gives the canvas item its anatomy and no size. § 1
   of this file gives it a size. Nothing in the anatomy changes.
5. **`components.md` § 1 rule 4**, "a provisional item never moves or
   overwrites anything the team placed by hand", is unchanged and is now backed
   by an algorithm in § 3 rather than by a prohibition alone.
6. **`dataviz.md`**, timeline: items sit above the spine. This file adds that
   tick labels sit below it, which is new and does not conflict.
7. **`dataviz.md`**, cluster: the hull. This file adds that a cluster of one
   has no hull, and gives the hull its 12px inset.
8. **`typography.md`**, the 12px floor, is not breached at any zoom
   level: a label stops being drawn rather than shrinking. § 7 states this as a
   rule so nobody implements a scaled label and calls it zoom.
9. **`forbidden.md`** rule 2, no arbitrary font sizes, is not breached by zoom.
   Zoom is a transform, which rule 5 permits as a computed value. Written down
   here so it is not filed as an audit finding.
10. **`interaction.md`**, "nothing moves on the canvas that the user did not
    move", constrains § 3: a new item appears at its final position and existing
    items do not slide. The one exception this file introduces is the
    re-positioning of untouched model-placed items inside a single layout pass,
    which is stated in § 3 and is one undo step (F3.7).
11. **The README's honest-limitations list** gains one entry this file cannot
    add itself: the board's numbers in § 1, § 7 and § 8 are reasoned guesses
    that have not been tested on a projector in a room. Each carries its test.
