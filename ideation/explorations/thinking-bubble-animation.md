# Thinking bubble animation: what the libraries are, and whether we want one

**What this is:** a survey of the animation libraries you would reach for if you
wanted a "thinking" / "typing" / "processing" indicator in Jarvaids, measured
against this design system's rules rather than against each other. Every number
below was taken from the package itself, downloaded from the npm registry and
measured locally, or from the project's own repository. Nothing here is from a
listicle.

**Status:** research, for manual review. Nothing has been changed in the design
system and no dependency has been added.

**The short version:** none of the eighteen candidates survives the rules
intact. The only options that do are the two that involve no library at all,
and of those two, the cheaper one is the one already specified: a `waiting` dot
and the word "Thinking". Detail and code below so the decision is a real one.

---

## 1 · Comparison

Weights are measured, not quoted. "min" is the shipped minified file as it
comes out of the tarball; "gz" is that same file through `gzip -9`. Where a
package ships several builds, the smallest usable one is listed.

| # | Candidate | What it actually is | Licence | Latest, date | Weight min / gz | Offline, no CDN | Honours `prefers-reduced-motion` | Verdict against this system |
|---|---|---|---|---|---|---|---|---|
| 1 | **Nothing new** (reuse `waiting` dot + word) | Already in `components.md` § 2 | n/a | shipped | 0 B | Yes | Yes, via `grid.css` | **Survives.** It is the rule, not an exception to it |
| 2 | **Hand-rolled CSS keyframes** | ~12 lines in `grid.css` | n/a | n/a | 727 B / 361 B | Yes | Yes, via the existing global gate | **Survives**, at the cost of one new token and one `forbidden.md` amendment |
| 3 | `three-dots` | CSS-only, one element per animation | MIT | 0.3.2, 2022-12-01 | 19.0 KB / 2.5 KB (whole file) | Yes | No | **Fails.** `dot-typing` is built out of `box-shadow`, banned outright by rule 9 |
| 4 | `ldrs` | Web components, shadow DOM | MIT | 1.1.9, 2025-10-22 | 1.2 KB gz (base + `dotPulse`) | Yes | No | **Fails.** Shadow DOM defeats the global reduced-motion gate |
| 5 | `lottie-web` (`lottie_light.min.js`) | JS player for After Effects JSON | MIT | 5.13.0, 2025-05-21 | 168.4 KB / 46.4 KB | Yes, if the JSON is vendored | No | **Fails.** 128x the hand-rolled CSS for a state the word already carries |
| 6 | `lottie-web` (full `lottie.min.js`) | as above, all renderers | MIT | 5.13.0, 2025-05-21 | 305.7 KB / 76.1 KB | Yes | No | **Fails**, more so |
| 7 | `lottie-react` | React wrapper over `lottie-web` | MIT | 3.1.2, 2026-09-07 | wraps #5 / #6 | Yes | No | **Fails.** Inherits #5 and adds a React peer dependency |
| 8 | `@lottiefiles/dotlottie-web` | Rust/WASM Lottie player | MIT | 0.80.0, 2026-08-28 | JS 165.1 / 32.8 KB **plus** WASM 1,238.1 / 496.3 KB | **No by default**, fetches WASM from jsDelivr | No | **Fails rule 27 out of the box.** Needs `setWasmUrl()` to be legal here at all |
| 9 | `@lottiefiles/dotlottie-wc` | `<dotlottie-wc>` custom element | MIT | 0.9.28, 2026-08-28 | #8 plus `lit` | No, same CDN fetch | No | **Fails.** #8's problem plus a runtime framework |
| 10 | `@rive-app/canvas` | WASM runtime for Rive files | MIT (package.json; no LICENSE in tarball) | 2.42.1, 2026-09-10 | JS 450.5 / 100.5 KB **plus** WASM 1,899.7 / 783.3 KB | Yes, if self-hosted | No | **Fails.** ~884 KB gzipped, and authoring needs the Rive editor, a hosted product |
| 11 | prompt-kit `Loader` | Copy-in React + Tailwind component | MIT (declared in `package.json`) | no versioned release | 10.4 KB source | Yes | No | **Fails.** Has a real `typing` variant, but ships Tailwind classes, `animate-spin` and no gate |
| 12 | Vercel AI Elements `Loader` | shadcn registry component | Apache-2.0 | **deprecated in 1.8.2** | n/a | Yes | No | **Fails twice.** Deprecated, and its replacement is a spinner (rule 21) |
| 13 | `@chatscope/chat-ui-kit-react` `TypingIndicator` | React chat kit | MIT | 2.1.1, 2025-05-15 | component 2.1 KB ESM; package 718.7 KB unpacked | Yes | No | **Fails.** It is a UI framework (rule 25) and it pulls Font Awesome (rule 26) |
| 14 | `@assistant-ui/react` | Full chat runtime | MIT | 0.15.20, 2026-09-15 | 2.41 MB unpacked | Yes | Not verified | **Fails rule 25 by a wide margin.** Depends on `radix-ui`, `zustand`, `zod` |
| 15 | **Hand-written SVG SMIL** | `<animate>` in inline SVG, no library | n/a | n/a | ~0.3 KB | Yes | **No** | **Fails.** `prefers-reduced-motion` is a CSS media query and does not stop SMIL |
| 16 | `typed.js` | JS typewriter text | **GPL-3.0** | 3.0.0, 2026-01-24 | 10.5 KB / 3.2 KB | Yes | No | **Fails.** Wrong shape, and GPL-3.0 is a whole-product licence decision |
| 17 | `react-type-animation` | React typewriter text | MIT | 3.2.0, 2023-10-10 | 8.1 KB / 3.2 KB | Yes | No | **Fails.** Typewriter text is not a thinking indicator |
| 18 | `react-loading-indicators` | React spinner/dot set | MIT | 1.0.1, 2025-04-28 | `ThreeDot.js` 19.8 KB raw | Yes | No | **Fails.** Spinner family, rule 21 |

