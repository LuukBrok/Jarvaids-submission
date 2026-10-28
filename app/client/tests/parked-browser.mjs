import { createRequire } from "node:module";
/**
 * The parked margin end to end: the real server, a real screen.
 *
 * Node plays the facilitator through the client library: it opens a session
 * and makes two accepted, placed notes. A browser joins as a participant and
 * parks one by dragging it onto the band and the other with the P key; the
 * server must then hold a section titled Parked with those members, the
 * board must hide them and the band must list them. Unpark returns a note,
 * and dragging a card onto the board returns it at the drop point. At 1920
 * by 1080 and at 400px wide, with no console errors and no sideways scroll.
 *
 *     node tests/parked-browser.mjs
 *     PARKED_SCREENSHOT=/path/p3-parked.png node tests/parked-browser.mjs
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
const STATIC_PORT = 5203, API_PORT = 3203, API = `http://127.0.0.1:${API_PORT}`;
const data = mkdtempSync(join(tmpdir(), "jarvaids-parked-"));
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
await owner.create({ ownerName: "Sanne", title: "Parked check" });
const run = async (op, payload) => (await owner.submit(owner.intent(op, payload))).result;
let snap = await owner.snapshot();
await run("consent.acknowledge", { policy_version: snap.session.policy_version });
snap = await owner.snapshot();
await run("session.activate", { policy_version: snap.session.policy_version, expected_session_revision: snap.session.revision });

const accepted = async text => {
  const typed = await run("source.text", { text });
  return (await run("proposal.review", { proposal_id: typed.proposal.id, expected_revision: typed.proposal.revision, decision: "accept" })).item;
};
const first = await accepted("Check the tour copy");
const second = await accepted("Ask about pricing later");
const third = await accepted("Name the new step");
await run("item.place", { placements: [
  { id: first.id, x: 0, y: 0, expected_position_revision: 0 },
  { id: second.id, x: 0, y: 220, expected_position_revision: 0 },
  { id: third.id, x: 320, y: 0, expected_position_revision: 0 },
] });

const invitation = newToken();
snap = await owner.snapshot();
await run("participant.invite", { invitation, expected_roster_revision: snap.session.roster_revision, role: "participant" });
const code = `${snap.session.id}.${snap.session.policy_version}.${invitation}`;

/** The server's own answer, polled: the Parked section's members. */
const shelfOnServer = async () => {
  const s = await owner.snapshot();
  const shelf = s.records.filter(r => r.kind === "item" && r.data.item_kind === "section" && r.data.status === "accepted" &&
    r.data.title === "Parked" && r.data.form === "free");
  return { count: shelf.length, members: shelf[0]?.data.member_ids ?? null, id: shelf[0]?.id ?? null, record: s.records };
};
const eventually = async (test, what, ms = 8000) => {
  const until = Date.now() + ms;
  let last;
  while (Date.now() < until) { last = await test(); if (last === true) return; await new Promise(r => setTimeout(r, 150)); }
  throw new Error(`${what}${typeof last === "string" ? ": " + last : ""}`);
};

// ---- a participant, in a browser ----------------------------------------
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
const errors = [];
page.on("pageerror", e => errors.push(String(e)));
page.on("console", m => { if (m.type() === "error") errors.push(m.text()); });
page.on("requestfailed", r => errors.push(`request failed: ${r.url()}`));
let failures = 0;
const step = async (label, fn) => {
  try { await fn(); console.log("ok   " + label); }
  catch (error) { failures++; console.log("FAIL " + label + "\n       " + String(error.message).split("\n")[0]); }
};
const boardNote = id => page.locator(`#board .note[data-id="${id}"]`);
const card = text => page.locator("#parked .parked-card", { hasText: text });
const visible = async locator => (await locator.count()) > 0 && locator.first().isVisible();
const noSideways = async () => {
  const [scroll, width] = await page.evaluate(() => [document.documentElement.scrollWidth, window.innerWidth]);
  if (scroll > width) throw new Error(`page scrolls sideways: ${scroll} > ${width}`);
};
/** Drags from one point to another with the mouse, in steps, as a person would. */
const drag = async (from, to) => {
  await page.mouse.move(from.x, from.y);
  await page.mouse.down();
  await page.mouse.move(from.x + 12, from.y + 4, { steps: 3 });
  await page.mouse.move(to.x, to.y, { steps: 14 });
  await page.mouse.up();
};

