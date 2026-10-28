# Apple's corner concentricity APIs

Researched September 2026, against Apple's own documentation, Human Interface
Guidelines and session video transcripts. Every API named here is backed by a
URL that was fetched during the research. Anything that could not be fetched is
marked **UNVERIFIED** in place, not quietly smoothed over.

One constraint on this research, stated up front: from the session it was
written in, outbound fetching was allowed to `developer.apple.com` only. All
Apple claims below are from pages actually retrieved. The CSS section at the end
is the weak part, because `drafts.csswg.org`, `developer.mozilla.org`,
`webkit.org`, `chromestatus.com` and `caniuse.com` were all blocked. That
section is marked accordingly.

---

## 1. The concept

### What Apple says it is

Apple's word for it is **concentricity**, and it is one of the three things the
2025 design system is built on. From "Get to know the new design system"
(WWDC25 session 356):

> There's a quiet geometry to how our shapes fit together, driven by
> concentricity. By aligning radii and margins around a shared center, shapes
> can comfortably nest within each other.

and, in the same session, the rule in one line:

> We use three shape types to build concentric layouts: fixed shapes have a
> constant corner radius. Capsules use a radius that's half the height of the
> container. And concentric shapes calculate their radius by subtracting
> padding from the parent's.

The API documentation states the same thing as an algorithm. From
`Edge.Corner.Style.concentric`:

> When a corner is concentric to its container, the system calculates the
> corner radius to equal the container shape's corner radius minus the distance
> between corners. When the system calculates a zero radius, the corner is
> square.

So Apple's own definition of the relationship is:

```
inner radius = outer radius - padding        (floored at zero)
```

### Why that is the right number

Take the top-left corner. Put the origin at the outer box's corner. An outer
rounded rectangle with radius `r` has its corner arc centred at `(r, r)`. Inset
a child by `d` on every side: the child's box corner is at `(d, d)`, so a child
with radius `r_i` has its arc centred at `(d + r_i, d + r_i)`.

The two arcs share a centre when:

```
d + r_i = r     therefore     r_i = r - d
```

That is the whole of it. Sharing a centre is not an aesthetic preference, it is
the only condition under which the gap between the two curves is the same
everywhere. Two arcs about a common centre are separated by the difference of
their radii at every angle, which here is `r - (r - d) = d`, exactly the padding
you set on the straight edges. The curves stay parallel, so the eye reads one
continuous margin all the way round.

### Why equal radii look wrong

Measure the perpendicular gap between the two curves at 45 degrees, where the
error is largest. For circular corners it works out to:

```
corner gap = sqrt(2) * [ d - (r - r_i) * (1 - 1/sqrt(2)) ]
```

With an outer radius of 20pt and 8pt of padding:

| inner radius | what it is | gap at the corner | gap along the edge |
|---|---|---|---|
| 12pt | `r - d`, correct | 8.00pt | 8pt |
| 20pt | same radius as the container | 11.31pt | 8pt |
| 8pt | radius set equal to the padding, a common mistake | 6.34pt | 8pt |
| 0pt | square inner corner | 3.03pt | 8pt |

Reusing the container's radius opens the corner gap by 41 per cent. The inner
card appears to shrink away from the container at its corners and to be
correctly inset along its edges, which is read as the container's curve being
too *flared*. Too small a radius does the opposite and the corner looks
*pinched*. WWDC25 356 uses exactly those two words:

> As you're updating your apps, keep an eye out for corners that feel too
> pinched, or flared. They can create tension and break the sense of balance.
> One place this often shows up in is nested containers, like artwork in a card.

There is a second, harder failure. A square inner corner sits at `(d, d)`, which
is at distance `sqrt(2) * (r - d)` from the outer arc's centre. It escapes the
container's curve entirely when that exceeds `r`, that is when:

```
d < r * (1 - 1/sqrt(2))  ~=  0.293 * r
```

| outer radius | square inner corner pokes out if padding is under |
|---|---|
| 4pt | 1.17pt |
| 8pt | 2.34pt |
| 12pt | 3.51pt |
| 20pt | 5.86pt |
| 44pt | 12.89pt |

