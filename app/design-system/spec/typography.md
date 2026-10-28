# Typography

One face. Six roles. Three weights. Everything on a screen belongs to exactly
one role, and if you cannot say which, you have picked the wrong style.

## The face

**Archivo**, a grotesque, SIL Open Font License, vendored in `../fonts/` as
one variable file. Nothing else loads. There is no second face, no icon font,
no monospace.

`--font-signal` and `--font-reading` both resolve to Archivo. The two tokens
stay so that a component still says which job its text does, and so that the
day a reading face is argued for again, it is one line and not a search
through every component.

Hierarchy comes from **size, weight and ink**, never from a second face. That
is the change from the previous system, which paired Archivo with a rounded
humanist face and asked the pairing to make machine output and human output
look different. It was the wrong instrument for that job: the provisional
distinction is carried by the dashed line, the glyph and the word, which
survive a projector and colour blindness, and a change of face survives
neither at a glance. One face also removes a whole class of defect, the
cross-face baseline and x-height matching that the old Rule T1 existed to
manage. Cost: a short label and a sentence now differ only by size, weight and
ink, so a screen that leans on faces for structure has to lean on space
instead.

## The six roles

| Role | Token | Size / line | Weight | Only for |
|---|---|---|---|---|
| **Display** | `--text-display` | 44/48, tracked -0.01em | 400 | The page `h1`, once. |
| **Heading** | `--text-heading` | 28/32 | 500 | A section's or a screen's own heading. |
| **Title** | `--text-signal-lg` | 18/24 | 500 | Panel titles, the session name, the dialog title. |
| **Body** | `--text-body` | 14/20 | 400 | Everything else. When in doubt, this one. |
| as a **figure** | `--text-signal` | 14/20, tabular | 500 | A time, a count, a confidence figure on a body line. |
| **Label** | `--text-signal-sm` | 12/16, sentence case | 500 | Labels that *name* content: field labels, column headers, definition-list keys, the kind line on a canvas item, a status word. |
| **Meta** | `--text-meta` | 12/16 | 400 | Second lines under content: counts, hints, empty states, incidental times. |
| as a **caption** | `--text-caption` | 12/16, italic, muted | 400 | Photograph captions and quoted provenance. |

The figure is body at weight 500 with tabular numerals, not a seventh role:
it sits on a body line at the body's size and is told apart by weight. The
caption is meta in italic and muted, for the same reason. A screen that seems
to need a seventh role is not short of a type size, it is short of a
structure.

**Older spec files cite four numbered roles.** Read them as: ① signal is
display, heading or title for a heading and a figure for a number; ② structure
is label, in sentence case now; ③ reading is body; ④ meta is meta or caption.
The new roles are named, not numbered, so the two schemes cannot be confused.

**Headings are two lines**: the heading in ink, and an optional muted second
line under it in the same role at weight 400, saying what the section is for.
Two strengths of one ink, not a second size.

## Weights

- **400**: reading. Body, meta, captions, the display title.
- **500**: structure. Headings, titles, labels, figures, button labels.
- **600**: held back. A single figure that must lead a group. Never a whole
  line.

Nothing else is used. Bold (700) is not part of the system: at this scale it
shouts, and the display title is deliberately light, because a large light
title reads as calm and the canvas is what should lead.

## No uppercase labels

Labels are sentence case at 12px weight 500, in ink or `--color-ink-muted`.
The previous system set structure labels in tracked uppercase. That is
removed, because uppercase at 12px is harder to read at distance (word shapes
disappear), spends horizontal room the label does not have, and gets spelled
out letter by letter by some screen readers when the source was typed in
capitals. A label is told from content by size and weight, which the label
role already has.

## In a table row

**Rule T2.** A table row is body text. The only figure inside a row is a
**fixed-width machine field**:

- a timestamp or a duration (`--text-signal`, `font-variant-numeric: tabular-nums`)
- a count, a percentage, a confidence figure
- an item ID

Prose in a row is never set as a figure, no matter how short. A speaker name
is prose. A note's text is prose. "Sanne" is body 400; "14:22:06" is body 500,
tabular.

Column headers are labels, live in the header once, and are never repeated per
row.

The reason for the rule: rows are the densest thing in this product (the
transcript is hundreds of them), and confining the figure weight to the
machine column means the tabular numerals line up, which is the whole point of
setting them that way.

## When a figure and a sentence share a line

They share a size and a **baseline**, never a centre. `.jv-row` does this. A
transcript line is a timestamp (figure) and a sentence (body), both 14px, the
figure at 500 and tabular. With one face there is no metric to reconcile, so
this rule is now only about alignment.

## Timestamps, specifically

Jarvaids has two kinds of timestamp and they are not the same role.

- **A citation handle** (F6.3): the timestamp you click to jump to the moment
  an answer came from. A figure, tabular, and interactive, so it carries the
  accent.
- **An incidental time in prose** ("asked 3 minutes ago"): meta, muted. Not
  clickable, not a figure.

## Room mode

On a projector, `data-room` on the root multiplies every size above by
`--room-scale`, 1.5: body becomes 21/30, label 18/24, display 66/72. The roles
and their order do not change, only the scale. See `touch.md` § 0 and
`space-and-hierarchy.md` § 3 for why the room gets a mode and not a larger
floor.

## Hard rules

- **12px is the floor**, at a desk. Label, meta and caption all sit on it.
  Nothing smaller exists.
- **One `h1` per page**, display. Heading levels descend without skipping.
- **Sentence case everywhere.** No `text-transform: uppercase`, no tracked
  capitals. A `<kbd>` shows the key as it is printed.
- **Numerals in any figure use `font-variant-numeric: tabular-nums`.** A timer
  that jitters as the digits change is a distraction in a room.
- **No arbitrary sizes.** If a size is not one of the eight tokens, it is
  wrong.
