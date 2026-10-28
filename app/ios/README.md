# Jarvaids iOS client: Core layer

A Swift client for the local backend in [`app/server`](../server). This directory holds
the non-UI half of it: the wire models, the HTTP client, the error vocabulary, the
observable session state and the facilitator heartbeat. There are no views here, and
there should not be.

The backend is the authority on behaviour. Read [`app/server/API.md`](../server/API.md)
first; everything below assumes it.

## What this is for

The product rule the flowchart keeps repeating is that **anything a model made is
provisional until a person accepts it**. The API models that as proposals versus items,
and so does this package:

| Product idea | API | Here |
| --- | --- | --- |
| The model suggested something | proposal, `status: needs_review` | `ProposalData`, `SessionStore.pendingProposals` |
| A person accepted it | item, `status: accepted` | `ItemData`, `SessionStore.acceptedItems` |
| Something underneath it changed | `status: stale`, transitively | `SessionStore.staleProposals`, `.staleItems` |
| A person took it back | item `status: undone` | `CommandIntent.undoItem(_:to:)` |
| The model is still working | job `queued`/`running` | `SessionStore.jobProgress` |

Nothing in this package accepts, edits or repairs anything on a person's behalf. That is
not caution, it is the contract: `item.edit` is defined as an explicit facilitator review,
and an HTTP 409 is defined as a request for renewed human intent.

## How it maps to the API

| API.md | Here |
| --- | --- |
| `GET /health` | `JarvaidsAPIClient.health()` |
| `POST /api/sessions` | `JarvaidsAPIClient.createSession(ownerName:title:retentionSeconds:)` |
| `GET /api/sessions/{sid}` | `JarvaidsAPIClient.snapshot()`, returning `.live` or `.deleted` |
| `POST /api/sessions/{sid}/commands` | `JarvaidsAPIClient.submit(_:)`, taking a `CommandIntent` |
| `GET .../events?after=N` | `JarvaidsAPIClient.events(after:)` |
| `GET .../records/{id}` | `JarvaidsAPIClient.record(_:revision:)` |
| `GET .../sources/{id}/media` | `JarvaidsAPIClient.sourceMedia(_:)` |
| `GET .../exports/{id}` | `JarvaidsAPIClient.exportDocument(_:)` and `.exportMarkdown(_:)` |
| `DELETE /api/sessions/{sid}` | `JarvaidsAPIClient.deleteSession()` |
| the 19 commands | one `CommandIntent` factory each, in `CommandIntent.swift` |
| `{error: {code, message, details}}` | `APIErrorBody`, `ErrorCode`, `JarvaidsError` |

### Three decisions worth knowing before you use it

**A command is a value, not a call.** `CommandIntent` generates its `X-Request-ID` and
serialises its body in the same initialiser, and both are constants. `submit` accepts
nothing else. So "retry after an uncertain result" can only mean handing the same value
back, which is what the idempotency rule asks for, and "a fresh action" can only mean
making a new intent, which is what it also asks for. There is no way to pair one request
ID with two payloads.

**A 409 is not a retry.** `JarvaidsError` splits the status codes into separate cases, and
`mayResendSameIntent` is true only for transport failures and 5xx. `ConflictError` reports
the server's `current_revision` as a plain `Int` documented as display-only, and the
`Revision` type that `expected_revision` demands has no public initialiser taking an
`Int`. Building one takes `Revision.afterHumanReview(_:)`, which is a sentence you have to
write on purpose. The reason is in API.md: auto-retrying a 409 with a fresh revision
accepts, on a person's behalf, something they never read.

**Events say "something moved", not "what moved".** `SessionStore` polls events, and when
any of them implies a record changed it refetches the whole snapshot. It never tries to
patch state from an event body, because the API does not provide one. The polling interval
is the single constant `SessionStore.pollInterval`.

### Credentials

Generated on the device, held in memory, and never written anywhere. `ActorToken` is
`Encodable` but not `Decodable`, and both its `description` and `debugDescription` are the
literal string `ActorToken(redacted)`, so it cannot reach a log by accident. Getting at
the secret takes `.rawValue`, which is one grep away in review.