This is what the Live Activities HIG is describing when it says even margins
"prevent elements from poking into the rounded shape of the Live Activity and
creating visual tension".

The derivation and the two tables above are mine, computed for circular arcs.
Apple publishes the `r - d` rule, not the error maths. Apple's corners are not
circular arcs (section 4), so the exact figures shift slightly, but the sign and
the rough magnitude of each error do not.

### Non-uniform padding

If the horizontal and vertical insets differ, no single circular arc can share a
centre with the parent in both axes, so there is no one correct radius. Apple
resolves this per corner and gives you a switch to force symmetry, which is what
`isUniform` is for. From Apple Developer Technical Support on the forums:

> Concentricity only makes sense when the bounds of the corner and its parent
> corner or edge area intersect, allowing them to form a common center in one or
> both axes.

---

## 2. The APIs

### SwiftUI: `ConcentricRectangle`

The shape type. `struct ConcentricRectangle`, **iOS 26.0, iPadOS 26.0, Mac
Catalyst 26.0, macOS 26.0, tvOS 26.0, visionOS 26.0, watchOS 26.0**. It conforms
to `Shape`, `View`, `Animatable` and `Sendable`.

> Use `ConcentricRectangle` to create a rectangular shape that fits inside a
> container's shape, similar to the way that a sheet's corners in iOS match the
> curvature of the screen. System-provided elements like sheets and popovers do
> this automatically.

`init()` is the important one: it makes a shape whose four corners are each
independently concentric with the container.

Initialisers, all iOS 26.0, all with a matching `Shape` static method
(`rect(...)`) so they compose in `clipShape` and `glassEffect(in:)` position:

```swift
init()
init(corners: Edge.Corner.Style, isUniform: Bool = false)
init(topLeadingCorner:topTrailingCorner:bottomLeadingCorner:bottomTrailingCorner:)
init(uniformTopCorners:uniformBottomCorners:)
init(uniformTopCorners:bottomLeadingCorner:bottomTrailingCorner:)
init(uniformBottomCorners:topLeadingCorner:topTrailingCorner:)
init(uniformLeadingCorners:uniformTrailingCorners:)
init(uniformLeadingCorners:topTrailingCorner:bottomTrailingCorner:)
init(uniformTrailingCorners:topLeadingCorner:bottomLeadingCorner:)
```

Only `init()` and `init(corners:isUniform:)` were opened individually; the rest
are listed by name on the `ConcentricRectangle` page, and their parameter labels
are therefore verified but their full signatures are not.

`isUniform` is worth understanding, because it is the difference between "each
corner is correct" and "the shape looks symmetric":

> When you provide `false` for `isUniform`, the system may calculate a different
> radius for each corner. This can happen when the rectangle is not centered
> within the container shape, or the container shape's corners have different
> radii. When you provide `true` for `isUniform`, the system calculates the
> radius for each corner first. Then, it selects the largest radius and applies
> it to each corner to achieve the symmetric look.

### SwiftUI: the corner styles

`Edge.Corner.Style`, **iOS 26.0** and the other platforms at 26.0. A corner is
square, a fixed radius, or concentric.

```swift
static var concentric: Edge.Corner.Style { get }
static func concentric(minimum: ...) -> Edge.Corner.Style     // listed, signature not fetched
static func fixed(_: ...) -> Edge.Corner.Style                // listed, signature not fetched
```

`Edge.Corner.Style` conforms to `ExpressibleByFloatLiteral` and
`ExpressibleByIntegerLiteral`, so a bare number is a fixed radius.

The sibling type `RoundedRectangularShapeCorners` (iOS 26.0) carries the version
whose full signature was verified:

```swift
static func concentric(minimum: Edge.Corner.Style? = nil) -> RoundedRectangularShapeCorners
```

> Corner styles will be concentric with its container, varying the radius as
> needed in all four corners but never going below zero, or the provided minimum
> corner style, if provided.

### How a shape learns its container's radius

