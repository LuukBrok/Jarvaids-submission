import { createRequire } from "node:module";
/**
 * Quote notes end to end: a transcript line quoted onto the canvas through
 * the real server, drawn in a real browser (DESIGN.md 1.2).
 *
 * The browser is the facilitator: it starts the session, agrees and starts
 * capture through the screens. Node reads the session and credential from
 * the page's own create request, invites a second person, Jo, and sends
 * short silent PCM16 chunks as both people, so the stand-in transcriber
 * writes real transcript segments with real speakers.
 *
 * The transcript rows and their Quote button belong to the rail (DESIGN.md
 * 1.5), built in parallel, so this test dispatches `jv:quote` itself and
 * gives each row the contract the rail will (`id="seg-<id>"`,
 * `data-segment-id`) if it does not have it yet.
 *
 *     node tests/quote-browser.mjs
 *     SCREENSHOT=path/to/file.png node tests/quote-browser.mjs
 */
import { spawn } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { GenAIClient, newToken } from "../../server/client.mjs";
import { quoteText, quoteTime } from "../tools/quote.mjs";

let chromium;
try { ({ chromium } = createRequire(import.meta.url)("playwright")); }
catch { console.log("SKIP: playwright is not installed."); process.exit(0); }

const HERE = dirname(fileURLToPath(import.meta.url));
const CLIENT = resolve(HERE, ".."), SERVER = resolve(CLIENT, "../server");
const STATIC_PORT = 5193, API_PORT = 3093, API = `http://127.0.0.1:${API_PORT}`;
const data = mkdtempSync(join(tmpdir(), "jarvaids-quote-"));
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

const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
const errors = [], failed = [];
page.on("pageerror", e => errors.push(String(e)));
page.on("console", m => { if (m.type() === "error") errors.push(m.text()); });
page.on("requestfailed", r => {
  if (r.url().startsWith("blob:")) return;
  // A poll the sync library cancels on purpose is not a failure (journey.mjs).
  if (r.method() === "GET" && /ERR_ABORTED/.test(r.failure()?.errorText ?? "")) return;
  failed.push(r.url().slice(-70));
});
let created = null;
page.on("request", r => {
  if (r.method() === "POST" && r.url().endsWith("/api/sessions")) created = JSON.parse(r.postData());
});

let failures = 0;
const step = async (label, fn) => {
  try { await fn(); console.log("ok   " + label); }
  catch (error) {
    failures++;
    const said = await page.evaluate(() => { const a = document.getElementById("attention"); return a && !a.hidden ? a.textContent : ""; }).catch(() => "");
    console.log("FAIL " + label + "\n       " + String(error.message).split("\n")[0].slice(0, 240) + (said ? "\n       app said: " + said.trim() : ""));
  }
};
const until = (fn, arg, timeout = 8000) => page.waitForFunction(fn, arg, { timeout });

// ---- the facilitator opens the session in the browser --------------------
await page.goto(`http://127.0.0.1:${STATIC_PORT}/client/`, { waitUntil: "networkidle" });
await page.click(".advanced summary");
await page.fill("#base-url", API);
await page.fill("#owner-name", "Sanne");
await page.click("#create");
await page.waitForSelector("#consent:not([hidden])", { timeout: 10000 });
await page.check("#agree-check");
await page.click("#acknowledge");
await until(() => !document.getElementById("activate").disabled);
await page.click("#activate");
await page.waitForSelector("#screen-workspace:not([hidden])", { timeout: 10000 });

// ---- Node speaks as both people ------------------------------------------
const sanne = new GenAIClient({ baseUrl: API, sessionId: created.session_id, token: created.owner_token });
const run = async (client, op, payload) => (await client.submit(client.intent(op, payload))).result;
let snap = await sanne.snapshot();
const invitation = newToken();
await run(sanne, "participant.invite", { invitation, expected_roster_revision: snap.session.roster_revision, role: "participant" });
const jo = new GenAIClient({ baseUrl: API, sessionId: created.session_id, token: newToken() });
await jo.join({ invitation, name: "Jo", policyVersion: snap.session.policy_version });
/** Silence, 16 kHz mono PCM16. The stand-in transcriber writes a line that
 * names the duration, so each chunk's line is different. */
