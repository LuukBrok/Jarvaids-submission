#!/usr/bin/env python3
"""Does the test suite actually protect the guards, or does it only pass?

A green suite proves the happy paths work. It says nothing about whether the
checks that refuse bad input are still there. This tool answers that: it deletes
one guard at a time and reports any guard whose removal the suite does not
notice.

It was written because the answer was bad. Four injected mutations left all 45
tests passing, including deleting the credential check on the deletion receipt
and the guard that stops the last facilitator demoting themselves out of the
session. Those are not edge cases, they are the reasons the functions exist.

Run it:

    python3 tests/mutation_check.py            # every mutant
    python3 tests/mutation_check.py --list     # names only, runs nothing

Exit 0 means every mutant was caught. Exit 1 names the survivors.

Adding a guard? Add a mutant for it here in the same commit. A guard with no
mutant is a guard nobody has checked is load-bearing.
"""
import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import mutation_runner

ROOT = pathlib.Path(__file__).resolve().parents[1]
TARGET = ROOT / "genai_server" / "service.py"

# (name, what it defends, the test that must fail, exact source to replace, replacement)
#
# Each `old` must appear exactly once in service.py. The tool checks that before
# running anything, so a mutant that silently stops matching after a refactor is
# reported as broken rather than passing quietly. That failure mode is the whole
# reason the previous regexes in AUDIT.md went unnoticed.
#
# The third field is why a red suite is not enough. A mutant caught by some
# other test is caught by accident: rename that test's subject and the guard
# goes unprotected again with nothing announcing it. The named test has to be
# the one that fails.
MUTANTS = [
    (
        "deletion-receipt-credential",
        "only the facilitator who deleted a session may read its receipt",
        "test_deletion_receipt_refuses_a_credential_that_is_not_the_deleters",
        "secrets.compare_digest(s['deletion_hash'] or '',digest(token))",
        "True",
    ),
    (
        "last-facilitator",
        "a session cannot be left with nobody who can close or export it",
        "test_the_only_facilitator_cannot_demote_themselves",
        "'last_facilitator','Promote a replacement before demoting the last facilitator.',409)",
        "'last_facilitator','x',409) if False else None",
    ),
    (
        "record-cap",
        "one session cannot exhaust the instance",
        "test_a_session_cannot_exceed_its_record_cap",
        "MAX_RECORDS=1000",
        "MAX_RECORDS=10**9",
    ),
    (
        "image-byte-cap",
        "one session cannot exhaust disk with photographs",
        "test_the_image_budget_can_actually_bind",
        "MAX_IMAGE_BYTES=20*1024*1024",
        "MAX_IMAGE_BYTES=10**12",
    ),
    (
        "duplicate-reference",
        "a proposal cannot reference the same record twice",
        "test_a_proposal_cannot_reference_the_same_record_twice",
        "require(record['id'] not in seen,'duplicate_reference','Reference IDs must be unique.')\n            seen.add(record['id'])\n            require(record['data'].get('status') not in ('stale','undone','superseded'),'stale_reference','Referenced item requires review or was undone.',409)",
        "pass\n            seen.add(record['id'])\n            require(record['data'].get('status') not in ('stale','undone','superseded'),'stale_reference','Referenced item requires review or was undone.',409)",
    ),
    (
        "job-terminal",
        "a finished job cannot be cancelled again",
        "test_a_finished_job_cannot_be_cancelled",
        "require(job['data']['status'] in ('queued','running'),'job_terminal','Job has already finished.',409)",
        "pass",
    ),
    (
        "events-has-more",
        "a client paging events is told when a page is not the last",
        "test_a_full_event_page_reports_that_more_remain",
        "'has_more':bool(events and events[-1]['seq']<s['seq'])",
        "'has_more':False",
    ),
    (
        "purge-verification",
        "deletion fails loudly rather than leaving rows behind",
        "test_deletion_fails_loudly_if_a_table_is_not_emptied",
        "'purge_failed','Store purge verification failed.',500)",
        "'purge_failed','x',500) if False else None",
    ),
    (
        "recovery-no-automatic-retry",
        "an interrupted job cannot silently repeat a possibly paid call",
        "test_recovery_requires_manual_retry_after_any_interruption",
        "d['status']='failed'",
        "d['status']='queued'",
    ),
    (
        "adapter-changed",
        "a result from a since-reconfigured adapter is refused",
        "test_a_result_from_a_reconfigured_adapter_is_refused",
        "require(job['data']['adapter']==self.extractor.name,'adapter_changed','Queued adapter is no longer configured.',409)",
        "pass",
    ),
]

