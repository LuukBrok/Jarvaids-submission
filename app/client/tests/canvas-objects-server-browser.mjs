import { createRequire } from "node:module";
/**
 * Canvas objects end to end: made through the real server, drawn on a real
 * screen.
 *
 * Node plays the facilitator through the client library: it opens a session,
 * makes one of each canvas kind by hand, proposes an ellipse the way a model
 * would, and draws an arrow to that proposal. A browser joins as a
 * participant and must draw every object, the proposal as proposed. Then the
 * facilitator accepts the proposal: it must turn into an accepted object, and
 * the arrow drawn to it must stay attached to what it became.
 *
 *     node tests/canvas-objects-server-browser.mjs
 */
import { spawn } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { GenAIClient, newId, newToken } from "../../server/client.mjs";

let chromium;
try { ({ chromium } = createRequire(import.meta.url)("playwright")); }
catch { console.log("SKIP: playwright is not installed."); process.exit(0); }

const HERE = dirname(fileURLToPath(import.meta.url));
const CLIENT = resolve(HERE, ".."), SERVER = resolve(CLIENT, "../server");
const STATIC_PORT = 5181, API_PORT = 3081, API = `http://127.0.0.1:${API_PORT}`;
const data = mkdtempSync(join(tmpdir(), "jarvaids-canvas-"));
const children = [];
const start = (command, args, cwd) => children.push(spawn(command, args, { cwd, stdio: "ignore" }));
const stopAll = () => { for (const c of children) { try { c.kill("SIGTERM"); } catch {} } try { rmSync(data, { recursive: true, force: true }); } catch {} };
process.on("exit", stopAll);
start(process.env.JARVAIDS_TEST_PYTHON || "python3", ["serve.py", "--port", String(STATIC_PORT)], CLIENT);
start(process.env.JARVAIDS_TEST_PYTHON || "python3", ["-m", "genai_server", "--port", String(API_PORT), "--data-dir", data,
  "--allow-origin", `http://127.0.0.1:${STATIC_PORT}`], SERVER);
const ready = async url => {
  for (let i = 0; i < 80; i++) {
    try { const r = await fetch(url); await r.arrayBuffer(); if (r.ok) return; } catch {}
    await new Promise(r => setTimeout(r, 150));
  }
  throw new Error("server never became ready: " + url);
};
await ready(`http://127.0.0.1:${STATIC_PORT}/client/index.html`);
await ready(`${API}/health`);

// ---- the facilitator, in Node -------------------------------------------
const owner = new GenAIClient({ baseUrl: API, sessionId: newId(), token: newToken() });
await owner.create({ ownerName: "Sanne", title: "Canvas check" });
const run = async (op, payload) => (await owner.submit(owner.intent(op, payload))).result;
let snap = await owner.snapshot();
await run("consent.acknowledge", { policy_version: snap.session.policy_version });
snap = await owner.snapshot();
await run("session.activate", { policy_version: snap.session.policy_version, expected_session_revision: snap.session.revision });

const typed = await run("source.text", { text: "People skip the tour" });
const note = (await run("proposal.review", { proposal_id: typed.proposal.id, expected_revision: typed.proposal.revision, decision: "accept" })).item;
const make = async (kind, data, x, y, w, h) => (await run("canvas.create", { kind, data, x, y, ...(w ? { w, h } : {}) })).item;
const shape = await make("shape", { shape: "rect", tone: "accent", text: "Ideas" }, 400, 0, 160, 80);
const words = await make("text", { text: "Where onboarding loses people", size: "heading" }, 0, -120, 520, 40);
const section = await make("section", { title: "Risks", form: "free", member_ids: [note.id] }, -40, 160, 360, 200);
const pen = await make("stroke", { points: [[0, 0], [30, -12], [60, 8], [90, -4]], weight: "regular", tone: "ink" }, 400, 200);
const arrow = await make("arrow", { from: { id: shape.id }, to: { id: words.id }, tone: "ink", label: "names" }, 0, 0);
const proposal = await run("proposal.create", { proposal_kind: "canvas", canvas_kind: "shape",
  canvas_data: { shape: "ellipse", tone: "ink", text: "Run a test" }, positions: [{ x: 700, y: 0, w: 160, h: 80 }] });