const silence = ms => Buffer.alloc(Math.round(16000 * ms / 1000) * 2).toString("base64");
const segments = [];
// Enough lines that the rail has to scroll to reach the first one.
for (let i = 0; i < 24; i++) {
  const who = i % 2 === 0 ? jo : sanne;
  segments.push(await run(who, "source.audio", { mime: "audio/pcm16", base64: silence(800 + 100 * i), ended_reason: "silence" }));
}
snap = await sanne.snapshot();
const memberIds = snap.members.map(m => m.id);
const [joSaid, sanneSaid] = segments;
const detailOf = (segment, name) => ({ segmentId: segment.id, text: segment.data.text, speakerName: name,
  speakerActorId: segment.data.speaker_actor_id, createdAt: segment.data.created_at });

// Until the rail's rows carry their segment ids (DESIGN.md 1.5), give them
// the contract here, matched by their words, on every redraw.
await page.evaluate(lines => {
  const box = document.getElementById("transcript");
  const tag = () => {
    for (const row of box.querySelectorAll(".transcript-row")) {
      if (row.id) continue;
      const words = row.querySelector(".transcript-words")?.textContent;
      const hit = lines.find(l => l.text === words);
      if (hit) { row.id = `seg-${hit.id}`; row.dataset.segmentId = hit.id; }
    }
  };
  new MutationObserver(tag).observe(box, { childList: true });
  tag();
}, segments.map(s => ({ id: s.id, text: s.data.text })));

const quote = detail => page.evaluate(d => document.dispatchEvent(new CustomEvent("jv:quote", { detail: d })), detail);
const noteOf = id => page.locator(`.note[data-id="${id}"]`);
const proposalFor = text => snap.records.find(r => r.kind === "proposal" && r.data.text === text);

await step("the transcript shows every line, each row carrying its segment id", async () => {
  await until(n => document.querySelectorAll("#transcript .transcript-row[id^='seg-']").length === n, segments.length, 10000);
});

const joText = quoteText(joSaid.data.text, joSaid.data.created_at);
const sanneText = quoteText(sanneSaid.data.text, sanneSaid.data.created_at);
const joTime = quoteTime(joSaid.data.created_at);
let joProposal, sanneProposal, joItem;

await step("a quote lands in the review queue as the words with the time marker", async () => {
  if (!/ · \d{2}:\d{2}$/.test(joText)) throw new Error("marker text: " + joText);
  await quote(detailOf(joSaid, "Jo"));
  await until(text => /Quoted onto the canvas, waiting for review\./.test(document.getElementById("attention-text").textContent), null);
  snap = await sanne.snapshot();
  joProposal = proposalFor(joText);
  if (!joProposal) throw new Error("no proposal with the text " + joText);
  if (joProposal.data.origin !== "human") throw new Error("a quote is a person's typed note, origin " + joProposal.data.origin);
  await page.click('[data-rail="review"]');
  await until(([id, text]) => document.querySelector(`.proposal[data-id="${id}"] textarea`)?.value === text, [joProposal.id, joText]);
});

await step("on the canvas it is a quote note: marker, speaker's colour, the text unchanged", async () => {
  const note = noteOf(joProposal.id);
  await note.waitFor({ timeout: 8000 });
  await until(id => document.querySelector(`.note[data-id="${id}"] .quote-marker`), joProposal.id);
  const seen = await note.evaluate(el => {
    const probe = document.createElement("i");
    probe.style.color = "var(--person-2)";
    document.body.append(probe);
    const want = getComputedStyle(probe).color;
    probe.remove();
    return { cls: el.className, fill: el.style.getPropertyValue("--note-fill").trim(), bg: getComputedStyle(el).backgroundColor, want,
      text: el.querySelector(".text").textContent, marker: el.querySelector(".quote-marker").textContent,
      markerTag: el.querySelector(".quote-marker").tagName, timeShown: getComputedStyle(el.querySelector(".quote-time")).display,
      kind: el.querySelector(".kind").textContent, segment: el.dataset.quoteSegment,
      font: getComputedStyle(el.querySelector(".quote-marker")).fontFamily };
  });
  if (!/\bnote-quote\b/.test(seen.cls)) throw new Error("class: " + seen.cls);
  // Jo joined second, so Jo is --person-2.
  const n = memberIds.indexOf(joSaid.data.speaker_actor_id) + 1;
  if (n !== 2 || seen.fill !== "var(--person-2)") throw new Error(`fill ${seen.fill}, Jo is member ${n}`);
  if (seen.bg !== seen.want) throw new Error(`drawn ${seen.bg}, --person-2 is ${seen.want}`);
  if (seen.text !== joText) throw new Error("the note's text changed: " + seen.text);
  if (seen.marker !== joTime || seen.markerTag !== "BUTTON") throw new Error(`marker ${seen.markerTag} ${seen.marker}`);
  if (seen.timeShown !== "none") throw new Error("the time inside the sentence is still shown");
  if (seen.kind !== "Quote · Jo") throw new Error("kind: " + seen.kind);
  if (seen.segment !== joSaid.id) throw new Error("data-quote-segment: " + seen.segment);
  if (!/JetBrains Mono/.test(seen.font)) throw new Error("marker face: " + seen.font);
});

