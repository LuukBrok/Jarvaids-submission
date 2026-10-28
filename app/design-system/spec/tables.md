# Tables

Two of Jarvaids's five screens are tables and neither of them says so. The
transcript is a three-column table of a few thousand rows (F1.2, F1.3). The
review queue is a two-column table of a few dozen (F3.5). Both were built by
inventing a grid in a screen-local `<style>` block, which is how two people
building two tables end up with two different tables.

This file is the column grammar. It does not introduce a new component: a
Jarvaids table is the row list from `components.md` §9 with a declared column
contract, a header, and a set of rules about what happens when there are more
rows than fit.

**There is no new token in this file.** If a table needs a value that is not
already in `tokens.css`, the table is wrong.

---

## 1. The column contract

A table declares its columns in exactly one place, and that declaration has
two halves:

```
template   the grid-template-columns line
collapse   the container width below which the row stops being columns
```

Both halves live together, in `grid.css`, as one class. A screen never writes
a `grid-template-columns` of its own. A column template split across a
component file and a media query in a page is the bug this section exists to
prevent.

### Declaring a template

```
grid-template-columns:
  <fixed>          a machine field: timestamp, count, confidence, state
  minmax(0, 1fr)   the one column that carries prose
  <fixed>          the actions, if any
```

Rules:

- **Fixed columns are fixed, never `auto`.** A machine field is the same width
  in every row (Rule T2, `typography.md`), so it gets a track in pixels. `auto`
  lets one long value in row 300 change the width of the column, which makes
  the timestamps appear to jitter as you scroll. Track widths are layout
  dimensions, which the "Literals" section of `forbidden.md` exempts, so a
  literal is correct here.
- **Exactly one column is `minmax(0, 1fr)`**, and it is the prose column. The
  `minmax(0, …)` is not optional. Without the zero minimum a long unbroken
  string sets the track's minimum to its own width and pushes the whole grid
  sideways. This is the most common layout bug in this system and
  `patterns.md` already says so.
- **Five columns is the ceiling on a desktop.** At the rail width
  (`--layout-rail`, 384) and at `--layout-reading-max`, a sixth column either
  truncates something that must not truncate or forces a sideways scroll. If
  a table seems to need six, one of them is a second line inside a cell.

### Where truncation is forbidden

`.jv-truncate` belongs on flexible text cells. It does not belong on these:

- **A provisional item's text** (F3.5). The reviewer's job is to judge exactly
  those words. An ellipsis hides the half of the sentence where the model went
  wrong, and a reviewer who cannot see the whole guess accepts it on faith,
  which is the failure this product is built to prevent.
- **A citation excerpt** (F6.3). A cut citation is not a citation. "Then the
  paywall is out of sco…" cannot be checked against the audio.
- **A person's name in a consent row** (F6.1). A truncated name in a consent
  record is a records problem, not a layout one.
- **An error sentence.** It has to say what still works, and that clause is at
  the end (`components.md` §13).

Those cells wrap instead, on `overflow-wrap: anywhere`, and the row grows. A
row growing to fit its content is correct behaviour, not a layout failure.

## 2. Row height

Three densities. A density is a `padding-block` value, not a pixel height.

| Density | `padding-block` | One line of body | For |
|---|---|---|---|
| **compact** | `--spacing-2` | about 37px | The transcript. Thousands of rows, read as a stream (F1.2). |
| **default** | `--spacing-3` | about 45px | Export destinations, consent rows, the canvas list view. The `.jv-rows` default. |
| **item** | `--spacing-5` | about 69px and up | The review queue. A row here is a block of content with its own actions, not a line. |

**The law: one table, one density, and it never mixes.** A table with a
37px row above a 45px row has no rhythm, and the eye reads the change as a
grouping that is not there.

Height and density are not the same thing, and the law is about density. A
table whose prose column wraps has rows of different heights, and that is
correct: the rows still share one padding. What is forbidden is a table that
pads one row with `--spacing-2` and the next with `--spacing-4`.

