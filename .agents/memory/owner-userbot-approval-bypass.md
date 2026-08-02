---
name: Owner Userbot approval bypass
description: The Owner Userbot must start independently of Manager approval state.
---

The configured Owner ID bypasses approval for Userbot startup; ordinary accounts require `approval_status=approved`. Manager and the Owner Userbot run as separate workflows.

**Why:** Approval was added to the Manager flow while the Owner’s existing standalone Userbot was not part of the active Project workflow, so `/start` worked but the Owner Userbot was absent.

**How to apply:** Keep an explicit Owner access decision and log its reason before Userbot startup. Do not require a Manager database row or approval record for the Owner, and keep ordinary pending/rejected accounts blocked.