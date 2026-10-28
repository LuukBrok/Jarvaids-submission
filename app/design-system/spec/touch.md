# Touch

**The signal is `pointer: coarse`, not screen width.** An iPad in landscape is
1194px wide and is touched. A desktop window dragged narrow is 800px wide and
is moused. Width drives layout. Pointer drives interaction. The two questions
are separate and this system had been answering the second one with the answer
to the first.

That single confusion produces every defect in this file. `grid.css` gates its
only touch utility, `.jv-hit`, on `@media (max-width: 1023px)`, so a 1280px
meeting-room touchscreen and an iPad in landscape both get 20px mouse targets
and hover-revealed actions that a finger can never reveal. The room screen is
the product's primary surface and it is the one surface the system never
considered touching.

The one breakpoint stays. 1024px is still the only width tier in this system
and `forbidden.md` #23 is unchanged: a pointer query is not a `sm:` / `md:` /
`xl:` tier, it is a different axis. Nothing below adds a width breakpoint.

---

## 0. Room mode: `data-room` on `<html>`

The room screen is the product's primary surface, and it is read from five
metres, off a projector, by someone mid-sentence. The new design handles that
with a **mode**, not with a larger floor for everybody.

```html
<html data-room>
```

- **Every type size is multiplied by `--room-scale`, 1.5.** Body 14/20 becomes
  21/30, label and meta 12/16 become 18/24, display 44/48 becomes 66/72. The
  roles, their order and their weights do not change.
- **Every target becomes `--target-room`, 44px.** Buttons, segmented options,
  tabs and item actions grow as controls, not only as hit areas, because the
  room screen is often a touchscreen operated standing up.
- **Nothing else moves.** Colours, lines, radii and the layout breakpoint are
  identical, so every contrast number in `accessibility.md` still holds, and
  room mode is not a second design to maintain.

Why a mode. `space-and-hierarchy.md` § 3 works out that text on a projected
1440px screen subtends about three quarters of what it does on a laptop at
arm's length. The previous system answered that with a 15px body floor
everywhere, which was too large for a facilitator at a desk and still small on
the wall. A mode lets the desk be dense (14px body, 32px targets) and the wall
be large (21px body, 44px targets). **The cost:** someone has to turn it on. A
room screen projected without `data-room` reads 14px body like 11px on a desk.
The session's shared display should set it; a desk view never does.

Room mode and the coarse pointer are separate signals. Room mode is about
distance; the coarse pointer is about the finger. Each gives 44px targets on
its own, and only room mode scales the type.

---

## 1. The mechanism: `data-pointer` on `<html>`

Set an attribute, do not scatter media queries.

```html
<!-- inline in <head>, before the stylesheet link, so it runs before paint -->
<script>
(function () {
  var root = document.documentElement;
  if (root.dataset.pointer) return;              /* a manual override wins */
  var mq = window.matchMedia('(pointer: coarse)');
  var set = function () { root.dataset.pointer = mq.matches ? 'coarse' : 'fine'; };
  set();
  mq.addEventListener('change', set);
})();
</script>
```

Three reasons this is better than a bare `@media (pointer: coarse)` block, and
the third is the one that matters:

1. **It is one decision in one place.** The pointer state is read once and
   published once. A media query re-asks the question in every rule that cares,
   and a rule that forgets to ask is a silent bug that only appears on a device
   nobody on the team owns.
2. **It composes with the width query instead of competing with it.** Layout
   keys on `@media (min-width: 1024px)`, interaction keys on the attribute, and
   a reader of the CSS can tell which question a rule is answering by looking at
   how it is written. The room touchscreen is `[data-pointer="coarse"]` **and**
   above the breakpoint, which is exactly the combination that was unreachable
   before.
3. **It can be toggled.** `document.documentElement.dataset.pointer = 'coarse'`
   in a console, or a two-second edit in the element inspector, puts a desktop
   into the touch state with no device, no emulator and no reload. A media query
   can only be faked through device emulation, which also changes the width, so
   testing the touch state on a wide screen, the exact case this system got
   wrong, is the case a media query cannot show you. A rule you cannot
   demonstrate is a rule that rots. This one has a switch.

**Use `pointer`, not `any-pointer`.** `(any-pointer: coarse)` asks what the
device is capable of; `(pointer: coarse)` asks how the person is pointing right
now. A Surface with a mouse plugged in, or an iPad with a trackpad, reports
`fine` and should get mouse targets, because that is what the user is holding.
When they detach the keyboard, `matchMedia` fires `change` and the attribute
flips live.

