# Forbidden

These are the things that make generated or hand-written UI drift off-system.
`../AUDIT.md` says how to check for them. Everything here is a hard rule, not a
preference. The numbers are stable, because other files cite them; a rule that
the new design reversed keeps its number and says what replaced it.

## Literals

1. **No colour literals.** Every colour comes from a `tokens.css` token. No
   hex, no `rgb()`, no named colours, no Tailwind palette classes
   (`bg-gray-100`, `text-slate-500`). Opacity uses the slash syntax on a token.
2. **No arbitrary font sizes.** `text-[13px]`, `font-size: 17px` and friends
   are wrong. Eight size tokens exist; use one.
3. **No arbitrary radii.** The scale is 2 / 4 / 8 / 16 / full. There is no 6,
   10 or 12.
4. **No arbitrary line widths.** Six exist, 0.5, 1 and 2px, and each means
   something.
5. **No colours or sizes in `style={{}}`.** Inline style is for computed values
   only: a measured position on the canvas, a transform, a z-index.

Layout dimensions are exempt: `width: 400px`, `max-width: 760px`,
`grid-template-columns: minmax(0, 400px) minmax(0, 1fr)` are content decisions
and are allowed. Keep them on the 4px rhythm where a token exists.

## Fonts

6. **No second face.** Archivo, for everything. No icon font, no monospace, no
   "just for this one heading". Hierarchy is size, weight and ink.
7. **No web font loaded over the network.** Archivo is vendored in
   `../fonts/`. A `@import` from a font CDN is a privacy leak in a product that
   records people, and it breaks the offline case the specimen and exemplars
   are built for.
8. **Nothing renders below 12px**, and nothing is set in uppercase. 12px is
   the label, meta and caption size; uppercase at that size loses its word
   shapes at distance.

## Surfaces and separation

9. **No decorative cards and no shadows in the page.** A note is a tonal fill
   or a line, never a raised card. `box-shadow` exists only as
   `--elevation-sm`, `-md` or `-lg`, and only on a surface that floats above
   the page: a menu, a popover, the confirmation dialog, the session bar once
   the page scrolls. A shadow says "above the page and will go away", which is
   false of everything in it.
10. **Grouping by tone uses `--color-surface-sunken`, and nothing else.** This
    rule used to ban grey grouping panels outright. The new design reverses
    that: separate by space first, then by a tonal fill, then by a line. A
    group panel is `--color-surface-sunken` with no border. What stays banned
    is any other grey, any tinted panel, and a panel that also has a border.
11. **No gradients.** None. Not on a button, not behind a heading, not as a
    scroll fade.
12. **Never a fill and a line on the same element.** A surface is told apart by
    tone or by a line; both together read as a box. Black is not a separator:
    two line colours exist, `--color-hairline` for a decorative divider and
    `--color-hairline-strong` for a line that carries meaning. Ink appears as a
    line only where it carries meaning: a chart's single series, the chosen
    tab's underline.

## Colour discipline

13. **Status colours are reserved.** Never as a chart series, a category, an
    emphasis, a hover tint, a brand moment, a fill on a box or a canvas item.
    Six colours, six meanings, closed set.
14. **The accent is not a mood.** It marks the place you can act, or the focus.
    It is never a heading colour, never a decorative rule, never a section
    theme, never a container outline, and never a warning.
15. **One hue per screen.** There is one accent, in tonal steps. No second
    hue: not for a topic, not for a paper colour (that is a small swatch on the
    note, never its fill), not for a brand moment.

## The provisional distinction

16. **Never render model output identically to team output.** This is the one
    rule that, broken once, makes the product dishonest. Anything the model
    made carries a 1px dashed accent line, the dashed-ring glyph and the word
    "Proposed" until a human accepts it (F3.5).
17. **Never grey out a provisional item.** Unreviewed is not unimportant, and
    greying it makes it harder to review. No `opacity`, no `--color-ink-muted`
    on its text.
18. **Never fill a provisional item.** A provisional note has no fill: the
    signal is the dashed line plus the word, and a fill would make it look
    accepted, because a tonal fill is exactly what acceptance looks like.

## Patterns

19. **No toasts.** A state change is shown where the thing is, and Undo is in
    place on the row and in the session bar.
20. **No modals except the confirmation dialog**, and the confirmation dialog
    is only for End session and Delete session. The side panel is non-modal.
    Export is a page.
21. **Nothing loops.** No spinner, no shimmer, no pulse. Skeletons, still, for
    first load; a waiting glyph and a word for work in progress.
22. **No illustration, no photography as decoration, no icon-only buttons
    without an accessible name.** Photographs appear as data (the wall, the
    sketch), never as atmosphere.
23. **No `sm:` / `md:` / `xl:` breakpoints.** One breakpoint, 1024px. Room
    mode and the coarse pointer are not width tiers; see `touch.md`.
24. **No second scroller on a screen.** `.jv-scroll` is used once.

## Dependencies

25. **No UI framework.** No MUI, Chakra, Ant, Mantine, DaisyUI, no vendored
    component library. Components are built from these tokens.
26. **No icon package.** Icons are inline SVG, 16px in a row, 20px in a bar,
    `currentColor`, `stroke-width: 1.5`. Every icon that is not next to a word
    has an accessible name. The six status glyphs follow the same rule.
27. **No CDN of any kind in an exemplar or in the specimen.** Those files must
    open offline by double-click. This is checked by the audit.

## Dark mode

28. **No hand-rolled `dark:` variants.** Dark mode does not exist in this
    system and adding it locally is worse than not having it.

It is not an oversight. The whole product is a light ground standing in for a
whiteboard, with the provisional distinction carried by a dashed blue line on
it, and three surfaces told apart by tonal steps that only work in one
direction. Inverting that means re-deciding the provisional line, the tonal
steps, the elevation, the status washes and every contrast pair. That is a real
piece of work and it is out of scope here. If it is taken on: add a
`[data-theme="dark"]` block redefining only the semantic tokens, extend
`contrast-check.py` with the dark pairs, and re-run the whole table. Do not
start until you are doing all three.

## The escape hatch

Needing something not covered here is not permission to invent. Compose from
tokens and existing patterns first. If the need is genuinely new:

1. Build it from tokens.
2. Mark it `/* PROPOSAL: <name>: not yet in the design system */`.
3. Raise it, with the contrast numbers if it introduces a colour pair.

A silent invention is indistinguishable from a bug six weeks later.

## Categorical colour

29. **No colour that means "this is a kind of thing".** Not on the canvas, not
    in a chart, not in a product screen. Kind is said in words. The one
    exception is the three `--color-diagram-*` tokens, which apply only to
    architecture diagrams in `deliverables/documentation/` and are bounded by
    five rules at the end of `spec/dataviz.md`. Using one of them in a product
    screen is a violation of this rule, not a use of the exception.
30. **A diagram colour never carries meaning on its own.** Every box it colours
    also says its kind in words. Delete the colour and the diagram must still
    read. If it does not, fix the diagram, not the palette.
