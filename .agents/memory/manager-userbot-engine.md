---
name: Manager userbot engine
description: Durable architecture rules for launching and controlling per-user IBEKS USERBOT processes.
---

Each logged-in account must run as its own child process, with its session passed through the child environment and its database, logs, restart state, and plugin backups isolated under a user-specific runtime directory. Keep the live registry keyed by telegram ID, use a per-user lifecycle lock, and ignore stale worker watchers so one account cannot overwrite another account's state.

**Why:** Userbot globals such as SQLite, logs, restart state, and clone backups are process-local paths; sharing them across accounts causes data leakage and lifecycle collisions.

**How to apply:** Keep lifecycle state in Manager SQLite, guard each user with a per-user lock, use internal locked start/stop helpers to avoid restart deadlocks, and always terminate supervisor tasks and child processes during Manager shutdown. Handle SIGTERM explicitly so workflow restarts do not orphan workers. Manual Stop suppresses reconnect until Start/Restart, while expired or suspended access must block all start paths.