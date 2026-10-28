//
//  Models.swift
//  JarvaidsCore
//
//  The wire shapes, written against payloads captured from a running server rather than
//  from the prose alone. Where the prose and the payload disagree the payload wins, and
//  the disagreement is noted in a comment so the next reader does not "fix" it back.
//
//  Coding keys are written out by hand everywhere. A `.convertFromSnakeCase` decoder
//  strategy would have been shorter, but it also rewrites the keys of any dictionary it
//  decodes, which would silently mangle `error.details.current_policy_version` into
//  something no lookup finds. Verbose and literal is the safer trade here.
//

import Foundation

// MARK: - References

/// API.md: references are `{id, revision}` and "must point to current sources or current
/// accepted items in the same session". Historical revisions can be inspected but are not
/// valid dependencies for a new acceptance.
public struct Reference: Hashable, Sendable, Codable {
    public let id: RecordID
    public let revision: Revision

    public init(id: RecordID, revision: Revision) {
        self.id = id
        self.revision = revision
    }

    private enum CodingKeys: String, CodingKey {
        case id, revision
    }
}

/// The manifest form of a reference, which also carries the record kind.
public struct ManifestReference: Hashable, Sendable, Decodable {
    public let id: RecordID
    public let kind: RecordKind
    public let revision: Revision

    private enum CodingKeys: String, CodingKey {
        case id, kind, revision
    }
}

// MARK: - Session

public struct Session: Hashable, Sendable, Decodable, Identifiable {
    public let id: SessionID
    public let title: String
    public let state: SessionState
    /// Bumped by anything that changes who is in the room. A bump invalidates every
    /// existing acknowledgement, which is why the roster and the agreement move together.
    public let policyVersion: Int
    /// The session's event cursor high-water mark. Compare against a locally held cursor
    /// to decide whether a refetch is needed at all.
    public let seq: Int
    public let created: Timestamp
    public let expires: Timestamp
    /// When the facilitator lease runs out. Renewed by `session.heartbeat`.
    public let lease: Timestamp
    public let deletedAt: Timestamp?

    private enum CodingKeys: String, CodingKey {
        case id, title, state, seq, created, expires, lease
        case policyVersion = "policy_version"
        case deletedAt = "deleted_at"
    }
}

/// One actor in the session. The wire calls these `members`, not `actors`, although
/// API.md's prose says "returns session, actors and public records".
public struct Member: Hashable, Sendable, Decodable, Identifiable {
    public let id: ActorID
    public let name: String
    public let role: ActorRole
    /// The policy version this member last acknowledged. Zero means never.
    public let consentVersion: Int

    private enum CodingKeys: String, CodingKey {
        case id, name, role
        case consentVersion = "consent_version"
    }

    /// Activation requires every current member, viewers included, to be caught up.
    public func hasAcknowledged(policyVersion: Int) -> Bool {
        consentVersion == policyVersion
    }
}

// MARK: - Records

/// One record envelope: `{id, kind, revision, data}`.
///
/// The payload is decoded into a concrete type chosen by `kind`. A kind this build does
/// not know is kept as raw JSON rather than throwing, because one unfamiliar record must
/// not cost the caller the whole snapshot.
public struct Record: Sendable, Decodable, Identifiable {
    public let id: RecordID
    public let kind: RecordKind
    public let revision: Revision
    public let payload: Payload

    public enum Payload: Sendable {
        case source(SourceData)
        case proposal(ProposalData)
        case item(ItemData)
        case job(JobData)
        case export(ExportRecordData)
        case unrecognised(JSONValue)
    }

    private enum CodingKeys: String, CodingKey {
        case id, kind, revision, data
    }

