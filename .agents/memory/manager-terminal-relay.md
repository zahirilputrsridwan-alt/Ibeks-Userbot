---
name: Manager terminal relay
description: Durable design rules for routing Manager Bot commands and Userbot responses.
---

The Manager terminal must remain command-agnostic: read the active prefix from the per-user Userbot database, forward the message to the Userbot account, and copy every response message back. Userbot plugin discovery remains the only command source.

**Why:** Hardcoding commands would make new Userbot plugins unavailable through Manager and would create two divergent command systems.

**How to apply:** Keep the relay as a generic Manager plugin, change the Userbot owner filter centrally so existing and future `dynamic_command(...) & filters.me` handlers accept Manager messages, and use a private startup handshake because a Bot API bot cannot initiate an unopened chat with a user account.