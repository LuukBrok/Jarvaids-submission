# Copy

UI language is **English**. Sentence case. Verb-first buttons.

## Switching to Dutch

The team is Dutch-speaking and the meetings this tool sits in will be held
partly in Dutch (F1.2 explicitly expects Dutch and English in the same
sentence). The repository is written in English throughout, so the UI is
English for consistency with everything around it.

**If the team decides to switch the interface to Dutch, that is a change to
this one file, not to the design system.** Change the language rule below, keep
every other rule: sentence case still holds, buttons become Dutch infinitives
(Accepteren, Afwijzen, Exporteren), status words stay single words, and the
number and date formats become `nl-NL`. Nothing in `tokens.css`, `grid.css` or
any other spec file assumes English.

Transcript content is a separate matter and is never translated. It is a record
of what was said, in the language it was said in.

## Rules

- **Sentence case everywhere**, labels included. Nothing is uppercased, in the
  source or in CSS: a 12px uppercase label loses its word shapes at distance
  and some screen readers spell it out letter by letter.
- **Buttons are verbs, and the verb comes first**: Accept, Reject, Edit, Start
  session, Pause capture, End session, Export canvas, Add note. Cancel is always "Cancel".
- **Status words are single words** where the language allows: Recording,
  Proposed, Accepted, Queued, Unreadable, Paused, Ended. A person's typed note
  that the room has not looked at yet says "Not yet reviewed": three words,
  because no single word says it without implying a verdict.
- **Meta lines use interpuncts**: `6 present · 2 not yet agreed`,
  `Sanne · 14:22`.
- **Pluralise properly**: `1 item` / `4 items`. Never `item(s)`.
- **Times are 24-hour** (`14:22`), durations are `M:SS` or `H:MM:SS`. Dates are
  `15 September 2026`. Every numeral is set as a figure: weight 500, tabular.
- **No exclamation marks. No emoji. No "please".**
- **British spelling**: organise, colour, recognise, behaviour.
- **No em dashes.** Use a comma, a colon, or the word "and".

## Words this product has settled on

Listed so they do not get relitigated in code review.

| Use | Not | Why |
|---|---|---|
| Proposed | Provisional, Draft, Pending, AI-generated, Suggested | It names who acts next: the model put it forward and the room decides. It is a word a facilitator can say out loud ("three proposed notes"), which "provisional" is not. "Draft" implies the model will finish it. `provisional` stays as the name of the state in tokens and code, so `--color-status-provisional` draws the word "Proposed". |
| Not yet reviewed | Pending, Unconfirmed, Draft | A person's own typed note before the room has looked at it. It is not model output, so it never says "Proposed". |
| Accept | Approve, Confirm, Keep | Accepting is taking ownership, which is what is happening. |
| Reject | Delete, Discard, Dismiss | The item is kept in the record (F6.5). "Delete" would be a lie. |
| Recording | Live, On air, Active | It is a consent word. It must be the plain one. |
| Capture | Recording (as a noun) | The verb for what the tool does to the room, covering audio and photographs. |
| Session | Meeting, Workshop | The meeting is the thing in the room; the session is the record of it. |
| Canvas | Board, Whiteboard | "Board" is taken by Miro and FigJam, which are export destinations (F5.3). |
| Item / Sticky note | Card, Sticky | Item is the general data term; Sticky note names the expandable main-point presentation (F3.8). Structural labels and connectors remain other items. |
| Gap | Silence, Missing, Error | A stretch that could not be transcribed. Neutral and accurate. |
| Unreadable | Failed, Error, Low confidence | The handwriting could not be read. Says what happened. |
| Catching up | Processing, Loading, Please wait | Says the model is behind, not that the user should wait. |
| Quiet mode / Active mode | Passive / Proactive | Plain words the facilitator can say out loud to the room. |

## Tone

Plain and factual. The interface is a colleague in the room, not a product
being sold.

- **Say what happens next**, not what happened. "Audio is deleted when the
  session ends" beats "Retention policy applied".
- **State what still works when something breaks**, in the same sentence:
  "Transcription has stopped. Audio is still being recorded."
- **Never apologise and never enthuse.** Not "Sorry, something went wrong" and
  not "Great, all done".
- **The model speaks in the first person only when it is answering a question**
  ("I cannot find that in this session"). Everywhere else the interface speaks
  about the model in the third person, or not at all. A status chip does not
  say "I'm still thinking".
- **Never claim certainty the model does not have.** If a speaker attribution
  is a guess, the copy says "Unknown speaker", not a name.

## Empty states

One sentence, naming the next action. Examples:

- Review queue: "Nothing waiting. Everything on the canvas has been accepted."
- Transcript, before capture: "Nothing yet. Capture starts once everyone has
  agreed."
- Canvas, empty: "Photograph the wall, or type a note, to put the first item
  here."
- Export, nothing selected: "Choose what to include."

F3.8 disclosure controls: Show details, Hide details. No-content state: No
further detail. Unavailable citation: Source unavailable. A collapsed proposed
note offers Review, not Accept, because its supporting detail is still hidden.
