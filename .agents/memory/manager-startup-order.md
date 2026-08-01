---
name: Manager startup order
description: Startup ordering rule for reliable Manager Bot handler registration.
---

The Manager Bot must validate Secrets and initialize SQLite, start and authenticate the Pyrogram client, then load plugins and register handlers. The final readiness log must occur only after required core plugins are loaded.

**Why:** Registering plugins before `client.start()` made the startup sequence misleading and could leave `/start` unavailable or unverified even though the loader reported success.

**How to apply:** Keep plugin import failures logged to both the file logger and console, require the start/account/admin core plugins after loading, and keep `/start` constrained to private chats.