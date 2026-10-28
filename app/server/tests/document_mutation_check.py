"""Named document guards, mutated only in disposable source copies."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mutation_runner import check_one_target

MUTANTS = [
    ('address-required', 'test_addressed_command_required_and_fixtures_do_not_start_lists',
     "creating = heard.get('status') == 'recognised' and intent in DOCUMENT_TYPES and not heard.get('document_action')", "intent = intent or 'todo'; creating = True"),
    ('fixture-gate', 'test_addressed_command_required_and_fixtures_do_not_start_lists',
     "if data['status'] != 'final' or data['provenance']['synthetic']:", "if data['status'] != 'final':"),
    ('whole-history', 'test_whole_history_is_batched_without_a_two_minute_cutoff',
     "if r['id'] in orders and r['data']['status'] == 'final'", "if r['id'] in orders and r['data'].get('captured_at_ms', 0) > 120000 and r['data']['status'] == 'final'"),
    ('evidence-quote', 'test_invented_evidence_is_rejected',
     "ref['source_id'] in sources and ref['quote'] in sources[ref['source_id']]['text']", 'True'),
    ('owner-date-evidence', 'test_invented_owner_deadline_commitment_and_completion_are_rejected',
     "grounded(patch[key+'_quote']) and normal(patch[key]) in normal(patch[key+'_quote'])", 'True'),
    ('actual-speaker', 'test_unknown_speaker_cannot_become_a_named_owner',
     "sources[r['source_id']]['speaker_id'] == patch['owner_speaker_id']", 'True'),
    ('manual-epoch', 'test_manual_edit_rejects_inflight_response',
     "or doc['data']['epoch'] != epoch", 'or False'),
    ('manual-barrier', 'test_manual_edit_wins_over_earlier_queued_changes',
     "if entry and entry['data'].get('manual_after', -1) >= wd['source_order']:", 'if False:'),
    ('capture-order', 'test_older_capture_cannot_overwrite_a_later_change',
     'if earlier is not None and later is not None and earlier < later:', 'if False:'),
    ('synthetic-output', 'test_synthetic_output_is_not_a_live_task',
     "require(not output.synthetic, 'document_synthetic', 'Synthetic interpretations cannot become live tasks.')", 'pass'),
    ('pending-acceptance', 'test_voice_close_drains_work_then_accepts_and_reopens',
     "not any(w['data']['status'] in (*PENDING, *UNRESOLVED) for w in works)", 'True'),
    ('coverage-acknowledgement', 'test_capacity_is_visible_and_incomplete_acceptance_needs_acknowledgement',
     "not incomplete or b.get('acknowledge_incomplete') is True", 'True'),
    ('retry-cost', 'test_error_requires_explicit_cost_acknowledgement_to_retry',
     "require(b['acknowledge_unknown_cost'] is True, 'document_retry_ack', 'A retry may incur additional API cost.')", 'pass'),
    ('cloud-agreement', 'test_enabling_whole_meeting_cloud_text_requires_new_agreement',
     'if not marker and not enabled:', 'if True:'),
    ('claim-authority', 'test_pausing_before_claim_prevents_a_provider_call',
     "if not self._document_authority(c, s, work) or doc['data']['state'] not in OPEN:",
     "if False or doc['data']['state'] not in OPEN:"),
    ('commit-authority', 'test_pausing_during_interpretation_prevents_committing_output',
     "if wd['status'] != 'running' or not self._document_authority(c, s, work)", "if wd['status'] != 'running' or False"),
    ('source-revision', 'test_transcript_change_during_interpretation_is_not_committed',
     "require(current['revision'] == ref['revision'], 'document_source', 'Transcript changed during interpretation.', 409)", 'pass'),
    ('batch-bound', 'test_oversized_transcript_line_is_not_sent_to_the_provider',
     "sum(len(line['text']) for line in lines) <= self.DOCUMENT_BATCH_CHARS and len(lines) <= self.DOCUMENT_BATCH_LINES", 'True'),
    ('removed-deduplication', 'test_removed_tasks_are_not_recreated_by_old_additions',
     "if patch['op'] == 'add' and any(normal(r['data']['text']) == normal(patch['text']) for r in entries.values()):", 'if False:'),
    ('entry-id-type', 'test_new_task_identifier_and_removal_are_strict',
     "text(b['entry_id'], 'entry_id', 80, empty=True)", 'pass'),
    ('new-entry-removal', 'test_new_task_identifier_and_removal_are_strict',
     "require(bool(b['entry_id']) or not b['removed'], 'document_entry', 'A new task cannot already be removed.')", 'pass'),
]

if __name__ == '__main__':
    check_one_target('documents.py', MUTANTS, 'test_documents.py', 60, 'document')
