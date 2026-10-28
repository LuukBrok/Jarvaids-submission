/** Test the actual Listen wiring with a fake microphone and detector replies. */
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createRequire } from "node:module";
import { mkdtempSync, mkdirSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const { chromium } = createRequire(import.meta.url)("playwright");
const client = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const output = resolve(client, "../../.local/wakeword-listen-ui");
mkdirSync(output, { recursive: true });
const data = mkdtempSync(join(tmpdir(), "jv-listen-"));
const python = process.env.JARVAIDS_TEST_PYTHON || "python3";
const children = [
  spawn(python, ["-m", "genai_server", "--port", "3097", "--data-dir", data,
    "--allow-origin", "http://127.0.0.1:5197"], { cwd: resolve(client, "../server"), stdio: "ignore" }),
  spawn(python, ["serve.py", "--port", "5197"], { cwd: client, stdio: "ignore" }),
];
let browser;
try {
  for (const url of ["http://127.0.0.1:3097/ready", "http://127.0.0.1:5197/client/"]) {
    for (let attempt = 0; ; attempt++) {
      try { const readyResponse = await fetch(url); await readyResponse.arrayBuffer(); if (readyResponse.ok) break; } catch {}
      if (attempt >= 100) throw new Error(`Server not ready: ${url}`);
      await new Promise(resolve => setTimeout(resolve, 100));
    }
  }
  browser = await chromium.launch({ headless: true,
    args: ["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"],
    ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}) });
  for (const width of [1440, 400]) {
    const page = await browser.newPage({ viewport: { width, height: 1000 } });
    const errors = [], failed = [];
    page.on("pageerror", error => errors.push(error.message));
    page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
    page.on("requestfailed", request => failed.push(request.url()));
    page.on("response", response => { if (response.status() >= 400) failed.push(response.url()); });
    await page.goto("http://127.0.0.1:5197/client/");
    await page.evaluate(async () => {
      const { GenAIClient } = await import("/server/client.mjs");
      for (const method of ["snapshot", "delta"]) {
        const original = GenAIClient.prototype[method];
        GenAIClient.prototype[method] = async function (...args) {
          const snapshot = await original.apply(this, args);
          if (snapshot.session) snapshot.session.wakeword_available = true;
          return snapshot;
        };
      }
      window.detectorTest = { starts: 0, stops: 0, unavailable: false };
      GenAIClient.prototype.wakewordStart = async function () {
        const test = window.detectorTest;
        test.starts++;
        if (test.unavailable) throw Object.assign(new Error("No custom model installed"), { code: "wakeword_unavailable" });
        return { stream_id: "test_detector", sample_rate: 16000, batch_samples: 5120, next_sequence: 0 };
      };
      GenAIClient.prototype.wakewordStop = async function () { window.detectorTest.stops++; };
      GenAIClient.prototype.wakewordBatch = async function (stream_id, sequence) {
        return { stream_id, sequence, detection: null };
      };
    });
    await page.locator(".advanced summary").click();
    await page.locator("#base-url").fill("http://127.0.0.1:3097");
    await page.locator("#create").click();
    await page.locator("#agree-check").check(); await page.locator("#acknowledge").click();
    await page.locator("#activate").click(); await page.waitForFunction(() => !document.getElementById("stop-capture").disabled);
    assert.equal(await page.locator("#wakeword-enabled").count(), 0);
    await page.locator("#listen").click();
    await page.waitForFunction(() => document.getElementById("listen").textContent === "Stop listening");
    assert.equal(await page.evaluate(() => window.detectorTest.starts), 1);
    assert.match(await page.locator("#wakeword-status").innerText(), /waiting/);
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.screenshot({ path: resolve(output, `listen-${width}.png`), fullPage: true });
    await page.locator("#listen").click();
    await page.waitForFunction(() => window.detectorTest.stops === 1);
    assert.match(await page.locator("#wakeword-status").innerText(), /off/);

    // A teammate without the local model can still listen and use transcript commands.
    await page.evaluate(() => { window.detectorTest.unavailable = true; });
    await page.locator("#listen").click();
    await page.waitForFunction(() => document.getElementById("listen").textContent === "Stop listening");
    assert.match(await page.locator("#wakeword-status").innerText(), /Transcript recognition still works/);
    await page.locator("#listen").click();

    // Refused microphone access must also release the detector stream.
    await page.evaluate(() => {
      window.detectorTest.unavailable = false;
      navigator.mediaDevices.getUserMedia = async () => { throw new DOMException("Denied in test", "NotAllowedError"); };
    });
    await page.locator("#listen").click();
    await page.waitForFunction(() => window.detectorTest.stops === 2);
    assert.equal(await page.locator("#listen").innerText(), "Listen");
    assert.match(await page.locator("#attention").innerText(), /not allowed to use the microphone/);
    assert.match(await page.locator("#wakeword-status").innerText(), /off/);
    assert.deepEqual(errors, []);
    assert.deepEqual(failed, []);
    await page.close();
    console.log(`PASS: automatic detector, stop, unavailable-model fallback and microphone refusal at ${width}px.`);
  }
} finally {
  await browser?.close();
  await Promise.all(children.map(child => new Promise(resolve => {
    if (child.exitCode !== null) return resolve();
    child.once("exit", resolve); child.kill();
  })));
  rmSync(data, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 });
}
