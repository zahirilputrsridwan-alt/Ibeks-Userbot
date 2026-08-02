---
name: Manager single-instance foundation
description: The standalone Manager foundation must guard its Bot API token with a process lock.
---

The Manager Bot foundation uses a filesystem `fcntl` lock before creating the Pyrogram client, so only one Manager process can consume the configured Bot Token at a time.

**Why:** Multiple Manager processes were able to start under separate workflow restarts and each responded to `/start`, producing duplicate menus.

**How to apply:** Keep the lock acquisition before bot startup and release the file handle on shutdown. If duplicate Bot API responses recur, inspect running Manager PIDs before changing handlers.