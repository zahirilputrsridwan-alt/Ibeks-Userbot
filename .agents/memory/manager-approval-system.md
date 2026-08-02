---
name: Manager approval system
description: Owner-gated approval is separate from Telegram login success.
---

A successful Telegram login stores the session but always starts with `approval_status` set to `pending`; only the configured Owner ID may approve or reject the request.

**Why:** Authentication proves account ownership, but access to the IBEKS service requires an explicit Owner decision.

**How to apply:** Keep approval callbacks Owner-checked at execution time, make approve/reject transitions idempotent, notify the user after the decision, and clear the stored session on rejection.