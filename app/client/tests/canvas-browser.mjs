/**
 * The canvas and its tools, end to end: through the real server, on a real
 * screen, at 1920 by 1080 (the projector) and at 400px.
 *
 * Node plays the facilitator through the client library: it opens a session,
 * adds and accepts notes, places them, groups two of them and sends a
 * photograph to the stand-in reader. A browser joins as a participant and
 * uses the canvas: the empty state first, then the dock and its keyboard
 * shortcuts, a stroke drawn with the pen (a `stroke` record must exist and be
 * drawn), a connector between two notes with a label and Shift for direction
 * (an `arrow` record must exist and a curve be drawn with its label), and the
 * eraser removing the stroke. Proposed notes must sit askew within 1.5
 * degrees and accepted ones straight. No console errors anywhere.
 *
 *     node tests/canvas-browser.mjs
 *
 * SCREENSHOTS=dir saves the canvas (p3-canvas.png) and the empty state
 * (p3-canvas-empty.png) there; without it they go to .local/canvas-ui/.
 */
import { spawn } from "node:child_process";
import { mkdirSync, mkdtempSync, rmSync } from "node:fs";
import { createRequire } from "node:module";
import { tmpdir } from "node:os";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { GenAIClient, newId, newToken } from "../../server/client.mjs";

let chromium;
try { ({ chromium } = createRequire(import.meta.url)("playwright")); }
catch { console.log("SKIP: playwright is not installed."); process.exit(0); }

const require = createRequire(import.meta.url);
const HERE = dirname(fileURLToPath(import.meta.url));
const CLIENT = resolve(HERE, ".."), SERVER = resolve(CLIENT, "../server");
const SHOTS = process.env.SCREENSHOTS || resolve(CLIENT, "../../.local/canvas-ui");
mkdirSync(SHOTS, { recursive: true });
const STATIC_PORT = 5197, API_PORT = 3097, API = `http://127.0.0.1:${API_PORT}`;
const PYTHON = process.env.JARVAIDS_TEST_PYTHON || "python3";
const data = mkdtempSync(join(tmpdir(), "jarvaids-canvas-tools-"));
const children = [];
const start = (command, args, cwd) => children.push(spawn(command, args, { cwd, stdio: "ignore" }));
const stopAll = () => { for (const c of children) { try { c.kill("SIGTERM"); } catch {} } try { rmSync(data, { recursive: true, force: true }); } catch {} };
process.on("exit", stopAll);
start(PYTHON, ["serve.py", "--port", String(STATIC_PORT)], CLIENT);
start(PYTHON, ["-m", "genai_server", "--port", String(API_PORT), "--data-dir", data,
  "--allow-origin", `http://127.0.0.1:${STATIC_PORT}`], SERVER);
const ready = async url => {
  for (let i = 0; i < 80; i++) {
    try { const r = await fetch(url); await r.arrayBuffer(); if (r.ok) return; } catch {}
    await new Promise(r => setTimeout(r, 150));
  }
  throw new Error("server never became ready: " + url);
};
await ready(`http://127.0.0.1:${STATIC_PORT}/client/index.html`);
await ready(`${API}/health`);

/** A 64x64 grey PNG built by hand, as the journey does, so the stand-in
 * reader has a photograph without a fixture file. */
function tinyPng() {
  const { deflateSync } = require("node:zlib");
  const size = 64, raw = Buffer.alloc((size * 3 + 1) * size, 0x90);
  for (let y = 0; y < size; y++) raw[y * (size * 3 + 1)] = 0;
  const crcTable = Array.from({ length: 256 }, (_, n) => {
    let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; return c >>> 0;
  });
  const crc = buf => { let c = 0xffffffff; for (const b of buf) c = crcTable[(c ^ b) & 0xff] ^ (c >>> 8); return (c ^ 0xffffffff) >>> 0; };
  const chunk = (type, body) => {
    const len = Buffer.alloc(4); len.writeUInt32BE(body.length);
    const all = Buffer.concat([Buffer.from(type, "ascii"), body]);
    const sum = Buffer.alloc(4); sum.writeUInt32BE(crc(all));
    return Buffer.concat([len, all, sum]);
  };
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(size, 0); ihdr.writeUInt32BE(size, 4); ihdr[8] = 8; ihdr[9] = 2;
  return Buffer.concat([Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk("IHDR", ihdr), chunk("IDAT", deflateSync(raw)), chunk("IEND", Buffer.alloc(0))]);
}

