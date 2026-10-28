/**
 * The review rail drawn from an injected snapshot: Review cards, the
 * transcript and People, at 1920 by 1080 and at 400px.
 *
 *     node tests/rail-browser.mjs
 *
 * No API server: the page's own modules draw a snapshot this test builds,
 * through a stand-in for app.mjs's context, the way
 * command-recognition-browser.mjs drives the transcript. It checks the card
 * order (evidence, text, then Accept, Correct, Reject), that Correct opens
 * the field in place and that a changed field is sent as a correction, the
 * transcript's people colours, current line, command row, Quote button and
 * `jv:quote` event, People rows with their colours and ids, no console
 * errors, and no sideways scroll. Screenshots of the three tabs go to
 * RAIL_SCREENSHOTS, or to .local/rail-ui/ at the repository root.
 */
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createRequire } from "node:module";
import { mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");
const client = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const output = process.env.RAIL_SCREENSHOTS || resolve(client, "../../.local/rail-ui");
mkdirSync(output, { recursive: true });
const port = 5197;
const server = spawn(process.env.JARVAIDS_TEST_PYTHON || "python3",
  ["serve.py", "--port", String(port)], { cwd: client, stdio: "ignore" });
server.on("error", error => { throw error; });

/** Builds the snapshot and a stand-in for app.mjs's ctx inside the page, then
 * draws the three panels. Runs in the browser. */
async function inject() {
  const { createReview } = await import("/client/review.mjs");
  const { renderTranscript } = await import("/client/transcript.mjs");
  const { createPeople } = await import("/client/people.mjs");
  document.getElementById("screen-setup").hidden = true;
  document.getElementById("screen-workspace").hidden = false;

  // A crop: a soft yellow note with words on it, drawn here so no file is needed.
  const canvas = document.createElement("canvas");
  canvas.width = 480; canvas.height = 300;
  const g = canvas.getContext("2d");
  g.fillStyle = "rgb(242, 239, 231)"; g.fillRect(0, 0, 480, 300);
  g.fillStyle = "rgb(255, 200, 61)"; g.fillRect(60, 30, 360, 240);
  g.fillStyle = "rgb(22, 21, 15)"; g.font = "600 34px sans-serif";
  g.fillText("Too many", 100, 130); g.fillText("fields", 100, 180);
  const png = await new Promise(done => canvas.toBlob(done, "image/png"));

  const now = Math.floor(Date.now() / 1000);
  const T = minutes => now - minutes * 60;
  const seg = (id, minutes, text, extra = {}) => ({ id, kind: "transcript_segment", revision: 1,
    data: { status: "final", text, created_at: T(minutes), provenance: { synthetic: false }, ...extra } });
  const s = {
    actor_id: "a_jo",
    session: { id: "sess", title: "Wall review", state: "active", policy_version: 1, roster_revision: 3, revision: 4 },
    members: [
      { id: "a_jo", name: "Jo", role: "facilitator", consent_version: 1, agreed_at: T(40) },
      { id: "a_sam", name: "Sam", role: "participant", consent_version: 1, agreed_at: T(38) },
      { id: "a_ali", name: "Ali", role: "participant", consent_version: 0, agreed_at: null },
    ],
    records: [
      { id: "src_1", kind: "source", revision: 1, data: { type: "image", regions: [{ id: "r1" }] } },
      { id: "i_1", kind: "item", revision: 1, data: { item_kind: "content", status: "accepted", text: "Too many fields before value", origin: "human" } },
      { id: "i_2", kind: "item", revision: 1, data: { item_kind: "content", status: "accepted", text: "Onboarding loses people at step two", origin: "human" } },
      { id: "p_read", kind: "proposal", revision: 1, data: { proposal_kind: "content", status: "needs_review", text: "Too many fields",
        refs: [{ id: "src_1", revision: 1 }], region_id: "r1", origin: "fixture", provider: "fixture", synthetic: true,
        confidence: null, author_id: "a_jo", created_at: T(12) } },
      { id: "p_typed", kind: "proposal", revision: 2, data: { proposal_kind: "content", status: "needs_review",
        text: "Nobody reads the tooltip", refs: [], origin: "human", author_id: "a_sam", created_at: T(9) } },
      { id: "p_group", kind: "proposal", revision: 1, data: { proposal_kind: "relationship", form: "cluster", status: "needs_review",
        text: "Onboarding", refs: [{ id: "i_1", revision: 1 }, { id: "i_2", revision: 1 }], origin: "human", author_id: "a_jo", created_at: T(6) } },
      { id: "p_canvas", kind: "proposal", revision: 1, data: { proposal_kind: "canvas", canvas_kind: "shape", status: "needs_review",
        canvas_data: { shape: "rect", text: "Run a test", tone: "accent" }, origin: "model", provider: "local", author_id: "a_jo", created_at: T(4) } },
      { id: "job_1", kind: "job", revision: 1, data: { status: "running", refs: [{ id: "src_1", revision: 1 }], created_at: T(1) } },
      { id: "prof_1", kind: "speaker_profile", revision: 1, data: { name: "Ali", provenance: { synthetic: true } } },
      seg("seg_1", 20, "Shall we start with the onboarding wall?", { speaker_actor_id: "a_jo" }),
      seg("seg_2", 18, "Yes. Most of the notes are about step three.", { speaker_actor_id: "a_sam" }),
      seg("seg_3", 15, "I counted seven that say the form is too long.", { attribution: "voice_identified", speaker_name: "Ali", speaker_actor_id: "a_jo" }),
      seg("seg_4", 12, "Could be the same person writing twice.", { attribution: "unidentified", speaker_actor_id: "a_jo" }),
      seg("seg_5", 8, "Hey Jarvaids, make a summary.", { speaker_actor_id: "a_jo", voice_command: { status: "recognised", intent: "summary" } }),
      seg("seg_6", 5, "Hey Jarvaids, make a...", { speaker_actor_id: "a_sam", voice_command: { status: "incomplete", command: "make a" } }),
      seg("seg_7", 2, "Then let us group the step three notes before lunch.", { speaker_actor_id: "a_sam" }),
    ],
  };

  const sent = [];
  const $ = id => document.getElementById(id);
  const show = (el, on) => { if (el) el.hidden = !on; };
  const app = { snapshot: s, crops: new Map(), drafts: new Map(), dismissedJobs: new Set(), undoStack: [],
    lastAccepted: null, focusProposal: null,
    client: { crop: async () => png, createMediaUrl: blob => URL.createObjectURL(blob),
      // As client.mjs: a released URL is revoked. The review rail gives a
      // card's crop back when the card leaves the queue (phase 4).
      revokeMediaUrl: url => { window.revokedUrls = [...(window.revokedUrls ?? []), url]; URL.revokeObjectURL(url); } } };
  const button = (label, variant, onClick) => {
    const b = document.createElement("button");
    b.type = "button"; b.className = `btn ${variant}`; b.textContent = label;
    b.addEventListener("click", () => onClick().catch(() => {}));
    return b;
  };
  const open = () => app.snapshot.records.filter(r => r.kind === "proposal" && ["needs_review", "stale"].includes(r.data.status));
  const render = () => {
    $("queue-count").textContent = String(open().length);
    review.renderQueue(app.snapshot, open());
    renderTranscript(app.snapshot);
    people.renderPeople(app.snapshot);
  };
  const send = async (operation, payload) => {
    sent.push([operation, payload]);
    const p = app.snapshot.records.find(r => r.id === payload.proposal_id);
    if (operation === "proposal.edit") { p.data.text = payload.text; p.data.last_editor = app.snapshot.actor_id; p.revision += 1; render(); return { id: p.id, revision: p.revision }; }
    if (operation === "proposal.review") { p.data.status = payload.decision === "accept" ? "accepted" : "rejected"; render(); return { item: { id: "item_" + p.id, data: { text: p.data.text } } }; }
    render();
    return {};
  };
  const ctx = { app, $, show, send, render, button, attention: () => {}, describe: String,
    confirm: async () => false, clock: sec => new Date(sec * 1000).toTimeString().slice(0, 5),
    undo: async () => {}, stopListening: () => {} };
  const review = createReview(ctx);
  const people = createPeople(ctx);
  ctx.review = review;
  const quotes = [];
  document.addEventListener("jv:quote", event => quotes.push(event.detail));
  Object.assign(window, { railTest: { app, render, sent, quotes } });
  render();
}

/** The computed value a token resolves to, read through a probe element. */
const token = (page, prop, value) => page.evaluate(([prop, value]) => {
  const probe = document.createElement("span");
  probe.style.setProperty(prop, value);
  document.querySelector(".ws-rail").append(probe);
  const out = getComputedStyle(probe).getPropertyValue(prop);
  probe.remove();
  return out;
}, [prop, value]);

let browser;
try {
  for (let attempt = 0; ; attempt++) {
    try { const r = await fetch(`http://127.0.0.1:${port}/client/`); await r.arrayBuffer(); if (r.ok) break; } catch {}
    if (attempt >= 80) throw new Error("Static server did not start.");
    await new Promise(done => setTimeout(done, 100));
  }
  browser = await chromium.launch({ headless: true,
    ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}) });
  for (const [width, height] of [[1920, 1080], [400, 900]]) {
    // Reduced motion, so a colour read just after a class change is the end
    // colour, not a frame of its transition.
    const page = await browser.newPage({ viewport: { width, height }, reducedMotion: "reduce" });
    const errors = [], failedRequests = [];
    page.on("pageerror", error => errors.push(error.message));
    page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
    page.on("requestfailed", request => { if (!request.url().startsWith("blob:")) failedRequests.push(request.url()); });
    page.on("response", response => { if (response.status() >= 400) failedRequests.push(response.url()); });
    await page.goto(`http://127.0.0.1:${port}/client/`);
    await page.evaluate(inject);
    await page.click('[data-rail="review"]');

    // ---- Review: four cards, each evidence, then text, then actions.
    const cards = page.locator("#queue .proposal[data-id]");
    assert.equal(await cards.count(), 4);
    assert.equal(await page.locator("#queue-count").innerText(), "4");
    assert(await page.locator("#queue-empty").isHidden(), "the empty sentence hides while cards wait");
    await page.waitForSelector('.proposal[data-id="p_read"] .evidence-crop img.crop-img', { timeout: 5000 });
    assert(await page.evaluate(() => document.querySelector('.proposal[data-id="p_read"] img.crop-img').naturalWidth > 0), "the crop loaded");
    const order = await page.evaluate(() => [...document.querySelectorAll("#queue .proposal")].map(card => {
      const kids = [...card.children].filter(k => !k.hidden);
      const at = sel => kids.findIndex(k => k.matches(sel));
      return { id: card.dataset.id, evidence: at(".evidence"), text: at(".proposal-text, .proposal-correct"),
        actions: at(".proposal-actions"), buttons: [...card.querySelectorAll(".proposal-actions button")].map(b => b.textContent),
        primary: card.querySelector(".btn-primary")?.textContent, quiet: card.querySelector(".btn-quiet")?.textContent };
    }));
    for (const card of order) {
      assert.equal(card.evidence, 0, `${card.id}: the evidence comes first`);
      assert.equal(card.primary?.startsWith("Accept"), true, `${card.id}: the first primary is Accept`);
      assert.equal(card.quiet, "Reject", `${card.id}: the first quiet button is Reject`);
      if (card.id === "p_canvas") { assert.deepEqual(card.buttons, ["Accept", "Reject"]); continue; }
      assert(card.text > card.evidence && card.actions > card.text, `${card.id}: evidence, then text, then actions`);
      assert.deepEqual(card.buttons, [card.id === "p_group" ? "Accept group" : "Accept", "Correct", "Reject"], card.id);
    }
    assert.equal(await page.locator('.proposal[data-id="p_typed"] .evidence-typed').innerText().then(t => /Typed by Sam/.test(t)), true);
    assert.equal(await page.locator('.proposal[data-id="p_group"] .evidence-members li').count(), 2);
    assert.equal(await page.locator('.proposal[data-id="p_canvas"] .evidence-line').innerText(), "Shape · Run a test");
    assert.match(await page.locator('.proposal[data-id="p_read"] .origin').innerText(), /fixture.*no handwriting recognition/);
    assert.equal(await page.locator('.proposal[data-id="p_read"] .proposal-marker').innerText(), "proposed");
    assert.equal(await page.locator('.proposal[data-id="p_typed"] .proposal-marker').innerText(), "not yet reviewed");
    assert(await page.locator('.proposal[data-id="p_read"] textarea').isHidden(), "the field stays closed until Correct");
    assert.equal(await page.locator(".job").count(), 1, "a reading in progress keeps its row above the queue");

    // The focused card: the one shadow, no outline, and its field open.
    await page.evaluate(() => { window.railTest.app.focusProposal = "p_read"; window.railTest.render(); });
    const focused = page.locator(".proposal.focused");
    assert.equal(await focused.getAttribute("data-id"), "p_read");
    const look = await focused.evaluate(el => ({ shadow: getComputedStyle(el).boxShadow, outline: getComputedStyle(el).outlineStyle }));
    assert.notEqual(look.shadow, "none", "the focused card carries the shadow");
    assert.equal(look.outline, "none");
    assert.equal(await page.locator(".proposal:not(.focused)").evaluateAll(els => els.every(el => getComputedStyle(el).boxShadow === "none")), true,
      "only the focused card is raised");
    assert(await page.locator(".proposal.focused textarea").isVisible(), "Review from the canvas opens the field");
    await page.locator(".ws-rail").screenshot({ path: resolve(output, width === 1920 ? "p3-rail-review.png" : "rail-review-400.png") });

    // A filled field is a correction, Correct pressed or not: edit, then review.
    await page.fill(".proposal.focused textarea", "Too many fields before any value");
    await page.click(".proposal.focused .btn-primary");
    await page.waitForFunction(() => !document.querySelector('.proposal[data-id="p_read"]'));
    // Its crop's blob URL went back when the card left the queue, so a long
    // session never runs into the client's cap of 16 media URLs.
    assert.equal(await page.evaluate(() => [...window.railTest.app.crops.keys()].some(k => k.startsWith("p_read:"))), false,
      "the accepted card's crop is released");
    assert.ok(await page.evaluate(() => (window.revokedUrls ?? []).length >= 1), "its blob URL was revoked");
    let sent = await page.evaluate(() => window.railTest.sent.splice(0));
    assert.deepEqual(sent.map(([op]) => op), ["proposal.edit", "proposal.review"]);
    assert.equal(sent[0][1].text, "Too many fields before any value");
    assert.equal(sent[1][1].decision, "accept");

    // Correct opens the field in place, with the text, focus in it.
    const typed = page.locator('.proposal[data-id="p_typed"]');
    await typed.getByRole("button", { name: "Correct" }).click();
    const field = typed.locator("textarea");
    assert(await field.isVisible());
    assert.equal(await field.inputValue(), "Nobody reads the tooltip");
    assert.equal(await page.evaluate(() => document.activeElement?.dataset.draftFor), "p_typed", "focus is in the field");
    assert(await typed.locator(".proposal-text").isHidden(), "the field takes the text's place");
    assert.deepEqual(await typed.locator(".proposal-actions button").allInnerTexts(), ["Accept", "Keep original", "Reject"]);
    await typed.getByRole("button", { name: "Keep original" }).click();
    assert(await typed.locator("textarea").isHidden());
    assert(await typed.locator(".proposal-text").isVisible());
    // Accept with an unchanged text sends the review alone.
    await typed.locator(".btn-primary").click();
    await page.waitForFunction(() => !document.querySelector('.proposal[data-id="p_typed"]'));
    sent = await page.evaluate(() => window.railTest.sent.splice(0));
    assert.deepEqual(sent.map(([op]) => op), ["proposal.review"]);
    // Reject is the first quiet button.
    await page.click('.proposal[data-id="p_group"] .btn-quiet');
    sent = await page.evaluate(() => window.railTest.sent.splice(0));
    assert.deepEqual(sent.map(([op, body]) => [op, body.decision]), [["proposal.review", "reject"]]);

    // ---- Transcript.
    await page.click('[data-rail="transcript"]');
    const rows = page.locator("#transcript .transcript-row");
    assert.equal(await rows.count(), 7);
    const ids = await rows.evaluateAll(els => els.map(el => [el.dataset.segmentId, el.id]));
    assert.deepEqual(ids, [1, 2, 3, 4, 5, 6, 7].map(n => [`seg_${n}`, `seg-seg_${n}`]));
    const colour = id => page.locator(`#seg-seg_${id} .transcript-speaker`).evaluate(el => getComputedStyle(el).color);
    assert.equal(await colour(1), await token(page, "color", "var(--lilac-deep)"), "Jo joined first: lilac");
    assert.equal(await colour(2), await token(page, "color", "var(--mint-deep)"), "Sam joined second: mint");
    assert.equal(await colour(3), await token(page, "color", "var(--periwinkle-deep)"), "the voice named Ali is Ali, third");
    assert.equal(await colour(4), await token(page, "color", "var(--ink-3)"), "an unknown speaker is ink-3");
    assert.equal(await page.locator("#seg-seg_4 .transcript-speaker").innerText(), "Unknown speaker");
    const bg = id => page.locator(`#seg-seg_${id}`).evaluate(el => getComputedStyle(el).backgroundColor);
    assert.equal(await bg(7), await token(page, "background-color", "var(--mint-soft)"), "the newest line is current");
    assert.equal(await page.locator("#seg-seg_7").getAttribute("aria-current"), "true");
    assert.equal(await bg(5), await token(page, "background-color", "var(--periwinkle-soft)"), "a recognised command is its own row");
    assert.equal(await bg(2), "rgba(0, 0, 0, 0)", "an ordinary line has no fill");
    assert.equal(await page.locator("#seg-seg_5 .command-provisional").count(), 1);
    assert.match(await page.locator("#seg-seg_5 .command-feedback").innerText(), /summary requested/);
    assert.equal(await page.locator("#seg-seg_6 .transcript-badge").innerText(), "Request unfinished");
    assert.match(await page.locator("#seg-seg_1 .transcript-time").innerText(), /^\d\d:\d\d:\d\d$/);
    assert.equal(await page.locator("#seg-seg_1 .transcript-time").evaluate(el => getComputedStyle(el).fontFamily.includes("JetBrains Mono")), true);
    assert.match(await page.locator("#transcript-note").innerText(), /Enrolled voices are matched automatically/);
    if (width === 1920) {
      const hidden = await page.locator("#seg-seg_2 .quote-line").evaluate(el => getComputedStyle(el).opacity);
      assert.equal(hidden, "0", "Quote is quiet until the line is hovered");
      await page.locator("#seg-seg_2").hover();
      await page.waitForFunction(() => getComputedStyle(document.querySelector("#seg-seg_2 .quote-line")).opacity === "1");
    }
    await page.locator("#seg-seg_2 .quote-line").focus();
    assert.equal(await page.locator("#seg-seg_2 .quote-line").evaluate(el => el.matches(".btn.btn-quiet.btn-sm")), true);
    await page.locator("#seg-seg_2 .quote-line").click();
    const quotes = await page.evaluate(() => window.railTest.quotes);
    assert.equal(quotes.length, 1);
    const said = await page.evaluate(() => window.railTest.app.snapshot.records.find(r => r.id === "seg_2").data.created_at);
    assert.deepEqual(quotes[0], { segmentId: "seg_2", text: "Yes. Most of the notes are about step three.",
      speakerName: "Sam", speakerActorId: "a_sam", createdAt: said });
    await page.evaluate(() => document.getElementById("seg-seg_2").classList.add("quoted-highlight"));
    assert.equal(await bg(2), await token(page, "background-color", "var(--mint-soft)"), "a quoted line is highlighted");
    await page.evaluate(() => window.railTest.render());
    assert.equal(await page.locator("#seg-seg_2.quoted-highlight").count(), 1, "the highlight survives a redraw");
    if (width === 1920) {
      await page.mouse.move(0, 0);
      await page.locator("#seg-seg_7").hover();
      await page.locator(".ws-rail").screenshot({ path: resolve(output, "p3-rail-transcript.png") });
    }

    // ---- People.
    await page.click('[data-rail="people"]');
    const people = page.locator("#people-rows .person");
    assert.deepEqual(await people.evaluateAll(els => els.map(el => el.dataset.actorId)), ["a_jo", "a_sam", "a_ali"]);
    assert.equal(await page.locator('#people-rows [data-actor-id="a_sam"] .person-dot').evaluate(el => getComputedStyle(el).backgroundColor),
      await token(page, "background-color", "var(--mint)"));
    assert.equal(await page.locator('#people-rows [data-actor-id="a_jo"] .person-dot').evaluate(el => el.getBoundingClientRect().width), 24);
    assert.match(await page.locator('#people-rows [data-actor-id="a_jo"] .person-name').innerText(), /Jo \(you\)/);
    assert.match(await page.locator('#people-rows [data-actor-id="a_jo"] .person-time').innerText(), /^\d\d:\d\d$/);
    assert.equal(await page.locator('#people-rows [data-actor-id="a_ali"] .person-time').innerText(), "not yet");
    assert.deepEqual(await page.locator('#people-rows [data-actor-id="a_sam"] .person-actions button').allInnerTexts(), ["Make facilitator", "Remove"]);
    assert.deepEqual(await page.locator('#people-rows [data-actor-id="a_jo"] .person-actions button').allInnerTexts(), ["Withdraw agreement"]);
    assert(await page.locator("#invite-section").isVisible());
    await page.evaluate(() => {
      document.getElementById("invite-code").textContent = "sess.1.9f2c4e7a1b3d5f60c8e2a4b6d8f0a1c3e5";
      document.getElementById("invite-created").hidden = false;
    });
    assert.equal(await page.locator("#invite-code").evaluate(el => getComputedStyle(el).backgroundColor),
      await token(page, "background-color", "var(--paper)"), "the invitation code is on paper");
    assert.match(await page.locator("#speaker-list").innerText(), /Ali · Test profile/);
    if (width === 1920) await page.locator(".ws-rail").screenshot({ path: resolve(output, "p3-rail-people.png") });

    // ---- Empty queue: the one sentence.
    await page.click('[data-rail="review"]');
    await page.evaluate(() => {
      const { app, render } = window.railTest;
      for (const r of app.snapshot.records) if (r.kind === "proposal" || r.kind === "job") r.data.status = r.kind === "job" ? "succeeded" : "rejected";
      app.lastAccepted = null;   // the undo line belongs to an acceptance, not to the queue
      render();
    });
    assert(await page.locator("#queue-empty").isVisible());
    assert.equal(await page.locator("#queue-empty").innerText(), "Evidence first, then the text. Nothing is in the record until it is accepted here.");
    assert.equal(await page.locator("#queue-empty").evaluate(el => getComputedStyle(el).color), await token(page, "color", "var(--ink-2)"));
    assert.equal(await page.locator("#rail-review > :not([hidden])").evaluateAll(els => els.filter(el => el.getBoundingClientRect().height > 0).length), 1,
      "nothing else shows in an empty queue");

    // Keyboard: arrows move between the tabs.
    await page.locator('[data-rail="review"]').focus();
    await page.keyboard.press("ArrowRight");
    assert.equal(await page.locator('[data-rail="transcript"]').getAttribute("aria-selected"), "true");

    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `no horizontal overflow at ${width}px`);
    assert.deepEqual(errors, []);
    assert.deepEqual(failedRequests, []);
    await page.close();
    console.log(`PASS: review cards, correction, transcript colours and quoting, people rows, empty queue at ${width}px.`);
  }
} finally {
  await browser?.close();
  server.kill();
}
