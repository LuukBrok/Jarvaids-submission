> **27 October local integration:** use [TEST-THIS-VERSION.md](TEST-THIS-VERSION.md).
> The dated descriptions below are historical. Live summaries and the shared canvas
> bridge are now connected, with Pieter's newer interface/calendar branch included.

# Complete Jarvaids localhost trial, 20 October 2026

This release combines the latest shared canvas and real photo reader from main,
Luuk's polling/to-do/requirements/calendar branch, and access to Julie's existing
summary-to-sticky exploration. Rosalique's WP1 transcript-to-overview pipeline is
still missing, confirmed by Luuk on 20 October. This is a complete trial of the
available implementations, with unfinished paths identified below.

## Start on a Windows PC

1. Use this complete checkout, or download the latest main from GitHub after the
   integration pull request is merged. Extract the ZIP before running commands.
   Older folders such as Jarvaids-localhost and Jarvaids-combined are historical.
2. Install Python 3.12 if needed. Double-click **Setup Jarvaids.cmd** once.
   This installs the packages, CPU speech/speaker engines and Whisper Base.
   It needs internet; later transcription runs locally.
3. Keep the project API key in the private repository-root `.env`, as
   `ANTHROPIC_API_KEY=your-project-key`. The key, sessions and model weights are
   not supplied by GitHub. Reuse your existing private configuration locally.
4. Double-click **Start Jarvaids.cmd**. Both start launchers now enable the real
   photo reader and automatic workspace. Choosing a photograph sends its whole
   sanitised image to Anthropic to find/read the notes; command interpretation
   sends relevant meeting text. These are paid calls. Audio/profiles stay local.
5. No routine acceptance is needed. Typed notes, photo readings and command
   results appear automatically. Use Show details to correct a note. Existing
   valid notes waiting in the old queue are applied once on server restart.
6. Keep the launcher window open. It opens
   <http://127.0.0.1:5173/client/> after both servers are ready. Ctrl+C stops
   its servers. Occupied ports produce an error and are never killed for you.

The speech runtime lives in `%LOCALAPPDATA%\JarvaidsLiveTest`, outside long
OneDrive paths. Private session data and server logs are in `.local/live-test/`.
Existing data is retained. The acoustic wake-word detector also needs the group's
private trained model ZIP. Install it explicitly with
`py -3.12 tools/local_test.py setup --wakeword-package path/to/hey-jarvaids-model.zip`.
Without it, Listen still transcribes and recognises addressed transcript commands,
and the acoustic status explains its unavailability. Use a fresh session for this trial and check that its
Meeting time zone says `Europe/Amsterdam` before creating it.

To exercise local speech without any cloud interpretation:

```powershell
py -3.12 tools/local_test.py start --language en --poll-ai off --command-ai off --photo-reader fixture
```

Alternative ports are supported, for example `--api-port 3010 --client-port 5180`.
The opened URL selects that local API automatically. English is the command trial
language. `--language nl` selects Dutch ASR, but the addressed command patterns
remain English and Dutch handwriting quality has not been established.

## One meeting, all available features

Use fictional meeting content and notes you are willing to send to the configured
provider. Leave short pauses between spoken sentences and wait for processing.
One shared microphone and enrolled voices are the supported group setup.

| Step | Action | Expected result |
|---|---|---|
| 1. Start and agree | Enter a session name/time zone, Start session, tick agreement, Agree, Start capture | The agreement explains text interpretation; no capture before agreement. The state says Session open until Listen is actually on. |
| 2. Join another browser | In People create an invitation. Open the same local URL in a separate browser profile/private window and redeem it with another name; agree | Independent participant credentials and agreement. Renew agreement/start capture if the roster change pauses capture. This tests two local browsers, not a phone connection. |
| 3. Voice enrolment | In People record a four-second introduction for each person. Return to Listen | Transcript shows enrolled names when matched, otherwise Unknown speaker. Enrolment stops listening; restart it afterwards. |
| 4. Speech | Talk, pause and try silence. Say "Hey Jarvaids, make a summary" | Real words appear, silence creates no ordinary transcript row. The summary request is recognised but does not execute; original wording remains inspectable. |
| 5. Typed notes | Type a note | It appears immediately with no Accept step. Show details, edit and Save note. Undo the typed addition. Typed discussion also feeds active collectors; addressed typed commands execute. |
| 6. Photograph | Choose a phone photo of several notes | The sheet closes and detection/reading runs in the background. Each detected note appears separately with a source crop and AI reading label. No boxes or acceptance. Unreadable notes retain their image and can be corrected. Fixture mode explicitly says no OCR ran. |
| 7. Organise | Add several notes, drag, shift-select/group, move a note out/in, park/unpark an ungrouped note | New notes form a measured grid automatically; groups apply immediately. Placement/grouping is shared. Human placements are preserved. |
| 8. Draw/connect | Use Select (V), Draw (D), Erase (E), Connect (C), labelled connections, zoom and Fit (0) | Strokes/connectors become server records; erasing and supported undo work. Another local browser sees them. Arrow direction itself remains device-local. |
| 9. Quote/evidence | Quote a transcript line, inspect its timestamp, select a photo note to see source threads, scrub the bottom session strip | Quote returns to its source; visible origins get threads. Scrubbing filters/dims later events and returns to now on release. It does not restore old positions. |
| 10. Poll | Discuss salad/sandwiches/fries. "Hey Jarvaids, make a voting list"; each enrolled person votes; change/withdraw a vote; "Hey Jarvaids, close the voting list" | A usable question/choice set opens automatically. One current choice per identified voice; corrections replace earlier ballots. Closing drains queued replies and finishes the tally without acceptance. Unclear replies remain separate and are not counted. Ties stay ties. |
| 11. To-dos | Say "Maybe we could interview students", request a to-do list, then "I will prepare the interview questions by tomorrow". Correct the deadline and report completion | Earlier and ongoing discussion is collected automatically. Tasks show their text, owner and deadline; editing/evidence sit under Details. Close stops collection without acceptance. Reopen/cancel remain available. |
| 12. Requirements | Say "The prototype must work offline" and "We prefer a green case". Request requirements and wishes. Add an incompatible cloud requirement, then review/edit the conflict | Requirements, Wishes and Needs clarification remain separate. Inferred suggestions stay labelled; conflicts retain both alternatives until reviewed. |
| 13. Calendar | Say "The prototype review is tomorrow at 2 pm" and an event without a date. "Hey Jarvaids, make an agenda" | Prior discussion creates events; shared tasks keep the same IDs as to-dos. Undated or ambiguous entries remain Unscheduled. Try Day/Week/Month/Year, navigation and manual edits. |
| 14. Shared task updates | Keep to-dos/calendar collecting and change a task date or completion by voice | The same task updates in both tools without acceptance. Manual corrections and newer source ordering remain protected. Ambiguous dates remain visible as questions. |
| 15. Coexistence | Keep poll/to-do/requirements/calendar objects in one session; add enough tasks/voting options to make a long note; use List and inspect a second browser | Result cards show content first, with collapsed details. Cards grow with content and never scroll internally. Pan the canvas to reach the end of a long card. Form drafts/focus survive sync. |
| 16. Finish | Export JSON/Markdown, inspect their contents, pause/resume, end, then delete the disposable test session | Existing note/canvas exports work. Polls and command documents are currently omitted. Deletion removes the server session, not downloaded copies. |

