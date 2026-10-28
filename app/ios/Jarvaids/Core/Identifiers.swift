//
//  Identifiers.swift
//  JarvaidsCore
//
//  Small wrapper types around the strings and integers the API moves around.
//  They exist so that a session ID cannot be passed where a record ID belongs,
//  and so that the two values the server treats as security sensitive, the bearer
//  token and the record revision, carry their handling rules in the type itself.
//

import Foundation

// MARK: - Plain identifiers

/// A value that is just a server-supplied string. The API constrains all of these to
/// 8 to 80 URL-safe characters, which `IdentifierText` checks on construction so that
/// a malformed ID fails locally instead of costing a round trip.
public protocol IdentifierText: RawRepresentable, Hashable, Sendable, Codable, CustomStringConvertible
where RawValue == String {
    init(unchecked rawValue: String)
}

extension IdentifierText {
    public init?(rawValue: String) {
        guard IdentifierSyntax.isValidIdentifier(rawValue) else { return nil }
        self.init(unchecked: rawValue)
    }

    /// Decoding never validates. The server is the authority on its own IDs and a
    /// stricter client would reject a whole snapshot over one unexpected character.
    public init(from decoder: any Decoder) throws {
        self.init(unchecked: try decoder.singleValueContainer().decode(String.self))
    }

    public func encode(to encoder: any Encoder) throws {
        var container = encoder.singleValueContainer()
        try container.encode(rawValue)
    }

    public var description: String { rawValue }
}

public enum IdentifierSyntax {
    /// API.md: "IDs/request IDs are 8-80 URL-safe alphanumeric, underscore or hyphen characters".
    public static func isValidIdentifier(_ value: String) -> Bool {
        guard (8...80).contains(value.count) else { return false }
        return value.allSatisfy(isURLSafe)
    }

    /// API.md: "tokens are 32-128 such characters".
    public static func isValidCredential(_ value: String) -> Bool {
        guard (32...128).contains(value.count) else { return false }
        return value.allSatisfy(isURLSafe)
    }

    private static func isURLSafe(_ character: Character) -> Bool {
        character.isASCII && (character.isLetter || character.isNumber || character == "_" || character == "-")
    }
}

public struct SessionID: IdentifierText {
    public let rawValue: String
    public init(unchecked rawValue: String) { self.rawValue = rawValue }
}

public struct ActorID: IdentifierText {
    public let rawValue: String
    public init(unchecked rawValue: String) { self.rawValue = rawValue }
}

public struct RecordID: IdentifierText {
    public let rawValue: String
    public init(unchecked rawValue: String) { self.rawValue = rawValue }
}

public struct RequestID: IdentifierText {
    public let rawValue: String
    public init(unchecked rawValue: String) { self.rawValue = rawValue }
}

/// Crop region IDs are chosen by the client and are not bound by the 8 to 80 rule the
/// way record IDs are, so this one is a thin wrapper with no syntax check.
public struct RegionID: RawRepresentable, Hashable, Sendable, Codable, CustomStringConvertible {
    public let rawValue: String
    public init(rawValue: String) { self.rawValue = rawValue }
    public init(from decoder: any Decoder) throws {
        self.rawValue = try decoder.singleValueContainer().decode(String.self)
    }
    public func encode(to encoder: any Encoder) throws {
        var container = encoder.singleValueContainer()
        try container.encode(rawValue)
    }
    public var description: String { rawValue }
}

// MARK: - Credentials

/// A bearer token. Held in memory only.
///
/// API.md: "Never put tokens in URLs or logs." That is why this type is `Encodable`
/// but not `Decodable` (the server never returns a token, so nothing should try to
/// read one out of a response), and why both of its textual descriptions are redacted.
/// Reaching the secret takes an explicit `.rawValue`, which is greppable in review.
public struct ActorToken: RawRepresentable, Hashable, Sendable, Encodable,
                          CustomStringConvertible, CustomDebugStringConvertible {
    public let rawValue: String

    public init?(rawValue: String) {
        guard IdentifierSyntax.isValidCredential(rawValue) else { return nil }
        self.rawValue = rawValue
    }

    /// 32 random bytes rendered as 64 hex characters, matching what `client.mjs` generates.
    public static func makeRandom() -> ActorToken {
        ActorToken(rawValue: RandomText.hexString(byteCount: 32))!
    }

    public func encode(to encoder: any Encoder) throws {
        var container = encoder.singleValueContainer()
        try container.encode(rawValue)
    }

    public var description: String { "ActorToken(redacted)" }
    public var debugDescription: String { "ActorToken(redacted)" }
}

