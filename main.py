from __future__ import annotations

import asyncio
import logging

from pyrogram import idle

from app.bot import MovieBot
from app.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


async def main() -> None:
    settings = get_settings()
    bot = MovieBot(settings)
    await bot.start()
    await bot.db_service.ensure_indexes()

    me = await bot.get_me()
    logging.info("Bot started as @%s", me.username)

    if not bot.settings.bot_username and me.username:
        bot.settings.bot_username = me.username

    await idle()
    await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
