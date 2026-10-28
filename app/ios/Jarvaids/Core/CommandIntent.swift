//
//  CommandIntent.swift
//  JarvaidsCore
//
//  A command plus the request ID that identifies it, frozen together.
//
//  API.md: "generate an `X-Request-ID` once per user intent, retain the exact
//  operation/payload and reuse all three after an uncertain network result. A reused key
//  with different content fails with `idempotency_conflict`. A fresh action needs a fresh
//  key."
//
//  That is three rules a caller has to remember, so the type keeps them instead:
//
//  * The request ID is generated inside the initialiser and is a `let`. There is no way
//    to supply one, so two different intents cannot share a key.
//  * The body is serialised once, in the same initialiser, and stored as bytes. There is
//    no way to change the payload of an existing intent, so a key cannot be reused with
//    different content.
//  * `JarvaidsAPIClient.submit` takes nothing but a `CommandIntent`. There is no overload
//    that accepts a loose operation, payload and request ID, so "retry" can only mean
//    resending the same three values.
//
//  Making a new intent is therefore the only way to express a fresh action, which is
//  exactly the rule the server enforces.
//

import Foundation

// MARK: - Operations

/// The operations this client knows how to send. Closed on purpose: unlike the states
/// the server reports back, this is a list the client authors, and an operation this
/// build has never heard of is not something it can meaningfully construct.
public enum CommandOperation: String, Sendable, Hashable {
    case participantInvite = "participant.invite"
    case participantRole = "participant.role"
    case consentAcknowledge = "consent.acknowledge"
    case sessionActivate = "session.activate"
    case sessionPause = "session.pause"
    case sessionClose = "session.close"
    case sessionHeartbeat = "session.heartbeat"
    case sourceText = "source.text"
    case sourceImage = "source.image"
    case sourceCorrect = "source.correct"
    case sourceRegions = "source.regions"
    case extractionQueue = "extraction.queue"
    case jobCancel = "job.cancel"
    case proposalCreate = "proposal.create"
    case proposalEdit = "proposal.edit"
    case proposalReview = "proposal.review"
    case itemEdit = "item.edit"
    case itemUndo = "item.undo"
    case exportCreate = "export.create"
}

public enum ReviewDecision: String, Sendable, Hashable {
    case accept
    case reject
}

/// What `item.undo` should do. The wire field is `restore_revision`, where zero means
/// "mark it undone" and a positive number means "restore that snapshot into a new
/// revision". Two different actions behind one integer, so they get two cases here.
public enum UndoTarget: Sendable, Hashable {
    /// API.md: "`item.undo` with `restore_revision: 0` marks the item undone."
    case markUndone
    /// Restores an earlier snapshot as a new revision, and only if that snapshot's
    /// dependencies are still current. Dependent records go stale either way.
    case restore(Revision)

    var wireValue: Int {
        switch self {
        case .markUndone: return 0
        case .restore(let revision): return revision.value
        }
    }
}

// MARK: - The intent

public struct CommandIntent<Result: Sendable & Decodable>: Sendable {
    /// Generated once, here, and never again for this value.
    public let requestID: RequestID
    public let operation: CommandOperation
    /// The serialised `{operation, payload}` body. Immutable by construction.
    let body: Data

    private init(_ operation: CommandOperation, _ payload: some Encodable & Sendable) throws {
        self.requestID = RandomText.requestID()
        self.operation = operation
        self.body = try CommandBodyEncoder.encode(operation: operation, payload: payload)
    }

    /// A description safe to put in a log. The payload is left out because sources,
    /// proposals and items all carry meeting content, and command bodies are the one
    /// place a token could end up (`participant.invite` carries the invitee's token).
    public var loggableDescription: String {
        "\(operation.rawValue) request=\(requestID.rawValue)"
    }
}

/// `{operation, payload}`, the body every command endpoint expects.
/// Declared at file scope rather than inside the encoding function because a local type
/// cannot be generic.
private struct CommandEnvelope<Payload: Encodable>: Encodable {
    let operation: String
    let payload: Payload
}

