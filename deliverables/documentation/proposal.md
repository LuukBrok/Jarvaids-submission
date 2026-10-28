# Jarvaids: what it is, who it is for, and where every function stands

**What this is:** the one page a reader can start from. Every function from the
initial brief, who it serves, and where it stands today, with the file that
establishes each status named beside it. It binds to its sources rather than
copying them, because two copies of the same list drift within a week and
nobody diffs documents.

**How to read a status.** Four words, and only four, so the table can be
counted: **built**, **plumbing**, **proposed**, **open**. Their definitions are
under the table. Nothing here was written from memory: each status was read
from the file named in its row, and `check_proposal.py` next to this file
fails the build if a function is missing, invented, or given a fifth word.

**The one thing to know before the table:** no handwriting recognition and no
speech recognition has ever run in this project. The only extraction adapter is
`FixtureExtractor` and the default transcriber is `FixtureTranscriber`, both
visibly synthetic (`deliverables/documentation/stack.md` section 4,
`app/server/BUILD-STATUS.md`). Nothing that depends on either is built.

---

## 1. What it is, in the concept's own words

> A meeting-time assistant that keeps a live, searchable record of a design
> session and writes back into the board the team is already using, so that what
> was said, sketched and stuck on the wall ends up in one place while the
> session is still running.

That is the opening sentence of `ideation/concepts/001-jarvaids-meeting-assistant.md`,
which remains the concept of record. `deliverables/documentation/flowchart.md`
is the working map of the same idea and defines the F1.1 to F6.6 numbering this
table uses.

## 2. Who it is for, and when

