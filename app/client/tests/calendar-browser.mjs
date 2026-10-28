/** Real HTTP, persistence and canvas; explicitly scripted speech/voice/AI replies. */
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
const data = mkdtempSync(join(tmpdir(), "jv-cal-browser-"));
const output = resolve(root, ".local/calendar-ui"); mkdirSync(output, { recursive: true });
const staticPort = 5195, apiPort = 3095, automaticPort = 3096, children = [];
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
  launch(["-m", "tests.calendar_browser_server", "--port", String(apiPort), "--data-dir", data,
    "--origin", `http://127.0.0.1:${staticPort}`], resolve(root, "app/server"));
  // The automatic workspace server, where a typed addressed command runs:
  // the Calendar view's empty state offers "Make a calendar" only there.
  launch(["-m", "tests.automatic_browser_server", "--port", String(automaticPort), "--data-dir", join(data, "automatic"),
    "--origin", `http://127.0.0.1:${staticPort}`], resolve(root, "app/server"));
  mkdirSync(join(data, "automatic"));
  await ready(`http://127.0.0.1:${staticPort}/client/`); await ready(`http://127.0.0.1:${apiPort}/health`); await ready(`http://127.0.0.1:${automaticPort}/health`);
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
    await page.locator("#base-url").fill(`http://127.0.0.1:${apiPort}`); await page.locator("#session-timezone").fill("Europe/Amsterdam"); await page.locator("#create").click();
    await page.waitForFunction(() => document.getElementById('consent-text').textContent.includes('whole meeting so far'));
    assert.match(await page.locator("#consent-text").innerText(), /whole meeting so far/);
    await page.locator("#agree-check").check(); await page.locator("#acknowledge").click(); await page.locator("#activate").click();
    await page.waitForFunction(() => !document.getElementById('stop-capture').disabled);
    const client = new GenAIClient({ baseUrl: `http://127.0.0.1:${apiPort}`, sessionId: credentials.session_id, token: credentials.owner_token });
    // The Calendar view before any calendar: one honest line. In review mode
    // a typed command is not executed, so no button is offered.
    const view = page.locator("#calendar-view");
    await page.locator('[data-view="calendar"]').click();
    await view.locator(".cal-empty").waitFor();
    assert.equal(await page.locator("#board").isVisible(), false);
    assert.match(await view.innerText(), /No calendar in this session yet\. Say “Hey Jarvaids, make a calendar” to start one/);
    assert.equal(await view.locator("#make-calendar").count(), 0);
    await page.locator('[data-view="canvas"]').click();
    const cmd = (op, payload) => client.submit(client.intent(op, payload));
    for (const [marker, name] of [[100, "Julie"], [200, "Pieter"]])
      await cmd("speaker.enroll", { name, mime: "audio/pcm16", base64: pcm(marker), ended_reason: "silence" });
    let stamp = 0;
    const say = async marker => {
      stamp += marker === 102 ? 200000 : 2000;
      const intent = client.intent("source.audio", { mime: "audio/pcm16", base64: pcm(marker), ended_reason: "silence",
        capture_id: "document_room_capture", captured_at_ms: stamp });
      const result = await client.submit(intent);
      if (marker === 102) assert.equal((await client.submit(intent)).replayed, true);
      return result;
    };

    const records = async kind => (await client.snapshot()).records.filter(r => r.kind === kind);
    const wait = async check => { for (let n = 0; n < 160; n++) { if (await check()) return; await new Promise(r => setTimeout(r, 100)); } throw new Error("Calendar condition timed out: " + await page.locator("#attention").textContent()); };
    const taskRecord = async () => (await records("command_entry")).find(r => r.data.entry_type === "task");
    const calendarRecord = async () => (await records("command_document")).find(r => r.data.document_type === "calendar");
    const idle = async () => wait(async () => !(await records("command_work")).some(r => ["queued", "running"].includes(r.data.status)));
    await say(141); await say(142); await idle();
    await page.locator('#board .document-task-text').waitFor();
    // A note can be given a date through the calendar. Before any calendar
    // collects, its details say so and offer no action that cannot work.
    const typedNote = (await cmd("source.text", { text: "Book the lab for user tests" })).result;
    const noteId = (await cmd("proposal.review", { proposal_id: typedNote.proposal.id,
      expected_revision: typedNote.proposal.revision, decision: "accept" })).result.item.id;
    const note = page.locator(`#board .note[data-id="${noteId}"]`);
    await note.waitFor(); await page.locator("#zoom-fit").click();
    // The board redraws on every sync, so a press can land on a drawing that
    // is being replaced; press again until the details are open.
    for (let attempt = 0; await note.locator('button[aria-expanded="true"]').count() === 0; attempt++) {
      if (attempt === 20) throw new Error("Note details did not open");
      await note.locator("button[aria-expanded]").click();
      await new Promise(r => setTimeout(r, 150));
    }
    await note.getByText(/^No calendar is collecting\./).waitFor();
    assert.equal(await note.getByRole("button", { name: "Add to calendar", exact: true }).isDisabled(), true);
    assert.equal(await note.locator(".date-chip").count(), 0);
    const taskId = (await taskRecord()).id;
    assert.equal((await taskRecord()).data.owner, "Julie");
    await say(143); await say(144); await say(145); await idle();
    const calendarId = (await calendarRecord()).id;
    // The canvas card is a compact summary: title, counts, the next dated
    // entries and Open calendar. The grid lives in the Calendar view.
    const doc = page.locator(`#board [data-id="${calendarId}"]`);
    await doc.getByRole("heading", { name: "Calendar", exact: true }).waitFor();
    await page.waitForFunction(() => document.querySelector('#board .calendar-document')?.textContent.includes('1 unscheduled'));
    assert.match(await doc.innerText(), /2 events · 1 linked task/);
    assert.equal(await doc.locator(".calendar-day, .cal-grid, .calendar-content, .document-entries").count(), 0, "the card is a summary, not a list");
    await page.screenshot({ path: resolve(output, `overview-${width}.png`), fullPage: true });
    // Add to calendar: a date picked in the note's details becomes an event in
    // the collecting calendar, linked back to the note, and the note shows a
    // chip; overdue is judged in the session's zone (Europe/Amsterdam here).
    await page.locator("#zoom-fit").click();
    await note.getByLabel("Date", { exact: true }).fill("2026-10-02");
    await note.getByRole("button", { name: "Add to calendar", exact: true }).click();
    await wait(async () => (await records("command_entry")).some(r => r.data.note_id === noteId));
    const noteEvent = (await records("command_entry")).find(r => r.data.note_id === noteId);
    assert.deepEqual([noteEvent.data.text, noteEvent.data.date, noteEvent.data.origin, noteEvent.data.entry_type],
      ["Book the lab for user tests", "2026-10-02", "human", "calendar_event"]);
    assert((await calendarRecord()).data.entry_ids.includes(noteEvent.id));
    const noteChip = note.locator(".note-dates .date-chip");
    await noteChip.waitFor();
    assert.deepEqual([await noteChip.getAttribute("data-tone"), await noteChip.innerText()], ["overdue", "Overdue · Fri 2 Oct"]);
    // The canvas card is compact, so the event's "From a note" line is read
    // in the List, which keeps the whole calendar in words.
    await page.locator('[data-view="list"]').click();
    await page.locator(`#list-view [data-id="${calendarId}"] [data-entry-id="${noteEvent.id}"] .calendar-from-note`).getByText("From a note: “Book the lab for user tests”", { exact: true }).waitFor();
    await page.locator('[data-view="canvas"]').click();
    await page.screenshot({ path: resolve(output, `note-date-${width}.png`), fullPage: true });
    // Changing the date in the note updates the chip; removing the event removes it.
    await note.getByLabel("Date", { exact: true }).fill("2099-01-15");
    await note.getByRole("button", { name: "Save date", exact: true }).click();
    await wait(async () => (await records("command_entry")).find(r => r.id === noteEvent.id).data.date === "2099-01-15");
    await page.waitForFunction(id => document.querySelector(`#board .note[data-id="${id}"] .note-dates .date-chip`)?.textContent === "Thu 15 Jan 2099", noteId);
    assert.equal(await noteChip.getAttribute("data-tone"), "plain");
    await note.getByRole("button", { name: "Remove from calendar", exact: true }).click();
    await wait(async () => (await records("command_entry")).find(r => r.id === noteEvent.id).data.removed);
    await note.getByRole("button", { name: "Add to calendar", exact: true }).waitFor();
    assert.equal(await note.locator(".date-chip").count(), 0);
    await note.getByRole("button", { name: "Hide details", exact: true }).click();
    assert.equal((await calendarRecord()).data.task_ids[0], taskId);
    const entryId = (await records("command_entry")).find(r => r.data.text === "Prototype review").id;
    await doc.getByRole("button", { name: "Open calendar", exact: true }).click();
    await view.locator(".cal-grid-month").waitFor();
    assert.equal(await page.locator('[data-view="calendar"]').getAttribute("aria-pressed"), "true");
    assert.equal(await page.locator("#board").isVisible(), false);
    assert(await page.locator("#tab-transcript").isVisible(), "the rail stays available beside the Calendar view");
    assert.match(await view.locator(".calendar-zone").innerText(), /Meeting time zone: Europe\/Amsterdam/);
    // The month grid holds the entries as pills, coloured by kind, the
    // task's owner on its pill; the undated one is in Unscheduled.
    assert.equal(await view.locator(".cal-grid-month .cal-cell").count(), 42);
    const cell = view.locator('.cal-cell[data-date="2026-10-20"]');
    const eventPill = cell.locator(".cal-pill-event"), taskPill = cell.locator(".cal-pill-task");
    assert.equal(await eventPill.count(), 1); assert.equal(await taskPill.count(), 1);
    assert.match(await eventPill.textContent(), /14:00Prototype review/);
    assert.match(await taskPill.textContent(), /Prepare the interview questionsJulie/);
    assert.match(await taskPill.getAttribute("aria-label"), /^Linked task: Prepare the interview questions, owner Julie/);
    assert.match(await eventPill.getAttribute("class"), /cal-pill-machine/, "an interpretation nobody accepted carries the machine mark");
    const [eventFill, taskFill, accents] = await page.evaluate(() => {
      const fill = sel => getComputedStyle(document.querySelector(sel)).backgroundColor;
      const probe = document.createElement("i"); document.body.append(probe);
      const resolve = name => { probe.style.backgroundColor = `var(${name})`; return getComputedStyle(probe).backgroundColor; };
      const out = [fill('#calendar-view .cal-cell .cal-pill-event'), fill('#calendar-view .cal-cell .cal-pill-task'), [resolve("--calendar-event-fill"), resolve("--calendar-task-fill")]];
      probe.remove(); return out;
    });
    assert.deepEqual([eventFill, taskFill], accents, "pills take the two accent tokens by kind");
    if (width >= 1024) assert(await eventPill.isVisible() && await taskPill.isVisible(), "pills show in the month cells");
    else assert(await view.locator(`.cal-period-list .cal-pill[data-entry-id="${entryId}"]`).isVisible(), "on a phone the month's entries follow the grid");
    assert.match(await view.locator(".cal-unscheduled").innerText(), /Launch party/);
    const contentBeforeNavigation = JSON.stringify(await records("command_entry"));
    for (const name of ["Day", "Week", "Month", "Year"]) {
      await view.getByRole("button", { name, exact: true }).click();
      assert.equal(await view.getByRole("button", { name, exact: true }).getAttribute("aria-pressed"), "true");
    }
    assert.equal(await view.locator(".cal-month-card").count(), 12);
    assert.match(await view.locator('.cal-month-card[data-month="2026-10-01"]').innerText(), /October\s+2\s+1 event · 1 task/);
    await view.getByRole("button", { name: "Next", exact: true }).click();
    assert.equal(await view.locator(".cal-period").innerText(), "2027");
    await view.getByRole("button", { name: "Previous", exact: true }).click();
    assert.equal(JSON.stringify(await records("command_entry")), contentBeforeNavigation, "navigating writes nothing");
    await view.getByRole("button", { name: "Month", exact: true }).click();
    await view.getByLabel("Go to date", { exact: true }).fill("2026-10-19");
    await view.getByLabel("Go to date", { exact: true }).dispatchEvent("change");
    assert.equal(await view.locator(".cal-cell").count(), 42);
    // A day is a list by time: the task's deadline first, then the event.
    await cell.locator(".cal-daynum").click();
    assert.deepEqual(await view.locator(".cal-day .cal-day-time").allInnerTexts(), ["Due", "14:00"]);
    await view.locator(`.cal-day .cal-pill[data-entry-id="${taskId}"]`).click();
    assert.match(await view.locator(".cal-detail").innerText(), /Owner: Julie · Agreed action/);
    await view.locator(`.cal-day .cal-pill[data-entry-id="${entryId}"]`).click();
    const detail = view.locator(".cal-detail");
    assert.match(await detail.innerText(), /2026-10-20 at 14:00/);
    await detail.getByText("Calendar evidence", { exact: true }).click();
    assert.match(await detail.innerText(), /The prototype review is tomorrow at 2 pm/);
    await page.screenshot({ path: resolve(output, `calendar-day-${width}.png`), fullPage: true });
    await view.getByRole("button", { name: "Month", exact: true }).click();
    await page.screenshot({ path: resolve(output, `calendar-${width}.png`), fullPage: true });
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    // The projector grows the grid with its type (--scale), so the pills
    // stay readable and stay inside their cells.
    const measure = () => view.evaluate(el => ({ pill: parseFloat(getComputedStyle(el.querySelector(".cal-pill")).fontSize),
      cell: el.querySelector(".cal-grid-month .cal-cell").getBoundingClientRect().height }));
    const plain = await measure();
    await page.locator("#session-menu-button").click(); await page.locator("#room-toggle").click();
    const projected = await measure();
    assert(Math.abs(projected.pill / plain.pill - 1.25) < 0.01, `pill type grows by --scale (${plain.pill} to ${projected.pill})`);
    if (width >= 1024) {
      assert(projected.cell > plain.cell, "month cells grow with the projector");
      assert(await cell.evaluate(c => [...c.querySelectorAll(".cal-pill")].every(p => p.getBoundingClientRect().right <= c.getBoundingClientRect().right + 1)), "pills stay inside their cell");
    }
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.screenshot({ path: resolve(output, `calendar-projector-${width}.png`), fullPage: true });
    await page.locator("#session-menu-button").click(); await page.locator("#room-toggle").click();
    // A spoken correction lands in the open view.
    await say(146); await idle();
    await page.waitForFunction(() => document.querySelector('#calendar-view .cal-cell[data-date="2026-10-23"] .cal-pill-event')?.textContent.includes('15:00'));
    assert.equal((await records("command_entry")).find(r => r.id === entryId).data.date, "2026-10-23");
    // A voice view command switches the Calendar view, from the canvas too.
    await page.locator('[data-view="canvas"]').click();
    await say(147); await idle();
    await page.waitForFunction(() => !document.getElementById("calendar-view").hidden
      && document.querySelector('#calendar-view .calendar-tools button[aria-pressed="true"]')?.textContent === 'Week');
    assert.equal(await page.locator('[data-view="calendar"]').getAttribute("aria-pressed"), "true");
    assert.equal(await view.locator(".cal-grid-week .cal-cell").count(), 7);
    assert.equal(await view.locator('.cal-grid-week .cal-cell[data-date="2026-10-23"] .cal-pill-event').count(), 1);
    await page.locator('[data-view="list"]').click();
    const list = page.locator(`#list-view [data-id="${calendarId}"]`);
    const row = list.locator(`[data-entry-id="${entryId}"]`);
    await row.getByText("Edit event", { exact: true }).click();
    const field = row.getByLabel("Event", { exact: true }); await field.fill("Prototype review with team");
    await field.evaluate(el => el.setSelectionRange(5, 5)); await say(152); await idle();
    await page.waitForFunction(() => [...document.querySelectorAll('#list-view .document-coverage')].some(el => el.textContent.includes('7 of 7')));
    assert.equal(await field.inputValue(), "Prototype review with team");
    assert(await field.evaluate(el => document.activeElement === el && el.selectionStart === 5));
    await row.getByRole("button", { name: "Save calendar entry", exact: true }).click();
    await wait(async () => (await records("command_entry")).find(r => r.id === entryId).data.text === "Prototype review with team");
    await say(148); await idle();
    await list.getByRole("button", { name: "Accept calendar", exact: true }).waitFor();
    await say(152); await idle(); // Discussion and to-do collection continue while calendar awaits acceptance.
    assert.equal((await calendarRecord()).data.state, "reviewing");
    await say(149); await idle();
    await list.getByText("Accepted calendar", { exact: true }).waitFor();
    assert.equal((await taskRecord()).data.status, "accepted");
    await say(150); await idle(); await say(151); await idle();
    const pending = (await records("command_task_change")).filter(r => r.data.state === "pending");
    assert.equal(pending.length, 1);
    assert.equal((await taskRecord()).data.deadline_date, "2026-10-20");
    await list.getByRole("button", { name: "Accept task change", exact: true }).click();
    await wait(async () => (await taskRecord()).data.deadline_date === "2026-10-23");
    assert.equal((await taskRecord()).id, taskId);
    await say(153); await idle();
    const completion = (await records("command_task_change")).find(r => r.data.state === "pending");
    assert(completion);
    await list.locator(`[data-change-id="${completion.id}"]`).getByRole("button", { name: "Accept task change", exact: true }).click();
    await wait(async () => (await taskRecord()).data.done);
    assert((await taskRecord()).data.done);
    await say(160); await idle();
    await list.locator(".calendar-unscheduled").getByText("Demo", { exact: true }).waitFor();
    assert.match(await list.locator(".calendar-unscheduled").innerText(), /upcoming friday/i);
    await say(155); await idle(); await list.getByText("Which event should move, and to which date?", { exact: true }).first().waitFor();
    await say(156); await idle();
    const party = (await records("command_entry")).find(r => r.data.text === "Launch party");
    assert.equal(party.data.date, "2026-10-25");
    await list.locator(`[data-entry-id="${party.id}"]`).getByText('Spoken date: “25 October 2026” → 2026-10-25', { exact: true }).waitFor();
    await list.getByText("Add an event manually", { exact: true }).click();
    const manual = list.getByText("Add an event manually", { exact: true }).locator("..");
    await manual.getByLabel("Event", { exact: true }).fill("Team lunch");
    await manual.getByLabel("Date", { exact: true }).fill("2026-10-22");
    await manual.getByLabel("Time", { exact: true }).fill("12:30");
    await manual.getByRole("button", { name: "Add event", exact: true }).click();
    await wait(async () => (await records("command_entry")).some(r => r.data.text === "Team lunch"));
    await say(162); await idle();
    const failed = (await records("command_work")).find(r => r.data.document_id === calendarId && r.data.status === "error");
    assert(failed);
    assert(!(await records("command_entry")).some(r => r.data.text === "Design expo"));
    const retry = list.locator("details").filter({ has: page.getByText("Interpretation needs review", { exact: true }) }).last();
    await retry.getByLabel("A retry may incur additional API cost", { exact: true }).check();
    await retry.getByRole("button", { name: "Retry interpretation", exact: true }).click(); await idle();
    await wait(async () => (await records("command_entry")).some(r => r.data.text === "Design expo"));
    assert.equal((await records("command_entry")).find(r => r.data.text === "Design expo").data.date, "");
    await say(157); await idle();
    // Said while the list showed: the Calendar view comes forward in year
    // view, and the list follows the same focus.
    await page.waitForFunction(() => !document.getElementById("calendar-view").hidden
      && document.querySelector('#calendar-view .calendar-tools button[aria-pressed="true"]')?.textContent === 'Year');
    assert.equal(await view.locator(".cal-month-card").count(), 12);
    await page.locator('[data-view="list"]').click();
    await page.waitForFunction(() => document.querySelector('#list-view .calendar-document button[aria-pressed="true"]')?.textContent === 'Year');
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.screenshot({ path: resolve(output, `list-${width}.png`), fullPage: true });
    await page.locator('[data-view="canvas"]').click();
    await doc.getByText("Calendar, evidence and controls", { exact: true }).click();
    await page.locator("#zoom-fit").click();
    const heading = await doc.locator(".kind").boundingBox(); assert(heading);
    await page.mouse.move(heading.x+8, heading.y+5); await page.mouse.down();
    await page.mouse.move(heading.x+35, heading.y+25, { steps: 5 }); await page.mouse.up();
    await wait(async () => (await calendarRecord()).position?.hand_placed);
    await page.locator('[data-view="list"]').click();
    const reconnected = new GenAIClient({ baseUrl: `http://127.0.0.1:${apiPort}`, sessionId: credentials.session_id, token: credentials.owner_token });
    assert.equal((await reconnected.snapshot()).records.find(r => r.id === calendarId).data.calendar_view, "year");
    await say(158); await idle(); await list.getByText("Cancelled calendar", { exact: true }).waitFor();
    assert.deepEqual(errors, []); assert.deepEqual(failures, []);
    console.log(`PASS ${width}px: Calendar view (empty state, Open calendar, grid pills by kind, day by time, projector, voice view switch), compact card, calendar creation/history, four views, navigation, evidence, unscheduled/ambiguous dates, voice corrections, manual creation/edit/focus, persisted drag, shared-task review/completion, lifecycle, explicit retry, List view and reconnect.`);
    await page.close();
  }

  // Automatic workspace: the empty Calendar view offers "Make a calendar",
  // which sends the typed addressed command through the typed-note route.
  for (const width of [1440, 400]) {
    const page = await browser.newPage({ viewport: { width, height: 1000 } });
    const errors = [], failures = [], typed = [];
    page.on("pageerror", e => errors.push(e.message));
    page.on("console", m => { if (m.type() === "error") errors.push(m.text()); });
    page.on("requestfailed", r => failures.push(r.url()));
    page.on("response", r => { if (r.status() >= 400) failures.push(`${r.status()} ${r.url()}`); });
    let credentials;
    page.on("request", r => {
      if (r.url() === `http://127.0.0.1:${automaticPort}/api/sessions` && r.method() === "POST") credentials = r.postDataJSON();
      let body = null; try { body = r.method() === "POST" ? r.postDataJSON() : null; } catch {}
      if (body?.operation === "source.text") typed.push(body.payload.text);
    });
    await page.goto(`http://127.0.0.1:${staticPort}/client/`);
    await page.locator(".advanced summary").click();
    await page.locator("#base-url").fill(`http://127.0.0.1:${automaticPort}`); await page.locator("#create").click();
    await page.locator("#agree-check").check(); await page.locator("#acknowledge").click(); await page.locator("#activate").click();
    await page.waitForFunction(() => !document.getElementById('stop-capture').disabled);
    const view = page.locator("#calendar-view");
    await page.locator('[data-view="calendar"]').click();
    const make = view.getByRole("button", { name: "Make a calendar", exact: true });
    await make.waitFor();
    assert.match(await view.locator(".cal-empty-text").innerText(), /^No calendar in this session yet\./);
    await make.click();
    await view.locator(".cal-grid-month").waitFor();
    assert.deepEqual(typed, ["Hey Jarvaids, make a calendar"]);
    const client = new GenAIClient({ baseUrl: `http://127.0.0.1:${automaticPort}`, sessionId: credentials.session_id, token: credentials.owner_token });
    const snapshot = await client.snapshot();
    assert.equal(snapshot.records.filter(r => r.kind === "command_document" && r.data.document_type === "calendar").length, 1);
    assert.equal(snapshot.records.filter(r => r.kind === "proposal").length, 0, "an executed command adds no note");
    assert.match(await view.locator(".cal-state").innerText(), /AI organised/);
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.screenshot({ path: resolve(output, `calendar-made-${width}.png`), fullPage: true });
    assert.deepEqual(errors, []); assert.deepEqual(failures, []);
    console.log(`PASS ${width}px: empty Calendar view offers Make a calendar in automatic workspace and the typed command makes one.`);
    await page.close();
  }
} finally {
  await browser?.close(); for (const child of children) child.kill();
  await Promise.all(children.map(c => new Promise(r => c.exitCode !== null ? r() : c.once("exit", r))));
  const target = resolve(data); assert(target.startsWith(resolve(tmpdir()) + "/") || target.startsWith(resolve(tmpdir()) + "\\"));
  rmSync(target, { recursive: true, force: true });
}
