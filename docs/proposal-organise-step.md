# Proposal: the organise step, from session to structured canvas

For the Tuesday 20 October checkpoint. Written by Pieter (WP4) with Claude
Code, 18 October 2026. **A proposal to agree on, not a decision:** links 1 and
2 belong to Rosalique (WP1) and Julie (WP2), and nothing below is built.

## Why this comes before the UX pass

Each input works on its own. Nothing yet turns them into an organised canvas,
which is the product:

| Piece | State on 18 October |
|---|---|
| Photo to notes | Live: marked regions read by Claude, reviewed by a person (PR #38) |
| Speech to transcript | Live: `transcript_segment` records with speaker labels |
| Voice commands | Recognised, not executed (WP3) |
| Batch synthesis | Works, one real run: photos and a transcript file to points, groups and a form. Writes a file; reaches no session |
| Placement | Accepted notes land under "Not placed yet"; a person drags each one |

The UX should be designed around capture, organise, review. The organise step
does not exist yet to design around.

**Handoff example:** `evidence/synthetic/demo-synthesis-2026-10-18.md` is the
synthesis run for real on three wall photographs and a fictional transcript:
20 points with their sources in six groups. It is the shape links 2 and 3
start from.

## Link 1: the session as the synthesis input (WP1, Rosalique)

Today `synthesis.py` reads a Whisper JSON file and re-reads whole photographs
itself. Proposal: read both from the session instead.

- **Speech:** the session's `transcript_segment` records, `final` only, in
  order. Each has `text`, `speaker_name` (or the per-connection label),
  `captured_at_ms` and `duration_ms`, which give the start and end the
  synthesis already expects.
- **Photos:** the notes the live reader already made, content proposals and
  items carrying a `region_id`, instead of phase 1a reading the photo again.
  One reader, and a person may already have corrected its output. The demo run
  shows why: the whole-photo read misread "get" as "set", where the region
  reader had it right.
- **First, smallest step:** an export of a session's segments as Whisper-style
  JSON. The existing CLI then runs on a real meeting with no other change, and
  WP1 gets real transcripts to evaluate on.

## Link 2: synthesis output onto the canvas (WP2, Julie)

The server already has the pieces; each synthesis result maps onto a command
that goes through review:

| Synthesis result | Becomes | Note |
|---|---|---|
| A point | `proposal.create`, `content`, its text, refs to the sources it came from | The proposal shows `photo`, `speech` or `photo+speech` support and any `conflict` |
| A group of accepted points | `proposal.create`, `relationship`, `form: "cluster"` | Only once its members are accepted; the server refuses relationships on proposals |
| Another form (timeline, flow, matrix, hierarchy) | Not yet: the server implements only `cluster` | Show the form and reason as text until then |

**Decision needed: speech cannot be cited yet.** A proposal may reference
only `source` and `item` records (`service.py`, `_refs`), and transcript
segments are their own kind. A point that came from speech would arrive with
no evidence, against F6.3. Options: allow `transcript_segment` as a reference
kind (a small service change, and the cleanest), or keep the quote in the
proposal text. Recommended: the first.

**Where it runs.** The demo run took 52 seconds; an extraction job has 60. A
`synthesis.queue` job like `extraction.queue` fits, with its own longer
deadline and the same isolated process. Triggered by an "Organise" action, and
by the Summarize and Visualize voice commands once WP3 executes them.

## Link 3: placement (WP2, Julie)

Synthesis gives meaning, never positions, by design. The client's layout
engine (`spec/canvas-layout.md`) turns groups and form into positions and
sends them as a `placement` proposal with `origin: machine`. The server
already refuses a machine placement onto anything a person placed by hand.

## To agree on Tuesday

1. Link 1's first step, the Whisper-style export, and who builds it.
2. Transcript segments as a reference kind: yes or no.
3. Synthesis as a session job with a longer deadline, and its trigger.
4. Batch, once after the meeting, stays (decision log, 13 October); re-running
   against accepted items is later work.
5. Who builds links 2 and 3, and what the demo shows if they are not ready:
   the handoff example as a static overview is the fallback.
