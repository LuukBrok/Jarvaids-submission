# Controls

The small interactive parts. `components.md` specifies the button and the form
field; everything else a form or a toolbar needs is here.

Every one of these already exists somewhere in the product, built locally and
differently each time: `exemplars/export-view.html` ships six checkboxes styled
by a screen-local `accent-color` rule, `exemplars/session-setup.html` hand-rolls
a four-option radio group out of `aria-pressed` buttons, and
`exemplars/live-canvas.html` falls back to a bare `title=` attribute where a
tooltip should be. This file is what they should have been built from.

**No new colour token is introduced here.** Every pair used below is already
measured in `accessibility.md`.

---

## 1. Checkbox

An independent yes or no. It is the control the export screen is made of
(F5.1, F5.2).

```
box          16px native <input type="checkbox">
accent       accent-color: var(--color-accent)
label        body, --color-ink, in a real <label> wrapping the input
hint         meta below the label text, --color-ink-muted
gap          --spacing-2 between box and label text
row padding  padding-block --spacing-1
alignment    the box aligns to the FIRST LINE of the label, not to its centre
```

**It is the native control.** Only `accent-color` and the size are set.
Replacing it with `appearance: none` and a hand-drawn box loses the platform's
own handling of forced-colours mode, of high-contrast settings, and of the
indeterminate mark, and buys a 16px square that looks slightly different on
each operating system for no gain.

**A checkbox is never a bare input.** It always sits inside its `<label>`, and
the label is the hit area: box, words and hint line are all one target. A 16px
box beside clickable-looking text that is not clickable is a control people
miss. `padding-block: --spacing-1` keeps two stacked labels from touching, so
a slightly low click on one does not land on the other.

On a coarse pointer and in room mode the label carries `.jv-hit` from
`grid.css`, which grows the hit area to 44px without redrawing the box.

### Indeterminate

For a select-all whose rows are partly selected (`tables.md` §6).

- It is a **DOM property, not an attribute**: `input.indeterminate = true`.
  There is no `indeterminate=""` in markup, and writing one does nothing.
- It is **not a third value**. The input still has a `checked` of true or
  false underneath and still submits as that. Indeterminate is a display
  state that says "some of the things this controls are on".
- Native indeterminate already maps to `aria-checked="mixed"`. **Do not also
  set `aria-checked`**, or two things claim the state and they will disagree.
- Clicking an indeterminate checkbox selects everything, never nothing.
  Selecting is the recoverable direction.

### States

- hover: the label row takes `--color-ink-wash`
- focus: the global ring from `grid.css`
- disabled: `opacity: 0.45` on the whole label, **and the reason stated beside
  it** (`components.md` §4). A disabled checkbox with no explanation is a dead
  end in a form someone is trying to submit.

## 2. Radio group

One of a small set of mutually exclusive options. This is what
`exemplars/session-setup.html` should be using for the canvas shape (F3.2).

```
wrapper   <fieldset>, border 0, padding 0
legend    <legend>, label, --color-ink-muted, the group's question
options   native <input type="radio"> in a <label>, same anatomy as §1
stack     .jv-stack-tight
```

- **A group with no legend is a group a screen reader cannot introduce.** The
  legend is the question, written as a label: "Starting shape of the canvas",
  not "Shape".
- Arrow keys move between options and change the selection. That is native
  radio behaviour and it is the reason to use radios rather than buttons: a
  group of four toggle buttons announces four independent controls that happen
  to be pressed, and nothing announces "1 of 4".
- There is **no unselected radio group in a form that must be submitted**. If
  no option is a safe default, add an explicit "Not decided yet" option rather
  than leaving the group empty. An empty radio group is a required field that
  looks optional.

### The option card variant

When each option carries a description line, as the canvas shapes do, the
option is a bordered block rather than a line:

```
block      --color-ink-wash fill, no line, --radius-sm, padding --spacing-3
title      body, --color-ink
detail     meta, --color-ink-muted, second line
chosen     --color-accent-wash fill, still no line, title at weight 500,
           and the radio itself is filled
grid       repeat(2, minmax(0, 1fr)), gap --spacing-2
```

Three signals on the chosen option, in this order: the filled radio (shape),
the title's weight, the wash (colour). Never the wash alone.

