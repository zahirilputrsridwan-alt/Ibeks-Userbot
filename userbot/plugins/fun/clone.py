"""IBEKS USERBOT - Plugin Clone.

Satu-satunya command yang didaftarkan plugin ini adalah ``.clone``.
"""

import asyncio
import io

from pyrogram import filters
from pyrogram.errors import RPCError

from config import AUTO_DELETE_CMD
from utils.autodelete import auto_delete
from utils.filters import dynamic_command
from utils.logger import log


async def _download_target_photo(client, target):
    """Unduh foto profil target ke memory, atau kembalikan None."""
    if not target.photo:
        return None

    try:
        downloaded = await client.download_media(
            target.photo.big_file_id,
            in_memory=True,
        )
        if downloaded is None:
            return None
        if isinstance(downloaded, bytes):
            return io.BytesIO(downloaded)
        if hasattr(downloaded, "getvalue"):
            return io.BytesIO(downloaded.getvalue())
        if hasattr(downloaded, "read"):
            if hasattr(downloaded, "seek"):
                downloaded.seek(0)
            return downloaded
        log.warning("[Clone] Format hasil download foto tidak didukung.")
    except Exception as exc:
        log.exception("[Clone] Gagal mengunduh foto target %s: %s", target.id, exc)
    return None


def _telegram_error(exc: Exception) -> str:
    """Ambil alasan Telegram yang cukup jelas untuk ditampilkan ke user."""
    reason = str(exc).strip()
    return reason or exc.__class__.__name__


async def _notify(client, chat_id: int, text: str) -> None:
    """Kirim status tanpa membiarkan error jaringan mematikan handler."""
    try:
        await client.send_message(chat_id, text)
    except Exception as exc:
        log.exception("[Clone] Gagal mengirim status ke chat %s: %s", chat_id, exc)


def setup(client):
    """Daftarkan command .clone."""

    @client.on_message(dynamic_command("clone") & filters.me)
    async def cmd_clone(client, message):
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))
        chat_id = message.chat.id

        reply = message.reply_to_message
        if not reply or not reply.from_user:
            await _notify(client, chat_id, "❌ Reply ke pengguna yang ingin di-clone.")
            return

        target = reply.from_user
        photo_status = "tidak ada"
        errors = []

        # Bio tidak tersedia di object User reply; ambil dari chat target.
        target_bio = ""
        try:
            target_chat = await client.get_chat(target.id)
            target_bio = target_chat.bio or ""
        except Exception as exc:
            log.exception("[Clone] Gagal mengambil bio target %s: %s", target.id, exc)
            errors.append(f"bio ({_telegram_error(exc)})")

        # Foto diproses terpisah agar nama dan bio tetap bisa diclone.
        target_photo = await _download_target_photo(client, target)
        if target.photo and target_photo is None:
            photo_status = "tidak dapat diunduh"
        if target_photo is not None:
            try:
                await client.set_profile_photo(photo=target_photo)
                photo_status = "berhasil"
            except RPCError as exc:
                photo_status = f"gagal ({_telegram_error(exc)})"
                log.exception("[Clone] Telegram menolak foto target %s: %s", target.id, exc)
                errors.append(f"foto ({_telegram_error(exc)})")
            except Exception as exc:
                photo_status = f"gagal ({_telegram_error(exc)})"
                log.exception("[Clone] Gagal menerapkan foto target %s: %s", target.id, exc)
                errors.append(f"foto ({_telegram_error(exc)})")

        # Nama dan bio tetap dicoba walaupun foto tidak ada atau gagal.
        first_name = target.first_name or "IBEKS USERBOT"
        last_name = target.last_name or ""
        try:
            await client.update_profile(
                first_name=first_name,
                last_name=last_name,
                bio=target_bio if target_bio is not None else None,
            )
        except RPCError as exc:
            reason = _telegram_error(exc)
            errors.append(f"profil ({reason})")
            log.exception("[Clone] Telegram menolak data target %s: %s", target.id, exc)
        except Exception as exc:
            reason = _telegram_error(exc)
            errors.append(f"profil ({reason})")
            log.exception("[Clone] Gagal menerapkan data target %s: %s", target.id, exc)

        if errors:
            details = "; ".join(errors)
            await _notify(
                client,
                chat_id,
                f"⚠️ Profil berhasil diproses sebagian. Foto: {photo_status}. "
                f"Alasan: {details}.",
            )
            return

        suffix = "" if target.photo else " Foto target tidak tersedia, bagian foto dilewati."
        await _notify(client, chat_id, f"✅ Berhasil meng-clone profil target.{suffix}")