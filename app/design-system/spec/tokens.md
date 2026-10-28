# Tokens

`../tokens.css` is the single source of truth. This file explains what the
tokens are *for*. When the two disagree, the CSS wins and this file is stale.

Every token is named by role, not by appearance. `--color-status-provisional`
is the token; the blue it currently resolves to is an implementation detail of
it. If the team later decides provisional items should be drawn differently,
one line changes and no component is touched.

The values below are the new design: one hue per screen, in tonal steps. What
changed from the previous system, and why, is at the end of this file.

## Colour · neutrals

Three surfaces, told apart by tone, never by a border around them.

| Token | Value | Job |
|---|---|---|
| `--color-canvas` | `#f8f9fc` | **The ground.** Everything sits on this. Slightly cool, so the one blue reads as belonging to the page rather than pasted on it. |
| `--color-surface-sunken` | `#ebeef2` | One tonal step down. A group's panel, an accepted note, a quoted transcript excerpt, a skeleton. It groups by tone, so it never also carries a border. |
| `--color-surface-float` | `#ffffff` | What floats above the page: menus, popovers, the confirmation dialog, the session bar. The only surfaces allowed an elevation shadow. |
| `--color-ink` | `#17181b` | Primary text. Also the capturing mark. 16.86:1 on the ground. |
| `--color-ink-secondary` | ink at 76% | Supporting text that is still content. 7.90:1. |
| `--color-ink-muted` | ink at 68% | Meta, hints, placeholders, empty states. **The text floor.** 5.97:1. Nothing lighter is ever text. |
| `--color-ink-edge` | ink at 50% | A boundary that carries meaning. Never text. 3.35:1. |
| `--color-ink-fill` | ink at 10% | A pressed state. Carries nothing. |
| `--color-ink-wash` | ink at 6% | A hover state, the secondary button's fill, the segmented control's track. Carries nothing. |
| `--color-ink-inverse` | `#ffffff` | Text on an ink or accent fill. |
| `--color-hairline` | `#e1e5eb` | A decorative divider. **Non-text and non-meaning only**: 1.20:1, and it is not supposed to be read. |
| `--color-hairline-strong` | `#85878c` | A line that carries meaning: a field's edge, a person's unreviewed note, a chart baseline. 3.41:1, meeting WCAG 1.4.11. |

The ladder steps are explained, and their ratios derived, in `ink-ladder.md`.

## Colour · the accent

| Token | Value | Job |
|---|---|---|
| `--color-accent` | `#114fa2` | The one hue. It means "you can act here" or "this is the focus": the primary button, links, the focus ring, the chosen relation on the canvas, the citation timestamp, and a provisional item's dashed line. 7.49:1 on the ground; white on it is 7.88:1. |
| `--color-accent-pressed` | `#063d85` | `:hover` and `:active` on a filled accent surface. |
| `--color-accent-wash` | `#e3eefe` | The accent's own tint. A selected row, a search match. **The only tinted surface in the system.** |

The accent is light, not line. It fills what is in focus or can be acted on
and it never outlines a container. The one line it is allowed to draw is the
provisional dash, and that is the point: a provisional item is exactly the
place a person can act.

The primitives behind these, `--palette-delft-*`, run from a tint (`100`) to a
deep text-on-tint blue (`950`). Components never bind them; see
`colour-schemes.md`.

## Colour · status

Six meanings. Closed set. Each is **always** drawn as a shaped 16px glyph plus
a word, so a status reads with no colour at all: roughly one in twelve men will
not see the difference between the green and the red, and a projector washes
both out.

| Token | Value | Glyph | Means | Word examples | Functions |
|---|---|---|---|---|---|
| `--color-status-capturing` | ink `#17181b` | a filled disc, beside a running timer | Capture is running. | Recording | F1.1, F6.1 |
| `--color-status-provisional` | the accent `#114fa2` | a dashed ring | The model made this. No human has accepted it. | Proposed | F3.5, F2.8 |
| `--color-status-accepted` | `#1d7344` | a ring with a tick | A human accepted it. Also: done. | Accepted, Done, Ready | F3.5, F6.5 |
| `--color-status-waiting` | `#8a5300` | a half-filled ring | Queued. The model is behind and catching up. | Queued, Catching up, Reading notes | F6.4 |
| `--color-status-failed` | `#a81f1a` | a ring with a bar | Could not read it. Transcription gap. Export failed. | Unreadable, Failed, Gap | F1.6, F6.4 |
| `--color-status-off` | `#595959` | a pair of bars | Paused, ended, consent withdrawn, archived. | Paused, Ended, Stopped, Archived | F6.1, F6.6 |

