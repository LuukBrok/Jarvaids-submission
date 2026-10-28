# Verification status

**None of the Swift in this directory has been compiled.** There is no Swift toolchain in
the environment it was written in and the platform was Linux, so there has been no
`swift build`, no `xcodebuild`, no test run and no execution of any kind. Treat every file
here as a reviewed draft, not as working code.

What *was* verified is the other half: the shapes on the wire. The Python backend was run
locally and driven through a full session with `curl`, and the `Codable` types were
written against the captured payloads rather than against the prose in `API.md`. That
distinction is spelled out below, because where the two disagreed the payload won and
someone reading `API.md` later may think the code is wrong.

## Verified against a running server

Server: `python3 -m genai_server --port 8803 --data-dir /tmp/swiftscaffold`, adapter
`fixture`, no keys. A complete session was created, activated, filled, reviewed, corrected,
exported, closed and deleted.

| Payload | Captured |
| --- | --- |
| `GET /health` | yes |
| `POST /api/sessions`, first call and replay, with and without `retention_seconds` | yes |
| `GET /api/sessions/{sid}` in draft and in active, and after deletion | yes |
| Every command response listed below | yes |
| `GET .../events?after=N`, including the paging envelope | yes |
| `GET .../records/{id}` current and `?revision=1` historical | yes |
| `GET .../sources/{id}/media` headers and bytes | yes |
| `GET .../exports/{id}?format=json` and `?format=markdown` | yes |
| `DELETE /api/sessions/{sid}`, first call and replay | yes |

Commands exercised and decoded: `participant.invite`, `consent.acknowledge`,
`session.activate`, `session.heartbeat`, `session.close`, `source.text`, `source.image`,
`source.correct`, `extraction.queue`, `proposal.create` for all three kinds,
`proposal.review` accept and reject, `item.edit`, `item.undo`, `export.create`.

Errors reproduced and their status codes recorded: `idempotency_conflict` (409),
`stale_revision` (409, with `details.record_id` and `details.current_revision`),
`policy_changed` (409, with `details.current_policy_version`), `forbidden` (403),
`unauthorized` (401), `unknown_operation` (404), `not_found` (404), `unknown_fields` (422),
`invalid_json` (400), `invalid_id` (422).

### Where the payload contradicted the prose

These are the reasons the code looks the way it does. Do not "correct" them back.

1. **`status`, not `state`.** `API.md` says "Proposal states: `needs_review`, `stale`,
   `accepted`, `rejected`" and "States are `queued`, `running`, ...". The wire field on
   proposals, items and jobs is `status` in every case. The Swift property is `status` and
   the type is named `ProposalState` to match the prose.
2. **`members`, not `actors`.** `API.md` says the snapshot returns "session, actors and
   public records". The key is `members`.
3. **422 is real.** The error table in `API.md` lists 400 for invalid fields. The server's
   validator defaults to **422**, and 400 is reserved for malformed JSON. `JarvaidsError`
   maps both 400 and 422 to `.invalidRequest`.
4. **A deleted session answers `GET` with a different document, under HTTP 200.**
   `{session_id, state, deleted_at, content_available}` instead of a snapshot. Hence
   `SnapshotResponse` being an enum rather than a struct full of optionals.
5. **`GET .../exports/{id}?format=json` has no record envelope.** It returns
   `{manifest, records, markdown}` directly, whereas the same export inside a snapshot is
   a normal record whose `data` contains only `manifest`. Two types: `ExportDocument` and
   `ExportRecordData`.
6. **`participant.invite` bumps `policy_version`.** Acknowledgements taken before an
   invite are void, so the obvious first-run sequence (acknowledge, then invite, then
   activate) fails. Documented on `Member.hasAcknowledged(policyVersion:)`.
7. **Missing or malformed `X-Request-ID` is `invalid_id` (422), not a 400.**
8. **Events carry more than their record list.** Worker events use `actor_id: "system"` and
   carry `job_id` and `code`. `ActorID` therefore does not validate its syntax on decode,
   because `system` is six characters and the ID rule is eight to eighty.
   **Stale since chunk C:** the field was `record_ids`, a list of strings. It is now
   `records`, a list of `{id, kind, revision}`, and every event also carries `state` and
   `policy_version`. This Swift has never been compiled, so the decoder has not been
   updated or checked against the new shape.
