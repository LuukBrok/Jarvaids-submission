# WP1 prototype: transcript to topic overview

A standalone demo for WP1 (Rosalique, "transcript to summary / structure /
overview", `docs/team-plan.md`), implementing flowchart.md's **F2.1 rolling
minutes**: *"A running summary that stays current through the meeting rather
than appearing at the end"*, and its stated risk, *"summarising too early
flattens a discussion that has not concluded yet"*.

It takes a transcript that already exists as text (no transcriber here: that
is F1.2/F1.3, already in `app/server`) and walks it in order, in chunks,
keeping a running set of topics rather than one end-of-transcript summary:

- A chunk that is genuinely new subject matter starts a new topic.
- A topic is written up as **closed** only once the chunk itself shows the
  discussion reaching a conclusion or the group visibly moving on, never
  just because the chunk ends.
- A later chunk that returns to an already-closed topic **reopens** it and
  revises its summary to the latest decision, which supersedes the old one;
  it can close again afterwards.
- Who said which line is dropped from the summary on purpose: every
  speaker's fragments on one subject are folded into one description of
  that subject, per the brief.

This is deliberately standalone: no server, no canvas, no voice pipeline. It
is meant to be checked against real transcripts first and folded into
`app/server/genai_server/` (alongside `synthesis.py`, which already has a
similar transcript-to-claims step) once the approach is good enough to share
with Julie (WP2) and Luuk (WP3), per the WP1 checklist.

## Running it in a browser (recommended for a first try)

```sh
python3 webui.py
```

Open the printed `http://127.0.0.1:8765/` in a browser. Paste a transcript
in, pick a provider, click **Generate overview**. The page shows a live log
as each chunk is processed (so a slow local model does not look like it has
frozen, which running `overview.py` from the command line gave no sign of
until it was entirely done), then the result as topic cards: a status badge
per topic, a reopened badge where that happened, and the supporting quotes
behind a collapsible "Evidence" section, rather than a Markdown file to read
cold. "Download .md" and "Download .json" on the result page give the exact
same files the command-line run would have written.

This is a convenience front end for trying *this prototype*, not a preview
of Jarvaids' actual UI (that is the canvas, Julie's WP2); it only renders
what `overview.py` already produces. It is plain `http.server` from the
standard library, the same choice `app/server/genai_server/http.py` already
made, bound to `127.0.0.1` only (nothing but your own browser can reach it).
No extra `pip install` beyond whatever the provider you pick needs.

## Running it from the command line

Fixture, offline, no key, proves the chunking and state machine (not the
summarising):

```sh
python3 overview.py --transcript sample-transcript.txt --provider fixture
```

Claude, the real thing:

```sh
pip install -r requirements.txt
python3 overview.py --transcript your-transcript.txt --provider claude
```

Ollama, a local model instead of an API key (see below for setup):

```sh
python overview.py --transcript your-transcript.txt --provider ollama --model llama3.1
```

Writes `<transcript>.overview.md` next to the input (`--out` to choose
another path). Add `--json-out state.json` to also get the raw topic state
(id, status, summary, every supporting quote and which chunk it came from,
how many times a topic was reopened) for WP2/WP3 to build on without
re-parsing Markdown.

`--chunk-chars` (default 3000) controls how much transcript goes into one
model call; smaller chunks track topic changes more finely but cost more
calls. `--effort` and `--model` tune the Claude call; `--model` and
`--ollama-host` tune the Ollama call.

### Running it against a local Ollama model (no API key, PowerShell)

This is the option for testing for free, repeatedly, without an Anthropic
key, and it fits this project's own F6.2 ("local processing" rather than a
third-party API). It needs **Ollama running on the same machine** you run
`overview.py` on: this script's cloud session cannot reach a model on your
own PC over the network, so this is for running on your own computer, the
same place the `.cmd` launchers in the repository root already target.

```powershell
# one-time setup
winget install Ollama.Ollama          # or download from ollama.com
ollama pull llama3.1                  # ~4.7 GB; see model choice below

# clone this branch onto that machine if it is not there already, then:
cd GenAI\ideation\explorations\wp1-transcript-overview
python overview.py --transcript your-transcript.txt --provider ollama --model llama3.1
```

No `pip install` needed for this path (`ollama_overview.py` only uses the
standard library). Ollama normally runs as a background service on Windows
right after install; if you get a connection error, start it yourself with
`ollama serve` in another PowerShell window first.

**Model choice is a real trade-off, untested here**: `llama3.1` (8B) is a
reasonable default; a smaller `llama3.2:3b` or `llama3.2:1b` is faster on a
laptop without a GPU but more likely to misjudge when a topic has actually
closed, or to drop the JSON schema on a long chunk; a larger model (for
example `qwen2.5:14b`) is slower but may track topics and reopens more
reliably. If a chunk fails to come back as valid JSON, try a smaller
`--chunk-chars` first before switching models. `--ollama-host` points at a
different Ollama instance if it is not on `localhost:11434` (for example a
model running on another machine on the same network).