Two things fall out of the table immediately.

**Everything except rows 1 and 2 fails, and mostly for the same reason.** Not
because the libraries are bad. Because they are general-purpose, and this
system is not. A library that ships thirty loading animations has to ship
thirty sets of hardcoded colours and thirty sets of hardcoded timings, and
every one of those is a rule 1 violation and a motion-vocabulary violation
before you have rendered a pixel.

**Only one candidate fails the offline test outright**, and it is the one most
people would reach for first: `@lottiefiles/dotlottie-web` fetches its ~496 KB
gzipped WASM engine from `cdn.jsdelivr.net` when the first player is
constructed. Its own README says so. There is an escape (`setWasmUrl()`), but
the default behaviour is a rule 27 violation and a privacy leak in a product
that records people, which is exactly the reasoning `forbidden.md` rule 7 gives
for banning font CDNs.

---

## 2 · The recommendation

**Do not add a thinking bubble, and do not add a library.**

The reasoning is not "libraries are heavy". It is that the feature does not
survive contact with the room it is meant to be read in.

**The viewing distance kills subtlety.** `principles.md` opens with the fact
that this interface is glanced at from across a room, on a projector, by
someone mid-sentence. An 8px dot fading from opacity 1 to 0.35 and back is
already at the edge of legible at that distance. Three of them staggered by a
fifth of a second do not read as "three dots in sequence". They read as one
smudge flickering. The animation carries no information at that distance; the
word next to it carries all of it. That is precisely why `components.md` § 2
says the capturing indicator is "never the only signal" and pairs the pulse
with a word and a running timer.

**The system already has this state, fully specified.** `interaction.md`, under
"Asking the model something": *"While it is working, the panel shows a
`waiting` dot and the word 'Thinking', not a spinner."* And under
"Degradation": *"Items that are coming appear as `waiting` placeholders in
position."* There is no gap here. A thinking bubble would be a second way of
saying something the system already says, which is how a design system starts
to drift.

