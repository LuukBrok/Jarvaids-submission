/**
 * Retake the fallback screenshots from the real client.
 *
 * The fallback window is what the presenter switches to when the live demo
 * dies, so every image in it must be a capture of the client actually doing
 * the step, not a drawing of what it should look like. This script starts its
 * own backend and static server on ports the demo does not use, walks the five
 * runbook steps in a real browser, and writes one PNG per step at 1280x800.
 *
 *     node deliverables/week4-midpoint/demo/shots.mjs
 *
 * It needs Playwright and a Chromium, like app/client/tests/journey.mjs. If
 * either is missing it stops with a message rather than leaving stale images
 * in place, because a stale fallback is worse than none: it shows a screen
 * the client no longer has.
 */
import { spawn } from "node:child_process";
import { mkdtempSync, rmSync, mkdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "../../..");
const CLIENT = join(ROOT, "app/client");
const SERVER = join(ROOT, "app/server");
const OUT = join(HERE, "fallback");
const WALL = join(HERE, "wall.png");
const STATIC_PORT = 5178, API_PORT = 3078;

let chromium;
try {
  ({ chromium } = await import("playwright"));
} catch {
  console.error("shots.mjs: playwright is not installed; nothing was written.");
  process.exit(1);
}

const data = mkdtempSync(join(tmpdir(), "jarvaids-shots-"));
const children = [];
const part = (command, args, cwd) => {
  const child = spawn(command, args, { cwd, stdio: ["ignore", "ignore", "pipe"] });
  child.stderr.on("data", d => process.env.VERBOSE && console.error(String(d).trim()));
  children.push(child);
};
const stopAll = () => { for (const c of children) { try { c.kill("SIGTERM"); } catch {} } rmSync(data, { recursive: true, force: true }); };
process.on("exit", stopAll);

part("python3", ["serve.py", "--port", String(STATIC_PORT)], CLIENT);
part("python3", ["-m", "genai_server", "--port", String(API_PORT), "--data-dir", data,
  "--allow-origin", `http://127.0.0.1:${STATIC_PORT}`], SERVER);

const ready = async url => {
  for (let i = 0; i < 80; i++) {
    try { if ((await fetch(url)).ok) return; } catch {}
    await new Promise(r => setTimeout(r, 150));
  }
  throw new Error("never became ready: " + url);
};
await ready(`http://127.0.0.1:${STATIC_PORT}/client/index.html`);
await ready(`http://127.0.0.1:${API_PORT}/health`);

mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined });
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
const problems = [];
page.on("console", m => { if (m.type() === "error") problems.push(m.text().slice(0, 160)); });
page.on("pageerror", e => problems.push(String(e).slice(0, 160)));

const shot = async name => {
  await page.waitForTimeout(300);
  await page.screenshot({ path: join(OUT, name), fullPage: false });
  console.log("wrote fallback/" + name);
};
const nav = screen => page.click(`#nav button[data-screen="${screen}"]`);
const queueIs = n => page.waitForFunction(v => document.getElementById("queue-count").textContent === String(v), n, { timeout: 15000 });

await page.goto(`http://127.0.0.1:${STATIC_PORT}/client/`, { waitUntil: "networkidle" });
await page.fill("#base-url", `http://127.0.0.1:${API_PORT}`);
await page.click("#create");
await page.waitForSelector("#consent:not([hidden])", { timeout: 10000 });
await page.click("#acknowledge");
await page.waitForFunction(() => !document.getElementById("activate").disabled, { timeout: 8000 });
await page.click("#activate");
await page.waitForFunction(() => document.getElementById("state-word").textContent === "active", { timeout: 8000 });

// Step 1: a typed note goes to Review, not to the canvas.
await nav("capture");
await page.fill("#note-text", "Onboarding loses people at step three");
await page.click("#add-note");
await queueIs(1);
await nav("review");
await page.waitForSelector(".proposal", { timeout: 5000 });
await shot("01-typed-note.png");

// Step 2: the wall is photographed and three notes are marked.
await nav("capture");
await page.setInputFiles("#photo", WALL);
await page.waitForSelector("#photo-stage:not([hidden])", { timeout: 5000 });
await page.waitForFunction(() => document.getElementById("photo-preview").naturalWidth > 0, { timeout: 5000 });
const stageEl = await page.$(".stage");
await stageEl.scrollIntoViewIfNeeded();
const stage = await stageEl.boundingBox();
if (process.env.VERBOSE) console.error("stage", stage);
// The three top notes of wall.png, as fractions of the drawn image.
for (const [x0, y0, x1, y1] of [[.09, .15, .32, .53], [.35, .12, .58, .50], [.63, .17, .87, .55]]) {
  await page.mouse.move(stage.x + x0 * stage.width, stage.y + y0 * stage.height);
  await page.mouse.down();
  await page.mouse.move(stage.x + x1 * stage.width, stage.y + y1 * stage.height, { steps: 8 });
  await page.mouse.up();
}
await page.waitForFunction(() => document.getElementById("region-count").textContent === "3");
await shot("02-wall-marked.png");

// Step 3: the readings come back provisional, dashed, naming the adapter.
await page.click("#send-photo");
await page.waitForTimeout(2500);
if (process.env.VERBOSE) console.error("attention:", await page.textContent("#attention"), "| queue:", await page.textContent("#queue-count"));
await queueIs(4);
await nav("review");
await page.waitForFunction(() => document.querySelectorAll(".proposal.provisional").length === 3, { timeout: 15000 });
await shot("03-readings-provisional.png");

// Step 4: correct one, accept it, reject one; the typed note is accepted too.
const provisional = await page.$$(".proposal.provisional");
await (await provisional[0].$("textarea")).fill("Onboarding loses people at step 3");
await (await provisional[0].$(".btn-primary")).click();
await queueIs(3);
await (await (await page.$$(".proposal.provisional"))[0].$(".btn-quiet")).click();
await queueIs(2);
await (await (await page.$$(".proposal:not(.provisional)"))[0].$(".btn-primary")).click();
await queueIs(1);
await nav("canvas");
await page.waitForFunction(() => document.querySelectorAll(".item").length === 2, { timeout: 8000 });
await shot("04-accepted.png");

// Step 5: a drag. Moving is not agreeing, so nothing goes through review.
const item = await (await page.$$(".item"))[0].boundingBox();
await page.mouse.move(item.x + 30, item.y + 20);
await page.mouse.down();
await page.mouse.move(item.x + 420, item.y + 240, { steps: 12 });
await page.mouse.up();
await page.waitForTimeout(1800);
await shot("05-drag.png");

await browser.close();
stopAll();
if (problems.length) { console.error("browser problems:\n  " + problems.join("\n  ")); process.exit(1); }
console.log("five fallback screenshots retaken from the running client");
