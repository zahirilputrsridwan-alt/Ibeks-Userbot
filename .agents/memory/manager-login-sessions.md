---
name: Manager login sessions
description: Durable security and lifecycle rules for Telegram account login in IBEKS MANAGER BOT.
---

Each Telegram account login must use a separate in-memory Pyrogram client and per-user state. Persist only the resulting session string and account metadata after successful login; never send the session to chat.

**Why:** Sharing a client or retaining OTP/password state across users could authenticate the wrong account or expose credentials.

**How to apply:** Expire and clean up the state on success, failure, cancellation, timeout, or flood wait. Clear phone-code hashes and password/OTP variables after each attempt. Keep OTP and password input out of logs. Delete the user's OTP message only after the Telegram login succeeds; for 2FA accounts, retain it until the password step succeeds.