enum CommandBodyEncoder {
    static func encode(operation: CommandOperation, payload: some Encodable) throws -> Data {
        let encoder = JSONEncoder()
        // Key order does not matter to the server, which fingerprints the decoded object,
        // but a stable order makes two serialisations of one intent byte-identical, which
        // makes a diff in a bug report meaningful.
        encoder.outputFormatting = [.sortedKeys]
        do {
            return try encoder.encode(
                CommandEnvelope(operation: operation.rawValue, payload: payload)
            )
        } catch {
            // The realistic cause is a non-finite coordinate reaching a placement
            // proposal. Report it in the same vocabulary as a server rejection.
            throw JarvaidsError.invalidRequest(APIErrorBody(
                code: .invalidObject,
                message: "The command payload could not be encoded as JSON: \(error)"
            ))
        }
    }
}

// MARK: - Payloads

// One struct per operation. Explicit coding keys throughout: the server rejects unknown
// fields outright, so a mistyped key is a hard failure rather than a silently dropped one.

private struct InvitePayload: Encodable, Sendable {
    let name: String
    let token: ActorToken
    let role: String?
}

private struct RolePayload: Encodable, Sendable {
    let actorID: ActorID
    let role: String

    private enum CodingKeys: String, CodingKey {
        case role
        case actorID = "actor_id"
    }
}

private struct PolicyPayload: Encodable, Sendable {
    let policyVersion: Int

    private enum CodingKeys: String, CodingKey {
        case policyVersion = "policy_version"
    }
}

private struct EmptyPayload: Encodable, Sendable {}

private struct TextPayload: Encodable, Sendable {
    let text: String
}

private struct ImagePayload: Encodable, Sendable {
    let mime: String
    let base64: String
    let regions: [SourceRegion]
}

private struct SourceCorrectionPayload: Encodable, Sendable {
    let sourceID: RecordID
    let expectedRevision: Int
    let text: String

    private enum CodingKeys: String, CodingKey {
        case text
        case sourceID = "source_id"
        case expectedRevision = "expected_revision"
    }
}

private struct SourceRegionsPayload: Encodable, Sendable {
    let sourceID: RecordID
    let expectedRevision: Int
    let regions: [SourceRegion]

    private enum CodingKeys: String, CodingKey {
        case regions
        case sourceID = "source_id"
        case expectedRevision = "expected_revision"
    }
}

private struct QueuePayload: Encodable, Sendable {
    let sourceID: RecordID
    let expectedRevision: Int

    private enum CodingKeys: String, CodingKey {
        case sourceID = "source_id"
        case expectedRevision = "expected_revision"
    }
}

private struct JobCancelPayload: Encodable, Sendable {
    let jobID: RecordID
    let expectedRevision: Int

    private enum CodingKeys: String, CodingKey {
        case jobID = "job_id"
        case expectedRevision = "expected_revision"
    }
}

private struct ProposalCreatePayload: Encodable, Sendable {
    let proposalKind: String
    let text: String
    let refs: [Reference]
    let positions: [Position]?
    let regionID: RegionID?

    private enum CodingKeys: String, CodingKey {
        case text, refs, positions
        case proposalKind = "proposal_kind"
        case regionID = "region_id"
    }
}

private struct ProposalEditPayload: Encodable, Sendable {
    let proposalID: RecordID
    let expectedRevision: Int
    let text: String
    let refs: [Reference]

    private enum CodingKeys: String, CodingKey {
        case text, refs
        case proposalID = "proposal_id"
        case expectedRevision = "expected_revision"
    }
}

private struct ReviewPayload: Encodable, Sendable {
    let proposalID: RecordID
    let expectedRevision: Int
    let decision: String

    private enum CodingKeys: String, CodingKey {
        case decision
        case proposalID = "proposal_id"
        case expectedRevision = "expected_revision"
    }
}

