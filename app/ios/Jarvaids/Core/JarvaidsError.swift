//
//  JarvaidsError.swift
//  JarvaidsCore
//
//  The API's status codes mean different things and want different responses, so they
//  get different cases rather than one `statusCode: Int`.
//
//  The case that matters most is 409. API.md: "Do not automatically retry an HTTP 409
//  with a new revision: that would bypass renewed human review." A single error type
//  carrying a status number makes that mistake a one-line `if error.status == 409` away.
//  Splitting it out, and refusing to hand back a usable `Revision`, makes the wrong thing
//  something you have to write on purpose.
//

import Foundation

// MARK: - The error envelope

/// `{error: {code, message, details}}`, the only error shape the API produces.
public struct APIErrorBody: Sendable, Decodable, Equatable {
    public let code: ErrorCode
    /// Server text. Written for a person, but still untrusted input: render it as text.
    public let message: String
    /// Shape varies per code, so it stays as JSON. The few fields worth acting on are
    /// pulled out by the conflict and validation types below.
    public let details: [String: JSONValue]

    private enum CodingKeys: String, CodingKey {
        case code, message, details
    }

    public init(from decoder: any Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        self.code = try container.decode(ErrorCode.self, forKey: .code)
        self.message = try container.decode(String.self, forKey: .message)
        self.details = try container.decodeIfPresent([String: JSONValue].self, forKey: .details) ?? [:]
    }

    /// A body for a failure the client itself detected, so callers always have one.
    public init(code: ErrorCode, message: String, details: [String: JSONValue] = [:]) {
        self.code = code
        self.message = message
        self.details = details
    }
}

struct APIErrorEnvelope: Decodable {
    let error: APIErrorBody
}

/// Every error code the backend can emit, read out of the server source rather than
/// guessed, plus an `.unknown` fallback for anything added later.
public enum ErrorCode: OpenStringEnum {
    case adapterChanged
    case agreementIncomplete
    case bodyTooLarge
    case captureInactive
    case credentialReused
    case cyclicReference
    case duplicateReference
    case duplicateRegion
    case forbidden
    case idempotencyConflict
    case imageCapacity
    case imageTooLarge
    case incompleteBody
    case invalidAdapterOutput
    case invalidBase64
    case invalidBox
    case invalidCredential
    case invalidDecision
    case invalidDimensions
    case invalidFormat
    case invalidHost
    case invalidID
    case invalidImage
    case invalidJSON
    case invalidKind
    case invalidLength
    case invalidObject
    case invalidPath
    case invalidPositions
    case invalidQuery
    case invalidReference
    case invalidReferences
    case invalidRegion
    case invalidRegions
    case invalidRole
    case invalidTargets
    case itemUndone
    case jobTerminal
    case lastFacilitator
    case missingFields
    case newPlacementRequired
    case newStructureRequired
    case notFound
    case originDenied
    case participantCapacity
    case policyChanged
    case proposalTerminal
    case purgeFailed
    case queueFull
    case recordCapacity
    case requestCapacity
    case sessionCapacity
    case sessionClosed
    case sessionDeleted
    case sessionExists
    case sessionExpired
    case staleProposal
    case staleReference
    case staleRevision
    case storageCapacity
    case unauthorized
    case unknownFields
    case unknownOperation
    case unreadableContent
    case unsupportedContentType
    case unsupportedEncoding
    case unsupportedMedia
    case wrongSourceType
    case unknown(String)

    public init(apiValue: String) {
        self = Self.byRawValue[apiValue] ?? .unknown(apiValue)
    }

