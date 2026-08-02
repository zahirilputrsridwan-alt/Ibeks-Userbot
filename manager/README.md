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
- Menu Akun Saya, Panduan, Tentang, dan placeholder Minta Akses
- Logging ke `manager/logs/manager.log`
- Global error handler agar error handler tidak mematikan bot

OTP, session Telegram, dan login akun Telegram sengaja belum dibuat.

## Secrets

Tambahkan Secrets berikut:

- `BOT_TOKEN`
- `API_ID`
- `API_HASH`

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