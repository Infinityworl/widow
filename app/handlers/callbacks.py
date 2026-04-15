from __future__ import annotations

from pyrogram import filters
from pyrogram.errors import RPCError
from pyrogram.types import CallbackQuery, InputMediaPhoto

from app.bot import MovieBot
from app.keyboards.browser import (
    admin_confirm_delete_title_keyboard,
    admin_home_keyboard,
    admin_poster_keyboard,
    admin_title_keyboard,
    admin_variant_edit_keyboard,
    admin_variant_picker,
    bot_inbox_keyboard,
    category_keyboard,
    download_keyboard,
    episodes_keyboard,
    movie_variants_keyboard,
    qualities_keyboard,
    search_results_keyboard,
    seasons_keyboard,
)
from app.utils.callbacks import decode
from app.utils.text import (
    build_admin_title_caption,
    build_inbox_intro_caption,
    build_inbox_reply_text,
    build_search_hub_caption,
    build_stage_caption,
    sort_qualities,
)


async def _render_card(query: CallbackQuery, *, poster_url: str | None, caption: str, reply_markup) -> None:
    try:
        if poster_url:
            await query.message.edit_media(
                InputMediaPhoto(media=poster_url, caption=caption),
                reply_markup=reply_markup,
            )
        elif query.message.photo:
            await query.message.edit_caption(caption=caption, reply_markup=reply_markup)
        else:
            await query.message.edit_text(caption, reply_markup=reply_markup)
    except RPCError:
        if poster_url:
            await query.message.reply_photo(poster_url, caption=caption, reply_markup=reply_markup)
        else:
            await query.message.reply_text(caption, reply_markup=reply_markup)


def _get_search_session(bot: MovieBot, query: CallbackQuery) -> dict | None:
    if not query.message:
        return None
    return bot.search_sessions.get((query.message.chat.id, query.message.id))


async def _ensure_owner(bot: MovieBot, query: CallbackQuery) -> bool:
    session = _get_search_session(bot, query)
    if not session:
        await query.answer("Search session expired", show_alert=True)
        return False
    owner_id = session.get("owner_id")
    if owner_id and query.from_user and query.from_user.id != owner_id:
        await query.answer("Not working for you", show_alert=True)
        return False
    return True


def _stage_photo(bot: MovieBot, title: dict | None = None, *, stage: str = "search", final: bool = False) -> str | None:
    if final and title:
        return title.get("poster_url")
    stage_map = {
        "search": bot.settings.search_hub_photo_url,
        "title": bot.settings.title_pick_photo_url,
        "season": bot.settings.season_pick_photo_url,
        "quality": bot.settings.quality_pick_photo_url,
        "codec": bot.settings.codec_pick_photo_url,
        "episode": bot.settings.episode_pick_photo_url,
    }
    if stage_map.get(stage):
        return stage_map[stage]
    if bot.settings.browser_placeholder_photo_url:
        return bot.settings.browser_placeholder_photo_url
    if title:
        return title.get("poster_url")
    return None


async def _show_search_category(bot: MovieBot, query: CallbackQuery, media_type: str) -> None:
    session = _get_search_session(bot, query)
    if not session:
        await query.answer("Search session expired", show_alert=True)
        return

    title_ids = session.get("movies", []) if media_type == "movie" else session.get("series", [])
    if not title_ids:
        await query.answer(f"No {media_type} results", show_alert=True)
        return

    items: list[dict] = []
    for title_id in title_ids:
        title = await bot.db_service.get_title(title_id)
        if title:
            items.append(title)

    if not items:
        await query.answer("Results not found", show_alert=True)
        return

    movie_count = len(session.get("movies", []))
    series_count = len(session.get("series", []))
    await query.answer()
    await _render_card(
        query,
        poster_url=_stage_photo(bot, items[0], stage="title"),
        caption=build_search_hub_caption(session.get("query", "Search"), movie_count=movie_count, series_count=series_count, active_type=media_type),
        reply_markup=search_results_keyboard(items, movie_count=movie_count, series_count=series_count, active_type=media_type),
    )


