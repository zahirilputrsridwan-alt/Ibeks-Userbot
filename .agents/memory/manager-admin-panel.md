---
name: Manager admin panel
description: Durable rules for Owner-only Manager Bot administration.
---

The Manager Admin Panel is restricted to the configured Owner Telegram ID, and every callback or operation re-checks that identity. User mutations, membership extensions, broadcasts, statistics, and denied access attempts are recorded in SQLite audit logs.

**Why:** Hiding an Admin button is not an authorization boundary; callback data can be invoked directly, so authorization must be enforced at every entry point.

**How to apply:** Keep Admin operations in the domain module and the UI in its own plugin. Suspend must block Terminal access and stop the child Userbot; delete must confirm first and remove the user’s isolated runtime after the database record is deleted.