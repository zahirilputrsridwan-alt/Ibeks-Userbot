# 💀 IBEKS USERBOT

Telegram Userbot modern berbasis **Python 3.11** + **Pyrogram**, dibangun dengan struktur modular, plugin loader otomatis, dan SQLite.

---

## 🚀 Cara Menjalankan

### 1. Isi Replit Secrets

Buka panel **Secrets** di Replit dan tambahkan tiga secrets berikut:

| Key              | Keterangan                                  |
|------------------|---------------------------------------------|
| `API_ID`         | Dari [my.telegram.org](https://my.telegram.org) |
| `API_HASH`       | Dari [my.telegram.org](https://my.telegram.org) |
| `STRING_SESSION` | Generate menggunakan skrip di bawah         |

### 2. Generate STRING_SESSION

Jalankan skrip ini secara lokal atau di terminal Replit:

```bash
python -c "
from pyrogram import Client
with Client(':memory:', input('API_ID: '), input('API_HASH: ')) as c:
    print(c.export_session_string())
"
```

Masukkan nomor telepon & kode OTP saat diminta, lalu salin string yang dihasilkan ke secret `STRING_SESSION`.

### 3. Jalankan Bot

```bash
cd userbot
pip install -r requirements.txt
python main.py
```

Atau gunakan workflow **IBEKS USERBOT** yang sudah dikonfigurasi di Replit.

---

## 📁 Struktur Project

```
userbot/
├── main.py              # Entry point utama
├── config.py            # Konfigurasi dari Replit Secrets
├── loader.py            # Plugin loader otomatis
├── db.py                # Inisialisasi & helpers SQLite
├── requirements.txt
├── README.md
│
├── plugins/
│   ├── core/
│   │   ├── ping.py      # Command .ping
│   │   └── alive.py     # Command .alive
│   ├── permission/      # (tahap berikutnya)
│   ├── broadcast/       # (tahap berikutnya)
│   ├── voice/           # (tahap berikutnya)
│   ├── ai/              # (tahap berikutnya)
│   ├── fun/             # (tahap berikutnya)
│   └── utils/           # (tahap berikutnya)
│
├── utils/
│   ├── autodelete.py    # Sistem auto-delete pesan
│   ├── helper.py        # RAM, CPU, ping helpers
│   ├── logger.py        # Logging terpusat
│   └── uptime.py        # Tracker uptime bot
│
└── logs/                # File log otomatis dibuat di sini
```

---

## 🎯 Command Tahap 1

| Command  | Fungsi                              |
|----------|-------------------------------------|
| `.ping`  | Status bot, uptime, RAM, CPU, owner |
| `.alive` | Cek apakah bot sedang online        |

> Pesan command otomatis terhapus setelah 5 detik.

---

## ➕ Menambahkan Plugin Baru

1. Buat file `.py` di dalam folder `plugins/<kategori>/`
2. Daftarkan handler menggunakan decorator `@Client.on_message`
3. Jalankan ulang bot — plugin dimuat otomatis

Contoh minimal:

```python
from pyrogram import Client, filters

@Client.on_message(filters.command("hello", prefixes=".") & filters.me)
async def cmd_hello(client, message):
    await message.edit("👋 Hello World!")
```

---

## ⚙️ Konfigurasi

Semua konfigurasi ada di `config.py` dan dibaca dari Replit Secrets / environment variables:

| Variabel         | Default | Keterangan                          |
|------------------|---------|-------------------------------------|
| `API_ID`         | —       | Wajib                               |
| `API_HASH`       | —       | Wajib                               |
| `STRING_SESSION` | —       | Wajib                               |
| `AUTO_DELETE_CMD`| 5 detik | Jeda auto-delete pesan command      |

---

## 📝 Log

Log tersimpan di `userbot/logs/ibeks.log` (rotating, maks 5MB, 3 backup).

---

## 🛠 Stack

- **Python** 3.11
- **Pyrogram** 2.0.106
- **TgCrypto** 1.2.5
- **SQLite** (bawaan Python)
- **python-dotenv** 1.0.1
- **psutil** 5.9.8