await step("the link is stored under jv.quotes.links as proposal id to segment, time and speaker", async () => {
  const links = await page.evaluate(() => JSON.parse(localStorage.getItem("jv.quotes.links")));
  const want = { segmentId: joSaid.id, time: joSaid.data.created_at, speakerActorId: joSaid.data.speaker_actor_id };
  if (JSON.stringify(links[joProposal.id]) !== JSON.stringify(want)) throw new Error(JSON.stringify(links));
});

await step("a second quote takes its own speaker's colour", async () => {
  await quote(detailOf(sanneSaid, "Sanne"));
  await until(t => [...document.querySelectorAll(".note.note-quote .text")].some(e => e.textContent === t), sanneText);
  snap = await sanne.snapshot();
  sanneProposal = proposalFor(sanneText);
  const fill = await noteOf(sanneProposal.id).evaluate(el => el.style.getPropertyValue("--note-fill").trim());
  if (fill !== "var(--person-1)") throw new Error("Sanne's quote fill: " + fill);
});

await step("accepted, the quote keeps its marker and colour as an item", async () => {
  await page.click('[data-rail="review"]');
  await page.click(`.proposal[data-id="${joProposal.id}"] .btn-primary`);
  for (let i = 0; i < 40 && !joItem; i++) {
    snap = await sanne.snapshot();
    joItem = snap.records.find(r => r.kind === "item" && r.data.proposal_id === joProposal.id);
    if (!joItem) await page.waitForTimeout(150);
  }
  if (!joItem) throw new Error("no item was made");
  await until(id => document.querySelector(`.note.item-accepted[data-id="${id}"] .quote-marker`), joItem.id);
  const seen = await noteOf(joItem.id).evaluate(el => ({ fill: el.style.getPropertyValue("--note-fill").trim(),
    marker: el.querySelector(".quote-marker").textContent, text: el.querySelector(".text").textContent }));
  if (seen.fill !== "var(--person-2)" || seen.marker !== joTime || seen.text !== joText) throw new Error(JSON.stringify(seen));
});

await step("the marker survives the board redrawing on its own", async () => {
  await noteOf(joItem.id).getByRole("button", { name: "Show details" }).click();
  await until(id => document.querySelector(`.note[data-id="${id}"] [aria-expanded="true"]`), joItem.id);
  await until(id => document.querySelector(`.note[data-id="${id}"] .quote-marker`), joItem.id, 3000);
  await noteOf(joItem.id).getByRole("button", { name: "Hide details" }).click();
  await until(id => document.querySelector(`.note[data-id="${id}"] [aria-expanded="false"]`) &&
    document.querySelector(`.note[data-id="${id}"] .quote-marker`), joItem.id, 3000);
});

/** Once scrolling has come to rest: is the row inside the window, inside
 * every scrolling box around it, and not under anything (a sticky header)? */
const rowInView = async id => {
  let last = "";
  for (let i = 0; i < 40; i++) {
    const now = await page.evaluate(() => [window.scrollY, document.querySelector(".ws-rail").scrollTop].join());
    if (now === last) break;
    last = now;
    await page.waitForTimeout(100);
  }
  return page.evaluate(segId => {
    const row = document.getElementById(`seg-${segId}`);
    if (!row) return false;
    const r = row.getBoundingClientRect();
    if (r.height === 0 || r.top < 0 || r.bottom > window.innerHeight) return false;
    for (let el = row.parentElement; el; el = el.parentElement) {
      const o = getComputedStyle(el).overflowY;
      if (o !== "auto" && o !== "scroll") continue;
      const c = el.getBoundingClientRect();
      if (r.top < c.top - 1 || r.bottom > c.bottom + 1) return false;
    }
    return [r.top + 2, r.bottom - 2].every(y => row.contains(document.elementFromPoint(r.left + r.width / 2, y)));
  }, id);
};

