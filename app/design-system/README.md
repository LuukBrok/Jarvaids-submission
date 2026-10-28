# Jarvaids design system

A design system for **Jarvaids**: a website that sits in a live design meeting,
takes the minutes, and organises the meeting visually onto a shared canvas from
voice and photographs. Its screens are the live canvas, the session and
transcript panel, the review queue, session setup and consent, and export.

This is the **design layer only**. There is no CLI, no build tooling, no npm
package and no component library. It is tokens, layout primitives, a written
spec, five reference screens and a specimen page. Everything here opens in a
browser by double-clicking it.

## The system in one paragraph

One hue per screen, in tonal steps. A single blue accent, `#114fa2`, meaning
"you can act here" or "this is the focus"; a slightly cool neutral ground,
`#f8f9fc`; a sunken tone, `#ebeef2`, for group panels and accepted notes; and
white for the surfaces that float, which are the only things allowed a shadow.
Separation is space first, then a tonal fill, then a line, and never a fill and
a line on the same element. One typeface, Archivo, in six roles and three
weights, sentence case throughout. Six status meanings, a closed set, each drawn
as a shaped 16px glyph beside a word so that colour never carries meaning
alone, and nothing that pulses or loops. And one rule that outranks the rest:
anything the model made has no fill, a 1px dashed accent line and the word
"Proposed" until a human accepts it, when it takes the settled tonal fill, so
that nothing Jarvaids produces is ever indistinguishable from what the team
made. On a projector, room mode scales the type by 1.5 and makes every target
44px.

There is one colour scheme, delft. The four earlier schemes are removed; the
`[data-scheme]` mechanism stays so that a future scheme is a block in
`tokens.css`, not a rewrite.

## What is here

| | |
|---|---|
| `tokens.css` | Tailwind v4 `@theme`. The single source of truth for every colour, size, radius, line width and duration. Every token is named by role, not by appearance. |
| `grid.css` | Layout primitives: page frame, the four page shapes, hairline row lists, truncation, focus, reduced motion, touch targets, print. Not yet brought up to the new design; see `spec/exemplars/_base.css`, which has been. |
| `specimen.html` | The whole system on one page, with every contrast ratio printed next to its pair. Opens offline. Start here. |
| `schemes.html` | The one scheme, delft: its tonal steps, the six status glyphs at 16px with and without their words and in greyscale, and the three provenance states side by side. Opens offline. |
| `fonts/` | Archivo as variable woff2 with its SIL OFL licence. |
| `spec/` | The spec, by topic, written to be read by a coding agent. |
| `spec/ink-ladder.md` | One colour at six strengths, 100/76/68/50/10/6. Why the neutrals are a ladder and not six greys, where the floors are, and why the ground must be known. |
| `spec/colour-schemes.md` | The scheme mechanism, the primitive and semantic layers, the one scheme with what it costs, and what removing the other three cost. |
| `spec/space-and-hierarchy.md` | Space, then tone, then line. Hierarchy without decoration, the reading-distance arithmetic behind room mode, the concentric corner rule at the new radii, and what was decided about materials. |
| `spec/canvas-layout.md` | How the canvas is laid out: item sizing, separation, placement, collision, overflow, zoom, density. The contract the layout engine implements. |
| `spec/expandable-notes.md` | Planned F3.8 sticky-note main points, in-place detail, organisation, review and acceptance scenarios. Not yet implemented. |
| `spec/tables.md` | Column grammar, sorting, selection, bulk actions, pagination. The transcript and the review queue are tables. |
| `spec/controls.md` | Checkbox, radio, switch, tooltip, popover, menu, `kbd`, field errors, busy buttons. |
| `spec/touch.md` | Room mode, and the touch canon. The signal for touch is `pointer: coarse`, not width; the signal for the projector is `data-room`. Plus the phone capture flow. |
| `spec/announcements.md` | What is announced and what is deliberately silent, region by region. Skip link, landmarks, dialog semantics. |
| `spec/exemplars/` | Five self-contained reference screens, one per Jarvaids screen, meant to be copied. |
| `spec/contrast-check.py` | Reads `tokens.css`, including any scheme blocks, computes every pair's WCAG ratio, measures how far apart the status marks are, prints both tables, exits non-zero on a failure. |
| `CLAUDE-fragment.md` | The distilled rulebook, to paste into a repo's `CLAUDE.md`. |
| `spec/audit.sh` | The mechanical half of the audit. Runs the contrast check and every grep, one exit code, resolves its own paths. |
| `AUDIT.md` | What counts as off-system: what the script checks, and the judgement half it cannot. |

