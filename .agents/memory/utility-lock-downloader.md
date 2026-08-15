---
name: Utility lock and downloader
description: Stage 8 utility boundaries for chat locking and supported media downloads.
---

Chat locks belong to the Userbot runtime SQLite database and are enforced before ordinary Userbot command handlers; only the configured Owner may change a lock, while the unlock command remains the sole exception in a locked chat. PM-control locks must carry a distinct source so `.pm all` never opens a manual Owner lock.

**Why:** Lock state must survive worker restarts without coupling Manager database state to each Userbot runtime.

**How to apply:** Keep the lock gate in the Utility plugin, use the existing dynamic prefix path, and filter PM unlocks by the PM-control source; do not add lock checks to every legacy plugin.

Downloader scope is intentionally limited to TikTok and Instagram through `yt-dlp`, plus media from Telegram messages the currently logged-in Userbot can access through Pyrogram.

**Why:** These are the only Stage 8 services requested, and Telegram access must use the active Userbot session rather than a separate client.

**How to apply:** Reject unsupported hosts explicitly, send downloaded files directly to the originating chat, and keep temporary files cleaned up after sending.