# Accessibility

Target: **WCAG 2.1 AA.** Contrast is verified. The rest is specified, and two
Level A criteria are known to be unmet today, so **the product does not conform
yet.** Saying otherwise would be the same dishonesty this system exists to
prevent on the canvas.

What is verified: 40 foreground and background pairs, computed from the
shipped token values by `spec/contrast-check.py`. All 40 pass 1.4.3 and 1.4.11.
That is fifteen pairs no colour scheme moves, plus twenty-five pairs measured
for the one scheme, delft, in `spec/colour-schemes.md`. The new design has one
hue, so there is one scheme to measure; the mechanism still measures any
scheme that is declared.

What is not met:

- **SC 2.1.4 Character Key Shortcuts, Level A.** The review queue's single
  character shortcuts have no off switch, no remap and no focus scope. The fix
  is specified in `spec/announcements.md` and is not yet applied.
- **SC 2.1.1 Keyboard, Level A**, for the canvas. Direct manipulation (F3.6)
  has no keyboard path. The parallel list view makes the canvas's content
  readable; it does not make its manipulation operable, so it is a mitigation
  and not conformance.
- **SC 4.1.3 Status Messages, Level AA** was unmet everywhere until
  `spec/announcements.md`. It is now specified and not yet implemented.

Nothing here has been run through NVDA, JAWS or VoiceOver, so the semantics are
specified as well as a spec can and are unverified in practice.

Two things make this product harder than average and both are addressed below:
it is read at a distance on a projector, and it has to distinguish machine
output from human output. The new design does that without colour at all,
because the provisional colour is the accent itself.

## Contrast: measured, not estimated

Every pair below was computed with the WCAG 2.1 relative-luminance formula by
`contrast-check.py`, which reads `../tokens.css` directly, including its
`[data-scheme]` blocks, so a scheme that is declared is a scheme that is
measured. Re-run it after any token change; do not hand-edit this table.

The first group is the pairs no scheme moves: the neutrals, the two surfaces
and the three documentation diagram colours. The second is the one scheme,
measured on twenty-five pairs, including the accent and the "Proposed" word on
`--color-surface-sunken`, because a provisional note can sit inside a group
panel.

```
$ python3 spec/contrast-check.py              # the table, readable
$ python3 spec/contrast-check.py --markdown   # the table below, generated
```

### Pairs no scheme moves

| Pair | Foreground | Background | Ratio | Needs | Result |
|---|---|---|---|---|---|
| body text on the canvas | ink `#17181b` | canvas `#f8f9fc` | 16.86:1 | 4.5 | PASS |
| supporting text | ink-secondary `#4d4e51` | canvas `#f8f9fc` | 7.90:1 | 4.5 | PASS |
| meta, hints, empty states (lightest legal grey) | ink-muted `#5f6063` | canvas `#f8f9fc` | 5.97:1 | 4.5 | PASS |
| text in a quoted excerpt | ink `#17181b` | surface-sunken `#ebeef2` | 15.25:1 | 4.5 | PASS |
| caption in a quoted excerpt | ink-muted `#5f6063` | surface-sunken `#ebeef2` | 5.40:1 | 4.5 | PASS |
| white label on an ink button | ink-inverse `#ffffff` | ink `#17181b` | 17.75:1 | 4.5 | PASS |
| text in a menu, dialog or the session bar | ink `#17181b` | surface-float `#ffffff` | 17.75:1 | 4.5 | PASS |
| meta in a menu, dialog or the session bar | ink-muted `#5f6063` | surface-float `#ffffff` | 6.29:1 | 4.5 | PASS |
| a field's edge in a dialog or the session bar (1.4.11) | hairline-strong `#85878c` | surface-float `#ffffff` | 3.59:1 | 3.0 | PASS |
| a field's or group's edge on a sunken panel (1.4.11) | hairline-strong `#85878c` | surface-sunken `#ebeef2` | 3.09:1 | 3.0 | PASS |
| diagram: a person acts here (documentation only) | diagram-human `#8a3a6e` | canvas `#f8f9fc` | 6.85:1 | 4.5 | PASS |
| diagram: a model runs here (documentation only) | diagram-machine `#0f6b66` | canvas `#f8f9fc` | 6.02:1 | 4.5 | PASS |
| diagram: a hard limit (documentation only) | diagram-guardrail `#2e3a63` | canvas `#f8f9fc` | 10.49:1 | 4.5 | PASS |
| second chart series, chart baseline (1.4.11) | hairline-strong `#85878c` | canvas `#f8f9fc` | 3.41:1 | 3.0 | PASS |
| form field border, canvas item stroke (1.4.11) | hairline-strong `#85878c` | canvas `#f8f9fc` | 3.41:1 | 3.0 | PASS |
| ink: the capturing disc and the chosen tab line (1.4.11) | ink `#17181b` | canvas `#f8f9fc` | 16.86:1 | 3.0 | PASS |
| ink ladder: non-text boundary at 50% (1.4.11) | ink-edge `#88888c` | canvas `#f8f9fc` | 3.35:1 | 3.0 | PASS |

