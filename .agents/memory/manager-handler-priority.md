---
name: Manager handler priority
description: Pyrogram handler group ordering for explicit Manager commands.
---

Broad `private & incoming` handlers must use a later Pyrogram group than explicit menu commands such as `/start`. Pyrogram stops after the first matching handler in a group sequence, so broad login or relay handlers can otherwise consume menu commands before they reach the intended handler.

**Why:** The Manager appeared healthy but `/start` was silently consumed by a broad login handler until explicit command priority was added. An end-to-end Telegram send confirmed the fix.

**How to apply:** Put explicit Manager commands in an earlier (lower-numbered) group and keep conversation-state or relay-response handlers later. When Owner and Userbot identities can overlap, mark/identify forwarded command messages so the response handler cannot consume them. Verify with a real Telegram message, not only plugin-load logs.