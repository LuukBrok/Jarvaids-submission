"""Named calendar guard removals, executed only in disposable code copies."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mutation_runner import check_multi_target

MUTANTS = [
    ('stable-manual-deadline', 'documents.py', 'if resolve_deadline:', 'if True:',
     'test_manual_todo_completion_does_not_reanchor_original_relative_deadline'),
    ('calendar-provider-schema', 'document_model.py', "calendar = request.get('document_type') == 'calendar'", 'calendar = False',
     'test_calendar_uses_typed_schema_and_prompt'),
    ('capture-clock-bounds', 'calendar_service.py', "session['created']-300 <= payload['captured_at_utc_ms']/1000 <= self.clock()+300", 'True',
     'test_out_of_session_capture_clock_is_rejected_before_transcription'),
    ('inflight-task-revision', 'calendar_service.py', "entry['revision'] == requested[entry['id']]['revision']", 'True',
     'test_shared_task_revision_is_checked_after_interpretation'),
    ('todo-accepted-task-review', 'documents.py', "if entry and entry['data']['status'] == 'accepted' and not self.automatic_workspace:", 'if False:',
     'test_todo_ai_also_proposes_instead_of_replacing_calendar_accepted_task'),
    ('source-clock', 'calendar_dates.py', "data.get('captured_at_utc_ms', data['created_at'] * 1000) / 1000", "data['created_at']",
     'test_date_is_anchored_to_source_not_worker_execution_day'),
    ('meeting-zone', 'calendar_dates.py', 'datetime.fromtimestamp(instant, ZoneInfo(zone)).date()', 'datetime.fromtimestamp(instant, timezone.utc).date()',
     'test_relative_dates_use_session_zone_and_calendar_days'),
    ('ambiguous-weekday', 'calendar_dates.py', "if prefix == 'next ' and not week:", 'if False:',
     'test_ambiguous_dates_and_weeks_stay_undated'),
    ('literal-date', 'calendar_model.py', "grounded(patch['date_quote']) and (not patch['date_phrase'] or patch['date_phrase'] in patch['date_quote'])", 'True',
     'test_unstated_date_and_invented_evidence_are_rejected'),
    ('literal-evidence', 'calendar_model.py', "ref['source_id'] in sources and ref['quote'] in sources[ref['source_id']]['text']", 'True',
     'test_invented_calendar_quotation_is_rejected'),
    ('known-event', 'calendar_model.py', "bool(patch['task_id']) or patch['op'] == 'add' and not patch['entry_id'] or\n                not patch['task_id'] and patch['op'] != 'add' and patch['entry_id'] in entries", 'True',
     'test_unknown_event_identity_is_rejected'),
    ('known-task', 'calendar_model.py', "not patch['task_id'] or patch['task_id'] in tasks and not patch['entry_id'] and patch['op'] != 'add'", 'True',
     'test_unknown_shared_task_is_rejected_before_application'),
    ('accepted-task-review', 'calendar_service.py', "if entry['data']['status'] == 'accepted' and not self.automatic_workspace:", 'if False:',
     'test_ai_cannot_replace_accepted_shared_task_without_review'),
    ('stale-task-review', 'calendar_service.py', "entry['revision'] == change['data']['base_revision']", 'True',
     'test_stale_task_proposal_requires_fresh_review'),
    ('event-edit-revision', 'calendar_service.py', "self._expected(entry, b.get('expected_entry_revision'))", 'pass',
     'test_stale_manual_event_revision_does_not_replace_newer_date'),
    ('task-edit-revision', 'calendar_service.py', "self._expected(entry, b.get('expected_task_revision'))", 'pass',
     'test_manual_calendar_task_completion_is_shared_and_revision_checked'),
    ('capture-order', 'calendar_service.py', 'if older is not None and newer is not None and older < newer:', 'if False:',
     'test_older_capture_cannot_overwrite_newer_event'),
    ('calendar-synthetic', 'documents.py', "require(not output.synthetic, 'calendar_synthetic', 'Synthetic interpretation cannot become live events.')", 'pass',
     'test_calendar_output_cannot_be_synthetic'),
    ('pending-review', 'documents.py', "require(not self._task_changes(c, s['id'], doc), 'calendar_changes_pending', 'Review or dismiss the proposed shared-task changes first.', 409)", 'pass',
     'test_pending_task_proposal_blocks_whole_calendar_acceptance'),
    ('view-authority', 'calendar_service.py', "doc['data']['calendar_focus_revision'] == request.get('calendar_focus_revision', 0)", 'True',
     'test_voice_view_survives_delayed_period_interpretation'),
    ('shared-proposal-deduplication', 'calendar_service.py', "meaning(r['data']['values']) == meaning(values)", 'False',
     'test_duplicate_shared_proposals_from_collectors_are_one_review'),
    ('note-link-target', 'calendar_service.py', "note['kind'] == 'item' and note['data'].get('item_kind') == 'content' and note['data'].get('status') == 'accepted'", 'True',
     'test_calendar_note_link_must_name_a_note_on_the_canvas'),
    ('note-link-new-event-only', 'calendar_service.py', "not note_id or not b['entry_id'] and not b['task_id']", 'True',
     'test_calendar_note_link_is_only_set_on_a_new_event'),
]

if __name__ == '__main__':
    check_multi_target(MUTANTS, 'test_calendar.py', 90, 'calendar')
