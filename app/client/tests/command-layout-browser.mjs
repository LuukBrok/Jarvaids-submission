/** Real canvas rendering and pointer interactions with local synthetic records. */
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createRequire } from "node:module";
import { mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
const { chromium } = createRequire(import.meta.url)("playwright");
const client = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const output = resolve(client, "../../.local/command-layout-ui"); mkdirSync(output, { recursive: true });
const port = 5196;
const server = spawn(process.env.JARVAIDS_TEST_PYTHON || "python3", ["serve.py", "--port", String(port)], { cwd: client, stdio: "ignore" });
server.on("error", e => { throw e; });
let browser;
try {
  for (let attempt = 0; ; attempt++) {
    try { const response = await fetch(`http://127.0.0.1:${port}/client/`); await response.arrayBuffer(); if (response.ok) break; } catch {}
    if (attempt === 80) throw new Error("Static server did not start");
    await new Promise(r => setTimeout(r, 100));
  }
  browser = await chromium.launch({ headless: true, ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}) });
  for (const width of [1440, 400]) {
    const page = await browser.newPage({ viewport: { width, height: 1100 } });
    const errors = [], failures = [];
    page.on("pageerror", e => errors.push(e.message));
    page.on("console", m => { if (m.type() === "error") errors.push(m.text()); });
    page.on("requestfailed", r => failures.push(r.url()));
    page.on("response", r => { if (r.status() >= 400) failures.push(`${r.status()} ${r.url()}`); });
    await page.goto(`http://127.0.0.1:${port}/client/`);
    const initial = await page.evaluate(async () => {
      const { Board } = await import("/client/board.mjs");
      document.getElementById("screen-setup").hidden = true;
      document.getElementById("screen-workspace").hidden = false;
      const record = (id, kind, data) => ({ id, kind, revision: 1, data });
      const snapshot = { actor_id: "actor", session: { state: "active", command_ai: { available: false } },
        members: [{ id: "actor", role: "facilitator", name: "Test facilitator" }], records: [] };
      const taskIds = Array.from({ length: 12 }, (_, i) => `task-${i}`);
      snapshot.records.push(record("tasks", "command_document", { document_type: "todo", title: "To-do list", created_at: 1,
        state: "collecting", entry_ids: taskIds, uncovered: 0, focus_request: 1, prompt: "Synthetic layout example." }));
      for (const id of taskIds) snapshot.records.push(record(id, "command_entry", { text: `Prepare ${id}`, owner: "", deadline: "",
        classification: "suggested", done: false, source_refs: [], status: "provisional" }));
      snapshot.records.push(record("criteria", "command_document", { document_type: "requirements", title: "Requirements and wishes", created_at: 2,
        state: "collecting", entry_ids: [], uncovered: 0, focus_request: 1, prompt: "Synthetic layout example." }));
      window.layoutSnapshot = structuredClone(snapshot);
      window.layoutCommands = [];
      window.layoutBoard = new Board(document.getElementById("board"), {
        attention: () => {}, send: async (op, payload) => { window.layoutCommands.push({ op, payload }); },
        onZoom: z => { document.getElementById("zoom-level").textContent = `${Math.round(z * 100)}%`; },
      });
      window.layoutBoard.render(snapshot);
      // Add the poll after a user zoom, with much taller neighbouring task content.
      window.layoutBoard.zoomBy(1.1);
      document.getElementById("board").hidden = true;
      snapshot.records.push(record("poll", "poll", { state: "open", question: "What should we have for lunch?", created_at: 3,
        options: [{ id: "yes", label: "Sandwiches" }, { id: "no", label: "Salad" }], prompt: "Synthetic layout example." }));
      window.layoutSnapshot = snapshot; window.layoutBoard.render(snapshot);
      document.getElementById("board").hidden = false;
      window.layoutBoard.render(snapshot);
      const boxes = [...document.querySelectorAll('#board .note')].map(el => ({ id: el.dataset.id, x: el.offsetLeft, y: el.offsetTop,
        w: el.offsetWidth, h: el.offsetHeight }));
      return { boxes, zoom: window.layoutBoard.view.z };
    });
    const boxes = [...initial.boxes].sort((a, b) => a.x - b.x);
    assert.deepEqual(boxes.map(b => b.id), ["tasks", "criteria", "poll"]);
    assert(boxes.every(b => b.y === boxes[0].y), "Command headings share a row");
    assert(boxes.slice(1).every((b, i) => b.x > boxes[i].x + boxes[i].w), "Columns have a gap");
    assert(initial.zoom >= .8, "New poll keeps text readable despite a tall to-do list");
    const before = await page.evaluate(() => ({ ...window.layoutBoard.view }));
    await page.evaluate(() => window.layoutBoard.render(window.layoutSnapshot));
    assert.deepEqual(await page.evaluate(() => ({ ...window.layoutBoard.view })), before, "Live updates preserve pan and zoom");
    await page.screenshot({ path: resolve(output, `columns-${width}.png`), fullPage: true });

    // Panning reaches the other columns on phones without horizontal page overflow.
    await page.evaluate(() => window.layoutBoard.panBy(window.layoutBoard.view.z * 624, 0));
    await page.screenshot({ path: resolve(output, `tasks-${width}.png`), fullPage: true });
    // Keep a user placement exact, and put unplaced objects to its right.
    const placed = await page.evaluate(() => {
      const task = window.layoutSnapshot.records.find(r => r.id === "tasks");
      task.position = { x: 120, y: 80, revision: 1, hand_placed: true };
      window.layoutBoard.render(window.layoutSnapshot);
      return [...document.querySelectorAll('#board .note')].map(el => ({ id: el.dataset.id, x: el.offsetLeft, y: el.offsetTop, w: el.offsetWidth }));
    });
    assert.deepEqual(placed.find(b => b.id === "tasks"), { id: "tasks", x: 120, y: 80, w: boxes.find(b => b.id === "tasks").w });
    assert(placed.filter(b => b.id !== "tasks").every(b => b.x > 120 + boxes.find(b => b.id === "tasks").w));
    assert.deepEqual(await page.evaluate(() => window.layoutCommands), [], "Display layout never writes placements or acceptance");
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    assert.deepEqual(errors, []); assert.deepEqual(failures, []);
    console.log(`PASS ${width}px: three top-aligned columns, readable automatic zoom, stable view on sync, panning, exact hand placement, no writes/errors/overflow.`);
    await page.close();
  }
} finally {
  await browser?.close(); server.kill();
}