**Vocabulary.** This system says **phone** for the device, **touch** for the
interaction and **coarse pointer** for the signal. It does not say "mobile",
which conflates a device, a width and an input method, and it is the word that
produced this gap in the first place.

---

## 2. CHANGE REQUIRED: `grid.css`, the touch block

Replace the whole `Touch` section at the end of `grid.css` (the
`@media (max-width: 1023px)` block containing `.jv-hit`) with this.

```css
/* --------------------------------------------------------------------------
   Touch. The signal is the POINTER, not the width (spec/touch.md).
   An iPad at 1194px is wide and touch; a narrow desktop window is narrow and
   mouse. Width drives layout, pointer drives interaction.

   --jv-pointer-coarse is a 0/1 flag. The media query supplies the default for
   a page where the head snippet did not run; the attribute, when present,
   overrides it in both directions, which is what makes the touch state
   demonstrable on a desktop.
   -------------------------------------------------------------------------- */

html                        { --jv-pointer-coarse: 0; }
@media (pointer: coarse) {
  html                      { --jv-pointer-coarse: 1; }
}
html[data-pointer="fine"]   { --jv-pointer-coarse: 0; }
html[data-pointer="coarse"] { --jv-pointer-coarse: 1; }

/* jv-hit: grows the HIT AREA without redrawing the control. At a fine pointer
   the flag is 0, the pseudo-element collapses to the control's own box, and
   nothing changes. 44px is a layout dimension, not a token value. */
.jv-hit { position: relative; }
.jv-hit::after {
  content: "";
  position: absolute;
  left: 50%;
  top: 50%;
  width: max(100%, calc(var(--jv-pointer-coarse) * 44px));
  height: max(100%, calc(var(--jv-pointer-coarse) * 44px));
  transform: translate(-50%, -50%);
}
.jv-hit.jv-absolute { position: absolute; }

/* jv-hit-grow: for an icon control with NO adjacent word, where a larger hit
   area is not enough because the target also has to be findable by a finger
   that cannot hover to look. The control itself grows and the icon inside it
   goes from 20px to 24px (forbidden.md #26 sizes, one step up the 4px
   rhythm). Every such control still carries an accessible name. */
.jv-hit-grow {
  min-width: calc(var(--jv-pointer-coarse) * 44px);
  min-height: calc(var(--jv-pointer-coarse) * 44px);
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.jv-hit-grow > svg {
  width: calc(20px + var(--jv-pointer-coarse) * 4px);
  height: calc(20px + var(--jv-pointer-coarse) * 4px);
}

/* Hover is a fine-pointer affordance and there is no blanket rule here to
   neutralise it, because a blanket neutraliser would also strip the primary
   button's accent fill. Hover styles are AUTHORED under @media (hover: hover)
   instead. See spec/touch.md section 7. */

/* Anything stuck to a screen edge pads itself past the device's own
   furniture. This is a system concern, not an application concern: the
   session bar can never be hidden (F1.1, F6.1), so it can never be the
   application's job to remember that a notch exists. Requires
   <meta name="viewport" content="... viewport-fit=cover"> on every page. */
.jv-stuck-top {
  position: sticky;
  top: 0;
  padding-top: env(safe-area-inset-top, 0px);
}
.jv-stuck-bottom {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  padding-bottom: max(env(safe-area-inset-bottom, 0px), var(--jv-keyboard-inset, 0px));
}

/* The viewport the user can actually see. 100dvh is the layout viewport and
   lies while the on-screen keyboard is open; --jv-viewport-height is the
   visual viewport, published by the snippet in spec/touch.md. The dvh value
   is the fallback for a page without the snippet. */
.jv-viewport { height: var(--jv-viewport-height, 100dvh); }
```

**CHANGE REQUIRED: `grid.css`, the file header comment.** The sentence "Above
1024 is the room screen and the facilitator's laptop; below 1024 is a phone,
which in this product is a camera and a text box, not a second desktop (F1.4,
F1.7)" describes a width as if it were an input method. Replace with:

```
   ONE breakpoint: 1024px, and it governs LAYOUT only. There is no sm/md/xl
   tier. Above 1024 is the room screen and the facilitator's laptop; below
   1024 is a phone, which in this product is a camera and a text box, not a
   second desktop (F1.4, F1.7).

   Interaction is a separate axis and is never keyed on width. The room screen
   is frequently a large touchscreen: wide layout, coarse pointer. See
   spec/touch.md.
```

