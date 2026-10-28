# Jarvaids

Jarvaids supports design meetings by bringing spoken discussion, photographs of
physical sticky notes and typed input into one shared visual workspace. It makes
topic summaries and supports polls, tasks, requirements and calendar entries.
Participants can inspect source evidence, correct interpretations and organise
the canvas while the meeting is happening.

**IDEM307 Generative AI and Design, TU Delft, 2026-27**

**Team:** Julie van Veelen, Luuk Brok, Pieter Borst and Roselique van den Brink

**Source submission:** 28 October 2026

## Start here

- [Assessor guide](SUBMISSION.md): setup, source map and limitations.
- [Integration record](INTEGRATION-20261027.md): contributions and source revisions.
- [Trial findings](VOICE-AND-MP3-TEST-20261027.md): failures, operator recoveries
  and verification limits.
- [System flowchart](deliverables/documentation/flowchart.md): wider design proposal;
  planned functions here are not all implemented.
- [AI use log](decisions/ai-use-log.md) and [decision log](decisions/decision-log.md):
  development choices and AI assistance.

This repository contains source and configuration. The final report, demo video
and portable saved demonstration are separate hand-in artefacts. Localhost links
in older guides refer to a running installation on the reader's computer. They
are not hosted demonstrations.

## Run on Windows

The full speech runtime was exercised on Windows with **Python 3.12**. Use a
current desktop browser and allow microphone access when prompted. First setup
needs internet access and downloads Python dependencies and speech model files.

1. Download and extract this repository, or clone it. Open its root folder.
2. Install Python 3.12 if needed, then double-click **Setup Jarvaids.cmd**.
3. Copy `.env.example` to `.env`. For cloud summaries, photograph reading and
   command interpretation, supply your own `ANTHROPIC_API_KEY`. Keep `.env`
   private. Provider calls can incur charges.
4. Double-click **Start Jarvaids.cmd** and keep its window open. The client opens
   at <http://127.0.0.1:5173/client/> after startup.
5. Start a session, review the capture agreement, agree and start capture. Use
   **People** to enrol speakers, then press **Listen**. Try a spoken discussion,
   **Jarvaids > Summary**, and **Photograph the wall**.
6. Inspect and correct results, and try the command menu. Stop the services with
   **Stop Jarvaids.cmd** or Ctrl+C in the launcher.

Speech transcription and enrolled voice profiles stay local. Cloud features send
relevant transcript/context or sanitised photograph pixels to the configured
provider. Metadata removal does not remove names visible in a photograph. The
session agreement reports the selected processing configuration.

Custom acoustic wake-word weights are not bundled. Transcript-based addressed
commands and the command menu remain available without that optional detector.
Local summary inference needs a separate model installation and was not verified
in the final trial; the demonstrated summary path used the approved cloud option.
Without the configured services, the source remains inspectable but the full AI
demonstration is not available. See [the detailed trial guide](TEST-THIS-VERSION.md)
for behaviour and commands. Its references to an existing runtime apply to the
original demonstration laptop, not a new installation.

## Implemented functions and limits

- Browser client, Python API and persistent shared session/canvas store.
- Local speech transcription and speaker enrolment/matching.
- Persistent topic summaries with source quotations and summary-to-canvas notes.
- Automatic whole-wall photograph reading and editable canvas results.
- Polls, to-dos, requirements/wishes and calendar collection from discussion.
- Canvas drawing, connectors, grouping, parking, correction and export.

The final integration was exercised with a fictional spoken recording and wall
photograph. This checks the connected flow, not accuracy in a real meeting.
Visualisation, comparison and suggestion requests remain conceptual. Overlapping
voices are not separated. Polls and command documents are missing from the older
output-only export. The iOS client is uncompiled. See the dated findings for the
full limits and manual recoveries.

## Source map

| Path | Contents |
| --- | --- |
| `app/client/` | Browser workspace, controls, canvas and client tests |
| `app/server/` | API, persistence, processing adapters and backend tests |
| `tools/` | Setup, launch, verification and local archive helpers |
| `prompts/` | Prompt/context material; live instructions also occur in server adapters |
| `docs/` | Feature guides and design specifications |
| `deliverables/documentation/` | Architecture and process documentation |
| `ideation/`, `evaluation/`, `decisions/` | Explorations, evaluation and development records |

## Provenance and privacy

This is a fresh-history source snapshot of the team's integrated commit
`198eddceb10096805ad8e10a1186bc7086486657` in
[the team development repository](https://github.com/ptborst/GenAI).
See [SOURCE-PROVENANCE.md](SOURCE-PROVENANCE.md) for its preparation record.

Credentials, recordings, identifying research transcripts, consent records,
session databases, installed runtimes and original development Git history are
excluded. Do not add these when reproducing a demonstration. Dated development
records describe earlier states; this README and the assessor guide describe
the submission entry point.
