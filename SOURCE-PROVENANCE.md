# Source provenance

| Item | Value |
| --- | --- |
| Tool | Jarvaids |
| Preparation date | 28 October 2026 |
| Development repository | https://github.com/ptborst/GenAI |
| Integrated source commit | `198eddceb10096805ad8e10a1186bc7086486657` |
| Policy | Copy tracked source, excluding `week 3 materials/`; initialise fresh Git history |
| Source files copied | 472 |
| Research files omitted | 18 |

The research folder was excluded by path without reading or copying its contents.
Ignored files were never copied. In particular, `.env`, `.local/`, `evidence/raw/`,
session credentials, dependencies and local model weights are absent. No
historical Git objects were imported.

Original contribution records and source revision references are retained. The
development repository is unchanged. Removal here does not purge its history.

Preparation changes are limited to README/app entry-point documentation, assessor
and provenance guides, ignore patterns and this work package's log entries.
Runtime source is unchanged from the integrated commit. Older guides remain
dated development records; setup starts at README.md.

## Published repository

The source submission is published at
[LuukBrok/Jarvaids-submission](https://github.com/LuukBrok/Jarvaids-submission).
The repository is **private**, as requested by Luuk on 28 October 2026. It was
briefly public during initial publication before that correction. It has fresh
submission history and no development-history objects. The original private
development repository remains unchanged. Assessors require individual GitHub
invitations before they can open the submission repository.

Use the repository URL for the Brightspace source-link entry. GitHub's commit
history identifies the exact submitted source revision.

## Submission checks

The following checks were run on this submission snapshot on 28 October 2026:

| Check | Result |
| --- | --- |
| Backend suite, installed Python 3.12 runtime | 639 tests completed, OK with 2 skips |
| JavaScript unit suite | 344 passed, no failures or skips |
| HTTP client/two-client journey | Passed |
| Sync transfer budget | Passed, 1867 B and 1881 B compressed per client in the two fixtures, below 5 KB |
| Schema registry | Passed, versions 1 through 6 consistent |
| Proposal coverage | Passed, all 38 functionality numbers matched |
| New README/guide local links | All resolved |
| New/edited documentation whitespace | Passed |
| Credential-pattern scan | No matches in 474 submission files |
| Exclusion and ignore checks | No research recordings, private settings or session stores staged; empty raw-folder marker only |
| Source Git object comparison | Application files and original executable flags unchanged; only 5 existing documentation/ignore/log files changed, 2 new guides |

The first sandbox attempt could not access its temporary folder or loopback
sockets. The successful verification used a workspace scratch directory and
localhost permissions. The interrupted sandbox backend attempt is not counted
as a passing run. Verification logs remain ignored under `.local/verification/`.

No fresh full speech installation, live provider call, microphone/room trial,
browser journey, design audit or mutation-suite run is claimed for this
preparation. Those areas have the separately dated historical records. Runtime
source was not changed, and these checks do not prove real-meeting accuracy.