Two ways.

**Implicitly.** System containers set it. Sheets, popovers and the device's own
screen edge already provide a container shape, which is why
`ConcentricRectangle().padding(8).ignoresSafeArea()` works with no further
setup.

**Explicitly**, with `containerShape(_:)`. There are two overloads and they are
not the same:

```swift
// iOS 26.0, macOS 26.0. Feeds both ContainerRelativeShape and ConcentricRectangle.
nonisolated func containerShape(_ shape: some RoundedRectangularShape) -> some View

// iOS 15.0, macOS 12.0. Feeds ContainerRelativeShape only.
nonisolated func containerShape<T>(_ shape: T) -> some View where T : InsettableShape
```

The iOS 26 overload takes `RoundedRectangularShape`, a new protocol
(**iOS 26.0**) that refines `InsettableShape` and exposes corner information via
`func corners(in size: CGSize?) -> Self.Corners?`. `Rectangle`,
`RoundedRectangle`, `UnevenRoundedRectangle`, `Capsule` and `Circle` conform
already. Apple's own container pattern:

```swift
struct PlatterContainer<Content: View> : View {
    @ContentBuilder var content: Content
    var body: some View {
        content
            .padding()
            .containerShape(shape)
            .background(shape.fill(.background))
    }
    var shape: RoundedRectangle { RoundedRectangle(cornerRadius: 20) }
}
```

### When there is nothing to inherit from

Three separate fallbacks, and they are easy to confuse.

1. **The container shape does not describe its corners.** If the shape passed to
   `containerShape(_:)` does not conform to `RoundedRectangularShape`,
   "`ConcentricRectangle` provides an inset version of the container shape like
   `ContainerRelativeShape`".
2. **There is no container shape at all.** `ContainerRelativeShape`: "If there
   is not a current container shape, the system provides a rectangle." Square
   corners.
3. **The corner is too far from the parent's corner to share a centre.** The
   computed radius is zero and the corner is square. This is the one that
   surprises people, and the fix is the minimum:

   > It's also possible that your app is running on a device whose corners are
   > square. To ensure that your view always has rounded corners that are
   > concentric relative to the container shape when they can be, use
   > `concentric(minimum:)`.

   WWDC25 356 calls the same move a fallback radius:

   > here's a neat trick for managing components that need to work both inside a
   > container and on their own: use a concentric shape with a fallback radius.
   > The concentric value adapts when nested, and the fallback kicks in when the
   > component stands alone.

### `ConcentricRectangle` versus `ContainerRelativeShape`

They are not interchangeable, and the difference is the single most common
source of confusion in the field. `ContainerRelativeShape` has existed since
**iOS 14.0 / macOS 11.0**: "A shape whose dimensions the system calculates from
an inset version of the current container shape." Apple DTS, on the forums:

> A `ConcentricRectangle` shape behaves differently from a
> `ContainerRelativeShape` when a corner lies within the inner region of a
> parent shape, a `ContainerRelativeShape` will retain a rounded corner, whereas
> a concentric shape will have a square corner because the corner cannot form a
> common center with its parent.

Put plainly: `ContainerRelativeShape` scales the parent's shape down and keeps
it rounded whether or not that is geometrically honest. `ConcentricRectangle`
refuses to invent a shared centre that does not exist and squares the corner
instead. `ContainerRelativeShape` flatters, `ConcentricRectangle` is correct.
Use `concentric(minimum:)` when you want correctness with a floor.

### UIKit

Same model, different spelling. All **iOS 26.0, iPadOS 26.0, Mac Catalyst 26.0,
tvOS 26.0, visionOS 26.0**. Note the absence of macOS: this family is not on
AppKit at 26.

```swift
@MainActor var cornerConfiguration: UICornerConfiguration { get set }   // on UIView
struct UICornerConfiguration
struct UICornerRadius
static func containerConcentric(minimum: CGFloat? = nil) -> UICornerRadius
static func fixed(_:) -> UICornerRadius                                  // listed, signature not fetched
static func corners(radius: UICornerRadius) -> UICornerConfiguration
```

