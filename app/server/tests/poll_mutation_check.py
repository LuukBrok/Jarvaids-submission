"""Remove critical polling guards in disposable copies and prove tests notice."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mutation_runner import check_one_target


MUTANTS = [
    ('command-required', 'test_command_required_and_fixtures_never_start_polls',
     "heard.get('status') == 'recognised' and heard.get('intent') == 'voting' and not heard.get('poll_action')", 'True'),
    ('unknown-speaker', 'test_unknown_speaker_never_enters_tally_and_can_be_corrected',
     "if not profile or speaker_provenance.get('synthetic', True):", 'if False:'),
    ('model-provenance', 'test_synthetic_model_output_never_becomes_a_vote',
     "require(not output.synthetic, 'poll_synthetic', 'Synthetic interpretations cannot become live votes.')", 'pass'),
    ('definition-version', 'test_manual_edit_invalidates_inflight_model_response',
     "or pd['epoch'] != wd['epoch']", 'or False'),
    ('manual-priority', 'test_manual_correction_wins_over_earlier_queued_vote',
     "if old and order < old['data']['source_order']:", 'if False:'),
    ('capture-order', 'test_capture_order_prevents_late_older_reply_overwriting_newer_choice',
     'if earlier is not None and later is not None and earlier < later:', 'if False:'),
    ('cloud-agreement', 'test_enabling_cloud_for_old_session_requires_fresh_agreement',
     'if not marker and not enabled:', 'if True:'),
]

if __name__ == '__main__':
    check_one_target('polls.py', MUTANTS, 'test_polls.py', 60, 'poll')
