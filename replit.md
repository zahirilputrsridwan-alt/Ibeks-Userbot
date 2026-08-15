# IBEKS MANAGER BOT + USERBOT

Telegram Userbot modern berbasis Python 3.11 + Pyrogram, struktur modular, plugin loader otomatis, dan SQLite.

## Run & Operate

- Workflow: **IBEKS MANAGER BOT** → `cd manager && python main.py`
- Manager required secrets: `BOT_TOKEN`, `API_ID`, `API_HASH`, `OWNER_ID`
- Userbot required secrets: `API_ID`, `API_HASH`, `STRING_SESSION`
- Userbot logs: `manager/userbot_runtime/<telegram_id>/logs/ibeks.log`

## Stack

- Python 3.11
- Pyrogram 2.0.106 + TgCrypto 1.2.5
- PyTgCalls 3.0.0.dev24 for voice-chat features
- SQLite (bawaan Python, db di `userbot/database.db`)
- python-dotenv 1.0.1
- psutil 5.9.8

## Where things live

- Entry point: `userbot/main.py`
- Konfigurasi: `userbot/config.py`
- Plugin loader: `userbot/loader.py`
- Database helpers: `userbot/db.py`
- Plugins: `userbot/plugins/<kategori>/<nama>.py`
- Utilities: `userbot/utils/`

## Architecture decisions

- Plugin loader scan `plugins/` secara rekursif — tambah file `.py` baru, langsung aktif tanpa import manual.
- `in_memory=True` di Pyrogram: session tidak disimpan ke disk, selalu pakai STRING_SESSION dari secret.
- Auto-delete hanya hapus pesan command (bukan reply) via `asyncio.create_task` agar tidak blocking.
- SQLite dengan `check_same_thread=False` + thread-local connection untuk kompatibilitas asyncio.
- Semua kredensial dibaca dari environment, tidak pernah hardcode.

## Product

IBEKS USERBOT — Tahap 1 aktif:
- `.ping` — status bot, uptime, RAM, CPU, owner
- `.alive` — cek status online + info versi
- `.pm all|contacts|nobody` — mengatur siapa yang boleh mengirim PM
- `.pmmsg set|status|reset` — mengatur pesan penolakan PM
- `.tagreply on|off|set|status|reset` — mengatur balasan mention di grup

## User preferences

- Bahasa Indonesia untuk dokumentasi dan komentar kode.
- Struktur modular: setiap command dalam file plugin terpisah.
- Kembangkan secara bertahap, tunggu instruksi per tahap.

## Gotchas

- Jalankan `pip install -r manager/requirements.txt` dan
  `pip install -r userbot/requirements.txt` jika packages hilang.
- Untuk generate STRING_SESSION baru: `python -c "from pyrogram import Client; c=Client(':memory:',int(input('id:')),input('hash:')); c.start(); print(c.export_session_string()); c.stop()"`
- Plugin hanya aktif saat bot direstart setelah menambahkan file plugin baru.

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