Apple's samples:

```swift
myView.cornerConfiguration = .corners(radius: 12.0)                  // fixed
myView.cornerConfiguration = .corners(radius: .containerConcentric()) // concentric
myView.cornerConfiguration = .capsule()                               // capsule
```

> The system uses squared corners by default, so you don't need to set a
> configuration to get squared corners.

`UICornerConfiguration` also has the uniform family: `uniformCorners(radius:)`,
`uniformEdges(topRadius:bottomRadius:)`, `uniformEdges(leftRadius:rightRadius:)`
and the four `uniform<Edge>Radius(_:...)` variants. `capsule(maximumRadius:)`
lets a capsule give up and stretch rather than exceed a radius you name.

### AppKit

`NSViewCornerConfiguration` exists and is **macOS 27.0**, a class rather than a
struct, with `capsule`, `corners(radius:)`, `uniformCorners(radius:)` and the
uniform-edge family. **UNVERIFIED:** I did not find a documented concentric
radius type for AppKit. The type listing on that page shows no
`containerConcentric` equivalent and I did not open its radius type. Treat
AppKit concentricity as unconfirmed.

### Related, and worth knowing

- `GeometryProxy.containerCornerInsets` (**iOS 26.0**), returning
  `RectangleCornerInsets`: "Returns the corner insets of the container view.
  Corner insets may include pieces of system UI as well as the corner radii for
  windows and presentations." Useful for nudging content out of a corner, not
  for computing a radius. On iPadOS and macOS the insets are zero when the
  window fills the screen with no window controls showing.
- `presentationCornerRadius(_:)` (**iOS 16.4**) sets a sheet's radius. If you
  set it, you have changed what your content should be concentric with.
- `View.cornerRadius(_:antialiased:)` (iOS 13.0) is **deprecated as of iOS 27.0**
  in favour of `clipShape(_:style:)` or `Shape.fill(style:)`. Do not reach for
  it.

---

## 3. The hardware angle

### The screen's own corners

The display is a container shape with a large radius, and Apple treats it as
one. `ConcentricRectangle`'s stated purpose includes matching it:

> You can use this effect for your custom views to match a device's curved
> edges [...] the Notes app format sheet has rounded bottom corners that are
> concentric relative to the device's corners, and rounded top corners that have
> a fixed radius.

The Tech Talk "Prepare your app for iPhone Duo" is blunter, and gives the
canonical snippet:

> To make sure your UI fits the corners of the screen perfectly, use
> Concentricity APIs introduced in iOS 26. They're updated to work with the
> screen shapes on iPhone Duo. For SwiftUI, use `ConcentricRectangle`. For
> UIKit, use `UICornerConfiguration`.

```swift
// SwiftUI
ConcentricRectangle()
    .fill(Color.green)
    .padding(8.0)
    .ignoresSafeArea()
```

Note what is missing: a number. **There is no public API that reports the
display's corner radius.** I looked: `UIScreen`'s symbol listing contains no
corner-related property at all. The whole design of these APIs is that you never
learn the radius, you declare the relationship and the system resolves it. That
is also why the same code is correct on a device whose screen corners are
square: the computed radius becomes zero.

The other half of fitting the hardware is the safe area, and the two are
separate problems. The same Tech Talk splits them: foreground content is inset
by the safe area (`foreground.frame = view.bounds.inset(by: view.safeAreaInsets)`)
while background content extends past it. `ignoresSafeArea()` in the snippet
above is what lets the shape reach the physical corner so that there is
something to be concentric with. A shape stopped at the safe area has a
different container and a different answer.

### Dynamic Island and Live Activities

Verified numbers, from the Live Activities HIG:

- **The Dynamic Island's corner radius is 44 points**, and "its rounded corner
  shape matches the TrueDepth camera".
- Dynamic Island width is 230pt on iPhone 17 Pro, 16 Pro, 15 Pro, 15, 14 Pro and
  iPhone 17, and 250pt on the Max and Plus sizes and iPhone Air, in compact and
  minimal presentations. Expanded is 371pt or 408pt on the same split.
