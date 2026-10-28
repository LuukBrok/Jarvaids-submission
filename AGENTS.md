# Working in this repository

Instructions for any AI coding agent working here: Claude Code, Codex, Cursor,
or a human who would rather read one page than five.

This is the single source of truth. `CLAUDE.md` points here and adds nothing.
Two copies of the same conventions drift within a week and nobody diffs
instruction files, so there is one copy.

---

## Integrated tutor trial, 27 October 2026

The later integration supersedes the missing-WP1 statement below. Read
[INTEGRATION-20261027.md](INTEGRATION-20261027.md),
[VOICE-AND-MP3-TEST-20261027.md](VOICE-AND-MP3-TEST-20261027.md) and
[TUTOR-DEMO.md](TUTOR-DEMO.md) for source revisions, measured outcomes,
operator recoveries and the three localhost presentation links. Persisted
summaries, Julie's bridge and Pieter's interface/calendar refinements are
combined. Luuk approved the five-colour topic presentation and temporary
cloud summary option; the local summary-model download was incomplete.
Raw evidence, recorded inputs and credentials remain ignored and local.


## Automatic workspace, 20 October 2026

Luuk explicitly requested automatic photo detection and application of all inputs,
without routine acceptance. The PC launcher now enables `--automatic-workspace`
and the real photo reader. Whole sanitised wall photographs are sent to the
configured reader when chosen. Source/model labels, editing, undo and capture
agreement remain. Read [the current design](docs/superpowers/specs/2026-10-20-automatic-workspace.md)
and [command phrases](docs/COMMAND-PHRASES.md). This instruction supersedes older
manual marking/acceptance policies below. Review mode remains an explicit legacy
server configuration for compatibility and its contract tests.

## Integrated trial, 20 October 2026

Read [COMPLETE-LOCAL-TEST.md](COMPLETE-LOCAL-TEST.md) and
[LOCAL-FEATURES.md](LOCAL-FEATURES.md) for the current integration. Main's latest
canvas and photo reader are combined with polling, to-dos, requirements and
calendar execution. Rosalique's WP1 remains missing, confirmed by Luuk. Julie's
summary-to-sticky exploration is available separately; it is not the session's
live overview pipeline. Real photo reading is explicitly selected, not enabled
silently. Older dated baseline statements below are historical where superseded.

## Current team priorities, 14 October 2026

**Read [docs/team-plan.md](docs/team-plan.md) before choosing or implementing
work.** It holds the team's current priorities, owners, dependencies and
submission plan so assistants working for different teammates share one brief.
The wider flowchart and older backend backlog remain reference material; they
do not override this dated work plan.

Identify the relevant package and coordinate shared interfaces with its owner:
Rosalique owns transcript-to-overview (WP1), Julie overview-to-canvas (WP2),
Luuk command execution (WP3), and Pieter photo/handwriting-to-canvas (WP4).
Everyone shares integration and delivery (WP5). Make substantial progress for
Tuesday morning, 20 October 2026. Submission is Wednesday of course week 9 on
Brightspace; the precise date/time is not yet supplied. Demonstrate on localhost
using `LOCAL-TEST.md`.

Reuse existing transcription, recognition, synthesis and canvas components.
Distinguish recognised commands from executed actions, and fixtures from live
model output, because neither recognition nor a synthetic example proves the
integrated feature works. Report your package, changed interfaces, verification
and blockers, and update the plan when a team agreement changes.

## What this is

A university GenAI course project. The product is **Jarvaids**: a tool that sits
in a live design meeting, takes the minutes, and organises the meeting visually
onto a shared canvas from voice and photographs. It is assessed on the
reasoning as much as on the artefact, which is why this repo keeps rejected
options, stated costs and measured numbers rather than only the winning answer.

Model-made content must remain identifiable and source-backed. In automatic
workspace mode it is applied without human acceptance; never manufacture an
accepted-by identity. The earlier provisional-until-accepted rule describes
legacy review mode.

Start with `deliverables/documentation/flowchart.md`. It defines the
functionality numbering, F1.1 to F6.6, that the rest of the repo cites.

## Where things are