const toProposal = await make("arrow", { from: { id: shape.id }, to: { id: proposal.id }, tone: "accent" }, 0, 0);

const invitation = newToken();
snap = await owner.snapshot();
await run("participant.invite", { invitation, expected_roster_revision: snap.session.roster_revision, role: "participant" });
const code = `${snap.session.id}.${snap.session.policy_version}.${invitation}`;

// ---- a participant, in a browser ----------------------------------------
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const errors = [];
page.on("pageerror", e => errors.push(String(e)));
page.on("console", m => { if (m.type() === "error") errors.push(m.text()); });
let failures = 0;
const step = async (label, fn) => {
  try { await fn(); console.log("ok   " + label); }
  catch (error) { failures++; console.log("FAIL " + label + "\n       " + String(error.message).split("\n")[0]); }
};
const drawn = id => page.locator(`[data-id="${id}"]`);

await page.goto(`http://127.0.0.1:${STATIC_PORT}/client/`, { waitUntil: "networkidle" });
await page.click(".advanced summary");
await page.fill("#base-url", API);
await page.fill("#join-name", "Jo");
await page.fill("#join-invitation", code);
await page.click("#join");
await page.waitForSelector("#screen-workspace:not([hidden])", { timeout: 10000 });

await step("every kind made by hand is drawn, in the accepted look", async () => {
  for (const [what, item] of [["shape", shape], ["text", words], ["section", section], ["stroke", pen], ["arrow", arrow]]) {
    await drawn(item.id).first().waitFor({ state: "attached", timeout: 8000 }).catch(() => { throw new Error(`${what} not drawn`); });
    if (await drawn(item.id).first().evaluate(el => el.classList.contains("cobj-proposed"))) throw new Error(`${what} drawn as proposed`);
  }
});

await step("a canvas proposal is drawn proposed, and the arrow to it is drawn", async () => {
  await drawn(proposal.id).first().waitFor({ state: "attached", timeout: 8000 });
  if (!(await drawn(proposal.id).first().evaluate(el => el.classList.contains("cobj-proposed")))) throw new Error("proposal not drawn as proposed");
  await drawn(toProposal.id).first().waitFor({ state: "attached", timeout: 8000 });
});

await step("accepted, the proposal becomes an accepted object and the arrow stays attached", async () => {
  const fresh = (await owner.snapshot()).records.find(r => r.id === proposal.id);
  const accepted = await run("proposal.review", { proposal_id: proposal.id, expected_revision: fresh.revision, decision: "accept" });
  await drawn(accepted.item.id).first().waitFor({ state: "attached", timeout: 8000 });
  if (await drawn(accepted.item.id).first().evaluate(el => el.classList.contains("cobj-proposed"))) throw new Error("accepted object still drawn as proposed");
  if (await drawn(proposal.id).count()) throw new Error("the proposal is still on the canvas");
  await page.waitForTimeout(1200);
  if (!(await drawn(toProposal.id).count())) throw new Error("the arrow lost the object its proposal became");
});

await step("the list view names the objects", async () => {
  await page.click('[data-view="list"]');
  const text = await page.textContent("#list-view");
  for (const want of ["Ideas", "Risks", "Arrow"]) if (!text.includes(want)) throw new Error(`list is missing ${want}`);
  await page.click('[data-view="canvas"]');
});

await step("no console errors", async () => { if (errors.length) throw new Error(errors.join(" | ").slice(0, 300)); });

if (process.env.SCREENSHOTS) await page.screenshot({ path: join(process.env.SCREENSHOTS, "canvas-server.png") });
await browser.close();
stopAll();
process.exit(failures ? 1 : 0);
