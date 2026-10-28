# Colour schemes

The system has **one scheme, delft**: a single blue accent in tonal steps, with
the six status colours that sit beside it. The previous system shipped four
interchangeable schemes; the new design removes them, because the design's
first principle is one hue per screen, and four ways to pick that hue were four
ways to argue about it instead of one decision.

The **mechanism stays**. A future scheme is a block in `tokens.css`, not a
rewrite, and the contrast check finds it by itself. This file describes the
mechanism, the one scheme, what removing the other three cost, and how to add
one if a real need appears.

Read `tokens.md` first. This file assumes the token vocabulary.

## What a scheme may touch

| Moves with the scheme | Never moves |
|---|---|
| `--color-accent`, `--color-accent-pressed`, `--color-accent-wash` | every neutral: the ground, both surfaces, the whole ink ladder |
| `--color-status-provisional`, `-accepted`, `-waiting`, `-failed`, `-off` | both hairlines |
| each of those five washes | the three `--color-diagram-*` documentation colours |
| | `--color-status-capturing`, which is ink |

The neutrals stay because they are what everything else is measured against.
Move the ground and every contrast number in `accessibility.md` is stale at
once, every hairline is re-opened, and the provisional line has to be
re-decided. That is dark mode, it is banned in `forbidden.md` #28, and it is
not what "a scheme" means.

The diagram colours stay because they belong to the team's documentation,
which is written once and read alongside the product. A scheme-dependent
diagram colour would mean the same architecture drawing said different things
in different rooms.

**A scheme that sets anything outside the left column is not a colour scheme.**
If a block in `tokens.css` under `[data-scheme]` ever assigns a neutral, a
hairline, a radius, a size or a line width, that is the bug.

## How it works

Three layers.

```
--palette-delft-accent: #114fa2;                primitive   named by appearance
--color-accent: var(--palette-delft-accent);    semantic    named by job
class="jv-link"  →  color: var(--color-accent)  component   binds the semantic
```

**Components bind semantics only.** Never a primitive, never a literal. That
one rule is what makes a scheme possible: a scheme works by repointing
semantics at a different primitive set, so a component that reached past the
semantic layer would simply not change, and the bug would show up as one
stubborn blue thing on a screen of another hue.

The rule is also enforced by naming rather than by trust. Primitives are
`--palette-*`, not `--color-*`. Tailwind v4 generates a utility class for every
token in the `--color-*` namespace and none for `--palette-*`, so there is no
`bg-palette-delft-accent` to reach for by accident. The audit's raw-hex check
catches the other half.

### Selecting a scheme

With no attribute the semantics resolve to **delft**, the only scheme. A
future scheme would be selected with `<html data-scheme="<name>">`, and
`[data-scheme]` on the root beats the plain `:root` block on specificity, so
there is no ordering problem and no `!important` anywhere.

## Delft, the one scheme

A single blue accent `#114fa2`, from a tonal family that runs from a tint
`#e3eefe` to a deep text-on-tint `#01204e`.

**Character.** One hue in tonal steps over a slightly cool ground. The blue is
the conventional colour of a link, so the affordance is learned before anybody
walks into the room, and the accent recedes into the page instead of
announcing itself. The canvas, and the team's own material on it, stays the
loudest thing on screen.

**Provisional is the accent.** `--palette-delft-provisional` is the same
`#114fa2`. A provisional item is exactly where a person can act, which is the
accent's meaning; a second hue for provenance would put two hues on every
screen with model output on it. Provisional is told from an ordinary accent use
by its dashed line, its dashed-ring glyph and the word "Proposed".

**Waiting moved out of the blue** and is an ochre `#8a5300`, so it does not sit
on the accent.

**Costs.** Three, stated plainly.

1. **Colour no longer separates provisional from the accent at all.** The
   separation measure below reports 0.0 for that pair, by design. On a screen
   with an accent button next to a provisional note, only the dash, the glyph
   and the word tell them apart. That is the order of signals the system always
   claimed, and it is now the only order.
2. **Waiting is an ochre close in hue to the failure red.** It measures clear
   of it, but it leans on the half-filled ring and the word more than a blue
   did, and the word is not optional anyway.
3. **A projector with a cool white balance desaturates blue more than it
   desaturates warm colours**, and this product lives on projectors. Untested
   in a real room, like every other contrast claim in this repo.

## What removing the other schemes cost

The previous system carried four schemes on one mechanism. They are gone from
`tokens.css`, from `schemes.html` and from the contrast table.

- **Gained:** one hue to learn, one set of numbers, one page to look at, and a
  contrast table of 40 pairs instead of 105. Every exemplar is built on the
  one scheme there is, so there is no scheme with no use evidence behind it.
- **Lost:** the ability to pick a warmer or more distinctive accent for a
  particular room without a change to `tokens.css`. If that need is evidenced,
  the mechanism is still there and the steps are below.