General voice commands require direct address. Recognising Summarise, Visualise,
Compare or Suggestion does not execute them. The four working command types have
ten tested creation/lifecycle phrasings in `docs/COMMAND-PHRASES.md`. The older review-mode scripts remain in `docs/voice-polls.md`, `docs/voice-todo-lists.md`,
`docs/voice-requirements.md` and `docs/voice-calendar.md`.

## Julie's companion exploration

Open **Session > Summary-to-sticky prototype**, or
<http://127.0.0.1:5173/explorations/jarvaids-live-canvas/> while the launcher runs.
Try the project picker/search/new board, editing/dragging, connectors, undo,
uploads/PDF previews, and paste a fictional summary into the transcription rail.
It produces up to six titled notes, importance labels and compact placement.

This is the checked-in original exploration. It uses browser-memory state, its
AI-labelled controls do not call an LLM, and its created notes are not stored in
the main application's session. Reloading loses its board. PDF preview fetches
PDF.js from jsDelivr. The summary/overview bridge is still missing; do not present
this interaction demo as Rosalique's live overview pipeline.

## Existing batch photo/transcript synthesis

This separate CLI reads photographs and a Whisper-style transcript and produces
a provisional JSON/Markdown file. It extracts cited claims, reconciles points and
proposes structure. It does not populate the shared canvas. Read
`app/server/SYNTHESIS.md` for its format, data sent and cost limitations.

```powershell
# From the repository root; choose your existing input files.
$speechPython = "$env:LOCALAPPDATA\JarvaidsLiveTest\venv\Scripts\python.exe"
Push-Location app/server
& $speechPython -m genai_server.synthesis --photo path/to/wall.jpg --transcript path/to/meeting.json
# Explicit real-provider variant: add --provider claude.
Pop-Location
```

## Automated verification

The app itself needs no Node build. To run browser automation, install Node 24,
then run `npm install` and `npx playwright install chromium` inside `app/client`.
Run **Verify Jarvaids.cmd**, or select one suite:

```powershell
py -3.12 tools/verify_local.py backend
py -3.12 tools/verify_local.py guards
py -3.12 tools/verify_local.py contracts
py -3.12 tools/verify_local.py browser
```

Logs/results are in `.local/verification/`. Backend/guard checks use a short,
code-only temporary copy to avoid long Windows SQLite paths. No `.env`, private
sessions, recordings or model weights are copied. Browser checks run serially
because their ports are fixed. A skipped browser check is reported as failed,
never as a passing complete trial. Scripted speech/voice/model replies test
wiring and automatic/review behaviour; your real microphone and handwriting trial remains separate.

The repository's Bash design audit, schema/proposal checks and JavaScript
contrast/unit checks also remain in GitHub CI. Current executed results and
platform limitations are recorded in `app/server/BUILD-STATUS.md`.

## Remaining gaps

- WP1 live transcript-to-overview, and connecting that overview/synthesis or
  Julie's summary notes to the main shared canvas.
- Executing Summarise, Visualise, Compare and Suggestion.
- Exporting polls, to-dos, requirements and calendars in the output downloads.
- Photo/speech duplicate reconciliation and broad automatic-detection/OCR quality evaluation.
- Shared connector direction, fully server-backed transcript citations, historical
  position playback and automatic login recovery after a full browser reload.
- External calendar sync, PNG/PDF/Miro/FigJam exports and a compiled iOS client.
- Measured room/overlap accuracy, long-meeting behaviour, broad handwriting
  evaluation and a real group calendar trial on this combined release.