9. **System event types exist that `API.md` never names**: `job.started`, `job.succeeded`,
   `job.failed`, `job.cancelled`, `job.recovered`, `session.lease_expired`. They were read
   out of `genai_server/service.py`.

### Inferred from prose or source, not observed

- **`participant.role`, `source.regions`, `job.cancel` and `proposal.edit` responses.**
  Their shapes were read from the return statements in `genai_server/service.py` rather
  than captured: `participant.role` returns the same shape as `participant.invite`,
  `source.regions` the same as `source.correct`, and `job.cancel` and `proposal.edit` a
  bare record. Confirm these four first.
- **`session.pause` response.** Inferred as `{state, policy_version}` from the shared
  `_revoke` helper. Almost certainly right, cheap to check.
- **Placement and relationship items.** Accepted content items were captured; an accepted
  *placement* item was not, so `ItemData.positions` is an inference. If an accepted
  placement stores its positions somewhere else, that property is wrong.
- **`reading_status: "unreadable"`.** The fixture only ever emits `readable`, so the
  unreadable path was never seen on the wire. `human_transcribed` was read from the source.
- **413 and 429 bodies.** Not provoked. They are assumed to use the same error envelope as
  everything else, which the server's single `Problem` class makes near certain.
- **`origin` values.** Only `human` and `fixture` were observed. A real provider adapter
  would add its own, which is what the `.unknown` fallback is for.

## What a human must check in Xcode, in order

The list is ordered by how likely it is to be wrong and how much depends on it.

1. **That it compiles at all**, on iOS 17 and macOS 14, in Swift 5.9 mode and then again
   with Swift 6 language mode. The package turns on `StrictConcurrency` as an experimental
   feature, which is the right setting but is also the one most likely to produce
   diagnostics I could not see.
2. **`OpenStringEnum` decoding.** This is the single highest-risk construct in the
   package. Every server-reported state conforms to a protocol that refines both
   `RawRepresentable` and `Codable`, and supplies `init(from:)` in a protocol extension.
   The standard library also has conditional `Codable` implementations on
   `RawRepresentable`. Mine is the more constrained of the two and should win overload
   resolution, but if it does not, decoding an unrecognised value will **throw** instead of
   falling back, which is exactly the crash the design is meant to prevent.
   **Test this first**, with a literal such as `"a_value_from_the_future"` decoded into
   `ProposalState`. If it throws, the fix is to paste an explicit `init(from:)` and
   `encode(to:)` into each concrete enum, which is mechanical.
   The same doubt applies to `IdentifierText` in `Identifiers.swift`.
3. **Hashable and Equatable synthesis through an inherited protocol.** The enums declare
   conformance to `OpenStringEnum`, which refines `Hashable`, rather than listing
   `Hashable` themselves. I believe Swift synthesises derived conformances in that case.
   If it does not, the fix is to add `Hashable` to each enum's conformance list.
4. **The `@Observable` macro on `SessionStore`.** The class is `@MainActor @Observable`
   with `public private(set)` stored properties. That combination is supported as far as I
   know, but macros and access-control interactions are exactly the kind of thing that
   surprises you. If the macro objects, the fallback is `ObservableObject` with
   `@Published`, which costs an `import Combine`.
5. **`URLSession(configuration:delegate:delegateQueue:)` with `RedirectRefusingDelegate`.**
   The delegate is `@unchecked Sendable` because it is stateless. Under Swift 6 the
   compiler may still object to the delegate parameter. Also check that the redirect
   method signature is exactly right: if it is spelled wrongly it simply never gets called,
   silently, and redirects would then be followed with the bearer token attached. Worth an
   actual test against a server that 302s.
6. **`URLSession.data(for:)` and `Duration` arithmetic.** `backoff * (attempt + 1)` in
   `submitRetryingUncertainDelivery` relies on `Duration` having a `*` with `Int`. I am
   fairly confident it does. If not, multiply the components by hand.
7. **`Task.sleep(for:)` cancellation behaviour** in `SessionStore.pollLoop` and
   `FacilitatorHeartbeat.loop`. Both treat any throw from `sleep` as cancellation and
   return. Confirm that is what you want when a task is cancelled mid-meeting.
8. **That `SessionStore` has no `deinit`.** Cancelling the poll task from a `deinit` on a
   main-actor class is a concurrency problem, so the owner has to call `stopPolling()`.
   If the app shell forgets, the loop keeps polling a session nobody is looking at.
