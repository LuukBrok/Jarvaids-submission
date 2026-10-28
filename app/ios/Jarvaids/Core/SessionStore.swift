//
//  SessionStore.swift
//  JarvaidsCore
//
//  The observable state a screen needs, and the loop that keeps it current.
//
//  The refresh strategy is the one API.md prescribes and is not an implementation
//  detail to change casually: "Poll events for changes, then refresh the snapshot;
//  events contain change metadata, not a patch stream. On reconnect, fetch the snapshot
//  first." So this type never tries to mutate a record from an event. An event only ever
//  answers the question "is anything different", and the snapshot is the truth.
//
//  This file holds no view code. It publishes derived collections, and what a screen does
//  with them belongs to the UI layer, which is owned elsewhere.
//

import Foundation
import Observation

@MainActor
@Observable
public final class SessionStore {

    // MARK: Tuning

    /// How long to wait between event polls.
    ///
    /// One named constant, on purpose: this is the number that trades "the board feels
    /// live" against "eight phones hammering one laptop in a meeting room". Two seconds
    /// is a starting point, not a measured result. Change it here and nowhere else.
    public static let pollInterval: Duration = .seconds(2)

    /// What to wait after a failed poll before trying again. Longer than `pollInterval`
    /// so that a server that has gone away is not asked twice a second.
    public static let pollRetryInterval: Duration = .seconds(5)

    // MARK: Observable state

    /// The last snapshot fetched. Nil until the first successful load.
    public private(set) var snapshot: SessionSnapshot?

    /// The event cursor. Everything up to and including this sequence has been seen.
    public private(set) var cursor: Int = 0

    /// Set when the session has been deleted, in which case there is no snapshot and
    /// there never will be one again.
    public private(set) var deletionReceipt: DeletionReceipt?

    public private(set) var connection: ConnectionState = .idle

    /// The most recent failure, kept so a screen can show it without the store deciding
    /// what "showing an error" looks like. Cleared by the next success.
    public private(set) var lastError: JarvaidsError?

    /// Records that changed in the most recent refresh, so a screen can draw attention to
    /// them rather than silently redrawing the board.
    public private(set) var recentlyChangedRecordIDs: Set<RecordID> = []

    public enum ConnectionState: Sendable, Equatable {
        case idle
        case loading
        case live
        /// Polling is still running, but the last attempt failed.
        case degraded
        /// Polling has stopped for good: the session is closed, deleted or unreachable
        /// with a credential that will never work.
        case stopped(reason: String)
    }

    // MARK: Dependencies

    private let client: JarvaidsAPIClient
    private var pollTask: Task<Void, Never>?

    public init(client: JarvaidsAPIClient) {
        self.client = client
    }

    // There is deliberately no `deinit` cancelling the poll task. A `deinit` on a
    // main-actor-isolated class cannot touch isolated state without a concurrency
    // complaint, so shutting the loop down is the owner's job: call `stopPolling()` when
    // the screen goes away.

    // MARK: Derived state
    //
    // All of this is recomputed from `snapshot` rather than maintained alongside it.
    // A session holds at most a thousand records, so the cost is irrelevant next to the
    // cost of two representations of the same board disagreeing.

    public var session: Session? { snapshot?.session }
    public var members: [Member] { snapshot?.members ?? [] }
    public var role: ActorRole { snapshot?.role ?? .unknown("absent") }
    public var isFacilitator: Bool { role == .facilitator }

    public var sources: [Entity<SourceData>] {
        (snapshot?.records ?? []).compactMap(\.source)
    }

    public var proposals: [Entity<ProposalData>] {
        (snapshot?.records ?? []).compactMap(\.proposal)
    }

    public var items: [Entity<ItemData>] {
        (snapshot?.records ?? []).compactMap(\.item)
    }

    public var jobs: [Entity<JobData>] {
        (snapshot?.records ?? []).compactMap(\.job)
    }

    public var exports: [Entity<ExportRecordData>] {
        (snapshot?.records ?? []).compactMap(\.export)
    }

    /// Everything a person still has to look at. The product's whole point sits here.
    public var pendingProposals: [Entity<ProposalData>] {
        proposals.filter { $0.data.status == .needsReview }
    }

