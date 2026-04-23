# Plan Version Archive

This directory stores full markdown snapshots of accepted trip plan versions.

Workflow:

- `georgia-trip-plan-current.md` is the canonical working source.
- Each accepted version is stored here as a full snapshot file such as `v1.md`, `v2.md`, `v3.md`.
- When a comment targets a specific `stable_key`, only that block should be edited in the next version unless the owner explicitly requests broader changes.
- All untouched blocks should be copied forward without rewriting.
- Service imports should always use a full snapshot file from this archive.