private struct ItemEditPayload: Encodable, Sendable {
    let itemID: RecordID
    let expectedRevision: Int
    let text: String
    let refs: [Reference]

    private enum CodingKeys: String, CodingKey {
        case text, refs
        case itemID = "item_id"
        case expectedRevision = "expected_revision"
    }
}

private struct ItemUndoPayload: Encodable, Sendable {
    let itemID: RecordID
    let expectedRevision: Int
    let restoreRevision: Int

    private enum CodingKeys: String, CodingKey {
        case itemID = "item_id"
        case expectedRevision = "expected_revision"
        case restoreRevision = "restore_revision"
    }
}

private struct ExportPayload: Encodable, Sendable {
    /// API.md requires an explicit boolean here, so there is no default.
    let includeUnresolved: Bool

    private enum CodingKeys: String, CodingKey {
        case includeUnresolved = "include_unresolved"
    }
}

// MARK: - Factories

// Every factory takes an `Entity` rather than a loose id and revision, so the revision
// sent as `expected_revision` is always the one attached to the record the caller
// actually fetched and displayed.

extension CommandIntent where Result == MembershipResult {
    /// Facilitator only. The invitee's token is generated by whoever is inviting and
    /// handed over out of band; the server never sends it back.
    public static func inviteParticipant(
        name: String,
        token: ActorToken,
        role: ActorRole = .participant
    ) throws -> CommandIntent {
        try CommandIntent(.participantInvite, InvitePayload(
            name: name, token: token, role: role.rawValue
        ))
    }

    /// Facilitator only. The server refuses to demote the last facilitator.
    public static func changeRole(of actor: ActorID, to role: ActorRole) throws -> CommandIntent {
        try CommandIntent(.participantRole, RolePayload(actorID: actor, role: role.rawValue))
    }
}

extension CommandIntent where Result == ConsentResult {
    /// Each actor acknowledges for themselves, viewers included. The version must be the
    /// one currently in force; an out-of-date version comes back as a `policyChanged`
    /// conflict carrying the current number.
    public static func acknowledgeConsent(policyVersion: Int) throws -> CommandIntent {
        try CommandIntent(.consentAcknowledge, PolicyPayload(policyVersion: policyVersion))
    }
}

extension CommandIntent where Result == SessionStateResult {
    /// Facilitator only, and only once every current member has acknowledged.
    public static func activateSession(policyVersion: Int) throws -> CommandIntent {
        try CommandIntent(.sessionActivate, PolicyPayload(policyVersion: policyVersion))
    }

    /// Any actor may pause, viewers included. Pausing revokes acknowledgements, so
    /// capture cannot silently resume afterwards.
    public static func pauseSession() throws -> CommandIntent {
        try CommandIntent(.sessionPause, EmptyPayload())
    }

    /// Facilitator only. A closed session is read-only apart from export and deletion.
    public static func closeSession() throws -> CommandIntent {
        try CommandIntent(.sessionClose, EmptyPayload())
    }
}

extension CommandIntent where Result == HeartbeatResult {
    /// Facilitator only. Renews the five-minute lease. See `FacilitatorHeartbeat`.
    public static func heartbeat() throws -> CommandIntent {
        try CommandIntent(.sessionHeartbeat, EmptyPayload())
    }
}

extension CommandIntent where Result == SourceTextResult {
    /// A typed note. Creates the source and a content proposal in one command, because
    /// even something a person typed is a proposal until a facilitator accepts it.
    public static func addTextSource(_ text: String) throws -> CommandIntent {
        try CommandIntent(.sourceText, TextPayload(text: text))
    }
}

extension CommandIntent where Result == Record {
    /// A photograph plus the crops a person drew on it. The regions are required: the
    /// backend does no region detection, so nothing is extracted from a crop nobody drew.
    public static func addImageSource(
        mimeType: String,
        imageData: Data,
        regions: [SourceRegion]
    ) throws -> CommandIntent {
        try validate(regions: regions)
        return try CommandIntent(.sourceImage, ImagePayload(
            mime: mimeType,
            base64: imageData.base64EncodedString(),
            regions: regions
        ))
    }

