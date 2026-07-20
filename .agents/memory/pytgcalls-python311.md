---
name: PyTgCalls Python 3.11 compatibility
description: PyTgCalls stable versions do not ship Python 3.11 wheels; use the pre-release line instead.
---

**Rule:** When installing PyTgCalls in this project (Python 3.11), do not pin a stable version. Use the pre-release line (e.g., `pytgcalls>=3.0.0.dev24`) and install with `--prerelease=allow`.

**Why:** Stable PyTgCalls versions depend on `tgcalls` wheels that only exist for CPython 3.6–3.9. The dev/3.0 line is the only one that resolves on Python 3.11 in this workspace.

**How to apply:** If the dependency is removed or needs reinstallation, run `uv add --prerelease=allow pytgcalls` and keep the pyproject.toml entry as `pytgcalls>=3.0.0.dev24` (or the latest available pre-release at that time).