    public var rawValue: String {
        switch self {
        case .adapterChanged: return "adapter_changed"
        case .agreementIncomplete: return "agreement_incomplete"
        case .bodyTooLarge: return "body_too_large"
        case .captureInactive: return "capture_inactive"
        case .credentialReused: return "credential_reused"
        case .cyclicReference: return "cyclic_reference"
        case .duplicateReference: return "duplicate_reference"
        case .duplicateRegion: return "duplicate_region"
        case .forbidden: return "forbidden"
        case .idempotencyConflict: return "idempotency_conflict"
        case .imageCapacity: return "image_capacity"
        case .imageTooLarge: return "image_too_large"
        case .incompleteBody: return "incomplete_body"
        case .invalidAdapterOutput: return "invalid_adapter_output"
        case .invalidBase64: return "invalid_base64"
        case .invalidBox: return "invalid_box"
        case .invalidCredential: return "invalid_credential"
        case .invalidDecision: return "invalid_decision"
        case .invalidDimensions: return "invalid_dimensions"
        case .invalidFormat: return "invalid_format"
        case .invalidHost: return "invalid_host"
        case .invalidID: return "invalid_id"
        case .invalidImage: return "invalid_image"
        case .invalidJSON: return "invalid_json"
        case .invalidKind: return "invalid_kind"
        case .invalidLength: return "invalid_length"
        case .invalidObject: return "invalid_object"
        case .invalidPath: return "invalid_path"
        case .invalidPositions: return "invalid_positions"
        case .invalidQuery: return "invalid_query"
        case .invalidReference: return "invalid_reference"
        case .invalidReferences: return "invalid_references"
        case .invalidRegion: return "invalid_region"
        case .invalidRegions: return "invalid_regions"
        case .invalidRole: return "invalid_role"
        case .invalidTargets: return "invalid_targets"
        case .itemUndone: return "item_undone"
        case .jobTerminal: return "job_terminal"
        case .lastFacilitator: return "last_facilitator"
        case .missingFields: return "missing_fields"
        case .newPlacementRequired: return "new_placement_required"
        case .newStructureRequired: return "new_structure_required"
        case .notFound: return "not_found"
        case .originDenied: return "origin_denied"
        case .participantCapacity: return "participant_capacity"
        case .policyChanged: return "policy_changed"
        case .proposalTerminal: return "proposal_terminal"
        case .purgeFailed: return "purge_failed"
        case .queueFull: return "queue_full"
        case .recordCapacity: return "record_capacity"
        case .requestCapacity: return "request_capacity"
        case .sessionCapacity: return "session_capacity"
        case .sessionClosed: return "session_closed"
        case .sessionDeleted: return "session_deleted"
        case .sessionExists: return "session_exists"
        case .sessionExpired: return "session_expired"
        case .staleProposal: return "stale_proposal"
        case .staleReference: return "stale_reference"
        case .staleRevision: return "stale_revision"
        case .storageCapacity: return "storage_capacity"
        case .unauthorized: return "unauthorized"
        case .unknownFields: return "unknown_fields"
        case .unknownOperation: return "unknown_operation"
        case .unreadableContent: return "unreadable_content"
        case .unsupportedContentType: return "unsupported_content_type"
        case .unsupportedEncoding: return "unsupported_encoding"
        case .unsupportedMedia: return "unsupported_media"
        case .wrongSourceType: return "wrong_source_type"
        case .unknown(let raw): return raw
        }
    }

    public var isUnknownCase: Bool { if case .unknown = self { return true }; return false }

    private static let byRawValue: [String: ErrorCode] = {
        let all: [ErrorCode] = [
            .adapterChanged, .agreementIncomplete, .bodyTooLarge, .captureInactive,
            .credentialReused, .cyclicReference, .duplicateReference, .duplicateRegion,
            .forbidden, .idempotencyConflict, .imageCapacity, .imageTooLarge,
            .incompleteBody, .invalidAdapterOutput, .invalidBase64, .invalidBox,
            .invalidCredential, .invalidDecision, .invalidDimensions, .invalidFormat,
            .invalidHost, .invalidID, .invalidImage, .invalidJSON, .invalidKind,
            .invalidLength, .invalidObject, .invalidPath, .invalidPositions,
            .invalidQuery, .invalidReference, .invalidReferences, .invalidRegion,
            .invalidRegions, .invalidRole, .invalidTargets, .itemUndone, .jobTerminal,
            .lastFacilitator, .missingFields, .newPlacementRequired, .newStructureRequired,
            .notFound, .originDenied, .participantCapacity, .policyChanged,
            .proposalTerminal, .purgeFailed, .queueFull, .recordCapacity,
            .requestCapacity, .sessionCapacity, .sessionClosed, .sessionDeleted,
            .sessionExists, .sessionExpired, .staleProposal, .staleReference,
            .staleRevision, .storageCapacity, .unauthorized, .unknownFields,
            .unknownOperation, .unreadableContent, .unsupportedContentType,
            .unsupportedEncoding, .unsupportedMedia, .wrongSourceType,
        ]
        return Dictionary(uniqueKeysWithValues: all.map { ($0.rawValue, $0) })
    }()
}

