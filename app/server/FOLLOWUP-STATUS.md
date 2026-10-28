# Assigned backend follow-ups, 16 September 2026

Based on main `9a16d1c83a7d6d2ddb9afbdfdb99adf47841a0ea`. The publishing
pull request records the exact candidate. Scope: INT01, INT02, INT07, INT08 and
the local recovery portion of INT10. Other workstreams retain board/sync,
general input validation, harness consolidation and CI work.

## Executed checks

| Check | Observed result |
| --- | --- |
| `python -m unittest discover -s tests` | 197 tests passed in 50.977 seconds, Windows / Python 3.14 / Pillow 12.0.0 |
| `python tests/mutation_check.py` | All 52 service/position/transport/recovery guards caught by named assertions |
| `python tests/schema_mutation_check.py` | All 12 schema guards caught by named assertions |
| `python tests/isolated_mutation_check.py` | All 8 isolation guards caught |
| `python tests/media_mutation_check.py` | All 9 media guards caught |
| `node tests/client-unit.mjs` | Passed |
| CLI demo and JavaScript HTTP smoke | Passed against an actual CLI process on an ephemeral loopback port |
| Contrast checker | 105 pairs across four schemes passed on the unchanged design-system files |
| Bash design audit | Unavailable: `bash` was not found in this shell; earlier attempts in this workspace also failed to start Bash. No passing audit claim |

There are 81 named mutants across the four current harnesses. Removing a guard
must cause its designated behavioural assertion to fail; errors are rejected as
evidence. Harness consolidation is a separate assigned task and must retain all
these protections. No Python source changed after these checks.

## New evidence

- Seventeen schema tests cover both published histories and intermediate
  migration stages, with repeated restart. Layout, column order/type,
  primary/unique keys, required nullability/defaults and foreign keys are
  checked before connection pragmas or migration writes. Rejected files remain
  byte-identical; a WAL test checks that journal mode is not rewritten.
- Sixteen follow-up tests cover removal/demotion across reads and cached
  commands, event paging with intervening writes, rollback descriptors,
  credential-loss boundaries, output release and recovery.
- A real subprocess exits immediately after a synthetic provider completes,
  before result persistence. Startup does not call it again; an explicit new
  retry acknowledgement is required. Separate tests cover restart after job
  deadline and lease expiry so cleanup cannot erase uncertainty.
- Returned synthetic usage remains recorded when pause or storage rejection
  prevents proposals. These are accounting-path tests, not evidence of actual
  charges, provider cancellation or pricing.
- Downloaded output JSON/Markdown remains readable after session deletion;
  evidence references are explicitly unavailable without the original session.
  Both inclusion modes have exact manifest/record equality. No evidence bundle
  or automatic redaction is created.

## Decisions and limits

Sole-facilitator credential loss is deliberately unrecoverable. A remaining
facilitator can revoke and re-invite, creating a new actor with fresh policy
acknowledgement. Display names do not establish identity. Client credential
storage and real-device journeys remain unverified.

Interrupted claims fail with unknown execution/usage rather than being silently
requeued. The new acknowledgement addresses uncertain execution. Completed
output can still have unknown cost, and separate explicitly requested jobs can
run concurrently within queue caps. This is not provider idempotency or a hard
spending limit. Live-provider connect/read deadlines, cost enforcement and remote
reconciliation remain open under INT10.

Schema validation recognises the supported structural contract. It does not
repair physical corruption, audit row contents, or certify arbitrary trigger/view
behaviour. Semantically equivalent but differently written defaults may be
refused; no extra schema version is introduced. Keep an operational backup before
upgrades and investigate rejected layouts without modifying their files blindly.

The coordinating assistant reviewed the implementation; a delegated review
caught the startup cleanup ordering defect before the final tests. Human
line-by-line review, phones, Swift compilation, actual OCR, live providers and
user evaluation were not performed. Passing mechanism checks do not establish
product readiness.
