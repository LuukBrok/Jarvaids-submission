# How this repository works: setup, automation, checks, design system, agents and logs

**What this is:** a plain account of how the repository is set up and what
keeps it honest, written from the files. Every section names the file it
describes, so nothing here has to be believed: open the file and disagree.

**Why it exists as one page.** All of this is already true somewhere in the
tree, in ten places. A reader arriving cold cannot find ten places. This page
is an index with reasons attached, and it deliberately does not restate the
contents of the files it points at, because a second copy drifts from the first
within a week and nobody diffs documents.

---

## 1. The shape of the repository

From `AGENTS.md`, "Where things are", plus the folders it does not list.

| Path | What is in it |
|---|---|
| `deliverables/documentation/` | The flowchart, the pipeline map, the stack, and this page. **Read the `.md` versions**: they carry the same content as the `.html` twins at a fraction of the size, which is why the markdown is what agents and reviewers are pointed at |
| `deliverables/week4-midpoint/` | The midpoint hand-in: plan, briefs, slides, demo runbook, annotations of the Week 3 material, and the packaging script |
| `app/design-system/` | Tokens, nineteen spec files, five exemplar screens, and the tooling that verifies them |
| `app/server/` | The backend: Python, SQLite, and the offline Pillow decoder |
| `app/client/` | The first thing in the project a person can use: plain ES modules served by `serve.py` |
| `app/ios/` | A Swift client core. **Never compiled.** See its `VERIFICATION.md` |
| `ideation/` | Concepts and explorations, including the rejected ones, because a project assessed on reasoning needs its discarded branches |
| `decisions/` | The decision log, the AI use log, the gap analysis and the backend task list |
| `evaluation/`, `evidence/` | Test cases, findings, field material. `evidence/raw/` is gitignored |
| `meeting notes/`, `prompts/` | The team's own notes, and the versioned prompt material |
| `.github/`, `.githooks/` | What runs on every pull request, and what runs before a push |

`deliverables/documentation/flowchart.md` is the place to start: it defines the
F1.1 to F6.6 numbering the rest of the repository cites, and
`deliverables/documentation/proposal.md` gives each of those numbers a status.

## 2. Branches and pull requests

**`main` is never committed to directly.** `AGENTS.md`, "Git", says to work on
a feature branch, to ask before pushing, and to merge `main` into the branch
before opening a pull request. That last one is not tidiness: a stale branch
shows other people's files as deletions, and merging a pull request like that
removes their work. `AGENTS.md` records that this has nearly happened twice.

**The protection itself needs a repository administrator and is not on.**
`.github/BRANCH-PROTECTION.md` holds the ruleset to apply by hand, at Settings,
Rules, Rulesets, and says plainly that it cannot be set from a coding session.
Checked against GitHub on 22 September 2026 through the repository's branch
listing, `main` reports `protected: false`, so **nothing is enforcing any of it
today**. The rules are written down with the accident behind each one: block
force pushes, because a force push to `main` loses work silently and this
repository has two people and two agents pushing; require every status check;
and require branches
to be up to date before merging, which is the one that matters most, because
both of the collisions this repository has had were green on their own branch
and only existed in the union. Approvals are deliberately set to zero: a
two-person project cannot supply a reviewer for every change, and a required
approval nobody can give turns into everyone using the administrator override,
which is weaker than no rule (`decisions/decision-log.md`, 2026-09-16).

**One branch per agent or person, and the name says which.** `git branch -r`
shows the convention: `claude/<two-words>-<id>` and `codex/<topic>` for the two
coding agents, `docs/<topic>` for document work, and a few bare topic names
from earlier in the project. Every route into `main` is a pull request.

## 3. What runs on every push and pull request

`.github/workflows/verify.yml`, seven jobs, on every pull request and on every
push to `main`. Its opening comment says why it exists: two branches each added
a schema migration, both numbered it version 2, nothing noticed until after the
merge, and both branches were green on their own.

