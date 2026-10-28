//
//  Enums.swift
//  JarvaidsCore
//
//  Every state the API names, modelled so that a value this build has never heard of
//  is carried through as `.unknown` rather than failing the decode.
//
//  The reason is operational: a snapshot is one JSON document containing every record in
//  the session. If one proposal came back with a status added by a newer server, a
//  closed enum would throw and the whole board would go blank. Carrying the raw string
//  lets the UI show "unrecognised state" for that one record and keep the rest.
//

import Foundation

// MARK: - Open enum machinery

/// A string-backed enum with a total mapping: every string maps to a case, and unknown
/// strings map to `.unknown`, so `init` cannot fail and decoding cannot throw.
public protocol OpenStringEnum: RawRepresentable, Hashable, Sendable, Codable, CustomStringConvertible
where RawValue == String {
    /// Total. Implementations must map anything unrecognised to their `.unknown` case.
    init(apiValue: String)

    /// True when this build does not recognise the value, which means the client is
    /// older than the server it is talking to. Worth surfacing rather than hiding.
    var isUnknownCase: Bool { get }
}

extension OpenStringEnum {
    public init?(rawValue: String) { self.init(apiValue: rawValue) }

    public init(from decoder: any Decoder) throws {
        self.init(apiValue: try decoder.singleValueContainer().decode(String.self))
    }

    public func encode(to encoder: any Encoder) throws {
        var container = encoder.singleValueContainer()
        try container.encode(rawValue)
    }

    public var description: String { rawValue }
}

// MARK: - Session

/// Implemented session states, per BUILD-STATUS.md: draft, active, paused, closed, deleted.
/// Readiness is not a state; it is derived from whether every current member has
/// acknowledged the current policy version.
public enum SessionState: OpenStringEnum {
    case draft
    case active
    case paused
    case closed
    case deleted
    case unknown(String)

    public init(apiValue: String) {
        switch apiValue {
        case "draft": self = .draft
        case "active": self = .active
        case "paused": self = .paused
        case "closed": self = .closed
        case "deleted": self = .deleted
        default: self = .unknown(apiValue)
        }
    }

    public var rawValue: String {
        switch self {
        case .draft: return "draft"
        case .active: return "active"
        case .paused: return "paused"
        case .closed: return "closed"
        case .deleted: return "deleted"
        case .unknown(let raw): return raw
        }
    }

    public var isUnknownCase: Bool { if case .unknown = self { return true }; return false }

    /// API.md: "Disable capture while draft/paused/closed". Only `active` accepts sources.
    public var acceptsCapture: Bool { self == .active }

    /// Whether a facilitator lease is still worth renewing. Closed and deleted sessions
    /// reject `session.heartbeat` outright, so the heartbeat stops there.
    public var acceptsHeartbeat: Bool {
        switch self {
        case .draft, .active, .paused: return true
        case .closed, .deleted, .unknown: return false
        }
    }
}

public enum ActorRole: OpenStringEnum {
    case facilitator
    case participant
    case viewer
    case unknown(String)

    public init(apiValue: String) {
        switch apiValue {
        case "facilitator": self = .facilitator
        case "participant": self = .participant
        case "viewer": self = .viewer
        default: self = .unknown(apiValue)
        }
    }

    public var rawValue: String {
        switch self {
        case .facilitator: return "facilitator"
        case .participant: return "participant"
        case .viewer: return "viewer"
        case .unknown(let raw): return raw
        }
    }

    public var isUnknownCase: Bool { if case .unknown = self { return true }; return false }

    /// Facilitator and participant may add sources and raise proposals. Viewers may only
    /// acknowledge the policy and pause, which the server enforces; this mirrors it so the
    /// UI can disable controls rather than let them fail.
    public var canEdit: Bool { self == .facilitator || self == .participant }

    /// Only a facilitator can turn a proposal into an item. That separation is the
    /// product's central rule, not a permissions detail.
    public var canReview: Bool { self == .facilitator }
}

// MARK: - Records

public enum RecordKind: OpenStringEnum {
    case source
    case proposal
    case item
    case job
    case export
    case unknown(String)

    public init(apiValue: String) {
        switch apiValue {
        case "source": self = .source
        case "proposal": self = .proposal
        case "item": self = .item
        case "job": self = .job
        case "export": self = .export
        default: self = .unknown(apiValue)
        }
    }

    public var rawValue: String {
        switch self {
        case .source: return "source"
        case .proposal: return "proposal"
        case .item: return "item"
        case .job: return "job"
        case .export: return "export"
        case .unknown(let raw): return raw
        }
    }

    public var isUnknownCase: Bool { if case .unknown = self { return true }; return false }
}

public enum SourceType: OpenStringEnum {
    case text
    case image
    case unknown(String)