await page.goto(`http://127.0.0.1:${STATIC_PORT}/client/`, { waitUntil: "networkidle" });
await page.click(".advanced summary");
await page.fill("#base-url", API);
await page.fill("#join-name", "Jo");
await page.fill("#join-invitation", code);
await page.click("#join");
await page.waitForSelector("#screen-workspace:not([hidden])", { timeout: 10000 });
await boardNote(first.id).waitFor({ state: "visible", timeout: 8000 });

await step("the band is at the board's right edge, 200px wide, titled Parked, with the hint when empty", async () => {
  await page.waitForSelector("#parked:not([hidden])", { timeout: 5000 });
  const band = await page.locator("#parked").boundingBox();
  const board = await page.locator("#board").boundingBox();
  if (Math.abs(band.width - 200) > 1) throw new Error(`band is ${band.width}px wide`);
  if (Math.abs(band.x + band.width - (board.x + board.width)) > 1) throw new Error("band is not on the board's right edge");
  if (Math.abs(band.y - board.y) > 1 || Math.abs(band.height - board.height) > 1) throw new Error("band is not the board's height");
  const title = (await page.textContent("#parked .parked-title")).trim();
  if (title !== "Parked") throw new Error("title: " + title);
  const hint = (await page.textContent("#parked .parked-hint")).trim();
  if (hint !== "Drag a note here to park it") throw new Error("hint: " + hint);
  const look = await page.$eval("#parked", el => {
    const cs = getComputedStyle(el), root = getComputedStyle(document.documentElement);
    const probe = document.createElement("i"); probe.style.color = "var(--paper-2)"; document.body.append(probe);
    const paper2 = getComputedStyle(probe).color; probe.remove();
    return { bg: cs.backgroundColor, paper2, line: cs.borderLeftWidth, size: getComputedStyle(el.querySelector(".parked-title")).fontSize, small: root.getPropertyValue("--fs-small").trim() };
  });
  if (look.bg !== look.paper2) throw new Error(`band ground ${look.bg}, not --paper-2 ${look.paper2}`);
  if (look.line !== "1px") throw new Error("no hairline on the left: " + look.line);
  if (look.size !== "13px") throw new Error("title is not Small: " + look.size);
  await noSideways();
});

await step("dragging a note onto the band parks it: a Parked section holds it, the board hides it, the band lists it", async () => {
  const from = await boardNote(first.id).boundingBox();
  const band = await page.locator("#parked").boundingBox();
  await drag({ x: from.x + 40, y: from.y + 30 }, { x: band.x + band.width / 2, y: band.y + 160 });
  await card("Check the tour copy").waitFor({ state: "visible", timeout: 8000 });
  await eventually(async () => {
    const shelf = await shelfOnServer();
    return shelf.count === 1 && JSON.stringify(shelf.members) === JSON.stringify([first.id]) || JSON.stringify(shelf.members);
  }, "the server has no Parked section holding the note");
  await page.waitForTimeout(1300);   // one poll: the server's answer, not this screen's guess
  if (await visible(boardNote(first.id))) throw new Error("the parked note is still drawn on the board");
  if (!(await boardNote(first.id).evaluate(el => el.classList.contains("is-parked")))) throw new Error("no is-parked class");
  const { id } = await shelfOnServer();
  if (await visible(page.locator(`#board [data-id="${id}"]`))) throw new Error("the Parked section is drawn as a rectangle");
  if (await page.locator("#parked .parked-hint").isVisible()) throw new Error("the empty hint still shows");
});

