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
    download_keyboard,
    episode_variants_keyboard,
    movie_variants_keyboard,
    qualities_keyboard,
    search_results_keyboard,
    season_episodes_keyboard,
    seasons_keyboard,
)
from app.utils.callbacks import decode
from app.utils.text import (
    build_admin_title_caption,
    build_inbox_intro_caption,
    build_inbox_reply_text,
    build_search_hub_caption,
    build_stage_caption,
    media_type_label,
)


async def _render_card(query: CallbackQuery, *, poster_url: str | None, caption: str, reply_markup) -> None:
    try:
        if poster_url:
            await query.message.edit_media(InputMediaPhoto(media=poster_url, caption=caption), reply_markup=reply_markup)
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


def _stage_photo(bot: MovieBot, title: dict | None = None, *, final: bool = False) -> str | None:
    if final and title and title.get("poster_url"):
        return title.get("poster_url")
    return None


async def _ensure_download_poster(bot: MovieBot, title: dict) -> dict:
    if title.get("poster_url"):
        return title
    metadata = await bot.metadata_service.search(title.get("title", ""), title.get("media_type", "movie"), title.get("year"))
    if metadata and metadata.get("poster_url"):
        await bot.db_service.update_title_fields(str(title["_id"]), {"poster_url": metadata.get("poster_url"), "poster_source": metadata.get("poster_source")})
        title = await bot.db_service.get_title(title["_id"])
    return title


async def _show_search_category(bot: MovieBot, query: CallbackQuery, media_type: str, page: int = 0) -> None:
    session = _get_search_session(bot, query)
    if not session:
        await query.answer("Search session expired", show_alert=True)
        return
    title_ids = session.get("movies", []) if media_type == "movie" else session.get("series", [])
    items: list[dict] = []
    for title_id in title_ids:
        title = await bot.db_service.get_title(title_id)
        if title:
            items.append(title)
    if not items:
        await query.answer("Results not found", show_alert=True)
        return
    await query.answer()
    await _render_card(
        query,
        poster_url=None,
        caption=build_search_hub_caption(session.get("query", "Search"), movie_count=len(session.get("movies", [])), series_count=len(session.get("series", [])), active_type=media_type),
        reply_markup=search_results_keyboard(bot.settings, items, movie_count=len(session.get("movies", [])), series_count=len(session.get("series", [])), active_type=media_type, page=page, page_size=bot.settings.result_page_size),
    )


async def _show_series_seasons(bot: MovieBot, query: CallbackQuery, title: dict) -> None:
    seasons = await bot.db_service.get_available_seasons(str(title["_id"]))
    if not seasons:
        await query.answer("මේ series එකට season data නැහැ.", show_alert=True)
        return
    await _render_card(query, poster_url=None, caption=build_stage_caption(bot.settings, title, stage="season"), reply_markup=seasons_keyboard(bot.settings, str(title["_id"]), seasons))


async def _show_series_episode_page(bot: MovieBot, query: CallbackQuery, title: dict, *, season: int, page: int = 0) -> None:
    page_size = bot.settings.result_page_size
    episodes = await bot.db_service.get_available_episode_numbers(str(title["_id"]), season, skip=page * page_size, limit=page_size)
    total_count = await bot.db_service.count_available_episode_numbers(str(title["_id"]), season)
    if not episodes:
        await query.answer("Episodes not found", show_alert=True)
        return
    await _render_card(query, poster_url=None, caption=build_stage_caption(bot.settings, title, stage="episode", season=season), reply_markup=season_episodes_keyboard(bot.settings, str(title["_id"]), season, episodes, page, page_size, total_count))


async def _show_series_episode_qualities(bot: MovieBot, query: CallbackQuery, title: dict, *, season: int, episode: int) -> None:
    qualities = await bot.db_service.get_episode_qualities(str(title["_id"]), season, episode)
    if not qualities:
        await query.answer("මේ episode එකට qualities නැහැ.", show_alert=True)
        return
    await _render_card(query, poster_url=None, caption=build_stage_caption(bot.settings, title, stage="quality", season=season, episode=episode), reply_markup=qualities_keyboard(bot.settings, str(title["_id"]), qualities, season=season, episode=episode, back_data=f"ss|{title['_id']}|{season}|0"))


async def _show_series_variants(bot: MovieBot, query: CallbackQuery, title: dict, *, season: int, episode: int, quality: str) -> None:
    variants = await bot.db_service.list_episode_variants(str(title["_id"]), season, episode, quality)
    if not variants:
        await query.answer("Episode files not found", show_alert=True)
        return
    await _render_card(query, poster_url=None, caption=build_stage_caption(bot.settings, title, stage="codec", season=season, episode=episode, quality=quality), reply_markup=episode_variants_keyboard(bot.settings, str(title["_id"]), variants, season=season, episode=episode, quality=quality))


async def _show_movie_quality_page(bot: MovieBot, query: CallbackQuery, title: dict, page: int = 0) -> None:
    qualities = await bot.db_service.get_available_qualities(str(title["_id"]))
    await _render_card(query, poster_url=None, caption=build_stage_caption(bot.settings, title, stage="quality"), reply_markup=qualities_keyboard(bot.settings, str(title["_id"]), qualities, page=page, page_size=bot.settings.result_page_size, back_data=None))


