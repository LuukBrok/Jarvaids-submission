# Local API and integration contract

## Automatic workspace configuration, 20 October 2026

`--automatic-workspace` is enabled by the PC launcher; the low-level Service and
fixture CLI retain review mode for compatibility. Snapshot/delta session metadata
contains `automatic_workspace: true` when enabled. Automatically applied items
retain the existing settled `status: accepted` storage state and add
`automatic: true, applied_by: system`. They never acquire a fabricated
`accepted_by`/`reviewed_by` identity. JSON exports retain these fields and Markdown
says `automatically_applied`. The author/source/model remain inspectable.

`source.image` now accepts omitted `regions`. This stores `detect_notes: true`
and queues whole-wall detection. Adapters receive an empty region tuple and must
return up to 60 unique `region_id` values with validated normalised `box` values,
text/status and existing provenance. Completion stores detected regions on the
source in a new revision and uses that revision in every resulting note/job ref.
Manual nonempty regions preserve the old crop protocol. No extra schema migration
is needed. Empty-wall results are valid; unreadable notes retain an editable gap.

In automatic mode `source.text` stores the original human text and a segment marked
`input_method: typed`. Ordinary text adds a canvas note and feeds active collectors.
Addressed recognised commands execute without adding a redundant command sticky.
Typed inputs never establish a voice-identified voter. A usable generated poll
opens immediately; close drains queued work then finishes without human acceptance.
Unclear replies remain inspectable and are excluded from tallies. Lists display
additions immediately; close stops collection without requiring acceptance.

On startup, valid pending content from review mode is applied once without another
provider call. Changed references, changed policies, removed authors and capacity
failures remain unresolved. Each application emits an event for connected clients.
Capture agreement, source revision checks and membership controls remain in force.


**To-do document extension, 19 October:** `session.command_ai` describes the
available command interpreter, enabled document types and whole-meeting text
scope. `document.*` operations and `command_document`/`command_entry`/`command_work`
records add to-do collection, editing, evidence and review without changing poll
interfaces or the SQL schema. See [the payload contract and lifecycle](../../docs/voice-todo-lists.md).
`item.place` accepts a `command_document`. Requirements/wishes and calendar
execution are now enabled by the later phases; see their contracts below.

Base URL: `http://127.0.0.1:3000`. JSON only for writes. Session requests require `Authorization: Bearer <actor token>`, except creation and invitation redemption. Loopback is the default. Explicit LAN binding uses `--bind 0.0.0.0 --advertise-host <host-ip> --allow-origin http://<client-host>:<port>`. Host and Origin checks remain exact. HTTP does not encrypt credentials; public deployment remains outside this prototype.

## Identity and retries

Generate a fresh cryptographically random session ID and actor token in the client. IDs/request IDs are 8–80 URL-safe alphanumeric, underscore or hyphen characters; tokens are 32–128 such characters. `client.mjs` generates 32 random bytes for a token. Never put tokens in URLs or logs.

Session creation is retried with the same ID, credential and creation fields. For commands, generate an `X-Request-ID` **once per user intent**, retain the exact operation/payload and reuse all three after an uncertain network result. A reused key with different content fails with `idempotency_conflict`. A fresh action needs a fresh key. Do not automatically retry an HTTP 409 with a new revision: that would bypass renewed human review.

Command responses have `{result, replayed, seq}`. Records have `{id, kind, revision, data}`. References are `{id, revision}` and must point to current sources or current accepted items in the same session. Historical revisions are available for inspection, not as valid dependencies for a new acceptance.

## Routes

| Method/path | Result or input |
| --- | --- |
| `GET /health` | Service/adapter status; `live_ocr` is true when a real photo reader is configured (`--extractor claude`), false for the fixture |
| `POST /api/sessions` | `{session_id, owner_token, owner_name, title, retention_seconds?}`; returns session/actor IDs and state |
| `POST /api/sessions/{sid}/join` | `{invitation, token, name, policy_version}`; participant supplies its own credential |
| `GET /api/sessions/{sid}` | `{session, actor_id, members, records, board_order}`; deleted session returns receipt to retained facilitator credential |
| `GET /api/sessions/{sid}?since_seq=N` | Only records changed after cursor `N`, or `resync_required`; see Events and sync |
| `POST /api/sessions/{sid}/commands` | `{operation, payload, control_sequence?}` and `X-Request-ID`; commands below |
| `POST /api/sessions/{sid}/export-snapshot` | `{include_unresolved}`; consistent JSON download without retained export/retry rows |
| `GET /api/sessions/{sid}/events?after=0` | Up to 200 metadata events, `next_after`; poll again if page full |
| `GET /api/sessions/{sid}/records/{id}?revision=N` | Current or historical record; full exports facilitator-only |
| `GET /api/sessions/{sid}/sources/{id}/media` | Authenticated image bytes; use fetch + Blob URL, revoke Blob URL after display |
| `GET /api/sessions/{sid}/sources/{id}/regions/{region_id}?revision=N` | Author/facilitator crop from the current named revision; stale revision conflicts |
| `GET /api/sessions/{sid}/exports/{id}?format=json` | Frozen JSON export; `format=markdown` downloads Markdown |
| `DELETE /api/sessions/{sid}` | Facilitator purge; retry returns deletion receipt |

