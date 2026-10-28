# Voice repairs and fictional MP3 trial, 27 October 2026

The visible Chrome trial uses the supplied 30-minute repair-cafe MP3 and
twelve-note wall photograph. A digital audio stream replaces the microphone
only inside the automated test window. Physical laptop-microphone and room
acoustics are not established by this route. The independent observer has its
own browser context and membership and never starts a microphone.

Speech recognition and voice embeddings run locally. Summaries, photograph
reading and document/poll interpretation use the cloud configuration Luuk
explicitly approved. The local summary-model download is still incomplete.

## Repairs

- Reject very quiet keyword-detector input and reset its model state. The
  installed model otherwise scored quiet random noise around 0.997, so raising
  the keyword threshold alone did not solve the false activations.
- Chime only once for a newly confirmed, final, non-synthetic spoken activation.
  Replayed snapshots, typed commands, continuations and delayed results after
  Stop listening do not chime. Acoustic candidates alone do not chime.
- Start enrolment timing after the microphone graph is ready, capture six
  seconds, reject insufficient speech, and replace a same-named profile rather
  than accumulating competing copies. Preserve existing other profiles.
- Use timestamped speech words and voice windows to keep multiple speakers in
  one capture chunk separate. Preserve uncertain attribution as Unknown.
- Supply the product name as ASR vocabulary and recognise the narrow spellings
  actually observed in this trial. Preserve the raw ASR text and avoid fuzzy
  matching arbitrary people. Keep connected spelled-name tokens together.
- Correct the summary-command feedback so a configured summariser points to
  Overview progress. This wording requires a newly loaded client; the existing
  long-running test window retains its initially loaded JavaScript.

## Observed results

| Check | Result | Evidence or limit |
| --- | --- | --- |
| Independent observer | PASS | Separate context, own invitation and membership |
| Four voice enrolments | PASS | Original MP3 introductions through the enrolment controls |
| Initial discussion names | PASS with limit | All four names; three short fragments remained Unknown |
| Quiet keyword input | PASS for sampled noise | 96 seconds across silence and quiet-noise samples; no detections after gate |
| ASR quiet input | PASS for sampled noise | Silence and three noise levels produced no text with the name hint |
| Suggestions and visualisation | Recognition recovered | Generation is not implemented; not a generation pass |
| Comparison | Recognition observed | Generation is not implemented |
| Summary | PASS | Persisted topics, Overview entries and linked canvas notes; cloud provider |
| Whole-wall photograph | PASS | 12/12 real readings, correct wording including negation; original crops retained |
| Source crop | PASS | Electrical-repairs crop inspected against the original photograph |
| Note edit/restore and typed-note undo | PASS via API | Operator-injected edit recorded separately from correct original OCR |
| Group, membership, park/unpark, stroke erase/undo, connector | PASS via API | Reversible shared-state operations; gesture coverage is separate |
| Requirements conflict | PASS | Both conflicting proposals retained before withdrawal |
| Furniture promotion and QR withdrawal | PASS | Model promoted furniture and marked mandatory QR removed |
| Requirements acceptance | PASS after operator steps | Operator cleared retained conflict; two failed batches passed one explicit retry each |
| Automatic poll definition | FAIL | ASR split pop-up and heard cart as card; evidence validation rejected choices |
| Poll definition recovery | Operator action | Three stated choices corrected and confirmed before any ballot |
| Initial voice ballots | PASS | Four model-origin ballots, expected 2/1/1 tally |
| Vote change and withdrawal | PASS | Expected 3/0/0 intermediate tally |
| Final voice ballots | PASS | Roselique, Julie, Luuk: pop-up; Pieter: cart; expected 3/1/0, closed |
| Tasks and calendar | Automatic misses; operator recovery | Owned commitments found; ASR dates and one duplicated sub-step required correction. Original records and failures retained |
| Reopen/accept lifecycle | IDs retained; review required | Incomplete coverage blocked voice acceptance. Operator reviewed and acknowledged exclusions. The initial three-accepted-document precondition at P32 was not met; no clean all-voice accepted/reopen pass is claimed |
| Disposable cancellation | Three lists passed; poll repaired | Separate list IDs cancelled without changing main documents. Final poll creation required typed recovery; poll/pole/pool cancellation passed an actual audio-API replay after repair |
| Final session | Closed and retained | Read-only capture refusal verified; no deletion performed |

