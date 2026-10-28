# Voice to-do lists: phase one

Implemented for Luuk's approved 19 October plan on `feature/voice-todo-lists`,
starting from the user-tested voice-poll version. Luuk reported a successful to-do
microphone trial. Phase two adds
[requirements and wishes](voice-requirements.md); the calendar remains recognition-only.
Integration with the newer main canvas remains a separate team task.

## Run and try

Use this checkout's Start Jarvaids.cmd. The existing speech runtime, optional AI
dependency and private repository-root .env from polling are reused. The launcher
passes `--command-ai auto`; no additional key or model installation is required
when the poll setup already works. Default direct backend CLI remains offline.

Start a fresh session, accept its agreement, activate capture, enrol speakers and
press Listen. When an existing session acquires whole-meeting interpretation,
it pauses and requires the updated agreement before capture resumes.

Pause briefly between these sentences and watch the canvas:

1. **Maybe we could interview students.** No list should appear yet.
2. **Hey Jarvaids, make a to-do list.** A collecting list should include that
   earlier idea as a suggested task with no invented owner or deadline.
3. **I will write the interview questions by Friday.** A second task should show
   the enrolled speaker as owner, Friday as deadline and an agreed-action label.
4. **Actually, the interview questions are due Monday.** The same task should
   change deadline rather than appearing twice.
5. **I have finished writing the interview questions.** The task should show
   provisional completion. A reported or ambiguous completion should not guess.
6. **Hey Jarvaids, close the to-do list.** Earlier queued speech finishes; new
   conversation stops changing this list.
7. Review/correct the entries, then **Hey Jarvaids, accept the to-do list.**
   Missing owner/deadline fields are allowed. Unresolved interpretations must be
   corrected by a follow-up, or excluded manually before acceptance.

**Hey Jarvaids, reopen the to-do list** resumes collection and retains the
previously accepted version. Reopening also scans speech not yet processed for
that list, including its closed interval. **Hey Jarvaids, cancel the to-do list** cancels it.
Jarvis is also an accepted direct-address spelling. Bare discussion such as
"maybe close it later" does not close a list. A repeated creation command refreshes
and focuses the existing collecting list rather than duplicating it.

Manual task editing, completion, removal, title editing, evidence, lifecycle
controls and explicit retries are also available in Canvas and List views. A
list can move without accepting it. Local unsaved fields/focus survive sync.

## Interpretation and review

The initial scan uses the original final, non-synthetic transcript from the whole
session, not an overview or the poll's two-minute look-back. Later chunks are
interpreted incrementally while collecting. Each bounded batch has at most 24
segments and 12000 transcript characters. A short preceding context helps resolve
references but cannot provide the only evidence for a live change.

The AI proposes supported tasks, stated assignments/deadlines and clear completion.
The backend owns stable task IDs, lifecycle, speaker attribution, persistence and
authority. First-person ownership requires a genuinely matched enrolled profile;
the microphone operator is never substituted. Named owners must occur in quoted
evidence. Deadlines retain the spoken wording; calendar date normalisation is
phase three. Suggested versus agreed is an interpretation, not proof of agreement.

Changes cite verbatim source quotes. The server validates quotes and required
field evidence, but cannot mechanically prove the AI's semantic reading. Everything
remains provisional until a person reviews it. A clear quoted follow-up can resolve
a prior clarification. Ambiguous references remain visible for manual correction.

Manual changes invalidate in-flight results and take priority over older queued
speech. Older captured changes cannot replace newer ones from the same recording.
Accepted lists ignore ordinary conversation until explicitly reopened. Shared task
records retain their accepted fields, preparing for calendar references later.

The separate text interpreter sends relevant original meeting text and task fields
to the existing provider. Audio, voice embeddings and credentials stay local.
Session agreement describes this broader text scope. `--command-ai off` disables
this path. To disable both cloud command paths use `--command-ai off --poll-ai off`.

## Interfaces and limits

`command_document`, `command_entry`, `command_work` and `command_policy` use the
existing records/versions store without an SQL schema migration. Documents contain
`document_type`, lifecycle state and shared `entry_ids`; phase one enabled
`todo`; phase two also enables `requirements` with typed criterion fields. Entries have type `task`, text, owner, deadline, suggested/agreed classification,
completion, removal state, evidence, origin and accepted-field history. Snapshots
and deltas include `session.command_ai` availability, enabled types and text scope.

All writes use the existing authenticated, replay-protected command envelope.
Except creation, document operations carry `document_id` and `expected_revision`.

| Operation | Additional fields |
|---|---|
| `document.create` | `document_type: "todo"`, optional `title` |
| `document.edit` | `title` |
| `document.refresh`, `.close`, `.reopen`, `.cancel` | none |
| `document.accept` | optional `acknowledge_incomplete: true` when coverage was excluded/missing |
| `document.entry.edit` | `entry_id` (empty to add), `task` with all five task fields, boolean `removed` |
| `document.resolve` | `work_id` to exclude an unresolved interpretation |
| `document.retry` | `work_id`, `acknowledge_unknown_cost: true` |

Lifecycle is collecting, reviewing, accepted or cancelled. Closure drains already
queued work. One to-do list can collect or be reviewed per session, alongside a
poll. `document_action` extends the existing `todo` recognition intent; poll
interfaces are preserved. `item.place` also accepts a command document.

The prototype bounds are 60 retained task entries, 120 work batches per session,
24 queued/inflight batches, three attempts per batch, 20-second provider timeout
and 4000 maximum output tokens per call. Limits are not measured cost/latency
guarantees. Usage available in decoded provider responses is retained even for discarded output.
No hidden SDK or restart retries occur. Failures and incomplete coverage remain
visible; explicitly acknowledge extra cost before retrying. After excluded work,
acceptance requires a separate incomplete-coverage acknowledgement on the canvas.

Lists, tasks and work follow normal session retention/deletion and persist across
server restarts and credential-based reconnects. Full browser reload still loses
the existing in-memory login. Output-only note exports do not yet include these
records. One shared microphone and the existing per-chunk speaker matching remain
the supported speech setup; overlapping-speaker accuracy is not established.

## Verification

Run backend discovery, `tests/document_mutation_check.py` and
`node app/client/tests/document-browser.mjs`, alongside the repository's required
checks. Browser speech, voice and AI responses are explicitly scripted doubles;
they verify wiring, not live model quality. Actual results and remaining limits
are recorded in app/server/BUILD-STATUS.md. The real microphone trial with Luuk is
complete according to his report; the requirements trial is the next gate before
calendar work.