**CHANGE REQUIRED: `grid.css`, `.jv-page` side padding.** A landscape phone
puts the notch and the rounded corner inside the page gutter. Replace both
`.jv-page` padding declarations with:

```css
.jv-page {
  padding-inline:
    max(var(--layout-pad-narrow), env(safe-area-inset-left, 0px))
    max(var(--layout-pad-narrow), env(safe-area-inset-right, 0px));
}

@media (min-width: 1024px) {
  .jv-page {
    padding-inline:
      max(var(--layout-pad), env(safe-area-inset-left, 0px))
      max(var(--layout-pad), env(safe-area-inset-right, 0px));
  }
}
```

---

## 3. Defect: iOS zooms the page on every field

`.field input`, `select` and `textarea` are set at `--text-body`, 14px. iOS Safari zooms the entire page when a field below 16px takes
focus, and it does not zoom back out. The page is then wider than the screen,
the session bar scrolls sideways out of view, and the user is panning to find
the control they were about to use.

This happens on the device F1.4 designates as the primary photographic input
and F1.7 designates as the typed-input fallback for anyone who does not want to
speak. It is the phone's two jobs, both broken by one pixel.

**Rule: on a coarse pointer, every text-entry control renders at 16px.**
Nothing else changes size. Body is still 14px everywhere it is read.

```css
/* PROPOSAL: --text-field-touch: 16px
   Not a ninth reading size. It is the platform's zoom threshold, and it
   applies to text ENTRY only. Raising --text-body to 16px instead was
   considered and rejected: 14px is the desk size, room mode handles the
   room, and changing it would restate every line height in the system to fix
   a phone bug. */

html[data-pointer="coarse"] :where(input, select, textarea) {
  font-size: var(--text-field-touch, 16px);
}
```

A field is 40px at a desk and 44px on a coarse pointer (`components.md` § 5);
16px text inside a 44px field still sits on the rhythm. `_base.css` already
applies both under `@media (pointer: coarse)`.

WCAG: the zoom leaves content requiring two-dimensional scrolling at 320 CSS
px, which is **SC 1.4.10 Reflow, Level AA**.

---

## 4. Defect: nothing pads itself past the safe area

`.session-bar` is `position: sticky; top: 0` with no `env(safe-area-inset-*)`
padding anywhere in the system. On a notched phone in landscape, and in any
installed or full-screen context, the recording indicator sits under the notch
and the End session control sits under the rounded corner.

The session bar is the one element this system insists can never be hidden
(F1.1, F6.1). A consent indicator that a device bezel can cover is the same
failure as a consent indicator a developer can hide, arrived at by accident.

**Rule: anything stuck to a screen edge pads itself.** It is a property of the
primitive, not of the screen using it. `.jv-stuck-top` and `.jv-stuck-bottom`
in the CHANGE REQUIRED above carry the inset; a screen never writes
`env(safe-area-inset-*)` in its own CSS, exactly as it never writes its own
horizontal padding.

**Rule: `viewport-fit=cover` is required on every page.** The five exemplars
already carry it. Without it the insets are all zero and the padding silently
does nothing, which is the worst kind of correct-looking code.

---

## 5. Defect: `100dvh` lies while the keyboard is open

`dvh` tracks the browser chrome collapsing. It does not track the on-screen
keyboard. With the keyboard open, a `100dvh` element is roughly half again as
tall as the space the user can see, so the bottom of it, which on the phone is
the typed-input box and the submit control (F1.7), is underneath the keyboard.

**Rule: follow `visualViewport`.** Publish two runtime variables and use them.

```js
/* Runtime values, not design tokens: they have no fixed value, they are
   measurements. tokens.css stays the source of truth for decided values. */
(function () {
  var vv = window.visualViewport;
  if (!vv) return;                       /* .jv-viewport falls back to 100dvh */
  var root = document.documentElement;
  var sync = function () {
    root.style.setProperty('--jv-viewport-height', vv.height + 'px');
    var inset = Math.max(0, window.innerHeight - vv.height - vv.offsetTop);
    root.style.setProperty('--jv-keyboard-inset', inset + 'px');
  };
  vv.addEventListener('resize', sync);
  vv.addEventListener('scroll', sync);
  sync();
})();
```

- `--jv-viewport-height` is what `.jv-viewport` uses. Any full-height shell,
  the capture screen and the board container use `.jv-viewport`, never `100vh`
  and never `100dvh` directly.
