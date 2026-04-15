from __future__ import annotations

from pyrogram import filters
from pyrogram.errors import RPCError
from pyrogram.types import CallbackQuery, InputMediaPhoto

from app.bot import MovieBot
from app.keyboards.browser import (
    admin_home_keyboard,
    admin_title_keyboard,
    admin_variant_edit_keyboard,
    admin_variant_picker,
    bot_inbox_keyboard,
    codecs_keyboard,
    episodes_keyboard,
    qualities_keyboard,
    search_results_keyboard,
    seasons_keyboard,
)
from app.utils.callbacks import decode
from app.utils.text import (
    build_admin_title_caption,
    build_group_delivery_text,
    build_inbox_intro_caption,
    build_inbox_reply_text,
    build_search_preview_caption,
    build_start_needed_text,
    build_title_card_caption,
    sort_qualities,
)


async def _render_card(
    query: CallbackQuery,
    *,
    poster_url: str | None,
    caption: str,
    reply_markup,
) -> None:
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
    best = items[0]
    await query.answer()
    await _render_card(
        query,
        poster_url=best.get("poster_url"),
        caption=build_search_preview_caption(best, movie_count=movie_count, series_count=series_count, active_type=media_type),
        reply_markup=search_results_keyboard(items, movie_count=movie_count, series_count=series_count, active_type=media_type),
    )


async def _show_title_selector(
    bot: MovieBot,
    query: CallbackQuery,
    title: dict,
    *,
    season: int | None = None,
    quality: str | None = None,
    codec: str | None = None,
) -> None:
    title_id = str(title["_id"])

    if title.get("media_type") == "series":
        if season is None:
            seasons = await bot.db_service.get_available_seasons(title_id)
            if not seasons:
                await query.message.reply_text("මේ series එකට season data නැහැ.")
                return
            markup = seasons_keyboard(title_id, seasons)
        elif quality is None:
            qualities = await bot.db_service.get_available_qualities(title_id, season=season)
            markup = qualities_keyboard(title_id, sort_qualities(qualities), back_to_series=season)
        elif codec is None:
            codecs = await bot.db_service.get_available_codecs(title_id, quality, season=season)
            markup = codecs_keyboard(title_id, quality, codecs, season=season)
        else:
            page_size = bot.settings.result_page_size
            episodes = await bot.db_service.get_series_episodes(
                title_id=title_id,
                season=season,
                quality=quality,
                codec=codec,
                skip=0,
                limit=page_size,
            )
            total_count = await bot.db_service.count_series_episodes(
                title_id=title_id,
                season=season,
                quality=quality,
                codec=codec,
            )
            if not episodes:
                await query.message.reply_text("Episodes not found")
                return
            markup = episodes_keyboard(
                title_id=title_id,
                season=season,
                quality=quality,
                codec=codec,
                episodes=episodes,
                page=0,
                page_size=page_size,
                total_count=total_count,
            )
    else:
        if quality is None:
            qualities = await bot.db_service.get_available_qualities(title_id)
            markup = qualities_keyboard(title_id, qualities)
        elif codec is None:
            codecs = await bot.db_service.get_available_codecs(title_id, quality)
            markup = codecs_keyboard(title_id, quality, codecs)
        else:
            markup = None

    caption = build_title_card_caption(title, season=season, quality=quality, codec=codec)
    await _render_card(query, poster_url=title.get("poster_url"), caption=caption, reply_markup=markup)


async def _send_private_copy(bot: MovieBot, query: CallbackQuery, item: dict, title: dict, label: str) -> None:
    inbox_markup = bot_inbox_keyboard(bot.settings.bot_username)
    try:
        poster_url = title.get("poster_url")
        intro_caption = build_inbox_intro_caption(
            title,
            season=item.get("season"),
            episode=item.get("episode"),
            quality=item.get("quality"),
            codec=item.get("codec"),
        )
        if poster_url:
            await bot.send_photo(query.from_user.id, poster_url, caption=intro_caption)
        else:
            await bot.send_message(query.from_user.id, intro_caption)

        copied = await bot.copy_message(
            chat_id=query.from_user.id,
            from_chat_id=item["source_chat_id"],
            message_id=item["source_message_id"],
        )
        await bot.send_message(query.from_user.id, build_inbox_reply_text(title), reply_to_message_id=copied.id)
        await query.answer(f"{label} sent to private chat")
        await query.message.reply_text(build_group_delivery_text(title), reply_markup=inbox_markup)
    except RPCError:
        await query.answer("Open the bot in private chat first", show_alert=True)
        await query.message.reply_text(build_start_needed_text(bot.settings.bot_username), reply_markup=inbox_markup)



def _is_admin(bot: MovieBot, query: CallbackQuery) -> bool:
    return bool(query.from_user and (not bot.settings.admins or query.from_user.id in bot.settings.admins))


@MovieBot.on_callback_query(filters.regex(r"^(st|pick|mq|mc|ss|sq|sc|ep|pg)\|"))
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

    if payload.action == "mc":
        item = await bot.db_service.get_movie_variant(payload.title_id, payload.quality or "", payload.codec or "")
        title = await bot.catalog_service.get_title_details(payload.title_id)
        if not item or not title:
            await query.answer("Movie file not found", show_alert=True)
            return
        await _send_private_copy(bot, query, item, title, "Movie")
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
        episodes = await bot.db_service.get_series_episodes(
            title_id=payload.title_id,
            season=payload.season or 1,
            quality=payload.quality or "",
            codec=payload.codec or "",
            skip=page * page_size,
            limit=page_size,
        )
        total_count = await bot.db_service.count_series_episodes(
            title_id=payload.title_id,
            season=payload.season or 1,
            quality=payload.quality or "",
            codec=payload.codec or "",
        )
        if not episodes:
            await query.answer("Episodes not found", show_alert=True)
            return
        await query.answer()
        await _render_card(
            query,
            poster_url=title.get("poster_url"),
            caption=build_title_card_caption(title, season=payload.season, quality=payload.quality, codec=payload.codec),
            reply_markup=episodes_keyboard(
                title_id=payload.title_id,
                season=payload.season or 1,
                quality=payload.quality or "",
                codec=payload.codec or "",
                episodes=episodes,
                page=page,
                page_size=page_size,
                total_count=total_count,
            ),
        )
        return

    if payload.action == "ep":
        item = await bot.catalog_service.get_media_file_by_id(payload.episode_id or "")
        title = await bot.catalog_service.get_title_details(payload.title_id)
        if not item or not title:
            await query.answer("Episode not found", show_alert=True)
            return
        await _send_private_copy(bot, query, item, title, "Episode")


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
        title_id = parts[2]
        title = await bot.db_service.get_title(title_id)
        if not title:
            await query.answer("Title not found", show_alert=True)
            return
        await query.answer()
        await _render_card(
            query,
            poster_url=title.get("poster_url"),
            caption=build_admin_title_caption(title),
            reply_markup=admin_title_keyboard(title_id, title.get("media_type", "movie")),
        )
        return

    if action == "variants":
        title_id = parts[2]
        variants = await bot.db_service.list_title_variants(title_id)
        if not variants:
            await query.answer("Variants not found", show_alert=True)
            return
        await query.answer()
        await query.message.reply_text("Edit කරන්න variant එක තෝරන්න.", reply_markup=admin_variant_picker(title_id, variants))
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
            f"Season: {media.get('season', '-')}\n"
            f"Episode: {media.get('episode', '-')}"
        )
        await query.message.reply_text(caption, reply_markup=admin_variant_edit_keyboard(title_id, media_file_id))
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