# The complete baseline runs first. Each mutation then runs its named test,
# because an unrelated failure is never valid evidence for this guard.
MUTANTS += [
    ('cancel-execution','committed cancellation releases the worker','test_committed_cancel_stops_running_isolated_adapter',
     "                    ticket['cancel_event'].set()", "                    pass"),
    ('completion-lease','a failed pause write cannot admit late output','test_completion_checks_lease_even_when_pause_write_fails',
     " or sr['lease']<=self.clock():", ":"),
    ('deleted-completion-ticket','output cannot re-enter cache after deletion','test_delete_before_failed_completion_cannot_retain_output',
     "not ticket['revoked'] and s['expires']>self.clock()", "s['expires']>self.clock()"),
    ('capture-lease','failed sweep cannot reopen capture','test_failed_lease_pause_cannot_allow_capture_or_heartbeat',
     "require(s['lease']>self.clock(),'lease_expired'", "require(True,'lease_expired'"),
    ('heartbeat-expired','heartbeat cannot override failed pause','test_failed_lease_pause_cannot_allow_capture_or_heartbeat',
     "s['state']!='active' or s['lease']>self.clock(),'lease_expired'", "True,'lease_expired'"),
    ('activation-revision','delayed activation cannot override pause','test_delayed_activation_cannot_override_pause',
     "b['expected_session_revision']==s['revision'],'stale_activation'", "True,'stale_activation'"),
    ('retain-completed-output','storage recovery must not repeat extraction','test_completion_store_recovers_without_another_extraction',
     "self.pending_completions[job['id']]=args", "pass"),
    ('clear-completed-output','purge removes retained output','test_delete_clears_retained_completion_output',
     "if args[0]['id']==sid:self.pending_completions.pop(jid,None)", "if False:self.pending_completions.pop(jid,None)"),
    ('control-window','control replay cache cannot grow forever','test_control_history_is_bounded_and_old_replay_is_refused',
     "(sid,a['id'],control_sequence-self.CONTROL_REPLAY_WINDOW)", "(sid,a['id'],-1)"),
    ('control-order','control allocation conflicts are explicit','test_control_sequence_cannot_be_allocated_twice',
     "control_sequence==a['control_seq']+1,'control_sequence_conflict'", "True,'control_sequence_conflict'"),
    ('control-old-replay','discarded outcome has explicit resync error','test_control_history_is_bounded_and_old_replay_is_refused',
     "control_sequence>a['control_seq']-self.CONTROL_REPLAY_WINDOW,'control_replay_expired'", "True,'control_replay_expired'"),
    ('queue-instance','session caps cannot exhaust shared worker queue','test_instance_queue_limit_is_distinct_from_session_limit',
     "'instance_queue_full','Instance extraction queue is full; retry later.',429)",
     "'instance_queue_full','x',429) if False else None"),
    ('queue-fairness','one session cannot monopolise claims','test_sessions_receive_round_robin_claims',
     "if self.last_claim_session in ids:", "if False:"),
    ('deadline-reconcile','callbacks are not required for expiry','test_maintenance_expires_running_jobs_without_callback',
     "job['data']['status'] in ('queued','running') and job['data']['deadline']<=now", "False"),
    ('media-authority','unrelated members cannot read originals','test_unrelated_and_demoted_members_cannot_read_images_or_crops',
     "a['role']=='facilitator' or (a['role']=='participant' and r['data']['author_id']==a['id'])", "True"),
    ('crop-authority','unauthorised callers do not trigger crop decoding','test_crop_authority_denies_before_decoding',
     "a['role']=='facilitator' or (a['role']=='participant' and source['data']['author_id']==a['id'])", "True"),
    ('join-expiry','expired invitations cannot admit members','test_expired_invitation_creates_no_member',
     "invite['expires']>self.clock(),'invitation_expired'", "True,'invitation_expired'"),
    ('join-revocation','revoked invitations cannot admit members','test_revoked_invitation_creates_no_member',
     "not invite['revoked'],'invitation_revoked'", "True,'invitation_revoked'"),
    ('join-policy','join requires current agreement','test_join_requires_current_policy',
     "body['policy_version']==s['policy_version'],'policy_changed'", "True,'policy_changed'"),
    ('join-consumption','another credential cannot reuse admission','test_join_retry_is_bound_to_exact_credential_and_payload',
     "secrets.compare_digest(invite['credential_hash'],digest(token))", "True"),
    ('join-intent','replay cannot change membership intent','test_join_retry_is_bound_to_exact_credential_and_payload',
     "secrets.compare_digest(invite['intent_hash'],intent)", "True"),
    ('join-removed','removed membership cannot be replayed','test_removal_revokes_cached_commands_and_join_replay',
     "c.execute('SELECT 1 FROM actors WHERE id=? AND session_id=?',(invite['actor_id'],sid)).fetchone() is not None", "True"),
    ('last-facilitator-remove','removal cannot strand a session','test_last_facilitator_cannot_be_removed',
     "'last_facilitator','Promote a replacement before removing the last facilitator.',409)",
     "'last_facilitator','x',409) if False else None"),
    ('roster-revision','stale administrators cannot overwrite attendance','test_stale_roster_action_has_no_effect',
     "revision==s['roster_revision'],'stale_roster'", "True,'stale_roster'"),
    ('close-revision','stale close cannot end a changed session','test_stale_close_cannot_end_changed_session',
     "b['expected_session_revision']==s['revision'],'stale_session'", "True,'stale_session'"),
    ('withdraw-agreement','withdrawal blocks capture until renewed','test_withdrawal_preserves_other_agreement_and_blocks_activation',
     "UPDATE actors SET consent_version=0,withdrawn_at=? WHERE id=?", "UPDATE actors SET withdrawn_at=? WHERE id=?"),
    ('pause-preserves-policy','pause must not reset room agreement','test_lease_preserves_policy_and_proposals',
     "UPDATE sessions SET state=?,revision=revision+1 WHERE id=?", "UPDATE sessions SET state=?,revision=revision+1,policy_version=policy_version+1 WHERE id=?"),
    ('pause-noop','fresh pause intents do not manufacture transitions','test_pause_noop_preserves_state_revision_and_event_cursor',
     "if s['state']==state:return", "if False:return"),
]


