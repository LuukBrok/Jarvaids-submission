/**
 * Photograph the wall (F16, F17, F19): a sheet over the canvas, then a card
 * in the corner.
 *
 *   choose  take or pick a photograph            (the sheet)
 *   mark    drag a box around each sticky note; undo one mark or clear all
 *   read    the job's own state, never a silent wait: Waiting, Reading,
 *           then "Here is what we found", or a reason and Try again
 *           (the card at the bottom right, #photo-reading)
 *
 * The sheet closes the moment the photograph is sent, because reading takes
 * seconds and the room should not stare at a page meanwhile: the card
 * follows the job while the canvas stays in use. The workspace keeps
 * rendering under the sheet; app.screen stays "workspace".
 *
 * Automatic workspace skips marking and sends the whole sanitised photo as
 * soon as it is chosen. Notes apply immediately with source/model labels.
 * The marking flow above remains available in legacy review mode.
 */
import { jobReason, jobSize } from "./review.mjs";
import { accentPalette, noteAccent } from "./board.mjs";

// The server stores every photo as a clean PNG of at most 4 MiB, and a phone
// JPEG is several times larger once it is a PNG, so it would be refused. Redraw
// anything but a small PNG as a PNG that fits, from the oriented preview the
// boxes were drawn on; the boxes are normalised, so they still fit.
const UPLOAD_LIMIT = 3.5 * 1024 * 1024, UPLOAD_EDGE = 3200;

