# Design reference: what Rondesignlab does, and what our system forbids

**Purpose.** The team found the Week 4 deck and the client flat, and asked for
an analysis of Rondesignlab's interface work as a reference, to hand to the
agent revising the design system. This is that analysis: what the studio does,
which of it our system currently forbids and why, and what to change.

**How this was made, honestly.** The session's network proxy blocks
rondesignlab.com, Dribbble, Behance, Medium and the gallery sites, so no page
was read directly. The list below comes from search-result descriptions of
three named projects (SolaFlux, ClauseOS, the Sugar CRM customer journey
dashboard) plus the coordinator's knowledge of the studio's widely published
dashboard work. Two reference screenshots from the team arrived afterwards and are read
in section 5; they change the feedback in section 3, and the file says where.

## 1. What Rondesignlab does, as a list

Grouped by what it is for, because the point is to take the craft and not the
costume.

### Depth and surfaces

1. **Three surface levels, not one.** Canvas, panel, card, each a step lighter
   or darker than the one below. Content sits *on* something.
2. **Cards with real radius.** Corners around 12 to 24 px, never 2 or 4.
3. **Soft ambient shadow.** Large blur, low opacity, offset downward, so a
   card lifts without a hard edge. Often paired with a 1 px inner border at
   low alpha so it also reads on dark backgrounds.
4. **Frosted panels over colour.** Navigation and overlays use blur and
   translucency where there is something colourful behind them; data-dense
   surfaces stay opaque.
5. **Dark and light as equals.** The dark variant is a deep tinted neutral,
   never pure black, with the same layering.

### Colour

6. **One saturated brand hue,** used for the primary action, the hero tile
   and chart accents, with neutrals tinted slightly toward it.
7. **Gradients as accent, not wallpaper.** A hero card fill, a glow or colour
   orb behind a key number, an area chart fading to transparent. One or two
   per screen.
8. **Tinted status chips.** Coloured text on a 10 to 15 percent tint of the
   same colour, pill shaped. Green, amber, red mean what they always mean.
9. **Icon tiles.** A line icon inside a small rounded square with a tinted
   background, one tint per icon, used as row leaders and in navigation.

### Type and numbers

10. **Big numerals.** A KPI at 32 to 48 px in a tight display face, label
    small above it, a delta chip beside it. The number is the design.
11. **Geometric or grotesk sans throughout,** display sizes tightly tracked,
    body loosely, and only three visible levels: display, body, muted meta.
12. **Generous white space.** Padding inside cards of 20 to 32 px; gaps
    between them of 16 to 24 px. Density comes from hierarchy, not from
    cramming.

### Layout

13. **Bento grids.** Mixed tile sizes on a strict column grid, with one hero
    tile spanning two columns and a taller chart tile beside it.
14. **Sidebar navigation** with icon plus label, the active item a filled soft
    rectangle, the user's avatar pinned at the bottom.
15. **Small floating cards for tooltips and menus,** with the same radius and
    shadow as the cards themselves.

### Data and objects

16. **Charts with weight.** Thick strokes with rounded caps, gradient area
    fills, dot markers on the current value, donut rings with the numeral in
    the centre, sparklines inside KPI cards.
17. **3D and illustrated anchor objects inside the product,** not only in
    the marketing: the SolaFlux house with soft lighting and warm gradients,
    the ClauseOS spatial document stack that groups contracts by category.
18. **People everywhere.** Avatar stacks on rows, faces on assignees, so data
    looks owned.

### Presentation

19. **Motion in the shots:** hover lift, charts drawing in, panels sliding.
20. **The case study is itself designed:** a coloured backdrop, angled device
    mockups, oversized captions. The polish of the presentation is part of
    the work.

## 2. What our system forbids, and why it did

Taken from `app/design-system/spec/forbidden.md`. The numbers are its rules.

