# Tutor demonstration, Wednesday 28 October 2026

Double-click **Open Tutor Demo.cmd** after restarting the PC. It starts or
reuses the installed localhost services and opens these three tabs:

1. [Completed repair-cafe test](http://127.0.0.1:5174/completed/).
   The actual client, connected to the retained, closed session. This link is
   read-only and does not expose the owner credential. Its live session is
   retained until **28 October at 13:50 Europe/Amsterdam**. The saved showcase
   remains usable after that time.
2. [Inputs, outputs and screenshot showcase](http://127.0.0.1:5174/showcase/).
   The local HTML archive with ten screenshots, original inputs and exports.
3. [Fresh working tool](http://127.0.0.1:5173/client/).
   An empty start screen, separate from the completed session. Enter a session
   name, choose the retention period, Start session, agree and Start capture.
   Enrol each speaker with a six-second sample in People, then press Listen.
   The microphone remains off until you enrol a voice or press Listen. Upload
   a wall photograph using Photograph the wall. Live microphone input is used;
   the earlier automated MP3 feed is not installed in this tab.

Keep the demo launcher running while using the links. A URL cannot start a
stopped local server by itself. Do not shut down or delete the retained session
before the tutor visit. The fresh tab creates a different meeting, with no old
voice profiles, transcript, notes, tasks or polls.

The current PC configuration uses local speech recognition and voice embeddings,
and the previously approved cloud summary, photo and command interpretation.
The launcher explicitly keeps that tested summary provider for this demonstration.
It does not claim that the incomplete local Gemma download is usable. The fresh
session agreement shows which data can go to the configured provider.

`tools/tutor_demo.py` serves only the public client files and local showcase,
binds only to loopback, restricts completed-session reads to its configured
session and refuses all mutation methods. The owner token stays in
`.local/watch-test/private-session.json`, which is ignored by Git. The saved
showcase and raw test inputs remain under ignored `evidence/raw/`; they are not
part of a public source push. On another PC, create that machine's own session
and runtime setup rather than copying credentials.

See [the full trial report](VOICE-AND-MP3-TEST-20261027.md) for original recognition
misses, operator corrections and checks not performed. A fresh classroom session
uses the same prototype and is not a guarantee of flawless speech recognition.

## Verification before the tutor visit

The three links were exercised at 1440 and 400 pixels. The completed test
reconnected after reload, with five groups and 41 cards. The showcase exposed
its ten screenshots and the fresh tab opened the blank start screen. A separate
disposable meeting was created, agreed, activated and used to add a real note;
it was then deleted. No microphone request occurred. Five local reader boundary
tests passed, including write refusal, private path refusal, session isolation
and absence of the owner credential from HTML.

The final integrated backend run passed 639 tests with two existing skips, and
all 344 JavaScript unit tests passed. The design-system audit passed. These
checks do not establish physical classroom acoustics or perfect voice matching.

The archive builder is retained as `tools/package_repair_cafe_showcase.mjs`.
Run it from the source root with `--inputs` pointing to the original input
folder and `--before` to the original before-layout screenshot. It uses the
ignored `.local/watch-test` evidence and writes the ignored `evidence/raw`
archive. It does not add those files to Git.
