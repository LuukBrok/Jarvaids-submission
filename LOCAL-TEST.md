> **27 October local integration:** use [TEST-THIS-VERSION.md](TEST-THIS-VERSION.md).
> The dated descriptions below are historical. Live summaries and the shared canvas
> bridge are now connected, with Pieter's newer interface/calendar branch included.

# Integrated localhost launcher

The complete current trial is [COMPLETE-LOCAL-TEST.md](COMPLETE-LOCAL-TEST.md).
Use that checklist for the combined canvas, real photo reading, speech, polls,
to-dos, requirements and calendar. Rosalique's overview pipeline is still missing.
Julie has a separate local companion exploration, linked from the Session menu.

Windows: run **Setup Jarvaids.cmd** once, then **Start Jarvaids.cmd**.
Both launchers enable automatic workspace mode and real photo reading. Choosing
a photo sends its whole sanitised image to Anthropic to find/read the notes; they
are added automatically. This needs the private project API key. Select
`--photo-reader fixture` explicitly for the offline synthetic path.
Command interpretation uses the existing optional key and the session agreement.

## Windows

1. Install Python 3.12 from python.org. The full speaker runtime requires
   Python 3.12+; the Windows commands select the tested 3.12 installation.
2. Download or clone the repository's `main` branch and extract it to a folder.
3. Double-click **Setup Jarvaids.cmd** once. Internet is required to install
   packages and download Whisper Base. No account or API key is required.
4. Double-click **Start Jarvaids.cmd**. It opens
   <http://127.0.0.1:5173/client/> once both servers are ready.
5. Choose **Start session**, tick **I agree to this session being recorded**,
   press **Agree**, then **Start capture**, then **Listen** in the bar. Allow the
   browser to use your microphone. The Windows start command uses English
   for the current command patterns. Speak, then pause briefly.

Open **Speakers** after starting capture. Each person enters their name and
records a four-second introduction. Then press **Listen**. The full launcher
enables real local Resemblyzer voice matching, with two CPU threads. Matched
chunks display the enrolled name; uncertain matches say **Unknown speaker**.
Listening pauses during enrolment and resumes only when you press Listen.
This is per-chunk voice matching, not separation of overlapping speakers.

Recognised words appear in Transcript. Natural pauses up to one second remain
in the same audio chunk. Consecutive unfinished fragments from the same voice
join into a sentence row until punctuation; speaker changes stay separate.
Observed activation spellings display as **Hey Jarvaids**, with the original
ASR wording available in the correction disclosure. Silence and brief noise do not create
rows. Genuine processing failures appear as one status notice. The energy
filter is a simple heuristic; Whisper is fallible and its output needs review.

Keep the start window open. Press Ctrl+C there to stop both servers. The launcher
refuses occupied ports; it does not kill another project's processes.

The runtime and downloaded model live under `%LOCALAPPDATA%\JarvaidsLiveTest`,
outside long OneDrive paths. This avoids the Windows path-length failure found
while installing ONNX Runtime. Local session data and logs live in
`.local/live-test/`, which is ignored by Git. Model weights, recordings and
credentials are not committed.

Setup also installs CPU-only PyTorch and the speaker encoder. A Windows
`webrtcvad-wheels` build provides the module used by Resemblyzer without
requiring a C++ compiler; its older package metadata still names `webrtcvad`,
so pip may warn about that dependency name. The actual embedding path was
tested. Use the setup helper rather than installing the old optional
requirements file directly.

PyAV is pinned to 16.1.0 because 19.0.1 is incompatible with the
`metadata_errors` argument used by faster-whisper 1.2.1. Once installed,
transcription runs locally without sending audio to a cloud provider.

## Terminal and other platforms

```sh
python tools/local_test.py setup
python tools/local_test.py start
# For English instead:
python tools/local_test.py start --language en
```

Use `python3` if that is your Python command. Linux/macOS use a runtime under
the user's cache directory. They have not been verified for this launcher.
`--runtime-dir` selects a different installation directory. `--no-browser`
starts the servers without opening a browser. Custom `--api-port` and
`--client-port` values are supported; enter the custom API address in the
session setup form when changing the API port.

## What can be tested

- Real local Dutch transcription, with silence omitted.
- Speaker enrolment, real voice matching and explicit unknown-speaker labels.
- Typed notes, photo intake, human review, grouping, canvas arrangement and
  export. Photo reading is synthetic by default; see below for real reading.
- Voice-command recognition in the backend. Recognition is provisional;
  the Transcript panel shows a provisional command badge, its request type
  and the latest recognition message. Incomplete and unsupported requests
  have their own feedback. The original transcript stays visible.
  Polls, to-dos, requirements/wishes and calendar requests execute on the canvas.
  Summary, visualise, compare and suggestion remain recognition-only.

The command patterns currently use English: for example, "Hey Jarvaids, make
a summary" or "Hey Jarvaids, let's vote". To test English speech reliably,
start with `python tools/local_test.py start --language en`. A name or unfinished
request can continue in the next audio chunk from the same recording within
five seconds. Stopping/restarting Listen starts a fresh recognition window.

Automatic general notes and summaries remain missing. Requested to-do lists
collect action items; requirements and calendars use their own collectors.
See COMPLETE-LOCAL-TEST.md for the combined trial.
Photograph extraction uses synthetic test output unless you opt in to Claude:
put `ANTHROPIC_API_KEY=...` in `.env` at the repository root and start with
`python tools/local_test.py start --photo-reader claude`. Press **Photograph
the wall** in the bar, mark each sticky note, then send it; every note comes
back proposed, and an
unreadable one waits for you to type it. This sends the marked regions to
Anthropic. See [app/server/PHOTO-READING.md](app/server/PHOTO-READING.md).
Run setup again once if your runtime predates this option, so the `anthropic`
package is installed. The iOS client is outside this browser test.

For an existing local session store, --data-dir selects its directory. The launcher still defaults to the ignored .local/live-test folder.

Known direct-address ASR spellings, including Jarvan's and Jarveds, display as Hey Jarvaids. The activation phrase corrected disclosure shows the original wording. Only the activation phrase is normalised; the rest of the sentence and stored ASR text stay unchanged. Uncertain sounds and mentions inside a sentence are not rewritten.

## Optional acoustic wake-word test

The separate trained-model detector is now integrated alongside transcript
recognition. Install your existing local model package with:

```sh
python tools/local_test.py setup --wakeword-package path/to/hey-jarvaids-model.zip
```

Then start normally and press **Listen**. The configured detector starts
automatically, without an additional checkbox. The same microphone feeds both paths. Detection gives
a short chime and two-second indicator; it does not authorise a command.
No separate stream of audio is sent to a cloud service. If no model is
installed, transcript command recognition still works and the optional
detector reports its unavailability. `--wakeword-manifest` can select an
existing local manifest. Package paths and hashes are checked before installation.

Custom weights remain local and are not redistributed in this repository;
the supplied candidate manifest records pending redistribution clearance.
The user's installed candidate runs through the local API, but its human
accuracy and false-positive rate have not been verified. Other groupmates
need the corresponding model package to exercise this optional path.

See [LOCAL-FEATURES.md](LOCAL-FEATURES.md) for the integrated feature inventory.
