# Checklist

Run this before calling a screen finished. It is short on purpose; a checklist
nobody finishes is worse than none.

## The one that matters most

- [ ] **Model output is visibly distinguishable from team output at a glance,
      from across a room.** A provisional item has no fill, a 1px dashed accent
      line and the word "Proposed"; an accepted item has a tonal fill and no
      line; a person's unreviewed note has a solid line, no fill and "Not yet
      reviewed". Colour does not separate them, so form must. If you squint at
      the screen and cannot tell them apart, nothing else on this list counts.

## Typography

- [ ] One face, Archivo. Every piece of text is traceable to one of the six
      roles: display, heading, title, body, label, meta.
- [ ] Weights 400, 500 and 600 only. No 700.
- [ ] Nothing below 12px. No uppercase, no tracked capitals: labels are
      sentence case.
- [ ] Table rows are body text, except fixed-width machine fields (Rule T2).
- [ ] Figures are `tabular-nums`.
- [ ] One `h1`. Heading levels descend without skipping.

## Tokens and colour

- [ ] No hex, no `rgb()`, no Tailwind palette class, no arbitrary size, radius
      or line width.
- [ ] One hue on the screen: the accent, in its tonal steps. No second hue for a
      topic or a paper colour; a paper colour is a small swatch, never a fill.
- [ ] Greys come from the ink ladder. Nothing lighter than `--color-ink-muted`
      is text.
- [ ] Separation is space first, then `--color-surface-sunken`, then a line.
      **Never a fill and a line on the same element.**
- [ ] No shadow in the page. Only menus, popovers, the dialog and the scrolled
      session bar carry an `--elevation-*` token.
- [ ] Every status is a shaped 16px glyph and a word, from the closed set,
      meaning what `tokens.md` says it means.
- [ ] The accent appears only where something can be acted on or is in focus,
      and never outlines a container.

## States

- [ ] Empty: one sentence in caption muted, naming the next action.
- [ ] Loading: a still skeleton mirroring the real layout, first load only.
      Nothing pulses, shimmers or spins.
- [ ] Degraded: hairline banner saying what is behind **and what still works**.
      Never silent.
- [ ] Failed: shown where the thing would have been, never a silent gap.
- [ ] Disabled: reason stated beside the control.

## Interaction

- [ ] Focus ring visible on everything interactive.
- [ ] Escape closes overlays; Enter submits; tab order matches visual order.
- [ ] Every hover-revealed action is permanently visible at
      `[data-pointer="coarse"]`, at any width. Test by setting the attribute
      on `<html>`, not by narrowing the window.
- [ ] Targets are 32px at a desk and 44px with `data-room` on the root and on a
      coarse pointer. An icon with no word beside it uses `.jv-hit-grow`.
- [ ] Room mode checked: with `data-room`, type is 1.5 times larger and nothing
      overflows at 1440px.
- [ ] Text-entry controls are 16px at a coarse pointer.
- [ ] Anything stuck to a screen edge uses `.jv-stuck-top` or
      `.jv-stuck-bottom`. Nothing writes `env(safe-area-inset-*)` locally.
- [ ] No `100vh` and no `100dvh`. Full-height uses `.jv-viewport`.
- [ ] The only modal is the confirmation dialog, for End session or Delete
      session. No toast; Undo is in place on the row and in the session bar
      (F3.7).
- [ ] Motion is under 300ms, transform and opacity only, and nothing loops.
      `prefers-reduced-motion` respected.

## Accessibility

- [ ] Every new colour pair added to `contrast-check.py`, the script re-run,
      and the table in `accessibility.md` regenerated with `--markdown`.
- [ ] Nothing is carried by colour alone. Print the screen in greyscale: every
      status and every provenance state must still be nameable.
- [ ] Real `<label>` on every field.
- [ ] Landmarks present: `header`, `main`, `aside`, `nav`.
- [ ] If the screen shows the canvas, the parallel list view is reachable from
      it.

## Layout and copy

- [ ] 8px rhythm; 4px only inside a cell.
- [ ] `minmax(0, …)` and `.jv-truncate` on every flexible text column.
- [ ] No horizontal scrollbar on the body at 400px wide.
- [ ] Copy: English, sentence case, verb-first buttons, no em dashes, no
      exclamation marks, British spelling.
- [ ] Every claim the model makes carries its citation (F6.3).

## Before merging

- [ ] `spec/audit.sh` exits 0. It runs the contrast check and every
      mechanical grep, and resolves its own paths, so it works from any
      directory.
- [ ] The grep list in `AUDIT.md` returns nothing.
- [ ] You have looked at the screen at 400px wide and at 1440px wide.

## Future expandable-note acceptance (F3.8)

These checks apply when the feature is implemented; none is claimed as passed
by the documentation change.

- [ ] Main points scan clearly; expanded detail preserves qualifications and sources.
- [ ] Dense and long notes, multiple expansions and fixed axes retain readable relationships.
- [ ] Team positions survive toggles, new arrivals, reconnect and concurrent saved edits.
- [ ] Review exposes full proposed content before Accept; expansion changes no review state.
- [ ] Keyboard, touch, reduced motion, no-detail and unavailable-source cases work.
- [ ] Overview and complete exports clearly state their content and retain provenance.

Scenario detail and comparison protocol: [expandable notes](expandable-notes.md).

- [ ] Topic is carried by group labels and group panels; no note takes a
      topic fill, which would break one hue per screen.
- [ ] A photographed note's paper colour is a small swatch on the note, kept
      as source evidence, never its fill.
- [ ] Any swatch that ships has its edge measured at 3:1 by the contrast check.
