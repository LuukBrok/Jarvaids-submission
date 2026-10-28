import test from "node:test";
import assert from "node:assert/strict";
import {SessionConnection} from "../session-sync.mjs";

const flush = async () => { for (let i = 0; i < 30; i++) await Promise.resolve(); };
function deferred() { let resolve, reject; const promise = new Promise((a, b) => { resolve = a; reject = b; }); return {promise, resolve, reject}; }
function error(code, outcome = "response_received", status = 409) { return Object.assign(new Error(code), {code, outcome, status}); }
class Clock {
  now = 0; id = 0; timers = new Map();
  setTimeout = (fn, delay) => { const id = ++this.id; this.timers.set(id, {fn, at: this.now + delay, delay}); return id; };
  clearTimeout = id => this.timers.delete(id);
  async tick(ms) {
    const target = this.now + ms;
    for (;;) {
      const next = [...this.timers].filter(([, t]) => t.at <= target).sort((a, b) => a[1].at - b[1].at)[0];
      if (!next) break;
      this.now = next[1].at; this.timers.delete(next[0]); next[1].fn(); await flush();
    }
    this.now = target; await flush();
  }
}
class Client {
  state = "active"; listeners = new Set(); calls = []; snapshots = []; deltas = []; submissions = [];
  value = {session: {seq: 1, state: "active"}, actor_id: "owner", members: [{id: "owner", role: "facilitator"}],
    records: [{id: "one", revision: 1, data: {text: "one"}}], board_order: [], next_control_sequence: 1};
  onState(fn) { this.listeners.add(fn); return () => this.listeners.delete(fn); }
  setState(value) { this.state = value; for (const fn of this.listeners) fn(value); }
  async snapshot(options) { this.calls.push(["snapshot", options]); return this.snapshots.length ? this.snapshots.shift()() : structuredClone(this.value); }
  async delta(cursor, options) { this.calls.push(["delta", cursor, options]); return this.deltas.length ? this.deltas.shift()(cursor) : {...structuredClone(this.value), since_seq: cursor, current_seq: this.value.session.seq, records: []}; }
  intent(operation, payload, {controlSequence}) { return Object.freeze({requestId: String(this.calls.length), serialized: JSON.stringify({operation, payload, control_sequence: controlSequence})}); }
  async submit(intent, options) {
    this.calls.push(["submit", intent, options]);
    if (this.submissions.length) return this.submissions.shift()(intent);
    const parsed = JSON.parse(intent.serialized); this.value.next_control_sequence++;
    if (parsed.operation === "session.pause") { this.value.session.state = "paused"; this.value.session.seq++; }
    return {result: {state: this.value.session.state}, seq: this.value.session.seq};
  }
}
function setup(options = {}) {
  const clock = new Clock(), client = new Client(), updates = [], attention = [];
  const connection = new SessionConnection(client, {setTimeout: clock.setTimeout, clearTimeout: clock.clearTimeout,
    random: () => 1, onUpdate: value => updates.push(value), onAttention: value => attention.push(value), ...options});
  return {clock, client, connection, updates, attention};
}

test("delta merges transaction cursor and future cursor requests a full resynchronisation", async () => {
  const {connection, client, clock} = setup(); await connection.start();
  client.value.session.seq = 2; client.deltas.push(cursor => ({...structuredClone(client.value), since_seq: cursor, current_seq: 2,
    records: [{id: "two", revision: 1, data: {text: "two"}}]}));
  await clock.tick(1000); assert.equal(connection.cursor, 2); assert.equal(connection.snapshot.records.length, 2);
  client.deltas.push(() => { throw error("cursor_ahead"); }); await clock.tick(1000); assert.equal(connection.cursor, 2);
  await clock.tick(2000); assert.equal(client.calls.at(-1)[0], "snapshot"); assert.equal(connection.snapshot.records.length, 1);
  assert.equal(client.calls.filter(call => call[0] === "submit").length, 0); connection.dispose();
});

test("pollSoon brings the next read forward and leaves a read in flight alone", async () => {
  const {connection, client, clock} = setup(); await connection.start();
  const reads = () => client.calls.filter(call => call[0] !== "submit").length;
  const before = reads();
  connection.pollSoon(); await clock.tick(0);
  assert.equal(reads(), before + 1, "a read happens now, not at the interval");
  // A read that has not answered yet: pollSoon must not start a second one.
  const slow = deferred(); client.deltas.push(() => slow.promise);
  await clock.tick(1000); const inFlight = reads();
  connection.pollSoon(); await clock.tick(0);
  assert.equal(reads(), inFlight, "no second read while one is in flight");
  // The read in flight may predate the command, so the next one comes at once.
  slow.resolve({...structuredClone(client.value), since_seq: 1, current_seq: 1, records: []}); await flush();
  await clock.tick(0);
  assert.equal(reads(), inFlight + 1, "the read after an in-flight one comes at once, not at the interval");
  connection.stop(); connection.pollSoon(); await clock.tick(0);
  assert.equal(reads(), inFlight + 1, "a stopped connection ignores it");
  connection.dispose();
});