async def _show_title_selector(bot: MovieBot, query: CallbackQuery, title: dict, *, season: int | None = None, quality: str | None = None, codec: str | None = None) -> None:
    title_id = str(title["_id"])

    if title.get("media_type") == "series":
        if season is None:
            seasons = await bot.db_service.get_available_seasons(title_id)
            if not seasons:
                await query.answer("මේ series එකට season data නැහැ.", show_alert=True)
                return
            markup = seasons_keyboard(title_id, seasons)
            caption = build_stage_caption(bot.settings, title, stage="season")
        elif quality is None:
            qualities = await bot.db_service.get_available_qualities(title_id, season=season)
            markup = qualities_keyboard(title_id, sort_qualities(qualities), back_to_series=season)
            caption = build_stage_caption(bot.settings, title, stage="quality", season=season)
        elif codec is None:
            from app.keyboards.browser import codecs_keyboard
            codecs = await bot.db_service.get_available_codecs(title_id, quality, season=season)
            markup = codecs_keyboard(title_id, quality, codecs, season=season)
            caption = build_stage_caption(bot.settings, title, stage="codec", season=season, quality=quality)
        else:
            page_size = bot.settings.result_page_size
            episodes = await bot.db_service.get_series_episodes(title_id=title_id, season=season, quality=quality, codec=codec, skip=0, limit=page_size)
            total_count = await bot.db_service.count_series_episodes(title_id=title_id, season=season, quality=quality, codec=codec)
            if not episodes:
                await query.answer("Episodes not found", show_alert=True)
                return
            markup = episodes_keyboard(title_id=title_id, season=season, quality=quality, codec=codec, episodes=episodes, page=0, page_size=page_size, total_count=total_count)
            caption = build_stage_caption(bot.settings, title, stage="episode", season=season, quality=quality, codec=codec)
    else:
        if quality is None:
            qualities = await bot.db_service.get_available_qualities(title_id)
            markup = qualities_keyboard(title_id, qualities)
            caption = build_stage_caption(bot.settings, title, stage="quality")
        else:
            variants = await bot.db_service.list_movie_variants(title_id, quality)
            if not variants:
                await query.answer("Movie variants not found", show_alert=True)
                return
            markup = movie_variants_keyboard(title_id, variants)
            caption = build_stage_caption(bot.settings, title, stage="codec", quality=quality)

    stage_name = "title"
    if title.get("media_type") == "series" and season is None:
        stage_name = "season"
    elif quality is None:
        stage_name = "quality"
    elif codec is None:
        stage_name = "codec"
    else:
        stage_name = "episode" if title.get("media_type") == "series" else "codec"
    await _render_card(query, poster_url=_stage_photo(bot, title, stage=stage_name), caption=caption, reply_markup=markup)


async def _show_download_ready(bot: MovieBot, query: CallbackQuery, title: dict, item: dict) -> None:
    caption = build_stage_caption(bot.settings, title, stage="download", season=item.get("season"), episode=item.get("episode"), quality=item.get("quality"), codec=item.get("codec"), size_label=item.get("size_label"))
    await _render_card(query, poster_url=_stage_photo(bot, title, final=True), caption=caption, reply_markup=download_keyboard(str(title["_id"]), str(item["_id"])))


async def _send_private_copy(bot: MovieBot, query: CallbackQuery, item: dict, title: dict) -> None:
    try:
        poster_url = title.get("poster_url")
        intro_caption = build_inbox_intro_caption(title, season=item.get("season"), episode=item.get("episode"), quality=item.get("quality"), codec=item.get("codec"), size_label=item.get("size_label"))
        if poster_url:
            await bot.send_photo(query.from_user.id, poster_url, caption=intro_caption)
        else:
            await bot.send_message(query.from_user.id, intro_caption)

        copied = await bot.copy_message(chat_id=query.from_user.id, from_chat_id=item["source_chat_id"], message_id=item["source_message_id"])
        await bot.send_message(query.from_user.id, build_inbox_reply_text(title), reply_to_message_id=copied.id)
        await query.answer()
    except RPCError:
        await query.answer("Open the bot in private chat first", show_alert=True)


def _is_admin(bot: MovieBot, query: CallbackQuery) -> bool:
    return bool(query.from_user and (not bot.settings.admins or query.from_user.id in bot.settings.admins))


async def _admin_show_title(bot: MovieBot, query: CallbackQuery, title_id: str) -> None:
    title = await bot.db_service.get_title(title_id)
    if not title:
        await query.answer("Title not found", show_alert=True)
        return
    file_count = await bot.db_service.count_title_files(title_id)
    caption = build_admin_title_caption(title) + f"\n\n📁 Files in DB: <b>{file_count}</b>"
    await _render_card(query, poster_url=title.get("poster_url"), caption=caption, reply_markup=admin_title_keyboard(title_id, title.get("media_type", "movie")))