await step("pressing the marker opens the Transcript, scrolls to the line and highlights it", async () => {
  await page.click('[data-rail="transcript"]');
  await page.evaluate(() => {
    document.querySelector(".ws-rail").scrollTop = 1e6;
    document.getElementById("transcript").scrollTop = 1e6;
  });
  if (await rowInView(joSaid.id)) throw new Error("the first line was already in view, so this proves nothing");
  await page.click('[data-rail="review"]');
  await noteOf(joItem.id).locator(".quote-marker").click();
  await until(() => document.querySelector('[data-rail="transcript"]').getAttribute("aria-selected") === "true" &&
    !document.getElementById("rail-transcript").hidden, null, 2000);
  await until(id => document.getElementById(`seg-${id}`).classList.contains("quoted-highlight"), joSaid.id, 1000);
  for (let i = 0; i < 20 && !(await rowInView(joSaid.id)); i++) await page.waitForTimeout(50);
  if (!(await rowInView(joSaid.id))) throw new Error("the line was not scrolled into view");
  const bg = await page.evaluate(id => {
    const probe = document.createElement("i");
    probe.style.color = "var(--highlight)";
    document.body.append(probe);
    const want = getComputedStyle(probe).color;
    probe.remove();
    return [getComputedStyle(document.getElementById(`seg-${id}`)).backgroundColor, want];
  }, joSaid.id);
  await page.waitForTimeout(400);   // the tone fades in; then the screenshot shows it settled
  if (process.env.SCREENSHOT) await page.screenshot({ path: process.env.SCREENSHOT });
  const settled = await page.evaluate(id => getComputedStyle(document.getElementById(`seg-${id}`)).backgroundColor, joSaid.id);
  if (settled !== bg[1]) throw new Error(`highlight ${settled}, --highlight is ${bg[1]}`);
});

await step("the highlight goes after two seconds", async () => {
  await page.waitForTimeout(2000);
  if (await page.evaluate(id => document.getElementById(`seg-${id}`).classList.contains("quoted-highlight"), joSaid.id)) {
    throw new Error("still highlighted");
  }
});

await step("the marker works from the keyboard", async () => {
  await page.click('[data-rail="review"]');
  // Reached by Tab, so the browser treats it as keyboard focus.
  await noteOf(sanneProposal.id).locator(".quote-marker").focus();
  await page.keyboard.press("Shift+Tab");
  await page.keyboard.press("Tab");
  const ring = await page.evaluate(() => document.activeElement.matches(".quote-marker")
    ? getComputedStyle(document.activeElement).outlineStyle : "focus is on " + document.activeElement.className);
  await page.keyboard.press("Enter");
  await until(id => document.getElementById(`seg-${id}`)?.classList.contains("quoted-highlight"), sanneSaid.id, 2000);
  if (ring !== "solid") throw new Error("no visible focus ring on the marker: " + ring);
});

await step("at 400px: no sideways scroll, and the marker still takes you to the line", async () => {
  await page.setViewportSize({ width: 400, height: 900 });
  await page.waitForTimeout(400);
  if (await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)) throw new Error("horizontal overflow at 400px");
  await page.click('[data-rail="review"]');
  await page.waitForTimeout(2100);   // the keyboard step's highlight runs out
  const marker = noteOf(joItem.id).locator(".quote-marker");
  await marker.scrollIntoViewIfNeeded();
  await marker.click();
  await until(id => document.getElementById(`seg-${id}`).classList.contains("quoted-highlight"), joSaid.id, 2000);
  for (let i = 0; i < 20 && !(await rowInView(joSaid.id)); i++) await page.waitForTimeout(50);
  if (!(await rowInView(joSaid.id))) throw new Error("the line was not scrolled into view at 400px");
  // Still lit at rest, even if the transcript was redrawn while it scrolled.
  if (!(await page.evaluate(id => document.getElementById(`seg-${id}`).classList.contains("quoted-highlight"), joSaid.id))) {
    throw new Error("the highlight was gone by the time the line came to rest");
  }
  if (process.env.SCREENSHOT_NARROW) await page.screenshot({ path: process.env.SCREENSHOT_NARROW });
});

await step("no console errors and no failed requests", async () => {
  if (errors.length) throw new Error("console: " + errors.join(" | ").slice(0, 300));
  if (failed.length) throw new Error("failed: " + failed.join(" | "));
});

await browser.close();
stopAll();
console.log(failures ? `\n${failures} step(s) failed` : "\nquote notes passed");
process.exit(failures ? 1 : 0);
