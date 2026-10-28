# Combined localhost integration

For this checkout, follow [LOCAL-TEST.md](../../LOCAL-TEST.md). The full launcher
installs the optional engine alongside real speech and speaker matching; the
older standalone environment and training instructions below are historical.
Custom model weights remain a separate local package.

# Hey Jarvaids, F2.5 detection only

**Integration candidate, not a completed feature.** No custom model or human
microphone accuracy results are bundled. Missing, corrupt or incompatible assets
show "Wake word unavailable"; the application never substitutes Hey Jarvis.
See [training](wakeword-training/README.md) and [pilot](wakeword-training/PILOT.md).

## Run locally

Use Python 3.11 or 3.12 on Windows initially. Python 3.12 was used for the runtime
smoke check. Create the optional environment in a short directory, since deeply
nested Windows paths can exceed pip's path limit:

```powershell
py -3.12 -m venv C:\jv-wakeword-env
C:\jv-wakeword-env\Scripts\python.exe -m pip install -r requirements.txt -r requirements-wakeword.txt
C:\jv-wakeword-env\Scripts\python.exe -m genai_server --port 3000 --allow-origin http://127.0.0.1:5173 --wakeword-manifest .local/wakeword/model/manifest.json
```

Run these commands from `app/server`. First train/import the custom model as
described in [wakeword-training/README.md](wakeword-training/README.md). The
default threshold is an untuned 0.5; override with `--wakeword-threshold` only
with a recorded validation reason. No optional dependencies are imported unless
a configured detector is started. Omit `--wakeword-manifest` for normal existing
backend workflows. A detector failure does not disable typed/photo capture.

In another terminal, from `app/client`:

```powershell
py serve.py --port 5173
```

Open `http://127.0.0.1:5173/client/` in Chrome or Edge. Create a session, enrol
people using independent invitations, acknowledge the agreement and activate
capture. On Capture, the facilitator selects **Start microphone** and grants
browser permission. The same stream supplies transcription and the detector.
Anyone near the shared microphone may trigger it; this is not speaker identity
recognition. Keep both browser and backend on this laptop for local processing.

The dedicated audio demo is at `http://127.0.0.1:5173/server/demo-audio.html`.
It makes a single-facilitator test session and shows provisional transcript
segments. Its checkbox is not a substitute for independent group consent. The
default transcript adapter returns synthetic text, not recognised speech.

Say **Hey Jar-vaydz**. When a valid custom model recognises it, a short chime and
"Wake word detected" appear. The label lasts two seconds; the backend suppresses
new detections for three seconds. Browser autoplay refusal suppresses only sound.
Commands, additional command recording and board actions are absent.

## Lifecycle and resource bounds

- The AudioWorklet supplies continuous 20 ms Float32 mono frames at 16 kHz to
  both consumers. The existing transcription chunker still receives the same
  frame contract. Wake-word audio bypasses its speech/silence filtering, becomes
  PCM16 and is sent in 320 ms batches. ONNX processes four ordered 80 ms frames.
- Only one facilitator-owned stream is allowed per session, at most four across
  a backend. The registry and inference slots are bounded separately, so stopping
  an in-flight detector cannot create unlimited concurrent inference work.
- The browser sends one request at a time, keeps at most one second of queued
  audio including its partial batch, and times out a batch after one second.
  Interruption discards the queue and requires explicit restart. There is no
  automatic retry. Matching duplicate batches return the same detection ID.
- Streams expire after five seconds without a new batch, checked on access and
  by the existing maintenance loop. Browser detection IDs prevent repeated
  chimes, and generation counters discard late responses after stop.
- Pause, withdrawal, closure, deletion, actor removal/demotion, microphone end,
  hidden page and connection loss stop detection. Returning to a visible/online
  page requires explicit microphone start. Session authority is checked before
  and after inference. ONNX work runs outside database transactions.
- Wake-word audio, engine state and detections exist only in memory. They never
  enter transcript records, command history or exports. Normal transcription
  continues its existing source lifecycle independently. Stopping capture drops
  unsent transcription tails to avoid sending audio after withdrawal.
- ONNX inference is bounded in concurrency, not forcibly terminated mid-call.
  A stuck native runtime can occupy a slot until server restart; stopped streams
  cannot emit results. This limitation should be observed during the laptop pilot.

## Validation

From `app/server`, run the normal suite plus:

```sh
python -m unittest discover -s tests -p 'test_wakeword*.py'
python tests/wakeword_mutation_check.py
node --test --test-isolation=none tests/capture-audio-unit.mjs tests/capture-browser-unit.mjs tests/wakeword-unit.mjs
```

From `app/client`, after installing its existing Playwright development dependency:

```sh
node tests/wakeword-journey.mjs
```

`PYTHON` and `CHROMIUM_PATH` optionally select installed executables. The browser
journey deliberately uses a synthetic microphone and constant-score test server.
It establishes audio wiring and lifecycle, not pronunciation or accuracy. The
production server has no synthetic wake-word mode. Logs and screenshots remain
under `.local/`. [BUILD-STATUS.md](BUILD-STATUS.md) records measured checks and
platform limitations; [PILOT.md](wakeword-training/PILOT.md) records the missing
human evaluation separately.
