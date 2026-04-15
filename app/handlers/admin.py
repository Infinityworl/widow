from __future__ import annotations

from pyrogram import filters
from pyrogram.types import Message

from app.bot import MovieBot
from app.keyboards.browser import admin_home_keyboard, admin_pick_title_keyboard
from app.utils.parser import parse_channel_message
from app.utils.text import build_admin_title_caption, normalize_title


TEMPLATE_TEXT = (
    "Use this caption template in your source channel:\n\n"
    "Type: movie\n"
    "Title: Interstellar\n"
    "Year: 2014\n"
    "Quality: 1080p\n"
    "Codec: x264\n"
    "Language: English\n"
    "Size: 2.3GB\n\n"
    "For series:\n\n"
    "Type: series\n"
    "Title: The Last of Us\n"
    "Year: 2023\n"
    "Season: 1\n"
    "Episode: 1\n"
    "Quality: 1080p\n"
    "Codec: HEVC"
)



def _is_admin(bot: MovieBot, message: Message) -> bool:
    return bool(message.from_user and (not bot.settings.admins or message.from_user.id in bot.settings.admins))


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
    if title.get("poster_url"):
        await bot.send_photo(bot.settings.series_info_channel_id, title["poster_url"], caption=caption)
    else:
        await bot.send_message(bot.settings.series_info_channel_id, caption)


async def _show_title_admin_card(bot: MovieBot, message: Message, title: dict) -> None:
    from app.keyboards.browser import admin_title_keyboard

    caption = build_admin_title_caption(title)
    keyboard = admin_title_keyboard(str(title["_id"]), title.get("media_type", "movie"))
    if title.get("poster_url"):
        await message.reply_photo(title["poster_url"], caption=caption, reply_markup=keyboard)
    else:
        await message.reply_text(caption, reply_markup=keyboard)


@MovieBot.on_message(filters.command("admin") & filters.private)
async def admin_panel(bot: MovieBot, message: Message) -> None:
    if not _is_admin(bot, message):
        await message.reply_text("Admins only.")
        return
    bot.admin_states.pop(message.from_user.id, None)
    await message.reply_text(
        "🛠 Admin panel\n\nMovie/Series manage කරන්න button එකක් ඔබන්න.",
        reply_markup=admin_home_keyboard(),
    )


@MovieBot.on_message(filters.command("template") & filters.private)
async def template_handler(bot: MovieBot, message: Message) -> None:
    if not _is_admin(bot, message):
        await message.reply_text("Admins only.")
        return
    await message.reply_text(TEMPLATE_TEXT)


@MovieBot.on_message(filters.command("syncseries") & filters.private)
async def sync_series_command(bot: MovieBot, message: Message) -> None:
    if not _is_admin(bot, message):
        await message.reply_text("Admins only.")
        return

    target = message.reply_to_message
    if not target:
        bot.admin_states[message.from_user.id] = {"mode": "await_series_forward"}
        await message.reply_text("Series post එක forward කරලා එවන්න. එතකොට bot එක MongoDB එකට save කරනවා.")
        return

    parsed = parse_channel_message(target)
    if not parsed:
        await message.reply_text("Reply කරලා තියෙන message එකේ video/document එකක් නැහැ.")
        return

    result = await bot.catalog_service.ingest_parsed_media(parsed, force_media_type="series")
    await _announce_series(bot, result['title'], parsed)
    await message.reply_text(f"✅ Series synced: {result['title']['title']}")


@MovieBot.on_message(filters.private & (filters.video | filters.document))
async def private_admin_media_router(bot: MovieBot, message: Message) -> None:
    if not _is_admin(bot, message):
        return

    state = bot.admin_states.get(message.from_user.id)
    if not state or state.get("mode") not in {"await_series_forward", "await_movie_forward"}:
        return

    forced_type = "series" if state["mode"] == "await_series_forward" else "movie"
    parsed = parse_channel_message(message)
    if not parsed:
        await message.reply_text("මෙම file parse කරන්න බැරි වුණා.")
        return

    result = await bot.catalog_service.ingest_parsed_media(parsed, force_media_type=forced_type)
    if forced_type == 'series':
        await _announce_series(bot, result['title'], parsed)
    bot.admin_states.pop(message.from_user.id, None)
    await message.reply_text(f"✅ Synced to MongoDB: {result['title']['title']} ({forced_type})")


@MovieBot.on_message(filters.private & filters.text & ~filters.command(["admin", "template", "syncseries", "start", "help"]))
async def admin_text_router(bot: MovieBot, message: Message) -> None:
    if not _is_admin(bot, message):
        return

    state = bot.admin_states.get(message.from_user.id)
    if not state:
        return

    mode = state.get("mode")
    text = (message.text or "").strip()
    if not text:
        return

    if mode == "await_find_title":
        media_type = state.get("media_type")
        items = await bot.db_service.search_titles(text, media_type=media_type, limit=8)
        if not items:
            await message.reply_text("Result හම්බුනේ නැහැ. වෙන title එකක් දාලා බලන්න.")
            return
        await message.reply_text("Edit කරන්න title එකක් තෝරන්න.", reply_markup=admin_pick_title_keyboard(items))
        return

    if mode == "await_edit_title_name":
        title_id = state["title_id"]
        title = await bot.db_service.get_title(title_id)
        if not title:
            await message.reply_text("Title not found.")
            bot.admin_states.pop(message.from_user.id, None)
            return
        aliases = list({*(title.get("aliases") or []), title.get("title"), text})
        await bot.db_service.update_title_fields(
            title_id,
            {"title": text, "normalized_title": normalize_title(text), "aliases": aliases},
        )
        bot.admin_states.pop(message.from_user.id, None)
        await message.reply_text(f"✅ Title name updated to: {text}")
        return

    if mode == "await_edit_title_poster":
        title_id = state["title_id"]
        title = await bot.db_service.get_title(title_id)
        if not title:
            await message.reply_text("Title not found.")
            bot.admin_states.pop(message.from_user.id, None)
            return
        if text.lower() == "remove":
            updates = {"poster_url": None, "poster_source": None}
        elif text.lower() == "auto":
            metadata = await bot.metadata_service.search(title.get("title", ""), title.get("media_type", "movie"), title.get("year"))
            updates = {
                "poster_url": metadata.get("poster_url") if metadata else title.get("poster_url"),
                "poster_source": metadata.get("poster_source") if metadata else title.get("poster_source"),
            }
        else:
            updates = {"poster_url": text, "poster_source": "manual"}
        await bot.db_service.update_title_fields(title_id, updates)
        bot.admin_states.pop(message.from_user.id, None)
        await message.reply_text("✅ Poster updated.")
        return

    if mode == "await_edit_file_quality":
        media_file_id = state["media_file_id"]
        await bot.db_service.update_media_file_fields(media_file_id, {"quality": text})
        bot.admin_states.pop(message.from_user.id, None)
        await message.reply_text(f"✅ Quality updated to: {text}")
        return

    if mode == "await_edit_file_codec":
        media_file_id = state["media_file_id"]
        await bot.db_service.update_media_file_fields(media_file_id, {"codec": text})
        bot.admin_states.pop(message.from_user.id, None)
        await message.reply_text(f"✅ Codec updated to: {text}")
        return
