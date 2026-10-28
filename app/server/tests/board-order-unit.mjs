/** The client's board z-order against the server's, on one server-built board.
 *
 * The rule in spec/canvas-layout.md is implemented twice, in Service._board_order
 * and in boardOrder in session-sync.mjs. They agreed when this was written and
 * nothing kept them agreeing; when they drift, two people in the same meeting
 * see a different item on top.
 *
 * So: tests/make_order_fixture.py builds a board through the real Service and
 * saves the server's own snapshot including its board_order, and these tests run
 * the client's real exported function over the same records. Nothing here
 * restates the sort. A test that restated it would pin each copy to itself,
 * which is the failure this is meant to catch.
 */
import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {boardOrder} from "../session-sync.mjs";

const fixture = JSON.parse(readFileSync(new URL("./board-order-fixture.json", import.meta.url), "utf8"));
const {records, board_order: server} = fixture.snapshot;
const placed = records.filter(record => record.position != null);

test("the client orders a server-built board exactly as the server did", () => {
  assert.deepEqual(boardOrder(records), server);
});

test("the client's order does not depend on the order records arrived in", () => {
  // A delta delivers records in change order, not the server's. The client
  // merges them into whatever its cache holds, so the ordering has to be a
  // function of the records alone. Reversed input also makes the identifier
  // tie-break load-bearing: a stable sort without it would return the ties
  // reversed.
  assert.deepEqual(boardOrder([...records].reverse()), server);
  assert.deepEqual(boardOrder([...placed].reverse().concat(records.filter(r => r.position == null))), server);
});

test("the fixture still exercises every part of the rule", () => {
  // Guards against a fixture degenerating into one any sort would satisfy,
  // which would leave the checks above passing while proving nothing.
  const at = key => placed.filter(record => record.position.hand_placed === key)
    .map(record => record.position.placed_at);
  const machine = at(false), hand = at(true);
  assert.ok(machine.length >= 2 && hand.length >= 2, "both origins are on the board");
  const ties = machine.filter(value => machine.filter(other => other === value).length >= 3);
  assert.ok(ties.length >= 3, "at least three records share one placed_at, so ids break the tie");
  assert.ok(new Set(machine).size >= 2, "placed_at separates records within one origin");
  assert.ok(Math.min(...hand) < Math.max(...machine),
    "a person placed something before the engine did, so hand_placed outranks placed_at " +
    "rather than agreeing with it; without this the first key could be dropped unnoticed");
  assert.ok(Math.max(...hand) > Math.max(...machine), "something a person moved sorts to the top");
  assert.ok(records.some(record => record.position == null), "an unplaced record is on the board");
  assert.notDeepEqual(server, placed.map(record => record.id), "the order is not just record order");
  assert.notDeepEqual(server, [...placed].map(record => record.id).sort(), "the order is not just id order");
  assert.equal(server.length, placed.length);
});

test("ordering metadata the server could not have sent is refused, not sorted", () => {
  // The fixture is trusted input; a snapshot off the wire is not. Ordering a
  // board on undefined would put a record somewhere arbitrary rather than fail.
  for (const position of [{hand_placed: "yes", placed_at: 1}, {hand_placed: false, placed_at: null}]) {
    assert.throws(() => boardOrder([{id: "record-one", position}]), {code: "invalid_snapshot"});
  }
});
