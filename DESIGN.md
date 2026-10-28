# Jarvaids client: design record of the UI/UX overhaul

**Current interaction update, 20 October:** Luuk requested automatic whole-wall
reading, immediate application of input and commands, cleaner result cards and
naturally growing notes. This supersedes acceptance and box-marking requirements
in the historical audit below. See [the automatic workspace design](docs/superpowers/specs/2026-10-20-automatic-workspace.md).

This file is the design record of the overhaul of the Jarvaids browser client on branch `ui-redesign`. Section 0 is an audit of the client as it stands before any redesign, taken from the code with file:line citations, so that later phases can change the screens without breaking what the code, the tests and the CI audit depend on. Later phases add their own sections below it. Statements are facts read from the files unless marked **inferred**; line numbers refer to the tree at commit `bd81d56` plus the untracked files noted in 0.1.

## 0. Audit

### 0.1 Files the client is made of

There is no build step. `index.html` loads two stylesheets and one ES module; every other module is reached by `import`.

| File | Size | Owns | Depends on it |
|---|---|---|---|
| `app/client/index.html` | 309 lines, 18406 B | All static markup: session bar (25-51), attention banner (55-59), setup screen with entry and agreement gate (62-122), workspace with three banners, board tools, board, list, composer and the three-tab rail (125-237), photo flow (240-275), export page (278-293), the one `<dialog>` (296-304). Inline SVG favicon (17). | `serve.py` serves it at `/client/`; every browser test loads `/client/` |
| `app/client/app.mjs` | 882 lines, 42607 B | The `app` state object (49-69), `attention` (76-82), `ERROR_WORDS`/`describe` (84-111), `send` and the control lane (115-154), heartbeat opt-in (160-164), `render` (230-309), the agreement gate (311-333), the list view (337-393), Place new notes (415-442), the composer (448-475), Undo (482-491), selection and grouping (495-535), listening (539-586), voice enrolment (588-617), export (621-647), end and delete (651-680), connecting and connection words (684-727), screen, rail, view, room and menu switching (729-768), all event wiring (774-858), `splitJoinCode` (869-880) | `index.html:307`; `tests/canvas-objects-browser.mjs:209` imports its exported `renderList` |
| `app/client/board.mjs` | 826 lines, 39074 B | Pure `boardModel` and the label helpers (72-162); the `Board` class: pan and zoom (188-306), selection (315-321), rendering notes, lane, hulls and canvas objects (325-734), drag and group membership by drop (738-825) | `app.mjs:36`, `review.mjs:12`, `transcript.mjs:3`; `tests/board-unit.mjs:11`, `tests/canvas-objects-unit.mjs:15`, `tests/canvas-objects-browser.mjs:93` |
| `app/client/canvas-objects.mjs` | 237 lines, 11267 B | Pure, DOM-free model of the five canvas kinds: `canvasObject` (41-52), tones (26, 54-56), default sizes (31-35), boxes (62-71), arrow geometry (78-150), stroke paths (156-190), list labels (194-237) | `board.mjs:52`, `app.mjs:37`, `review.mjs:13`; `tests/canvas-objects-unit.mjs:13` |
| `app/client/composer.mjs` | 49 lines, 2560 B | "Add and accept": `source.text` then `proposal.review` (19-32) and the banner text for each outcome (38-49) | `app.mjs:38`; `tests/canvas-objects-unit.mjs:16` |
| `app/client/review.mjs` | 309 lines, 14982 B | The Review panel: job rows (94-124) and retry (128-147), the undo line (149-159), the proposal queue (161-256), canvas proposal rows (261-299), crop fetching (43-53), `JOB_WORDS` (15-27), `readingLabel` (306-309) | `app.mjs:39`; `photo.mjs:12` uses `jobReason`, `jobSize`, and `ctx.review.cropFor`/`confidence` |
| `app/client/people.mjs` | 139 lines, 6016 B | Agreement helpers `agreed`, `waitingFor`, `names` (12-24); person rows on the gate and in People (29-103); invitation and copy (114-136) | `app.mjs:40` |
| `app/client/photo.mjs` | 232 lines, 10814 B | The photo flow: choose, mark, send, follow the job (23-229); PNG re-encoding under 3.5 MiB and 3200 px (18, 132-148) | `app.mjs:41` |
| `app/client/transcript.mjs` | 87 lines, 4741 B | Transcript rows, the note above them, command badges and `#command-status` (7-87) | `app.mjs:33`; `tests/command-recognition-browser.mjs:36`, `tests/speaker-enrollment-browser.mjs:57` |
| `app/client/transcript-sentences.mjs` | 37 lines, 1707 B | Joins consecutive segments of one voice and capture into one displayed sentence (6-37) | `transcript.mjs:2`; `app/server/tests/transcript-sentences-unit.mjs:3` (not run in CI) |
| `app/client/speakers.mjs` | 47 lines, 2417 B | Four-second voice sample recording (3-33) and the enrolled list (35-47) | `app.mjs:34`, `people.mjs:10` |
| `app/client/client.css` | 347 lines, 22660 B | Layout only by its own rule (1-10): the `[hidden]` override (15), bar, entry, gate, workspace grid, board and note geometry, hulls, canvas object looks and the proposed canvas tones (159-186), list, review, transcript, invite, photo flow, dialog, the sub-1024px rules (339-345) | `index.html:12` |
| `app/design-system/spec/exemplars/_base.css` | 307 lines, 19429 B | A hand-flattened copy of `tokens.css` as plain custom properties (18-88), room and touch scaling (77-90), type roles (107-117), layout primitives, focus ring, glyphs and statuses (181-202), buttons (212-233), fields (236-245), canvas item looks (250-264), session bar, segmented control, tabs, banner, menu, dialog | `index.html:11`; the five exemplars in `spec/exemplars/*.html:7`; `app/server/demo-audio.html:8`; `deliverables/week4-midpoint/slides/index.html:7` |
| `app/design-system/tokens.css` | 282 lines, 14294 B | Source of truth: Tailwind v4 `@theme` with palette primitives and job-named semantics (52-274). Not loaded by the browser: `_base.css:6-9` says it is the flattened copy and is stale if they disagree | `spec/contrast-check.py:47` reads it; `_base.css` mirrors it by hand |
| `app/design-system/fonts/` | `archivo-variable-latin.woff2` 34928 B, `LICENSE-Archivo.txt` 4481 B | The one face, weights 400 to 700 | `_base.css:14` (`../../fonts/...`), `tokens.css:45` |
| `app/server/client.mjs` | 166 lines, 11233 B | Transport: `GenAIClient` (39-166), `RequestError`/`ApiError` (8-25), ids and tokens (2-7), media URL ownership capped at 16 (68-73) | `app.mjs:30`, `people.mjs:9`, `capture-audio.mjs:17`; `tests/canvas-objects-server-browser.mjs:19`; 18 mutants in `app/server/tests/client_mutation_check.py:5-22` |
| `app/server/session-sync.mjs` | 280 lines, 16548 B | `SessionConnection`: 1 s polling, deltas and resync, `boardOrder` (30-36), the control lane (214-245), heartbeat every 30 s (190-204), visibility and online suspension (98-111) | `app.mjs:31`; 21 mutants in `client_mutation_check.py:23-43` |
| `app/server/capture-audio.mjs` | 214 lines, 10622 B | Microphone at 16 kHz, energy VAD, chunks cut at 1 s silence or 6 s (23, 32), each sent as `source.audio` (173-186) | `app.mjs:32`, `speakers.mjs:1`, `wakeword.mjs:1` |
| `app/server/wakeword.mjs` | 106 lines, 4954 B | Optional wake-word detector stream and a chime | `app.mjs:35` |
| `app/server/voice-command-feedback.mjs` | 16 lines, 894 B | The four command feedback sentences | `transcript.mjs:1` |
| `app/client/serve.py` | 68 lines, 2676 B | Static server: serves `app/` (29, 56), not `app/client/`, so `/client/`, `/server/` and `/design-system/` resolve; prints `http://127.0.0.1:<port>/client/` (57); `.mjs` as `text/javascript` and `.woff2` MIME (33-35); `Cache-Control: no-store` (37-41); no request logging (43-44); refuses any bind but 127.0.0.1 (52-55); default port 5173 | All browser tests spawn it |

Served paths: the page is `/client/index.html`; it links `../design-system/spec/exemplars/_base.css` and imports `../server/*.mjs`, which is why the server root is `app/` (`serve.py:20-22`). **Inferred:** everything under `app/`, including the Python server source, is readable from the static server on 127.0.0.1.

Other files present: `app/client/package.json` (Playwright `^1.49.0` as the only devDependency), `app/client/node_modules/` (playwright, playwright-core), `app/client/.gitkeep`, `app/client/README.md`. An **untracked** `app/client/fonts/` (General Sans 400/500/600, JetBrains Mono, two licences, created 19 October 00:11) is referenced by no file; the audit's typeface check (0.7) refuses any `font-family` literal that would use it.

`app/client/README.md` has drifted from the code and should not be used as a spec: it describes an "Add" tab, a violet dashed stroke, a "Provisional" label, "Start capture" making the bar say Recording, Delete inside the export dialog, "No shapes, connectors", and 1024-sample audio blocks (the code uses 512, `capture-audio.mjs:167`).

### 0.2 Every element JavaScript binds to

`$` is `document.getElementById` (`app.mjs:45`). "Markup" is the `index.html` line; "made at" is where JavaScript creates the element.

**Ids in the markup.**

| Id | Markup | Bound at |
|---|---|---|
| `bar` | 25 | app 232, 673 |
| `bar-title` | 27 | app 244 |
| `session-status`, `state-glyph`, `state-word` | 28 | app 241, 242, 243 |
| `bar-members` | 30 | app 246, 835 |
| `listen-status` | 32 | app 560, 576 |
| `listen-timer` | 34 | app 584 |
| `bar-actions` | 36 | app 267 |
| `open-photo` | 37 | app 249; photo 220 |
| `listen` | 38 | app 248, 559, 575, 830 |
| `undo` | 39 | app 252, 831 |
| `stop-capture` | 40 | app 250, 828 |
| `session-menu-button` | 42 | app 767, 843 |
| `session-menu` | 43 | app 764 |
| `room-toggle` | 44 | app 758, 759, 846 |
| `open-export`, `end-session`, `delete-session` | 45, 46, 47 | app 255/847, 253/848, 254/849 |
| `attention` (+ `data-kind`) | 55 | app 77, 79 |
| `attention-glyph`, `attention-text`, `attention-dismiss` | 56, 57, 58 | app 80, 78, 795 |
| `page-head` | 63 | app 268, 676 |
| `start-join` | 72 | app 312, 675 |
| `join-name`, `join-invitation`, `join` | 75, 76, 78 | app 813, 808, 806 |
| `owner-name`, `session-title`, `retention`, `create` | 83, 84, 86, 92 | app 800, 801, 801, 797 |
| `base-url` | 97 | app 771 |
| `consent`, `consent-session`, `consent-text` | 103, 104, 105 | app 313/677, 314, 315 |
| `agree-line`, `agree-check`, `acknowledge` | 106, 107, 111 | app 318; 320/818/821; 319/320/818/819 |
| `agreed-note` | 112 | app 322, 323 |
| `consent-rows` | 115 | app 324 |
| `activate`, `activate-reason` | 117, 118 | app 327-329, 826; 330 |
| `screen-setup`, `screen-workspace`, `screen-photo`, `screen-export` | 62, 125, 240, 278 | app 731 as `` `screen-${id}` `` |
| `paused-banner`, `paused-reason`, `resume` | 126, 128, 129 | app 270, 272, 275-276/827 |
| `keepalive-banner`, `keep-alive` | 133, 136 | app 284, 829 |
| `ended-banner`, `ended-text` | 138, 140 | app 277, 278 |
| `zoom-out`, `zoom-level`, `zoom-in`, `zoom-fit` | 151-154 | app 789, 780, 788, 790 |
| `arrange` | 156 | app 305, 791 |
| `selection`, `selection-count` | 157, 158 | app 497, 502 |
| `group-label`, `propose-group`, `group-reason`, `ungroup`, `clear-selection` | 159-163 | app 516-519, 506/792, 507-508, 509/793, 794 |
| `board-empty` | 166 | app 302 |
| `board` | 167 | app 747, 775 (`new Board`) |
| `list-view` | 169 | app 363, 748 |
| `board-hint` | 170 | app 749 |
| `composer`, `note-text`, `add-note`, `add-accept` | 174-177 | app 837; 294/297/449; 294 (loop over ids); 294/296/838 |
| `queue-count` | 183 | app 287 |
| `rail-review`, `rail-transcript`, `rail-people` | 188, 197, 208 | app 739 as `` `rail-${id}` `` |
| `jobs`, `undo-line`, `queue`, `queue-empty` | 191-194 | review 95, 150, 164, 168 |
| `transcript-note`, `command-status`, `transcript` | 198-200 | transcript 18, 81, 11 |
| `wakeword-enabled`, `wakeword-status` | 203, 204 | app 542/834; 545-547/834 |
| `people-rows`, `invite-section` | 209, 211 | people 106, 108 |
| `make-invite`, `invite-created`, `invite-code`, `copy-invite` | 214-217 | app 840; people 120/125; people 124/129/132; app 841 |
| `speaker-name`, `speaker-enrol`, `speaker-cancel` | 224, 226, 227 | app 589/607; 291/595/615/832; 595/614/833 |
| `speaker-reason`, `speaker-status`, `speaker-list` | 229-231 | people 111; app 590-609; speakers 36 |
| `photo-step`, `close-photo` | 242, 243 | photo 38/62/160/178, 221 |
| `photo-choose`, `photo` (file input) | 246, 248 | photo 35/60, 26/32/222 |
| `photo-stage`, `photo-preview`, `regions`, `region-count` | 253, 254, 254, 256 | photo 36/61/158; 57/135; 33/58/69/119/127; 34/59/111/120/128 |
| `undo-region`, `clear-regions`, `send-photo` | 258-260 | photo 45/223, 46/224, 44/153/162/225 |
| `photo-reading`, `reading-status`, `reading-word`, `reading-text` | 265-267 | photo 37/159; 174 (`#reading-status .glyph`); 176; 179 |
| `found-list`, `found-review`, `reading-retry`, `photo-again` | 268, 270-272 | photo 184, 182/226, 183/227, 228 |
| `close-export`, `export-summary`, `include-unresolved`, `do-export`, `export-out`, `export-retention` | 281-292 | app 850, 624, 631, 851, 632/847, 627 |
| `confirm-dialog`, `confirm-title`, `confirm-text`, `confirm-detail`, `confirm-cancel`, `confirm-ok` | 296-302 | app 193-206 |

Ids in the markup that no script binds: `join-title`, `start-title`, `consent-title`, `photo-title`, `export-title`, `invite-title`, `voices-title` (targets of `aria-labelledby` only) and `activate-row`.

**Selectors, data attributes and classes in the static markup.**

| Selector | Markup | Bound at |
|---|---|---|
| `[data-rail]` (`review`, `transcript`, `people`), `aria-selected` | 183-185 | app 740, 786; tests |
| `[data-view]` (`canvas`, `list`), `aria-pressed` | 147-148 | app 746, 787; tests |
| `.zoom` | 150 | app 750 |
| `.menu-wrap` | 41 | app 844 (outside click closes the menu) |
| `.stage` (+ `data-wired`) | 254 | photo 68, 71-72 |
| `html[data-room]` | set on `<html>` | app 755-756, 846; `_base.css:89, 230, 233` |
| `.advanced summary` | 96 | tests only |

**Elements and classes created by script.**

| Selector | Made at | Read or tested at |
|---|---|---|
| `.world` (zero-sized, carries the pan and zoom transform) | board 172-174, 190 | tests: journey 300, canvas-objects-browser 117, 179 |
| `article.note.item` + `narrow`/`default`/`wide` + `item-accepted`/`item-provisional`/`item-pending` + `readonly` | board 383-387 | journey 126, 170-172, 181, 220, 258; canvas-objects-browser 162, 196 |
| `.item-selected` | board 319, 388 | none in tests |
| `.dragging` | board 768, 773 | none |
| `.note[data-id]`, `[data-kind]`, `[data-revision]` (position revision, sent as `expected_position_revision`), `[data-offset]` (display push), inline `left`/`top`/`transform` | board 346-347, 389-391, 559-560 | app 399 (`.proposal[data-id]`), app 433, board 234, 751, 786, 806; journey 232, 246; canvas-objects-browser 162 |
| `.badge.st-provisional` "Proposed" / `.badge.st-off` "Not yet reviewed" | board 395-403 | journey 222 |
| `.note-head`, `.swatch`, `.kind`, `.text`, `.meta` | board 405-427 | none |
| `.note-actions` with "Show details"/"Hide details" (`aria-expanded`, `aria-controls`, `data-focus-key`) and "Review" | board 429-453 | journey 176, 233-245; canvas-objects-browser 169, 175 |
| `.details` (`id="detail-<id>"`), `dl.facts`, `.swatch-line`, `figure.crop`, `img`, `.t-caption` | board 455-535 | board 550; journey 238, 240 |
| `[data-focus-key]` | board 439, 449 | board 329, 378 |
| `.lane-label.t-structure` "Not placed yet" | board 366-372 | board 217 |
| `section.hull` + `hull-accepted`/`hull-provisional` + `[data-id]`, `.hull-label` (+ Review button) | board 570-587 | board 217, 599; journey 265, 271-272, 290-292 |
| `.cobj.cobj-{section,shape,text}` + `cobj-proposed` or `tone-{ink,accent,category-1,category-2,category-3}` + `[data-id]`, `[data-kind]`; `shape-{rect,ellipse,diamond,line}` | board 605, 632-651 | board 217; canvas-objects-browser 107-109, 129-156, 185; canvas-objects-server-browser 96-110 |
| `.cobj-title`, `.cobj-label`, `.cobj-words.t-{body,title,heading}`, `svg.cobj-outline` with `.body` or `.rule` | board 643, 657-666, 703-710 | canvas-objects-browser 129, 135, 138, 144, 149, 156 |
| `.cobj-tag.st-provisional` (glyph, words, Review) | board 716-724 | canvas-objects-browser 152-157 |
| `svg.links`, `path.pen.weight-{fine,regular,bold}`, `g.arrow` with `path.arrow-line` and `path.arrow-head`, all `[data-id]` | board 604, 621, 679-683 | canvas-objects-browser 110-113, 139-143, 161 |
| `.cobj-float.cobj-float-{above,over,middle}`, `.arrow-label` | board 624, 688-693, 729-733 | none |
| `.list-row` with `.status`, `.t-body`, `.t-meta`, Review button; `section > h2.t-title` | app 345-357, 365-375 | canvas-objects-browser 219-220 |
| `article.proposal` + `provisional` + `focused` + `[data-id]`; `.origin`, `.evidence`, `.members`, `textarea[data-draft-for]`, `.row`, `.why` | review 173-252, 262-298 | app 399-401; review 166; journey 177-179, 224, 247, 256, 269 |
| `.job` with `.status`, `.word`, Try again, Dismiss | review 102-122 | none |
| `.person`, `.person-name`, `.role`, `.person-actions` | people 57-90 | none |
| `.jv-row.transcript-row`, `.transcript-badge`, `.command-provisional`, `.transcript-words`, `details.activation-correction`, `.command-feedback` | transcript 30-78 | journey 336; command-recognition 57-66, 81-86 |
| `.region` (with numbered `span`) | photo 78-80, 107-109 | photo 75; journey 208 |
| `#found-list li` with `img`, `p.t-body`, `p.t-meta` | photo 190-203 | none |
| Export links `a.btn.btn-secondary[download]` | app 640-645 | journey 357-358 |

