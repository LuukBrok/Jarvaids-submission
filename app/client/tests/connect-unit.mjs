/**
 * The connector's pure parts, without a browser: the cubic curve between two
 * boxes, which sides it leaves and enters by, the payload it is saved with,
 * and the set of directed connectors kept on this device.
 *
 *     node --test tests/connect-unit.mjs
 */
import test from "node:test";
import assert from "node:assert/strict";
import { connectorGeometry, connectorHead, nearestSides, sidePoint } from "../canvas-objects.mjs";
import { DIRECTED_KEY, DIRECTION_FLAG, connectorPayload, createDirectedStore, directionEnabled } from "../tools/connect.mjs";

const A = { x: 0, y: 0, w: 100, h: 50, outline: "rect" };
const B = { x: 300, y: 0, w: 100, h: 50, outline: "rect" };
const numbers = d => d.match(/-?[\d.]+/g).map(Number);

test("side by side, a connector leaves the right side and enters the left, at their middles", () => {
  const c = connectorGeometry(A, B);
  assert.deepEqual(c.sides, ["right", "left"]);
  assert.deepEqual(c.start, { x: 100, y: 25 });
  assert.deepEqual(c.end, { x: 300, y: 25 });
  assert.match(c.d, /^M 100 25 C [-\d.]+ [-\d.]+ [-\d.]+ [-\d.]+ 300 25$/, "one cubic curve");
});

test("each control point leaves its side at a right angle", () => {
  const c = connectorGeometry(A, B);
  assert.equal(c.c1.y, 25);
  assert.ok(c.c1.x > 100, "out of the right side");
  assert.equal(c.c2.y, 25);
  assert.ok(c.c2.x < 300, "out of the left side");
  const below = connectorGeometry(A, { x: 0, y: 300, w: 100, h: 50 });
  assert.deepEqual(below.sides, ["bottom", "top"]);
  assert.equal(below.c1.x, 50);
  assert.ok(below.c1.y > 50);
});

test("the nearest sides follow the wider gap, in every direction", () => {
  assert.deepEqual(nearestSides(B, A), ["left", "right"]);
  assert.deepEqual(nearestSides(A, { x: 0, y: -300, w: 100, h: 50 }), ["top", "bottom"]);
  // Further apart across than down: across wins.
  assert.deepEqual(nearestSides(A, { x: 400, y: 120, w: 100, h: 50 }), ["right", "left"]);
  // Further apart down than across: down wins.
  assert.deepEqual(nearestSides(A, { x: 120, y: 400, w: 100, h: 50 }), ["bottom", "top"]);
  // A point is a box of no size.
  assert.deepEqual(nearestSides(A, { x: 50, y: 500 }), ["bottom", "top"]);
});

test("side middles lie on every outline: rectangle, ellipse and diamond", () => {
  const e = { x: 0, y: 0, w: 100, h: 50, outline: "ellipse" };
  assert.deepEqual(sidePoint(e, "right"), { x: 100, y: 25 });
  assert.deepEqual(sidePoint(e, "top"), { x: 50, y: 0 });
  assert.deepEqual(sidePoint({ x: 7, y: 9 }, "left"), { x: 7, y: 9 }, "a point is its own side");
});

test("the label sits halfway along the curve", () => {
  const c = connectorGeometry(A, B);
  assert.deepEqual(c.mid, { x: 200, y: 25 });
  const n = numbers(c.d);
  assert.equal(n.length, 8);
});

test("where a straight arrow could not be drawn honestly, nor can a curve", () => {
  assert.equal(connectorGeometry(A, { x: 50, y: 10, w: 100, h: 50 }), null, "one box over the other's centre");
  assert.equal(connectorGeometry({ x: 5, y: 5 }, { x: 5, y: 5 }), null, "two ends at one place");
});

test("a directed connector's head is an open chevron at the end, along the last tangent", () => {
  const c = connectorGeometry(A, B);
  const d = connectorHead(c);
  assert.match(d, /^M [-\d.]+ [-\d.]+ L 300 25 L [-\d.]+ [-\d.]+$/);
  const [x1, y1, , , x3, y3] = numbers(d);
  assert.ok(x1 < 300 && x3 < 300, "both arms trail back from the tip");
  assert.ok(Math.abs((y1 - 25) + (y3 - 25)) < 1e-6, "symmetric about the tangent");
});

test("the payload is an ink arrow between two records, with a label only when one was typed", () => {
  assert.deepEqual(connectorPayload("n1", "n2", "  leads to  ", { x: 10.4, y: 20.6 }),
    { kind: "arrow", data: { from: { id: "n1" }, to: { id: "n2" }, tone: "ink", label: "leads to" }, x: 10, y: 21 });
  assert.deepEqual(connectorPayload("n1", "n2", "", { x: 0, y: 0 }).data,
    { from: { id: "n1" }, to: { id: "n2" }, tone: "ink" });
  assert.equal(connectorPayload("a", "b", "x".repeat(200), { x: 0, y: 0 }).data.label.length, 80, "the server's limit");
});

const fakeStorage = () => {
  const map = new Map();
  return { getItem: k => map.has(k) ? map.get(k) : null, setItem: (k, v) => map.set(k, String(v)), map };
};

test("the directed set survives a reload: written to storage and read back", () => {
  const storage = fakeStorage();
  const first = createDirectedStore(() => storage);
  first.add("arrow_1");
  first.add("arrow_2");
  assert.deepEqual(JSON.parse(storage.map.get(DIRECTED_KEY)), ["arrow_1", "arrow_2"]);
  const again = createDirectedStore(() => storage);
  assert.ok(again.has("arrow_1") && again.has("arrow_2"));
  assert.ok(!again.has("arrow_3"), "an arrow nobody made directed is undirected");
  again.delete("arrow_1");
  assert.ok(!createDirectedStore(() => storage).has("arrow_1"));
});

test("storage that throws keeps the set in memory and says so once", () => {
  let told = 0;
  const store = createDirectedStore(() => { throw new Error("SecurityError"); }, { onMemoryOnly: () => told++ });
  store.add("arrow_1");
  store.add("arrow_2");
  assert.ok(store.has("arrow_1") && store.has("arrow_2"));
  assert.equal(store.memoryOnly, true);
  assert.equal(told, 1);
});

test("a write that fails half way through a session falls back to memory", () => {
  let told = 0, full = false;
  const storage = fakeStorage();
  const quota = { getItem: k => storage.getItem(k), setItem: (k, v) => { if (full) throw new Error("QuotaExceededError"); storage.setItem(k, v); } };
  const store = createDirectedStore(() => quota, { onMemoryOnly: () => told++ });
  store.add("a");
  assert.equal(told, 0);
  full = true;
  store.add("b");
  assert.ok(store.has("b"));
  assert.equal(told, 1);
});

test("garbage under the key reads as an empty set, and saving still works", () => {
  const storage = fakeStorage();
  storage.setItem(DIRECTED_KEY, "{not json");
  const store = createDirectedStore(() => storage);
  assert.equal(store.size, 0);
  store.add("x");
  assert.deepEqual(JSON.parse(storage.map.get(DIRECTED_KEY)), ["x"]);
});

test("Shift's direction can be switched off with the flag, and is on otherwise", () => {
  const storage = fakeStorage();
  assert.equal(directionEnabled(() => storage), true);
  storage.setItem(DIRECTION_FLAG, "off");
  assert.equal(directionEnabled(() => storage), false);
  assert.equal(directionEnabled(() => { throw new Error("blocked"); }), true);
});
