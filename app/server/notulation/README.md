# Rolling minutes: a transcript to a section-by-section overview

`pipeline.py` is WP1 (`docs/team-plan.md`): it turns a brainstorm transcript
into a **provisional** overview, organised by topic rather than by time, the
way a brainstorm actually works. It answers the specific shape the work was
asked for: wait while a topic is still running, summarise a section once it
closes, and when the room circles back to a topic already closed, update that
section to the latest decision instead of opening a second one.

This package lives beside `app/server/genai_server`, not inside it, and
changes nothing in that package: it imports what it reuses
(`load_whisper`, the gate/ledger machinery, the output-path check) from
`genai_server.synthesis` rather than copying it.

It implements pipelines.md section 6, "notulation", over a complete
transcript file rather than a live stream: the two deterministic stages (S1
buffer, S2 topic boundary) and the five model stages (S3 conclusion detection
through S7 open-question tracking) run as one pass. The live loop that reads
S1/S2 continuously off the event bus is future work; this is the batch
equivalent, the same relationship `genai_server/synthesis.py` has to the live
photo and speech pipelines it eventually feeds.

## The two stages

| Stage | Model call | What decides the boundary between topics | When a topic is treated as "the same one" |
|---|---|---|---|
| 1 Segment, boundary | None | A silence of 8 seconds or more, a sharp change in vocabulary between what was just said and what comes next, or a block simply growing past 2200 words (pipelines.md 6.3) | n/a |
| 2 Conclude, summarise, extract | One LLM call per block | n/a | The model's own topic label matches a topic already summarised, or the model names that topic in `continues_topic`, checked deterministically against the topics it was shown |

A block carries one gated model call that answers five questions at once,
sharing pipelines.md S3 to S7's "shared call" design:

- **Concluded?** The single question this module exists to get right (F2.1):
  summarising a discussion before it has actually concluded, as though it had,
  is the specific failure the user described and the task asked to avoid.
  When unsure, the model is told to say no.
- **Continuing a known topic, or a new one?** This is the circling-back
  behaviour. The model is shown every topic label summarised so far and may
  either answer with a new label, or copy an existing one into
  `continues_topic`. A block whose own topic label exactly matches an
  existing section's is also merged, even if the model forgot to set
  `continues_topic`, so a close paraphrase of the same label does not quietly
  fork into a second section.
- **Summary bullets**, as free prose, ignoring who said what, summarising the
  content as one whole, exactly as asked. A concluded block's bullets
  *replace* its section's summary; an unconcluded block's bullets are
  appended, deduplicated, as a running note. That split is the whole point:
  the latest word on a topic should not sit beside the stale note it
  supersedes.
- **Decisions and actions**, each required to quote, verbatim, the sentence
  that grounds it and cite the segments it came from (F6.3). Only decisions
  and actions from a *concluded* block are kept; a decision read off a topic
  that is still running is exactly the premature-summary failure this module
  exists to prevent.
- **Open questions**, added when raised and left hanging, and retired by id
  when a later block answers them. Retiring is checked the same way a
  decision is, against a closed list of ids that actually exist; F2.4 names
  forgetting to retire as the risk, so retiring is treated as equally
  important as adding.

A decision, action or open question without a verifiable quote is discarded
by the gate, the same hallucination guard `genai_server/synthesis.py` uses
for claims: a free-text summary bullet cannot be checked this way, but a
decision is a strong enough claim that it must be. Each gate gets one repair
attempt (`genai_server.synthesis._gated`, reused unchanged), then the block
falls back to an empty, visibly-gapped entry rather than showing an invented
one.

## Running it

From `app/server` (so both `notulation` and `genai_server` resolve as
packages on the path):

Fixture, offline, no key:

```sh
cd app/server
python3 -m notulation.pipeline --transcript meeting.json
```

Claude:

```sh
pip install -r requirements-claude.txt
python3 -m notulation.pipeline --provider claude --transcript meeting.json
```

Ollama, local, no key and no extra package (uses only `urllib`): needs
`ollama serve` already running on the same machine this command runs on, and
the named model already pulled.

```sh
ollama pull llama3.1
python3 -m notulation.pipeline --provider ollama --model llama3.1 --transcript meeting.json
# --ollama-host http://127.0.0.1:11434 is the default; override if ollama serve listens elsewhere
```