// ---- the facilitator, in Node -------------------------------------------
const owner = new GenAIClient({ baseUrl: API, sessionId: newId(), token: newToken() });
await owner.create({ ownerName: "Sam", title: "Canvas tools" });
const run = async (op, payload) => (await owner.submit(owner.intent(op, payload))).result;
let snap = await owner.snapshot();
await run("consent.acknowledge", { policy_version: snap.session.policy_version });
snap = await owner.snapshot();
await run("session.activate", { policy_version: snap.session.policy_version, expected_session_revision: snap.session.revision });
const records = async () => (await owner.snapshot()).records;
const until = async (what, fn, timeout = 15000) => {
  for (const end = Date.now() + timeout; Date.now() < end;) {
    const value = await fn();
    if (value) return value;
    await new Promise(r => setTimeout(r, 250));
  }
  throw new Error(`timed out waiting for ${what}`);
};

const invitation = newToken();
snap = await owner.snapshot();
await run("participant.invite", { invitation, expected_roster_revision: snap.session.roster_revision, role: "participant" });
const code = `${snap.session.id}.${snap.session.policy_version}.${invitation}`;

// ---- a participant, in a browser ----------------------------------------
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
const errors = [];
page.on("pageerror", e => errors.push(String(e)));
page.on("console", m => { if (m.type() === "error") errors.push(m.text()); });
page.on("response", r => { if (r.status() >= 400) errors.push(`${r.status()} ${r.url().slice(-80)}`); });
let failures = 0;
const step = async (label, fn) => {
  try { await fn(); console.log("ok   " + label); }
  catch (error) {
    failures++;
    const said = await page.evaluate(() => { const a = document.getElementById("attention"); return a && !a.hidden ? a.textContent : ""; }).catch(() => "");
    console.log("FAIL " + label + "\n       " + String(error.message).split("\n")[0].slice(0, 240) + (said ? "\n       app said: " + said.trim() : ""));
  }
};
const expect = (ok, message) => { if (!ok) throw new Error(message); };
const tool = () => page.$eval("#board", b => b.dataset.tool);
const pressed = () => page.$$eval("#dock .dock-tools .dock-button", bs => bs.filter(b => b.getAttribute("aria-pressed") === "true").map(b => b.dataset.tool));
const angle = el => el.evaluate(n => { const r = getComputedStyle(n).rotate; return r === "none" ? 0 : parseFloat(r); });
const noOverflow = () => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1);

await page.goto(`http://127.0.0.1:${STATIC_PORT}/client/`, { waitUntil: "networkidle" });
await page.click(".advanced summary");
await page.fill("#base-url", API);
await page.fill("#join-name", "Jo");
await page.fill("#join-invitation", code);
await page.click("#join");
await page.waitForSelector("#screen-workspace:not([hidden])", { timeout: 10000 });
// Which motion classes the board puts on notes, as they are put on.
await page.evaluate(() => {
  window.motions = new Set();
  new MutationObserver(changes => {
    for (const c of changes) for (const k of ["note-landing", "note-accepting", "note-rejecting"]) {
      if (typeof c.target.className === "string" && c.target.className.includes(k)) window.motions.add(k);
    }
  }).observe(document.getElementById("board"), { attributes: true, attributeFilter: ["class"], subtree: true });
});
const motions = () => page.evaluate(() => [...window.motions]);