- `--jv-keyboard-inset` is how far the keyboard intrudes. `.jv-stuck-bottom`
  takes the larger of it and the home-indicator inset, so a bottom bar rides
  above the keyboard instead of under it.
- The session bar is `.jv-stuck-top` and therefore stays visible while the
  keyboard is open. That is deliberate: F1.1 does not pause because someone is
  typing.

WCAG: a focused field covered by the keyboard or by a sticky bar is **SC 2.4.11
Focus Not Obscured (Minimum), Level AA** in WCAG 2.2. It is not in the 2.1 AA
target this system sets, and it is still a defect worth fixing rather than
inheriting.

---

## 6. Touch targets

- **44px minimum in both dimensions** for anything a finger can reach. At a
  desk a control is `--target-desk`, 32px; on a coarse pointer and in room
  mode the control itself becomes `--target-room`, 44px, through the one
  `--target` variable `_base.css` publishes. Where a control cannot grow
  without breaking its row, `.jv-hit` grows the hit area instead, without
  redrawing the control.
- **`.jv-hit-grow` for icon controls with no adjacent word.** A hit area only
  helps a finger that has already found the target. An icon-only control has to
  be findable as well, and the pointer that cannot hover to inspect it is the
  same pointer that occludes it. The control grows to 44px and the icon inside
  it steps 20px to 24px. Use it for the canvas item's Accept, Edit and Reject
  cluster, the transcript's playhead control, and any bar icon without a label.
  `forbidden.md` #22 and #26 still apply: every one of them carries an
  accessible name.
- **Adjacent targets are separated by at least `--spacing-2`.** Two `.jv-hit`
  pseudo-elements that overlap hand the tap to whichever is later in the DOM,
  which reads as a control that does the wrong thing at random. Where a row is
  tight enough that the hit areas would meet, space it at `--spacing-3` or use
  `.jv-hit-grow` and let the controls take the room honestly.
- WCAG: 44px is **SC 2.5.5 Target Size, Level AAA** in WCAG 2.1, above this
  system's stated AA target, and **SC 2.5.8 Target Size (Minimum), Level AA**
  in WCAG 2.2 sets 24px. This system holds 44px because the room screen is
  operated standing up, at arm's length, by someone mid-sentence.

## 7. Hover on a coarse pointer

`interaction.md` says "Touch has no hover. Below 1024, every action that hover
would have revealed is permanently visible." The rule is right and the
condition is wrong.

**Rule: on a coarse pointer, at any width, every hover-revealed action is
permanently visible.** A provisional item's Accept, Edit and Reject cluster is
visible on the 1280px room touchscreen, because a finger has no hover state to
reveal it with and the room screen is the surface where accepting happens.

**Rule: every hover style is written under `@media (hover: hover)` or keyed on
`[data-pointer="fine"]`.** A hover tint applied on tap sticks until the next
tap elsewhere and reads as a stuck selection, which in this product means a row
that looks selected and is not.

WCAG: content that appears on hover must be dismissible, hoverable and
persistent under **SC 1.4.13 Content on Hover or Focus, Level AA**. Making it
permanent on a coarse pointer satisfies it by removing the case.

---

## 8. CHANGE REQUIRED: `spec/exemplars/_base.css`

`_base.css` is the flattened browser copy of `tokens.css` and `grid.css`. The
new design already gave it the coarse-pointer field size and 44px targets
under `@media (pointer: coarse)`, and room mode under `:root[data-room]`. Two
changes are still owed.

```css
/* 1. Session bar: pad past the notch. Add to the .session-bar rule. */
.session-bar { padding-top: env(safe-area-inset-top, 0px); }

/* 2. Hover: fine pointer only. Wrap the :hover rules on the buttons and the
   field controls. */
@media (hover: hover) {
  .btn-primary:hover:not([disabled])   { background: var(--color-accent-pressed); }
  .btn-secondary:hover:not([disabled]) { background: var(--color-ink-fill); }
  .btn-quiet:hover:not([disabled])     { background: var(--color-ink-wash); color: var(--color-ink); }
  .btn-danger:hover:not([disabled])    { background: var(--color-status-failed-wash); }
  .field input:hover, .field select:hover, .field textarea:hover { border-color: var(--color-ink); }
}
```

The session bar's `min-height: 56px` plus `padding-top` makes it taller than
56 where an inset exists. That is correct: 56 is the height of the bar's
content, and the inset is the device's, not the design's.