- Lock Screen and expanded Live Activities are 84 to 160 points tall, 371pt wide
  on a 393x852 screen and 408pt wide on a 430x932 screen.

The guidance for the nesting itself:

> Use consistent margins and concentric placement. Use even, matching margins
> between rounded shapes and the edges of the Live Activity, including corners,
> to ensure a harmonious fit. [...] For example, when placing a rounded
> rectangle near a corner of your Live Activity, match its corner radius to the
> outer corner radius of the Live Activity by subtracting the margin and using a
> SwiftUI container to apply the correct corner radius.

and

> When separating a block of content, place it in an inset container shape or
> use a thick line. Don't draw content all the way to the edge of the Dynamic
> Island.

So the three-layer nesting is: the Live Activity container, whose radius the
system owns and does not publish; an inset panel inside it, which should be
concentric by subtraction; and the Dynamic Island cutout at 44pt, which your
content must stay clear of rather than nest inside.

Two honest caveats.

- The HIG's "developer guidance" link for that rule still points at
  **`ContainerRelativeShape`**, not at `ConcentricRectangle`. Given the DTS
  explanation above, those two produce different results for a panel that is not
  touching the corner. Apple's written design guidance has not caught up with
  Apple's newer API.
- **UNVERIFIED:** whether `ConcentricRectangle` resolves against the Live
  Activity container shape in a widget extension. Apple documents that system
  containers provide container shapes and names sheets and popovers; I found no
  page stating this for Live Activities. Test it before relying on it, and set
  an explicit `containerShape(_:)` if it does not resolve.
- The widgets HIG carries the same instruction in general form: "Coordinate the
  corner radius of your content with the corner radius of the widget. To ensure
  that your content looks good within a widget's rounded corners, use a SwiftUI
  container to apply the correct corner radius."

### Icons

Worth knowing because it shows how far Apple takes this. The app icon mask is
not a generic rounded rectangle: icons are masked "to produce rounded corners
that precisely match the curvature of other rounded interface elements
throughout the system and the bezel of the physical device itself". The 2025
icon grid was redrawn for it: "the new grid also features a rounder corner
radius, which makes the icons sit more concentric with our UI and even within
our hardware."

---

## 4. Squircles

### What Apple actually exposes

Apple's public vocabulary is **continuous curvature**, not squircle and not
superellipse. The knobs are:

| API | Since | Values |
|---|---|---|
| `RoundedCornerStyle` (SwiftUI) | iOS 13.0, macOS 10.15 | `.circular`, `.continuous` |
| `CALayer.cornerCurve` / `CALayerCornerCurve` | iOS 13.0, macOS 10.15 | `.circular`, `.continuous` |
| `UICornerCurve` (UIKit) | iOS 17.0 | `.automatic`, `.circular`, `.continuous` |

The documentation for the two SwiftUI cases is one line each, and that is the
entire published description of the difference:

- `.circular`: "Quarter-circle rounded rect corners."
- `.continuous`: "Continuous curvature rounded rect corners."

`RoundedRectangle(cornerRadius:style:)` and
`UnevenRoundedRectangle(cornerRadii:style:)` both take the style. The difference
from a plain radius is curvature continuity: a circular corner switches from
zero curvature on the straight edge to constant curvature `1/r` at a single
point, and that discontinuity is visible as a slight kink where the edge meets
the corner. A continuous corner ramps the curvature in, so the transition has no
seam. It also starts curving further from the corner, which is why a continuous
corner at the same nominal radius looks softer and slightly larger.

**UNVERIFIED, and important:** Apple does not publish the curve. There is no
Apple page giving a formula, a superellipse exponent, or control point
positions, and none of the pages fetched here mention "squircle" or
"superellipse" at all, including the app icon HIG. Any exponent you have seen
quoted for Apple's corner comes from third-party reverse engineering, not from
Apple. Do not put such a number in a spec and call it Apple's.

