//
//  JSONValue.swift
//  JarvaidsCore
//
//  A minimal any-JSON tree. It exists for exactly two jobs, both of which are places
//  where the client must survive data it does not have a type for:
//
//  1. `error.details`, which API.md leaves open and which differs per error code.
//  2. The `data` of a record whose `kind` this build does not recognise.
//
//  It is deliberately not used anywhere else. Everything the contract does specify gets
//  a real struct, so that a typo in a key name is a compile error rather than a nil.
//

import Foundation

public enum JSONValue: Hashable, Sendable, Codable {
    case null
    case bool(Bool)
    case number(Double)
    case string(String)
    case array([JSONValue])
    case object([String: JSONValue])

    public init(from decoder: any Decoder) throws {
        let container = try decoder.singleValueContainer()
        if container.decodeNil() {
            self = .null
        } else if let value = try? container.decode(Bool.self) {
            self = .bool(value)
        } else if let value = try? container.decode(Double.self) {
            self = .number(value)
        } else if let value = try? container.decode(String.self) {
            self = .string(value)
        } else if let value = try? container.decode([JSONValue].self) {
            self = .array(value)
        } else if let value = try? container.decode([String: JSONValue].self) {
            self = .object(value)
        } else {
            throw DecodingError.dataCorruptedError(
                in: container,
                debugDescription: "Value is not JSON this decoder recognises."
            )
        }
    }

    public func encode(to encoder: any Encoder) throws {
        var container = encoder.singleValueContainer()
        switch self {
        case .null: try container.encodeNil()
        case .bool(let value): try container.encode(value)
        case .number(let value): try container.encode(value)
        case .string(let value): try container.encode(value)
        case .array(let value): try container.encode(value)
        case .object(let value): try container.encode(value)
        }
    }

    // Accessors, for reading the few `details` fields worth acting on without
    // writing a cast at every call site.

    public var stringValue: String? { if case .string(let value) = self { return value }; return nil }
    public var boolValue: Bool? { if case .bool(let value) = self { return value }; return nil }
    public var doubleValue: Double? { if case .number(let value) = self { return value }; return nil }
    public var objectValue: [String: JSONValue]? { if case .object(let value) = self { return value }; return nil }
    public var arrayValue: [JSONValue]? { if case .array(let value) = self { return value }; return nil }

    /// Whole numbers arrive as JSON numbers, so an `Int` read has to go through `Double`.
    public var intValue: Int? {
        guard case .number(let value) = self, value.rounded() == value,
              value >= Double(Int.min), value <= Double(Int.max) else { return nil }
        return Int(value)
    }

    public subscript(key: String) -> JSONValue? { objectValue?[key] }
}
