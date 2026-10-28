<!-- jarvaids-design-system:start: paste this block into the target repo's CLAUDE.md.
     Full spec: app/design-system/spec/ -->

# Jarvaids UI rules

You are generating UI for Jarvaids: a website that sits in a live design meeting,
takes the minutes, and organises the meeting visually onto a shared canvas from
voice and photographs. These rules are mandatory.

Canonical truth: `app/design-system/`. Tokens in `tokens.css`, layout in
`grid.css`, full spec in `spec/`, reference screens in `spec/exemplars/`, browser
implementation of the anatomies in `spec/exemplars/_base.css`. Build from
tokens; copy the exemplars' structure.

**Priority on conflict** (lower never overrules higher): `tokens.css` values →
`spec/forbidden.md` → `spec/accessibility.md` → `spec/exemplars/` → the rest of
`spec/` → host-repo conventions (code style only). Still ambiguous: build from
tokens, mark `/* PROPOSAL: <name> */`, raise it. Never invent silently.

## The look, in one line

One hue per screen, in tonal steps. Separate by space, then a tonal fill, then a
line, and **never a fill and a line on the same element**.

## The rule that outranks everything else

**Model output must be visibly distinguishable from the team's own work.**

| | Fill | Line | Word |
|---|---|---|---|
| Accepted | `--color-surface-sunken` | **none** | none needed |
| Model-made, not accepted | **none** | **1px dashed** `--color-status-provisional` (the accent), `stroke-dasharray` `4 4` | dashed-ring glyph + "Proposed" |
| A person's typed note, not yet reviewed | none | **1px solid** `--color-hairline-strong` | "Not yet reviewed" |

Text is **full ink in every state, never greyed**. The provisional colour is the
accent, so colour cannot tell a proposal from a button: the dash, the glyph and
the word do. Never fill a provisional item. Never move or overwrite a
hand-placed item (F3.4). Accepting fades the dash out and the fill in over
`--motion-slow` 250ms. A photographed note's paper colour is a small swatch on
the note, never its fill.

## Typography: one face, six roles

Archivo for everything. Weights 400, 500, 600. Sentence case. **No uppercase
labels.** 12px is the floor.

| Role | Token | Size | For |
|---|---|---|---|
| Display | `--text-display` | 44/48, 400 | The page h1, once. |
| Heading | `--text-heading` | 28/32, 500 | A section's heading; optional muted second line. |
| Title | `--text-signal-lg` | 18/24, 500 | Panel titles, the session name. |
| Body | `--text-body` | 14/20, 400 | Everything else. The default. |
| Body as figure | `--text-signal` | 14/20, 500, tabular | Times, counts, confidence on a body line. |
| Label | `--text-signal-sm` | 12/16, 500 | Field labels, column headers, a status word. |
| Meta | `--text-meta` · `--text-caption` | 12/16, 400 (caption italic, muted) | Second lines, hints, empty states, captions. |

- **Rule T2 (table row)**: rows are body text. The only figure in a row is a
  **fixed-width machine field** (timestamp, duration, count, percentage, ID)
  with `tabular-nums`. A speaker name is prose.
- A figure and a sentence on one line share a size and a **baseline**. Use
  `.jv-row`.
- A timestamp used as a **citation handle** is a figure, accent-coloured and
  clickable. A time in prose ("3 minutes ago") is meta.
- **Room mode**: `data-room` on the root scales every size by 1.5 and makes
  every target 44px. Set it on the projected display.

## Tokens: read `tokens.css`; these are the most-misused

| Job | Use | Not |
|---|---|---|
| the ground | `--color-canvas` `#f8f9fc` | white, which is for floating surfaces |
| primary text | `--color-ink` | black hex, `text-gray-900` |
| supporting text | `--color-ink-secondary` | any grey hex |
| meta / hints / placeholders | `--color-ink-muted` (**the text floor**) | anything lighter, opacity hacks |
| a group panel, an accepted note, an excerpt, a skeleton | `--color-surface-sunken`, no border | any other grey, a panel with a border |
| menus, popovers, the dialog, the session bar | `--color-surface-float` + `--elevation-*` | a border instead of the shadow |
| decorative divider | `--color-hairline` | shadows, black lines |
| a line that means something: field edge, unreviewed note, chart baseline | `--color-hairline-strong` (3.41:1) | `--color-hairline` |
| **the** accent: primary button, link, focus ring, chosen relation, provisional dash | `--color-accent` `#114fa2` | any second hue |
| selected row, search match | `--color-accent-wash` (the only tinted surface) | grey fills, a tint plus a border |
| hover / press | `--color-ink-wash` / `--color-ink-fill` | a shadow, a size change |
| radii | `--radius-xs` 2 · `-sm` 4 (buttons, fields, chips) · `-md` 8 (notes, panels, menus) · `-lg` 16 (dialog, photo stage) · `-full` | 6, 10, 12, arbitrary |
| lines | `--line-fine` 0.5 · `-hairline` 1 · `-boundary` 1 · `-provisional` 1 · `-focal` 2 · `-focus` 2 | arbitrary widths |
| shadows | `--elevation-sm/md/lg`, **floating surfaces only** | any shadow in the page, `shadow-md`, cards |
| targets | `--target-desk` 32 · `--target-room` 44 (room mode and touch) | smaller |