MUTANTS += [('position-concurrency', 'two people dragging one note do not silently overwrite each other', 'test_a_move_from_a_stale_view_is_refused', "require((existing['revision'] if existing else 0)==p['expected_position_revision'],", 'require(True,'), ('hand-placed-protected', 'the layout engine never moves what a person placed', 'test_the_layout_engine_may_not_move_what_a_person_placed', "require(origin=='human' or not (existing and existing['hand_placed']),", 'require(True,'), ('machine-placement-unowned', "the layout engine's own guesses stay moveable by the engine", 'test_a_machine_placement_is_not_owned_until_a_person_moves_it', 'hand_placed=1 if hand else 0', 'hand_placed=1'), ('placement-bounds', 'a record cannot be moved off the addressable board', 'test_coordinates_off_the_board_are_refused', 'and abs(p[key])<=self.MAX_COORDINATE,', 'and True,'), ('placement-duplicate', 'one move cannot give one record two positions', 'test_one_record_cannot_appear_twice_in_one_move', "require(p['id'] not in seen,'duplicate_placement','Each record may appear once in a move.')", 'pass'), ('positions-purged', 'deleting a session deletes where everything was put', 'test_deleting_a_session_takes_the_positions_with_it', "for table in ('requests','control_requests','events','versions','positions','records','actors','invitations','media'):", "for table in ('requests','control_requests','events','versions','records','actors','invitations','media'):"), ('event-completeness', 'an event names every record the command wrote', 'test_accepting_a_proposal_names_both_records_it_wrote', "c.changed[(record['id'],what)]={'id':record['id'],'kind':what,'revision':record['revision']}", 'pass'), ('delta-cursor-ahead', 'a cursor this session never issued is refused, not answered empty', 'test_a_cursor_ahead_of_the_session_is_refused', "require(since_seq<=s['seq'],'cursor_ahead',", "require(True,'cursor_ahead',"), ('keepalive-drain', 'an unread request body cannot be parsed as the next request', 'test_an_unread_request_body_does_not_corrupt_the_next_request', '        self._drain()\n', '')]

