---
name: Standalone Userbot mode
description: The active deployment mode for IBEKS is the original standalone Userbot, without Manager Bot relay.
---

The active IBEKS runtime is the standalone Userbot. Its plugins receive commands through the normal Pyrogram `filters.me` path, use the Userbot directory directly, and do not depend on Manager Bot handshakes, relay filters, or Manager-owned runtime directories.

**Why:** The user explicitly chose to return all plugins to the pre-Manager behavior after relay and duplicate-message changes caused operational confusion.

**How to apply:** Do not re-enable Manager Bot as the active workflow or reintroduce relay-specific Userbot hooks unless the user explicitly requests the Manager architecture again. Keep the shared UI plain-text fallback because it is a Pyrogram compatibility fix, not a Manager feature.