await step("an empty wall says so, centred, on a lilac rectangle turned two degrees, with two ways to start", async () => {
  await page.waitForSelector("#board-empty:not([hidden])", { timeout: 5000 });
  expect((await page.textContent("#board-empty .t-display")).trim() === "Nothing on the wall yet.", "the Display line");
  const card = page.locator(".board-empty-card");
  const look = await card.evaluate(el => {
    const before = getComputedStyle(el, "::before");
    return { rotate: before.rotate, width: el.getBoundingClientRect().width };
  });
  expect(look.rotate === "-2deg", "the rectangle is turned -2deg: " + look.rotate);
  expect(look.width <= 560.5, "at most 560px wide: " + look.width);
  const board = await page.locator("#board").boundingBox(), box = await card.boundingBox();
  const dx = Math.abs((box.x + box.width / 2) - (board.x + board.width / 2)), dy = Math.abs((box.y + box.height / 2) - (board.y + board.height / 2));
  expect(dx < 2 && dy < 2, `centred on the board: off by ${dx}, ${dy}`);
  await page.screenshot({ path: join(SHOTS, "p3-canvas-empty.png") });
  await page.click("#empty-note");
  expect(await page.evaluate(() => document.activeElement?.id) === "note-text", "Add a note focuses the composer");
  await page.click("#empty-photo");
  await page.waitForSelector("#screen-photo:not([hidden])", { timeout: 5000 });
  // A sheet over the workspace, not a page: the canvas stays in view behind it.
  expect(await page.isVisible("#board"), "the board stays visible under the photograph sheet");
  await page.waitForTimeout(400);   // past the sheet's entrance, so the shot shows it settled
  await page.screenshot({ path: join(SHOTS, "p3-photo-sheet.png") });
  await page.keyboard.press("Escape");
  await page.waitForSelector("#screen-photo", { state: "hidden", timeout: 5000 });
  await page.waitForSelector("#screen-workspace:not([hidden])", { timeout: 5000 });
});

await step("the empty state fits a phone width", async () => {
  await page.setViewportSize({ width: 400, height: 860 });
  await page.waitForTimeout(200);
  expect(await noOverflow(), "horizontal overflow at 400px");
  const card = await page.locator(".board-empty-card").boundingBox();
  expect(card.x >= 0 && card.x + card.width <= 400, `the card is inside the screen: ${card.x}, ${card.width}`);
  await page.setViewportSize({ width: 1920, height: 1080 });
});

// Notes, placed, two of them grouped; then a photograph for the stand-in reader.
const accept = async text => {
  const added = await run("source.text", { text });
  return (await run("proposal.review", { proposal_id: added.proposal.id, expected_revision: added.proposal.revision, decision: "accept" })).item;
};
const story = await accept("Steve gave up at the second form");
const reason = await accept("He could not find where to start");
const third = await accept("Make the first step one field");
await run("item.place", { placements: [
  { id: story.id, x: 0, y: 0, expected_position_revision: 0 },
  { id: reason.id, x: 320, y: 0, expected_position_revision: 0 },
  { id: third.id, x: 780, y: 220, expected_position_revision: 0 },
] });
const group = await run("proposal.create", { proposal_kind: "relationship", form: "cluster", text: "Steve's story",
  refs: [{ id: story.id, revision: story.revision }, { id: reason.id, revision: reason.revision }] });
await run("proposal.review", { proposal_id: group.id, expected_revision: group.revision, decision: "accept" });