Ollama enforces the JSON schema itself (grammar-constrained decoding, not the
model's own judgement, so it works with most models Ollama can serve), and
`check_block` still checks the answer afterwards regardless, the same as it
does for Claude's structured output.

Options mirror `genai_server/synthesis.py`: `--budget-tokens` (default
300000), `--effort` (default `medium`), `--out` for the JSON path (a `.md`
twin is written beside it; defaults under `evidence/raw/notulation/`, and the
CLI refuses a path inside the tracked repository outside `evidence/raw/`, for
the same reason `synthesis.py` does: the output quotes the transcript).

### Transcript format

The same Whisper JSON `synthesis.py` reads: `{"segments": [{"start", "end",
"text"}, ...]}` or a bare list of the same, with an optional per-segment
`speaker`. Reused directly (`load_whisper`), not duplicated.

## What leaves the machine with `--provider claude`

The current block's segment text, timestamps and speaker labels; the labels
of topics already summarised, so the model can recognise the room circling
back; and the text of open questions not yet retired. Audio never leaves;
F6.2 is about audio and still holds.

## What has and has not been verified

Verified, 20 October 2026, in a Linux container with Python 3.13:

- 36 tests, passing: 27 in `tests/test_pipeline.py` (boundary detection
  including the silence-versus-lexical-shift distinction, every gate failure
  mode (bad `concluded`, an unknown `continues_topic`, an uncited or
  misquoted decision, retiring an unknown question id), the circling-back
  merge both by an explicit `continues_topic` and by an exact repeated topic
  label, a question opened in one block and retired in a later one, a block
  that fails its gate twice falling back without inventing content, and the
  CLI writing JSON and Markdown and refusing a tracked-repository output
  path) plus 9 in `tests/test_ollama_adapter.py` (request shape against a
  mocked `urllib`: the shared system prompt and schema are sent, a repair
  round includes the previous answer, connection-refused and unpulled-model
  404 are reported with the fix named, a non-200 HTTP error or a timeout is a
  retryable `ModelFailure` not an abort, a non-JSON or missing answer is a
  `ModelFailure`). Run from `app/server` with
  `python3 -m unittest discover -s notulation/tests`.
- The full existing `app/server/tests` backend suite (471 tests) still
  passes unchanged; this package touches nothing in `genai_server`.
- A run against `evidence/synthetic/demo-transcript-chemistry-brainstorm.json`
  (the WP1/WP2 handoff transcript used for the batch synthesis demo) with the
  bundled fixture: `evidence/synthetic/demo-notulation-2026-10-20.md`.
- A run against a real ~20-minute, two-speaker interview transcript supplied
  outside this session (not committed here: AGENTS.md keeps real transcripts
  out of the tracked repository), with the bundled fixture: 366 timestamped
  lines, 20 boundary-detected blocks, merged into 14 sections, zero gate
  failures. Confirms the segmentation and merge logic hold up on real timing
  and real conversational Dutch, not just the short hand-built test fixtures
  above; says nothing about summary quality, which the fixture does not
  attempt.

**Not verified:**

- **No real LLM run, on any provider.** No `ANTHROPIC_API_KEY` was available
  in the session that built this, and this cloud session cannot reach a
  user's local `ollama serve` (it runs on their machine, not this
  container), so neither `claude_adapter.py` nor `ollama_adapter.py` has been
  called for real; the Ollama tests mock `urllib` rather than a running
  server. The 36 tests exercise the gate, the merge logic and each adapter's
  request/error handling against a scripted or mocked model standing in for
  the LLM, which proves the plumbing, not real summary quality, real
  conclusion-detection judgement, or whether a real model reliably
  recognises circling back. That is the next thing to run, the same
  way `synthesis.py`'s own first real run replaced a cost guess with a
  measurement.
- **Boundary tuning against a real meeting.** On the demo transcript, a
  continuous three-minute fictional brainstorm, the heuristics found exactly
  one boundary. That may be correct (it largely is one topic) or it may mean
  8 seconds and the lexical-overlap threshold need tuning against how real
  meetings actually pause and shift; pipelines.md 6.3 already states both
  numbers as guesses, not measurements, for the same reason.
- **Mutation testing.** Unlike `synthesis.py`, this module's gates are not
  wired into `app/server/tests/mutation_check.py`, and because this package
  now lives outside `app/server/genai_server` and `app/server/tests`, it is
  also not picked up by the repo-wide `python3 -m unittest discover -s tests`
  command in `AGENTS.md`'s own checklist. Run its tests with the command
  above as a separate step; that is the cost of keeping this addition
  isolated from the existing packages rather than wired into their shared
  commands.
- **Real-time behaviour.** This runs over a complete transcript file, not
  live against the event bus; S8 (agenda anchoring) and S9 (emit to the
  minutes panel and offer canvas items) are not built, because there is no
  live session or canvas item type to emit into yet.

## Not built yet

- **Tier A's 90-second cadence.** This module summarises each block once, on
  conclusion or not; the live pipeline's frequent "still running" ticks
  between boundaries are not simulated here, because without a live clock
  there is nothing to tick against.
- **Agenda anchoring (S8).** No agenda model exists yet to anchor a block to.
- **Getting a section onto the canvas (S9).** Each concluded section's
  decisions and actions map onto the server's existing review flow the same
  way `synthesis.py`'s points do; not wired up, coordinate with WP2.