test("read failures use bounded backoff and never overlap or advance the last cursor", async () => {
  const {connection, client, clock} = setup(); await connection.start();
  for (let i = 0; i < 8; i++) client.deltas.push(() => { throw error("offline", "unknown", 0); });
  await clock.tick(1000); assert.equal(connection.cursor, 1);
  assert.equal([...clock.timers.values()][0].delay, 2000);
  await clock.tick(2000); assert.equal([...clock.timers.values()][0].delay, 4000);
  await clock.tick(120000); assert.ok([...clock.timers.values()].every(timer => timer.delay <= 30000));
  connection.dispose();
});

test("stop aborts polling and ignores a late response even when transport ignores abort", async () => {
  const {connection, client, clock, updates} = setup(); const pending = deferred(); client.snapshots.push(() => pending.promise);
  const start = connection.start(); await flush(); await clock.tick(5000); assert.equal(client.calls.length, 1);
  connection.stop(); assert.equal(client.calls[0][1].signal.aborted, true);
  pending.resolve(structuredClone(client.value)); await start; assert.equal(connection.snapshot, null); assert.equal(updates.length, 0);
  await clock.tick(100000); assert.equal(client.calls.length, 1); connection.dispose();
});

test("cache bounds reject oversize or duplicate record batches without partial state", async () => {
  const {connection, client, clock, attention} = setup({maxRecords: 2}); await connection.start();
  client.deltas.push(cursor => ({...structuredClone(client.value), since_seq: cursor, current_seq: 1,
    records: [{id: "two"}, {id: "three"}]})); await clock.tick(1000);
  assert.equal(connection.snapshot.records.length, 1); assert.equal(connection.cursor, 1);
  assert.equal(attention.at(-1).errorCode, "cache_limit");
  client.deltas.push(cursor => ({...structuredClone(client.value), since_seq: cursor, current_seq: 1, records: [{id: "one"}, {id: "one"}]}));
  await clock.tick(2000); assert.equal(attention.at(-1).errorCode, "invalid_snapshot"); assert.equal(connection.snapshot.records[0].data.text, "one");
  connection.dispose();
});

test("heartbeats require explicit facilitator opt-in and do not resume after hidden or offline", async () => {
  const {connection, client, clock} = setup(); await connection.start(); await clock.tick(30000);
  assert.equal(client.calls.filter(c => c[0] === "submit").length, 0);
  connection.enableHeartbeat(); await clock.tick(30000); assert.equal(client.calls.filter(c => c[0] === "submit").length, 1);
  connection.setVisibility(false); connection.setVisibility(true); await clock.tick(60000);
  assert.equal(client.calls.filter(c => c[0] === "submit").length, 1);
  connection.enableHeartbeat(); connection.setOnline(false); connection.setOnline(true); await clock.tick(60000);
  assert.equal(client.calls.filter(c => c[0] === "submit").length, 1);
  client.value.members[0].role = "participant"; await clock.tick(1000);
  assert.throws(() => connection.enableHeartbeat(), /heartbeat_not_available/);
  client.value.members[0].role = "facilitator"; client.value.session.state = "paused"; await clock.tick(1000);
  assert.throws(() => connection.enableHeartbeat(), /heartbeat_not_available/); connection.dispose();
});

test("control lane rejects a concurrent mutation and retains exact uncertain intent for explicit retry", async () => {
  const {connection, client, clock} = setup(); await connection.start(); const pending = deferred(); client.submissions.push(() => pending.promise);
  const first = connection.submitControl("session.heartbeat"); await flush();
  await assert.rejects(connection.submitControl("session.pause"), /control_busy/);
  const original = client.calls.find(c => c[0] === "submit")[1]; pending.reject(error("timeout", "unknown", 0));
  await assert.rejects(first, e => e.intent === original && e.outcome === "unknown");
  assert.equal(connection.pendingControl?.intent, original);
  await clock.tick(100000); assert.equal(client.calls.filter(c => c[0] === "submit").length, 1);
  await connection.retryPendingControl(); assert.equal(client.calls.filter(c => c[0] === "submit")[1][1], original);
  assert.equal(connection.pendingControl, null); connection.dispose();
});