| Rondesignlab trait | Our rule | Why the rule exists | Verdict |
|---|---|---|---|
| Cards, shadows, three surface levels (1, 3, 15) | 9: no cards, no `box-shadow`; 10: no grey panels to group | One flat plane so the dashed provisional stroke is the only depth cue on the board | **Relax off the board.** Elevation is a real hierarchy tool. Keep the board itself flat so the provisional stroke stays the strongest signal there |
| Radius 12 to 24 px (2) | 3: the scale is 2 / 4 / full | Consistency, and a sharp edge reads as precise | **Extend** the scale by two steps, for cards and floating panels only |
| Gradients (7) | 11: no gradients, none | An accent that is a mood stops marking the place you can act | **Allow one**, tokenised, for a hero surface or a chart fill. Never on a control |
| Frosted panels (4) | Not named, but 9 and 11 together exclude it | Same as above | **Decline.** It costs contrast on a projector, which is where this product is seen |
| Dark variant (5) | 28: dark mode does not exist | One scheme to keep the contrast table honest; four schemes are already contrast-checked | **Reconsider** once the elevation and radius work is done. A meeting-room projector is bright; dark needs testing there, not assuming |
| Tinted status chips (8) | 13: status colours reserved | Status colours already have this shape in the system; the reservation is about not spending them elsewhere | **Compatible.** Already allowed, under-used |
| Icon tiles with tints (9) | 29: no categorical colour | A colour that means "kind of thing" competes with the provisional stroke and with status | **Half.** The tile shape yes; a tint per icon no, one neutral tint for all |
| Big numerals, three type levels, white space (10, 11, 12) | Nothing forbids them; `typography.md` has the display level | | **Compatible.** This is the gap in execution, not in rules: the deck and the client use the body size where the display size was available |
| Bento grid, sidebar, floating menus (13, 14, 15) | Only 24, one scroller per screen | | **Compatible**, given the elevation change above |
| Charts with weight (16) | `dataviz.md` governs | Thin strokes were chosen for print and projector legibility | **Partly.** Thicker strokes and a current-value marker yes; gradient fills only under the single gradient token |
| 3D objects, illustration (17) | 22: no illustration or photography as decoration | Decoration on a tool that shows other people's sticky notes competes with the content | **Decline in the product.** Allow in the deck, which is not the product |
| Avatars (18) | Not forbidden; the product has no faces by design | Participants are names, and the record is anonymised on export (F6.6) | **Decline.** It is a privacy decision, not a taste one |
| Motion (19) | `interaction.md` allows state change in place; 19 and 21 forbid toasts and spinners | | **Compatible** for hover and chart draw-in, with reduced-motion respected |
| The presentation is designed (20) | The deck inherits product rules through `_base.css` | | **Change.** The deck should have its own layer: bigger type, a dark or tinted stage, room for one anchor visual per slide |

## 3. The feedback to give the design-system agent (superseded by section 7)

Written from the first two screenshots and kept for the record. Section 7
is the version to hand over.

Ordered so each step is safe on its own.

1. **Add depth by tone, not by shadow.** Three stage tokens per scheme:
   `--color-stage` (the deep tone of one hue), `--color-stage-wash` (its
   mid tone) and `--color-stage-stroke` (a light translucent stroke, white
   at about 40 percent). A container is a step lighter or darker than what
   it sits on, and its edge is the translucent stroke. Rule 9 can stay as
   written, because no `box-shadow` is needed: both reference screenshots
   in section 5 get their depth exactly this way. Reason: hierarchy needs a
   second axis besides type, and tone gives it without the projector
   contrast cost of shadows and blur. Keep the board flat either way, so the
   provisional stroke stays the strongest signal there.
2. **Extend the radius scale** with `--radius-md: 12px` and
   `--radius-lg: 16px`, for sheets and panels, and use the existing
   `--radius-full` for compact status containers. Not on board items.
   Reason: a tonal container with a 4 px corner reads as a form field; the
   capsule and the 16 px sheet in section 5 read as surfaces.
3. **Fill against outline as the one state language.** Outline is the
   default for every control and icon button; fill is selected, active or
   done. The design system already uses exactly this for provisional against
   accepted (rules 16 to 18), so this extends a rule it has rather than
   adding one. Reason: both screenshots carry state without a second colour,
   and it is the same idea the product already leans on.
4. **One gradient token**, `--gradient-stage`, a soft two-stop gradient
   between two tones of the stage hue, permitted on the stage behind the
   interface and nowhere on it. Reason: rule 11's worry was the accent
   becoming a mood; a backdrop gradient with a flat interface on top keeps
   the accent meaning "you can act here", which is how the first screenshot
   uses it.
5. **Raise the display type in the exemplars.** A `t-numeral` at 48 to
   64 px, bold, tabular, and a `t-backdrop` size for one word set behind an
   object, with the exemplars rebuilt so the largest thing on each screen is
   a number or a word, not a box. Labels beside a numeral drop to a lighter
   tone of the same colour, so the number wins. Reason: this is most of the
   flatness people see, and it needs no rule change.
6. **A deck layer.** A `deck.css` that inherits tokens and adds the stage:
   larger sizes, a tinted or dark stage background, the elevation scale, one
   anchor visual per slide allowed. Reason: the deck is not the product, and
   the product's discipline about decoration should not make the proposal
   look unfinished.
7. **Keep three things as they are and say why on the slide about the
   system:** the dashed provisional stroke as the only signal for model
   output (rules 16 to 18), no faces (privacy), no frosted glass (projector
   contrast). Reason: these are product decisions, and a reviewer who sees
   them stated will read the flatness elsewhere as intent.

## 4. Two things to say to the team