## The proof

Every scheme has to satisfy every constraint. There are three, and all three
are measured rather than judged.

### 1. Contrast

Every foreground and background pair. `spec/accessibility.md` holds the
generated table: **40 pairs, 0 failing.** That is fifteen pairs no scheme moves
plus twenty-five measured for the scheme.

```sh
python3 spec/contrast-check.py              # every pair, every scheme
python3 spec/contrast-check.py --markdown   # the table in accessibility.md
```

The script reads the `[data-scheme]` blocks out of `tokens.css`, so a scheme
that is declared is a scheme that is measured, and there is no second list to
forget to update.

### 2. Separation

Contrast says a mark can be read against the page. It does not say a mark can
be told from the mark next to it. So every scheme is also measured with
CIEDE2000, between every pair of status marks and between every mark and that
scheme's own accent. **The bar is taken from the default scheme, not
invented.**

```sh
python3 spec/contrast-check.py --separation   # the table below, generated
```

| Scheme | Closest two marks | Closest mark to the accent | At least as separated as delft |
|---|---|---|---|
| delft (the default) | capturing and off, 21.2 | off, 24.3 | sets the bar |
**The bar is the default scheme's own worst case: 21.2 between two marks, 24.3 between a mark and the accent. CIEDE2000, 1 schemes, 0 below the bar.**

How to read this now that provisional is the accent:

- **21.2 between two marks is the bar that means something.** It is ink
  against the off grey, and it is wider than the previous system's worst pair
  (17.5), because the violet that sat close to the old waiting blue is gone.
- **Provisional is left out of the accent half, by design.** The provisional
  mark is the accent, so measuring it against the accent would always read 0.0
  and protect nothing. The script measures the closest mark to the accent
  other than provisional: off, at 24.3. A future scheme has to keep every
  other status at least that far from its accent.

Two honest limits on these numbers. CIEDE2000 was fitted to large flat patches
seen side by side, not to 16px glyphs seen across a room, so it is a proxy and
not a verdict: the real test is opening `schemes.html` and looking at the
glyphs at the size they are drawn. And it says nothing about colour blindness,
which is handled by the rule that never changed, that status is a shape **and**
a word.

### 3. The rules that do not bend

- **Red is reserved for failure.** `--color-status-failed` is `#a81f1a`. A
  scheme does not get to spend red on anything else.
- **Capturing is ink, not red.** It is not in any scheme's primitive block at
  all: it binds straight to `--color-ink`. This product needs red for failure,
  one colour for "working" and "broken" is worse than breaking the
  recording-light convention, and ink is the one status mark that cannot
  collide with any accent, present or future. The indicator is a filled disc,
  a word and a running timer, three signals. **A scheme that wants to move it
  is proposing to re-open that argument, and the argument, not the hex, is the
  thing to beat.**
- **Off is a neutral grey**, `#595959`. It means nothing is happening, and a
  tint would be a hue with no meaning attached.
- **Status meanings do not move.** Only the hues may. That is why every rule in
  this system is written in terms of `--color-status-accepted` and never in
  terms of green.
- **Provisional is told apart by shape and word, never by hue.** A future
  scheme may give provisional a hue of its own only by arguing against the
  one-hue rule in `principles.md`, not by quietly adding one.

## Adding a scheme

1. Add a `--palette-<name>-*` block to `tokens.css`: accent, accent-pressed,
   accent-wash, five statuses, five washes, and the tonal steps of the accent.
   Washes are computed and written out as literals, so the stated rule and the
   values agree.
2. Add the matching `:root[data-scheme="<name>"]` block. Semantics only.
   Nothing outside the left column of the table at the top of this file.
3. Run `python3 spec/contrast-check.py`. It finds the new scheme by itself. It
   must exit 0, which means both AA and the separation bar.
4. Regenerate `--markdown` into `spec/accessibility.md` and `--separation` into
   this file. Do not hand-edit either table.
5. Add the scheme to `schemes.html` and **look at the glyphs at 16px**, at
   1440px and at 400px. A number is not a look.
6. Write down its character, what it is for and what it costs. A scheme that is
   only "the green one" is not worth shipping, and a scheme that puts a second
   hue on a screen is not a scheme, it is a different design.

## Topic and paper colour (F3.8)

A photographed note's paper colour is evidence, so it is shown as a **small
swatch on the note, never as its fill**. A fill in a second hue would break the
one-hue rule and would make a yellow note and a pink note look like two kinds
of thing when they are one kind on two papers.

The planned topic fills in `expandable-notes.md` predate the one-hue rule and
conflict with it. Until that contract is revised, topic is said by the group
label and the group panel's tone, and at most by a swatch, never by a fill. No
categorical palette exists in `tokens.css`, and none should be added under
this mechanism: a categorical palette is not a scheme.