@MovieBot.on_callback_query(filters.regex(r"^(st|pick|mq|mv|dl|ss|sq|sc|ep|pg)\|"))
async def user_callback_router(bot: MovieBot, query: CallbackQuery) -> None:
    if not await _ensure_owner(bot, query):
        return

    try:
        payload = decode(query.data)
    except Exception:
        await query.answer("Invalid action", show_alert=True)
        return

    if payload.action == "st":
        await _show_search_category(bot, query, payload.media_type or "movie")
        return

    if payload.action == "pick":
        title = await bot.catalog_service.get_title_details(payload.title_id)
        if not title:
            await query.answer("Title not found", show_alert=True)
            return
        await query.answer()
        await _show_title_selector(bot, query, title)
        return

    if payload.action == "mq":
        title = await bot.catalog_service.get_title_details(payload.title_id)
        if not title:
            await query.answer("Title not found", show_alert=True)
            return
        await query.answer()
        await _show_title_selector(bot, query, title, quality=payload.quality or "")
        return

    if payload.action == "mv":
        item = await bot.catalog_service.get_media_file_by_id(payload.media_file_id or "")
        title = await bot.catalog_service.get_title_details(payload.title_id)
        if not item or not title:
            await query.answer("Movie file not found", show_alert=True)
            return
        await query.answer()
        await _show_download_ready(bot, query, title, item)
        return

    if payload.action == "dl":
        item = await bot.catalog_service.get_media_file_by_id(payload.media_file_id or "")
        title = await bot.catalog_service.get_title_details(payload.title_id)
        if not item or not title:
            await query.answer("File not found", show_alert=True)
            return
        await _send_private_copy(bot, query, item, title)
        return

    if payload.action == "ss":
        title = await bot.catalog_service.get_title_details(payload.title_id)
        if not title:
            await query.answer("Title not found", show_alert=True)
            return
        await query.answer()
        await _show_title_selector(bot, query, title, season=payload.season)
        return

    if payload.action == "sq":
        title = await bot.catalog_service.get_title_details(payload.title_id)
        if not title:
            await query.answer("Title not found", show_alert=True)
            return
        await query.answer()
        await _show_title_selector(bot, query, title, season=payload.season, quality=payload.quality or "")
        return

    if payload.action in {"sc", "pg"}:
        title = await bot.catalog_service.get_title_details(payload.title_id)
        if not title:
            await query.answer("Title not found", show_alert=True)
            return
        page = payload.page or 0
        page_size = bot.settings.result_page_size
        episodes = await bot.db_service.get_series_episodes(title_id=payload.title_id, season=payload.season or 1, quality=payload.quality or "", codec=payload.codec or "", skip=page * page_size, limit=page_size)
        total_count = await bot.db_service.count_series_episodes(title_id=payload.title_id, season=payload.season or 1, quality=payload.quality or "", codec=payload.codec or "")
        if not episodes:
            await query.answer("Episodes not found", show_alert=True)
            return
        await query.answer()
        await _render_card(query, poster_url=_stage_photo(bot, title, stage="episode"), caption=build_stage_caption(bot.settings, title, stage="episode", season=payload.season, quality=payload.quality, codec=payload.codec), reply_markup=episodes_keyboard(title_id=payload.title_id, season=payload.season or 1, quality=payload.quality or "", codec=payload.codec or "", episodes=episodes, page=page, page_size=page_size, total_count=total_count))
        return

    if payload.action == "ep":
        item = await bot.catalog_service.get_media_file_by_id(payload.media_file_id or "")
        title = await bot.catalog_service.get_title_details(payload.title_id)
        if not item or not title:
            await query.answer("Episode not found", show_alert=True)
            return
        await query.answer()
        await _show_download_ready(bot, query, title, item)