    public init(from decoder: any Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        self.id = try container.decode(RecordID.self, forKey: .id)
        self.kind = try container.decode(RecordKind.self, forKey: .kind)
        self.revision = try container.decode(Revision.self, forKey: .revision)
        switch kind {
        case .source: self.payload = .source(try container.decode(SourceData.self, forKey: .data))
        case .proposal: self.payload = .proposal(try container.decode(ProposalData.self, forKey: .data))
        case .item: self.payload = .item(try container.decode(ItemData.self, forKey: .data))
        case .job: self.payload = .job(try container.decode(JobData.self, forKey: .data))
        case .export: self.payload = .export(try container.decode(ExportRecordData.self, forKey: .data))
        case .unknown: self.payload = .unrecognised(try container.decode(JSONValue.self, forKey: .data))
        }
    }

    // Typed views. These return `Entity`, which carries the id and revision alongside the
    // data, because almost every command needs the revision the person was shown.

    public var source: Entity<SourceData>? {
        guard case .source(let data) = payload else { return nil }
        return Entity(id: id, revision: revision, data: data)
    }

    public var proposal: Entity<ProposalData>? {
        guard case .proposal(let data) = payload else { return nil }
        return Entity(id: id, revision: revision, data: data)
    }

    public var item: Entity<ItemData>? {
        guard case .item(let data) = payload else { return nil }
        return Entity(id: id, revision: revision, data: data)
    }

    public var job: Entity<JobData>? {
        guard case .job(let data) = payload else { return nil }
        return Entity(id: id, revision: revision, data: data)
    }

    public var export: Entity<ExportRecordData>? {
        guard case .export(let data) = payload else { return nil }
        return Entity(id: id, revision: revision, data: data)
    }
}

/// A record narrowed to one payload type, keeping the identity and revision attached.
/// Commands take an `Entity` rather than a loose id plus revision so that the two cannot
/// be paired up from different fetches by accident.
public struct Entity<Data: Sendable>: Sendable, Identifiable {
    public let id: RecordID
    public let revision: Revision
    public let data: Data

    public init(id: RecordID, revision: Revision, data: Data) {
        self.id = id
        self.revision = revision
        self.data = data
    }

    /// The reference form of this entity, for use in a proposal's `refs`.
    public var reference: Reference { Reference(id: id, revision: revision) }
}

// MARK: - Sources

/// A normalised crop box: `[x, y, width, height]`, all inside `[0, 1]`, relative to the
/// original image and not to anything the client happens to be displaying.
public struct RegionBox: Hashable, Sendable, Codable {
    public let x: Double
    public let y: Double
    public let width: Double
    public let height: Double

    public init(x: Double, y: Double, width: Double, height: Double) {
        self.x = x
        self.y = y
        self.width = width
        self.height = height
    }

    /// The server validates this too, but failing locally saves an upload of several
    /// megabytes to learn that one box was off the edge.
    public var isValid: Bool {
        width > 0 && height > 0
            && x >= 0 && y >= 0
            && x + width <= 1 && y + height <= 1
            && [x, y, width, height].allSatisfy { $0.isFinite }
    }

    public init(from decoder: any Decoder) throws {
        var container = try decoder.unkeyedContainer()
        self.x = try container.decode(Double.self)
        self.y = try container.decode(Double.self)
        self.width = try container.decode(Double.self)
        self.height = try container.decode(Double.self)
    }

    public func encode(to encoder: any Encoder) throws {
        var container = encoder.unkeyedContainer()
        try container.encode(x)
        try container.encode(y)
        try container.encode(width)
        try container.encode(height)
    }
}

public struct SourceRegion: Hashable, Sendable, Codable {
    public let id: RegionID
    public let box: RegionBox

    public init(id: RegionID, box: RegionBox) {
        self.id = id
        self.box = box
    }

    private enum CodingKeys: String, CodingKey {
        case id, box
    }
}

/// Text and image sources share an envelope and differ in which fields are present.
/// One struct with optionals matches the wire; `content` gives the tidy view.
public struct SourceData: Sendable, Decodable {
    public let type: SourceType
    public let authorID: ActorID
    public let origin: RecordOrigin
    public let createdAt: Timestamp
    public let lastEditor: ActorID?

    // Text sources only.
    public let text: String?

    // Image sources only. Snapshot and record responses never include the base64 bytes;
    // fetch them from the media endpoint instead.
    public let mime: String?
    public let width: Int?
    public let height: Int?
    public let byteCount: Int?
    public let regions: [SourceRegion]?

