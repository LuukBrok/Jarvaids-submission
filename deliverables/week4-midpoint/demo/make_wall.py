#!/usr/bin/env python3
"""Draw the sticky-note wall the demo photographs.

A drawing, not a photograph, and it says so in its own bottom edge so that a
projector cannot make it look like evidence. The reading that comes back from
the fixture adapter is a stand-in whatever the picture is, so a real photograph
would prove nothing extra and would drag real handwriting and a real room into
the repository. The notes it carries are the three the runbook narrates.

    python3 make_wall.py            # writes wall.png next to this file
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
OUT = HERE / "wall.png"
W, H = 1600, 1000

NOTES = [
    # (x, y, tilt, fill, lines)
    (140, 150, -3, (255, 232, 120), ["Onboarding loses", "people at step 3"]),
    (560, 120, 2, (255, 190, 140), ["Who owns the", "paywall copy?"]),
    (1010, 170, -2, (180, 225, 170), ["Ship the smaller", "version first"]),
    (330, 520, 1, (255, 232, 120), ["Ask Sanne about", "the tablet study"]),
    (820, 540, -1, (200, 210, 250), ["Test with 2 teams", "before Friday"]),
]


def font(size):
    for name in ("DejaVuSans.ttf", "LiberationSans-Regular.ttf", "Arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def main():
    wall = Image.new("RGB", (W, H), (226, 222, 214))
    draw = ImageDraw.Draw(wall)
    # A faint grid so the wall reads as a wall rather than a flat colour.
    for x in range(0, W, 200):
        draw.line([(x, 0), (x, H)], fill=(214, 210, 202), width=2)
    for y in range(0, H, 200):
        draw.line([(0, y), (W, y)], fill=(214, 210, 202), width=2)

    body = font(34)
    for x, y, tilt, fill, lines in NOTES:
        note = Image.new("RGBA", (380, 380), (0, 0, 0, 0))
        nd = ImageDraw.Draw(note)
        nd.rectangle([8, 12, 372, 376], fill=(0, 0, 0, 40))          # shadow
        nd.rectangle([0, 0, 364, 364], fill=fill + (255,))
        for i, line in enumerate(lines):
            nd.text((28, 110 + i * 52), line, font=body, fill=(40, 36, 32, 255))
        note = note.rotate(tilt, resample=Image.BICUBIC, expand=True)
        wall.alpha_composite(note.convert("RGBA"), (x, y)) if wall.mode == "RGBA" else wall.paste(note, (x, y), note)

    caption = font(22)
    draw = ImageDraw.Draw(wall)
    draw.rectangle([0, H - 44, W, H], fill=(60, 56, 52))
    draw.text((20, H - 34), "Drawn stand-in wall for the demo. Not a photograph of a real session.",
              font=caption, fill=(235, 230, 222))
    wall.save(OUT, optimize=True)
    print(f"wrote {OUT.relative_to(HERE.parent.parent.parent)} ({W}x{H})")


if __name__ == "__main__":
    main()