The coarse-pointer rules in `_base.css` key on the media query rather than on
the `data-pointer` attribute from § 1, so the touch state cannot yet be
toggled on a desktop by setting the attribute. Moving them onto
`html[data-pointer="coarse"]` is the remaining half of § 1.

---

## 9. The phone capture flow (F1.4, F1.5, F1.6)

This flow does not exist anywhere in the system, and it is the phone's reason
for being in the product. Any participant photographs the wall from their own
phone, with no login (F1.4, F4.1). Three screens.

### 9a. Capture

```
[.jv-stuck-top: session bar, cut down: capturing glyph + "Recording" + Pause]
[.jv-viewport: the camera preview, full bleed]
[one line of guidance, meta, muted, over the preview on a --color-canvas strip]
[.jv-stuck-bottom: the shutter, primary, 64px, .jv-hit-grow]
```

- **The session bar is cut down, never removed** (F1.1, F6.1). The capturing
  glyph, the word, and Pause. The timer and the mode belong to the room
  screen. Anyone can pause capture from their own phone; that control is never
  behind an overflow menu.
- **One primary action.** The shutter. Everything else on this screen is quiet.
- **The guidance is one sentence**, in the shape `patterns.md` uses for empty
  states: "Photograph the whole wall. Jarvaids will split it into notes."
- The preview is `.jv-viewport`, so it is the visible viewport and not the lying
  one.

### 9b. Uploading and reading