| Path | What |
|---|---|
| `deliverables/documentation/` | The flowchart and the pipeline map, as HTML and as markdown. **Read the `.md` versions**, they carry the same content at a fraction of the size. |
| `app/design-system/` | Tokens, spec, exemplar screens, and the tooling that verifies them |
| `app/server/` | The backend: Python, SQLite and the offline Pillow decoder |
| `app/ios/` | A Swift client core. **Never compiled.** See its `VERIFICATION.md` |
| `ideation/` | Concepts and explorations, including rejected ones |
| `decisions/` | Decision log and AI use log |
| `evaluation/`, `evidence/` | Test cases, findings, field material |

## Before you finish: run these

From the repository root. Run the checks below. Record unavailable checks as
unverified, never as passing; `app/server/BUILD-STATUS.md` holds candidate results.

```sh
./app/design-system/spec/audit.sh              # design system, 13 checks
node --test app/client/tests/contrast-unit.mjs   # every contrast pair (client tokens; DESIGN.md 2)
(cd app/server && python3 -m unittest discover -s tests)   # complete backend suite
(cd app/server && python3 tests/mutation_check.py)
(cd app/server && python3 tests/media_mutation_check.py)
(cd app/server && python3 tests/isolated_mutation_check.py)
(cd app/server && python3 tests/schema_mutation_check.py)
(cd app/server && python3 tests/runtime_mutation_check.py)
(cd app/server && python3 tests/synthesis_mutation_check.py)
(cd app/server && python3 tests/extractor_mutation_check.py)
(cd app/server && python3 tests/client_mutation_check.py)
(cd app/server && node --test --test-isolation=none tests/client-transport-unit.mjs tests/session-sync-unit.mjs tests/board-order-unit.mjs)
(cd app/server && python3 tests/client_http_check.py)
python3 .github/scripts/check_schema_versions.py   # one meaning per schema version
python3 deliverables/documentation/check_proposal.py   # every F-number has exactly one of four statuses
(cd app/server && python3 tests/measure_sync.py)   # one acceptance stays under 5 KB a client
```

All of these now also run in CI on every pull request, in
`.github/workflows/verify.yml`. Running them yourself is still faster than
waiting for a red build, and two of them exist because of specific accidents:

- **`check_schema_versions.py`.** Two branches each added a migration and each
  numbered it version 2. Both were green alone; the collision only existed in
  the union, and a database written by either side would have been read as the
  other's shape. `SCHEMA_VERSIONS` in `db.py` is now the registry, and claiming
  a number twice produces a git conflict on one line instead of silence. Add
  the line there before you write the migration.
- **`measure_sync.py`.** A delta grew with the board, 8183 B per client against
  a 5 KB budget, because the realistic fixture was behind a flag and nobody ran
  it. It now runs by default and exits non-zero over budget.

The six Python mutation harnesses and the JavaScript catalogue share one runner, `tests/mutation_runner.py`. They
were forty identical lines copied five times, differing in four values. Adding a
harness is a mutant list and one call: `check_one_target` when every mutant is
in one file, `check_multi_target` when a guard spans two, `check_javascript` for
the client. 223 guards: 113 service, 45 JavaScript, 26 synthesis, 12 schema, 10
runtime, 9 media, 8 isolation.

`client_mutation_check.py` needs a Node with `--test-isolation`. CI uses Node 24
and it passes there; it will not start on Node 22.22, which is what this
development container has, so a green local run is not a full run. Say so rather
than reporting six of seven harnesses as everything.

`tests/measure_operations.py` prints the operational numbers and the machine
they came from: connection-slot recovery, memory under concurrent image intake,
a write that fails at the operating system, and what a deleted session leaves on
disk. It asserts nothing. Quote a number from it only with the machine attached,
and re-run it on the machine a claim is being made about. Two rules live in that runner and are worth
knowing before you write a mutant: the mutation happens in a throwaway copy of
the tree, never the working one, so a killed process cannot leave your source
mutated; and an **error is not a kill**. A mutant that makes the suite crash or
fail to import has not shown that a guard matters. Only the named assertion
failing shows that, so write the assertion to fail rather than to raise. Use
`.get('key')` where a mutant removes a key, not `['key']`. The JavaScript
catalogue uses `check_javascript`, whose Node TAP parser likewise requires the
specified assertion to fail and refuses collection, syntax and timeout errors.

