# CLAUDE.md

**Read [`AGENTS.md`](AGENTS.md) first. It is the whole brief and this file adds
nothing to it.**

`AGENTS.md` is the single source of truth for everyone: Claude Code, Codex,
Cursor, and humans. It is not duplicated here on purpose. Two copies of the same
conventions drift within a week, and the drift is invisible because nobody
diffs instruction files. This repository has already been bitten by exactly that
pattern twice, once with a stylesheet that duplicated token values and once with
a contrast table that was hand-maintained under a heading reading "do not
hand-edit this table".

If you are about to write a second copy of something, that is the moment to bind
it to the first instead.

## The ninety-second version

- The product is **Jarvaids**: a during-meeting assistant that turns speech and
  photographs of a sticky-note wall into a visual record. Anything a model made
  is **provisional** until a human accepts it, and is never rendered as if a
  human made it.
- Read `deliverables/documentation/flowchart.md` for the product and the F1.1 to
  F6.6 numbering the rest of the repo cites. Prefer the `.md` files over their
  `.html` twins: same content, a fraction of the size.
- Before finishing, run the three commands in `AGENTS.md`. They take seconds.
- No em dashes. British spelling. Every rule carries its reason.
- Generating UI? Read `app/design-system/CLAUDE-fragment.md` first.
- When your work lands, log it in `decisions/ai-use-log.md`, and log any
  decision that closed off an option in `decisions/decision-log.md`. Be honest
  about what review actually happened.
