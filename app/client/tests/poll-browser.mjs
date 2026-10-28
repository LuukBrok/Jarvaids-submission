/** Real HTTP/browser journey with explicitly scripted speech and AI adapters. */
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createRequire } from "node:module";
import { mkdtempSync, mkdirSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { resolve, dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { GenAIClient } from "../../server/client.mjs";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");
const root = resolve(dirname(fileURLToPath(import.meta.url)), "../../..");
const python = process.env.JARVAIDS_TEST_PYTHON || "python3";
const data = mkdtempSync(join(tmpdir(), "jvp-browser-"));
const output = resolve(root, ".local/poll-ui"); mkdirSync(output, { recursive: true });
const staticPort = 5196, apiPort = 3096;
const children = [];
let browser;
function launch(args, cwd) {
  const child = spawn(python, args, { cwd, stdio: ["ignore", "pipe", "pipe"] });
  child.on("error", error => { throw error; });
  child.stderr.on("data", d => { if (process.env.VERBOSE) console.error(String(d)); });
  children.push(child);
}
async function ready(url) {
  for (let i = 0; i < 100; i++) {
    try { const readyResponse = await fetch(url); await readyResponse.arrayBuffer(); if (readyResponse.ok) return; } catch {}
    await new Promise(r => setTimeout(r, 100));
  }
  throw new Error(`Server did not start: ${url}`);
}
function pcm(marker) { const bytes = Buffer.alloc(32000); for (let i = 0; i < bytes.length; i += 2) bytes.writeInt16LE(marker, i); return bytes.toString("base64"); }
try {
  launch(["serve.py", "--port", String(staticPort)], resolve(root, "app/client"));
  launch(["-m", "tests.poll_browser_server", "--port", String(apiPort), "--data-dir", data,
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
    await page.locator("#base-url").fill(`http://127.0.0.1:${apiPort}`);
    await page.locator("#create").click(); await page.locator("#agree-check").check(); await page.locator("#acknowledge").click();
    await page.locator("#activate").click(); await page.waitForFunction(() => !document.getElementById("stop-capture").disabled); await page.locator("#screen-workspace").waitFor({ state: "visible" });
    const client = new GenAIClient({ baseUrl: `http://127.0.0.1:${apiPort}`, sessionId: credentials.session_id, token: credentials.owner_token });
    const cmd = (op, payload) => client.submit(client.intent(op, payload));
    for (const [marker, name] of [[100, "Julie"], [200, "Pieter"], [300, "Luuk"]])
      await cmd("speaker.enroll", { name, mime: "audio/pcm16", base64: pcm(marker), ended_reason: "silence" });
    let stamp = 0;
    const say = async marker => {
      const intent = client.intent("source.audio", { mime: "audio/pcm16", base64: pcm(marker), ended_reason: "silence",
        capture_id: "browser_room_capture", captured_at_ms: (stamp += 2000) });
      const result = await client.submit(intent);
      if (marker === 101) assert.equal((await client.submit(intent)).replayed, true);
      return result;
    };
    await say(101);
    const poll = page.locator("#board .poll").first();
    await poll.getByLabel("Question", { exact: true }).waitFor();
    await page.waitForFunction(() => document.querySelector('#board .poll textarea')?.value === 'What should we have for lunch?');
    await page.screenshot({ path: resolve(output, `draft-${width}.png`), fullPage: true });
    await say(102);
    await poll.getByText("Voting open", { exact: true }).waitFor();
    assert.match(await poll.innerText(), /0 voted · 3 not voted/);
    await say(103); await say(205); await say(104);
    await page.waitForFunction(() => document.querySelector('#board .poll .poll-turnout')?.textContent === '2 voted · 1 not voted');
    assert.match(await poll.locator(".poll-option").nth(0).innerText(), /Julie/);
    assert.match(await poll.locator(".poll-option").nth(2).innerText(), /Pieter/);
    // The tally reads as bars: the count and voters are written on each bar,
    // and two choices level at the top are a tie while voting is open.
    assert.equal(await poll.locator(".poll-option .poll-bar").count(), 3);
    assert.equal(await poll.locator(".poll-option").nth(0).locator(".poll-bar-words").innerText().then(t => t.replace(/\s+/g, " ")), "1 Julie");
    assert.equal(await poll.locator(".poll-option").nth(1).locator(".poll-bar-words").innerText().then(t => t.replace(/\s+/g, " ")), "0 No votes");
    assert.equal(await poll.locator(".poll-options").getAttribute("data-outcome"), "tie");
    assert.deepEqual(await poll.locator(".poll-mark").allInnerTexts(), ["Tie", "Tie"]);
    const shares = await poll.locator(".poll-bar").evaluateAll(bars => bars.map(bar =>
      Math.round(bar.querySelector(".poll-bar-fill").getBoundingClientRect().width / bar.getBoundingClientRect().width * 100)));
    assert.deepEqual(shares, [50, 0, 50]);
    assert.match(await poll.locator(".poll-option").nth(0).locator(".poll-bar").getAttribute("aria-label"), /1 of 2 votes, Julie, tie/);
    await say(999);
    await poll.getByText("Reply needs clarification", { exact: true }).waitFor();
    await poll.getByText("Reply needs clarification", { exact: true }).click();
    const review = poll.locator(".poll-clarification");
    const snap = await client.snapshot(); const luuk = snap.records.find(r => r.kind === "speaker_profile" && r.data.name === "Luuk");
    await review.getByLabel("Speaker for unclear reply").selectOption(luuk.id);
    await review.getByLabel("Choice for unclear reply").selectOption("option_02");
    await review.getByRole("button", { name: "Apply correction" }).click();
    await page.waitForFunction(() => document.querySelector('#board .poll .poll-turnout')?.textContent === '3 voted · 0 not voted');
    // Cards grow instead of scrolling internally. Pan the canvas to their controls.
    const reach = async target => {
      const board = await page.locator("#board").boundingBox(), box = await target.boundingBox();
      const bottom = board.y + board.height - 160;
      const delta = box.y + box.height > bottom ? box.y + box.height - bottom : box.y < board.y + 40 ? box.y - board.y - 40 : 0;
      if (delta) { await page.mouse.move(board.x + 20, board.y + 50); await page.mouse.wheel(0, delta); }
    };
    const close = poll.getByRole("button", { name: "Close voting" });
    await reach(close); await close.click();
    const accept = poll.getByRole("button", { name: "Accept results" });
    await reach(accept); await accept.click();
    await poll.getByText("Results accepted", { exact: true }).waitFor();
    assert.equal(await poll.locator(".poll-option .poll-bar").count(), 3);
    assert.deepEqual(await poll.locator(".poll-mark").allInnerTexts(), ["Tie", "Tie", "Tie"]);
    assert.equal(await poll.locator(".poll-option[data-mark=\"lead\"]").count(), 0);
    await page.locator("#zoom-fit").click();
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), "No horizontal body overflow");
    await page.screenshot({ path: resolve(output, `results-${width}.png`), fullPage: true });
    const persisted = await client.snapshot(); const result = persisted.records.find(r => r.kind === "poll");
    assert.deepEqual(result.data.counts, { option_01: 1, option_02: 1, option_03: 1 });
    assert.equal(persisted.records.filter(r => r.kind === "poll_ballot").length, 3);
    const reconnected = new GenAIClient({ baseUrl: `http://127.0.0.1:${apiPort}`, sessionId: credentials.session_id, token: credentials.owner_token });
    assert.deepEqual((await reconnected.snapshot()).records.find(r => r.id === result.id).data.counts, result.data.counts);
    await say(107);
    const binary = page.locator("#board .poll").last();
    await page.waitForFunction(() => [...document.querySelectorAll('#board .poll textarea')].some(e => e.value === 'Should we order lunch?'));
    const start = binary.getByRole("button", { name: "Start voting" });
    await reach(start); await start.click();
    await binary.getByText("Voting open", { exact: true }).waitFor();
    assert.match(await binary.innerText(), /Yes/); assert.match(await binary.innerText(), /No/);
    // One manual choice makes a single leader, marked "Leading" while voting is open.
    const manualChoice = binary.getByText("Record or correct a choice", { exact: true });
    await reach(manualChoice); await manualChoice.click();
    await binary.getByLabel("Speaker for manual choice").selectOption(luuk.id);
    await binary.getByLabel("Manual choice", { exact: true }).selectOption({ label: "Yes" });
    await binary.getByRole("button", { name: "Record choice" }).click();
    await binary.locator('.poll-option[data-mark="lead"]').waitFor();
    assert.deepEqual(await binary.locator(".poll-mark").allInnerTexts(), ["Leading"]);
    assert.equal(await binary.locator(".poll-options").getAttribute("data-outcome"), "lead");
    await page.screenshot({ path: resolve(output, `leading-${width}.png`), fullPage: true });
    assert.deepEqual(errors, []); assert.deepEqual(failures, []);
    console.log(`PASS ${width}px: real HTTP recognition -> draft -> voice confirmation -> votes/change -> unknown correction -> accepted tie; binary poll; no errors or overflow.`);
    await page.close();
  }
} catch (error) {
  const page = browser?.contexts().at(-1)?.pages().at(-1);
  if (page) {
    await page.screenshot({ path: resolve(output, "failure.png"), fullPage: true });
    console.log(await page.locator("#board .poll").first().evaluate(el => ({ rect: el.getBoundingClientRect().toJSON(),
      maxHeight: getComputedStyle(el).maxHeight, scrollHeight: el.scrollHeight, scrollTop: el.scrollTop,
      board: document.getElementById("board").getBoundingClientRect().toJSON(), dock: document.getElementById("dock").getBoundingClientRect().toJSON() })));
  }
  throw error;
} finally {
  await browser?.close();
  for (const c of children) c.kill();
  await Promise.all(children.map(c => new Promise(r => c.exitCode !== null ? r() : c.once("exit", r))));
  const target = resolve(data); assert(target.startsWith(resolve(tmpdir()) + "/") || target.startsWith(resolve(tmpdir()) + "\\"));
  rmSync(target, { recursive: true, force: true });
}
