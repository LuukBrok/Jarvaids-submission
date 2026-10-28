# Voice polls on the localhost canvas

Implemented for WP3 from the plan approved by Luuk on 19 October 2026.
The browser and backend run on localhost. Audio transcription and enrolled-voice
matching stay local. Optional cloud interpretation receives recent transcript
text and opaque speaker IDs, never audio or voice embeddings.

## Team handoff for 20 October

Fetch and check out `feature/voice-polls` to run this independently tested WP3
version. Run setup from that checkout and supply your own repository-root `.env`
key. Credentials, recordings, session stores and custom acoustic model weights
are excluded from Git. Listen starts wake-word recognition automatically;
there is no additional detector checkbox. Without custom acoustic weights,
transcript-based addressed commands remain available.

On 19 October, Luuk reported that the real microphone voting trial went well
and confirmed that addressed voice closing worked. This is a user report,
not a measured multi-person accuracy or latency evaluation.

The branch is based on `ad0e17b` plus the shared team plan, before the newer
canvas, photo-reading and interface work on main (observed at `e762a5d`). It is
published separately for the planned joint integration. Do not replace the newer
client wholesale. Combine the poll rendering and Listen wiring with the current
canvas/app, retain both backend feature sets, and reconcile setup, CI, agreement
copy and documentation. Polls use session records without a schema migration.
After integration, repeat the full checks and a real group journey through
draft, confirmation, named choices, changed vote, voice closing and acceptance.

## Start and configure

Use this checkout's **Setup Jarvaids.cmd**, then **Start Jarvaids.cmd**. Setup
now includes the existing optional Claude dependency. The live launcher enables
poll interpretation when a key is configured. To-do execution is added separately
on `feature/voice-todo-lists`; see [its guide](voice-todo-lists.md).

Put `ANTHROPIC_API_KEY=your-key` in the repository-root `.env`, then restart.
Keep that file private and gitignored; never paste the key into a chat or browser
field. There is no key supplied with this implementation. Without one, a spoken
voting command still creates a visible draft with manual controls and a setup
message; it does not fabricate AI output. The optional `JARVAIDS_POLL_MODEL`
environment variable selects a different compatible provider model. Otherwise
the existing synthesis model setting is reused.

`python tools/local_test.py start --language en --poll-ai off` disables cloud
poll interpretation. Also pass `--command-ai off` to disable cloud to-do
interpretation on the to-do branch. The default backend CLI uses both flags off;
the live launcher explicitly selects `auto`. `--poll-ai claude` is an explicit
attempt to configure the same provider and shows a setup notice if unavailable.

Changing whether cloud interpretation is configured pauses existing active
sessions and advances their agreement version. Members acknowledge the updated
description before capture resumes. New sessions describe cloud use before
their initial agreement. This prevents an older local-only agreement being
silently reused after adding a key.

## Try it with the group

1. Create a session, agree, and start capture. Enrol the room's speakers, then
   press **Listen**. Use one shared microphone for this first version.
2. Discuss the question and choices: for example, salad, sandwiches or fries
   for lunch. Say **Hey Jarvaids, make a voting list**.
3. Check the provisional draft. Supply missing information by voice, or edit
   the question and one-choice-per-line field and choose **Save draft**.
4. Say **Yes, start voting**, or choose **Start voting**. The confirmation
   opens the poll and does not cast a ballot.
5. Say **Sandwiches for me**, **I vote fries**, or **option B**. A recognised
   enrolled voice receives one current choice. **Actually, salad instead**
   replaces the earlier choice. **Remove my vote** withdraws it.
6. Inspect replies requiring clarification. A clearly identified speaker can
   answer a clarification naturally. Otherwise assign the speaker and choice
   explicitly, or exclude the reply. Manual corrections identify the operator
   separately from the speaker they are acting for.
7. Say **Hey Jarvaids, close voting**, or choose **Close voting**. Earlier
   submitted replies finish processing. Resolve or exclude outstanding replies,
   then choose **Accept results**, or say **Hey Jarvaids, accept voting results**.
   **Hey Jarvaids, cancel the poll** cancels instead.

Only a recognised addressed command creates a poll. Earlier conversation can
supply its question/options, but is never backfilled as ballots. There is one
active draft/open poll and one selection per enrolled voice. Questions and
options are fixed once open; cancel and create another poll to change them.
Ties remain ties and nonvoters remain nonvoters. Accepted results are immutable.

