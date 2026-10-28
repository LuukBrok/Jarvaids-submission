# Page patterns

Jarvaids has five screens. There are four page shapes, because session setup and
export share one. Pick the shape that matches the job. Do not invent a fifth
without proposing it.

Every shape is built from the primitives in `../grid.css`. A screen never adds
its own horizontal padding, its own max-width wrapper, or its own breakpoint.

---

## 1. Live canvas: `.jv-workspace`

The product. Exemplar: `exemplars/live-canvas.html`.

```
[session bar: capturing glyph + timer + mode + Undo + consent]   ← always visible,
                                                                     floats, white
.jv-workspace
├── .jv-board          the canvas itself (F3.1, F3.3, F3.6)
└── side panel (384)   transcript, or review queue, or nothing; non-modal
```

- **The session bar is not optional and does not scroll away.** It carries the
  capturing indicator (F1.1), the elapsed timer, the mode (Quiet or Active,
  F4.4) and a link to the consent record (F6.1). A recording indicator that
  can be hidden is a consent failure, not a layout preference.
- **The board is the page's own ground**, `--color-canvas`, with no frame
  around it, so it reads as the place the work is and not as a box inside a
  page. Groups on it are `--color-surface-sunken` panels; accepted notes are
  the same tone; provisional notes are dashed accent outlines with no fill.
- **The side panel is one thing at a time**, switched by a segmented
  control: Transcript, or Review (N). Never two stacked scrollers. It is
  **non-modal**: it does not trap focus or dim the canvas, because the meeting
  goes on while someone reads it.
- Below 1024 the rail stacks under the board. On a phone this screen is mostly
  the photograph button and the typed-input box (F1.4, F1.7); the board is
  read-only and pannable.
- **Deliberately not in the system**: a floating toolbar over the canvas, a
  minimap, a right-click context menu. Canvas item actions live on the item.

Planned F3.8 adds collapsed sticky-note main points and in-place detail to this
canvas. Read-only on a phone still permits expansion, since it changes no shared
content. Current exemplars remain baseline screens. See [expandable notes](expandable-notes.md).

## 2. Session and transcript: `.jv-workspace`, rail wide

Exemplar: `exemplars/session-transcript.html`.

The same shape, used when the transcript is the subject rather than the
sidekick: reviewing what was said, asking a question of the session (F2.7),
checking a citation.

```
[h1 → hairline]
[ask row: one input, full width]
.jv-workspace
├── transcript (.jv-rows, .jv-scroll)   timestamp · speaker · line
└── rail: answer panel with citations
```

- **A transcript line is: timestamp (figure, tabular, clickable, accent) ·
  speaker (body 500) · the line (body 400).** Rule T2 applies: the timestamp
  is the only figure in the row.
- **Speaker separation is uncertain data (F1.3).** A line whose speaker the
  model is unsure of shows the speaker in muted with the dashed-ring glyph and
  the words "Speaker is a guess". Never guess a name silently; an invented
  attribution is worse than "Unknown".
- **An answer always carries its citations** as a row of clickable timestamps
  (F6.3). An answer without a citation does not render; if the model cannot
  cite it, the panel says so.
- **Gaps are shown.** A stretch the model could not transcribe is a row with a
  `failed` glyph and the word "Gap", with its time range. Never a silent skip
  (F6.4).

## 3. Review queue: `.jv-queue`

Exemplar: `exemplars/review-queue.html`.

One column of decisions. Everything the model made and no human has accepted.
For F3.8, show the complete proposed main point, supporting detail, changes and
evidence before offering Accept. The collapsed canvas offers Review instead.
Opening detail is not acceptance and does not establish that someone read it.

```
[h1 → hairline]
[toolbar: segmented (All / Notes / Layout / Minutes) · count as a figure]
.jv-rows
└── per item: evidence · what the model made · Accept | Edit | Reject
```

