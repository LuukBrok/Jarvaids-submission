/** Real HTTP, persistence and canvas; explicitly scripted speech/voice/AI replies. */
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
const data = mkdtempSync(join(tmpdir(), "jv-doc-browser-"));
const output = resolve(root, ".local/document-ui"); mkdirSync(output, { recursive: true });
const staticPort = 5198, apiPort = 3098, children = [];
let browser;
function launch(args, cwd) {
  const child = spawn(python, args, { cwd, stdio: ["ignore", "pipe", "pipe"] });
  child.on("error", error => { throw error; });
  child.stderr.on("data", d => { if (process.env.VERBOSE) console.error(String(d)); }); children.push(child);
}
async function ready(url) {
  for (let i = 0; i < 100; i++) {
    try { const readyResponse = await fetch(url); await readyResponse.arrayBuffer(); if (readyResponse.ok) return; } catch {}
    await new Promise(r => setTimeout(r, 100));
  } throw new Error(`Server did not start: ${url}`);
}
function pcm(marker) { const bytes = Buffer.alloc(32000); for (let i = 0; i < bytes.length; i += 2) bytes.writeInt16LE(marker, i); return bytes.toString("base64"); }
try {
  launch(["serve.py", "--port", String(staticPort)], resolve(root, "app/client"));
  launch(["-m", "tests.document_browser_server", "--port", String(apiPort), "--data-dir", data,
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
    await page.waitForFunction(() => document.getElementById('consent-text').textContent.includes('whole meeting so far'));
    assert.match(await page.locator("#consent-text").innerText(), /whole meeting so far/);
    await page.locator("#agree-check").check(); await page.locator("#acknowledge").click(); await page.locator("#activate").click(); await page.waitForFunction(() => !document.getElementById("stop-capture").disabled);
    await page.waitForFunction(() => !document.getElementById('stop-capture').disabled);
    const client = new GenAIClient({ baseUrl: `http://127.0.0.1:${apiPort}`, sessionId: credentials.session_id, token: credentials.owner_token });
    const cmd = (op, payload) => client.submit(client.intent(op, payload));
    for (const [marker, name] of [[100, "Julie"], [200, "Pieter"]])
      await cmd("speaker.enroll", { name, mime: "audio/pcm16", base64: pcm(marker), ended_reason: "silence" });
    let stamp = 0;
    const say = async marker => {
      stamp += marker === 102 ? 200000 : 2000;
      const intent = client.intent("source.audio", { mime: "audio/pcm16", base64: pcm(marker), ended_reason: "silence",
        capture_id: "document_room_capture", captured_at_ms: stamp });
      const result = await client.submit(intent);
      if (marker === 102) assert.equal((await client.submit(intent)).replayed, true);
      return result;
    };
    await say(101);
    assert.equal((await client.snapshot()).records.filter(r => r.kind === "command_document").length, 0);
    await say(102);
    let doc = page.locator("#board .command-document").first();
    // A task row: the done mark and text, then an owner chip and a date chip.
    const taskRow = (scope, text) => scope.locator(".document-task").filter({ has: page.locator(".document-task-text").getByText(text, { exact: true }) });
    const chips = async (scope, text) => {
      const row = taskRow(scope, text);
      return { owner: await row.locator(".owner-chip").innerText(), date: await row.locator(".date-chip").getAttribute("title"),
        tone: await row.locator(".date-chip").getAttribute("data-tone"), done: await row.getAttribute("data-done") };
    };
    await page.waitForFunction(() => document.querySelectorAll('#board .document-task').length === 1);
    assert.match(await doc.innerText(), /Interview students/);
    assert.match(await doc.innerText(), /Suggested task/);
    await say(103); await say(204);
    await page.waitForFunction(() => document.querySelectorAll('#board .document-task').length === 3);
    const questions = await chips(doc, "Prepare the interview questions");
    assert.equal(questions.owner, "Julie"); assert.match(questions.date, /^Deadline Friday \d+ \w+ \d{4}/);
    const recruit = await chips(doc, "Recruit participants");
    assert.equal(recruit.owner, "Pieter"); assert.match(recruit.date, /^Deadline Thursday /);
    assert.equal(await taskRow(doc, "Interview students").locator(".date-chip").innerText(), "No deadline");
    assert.equal(await taskRow(doc, "Interview students").locator(".owner-chip").innerText(), "Unassigned");
    assert.match(await taskRow(doc, "Recruit participants").locator(".date-chip").innerText(), /^(Overdue · |Today|\w{3} \d+ \w{3})/);
    await say(105); await say(106);
    await page.waitForFunction(() => document.querySelector('#board .command-document')?.textContent.includes('1 of 3 tasks complete'));
    const finished = await chips(doc, "Prepare the interview questions");
    assert.match(finished.date, /^Deadline Monday .*done$/);
    assert.deepEqual([finished.tone, finished.done], ["plain", "true"]);
    assert.equal(await taskRow(doc, "Prepare the interview questions").locator(".document-task-text").evaluate(el => getComputedStyle(el).textDecorationLine), "line-through");
    await taskRow(doc, "Prepare the interview questions").getByText("Task evidence", { exact: true }).click();
    await taskRow(doc, "Prepare the interview questions").getByText("Deadline as said: “Monday”", { exact: true }).waitFor();
    await say(999);
    await doc.getByText("Who will contact the museum?", { exact: true }).first().waitFor();
    await say(108);
    await page.waitForFunction(() => !document.querySelector('#board .command-document')?.textContent.includes('Reply needs clarification'));
    assert.equal(await doc.locator(".document-task").count(), 4);

    // Unsaved fields, focus and caret survive an unrelated transcript/sync update.
    const first = doc.locator(".document-task").first();
    await first.getByText("Edit task", { exact: true }).click();
    const task = first.getByLabel("Task", { exact: true }); await task.fill("Interview more students");
    await task.evaluate(el => el.setSelectionRange(5, 5)); await say(113);
    await page.waitForFunction(() => document.querySelector('#board .command-document .document-coverage')?.textContent.includes('9 of 9'));
    assert.equal(await task.inputValue(), "Interview more students");
    assert(await task.evaluate(el => document.activeElement === el && el.selectionStart === 5));
    await say(116);
    await page.waitForFunction(() => document.querySelector('#board .command-document .document-coverage')?.textContent.includes('10 of 10'));
    assert.equal(await task.inputValue(), "Interview more students");
    assert.equal(await first.getByLabel("Deadline", { exact: true }).inputValue(), "Tuesday");
    await first.getByRole("button", { name: "Save task", exact: true }).click();
    await page.waitForFunction(() => document.querySelector('#board .document-task-text')?.textContent === 'Interview more students');
    await doc.getByText("Tasks, evidence and controls", { exact: true }).click();
    await page.locator("#zoom-fit").click();
    const headingBox = await doc.locator(".kind").boundingBox(); assert(headingBox);
    await page.mouse.move(headingBox.x + 10, headingBox.y + 5); await page.mouse.down();
    await page.mouse.move(headingBox.x + 35, headingBox.y + 25, { steps: 5 }); await page.mouse.up();
    for (let attempt = 0; ; attempt++) {
      const moved = (await client.snapshot()).records.find(r => r.kind === "command_document");
      if (moved.position?.hand_placed) break;
      if (attempt === 50) throw new Error("Task list drag was not persisted");
      await new Promise(r => setTimeout(r, 100));
    }
    await page.waitForFunction(() => Number(document.querySelector('#board .command-document')?.dataset.revision) > 0);
    await page.screenshot({ path: resolve(output, `canvas-${width}.png`), fullPage: true });
    await doc.getByText("Tasks, evidence and controls", { exact: true }).click();
    await page.locator('[data-view="list"]').click();
    const listDoc = page.locator("#list-view .command-document");
    assert.match(await listDoc.innerText(), /Interview more students/);
    assert.match(await listDoc.locator(".document-task").first().locator(".date-chip").getAttribute("title"), /^Deadline Tuesday /);
    assert.equal(await listDoc.locator(".document-task").count(), 4);
    await listDoc.getByText("Edit list title", { exact: true }).click();
    await listDoc.getByLabel("List title", { exact: true }).fill("Research tasks");
    await listDoc.getByRole("button", { name: "Save title", exact: true }).click();
    await listDoc.getByRole("heading", { name: "Research tasks" }).waitFor();
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.screenshot({ path: resolve(output, `collecting-${width}.png`), fullPage: true });
    await say(109);
    await listDoc.getByRole("button", { name: "Accept to-do list", exact: true }).waitFor();
    await say(110); await listDoc.getByText("Accepted list", { exact: true }).waitFor();
    await say(113);
    const snapshot = await client.snapshot();
    const saved = snapshot.records.find(r => r.kind === "command_document");
    assert.equal(saved.data.state, "accepted"); assert.equal(saved.data.entry_ids.length, 4);
    const reconnected = new GenAIClient({ baseUrl: `http://127.0.0.1:${apiPort}`, sessionId: credentials.session_id, token: credentials.owner_token });
    assert.deepEqual((await reconnected.snapshot()).records.find(r => r.id === saved.id).data, saved.data);
    await page.screenshot({ path: resolve(output, `accepted-${width}.png`), fullPage: true });
    await say(111); await listDoc.getByText("Collecting tasks", { exact: true }).waitFor();
    await listDoc.getByText("Previously accepted version", { exact: true }).waitFor();
    await say(112); await listDoc.getByText("Cancelled list", { exact: true }).waitFor();
    assert.deepEqual(errors, []); assert.deepEqual(failures, []);
    console.log(`PASS ${width}px: history, addressed command/replay, named tasks/dates, correction/completion, unknown clarification, manual edit/focus, List view, voice close/accept/reopen/cancel and reconnect.`);
    await page.close();
  }
} finally {
  await browser?.close(); for (const child of children) child.kill();
  await Promise.all(children.map(c => new Promise(r => c.exitCode !== null ? r() : c.once("exit", r))));
  const target = resolve(data); assert(target.startsWith(resolve(tmpdir()) + "/") || target.startsWith(resolve(tmpdir()) + "\\"));
  rmSync(target, { recursive: true, force: true });
}
