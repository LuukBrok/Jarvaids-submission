/**
 * The session strip in a real browser, from a fixture.
 *
 * Like canvas-objects-browser.mjs, this injects a snapshot into a fresh
 * Board and a fresh strip on the real page: it proves the drawing and the
 * scrubbing, not the commands. The fixture holds two photographs, three
 * accepted notes at different times, a pen stroke, a recognised command, a
 * proposal and one quote link. It checks the marks and their looks, the
 * words on hover, scrubbing with the pointer and with the keys, that
 * `after-moment` lands on exactly what was made after the moment and clears
 * on release, Escape, End and blur, that a board redraw keeps the classes,
 * the quiet control, that nothing in the strip animates, no console errors
 * and no horizontal overflow, at 1920 by 1080 and at 400px.
 *
 *     node tests/strip-browser.mjs
 *
 * STRIP_SCREENSHOT=path saves the 1920px canvas and strip, open and
 * scrubbing; both widths always go to .local/strip-ui/.
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
const output = resolve(client, "../../.local/strip-ui");
mkdirSync(output, { recursive: true });
const port = Number(process.env.STRIP_PORT || 5243);
const server = spawn(process.env.JARVAIDS_TEST_PYTHON || "python3",
  ["serve.py", "--port", String(port)], { cwd: client, stdio: "ignore" });
server.on("error", error => { throw error; });

const T0 = Math.floor(Date.now() / 1000) - 900;   // fifteen minutes ago
const placed = (x, y) => ({ x, y, revision: 1, hand_placed: true });
const accepted = (id, text, at, x, y) => ({ id, kind: "item", revision: 1, position: placed(x, y),
  data: { item_kind: "content", status: "accepted", origin: "human", text, accepted_by: "a1", author_id: "a1", refs: [], created_at: T0 + at } });
const FIXTURE = {
  session: { id: "s1", title: "Wall review", state: "active" },
  actor_id: "a1",
  members: [{ id: "a1", name: "Sanne", role: "facilitator" }],
  records: [
    { id: "photo-1", kind: "source", revision: 1, data: { type: "image", regions: [], created_at: T0 + 10 } },
    accepted("n1", "Onboarding loses people at step two", 60, 0, 0),
    { id: "photo-2", kind: "source", revision: 1, data: { type: "image", regions: [], created_at: T0 + 200 } },
    accepted("n2", "Too many fields", 300, 340, 0),
    { id: "pen", kind: "item", revision: 1, position: placed(680, 40), data: { item_kind: "stroke", status: "accepted", origin: "human",
      made_by_hand: true, author_id: "a1", tone: "ink", weight: "regular", points: [[0, 0], [40, 20], [80, 0], [120, 24]], created_at: T0 + 350 } },
    { id: "seg-cmd", kind: "transcript_segment", revision: 1, data: { status: "final", text: "Hey Jarvaids, make a summary",
      voice_command: { status: "recognised", intent: "summary" }, created_at: T0 + 400 } },
    { id: "p1", kind: "proposal", revision: 1, position: placed(340, 220), data: { proposal_kind: "content", status: "needs_review",
      origin: "model", provider: "claude", model: "m", text: "Run a test with five people", refs: [], created_at: T0 + 450 } },
    accepted("n3", "People skip the tour", 500, 0, 220),
  ],
};
FIXTURE.board_order = FIXTURE.records.map(r => r.id);
const LINKS = { n1: { segmentId: "seg-quoted", time: T0 + 60 } };

let browser;
try {
  for (let attempt = 0; ; attempt++) {
    if (server.exitCode != null) throw new Error(`The static server on ${port} exited; is the port in use? Set STRIP_PORT.`);
    try { const r = await fetch(`http://127.0.0.1:${port}/client/`); await r.arrayBuffer(); if (r.ok) break; } catch {}
    if (attempt >= 80) throw new Error("Static server did not start.");
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  browser = await chromium.launch({ headless: true,
    ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}) });
  for (const [width, height] of [[1920, 1080], [400, 860]]) {
    const page = await browser.newPage({ viewport: { width, height } });
    const errors = [], failedRequests = [];
    page.on("pageerror", error => errors.push(error.message));
    page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
    page.on("requestfailed", request => failedRequests.push(request.url()));
    page.on("response", response => { if (response.status() >= 400) failedRequests.push(response.url()); });
    await page.goto(`http://127.0.0.1:${port}/client/`);
    await page.evaluate(async ([fixture, links]) => {
      localStorage.setItem("jv.quotes.links", JSON.stringify(links));
      document.getElementById("screen-setup").hidden = true;
      document.getElementById("screen-workspace").hidden = false;
      // A fresh board and a fresh strip on the real elements: the app's own
      // have no session behind them here, and cloning drops their listeners.
      for (const id of ["board", "session-strip"]) {
        const old = document.getElementById(id);
        old.replaceWith(old.cloneNode(false));
      }
      const { Board } = await import("/client/board.mjs");
      const { createStrip } = await import("/client/tools/strip.mjs");
      const board = new Board(document.getElementById("board"), {
        send: async () => {}, review: () => {}, attention: () => {}, onSelection: () => {}, crop: async () => "", revoke: () => {},
      });
      const ctx = {
        app: { screen: "workspace", view: "canvas", board }, board,
        $: id => document.getElementById(id), show: (el, on) => { if (el) el.hidden = !on; },
        clock: s => new Date(s * 1000).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", hour12: false }),
      };
      const strip = createStrip();
      strip.mount(ctx);
      // As app.mjs does: the board first, then the tools.
      window.redraw = () => { board.render(fixture); strip.render(ctx, fixture); };
      window.redraw();
      Object.assign(window, { testBoard: board, testStrip: strip, ctx, fixture });
    }, [FIXTURE, LINKS]);

    const clock = s => page.evaluate(s => window.ctx.clock(s), s);
    const count = selector => page.locator(selector).count();
    const faded = () => page.$$eval(".after-moment", els => els.map(el => el.dataset.id ?? el.getAttribute("data-id")).sort());
    const gone = () => page.$$eval(".after-moment-proposal", els => els.map(el => el.dataset.id).sort());
    const stripBox = () => page.locator("#session-strip").boundingBox();
    const markCentre = async key => {
      const b = await page.locator(`.strip-mark[data-key="${key}"]`).boundingBox();
      return [b.x + b.width / 2, b.y + b.height / 2];
    };

    // ---- the strip and its marks
    assert.equal(await page.locator("#session-strip").isVisible(), true, "the strip is shown in the workspace");
    assert.equal(Math.round((await stripBox()).height), 40, "closed, it is --strip-h tall");
    assert.equal(await count(".strip-mark-photo"), 2, "two photographs");
    assert.equal(await count(".strip-mark-accept"), 3, "three accepts");
    assert.equal(await count(".strip-mark-command"), 1, "one recognised command");
    assert.equal(await count(".strip-mark-quote"), 1, "one quote, from jv.quotes.links");
    const size = key => page.$eval(`.strip-mark[data-key="${key}"]`, el => {
      const cs = getComputedStyle(el); return [el.offsetWidth, el.offsetHeight, cs.borderRadius];
    });
    assert.deepEqual((await size("photo:photo-1")).slice(0, 2), [8, 8], "a photograph is an 8px square");
    assert.deepEqual((await size("accept:n1")).slice(0, 2), [8, 8], "an accept is an 8px circle");
    assert.notEqual((await size("accept:n1"))[2], "0px");
    assert.deepEqual((await size("command:seg-cmd")).slice(0, 2), [3, 12], "a command is a 3 by 12 bar");
    assert.deepEqual((await size("quote:n1")).slice(0, 2), [2, 10], "a quote is a 2 by 10 line");
    const colour = await page.evaluate(() => [getComputedStyle(document.querySelector('.strip-mark[data-key="accept:n2"]')).backgroundColor,
      getComputedStyle(document.querySelector('.note[data-id="n2"]')).backgroundColor]);
    assert.equal(colour[0], colour[1], "an accept's mark is the note's own colour");
    const order = await page.$$eval(".strip-mark", els => els.map(el => [el.dataset.key, el.getBoundingClientRect().x]));
    const xs = Object.fromEntries(order);
    assert.ok(xs["photo:photo-1"] < xs["accept:n1"] && xs["accept:n1"] < xs["photo:photo-2"] && xs["photo:photo-2"] < xs["accept:n2"] &&
      xs["accept:n2"] < xs["command:seg-cmd"] && xs["command:seg-cmd"] < xs["accept:n3"], "marks run in time order, left to right");
    assert.equal(await page.textContent(".strip-start"), await clock(T0 + 10), "the first moment's time at the left end");
    const slider = page.locator('#session-strip [role="slider"]');
    assert.match(await slider.getAttribute("aria-valuetext"), /^Now, \d\d:\d\d$/);
    assert.deepEqual(await faded(), [], "nothing faded at now");

    // ---- hover: a moment's words over its mark, inside the page
    await page.mouse.move(...await markCentre("photo:photo-1"));
    assert.equal(await page.locator(".strip-tip").isVisible(), true);
    assert.equal(await page.textContent(".strip-tip"), `Photograph · ${await clock(T0 + 10)}`);
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), "a tip at the left end does not overflow");
    await page.mouse.move(...await markCentre("command:seg-cmd"));
    assert.equal(await page.textContent(".strip-tip"), `Command · summary · ${await clock(T0 + 400)}`);
    await page.mouse.move(...await markCentre("accept:n3"));
    assert.equal(await page.textContent(".strip-tip"), `Accepted · People skip the tour · ${await clock(T0 + 500)}`);
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), "nor at the right end");
    await page.mouse.move(5, 5);
    assert.equal(await page.locator(".strip-tip").isVisible(), false, "leaving the strip hides the words");

    // ---- scrubbing with the pointer
    const [ax] = await markCentre("accept:n1"), [bx] = await markCentre("photo:photo-2");
    const y = (await stripBox()).y + 20;
    await page.mouse.move((ax + bx) / 2, y);
    await page.mouse.down();
    assert.equal(Math.round((await stripBox()).height), 96, "a press opens the strip to --strip-h-open");
    assert.deepEqual(await page.evaluate(() => [document.activeElement?.matches(".strip-axis"), document.activeElement?.matches(":focus-visible")]),
      [true, false], "a press focuses the slider without the keyboard's focus ring");
    assert.deepEqual(await faded(), ["n2", "n3", "p1", "pen"], "after a moment between n1 and the second photograph");
    assert.deepEqual(await gone(), ["p1"], "the later proposal is not shown");
    const look = id => page.$eval(`#board [data-id="${id}"]`, el => {
      const cs = getComputedStyle(el); return { opacity: cs.opacity, events: cs.pointerEvents, visibility: cs.visibility };
    });
    assert.deepEqual(await look("n2"), { opacity: "0.2", events: "none", visibility: "visible" }, "a later note fades to 20 percent");
    assert.equal((await look("pen")).opacity, "0.2", "a later stroke fades too");
    assert.equal((await look("p1")).visibility, "hidden");
    assert.deepEqual(await look("n1"), { opacity: "1", events: "auto", visibility: "visible" }, "an earlier note is untouched");
    assert.equal(await page.locator(".strip-cursor").isVisible(), true, "the cursor shows");
    const cursorTime = await page.textContent(".strip-cursor-time");
    assert.match(cursorTime, /^\d\d:\d\d$/);
    assert.equal(await slider.getAttribute("aria-valuetext"), cursorTime, "between moments the slider says the time");
    // Paper to the right of the cursor, the sunken ground to its left.
    const grounds = await page.evaluate(() => {
      const strip = document.getElementById("session-strip"), future = strip.querySelector(".strip-future");
      const cursor = strip.querySelector(".strip-cursor").getBoundingClientRect();
      return { strip: getComputedStyle(strip).backgroundColor, future: getComputedStyle(future).backgroundColor,
        futureLeft: future.getBoundingClientRect().left, cursorMid: cursor.left + cursor.width / 2,
        paper: getComputedStyle(document.body).backgroundColor };
    });
    assert.equal(grounds.future, grounds.paper, "--paper right of the cursor");
    assert.notEqual(grounds.strip, grounds.paper, "--paper-2 left of it");
    assert.ok(Math.abs(grounds.futureLeft - grounds.cursorMid) < 1.5, JSON.stringify(grounds));
    // Drag onto the second accept: it snaps to the moment and shows its words.
    await page.mouse.move(...[(await markCentre("accept:n2"))[0] + 3, y], { steps: 5 });
    assert.deepEqual(await faded(), ["n3", "p1", "pen"], "at n2's acceptance n2 is already there");
    assert.equal(await page.textContent(".strip-tip"), `Accepted · Too many fields · ${await clock(T0 + 300)}`);
    assert.equal(await slider.getAttribute("aria-valuetext"), `Accepted · Too many fields · ${await clock(T0 + 300)}`);
    assert.equal(await page.evaluate(() => document.getAnimations().filter(a => a.effect?.target?.closest?.("#session-strip, .after-moment")).length), 0,
      "nothing in the strip, or on what it fades, animates");
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), "no horizontal overflow while scrubbing");
    if (width === 1920) {
      const b = await page.locator("#board").boundingBox(), s = await stripBox();
      const clip = { x: b.x, y: b.y, width: b.width, height: s.y + s.height - b.y + 8 };
      await page.screenshot({ path: resolve(output, "strip-scrubbing-1920.png"), clip });
      if (process.env.STRIP_SCREENSHOT) await page.screenshot({ path: process.env.STRIP_SCREENSHOT, clip });
    } else {
      await page.locator("#session-strip").screenshot({ path: resolve(output, `strip-scrubbing-${width}.png`) });
    }
    // A redraw while the pointer is down keeps the classes.
    await page.evaluate(() => window.redraw());
    assert.deepEqual(await faded(), ["n3", "p1", "pen"], "reapplied after a render");
    await page.mouse.up();
    assert.deepEqual(await faded(), [], "releasing returns to now");
    assert.deepEqual(await gone(), []);
    assert.equal(await page.locator(".strip-cursor").isVisible(), false);
    assert.equal(await page.evaluate(() => window.testStrip.place), null);
    assert.equal((await look("p1")).visibility, "visible");

    // ---- scrubbing with the keys
    await slider.focus();
    assert.equal(Math.round((await stripBox()).height), 96, "focus opens the strip");
    await page.keyboard.press("Home");
    assert.equal(await slider.getAttribute("aria-valuetext"), `Photograph · ${await clock(T0 + 10)}`, "Home: the first moment");
    assert.deepEqual(await faded(), ["n1", "n2", "n3", "p1", "pen"]);
    await page.keyboard.press("ArrowRight");
    assert.equal(await slider.getAttribute("aria-valuetext"), `Accepted · Onboarding loses people at step two · ${await clock(T0 + 60)}`);
    assert.deepEqual(await faded(), ["n2", "n3", "p1", "pen"]);
    await page.keyboard.press("ArrowRight");
    assert.equal(await slider.getAttribute("aria-valuetext"), `Quote · ${await clock(T0 + 60)}`, "a quote at the same second is its own step");
    await page.keyboard.press("ArrowRight");
    assert.equal(await slider.getAttribute("aria-valuetext"), `Photograph · ${await clock(T0 + 200)}`);
    await page.keyboard.press("Escape");
    assert.deepEqual(await faded(), [], "Escape returns to now");
    assert.match(await slider.getAttribute("aria-valuetext"), /^Now, /);
    await page.keyboard.press("ArrowLeft");
    assert.equal(await slider.getAttribute("aria-valuetext"), `Accepted · People skip the tour · ${await clock(T0 + 500)}`, "back from now: the newest");
    assert.deepEqual(await faded(), []);
    await page.keyboard.press("ArrowDown");
    assert.equal(await slider.getAttribute("aria-valuetext"), `Command · summary · ${await clock(T0 + 400)}`);
    assert.deepEqual(await faded(), ["n3", "p1"]);
    assert.equal(await slider.getAttribute("aria-valuenow"), String(T0 + 400));
    // The board redrawing on its own (details, a crop) keeps the classes.
    await page.evaluate(() => window.testBoard.render(window.fixture));
    await page.waitForFunction(() => document.querySelector('.note[data-id="n3"]')?.classList.contains("after-moment"), null, { timeout: 2000 });
    assert.deepEqual(await faded(), ["n3", "p1"], "reapplied after the board redrew alone");
    await page.keyboard.press("End");
    assert.deepEqual(await faded(), [], "End returns to now");
    await page.keyboard.press("ArrowLeft");
    await page.keyboard.press("ArrowLeft");
    assert.deepEqual(await faded(), ["n3", "p1"]);
    await page.evaluate(() => document.activeElement.blur());
    assert.deepEqual(await faded(), [], "leaving the strip returns to now");
    assert.equal(Math.round((await stripBox()).height), 40, "and closes it");

    // ---- the quiet control pins it open, and closes it again
    const toggle = page.locator(".strip-toggle");
    assert.equal(await toggle.getAttribute("aria-expanded"), "false");
    await toggle.click();
    assert.equal(await toggle.getAttribute("aria-expanded"), "true");
    assert.equal(Math.round((await stripBox()).height), 96);
    assert.equal(await page.locator(".strip-lane-command").isVisible(), true, "open, the lanes are named");
    await toggle.click();
    assert.equal(Math.round((await stripBox()).height), 40, "closed again, even with the control focused");
    assert.deepEqual(await faded(), [], "the control scrubs nothing");

    // ---- reduced motion: still nothing animates, and it all still works
    // The control's own hover transition (a primitive's, before the switch)
    // finishes first, so what is measured is what happens under reduce.
    await page.mouse.move(5, 5);
    await page.waitForFunction(() => document.getAnimations().length === 0, null, { timeout: 3000 });
    await page.emulateMedia({ reducedMotion: "reduce" });
    await slider.focus();
    await page.keyboard.press("Home");
    assert.deepEqual(await faded(), ["n1", "n2", "n3", "p1", "pen"]);
    const running = await page.evaluate(() => document.getAnimations().filter(a => a.playState === "running")
      .map(a => `${a.constructor.name} ${a.animationName ?? a.transitionProperty} on ${a.effect?.target?.className}`));
    assert.deepEqual(running, [], "no animation anywhere on the page");
    await page.keyboard.press("End");
    await page.emulateMedia({ reducedMotion: null });

    // ---- the list view hides the strip
    await page.evaluate(() => { window.ctx.app.view = "list"; window.redraw(); });
    assert.equal(await page.locator("#session-strip").isVisible(), false, "the strip belongs to the canvas");
    await page.evaluate(() => { window.ctx.app.view = "canvas"; window.redraw(); });

    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), "No horizontal overflow.");
    assert.deepEqual(errors, []);
    assert.deepEqual(failedRequests, []);
    await page.close();
    console.log(`PASS: marks, hover words, pointer and key scrubbing, after-moment on exactly the later records and cleared on release, ` +
      `Escape, End and blur, kept through redraws, the quiet control, no motion, at ${width}px.`);
  }
} finally {
  await browser?.close();
  server.kill();
}
