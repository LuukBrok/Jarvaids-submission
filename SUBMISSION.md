# Jarvaids: source submission guide

Prepared for the IDEM307 group-project submission on 28 October 2026. The source
requirement is code/configuration as a GitHub link the course team can open or as
a ZIP, with no API keys or passwords. The report and video are separate hand-ins.

## Inspect or run

Start with [README.md](README.md) for setup on a new computer. This source snapshot
does not include the demonstration laptop's runtime, credentials or saved session.
The separate portable demonstration package is the route for inspecting the
saved completed test. Its launcher runs on the reader's own computer; a
`127.0.0.1` URL is not a public web link.

The original [tutor guide](TUTOR-DEMO.md) records the morning demonstration and its
time-limited session. It is historical evidence, not setup for a clean clone.

## Where to inspect the AI integration

| Question | Source |
| --- | --- |
| How do components connect? | [Integration record](INTEGRATION-20261027.md), [system flowchart](deliverables/documentation/flowchart.md) |
| What instructions/context shape output? | `prompts/`, live adapters in `app/server/genai_server/`, and `docs/` specifications |
| How does a designer direct and inspect results? | `app/client/`, [command phrases](docs/COMMAND-PHRASES.md), [trial guide](TEST-THIS-VERSION.md) |
| How were decisions made? | [Decision log](decisions/decision-log.md), [AI use log](decisions/ai-use-log.md) |
| What worked and what needed recovery? | [Trial findings](VOICE-AND-MP3-TEST-20261027.md) |
| Which checks can be repeated? | `tools/verify_local.py`, `.github/workflows/verify.yml`, `app/server/tests/`, `app/client/tests/` |

The final fictional trial used local speech processing and configured cloud
interpretation. Source-quotation checks constrain unsupported claims but do not
prove semantic correctness. People still need to inspect and correct results.
The README distinguishes connected features from conceptual requests and records
the export, voice and platform limitations.

## Verification

The [dated tutor guide](TUTOR-DEMO.md) records 639 backend tests with two skips,
344 JavaScript tests and the design audit for the demonstrated integration.
Those are prior results, not evidence of accuracy with real participants.

For a new run after setup:

```powershell
py -3.12 tools/verify_local.py backend
py -3.12 tools/verify_local.py contracts
```

`guards` runs mutation harnesses. `browser` needs the browser-test dependencies
and executable configured as documented in the existing test guides. Node 24 is
the CI configuration. Missing dependencies or skipped checks are not passes.
See [SOURCE-PROVENANCE.md](SOURCE-PROVENANCE.md) for this snapshot's own checks.

## GitHub handoff

The source submission is the **public** repository
[LuukBrok/Jarvaids-submission](https://github.com/LuukBrok/Jarvaids-submission).
Share this URL in Brightspace or directly with the tutor. Viewing and downloading
the source requires no GitHub invitation or sign-in. Public access was explicitly
authorised by Luuk on 28 October 2026 and checked without authentication.

The original team development repository remains private. Its earlier research
history is excluded from this clean source snapshot.

- Record the assessed commit from GitHub's history if the course team needs an
  exact source revision.
- Do not upload `.env`, `.local`, raw evidence or installed model/runtime files.
- A source ZIP through Brightspace remains the alternative source-code route.

This is the source-code hand-in link, not a hosted instance of the running tool.
Setup and the separate saved demonstration remain as described above.