For the fast subset before every push:

```sh
git config core.hooksPath .githooks
```

Protecting `main` needs repository admin rights and cannot be done from a
session here. The settings, and the accident behind each one, are in
`.github/BRANCH-PROTECTION.md`.

If you touched an HTML page, render it before you claim it works. Chromium is
at `/opt/pw-browsers/chromium-1194/chrome-linux/chrome`; pass it as
`executablePath`. Check zero console errors, zero failed requests, and no
horizontal body overflow at 1440px **and** 400px. Then screenshot it and
actually look at the screenshot. Hand-placed SVG coordinates collide silently
and no automated check will catch it.

## House style

- **No em dashes.** Use a comma, a colon, or the word "and". This is not a
  preference to be talked out of; it is checked.
- British spelling in prose. Code follows its own language's conventions.
- **Every rule carries its reason.** A rule without one gets deleted by the next
  person, because they cannot tell whether it was load-bearing.
- State costs. A decision written without what it costs is a slogan.
- When you guess a number, say so and say how it would be tested.

## Things that are easy to get wrong here

These are all mistakes that have actually been made in this repo.

**Do not hand-edit a generated table.** `spec/accessibility.md` holds a contrast
table produced by `contrast-check.py --markdown`. It once said "do not hand-edit
this table" while being maintained by hand, and it had gone stale. Regenerate it
and verify byte-identical.

**Do not duplicate token values.** If a value is definitionally another value,
bind it with `var()` or `color-mix()` so it cannot drift. Two tokens that
happened to share a literal are how the ink ladder went unnoticed for weeks.

**Do not add a dependency without checking it works offline.** The exemplars and
documents must open by double-click with no network. A library that fetches a
WASM blob from a CDN unless you opt out is disqualified, not configured.

**Do not trust a green test suite as proof a guard works.** Ten injected
mutations to `app/server` left all 45 tests passing, including deleting the
deletion-receipt credential check. `tests/mutation_check.py` now removes each
guard in turn and fails if the suite does not notice, and `tests/test_guards.py`
holds the test that catches each one. If you add a guard, add a mutant and a
test in the same commit.

Watch for a test that cannot fail. Three of those ten tests passed against the
mutated source on the first attempt: two lowered a cap on the instance, which
shadows the class constant the mutant edits, and one asserted an outcome that
both branches produce. A test only counts once you have seen it go red.

**Do not describe unverified work as verified.** If you could not compile, run or
measure something, say that in the artefact itself, not only in a chat message.

## The design system

Read `app/design-system/CLAUDE-fragment.md` before generating any UI. It is the
distilled rulebook, and `app/design-system/spec/` has the full detail by topic.

The short version (rebuilt 18 October, see `decisions/decision-log.md`): one
face, Archivo, with six roles and weight carrying the hierarchy. One hue per
screen: one blue accent in tonal steps, a slightly cool ground, a sunken tone
for settled things. Separate by space, then tone, then a line, never a fill and
a line together. Model output is proposed: no fill, a dashed accent line and the
word "Proposed"; accepted work is a tonal fill. Shadows only on floating
surfaces, no gradients, nothing loops. Six statuses, each a shaped glyph plus a
word. Neutrals are one ink at several strengths, and the ground must be known
before any of them is used on it.

Planned F3.8 permits topic-coloured sticky-note content surfaces with group labels
and a key. These use a separate categorical palette, not status or action tokens;
provisional strokes and labels remain independent. See `spec/expandable-notes.md`.
Current tokens and contrast checks do not yet implement or validate these fills.

Colour schemes are in `spec/colour-schemes.md`, the ink ladder in
`spec/ink-ladder.md`, canvas layout in `spec/canvas-layout.md`.

## What is missing

Before starting anything, read `decisions/gaps.md`. It is the honest list of
what this project does not have, checked against the code on 16 September,
with a direction for each. Two of its gaps have moved since and are restated
here so the two files do not disagree:

