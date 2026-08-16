---
name: Utility lock and downloader
description: Stage 8 utility boundaries for chat locking and supported media downloads.
---

Chat locks belong to the Userbot runtime SQLite database and are enforced before ordinary Userbot command handlers; only the configured Owner may change a lock, while the unlock command remains the sole exception in a locked chat. PM Control is a rejection gate only: `.pm nobody` must never create a lock or call Telegram block APIs. Legacy PM-control locks may be cleared only by explicit `.pm all` or `.pm contacts` commands, never by startup or an incoming PM.

**Why:** A PM rejection must preserve the sender's access to the profile and avoid turning a message policy into an account block. Explicit cleanup is needed only for blocks left by older versions, while manual Owner locks must remain untouched.

**How to apply:** Keep chat locks in the Utility plugin, use the existing dynamic prefix path, restrict legacy cleanup to `source='pm_control'`, and debounce repeated PM rejection replies in memory. Do not add lock checks to every legacy plugin.

Downloader scope is intentionally limited to TikTok and Instagram through `yt-dlp`, plus media from Telegram messages the currently logged-in Userbot can access through Pyrogram.

**Why:** These are the only Stage 8 services requested, and Telegram access must use the active Userbot session rather than a separate client.

**How to apply:** Reject unsupported hosts explicitly, send downloaded files directly to the originating chat, and keep temporary files cleaned up after sending.