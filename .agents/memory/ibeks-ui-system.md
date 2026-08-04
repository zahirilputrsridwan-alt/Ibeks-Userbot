---
name: IBEKS UI system
description: Shared Telegram presentation rules for text-only plugins.
---

 All text-only plugin output should pass through the shared UI sender, which preserves the original message body and adds Telegram's collapsed blockquote entity only. Media and animation plugins remain outside that pipeline.

## Per-plugin field ownership

Text UI must not generate generic labels, fallback fields, or inferred headings. Each plugin owns its own visible field names and may build its card directly; the shared sender only transports the resulting text.

**Why:** Generic `Label`/`Info` rows made reports longer and hid the actual meaning of fields such as Target, ID, Aura, Outfit, and Tier.

**How to apply:** When editing a plugin, write the real field name at the output boundary. Never add a label-parsing or template-generator layer to `send_ui`/`edit_ui`.

**Why:** The old UI must remain byte-for-byte equivalent visually; HTML wrappers add headers, footers, and formatting changes. The current Pyrogram version exposes only the older blockquote type, so expandable behavior requires the newer raw entity with the `collapsed` flag and a safe fallback.

**How to apply:** Keep original Markdown/emoji/report bodies at plugin boundaries. With the current Pyrogram runtime, send/edit through the standard text path rather than manually supplying high-level entities; never migrate media/document/animation handlers to expandable text UI.

**Compatibility note:** Pyrogram 2.0.106 injects `_client` into manually supplied entities, but the custom expandable entity and parsed high-level entities do not expose that slot. The safe shared fallback is plain text with the original body preserved.

**Inline keyboard note:** Help navigation must send its `InlineKeyboardMarkup` directly through `client.send_message` and include the markup in `edit_message_text`; do not rely on the generic expandable-text helper for the initial Help message.

**Why:** The generic text helper is intentionally optimized for plain text output, while Help requires Telegram to receive an explicit keyboard on the first send and on every page edit.

**How to apply:** Keep this direct path limited to interactive Help UI; other text-only plugins should continue using the shared sender.

**Help bridge note:** `.help` is requested by STRING_SESSION Userbot through per-runtime IPC, while Manager BOT_TOKEN sends the keyboard UI and owns every `help_*` callback.

**Why:** Inline keyboards must be rendered and edited by the Manager bot; the Userbot must remain responsible for all other commands and runtime behavior.

**How to apply:** Consume each IPC request once, isolate bridge errors from polling, and keep the bridge limited to Help so login, approval, Runner, and other plugins stay unchanged.

**Runtime edge cases:** A request targeting the Manager bot's own private chat must fall back to the requesting Userbot's ID; the watcher must not consume requests until the Manager client is connected.

**Why:** Telegram rejects bot-to-self messages, and the bridge is started before `client.run()` completes, so processing during boot can otherwise drop valid requests.

**How to apply:** Preserve the request until `client.is_connected` is true, then use `user_id` only for the bot-self target; normal user/group chats continue using their original `chat_id`.

**Expandable report status:** Text-only long reports may now opt into HTML `<blockquote expandable>` through the shared sender, with the footer outside the blockquote.

**Why:** The requested UI is now explicitly limited to long text output and requires HTML parse mode; the existing media, animation, Voice Chat, and interactive-panel exclusions remain.

**How to apply:** Keep expandable output opt-in. Use `ParseMode.HTML` only for selected long-text sends/edits, escape dynamic values, and never apply it to media, animations, Voice Chat, clone/card, or inline-keyboard flows.

**Minimum height:** Keep expandable content at least six lines tall; short reports receive visual `│` separator lines inside the blockquote.

**Why:** Telegram may render a short expandable blockquote fully open instead of showing the collapse affordance.

**How to apply:** Add padding only in the shared expandable formatter, never in plugin handlers or business output construction.

**Scope rule:** The shared UI System is limited to ordinary text-only plugin output. Restore direct message sending for media, animation, Voice Chat, and inline/keyboard panel flows.

**Why:** Applying presentation wrappers to interactive or media flows changed their established behavior and made rollback/debugging harder without improving those interfaces.

**How to apply:** Before changing a sender, classify the plugin by output type. Preserve handlers, callbacks, permissions, auto-delete, sessions, and lifecycle logic; change only the text body for eligible text-only plugins.