# Expandable sticky notes (F3.8)

Status: approved product direction, 22 September 2026. Implementation and user
validation are future work. This document defines the planned behaviour; it does
not claim that the current prototype, API, client or exemplar screens implement it.
It refines F3.1 to F3.7 without changing their identifiers or the capture-first
milestone in pipeline decision D01.

## One main point, with supporting detail

The session overview consists of sticky notes representing main points from a
meeting, brainstorm or other working session. A note may originate in speech,
a photograph or typed input. Sticky notes are the presentation of content items;
group labels, axes, photographs and connectors remain their own canvas elements.

Collapsed is the default. Show one concise main point in full, its kind, source
handle and essential status. Never hide Proposed, source-changed or unreadable
status behind expansion. A summary is a separate representation of the content,
not its first few lines silently cut off. An AI-written summary remains
provisional even when the underlying material was written by a person.

The explicit Show details control unfolds the same note. Keep the main point
visible above supporting explanation, reasoning, qualifications and source
references. Include only relevant captured session material or team-written
context; do not fill missing background with invented or external knowledge.
Hide details collapses it again. If there is no additional detail or evidence,
show No further detail instead of an empty expander. If a source is unavailable,
retain a labelled unavailable reference; do not substitute a fabricated citation.

The sticky-note metaphor uses the canvas item's own three forms (a tonal fill
when accepted, a dashed accent line when proposed, a solid line when a person's
note is not yet reviewed) and the existing typography. It introduces no
shadows, because shadows belong only to surfaces that float above the page and
a note is part of the page. These are content objects, not decorative cards
around unrelated interface controls.

## Topic and choice colours, planned (23 September 2026)