No spinner (`forbidden.md` #21). The photograph is the content, so it is shown.

```
[the photograph, full width, on the photo stage, --radius-lg]
[status glyph + word, label, and a determinate track underneath]
```

- Two named states, in order: the `waiting` glyph and **"Uploading"** while
  bytes move, then the `waiting` glyph and **"Reading notes"** while
  segmentation and
  handwriting reading run (F1.5, F1.6). Two words, because they fail
  differently and the user's options differ.
- **The track is determinate for the upload** and absent for the read, because
  the read has no honest percentage. During the read the status is the still
  glyph and the word alone. An invented progress bar is a lie told to look busy.
- **Cancel is available throughout**, quiet, and it discards the photograph.
- **Failure is a state, not an error screen**: the `failed` glyph, the word "Not
  sent", one sentence naming what still works, and a Retry. The photograph
  stays on the device until it has landed. Copy: "Not sent. The photograph is
  still on your phone. Capture is still running."
- The room screen shows nothing from this phone until 9c is confirmed. A
  half-read wall appearing live on the shared canvas is the model writing to
  the canvas unasked.

### 9c. Confirm what was found

The screen this flow exists for. Heading: **"Here is what we found on the
wall."**

```
[h1 → hairline]
[the photograph, with the detected note boundaries drawn on it,
 --line-provisional dashed --color-status-provisional]
[.jv-rows, one row per detected note:]
  [the crop, --color-surface-sunken ground, the paper colour as a small
   swatch beside it, never as a fill]
  [the text that was read, in an editable field]
  [meta: confidence, if the model has one]
[.jv-stuck-bottom: "Add 14 items to the canvas" (primary) · "Discard photograph" (quiet)]
```

- **Confirming the read is not accepting the items.** Everything added here
  lands on the canvas **provisional**, with a dashed accent line and the
  word "Proposed" (F3.5), and goes
  into the review queue. This screen answers "did the camera see the wall",
  not "is the model right", and those are two different people's jobs at two
  different moments. `patterns.md` § 3's ban on bulk accept is intact, because
  nothing here is being accepted.
- **A note the model could not read is not dropped.** The `failed` glyph, the word
  "Unreadable", the crop, and an empty field ready to be typed into (F1.6,
  `components.md` § 1). It is a request for help, not an error.
- **Every item keeps the photograph.** The crop and the full photograph stay
  attached for the life of the session, so a bad read is checked against the
  original rather than argued about (F1.5, F6.3).
- **The count is in the button**, as a tabular figure: "Add 14 items to the
  canvas". A user who has just photographed a wall of forty notes and is being
  offered fourteen needs to see that number before they tap, not after.
- Discarding is one tap and needs no confirmation: nothing has been recorded to
  the session yet and the wall is still on the wall.

---

## 10. The board on a phone: read-only, stated

`patterns.md` mentions this in passing, in one clause. It is a real rule and it
belongs here in full.

**Below the layout breakpoint the board is pannable, zoomable and read-only.**
Planned F3.8 expansion remains available: Show details and Hide details are
viewing controls, not edits, with at least 44px targets and no hover dependency.
Full-content acceptance remains in the review surface. See
[expandable notes](expandable-notes.md).

- **No drag, no resize, no reposition, no delete.** On a phone a one-finger
  drag means pan. Overloading it with item-drag means every attempt to look
  around the board risks moving an item during a live meeting, and F3.4 says
  new output never moves what the team placed by hand. A phone that moves it by
  accident breaks the same promise from the other end.
- **Two write paths on a phone, both append and neither positions**: the
  photograph button (F1.4) and the typed-input box (F1.7). Position is decided
  by the layout engine (F3.3) and adjusted on the room screen.
- **The review queue is fully usable on a phone**, because it is a list and not
  a spatial surface. Accept, Edit and Reject are permanently visible there, at
  44px, under § 6 and § 7.
- **The list view is the phone's default board view.** The segmented control
  still offers Canvas and List, and below the breakpoint it opens on List,
  because the board is read-only there anyway and a 390px screen reads a list
  better than it reads a wall. This also means the parallel list view that
  `accessibility.md` requires is the one every phone user meets first, which is
  the right way round for a view that has to be genuinely good.
- **Undo stays reachable** (F3.7), in the cut-down session bar, on every phone
  screen. Undo is not a desktop feature.
- **Pause capture stays reachable** (F6.1). Same bar, same rule.

---

## 11. Checklist additions

**Applied to `spec/checklist.md`**, under "Interaction", in place of the
line "Every hover-revealed action is permanently visible below 1024px.", with
the room-mode and 32px desk target lines added alongside:

```
- [ ] Every hover-revealed action is permanently visible at
      `[data-pointer="coarse"]`, at any width. Test by setting the attribute
      on `<html>`, not by narrowing the window.
- [ ] Every finger target is 44px via `.jv-hit`, or `.jv-hit-grow` if it is an
      icon with no word beside it.
- [ ] Text-entry controls are 16px at a coarse pointer.
- [ ] Anything stuck to a screen edge uses `.jv-stuck-top` or
      `.jv-stuck-bottom`. Nothing writes `env(safe-area-inset-*)` locally.
- [ ] No `100vh` and no `100dvh`. Full-height uses `.jv-viewport`.
```

---

## 12. What this file contradicts or supersedes

- **`interaction.md`, "Hover, focus, active"**, the line "**Touch has no
  hover.** Below 1024, every action that hover would have revealed is
  permanently visible." The rule stands, the condition is superseded: the test
  is `[data-pointer="coarse"]`, at any width. Applied: `interaction.md` now
  says "On a coarse pointer, at any width".
- **`grid.css`**, the `@media (max-width: 1023px)` touch block and the file
  header comment. Both superseded by § 2.
- **`patterns.md` § 1**, "Below 1024 the rail stacks under the board. On a
  phone this screen is mostly the photograph button and the typed-input box
  (F1.4, F1.7); the board is read-only and pannable." The stacking sentence is
  a width rule and is correct. The read-only clause is expanded into § 10 here,
  which is now the authority on it.
- **`forbidden.md` #23**, "No `sm:` / `md:` / `xl:` breakpoints." Not
  contradicted. Nothing here adds a width tier. Read it as governing width
  only, which is what it meant.
- **`README.md`, "Honest limitations"**, the entry "There is no tablet layout.
  One breakpoint means a 900px screen gets the phone layout. Deliberate,
  because this product's phone is a camera and its desktop is the room screen,
  and a tablet is neither." The layout decision is defensible and stands. The
  reasoning is answering a different question, because the tablet complaint is
  not usually about width. Replace the last sentence with:

  > Deliberate, because this product's phone is a camera and its desktop is the
  > room screen, and a tablet is neither. Note that this is a layout decision
  > only. A tablet gets full touch treatment regardless of its width, and so
  > does the room touchscreen, because interaction is keyed on pointer, not on
  > width. See `spec/touch.md`.

- **`README.md`, "Accessibility"**, and **`accessibility.md`**, the claim
  "**WCAG 2.1 AA on every screen. Not aspirational.**" It cannot stand as
  written. `spec/announcements.md` § 10 carries the full replacement wording
  and the reasons, which are the SC 2.1.4 breach and the canvas keyboard gap.
  Touch adds nothing to that breach list: the defects in this file are SC 1.4.10
  and SC 1.4.13 at AA, which the fixes above close, plus SC 2.4.11 and SC 2.5.8,
  which are WCAG 2.2 and outside the stated target. Use the wording in
  `announcements.md`; do not write a second version of it here.