**17 pairs checked, 0 failing.**

### Scheme: delft (the default)

| Pair | Foreground | Background | Ratio | Needs | Result |
|---|---|---|---|---|---|
| text in a selected row | ink `#17181b` | accent-wash `#e3eefe` | 15.16:1 | 4.5 | PASS |
| meta in a selected row | ink-muted `#5f6063` | accent-wash `#e3eefe` | 5.37:1 | 4.5 | PASS |
| link, quiet button label, active tab | accent `#114fa2` | canvas `#f8f9fc` | 7.49:1 | 4.5 | PASS |
| accent label inside its own tint | accent `#114fa2` | accent-wash `#e3eefe` | 6.73:1 | 4.5 | PASS |
| white label on the primary button | ink-inverse `#ffffff` | accent `#114fa2` | 7.88:1 | 4.5 | PASS |
| white label on the pressed primary button | ink-inverse `#ffffff` | accent-pressed `#063d85` | 10.43:1 | 4.5 | PASS |
| capturing glyph and its word | status-capturing `#17181b` | canvas `#f8f9fc` | 16.86:1 | 3.0 | PASS |
| proposed glyph, dashed line and word | status-provisional `#114fa2` | canvas `#f8f9fc` | 7.49:1 | 3.0 | PASS |
| accepted glyph and word | status-accepted `#1d7344` | canvas `#f8f9fc` | 5.56:1 | 3.0 | PASS |
| waiting glyph and word | status-waiting `#8a5300` | canvas `#f8f9fc` | 6.01:1 | 3.0 | PASS |
| failed glyph and word | status-failed `#a81f1a` | canvas `#f8f9fc` | 6.94:1 | 3.0 | PASS |
| off glyph and word | status-off `#595959` | canvas `#f8f9fc` | 6.65:1 | 3.0 | PASS |
| provisional word as text | status-provisional `#114fa2` | canvas `#f8f9fc` | 7.49:1 | 4.5 | PASS |
| accepted word as text | status-accepted `#1d7344` | canvas `#f8f9fc` | 5.56:1 | 4.5 | PASS |
| waiting word as text | status-waiting `#8a5300` | canvas `#f8f9fc` | 6.01:1 | 4.5 | PASS |
| failed word as text | status-failed `#a81f1a` | canvas `#f8f9fc` | 6.94:1 | 4.5 | PASS |
| off word as text | status-off `#595959` | canvas `#f8f9fc` | 6.65:1 | 4.5 | PASS |
| provisional chip label on its tint | status-provisional `#114fa2` | status-provisional-wash `#e3eefe` | 6.73:1 | 4.5 | PASS |
| accepted chip label on its tint | status-accepted `#1d7344` | status-accepted-wash `#e8f1ec` | 5.08:1 | 4.5 | PASS |
| waiting chip label on its tint | status-waiting `#8a5300` | status-waiting-wash `#f3eee6` | 5.48:1 | 4.5 | PASS |
| failed chip label on its tint | status-failed `#a81f1a` | status-failed-wash `#f6e9e8` | 6.17:1 | 4.5 | PASS |
| off chip label on its tint | status-off `#595959` | status-off-wash `#eeeeee` | 6.04:1 | 4.5 | PASS |
| focus ring against the canvas (1.4.11) | accent `#114fa2` | canvas `#f8f9fc` | 7.49:1 | 3.0 | PASS |
| focus ring and accent line on a group panel (1.4.11) | accent `#114fa2` | surface-sunken `#ebeef2` | 6.77:1 | 3.0 | PASS |
| Proposed word inside a group panel | status-provisional `#114fa2` | surface-sunken `#ebeef2` | 6.77:1 | 4.5 | PASS |

**25 pairs checked, 0 failing.**

**42 pairs checked across 1 schemes, 0 failing.**

Note on `--color-hairline` (`#e1e5eb`, 1.20:1 on the ground): it is
deliberately excluded from the table. It separates regions and carries no information, so
1.4.11 does not apply to it. Any line that *does* carry information uses
`--color-hairline-strong` or a status colour instead. If you find yourself
wanting a `--color-hairline` line to mean something, it needs to be a stronger
line, not a darker hairline token.

## Never colour alone

This is the rule this product would most easily break, because its central
distinction is drawn partly in colour.

- **Provisional versus accepted is carried by form, never by colour**: a
  dashed line with no fill against a tonal fill with no line, plus the word
  "Proposed" and its dashed-ring glyph. The provisional colour is the accent,
  so colour does not separate them at all, by design. A reviewer with
  deuteranopia, or a projector washing out the blue, still sees a dashed
  outline labelled "Proposed" beside a filled note.
- **A person's unreviewed note is a solid line and no fill**, with the words
  "Not yet reviewed". Three forms for three provenances, all readable in
  greyscale.
