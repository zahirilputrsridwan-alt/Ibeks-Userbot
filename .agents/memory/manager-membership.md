---
name: Manager membership
description: Durable rules for membership expiry and future admin extensions.
---

Membership access is based on a UTC ISO expiry timestamp stored with the Manager user record. `Active` means expiry is strictly in the future; missing or past expiry is `Expired`. The initial 30-day grant happens only when a successful login has no existing expiry, while extensions build from the later of the current expiry or now.

**Why:** Repeated login must not silently renew access, and UTC timestamps avoid timezone-dependent command gates.

**How to apply:** Use the membership domain helpers for status, remaining days, and extensions. Check membership before Userbot availability or command forwarding, and keep Admin extension commands separate from the terminal relay.