**Why provisional is the accent and not a hue of its own.** A provisional item
is precisely where a person can act: review it, accept it, edit it. That is the
accent's whole meaning. A second hue for provenance would put two hues on every
screen that has model output on it, which is every screen, and break the
one-hue rule for the one thing the rule most needs to hold for. Provisional is
told apart from an ordinary accent use by its dashed line, its dashed-ring
glyph and the word "Proposed", never by colour. The cost: on a page full of
accent buttons, colour no longer helps at all, and the shape and the word do
all of the work. They were always meant to.

**Why capturing is ink and not red.** Every product puts a red dot on a
recording light. This one cannot: it needs red for failure, and using one
colour for "working correctly" and "broken" is a worse failure than breaking a
convention. Ink is the strongest mark available on the ground. The indicator
carries a filled disc, the word "Recording" and a running elapsed timer, so the
state is carried by three signals, not one. It does not pulse: nothing in this
system loops.

**Why waiting is ochre.** The accent took the blue. Waiting sits at `#8a5300`
so it stays clear of the accent and of the failure red; the half-filled ring
and the word carry it where the hues come close.

Each status also has a `-wash` token, for a chip background. Each status
colour is AA as text on its own wash (measured in `accessibility.md`). Status
colour marks the glyph and the word; **it never fills a box, a chart or a
canvas item.**

**Never** use a status colour for a chart series, a category, an emphasis, a
brand moment or a hover. The set is reserved.

## Type

One face, Archivo, for everything. Six roles, eight size tokens, three
weights. See `typography.md` for which is which.

| Token | Size / line | Weight | Role |
|---|---|---|---|
| `--text-display` | 44/48 | 400 | Display: the one page title |
| `--text-heading` | 28/32 | 500 | Heading: a section or a screen's own heading |
| `--text-signal-lg` | 18/24 | 500 | Title: panel titles, the session name |
| `--text-signal` | 14/20 | 500, tabular | Body, as a figure: time, count, confidence |
| `--text-body` | 14/20 | 400 | Body: the default |
| `--text-signal-sm` | 12/16 | 500 | Label: structural labels, sentence case |
| `--text-meta` | 12/16 | 400 | Meta: supporting lines |
| `--text-caption` | 12/16 | 400 italic, muted | Meta, as a caption |

12px is the floor. Nothing renders smaller.

`--room-scale` is 1.5. Room mode, `data-room` on the root, multiplies every
size above by it. See `touch.md` § 0.

## Spacing

`--spacing-1` 4 · `-2` 8 · `-3` 12 · `-4` 16 · `-5` 24 · `-6` 32 · `-7` 48 ·
`-8` 64.

The rhythm: **8 inside a group, 24 between groups, 64 between sections, 32 for
the page margin.** Outside is always larger than inside, because proximity is
the first way a reader sees a group (`space-and-hierarchy.md`). The 4px step
exists as a micro-step *inside* a cell and nowhere else. If a gap between two
blocks is 4px, it is a mistake.

## Radii

| Token | Value | For |
|---|---|---|
| `--radius-xs` | 2 | Something nested inside a small control. |
| `--radius-sm` | 4 | Buttons, fields, chips. |
| `--radius-md` | 8 | Notes on the canvas, group panels, menus. |
| `--radius-lg` | 16 | The confirmation dialog and the photo stage. |
| `--radius-full` | 999 | Glyph discs and pills only. |

Corners grow with the surface: the bigger and more separate a surface is, the
rounder it is, so rank can be read from the corner. Nested radii are derived,
not picked; see `space-and-hierarchy.md` § 4.

## Lines

Line width carries meaning here, so the widths are tokens and not literals.