**UNVERIFIED:** which curve `ConcentricRectangle` draws. It has no `style:`
parameter in any of its documented initialisers, and no page states whether it
uses continuous corners. Given that it is the new-design-system shape, it
presumably does, but that is inference. Check it against a screenshot before
relying on it.

Two practical notes that follow from the above. First, `.continuous` is a
separate axis from concentricity: getting the radius right and getting the curve
right are two different corrections, and a nested card can be wrong in either or
both. Second, mixing a `.circular` inner shape inside a `.continuous` outer one
breaks the parallel-curve effect even when the radius arithmetic is correct,
because the two curves have different shapes.

---

## 5. Worked examples

### A. A card inside a container, done right and done wrong

```swift
// RIGHT. Container radius 20, padding 8, so the inner radius resolves to 12.
// Nothing here hard-codes 12: change the padding and the inner radius follows.
struct CardStack: View {
    var body: some View {
        VStack {
            ConcentricRectangle()
                .fill(.white)
                .frame(height: 120)
        }
        .padding(8)
        .containerShape(RoundedRectangle(cornerRadius: 20))
        .background(RoundedRectangle(cornerRadius: 20).fill(.gray.opacity(0.2)))
    }
}
```

```swift
// WRONG, version one: the inner radius reuses the container's number.
// Corner gap becomes 11.31 against an 8pt edge gap. The container reads flared.
RoundedRectangle(cornerRadius: 20)
    .fill(.white)
    .frame(height: 120)
    .padding(8)
    .background(RoundedRectangle(cornerRadius: 20).fill(.gray.opacity(0.2)))
```

```swift
// WRONG, version two: the radius is pinned to a token from a scale.
// It is 12 today by luck. Change the padding to 12 and it is wrong, silently.
RoundedRectangle(cornerRadius: 12)
    .fill(.white)
    .padding(8)
```

The second wrong version is the dangerous one, because it looks right. The bug
is that the relationship is not expressed, so nothing keeps the two numbers in
step when someone changes the padding.

### B. A component that must work nested and standalone

```swift
// A badge that is concentric when it sits in the corner of a card, and falls
// back to 8pt when it is used on its own or sits away from any corner.
ConcentricRectangle(corners: .concentric(minimum: 8.0))
    .fill(.tint)
    .frame(width: 64, height: 28)
```

Without the minimum, the same badge goes square the moment it is not near a
corner, because the system computes a zero radius and a zero radius means a
square corner. That is correct behaviour and almost never what you want for a
badge.

### C. Fitting the device's screen corner

```swift
// Apple's own snippet. The padding is the only number; the screen's radius is
// never named, and the same code is correct on a square-cornered display.
ConcentricRectangle()
    .fill(Color.green)
    .padding(8.0)
    .ignoresSafeArea()
```

```swift
// Apple's mixed-corner example: bottom corners hug the device, top corners are
// a designed constant, as in the Notes format sheet.
ConcentricRectangle(
    uniformTopCorners: .fixed(24.0),
    uniformBottomCorners: .concentric
)
.fill(Color.green)
.padding(8.0)
.ignoresSafeArea()
.frame(height: 240.0)
```

Both snippets are Apple's, taken verbatim from the `ConcentricRectangle` page
and the iPhone Duo Tech Talk. Drop `.ignoresSafeArea()` and the shape no longer
reaches the physical corner, so there is nothing for it to be concentric with.

---

## 6. What this means for this repo's web design system

Read against `/home/user/GenAI/app/design-system/tokens.css`, which declares the
whole radius scale in three lines:

```css
/* Radii: three steps. Nothing else. */
--radius-xs: 2px;     /* nested inside a radius-sm container */
--radius-sm: 4px;     /* the default: buttons, fields, canvas items, panels */
--radius-full: 999px; /* dots and pills only */
```

### What transfers

**The principle transfers completely, and this system already half-encodes it.**
The comment on `--radius-xs` says "nested inside a radius-sm container". Apply
Apple's rule: 4px outer minus 2px padding gives a 2px inner radius. The scale is
already concentric, for exactly one padding value, 2px. That is worth writing
down in the token comment, because right now the relationship is implied by
adjacency in a file and nothing protects it.

