import sqlite3
from telethon import TelegramClient
from config import API_ID, API_HASH, DATABASE_CHANNELS

client = TelegramClient('session', API_ID, API_HASH)

conn = sqlite3.connect('database.db')
cur = conn.cursor()

cur.execute('''
CREATE TABLE IF NOT EXISTS media (
    message_id INTEGER,
    channel_id INTEGER,
    text TEXT,
    PRIMARY KEY(message_id, channel_id)
)
''')

async def build_index():
    await client.start()

    for channel in DATABASE_CHANNELS:
        async for msg in client.iter_messages(channel):
            if msg.media:
                text = ""

                if msg.message:
                    text += msg.message.lower()

                if msg.file and msg.file.name:
                    text += " " + msg.file.name.lower()

                cur.execute(
                    "INSERT OR REPLACE INTO media VALUES (?, ?, ?)",
                    (msg.id, channel, text)
                )

    conn.commit()
    print("Index completed")

with client:
    client.loop.run_until_complete(build_index())