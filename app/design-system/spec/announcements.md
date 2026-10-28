# Announcements

This system specifies landmarks, labels, heading order and focus, and then
stops. There is no `aria-live` guidance anywhere in it: grep the spec files and
`CLAUDE-fragment.md` and the count is zero.

That is a gap in a product whose whole behaviour is arrival. The transcript
appends a line every few seconds. Provisional items appear on the canvas. A
degradation banner appears and disappears. An answer lands in the rail. Capture
starts and stops. Every one of those is a change a sighted person sees at a
glance and a screen-reader user is told about only if somebody decided they
would be.

**Both failure directions are real, and this system is currently exposed to
both.** `aria-live="polite"` on a live transcript makes the product unusable:
speech runs at roughly 150 words a minute, the region re-announces on every
append, the queue never drains, and the user hears nothing else, including the
one announcement that matters. And nothing anywhere makes capture state audible,
so a screen-reader user in a consent-critical product cannot tell whether the
room is being recorded.

**The rule this file exists to impose: every region is either live or
deliberately silent, and which one it is, is written down.** Silence is a
decision with a reason, not an omission. The default is silent.

WCAG: this closes **SC 4.1.3 Status Messages, Level AA**, which is unmet
everywhere in the product today because no live region exists.

---

## 1. The three mechanisms, and when each is right

| Mechanism | Interrupts | Use for |
|---|---|---|
| `role="status"` (`aria-live="polite"`) | No. Waits for a pause. | Almost everything live in this product. |
| `role="alert"` (`aria-live="assertive"`) | Yes. Cuts off what is being read. | Capture state, and nothing else. |
| No live region | n/a | The default. Anything continuous, anything the user will reach on their own, anything a focus move already reads. |

**Exactly one thing in this product is assertive: capture starting, stopping or
pausing.** Interrupting someone mid-sentence is justified when the sentence
being interrupted is less important than "this room is being recorded". It is
not justified for anything else, and a second assertive region would train
people to ignore the first.

## 2. Plumbing rules a developer must not have to guess

Two regions per screen, owned by the application shell, present in the DOM at
first paint, empty:

```html
<div id="jv-say"        class="jv-visually-hidden" role="status" aria-live="polite"    aria-atomic="true"></div>
<div id="jv-say-urgent" class="jv-visually-hidden" role="alert"  aria-live="assertive" aria-atomic="true"></div>
```

- **They exist before the message does.** A region created at the moment it is
  needed is frequently missed, because assistive technology registers live
  regions as they enter the accessibility tree, not as they change. Never
  create, move, or `display: none` a live region.
- **`role` and `aria-live` are both written.** Redundant on paper, and the
  redundancy is what makes older combinations behave.
- **`aria-atomic="true"`.** The whole message is read, every time. Without it
  some combinations read only the changed word.
- **Set `textContent`, never append.** An appending region grows without bound
  and some combinations re-read the whole thing.
- **To repeat an identical message, clear it first**, then set it on the next
  frame. An unchanged string is not a change and is not announced:

```js
function say(text, urgent) {
  var el = document.getElementById(urgent ? 'jv-say-urgent' : 'jv-say');
  el.textContent = '';
  requestAnimationFrame(function () { el.textContent = text; });
}
```

- **Announcement text is written for listening, not copied from the screen.**
  It is a sentence, it names the state and the consequence, it never says
  "updated" or "changed" on its own.
- **A visible element may be the live region**, and should be, when it appears
  whole, carries one sentence, and does not update word by word. The
  degradation banner and the phone's upload status are the two cases. Nothing
  that streams is ever a live region.
- **Never announce something a focus move already reads.** Doing both reads it
  twice, which is worse than doing neither.

**CHANGE REQUIRED: `grid.css`.** The visually-hidden utility every live region
and the skip link depend on does not exist. Add it beside the focus block.

```css
/* --------------------------------------------------------------------------
   Visually hidden. For live-region text and the skip link: present for a
   screen reader, absent to the eye. Never display:none, which removes it from
   the accessibility tree, and never width/height 0, which some combinations
   skip. See spec/announcements.md.
   -------------------------------------------------------------------------- */

.jv-visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  padding: 0;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
  border: 0;
}
```

---

## 3. Region by region

