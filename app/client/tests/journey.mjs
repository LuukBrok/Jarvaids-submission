/**
 * The client journey, driven in a real browser.
 *
 * Everything else in this repository tests a mechanism. This tests the only
 * thing a person actually touches, and it exists because the client's first
 * three defects were all invisible to assertions: a favicon 404, a library
 * whose default timers throw in a browser but not in Node, and a stylesheet
 * rule of mine that painted black text on the design system's black
 * background. Two of those three needed a screenshot or a console to see.
 *
 * It starts both servers itself, so there is nothing to remember.
 *
 *     node tests/journey.mjs
 *
 * Playwright and a Chromium are required. If they are missing this SKIPS with
 * a message rather than failing, because a missing browser is not a broken
 * client, and a check that cannot tell those apart teaches people to ignore
 * it. CI installs both, so CI runs it for real.
 */
import { spawn } from "node:child_process";
import { createRequire } from "node:module";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const HERE = dirname(fileURLToPath(import.meta.url));
const CLIENT = resolve(HERE, "..");
const SERVER = resolve(CLIENT, "../server");
const STATIC_PORT = 5177, API_PORT = 3077;

let chromium;
try {
  ({ chromium } = require("playwright"));
} catch {
  console.log("SKIP: playwright is not installed. `npm i -D playwright` and `npx playwright install chromium`.");
  process.exit(0);
}

const data = mkdtempSync(join(tmpdir(), "jarvaids-journey-"));
const children = [];
const spawnPart = (label, command, args, cwd) => {
  const child = spawn(command, args, { cwd, stdio: ["ignore", "pipe", "pipe"] });
  child.stderr.on("data", d => process.env.VERBOSE && console.error(label, String(d).trim()));
  children.push(child);
  return child;
};
const stopAll = async () => {
  for (const c of children) { try { c.kill("SIGTERM"); } catch {} }
  await Promise.all(children.map(c => new Promise(done => c.exitCode !== null || c.signalCode !== null ? done() : c.once("exit", done))));
  if (!resolve(data).startsWith(resolve(tmpdir()) + "/") && !resolve(data).startsWith(resolve(tmpdir()) + "\\")) throw new Error("Unsafe temporary cleanup path");
  rmSync(data, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 });
};
process.on("exit", () => { for (const c of children) { try { c.kill("SIGTERM"); } catch {} } });

spawnPart("static", process.env.JARVAIDS_TEST_PYTHON || "python3", ["serve.py", "--port", String(STATIC_PORT)], CLIENT);
spawnPart("api", process.env.JARVAIDS_TEST_PYTHON || "python3", ["-m", "genai_server", "--port", String(API_PORT),
  "--data-dir", data, "--allow-origin", `http://127.0.0.1:${STATIC_PORT}`], SERVER);

const ready = async url => {
  for (let i = 0; i < 80; i++) {
    // Read the body: an unread response from an HTTP/1.0 server that closes the
    // socket crashes Node's HTTP client once the page is larger than one read.
    try { const r = await fetch(url); await r.arrayBuffer(); if (r.ok) return true; } catch {}
    await new Promise(r => setTimeout(r, 150));
  }
  throw new Error("server never became ready: " + url);
};
await ready(`http://127.0.0.1:${STATIC_PORT}/client/index.html`);
await ready(`http://127.0.0.1:${API_PORT}/health`);

/** A 64x64 grey PNG built by hand, so the photo path runs without a fixture
 * file in the tree and without a PNG library in CI. */
function tinyPng() {
  const { deflateSync } = require("node:zlib");
  const size = 64, raw = Buffer.alloc((size * 3 + 1) * size, 0x90);
  for (let y = 0; y < size; y++) raw[y * (size * 3 + 1)] = 0;   // filter byte per row
  const crcTable = Array.from({ length: 256 }, (_, n) => {
    let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; return c >>> 0;
  });
  const crc = buf => { let c = 0xffffffff; for (const b of buf) c = crcTable[(c ^ b) & 0xff] ^ (c >>> 8); return (c ^ 0xffffffff) >>> 0; };
  const chunk = (type, data) => {
    const len = Buffer.alloc(4); len.writeUInt32BE(data.length);
    const body = Buffer.concat([Buffer.from(type, "ascii"), data]);
    const sum = Buffer.alloc(4); sum.writeUInt32BE(crc(body));
    return Buffer.concat([len, body, sum]);
  };
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(size, 0); ihdr.writeUInt32BE(size, 4); ihdr[8] = 8; ihdr[9] = 2;
  return Buffer.concat([Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk("IHDR", ihdr), chunk("IDAT", deflateSync(raw)), chunk("IEND", Buffer.alloc(0))]);
}

