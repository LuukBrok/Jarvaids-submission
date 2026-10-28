# Annotations: the FrameIt material

> **AI draft, pending group edit.** Every annotation in this file was drafted by
> an AI agent and no member of the group has yet read it. The group keeps,
> rewrites or deletes each one and then changes this line to **Group comment**.

## The source

Three files, all read in full from the `main` branch with `git show`, never
copied into this branch, because the Week 3 folder is raw material and a
decision about it is still open with the coordinator.

- **`FrameIt interview 1.md`.** Eight questions put to the group by the FrameIt
  interview tool with the group's answers, timestamped Wednesday 11:32 to 11:42.
  Made by a tool and a person together: the questions are the tool's, the
  answers are the group's, and the last answer is missing.
- **`FrameIt conversation (redacted).md`.** The visible messages of the same
  conversation, twenty one messages plus a stop summary. It is an **edited
  copy**: its own header says local paths were redacted and em dash punctuation
  was normalised to hyphens, and that tool activity and internal messages are
  not included. The original remains in the application and is not in the
  repository.
- **`FrameIt conversation and tool summary.md`.** Two AI-written sections: a
  prose synthesis of the MapIt interviews, and a description of FrameIt as a
  product. Neither section is the group speaking.

Nobody is named in this file; the parties are "the group" and "the tool".

**What this source is good for.** It is the closest thing in the Week 3 material
to a statement of our own concept, so it carries most weight on what Jarvaids
should do, and almost none as evidence about users.

## Annotations

### F1. The group's own one-line concept

> "a live structed summary" (Message 9, typo in the original)

**Labels:** useful / keep
**Why:** It is the group stating the concept in its own words and unprompted,
which makes it a better source for slide 1 of the proposal than anything written
about the group afterwards.

### F2. Correction is by dragging, during the meeting

> "Drag it themselves, like adjust it" (interview 1, question 5)

**Labels:** useful / keep
**Why:** The group answered a question about wrong clusters with a direct
manipulation, during the meeting rather than after it, which is precisely the
correction path the client already implements.

### F3. The tool proposes, the group disposes

> "Create them, but people can adjust them" (interview 1, question 6)

**Labels:** useful / keep
**Why:** Asked whether the tool or the group should make the first clusters, the
group chose the tool with a correction right attached, which is the product's
central rule arrived at independently and is worth quoting on the value slide.

### F4. Wrong clustering is the failure mode named first

> "If it is unrelated to the meeting" (interview 1, question 4)

**Labels:** useful / keep
**Why:** When asked what would make a generated note unhelpful the group named
mis-clustering and off-topic content, not misread words, which suggests the
grouping is judged more harshly than the transcription and should therefore be
the more conservative of the two.

### F5. The provisional distinction is wanted but unspecified

> "that should be something visual, maybe, lettertype" (Message 13)

**Labels:** unclear / question
**Why:** The group is certain the distinction between what was said and what the
model proposed must be visible and entirely undecided about how, so this is an
open design question rather than a finding, and the hedging in the passage is
part of what it says.

### F6. Suggestions: automatic or on request, unresolved

> "they can choose between 2 modes" (Message 15)

**Labels:** unclear / question
**Why:** Offering the user a mode switch defers the decision rather than making
it, and the group's own summary agrees it is unsettled, so the proposal should
present it as an open question with a test attached, not as a feature.

### F7. The basis for "you missed something" is not grounded

> "all the knowledge of the internet" (Message 17)

**Labels:** unconvincing / question
**Why:** Asked what the tool should use to decide that a subject has been missed,
the group answered with general knowledge plus project context and the interview
stopped before the follow-up about which wins in a conflict, so the suggestion
feature currently has no stated basis that could be built or tested.

### F8. The interview stopped one question short

> "No response recorded." (interview 1, question 8)

**Labels:** unclear / keep
**Why:** The unanswered question is how an agreed task differs from one that was
only mentioned, which is the same acceptance boundary the product rests on, so
the gap is worth keeping visible rather than filling in from our own opinion.

### F9. The tool summary is firmer than the conversation was

> "colour-coded theme clusters" (tool summary, section "Our tool: FrameIt")

**Labels:** unconvincing / question
**Why:** The summary describes headings, bullets and colour-coded clusters as
settled product behaviour, while the conversation it summarises reached only
"explored and narrowed, but not finalized", so the firmer document is the weaker
source and should not be cited as if the group had decided these things.

### F10. The record is an edited copy, not an export

> "A transcript file could not be exported" (Message 21)

**Labels:** useful / keep
**Why:** The mechanical export failed for want of a Python runtime, so what the
repository holds is a hand-redacted copy of the conversation and the original
sits in the application, which is a limitation the submission should state
rather than a detail to leave out.

### F11. The concept came from the group's notes, not from the tool

> "i dont know, come up with something" (Message 4)

**Labels:** surprising / keep
**Why:** The group opened by asking the tool to invent the concept and the tool
refused, after which the group attached its own brainstorm notes, so the concept
in this conversation is the flip chart sharpened by questioning rather than
anything the tool originated.