| Job | What it runs | What it catches, and the accident behind it |
|---|---|---|
| `design-system` | `spec/audit.sh` (13 checks), `contrast-check.py` over every pair in every scheme, and a check that `spec/accessibility.md` contains every generated contrast row | Hand-drift in the design system. The contrast table once carried the heading "do not hand-edit this table" while being maintained by hand, and it had gone stale (`AGENTS.md`, "Things that are easy to get wrong here") |
| `house-style` | A grep for the em dash character across the files this branch changed | New prose breaking house style. Scoped to the diff on purpose: 102 lines predate the rule, and a build that is always red trains everyone to ignore it (`decisions/decision-log.md`, 2026-09-16) |
| `backend` | Python 3.11, 3.12 and 3.13: the full suite, then the five mutation harnesses, then "nothing was left mutated" | A suite that passes on one Python and was never run on another. The last step exists because a killed harness never reaches the code that restores its target, so a leftover mutation would otherwise be silent |
| `sync-budget` | `tests/measure_sync.py` | A delta that grows with the board. It reached 8183 B per client against a 5 KB budget and was invisible because the realistic fixture sat behind a flag; it now runs by default and exits non-zero over budget |
| `schema` | `.github/scripts/check_schema_versions.py` | Two branches claiming one schema version. `SCHEMA_VERSIONS` in `db.py` is the registry, so claiming a number twice is a git conflict on one line instead of a database read as the wrong shape |
| `client` | Node 24: contract and lifecycle tests, the named client guard mutations, the real CLI and two-client HTTP journeys, and a check that nothing in the tree changed | Drift between the two implementations of the board z-order rule, one in `service.py` and one in `session-sync.mjs`. `board-order-unit.mjs` runs the client's ordering over a fixture the Python service generated, and the backend job checks the fixture still matches, so neither copy can drift alone |
| `browser` | Playwright Chromium, `app/client/tests/journey.mjs` | The only job with a person's view of the product in it. The client's first three defects were a favicon 404, a library timer that throws only in a browser, and invisible text on a tab, and none of them was visible to any other check in this file |

## 4. Before the push

Two things, and both are faster than waiting for a red build.

**`.githooks/pre-push`**, enabled per clone with `git config core.hooksPath .githooks`.
It runs the design audit, the contrast check, the schema version check, the
backend suite and the em dash grep. It deliberately leaves out the mutation
harnesses: they take about two minutes, and a hook slow enough to be worth
skipping teaches people to pass `--no-verify`, which costs more than it saves.

**The "Before you finish" block in `AGENTS.md`** is the longer list, including
the six mutation harnesses, the client transport tests, the schema version
check, the sync measurement and `deliverables/documentation/check_proposal.py`,
which binds the function table in `proposal.md` to the F-numbers in
`flowchart.md`. That block also carries the rule that makes it worth running:
record an unavailable check as unverified, never as passing.

One check cannot pass in this development container:
`client_mutation_check.py` needs a Node with `--test-isolation`, CI uses Node
24, and this container has Node 22.22. A green local run is therefore not a
full run, and `AGENTS.md` asks for that to be said rather than reporting five
of six harnesses as everything.

## 5. The mutation discipline

`app/server/tests/mutation_runner.py` is the shared runner behind the five
Python harnesses and the JavaScript catalogue. They were forty identical lines
copied five times, differing in four values.

The discipline it enforces, with the reason for each rule:

- **Every guard names the test that kills it.** A guard is removed in a
  throwaway copy of the tree, and the named test must go red. It is not enough
  for the suite to go red somewhere.
- **An error is not a kill.** A mutant that makes the suite crash or fail to
  import has not shown that a guard matters; only the named assertion failing
  shows that. Write the assertion to fail rather than to raise, and use
  `.get('key')` where a mutant removes a key.
- **The mutation happens in a scratch copy, never the working tree,** so a
  killed process cannot leave your source mutated.