    private enum CodingKeys: String, CodingKey {
        case type, origin, text, mime, width, height, regions
        case authorID = "author_id"
        case createdAt = "created_at"
        case lastEditor = "last_editor"
        case byteCount = "byte_count"
    }

    public enum Content: Sendable {
        case text(String)
        case image(ImageInfo)
        case unrecognised
    }

    public struct ImageInfo: Hashable, Sendable {
        public let mime: String
        public let width: Int
        public let height: Int
        public let byteCount: Int
        public let regions: [SourceRegion]
    }

    public var content: Content {
        switch type {
        case .text:
            return .text(text ?? "")
        case .image:
            guard let mime, let width, let height, let byteCount else { return .unrecognised }
            return .image(ImageInfo(
                mime: mime, width: width, height: height,
                byteCount: byteCount, regions: regions ?? []
            ))
        case .unknown:
            return .unrecognised
        }
    }
}

// MARK: - Proposals

/// Board coordinates for a placement proposal. API.md: "Positions are board coordinates,
/// not normalized crop coordinates", bounded to plus or minus 100000.
public struct Position: Hashable, Sendable, Codable {
    public let id: RecordID
    public let x: Double
    public let y: Double

    public init(id: RecordID, x: Double, y: Double) {
        self.id = id
        self.x = x
        self.y = y
    }

    private enum CodingKeys: String, CodingKey {
        case id, x, y
    }
}

/// Everything a model made is a proposal until a facilitator accepts it. That is the
/// product's central rule, and this is the type it lives in.
public struct ProposalData: Sendable, Decodable {
    public let proposalKind: ProposalKind
    public let text: String
    public let refs: [Reference]
    public let origin: RecordOrigin
    public let authorID: ActorID
    /// Wire field is `status`; API.md's prose calls it the proposal state.
    public let status: ProposalState
    public let policyVersion: Int
    public let createdAt: Timestamp

    /// Present once reviewed.
    public let reviewedBy: ActorID?
    /// Present on an accepted proposal, pointing at the item it became.
    public let itemID: RecordID?

    /// Placement proposals only.
    public let positions: [Position]?

    /// Crop provenance, present on content proposals tied to one image region.
    public let regionID: RegionID?
    public let readingStatus: ReadingStatus?

    /// Model provenance. API.md: display these wherever available and never hide them.
    public let provider: String?
    public let model: String?
    public let synthetic: Bool?

    private enum CodingKeys: String, CodingKey {
        case text, refs, origin, status, positions, provider, model, synthetic
        case proposalKind = "proposal_kind"
        case authorID = "author_id"
        case policyVersion = "policy_version"
        case createdAt = "created_at"
        case reviewedBy = "reviewed_by"
        case itemID = "item_id"
        case regionID = "region_id"
        case readingStatus = "reading_status"
    }

    /// True when this content came out of a model or fixture and has not been rewritten
    /// by a person. Drives the provisional styling the flowchart calls "dashed".
    public var isMachineMade: Bool { origin.isMachineMade || synthetic == true }

    /// The server refuses to accept unreadable model output, so the UI should refuse to
    /// offer the accept control for it and offer an edit instead.
    public var needsHumanTextBeforeAcceptance: Bool {
        readingStatus?.requiresHumanTextBeforeAcceptance ?? false
    }
}

// MARK: - Items

/// An accepted proposal. Items are the team's work; proposals are not yet.
public struct ItemData: Sendable, Decodable {
    public let itemKind: ItemKind
    public let text: String
    public let refs: [Reference]
    public let origin: RecordOrigin
    public let status: ItemStatus
    public let proposalID: RecordID
    public let acceptedBy: ActorID
    public let lastEditor: ActorID
    public let createdAt: Timestamp

    public let positions: [Position]?

    /// Provenance is copied forward from the proposal. API.md: "Human editing does not
    /// erase fixture/model origin."
    public let regionID: RegionID?
    public let readingStatus: ReadingStatus?
    public let provider: String?
    public let model: String?
    public let synthetic: Bool?

