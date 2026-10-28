# A/E/D delivery evidence

This matrix maps the expanded task list to the implementation. Mechanism-tested means synthetic automated evidence, not product readiness, device verification or a user study. No B/C ownership is reassigned.

| Requirements | Implemented evidence | Remaining limit |
| --- | --- | --- |
| A01-A03 invitation and independent credentials | Single-use expiry/revocation, exact retry binding, concurrent redemption, wrong-session refusal, plaintext-secret scans | A code is not real identity; deliberate self-redemption remains possible |
| A04 removal | Authentication/replay/history/media/crop/events/export denial and an in-flight author-removal barrier test | Historical actor IDs remain provenance |
| A05 roster concurrency | Expected roster revision, concurrent conflicting writers, last-facilitator removal/demotion guards | UI must preserve and resolve conflicts |
| A06-A08 agreement/admission/withdrawal | Authenticated self-targeting, timestamps, current-policy admission, retained existing acknowledgements, withdrawal blocks activation | Legacy credentials are preserved; unknown historic agreement timestamps are not invented |
| A09 LAN | Explicit binding and advertised Host/Origin validation, client crypto works without secure-context randomUUID | No physical phone/firewall test or encrypted public deployment |
| A10 recovery/identity limits | No credential recovery documented; token loss and device-mediated agreement limits explicit | Recovery provider remains a separate product decision |
| E01-E05 lifecycle | Separate state/roster/event revisions, no-op pause, lease preservation, stale activation/close refusal, closed-state read/export semantics | No reopen flow |
| E06 bounded controls | 1001 distinct heartbeat intents at zero logical budgets, bounded 128-result ledger, explicit old replay conflict, no heartbeat events; stop and close still work | Logical bounds are not total filesystem-byte or write-rate limits |
| E07 completion recovery | Selective event failure, complete database outage after extraction, lost acknowledgement after commit, recovery without another adapter call, deletion-generation coordination | Completed output retained in memory can be lost on process crash; live-provider duplicate cost requires its own policy |
| E08 deadlines/cancellation | Killable subprocess, real hangs, cancellation including closed stdout, independent job-deadline reconciliation, committed cancellation releases worker | Remote connect/read timeouts and external billing are provider-specific; detached child processes are unsupported |
| E09 purge isolation | One failed purge does not block another session; expired content inaccessible; retry succeeds | Whole-store unavailability still affects all sessions |
| E10 failure boundaries | Failed claim rollback, partial completion rollback, post-commit lost acknowledgement, deletion while completion fails, startup recovery baseline | No physical disk-full/power-loss experiment; injected SQLite failures are labelled synthetic |
| E11 fairness/capacity | Round-robin claims; 5 jobs/session and 32/instance; cancellation and pending-completion backpressure | No throughput, latency percentile or memory-capacity claim; deployment benchmarking remains open |
| E12 export at caps | Consistent nonpersistent snapshot export at zero record/request/content budgets, with exact manifest inclusion and no extra writes | Retrying a snapshot download may reflect later edits; physical unreadable storage cannot be exported |
| D01-D02 sanitisation/orientation | Real PNG/JPEG decode, corruption/APNG/cap tests, exact/asymmetric rotated pixels and crop dimensions, alpha/ICC policy documented | Visible identity is not anonymised; colour-managed fidelity and hardware memory benchmarks are not claimed |
| D03 media storage | Session-scoped immutable deduplication; repeated region versions contain references, not base64; media counted in content budget | No external object store |
| D04-D05 media/crops | Current author-participant or facilitator; pre-decode denial, stale region revision conflict and post-render reauthorisation | Historical metadata remains inspectable; crop route deliberately requires the current source revision |
| D06 migration | Current/history/retry payload rewrite, invalid legacy image removal, interrupted migration rollback/restart and legacy region orientation transformation | Malformed database structure fails startup; external backups retain their own policy |
| D07 purge/cache | Media/invitations/control ledger included in purge; retained completions cleared; deletion during crop generation refuses return | No persistent crop cache; downloaded copies and forensic process-memory recovery outside claim |
| D08 provenance | Source/item history retained and model/fixture origin survives human correction | Re-encoding is not anonymisation |

The first H gate was verified before production edits: 56 baseline tests passed on the merged H source, and the ten original guards were caught after portable scratch-runner repair. A bounded record-cap fixture replaced a loop derived from the mutated constant, so the test fails for the intended ceiling rather than a later quota.

The integrated candidate also corrects the export manifest inventory while adding E12. Source evidence is explicitly excluded and references require the retained session. This is an output release, not a standalone evidence bundle.

See BUILD-STATUS.md for exact commands/results. The design audit could not start under this Windows sandbox and is not marked passed. The broader H02/H05 and K/L/M programme is not certified by these changes, particularly arbitrary process interruption, resource benchmarking, client UX, phone connectivity and user evaluation.

## Combined main integration

The candidate also preserves B/C positions and transaction-based event tracking. Pause continues to preserve policy and proposals under A/E; the older B/C test that expected staling was reconciled to that intentional lifecycle decision. Delta snapshots include actor control sequence and safe export projection. Both published database histories converge to schema 5. The populated-board bandwidth target remains unmet because board order is sent in full. No new device or Swift compatibility claim is made.

## Post-merge assigned follow-ups

| Task | Implementation and mechanism evidence | Remaining boundary |
| --- | --- | --- |
| INT01 | Preflight before writes checks published layouts, columns/order/types, keys/uniqueness, defaults/nullability and session foreign keys; supported histories restart; malformed files are unchanged on rejection | No physical repair, row-content audit or arbitrary trigger/view certification |
| INT02 | Removal denies snapshot/delta/events/record/history/media/crop/export and cached writes; demotion rechecks evidence/export/replay permissions; writes between pages and rollback descriptors are tested | Actual UI subscription and reconnect evidence belongs to INT05; large board cascades remain with INT12 |
| INT07 | No reset by reused name/session ID; remaining facilitator can revoke and re-invite with a new actor and fresh policy acknowledgement | Lost sole-facilitator access is deliberately unrecoverable; credential storage/device UX remains client work |
| INT08 | Output-only manifest metadata and exact inclusion in both release modes; downloaded JSON/Markdown stays readable after deletion while evidence unavailability is explicit | No automatic redaction or bundled source release |
| INT10 | No automatic retry after a claimed job; explicit uncertainty acknowledgement; real subprocess exit after synthetic provider success; expiry ordering and retained usage on discarded output tested | Live provider deadlines, idempotency, remote billing reconciliation and hard budgets still require provider-specific work |

See FOLLOWUP-STATUS.md for current commands, counts and measured limits.