It exists because ten injected mutations to `app/server` left all 45 tests of
the day passing, including the deletion of the deletion-receipt credential
check, and because three of the ten replacement tests passed against mutated
source on the first attempt (`AGENTS.md`). Coverage was rejected as the bar for
the same reason: every one of those ten guards was executed by a passing test
that never checked the outcome (`decisions/decision-log.md`, 2026-09-16).

The counts, as `AGENTS.md` records them: **150 guards, being 66 service, 45
JavaScript, 12 schema, 10 runtime, 9 media and 8 isolation.** Adding a harness
is a mutant list and one call.

## 6. The design system

`app/design-system/`. Tokens in `tokens.css`, which is the single source of
truth, with `spec/tokens.md` explaining what the tokens are for and stating
that when the two disagree the CSS wins and the document is stale.

**Two faces, paired at the same size with weight carrying the difference:**
Archivo for signal, Nunito Sans for reading. White canvas, hairlines instead of
fills, no shadows, no cards, no gradients, one accent, six status colours as a
closed set always shown as a dot plus a word, and neutrals as one ink at six
strengths rather than six greys.

The specs, one line each:

| File | What it settles |
|---|---|
| `principles.md` | What the system is for, and what wins when rules collide |
| `tokens.md` | What each token is for; the CSS wins where they disagree |
| `ink-ladder.md` | One colour at six strengths, not six greys |
| `colour-schemes.md` | The mechanism for varying accent and status, and the four schemes |
| `typography.md` | Two faces, four roles, seven sizes |
| `space-and-hierarchy.md` | Grouping and rank with only space, type role, weight and rule |
| `components.md` | What each component is made of, in tokens |
| `controls.md` | The small interactive parts a form or a toolbar needs |
| `patterns.md` | Five screens, four page shapes; do not invent a fifth |
| `canvas-layout.md` | How the board itself is laid out, and where the layout engine lives |
| `dataviz.md` | A spatial tool, not a charting one, and what that means for charts |
| `tables.md` | Two of the five screens are tables and neither says so |
| `interaction.md` | Rules that follow from running during a live meeting |
| `touch.md` | The signal is `pointer: coarse`, not screen width |
| `accessibility.md` | Target WCAG 2.1 AA, with the generated contrast table and two known unmet Level A criteria |
| `announcements.md` | What the system says out loud, and where it stops |
| `copy.md` | UI language, sentence case, verb-first buttons |
| `checklist.md` | The short list to run before calling a screen finished |
| `forbidden.md` | Thirty hard rules, each with its reason |

**`forbidden.md` is the list that does the work.** Thirty numbered rules, every
one with the reason it exists, because a rule without one gets deleted by the
next person who cannot tell whether it was load-bearing. Rules 16 to 18 are the
product's own rule in visual form: never render model output identically to
team output, never grey out a provisional item, and never tint its background,
because the signal is the stroke.

**The exemplars** are five static screens in `spec/exemplars/`: session setup,
review queue, live canvas, session transcript and export view. They must open
offline by double-click, which is why rule 27 forbids a CDN of any kind in
them.

**The tooling.** `spec/audit.sh` is 13 checks over the application source,
including the design system, the client and the exemplars, and
`spec/contrast-check.py` measures 105 pairs across four schemes and can
regenerate the accessibility table with `--markdown`. Both run in CI and in the
pre-push hook.

**`CLAUDE-fragment.md` is what an agent generating UI reads first.** It is the
distilled rulebook, and `AGENTS.md` makes reading it a precondition for
generating any interface, because the alternative is a screen that has to be
audited back onto the system afterwards.

**The pending revision is a direction of travel, not a state.**
`decisions/design-reference-rondesignlab.md` section 7 consolidates thirty
screenshots into eight rules and twelve concrete changes, ordered tokens first,
then usage rules, then rule changes, each naming the rule in `forbidden.md` it
touches. **None of the twelve has been made.** Two of them would change hard
rules, so they carry their own conditions: the gradient token narrows rule 11
rather than dropping it, and the translucent material for provisional notes is
marked "test, do not adopt", with a contrast check first, because translucency
can read as dimmed on a projector and rule 17 exists for exactly that reason.