// MARK: - Conflicts

/// An HTTP 409. Every one of these means the same thing at the product level: the world
/// moved under the person, and a person has to look again before anything is written.
///
/// The type deliberately gives you no `Revision` to resubmit with. See `Revision` for why.
public struct ConflictError: Sendable, Equatable {
    public enum Kind: Sendable, Equatable {
        /// The target record is at a different revision than the one the person saw.
        case staleRevision(recordID: RecordID?)
        /// The proposal is no longer reviewable because a dependency changed.
        case staleProposal
        /// A reference points at something stale or undone.
        case staleReference
        /// Capture is off: the session is draft, paused or closed.
        case captureInactive
        /// The same request ID was sent with different content. This is a client bug:
        /// a fresh action needs a fresh key.
        case idempotencyConflict
        /// The roster or the policy changed, so acknowledgements were revoked.
        case policyChanged(currentPolicyVersion: Int?)
        /// Activation was attempted before everyone acknowledged.
        case agreementIncomplete(pending: [ActorID])
        case sessionClosed
        case sessionDeleted
        case sessionExpired
        case sessionExists
        case credentialReused
        case lastFacilitator
        /// The proposal was already accepted or rejected, and that history is immutable.
        case proposalTerminal
        case jobTerminal
        case itemUndone
        /// Changing relationship or placement targets needs a fresh proposal, not an edit.
        case freshProposalRequired
        case other(ErrorCode)
    }

    public let kind: Kind
    public let body: APIErrorBody

    /// The revision the server says the record is at now.
    ///
    /// This is an `Int` and not a `Revision` on purpose: it is for showing the person
    /// ("this moved to revision 4 while you were typing"), not for putting straight back
    /// into `expected_revision`. Doing that would accept on the person's behalf something
    /// they never read. Refetch the record, show it, and let them decide again.
    public var reportedCurrentRevision: Int? { body.details["current_revision"]?.intValue }

    init(body: APIErrorBody) {
        self.body = body
        switch body.code {
        case .staleRevision:
            let id = body.details["record_id"]?.stringValue.map { RecordID(unchecked: $0) }
            self.kind = .staleRevision(recordID: id)
        case .staleProposal: self.kind = .staleProposal
        case .staleReference: self.kind = .staleReference
        case .captureInactive: self.kind = .captureInactive
        case .idempotencyConflict: self.kind = .idempotencyConflict
        case .policyChanged:
            self.kind = .policyChanged(
                currentPolicyVersion: body.details["current_policy_version"]?.intValue
            )
        case .agreementIncomplete:
            let pending = (body.details["actor_ids"]?.arrayValue ?? [])
                .compactMap { $0.stringValue }
                .map { ActorID(unchecked: $0) }
            self.kind = .agreementIncomplete(pending: pending)
        case .sessionClosed: self.kind = .sessionClosed
        case .sessionDeleted: self.kind = .sessionDeleted
        case .sessionExpired: self.kind = .sessionExpired
        case .sessionExists: self.kind = .sessionExists
        case .credentialReused: self.kind = .credentialReused
        case .lastFacilitator: self.kind = .lastFacilitator
        case .proposalTerminal: self.kind = .proposalTerminal
        case .jobTerminal: self.kind = .jobTerminal
        case .itemUndone: self.kind = .itemUndone
        case .newStructureRequired, .newPlacementRequired: self.kind = .freshProposalRequired
        default: self.kind = .other(body.code)
        }
    }

    /// API.md's instruction for every 409: "Refresh, preserve unsaved text and require
    /// renewed intent." Nothing here is ever retried automatically.
    public var requiresRenewedHumanIntent: Bool { true }
}

// MARK: - The error type

