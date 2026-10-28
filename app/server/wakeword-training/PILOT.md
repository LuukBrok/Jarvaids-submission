# Held-out microphone pilot

**Status: NOT RUN. The feature is not accepted.** There is no trained custom
model in this candidate and no human speech has been evaluated. Synthetic
browser checks and the reference runtime smoke check do not fill any cell below.

## Procedure

Record the commit, manifest/weights SHA-256, threshold, Windows version, browser
version, laptop and microphone, noise conditions and speaker distances. Start
with Chrome and Edge on Windows. Test each browser explicitly and identify
which trials belong to which browser; do not imply both passed from one result.

Obtain consent before opening the microphone. Use three anonymous speaker labels,
20 attempts each (10 close, 10 at approximately 1 to 2 metres), at least four
seconds apart. Say Hey Jar-vaydz naturally. Keep these recordings and consent
records under `evidence/raw/wakeword/`, outside Git and hosted training. Separate
training/tuning data from evaluation; if a result informs tuning, use fresh
held-out evaluation for the next candidate.

Measure visible-feedback time relative to the end of the phrase, using a local
screen/audio recording or observer timestamps. Record negative latency if
detection happens before completion, rather than silently clipping it. Count
one detection per attempt, misses, repeats and unintended triggers. Then run a
30-minute ordinary meeting sample including similar-sounding phrases; log each
false trigger and elapsed minutes. Record blocked chimes separately from misses.
Test mic unplugging, tab hide/return, pause and consent withdrawal as well.

Proposed acceptance: overall detection at least 90%, each speaker at least 80%,
visible feedback within one second of phrase completion for at least 90% of
detected attempts, and no unintended triggers in the 30-minute sample. These
targets are not promised accuracy or a statistically established deployment
false-positive rate.

## Results

| Measure | Chrome on Windows | Edge on Windows |
| --- | --- | --- |
| Custom model hash / threshold | Not available | Not available |
| Speaker A, detected / attempted | Not run | Not run |
| Speaker B, detected / attempted | Not run | Not run |
| Speaker C, detected / attempted | Not run | Not run |
| Overall detection | Not measured | Not measured |
| Detected attempts within 1 second | Not measured | Not measured |
| Latency distribution, median / p90 / max | Not measured | Not measured |
| False triggers / conversation minutes | Not measured | Not measured |
| Misses by distance / speaker | Not measured | Not measured |
| Chime and lifecycle checks | Not run with real mic | Not run |

Publish only anonymous aggregate results and non-identifying setup metadata.
Do not commit raw audio, transcripts, consent records or speaker identities.
