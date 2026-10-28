# Photo reading, first real run: 13 sticky notes, 18 October 2026

WP4. The first calls to the real API from the live photo path
(`genai_server/claude_extractor.py`), run through `tools/photo_reading_eval.py`,
which uses the same sanitise, crop and adapter code as the server.

## Material

Three iPhone photographs (4032 x 3024, MPO) of a real brainstorm wall from an
earlier, unrelated session. Real handwriting by several people, not written
for this test. 13 sticky notes marked by hand, as a person would in the canvas:

- 1 note alone on a wall (IMG_5816), 7 on a whiteboard (IMG_5817), 5 more
  (IMG_5818), two of which repeat notes from IMG_5817 photographed again.
- Four paper colours; marker, felt pen and one faint thin-pen note with a
  crossed-out word; two notes slanted; one cut off by the photograph's edge.
- Boxes drawn loosely, overlapping neighbours by a few percent.

The photographs and every reading stay in `evidence/raw/photo-reading/`
(gitignored); only totals and the one error are copied here.

## Baseline, and its weakness

Pieter, who knows the notes' content, judged each reading of the first run as
right or wrong and gave the correct text for the one he marked wrong. That is
the baseline for the scored runs. **It was set after seeing the model's output,
not typed blind**, so an error he did not notice would count as correct. A
blind-typed baseline on new notes is the stronger test.

## Results

| Run | Effort | Exact | Character error rate | Time, 3 photos | Cost at list price |
|---|---|---|---|---|---|
| 1, judged by Pieter | low | 12 of 13 | not scored | 13.4 s | $0.029 |
| 2 | low | 12 of 13 | 0.64% | 11.7 s | $0.029 |
| 3 | medium | 12 of 13 | 0.64% | 20.7 s | $0.039 |

Character error rate ignores case and spacing; punctuation and `[?]` count.
Every call was answered by `claude-opus-5-5`; no refusal fallback occurred.

**The one error** is the note cut off by the photograph's edge. All three runs
wrote `[?]` where letters leave the frame (`wher[?]` or `whe[?]` for "where",
`relationship[?]`) rather than completing the words. Pieter's verdict: a
human-review fix, and the same note is fully visible in IMG_5817, where it was
read exactly.

**Uncertainty is visible where it should be.** The lowest confidence (0.60) was
the faint thin-pen note, whose crossed-out last word became `[?]`; the
cut-off note scored 0.70; clear marker notes 0.85 to 0.95.

Spelling was copied, not corrected ("dont", "a app"), and the two notes
photographed twice were read identically apart from capitals.

## Decisions it supports

- **Effort stays `low`.** Medium gave the identical score at 1.8 times the time
  and 1.35 times the cost.
- **The 4 MiB stored-photo limit is not the bottleneck yet.** Photos shrink to
  about 1500 x 2000 px to fit as PNG, leaving each note about 330 px wide, and
  that was enough here, including the faint pen. Revisit if a wider wall shot
  gives smaller notes.

## What this does not show

- Accuracy on handwriting the model has not seen in a similar setting, on
  Dutch notes (all 13 were English), or on a photo with 30 or more notes.
- Whether correcting the output beats retyping, timed with a person; here one
  of 13 notes needed a correction.
- The browser path with these photos; this ran the server's code directly.
