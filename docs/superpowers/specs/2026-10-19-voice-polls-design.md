# Voice polls: approved design

Luuk approved the conversational plan on 19 October 2026, after selecting natural
voting with uncertainty review, confirmation of the initial draft, cloud AI with
the app hosted on localhost, one choice per speaker, and canvas-only feedback.

The original transcript is the source of evidence. A dedicated poll interpreter
uses the existing cloud provider configuration, independently of the overview
pipeline. Backend code owns poll state, enrolled-speaker attribution, ballot
replacement and totals. Generated interpretations stay visibly provisional until
human acceptance. Only a recognised voting command starts this workflow.

The lifecycle is draft, open, closing/review, then accepted or cancelled. Missing
questions/options and unclear choices prompt clarification. Unknown voices do
not enter a named tally. Earlier preferences are not retroactive ballots. A
confirmation never doubles as a ballot. The single active poll supports arbitrary
alternatives or Yes/No, one current choice per speaker, changes and withdrawal.
Close explicitly, drain earlier work, resolve or exclude uncertain replies, then
accept results together. Questions/options do not change after opening.

Implementation order: transactional records/manual controls; canvas poll;
recognised-command integration; background cloud interpretation; spoken ballots
and controls; replay/staleness/authority tests; desktop/mobile browser validation.
Reuse session persistence, positions, version history and synchronisation.

Acceptance includes command gating, drafting and confirmation, changes and
withdrawals, unknown/ambiguous replies, no duplicate delivery effects, stale
response rejection, persistence and accepted ties. Synthetic pipeline tests and
real-provider/group microphone evaluation are reported separately.

The detailed runtime, shared interfaces, reproduction steps and limits are in
`docs/voice-polls.md`. WP3 owns poll execution; WP1 shares AI configuration and
traceable transcripts; WP2 consumes poll state in the shared canvas. No other
voice-command execution feature is included in this package.