The test preserves original failures. Replaying after a repair, correcting a
poll definition or reviewing a conflict does not retroactively pass the
original automatic result. The operator actions are automated test operations,
not a claim of line-by-line human review by a teammate.

Private checkpoint snapshots, screenshots and operator records are under
`.local/watch-test/`. Credentials remain in its private session file and are
excluded from reports. JSON and Markdown product exports have known omissions
for polls and command documents; retained snapshots supplement those exports.

## Regression checks

The final broad backend run passed 638 checks with two skips. Subsequent focused verification passed 58 voice/poll/continuation checks and 14 summary/export checks after their final repairs. Six JavaScript wake/feedback checks passed. Earlier sandbox and temporary-location failures were rerun with localhost access and an ignored private temporary directory. Logs are retained in `.local/verification/`.

The sampled fictional voices, non-overlapping playback and noise probes do not
establish overlapping-human diarisation or arbitrary room performance.

## Finished run

The recording reached 29:59. Playback and browser capture were stopped. All 48/48 persisted summary batches completed, including the final typed settings check. This establishes processing and persistence, not a complete semantic audit of every summary sentence.

The final session is **closed**. The 3 main documents remain accepted. 3 separate documents and 1 separate poll are cancelled. The primary concept poll remains closed.

| Speaker | Final option | Ballot origin |
| --- | --- | --- |
| Roselique | Pop-up repair cafe | model |
| Pieter | Mobile repair cart | model |
| Julie | Pop-up repair cafe | model |
| Luuk | Pop-up repair cafe | model |

The full captured transcript contains 49 Unknown-speaker rows out of 310 final spoken rows, including short boundary fragments and replayed verification clips. The four-name and ballot checks must not be read as perfect word-by-word attribution.

| Post-playback check | Observed result |
| --- | --- |
| Disable automatic summaries | PASS |
| Re-enable and addressed typed summary | PASS |
| Manual summary text preserved | PASS |
| Same-topic manual overwrite exercise | NOT RUN |
| Manual note placement retained | PASS |
| Summary-to-sticky bridge | PASS |
| JSON and Markdown exports | PASS |
| Edited summary heading in JSON | PASS |
| Edited summary heading in Markdown | FAIL; repaired live export PASS afterwards |
| End session | PASS |
| Read-only capture after ending | PASS |
| Manual UI-only coverage | NOT RUN |

JSON and Markdown were inspected and saved. The Markdown heading omission was repaired and the live export was repeated. Both files now retain the manual heading. Product exports still omit polls and command documents; the complete private final snapshot supplements them. Source media are not bundled.

The live same-topic manual-overwrite exercise was not established because the model updated another topic; the dedicated same-topic regression passed. API canvas checks do not establish drag/keyboard gestures or observer edit-focus behaviour. Physical laptop microphone, room acoustics, overlapping humans and other listed manual-only checks remain NOT RUN.

The local date parser now accepts explicit forms such as “the 6th of November, 2026”. This does not repair dates that ASR transcribed incorrectly. Day-view and some poll phrases were also misheard. General visualisation, comparison and suggestion generation remain unimplemented. The calendar still has no event end-time field. These are remaining prototype limits.

## Topic layout and showcase

Luuk approved the five-theme presentation after the completed trial. The client now lays out 41 current cards in compact, labelled colour groups, measures expanded details, and retains original photograph colours in source details. Free layout preserves saved positions and drawings. The ended session was not reactivated or rewritten.

The showcase is in `evidence/raw/Jarvaids-showcase-20261027/`: ten authentic screenshots, unchanged MP3/photo/instructions, readable transcript and summary, portable grouped canvas, document/poll exports, sanitised full snapshot, provenance reports and SHA-256 manifest. Screenshots of the updated UI show the existing final state, including operator recoveries. They do not retroactively pass the original automatic misses.

Layout verification passed 117 focused client checks, the summary browser journey at 1440 and 400 pixels, and actual completed-session checks at 1920 and 400 pixels. Collapsed cards did not overlap, the full saved records and positions stayed identical, and view actions sent no mutation requests. Expanded source crops reserve their loaded dimensions.
