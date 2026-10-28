"""Named mutations of the Claude extractor run in disposable copies; errors never count as kills.

Each mutant removes one guard from claude_extractor.py, and the test named
beside it in test_claude_extractor.py has to fail, not error.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mutation_runner import check_multi_target

E = 'claude_extractor.py'
MUTANTS = [
    # Every region sent is answered exactly once, and nothing else is invented.
    ('regions-match', E, '        if sorted(ids) != sorted(crops):', '        if False:',
     'test_an_invented_region_fails_the_job'),
    # A gap stays a gap: no text means unreadable, and unreadable means no text.
    ('readable-needs-text', E, "readable = answer['status'] == 'readable' and answer['text'].strip() != ''",
     "readable = answer['status'] == 'readable'", 'test_readable_with_no_text_becomes_unreadable'),
    ('unreadable-no-text', E, "'text': answer['text'].strip() if readable else '',",
     "'text': answer['text'].strip(),", 'test_unreadable_note_carries_no_text'),
    ('confidence-range', E, "'confidence': confidence if 0 <= confidence <= 1 else None,",
     "'confidence': confidence,", 'test_confidence_outside_zero_to_one_is_dropped_not_clamped'),
    # A refusal or a cut-off is never an answer, and provenance names who answered.
    ('refusal', E, "if message.stop_reason == 'refusal':", 'if False:', 'test_refusal_is_a_failure_not_an_answer'),
    ('cut-off', E, "if message.stop_reason == 'max_tokens':", 'if False:', 'test_cut_off_answer_is_a_failure_not_an_answer'),
    ('served-model', E, "return ExtractionOutput(tuple(notes), 'claude', message.model, False, usage)",
     "return ExtractionOutput(tuple(notes), 'claude', self.model, False, usage)",
     'test_provenance_names_the_model_that_answered'),
    # What is sent, and what is measured rather than asked.
    ('crop-size', E, '    image.thumbnail((MAX_EDGE, MAX_EDGE))\n', '', 'test_large_crops_are_scaled_down_before_sending'),
    ('colour-median', E, 'ImageStat.Stat(centre).median', '(round(v) for v in ImageStat.Stat(centre).mean)',
     'test_paper_colour_ignores_ink'),
]


def main():
    return check_multi_target(MUTANTS, 'test_claude_extractor.py', 60, 'extractor', 'extractor')


if __name__ == '__main__':
    raise SystemExit(main())
