# IBEKS MANAGER BOT

Pondasi Telegram Manager Bot untuk mengelola layanan IBEKS USERBOT.

## Runtime

- Python 3.11
- Pyrogram 2.0.106
- SQLite

## Secret yang diperlukan

Tambahkan secret berikut di Replit:

- `BOT_TOKEN`
- `API_ID`
- `API_HASH`

`BOT_TOKEN` digunakan untuk login bot manager. Tidak ada `STRING_SESSION`,
login OTP, atau eksekusi Userbot pada tahap ini.

## Menjalankan

```bash
cd manager
python main.py
```

Saat mulai, database SQLite dan tabel `users` dibuat otomatis. Plugin pada
`manager/plugins/` dimuat otomatis oleh `loader.py`.