**Open for the team: this section conflicts with the current design.** It was
written before Jarvaids adopted one hue per screen in tonal steps
(`principles.md` #1, `forbidden.md` #15). A set of topic fills puts several
hues on every canvas, and a topic fill would also collide with the accepted
note's tonal fill, which is how acceptance is now drawn. The team has not
decided which gives way. Until it does, the holding position is:

- **Topic is shown by the group's label and its outline**, not by the note: an
  accepted group is a `--color-surface-sunken` panel, a proposed group is a
  dashed accent outline, and the group label names the topic on the canvas and
  in the list view. Notes take no topic fill.
- **Paper colour is a swatch.** A photographed note's original colour is shown
  as a small swatch on the note, beside its source handle, never as its fill.
- **No categorical note palette is added** to `tokens.css` while the question is
  open.

The text below is the planned behaviour as approved on 23 September 2026, kept
so the decision can be argued from it. Where it says "fill", read it as the
proposal being weighed, not as current design.

When Jarvaids structures the discussion, each main topic, subject or choice under
comparison can receive its own sticky-note background colour. Notes belonging to
the same group share that colour. Colour supports the structure; it does not
replace spatial grouping, ordering or meaningful connections.

Assign colours from a dedicated categorical note palette, not the action accent
or status-colour tokens. A fill means belongs to this topic or choice, never
accepted, important, correct or preferred. AI assigns the initial group and
colour provisionally; the team can rename, regroup and change colours. Keep each
group's colour stable for the session and across connected screens, expansion,
collapse and exports. Do not reshuffle colours when a new group arrives. A human
colour override persists until the team changes it.

Show a short group label on each note and a labelled colour key for the overview,
so colour is never the only way to identify a group. Give unassigned notes a
neutral surface labelled Ungrouped. If a note concerns several topics, use one
explicit primary group for its fill and label or link its other relationships;
do not blend colours into an unexplained new category. If there are more groups
than distinguishable tested colours, retain existing assignments and use neutral
fills with distinct labels for additional groups instead of recycling a colour
as though the groups were the same.

Review status remains independent: dashed boundary plus the Proposed label for
unaccepted AI content or grouping; accepted content keeps its own status when
its grouping is provisional. Show grouping status beside the group label or hull.
Changing a colour or opening a note never accepts content or a relationship.
Keep status labels on a tested neutral backing, and verify boundary contrast
against both the note fill and surrounding canvas. Topic-coloured notes may be
provisional or accepted, with the same group colour in either state.

The original colour of a photographed physical note stays source metadata. It
can inform a provisional grouping, but must not silently become its topic colour
or override the team's chosen mapping. Source crops retain their original pixels.

This was written as a deliberate exception to the earlier white-only
content-item rule. Under the current design, tonal group panels exist in one
hue (`--color-surface-sunken`), so the exception now being asked for is a
second hue, not a tint. Future
implementation must add semantic note-fill tokens and measure text, focus,
boundary and status contrast on every fill in each supported scheme. Keep full
reading contrast, test colour-vision differences and projector washout, and retain
labels in greyscale or monochrome export. Exact hues are a future palette design
and validation task; the current token file and contrast results contain no such
palette and do not certify it.

## Organisation and human control

AI organises incoming notes into a fitting structure: proximity for related
ideas, order for a sequence, axes for an explicit comparison, and labelled
connections for supported relationships. A plain ordered set or the captured
physical arrangement is the fallback when evidence does not justify more.
Never manufacture chronology, priority, consensus or causality merely to fill a
layout. Preserve minority positions and disagreements in the main point or its
visible status when their omission would change its meaning.

This organisation can appear automatically as a provisional arrangement while
the session develops. It is not permission for continuous whole-board reshuffling.
Preserve accepted structure and team-adjusted positions and relationships. Place
new notes around that work; offer conflicting regroupings for explicit review.
The team can move, edit, regroup and correct connections. Accepting an arrangement
does not accept its notes, and expanding or moving a note accepts neither.
The model proposes meaning; deterministic layout code computes geometry.

## Expansion without changing the saved arrangement

Expansion is local to the viewing screen, so a participant opening detail on a
phone does not expand the shared display. Keep the expanded note's saved anchor
fixed. Grow downward at its existing width, with wrapped, fully accessible text.
Make temporary room using local display offsets for neighbours, including
team-positioned notes, while preserving order, membership and connector endpoints.
These offsets are not saved moves, do not invoke item.place, and never change
content or position revisions. They are the narrow, user-triggered exception to
the rule against moving other items on screen.

Several notes may be open. Recompute spacing from current saved geometry and the
set of open notes, so repeated toggling cannot accumulate drift. Collapse removes
only the space needed for that note. Once all notes close, the view matches the
latest saved layout, including edits received while detail was open, rather than
restoring an obsolete snapshot. Redraw links and hulls against displayed bounds.
A drag after closing detail changes saved layout through the existing move path;
while expanded, close detail before dragging so display offsets cannot be saved.

Do not solve collisions by covering other notes, clipping text, hiding statuses
or shrinking type. Extend the pannable surface; keep the focused control visible.
Where fixed axes would make displacement misleading, reserve a detail lane at the
note's anchor and keep its axis marker fixed, with a visible connector to the
unfolded detail. The parallel list supplies the same content and relationships
for small screens and non-spatial reading. Expansion never calls a model.

## Review and access

Collapsed notes offer Review rather than a direct Accept action. Review opens the
full proposed main point, all supporting detail, changes and relevant evidence.
The review surface keeps this content expanded while Accept is available; opening
it is not acceptance or proof that a person has read it. Existing role, source
revision and conflict checks still apply. Review arrangement separately from
content. A long note may have a collapsed overview while its complete proposal
is inspected in the review queue; the old 24-line exclusion is superseded.

Use a real button labelled Show details or Hide details with aria-expanded and
aria-controls. Enter and Space toggle it. Keep focus on the control; when another
action collapses content containing focus, return focus to that control first.
Collapsed content is outside the tab order and accessibility tree. Reading order
stays main point, detail, sources and actions, with textual group and relationship
labels in the parallel list. Announce state changes without reading the entire
note on each toggle. Touch targets are at least 44px and need no hover. Expansion
remains available on the read-only phone canvas because it edits no shared data.
Use the existing expansion timing and disable movement under reduced motion.

## Future data and export requirements

Reuse item identity, provenance, source revisions, review history, saved positions,
groups and links. Future implementation also needs a shared mapping from stable
group identity to topic colour, plus team overrides; this is distinct from local
disclosure state and original photographed colour. It must represent the concise main point
separately from supporting detail, with enough source attribution to review both.
Changing either is a content change; disclosure state and temporary spacing are
view state. Existing records without a separate summary continue to display their
full text until an explicit summary proposal is available, avoiding silent data
loss or an unlabelled AI rewrite. Current wire formats and schemas are unchanged.

An overview export uses collapsed notes and explicitly says that detail is omitted.
A complete export includes supporting detail and source references independently
of which notes happen to be open. Neither export promotes provisional content or
bypasses existing source permissions, deletion rules or review inclusion choices.
Source references still depend on source availability; this adds no promise to
bundle evidence. These export behaviours require future implementation.

## Acceptance scenarios for the future implementation

- Topic and choice groups retain their identity across new arrivals, team
  overrides, expansion, reconnect and export; changing a group never changes
  review state. (Under the holding position above, identity is the group label
  and panel; if the team adopts topic fills, the fill must persist the same way.)
- Group labels and the key distinguish colours in greyscale and colour-vision
  tests. Neutral overflow, Ungrouped and multi-topic notes remain understandable.
- A reader identifies the main points from collapsed notes and locates the
  corresponding reasoning and source after expansion, without a changed meaning.
- Long and dense notes, multiple open notes and a note beside fixed axes remain
  readable without overlap, broken connections or altered semantic placement.
- Repeated expand/collapse, concurrent saved edits and reconnect do not change
  stored content, position revisions, review state or another screen's disclosure.
- New notes respect team adjustments. Unsupported or disputed relationships remain
  explicit; an uncertain layout can fall back without losing items.
- Collapsed provisional summaries cannot directly accept hidden detail. Review
  exposes the whole proposal, including qualifications and source changes.
- Keyboard, touch, reduced motion and the parallel list provide the same access.
  No-detail notes and unavailable sources give an honest, useful result.
- Overview and complete exports state what they contain and preserve provenance.

Evaluate scan accuracy, detail retrieval and relationship interpretation against
the existing full-text canvas using the same session material. Also record missed
qualifications, incorrect acceptances and unwanted movement. No numeric success
claim or user-study result is asserted by this documentation update.

The cost is extra summary review, disclosure accessibility, local collision
handling and export design. These are future delivery tasks, not evidence that
automatic form selection or expandable notes already work.
