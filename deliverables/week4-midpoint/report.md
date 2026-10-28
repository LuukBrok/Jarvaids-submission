# Jarvaids: midpoint report

**Group 3, GenAI course, 16 September 2026.**

> **On this document's shape.** The course's own structure requirements for the
> midpoint hand-in were not available in this repository, so the sections below
> follow the project's reasoning rather than a rubric. Re-order them to match
> the brief before handing in. Every number here was measured and the command
> that produced it is named, so anything can be re-run and disagreed with.

---

## 1. What we set out to build

Jarvaids: a tool that sits in a live design meeting, takes the minutes, and
organises the meeting visually onto a shared canvas from voice and photographs.

The single rule the whole product turns on:

> **Anything a model made is provisional until a human accepts it, and it is
> never rendered as if a human made it.**

Almost every design and engineering decision in this repository follows from
that sentence, and the ones that do not are written down as decisions with
their costs in `decisions/decision-log.md`.

The functionality is numbered F1.1 to F6.6 in
`deliverables/documentation/flowchart.md`. Thirty-seven numbers, every one of
them cited somewhere else in the repository, and none invented: checked
mechanically across markdown, CSS, Python and JavaScript.

## 2. What actually exists

| Part | Size | State |
|---|---|---|
| Backend | 2429 lines | 247 tests, all passing |
| Client application | 819 lines | Works end to end in a browser |
| Client library | 423 lines | Transport and sync, separately tested |
| Design system | 857 lines of CSS, 5597 of spec | Tokens, grid, five exemplar screens |
| Documentation | 3 interactive documents | Flowchart, pipelines, process network |
| Continuous integration | 8 jobs | Green on every pull request |

A person can now start a session, agree to the recording policy, start capture,
type notes or photograph a sticky-note wall, review what came back, correct it,
accept it, drag it around a shared canvas, export it and delete it. That is the
whole spine, and it is driven end to end in a real browser by
`app/client/tests/journey.mjs`.

### How it is verified

The repository does not treat a passing test suite as evidence that a guard
works, because it once measured that it is not. Ten guards were deleted from
the backend one at a time and all forty-five tests stayed green, including the
credential check on a deletion receipt.

So every guard now carries a **mutant**: a named change that deletes it, and
the named test that must fail when it does. 147 of them across six harnesses.
An error does not count as a kill, only a named assertion failing does, because
a mutant that makes the suite crash has not shown that a guard matters.

That habit has repeatedly caught tests that could not fail, including several of
our own. Two worth reporting because they are instructive rather than
embarrassing:

- A test lowered a limit on the object under test, which shadowed the constant
  the mutant edited, so it passed whether the limit was 1000 or a billion.
- A board fixture placed every machine item before every human one, so
  "hand-placed" correlated perfectly with time and the key could be deleted with
  the test still green.

## 3. What we measured

**Synchronisation cost.** Accepting one proposal, with seven clients connected,
measured over real HTTP by `app/server/tests/measure_sync.py`:

| Board | Records | Per client, compressed |
|---|---|---|
| Small | 41 | about 1650 B |
| At the record ceiling | 965, 321 of them positioned | about 1660 B |

The point is the second row: the cost of one acceptance does not grow with the
size of the board. An earlier version sent the whole board's ordering on every
update and cost 8183 B per client on a populated board, which we found only
after building a fixture that placed its notes. The fixture that would have
shown it existed and was behind a flag.

**Deletion.** After a session is deleted, its text appears **zero** times in the
raw bytes of the database file. Reading rows back proves the rows are gone; it
does not prove the words are. `secure_delete` overwrites the freed pages, and
that is now asserted against the file rather than assumed.

**Resources.** Four simultaneous 4.6 MB photograph uploads peak at 85 MB
resident. Sixteen connection slots, released after a ten second idle timeout,
so a room that fills them recovers without a restart.

All of these come from one container: a four-core Xeon, 16 GiB, Linux 6.18.
`app/server/tests/measure_operations.py` prints the machine alongside every
number for that reason. None of it is evidence about a team laptop, a phone or
a projector.

## 4. What we have not established, and will not claim

This is the section that matters most, and it is deliberately blunt.

- **No handwriting recognition has ever run in this project.** The only
  extraction adapter is a synthetic fixture whose output literally reads
  "FIXTURE ONLY". Every accuracy property of the real system is unknown.
- **No user evaluation has been run.** `evaluation/` now holds the protocol,
  the generated test fixtures and the baseline recording sheet, with every
  result field empty and marked not yet collected. Nothing in this repository
  supports a claim that Jarvaids saves anyone time or effort.
- **No evidence from real hardware.** No phone has joined a session, no
  projector has displayed a board, and several design decisions cite
  legibility at four metres as their reason.
- **The speech path is a mechanism, not a capability.** See section 5.

We would rather hand in a project that says this clearly than one that implies
otherwise.

## 5. The decision we had to make about scope

The flowchart lists **F1.2 speech to text** as in scope and calls it "the
riskiest assumption in the whole tool", alongside F2.1 rolling minutes and F6.2
local processing. For most of the build, the backend accepted exactly two kinds
of input: typed text and photographs. The documentation promised something the
artefact could not do.

Three options were on the table: narrow the product to what it is, build the
audio path, or mark speech explicitly as future work. Doing none of them was
what was happening, and it was the only indefensible choice, because it left
the gap invisible.

The decision taken, and what it cost, is recorded in
`decisions/decision-log.md`. Whatever it says there is the authority; this
report should not be read as a second version of it.

## 6. How the work was organised

Two AI agents worked in parallel on the backend for most of this period, split
by table rather than by topic, because almost every feature touches one service
file and a split by topic would have put both in the same functions.

It went wrong in an instructive way. Both branches added a database migration,
both numbered it version 2, and both were green on their own: the collision only
existed in the union, and a database written by one side would have been read as
the other's shape. Nothing caught it because nothing ran the two together.

Three things came out of that:

1. Continuous integration, so every pull request runs what the brief already
   asked every contributor to run.
2. A schema version registry, so claiming a number twice produces a merge
   conflict on one line instead of silence. It does not prevent the mistake; it
   relocates it to somewhere a person will see it.
3. Branch protection requiring branches to be current before merging, because
   both collisions so far existed only in the union.

`decisions/ai-use-log.md` records what each agent did and, more importantly,
what review actually happened. Several rows say "verified by automated checks,
not reviewed line by line", because that is the truth.

## 7. Where the project stands

`decisions/gaps.md` is the honest list, checked against the code rather than
recalled. The short version at midpoint:

**Closed:** the client application, the schema collision, synchronisation cost
on a populated board, malformed input handling, the evaluation apparatus, the
duplicated board ordering rule, operational evidence on this container.

**Open, and each with a stated direction:** a real extraction provider, user
evaluation data, evidence from real hardware, and the remaining canvas forms.

## 8. What we would do next, in order

1. **Collect one real data point.** One photographed wall, transcribed by hand
   as the baseline, run through the tool, correction effort counted. One
   afternoon, and it produces a real number, possibly a bad one, which is worth
   more to this project than another hundred tests.
2. **Put one real provider behind the extraction boundary.** The mechanism
   around it is thoroughly tested; the provider is a stub.
3. **Take it into a room**, on a phone and a projector, and find out which of
   our distance and legibility decisions survive contact.

---

*Numbers in this report were produced by `measure_sync.py`,
`measure_operations.py`, the six mutation harnesses and the test suite. Re-run
them before quoting any of them: they are facts about a commit and a machine,
not properties of the idea.*