| Token | Value | Job |
|---|---|---|
| `--line-fine` | 0.5px | A divider between small items, inside a menu or a dense list. |
| `--line-hairline` | 1px | A divider between regions and rows, in `--color-hairline`. |
| `--line-boundary` | 1px | A field's edge, a person's unreviewed note's edge. Drawn in `--color-hairline-strong`. |
| `--line-provisional` | 1px | The dashed accent line on a model-made item. |
| `--line-focal` | 2px | The one relation in focus, a selected canvas item. |
| `--line-focus` | 2px | The focus ring. Never removed. |
| `--dash-provisional` | `4 4` | The `stroke-dasharray` for provisional items in SVG. Same everywhere, so the rhythm is recognisable. |

**Never a fill and a line on the same element.** A surface is told apart by
tone or by a line, and the two together say the same thing twice, which reads
as a box rather than a surface. That is also why each canvas state below uses
exactly one of them.

## Elevation

`--elevation-sm` · `--elevation-md` · `--elevation-lg`: two-layer shadows in
ink at low strength.

**Only for what floats above the page**: menus and popovers (`md`), the
confirmation dialog (`lg`), the session bar once the page scrolls under it
(`sm`). Nothing in the page has a shadow, ever. A shadow says "this is above
the page and will go away", which is true of a menu and false of a note. The
audit allows `box-shadow` only as one of these three tokens.

## Targets

`--target-desk` 32 · `--target-room` 44.

32px at a desk, where a mouse is precise and density matters. 44px in room
mode and on any coarse pointer, because the room screen is operated standing
up, at arm's length, by someone mid-sentence. See `touch.md`.

## Layout

`--layout-breakpoint` 1024 (the only one) · `--layout-rail` 384 (the side
panel beside the canvas) · `--layout-form` 400 · `--layout-gutter` 8 ·
`--layout-pad` 32 / `--layout-pad-narrow` 16 · `--layout-reading-max` 68ch.

## Motion

`--motion-fast` 150ms · `--motion-base` 200ms · `--motion-slow` 250ms ·
`--motion-ease` `cubic-bezier(0.23, 1, 0.32, 1)`.

Ease out, under 300ms, transform and opacity only. **Nothing loops**: no
spinner, no shimmer, no pulse. Work in progress is a word and a still mark.
There is no pulse token, because there is no pulse. All of it is gated behind
`prefers-reduced-motion` in `grid.css`. See `interaction.md`.

## Adding a token

Do not. Compose from what is here first. If the need is genuine: add it to
`tokens.css` with a comment saying what job it does, add its contrast pairs to
`contrast-check.py`, run that, and regenerate the table in `accessibility.md`.
A token without a stated job is how a design system dies.

## What changed in the new design, and why

Recorded so a reader can tell a deliberate change from a stale line.

- **The ground is no longer white.** `#ffffff` became `#f8f9fc`, a slightly
  cool neutral, and white moved up to `--color-surface-float`, for the things
  that float. Three tones now do the separating that hairlines did alone,
  because a tonal step groups from across a room where a 1px line disappears.
- **The surface-sunken tone gained a job.** It was restricted to skeletons,
  photograph placeholders and excerpts, and grouping was banned. It is now the
  group panel and the accepted note, because tone is the second instrument of
  separation after space, and it groups without drawing a box.
- **One hue.** The four colour schemes are removed and one palette, delft,
  remains. Provisional is now the accent; the violet is gone. See
  `colour-schemes.md` for what that costs.
- **Status is a shaped glyph, not an 8px dot.** Six shapes at 16px read
  without colour and survive a projector; six dots differed only in hue.
- **One face.** Archivo for everything; the second face is no longer loaded.
  Hierarchy comes from size, weight and ink. See `typography.md`.
- **Radii 8 and 16 exist.** Notes and panels at 8, the dialog and the photo
  stage at 16, so the corner says how separate a surface is.
- **Lines thinned.** The provisional line went from a 1.5px dash at `5 4` to a
  1px dash at `4 4`, and a 0.5px fine line and a 2px focal line were added.
- **Elevation exists, for floating surfaces only.** There was no shadow token
  at all. Menus and the dialog float, and pretending they do not, with a hard
  1px border, read as a box drawn on the page.
- **Motion is shorter and never loops.** 120/180/320 became 150/200/250, and
  the pulse token is gone.
- **Targets are tokens.** 32 at a desk, 44 in room mode and on touch.
