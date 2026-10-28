/**
 * The canvas objects' pure rules, without a browser: what counts as one,
 * where an arrow starts and ends, how a pen stroke becomes a path, what the
 * list view calls each object, and how "Add and accept" reports each outcome.
 *
 * The board draws from these and the list labels from them, so a mistake here
 * is a mistake in two views at once. These run in Node in a second.
 *
 *     node --test tests/canvas-objects-unit.mjs
 */
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { ACCENTS, aliasAccepted, arrowEnds, arrowGeometry, arrowHead, canvasObject, edgePoint, nearestAccent, objectBox, objectLabel,
  parseColour, resolveEnd, strokeBounds, strokePath, toneOf } from "../canvas-objects.mjs";
import { boardModel, objectMeta } from "../board.mjs";
import { addAndAccept, addAndAcceptMessage } from "../composer.mjs";

const members = [{ id: "a1", name: "Sanne" }];
const note = (id, text = id) => ({ id, kind: "item", revision: 1, position: { x: 0, y: 0, revision: 1 },
  data: { item_kind: "content", status: "accepted", origin: "human", text, accepted_by: "a1", refs: [] } });
const made = (id, item_kind, fields, position = { x: 0, y: 0, w: 100, h: 50, revision: 1 }) => ({ id, kind: "item", revision: 1, position,
  data: { item_kind, status: "accepted", origin: "human", made_by_hand: true, author_id: "a1", accepted_by: "a1", ...fields } });
const proposed = (id, canvas_kind, canvas_data, status = "needs_review") => ({ id, kind: "proposal", revision: 1,
  data: { proposal_kind: "canvas", canvas_kind, canvas_data, status, origin: "model", provider: "claude" } });
const snap = records => ({ records, members, board_order: records.map(r => r.id) });

// ------------------------------------------------------------------ model

test("the five kinds are canvas objects, accepted items and open proposals only", () => {
  const s = snap([
    note("n"),
    made("shape", "shape", { shape: "rect", tone: "ink" }),
    made("gone", "shape", { shape: "rect", status: "undone" }),
    proposed("open", "text", { text: "Maybe", size: "body" }),
    proposed("stale", "text", { text: "Changed", size: "body" }, "stale"),
    proposed("no", "text", { text: "No", size: "body" }, "rejected"),
    proposed("yes", "text", { text: "Yes", size: "body" }, "accepted"),
    { id: "content", kind: "proposal", revision: 1, data: { proposal_kind: "content", status: "needs_review", origin: "human", text: "typed", refs: [] } },
  ]);
  const model = boardModel(s);
  assert.deepEqual(model.objects.map(o => o.id).sort(), ["open", "shape", "stale"]);
  assert.deepEqual(model.notes.map(n => n.id).sort(), ["content", "n"], "a canvas object is never drawn as a note");
  assert.equal(model.objects.find(o => o.id === "open").proposed, true);
  assert.equal(model.objects.find(o => o.id === "shape").proposed, false);
});

test("a proposal's fields come from canvas_data, an item's from data", () => {
  assert.equal(canvasObject(proposed("p", "shape", { shape: "ellipse", text: "Ideas" })).fields.text, "Ideas");
  assert.equal(canvasObject(made("i", "shape", { shape: "ellipse", text: "Ideas" })).fields.text, "Ideas");
  assert.equal(canvasObject(note("n")), null);
});

test("sections are drawn first, so their members sit on top of them", () => {
  const model = boardModel(snap([made("s", "shape", { shape: "rect" }), made("sec", "section", { title: "Risks", form: "free", member_ids: [] })]));
  assert.equal(model.objects[0].kind, "section");
});

test("an unknown tone draws as ink rather than not at all", () => {
  assert.equal(toneOf({ tone: "category-2" }), "category-2");
  assert.equal(toneOf({ tone: "red" }), "ink");
  assert.equal(toneOf({}), "ink");
});

