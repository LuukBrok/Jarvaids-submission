# Space and hierarchy

How grouping and rank are made in a system with one hue, no decorative cards
and no shadows in the page. Grouping has three instruments, used in this
order: **space, then a tonal fill, then a line.** Rank has four: **space, type
role, weight and ink, and position.** This file says how to use them and how
to test that they worked.

Everything here is already implied by `principles.md`, `typography.md` and the
spacing scale in `tokens.md`. It is written down because "strong hierarchy"
and "good gestalt" are not instructions, and a screen that fails them fails
quietly.

## 1. Spacing is the grouping

Gestalt proximity: things closer together are read as belonging together, and
the eye does that before it reads a single word. Common region, a shared
ground behind a group, does the same job, and the new design now has it: a
group panel in `--color-surface-sunken`. Proximity still goes first, because
it is free and it survives every display; the tonal panel confirms a group
that space has already made; a line is the last resort.

**Never a fill and a line on the same element.** A group panel has no border.
A filled note has no border. A line on a tonal surface says the same thing
twice and turns a surface back into a box.

### The ratio

**The gap between groups is at least twice the gap inside a group, and three
times where the page has room.** The rhythm in `tokens.css`: 8 inside a group,
24 between groups, 64 between sections, 32 for the page margin. Outside is
always larger than inside.

| Inside a group | Between groups | Ratio | Where |
|---|---|---|---|
| `--spacing-2` 8 | `--spacing-5` 24 | 1:3 | a list of rows, and the next block |
| `--spacing-2` 8 | `--spacing-6` 32 | 1:4 | a dense figure row inside a section |
| `--spacing-3` 12 | `--spacing-6` 32 | 1:2.7 | `.jv-rows` padding against a section break |
| `--spacing-4` 16 | `--spacing-7` 48 | 1:3 | the two halves of a split page |
| `--spacing-5` 24 | `--spacing-8` 64 | 1:2.7 | page sections |

`--spacing-1` 4 is never a grouping gap. It is the micro-step inside a cell,
and `tokens.md` already says so.

### Never adjacent steps

**Two gaps that are adjacent on the scale do not read as different.** 8 against
12, 12 against 16, 16 against 24: those are one step apart and the eye does not
reliably resolve them, least of all at the reading distance in section 3. A
grouping distinction must be **at least two steps apart on the scale**, which
is also what the 1:2 minimum produces. If a layout seems to need 8 against 12
to make its point, the layout has too many levels in it, not too few gaps.

### The test

**Delete every divider and every tonal fill, and the grouping still reads.**

Take the screen, remove every hairline, every `.jv-rows` border, every group
panel's tone. The groups must still be groups. If two things merge into one,
or one group splits in two, the spacing was doing nothing and the tone or the
line was doing all the work.

That is the whole test, and it is a real one: hairlines and tones are cheap to
reach for, and a screen held together by them alone looks tidy on a laptop and
reads as one undifferentiated mass from the back of a room, where the 1px lines
have disappeared and a 1.11:1 tonal step is close to gone on a washed-out
projector.

A hairline or a tone is a **confirmation of a grouping that space has already
made**, never the grouping itself. That is also why the last row of `.jv-rows`
carries no line: the list ends because the space after it ends it.

## 2. Hierarchy without decoration

### The three reads

Every screen is read three times, in this order, and the design's job is to
decide what is in each read rather than to hope.

**First read, under a second, from across the room.** One thing. The `h1`, or
the single largest figure, or the accent, or the one dashed item in a field of
settled ones. Exactly one. A screen with two first reads has none.

**Second read, two to three seconds.** The structure: where the regions are,
what they are called, how many things are in each. Carried by the headings,
the labels, the group panels and the between-group gaps, not by lines.

**Third read, when someone sits down.** The content: body text, meta, figures,
the rows themselves.

### The four instruments of rank, in order of strength

1. **Space.** The strongest and the one to try first. Rank is distance from
   everything else: a thing with more space around it is more important, with
   no size change at all.
2. **Type role.** The six roles in `typography.md` are already a hierarchy:
   display, heading, title, body, label, meta. Use the role, do not invent a
   size.
3. **Weight and ink.** Within one role: 500 against 400, or ink against
   `--color-ink-muted`. A heading's muted second line is this instrument.
   Weight and ink separate two things at the same rank; they do not create a
   new rank.
