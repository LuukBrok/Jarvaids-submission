/** In-memory session synchronisation. Reads retry; mutations never retry themselves.
 * start/stop control local polling. pause sends one explicit server pause.
 * Heartbeats require explicit opt-in after every visibility/connectivity interruption.
 * onAttention receives bounded notifications; callers may retain an uncertain intent.
 */
export class ConnectionError extends Error {
  constructor(code, {outcome = "not_sent", intent, cause} = {}) {
    super(code, {cause}); this.name = "ConnectionError"; this.code = code;
    this.outcome = outcome; if (intent) this.intent = intent;
  }
}

const TERMINAL = new Set(["revoked", "expired", "deleted", "disposed"]);
const CONTROLS = new Set(["session.pause", "session.close", "session.heartbeat", "participant.remove", "consent.withdraw", "invitation.revoke"]);
const CURSOR_ERRORS = new Set(["cursor_ahead", "invalid_cursor", "stale_cursor", "resync_required"]);

/** Board z-order, innermost first, per spec/canvas-layout.md: the layout
 * engine's guesses, then what people placed, then whatever was touched last,
 * with ties broken on record id so two clients agree. Position deltas carry
 * their own order inputs, so no full order is needed on the wire and the client
 * derives it here.
 *
 * The same rule lives in Service._board_order, in Python, because the server
 * sends board_order with a full snapshot. Two copies of one rule drift, and a
 * drift here means two people in the same meeting see a different item on top.
 * Exported rather than inlined so tests/board-order-unit.mjs can run it over a
 * server-generated fixture and compare: a test that restated the sort would
 * only pin this copy to itself.
 */