// The participant photographs the wall, so the crops are theirs to see.
await step("a photograph of two notes is read by the stand-in reader", async () => {
  await page.click("#open-photo");
  await page.waitForSelector("#screen-photo:not([hidden])", { timeout: 5000 });
  await page.setInputFiles("#photo", { name: "wall.png", mimeType: "image/png", buffer: tinyPng() });
  await page.waitForSelector("#photo-stage:not([hidden])", { timeout: 5000 });
  await page.waitForFunction(() => document.getElementById("photo-preview").naturalWidth > 0, null, { timeout: 5000 });
  const stage = await page.locator(".stage").boundingBox();
  for (const [x0, y0] of [[0.05, 0.05], [0.55, 0.55]]) {
    await page.mouse.move(stage.x + stage.width * x0, stage.y + stage.height * y0);
    await page.mouse.down();
    await page.mouse.move(stage.x + stage.width * (x0 + 0.35), stage.y + stage.height * (y0 + 0.35), { steps: 4 });
    await page.mouse.up();
  }
  await page.click("#send-photo");
  // Sending closes the sheet; the reading is followed from the card in the
  // corner while the canvas stays in use.
  await page.waitForSelector("#screen-photo", { state: "hidden", timeout: 5000 });
  await page.waitForSelector("#photo-reading:not([hidden])", { timeout: 5000 });
  await page.waitForSelector("#found-review:not([hidden])", { timeout: 15000 });
  await page.waitForTimeout(400);
  await page.screenshot({ path: join(SHOTS, "p3-reading-card.png") });
  const card = await page.locator("#photo-reading").boundingBox(), view = page.viewportSize();
  expect(card.x + card.width <= view.width && card.y + card.height <= view.height && card.x > view.width / 2 && card.y + card.height > view.height / 2,
    `the reading card sits in the bottom right corner: ${JSON.stringify(card)}`);
  expect(card.height <= view.height / 2, `the card with two readings takes at most half the window: ${card.height}`);
  await page.click("#reading-dismiss");
  await page.waitForSelector("#photo-reading", { state: "hidden", timeout: 5000 });
  await page.waitForSelector("#screen-workspace:not([hidden])", { timeout: 5000 });
});
const readings = await until("the stand-in reader's proposals", async () => {
  const found = (await records()).filter(r => r.kind === "proposal" && r.data.region_id && r.data.status === "needs_review");
  return found.length >= 2 ? found : null;
});

await step("the dock floats at the board's bottom left with the four tools, zoom and the view toggle", async () => {
  await page.waitForSelector("#dock:not([hidden])", { timeout: 5000 });
  const tools = await page.$$eval("#dock .dock-tools .dock-button", bs => bs.map(b => [b.dataset.tool, b.getAttribute("aria-label"), b.querySelector("svg") !== null]));
  expect(JSON.stringify(tools.map(t => t[0])) === JSON.stringify(["select", "draw", "erase", "connect"]), "tool order: " + JSON.stringify(tools));
  expect(tools.every(t => t[1] && t[2]), "each tool has a label and an icon");
  for (const id of ["zoom-out", "zoom-level", "zoom-in", "zoom-fit"]) expect(await page.locator(`#dock #${id}`).count() === 1, `#${id} in the dock`);
  expect(await page.locator('#dock [data-view="canvas"]').count() === 1, "the view toggle in the dock");
  const dock = await page.locator("#dock").boundingBox(), board = await page.locator("#board").boundingBox();
  expect(Math.abs(dock.x - board.x - 16) < 2 && Math.abs(board.y + board.height - dock.y - dock.height - 16) < 2,
    `bottom left, 16px in: dock ${JSON.stringify(dock)} board ${JSON.stringify(board)}`);
  expect(JSON.stringify(await pressed()) === '["select"]', "select is the tool at first");
});

await step("proposed notes sit askew within 1.5 degrees; accepted notes are straight", async () => {
  await page.waitForFunction(n => document.querySelectorAll(".note.item-provisional").length >= n, readings.length, { timeout: 10000 });
  await page.waitForFunction(() => document.querySelectorAll(".note.item-accepted").length >= 3, null, { timeout: 10000 });
  await page.waitForTimeout(500);   // past the landing motion
  for (const n of await page.locator(".note.item-provisional").all()) {
    const a = await angle(n);
    expect(Math.abs(a) <= 1.5 && Math.abs(a) > 0, "a proposed note's angle: " + a);
    expect(/Proposed/.test(await n.locator(".badge").textContent()), "the mono Proposed marker");
  }
  for (const n of await page.locator(".note.item-accepted").all()) expect(await angle(n) === 0, "an accepted note is straight");
  // Accepted while this screen watches: it settles straight.
  const fresh = (await records()).find(r => r.id === readings[0].id);
  await run("proposal.review", { proposal_id: fresh.id, expected_revision: fresh.revision, decision: "accept" });
  await page.waitForFunction(() => document.querySelectorAll(".note.item-accepted").length >= 4, null, { timeout: 10000 });
  await page.waitForTimeout(500);
  for (const n of await page.locator(".note.item-accepted").all()) expect(await angle(n) === 0, "the newly accepted note is straight");
  const stamp = await page.locator(".note.item-accepted .meta").first().textContent();
  expect(/^Accepted by Sam \d\d:\d\d$/.test(stamp), "the stamp says who and when: " + stamp);
  const seen = await motions();
  expect(seen.includes("note-landing") && seen.includes("note-accepting"), "the readings landed and the accepted one settled: " + seen);
});