`.gap-row` (`client.css:290`) and `.item-waiting`/`.item-failed` (`_base.css:262-263`) are styled but never applied.

**Selectors each test uses.** These are the hooks a redesign must keep or update with the test.

- `tests/journey.mjs`: `.advanced summary`, `#base-url`, `#create`, `#bar:not([hidden])`, `#consent:not([hidden])`, `#activate` (disabled), `#activate-reason` ("Waiting for Facilitator to agree"), `#acknowledge` (disabled), `#agree-check`, `#state-word` ("Session open", "Paused"), `#listen-status` (hidden while no microphone; `[hidden]` after stop), `#screen-workspace:not([hidden])`, `#note-text`, `#add-note`, `#queue-count` (exact count), `.note` by text with classes `item-pending`, `item-provisional`, `item-accepted`, the role button "Review" inside a note, `#rail-review:not([hidden]) .proposal.focused`, `.proposal.focused textarea`, `.proposal.focused .btn-primary`, `#open-photo`, `#screen-photo:not([hidden])`, `#photo`, `#photo-stage:not([hidden])`, `#photo-preview` (naturalWidth and box equal to `.stage` box within 1px), `#regions .region` (inline style), `#send-photo`, `#found-review:not([hidden])`, `#reading-word` ("Here is what we found"), `.badge` ("Proposed"), `[data-rail="review"]`, `[data-rail="people"]`, `.proposal .origin` (must match "fixture" and "no handwriting recognition"), `data-revision`, role buttons "Show details" and "Hide details" with `aria-expanded`, `.note.item-provisional .facts` ("Stand-in reading", "Confidence Not measured"), `.note.item-provisional .crop img`, `.note` inline `transform`, `.proposal .btn-quiet` (first quiet button is Reject), `.proposal .btn-primary` (first primary is Accept), `#zoom-fit`, shift-click on a note, `#selection:not([hidden])`, `#group-label`, `#propose-group`, `.hull.hull-provisional`, `.hull:not(.hull-provisional)`, `.hull .hull-label`, `#zoom-out`, `#zoom-level`, `.hull` box, `.world` inline transform, `#board` box, `#zoom-in`, `[data-view="list"]`, `[data-view="canvas"]`, `#list-view` ("Group · Onboarding"), `#add-accept` (visible), `#attention-text` ("Added and accepted"), note text "Accepted by Facilitator", `#note-text` value, `#listen`, `#transcript .jv-row`, `#transcript-note` ("Stand-in transcript"), `#make-invite`, `#invite-created:not([hidden])` (text matches `[0-9a-f]{32}\.\d+\.[A-Za-z0-9_-]{32,}`), `#session-menu-button`, `#open-export`, `#screen-export:not([hidden])`, `#do-export`, `#export-out a` (two, fetched), `#close-export`, `#keepalive-banner` (not visible), `#stop-capture`, `#paused-banner:not([hidden])`, `#attention` (read on failure), and a POST body matching `"session.heartbeat"`.
- `tests/canvas-objects-browser.mjs`: hides `#screen-setup`, shows `#screen-workspace`, replaces `#board` with a clone and builds `new Board(el, {send, review, attention, onSelection, crop, revoke})` from `/client/board.mjs`, uses `board.render`, `board.view.z`, `board.view.touched`; imports `renderList` from `/client/app.mjs`. Selectors: `.cobj-section`, `.cobj-shape`, `.cobj-text`, `.links`, `.links .pen`, `.links .arrow`, `.links .arrow[data-id]`, `.world` children order (`.cobj-section` before last `.cobj` before `.links` before first `.note`), `.cobj[data-id] .body`, `.cobj[data-id]` background and border, `.cobj-title`, `.cobj-words` (28px for heading), `.arrow[data-id] .arrow-line` (stroke, dasharray, fill, and the numbers in `d`), `.cobj[data-id] .rule`, `.cobj-tag` (text "Proposed", one `.glyph-provisional`, role button "Review"), `.cobj-label`, `.note[data-id]` (inline left/top, `data-offset`, offset size), "Show details"/"Hide details", `document.elementFromPoint` on an arrow and on a shape must return `#board`, `#list-view`, `.list-row` with `.status`. It compares computed colours to `rgb(17, 79, 162)` (accent) and `rgb(23, 24, 27)` (ink), and the bold pen width to `4px`.
- `tests/canvas-objects-server-browser.mjs`: `.advanced summary`, `#base-url`, `#join-name`, `#join-invitation`, `#join`, `#screen-workspace:not([hidden])`, `[data-id="<record id>"]` (first match) with and without class `cobj-proposed`, `[data-view="list"]`, `[data-view="canvas"]`, `#list-view` text.
- `tests/command-recognition-browser.mjs`: imports `renderTranscript` from `/client/transcript.mjs`; `#screen-setup`, `#screen-workspace`, `[data-rail="transcript"]`, `.command-provisional` (8), `.transcript-row` (13, then 1, then 0), `#transcript img` (0), `#command-status` (text, then hidden), `.activation-correction` and its `summary`, `.transcript-words`, `#transcript` text.
- `tests/speaker-enrollment-browser.mjs`: `.advanced summary`, `#base-url`, `#create`, `#agree-check`, `#acknowledge`, `#activate`, `[data-rail="people"]`, `#speaker-name`, `#speaker-enrol`, `#speaker-list`, `#speaker-cancel`, `#speaker-status` (exactly "Recording cancelled."), `[data-rail="transcript"]`, `#transcript`, `#transcript-note`.
- `tests/board-unit.mjs` and `tests/canvas-objects-unit.mjs` select nothing; they import `boardModel`, `machineMade`, `noteMeta`, `noteKind`, `widthStep`, `objectMeta` (board.mjs), every export listed at `canvas-objects-unit.mjs:13-14`, and `addAndAccept`, `addAndAcceptMessage` (composer.mjs). Those export names and their output strings are part of the contract.

### 0.3 Every UI state

**Screens.** `screen(name)` shows exactly one of `screen-setup`, `screen-workspace`, `screen-photo`, `screen-export` (`app.mjs:729-735`). The bar (`#bar`) shows whenever a snapshot exists and the session is not deleted (232); its actions (`#bar-actions`) are hidden on the setup screen (267). `render` moves a person to setup when they have not agreed and the session is not closed (262), and from setup to the workspace once they have agreed and the session has started at least once, meaning `active`, `paused` or `closed` (261-263).

| State | How to reach it | Rendered at |
|---|---|---|
| Entry (no session) | Page load | `index.html:62-99`; `page-head` and `start-join` visible |
| Not started (`draft`) | Start session; bar word "Not started", off glyph | `app.mjs:221-226`, 240-243; gate stays up |
| Agreement needed | Any member whose `consent_version` differs from `policy_version` (`people.mjs:12-14`) | Gate: tick box and Agree (`app.mjs:318-320`), "Who has agreed" rows (324) |
| Agreed, waiting for others | Agree while others have not | `#agreed-note` "You agreed at HH:MM." or "You agreed." (322-323); `#activate-reason` "Waiting for {names} to agree." (331) |
| Ready to start | Facilitator, everyone agreed | `#activate` enabled, "Everyone has agreed." (332); participant sees "The facilitator starts capture once everyone has agreed." |
| Open (`active`) | Start capture | Bar "Session open", accepted glyph; `#stop-capture` "Pause" shown (250); composer, photo and Listen enabled (248-249, 294) |
| Paused, no withdrawal | Pause by anyone; also lease expiry on the server | `#paused-banner` "Nothing new is being recorded. The canvas and review still work." (270-274); Resume for facilitators only, disabled while anyone has not agreed (275-276) |
| Paused by a withdrawal | Withdraw agreement (People) | Others: "Paused because {names} withdrew agreement. Capture can resume once everyone has agreed again." (272-273); the withdrawer is sent back to the gate (262), where a facilitator's button reads "Resume capture" (328) |
| Ended (`closed`) | Session menu, End session, confirm | `#ended-banner` "This session has ended. The canvas can still be read and exported until {date}." (277-279); Undo, End, invite, person actions and Place new notes hidden (252-253, `people.mjs:69, 108`, `app.mjs:305`) |
| Deleted by this device | Session menu, Delete session, confirm | Back to entry with `page-head` and `start-join`; banner "Deleted. The server keeps only a receipt that the session existed." (`app.mjs:667-679`) |
| Deleted elsewhere | Another facilitator deletes | Banner "This session was deleted. The server keeps only a receipt." (726); snapshot becomes null so the bar hides (232). **Inferred:** the workspace stays on screen with its last drawing, because `render` returns before redrawing (233) |
| Recording on this device | Listen | `#listen-status` "Recording" with `#listen-timer` MM:SS updated every second (`app.mjs:557-561`, 581-586); button reads "Stop listening"; rail switches to Transcript |
| Keep-alive prompt | Facilitator, session active, heartbeat off: after the tab was hidden or offline, after a heartbeat or sync failure, or after a control conflict or uncertainty (`app.mjs:281-284, 695-697, 718`) | `#keepalive-banner` "Capture will pause" with "Keep capture running" (`index.html:133-137`) |
| Session menu open | Session button | `#session-menu` (`app.mjs:763-768`); Room view for everyone, Export, End and Delete for facilitators (253-255) |
| Room view | Session menu, Room view | `html[data-room]`, label "Room view: on/off", board zoomed by 1.5 (`app.mjs:754-761`) |
| Confirmation | End, Delete, Remove, or an uncertain photo retry | `<dialog>`; Cancel focused, Escape cancels (`app.mjs:192-208`). Titles: "End this session?", "Delete this session?", "Remove {name}?", "Read this photograph again?" (non-danger, primary button) |

**Agreement per person** (`people.mjs:29-45`): "Agreed HH:MM" or "Agreed" (accepted glyph), "Withdrew HH:MM" (off glyph), "Not yet" (waiting glyph). Own row offers "Withdraw agreement" or "Agree again"; a facilitator sees "Make facilitator"/"Make participant" and "Remove" on others; none of these when closed (69-90). Roles shown: Facilitator, Participant, Viewer (63). The client never assigns Viewer and invitations are always `participant` (119).

**The attention banner.** One element, two kinds: `problem` (failed glyph, the default) and `note` (accepted glyph) (`app.mjs:76-82`, `client.css:43-45`). It stays until dismissed or replaced, and every successful `send` clears it (134). Every text it can show:

| Kind | Text | Source |
|---|---|---|
| note | "Added to the canvas, waiting for review. A person's own note still goes through review, so the record says who accepted it." | app 458 |
| note | "Added and accepted. The record names you as the person who accepted it." | composer 41 |
| problem | "Added to the canvas. The server may or may not have accepted it, so nothing was retried. Check Review before accepting it again." | composer 44-45 |
| problem | "Added to the canvas, but it could not be accepted: {reason} It is waiting for review." (reason may be "The server did not say which note it added.") | composer 47-48 |
| note | "Undid “{text, 60 chars}”. It is no longer in the record." | app 490 |
| note | "Name the group first, so the label says what it is about." | app 517 |
| note | "Group proposed. It is drawn dashed until a facilitator accepts it in Review." | app 521 |
| problem | "Finish or cancel the voice recording first." | app 541 |
| problem | "A {n} second piece of audio did not reach the server: {describe}" | app 554-555 |
| problem | "The browser was not allowed to use the microphone. Allow it in the address bar and try again." / "Could not start the microphone: {describe}" | app 564-566 |
| note | "Listening paused while a voice sample is recorded. Press Listen to continue." | app 592 |
| note | "Listening stopped because this tab was hidden. Press Listen to continue." | app 711 |
| note | "Deleted. The server keeps only a receipt that the session existed." | app 678 |
| note | "Hide the open details before moving notes. Details only change your screen, so a move made while they are open would save the wrong place." | board 776 |
| note | "You withdrew your agreement, so capture stopped for the room. Agree again to let it resume." | people 97 |
| note | "Invitation copied. Send it to one person." / "Copy the selected code, then send it to one person." | people 130, 134 |
| note | "Correction saved. A facilitator accepts it into the record." | review 245 |
| problem | "The photograph is no longer in the session." | review 130 |
| problem | "Mark at least one note on the photograph first." | photo 151 |
| problem | `CONNECTION_WORDS`: heartbeat_failed "Could not keep capture running from this screen. It pauses itself within five minutes unless kept running."; control_conflict "Someone changed the session at the same moment. Check what happened, then try again."; control_uncertain "The server may or may not have applied that. Nothing was retried automatically."; offline "You are offline. Nothing new arrives until the connection is back; capture on the server is unchanged."; sync_failed "Could not refresh from the server. It keeps trying; what you see may be out of date."; session_deleted (above) | app 720-727 |
| problem | "Connection problem: {code with spaces}." for any other signal, which from `session-sync.mjs` can be `client_revoked`, `client_expired`, `client_deleted`, `client_disposed` (59), `connection_stopped` (88), `heartbeat_superseded_by_pause` (267, 275), `control_reconciliation_abandoned` (260). `hidden` is silent; the two `*_heartbeat_requires_opt_in` codes clear the banner (697-698) | app 699 |
| problem | `describe(error)` for any failed command, create, join, export or photo send | app 139, 803, 815, 851; photo 216, 225 |

**Connection states** and what each does: polling every 1 s with exponential backoff to 30 s on failure (`session-sync.mjs:48, 180`); hidden tab and offline suspend polling, heartbeat and any control in flight (93-111) and the client also stops listening and aborts enrolment (`app.mjs:710-716`); coming back schedules a full read and asks for heartbeat opt-in again; sync failed keeps retrying; a control conflict (409) forces a refresh before the next control (237-240); an uncertain control is retained and blocks the next control with `control_uncertain` (218, 234-236). The client never calls `retryPendingControl` or `discardPendingControl`, so after an uncertain control **inferred:** controls stay blocked for the life of the page.

**`describe()`** (`app.mjs:95-111`): a `ConnectionError` wrapping an `ApiError` is described by its cause; then `ERROR_WORDS` by code: invalid_join_code, invitation_expired, invitation_consumed, invalid_invitation, policy_changed, session_closed, agreement_incomplete, unreadable_content (84-93); then any `ApiError` shows the server's own message, prefixed "Uncertain, so nothing was retried automatically: " when its outcome is unknown; then `RequestError`/`ConnectionError` say "The server may or may not have applied that. Nothing was retried automatically." when uncertain, else "Could not reach the server. Check the server address and the connection."; anything else shows its message. The server's English messages therefore reach the banner verbatim. `RequestError` carries its own messages (`client.mjs:10`), used only through `describe`'s last line.

**Photo flow** (`photo.mjs`). Choose (`#photo-choose`, step text "Take a photo, or choose one, of the sticky notes."); Mark (`#photo-stage`, "Mark each sticky note you want read.", a drag makes a numbered `.region`, boxes under 12px are discarded (99), Send reads "Read N notes" or "Send for reading", Undo last mark and Clear marks disabled at zero (42-47)); Sending (Send disabled, 153-162); Waiting ("Waiting to be read"); Reading ("Reading N notes"); Found ("Here is what we found", step "Everything found is on the canvas, proposed.", a list of crop, text or "Unreadable: type it in Review", confidence; Review them); Failed or Cancelled ("Reading failed" / "Reading cancelled", "{reason} The photograph is kept, so it can be read again.", Try again) (167-205). The reasons are `JOB_WORDS` (`review.mjs:15-27`): capture_stopped, deadline_exceeded and adapter_timeout ("It took longer than a minute."), adapter_failed, interrupted_unknown_outcome, policy_changed, source_changed, permission_changed, record_capacity, storage_capacity, user_cancelled, and the fallback "It could not be read." The photo flow's Try again does not handle `uncertain_retry_requires_acknowledgement`; only the Review panel's does (`review.mjs:133-145`). Leaving with "Back to the canvas" keeps the job running; the Review panel then tracks it.

**Review queue** (`review.mjs`). Empty: "Nothing waiting for review. Photograph the wall or add a note to start." Job rows above the queue for every job not succeeded and not dismissed: "Waiting to read N notes", "Reading N notes", "Reading failed"/"Reading cancelled" with reason, Try again and Dismiss. Undo line "Accepted “…”." with Undo, shown while the last acceptance is on top of the undo stack and no other command has run since (`app.mjs:135`, `review.mjs:149-159`). Proposal rows, in snapshot order:

| Row | Status word | Origin line | Evidence |
|---|---|---|---|
| Model or fixture reading | "Proposed" (provisional) | "Read by {Provider}, not yet accepted", or "Stand-in reading (fixture): no handwriting recognition ran. Not yet accepted" | Crop: "Loading the part of the photograph…", then the image with "{Note · from photograph}. Confidence N%/not measured", or "The photograph is only visible to the person who took it and to facilitators." |
| Unreadable reading | "Unreadable: type what the note says" (failed) | as above | as above |
| Typed note | "Not yet reviewed" (off) | "Typed by {name}, not yet accepted" | none |
| Proposed group | "Proposed" | "Group proposed by {name}, not yet accepted" | member texts, or "A note that is no longer on the canvas"; textarea is the group name; "Accept group" |
| Canvas proposal | "Proposed" | "Proposed by {Provider or name}, not yet accepted" | the list label, e.g. "Shape · Run a test"; no textarea |
| Any, stale | as above | suffix ". Its source changed since this was made" | as above |

A facilitator gets Accept (disabled while the text is empty) and Reject; an edited text is sent as `proposal.edit` before the accept (213-229). Anyone else gets "Save correction" and "A facilitator accepts or rejects. Your correction is kept.", or for a canvas proposal only "A facilitator accepts or rejects." Drafts survive re-rendering while the proposal's revision is unchanged (204-210). Review from a note, hull, tag or list row marks the row `.focused` and focuses its textarea (`app.mjs:395-402`). `#queue-count` counts every open proposal, including groups and canvas proposals (286-287).

**Notes on the canvas** (`board.mjs:382-464`). Accepted item: tonal fill, no badge, meta "Accepted by {name}". Model or fixture proposal: dashed accent line, "Proposed" badge, meta "Read by {Provider}, needs review" or "Stand-in reading, needs review". Typed proposal: solid line, "Not yet reviewed" badge, "Typed by {name}, not yet reviewed". Stale adds ". Its source changed". The kind line is "Note · from photograph", "Note · retyped from photograph" or "Note · typed", with a paper colour swatch when known. Selected: `item-selected` outline. Dragging: `dragging`, raised. Details open: provenance facts (Read by / Written by, Text retyped, Confidence, Paper colour, Accepted by, Group, Position "Not placed yet", "Placed by a person", "Placed by the layout") and the crop ("Loading the photograph crop…", the image, or "The photograph is not available to you: only its uploader and facilitators can see it."); notes below and overlapping horizontally are pushed down locally by the details' height plus 8px (548-562). An open or pushed note refuses to move and says why (751-778). In a group: inside a hull, no per-note group label. Proposed group: dashed hull labelled "Proposed group · {name}" with Review. Not placed: stacked in the lane with the label "Not placed yet". Read only on a coarse pointer: a tap selects, nothing drags (739-745).

