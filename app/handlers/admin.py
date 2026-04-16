from __future__ import annotations

from pyrogram import filters
from pyrogram.types import Message

from app.bot import MovieBot
from app.keyboards.browser import admin_home_keyboard, admin_pick_title_keyboard
from app.utils.parser import parse_channel_message
from app.utils.text import build_admin_title_caption, normalize_title

TEMPLATE_TEXT = (
    "Use this caption template in your source channel:\n\n"
    "Type: movie\nTitle: Interstellar\nYear: 2014\nQuality: 1080p\nCodec: x264\nLanguage: English\nSize: 2.3GB\n\n"
    "For series:\n\nType: series\nTitle: The Last of Us\nYear: 2023\nSeason: 1\nEpisode: 1\nQuality: 1080p\nCodec: HEVC"
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
    try:
        if title.get("poster_url"):
            await bot.send_photo(bot.settings.series_info_channel_id, title["poster_url"], caption=caption)
        else:
            await bot.send_message(bot.settings.series_info_channel_id, caption)
    except Exception:
        return


@MovieBot.on_message(filters.command("admin") & filters.private)
async def admin_panel(bot: MovieBot, message: Message) -> None:
    if not _is_admin(bot, message):
        await message.reply_text("Admins only.")
        return
    bot.admin_states.pop(message.from_user.id, None)
    await message.reply_text("🛠 Admin panel\n\nMovie/Series manage කරන්න button එකක් ඔබන්න.", reply_markup=admin_home_keyboard(bot.settings))


@MovieBot.on_message(filters.command("template") & filters.private)
async def template_handler(bot: MovieBot, message: Message) -> None:
    if _is_admin(bot, message):
        await message.reply_text(TEMPLATE_TEXT)


@MovieBot.on_message(filters.command("syncseries") & filters.private)
async def sync_series_command(bot: MovieBot, message: Message) -> None:
    if not _is_admin(bot, message):
        await message.reply_text("Admins only.")
        return
    target = message.reply_to_message
    if not target:
        bot.admin_states[message.from_user.id] = {"mode": "await_series_forward"}
        await message.reply_text("Series post එක forward කරලා එවන්න.")
        return
    parsed = parse_channel_message(target)
    if not parsed:
        await message.reply_text("Reply කරලා තියෙන message එකේ video/document එකක් නැහැ.")
        return
    result = await bot.catalog_service.ingest_parsed_media(parsed, force_media_type="series")
    await _announce_series(bot, result["title"], parsed)
    await message.reply_text(f"✅ Series synced: {result['title']['title']}")


@MovieBot.on_message(filters.private & (filters.video | filters.document))
async def private_admin_media_router(bot: MovieBot, message: Message) -> None:
    if not _is_admin(bot, message):
        return
    state = bot.admin_states.get(message.from_user.id)
    if not state:
        return
    mode = state.get("mode")
    if mode not in {"await_series_forward", "await_movie_forward", "await_replace_media"}:
        return
    parsed = parse_channel_message(message)
    if not parsed:
        await message.reply_text("මෙම file parse කරන්න බැරි වුණා.")
        return
    if mode == "await_replace_media":
        await bot.db_service.update_media_file_fields(state["media_file_id"], {
            "source_chat_id": parsed.source_chat_id,
            "source_message_id": parsed.source_message_id,
            "telegram_file_id": parsed.file_id,
            "file_unique_id": parsed.file_unique_id,
            "file_name": parsed.file_name,
            "caption": parsed.caption,
            "media_kind": parsed.media_kind,
            "size_label": parsed.size_label,
        })
        bot.admin_states.pop(message.from_user.id, None)
        await message.reply_text("✅ Media file replaced.")
        return
    forced_type = "series" if mode == "await_series_forward" else "movie"
    result = await bot.catalog_service.ingest_parsed_media(parsed, force_media_type=forced_type)
    if forced_type == "series":
        await _announce_series(bot, result["title"], parsed)
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
        items = await bot.db_service.search_titles(text, media_type=state.get("media_type"), limit=12)
        if not items:
            await message.reply_text("Result හම්බුනේ නැහැ.")
            return
        await message.reply_text("Edit කරන්න title එකක් තෝරන්න.", reply_markup=admin_pick_title_keyboard(bot.settings, items))
        return
    if mode == "await_move_file_title":
        items = await bot.db_service.search_titles(text, limit=5)
        if not items:
            await message.reply_text("Target title not found.")
            return
        await bot.db_service.reassign_media_file(state["media_file_id"], str(items[0]["_id"]))
        bot.admin_states.pop(message.from_user.id, None)
        await message.reply_text(f"✅ File moved to: {items[0].get('title')}")
        return
    if mode == "await_edit_title_name":
        title = await bot.db_service.get_title(state["title_id"])
        if not title:
            await message.reply_text("Title not found.")
            bot.admin_states.pop(message.from_user.id, None)
            return
        aliases = list({*(title.get("aliases") or []), normalize_title(title.get("title", "")), normalize_title(text)})
        await bot.db_service.update_title_fields(state["title_id"], {"title": text, "normalized_title": normalize_title(text), "aliases": aliases})
        bot.admin_states.pop(message.from_user.id, None)
        await message.reply_text(f"✅ Title name updated to: {text}")
        return
    if mode == "await_edit_title_poster":
        title = await bot.db_service.get_title(state["title_id"])
        if not title:
            await message.reply_text("Title not found.")
            bot.admin_states.pop(message.from_user.id, None)
            return
        if text.lower() == "remove":
            updates = {"poster_url": None, "poster_source": None}
        elif text.lower() == "auto":
            metadata = await bot.metadata_service.search(title.get("title", ""), title.get("media_type", "movie"), title.get("year"))
            updates = {"poster_url": metadata.get("poster_url") if metadata else None, "poster_source": metadata.get("poster_source") if metadata else None}
        else:
            updates = {"poster_url": text, "poster_source": "manual"}
        await bot.db_service.update_title_fields(state["title_id"], updates)
        bot.admin_states.pop(message.from_user.id, None)
        await message.reply_text("✅ Poster updated.")
        return
    if mode == "await_edit_file_quality":
        await bot.db_service.update_media_file_fields(state["media_file_id"], {"quality": text})
        bot.admin_states.pop(message.from_user.id, None)
        await message.reply_text(f"✅ Quality updated to: {text}")
        return
    if mode == "await_edit_file_codec":
        await bot.db_service.update_media_file_fields(state["media_file_id"], {"codec": text})
        bot.admin_states.pop(message.from_user.id, None)
        await message.reply_text(f"✅ Codec updated to: {text}")
        return