await step("a card is a compact note: Body words on the accent at -soft, straight, with Unpark", async () => {
  const look = await card("Check the tour copy").evaluate(el => {
    const probe = document.createElement("i"); probe.style.color = "var(--yellow-soft)"; document.body.append(probe);
    const soft = getComputedStyle(probe).color; probe.remove();
    const text = getComputedStyle(el.querySelector(".parked-text"));
    return { bg: getComputedStyle(el).backgroundColor, soft, rotate: getComputedStyle(el).rotate, size: text.fontSize,
      body: getComputedStyle(document.documentElement).getPropertyValue("--fs-body").trim() };
  });
  if (look.bg !== look.soft) throw new Error(`card fill ${look.bg}, not --yellow-soft ${look.soft}`);
  if (look.rotate !== "none" && look.rotate !== "0deg") throw new Error("card is rotated: " + look.rotate);
  if (look.size !== "15px") throw new Error("card text is not Body: " + look.size);
  await card("Check the tour copy").getByRole("button", { name: /^Unpark/ }).waitFor({ state: "visible" });
});

await step("P parks the focused board note", async () => {
  await boardNote(second.id).locator("button").first().focus();
  await page.keyboard.press("p");
  await card("Ask about pricing later").waitFor({ state: "visible", timeout: 8000 });
  await eventually(async () => {
    const shelf = await shelfOnServer();
    return JSON.stringify(shelf.members) === JSON.stringify([first.id, second.id]) || JSON.stringify(shelf.members);
  }, "the server's shelf does not hold both notes in order");
  await page.waitForTimeout(1300);
  if (await visible(boardNote(second.id))) throw new Error("the note parked with P is still on the board");
  const order = await page.$$eval("#parked .parked-text", ps => ps.map(p => p.textContent));
  if (order.join("|") !== "Check the tour copy|Ask about pricing later") throw new Error("shelf order: " + order.join("|"));
  const gap = await page.$$eval("#parked .parked-list > li", lis => lis[1].getBoundingClientRect().top - lis[0].getBoundingClientRect().bottom);
  if (Math.abs(gap - 12) > 0.5) throw new Error(`cards are ${gap}px apart, not 12`);
});

if (process.env.PARKED_SCREENSHOT) {
  const board = await page.locator("#board").boundingBox();
  await page.mouse.move(board.x + 10, board.y + 10);
  // The board holds the keyboard focus after P, and its ring is not what
  // the picture is about.
  await page.evaluate(() => document.activeElement?.blur());
  const width = Math.min(board.width + 16, 1000);
  await page.screenshot({ path: process.env.PARKED_SCREENSHOT,
    clip: { x: board.x + board.width + 8 - width, y: board.y - 8, width, height: Math.min(board.height + 16, 720) } });
}

await step("P in a field types the letter and parks nothing", async () => {
  await page.fill("#note-text", "");
  await page.focus("#note-text");
  await page.keyboard.press("p");
  if ((await page.inputValue("#note-text")) !== "p") throw new Error("the field did not get the p");
  await page.fill("#note-text", "");
  if ((await page.locator("#parked .parked-card").count()) !== 2) throw new Error("something else was parked");
});

await step("Unpark returns the note to the board, beside the band", async () => {
  await card("Check the tour copy").getByRole("button", { name: /^Unpark/ }).click();
  await boardNote(first.id).waitFor({ state: "visible", timeout: 8000 });
  if (await card("Check the tour copy").count()) throw new Error("the card is still on the shelf");
  await eventually(async () => {
    const shelf = await shelfOnServer();
    return JSON.stringify(shelf.members) === JSON.stringify([second.id]) || JSON.stringify(shelf.members);
  }, "the server still holds the unparked note");
  await page.waitForTimeout(1300);
  const note = await boardNote(first.id).boundingBox();
  const band = await page.locator("#parked").boundingBox();
  const board = await page.locator("#board").boundingBox();
  if (!note || note.x + note.width > band.x + 1) throw new Error(`the note came back under the band: ${JSON.stringify(note)}`);
  if (note.x < board.x || note.y < board.y || note.y > board.y + board.height) throw new Error("the note came back outside the board");
});