test("pause supersedes uncertain heartbeat with one fresh explicit intent and never activates", async () => {
  const {connection, client, attention} = setup(); await connection.start();
  client.submissions.push(() => { throw error("timeout", "unknown", 0); });
  await assert.rejects(connection.submitControl("session.heartbeat")); const displaced = connection.pendingControl.intent;
  await connection.pause(); const sends = client.calls.filter(c => c[0] === "submit");
  assert.deepEqual(sends.map(c => JSON.parse(c[1].serialized).operation), ["session.heartbeat", "session.pause"]);
  assert.ok(attention.some(event => event.intent === displaced && event.code === "heartbeat_superseded_by_pause"));
  connection.dispose();
});

test("conflict is surfaced once and refreshed without rebasing or retrying mutation", async () => {
  const {connection, client, clock} = setup(); await connection.start();
  client.submissions.push(() => { throw error("control_sequence_conflict"); });
  await assert.rejects(connection.pause(), e => e.code === "control_sequence_conflict" && Boolean(e.intent));
  await clock.tick(60000); assert.equal(client.calls.filter(c => c[0] === "submit").length, 1);
  assert.ok(client.calls.filter(c => c[0] === "snapshot").length >= 2); connection.dispose();
});

test("terminal client state clears caches, cancels controls and removes listeners on dispose", async () => {
  const {connection, client, clock} = setup(); await connection.start(); connection.enableHeartbeat();
  client.setState("revoked"); assert.equal(connection.snapshot, null); await clock.tick(100000);
  assert.equal(client.calls.filter(c => c[0] === "submit").length, 0); connection.dispose(); assert.equal(client.listeners.size, 0);
});

test("a polling response from before a control commit cannot regress sequence or state", async () => {
  const {connection, client, clock} = setup(); await connection.start(); const pending = deferred();
  const old = {...structuredClone(client.value), since_seq: 1, current_seq: 1}; client.deltas.push(() => pending.promise);
  await clock.tick(1000); await connection.pause(); pending.resolve(old); await flush(); await clock.tick(0);
  assert.equal(connection.snapshot.session.state, "paused");
  assert.equal(connection.snapshot.next_control_sequence, 2);
  const result = await connection.submitControl("session.pause");
  assert.equal(JSON.parse(result.intent.serialized).control_sequence, 2); connection.dispose();
});

test("full resynchronisation replaces a future control sequence rather than permanently wedging controls", async () => {
  const {connection, client, clock} = setup(); client.value.next_control_sequence = 8; await connection.start();
  client.value.next_control_sequence = 2; client.deltas.push(() => { throw error("cursor_ahead"); });
  await clock.tick(1000); await clock.tick(2000);
  const result = await connection.pause(); assert.equal(JSON.parse(result.intent.serialized).control_sequence, 2);
  connection.dispose();
});

test("stopping an in-flight control retains intent and ignores its eventual success", async () => {
  const {connection, client, clock} = setup(); await connection.start(); const pending = deferred(); client.submissions.push(() => pending.promise);
  const result = connection.submitControl("session.pause"); await flush(); const intent = client.calls.find(call => call[0] === "submit")[1];
  connection.stop(); assert.equal(connection.pendingControl.intent, intent); pending.resolve({seq: 2});
  await assert.rejects(result, e => e.outcome === "unknown" && e.intent === intent);
  await clock.tick(60000); assert.equal(client.calls.filter(call => call[0] === "submit").length, 1);
  connection.dispose();
});

test("a deleted snapshot clears cached content and stops polling", async () => {
  const {connection, client, clock} = setup(); await connection.start();
  client.deltas.push(() => ({state: "deleted", content_available: false, session_id: "gone"}));
  await clock.tick(1000); assert.equal(connection.snapshot, null); const count = client.calls.length;
  await clock.tick(60000); assert.equal(client.calls.length, count); connection.dispose();
});

test("a truncated delta cannot advance the cursor or silently discard cached records", async () => {
  const {connection, client, clock} = setup(); await connection.start();
  client.deltas.push(cursor => ({...structuredClone(client.value), session: {...client.value.session, seq: 9},
    since_seq: cursor, current_seq: 9, records: [], has_more: true}));
  await clock.tick(1000); assert.equal(connection.cursor, 1); assert.equal(connection.snapshot.records.length, 1);
  await clock.tick(2000); assert.equal(client.calls.at(-1)[0], "snapshot"); connection.dispose();
});

