/**
 * The Jarvaids menu, the "What you can say" sheet and the collecting chip,
 * in a real browser against the real server in the automatic workspace,
 * with the scripted providers of tests/automatic_browser_server.py (no
 * model output is claimed; the to-do list's interpretation is scripted).
 *
 * Checks: the menu opens from the button and from the keyboard (arrows,
 * Home, End, Escape giving focus back), the commands are unavailable with a
 * reason before capture runs, the four recognised-only rows are listed,
 * unavailable and send nothing, the sheet shows eight groups of three
 * phrases at the header's Body size and closes with Escape, choosing
 * "To-do list" creates a to-do list in the session through the typed route
 * (a typed transcript segment with the addressed words), the chip then says
 * "Collecting: to-do" and pressing it brings the card back into view, the
 * chip leaves and the commands become unavailable while paused. Also: the
 * Session menu closes when the Jarvaids menu opens, Photograph the wall is
 * still the only filled primary, no horizontal overflow and no console
 * errors, at 1440px and 400px.
 *
 *     node tests/command-menu-browser.mjs
 */
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
const data = mkdtempSync(join(tmpdir(), "jv-command-menu-")), children = [];
const output = resolve(root, ".local/command-menu-ui"); mkdirSync(output, { recursive: true });
const staticPort = 5191, apiPort = 3091;
let browser;

function launch(args, cwd) {
  const child = spawn(python, args, { cwd, stdio: ["ignore", "pipe", "pipe"] });
  child.on("error", e => { throw e; });
  child.stderr.on("data", d => { if (process.env.VERBOSE) console.error(String(d)); });
  children.push(child);
}
async function ready(url) {
  for (let i = 0; i < 100; i++) {
    try { const response = await fetch(url); await response.arrayBuffer(); if (response.ok) return; } catch {}
    await new Promise(r => setTimeout(r, 100));
  }
  throw new Error(`Server did not start: ${url}`);
}