test("a box carries its size, its outline, and a default size when the server sent none", () => {
  const box = objectBox(canvasObject(made("e", "shape", { shape: "ellipse" }, { x: 10, y: 20, w: 120, h: 60 })), { x: 10, y: 20, w: 120, h: 60 });
  assert.deepEqual(box, { x: 10, y: 20, w: 120, h: 60, outline: "ellipse" });
  const text = canvasObject(proposed("t", "text", { text: "x" }));
  assert.deepEqual(objectBox(text, { x: 0, y: 0 }), { x: 0, y: 0, w: 224, h: 48, outline: "rect" });
  assert.equal(objectBox(canvasObject(made("a", "arrow", {})), { x: 0, y: 0 }), null, "an arrow has no box of its own");
});

// ----------------------------------------------------------------- arrows

const A = { x: 0, y: 0, w: 100, h: 50, outline: "rect" };
const B = { x: 200, y: 0, w: 100, h: 50, outline: "rect" };

test("an arrow runs edge to edge, not centre to centre", () => {
  assert.deepEqual(arrowGeometry(A, B), { x1: 100, y1: 25, x2: 200, y2: 25 });
  const below = { x: 0, y: 150, w: 100, h: 50, outline: "rect" };
  assert.deepEqual(arrowGeometry(A, below), { x1: 50, y1: 50, x2: 50, y2: 150 });
});

test("a diagonal arrow leaves through the side the line actually crosses", () => {
  const far = { x: 300, y: 100, w: 100, h: 50, outline: "rect" };
  const line = arrowGeometry(A, far);
  // Centres (50,25) and (350,125): slope 1/3, so it leaves A through its right
  // side at x 100 and enters the other box through its left side at x 300.
  assert.equal(line.x1, 100);
  assert.ok(Math.abs(line.y1 - (25 + 50 / 3)) < 1e-9);
  assert.equal(line.x2, 300);
  assert.ok(Math.abs(line.y2 - (125 - 50 / 3)) < 1e-9);
});

test("an ellipse and a diamond are met on their own outline", () => {
  const e = { x: 0, y: 0, w: 100, h: 50, outline: "ellipse" };
  const d = { x: 0, y: 0, w: 100, h: 50, outline: "diamond" };
  // Straight right: every outline is met at the box's right edge.
  assert.deepEqual(edgePoint(e, { x: 500, y: 25 }), { x: 100, y: 25 });
  assert.deepEqual(edgePoint(d, { x: 500, y: 25 }), { x: 100, y: 25 });
  // Towards the corner: inside the box, on the ellipse and on the diamond.
  const toward = { x: 100 + 500, y: 50 + 250 };
  const pe = edgePoint(e, toward), pd = edgePoint(d, toward);
  assert.ok(Math.abs(((pe.x - 50) / 50) ** 2 + ((pe.y - 25) / 25) ** 2 - 1) < 1e-9, "on the ellipse");
  assert.ok(Math.abs(Math.abs(pd.x - 50) / 50 + Math.abs(pd.y - 25) / 25 - 1) < 1e-9, "on the diamond");
  assert.ok(pe.x < 100 && pd.x < pe.x, "the diamond's edge is inside the ellipse's, which is inside the box");
});

test("a point end is used as it is", () => {
  assert.deepEqual(arrowGeometry(A, { x: 400, y: 25 }), { x1: 100, y1: 25, x2: 400, y2: 25 });
  assert.deepEqual(arrowGeometry({ x: -100, y: 25 }, A), { x1: -100, y1: 25, x2: 0, y2: 25 });
});

test("a box over the other's centre line, or a point inside the other box, draws nothing", () => {
  assert.equal(arrowGeometry(A, { x: 50, y: 10, w: 100, h: 50 }), null);
  assert.equal(arrowGeometry({ x: 0, y: 0, w: 200, h: 200 }, { x: 150, y: 90, w: 100, h: 20 }), null);
  assert.equal(arrowGeometry({ x: 50, y: 25 }, A), null);
  assert.equal(arrowGeometry({ x: 5, y: 5 }, { x: 5, y: 5 }), null);
});

