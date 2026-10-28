# Runtime signals and operational follow-up

Based on main `b76364f57650450c64f30ae9180abe166ed474af`. The publishing PR
records the exact candidate. This adds the L02/L03 backend diagnostic layer;
it does not complete physical storage, deployment or real-client acceptance.

## What the signals mean

| Signal | Meaning | Next check |
| --- | --- | --- |
| `/health` is 200 | HTTP handled the request | Read `/ready` before assuming processing is available |
| Worker/maintenance `starting` or `not_started` | No successful iteration observed | Confirm the configured CLI loops actually started; do not fake monitor ticks |
| Loop `failed` | Its last iteration raised an exception | Inspect the safe diagnostic categories and storage availability; do not log raw provider exceptions |
| Loop `stalled` | No timely progress under the diagnostic threshold | Inspect contention and the configured worker deadline; a listening socket is insufficient evidence |
| Store `busy` | Write transaction could not be acquired promptly | Retry with backoff and investigate prolonged transaction/lock contention |
| Store `unavailable` | Existing database could not be opened/read as required | Check the configured data location and permissions without creating a replacement store or deleting evidence |
| Store/completion `checking` | Another operation holds the short probe/observation lock | Retry later; do not display an unknown count as zero |
| Completion store `pending` | Validated results are waiting for persistence | Allow controlled completion retries; do not repeat extraction blindly |
| Maintenance cleanup `pending` | A cleanup operation remains unsuccessful | Inspect the owned-store failure and retention behaviour; expired content must remain inaccessible |
| Job execution outcome `unknown` | A claimed attempt lacks a confirmed result | Use the explicit acknowledged retry contract if another attempt is intended |

Readiness reports the current process and store transaction availability. It
does not gate stop/deletion commands, prove OCR correctness, check a provider
account, or certify a durable physical write. Readiness requests do no work on
behalf of the worker. A store result may be up to one second old.

The 90-second worker and 15-second maintenance thresholds are diagnostic
defaults, not measured service-level promises. SQLite probes use a 100 ms busy
timeout and a 250 ms query progress budget. Those budgets do not interrupt
arbitrary operating-system I/O stalls or cover HTTP request-body handling.
Physical disk-full, power-loss and restoration testing remain separate work.

## Diagnostic privacy and consistency

The current facilitator can obtain a bounded session diagnostic snapshot through
`GET /api/sessions/{sid}/diagnostics`. Keep bearer credentials in the normal
authenticated client; do not paste real credentials into examples or logs.

Durable counts, payload byte sizes and at most 20 attention jobs share a read-only
transaction. In-memory completion counts and loop states are sampled afterwards.
The attention list is newest-created first, not a complete incident history;
`attention_total` and `attention_truncated` disclose that limit. Null pending
counts mean the lock was busy, not that no result remains.

Only generated job IDs, fixed statuses/reasons and numeric aggregates are
returned. Participant names, titles, source text/images, credentials, database
paths and raw exception messages are excluded. Unknown stored categories are
mapped to fixed fallback values. Removal/demotion revokes diagnostic authority.
The endpoint does not sweep, change session state, emit events or create retry
records. Logical payload bytes do not measure physical file size or free space.

## Executed verification

| Check | Result |
| --- | --- |
| `python -m unittest discover -s tests` | 210 tests passed in 62.256 seconds |
| `python tests/mutation_check.py` | All 52 existing service/position/transport/recovery guards caught |
| `python tests/schema_mutation_check.py` | All 12 schema guards caught |
| `python tests/isolated_mutation_check.py` | All 8 isolation guards caught |
| `python tests/media_mutation_check.py` | All 9 media guards caught |
| `python tests/runtime_mutation_check.py` | All 10 runtime guards caught by named assertions |
| JavaScript unit checks, CLI demo and JavaScript HTTP smoke | Passed against the actual CLI process |
| Contrast checker | 105 pairs across four schemes passed on unchanged design-system files |
| Bash design audit | Unavailable in this Windows shell; the prior failed startup remains an unavailable check, not a pass |

Tests ran on Windows with Python 3.14 and Pillow 12.0.0. Thirteen runtime tests
cover actual CLI readiness, stale/failed/stopped loops, first-success gating,
short lock contention, missing-store protection, cache expiry, pending cleanup,
private bounded diagnostics, revocation, unchanged database bytes and a busy
in-memory observation lock. All 91 named guards across the five current harnesses
pass. Infrastructure errors do not count as successful guard checks.

The delegated test pass and coordinating code review do not substitute for human
line-by-line review. Physical corruption/exhaustion, throughput under real load,
phone/firewall journeys, Swift compilation, live providers and user evaluation
remain unverified. Keep these harness cases when the other workstream consolidates
the checks and adds CI.
