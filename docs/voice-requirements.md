# Voice requirements and wishes: phase two

Built on the published, user-tested to-do branch. Luuk reported the to-do trial
worked well and requested this next command on 19 October 2026. He subsequently
confirmed requirements and the command layout worked and requested phase three;
see [the calendar guide](voice-calendar.md) for its implementation and pending trial. Integration with
the newer main canvas remains a separate team step.

## Try it with your microphone

Use the same localhost launcher, Python setup and private `.env` as polling and
to-do lists. No additional installation or key is needed. Reload the client and
start a fresh session, agree to whole-meeting text interpretation, activate capture,
enrol speakers and press Listen. Existing sessions require renewed agreement when
the supported document types change; their stored content is retained.

Pause briefly between these sentences:

1. **The prototype must work offline.** No requirements list appears yet.
2. **We would prefer a green case.** This is a preference, rather than a must-have.
3. **Hey Jarvaids, make a list of requirements and wishes.** The canvas should
   show the earlier statements in Requirements and Wishes, with transcript evidence.
4. **People struggle to read the display.** The AI may propose a readability
   criterion under Needs clarification, labelled as an AI suggestion. It should
   not invent a font size, contrast ratio or other numerical target.
5. **Actually, a green case is a requirement.** The existing criterion should
   move sections, retaining its identity rather than appearing twice.
6. **The prototype must always use the cloud.** The offline and cloud criteria
   should both remain visible with the possible conflict flagged for review.
7. **Hey Jarvaids, close the requirements and wishes.** Continue discussing
   something else. Transcription, listening and other commands must keep working.
8. Review the conflict. Edit/remove the conflicting criterion as appropriate,
   then clear its conflict note after deciding. Review inferred suggestions and
   adjust their sections or wording as needed.
9. **Hey Jarvaids, accept the requirements and wishes.** This can happen now or
   later. Acceptance waits for pending/unclear interpretations and flagged conflicts.

Also try **Hey Jarvaids, reopen the requirements and wishes**, then **Hey Jarvaids,
cancel the requirements and wishes**. Jarvis is an accepted addressing variant.
You can say "requirements list" or "list of requirements" for lifecycle controls.
Bare conversation without direct address does not execute these commands.

## What the list means

- **Requirements:** explicitly stated criteria interpreted as must-haves.
- **Wishes:** explicitly stated preferences.
- **Needs clarification:** uncertain criteria, inferred suggestions and potential
  conflicts. AI inference stays here until a person reviews/reclassifies it.

All AI entries remain provisional until accepted. A stated criterion is an
interpretation of what was said, not proof everyone agreed. An accepted inferred
entry keeps its suggestion label; acceptance does not manufacture a statement
in the transcript. Conflicts retain both alternatives rather than choosing one.
Only human editing can clear an existing conflict note. Voice can edit,
reclassify or withdraw clearly identified criteria while collecting; ambiguous
references ask for clarification. Manual editing is available in Canvas and List.

Close stops collection for that document, while earlier queued work finishes.
Acceptance can wait without interrupting discussion, transcription or unrelated
commands. One collecting/reviewing document of each type can coexist with a poll.
A second document of the same type requires finishing or cancelling the first.
Accepted lists ignore ordinary speech until explicitly reopened; reopening scans
previously unprocessed speech, including the closed interval.

## Interfaces and safeguards

Use the existing authenticated, replay-protected, revision-checked `document.*`
operations from [the to-do guide](voice-todo-lists.md). `document.create` now also
accepts `document_type: "requirements"`. The shared entry-edit envelope keeps its
`task` field for compatibility, containing these four fields for criteria:

```json
{"text":"Work offline","category":"requirement","basis":"stated","conflict":""}
```

Categories are `requirement`, `wish`, `clarification`; basis is `stated` or
`inferred`. Criterion entries use `entry_type: "criterion"`; existing task fields
and poll interfaces retain their meanings. Generic records/history/sync/positions
are reused without a SQL schema migration. Snapshot `session.command_ai.types`
lists both supported document types. Policy records retain the agreed types.

The provider receives original whole-meeting transcript batches and existing list
entries, independently of the overview pipeline. Separate typed prompts/schemas
interpret tasks and criteria. Each collector ignores irrelevant content in model
interpretation; simultaneous collection can incur a call per collector per batch.
This is not a local semantic filter that guarantees zero calls for unrelated talk.
Audio, embeddings and credentials remain local. Existing bounded batches, queue,
entry limits, timeout and explicit retries apply across both document types.

The server checks current source IDs, verbatim quotes, stable entry IDs and stated
field evidence. It rejects unsupported digit/English number-word targets and forces
AI-inferred/conflicting criteria into Needs clarification. These checks cannot prove
semantic correctness, detect every conflict or recognise every written number/unit.
Human review and the microphone trial remain necessary. Errors and incomplete
coverage stay visible; no fabricated fallback or automatic paid retry is used.
Manual edits and source/capture order are checked before committing delayed output.

## Verification and integration

Run backend discovery, `tests/requirements_mutation_check.py`, the existing
document/poll mutations and `node app/client/tests/requirements-browser.mjs`, plus
the repository's required checks. Browser adapters are scripted doubles, with no
live speech/AI quality claim. Candidate results are in `app/server/BUILD-STATUS.md`.
Stop for Luuk's microphone trial before implementing the calendar.

Shared integration files are `documents.py`, `document_model.py`, `criteria.py`,
`voice_commands.py`, `service.py`, `documents.mjs`, `transcript.mjs`, the consent
text in `app.mjs`, and the small criterion CSS rules. Keep the newer main canvas
when combining branches; port these records, operations and render hooks into it.
Output-only note exports still do not include command documents. No real phone,
overlapping-speaker, latency or cost benchmark is established.

Follow-up trial report: Luuk reported the requirements list worked, then supplied
an unrecognised **Hey Jarvaids, let's make a voting list** transcript. Conversational
build framing is now accepted. The scripted browser journey explicitly creates
requirements, a to-do list and a poll in the same session and records a ballot.
This establishes coexistence; the phrasing repair still needs his live retest.

Canvas layout: unplaced command objects now appear beside each other with aligned
headings. Growing list content does not push the next command down. Automatic
focus keeps text readable; narrow screens focus the new command and let people
pan to its neighbours. Manually placed objects keep their saved coordinates. The
List view remains the linear alternative. Reload the page to load this UI change.