**A second looping animation costs more than it looks.** `interaction.md` says
"Nothing loops except the capturing pulse", and that rule is load-bearing for a
reason that is specific to this product: the capture pulse is a
**consent-critical** signal. It means microphones are live. If a second thing
on screen loops at a similar rhythm, the pulse stops being the one moving thing
and becomes one of two moving things, and "is it still recording" becomes a
question you have to answer by reading rather than by glancing. That is a real
cost, paid in the exact currency the product is most careful with.

**If the answer has to be yes**, the ranking is:

1. **Hand-rolled CSS keyframes** (row 2). 361 bytes gzipped, no dependency, no
   build step, and it inherits the existing `prefers-reduced-motion` gate for
   free because it is a plain CSS animation in a document stylesheet. Code
   below.
2. **`ldrs`** (row 4), if and only if someone rewrites the shadow-DOM styles.
   It is the only library that reads tokens correctly, because it colours
   itself through a CSS custom property (`--uib-color`) and custom properties
   inherit through shadow boundaries. You could genuinely write
   `--uib-color: var(--color-status-waiting)`. But the animation itself lives
   inside a shadow root, and the reduced-motion reset in `grid.css` is a
   document-level `*` rule, which does not cross a shadow boundary. The gate
   would silently not apply. That is an accessibility regression hidden inside
   a 1.2 KB dependency, which is the worst kind.
3. **`three-dots`** (row 3), only after rewriting `dot-typing` from scratch, at
   which point you have written row 2 with extra steps.

Everything from Lottie downwards is a category error at this scale. `lottie_light.min.js`
is 46.4 KB gzipped **before** the animation JSON, to render something the
hand-rolled version does in 361 bytes. Lottie earns its weight when a designer
needs to ship motion the engineer cannot express: easing curves, masks,
shape morphs, a brand animation. This system bans illustration and decorative
motion outright (`principles.md` § 8). There is nothing for Lottie to carry.

---

## 3 · The hand-rolled baseline

This is the honest cost of row 2. It is 727 bytes of source, 361 gzipped, and
it uses nothing that is not already in `tokens.css`. It is marked as a proposal
because `forbidden.md`'s escape hatch requires that, and because it introduces
one token that does not exist yet.

```css
/* --------------------------------------------------------------------------
   PROPOSAL: thinking-dots: not yet in the design system

   Three waiting dots, staggered, beside the word the system already
   specifies. Opacity only, because a size change or a translate would be new
   motion vocabulary; this reuses the jv-pulse shape exactly.

   It needs ONE new token. --motion-pulse is reserved for the capturing
   indicator and nothing else (interaction.md), so borrowing it here would be a
   violation, not a reuse. 1.4s is proposed rather than 2s because the ask box
   answers in seconds, not minutes, and a 2s cycle would often complete less
   than once before the answer lands.
   -------------------------------------------------------------------------- */

:root {
  --motion-think: 1.4s;              /* PROPOSAL: the thinking cycle */
}

.jv-thinking {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-2);
}

.jv-thinking__dots {
  display: inline-flex;
  gap: var(--spacing-1);
}

.jv-thinking__dot {
  width: 8px;                        /* the status dot size, components.md § 2 */
  height: 8px;
  border-radius: var(--radius-full);
  background: var(--color-status-waiting);
  animation: jv-thinking var(--motion-think) var(--motion-ease) infinite;
}

.jv-thinking__dot:nth-child(2) { animation-delay: calc(var(--motion-think) / 6); }
.jv-thinking__dot:nth-child(3) { animation-delay: calc(var(--motion-think) / 3); }

@keyframes jv-thinking {
  0%, 100% { opacity: 1; }
  50%      { opacity: 0.35; }
}

.jv-thinking__word {
  font-family: var(--font-reading);
  font-size: var(--text-meta);
  line-height: var(--text-meta--line-height);
  color: var(--color-ink);
}

/* No local @media (prefers-reduced-motion) block is needed or wanted. The
   global gate in grid.css already sets animation-iteration-count: 1 and
   animation-duration: 0.01ms on everything, so the dots settle at full opacity
   and the word carries the state alone. Writing a second gate here would be a
   second place to forget to update. */
```

