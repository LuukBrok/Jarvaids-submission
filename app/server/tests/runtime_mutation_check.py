"""Named runtime guards; a test error is never a successful mutation result."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mutation_runner import check_multi_target

MUTANTS=[
    ('first-loop-success','runtime.py',"elif not state['successful']:status='starting'","elif False:status='starting'",'test_liveness_remains_up_while_readiness_requires_first_success'),
    ('loop-staleness','runtime.py',"elif age>self.limits[name]:status='stalled'","elif False:status='stalled'",'test_loop_clock_stalls_and_begin_cannot_erase_failure'),
    ('write-transaction-probe','runtime.py',"connection.execute('BEGIN IMMEDIATE')","connection.execute('BEGIN')",'test_store_write_contention_is_bounded_and_not_ready'),
    ('existing-store-only','runtime.py',"connection=_open_existing(self.path,'rw')","connection=_open_existing(self.path,'rwc')",'test_readiness_does_not_recreate_a_missing_store'),
    ('diagnostic-authority','service.py',"self._facilitator(actor)\n                result=session_metrics", "pass\n                result=session_metrics",'test_removed_facilitator_cannot_read_diagnostics'),
    ('attention-bound','runtime.py','ORDER BY rowid DESC LIMIT 20','ORDER BY rowid DESC LIMIT 200','test_diagnostics_bounds_and_redacts_attention_and_aggregates'),
    ('reason-redaction','runtime.py',"row['reason'] if row['reason'] in SAFE_JOB_REASONS else 'unclassified_failure'","row['reason']",'test_diagnostics_bounds_and_redacts_attention_and_aggregates'),
    ('pending-completion-readiness','service.py',"and completion=='clear' and cleanup=='clear')","and cleanup=='clear')",'test_pending_completion_and_maintenance_faults_keep_readiness_false'),
    ('pending-cleanup-readiness','service.py',"and completion=='clear' and cleanup=='clear')","and completion=='clear')",'test_pending_completion_and_maintenance_faults_keep_readiness_false'),
    ('store-cache-age','runtime.py',"\n        if self.cached is not None and self.checked is not None and 0<=now-self.checked<1.0:","\n        if self.cached is not None and self.checked is not None and 0<=now-self.checked<100.0:",'test_store_probe_cache_expires_and_concurrent_probe_does_not_wait'),
]


def main():
    return check_multi_target(MUTANTS, 'test_runtime*.py', 60, 'runtime', 'runtime')


if __name__=='__main__':
    raise SystemExit(main())