| Region | Live | Politeness | Mechanism |
|---|---|---|---|
| Transcript lines (F1.2, F1.3) | **No** | silent | reachable "N new lines" control |
| Transcript gap rows (F6.4) | **No** | silent | in the list, covered by the count |
| Capture started, stopped, paused (F1.1, F6.1) | **Yes** | assertive | `#jv-say-urgent` |
| Consent withdrawn (F6.1) | **Yes** | assertive | `#jv-say-urgent` |
| Degradation banner (F6.4) | **Yes** | polite | the banner element is `role="status"` |
| Answer panel on arrival (F2.7) | **No** | silent | focus moves to the panel heading |
| Provisional items on the canvas (F3.5) | **Yes** | polite | coalesced count, `#jv-say` |
| Review queue accept and reject (F6.5) | **Yes** | polite | focus move plus remaining count |
| Mode switched to Quiet or Active (F4.4) | **Yes** | polite | `#jv-say` |
| Undo (F3.7) | **Yes** | polite | `#jv-say` |
| Phone upload and read (F1.5, F1.6) | **Yes** | polite | the status element is `role="status"` |
| Export destination state (F5.1, F5.2, F5.3) | **Yes** | polite | `#jv-say`, one message per row |
| Form errors | **No** | silent | `aria-invalid` plus `aria-describedby` |
| Disabled primary action's reason | **No** | silent | `aria-disabled` plus `aria-describedby` |

### 3a. The transcript: deliberately silent

The transcript is `aria-live` free. Not `off` written defensively, just absent,
with a comment saying it is deliberate so the next person does not add one.

**Why.** A live transcript appends roughly two to three lines a minute at
conversational pace, in bursts. A polite region queues them and reads them in
order, behind whatever the user is doing, forever. The user cannot skim past a
queue, cannot get to the capture announcement behind it, and cannot use the
product. The failure is not subtle: it is total.

**What replaces it.** A real control, reachable, that says how far behind you
are and takes you there.

```html
<ol class="jv-rows jv-scroll" id="jv-transcript"> ... </ol>
<button type="button" class="jv-hit" data-jump aria-controls="jv-transcript">
  5 new lines, jump to latest
</button>
```

- It is a `<button>`, in the DOM immediately after the transcript, permanently
  in the tab order. It is not a live region, so its label changing as lines
  arrive is silent. The count is there when the user goes looking, which is the
  point.
- When the user is already at the latest line, the button reads "Following.
  Jump to latest" and is not disabled, because a disabled control cannot be
  read to check.
- **Activating it scrolls to the latest line and moves focus to it.** The line
  carries `tabindex="-1"`. The focus move is what reads the line; nothing is
  announced on top of it.
- **The transcript does not auto-scroll while focus is inside it.** Content
  moving under a reader who is reading it is the same bug as announcing it.
  Auto-follow resumes when focus leaves.
- Each line is an `<li>` with the anatomy in `components.md` § 10. A gap row
  (F6.4) is an `<li>` like any other, with the `failed` glyph and the word "Gap",
  so a reader moving line by line meets it in place.

### 3b. Capture state: assertive, because it is consent

F1.1 and F6.1. This is the one thing in the product that interrupts.

```js
say('Recording started. Everyone present has agreed.', true);
say('Recording paused.', true);
say('Recording stopped. Audio will be deleted when this session ends.', true);
say('Marijke withdrew consent. Recording stopped.', true);
```

- The sentence names the state and the consequence. "Recording stopped" alone
  leaves the user asking the question F6.6 exists to answer.
- **The running timer is never inside a live region.** A live elapsed timer
  announces every second and drowns the product. The session bar's visible
  timer stays visible, silent, and readable on demand.
- The announcement is fired by the state change, once, wherever it originated.
  Anyone can stop capture from any device (F6.1), so the announcement is not
  the responsibility of the control that was pressed.
- The visible indicator is unchanged: the filled disc, the word "Recording",
  the timer. Three signals, per `accessibility.md`, and none of them moves:
  nothing in the system pulses. The announcement is a fourth,
  for the person who cannot see the other three.

### 3c. The degradation banner: polite, and it is its own region

F6.4. `components.md` § 13.

```html
<div class="banner" role="status" aria-live="polite" aria-atomic="true">
  <span class="status">...</span>
  <span>The model is about 40 seconds behind. Capture is still running.</span>
</div>
```

- The banner is the live region, because its sentence is already one sentence
  written for both eye and ear, and duplicating it into `#jv-say` would read it
  twice.