And the markup:

```html
<span class="jv-thinking">
  <span class="jv-thinking__dots" aria-hidden="true">
    <span class="jv-thinking__dot"></span>
    <span class="jv-thinking__dot"></span>
    <span class="jv-thinking__dot"></span>
  </span>
  <span class="jv-thinking__word" role="status">Thinking</span>
</span>
```

Three notes on that markup, because they are the part libraries get wrong.

- **The dots are `aria-hidden`.** They are decoration on top of a word. A
  screen reader announcing "bullet bullet bullet" is worse than silence.
- **`role="status"` sits on the word, not the wrapper.** It announces
  "Thinking" once, politely, when the element appears. If it wrapped the dots
  too, some implementations re-announce on every DOM change.
- **Nothing here is a live region that repeats.** A meeting with eight people
  talking is not a place to be reannouncing a state every 1.4 seconds.

**The cost, stated honestly.** It is one new token, one keyframe, twelve lines
of CSS, and one amendment to `forbidden.md`. It is also one more thing that
loops on a screen whose only looping thing is currently the consent signal.
That second cost is larger than the first, and it is the one the decision
should actually turn on.

---

## 4 · Candidate detail

### Lottie and its players

**`lottie-web`** (Airbnb, MIT, 5.13.0, published 2025-05-21). The original.
Pure JavaScript, no dependencies, no peer dependencies, renders After Effects
JSON to SVG, canvas or HTML. Measured from the 5.13.0 tarball:

| Build | min | gzip |
|---|---|---|
| `lottie.min.js` (all renderers) | 305,704 B | 76,054 B |
| `lottie_svg.min.js` | 242,630 B | 62,320 B |
| `lottie_canvas.min.js` | 266,108 B | 67,642 B |
| `lottie_light.min.js` | 168,394 B | 46,410 B |
| `lottie_light_canvas.min.js` | 203,001 B | 54,252 B |

It is **not tree-shakeable** in any meaningful sense. You pick a prebuilt file;
you do not import three functions from it. The unpacked package is 25.4 MB,
almost all of it demos and source maps, which matters for `node_modules` size
but not for what ships.

**Offline: yes.** Grepping `lottie.min.js` for URLs returns only the three XML
namespace strings (`w3.org/2000/svg` and friends), which are identifiers, not
fetches. Vendor the player and the JSON and it runs with the network off.

**Reduced motion: no.** `prefers-reduced-motion` does not appear anywhere in
the package. You would gate it yourself with `matchMedia` and call
`anim.pause()`. That is not hard, it is just not free, and it is one more thing
that is easy to leave out.

One maintenance note, offered as a signal rather than a conclusion: 5.13.0 was
published in May 2025, so roughly sixteen months before this was written. That
is not abandonment for a library this mature, but it is not active development
either.

**`lottie-react`** (MIT, 3.1.2, 2026-09-07). A thin React wrapper. Depends on
`lottie-web ^5.13.0` and peer-depends on React 18 or 19. Adds nothing to the
size argument and adds a React coupling. Actively published.

**`@lottiefiles/dotlottie-web`** (MIT, 0.80.0, 2026-08-28). The modern
successor: a Rust player compiled to WASM. Measured from the tarball:

| File | raw | gzip |
|---|---|---|
| `dist/index.js` | 165,095 B | 32,844 B |
| `dist/dotlottie-player.wasm` | 1,238,072 B | 496,347 B |
| `dist/webgl/dotlottie-player.wasm` | 1,366,371 B | 541,814 B |
| `dist/webgpu/dotlottie-player.wasm` | 1,398,289 B | 547,509 B |

**This is the one that fails the offline bar as shipped.** Its README states
plainly: *"The player's WASM engine (~500 KB compressed) is fetched from a CDN
when the first player is constructed."* The default URL is
`https://cdn.jsdelivr.net/npm/@lottiefiles/dotlottie-web@0.80.0/dist/dotlottie-player.wasm`,
with `https://unpkg.com/...` as a fallback. The README also notes that calling
`setWasmUrl()` with an explicit path *"disables the jsdelivr/unpkg fallback"*,
so self-hosting is possible and documented. But the default is a silent CDN
fetch, and a silent CDN fetch in a product that records meetings is exactly the
failure mode `forbidden.md` rule 7 was written about. A library whose safe
configuration is opt-in is a library you will misconfigure once.