async def _show_movie_variants_page(bot: MovieBot, query: CallbackQuery, title: dict, quality: str, page: int = 0) -> None:
    variants = await bot.db_service.list_movie_variants(str(title["_id"]), quality)
    if not variants:
        await query.answer("Movie variants not found", show_alert=True)
        return
    await _render_card(query, poster_url=None, caption=build_stage_caption(bot.settings, title, stage="codec", quality=quality), reply_markup=movie_variants_keyboard(bot.settings, str(title["_id"]), quality, variants, page=page, page_size=bot.settings.result_page_size))


async def _show_download_ready(bot: MovieBot, query: CallbackQuery, title: dict, item: dict) -> None:
    title = await _ensure_download_poster(bot, title)
    caption = build_stage_caption(bot.settings, title, stage="download", season=item.get("season"), episode=item.get("episode"), quality=item.get("quality"), codec=item.get("codec"), size_label=item.get("size_label"))
    await _render_card(query, poster_url=_stage_photo(bot, title, final=True), caption=caption, reply_markup=download_keyboard(bot.settings, str(title["_id"]), str(item["_id"])))


async def _send_private_copy(bot: MovieBot, query: CallbackQuery, item: dict, title: dict) -> None:
    try:
        title = await _ensure_download_poster(bot, title)
        intro_caption = build_inbox_intro_caption(title, season=item.get("season"), episode=item.get("episode"), quality=item.get("quality"), codec=item.get("codec"), size_label=item.get("size_label"))
        if title.get("poster_url"):
            try:
                await bot.send_photo(query.from_user.id, title["poster_url"], caption=intro_caption)
            except RPCError:
                await bot.send_message(query.from_user.id, intro_caption)
        else:
            await bot.send_message(query.from_user.id, intro_caption)
        copied = None
        source_chat_id = item.get("source_chat_id")
        source_message_id = item.get("source_message_id")
        if source_chat_id and source_message_id:
            try:
                copied = await bot.copy_message(chat_id=query.from_user.id, from_chat_id=source_chat_id, message_id=source_message_id)
            except Exception:
                copied = None
        if copied is None and item.get("telegram_file_id"):
            copied = await bot.send_cached_media(chat_id=query.from_user.id, file_id=item["telegram_file_id"])
        if copied:
            await bot.send_message(query.from_user.id, build_inbox_reply_text(title), reply_to_message_id=copied.id)
            await query.answer()
        else:
            await query.answer("Open the bot in private chat first or re-sync this file", show_alert=True)
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
    await _render_card(query, poster_url=title.get("poster_url"), caption=caption, reply_markup=admin_title_keyboard(bot.settings, title_id, title.get("media_type", "movie")))