const SHOTS = process.env.SCREENSHOTS || "";
const browser = await chromium.launch({
  executablePath: process.env.CHROMIUM_PATH || undefined,
  // A fake microphone that plays a tone, and no permission prompt, so the
  // listening path runs headless. It proves the plumbing, not recognition.
  args: ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"],
});
const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, acceptDownloads: true });
await context.grantPermissions(["microphone"]);
const page = await context.newPage();
const consoleErrors = [], failedRequests = [];
page.on("console", m => { if (m.type() === "error") consoleErrors.push(m.text().slice(0, 160)); });
page.on("pageerror", e => consoleErrors.push("pageerror: " + String(e).slice(0, 160)));
// A read the sync library cancels on purpose (a control command such as Pause
// invalidates the poll in flight) is not a failure; a failed write always is.
page.on("requestfailed", r => {
  if (r.url().startsWith("blob:")) return;
  if (r.method() === "GET" && /ERR_ABORTED/.test(r.failure()?.errorText ?? "")) return;
  failedRequests.push(r.url().slice(-70));
});
const heartbeats = [];
page.on("request", r => { if (r.method() === "POST" && /"session\.heartbeat"/.test(r.postData() ?? "")) heartbeats.push(Date.now()); });

let failures = 0;
const step = async (label, fn) => {
  try { await fn(); console.log("ok   " + label); }
  catch (error) {
    failures++;
    // The app's own attention line usually names the cause; print it with the failure.
    const said = await page.evaluate(() => { const a = document.getElementById("attention"); return a && !a.hidden ? a.textContent : ""; }).catch(() => "");
    console.log("FAIL " + label + "\n       " + String(error.message).split("\n")[0].slice(0, 200) + (said ? "\n       app said: " + said : ""));
  }
};
const shot = async name => { if (SHOTS) await page.screenshot({ path: join(SHOTS, name + ".png"), fullPage: false }); };
const queue = n => page.waitForFunction(v => document.getElementById("queue-count").textContent === String(v), n, { timeout: 10000 });
const rail = name => page.click(`[data-rail="${name}"]`);
const note = text => page.locator(".note", { hasText: text });
/** The board redraws on every change it hears about, so a note can be replaced
 * between finding it and measuring it. Measure again rather than fail. */
const box = async locator => {
  for (let i = 0; i < 20; i++) { const b = await locator.boundingBox().catch(() => null); if (b) return b; await page.waitForTimeout(50); }
  return null;
};

await page.goto(`http://127.0.0.1:${STATIC_PORT}/client/`, { waitUntil: "networkidle" });
// The server address is folded away on the entry screen: most people never need it.
await page.click(".advanced summary");
await page.fill("#base-url", `http://127.0.0.1:${API_PORT}`);

await step("a session starts", async () => {
  await page.click("#create");
  await page.waitForSelector("#bar:not([hidden])", { timeout: 10000 });
});

await step("capture is gated on agreement, then the workspace opens", async () => {
  await page.waitForSelector("#consent:not([hidden])", { timeout: 5000 });
  // The order matters: agreement first, capture second, never the reverse.
  if (!(await page.$eval("#activate", e => e.disabled))) {
    throw new Error("capture could be started before anyone agreed");
  }
  if (!/Waiting for Facilitator to agree/.test(await page.textContent("#activate-reason"))) {
    throw new Error("Start capture must say whose agreement it waits for");
  }
  // Agreement is a ticked box, not a button that agrees on its own.
  if (!(await page.$eval("#acknowledge", e => e.disabled))) throw new Error("Agree worked without the box ticked");
  await page.check("#agree-check");
  await page.click("#acknowledge");
  await page.waitForFunction(() => !document.getElementById("activate").disabled, { timeout: 8000 });
  await page.click("#activate");
  // The session is open; "Recording" is kept for a microphone that is on.
  await page.waitForFunction(() => document.getElementById("state-word").textContent === "Session open", { timeout: 8000 });
  if (await page.isVisible("#listen-status")) throw new Error("Recording shows while no microphone is on");
  await page.waitForSelector("#screen-workspace:not([hidden])", { timeout: 5000 });
});

await step("a typed note lands on the canvas unreviewed, and is not drawn as a model guess", async () => {
  await page.fill("#note-text", "Onboarding loses people at step three");
  await page.click("#add-note");
  await queue(1);
  await note("step three").waitFor({ timeout: 5000 });
  const cls = await note("step three").getAttribute("class");
  if (/item-provisional/.test(cls)) throw new Error("a person typed it, so it must not carry provisional styling");
  if (!/item-pending/.test(cls)) throw new Error("an unreviewed note must not look accepted: " + cls);
});