The option is a tonal surface, so it has no border in either state: a fill and
a line on one element is the box this system refuses (`forbidden.md` #12).
`exemplars/session-setup.html` currently thickens the chosen option's border
to 2px and compensates with a 1px padding change, which is now wrong twice: it
adds a line to a choice, and it makes the chosen option a pixel smaller than
its neighbours.

The chosen option takes the accent wash because choosing is the action here;
the radio itself is the native control in `accent-color`.

## 3. Switch

A setting that takes effect the instant it is flicked.

```
track      36 x 20, --radius-full
off        --color-hairline-strong fill
on         --color-ink fill
knob       16px circle, --color-surface-float, 2px inset, moves over
           --motion-fast with a transform
label      body, to the LEFT of the track, always a real label
```

Markup is `<button type="button" role="switch" aria-checked="true">` with the
label referenced by `aria-labelledby`, or a native checkbox with
`role="switch"`. Space and Enter both toggle it.

On is ink, not accent, for the same reason the segmented control's active
option is ink. The knob's position is the primary signal, the fill is second,
the label is third, so nothing here is carried by colour alone. Both fills are
already measured against `--color-canvas` in `accessibility.md`
(`--color-ink` 16.86:1, `--color-hairline-strong` 3.41:1, both above the 3.0
that WCAG 1.4.11 asks of a control boundary).

**A switch never carries an on and off word.** The label says what the setting
is, not what the switch currently is: "Follow the live edge", not "Follow the
live edge: on". The knob says the rest.

### The discipline rule

**A switch applies immediately. A form you explicitly save takes a checkbox,
not a switch.** A switch inside a form with a Save button makes a promise it
does not keep: it looks like it has already done the thing, and then the thing
does not happen until a button somewhere else is pressed. If a control's
effect waits for a Save, it is a checkbox.

Two consequences for Jarvaids, stated because both look like switch cases and
neither is:

- **The export options are checkboxes** (F5.1, F5.2), because nothing happens
  until Export is pressed.
- **Quiet and Active mode is a segmented control, not a switch** (F4.4). Both
  states are named, both names are visible to the whole room at once, and a
  room that has to work out what the off position of an unlabelled switch
  means is exactly the ambiguity that rule exists to prevent.

That leaves **no switch anywhere in Jarvaids today**, and that is the honest
state of it. It is specified here so that the first genuine case, a setting
that applies immediately and needs no name for its off state, is built once
rather than invented.

## 4. Which one when

| Situation | Control | Threshold |
|---|---|---|
| Independent yes or no | Checkbox | Any number, one per thing |
| Several things at once, all worth reading | Checkboxes | Up to 7 options. Above 7, a searchable list, not a wall of boxes. |
| One of a few, all worth reading, options carry a description | Radio group | 2 to 5 options |
| One of many, options are self-explanatory single values | Select | 6 or more |
| One of a few, and the choice is a change of view, not data | Segmented control | 3 at most (`components.md` §7) |
| A setting that applies instantly | Switch | Never inside a form with a Save |

Two rules that override the table:

- **Never a select of two.** Two radios show both options at once and cost one
  click instead of two.
- **Never a select where each option carries a consequence.** `patterns.md` §4
  already rules this for retention (F6.6): a choice whose options mean
  different things gets radios with a sentence each, not "a dropdown of
  durations with no consequence attached". A closed select hides the
  consequence behind a click, which is where consent decisions go to die.

## 5. Tooltip

### What it is for

**An icon-only control with no visible label, and nothing else.**

- Never on a control that already has a label. If the label is not enough, the
  label is wrong, and a tooltip is a way of not fixing it.
- Never on static text.
- **Never as the only carrier of a piece of information.** A tooltip is
  unreachable on touch, invisible on a projector, and gone the moment the
  pointer moves. Anything that matters is on the screen.
- Never containing an interactive element. That is a popover, §6.

### Anatomy

```
text        meta, --text-meta, --color-ink-inverse
background  --color-ink
radius      --radius-sm
padding     --spacing-1 --spacing-2
max-width   240px
offset      8px from the trigger, flipping side when there is no room
z-index     40
no arrow, no shadow
```

17.75:1, already measured as white on ink. It floats, so it would be allowed
an elevation token, and it has no need of one: ink against the light ground is
the strongest edge in this system. It has no
arrow because an arrow is decoration that then needs a shadow to read against
the content behind it.

### Behaviour

- Appears after 400ms on hover, immediately on focus. A keyboard user reaching
  a control has already committed to it; a pointer passing over one has not.
- Dismissed by Escape, by blur, and by the pointer leaving.
- Meets WCAG 1.4.13 on all three counts: **hoverable** (the pointer can move
  onto the tooltip without it vanishing), **dismissible** (Escape, without
  moving the pointer), **persistent** (it does not time out on its own).

### ARIA

```
<button type="button" aria-label="Undo the last thing Jarvaids did">
  <svg …>
</button>
<span role="tooltip" id="…">Undo the last thing Jarvaids did</span>
```

- **The icon button always carries its own `aria-label`, in the same words as
  the tooltip.** The tooltip is the sighted user's copy of the accessible name.
- `aria-describedby` points at the tooltip **only when it says something
  beyond the name**. Pointing it at a tooltip that repeats the name has the
  name read out twice.

### Touch

`interaction.md`: **touch has no hover.** On a coarse pointer there is no
hover event to open a tooltip with, and the long-press that some
implementations use collides with the system text-selection gesture.

```css
@media (pointer: coarse) { /* the tooltip is a tap-opened popover */ }
```

On a coarse pointer the tooltip becomes a popover (§6): opened by a tap,
carrying a close affordance, with `aria-expanded` on the trigger, dismissed by
Escape or a tap outside. `pointer: coarse` is a capability query, not a width
breakpoint, so it does not breach `forbidden.md` #23. There is still one
breakpoint in the system.

### `title=` is forbidden as a status carrier

`exemplars/live-canvas.html` puts `title="Speaker is a guess"` on a bare
provisional dot. That is wrong twice over:

1. **`title=` is not a tooltip.** It never appears on touch, it does not
   appear on keyboard focus, it cannot be styled, its delay is the browser's
   and not yours, and screen readers treat it inconsistently, some announcing
   it, some not, some only in place of a missing name.
2. **It makes an uncertain attribution colour-only.** `components.md` §2:
   status is always a glyph **and a word**. A coloured mark with a hidden
   attribute is just a coloured mark to a colour-blind reviewer, to a phone,
   and to a projector washing it out, which is the precise failure
   `accessibility.md` names as this product's easiest to commit.

The fix is the pattern the system already has: the dashed-ring glyph plus the
words "Speaker is a guess" beside it (F1.3), as
`exemplars/session-transcript.html` renders the state. That is the pattern. `title=` is
allowed nowhere except on an `<iframe>`, where it is the element's name.

## 6. Popover

A small panel anchored to its trigger, holding content or controls. z-index 40,
the value `patterns.md` reserves.

```
background  --color-surface-float
shadow      --elevation-md
line        none
radius      --radius-md
padding     --spacing-3
max-width   320px
offset      8px below the trigger, flipping above when there is no room
z-index     40
```

A popover floats above the page, so it is white with a shadow and no border.
The previous system drew it with a 1px `--color-hairline-strong` edge and no
shadow, because it had no elevation; on a light ground that read as a box
drawn on the page rather than a panel above it, and a border plus a fill is
two instruments on one element (`forbidden.md` #12). Text inside it is
measured on `--color-surface-float` in `accessibility.md`.

### Behaviour and ARIA

- Trigger: `aria-expanded="true|false"` and `aria-controls` pointing at the
  panel.
- Focus moves into the panel on open, to the first focusable thing in it.
- **Focus is not trapped.** Only the confirmation dialog traps focus
  (`components.md` §14). A popover is not modal: Tab leaves it and that closes
  it, a click outside closes it, and Escape closes it and returns focus to the
  trigger (`interaction.md`).
- **Popovers never stack.** Opening one closes any other. A tooltip on a
  control inside an open popover does not render: two things at z-index 40 on
  top of each other is the pattern being wrong, the same argument
  `patterns.md` makes about anything wanting to sit above a dialog.

## 7. Dropdown menu

A popover whose content is a list of actions. The review queue's sort control
is one (`tables.md` §3).

```
panel           as the popover: --color-surface-float, --elevation-md,
                --radius-md, padding --spacing-1
item height     --target-desk 32px; 44px in room mode and on touch
item padding    padding-inline --spacing-3
item text       body, --color-ink
tick gutter     20px leading, reserved on EVERY item in a menu that has any
                selectable item
separator       --line-fine solid --color-hairline, full bleed
```

### Menu roles, and when not to use them

- `role="menu"` with `role="menuitem"` children **only when every item is an
  action taken immediately**. Then arrow keys move, Home and End jump, Escape
  closes, and typing a letter jumps to the next item starting with it.
- **If the panel holds a mix of controls, do not use menu roles.** Menu roles
  take Tab away and make the arrow keys the only navigation, which surprises
  people who expected a panel. A panel of controls is a popover (§6) and Tab
  moves through it.

### Item states

| State | Treatment |
|---|---|
| rest | `--color-ink` on `--color-surface-float` |
| hover, and the keyboard's current item | `--color-ink-wash` across the full item |
| focus | the global ring, `outline-offset: -2px` so it is not clipped by the panel's own radius |
| disabled | `opacity: 0.45`, `aria-disabled="true"`, **and the reason as a meta second line** (`components.md` §4) |

### Showing "selected", never by colour alone

```
role         menuitemradio (one of a set) or menuitemcheckbox (independent)
aria         aria-checked="true"
mark         a 16px tick in the leading gutter, currentColor, stroke-width 1.5
```

The tick is the signal. The wash may accompany it but never replaces it,
because the wash is also what hover looks like, and a menu where the selected
item and the item under the pointer are the same colour tells you nothing.

The gutter is reserved on every item in the menu, so items do not shift
sideways when the selection moves. A menu whose text jumps as you arrow
through it is the most annoying 20px in any interface.

### The destructive item

- **Last, below a separator**, so a miss on the item above does not land on
  it.
- Label in `--color-status-failed`, no wash, no icon. It reads as the odd one
  out because it is.
- **An irreversible action is not a menu item at all.** Everything on
  `interaction.md`'s confirm list, stopping capture, deleting audio early
  (F6.6), ending a session, is a button that opens the confirmation
  (`components.md` §14), never a line in a menu that can be reached by an
  arrow key and an Enter. Menu destructive items are limited to reversible
  removals, which in this product means rejecting (F3.5), covered by undo
  in place and in the session bar (F3.7).

## 8. Keyboard hint

`<kbd>`. The review queue toolbar already renders three of them, from a
screen-local rule.

```
font-family     --font-signal
font-size       --text-signal-sm (12px, the floor)
text-transform  none
weight          500
colour          --color-ink-secondary
fill            none
line            --line-hairline solid --color-hairline-strong
radius          --radius-xs
padding         1px 5px
```

**The legend is shown exactly as the key prints it**, which the label role
already does now that nothing in the system is uppercase: a key legend is the
key, and uppercasing `a` would name `A`, a different keystroke that needs
Shift. The edge is `--color-hairline-strong` because a key outline is the only
thing that tells a key legend from a word, so it carries meaning; and it has a
line and no fill, never both.

- Real `<kbd>`, never a styled `<span>`.
- **Never interactive.** A `<kbd>` that can be clicked is a button that looks
  like a key, and people will try to press the real key instead and wonder why
  nothing happens.
- A chord keeps its joiner as plain text outside the elements:
  `<kbd>Shift</kbd>+<kbd>Click</kbd>`. One `<kbd>` per physical key.
- Shortcut hints live in the toolbar, where `interaction.md` puts them, not in
  a help modal nobody opens mid-meeting. The hint reads as a caption:
  `<kbd>A</kbd> accept · <kbd>E</kbd> edit · <kbd>R</kbd> reject`.
- No shadow and no bottom border pretending to be a keycap's depth. It is a
  label, not a picture of a key.

## 9. The visually hidden label

Needed by the selection checkbox in a table header (`tables.md` §6), which has
to have a real `<label>` but no room for a visible one.

```css
/* PROPOSAL: jv-visually-hidden: not yet in grid.css. */
.jv-visually-hidden {
  position: absolute;
  width: 1px; height: 1px;
  margin: -1px; padding: 0; border: 0;
  clip-path: inset(50%);
  overflow: hidden;
  white-space: nowrap;
}
```

- `white-space: nowrap` matters: without it the text wraps to one character
  per line inside a 1px box and some screen readers read it letter by letter.
- **It is not a way to hide interface.** Its only legitimate uses are a label
  that the surrounding layout already makes obvious to a sighted user, and a
  heading that gives a region a name. Hiding a control's text and leaving the
  control visible is how an interface becomes two different interfaces.
- It is not `display: none`: that removes the text from the accessibility tree
  too, which is the opposite of the point.

## 10. Field error and required marking

`components.md` §5 says a field's invalid border is
`--color-status-failed`, "only after the field has been touched". Nothing in
the system ships a selector for that, and `specimen.html` demonstrates the
error sentence with an inline `style="color:var(--color-status-failed)"`,
which `forbidden.md` #5 disallows. This section is the missing half.

### The selector is the ARIA state

```css
/* PROPOSAL: the invalid selector and the error line: not yet in the system. */
.field :is(input, select, textarea)[aria-invalid="true"] {
  border-color: var(--color-status-failed);
}
.field-error {
  display: flex;
  align-items: baseline;
  gap: var(--spacing-1);
  color: var(--color-status-failed);
  font-size: var(--text-meta);
}
/* the glyph is .glyph.glyph-failed from _base.css, on currentColor */
```

**Style off `[aria-invalid="true"]`, never off a `.invalid` class.** A class
and an ARIA state are two sources of truth for one fact, and when they drift
the screen and the screen reader say different things about the same field.
One attribute, styled and announced.

### The error line

```
[failed glyph, 16px, a ring with a bar] [the sentence, meta, --color-status-failed]
```

The glyph is not decoration. It makes the error the same grammar as every
other state in the product, a shape and words (`components.md` §2), and it
means the error is not carried by colour alone, which a red sentence on its own
would be. 6.94:1, already measured.

The sentence says what would be right, not what is wrong: "A join code is six
characters", not "Invalid input".

### Wiring

```html
<label class="field">
  <span class="t-structure">Join code <span class="req">Required</span></span>
  <input id="code" aria-invalid="true" aria-describedby="code-help code-error"
         required>
  <p id="code-help" class="t-caption">From the invitation, six characters.</p>
  <p id="code-error" class="field-error"><span class="glyph glyph-failed"
  aria-hidden="true"></span>A join code is six characters.</p>
</label>
```

- `aria-describedby` takes a **space-separated list**, and the order is **help
  first, then error**: the help describes the field, the error describes the
  value, and that is the order someone needs them in.

### Help versus error precedence

**They do not replace each other. Both render, help above the error, and the
help does not change colour.**

Swapping the help out for the error is the common implementation and it is
backwards: it removes the instruction at the exact moment someone has proved
they need it. The help stays in `--color-ink-muted` and keeps its job.

### Timing

- `aria-invalid` is **absent** until the field has been blurred once with an
  invalid value, or the form has been submitted. Not `aria-invalid="false"` on
  every idle field: an attribute repeated on everything is noise, and an idle
  empty field is not invalid, it is empty (`components.md` §5).
- Once present, it updates on every keystroke, so the error clears the instant
  the value becomes valid.

Validate on blur, release on input. Nobody is told off while typing, and
everybody is released the moment they fix it.

### Required marking

```
[label text] [the word "Required", label weight 400, --color-ink-muted]
```

- **The word, not an asterisk.** An asterisk is a symbol that needs a legend
  somewhere else on the page, it is read as "star" or skipped entirely, and at
  label size it is close to invisible on a projector at the back of a room.
- The native `required` attribute goes on the input. Do not add
  `aria-required` as well when `required` is available: same fact, two
  sources.
- **Mark the minority.** If every field but one is required, mark the optional
  one instead, with the word "Optional", and say so once above the form:
  "Everything here is required unless it says otherwise." Marking eleven
  fields Required teaches people to stop reading the marks.

## 11. Busy button

Accept is a server round trip on every provisional item (F3.5), and spinners
are forbidden (`forbidden.md` #21). This is what happens instead.

### The button

```
label        swaps to the present participle: "Accept" becomes "Accepting"
width        frozen at its resting width, so the row does not reflow
aria         aria-busy="true", aria-disabled="true"
disabled     NOT the disabled attribute
opacity      unchanged
cursor       progress
```

- **`aria-disabled`, not `disabled`.** A disabled element loses focus in most
  browsers, which throws a keyboard user back to the top of the document
  mid-action and takes the screen reader's place with it. `aria-disabled`
  keeps focus and announces the state; the click handler ignores the click.
- **Do not drop it to `opacity: 0.45`.** That opacity means "you cannot do
  this". This is "this is happening", which is a different sentence.
- **Freeze the width.** "Accept" becoming "Accepting" is four characters wider,
  and a button that grows shifts Edit and Reject sideways under a pointer
  already moving toward them.

### The waiting state is on the item, not in the button

`forbidden.md` #19: a state change is shown where the thing is. The thing here
is the item, not the button.

- The item takes the `waiting` glyph and the word "Accepting" in its badge
  position, which is the same grammar the ask panel uses for a model that is
  thinking (`interaction.md`) and the same one F6.4 uses for the model running
  behind.
- **The dashed line stays dashed until the server confirms.** No optimistic
  accept. An item that takes the settled fill and then fails has, for a moment,
  shown a model's guess as the team's work, and that is `forbidden.md` #16, the one
  rule that makes the product dishonest when it breaks.
- On success, the dashed line fades out and the tonal fill fades in over
  `--motion-slow`, 250ms. That is the longest transition in the product and
  `interaction.md` already says it is worth its cost.
- On failure, the item returns to provisional and a hairline banner
  (`components.md` §13) says what failed and that nothing was changed. Never a
  toast.

### Timing, in tokens

- The busy state renders only if the round trip has not finished within
  `--motion-fast` (150ms). Below that, nothing flashes.
- Once shown, it stays at least `--motion-base` (200ms), so a fast reply does
  not produce a flicker.
- Past four seconds it is no longer a busy button, it is degradation: the
  banner rule takes over (F6.4), saying what is slow and that capture is still
  running.

### While it is in flight

Edit and Reject on that same item take `aria-disabled="true"` with the reason
beside them, "Accepting", per `components.md` §4. Rejecting something that is
half accepted produces two records of one decision (F6.5), and the record is
the thing this product is measured on.

Everything else on the screen stays live. One item accepting does not freeze
a queue.

## 12. What this file changes

- **`components.md` §5** gains its missing half: the invalid state now has a
  selector (`[aria-invalid="true"]`), an error line component, a required
  marking rule and a stated help-versus-error precedence. Nothing in §5 is
  contradicted; the border rule is unchanged.
- **`typography.md`** used to set structure labels in tracked uppercase, which
  made `<kbd>` an exception. The new design removed uppercase everywhere, so
  `<kbd>` is now an ordinary label and there is no exception to record.
- **`exemplars/session-setup.html`** builds the canvas shape choice (F3.2) as
  four `aria-pressed` buttons with a 2px chosen border. Superseded by §2: it is
  a radio group in a fieldset, and the chosen option keeps a 1px border. The
  screen-local `.shape` block goes.
- **`exemplars/export-view.html`** styles its checkboxes with a screen-local
  `accent-color` rule. Superseded by §1, which is the same rule promoted into
  the system. The `.opt` block goes.
- **`exemplars/live-canvas.html`** carries `title="Speaker is a guess"` on a
  bare provisional dot. That breaches `components.md` §2 and
  `accessibility.md`'s "never colour alone", and it is now explicitly
  forbidden by §5. It becomes the dashed-ring glyph plus the words (F1.3).
- **`specimen.html`** demonstrates the invalid field with an inline
  `style="color:var(--color-status-failed)"` on the error caption, which
  `forbidden.md` #5 disallows, and with a `.invalid` class rather than the
  ARIA state. Both are superseded by §10.
- **`forbidden.md`** should gain one line: `title=` is not permitted as a
  tooltip or as a status carrier, on any element except `<iframe>`.
- **`grid.css`** needs `.jv-visually-hidden` (§9) and the two selectors in
  §10. Both are marked PROPOSAL because this file cannot add them.
- **`patterns.md`** reserves z-index 40 for popovers. This file is what fills
  that reservation: tooltips, popovers and dropdown menus all sit there, and
  they never stack on each other.