Snapshot/record responses omit image base64. Snapshot exports expose their manifest, not the full export. Responses use `Cache-Control: no-store`.

## Commands

Payload fields listed without `?` are required. Unknown fields are rejected. `expected_revision` always refers to the target record's displayed revision.

| Operation | Payload | Who |
| --- | --- | --- |
| `participant.invite` | `{invitation, expected_roster_revision, role?, expires_seconds?}`; client-generated capability, 60-3600 seconds, default 600 | Facilitator |
| `invitation.revoke` | `{invitation_id, expected_roster_revision}` | Facilitator |
| `participant.role` | `{actor_id, role, expected_roster_revision}`; facilitator/participant/viewer | Facilitator; last facilitator retained |
| `participant.remove` | `{actor_id, expected_roster_revision}` | Facilitator; last facilitator retained |
| `consent.acknowledge` | `{policy_version}` | Each actor for themselves |
| `consent.withdraw` | `{}` | Each actor for themselves; pauses capture |
| `session.activate` | `{policy_version, expected_session_revision}` | Facilitator; every current actor acknowledged |
| `session.pause` | `{}` | Any actor |
| `session.close` | `{expected_session_revision}` | Facilitator |
| `session.heartbeat` | `{}` | Facilitator |
| `source.text` | `{text}` | Participant/facilitator; active session |
| `source.image` | `{mime, base64, regions}` | Participant/facilitator; active session |
| `source.audio` | `{mime, base64, ended_reason}`; `mime` is `audio/pcm16` (16kHz mono PCM16), `ended_reason` is `silence` or `hard_cut` | Participant/facilitator; active session |
| `source.correct` | `{source_id, expected_revision, text}` | Source author/facilitator |
| `source.regions` | `{source_id, expected_revision, regions}` | Source author/facilitator |
| `extraction.queue` | `{source_id, expected_revision}` | Participant/facilitator; active image source |
| `job.cancel` | `{job_id, expected_revision}` | Job author/facilitator |
| `proposal.create` | `{proposal_kind, text, refs, positions?, region_id?}`; a canvas proposal is `{proposal_kind: "canvas", canvas_kind, canvas_data, positions?}` | Participant/facilitator |
| `proposal.edit` | `{proposal_id, expected_revision, text, refs}` | Proposal author/facilitator |
| `proposal.review` | `{proposal_id, expected_revision, decision}`; accept/reject | Facilitator |
| `item.place` | `{placements: [{id, x, y, expected_position_revision, w?, h?}], origin?}` | Participant/facilitator; no review |
| `cluster.membership` | `{cluster_id, expected_revision, add?, remove?}` | Participant/facilitator; no review |
| `canvas.create` | `{kind, data, x, y, w?, h?}` | Participant/facilitator; no review; not gated on an active session |
| `canvas.update` | `{item_id, expected_revision, data}` | Participant/facilitator; no review; canvas objects only |
| `canvas.remove` | `{item_id, expected_revision}` | Participant/facilitator; no review; canvas objects only |
| `item.edit` | `{item_id, expected_revision, text, refs}` | Facilitator |
| `item.undo` | `{item_id, expected_revision, restore_revision}` | Facilitator |
| `export.create` | `{include_unresolved}`; explicit boolean | Facilitator, including closed session |

`source.text` returns `{source, proposal}`; image intake returns a source record. `source.audio` returns a `transcript_segment` record directly, not a source plus proposal: F1.1-F1.3 is single-lane (see decisions/decision-log.md), so there is no separate extraction-queue step for audio the way there is for images. Its `data` carries `status` (`final` or `gap`, F6.4: a failed transcription is a visible gap, never dropped), `text`, `confidence`, `speaker_actor_id` and `attribution` (`per_connection`, the documented diarisation fallback, not embedding+clustering), and a `provenance` object (`producer`, `model_version`, `synthetic`, `checksum`, `created_at`) per F6.3. A transcript segment is written directly rather than going through `proposal.review` because pipelines.md treats S9 (emit to the bus) as the end of pipeline 1: promoting words into decisions/actions is pipeline 6's job, not this one's. Queue returns a job record. Proposal creation/edit returns a proposal record. Accept returns `{proposal, item}`; reject returns `{proposal}`. Item edits/undo return `{item, invalidated}`. `canvas.create` returns `{item, position}`; `canvas.update` and `canvas.remove` return `{item, invalidated}`. Read the returned revisions after every operation.

### Joining and lifecycle compatibility

The old `{name, token}` invitation is rejected. The facilitator generates an invitation capability locally and retains the original request for delivery retries. Its response contains `invitation_id`, role, expiry, policy version and roster revision, never the reusable capability. The participant's client generates its own credential and redeems directly. Only hashes are stored. A successful join retry must repeat the exact payload; another credential cannot recover a consumed invitation. There are at most eight current members and 128 invitation records per session.