await step("a group is a soft rectangle with its label inside, nothing cut off", async () => {
  await page.click("#zoom-fit");
  const hull = page.locator(".hull").first();
  expect(/Group · Steve's story/.test(await hull.locator(".hull-label").textContent()), "the group's label");
  expect(await angle(hull) === 0, "an accepted group is straight");
  const label = await hull.locator(".hull-label").boundingBox(), box = await hull.boundingBox(), board = await page.locator("#board").boundingBox();
  expect(label.y >= box.y && label.y + label.height <= box.y + box.height, "the label is inside the rectangle");
  expect(label.y >= board.y, "the label is not cut off by the board's top edge");
});

await step("the shortcuts choose tools, and never while typing", async () => {
  await page.locator("#board").focus();
  for (const [key, name] of [["d", "draw"], ["e", "erase"], ["c", "connect"], ["v", "select"]]) {
    await page.keyboard.press(key);
    expect(await tool() === name, `${key} chooses ${name}, got ${await tool()}`);
    expect(JSON.stringify(await pressed()) === JSON.stringify([name]), `the dock shows ${name} pressed`);
  }
  await page.click("#note-text");
  await page.keyboard.press("d");
  expect(await tool() === "select", "typing d in a field must not switch to the pen");
  expect(await page.inputValue("#note-text") === "d", "the d reached the field");
  await page.fill("#note-text", "");
  await page.click('#dock [data-tool="draw"]');
  expect(await tool() === "draw", "pressing the pen in the dock chooses it");
  await page.click('#dock [data-tool="select"]');
});

/** A screen rectangle over empty board, found by asking the page what is
 * under a grid of points: nothing but the board itself, all the way along. */
const emptySpot = async (w, h) => page.evaluate(([w, h]) => {
  const board = document.getElementById("board").getBoundingClientRect();
  const clear = (x, y) => document.elementFromPoint(x, y)?.id === "board";
  for (let y = board.top + 40; y < board.bottom - 140 - h; y += 20) {
    for (let x = board.left + 40; x < board.right - 40 - w; x += 20) {
      let ok = true;
      for (let i = 0; i <= 8 && ok; i++) for (let j = 0; j <= 4 && ok; j++) ok = clear(x + w * i / 8, y + h * j / 4);
      if (ok) return { x, y };
    }
  }
  return null;
}, [w, h]);

const drawStroke = async () => {
  const at = await emptySpot(200, 80);
  expect(at, "no empty part of the board to draw on");
  await page.keyboard.press("d");
  await page.mouse.move(at.x, at.y + 40);
  await page.mouse.down();
  for (let i = 1; i <= 24; i++) await page.mouse.move(at.x + i * 8, at.y + 40 + Math.sin(i / 3) * 30);
  await page.mouse.up();
  return at;
};

let stroke, strokeAt;
await step("the pen draws a stroke: a stroke record exists, and the board draws it from the snapshot", async () => {
  const before = new Set((await records()).map(r => r.id));
  strokeAt = await drawStroke();
  stroke = await until("a stroke record", async () =>
    (await records()).find(r => !before.has(r.id) && r.kind === "item" && r.data.item_kind === "stroke"));
  expect(stroke.data.origin === "human" && stroke.data.made_by_hand === true, "made by hand");
  expect(stroke.data.tone === "ink" && stroke.data.weight === "regular", "ink, regular");
  expect(JSON.stringify(stroke.data.points[0]) === "[0,0]", "relative to its first point: " + JSON.stringify(stroke.data.points[0]));
  expect(stroke.data.points.length >= 2 && stroke.data.points.length <= 256, "2 to 256 points");
  await page.waitForSelector(`.links .pen[data-id="${stroke.id}"]`, { state: "attached", timeout: 8000 });
  const look = await page.$eval(`.links .pen[data-id="${stroke.id}"]`, p => [getComputedStyle(p).strokeWidth, p.getAttribute("d")]);
  expect(look[0] === "3px", "the one pen weight: " + look[0]);
  expect(/ Q /.test(look[1]), "smoothed into curves");
  expect(await page.locator(".drafts .draft-stroke").count() === 0, "the draft is gone once the stroke is drawn");
  await page.keyboard.press("v");
});

let arrow;
await step("the connector joins two notes with a curve and a label; Shift makes it directed", async () => {
  await page.keyboard.press("c");
  expect(await tool() === "connect", "connect chosen");
  const a = await page.locator(`.note[data-id="${reason.id}"]`).boundingBox();
  const b = await page.locator(`.note[data-id="${third.id}"]`).boundingBox();
  await page.mouse.click(a.x + 24, a.y + 14);
  await page.waitForSelector(`.note[data-id="${reason.id}"].connect-from`, { timeout: 3000 });
  await page.mouse.move(b.x - 40, b.y + 30, { steps: 4 });
  expect(await page.locator(".drafts .connector-preview").count() === 1, "a preview follows the pointer");
  await page.keyboard.down("Shift");
  await page.mouse.click(b.x + 24, b.y + 14);
  await page.keyboard.up("Shift");
  await page.waitForSelector(".connector-input", { timeout: 3000 });
  await page.waitForFunction(() => document.activeElement?.classList.contains("connector-input"), null, { timeout: 3000 });
  await page.keyboard.type("leads to");
  await page.keyboard.press("Enter");
  arrow = await until("an arrow record", async () =>
    (await records()).find(r => r.kind === "item" && r.data.item_kind === "arrow" && r.data.label === "leads to"));
  expect(arrow.data.from.id === reason.id && arrow.data.to.id === third.id && arrow.data.tone === "ink", "from, to and tone: " + JSON.stringify(arrow.data));
  const curve = page.locator(`.links .connector[data-id="${arrow.id}"]`);
  await curve.waitFor({ state: "attached", timeout: 8000 });
  expect(/^M [-\d.]+ [-\d.]+ C /.test(await curve.locator(".arrow-line").getAttribute("d")), "a cubic curve");
  await page.waitForFunction(id => document.querySelector(`.links .connector[data-id="${id}"] .connector-head`), arrow.id, { timeout: 5000 });
  const kept = await page.evaluate(() => JSON.parse(localStorage.getItem("jv.connectors.directed") || "[]"));
  expect(kept.includes(arrow.id), "the direction is kept on this device");
  expect((await page.locator(".cobj-float .connector-label", { hasText: "leads to" }).count()) === 1, "the label is drawn at the middle");
  const stroke = await curve.locator(".arrow-line").evaluate(p => getComputedStyle(p).stroke);
  const human = await page.evaluate(() => { const i = document.createElement("i"); i.style.color = "var(--mark-human)"; document.body.append(i); const c = getComputedStyle(i).color; i.remove(); return c; });
  expect(stroke === human, `the human mark: ${stroke} vs ${human}`);
});

await step("a connector made without Shift and with Escape has no head and no label", async () => {
  const a = await page.locator(`.note[data-id="${story.id}"]`).boundingBox();
  const b = await page.locator(`.note[data-id="${reason.id}"]`).boundingBox();
  await page.mouse.click(a.x + 24, a.y + 14);
  await page.mouse.click(b.x + 24, b.y + 40);
  await page.waitForSelector(".connector-input", { timeout: 3000 });
  await page.waitForFunction(() => document.activeElement?.classList.contains("connector-input"), null, { timeout: 3000 });
  await page.keyboard.press("Escape");
  const plain = await until("the second arrow", async () =>
    (await records()).find(r => r.kind === "item" && r.data.item_kind === "arrow" && r.data.from.id === story.id));
  expect(!("label" in plain.data), "no label");
  await page.waitForSelector(`.links .connector[data-id="${plain.id}"]`, { state: "attached", timeout: 8000 });
  expect(await page.locator(`.links .connector[data-id="${plain.id}"] .connector-head`).count() === 0, "undirected: no head");
  await page.keyboard.press("v");
});

await step("presses on marks still reach the board while the eraser is not in hand", async () => {
  const hit = await page.$eval(`.links .pen[data-id="${stroke.id}"]`, p => {
    const { x, y } = p.getPointAtLength(p.getTotalLength() / 2);
    const m = p.getScreenCTM();
    const sx = m.a * x + m.c * y + m.e, sy = m.b * x + m.d * y + m.f;
    return document.elementFromPoint(sx, sy)?.id;
  });
  expect(hit === "board", "a press on a stroke reaches the board: " + hit);
});

await page.mouse.move(5, 5);
await page.waitForTimeout(400);   // past the dock's own transitions
await page.screenshot({ path: join(SHOTS, "p3-canvas.png") });

await step("the eraser dims a stroke under the pointer and removes it with a click", async () => {
  await page.keyboard.press("e");
  const point = await page.$eval(`.links .pen[data-id="${stroke.id}"]`, p => {
    const { x, y } = p.getPointAtLength(p.getTotalLength() / 2);
    const m = p.getScreenCTM();
    return { x: m.a * x + m.c * y + m.e, y: m.b * x + m.d * y + m.f };
  });
  await page.mouse.move(point.x, point.y);
  const dim = await page.$eval(`.links .pen[data-id="${stroke.id}"]`, p => Number(getComputedStyle(p).opacity));
  expect(dim < 1, "hovering dims the stroke: " + dim);
  await page.mouse.click(point.x, point.y);
  await until("the stroke to be removed", async () => (await records()).find(r => r.id === stroke.id)?.data.status === "undone");
  await page.waitForFunction(id => !document.querySelector(`.links .pen[data-id="${id}"]`), stroke.id, { timeout: 8000 });
  await page.keyboard.press("v");
});

await step("a rejected reading fades out and leaves nothing behind", async () => {
  const fresh = (await records()).find(r => r.id === readings[1].id);
  await run("proposal.review", { proposal_id: fresh.id, expected_revision: fresh.revision, decision: "reject" });
  await page.waitForFunction(() => document.querySelectorAll(".note.item-provisional").length === 0, null, { timeout: 8000 });
  await page.waitForFunction(() => !document.querySelector(".note-ghost"), null, { timeout: 3000 });
  expect((await motions()).includes("note-rejecting"), "the rejected note left with the rejecting motion");
});

await step("at 400px: no sideways scroll, the dock inside the screen, the tools still work", async () => {
  await page.setViewportSize({ width: 400, height: 860 });
  await page.waitForTimeout(300);
  expect(await noOverflow(), "horizontal overflow at 400px");
  const dock = await page.locator("#dock").boundingBox();
  expect(dock.x >= 0 && dock.x + dock.width <= 400, "the dock fits: " + JSON.stringify(dock));
  await page.locator("#board").scrollIntoViewIfNeeded();
  await page.locator("#board").focus();
  await page.click("#zoom-fit");
  const before = new Set((await records()).map(r => r.id));
  await drawStroke();
  await until("a stroke drawn at 400px", async () =>
    (await records()).find(r => !before.has(r.id) && r.kind === "item" && r.data.item_kind === "stroke"));
  await page.keyboard.press("v");
  for (const n of await page.locator(".note.item-provisional").all()) expect(Math.abs(await angle(n)) <= 1.5, "askew within 1.5 at 400px");
  await page.click('[data-view="list"]');
  expect(await page.isVisible('#dock [data-view="canvas"]'), "the way back to the canvas stays in the list");
  expect(!(await page.isVisible("#dock .dock-tools")), "the drawing tools step aside in the list");
  await page.click('[data-view="canvas"]');
  await page.setViewportSize({ width: 1920, height: 1080 });
});

await step("no console errors", async () => { expect(!errors.length, errors.join(" | ").slice(0, 400)); });

await browser.close();
stopAll();
console.log(failures ? `\n${failures} step(s) failed` : "\ncanvas tools passed");
process.exit(failures ? 1 : 0);
