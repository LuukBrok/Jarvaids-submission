"""Named synthesis mutations run in disposable copies; errors never count as kills.

Each mutant removes one guard from synthesis.py or claude_synthesis.py, and the
test named beside it in test_synthesis_guards.py has to fail, not error.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mutation_runner import check_multi_target

S, C = 'synthesis.py', 'claude_synthesis.py'
MUTANTS = [
    # Phase 1: what a claim may cite.
    ('quote-check', S, 'if _normal(quote) not in spoken:', 'if False:',
     'test_claim_quote_must_appear_in_cited_segments'),
    ('cited-ids-exist', S, '        if unknown:\n', '        if False:\n',
     'test_claim_must_cite_segments_that_exist'),
    ('segment-order', S, 'if not 0 <= start <= end:', 'if not 0 <= start:',
     'test_segment_that_ends_before_it_starts_is_refused'),
    ('unreadable-note', S, "if note['reading'] == 'unreadable':", 'if False:',
     'test_unreadable_note_is_flagged_not_merged'),
    # Phase 2: every claim exactly once, and support from provenance.
    ('reconcile-missing', S, "errors.append('Claims appear in no point: %s.' % ', '.join(missing))", 'pass',
     'test_reconcile_refuses_a_dropped_claim'),
    ('reconcile-twice', S, "errors.append('Claims appear in more than one point: %s.' % ', '.join(twice))", 'pass',
     'test_reconcile_refuses_a_claim_counted_twice'),
    ('reconcile-invented', S,
     "errors.append('Point %d lists a claim that does not exist: %s.' % (index, claim_id))", 'pass',
     'test_reconcile_refuses_an_invented_claim'),
    ('support-derived', S, "return 'photo+speech' if kinds == {'photo', 'speech'} else kinds.pop()",
     "return 'photo+speech'", 'test_support_comes_from_sources_not_the_model'),
    # Phase 3: every point exactly once, relations real, the team's form kept.
    ('structure-missing', S, "errors.append('Points appear in no group: %s.' % ', '.join(missing))", 'pass',
     'test_structure_refuses_a_dropped_point'),
    ('structure-twice', S, "errors.append('Points appear in more than one group: %s.' % ', '.join(twice))", 'pass',
     'test_structure_refuses_a_point_in_two_groups'),
    ('relation-ends', S, 'if not all(isinstance(end, str) and end in known for end in ends) or ends[0] == ends[1]:',
     'if False:', 'test_relation_must_join_existing_points'),
    ('named-form', S, 'elif form and chosen != form:', 'elif False:', 'test_named_form_is_not_overridden'),
    ('group-cap', S, 'if len(ids) > MAX_GROUP:', 'if False:', 'test_group_cannot_exceed_the_server_cluster_cap'),
    ('structure-cap', S, 'if 0 < len(points) <= MAX_STRUCTURE_POINTS:', 'if 0 < len(points):',
     'test_over_sixty_points_are_not_sent_to_structure'),
    # Running: one repair, a budget, output kept out of git.
    ('no-repair', S, "    for attempt in (1, 2):\n        record['attempts'] = attempt\n        try:\n            result = ledger.call(step,",
     "    for attempt in (1,):\n        record['attempts'] = attempt\n        try:\n            result = ledger.call(step,",
     'test_gate_repairs_once_then_falls_back'),
    ('unbounded-repair', S, "    for attempt in (1, 2):\n        record['attempts'] = attempt\n        try:\n            result = ledger.call(step,",
     "    for attempt in (1, 2, 3):\n        record['attempts'] = attempt\n        try:\n            result = ledger.call(step,",
     'test_gate_repairs_once_then_falls_back'),
    ('budget', S, 'if self.spent >= self.budget:', 'if False:', 'test_budget_stops_before_the_next_call'),
    ('output-path', S, "return not path.is_relative_to(repo_root) or path.is_relative_to(repo_root / 'evidence' / 'raw')",
     'return True', 'test_output_must_stay_out_of_tracked_files'),
    # What leaves the machine.
    ('photo-exif', S, "clean.save(output, format='JPEG', quality=85)",
     "clean.save(output, format='JPEG', quality=85, exif=decoded.getexif())",
     'test_photo_sent_to_a_model_carries_no_exif'),
    ('photo-mpo', S, "(getattr(probe, 'n_frames', 1) != 1 and probe.format != 'MPO')",
     "getattr(probe, 'n_frames', 1) != 1", 'test_iphone_mpo_photo_is_read_from_its_primary_image'),
    ('photo-orientation', S, 'oriented = ImageOps.exif_transpose(decoded)', 'oriented = decoded',
     'test_photo_orientation_is_applied_before_sending'),
    ('photo-original', S, "model.read_photo(image, 'image/jpeg', repair)", "model.read_photo(raw, 'image/jpeg', repair)",
     'test_model_receives_the_prepared_photo_not_the_original'),
    ('module-identity', S, '    from genai_server.synthesis import main as package_main\n    raise SystemExit(package_main())',
     '    raise SystemExit(main())', 'test_adapter_errors_are_reported_not_raised_when_run_as_a_module'),
    ('env-override', C, "    if os.environ.get('ANTHROPIC_API_KEY'):\n        return\n    try:", '    try:',
     'test_env_key_never_overrides_the_environment'),
    # The Claude adapter never mistakes a refusal or a cut-off for an answer.
    ('refusal', C, "if message.stop_reason == 'refusal':", 'if False:', 'test_refusal_is_a_failure_not_an_answer'),
    ('cut-off', C, "if message.stop_reason == 'max_tokens':", 'if False:', 'test_cut_off_answer_is_a_failure_not_an_answer'),
    ('served-model', C, "return ModelResult(data, 'anthropic', message.model, False, usage)",
     "return ModelResult(data, 'anthropic', self.model, False, usage)", 'test_provenance_names_the_model_that_answered'),
]


def main():
    return check_multi_target(MUTANTS, 'test_synthesis_guards.py', 60, 'synthesis', 'synthesis')


if __name__ == '__main__':
    raise SystemExit(main())