/// Everything the client needs to talk to one session as one actor. Never persisted.
///
/// API.md and the server README are explicit that losing a credential loses access and
/// that there is no recovery: writing this to the keychain or to disk would be a
/// deliberate product decision, not a convenience, so the type gives you no help with it.
public struct SessionCredential: Sendable {
    public let sessionID: SessionID
    public let token: ActorToken

    public init(sessionID: SessionID, token: ActorToken) {
        self.sessionID = sessionID
        self.token = token
    }

    /// Fresh credentials for a session this device is about to create.
    public static func makeRandom() -> SessionCredential {
        SessionCredential(
            sessionID: SessionID(rawValue: "sess_" + RandomText.hexString(byteCount: 16))!,
            token: .makeRandom()
        )
    }
}

// MARK: - Revisions

/// The revision of a record, as displayed to the person who is about to act on it.
///
/// This type has no public initialiser taking an `Int` by design. A `Revision` can only
/// be obtained by decoding a record the client actually fetched, or through the
/// conspicuously named `afterHumanReview(_:)`.
///
/// The reason is in API.md: "Do not automatically retry an HTTP 409 with a new revision:
/// that would bypass renewed human review." The obvious way to get that wrong is to read
/// `details.current_revision` off a conflict and resubmit with it. `ConflictError`
/// therefore reports that number as a plain `Int` for display, and a plain `Int` will not
/// compile where a `Revision` is wanted. Turning one into the other is possible, but it
/// has to be written out and it says what it is claiming.
public struct Revision: Hashable, Sendable, Codable, Comparable, CustomStringConvertible {
    public let value: Int

    init(unchecked value: Int) { self.value = value }

    /// Assert that a person has looked at the current revision of the record and still
    /// wants the change. Only call this on a revision that came from a fresh fetch and
    /// was shown to the person, not on the number carried in a 409 response.
    public static func afterHumanReview(_ value: Int) -> Revision {
        Revision(unchecked: value)
    }

    public init(from decoder: any Decoder) throws {
        self.value = try decoder.singleValueContainer().decode(Int.self)
    }

    public func encode(to encoder: any Encoder) throws {
        var container = encoder.singleValueContainer()
        try container.encode(value)
    }

    public static func < (lhs: Revision, rhs: Revision) -> Bool { lhs.value < rhs.value }
    public var description: String { String(value) }
}

// MARK: - Timestamps

/// The server sends epoch seconds as a JSON number. Decoding straight into `Date` would
/// need a global decoder strategy, which would then also apply to fields such as
/// `duration_ms` if they ever changed type, so the conversion is kept explicit and local.
public struct Timestamp: Hashable, Sendable, Codable, Comparable, CustomStringConvertible {
    public let epochSeconds: Double

    public init(epochSeconds: Double) { self.epochSeconds = epochSeconds }

    public var date: Date { Date(timeIntervalSince1970: epochSeconds) }

    public init(from decoder: any Decoder) throws {
        self.epochSeconds = try decoder.singleValueContainer().decode(Double.self)
    }

    public func encode(to encoder: any Encoder) throws {
        var container = encoder.singleValueContainer()
        try container.encode(epochSeconds)
    }

    public static func < (lhs: Timestamp, rhs: Timestamp) -> Bool {
        lhs.epochSeconds < rhs.epochSeconds
    }

    public var description: String { date.description }
}

// MARK: - Randomness

public enum RandomText {
    /// `SystemRandomNumberGenerator` is documented as cryptographically secure on Apple
    /// platforms. It is used rather than CryptoKit so that this target keeps to the
    /// standard library and Foundation. See VERIFICATION.md if that is not good enough
    /// for a given deployment.
    public static func hexString(byteCount: Int) -> String {
        var generator = SystemRandomNumberGenerator()
        var output = ""
        output.reserveCapacity(byteCount * 2)
        for _ in 0..<byteCount {
            let byte = UInt8.random(in: UInt8.min...UInt8.max, using: &generator)
            output += String(format: "%02x", byte)
        }
        return output
    }

    /// Request IDs only need to be unique per session and actor, and a UUID string is
    /// 36 URL-safe characters, which is inside the 8 to 80 rule.
    public static func requestID() -> RequestID {
        RequestID(unchecked: UUID().uuidString)
    }
}