- **There is a client now, and it is the first thing a person can use.**
  `app/client/` is plain ES modules served by `serve.py`, driven end to end by
  `tests/journey.mjs` in a real browser. It draws anything a model made as
  provisional and sends a drag straight to `item.place` with no review.
  `gaps.md` G1 is closed; read `app/client/README.md` for what it is not.
  Since 6 October it is one workspace: a pannable canvas with groups and
  notes that open in place, a review rail, and a live (stand-in) transcript.
  The README has a ten-minute click-through for checking it by hand.
- **The localhost speech path now runs real local transcription.**
  `LOCAL-TEST.md`, `LOCAL-FEATURES.md` and `app/server/BUILD-STATUS.md`
  describe the integrated Whisper, speaker matching and command recognition
  and their verification limits. Polls, to-dos, requirements and calendar execute
  on the canvas; general notes and overview generation remain missing.
  Room accuracy and overlapping-speaker separation
  are not established. The default fixture CLI and the real localhost launcher
  are different configurations; do not infer one from the other.

`decisions/backend-chunks.md` remains the detailed technical backlog, with its
5 October snapshot preserved. Use `docs/team-plan.md` for current priorities
and owners. Still check a claim against the code before building on it.

## The backend: current boundaries and remaining work

The integrated A/E/D and B/C backend replaces shared guest credentials with expiring single-use invitations,
adds removal and withdrawal, separates membership from capture state, and guards
activation/close against stale session revisions. Every authenticated member can
stop capture. A heartbeat never reactivates it. Control commands use an
actor-scoped monotonic sequence and bounded replay window; refresh after an
expired replay instead of assuming that its earlier outcome never committed.

Photographs are fully decoded, oriented and re-encoded as clean PNG pixels with
the offline Pillow dependency, tested at the version in `app/server/BUILD-STATUS.md`.
Sources and their histories reference
immutable sanitised media rather than embedding original bytes. Full images and
revision-checked crops require the uploader's current participant authority or a
facilitator. Re-encoding removes metadata, not visible names or faces.

The configured server runs its synthetic fixture adapter in a bounded, killable
child process. Completion results survive transient store failures in a bounded
in-memory cache, with authority checked before commit. Deletion clears retained
results and revokes execution tickets. A process crash still loses an uncommitted
in-memory result. Startup marks claimed jobs uncertain before expiry cleanup
and never requeues them. A deliberate new attempt requires an explicit uncertain-
cost acknowledgement; returned usage survives proposal cancellation or rejection.
Provider-specific idempotency, cost limits and remote reconciliation remain open.

The synthetic HTTP journey exercises the configured server, independent joining,
agreement, photo intake, fixture extraction, crop, human acceptance, both export
paths, withdrawal and deletion. Test and mutation counts belong in
`app/server/BUILD-STATUS.md`, together with the exact candidate and limitations.
Mechanism checks are not evidence of OCR quality, phone connectivity or user value.

Remaining boundaries:

- **Joining is device-mediated, not proof of identity.** A facilitator can still
  deliberately redeem their own invitation. Existing credentials are preserved by
  migration; an old session does not acquire independent credential provenance
  retroactively. Use a new session to exercise the independent join protocol.
- **B/C supplies canonical positions and transaction-collected changes.**
  Position revisions are separate from content revisions; `item.place` moves
  records without accepting their meaning. Delta snapshots, gzip and keep-alive
  are part of the combined contract. Collision rules, larger board forms and a
  forced-resync bound for large cascades remain open. Preserve these features
  when changing membership, capture or media logic.
- **The default server CLI uses fixtures.** `FixtureExtractor` for
  photographs and `FixtureTranscriber` for audio are the only adapters the
  default CLI enables. The localhost launcher enables real local speech;
  live photo extraction defaults to synthetic; the explicit real-photo launcher selects Claude. Fixture output must remain visibly
  synthetic and provisional until a person accepts it. Adapters must not
  launch detached children; remote network and billing behaviour needs its own
  evidence before a provider is enabled.
- **The batch synthesis has a Claude adapter, outside the server.**
  `python3 -m genai_server.synthesis` turns wall photographs and a Whisper
  JSON transcript into a provisional proposal file; `--provider claude` sends
  sanitised photographs and transcript text to Anthropic with the key from a
  local `.env`. It writes no session record and the server does not call it.
  `app/server/SYNTHESIS.md` says what leaves the machine and what has not
  been run.