**The header row is 32px**, `padding-block --spacing-2`, independent of the
body's density. It is the same height in all three, because it is a label
strip and not a row of content.

## 3. Sortable headers

### The header cell is a button

```
<th scope="col" aria-sort="ascending">
  <button type="button">Confidence</button>
</th>
```

- `aria-sort` goes on the cell, never on the button. It describes the column,
  and there is one per table: the two columns that are not sorted carry no
  `aria-sort` attribute at all, not `aria-sort="none"` on every one of them.
- The button fills the cell, so the whole header is the target. A word with a
  click handler beside dead space is a control people miss.
- A header that does not sort is not a button. A button that does nothing
  teaches people that headers do nothing.

### The cycle

**Ascending, then descending, then ascending again.** There is no unsorted
state to return to, because a table without a sort is a table in whatever
order the server happened to answer in, and that is not a state worth a
click. Every table declares a default sort, and the default is a real column
sort that the user can reach by clicking back to it.

**A column switch resets to the new column's declared first direction**, never
to the direction the previous column was in. Carrying a direction across
columns produces a sort nobody asked for and cannot explain.

First directions:

| Column kind | First direction | Why |
|---|---|---|
| Text | ascending | A to Z is what a text sort means to everyone. |
| Time | ascending | Oldest first. A queue is worked from the front. |
| Confidence | **ascending** | Least confident first. The reason to sort a review queue by confidence is to find what most needs a human, and that is the bottom of the range, not the top. This is a deliberate exception to the usual "numbers start descending" habit and it is the only numeric column in the product. |

### The indicator

