from __future__ import annotations

from typing import Iterable, List

from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.utils.callbacks import encode
from app.utils.text import build_variant_button_text, build_variant_label, sort_qualities, ui_text


def category_keyboard(settings, *, movie_count: int = 0, series_count: int = 0) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton(
                ui_text(settings, "movie_tab_button_text", "🎬 Movies ({movie_count})", movie_count=movie_count),
                callback_data=encode(["st", "movie"]),
            ),
            InlineKeyboardButton(
                ui_text(settings, "series_tab_button_text", "📺 TV Series ({series_count})", series_count=series_count),
                callback_data=encode(["st", "series"]),
            ),
        ]]
    )


def search_results_keyboard(settings, items: list[dict], *, movie_count: int = 0, series_count: int = 0, active_type: str = "movie") -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                ui_text(settings, "movie_tab_button_text", "🎬 Movies ({movie_count})", movie_count=movie_count),
                callback_data=encode(["st", "movie"]),
            ),
            InlineKeyboardButton(
                ui_text(settings, "series_tab_button_text", "📺 TV Series ({series_count})", series_count=series_count),
                callback_data=encode(["st", "series"]),
            ),
        ]
    ]

    if not items:
        rows.append([InlineKeyboardButton(ui_text(settings, "no_results_button_text", "❌ No results"), callback_data=encode(["st", active_type]))])
        return InlineKeyboardMarkup(rows)

    for item in items[:8]:
        year_label = f" ({item['year']})" if item.get("year") else ""
        if item.get("media_type") == "series":
            label = ui_text(settings, "series_title_button_text", "📺 {title}{year_label}", title=item.get("title", "Unknown"), year=item.get("year"), year_label=year_label)
        else:
            label = ui_text(settings, "movie_title_button_text", "🎞 {title}{year_label}", title=item.get("title", "Unknown"), year=item.get("year"), year_label=year_label)
        rows.append([InlineKeyboardButton(label[:60], callback_data=encode(["pick", str(item["_id"])]))])

    return InlineKeyboardMarkup(rows)


def bot_inbox_keyboard(settings, bot_username: str | None) -> InlineKeyboardMarkup | None:
    if not bot_username:
        return None
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(ui_text(settings, "open_inbox_button_text", "📩 Open Bot Inbox"), url=f"https://t.me/{bot_username}?start=downloads")]]
    )


def qualities_keyboard(settings, title_id: str, qualities: Iterable[str], *, season: int | None = None, episode: int | None = None) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    for quality in sort_qualities(qualities):
        if season is None or episode is None:
            data = encode(["mq", title_id, quality])
        else:
            data = encode(["eq", title_id, season, episode, quality])
        rows.append([InlineKeyboardButton(ui_text(settings, "quality_button_text", "📦 {quality}", quality=quality), callback_data=data)])
    return InlineKeyboardMarkup(rows)


def movie_variants_keyboard(settings, title_id: str, items: list[dict]) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    for item in items[:20]:
        rows.append([
            InlineKeyboardButton(
                build_variant_button_text(item, settings)[:60],
                callback_data=encode(["mv", title_id, str(item["_id"])]),
            )
        ])
    return InlineKeyboardMarkup(rows)


def seasons_keyboard(settings, title_id: str, seasons: Iterable[int]) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    for season in seasons:
        rows.append([InlineKeyboardButton(ui_text(settings, "season_button_text", "🗂 Season {season}", season=season), callback_data=encode(["ss", title_id, season, 0]))])
    return InlineKeyboardMarkup(rows)


def season_episodes_keyboard(settings, title_id: str, season: int, episodes: list[int], page: int, page_size: int, total_count: int) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    batch: List[InlineKeyboardButton] = []
    for episode in episodes:
        batch.append(InlineKeyboardButton(ui_text(settings, "episode_button_text", "🎬 E{episode_label}", episode=episode, episode_label=f"{int(episode):02d}"), callback_data=encode(["se", title_id, season, episode])))
        if len(batch) == 3:
            rows.append(batch)
            batch = []
    if batch:
        rows.append(batch)

    nav: List[InlineKeyboardButton] = []
    if page > 0:
        nav.append(InlineKeyboardButton(ui_text(settings, "prev_button_text", "⬅️ Prev"), callback_data=encode(["sp", title_id, season, page - 1])))
    if (page + 1) * page_size < total_count:
        nav.append(InlineKeyboardButton(ui_text(settings, "next_button_text", "Next ➡️"), callback_data=encode(["sp", title_id, season, page + 1])))
    if nav:
        rows.append(nav)

    return InlineKeyboardMarkup(rows)


def episode_variants_keyboard(settings, title_id: str, items: list[dict]) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    for item in items[:20]:
        rows.append([
            InlineKeyboardButton(
                build_variant_button_text(item, settings)[:60],
                callback_data=encode(["ev", title_id, str(item["_id"])]),
            )
        ])
    return InlineKeyboardMarkup(rows)