test("boxes that only overlap at a corner still get an arrow, outside both", () => {
  const wide = { x: 0, y: 0, w: 100, h: 10 }, tall = { x: 90, y: 0, w: 100, h: 200 };
  const line = arrowGeometry(wide, tall);
  assert.ok(line, "a corner overlap is not a reason to hide the connection");
  assert.ok(Math.abs(line.y1 - 10) < 1e-9 && line.x1 < 90, "leaves the wide box through its bottom, before the tall one");
  assert.ok(Math.abs(line.x2 - 90) < 1e-9 && line.y2 > 10, "enters the tall box through its left side, below the wide one");
});

test("an arrow whose record is gone is not drawn", () => {
  const boxes = new Map([["a", A], ["b", B]]);
  assert.ok(arrowEnds({ from: { id: "a" }, to: { id: "b" } }, boxes));
  assert.equal(arrowEnds({ from: { id: "a" }, to: { id: "removed" } }, boxes), null);
  assert.equal(arrowEnds({ from: { id: "removed" }, to: { x: 10, y: 10 } }, boxes), null);
  assert.equal(arrowEnds({ from: { id: "a" }, to: { id: "a" } }, boxes), null, "from a record to itself");
  assert.equal(arrowEnds({ from: { x: Infinity, y: 0 }, to: { id: "a" } }, boxes), null, "a point must be finite");
  assert.deepEqual(resolveEnd({ x: 3, y: 4 }, boxes), { x: 3, y: 4 });
});

test("the head is an open chevron whose tip is the arrow's end", () => {
  const d = arrowHead({ x1: 0, y1: 0, x2: 100, y2: 0 });
  assert.match(d, /^M [-\d.]+ [-\d.]+ L 100 0 L [-\d.]+ [-\d.]+$/);
  assert.ok(!/Z/.test(d), "an open path, so a proposed head is never a fill");
});

// ---------------------------------------------------------------- strokes

test("a stroke's path starts and ends on its points, relative to its position", () => {
  assert.equal(strokePath([[0, 0], [10, 5]], { x: 100, y: 200 }), "M 100 200 L 110 205");
  const d = strokePath([[0, 0], [10, 0], [20, 10], [30, 10]], { x: 0, y: 0 });
  assert.match(d, /^M 0 0 Q 10 0 15 5 Q 20 10 25 10 L 30 10$/);
});

test("a smooth stroke curves through its middle points rather than turning a corner", () => {
  const d = strokePath([[0, 0], [10, 10], [20, 0]]);
  assert.ok(d.includes(" Q "), d);
  assert.ok(!/L 10 10/.test(d), "a polyline would turn a corner at the sample");
});

test("a stroke needs two usable points; anything that is not a number is left out", () => {
  assert.equal(strokePath([[1, 1]]), null);
  assert.equal(strokePath(null), null);
  assert.equal(strokePath([[0, 0], ["x", 1], [NaN, 2], [4, 4]]), "M 0 0 L 4 4");
  assert.deepEqual(strokeBounds([[0, 0], [-10, 20], [30, 5]], { x: 100, y: 100 }), { x: 90, y: 100, w: 40, h: 20, outline: "rect" });
});

// ----------------------------------------------------------------- labels

