# Audit

What counts as off-system, and how to check it by hand.

The mechanical half runs. The judgement half does not, and cannot: greps catch
literals, and most of the ways this system gets broken are judgement calls. The
looking half of this file, section 5, still matters more than section 2. But
"most" is not "all", and everything that can be checked is now checked by a
script with an exit code rather than by a reader copying commands out of a
document.

```sh
spec/audit.sh                 # the application source
spec/audit.sh app/client      # or a path you name
```

Exit 0 is clean, exit 1 means at least one check found something. It resolves
`contrast-check.py` from its own location, so there is exactly one path to that
script and it runs from any working directory.

**It never audits the design system's own files.** This is where the literals
are supposed to live. An earlier version of this document said to run the greps
over `app/`, which returned 159 hits on a repo with no application UI in it at
all, every one of them from the design system quoting itself. An audit whose
first run is entirely noise is an audit that gets dismissed once and never run
again.

---

## 1. Automated: the contrast check

Run on its own when you want the table rather than a pass or fail.

```sh
python3 app/design-system/spec/contrast-check.py   # or just: spec/audit.sh
```

Exit 0 means every shipped foreground/background pair meets AA for its size
class. If you added a colour pair and did not add it here, this check passes
while your screen fails, so **adding the pair is part of adding the colour**.

## 2. Automated: literals that should be tokens

What `spec/audit.sh` checks, all of it inside `spec/audit.sh`:

| Check | Catches |
|---|---|
| contrast | any declared pair below AA for its size class |
| raw hex | a colour that is not a token |
| arbitrary radii | a literal that is not 2px, 4px or 999px. The 8px and 16px steps must be written as `--radius-md` and `--radius-lg` |
| non-system typefaces | a second face, however it is spelled |
| one breakpoint | any width query other than 1023/1024px |
| arbitrary line widths | line weight carries meaning here, so it is tokenised |
| Tailwind palette | `bg-blue-500` and its whole family |
| shadows on content | any `box-shadow` that is not `none` or one of `--elevation-sm/md/lg`. Whether the element carrying it actually floats is judgement, section 5 |
| toasts and spinners | neither exists; nothing loops |
| network fonts | a CDN font in a product that records people |
| glyphs as icons | `✓` and `×` standing in for an icon |
| provisional is never dimmed | forbidden.md #17 |
| provisional is never a plain fill | forbidden.md #16 |

The last two are new. The A/B audit against the reference system found that the
three rules carrying the product's central claim, forbidden.md #16, #17 and
#18, were the only ones left entirely to human judgement, which is the wrong
half to leave unenforced: they are the rules that, broken once, make the
product dishonest. Two of the three turned out to be mechanically checkable.
The third, that model output is never rendered identically to team output, is
still a judgement call and is in section 5.

### A note on the regexes, because they were wrong

Three checks in an earlier version of this file used PCRE lookaheads under
`grep -E`, which does not support them. They printed `grep: warning: ? at start
of expression` and then matched the wrong thing: the radius check matched the
LEGAL `border-radius: 4px` and missed the illegal `6px`, and the typeface check
exited clean on `font-family: Comic Sans`. An off-system typeface passed the
audit.

The fix is `grep -P` and a possessive `\s*+`. Without the possessive quantifier
the `\s*` backtracks to zero width, the lookahead then succeeds against the
space rather than the value, and the check inverts again while looking correct.
Every regex in `audit.sh` is tested against a legal fixture and an illegal one
before it ships. If you add a check, add both fixtures.

## 3. Greps: the rules specific to this product

Not yet in `audit.sh`, because each of these needs a human to read the hit and
decide. They are filters that produce candidates, not checks that produce
verdicts. Point `SRC` at application source, never at this directory.

```sh
SRC=app/client

# A div that is really a button loses focus, Escape and screen-reader semantics
grep -rnE '<div[^>]*onClick' $SRC

# The focus ring is never removed
grep -rniE 'outline:\s*none|outline-none|focus:outline-none' $SRC

# A status colour used as a chart series or a category is a reserved-set breach
grep -rn 'status-provisional\|status-accepted\|status-waiting\|status-failed' $SRC | grep -i 'chart\|series\|category\|legend'

# surface-sunken outside its permitted uses: group panel, accepted note,
# excerpt, skeleton, photograph placeholder
grep -rn 'surface-sunken' $SRC | grep -viE 'group|panel|accepted|skeleton|placeholder|excerpt|quote|crop'

# A fill and a line on the same element: candidates, read each one
grep -rnE 'background:[^;]*var\(--color-(surface-sunken|accent-wash|ink-wash)' $SRC | grep -E 'border:'

# Uppercase labels and pulses are gone from the system
grep -rnE 'text-transform:\s*uppercase|@keyframes|animation:[^;]*infinite' $SRC

# Flexible grid columns without minmax(0, ...)
grep -rnE 'grid-template-columns:[^;]*\b1fr' $SRC | grep -v 'minmax(0'
```