The sorted column's header is a label in `--color-ink` with a 16px inline
chevron in `currentColor`, `stroke-width: 1.5` (`forbidden.md` #26), pointing
up for ascending. Unsorted headers are labels in `--color-ink-muted`, with no
chevron and no reserved space for one: with at most five columns the shift of
a single chevron appearing is not worth a permanently empty 16px in every
header.

The indicator is never the accent. Sort is a state, and **action is accent,
state is ink** (`components.md` §7).

### Focus

The global ring from `grid.css`, with one change: `outline-offset: -2px` so
the ring draws inside the header cell. A sticky header sits at the top edge of
`.jv-scroll` and a 2px outset ring is clipped there, which turns a focus
indicator into a thin line and a WCAG 2.4.7 argument.

Hover on a sortable header is `--color-ink-wash` across the whole cell, the
same hover tone used on every quiet control and row.

### Which of Jarvaids's tables sort, and by what

| Table | Sorts | Default | Mechanism |
|---|---|---|---|
| **Transcript** (F1.2) | **No.** | Time, ascending | None. See below. |
| **Review queue** (F3.5) | Time made, confidence, kind | Time made, ascending | Toolbar menu, not a header row |
| **Canvas list view** (`accessibility.md`) | Creation order, state, kind | Creation order, ascending | Header row |
| **Searchable archive** (F5.4) | Session date, name | Session date, descending | Header row |
| **Export destinations** (F5.1, F5.2, F5.3) | **No.** Four fixed rows. | Fixed | None |
| **Consent record** (F6.1) | **No.** | Order people joined | None |

**The transcript does not sort, and this is a position, not an omission.**
Time order is not one view of a transcript, it is what a transcript is. A
transcript sorted by speaker is a list of quotations with the conversation
removed, and every citation timestamp in the product (F6.3) points into an
order that would no longer be on screen. The transcript filters and it
searches. It does not sort.

**Two sort mechanisms, one rule for picking.** A table with a header row sorts
by header button. A row list with no header row, which the review queue is,
sorts by a single menu in its toolbar showing the current sort as its label
("Oldest first"). Inventing a header row for the review queue purely to hang
a sort on it would put five column labels above a screen that has two columns
of content.

## 4. Numeric columns

Applies to timestamps, durations, counts, confidence percentages and item IDs:
everything Rule T2 lets into a row as a figure (body at weight 500, tabular).

```
font-family              --font-signal
font-size                --text-signal
font-variant-numeric     tabular-nums
text-align               right
white-space              nowrap
```

- **The header of a numeric column is right-aligned too.** A left-aligned
  label sitting over right-aligned digits reads as a label for a different
  column.
- **A numeric column never truncates.** It is a fixed track wide enough for
  its widest legal value. A truncated number is a wrong number.
- Left-align a machine field only when it is the row's first column and acts
  as the row's handle, which is what the transcript timestamp does.

**`tabular-nums` aligns digits inside a cell and does nothing to the column
edge.** It makes every digit the same advance width, so `14:22:06` and
`14:23:10` occupy the same space and the colons line up. It does not position
the cell. The column edge comes from `text-align: right` plus the cell's
`padding-inline-end`, and two numeric columns only line up with each other if
they carry the same padding. Setting `tabular-nums` and then leaving a cell
left-aligned inside a wide track gets you evenly spaced digits in a ragged
column, which looks like a bug in the font.

## 5. Sticky header

```
position    sticky
top         0
z-index     10
background  --color-canvas, the ground itself, so no tonal step is added
border-bottom  --line-hairline solid --color-hairline-strong
```

- **It sticks inside `.jv-scroll`, not to the page.** z-index 10 is the value
  `patterns.md` already reserves for sticky headers.
- **The background must be opaque.** A transparent sticky header has rows
  sliding through its letters. It is the ground's own colour, not a tonal
  fill, so the line below it is the header's one instrument and the "never a
  fill and a line" rule holds.
- **The bottom border is `--color-hairline-strong`, not `--color-hairline`.**
  Everywhere else a row separator is the pale hairline, but this line is the
  only thing separating a stationary header from moving content, and
  `--color-hairline` at 1.20:1 disappears against rows in motion. This is the
  "a boundary that must be seen" case the strong token exists for.

### Why a page-sticky header fails here

`position: sticky` resolves against the nearest scrolling ancestor, and inside
`.jv-scroll` that ancestor is the box, not the page. Three consequences:

1. A header told to stick to the page (`top: 48px`, to clear the session bar)
   never moves at all, because the page is not what is scrolling. It sits
   still while rows scroll under it inside the box, and then leaves the screen
   entirely the moment the page itself scrolls.
2. It would have to know the session bar's height to avoid colliding with it.
   The session bar is z-index 30 and permanently at the top (F1.1), so a table
   header that reached the viewport would slide under it. Hard-coding 48 into
   a table couples the table to the chrome, and the chrome changes.
3. `forbidden.md` #24 allows one scroller per screen. If a table scrolls, the
   table **is** that scroller, so there is nothing else for its header to
   stick to.

**One element, both overflows.** When a table scrolls vertically and
horizontally, `.jv-scroll` and `.jv-overflow-x` go on the same element. Put
`overflow-x` on an ancestor and it becomes a scroll container of its own, and
the sticky header silently stops sticking. This costs an hour every time it
happens.

## 6. Row selection

Selection exists in exactly one place: the review queue. Nothing else in
Jarvaids selects rows, and adding selection to a table is a spec change, not a
feature.

### The mechanism

A leading 40px column holding one native checkbox per row, specified in
`controls.md` §1. Not a click on the row.

**A click on the row does not select it**, because a review row's own controls
are Accept, Edit and Reject (F3.5). A row that also selects on click means a
misjudged click on the row's padding changes what a later bulk action will
act on, silently. Selection is the one thing in this table that must be
deliberate.

`Shift` and a click on a second checkbox extends the selection from the last
one clicked, because the real case is twelve bad reads from one glare-ruined
wall photograph (F1.5, F1.6) sitting next to each other. `Shift` and `Space`
does the same from the keyboard.

### Telling a selected row from a hovered one

Hover and selected use two different tones, and selected carries a second
signal:

```
hovered    --color-ink-wash                                     (1 signal)
selected   --color-accent-wash                                  (tone)
           + its checkbox is checked                            (2 signals)
```

- **No left border.** The previous version of this rule added a 2px accent
  border to a selected row. That is a fill and a line on one element, which the
  design refuses (`forbidden.md` #12), so the second signal is the checked box
  and the tone difference between ink wash and accent wash.
- Hovering a selected row changes nothing: it keeps the accent wash, so hover
  can never erase the distinction.
- On touch there is no hover at all (`interaction.md`), so the accent wash and
  the checkbox carry it alone, and both are still present.
- The checkbox is the accessible state. **Do not also put `aria-selected` on
  the row.** Two attributes claiming one state will disagree, and the screen
  reader will read the one that is wrong.

### The count

In the toolbar, replacing the waiting count while a selection exists:

```
[3] selected of [12]        numbers --text-signal, words --text-meta
[Clear selection]           quiet button
```

`aria-live="polite"` on the count only, so it announces "3 selected of 12" and
not the row that changed. A live region that reads a row on every click makes
the table unusable with a screen reader.

### Select-all

A checkbox in the header of the selection column, with a real label reading
"Select all on this page" (visually hidden, see `controls.md` §9).

- It selects **every row the current filter is showing on the current page,
  and nothing else.**
- It is indeterminate when some but not all of those rows are selected. See
  `controls.md` §1.
- **When the list is paginated, select-all never crosses the page boundary.**
  After a page select-all, a second line appears under the toolbar:

  ```
  All 25 on this page are selected.   [Select all 63 matching this filter]
  ```

  A real button, one explicit click, and the count is in the label. The reason
  is the whole safety argument for bulk actions in this product: a bulk action
  is defensible because the reviewer saw what they acted on. A select-all that
  silently reaches 38 rows on pages the reviewer never opened destroys that
  argument in one click.

## 7. Bulk actions, and the contradiction in `patterns.md` §3

`patterns.md` §3 says: bulk accept-all is deliberately not in the system, and
bulk reject is allowed "because rejecting in bulk risks nothing". Until this
file there was no way to select rows, so bulk reject was a permission with no
mechanism.

**Position: bulk reject stays, this file supplies the mechanism, and the
claim that it risks nothing is narrowed until it is actually true.**

The claim as written is wrong. Rejection is not a discard, it is recorded:
`interaction.md` says rejections are kept in the session record, and F6.5
makes correction capture the evaluation data the whole product is measured
against. A reviewer who sweeps thirty unseen items into Reject writes thirty
"the model was wrong" signals that really mean "a human was in a hurry", and
that poisons the only dataset that says whether Jarvaids works. The risk is not
to the canvas. It is to the record.

So bulk reject ships with four constraints, and each one closes part of that
hole:

1. **Only explicitly selected rows.** A filter is not a selection. You cannot
   reject "everything matching this filter"; you can select the rows a filter
   is showing and reject those.
2. **Select-all never crosses a page boundary silently.** §6.
3. **More than one item opens the confirmation** (`components.md` §14),
   stating the count and the consequence in one sentence: "Reject 12 items.
   They leave the canvas and stay in the session record as rejections." This
   does not contradict `interaction.md`'s rule against confirming cheap
   actions: §14 already lists "rejecting a whole cluster" as a confirmation
   case, and twelve rejections at once is not a cheap action, it is twelve
   actions.
4. **A bulk rejection is recorded as a bulk rejection**, one record per item,
   each marked as part of one sweep. This is the constraint that makes "risks
   nothing" true rather than asserted: the evaluation set can then separate
   twelve considered judgements from one sweep, and F6.5 keeps its meaning.

Undo (F3.7) covers the whole sweep as one step, not twelve.

### There is still no bulk accept

The selection column makes bulk accept trivial to build. It is still not in
the system, and now the asymmetry needs stating plainly: **accept is a claim
about truth and reject is a claim about not being good enough.** Accepting
thirty items you have not read puts thirty unverified statements on the board
as the team's work, which is `forbidden.md` #16 with extra steps.

Two consequences that follow from having selection at all:

- The selection toolbar offers exactly one action, Reject. There is no second
  button, greyed or otherwise.
- `interaction.md` gives `A` to accept and `E` to edit. **With more than one
  row selected, `A` and `E` do nothing**, and the toolbar hint reads "Accept
  one at a time." Otherwise selection quietly turns a single-item shortcut
  into the accept-all this system refuses to build.

## 8. Pagination, load-more, virtualisation

Three mechanisms, chosen per table by how many rows there are and what the
reader is doing with them.

### Review queue: pagination, 25 per page

Tens of items, and the reader is working through them (F3.5).

- A queue is work with an end. A page is a finishable unit, and "page 1 of 3"
  is a progress measure in a screen whose whole point is getting to zero.
- Select-all needs a bounded set to mean anything (§6).
- Scroll position and keyboard order (`J` and `K`) stay stable. An infinite
  list moves under a keyboard user whenever more rows land.
- The pager is `<nav aria-label="Review queue pages">` with Previous, the page
  numbers, and Next. Previous on page 1 is disabled with the reason stated,
  per `components.md` §4, not hidden.

**With exactly one page, the pager does not render at all.** The count line
remains and is the only thing: "12 waiting". A pager reading "1 of 1" is
chrome doing no work, and it teaches people to ignore the place where the real
pager will later appear. This also replaces the static "Showing 4 of 12" line
in `exemplars/review-queue.html`, which stated a truncation it gave no way to
undo.

### Transcript: load-more, upward, in blocks of 200

Thousands of rows, live and still growing (F1.2).

- The scroller renders the most recent 200 lines. Older lines arrive through
  an explicit button at the top of the scroller: "Load 200 earlier lines".
- **Not infinite scroll.** It breaks find-in-page, it removes any sense of how
  far back you are, and in a live meeting it fights the reader for the scroll
  position every time a new line lands.
- **Following the live edge is conditional.** The scroller follows the newest
  line only while it is already at the bottom. Once the reader scrolls up,
  following stops and a control appears pinned to the bottom edge of the
  scroller: a hairline row reading "3 new lines", which scrolls to the bottom
  and resumes following. That is not a toast (`forbidden.md` #19): it is
  inside the list it refers to, and it is a control, not a notification.
- Not pagination: a transcript has no natural page, and a citation (F6.3) has
  to be able to land on line 1,340 and show the lines around it, which a page
  boundary would cut in half.

### Virtualisation: above 2,000 rendered rows, and not before

412 lines at compact density is roughly 16,000px of DOM, which browsers handle
without help. Virtualisation costs something real: **it removes find-in-page**,
because rows that are not in the DOM cannot be found, and the transcript is
the one screen where people use it constantly.

- Below 2,000 rendered rows: do not virtualise.
- Above it: virtualise, and only if both of these ship with it: the "Load
  earlier lines" control stays, and a full-text search over the whole session
  (F5.4) is present in the toolbar, because it is now the only way to find a
  line.
- A virtualised or paginated table carries `aria-rowcount` on the table and
  `aria-rowindex` on every row. Without them a screen reader announces "row 3
  of 25" in a session with 412 lines, which is a lie the DOM is telling.

## 9. Empty, loading and error

All three render **inside the table body**, in one cell spanning every column,
with the header row left in place. Removing the header when the body is empty
makes a filtered table look like a broken page, and the header is what tells
the reader which columns they just searched.

### Empty

One sentence, meta, muted, naming the next action (`components.md` §15).
There are two empties and **they never share a sentence**:

| Case | Sentence |
|---|---|
| Nothing has arrived yet | "Nothing waiting. Everything on the canvas has been accepted." (`patterns.md` §3: an empty queue is a good state.) |
| A filter matched nothing | "No items match Minutes. [Show all 12]" The filter is named and clearing it is one click. |

Telling someone their queue is clear when they have in fact filtered
everything out is a small lie with a large cost in a meeting.

### Loading

Skeleton rows in `--color-surface-sunken`, at the table's own density, on the
table's own column template, first load only (`components.md` §16). Five rows,
or the page size, whichever is smaller.

The header row is real, not a skeleton: the columns are known before the data
is. Never a spinner (`forbidden.md` #21). Never on a filter change or a sort:
a table that flickers to skeleton on every sort feels broken.

### Error

- **If the table has never had rows**: one row spanning all columns, with a
  `failed` glyph, the word, one sentence saying what still works, and a Retry
  secondary button. "Could not load the review queue. Capture is still
  running." The second clause is the one the room cares about (F6.4).
- **If the table already had rows on screen, they stay.** The error is a
  hairline banner above the table (`components.md` §13). Throwing away visible
  data to show an error loses the reader's place and tells them less than
  leaving it up would have.

Never a modal, never a full-screen block, never a toast.

## 10. Overflow

- A table wider than its container scrolls inside `.jv-overflow-x`, and the
  page body never scrolls sideways.
- **The horizontal scroller is focusable**: `tabindex="0"`, `role="region"`
  and an `aria-label` naming the table. A scroll container with no focusable
  child cannot be scrolled from a keyboard, which is a WCAG 2.1.1 failure and
  is easy to miss because a mouse hides it.
- **No frozen first column.** Freezing a column needs a second stacking
  context and an edge that reads as an edge, and the edge everyone uses is a
  shadow. This system allows shadows only on surfaces that float above the
  page (`forbidden.md` #9), and a frozen column is part of the page. A frozen
  column separated by a hairline reads as two tables that failed to align.

### What a phone does with a five-column row

It does not scroll sideways. Below the table's declared collapse width the row
stops being a grid and becomes a block:

```
[the identifying column]        body at weight 500, the row's heading
[the prose column]              full width, wrapping, never truncated
[label] [value]                 the remaining columns, one pair per line,
                                a label, then body or a figure
[actions]                       full width, permanently visible
```

- **The column headers move into the rows as labels.** This is the one place a
  header text repeats per row, and it supersedes `typography.md` Rule T2's
  "never repeated per row" for the collapsed layout only.
- When they do, **the header row is removed from the accessibility tree too**,
  with `hidden`, not merely hidden visually. Left in place it announces every
  column name twice.
- Actions are permanently visible, because touch has no hover
  (`interaction.md`).
- Collapse is a **container query** against the `page` container that
  `grid.css` already names, not a media query. It responds to the width the
  table actually has, which is `--layout-rail` (384) in the side panel and the full
  page on the queue screen, so one table does not need two breakpoints to
  behave in two places. This is why it does not breach `forbidden.md` #23:
  there is still exactly one media breakpoint in the system, 1024px.

## 11. The two exemplar grids, promoted

Both of these currently live in a `<style>` block inside an exemplar. They are
the system's two column contracts. Once the block below is in `grid.css`, both
screen-local blocks are deleted and the exemplars use the classes.

```css
/* PROPOSAL: jv-cols-line and jv-cols-review: not yet in grid.css.
   Promoted from the screen-local <style> blocks in
   exemplars/session-transcript.html and exemplars/review-queue.html. */

/* A transcript line: a fixed machine handle and the words (F1.2, F6.3).
   84px is a tabular "14:22:06" at --text-signal plus its gap. The track is
   fixed, not auto, so the timestamps do not shift column as you scroll. */
.jv-cols-line {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: var(--spacing-3);
  align-items: baseline;
  min-width: 0;
}
@container page (min-width: 560px) {
  .jv-cols-line { grid-template-columns: 84px minmax(0, 1fr); }
}

/* A review row: evidence first, conclusion second. That ordering is the
   screen (patterns.md §3). 220px is the 4:3 photograph crop. */
.jv-cols-review {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: var(--spacing-4);
  min-width: 0;
}
@container page (min-width: 720px) {
  .jv-cols-review { grid-template-columns: 220px minmax(0, 1fr); }
}

/* Selection on (tables.md §6) adds a leading 40px track and nothing else.
   The checkbox column is never added below the collapse width: a stacked row
   puts its checkbox in the row's first line, beside the row's heading. */
/* Applied alongside .jv-cols-review, not instead of it. */
@container page (min-width: 720px) {
  .jv-cols-review-select { grid-template-columns: 40px 220px minmax(0, 1fr); }
}

/* The evidence column is separated by a hairline, never by a grey panel
   (forbidden.md #10): a bottom line when stacked, a right line when beside. */
.jv-cols-review > :first-child {
  padding-bottom: var(--spacing-3);
  border-bottom: var(--line-hairline) solid var(--color-hairline);
  min-width: 0;
}
@container page (min-width: 720px) {
  .jv-cols-review > :first-child {
    padding-bottom: 0;
    border-bottom: 0;
    padding-right: var(--spacing-4);
    border-right: var(--line-hairline) solid var(--color-hairline);
  }
}
```

The 560 and 720 are the widths the exemplars already use, carried over rather
than re-derived: 560 is where an 84px handle plus a readable line stops
fitting, and 720 is where a 220px crop plus a readable conclusion stops
fitting. Both are layout dimensions, exempt under `forbidden.md`'s
"Literals" section.

`exemplars/review-queue.html` also sets `padding-block:20px` inline on each
review row. The item density is `--spacing-5` (24px), and 20 is a literal that
happens to be on the 4px rhythm rather than a token. It goes with the block.

`exemplars/session-transcript.html` also sets `max-height:600px` inline on its
scroller. That belongs with the table, not in the markup: a table's scroller
height is declared alongside its column contract, and 600 is the value to
promote.

## 12. Accessibility summary

Everything a table needs, in one place.

| Thing | Markup |
|---|---|
| The table | `<table>`. If the rows are laid out with `display: grid`, the implicit table roles are dropped by the browser, so restore them: `role="table"`, `role="row"`, `role="columnheader"`, `role="cell"`. A grid layout is not a reason to give up table semantics. |
| Column header | `<th scope="col">`, a label, sentence case in the source and on screen. Nothing is uppercased. |
| Sortable header | `aria-sort` on the `<th>`, a real `<button>` inside it, and no `aria-sort` at all on the columns that are not sorted. |
| Row count when the DOM is short | `aria-rowcount` on the table, `aria-rowindex` on each row. |
| Selection checkbox | A native checkbox with a real `<label>`, visually hidden in the cell. The checkbox is the state; no `aria-selected` on the row. |
| Selection count | `aria-live="polite"` on the count element only. |
| Horizontal scroller | `tabindex="0"`, `role="region"`, `aria-label`. |
| Empty, loading, error | Inside the body, spanning all columns, header kept. |
| Status in a cell | A shaped glyph and a word, always both (`components.md` §2). There is no status column that is a coloured square. |
| Collapsed layout | Header row `hidden`, labels repeated per row. |

## 13. What this file changes

- **`patterns.md` §3** says bulk reject "risks nothing". That is narrowed here:
  it risks the correction record (F6.5), and it is allowed under the four
  constraints in §7. The sentence in `patterns.md` should be re-worded to
  point at this file. Bulk accept-all remains out of the system.
- **`typography.md` Rule T2** says column headers are "never repeated per
  row". Superseded below a table's collapse width, where the header text
  becomes the per row label and the header row is removed entirely.
- **`components.md` §9**: hover is `--color-ink-wash` and selected is
  `--color-accent-wash` with a checked box. The earlier rule here, a mandatory
  2px accent left border on a selected row, is withdrawn, because a tint and a
  line on one element is what the new design refuses.
- **`exemplars/session-transcript.html`** and **`exemplars/review-queue.html`**
  each carry a screen-local grid and a screen-local media query at 559px and
  720px. Both are superseded by §11, and both `<style>` blocks go once the
  proposal lands in `grid.css`. The inline `max-height:600px` goes with them.
- **`exemplars/review-queue.html`** ends with "Showing 4 of 12", which is
  superseded by the pager in §8. With 12 items and a page size of 25 the
  correct rendering is no pager at all and the line "12 waiting".
- **`accessibility.md`'s known gaps** should gain one: no sortable header in
  this system has been run through a screen reader, so whether `aria-sort`
  changes are announced at the moment of the sort is specified but unverified.
- **`grid.css`** needs the block in §11, plus `.jv-visually-hidden` from
  `controls.md` §9. Neither is in the system yet and both are marked PROPOSAL.
