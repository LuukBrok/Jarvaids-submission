---
id: 001
title: Jarvaids, design meeting assistant
status: exploring
date: 2026-09-09
owner: TODO
---

## One sentence

A meeting-time assistant that keeps a live, searchable record of a design
session and writes back into the board the team is already using, so that what
was said, sketched and stuck on the wall ends up in one place while the session
is still running.

## Who it is for, and when

Design teams in a working session: a workshop, a sprint review, a concept
critique. Two to eight people, a wall or a whiteboard, one or two hours,
usually with sticky notes and always with more said than written down.

The moment it targets is not the meeting as a whole. It is three specific
seconds:

1. "What did Sanne say about that twenty minutes ago?" and nobody can find it.
2. The wall is full of sticky notes and someone has to photograph and retype
   them afterwards, which either takes an hour or does not happen.
3. The meeting ends and the board is a graveyard: the artefacts survive, the
   reasoning does not.

## Concept expansion, 22 September 2026

The live overview is a board of expandable sticky notes. Each collapsed note
shows one main point; opening it reveals the supporting explanation, reasoning
and session sources. AI groups, orders and connects notes in a structure fitting
the discussion, while the team can adjust it and retain control. Notes unfold
in place, with temporary local spacing that preserves the saved arrangement.
AI content and relationships remain provisional until reviewed.

This extends the product vision beyond photographed notes to main points from
any captured session material. It does not replace the capture-first milestone
or claim a working interface. The original exploration and scope trade-offs
below remain the historical starting point. Planned behaviour and evaluation:
[expandable sticky notes](../../app/design-system/spec/expandable-notes.md).

### Topic and choice colours, 23 September 2026

Each main topic, subject or choice can have a distinct sticky-note colour. Notes in the same group share it, with visible group labels and an overview key. AI assignments are provisional and team-adjustable; colours stay consistent as notes expand or new content arrives. Topic fills never replace provenance boundaries or review labels.

This extends the planned overview; the categorical palette and interface remain
future work. Source-note colours remain evidence, separate from topic colours.

## What it does

**Live transcription.** Runs speech recognition on the room audio for the
duration of the session. The transcript is working material, not a deliverable.

**Pull, do not push.** The assistant does not speak unless asked. A team member
asks it something out loud or by typing, and it answers from the meeting so far:
"what did we decide about onboarding", "who objected to the paywall and why",
"summarise the last ten minutes". Answers cite the moment they came from, so
they can be checked rather than trusted.

**Sticky note capture.** Photograph a wall or a cluster of sticky notes with a
phone. The assistant extracts each note as a separate item, reads the
handwriting, groups them by physical proximity and colour, and places them on
the shared board (Miro or FigJam) as a matching cluster. The photograph stays
attached so a bad read can be corrected against the original.

**Write back, provisionally.** Anything the assistant adds to the board is
visually marked as machine-generated until a human accepts it. Nothing it
produces is indistinguishable from what the team made.

## Why AI, and why this shape of AI

Remove the model and three things break: the transcript does not exist,
handwriting on a photograph stays a photograph, and asking a question in
natural language becomes searching a text file.

The shape matters more than the presence. This is deliberately not a chat
window next to a meeting. Two constraints define it:

- **The board is the only context.** The model reads the transcript and the
  board, and writes only to the board. It has no general knowledge task and no
  open-ended conversation. That is what makes it a designed tool rather than a
  chat interface with a meeting-shaped prompt.
- **It answers, it does not volunteer.** No unprompted suggestions during the
  session. See the risk below.

## Scope, honestly

As written this is three products: speech recognition, physical-to-digital
capture, and grounded retrieval. That is too much for the time available.

Proposed cut, to be decided in week 1:

- **Core:** sticky note capture and board write-back. Most visible, most
  testable, most obviously not a chat wrapper.
- **Supporting:** transcription plus retrieval. Transcription is plumbing, not
  a feature. It exists to make retrieval possible.
- **Cut or demote:** live idea generation. See below.

## The idea generation problem

Live idea generation is the weakest part of the concept and the most tempting
one. It is close to a generic chat interface, and worse, it risks anchoring the
group: an AI suggestion put on the board mid-divergence narrows the space
instead of widening it, and it carries an authority a colleague's half-formed
idea does not.

Two defensible options:

1. Drop it. The tool captures and retrieves. It does not ideate.
2. Keep it and make the fixation risk the thing being tested. Run sessions with
   and without it and look at the spread of ideas produced, not at whether
   participants liked it. A finding that the tool narrowed the group's thinking
   would be a better result than "the tool helped".

Option 2 is more interesting and more work. Decide before building.

## Riskiest assumption

**Handwriting on sticky notes, photographed under real room lighting, at an
angle, in mixed handwriting and mixed languages, can be read well enough to be
useful.**

If extraction is unreliable, correcting the output costs more than retyping and
the concept changes shape entirely.

Test in week 1, before building anything: photograph a real wall from a real
session, run it through two or three vision models, and count. Metric agreed in
advance, for example 80 percent of notes correctly transcribed and correctly
separated. Ten photographs is enough to know.

Second assumption, cheaper to test: that anyone will actually ask the assistant
something mid-meeting. Facilitators are busy. Watch one session and count how
often someone would have wanted it.

## Consent and privacy

This concept records people, which the course explicitly restricts.

- Transcription runs locally (Whisper or equivalent). Audio does not go to a
  third-party API.
- Raw audio is deleted after the session. Transcripts are anonymised before
  leaving `evidence/raw/`.
- Everyone in the room agrees before recording starts, out loud, on the record,
  and can ask for it to stop at any point.
- Agreement with the teaching team before the first recorded session, not after.

This is a hard gate. If it is not settled, the concept cannot be tested with
real teams and falls back to synthetic material, which weakens the evidence.

## What would make us drop this

- Sticky note extraction below the agreed accuracy on the week 1 test, with no
  clear path to fixing it.
- No team willing to be recorded, and no acceptable synthetic substitute.
- Board integration (Miro or FigJam API) turns out to cost more implementation
  time than the whole concept is worth. Check the API before committing.

## Open questions

- Miro or FigJam? Decide on API access and cost, not preference.
- Who talks to it during a session: anyone, or only the facilitator? Anyone is
  chaos, only the facilitator is a bottleneck.
- Does the assistant have a voice, or only text? Voice output in a meeting
  interrupts. Probably text on a shared screen.
- What happens after the meeting? Out of scope for now, but the team will ask.