## 4. Greps: the exemplars and the specimen must open offline

```sh
grep -rnE '(src|href)="https?://' app/design-system/
grep -rn 'http' app/design-system/specimen.html app/design-system/spec/exemplars/
```

Both should return nothing.

## 5. Looking: the things a grep cannot catch

This is the part that matters. Do it on a real screen, at 1440 and at 400.

**The provisional distinction.** Squint at the screen from two metres. Can you
tell what the team made from what the model guessed, without reading anything?
If not, nothing else on this list counts. Check specifically that:

- the provisional item has a dashed line, the dashed-ring glyph and the word
  "Proposed", because its colour is the accent and cannot tell it apart
- the provisional text is not greyed
- the provisional item has no fill; an accepted item has the tonal fill and no
  line; a person's unreviewed note has a solid line and no fill
- nothing on the canvas moved to make room for model output (F3.4)

**Type roles.** Every piece of text is one of the six roles. Nothing is
uppercase, nothing is below 12px, nothing is weight 700, and every table row is
body text except its machine fields.

**The accent.** Find every blue thing on the screen. Each one should be
something you can act on, the focus, or a provisional item. A blue heading, a
blue rule, a blue section theme, a blue outline round a container, or a second
hue anywhere are all wrong.

**Status.** Every status is a shaped glyph with a word next to it. Every
status word means what `spec/tokens.md` says it means. No seventh colour has
crept in, and nothing pulses.

**Separation.** Space first, then `--color-surface-sunken`, then a line. Is
any element carrying both a fill and a line? Is anything in the page, rather
than floating above it, carrying a shadow? Both are wrong.

**Degradation.** Turn the model off, or fake it. Does the interface say what
broke and what still works? Is there a silent gap anywhere? Does capture keep
running and does the interface say so? (F6.4)

**Citations.** Find every claim the model makes on the screen. Does each one
carry a timestamp you can click? An answer without one should not have
rendered at all. (F6.3)

**Consent.** On any screen where capture could be running, is the recording
indicator visible without scrolling, and can it be hidden or collapsed? It
should not be possible. (F1.1, F6.1)

**Keyboard.** Tab through the whole screen. Is the ring always visible? Does
the order match what you see? Does Escape close things? On the review queue, do
`A`, `E` and `R` work and are they shown in the toolbar?

**400px.** Open the screen at 400px wide. Is there a horizontal scrollbar on
the body? Is every hover-revealed action visible on a coarse pointer? Are
targets 44px there?

**Room mode.** Set `data-room` on `<html>` at 1440px. Is the type 1.5 times
larger, is every target 44px, and does nothing overflow?

## 6. Before merging

- [ ] `spec/audit.sh` exits 0, which covers sections 1 and 2
- [ ] The section 3 greps return nothing, or each hit is deliberately explained
      in the pull request
- [ ] `spec/checklist.md` completed for the screen
- [ ] You have looked at the screen at 400px and at 1440px

---

## What this audit does not catch

Stated plainly, because a checklist that implies completeness is worse than one
that admits its holes.

- **Judgement.** Whether a timeline was the right form for that content, whether
  the copy is honest, whether a confirmation was warranted. No grep helps.
- **Contrast in the room.** The numbers in `spec/accessibility.md` are computed
  on an ideal display. A projector crushes contrast badly and nobody has tested
  this on one.
- **Screen readers.** The semantics are specified; whether they actually work
  in NVDA, JAWS or VoiceOver is unverified.
- **The canvas as a keyboard surface.** The parallel list view is a mitigation,
  not a solution, and this audit cannot tell you whether it is enough.
- **Regressions over time.** Sections 1 and 2 run in CI on every pull request
  (`.github/workflows/verify.yml`, job `design-system`). The greps in section 3
  and the looking in section 5 still get run when someone remembers.
- **Whether a shadow is on a floating surface.** The audit accepts any
  elevation token wherever it appears; putting `--elevation-md` on a note
  passes the grep and breaks the design.
