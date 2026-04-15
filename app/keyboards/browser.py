from __future__ import annotations

from typing import Iterable, List

from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.utils.callbacks import encode
from app.utils.text import build_variant_label, sort_qualities


def search_results_keyboard(items: list[dict], *, movie_count: int = 0, series_count: int = 0, active_type: str = "movie") -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    rows.append(
        [
            InlineKeyboardButton(
                f"🎬 Movies ({movie_count})",
                callback_data=encode(["st", "movie"]),
            ),
            InlineKeyboardButton(
                f"📺 TV Series ({series_count})",
                callback_data=encode(["st", "series"]),
            ),
        ]
    )

    if not items:
        rows.append([InlineKeyboardButton("❌ No results", callback_data=encode(["st", active_type]))])
        return InlineKeyboardMarkup(rows)

    primary = items[0]
    primary_icon = "📺" if primary.get("media_type") == "series" else "🎬"
    primary_text = "⬇️ Download TV Series" if primary.get("media_type") == "series" else "⬇️ Download Movie"
    rows.append([InlineKeyboardButton(f"{primary_icon} {primary_text}", callback_data=encode(["pick", str(primary["_id"])]))])

    for item in items[1:6]:
        icon = "📺" if item.get("media_type") == "series" else "🎬"
        label = f"{icon} {item['title']}"
        if item.get("year"):
            label += f" ({item['year']})"
        rows.append([InlineKeyboardButton(label[:60], callback_data=encode(["pick", str(item["_id"])]))])

    return InlineKeyboardMarkup(rows)



def bot_inbox_keyboard(bot_username: str | None) -> InlineKeyboardMarkup | None:
    if not bot_username:
        return None
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("📩 Open Bot Inbox", url=f"https://t.me/{bot_username}?start=downloads")]]
    )



def qualities_keyboard(title_id: str, qualities: Iterable[str], back_to_series: int | None = None) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    for quality in sort_qualities(qualities):
        if back_to_series is None:
            data = encode(["mq", title_id, quality])
        else:
            data = encode(["sq", title_id, back_to_series, quality])
        rows.append([InlineKeyboardButton(f"📦 {quality}", callback_data=data)])
    return InlineKeyboardMarkup(rows)



def codecs_keyboard(title_id: str, quality: str, codecs: Iterable[str], season: int | None = None) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    for codec in sorted({codec for codec in codecs if codec}):
        if season is None:
            data = encode(["mc", title_id, quality, codec])
        else:
            data = encode(["sc", title_id, season, quality, codec, 0])
        rows.append([InlineKeyboardButton(f"⚙️ {codec}", callback_data=data)])
    return InlineKeyboardMarkup(rows)



def seasons_keyboard(title_id: str, seasons: Iterable[int]) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    for season in seasons:
        rows.append([InlineKeyboardButton(f"🗂 Season {season}", callback_data=encode(["ss", title_id, season]))])
    return InlineKeyboardMarkup(rows)



def episodes_keyboard(
    title_id: str,
    season: int,
    quality: str,
    codec: str,
    episodes: list[dict],
    page: int,
    page_size: int,
    total_count: int,
) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    for item in episodes:
        ep = item.get("episode")
        label = f"▶️ Episode {ep}" if ep is not None else "▶️ Send file"
        rows.append([InlineKeyboardButton(label, callback_data=encode(["ep", title_id, str(item["_id"])]))])

    nav: List[InlineKeyboardButton] = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=encode(["pg", title_id, season, quality, codec, page - 1])))
    if (page + 1) * page_size < total_count:
        nav.append(InlineKeyboardButton("Next ➡️", callback_data=encode(["pg", title_id, season, quality, codec, page + 1])))
    if nav:
        rows.append(nav)

    return InlineKeyboardMarkup(rows)



def admin_home_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🎬 Manage Movies", callback_data="adm|find|movie")],
            [InlineKeyboardButton("📺 Manage Series", callback_data="adm|find|series")],
            [InlineKeyboardButton("📥 Sync Series Post", callback_data="adm|sync|series")],
            [InlineKeyboardButton("📥 Sync Movie Post", callback_data="adm|sync|movie")],
        ]
    )



def admin_pick_title_keyboard(items: list[dict]) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    for item in items[:8]:
        icon = "📺" if item.get("media_type") == "series" else "🎬"
        label = f"{icon} {item.get('title', 'Unknown')}"
        if item.get("year"):
            label += f" ({item['year']})"
        rows.append([InlineKeyboardButton(label, callback_data=f"adm|title|{item['_id']}")])
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data="adm|home")])
    return InlineKeyboardMarkup(rows)



def admin_title_keyboard(title_id: str, media_type: str) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = [
        [InlineKeyboardButton("🖼 Edit Poster", callback_data=f"adm|edit|title|poster|{title_id}")],
        [InlineKeyboardButton("🎞 Edit Name", callback_data=f"adm|edit|title|name|{title_id}")],
        [InlineKeyboardButton("🎚 Edit Quality / Codec", callback_data=f"adm|variants|{title_id}")],
    ]
    if media_type == "series":
        rows.append([InlineKeyboardButton("📺 Mark as Series", callback_data=f"adm|retag|series|{title_id}")])
    rows.append([InlineKeyboardButton("⬅️ Admin Home", callback_data="adm|home")])
    return InlineKeyboardMarkup(rows)



def admin_variant_picker(title_id: str, variants: list[dict]) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    for item in variants[:20]:
        label = build_variant_label(item)
        rows.append([InlineKeyboardButton(label[:60], callback_data=f"adm|variant|{title_id}|{item['_id']}")])
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data=f"adm|title|{title_id}")])
    return InlineKeyboardMarkup(rows)



def admin_variant_edit_keyboard(title_id: str, media_file_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📦 Change Quality", callback_data=f"adm|edit|file|quality|{title_id}|{media_file_id}")],
            [InlineKeyboardButton("⚙️ Change Codec", callback_data=f"adm|edit|file|codec|{title_id}|{media_file_id}")],
            [InlineKeyboardButton("⬅️ Back", callback_data=f"adm|variants|{title_id}")],
        ]
    )