**The failure modes transfer.** A nested panel reusing `--radius-sm` inside a
`--radius-sm` container is the flared case. At this scale the absolute error is
about 1.7px on a 4px radius with 4px padding, which is small but not invisible
on a hairline-based canvas where there are no shadows or fills to hide it.

**The poke-out rule transfers and mostly lets you off.** A square inner corner
escapes a 4px outer curve only if the padding is under 1.17px, and this system's
smallest real padding is larger than that. So square inner corners are safe here.
Given a 4px scale, that is usually the right answer: with 8px of padding inside a
4px container, the honest concentric radius is `max(0, 4 - 8)` which is zero.
**At small radii, concentricity mostly tells you to stop rounding the inside.**
That is a genuinely useful rule and it costs nothing to follow.

**Capsules transfer.** `--radius-full: 999px` is Apple's capsule shape type, and
WWDC25 356 notes that "the capsule's geometry naturally supports concentricity",
because a radius of half the height stays correct as the height changes.

### What does not transfer

**Nothing on the web resolves a radius from its container.** There is no CSS
equivalent of `ConcentricRectangle`, `ContainerRelativeShape` or
`containerShape(_:)`. Container queries can query size, not border-radius, and
there is no way to read an ancestor's computed radius from a descendant. You
must do the subtraction yourself, in a custom property, every time.

The only safe pattern is to make the relationship explicit rather than to write
the answer down:

```css
/* The padding is the source of truth. The inner radius is derived from it, so
   changing the padding cannot silently break the corner. */
.panel {
  --panel-radius: var(--radius-sm);   /* 4px */
  --panel-pad: 2px;
  border-radius: var(--panel-radius);
  padding: var(--panel-pad);
}
.panel > .inset {
  border-radius: max(0px, calc(var(--panel-radius) - var(--panel-pad)));
}
```

`max(0px, ...)` is doing the same job as Apple's "never going below zero".

**There is no web access to the display's corner radius either**, and unlike
native there is no API that resolves the relationship for you, so the whole
category of device-edge concentricity is simply unavailable in a browser. The
closest thing is the safe-area inset environment variables for the notch and
home indicator, which give you a keep-out distance and not a curve. **UNVERIFIED:**
I could not fetch MDN or the CSS specs from this session to confirm the current
state of that.

### Continuous corners in CSS

**This section could not be verified against primary sources and should be
re-checked before anything is built on it.** `drafts.csswg.org`,
`developer.mozilla.org`, `webkit.org`, `chromestatus.com` and `caniuse.com` were
all blocked by the network egress policy in this session. What follows comes
from search-result summaries of those pages, not from pages I fetched.

The reported state of the world, September 2026:

- CSS has a `corner-shape` property, specified in CSS Borders and Box
  Decorations Level 4, that sets the geometry of a corner while `border-radius`
  continues to set its size.
- Values are reported as `round`, `bevel`, `notch`, `scoop`, `square`, `squircle`
  and `superellipse(k)`, with `round` = `superellipse(1)` and the initial value,
  `squircle` = `superellipse(2)`, `bevel` = `superellipse(0)`,
  `scoop` = `superellipse(-1)`, `square` = `superellipse(infinity)`. Negative
  values curve inward.
- Support: Chromium only, from Chrome 139, with WebKit support reported in
  Safari Technology Preview 251. MDN is reported to say the feature "is not
  Baseline because it does not work in some of the most widely-used browsers"
  and to describe it as experimental.

Two things to be honest about even if all of that checks out. First,
`corner-shape: squircle` is `superellipse(2)`, and Apple has never published
what its own continuous corner is, so "squircle" in CSS is not documented to be
Apple's curve and should not be described as such. Second, none of it helps with
concentricity: `corner-shape` changes the shape of a corner, it does not derive a
radius from a container. The subtraction is still yours to do.

