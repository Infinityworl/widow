from __future__ import annotations

from pyrogram import filters
from pyrogram.errors import RPCError
from pyrogram.types import Message

from app.bot import MovieBot
from app.utils.parser import parse_channel_message


async def _safe_send_text(bot: MovieBot, chat_id: int | None, text: str) -> None:
    if not chat_id:
        return
    try:
        await bot.send_message(chat_id, text)
    except (RPCError, ValueError):
        return


async def _announce_series(bot: MovieBot, title: dict, parsed) -> None:
    if not bot.settings.series_info_channel_id or title.get("media_type") != "series":
        return
    caption = (
        f"📺 <b>{title.get('title', 'Unknown Title')}</b>\n"
        f"🗓 {title.get('year', '-')}\n"
        f"🧩 Season: {parsed.season or '-'} • Episode: {parsed.episode or '-'}\n"
        f"📦 Quality: {parsed.quality}\n"
        f"⚙️ Codec: {parsed.codec}"
    )
    try:
        if title.get("poster_url"):
            await bot.send_photo(bot.settings.series_info_channel_id, title["poster_url"], caption=caption)
        else:
            await bot.send_message(bot.settings.series_info_channel_id, caption)
    except (RPCError, ValueError):
        return



@MovieBot.on_message((filters.channel) & (filters.video | filters.document))
async def ingest_channel_post(bot: MovieBot, message: Message) -> None:
    parsed = parse_channel_message(message)
    if not parsed or not parsed.title or parsed.title == "Unknown Title":
        if bot.settings.log_chat_id:
            await _safe_send_text(bot, bot.settings.log_chat_id, f"⚠️ Skipped channel post {message.chat.id}/{message.id} because title could not be parsed.")
        return

    force_media_type = None
    movie_channels = set(bot.settings.movie_source_channels)
    series_channels = set(bot.settings.series_source_channels)
    fallback_channels = set(bot.settings.source_channels)

    if movie_channels or series_channels:
        if message.chat.id in movie_channels:
            force_media_type = "movie"
        elif message.chat.id in series_channels:
            force_media_type = "series"
        else:
            return
    elif fallback_channels and message.chat.id not in fallback_channels:
        return

    result = await bot.catalog_service.ingest_parsed_media(parsed, force_media_type=force_media_type)
    title = result["title"]
    await _announce_series(bot, title, parsed)
    if bot.settings.log_chat_id:
        season_text = f" S{parsed.season}" if parsed.season is not None else ""
        episode_text = f"E{parsed.episode}" if parsed.episode is not None else ""
        await _safe_send_text(bot, bot.settings.log_chat_id, (f"✅ Saved {title['media_type']}\n" f"Title: {title['title']}\n" f"Year: {title.get('year', '-')}\n" f"Quality: {parsed.quality}\n" f"Codec: {parsed.codec}\n" f"Part: {(season_text + episode_text).strip() or '-'}"))