    /// Set by `item.undo`. Zero means the item was marked undone rather than restored.
    public let restoredFromRevision: Int?

    private enum CodingKeys: String, CodingKey {
        case text, refs, origin, status, positions, provider, model, synthetic
        case itemKind = "item_kind"
        case proposalID = "proposal_id"
        case acceptedBy = "accepted_by"
        case lastEditor = "last_editor"
        case createdAt = "created_at"
        case regionID = "region_id"
        case readingStatus = "reading_status"
        case restoredFromRevision = "restored_from_revision"
    }

    public var isMachineMade: Bool { origin.isMachineMade || synthetic == true }
}

// MARK: - Jobs

public struct JobUsage: Hashable, Sendable, Decodable {
    /// Null when unknown. The backend README is firm that unknown cost stays null and is
    /// never reported as a made-up zero, so this stays optional rather than defaulting.
    public let cost: Double?
    public let currency: String?
    public let inputUnits: Int?
    public let outputUnits: Int?

    private enum CodingKeys: String, CodingKey {
        case cost, currency
        case inputUnits = "input_units"
        case outputUnits = "output_units"
    }
}

public struct JobData: Sendable, Decodable {
    public let status: JobState
    public let refs: [Reference]
    public let policyVersion: Int
    public let authorID: ActorID
    public let createdAt: Timestamp
    /// Sixty seconds after creation. Results arriving later are discarded by the server.
    public let deadline: Timestamp
    public let attempts: Int
    public let adapter: String
    public let synthetic: Bool
    /// A short failure code such as `deadline_exceeded`, `user_cancelled` or
    /// `source_changed`, not a message for a person.
    public let error: String?

    public let startedAt: Timestamp?
    public let durationMilliseconds: Double?
    public let provider: String?
    public let model: String?
    /// The proposals the job produced, once it has succeeded.
    public let proposalIDs: [RecordID]?
    public let usage: JobUsage?

    private enum CodingKeys: String, CodingKey {
        case status, refs, attempts, adapter, synthetic, error, deadline, provider, model, usage
        case policyVersion = "policy_version"
        case authorID = "author_id"
        case createdAt = "created_at"
        case startedAt = "started_at"
        case durationMilliseconds = "duration_ms"
        case proposalIDs = "proposal_ids"
    }

    public var isActive: Bool { status.isActive }
}

// MARK: - Exports

public struct ExportManifest: Sendable, Decodable {
    public let sessionID: SessionID
    public let sessionTitle: String
    /// The event sequence the export was frozen at.
    public let snapshotSeq: Int
    public let policyVersion: Int
    public let createdAt: Timestamp
    public let included: [ManifestReference]
    public let unresolvedCount: Int
    public let includedUnresolved: Bool
    public let omittedIDs: [RecordID]
    /// Always false today: exports never carry image bytes.
    public let sourceMediaIncluded: Bool
    /// Plain-language boundary statements written by the server. Show them, do not
    /// paraphrase them: they are the honest limits of what an export is.
    public let audience: String
    public let boundary: String

    private enum CodingKeys: String, CodingKey {
        case included, audience, boundary
        case sessionID = "session_id"
        case sessionTitle = "session_title"
        case snapshotSeq = "snapshot_seq"
        case policyVersion = "policy_version"
        case createdAt = "created_at"
        case unresolvedCount = "unresolved_count"
        case includedUnresolved = "included_unresolved"
        case omittedIDs = "omitted_ids"
        case sourceMediaIncluded = "source_media_included"
    }
}

/// What an export record looks like inside a snapshot: the manifest only.
/// API.md: "Snapshot exports expose their manifest, not the full export."
public struct ExportRecordData: Sendable, Decodable {
    public let manifest: ExportManifest

    private enum CodingKeys: String, CodingKey {
        case manifest
    }
}

/// What `GET /exports/{id}?format=json` returns: the full frozen document.
///
/// Note the shape difference from every other read: this is the export body directly,
/// with no `{id, kind, revision, data}` envelope around it.
public struct ExportDocument: Sendable, Decodable {
    public let manifest: ExportManifest
    public let records: [Record]
    public let markdown: String

