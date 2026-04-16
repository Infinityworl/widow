from __future__ import annotations

from typing import Optional

from pyrogram import filters
from pyrogram.types import Message

from app.bot import MovieBot
from app.keyboards.browser import category_keyboard, search_results_keyboard
from app.utils.text import build_search_hub_caption



def _partition_items(items: list[dict]) -> tuple[list[dict], list[dict]]:
    movies = [item for item in items if item.get("media_type") != "series"]
    series = [item for item in items if item.get("media_type") == "series"]
    return movies, series


async def _send_preview_card(bot: MovieBot, message: Message, query: str, items: list[dict], active_type: str) -> None:
    movies, series = _partition_items(items)
    active_items = movies if active_type == "movie" else series
    if not active_items:
        active_items = movies or series
        active_type = "movie" if movies else "series"
    if not active_items:
        await message.reply_text("Database එකේ matching result එකක් නැහැ.")
        return

    caption = build_search_hub_caption(
        bot.settings,
        query,
        movie_count=len(movies),
        series_count=len(series),
        active_type=active_type,
    )
    keyboard = category_keyboard(bot.settings, movie_count=len(movies), series_count=len(series))

    poster_url = bot.settings.search_hub_photo_url or bot.settings.browser_placeholder_photo_url or active_items[0].get("poster_url")
    if poster_url:
        sent = await message.reply_photo(poster_url, caption=caption, reply_markup=keyboard)
    else:
        sent = await message.reply_text(caption, reply_markup=keyboard)

    bot.search_sessions[(sent.chat.id, sent.id)] = {
        "query": query,
        "owner_id": message.from_user.id if message.from_user else None,
        "owner_name": message.from_user.first_name if message.from_user else None,
        "movies": [str(item["_id"]) for item in movies[:10]],
        "series": [str(item["_id"]) for item in series[:10]],
    }


async def _run_search(bot: MovieBot, message: Message, query: str, media_type: Optional[str]) -> None:
    query = query.strip()
    if not query or len(query) < 2:
        return

    items = await bot.db_service.search_titles(
        query=query,
        media_type=media_type,
        limit=max(bot.settings.max_search_results, 10),
    )
    if not items:
        await message.reply_text("Database එකේ matching result එකක් නැහැ.")
        return

    active_type = media_type or ("movie" if any(item.get("media_type") != "series" for item in items) else "series")
    await _send_preview_card(bot, message, query, items, active_type)


@MovieBot.on_message(filters.text & filters.group & ~filters.command(["start", "help"]))
async def auto_search_groups(bot: MovieBot, message: Message) -> None:
    if bot.settings.user_group_ids and message.chat.id not in bot.settings.user_group_ids:
        return

    query = (message.text or "").strip()
    if not query:
        return

    lowered = query.lower()
    media_type: Optional[str] = None
    if lowered.startswith("movie ") or lowered.startswith("film "):
        media_type = "movie"
        query = query.split(maxsplit=1)[1] if len(query.split()) > 1 else query
    elif lowered.startswith("series ") or lowered.startswith("tv ") or lowered.startswith("show "):
        media_type = "series"
        query = query.split(maxsplit=1)[1] if len(query.split()) > 1 else query

    await _run_search(bot, message, query, media_type)

```
