---
name: Manager admin panel
description: Durable rules for Owner-only Manager Bot administration.
---

The Manager Admin Panel is restricted to the configured Owner Telegram ID, and every callback or operation re-checks that identity. Its command handler must run in a higher-priority Pyrogram group than broad login text handlers, otherwise `/panel` can be consumed before the dashboard sees it.

The Manager `/panel` is the Bot Manager Control Panel: its home screen exposes Plugin Manager, Theme Engine, Dashboard, and Settings, while every submenu uses the same message with Back/Home/Close callback navigation.

**Why:** The Manager and Userbot have separate panel implementations; changing the Userbot panel does not fix the Bot Manager `/panel`.

**How to apply:** Keep Manager callbacks under the `panel:` namespace, answer every CallbackQuery, re-check Owner access, and use `edit_message_text` for navigation instead of sending a new message.

**Why:** Hiding an Admin button is not an authorization boundary; callback data can be invoked directly, so authorization must be enforced at every entry point.

**How to apply:** Keep Admin operations in the domain module and the UI in its own plugin. Register explicit Admin commands before broad private-text/login handlers, and emit startup logs proving the plugin loaded and command registered. Suspend must block Terminal access and stop the child Userbot; delete must confirm first and remove the user’s isolated runtime after the database record is deleted.