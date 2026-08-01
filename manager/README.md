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

`BOT_TOKEN` digunakan untuk login bot manager. Login akun Telegram pengguna
menggunakan OTP dan Password Dua Langkah didukung melalui menu `📲 Minta Akses`.
`STRING_SESSION` pengguna tidak pernah dikirim ke chat; hanya disimpan di
database Manager Bot. Eksekusi Userbot belum diaktifkan.

## Menjalankan

```bash
cd manager
python main.py
```

Saat mulai, database SQLite dan tabel `users` dibuat otomatis. Plugin pada
`manager/plugins/` dimuat otomatis oleh `loader.py`.

## Tahap login Telegram

1. Buka `/start`, lalu pilih `📲 Minta Akses`.
2. Bagikan kontak Telegram atau kirim nomor internasional secara manual.
3. Masukkan OTP yang dikirim Telegram.
4. Masukkan Password Dua Langkah jika diminta.
5. Setelah berhasil, status akun berubah menjadi `Aktif`.

Sesi login sementara memiliki batas waktu dan dibersihkan setelah proses
selesai, gagal, dibatalkan, atau timeout.
