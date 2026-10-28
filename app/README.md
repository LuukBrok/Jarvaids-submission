# Jarvaids prototype

Use the [repository README](../README.md) to install and start the integrated
tool on a new computer. [The assessor guide](../SUBMISSION.md) maps source files,
AI instructions, development records and verification limits.

| Folder | Role |
| --- | --- |
| `client/` | Browser workspace; never holds API keys |
| `server/` | Python API, session store, speech and AI adapters; keys stay server-side |
| `design-system/` | Design specifications and audit tooling |
| `ios/` | Uncompiled exploration, not the demonstrated browser tool |

See the [trial guide](../TEST-THIS-VERSION.md) and
[observed findings](../VOICE-AND-MP3-TEST-20261027.md).
Failed summary work is visible and requires explicit retry. An uncertain or
failed provider call is not silently repeated. Source quotations and provenance
support inspection; editing and undo support correction. These mechanisms do not
establish accuracy. Slow providers, uncertain speakers and export omissions
remain documented limits.