    /// Proposals that were waiting for review when something underneath them changed.
    /// They still need a person, they just need re-reading first.
    public var staleProposals: [Entity<ProposalData>] {
        proposals.filter { $0.data.status == .stale }
    }

    /// The team's work: accepted and still current.
    public var acceptedItems: [Entity<ItemData>] {
        items.filter { $0.data.status == .accepted }
    }

    /// Accepted items whose sources or dependencies moved underneath them.
    /// API.md: "show stale dependencies visibly". Never repair these automatically.
    public var staleItems: [Entity<ItemData>] {
        items.filter { $0.data.status == .stale }
    }

    public var undoneItems: [Entity<ItemData>] {
        items.filter { $0.data.status == .undone }
    }

    /// Anything provisional or broken that a person has not resolved. This is the number
    /// worth putting on screen before anyone exports or closes.
    public var unresolvedCount: Int {
        pendingProposals.count + staleProposals.count + staleItems.count
    }

    public var activeJobs: [Entity<JobData>] {
        jobs.filter(\.data.isActive)
    }

    /// A count per job state, for a progress indicator that does not need the jobs.
    public var jobProgress: JobProgress {
        JobProgress(jobs: jobs.map(\.data))
    }

    public struct JobProgress: Sendable, Equatable {
        public var queued = 0
        public var running = 0
        public var succeeded = 0
        public var failed = 0
        public var cancelled = 0

        init(jobs: [JobData]) {
            for job in jobs {
                switch job.status {
                case .queued: queued += 1
                case .running: running += 1
                case .succeeded: succeeded += 1
                case .failed: failed += 1
                case .cancelled: cancelled += 1
                case .unknown: break
                }
            }
        }

        public var active: Int { queued + running }
        public var isBusy: Bool { active > 0 }
    }

    /// Whether capture is on. The UI disables photo and note controls when this is false,
    /// rather than letting them fail with `capture_inactive`.
    public var isCaptureActive: Bool {
        session?.state.acceptsCapture ?? false
    }

    /// Members who have not acknowledged the policy version currently in force.
    /// Activation is blocked until this is empty, viewers included.
    public var membersAwaitingAcknowledgement: [Member] {
        snapshot?.membersAwaitingAcknowledgement ?? []
    }

    /// Whether this device's own actor still needs to acknowledge. Note that a roster
    /// change bumps the policy version and revokes everyone's acknowledgement, so this
    /// can become true again part way through a meeting.
    public var needsMyAcknowledgement: Bool {
        guard let snapshot, let me = snapshot.viewer else { return false }
        return !me.hasAcknowledged(policyVersion: snapshot.session.policyVersion)
    }

    /// Records that reference a record which is no longer current. Useful for drawing the
    /// broken edge, not for repairing it.
    public func dependents(of recordID: RecordID) -> [Record] {
        (snapshot?.records ?? []).filter { record in
            switch record.payload {
            case .proposal(let data): return data.refs.contains { $0.id == recordID }
            case .item(let data): return data.refs.contains { $0.id == recordID }
            case .job(let data): return data.refs.contains { $0.id == recordID }
            case .source, .export, .unrecognised: return false
            }
        }
    }

    public func record(_ id: RecordID) -> Record? {
        snapshot?.records.first { $0.id == id }
    }

    // MARK: Loading

    /// Fetches the snapshot and resets the cursor to match it.
    ///
    /// Call this on first load and on every reconnect. The cursor is taken from the
    /// snapshot's own sequence number rather than left where it was, because a snapshot
    /// already contains the effect of every event up to that number.
    public func refresh() async {
        connection = snapshot == nil ? .loading : connection
        do {
            switch try await client.snapshot() {
            case .live(let fresh):
                apply(fresh)
            case .deleted(let receipt):
                deletionReceipt = receipt
                snapshot = nil
                stopPolling(reason: "The session has been deleted.")
            }
        } catch let error as JarvaidsError {
            handle(error)
        } catch {
            lastError = .malformedResponse(String(describing: error))
            connection = .degraded
        }
    }

    private func apply(_ fresh: SessionSnapshot) {
        let previous = snapshot
        snapshot = fresh
        cursor = max(cursor, fresh.session.seq)
        lastError = nil
        connection = .live
        recentlyChangedRecordIDs = Self.changedRecordIDs(from: previous, to: fresh)
    }