test("pause cannot clear an uncertain intent that another explicit retry is currently resolving", async () => {
  const {connection, client} = setup(); await connection.start();
  client.submissions.push(() => { throw error("timeout", "unknown", 0); });
  await assert.rejects(connection.submitControl("session.heartbeat"));
  const read = deferred(), retry = deferred(); client.snapshots.push(() => read.promise); client.submissions.push(() => retry.promise);
  const pause = connection.pause(); await flush(); const retryResult = connection.retryPendingControl();
  read.resolve(structuredClone(client.value)); await assert.rejects(pause, /pause_supersession_conflict/);
  assert.equal(client.calls.filter(c => c[0] === "submit").length, 2);
  retry.resolve({seq: 1}); await retryResult; connection.dispose();
});

test("cache byte budget counts UTF-8 and rejects a large snapshot before publishing", async () => {
  const {connection, client, attention, updates} = setup({maxStateBytes: 500});
  client.value.records[0].data.text = "😀".repeat(100); await connection.start();
  assert.equal(connection.snapshot, null); assert.equal(updates.length, 0); assert.equal(attention.at(-1).errorCode, "cache_limit");
  connection.dispose();
});

test("timer options cannot trigger native overflow or rapid polling loops", () => {
  assert.throws(() => setup({maxBackoffMs: 2 ** 40}), /Timer limits/);
  assert.throws(() => setup({pollIntervalMs: 1}), /Timer limits/);
  assert.throws(() => setup({heartbeatIntervalMs: 1}), /Timer limits/);
});

test("sync deadlines remain compatible with the transport", () => {
  assert.throws(() => setup({timeoutMs: 120001}), /Transport deadline/);
  assert.throws(() => setup({timeoutMs: 1.5}), /Transport deadline/);
});

test("position-only deltas derive canonical board order including moves removals and ordinal ties", async () => {
  const {connection, client, clock} = setup();
  const record = (id, hand, at) => ({id, revision: 1, position: {x: 1, y: 2, hand_placed: hand, placed_at: at}});
  client.value.records = [record("z", true, 0), record("b", false, 5), record("a", false, 5), record("c", false, 1)];
  client.value.board_order = ["z", "b", "a", "c"]; await connection.start();
  assert.deepEqual(connection.snapshot.board_order, ["c", "a", "b", "z"]);
  client.deltas.push(cursor => { const value = {...structuredClone(client.value), session: {...client.value.session, seq: 2},
    since_seq: cursor, current_seq: 2, records: [record("c", true, 10), {id: "a", revision: 1, position: null}]};
    delete value.board_order; return value; });
  await clock.tick(1000); assert.equal(connection.cursor, 2);
  assert.deepEqual(connection.snapshot.board_order, ["b", "z", "c"]);
  assert.equal(connection.snapshot.records.find(r => r.id === "a").position, null); connection.dispose();
});

test("cascade resync immediately fetches one full snapshot without publishing a partial cursor", async () => {
  const {connection, client, clock, updates, attention} = setup(); await connection.start(); const pending = deferred();
  client.deltas.push(() => ({resync_required: true, changed_records: 400, session_records: 900, reason: "cascade_limit"}));
  client.snapshots.push(() => pending.promise); await clock.tick(1000);
  assert.equal(client.calls.at(-1)[0], "snapshot"); assert.equal(connection.cursor, 1); assert.equal(updates.length, 1);
  pending.resolve({...structuredClone(client.value), session: {...client.value.session, seq: 50}, records: [{id: "replacement", position: null}]});
  await flush(); assert.equal(connection.cursor, 50); assert.deepEqual(connection.snapshot.records.map(r => r.id), ["replacement"]);
  assert.equal(updates.length, 2); assert.equal(attention.length, 0);
  assert.equal(client.calls.filter(c => c[0] === "snapshot").length, 2); connection.dispose();
});

test("a failed cascade snapshot preserves cursor and retries the full snapshot", async () => {
  const {connection, client, clock} = setup(); await connection.start();
  client.deltas.push(() => ({resync_required: true, changed_records: 400}));
  client.snapshots.push(() => { throw error("offline", "unknown", 0); });
  await clock.tick(1000); assert.equal(connection.cursor, 1);
  await clock.tick(2000); assert.equal(client.calls.at(-1)[0], "snapshot"); connection.dispose();
});

test("invalid position ordering metadata cannot advance the cursor", async () => {
  const {connection, client, clock} = setup(); await connection.start();
  client.deltas.push(cursor => ({...structuredClone(client.value), session: {...client.value.session, seq: 2}, since_seq: cursor, current_seq: 2,
    records: [{id: "one", position: {hand_placed: false, placed_at: Infinity}}]}));
  await clock.tick(1000); assert.equal(connection.cursor, 1); assert.equal(connection.snapshot.records[0].data.text, "one"); connection.dispose();
});
