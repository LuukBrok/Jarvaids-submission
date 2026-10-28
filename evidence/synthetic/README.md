# Synthetic evidence

Material written to develop and demonstrate the tool, not recorded from people.
Nothing here is evidence of how a real meeting went or of how well the tool
works with real speech. Results that use it must say so.

| File | What it is | Made by |
|---|---|---|
| `demo-transcript-chemistry-brainstorm.json` | A **fictional** three-minute brainstorm in WhisperX JSON (`segments` with `start`, `end`, `text`, `speaker`), discussing the concept on the sticky-note wall in Pieter's photographs. It overlaps the notes on purpose, so the batch synthesis has wall and speech to merge, and adds speech-only content: a decision, actions, open questions and one disagreement. Speakers are anonymous labels. | Claude Code, 18 October 2026, for WP4 and the WP1/WP2 handoff |
| `demo-synthesis-2026-10-18.json` and `.md` | The batch synthesis (`app/server/SYNTHESIS.md`) run for real on that transcript and Pieter's three wall photographs: 20 provisional points with their photo and speech sources, in six cluster groups. The **handoff example for WP1 and WP2**: the shape of an overview, and what reaches the canvas once it is wired. Speech in it is fictional; note texts are read from real photographs of an earlier, unrelated brainstorm. | `python -m genai_server.synthesis --provider claude`, `claude-opus-5-5`, effort medium, 18 October 2026 |

Use it as the demo and staging transcript until a real session transcript
replaces it (WP1). The photographs it refers to stay in `evidence/raw/`,
which is not tracked.