- **Announce on state transition, not on re-render.** A banner whose "40
  seconds" ticks upward must not re-announce; the number is visible, the state
  is what changed. Render the number outside the atomic region, or update it
  without touching the announced sentence.
- **The sentence that is announced is the whole sentence, including what still
  works.** "Capture is still running" is the half of it a listener most needs,
  and it is the half a truncated announcement drops.
- When the banner is removed, announce the recovery once: "The model has caught
  up." A banner that silently vanishes leaves the user believing it is still
  there.

### 3d. The answer panel: focus, not live

F2.7. The user asked, so the answer is expected, and an expected arrival is
better handled by moving focus than by talking over them.

- On arrival, focus moves to the panel's `<h2>`, which carries `tabindex="-1"`.
  The heading is read, and the answer is the next thing under the reading
  cursor.
- **The panel is not a live region.** Doing both reads the answer twice.
- **Focus only moves if the user's last action was submitting the ask box.**
  An answer arriving after the user has moved on does not steal focus; it
  announces politely instead: "Answer ready, 3 citations."
- While the model is working, the panel shows the still `waiting` glyph and the word
  "Thinking", and that element is **not** live: the user just pressed submit
  and knows.
- The failure case is the same path: focus moves to the heading and the panel
  says "I cannot find that in this session." An answer that does not render
  (`components.md` § 11) still has to be told to somebody.
- The citations are a row of links, in the tab order after the answer, each
  with an accessible name that carries the time and the speaker, per
  `accessibility.md`.

### 3e. Proposed items arriving on the canvas: polite, counted, coalesced

F3.5, and in Active mode F2.8. Items can arrive in bursts, and one announcement
per item is the transcript failure in miniature.

- **Never per item.** One message per coalescing window, and the window is 10
  seconds. That number is a product decision: short enough that the canvas and
  the announcement do not diverge in a live meeting, long enough that a burst
  of fourteen notes from one photograph is one sentence.
- The message is a count plus where to deal with it:
  `say('3 proposed items added to the canvas. 12 waiting in review.')`
  "Proposed" is the on-screen word for model output (`copy.md`), so the
  announcement uses it too: a screen-reader user and a sighted user hear and
  see the same word.
- **The announcement points at the list view, not at the canvas**, because the
  list view is the navigable surface (`accessibility.md`). The canvas itself is
  not keyboard-navigable and announcing arrivals on it without saying where to
  go is a dead end.
- In Quiet mode the model does not add to the canvas unasked (F4.4), so this
  fires rarely. In Active mode it is the main thing a listener needs.
- `waiting` placeholders (F6.4) are not announced on appearance, only when they
  resolve into content. A placeholder is a promise, not a change.

### 3f. The review queue: focus does the work, the count is announced

F6.5. Accepting or rejecting removes the row the user is standing on, so focus
management is not optional.

- **On accept or reject, focus moves to the next item in the queue**, or to the
  previous one if the accepted item was last.
- The announcement is the outcome and what is left:
  `say('Accepted. 11 remaining.')` / `say('Rejected. 11 remaining.')`
- **When the queue empties**, focus moves to the empty-state sentence, which
  carries `tabindex="-1"`, and it reads: "Nothing waiting. Everything on the
  canvas has been accepted." (`patterns.md` § 3). No separate announcement.
- Editing (F6.5) announces nothing on open: focus moves into the field, which
  reads its label. On save: `say('Saved. Your correction is kept as part of the
  session record.')` The consent-relevant half of that sentence is said once
  per save, not once per session, because it is the sentence that matters and a
  listener has no toolbar note to glance at.
- Bulk reject announces the count: "12 items rejected." Bulk accept does not
  exist (`patterns.md` § 3).

### 3g. Form errors

WCAG: **SC 3.3.1 Error Identification, Level A**, and **SC 3.3.3 Error
Suggestion, Level AA**. Neither needs a live region, and using one here causes
the double-announcement bug.

```html
<div class="field">
  <label for="session-name">Session name</label>
  <input id="session-name" aria-invalid="true" aria-describedby="session-name-err">
  <p class="t-caption" id="session-name-err">Give the session a name so it can be found later.</p>
</div>
```

- `aria-invalid="true"` goes on and comes off with the invalid state. It is
  never set on an untouched empty field, matching `interaction.md`: validation
  shows after a field has been touched.
