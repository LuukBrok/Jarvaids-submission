/**
 * The dock: the floating canvas toolbar (DESIGN.md 1.3). Bottom left of the
 * canvas, in this order: select (V), draw (D), erase (E), connect (C), a
 * hairline, zoom out, the zoom level, zoom in, fit (0), a hairline, the
 * Canvas, List and Calendar toggle. Outside the canvas only the toggle
 * shows, so the way back is always where it was.
 *
 * The zoom buttons and the view toggle are static markup in index.html with
 * the ids app.mjs wires and the tests press; this module adds the four tools,
 * keeps their pressed state in step with the board, answers the keyboard
 * shortcuts, gives the board its motion helper and fills the empty state's
 * two actions.
 *
 * A shortcut works only when focus is not in a field, so typing a "d" into a
 * note never switches to the pen.
 */

const TOOLS = [
  { name: "select", key: "v", label: "Select", icon: '<path d="M5 3l10 7-4.5 1.2L13 16l-2 1-2.4-4.8L5 15z"/>' },
  { name: "draw", key: "d", label: "Draw", icon: '<path d="M4 16l1-4 8.5-8.5a2.1 2.1 0 0 1 3 3L8 15z"/><path d="M12 5l3 3"/>' },
  { name: "erase", key: "e", label: "Erase", icon: '<path d="M8 17h9"/><path d="M3.5 12.5l7-7.5a2 2 0 0 1 2.8 0l2.7 2.7a2 2 0 0 1 0 2.8L10 17H7.5z"/><path d="M7 9l5 5"/>' },
  { name: "connect", key: "c", label: "Connect", icon: '<circle cx="4.5" cy="15.5" r="2"/><circle cx="15.5" cy="4.5" r="2"/><path d="M6.5 15.5c5 0 2-11 7-11"/>' },
];
const NEEDS_EDITING = new Set(["draw", "erase", "connect"]);

/** True when a key press belongs to a field, a button's own keys, or a
 * modifier chord, so the dock must leave it alone. */
export function isTypingTarget(target) {
  const el = target?.closest ? target : null;
  if (!el) return false;
  if (el.isContentEditable) return true;
  return Boolean(el.closest("input, textarea, select, [contenteditable=''], [contenteditable='true']"));
}

/** The tool a key chooses, or null. "0" fits rather than choosing a tool. */
export function toolForKey(key) {
  const k = String(key ?? "").toLowerCase();
  return TOOLS.find(t => t.key === k)?.name ?? null;
}

export function register(registerTool) {
  let buttons = new Map();
  let editable = true;

  registerTool("dock", {
    mount(ctx) {
      const board = ctx.board;
      const dock = ctx.$("dock");
      if (!dock || !board) return;
      // The motion helper, so the board can land, accept and reject notes.
      board.settle = ctx.settle;

      const group = dock.querySelector(".dock-tools");
      for (const tool of TOOLS) {
        const b = document.createElement("button");
        b.type = "button";
        b.className = "dock-button";
        b.dataset.tool = tool.name;
        b.setAttribute("aria-pressed", String(tool.name === board.tool));
        b.setAttribute("aria-label", tool.label);
        b.setAttribute("aria-keyshortcuts", tool.key.toUpperCase());
        b.title = `${tool.label} (${tool.key.toUpperCase()})`;
        b.innerHTML = `<svg viewBox="0 0 20 20" aria-hidden="true" focusable="false">${tool.icon}</svg>`;
        b.addEventListener("click", () => board.setTool(tool.name));
        group.append(b);
        buttons.set(tool.name, b);
      }
      board.root.addEventListener("jv:tool", event => {
        for (const [name, b] of buttons) b.setAttribute("aria-pressed", String(name === event.detail.tool));
      });
      ctx.show(dock, true);

      document.addEventListener("keydown", event => {
        if (event.defaultPrevented || event.ctrlKey || event.metaKey || event.altKey) return;
        if (isTypingTarget(event.target) || document.querySelector("dialog[open]")) return;
        if (ctx.app.screen !== "workspace" || ctx.app.view !== "canvas") return;
        if (event.key === "0") {
          // The board answers 0 itself while it has focus.
          if (event.target === board.root) return;
          event.preventDefault();
          board.fit();
          return;
        }
        const name = toolForKey(event.key);
        if (!name || (NEEDS_EDITING.has(name) && !editable)) return;
        event.preventDefault();
        board.setTool(name);
      });

      // The empty state's two actions are the bar's photograph button and
      // the composer's field, so they are refused exactly when those are.
      ctx.$("empty-photo")?.addEventListener("click", () => ctx.$("open-photo")?.click());
      ctx.$("empty-note")?.addEventListener("click", () => ctx.$("note-text")?.focus());
    },

    render(ctx, snapshot) {
      const board = ctx.board, dock = ctx.$("dock");
      if (!board || !dock) return;
      // Drawing, erasing and connecting write to the canvas: not on a read
      // only (touch) board, not once the session has ended, not in the list.
      const canvas = ctx.app.view === "canvas";
      editable = !board.readonly && snapshot?.session?.state !== "closed";
      for (const [name, b] of buttons) if (NEEDS_EDITING.has(name)) b.disabled = !editable;
      if (!editable && board.tool !== "select") board.setTool("select");
      for (const el of dock.querySelectorAll(".dock-tools, .dock-tools-sep, .dock-view-sep")) el.hidden = !canvas;
      const photo = ctx.$("open-photo"), field = ctx.$("note-text");
      if (ctx.$("empty-photo") && photo) ctx.$("empty-photo").disabled = photo.disabled;
      if (ctx.$("empty-note") && field) ctx.$("empty-note").disabled = field.disabled;
    },
  });
}