9. **Every `private` initialiser reached from an extension in the same file.**
   `CommandIntent.init` is private and every factory is in an extension in that same file.
   That is legal Swift; confirm the compiler agrees.
10. **`escape(_:)` on path components.** It uses `.urlPathAllowed`, which does not escape
    `/`. Server IDs are hex and cannot contain one, and `SessionID` validates on
    construction, but a hand-built ID could slip through the non-validating decode path.

## Things I was unsure about and chose deliberately

- **`SystemRandomNumberGenerator` for tokens.** Documented as cryptographically secure on
  Apple platforms, and it keeps the package free of CryptoKit. If a reviewer disagrees,
  `SecRandomCopyBytes` or `SymmetricKey(size: .bits256)` is a drop-in replacement in
  `RandomText.hexString(byteCount:)`.
- **UUID strings as request IDs.** 36 URL-safe characters, inside the eight to eighty
  rule, and confirmed accepted by the running server.
- **Explicit `CodingKeys` on every type rather than `.convertFromSnakeCase`.** The
  convenience strategy also rewrites the keys of decoded dictionaries, which would mangle
  `error.details.current_policy_version` into a key no lookup finds. Verbose was safer.
- **Two seconds for `SessionStore.pollInterval` and fifty seconds for
  `FacilitatorHeartbeat.interval`.** Neither is a measured number. The heartbeat one has a
  reason behind it (the server lease is three hundred seconds, so a missed beat is
  survivable); the poll interval is a guess that needs a real room to settle.
- **`Revision` having no public `init(Int)`.** This is friction on purpose, and it will
  annoy someone writing a test fixture. `Revision.afterHumanReview(_:)` is the way through.

## Not done

No unit tests are included. The highest-value ones, in order, would be: decoding an
unrecognised enum value; decoding each captured payload from a file of fixtures; the
`JarvaidsError.from(status:body:)` mapping; and a check that `mayResendSameIntent` is false
for every 4xx. Captured payloads for the first two are easy to regenerate by running the
server and repeating the `curl` walkthrough described at the top of this file.

## Awkward corners of the HTTP API, from a Swift client's point of view

Recorded so the next person does not think these are mistakes in the client.

1. **Command results are heterogeneous under one route.** Every command goes to
   `POST /commands` and `result` has a different shape per operation. Swift wants one
   response type per endpoint. The workaround here is a phantom type parameter on
   `CommandIntent`, so the intent carries the result type it expects. It works, but it
   means the compiler is trusting a table in `CommandIntent.swift` that nothing verifies.
2. **`kind` discriminates `data`, but only inside records.** Records are tidy. Command
   results are not: `source.text` returns `{source, proposal}`, `proposal.review` returns
   `{proposal, item?}`, `item.edit` returns `{item, invalidated}`, and `source.image`
   returns a bare record. Six result types for nineteen operations.
3. **The same endpoint returns two document types.** `GET /api/sessions/{sid}` returns a
   snapshot or a deletion receipt, both under HTTP 200. The client has to sniff for a
   `session` key.
4. **`restore_revision: 0` means something categorically different from
   `restore_revision: 3`.** One marks an item undone, the other restores a snapshot. Two
   actions behind one integer. Modelled here as `UndoTarget` with two cases.
5. **Revisions are integers on the wire and the error body hands one straight back.** The
   shape of the API actively invites the auto-retry that `API.md` forbids in prose. All
   the ceremony around `Revision` exists to fight that.
6. **`expected_revision` refers to "the target record's displayed revision", which is a
   fact about the UI.** A client library cannot know what was on screen. Passing an
   `Entity`, which carries id and revision together from one fetch, is the closest
   approximation available in the type system.
7. **Image bytes go up as base64 inside a JSON body and come back as raw bytes from a
   different route.** The four-megabyte-per-image limit is therefore about a third smaller
   in real pixels than it looks. Nothing here does anything about that.
8. **Unknown fields are rejected, which makes optional payload fields a hazard.** Sending
   `role: null` rather than omitting it would fail. This relies on Swift's synthesised
   encoder using `encodeIfPresent` for optionals, which it does, but it is load-bearing
   and not obvious.
9. **`policy_version` is bumped by things that do not look like policy changes**, such as
   inviting someone or closing the session. Every acknowledgement is revoked each time.
   Correct, and surprising the first time it happens mid-meeting.