await step("Review on the note opens it in the rail, and a correction survives acceptance", async () => {
  await note("step three").getByRole("button", { name: "Review" }).click();
  await page.waitForSelector("#rail-review:not([hidden]) .proposal.focused", { timeout: 5000 });
  await page.fill(".proposal.focused textarea", "Onboarding loses people at step two");
  await page.click(".proposal.focused .btn-primary");
  await queue(0);
  await page.waitForFunction(() => [...document.querySelectorAll(".note.item-accepted")].some(n => /step two/.test(n.textContent)), null, { timeout: 8000 });
});

await step("a reading from a photograph lands dashed and provisional, naming its adapter", async () => {
  // The fixture adapter marks its proposals `fixture`, a live one `model`.
  // The first client only knew the word `machine`, so a fixture reading was
  // drawn exactly like a person's note. This step walks that path.
  await page.click("#open-photo");
  await page.waitForSelector("#screen-photo:not([hidden])", { timeout: 5000 });
  await page.setInputFiles("#photo", { name: "wall.png", mimeType: "image/png", buffer: tinyPng() });
  await page.waitForSelector("#photo-stage:not([hidden])", { timeout: 5000 });
  await page.waitForFunction(() => document.getElementById("photo-preview").naturalWidth > 0, { timeout: 5000 });
  const stageEl = await page.$(".stage");
  await stageEl.scrollIntoViewIfNeeded();
  const stage = await stageEl.boundingBox();
  // Marks are normalised against the stage, so it must be exactly the photo.
  const image = await (await page.$("#photo-preview")).boundingBox();
  if (Math.abs(image.width - stage.width) > 1 || Math.abs(image.height - stage.height) > 1) {
    throw new Error(`the marking area is not the photograph: stage ${stage.width}x${stage.height}, photo ${image.width}x${image.height}`);
  }
  await page.mouse.move(stage.x + stage.width * .1, stage.y + stage.height * .1);
  await page.mouse.down();
  // Ends past the photograph's corner: the box must stop at the edge, because
  // the server refuses a region that leaves the image.
  await page.mouse.move(stage.x + stage.width * 1.5, stage.y + stage.height * 1.5, { steps: 6 });
  await page.mouse.up();
  const box = await page.evaluate(() => {
    const r = document.querySelector("#regions .region").style;
    return [r.left, r.top, r.width, r.height].map(parseFloat);
  });
  if (box[0] + box[2] > stage.width + .5 || box[1] + box[3] > stage.height + .5) {
    throw new Error("a box dragged off the photograph must stop at its edge: " + box);
  }
  await page.click("#send-photo");
  // Sending closes the sheet; the card in the corner follows the reading
  // through to what it found while the canvas stays in use.
  await page.waitForSelector("#screen-photo", { state: "hidden", timeout: 5000 });
  await page.waitForSelector("#found-review:not([hidden])", { timeout: 10000 });
  if (!/Here is what we found/.test(await page.textContent("#reading-word"))) throw new Error("no found step");
  await page.click("#found-review");
  await queue(1);
  const reading = page.locator(".note.item-provisional");
  await reading.waitFor({ timeout: 8000 });
  if (!/Proposed/.test(await reading.locator(".badge").textContent())) throw new Error("no Proposed tag");
  await rail("review");
  const label = await page.textContent(".proposal .origin");
  if (!/fixture/.test(label) || !/no handwriting recognition/i.test(label)) {
    throw new Error("the label must name the adapter and say it is a stand-in: " + label);
  }
});

await step("details open in place, show provenance, push neighbours locally and save nothing", async () => {
  const reading = page.locator(".note.item-provisional");
  const before = await reading.getAttribute("data-revision");
  const toggle = reading.getByRole("button", { name: "Show details" });
  await toggle.click();
  const opened = page.locator(".note.item-provisional").getByRole("button", { name: "Hide details" });
  await opened.waitFor({ timeout: 3000 });
  if (await opened.getAttribute("aria-expanded") !== "true") throw new Error("aria-expanded not true");
  const facts = await page.locator(".note.item-provisional .facts").textContent();
  if (!/Stand-in reading/.test(facts) || !/Confidence\s*Not measured/.test(facts)) throw new Error("provenance missing: " + facts);
  await page.waitForSelector(".note.item-provisional .crop img", { timeout: 8000 });
  await shot("details-open");
  await page.waitForTimeout(1300);   // one poll: nothing was saved
  if (await page.locator(".note.item-provisional").getAttribute("data-revision") !== before) throw new Error("opening details changed a saved position");
  await opened.click();
  await page.locator(".note.item-provisional").getByRole("button", { name: "Show details" }).waitFor({ timeout: 3000 });
  if (await page.$$eval(".note", ns => ns.some(n => n.style.transform))) throw new Error("a display offset outlived the open note");
  await page.click(".proposal .btn-quiet");   // reject the stand-in reading
  await queue(0);
});