- **Rondesignlab designs dashboards for SaaS shots; Jarvaids is a tool used
  in a meeting room on a projector next to a wall of paper.** Take the craft
  (hierarchy, numerals, layering, spacing, chips) and leave the costume
  (orbs, 3D renders, glass). A shot that wins on Dribbble is composed for a
  phone screen at arm's length, which is not where this is judged.
- **The deck can move faster than the product.** Items 5 and 6 above need no
  rule change and would lift the presentation tomorrow. Items 1 to 4 are
  rule changes and deserve the contrast check and a decision-log row each.

Sources the search returned, for whoever can open them: the studio site
(rondesignlab.com, cases for SolaFlux, ClauseOS, Salesforce, PipeDrive and
Netsuite CRM), dribbble.com/RonDesignLab, behance.net/rondesignlab, and the
Muzli 2026 dashboard roundup that describes the SolaFlux dashboard.

## 5. The two reference screenshots, read closely

Both arrived after the list above was written. They are more useful than the
portfolio survey, because they show what the team actually responds to.

### A. A live-activity score pill, compact and expanded

An iOS Dynamic Island design for a baseball score, shown twice: the compact
capsule and the expanded state, on a coral stage.

- **One hue, three tones.** The stage is a soft two-stop gradient from
  orange to pink, the device outline is a light translucent stroke of the
  same hue, and the pill is a deep wine of it. There is no second colour.
  Contrast is lightness, not hue.
- **Depth without shadow.** The pill is flat on the stage. It reads as a
  layer purely because it is darker, and the device edge reads as glass
  purely because it is a wide, translucent stroke.
- **The number is the design.** "KC 7" is about two and a half times the
  body size, bold, white. The team code sits at the same size but in a pink
  tint, so the score wins by tone, not by size. Two small levels below it
  (name, statistic) and one centred line of state.
- **Fill against outline as state.** The three diamonds are the bases: two
  filled, one outlined. A binary state carried by fill, with no colour and
  no icon change. This is our provisional rule, used on data.
- **A dashed reserved region.** The camera cutout is drawn as a dashed
  rounded rectangle: dashed meaning "not yours to draw on". Dashed as a
  reservation is again the product's own convention.
- **Two states side by side.** The design shows behaviour, not one screen.
  Our deck shows single frames; the demo slide could show compact and
  expanded states of the session bar the same way.
- **What it is for us.** A meeting session *is* a live activity: state word,
  unresolved count, who is in the room, time. The session bar could be this
  capsule, compact by default and expanded on tap, and it would carry the
  product's own rules (dashed for provisional, fill for accepted) without
  a single new colour.

### B. A colour page on a car maker's media site

A monochrome green stage with the car on a reflective floor, the colour
name set enormous behind it, and a bottom sheet of controls.

- **The whole screen is one hue.** Near-black green at the edges, a
  spotlight of the colour behind the object, the reflection below it, the
  sheet a translucent tint of the same green. The only full-colour element
  is the crest, which is the brand.
- **Type as backdrop.** The word is set at roughly an eighth of the viewport
  height in the colour itself, and the object occludes it. Two layers only,
  and the text is behind. Depth from occlusion, not from shadow.
- **Outline is default, fill is selected.** Four icon buttons, 1.5 px white
  outline, 8 px radius; the selected one is inverted, white filled with a
  dark icon. The primary call to action is outlined with text, not filled.
  The full-width secondary action is outlined too. One consistent language.
- **Restraint in type.** One grotesk, one weight, no uppercase labels, two
  sizes inside the sheet, body around 17 px on a phone. Density comes from
  size and space, not from more levels.
- **Thin monochrome icons**, 1.5 px line, no tints, no tiles.
- **The object gets half the viewport.** Everything else is quiet around
  it.
- **What it is for us.** The canvas is our object. A tinted dark stage with
  paper-coloured notes on it would make the notes the brightest thing on
  screen, which is where the eye should be in a meeting. The sheet of
  outlined controls is the review row: correct, accept, reject, with accept
  the one that fills.

### What the two share, which is the actual brief for the system

1. One hue in several tones per scheme, instead of neutral grey plus an
   accent. Depth is tonal.
2. Fill against outline as the single state language, for controls and for
   data.
3. The largest thing on the screen is a number, a word or the object, never
   a container.
4. A soft backdrop gradient with a flat interface on top.
5. Radius is either a capsule or about 16 px; there is nothing at 4 px.
6. Two states shown together when behaviour is the point.

None of the six needs a shadow, a blur, an illustration or a second accent.
Items 1, 4 and 5 are token changes; 2 and 3 are usage rules the system half
has already; 6 is a deck convention.

## 6. The Rondesignlab screenshots, batch by batch