## Status: a closed set of six, always glyph + word

| Token | Glyph (16px) | Means | Words |
|---|---|---|---|
| `--color-status-capturing` ink | filled disc + timer | capture is running (F1.1, F6.1) | Recording |
| `--color-status-provisional` the accent | dashed ring | model made it, nobody accepted it (F3.5) | Proposed |
| `--color-status-accepted` green | ring with a tick | a human accepted it | Accepted, Done, Ready |
| `--color-status-waiting` ochre | half-filled ring | queued, model behind (F6.4) | Queued, Catching up |
| `--color-status-failed` red | ring with a bar | could not read, gap, failed export (F1.6, F6.4) | Unreadable, Gap, Failed |
| `--color-status-off` grey | pair of bars | paused, ended, withdrawn, archived (F6.1, F6.6) | Paused, Ended |

Never repurpose one for a category, a chart series, an emphasis, a hover or a
fill on a box. Capturing is ink, not red, because red is needed for failure;
the disc, the word and the running timer make it three signals. **Nothing
pulses.**

## Layout: `grid.css`, one breakpoint (1024px)

- `.jv-page` owns side padding (32, or 16 below 1024). Screens never add their
  own, and never add a `mx-auto` wrapper or a second breakpoint. No
  `sm:`/`md:`/`xl:`.
- Shapes: `.jv-workspace` (canvas + 384 side panel) · `.jv-split` (400 + rest)
  · `.jv-queue` (760 max) · `.jv-board` (the canvas: the page's own ground, no
  frame).
- `.jv-rows` is the default list. `.jv-mesh` is a compartment grid.
- **`minmax(0, …)` + `.jv-truncate` on every flexible text column.** This is the
  most common layout bug here.
- Rhythm: 8 inside a group, 24 between groups, 64 between sections. 4px only
  inside a cell. `.jv-scroll` once per screen.
- Z-order: content 0 · sticky 10 · session bar 30 · popovers 40 · dialogs 50.
- **ACTION is accent, STATE is ink.** A chosen segment and a chosen tab's
  underline are `--color-ink`, never accent.

## Components: anatomies in `spec/components.md`

Buttons: primary (accent fill) · secondary (`--color-ink-wash` fill, no line) ·
quiet (no fill, hover wash) · danger (red words; a red fill only in the
confirmation dialog). 32px at a desk, 44px in room mode and on touch; a form's
primary may be 40. One primary per view. Disabled always states its reason
beside it.

Fields: one anatomy. 1px `--color-hairline-strong` line, no fill,
`--radius-sm`, 40 tall (44 on touch), a **real `<label>`** above in sentence
case. Hover darkens the line, focus adds the ring, invalid only after touch.
Placeholders are not labels.

Session bar: sticky, white, `--elevation-sm` once the page scrolls, never
hides, never collapses. Carries the capturing glyph + word + timer, the
Quiet/Active mode (F4.4), who is present, **Undo** (F3.7), the consent record,
and End session.

Answer panel: **an answer without citations does not render** (F6.3). If the
model cannot cite it, show "I cannot find that in this session."

Degradation: a **hairline banner**, never a toast or a modal, never silent. It
says what broke **and what still works, in the same sentence**: "Transcription
has stopped. Audio is still being recorded." (F6.4)

Review queue: **evidence above the conclusion**. Actions in order Accept
(primary) · Edit · Reject (quiet). No accept-all. Corrections are kept as
evidence (F6.5) and the interface says so once, in the toolbar.

Side panel: non-modal. Export: a page. **The only modal is the confirmation
dialog**, for End session and Delete session.

