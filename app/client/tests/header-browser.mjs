/**
 * The header and the capture banner, in a real browser against the real
 * server.
 *
 * It drives the session the way a facilitator does, so the chip is checked
 * after app.mjs's own render and header.mjs's render on top of it: Not
 * started, Session open, Listening with the bars and the timer (a fake
 * microphone), the keep-alive countdown after the screen went offline and
 * came back, its last minute (the page's clock is moved forward; the
 * server's is not), Paused with the reason and Resume capture, and Ended.
 * Also: the participant line, the header's 56px row and the 40px banner,
 * that nothing in the header animates but the bars, that People opens from
 * the keyboard, no horizontal overflow, and no console errors, at 1920 by
 * 1080 and at 400px.
 *
 *     node tests/header-browser.mjs
 *
 * HEADER_SCREENSHOT=path writes the 1920px header, listening above paused,
 * as one image; without it the image goes to .local/header-ui/header.png.
 */
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createRequire } from "node:module";
import { mkdirSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");
const CLIENT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const SERVER = resolve(CLIENT, "../server");
const OUTPUT = resolve(CLIENT, "../../.local/header-ui");
mkdirSync(OUTPUT, { recursive: true });
const STATIC_PORT = 5263, API_PORT = 3263;
const python = process.env.JARVAIDS_TEST_PYTHON || "python3";

const data = mkdtempSync(join(tmpdir(), "jarvaids-header-"));
const children = [
  spawn(python, ["serve.py", "--port", String(STATIC_PORT)], { cwd: CLIENT, stdio: "ignore" }),
  spawn(python, ["-m", "genai_server", "--port", String(API_PORT), "--data-dir", data,
    "--allow-origin", `http://127.0.0.1:${STATIC_PORT}`], { cwd: SERVER, stdio: "ignore" }),
];
for (const child of children) child.on("error", error => { throw error; });

const ready = async url => {
  for (let i = 0; i < 80; i++) {
    try { const r = await fetch(url); await r.arrayBuffer(); if (r.ok) return; } catch {}
    await new Promise(r => setTimeout(r, 150));
  }
  throw new Error("server never became ready: " + url);
};

let browser;
try {
  await ready(`http://127.0.0.1:${STATIC_PORT}/client/index.html`);
  await ready(`http://127.0.0.1:${API_PORT}/health`);
  browser = await chromium.launch({ headless: true,
    ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}),
    args: ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"] });

  const shots = {};
  for (const [width, height] of [[1920, 1080], [400, 860]]) {
    const desk = width >= 1024;
    const context = await browser.newContext({ viewport: { width, height } });
    await context.grantPermissions(["microphone"]);
    const page = await context.newPage();
    const errors = [], failed = [];
    let offline = false;
    page.on("pageerror", error => errors.push(error.message));
    page.on("console", message => { if (message.type() === "error" && !offline) errors.push(message.text()); });
    page.on("requestfailed", request => {
      // A read the sync library cancels on purpose is not a failure (as the
      // journey); nor is anything while the test has the network off.
      if (offline || request.url().startsWith("blob:")) return;
      if (request.method() === "GET" && /ERR_ABORTED/.test(request.failure()?.errorText ?? "")) return;
      failed.push(request.url());
    });
    // The page's clock runs at its natural pace until the test moves it.
    await page.clock.install();
    await page.goto(`http://127.0.0.1:${STATIC_PORT}/client/`, { waitUntil: "networkidle" });
    await page.click(".advanced summary");
    await page.fill("#base-url", `http://127.0.0.1:${API_PORT}`);

    const probe = (property, value) => page.evaluate(([property, value]) => {
      const el = document.createElement("i");
      el.style.setProperty(property, value);
      document.getElementById("bar").append(el);   // inside the header, where its local names apply
      const out = getComputedStyle(el).getPropertyValue(property);
      el.remove();
      return out;
    }, [property, value]);
    const chip = () => page.evaluate(() => {
      const box = document.getElementById("session-status");
      return { text: box.innerText.replace(/\s+/g, " ").trim(), className: box.className,
        word: document.getElementById("state-word").textContent,
        background: getComputedStyle(box).backgroundColor,
        bars: !document.getElementById("state-bars").hidden };
    });
    const waitWord = word => page.waitForFunction(w => document.getElementById("state-word").textContent === w, word, { timeout: 10000 });
    const banner = () => page.evaluate(() => {
      const b = document.getElementById("capture-banner");
      return { hidden: b.hidden || b.offsetParent === null, state: b.dataset.state, urgent: b.classList.contains("is-urgent"),
        background: getComputedStyle(b).backgroundColor, height: b.offsetHeight, text: b.innerText.replace(/\s+/g, " ").trim() };
    });
    const noOverflow = async label => assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
      `no horizontal overflow at ${width}px: ${label}`);
    // Only the listening bars may move: every running animation in the
    // header must belong to them. A transition (a hover settling, a button
    // being disabled) is a change finishing, not motion, so it is not counted.
    const headerAnimations = () => page.evaluate(() => document.getAnimations()
      .filter(a => a instanceof CSSAnimation && a.playState === "running" && a.effect?.target?.closest?.("#bar"))
      .map(a => a.effect.target.closest("#state-bars") ? "bars" : (a.effect.target.id || a.effect.target.className || "?")));

    // ---- Not started: the bar shows on the agreement screen
    await page.click("#create");
    await page.waitForSelector("#bar:not([hidden])", { timeout: 10000 });
    await waitWord("Not started");
    let c = await chip();
    assert.match(c.className, /\bchip-idle\b/);
    assert.equal(c.text, "Not started");
    assert.equal(c.bars, false);
    assert.match(await page.innerText("#bar-members"), /waiting for Facilitator/);
    assert.equal(await page.locator("#bar-members .person-dot").count(), 1);
    assert.equal(await page.innerText("#bar-members .person-dot"), "F");
    assert.equal(await page.$eval("#bar-members .person-dot", el => getComputedStyle(el).backgroundColor),
      await probe("color", "var(--person-1)"), "the first person to join takes --person-1");
    assert.equal((await banner()).hidden, true, "no capture banner before capture");

    // ---- Session open
    await page.check("#agree-check");
    await page.click("#acknowledge");
    await page.waitForFunction(() => /everyone agreed/.test(document.getElementById("bar-members").innerText), null, { timeout: 8000 });
    await page.waitForFunction(() => !document.getElementById("activate").disabled, null, { timeout: 8000 });
    await page.click("#activate");
    await waitWord("Session open");
    await page.waitForSelector("#screen-workspace:not([hidden])", { timeout: 5000 });
    c = await chip();
    assert.equal(c.text, "Session open");
    assert.match(c.className, /\bchip-open\b/);
    assert.equal(c.background, await probe("color", "var(--mint-soft)"));
    assert.equal(await page.isVisible("#listen-status"), false, "no timer while no microphone is on");
    assert.equal(c.bars, false);
    assert.equal((await banner()).hidden, true);
    assert.deepEqual(await headerAnimations(), [], "nothing in the header moves while not listening");
    if (desk) {
      assert.equal(await page.$eval(".bar-row", el => el.offsetHeight), 56, "the header row is 56px");
      for (const id of ["bar-title", "session-status", "bar-members", "open-photo", "listen", "stop-capture", "session-menu-button"]) {
        const box = await page.locator("#" + id).boundingBox();
        assert.ok(box && box.y >= 0 && box.y + box.height <= 56, `${id} sits inside the 56px row`);
      }
      assert.equal(await page.$eval("#bar-title", el => el.tagName), "H1");
      assert.equal(await page.$eval("#bar-title", el => getComputedStyle(el).fontSize), await probe("font-size", "var(--fs-title)"));
      assert.equal(await page.$$eval(".bar-actions .btn-primary", els => els.filter(e => e.offsetParent).map(e => e.id).join()), "open-photo",
        "Photograph the wall is the only filled primary");
    }
    await noOverflow("open");

    // ---- the participant line opens People, from the keyboard
    await page.focus("#bar-members");
    await page.keyboard.press("Enter");
    await page.waitForSelector("#rail-people:not([hidden])", { timeout: 3000 });
    await page.click('[data-rail="review"]');

    // ---- Listening, with the bars and the timer
    await page.click("#listen");
    await page.waitForSelector("#listen-status:not([hidden])", { timeout: 5000 });
    await waitWord("Listening");
    await page.waitForFunction(() => document.getElementById("listen-timer").textContent !== "00:00", null, { timeout: 5000 });
    c = await chip();
    assert.match(c.text, /^Listening \d\d:\d\d$/, c.text);
    assert.match(c.className, /\bchip-listening\b/);
    assert.equal(c.background, await probe("color", "var(--ink)"));
    assert.equal(c.bars, true);
    assert.equal(await page.textContent("#listen"), "Stop listening");
    const moving = await headerAnimations();
    assert.ok(moving.length > 0 && moving.every(m => m === "bars"), `only the bars move: ${moving}`);
    assert.equal(await page.textContent("#state-announce"), "Listening", "the change is announced once");
    if (desk) shots.listening = await page.locator("#bar").screenshot();
    await noOverflow("listening");
    await page.click("#listen");
    await page.waitForSelector("#listen-status[hidden]", { state: "attached", timeout: 5000 });
    await waitWord("Session open");
    assert.equal((await chip()).bars, false);
    assert.equal(await page.textContent("#listen"), "Listen");

    // ---- keep-alive: the screen went offline and came back, so renewing
    // is the facilitator's choice, with a countdown from the activation
    offline = true;
    await context.setOffline(true);
    await page.waitForTimeout(400);
    await context.setOffline(false);
    await page.waitForSelector("#keepalive-banner:not([hidden])", { timeout: 10000 });
    offline = false;
    let b = await banner();
    assert.equal(b.hidden, false);
    assert.equal(b.state, "keepalive");
    assert.match(b.text, /^Capture pauses itself in [0-4]:\d\d unless a facilitator keeps it running\. Keep capture running$/, b.text);
    assert.equal(b.urgent, false);
    assert.equal(b.background, await probe("color", "var(--paper-2)"));
    if (desk) assert.equal(b.height, 40, "the banner is 40px");
    // The last minute: the page's clock jumps 4 minutes 30 seconds.
    await page.clock.fastForward("04:30");
    await page.waitForFunction(() => document.getElementById("capture-banner").classList.contains("is-urgent"), null, { timeout: 5000 });
    b = await banner();
    assert.match(b.text, /Capture (pauses itself in 0:\d\d|is due to pause now)/, b.text);
    assert.equal(b.background, await probe("color", "var(--yellow-soft)"), "yellow-soft under a minute");
    await page.click("#keep-alive");
    await page.waitForSelector("#keepalive-banner[hidden]", { state: "attached", timeout: 5000 });
    assert.equal((await banner()).hidden, true);
    // Clear the offline notice the attention banner holds, so it does not
    // sit in the screenshot.
    if (await page.isVisible("#attention")) await page.click("#attention-dismiss");

    // ---- Paused, with the reason and Resume capture
    await page.click("#stop-capture");
    await waitWord("Paused");
    await page.waitForSelector("#paused-banner:not([hidden])", { timeout: 5000 });
    c = await chip();
    assert.equal(c.text, "Paused");
    assert.match(c.className, /\bchip-paused\b/);
    assert.equal(c.background, await probe("color", "var(--yellow-soft)"));
    b = await banner();
    assert.equal(b.state, "paused");
    assert.equal(b.text, "Nothing new is being recorded. The canvas and review still work. Resume capture");
    assert.equal(b.background, await probe("color", "var(--paper-2)"));
    assert.deepEqual(await headerAnimations(), [], "nothing moves while paused");
    if (desk) {
      assert.equal(b.height, 40);
      shots.paused = await page.locator("#bar").screenshot();
    }
    await page.screenshot({ path: resolve(OUTPUT, `paused-${width}.png`) });
    await noOverflow("paused");

    // ---- Resume, then End: Ended
    await page.click("#resume");
    await waitWord("Session open");
    await page.waitForSelector("#paused-banner[hidden]", { state: "attached", timeout: 5000 });
    await page.click("#session-menu-button");
    await page.click("#end-session");
    await page.click("#confirm-ok");
    await waitWord("Ended");
    await page.waitForSelector("#ended-banner:not([hidden])", { timeout: 5000 });
    c = await chip();
    assert.match(c.className, /\bchip-ended\b/);
    assert.equal(c.background, await probe("color", "var(--paper-2)"));
    b = await banner();
    assert.equal(b.state, "ended");
    assert.match(b.text, /^This session has ended\. The canvas can still be read and exported until /);
    await noOverflow("ended");

    // ---- the attention banner: a quiet line with a coloured mark
    await page.evaluate(() => {
      const a = document.getElementById("attention");
      a.dataset.kind = "problem"; a.hidden = false;
      document.getElementById("attention-text").textContent = "A test problem.";
    });
    const mark = kind => page.evaluate(k => {
      document.getElementById("attention").dataset.kind = k;
      return getComputedStyle(document.getElementById("attention-glyph")).backgroundColor;
    }, kind);
    assert.equal(await mark("problem"), await probe("color", "var(--coral)"));
    assert.equal(await mark("note"), await probe("color", "var(--mint)"));
    const dismiss = await page.locator("#attention-dismiss").boundingBox();
    const line = await page.locator("#attention").boundingBox();
    assert.ok(dismiss.x + dismiss.width > line.x + line.width - 2, "Dismiss sits on the right");
    await page.click("#attention-dismiss");
    assert.equal(await page.isVisible("#attention"), false);

    assert.deepEqual(errors, [], "no console errors");
    assert.deepEqual(failed, [], "no failed requests");
    await context.close();
    console.log(`PASS: header chip in every state, the participant line, the capture banner (keep-alive countdown, urgent, ` +
      `paused, ended), the attention mark, only the bars moving, no overflow and no console errors at ${width}px.`);
  }

  // One image: the 1920px header listening, above it paused.
  const page = await browser.newPage({ viewport: { width: 1920, height: 400 } });
  const img = buf => `<img style="display:block;margin:0 0 16px" src="data:image/png;base64,${buf.toString("base64")}">`;
  await page.setContent(`<body style="margin:0;background:white">${img(shots.listening)}${img(shots.paused)}</body>`);
  const out = process.env.HEADER_SCREENSHOT || resolve(OUTPUT, "header.png");
  await page.screenshot({ path: out, fullPage: true });
  console.log("Screenshot: " + out);
} finally {
  await browser?.close();
  for (const child of children) { try { child.kill(); } catch {} }
  // Windows may still hold the database for a moment after the kill.
  try { rmSync(data, { recursive: true, force: true }); } catch {}
}
