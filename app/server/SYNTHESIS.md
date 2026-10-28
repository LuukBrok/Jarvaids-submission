# Batch synthesis: photographs and a transcript to a canvas proposal

`genai_server/synthesis.py` takes photographs of the sticky-note wall and a
Whisper JSON transcript, and writes one **provisional** proposal: points with
their sources, organised into a form with groups. It runs once, after the
meeting. Nothing it writes is accepted, and it writes nothing to a session.

## The three phases

| Phase | Model call | Gate, deterministic | When the gate refuses twice |
|---|---|---|---|
| 1a Read the wall | Photograph to sticky notes: text, paper colour, readable, partial or unreadable | Colour and status from closed lists; a readable note has text | The photograph is left out, with a warning |
| 1b Read the transcript | Segments to claims: point, decision, action or question, each citing segment ids and a verbatim quote | Cited segments exist; the quote is in them, ignoring case, punctuation and spacing | Claims that pass are kept; the rest are listed under `rejected` |
| 2 Reconcile | Claims from wall and room that make the same point become one point; disagreements go in `conflict` | Every claim in exactly one point; no invented claim ids | No merging: one point per claim, with a warning |
| 3 Structure | Points to a form (cluster, timeline, matrix, flow, hierarchy), labelled groups and relations | Form from the list, and the one the team named if `--form` was given; every point in exactly one group; at most 24 per group, the server's cluster cap; at most 12 groups; relations join two existing points | Form `ordered`, one unorganised group, with a warning |

Why claims rather than summaries: a summary cannot cite anything, and F6.3
says every claim points to session evidence. Why merging keeps every source:
the wall and the room agreeing is evidence, and a merge is a model's judgement
that a person may need to undo. Why `support` (`photo`, `speech` or
`photo+speech`) is computed from the sources and never asked of the model:
whether the wall and the room agree is a fact about provenance.

Each gate gets one repair call carrying the failed checks, then falls back to
an output that invents nothing (pipelines.md 4.1 S5). Unreadable notes are
never merged: they are listed for typing by hand. More than 60 points skips
phase 3, the cap pipelines.md 4.1 S1 sets for one visualisation call.

## Running it

Fixture, offline, no key. Use it to check your files are read correctly:

```sh
cd app/server
python3 -m genai_server.synthesis --photo wall1.jpg --photo wall2.jpg --transcript meeting.json
```

Claude:

```sh
pip install -r requirements-claude.txt
python3 -m genai_server.synthesis --provider claude --photo wall1.jpg --transcript meeting.json
```

Options: `--form timeline` names the form instead of letting the model choose;
`--budget-tokens N` (default 300000) stops before a call once that many tokens
are spent, so a run can overshoot by at most one call; `--effort` (default
`medium`, a guess to be tested against `high` on the same inputs).

Output goes to `evidence/raw/synthesis/` as JSON plus a Markdown twin to read.
`--out` can point elsewhere, but not into tracked parts of the repository: the
output quotes the transcript, and transcripts carrying identifiers stay out of
git (AGENTS.md). The CLI refuses such a path.

### Transcript format

openai-whisper's JSON (`{"segments": [{"start", "end", "text"}, ...]}`) or a
bare list of `{start, end, text}`, which is what most faster-whisper scripts
write. A `speaker` string per segment, as WhisperX writes, is kept. Segment ids
are assigned by position, so the model can only cite segments that exist.

### The API key

Put `ANTHROPIC_API_KEY=...` in `.env` at the repository root, which is
gitignored, or export it. The CLI reads only that one key from `.env` and never
overrides a key already in the environment.

Do not store it as a GitHub Actions secret. Anyone with write access, or an AI
agent working for them, can push a workflow that reads a secret and sends it
elsewhere; log masking does not stop that. CI runs on the fixture and needs no
key. Use a key made for this project with a monthly spend limit, so revoking
it costs nothing.

## What leaves the machine with `--provider claude`

- Each photograph, decoded, oriented and re-encoded as JPEG with a 2048 px
  long edge. EXIF, GPS and device data are removed; visible names and faces
  are not.
- The transcript's segment text, start times and speaker labels.
- The claim and point texts derived from them, in phases 2 and 3.

Audio never leaves; F6.2 is about audio and still holds. The decision to send
the rest is in `decisions/decision-log.md`.

The adapter uses structured outputs, so every answer matches a JSON schema
before the gates check what a schema cannot: that ids exist and quotes are
real. It opts into Anthropic's server-side refusal fallback; when another
model answers, the output's `producers` names the model that actually
answered. A refusal, a cut-off answer or a rate limit fails that step only.
A rejected key or a malformed request stops the run.

## Cost

A guess, not a measurement: under $1 for an hour-long meeting and one
photograph, at the configured model's list price on 13 October 2026 ($4 per
million input tokens, $20 per million output). Every output file carries a
`usage` block with the tokens each call used; the first real runs should
replace this guess with those numbers.

## What has and has not been verified

Verified, 13 October 2026, in a Linux container with Python 3.13:

- 46 tests in `tests/test_synthesis.py` and `tests/test_synthesis_guards.py`,
  passing.
- `tests/synthesis_mutation_check.py`: 26 of 26 guards caught by their named
  assertions.
- The adapter against the real `anthropic` 1.13.0 SDK with a mocked network:
  the request carries the model, the fallback beta, `fallbacks: "default"`,
  the schema and the effort; a streamed answer is parsed; 400 and 401 stop the
  run, 429 and 529 fail the step.

**Not verified:**

- **One real run, 18 October 2026**, on three iPhone wall photos and a
  fictional transcript (`evidence/synthetic/demo-synthesis-2026-10-18.md`):
  20 points, 6 calls, 20706 input and 4528 output tokens (about $0.17), 52 s,
  every gate passed on the first attempt. Wall and speech claims for the same
  note were merged across two photos; a disagreement came out as two points
  rather than one point with a `conflict`. The whole-photo read misread one
  word ("set" for "get") that the live region reader had right.
  Quality is judged by one person on one fictional meeting, not measured. The test
  `pipelines.md` section 2 asks for before relying on the photo phase, whether
  correcting the output beats retyping, has not been run.
- The cost guess above.
- Long meetings. The transcript goes in one call; over 400000 characters or
  5000 segments is refused rather than chunked.

## Not built yet

- **Getting points onto the canvas.** Each point maps onto the server's
  existing review flow: a `content` proposal whose refs are the image and text
  sources it came from, then a `relationship` proposal with `form: "cluster"`
  for each group once its members are accepted. API.md says only `cluster` is
  implemented server-side.
- Rule-first form selection (pipelines.md 4.2). The model chooses unless the
  team names the form.
- A crop per sticky note. Notes cite the photograph and their position in
  reading order, not a region.
