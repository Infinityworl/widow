from __future__ import annotations

from pyrogram import filters
from pyrogram.types import Message

from app.bot import MovieBot


START_TEXT = (
    "👋 Welcome!\n\n"
    "👥 Users: allowed Telegram group එකේ movie හරි TV series හරි නම type කරන්න.\n"
    "🎛 Group result card එකේ Movies / TV Series buttons දෙකෙන් category තෝරන්න.\n"
    "📩 Download කරන file bot inbox එකට යවයි, ඒකෙන්ම save කරගන්න.\n"
    "🛠 Admins: private chat එකේ /admin දාලා manage කරන්න.\n\n"
    "Examples in group:\n"
    "• Interstellar\n"
    "• movie Avatar\n"
    "• series The Last of Us\n"
)


@MovieBot.on_message(filters.command(["start", "help"]))
async def start_handler(_: MovieBot, message: Message) -> None:
    await message.reply_text(START_TEXT)
