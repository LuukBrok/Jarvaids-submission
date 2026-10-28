import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createRequire } from "node:module";
import { mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
const { chromium } = createRequire(import.meta.url)("playwright");
const client = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const root = resolve(client, "../..");
const data = resolve(root, ".local/speaker-browser-test", String(Date.now()));
mkdirSync(data, { recursive: true });
const python = process.env.JARVAIDS_TEST_PYTHON || "python3";
const children = [
  spawn(python, ["-m", "genai_server", "--port", "3095", "--data-dir", data,
    "--allow-origin", "http://127.0.0.1:5189"], { cwd: resolve(client, "../server"), stdio: "ignore" }),
  spawn(python, ["serve.py", "--port", "5189"], { cwd: client, stdio: "ignore" }),
];
let browser;
try {
  for (const url of ["http://127.0.0.1:3095/ready", "http://127.0.0.1:5189/client/"]) {
    for (let attempt = 0; ; attempt++) {
      try { const r = await fetch(url); await r.arrayBuffer(); if (r.ok) break; } catch {}
      if (attempt >= 100) throw new Error(`Server not ready: ${url}`);
      await new Promise(resolve => setTimeout(resolve, 100));
    }
  }
  browser = await chromium.launch({ headless: true, args: ["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"],
    ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}) });
  for (const width of [1440, 400]) {
    const page = await browser.newPage({ viewport: { width, height: 1000 } });
    const errors = [], failed = [];
    page.on("pageerror", error => errors.push(error.message));
    page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
    page.on("requestfailed", request => failed.push(request.url()));
    page.on("response", response => { if (response.status() >= 400) failed.push(response.url()); });
    await page.goto("http://127.0.0.1:5189/client/");
    await page.locator(".advanced summary").click();
    await page.locator("#base-url").fill("http://127.0.0.1:3095");
    await page.locator("#create").click();
    await page.locator("#agree-check").check();
    await page.locator("#acknowledge").click();
    await page.locator("#activate").click();
    await page.locator('[data-rail="people"]').click();
    await page.locator("#speaker-name").fill("Synthetic test speaker");
    await page.locator("#speaker-enrol").click();
    await page.waitForFunction(() => document.getElementById("speaker-list").textContent.includes("Synthetic test speaker"));
    assert.match(await page.locator("#speaker-list").innerText(), /Test profile/);
    await page.locator("#speaker-name").fill("Cancelled sample");
    await page.locator("#speaker-enrol").click();
    await page.locator("#speaker-cancel").click();
    await page.waitForFunction(() => document.getElementById("speaker-status").textContent === "Recording cancelled.");
    assert.doesNotMatch(await page.locator("#speaker-list").innerText(), /Cancelled sample/);
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.screenshot({ path: resolve(data, `speakers-${width}.png`), fullPage: true });
    await page.locator('[data-rail="transcript"]').click();
    await page.evaluate(async () => {
      const { renderTranscript } = await import("/client/transcript.mjs");
      renderTranscript({ members: [], records: [
        { kind: "transcript_segment", data: { status: "final", text: "Matched speech.", created_at: 1,
          attribution: "voice_identified", speaker_name: "Synthetic test speaker", provenance: { synthetic: false } } },
        { kind: "transcript_segment", data: { status: "final", text: "Uncertain speech.", created_at: 2,
          attribution: "unidentified", provenance: { synthetic: false } } },
      ] });
    });
    assert.match(await page.locator("#transcript").innerText(), /Synthetic test speaker/);
    assert.match(await page.locator("#transcript").innerText(), /Unknown speaker/);
    assert.match(await page.locator("#transcript-note").innerText(), /Enrolled voices are matched automatically/);
    assert.deepEqual(errors, []); assert.deepEqual(failed, []);
    await page.close();
    console.log(`PASS: enrolment, cancellation, truthful speaker labels and responsive layout at ${width}px.`);
  }
} finally {
  await browser?.close();
  for (const child of children) child.kill();
}
