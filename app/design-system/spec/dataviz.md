# Dataviz

Jarvaids is a visual tool, but it is a *spatial* one, not a charting one. Its
main visual output is a canvas of items arranged to mean something, and that
is not a chart. This file covers both: the canvas forms first, because they
are what the product does, then the small number of real charts it needs.

---

## Part 1: Canvas forms

The model picks a form for the content and places items in it (F3.2, F3.3).
Defaulting to a cluster every time is the failure mode: a cluster of everything
is a list with extra steps.

| Content shape | Form | Why not the neighbour |
|---|---|---|
| Things that belong together but have no order | **Cluster** | A timeline on unordered things invents a sequence that was never said. |
| Things with a before and an after | **Timeline** | A cluster of ordered things loses the only structure they had. |
| Things scored on two independent axes | **Matrix** | A cluster hides the trade-off the two axes exist to show. |
| Things where one leads to the next | **Flow** | A timeline says "then"; a flow says "therefore". They are different claims. |
| Things at levels of a whole | **Hierarchy** | A flow implies causation between siblings that are only categories. |

**The form is a claim the model is making about the content, and it is
provisional like anything else.** A timeline the model built is drawn with a
dashed spine until a human accepts the *arrangement*, separately from accepting
the individual items.

### Expandable notes within forms, planned

Sticky notes hold main points and supporting detail; forms express relationships
between them. Expansion must preserve group membership, ordering and connector
endpoints. Keep axis markers fixed when opening detail so spacing cannot invent
a new date or score. AI organisation of incoming notes remains provisional and
respects team adjustments; unsupported structure falls back to the original
arrangement or a simple ordered set. See [expandable notes](expandable-notes.md).

### Drawing the forms

Structural forms are drawn on the canvas's own ground with one hue and in
tonal steps: a group is a tone or an outline, never a coloured background, and
never both a fill and a line.

- **Cluster**: while proposed, a 1px dashed hull in
  `--color-status-provisional` (the accent) with no fill; once accepted, a
  `--color-surface-sunken` panel at `--radius-md` with no line. The same two
  forms as a single note, so a reader learns one distinction and not two. The
  cluster label is a label: on the dashed line on a `--color-canvas` backing
  for a proposed cluster, inside the panel's top-left for an accepted one.
- **Timeline**: one horizontal 1px `--color-hairline-strong` spine. Ticks are
  1px, 8px tall. Tick labels are labels in `--color-ink-muted`. Items sit above
  the spine, connected by a 1px drop line.
- **Matrix**: two 1px `--color-hairline-strong` axes crossing, four quadrant
  labels in `--color-ink-muted` at the outer corners. No quadrant fills, no shading.
  Shading a quadrant to mean "good" is a judgement the tool does not get to
  make.
- **Flow**: 1px `--color-hairline-strong` connectors with a 6px arrowhead.
  Provisional connectors are dashed with `--dash-provisional`.
- **Hierarchy**: 1px orthogonal connectors, no curves.

### Colour on the canvas

**Open for the team.** F3.8 planned a distinct sticky-note fill per main
topic, subject or choice. The design adopted since has one hue per screen, and
a set of topic fills would put several hues on every canvas. The two cannot
both hold, and the team has not yet decided which gives way. Until it does,
this is the holding position:

- **Topic is shown by the group, not by the note.** A topic is a cluster: its
  label names it, and its tonal panel (accepted) or dashed outline (proposed)
  contains it. Notes take no topic fill. Keep the grouping stable and editable
  by the team, and keep the group label visible on the canvas and in the list
  view, so the topic reads without any colour at all.
- **State is separate:** provenance and review status remain the note's own
  forms, a tonal fill, a dashed line or a solid line, plus a glyph and a word.
  Nothing about a topic may imitate them: a topic panel around proposed notes
  must not make them look accepted, which is why each note keeps its own dashed
  line inside an accepted group.
- **Paper colour is evidence:** a photographed note's paper colour is kept as
  metadata and shown as a small swatch on the note, beside its source handle,
  never as its fill. It may suggest a group, but it is not a topic.
- No categorical note palette exists in `tokens.css`. If the team decides for
  topic fills, the [expandable-note contract](expandable-notes.md) lists what
  must be tested first, and `principles.md` #1 is what that decision would be
  arguing against. Chart rules below remain separate.

---

## Part 2: Charts

Jarvaids needs very few. Session statistics, and the evaluation data (F6.5).
Everything here is deliberately minimal.

### Which form

| Data shape | Use | Not |
|---|---|---|
| One number with no series | **A figure**, `--text-heading` with tabular numerals, with a label above it | A chart of one point is a number with noise around it. |
| Comparison across a handful of categories | **Bar** | A line implies a progression between things that do not flow into each other. |
| Something over the session's timeline | **Line** | Bars per minute turn a movement into a row of blocks. |
| One value against a whole | **A track bar**: 8px tall, `--radius-full`, track `--color-ink-wash`, fill `--color-ink`, the figure beside it, tabular | A donut for one value is a decorated percentage. |
| Anything inside a table row | **The track bar**, 4px | A chart cannot be under 40px tall and stay readable. |

