/** Production HTTP/canvas with explicitly scripted speech and interpretation. */
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
const data = mkdtempSync(join(tmpdir(), "jv-req-browser-"));
const output = resolve(root, ".local/requirements-ui"); mkdirSync(output, { recursive: true });
const staticPort = 5199, apiPort = 3099, children = [];
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
  launch(["-m", "tests.requirements_browser_server", "--port", String(apiPort), "--data-dir", data,
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
    await page.waitForFunction(() => document.getElementById("consent-text").textContent.includes("requirements and wishes"));
    await page.locator("#agree-check").check(); await page.locator("#acknowledge").click(); await page.locator("#activate").click(); await page.waitForFunction(() => !document.getElementById("stop-capture").disabled);
    const client = new GenAIClient({ baseUrl: `http://127.0.0.1:${apiPort}`, sessionId: credentials.session_id, token: credentials.owner_token });
    const cmd = (op, payload) => client.submit(client.intent(op, payload));
    await cmd("speaker.enroll", { name: "Julie", mime: "audio/pcm16", base64: pcm(300), ended_reason: "silence" });
    let stamp = 0;
    const say = async marker => {
      stamp += marker === 303 ? 200000 : 2000;
      const intent = client.intent("source.audio", { mime: "audio/pcm16", base64: pcm(marker), ended_reason: "silence",
        capture_id: "requirements_room_capture", captured_at_ms: stamp });
      const result = await client.submit(intent);
      if (marker === 303) assert.equal((await client.submit(intent)).replayed, true);
      return result;
    };
    await say(301); await say(302);
    assert.equal((await client.snapshot()).records.filter(r => r.kind === "command_document").length, 0);
    await say(303);
    let doc = page.locator("#board .command-document").first();
    await doc.getByText("Work offline", { exact: true }).waitFor();
    await doc.getByText("Green case", { exact: true }).waitFor();
    assert.equal(await doc.locator('[data-category="requirement"] .document-task').count(), 1);
    assert.equal(await doc.locator('[data-category="wish"] .document-task').count(), 1);
    await say(304); await say(305);
    await doc.locator('[data-category="clarification"]').getByText("Readable display", { exact: true }).waitFor();
    await doc.getByText("Potential conflict: Conflicts with Work offline.", { exact: true }).waitFor();
    assert.match(await doc.innerText(), /AI suggestion from discussion/);
    // Three labelled groups with counts; the conflict is flagged in the coral
    // field; an inference carries the dashed machine mark, a stated one none.
    const token = name => page.evaluate(value => { const probe = document.createElement("i"); probe.style.background = `var(${value})`;
      document.body.append(probe); const colour = getComputedStyle(probe).backgroundColor; probe.remove(); return colour; }, name);
    assert.deepEqual(await doc.locator(".document-section-label").evaluateAll(els => els.map(el => el.firstChild.textContent)),
      ["Requirements", "Wishes", "Needs clarification"]);
    for (const category of ["requirement", "wish", "clarification"])
      assert.equal(await doc.locator(`[data-category="${category}"] .document-section-count`).innerText(),
        String(await doc.locator(`[data-category="${category}"] .document-task`).count()));
    const flag = doc.getByText("Potential conflict: Conflicts with Work offline.", { exact: true });
    assert.equal(await flag.evaluate(el => getComputedStyle(el).backgroundColor), await token("--conflict-fill"));
    assert.equal(await doc.locator('.document-basis[data-basis="inferred"]').first().evaluate(el => getComputedStyle(el).borderTopStyle), "dashed");
    assert.equal(await doc.locator('.document-basis[data-basis="stated"]').first().evaluate(el => getComputedStyle(el).borderTopStyle), "none");
    await doc.locator(".document-entries").screenshot({ path: resolve(output, `groups-${width}.png`) });
    const offlineId = (await client.snapshot()).records.find(r => r.kind === "command_entry" && r.data.text === "Work offline").id;
    const offline = doc.locator(`[data-entry-id="${offlineId}"]`);
    await offline.getByText("Criterion evidence", { exact: true }).click();
    assert.match(await offline.innerText(), /It must work offline/);
    await offline.getByText("Edit criterion", { exact: true }).click();
    const input = offline.getByLabel("Criterion", { exact: true }); await input.fill("Offline operation supported");
    await input.evaluate(el => el.setSelectionRange(5, 5)); await say(311);
    await page.waitForFunction(() => document.querySelector('#board .document-coverage')?.textContent.includes('6 of 6'));
    assert.equal(await input.inputValue(), "Offline operation supported");
    assert(await input.evaluate(el => document.activeElement === el && el.selectionStart === 5));
    await say(306);
    await doc.locator('[data-category="requirement"]').getByText("Green case", { exact: true }).waitFor();
    await offline.getByRole("button", { name: "Save criterion", exact: true }).click();
    await doc.getByText("Offline operation supported", { exact: true }).waitFor();
    await say(313); await doc.getByText("Which criterion should change?", { exact: true }).first().waitFor();
    assert.equal((await client.snapshot()).records.find(r => r.id === offlineId).data.text, "Offline operation supported");
    await doc.getByRole("button", { name: "Exclude interpretation", exact: true }).click();
    await doc.getByText("Reply needs clarification", { exact: true }).waitFor({ state: "hidden" });
    await say(316);
    await doc.getByText("Interpretation needs review", { exact: true }).waitFor();
    assert.equal(await doc.getByText("Respond within 2 seconds", { exact: true }).count(), 0);
    await doc.getByLabel("A retry may incur additional API cost", { exact: true }).check();
    await doc.getByRole("button", { name: "Retry interpretation", exact: true }).click();
    await doc.getByText("Interpretation needs review", { exact: true }).waitFor({ state: "hidden" });
    await doc.getByText("Criteria, evidence and controls", { exact: true }).click();
    await page.locator("#zoom-fit").click();
    const headingBox = await doc.locator(".kind").boundingBox(); assert(headingBox);
    await page.mouse.move(headingBox.x + 10, headingBox.y + 5); await page.mouse.down();
    await page.mouse.move(headingBox.x + 35, headingBox.y + 25, { steps: 5 }); await page.mouse.up();
    for (let attempt = 0; ; attempt++) {
      if ((await client.snapshot()).records.find(r => r.kind === "command_document").position?.hand_placed) break;
      if (attempt === 50) throw new Error("Requirements drag was not persisted");
      await new Promise(r => setTimeout(r, 100));
    }
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: resolve(output, `canvas-${width}.png`), fullPage: true });
    await doc.getByText("Criteria, evidence and controls", { exact: true }).click();
    await page.locator('[data-view="list"]').click();
    const documentId = await doc.getAttribute("data-id");
    const listDoc = page.locator(`#list-view .command-document[data-id="${documentId}"]`);
    await listDoc.getByText("Edit list title", { exact: true }).click();
    await listDoc.getByLabel("List title", { exact: true }).fill("Prototype criteria");
    await listDoc.getByRole("button", { name: "Save title", exact: true }).click();
    await listDoc.getByRole("heading", { name: "Prototype criteria" }).waitFor();
    await say(307);
    const accept = listDoc.getByRole("button", { name: "Accept requirements and wishes", exact: true });
    await accept.waitFor(); assert.equal(await accept.isEnabled(), false);
    assert.match(await listDoc.innerText(), /continue your discussion and accept this list later/);
    await say(311); await say(317);
    await page.waitForFunction(() => document.querySelectorAll('#list-view .command-document').length === 2);
    assert.equal((await client.snapshot()).session.state, "active");
    await say(318);
    const poll = page.locator('#list-view .poll:not(.command-document)');
    await poll.getByText('Draft poll', { exact: true }).waitFor();
    await say(319); await poll.getByText('Voting open', { exact: true }).waitFor();
    await say(320);
    for (let attempt = 0; ; attempt++) {
      const snapshot = await client.snapshot();
      if (snapshot.records.some(r => r.kind === 'poll_ballot' && r.data.option_id === 'option_02')) break;
      if (attempt === 50) throw new Error('Parallel poll did not collect the vote');
      await new Promise(r => setTimeout(r, 100));
    }
    assert.equal(await page.locator('#list-view .poll').count(), 3);
    const typed = (await cmd("source.text", { text: "A shared note beside voice tools" })).result;
    const acceptedNote = (await cmd("proposal.review", { proposal_id: typed.proposal.id,
      expected_revision: typed.proposal.revision, decision: "accept" })).result.item;
    const shape = (await cmd("canvas.create", { kind: "shape", data: { shape: "rect", tone: "accent", text: "Integration" },
      x: -400, y: 0, w: 180, h: 100 })).result.item;
    // A synthetic, valid PNG is generated locally; the fixture reader makes no cloud call.
    const png = await page.evaluate(() => {
      const canvas = document.createElement("canvas"); canvas.width = canvas.height = 64;
      const context = canvas.getContext("2d"); context.fillStyle = "gold"; context.fillRect(0, 0, 64, 64);
      return canvas.toDataURL("image/png").split(",")[1];
    });
    const photo = (await cmd("source.image", { mime: "image/png", base64: png,
      regions: [{ id: "combined_region", box: [0, 0, 1, 1] }] })).result;
    await cmd("extraction.queue", { source_id: photo.id, expected_revision: photo.revision });
    await page.locator('#list-view').getByText("A shared note beside voice tools", { exact: true }).waitFor();
    await page.locator('#list-view').getByText("Shape · Integration", { exact: true }).waitFor();
    for (let attempt = 0; ; attempt++) {
      const snapshot = await client.snapshot();
      if (snapshot.records.some(r => r.kind === "proposal" && r.data.region_id === "combined_region")) break;
      if (attempt === 80) throw new Error("Photo reading did not coexist with command tools");
      await new Promise(r => setTimeout(r, 100));
    }
    const anotherView = new GenAIClient({ baseUrl: `http://127.0.0.1:${apiPort}`, sessionId: credentials.session_id, token: credentials.owner_token });
    const shared = await anotherView.snapshot();
    assert(shared.records.some(r => r.id === acceptedNote.id)); assert(shared.records.some(r => r.id === shape.id));
    assert.equal(shared.records.filter(r => r.kind === "poll").length, 1);
    assert.equal(shared.records.filter(r => r.kind === "command_document").length, 2);

    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: resolve(output, `reviewing-${width}.png`), fullPage: true });
    const cloudId = (await client.snapshot()).records.find(r => r.kind === "command_entry" && r.data.text === "Always use the cloud").id;
    const cloudRow = listDoc.locator(`[data-entry-id="${cloudId}"]`);
    await cloudRow.getByText("Edit criterion", { exact: true }).click();
    await cloudRow.getByLabel("Criterion", { exact: true }).fill("Cloud access is optional");
    await cloudRow.getByLabel("Section", { exact: true }).selectOption("wish");
    await cloudRow.getByLabel("Conflict to review (clear after resolving)", { exact: true }).fill("");
    await cloudRow.getByRole("button", { name: "Save criterion", exact: true }).click();
    await listDoc.getByText("Cloud access is optional", { exact: true }).waitFor();
    await listDoc.getByLabel("Accept a list with incomplete transcript coverage", { exact: true }).check();
    await accept.click();
    await listDoc.getByText("Accepted list", { exact: true }).waitFor();
    await say(311);
    const snapshot = await client.snapshot();
    const saved = snapshot.records.find(r => r.kind === "command_document" && r.data.document_type === "requirements");
    assert.equal(saved.data.state, "accepted"); assert.equal(saved.data.entry_ids.length, 4);
    const reconnected = new GenAIClient({ baseUrl: `http://127.0.0.1:${apiPort}`, sessionId: credentials.session_id, token: credentials.owner_token });
    assert.deepEqual((await reconnected.snapshot()).records.find(r => r.id === saved.id).data, saved.data);
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: resolve(output, `accepted-${width}.png`), fullPage: true });
    await say(309); await listDoc.getByText("Collecting criteria", { exact: true }).waitFor();
    await listDoc.getByText("Previously accepted version", { exact: true }).waitFor();
    await say(310); await listDoc.getByText("Cancelled list", { exact: true }).waitFor();
    assert.deepEqual(errors, []); assert.deepEqual(failures, []);
    console.log(`PASS ${width}px: criteria, evidence, conflicts, manual edits, retries, dragging, deferred acceptance, natural let's-make commands, parallel to-do and voting, reopen/cancel and reconnect.`);
    await page.close();
  }
} finally {
  await browser?.close(); for (const child of children) child.kill();
  await Promise.all(children.map(c => new Promise(r => c.exitCode !== null ? r() : c.once("exit", r))));
  const target = resolve(data); assert(target.startsWith(resolve(tmpdir()) + "/") || target.startsWith(resolve(tmpdir()) + "\\"));
  rmSync(target, { recursive: true, force: true });
}
