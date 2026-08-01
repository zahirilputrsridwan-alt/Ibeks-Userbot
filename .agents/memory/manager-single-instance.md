---
name: Manager single instance
description: Runtime rule preventing duplicate Manager Bot connections.
---

Only one Manager Bot process may run in a workspace for the shared `BOT_TOKEN`. A non-blocking file lock prevents duplicate workflow/manual instances from consuming Telegram updates simultaneously.

**Why:** Multiple Pyrogram connections for the same Bot token can split or interfere with updates, making `/start` appear unresponsive even when each process logs a successful login.

**How to apply:** Keep the lock file runtime-only and ignored by Git. When debugging missing Bot responses, check for duplicate Manager processes before changing handlers or plugin code.