There is no pie, no radar, no stacked anything, and no second axis. If the data
needs a second axis it is two charts.

### Anatomy

- **One axis.** Horizontal gridlines only, 1px `--color-hairline`. The
  baseline is 1px `--color-hairline-strong`. No vertical gridlines, no frame.
- **Tick labels** are meta, muted, for words, and `--text-signal-sm` with
  tabular numerals for numbers.
- **Values are labelled selectively**: the last point, the maximum, the one
  being discussed: never every point.
- Bars are flat, square-cornered, 2px apart.
- Lines are 1.5px, with a marker only on the last point or on hover.

### Series colour

- **One series has no colour.** It is `--color-ink`. The accent belongs to
  interaction, and a single series has nothing to distinguish itself from.
- **Two series**: `--color-ink` and `--color-hairline-strong`, distinguished by
  a direct label. Not by colour.

  It is a declared token and not an opacity on ink. Ink at 30% composites to
  `#b8b8b8`, which is 1.98:1 against the canvas, and WCAG 1.4.11 asks 3:1 of a
  graphical object that carries information. A chart series carries
  information. `--color-hairline-strong` is 3.47:1 against the canvas and
  5.32:1 against ink, so the two series are told apart and the weaker one is
  still visible on a washed-out projector. An opacity would also be invisible
  to `spec/contrast-check.py`, which reads declared values, so the system
  could not have caught its own failure.
- **Three or more**: this system does not have a categorical chart palette, on
  purpose. The status colours are reserved and cannot be borrowed, and inventing
  a chart palette would double the colour vocabulary for a need this product
  has not evidenced. If three series are genuinely needed, build small
  multiples: three small charts side by side, each with one series. That is a
  better chart anyway and it costs no new tokens.
- **Status colours are never a series colour.** Not once, not "just this one".

This is a real limitation and it is deliberate. The cost: a stacked composition
chart is not available. If the evaluation work needs one, that is a token
proposal with a contrast check attached, not a local decision.

### The evaluation chart (F6.5)

The one chart this product owes its own course project: corrections over a
session. A bar per category of model output (notes, layout, decisions, minutes),
showing accepted versus corrected versus rejected.

Since three values per category cannot be three colours, it is drawn as three
small charts, one per outcome, sharing an axis range. Same data, no palette,
and the comparison is easier to read than a stacked bar would have been.

### Always

- Every chart is accompanied by **the same data as a table**, reachable from
  the chart. That is the 1.4.11 route and it is also just good practice.
- Empty is one sentence in caption muted. Loading is a skeleton in the plot's
  shape. Neither is a spinner.
- Entry animation: bars grow from the baseline over `--motion-base`, once,
  never on filter changes. Off under `prefers-reduced-motion`.

---

## The one exception: architecture diagrams in documentation

Everything above refuses a category palette, and that refusal still holds
everywhere it applied before. This is the single named exception to it, and it
is bounded deliberately.

**Where it applies.** Architecture and flow diagrams inside the team's
documentation: `deliverables/documentation/flowchart.html` and
`pipelines.html`. Nowhere else. Never in a product screen, never on the canvas,
never in a chart.

**Why a diagram is different from the canvas.** The canvas shows the team's own
content, and a colour there would be a claim the machine is making about what
the content IS. A diagram shows the system's structure, where the single most
important fact about any box is who or what is acting in it: a person, a model,
or a rule that nothing may cross. A reader takes that in across forty boxes at
once, from a distance, in a review. Words alone make them read every box to
learn what they could have seen.

**What it is.** Exactly three tokens, in `tokens.css`:

| Token | Means | On canvas |
|---|---|---|
| `--color-diagram-human` | a person is acting | 7.21:1 |
| `--color-diagram-machine` | a model runs here | 6.33:1 |
| `--color-diagram-guardrail` | a hard limit nothing may cross | 11.04:1 |

**The rules that keep it bounded.**

1. **Three, and the set is closed.** A fourth is a spec change, argued the way
   a seventh status colour would be.
2. **Colour is redundant, never load-bearing.** Every box also carries its kind
   in words on its edge. Remove the colour and the diagram still reads: in
   greyscale, on a projector that has crushed the contrast, and to a reader who
   cannot separate the hues. The colour makes a diagram faster, it never makes
   it possible.
3. **These are not status colours and status colours are not these.** The
   reserved six exist so a colour means one thing. Borrowing one here would
   make it mean two.
4. **The machine colour never replaces the dashed edge.** Model stages are
   drawn with `--dash-provisional`, and the colour sits with it. The dash
   first, colour second, as on the canvas, where the dash is now the only
   signal colour does not duplicate.
5. **Product UI gets none of this.** If a screen wants to distinguish kinds of
   thing by colour, the answer is still no, and the answer is still words.