    private enum CodingKeys: String, CodingKey {
        case manifest, records, markdown
    }
}

// MARK: - Snapshot

public struct SessionSnapshot: Sendable, Decodable {
    public let session: Session
    /// Which member the calling credential is. Needed to know what this device may do.
    public let actorID: ActorID
    public let members: [Member]
    public let records: [Record]

    private enum CodingKeys: String, CodingKey {
        case session, members, records
        case actorID = "actor_id"
    }

    public var viewer: Member? { members.first { $0.id == actorID } }
    public var role: ActorRole { viewer?.role ?? .unknown("absent") }

    /// Activation requires every current member to have acknowledged the current policy.
    public var membersAwaitingAcknowledgement: [Member] {
        members.filter { !$0.hasAcknowledged(policyVersion: session.policyVersion) }
    }

    public var isReadyToActivate: Bool {
        session.state == .draft && membersAwaitingAcknowledgement.isEmpty
    }
}

/// What every read returns once the session is gone. API.md: "deleted session returns
/// receipt to retained facilitator credential".
public struct DeletionReceipt: Sendable, Decodable {
    public let sessionID: SessionID
    public let state: SessionState
    public let deletedAt: Timestamp?
    /// Present on the DELETE response, absent on a GET of a deleted session.
    public let replayed: Bool?
    /// Present on a first DELETE only, absent on a replay.
    public let boundary: String?
    /// Present on a GET of a deleted session only.
    public let contentAvailable: Bool?

    private enum CodingKeys: String, CodingKey {
        case state, replayed, boundary
        case sessionID = "session_id"
        case deletedAt = "deleted_at"
        case contentAvailable = "content_available"
    }
}

/// `GET /api/sessions/{sid}` returns two different documents depending on whether the
/// session still exists, and both come back as HTTP 200. Modelling that as one enum
/// rather than an optional-riddled struct keeps the caller honest about the difference.
public enum SnapshotResponse: Sendable {
    case live(SessionSnapshot)
    case deleted(DeletionReceipt)
}

// MARK: - Events

/// API.md: events carry "change metadata, not a patch stream". Poll them, then refetch
/// the snapshot. The event body is never enough to update state on its own.
public struct SessionEvent: Sendable, Decodable, Identifiable {
    public let seq: Int
    public let type: EventType
    /// Either a member's ID or the literal string `system` for events the worker raised,
    /// which is why this is not validated as an identifier.
    public let actorID: ActorID
    public let created: Timestamp
    public let data: EventData

    public var id: Int { seq }

    private enum CodingKeys: String, CodingKey {
        case seq, type, created, data
        case actorID = "actor_id"
    }

    public var isSystemEvent: Bool { actorID.rawValue == "system" }

    public struct EventData: Sendable, Decodable {
        public let recordIDs: [RecordID]
        public let jobID: RecordID?
        /// A short failure code on job events, not a message for a person.
        public let code: String?

        private enum CodingKeys: String, CodingKey {
            case code
            case recordIDs = "record_ids"
            case jobID = "job_id"
        }

        public init(from decoder: any Decoder) throws {
            let container = try decoder.container(keyedBy: CodingKeys.self)
            self.recordIDs = try container.decodeIfPresent([RecordID].self, forKey: .recordIDs) ?? []
            self.jobID = try container.decodeIfPresent(RecordID.self, forKey: .jobID)
            self.code = try container.decodeIfPresent(String.self, forKey: .code)
        }
    }
}

public struct EventPage: Sendable, Decodable {
    public let events: [SessionEvent]
    /// The cursor to pass as `after` next time.
    public let nextAfter: Int
    /// The session's current sequence number, so a caller can tell how far behind it is.
    public let currentSeq: Int
    /// API.md: the page holds up to 200 events; poll again immediately while this is true.
    public let hasMore: Bool

    private enum CodingKeys: String, CodingKey {
        case events
        case nextAfter = "next_after"
        case currentSeq = "current_seq"
        case hasMore = "has_more"
    }
}

