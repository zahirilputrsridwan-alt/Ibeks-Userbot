"""
IBEKS USERBOT - Chat Lock

Perilaku:
- .lock dan .unlock hanya Owner.
- .lock dan .unlock otomatis dihapus.
- Setelah locked, pesan Owner ke chat tersebut tidak dikirim/ditampilkan.
- Pesan dari lawan chat dihapus dari sisi Owner.
- Lawan chat mendapat notifikasi 1x setiap sesi lock.
- Owner mendapat notifikasi lock/unlock.
- Notifikasi Owner tidak ikut terhapus.
"""

from pyrogram import StopPropagation, filters

from config import OWNER_ID
from db import is_chat_locked, set_chat_lock
from utils.filters import dynamic_command


# =========================================================
# SESSION STATE
# =========================================================

# Chat yang sudah menerima notifikasi lock
_notified_chats = set()


# Pesan yang memang sengaja dibuat oleh fitur lock.
# Format:
# (chat_id, message_id)
#
# Supaya tidak ikut dihapus oleh outgoing gate.
_allowed_outgoing = set()


# =========================================================
# HELPER
# =========================================================

def _is_lock_command(message):
    text = (
        message.text
        or message.caption
        or ""
    ).strip().casefold()

    if not text:
        return False

    command = text.split(maxsplit=1)[0]

    return command in (
        ".lock",
        ".unlock",
    )


async def _is_owner(client):
    if not OWNER_ID:
        return False

    try:
        me = await client.get_me()
    except Exception:
        return False

    return me.id == OWNER_ID


# =========================================================
# SETUP
# =========================================================

def setup(client):

    # =====================================================
    # 1. OUTGOING GATE
    #
    # Semua pesan Owner yang menuju chat locked
    # akan diblokir.
    # =====================================================

    @client.on_message(
        filters.me & filters.private,
        group=-100
    )
    async def locked_outgoing_gate(client, message):

        chat_id = message.chat.id

        # Kalau chat tidak locked, biarkan normal.
        if not is_chat_locked(chat_id):
            return

        # -------------------------------------------------
        # Pesan yang sengaja dibuat oleh fitur lock.
        # Jangan hapus.
        # -------------------------------------------------

        key = (chat_id, message.id)

        if key in _allowed_outgoing:
            _allowed_outgoing.discard(key)
            return

        # -------------------------------------------------
        # .lock / .unlock harus dibiarkan menuju handler
        # command masing-masing.
        # -------------------------------------------------

        if _is_lock_command(message):
            return

        # -------------------------------------------------
        # PESAN OWNER SETELAH LOCK
        #
        # Hapus supaya pesan tidak masuk ke chat.
        # -------------------------------------------------

        try:
            await client.delete_messages(
                chat_id,
                message.id,
                revoke=False
            )
        except Exception:
            pass

        # Hentikan handler lain.
        raise StopPropagation


    # =====================================================
    # 2. INCOMING GATE
    #
    # Pesan dari lawan chat ketika locked.
    # =====================================================

    @client.on_message(
        filters.incoming & filters.private,
        group=-100
    )
    async def locked_incoming_gate(client, message):

        chat_id = message.chat.id

        if not is_chat_locked(chat_id):
            return

        # -------------------------------------------------
        # Kirim notifikasi hanya 1x setiap sesi lock.
        # -------------------------------------------------

        if chat_id not in _notified_chats:

            try:
                notification = await client.send_message(
                    chat_id,
                    "⚠️ PESAN INI SEDANG DI KUNCI",
                    reply_to_message_id=message.id
                )

                # Tandai pesan notifikasi agar outgoing gate
                # tidak menghapusnya.
                _allowed_outgoing.add(
                    (chat_id, notification.id)
                )

                _notified_chats.add(chat_id)

            except Exception:
                pass

        # -------------------------------------------------
        # Hapus pesan asli dari sisi Owner.
        # -------------------------------------------------

        try:
            await client.delete_messages(
                chat_id,
                message.id,
                revoke=False
            )
        except Exception:
            pass

        raise StopPropagation


    # =====================================================
    # 3. .LOCK
    # =====================================================

    @client.on_message(
        dynamic_command("lock")
        & filters.me
        & filters.private
    )
    async def cmd_lock(client, message):

        chat_id = message.chat.id

        # Pastikan hanya Owner.
        if not await _is_owner(client):
            return

        # Kalau sudah locked, tidak melakukan apa-apa.
        if is_chat_locked(chat_id):
            return

        # -------------------------------------------------
        # Mulai sesi lock baru.
        # -------------------------------------------------

        _notified_chats.discard(chat_id)

        set_chat_lock(
            chat_id,
            True,
            source="manual"
        )

        # -------------------------------------------------
        # Hapus command .lock.
        # -------------------------------------------------

        try:
            await client.delete_messages(
                chat_id,
                message.id,
                revoke=True
            )
        except Exception:
            try:
                await client.delete_messages(
                    chat_id,
                    message.id,
                    revoke=False
                )
            except Exception:
                pass

        # -------------------------------------------------
        # Notifikasi Owner.
        #
        # Ini dikirim ke OWNER_ID, bukan ke lawan chat.
        # -------------------------------------------------

        try:
            notification = await client.send_message(
                OWNER_ID,
                "🔒 CHAT BERHASIL DI KUNCI"
            )

            # Jangan biarkan outgoing gate menghapus
            # notifikasi ini jika kebetulan berada di chat
            # yang sama.
            _allowed_outgoing.add(
                (OWNER_ID, notification.id)
            )

        except Exception:
            pass

        raise StopPropagation


    # =====================================================
    # 4. .UNLOCK
    # =====================================================

    @client.on_message(
        dynamic_command("unlock")
        & filters.me
        & filters.private
    )
    async def cmd_unlock(client, message):

        chat_id = message.chat.id

        # Pastikan hanya Owner.
        if not await _is_owner(client):
            return

        # -------------------------------------------------
        # Buka lock.
        # -------------------------------------------------

        set_chat_lock(
            chat_id,
            False,
            source="manual"
        )

        # Reset sesi notifikasi.
        _notified_chats.discard(chat_id)

        # -------------------------------------------------
        # Hapus command .unlock.
        # -------------------------------------------------

        try:
            await client.delete_messages(
                chat_id,
                message.id,
                revoke=True
            )
        except Exception:
            try:
                await client.delete_messages(
                    chat_id,
                    message.id,
                    revoke=False
                )
            except Exception:
                pass

        # -------------------------------------------------
        # Notifikasi Owner.
        # -------------------------------------------------

        try:
            notification = await client.send_message(
                OWNER_ID,
                "🔓 CHAT BERHASIL DI BUKA"
            )

            _allowed_outgoing.add(
                (OWNER_ID, notification.id)
            )

        except Exception:
            pass

        raise StopPropagation