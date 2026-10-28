# Interaction

The governing fact: this interface runs during a live meeting, on a screen
people glance at. Every interaction rule below follows from that.

## Motion

Three durations, one easing curve. Ease out, under 300ms, transform and
opacity only. All of it gated behind `prefers-reduced-motion` in `grid.css`.

| Token | Use |
|---|---|
| `--motion-fast` 150ms | Button press, hover tint, focus ring. |
| `--motion-base` 200ms | A row expanding, a panel switching, an item appearing on the canvas, a menu opening. |
| `--motion-slow` 250ms | An item being accepted: the dashed line fading out as the tonal fill fades in. |

`--motion-ease` is `cubic-bezier(0.23, 1, 0.32, 1)`: a strong ease out, so a
change lands at once and settles, rather than winding up first.

Rules:

- **Motion marks a state change the user caused.** Never on load, never on
  data arriving in bulk, never as decoration.
- **Transform and opacity only.** They are composited, so they never reflow the
  page under someone's pointer, and they are the two properties that stay
  smooth on the cheap laptop driving a projector.
- **Under 300ms.** Anything longer is the interface asking the room to watch
  it, and nobody in a meeting is watching the interface.
- **The accept transition is the one worth its length.** When a human accepts
  a provisional item, the dashed accent line fades out and the
  `--color-surface-sunken` fill fades in over `--motion-slow`, drawn as two
  layers changing opacity so the rule holds. It is the moment the product is
  about, and showing it happen is what makes the distinction learnable.
- **Nothing loops.** No spinner, no shimmer, no pulse, including on the
  capturing indicator. A looping mark on the room screen pulls every eye in
  the room to it every cycle, and a mark that moves forever stops meaning
  anything. Work in progress is a word and a still glyph.
- **Nothing moves on the canvas that the user did not move.** New model output
  appears; it does not slide existing items aside (F3.4). Planned F3.8
  expansion is the explicit user-triggered exception: temporary local spacing
  preserves saved geometry and is removed on collapse. It never accepts
  content.

## Hover, focus, active

- Hover is a tone (`--color-ink-wash` on a quiet control or a row,
  `--color-ink-fill` on a secondary button, `--color-accent-pressed` on the
  primary) or a field's line darkening. Never a size change, never a shadow,
  and never a line added to a filled element.
- **Focus is always visible.** The 2px accent ring in `grid.css` applies to
  everything interactive. Removing it without replacing it is a WCAG 2.4.7
  failure and an audit finding.
- Active presses the element to `scale(0.97)`.
- **Touch has no hover.** On a coarse pointer, at any width, every action that
  hover would have revealed is permanently visible. A provisional item's
  Accept button is not hidden behind a hover on a phone or on the room
  touchscreen. See `touch.md` § 7.

## Keyboard

The review queue is the screen that most wants a keyboard, because a
facilitator clearing a queue is doing the same three things repeatedly.

- `J` / `K` or arrows move between queue items.
- `A` accepts, `R` rejects, `E` opens the edit field.
- `Escape` closes any overlay and returns focus to what opened it.
- `Enter` submits from the last field of a form.
- Tab order follows the visual order. If it does not, the DOM order is wrong;
  do not patch it with `tabindex`.

Shortcuts are shown in the toolbar as labels, not hidden in a help
modal nobody opens mid-meeting.

## Destructive and irreversible actions

The confirmation dialog is the only modal in the product, and it confirms only
what Undo cannot reach:

- **End session.**
- **Delete session**, which also deletes its audio before the automatic
  deletion (F6.6).

Do not confirm: pausing capture, rejecting one provisional item, rejecting a
cluster, removing an item from the canvas, clearing a queue filter. Each is
reversible, with Resume or with Undo, and a confirmation on a cheap action trains people to
click through confirmations on expensive ones.

**Undo is not a nicety here** (F3.7). One step back from anything the model
did, at any point in the session. Without it, a team will not let this thing
touch a live board. Undo lives in two places: **in place on the row or item
that changed**, for as long as that change is the latest one, and as a
persistent quiet button in the session bar. That pair is what replaces a
toast: the undo is where the change is, and it does not time out.

## Accepting, editing, rejecting

The three actions on model output (F3.5, F6.5).

- **Accept** gives the item the settled tonal fill and removes its dashed
  line. One click, no confirmation.
- **Edit** opens the text in place. The original text is kept alongside the
  edit, because the difference between them is the evaluation data (F6.5). The
  interface says this once, in the queue toolbar: "Your corrections are kept
  as part of the session record."
- **Reject** removes the item from the canvas and keeps it in the session
  record. Rejections are data too.

The correction capture is not a hidden feature. If people do not know their
edits are recorded, recording them is a consent problem.

## Asking the model something

The ask box (F2.7) is one input, full width, always in the same place.

- The answer arrives in the rail. It does not appear on the canvas, because
  the model does not write to the canvas unasked.
- While it is working, the panel shows the still `waiting` glyph and the word
  "Thinking", not a spinner.
- The answer renders only with citations. See `components.md` § 11.

## Quiet mode and Active mode

The facilitator's switch (F4.4). Quiet means the model listens and answers when
asked. Active means it may also put suggestions on the canvas (F2.8).

- **The mode is visible to the whole room**, in the session bar, at all times.
  A model that might be volunteering ideas without the room knowing is the
  anchoring risk with the safety off.
- Switching to Active is one click and shows a one-line consequence:
  "Jarvaids may add suggestions to the canvas. They will be marked Proposed."
- The default is Quiet. That is a design position, not a technical one, and it
  is the position this system takes because an AI suggestion placed on the
  board mid-divergence carries an authority a colleague's half-formed idea does
  not.

## Degradation

When the model is slow or down (F6.4):

- A hairline banner appears, stating what is behind and what still works.
  Never silent.
- Items that are coming appear as `waiting` placeholders in position, so the
  canvas does not silently reorganise when they land.
- **Capture keeps running.** The banner says so explicitly, because the room's
  first question will be "are we still being recorded".
- Never a full-screen block, never a modal, never a spinner. The meeting does
  not stop because the model did.

## Loading

Still skeleton blocks mirroring the real layout, first load only. They do not
pulse or shimmer. Not on refresh. Not on a filter change: a filter that
flickers to skeleton feels broken.

## Forms

- The primary action is disabled until the form is valid, and the reason is
  stated beside it.
- Validation shows after a field has been touched, never on an idle empty form.
- `Enter` submits.
- After submitting, the form resets and the new record is visible immediately,
  in place. No confirmation screen.

## What changed in the new design

- Durations went from 120/180/320ms to 150/200/250ms and the 2s pulse token
  was removed. Everything is now under 300ms and nothing loops, because a
  looping capturing indicator in the corner of the room screen was the one
  moving thing in the meeting.
- Accepting no longer resolves a dashed violet stroke to a solid ink stroke; it
  fades a dashed accent line out and a tonal fill in.
- The confirm list shrank to End session and Delete session. Pausing capture
  is reversed by Resume, and rejecting a cluster by Undo, which is now in
  place on the row as well as in the session bar.
- The touch rule is keyed on the pointer, not on the width.