**`@lottiefiles/dotlottie-wc`** (MIT, 0.9.28, 2026-08-28). A `<dotlottie-wc>`
custom element over the above. Depends on `lit ^3.2.1` and on
`@lottiefiles/dotlottie-web@0.80.0` exactly. Everything above applies, plus a
runtime framework, plus the shadow-DOM problem described under `ldrs`.

**`@rive-app/canvas`** (2.42.1, 2026-09-10). The nearest competitor to Lottie
and the most actively published thing in this document. `package.json` declares
MIT; there is no `LICENSE` file inside the tarball, which is worth resolving
before adoption. Measured:

| File | raw | gzip |
|---|---|---|
| `rive.js` | 450,539 B | 100,501 B |
| `rive.wasm` | 1,899,725 B | 783,322 B |

That is ~884 KB gzipped of runtime. Rive's real cost is not the bytes though,
it is that authoring a `.riv` file requires the Rive editor, a hosted
commercial product. Adopting Rive means the animation source of truth lives
outside this repository, which is a poor fit for something that describes
itself as a single-file, offline, no-internet-needed deliverable.

### CSS-only approaches

**`three-dots`** (nzbin, MIT, 0.3.2, published 2022-12-01, 1.3k stars, 3 open
issues, not archived). The most-cited CSS-only answer, and it does have a
`dot-typing` style specifically. The whole stylesheet is 19,008 B minified,
2,539 B gzipped, and covers 33 animations. It ships Sass and Less sources so
you can compile just the one you want.

It still fails here, and the way it fails is instructive. This is the actual
compiled `dot-typing`:

```css
.dot-typing {
  position: relative;
  left: -9999px;
  width: 10px; height: 10px; border-radius: 5px;
  background-color: #9880ff; color: #9880ff;
  box-shadow: 9984px 0 0 0 #9880ff, 9999px 0 0 0 #9880ff, 10014px 0 0 0 #9880ff;
  animation: dot-typing 1.5s infinite linear;
}
```

The whole library's conceit is "one element", achieved by drawing the other two
dots as `box-shadow` and parking the real element 9,999 pixels off-screen.
`forbidden.md` rule 9 is "No `box-shadow` anywhere in the product", stated
without qualification. The hardcoded `#9880ff` breaks rule 1, the `10px` and
`5px` break rules 2 and 3, and `1.5s linear` is outside the motion vocabulary.
There is no `prefers-reduced-motion` anywhere in the package. Fixing all of
that leaves you with your own CSS.

Last release was December 2022, so about three and a half years dormant. For a
pure stylesheet that is close to harmless, but it does mean no one is going to
add a reduced-motion gate for you.

**`ldrs`** (Griffin Johnston, MIT, 1.1.9, 2025-10-22). The best-engineered
candidate in the list and still the wrong answer. It ships ~20 animations as
individual custom elements, each importable on its own: `LdrsBaseElement.js` is
816 B (464 B gz) and `dotPulse.js` is 2,047 B (901 B gz), so base plus one
element is 2,863 B raw and 1,187 B gzipped. Genuinely tree-shakeable, zero
dependencies, no network URLs anywhere in the package. React bindings ship in
the same package.

Two things stop it.

First, **it themes through CSS custom properties**, which is normally a virtue:
`dotPulse` styles itself with `color: var(--uib-color)` and a default of
`"black"`. Custom properties inherit across shadow boundaries, so
`--uib-color: var(--color-status-waiting)` would actually work, and this is the
only library here that could be made token-compliant without a fork.