### Transcript format

A plain `.txt` file, one turn per line (a `Speaker: ` prefix is fine and is
kept in the chunk text, just never relied on for the summary); or the same
segment JSON `synthesis.py` already reads
(`{"segments": [{"start", "end", "text"}, ...]}`, or a bare list of those),
so a real transcript from that pipeline needs no conversion to try this.

`sample-transcript.txt` is a short, fictional, synthetic design-meeting
transcript for smoke-testing the mechanics; it is not evidence of summary
quality (WP1 checklist: distinguish synthetic material from real sessions).

## The API key

Same rule as `app/server/SYNTHESIS.md`: put `ANTHROPIC_API_KEY=...` in `.env`
at the repository root (or in this folder), which is gitignored. Never as a
GitHub Actions secret.

## What leaves the machine with `--provider claude`

Each chunk's transcript text, and the titles and summaries of topics already
opened or closed earlier in the run (so the model can recognise a reopen).
Nothing else; there is no audio or photograph input in this prototype.
With `--provider ollama`, nothing leaves the machine Ollama runs on at all:
the call is a local HTTP request to `localhost:11434` (or `--ollama-host`).

## Traceability

Every topic's summary carries verbatim quotes from the chunk that produced
or revised it. Each quote is checked against that chunk's actual text
(`verify_quotes` in `overview.py`), the same check `SYNTHESIS.md` applies to
claim quotes; a quote that is not really there is dropped and reported under
"Processing notes" in the output, never kept silently. This is what lets a
person inspect the overview for omissions or inventions, the WP1 checklist
item this whole gate exists for.

## What has and has not been verified

Verified, 21 October 2026, in this container:

- The chunking and topic state machine (`apply_touched`, `verify_quotes`) by
  direct calls, confirming a topic can open, close, stay closed while an
  unrelated chunk is processed, reopen when a later chunk returns to it (the
  `reopened` counter and the summary update), close again, and that a
  fabricated quote not present in its chunk is dropped rather than kept.
- The fixture path end to end against `sample-transcript.txt`: chunking,
  Markdown rendering and JSON export all run and produce the expected shape.
- `_parse_timestamped_blocks` against a real 366-turn, 20-minute interview
  transcript (pandoc-converted from a `.docx`, kept out of git under
  `evidence/raw/`, per AGENTS.md): header lines are correctly merged with
  their wrapped paragraph text into one turn each.
- `ollama_overview.py`'s error handling, against no running Ollama server in
  this container (expected here: Ollama has to run on the same machine as
  the script, see above): a clear, actionable error rather than a traceback.
- `webui.py` end to end against a running local server in this container
  (curl, not a browser): the form page, a submitted job, its live log, the
  rendered result cards, both download endpoints, an unknown job id (404),
  an empty submitted transcript (400), and a provider failure (the ollama
  path with nothing listening) all come back as a readable error on the
  result page rather than a server crash. One real bug was caught this way
  and fixed: the job page's inline CSS is full of literal `%` characters
  (`width: 100%`), which broke Python's `%`-string-formatting used to fill
  in the job id; the page now builds with plain string replacement instead.

**Not verified:**

- Real summary quality and whether the model actually waits for a topic to
  conclude before closing it, or recognises a reopen correctly, rather than
  just doing the mechanically-checked parts right. This needs a real
  `--provider claude` or `--provider ollama` run against an actual
  transcript, which has not happened yet; ignoring who said what and still
  catching a topic that circles back several chunks later is exactly where
  it could go wrong.
- Any local model's JSON-schema adherence and language quality on this
  task, in particular on Dutch input; untested with any Ollama model.
- Cost and latency per meeting length: unmeasured, no run has been made.
- Long transcripts: nothing here caps total length the way `synthesis.py`
  does; a very long transcript just means more chunks and more calls, so
  cost grows linearly with length, untested at a real meeting's size.
- Mixed-language (Dutch/English) transcripts, which flowchart.md F1.2
  flags as the normal case for this project; only tested on English so far.

## Known limitations of this prototype

- Topic identity relies on the model reusing the same `id` for a topic it
  recognises as continuing; there is no independent check that two topics
  with different ids are not actually the same subject under two names. A
  model that titles a reopened topic differently and gives it a new id
  would show up as a duplicate rather than a reopen.
- Nothing forces a topic still open when the transcript ends into a false
  conclusion; it stays "open" and is labelled "still open when the
  transcript ended" in the output. That is deliberate (inventing a
  conclusion that was not reached is worse than leaving a gap), but it means
  a transcript that never neatly concludes produces an overview with loose
  ends, matching the meeting rather than tidying it.