4. **Position.** Reading order is a hierarchy for free. **A thing that must be
   seen first is moved, not enlarged.** Enlarging is the expensive fix and it
   costs a type role.

What is not on the list: colour, tone, borders, shadows, size outside the
scale. Tone groups; it does not rank. The accent is not an instrument of
hierarchy either. It marks what can be acted on, and `forbidden.md` #14 already
says an accent heading is wrong.

### The squint test

The one from `checklist.md`, applied to hierarchy as well as to the
provisional distinction.

**Stand two metres back and squint until the words are illegible.** Then:

- Is there exactly one thing your eye lands on first?
- Can you still see how many groups there are, and roughly how big each is?
- Do the team's items and the model's items still look different? (A tonal
  fill against a dashed line with no fill.)

If the answer to the first is "two things", the screen has two first reads and
one of them has to lose its weight, its space or its position. If the answer to
the second is "no", go back to section 1, because that is a spacing failure
wearing a typography costume.

## 3. Density, and the room

### The assumption, stated so it can be argued with

This product is read from across a room, off a projector, by someone
mid-sentence. Everything below follows from three numbers, and **all three are
guesses**:

- the projected image is about **2.4m wide** (a typical meeting room throw)
- the browser is at about **1440 CSS px** wide
- the furthest reader is about **5m** from the wall

**How to test them:** measure the projected width with a tape, measure the
distance from the wall to the back chair, and then have somebody in that chair
read the smallest text on the screen out loud, with room mode on. That is the
whole test and it has never been run. `accessibility.md` already admits that no
contrast number in this repo has been checked on a projector; this is the same
gap measured in millimetres instead of ratios.

### What those numbers imply

At 2.4m across 1440px, one CSS pixel is **1.67mm on the wall**. On a laptop at
96dpi it is 0.265mm, so the room screen magnifies by **6.3x**. But the reader
is 5m away instead of 0.6m, which is **8.3x** further.

**6.3 divided by 8.3 is 0.76.** Text on the room screen subtends about three
quarters of what the same size subtends on a laptop at arm's length.

That is the sentence this whole section exists for. The room screen is not a
big laptop, it is a **smaller** one. `--text-body` at 14px reads on the wall
like 11px reads on a desk. 12px meta reads like 9px.

### What follows: a mode, not a floor

The previous system answered this arithmetic with a single 15px body floor for
every screen. That was too large for a facilitator at a desk and still too
small on the wall, so the new design splits the two cases.

- **At a desk**, body is 14px, meta 12px, targets 32px. Dense enough for a
  facilitator working through a queue.
- **In room mode**, `data-room` on the root multiplies every size by 1.5 and
  makes every target 44px. Body becomes 21px, which on the wall reads like
  **16px on a desk**; meta becomes 18px, which reads like about 14px. Both clear
  the old floor with room to spare. See `touch.md` § 0.
- **Fewer things, not smaller things.** When a screen will not fit, the answer
  is never a smaller size. It is fewer items, a second screen, or the parallel
  list view.
- **Spacing gets the same treatment.** Room mode scales type and targets, not
  the spacing scale, so in room mode the ratios in section 1 tighten in
  relative terms. 8px is 13mm on the wall; 12px is 20mm. At 5m those differ by
  about 4.5 arcminutes, which is at the edge of what the eye resolves as
  "different". That is the measurement behind the two-steps-apart rule in
  section 1, and it is why the ratio is 1:2 minimum rather than something more
  delicate.
- **Anything hoverable is visible.** Already in `checklist.md` for the coarse
  pointer; it holds here for a different reason, because nobody is hovering a
  projector.

### The cost, stated plainly

**Room mode has to be switched on.** A shared screen projected without it is
the desk design at three quarters of its size, and 12px meta then reads like
9px from the back. The shared display should set `data-room` itself; nobody
should have to remember. Until that is wired, this is the system's most likely
legibility failure in a real meeting.

## 4. Concentric corners

### The geometric rule

When a rounded element sits inside a rounded container:

```
inner radius = outer radius - padding
```

The two curves are then concentric, sharing a centre, and the gap between them
is constant all the way round the corner. Break it and the gap visibly grows or
pinches at the corner while staying constant along the edges, which reads as
sloppiness without the reader being able to say why.