`session.revision` tracks capture-state changes; `session.roster_revision` tracks invitation/admission/removal/role changes; `session.seq` orders events. Heartbeat does not change administrative revisions. Close and roster commands require their displayed revision. Delivery retries retain the original payload.

Invitation/admission does not pause capture. Lease expiry and explicit pause preserve agreement and proposals, while cancelling pending capture jobs. Heartbeat never reactivates capture. Withdrawal clears only the caller's agreement, records `withdrawn_at`, and pauses capture. Reactivation requires every remaining member to acknowledge. Close remains terminal. Members expose `consent_version`, `agreed_at` and `withdrawn_at`; repeated acknowledgements preserve timestamps.

Removal immediately denies authentication and replay, and cancels that actor's pending jobs. Historical actor IDs remain provenance. There is no lost-credential recovery. This prevents routine facilitator credential sharing; invitation redemption does not establish real-world identity or prevent deliberate self-redemption.

Ordered migrations add invitations/session fields in schema 2, sanitised media in schema 3, and the bounded control ledger in schema 4. Existing credentials are preserved. Legacy acknowledgements have unknown `agreed_at` until renewed and are not retroactively described as independent joining. Declared original image payloads are removed from current records, history and retry results; invalid legacy images become unavailable. Migration failure rolls back that migration and prevents startup.

### Bounded control replay

`session.pause`, `session.close`, `session.heartbeat`, `participant.remove`, `consent.withdraw` and `invitation.revoke` require integer `control_sequence` in the command envelope. Other commands reject that field. The snapshot exposes the authenticated actor's `next_control_sequence`; allocate intents serially and preserve sequence, request ID and payload on retry. A control response includes the next sequence at that commit.

The latest 128 responses per actor are retained, each bounded to 2048 bytes. Old sequences return `control_replay_expired`, which does not mean the earlier action failed. Competing allocations return `control_sequence_conflict`. Refresh after either conflict. Ordinary requests and controls have separate replay ledgers; never reuse an intent across command classes.

Role changes and agreement renewal use ordinary quotas, bounding repeated withdrawal/renewal and promotion/demotion history while keeping stop actions available at logical caps. Repeated pause/withdrawal is a state no-op. Heartbeats coalesce lease writes within ten seconds and emit no events. The control sequence can advance for a state no-op.

`export-snapshot` reads one consistent transaction and adds no export, event or retry rows. It works at record/request/content limits, including after close. Repeated downloads can reflect later edits, so the manifest's snapshot sequence identifies the release. Use `export.create` for a retained immutable server export. Unreadable physical storage cannot be exported.

### Source regions

```json
{"mime":"image/png","base64":"<encoded bytes>","regions":[{"id":"region_001","box":[0.1,0.2,0.3,0.4]}]}
```

`box` is `[x, y, width, height]` normalised to the EXIF-oriented image, with positive dimensions inside `[0,1]`. Supply 1–60 unique region IDs. Intake fully decodes PNG/JPEG and returns sanitised dimensions and a media ID. Fresh PNG encoding strips metadata/appended bytes, applies orientation, flattens alpha onto white and discards ICC profiles. RGB values are treated as sRGB; colour-managed fidelity is not promised. Region edits reference the same immutable payload.

Full media and crops require a current facilitator or the source's participant author. Viewers and unrelated participants are denied, including full-image crop regions. Crops name the current source revision and region; stale or removed regions cannot resolve to different evidence. Crops have no persistent cache and authority/revision are rechecked before return. Sanitisation does not hide visible names or faces.

### Clusters

A cluster is a `relationship` proposal carrying `form: "cluster"`, so it goes through review like anything else a model makes: a grouping is a claim about meaning, and the product's rule is that a model's claim is provisional until a person accepts it. A direct-write command for clusters would have quietly exempted the model's groupings from that.

Membership is a list of references, not a geometric fact. `spec/canvas-layout.md` has the client decide that a drop joins a group when the item's centre falls inside the hull; the result is recorded here, so two clients cannot disagree about who is in a group. The hull itself is drawn by the client from the members' positions and is never stored.

- **At most 24 members.** Past that the spec says it is "a list that has been drawn badly", so it is not a form. The 9-item threshold in the same section, where a hull stops reading as a group, is guidance for the layout engine in the client and is **not** enforced here: refusing a person's grouping of twelve would be the server arguing with the person holding the pen, which that spec rejects elsewhere in as many words.
- **An item belongs to at most one cluster.** A hull is drawn 12px outside its members and wants 24px clearance from an item it does not contain, so an item inside two hulls cannot satisfy its own separation rules. A drawing constraint, not a policy preference. 409 `already_clustered`, naming the cluster that holds it.
- A cluster cannot hold a cluster.
- `cluster.membership` moves items in and out with no review, because joining a group by dragging is a person's arrangement act, like `item.place`. Concurrency-checked on the cluster's `expected_revision`.
- **Removing the last member marks the cluster `undone`,** rather than deleting it. What the meeting grouped is evidence, and `item.undo` can restore it. Its former members are free to join another cluster immediately.

