"""Named summary guards must fail assertions when removed from scratch copies."""
from mutation_runner import check_multi_target

MUTANTS = [
    ('protect-manual-summary-note', 'summaries.py',
     "if not manual_note and note['data'].get('status') not in ('undone', 'rejected'):",
     "if note['data'].get('status') not in ('undone', 'rejected'):",
     'test_manual_correction_is_not_overwritten'),
    ('preserve-failed-batch-order', 'summaries.py',
     "if w['data']['status'] != 'done'", "if w['data']['status'] not in ('done', 'error')",
     'test_failure_blocks_later_batches_and_retry_preserves_sources'),
    ('source-quote-must-exist', 'summary_model.py',
     "ref['source_id'] in sources and quote in sources[ref['source_id']]",
     "ref['source_id'] in sources", 'test_invented_quote_or_owner_is_rejected'),
    ('summary-word-trigger', 'summaries.py',
     'or words >= self.SUMMARY_WORDS + self.SUMMARY_EXTRA_WORDS)', 'or words >= self.SUMMARY_WORDS)',
     'test_word_threshold_waits_until_sentence_boundary'),
]

if __name__ == '__main__':
    raise SystemExit(check_multi_target(MUTANTS, 'test_summaries.py', 60, 'summary'))