    /// Queue fixture or provider extraction for one image source. Returns a job record.
    /// A deliberate second attempt is a new command and a new job, never a hidden retry.
    public static func queueExtraction(for source: Entity<SourceData>) throws -> CommandIntent {
        try CommandIntent(.extractionQueue, QueuePayload(
            sourceID: source.id, expectedRevision: source.revision.value
        ))
    }

    public static func cancelJob(_ job: Entity<JobData>) throws -> CommandIntent {
        try CommandIntent(.jobCancel, JobCancelPayload(
            jobID: job.id, expectedRevision: job.revision.value
        ))
    }

    /// A content proposal. `refs` must point at current sources or current accepted items.
    public static func proposeContent(
        text: String,
        refs: [Reference]
    ) throws -> CommandIntent {
        try CommandIntent(.proposalCreate, ProposalCreatePayload(
            proposalKind: ProposalKind.content.rawValue,
            text: text, refs: refs, positions: nil, regionID: nil
        ))
    }

    /// A person transcribing one crop by hand, which is the path that stays open when a
    /// model is unavailable or returned unreadable output. Exactly one image source ref.
    public static func transcribeRegion(
        _ regionID: RegionID,
        of source: Entity<SourceData>,
        text: String
    ) throws -> CommandIntent {
        try CommandIntent(.proposalCreate, ProposalCreatePayload(
            proposalKind: ProposalKind.content.rawValue,
            text: text,
            refs: [source.reference],
            positions: nil,
            regionID: regionID
        ))
    }

    /// A relationship between accepted items. API.md: relationships target accepted
    /// items, not proposals, so the caller passes items rather than loose references.
    public static func proposeRelationship(
        text: String,
        between items: [Entity<ItemData>]
    ) throws -> CommandIntent {
        try CommandIntent(.proposalCreate, ProposalCreatePayload(
            proposalKind: ProposalKind.relationship.rawValue,
            text: text,
            refs: items.map(\.reference),
            positions: nil,
            regionID: nil
        ))
    }

    /// A layout. Positions are board coordinates, and there must be exactly one position
    /// per referenced item. Changing which items a placement covers needs a fresh
    /// proposal, not an edit, which is why this takes the items and positions together.
    public static func proposePlacement(
        text: String,
        positions: [(item: Entity<ItemData>, x: Double, y: Double)]
    ) throws -> CommandIntent {
        let coordinates = positions.map { Position(id: $0.item.id, x: $0.x, y: $0.y) }
        try validate(positions: coordinates)
        return try CommandIntent(.proposalCreate, ProposalCreatePayload(
            proposalKind: ProposalKind.placement.rawValue,
            text: text,
            refs: positions.map { $0.item.reference },
            positions: coordinates,
            regionID: nil
        ))
    }

    /// Edit a proposal's text or references before review. Author or facilitator only.
    public static func editProposal(
        _ proposal: Entity<ProposalData>,
        text: String,
        refs: [Reference]
    ) throws -> CommandIntent {
        try CommandIntent(.proposalEdit, ProposalEditPayload(
            proposalID: proposal.id,
            expectedRevision: proposal.revision.value,
            text: text,
            refs: refs
        ))
    }

    /// Freeze an export. Facilitator only, and allowed on a closed session.
    ///
    /// `includeUnresolved` has no default because API.md requires an explicit choice:
    /// false lists what was left out, true includes and labels it. Either is defensible,
    /// neither should be picked by a library on the team's behalf.
    public static func createExport(includeUnresolved: Bool) throws -> CommandIntent {
        try CommandIntent(.exportCreate, ExportPayload(includeUnresolved: includeUnresolved))
    }
}

extension CommandIntent where Result == SourceChangeResult {
    /// Correct a typed source. Everything downstream of it goes stale, transitively, and
    /// the result says which records those were.
    public static func correctSource(
        _ source: Entity<SourceData>,
        text: String
    ) throws -> CommandIntent {
        try CommandIntent(.sourceCorrect, SourceCorrectionPayload(
            sourceID: source.id, expectedRevision: source.revision.value, text: text
        ))
    }

