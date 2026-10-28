/**
 * Provenance threads in a real browser, at 1920 by 1080 (DESIGN.md 1.2).
 *
 * In the style of canvas-objects-browser.mjs: a snapshot is injected straight
 * into a Board on the real page, and the threads tool is registered and
 * mounted against it the way app.mjs does, so this proves the drawing, not
 * the commands. The rail-side anchors (a review card with a crop, a People
 * row, a transcript row) are injected as markup by this test, through the
 * contracts the tool relies on, so it does not depend on how the rail is
 * drawn.
 *
 * It checks: one path per on-screen origin for each selected note, ending in
 * a dot on the origin's edge and starting on the note's edge; nothing on
 * deselect, and nothing running then; no thread to a rail tab that is not
 * shown, to a card scrolled out of the rail's view or under its tabs, or to a
 * card that is gone; that threads follow a pan, a zoom, a rail scroll and a
 * drag, coalesced to one frame; nothing while the strip is scrubbing; the
 * tokens they are drawn with; and no console errors.
 *
 *     node tests/threads-browser.mjs
 *
 * THREADS_SCREENSHOT=path saves the page with a selected note's threads
 * there; a copy always goes to .local/threads-ui/.
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
const output = resolve(client, "../../.local/threads-ui");
mkdirSync(output, { recursive: true });
const port = Number(process.env.THREADS_PORT || 5263);
const server = spawn(process.env.JARVAIDS_TEST_PYTHON || "python3",
  ["serve.py", "--port", String(port)], { cwd: client, stdio: "ignore" });
server.on("error", error => { throw error; });

const placed = (x, y) => ({ x, y, revision: 1, hand_placed: true });
const accepted = (id, text, x, y, extra = {}) => ({ id, kind: "item", revision: 1, position: placed(x, y),
  data: { item_kind: "content", status: "accepted", origin: "human", text, accepted_by: "a1", refs: [], ...extra } });
const FIXTURE = {
  actor_id: "a1",
  members: [{ id: "a1", name: "Sanne", role: "facilitator" }],
  records: [
    { id: "src", kind: "source", revision: 1, data: { source_type: "image", regions: [{ id: "r1" }, { id: "r2" }] } },
    // Accepted from proposal p0, which was quoted from transcript segment s1.
    accepted("i1", "Onboarding loses people at step two", 0, 0,
      { proposal_id: "p0", region_id: "r1", refs: [{ id: "src", revision: 1 }] }),
    accepted("i2", "People skip the tour", 0, 200),
    accepted("i3", "Too many fields before value", 460, 360),
    { id: "p1", kind: "proposal", revision: 1, position: placed(460, 0),
      data: { proposal_kind: "content", status: "needs_review", origin: "fixture", synthetic: true,
        text: "Ask what they expected on step two", region_id: "r2", refs: [{ id: "src", revision: 1 }] } },
    { id: "g1", kind: "item", revision: 1,
      data: { item_kind: "relationship", form: "cluster", status: "accepted", text: "Drop-off",
        refs: [{ id: "i1", revision: 1 }, { id: "i2", revision: 1 }] } },
    { id: "c1", kind: "item", revision: 1, position: null,
      data: { item_kind: "arrow", status: "accepted", origin: "human", made_by_hand: true, author_id: "a1",
        from: { id: "i1" }, to: { id: "i3" }, tone: "ink" } },
  ],
};
FIXTURE.board_order = FIXTURE.records.map(r => r.id);
const LINKS = { p0: { segmentId: "s1", time: 842, speakerActorId: "a1" } };

let browser;
try {
  for (let attempt = 0; ; attempt++) {
    try { const r = await fetch(`http://127.0.0.1:${port}/client/`); await r.arrayBuffer(); if (r.ok) break; } catch {}
    if (attempt >= 80) throw new Error("Static server did not start.");
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  browser = await chromium.launch({ headless: true,
    ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}) });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  const errors = [], failedRequests = [];
  page.on("pageerror", error => errors.push(error.message));
  page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
  page.on("requestfailed", request => failedRequests.push(request.url()));
  page.on("response", response => { if (response.status() >= 400) failedRequests.push(response.url()); });
  await page.goto(`http://127.0.0.1:${port}/client/`);
  await page.evaluate(async ([fixture, links]) => {
    // Every animation frame the page asks for, counted from before the tool
    // is mounted, so a test can tell whether the tool is idle.
    window.frames = 0;
    const raf = window.requestAnimationFrame.bind(window);
    window.requestAnimationFrame = fn => { window.frames++; return raf(fn); };
    localStorage.setItem("jv.quotes.links", JSON.stringify(links));
    document.getElementById("screen-setup").hidden = true;
    document.getElementById("screen-workspace").hidden = false;

    // The rail-side anchors, as the contracts describe them. A crop is any
    // image; this one is drawn inline so nothing is fetched.
    const crop = "data:image/svg+xml," + encodeURIComponent(
      "<svg xmlns='http://www.w3.org/2000/svg' width='280' height='140'><rect width='280' height='140' fill='khaki'/></svg>");
    document.getElementById("queue-empty").hidden = true;
    document.getElementById("queue").innerHTML =
      `<article class="proposal provisional" data-id="p1"><div class="evidence">` +
      `<img src="${crop}" width="280" height="140" alt="The part of the photograph this was read from"></div>` +
      `<textarea rows="2" aria-label="The text">Ask what they expected on step two</textarea></article>`;
    document.getElementById("people-rows").innerHTML =
      `<li class="person" data-actor-id="a1"><span class="person-name">Sanne</span><span class="t-meta role">Facilitator</span></li>`;
    document.getElementById("transcript").innerHTML =
      `<div class="jv-row transcript-row" id="seg-s1" data-segment-id="s1"><span class="t-signal">14:02</span>` +
      `<span class="t-body transcript-words">They give up when the second step asks for a phone number.</span></div>`;

    // A fresh board on the real element, and the threads tool mounted on it
    // as app.mjs mounts it, with the board's hooks calling the tool's.
    const old = document.getElementById("board");
    const fresh = old.cloneNode(false);
    old.replaceWith(fresh);
    const { Board } = await import("/client/board.mjs");
    const { register } = await import("/client/tools/threads.mjs");
    let hooks = null;
    register((name, h) => { hooks = h; });
    window.sent = [];
    const ctx = { app: { snapshot: fixture } };
    const board = new Board(fresh, {
      send: async (operation, payload) => { window.sent.push([operation, payload]); },
      review: () => {}, attention: () => {}, crop: async () => "", revoke: () => {},
      onSelection: ids => hooks.onSelection(ids),
      onZoom: z => hooks.onZoom(z),
    });
    Object.defineProperty(ctx, "board", { get: () => board });
    hooks.mount(ctx);
    board.render(fixture);
    hooks.render(ctx, fixture);
    window.testBoard = board;
    window.threadHooks = hooks;
    window.threadCtx = ctx;
    window.fixture = fixture;
  }, [FIXTURE, LINKS]);
  await page.waitForFunction(() => document.querySelector("#queue img")?.complete);

  const frame = () => page.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))));
  const select = async (id, additive = false) => { await page.evaluate(([id, a]) => window.testBoard.select(id, a), [id, additive]); await frame(); };
  const threads = () => page.$$eval("#threads path", ps => ps.map(p => `${p.dataset.note}:${p.dataset.origin}`).sort());
  const count = async () => (await threads()).length;
  // What is rendered, not the `hidden` property: an SVG element has no such
  // property, and reading it once agreed with code that drew nothing.
  const shown = () => page.$eval("#threads", s => !s.hasAttribute("hidden") && getComputedStyle(s).display !== "none" &&
    s.getBoundingClientRect().width > 0);
  const drawn = () => page.$$eval("#threads path", ps => ps.every(p => { const b = p.getBoundingClientRect(); return b.width + b.height > 0; }));
  const tab = async name => { await page.click(`[data-rail="${name}"]`); await frame(); };
  const pathOf = (note, origin) => page.$eval(`#threads path[data-note="${note}"][data-origin="${origin}"]`,
    p => p.getAttribute("d").match(/-?[\d.]+/g).map(Number));
  const dotOf = (note, origin) => page.$eval(`#threads circle[data-note="${note}"][data-origin="${origin}"]`,
    c => [Number(c.getAttribute("cx")), Number(c.getAttribute("cy"))]);
  const rectOf = selector => page.$eval(selector, el => { const r = el.getBoundingClientRect(); return { l: r.left, t: r.top, r: r.right, b: r.bottom }; });
  const onEdge = ([x, y], b) => {
    const inX = x >= b.l - 0.5 && x <= b.r + 0.5, inY = y >= b.t - 0.5 && y <= b.b + 0.5;
    const nearX = Math.min(Math.abs(x - b.l), Math.abs(x - b.r)) < 0.5, nearY = Math.min(Math.abs(y - b.t), Math.abs(y - b.b)) < 0.5;
    return (inX && nearY) || (inY && nearX);
  };

  // ---- nothing selected, nothing drawn
  assert.equal(await count(), 0);
  assert.equal(await shown(), false, "the layer stays hidden with no threads");

  // ---- the layer: page space, above everything, never a press target, tokens only
  const layer = await page.$eval("#threads", s => { const cs = getComputedStyle(s); return [cs.position, cs.pointerEvents, cs.zIndex]; });
  const zThreads = await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue("--z-threads").trim());
  assert.deepEqual(layer, ["fixed", "none", zThreads]);

  // ---- an accepted note in the Review tab: its group and its connector
  await select("i1");
  assert.deepEqual(await threads(), ["i1:connector", "i1:group"], "the person and the quote are on tabs not shown");
  assert.equal(await shown(), true, "the layer is rendered over the page");
  assert.equal(await drawn(), true, "and every thread has a box on screen");
  const look = await page.$eval("#threads path", p => { const cs = getComputedStyle(p); return [cs.stroke, cs.strokeWidth, cs.fill, cs.markerEnd]; });
  const dot = await page.$eval("#threads circle", c => { const cs = getComputedStyle(c); return [cs.fill, cs.r]; });
  const thread = await page.evaluate(() => { const i = document.createElement("i"); i.style.color = "var(--thread)"; document.body.append(i);
    const c = getComputedStyle(i).color; i.remove(); return c; });
  const ink3 = await page.evaluate(() => { const i = document.createElement("i"); i.style.color = "var(--ink-3)"; document.body.append(i);
    const c = getComputedStyle(i).color; i.remove(); return c; });
  assert.equal(thread, ink3, "--thread is --ink-3");
  assert.deepEqual(look, [ink3, "1px", "none", "none"], "1px --ink-3, no fill, no head");
  assert.deepEqual(dot, [ink3, "2px"], "a 4px --ink-3 dot");
  assert.ok(onEdge(await dotOf("i1", "group"), await rectOf('.hull[data-id="g1"] .hull-label')),
    "the group thread ends on the edge of the group's label");
  const middle = await page.$eval('[data-id="c1"] path', line => {
    const p = line.getPointAtLength(line.getTotalLength() / 2).matrixTransform(line.getScreenCTM()); return [p.x, p.y];
  });
  const connectorDot = await dotOf("i1", "connector");
  assert.ok(Math.hypot(connectorDot[0] - middle[0], connectorDot[1] - middle[1]) < 0.5,
    `the connector thread ends at the middle of its line: ${connectorDot} vs ${middle}`);
  const start = (await pathOf("i1", "group")).slice(0, 2);
  assert.ok(onEdge(start, await rectOf('.note[data-id="i1"]')), `and starts on the note's edge: ${start}`);

  // ---- the rail tab decides: People shows who accepted it, Transcript the quote
  await tab("people");
  assert.deepEqual(await threads(), ["i1:connector", "i1:group", "i1:person"]);
  assert.ok(onEdge(await dotOf("i1", "person"), await rectOf('.person[data-actor-id="a1"]')), "the person thread ends on the row's edge");
  await tab("transcript");
  assert.deepEqual(await threads(), ["i1:connector", "i1:group", "i1:transcript"], "the quote, through the accepted item's proposal_id");
  assert.ok(onEdge(await dotOf("i1", "transcript"), await rectOf("#seg-s1")));
  await tab("review");
  assert.deepEqual(await threads(), ["i1:connector", "i1:group"]);

  // ---- a second, proposed note: its crop in the review card
  await select("p1", true);
  assert.deepEqual(await threads(), ["i1:connector", "i1:group", "p1:crop"]);
  assert.ok(onEdge(await dotOf("p1", "crop"), await rectOf('.proposal[data-id="p1"] img')), "the crop thread ends on the image's edge");
  assert.ok(onEdge((await pathOf("p1", "crop")).slice(0, 2), await rectOf('.note[data-id="p1"]')));

  // The screenshot: two selected notes, one accepted and one proposed.
  await page.screenshot({ path: resolve(output, "threads-1920.png") });
  if (process.env.THREADS_SCREENSHOT) await page.screenshot({ path: process.env.THREADS_SCREENSHOT });

  // ---- deselect clears, and then nothing runs
  await select(null);
  assert.equal(await count(), 0, "deselect clears every thread");
  assert.equal(await shown(), false, "and hides the layer");
  assert.equal(await page.$eval("#threads", s => s.childElementCount), 0);
  await page.evaluate(() => { window.frames = 0; });
  await page.evaluate(() => {
    document.querySelector(".ws-rail").dispatchEvent(new Event("scroll"));
    window.dispatchEvent(new Event("scroll")); window.dispatchEvent(new Event("resize"));
    document.body.classList.add("idle-probe"); document.body.classList.remove("idle-probe");
    window.threadHooks.render(window.threadCtx, window.fixture);
    window.threadHooks.onZoom(1);
  });
  await page.mouse.move(300, 300); await page.mouse.down(); await page.mouse.move(340, 320, { steps: 4 }); await page.mouse.up();
  await page.waitForTimeout(200);
  assert.equal(await page.evaluate(() => window.frames), 0, "with nothing selected, no frame is ever asked for");
  await page.evaluate(() => { window.testBoard.view.touched = false; window.testBoard.render(window.fixture); });

  // ---- many triggers in one task, one recompute
  await select("p1");
  assert.equal(await count(), 1);
  const asked = await page.evaluate(() => {
    window.frames = 0;
    for (let i = 0; i < 20; i++) document.querySelector(".ws-rail").dispatchEvent(new Event("scroll"));
    for (let i = 0; i < 5; i++) window.testBoard.panBy(1, 0);
    window.threadHooks.render(window.threadCtx, window.fixture);
    return window.frames;
  });
  assert.equal(asked, 1, "twenty scrolls, five pans and a render ask for one frame");
  await frame();

  // ---- an origin scrolled out of the rail's view has no thread, and gets it back in view
  await page.evaluate(() => {
    // Room above and below the card, so the rail can scroll it anywhere.
    for (const [id, where] of [["spacer", "prepend"], ["spacer-below", "append"]]) {
      const spacer = document.createElement("div");
      spacer.id = id; spacer.style.height = "2400px";
      document.getElementById("queue")[where](spacer);
    }
    document.querySelector(".ws-rail").scrollTop = 0;
    window.threadHooks.render(window.threadCtx, window.fixture);
  });
  await frame();
  assert.equal(await count(), 0, "the card is below the rail's visible area");
  await page.evaluate(() => document.querySelector('.proposal[data-id="p1"] img').scrollIntoView({ block: "center" }));
  await frame();
  assert.deepEqual(await threads(), ["p1:crop"], "scrolling the rail brings it back");
  // Put the image's top 160px below the note's middle, so the dot sits near
  // the image's top corner and has to travel with the image: a dot level
  // with the note would stay put whether or not it was recomputed.
  await page.evaluate(() => {
    const rail = document.querySelector(".ws-rail");
    const n = document.querySelector('#board .note[data-id="p1"]').getBoundingClientRect();
    const img = document.querySelector('.proposal[data-id="p1"] img').getBoundingClientRect();
    rail.scrollTop += img.top - (n.top + n.height / 2 + 160);
  });
  await frame();
  const before = await dotOf("p1", "crop");
  await page.evaluate(() => { document.querySelector(".ws-rail").scrollTop += 60; });
  await frame();
  const after = await dotOf("p1", "crop");
  // Where the dot should be now, worked out from the image's new place with
  // the tool's own geometry; and, because the image was put below the note
  // above, exactly 60px higher. Before phase 4 this step assumed the second
  // alone, which held only while the board was short enough to keep the
  // note above the image.
  const want = await page.evaluate(async () => {
    const { threadEnds, visibleRect } = await import("/client/tools/threads.mjs");
    const note = visibleRect(document.querySelector('#board .note[data-id="p1"]'));
    const img = visibleRect(document.querySelector('.proposal[data-id="p1"] img'));
    const { origin } = threadEnds(note, img);
    return [origin.x, origin.y];
  });
  assert.ok(Math.abs(after[1] - want[1]) < 1 && Math.abs(after[0] - want[0]) < 1,
    `the dot follows the rail's scroll: ${before} to ${after}, expected ${want}`);
  assert.ok(Math.abs(after[1] - (before[1] - 60)) < 1, `the dot travelled with the image: ${before[1]} to ${after[1]}`);
  // Under the rail's sticky tabs: inside the scroll area, but covered.
  await page.evaluate(() => {
    const rail = document.querySelector(".ws-rail"), tabs = rail.querySelector(".tabs");
    const img = document.querySelector('.proposal[data-id="p1"] img');
    img.style.height = `${tabs.getBoundingClientRect().height - 4}px`;
    rail.scrollTop += img.getBoundingClientRect().top - tabs.getBoundingClientRect().top;
  });
  await frame();
  assert.ok(await page.evaluate(() => {
    const img = document.querySelector('.proposal[data-id="p1"] img').getBoundingClientRect();
    const tabs = document.querySelector(".ws-rail .tabs").getBoundingClientRect();
    return img.top >= tabs.top - 0.5 && img.bottom <= tabs.bottom + 0.5;
  }), "the crop sits wholly under the tabs");
  assert.equal(await count(), 0, "a crop under the rail's tabs has no thread");
  await page.evaluate(() => {
    document.getElementById("spacer").remove();
    document.getElementById("spacer-below").remove();
    document.querySelector('.proposal[data-id="p1"] img').style.height = "";
    document.querySelector(".ws-rail").scrollTop = 0;
  });
  await frame();
  assert.deepEqual(await threads(), ["p1:crop"]);

  // ---- an origin that is gone has no thread
  const card = await page.evaluate(() => {
    const el = document.querySelector('.proposal[data-id="p1"]'); const html = el.outerHTML; el.remove();
    window.threadHooks.render(window.threadCtx, window.fixture);
    return html;
  });
  await frame();
  assert.equal(await count(), 0, "a review card that is gone has no thread");
  await page.evaluate(html => { document.getElementById("queue").innerHTML = html; window.threadHooks.render(window.threadCtx, window.fixture); }, card);
  await page.waitForFunction(() => document.querySelector("#queue img")?.complete);
  await frame();
  assert.equal(await count(), 1);

  // ---- threads follow the world: pan and zoom
  await select("i1");
  const g0 = await pathOf("i1", "group");
  await page.evaluate(() => window.testBoard.panBy(120, 40));
  await frame();
  const g1 = await pathOf("i1", "group");
  assert.ok(Math.abs(g1[0] - g0[0] - 120) < 1 && Math.abs(g1[1] - g0[1] - 40) < 1, `a pan moves the thread with it: ${g0.slice(0, 2)} to ${g1.slice(0, 2)}`);
  await page.evaluate(() => window.testBoard.zoomBy(1.2));
  await frame();
  assert.notDeepEqual(await pathOf("i1", "group"), g1, "a zoom redraws it");
  assert.ok(onEdge((await pathOf("i1", "group")).slice(0, 2), await rectOf('.note[data-id="i1"]')), "still on the zoomed note's edge");

  // ---- and a drag, while it is in progress
  await page.evaluate(() => window.testBoard.zoomBy(1 / 1.2));
  await frame();
  const c0 = await pathOf("i1", "connector");
  const note = await page.locator('.note[data-id="i1"]').boundingBox();
  await page.mouse.move(note.x + 40, note.y + 14);
  await page.mouse.down();
  await page.mouse.move(note.x + 40, note.y + 94, { steps: 6 });
  await frame();
  const c1 = await pathOf("i1", "connector");
  const moved = await rectOf('.note[data-id="i1"]');
  assert.ok(moved.t - note.y > 40, `the note is mid-drag: ${note.y} to ${moved.t}`);
  assert.ok(Math.hypot(c1[0] - c0[0], c1[1] - c0[1]) > 2, `the thread follows the note during the drag: ${c0.slice(0, 2)} to ${c1.slice(0, 2)}`);
  assert.ok(onEdge(c1.slice(0, 2), moved), "from the dragged note's edge where it is now");
  await page.mouse.up();
  await page.waitForFunction(() => window.sent.length > 0, null, { timeout: 3000 });
  assert.equal(await page.evaluate(() => window.sent[0][0]), "item.place", "the drag still went to item.place");
  assert.deepEqual(await page.evaluate(() => window.testBoard.selection ?? [...window.testBoard.selected]), ["i1"], "and the note is still selected");

  // ---- not while the strip is scrubbing
  await page.evaluate(() => document.body.classList.add("scrubbing"));
  await frame();
  assert.equal(await count(), 0, "scrubbing on the body hides the threads");
  await page.evaluate(() => document.body.classList.remove("scrubbing"));
  await frame();
  assert.equal(await count(), 2, "and they return when it stops");
  await page.evaluate(() => window.testBoard.root.classList.add("scrubbing"));
  await frame();
  assert.equal(await count(), 0, "scrubbing on the board as well");
  await page.evaluate(() => window.testBoard.root.classList.remove("scrubbing"));
  await frame();
  assert.equal(await count(), 2);

  // ---- a note with no origins has no threads
  await select("i3");
  assert.deepEqual(await threads(), ["i3:connector"], "i3 has only its connector");
  await page.evaluate(() => {
    window.fixture.records = window.fixture.records.filter(r => r.id !== "c1");
    window.testBoard.render(window.fixture);
    window.threadHooks.render(window.threadCtx, window.fixture);
  });
  await frame();
  assert.equal(await count(), 0, "with the connector gone, i3 is a note nobody has substantiated");

  await select(null);
  assert.equal(await count(), 0);
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), "No horizontal overflow.");
  assert.deepEqual(errors, []);
  assert.deepEqual(failedRequests, []);
  await page.close();
  console.log("PASS: threads to the group, connector, person, quote and crop when on screen; none to a hidden tab, " +
    "a scrolled-out, covered or missing origin; cleared and idle on deselect; one frame per burst; follow pan, zoom, " +
    "rail scroll and drag; hidden while scrubbing; tokens; no console errors; at 1920 by 1080.");
} finally {
  await browser?.close();
  server.kill();
}