Voice-inferred ballots and live tallies remain provisional until the team accepts
the results. Question and vote evidence can be expanded on the canvas. Polls
can be dragged without accepting them. They also have controls in the List view.
Session snapshots, reconnects with the existing credential and server restarts
retain poll records; the existing app still keeps login credentials in memory,
so a full page reload does not automatically log back into the session.

## Interfaces and runtime

`poll`, `poll_ballot`, `poll_work` and `poll_policy` are session-owned records in
the existing records/versions store. No SQL layout or schema-version change is
needed. Snapshots and deltas expose `session.poll_ai` with provider availability,
whether cloud text is enabled, and a safe configuration notice. Poll positions
use `item.place`; moving a poll never accepts its meaning.

All operations use the existing authenticated command envelope and normal
request replay protection. Poll operations require an active session, an editor
role and current agreement. All carry `poll_id` and `expected_revision`:

| Operation | Additional payload |
|---|---|
| `poll.edit` | `question`, `options` (2 to 12 unique labels) |
| `poll.confirm` | none |
| `poll.vote` | `speaker_profile_id`, `option_id` (null withdraws) |
| `poll.resolve` | `work_id`, `dismiss`; when assigning, also speaker and option |
| `poll.close`, `poll.finalise`, `poll.cancel` | none |
| `poll.retry` | `work_id`, `acknowledge_unknown_cost: true` |

The `voting` recognition intent has an optional `poll_action` for addressed
close, finalise and cancel requests. Recognition feedback is distinct from
actual poll state. Other command intents are unchanged.

A dedicated serial worker claims durable work, calls the provider outside the
database transaction, then rechecks session authority and the poll definition.
Repeated source delivery cannot create another poll or vote. Stale responses
cannot replace a human-edited definition; older captured replies cannot overwrite
later choices. Confirmation establishes the opening boundary. Closure drains
earlier work and prevents new ballots. Source and correction histories remain
in the existing version store and follow session deletion.

Interpretations have a constrained response shape and cite existing transcript
IDs. Ballots must quote the current utterance and choose an existing option.
The backend supplies voice identity and counts. Nonbinary draft choices must
appear in cited discussion; a person checks the inferred question before opening.
The model is instructed to distinguish personal votes from reported speech,
collective claims, hypotheticals and unrelated agreement. Those semantic
distinctions still require real-provider evaluation.

Creation uses up to 40 transcript segments from the preceding two minutes;
open voting uses the last four relevant segments plus the fixed question and
choices. No call depends on the meeting overview or the batch synthesis chain.
The default limits are 80 work records per session, 24 queued/inflight replies,
a 20-second provider timeout and 1600 maximum output tokens per request.
These are prototype bounds, not measured cost/latency guarantees. Usage and
actual returned provider/model are retained per interpretation. SDK retries
are disabled. Failure/timeout/restart uncertainty requires an explicit retry
acknowledging possible additional cost, or a manual correction/exclusion.

## Verification and remaining limits

Repeatable checks:

```sh
cd app/server
python -m unittest tests.test_polls
python tests/poll_mutation_check.py
node --test tests/poll-model-unit.mjs
cd ../client
node tests/poll-browser.mjs
```

The browser test runs the real HTTP, recognition, persistence, worker, canvas
and sync paths at 1440px and 400px using scripted speech/voice/AI test doubles.
It does not contact a cloud provider or prove real microphone/model accuracy.
Set `JARVAIDS_TEST_PYTHON` and `CHROMIUM_PATH` when the default executables are
unavailable. On Windows, use a short temporary source path for mutation runs
because nested SQLite paths can exceed Windows' path-length limit.

The current speaker pipeline identifies one voice per audio chunk and does not
separate overlapping speakers. Very short replies and quick turn changes need
a group microphone trial; unknown speakers are never assigned by the LLM.
Use longer clear replies or the manual controls when needed. One shared capture
operator is supported; voting from several simultaneous microphone devices,
multiple-choice ballots, simultaneous polls and spoken output are not included.
Existing exports cover notes and proposals; poll records are retained in the
session but are not yet included in those output-only export formats.

See `app/server/BUILD-STATUS.md` for this candidate's actual checks. No real
API call or human microphone trial is claimed without an explicit result there.