@MovieBot.on_callback_query(filters.regex(r"^adm\|"))
async def admin_callback_router(bot: MovieBot, query: CallbackQuery) -> None:
    if not _is_admin(bot, query):
        await query.answer("Admins only", show_alert=True)
        return

    parts = (query.data or "").split("|")
    action = parts[1] if len(parts) > 1 else ""
    user_id = query.from_user.id

    if action == "home":
        bot.admin_states.pop(user_id, None)
        await query.answer()
        await query.message.reply_text("🛠 Admin panel", reply_markup=admin_home_keyboard())
        return

    if action == "find":
        media_type = parts[2]
        bot.admin_states[user_id] = {"mode": "await_find_title", "media_type": media_type}
        await query.answer()
        await query.message.reply_text(f"{media_type} title එක send කරන්න.")
        return

    if action == "sync":
        media_type = parts[2]
        bot.admin_states[user_id] = {"mode": f"await_{media_type}_forward"}
        await query.answer()
        await query.message.reply_text(f"{media_type} post එක forward කරන්න.")
        return

    if action == "title":
        await query.answer()
        await _admin_show_title(bot, query, parts[2])
        return

    if action == "poster":
        title_id = parts[2]
        title = await bot.db_service.get_title(title_id)
        if not title:
            await query.answer("Title not found", show_alert=True)
            return
        await query.answer()
        await _render_card(query, poster_url=title.get("poster_url"), caption=build_admin_title_caption(title) + "\n\n🖼 Poster tools වලින් option එකක් තෝරන්න.", reply_markup=admin_poster_keyboard(title_id))
        return

    if action == "posterauto":
        title_id = parts[2]
        title = await bot.db_service.get_title(title_id)
        if not title:
            await query.answer("Title not found", show_alert=True)
            return
        metadata = await bot.metadata_service.search(title.get("title", ""), title.get("media_type", "movie"), title.get("year"))
        updates = {
            "poster_url": metadata.get("poster_url") if metadata else title.get("poster_url"),
            "poster_source": metadata.get("poster_source") if metadata else title.get("poster_source"),
        }
        await bot.db_service.update_title_fields(title_id, updates)
        await query.answer("Poster refreshed")
        await _admin_show_title(bot, query, title_id)
        return

    if action == "posterremove":
        title_id = parts[2]
        await bot.db_service.update_title_fields(title_id, {"poster_url": None, "poster_source": None})
        await query.answer("Poster removed")
        await _admin_show_title(bot, query, title_id)
        return

    if action == "variants":
        title_id = parts[2]
        variants = await bot.db_service.list_title_variants(title_id)
        if not variants:
            await query.answer("Variants not found", show_alert=True)
            return
        await query.answer()
        await query.message.reply_text("Edit කරන්න variant එකක් තෝරන්න. Quality / Codec වෙනස් කරාම DB buttons auto update වෙයි.", reply_markup=admin_variant_picker(title_id, variants))
        return

    if action == "variant":
        title_id = parts[2]
        media_file_id = parts[3]
        media = await bot.db_service.get_media_file(media_file_id)
        if not media:
            await query.answer("Variant not found", show_alert=True)
            return
        await query.answer()
        caption = (
            "🧩 Selected variant\n\n"
            f"Quality: {media.get('quality', '-')}\n"
            f"Codec: {media.get('codec', '-')}\n"
            f"Size: {media.get('size_label', '-')}\n"
            f"Season: {media.get('season', '-')}\n"
            f"Episode: {media.get('episode', '-')}"
        )
        await query.message.reply_text(caption, reply_markup=admin_variant_edit_keyboard(title_id, media_file_id))
        return

    if action == "delask":
        title_id = parts[2]
        title = await bot.db_service.get_title(title_id)
        if not title:
            await query.answer("Title not found", show_alert=True)
            return
        file_count = await bot.db_service.count_title_files(title_id)
        await query.answer()
        await query.message.reply_text(
            f"🗑 <b>{title.get('title','Unknown Title')}</b> delete කරන්න ඕනේද?\n\nමේ title එකත්, related files <b>{file_count}</b>ක්ත් DB එකෙන් අයින් වෙනවා.",
            reply_markup=admin_confirm_delete_title_keyboard(title_id),
        )
        return

    if action == "deltitle":
        title_id = parts[2]
        await bot.db_service.delete_title_and_media(title_id)
        bot.admin_states.pop(user_id, None)
        await query.answer("Deleted")
        await query.message.reply_text("✅ Title + related files DB එකෙන් delete කළා.", reply_markup=admin_home_keyboard())
        return

    if action == "delfile":
        title_id = parts[2]
        media_file_id = parts[3]
        await bot.db_service.delete_media_file(media_file_id)
        remaining = await bot.db_service.list_title_variants(title_id)
        await query.answer("File deleted")
        if remaining:
            await query.message.reply_text("✅ Selected file delete කළා. Remaining variants මෙන්න.", reply_markup=admin_variant_picker(title_id, remaining))
        else:
            await query.message.reply_text("✅ File delete කළා. මේ title එකට තව variants නැහැ.")
        return

    if action == "edit":
        target = parts[2]
        field = parts[3]
        title_id = parts[4]
        if target == "title":
            bot.admin_states[user_id] = {"mode": f"await_edit_title_{field}", "title_id": title_id}
            hint = "Poster URL / auto / remove" if field == "poster" else "New title name"
            await query.answer()
            await query.message.reply_text(f"Reply with: {hint}")
            return

        if target == "file":
            media_file_id = parts[5]
            bot.admin_states[user_id] = {"mode": f"await_edit_file_{field}", "title_id": title_id, "media_file_id": media_file_id}
            hint = "New quality (480p / 720p / 1080p / 2160p / 4K)" if field == "quality" else "New codec (x264 / x265 / H264 / H265 / HEVC / AV1)"
            await query.answer()
            await query.message.reply_text(f"Reply with: {hint}")
            return

    if action == "retag":
        media_type = parts[2]
        title_id = parts[3]
        await bot.db_service.update_title_fields(title_id, {"media_type": media_type})
        await query.answer("Updated")
        await query.message.reply_text(f"✅ Title media type updated to {media_type}")
        return

    await query.answer("Unknown admin action", show_alert=True)

