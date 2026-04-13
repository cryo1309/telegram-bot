import sqlite3
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telethon import TelegramClient, events

from config import BOT_TOKEN, API_ID, API_HASH, MAIN_CHANNEL_ID, DATABASE_CHANNELS

# Telethon client
telethon_client = TelegramClient('session', API_ID, API_HASH)

# Database
conn = sqlite3.connect('database.db', check_same_thread=False)
cur = conn.cursor()

# Create table
cur.execute('''
CREATE TABLE IF NOT EXISTS media (
    message_id INTEGER,
    channel_id INTEGER,
    text TEXT,
    PRIMARY KEY(message_id, channel_id)
)
''')
conn.commit()

# 🔍 SEARCH COMMAND
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /search keyword")
        return

    keyword = " ".join(context.args).lower()

    print("SEARCHING FOR:", keyword)

    cur.execute(
        "SELECT message_id, channel_id FROM media WHERE text LIKE ? LIMIT 10",
        (f"%{keyword}%",)
    )

    results = cur.fetchall()

    print("RESULTS FOUND:", results)

    if not results:
        await update.message.reply_text("No results found")
        return

    await update.message.reply_text(f"Found {len(results)} results")

    for message_id, channel_id in results:
        try:
            print("FORWARDING:", message_id, "FROM", channel_id)

            msg = await telethon_client.get_messages(channel_id, ids=message_id)

            if msg and msg.media:
                await telethon_client.send_file(
                    MAIN_CHANNEL_ID,
                    msg.media,
                    caption=msg.text or ""
                )
                await asyncio.sleep(1)

        except Exception as e:
            print("ERROR SENDING:", e)


# 🔁 AUTO INDEX (every 5 min)
async def auto_index():
    while True:
        print("🔄 Running auto index...")

        for channel in DATABASE_CHANNELS:
            print("📡 READING CHANNEL:", channel)

            try:
                async for msg in telethon_client.iter_messages(channel, limit=50):
                    if msg.media:
                        text = ""

                        if msg.message:
                            text += msg.message.lower()

                        if msg.file and msg.file.name:
                            text += " " + msg.file.name.lower()

                        print("📥 FOUND MEDIA:", msg.id, "TEXT:", text)

                        cur.execute(
                            "INSERT OR REPLACE INTO media VALUES (?, ?, ?)",
                            (msg.id, channel, text)
                        )

            except Exception as e:
                print("❌ ERROR READING CHANNEL:", channel, e)

        conn.commit()
        print("✅ Index updated!")

        await asyncio.sleep(300)


# ⚡ REAL-TIME INDEX
@telethon_client.on(events.NewMessage(chats=DATABASE_CHANNELS))
async def handler(event):
    msg = event.message

    if msg.media:
        text = ""

        if msg.message:
            text += msg.message.lower()

        if msg.file and msg.file.name:
            text += " " + msg.file.name.lower()

        print("⚡ NEW MEDIA DETECTED:", msg.id, "IN", event.chat_id)

        cur.execute(
            "INSERT OR REPLACE INTO media VALUES (?, ?, ?)",
            (msg.id, event.chat_id, text)
        )

        conn.commit()
        print("✅ Indexed instantly!")


# 🚀 MAIN
def main():
    telethon_client.start()

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("search", search))

    print("🤖 Bot running...")

    loop = asyncio.get_event_loop()
    loop.create_task(auto_index())

    app.run_polling()


# ▶️ RUN
if __name__ == "__main__":
    main()
