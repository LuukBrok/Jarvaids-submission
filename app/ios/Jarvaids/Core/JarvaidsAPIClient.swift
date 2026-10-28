//
//  JarvaidsAPIClient.swift
//  JarvaidsCore
//
//  Every route in API.md, wrapped in an actor.
//
//  It is an actor rather than a struct because the bearer credential lives in it and
//  nowhere else. Keeping the secret behind actor isolation means there is one place to
//  read when asking "where could this token go", and the answer is: into an
//  `Authorization` header, and into the body of a session-creation or invite request.
//  It is never written to disk, never put in a URL, and never included in any string
//  this file produces.
//

import Foundation

public actor JarvaidsAPIClient {

    // MARK: Configuration

    public struct Configuration: Sendable {
        public let baseURL: URL
        /// Applied per request. The backend's own job deadline is 60 seconds, so a
        /// shorter client timeout would report failure while the server was still working.
        public let requestTimeout: TimeInterval

        /// Rejects a base URL that could leak the credential.
        ///
        /// `client.mjs` refuses anything that is not a bare loopback HTTP origin, because
        /// the prototype binds to 127.0.0.1 and has no transport security. This is a
        /// little looser: plain HTTP is still loopback-only, but HTTPS is allowed, so the
        /// same client can be pointed at a real deployment when there is one. A base URL
        /// with embedded credentials, a query or a fragment is refused either way.
        public init(baseURL: URL, requestTimeout: TimeInterval = 30) throws {
            guard let components = URLComponents(url: baseURL, resolvingAgainstBaseURL: false),
                  let scheme = components.scheme?.lowercased(),
                  let host = components.host,
                  components.user == nil, components.password == nil,
                  components.query == nil, components.fragment == nil,
                  components.path.isEmpty || components.path == "/"
            else {
                throw JarvaidsError.invalidRequest(APIErrorBody(
                    code: .invalidHost,
                    message: "The base URL must be a bare origin with no credentials, query or fragment."
                ))
            }
            let isLoopback = ["localhost", "127.0.0.1", "::1", "[::1]"].contains(host.lowercased())
            guard scheme == "https" || (scheme == "http" && isLoopback) else {
                throw JarvaidsError.invalidRequest(APIErrorBody(
                    code: .invalidHost,
                    message: "Plain HTTP is only allowed for loopback. Use HTTPS for anything else."
                ))
            }
            self.baseURL = baseURL
            self.requestTimeout = requestTimeout
        }

        /// The default the backend README documents for local development.
        public static func localPrototype(port: Int = 3000) throws -> Configuration {
            try Configuration(baseURL: URL(string: "http://127.0.0.1:\(port)")!)
        }
    }

    // MARK: State

    private let configuration: Configuration
    private let credential: SessionCredential
    private let urlSession: URLSession
    private let ownsURLSession: Bool
    private let decoder = JSONDecoder()

    /// - Parameter urlSession: pass one only for tests. The default is built here so that
    ///   caching, cookies and redirects are all off, which matters: a cached response
    ///   would show a stale board, and a followed redirect would forward the bearer token
    ///   to somewhere that was never authorised to see it.
    public init(
        configuration: Configuration,
        credential: SessionCredential,
        urlSession: URLSession? = nil
    ) {
        self.configuration = configuration
        self.credential = credential
        if let urlSession {
            self.urlSession = urlSession
            self.ownsURLSession = false
        } else {
            let settings = URLSessionConfiguration.ephemeral
            settings.urlCache = nil
            settings.requestCachePolicy = .reloadIgnoringLocalAndRemoteCacheData
            settings.httpCookieStorage = nil
            settings.httpShouldSetCookies = false
            settings.httpAdditionalHeaders = ["Accept": "application/json"]
            settings.timeoutIntervalForRequest = configuration.requestTimeout
            self.urlSession = URLSession(
                configuration: settings,
                delegate: RedirectRefusingDelegate(),
                delegateQueue: nil
            )
            self.ownsURLSession = true
        }
    }

    /// A `URLSession` built with a delegate holds that delegate until it is invalidated,
    /// so a long-lived app should call this when it is finished with the session.
    public func shutdown() {
        if ownsURLSession {
            urlSession.finishTasksAndInvalidate()
        }
    }

    public nonisolated var sessionID: SessionID { credential.sessionID }

    // MARK: Routes

    /// `GET /health`. Needs no credential, but is sent with one anyway so that a
    /// misconfigured base URL fails the same way here as everywhere else.
    public func health() async throws -> HealthStatus {
        try await get(path: "/health", as: HealthStatus.self)
    }

    /// `POST /api/sessions`.
    ///
    /// Safe to repeat verbatim: the server matches on the session ID and the creation
    /// fields, and answers a repeat with `replayed: true`. Repeating it with *different*
    /// fields is an `idempotencyConflict`, so retry the same call, do not rebuild it.
    public func createSession(
        ownerName: String,
        title: String,
        retentionSeconds: Int? = nil
    ) async throws -> SessionCreationResult {
        struct Body: Encodable {
            let sessionID: SessionID
            let ownerToken: ActorToken
            let ownerName: String
            let title: String
            let retentionSeconds: Int?

            private enum CodingKeys: String, CodingKey {
                case title
                case sessionID = "session_id"
                case ownerToken = "owner_token"
                case ownerName = "owner_name"
                case retentionSeconds = "retention_seconds"
            }
        }
        let body = try JSONEncoder().encode(Body(
            sessionID: credential.sessionID,
            ownerToken: credential.token,
            ownerName: ownerName,
            title: title,
            retentionSeconds: retentionSeconds
        ))
        return try await send(
            method: "POST",
            path: "/api/sessions",
            body: body,
            requestID: nil,
            as: SessionCreationResult.self
        )
    }

    /// `GET /api/sessions/{sid}`.
    ///
    /// Two different documents come back under HTTP 200 depending on whether the session
    /// still exists, so the result is an enum rather than an optional-riddled struct.
    /// On reconnect, call this before polling events: a cursor alone cannot rebuild state.
    public func snapshot() async throws -> SnapshotResponse {
        let data = try await requestData(
            method: "GET", path: sessionPath, body: nil, requestID: nil, accept: "application/json"
        )
        // The deleted form has no `session` key at all. Probing for it is more robust than
        // guessing from the state string, which only the live form carries in that place.
        if let probe = try? decoder.decode(DeletedProbe.self, from: data.bytes), probe.session == nil {
            return .deleted(try decode(DeletionReceipt.self, from: data.bytes))
        }
        return .live(try decode(SessionSnapshot.self, from: data.bytes))
    }

    /// `POST /api/sessions/{sid}/commands`.
    ///
    /// The only way to write. Takes a `CommandIntent` and nothing else, so resending
    /// after an uncertain result can only mean resending the identical operation, payload
    /// and request ID, which is exactly what the idempotency contract asks for.
    @discardableResult
    public func submit<Result>(
        _ intent: CommandIntent<Result>
    ) async throws -> CommandResponse<Result> {
        try await send(
            method: "POST",
            path: sessionPath + "/commands",
            body: intent.body,
            requestID: intent.requestID,
            as: CommandResponse<Result>.self
        )
    }

    /// Resends the same intent when, and only when, the outcome is genuinely unknown.
    ///
    /// The retry condition is `JarvaidsError.mayResendSameIntent`, which excludes every
    /// 4xx. In particular a 409 stops immediately, because API.md is explicit that
    /// retrying one with a fresh revision bypasses renewed human review, and there is no
    /// sense in retrying one with the same revision either.
    @discardableResult
    public func submitRetryingUncertainDelivery<Result>(
        _ intent: CommandIntent<Result>,
        attempts: Int = 3,
        backoff: Duration = .milliseconds(400)
    ) async throws -> CommandResponse<Result> {
        precondition(attempts >= 1, "An intent must be sent at least once.")
        var lastError: JarvaidsError = .cancelled
        for attempt in 0..<attempts {
            do {
                return try await submit(intent)
            } catch let error as JarvaidsError where error.mayResendSameIntent {
                lastError = error
                if attempt + 1 < attempts {
                    // Linear rather than exponential: a meeting is happening, and a long
                    // backoff is worse for the room than one more request.
                    try await Task.sleep(for: backoff * (attempt + 1))
                }
            }
        }
        throw lastError
    }

    /// `GET /api/sessions/{sid}/events?after=N`.
    ///
    /// Up to 200 events per page. Call again immediately while `hasMore` is true.
    public func events(after cursor: Int) async throws -> EventPage {
        try await get(path: sessionPath + "/events", query: [
            URLQueryItem(name: "after", value: String(cursor))
        ], as: EventPage.self)
    }

    /// `GET /api/sessions/{sid}/records/{id}`.
    ///
    /// Omit `revision` for the current record. A historical revision is available for
    /// inspection, and API.md is clear that it is not a valid dependency for a new
    /// acceptance, which is why nothing here turns one into a `Reference` for you.
    public func record(_ id: RecordID, revision: Revision? = nil) async throws -> Record {
        var query: [URLQueryItem] = []
        if let revision {
            query.append(URLQueryItem(name: "revision", value: String(revision.value)))
        }
        return try await get(
            path: sessionPath + "/records/" + escape(id.rawValue),
            query: query,
            as: Record.self
        )
    }

    /// `GET /api/sessions/{sid}/sources/{id}/media`.
    ///
    /// Authenticated image bytes. Snapshots and record reads never carry them, so this is
    /// the only way to get a photograph, and the bytes must not be cached to disk.
    public func sourceMedia(_ id: RecordID) async throws -> SourceMedia {
        let response = try await requestData(
            method: "GET",
            path: sessionPath + "/sources/" + escape(id.rawValue) + "/media",
            body: nil,
            requestID: nil,
            accept: "image/*"
        )
        return SourceMedia(bytes: response.bytes, mimeType: response.mimeType)
    }

    /// `GET /api/sessions/{sid}/exports/{id}?format=json`.
    ///
    /// The one read whose body is not a `{id, kind, revision, data}` record envelope.
    public func exportDocument(_ id: RecordID) async throws -> ExportDocument {
        try await get(
            path: sessionPath + "/exports/" + escape(id.rawValue),
            query: [URLQueryItem(name: "format", value: "json")],
            as: ExportDocument.self
        )
    }

    /// `GET /api/sessions/{sid}/exports/{id}?format=markdown`.
    ///
    /// Returns the Markdown the server generated, with its text already escaped. The
    /// server also sends a `Content-Disposition` filename, which is ignored here: naming
    /// a downloaded file is a UI decision.
    public func exportMarkdown(_ id: RecordID) async throws -> String {
        let response = try await requestData(
            method: "GET",
            path: sessionPath + "/exports/" + escape(id.rawValue),
            body: nil,
            requestID: nil,
            accept: "text/markdown",
            query: [URLQueryItem(name: "format", value: "markdown")]
        )
        guard let text = String(data: response.bytes, encoding: .utf8) else {
            throw JarvaidsError.malformedResponse("The Markdown export was not valid UTF-8.")
        }
        return text
    }

    /// `DELETE /api/sessions/{sid}`.
    ///
    /// Facilitator only. Safe to repeat: a second call returns the same receipt with
    /// `replayed: true`. The receipt is not a certificate of removal from backups or from
    /// copies anyone already downloaded, and the server says so in its `boundary` text.
    @discardableResult
    public func deleteSession() async throws -> DeletionReceipt {
        try await send(
            method: "DELETE", path: sessionPath, body: nil, requestID: nil,
            as: DeletionReceipt.self
        )
    }

    // MARK: Request plumbing

    private var sessionPath: String { "/api/sessions/" + escape(credential.sessionID.rawValue) }

    private func get<T: Decodable>(
        path: String,
        query: [URLQueryItem] = [],
        as type: T.Type
    ) async throws -> T {
        let response = try await requestData(
            method: "GET", path: path, body: nil, requestID: nil,
            accept: "application/json", query: query
        )
        return try decode(type, from: response.bytes)
    }

    private func send<T: Decodable>(
        method: String,
        path: String,
        body: Data?,
        requestID: RequestID?,
        as type: T.Type
    ) async throws -> T {
        let response = try await requestData(
            method: method, path: path, body: body, requestID: requestID,
            accept: "application/json"
        )
        return try decode(type, from: response.bytes)
    }

    private struct RawResponse {
        let bytes: Data
        let mimeType: String?
    }

    private func requestData(
        method: String,
        path: String,
        body: Data?,
        requestID: RequestID?,
        accept: String,
        query: [URLQueryItem] = []
    ) async throws -> RawResponse {
        var components = URLComponents(
            url: configuration.baseURL, resolvingAgainstBaseURL: false
        )
        components?.path = path
        components?.queryItems = query.isEmpty ? nil : query
        guard let url = components?.url else {
            throw JarvaidsError.invalidRequest(APIErrorBody(
                code: .invalidPath,
                message: "Could not build a URL for \(path)."
            ))
        }

        var request = URLRequest(url: url)
        request.httpMethod = method
        request.timeoutInterval = configuration.requestTimeout
        request.cachePolicy = .reloadIgnoringLocalAndRemoteCacheData
        request.setValue(accept, forHTTPHeaderField: "Accept")
        // Per request, never on the session configuration: a header set there would ride
        // along on any redirect the system followed before this code saw it.
        request.setValue("Bearer \(credential.token.rawValue)", forHTTPHeaderField: "Authorization")
        if let requestID {
            request.setValue(requestID.rawValue, forHTTPHeaderField: "X-Request-ID")
        }
        if let body {
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = body
        }

        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await urlSession.data(for: request)
        } catch is CancellationError {
            throw JarvaidsError.cancelled
        } catch let error as URLError {
            if error.code == .cancelled { throw JarvaidsError.cancelled }
            throw JarvaidsError.transport(error)
        } catch {
            throw JarvaidsError.malformedResponse(String(describing: error))
        }

        guard let http = response as? HTTPURLResponse else {
            throw JarvaidsError.malformedResponse("The reply was not an HTTP response.")
        }
        guard (200..<300).contains(http.statusCode) else {
            // Errors are always JSON, but a proxy or a crash could produce something else,
            // so a body that will not decode becomes a nil body rather than a new failure.
            let envelope = try? decoder.decode(APIErrorEnvelope.self, from: data)
            throw JarvaidsError.from(status: http.statusCode, body: envelope?.error)
        }
        return RawResponse(bytes: data, mimeType: http.mimeType)
    }

    private func decode<T: Decodable>(_ type: T.Type, from data: Data) throws -> T {
        do {
            return try decoder.decode(type, from: data)
        } catch {
            // The message names the type, which is what tells a reader whether the
            // contract moved or the client simply asked for the wrong shape.
            throw JarvaidsError.decodingFailed("\(type): \(error)")
        }
    }

    private nonisolated func escape(_ value: String) -> String {
        value.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? value
    }
}

/// Used only to tell a live snapshot from a deletion receipt.
private struct DeletedProbe: Decodable {
    let session: JSONValue?
}

/// Refuses every redirect.
///
/// `client.mjs` sets `redirect: "error"` for the same reason: the request carries a
/// bearer token in a header, and URLSession would replay that header to wherever the
/// redirect pointed. There is no legitimate redirect in this API, so any redirect is
/// either a misconfiguration or an attempt to collect the credential.
///
/// `@unchecked Sendable` is honest here: the class has no stored state at all.
private final class RedirectRefusingDelegate: NSObject, URLSessionTaskDelegate, @unchecked Sendable {
    func urlSession(
        _ session: URLSession,
        task: URLSessionTask,
        willPerformHTTPRedirection response: HTTPURLResponse,
        newRequest request: URLRequest,
        completionHandler: @escaping (URLRequest?) -> Void
    ) {
        completionHandler(nil)
    }
}
