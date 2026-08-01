---
name: Broadcast deduplication
description: Rules for preventing duplicate GCAST/UCAST progress and result messages across the Manager relay and Userbot child.
---

GCAST/UCAST must be deduplicated at both transport boundaries and at command execution. Do not rely only on Telegram message IDs: duplicate updates may arrive with different IDs, so use a short-lived content key and prevent concurrent broadcasts for the same chat. Result templates must also be checked for repeated literal lines.

**Why:** Duplicate “GCAST sedang berjalan…” output can come from replayed relay updates, concurrent child handlers, or a duplicated result-template line; fixing only the process count does not cover all paths.

**How to apply:** Keep short in-memory dedupe windows on Manager command/response relay and Userbot broadcast handlers. Avoid retrying a send after an ambiguous Telegram send error, because the first request may already have been accepted.