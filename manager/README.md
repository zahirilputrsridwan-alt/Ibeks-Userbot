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
database Manager Bot.

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

## Engine Userbot

Setelah login berhasil, Manager Bot menyiapkan proses IBEKS USERBOT milik
pengguna secara otomatis. Setiap pengguna memiliki proses, direktori runtime,
database, log, dan backup plugin yang terisolasi.

Kontrol tersedia dari menu `👤 Akun Saya`:

- `▶ Start Userbot`
- `⏹ Stop Userbot`
- `🔄 Restart Userbot`
- `📊 Status Userbot`

Status lifecycle disimpan di SQLite. `STRING_SESSION` dikirim ke proses child
melalui environment internal dan tidak pernah dicetak ke command line, pesan,
atau log Manager Bot.

## Terminal Userbot

Pesan privat yang diawali prefix aktif diteruskan ke Userbot akun tersebut.
Prefix dibaca langsung dari database runtime Userbot, sehingga perubahan lewat
`.setprefix` langsung berlaku di Manager Bot. Manager Bot tidak mempunyai daftar
command manual; plugin Userbot yang terpasang menjadi sumber kebenaran.

Saat Userbot dijalankan oleh Manager, Userbot membuka kanal privat internal ke
Manager terlebih dahulu. Ini diperlukan agar Telegram mengizinkan Bot Manager
mengirim pesan ke akun Userbot; pesan handshake tersebut tidak diteruskan ke
pengguna.

Semua output pesan Userbot disalin kembali, termasuk teks, foto, video,
animation, sticker, voice, audio, dan document. Command yang tidak tersedia
menghasilkan error dari Userbot, sedangkan Userbot yang berhenti menampilkan
instruksi untuk menyalakannya.

## Membership

Login Telegram pertama yang berhasil memberikan Membership selama 30 hari.
Tanggal berakhir disimpan dalam UTC pada SQLite dan status `Active` atau
`Expired` dihitung saat data dibaca. Command Terminal tidak diteruskan jika
Membership sudah berakhir. Fungsi `extend_membership()` tersedia untuk plugin
Admin.

## Admin Panel

Owner Manager Bot adalah Telegram ID `8823165964`. Hanya Owner yang dapat
melihat dan membuka tombol `🛠 Admin Panel`. Panel menyediakan:

- Daftar dan detail user
- Statistik total, aktif, expired, online, dan offline
- Perpanjangan Membership `+7`, `+30`, `+90`, dan `+365` hari
- Suspend, aktifkan, serta hapus user dengan konfirmasi
- Broadcast pesan atau media ke seluruh user terdaftar

Semua operasi Admin dan percobaan akses non-Owner dicatat pada tabel audit
SQLite `admin_logs`. Penghapusan user juga membersihkan runtime Userbot
terisolasinya.