## 7. How agents work here

**`AGENTS.md` is the single brief**, for every coding agent and for humans.
`CLAUDE.md` points at it and adds nothing. The reason is written into both
files: two copies of the same conventions drift within a week, and the drift is
invisible because nobody diffs instruction files. This repository has been
bitten by exactly that twice, once with a stylesheet that duplicated token
values and once with a contrast table maintained by hand under a heading saying
not to.

**Work arrives as a brief.** `deliverables/week4-midpoint/PLAN.md` holds the
workstreams and what is deliberately not in the plan;
`deliverables/week4-midpoint/BRIEFS.md` holds one brief per workstream, written
to be handed to an agent as-is. Every brief ends with the checks that will be
run on its result, so a builder knows what "done" is measured against before
starting, rather than after.

**The split is coordinator and builder.** The coordinator writes the plan and
the briefs and checks each piece against them; a builder agent does the work on
its own branch; the group supplies the material and makes every judgement call.
The rule that makes the split safe is in every brief: **a builder commits
nothing and pushes nothing. The coordinator verifies the report and
integrates.** A builder's report is a claim, and the difference between a claim
and a verified result is the whole point of the logs in section 8. The W5 work
package is the standing example of why: the builder built against `main`, where
no client existed, so its runbook narrated a terminal and its screenshots were
design drawings, and the integration step caught it and retook all five from
the running client (`decisions/ai-use-log.md`, 2026-09-22).

**Worktree isolation, and its trap.** Agents run in separate worktrees so two
of them cannot edit one checkout at once. The trap is that a worktree branches
from `main`: it does not contain work that exists only on another agent's
branch, so the second agent's pull request shows the first agent's files as
deletions, and merging it removes their work. `AGENTS.md` names the remedy,
merge `main` into the branch before opening the pull request, and records that
the accident has nearly happened twice. `PLAN.md` also notes that uncommitted
work left in a stopped agent's worktree is safe there and is not lost, which is
worth knowing before anybody tries to recreate it.

## 8. The logs

This project is assessed partly on the traceability of AI involvement, so an
undocumented contribution is worth less than a documented one. Both logs live
in `decisions/`, and the row is written when the work lands, not at the end of
the project.

- **`decisions/ai-use-log.md`.** One row per work package: what the tool did,
  what it touched, and what review actually happened. Three rules decide
  whether it is worth anything: be honest about review, because directing an
  agent and accepting its output is not the same as reading it; log what could
  not be verified in the row itself, which is why the `app/ios` row says in
  bold that the Swift has never been compiled; and one row per work package,
  not per commit, because the commit history already has that detail.
- **`decisions/decision-log.md`.** One row per decision that closed off an
  option: what was chosen, what else was considered, why, and whether it is
  reversible. A decision with no alternative listed is a default, not a
  decision, and gets no row.
- **`decisions/gaps.md`.** The honest list of what this project does not have,
  checked against the code on 16 September, with a direction for each. Two of
  its gaps have moved since and `AGENTS.md` restates them so the two files
  cannot disagree: there is a client now, and the speech path is plumbing with
  a synthetic transcriber rather than transcription.
- **`decisions/backend-chunks.md`.** The backend task list and requirement
  ownership. It currently **overstates what is open**: `gaps.md` G6 sampled it
  against the code and found items marked open that are implemented and never
  ticked, so check a claim against the code before planning from it.

A formatting rule with a real cost behind it: blank lines between rows end a
markdown table, so rows stay contiguous. Both logs were broken this way once
and the last entry in each silently stopped rendering as a row.

## 9. Privacy and secrets

Two rules from the repository README that predate everything else.

- **Secrets live in `.env`, which is gitignored.** `.env.example` lists key
  names only.