The other forms `dataviz.md` names, timeline, flow, hierarchy and matrix, are refused: `cluster` is the only one implemented.

Collision and visibility, `spec/canvas-layout.md` section 4, are **not** enforced here and cannot be without a change of decision. They need each item's rendered box, and the server stores only a position: width follows from text length in three steps, but height follows from wrapping, which is a rendering fact. Enforcing "the model never creates an overlap" server-side would mean storing a box per item, which is a second answer to a question the text already half answers. The layout engine lives in the client, as that spec's own first paragraph says. What the server does enforce is the rule that protects a person's work: a `machine` placement onto a hand-placed record is refused.

### Canvas objects

The contract is `docs/specs/2026-10-18-canvas-object-model.md`. Five kinds join the notes: `shape`, `text`, `arrow`, `section` and `stroke`. They are records of kind `item` (drawn by hand, or accepted) or `proposal` (proposed), so provenance and review stay native to every object.

**The review rule.** Who made it decides the path, because the product's rule is that a model's output is provisional until a person accepts it, while a person drawing is arranging their own board.

| Who made it | Path |
| --- | --- |
| A person, by hand | `canvas.create`: an accepted item at once, `origin: "human"`, `made_by_hand: true`, `author_id` and `accepted_by` both the maker, position hand-placed. No review, like `item.place`. |
| Anyone proposing (a model, later) | `proposal.create` with `proposal_kind: "canvas"`: `needs_review` until a facilitator accepts or rejects it, as for every proposal. |
| A person typing a sticky note | Unchanged: `source.text` makes a content proposal that is reviewed, so the record says who accepted it. A facilitator's "add and accept" is `source.text` then `proposal.review`. |

**Kinds and `data`.** Each kind takes exactly its own fields; unknown fields are 422 `unknown_fields`, missing ones `missing_fields`. Every closed set is closed because the client draws exactly these values and an unknown one would be stored and silently not drawn.