Read from the team's Instagram captures, five per batch. Each entry says what
the shot is, what it does, and whether it adds anything to the list in
section 5 or repeats it.

### Batch 1

**1. Air purifier app, filter picker.** A phone held against the sky. Stage is
a two-stop gradient from sky blue to warm cream. Two large squircle panels
(radius near 40 px) hold 3D renders of the filters; a third holds a stepper
with circular minus and plus buttons and the count "2" set in a dot-matrix
display face. Price is the second largest thing on screen. Type is a light
geometric sans, small labels in a lighter tint.
*New:* the dot-matrix numeral as a signature for a live value, 3D product
renders inside panels as the content rather than decoration, circular
buttons for a stepper.

**2. Air purifier, four rooms.** Four frosted squircle tiles over a heavily
blurred photograph of a person. Each tile is a thin ring gauge with tick
marks, a dot-matrix score and a one-word label (Bad, Good, Medium). One lime
accent curve on one tile, nowhere else.
*New:* frosted glass with a strong blur over a photograph is used here at
full strength, not sparingly, which contradicts the portfolio survey's
"selective transparency". Ring gauges with tick marks and one accent curve.
The word label under the number carries the meaning; the colour does not.

**3. Air purifier, total score.** One large glass card over the same blurred
photograph. Dot-matrix "56", the label "Medium" beneath, a rising lime curve
to a filled circular marker, then three tabular figures (78h, 56h, 78h) with
small labels. The chart's area is a translucent blue tint that fades.
*Repeats:* number first, glass over photo, one accent curve. *New:* the chart
lives inside the same card as the number, and the tabular row under it is
the only other text.

**4. Quarn, landing page on a tablet.** Near-black page with a deep green
vignette. The wordmark is set enormous behind a laptop mockup and the mockup
occludes it (the same move as the Porsche page). The product is a node graph:
dark cards as nodes, glowing green connectors. Three statistics at display
size in a light weight (72%, 1.2M, 99.9%) with tiny captions.
*Repeats:* one hue in tones, type as backdrop, numbers as the design.
*New:* light weight rather than bold for display numerals; glowing
connectors as the only saturated element on a dark canvas.

**5. Quarn, case-study insight.** A green gradient panel holding a glass quote
card with an avatar, beside a headline "57% Less Time on Model Setup" in a
light weight with a small "Insight 002" pill above it. Below, a before and
after bar chart where the before bar is hatched grey and the after bar is
dotted green, with a large "-57%" beside it.
*New:* **texture as a category language.** Hatched against dotted
distinguishes the two bars before colour does, which is exactly the move our
rule 29 asks for. Also the case-study grammar itself: a numbered insight, a
metric headline, a quote with a face, one chart.

**What batch 1 adds to the six shared traits:**

7. A display face for live values (here dot-matrix), distinct from the text
   face, so a number reads as an instrument reading.
8. Texture (hatch, dots) as a way to tell two series or two states apart
   without spending a colour.
9. Light weight at display size. The big numbers are thin, not bold.
10. Content objects (a 3D render, a node graph) sit inside the panels as the
    subject; the panels are frames, not decoration.

**One correction to section 2.** Frosted glass over a photograph is a main
tool for this studio, not a selective one. The verdict there stands for the
product (projector contrast), and the deck can use it over its own stage
where nothing has to be read through it.

### Batch 2

**1. Eilo, "Interface Concept" card.** A flat, opaque, saturated yellow
square with sharp corners, sitting on a motion-blurred photograph. No glass,
no gradient, no shadow. The title is two-tone: "Interface" in black,
"Concept" in a muted olive, same size. A range chart of thin vertical
hairlines with red dot endpoints, one value labelled ("14 Hours"). Two
statistics in the bottom corners, a three-dot activity glyph between them,
a week scrubber with tick marks and arrows. The calendar icon sits in a
lighter yellow square: a tonal tile inside the card.
*New:* **a flat saturated card can be the richest thing on the screen** when
it is the only saturated thing and the stage is muted. It is, in effect, a
sticky note. Also the two-tone title and the dumbbell chart.

**2. Eilo, dashboard on a phone.** Off-white ground. Two large figures
(a tracking number and a payment total) in a medium weight with two-tone
labels ("Tracking" bold, "Number" muted). Chips: a white "Production" pill
and a pink "Design" pill. A black square "+" button. The yellow card below.
A tab bar of white icon tiles; the avatar sits in a yellow square.
*New:* a palette of four opaque colours (yellow, pink, black, off-white) at
full saturation, small radius (about 8 px), no translucency anywhere. Flat
works here because contrast is high and every surface is a distinct tone.

**3. Eilo, end card.** "Save this design" set enormous in white, bleeding off
the frame, the yellow card centred over the blurred figure, a teasing line
above. *Repeats:* type as backdrop, the presentation is designed.

