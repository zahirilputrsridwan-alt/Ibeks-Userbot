---
name: Telegram edit animation behavior
description: Pyrogram animation messages must avoid duplicate edits and preserve final output.
---

When an animation starts by sending its first frame, skip editing that message to the same first-frame text; Telegram can reject it as `MessageNotModified` and stop the task. Keep final output handling separate from command auto-delete when the result is intended to persist.

**Why:** A duplicate first-frame edit previously stopped the animation before later frames and prevented the result from appearing.

**How to apply:** For future Pyrogram animations, send frame one once, edit only subsequent frames, and ensure fallback result delivery does not inherit command-message deletion behavior.