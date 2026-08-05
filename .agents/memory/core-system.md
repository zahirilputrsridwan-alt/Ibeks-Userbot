---
name: Core system boundaries
description: Core command, prefix persistence, restart notification, and plugin error isolation rules.
---

Core commands use the existing dynamic prefix filter and shared IBEKS UI. Prefix changes are limited to `.`, `/`, `!`, and `?`, and are stored per logged-in Telegram account in SQLite.

**Why:** Prefix persistence must survive worker restarts without changing the plugin loader or existing command registration pattern.

The restart marker is process-local runtime state; after startup, the Userbot sends the success notification only to the private Bot Manager chat, never to the command's originating group.

**Why:** Userbot workers are supervised child processes and restart commands may be issued in groups, while restart status belongs in Manager.

Plugin callback exceptions are isolated at the Pyrogram client handler boundary and written with plugin, command, error type, detail, and traceback metadata under `logs/`; one failing plugin must not stop other handlers.

**Why:** Pyrogram already catches callback errors, so the global layer must enrich that boundary rather than replace the loader or let exceptions escape into process shutdown.