test("the list names each kind in a line", () => {
  const s = snap([
    note("n1", "Onboarding loses people"), note("n2", "Too many fields"),
    made("ideas", "shape", { shape: "rect", text: "Ideas", tone: "accent" }),
    made("plain", "shape", { shape: "ellipse" }),
    made("words", "text", { text: "Where we lose people", size: "heading" }),
    made("risks", "section", { title: "Risks", form: "free", member_ids: ["n1", "n2", "removed"] }),
    made("pen", "stroke", { points: [[0, 0], [5, 5]], weight: "bold", tone: "ink" }),
    made("link", "arrow", { from: { id: "n1" }, to: { id: "ideas" }, tone: "ink" }),
    made("cause", "arrow", { from: { id: "n2" }, to: { x: 5, y: 5 }, label: "causes", tone: "ink" }),
    made("dangling", "arrow", { from: { id: "removed" }, to: { id: "n1" }, tone: "ink" }),
  ]);
  const model = boardModel(s);
  const label = id => objectLabel(model.objects.find(o => o.id === id), model.nameOf);
  assert.equal(label("ideas"), "Shape · Ideas");
  assert.equal(label("plain"), "Shape · Ellipse");
  assert.equal(label("words"), "Text · Where we lose people");
  assert.equal(label("risks"), "Section · Risks (2)", "counts the members still on the canvas");
  assert.equal(label("pen"), "Pen stroke · Bold");
  assert.equal(label("link"), "Arrow · from “Onboarding loses people” to “Ideas”");
  assert.equal(label("cause"), "Arrow · causes · from “Too many fields” to a point");
  assert.equal(label("dangling"), "Arrow · from something no longer on the canvas to “Onboarding loses people”");
});

test("a long name is cut with an ellipsis, never mid-line", () => {
  const s = snap([made("t", "text", { text: "x".repeat(200), size: "body" })]);
  const line = objectLabel(boardModel(s).objects[0], () => null);
  assert.ok(line.length <= "Text · ".length + 60 && line.endsWith("…"), line);
});

test("the line under an object says who drew, accepted or proposed it", () => {
  const s = snap([]);
  const hand = canvasObject(made("h", "shape", { shape: "rect" }));
  const words = canvasObject(made("w", "text", { text: "Hi", size: "body" }));
  const acceptedFromModel = canvasObject({ id: "m", kind: "item", revision: 1,
    data: { item_kind: "shape", status: "accepted", origin: "model", made_by_hand: false, accepted_by: "a1", shape: "rect" } });
  assert.equal(objectMeta(s, hand), "Drawn by Sanne");
  assert.equal(objectMeta(s, words), "Written by Sanne");
  assert.equal(objectMeta(s, acceptedFromModel), "Accepted by Sanne");
  assert.equal(objectMeta(s, canvasObject(proposed("p", "arrow", {}))), "Proposed by Claude, needs review");
  assert.match(objectMeta(s, canvasObject(proposed("p", "arrow", {}, "stale"))), /source changed/);
});

// ---------------------------------------------------------- add and accept

const fakeSend = steps => {
  const calls = [];
  const send = async (operation, payload) => {
    calls.push([operation, payload]);
    const step = steps[operation];
    if (step instanceof Error) throw step;
    return step;
  };
  return { send, calls };
};
const added = { source: { id: "s1" }, proposal: { id: "p1", revision: 3 } };

test("add and accept sends the note, then accepts the proposal it returned", async () => {
  const { send, calls } = fakeSend({ "source.text": added, "proposal.review": { item: { id: "i1", data: { text: "Hi" } } } });
  const outcome = await addAndAccept(send, "Hi");
  assert.deepEqual(calls, [["source.text", { text: "Hi" }],
    ["proposal.review", { proposal_id: "p1", expected_revision: 3, decision: "accept" }]]);
  assert.equal(outcome.stage, "done");
  assert.equal(outcome.item.id, "i1");
  assert.match(addAndAcceptMessage(outcome).text, /Added and accepted/);
});

test("if adding fails nothing is accepted, and the add's own banner stands", async () => {
  const { send, calls } = fakeSend({ "source.text": new Error("Could not reach the server") });
  const outcome = await addAndAccept(send, "Hi");
  assert.equal(outcome.stage, "add");
  assert.equal(calls.length, 1);
  assert.equal(addAndAcceptMessage(outcome), null);
});

test("if accepting fails the note stays waiting for review, and the banner says so", async () => {
  const refused = Object.assign(new Error("That changed since you loaded it"), { outcome: "response_received" });
  const { send } = fakeSend({ "source.text": added, "proposal.review": refused });
  const outcome = await addAndAccept(send, "Hi");
  assert.equal(outcome.stage, "accept");
  const message = addAndAcceptMessage(outcome);
  assert.equal(message.kind, "problem");
  assert.equal(message.text, "Added to the canvas, but it could not be accepted: That changed since you loaded it. It is waiting for review.");
});

