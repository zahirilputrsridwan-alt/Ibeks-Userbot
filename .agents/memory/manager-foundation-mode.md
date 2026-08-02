---
name: Manager foundation mode
description: The new Manager Bot starts as an independent menu/database project before any account login integration.
---

The active Manager Bot foundation is intentionally separate from the Userbot source. It uses Bot API credentials, automatic plugin loading, SQLite users, menu callbacks, and logging only. OTP, Telegram session storage, Userbot process control, relay, membership, and admin operations are not part of this stage.

**Why:** The project was restarted from zero so the Manager architecture can be built incrementally without inheriting the previous relay and lifecycle complexity.

**How to apply:** Add later features as isolated Manager plugins and extend the database deliberately. Never import or execute `userbot/` from this foundation unless the user explicitly requests that integration in a later stage.