| Kind | Fields | Limits and codes |
| --- | --- | --- |
| `shape` | `shape` (`rect`, `ellipse`, `diamond`, `line`), `tone`, `text?` | text at most 280 characters (`invalid_text`); `invalid_shape` |
| `text` | `text`, `size` (`body`, `title`, `heading`) | 1 to 1000 characters, not only whitespace; `invalid_text_size` |
| `arrow` | `from`, `to`, `tone`, `label?` | each end is exactly `{"id": record}` or `{"x": n, "y": n}` (`invalid_endpoint`); points within ±100000; label at most 80 characters |
| `section` | `title`, `form` (`free`, `cluster`, `timeline`, `matrix`, `flow`), `member_ids` | title at most 80 characters (may be empty); at most 60 unique members (`section_too_large`, `duplicate_member`) |
| `stroke` | `points` (`[x, y]` relative to the stroke's position), `weight` (`fine`, `regular`, `bold`), `tone` | 2 to 256 points, each coordinate finite and within ±10000 (`invalid_points`); `invalid_weight` |

`tone` is `ink`, `accent`, `category-1`, `category-2` or `category-3` (`invalid_tone`): the design system's labelled categories, never a status colour, so a coloured shape cannot read as an error.

- **Arrow ends.** An `id` end must exist (404 `not_found`), be an item or proposal (422 `invalid_endpoint`) and be on the canvas, meaning not undone, rejected or superseded, the same test `item.place` uses (409 `invalid_endpoint`). An arrow cannot point from a record to itself, nor at itself after an update (422 `self_arrow`). An arrow whose end is later removed is kept; the client does not draw it.
- **Section members.** Each must exist (404), be a note (a content item or proposal), shape, text or stroke (422 `invalid_member`), never a section (422 `nested_section`: nested sections make "which area is this in" a tree), and be on the canvas (409 `invalid_member`). A section is not a cluster: a cluster is a claim about meaning and is reviewed; a section is an area a person draws.
- **Common fields** on every item: `item_kind`, `origin`, `author_id`, `accepted_by`, `status` (`accepted` or `undone`), `created_at`, `last_editor`; hand-made items add `made_by_hand: true`, accepted proposals add `proposal_id` and keep the proposal's `origin`.

**Commands.** None is gated on an active session, for the reason `item.place` is not: arranging adds no captured content and a missed heartbeat alone pauses a session. All are refused 409 `session_closed` once the session is closed, and 403 `forbidden` for a viewer. Any participant or facilitator may change or remove any canvas object, as any of them may move any note.

- `canvas.create` validates `data` and the size rules below, writes the item and its hand-placed position in one transaction, and counts towards `MAX_RECORDS` (429 `record_capacity`).
- `canvas.update` merges `data`, which names only the fields that change and must name at least one (`invalid_data`), onto the current fields and validates the whole object again, so an update cannot make what creation would refuse. Only the kind's own fields may change: `origin`, `status` and the other common fields are `unknown_fields`, because provenance is not something an edit may rewrite. A new revision; 409 `stale_revision` on a stale `expected_revision`. A removed object is 409 `item_undone`.
- `canvas.remove` sets `status: "undone"` and `removed_by`, keeping the record and its position, so `item.undo` with a positive `restore_revision` restores it where it was. 409 `stale_revision` as above.
- Both refuse anything that is not one of the five kinds with 422 `invalid_target`. In the other direction `item.edit` refuses a canvas object (`invalid_target`), because writing text and refs onto a drawing would make it shaped like a note, and `proposal.edit` refuses a canvas proposal (409 `invalid_target`): changing a proposal is a rejection and a fresh proposal, so the history shows both.

**Canvas proposals.** `{proposal_kind: "canvas", canvas_kind, canvas_data, positions?}`, with `canvas_data` validated exactly as `canvas.create` validates `data`; `text` and `refs` are not taken. `positions`, when given, is a list of exactly one entry, the proposal's own place, `{x, y, w?, h?}` (`invalid_positions` otherwise), with the size rules below. It is written as a machine placement, so the layout engine may still refine it and a person's drag overrides it. Accepting creates an item with `item_kind` equal to `canvas_kind` and the same fields, after validating them again (an arrow end or member removed meanwhile is refused as at creation), and carries the position and size onto the item as a hand placement, as for content proposals. Rejecting creates nothing.

**Sizes.** A position may carry `w` and `h`, each a finite number from 8 to 4000 (`invalid_size`); one without the other is `invalid_size`. A size is required whenever a `shape`, `text` or `section` first gets a position (at `canvas.create`, in a canvas proposal's `positions`, or at its first `item.place`), optional for `arrow` and `stroke` (stored, ignored by the client), and refused for notes, clusters and every other record (`invalid_size`), whose width follows their text. A placement without `w` and `h` keeps the stored size.

### Proposals and items

`proposal_kind` is `content`, `relationship`, `placement` or `canvas` (see Canvas objects; the rest of this paragraph is about the first three). All have reviewable text and 1–60 current refs. Relationships/placements target accepted items, not proposals. Placement `positions` is a list of `{id, x, y}` with exactly the referenced IDs and finite coordinates bounded to ±100000. Positions are board coordinates, not normalized crop coordinates. Changing placement targets requires a fresh proposal.

Manual crop transcription uses a content proposal with `region_id` and exactly one current image source ref. Model output marked `unreadable` must be edited with human text before acceptance. Display `origin`, `synthetic`, `reading_status`, source crop and provider/model metadata where available. Human editing does not erase fixture/model origin.

Extraction proposals also carry `confidence` and `colour` (F02), both always present and often `null`. `null` means nobody measured it; the fixture always sends `null` for both, because a made-up score would be read as a real one. `confidence` is a number from 0 to 1 on the named `provider`/`model`'s own scale, so it is comparable only within one model. It is never acceptance authority: a reading at 1.0 waits for review like one at 0.0. `colour` is the colour of the physical paper in the photograph, not the planned F3.8 topic colour, which is a separate categorical palette chosen for meaning. It is `{space: "srgb", hex: "#rrggbb", source}` with lowercase hex, where `source` is `model_reported` (the model named a colour) or `pixel_measured` (sampled from the sanitised image). An adapter that returns anything else for either fails the job with `adapter_failed`, and none of its proposals are published. Both fields carry onto the accepted item. When a person edits the text of the proposal or the item, `confidence` becomes `null`, because it described words that are no longer there; `colour` stays, and the version history keeps the model's original score. Records created before this change have neither key.

Proposal states: `needs_review`, `stale`, `accepted`, `rejected`. Accepted/rejected proposals are immutable history. Items have `accepted`, `stale` or `undone` status. A changed source/item invalidates dependent items and proposals transitively; new review or a fresh proposal is needed. Content edits and structural acceptance are separate actions. `item.edit` is an explicit facilitator review of current refs; it must not run automatically when source revisions change.

`item.undo` with `restore_revision: 0` marks the item undone. A positive earlier revision restores that snapshot into a **new** revision, only if its dependencies remain current. Dependent records become stale. Undo never rewinds the entire session.

### Jobs

States are `queued`, `running`, `succeeded`, `failed` and `cancelled`. Poll events/record, show fixture status, and retain a manual transcription path. Jobs time out after 60 seconds; late results are discarded. A source revision change, pause, policy change or deletion prevents stale completion. Restart recovery never requeues a claimed job. It marks the outcome unknown before deadline/lease cleanup, fails the job with `interrupted_unknown_outcome`, and requires an explicit new intent for another attempt. Unclaimed queued jobs can still run.

### Export and deletion

`export.create` returns a frozen export record with a manifest, included records and Markdown. `include_unresolved: false` includes accepted items and lists omitted unresolved IDs/counts; `true` includes unresolved proposals/stale items. Manifest ID/kind/revision entries match every included record. Export creation does not accept proposals. Source evidence and credentials are excluded; references require the retained server session. Downloaded copies are outside server deletion.

Deletion removes live session content, history, events, jobs and retry results together. A small receipt retains the session ID, timestamps and a facilitator credential hash for idempotent acknowledgement. It does not certify removal from backups or copies outside the live database.

## Errors and UI behavior

Errors have `{error: {code, message, details}}`.

| HTTP | Examples | UI response |
| --- | --- | --- |
| 400 | Malformed JSON | Explain the specific input error; do not blindly retry |
| 422 | Missing/unknown fields, invalid values or refs | Explain the specific input error; do not blindly retry |
| 401/403 | Invalid credential / insufficient role | Stop writes and show access state |
| 404 | Missing record/route/operation | Refresh relevant state; do not substitute another record |
| 409 | `stale_revision`, `stale_proposal`, `capture_inactive`, `idempotency_conflict` | Refresh, preserve unsaved text and require renewed intent |
| 413 | Oversized request/image | Reduce source size before resubmitting |
| 429 | Queue, record or storage capacity | Offer cancellation, export, close or deletion as appropriate |
| 500 | Generic internal failure | Preserve request ID/payload for uncertain-result retry |

The client must preserve edits when a conflict occurs. Render all source/model/user strings as untrusted text. Disable capture while draft/paused/closed and show stale dependencies visibly. Do not hide provider fixture labels or turn model confidence into acceptance.

### Position

Every record in a snapshot carries `position`, either `null` or
`{x, y, w, h, revision, hand_placed, placed_by, placed_at}`. It is the only answer to
where something is. Coordinates are board coordinates, finite and within
±100000. `w` and `h` are `null` for every note and cluster, because
`spec/canvas-layout.md` derives item width from text length in three steps
rather than storing it; only the canvas objects carry a size (see Canvas objects).

`item.place` moves one to 60 records in one atomic command. Any participant may
move any item or proposal without review, because moving is not agreeing:
dragging a provisional note somewhere useful is how a person reads a board. It
is not gated on an active session, unlike capture, since a move adds no content
and a missed heartbeat alone pauses a session.

Concurrency is per record, on `expected_position_revision`, starting at 0 for a
record that has never been placed. A mismatch is 409 `stale_position` carrying
`current_position_revision`. Nothing is written unless every placement in the
command validates.

`origin` is `human` (default) or `machine`. A human placement sets `hand_placed`,
which is permanent for the session: a `machine` placement onto a hand-placed
record is refused 409 `hand_placed`. That is F3.4 enforced by the server rather
than promised by the client, and it is why the layout engine can still refine
its own guesses. `board_order` in the snapshot is the board's z-order, innermost
first: model-placed, then hand-placed, then most recently touched, ties broken
on record id so two clients agree.

A move never touches the record, so its revision does not change, no `versions`
row is written, and pending proposals that reference it do not go stale.
Correcting a note's text therefore leaves it where it is, and `item.undo`
restores text without restoring a position, so undo cannot erase somebody
else's later move.

Accepting a `placement` proposal writes the coordinates onto the items it names
and creates **no item of its own**: the result is `{proposal, placements}`, not
`{proposal, item}`. Accepting a content proposal that a person had already
dragged carries that position onto the new item and clears it from the proposal.

Schema 5 converges both published histories: the B/C version 2 positions schema and the A/E/D versions 2-4 consent/media/control schema. Migration detects actual tables before advancing. Existing positions survive; databases without positions fold accepted legacy placement items in rowid order and mark those items superseded. Migration failure rolls back its current stage and restart resumes from the durable stage. Schema 6 adds nullable `w` and `h` to positions in one transaction and leaves every existing row's size null.

### Deletion on disk

`secure_delete` is on, so a purge overwrites the freed pages rather than only
unlinking rows. `test_deleted_words_are_not_left_in_the_database_file` asserts
that by searching the raw file for text the session held: zero occurrences after
deletion.

The file itself does not shrink. Freed pages stay in it, zeroed and reusable,
rather than being returned to the filesystem, so an unchanged file size after a
deletion is expected and is not a failed purge. One session row per deleted
session is kept for the receipt, about 96 bytes, and is never reclaimed.

### Events and sync

Events carry session `state`, `policy_version` and `records: [{id, kind, revision}]`, collected from transaction writes. A position change uses kind `position`; clearing a position uses revision 0. Pause preserves proposals and agreements, so it does not falsely announce staled proposals. Cancellation writes are included.

`GET /api/sessions/{sid}?since_seq=N` returns changed public records, session, members, actor ID, `next_control_sequence`, `since_seq` and `current_seq` from one transaction. It does **not** carry `board_order`: that is a pure function of `hand_placed`, `placed_at` and id, all of which arrive on each record's position, so a client derives it. Sending it made the delta grow with the board. The snapshot still carries it, where the client is receiving everything anyway. Exports remain manifest-only. An ahead cursor is 409 `cursor_ahead`. Encountering legacy events without write descriptors falls back to a full record refetch. Clients should take an initial full snapshot before polling. Record reads include current position even when requesting historical text revisions.

HTTP/1.1 connections are reused, with bounded unread-body draining and the existing ten-second timeout and sixteen connection slots. JSON responses of at least 1 KiB may use gzip when requested and smaller than the original.

When more than half the session's records changed since the cursor, the answer is `{resync_required: true, changed_records, session_records, reason}` and no records. That is a normal answer, not an error: past halfway the snapshot is at most twice the bytes, in one request, with no merge to get wrong. The client takes a snapshot and uses the seq that snapshot reports. `since_seq=0` therefore always answers `resync_required`, so every client exercises that branch on its first call rather than meeting it for the first time during a rare large cascade.

Measured by `tests/measure_sync.py`, one acceptance, seven clients holding cursors, over loopback. These are not device or load measurements.

| Fixture | Records | Positioned | Per client, gzip | Full reload |
|---|---|---|---|---|
| WALL-12 | 41 | yes | 1657 B | 18150 B |
| POSITIONED | 965 | 321 | 1667 B | 465356 B |

Re-measured on 18 October 2026 on a Windows 11 laptop after positions gained `w` and `h`. The same harness on the commit before, on the same machine, gave 1653 B and 1667 B per client and 18149 B and 458297 B for a full reload, so the two keys cost at most 4 B compressed per client and about 7 KB uncompressed on a 321-position full reload. The budget is under 5 KB per client. The second row is the point: the cost is flat in board size. POSITIONED runs by default and the unpositioned CEILING fixture is opt-in, because a board where nothing has been placed is not a board, and keeping the realistic fixture behind a flag is how an 8183 B delta went unnoticed.

Malformed input is a specific client error, never a 500. A string containing an unpaired surrogate is 400 `invalid_json`: `"\ud800"` is a legal JSON escape, so it survives parsing and only fails when something encodes it, and the first thing that does is the idempotency fingerprint, before any handler sees a field. It is checked across the whole body, including keys, for that reason. Valid Unicode, including surrogate pairs for emoji, is unaffected. An id of the wrong JSON type is 422 `invalid_id`. Non-finite numbers remain 400 at the parser.


## Follow-up contracts: recovery, identity and release

### Uncertain extraction outcomes

Claiming a job durably sets `execution_outcome: "unknown"`, `usage_status:
"unknown"` and `usage: null`. A validated returned output records execution as
`completed`; `usage_status: "reported"` requires a reported cost, otherwise it
remains `unknown`. Cancellation and storage rejection do not erase returned
usage, but still prevent proposals from being published. These fields describe
an attempt, not acceptance or a guarantee that a remote provider stopped billing.

If this source has a failed/cancelled job with an uncertain execution outcome,
`extraction.queue` returns 409 `uncertain_retry_requires_acknowledgement` with
`retry_of` identifying the latest uncertain job. A deliberate new attempt uses:

```json
{"source_id":"SOURCE_ID","expected_revision":1,"retry_of":"JOB_ID","acknowledge_uncertain_cost":true}
```

Use the IDs/revision actually returned by the API, generate one new request ID
for that deliberate intent, and retain it for network retries. The boolean must
be exactly true. Acknowledgement for another source is refused. Existing cached
queue replies do not restart their original terminal jobs. Acknowledgement is
required for execution uncertainty, not merely a completed output whose cost is
unknown. Concurrent explicit queue requests remain possible within quotas;
this mechanism is not provider-level idempotency or a billing cap.

The current CLI enables only the offline fixture. Before adding a paid adapter,
its own connect/read/total deadlines, idempotency keys, hard cost limits and
remote cancellation/reconciliation must be implemented and verified. No provider
or price has been selected by this change.

### Credential loss and participant identity

There is no credential-reset, name-based lookup or administrator impersonation
endpoint. If the only facilitator loses their token, privileged access is
unrecoverable; retention still applies. Where another facilitator remains,
they can remove the lost membership and issue a fresh invitation. The new device
creates a new credential and must explicitly acknowledge the current policy;
it receives a new actor ID and does not inherit another actor's agreement.
A display name is not proof of identity. Previously downloaded copies and
previously shared legacy credentials do not become secret through migration.

### Output-only release

New export manifests include `format_version: 1`, `release_kind: "output_only"`,
`output_readable_offline: true`, `redaction_applied: false` and an explicit
`evidence_availability` explanation. The downloaded JSON/Markdown contains the
selected outputs and their labels, so it remains readable after session deletion.
Source references are identifiers whose evidence requires the retained server;
no photograph, crop or transcript evidence bundle is created automatically.

`include_unresolved` is an explicit release choice. It does not accept proposals
or remove visible names. The manifest records exact included revisions and
omitted IDs; the export labels unresolved states and machine/fixture origins.
If redaction or a separately consented evidence bundle is needed, create a
separate release with its own review. Existing exports stay immutable and may
lack the new descriptive fields; do not treat their absence as evidence inclusion.

## Runtime readiness and private diagnostics

| Route | Authority | Response |
| --- | --- | --- |
| `GET /health` | Existing Host/Origin boundary | HTTP liveness only; it can be 200 when processing is not ready |
| `GET /ready` | Existing Host/Origin boundary; no bearer required | 200 with `status: ready`, or 503 with `status: not_ready` and fixed-code checks |
| `GET /api/sessions/{sid}/diagnostics` | Current facilitator credential | Read-only aggregate snapshot; 503 `diagnostics_unavailable` when the bounded store read fails |

The two new routes reject query parameters. Normal `Cache-Control: no-store`
and origin checks apply. Readiness is a signal, not a gate on stop, deletion or
other API commands. Calling `/ready` never advances worker progress.

### Readiness checks

`checks` contains `store`, `worker`, `maintenance`, `completion_store` and
`maintenance_cleanup`. Worker/maintenance states are `not_started`, `starting`,
`idle`, `busy`, `failed`, `stalled` or `stopped`. At least one actual successful
iteration is required. Beginning another iteration does not erase a failure.
The CLI drives these signals; an embedding application must monitor its own
real worker and maintenance loops instead of manufacturing successful ticks.

Worker progress becomes stale after 90 seconds, maintenance after 15 seconds,
using monotonic time. These are diagnostic thresholds, not performance targets.
Failed/stalled/stopped loops, pending completion-store retries or pending cleanup
faults keep readiness at 503. A contended completion lock reports `checking`.
No session IDs, paths, credentials or exception text appear in `/ready`.

The store check opens the existing SQLite file and attempts `BEGIN IMMEDIATE`,
reads the session table, and rolls back. `available` means a write transaction
can be acquired; it does not prove a future commit has disk space or that a
backup can be restored. It never creates a replacement for a missing database.
The check is cached for at most one second and concurrent refreshes do not queue
behind each other. SQLite lock timeout is 100 ms; a progress handler applies a
250 ms query budget. These do not impose a hard deadline on stalled operating-
system I/O, and do not replace physical fault tests.

### Session diagnostics

The response includes:

- `record_counts`: source/proposal/item/job/export totals and an `other` count.
- `jobs.counts`, nonnegative `oldest_queued_age_seconds`, and `uncertain_count`.
- At most 20 failed/cancelled jobs, newest-created first, under `jobs.attention`.
  Entries contain generated job IDs, fixed status/outcome values and allowlisted
  reason codes. `attention_total` and `attention_truncated` prevent the limited
  list from implying that all attention items were returned.
- `storage`: UTF-8 JSON byte counts for records, history, events and retained
  ordinary/control replies, plus media payload bytes. These are logical stored
  payload sizes, not physical file size, memory use or remaining disk space.
- Session state, snapshot sequence and time until retention expiry.
- `pending_completions`: this session's in-memory result count, or null if the
  short lock attempt cannot observe it; null must not be displayed as zero.
- Global runtime loop signals, without details of other sessions.

Durable metrics share one read-only transaction. In-memory completion counts and
loop signals are sampled afterwards and may describe a slightly later instant.
The route does not sweep sessions, emit events or append retry records. Removed
and demoted facilitators lose diagnostic access immediately at the next read.
Titles, participant names, credentials, source text/images, file paths and raw
provider/SQL error strings are not returned. See RUNTIME-OPERATIONS.md for how to
interpret failures without treating diagnostics as an automatic recovery tool.
## Executable JavaScript connection layer

[CLIENT-PLUMBING.md](CLIENT-PLUMBING.md) documents the dependency-free transport
and SessionConnection contracts. All request methods accept trailing signal and
timeout options; commands retain exact immutable intent bytes for explicit retry.
An uncertain outcome is never resolved by silently generating a new request ID.
Client terminal states clear owned credentials/URLs and session cache. Application
visibility/connectivity events and reconciliation presentation remain host duties.

## Voice poll addition, 19 October 2026

The existing authenticated command envelope also supports the `poll.*`
operations documented in [voice-polls.md](../../docs/voice-polls.md). Poll,
ballot, interpretation-work and poll-policy records use the existing session
store and version history. Snapshots/deltas include `session.poll_ai` for
configuration and consent feedback. `item.place` also accepts a poll record;
moving it does not accept its question or inferred ballots. Other commands and
their envelopes retain the contract documented above.

## Voice command documents, 19 October 2026

Authenticated `document.*` operations create, edit, close, accept, reopen, cancel
and explicitly retry original-transcript documents. Types are `todo`,
`requirements` and `calendar`, with typed task/criterion/event entries. See [the to-do interface](../../docs/voice-todo-lists.md),
[criterion fields and safeguards](../../docs/voice-requirements.md) and
[calendar operations, date fields and shared-task review](../../docs/voice-calendar.md).
Snapshots/deltas include `session.command_ai`. Collection and review do not gate
transcription or other document types. Existing session agreement is renewed when
the enabled text scope/types change. Session creation optionally accepts an IANA
`timezone` (legacy default UTC); snapshots/deltas expose it. Audio optionally
supplies integer `captured_at_utc_ms` alongside monotonic capture order.
`calendar.entry.edit`, `calendar.task.resolve` and `calendar.view` use the same
authenticated, revision-checked command envelope. Poll interfaces are unchanged.
`calendar.entry.edit` optionally accepts `note_id` on a new manual event, linking
it to an accepted content item on the canvas; see the calendar document.