**Canvas objects** (`board.mjs:595-697`, `client.css:151-247`). Section: tonal area with its title above ("Untitled section" when empty), drawn under everything; proposed: dashed outline and "Proposed section · {title}" tag. Shape (rect, ellipse, diamond, line): outline drawn in SVG at its own size, tonal fill in its tone, words centred (a line's words go under it); proposed: no fill, 1px dashed accent outline, "Proposed" tag. Text: the type alone in body, title or heading size, no fill; proposed: dashed border. Stroke: a smoothed path on the shared SVG layer, weight fine 1px, regular 2px, bold 4px, in its tone; proposed: dashed and a tag above. Arrow: edge to edge between displayed boxes, open chevron head, optional label on a canvas-coloured patch; not drawn when an end is gone, points from a record to itself, or the geometry overlaps (`canvas-objects.mjs:105-142`); an arrow to an accepted proposal follows the new item (`aliasAccepted`, 122-128); proposed: dashed line, solid head, tag above the middle. An object without a position joins the lane under the notes. Section `form` values other than `free` draw identically. There are no drawing tools, selection or editing of objects in the client.

**List view** (`app.mjs:361-393`): sections "Group · {name}", "Proposed group · {name}", "Not in a group", "Shapes, sections and drawings"; each row has a status (Accepted, Proposed, Not yet reviewed), the text or object label, the meta line, and Review for proposals; empty: "Nothing on the canvas yet. Photograph the wall or add a note." List is the default view on a coarse pointer (56).

**Empty canvas**: `#board-empty` in canvas view when there are no notes and no objects (300-302).

**Board tools**: Canvas/List segmented control; zoom out, level (25% to 200%), zoom in, Fit (fit never zooms past 100%, `board.mjs:216-229`); "Place new notes" when accepted notes are unplaced, canvas view, not closed (`app.mjs:305`); the selection bar "{n} selected", group name field, "Propose group" (enabled only for two or more accepted notes in no group), the reason "Select two or more accepted notes that are not in a group yet.", "Remove from group" when any selected note is grouped, Clear (495-510).

**Composer**: enabled only while active, placeholder "Type what someone said or wrote" or "Notes can be added while capture runs"; Add note for everyone, "Add and accept" for facilitators; one add at a time (`app.adding`, 448-475).

**Transcript** (`transcript.mjs`). Note above the rows, in priority order: "Some audio could not be transcribed because of a technical error. Listening continues."; "Recognised speech will appear here while listening." (no rows; the markup's "Press Listen in the bar to transcribe the room." shows only before the first render); "Stand-in transcript: no speech recognition ran. Speakers are whoever's device sent the audio."; "Enrolled voices are matched automatically. Uncertain matches appear as Unknown speaker."; "Speakers are whoever's device sent the audio, not voice recognition." Each row: time HH:MM:SS, speaker (matched name with a tooltip "Automatic voice match; may be incorrect.", "Unknown speaker", or the member name), a badge ("Transcript", "Provisional command" with a dashed ring, "Request unfinished", "Command not recognised"), the words, an optional "Activation phrase corrected" disclosure showing what the recogniser originally heard (69), and the command feedback line. `#command-status` repeats the latest feedback and hides when there is none. Feedback strings (`voice-command-feedback.mjs:7-16`): "Provisional command: {label} requested. Generation is not connected yet." for summary, visualisation, comparison, voting list, suggestions, to-do list, requirements or wishes list, agenda or schedule; "Request unfinished. Continue straight away; two transcript lines can form one request."; "Hey Jarvaids recognised. Say your command straight away; two transcript lines can form one request."; "Command not recognised. Try rephrasing: {command}". Synthetic segments never show a command. Only `final` segments with text are shown, so `gap` segments are invisible. Test tools: the wake-word checkbox and status "Wake-word detector: {loading, waiting, detected, off, unavailable, interrupted}", "Wake-word unavailable: {message}. Transcript recognition still works.", "Hey Jarvaids detected" with a chime, "Press Listen to apply detector settings." (`app.mjs:542-549, 834`).

**People panel**: rows as above; Invite someone for facilitators while not closed (`people.mjs:108`): "Create an invitation", then a code `sessionId.policyVersion.invitation` with Copy, shown only after the server accepted it; on failure the code area hides and the banner explains (114-126). Voices: name field; "Record a four-second sample" enabled only while active and not already recording; "Cancel recording" while recording; reason "Voices can be recorded while capture is running."; status lines "Enter the speaker's name first.", "Recording for four seconds. Say the introduction now.", "Storing the voice sample…", "Test profile stored. This server has no real speaker identifier enabled.", "{name} enrolled. Add another speaker, or press Listen to continue.", "Upload cancelled; the profile may have been stored. Check the enrolled list before trying again.", "Recording cancelled.", or `describe`; list "No voices enrolled yet. Audio is attributed to this microphone's participant." or "{name} · Test profile, no real voice matching" / "{name} · Voice profile enrolled". **Inferred:** if the tab is hidden or goes offline after the four seconds, the status stays on "Recording for four seconds…" because that path returns without a message (`app.mjs:599`).

**Export page** (facilitators only, from the menu): summary "{n} accepted notes. {m} items were never reviewed: leave them out, or include them marked as proposed." or "{n} accepted notes, and nothing left unreviewed."; the include checkbox; Create export; two download links "Download JSON" and "Download Markdown" named after the session title; retention line (`app.mjs:621-647`). The output is cleared each time the page is opened (847).

**Phone width and touch.** Below 1024px the workspace is one column with the rail above the board (`client.css:343`), the board is 56vh with a 320px minimum (108), the board hint is hidden, the bar's identity and actions each take a full row and the photo button stretches (339-345), and the entry, list rows and photo stage stack. A coarse pointer, read once at load (`app.mjs:47`, `board.mjs:182`), gives 44px targets, 44px small buttons and 16px field text (`_base.css:90, 232, 242`), List as the default view, and a read-only board (pan and pinch still work). **Inferred from `client.mjs:44` and `app.mjs:799, 809`:** the client never passes `allowLan`, so it can only reach a server on `localhost` or `127.0.0.1`; a phone cannot use it against a laptop's server today, and phone width is tested only as a viewport.

**Several people.** A second device joins with the one-string code (`app.mjs:806-816`, `splitJoinCode` 869-879); joining records the joiner's agreement at the current policy version (`service.py:462-463`), so a joiner lands in the workspace if capture has started and on the gate otherwise. At most eight members (`service.py:459`). Every screen polls each second, so another person's change appears within about a poll. Facilitator-only controls: Start and Resume, Add and accept, Accept and Reject, Undo, End, Delete, Export, invitations, role and removal, and the heartbeat. Crops are visible only to the photograph's uploader and to facilitators.

**Long and many notes.** Width steps: up to 24 characters narrow 160px, up to 90 default 224px, longer wide 288px (`board.mjs:72-75`, `client.css:117-119`); text wraps anywhere and is never cut. The lane stacks unplaced notes by measured height with 24px gaps (`board.mjs:356-358`), 336px left of the leftmost placed object. Place new notes lays columns 352px apart by group or source photograph, 320px right of the rightmost note, in commands of 50 placements (`app.mjs:421-440`). Limits from the server: 1 to 60 regions per photograph, 1 to 60 placements per `item.place`, 1 to 60 refs per proposal, 60 section members, 24 cluster members, 5 queued or running jobs per session (`service.py:901`), 1000 records; the client's cache also refuses more than 1000 records or 16 MiB (`session-sync.mjs:49`). **Inferred:** media URLs are capped at 16 per client (`client.mjs:70`) and the Review crops (`review.mjs:50`) and export links (`app.mjs:642`) are never revoked, so after about 16 crops later ones fail and show the permission caption, which is misleading.

### 0.4 The command and data surface

Every command goes through `send` (`app.mjs:119-142`), which routes the six control operations through `SessionConnection.submitControl` (waiting up to 20 times 100ms on `control_busy`), clears the banner on success, and refreshes from the connection's cached snapshot. Audio chunks bypass `send`.

| Operation | Payload as sent | Sent at |
|---|---|---|
| `consent.acknowledge` | `{policy_version}` | app 820; people 75 |
| `session.activate` | `{policy_version, expected_session_revision}` | app 824 |
| `session.pause` (control) | `{}` | app 828 |
| `session.close` (control) | `{expected_session_revision}` | app 659 |
| `session.heartbeat` (control) | `{}`, every 30 s once enabled | session-sync 200 |
| `consent.withdraw` (control) | `{}` | people 96 |
| `participant.invite` | `{invitation, expected_roster_revision, role: "participant"}` | people 118 |
| `participant.role` | `{actor_id, role, expected_roster_revision}` | people 82 |
| `participant.remove` (control) | `{actor_id, expected_roster_revision}` | people 87 |
| `source.text` | `{text}` | app 455; composer 21 |
| `source.image` | `{mime: "image/png", base64, regions: [{id: "region_001", box: [x, y, w, h]}]}` | photo 155 |
| `source.audio` | `{mime: "audio/pcm16", base64, ended_reason, capture_id, captured_at_ms}`, 45 s timeout | capture-audio 173-186 |
| `extraction.queue` | `{source_id, expected_revision}`, plus `retry_of`, `acknowledge_uncertain_cost: true` on a confirmed retry | photo 156, 213; review 132, 143 |
| `proposal.edit` | `{proposal_id, expected_revision, text, refs}` | review 217, 243 |
| `proposal.review` | `{proposal_id, expected_revision, decision: "accept" or "reject"}` | composer 26; review 220, 232, 281, 289 |
| `proposal.create` | `{proposal_kind: "relationship", form: "cluster", text, refs}` | app 518 |
| `cluster.membership` | `{cluster_id, expected_revision, add}` or `{..., remove}` | app 532; board 819, 823 |
| `item.place` | `{placements: [{id, x, y, expected_position_revision}]}`; `origin: "machine"` from Place new notes | board 785; app 439 |
| `item.undo` | `{item_id, expected_revision, restore_revision: 0}` | app 487 |
| `speaker.enroll` | `{name, mime: "audio/pcm16", base64, ended_reason: "silence"}`, 45 s timeout | app 602 |
| `export.create` | `{include_unresolved}` | app 631 |

Not used by the client: `canvas.create`, `canvas.update`, `canvas.remove`, `invitation.revoke`, `job.cancel`, `source.correct`, `source.regions`, `item.edit`, and `w`/`h` on placements.

`GenAIClient` methods used: `create` (app 800), `join` (812), `intent` and `submit` (129-131, through the control lane in session-sync 221-228), `crop` (review 49; the board's hook at app 781), `createMediaUrl` (review 50, app 642, 781), `revokeMediaUrl` (app 782), `export` (637), `delete` (669), `onState` (session-sync 58, wakeword 8), `wakewordStart`/`wakewordBatch`/`wakewordStop` (wakeword 19, 51, 79); `snapshot` and `delta` only inside `SessionConnection` (125, 130). `media`, `exportSnapshot`, `events`, `record`, `readiness` and `diagnostics` are not used.

**Snapshot fields read.** Top level: `session`, `actor_id`, `members`, `records`, `board_order` (recomputed client side, `session-sync.mjs:159`), `next_control_sequence` (`app.mjs:169`). `session`: `id`, `title`, `state` (`draft`, `active`, `paused`, `closed`; `deleted` arrives as a receipt), `expires`, `policy_version`, `revision`, `roster_revision`. Members: `id`, `name`, `role`, `consent_version`, `agreed_at`, `withdrawn_at`. Records: `id`, `kind`, `revision`, `position` `{x, y, w, h, revision, hand_placed, placed_at}`, `data`, by kind:

- `item`: `item_kind` (`content`, `relationship` with `form: "cluster"`, `shape`, `text`, `arrow`, `section`, `stroke`), `status`, `text`, `refs`, `origin`, `author_id`, `accepted_by`, `last_editor`, `made_by_hand`, `proposal_id`, `region_id`, `reading_status`, `confidence`, `colour {hex, source}`, `model`, `provider`, `synthetic`, and each canvas kind's own fields.
- `proposal`: `proposal_kind` (`content`, `relationship`, `canvas`), `status` (`needs_review`, `stale` are open), `form`, `text`, `refs`, `origin` (`human`, `fixture`, `model`), `author_id`, `provider`, `model`, `synthetic`, `region_id`, `reading_status` (`unreadable`, `human_transcribed`), `confidence`, `colour`, `canvas_kind`, `canvas_data`.
- `job`: `status` (`queued`, `running`, `succeeded`, `failed`, `cancelled`), `error`, `refs`, `created_at`, `proposal_ids`.
- source records (image): `id`, `revision`, `data.regions` (count only).
- `transcript_segment`: `status`, `text`, `created_at`, `captured_at_ms`, `duration_ms`, `capture_id`, `capture_revision`, `attribution` (`voice_identified`, `unidentified`, otherwise per device), `speaker_name`, `speaker_actor_id`, `speaker_profile_id`, `provenance.synthetic`, `failure_reason`, `voice_command {status, intent, command}`, `activation_correction {corrected, text}`.
- `speaker_profile`: `data.name`, `data.provenance.synthetic`.

Command results read: `source.image` and `extraction.queue` return records (`id`, `revision`); `source.text` returns `{proposal}`; `proposal.review` returns `{item}`; `proposal.edit` returns the proposal; `speaker.enroll` returns `{profile}`; `export.create` returns the export record's `id`.

**Added on this branch** (`docs/specs/2026-10-18-canvas-object-model.md`, `app/server/API.md:118-155`): five record kinds `shape`, `text`, `arrow`, `section`, `stroke` as items (by hand or accepted) or `proposal_kind: "canvas"` proposals; `tone` from `ink`, `accent`, `category-1`, `category-2`, `category-3`; positions gain nullable `w`/`h` (schema 6), required for shape, text and section, refused for notes and clusters; commands `canvas.create {kind, data, x, y, w?, h?}`, `canvas.update {item_id, expected_revision, data}`, `canvas.remove {item_id, expected_revision}`, not gated on an active session and refused once closed; `proposal.create` with `canvas_kind`, `canvas_data`, `positions`. The client draws all of this but creates none of it except through the facilitator's Add and accept. Drawing tools, selection handles, resizing, cursors and presence are named as later sub-projects (spec 104-109).

### 0.5 What persists where

`localStorage`: one key, `jarvaids-room` (`"1"` or `""`), read at `app.mjs:854` and written at 760, both inside try/catch. Nothing else is stored in the browser; credentials live in private fields of `GenAIClient` (`client.mjs:40`).

In memory, `app` (`app.mjs:49-69`): `client`, `connection`, `snapshot`, `screen`, `rail`, `view`, `photo` `{file, dataUrl, regions}`, `photoJob`, `controlSequence`, `drafts` (proposal id to `{revision, text}`), `crops` (`id:revision` to blob URL, `null` while loading, `false` if refused), `dismissedJobs`, `undoStack`, `lastAccepted`, `focusProposal`, `mic`, `listenStarted`, `board`; added later at run time: `heartbeat`, `wantHeartbeat` (283, 825), `adding` (451). Module level: `enrolmentAbort`, `wakeController`, `wakeChime` (43-44). The `Board` instance: `view {x, y, z, touched}`, `expanded`, `selected`, `snapshot`, `busy`, `dirty`, `cropUrls`, `readonly`, `linkBounds` (`board.mjs:175-182, 596`). `SessionConnection` holds the cached snapshot, cursor, control sequence and any pending uncertain control.

Lost on reload: the session itself for this device, because the credential is gone and the server has no lost-credential route (`AGENTS.md`, backend boundaries); a facilitator who reloads cannot return, and a participant needs a new invitation. Also lost: correction drafts, the undo stack, dismissed job rows, the photo and its marks, pan, zoom, open details, selection, the chosen view and tab, and the microphone. Kept: room view.

### 0.6 Tests

| Test | Covers | Servers and ports |
|---|---|---|
| `tests/board-unit.mjs` (81 lines) | What the board holds, groups, the provisional rule, meta lines, note kinds, width steps | none |
| `tests/canvas-objects-unit.mjs` (272 lines) | Which records are canvas objects, tones, boxes, arrow geometry, strokes, list labels, `objectMeta`, Add and accept outcomes, `aliasAccepted` | none |
| `tests/journey.mjs` (396 lines) | 18 steps of the real workspace through the real server, listed in 0.2; viewport 1440x900 then 400x860; fake microphone; zero console errors and failed requests | static 5177, API 3077 with a temporary data dir; skips if Playwright is missing |
| `tests/canvas-objects-browser.mjs` (238 lines) | The five kinds drawn from a fixture snapshot, their looks, edge-to-edge arrows that follow open details, pass-through of presses, the list view; at 1440 and 400px | static 5191 only; screenshots to `.local/canvas-ui/` |
| `tests/canvas-objects-server-browser.mjs` (128 lines) | Node creates each kind through the server as facilitator; a browser joins as participant and must draw them; accepting a canvas proposal keeps the arrow attached | static 5181, API 3081 |
| `tests/command-recognition-browser.mjs` (96 lines) | Command badges and feedback, fixture exclusion, text safety, sentence joining, silence; at 1440 and 400px | static 5188 only; screenshots to `.local/command-ui/` |
| `tests/speaker-enrollment-browser.mjs` (75 lines) | Enrolment, cancellation, speaker labels; at 1440 and 400px | API 3095, static 5189; data and screenshots to `.local/speaker-browser-test/<time>/`, never removed |

Environment variables: `CHROMIUM_PATH` (all browser tests), `SCREENSHOTS` (journey, server-browser), `CANVAS_SCREENSHOT`, `JARVAIDS_TEST_PYTHON` (the three that use it; journey and server-browser call `python3` directly), `VERBOSE` (journey).

Running on this machine, as done for this audit on 19 October 2026:

```sh
eval "$(fnm env --shell bash)"; fnm use 24        # before any cd: see below
export PATH="/c/Users/Pieter/dev/GenAI/.venv/Scripts:$PATH"   # python3 is 3.14.0 here
cd /c/Users/Pieter/dev/GenAI/app/client
node --test tests/board-unit.mjs tests/canvas-objects-unit.mjs
node tests/journey.mjs
node tests/canvas-objects-browser.mjs
node tests/canvas-objects-server-browser.mjs
node tests/command-recognition-browser.mjs
node tests/speaker-enrollment-browser.mjs
```

`~/.bashrc` installs fnm's `--use-on-cd` hook, which errors in the tool's shell if `cd` runs before `fnm env` has been evaluated, so the order above matters. Results: 33 unit tests pass; the four non-journey browser tests pass; the journey prints `ok` for all 18 steps but exits 1, because `rmSync` of its temporary data dir (`journey.mjs:49`) gets EPERM on Windows while the API child still holds the database after SIGTERM, and seven `jarvaids-journey-*` folders were left in `%TEMP%`. CI runs on Ubuntu with Python 3.12 and Node 24 (`.github/workflows/verify.yml:196-235`) and runs all seven, then `git diff --exit-code`.

### 0.7 Constraints the code imposes on a redesign

- **One breakpoint, 1024px.** Every width query is `min-width: 1024px` or `max-width: 1023px` (`client.css:50, 73, 76, 108, 254, 310, 339`; `_base.css:121, 142, 145, 150, 271`), and the audit refuses any other width.
- **`[hidden]` must win.** `client.css:15` sets `[hidden] { display: none !important; }` because design-system components set `display: flex`. All showing and hiding goes through the `hidden` property (`app.mjs:46`) and the tests wait on `:not([hidden])` and `[hidden]`.
- **Room mode** is `data-room` on `<html>`: `--scale: 1.5` and `--target: 44px` (`_base.css:89`), larger buttons (230, 233), and the board resets its own type sizes so that room view zooms the board by 1.5 instead (`client.css:28-30`, `app.mjs:757`).
- **Segmented control and tabs.** The tests click `[data-view="canvas"|"list"]` and `[data-rail="review"|"transcript"|"people"]`; the code sets `aria-pressed` and `aria-selected` on those attributes and shows `rail-{name}` panels by id (`app.mjs:737-752`). `_base.css:274-287` styles them from the same attributes.
- **First-button selectors.** The journey accepts with `.proposal .btn-primary` and rejects with `.proposal .btn-quiet`, so a proposal row's first primary must be Accept and its first quiet button Reject.
- **The lane** for unplaced notes is derived on every render and never saved (`board.mjs:337-373`); Place new notes measures note heights from it (`app.mjs:433`).
- **Note widths** are three classes at 160, 224 and 288px chosen by text length; `LANE_WIDTH` (288 + 48) and Place new notes' 288 + 64 column step assume the widest (`board.mjs:57`, `app.mjs:436`). `DEFAULT_SIZE` for unsized objects reuses those steps (`canvas-objects.mjs:31-35`).
- **One SVG layer** (`svg.links`, 1x1 with visible overflow and `max-width: none`, `client.css:223`) holds every arrow and stroke and must stay under the notes in DOM order; the browser test checks section, shapes, links, then notes.
- **Pointer handling.** The board root pans and pinches on any press not on `.note, button, a, input, textarea` (`board.mjs:244`), captures the pointer, and defers re-renders while busy (179-180, 327). Wheel is always prevented: plain wheel pans, Ctrl or Cmd wheel zooms (286-293). Keys work only when the board itself has focus (295-305). A note stops propagation and captures its own pointer; presses on its buttons, links and images are left alone (742, 749). Hulls, `.cobj`, `.links` and `.cobj-float` take no pointer events; `.hull-label` and `.cobj-tag` do, for their Review buttons (`client.css:139, 145, 188-189, 223, 239`). `.world` is zero-sized, which is why `elementFromPoint` over an arrow or shape returns `#board`; the canvas test depends on this. The board and notes set `touch-action: none` (106, 113). The photo stage captures the pointer for marking and must hug the image exactly, since boxes are normalised to it (`client.css:304-308`; journey asserts within 1px).
- **The design audit** (`app/design-system/spec/audit.sh`) runs in CI with no arguments, so it checks `app/client` and `app/server`, every `.css`, `.html`, `.mjs`, `.js`, `.ts`, `.tsx`, `.jsx`, `.vue`, `.svelte`, excluding `node_modules` and the design-system folder (53-54). Its 13 checks: contrast of every declared token pair (78-83); no raw hex colour `#` plus 3 to 8 hex digits not followed by a word character or hyphen, which also catches an id selector such as `#feed` (89); `border-radius` only 2px, 4px, 999px or `var(` (90); `font-family` only `var(` or `inherit` (91); width media queries only 1023px or 1024px (92); border and outline widths only `var(`, 0, 1px or 2px (93); no Tailwind palette classes (94); `box-shadow` only `none` or an elevation token (99); the words toast, Toast, spinner or Spinner anywhere, comments included (100); no CDN or network font URL (101); no ✓ ✔ ✕ ✖ × ▾ ▴ ▸ ◂ → ← alone between tags (102); and on any line containing "provisional", no `opacity` or `ink-muted` within 80 characters, and no non-transparent `background` (109-110). It passed clean on 19 October 2026. The audit does not see `client.css`'s proposed canvas tones, which are `color-mix` of tokens and absent from `contrast-check.py` (`client.css:159-181`).
- **Mutation catalogue.** `client_mutation_check.py` mutates exact strings in `app/server/client.mjs` and `session-sync.mjs` (5-43), so editing those lines breaks a named guard; it mutates nothing in `app/client`.
- **Shared stylesheet.** Changing `_base.css` changes the five exemplars, the audio demo and the week 4 slides as well (0.1), and it must stay a faithful copy of `tokens.css`.

## 1. Concept

Everything below is decided. Later phases build it; they do not reopen it.

### 1.1 The three signature moves

What a person would describe to a colleague after one session. Each grows from one of the product's four materials: evidence, record, voice, time.

1. **A note can be asked where it came from, and points.** Every proposed note arrives with the photograph crop it was read from, and the crop stays with it. Selecting any note draws thin threads from the note to its origins: the crop in the review rail, the transcript line it was quoted from, the person who accepted it in People. Evidence and record, made visible as lines on the page. No whiteboard can do this, because no whiteboard knows where a note came from.
2. **Accepting is the loudest thing on the screen.** Proposed notes sit slightly askew (at most 1.5 degrees, deterministic from the id) in `--yellow-soft` with a mono "proposed" marker. When a facilitator accepts one, it settles straight, fills with its colour, swells by 3 percent and back, and gains a mono stamp of who accepted it and when. Over a 90 minute workshop the canvas visibly becomes the record. The record, as motion.
3. **Time runs along the bottom.** A session strip under the canvas holds the session's moments: each photograph, each accept, each recognised voice command, each quote pulled from the transcript. Dragging along it shows the wall as it was at that moment. Time, as a place you can go back to.

### 1.2 The tools (section 7)

**Required, built**

- **Drawing tool.** Freehand ink on the canvas: single weight, `--ink` at 85 percent, no pressure, smoothed into a quadratic curve through the midpoints of the points. A person's strokes are accepted at once and persist as `stroke` records through `canvas.create` (the canvas object model on this branch). Erase by stroke: hovering a stroke with the eraser dims it, a click removes it (`canvas.remove`), and Undo in the bar restores it. The assistant proposes no strokes in this pass; if it ever does, they use the machine mark: `--ink-3`, dashed.
- **Connector tool.** Click one note, then another, to relate them with a clean cubic curve that leaves and enters at the nearest edges; an optional Small label sits at the curve's midpoint on a `--paper` backing. Undirected by default: no arrowhead. Holding Shift while finishing makes it directed and draws an open chevron at the end. A connector persists as an `arrow` record (`canvas.create`), label included. **Direction is kept client-side** in `localStorage` under `jv.connectors.directed` (a set of record ids) behind the flag `jv.flags.connectorDirection`, because the `arrow` kind has no direction field and the backend is out of scope. On another device a directed connector shows as undirected, which is the default look, so nothing misleads. The endpoint this needs: a `directed: boolean` on the `arrow` kind. A connector made by voice would land as a canvas proposal (`proposal.create`, kind `arrow`), proposed until accepted; the voice path itself is WP3's and is not built here.

**Chosen, built (three)**

- **Session strip** (time). A 40 px strip between the canvas and the composer, expandable to 96 px. One mark per moment, in mono: a photograph (a small square), an accept (a filled circle in the note's colour), a recognised voice command (a periwinkle bar), a quote (a short line). Moments come from what the snapshot already holds: `source` records of type image, items with `created_at` at acceptance, transcript segments carrying `voice_command`, and quote links. Dragging along the strip, or pressing the arrow keys while it has focus, scrubs: notes accepted after that moment fade to 20 percent and proposals made after it disappear, positions stay current (the server keeps no position history; stated in 1.4), and the strip's cursor shows the time in mono. Releasing returns to now. Needs no persistence.
- **Quote notes** (voice). Hovering a transcript line shows "Quote"; pressing it pulls the line onto the canvas as a note whose text is the words, with a mono marker of the time it was said (`14:02`) linking back: pressing the marker scrolls the transcript to the line and highlights it in `--mint-soft`. The note persists as a typed note (`source.text`), so it is reviewed like any person's note; a quote note's fill is its speaker's People colour. **The link from note to segment** is kept in `localStorage` under `jv.quotes.links` (note id to segment id and time) behind the flag `jv.flags.quoteLinks`, and the time is also written into the note text as a trailing mono-styled marker, so the link survives on other devices as text. The endpoint this needs: `transcript_segment` as an allowed reference kind on proposals, which is the open decision in `docs/proposal-organise-step.md`.
- **Parked margin** (a place). A fixed 200 px band at the canvas's right edge, `--paper-2` with a hairline, titled "Parked" in Small. Dragging a note into the band parks it; dragging it out unparks it. The band reads as a shelf, not a list: parked notes stack top to bottom with their accepted colour muted to `-soft` and no rotation. Parking persists through the canvas object model: the band is a `section` record titled "Parked" with form `free`, created on first use by `canvas.create`, and membership changes through `canvas.update`. The section itself is never drawn as a rectangle on the canvas; the client draws the margin. "Park this" by voice is WP3's and is not built here.

**Not built, and why.** Evidence view (the full photograph is reachable through the media endpoint, but mapping notes back onto it duplicates what the threads and the review crop already show; it goes to the next pass). Voice as an actor (commands are recognised but not executed on this branch, so there is nothing for the caption to show; the transcript already shows the recognised command and its result line, which is the honest version of this feature today).

**Invented: provenance threads** (evidence, record, voice). When a note is selected, thin curves are drawn in page space from the note's edge to each of its origins that is on screen: the photograph crop in the review rail or in the note's own details, the transcript line a quote came from, the row in People of the person who accepted it, and the connector or section it belongs to. Threads are `--ink-3` at 1 px, drawn on a full-page SVG above everything, and they follow scrolling and panning for as long as the selection lasts. Nothing else on the screen has lines leaving it, so a thread reads as "this note is attached to the world". It comes from the product's claim that every note has a source: the claim becomes something a person can see from two metres away, and a note with no threads is visibly a note that nobody has substantiated. Threads use only data the snapshot already holds (`refs`, `region_id`, `accepted_by`, the quote links); they persist nothing.

### 1.3 Departures from section 6, and decisions the brief left open

- **Base of the branch.** `ui-redesign` branches from `feature/canvas-model` (pull request 42), which adds the `stroke`, `arrow` and `section` records and their commands. The drawing tool, the connector tool and the parked margin therefore persist through real endpoints instead of `localStorage`, and the brief's rule that the tools are part of the record holds. No Python file is modified in this pass.
- **The entry and agreement screens stay** (join or start, the agreement gate, the photograph flow, the export page). They are not new top-level screens; they are restyled with the system. The session view is where everything else lives.
- **Header.** As section 6, with one change: the state chip and the recording timer are one element, so the room reads "listening 12:04" or "paused" at a glance. The participant line shows the people as their coloured circles followed by "everyone agreed" or "waiting for Sam".
- **Canvas toolbar.** Bottom left, floating, as section 6. Tools in order: select, draw, erase, connect, then a hairline, then zoom out, zoom level, zoom in, fit, then the view toggle (canvas, list). Keyboard: V select, D draw, E erase, C connect, 0 fit.
- **Notes.** Width steps 200, 260 and 320 px (the brief's 200 px minimum, three steps so a wall of mixed lengths still aligns). Proposed notes rotate; accepted never. **A note's colour is evidence:** a note read from a photograph takes the accent nearest its measured paper colour (yellow, lilac, mint, periwinkle, coral), so the canvas keeps the wall's own colour logic; a typed note is yellow; a quote note is its speaker's colour; a corrected note carries the 6 px `--ink` corner mark.
- **Groups and sections.** Both draw as section 6's groups: a `-soft` accent rectangle behind the members with a Small label, at -1 degree for a proposed group, straight once accepted. A cluster (a reviewed claim about meaning) and a section (an area a person drew) look the same; the label says which ("Group" or "Section").
- **Canvas objects from the model** (shapes, text, arrows, strokes) are drawn in the new system: shapes as flat `-full` fields, text as Title or Body in `--ink`, hand-made strokes and connectors as the human mark, proposed ones as the machine mark.
- **Review rail.** As section 6. A review card is: crop first (or the quoted line, or "typed by Jo"), text second in Note style, then Accept, Correct, Reject. Correct turns the text into a field in place; accepting a corrected text keeps the corner mark. The queue's focused card carries the one shadow.
- **Typefaces** are vendored in `app/client/fonts/`: General Sans 400, 500 and 600 (Fontshare, ITF Free Font License, section 01 permits self-hosting; the repository is private; if it goes public, switch to the Fontshare API link) and JetBrains Mono 400 (SIL OFL). No network fonts, which the design audit also requires.
- **Room mode.** The scale in section 5 is designed for the projector at 1920 by 1080, so the previous `data-room` 1.5 scale is removed. A "Projector" setting in the Session menu scales type by 1.25 through one token and nothing else.
- **The previous design system** (`app/design-system/`, rebuilt on 18 October) is superseded on this branch by this file and `app/client/tokens.css`. Its specification files are left as the record of the previous system; folding this concept into them is on the next-pass list. Its mechanical audit (`spec/audit.sh`, a shell script) is kept and pointed at the new token file; its Python contrast tool is not modified (the brief forbids `.py` changes), so this branch verifies text-on-colour pairs with `app/client/tests/contrast-unit.mjs` over the new tokens, and the CI workflow runs that instead.
- **Gaps in the transcript** stay one notice outside the transcript, as the team decided on 12 October.
- **Phone width** keeps the previous rules: the list by default, the board read only, 44 px targets through the coarse-pointer token.

### 1.4 What this pass does not do

- Position history: the session strip cannot show where a note was at a past moment, only whether it existed and was accepted; the server keeps only the current position.
- Voice commands do not edit the board yet (WP3), so the connector-by-voice and park-by-voice paths are specified, not built.
- The backend's API is unchanged; the three persistence gaps (connector direction, quote links, nothing for threads) are listed above with the endpoint each needs.

Latent defects the audit found in the existing client, and what happens to them here: crops are capped at 16 blob URLs per client and never released, which the review rail and the threads would hit in a long session, so phase 4 releases crop URLs when a card leaves the queue and raises nothing else; after one uncertain control command the control buttons stay blocked until a reload, so phase 4 adds "Try again" and "Discard" to that banner using the sync library's retry and discard; the client accepts only a localhost server address (`allowLan` is off), a reload loses the device's credential, and a session deleted by another facilitator may leave the old canvas on screen: these three go to the next-pass list, because each needs a product decision or a backend change.

### 1.5 Ownership for phase 3

Each agent edits only its own files and its own marked region of `index.html`. `app.mjs` is edited by phase 2 (hook points) and phase 4 (integration) only.

| Agent | Files |
|---|---|
| Header and banner | `app/client/header.mjs`, `app/client/css/header.css`, the `<!-- region: header -->` block |
| Canvas | `app/client/board.mjs`, `app/client/canvas-objects.mjs`, `app/client/tools/draw.mjs`, `app/client/tools/connect.mjs`, `app/client/tools/dock.mjs`, `app/client/css/canvas.css`, the `<!-- region: canvas -->` block |
| Review rail | `app/client/review.mjs`, `app/client/transcript.mjs`, `app/client/people.mjs`, `app/client/css/rail.css`, the `<!-- region: rail -->` block |
| Session strip | `app/client/tools/strip.mjs`, `app/client/css/strip.css`, the `<!-- region: strip -->` block |
| Quote notes | `app/client/tools/quote.mjs`, `app/client/css/quote.css` |
| Parked margin | `app/client/tools/parked.mjs`, `app/client/css/parked.css`, the `<!-- region: parked -->` block |
| Provenance threads | `app/client/tools/threads.mjs`, `app/client/css/threads.css`, the `<!-- region: threads -->` block |

## 2. Foundations

Phase 2 built the token file, the primitives, the stylesheet split, the module skeleton with the tool registry, a showcase page, a contrast test and the audit changes. The regions themselves are not redesigned yet: every region stylesheet is a placeholder that moves the previous client's rules onto the new tokens, so the current screens already render on the new ground, type and colours.

### 2.1 Files

| File | What it holds | Owner from phase 3 |
|---|---|---|
| `app/client/tokens.css` | Every literal value: faces, palette, derived accents, roles, type, space, radii, shadow, lines, motion, layout sizes, layers, and the three switches | phase 4 only |
| `app/client/client.css` | Ten `@import` lines, then the page-wide rules: `[hidden]` wins, box sizing, body ground and type, the focus ring, `.visually-hidden` | phase 4 only |
| `app/client/primitives.css` | Type roles, layout utilities, buttons, chips, legacy status marks, tabs, the view toggle, fields, the note, canvas marks, the dock | phase 4 only |
| `app/client/css/screens.css` | Entry, agreement gate, workspace grid, photograph flow, export page, confirmation dialog | phase 4 (added beyond the brief's list, see 2.7) |
| `app/client/css/header.css` | Session bar, menu, banners | header and banner agent |
| `app/client/css/canvas.css` | Board tools, board, notes on the board, groups, canvas objects, list, hint, composer | canvas agent |
| `app/client/css/rail.css` | Rail, review queue, transcript, people rows (also on the gate), invitation | review rail agent |
| `app/client/css/strip.css`, `quote.css`, `parked.css`, `threads.css`, `tools.css` | A header comment naming the owner; `threads.css` lays out the hidden page-space SVG; the rest hold no rules | strip, quote, parked and threads agents; `tools.css` is the canvas agent's |
| `app/client/header.mjs`, `app/client/tools/{dock,draw,connect,strip,quote,parked,threads}.mjs` | Stubs exporting `register(registerTool)` that register nothing | as 1.5 |
| `app/client/dev/components.html` | The showcase (2.4) | phase 4 |
| `app/client/tests/contrast-unit.mjs` | The contrast test (2.3) | phase 4 |

`index.html` links `tokens.css` then `client.css` and no longer links `app/design-system/spec/exemplars/_base.css`. `app/design-system/tokens.css` is deleted. `_base.css` is unchanged and still serves the five exemplars, `app/server/demo-audio.html` and the week 4 slides.

### 2.2 The token file

Sections, in order: 1 faces (`@font-face` for General Sans 400, 500, 600 and JetBrains Mono 400, from `fonts/`, `font-display: swap`); 2 palette; 3 derived accents; 4 roles; 5 type; 6 space, shape, depth, lines; 7 motion; 8 layout sizes and layers; 9 switches. All custom properties sit on one `:root` block, followed by `:root[data-projector] { --scale: 1.25; }`, a `(pointer: coarse)` block that raises `--target`, the control heights, `--dock-button` and `--h-field` to 44px (`--h-control-lg` to 48px), and a `(prefers-reduced-motion: reduce)` block that sets `--t-fast`, `--t-base`, `--t-slow` and `--stagger` to 0ms.

**Palette.** As the brief: `--paper` #FAF8F3, `--paper-2` #F2EFE7, `--line` #E4E0D5, `--ink` #16150F, `--ink-2` #5C594F, `--yellow` #FFC83D, `--lilac` #E9A8F2, `--mint` #9FE8CC, `--periwinkle` #8FB0FF, `--coral` #FF9C8A. One departure: `--ink-3` is `color-mix(in srgb, #8E8A7E, var(--ink) 25%)`, which resolves to #706D62. The brief's #8E8A7E measures 3.25:1 on `--paper` and 3.00:1 on `--paper-2`, below AA for Small text, and the brief asks for `--ink-3` to pass as Small text; 25% toward ink is the smallest step in 5% increments that passes on both grounds.

**Derived accents.** `-soft` is `color-mix(in srgb, var(--accent) 32%, var(--paper))` and `-deep` is `color-mix(in srgb, var(--accent), var(--ink) 55%)`: the brief's percentages, unchanged, because every pair passed at them. Values as resolved (the browser matches them to the channel, 2.3), ratios to 1:

| Accent | full | -soft | ink on full | ink on -soft | ink-2 on -soft | -deep | paper on -deep |
|---|---|---|---|---|---|---|---|
| yellow | #ffc83d | #fce9b9 | 11.83 | 15.19 | 5.82 | #7f6624 | 5.20 |
| lilac | #e9a8f2 | #f5def3 | 9.88 | 14.50 | 5.56 | #755775 | 5.85 |
| mint | #9fe8cc | #ddf3e7 | 12.97 | 15.70 | 6.01 | #547464 | 4.88 |
| periwinkle | #8fb0ff | #d8e1f7 | 8.55 | 13.95 | 5.35 | #4c5b7b | 6.41 |
| coral | #ff9c8a | #fcdbd1 | 9.03 | 14.05 | 5.38 | #7f5246 | 6.20 |

Other measured pairs, ratios to 1: ink on paper 17.23, on paper-2 15.92, on line 13.87; ink-2 on paper 6.60, on paper-2 6.10; ink-3 on paper 4.89, on paper-2 4.52; danger (coral-deep) on paper 6.20, on danger-soft 5.06; paper on danger 6.20; ink on the primary hover (yellow 10% toward ink, #e8b638) 9.73; the accepted status word (mint-deep) on paper 4.88; the waiting status word (yellow-deep) on paper 5.20; paper on ink 17.23; mint bars on ink 12.97 (non-text, 3:1 needed); the machine mark (ink-3) on paper 4.89 (non-text). `--ink-2` on a full accent measures 3.28 (periwinkle), 3.46 (coral), 3.79 (lilac), 4.53 (yellow) and 4.97 (mint), so it is not used there (2.7).

**Roles.** Components use these, never a hue name: `--surface`, `--surface-sunken`, `--edge`, `--text`, `--text-2`, `--text-3`, `--text-on-deep`; `--action-primary` (yellow), `--action-primary-hover`, `--action-primary-text` (ink), `--action-secondary` (paper-2), `--action-secondary-hover` (line), `--action-quiet-hover`, `--danger` (coral-deep), `--danger-soft`, `--text-on-danger`; `--state-listening` (mint), `--state-paused` (yellow), `--state-ended` (ink-3); `--status-accepted`, `--status-waiting`, `--status-failed`, `--status-proposed`, `--status-off`; `--note-proposed-fill` (yellow-soft), `--note-proposed-edge` (yellow), `--note-accepted-fill` (yellow), `--note-corrected-mark` (ink), `--note-max-rotation` (1.5deg); `--person-1` to `--person-10` (lilac, mint, periwinkle, coral, yellow, then their `-deep`); `--mark-human` (ink at 85%), `--mark-machine` (ink-3), `--dash-machine` (`4 4`), `--thread` (ink-3); `--tone-{ink,accent,category-1,category-2,category-3}-{fill,line}` for the canvas object model's tones (paper-2 and ink; then periwinkle, lilac, mint and coral as a `-soft` fill and a `-deep` line); `--focus-ring` and `--selected` (ink), `--backdrop`, `--highlight` (mint-soft). A dark theme redefines sections 2 and 4 under `:root[data-theme="dark"]` and touches no component.

**Type.** `--font-ui` (General Sans, then system faces) and `--font-mono` (JetBrains Mono, then system monospace). `--fs-*`, `--lh-*` and `--fw-*` for display 44/1.05/500 (with `--ls-display` -0.02em), title 22/1.2/600, note 18/1.3/500, body 15/1.5/400, small 13/1.4/500, mono 13/1.4/400 (12px until the phase 5 review, 5.6); each size is `calc(Npx * var(--scale))`. The canvas has its own sizes, `--fs-canvas-*`, which do not follow `--scale` and put Small and Mono at 15px there (5.6). `--fw-strong` 600, `--fs-field-touch` 16px, `--reading-max` 68ch.

**Space, shape, depth, lines.** `--space-1` to `--space-8` are 4, 8, 12, 16, 24, 32, 48 and 64px. `--r-sm` 6px, `--r-lg` 14px, `--r-pill` 999px, `--r-none` 0. `--shadow` is `0 2px 12px color-mix(in srgb, var(--ink) 8%, transparent)`, which equals the brief's rgba(22, 21, 15, 0.08), bound to ink. `--line-1` 1px, `--line-2` 2px, `--focus-width` 2px, `--focus-offset` 2px, `--ink-weight` 3px, `--corner-mark` 6px, `--glyph` 10px, `--bar-w` 4px, `--bars-h` 12px. Control heights: `--target` 32px, `--h-control-sm` 28px, `--h-control` 36px, `--h-control-lg` 44px, `--h-field` 40px, `--h-chip` 24px, `--dock-button` 40px, `--check` 20px, `--icon` 20px; `--press` 0.98, `--disabled-opacity` 0.4.

**Motion.** `--t-fast` 120ms, `--t-base` 200ms, `--t-slow` 360ms, `--t-bars` 1.6s, `--stagger` 40ms, `--ease-out` cubic-bezier(0.2, 0.8, 0.2, 1), `--ease-in-out` cubic-bezier(0.6, 0, 0.3, 1), `--land-from` 0.92, `--accept-peak` 1.03, `--reject-to` 0.96.

**Layout and layers.** `--rail` 360px, `--header` 56px, `--banner` 40px, `--content-max` 1280px, `--form-max` 400px, `--gate-max` 720px, `--menu-min` 200px, `--dialog-max` 480px, `--page-pad` 16px, `--page-pad-wide` 32px, `--note-w-narrow` 200px, `--note-w-default` 260px, `--note-w-wide` 320px, `--parked-w` 200px, `--strip-h` 40px, `--strip-h-open` 96px, `--board-chrome` 260px, `--board-min` 420px, `--board-min-narrow` 320px, `--board-narrow-h` 56vh, and placeholder layout sizes carried from the previous client (`--crop-max-h`, `--found-thumb`, `--stage-tools-min`, `--stage-tools-max`, `--stage-chrome`, `--list-label-w`). Layers: `--z-sticky` 2, `--z-drag` 5, `--z-dock` 20, `--z-header` 30, `--z-menu` 40, `--z-threads` 50.

### 2.3 The contrast test

`node --test app/client/tests/contrast-unit.mjs` (50 tests) parses the first `:root` block of `tokens.css`; resolves `var()`, hex, `rgb()`, `transparent` and `color-mix(in srgb, ...)` as CSS Color 5 defines them (a missing percentage is the rest of 100%, alpha is premultiplied); and asserts 4.5:1 for every text pair the system ships and 3:1 for the meaningful non-text marks, printing each measured ratio as a test diagnostic. It also asserts that each accent's `-soft` and `-deep` are bound to it with `color-mix`, that `--mark-human` is ink at 85%, that the projector block sets `--scale` to 1.25 and every `--fs-*` follows `--scale`, and that reduced motion sets the three durations to 0ms. Its resolver was checked against Chromium: all 76 colour tokens resolve to the browser's computed value with a worst channel difference of 0.000.

### 2.4 The showcase

`/client/dev/components.html` links `../tokens.css` and `../client.css` and shows: every colour token (ground, ink, accents with `-soft` and `-deep`, roles, people) with its value and the contrast of the text drawn on it, both read from the page at run time; the six type roles, with a Projector toggle; the space scale; radii and the shadow; every button variant at three sizes, disabled and focused; the chips (listening with the three bars, paused, ended, count, plain) and the legacy status marks; tabs with a count; the view toggle; fields (input, hint, textarea, select, disabled, focused, checkbox rows); the note in every state (proposed with `--rot`, proposed through the legacy `item-pending` class, a 9 degree request clamped to 1.5, accepted in each accent, corrected, selected, dragging, details open, parked) with buttons that replay landing, accepting and rejecting; the canvas marks (connector, directed connector with its chevron, label, ink stroke, and the machine mark on both); the dock. At 1440px and 400px it has no horizontal overflow, no console errors and no failed requests, and all four faces load.

### 2.5 The module skeleton and the tool registry

`index.html` marks each region with `<!-- region: NAME -->` and `<!-- /region: NAME -->`:

- `header`: two blocks. The first holds `#bar` and `#attention`; the second, inside `#screen-workspace`, holds `#paused-banner`, `#keepalive-banner` and `#ended-banner`, because those show only in the workspace.
- `canvas`: inside `.ws-main`, from `.board-tools` to the composer. Three regions are nested inside it and are not the canvas agent's: `parked` (`<aside id="parked" aria-label="Parked" hidden>`, right after `#board`), `dock` (`<div id="dock" role="toolbar" aria-label="Canvas tools" hidden>`, after `#parked`) and `strip` (`<div id="session-strip" hidden>`, between `#board-hint` and the composer).
- `rail`: the `<aside class="ws-rail">`.
- `threads`: `<svg id="threads" aria-hidden="true" focusable="false" hidden>`, the last element before `</body>`, after the module script; `threads.css` makes it fixed, full page, above everything, and never a press target.

The four new containers start `hidden`, so no empty landmark is announced before its agent fills it; each agent shows its own through the `hidden` property (0.7).

`app.mjs` imports the eight stubs and calls `register(registerTool)` on each, in this order: header, dock, draw, connect, strip, quote, parked, threads. The API, exactly:

```js
// In a tool module:
export function register(registerTool) {
  registerTool("name", {
    mount(ctx) {},              // once, from wire(), right after the Board is made and the photo
                                // flow is wired, before the first render
    render(ctx, snapshot) {},   // at the end of every render() that has a snapshot with a session
    onSelection(ids) {},        // first thing in the board's selection callback; ids is an array of record ids
    onZoom(z) {},               // after the zoom readout updates; z is the zoom factor, 1 is 100%
  });
}
```

`registerTool(name, hooks)` throws a `TypeError` for an empty name and an `Error` for a name already registered. Every hook is optional. Hooks run in registration order; a hook that throws is reported with `console.error`, and the remaining tools and the render continue (the browser tests fail on any console error, so a broken tool is still caught).

`ctx` holds: `app` (the state object, 0.5), `$` (getElementById), `show(el, on)`, `send(operation, payload, options)`, `attention(message, kind)`, `describe(error)`, `render()`, `button(label, variantClasses, asyncOnClick)`, `confirm({title, text, detail, action, danger})`, `clock(seconds)`, `screen(name)`, `rail(name)`, `undo()`, `stopListening(reason)`, `review` (the Review panel), `board` (a getter for `app.board`, the `Board` instance), `machineMade(record)`, `boardModel(snapshot)`, `memberName(snapshot, actorId)`, and `settle(el, className, {keep = false, timeoutMs = 1000})`. `settle` adds a motion class (`note-landing`, `note-accepting`, `note-rejecting`) and resolves when that element's own animation ends, at once when there is no animation (reduced motion), or after the timeout; it removes the class unless `keep` is true.

### 2.6 Bindings changed

Every id, class and data attribute in 0.2 is kept, except:

- **Stylesheets.** `index.html` links `tokens.css` and `client.css`; the client no longer links `_base.css`.
- **Room view became the projector setting.** `html[data-room]` is now `html[data-projector]`, set by `setRoom` in `app.mjs`. The button keeps the id `room-toggle` and reads "Projector", then "Projector: on" or "Projector: off". The board is no longer zoomed by 1.5, because `--scale` now grows the type everywhere. Revised in the phase 5 review (5.6): the type on the canvas no longer grows, and the board's zoom carries the projector there instead, because grown type at fixed note places ran notes into each other. The `localStorage` key stays `jarvaids-room`, so a browser with room view on returns with the projector on.
- **New ids:** `session-strip`, `parked`, `dock`, `threads`, all hidden.
- **Note widths** are 200, 260 and 320px (1.3), through `--note-w-*`. `LANE_WIDTH` in `board.mjs` is 320 + 48; Place new notes in `app.mjs` starts 320 + 32 right of the rightmost note and steps columns by 320 + 64.
- **Legacy classes restyled, names kept.** `.st-provisional` is `--ink-2` (was the blue accent); `.glyph-*` are 10px token-coloured marks (disc, dashed ring, ring, rotated square, square) instead of the six drawn glyphs; `.badge` is mono; `.item-provisional` and `.item-pending` are the proposed note, `.item-accepted` the accepted note, `.item-selected` the ink outline, `.dragging` the shadow; `.t-heading` is the Title role, `.t-meta` and `.t-caption` Small in `--text-2`, `.t-signal` Mono, `.t-structure` Small in `--text-3`.
- **`tests/canvas-objects-browser.mjs`** reads its expected values from the page's tokens instead of literals: `accent` is `var(--tone-accent-line)`, `ink` is `var(--ink)`, a proposed shape's stroke is `var(--mark-machine)` (was the accent), and a heading text's size is `var(--fs-display)` (was 28px).
- **Audit and CI.** `audit.sh` excludes `app/client/tokens.css` and `app/client/fonts/` from the four literal checks (hex, radii, typefaces, line widths) and from nothing else; its contrast step runs the node test, with a comment saying why the Python tool is not edited; its shadow check also allows `var(--shadow)`. In `.github/workflows/verify.yml` the design-system job sets up Node 24 and its two Python contrast steps (the check and the generated-table comparison) became one `node --test app/client/tests/contrast-unit.mjs`; the client job runs the same test from `app/client`. `.githooks/pre-push` and the command list in `AGENTS.md` run the node test instead of `contrast-check.py`.

### 2.7 Decisions

- `--ink-3` moves 25% toward ink (2.2), because the brief requires it to pass as Small text and its literal does not.
- On a full accent, a note's secondary lines (kind, meta, marker, stamp, its quiet buttons, the facts) are `--ink`, set through `--note-text-2`; on `-soft` fills (proposed, parked) they are `--ink-2`. Size and the mono face tell them apart, because `--ink-2` fails on three of the five full accents.
- The listening chip is `--ink` with `--paper` words and three `--mint` bars. A mint chip would hide mint bars; on ink they measure 12.97:1 and read across a room.
- A typed note waiting for review is drawn as a proposed note (soft yellow, yellow edge, rotation), because it is a proposal; its marker says who typed it.
- Rotation uses the `rotate` property, clamped in CSS to plus or minus `--note-max-rotation`, because the board already writes `transform` inline for the details offset. Motion uses `scale` and `rotate` for the same reason.
- Every transition and animation is declared inside `@media (prefers-reduced-motion: no-preference)`, and the reduced-motion switch also zeroes the durations; `settle` resolves at once when no animation runs.
- The proposed look is set through `--note-fill` on `.note`. The audit's "provisional is never a plain fill" check looks for `background:` on a line that names provisional, so it does not see this fill. That rule comes from the previous system, where proposed meant no fill; concept 1.1 deliberately replaces it with a soft fill plus an edge, a marker and rotation. The check is kept and still refuses a bare background on a provisional selector.
- `css/screens.css` is a tenth import beyond the brief's nine, owned by phase 4, for the screens no phase 3 agent owns (entry, gate, photograph, export, dialog) and the workspace grid.
- Menus and the dialog are floating but carry a 1px `--edge` line, not the shadow, because the brief gives the one shadow to the dock, dragged notes and the focused review item only.
- The view toggle is the only pill, as "toggles are the only pills" says.
- Region containers start hidden (2.5).
- The favicon is a soft yellow square with a yellow edge, written as `%23` literals in a data URI, the one place a token cannot reach; it duplicates `--yellow-soft` and `--yellow`.
- The `.dock` primitive wraps at narrow widths, so a full toolbar never makes the page scroll sideways at 400px.
- `--target` stays 32px on a fine pointer (the previous value) and is 44px on a coarse pointer.

### 2.8 Known gaps

- Field edges are `--line` on `--paper`, 1.24:1, below the 3:1 of WCAG 1.4.11 for a component boundary. The brief specifies the 1px `--line` edge; the label above each field identifies it, and the edge darkens to `--text-3` on hover. A redesign that wants 1.4.11 should use `--text-3` for the edge.
- The proposed note's yellow edge on its soft yellow fill is 1.28:1. It is not the only signal: the fill, the rotation and the mono "proposed" marker (ink-2 on yellow-soft, 5.82:1) carry it.
- `app/design-system/spec/contrast-check.py` cannot run now (it reads the deleted token file), and `spec/accessibility.md` and the design-system README describe the previous tokens. They stay as the record of the previous system (1.3).

### 2.9 Verification, 19 October 2026, on this Windows machine

Node 24.22.0, Python 3.14.0 from `.venv`, Chromium from Playwright in `app/client/node_modules`.

- `node --test tests/contrast-unit.mjs tests/canvas-objects-unit.mjs tests/board-unit.mjs`: 83 tests, 83 pass.
- `node tests/journey.mjs`: all 18 steps print `ok`, including the steps for no console errors and no failed requests and for no sideways scroll at 400px; it then exits 1 on the known EPERM when removing its temporary data folder (0.6).
- `node tests/canvas-objects-browser.mjs`, `node tests/command-recognition-browser.mjs` and `node tests/speaker-enrollment-browser.mjs` pass at 1440px and 400px. `node tests/canvas-objects-server-browser.mjs` passes.
- `bash app/design-system/spec/audit.sh app/client`, and with no arguments: 13 checks, Clean. The literal exclusion was checked against a fixture: a hex, a face name and a literal shadow in another file under `app/client` fail; the same in `app/client/tokens.css` do not; `var(--shadow)` passes.
- Screenshots looked at: the showcase at 1440px (full page), and the journey's workspace and details screens. The header, banner, buttons, tabs, notes and rail are on paper, in General Sans, with the yellow primary; accepted notes are full yellow with mono stamps; the proposed note is soft yellow with the yellow edge and a mono "Proposed".
- Not verified: the CI workflow itself (not run here); the projector setting and a coarse pointer in the real client (the projector toggle was exercised only on the showcase); reduced motion in a browser; the motion classes inside the real board, which does not use them until phase 3. The board does not yet set `--rot`, so proposed notes on the board are straight.

## 3. Regions and tools

Phase 3 built the seven regions in parallel, one agent each, on branches merged into `ui-redesign` at `d95df94`. This section says what each built and the decisions each made, as they stand after phase 4 (section 4 lists what phase 4 changed). Sources: the seven commit messages (`38bcbb5`, `1fad29a`, `f7e531f`, `050660d`, `033f3c0`, `a854469`, `2533775`), the agents' reports as the orchestrator recorded them, and the code.

### 3.1 Header and banners (`header.mjs`, `css/header.css`)

Built: one 56px row with the session title as an `h1` in the Title role, one state chip, the people as coloured circles in join order followed by "everyone agreed" or "waiting for Sam and Jo", then Photograph the wall as the only filled primary, the Listen toggle, and quiet Undo, Pause and Session. The three workspace banners (`#paused-banner`, `#keepalive-banner`, `#ended-banner`) are now the parts of one 40px capture banner (`#capture-banner`) inside the header's bottom edge, every id kept. The attention banner is a quiet line with a coral or mint mark and Dismiss. Tests: `tests/header-unit.mjs` (12) and `tests/header-browser.mjs` (real server, 1920 by 1080 and 400px).

Decisions:

- The chip is one element (`#session-status`) carrying the session's state, or "Listening" with the three bars and the `#listen-timer` timer. It says "Listening" only while the session is open and this device's microphone is on, because "Session open" is not recording.
- The chip's words for the session states stay app.mjs's own ("Session open", "Paused", "Not started", "Ended"), because the journey waits on them; header.mjs renders after app.mjs and sets the chip's class and bars.
- Open is `--chip-open` (mint-soft), paused `--chip-paused` (yellow-soft), listening is ink with mint bars, ended is the sunken tone, not started is a line with no fill.
- header.mjs watches `#listen-status` and the agreement screen's `hidden` attribute with a MutationObserver, because both change without a render.
- The keep-alive part counts down from the last renewal this screen saw and errs early: it counts heartbeats from the moment it saw the heartbeat come on and keeps the last whole beat. With no renewal seen it says "within 5 minutes". In the last minute the banner turns `--chip-paused`. A countdown that reached zero while capture still ran would teach the room to ignore it.
- The capture banner is hidden on the agreement screen, which explains a pause in its own words.
- `--header-stack` is `--header`, or `--header` plus `--banner` while the capture banner shows (`:root:has(.capture-banner:not([hidden]))`), so sticky parts below the header can clear it.
- `personTone(i)` gives `var(--person-N)` by join order, ink initials on the five accents and paper initials on the five `-deep` steps.
- The attention marks (coral, mint) measure under 3:1 against the ground; the sentence beside each carries the meaning, so this is accepted.
- A state change is announced once through a visually hidden live region (`#state-announce`), not the timer every second.

### 3.2 Canvas (`board.mjs`, `canvas-objects.mjs`, `tools/dock.mjs`, `tools/draw.mjs`, `tools/connect.mjs`, `css/canvas.css`, `css/tools.css`)

Built: the board is paper with 24px dots that pan and scale with the world, and no frame. Notes take the concept's looks; new proposals land, accepted ones settle and swell, rejected ones fade out, through `ctx.settle`. Groups and sections are one soft rectangle with the label inside its top left. Shapes are full accent fields with Note text; connectors and strokes are the human mark, proposed ones the machine mark. The dock floats at the board's bottom left. The empty state is a Display line, one sentence and two actions on a lilac rectangle turned two degrees. Tests: `tests/canvas-browser.mjs` (real server, 1920 and 400px), `tests/draw-unit.mjs` (9), `tests/connect-unit.mjs` (13), and updates to `board-unit.mjs` (13), `canvas-objects-unit.mjs` (29) and `canvas-objects-browser.mjs`.

Decisions:

- A proposed note is askew by 0.4 to 1.5 degrees either way, deterministic from its id (`noteRotation`, an FNV hash), written as `--rot` and clamped in CSS, so every screen draws the same note at the same angle and a redraw never makes it wobble. Under 0.4 degrees a note reads as straight, which is the accepted look.
- A typed note waiting for review is paper with a hairline edge and "Not yet reviewed", straight. This replaces the 2.7 wording (drawn as a proposal): a person wrote it, so it is not a guess, but nobody accepted it either.
- An accepted note takes the accent nearest its measured paper colour (`nearestAccent`, over the five accents read from the page's tokens); anything else is yellow. Its stamp is "Accepted by Sam 14:02", the time from the item's `created_at`, which is the moment of acceptance.
- A note is corrected (`note-corrected`, the 6px ink corner mark) when it was retyped from the photograph or a model reading's accepted text was edited since.
- The classes `.note-{yellow,lilac,mint,periwinkle,coral}` and the `--note-fill` custom property are the contract the quote and parked tools rely on; an inline `--note-fill` wins.
- Groups and sections draw the same way; the label says "Group", "Proposed group" or "Section". A proposed group is askew by one degree.
- Motion runs only with `ctx.settle` and never on the first render, so opening a board does not replay its history. Landing is staggered in wall reading order (the region the note was read from, then board order).
- The dock: select, draw, erase, connect (V, D, E, C), a hairline, zoom out, the level, zoom in, fit (0), a hairline, Canvas and List. The zoom buttons and the view toggle stay static markup with their ids. Shortcuts are ignored in a field, in a dialog and outside the canvas view. Draw, erase and connect are disabled on a read-only (touch) board and once the session has ended.
- The pen draws one weight in the human mark, smoothed into quadratic curves through the midpoints, simplified (Ramer, Douglas and Peucker, the tolerance growing by half) to at most the server's 256 points, positioned at its first point, cut where it leaves the server's 10000px offset limit, and saved as a `stroke` through `canvas.create`, accepted at once like a move. The draft stays drawn until the snapshot has the stroke, so the line never blinks out.
- The eraser removes strokes and connectors only: each carries a wide transparent hit path that takes the pointer only while the eraser is the tool. Hovering dims the mark; a click sends `canvas.remove`.
- The connector: press one note or shape, then another; a cubic curve between their nearest sides; a label field opens at the curve's middle (Enter saves with the label, Escape without). Shift on the second press makes it directed, kept on this device in `localStorage` under `jv.connectors.directed` (flag `jv.flags.connectorDirection`), in memory with one note if storage fails. Arrows that existed before this tool draw as undirected curves unless their id is in the set.
- `Board` gained `setTool`, `setToolHandler`, `hold`, `decorate`, `draftLayer`, `toWorld`, `boxOf`, `objectAt`, `directed` and `settle`, and emits `jv:tool` and `jv:board-rendered` on `#board`. `.board-stage` wraps `#board`, `#board-empty`, `#parked` and `#dock`.
- The dots are the one `radial-gradient` in the client: it draws dots, not a colour ramp, so it keeps the no-gradients rule's reason.

### 3.3 Review rail (`review.mjs`, `transcript.mjs`, `people.mjs`, `speakers.mjs`, `css/rail.css`)

Built: review cards show the evidence first (the crop at full card width, "Typed by" with the person's circle, a group's members, or a canvas proposal's list line), the text second in the Note style, then Accept, Correct, Reject. The focused card carries the one shadow and opens with its field. Transcript rows carry `data-segment-id` and `id="seg-<id>"`, the speaker in their People colour, mono times, the newest line on the highlight tone, a recognised command on periwinkle-soft, and a quiet Quote button. People rows carry `data-actor-id`, a circle in the person's colour, role, mono agreement time and the agreement mark. Tests: `tests/rail-unit.mjs` (9) and `tests/rail-browser.mjs` (1920 by 1080 and 400px).

Decisions:

- Evidence before text, because a reviewer who reads the claim first judges the evidence against it.
- A changed field is a correction whether or not Correct was pressed: Accept sends `proposal.edit` first, then the review. A corrected text keeps the corner mark.
- Accept is the card's first primary and Reject its first quiet button, because the journey and keyboard users rely on the order. While correcting, "Keep original" takes Correct's place so Accept and Reject do not move. A canvas proposal has no Correct, because the server refuses to edit one.
- The empty queue is one sentence: "Evidence first, then the text. Nothing is in the record until it is accepted here."
- Focus inside the queue survives the redraw every poll (the field and its caret, or the pressed action), so a keyboard user is not thrown out of a card every second.
- Left and Right arrows, Home and End move between the rail's tabs.
- People colours are by join order, `--person-1` to `--person-10`; a name is drawn in its accent's `-deep`, which is legible as text where the full accent is not; on a filled transcript row the name steps to ink and the circle carries the colour.
- The transcript skips its redraw when nothing changed, so an open disclosure, a hovered Quote button and the focus stay. Quote dispatches `jv:quote` with `{segmentId, text, speakerName, speakerActorId, createdAt}`; `speakerActorId` is null for an unknown or unmatched voice.
- An ordinary line's "Transcript" badge is for screen readers only; only a command shows a badge on screen.
- `#command-status` became `class="command-status"`; `#transcript` lost `jv-rows` and `#speaker-list` lost `t-meta`. No other region's stylesheet depended on them (checked in phase 4).

### 3.4 Session strip (`tools/strip.mjs`, `css/strip.css`)

Built: one mark per moment on a time axis from the session's first moment to now, at least 60 seconds long: photographs (an 8px square), accepts (an 8px circle in the note's drawn colour, ringed in `--ink-2` so it reads at 3:1 on the sunken ground), recognised voice commands (a 3 by 12px bar in `--mark-command`) and quotes from `jv.quotes.links` (a 2 by 10px line). Scrubbing by pointer or by the arrow keys sets a moment; Home goes to the first; release, Escape, End or leaving the strip returns to now. It opens to 96px by its quiet control or while the slider has focus, one lane per kind. Tests: `tests/strip-unit.mjs` (10) and `tests/strip-browser.mjs` (1920 by 1080 and 400px).

Decisions:

- Every time is the record's own `data.created_at`; an accepted item is created at acceptance, so its time is when it was accepted.
- While a moment is set, notes accepted and canvas items made after it carry `after-moment` (20 percent opacity, no pointer events) and proposals made after it also carry `after-moment-proposal` (hidden), reapplied after every render and after the board redraws itself. The review rail is never faded, because review is present tense. Positions stay current (1.4).
- These two classes use `!important`, because they must beat a hull label's or tag's own `pointer-events` and the landing animation's opacity for as long as a moment is set.
- Nothing in the strip animates: scrubbing is direct manipulation, and a fade or a growing strip that lagged the pointer would show a moment the pointer has already left.
- A pointer within 6px of a mark lands on that moment; hover words show for the nearest mark within 10px, nearest rather than topmost because marks a few seconds apart overlap.
- The axis is a `role="slider"` whose value text names the moment in full, so a screen reader hears it.

### 3.5 Quote notes (`tools/quote.mjs`, `css/quote.css`)

Built: on `jv:quote` the words are sent as a typed note (`source.text`) ending in " · HH:MM", so a quote is reviewed like any person's note and its time survives as text on other devices. After the board draws, each linked note gets its speaker's People colour as `--note-fill`, the class `note-quote`, "Quote · <speaker>" as its kind, the trailing marker wrapped in a hidden `.quote-time` (the text's `textContent` unchanged) and a mono `.quote-marker` button. Pressing it opens the Transcript, scrolls `#seg-<id>` into view and adds `quoted-highlight` for two seconds from when the scroll ends. Tests: `tests/quote-unit.mjs` (17) and `tests/quote-browser.mjs` (12 steps, real server, 1920 by 1080 and 400px).

Decisions:

- The link is proposal id to `{segmentId, time, speakerActorId}` in `localStorage` under `jv.quotes.links`, behind `jv.flags.quoteLinks` (on unless "0", "false" or "off"), at most 500 links (a guess at about 60 KB, tested by filling the store), falling back to memory with one notice when storage throws. Writes merge what another tab stored meanwhile.
- An accepted item is linked through its `data.proposal_id`. On a device without the stored link, a note whose text ends in the marker is linked to the one transcript line with exactly those words said in exactly that minute; with none or several it is not linked, because a pointer to the wrong line is worse than none.
- A quote's secondary lines are ink on a full accent and paper on a `-deep` one (`data-quote-tone`), as on an accepted note (2.7).
- The fill does not transition, because the board redraws every note and the quote's fill is set just after, which would wash each quote from yellow to its colour on every redraw.
- Two MutationObservers (the board's world and `#transcript`) re-dress notes after the board's own redraws and relight a row redrawn mid-highlight.

### 3.6 Parked margin (`tools/parked.mjs`, `css/parked.css`)

Built: a 200px shelf on the sunken ground over the board's right edge, titled Parked, with a hairline on its left and a hint when empty. A note dragged onto it, or parked with P while focused on the board, leaves the board (`is-parked`) and stands on the shelf as a compact card in its accent at `-soft`, straight, with Unpark. Unpark puts it back just left of the band, level with its card; dragging a card onto the board puts it back at the drop point. Tests: `tests/parked-unit.mjs` (11) and `tests/parked-browser.mjs` (11 steps, real server, 1920 by 1080 and 400px).

Decisions:

- The shelf is a hand-made, accepted `section` titled "Parked" with form `free`, created on first use with its first member by `canvas.create` (so first use is one write) and changed by `canvas.update` on `member_ids`. The oldest such section is the shelf, so two screens parking at once converge on one record; notes on a second one still count as parked. A model's section titled Parked is never adopted.
- Only accepted notes park: a proposal must stay where the room can review it, and accepting one makes a new record. A note in a group or another section is refused with the reason; a note dragged out of a group parks once the board has taken it out of the group (waiting up to three seconds).
- The board's drawing of the Parked section, of parked notes and of arrows to parked notes is hidden (`is-parked-section`, `is-parked`, `is-parked-link`), marked after every board render through a MutationObserver.
- Writes run one at a time on the freshest snapshot and wait for the next poll; the screen shows the result at once through pending marks.
- The band is placed by CSS anchor positioning on `#board` (`anchor-name: --jv-board`, the one property set on an element the parked tool does not own), so it follows the board without script. Under 1024px, or without anchor positioning, it is a full-width shelf under the board whose cards run left to right.
- The shelf holds the server's limit of 60 members and says so when full.

### 3.7 Provenance threads (`tools/threads.mjs`, `css/threads.css`)

Built: selecting notes draws, in a fixed page-space SVG above everything, one `--thread` curve (`--ink-3`, 1px, no head) from the nearest edge of each note to each of its origins on screen, ending in a 4px dot: the crop in its review card or open details, the transcript line of a quote, the People row of whoever accepted it, the label of its group or section, and the middle of each connector at it. Tests: `tests/threads-unit.mjs` (22) and `tests/threads-browser.mjs` (1920 by 1080, injected rail anchors); seven injected mutants were each killed by their named assertion.

Decisions:

- An origin on a hidden rail tab, scrolled out of view, under the rail's sticky tabs or missing gets no thread; a page origin must be uncovered at its dot (an `elementFromPoint` test). A board origin is not hit-tested, because notes sit on top of their own group outline.
- A group's thread ends at its label, a connector's at the middle of its line, anything else at its edge facing the note, kept off the corners.
- Positions are recomputed at most once a frame on zoom, pan, scroll, a drag, every render and a class or `hidden` change; nothing is attached or scheduled while nothing is selected.
- Nothing is drawn while `body` or the board has the class `scrubbing`.
- The tool reads record shapes directly rather than through `canvas-objects.mjs`, because it was built in parallel with the canvas rebuild; it finds group anchors by `.hull-label` and `.cobj-title`, which the canvas kept.

## 4. Integration

Phase 4 merged nothing new: it resolved what the seven-way merge left, fixed the two latent defects 1.4 assigned to it, restyled the screens no phase 3 agent owned, put the new tests into CI and clicked through every flow in a real browser against the real server. Verified on 19 October 2026 on the Windows machine of 2.9 (Node 24.22.0, Python 3.14.0 from `.venv`, Chromium from Playwright in `app/client/node_modules`).

### 4.1 Conflicts found and how each was resolved

- **The header's people circles were empty** (`header-browser` failed: computed fill transparent). `css/header.css` and `css/rail.css` both styled `.person-dot`, one reading `--dot-fill`, the other `--person`; the rail's loads later and won, and in the header its fallback (`--rail-ground`, defined only inside the rail) was invalid. Resolved: one `.person-dot` primitive in `primitives.css` reading `--person` for the fill and `--person-text` for the initial, at `--avatar` (a new token bound to `--h-chip`); `header.mjs` sets those two variables; both duplicate rules are gone.
- **At 400px the parked shelf's Unpark could not be pressed** (`parked-browser` failed). After the canvas introduced `.board-stage`, the dock was placed absolutely against the stage's bottom, and under 1024px the shelf sits inside the stage under the board, so the dock covered it. Resolved: `.board-stage` is a grid whose one cell holds the board, the empty state and the dock (the dock at that cell's bottom left); under 1024px the shelf takes a second row. The band laid over the board on a wide screen is anchor-positioned and takes no row.
- **The workspace scrolled vertically at 1920 by 1080**, because `--board-chrome` (260px) did not count the session strip. Resolved by layout, not by a larger constant: on a wide screen, while the workspace shows, the page is a column one window tall (`css/screens.css`) and the board stage takes what the header, the attention line, the board tools, the hint, the strip and the composer leave, never less than `--board-min`. It also counts the capture banner and an open selection row, which no constant could. `--board-chrome` is removed from `tokens.css`. Measured: no vertical or horizontal scroll at 1920 by 1080 and at 1440 by 900, with and without the attention line.
- **The rail's sticky top ignored the capture banner.** `css/rail.css` uses `--header-stack` for its sticky top and its maximum height.
- **Local bindings became roles.** `--chip-open`, `--chip-paused`, `--mark-problem`, `--mark-note` and `--mark-command` are in `tokens.css` section 4 and used by `header.css` and `strip.css`; the contrast test asserts ink on both chip fills (52 tests, was 50). The three marks stay under 3:1 as non-text, which is accepted because the words beside each carry the meaning.
- **Dead `#state-glyph`.** `app.mjs` no longer writes `#state-glyph` or the chip's class (header.mjs owns the chip); the element is gone from `index.html`, so 0.2's `state-glyph` id no longer exists.
- **Threads did not hide while scrubbing**, because the strip set no class. `tools/strip.mjs` toggles `scrubbing` on `body` whenever a moment is set or cleared.
- **Fitting counted hidden things.** `Board.fit()` fits only displayed elements (a parked note and the Parked section are `display: none`) and only link bounds whose marks are displayed (each link bound now carries its record id), and leaves free the part of the board the parked band covers on the right and the dock's height at the bottom.
- **The list view said "Section · Parked".** `renderList` lists parked notes under "Parked shelf", leaves them out of the other sections, and leaves the shelf's own section record out of "Shapes, sections and drawings".
- **A note dragged over the band slid under it.** The world carries the pan transform, so it is one stacking layer, below the band's `--z-sticky`. While a note is dragged the world is lifted to `--z-sticky` plus one, so the note is drawn over the band; the board's ground stays under it. Measured in the click-through: the world's `z-index` is 3 during the drag and the element under the pointer over the band is the note.
- **Erasing could not be undone from the bar.** `send()` in `app.mjs` pushes every successful `canvas.remove` made by a facilitator onto the undo stack, with the revision before the removal and the revision the removal returned; Undo sends `item.undo` with `restore_revision` set to the earlier one and says "Put back the drawing." (or "the connector"). It uses the removal's returned revision, so a press within a poll of erasing works before the screen has heard of the removal. Only a facilitator's removals are remembered, because only a facilitator may send `item.undo`.
- **A quote by an unknown voice** (null `speakerActorId`) kept the paper look of a typed note under review, which its "Quote" label contradicted. It takes `--note-accepted-fill` (yellow), the typed note's colour, and claims no person.
- **The rail's Quote button reaches the quote tool.** Verified end to end in the click-through: Quote on a real transcript row made a typed proposal ending in its time, the note was drawn in `--person-1` (the facilitator, whose device sent the audio), and its marker opened the Transcript with the line highlighted.
- **Every merged branch contains `e3545a7`**, checked with `git merge-base --is-ancestor` for each of the seven commits.
- **`tests/threads-browser.mjs` assumed geometry the new layout changed.** It expected a crop's thread dot to move exactly as far as the rail scrolled; the dot sits on the image's edge level with the note when the two overlap vertically, so with the taller board it moved less while being right. The test now puts the image clearly below the note before scrolling, so the dot has to travel with it, and also checks the dot against the tool's own geometry; with the recompute removed it would fail.
- **A press in the photograph's rounded corner fell through to the page** (`canvas-browser` failed to mark a 64px photograph once the taller Display heading moved it). The stage was clipped to `--r-lg`, so a press inside the corner missed it and started a text selection, and the next drag dragged that selection and was cancelled. The image now carries the radius, the marking layer covers the whole stage, and nothing on the stage selects.

### 4.2 Defects found in the click-through and fixed

- **A second invitation within a second was refused** ("Refresh the roster before changing membership"): an invitation moves the roster on and the screen hears of it only at the next poll. `people.mjs` waits, up to three seconds, for the snapshot's roster revision to move past the one the last invitation used.
- **A participant was offered Correct on everyone's proposals**, and Save correction was then refused with a 403: the server lets only a proposal's author or a facilitator edit it. `cardActions` takes `author`; a participant sees Correct only on what they added (their typed notes, and readings of photographs they sent) and otherwise the line "A facilitator accepts or rejects. Only a facilitator or the person who added it can correct it." This revises 0.3's "Anyone else gets Save correction".
- **A participant's console filled with 403s**, one per crop: crops are visible only to the uploader and facilitators, and the client asked anyway. `mayReadCrop(snapshot, sourceId)` in `review.mjs` answers from the snapshot (a facilitator, or the participant whose id is the source's `author_id`); the review rail and the board's details do not ask when it says no and show their "not visible to you" line at once.
- **"Connection problem: client revoked."** after another facilitator deleted the session. `CONNECTION_WORDS` says, for `client_revoked`, "This device can no longer reach the session: it was deleted, or this person was removed. What is on screen is the last thing it saw.", and has plain words for `client_expired` and `client_deleted`. The stale canvas staying on screen remains on the next-pass list (1.4).
- **The composer's field was a few characters wide at 400px** beside its two buttons; under 1024px it takes its own row.
- **Export links kept two media URLs each for the life of the page.** `clearExport()` revokes them when the export page is opened again or a new export is made.

### 4.3 The latent defects 1.4 assigned to this phase

- **Crop URLs are released.** `releaseCrops` in `review.mjs` runs on every queue render and revokes the blob URL of every crop whose card is no longer open (accepted, rejected or gone), and forgets refused crops so a returning card asks again; a fetch still in flight is released when it lands. The photo flow's found list asks for crops only for proposals still waiting, so it cannot fetch a released crop again on every render. Verified twice: `tests/rail-browser.mjs` asserts the accepted card's crop is released and its URL revoked (and fails with the release removed, checked), and the click-through counted live blob URLs falling from 3 to 1 as cards left the queue.
- **An uncertain control command can be resolved without a reload.** The attention banner gained `#attention-actions` with Try again (`retryPendingControl()`, which resends the retained intent with its original control sequence, so the server applies it at most once) and Discard (`discardPendingControl()`, which drops it and forces a fresh read). The banner names the command ("The server may or may not have applied the pause. ..."), hides Dismiss while the choice is offered, and comes back whenever the banner is free while a command is pending, because until someone chooses every control stays refused. Verified in the click-through by aborting a Pause request in the browser: Try again paused the session; Discard dropped it, and the next Pause worked. `app/server/session-sync.mjs` is unchanged.

### 4.4 The screens phase 4 owned

`css/screens.css` was rewritten. Each screen opens on a Display line (`.screen-title`) with one sentence in the Title size under it; parts are separated by space and by `--r-lg` panels on the sunken tone, never by a line round a box; the one yellow primary is the next step.

- Entry: the product's name in Display, then two panels side by side: Join on the proposed note's soft yellow, because most people in a room join, and Start on the sunken tone; fields sit on paper.
- Agreement gate: the Display heading with the session's name under it, the agreement in its own panel (`.gate-agree`, the box and Agree, or once agreed when), then the People rows from `people.mjs`, then Start capture.
- Photograph: the choose step in a panel; the stage hugging the image (the 1px fit the journey asserts is kept) with the radius on the image; marks drawn in the human mark, solid, because dashed is the machine's; the tools in a sticky panel; the found list as cards in each note's coming colour at `-soft` with the full accent as its edge, because each is still a proposal.
- Export: the summary, the choice and Create export in one panel, then the downloads as secondary buttons and the retention line.
- The dialog lost its line: the backdrop separates it (this revises the dialog half of 2.7; menus keep theirs).

Every id and every word the journey and the tests read is unchanged; only classes and wrappers changed (`.screen-title` on the three screen headings, the `.gate-agree` and `.export-choice` panels).

### 4.5 Click-through, flow by flow

A scripted walk (kept outside the repository) in a real browser against the real server on ports 5301 and 3301, with the default fixture extractor and transcriber: the facilitator at 1920 by 1080, a participant in a second browser context at 1440 by 900, and a third member joined from Node to read the record. Screenshots were looked at for the entry, the gate, the empty workspace, the found list, the threads, the uncertain banner, the 400px workspace, the export page and the participant after deletion. Final run: every flow passed.

| Flow | Result |
|---|---|
| Entry; start a session | Pass. Chip "Not started" |
| Agreement gate: tick, Agree, Start capture | Pass |
| Workspace at 1920 by 1080 and at 1440 by 900 | Pass: no scroll either way (scrolled before 4.1) |
| Two invitations in a row | Pass (the second was refused before 4.2) |
| Second device joins as a participant | Pass; three header circles, each filled (empty before 4.1) |
| Listen: transcript arrives, chip "Listening", stop | Pass; "Stand-in transcript" note |
| Type a note and Add; Add and accept | Pass |
| Photograph `IMG_5818(1).JPEG`, mark three notes, fixture reading | Pass; the found list in the note colours (all three yellow, because the fixture names no paper colour) |
| Review: crops first, Correct then Accept, Reject | Pass; corner mark on the corrected note |
| Crop URLs released | Pass (3 live to 1) |
| Participant review: no actions on others' cards, Correct and Save correction on their own note; the facilitator accepts it | Pass (refused with 403 before 4.2) |
| Group two accepted notes and accept the group | Pass |
| Drag a note; the server agrees | Pass |
| Pan and zoom; list view and back | Pass |
| Draw a stroke; erase it; Undo restores it | Pass (Undo could not restore before 4.1) |
| Connect with a label and Shift (directed), and without either | Pass |
| Quote a transcript line through the rail's button; follow its marker | Pass |
| Park by dragging onto the band; the list says "Parked shelf"; fit leaves the band free; Unpark | Pass |
| Select a note: threads to the People row, the group label and its connectors | Pass |
| Scrub the strip: later notes fade, `body.scrubbing`, threads hidden, all cleared on release | Pass |
| Pause and Resume; the rail stays below the header and banner | Pass |
| Keep-alive banner after the tab was hidden; Keep capture running | Pass; "Capture pauses itself in 5:00 ..." |
| Uncertain control: Try again; Discard | Pass (no way out before 4.3) |
| Projector setting | Pass: the title grows from 22px to 27.5px and nothing scrolls |
| 400px | Pass: no sideways scroll, the dock clear of the shelf |
| Participant withdraws: the room pauses with the reason, the participant is back at the gate and agrees again | Pass |
| End session (confirmation), export both formats, delete | Pass |
| Reduced motion (`prefers-reduced-motion: reduce`) | Pass: across adding, accepting, a review accept and listening, no `animationstart` or `transitionrun` fired and `document.getAnimations()` was empty |
| Console errors and failed responses | One expected kind only: after the facilitator deleted the session, the participant's next poll got 401 and the browser logged it. Nothing else |

Not exercised: a real microphone and real speech (the fake device and the fixture transcriber only); a real phone or touch screen (phone width only as a viewport; the coarse-pointer rules were not emulated); the wake-word detector; voice enrolment by hand (covered by `speaker-enrollment-browser.mjs`); a photograph whose reading names a paper colour (the fixture names none, so the found list and the accepted notes were all yellow); the Remove and role buttons in People; anything over a LAN.

### 4.6 Tests, run one after another

- `node --test tests/*-unit.mjs`: 197 tests, 197 pass (board 13, canvas objects 29, connect 13, contrast 52, draw 9, header 12, parked 11, quote 17, rail 9, strip 10, threads 22).
- The eleven browser tests, each alone and one after another: `canvas-browser`, `canvas-objects-browser`, `canvas-objects-server-browser`, `command-recognition-browser`, `header-browser`, `parked-browser`, `quote-browser`, `rail-browser`, `speaker-enrollment-browser`, `strip-browser` and `threads-browser` pass. Before phase 4, `header-browser` and `parked-browser` failed on the merged tree; `rail-browser`, `threads-browser` and `canvas-browser` failed on the way and were fixed as 4.1 and 4.3 say.
- `node tests/journey.mjs`: all 18 steps print `ok`; it then exits 1 on the known EPERM when removing its temporary folder on Windows (0.6).
- `bash app/design-system/spec/audit.sh app/client`, and with no arguments: 13 checks, Clean.
- `python deliverables/documentation/check_proposal.py` (38 F-numbers matched) and `python .github/scripts/check_schema_versions.py` (versions 1 to 6 consistent) pass; phase 4 changed nothing they check.
- CI (`.github/workflows/verify.yml`): the client job runs `node --test tests/*-unit.mjs` from `app/client`, so a new unit test file runs without editing the workflow, and the browser job runs every browser test as its own step, one after another. The workflow itself was not run here. `app/client/package-lock.json` is ignored; none was present.

### 4.7 Left for the next pass

Merged into section 6, with the review's own items, so there is one list.

## 5. Review

Phase 5 judged the client against the brief's sections 3 (character), 4 (the cheap line), 6 (meeting mode), 7 (tools and features) and 11 (done), and the originality test, from screenshots of every state at 1920 by 1080, then fixed what failed. Done on 19 October 2026 on the Windows machine of 2.9 (Node 24.22.0, Python 3.14.0 from `.venv`, Chromium from Playwright in `app/client/node_modules`). The agent that did it built none of the client.

### 5.1 How the screenshots were made

A scripted walk, kept outside the repository as phase 4's was, drove a real browser against the real server on ports 5321 (static) and 3321 (API), with a temporary data folder. It built one realistic session, "Onboarding workshop":

- Anna starts the session in the browser, agrees and starts capture. Sam joins from Node through an invitation Anna made in People, and Anna makes Sam a facilitator from his People row.
- Sam, through the client library: six typed notes accepted and placed, one typed note left waiting for review, a group "Onboarding friction" proposed and accepted, a connector labelled "solved by", and two spoken lines.
- Anna, in the browser: photographs `IMG_5818(1).JPEG` from `evidence/raw/photo-reading/` through the photograph flow and marks the three sticky notes on it (yellow, pink, blue); the fixture reader reads all three; she corrects and accepts two in Review and leaves the third proposed; Place new notes; listens for about 30 seconds; quotes a transcript line and accepts the quote; parks two notes (one dragged onto the margin, one with P); draws a stroke with the pen; connects two notes with Shift (directed) and a label.
- **The transcript is not the fixture transcriber's.** The server ran with `--transcriber whispercpp` pointed at a stand-in whisper.cpp server on 127.0.0.1:8321, a short script in the agent's scratch folder that answers every audio chunk with the next of seven scripted English lines. The real adapter, the real command recogniser and the real transcript rendering ran on those lines; no speech was recognised. One line, "Hey Jarvaids, make a summary of the onboarding risks.", is a recognised command.
- The "reading" screenshot (07) was taken with the browser's poll answers held for 2.5 seconds, because the fixture reader finishes before a screenshot can be taken.
- `06-photo-mark.png` was reduced to a 256-colour PNG (697 KB to 256 KB) to stay under 400 KB; the others are as taken.

The same walk measured every visible text element (its computed size, multiplied by the board's zoom on the canvas, and its colour composited over the backgrounds behind it) and the non-text marks (the dock's icons, the strip's marks), at 16 points in the walk, including the canvas zoomed to 100% and the projector setting on.

### 5.2 The screenshots and the originality test

In `design-review/` at the repository root, 1920 by 1080 unless named, `fullPage: false`, all after the fixes in 5.6. "Mistaken for" names the product the screenshot could be attributed to, or "none".

| File | State | Mistaken for | Judgement |
|---|---|---|---|
| `01-entry.png` | Entry: join or start | none | The name in Display, the join panel on the proposed note's soft yellow. The eye lands on the name, then the yellow Join. A form page, but typographic, not a SaaS sign-in card |
| `02-gate-before.png` | Agreement gate, not yet agreed | none | Display question, the session's name, one sunken panel with the box and Agree, the people with their agreement mark |
| `03-gate-agreed.png` | Agreement gate, agreed | none | Start capture is the one live primary |
| `04-workspace-empty.png` | Empty workspace | none | The flat lilac rectangle at -2 degrees with a Display line. Failed before the fix: two yellow "Photograph the wall" buttons on one screen (5.6, fix 5) |
| `05-photo-choose.png` | Photograph flow: choose | none | One panel, one primary |
| `06-photo-mark.png` | Photograph flow: mark (three marks) | none | Failed before the fix: the tools stood 900px from the photograph at the window's edge (fix 6), and the header's primary competed with "Read 3 notes" (fix 5) |
| `07-photo-reading.png` | Photograph flow: reading ("Waiting to be read") | none | Calm; nothing animates |
| `08-photo-found.png` | Photograph flow: found | none | The crops in the coming note colour. Failed before the fix: the sentence said proposals are "dashed", which they no longer are (fix 7) |
| `09-review-correct.png` | Focused review card, Correct open | none (nearest: FigJam, for the canvas) | Crop first, the field in place with the corner mark, Accept, Keep original, Reject; the focused card carries the one shadow |
| `10-workspace-session.png` | Workspace with the session | none (nearest: FigJam) | Fits at 77% (44% before fixes 9 and 10). Proposed notes askew in soft yellow with the mono marker, accepted notes full and straight with their stamp, the strip's marks along the bottom |
| `11-rail-review.png` | Rail: Review tab | none | Count chip in mono, ink underline |
| `12-rail-transcript.png` | Rail: Transcript tab | none | Speakers in their `-deep` accent, mono times, the newest line on mint-soft, the command on periwinkle-soft. Failed before the fix: an empty band inside every command row (fix 8) |
| `13-rail-people.png` | Rail: People tab | none | 24px circles, the invitation code in mono |
| `14-note-threads.png` | A selected note with threads | none | Threads to Sam's People row and to the connector. Failed before the fix: selecting a note pushed the whole board down 44px (fix 4) |
| `15-strip-scrub.png` | The strip open while scrubbing | none | The quote accepted after the moment fades to 20%; four lanes and the cursor's time |
| `16-dock-draw.png` | Dock with Draw active, a stroke being drawn | none (nearest: FigJam, for the pen) | The dock sits bottom left, not FigJam's bottom centre, and carries the view toggle |
| `17-connector-label.png` | Connector label field open | none | Directed (Shift) from the group to the waiting note, "could fix" typed. Failed before the fix: after the stroke was drawn, the lane carried both waiting notes off the screen (fix 11) |
| `18-parked.png` | Parked margin with two notes | none | Two compact cards at `-soft`, straight, with Unpark |
| `19-header-listening.png` | Listening in the header | none | Ink chip, three mint bars, mono timer; the rail switches to Transcript |
| `20-paused.png` | Paused, with the capture banner | none | 40px banner with Resume capture; Photograph the wall and Listen disabled |
| `21-keepalive.png` | Keep-alive banner | none | "Capture pauses itself in 5:00 unless a facilitator keeps it running." |
| `22-projector.png` | Projector setting on | none | Chrome type at 1.25. Failed before the fix: notes ran into each other and stamps were hidden under the next note (fix 3) |
| `23-session-menu.png` | Session menu | none | The menu alone is an ordinary dropdown, kept small; the screen is not |
| `24-end-confirm.png` | End-session confirmation | none | The dialog alone is an ordinary confirmation, deliberately; the screen behind it is not |
| `25-export.png` | Export page | none | Display heading and one panel; the header's primary takes the secondary look here (fix 5) |
| `26-list-view.png` | List view | none (before the fix: a Notion database list, or any admin table) | Failed the originality test before fix 12: a status column, Body text and a hairline under every row. Now the words in the Note style, separated by space |
| `27-workspace-400.png` | Workspace at 400 by 860 | none | Header in three rows, the rail above the board; no sideways scroll (measured: 0px) |

Reduced motion is not a screenshot: with `prefers-reduced-motion: reduce` emulated, the walk accepted a reading in Review, added and accepted a note, and listened; no `animationstart` or `transitionrun` event fired and `document.getAnimations()` held no running animation.

### 5.3 The cheap line (brief section 4)

Checked in every screenshot and in the source of `app/client` (not `node_modules`, `fonts` or `dev/`):

- No tape, pushpin, paperclip, torn edge, paper texture, wood or cork: none in any file or screenshot.
- Rotation: proposed notes are clamped to plus or minus `--note-max-rotation` (1.5 degrees, `primitives.css`); accepted, parked and typed-waiting notes are `rotate: 0deg`. Other rotations are not notes: the empty-state rectangle (-2 degrees, the brief's own number), a proposed group or section (-1 degree), the failed glyph's square (45 degrees) and the strip toggle's chevron (180 degrees).
- Shadows: one token, `--shadow`, on the dock, a dragged note, a dragged parked card and the focused review card; nothing else.
- Gradients: one `radial-gradient`, the board's dots (2.7, 3.2); no colour ramp. No `backdrop-filter`, no blur, so no glassmorphism.
- Emoji: none (scanned for pictographic code points).
- No decorative illustration in a working area.
- The sticky note stays under FigJam's: flat fill, `--r-lg`, no curl, no shadow at rest.

No failures.

### 5.4 Meeting mode at 1920 by 1080 (brief section 6)

**Smallest text, measured.** The floor is 13px in the chrome and 15px on the canvas for anything that carries meaning.

| Region | Before the fixes | After |
|---|---|---|
| Header | 12px (the people circles' initials, Mono) | 13px (initials, "everyone agreed") |
| Rail | 12px (the review count, transcript times, card times, agreement times) | 13px |
| Dock | 12px (the zoom level) | 13px |
| Strip | 12px (start and end times, lane words, cursor time) | 13px |
| Parked margin | 12px (the count) | 13px (title, count, hint, Unpark) |
| Pages (entry, gate, photograph, export) | 12px (People rows' agreement time) | 13px |
| Canvas at 100% zoom (CSS size) | 12px (the "Proposed" and "Not yet reviewed" markers, the "Accepted by" stamp) and 13px (kind line, buttons, group and connector labels, lane label) | 15px (all of those); note text 18px |
| Canvas at this session's Fit zoom | 5.3px at 44% | 11.6px at 77% (note text 13.9px) |
| Projector setting, chrome | 15px | 16.3px |

Every region now passes at the design size. **The canvas still fails the 15px floor whenever Fit zooms below 100%,** which it must once the wall is larger than the board: in this session at 77%, the smallest canvas text renders at 11.6px. Fixes 9 and 10 took the same session from 44% to 77%; no type size can pass at every zoom, because a wall keeps growing. A person reading from the back of the room zooms to the part under discussion, or uses the projector setting, under which Fit may now go to 125%. What the board should do for the back of the room on a large wall is on the next-pass list (6).

**Could it stay on a projector for an hour unnoticed?** Nothing on screen moves on its own: the listening bars run only while this device listens, the keep-alive countdown only while that banner shows, and the strip never animates. Before fix 4, selecting a note moved the whole board 44px down, which a room would notice at every click. The board hint line under the canvas stays on screen permanently; it is quiet (13px, `--ink-2`) but it is instruction text on a projector (next pass).

**Read at a glance from the back?** The session's title (22px, Title), the state chip and "Photograph the wall" read; the chip reads by fill as well as by word. The canvas reads at 100%; at this session's 77% even the 18px note text renders at 13.9px, under the floor, and the stamps at 11.6px.

**Hierarchy.** In the workspace the eye lands on the yellow notes, then the review rail's crop, then the yellow primary in the header: the work, then the evidence, then the next action, which is the intended order. Before fix 5 the eye split between two identical yellow buttons on the empty board and on the photograph and export pages.

**Region defaults (section 6) as built:** header with the Title, one chip, the participant line and the one filled primary; the 40px capture banner; the canvas on `--paper` with 1px `--line` dots on a 24px grid; the dock floating bottom left; the empty state's lilac rectangle at -2 degrees; notes at least 200px wide with 16px padding and `--r-lg`, the mono "Proposed" marker and deterministic rotation; the rail 360px on `--paper-2`, tabs under an `--ink` underline, the count in a chip; review cards evidence first, text second, actions third; the transcript's speakers in `-deep`, mono times, current line `--mint-soft`, commands `--periwinkle-soft`; People with 24px circles. All present in the screenshots.

### 5.5 Contrast (WCAG AA), measured in the page

The walk read each visible text element's computed colour, composited it over every background behind it, and computed the ratio; `tests/contrast-unit.mjs` (52 tests, passing) asserts the token pairs. The lowest of each pair seen, after the fixes, need 4.5:1 unless marked:

| Pair | Where | Ratio |
|---|---|---|
| `--mint-deep` on `--paper-2` | Sam's name in the transcript | 4.51 |
| `--ink-3` on `--paper-2` | strip lane words, parked hint, strip quote mark | 4.52 |
| `--mint-deep` on `--paper` | "Accepted" status word | 4.88 |
| `--ink-3` on `--paper` | agreement time, "Not yet reviewed" marker | 4.89 |
| `--yellow-deep` on `--paper` | "Waiting" status word | 5.20 |
| `--ink-2` on `--periwinkle-soft` | group label on its rectangle | 5.35 |
| `--lilac-deep` on `--paper-2` | Anna's name in the transcript | 5.40 |
| `--coral-deep` on `--paper-2` | Remove in People | 5.73 |
| `--ink-2` on `--yellow-soft` | proposed marker, kind line, stamp on a proposed note | 5.82 |
| `--ink-2` on `--mint-soft` | time on the current transcript line | 6.01 |
| `--ink-2` on `--paper-2` | dock's List, rail text | 6.10 |
| `--paper` on `--coral-deep` | End session in the dialog | 6.20 |
| `--ink-2` on `--paper` | "Not started" chip, hints | 6.60 |
| `--ink` on the primary hover | Create export | 9.73 |
| `--ink` on `--lilac` | Anna's initial, the quote note's text and stamp | 9.88 |
| `--ink` on `--yellow` | accepted notes, the primary | 11.83 |
| `--ink` on `--mint` | Sam's initial | 12.97 |
| `--ink` on `--line` | a pressed secondary button | 13.87 |
| `--ink` on `--periwinkle-soft` | a command row | 13.95 |
| `--ink` on `--yellow-soft` | proposed note text, paused chip, parked cards | 15.19 |
| `--ink` on `--mint-soft` | "Session open" chip | 15.70 |
| `--ink` on `--paper` and `--paper` on `--ink` | everything else; the listening chip; the dock's pressed tool | 17.23 |

`--ink-2` and `--ink-3` never sit on a full accent: on full accents the note's secondary lines are `--ink` (2.7), and the walk found no `--ink-2` or `--ink-3` text on any of the five full accents. Disabled controls (40% opacity) are exempt and were left out.

Non-text marks need 3:1. The dock's icons: `--ink` on `--paper` 17.23, `--paper` on `--ink` for the pressed tool 17.23, `--ink` on `--paper-2` while hovered 15.92. The strip's marks on `--paper-2`: photograph square `--ink-2` 6.10, quote line `--ink-3` 4.52, accept circle `--yellow` 1.35 with its `--ink-2` ring at 6.10, and the command bar `--periwinkle` 1.86, which **failed**: it had no ring and the closed strip has no lane word beside it. It now carries the same `--ink-2` ring (fix 13). The attention marks (coral, mint) stay under 3:1 beside the sentence that carries their meaning, as 4.1 accepted.

### 5.6 Fixes, and why

Each fix uses tokens only and keeps every id, class and data attribute the tests use.

1. **Mono 12px to 13px** (`tokens.css`, `--fs-mono`). It was the smallest text in every chrome region and failed the 13px floor; the header's initials, times, counts, the zoom level and the strip all read it.
2. **The canvas's own type** (`tokens.css` `--fs-canvas-*`, rebound inside `.world` in `css/canvas.css`). Small and Mono on the canvas are 15px (bound to Body), so the markers, stamps, kind lines, labels and the note's buttons meet the 15px floor at 100%. One rebinding inside the world reaches every rule that draws there.
3. **The projector acts through the board's zoom on the canvas** (`tokens.css`, `css/canvas.css`, `board.mjs` `roomZoom`, `app.mjs` `setRoom`). Type grown by a quarter at fixed note places made each note a quarter taller and ran it into the next, hiding stamps (seen in `22-projector.png` before the fix). Now the canvas's type stays at one scale, Fit may zoom to 125% with the projector on, and toggling the setting multiplies a person's chosen zoom by the same step. This revises 2.6.
4. **The selection row floats over the board's top left** (`css/canvas.css`, 1024px and up). In the flow it pushed the whole board down 44px at every selection, which a room would notice. Paper with the menus' hairline, not the shadow.
5. **One filled primary per screen.** The empty state's "Photograph the wall" is secondary (`index.html`), because the header's is the brief's only filled primary; this answers 4.7's open item. On the photograph and export pages the header's button takes the secondary look (`css/header.css`), because the step's own action is the primary there; the class stays, so the header test still finds it.
6. **The photograph's tools stand beside it** (`css/screens.css`): a `max-content` column instead of `1fr`, so a portrait photograph no longer leaves 900px of empty paper between itself and its tools.
7. **The found step's sentence** (`photo.mjs`) said proposals are "dashed"; it now says they are marked Proposed and slightly askew, which is what the canvas draws.
8. **The transcript row's head stays on one line** (`css/rail.css`). It wrapped, and the hidden Quote button took a line of its own, an empty band inside every command row; the time and name no longer shrink, and the badge wraps inside itself.
9. **Place new notes fills across, then down** (`app.mjs` `arrange`). It put each new column 352px right of the rightmost note, so the wall only grew sideways and Fit fell to 44%. Columns now go into slots 384px apart across the board's width at 100%, each into the slot whose lowest note is highest.
10. **Fit after the parked notes are hidden** (`tools/parked.mjs` `markBoard`). Until a person pans or zooms, the board fits on every render, and that fit ran before the parked tool hid the parked notes, so it fitted notes nobody could see (52% where 77% fits). The tool fits again when its marking changed something.
11. **Strokes do not move the lane** (`board.mjs`). The lane for unplaced notes sits left of the leftmost placed object; a stroke drawn left of the wall moved it, and the two notes waiting for review jumped off the screen mid-session.
12. **The list reads as the minutes** (`css/canvas.css`): words in the Note style, rows separated by space with no hairline, Review under the words it reviews. It failed the originality test as an admin table.
13. **The strip's command bar carries the `--ink-2` ring** (`css/strip.css`), as the accept circle does: 1.86:1 alone, 6.10 with the ring.
14. **A note's buttons show when a hand is on it** (`css/canvas.css`): hovered, focused, selected or with details open, always on a touch screen, keeping their place so nothing moves. With 15px buttons, a wall of notes carried two buttons each and read as a dashboard; the rail holds every review action. Notion's "hover states that reveal rather than shout".
15. **The strip's lane words are line-height 1** (`css/strip.css`). At 13px Mono the four lane words stacked the open strip to 99px, past `--strip-h-open` (96px); `tests/strip-browser.mjs` caught it.

**What the fixes did not touch.** Rotation angles (-2, -1, 45 and 180 degrees) and the world coordinates in Place new notes (320, 64, 24, 40) are literals outside the token file, as they were before this phase; the brief's rule names colour, size and duration, and these are angles and world positions, but binding them is on the next-pass list.

### 5.7 The three signature moves (1.1) and the section 7 features

- **A note points to where it came from.** Visible the moment a note is selected (`14-note-threads.png`: a thread to the People row of Sam, who accepted it, and to its connector). By design nothing is drawn without a selection. At 1px in `--ink-3` the thread is quiet: it reads at a desk; from the back of a room it was not verified.
- **Accepting is the loudest thing.** Visible in every workspace screenshot without being pointed out: the proposed notes are soft, askew and marked "Proposed" in mono; the accepted ones are full, straight and stamped "Accepted by Anna 04:52". The motion (settle, fill, swell) cannot be seen in a still; reduced motion was verified to run none of it.
- **Time runs along the bottom.** The strip with its marks is in every workspace screenshot; `15-strip-scrub.png` shows a later note fading.
- **Section 7:** the drawing tool (16), the connector tool with label and direction (17), the session strip (15), quote notes (the lilac "Quote · Anna" note in 10, from the transcript line in 12), the parked margin (18), and the invented provenance threads (14). Both required tools and four features are built and visible.

### 5.8 Brief section 11, done

- Every flow works: the walk passed through all of them with no console error and no failed request, and every test passes (5.9).
- No hard-coded colour, size or duration outside the token file: the audit is Clean; the angle and world-coordinate literals are recorded above.
- Nothing from section 4 anywhere (5.3).
- Both required tools and at least three section 7 features (5.7).
- The three signature moves visible (5.7).
- The originality test: no screenshot can be attributed to an existing product after fix 12 (5.2).
- Every text-on-colour pair passes AA (5.5).
- `prefers-reduced-motion` respected (5.2).
- No open questions in this file.

### 5.9 Tests after the fixes, run one at a time

- `node --test tests/*-unit.mjs`: 197 tests, 197 pass.
- Each browser test alone, one after another: `canvas-browser` (15 steps ok), `canvas-objects-browser` (1440 and 400px), `canvas-objects-server-browser` (5 steps ok), `command-recognition-browser`, `header-browser`, `parked-browser` (11 steps ok), `quote-browser` (12 steps ok), `rail-browser`, `speaker-enrollment-browser`, `strip-browser` and `threads-browser` pass. `strip-browser` failed once, on fix 1 (the open strip measured 99px), and passes after fix 15.
- `node tests/journey.mjs`: all 18 steps print `ok`, then it exits 1 on the known EPERM removing its temporary folder (0.6). Run twice.
- `bash app/design-system/spec/audit.sh app/client`: 13 checks, Clean.

### 5.10 What could not be verified

- A real projector, a real room and its back row: the meeting-mode sizes are measured in pixels at 1920 by 1080, not read at a distance.
- Real speech: the transcript came from a scripted stand-in recogniser (5.1), and the microphone was Chromium's fake device.
- A photograph whose reading names a paper colour: the fixture names none, so every note read from the photograph is yellow.
- A touch screen or phone: 400px was a viewport only, and the touch rules (buttons always shown, 44px targets) were not emulated.
- The reading step at its natural speed: the screenshot held the poll answers back (5.1).
- CI itself was not run.
- Whether the character reads as "editorial, warm, attentive" to anyone but the reviewing agent: no person has looked at these screenshots yet.

## 7. After the first look

Pieter looked at the redesigned client on the morning of 19 October 2026 and named three things. Each is decided and built here; nothing in sections 0 to 6 is reopened except where this section says so.

### 7.1 Photographing the wall is a sheet, not a page

The photograph flow was its own screen (`#screen-photo` replaced the workspace). In a room that means the wall disappears from the projector for as long as someone chooses a photograph and marks it, and everyone else's canvas is out of reach on that device.

Now `#screen-photo` is a sheet over the workspace (`css/screens.css`, `.sheet-layer` and `.sheet`): paper on the backdrop, the large radius, no line and no shadow, as the confirmation is, because the backdrop already separates it. The workspace keeps rendering under it; `app.screen` stays `"workspace"`. Close, Escape and a press on the backdrop close it. It is a sheet and not a drawer because marking needs the width of a landscape photograph with the tools beside it (section 5, fix 6); a drawer of the rail's width would turn a wall of thirty notes into thumbnails nobody can mark. Its width is `--sheet-max` (1120px); the photograph's height is limited to the window less `--sheet-chrome`; past that the sheet scrolls inside itself. Below 1024px it rises from the bottom edge.

The id stays, so the header's rule that demotes its own "Photograph the wall" while the sheet shows (section 5, fix 5) still applies, and the journey and the canvas test still wait on `#screen-photo:not([hidden])`.

### 7.2 The reading is followed from a card in the corner

Sending the photograph closes the sheet at once. The reading (waiting, reading, found with each note's crop and words, or why not and Try again) is followed from `#photo-reading`, a card fixed at the bottom right (`.reading-card`): paper, the large radius, the one shadow, because it floats as the dock does. It is not a toast: it never leaves on a timer. It stays until Dismiss, or until Review them, which opens the rail's Review tab, and "Photograph another" opens the sheet again from it. Its list scrolls inside the card past a few notes. The canvas, the rail and the composer stay in use while a reading runs, which is the point: reading takes seconds and the room should not stare at a page meanwhile.

`photo.mjs` renders the card on every render while it shows, following the job id in `app.photoJob` as before; `app.mjs` no longer has a `"photo"` screen.

### 7.3 Dropping a note no longer jumps

Dragging a note did follow the pointer, but on release the note went back to where it was and jumped forward up to a second later. The cause: the reply to `item.place` is not merged into the sync library's snapshot, so the render after the command still drew the server's old position, and the next poll moved the note. Three changes, all in the client:

- The board keeps where a person dropped a note (`board.mjs`, `placed`, read by `#dropped` on every render) until the server's snapshot carries a newer position revision for it; a refused move clears it and puts the note back, as before. Group membership and the hull still follow the snapshot, so a note dropped into a group fills its colour when the poll lands, which is the honest moment.
- The sync library gained `pollSoon()` (`app/server/session-sync.mjs`): the next read is brought forward to now, and a read in flight is left alone. `app.mjs` calls it after every command sent outside the control lane, so what a person did shows as soon as the server has it. Unit test in `app/server/tests/session-sync-unit.mjs`.
- A press on a note prevents the browser's default (`board.mjs`, `pointerdown`), so a drag no longer selects the note's words as the pointer travels. The journey's drag step now checks that the note follows the pointer and that it does not move in the 1.8 seconds after the drop.

### 7.4 Tokens added

`--sheet-max`, `--sheet-chrome`, `--reading-card-w`, `--z-card` (25, above the dock, below the header) and `--z-sheet` (35, above the header, below the menu). `--stage-chrome` is no longer read by the client and is left in place for the design system's record.

## 6. Next pass

One list: phase 4's items (4.7) and the review's.

- **The canvas at the back of the room.** Below 100% zoom the canvas falls under the 15px floor (5.4); a wall of 30 notes cannot fit a 1270px board at 100%. Options to judge with a person at a projector: a follow mode that keeps the newest activity at 100% and pans to it, or a Fit for the room that never goes below about 85% and shows the most recent part of the wall.
- **Threads at a distance.** 1px `--ink-3` may be too quiet from the back of a room; measure on a projector before thickening, because they cross other regions.
- **The board hint line** stays on screen for the whole session; hide it after the first pan or zoom, or fold it into the dock's tooltips.
- **The selection row** floats over the wall's top left while open and can cover the first group's label; place it against the selection instead.
- **The transcript's command status** above the rows repeats the newest command row's feedback.
- **Literals outside the token file:** the rotation angles (-2, -1, 45, 180 degrees) and Place new notes' world coordinates (320, 64, 24, 40, and `board.mjs`'s lane and fit margins); read them from tokens as the accents are read.
- **The projector on a crowded wall** grows only the chrome, because Fit is limited by the content; judge on a projector whether that is enough.
- A session deleted elsewhere still leaves the last canvas on screen, now with honest words (4.2); the client accepts only a localhost server (`allowLan`); a reload loses the device's credential. Each needs a product decision or a backend change (1.4).
- The board does not refit when the window is resized after a person has panned or zoomed, and until a person pans or zooms it refits on every render, so a note unparked beside the band can shift.
- Notes read from a photograph were only seen in yellow, because the fixture names no paper colour.
- Undo of an accepted note still reads the item's status from the snapshot, so a press within a poll of accepting does nothing; the removal path no longer has this race.
- Canvas tones in `css/canvas.css` name their full accents (`--periwinkle`, `--lilac`, `--mint`, `--coral`) rather than roles; a `--tone-*-full` role per tone would finish 2.2's rule that components use roles.
- The coarse-pointer layout and the projector setting on a real projector were not checked by eye.
- Folding this design into `app/design-system/` (1.3), and the three persistence endpoints (1.4).
