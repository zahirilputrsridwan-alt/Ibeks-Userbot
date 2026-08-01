---
name: IBEKS UI system
description: Shared Telegram presentation rules for text-only plugins.
---

 All text-only plugin output should pass through the shared UI sender, which preserves the original message body and adds Telegram's collapsed blockquote entity only. Media and animation plugins remain outside that pipeline.

**Why:** The old UI must remain byte-for-byte equivalent visually; HTML wrappers add headers, footers, and formatting changes. The current Pyrogram version exposes only the older blockquote type, so expandable behavior requires the newer raw entity with the `collapsed` flag and a safe fallback.

**How to apply:** Keep original Markdown/emoji/report bodies at plugin boundaries, parse them only into Telegram entities for transport, append one collapsed blockquote entity around the complete text, and never migrate media/document/animation handlers to expandable text UI.