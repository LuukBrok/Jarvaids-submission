"""Named isolated-adapter guard mutations in disposable source copies."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mutation_runner import check_one_target

MUTANTS = [
    ('cancellation', 'test_cancellation_stops_hung_child_before_timeout',
     'if self.cancel_event is not None and self.cancel_event.is_set():', 'if False:'),
    ('total-deadline', 'test_hung_child_is_killed_and_next_call_progresses',
     '                if time.monotonic() - started >= self.timeout_seconds:',
     '                if time.monotonic() - started >= self.timeout_seconds * 6:'),
    ('parent-output-cap', 'test_native_output_is_bounded_and_child_terminated',
     'if len(received) + len(chunk) > MAX_OUTPUT:', 'if len(received) + len(chunk) > MAX_OUTPUT * 2:'),
    ('child-output-cap', 'test_oversized_result_is_refused',
     'if len(encoded) + len(chunk) > MAX_OUTPUT:', 'if False:'),
    ('parent-input-cap', 'test_input_limit_prevents_starting_adapter',
     'if len(payload) > MAX_INPUT:', 'if False:'),
    ('child-input-cap', 'test_child_refuses_overlong_input_even_with_valid_json',
     'if len(raw) > MAX_INPUT:', 'if False:'),
    ('child-note-cap', 'test_note_count_is_bounded_in_child',
     'or len(result.notes) > 60:', 'or False:'),
    ('timeout-configuration', 'test_timeout_must_be_finite_and_bounded',
     'if not math.isfinite(timeout_seconds) or not 0 < timeout_seconds <= 60:', 'if False:'),
]


def main():
    return check_one_target('isolated.py', MUTANTS, 'test_isolated.py', 30, 'isolation')


if __name__ == '__main__':
    raise SystemExit(main())