MUTANTS += [('uncertain-retry-ack', 'uncertain extraction cannot be silently retried', 'test_uncertain_retry_requires_specific_explicit_acknowledgement', "retry_of==uncertain[-1]['id'] and b.get('acknowledge_uncertain_cost') is True,", 'True,'), ('retry-source-binding', 'acknowledgement must refer to this source uncertainty', 'test_retry_acknowledgement_cannot_name_an_unrelated_source', "retry_of is None and 'acknowledge_uncertain_cost' not in b,", 'True,'), ('recovery-before-expiry', 'expiry cannot erase evidence of an interrupted claim', 'test_startup_deadline_or_lease_cleanup_cannot_erase_claim_uncertainty', '        # Preserve claim uncertainty before expiry/lease cleanup makes it terminal.', '        self.sweep()'), ('cancelled-attempt-usage', 'cancellation cannot erase reported cost', 'test_cancelled_output_keeps_reported_usage_without_publishing_proposals', "if d['status'] in ('failed','cancelled') and d['attempts']==job['data']['attempts'] and any(d.get(k)!=v for k,v in outcome.items()):", 'if False:'), ('storage-rejection-usage', 'budget rollback cannot erase reported cost', 'test_storage_rejection_keeps_reported_attempt_usage', "error='storage_capacity',duration_ms=round((time.monotonic()-started)*1000,2),**outcome)", "error='storage_capacity',duration_ms=round((time.monotonic()-started)*1000,2))")]

# INT13. The delta used to carry board_order, so one edit cost every id on the
# board. This mutant puts it back.
MUTANTS += [
    (
        "delta-board-order",
        "a delta costs the same whatever is already on the board",
        "test_a_delta_does_not_grow_with_the_board",
        "'records':records,'since_seq':since_seq,'current_seq':s['seq']}",
        "'records':records,'board_order':self._board_order(positions),'since_seq':since_seq,'current_seq':s['seq']}",
    ),
]

# J02 / INT04. Both of these returned HTTP 500 before they were guarded.
MUTANTS += [
    (
        "surrogate-rejected",
        "text that cannot be encoded is refused at the boundary, not at the fingerprint",
        "test_a_lone_surrogate_anywhere_in_the_body_is_refused",
        '    reject_surrogates(parsed)\n',
        "",
    ),
    (
        "placement-id-type",
        "an id is validated before anything tries to hash it",
        "test_an_id_of_the_wrong_type_is_a_client_error",
        "            ident(p['id'])\n",
        "",
    ),
]

# INT12 / INT13. A cascade can name most of the session; past halfway the
# delta stops being the cheap path and says so.
MUTANTS += [
    (
        "delta-resync-bound",
        "a cascade over half the session asks for a snapshot instead",
        "test_a_cascade_over_half_the_session_asks_for_a_snapshot",
        'if wanted and len(wanted)*2>total:',
        'if False:',
    ),
]

# B06. Cluster membership rules.
MUTANTS += [
    (
        'cluster-size-cap',
        'a form holds at most 24 items; past that it is a list',
        'test_a_form_cannot_hold_more_than_twenty_four_items',
        "require(len(refs)<=self.MAX_CLUSTER_MEMBERS,'cluster_too_large',",
        "require(True,'cluster_too_large',",
    ),
    (
        'one-cluster-per-item',
        'an item in two hulls cannot satisfy its own separation rules',
        'test_an_item_belongs_to_at_most_one_cluster',
        "            require(ref['id'] not in taken,'already_clustered',",
        "            require(True,'already_clustered',",
    ),
    (
        'empty-cluster-undone',
        'a cluster with no members is undone, not left undrawable',
        'test_removing_the_last_member_undoes_the_cluster',
        "            d.update(status='undone',emptied_by=a['id'])",
        '            pass',
    ),
]

# INT09. Connection slots under keep-alive: a slot now lasts a whole
# connection, so the ceiling is reachable by eight people on two devices each.
MUTANTS += [
    (
        'slot-ceiling',
        'a room that fills the connection slots is refused, not queued',
        'test_a_connection_that_goes_idle_still_gives_its_slot_back',
        '        if not self.slots.acquire(blocking=False):',
        '        if False:',
    ),
    (
        'slot-release',
        'a finished connection gives its slot back',
        'test_a_refused_connection_does_not_leak_a_slot',
        '        try:super().process_request_thread(request,client_address)\n        finally:self.slots.release()',
        '        super().process_request_thread(request,client_address)',
    ),
    (
        'idle-timeout',
        'an idle keep-alive connection cannot hold a slot for ever',
        'test_a_connection_that_goes_idle_still_gives_its_slot_back',
        'self.connection.settimeout(self.server.idle_timeout)',
        'self.connection.settimeout(None)',
    ),
]