- `aria-describedby` points at the error text. If the field also has a hint,
  `aria-describedby` lists both ids, hint first.
- **On blur validation, the message appears silently.** It is read the next
  time the field takes focus, which is the next time it is relevant.
- **On submit, focus moves to the first invalid field.** That reads its label,
  its state and its description in one go. No live region, no error summary
  block, no scroll-and-hope.
- The error text is the same text a sighted user reads. It says what to do, not
  that something is wrong.

**The disabled primary action.** `interaction.md` requires the primary action
to be disabled until the form is valid, with the reason beside it, and
`patterns.md` § 4 gives the example: "Two people have not agreed yet." A
`disabled` button is not focusable, so a screen-reader user tabbing the form
never meets the control or its reason.

```html
<button class="btn btn-primary" aria-disabled="true" aria-describedby="start-why">Start session</button>
<p class="t-caption" id="start-why">Two people have not agreed yet.</p>
```

- Use `aria-disabled="true"`, not the `disabled` attribute, so the control stays
  focusable and its reason is read.
- The click handler returns early while `aria-disabled` is true. It does not
  submit and it does not announce.
- The visual treatment is unchanged: `opacity: 0.4`, `cursor: not-allowed`
  (`components.md` § 4).
- The reason text is not live. It is read when the button is focused, which is
  when the user is asking why.

---

## 4. The skip link

**SC 2.4.1 Bypass Blocks, Level A. Currently unmet on every screen**, and every
screen carries a sticky session bar and a tab row before its content, with a
rail after it.

```html
<a class="jv-skip" href="#jv-main">Skip to the canvas</a>
```

- **First focusable element in the document**, before the session bar.
- The target is `<main id="jv-main" tabindex="-1">`. Without the `tabindex` the
  fragment jump moves the reading position in some browsers and not the focus.
- **The label names the destination on that screen**: "Skip to the canvas",
  "Skip to the transcript", "Skip to the review queue", "Skip to the form".
  Not "Skip to content", which tells a user who has four screens nothing.
- One skip link per screen. The named landmarks in § 5 do the rest of the
  bypassing.

**CHANGE REQUIRED: `grid.css`.** Add beside the focus block.

```css
/* --------------------------------------------------------------------------
   Skip link. SC 2.4.1, Level A. Hidden until focused, then it is the first
   thing on the screen, above the session bar's z-index of 30 but below a
   dialog's 50 (spec/patterns.md). Pads itself past the notch, because it sits
   at the very top edge (spec/touch.md).
   -------------------------------------------------------------------------- */

.jv-skip {
  position: absolute;
  left: -9999px;
  top: 0;
  z-index: 40;
  background: var(--color-surface-float);
  box-shadow: var(--elevation-md);
  color: var(--color-accent);
  font-family: var(--font-reading);
  font-size: var(--text-body);
  padding: var(--spacing-2) var(--spacing-3);
  padding-top: calc(var(--spacing-2) + env(safe-area-inset-top, 0px));
  border-radius: var(--radius-sm);
  text-decoration: underline;
}
.jv-skip:focus {
  left: var(--spacing-2);
}
```

It uses the existing focus ring from the `:focus-visible` rule above it. When
focused it floats over the session bar, so it is a floating surface: white with
an elevation token and no line, never a fill and a border together.
`--color-accent` on `--color-surface-float` is 7.88:1 by the same formula,
the value the generated table already reports for white on the accent; the
exact pair is not yet declared in `contrast-check.py`.

---

## 5. Landmarks, labelled distinctly

The landmark set in `accessibility.md` is right and unlabelled, which on a
screen with a sticky bar, a tab row, a main region and a rail gives a listener
four unnamed places.

```html
<header class="session-bar jv-stuck-top" aria-label="Session"> ... </header>
<nav class="tabs" aria-label="Screens"> ... </nav>
<main id="jv-main" tabindex="-1"> ... </main>
<aside aria-label="Transcript"> ... </aside>
```

- **Any landmark type that appears twice on a screen carries distinct
  `aria-label`s.** Two unlabelled `nav` landmarks are two identical entries in
  a landmarks list.
- **The label does not repeat the role word.** "Session", not "Session header".
  The screen reader says the role itself and "session header header" is what a
  duplicated label sounds like.