    /// Replace the whole region list on an image source. API.md: this "replaces the
    /// complete region list", so callers pass every region they want to keep, and
    /// existing dependencies go stale even if only one crop moved.
    public static func replaceRegions(
        on source: Entity<SourceData>,
        with regions: [SourceRegion]
    ) throws -> CommandIntent {
        try validate(regions: regions)
        return try CommandIntent(.sourceRegions, SourceRegionsPayload(
            sourceID: source.id, expectedRevision: source.revision.value, regions: regions
        ))
    }
}

extension CommandIntent where Result == ReviewResult {
    /// The moment a proposal becomes the team's work, or does not. Facilitator only.
    ///
    /// The revision travels inside the `Entity`, so it is the revision of the proposal
    /// the facilitator was actually shown.
    public static func review(
        _ proposal: Entity<ProposalData>,
        decision: ReviewDecision
    ) throws -> CommandIntent {
        try CommandIntent(.proposalReview, ReviewPayload(
            proposalID: proposal.id,
            expectedRevision: proposal.revision.value,
            decision: decision.rawValue
        ))
    }
}

extension CommandIntent where Result == ItemChangeResult {
    /// API.md: "`item.edit` is an explicit facilitator review of current refs; it must
    /// not run automatically when source revisions change." Nothing in this package calls
    /// it on its own, and nothing should.
    public static func editItem(
        _ item: Entity<ItemData>,
        text: String,
        refs: [Reference]
    ) throws -> CommandIntent {
        try CommandIntent(.itemEdit, ItemEditPayload(
            itemID: item.id, expectedRevision: item.revision.value, text: text, refs: refs
        ))
    }

    /// Undo produces a new revision rather than rewinding history, and it never rewinds
    /// the session as a whole.
    public static func undoItem(
        _ item: Entity<ItemData>,
        to target: UndoTarget
    ) throws -> CommandIntent {
        try CommandIntent(.itemUndo, ItemUndoPayload(
            itemID: item.id,
            expectedRevision: item.revision.value,
            restoreRevision: target.wireValue
        ))
    }
}

// MARK: - Local validation

// The server validates all of this too. Checking locally saves a round trip, and in the
// image case it saves uploading several megabytes to be told a box was off the edge.

private func validate(regions: [SourceRegion]) throws {
    guard (1...60).contains(regions.count) else {
        throw JarvaidsError.invalidRequest(APIErrorBody(
            code: .invalidRegions,
            message: "Supply between 1 and 60 crop regions."
        ))
    }
    guard Set(regions.map(\.id)).count == regions.count else {
        throw JarvaidsError.invalidRequest(APIErrorBody(
            code: .duplicateRegion,
            message: "Region IDs must be unique within a source."
        ))
    }
    if let bad = regions.first(where: { !$0.box.isValid }) {
        throw JarvaidsError.invalidRequest(APIErrorBody(
            code: .invalidBox,
            message: "Region \(bad.id) is not a positive box inside the image."
        ))
    }
}

private func validate(positions: [Position]) throws {
    guard !positions.isEmpty else {
        throw JarvaidsError.invalidRequest(APIErrorBody(
            code: .invalidPositions,
            message: "A placement proposal needs a position for every item it covers."
        ))
    }
    guard Set(positions.map(\.id)).count == positions.count else {
        throw JarvaidsError.invalidRequest(APIErrorBody(
            code: .invalidPositions,
            message: "Each item may appear in a placement only once."
        ))
    }
    let limit = 100_000.0
    for position in positions where !position.x.isFinite || !position.y.isFinite
        || abs(position.x) > limit || abs(position.y) > limit {
        throw JarvaidsError.invalidRequest(APIErrorBody(
            code: .invalidPositions,
            message: "Board coordinates must be finite and within plus or minus 100000."
        ))
    }
}