await step("dragging a card onto the board unparks it at the drop point", async () => {
  const from = await card("Ask about pricing later").locator(".parked-text").boundingBox();
  const cardBox = await card("Ask about pricing later").boundingBox();
  const board = await page.locator("#board").boundingBox();
  // A pan makes the view the person's own, so the board stops refitting it
  // on every render and the note's screen position can be compared.
  await page.mouse.move(board.x + 200, board.y + 200);
  await page.mouse.wheel(0, 8);
  await page.waitForTimeout(100);
  const to = { x: board.x + 360, y: board.y + 420 };
  await drag({ x: from.x + 10, y: from.y + 8 }, to);
  await boardNote(second.id).waitFor({ state: "visible", timeout: 8000 });
  await eventually(async () => {
    const shelf = await shelfOnServer();
    return JSON.stringify(shelf.members) === "[]" || JSON.stringify(shelf.members);
  }, "the server's shelf is not empty");
  await page.waitForTimeout(1300);
  const note = await boardNote(second.id).boundingBox();
  const want = { x: to.x - (from.x + 10 - cardBox.x), y: to.y - (from.y + 8 - cardBox.y) };
  if (Math.abs(note.x - want.x) > 3 || Math.abs(note.y - want.y) > 3) {
    throw new Error(`landed at ${Math.round(note.x)},${Math.round(note.y)}, dropped at ${Math.round(want.x)},${Math.round(want.y)}`);
  }
  const hint = (await page.textContent("#parked .parked-hint")).trim();
  if (hint !== "Drag a note here to park it") throw new Error("empty hint did not come back: " + hint);
});

await step("a note in a group is refused with the reason", async () => {
  const group = await run("proposal.create", { proposal_kind: "relationship", form: "cluster", text: "Tour",
    refs: [{ id: first.id, revision: first.revision }, { id: third.id, revision: third.revision }] });
  const fresh = (await owner.snapshot()).records.find(r => r.id === group.proposal?.id || r.id === group.id);
  await run("proposal.review", { proposal_id: fresh.id, expected_revision: fresh.revision, decision: "accept" });
  await page.waitForSelector(".hull", { timeout: 8000 });
  await boardNote(third.id).locator("button").first().focus();
  await page.keyboard.press("p");
  await page.waitForSelector("#attention:not([hidden])", { timeout: 4000 });
  const words = await page.textContent("#attention-text");
  if (!/^Take the note out of its group first/.test(words)) throw new Error("banner: " + words);
  if (!(await visible(boardNote(third.id)))) throw new Error("the grouped note left the board");
  await page.click("#attention-dismiss");
});

await step("the list view hides the band", async () => {
  await page.click('[data-view="list"]');
  if (await page.locator("#parked").isVisible()) throw new Error("band shows over the list");
  await page.click('[data-view="canvas"]');
  await page.waitForSelector("#parked:not([hidden])");
});

await step("at 400px the band is a shelf under the board, parks with P, unparks, and nothing scrolls sideways", async () => {
  await page.setViewportSize({ width: 400, height: 860 });
  await page.waitForTimeout(300);
  await noSideways();
  const band = await page.locator("#parked").boundingBox();
  const board = await page.locator("#board").boundingBox();
  if (band.y < board.y + board.height - 1) throw new Error("band overlays the board at 400px");
  if (band.x < 0 || band.x + band.width > 400) throw new Error("band leaves the screen");
  await page.locator("#board").focus();
  await boardNote(second.id).locator("button").first().focus();
  await page.keyboard.press("p");
  await card("Ask about pricing later").waitFor({ state: "visible", timeout: 8000 });
  await page.waitForTimeout(1300);
  await noSideways();
  if (process.env.PARKED_SCREENSHOT) {
    await page.evaluate(() => document.activeElement?.blur());
    await page.locator("#parked").scrollIntoViewIfNeeded();
    await page.screenshot({ path: process.env.PARKED_SCREENSHOT.replace(/\.png$/, "-400.png") });
  }
  await card("Ask about pricing later").getByRole("button", { name: /^Unpark/ }).click();
  await boardNote(second.id).waitFor({ state: "visible", timeout: 8000 });
  await page.waitForTimeout(1300);
  await noSideways();
});

await step("no console errors and no failed requests", async () => { if (errors.length) throw new Error(errors.join(" | ").slice(0, 400)); });

await browser.close();
stopAll();
process.exit(failures ? 1 : 0);
