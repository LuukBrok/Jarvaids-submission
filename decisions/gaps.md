# What is missing, 16 September 2026

**Historical snapshot.** For current work, read
[the team plan, 14 October 2026](../docs/team-plan.md) and
[LOCAL-FEATURES.md](../LOCAL-FEATURES.md). The integrated browser client and real
local transcription now exist; older absence claims below describe September.
Current generation, command execution and live photo-reading work are tracked
in the team plan. Keep this analysis as evidence of the earlier state.

A gap analysis of the project as it stands on main plus the branch in flight.
Written because the tracking list in `backend-chunks.md` has 105 open items and
a third of them are done, which makes it useless for deciding what to do next.

Everything below was checked against the code, not recalled. The commands are
named so each claim can be re-run and disagreed with.

---

## What exists, verified

| Thing | Size | State |
|---|---|---|
| Backend | 2429 lines | 242 tests, 102 Python guards, all green |
| Client library | 423 lines | `client.mjs`, `session-sync.mjs`, 45 JavaScript guards |
| Design system | 857 lines CSS, 5597 lines of spec | Tokens and grid built, 19 spec files |
| Exemplar screens | 883 lines, 5 screens | Static HTML, none connected to the server |
| Documentation | flowchart, pipelines, process network | 37 F-numbers, all cited, none invented |
| CI | 7 jobs | Green on main |

The backend is the most thoroughly verified part of this project by a wide
margin, and the ratio says so: 5289 lines of test against 2429 lines of code.
That is not automatically a good sign. It is a good sign only if the thing being
tested is the thing that matters, and gaps G1 and G2 below argue it is half of it.

---

## G1. There is no client application

**What.** `app/client/` contains a `.gitkeep` and nothing else. There is a
server, a client library, and five static exemplar screens. No exemplar makes a
network call: `grep -rl "fetch(" app/design-system/` returns nothing.

**Why it matters.** Nobody can use this. Every claim about review burden,
arrangement effort or time saved is currently untestable, because there is no
path from a person to the backend. It also means the design system's 5597 lines
of spec describe a UI that has never been rendered against real data.

**Direction.** Both ends already exist, which makes this cheaper than it looks.
`session-sync.mjs` already handles the delta protocol, resync and board order.
The five exemplars are already on the design system's tokens. The work is
wiring, not invention: replace the exemplars' hardcoded content with state from
`session-sync.mjs`, in the order session-setup, review-queue, live-canvas.

**Cost.** The largest single remaining piece. It is also the one that unlocks
G4, so it should not be sequenced after it.

---

## G2. There is no speech path, and the documentation says there is

**What.** The server accepts two source types, `text` and `image`. There is no
audio intake, no transcript record, no speaker, no segment. Four mentions of
audio across the whole backend, all in prose.

Meanwhile `flowchart.md` lists **F1.2 Speech to text** as in scope, and calls it
"the riskiest assumption in the whole tool". F2.1 rolling minutes and F6.2 local
processing are also in scope and also absent.

**Why it matters.** This is the largest single honesty problem in the project.
The product is described as a tool that "sits in a live design meeting, takes
the minutes". What is built photographs a wall and helps arrange the results.
That is a good product, and it is not the one the documentation promises.

**Direction.** This is a decision, not a task, and doing neither is the worst of
the three options because it is what is happening now.

1. **Narrow the product.** Mark F1.2, F2.1 and F6.2 out of scope in the
   flowchart with the reason, and describe the tool as what it is: a sticky-note
   wall capture and arrangement assistant. Cheapest, honest, and loses the
   riskiest assumption rather than testing it.
2. **Build the audio path.** New source type, transcript and segment record
   kinds, a speech adapter behind the same provider boundary as the extractor.
   Weeks, not days, and it drags in consent questions that a photograph does not
   raise, because a recording captures people who never opted in.
3. **Declare it explicitly future work** in the flowchart rather than silently
   leaving it in scope.

**Recommendation.** Option 1 or 3 before the hand-in. Option 2 only if the
course timeline genuinely allows it, and its consent implications are worked
through first, not after.

---

## G3. No provider has ever run

**What.** `adapters.py` contains exactly one implementation, `FixtureExtractor`,
whose output is the literal string "FIXTURE ONLY". No OCR has been performed by
this project, ever.

**Why it matters.** Every accuracy, latency and cost property of the real system
is unknown. The mechanism around the provider is well tested: bounded subprocess,
cancellation, restart recovery, adapter-change refusal. The provider itself is a
stub.

**Direction.** `F01`/`F02` in the chunk list already make the right argument:
add confidence and colour to the extraction contract **now**, while the only
implementation is a fixture and the contract is free to change. Doing it later
is a migration. Then one real provider behind the existing boundary, measured
on a held-out wall.

