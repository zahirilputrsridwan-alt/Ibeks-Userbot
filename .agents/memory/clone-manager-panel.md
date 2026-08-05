---
name: Clone Manager panel
description: IPC and panel rules for controlling clone restore from Bot Manager.
---

Successful clone must not reply in the originating chat; it publishes one Manager-owned panel through per-runtime atomic IPC. The panel is keyed by Userbot ID and uses one Restore callback restricted to that Userbot owner.

**Why:** Clone control belongs in Manager, while each isolated Userbot still owns the profile mutation and backup files.

The Manager callback writes one action file, the Userbot reuses the same restore operation as `.restore`, and the result edits the existing panel instead of sending a new message.

**Why:** Reusing the restore function prevents command and panel behavior from drifting, and editing one panel avoids callback spam.