**4. Quarn, a node over a portrait.** A dark glass node card ("AI Agent,
Tools Agent") with a thin light stroke, floating over a green-tinted blurred
portrait; glowing green splines run to labelled ports ("Chat model",
"Memory", "1 item"). Below, a second glass card with a slider on a 0 to 100
scale with tick marks and a tabular readout ("Posts ready: 32.4%").
*Repeats:* one hue in tones, glass over photo, glow as the only saturated
element. *New:* ports and connectors labelled in small text, so the graph
reads without a legend.

**5. Quarn, the design process as a node graph.** The case study's process
(Discovery, Architecture, Interface Design, Flow Mapping, Validation,
Design System) drawn in the product's own idiom: dark node cards with a
small icon and title, body copy with key phrases in bold, green flowing
splines between them.
*New:* **the case study is told in the product's own vocabulary.** The
process diagram uses the product's node cards, so the method and the thing
look like one piece of work. Also emphasis by weight inside a sentence.

**What batch 2 adds:**

11. Flat and saturated is a legitimate register, not a failure of depth: an
    opaque colour card with sharp corners on a muted stage. This is the
    closest thing in the set to a sticky note, and it is the one register
    our own system already permits.
12. Two-tone labels: a bold word and a muted word at the same size, so one
    label carries a heading and a subheading.
13. Dumbbell and range charts on hairlines with dot endpoints, one accent.
14. Emphasis by weight inside body copy.
15. The method drawn in the product's idiom, so process slides look like
    the product rather than like a template.

**What this means for Jarvaids, more precisely than before.** Our canvas is
flat because everything on it is the same tone: white ground, hairline
items, black ink. The Eilo card is flat too, and reads as rich, because it
is the one saturated object on a muted, blurred stage. So the fix for the
board is not depth; it is contrast of tone between the stage and the notes.
A muted tinted stage with saturated paper-coloured notes, sharp corners, a
two-tone label (note text bold, origin muted), and the dashed stroke for
provisional ones, would sit inside our current rules almost entirely. And
the deck's process and stack slides should use the product's own note and
card idiom, as Quarn's process page does.

### Batch 3

All five are Quarn case-study slides (7 to 11 of 15), so this batch is one
template seen five times, and the value is in what repeats.

**1. Insight 002, model setup (seen again).** Same slide as batch 1 item 5.
*Repeats.*

**2. Visual priority, +49%.** Top left, a green gradient panel with a glass
card carrying the metric and a checked line ("Instant Status"). Top right,
the same metric as a light-weight headline under a muted title ("Visual
Priority" in grey, "+49%" in white), then a bar chart: baseline bars in flat
dark grey, the current bar in green hatch, value labels above, dashed
gridlines, tiny axis type. Bottom, a crop of the node canvas: the active
node has a green gradient fill and a check mark; a deactivated node is dark
grey with a red bin icon and "(Deactivated)" in its label; ports and edges
carry small tags ("Model", "Memory", "1 item").
*New:* node state by fill (active is filled, inactive is dark), the metric
echoed twice (once inside the product card, once as the headline), and the
two-tone heading inverted: label muted above, value bright below.

**3. AI configuration, +56.4%.** Phone mockup beside a desktop panel of the
same screen, then the green panel and a scatter-step chart whose area is
diagonal hatch with green dots at each point, on dashed gridlines.
*New:* two form factors of one screen side by side. Hatch as the area fill
under a line, not only in bars.

**4. AI model configuration, +58.4%.** Same template: crop, phone, the metric
headline, a step chart with hatched area and labelled points (20%, 42%,
58%), and a dark panel with the green node card.
*Repeats.*

**5. Market shift, 68%.** Same template again: muted title, bright number,
step chart on a dot-grid background, the metric repeated inside the glass
card on the green panel, the node canvas below.
*New:* the canvas itself has a dot grid, which reads as a workspace texture
without a tint.

**What batch 3 adds:**

16. Texture fills are a system, not a flourish: flat dark for baseline,
    hatch for before or area, dots for current or after. Every chart in the
    case study obeys it.
17. State by fill on cards: the active node is filled with the hue, the
    inactive one is dark with a word saying so.
18. One slide template for the whole case study: four panels with fixed
    roles (product crop, metric headline, chart, product detail), so fifteen
    slides read as one document.
19. A dot grid as the workspace background: texture instead of tint.
20. Two form factors of the same screen shown together.

**For Jarvaids.** Three of these are direct. A dot grid on the board gives the
canvas a surface without breaking rule 10. Fill against outline already
carries provisional against accepted; the deactivated node shows how to add
a third state (stopped, rejected) with a dark fill and a word, never a
colour. And the deck's slides 6 to 8 would gain from one fixed template
with the same four roles, so the how slides read as one document rather
than three layouts.

### Batch 4

All five are Eilo (slides 2 to 6 of 9): the same card and dashboard as
batch 2, shown at different scales and crops. Mostly repeats; the new
material is about scale and about tone within one hue.

**1. The card at poster scale (6 of 9).** The yellow card fills the whole
frame. "Interface" in black italic, "Concept" in olive italic, the dumbbell
chart drawn on skewed hairlines so the lines lean, the two statistics
enormous in the corners.
*New:* italic as an emphasis register on a flat card, and one component
shown at poster scale as a slide of its own.

**2. Macro crop of the dashboard (5 of 9).** The two-tone label pairs
("Tracking" black, "Number" grey; "Payment", "Total") over heavy figures.
The back button sits in a translucent cream tile, the avatar in a yellow
tile, the chips beside a black square button.
*New:* controls on a saturated or off-white surface are translucent tiles
of the same hue, lighter or darker, never a second colour.

**3. The card over a blurred figure (4 of 9).** *Repeats* batch 2 item 1.

**4. Phone in hand (3 of 9).** The dashboard again, and the "white" screen is
not white: a faint yellow-to-pink gradient sits under the off-white, so the
whole screen belongs to the card's palette. Labels are italic here too.
*New:* even the neutral ground is tinted toward the palette.

**5. Extreme close-up with the tab bar (2 of 9).** The tab bar is a row of
tiles: the active one opaque white, the others translucent white over the
yellow. *Repeats* fill against outline, as fill against translucency.

**What batch 4 adds:**

21. One component at three scales across a case study: in context, at
    poster scale, and as a macro crop. The component has to be good enough
    to survive all three.
22. Italic as a register for emphasis on flat surfaces, where weight alone
    would be heavy.
23. Controls on a coloured surface are lighter or darker tiles of that
    surface, translucent, so a card never needs a second colour for its
    own buttons.
24. The neutral ground is tinted toward the palette. Nothing is pure white.

**For Jarvaids.** The note is our one component, and it should survive the
same three scales: on the canvas, as a review row, and full-screen on the
projector when one note is being discussed. The deck's demo slide could
show the note at poster scale the way Eilo shows its card. And the stage
token from section 3 applies to the light scheme as well: an off-white
tinted toward the paper colour, not pure white.

### Batch 5

Two Eilo (the same image twice) and three from a health-data app posted in
June ("make health data feel less clinical and more human").

**1 and 2. Eilo, the card as dark glass (1 of 9).** The identical card from
batches 2 and 4, but as a dark translucent panel over a red and pink blurred
figure: white type, white dumbbells, the same two-tone title, corner
statistics and week scrubber.
*New, and the most useful thing in the batch:* **one component, two
materials.** The structure is invariant (title, chart, statistics,
scrubber) and only the skin changes, opaque yellow on one slide and dark
glass on another. The component is designed before the material is.

**3. Health data, end card (10 of 10).** "Save this design" bleeding off the
frame, a glass card "Your results are pending" with "7 to 10 Days", a slider
with a filled dot and a dotted waiting glyph, and a white squircle holding
a 3D render of a blood vial. *Repeats:* glass over portrait, object in a
white tile, type as poster.

**4. Health data, light interface at an angle (9 of 10).** Pale grey ground,
white pill-shaped tiles ("Existing Records, 2 files", "Upload Health
Records"), a chip "Out of range" beside a dot-matrix "5", a calendar row with
green and red dots, and paper documents (invoices) rendered as paper inside
a tile. One tile has a soft pink gradient edge.
*New:* the light mode of the same language, and **the artefact shown as
itself**: a document is drawn as a sheet of paper, not as an icon.

**5. Health data, biomarkers card (8 of 10).** A large squircle filled with a
vertical gradient from amber to green, a dot-matrix "70" with the label "On
Track", and a sparkline drawn entirely in dots. Below, "Biomarkers" in a
light grotesk with a one-line subtitle, and muted grey tiles.
*New:* a chart drawn in the same dot idiom as the numeral, and a gradient
used as a status scale on one card, with the state also said in a word.

**What batch 5 adds:**

25. One component, two materials. Design the structure once; the opaque
    and the translucent skin are both valid renderings of it.
26. The light scheme is the same language on a pale grey ground with white
    tiles, not a separate design.
27. Charts can be drawn in the display face's own idiom (dots), so the
    number and its history read as one instrument.
28. Artefacts are shown as themselves: a document as paper, a sample as a
    vial. The content object is literal.
29. A gradient can carry a status scale on a single card when the word
    beside it says the state too. The colour is never alone.

**For Jarvaids, and one tension to hand the system agent.** Item 28 is
direct: the crop of the photograph a reading came from should be shown as
the photograph, inside the review row, which is what F6.3 asks for. Item 25
raises a question rather than an answer. A note has one structure and could
have two materials: opaque paper when accepted, translucent when provisional.
That would be a material, not a tint, so it does not break rule 18 as
written. But rule 17 says provisional is never greyed out, and translucent
can read as dimmed on a projector. The dashed stroke stays the signal; a
second material is a proposal to test with the contrast check, not to adopt.

### Batch 6

All five from the health-data app (slides 1 to 6 of 10), ending with the
whole dashboard on a monitor, which shows how the pieces from batch 5 sit
together.

**1. Biomarkers, macro (6 of 10).** A white tile with a heart icon in a
circle, "Heart Health" muted, "103 mg/dl" in dot-matrix with "LDL
Cholesterol" beneath, and a ruler of tick marks along the bottom with one
bold tick as the marker. The green gradient card above carries a dotted grid.
*New:* **a value against its range as a ruler**, ticks in hairline and the
current position as one heavier tick. No colour, no fill, and the reader
sees where the number sits.

**2. Health improving pill (5 of 10).** A floating capsule with a trend arrow,
"Health Improving" and "+3.2 last 30 days" muted beneath, over a timeline
drawn as a row of dots with a few coloured event dots. A small spectral
smear on the glass edge. Dot-matrix "80" with an "Optimal" chip above.
*New:* **time as a row of dots** with events as coloured dots and a summary
pill floating over it. The spectral highlight is a material flourish and
adds nothing for us.

**3. Upload records (3 of 10).** *Repeats* batch 5 item 4: paper documents in
a tile, chips, the June dot row.

**4. Biological age (2 of 10).** An orange-to-blue gradient card, dot-matrix
"25" with "2.5 years younger", a tick ruler with a bold marker along the
bottom, and the health pill above the dot timeline. *Repeats* the ruler and
the gradient status card.

**5. The whole dashboard on a monitor (1 of 10).** Pale grey ground, white
squircle tiles. A top row of numbers with a state chip each: "80 Optimal",
"21 In range", "5 Out of range". The dot timeline from April to June with
the pill floating on it. Two gradient hero tiles (green "Superpower Score
70, On Track", orange "Biological age 25"). The pending card with the vial.
A supplements row with 3D spheres in white tiles and a small yellow "Best
Seller" chip. Biomarker tiles with dot numerals and tiny sparklines.
*New:* **a saturation budget.** On a full page only two tiles carry colour,
and everything else is white, grey and black. The dots run through the
whole page (numerals, timeline, sparklines) as the one texture.

**What batch 6 adds:**

30. A value against its range is a ruler of hairline ticks with one heavy
    tick, never a coloured bar.
31. Time is a row of dots; events are dots with status colour; a summary
    pill floats over the row.
32. Every number carries a word for its state in a chip beside it.
33. A saturation budget per screen: two coloured surfaces, the rest neutral.
34. One texture runs through the whole product, here dots, so the page
    reads as one instrument.

**For Jarvaids.** Three direct uses. The session timeline can be a dot row
with events (a photograph taken, a note accepted, someone joined) as status
dots and a floating pill saying "3 unresolved", which is F2.4 and F6.3 made
visible. A reading's confidence can be a ruler with one heavy tick beside
the text, which shows where it sits without a colour and without a
percentage the room will argue with. And the canvas gets a saturation
budget: the notes are the coloured surfaces, and nothing else on the screen
competes with them.

## 7. The consolidated brief, after all thirty screenshots

This section supersedes section 3. Section 3 was written from two
screenshots; this one is written from thirty, and where they disagree this
one wins. The thirty-four traits recorded in sections 5 and 6 collapse into
eight rules, and the eight rules into twelve concrete changes. Each change
says which rule in `forbidden.md` it touches, so the system agent can see
at a glance what is a token, what is a usage rule and what is a rule change.

### The eight rules the studio actually follows

1. **Tone before hue.** One hue per screen in several tones; depth is a
   step lighter or darker, never a shadow. Even the neutral ground is
   tinted toward the palette. Nothing is pure white.
2. **A saturation budget.** Two coloured surfaces per screen at most. On a
   dark stage the colour is a glow on edges; on a light stage it is one or
   two tiles. Everything else is neutral.
3. **Fill against outline, and fill against translucency, as the whole
   state language.** Outline is default, fill is selected or active, dark
   fill with a word is inactive. Colour never carries state alone; a word
   sits beside it.
4. **Texture instead of colour for categories.** Hatch, dots and flat tell
   series and states apart. Dots run through numerals, timelines and
   sparklines so the product reads as one instrument.
5. **The number is the design.** A display face for live values, light
   weight at display size, a two-tone label (bold word, muted word), the
   value against its range as a ruler with one heavy tick, and a chip with
   a word for its state.
6. **The artefact is shown as itself.** A document is paper, a sample is a
   vial, a product is a render. The panel is a frame, the object is the
   subject, and the object gets half the viewport.
7. **One component, three scales, two materials.** A component is designed
   once, must survive in context, at poster scale and as a macro crop, and
   can be rendered opaque or translucent without changing structure.
8. **The presentation speaks the product's language.** Type set enormous
   behind the object, one slide template with fixed roles across a whole
   case study, the method drawn in the product's own cards, and the
   component shown as a poster.

### The twelve changes, in the order to make them

Tokens first, because they change nothing until used; usage rules next;
rule changes last, each with its contrast check.

| # | Change | Touches | Why |
|---|---|---|---|
| 1 | Stage tokens per scheme: `--color-stage`, `--color-stage-wash`, `--color-stage-stroke` (a light translucent stroke) and an off-white `--color-canvas` tinted toward the paper colour | Adds tokens; rule 9 stays | Depth by tone needs three named steps, and nothing in the studio's work is pure white |
| 2 | `--radius-md: 12px`, `--radius-lg: 16px` for sheets and panels; `--radius-full` for compact status containers; notes keep sharp corners | Rule 3 extended | A tonal container at 4 px reads as a form field; a note at 16 px stops reading as paper |
| 3 | `--gradient-stage`, two stops between two tones of the stage hue, permitted on the stage and on at most one hero surface per screen, never on a control | Rule 11 narrowed, not dropped | Every gradient in the set is a backdrop or one hero tile; the interface on top is flat |
| 4 | A display face for live values: `t-numeral` at 48 to 64 px, tabular, light weight, and `t-backdrop` for one word set behind an object | Adds type styles | Most of the flatness people see is body-sized numbers; no rule change needed |
| 5 | Two-tone labels as a component: a bold word and a muted word at the same size | Adds a component | One label carries heading and subheading by tone alone |
| 6 | Texture tokens: `--pattern-hatch`, `--pattern-dots`, and a dot-grid background for the board | Adds tokens; satisfies rule 29 | Series and states told apart without spending a colour, which is what rule 29 asks for |
| 7 | Usage rule: outline is the default for every control and icon button; fill is selected or active; a dark fill with a word is inactive or rejected | Extends rules 16 to 18 to controls | The system already uses this for provisional against accepted; the studio uses it everywhere |
| 8 | Usage rule: every displayed number carries a word for its state in a chip, and a value against a range is a ruler with one heavy tick | Adds to `dataviz.md` | Colour never carries state alone, and a ruler shows position without a percentage the room argues with |
| 9 | Usage rule: a saturation budget of two coloured surfaces per screen; on the board the notes are those surfaces | Adds to `principles.md` | Contrast between a muted stage and saturated paper is what makes a flat note read as rich |
| 10 | Rebuild the exemplars so the largest thing on each screen is a number, a word or the object, and show the note at three scales: on the board, as a review row, full-screen | Exemplars only | The note is the one component, and it has to survive all three |
| 11 | A `deck.css` layer: the stage tokens, larger sizes, one anchor visual per slide, one slide template with four fixed roles, the journey and stack slides drawn in the product's note and card idiom | Adds a file; no product rule touched | The deck is not the product, and a proposal that looks unfinished is read as one |
| 12 | Test, do not adopt: a translucent material for provisional notes beside the dashed stroke | Rules 17 and 18, contrast check first | One component, two materials is the studio's strongest idea, but translucent can read as dimmed on a projector, and rule 17 exists for that reason |

### What stays, and is said aloud

Three things the studio does are declined for the product, each for a
reason that belongs on a slide: frosted glass over photographs (projector
contrast), faces and avatars (the record is anonymised on export, F6.6), and
illustration or 3D as decoration (the sticky notes are the content, and
nothing may compete with them). The dashed stroke stays the one signal for
model output. Stated, the restraint reads as intent.

### For Jarvaids in particular, collected

- The session bar as a live-activity capsule: compact by default, expanded
  on tap, carrying state, unresolved count and who is in the room.
- The timeline as a row of dots with status dots for events and a floating
  "3 unresolved" pill (F2.4, F6.3).
- The note as a flat saturated card with sharp corners, a two-tone label
  (text bold, origin muted), the dashed stroke when provisional, on a muted
  tinted stage with a dot grid.
- A reading's confidence as a ruler with one heavy tick beside the text,
  and the crop it came from shown as the photograph inside the review row
  (F6.3).
- A rejected or stopped state as a dark fill with a word, never a colour.
- The deck's demo slide showing the note at poster scale, and the journey
  and stack slides drawn in the product's own cards.
