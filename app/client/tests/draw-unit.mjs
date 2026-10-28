/**
 * The drawing tool's pure parts, without a browser: how a drawn line is
 * thinned to the server's 256 points, how it is smoothed, and how it becomes
 * a stroke record relative to its first point.
 *
 *     node --test tests/draw-unit.mjs
 */
import test from "node:test";
import assert from "node:assert/strict";
import { MAX_POINTS, relativePoints, simplify, simplifyTo, smoothPath, strokeRecord } from "../tools/draw.mjs";
import { strokePath } from "../canvas-objects.mjs";

test("simplification keeps both ends and drops points on the line between them", () => {
  const straight = Array.from({ length: 50 }, (_, i) => [i, 2 * i]);
  assert.deepEqual(simplify(straight, 0.5), [[0, 0], [49, 98]]);
});

test("simplification keeps a corner", () => {
  const corner = [[0, 0], [5, 0], [10, 0], [10, 5], [10, 10]];
  assert.deepEqual(simplify(corner, 0.5), [[0, 0], [10, 0], [10, 10]]);
});

test("a long scribble is thinned to the server's limit, and a short one keeps its detail", () => {
  const scribble = Array.from({ length: 3000 }, (_, i) => [i, Math.sin(i / 3) * 40]);
  const thin = simplifyTo(scribble, MAX_POINTS);
  assert.ok(thin.length <= MAX_POINTS && thin.length >= 2, `${thin.length} points`);
  assert.deepEqual(thin[0], scribble[0]);
  assert.deepEqual(thin.at(-1), scribble.at(-1));
  const short = [[0, 0], [10, 8], [20, 0], [30, 8]];
  assert.deepEqual(simplifyTo(short, MAX_POINTS), short);
});

test("two points or fewer are returned as they are", () => {
  assert.deepEqual(simplify([[1, 1], [2, 2]]), [[1, 1], [2, 2]]);
  assert.deepEqual(simplify([]), []);
  assert.deepEqual(simplify(null), []);
});

test("points are made relative to the first, which becomes the stroke's position", () => {
  const rel = relativePoints([[100.44, 200.61], [110.44, 205.66], [90, 220]]);
  assert.equal(rel.x, 100.4);
  assert.equal(rel.y, 200.6);
  assert.deepEqual(rel.points, [[0, 0], [10, 5.1], [-10.4, 19.4]]);
});

test("the live line is smoothed exactly as the saved stroke will be drawn", () => {
  const points = [[0, 0], [10, 0], [20, 10], [30, 10]];
  assert.equal(smoothPath(points), strokePath(points));
  assert.match(smoothPath(points), /^M 0 0 Q 10 0 15 5 Q 20 10 25 10 L 30 10$/, "quadratic curves through the midpoints");
  assert.match(smoothPath([[3, 4]]), /^M 3 4 L 3 4$/, "a single point is drawn as a dot while the pen is down");
});

test("a stroke record is what canvas.create takes: a stroke in ink, regular, relative to its start", () => {
  const drawn = Array.from({ length: 600 }, (_, i) => [500 + i, 300 + Math.cos(i / 5) * 20]);
  const record = strokeRecord(drawn);
  assert.equal(record.kind, "stroke");
  assert.equal(record.x, 500);
  assert.equal(record.y, 320);
  assert.equal(record.data.weight, "regular");
  assert.equal(record.data.tone, "ink");
  assert.deepEqual(record.data.points[0], [0, 0]);
  assert.ok(record.data.points.length >= 2 && record.data.points.length <= MAX_POINTS);
});

test("a press that barely moves is not a stroke", () => {
  assert.equal(strokeRecord([[0, 0]]), null);
  assert.equal(strokeRecord([[0, 0], [1, 1]]), null);
  assert.ok(strokeRecord([[0, 0], [10, 0]]));
});

test("a stroke dragged past the server's limit is cut where it leaves it", () => {
  const record = strokeRecord([[0, 0], [5000, 0], [9000, 4000], [12000, 9000]]);
  assert.ok(record.data.points.every(([x, y]) => Math.abs(x) <= 10000 && Math.abs(y) <= 10000));
  assert.equal(record.data.points.length, 3);
});