    public init(apiValue: String) {
        switch apiValue {
        case "text": self = .text
        case "image": self = .image
        default: self = .unknown(apiValue)
        }
    }

    public var rawValue: String {
        switch self {
        case .text: return "text"
        case .image: return "image"
        case .unknown(let raw): return raw
        }
    }

    public var isUnknownCase: Bool { if case .unknown = self { return true }; return false }
}

/// `content`, `relationship` and `placement`. Items reuse the same vocabulary under
/// `item_kind`, so `ProposalKind` is used for both rather than duplicating it.
public enum ProposalKind: OpenStringEnum {
    case content
    case relationship
    case placement
    case unknown(String)

    public init(apiValue: String) {
        switch apiValue {
        case "content": self = .content
        case "relationship": self = .relationship
        case "placement": self = .placement
        default: self = .unknown(apiValue)
        }
    }

    public var rawValue: String {
        switch self {
        case .content: return "content"
        case .relationship: return "relationship"
        case .placement: return "placement"
        case .unknown(let raw): return raw
        }
    }

    public var isUnknownCase: Bool { if case .unknown = self { return true }; return false }
}

public typealias ItemKind = ProposalKind

/// The wire field is `status`, although API.md calls these "proposal states".
public enum ProposalState: OpenStringEnum {
    case needsReview
    case stale
    case accepted
    case rejected
    case unknown(String)

    public init(apiValue: String) {
        switch apiValue {
        case "needs_review": self = .needsReview
        case "stale": self = .stale
        case "accepted": self = .accepted
        case "rejected": self = .rejected
        default: self = .unknown(apiValue)
        }
    }

    public var rawValue: String {
        switch self {
        case .needsReview: return "needs_review"
        case .stale: return "stale"
        case .accepted: return "accepted"
        case .rejected: return "rejected"
        case .unknown(let raw): return raw
        }
    }

    public var isUnknownCase: Bool { if case .unknown = self { return true }; return false }

    /// API.md: "Accepted/rejected proposals are immutable history."
    public var isTerminal: Bool { self == .accepted || self == .rejected }

    /// A stale proposal is still waiting for a person, it just needs re-reading first.
    public var awaitsHuman: Bool { self == .needsReview || self == .stale }
}

public enum ItemStatus: OpenStringEnum {
    case accepted
    case stale
    case undone
    case unknown(String)

    public init(apiValue: String) {
        switch apiValue {
        case "accepted": self = .accepted
        case "stale": self = .stale
        case "undone": self = .undone
        default: self = .unknown(apiValue)
        }
    }

    public var rawValue: String {
        switch self {
        case .accepted: return "accepted"
        case .stale: return "stale"
        case .undone: return "undone"
        case .unknown(let raw): return raw
        }
    }

    public var isUnknownCase: Bool { if case .unknown = self { return true }; return false }

    /// Only a currently accepted item is a valid dependency for a new acceptance.
    /// API.md: references "must point to current sources or current accepted items".
    public var canBeReferenced: Bool { self == .accepted }
}

public enum JobState: OpenStringEnum {
    case queued
    case running
    case succeeded
    case failed
    case cancelled
    case unknown(String)

    public init(apiValue: String) {
        switch apiValue {
        case "queued": self = .queued
        case "running": self = .running
        case "succeeded": self = .succeeded
        case "failed": self = .failed
        case "cancelled": self = .cancelled
        default: self = .unknown(apiValue)
        }
    }

    public var rawValue: String {
        switch self {
        case .queued: return "queued"
        case .running: return "running"
        case .succeeded: return "succeeded"
        case .failed: return "failed"
        case .cancelled: return "cancelled"
        case .unknown(let raw): return raw
        }
    }

    public var isUnknownCase: Bool { if case .unknown = self { return true }; return false }

    public var isActive: Bool { self == .queued || self == .running }
    public var isTerminal: Bool { !isActive && !isUnknownCase }
}

// MARK: - Provenance

/// Where a record's content came from. `human` and the adapter name, `fixture`, are the
/// values this backend emits today; a real provider adapter would add its own.
///
/// API.md: "Human editing does not erase fixture/model origin" and "Do not hide provider
/// fixture labels". Keep this visible wherever the text is shown.
public enum RecordOrigin: OpenStringEnum {
    case human
    case fixture
    case unknown(String)

    public init(apiValue: String) {
        switch apiValue {
        case "human": self = .human
        case "fixture": self = .fixture
        default: self = .unknown(apiValue)
        }
    }

    public var rawValue: String {
        switch self {
        case .human: return "human"
        case .fixture: return "fixture"
        case .unknown(let raw): return raw
        }
    }

    public var isUnknownCase: Bool { if case .unknown = self { return true }; return false }

    /// Anything not made by a person needs a provisional label on screen.
    public var isMachineMade: Bool { self != .human }
}