try {
  launch(["serve.py", "--port", String(staticPort)], resolve(root, "app/client"));
  launch(["-m", "tests.automatic_browser_server", "--port", String(apiPort), "--data-dir", data,
    "--origin", `http://127.0.0.1:${staticPort}`], resolve(root, "app/server"));
  await ready(`http://127.0.0.1:${staticPort}/client/`); await ready(`http://127.0.0.1:${apiPort}/health`);
  browser = await chromium.launch({ headless: true, ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}) });

  for (const [width, height] of [[1440, 1000], [400, 900]]) {
    const desk = width >= 1024;
    const page = await browser.newPage({ viewport: { width, height } });
    const errors = [], failures = [];
    page.on("pageerror", e => errors.push(e.message));
    page.on("console", m => { if (m.type() === "error") errors.push(m.text()); });
    page.on("requestfailed", r => {
      if (r.method() === "GET" && /ERR_ABORTED/.test(r.failure()?.errorText ?? "")) return;
      failures.push(r.url());
    });
    page.on("response", r => { if (r.status() >= 400) failures.push(`${r.status()} ${r.url()}`); });
    let credentials;
    page.on("request", r => { if (r.url() === `http://127.0.0.1:${apiPort}/api/sessions` && r.method() === "POST") credentials = r.postDataJSON(); });

    const menuShown = () => page.locator("#command-menu").isVisible();
    const focusedText = () => page.evaluate(() => document.activeElement?.textContent.trim());
    const noOverflow = async label => assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
      `no horizontal overflow at ${width}px: ${label}`);
    const probe = (property, value) => page.evaluate(([property, value]) => {
      const el = document.createElement("i");
      el.style.setProperty(property, value);
      document.getElementById("bar").append(el);
      const out = getComputedStyle(el).getPropertyValue(property);
      el.remove();
      return out;
    }, [property, value]);

    await page.goto(`http://127.0.0.1:${staticPort}/client/`);
    await page.locator(".advanced summary").click();
    await page.locator("#base-url").fill(`http://127.0.0.1:${apiPort}`);
    await page.locator("#create").click();
    await page.waitForSelector("#bar:not([hidden])", { timeout: 10000 });

    // ---- before capture runs (the bar's actions are hidden on the agreement
    // screen): the commands already carry the reason they are unavailable
    await page.waitForFunction(() => document.querySelector('#command-menu [data-command="todo"]').getAttribute("aria-disabled") === "true");
    const todo = page.locator('#command-menu [data-command="todo"]');
    assert.match(await todo.getAttribute("aria-description"), /while capture runs/);
    assert.match(await todo.getAttribute("title"), /while capture runs/);

    await page.locator("#agree-check").check(); await page.locator("#acknowledge").click();
    await page.waitForFunction(() => !document.getElementById("activate").disabled);
    await page.locator("#activate").click();
    await page.waitForFunction(() => !document.getElementById("stop-capture").disabled);
    await page.waitForSelector("#screen-workspace:not([hidden])");
    const client = new GenAIClient({ baseUrl: `http://127.0.0.1:${apiPort}`, sessionId: credentials.session_id, token: credentials.owner_token });
    assert.equal(await page.locator("#collecting-pill").isVisible(), false, "nothing collects yet");

    // ---- the menu from the keyboard
    await page.focus("#command-menu-button");
    await page.keyboard.press("ArrowDown");
    assert.equal(await menuShown(), true);
    assert.equal(await page.getAttribute("#command-menu-button", "aria-expanded"), "true");
    assert.equal(await focusedText(), "Poll", "ArrowDown opens on the first item");
    await page.keyboard.press("ArrowDown");
    assert.equal(await focusedText(), "To-do list");
    await page.keyboard.press("ArrowUp"); await page.keyboard.press("ArrowUp");
    assert.equal(await focusedText(), "What you can say", "ArrowUp wraps to the last item");
    await page.keyboard.press("Home");
    assert.equal(await focusedText(), "Poll");
    await page.keyboard.press("End");
    assert.equal(await focusedText(), "What you can say");
    await page.keyboard.press("Escape");
    assert.equal(await menuShown(), false);
    assert.equal(await page.evaluate(() => document.activeElement?.id), "command-menu-button", "Escape gives focus back");
    assert.equal(await page.getAttribute("#command-menu-button", "aria-expanded"), "false");
    await page.keyboard.press("ArrowUp");
    assert.equal(await focusedText(), "What you can say", "ArrowUp on the button opens on the last item");
    await page.keyboard.press("Escape");

    // ---- the Session menu closes when the Jarvaids menu opens
    await page.locator("#session-menu-button").click();
    assert.equal(await page.locator("#session-menu").isVisible(), true);
    await page.locator("#command-menu-button").click();
    assert.equal(await page.locator("#session-menu").isVisible(), false, "one menu at a time");
    assert.equal(await menuShown(), true);

    // ---- executed items are available; the recognised-only rows are not, and send nothing
    for (const key of ["voting", "todo", "requirements", "planning"])
      assert.equal(await page.locator(`#command-menu [data-command="${key}"]`).getAttribute("aria-disabled"), null, `${key} is available`);
    assert.equal(await page.locator("#command-menu-recognised").innerText(), "Recognised, not yet carried out");
    const recognised = page.locator("#command-menu [data-recognised]");
    assert.deepEqual(await recognised.allInnerTexts(), ["Visualisation", "Comparison", "Suggestions"]);
    for (let i = 0; i < 3; i++) {
      assert.equal(await recognised.nth(i).getAttribute("aria-disabled"), "true");
      assert.match(await recognised.nth(i).getAttribute("aria-description"), /^Recognised, not yet carried out\./);
    }
    const before = (await client.snapshot()).records.length;
    await recognised.first().click({ force: true });   // Playwright treats aria-disabled as not clickable
    assert.equal(await menuShown(), true, "an unavailable row does not close the menu");
    await page.waitForTimeout(300);
    assert.equal((await client.snapshot()).records.length, before, "an unavailable row sends nothing");
    const menuBox = await page.locator("#command-menu").boundingBox();
    assert.ok(menuBox.x >= 0 && menuBox.x + menuBox.width <= width, `the menu opens inside the window at ${width}px`);
    await page.screenshot({ path: resolve(output, `menu-${width}.png`) });
    await noOverflow("menu open");

    // ---- the sheet
    await page.locator("#open-commands").click();
    await page.waitForSelector("#commands-sheet:not([hidden])");
    assert.equal(await menuShown(), false);
    assert.equal(await page.evaluate(() => document.activeElement?.id), "close-commands", "the sheet takes focus");
    const groups = page.locator("#commands-sheet .commands-group");
    assert.equal(await groups.count(), 8);
    for (let i = 0; i < 8; i++) assert.equal(await groups.nth(i).locator("li").count(), 3);
    assert.deepEqual(await page.locator("#commands-sheet .commands-group-title").allInnerTexts(),
      ["Poll", "To-do list", "Requirements and wishes", "Calendar", "Summary", "Visualisation", "Comparison", "Suggestions"]);
    assert.match(await page.locator("#commands-sheet").innerText(), /Recognised, not yet carried out/);
    assert.match(await page.locator("#commands-sheet .commands-lifecycle").innerText(), /close the to do list.*accept the to do list.*reopen the to do list.*cancel the to do list/s);
    const bodySize = parseFloat(await probe("font-size", "var(--fs-body)"));
    const smallest = await page.$$eval("#commands-sheet li, #commands-sheet h3, #commands-sheet h4, #commands-sheet p",
      els => Math.min(...els.map(e => parseFloat(getComputedStyle(e).fontSize))));
    assert.ok(smallest >= bodySize, `nothing on the sheet is smaller than Body (${smallest} < ${bodySize})`);
    await page.waitForTimeout(400);   // the sheet's entrance, before the picture
    await page.screenshot({ path: resolve(output, `sheet-${width}.png`) });
    await noOverflow("sheet open");
    await page.keyboard.press("Escape");
    await page.waitForSelector("#commands-sheet[hidden]", { state: "attached" });
    assert.equal(await page.evaluate(() => document.activeElement?.id), "command-menu-button", "closing gives focus back");

    // ---- choosing To-do list creates a to-do list through the typed route
    await page.locator("#command-menu-button").click();
    await page.locator('#command-menu [data-command="todo"]').click();
    await page.waitForSelector("#board .command-document", { timeout: 10000 });
    let snapshot = await client.snapshot();
    const docs = snapshot.records.filter(r => r.kind === "command_document");
    assert.equal(docs.length, 1);
    assert.equal(docs[0].data.document_type, "todo");
    assert.equal(docs[0].data.state, "collecting");
    const typed = snapshot.records.filter(r => r.kind === "transcript_segment" && r.data.input_method === "typed");
    assert.equal(typed.length, 1);
    assert.equal(typed[0].data.text, "Hey Jarvaids, make a to do list.");
    assert.equal(typed[0].data.voice_command?.intent, "todo");
    assert.equal(typed[0].data.author_id, snapshot.actor_id, "the record says this person asked for it");
    assert.match(await page.locator("#attention-text").innerText(), /^Asked for a to-do list\./);

    // ---- the collecting chip, and pressing it shows the card
    await page.waitForSelector("#collecting-pill:not([hidden])");
    assert.equal(await page.locator("#collecting-words").innerText(), "Collecting: to-do");
    assert.equal(await page.getAttribute("#collecting-pill", "aria-label"), "Collecting: to-do. Show it on the canvas");
    assert.equal(await page.$eval("#collecting-pill", el => getComputedStyle(el).backgroundColor), await probe("color", "var(--periwinkle-soft)"));
    if (desk) {
      assert.equal(await page.$eval(".bar-row", el => el.offsetHeight), 56, "the header row stays 56px with the chip");
      for (const id of ["collecting-pill", "command-menu-button", "session-menu-button", "open-photo"]) {
        const box = await page.locator("#" + id).boundingBox();
        assert.ok(box && box.y >= 0 && box.y + box.height <= 56, `${id} sits inside the 56px row`);
      }
      assert.equal(await page.$$eval(".bar-actions .btn-primary", els => els.filter(e => e.offsetParent).map(e => e.id).join()), "open-photo",
        "Photograph the wall is the only filled primary");
    }
    const card = page.locator("#board .command-document");
    const inView = async () => {
      const [b, c] = [await page.locator("#board").boundingBox(), await card.boundingBox()];
      return c.x < b.x + b.width && c.x + c.width > b.x && c.y < b.y + b.height && c.y + c.height > b.y;
    };
    // A plain wheel pans the board (board.mjs); pan until the card is gone.
    await page.locator("#board").scrollIntoViewIfNeeded();
    const board = await page.locator("#board").boundingBox();
    await page.mouse.move(board.x + board.width / 2, board.y + board.height / 2);
    for (let i = 0; i < 20 && await inView(); i++) { await page.mouse.wheel(600, 600); await page.waitForTimeout(30); }
    assert.equal(await inView(), false, "the card was panned out of view");
    // From the top of the page, as a person at the header would press it.
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.locator("#collecting-pill").click();
    await page.waitForFunction(() => {
      const b = document.getElementById("board").getBoundingClientRect();
      const c = document.querySelector("#board .command-document")?.getBoundingClientRect();
      const onBoard = c && c.left < b.right && c.right > b.left && c.top < b.bottom && c.bottom > b.top;
      const inWindow = c && c.top < innerHeight && Math.min(c.bottom, b.bottom) > 0;
      return onBoard && inWindow;
    }, null, { timeout: 5000 });
    await page.screenshot({ path: resolve(output, `collecting-${width}.png`) });
    await noOverflow("collecting");

    // ---- paused: no chip, and the commands say why they are unavailable
    if (await page.locator("#attention").isVisible()) await page.locator("#attention-dismiss").click();
    await page.locator("#stop-capture").click();
    await page.waitForFunction(() => document.getElementById("state-word").textContent === "Paused");
    await page.waitForSelector("#collecting-pill[hidden]", { state: "attached" });
    assert.match(await page.locator('#command-menu [data-command="voting"]').getAttribute("aria-description"), /while capture runs/);
    snapshot = await client.snapshot();
    assert.equal(snapshot.records.filter(r => r.kind === "command_document").length, 1, "nothing else was created");

    assert.deepEqual(errors, [], "no console errors");
    assert.deepEqual(failures, [], "no failed requests");
    console.log(`PASS ${width}px: menu by pointer and keyboard, unavailable reasons, recognised-only rows send nothing, ` +
      `the sheet (8 groups of 3 at Body size), To-do list created through the typed route, the collecting chip shows the card, paused state.`);
    await page.close();
  }
} finally {
  await browser?.close();
  for (const child of children) child.kill();
  await Promise.all(children.map(c => new Promise(r => c.exitCode !== null ? r() : c.once("exit", r))));
  const target = resolve(data);
  assert(target.startsWith(resolve(tmpdir()) + "/") || target.startsWith(resolve(tmpdir()) + "\\"));
  rmSync(target, { recursive: true, force: true });
}