**Recommendation for this system:** do the arithmetic in custom properties, keep
`border-radius` circular, and do not adopt `corner-shape` yet. At a 4px scale the
difference between a circular and a continuous corner is well under a pixel, so
it buys nothing, and it is a non-Baseline feature in one engine family.

---

## Sources

Every URL below was fetched during this research, except where noted.

**SwiftUI**

- https://developer.apple.com/documentation/swiftui/concentricrectangle
- https://developer.apple.com/documentation/swiftui/concentricrectangle/init(corners:isuniform:)
- https://developer.apple.com/documentation/swiftui/shape/rect(corners:isuniform:)
- https://developer.apple.com/documentation/swiftui/edge/corner/style
- https://developer.apple.com/documentation/swiftui/edge/corner/style/concentric
- https://developer.apple.com/documentation/swiftui/roundedrectangularshapecorners
- https://developer.apple.com/documentation/swiftui/roundedrectangularshapecorners/concentric(minimum:)
- https://developer.apple.com/documentation/swiftui/roundedrectangularshape
- https://developer.apple.com/documentation/swiftui/roundedrectangularshape/corners(in:)
- https://developer.apple.com/documentation/swiftui/view/containershape(_:)
- https://developer.apple.com/documentation/swiftui/view/containershape(_:)-qn9q
- https://developer.apple.com/documentation/swiftui/containerrelativeshape
- https://developer.apple.com/documentation/swiftui/geometryproxy/containercornerinsets
- https://developer.apple.com/documentation/swiftui/roundedrectangle
- https://developer.apple.com/documentation/swiftui/unevenroundedrectangle
- https://developer.apple.com/documentation/swiftui/rectanglecornerradii
- https://developer.apple.com/documentation/swiftui/roundedcornerstyle
- https://developer.apple.com/documentation/swiftui/roundedcornerstyle/circular
- https://developer.apple.com/documentation/swiftui/roundedcornerstyle/continuous
- https://developer.apple.com/documentation/swiftui/view/cornerradius(_:antialiased:)
- https://developer.apple.com/documentation/swiftui/view/presentationcornerradius(_:)

**UIKit, AppKit, Core Animation**

- https://developer.apple.com/documentation/uikit/uicornerconfiguration-swift.struct
- https://developer.apple.com/documentation/uikit/uicornerconfiguration-swift.struct/corners(radius:)
- https://developer.apple.com/documentation/uikit/uiview/cornerconfiguration-7l0ja
- https://developer.apple.com/documentation/uikit/uicornerradius-swift.struct
- https://developer.apple.com/documentation/uikit/uicornerradius-swift.struct/containerconcentric(minimum:)
- https://developer.apple.com/documentation/uikit/uicornercurve
- https://developer.apple.com/documentation/uikit/uiscreen (checked for a display corner radius property; there is none)
- https://developer.apple.com/documentation/appkit/nsviewcornerconfiguration
- https://developer.apple.com/documentation/quartzcore/calayer/cornercurve
- https://developer.apple.com/documentation/quartzcore/calayercornercurve

**Design guidance**

- https://developer.apple.com/videos/play/wwdc2025/356/ (Get to know the new design system)
- https://developer.apple.com/videos/play/wwdc2025/220/ (Say hello to the new look of app icons)
- https://developer.apple.com/videos/play/tech-talks/111461/ (Prepare your app for iPhone Duo)
- https://developer.apple.com/design/human-interface-guidelines/live-activities
- https://developer.apple.com/design/human-interface-guidelines/widgets
- https://developer.apple.com/design/human-interface-guidelines/app-icons
- https://developer.apple.com/design/human-interface-guidelines/layout (checked; contains no corner or concentricity guidance)

**Forums**

- https://developer.apple.com/forums/thread/794685 (Apple DTS on `ConcentricRectangle` versus `ContainerRelativeShape`)

**Not fetched, reported from search summaries only, treat as unverified**

- MDN `corner-shape`, `<corner-shape-value>` and `superellipse()`
- CSS Borders and Box Decorations Level 4
- Chrome 139 release notes and the Chrome Status entry for corner shaping
- WebKit release notes for Safari Technology Preview 251