await step("two accepted notes can be proposed as a group, drawn dashed until accepted", async () => {
  await page.fill("#note-text", "Too many fields before value");
  await page.click("#add-note");
  await queue(1);
  await rail("review");
  await page.click(".proposal .btn-primary");
  await queue(0);
  await page.waitForFunction(() => document.querySelectorAll(".note.item-accepted").length === 2, null, { timeout: 8000 });
  await page.click("#zoom-fit");
  await note("step two").click();
  await note("Too many fields").click({ modifiers: ["Shift"] });
  await page.waitForSelector("#selection:not([hidden])", { timeout: 3000 });
  await page.fill("#group-label", "Onboarding");
  await page.click("#propose-group");
  await page.waitForSelector(".hull.hull-provisional", { timeout: 8000 });
  await shot("group-proposed");
  await queue(1);
  await rail("review");
  await page.click(".proposal .btn-primary");
  await queue(0);
  await page.waitForSelector(".hull:not(.hull-provisional)", { timeout: 8000 });
  const label = await page.textContent(".hull .hull-label");
  if (!/Onboarding/.test(label)) throw new Error("group label: " + label);
});

await step("a drag moves the note and the server agrees, at any zoom", async () => {
  await page.click("#zoom-out");
  const zoom = await page.textContent("#zoom-level");
  const target = note("step two");
  const before = await box(target);
  if (!before) throw new Error("no box before the drag: " + JSON.stringify(await page.$$eval(".note", ns => ns.map(n => [n.textContent.slice(0, 30), n.offsetWidth, getComputedStyle(n).display]))));
  await page.mouse.move(before.x + 30, before.y + 14);
  await page.mouse.down();
  await page.mouse.move(before.x + 330, before.y + 200, { steps: 12 });
  // The note follows the pointer while the button is down.
  const during = await box(note("step two"));
  if (Math.abs(during.x - before.x) < 150) throw new Error(`the note did not follow the pointer: ${before.x} to ${during.x}`);
  await page.mouse.up();
  // From the drop until the server's answer the note stays put: the reply is
  // not in the snapshot yet, and the old client drew the note back at its
  // old place for a poll, then jumped it forward (seen on 19 October).
  for (let i = 0; i < 12; i++) {
    await page.waitForTimeout(150);
    const now = await box(note("step two"));
    if (Math.abs(now.x - during.x) > 2 || Math.abs(now.y - during.y) > 2) throw new Error(`the note moved after the drop (${i * 150}ms): ${during.x},${during.y} to ${now.x},${now.y}`);
  }
  const after = await box(note("step two"));   // past one poll, so this is the server's answer
  if (Math.abs(after.x - before.x) < 150) throw new Error(`the move did not stick at ${zoom}: ${before.x} to ${after.x}`);
  // Dragged well outside the group, so it left the group without review.
  const member = await page.locator(".hull").count();
  if (member) {
    const hull = await box(page.locator(".hull"));
    if (after.x >= hull.x && after.x + after.width <= hull.x + hull.width && after.y >= hull.y && after.y <= hull.y + hull.height) {
      throw new Error("the note was dragged out but is still inside the hull");
    }
  }
});

await step("panning and zooming change only this screen", async () => {
  const transform = () => page.$eval(".world", w => w.style.transform);
  const t0 = await transform();
  const board = await box(page.locator("#board"));
  await page.mouse.move(board.x + board.width - 20, board.y + board.height - 20);
  await page.mouse.down();
  await page.mouse.move(board.x + board.width - 120, board.y + board.height - 80, { steps: 5 });
  await page.mouse.up();
  await page.click("#zoom-in");
  if (await transform() === t0) throw new Error("pan and zoom did nothing");
});

await step("the list view holds the same notes and the group", async () => {
  await page.click('[data-view="list"]');
  const text = await page.textContent("#list-view");
  if (!/Group · Onboarding/.test(text) || !/Too many fields/.test(text) || !/step two/.test(text)) throw new Error("list: " + text.slice(0, 160));
  await page.click('[data-view="canvas"]');
});

