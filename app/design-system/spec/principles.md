# Principles, and what wins when rules collide

## What this system is for

Jarvaids is a website that sits inside a live design meeting. It listens, it
reads photographs of the wall, and it builds a shared visual canvas while the
meeting is still running. The people using it are not looking at the screen
most of the time. They are talking to each other. The interface gets glanced
at, from across a room, on a projector, by someone mid-sentence.

That one fact drives everything below. This is not dense operations software
that a person lives inside all day. It is a surface that has to be legible in a
two-second glance and has to make one distinction unmissable: **what the team
made, and what the model guessed.**

## The principles

1. **One hue per screen, in tonal steps.** A single blue accent, a slightly
   cool neutral ground, a sunken tone for groups and settled items, and white
   for what floats. The canvas is the place the work is, so the interface
   spends almost no colour: every hue the interface paints competes with the
   meeting's own output.

2. **Separate by space first, then by a tonal fill, then by a line.** Never a
   fill and a line on the same element. Space groups before a word is read;
   a tonal step groups from across a room where a 1px line disappears; a line
   is kept for edges that carry meaning, such as a field you type into.

3. **Colour is light, not line.** The accent fills what is in focus or can be
   acted on: the primary button, the chosen relation, the focus ring. It means
   "you can act here". It is not a mood, not a brand wash, never a container
   outline and never a status other than provisional.

4. **One face, six roles.** Archivo carries everything. Hierarchy comes from
   size, weight (400, 500, 600) and ink, never from a second face and never
   from uppercase. See `typography.md`.

5. **Status is a shape and a word, always both.** Six meanings, each drawn as
   a shaped 16px glyph beside its word, so it reads in greyscale, on a
   washed-out projector and to a colour-blind reviewer. See `tokens.md`.

6. **Model output never looks like team output.** Anything the model made has
   no fill, a 1px dashed accent line and the word "Proposed", until a human
   accepts it (F3.5); accepting gives it the settled tonal fill. A person's
   own typed note has a solid line and no fill until the room reviews it. This
   is the most important visual rule in the product and the cheapest trust
   mechanism it has.

7. **Agreement before capture.** Nothing is recorded until every person present
   has agreed (F6.1), and the recording indicator can never be hidden.

8. **Never a silent failure.** If the model is behind or something broke, the
   interface says so, in a word, where the thing would have appeared, and says
   what still works (F6.4). Degradation is a designed state, not an absence.

9. **Nothing a person placed is moved by a machine** (F3.4). New output
   appears; it never slides the team's arrangement aside.

10. **Corrections are kept as evidence** (F6.5). An edit keeps the original
    beside it, and the interface says so once.

11. **Every claim points back.** Anything the model asserts carries the moment
    it came from, as a timestamp you can click (F6.3). "Trust me" is replaced
    by "check me".

12. **Restraint, and stillness.** No illustration, no decorative motion, no
    gradients, no photography as atmosphere, and nothing that loops: no
    spinner, shimmer or pulse. Photographs appear only as data: the picture of
    the wall, next to the notes read from it (F1.5, F1.6).

13. **Tokens are the whole vocabulary.** No colour, size, radius or line width
    exists outside `tokens.css`. A new need is a token proposal, not a local
    literal.

## Priority order when sources disagree

A lower layer never overrules a higher one.

1. `tokens.css`: the values are not negotiable.
2. `forbidden.md`: the hard bans.
3. `accessibility.md`: the contrast and non-colour-alone rules.
4. `exemplars/`: copy the structure of the reference screens.
5. The rest of `spec/`: rules for what the exemplars do not show.
6. Host-repo conventions: code style only, never a design decision.
7. Still unclear: build it from tokens, mark it
   `/* PROPOSAL: <name>: not yet in the design system */`, and raise it. Never
   invent silently, because a silent invention is indistinguishable from a bug
   six weeks later.

## The trade-offs this system knowingly makes

Stating these so nobody has to rediscover them.

- **A tonal canvas groups better than hairlines and costs a little calm.**
  Group panels and accepted notes in `--color-surface-sunken` give the eye
  something to grab on a dense screen, which hairline-only separation did not.
  The cost is that the page now has three tones where it had one, so the rule
  that a fill never also carries a line is what stops it becoming a page of
  boxes.

- **Dashed lines for provisional items cost visual calm.** A canvas with
  thirty provisional items looks noisy. That is correct: thirty unreviewed
  guesses *is* a noisy state, and the review queue exists to clear it.

- **Provisional shares the accent's hue.** One hue per screen means colour can
  no longer separate a model's proposal from a button. The dash, the glyph and
  the word carry it alone. They were always meant to be the primary signals;
  now they are the only ones.

- **One breakpoint means the tablet case is unhandled.** A 900px tablet gets
  the phone layout. That is a deliberate omission, not an oversight. This
  product's phone is a camera and a text box; its desktop is the room screen.
  A tablet is neither, and designing for it would double the work for a case
  the team has not evidenced. Touch treatment follows the pointer, not the
  width, so a tablet still gets 44px targets (`touch.md`).

- **Desk density and room legibility are two modes, not one compromise.** Body
  is 14px at a desk and 21px in room mode. A single size that suited the back
  of the room was wastefully large at a desk, and a desk size alone was too
  small on the wall. The cost is that someone has to switch room mode on.

## What changed in the new design

The previous principles were a white canvas separated only by hairlines, two
faces with two jobs, a warm accent with a violet for provenance, and status as
an 8px dot. Each was replaced for a stated reason: hairlines vanish at 5m and a
tonal step does not; a second face was asked to carry a distinction that the
dashed line carries better; two hues for "act here" and "the model made this"
broke one hue per screen for the screens where it matters most; and six dots
differed only in hue, where six shapes differ in greyscale. What did not change
is the list of things the product promises: model output never looks like team
output, agreement before capture, no silent failure, nothing a person placed is
moved by a machine, and corrections are kept as evidence.
