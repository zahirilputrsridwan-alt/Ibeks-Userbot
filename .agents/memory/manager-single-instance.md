---
name: Manager single instance
description: Runtime rule preventing duplicate Manager Bot connections.
---

Only one Manager Bot process may run in a workspace for the shared `BOT_TOKEN`, and each Telegram user session must have only one Manager-owned Userbot child. The standalone Userbot workflow must not run alongside Manager.

**Why:** Multiple Pyrogram connections for the same Bot token or user session can split/interfere with updates and execute commands twice. A standalone Userbot plus the Manager child caused duplicate broadcast progress messages.

**How to apply:** Keep the Manager lock file runtime-only and ignored by Git. Run the Userbot only through Manager's per-user child supervisor; do not include a standalone Userbot task in the Project workflow. When debugging duplicate or missing messages, inspect both Manager and Userbot process trees first.