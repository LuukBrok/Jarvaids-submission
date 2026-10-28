# Live photo reading: marked sticky notes to provisional notes (WP4)

`genai_server/claude_extractor.py` is the `Extractor` behind
`extraction.queue`. Until now the live path ran `FixtureExtractor`, which
answers "FIXTURE ONLY" for every region. With `--extractor claude` each region
a person marked on the photograph is read by Claude and comes back as one
provisional note on the review rail, with the photo and region it came from.

It is separate from the batch synthesis in [SYNTHESIS.md](SYNTHESIS.md), which
reads a whole wall after the meeting. The two share the model, the refusal
fallback and the rule that a guessed word is worse than a gap. Only this one
writes to a live session.

## How a photo becomes notes

1. A person uploads a photograph and drags one box around each sticky note
   (1 to 60 regions). The server stores the photo already oriented, with EXIF
   removed, as PNG (`media.sanitise`).
2. Extraction queues one job. The job runs in `IsolatedExtractor`'s child
   process, which is killed at the job's 60 second deadline.
3. The adapter crops every region (`media.crop`), scales each crop to at most
   1024 px on its long edge, and sends all crops in **one** call, each labelled
   with its region id. Structured outputs constrain the answer to one note per
   region: text, `readable` or `unreadable`, and a confidence.
4. Deterministic checks, in the adapter and again in the Service:
   - every region sent is answered exactly once, and no other region is invented;
     otherwise the job fails and nothing reaches the canvas;
   - a "readable" note with no text becomes `unreadable`, and an unreadable note
     carries no text, so it waits for a person to type it;
   - a confidence outside 0 to 1 is dropped, not clamped;
   - illegible words are written `[?]`, never guessed.
5. Each note becomes a `content` proposal with `origin: model`, the provider and
   the model that actually answered. Nothing is accepted until a person accepts
   it, and an unreadable one cannot be accepted until it is typed.

**Paper colour is measured, not asked.** It is the median of the crop's central
area, per channel, reported as `pixel_measured`. Ink is a minority of a note's
pixels, and the centre avoids background from a loosely drawn box. Lighting
still shifts it; the canvas says "measured from the photo", which is true.

## Running it

```sh
pip install -r app/server/requirements.txt -r app/server/requirements-claude.txt
# .env at the repository root, gitignored: ANTHROPIC_API_KEY=...
cd app/server
python -m genai_server --extractor claude
```

Through the localhost launcher: `python tools/local_test.py start --photo-reader claude`.
The default stays `fixture`, because this option sends data off the machine.
`--extractor-effort` is `low` by default, a guess to be measured against
`medium` on the same photographs.

The key is never in a GitHub secret (decision log, 13 October). CI runs these
tests with a fake client and no key.

## What leaves the machine with `--extractor claude`

- The marked regions only, as JPEG crops. Nothing outside a box is sent.
- Names or faces visible inside a box are not removed.
- No audio, transcript or session data.

## Cost

Each job reports its tokens, and a cost at list price for
`claude-opus-5-5` ($4 per million input tokens, $20 per million output, 18
October 2026). When the refusal fallback answers with another model, the cost
is reported as unknown rather than guessed.

## Verified, and not

Verified, 18 October 2026, Windows, Python 3.14:

- 19 tests in `tests/test_claude_extractor.py`, offline with a fake client,
  including one through the real `Service` job path; 9 of 9 guards caught by
  `tests/extractor_mutation_check.py`.
- **Real API, 13 real handwritten notes on three iPhone wall photos:** 12 of 13
  exact at `low` and at `medium`, character error rate 0.64%. The one miss is a
  note cut off by the photo's edge, read with `[?]` where letters leave the
  frame. 4 to 9 seconds per photo, about $0.03 for all 13 notes. Details and
  the baseline's weakness in
  [evaluation/test-cases/photo-reading-2026-10-18.md](../../evaluation/test-cases/photo-reading-2026-10-18.md).

- **Through the browser, by Pieter:** an iPhone wall photo (IMG_5818, MPO,
  3.4 MB) uploaded in Chrome, three notes marked, all three read correctly
  and shown as provisional notes "Read by claude". This exercised the client
  redrawing the photo as a PNG that fits the server's 4 MiB limit.
- The browser journey (`app/client/tests/journey.mjs`) drags a box past the
  photo's corner and requires it to stop at the edge.

**Not verified yet:**

- Dutch handwriting, and a photo with many more notes. A blind-typed baseline
  on new notes.
- Whether 60 regions finish inside the 60 second job deadline.

## Found on the way, and fixed

- A phone JPEG, and any iPhone MPO, was refused before it was read: the
  server keeps photos as PNG of at most 4 MiB and refuses multi-frame files.
  The client now redraws anything but a small PNG as a PNG that fits.
- A box dragged off the photo was refused by the server; boxes now stop at
  the edge.
- Every server error in the browser read only "refused": `describe()` looked
  for the code and message where `ApiError` does not keep them, and checked
  for an outcome name (`uncertain`) no client code produces (`unknown`).
- `/health` always said `live_ocr: false`, the startup line always said
  "Image adapter: fixture. No paid calls", and the photo panel said no
  handwriting recognition had run. All three now follow the configured reader.

## Not built

- **Finding the notes.** A person still marks each note by hand. A model step
  that proposes boxes, for a person to adjust, would remove most of that work.
- Duplicate detection against speech-derived notes (WP1/WP2).
