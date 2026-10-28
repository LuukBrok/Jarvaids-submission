/**
 * The five canvas object kinds, drawn in a real browser from a fixture.
 *
 * The server half of the canvas object model is built separately, so this
 * injects a snapshot straight into a Board, the way the transcript test
 * injects segments: it proves the drawing, not the commands. It checks that
 * each kind is drawn with the look the design system gives it (accepted: a
 * tonal fill and no line; proposed: no fill, a dashed accent line and
 * "Proposed"), that arrows run edge to edge and follow a note pushed by open
 * details, that an arrow to a removed record is not drawn, that the new
 * layers do not swallow a note's drag or a pan, and that the list view names
 * every object. At 1440 and 400px, with no horizontal overflow and no console
 * errors.
 *
 *     node tests/canvas-objects-browser.mjs
 *
 * CANVAS_SCREENSHOT=path saves the 1440px board there; screenshots of both
 * widths always go to .local/canvas-ui/.
 */
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createRequire } from "node:module";
import { mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");
const client = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const output = resolve(client, "../../.local/canvas-ui");
mkdirSync(output, { recursive: true });
const port = 5191;
const server = spawn(process.env.JARVAIDS_TEST_PYTHON || "python3",
  ["serve.py", "--port", String(port)], { cwd: client, stdio: "ignore" });
server.on("error", error => { throw error; });

const at = (x, y, w, h) => ({ x, y, w, h, revision: 1, hand_placed: true });
const hand = { status: "accepted", origin: "human", made_by_hand: true, author_id: "a1", accepted_by: "a1", created_at: 1 };
const note = (id, text, x, y) => ({ id, kind: "item", revision: 1, position: { x, y, revision: 1, hand_placed: true },
  data: { item_kind: "content", status: "accepted", origin: "human", text, accepted_by: "a1", refs: [] } });
const item = (id, item_kind, fields, position) => ({ id, kind: "item", revision: 1, position, data: { item_kind, ...hand, ...fields } });
const FIXTURE = {
  members: [{ id: "a1", name: "Sanne", role: "facilitator" }],
  records: [
    item("heading", "text", { text: "Where onboarding loses people", size: "heading" }, at(0, -120, 520, 40)),
    note("n1", "Onboarding loses people at step two", 0, 0),
    note("n3", "Too many fields before value", 340, 0),
    item("ideas", "shape", { shape: "rect", text: "Ideas", tone: "accent" }, at(680, 0, 160, 96)),
    item("interviews", "shape", { shape: "ellipse", text: "Interviews", tone: "category-1" }, at(680, 170, 160, 96)),
    item("rule", "shape", { shape: "line", tone: "category-3" }, at(900, 30, 120, 60)),
    item("risks", "section", { title: "Risks", form: "free", member_ids: ["n2", "decide", "removed"] }, at(-24, 300, 600, 240)),
    note("n2", "People skip the tour", 0, 360),
    item("decide", "shape", { shape: "diamond", text: "Decide", tone: "category-2" }, at(320, 360, 136, 112)),
    item("pen", "stroke", { weight: "bold", tone: "accent",
      points: [[0, 0], [24, -18], [48, 6], [72, -12], [96, 10], [128, -4], [160, 8]] }, { x: 660, y: 340, revision: 1, hand_placed: true }),
    item("a-n1-n3", "arrow", { from: { id: "n1" }, to: { id: "n3" }, label: "leads to", tone: "ink" }, null),
    item("a-n3-ideas", "arrow", { from: { id: "n3" }, to: { id: "ideas" }, tone: "accent" }, null),
    item("a-n2-decide", "arrow", { from: { id: "n2" }, to: { id: "decide" }, tone: "ink" }, null),
    item("a-point", "arrow", { from: { x: 1040, y: 300 }, to: { id: "interviews" }, tone: "category-1" }, null),
    item("a-gone", "arrow", { from: { id: "removed" }, to: { id: "n1" }, tone: "ink" }, null),
    { id: "proposal", kind: "proposal", revision: 1, position: at(900, 170, 160, 96),
      data: { proposal_kind: "canvas", canvas_kind: "shape", status: "needs_review", origin: "model", provider: "claude",
        canvas_data: { shape: "ellipse", text: "Run a test", tone: "accent" } } },
  ],
};
FIXTURE.board_order = FIXTURE.records.map(r => r.id);

let browser;
try {
  for (let attempt = 0; ; attempt++) {
    try { const r = await fetch(`http://127.0.0.1:${port}/client/`); await r.arrayBuffer(); if (r.ok) break; } catch {}
    if (attempt >= 80) throw new Error("Static server did not start.");
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  browser = await chromium.launch({ headless: true,
    ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}) });
  for (const width of [1440, 400]) {
    const page = await browser.newPage({ viewport: { width, height: 1000 } });
    const errors = [], failedRequests = [];
    page.on("pageerror", error => errors.push(error.message));
    page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
    page.on("requestfailed", request => failedRequests.push(request.url()));
    page.on("response", response => { if (response.status() >= 400) failedRequests.push(response.url()); });
    await page.goto(`http://127.0.0.1:${port}/client/`);
    await page.evaluate(async fixture => {
      document.getElementById("screen-setup").hidden = true;
      document.getElementById("screen-workspace").hidden = false;
      // A fresh board on the real element, with hooks that record instead of
      // sending: the app's own board has no session behind it here.
      const old = document.getElementById("board");
      const fresh = old.cloneNode(false);
      old.replaceWith(fresh);
      const { Board } = await import("/client/board.mjs");
      window.sent = []; window.reviewed = [];
      const board = new Board(fresh, {
        send: async (operation, payload) => { window.sent.push([operation, payload]); },
        review: id => window.reviewed.push(id), attention: () => {}, onSelection: () => {},
        crop: async () => "", revoke: () => {},
      });
      board.render(fixture);
      window.testBoard = board;
      window.fixture = fixture;
    }, FIXTURE);

    // ---- each kind is drawn
    const count = selector => page.locator(selector).count();
    assert.equal(await count(".cobj-section"), 1, "one section");
    assert.equal(await count(".cobj-shape"), 5, "four accepted shapes and the proposed one");
    assert.equal(await count(".cobj-text"), 1, "one text");
    assert.equal(await count(".links .pen"), 1, "one stroke");
    assert.equal(await count(".links .arrow"), 4, "four arrows; the one to a removed record is not drawn");
    assert.equal(await count('.links .arrow[data-id="a-gone"]'), 0);
    assert.equal(await count(".links"), 1, "arrows and strokes share one layer");

    // ---- under the notes: the layer and the objects come before every note
    const order = await page.evaluate(() => {
      const kids = [...document.querySelector(".world").children];
      const first = sel => kids.findIndex(k => k.matches(sel));
      const last = sel => kids.findLastIndex(k => k.matches(sel));
      return { links: first(".links"), section: first(".cobj-section"), shape: last(".cobj"), note: first(".note") };
    });
    assert.ok(order.section < order.shape && order.shape < order.links && order.links < order.note, JSON.stringify(order));

    // ---- the looks
    const style = (selector, ...props) => page.$eval(selector, (el, props) => {
      const cs = getComputedStyle(el); return Object.fromEntries(props.map(p => [p, cs.getPropertyValue(p)]));
    }, props);
    // The expected colours and sizes are read from the tokens the page
    // loaded (app/client/tokens.css), so a token change is not a test change;
    // what is tested is which token each look uses.
    const probe = (property, value) => page.evaluate(([property, value]) => {
      const el = document.createElement("i");
      el.style.setProperty(property, value);
      document.body.append(el);
      const out = getComputedStyle(el).getPropertyValue(property);
      el.remove();
      return out;
    }, [property, value]);
    const accent = await probe("color", "var(--tone-accent-line)");
    const ink = await probe("color", "var(--ink)");
    // A connector or stroke in the ink tone is the human mark (DESIGN.md 1.2).
    const human = await probe("color", "var(--mark-human)");
    const machine = await probe("color", "var(--mark-machine)");
    const display = await probe("font-size", "var(--fs-display)");
    const shapeBody = await style('.cobj[data-id="interviews"] .body', "fill", "stroke");
    assert.notEqual(shapeBody.fill, "none", "an accepted shape has a tonal fill");
    assert.equal(shapeBody.stroke, "none", "and no line");
    const section = await style('.cobj[data-id="risks"]', "background-color", "border-top-style");
    assert.notEqual(section["background-color"], "rgba(0, 0, 0, 0)", "an accepted section is a tonal area");
    assert.equal(section["border-top-style"], "none");
    // A section is labelled like a group, and the label says which it is.
    assert.match(await page.textContent('.cobj[data-id="risks"] .cobj-title'), /^Section · Risks$/);
    const text = await style('.cobj[data-id="heading"]', "background-color", "border-top-style", "color");
    assert.deepEqual([text["background-color"], text["border-top-style"], text.color], ["rgba(0, 0, 0, 0)", "none", ink]);
    assert.equal((await style('.cobj[data-id="heading"] .cobj-words', "font-size"))["font-size"], display, "a heading text uses the Display size on the canvas");
    const arrow = await style('.arrow[data-id="a-n1-n3"] .arrow-line', "stroke", "stroke-dasharray", "fill");
    assert.deepEqual([arrow.stroke, arrow["stroke-dasharray"], arrow.fill], [human, "none", "none"]);
    assert.equal((await style('.arrow[data-id="a-n3-ideas"] .arrow-line', "stroke")).stroke, accent, "an arrow in its tone");
    const pen = await style(".links .pen", "stroke", "fill", "stroke-width");
    assert.deepEqual([pen.stroke, pen.fill, pen["stroke-width"]], [accent, "none", "4px"]);
    const rule = await style('.cobj[data-id="rule"] .rule', "stroke", "fill", "stroke-dasharray");
    assert.deepEqual([rule.fill, rule["stroke-dasharray"]], ["none", "none"]);
    assert.notEqual(rule.stroke, "none");

    // The proposal: no fill, the machine mark (--ink-3, dashed), "Proposed" and the ring.
    const prop = await style('.cobj[data-id="proposal"] .body', "fill", "stroke", "stroke-dasharray", "stroke-width");
    assert.deepEqual([prop.fill, prop.stroke, prop["stroke-width"]], ["none", machine, "1px"]);
    assert.match(prop["stroke-dasharray"], /^4(px)?,? 4(px)?$/);
    const tag = page.locator('.cobj[data-id="proposal"] .cobj-tag');
    assert.match(await tag.innerText(), /Proposed/);
    assert.equal(await tag.locator(".glyph-provisional").count(), 1);
    assert.equal((await style('.cobj[data-id="proposal"]', "opacity")).opacity, "1", "never dimmed");
    assert.equal((await style('.cobj[data-id="proposal"] .cobj-label', "color")).color, ink, "its text is never greyed");
    await tag.getByRole("button", { name: "Review" }).click();
    assert.deepEqual(await page.evaluate(() => window.reviewed), ["proposal"]);

    // ---- arrows run edge to edge and follow the displayed box. A connector
    // is a cubic curve, so its ends are the first and the last two numbers.
    const line = id => page.$eval(`.arrow[data-id="${id}"] .arrow-line`, p => {
      const n = p.getAttribute("d").match(/-?[\d.]+/g).map(Number);
      return [n[0], n[1], n.at(-2), n.at(-1)];
    });
    const box = id => page.$eval(`.note[data-id="${id}"]`, el => ({ x: parseFloat(el.style.left),
      y: parseFloat(el.style.top) + Number(el.dataset.offset || 0), w: el.offsetWidth, h: el.offsetHeight }));
    const [x1, , x2] = await line("a-n1-n3");
    const n1 = await box("n1"), n3 = await box("n3");
    assert.ok(Math.abs(x1 - (n1.x + n1.w)) < 0.5, `starts on n1's right edge: ${x1} vs ${n1.x + n1.w}`);
    assert.ok(Math.abs(x2 - n3.x) < 0.5, `ends on n3's left edge: ${x2} vs ${n3.x}`);
    const before = await line("a-n2-decide");
    await page.locator('.note[data-id="n1"]').getByRole("button", { name: "Show details" }).click();
    const pushed = await box("n2");
    assert.ok(pushed.y > 360, "opening n1 pushes n2 down on this screen");
    const after = await line("a-n2-decide");
    assert.ok(after[1] > before[1] + 10, `the arrow follows the pushed note: ${before[1]} to ${after[1]}`);
    assert.deepEqual(await page.evaluate(() => window.sent), [], "opening details saves nothing");
    await page.locator('.note[data-id="n1"]').getByRole("button", { name: "Hide details" }).click();

    // ---- the new layers never take a press meant for a note or a pan
    const screenPoint = async ([ax, ay, bx, by]) => page.evaluate(([x, y]) => {
      const world = document.querySelector(".world").getBoundingClientRect(), z = window.testBoard.view.z;
      return [world.left + x * z, world.top + y * z];
    }, [(ax + bx) / 2, (ay + by) / 2]);
    const onArrow = await screenPoint(await line("a-point"));
    const hit = await page.evaluate(([x, y]) => document.elementFromPoint(x, y)?.id || document.elementFromPoint(x, y)?.className?.baseVal || document.elementFromPoint(x, y)?.className, onArrow);
    assert.equal(hit, "board", "a press on an arrow reaches the board, so it pans");
    const shapeCentre = await page.$eval('.cobj[data-id="decide"]', el => { const r = el.getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; });
    assert.equal(await page.evaluate(([x, y]) => document.elementFromPoint(x, y)?.id, shapeCentre), "board", "a press on a shape pans too");
    const t0 = await page.$eval(".world", w => w.style.transform);
    await page.mouse.move(...onArrow);
    await page.mouse.down();
    await page.mouse.move(onArrow[0] - 60, onArrow[1] - 30, { steps: 4 });
    await page.mouse.up();
    assert.notEqual(await page.$eval(".world", w => w.style.transform), t0, "dragging from an arrow pans the board");
    if (width === 1440) {
      // A drag of a note still goes to item.place, layers or not. Only at the
      // desk width: below the breakpoint the rail sits above the board.
      const target = await page.locator('.note[data-id="n3"]').boundingBox();
      await page.mouse.move(target.x + 40, target.y + 12);
      await page.mouse.down();
      await page.mouse.move(target.x + 120, target.y + 60, { steps: 6 });
      await page.mouse.up();
      await page.waitForFunction(() => window.sent.length > 0, null, { timeout: 3000 });
      const [operation, payload] = await page.evaluate(() => window.sent[0]);
      assert.equal(operation, "item.place");
      assert.equal(payload.placements[0].id, "n3");
    }

    // ---- the list view names every object, proposed ones marked
    await page.evaluate(async () => {
      const { renderList } = await import("/client/app.mjs");
      document.getElementById("list-view").hidden = false;
      renderList(window.fixture);
    });
    const list = await page.textContent("#list-view");
    for (const line of ["Shape · Ideas", "Shape · Interviews", "Shape · Line", "Shape · Decide", "Text · Where onboarding loses people",
      "Section · Risks (2)", "Pen stroke · Bold", "Arrow · leads to · from “Onboarding loses people at step two” to “Too many fields before value”",
      "Arrow · from a point to “Interviews”", "Arrow · from something no longer on the canvas to", "Drawn by Sanne", "Proposed by Claude, needs review"]) {
      assert.ok(list.includes(line), `list has "${line}"`);
    }
    const proposedRow = page.locator(".list-row", { hasText: "Shape · Run a test" });
    assert.match(await proposedRow.locator(".status").innerText(), /Proposed/);
    await page.evaluate(() => { document.getElementById("list-view").hidden = true; });

    // ---- the page, at this width
    await page.evaluate(() => { window.testBoard.view.touched = false; window.testBoard.render(window.fixture); });
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), "No horizontal overflow.");
    const board = page.locator("#board");
    await board.screenshot({ path: resolve(output, `canvas-fixture-${width}.png`) });
    if (width === 1440 && process.env.CANVAS_SCREENSHOT) await board.screenshot({ path: process.env.CANVAS_SCREENSHOT });
    assert.deepEqual(errors, []);
    assert.deepEqual(failedRequests, []);
    await page.close();
    console.log(`PASS: five kinds drawn with their looks, a proposal drawn proposed, edge-to-edge arrows that follow open details, ` +
      `no arrow to a removed record, pan and drag through the layers, the list view, at ${width}px.`);
  }
} finally {
  await browser?.close();
  server.kill();
}