Second, and fatally, **the animation lives inside a shadow root**. The element
calls `attachShadow({mode:"open"})` and injects its stylesheet into that root.
The reduced-motion gate in `grid.css` is a document-level rule:

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: 0.01ms !important; ... }
}
```

A `*` selector in a document stylesheet matches the custom element host, but
not the `.container::before` and `.container::after` pseudo-elements inside its
shadow root, which are where the animation actually runs. So the system's
global gate would appear to apply and would not. `prefers-reduced-motion` does
not appear anywhere in the `ldrs` package either, so there is no internal gate
to fall back on. Two mechanisms, both absent, and the failure is invisible in
review.

### SVG approaches

**Hand-written SMIL** (`<animate>`, `<animateTransform>`). No library, a few
hundred bytes, and it works in every browser that matters. It is also the one
technique in this document that I would rule out on accessibility grounds
rather than on weight.

`prefers-reduced-motion` is a **CSS** media query, and the gate in `grid.css`
works by overriding `animation-duration` and `transition-duration`. SMIL is a
declarative animation model inside SVG that does not use those CSS properties
at all, so the gate has nothing to override. A SMIL animation keeps running.
Stopping it means calling `pauseAnimations()` on the SVG element from
JavaScript, driven by a `matchMedia` listener, which is a JavaScript dependency
introduced in order to use a technique whose selling point was not needing one.

There is a second reason to leave it alone: SMIL has an unsettled history, with
a Chromium intent-to-deprecate that was raised and then not carried out. I
could not reach a primary source on its current status from this environment
(see § 6), so I am not making a claim about it. The reduced-motion argument is
sufficient on its own.

**CSS keyframes on inline SVG** has none of these problems and is just § 3
applied to an `<svg>` instead of three `<span>`s. If the indicator ever needs a
shape a span cannot make, this is the route, not SMIL.

### Purpose-built AI / chat component sets

**prompt-kit `Loader`** (ibelick, MIT per `package.json`, 3.1k stars). A
copy-in shadcn registry component, installed with
`npx shadcn@latest add prompt-kit/loader`, not an npm dependency. The source is
a single 10,389-byte `loader.tsx` exporting eleven variants including a real
`typing` one. Read directly, it:

- imports only `react` and a local `cn` helper, so it is light on dependencies;
- styles everything with Tailwind utility classes (`bg-primary`, `size-4`,
  `animate-spin`), which is a rule 1 problem: Tailwind palette classes are
  named in `forbidden.md` as the example of what not to do;
- uses `animate-spin` in several variants, which is a spinner;
- stages its dots with `style={{ animationDelay: ... }}`, which is a rule 5
  problem in spirit, though a timing value is arguably "computed";
- has **no** `prefers-reduced-motion` handling;
- gives every variant a static `<span className="sr-only">Loading</span>` and
  **no** `aria-live` region, so the state is readable but never announced.

It is honest, small work and it is the closest thing to a purpose-built answer
in this survey. It is also 90% incompatible with a system that bans Tailwind
palette classes and spinners. There is no versioned release, so "current
version" is whatever `main` is on the day you copy it.

**Vercel AI Elements** (Apache-2.0, verified from the repo `LICENSE` and the
npm package; note the GitHub summary page reports it differently, so check
before relying on it). The `ai-elements` npm package is 8,568 B unpacked
because it is only a CLI; the components arrive through the shadcn registry.
Latest is 1.9.0, 2026-03-12, actively released.

Its `Loader` is **deprecated**. The 1.8.2 release notes say, verbatim:
*"Deprecate Loader component for shadcn/ui Spinner."* The replacement is a
spinner, and rule 21 is "No spinners." This candidate rules itself out.

**`@chatscope/chat-ui-kit-react`** (MIT, 2.1.1, 2025-05-15). Has an actual
`TypingIndicator` component, which is the literal thing asked for. The built
component is 2,092 B of ESM. The package around it is 718,704 B unpacked and
depends on `@fortawesome/fontawesome-free`, `@fortawesome/fontawesome-svg-core`,
`@fortawesome/free-solid-svg-icons`, `@fortawesome/react-fontawesome`,
`classnames` and `prop-types`. That is a UI framework (rule 25) that ships an
icon package (rule 26). `prefers-reduced-motion` appears once, in the minified
bundle, so something in there respects it, but I did not trace whether the
typing indicator specifically is covered.

**`@assistant-ui/react`** (MIT, 0.15.20, 2026-09-15, 2,408,983 B unpacked).
Very actively developed. It is a complete chat runtime, depending on `zod`,
`zustand`, `radix-ui`, `assistant-cloud`, `assistant-stream`,
`react-textarea-autosize` and four of its own scoped packages. Adopting it to
get a thinking indicator is adopting a chat product to get a dot. Listed for
completeness only.

### Adjacent, and not what you want

**`typed.js`** (3.0.0, 2026-01-24, 10,490 B raw / 3,206 B gzipped) is a
typewriter effect, not a thinking indicator. Worth naming for one reason: as of
3.0.0 it is **GPL-3.0**, confirmed from `LICENSE.txt` in the tarball, which
opens *"Typed.js, a javascript typing animation library / Copyright (C) 2026
Matt Boldt"* followed by the GPL v3 text. Earlier versions were permissive.
That is a whole-product licensing decision, not a UI one.

**`react-type-animation`** (MIT, 3.2.0, 2023-10-10, 8,087 B / 3,188 B gz). Same
category, permissive licence, dormant since 2023.

**`react-loading-indicators`** (MIT, 1.0.1, 2025-04-28). Spinners and dots as
React components; `ThreeDot.js` alone is 19,759 B raw. No
`prefers-reduced-motion` in the package. Rule 21.

**`SpinKit`** (MIT, 2.0.1, published 2019-10-30). Included because it is still
the first result for "CSS loading animation". Six and a half years without a
release, and it is spinners by name.

---

## 5 · What a thinking bubble bends or breaks

If the decision is to build one anyway, these are the rules it touches. Listing
them so the amendment is deliberate rather than discovered in an audit.

**Breaks outright:**

| Source | Rule | How |
|---|---|---|
| `interaction.md`, Motion | *"Nothing loops except the capturing pulse."* | A thinking indicator loops. This is the real cost, because the capture pulse is a consent signal and it currently owns being the only moving thing on screen |
| `interaction.md`, Motion | *"`--motion-pulse` 2s: the capturing indicator, and nothing else."* | Needs a second looping duration token, or an illegal reuse of this one |
| `tokens.css` | `--motion-pulse` comment: *"the capturing indicator, and only that"* | Same, stated again in the token file |

**Bends:**

| Source | Rule | How |
|---|---|---|
| `interaction.md`, Motion | *"Motion marks a state change the user caused."* | Arguably satisfied: the user asked the question. Worth stating rather than assuming |
| `principles.md` § 8 | *"Restraint. No illustration, no decorative motion, no gradients, no photography as atmosphere."* | The dots are decorative, since the word carries the state. This is the principle the feature has to argue against |
| `principles.md` § 4 | *"Status is a dot and a word, always both."* | Three dots plus a word is not the specified shape. Either the pattern generalises to "dots and a word" or it gets a documented exception |
| `forbidden.md` rule 21 | *"No spinners. Skeletons for first load, a `waiting` dot and a word for work in progress."* | This rule already prescribes the answer. A thinking bubble is a third option it does not allow for |

**What `forbidden.md` would have to say.** Rule 21 is the one that needs
changing, and the smallest honest amendment is to widen the prescription rather
than add an exception:

> 21. **No spinners.** Skeletons for first load; a `waiting` dot and a word for
>     work in progress. Where the wait is short and the user caused it, the
>     dot may be a group of three, staggered on opacity only, at
>     `--motion-think`. The word is never optional and the dots are never the
>     only signal.

And `interaction.md`'s Motion table needs a fourth row plus a rewrite of
"Nothing loops except the capturing pulse" to "Two things loop: the capturing
pulse and the thinking dots. Nothing else." That sentence is the one to read
twice before agreeing, because it is where the consent signal loses its
exclusivity.

If the amendment is not worth making, the feature is not worth building, and
`waiting` dot plus "Thinking" is already there and already correct.

---

## 6 · What I could not verify

Stated plainly rather than papered over.

- **SMIL's current deprecation status.** MDN, caniuse, chromestatus and the
  Chromium `blink-dev` thread are all blocked by this environment's egress
  proxy. Secondary sources say the 2015 intent to deprecate was withdrawn and
  SMIL still ships, but I did not reach a primary source, so I make no claim.
  The recommendation against SMIL rests on the reduced-motion argument in § 4,
  which I verified by reading `grid.css` directly.
- **`css-loaders.com`** (Temani Afif's collection, frequently recommended) is
  blocked by the proxy, so I could not check its licence terms or its markup.
  It is copy-paste CSS rather than a package, so it collapses into "hand-rolled
  CSS with a starting point" either way.
- **prompt-kit's licence file.** `package.json` declares MIT and the GitHub
  repository page reports MIT, but there is no `LICENSE`, `LICENSE.md` or
  `LICENSE.txt` at the repository root that I could fetch. Confirm before
  copying code in.
- **Rive's licence file.** `@rive-app/canvas@2.42.1` declares MIT in
  `package.json` but ships no `LICENSE` in the tarball.
- **`@chatscope/chat-ui-kit-react`'s reduced-motion coverage.** The string
  appears in the minified bundle; I did not trace whether it wraps the
  `TypingIndicator` specifically.
- **Repository commit activity and star counts** beyond `three-dots`,
  `ai-elements` and `prompt-kit`. The GitHub API is not reachable from this
  session, so maintenance is judged from npm publish history, which is a
  reasonable proxy and not the same thing.
- **The AI Elements release dates** shown on its GitHub releases page were read
  back inconsistently by the fetcher, so the dates in the table come from the
  npm registry instead. The deprecation wording was confirmed from the releases
  page.

---

## 7 · Sources

Package metadata and all measured sizes come from the npm registry API and from
the published tarballs, downloaded and measured locally:

- `https://registry.npmjs.org/lottie-web` and `lottie-web-5.13.0.tgz`
- `https://registry.npmjs.org/lottie-react`
- `https://registry.npmjs.org/@lottiefiles/dotlottie-web` and `dotlottie-web-0.80.0.tgz`
- `https://registry.npmjs.org/@lottiefiles/dotlottie-wc`
- `https://registry.npmjs.org/@rive-app/canvas` and `canvas-2.42.1.tgz`
- `https://registry.npmjs.org/three-dots` and `three-dots-0.3.2.tgz`
- `https://registry.npmjs.org/ldrs` and `ldrs-1.1.9.tgz`
- `https://registry.npmjs.org/@chatscope/chat-ui-kit-react` and `chat-ui-kit-react-2.1.1.tgz`
- `https://registry.npmjs.org/@assistant-ui/react`
- `https://registry.npmjs.org/ai-elements`
- `https://registry.npmjs.org/typed.js` and `typed.js-3.0.0.tgz`
- `https://registry.npmjs.org/react-type-animation` and `react-type-animation-3.2.0.tgz`
- `https://registry.npmjs.org/react-loading-indicators` and `react-loading-indicators-1.0.1.tgz`
- `https://registry.npmjs.org/spinkit`

Repositories and source files read directly:

- `https://github.com/nzbin/three-dots`
- `https://github.com/vercel/ai-elements`
- `https://github.com/vercel/ai-elements/releases`
- `https://raw.githubusercontent.com/vercel/ai-elements/main/LICENSE`
- `https://github.com/ibelick/prompt-kit`
- `https://raw.githubusercontent.com/ibelick/prompt-kit/main/components/prompt-kit/loader.tsx`
- `https://raw.githubusercontent.com/ibelick/prompt-kit/main/package.json`

In-repository sources for every design-system claim:

- `app/design-system/tokens.css`
- `app/design-system/grid.css`
- `app/design-system/spec/forbidden.md`
- `app/design-system/spec/interaction.md`
- `app/design-system/spec/principles.md`
- `app/design-system/spec/components.md`
- `deliverables/documentation/flowchart.md`
