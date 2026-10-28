/**
 * Every text-on-colour pair the client ships meets WCAG 2.1 AA.
 *
 *     node --test tests/contrast-unit.mjs
 *
 * It reads tokens.css itself, resolves var() and color-mix(in srgb, ...)
 * exactly as a browser does, and measures each pair with the WCAG relative
 * luminance formula. Nothing is copied out of the token file, so a changed
 * token is measured as it now is. This replaces the design system's Python
 * contrast tool for the client, because that tool reads the previous token
 * file, which this branch deleted, and Python files are not changed here.
 *
 * Text is Small (13px, 500) at most sizes the client uses, which is not
 * "large" text under WCAG, so every text pair needs 4.5:1. Non-text marks
 * that carry meaning (the focus ring, the machine mark) need 3:1.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const SOURCE = readFileSync(resolve(HERE, "../tokens.css"), "utf8");

// ------------------------------------------------------------------ parsing

/** The declarations of the first top-level `:root {` block, comments removed. */
export function rootTokens(css) {
  const text = css.replace(/\/\*[\s\S]*?\*\//g, "");
  const start = text.search(/(^|\n)\s*:root\s*\{/);
  assert.ok(start >= 0, "tokens.css has a :root block");
  const open = text.indexOf("{", start);
  let depth = 0, end = open;
  for (; end < text.length; end++) {
    if (text[end] === "{") depth++;
    if (text[end] === "}" && --depth === 0) break;
  }
  return declarations(text.slice(open + 1, end));
}

function declarations(body) {
  const tokens = new Map();
  for (const m of body.matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)) tokens.set(m[1], m[2].trim());
  return tokens;
}

/** Split on commas that are not inside brackets. */
function splitTop(s) {
  const parts = [];
  let depth = 0, from = 0;
  for (let i = 0; i < s.length; i++) {
    if (s[i] === "(") depth++;
    else if (s[i] === ")") depth--;
    else if (s[i] === "," && depth === 0) { parts.push(s.slice(from, i).trim()); from = i + 1; }
  }
  parts.push(s.slice(from).trim());
  return parts;
}

/** A colour expression to [r, g, b, a], channels 0 to 255, alpha 0 to 1. */
export function resolveColour(expr, tokens, seen = new Set()) {
  expr = expr.trim();
  const v = expr.match(/^var\(\s*(--[\w-]+)\s*\)$/);
  if (v) {
    assert.ok(!seen.has(v[1]), `${v[1]} refers to itself`);
    assert.ok(tokens.has(v[1]), `${v[1]} is declared`);
    return resolveColour(tokens.get(v[1]), tokens, new Set([...seen, v[1]]));
  }
  const hex = expr.match(/^#([0-9a-f]{6})$/i);
  if (hex) return [0, 2, 4].map(i => parseInt(hex[1].slice(i, i + 2), 16)).concat(1);
  if (expr === "transparent") return [0, 0, 0, 0];
  const rgba = expr.match(/^rgba?\(([^)]+)\)$/);
  if (rgba) {
    const [r, g, b, a = "1"] = rgba[1].split(/[\s,/]+/).filter(Boolean);
    return [Number(r), Number(g), Number(b), Number(a)];
  }
  const mix = expr.match(/^color-mix\(\s*in\s+srgb\s*,([\s\S]*)\)$/);
  if (mix) {
    const [a, b] = splitTop(mix[1]).map(part => {
      const pm = part.match(/^([\s\S]*?)\s+(\d+(?:\.\d+)?)%$/);
      return pm ? { colour: resolveColour(pm[1], tokens, seen), p: Number(pm[2]) / 100 }
                : { colour: resolveColour(part, tokens, seen), p: null };
    });
    // CSS Color 5: a missing percentage is the rest of 100%; neither means
    // half and half. Sums under 100% would scale alpha; the tokens never do.
    let pa = a.p, pb = b.p;
    if (pa === null && pb === null) pa = pb = 0.5;
    else if (pa === null) pa = 1 - pb;
    else if (pb === null) pb = 1 - pa;
    assert.ok(Math.abs(pa + pb - 1) < 1e-9, `color-mix percentages add up to 100%: ${expr}`);
    // Premultiplied by alpha, as the browser interpolates.
    const alpha = a.colour[3] * pa + b.colour[3] * pb;
    const channel = i => alpha === 0 ? 0 : (a.colour[i] * a.colour[3] * pa + b.colour[i] * b.colour[3] * pb) / alpha;
    return [channel(0), channel(1), channel(2), alpha];
  }
  throw new Error(`cannot resolve a colour from: ${expr}`);
}

// ---------------------------------------------------------------- measuring

const linear = c => { c /= 255; return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; };
const luminance = ([r, g, b]) => 0.2126 * linear(r) + 0.7152 * linear(g) + 0.0722 * linear(b);
export function ratio(fg, bg) {
  const [x, y] = [luminance(fg), luminance(bg)];
  return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
}
const hexOf = c => "#" + c.slice(0, 3).map(v => Math.round(v).toString(16).padStart(2, "0")).join("");

const tokens = rootTokens(SOURCE);
const colour = name => resolveColour(`var(${name})`, tokens);
const ACCENTS = ["yellow", "lilac", "mint", "periwinkle", "coral"];

/** Every pair the system ships: [foreground, background, minimum, where it is used]. */
const PAIRS = [
  ["--ink", "--paper", 4.5, "all text on the ground"],
  ["--ink", "--paper-2", 4.5, "text on sunken panels and secondary buttons"],
  ["--ink", "--line", 4.5, "a secondary button's hover"],
  ...ACCENTS.flatMap(a => [
    ["--ink", `--${a}`, 4.5, `text on a ${a} note, chip or button`],
    ["--ink", `--${a}-soft`, 4.5, `text on a ${a} soft field`],
    ["--paper", `--${a}-deep`, 4.5, `text on a ${a} deep fill`],
    // --ink-2 on a full accent measures 3.28:1 to 4.97:1, so a note's
    // secondary lines on an accepted (full) note are --ink, told apart by
    // size and face instead. On -soft, --ink-2 passes.
    ["--ink-2", `--${a}-soft`, 4.5, `a note's kind line and marker on ${a} soft`],
  ]),
  ["--ink-2", "--paper", 4.5, "Small secondary text on the ground"],
  ["--ink-2", "--paper-2", 4.5, "Small secondary text on sunken panels"],
  ["--ink-3", "--paper", 4.5, "Small tertiary text on the ground"],
  ["--ink-3", "--paper-2", 4.5, "Small tertiary text on sunken panels"],
  ["--danger", "--paper", 4.5, "a danger button's words"],
  ["--danger", "--danger-soft", 4.5, "a danger button's words on hover"],
  ["--text-on-danger", "--danger", 4.5, "the filled danger button in a confirmation"],
  ["--action-primary-text", "--action-primary", 4.5, "the primary button"],
  ["--action-primary-text", "--action-primary-hover", 4.5, "the primary button on hover"],
  ["--status-accepted", "--paper", 4.5, "the accepted status word"],
  ["--status-waiting", "--paper", 4.5, "the waiting status word"],
  ["--status-failed", "--paper", 4.5, "the failed status word"],
  ["--status-proposed", "--paper", 4.5, "the proposed status word"],
  ["--status-off", "--paper", 4.5, "the off status word"],
  ["--paper", "--ink", 4.5, "the listening chip and the chosen toggle"],
  ["--state-listening", "--ink", 3, "the listening bars on the listening chip"],
  ["--ink", "--state-paused", 4.5, "the paused chip"],
  ["--ink", "--chip-open", 4.5, "the open-session chip in the header"],
  ["--ink", "--chip-collecting", 4.5, "the collecting chip in the header"],
  ["--ink", "--chip-paused", 4.5, "the paused chip in the header, and the keep-alive banner's last minute"],
  ["--ink-2", "--paper-2", 4.5, "the ended chip"],
  ["--focus-ring", "--paper", 3, "the focus ring on the ground (non-text)"],
  ["--focus-ring", "--paper-2", 3, "the focus ring on sunken panels (non-text)"],
  ["--mark-machine", "--paper", 3, "a machine's proposed mark (non-text)"],
  ["--ink", "--note-proposed-fill", 4.5, "a proposed note's words"],
  ["--ink", "--highlight", 4.5, "a highlighted transcript line"],
  ["--ink", "--date-overdue", 4.5, "an overdue date chip on a note or task row"],
  ["--ink", "--date-today", 4.5, "a date chip for today on a note or task row"],
  ["--ink", "--conflict-fill", 4.5, "a criterion's conflict flag"],
  ["--ink", "--tally-track", 4.5, "a poll bar's count and voters over the empty track"],
  ["--ink", "--tally-fill", 4.5, "a poll bar's count and voters over its fill"],
  ["--ink", "--tally-lead", 4.5, "the count and voters on the choice with the most votes"],
  ["--ink", "--calendar-event-fill", 4.5, "an event pill's words in the Calendar view"],
  ["--ink", "--calendar-task-fill", 4.5, "a linked task pill's words in the Calendar view"],
  ["--ink-2", "--calendar-task-fill", 4.5, "a task pill's owner name"],
  ["--calendar-event-edge", "--calendar-event-fill", 3, "an event pill's leading edge (non-text)"],
  ["--calendar-task-edge", "--calendar-task-fill", 3, "a task pill's leading edge (non-text)"],
  ["--mark-machine", "--calendar-event-fill", 3, "the dashed machine mark round an interpreted event pill (non-text)"],
  ["--mark-machine", "--calendar-task-fill", 3, "the dashed machine mark round an interpreted task pill (non-text)"],
];

/** A translucent overlay painted over an opaque ground, as the post-it's glue
 * strip and sheen are painted over a note's fill (css/canvas.css). */
const over = (top, ground) => [0, 1, 2].map(i => top[i] * top[3] + ground[i] * (1 - top[3])).concat(1);

/** Text on the post-it's paper: [foreground, overlay, the fill under it,
 * minimum, where]. The fills are every one a board note can have: the five
 * accents (a typed note, a photograph's nearest accent, a quote by people
 * one to five), the proposed soft yellow, the typed note's paper, and the
 * -deep accents of a quote by people six to ten (paper words, no sheen). */
const OVERLAID = [
  ...ACCENTS.flatMap(a => [
    ["--ink", "--note-glue", `--${a}`, 4.5, `a ${a} note's words and marker on its glue strip`],
    ["--ink", "--note-sheen", `--${a}`, 4.5, `a ${a} note's words at its pale foot`],
    ["--paper", "--note-glue", `--${a}-deep`, 4.5, `a deep ${a} quote note's words on its glue strip`],
  ]),
  ["--ink", "--note-glue", "--note-proposed-fill", 4.5, "a proposed note's words on its glue strip"],
  ["--ink-2", "--note-glue", "--note-proposed-fill", 4.5, "the Proposed marker on a proposed note's glue strip"],
  ["--ink-2", "--note-sheen", "--note-proposed-fill", 4.5, "a proposed note's secondary lines at its pale foot"],
  ["--ink-2", "--note-glue", "--surface", 4.5, "Not yet reviewed on a typed note's glue strip"],
];

// -------------------------------------------------------------------- tests

test("every accent has a -soft and a -deep, bound to it with color-mix", () => {
  for (const a of ACCENTS) {
    assert.match(tokens.get(`--${a}-soft`) ?? "", new RegExp(`^color-mix\\(in srgb, var\\(--${a}\\) \\d+%, var\\(--paper\\)\\)$`), `--${a}-soft`);
    assert.match(tokens.get(`--${a}-deep`) ?? "", new RegExp(`^color-mix\\(in srgb, var\\(--${a}\\), var\\(--ink\\) \\d+%\\)$`), `--${a}-deep`);
  }
});

for (const [fg, bg, minimum, where] of PAIRS) {
  test(`${fg} on ${bg} is at least ${minimum}:1 (${where})`, t => {
    const f = colour(fg), b = colour(bg);
    assert.equal(b[3], 1, `${bg} is opaque`);
    assert.equal(f[3], 1, `${fg} is opaque`);
    const r = ratio(f, b);
    t.diagnostic(`${fg} ${hexOf(f)} on ${bg} ${hexOf(b)}: ${r.toFixed(2)}:1`);
    assert.ok(r >= minimum, `${fg} on ${bg} is ${r.toFixed(2)}:1, needs ${minimum}:1`);
  });
}

for (const [fg, overlay, fill, minimum, where] of OVERLAID) {
  test(`${fg} on ${overlay} over ${fill} is at least ${minimum}:1 (${where})`, t => {
    const top = colour(overlay), ground = colour(fill);
    assert.ok(top[3] > 0 && top[3] < 1, `${overlay} is translucent, an overlay`);
    assert.equal(ground[3], 1, `${fill} is opaque`);
    const f = colour(fg), b = over(top, ground);
    const r = ratio(f, b);
    t.diagnostic(`${fg} ${hexOf(f)} on ${overlay} over ${fill}, ${hexOf(b)}: ${r.toFixed(2)}:1`);
    assert.ok(r >= minimum, `${fg} on ${overlay} over ${fill} is ${r.toFixed(2)}:1, needs ${minimum}:1`);
  });
}

test("the human mark is ink at 85%, and the machine mark is dashed", () => {
  const human = colour("--mark-human");
  assert.deepEqual(human.slice(0, 3).map(Math.round), colour("--ink").slice(0, 3).map(Math.round));
  assert.ok(Math.abs(human[3] - 0.85) < 1e-9, "85% opacity");
  assert.match(tokens.get("--dash-machine") ?? "", /^\d+ \d+$/);
});

test("the projector setting scales type by 1.25 and reduced motion zeroes every duration", () => {
  assert.match(SOURCE, /:root\[data-projector\]\s*\{\s*--scale:\s*1\.25;\s*\}/);
  for (const size of ["display", "title", "note", "body", "small", "mono"]) {
    assert.match(tokens.get(`--fs-${size}`) ?? "", /^calc\(\d+px \* var\(--scale\)\)$/, `--fs-${size} follows --scale`);
  }
  const reduced = SOURCE.match(/@media \(prefers-reduced-motion: reduce\)\s*\{\s*:root\s*\{([^}]*)\}/);
  assert.ok(reduced, "a reduced-motion block on :root");
  const zeroed = declarations(reduced[1]);
  for (const t of ["--t-fast", "--t-base", "--t-slow"]) assert.equal(zeroed.get(t), "0ms", `${t} is 0ms`);
});

test("the resolver matches a browser on a known mix", () => {
  // Half white and half black in sRGB is mid grey, 127.5 per channel.
  const grey = resolveColour("color-mix(in srgb, rgb(255, 255, 255), rgb(0, 0, 0))", new Map());
  assert.deepEqual(grey, [127.5, 127.5, 127.5, 1]);
  // Black on white is the largest ratio there is.
  assert.equal(ratio([0, 0, 0], [255, 255, 255]), 21);
});
