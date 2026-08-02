# IBEKS MANAGER BOT

Project Manager Bot yang berdiri sendiri untuk mengelola pengguna IBEKS
USERBOT. Source code Userbot tidak diimpor atau digabungkan pada tahap ini.

## Tahap saat ini

Fondasi awal yang tersedia:

- Python 3.11 dan Pyrogram
- Login Bot API dengan `BOT_TOKEN`
- `API_ID` dan `API_HASH` dibaca dari Replit Secrets
- Plugin loader otomatis
- SQLite dengan tabel `users`
- `/start` dan inline keyboard
- Menu Akun Saya, Panduan, Tentang, dan login melalui Minta Akses
- Logging ke `manager/logs/manager.log`
- Global error handler agar error handler tidak mematikan bot
- Login Telegram dengan OTP dan dukungan Password 2FA
- Penyimpanan `STRING_SESSION` hanya di SQLite setelah login berhasil

## Secrets

Tambahkan Secrets berikut:

- `BOT_TOKEN`
- `API_ID`
- `API_HASH`
- `OWNER_ID` — Telegram ID Owner yang menerima dan memproses approval

`STRING_SESSION`, OTP, dan Password 2FA tidak pernah dikirim ke chat atau
ditulis ke log.

## Menjalankan

```bash
cd manager
python main.py
```

## Struktur

```text
manager/
├── main.py
├── config.py
├── requirements.txt
├── README.md
├── database.db
├── plugins/
│   ├── start/
│   ├── account/
│   ├── admin/
│   ├── auth/
│   └── utils/
├── logs/
└── assets/
```

Semua plugin yang memiliki fungsi `setup(client)` di bawah `plugins/`
dimuat otomatis saat startup.

## Catatan

Folder `userbot/` adalah project terpisah dan tidak digunakan oleh fondasi
Manager Bot ini.