    /// Compares two snapshots by revision. Cheap, and it means a screen can highlight what
    /// moved without the server having to describe the change.
    private static func changedRecordIDs(
        from previous: SessionSnapshot?,
        to current: SessionSnapshot
    ) -> Set<RecordID> {
        guard let previous else { return [] }
        var before: [RecordID: Revision] = [:]
        before.reserveCapacity(previous.records.count)
        for record in previous.records { before[record.id] = record.revision }
        var changed: Set<RecordID> = []
        for record in current.records where before[record.id] != record.revision {
            changed.insert(record.id)
        }
        return changed
    }

    // MARK: Polling

    /// Starts the poll loop. Safe to call more than once; the second call is a no-op.
    public func startPolling() {
        guard pollTask == nil else { return }
        pollTask = Task { [weak self] in
            await self?.pollLoop()
        }
    }

    public func stopPolling(reason: String? = nil) {
        pollTask?.cancel()
        pollTask = nil
        if let reason {
            connection = .stopped(reason: reason)
        }
    }

    private func pollLoop() async {
        // API.md: "On reconnect, fetch the snapshot first." A cursor on its own cannot
        // rebuild a board, so the loop never starts from events alone.
        await refresh()

        while !Task.isCancelled {
            if case .stopped = connection { return }
            let interval: Duration
            do {
                let changed = try await drainEvents()
                if changed { await refresh() }
                lastError = nil
                if connection != .live { connection = .live }
                interval = Self.pollInterval
            } catch let error as JarvaidsError {
                handle(error)
                if case .stopped = connection { return }
                interval = Self.pollRetryInterval
            } catch {
                lastError = .malformedResponse(String(describing: error))
                connection = .degraded
                interval = Self.pollRetryInterval
            }
            do {
                try await Task.sleep(for: interval)
            } catch {
                return  // Cancelled.
            }
        }
    }

    /// Reads every event page waiting for us and advances the cursor.
    ///
    /// Returns whether any of them implies a record changed. A heartbeat moves the
    /// sequence number without touching a record, and refetching a whole snapshot once a
    /// minute for that would be waste on a meeting-room network.
    @discardableResult
    private func drainEvents() async throws -> Bool {
        var sawRecordChange = false
        var guardCounter = 0
        while true {
            let page = try await client.events(after: cursor)
            for event in page.events where event.type.impliesRecordChange {
                sawRecordChange = true
            }
            cursor = max(cursor, page.nextAfter)
            guard page.hasMore else { break }
            // The server pages at 200 events. This bound only exists so that a server
            // that always claims `has_more` cannot spin this loop forever.
            guardCounter += 1
            if guardCounter > 50 { break }
        }
        return sawRecordChange
    }

    private func handle(_ error: JarvaidsError) {
        lastError = error
        switch error {
        case .unauthorized, .forbidden:
            // The credential will not start working by itself, and API.md says to stop
            // writes and show the access state rather than keep trying.
            stopPolling(reason: error.errorDescription ?? "Access was refused.")
        case .notFound:
            stopPolling(reason: "This session is no longer on the server.")
        case .conflict(let conflict) where conflict.kind == .sessionDeleted:
            stopPolling(reason: "The session has been deleted.")
        default:
            connection = .degraded
        }
    }

    // MARK: Writing

    /// Submits a command and refreshes afterwards.
    ///
    /// The refresh is not an optimisation, it is the contract: API.md says to "read the
    /// returned revisions after every operation", and the snapshot is what the next
    /// command's `expected_revision` has to come from.
    ///
    /// Errors are rethrown rather than swallowed. A caller that has unsaved text in a
    /// field is the only code that can preserve it, and API.md requires that it be
    /// preserved across a conflict.
    @discardableResult
    public func submit<Result>(
        _ intent: CommandIntent<Result>
    ) async throws -> CommandResponse<Result> {
        do {
            let response = try await client.submit(intent)
            await refresh()
            return response
        } catch let error as JarvaidsError {
            lastError = error
            // A 409 means the board moved. Refreshing shows the person what it moved to;
            // it does not resubmit anything, and the error still reaches the caller so
            // that whatever they had typed can be kept on screen.
            if error.requiresRefresh { await refresh() }
            throw error
        }
    }
}
