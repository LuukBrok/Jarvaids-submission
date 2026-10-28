# Annotations: the MapIt interviews, read through the group report

> **AI draft, pending group edit.** Every annotation in this file was drafted by
> an AI agent and no member of the group has yet read it. The group keeps,
> rewrites or deletes each one and then changes this line to **Group comment**.
> Anything still marked as a draft at submission is submitted as a draft, which
> is honest; presenting a draft as the group's view would not be.

## The source

- **What it is.** `report-a92c7d1d.md`, the MapIt group report: pains, gains,
  possible AI assistance, other observations and open questions, synthesised
  from three interview recordings and one photograph of the flip chart.
- **Who made it.** A tool, not a person. The report labels itself
  "AI interpretation for discussion" on its second line, and it is an
  interpretation of material the group gathered.
- **When.** Generated 2026-09-16T08:27:46Z, revision `026ab4b3ab63df303aa7028a`.
- **How it was read.** In full, from the `main` branch with
  `git show "origin/main:week 3 materials/report-a92c7d1d.md"`. The file was
  read, not copied into this branch, because raw Week 3 material carrying
  identifiers must not enter the public repository.
- **What was not read, and what that costs.** The three interview transcripts
  and the three recordings were not opened: they carry identifiers and a
  permission check refuses them. **So this is an annotation of the report about
  the interviews, not of the interviews.** Every statement below is a statement
  about what the report says. Where the report generalises, nobody here can
  check it against what was actually said. `GAPS.md` records this.
- **Naming.** No interviewee, participant or member of course staff is named
  anywhere in this file.

## Annotations

### A1. Jumping to the first idea is the pain the tool should address

> "move too quickly to a first-seeming solution" (heading: Pains)

**Labels:** useful / keep
**Why:** This is the one pain in the report that a during-meeting record can act
on directly, because a visible overview of what has already been said is what
makes a premature commitment noticeable while it can still be reopened.

### A2. Generic feedback is worthless, specific feedback is wanted

> "Generic feedback from AI ... is often too vague" (heading: Pains)

**Labels:** useful / keep
**Why:** It sets a design constraint rather than a feature request: a suggestion
that does not point at a specific element of the record will be ignored, so the
suggestion path must be anchored to a note or a passage or not exist at all.

### A3. Simulated users diverged sharply from real ones

> "can diverge sharply from the real responses" (heading: Pains)

**Labels:** surprising / keep
**Why:** The report states the divergence as a finding rather than as a risk,
which is stronger than expected and is the clearest available argument that the
tool must never let a generated item stand in for something a person said.

### A4. Trust breaks on provenance, not on accuracy

> "produces uncertainty if challenged on their provenance" (heading: Pains)

**Labels:** surprising / keep
**Why:** The stated failure is social rather than technical, the designer cannot
defend the number to somebody else, which argues that every generated item needs
a traceable source attached and not merely a confidence score.

### A5. Designers want to verify AI themes themselves

> "want to review, verify, and interpret these results themselves"
> (heading: Possible AI assistance)

**Labels:** useful / keep
**Why:** This is the closest thing in the material to independent support for the
product's central rule, that anything a model made stays provisional until a
person accepts it, and it arrived from interviews rather than from our own
reasoning.

### A6. Checklists are wanted and doubted in the same report

> "Reminder systems or checklists" (heading: Gains)

**Labels:** unclear / question
**Why:** The gain is listed, and then "Other observations" says the reluctance to
run a skipped method "may persist even when support is available", so the report
records a want and its own rebuttal without resolving which is the finding.

### A7. Sketching as a deliberate AI-free zone

> "inappropriate to delegate to AI" (heading: Other observations)

**Labels:** useful / question
**Why:** It is a genuine boundary and the group's own summary already warns that
it came from one person, so it should be carried into the proposal as a
consideration about where the tool stops, not as a rule presented as consensus.

### A8. The report has no counts and no attribution

> "Some designers move too quickly" (heading: Pains)

**Labels:** unconvincing / question
**Why:** Nearly every statement uses an unquantified subject such as "some",
"designers" or "participants", so nothing in the report says how many people held
a view or whether one interviewee produced a whole section, which is exactly the
flattening the group's own summary complains about.

### A9. The flip chart is folded into the interview findings

> "Flip-chart reflection:" (headings: Pains, Gains, Other observations)

**Labels:** unclear / question
**Why:** The group's own reflection sheet is mixed into the same lists as the
interview material under a prefix rather than a separate section, so a reader of
the report cannot tell the group's prior beliefs from what interviewees said,
and a reader of only the deck certainly cannot.

### A10. The open questions are research questions, not design questions

> "Can AI effectively foster more reflective choice-making" (heading: Open questions)

**Labels:** unclear / reject
**Why:** Reject for this deliverable rather than as a bad question: it cannot be
settled by anything the group can build or test before the midpoint, and citing
it in the proposal would spend a line of a seven-minute talk on a question with
no next step attached.