Losing a credential loses access. There is no recovery and no identity provider, which is
the backend's position too. Persisting one would be a product decision with consequences,
so this package gives you no help with it.

## Opening it in Xcode

There is no `.xcodeproj` in this directory. The Core layer is a SwiftPM library, and the
app shell that wraps it is not yet written.

To work on the Core layer alone:

```sh
cd app/ios
open Package.swift          # Xcode opens the package directly
swift build                 # or from the command line, on macOS
```

To use it from an app:

1. Create an iOS App target in Xcode (iOS 17 or later; `@Observable` and
   `Task.sleep(for:)` set that floor).
2. **File > Add Package Dependencies > Add Local**, and choose this `app/ios` directory.
3. Add `JarvaidsCore` to the app target's frameworks.
4. Put the UI in `Jarvaids/UI/` and add a target for it in `Package.swift`. No target is
   declared for it here, deliberately: see below.

For the simulator, point the client at the local backend:

```swift
let credential = SessionCredential.makeRandom()
let client = JarvaidsAPIClient(
    configuration: try .localPrototype(port: 3000),
    credential: credential
)
```

`http://127.0.0.1` reaches the host machine from the simulator but **not** from a device
on the desk. A device needs the server reachable another way, and the server binds only to
loopback and has no transport security, so that is a deployment question and not a
configuration flag. `JarvaidsAPIClient.Configuration` refuses plain HTTP to anything that is
not loopback for the same reason.

## What is deliberately absent

- **Every view.** No SwiftUI, no UIKit, no navigation, no formatting. The UI layer lives
  in `Jarvaids/UI/` and is owned by a different workstream. This package imports
  `Foundation` and `Observation` and nothing else.
- **Audio capture, speech recognition and OCR.** The backend has none: `/health` reports
  `live_ocr: false` and the only adapter is a labelled fixture that emits one synthetic
  note per crop. A client that captured audio would be collecting data nothing can
  process. The flowchart's speech path is a design intention, not a built feature.
- **Third-party dependencies.** None, at all. The contract is JSON over HTTP.
- **Credential storage.** No Keychain, no `UserDefaults`, no file.
- **Automatic conflict resolution, automatic re-acceptance and automatic reactivation of
  capture.** All three would bypass a person. The last one is called out explicitly in the
  backend README.
- **Offline queueing.** A command carries an `expected_revision` that was true when a
  person looked at the screen. Replaying a queue of those later would submit decisions
  against a board that has moved.
- **Image decoding, cropping and rendering.** `sourceMedia` returns bytes and a MIME type.
  Turning those into something on screen is the UI layer's job.
- **Tests.** See [VERIFICATION.md](VERIFICATION.md), which is blunt about what has and has
  not been checked.

## The UI layer is somebody else's

`Jarvaids/UI/` is not written, not declared in `Package.swift` and not referenced from any
file here. Core exposes state and takes commands; it has no opinion about screens.

What the UI layer owes the product, and what this package cannot do for it, is in API.md's
last section: render every source, model and user string as untrusted text rather than
markup; keep fixture and model labels visible; show stale dependencies rather than hiding
them; preserve what someone typed when a conflict arrives; and never turn a model's
confidence into an acceptance.

## Layout

```
app/ios/
  Package.swift              SwiftPM manifest. Core only.
  README.md                  This file.
  VERIFICATION.md            What has not been compiled, and what to check first.
  Jarvaids/
    Core/
      Identifiers.swift        IDs, tokens, revisions, timestamps, randomness.
      Enums.swift              Every server-reported state, with unknown-value fallback.
      JSONValue.swift          Any-JSON, for error details and unrecognised records.
      Models.swift             The wire shapes.
      JarvaidsError.swift        Status codes as distinct cases; the 409 rules.
      CommandIntent.swift      One frozen intent per user action, one per operation.
      JarvaidsAPIClient.swift    The actor wrapping URLSession.
      SessionStore.swift       Observable snapshot, cursor, derived state, poll loop.
      FacilitatorHeartbeat.swift  Roughly once a minute while attended.
    UI/                      Owned elsewhere. Nothing in this package touches it.
```