Design teams in a working session: a workshop, a sprint review, a concept
critique. Two to eight people, a wall or a whiteboard, one or two hours,
usually with sticky notes and always with more said than written down
(`ideation/concepts/001-jarvaids-meeting-assistant.md`, "Who it is for, and
when"). The server enforces that size: at most eight current members per
session (`app/server/README.md`, "Limits and failure behaviour").

Two roles, and the split is F4.3 in the flowchart: a **facilitator** can steer
the tool and change modes, **participants** can add and ask. The server adds a
third, `viewer`, who may read but not contribute (`app/server/API.md`,
"Commands", `participant.role`). Who may command the tool is still an open
question in `flowchart.md`: anyone is chaos, only the facilitator is a
bottleneck.

It is not built for the meeting as a whole. It is built for three seconds,
quoted from the concept:

> 1. "What did Sanne say about that twenty minutes ago?" and nobody can find it.
> 2. The wall is full of sticky notes and someone has to photograph and retype
>    them afterwards, which either takes an hour or does not happen.
> 3. The meeting ends and the board is a graveyard: the artefacts survive, the
>    reasoning does not.

**What the Week 3 material adds.** The closing section of
`deliverables/week4-midpoint/annotations/INDEX.md` lists ten points the
annotations make for the proposal. Five of them bear directly on who this is
for and what it must do, cited by its item number there:

- **Item 1.** During the meeting, not after it, is the one claim the material
  states plainly, and it is the whole differentiator.
- **Item 2.** The tool makes the first clusters and the group corrects them by
  dragging, during the session: the product's rule came from the group before
  it came from the build.
- **Item 3.** What was said and what the model proposed must be distinguishable
  on sight. The group is certain of that and has not decided how.
- **Item 5.** Trust breaks on provenance, and a plausible wrong reading is more
  dangerous than an obviously broken one, so a stand-in reading must be
  labelled out loud and every item must carry its source.
- **Item 7.** Wrong grouping is the failure named first, ahead of misread
  words, so clustering should be the more cautious of the two.

Two cautions from the same list belong here rather than in a footnote. **Item
8** holds three questions open on purpose: when suggestions appear, what wins
when general advice contradicts an earlier project decision, and how an agreed
task differs from one merely mentioned. **Item 10** warns that the interview
findings reach this proposal through a report the group itself found
flattening, so they are cited through that report, not quoted from the room.
The annotations are themselves an unreviewed draft: every row of that index
says "No, AI draft" in its last column.

## 3. The rule everything follows from

**Anything a model made is provisional until a human accepts it, and it is
never rendered as if a human made it.** It is the central rule of
`flowchart.md`, where a dashed outline on a box means a model runs at that
stage, and it is the reason the canvas draws items made by the team solid and
items made by the model dashed. The design system turns it into three hard
rules with their reasons: `app/design-system/spec/forbidden.md` rule 16, never
render model output identically to team output, because broken once it makes
the product dishonest; rule 17, never grey out a provisional item, because
unreviewed is not unimportant and greying it makes it harder to review; and
rule 18, never use a fill to encode provisional status, because the signal is
the stroke plus label. Planned F3.8 topic fills are a separate, labelled grouping
channel; the palette and interaction are not implemented by this documentation. The product enforces it in code as well as in prose: the client treats
every origin except `human` as provisional rather than testing for machine
names it might not recognise (`decisions/decision-log.md`, 2026-09-22).

## 4. Every function, with its status

One row per F-number in `flowchart.md`. The function column carries the
flowchart's short name only, not its description, so this table binds to the
flowchart instead of copying it: read `flowchart.md` section 3 for what each
one does and what its main risk is.

| F-number | Function | Who it serves | AI? | Status | Evidence |
|---|---|---|---|---|---|
| F1.1 | Live audio capture | The room | No | plumbing | `BUILD-STATUS.md` section "F1.1-F1.3 audio": `source.audio` contract and `capture-audio.mjs`; `test_audio_capture_requires_active_session`; `capture-audio-unit.mjs` 4/4 on the DOM-free `Chunker` only. The getUserMedia and AudioWorklet half has never run in a browser |
| F1.2 | Speech to text | The record | Yes | plumbing | `BUILD-STATUS.md` "Not run, not verified": `FixtureTranscriber` is synthetic and deterministic; `LocalWhisperTranscriber` was written and never constructed. `gaps.md` G2. No speech recognition has run |
| F1.3 | Speaker separation | The record | Yes | plumbing | `API.md` "Commands": `attribution: per_connection`, the sending credential is the speaker. `decisions/decision-log.md` 2026-09-22 records it as a concept-level cut, not diarisation |
| F1.4 | Photograph intake | Participant | No | built | `API.md` `source.image`; `test_intake_strips_metadata_and_appended_bytes`, `test_corrupt_and_multiframe_images_are_rejected`; the photo path is walked in `app/client/tests/journey.mjs` |
| F1.5 | Note segmentation | The record | Yes | proposed | `pipelines.md` section 2 stage S6 and `stack.md` row "Note segmentation, F1.5". Today a person draws the boxes (`source.regions`, `test_fixture_extraction_and_manual_region_repair`); nothing splits a wall automatically |
| F1.6 | Handwriting reading | The record | Yes | plumbing | `README.md` "Scope that remains separate": no live OCR. The adapter boundary, queue, cancellation and manual repair path are tested (`test_manual_crop_transcription_without_adapter`, `test_unreadable_crop_requires_human_transcription`); `gaps.md` G3 records that no OCR has ever been performed |
| F1.7 | Typed input | Participant | No | built | `API.md` `source.text`; `test_typed_accept_reject_export_restart`; a typed note through review with a correction is the spine of `app/client/tests/journey.mjs` |
| F2.1 | Rolling minutes | The record | Yes | proposed | `pipelines.md` section 6, which names F2.1 in its covered functionalities. `gaps.md` G2 records it as absent from the backend |
| F2.2 | Decision extraction | The record | Yes | proposed | `pipelines.md` section 6. No record kind, command or test exists for a decision |
| F2.3 | Action items and owners | The record | Yes | proposed | `pipelines.md` section 6. The review queue exemplar draws one (`spec/exemplars/review-queue.html`); nothing produces one |
| F2.4 | Open question tracking | The room | Yes | proposed | `pipelines.md` section 6 |
| F2.5 | Command detection | The room | Yes | proposed | `pipelines.md` section 3, stage S1, and `stack.md` row "Wake phrase, F2.5". `stack.md` section 3 holds the gate test that decides whether the command pipeline is the core at all |
| F2.6 | Intent parsing | The room | Yes | proposed | `pipelines.md` section 3 stages S4 to S5, and `stack.md` row "Intent and slots, F2.6". Referent resolution is named there as the hardest unsolved piece |
| F2.7 | Grounded question answering | The room | Yes | proposed | `pipelines.md` section 5, and `stack.md` row "Retrieval, F2.7". FTS5 is in the database already; nothing queries it for an answer |
| F2.8 | Live suggestions | The room | Yes | open | `stack.md` section 4: "No proactive suggestion. F2.8 and F4.4 are left open on purpose." The anchoring risk in concept 001 has not been tested, and `flowchart.md` carries the question unanswered |
| F3.1 | Canvas data model | The record | No | built | `API.md` "Position" and "Proposals and items"; `db.py` `SCHEMA_VERSIONS` 5, positions in their own table; `test_where_an_item_is_has_exactly_one_answer`, `test_a_delta_carries_the_position_of_a_record_it_returns` |
| F3.2 | Form selection | The room | Yes | proposed | `API.md` "Clusters": timeline, flow, hierarchy and matrix are refused, `cluster` is the only form implemented, and it is a reviewed proposal a person creates. `pipelines.md` section 4.2 proposes the selection itself |
| F3.3 | Automatic layout | The room | Yes | proposed | `stack.md` row "Layout, F3.3": d3-force, ELK or dagre, candidate, nothing run. `API.md` "Clusters" records that collision and visibility rules are not enforced and cannot be without a change of decision |
| F3.4 | Non-destructive insertion | Participant | No | built | `test_the_layout_engine_may_not_move_what_a_person_placed`, `test_a_machine_placement_is_not_owned_until_a_person_moves_it`; `API.md` "Clusters": a machine placement onto a hand-placed record is refused |
| F3.5 | Provisional styling | The room | No | built | `app/client/app.mjs` draws anything not written by a person with the `provisional` class; `audit.sh` checks "provisional is never dimmed" and "provisional is never a plain fill"; `decisions/decision-log.md` 2026-09-22 on testing origin against `human` |
| F3.6 | Direct manipulation | Participant | No | built | Drag to `item.place` in `app/client/app.mjs`, driven in `journey.mjs`; `test_a_participant_moves_their_own_note_without_review`, `test_any_editor_moves_an_item_into_a_group_without_review`. The client has drag and in-place correction, no pan or zoom |
| F3.7 | Undo | Facilitator | No | built | `API.md` `item.undo`; `test_undo_rejects_stale_client_and_preserves_history`, `test_undo_restores_text_without_restoring_a_position`. Server command with tests; there is no undo control in the client yet |
| F3.8 | Expandable sticky notes | The room | No | proposed | `app/design-system/spec/expandable-notes.md`: main points, in-place detail, stable topic/choice colours, group labels and a key. Interaction, palette and contrast validation remain future work |
| F4.1 | Create and join | Facilitator | No | built | `API.md` "Joining and lifecycle compatibility"; `test_join_retry_is_bound_to_exact_credential_and_payload`, `test_concurrent_redemption_has_one_member`, `test_expired_invitation_creates_no_member` |
| F4.2 | Live multi-user view | The room | No | built | Bounded polling with deltas: `test_a_client_can_rebuild_board_order_from_deltas_alone`, `test_a_delta_does_not_grow_with_the_board`, two-client journeys in `tests/client_http_check.py`. `tests/measure_sync.py` holds both fixtures under the 5 KB budget, at 1660 B per client positioned when run here on 22 September 2026. Sub-second on a real network is unmeasured: that figure is loopback on one machine, and the tool says so in its own output |
| F4.3 | Roles | Facilitator | No | built | `API.md` `participant.role`, facilitator, participant and viewer; `test_last_facilitator_cannot_be_removed`, `test_unrelated_and_demoted_members_cannot_read_images_or_crops`. Who may command the tool stays open in `flowchart.md` |
| F4.4 | Mode switch | Facilitator | No | open | `stack.md` section 4: F2.8 and F4.4 are left open on purpose, so that adding suggestion later costs one new trigger and nothing else |
| F4.5 | Agenda anchoring | The record | Yes | proposed | `pipelines.md` section 6, which names F4.5 in its covered functionalities. The session setup exemplar has a field for an agenda; nothing reads it |
| F5.1 | Canvas export | The record | No | proposed | `stack.md` row "Canvas export, F5.1": headless Chromium for PNG and PDF, candidate. What exists today is JSON and Markdown (`app/client/app.mjs`, `API.md` "Export and deletion"), not a picture of the canvas |
| F5.2 | Minutes export | The record | No | built | `API.md` "Export and deletion"; `test_export_is_frozen_and_escapes_html`, `test_export_marks_and_excludes_unresolved_explicitly`. It exports accepted items and their references as Markdown or JSON. The decision, action and open-question categories depend on F2.2 to F2.4, which are proposed, so what a reader gets today is items, not minutes |
| F5.3 | Board integration | The record | No | proposed | `pipelines.md` section 7 stage S7 and `stack.md` row "Board push, F5.3": Miro REST API v2, candidate, marked "To verify". `stack.md` section 4 rules out FigJam for the first version and asks for one day against the real API before committing |
| F5.4 | Searchable archive | The record | Yes | proposed | `pipelines.md` section 5 names F5.4 among its covered functionalities. Retention today deletes a session after 24 hours by default (`README.md`), so an archive is a decision against the current retention design, not an addition to it |
| F6.1 | Consent gate | Participant | No | built | `test_capture_requires_agreement`, `test_withdrawal_preserves_other_agreement_and_blocks_activation`, `test_join_requires_current_policy`; agreement before capture is asserted in `app/client/tests/journey.mjs` |
| F6.2 | Local processing | Participant | No | plumbing | `stack.md` section 1: nothing runs from the transcriber boxes into the external gate, by design. The audio path keeps bytes on our server and the only transcriber that has run is the synthetic fixture, so there is no transcription to keep local yet. `gaps.md` G2 |
| F6.3 | Citation to source | The record | No | built | `API.md` "Commands": every transcript segment carries a provenance object, and every proposal carries 1 to 60 current references; `test_refresh_stale_proposal_preserves_origin`, `test_accepted_crop_edit_checks_region_binding`, `test_removed_crop_cannot_be_rebound_by_text_edit` |
| F6.4 | Degradation behaviour | The room | No | built | `test_a_failing_transcriber_writes_a_visible_gap_not_a_silent_drop`, `test_job_completion_over_budget_has_no_partial_proposals`, `test_late_result_after_pause_cannot_commit`, `test_storage_limit_does_not_block_pause_or_close`; `API.md` "Jobs" |
| F6.5 | Correction capture | The record | No | built | `API.md` `source.correct`; `test_source_correction_stales_proposals_and_accepted_derivatives`, `test_undo_rejects_stale_client_and_preserves_history`. Corrections are kept as record history in the `versions` table. Nothing yet turns that history into evaluation data: `gaps.md` G4 records the evaluation directories as empty |
| F6.6 | Retention and deletion | Participant | No | built | `test_delete_purges_all_content_and_survives_restart`, `test_expiry_purges_and_lease_expiry_pauses`, and the deletion promise asserted against raw file bytes (`decisions/decision-log.md` 2026-09-16, `secure_delete`). The anonymisation half of the function is not built: `README.md` states plainly that exports are not anonymised |

### What the four words mean

- **built.** It runs in this repository and it is tested. The evidence column
  names the test. Built does not mean finished, and where a built row has a
  limit the row says so, because a status word that hides a limit is worse than
  no status at all.
- **plumbing.** The contract, the record shape and the tests exist; the model
  or the device path does not. Every plumbing row here sits behind a synthetic
  adapter, `FixtureExtractor` for photographs and `FixtureTranscriber` for
  audio, whose output is visibly synthetic on purpose so it can never be
  mistaken for a result.
- **proposed.** Designed in `pipelines.md`, with a candidate named in
  `stack.md` where one has been chosen. Nothing runs.
- **open.** A decision the team has not made. Not a task waiting for time, a
  question waiting for an answer.

## 5. Counts

| Status | Count |
|---|---|
| built | 16 |
| plumbing | 5 |
| proposed | 15 |
| open | 2 |
| **Total** | **38** |

**These counts were read from the table above, not the other way round.** That
direction matters: a count written first becomes a target, and a row then gets
the word that keeps the total tidy. `check_proposal.py` recomputes them from
the same table and prints them, so a row whose status changes and a count that
does not follow will disagree in the output of a check that runs on every push.

Sixteen built rows out of thirty-seven is not sixteen thirty-sevenths of a
product. Every built row is in capture, the canvas, the session and the
guardrails. The understanding group, F2.1 to F2.8, has no built row at all,
which is the honest shape of the project: the mechanism a model would plug into
is the finished part, and the model is the part nobody has run.

## 6. What is deliberately not chosen

Seven things this project has decided **not** to adopt yet, each with the
reason and the cost, are in `deliverables/documentation/stack.md` section 4,
"What is deliberately not chosen, and why": no paid provider, no framework on
either side, no WebSocket, no vector database, no YOLO fine-tune, no FigJam
push in the first version, no proactive suggestion, and no handwriting or
speech recognition.

They are not repeated here on purpose. This document would then hold a second
copy of a list that already has an owner, and the copy would be the one a
reader found first after it went stale. Read them there.

---

**Unverified, and recorded as such.** No accuracy, latency or cost figure
anywhere in this project has been measured: every number in `pipelines.md` and
`stack.md` is a proposal, and `stack.md` says so in its own header. The three
seconds this tool is designed for are quoted from the concept, not observed:
`gaps.md` G4 records that the evaluation directories are empty and that the
project cannot yet demonstrate that the tool helps anyone do anything. The
Week 3 interview findings reach this document through a report, not through
the room.
