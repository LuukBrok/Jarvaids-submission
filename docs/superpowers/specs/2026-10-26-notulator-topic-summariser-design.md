# Notulator topic summariser: approved design

Rosalique worked through this design in conversation on 26 October 2026. It is
WP1 (transcript to overview) made concrete: the running minutes agent the
flowchart calls Agent 1, the Notulator, covering F2.1 (rolling minutes), F2.2
(decision extraction), F2.3 (action items) and F2.4 (open question tracking).
Nothing below is built yet. This is the spec to build against.

## What it does

The transcript, as it is produced live by F1.2, is organised into **two
levels**: a small number of broad themes (roughly four to eight for a whole
meeting, things like "Introduction", "Pricing", "Mechanics", "Protocol"),
each holding the more specific topics discussed under it ("Student
discount", "Payment methods" under "Pricing"). Each specific topic carries a
running summary, its decisions, its action items and its open questions,
each citing when that information was added. When the room returns to a
specific topic after talking about something else, the summariser adds a
new timestamped entry to it rather than starting a duplicate or losing the
thread.

**This two-level structure was added after the first live test** (26
October 2026, against `gemma3:4b`) of the flat, single-level version this
spec originally described. Flat topic matching worked mechanically (the
model, once prompted with a concrete good/bad example, did keep reusing an
existing short label rather than forking a new one for every mention), but
it produced around fifteen distinct topics from one minute of transcript:
each specific moment of a discussion read as its own topic, with nothing
grouping "feelings of isolation", "levels of calmness" and "overthinking"
under the one umbrella conversation they were actually part of. The broad
theme layer gives the model a second, much coarser bucket to sort into
first, which both reads better and is closer to what a person skimming the
minutes would expect to see.

Specific topics are seeded from whatever agenda the team entered at the
start of the session (F3's "drop in the agenda" step); broad themes are not
seeded, since the agenda's own items are closer in size to a specific topic
than to a theme spanning several of them, and are created by the model as
the meeting's shape becomes clear. When something comes up that does not
fit any existing broad theme or specific topic, the model creates a new
one at the relevant level. Both kinds of label are instructed to be broad
and short (one to three words for a theme, two to five for a specific
topic) with a worked good/bad example in the prompt, since an abstract
instruction alone ("name it broadly") was not enough to stop `gemma3:4b`
generating a verbose, sentence-like label for nearly every batch. Matching
an existing label also tolerates case, punctuation and whitespace drift in
code, rather than requiring the model to reproduce a label byte-for-byte,
since it reliably does not even when it means to match one.

## Update model

The summariser updates its existing state incrementally; it does not
re-read and re-summarise the whole transcript on every run. Re-summarising
from scratch would be simpler to write, but its cost grows with meeting
length and it does nothing useful with the fact that most of a long meeting
has already been processed.

## Trigger: when a batch is sent for processing

A batch is accumulated by word count, not by a fixed time interval. A clock
based trigger wastes a call in a quiet stretch and can cut a fast, talkative
stretch off mid-sentence; pacing by how much has actually been said keeps
each batch meaningful.

Once the word-count threshold is reached, the batch does not fire
immediately. It waits for the next sentence boundary (the next `.`, `?` or
`!` in the transcriber's punctuated output) so a batch is never cut off
mid-thought. This wait has a fallback cap: if no sentence boundary turns up
within some generous extra word count past the threshold, the batch fires
anyway, so a transcription that drops punctuation, or a genuine run-on
sentence, cannot stall the pipeline indefinitely.

**Open and guessed:** the exact word-count threshold and the fallback cap
are not chosen yet. Both are numbers to be tested against how a real meeting
actually paces, not assumed.

## Topic matching and extraction: two model calls per batch

Each batch goes through two separate calls rather than one combined call:

1. **Classify.** The model is shown a short, nested index (each broad theme,
   with its specific topics and their one-line descriptions underneath) and
   the new batch of text, and asked for both a broad theme and a specific
   topic in one response. It does not see any specific topic's full history
   at this stage, only the index, so this call stays small and fast
   regardless of how long the meeting runs.
2. **Create or update.** If the batch matched an existing specific topic,
   that one topic's fuller history is pulled in and the model is asked to
   merge the new information into it: extend the summary, and add any new
   decisions, action items or open questions. If it is a new specific topic
   (whether under an existing or a brand new broad theme), the model seeds a
   fresh record from the batch instead.

Splitting the work this way costs one extra model call per batch, which was
accepted deliberately: a 4B local model is noticeably more reliable doing
one simple job at a time than doing classification and detailed extraction
together in a single pass.

Whether a topic entry is a continuation of the previous batch or a fresh
"visit" (and so gets a new timestamp) is decided mechanically, not by the
model: if the immediately preceding batch was filed under the same topic,
this one extends the current entry; if it matches a topic that exists but
was not the previous batch's topic, it opens a new timestamped entry under
that topic; if it matches nothing, it is a brand new topic.

## Tolerating misattribution, never losing information

A single batch can straddle two topics (a sentence finishing off a pricing
point, immediately followed by someone starting on onboarding). The model is
not asked to split a batch across topics. An occasional sentence filed under
the "wrong but adjacent" topic is tolerated, since batches are short and the
next batch tends to correct course once the room has properly moved on.

The one thing this tolerance does not extend to: **nothing extracted is
ever dropped because the model is unsure which topic it belongs to.** A
decision, action item or open question gets attached to the model's best
guess of a topic and kept, rather than discarded for being hard to place.
This is the overriding rule for the extraction step and should be stated
explicitly in its prompt.

## Where it runs

The summariser runs locally, through Ollama, using **Gemma 3 4B**. This
follows the same local-processing spirit as F6.2 (audio stays on the
machine), extended here to text: it costs nothing per call, needs no
network dependency during the meeting, and only needs a one-time download
before the session, which is accepted as reasonable for whoever is running
the transcriber that day. 4B is chosen because the laptop running it is not
known in advance (a different person's machine each meeting), and it is the
realistic ceiling for CPU-only hardware; it is also one of Gemma 3's more
recent sizes and has noticeably better multilingual handling than most
models its size, which matters given F1.2 already flags mixed Dutch/English
speech as the project's riskiest assumption.

**Cost, stated plainly:** a 4B local model is weaker at the judgement calls
this task leans on (deciding whether something was really decided, matching
topics correctly, not inventing an owner for an action item) than a larger
hosted model would be. This trade was made deliberately for cost and
privacy, and it is untested: extraction quality against a fixture
transcript has not been measured, and should be before this is trusted on a
real meeting.

## Degradation behaviour

If Ollama cannot keep up with the pace of the meeting, batches queue and are
processed in order; none are skipped or dropped to catch up. This matches
the project's existing guardrail (F6.4): slow is acceptable, a silent gap is
not. **Not yet built:** a visible "summary is still catching up" indicator
on the canvas, which F6.4 calls for and which this design currently has no
code for.

## What this does not cover yet

- The exact prompt wording for both calls.
- The JSON shape returned by each call and how it is validated.
- Where topic state actually lives (in-memory for the session, or persisted
  like the rest of session state in F3.1's canvas data model).
- The handoff to WP2 (Julie, overview to canvas): this spec produces
  structured topic data, not laid-out canvas objects. Clustering and layout
  stay the Visualiser's job (Agent 3), not this agent's.
- Evaluation: a fixture transcript with known decisions and action items
  planted in it, checked against what the pipeline actually extracts.

## Ownership

WP1, owned by Rosalique, per `docs/team-plan.md`. Provide output examples to
Julie (WP2) and Luuk (WP3) once there is something to show, per the team
plan's stated dependency.