# INT09. The deletion promise, in the file's bytes.
MUTANTS += [
    (
        "secure-delete",
        "deleted words are overwritten on disk, not just unlinked from a table",
        "test_deleted_words_are_not_left_in_the_database_file",
        "conn.execute('PRAGMA secure_delete=ON')",
        "conn.execute('PRAGMA secure_delete=OFF')",
    ),
]

# F1.1-F1.3 audio capture guards.
MUTANTS += [
    (
        'audio-consent-gate',
        'no transcript is written before consent/activation, matching every other source (F6.1)',
        'test_audio_capture_requires_active_session',
        "self._editor(a);self._active(s)\n            raw,sample_rate,duration_ms=self._validate_audio(b)",
        "self._editor(a)\n            raw,sample_rate,duration_ms=self._validate_audio(b)",
    ),
    (
        'audio-capacity-cap',
        'one session cannot grow its transcript without bound',
        'test_audio_capacity_can_actually_bind',
        'MAX_AUDIO_CHUNKS=400',
        'MAX_AUDIO_CHUNKS=10**9',
    ),
    (
        'audio-gap-not-dropped',
        'a failing transcriber still writes a visible gap, never a mislabelled success (F6.4)',
        'test_a_failing_transcriber_writes_a_visible_gap_not_a_silent_drop',
        "return {'status':'gap','text':None,'confidence':0.0,",
        "return {'status':'final','text':'','confidence':0.0,",
    ),
]


# F02: confidence and colour on an extracted reading.
MUTANTS += [
    (
        'note-confidence-range',
        'a confidence outside 0 to 1, NaN or a boolean is refused rather than drawn',
        'test_a_confidence_outside_zero_to_one_fails_the_job',
        "require(confidence is None or (type(confidence) in (int,float) and math.isfinite(confidence) and 0<=confidence<=1),",
        "require(True,",
    ),
    (
        'note-colour-shape',
        'a colour must name its space and its source',
        'test_a_colour_without_a_space_and_a_source_fails_the_job',
        "require(colour['space']=='srgb' and type(colour['hex']) is str and re.fullmatch('#[0-9a-f]{6}',colour['hex']) is not None",
        "require(True",
    ),
    (
        'edited-text-drops-confidence',
        "a model's confidence is not left on text a person retyped",
        'test_retyping_a_reading_clears_the_models_confidence',
        "if 'confidence' in d:d['confidence']=None",
        "pass",
    ),
]


# J02: a number that overflows a float is a client error, not a 500.
MUTANTS += [
    (
        'overflowing-number',
        'a JSON number too large for a float is refused at the parser, not at the fingerprint',
        'test_a_number_too_large_for_a_float_is_a_client_error',
        "parse_float=finite_float,parse_int=float_sized_int)",
        "parse_int=float_sized_int)",
    ),
    (
        'nesting-depth',
        'a body nested past the stated depth limit is refused, on every Python version',
        'test_nesting_past_the_stated_limit_is_a_client_error',
        "        if depth>MAX_JSON_DEPTH:\n",
        "        if False:\n",
    ),
    (
        'overflowing-integer',
        'an integer too large for a float is refused at the parser, not by an OverflowError in a validator',
        'test_a_number_too_large_for_a_float_is_a_client_error',
        "parse_float=finite_float,parse_int=float_sized_int)",
        "parse_float=finite_float)",
    ),
]


