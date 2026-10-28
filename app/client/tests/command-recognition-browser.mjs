import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createRequire } from "node:module";
import { mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");
const client = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const output = resolve(client, "../../.local/command-ui");
mkdirSync(output, { recursive: true });
const port = 5188;
const server = spawn(process.env.JARVAIDS_TEST_PYTHON || "python3",
  ["serve.py", "--port", String(port)], { cwd: client, stdio: "ignore" });
server.on("error", error => { throw error; });
let browser;
try {
  for (let attempt = 0; ; attempt++) {
    try { const r = await fetch(`http://127.0.0.1:${port}/client/`); await r.arrayBuffer(); if (r.ok) break; } catch {}
    if (attempt >= 80) throw new Error("Static server did not start.");
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  browser = await chromium.launch({ headless: true,
    ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}) });
  const intents = ["summary", "visualisation", "comparison", "voting", "suggestions", "todo", "requirements", "planning"];
  for (const width of [1440, 400]) {
    const page = await browser.newPage({ viewport: { width, height: 1000 } });
    const errors = [], failedRequests = [];
    page.on("pageerror", error => errors.push(error.message));
    page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
    page.on("requestfailed", request => failedRequests.push(request.url()));
    page.on("response", response => { if (response.status() >= 400) failedRequests.push(response.url()); });
    await page.goto(`http://127.0.0.1:${port}/client/`);
    await page.evaluate(async intents => {
      const { renderTranscript } = await import("/client/transcript.mjs");
      window.renderTranscriptForTest = renderTranscript;
      document.getElementById("screen-setup").hidden = true;
      document.getElementById("screen-workspace").hidden = false;
      document.querySelector('[data-rail="transcript"]').click();
      const records = [];
      const add = (text, voice_command, synthetic = false, status = "final") => records.push({
        id: `test_${records.length}`, kind: "transcript_segment",
        data: { text, voice_command, status, created_at: 1700000000 + records.length,
          speaker_actor_id: "test_speaker", provenance: { synthetic } } });
      add("An ordinary conversation, with <img src=x onerror=alert(1)> shown as text.");
      for (const intent of intents) add(`Hey Jarvaids, request ${intent}.`, { status: "recognised", intent });
      add("Hey Jarvaids, make a...", { status: "incomplete", command: "make a" });
      add("Hey Jarvaids, delete everything.", { status: "unsupported", command: "delete everything" });
      add("Hey Jarvan's", { status: "incomplete", command: "" });
      records.at(-1).data.activation_correction = {
        text: "Hey Jarvaids", original_phrase: "Hey Jarvan's", corrected: true };
      add("FIXTURE ONLY", { status: "recognised", intent: "summary" }, true);
      add(null, null, false, "gap");
      renderTranscript({ records, members: [{ id: "test_speaker", name: "Test speaker" }] });
    }, intents);
    assert.equal(await page.locator(".command-provisional").count(), 8);
    assert.equal(await page.locator(".transcript-row").count(), 13);
    assert.equal(await page.locator("#transcript img").count(), 0);
    assert.match(await page.locator("#command-status").innerText(), /Hey Jarvaids recognised/);
    const corrected = page.locator(".transcript-row").filter({ has: page.locator(".activation-correction") });
    assert.equal(await corrected.locator(".transcript-words").innerText(), "Hey Jarvaids");
    await corrected.locator("summary").click();
    assert.match(await corrected.locator(".activation-correction").innerText(), /Whisper originally heard: Hey Jarvan's/);
    assert.match(await page.locator("#transcript").innerText(), /agenda or schedule requested/);
    assert.match(await page.locator("#transcript").innerText(), /Request unfinished/);
    assert.match(await page.locator("#transcript").innerText(), /Generation is not connected yet/);
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), "No horizontal overflow.");
    await page.screenshot({ path: resolve(output, `commands-${width}.png`), fullPage: true });
    await page.evaluate(() => {
      const common = { status: "final", capture_id: "run", capture_revision: 1,
        attribution: "voice_identified", speaker_actor_id: "speaker", speaker_profile_id: "voice",
        speaker_name: "Luuk", duration_ms: 2000, provenance: { synthetic: false } };
      window.renderTranscriptForTest({ members: [], records: [
        { id: "a", kind: "transcript_segment", data: { ...common, text: "Hey Jarf Aids", created_at: 1,
          captured_at_ms: 1000, activation_correction: { corrected: true, text: "Hey Jarvaids" } } },
        { id: "b", kind: "transcript_segment", data: { ...common, text: "make a voting list.", created_at: 2,
          captured_at_ms: 3000, voice_command: { status: "recognised", intent: "voting" } } },
      ] });
    });
    assert.equal(await page.locator(".transcript-row").count(), 1);
    assert.equal(await page.locator(".transcript-words").innerText(), "Hey Jarvaids make a voting list.");
    assert.match(await page.locator("#command-status").innerText(), /voting list/);
    await page.screenshot({ path: resolve(output, `sentences-${width}.png`), fullPage: true });
    await page.evaluate(() => window.renderTranscriptForTest({ records: [], members: [] }));
    assert.equal(await page.locator(".transcript-row").count(), 0);
    assert(await page.locator("#command-status").isHidden());
    assert.deepEqual(errors, []);
    assert.deepEqual(failedRequests, []);
    await page.close();
    console.log(`PASS: command types, incomplete/unsupported feedback, fixture exclusion, text safety and silence at ${width}px.`);
  }
} finally {
  await browser?.close();
  server.kill();
}