- **Evidence first, conclusion second.** The photograph crop, or the transcript
  excerpt, appears *above* what the model produced from it. The reviewer's
  question is "is this right", and they cannot answer it without the source.
- **Three actions, always in this order: Accept, Edit, Reject.** Accept is the
  accent-filled button. Edit and Reject are quiet. Reject is not destructive
  styling; rejecting a guess is normal, not dangerous, and Undo appears in
  place on the row the moment it happens.
- **Rejection captures the correction (F6.5).** When a reviewer edits, the
  original and the edit are both kept. The interface says so once, quietly, in
  the toolbar, and never again per item.
- **An empty queue is a good state**, and reads as one sentence in caption
  muted: "Nothing waiting. Everything on the canvas has been accepted."
- **Deliberately not in the system**: bulk accept-all. It defeats the point.
  Bulk *reject* is allowed, because rejecting in bulk risks nothing.

## 4. Session setup and consent: `.jv-split`

Exemplar: `exemplars/session-setup.html`.

```
[h1 → hairline]
.jv-split
├── left (400)  the form: session name, canvas shape, agenda, retention
└── right       the consent panel: who is present, who has agreed
```

- **The consent panel is the right column, not a modal.** It is the most
  important thing on this screen (F6.1) and a modal implies it is a step to get
  past. It is a gate.
- **Capture cannot start until every person present has agreed.** The start
  button stays disabled, and the hint under it names what is missing: "Two
  people have not agreed yet." Never hide the button; a hidden control is a
  mystery, a disabled one with a reason is an instruction.
- **Retention is set here, before anything is recorded (F6.6)**, and shown as
  a plain sentence, not a dropdown of durations with no consequence attached:
  "Audio is deleted when the session ends. The transcript is anonymised before
  it leaves this session."
- **Anyone can stop capture at any point**, and that control lives on the
  session bar of every screen, not only here.

## 5. Export: `.jv-split`

Exemplar: `exemplars/export-view.html`.

**Export is a page, not a modal.** Choosing what leaves the session deserves
the room of a page and the back button of a page; a modal would imply it is a
step to get past.

```
[h1 → hairline]
.jv-split
├── left (400)  what to include: canvas, minutes, decisions, open questions
└── right       the preview, and the destination list (.jv-rows)
```

- **What is provisional is called out before export**, at the top of the left
  column: "4 items on the canvas are still proposed. They will be exported
  with their Proposed marking." Exporting an unreviewed guess as if it were
  the team's decision is the failure mode this screen exists to prevent.
- **Destinations are a hairline row list** (F5.1, F5.2, F5.3): PNG, PDF,
  minutes as text, push to a board tool. Each row carries its own status glyph,
  because a push to an external API can be `waiting` or `failed` while the PNG
  is already `accepted`.
- **Every exported claim keeps its citation** (F6.3). The minutes export is a
  list of decisions each carrying its timestamp.

---

## Shared layout rules

- **8px rhythm.** 4px only as a micro-step inside a cell.
- **`minmax(0, …)` and `.jv-truncate` on every flexible text column.** A long
  sticky-note transcription will otherwise push the grid sideways. This is the
  most common layout bug in this system.
- **View switching inside a screen is a segmented control**, three options at
  most. Navigation between sections is tabs with an ink underline. They look
  different because they do different things.
- **Empty states are one sentence** in caption muted, naming the next action.
  No illustrations.
- **Loading is a still skeleton** in `--color-surface-sunken` mirroring the
  real layout, on first load only. Never a spinner, shimmer or pulse: a moving
  mark in a live meeting says "wait", and nobody in the room is waiting.
- **The only modal is the confirmation dialog**, for End session and Delete
  session. Everything else is a page, the side panel or a floating menu.
- **Z-order is fixed**: content 0 · sticky headers 10 · session bar 30 ·
  popovers 40 · dialogs 50. Nothing above 50. If something must sit above a
  dialog, the dialog was the wrong pattern.
