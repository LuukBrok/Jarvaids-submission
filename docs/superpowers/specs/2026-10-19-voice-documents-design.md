# Voice command documents: approved phased design

Luuk approved the conversational plan on 19 October 2026 and requested its
implementation. Deliver the to-do list first, pause for his microphone trial,
then implement requirements/wishes, and finally the visual calendar. All three
use command-gated, provisional, editable canvas documents backed by original
whole-meeting transcript evidence, with live collection and explicit voice
closing, acceptance, reopening and cancellation. Generated meaning stays subject
to human review. No spoken responses are added.

Tasks distinguish suggestions from agreed actions and carry optional stated owner
and deadline plus completion. Clear personal completion can update a provisional
task; ambiguity asks for clarification. Unknown first-person speakers are never
assigned to the capture operator. Requirements later separate must-haves, wishes
and uncertain/inferred criteria without invented numerical thresholds. The calendar
later uses day/week/month/year views, stated dates and an unscheduled section;
tasks share identity with the to-do list rather than being copied.

Phase one adds generic documents, typed task entries, durable bounded work and
scope-aware agreement records using the existing store, sync, positions and
provider configuration. APIs and the live trial script are in
[the implementation guide](../../voice-todo-lists.md). Later document types are
deliberately not enabled. Keep this branch based on the tested poll version;
combining it with the newer main interface is a separate integration task.

Costs: whole-session text requires more provider processing than a short poll
window, continued collection adds calls, and semantic extraction still needs a
real group trial. Batches, queue depth, output size, retries and entry count are
bounded. Model calls run outside write transactions, with authority/evidence and
manual-edit checks before committing. Failure or incomplete coverage is visible.

Phase update, 19 October: Luuk reported that the to-do trial worked well and
authorised requirements/wishes. Phase two uses criterion entries with stated or
inferred basis, three sections and persistent conflict notes for human review.
Acceptance remains separate from capture and may wait until after discussion.
See [the phase-two guide](../../voice-requirements.md). Calendar remains deferred.