# The canvas object model, docs/specs/2026-10-18-canvas-object-model.md. Every
# guard in tests/test_canvas_objects.py, one mutant each. Guards inherited from
# shared code are not repeated here: a missing endpoint or member is `_get`'s
# not_found, the closed-session and viewer refusals are the command dispatcher's,
# and the record cap is `_new`'s, each with its own mutant above.
MUTANTS += [
    ('canvas-kind', 'a canvas object is one of the five kinds the client can draw',
     'test_an_unknown_canvas_kind_is_refused',
     "require(kind in self.CANVAS_KINDS,'invalid_kind','A canvas object is a shape, text, arrow, section or stroke.')",
     "pass"),
    ('canvas-proposal-kind', 'a canvas proposal is one of the five kinds the client can draw',
     'test_an_unknown_canvas_proposal_kind_is_refused',
     "require(kind in self.CANVAS_KINDS,'invalid_kind','canvas_kind is shape, text, arrow, section or stroke.')",
     "pass"),
    ('canvas-own-fields', 'an object carries only its kind\'s fields, so an update cannot rewrite provenance',
     'test_an_update_cannot_change_common_fields',
     "fields(data,required,optional)",
     "fields(data,required,tuple(data))"),
    ('canvas-tone', 'tone is a closed set, never a status colour',
     'test_an_unknown_tone_is_refused',
     "require(data['tone'] in self.TONES",
     "require(True"),
    ('canvas-shape', 'a shape is one of the four the client draws',
     'test_an_unknown_shape_is_refused',
     "require(data['shape'] in self.SHAPES",
     "require(True"),
    ('canvas-shape-text', 'shape text is at most 280 characters',
     'test_shape_text_is_at_most_280_characters',
     "text(data['text'],'text',280,empty=True)",
     "text(data['text'],'text',10**9,empty=True)"),
    ('canvas-text-length', 'a text object is at most 1000 characters',
     'test_text_is_1_to_1000_characters',
     "text(data['text'],'text',1000)",
     "text(data['text'],'text',10**9)"),
    ('canvas-text-size', 'text size is body, title or heading',
     'test_an_unknown_text_size_is_refused',
     "require(data['size'] in self.TEXT_SIZES",
     "require(True"),
    ('canvas-arrow-label', 'an arrow label is at most 80 characters',
     'test_an_arrow_label_is_at_most_80_characters',
     "text(data['label'],'label',80,empty=True)",
     "text(data['label'],'label',10**9,empty=True)"),
    ('canvas-endpoint-shape', 'an arrow end is an id or a point, never both',
     'test_an_arrow_end_is_an_id_or_a_point_not_both',
     "require(type(value) is dict and (value.keys()=={'id'} or value.keys()=={'x','y'}),'invalid_endpoint',",
     "require(type(value) is dict,'invalid_endpoint',"),
    ('canvas-endpoint-point', 'an arrow end point is on the board',
     'test_an_arrow_end_point_stays_on_the_board',
     "self._coordinates(value,'invalid_endpoint');return",
     "return"),
    ('canvas-endpoint-kind', 'an arrow connects items or proposals, not sources',
     'test_an_arrow_end_must_be_an_item_or_proposal',
     "require(record['kind'] in ('item','proposal'),'invalid_endpoint'",
     "require(True,'invalid_endpoint'"),
    ('canvas-endpoint-on-board', 'an arrow cannot be drawn to a removed record',
     'test_an_arrow_end_must_be_on_the_canvas',
     "require(self._on_board(record),'invalid_endpoint'",
     "require(True,'invalid_endpoint'"),
    ('canvas-self-arrow', 'an arrow cannot point from a record to itself',
     'test_an_arrow_cannot_point_from_a_record_to_itself',
     "require(not ('id' in data['from'] and data['from'].get('id')==data['to'].get('id')),",
     "require(True,"),
    ('canvas-arrow-at-itself', 'an arrow cannot be updated to point at itself',
     'test_an_arrow_cannot_be_turned_to_point_at_itself',
     "require(value['id']!=self_id,'self_arrow'",
     "require(True,'self_arrow'"),
    ('canvas-section-title', 'a section title is at most 80 characters',
     'test_a_section_title_is_at_most_80_characters',
     "text(data['title'],'title',80,empty=True)",
     "text(data['title'],'title',10**9,empty=True)"),
    ('canvas-section-form', 'a section form is one of the five the spec names',
     'test_an_unknown_section_form_is_refused',
     "require(data['form'] in self.SECTION_FORMS",
     "require(True"),
    ('canvas-section-cap', 'a section holds at most 60 members',
     'test_a_section_holds_at_most_60_members',
     "MAX_SECTION_MEMBERS=60",
     "MAX_SECTION_MEMBERS=10**9"),
    ('canvas-duplicate-member', 'a section names each member once',
     'test_a_section_member_appears_once',
     "require(rid not in seen,'duplicate_member'",
     "require(True,'duplicate_member'"),
    ('canvas-nested-section', 'a section cannot hold a section',
     'test_a_section_cannot_hold_a_section',
     "require(kind_of!='section' and rid!=self_id,'nested_section'",
     "require(True,'nested_section'"),
    ('canvas-member-kind', 'a member is a note, shape, text or stroke',
     'test_a_section_member_is_a_note_shape_text_or_stroke',
     "require(member['kind'] in ('item','proposal') and kind_of in ('note','shape','text','stroke'),",
     "require(True,"),
    ('canvas-member-on-board', 'a removed record cannot join a section',
     'test_a_removed_record_cannot_join_a_section',
     "require(self._on_board(member),'invalid_member'",
     "require(True,'invalid_member'"),
    ('canvas-stroke-min', 'a stroke has at least two points',
     'test_a_stroke_has_at_least_two_points',
     "2<=len(points)<=self.MAX_STROKE_POINTS",
     "0<=len(points)<=self.MAX_STROKE_POINTS"),
    ('canvas-stroke-max', 'a stroke has at most 256 points',
     'test_a_stroke_has_at_most_256_points',
     "MAX_STROKE_POINTS=256",
     "MAX_STROKE_POINTS=10**9"),
    ('canvas-stroke-offset', 'stroke points stay within 10000 of the position',
     'test_stroke_points_stay_within_10000_of_the_position',
     "MAX_STROKE_OFFSET=10000",
     "MAX_STROKE_OFFSET=10**9"),
    ('canvas-stroke-pair', 'a stroke point is a pair',
     'test_a_stroke_point_is_a_pair_of_numbers',
     "require(type(point) is list and len(point)==2 and all(",
     "require(type(point) is list and all("),
    ('canvas-stroke-weight', 'stroke weight is fine, regular or bold',
     'test_an_unknown_stroke_weight_is_refused',
     "require(data['weight'] in self.STROKE_WEIGHTS",
     "require(True"),
    ('canvas-create-coordinates', 'a hand-made object is placed on the board',
     'test_a_hand_made_object_must_be_drawn_on_the_board',
     "        self._coordinates(b)\n",
     ""),
    ('size-required', 'a shape, text or section cannot be made without a size',
     'test_a_shape_text_or_section_needs_a_size_when_made',
     "require(not required,'invalid_size'",
     "require(True,'invalid_size'"),
    ('size-required-on-first-place', 'first placing a proposed shape needs a size',
     'test_first_placing_a_proposed_shape_needs_a_size',
     "kind in self.SIZED_KINDS and (existing is None or existing['w'] is None)",
     "False"),
    ('size-refused-for-notes', 'a note takes its width from its text, never a stored size',
     'test_a_note_is_refused_a_size',
     "require(kind in self.CANVAS_KINDS,'invalid_size'",
     "require(True,'invalid_size'"),
    ('size-min', 'a size below 8 is refused',
     'test_a_size_below_8_is_refused',
     "MIN_SIZE=8",
     "MIN_SIZE=-10**9"),
    ('size-max', 'a size above 4000 is refused',
     'test_a_size_above_4000_is_refused',
     "MAX_SIZE=4000",
     "MAX_SIZE=10**9"),
    ('size-both', 'a width needs a height',
     'test_a_width_needs_a_height',
     "        for key in ('w','h'):\n            value=body.get(key)",
     "        for key in ('w',):\n            value=body.get(key)"),
    ('canvas-proposal-one-position', 'a canvas proposal has exactly one position, its own',
     'test_a_canvas_proposal_has_one_position_of_its_own',
     "require(type(positions) is list and len(positions)==1,'invalid_positions',",
     "require(type(positions) is list and len(positions)>=1,'invalid_positions',"),
    ('canvas-only-canvas-targets', 'canvas.update and canvas.remove touch only the five new kinds',
     'test_only_canvas_objects_can_be_removed_this_way',
     "require(kind in self.CANVAS_KINDS,'invalid_target'",
     "require(True,'invalid_target'"),
    ('canvas-removed-is-frozen', 'a removed object is restored before it is changed',
     'test_a_removed_object_cannot_be_updated',
     "require(r['data'].get('status')!='undone','item_undone','That object was removed",
     "require(True,'item_undone','That object was removed"),
    ('canvas-empty-update', 'an update names at least one field',
     'test_an_update_names_at_least_one_field',
     "require(type(b['data']) is dict and b['data'],'invalid_data'",
     "require(type(b['data']) is dict,'invalid_data'"),
    ('item-edit-not-canvas', 'item.edit cannot write text and refs onto a drawing',
     'test_item_edit_refuses_a_canvas_object',
     "require(r['data'].get('item_kind') not in self.CANVAS_KINDS,'invalid_target'",
     "require(True,'invalid_target'"),
    ('proposal-edit-not-canvas', 'a canvas proposal is rejected and proposed again, not edited',
     'test_proposal_edit_refuses_a_canvas_proposal',
     "require(r['data'].get('proposal_kind')!='canvas','invalid_target'",
     "require(True,'invalid_target'"),
    ('canvas-accept-recheck', 'accepting a canvas proposal rechecks what it points at',
     'test_accepting_a_canvas_proposal_rechecks_its_ends',
     "data=self._canvas_data(c,s['id'],d['canvas_kind'],d['canvas_data'])",
     "data=deepcopy(d['canvas_data'])"),
]


