# Complete Jarvaids PC test, 27 October 2026

Open http://127.0.0.1:5173/client/ while the launcher is running.

## Start and stop

- Double-click **Start Jarvaids.cmd** in this folder. Your existing speech,
  speaker and wake-word runtime is reused; no setup is needed on this PC.
- Choose Start session, Agree, Start capture and Listen. Allow microphone access.
- Double-click **Stop Jarvaids.cmd** to stop this folder's launcher and servers.
  Ctrl+C in a normally launched test's launcher window also works.
- Restart from this folder, not the older Jarvaids-combined or Jarvaids-localhost folders.
- Your private key is in the ignored `.env`. Sessions and logs are in `.local/live-test`.

## What is connected

1. Real local Whisper speech, speaker enrolment/matching and the installed wake word.
2. Rosalique's two-level topic design: broad themes, specific topics, summaries,
   decisions, action items and open questions, with timestamped transcript evidence.
3. Julie's summary-to-sticky bridge, writing to the same persistent canvas as photos.
   Opening a summary note shows its detail. Moving/editing a note is preserved.
4. Pieter's latest unmerged interface work: sticky-note presentation, Jarvaids command
   menu, collecting indicators, calendar view, date chips and note/calendar links,
   alongside the existing real whole-wall photo reader.
5. Polls, to-dos, requirements/wishes and calendar collection from original discussion.
   Drawing, connectors, grouping, parking, editing, provenance, undo and export remain.

## A five-minute trial

1. Start capture. Use People to enrol voices, then press Listen again.
2. Say: "We agreed the prototype must work offline. Alex will test it tomorrow.
   We still need to decide how to recruit participants."
3. Say "Hey Jarvaids, make a summary", or use **Jarvaids > Summary**.
   The Overview tab and the canvas should update after processing. For a short
   discussion, **Overview > Update summary now** flushes the waiting words.
4. Open a topic to inspect its evidence. Open its canvas note to see the detail.
   Change the heading, drag it, then discuss the topic again: your heading and
   position remain while the structured overview continues updating.
5. Use **Jarvaids > To-do list**, **Poll**, **Requirements and wishes** and
   **Calendar**. Each uses original transcript evidence, not an abbreviated summary.
6. Choose **Photograph the wall** and select a photograph. Detection/reading runs
   automatically. Inspect source crops and correct any reading errors.
7. Try the Canvas/List/Calendar views, drawing, grouping and parking.
8. Export the meeting. Summary notes include their full detail in Markdown/JSON.
   Polls and command documents retain their existing export limitation (see below).

## Summary providers and waiting

Luuk explicitly approved the temporary cloud-summary option on 27 October.
The running test uses Anthropic with the existing project key. Transcript text
and previous topic context leave this PC; audio and voice profiles stay local.
The agreement and summary status disclose the configured provider. This can incur
API charges. No automatic retry is made after an uncertain or failed model call.

The default launcher selects local Gemma when its verified model installation is
complete, otherwise the authorised cloud alternative. To select explicitly:

```powershell
py -3.12 tools/local_test.py start --language en --summary-ai claude
py -3.12 tools/local_test.py start --language en --summary-ai ollama
```

The portable local runtime/model are under `.local/ollama`. The first model download ended with connection resets and remains incomplete. Completed chunks were retained. The cloud option is available now; local Gemma inference is not yet verified.

The provisional automatic batch settings are 60 words and the next sentence end,
with a 100-word fallback for missing punctuation. These are starting settings,
not measured accuracy/latency claims. Short final fragments wait for Update summary
now or an addressed summary request. Failed work blocks later batches for that
meeting until an explicit Retry; original transcript records remain.

## Scope and honest limits

- Visualisation, comparison and suggestions remain recognised requests without
  generative execution. Their menu entries say so.
- Polls and command documents are not included by the older output-only export.
  The live session does store them. Summary note detail is included by this build.
- Voice matching does not separate overlapping voices. AI interpretations need
  human inspection; exact-quote checks do not prove semantic correctness.
- Localhost verifies this PC. Phone/LAN use and the iOS client are separate.
- This is a local integration snapshot. Nothing was pushed to GitHub.

See INTEGRATION-20261027.md for branch revisions and verification evidence.

Completed fictional-trial results, voice repairs and remaining limits: [VOICE-AND-MP3-TEST-20261027.md](VOICE-AND-MP3-TEST-20261027.md).
