> **27 October local integration:** use [TEST-THIS-VERSION.md](TEST-THIS-VERSION.md).
> The dated descriptions below are historical. Live summaries and the shared canvas
> bridge are now connected, with Pieter's newer interface/calendar branch included.

# Integrated localhost feature inventory, 20 October 2026

Run [COMPLETE-LOCAL-TEST.md](COMPLETE-LOCAL-TEST.md) for the full PC/group trial.
This release combines main's shared canvas/photo reading and Luuk's voice-calendar
branch. The PC launcher now applies inputs automatically, detects whole-wall notes,
and uses growing result cards with collapsed details. See [the phrase catalogue](docs/COMMAND-PHRASES.md).
Julie's checked-in exploration is served as a separate companion.

| Feature | Current integrated behaviour | Limit |
|---|---|---|
| Sessions/people | Invitations, independent joining, roles, agreement, capture lifecycle, retention/deletion | Local browsers verified; a real phone/LAN journey is separate |
| Current workspace | Latest design, Canvas/List, review/transcript/people, projector mode | Windows browser prototype |
| Notes | Immediate typed/photo notes, automatic source labels, editing, details and supported undo | Legacy review mode remains available outside the PC launcher |
| Canvas | Pan/zoom/fit, placement, grouping, Place new notes, parked shelf, pen/eraser/connectors | Arrow direction is device-local; some object kinds have API/rendering support without dedicated creation controls |
| Evidence | Photo crops, confidence/colour, transcript quote notes, provenance threads, session strip | Quote links have local storage; strip does not replay position history |
| Speech | Real local Whisper, silence filter, sentence rows, activation correction with original wording | Group/overlap accuracy unmeasured; English command patterns |
| Speakers | Real local Resemblyzer enrolment and matching; Unknown speaker | One shared microphone, no overlapping-voice separation |
| Acoustic wake word | Starts with Listen when configured; visible state and chime | Requires private custom weights; transcript commands work without them |
| Real photo reading, Pieter/WP4 | Whole-wall detection and transcription to separate notes, validated source crops, confidence and measured colour | Whole sanitised photo goes to configured cloud reader; private key/paid API; accuracy needs room evaluation |
| Polls, Luuk/WP3 | Automatic opening, single-choice ballots per voice, changes/withdrawal, clarification, automatic finish on close | Unidentified/ambiguous replies are excluded from tally and remain inspectable |
| To-dos, Luuk/WP3 | Whole-meeting and typed discussion, automatic collection, owners/deadlines/completion, editing and lifecycle | Cloud text interpretation needs a configured key |
| Requirements/wishes, Luuk/WP3 | Automatic sections, inference labels, conflicts, evidence and corrections | Conflicts stay visible; automatic application does not prove semantic correctness |
| Calendar, Luuk/WP3 | Day/week/month/year, date resolution, unscheduled events, shared task IDs and automatic updates | Real group microphone trial pending; no external calendar sync |
| Summary/visualise/compare/suggestion commands | Recognised with explicit feedback | Executors missing |
| Julie/WP2 exploration | Summary to up to six titled notes, compact placement and directional relationships; original project/edit/upload/PDF demo | Separate browser-memory board, no LLM call or main-session bridge |
| Batch synthesis | Existing photo/transcript CLI, real provider or labelled fixture, provisional JSON/Markdown | Does not write the shared canvas |
| Rosalique/WP1 | Missing, confirmed by Luuk | No live transcript-to-overview pipeline |
| Export | Existing JSON/Markdown outputs and source-reference disclosure | Polls/command documents omitted; no PNG/PDF/Miro/FigJam export |
| Runtime | Readiness/diagnostics, shared sync, saved positions, server restart/reconnect with credentials | Full browser reload loses in-memory login |
| iOS | Retained source | Never compiled; outside Windows trial |

No credentials, models, recordings, voice profiles or session databases are supplied
through GitHub. Automated journeys use scripted adapters and synthetic pictures;
they establish integration, not live AI or room quality.