- **Raw recordings, transcripts carrying identifiers and consent records stay
  in `evidence/raw/`, which is gitignored.** They do not enter the public
  repository, because the course restricts recording people and because a
  transcript carrying names cannot be un-shared once it is in a git history.

**The recorded exception, which is not the rule.** On 22 September the group
chose to leave the Week 3 recordings, transcripts and a session photograph on
`main` under `week 3 materials/`, because the repository is private to the
group during this phase and the material was needed for the midpoint
deliverable. `AGENTS.md` records it as a known exception and
`decisions/decision-log.md` carries the row, including its cost: it is a
standing breach of the repository's own rule and of the course's consent
restriction if anyone outside the group is on the recordings. The condition for
undoing it is named: before the repository is shared beyond the group, that
material moves to `evidence/raw/` and the history is purged, and nothing new
follows the precedent. Agents do not read, copy or quote those files; they
annotate through the report and the group's summaries, which is what
`deliverables/week4-midpoint/annotations/` does and says in its own header.

## 10. Numbers

Every number here was read from the file named beside it, on 22 September 2026.
Where a command was also run to confirm it, the command and what it printed are
named, because a number without the command that produced it is not a number.

| What | Number | Read from |
|---|---|---|
| Backend tests | 254 | `AGENTS.md`, "Before you finish" block. Confirmed here: `python3 -m unittest discover -s tests` printed "Ran 254 tests in 22.223s, OK" |
| Named guards | 150: 66 service, 45 JavaScript, 12 schema, 10 runtime, 9 media, 8 isolation | `AGENTS.md`, the paragraph on `tests/mutation_runner.py`. The service count confirmed here: `tests/mutation_check.py` printed "All 66 guards are protected". The JavaScript catalogue could not be run in this container (Node 22.22 rejects `--test-isolation`) |
| Design system audit checks | 13 | `AGENTS.md` and `.github/workflows/verify.yml`, "Design system audit, 13 checks". Confirmed here: `audit.sh` printed 13 check lines |
| Contrast pairs | 105, across four schemes | `AGENTS.md`. Confirmed here: `contrast-check.py` printed "105 pairs checked across 4 schemes (ember, harbour, fern, mulberry), 0 failing" |
| Schema versions | 5 | `app/server/genai_server/db.py`, the `SCHEMA_VERSIONS` registry, versions 1 to 5 |
| F-numbers | 37 | `deliverables/documentation/flowchart.md` section 3. Confirmed here: `check_proposal.py` printed "37 F-numbers in flowchart.md, 37 rows in proposal.md, all matched" |
| Commits on this branch, ahead of `main` | 35 | `git rev-list --count origin/main..HEAD` on `claude/pensive-volta-w9c4lt`, before the commit that adds this file |

**Not a number, and deliberately so.** `app/server/tests/measure_operations.py`
prints operational figures with the machine they came from and asserts nothing.
`AGENTS.md` asks for such a figure to be quoted only with the machine attached
and re-measured on the machine a claim is being made about, because every
operational number in this project was measured on one container
(`decisions/gaps.md` G8).

---

**Unverified, and recorded here rather than only in a report.**

- **Branch protection is not on.** The GitHub branch listing reports `main` as
  `protected: false`, so every rule in `.github/BRANCH-PROTECTION.md` is a
  document, not an enforcement. It needs a repository administrator.
- **The design audit does not currently pass on this branch.** `audit.sh`
  reports one violation, a hard-coded `#fff` in `app/server/demo-audio.html`,
  which arrived with the audio slice and predates this document. Twelve of the
  thirteen checks are clean.
- **Six of the seven CI jobs cannot be fully reproduced in this container.**
  Node here is 22.22 and CI uses 24, so the client guard catalogue and the
  transport tests do not start; the browser job needs Playwright and a real
  Chromium.
- **No claim here is evidence about the product.** Everything in this document
  is about the apparatus. What the apparatus has not yet shown is in
  `decisions/gaps.md` G4: the evaluation directories are empty, and the project
  cannot yet demonstrate that the tool helps anyone do anything.