/// How a crop was read. `unreadable` output must be edited by a person before it can be
/// accepted; the server rejects acceptance otherwise.
public enum ReadingStatus: OpenStringEnum {
    case readable
    case unreadable
    case humanTranscribed
    case unknown(String)

    public init(apiValue: String) {
        switch apiValue {
        case "readable": self = .readable
        case "unreadable": self = .unreadable
        case "human_transcribed": self = .humanTranscribed
        default: self = .unknown(apiValue)
        }
    }

    public var rawValue: String {
        switch self {
        case .readable: return "readable"
        case .unreadable: return "unreadable"
        case .humanTranscribed: return "human_transcribed"
        case .unknown(let raw): return raw
        }
    }

    public var isUnknownCase: Bool { if case .unknown = self { return true }; return false }

    /// API.md: "Model output marked `unreadable` must be edited with human text before acceptance."
    public var requiresHumanTextBeforeAcceptance: Bool { self == .unreadable }
}

// MARK: - Events

/// Event types are the command names plus `session.created`. Events carry change
/// metadata, not a patch stream, so the type is mostly useful for logging and for
/// deciding how loudly to tell the person that something moved.
public enum EventType: OpenStringEnum {
    case sessionCreated
    case participantInvite
    case participantRole
    case consentAcknowledge
    case sessionActivate
    case sessionPause
    case sessionClose
    case sessionHeartbeat
    case sourceText
    case sourceImage
    case sourceCorrect
    case sourceRegions
    case extractionQueue
    case jobCancel
    case jobStarted
    case jobSucceeded
    case jobFailed
    case jobCancelled
    case jobRecovered
    case sessionLeaseExpired
    case proposalCreate
    case proposalEdit
    case proposalReview
    case itemEdit
    case itemUndo
    case exportCreate
    case unknown(String)

    public init(apiValue: String) {
        switch apiValue {
        case "session.created": self = .sessionCreated
        case "participant.invite": self = .participantInvite
        case "participant.role": self = .participantRole
        case "consent.acknowledge": self = .consentAcknowledge
        case "session.activate": self = .sessionActivate
        case "session.pause": self = .sessionPause
        case "session.close": self = .sessionClose
        case "session.heartbeat": self = .sessionHeartbeat
        case "source.text": self = .sourceText
        case "source.image": self = .sourceImage
        case "source.correct": self = .sourceCorrect
        case "source.regions": self = .sourceRegions
        case "extraction.queue": self = .extractionQueue
        case "job.cancel": self = .jobCancel
        case "job.started": self = .jobStarted
        case "job.succeeded": self = .jobSucceeded
        case "job.failed": self = .jobFailed
        case "job.cancelled": self = .jobCancelled
        case "job.recovered": self = .jobRecovered
        case "session.lease_expired": self = .sessionLeaseExpired
        case "proposal.create": self = .proposalCreate
        case "proposal.edit": self = .proposalEdit
        case "proposal.review": self = .proposalReview
        case "item.edit": self = .itemEdit
        case "item.undo": self = .itemUndo
        case "export.create": self = .exportCreate
        default: self = .unknown(apiValue)
        }
    }

    public var rawValue: String {
        switch self {
        case .sessionCreated: return "session.created"
        case .participantInvite: return "participant.invite"
        case .participantRole: return "participant.role"
        case .consentAcknowledge: return "consent.acknowledge"
        case .sessionActivate: return "session.activate"
        case .sessionPause: return "session.pause"
        case .sessionClose: return "session.close"
        case .sessionHeartbeat: return "session.heartbeat"
        case .sourceText: return "source.text"
        case .sourceImage: return "source.image"
        case .sourceCorrect: return "source.correct"
        case .sourceRegions: return "source.regions"
        case .extractionQueue: return "extraction.queue"
        case .jobCancel: return "job.cancel"
        case .jobStarted: return "job.started"
        case .jobSucceeded: return "job.succeeded"
        case .jobFailed: return "job.failed"
        case .jobCancelled: return "job.cancelled"
        case .jobRecovered: return "job.recovered"
        case .sessionLeaseExpired: return "session.lease_expired"
        case .proposalCreate: return "proposal.create"
        case .proposalEdit: return "proposal.edit"
        case .proposalReview: return "proposal.review"
        case .itemEdit: return "item.edit"
        case .itemUndo: return "item.undo"
        case .exportCreate: return "export.create"
        case .unknown(let raw): return raw
        }
    }

    public var isUnknownCase: Bool { if case .unknown = self { return true }; return false }

    /// A heartbeat moves the sequence number without changing any record, so refetching
    /// the whole snapshot for one is wasted work on a meeting-room network.
    public var impliesRecordChange: Bool { self != .sessionHeartbeat && self != .sessionCreated }
}