def run_suite(source=None,killed_by=None,target_name="service.py"):
    """Run the suite against a disposable copy. See tests/mutation_runner.py.

    Returns (passed, failing test names). The names are what tells an intended
    kill from an accidental one.
    """
    return mutation_runner.run(target=target_name, source=source, killed_by=killed_by,
                               timeout=180, scratch_name='mutation-runs')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="print the mutants and exit")
    args = parser.parse_args()

    if args.list:
        for name, defends, killed_by, _, _ in MUTANTS:
            print("%-28s %s\n%-28s   killed by %s" % (name, defends, "", killed_by))
        return 0

    source = TARGET.read_text(encoding="utf-8")
    sources={name:(TARGET.parent/name).read_text(encoding="utf-8") for name in ("service.py","http.py","db.py")}
    homes={name:[path for path,text in sources.items() if text.count(old)==1] for name,_,_,old,_ in MUTANTS}

    # Check every mutant still matches before running anything, so a mutant that
    # has rotted is a loud failure rather than a quiet pass.
    broken = [n for n, _, _, old, _ in MUTANTS if len(homes[n]) != 1]
    if broken:
        print("These mutants no longer match service.py exactly once:")
        for name in broken:
            print("   %s" % name)
        print("\nservice.py changed and this file did not. Fix the patterns.")
        return 1

    if not run_suite()[0]:
        print("The suite fails before any mutation. Fix that first.")
        return 1

    survivors, misattributed = [], []
    try:
        for name, defends, killed_by, old, new in MUTANTS:
            passed, failing = run_suite(sources[homes[name][0]].replace(old,new,1),killed_by,homes[name][0])
            if passed:
                verdict = "SURVIVED"
                survivors.append((name, defends))
            elif killed_by in failing:
                verdict = "caught by %s" % killed_by
            else:
                # Red, but not for this guard's reason. Treated as a survivor,
                # because the test that names this guard is not defending it.
                verdict = "CAUGHT BY THE WRONG TEST: %s" % ", ".join(sorted(failing) or ["nothing named"])
                misattributed.append((name, killed_by, sorted(failing)))
            print("  %-28s %s" % (name, verdict), flush=True)
    finally:
        # The original file is never a mutation target, even after interruption.
        if TARGET.read_text(encoding="utf-8") != source:
            raise RuntimeError('Original service.py changed concurrently.')

    print()
    if survivors:
        print("%d guard(s) the suite does not protect:" % len(survivors))
        for name, defends in survivors:
            print("   %-28s %s" % (name, defends))
        print("\nAdd a test that fails when the guard is removed.")
    if misattributed:
        print("%d guard(s) whose own test did not fail:" % len(misattributed))
        for name, killed_by, failing in misattributed:
            print("   %-28s expected %s" % (name, killed_by))
            print("   %-28s got      %s" % ("", ", ".join(failing) or "nothing named"))
        print("\nThe guard is protected by accident, not on purpose.")
    if survivors or misattributed:
        return 1

    print("All %d guards are protected: removing any one turns the suite red." % len(MUTANTS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