The same rule outward: a ring drawn **around** an element at an offset needs
`element radius + offset`.

### What this scale permits

Five steps: `--radius-xs` 2, `--radius-sm` 4, `--radius-md` 8, `--radius-lg`
16, `--radius-full`. Padding comes off the spacing scale, whose smallest step
is 4. The new design adopted the larger corners, which is exactly the case the
previous version of this file warned about: at 8 and 16 the rule stops being
academic.

Worked through for the surfaces that exist:

| Container | Padding | Concentric inner radius | What is nested |
|---|---|---|---|
| a button or field, `--radius-sm` 4 | 4 or more | 0 | an icon or a chip inside: square, or use `--radius-xs` only at 2px padding |
| a note or panel, `--radius-md` 8 | `--spacing-3` 12 | 0 | an action button inside a note: its own 4 is a small error, under 4px of arc |
| a group panel, `--radius-md` 8 | `--spacing-3` 12 | 0 | **a note inside the panel, radius 8**: the open case below |
| the dialog, `--radius-lg` 16 | `--spacing-5` 24 | 0 | its buttons, radius 4: a small error at this size |
| the photo stage, `--radius-lg` 16 | `--spacing-2` 8, if a crop sits that close | 8 | a crop inside: `--radius-md` is exactly right at that padding |

So the honest rule is to derive the inner radius rather than to pick a token:

```css
border-radius: max(0px, calc(var(--radius-md) - var(--spacing-3)));
```

### The open case: a note inside a group panel

A note keeps `--radius-md` 8 inside a group panel whose radius is also 8, with
12 of padding. The concentric rule wants 0. Reusing the container's radius
opens the corner gap from 12px along the edges to about 17px across the
corner, 41 per cent wider. It is left open, not decided: a note is a
free-standing object that keeps its shape when it is moved out of a group,
which argues for its own radius, and the gap is noticeable at 8px in a way it
was not at 4px. If it looks wrong on the room screen, the fix is a larger panel
radius or less padding, not a square note.

### Where it already bites

`grid.css` sets the focus ring with `outline-offset: 2px` and pulls the focused
element's own `border-radius` down to `--radius-xs` 2. The outward rule says
the ring around a `--radius-sm` 4 element wants a radius of 4 + 2 = **6**,
which this scale does not have. Setting the element to 2 makes the ring land on
2 + 2 = 4, back on the scale, at the cost of the element's corner changing
shape for as long as it is focused. The selected canvas note's 2px focal ring
at 2px offset around an 8px note wants 10; current browsers draw an outline
following the element's own radius plus the offset, which produces that 10
without a token, so it is correct as drawn.

`--radius-full` has no concentric case: it is not a length, so a pill inside a
pill is simply two pills, and a glyph inside a chip is correct as drawn.

## 5. Materials: what was decided

The previous version of this file left materials as an open question and
listed what would have to change if layered surfaces won. The new design
decided it, and only part of it.

**Adopted:**

1. **Tonal surfaces.** Three opaque tones, the ground, sunken and float, now
   do common region. `principles.md` #1 was rewritten from "white, separated
   by hairlines" to "one hue per screen, in tonal steps".
2. **Grouping panels.** `forbidden.md` #10 was reversed: a group panel in
   `--color-surface-sunken`, with no border.
3. **Elevation, for floating surfaces only.** `tokens.css` gained
   `--elevation-sm/md/lg`, bound only to menus, popovers, the dialog and the
   scrolled session bar. Nothing in the page has a shadow.
4. **Larger corners.** 8 and 16, with the concentric consequences in section 4.

**Not adopted:**

- **Translucency and blur.** Every surface is opaque. `contrast-check.py`
  measures a foreground against a fixed background, and a translucent surface
  has none: every ratio would become a range and the claim that contrast is
  verified would stop being true. The 40 ratios in `accessibility.md` all
  assume an opaque, known ground, and they still can.
- **Gradients.** Still banned (`forbidden.md` #11).

**What it cost:** the hairline lost most of its job, so it is now a decorative
divider only and `--color-hairline-strong` is kept for lines that mean
something; and the provisional distinction had to be re-proven on a tinted
ground, which is why the generated table now measures the accent and the
"Proposed" word on `--color-surface-sunken` as well as on the ground.

Hierarchy here is still space, type role, weight and ink, and position. Those
four cost nothing, and they survive a projector.
