/** Real UI/HTTP/store; deliberately scripted providers, no OCR quality claim. */
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createRequire } from "node:module";
import { mkdtempSync, mkdirSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { resolve, dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { GenAIClient } from "../../server/client.mjs";
const { chromium } = createRequire(import.meta.url)("playwright");
const root = resolve(dirname(fileURLToPath(import.meta.url)), "../../..");
const python = process.env.JARVAIDS_TEST_PYTHON || "python3";
const data = mkdtempSync(join(tmpdir(), "jv-auto-")), children = [];
const output = resolve(root, ".local/automatic-ui"); mkdirSync(output, { recursive: true });
const staticPort = 5195, apiPort = 3095;
let browser;
function launch(args, cwd) {
  const child = spawn(python, args, { cwd, stdio: ["ignore", "pipe", "pipe"] });
  child.on("error", e => { throw e; });
  child.stderr.on("data", d => { if (process.env.VERBOSE) console.error(String(d)); }); children.push(child);
}
async function ready(url) {
  for (let i = 0; i < 100; i++) {
    try { const response = await fetch(url); await response.arrayBuffer(); if (response.ok) return; } catch {}
    await new Promise(r => setTimeout(r, 100));
  } throw new Error(`Server did not start: ${url}`);
}
function pcm(marker) {
  const b = Buffer.alloc(32000); for (let i = 0; i < b.length; i += 2) b.writeInt16LE(marker, i);
  return b.toString("base64");
}
try {
  launch(["serve.py", "--port", String(staticPort)], resolve(root, "app/client"));
  launch(["-m", "tests.automatic_browser_server", "--port", String(apiPort), "--data-dir", data,
    "--origin", `http://127.0.0.1:${staticPort}`], resolve(root, "app/server"));
  await ready(`http://127.0.0.1:${staticPort}/client/`); await ready(`http://127.0.0.1:${apiPort}/health`);
  browser = await chromium.launch({ headless: true, ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}) });
  for (const width of [1440, 400]) {
    const page = await browser.newPage({ viewport: { width, height: 1100 } });
    const errors = [], failures = [];
    page.on("pageerror", e => errors.push(e.message));
    page.on("console", m => { if (m.type() === "error") errors.push(m.text()); });
    page.on("requestfailed", r => failures.push(r.url()));
    page.on("response", r => { if (r.status() >= 400) failures.push(`${r.status()} ${r.url()}`); });
    let credentials;
    page.on("request", r => { if (r.url() === `http://127.0.0.1:${apiPort}/api/sessions` && r.method() === "POST") credentials = r.postDataJSON(); });
    await page.goto(`http://127.0.0.1:${staticPort}/client/`);
    await page.locator(".advanced summary").click();
    await page.locator("#base-url").fill(`http://127.0.0.1:${apiPort}`); await page.locator("#create").click();
    await page.getByText(/whole sanitised photograph/).waitFor();
    await page.locator("#agree-check").check(); await page.locator("#acknowledge").click(); await page.locator("#activate").click();
    await page.waitForFunction(() => !document.getElementById("stop-capture").disabled);
    assert.equal(await page.locator("#add-accept").isVisible(), false);
    const client = new GenAIClient({ baseUrl: `http://127.0.0.1:${apiPort}`, sessionId: credentials.session_id, token: credentials.owner_token });
    const cmd = (op, payload) => client.submit(client.intent(op, payload));
    await page.locator("#note-text").fill("A typed note, added immediately"); await page.locator("#add-note").click();
    await page.locator('#board .note').getByText("A typed note, added immediately", { exact: true }).waitFor();
    const png = await page.evaluate(() => { const c = document.createElement("canvas"); c.width = c.height = 64;
      const x = c.getContext("2d"); x.fillStyle = "yellow"; x.fillRect(0, 0, 64, 64); return c.toDataURL("image/png").split(",")[1]; });
    await page.locator("#open-photo").click();
    await page.locator("#photo").setInputFiles({ name: "synthetic-wall.png", mimeType: "image/png", buffer: Buffer.from(png, "base64") });
    await page.waitForFunction(() => document.getElementById("reading-text").textContent.includes("2 notes added"));
    assert.equal(await page.locator("#screen-photo").isVisible(), false);
    assert.equal(await page.locator("#found-review").isVisible(), false);
    assert.equal(await page.locator("#arrange").isVisible(), false, "Placement happens in the background");
    await page.locator("#reading-dismiss").click();
    let snapshot = await client.snapshot();
    const photoNotes = snapshot.records.filter(r => r.kind === "item" && r.data.region_id);
    assert.equal(photoNotes.length, 2); assert(photoNotes.every(r => r.data.automatic && !r.data.accepted_by));
    assert.equal(snapshot.records.filter(r => r.kind === "proposal" && r.data.status === "needs_review").length, 0);
    await page.locator("#zoom-fit").click();
    const note = page.locator(`#board .note[data-id="${photoNotes[0].id}"]`);
    await note.getByRole("button", { name: "Show details", exact: true }).click();
    await note.getByLabel("Note text", { exact: true }).fill("Corrected wall note");
    await note.getByRole("button", { name: "Save note", exact: true }).click();
    await note.getByText("Corrected wall note", { exact: true }).first().waitFor();
    await page.locator("#undo").click();
    await page.waitForFunction(id => !document.querySelector(`#board .note[data-id="${id}"]`), photoNotes[1].id);
    const removed = (await client.snapshot()).records.find(r => r.id === photoNotes[1].id);
    assert.equal(removed.data.status,"undone","Undo removes the latest automatic photo note");
    await cmd("item.undo",{item_id:removed.id,expected_revision:removed.revision,restore_revision:1});
    for (const [marker,name] of [[100,"Julie"],[300,"Luuk"]])
      await cmd("speaker.enroll", { name, mime: "audio/pcm16", base64: pcm(marker), ended_reason: "silence" });
    let stamp = 0;
    const say = marker => cmd("source.audio", { mime: "audio/pcm16", base64: pcm(marker), ended_reason: "silence",
      capture_id: "automatic_room_capture", captured_at_ms: stamp += 2000 });
    await say(101); await say(102);
    await page.waitForFunction(() => document.querySelector('#board .command-document .document-task-text')?.textContent === 'Interview students');
    await say(301); await say(302); await say(303);
    await page.getByText("Work offline", { exact: true }).first().waitFor();
    await say(143); await say(145);
    // The canvas card is the calendar's compact summary; its grid is the Calendar view.
    await page.locator('#board .calendar-summary').getByText("Prototype review", { exact: true }).first().waitFor();
    await say(318);
    await page.waitForFunction(() => [...document.querySelectorAll('#board .poll:not(.command-document) .kind')].some(el => el.textContent === 'Voting open'));
    await say(320); await say(321);
    await page.waitForFunction(() => [...document.querySelectorAll('#board .poll:not(.command-document) .kind')].some(el => el.textContent === 'Voting finished'));
    snapshot = await client.snapshot();
    assert.equal(snapshot.records.find(r => r.kind === "poll").data.state, "closed");
    assert.equal(Object.values(snapshot.records.find(r => r.kind === "poll").data.counts).reduce((a,b) => a+b,0),1);
    await page.screenshot({ path: resolve(output, `canvas-${width}.png`) });
    assert.equal(snapshot.records.filter(r => r.kind === "command_document").length, 3);
    const todoId = snapshot.records.find(r => r.kind === "command_document" && r.data.document_type === "todo").id;
    const todo = page.locator(`#board [data-id="${todoId}"]`);
    const before = await todo.evaluate(el => el.offsetHeight);
    for (let i = 0; i < 12; i++) {
      const doc = (await client.snapshot()).records.find(r => r.id === todoId);
      await cmd("document.entry.edit", { document_id: todoId, expected_revision: doc.revision, entry_id: "", removed: false,
        task: { text: `Additional task ${i + 1}: prepare a clear prototype for the next discussion`, owner: "Julie", deadline: "Friday", classification: "suggested", done: false } });
    }
    await page.waitForFunction(id => document.querySelector(`[data-id="${id}"] .document-entries`).querySelectorAll('.document-task').length >= 13, todoId);
    const geometry = await todo.evaluate(el => ({ height: el.offsetHeight, client: el.clientHeight, scroll: el.scrollHeight, overflow: getComputedStyle(el).overflowY }));
    assert(geometry.height > before + 500, "The note grows as tasks are added");
    assert.equal(geometry.overflow, "visible"); assert(geometry.scroll <= geometry.client + 2, "No internal note scrolling");
    assert.equal(await todo.getByText("Details and controls", { exact: true }).evaluate(el => el.parentElement.open), false);
    await page.locator('[data-view="list"]').click();
    await page.evaluate(() => window.scrollTo(0,0));
    await page.screenshot({ path: resolve(output, `viewport-${width}.png`) });
    await page.screenshot({ path: resolve(output, `automatic-${width}.png`), fullPage: true });
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    assert.deepEqual(errors, []); assert.deepEqual(failures, []);
    console.log(`PASS ${width}px: automatic photo/typed intake, editable notes, three collectors, poll auto-open/close, growing cards, no UI errors/overflow.`);
    await page.close();
  }
} finally {
  await browser?.close();
  for (const child of children) child.kill();
  await Promise.all(children.map(child => new Promise(done => child.exitCode !== null || child.signalCode !== null ? done() : child.once("exit", done))));
  if (!resolve(data).startsWith(resolve(tmpdir()) + "/") && !resolve(data).startsWith(resolve(tmpdir()) + "\\")) throw new Error("Unsafe cleanup path");
  rmSync(data, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 });
}
