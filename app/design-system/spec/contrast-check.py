#!/usr/bin/env python3
"""
Reads ../tokens.css, computes the WCAG 2.1 relative-luminance contrast ratio of
every foreground/background pair this design system actually ships, IN EVERY
COLOUR SCHEME IT DECLARES, and reports pass or fail against the AA threshold
for that pair's size class.

It also measures the second thing a colour scheme can break and WCAG says
nothing about: whether the six status marks are still told apart from each
other, and from that scheme's own accent, at 8px dot size.

  python3 spec/contrast-check.py               every check, readable
  python3 spec/contrast-check.py --markdown    the table in spec/accessibility.md
  python3 spec/contrast-check.py --separation  the table in spec/colour-schemes.md

Exit code 0 = every pair in every scheme passes AA and every scheme separates
its marks at least as well as the default scheme does. Non-zero = at least one
of those is untrue.

Thresholds used:
  4.5  normal text (< 18.66px regular / < 24px bold)
  3.0  large text (>= 18.66px regular, >= 24px bold)  [WCAG 1.4.3]
  3.0  non-text: UI component boundaries and state indicators [WCAG 1.4.11]
  none decorative separators that carry no information

--color-ink-fill (12%) and --color-ink-wash (6%) are deliberately not measured,
for the same reason --color-hairline is not: they are fills, they carry no
information, and nothing is ever read against them. If a fill ever has to mean
something it is the wrong step, not a failing pair. The lowest step that may
carry meaning is --color-ink-edge at 48%, and it is measured.

Pairs come in two lists. SCHEME_INDEPENDENT pairs touch only the neutrals and
the documentation diagram colours, which no scheme moves, so they are measured
once. SCHEME_PAIRS touch the accent or a status, so they are measured once per
scheme. Schemes are discovered by reading tokens.css: a scheme that is declared
is a scheme that is measured, and there is no list here to forget to update.

The numbers this prints are the numbers in spec/accessibility.md and in
spec/colour-schemes.md. If you change a token, re-run this and paste the
generated output into those tables. Do not hand-edit either of them.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOKENS = os.path.join(HERE, os.pardir, "tokens.css")


def channel(value):
    v = value / 255.0
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def luminance(hex_colour):
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def ratio(fg, bg):
    a, b = luminance(fg), luminance(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


# ---------------------------------------------------------------------------
# Separation: can you tell the marks apart?
#
# Contrast answers "can you read it against the page". It does not answer "is
# this dot the accepted one or the waiting one", which is the question a status
# dot exists to answer and the one a new colour scheme is most likely to get
# wrong. So this measures CIEDE2000 between every pair of status marks, and
# between every status mark and that scheme's accent.
#
# There is no WCAG threshold for this and no honest absolute one either:
# CIEDE2000 was fitted to large flat patches viewed side by side, not to 8px
# dots seen across a room, so its number is a proxy and not a verdict. The bar
# is therefore relative and taken from the system itself: EVERY SCHEME MUST
# SEPARATE ITS MARKS AT LEAST AS WELL AS THE DEFAULT SCHEME ALREADY DOES.
# The default scheme shipped, so whatever it manages is by definition
# acceptable, and a new scheme that beats it cannot be worse. The real test is
# still looking at schemes.html at small size.
# ---------------------------------------------------------------------------

import math

MARKS = ("capturing", "provisional", "accepted", "waiting", "failed", "off")


def lab(hex_colour):
    h = hex_colour.lstrip("#")
    r, g, b = (channel(int(h[i:i + 2], 16)) for i in (0, 2, 4))
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = (0.2126 * r + 0.7152 * g + 0.0722 * b)
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883

    def f(t):
        return t ** (1.0 / 3.0) if t > 0.008856 else 7.787 * t + 16.0 / 116.0

    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def delta_e(c1, c2):
    """CIEDE2000. Long, and it is the published formula, not a shortened one:
    the cheap sqrt-of-squares version in Lab overstates differences in the
    blues by enough to pass a scheme that is not actually distinguishable."""
    l1, a1, b1 = lab(c1)
    l2, a2, b2 = lab(c2)
    c1ab, c2ab = math.hypot(a1, b1), math.hypot(a2, b2)
    cbar = (c1ab + c2ab) / 2.0
    g = 0.5 * (1 - math.sqrt(cbar ** 7 / (cbar ** 7 + 25.0 ** 7))) if cbar else 0.5
    a1p, a2p = (1 + g) * a1, (1 + g) * a2
    c1p, c2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360 if (a1p or b1) else 0.0
    h2p = math.degrees(math.atan2(b2, a2p)) % 360 if (a2p or b2) else 0.0

    dlp = l2 - l1
    dcp = c2p - c1p
    if c1p * c2p == 0:
        dhp = 0.0
    else:
        dh = h2p - h1p
        dhp = dh - 360 if dh > 180 else dh + 360 if dh < -180 else dh
    dhp = 2 * math.sqrt(c1p * c2p) * math.sin(math.radians(dhp) / 2)

    lbar = (l1 + l2) / 2.0
    cbarp = (c1p + c2p) / 2.0
    if c1p * c2p == 0:
        hbar = h1p + h2p
    elif abs(h1p - h2p) > 180:
        hbar = (h1p + h2p + 360) / 2.0 if h1p + h2p < 360 else (h1p + h2p - 360) / 2.0
    else:
        hbar = (h1p + h2p) / 2.0

    t = (1
         - 0.17 * math.cos(math.radians(hbar - 30))
         + 0.24 * math.cos(math.radians(2 * hbar))
         + 0.32 * math.cos(math.radians(3 * hbar + 6))
         - 0.20 * math.cos(math.radians(4 * hbar - 63)))
    sl = 1 + (0.015 * (lbar - 50) ** 2) / math.sqrt(20 + (lbar - 50) ** 2)
    sc = 1 + 0.045 * cbarp
    sh = 1 + 0.015 * cbarp * t
    rt = (-math.sin(math.radians(2 * 30 * math.exp(-(((hbar - 275) / 25.0) ** 2))))
          * 2 * math.sqrt(cbarp ** 7 / (cbarp ** 7 + 25.0 ** 7)))
    return math.sqrt((dlp / sl) ** 2 + (dcp / sc) ** 2 + (dhp / sh) ** 2
                     + rt * (dcp / sc) * (dhp / sh))


def separation(tokens):
    """(closest two marks, their distance), (closest mark to the accent, its
    distance) for one scheme."""
    marks = {m: tokens["color-status-" + m] for m in MARKS}
    worst_pair = min(
        ((delta_e(marks[a], marks[b]), a, b)
         for i, a in enumerate(MARKS) for b in MARKS[i + 1:]),
        key=lambda row: row[0])
    # Provisional IS the accent by design (tokens.css): a proposed item is where
    # a person can act, and it is told apart by its dashed line and its word,
    # not its colour. Measuring it against the accent would always read 0.0
    # and protect nothing, so the accent half of the check covers the others.
    worst_accent = min(
        ((delta_e(marks[m], tokens["color-accent"]), m) for m in MARKS if m != "provisional"),
        key=lambda row: row[0])
    return worst_pair, worst_accent


# ---------------------------------------------------------------------------
# Reading tokens.css
#
# The file has three kinds of declaration that matter here: --palette-* colour
# primitives, --color-* semantics that alias them, and one [data-scheme] block
# per scheme that repoints the semantics at a different primitive set. This
# reader reproduces that cascade rather than trusting a hand-kept copy of it,
# because a scheme nobody measured is a scheme that ships a failing pair.
# ---------------------------------------------------------------------------

DECL = re.compile(r"(--(?:color|palette)-[a-z0-9-]+):\s*([^;]+);")
HEX = re.compile(r"#[0-9a-fA-F]{6}")
VAR = re.compile(r"var\(\s*(--[a-z0-9-]+)\s*\)")


def body_after(text, index):
    """The contents of the { ... } block that starts at or after `index`."""
    open_at = text.index("{", index)
    depth = 0
    for i in range(open_at, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[open_at + 1:i]
    raise SystemExit("tokens.css: unclosed block at offset %d" % open_at)


def declarations(block):
    out = {}
    for name, value in DECL.findall(block):
        out[name.lstrip("-")] = value.strip()
    return out


MIX = re.compile(
    r"color-mix\(\s*in\s+srgb\s*,\s*"
    r"(#[0-9a-fA-F]{6}|var\(\s*(--[a-z0-9-]+)\s*\))\s+([0-9.]+)%\s*,\s*"
    r"(#[0-9a-fA-F]{6}|var\(\s*(--[a-z0-9-]+)\s*\))\s*\)")


def composite(fg, alpha, bg):
    """source-over of an opaque fg at `alpha` onto an opaque bg, in sRGB.

    The ink ladder is declared as color-mix rather than as six hand-picked
    greys, so this has to exist: a checker that cannot read the ladder cannot
    verify it, and an unverifiable ladder is just six greys again.
    """
    f = [int(fg.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    b = [int(bg.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    return "#%02x%02x%02x" % tuple(
        round(fv * alpha + bv * (1 - alpha)) for fv, bv in zip(f, b))


def resolve(decls, where):
    """Flatten a declaration map to literals, following var() chains and
    evaluating color-mix()."""
    literal = {}
    alias = {}
    mixes = {}
    for name, value in decls.items():
        if HEX.fullmatch(value):
            literal[name] = value
            continue
        mix = MIX.fullmatch(value.strip())
        if mix:
            mixes[name] = (mix.group(1), mix.group(2), float(mix.group(3)) / 100.0,
                           mix.group(4), mix.group(5))
            continue
        ref = VAR.fullmatch(value)
        if ref:
            alias[name] = ref.group(1).lstrip("-")

    for name, target in alias.items():
        seen = {name}
        while target in alias:
            if target in seen:
                raise SystemExit("token alias cycle at --%s (%s)" % (name, where))
            seen.add(target)
            target = alias[target]
        if target not in literal:
            raise SystemExit("--%s aliases --%s, which has no literal value (%s)"
                             % (name, target, where))
        literal[name] = literal[target]

    # Mixes resolve last, so their operands may be literals or aliases. They are
    # not allowed to reference another mix: one level keeps the ladder readable
    # and keeps this loop from needing a topological sort.
    for name, (fg_raw, fg_var, alpha, bg_raw, bg_var) in mixes.items():
        def operand(raw, var_name):
            if var_name is None:
                return raw
            key = var_name.lstrip("-")
            if key not in literal:
                raise SystemExit("--%s mixes --%s, which is not a literal (%s)"
                                 % (name, key, where))
            return literal[key]
        literal[name] = composite(operand(fg_raw, fg_var), alpha,
                                  operand(bg_raw, bg_var))

    return literal


def load_schemes(path):
    """Returns (default_name, [(scheme name, resolved token map), ...]).

    The default scheme is not named in the CSS and is not guessed here: it is
    whichever scheme's accent primitive the unqualified semantic accent
    resolves to. If somebody repoints the default at another scheme's
    primitives and forgets to tell anyone, that is the line that notices.
    """
    text = open(path, encoding="utf-8").read()

    theme = re.search(r"@theme\s*\{", text)
    if theme is None:
        raise SystemExit("tokens.css: no @theme block")
    base = declarations(body_after(text, theme.start()))
    named = []
    for match in re.finditer(r':root\[data-scheme="([a-z0-9-]+)"\]', text):
        named.append((match.group(1), declarations(body_after(text, match.end()))))

    resolved_base = resolve(base, "default")
    default = None
    for name, _ in named + [(n, None) for n in sorted(
            {k.split("-")[1] for k in base if k.startswith("palette-")})]:
        key = "palette-%s-accent" % name
        if key in resolved_base and resolved_base[key] == resolved_base.get("color-accent"):
            default = name
            break
    if default is None:
        raise SystemExit("tokens.css: --color-accent does not resolve to any "
                         "scheme's accent primitive, so the default scheme "
                         "cannot be named")

    schemes = [(default, resolved_base)]
    for name, overrides in named:
        merged = dict(base)
        merged.update(overrides)
        schemes.append((name, resolve(merged, name)))
    return default, schemes


# ---------------------------------------------------------------------------
# The pairs
# ---------------------------------------------------------------------------

# (foreground token, background token, threshold, what this pair is for)
# Neutrals and documentation diagram colours. No scheme moves these, so they
# are measured once and the result holds for every scheme.
SCHEME_INDEPENDENT = [
    ("color-ink",                    "color-canvas", 4.5, "body text on the canvas"),
    ("color-ink-secondary",          "color-canvas", 4.5, "supporting text"),
    ("color-ink-muted",              "color-canvas", 4.5, "meta, hints, empty states (lightest legal grey)"),
    ("color-ink",                    "color-surface-sunken", 4.5, "text in a quoted excerpt"),
    ("color-ink-muted",              "color-surface-sunken", 4.5, "caption in a quoted excerpt"),
    ("color-ink-inverse",            "color-ink", 4.5, "white label on an ink button"),
    ("color-ink",                    "color-surface-float", 4.5, "text in a menu, dialog or the session bar"),
    ("color-ink-muted",              "color-surface-float", 4.5, "meta in a menu, dialog or the session bar"),
    ("color-hairline-strong",        "color-surface-float", 3.0, "a field's edge in a dialog or the session bar (1.4.11)"),
    ("color-hairline-strong",        "color-surface-sunken", 3.0, "a field's or group's edge on a sunken panel (1.4.11)"),

    ("color-diagram-human",          "color-canvas", 4.5, "diagram: a person acts here (documentation only)"),
    ("color-diagram-machine",        "color-canvas", 4.5, "diagram: a model runs here (documentation only)"),
    ("color-diagram-guardrail",      "color-canvas", 4.5, "diagram: a hard limit (documentation only)"),

    ("color-hairline-strong",        "color-canvas", 3.0, "second chart series, chart baseline (1.4.11)"),
    ("color-hairline-strong",        "color-canvas", 3.0, "form field border, canvas item stroke (1.4.11)"),
    ("color-ink",                    "color-canvas", 3.0, "ink: the capturing disc and the chosen tab line (1.4.11)"),

    # The ink ladder. --color-ink, -secondary and -muted are already measured
    # above as text. This is the one step below the text floor that is still
    # allowed to carry meaning, so it is held to 1.4.11 rather than to 1.4.3.
    ("color-ink-edge",               "color-canvas", 3.0, "ink ladder: non-text boundary at 50% (1.4.11)"),
]

# Anything touching the accent or a status. Measured once per scheme.
SCHEME_PAIRS = [
    ("color-ink",                    "color-accent-wash", 4.5, "text in a selected row"),
    ("color-ink-muted",              "color-accent-wash", 4.5, "meta in a selected row"),
    ("color-accent",                 "color-canvas", 4.5, "link, quiet button label, active tab"),
    ("color-accent",                 "color-accent-wash", 4.5, "accent label inside its own tint"),
    ("color-ink-inverse",            "color-accent", 4.5, "white label on the primary button"),
    ("color-ink-inverse",            "color-accent-pressed", 4.5, "white label on the pressed primary button"),

    ("color-status-capturing",       "color-canvas", 3.0, "capturing glyph and its word"),
    ("color-status-provisional",     "color-canvas", 3.0, "proposed glyph, dashed line and word"),
    ("color-status-accepted",        "color-canvas", 3.0, "accepted glyph and word"),
    ("color-status-waiting",         "color-canvas", 3.0, "waiting glyph and word"),
    ("color-status-failed",          "color-canvas", 3.0, "failed glyph and word"),
    ("color-status-off",             "color-canvas", 3.0, "off glyph and word"),

    ("color-status-provisional",     "color-canvas", 4.5, "provisional word as text"),
    ("color-status-accepted",        "color-canvas", 4.5, "accepted word as text"),
    ("color-status-waiting",         "color-canvas", 4.5, "waiting word as text"),
    ("color-status-failed",          "color-canvas", 4.5, "failed word as text"),
    ("color-status-off",             "color-canvas", 4.5, "off word as text"),

    ("color-status-provisional",     "color-status-provisional-wash", 4.5, "provisional chip label on its tint"),
    ("color-status-accepted",        "color-status-accepted-wash", 4.5, "accepted chip label on its tint"),
    ("color-status-waiting",         "color-status-waiting-wash", 4.5, "waiting chip label on its tint"),
    ("color-status-failed",          "color-status-failed-wash", 4.5, "failed chip label on its tint"),
    ("color-status-off",             "color-status-off-wash", 4.5, "off chip label on its tint"),

    ("color-accent",                 "color-canvas", 3.0, "focus ring against the canvas (1.4.11)"),
    ("color-accent",                 "color-surface-sunken", 3.0, "focus ring and accent line on a group panel (1.4.11)"),
    ("color-status-provisional",     "color-surface-sunken", 4.5, "Proposed word inside a group panel"),
]


def missing(tokens, pairs):
    return sorted({t for pair in pairs for t in pair[:2] if t not in tokens})


def measure(tokens, pairs):
    rows = []
    for fg, bg, threshold, label in pairs:
        r = ratio(tokens[fg], tokens[bg])
        rows.append((label, fg, tokens[fg], bg, tokens[bg], r, threshold, r >= threshold))
    return rows


def markdown(rows):
    print("| Pair | Foreground | Background | Ratio | Needs | Result |")
    print("|---|---|---|---|---|---|")
    for label, fg, fgv, bg, bgv, r, threshold, ok in rows:
        print("| %s | %s `%s` | %s `%s` | %.2f:1 | %.1f | %s |" % (
            label, fg.replace("color-", ""), fgv, bg.replace("color-", ""), bgv,
            r, threshold, "PASS" if ok else "FAIL"))
    print()
    failures = sum(0 if row[7] else 1 for row in rows)
    print("**%d pairs checked, %d failing.**" % (len(rows), failures))
    return failures


def plain(rows, width):
    print("%-*s  %-24s  %-24s  %7s  %6s  %s" % (
        width, "pair", "foreground", "background", "ratio", "needs", "result"))
    print("-" * (width + 78))
    for label, fg, fgv, bg, bgv, r, threshold, ok in rows:
        print("%-*s  %-24s  %-24s  %6.2f:1  %5.1f   %s" % (
            width, label,
            "%s %s" % (fg.replace("color-", ""), fgv),
            "%s %s" % (bg.replace("color-", ""), bgv),
            r, threshold, "PASS" if ok else "FAIL"))
    print()
    failures = sum(0 if row[7] else 1 for row in rows)
    print("%d pairs checked, %d failing." % (len(rows), failures))
    return failures


def separation_rows(default, schemes):
    """One row per scheme, plus the bar taken from the default scheme."""
    measured = [(name, separation(tokens)) for name, tokens in schemes]
    bar = dict(measured)[default]
    return measured, bar


def main():
    default, schemes = load_schemes(TOKENS)
    gone = missing(schemes[0][1], SCHEME_INDEPENDENT + SCHEME_PAIRS)
    if gone:
        print("tokens.css is missing: " + ", ".join(gone))
        return 2

    measured, bar = separation_rows(default, schemes)
    (bar_pair, bar_accent) = bar
    sep_failures = sum(
        1 for _, (pair, accent) in measured
        if pair[0] < bar_pair[0] - 0.05 or accent[0] < bar_accent[0] - 0.05)

    if "--separation" in sys.argv:
        print("| Scheme | Closest two marks | Closest mark to the accent | At least as separated as %s |"
              % default)
        print("|---|---|---|---|")
        for name, (pair, accent) in measured:
            ok = pair[0] >= bar_pair[0] - 0.05 and accent[0] >= bar_accent[0] - 0.05
            print("| %s%s | %s and %s, %.1f | %s, %.1f | %s |" % (
                name, " (the default)" if name == default else "",
                pair[1], pair[2], pair[0], accent[1], accent[0],
                "sets the bar" if name == default else ("PASS" if ok else "FAIL")))
        print()
        print("**The bar is the default scheme's own worst case: %.1f between two marks, "
              "%.1f between a mark and the accent. CIEDE2000, %d schemes, %d below the bar.**"
              % (bar_pair[0], bar_accent[0], len(measured), sep_failures))
        return 1 if sep_failures else 0

    as_markdown = "--markdown" in sys.argv
    total = 0
    failures = 0

    if as_markdown:
        print("### Pairs no scheme moves")
        print()
        rows = measure(schemes[0][1], SCHEME_INDEPENDENT)
        failures += markdown(rows)
        total += len(rows)
        for name, tokens in schemes:
            print()
            print("### Scheme: %s%s" % (name, " (the default)" if name == default else ""))
            print()
            rows = measure(tokens, SCHEME_PAIRS)
            failures += markdown(rows)
            total += len(rows)
        print()
        print("**%d pairs checked across %d schemes, %d failing.**"
              % (total, len(schemes), failures))
        return 1 if failures else 0

    width = max(len(p[3]) for p in SCHEME_INDEPENDENT + SCHEME_PAIRS)
    print("PAIRS NO SCHEME MOVES")
    print()
    rows = measure(schemes[0][1], SCHEME_INDEPENDENT)
    failures += plain(rows, width)
    total += len(rows)
    for name, tokens in schemes:
        print()
        print("SCHEME: %s%s" % (name.upper(), "  (the default)" if name == default else ""))
        print()
        rows = measure(tokens, SCHEME_PAIRS)
        failures += plain(rows, width)
        total += len(rows)

    print()
    print("%d pairs checked across %d schemes (%s), %d failing."
          % (total, len(schemes), ", ".join(n for n, _ in schemes), failures))

    print()
    print("SEPARATION  (CIEDE2000, not a WCAG measure: see the note in this file)")
    print()
    print("%-12s  %-34s  %-30s  %s" % (
        "scheme", "closest two marks", "closest mark to the accent", "result"))
    print("-" * 100)
    for name, (pair, accent) in measured:
        ok = pair[0] >= bar_pair[0] - 0.05 and accent[0] >= bar_accent[0] - 0.05
        print("%-12s  %-34s  %-30s  %s" % (
            name,
            "%s / %s  %.1f" % (pair[1], pair[2], pair[0]),
            "%s  %.1f" % (accent[1], accent[0]),
            "SETS THE BAR" if name == default else ("PASS" if ok else "FAIL")))
    print()
    print("The bar is %s's own worst case: %.1f between two marks, %.1f between a "
          "mark and the accent." % (default, bar_pair[0], bar_accent[0]))
    print("%d schemes checked, %d below the bar." % (len(measured), sep_failures))

    return 1 if (failures or sep_failures) else 0


if __name__ == "__main__":
    sys.exit(main())