export function boardOrder(records) {
  const positioned = records.filter(record => record.position != null);
  if (positioned.some(record => typeof record.position.hand_placed !== "boolean" || !Number.isFinite(record.position.placed_at))) throw new ConnectionError("invalid_snapshot");
  positioned.sort((a, b) => Number(a.position.hand_placed) - Number(b.position.hand_placed) ||
    a.position.placed_at - b.position.placed_at || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
  return positioned.map(record => record.id);
}

export class SessionConnection {
  #client; #options; #state = null; #running = false; #disposed = false;
  #visible = true; #online = true; #epoch = 0; #timer; #heartbeatTimer;
  #read = null; #readAbort = null; #full = true; #failures = 0; #again = false;
  #heartbeat = false; #control = null; #pending = null; #sequence = null;
  #controlRefresh = false;
  #unsubscribe;

  constructor(client, options = {}) {
    this.#client = client;
    this.#options = {pollIntervalMs: 1000, maxBackoffMs: 30000, heartbeatIntervalMs: 30000,
      timeoutMs: 10000, maxRecords: 1000, maxStateBytes: 16 * 1024 * 1024,
      random: Math.random, setTimeout, clearTimeout, onUpdate: () => {}, onAttention: () => {}, ...options};
    for (const key of ["pollIntervalMs", "maxBackoffMs", "heartbeatIntervalMs", "timeoutMs", "maxRecords", "maxStateBytes"]) {
      if (!Number.isFinite(this.#options[key]) || this.#options[key] <= 0) throw new TypeError("Positive finite " + key + " required");
    }
    if (!Number.isInteger(this.#options.timeoutMs) || this.#options.timeoutMs > 120000) throw new TypeError("Transport deadline out of range");
    if (this.#options.maxRecords > 10000 || this.#options.maxStateBytes > 64 * 1024 * 1024) throw new TypeError("Cache limits too large");
    if (["pollIntervalMs", "maxBackoffMs", "heartbeatIntervalMs", "timeoutMs"].some(key => this.#options[key] > 300000) ||
        this.#options.pollIntervalMs < 100 || this.#options.heartbeatIntervalMs < 1000) throw new TypeError("Timer limits out of range");
    this.#unsubscribe = client.onState(state => {
      if (TERMINAL.has(state)) { this.stop(); this.#state = null; this.#pending = null; this.#sequence = null; this.#attention("client_" + state); }
    });
  }

  get snapshot() { return this.#state === null ? null : structuredClone(this.#state); }
  get cursor() { return this.#state?.session.seq ?? null; }
  get pendingControl() { return this.#pending ? Object.freeze({operation: this.#pending.operation, intent: this.#pending.intent}) : null; }
  #attention(code, extra = {}) { try { this.#options.onAttention({code, ...extra}); } catch {} }
  #usable() { return !this.#disposed && this.#client.state === "active"; }
  #pollable() { return this.#running && this.#visible && this.#online && this.#usable(); }
  #clearTimers() {
    this.#options.clearTimeout(this.#timer); this.#options.clearTimeout(this.#heartbeatTimer);
    this.#timer = this.#heartbeatTimer = undefined;
  }
  #invalidateRead() {
    this.#epoch++; this.#readAbort?.abort(); this.#readAbort = null; this.#read = null; this.#full = true;
  }

  async start() {
    if (!this.#usable()) throw new ConnectionError("connection_inactive");
    if (this.#running) return this.snapshot;
    this.#running = true; this.#full = true;
    if (this.#pollable()) await this.#poll();
    return this.snapshot;
  }

  stop() {
    this.#running = false; this.#epoch++; this.disableHeartbeat(); this.#clearTimers();
    this.#readAbort?.abort(); this.#readAbort = null; this.#read = null;
    this.#abortControl("connection_stopped");
  }

  dispose() { if (this.#disposed) return; this.stop(); this.#disposed = true; this.#state = null; this.#pending = null; this.#unsubscribe?.(); }

  #suspend(code) {
    this.disableHeartbeat(); this.#epoch++; this.#clearTimers();
    this.#readAbort?.abort(); this.#read = null; this.#readAbort = null;
    this.#abortControl(code); this.#attention(code, {needsAttention: true});
  }
  setVisibility(visible) {
    if (typeof visible !== "boolean") throw new TypeError("Boolean visibility required");
    if (visible === this.#visible) return;
    this.#visible = visible;
    if (!visible) this.#suspend("hidden");
    else if (this.#pollable()) { this.#full = true; this.#schedule(0); this.#attention("visible_heartbeat_requires_opt_in"); }
  }
  setOnline(online) {
    if (typeof online !== "boolean") throw new TypeError("Boolean connectivity required");
    if (online === this.#online) return;
    this.#online = online;
    if (!online) this.#suspend("offline");
    else if (this.#pollable()) { this.#full = true; this.#schedule(0); this.#attention("reconnected_heartbeat_requires_opt_in"); }
  }

  #schedule(delay) {
    this.#options.clearTimeout(this.#timer);
    if (this.#pollable()) this.#timer = this.#options.setTimeout(() => { this.#timer = undefined; void this.#poll(); }, delay);
  }

  /** Brings the next read forward to now: after a command this person sent
   * outside the control lane, so its effect shows as soon as the server has
   * it instead of up to a poll interval later. A read already in flight is
   * left alone, but it may have started before the command landed, so the
   * read after it comes at once rather than at the interval. A connection
   * that cannot poll ignores it. */
  pollSoon() {
    if (!this.#pollable()) return;
    if (this.#read) this.#again = true; else this.#schedule(0);
  }

  async #fetchState(forceFull = false) {
    if (this.#read) { await this.#read; if (!forceFull) return; }
    if (!this.#usable() || !this.#online) throw new ConnectionError("connection_inactive");
    const epoch = this.#epoch, full = forceFull || this.#full || !this.#state;
    const cursor = this.cursor; const abort = new AbortController(); this.#readAbort = abort;
    const task = (async () => {
      const options = {signal: abort.signal, timeoutMs: this.#options.timeoutMs};
      let result = await (full ? this.#client.snapshot(options) : this.#client.delta(cursor, options));
      let applyFull = full;
      if (!full && result?.resync_required === true) {
        if (abort.signal.aborted || epoch !== this.#epoch || !this.#usable()) throw new ConnectionError("read_obsolete");
        this.#full = true;
        result = await this.#client.snapshot(options); applyFull = true;
      }
      if (epoch !== this.#epoch || abort.signal.aborted || !this.#usable()) throw new ConnectionError("read_obsolete");
      this.#apply(result, applyFull, cursor); this.#full = false;
    })();
    this.#read = task;
    try { await task; } finally { if (this.#read === task) { this.#read = null; this.#readAbort = null; } }
  }

  #apply(result, full, cursor) {
    if (result?.state === "deleted" && result.content_available === false) {
      this.stop(); this.#state = null; this.#pending = null; this.#sequence = null;
      this.#attention("session_deleted"); return;
    }
    if (result?.has_more === true || result?.truncated === true || result?.resync_required === true) throw new ConnectionError("resync_required");
    const seq = full ? result?.session?.seq : result?.current_seq;
    if (!Number.isSafeInteger(seq) || seq < 0 || (!full && (seq < cursor || result.since_seq !== cursor)) ||
        result?.session?.seq !== seq || !Array.isArray(result.records) || !Array.isArray(result.members) ||
        (full && !Array.isArray(result.board_order)) || result.records.length > this.#options.maxRecords ||
        result.members.length > 1000 ||
        !Number.isSafeInteger(result.next_control_sequence) || result.next_control_sequence < 1) throw new ConnectionError("invalid_snapshot");
    const records = new Map(full ? [] : this.#state.records.map(record => [record.id, record]));
    const seen = new Set();
    for (const record of result.records) {
      if (!record || typeof record.id !== "string" || seen.has(record.id)) throw new ConnectionError("invalid_snapshot");
      seen.add(record.id); records.set(record.id, record);
    }
    if (records.size > this.#options.maxRecords) throw new ConnectionError("cache_limit");
    const candidate = {...result, records: [...records.values()]};
    candidate.board_order = boardOrder(candidate.records);
    delete candidate.since_seq; delete candidate.current_seq;
    if (new TextEncoder().encode(JSON.stringify(candidate)).byteLength > this.#options.maxStateBytes) throw new ConnectionError("cache_limit");
    this.#sequence = candidate.next_control_sequence;
    if (full) this.#controlRefresh = false;
    candidate.next_control_sequence = this.#sequence; this.#state = structuredClone(candidate);
    if (!this.#canHeartbeat()) this.disableHeartbeat();
    try { this.#options.onUpdate(this.snapshot); } catch {}
  }

  async #poll() {
    if (!this.#pollable()) return;
    if (this.#read) { this.#schedule(this.#options.pollIntervalMs); return; }
    const epoch = this.#epoch;
    let delay = this.#options.pollIntervalMs;
    try { await this.#fetchState(); this.#failures = 0; if (this.#again) { this.#again = false; delay = 0; } }
    catch (error) {
      if (epoch !== this.#epoch || !this.#pollable()) return;
      if (CURSOR_ERRORS.has(error.code) || error.code === "invalid_snapshot") this.#full = true;
      this.#failures = Math.min(16, this.#failures + 1);
      const random = Math.min(1, Math.max(0, Number(this.#options.random()) || 0));
      delay = Math.min(this.#options.maxBackoffMs, this.#options.pollIntervalMs * 2 ** this.#failures) * (.5 + random * .5);
      this.disableHeartbeat(); this.#attention("sync_failed", {errorCode: error.code ?? "read_failed", needsAttention: true});
    }
    if (epoch === this.#epoch) this.#schedule(delay);
  }

  #canHeartbeat() {
    return this.#pollable() && this.#state?.session.state === "active" &&
      this.#state.members.some(member => member.id === this.#state.actor_id && member.role === "facilitator");
  }
  enableHeartbeat() {
    if (!this.#canHeartbeat() || this.#pending || this.#control) throw new ConnectionError("heartbeat_not_available");
    this.#heartbeat = true; this.#scheduleHeartbeat();
  }
  disableHeartbeat() { this.#heartbeat = false; this.#options.clearTimeout(this.#heartbeatTimer); this.#heartbeatTimer = undefined; }
  #scheduleHeartbeat() {
    this.#options.clearTimeout(this.#heartbeatTimer);
    if (this.#heartbeat && this.#canHeartbeat()) this.#heartbeatTimer = this.#options.setTimeout(async () => {
      this.#heartbeatTimer = undefined;
      if (!this.#heartbeat || !this.#canHeartbeat()) return;
      try { await this.submitControl("session.heartbeat", {}); }
      catch (error) { this.disableHeartbeat(); this.#attention("heartbeat_failed", {errorCode: error.code, needsAttention: true}); }
      this.#scheduleHeartbeat();
    }, this.#options.heartbeatIntervalMs);
  }

  #abortControl(code) {
    const active = this.#control;
    if (!active) return;
    this.#control = null; active.abort.abort(); this.#pending = active;
    this.#attention(code, {outcome: "unknown", intent: active.intent, operation: active.operation});
  }

  /** One mutation in flight; no queue. Returned errors retain the exact intent. */
  async submitControl(operation, payload = {}) {
    if (!CONTROLS.has(operation)) throw new ConnectionError("not_a_control");
    if (!this.#usable() || !this.#online) throw new ConnectionError("connection_inactive");
    if (this.#control) throw new ConnectionError("control_busy");
    if (this.#pending) throw new ConnectionError("control_uncertain", {outcome: "unknown", intent: this.#pending.intent});
    if (this.#controlRefresh) throw new ConnectionError("control_refresh_required");
    if (!this.#state) throw new ConnectionError("snapshot_required");
    const entry = {operation, sequence: this.#sequence, intent: this.#client.intent(operation, payload, {controlSequence: this.#sequence}), abort: new AbortController()};
    return this.#sendControl(entry);
  }

  async #sendControl(entry) {
    this.#control = entry;
    try {
      const result = await this.#client.submit(entry.intent, {signal: entry.abort.signal, timeoutMs: this.#options.timeoutMs});
      if (this.#control !== entry || entry.abort.signal.aborted || !this.#usable()) throw new ConnectionError("control_obsolete", {outcome: "unknown", intent: entry.intent});
      this.#sequence = Math.max(this.#sequence, entry.sequence + 1); this.#pending = null; this.#invalidateRead(); this.#schedule(0);
      return {intent: entry.intent, result};
    } catch (error) {
      if (this.#control === entry) {
        if (error.outcome === "unknown" || !error.outcome) {
          this.#pending = entry; this.disableHeartbeat();
          this.#attention("control_uncertain", {operation: entry.operation, intent: entry.intent, outcome: "unknown"});
        } else if (error.status === 409) {
          this.#controlRefresh = true;
          this.#invalidateRead(); this.#schedule(0); this.disableHeartbeat();
          this.#attention("control_conflict", {operation: entry.operation, intent: entry.intent, needsAttention: true});
        }
      }
      throw new ConnectionError(error.code ?? "control_failed", {outcome: error.outcome ?? "unknown", intent: entry.intent, cause: error});
    } finally { if (this.#control === entry) this.#control = null; }
  }

  /** Caller explicitly chooses to resend the retained intent; never allocates a new sequence. */
  retryPendingControl() {
    if (!this.#usable() || !this.#online) return Promise.reject(new ConnectionError("connection_inactive"));
    if (this.#control || !this.#pending) return Promise.reject(new ConnectionError("no_retry_available"));
    const entry = {...this.#pending, abort: new AbortController()};
    return this.#sendControl(entry);
  }

  /** Explicitly abandon automatic reconciliation; the caller receives the old intent. */
  discardPendingControl() {
    if (this.#control) throw new ConnectionError("control_busy");
    const previous = this.pendingControl;
    this.#pending = null; this.#controlRefresh = true; this.#invalidateRead(); this.#schedule(0);
    if (previous) this.#attention("control_reconciliation_abandoned", {...previous, outcome: "unknown"});
    return previous;
  }

  /** An explicit stop request may supersede uncertain heartbeat, after a fresh read. */
  async pause() {
    this.disableHeartbeat();
    if (this.#control?.operation === "session.heartbeat") this.#abortControl("heartbeat_superseded_by_pause");
    if (this.#control) throw new ConnectionError("control_busy");
    if (this.#pending) {
      if (this.#pending.operation !== "session.heartbeat") throw new ConnectionError("control_uncertain", {outcome: "unknown", intent: this.#pending.intent});
      const displaced = this.#pending;
      const epoch = this.#epoch;
      await this.#fetchState(true);
      if (this.#pending !== displaced || this.#control || epoch !== this.#epoch || !this.#usable()) throw new ConnectionError("pause_supersession_conflict", {intent: displaced.intent});
      this.#attention("heartbeat_superseded_by_pause", {intent: displaced.intent, outcome: "unknown"});
      this.#pending = null;
    }
    return this.submitControl("session.pause", {});
  }
}