- **LAN binding is not device verification.** Loopback remains the default.
  Explicit advertised hosts and exact origins permit configured LAN access, but
  plain HTTP is unencrypted and no real phone/firewall journey has been verified.
- **Exports do not bundle source evidence.** Nonpersistent snapshot downloads
  remain available at logical storage caps. Their source references depend on
  the session and stop resolving after deletion; downloaded copies are outside
  server deletion control.
- **This is still a local prototype.** Physical disk exhaustion, operational
  backup/receipt retention, broader contract hardening and user evaluation are
  not certified by the synthetic failure tests. The Swift client remains
  uncompiled and must not be assumed compatible with these revised contracts.

Use `/ready` for runtime readiness; `/health` is HTTP liveness only. Session
diagnostics require a current facilitator and must remain read-only and free of
source content, credentials and exception text. Readiness requests must never
manufacture worker progress or recreate a missing store.

Schema preflight must reject unsupported structural layouts before any migration
write; preserve its tests when changing tables or constraints. Lost sole-facilitator
credentials have no reset route. Fresh invitations never inherit agreement.

Start from `app/server/API.md` and its executable tests. In particular, legacy
facilitator-supplied invite payloads are rejected, control sequences are command
envelope fields, and activation requires the current session revision. Consult
`decisions/backend-chunks.md` for requirement ownership and remaining work.

## Logging your work

This is a course project assessed partly on **traceability of AI involvement**.
An undocumented contribution is worth less than a documented one, however good
it is. Two logs, both in `decisions/`, and you write the row when the work
lands rather than at the end of the project.

**`decisions/ai-use-log.md`** gets a row per work package: what the tool did,
what it touched, and what review actually happened.

**`decisions/decision-log.md`** gets a row per decision that closed off an
option: what was chosen, what else was considered, why, and whether it is
reversible. A decision with no alternative listed is not a decision, it is a
default, and it does not need a row.

Three rules that decide whether the log is worth anything:

1. **Be honest about review.** Directing an agent and accepting its output is
   not the same as reading it. Write which one happened. "Directed by the team,
   verified by automated checks, not reviewed line by line" is a perfectly good
   entry and it is the truth in most rows here. Claiming a review that did not
   occur is the one failure mode that makes the whole log worthless.
2. **Log what could not be verified, in the row.** If code was never compiled,
   a number was never measured on real hardware, or a claim rests on a source
   you could not fetch, the row says so. `app/ios` is the standing example: it
   has never been compiled and its row says that in bold.
3. **One row per work package, not per commit.** The commit history already has
   the per-commit detail and links from the pull request. The log is for
   somebody reading the project cold.

Blank lines between rows end a markdown table, so keep the rows contiguous.
Both files were broken this way once and the last entry in each silently stopped
rendering as a row.

## Git

- Work on a feature branch. Never commit to `main`.
- **Ask before pushing** unless the person you are working with has said
  otherwise in this session.
- If `main` has moved ahead, merge it into your branch before opening a pull
  request. A stale branch shows other people's files as deletions, and merging
  a PR like that removes their work. This has nearly happened twice.
- Do not put a model name in a commit message, a pull request, a code comment or
  any other artefact in the repository.

## Two rules that are not negotiable

From the repository README, and they predate all of this:

- Secrets live in `.env`, which is gitignored. `.env.example` lists key names
  only.
- Raw recordings, transcripts carrying identifiers, and consent records stay in
  `evidence/raw/`, which is gitignored. They do not enter the public repo.

  **Known exception, recorded so nobody mistakes it for the rule.** On
  22 September the group chose to leave the Week 3 recordings, transcripts
  and a session photograph on `main` under `week 3 materials/`, because the
  repository is private to the group during this phase and the material was
  needed for the midpoint deliverable. `decisions/decision-log.md` carries
  the row. The rule above is still the target: before the repository is
  shared beyond the group, that material moves to `evidence/raw/` and the
  history is purged, and nothing new follows the precedent. Agents do not
  read, copy or quote those files; annotate through the report and the
  summaries instead, as `deliverables/week4-midpoint/annotations/` does.
