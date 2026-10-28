# Protecting main

Not settable from a coding session: it needs repository admin rights, and the
GitHub tooling available here has no branch-protection or ruleset call. These
are the settings to apply by hand, once, at
**Settings, Rules, Rulesets, New branch ruleset**.

## Why, specifically

Every rule below exists because of something that already happened in this
repository, not because it is conventional.

| Setting | Value | The thing it would have caught |
|---|---|---|
| Target | `main`, enforcement **Active** | Work has been committed straight to main before. `AGENTS.md` already forbids it; this makes it true rather than requested |
| Restrict deletions | on | |
| Block force pushes | on | A force push to main loses other people's work silently, and this repository has two people and two agents pushing |
| Require a pull request before merging | on, **0 approvals** | Zero, deliberately. A two-person course project cannot supply a reviewer for every change, and a required approval nobody can give turns into everyone using admin override, which is worse than no rule. The gate here is the checks, not a person |
| Require status checks to pass | on | |
| check `design-system` | required | |
| check `house-style` | required | |
| check `backend (3.11)`, `(3.12)`, `(3.13)` | required | The suite passed on one Python and was never run on another until CI |
| check `sync-budget` | required | INT13: a delta grew with the board, over the 5 KB budget, and the fixture that would have shown it was behind a flag |
| check `schema` | required | Two branches both numbered a migration version 2, one for positions and one for invitations. Both were green alone. A database written by either side would have been read as the other's shape |
| Require branches to be up to date before merging | **on** | This is the one that matters most. Both collisions above were green on their own branch and only existed in the union. Requiring the branch to be current forces the union to be tested before the merge, not after |
| Require conversation resolution | on | |

## What to leave off, and why

- **Required approvals above zero.** See above. Turn this on the moment a third
  person joins, and not before.
- **Require signed commits.** Nothing here needs it, and it would block both
  agents from pushing at all.
- **Include administrators.** Leave the override available. A two-person project
  needs a way out when CI itself is broken. The override is visible in the
  audit log, which is enough accountability at this size.

## Checking it took effect

Open a pull request that deliberately fails one check, for example by adding an
em dash to a file the branch already touches, and confirm the merge button is
blocked. A protection rule nobody has watched fail is a rule nobody knows is on.