Planned F3.8: content items are expandable sticky notes. Main points, group
labels and status stay visible; supporting detail unfolds in place. The planned
topic fills conflict with one hue per screen; until `spec/expandable-notes.md`
is revised, topic is a group label and a group panel, never a note fill.
Collapsed provisional notes offer Review; Accept belongs to full-content
review. This is future behaviour, not a claim about the current exemplar
screens.

## Interaction

- Motion: `--motion-fast` 150 (press, hover) · `--motion-base` 200 (expand,
  panel, menu) · `--motion-slow` 250 (accept only). Ease out, transform and
  opacity only, under 300ms. **Nothing loops**: no spinner, shimmer or pulse.
  Automatic updates never move team-arranged notes. User-triggered F3.8
  expansion may apply temporary local display offsets, never saved moves. All
  of it gated behind `prefers-reduced-motion`.
- Focus ring on **everything** interactive, 2px accent, applied globally in
  `grid.css`. Removing it is a WCAG 2.4.7 failure.
- On a coarse pointer, at any width, there is no hover: every hover-revealed
  action is permanently visible, and targets are 44px.
- **Agreement before capture.** Capture cannot start until everyone present has
  agreed (F6.1).
- Confirm only End session and Delete session. Never confirm rejecting an item
  or a cluster. **Undo is not optional** (F3.7): in place on the row, and in the
  session bar. No toasts.
- Loading: still skeletons on first load only. Never spinners; a spinner in a
  live meeting says "wait" and nobody is waiting.
- Quiet mode is the default. Switching to Active shows a one-line consequence.

## Accessibility (WCAG 2.1 AA, contrast verified)

- Every shipped colour pair is measured in `spec/accessibility.md`: 40 pairs,
  0 failing, one scheme. **Add any new pair to `spec/contrast-check.py`, run it,
  and regenerate the table with `--markdown`.** Never eyeball a ratio, never
  hand-edit the table.
- **Bind semantic tokens (`--color-*`), never primitives (`--palette-*`) and
  never a literal.** The `[data-scheme]` mechanism repoints the semantics; a
  component that reaches past them does not change. There is one scheme,
  delft; no attribute selects it. See `spec/colour-schemes.md`.
- **Never colour alone.** Provisional is a dashed line, no fill, and "Proposed".
  Status is a shaped glyph *and* a word. Confidence is a number, not a colour
  ramp.
- Native elements or real ARIA widgets. Never a `div` with `onClick`.
- One `h1`, headings in order, real `<label>`s, landmarks (`header`, `main`,
  `aside`, `nav`).
- The canvas needs its **parallel list view**, reachable from the segmented
  control on the canvas screen, not hidden in a setting.

## Copy: English, sentence case, verb-first

Buttons are verbs: Accept, Reject, Start session, End session, Export canvas.
Status words are single words. Meta lines use interpuncts (`6 present · 2 not
yet agreed`). 24-hour times, `15 September 2026` dates, British spelling.
**No em dashes, no exclamation marks, no emoji, no "please".**

Settled vocabulary: Proposed (on screen; `provisional` is the token's name for
the state) · Accept (not Approve) · Reject (not Delete, the item is kept) ·
Recording (not Live) · Session (not Meeting) · Canvas (not Board, which is an
export destination) · Item (not Card) · Gap (not Silence) · Unreadable (not
Error) · Catching up (not Please wait).

Say what happens next, not what happened. State what still works when something
breaks. Never claim certainty the model does not have: an uncertain speaker is
"Unknown speaker", never a guessed name.

## Forbidden: the short list

1. No colour, size, radius or line-width literals. Tokens only.
2. One face. No web font over the network. No uppercase labels. No icon
   package; icons are inline SVG on `currentColor`.
3. No shadow in the page; elevation tokens on floating surfaces only. No
   decorative cards, no gradients. Never a fill and a line on one element.
4. One hue per screen. No second hue for a topic or a paper colour.
5. Nothing loops. No toasts, no spinners, no modal except the confirmation
   dialog, no illustration.
6. No UI framework, no vendored component library.
7. No CDN in any exemplar or in the specimen: they must open offline.
8. No `dark:` variants. Dark mode does not exist here (see `forbidden.md` for
   what adding it would take).
9. Never render model output identically to team output.

Full detail in `spec/`: principles · typography · tokens · ink-ladder ·
colour-schemes · space-and-hierarchy · patterns · components · controls ·
interaction · touch · accessibility · dataviz · copy · forbidden · checklist.
Off-system checks in `AUDIT.md`.

<!-- jarvaids-design-system:end -->
