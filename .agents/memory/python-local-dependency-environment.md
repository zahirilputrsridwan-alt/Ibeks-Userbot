---
name: Python local dependency environment
description: Environment-specific fallback for Python packages when the system interpreter cannot write to Nix site-packages.
---

When a Python dependency is declared by the project but the managed installation cannot write to the system site-packages, the running workflow uses the project-local `.pythonlibs` environment instead.

**Why:** The system Python installation is read-only in this workspace, so a normal package install can resolve successfully but fail during the write step.

**How to apply:** Keep the dependency in the project manifest and install it into the existing `.pythonlibs` environment; do not bypass the package firewall or alter the workflow to use a different Python runtime.