test("an uncertain accept is not reported as a failure, so nobody accepts twice blind", async () => {
  const unknown = Object.assign(new Error("timeout"), { outcome: "unknown" });
  const { send } = fakeSend({ "source.text": added, "proposal.review": unknown });
  const message = addAndAcceptMessage(await addAndAccept(send, "Hi"));
  assert.match(message.text, /may or may not have accepted it/);
  assert.doesNotMatch(message.text, /could not be accepted/);
});

test("an arrow drawn to a proposal still finds it once it is accepted as an item", () => {
  const boxes = new Map([["item_9", { x: 0, y: 0, w: 100, h: 40 }]]);
  aliasAccepted(boxes, [{ id: "item_9", kind: "item", data: { proposal_id: "prop_1" } }]);
  assert.deepEqual(boxes.get("prop_1"), { x: 0, y: 0, w: 100, h: 40 });
  assert.ok(arrowEnds({ from: { id: "prop_1" }, to: { x: 300, y: 20 } }, boxes));
});

// ----------------------------------------------------------------- colour

/** The five accents as tokens.css defines them, read from the file, so this
 * test never repeats a colour literal and moves with the tokens. */
const PALETTE = (() => {
  const css = readFileSync(new URL("../tokens.css", import.meta.url), "utf8");
  return Object.fromEntries(ACCENTS.map(name => {
    const m = css.match(new RegExp(`--${name}:\\s*([^;]+);`));
    return [name, parseColour(m?.[1])];
  }));
})();
/** A colour a step away from an accent, as a photograph's paper rarely
 * matches the token exactly. */
const near = (name, [dr, dg, db]) => PALETTE[name].map((v, i) => Math.max(0, Math.min(255, v + [dr, dg, db][i])));
const hex = rgb => "#" + rgb.map(v => v.toString(16).padStart(2, "0")).join("");

test("every accent is read from the tokens", () => {
  for (const name of ACCENTS) assert.equal(PALETTE[name]?.length, 3, name);
});

test("a photographed note takes the accent nearest its measured paper colour", () => {
  for (const name of ACCENTS) {
    assert.equal(nearestAccent(hex(PALETTE[name]), PALETTE), name, `${name} itself`);
    assert.equal(nearestAccent(hex(near(name, [-14, 9, -6])), PALETTE), name, `a paper close to ${name}`);
  }
  // A washed-out pink sticky note is lilac or coral, never yellow.
  assert.ok(["lilac", "coral"].includes(nearestAccent(hex(near("lilac", [10, -20, -30])), PALETTE)));
});

test("colours are read as #rgb, #rrggbb and rgb()", () => {
  assert.deepEqual(parseColour("rgb(1, 2, 3)"), [1, 2, 3]);
  assert.deepEqual(parseColour(hex([255, 0, 136])), [255, 0, 136]);
  assert.deepEqual(parseColour("#" + "fa0"), [255, 170, 0]);
  assert.equal(parseColour("yellowish"), null);
});

test("a colour that cannot be read is no evidence, so the note stays yellow", () => {
  assert.equal(nearestAccent("not a colour", PALETTE), "yellow");
  assert.equal(nearestAccent(null, PALETTE), "yellow");
  assert.equal(nearestAccent(hex(PALETTE.mint), null), "yellow");
});

test("a proposal still drawn keeps its own box; an alias never replaces it", () => {
  const own = { x: 5, y: 5, w: 10, h: 10 };
  const boxes = new Map([["prop_1", own], ["item_9", { x: 0, y: 0, w: 100, h: 40 }]]);
  aliasAccepted(boxes, [{ id: "item_9", kind: "item", data: { proposal_id: "prop_1" } }]);
  assert.equal(boxes.get("prop_1"), own);
});