- **The rail's label follows the segmented control.** It is "Transcript",
  "Review queue" or "Answer", and it changes when the rail changes, because the
  rail is one thing at a time (`patterns.md` § 1).
- **A `<section>` is only a landmark when it is labelled.** The answer panel is
  `<section aria-labelledby="jv-answer-title">`. An unlabelled `<section>` is
  a generic box and does not belong in the landmark list.
- `<main>` appears once. There is no `aria-label` on it; the `h1` names the
  screen.
- WCAG: **SC 1.3.1 Info and Relationships, Level A**, and **SC 2.4.6 Headings
  and Labels, Level AA**.

---

## 6. Dialogs

The system forbids every component library (`forbidden.md` #25), so it has to
write down what a library would otherwise have supplied. This product has
exactly one dialog, the confirmation (`components.md` § 14), used for End
session and Delete session (F6.6). Everything else that might once have asked
for a confirmation is reversible with Undo, in place and in the session bar.

**Use the native `<dialog>` element with `showModal()`.** It supplies the focus
trap, the inertness of the rest of the document, Escape, and the top layer,
correctly, for free. Everything below is either what the native element gives
you, or what it does not.

```html
<dialog id="jv-confirm" class="jv-dialog" aria-labelledby="jv-confirm-title">
  <h2 id="jv-confirm-title" class="t-signal-lg">End this session?</h2>
  <p class="t-body">Capture stops and the audio is deleted.</p>
  <p class="t-meta">The transcript and the canvas are kept.</p>
  <div class="jv-row-centre">
    <button type="button" class="btn btn-secondary" autofocus data-close>Cancel</button>
    <button type="button" class="btn btn-danger-fill">End session</button>
  </div>
</dialog>
```

1. **`aria-modal="true"` and `role="dialog"`** are implicit on a modal
   `<dialog>` opened with `showModal()`. Write them explicitly only on a
   hand-rolled `<div>` dialog. Never call `show()`, which is not modal and
   traps nothing.
2. **`aria-labelledby` points at the visible title.** Never an `aria-label`
   that duplicates it, which produces two names that drift apart.
3. **Initial focus is the least destructive control.** For a confirmation that
   is Cancel, marked with `autofocus`. Never the destructive button, which
   turns a stray Enter into the irreversible action this dialog exists to
   guard. If the dialog contains a field, focus the first field instead.
4. **Focus is trapped.** `showModal()` does this. Hand-rolled: set `inert` on
   every body-level sibling of the dialog. Use `inert` rather than a keydown
   cycle, because `inert` removes the content from the accessibility tree,
   which a Tab-cycling loop does not, leaving a virtual cursor free to read the
   page behind the dialog.
5. **Escape closes, and Escape means Cancel.** Native behaviour; a hand-rolled
   dialog listens for it. WCAG: **SC 2.1.2 No Keyboard Trap, Level A**, met by
   Escape plus a labelled Cancel.
6. **Focus is restored to the trigger on close.** If the trigger no longer
   exists, because the row it was on was removed, focus goes to the nearest
   surviving heading with `tabindex="-1"`. Never to `<body>`, which drops a
   screen reader back to the top of the document with no announcement.
7. **The backdrop does not dismiss.** A confirmation is a question, so it is
   answered, not dismissed by tapping beside it, and at a coarse pointer a
   mis-tap next to a 480px dialog is easy (`spec/touch.md`). Escape and Cancel
   are the two ways out and both are labelled. The backdrop is `--color-ink` at
   40%, written with the slash syntax on the token, never a literal:

```css
/* Tailwind v4 utility form on the dialog element: backdrop:bg-[--color-ink]/40
   Plain CSS, for _base.css and for anything not going through Tailwind: */
.jv-dialog::backdrop {
  background: color-mix(in srgb, var(--color-ink) 40%, transparent);
}
/* Custom properties reach ::backdrop by inheritance in current browsers. If a
   target browser does not resolve it there, declare the computed value once on
   :root and use it, or fall back to a wrapper div. No literal in the rule.
   PROPOSAL: --color-backdrop: the modal backdrop, ink at 40%. Only if the
   above cannot be expressed. It carries no text, so it introduces no contrast
   pair and nothing needs adding to contrast-check.py. */
```

8. **Scroll is locked behind the dialog**, and the position is preserved:

```js
var y = window.scrollY;
document.body.style.position = 'fixed';
document.body.style.top = (-y) + 'px';
document.body.style.width = '100%';
/* on close */
document.body.style.position = document.body.style.top = document.body.style.width = '';
window.scrollTo(0, y);
```

   `overflow: hidden` alone does not hold on iOS. The `.jv-scroll` region
   inside a dialog, if one ever exists, is unaffected.
9. **Dialogs never stack.** Z-order tops out at 50 (`patterns.md`). One dialog
   at a time; a dialog that needs a dialog means the first one was the wrong
   pattern.
10. **A dialog is never announced through a live region.** Moving focus into it
    reads its name and its content. Doing both reads it twice.
11. **The dialog is not a live region** and its content does not update while
    open. A confirmation that changes under the reader is a different dialog.
12. WCAG: **SC 2.4.3 Focus Order, Level A**, and **SC 4.1.2 Name, Role, Value,
    Level A**.

---

## 7. Single-character shortcuts: a Level A failure to fix

`interaction.md` says:

> `J` / `K` or arrows move between queue items.
> `A` accepts, `R` rejects, `E` opens the edit field.

There is no remap, no off switch, and no statement that they are active only
while a queue item has focus. **SC 2.1.4 Character Key Shortcuts is Level A**
and requires at least one of exactly those three. The system provides none, so
it fails at Level A today.

The practical failure is ordinary, not theoretical. Anyone dictating into this
product, and speech input is precisely the accommodation a live-meeting tool
attracts, drops an "a" or an "r" into the page and accepts or rejects the
model's guess without knowing. In a product whose one job is keeping the
model's guesses distinguishable from the team's decisions, a stray keystroke
that accepts one is the worst available bug.

**They also collide with screen-reader quick navigation.** In NVDA and JAWS
browse mode, `E`, `R` and `K` are single-letter navigation keys (edit field,
radio button, link). Those keystrokes are swallowed by the screen reader and
never reach the page, so for a browse-mode user the shortcuts silently do
nothing at all.

### The fix

**1. Scope them to focus. This is the conformance fix and it is required.**

- The handler is attached to the queue list element, never to `document`.
- It runs only when the active element is the list or a descendant of it.
- It does not run when a text-entry control has focus. `E` opens the edit
  field; while that field has focus, `a`, `r`, `e`, `j` and `k` type letters.
- It does not run when any modifier is held.
- Focus must be visibly on a queue item for the keys to do anything, and the
  focus ring is what tells the user that (`grid.css`).

**2. State it in the label.** `interaction.md` already requires the shortcuts
to be shown in the toolbar as labels. The label gains the condition:

> `J K` move · `A` accept · `R` reject · `E` edit, while a queue item is
> focused

**3. Provide an off switch.** One checkbox in session settings: "Single-key
shortcuts in the review queue". Default on, persisted per person, not per
session. It costs one setting and it covers the dictation user whose input
method makes focus scoping insufficient.

**4. Remapping is not built, and this file says so rather than implying it.**
Three keys, and a remapping interface costs more than it returns for three
keys. SC 2.1.4 is satisfied twice over by scoping and the off switch. If the
set ever grows beyond the queue, remapping is the next thing to build, and it
should arrive with the fourth shortcut, not after the tenth.

**5. Expose them to assistive technology** with `aria-keyshortcuts` on the
control each one operates:

```html
<button type="button" class="btn btn-primary" aria-keyshortcuts="A">Accept</button>
<button type="button" class="btn btn-quiet"   aria-keyshortcuts="E">Edit</button>
<button type="button" class="btn btn-quiet"   aria-keyshortcuts="R">Reject</button>
```

### The position on screen readers, stated rather than left to be discovered

**The queue is not turned into a composite widget to make the shortcuts work
under a screen reader.** Making it a `listbox` with a roving `tabindex` would
force focus mode and hand the keys back, at the cost of turning a list of rich
rows, each containing an evidence crop, editable text and three buttons, into a
list of options. That is a worse screen-reader experience bought to rescue an
accelerator.

**The screen-reader path is the buttons.** Accept, Edit and Reject are real
`<button>` elements, permanently present on every row, in that fixed order
(`patterns.md` § 3), reachable by Tab and by the button quick-key. The
single-character shortcuts are a sighted-keyboard accelerator, and this system
specifies them as one.

---

## 8. CHANGE REQUIRED: `spec/checklist.md`

Add under "Accessibility":

```
- [ ] Every region that changes on its own is listed in
      `spec/announcements.md` § 3 as live or as deliberately silent, and the
      screen matches it.
- [ ] Live regions exist in the DOM at first paint, empty, and are never
      created at the moment of the message.
- [ ] Nothing that streams is a live region. The transcript has its
      "N new lines" control instead.
- [ ] Skip link present, first in the tab order, naming this screen's
      destination.
- [ ] Repeated landmarks carry distinct `aria-label`s that do not repeat the
      role word.
- [ ] Every dialog: `aria-modal`, `aria-labelledby`, initial focus on the
      least destructive control, focus restored on close, scroll locked, and
      no second dialog above it.
- [ ] Single-key shortcuts fire only while a queue item has focus, and never
      while a text-entry control does.
```

---

## 9. CHANGE REQUIRED: `spec/interaction.md`

In "Keyboard", replace the two shortcut lines with:

```
- While a queue item has focus, and no text-entry control does: `J` / `K` or
  arrows move between queue items, `A` accepts, `R` rejects, `E` opens the
  edit field. These keys are inert everywhere else on the page, which is what
  makes them conform to WCAG SC 2.1.4 (Level A). They can be turned off in
  session settings. See `spec/announcements.md` § 7.
```

---

## 10. What this file contradicts or supersedes

- **`accessibility.md`, "Focus and keyboard"**, the line "The review queue's
  shortcuts (`A`, `R`, `E`) are shown in the toolbar, not hidden." True and
  insufficient. Superseded by § 7: shown, scoped to focus, and switchable off.
- **`interaction.md`, "Keyboard"**. Superseded by § 9.
- **`components.md` § 14, Confirmation**, "Escape closes. Focus is trapped and
  restored. Overlays never stack." Not contradicted, expanded by § 6, which
  adds `aria-modal`, `aria-labelledby`, initial focus on Cancel, the backdrop
  position, and the scroll lock.
- **`accessibility.md`, "Structure and semantics"**. The landmark list is
  correct and incomplete: § 5 adds the labels, and § 4 adds the skip link that
  SC 2.4.1 requires and the list does not mention.
- **`README.md` and `accessibility.md`, the conformance claim.**
  `accessibility.md` opens "Target: **WCAG 2.1 AA** on every screen. Not
  aspirational. A screen that does not meet it is not finished." `README.md`
  says "Target is WCAG 2.1 AA and it is verified, not asserted." Neither can
  stand as written, because two Level A criteria are unmet today and a product
  with a Level A failure does not conform at AA. Replace both with this, and
  keep the two texts identical:

  > **Target: WCAG 2.1 AA. Contrast is verified; the rest is specified, and two
  > Level A criteria are known to be unmet today, so the product does not
  > conform yet.**
  >
  > What is verified: 104 foreground and background pairs, computed from the
  > shipped token values by `spec/contrast-check.py`. All 104 pass 1.4.3 and
  > 1.4.11. That is twelve pairs no colour scheme moves, plus twenty-three
  > pairs measured once in each of the four schemes in
  > `spec/colour-schemes.md`.
  >
  > What is not met:
  >
  > - **SC 2.1.4 Character Key Shortcuts, Level A.** The review queue's single
  >   character shortcuts have no off switch, no remap and no focus scope. The
  >   fix is specified in `spec/announcements.md` § 7 and is not yet applied.
  > - **SC 2.1.1 Keyboard, Level A**, for the canvas. Direct manipulation
  >   (F3.6) has no keyboard path. The parallel list view makes the canvas's
  >   content readable; it does not make its manipulation operable, so it is a
  >   mitigation and not conformance.
  > - **SC 4.1.3 Status Messages, Level AA** was unmet everywhere until
  >   `spec/announcements.md`; it is now specified and not yet implemented.
  >
  > And nothing here has been run through NVDA, JAWS or VoiceOver, so the
  > semantics are specified correctly as far as the spec goes and are
  > unverified in practice.

- **`README.md`, "Honest limitations"**, the entry "The canvas is not
  keyboard-navigable in this spec." Correct, and it should name the criterion:
  it is an SC 2.1.1 Level A failure, not only a design gap.
- **`spec/touch.md` § 12** defers to the wording above rather than writing a
  second version of it. If it is changed, change it in one place and copy it.