---

## G4. There is no evaluation evidence at all

**What.** These directories are tracked and empty:

- `evaluation/test-cases/`
- `evaluation/baseline/`
- `evidence/synthetic/`

`evaluation/findings.md` is an unfilled template: "State the value claim in one
sentence, in a form that could turn out false."

`evidence/raw/` is also empty, but that one is correct: its contents are
gitignored by design, because consent records and identifiable transcripts do
not enter a public repository.

**Why it matters.** This is the assessed core of the course, and it is the one
part with nothing in it. The project can currently demonstrate that a mechanism
refuses bad input in 147 named ways. It cannot demonstrate that the tool helps
anyone do anything.

**Direction.** The cheapest thing that would change the project's evidential
position more than any further backend work: **one held-out photograph of a real
sticky-note wall, transcribed by hand as the baseline, then processed through
the tool, with the correction effort counted.** That is one afternoon and it
produces a real number, including possibly a bad one, which is worth more than
another hundred tests.

Blocked on G1: without a client there is nothing for a participant to use.

---

## G5. The hand-in folders are empty

`deliverables/week4-midpoint/` and `deliverables/showcase/` contain `.gitkeep`
and nothing else. The documentation deliverables in
`deliverables/documentation/` are real and good. The graded artefacts are not
started.

**Direction.** Timeboxed and the team's call, not an engineering task. Worth
naming here because it is invisible from inside the code.

---

## G6. The tracking list overstates what is open

**Closed 5 October 2026.** Every unticked item was checked against the code,
done items were ticked with the tests that prove them, and the list now opens
with a short current summary. The check found one wrong tick (J02: `1e999`
returned HTTP 500), which is now fixed. The text below is the original finding.

**What.** `backend-chunks.md` reports 105 open items. A sample checked against
the code shows many are done and never ticked:

| Item | Claimed | Actually |
|---|---|---|
| A01 invitations replace facilitator-supplied tokens | open | `invitations` table, `participant.invite` takes an invitation |
| A04 `participant.remove` | open | in `service.handlers` |
| A06 `agreed_at`, `withdrawn_at`, `consent.withdraw` | open | columns exist, command exists |
| A09 LAN bind | open | `advertised_hosts` in `LocalServer` |
| D01 media sanitisation | open | `media.py`, `media` table, crop authority |
| E-series control replay | open | `control_requests`, `control_seq` |

**Why it matters.** A plan that overstates what is left is as useless as one
that understates it. Nobody can decide what to do next from a list where a third
of the open items are finished, so nobody uses it, so it drifts further.

**Direction.** One pass reconciling the expanded A to M contract against the
code, ticking what is done with the evidence. Mechanical, an hour, and it makes
every subsequent planning conversation possible.

---

## G7. One rule, two implementations, nothing binding them

**What.** Board z-order is implemented in `service.py` (`_board_order`) and again
in `session-sync.mjs`, in two languages. They agree today: verified empirically
on a board with three records sharing a timestamp and mixed origins, comparing
the server's `board_order` with the client's sort over the same snapshot.

**Why it matters.** Nothing keeps them agreeing. It is the pattern `AGENTS.md`
opens on: two copies drift within a week and nobody diffs them. When they drift,
two people in the same meeting see a different item on top, which is the kind of
bug that gets blamed on the projector.

**Direction.** A JavaScript test that reads a server-generated fixture and
asserts the same order. Small, and it converts an argument into a check.

---

## G8. No hardware evidence beyond one container

Every operational number was measured on a 4-core Xeon container with 16 GiB
running Linux 6.18 and Python 3.11. `tests/measure_operations.py` prints the
machine with every number and says so in its own output.

Untested anywhere: a real phone joining over a LAN, a projector at 4 metres, a
shared screen, abrupt power loss. Several design decisions cite projector
legibility at 4 metres as their reason and none has been looked at on a
projector.

---

## Suggested order

Sequenced by what unblocks what, not by size.

1. **G6**, reconcile the list. An hour, and everything else plans better after it.
2. **G2**, decide the speech question. A conversation, not code, and it changes
   what the flowchart says the product is.
3. **G1**, one connected screen. Not all five: `review-queue` against a live
   server proves the whole spine works and is the smallest thing that does.
4. **G3**, confidence and colour into the extraction contract, while it is free.
5. **G4**, one held-out wall with a hand-made baseline.
6. **G7**, the ordering fixture test. Cheap, do it whenever.
7. **G5** and **G8**, the team's timeline and the team's hardware.

Nothing in this list is backend correctness work, and that is the point. The
backend is the most finished part of this project. The next useful thing is not
another guard.