await step("a facilitator adds and accepts a note in one step, and the record says who accepted it", async () => {
  // Two commands, source.text then proposal.review, behind one press. Its
  // failure paths are in canvas-objects-unit.mjs; this is the real server.
  if (!(await page.isVisible("#add-accept"))) throw new Error("a facilitator is not offered Add and accept");
  await page.fill("#note-text", "Nobody reads the tooltip");
  await page.click("#add-accept");
  await page.waitForFunction(() => /Added and accepted/.test(document.getElementById("attention-text").textContent), null, { timeout: 8000 });
  // The server's answer arrives with the next read; the note is never drawn
  // as a proposal in between (app.mjs holds the read until both commands land).
  const added = page.locator(".note.item-accepted", { hasText: "tooltip" });
  await added.waitFor({ timeout: 5000 });
  if (await page.locator(".note.item-pending", { hasText: "tooltip" }).count()) throw new Error("the note is drawn as a proposal beside the accepted one");
  if (!/Accepted by Facilitator/.test(await added.textContent())) throw new Error("the note does not say who accepted it");
  if (await page.textContent("#queue-count") !== "0") throw new Error("the note is still waiting for review");
  if (await page.inputValue("#note-text") !== "") throw new Error("the field still holds the note, so a second press would add it twice");
});

await step("listening writes transcript segments, labelled as a stand-in", async () => {
  await page.click("#listen");
  await page.waitForSelector("#listen-status:not([hidden])", { timeout: 5000 });
  // The fake device plays a tone; the chunker cuts at silence or after 12 s.
  await page.waitForSelector("#transcript .jv-row", { timeout: 20000 });
  const note = await page.textContent("#transcript-note");
  if (!/Stand-in transcript/.test(note)) throw new Error("transcript must say it is a stand-in: " + note);
  await shot("workspace");
  await page.click("#listen");
  await page.waitForSelector("#listen-status[hidden]", { state: "attached", timeout: 5000 });
});

await step("an invitation is one string carrying session, version and credential", async () => {
  await rail("people");
  await page.click("#make-invite");
  await page.waitForSelector("#invite-created:not([hidden])", { timeout: 5000 });
  const code = await page.textContent("#invite-created");
  if (!/[0-9a-f]{32}\.\d+\.[A-Za-z0-9_-]{32,}/.test(code)) throw new Error("join code shape: " + code);
});

await step("export downloads both formats with the session's credential", async () => {
  await page.click("#session-menu-button");
  await page.click("#open-export");
  await page.waitForSelector("#screen-export:not([hidden])", { timeout: 5000 });
  await page.click("#do-export");
  await page.waitForSelector("#export-out a", { timeout: 8000 });
  const files = await page.$$eval("#export-out a", links => Promise.all(links.map(a => fetch(a.href).then(r => r.text()))));
  if (files.length !== 2) throw new Error("expected json and markdown, got " + files.length);
  if (!files.every(f => /step two|Too many fields/.test(f))) throw new Error("an export is missing the accepted notes");
  await page.click("#close-export");
});

await step("a facilitator's open screen keeps capture running", async () => {
  // Capture's lease runs out five minutes after the last heartbeat. Before this
  // the client sent none, so every session paused itself after five minutes.
  for (let i = 0; i < 80 && !heartbeats.length; i++) await page.waitForTimeout(500);
  if (!heartbeats.length) throw new Error("no session.heartbeat was sent after capture started");
  if (await page.isVisible("#keepalive-banner")) throw new Error("the keep-alive prompt shows while heartbeats run");
  if (await page.textContent("#state-word") !== "Session open") throw new Error("capture is no longer running");
});

await step("stop capture pauses the room and says so", async () => {
  await page.click("#stop-capture");
  await page.waitForFunction(() => document.getElementById("state-word").textContent === "Paused", { timeout: 8000 });
  await page.waitForSelector("#paused-banner:not([hidden])", { timeout: 5000 });
});

await step("the phone width does not scroll sideways", async () => {
  await page.setViewportSize({ width: 400, height: 860 });
  await page.waitForTimeout(400);
  if (await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)) {
    throw new Error("horizontal overflow at 400px");
  }
  await shot("phone");
});

await step("no console errors and no failed requests in the whole journey", async () => {
  if (consoleErrors.length) throw new Error("console: " + consoleErrors.join(" | "));
  if (failedRequests.length) throw new Error("failed: " + failedRequests.join(" | "));
});

await browser.close();
await stopAll();
console.log(failures ? `\n${failures} step(s) failed` : "\nclient journey passed");
process.exit(failures ? 1 : 0);
