//
//  FacilitatorHeartbeat.swift
//  JarvaidsCore
//
//  API.md and the backend README: "Send a facilitator heartbeat roughly once per minute
//  while the session is attended."
//
//  The lease the heartbeat renews is five minutes. That gap is the point: a facilitator
//  who walks out of the room does not keep the session attended for long, and one dropped
//  heartbeat on a bad network does not end the meeting. Hence "roughly once per minute",
//  and hence a missed beat is logged rather than escalated.
//
//  What this deliberately does not do is reactivate anything. The backend README is
//  explicit: "Do not automatically reactivate capture after pause, roster changes or
//  lease expiry." A heartbeat renews a lease; it never turns capture back on.
//

import Foundation

public actor FacilitatorHeartbeat {

    /// Roughly once a minute, a little under, so that a single late or lost beat still
    /// lands inside the server's five-minute lease.
    public static let interval: Duration = .seconds(50)

    /// How long to wait after a failed beat before trying again. Short, because a lapsed
    /// lease is worse than one extra request.
    public static let retryInterval: Duration = .seconds(10)

    private let client: JarvaidsAPIClient
    private var task: Task<Void, Never>?
    private var lastRenewal: Date?
    private var lastFailure: JarvaidsError?

    public init(client: JarvaidsAPIClient) {
        self.client = client
    }

    public var isRunning: Bool { task != nil }

    /// When the last successful beat landed. Nil if none has.
    public var lastSuccessfulRenewal: Date? { lastRenewal }

    /// The last failure, kept so a screen can say the lease is at risk.
    public var mostRecentFailure: JarvaidsError? { lastFailure }

    /// Starts beating. Safe to call more than once; the second call is a no-op.
    ///
    /// Start this when a facilitator is present and looking at the session, and stop it
    /// when they are not. "Attended" is a fact about the room, which only the UI layer
    /// knows, so this type does not try to infer it from anything.
    public func start() {
        guard task == nil else { return }
        task = Task { [weak self] in
            await self?.loop()
        }
    }

    public func stop() {
        task?.cancel()
        task = nil
    }

    private func loop() async {
        // Beat immediately rather than waiting out the first interval: the session may
        // have been unattended for a while before someone opened this screen.
        while !Task.isCancelled {
            let wait: Duration
            switch await beatOnce() {
            case .renewed:
                wait = Self.interval
            case .retryable:
                wait = Self.retryInterval
            case .stop:
                return
            }
            do {
                try await Task.sleep(for: wait)
            } catch {
                return  // Cancelled.
            }
        }
    }

    private enum Outcome {
        case renewed
        /// Worth another beat: a flaky network, a slow server, a transient failure.
        case retryable
        /// Beating again would be pointless: the session is closed, gone, or this
        /// credential is not a facilitator's.
        case stop
    }

    private func beatOnce() async -> Outcome {
        do {
            // A fresh intent every time. A heartbeat is a new action, not a retry of the
            // last one, so it gets its own request ID, which is what API.md asks for.
            let intent = try CommandIntent<HeartbeatResult>.heartbeat()
            _ = try await client.submit(intent)
            lastRenewal = Date()
            lastFailure = nil
            return .renewed
        } catch let error as JarvaidsError {
            lastFailure = error
            switch error {
            case .unauthorized, .forbidden, .notFound:
                // Not a facilitator, or the session is gone. Neither improves by asking
                // again every ten seconds.
                return .stop
            case .conflict(let conflict):
                switch conflict.kind {
                case .sessionClosed, .sessionDeleted, .sessionExpired:
                    return .stop
                default:
                    return .retryable
                }
            default:
                return .retryable
            }
        } catch {
            lastFailure = .malformedResponse(String(describing: error))
            return .retryable
        }
    }
}
