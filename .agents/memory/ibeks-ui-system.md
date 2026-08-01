---
name: IBEKS UI system
description: Shared Telegram presentation rules for text-only plugins.
---

All text-only plugin output should pass through the shared UI sender, which tries HTML expandable blockquote, normal HTML blockquote, then plain text. Media and animation plugins remain outside that pipeline.

**Why:** Telegram clients may reject expandable blockquotes or parse dynamic text differently; a centralized fallback prevents raw markup and keeps the bot's visual identity consistent.

**How to apply:** Keep report bodies as plain text at plugin boundaries, preserve deterministic report builders, and never migrate media/document/animation handlers to expandable text UI.