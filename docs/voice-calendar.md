# Voice calendar: phase three

Luuk reported that requirements/wishes and the command columns worked, then
requested the agenda on 19 October 2026. This branch continues that tested
poll/to-do/requirements version. Integration with the newer main canvas remains
a separate team step. The agenda is a date-based calendar, rather than a list of
meeting topics. No external calendar account or synchronisation is involved.

## Microphone trial

Use the existing localhost launcher and private API-key configuration. Reload
the client, create a fresh session and check **Meeting time zone** is
`Europe/Amsterdam`. Agree, activate capture, enrol your voice and press Listen.
Existing sessions retain their content but need renewed agreement for the new
calendar interpretation capability. Windows time-zone data is installed by the
normal setup; this computer's live environment has also been updated.

Pause between sentences and wait for the processing indicator:

1. **I will prepare the interview questions by tomorrow.**
2. **Hey Jarvaids, make a to-do list.** Check your name and the spoken deadline.
3. **The prototype review is tomorrow at 2 pm.**
4. **We should hold a launch party, but we have not decided the date.**
5. **Hey Jarvaids, make an agenda.** It should retrieve the earlier discussion,
   place the review and linked task on tomorrow, and keep the party in Unscheduled.
6. **Actually, the prototype review is Friday at 3 pm.** The same event should
   move, rather than appear twice. Inspect its Calendar evidence.
7. **Hey Jarvaids, show week view.** Also try **show day view**, **show month
   view**, and **show year view**, plus the buttons and date navigation.
8. **The demo is next Friday.** Expect an unscheduled entry asking which Friday.
   Clarify with **The demo is on 30 October 2026**, adjusting the date if needed.
9. **Hey Jarvaids, close the agenda.** Continue talking and use another command
   before accepting. Capture and other collectors must continue.
10. Review and accept it manually, or say **Hey Jarvaids, accept the agenda**.
    Acceptance also confirms the displayed shared to-do task details, as the
    calendar's review notice explains.
11. **Hey Jarvaids, reopen the agenda.** Wait, then say **The interview questions
    are due Friday.** The accepted
    task should retain its old date until you accept the proposed task change.
12. **I have finished preparing the interview questions.** Review the proposed
    completion; the same task should become complete in both views.

Also try **Hey Jarvaids, make a calendar for next week** in a fresh calendar,
manual event editing, calendar dragging, List view and a narrow browser window.
Close, accept, reopen and cancel support agenda/calendar aliases and an addressed
wake phrase. A repeated creation while collecting focuses and refreshes the
existing calendar. Explicit acceptance is optional until you are ready to review.

Pause here for Luuk's real microphone trial. Scripted checks establish wiring
and guard behaviour, not recognition or model accuracy in a group meeting.

## Date interpretation and review

The AI reads bounded batches of original whole-meeting transcript, independently
of the overview pipeline. It proposes literal date/time phrases with source IDs
and quotations. Server code resolves dates against each chunk's captured UTC
instant and the session's IANA time zone. Legacy chunks fall back to their stored
transcript creation instant; their original recording instant cannot be recovered.
The browser supplies chunk-end wall-clock time alongside the existing monotonic
capture order. The device clock must be within five minutes of the session/server
clock; an invalid clock produces an explicit error before transcription.

Supported examples include today, tomorrow, in three days when transcribed as
`in 3 days`, Friday, Friday next week, 23 October 2026 and ISO dates. Relative
calendar periods include this/next week, month and year. Times support 24-hour
notation and AM/PM. Unsupported, invalid or ambiguous phrases remain unscheduled
and show a question. “Next Friday”, numeric slash dates, a past month/day without
a year, and “next week” without a day are deliberately not guessed. Give an exact
date or edit it manually. Dates are displayed for review before acceptance.

Day, week, month and year are local presentation choices. Previous, Next, Today,
date jumps, day buttons and month buttons never change stored event content.
Addressed view commands update the preferred focus and work after acceptance.
Delayed interpretation cannot undo a newer explicit view command or local
navigation. The year view summarises months and opens a chosen month; the other
views show date cells and the entries in that period. Unscheduled remains visible.
The calendar stays at readable zoom on the canvas; small screens can pan.

## Shared tasks and accepted meaning

Calendars reference the canonical `command_entry` task IDs already used by to-do
lists. Tasks created while a calendar collects attach automatically. Deadline,
completion, text and removal edits operate on that same record. Manual calendar
editing checks both document and task/event revisions. Calendar-only events have
their own IDs and do not create to-do tasks.

Accepting a calendar explicitly confirms its displayed linked task details.
Subsequent AI changes to accepted tasks create `command_task_change` records,
visible in both documents. Accepting or dismissing each proposal is explicit;
identical proposals from the two collectors share one review. A proposal based
on an older task revision cannot overwrite a newer edit. Pending proposals block
whole-document acceptance. Manual shared-task edits are explicit human actions;
an affected accepted document returns to review without resuming collection.
Reviewed shared-task updates propagate to accepted views without reopening them.
Previously accepted snapshots remain inspectable after reopening.

## Integration contract

No SQL schema migration: the existing record/version/event/sync store holds:

- `session_clock`: `{timezone}`; the session snapshot/delta also exposes timezone.
  Session creation optionally accepts timezone; omitted legacy clients use UTC.
- `command_document.document_type = calendar`: existing lifecycle fields plus
  timezone, task_ids, calendar_view, calendar_date, calendar_focus_revision and
  calendar_focus_origin. entry_ids contains calendar-only event IDs.
- `command_entry.entry_type = calendar_event`: text, date/date_phrase,
  time/time_phrase, done, clarification, status, source_refs and provenance.
- Canonical tasks add deadline_date, deadline_clarification, deadline_anchor and
  deadline_timezone; the original spoken deadline remains intact.
- `command_task_change`: task_id, document_id, base_revision, values, state,
  source_refs, provenance and creation/review metadata.

All operations use the existing authenticated, replay-safe command envelope:

- Existing `document.create` accepts type calendar; edit/refresh/close/accept/
  reopen/cancel/retry/resolve retain their interfaces.
- `calendar.entry.edit`: document_id, expected_revision, entry_id or task_id
  (the other is an empty string), value `{text,date,time,done,date_changed?}`,
  removed, and expected_entry_revision or expected_task_revision for existing
  entries. Shared tasks do not carry calendar-only event times.
- `calendar.task.resolve`: document_id, expected_revision, change_id,
  expected_change_revision, accept boolean.
- `calendar.view`: document_id, expected_revision, view and optional ISO date.

Voice recognition retains intent `planning` for compatibility and maps execution
to document type calendar. Transcript feedback distinguishes recognition and
execution. Poll interfaces stay compatible. Preserve positioning and the exact
record IDs when integrating with the newer canvas.

Provider safeguards, bounded history, consent, source validation, stale replies,
human corrections, durable work, explicit retries and capacity limits are shared
with the to-do and requirements collectors. Audio, voice embeddings and API keys
stay local; authorised transcript text goes to the configured provider. Keeping
several collectors active can add interpretation calls and cost.

Python's time-zone implementation needs system data or the bundled tzdata
dependency, particularly on Windows. See the primary documentation for
[zoneinfo](https://docs.python.org/3/library/zoneinfo.html) and
[tzdata](https://tzdata.python.org/). No time-zone data is fetched at runtime.