export function createPhoto(ctx) {
  const { app, $, show, send, attention, describe, render, rail } = ctx;
  const rememberedJobs = new Set();

  function open() {
    reset();
    show($("screen-photo"), true);
    $("photo").focus();
  }

  /** Closes the sheet and gives focus back to the button that opened it. A
   * reading already under way keeps its card. */
  function close() {
    if ($("screen-photo").hidden) return;
    show($("screen-photo"), false);
    if (document.activeElement && $("screen-photo").contains(document.activeElement)) $("open-photo").focus();
  }

  function isOpen() { return !$("screen-photo").hidden; }

  function reset() {
    app.photo = null;
    $("photo").value = "";
    $("regions").textContent = "";
    $("region-count").textContent = "0";
    show($("photo-choose"), true);
    show($("photo-stage"), false);
    $("photo-step").textContent = "Take a photo, or choose one, of the sticky notes.";
    updateSend();
  }

  function dismissReading() {
    app.photoJob = null;
    show($("photo-reading"), false);
  }

  function updateSend() {
    const n = app.photo?.regions.length ?? 0;
    $("send-photo").textContent = n ? `Read ${n} ${n === 1 ? "note" : "notes"}` : "Send for reading";
    $("undo-region").disabled = !n;
    $("clear-regions").disabled = !n;
  }

  async function chosen(file) {
    const dataUrl = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
    app.photo = { file, dataUrl, regions: [] };
    $("photo-preview").src = dataUrl;
    await $("photo-preview").decode();
    if (app.snapshot?.session?.automatic_workspace) {
      $("photo-step").textContent = "Finding and reading the sticky notes…";
      await sendPhoto();
      return;
    }
    $("regions").textContent = "";
    $("region-count").textContent = "0";
    show($("photo-choose"), false);
    show($("photo-stage"), true);
    $("photo-step").textContent = "Mark each sticky note you want read.";
    updateSend();
    wireStage();
  }

  function wireStage() {
    const stage = document.querySelector(".stage");
    const layer = $("regions");
    let origin = null, box = null;
    if (stage.dataset.wired) return;
    stage.dataset.wired = "1";

    stage.addEventListener("pointerdown", event => {
      if (event.target.closest(".region")) return;
      const rect = stage.getBoundingClientRect();
      origin = { x: event.clientX - rect.left, y: event.clientY - rect.top, rect };
      box = document.createElement("div");
      box.className = "region";
      layer.append(box);
      stage.setPointerCapture(event.pointerId);
    });
    stage.addEventListener("pointermove", event => {
      if (!origin) return;
      // Pointer capture follows the drag off the photograph; the server refuses a
      // box that leaves the image, so the box stops at its edge.
      const x = Math.min(Math.max(event.clientX - origin.rect.left, 0), origin.rect.width);
      const y = Math.min(Math.max(event.clientY - origin.rect.top, 0), origin.rect.height);
      Object.assign(box.style, {
        left: `${Math.min(origin.x, x)}px`, top: `${Math.min(origin.y, y)}px`,
        width: `${Math.abs(x - origin.x)}px`, height: `${Math.abs(y - origin.y)}px` });
    });
    stage.addEventListener("pointerup", () => {
      if (!origin) return;
      const rect = origin.rect;
      const w = parseFloat(box.style.width), h = parseFloat(box.style.height);
      origin = null;
      // Too small to be a note: almost certainly a stray tap.
      if (!(w >= 12 && h >= 12)) { box.remove(); box = null; return; }
      const id = `region_${String(app.photo.regions.length + 1).padStart(3, "0")}`;
      // Normalised, because the server stores boxes independent of display size.
      // Clamped again here: style lengths are rounded when read back, which can
      // put a box at the edge a hair outside the image, and the server refuses it.
      const x = Math.min(Math.max(parseFloat(box.style.left) / rect.width, 0), 1);
      const y = Math.min(Math.max(parseFloat(box.style.top) / rect.height, 0), 1);
      app.photo.regions.push({ id, box: [x, y, Math.min(w / rect.width, 1 - x), Math.min(h / rect.height, 1 - y)] });
      const tag = document.createElement("span");
      tag.textContent = String(app.photo.regions.length);
      box.append(tag);
      box = null;
      $("region-count").textContent = String(app.photo.regions.length);
      updateSend();
    });
  }

  function undoRegion() {
    if (!app.photo?.regions.length) return;
    app.photo.regions.pop();
    $("regions").lastElementChild?.remove();
    $("region-count").textContent = String(app.photo.regions.length);
    updateSend();
  }

  function clearRegions() {
    if (!app.photo) return;
    app.photo.regions = [];
    $("regions").textContent = "";
    $("region-count").textContent = "0";
    updateSend();
  }

  function uploadable(photo) {
    if (photo.file.type === "image/png" && photo.file.size <= UPLOAD_LIMIT)
      return { mime: "image/png", base64: photo.dataUrl.split(",")[1] };
    const image = $("photo-preview");
    let scale = Math.min(1, UPLOAD_EDGE / Math.max(image.naturalWidth, image.naturalHeight));
    for (;;) {
      const canvas = document.createElement("canvas");
      canvas.width = Math.max(1, Math.round(image.naturalWidth * scale));
      canvas.height = Math.max(1, Math.round(image.naturalHeight * scale));
      canvas.getContext("2d").drawImage(image, 0, 0, canvas.width, canvas.height);
      const base64 = canvas.toDataURL("image/png").split(",")[1];
      const bytes = base64.length * 3 / 4;
      if (bytes <= UPLOAD_LIMIT || canvas.width < 64) return { mime: "image/png", base64 };
      // PNG size grows with area, so shrink the edge by the square root, with margin.
      scale *= Math.sqrt(UPLOAD_LIMIT / bytes) * 0.95;
    }
  }

  async function sendPhoto() {
    if (!app.photo) return;
    const automatic = app.snapshot?.session?.automatic_workspace;
    if (!automatic && !app.photo.regions.length) { attention("Mark at least one note on the photograph first."); return; }
    const { mime, base64 } = uploadable(app.photo);
    $("send-photo").disabled = true;
    try {
      const source = await send("source.image", { mime, base64, ...(automatic ? {} : { regions: app.photo.regions }) });
      const job = await send("extraction.queue", { source_id: source.id, expected_revision: source.revision });
      app.photoJob = job.id;
      close();
      show($("photo-reading"), true);
      renderReading(app.snapshot);
    } finally { $("send-photo").disabled = false; }
  }

  /** The card follows its own job, so the person who took the photo sees it
   * through: waiting, reading, found, or why not. */
  function renderReading(s) {
    if (!app.photoJob || !s || $("photo-reading").hidden) return;
    const job = s.records.find(r => r.id === app.photoJob);
    const status = job?.data.status ?? "queued";
    const n = job ? jobSize(s, job) : app.photo?.regions.length ?? 0;
    const failed = ["failed", "cancelled"].includes(status);
    const done = status === "succeeded";
    const automatic = s.session?.automatic_workspace;
    if (done && automatic && !rememberedJobs.has(job.id)) {
      rememberedJobs.add(job.id);
      for (const id of job.data.proposal_ids ?? []) {
        const proposal = s.records.find(r => r.id === id);
        const item = s.records.find(r => r.id === proposal?.data.item_id);
        if (item) app.undoStack.push({ id:item.id, text:item.data.text });
      }
      requestAnimationFrame(render);
    }
    const glyph = document.querySelector("#reading-status .glyph");
    glyph.className = "glyph " + (failed ? "glyph-failed st-failed" : done ? "glyph-provisional st-provisional" : "glyph-waiting st-waiting");
    $("reading-word").textContent = status === "queued" ? "Waiting to be read" : status === "running" ? (automatic ? "Finding and reading notes…" : `Reading ${n} ${n === 1 ? "note" : "notes"}`)
      : done ? "Here is what we found" : status === "cancelled" ? "Reading cancelled" : "Reading failed";
    $("reading-text").textContent = failed ? `${jobReason(job)} The photograph is kept, so it can be read again.`
      : done ? (automatic ? `${job.data.proposal_ids?.length ?? 0} notes added to the canvas. You can edit them there.` : "Each is on the canvas, proposed and slightly askew, until someone accepts it in Review.")
      : "This usually takes a few seconds. The canvas stays in use meanwhile.";
    show($("found-review"), done && !automatic);
    show($("reading-retry"), failed);
    const list = $("found-list");
    list.textContent = "";
    if (!done || automatic) return;
    const palette = accentPalette() ?? {};
    for (const id of job.data.proposal_ids ?? []) {
      const p = s.records.find(r => r.id === id);
      if (!p) continue;
      const li = document.createElement("li");
      // The colour the note will have on the canvas: the accent nearest its
      // measured paper colour, so the list reads as the wall did.
      li.className = `found-item note-${noteAccent(p, palette)}`;
      // Only a proposal still waiting has its crop: the review rail gives a
      // card's crop back once the card leaves the queue, and asking again
      // here would fetch it on every render.
      const waiting = ["needs_review", "stale"].includes(p.data.status);
      const crop = waiting ? ctx.review.cropFor(p) : null;
      if (crop) { const img = document.createElement("img"); img.src = crop; img.alt = "The marked note"; li.append(img); }
      else li.append(document.createElement("span"));
      const body = document.createElement("div");
      const text = document.createElement("p");
      text.className = "t-body";
      text.textContent = p.data.reading_status === "unreadable" ? "Unreadable: type it in Review" : p.data.text;
      const meta = document.createElement("p");
      meta.className = "t-meta";
      meta.textContent = ctx.review.confidence(p);
      body.append(text, meta);
      li.append(body);
      list.append(li);
    }
  }

  async function retry() {
    const s = app.snapshot;
    const job = s.records.find(r => r.id === app.photoJob);
    const source = s.records.find(r => r.id === job?.data.refs?.[0]?.id);
    if (!source) return;
    try {
      const next = await send("extraction.queue", { source_id: source.id, expected_revision: source.revision });
      app.photoJob = next.id;
      renderReading(app.snapshot);
    } catch (error) { attention(describe(error)); }
  }

  function wire() {
    $("open-photo").addEventListener("click", () => open());
    $("close-photo").addEventListener("click", () => close());
    // A press on the backdrop, or Escape, closes the sheet as Close does.
    $("screen-photo").addEventListener("click", event => { if (event.target === $("screen-photo")) close(); });
    document.addEventListener("keydown", event => { if (event.key === "Escape" && isOpen()) close(); });
    $("photo").addEventListener("change", event => { const f = event.target.files?.[0]; if (f) chosen(f).catch(error => attention(describe(error))); });
    $("undo-region").addEventListener("click", () => undoRegion());
    $("clear-regions").addEventListener("click", () => clearRegions());
    $("send-photo").addEventListener("click", () => sendPhoto().catch(error => attention(describe(error))));
    $("found-review").addEventListener("click", () => { dismissReading(); rail("review"); render(); });
    $("reading-retry").addEventListener("click", () => retry());
    $("reading-dismiss").addEventListener("click", () => dismissReading());
    $("photo-again").addEventListener("click", () => open());
  }

  return { wire, renderReading, open, close, isOpen };
}