## How to use it

**Reading it.** Open `specimen.html` in a browser. Then read
`spec/principles.md` and `spec/typography.md`. Then open the exemplar for the
screen you are building.

**Building a screen.** Copy the closest exemplar from `spec/exemplars/` and
replace its content. The exemplars link `spec/exemplars/_base.css`, which is a
flattened plain-CSS copy of the tokens for browser use. In a real Tailwind v4
application you would import `tokens.css` and `grid.css` instead; `_base.css`
exists because `@theme` does not resolve in a browser on its own.

**Building with an agent.** Paste `CLAUDE-fragment.md` into the repo's
`CLAUDE.md` and point the agent at `spec/` for detail.

**Changing a colour.** Change it in `tokens.css`, add its pairs to
`spec/contrast-check.py` if they are new, run the script, and regenerate the
table in `spec/accessibility.md` with `--markdown`. Do not hand-edit that table
and do not eyeball a ratio.

**Projecting.** Set `<html data-room>` on the shared display. Every size scales
by 1.5 and every target becomes 44px; nothing else changes. See
`spec/touch.md` § 0.

**Adding a colour scheme.** There is one, and the design's first principle is
one hue per screen, so a second scheme is a decision to argue, not a
preference to add. If it is argued: `spec/colour-schemes.md` has the six steps.
The short version is a `--palette-<name>-*` block and a `[data-scheme]` block
in `tokens.css`, then `python3 spec/contrast-check.py`, which finds the new
scheme by itself and must exit 0.

## What is deliberately forbidden

The full list is `spec/forbidden.md`. The short version:

- No shadow in the page. Only floating surfaces (menus, popovers, the
  confirmation dialog, the session bar once the page scrolls) carry an
  elevation token. No decorative cards, no gradients.
- Never a fill and a line on the same element. Grouping is space, then
  `--color-surface-sunken`, then a line.
- One hue per screen. No second hue for a topic or for a note's paper colour,
  which is a small swatch on the note, never its fill.
- No second typeface, no uppercase labels, and no font loaded over the network.
- No colour, size, radius or line-width literals. Tokens only, and semantic
  tokens (`--color-*`) rather than the primitives (`--palette-*`) that sit
  underneath them.
- Nothing loops: no spinner, no shimmer, no pulse.
- No toasts. Undo is in place on the row and in the session bar.
- The only modal is the confirmation dialog, for End session and Delete
  session. The side panel is non-modal; Export is a page.
- No UI framework and no vendored component library.
- No breakpoints other than 1024px. Room mode and the coarse pointer are not
  width tiers.
- No dark mode, and no hand-rolled `dark:` variants.
- **Never render model output identically to team output.** Break this once and
  the product is dishonest.

## Accessibility

Target is WCAG 2.1 AA. **Contrast is verified; the product does not conform
yet.** 40 foreground/background pairs are computed from the shipped token
values by `spec/contrast-check.py` and all 40 pass. That is fifteen pairs no
colour scheme moves plus twenty-five measured for the one scheme. But two Level A criteria are known to be unmet today: SC 2.1.4,
because the review queue's single character shortcuts have no off switch,
remap or focus scope, and SC 2.1.1 for the canvas, because direct manipulation
(F3.6) has no keyboard path. Both fixes are specified and neither is applied. The full
statement, and what has and has not been tested, is in
`spec/accessibility.md`.

