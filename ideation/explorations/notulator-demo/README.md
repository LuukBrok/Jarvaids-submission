# Notulator demo

Preserved original standalone exploration. The integrated product uses
`app/server/genai_server/summaries.py`; this experiment keeps its original UI
and local-model requirements.

A standalone, throwaway way to test the WP1 summarisation design
(`docs/superpowers/specs/2026-10-26-notulator-topic-summariser-design.md`)
without the rest of the project. It is not imported by, or wired into,
`genai_server`. Nothing it does is persisted: restarting it clears
everything.

## What it does

Paste a transcript into the page and press Start. The server feeds it in
word by word at a settable pace, to simulate live speech, and batches it by
word count plus the next sentence boundary, exactly as the design spec
describes. Each batch goes through the same two Ollama calls the real
design calls for (classify, then create-or-update), and the page shows the
resulting topics live, each with its summary, decisions, action items and
open questions, next to a log of every raw model call so extraction quality
can actually be judged by eye.

## Running it

1. Install [Ollama](https://ollama.com) if it is not already, and pull the
   model:
   ```sh
   ollama pull gemma3:4b
   ```
   Ollama needs to be running (`ollama serve`, or the desktop app) and
   reachable at `http://localhost:11434` before you start the demo.
2. From the repository root:
   ```sh
   python3 ideation/explorations/notulator-demo/server.py
   ```
   On Windows, use `python` or `py` instead of `python3`, PowerShell does
   not recognise the Unix-style name:
   ```powershell
   py ideation/explorations/notulator-demo/server.py
   ```
3. Open `http://localhost:8808`, paste a transcript, and press Start.

No dependency beyond the Python standard library and a browser; nothing
here calls out to the internet except the local Ollama request.

## What this is not

- Not real speech-to-text. The transcript is pasted text, fed at a
  simulated pace; there is no microphone or F1.2 integration here.
- Not the real WP1 implementation. If the design changes, or extraction
  quality turns out to need a different prompt or model, this demo is
  disposable, not something to carefully migrate.
- Single session, single process, in memory. It is not meant to run for
  more than one test at a time, and it has no concept of more than one
  meeting.

## Known untested parts

The model, the word-count threshold, and the fallback cap are all guesses
stated as such in the design spec. This demo exists to test exactly that:
whether `gemma3:4b` is good enough at classification and extraction, and
what threshold values actually suit how people talk. Nobody has run it
against a real Ollama instance yet; it was built and syntax/logic-checked
in a sandbox without Ollama installed.