- **Status is always a shaped glyph and a word.** Six distinct shapes at 16px:
  a filled disc, a dashed ring, a ring with a tick, a half-filled ring, a ring
  with a bar, a pair of bars. There is no glyph-only status and no row that is
  coloured to mean something.
- **Confidence is a number**, not a colour ramp.
- **The capturing indicator is a filled disc, the word "Recording", and a
  running timer.** Three signals. In a consent context, one is not enough.

## Focus and keyboard

- The focus ring is applied globally in `grid.css` and is never removed.
- Everything interactive is a native element or a real ARIA widget. A `div`
  with an `onClick` silently loses focus handling, Escape, and screen-reader
  semantics.
- Escape closes every overlay and returns focus to the trigger.
- Tab order follows visual order. If it does not, fix the DOM, not the
  `tabindex`.
- The review queue's shortcuts (`A`, `R`, `E`) are shown in the toolbar, not
  hidden.
- The confirmation dialog is the only modal and the only place focus is
  trapped. The side panel is non-modal: it does not trap focus and the canvas
  behind it stays operable.

## Structure and semantics

- One `h1` per page. Heading levels descend without skipping.
- Every form field has a real `<label>`. A placeholder is not a label.
- There is no uppercase anywhere. Labels are sentence case in the source and on
  screen, so no screen reader spells a label out letter by letter.
- The transcript is a list, and each line's timestamp is a link with an
  accessible name that includes the time and the speaker, not just "14:22".
- Landmarks: `header` for the session bar, `main` for the screen, `aside` for
  the rail, `nav` for the tabs.
- The canvas is the hard case. A free-positioned board is not navigable by
  screen reader as a spatial thing. **The list view of the canvas is not a
  fallback, it is a required parallel view**: every item, in creation order,
  with its kind, state and provenance, as a `.jv-rows` list. It is reachable
  from the segmented control on the canvas screen, not hidden behind an
  accessibility setting.

## Motion

- Nothing loops: there is no spinner, shimmer or pulse anywhere, including
  the capturing indicator, so there is nothing that could flash and nothing
  for reduced motion to stop on a loop.
- `prefers-reduced-motion: reduce` collapses every transition, including the
  accept transition, to an instant change. The end state is identical.
- Every transition is under 300ms and uses transform and opacity only.

## Text and zoom

- Reading text is 14px at a desk and 21px in room mode, where `data-room`
  scales every size by 1.5 and makes every target 44px. The room is read from
  five metres, and `space-and-hierarchy.md` § 3 has the arithmetic.
- Targets are 32px at a desk and 44px in room mode and on a coarse pointer.
- Nothing is set in `px` that prevents browser zoom; the page reflows to 400px
  wide without a horizontal scrollbar on the body.
- Line length is capped at `--layout-reading-max` (68ch) for anything that is
  read rather than scanned.

## Known gaps, stated honestly

- **The canvas itself is not keyboard-navigable in this spec.** Arrow-key
  traversal of a spatial board is a real design problem and this system does
  not solve it; it provides the parallel list view instead. That is a
  mitigation, not a solution, and it should be written up as a limitation
  rather than quietly relied upon.
- **Contrast was verified by computation, not on a projector.** Projectors
  crush contrast badly. The numbers here are the floor, not the room test. A
  real check in the room the team will present in is still owed, and it
  matters more now: `--color-surface-sunken` is a 1.11:1 step from the ground,
  which is exactly the kind of difference a projector erases.
- **Two pairs are not in the generated table.** `--color-hairline-strong` on
  `--color-surface-float` (a field inside a dialog) and on
  `--color-surface-sunken` (a field or an unreviewed note inside a group
  panel) are not declared in `contrast-check.py`. Computed by hand with the
  same formula they are 3.59:1 and 3.09:1, both above 3:1, the second only
  just. They are not claimed as verified until the script measures them.
- **Screen-reader behaviour was not tested.** No component here has been run
  through NVDA, JAWS or VoiceOver. The semantics are specified correctly as far
  as the spec goes; whether they work is unverified.

## Expandable sticky notes, planned (F3.8)

Use a native disclosure button with aria-expanded and aria-controls. Enter and
Space toggle it; preserve focus and remove collapsed detail from the tab order
and accessibility tree. Expose the same detail and named relationships in the
parallel list. Status and source-change warnings remain visible when collapsed.
Touch targets are at least 44px and never require hover. Reduced motion removes
expansion movement. These are requirements to test, not verified accessibility
claims for an implemented feature. See [the full contract](expandable-notes.md).

### Topic-colour acceptance, future work

The planned topic fills conflict with the one-hue rule and are not part of the
new design; a photographed note's paper colour is a small swatch, never a
fill. If any topic or paper swatch ships, group labels and a labelled key must
carry the same information without colour, and the swatch's edge against the
note and the ground must be added to the contrast checker and measured at 3:1
for a necessary non-text indicator. Existing generated tables certify only the
existing surfaces.
