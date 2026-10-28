# Spec: the canvas object model

Sub-project 1 of the creative canvas (Pieter, 18 October 2026). The plan has
four parts, all chosen for the hand-in: **making things by hand**, **the canvas
feel**, **working together live** and **AI that draws**. Every one of them
needs objects other than text notes, so the data model comes first. This spec
is the contract the server and the client are built against.

Approach A, agreed: Jarvaids grows its own canvas engine rather than embedding
a whiteboard library, so that provenance, review and "where did this come
from" stay native to every object, which is what FigJam and Miro do not have.

## The rule, agreed

| Who made it | What happens |
|---|---|
| **A model** | Always a proposal: dashed accent line, "Proposed", reviewed by a facilitator. Unchanged. |
| **A person, by hand** (shape, text, arrow, section, pen stroke, tone) | Arranging, like moving a note: on the canvas at once, no review. |
| **A person, a typed sticky note** | Still reviewed, so the record says who accepted it. A facilitator may add and accept in one step. |

## Objects

Everything on the canvas is a record. Notes stay what they are (content items
and content proposals, unchanged). Five new kinds join them, stored as records
of kind `item` (made by hand, or accepted) or `proposal` (made by a model):

| `item_kind` / `canvas_kind` | `data` fields (besides the common ones below) | Limits |
|---|---|---|
| `shape` | `shape`: `rect`, `ellipse`, `diamond`, `line`; `tone`; optional `text` (at most 280 characters) | |
| `text` | `text` (1 to 1000 characters); `size`: `body`, `title`, `heading` | |
| `arrow` | `from` and `to`, each either `{"id": record id}` (an item or proposal on the canvas) or `{"x": n, "y": n}`; optional `label` (at most 80 characters); `tone` | an arrow cannot point from a record to itself |
| `section` | `title` (at most 80 characters); `form`: `free`, `cluster`, `timeline`, `matrix`, `flow`; `member_ids`: ordered list of record ids | at most 60 members; a member is a note, shape, text or stroke, never a section |
| `stroke` | `points`: list of `[x, y]` relative to the stroke's position; `weight`: `fine`, `regular`, `bold`; `tone` | 2 to 256 points, each coordinate finite and within ±10000 of the position |

`tone` is a closed set: `ink`, `accent`, `category-1`, `category-2`,
`category-3`. The three categories are the design system's labelled
categories, never status colours.

Common fields on every new object's `data`: `origin` (`human` or `model`),
`author_id`, `created_at`, `status` (`accepted` or `undone` for items;
`needs_review`, `accepted`, `rejected`, `stale` for proposals, as today), and for
items made by hand `made_by_hand: true` and `accepted_by` equal to the maker.

**A section is not a cluster.** A cluster (today's group) is a claim about
meaning, made by a person or a model and reviewed. A section is an area a person
draws to arrange things. Clusters stay exactly as they are; the client draws
both the same way, and the organise step can later propose sections.

## Geometry

Positions gain a size. `positions` gets two nullable columns, `w` and `h`
(schema version 6, with a migration that leaves every existing row's size
null). A size is required for `shape`, `text` and `section`, optional for
`arrow` and `stroke` (ignored by the client for those) and refused for notes and
clusters (`invalid_size`), whose width follows their text. Bounds: 8 to 4000
each. Snapshots and deltas carry `w` and `h` on the position.

## Commands

| Command | Payload | Who | Review |
|---|---|---|---|
| `canvas.create` | `{kind, data, x, y, w?, h?}` | participant or facilitator; session not closed | none: becomes an accepted item, `origin: human`, `made_by_hand: true`, position `hand_placed` |
| `canvas.update` | `{item_id, expected_revision, data}` | participant or facilitator | none; a new revision; only the kind's own fields may change; only for the five new kinds |
| `canvas.remove` | `{item_id, expected_revision}` | participant or facilitator | none; status `undone`; `item.undo` restores it as today |
| `item.place` | each placement may add `w` and `h` | as today | as today |
| `proposal.create` | `proposal_kind: "canvas"`, `canvas_kind`, `canvas_data`, optional `positions` | as today | as today: accepting creates the item |

Rules carried over unchanged: `expected_revision` and `expected_position_revision`
concurrency with 409 `stale_revision` and `stale_position`; a machine placement
never moves a hand-placed record; `MAX_RECORDS` (1000) counts the new objects;
every write is an event, so other screens see it within one poll.

Not gated on an active session: like moves, arranging must work while capture
is paused. Refused once the session is closed (`session_closed`).

## What the client does in this sub-project

Read and draw, plus the one-step add for facilitators. **No drawing tools yet**:
those are sub-project 2 (making things by hand).

- Draws all five kinds from the snapshot: shapes, text and sections as positioned
  elements; arrows and strokes on one SVG layer under the notes. Arrows follow
  the current displayed position of the objects they connect; an arrow whose
  record is gone is not drawn.
- Accepted or hand-made: the design system's accepted look (tonal fill, no line;
  for lines and strokes, ink or the tone). Proposed (`proposal`, `canvas`
  kind): no fill, dashed accent line, "Proposed" on hover or beside the object.
- Sections draw as a tonal area with the title above; their members draw inside.
- The list view gets a line per new object ("Shape · Ideas", "Arrow · from A to B").
- A facilitator's composer gets **Add and accept**: `source.text`, then
  `proposal.review` accept, shown as one step.

## Testing

- Server: one named test per rule above (each limit, each refusal, the review
  rule, concurrency, closed session, size refused for notes, migration of a
  version 5 database), added to the mutation harness so each guard is
  load-bearing; schema registry entry for version 6; `API.md` updated.
- Client: unit tests over pure functions (geometry of arrows between boxes,
  list labels) with fixture snapshots; the browser journey extended to create
  each kind through the API and check it is drawn, and a canvas proposal
  is drawn proposed.

## Not in this sub-project

Drawing tools, selection handles and resizing (sub-project 2); a dotted
infinite canvas, tool dock, minimap and snapping (sub-project 2); cursors,
presence, reactions and votes (sub-project 3); the model proposing sections,
arrows and layouts (sub-project 4, with the organise step).