public enum JarvaidsError: Error, Sendable {
    /// The request never got a usable answer. This is the only family where sending the
    /// same `CommandIntent` again is the right move: the request ID makes it safe.
    case transport(URLError)
    case cancelled
    /// A response arrived but was not HTTP, or was not JSON the client could read.
    case malformedResponse(String)
    case decodingFailed(String)

    /// 401. Stop writing and show the access state. Nothing the client can fix by itself.
    case unauthorized(APIErrorBody)
    /// 403. The credential is fine but this role may not do this.
    case forbidden(APIErrorBody)
    /// 404. Refresh the relevant state. API.md: "do not substitute another record".
    case notFound(APIErrorBody)
    /// 400 and 422. A specific input is wrong, so explain which one. Do not blindly retry.
    case invalidRequest(APIErrorBody)
    /// 409. Never retried automatically. See `ConflictError`.
    case conflict(ConflictError)
    /// 413. Reduce the source before resubmitting.
    case payloadTooLarge(APIErrorBody)
    /// 429. Some capacity ran out. Offer cancel, export, close or delete as appropriate.
    case capacityExhausted(APIErrorBody)
    /// 5xx. The result is uncertain, so keep the intent and retry that same intent.
    case serverFailure(APIErrorBody)
    case unexpectedStatus(Int, APIErrorBody?)

    /// Whether resending the *same* `CommandIntent`, with its original request ID, is
    /// correct. True only where the outcome is genuinely unknown.
    ///
    /// Note what is absent: 409 is never in here, and neither is 400, 401, 403 or 404.
    /// A conflict is a decision for a person, not a retry for a client.
    public var mayResendSameIntent: Bool {
        switch self {
        case .transport, .serverFailure, .malformedResponse:
            return true
        case .cancelled, .decodingFailed, .unauthorized, .forbidden, .notFound,
             .invalidRequest, .conflict, .payloadTooLarge, .capacityExhausted,
             .unexpectedStatus:
            return false
        }
    }

    /// The server's own error body, where there was one.
    public var body: APIErrorBody? {
        switch self {
        case .unauthorized(let body), .forbidden(let body), .notFound(let body),
             .invalidRequest(let body), .payloadTooLarge(let body),
             .capacityExhausted(let body), .serverFailure(let body):
            return body
        case .conflict(let conflict):
            return conflict.body
        case .unexpectedStatus(_, let body):
            return body
        case .transport, .cancelled, .malformedResponse, .decodingFailed:
            return nil
        }
    }

    public var code: ErrorCode? { body?.code }

    /// True when the current snapshot is known to be out of date and a refetch is the
    /// first thing to do. Covers 404 and every 409, per API.md's UI behaviour table.
    public var requiresRefresh: Bool {
        switch self {
        case .notFound, .conflict: return true
        default: return false
        }
    }

    /// Maps a non-2xx response onto a case. Used by the client; exposed so tests can
    /// check the mapping without going through URLSession.
    public static func from(status: Int, body: APIErrorBody?) -> JarvaidsError {
        let fallback = body ?? APIErrorBody(
            code: .unknown("http_\(status)"),
            message: "The server returned HTTP \(status) without an error body."
        )
        switch status {
        case 400, 422: return .invalidRequest(fallback)
        case 401: return .unauthorized(fallback)
        case 403: return .forbidden(fallback)
        case 404: return .notFound(fallback)
        case 409: return .conflict(ConflictError(body: fallback))
        case 413: return .payloadTooLarge(fallback)
        case 429: return .capacityExhausted(fallback)
        case 500...599: return .serverFailure(fallback)
        default: return .unexpectedStatus(status, body)
        }
    }
}

extension JarvaidsError: LocalizedError {
    public var errorDescription: String? {
        switch self {
        case .transport(let error):
            return "The request did not complete: \(error.localizedDescription)"
        case .cancelled:
            return "The request was cancelled."
        case .malformedResponse(let detail):
            return "The server's reply could not be read: \(detail)"
        case .decodingFailed(let detail):
            return "The server's reply did not match the expected shape: \(detail)"
        case .conflict(let conflict):
            return conflict.body.message
        default:
            return body?.message
        }
    }
}