Status is never carried by colour alone: every status is a shaped glyph and a
word, and the six shapes are distinct in greyscale. The provisional distinction
is carried by form and word only, a dashed line with no fill and "Proposed"
against a tonal fill with no line, because the provisional colour is the accent
itself. It survives both colour blindness and a projector washing out.

## Honest limitations

- **The canvas is not keyboard-navigable in this spec.** Arrow-key traversal of
  a spatial board is a genuine design problem and this system does not solve it.
  It requires a parallel list view of the canvas instead. That is a mitigation,
  not a solution.
- **Nothing here has been tested with a screen reader.** The semantics are
  specified correctly as far as the spec goes. Whether they work in NVDA, JAWS
  or VoiceOver is unverified.
- **Contrast was verified by computation, on an ideal display.** Projectors
  crush contrast badly, and this product lives on projectors. A check in the
  room the team will present in is still owed. It matters more in the new
  design, because the sunken tone that now groups is a 1.11:1 step from the
  ground, exactly what a projector erases.
- **Room mode has to be switched on.** A shared screen projected without
  `data-room` shows 14px body that reads like 11px from the back of the room.
  Nothing sets it automatically yet.
- **There is no tablet layout.** One breakpoint means a 900px screen gets the
  phone layout. Deliberate, because this product's phone is a camera and its
  desktop is the room screen, and a tablet is neither. Note that this is a
  layout decision only. A tablet gets full touch treatment regardless of its
  width, and so does the room touchscreen, because interaction is keyed on
  pointer, not on width. See `spec/touch.md`.
- **The audit is greps and a looking list.** `spec/audit.sh` and the contrast
  check run in CI on every pull request, but greps catch literals and most of
  the ways this system gets broken are judgement, which is `AUDIT.md`
  section 5.
- **There is no categorical chart palette**, on purpose, because the status
  colours are reserved, the design has one hue, and inventing a palette would
  double the colour vocabulary for a need this product has not evidenced. The cost is that a stacked composition
  chart is unavailable; `spec/dataviz.md` explains the small-multiples route
  instead.
- **Dark mode does not exist.** Adding it means re-deciding the provisional
  line, the tonal steps, the elevation, the status washes and every contrast
  pair. It is a real piece of work, not a `dark:` prefix.
- **The new design has not been seen on a projector.** The separation figure in
  `spec/colour-schemes.md` is CIEDE2000, which was fitted to large flat patches
  side by side and not to 16px glyphs across a room. The glyphs were looked at
  in `schemes.html`, which is a laptop.
- **The exemplars are not yet redrawn.** `spec/exemplars/_base.css` carries
  the new tokens, glyphs and canvas states, but the five exemplar screens still
  use the older 8px dot markup in places, kept working by a compatibility rule.
- **Materials were decided, in part.** Tonal surfaces, group panels, larger
  corners and elevation for floating surfaces were adopted; translucency and
  blur were not, because every contrast ratio here assumes an opaque, known
  ground. `spec/space-and-hierarchy.md` § 5 has the reasoning.

## Fonts and licensing

One face is vendored as variable woff2, subset to Latin, in `fonts/`:

- **Archivo**, SIL Open Font License 1.1, `fonts/LICENSE-Archivo.txt`

The OFL permits bundling and redistribution, including in a commercial product,
provided the licence travels with the font and the font is not sold on its own.
The licence file is the compliance; keep it next to the binary.

It ships as one variable file covering weights 400 to 700, of which the system
uses 400, 500 and 600. The `@font-face` declaration carries a real fallback
stack, so a page still reads if the binary fails to load. The second face the
system used to carry has been removed from `fonts/` with its licence, since
nothing loads it.

## Planned topic-coloured sticky notes

F3.8 planned a distinct sticky-note fill per main topic, subject or choice. That
plan predates the one-hue rule and conflicts with it: several topic fills would
put several hues on every canvas. Until [the contract](spec/expandable-notes.md)
is revised, topic is carried by group labels and group panels, and a
photographed note's paper colour is a small swatch on the note, never its fill.
No categorical note palette is in the tokens or the contrast results.
