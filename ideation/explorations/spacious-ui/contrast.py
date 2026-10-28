#!/usr/bin/env python3
"""
Composited contrast checker for the spacious-ui explorations.

The luminance maths is lifted verbatim from
app/design-system/spec/contrast-check.py. What is added here is the thing that
makes an opacity-driven aesthetic dangerous: a colour written as
`rgb(20 20 20 / 0.6)` is NOT the colour the token says it is. The browser
composites it over whatever is behind it, and the ratio you get is the ratio of
the composited value, not of the token.

So every pair below is declared as (ink token, alpha, stack of backgrounds it is
composited over). The script flattens the stack, composites the foreground, and
reports the real ratio.

Usage:
  python3 contrast.py            print every table
  python3 contrast.py --html     print the tables as HTML <tr> rows
  python3 contrast.py air        print one exploration's table
"""
import sys

# ---------------------------------------------------------------- maths ----


def channel(value):
    v = value / 255.0
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def luminance(rgb):
    r, g, b = rgb
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def ratio(fg, bg):
    a, b = luminance(fg), luminance(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def tohex(rgb):
    return "#%02x%02x%02x" % tuple(int(round(c)) for c in rgb)


def over(fg, alpha, bg):
    """Source-over compositing, the same thing the compositor does."""
    return tuple(fg[i] * alpha + bg[i] * (1 - alpha) for i in range(3))


def flatten(stack):
    """stack is [(colour, alpha), ...] painted back to front onto white."""
    out = (255.0, 255.0, 255.0)
    for colour, alpha in stack:
        out = over(hexrgb(colour) if isinstance(colour, str) else colour, alpha, out)
    return out


# --------------------------------------------------------------- tokens ----

INK = "#141414"
ACCENT = "#a85a00"
PROVISIONAL = "#5b46be"
ACCEPTED = "#1d7344"
WAITING = "#19608c"
FAILED = "#a81f1a"
OFF = "#595959"
WHITE = "#ffffff"
SUNKEN = "#f7f7f5"
HAIRLINE_STRONG = "#8a8a86"

# The ink alpha ladder the explorations use in place of the three grey tokens.
# Values chosen so that every step is legal at the size class it is used for,
# which is why they are not a round 80/60/40.
LADDER = [
    (1.00, "primary: the thing the screen is about", 4.5),
    (0.78, "secondary: supporting content, read word by word", 4.5),
    (0.64, "meta: times, counts, hints. THE TEXT FLOOR.", 4.5),
    (0.48, "edge: non-text that must be seen, 1.4.11", 3.0),
    (0.12, "field: decorative rule, carries no information", 1.0),
]


def ladder_rows(stack, stack_label):
    rows = []
    bg = flatten(stack)
    for alpha, job, need in LADDER:
        fg = over(hexrgb(INK), alpha, bg)
        rows.append((
            "ink %d%% %s" % (round(alpha * 100), stack_label),
            tohex(fg), tohex(bg), ratio(fg, bg), need, job))
    return rows


# ----------------------------------------------------------- the tables ----

def table_air():
    """01 Air uses the shipped tokens unchanged. Nothing composited."""
    rows = []
    for fg, bg, need, job in [
        (INK, WHITE, 4.5, "item text, headings"),
        ("#545454", WHITE, 4.5, "supporting text"),
        ("#636363", WHITE, 4.5, "meta line under an item"),
        (ACCENT, WHITE, 4.5, "citation timestamp, primary button label ground"),
        (WHITE, ACCENT, 4.5, "label on the primary button"),
        (PROVISIONAL, WHITE, 4.5, "provisional word and dashed stroke"),
        (WAITING, WHITE, 4.5, "queued word"),
        (FAILED, WHITE, 4.5, "unreadable word"),
        (ACCEPTED, WHITE, 4.5, "accepted word"),
        (HAIRLINE_STRONG, WHITE, 3.0, "secondary button border, 1.4.11 non-text"),
        (INK, WHITE, 3.0, "accepted item stroke, 1.4.11 non-text"),
    ]:
        rows.append((job, tohex(hexrgb(fg)), tohex(hexrgb(bg)),
                     ratio(hexrgb(fg), hexrgb(bg)), need, "shipped token, no alpha"))
    return rows


def table_vellum():
    """02 Vellum. Three layers over the live canvas:
         scrim  30% white + blur   (the canvas is pushed back, still visible)
         sheet  86% white + blur   (the review surface)
         panel  92% white          (the one item under review)
    The ground that matters is not white. It is whatever the canvas puts
    behind the sheet, and the darkest thing the canvas can put there is a 100%
    ink item stroke. Every row below is measured on THAT, not on white."""
    scrim = [(WHITE, 0.30)]
    sheet = [(WHITE, 0.30), (WHITE, 0.86)]
    panel = [(WHITE, 0.30), (WHITE, 0.86), (WHITE, 0.92)]
    worst_sheet = flatten([(INK, 1.0)] + sheet)
    worst_panel = flatten([(INK, 1.0)] + panel)
    rows = []
    for alpha, job, need in LADDER:
        fg = over(hexrgb(INK), alpha, worst_sheet)
        rows.append(("ink %d%% on the sheet, ink stroke behind it" % round(alpha * 100),
                     tohex(fg), tohex(worst_sheet), ratio(fg, worst_sheet), need, job))
    for alpha, job, need in LADDER:
        fg = over(hexrgb(INK), alpha, worst_panel)
        rows.append(("ink %d%% on the inner panel, ink stroke behind it" % round(alpha * 100),
                     tohex(fg), tohex(worst_panel), ratio(fg, worst_panel), need, job))
    for colour, name, need in [(PROVISIONAL, "provisional chip", 4.5),
                               (FAILED, "unreadable chip", 4.5),
                               (ACCEPTED, "accepted mark", 4.5)]:
        rows.append(("%s at 100%% on the sheet, ink stroke behind it" % name,
                     colour, tohex(worst_sheet), ratio(hexrgb(colour), worst_sheet), need,
                     "status never takes alpha"))
    rows.append(("citation link at 100% on the inner panel",
                 ACCENT, tohex(worst_panel), ratio(hexrgb(ACCENT), worst_panel), 4.5,
                 "the accent lives on the panel, not on the sheet: see the note"))
    # What the canvas itself looks like once the scrim is over it. This is not
    # a text pair, it is the evidence that the background is still PRESENT.
    behind = flatten([(INK, 1.0), (WHITE, 0.30)])
    rows.append(("canvas ink beside the sheet, under the scrim only",
                 tohex(behind), "#ffffff", ratio(behind, (255.0, 255.0, 255.0)), 3.0,
                 "visible as shape, no longer readable as text: intended"))
    ghost = flatten([(INK, 1.0)] + sheet)
    rows.append(("canvas ink seen THROUGH the sheet",
                 tohex(ghost), "#ffffff", ratio(ghost, (255.0, 255.0, 255.0)), 1.0,
                 "the ghost. Deliberately below every threshold."))
    return rows


def table_column():
    """03 Column: no surfaces at all. Only the ink ladder on white."""
    return ladder_rows([], "on white")


def table_glance():
    """04 Glance: outer container is ink at 4% over white, inner panel is white
    at 100% sitting inside it. Concentric, so two grounds."""
    outer = [(INK, 0.04)]
    inner = [(INK, 0.04), (WHITE, 1.0)]
    rows = []
    rows += ladder_rows(outer, "on the outer container")
    rows += ladder_rows(inner, "on the inner panel")
    bg_outer = flatten(outer)
    for colour, name in [(ACCEPTED, "agreed"), (OFF, "not yet"), (ACCENT, "action")]:
        rows.append((
            "%s at 100%% on the outer container" % name,
            colour, tohex(bg_outer), ratio(hexrgb(colour), bg_outer), 4.5,
            "status colour never takes alpha"))
    return rows


def table_attenuation():
    """05 Attenuation: the page re-weights by alpha. Attenuated content is still
    content, so it must stay legal, which is the whole constraint."""
    rows = ladder_rows([], "on white")
    bg = (255.0, 255.0, 255.0)
    # What the screen DOES: attenuated ink text stops at the 64% text floor,
    # and status colour is never attenuated at all. Both shown.
    for colour, name in [(PROVISIONAL, "provisional"), (FAILED, "unreadable"),
                         (ACCEPTED, "accepted")]:
        rows.append((
            "%s at 100%% inside an attenuated region" % name,
            colour, "#ffffff", ratio(hexrgb(colour), bg), 4.5,
            "status keeps full strength: see the note below the table"))
    # What the screen REFUSES to do, kept in the table as the evidence for why.
    for alpha in (0.55, 0.35):
        fg = over(hexrgb(PROVISIONAL), alpha, bg)
        rows.append((
            "REJECTED: provisional dimmed to %d%%" % round(alpha * 100),
            tohex(fg), "#ffffff", ratio(fg, bg), 4.5,
            "this is why status colour is never dimmed"))
    fg = over(hexrgb(INK), 0.55, bg)
    rows.append((
        "REJECTED: ink body text dimmed to 55%",
        tohex(fg), "#ffffff", ratio(fg, bg), 4.5,
        "0.05 below the alpha floor and it is already illegal"))
    return rows


TABLES = {
    "air": ("01 Air", table_air),
    "vellum": ("02 Vellum", table_vellum),
    "column": ("03 Column", table_column),
    "glance": ("04 Glance", table_glance),
    "attenuation": ("05 Attenuation", table_attenuation),
}


def main_key(key):
    """Print just the <tr> rows for one table. Used by inject.py."""
    _, fn = TABLES[key]
    for label, fg, bg, r, need, note in fn():
        rej = label.startswith("REJECTED")
        ok = r >= need
        cls = ' class="rej"' if rej else ""
        result = "fails, not used" if rej else ("pass" if ok else "FAIL")
        print('<tr%s><td>%s</td><td><code>%s</code></td><td><code>%s</code></td>'
              '<td class="n">%.2f:1</td><td class="n">%.1f</td><td>%s</td></tr>'
              % (cls, label, fg, bg, r, need, result))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    as_html = "--html" in sys.argv
    keys = args or list(TABLES)
    failures = 0
    for key in keys:
        title, fn = TABLES[key]
        rows = fn()
        if as_html:
            print("<!-- %s -->" % title)
        else:
            print("\n== %s ==" % title)
            print("%-52s %-9s %-9s %8s %6s  %s" % (
                "pair", "composited", "ground", "ratio", "needs", "result"))
        for label, fg, bg, r, need, note in rows:
            ok = r >= need
            if label.startswith("REJECTED"):
                # Kept in the table as evidence. A fail here is the point.
                if as_html:
                    print('<tr class="rej"><td>%s</td><td><code>%s</code></td>'
                          '<td><code>%s</code></td><td class="n">%.2f:1</td>'
                          '<td class="n">%.1f</td><td>fails, not used</td></tr>'
                          % (label, fg, bg, r, need))
                else:
                    print("%-52s %-9s %-9s %7.2f:1 %6.1f  fails, not used   %s"
                          % (label, fg, bg, r, need, note))
                continue
            failures += 0 if ok else 1
            if as_html:
                print('<tr><td>%s</td><td><code>%s</code></td><td><code>%s</code></td>'
                      '<td class="n">%.2f:1</td><td class="n">%.1f</td><td>%s</td></tr>'
                      % (label, fg, bg, r, need, "pass" if ok else "FAIL"))
            else:
                print("%-52s %-9s %-9s %7.2f:1 %6.1f  %s   %s" % (
                    label, fg, bg, r, need, "pass" if ok else "FAIL", note))
    if not as_html:
        print("\n%d failing." % failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