def download_keyboard(settings, title_id: str, media_file_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(ui_text(settings, "download_button_text", "⬇️ Download to Inbox"), callback_data=encode(["dl", title_id, media_file_id]))]]
    )


def admin_home_keyboard(settings) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(ui_text(settings, "admin_manage_movies_button_text", "🎬 Manage Movies"), callback_data="adm|find|movie")],
            [InlineKeyboardButton(ui_text(settings, "admin_manage_series_button_text", "📺 Manage Series"), callback_data="adm|find|series")],
            [InlineKeyboardButton(ui_text(settings, "admin_sync_series_button_text", "📥 Sync Series Post"), callback_data="adm|sync|series")],
            [InlineKeyboardButton(ui_text(settings, "admin_sync_movie_button_text", "📥 Sync Movie Post"), callback_data="adm|sync|movie")],
        ]
    )


def admin_pick_title_keyboard(settings, items: list[dict]) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    for item in items[:8]:
        year_label = f" ({item['year']})" if item.get("year") else ""
        if item.get("media_type") == "series":
            label = ui_text(settings, "series_title_button_text", "📺 {title}{year_label}", title=item.get("title", "Unknown"), year=item.get("year"), year_label=year_label)
        else:
            label = ui_text(settings, "movie_title_button_text", "🎞 {title}{year_label}", title=item.get("title", "Unknown"), year=item.get("year"), year_label=year_label)
        rows.append([InlineKeyboardButton(label[:60], callback_data=f"adm|title|{item['_id']}")])
    rows.append([InlineKeyboardButton(ui_text(settings, "admin_back_button_text", "⬅️ Back"), callback_data="adm|home")])
    return InlineKeyboardMarkup(rows)


def admin_title_keyboard(settings, title_id: str, media_type: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(ui_text(settings, "admin_poster_tools_button_text", "🖼 Poster Tools"), callback_data=f"adm|poster|{title_id}")],
            [InlineKeyboardButton(ui_text(settings, "admin_edit_name_button_text", "🎞 Edit Name"), callback_data=f"adm|edit|title|name|{title_id}")],
            [InlineKeyboardButton(ui_text(settings, "admin_manage_variants_button_text", "🎚 Manage Quality / Codec"), callback_data=f"adm|variants|{title_id}")],
            [InlineKeyboardButton(ui_text(settings, "admin_delete_title_button_text", "🗑 Delete This Title"), callback_data=f"adm|delask|{title_id}")],
            [InlineKeyboardButton(ui_text(settings, "admin_back_home_button_text", "⬅️ Admin Home"), callback_data="adm|home")],
        ]
    )


def admin_poster_keyboard(settings, title_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(ui_text(settings, "admin_auto_refresh_poster_button_text", "♻️ Auto Refresh Poster"), callback_data=f"adm|posterauto|{title_id}")],
            [InlineKeyboardButton(ui_text(settings, "admin_remove_poster_button_text", "🧹 Remove Poster"), callback_data=f"adm|posterremove|{title_id}")],
            [InlineKeyboardButton(ui_text(settings, "admin_manual_poster_url_button_text", "🔗 Set Manual Poster URL"), callback_data=f"adm|edit|title|poster|{title_id}")],
            [InlineKeyboardButton(ui_text(settings, "admin_back_button_text", "⬅️ Back"), callback_data=f"adm|title|{title_id}")],
        ]
    )


def admin_confirm_delete_title_keyboard(settings, title_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(ui_text(settings, "admin_confirm_delete_button_text", "✅ Yes, Delete"), callback_data=f"adm|deltitle|{title_id}")],
            [InlineKeyboardButton(ui_text(settings, "admin_cancel_button_text", "❌ Cancel"), callback_data=f"adm|title|{title_id}")],
        ]
    )


def admin_variant_picker(settings, title_id: str, variants: list[dict]) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    for item in variants[:20]:
        label = build_variant_label(item)
        rows.append([InlineKeyboardButton(label[:60], callback_data=f"adm|variant|{title_id}|{item['_id']}")])
    rows.append([InlineKeyboardButton(ui_text(settings, "admin_back_button_text", "⬅️ Back"), callback_data=f"adm|title|{title_id}")])
    return InlineKeyboardMarkup(rows)


def admin_variant_edit_keyboard(settings, title_id: str, media_file_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(ui_text(settings, "admin_change_quality_button_text", "📦 Change Quality"), callback_data=f"adm|edit|file|quality|{title_id}|{media_file_id}")],
            [InlineKeyboardButton(ui_text(settings, "admin_change_codec_button_text", "⚙️ Change Codec"), callback_data=f"adm|edit|file|codec|{title_id}|{media_file_id}")],
            [InlineKeyboardButton(ui_text(settings, "admin_delete_file_button_text", "🗑 Delete This File"), callback_data=f"adm|delfile|{title_id}|{media_file_id}")],
            [InlineKeyboardButton(ui_text(settings, "admin_back_button_text", "⬅️ Back"), callback_data=f"adm|variants|{title_id}")],
        ]
    )

```

