import os
import aiosqlite
import asyncio
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# API Credentials resmi lu
API_ID = 39798969
API_HASH = "0bcd8c96000fc0a162769af31511613e"

# Bot Token Telegram lu dari @BotFather
BOT_TOKEN = "8253863285:AAFbu3HzSFFTuLKv-xrmsA7vWwsKqQ_ZBjY"

DB_NAME = 'anon_bot.db'
MAX_LENGTH = 300
BAD_WORDS = [
    'anjing', 'anj', 'anjg', 'babi', 'kontol', 'kntl', 'memek', 'mmk', 
    'goblok', 'goblq', 'tolol', 'bangsat', 'bgst', 'pantek', 'asu', 'bajingan'
]

def check_toxic(text: str) -> bool:
    text_lower = text.lower()
    for word in BAD_WORDS:
        if word in text_lower:
            return True
    return False

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                user_id INTEGER PRIMARY KEY,
                target_id INTEGER,
                send_type TEXT DEFAULT 'text'
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS inbox (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER,
                sender_text TEXT,
                msg_type TEXT DEFAULT 'text',
                created_at TEXT
            )
        ''')
        await db.commit()

# Inisialisasi Bot Client menggunakan kredensial asli
app = Client(
    "anon_standalone_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

@app.on_message(filters.command("start"))
async def start_handler(client: Client, message: Message):
    user = message.from_user
    args = message.command
    me = await client.get_me()
    bot_username = me.username

    if len(args) > 1:
        try:
            target_id = int(args[1])
            if target_id == user.id:
                await message.reply_text("❌ Waduh, ngapain ngirim pesan rahasia ke diri sendiri, bro? Kurang kerjaan amat wkwk 😂")
                return

            async with aiosqlite.connect(DB_NAME) as db:
                await db.execute('INSERT OR REPLACE INTO sessions (user_id, target_id, send_type) VALUES (?, ?, ?)', (user.id, target_id, 'text'))
                await db.commit()

            # Tampilan tombol ala NGL / AnoMessBot sesuai request lu
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✉️ Kirim pesan anonim", callback_data=f"send_type_text_{target_id}")],
                [InlineKeyboardButton("🎁 Kirim hadiah anonim", callback_data=f"send_type_gift_{target_id}")]
            ])

            await message.reply_text(
                "Kirimkan saya pesan anonim atau hadiah:",
                reply_markup=keyboard
            )
            return
        except ValueError:
            pass

    my_link = f"https://t.me/{bot_username}?start={user.id}"
    text = (
        f"Wih, halo bro! Selamat datang di bot anonim lu 🤫🔥\n\n"
        f"🔗 Tautan Pribadi-mu:\n{my_link}\n\n"
        f"💡 Tambahkan tautan ini ke bio akunmu dan tunggu pesan anonim masuk! 💌✨"
    )

    await message.reply_text(text)

@app.on_callback_query(filters.regex("^send_type_"))
async def callback_handler(client: Client, callback_query: CallbackQuery):
    data = callback_query.data
    user = callback_query.from_user
    parts = data.split("_")
    stype = parts[2]
    target_id = int(parts[3])

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('INSERT OR REPLACE INTO sessions (user_id, target_id, send_type) VALUES (?, ?, ?)', (user.id, target_id, stype))
        await db.commit()

    label = "pesan anonim" if stype == "text" else "hadiah anonim"
    await callback_query.message.reply_text(
        f"🤫 Mode Kirim {label} aktif!\n\n"
        f"Coba ketik unek-unek lu yang paling jujur di bawah ini, identitas lu aman 100%! 👇✨"
    )
    await callback_query.answer()

@app.on_message(filters.private & ~filters.command(["start", "inbox"]))
async def handle_anonymous_message(client: Client, message: Message):
    user = message.from_user

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT target_id, send_type FROM sessions WHERE user_id = ?', (user.id,)) as cursor:
            row = await cursor.fetchone()

    if not row:
        await message.reply_text("⚠️ Ketik /start atau gunakan tautan pengirim yang valid terlebih dahulu ya, bre!")
        return

    target_id, send_type = row

    if not message.text:
        await message.reply_text("⚠️ Kirim pesan teks biasa dulu ya bro!")
        return
    if len(message.text) > MAX_LENGTH:
        await message.reply_text(f"⚠️ Kepanjangan bro! Maksimal {MAX_LENGTH} karakter.")
        return
    if check_toxic(message.text):
        await message.reply_text("🚫 Eits, kedeteksi ada kata toxic/kotor. Ganti bahasa yang adem ya 🛑✨")
        return

    content_text = message.text
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('INSERT INTO inbox (owner_id, sender_text, msg_type, created_at) VALUES (?, ?, ?, ?)', (target_id, content_text, send_type, now))
        await db.commit()

    await message.reply_text("✅ Mantap! Kiriman rahasia lu berhasil meluncur secara misterius tanpa ketahuan 🥷✨")

    try:
        await client.send_message(
            chat_id=target_id,
            text=f"📬 Ada kiriman anonim baru masuk!\n\nKetik /inbox untuk membaca pesannya."
        )
    except Exception:
        pass

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('DELETE FROM sessions WHERE user_id = ?', (user.id,))
        await db.commit()

@app.on_message(filters.command("inbox"))
async def inbox_handler(client: Client, message: Message):
    user = message.from_user
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT id, sender_text, created_at FROM inbox WHERE owner_id = ?', (user.id,)) as cursor:
            messages = await cursor.fetchall()

    if not messages:
        await message.reply_text("🌱 Inbox lu masih kosong, bre...")
        return

    await message.reply_text(f"📬 Nih, ada {len(messages)} pesan rahasia masuk:")
    for msg_id, text, created_at in messages:
        await message.reply_text(f"📥 Inbox\n🕒 {created_at}\n\n{text}")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_db())
    print("Bot Anonim Standalone Berhasil Dijalankan!")
    app.run()
