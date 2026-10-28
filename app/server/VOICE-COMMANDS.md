# Supported voice commands

Say **Hey Jarvaids** before any of these phrases. Known transcription spellings
such as Jarvates and Jarvite are also accepted. A lead-in sentence can come
before the addressed request.

You can add **please**, **can you**, **could you**, **would you**, **will you**,
**we would like you to**, **briefly**, **quickly**, or a trailing **please**,
**thanks** or **thank you**. Combinations such as **could you please** work.

These are tested examples of broader phrase patterns, not a fixed exact-phrase
whitelist or unrestricted semantic classification. Original words stay visible.
Requests remain provisional. Voting now creates a canvas poll and can interpret
spoken choices when the optional cloud AI is configured. To-do commands now
create a collecting list from original whole-meeting evidence; see
[the to-do guide](../../docs/voice-todo-lists.md) for exact lifecycle commands and
verification limits. Requirements/wishes, calendar and other commands still
recognise requests without executing them. See [the poll guide](../../docs/voice-polls.md).
Keep one request per utterance. Negated, deferred and compound requests are
refused. Existing same-microphone, five-second continuation rules still apply.
Recognised requests show a green Command badge.

## Summary

- Make a summary.
- Summarise this.
- Summarize our discussion.
- Give us a summary.
- Give me a quick recap.
- Sum up what we discussed.
- Tell us the main points.
- Create a short overview of this meeting.

## Visualisation

- Make a visualisation.
- Visualize this.
- Visualise these ideas.
- Show this visually.
- Turn our discussion into a diagram.
- Create a visual overview.
- Draw a diagram of these ideas.
- Help us picture this.

## Comparison

- Make a comparison.
- Compare these ideas.
- Compare these two options.
- Show us the differences.
- Show us the similarities.
- Give us a side-by-side comparison.
- What are the differences between these concepts?
- Compare the pros and cons of these options.

## Voting

After creating a draft, check its question and choices and say **Yes, start
voting**, or confirm on the canvas. Subsequent ballots need no activation phrase.
Use **Hey Jarvaids, close voting**, then **Hey Jarvaids, accept voting results**
after reviewing outstanding replies. **Hey Jarvaids, cancel the poll** cancels it.
These lifecycle requests remain part of the voting intent, with `poll_action`
metadata, and do not create a second poll.

- Make a voting list.
- We want to vote.
- Let's vote.
- Set up a poll.
- Create a list we can vote on.
- Start a vote on these ideas.
- Help us vote on these options.
- Prepare these concepts for voting.

## Suggestions

- Give me a suggestion.
- Give us a few suggestions.
- Make a suggestion.
- Suggest something.
- Suggest some ideas.
- Do you have any suggestions?
- What would you suggest?
- Give us some options to consider.

## To-do list

- Make a to-do list.
- Create a task list.
- List our action items.
- What do we need to do next?
- Turn this into a to-do list.
- Give us a list of next steps.
- List the tasks we still need to complete.
- Make an action list for our team.

## Requirements or wishes

- Make a list of requirements.
- List our requirements.
- Make a list of wishes.
- Create a wish list.
- List our requirements and wishes.
- What requirements have we discussed?
- Give us a list of must-haves.
- Collect our wishes into a list.

## Agenda, planning or schedule

- Make an agenda.
- Make a planning.
- Create a schedule.
- Plan our next meeting.
- Make a timeline for our project.
- Give us an agenda for this session.
- Organise our next steps into a plan.
- Create a plan for the coming week.

## Requirements and wishes execution

Requirements commands now create a provisional three-section document from original
whole-meeting speech, separately from the overview. See [the trial and API guide](../../docs/voice-requirements.md).
Addressed close, accept, reopen, cancel and refresh controls target the requirements
list independently of a to-do list or poll. Acceptance may wait while capture continues.

## Conversational build framing

Addressed build requests also accept "let's", "let us" and ASR's unpunctuated
"lets", for example **Hey Jarvaids, let's make a voting list** and **Hey Jarvaids,
let's make a to-do list**. The original transcript is preserved. Existing
**Hey Jarvaids, let's vote** still works. Direct address is still required;
negated, deferred and compound requests do not execute one arbitrarily chosen action.
Polling, to-do and requirements are enabled together in one session; testing the
features in phases is a development process rather than an execution restriction.
