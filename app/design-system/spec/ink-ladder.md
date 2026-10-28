# The ink ladder

One colour at six strengths, not six greys.

## The rule

Every neutral that carries text or a boundary is `--color-ink` composited over
`--color-canvas` at a stated percentage. There are six steps and the set is
closed. A seventh is a spec change, argued the way a seventh status would be.

| Token | Step | Resolves to | On the ground | Job |
|---|---|---|---|---|
| `--color-ink` | 100% | `#17181b` | 16.86:1 | primary text, and the capturing mark |
| `--color-ink-secondary` | 76% | `#4d4e51` | 7.90:1 | supporting text that is still content |
| `--color-ink-muted` | 68% | `#5f6063` | 5.97:1 | meta, hints, empty states. **The text floor.** |
| `--color-ink-edge` | 50% | `#88888c` | 3.35:1 | a boundary, never text. **The meaning floor.** |
| `--color-ink-fill` | 10% | `#e2e2e6` | 1.23:1 | a pressed state. Carries nothing. |
| `--color-ink-wash` | 6% | `#eaebee` | 1.13:1 | a hover state, a secondary fill. Carries nothing. |

The four ratios that matter are not typed into this table by hand. They come
out of `spec/contrast-check.py`, which evaluates the `color-mix()`
declarations rather than reading hard-coded hexes. A checker that cannot read
the ladder cannot verify it, and an unverifiable ladder is just six greys
again. The two fill steps were measured with the same arithmetic and are
excluded from the generated table, because nothing is ever read against them.

## Why a ladder rather than six greys

Because harmony stops being a judgement and becomes a property.

Six independently chosen greys hold together only as long as everyone choosing
them has good taste and the same reference. One colour at six strengths cannot
clash with itself. You cannot pick a value that breaks the family, because
there is only one colour to pick from and the only remaining decision is how
much of it.

This is also why the new design reads as one object rather than a collection
of parts. It is one hue in tonal steps: the accent in tonal steps for the
interactive layer, and ink in tonal steps for everything else, over one ground.
Nothing was harmonised. There was never anything to harmonise.

## The steps are measured, not chosen

The ground changed from white to `#f8f9fc` and the ink from `#141414` to
`#17181b`, so every step was re-derived over the new pair rather than carried
over. The previous percentages, 100/72/64/48/12/6, would all still have been
legal; the new ones were chosen with margin, because this product is read off a
projector and a projector takes contrast away.

**68% is the text floor.** Ink at 68% is 5.97:1 on the ground. The last legal
step is near 60%, at 4.57:1, which clears 4.5:1 by a rounding error and would
fail on the first washed-out projector. Ink at 56% is already 4.02:1 and
illegal. There is deliberately no step between 68 and 50, because every value
in that gap is legal as a boundary and illegal or marginal as text, and a step
that is legal for one use and illegal for another is a trap rather than a
token.

**76% for secondary** sits two clear steps above the floor, so supporting text
and meta are distinguishable by eye and not only by token name.

**50% is the meaning floor**, the lowest ink kept for a non-text boundary at
1.4.11's 3:1. It measures 3.35:1. Ink at 48% would still pass at 3.15:1 and 46%
fails at 2.96:1, so 50 is the floor with a margin. Below it nothing may carry
meaning. `--color-ink-fill` and `--color-ink-wash` exist to be fills.

**10% and 6%** are the press and hover fills. They are a tone, not a line, so
the "never a fill and a line on one element" rule is what keeps them honest: a
hovered row darkens by tone and does not also gain a border.

## The ground must be known

Every ratio above assumes the ground. This is the constraint that decides where
the ladder may and may not be used.

```
ink at 68% over the ground          5.97:1
ink at 68% over surface-float       6.29:1
ink at 68% over the accent wash     5.37:1
ink at 68% over surface-sunken      5.40:1
ink at 68% over an ink panel        2.82:1     illegal
```

An alpha over a known ground is arithmetic. An alpha over an unknown ground is
a range, and at the wrong end of that range the text is gone. So:

- **The ladder is for opaque grounds.** The ground, surface-float, the accent
  wash and surface-sunken are all known, all four are opaque, and all four are
  measured in `spec/accessibility.md`.
- **The ladder may not be put on a translucent surface** until somebody decides
  that surface's worst-case ground and measures against it. `contrast-check.py`
  measures a foreground against a fixed background; a translucent surface has
  none, so every ratio becomes a range and the system's claim that contrast is
  verified rather than asserted stops being true. That is why the floating
  surfaces in this design are opaque white with a shadow, not frosted.

## What the ladder is not

- **It is not for status colours.** A status may never carry alpha. The
  provisional accent at 55% is 2.69:1 and at 35% is 1.81:1, so dimming a status
  destroys the one distinction the product depends on. `forbidden.md` #17 says
  this; the ladder does not create an exception to it.
- **It is not for the hairlines.** `--color-hairline` and
  `--color-hairline-strong` are very slightly cool and sit off the pure ink
  axis, so they belong to the ground rather than to the text. They stay
  separate tokens with separate jobs. Note that `--color-hairline-strong`
  (3.41:1) and `--color-ink-edge` (3.35:1) now sit within a few units of each
  other: one is a line, the other a boundary step on the ladder, and a reader
  asking why there are two deserves that answer.
- **It is not a dimming mechanism.** If a future state needs to recede, swap
  which step each role binds to. Do not put `opacity` on a container: that dims
  the status colours too, and it does it invisibly.
- **The washes are close to the sunken surface.** `--color-ink-wash`
  (`#eaebee`) and `--color-surface-sunken` (`#ebeef2`) are one unit apart in
  places. A secondary button or a hover tint inside a group panel is therefore
  invisible as a tone. Inside a sunken panel, a hover or a secondary control
  uses `--color-ink-fill` instead, or the control floats.

## Adding a step

Do not. If a screen seems to need a seventh, the likely causes in order are:
too many type roles on one screen, a grouping that wants space rather than a
new tone, or a fill being asked to carry meaning. If a step is genuinely
needed, add it here with its measured ratio, its job, and the argument for why
the existing six could not do it, then re-run `spec/contrast-check.py` and
regenerate the table in `spec/accessibility.md`.