// MARK: - Health

public struct HealthStatus: Sendable, Decodable {
    public let status: String
    public let version: String
    public let adapter: String
    /// False on this backend, always. There is no OCR and no speech, here or in the
    /// client. Show it rather than assuming it.
    public let liveOCR: Bool
    public let storage: String?
    public let deployment: String?

    private enum CodingKeys: String, CodingKey {
        case status, version, adapter, storage, deployment
        case liveOCR = "live_ocr"
    }
}

// MARK: - Command envelopes

/// Every command response: `{result, seq, replayed}`.
///
/// `replayed` is true when the server recognised the request ID and returned the stored
/// result rather than acting again. That is success, not a problem to report.
public struct CommandResponse<Result: Sendable & Decodable>: Sendable, Decodable {
    public let result: Result
    public let seq: Int
    public let replayed: Bool

    private enum CodingKeys: String, CodingKey {
        case result, seq, replayed
    }
}

public struct SessionCreationResult: Sendable, Decodable {
    public let sessionID: SessionID
    public let actorID: ActorID
    public let state: SessionState
    public let replayed: Bool

    private enum CodingKeys: String, CodingKey {
        case state, replayed
        case sessionID = "session_id"
        case actorID = "actor_id"
    }
}

/// Returned by `session.activate`, `session.pause` and `session.close`.
public struct SessionStateResult: Sendable, Decodable {
    public let state: SessionState
    /// Pause, close and roster changes bump this, which invalidates every acknowledgement.
    public let policyVersion: Int

    private enum CodingKeys: String, CodingKey {
        case state
        case policyVersion = "policy_version"
    }
}

/// Returned by `participant.invite` and `participant.role`.
public struct MembershipResult: Sendable, Decodable {
    public let actorID: ActorID
    public let role: ActorRole
    public let state: SessionState
    public let policyVersion: Int

    private enum CodingKeys: String, CodingKey {
        case role, state
        case actorID = "actor_id"
        case policyVersion = "policy_version"
    }
}

public struct ConsentResult: Sendable, Decodable {
    public let actorID: ActorID
    public let policyVersion: Int
    public let acknowledged: Bool

    private enum CodingKeys: String, CodingKey {
        case acknowledged
        case actorID = "actor_id"
        case policyVersion = "policy_version"
    }
}

public struct HeartbeatResult: Sendable, Decodable {
    /// How long the renewed lease lasts. The server sends 300.
    public let leaseSeconds: Int

    private enum CodingKeys: String, CodingKey {
        case leaseSeconds = "lease_seconds"
    }
}

/// `source.text` creates the source and its first proposal in one command, because a
/// typed note is still a proposal until someone accepts it.
public struct SourceTextResult: Sendable, Decodable {
    public let source: Record
    public let proposal: Record

    private enum CodingKeys: String, CodingKey {
        case source, proposal
    }
}

/// Returned by `source.correct` and `source.regions`. `invalidated` lists the records
/// that just went stale, transitively. Show them: API.md asks for stale dependencies to
/// be visible, not silently repaired.
public struct SourceChangeResult: Sendable, Decodable {
    public let source: Record
    public let invalidated: [RecordID]

    private enum CodingKeys: String, CodingKey {
        case source, invalidated
    }
}

/// Returned by `proposal.review`. `item` is present on accept and absent on reject.
public struct ReviewResult: Sendable, Decodable {
    public let proposal: Record
    public let item: Record?

    private enum CodingKeys: String, CodingKey {
        case proposal, item
    }
}

/// Returned by `item.edit` and `item.undo`.
public struct ItemChangeResult: Sendable, Decodable {
    public let item: Record
    public let invalidated: [RecordID]

    private enum CodingKeys: String, CodingKey {
        case item, invalidated
    }
}

// MARK: - Media

public struct SourceMedia: Sendable {
    public let bytes: Data
    public let mimeType: String?

    public init(bytes: Data, mimeType: String?) {
        self.bytes = bytes
        self.mimeType = mimeType
    }
}
