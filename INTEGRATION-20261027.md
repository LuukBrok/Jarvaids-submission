# Jarvaids local integration, 27 October 2026

This is the complete local test folder. Nothing was pushed or merged remotely.
Private settings were reused locally without exposing their values. Existing
project folders and session stores were preserved. Raw field materials were
excluded from this source snapshot.

## Included team work

| Source | Revision | Included contribution |
| --- | --- | --- |
| Shared main | `f9dfe15f1e8ec7c75c353b6461906f06398ccd8f` | Current shared app, real speech/speakers, wall photographs, command tools, canvas and persistence |
| Rosalique's latest Notulator branch | `8a4c49ed49e76295868a40377a4cc1444826251c` | Two-level theme/topic design, two-call model prompts and original standalone demo |
| Earlier notulation package | `0b66594138494688915d06c32fe949e7dc6f052f` | Preserved batch pipeline and local/cloud adapters, separately tested |
| Julie's summary bridge | `0f39548cd7dd61df9afa4adca4938bff4a087727` | Summary-to-sticky conversion and shared-session publication; companion exploration retained |
| Pieter's interface refinements | `4f6096874545c113ef2243aa8c98693449cad1cc` | Sticky-note appearance, command menu, collection indicators, calendar views, date chips and note/calendar links |
| Additional WP1 exploration | `60b4e468d6afa53941854695e365767237a1d744` | Original transcript-overview exploration preserved under ideation |

The new integration connects live transcript records to a persisted, ordered
summary queue. Structured topics retain timestamped visits and source references.
Summary and extracted claims must cite exact current transcript quotations.
Topic summaries become canvas notes through Julie's bridge. Updates preserve
manual note corrections, deletion and placement. The overview remains readable
independently of a manually edited canvas heading.

Agenda topics, an explicit flush, status, failed-batch retry and a Summary menu
action are available in the UI. Cloud/local provider changes renew agreement.
Summary note exports contain their full detail. Existing command-document and
poll export omissions remain recorded in the trial guide.

## Verification completed on this Windows PC

- Full backend: 633 tests, passing with two existing platform skips.
- JavaScript: 338 tests, all passing.
- HTTP client journey, populated-board sync budget, schema registry and proposal
  coverage checks: passing.
- All 21 browser journeys passed, including the rail-navigation retest. The
  summary journey exercised desktop and 400px layouts, checked no console errors,
  failed requests or horizontal body overflow, and its screenshots were inspected.
- Earlier batch notulation package: 36 tests passing.
- New summary mutation harness: all four named mutants caught by assertions.
- Existing media, isolation, schema, runtime, synthesis, extractor, client, poll,
  document, requirements, calendar and automatic-workspace mutation harnesses:
  passing on this combination.
- The service mutation harness initially found an ambiguous mutation anchor
  after integration added another reference validator. Its anchor was narrowed
  to the original validator. The completed rerun passed all 113 named guards.
- Real local Whisper recognition of a locally generated fictional spoken sample
  produced two transcript segments. The real cloud summariser produced a topic
  and a positioned summary note in the running shared session. This verifies the
  connected flow, not human-room accuracy or usefulness.
- A separate real cloud extraction of fictional text produced a decision, action
  and open question in approximately 33 seconds, with matching source quotes.
- Final combined scenario: the same persisted session contains one generated
  summary note from real local speech recognition and three notes from the real
  photo reader. The photograph was a locally generated fictional sticky-note
  wall. This checks audio, summaries and photo input together; it is not a
  handwriting-quality evaluation. Result: `.local/combined-audio-photo-smoke.json`.

Logs and screenshots are private under `.local/verification`, `.local/summary-ui`
and `.local/real-integration-smoke.json`. They include fictional test material;
the smoke-result file also contains its disposable session credential.

## Limits and unavailable checks

The selected Gemma 3 4B model's download ended with connection resets and is incomplete. Completed chunks were retained for resumption. Local inference is not verified. The running app uses the explicitly approved cloud alternative; local audio and voice profiles remain local.

The legacy design-system contrast script cannot run from this snapshot because
its old `app/design-system/tokens.css` input is absent. Bash is unavailable for
the shell audit. The current client contrast/unit checks passed, but those are
not substitutes for claiming the unavailable legacy checks passed.

Automatic approval review later failed because the approval service reported an
account usage limit. The blocked final browser-check invocation did not execute.
A final provenance-label wording fix and the stop helper were subsequently saved
as workspace edits. Both passed syntax checks without network access; a fresh
browser rerun of that wording change is not claimed here.

## Later verification, 27 October

The visible fictional MP3 and wall-photo trial is now complete. See [the voice repair and test report](VOICE-AND-MP3-TEST-20261027.md) for verified fixes, original failures, operator recoveries and untested manual coverage. All 48 summary batches completed, three main documents remain accepted, separate cancellation fixtures were retained, and both exports were saved. The test session is closed and readable. The localhost servers remain running. The local summary-model download is still incomplete; this run used the approved cloud configuration. The earlier approval/check failures above remain historical observations, not the final test status.

## Tutor handoff and source publication

The three local tutor links and restart instructions are in TUTOR-DEMO.md.
The original Notulator standalone experiment is preserved under
`ideation/explorations/notulator-demo/`, next to the other explorations; it is
separate from the integrated product and keeps its original UI and requirements.
The private archive builder is retained in tools. Source publication excludes
recordings, raw transcript/snapshot files, credentials and the local runtime.
The existing feature checkout and its uncommitted packaging work were preserved;
publication was prepared from current GitHub main in an isolated checkout.