@MovieBot.on_callback_query(filters.regex(r"^(st|pick|mqp|mq|mvp|mv|dl|ss|sp|se|eq|ev)\|"))
async def user_callback_router(bot: MovieBot, query: CallbackQuery) -> None:
    if not await _ensure_owner(bot, query):
        return
    try:
        payload = decode(query.data)
    except Exception:
        await query.answer("Invalid action", show_alert=True)
        return
    if payload.action == "st":
        await _show_search_category(bot, query, payload.media_type or "movie", page=payload.page)
        return
    title = None
    if payload.title_id:
        title = await bot.catalog_service.get_title_details(payload.title_id)
        if not title:
            await query.answer("Title not found", show_alert=True)
            return
    if payload.action == "pick":
        await query.answer()
        if title.get("media_type") == "series":
            await _show_series_seasons(bot, query, title)
        else:
            await _show_movie_quality_page(bot, query, title)
        return
    if payload.action == "mqp":
        await query.answer()
        await _show_movie_quality_page(bot, query, title, page=payload.page)
        return
    if payload.action == "mq":
        await query.answer()
        await _show_movie_variants_page(bot, query, title, payload.quality or "", page=payload.page)
        return
    if payload.action == "mvp":
        await query.answer()
        await _show_movie_variants_page(bot, query, title, payload.quality or "", page=payload.page)
        return
    if payload.action == "mv":
        item = await bot.catalog_service.get_media_file_by_id(payload.media_file_id or "")
        if not item:
            await query.answer("Movie file not found", show_alert=True)
            return
        await query.answer()
        await _show_download_ready(bot, query, title, item)
        return
    if payload.action == "ss":
        await query.answer()
        await _show_series_episode_page(bot, query, title, season=payload.season or 1, page=payload.page)
        return
    if payload.action == "sp":
        await query.answer()
        await _show_series_episode_page(bot, query, title, season=payload.season or 1, page=payload.page)
        return
    if payload.action == "se":
        await query.answer()
        await _show_series_episode_qualities(bot, query, title, season=payload.season or 1, episode=payload.episode or 1)
        return
    if payload.action == "eq":
        await query.answer()
        await _show_series_variants(bot, query, title, season=payload.season or 1, episode=payload.episode or 1, quality=payload.quality or "")
        return
    if payload.action == "ev":
        item = await bot.catalog_service.get_media_file_by_id(payload.media_file_id or "")
        if not item:
            await query.answer("Episode not found", show_alert=True)
            return
        await query.answer()
        await _show_download_ready(bot, query, title, item)
        return
    if payload.action == "dl":
        item = await bot.catalog_service.get_media_file_by_id(payload.media_file_id or "")
        if not item:
            await query.answer("File not found", show_alert=True)
            return
        await _send_private_copy(bot, query, item, title)
        return


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
        await query.message.reply_text("🛠 Admin panel", reply_markup=admin_home_keyboard(bot.settings))
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
        await _render_card(query, poster_url=title.get("poster_url"), caption=build_admin_title_caption(title) + "\n\n🖼 Poster tools වලින් option එකක් තෝරන්න.", reply_markup=admin_poster_keyboard(bot.settings, title_id))
        return
    if action == "posterauto":
        title_id = parts[2]
        title = await bot.db_service.get_title(title_id)
        if not title:
            await query.answer("Title not found", show_alert=True)
            return
        metadata = await bot.metadata_service.search(title.get("title", ""), title.get("media_type", "movie"), title.get("year"))
        if metadata:
            await bot.db_service.update_title_fields(title_id, {"poster_url": metadata.get("poster_url"), "poster_source": metadata.get("poster_source")})
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
        await query.message.reply_text("Edit කරන්න variant එකක් තෝරන්න.", reply_markup=admin_variant_picker(bot.settings, title_id, variants))
        return
    if action == "variant":
        title_id, media_file_id = parts[2], parts[3]
        media = await bot.db_service.get_media_file(media_file_id)
        if not media:
            await query.answer("Variant not found", show_alert=True)
            return
        caption = ("🧩 Selected variant\n\n" f"Quality: {media.get('quality', '-')}\n" f"Codec: {media.get('codec', '-')}\n" f"Size: {media.get('size_label', '-')}\n" f"Season: {media.get('season', '-')}\n" f"Episode: {media.get('episode', '-')}")
        await query.answer()
        await query.message.reply_text(caption, reply_markup=admin_variant_edit_keyboard(bot.settings, title_id, media_file_id))
        return
    if action == "delask":
        title_id = parts[2]
        title = await bot.db_service.get_title(title_id)
        if not title:
            await query.answer("Title not found", show_alert=True)
            return
        file_count = await bot.db_service.count_title_files(title_id)
        await query.answer()
        await query.message.reply_text(f"🗑 <b>{title.get('title', 'Unknown Title')}</b> delete කරන්න ඕනේද?\n\nමේ title එකත්, related files <b>{file_count}</b>ක්ත් DB එකෙන් අයින් වෙනවා.", reply_markup=admin_confirm_delete_title_keyboard(bot.settings, title_id))
        return
    if action == "deltitle":
        title_id = parts[2]
        await bot.db_service.delete_title_and_media(title_id)
        bot.admin_states.pop(user_id, None)
        await query.answer("Deleted")
        await query.message.reply_text("✅ Title + related files DB එකෙන් delete කළා.", reply_markup=admin_home_keyboard(bot.settings))
        return
    if action == "delfile":
        title_id, media_file_id = parts[2], parts[3]
        await bot.db_service.delete_media_file(media_file_id)
        remaining = await bot.db_service.list_title_variants(title_id)
        await query.answer("File deleted")
        if remaining:
            await query.message.reply_text("✅ Selected file delete කළා. Remaining variants මෙන්න.", reply_markup=admin_variant_picker(bot.settings, title_id, remaining))
        else:
            await query.message.reply_text("✅ File delete කළා. මේ title එකට තව variants නැහැ.")
        return
    if action == "moveto":
        bot.admin_states[user_id] = {"mode": "await_move_file_title", "media_file_id": parts[3], "title_id": parts[2]}
        await query.answer()
        await query.message.reply_text("Move කරන්න ඕන correct title එක text එකෙන් එවන්න.")
        return
    if action == "replace":
        bot.admin_states[user_id] = {"mode": "await_replace_media", "media_file_id": parts[3], "title_id": parts[2]}
        await query.answer()
        await query.message.reply_text("Replace කරන්න new video/document file එක private chat එකට එවන්න.")
        return
    if action == "edit":
        target, field, title_id = parts[2], parts[3], parts[4]
        if target == "title":
            bot.admin_states[user_id] = {"mode": f"await_edit_title_{field}", "title_id": title_id}
            hint = "Poster URL / auto / remove" if field == "poster" else "New title name"
            await query.answer()
            await query.message.reply_text(f"Reply with: {hint}")
            return
        if target == "file":
            media_file_id = parts[5]
            bot.admin_states[user_id] = {"mode": f"await_edit_file_{field}", "title_id": title_id, "media_file_id": media_file_id}
            hint = "New quality" if field == "quality" else "New codec"
            await query.answer()
            await query.message.reply_text(f"Reply with: {hint}")
            return
    await query.answer("Unknown admin action", show_alert=True)
