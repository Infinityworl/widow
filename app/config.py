from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional

from dotenv import load_dotenv

load_dotenv()


def _split_csv(value: str | None) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]



def _split_int_csv(value: str | None) -> List[int]:
    items: List[int] = []
    for raw in _split_csv(value):
        try:
            items.append(int(raw))
        except ValueError:
            continue
    return items


@dataclass(slots=True)
class Settings:
    api_id: int
    api_hash: str
    bot_token: str
    mongo_uri: str
    database_name: str = "telegram_media_bot"
    tmdb_api_key: Optional[str] = None
    tmdb_bearer_token: Optional[str] = None
    omdb_api_key: Optional[str] = None
    admins: List[int] = field(default_factory=list)
    source_channels: List[int] = field(default_factory=list)
    movie_source_channels: List[int] = field(default_factory=list)
    series_source_channels: List[int] = field(default_factory=list)
    user_group_ids: List[int] = field(default_factory=list)
    log_chat_id: Optional[int] = None
    series_info_channel_id: Optional[int] = None
    bot_username: Optional[str] = None
    max_search_results: int = 8
    result_page_size: int = 10
    browser_placeholder_photo_url: Optional[str] = None
    search_hub_photo_url: Optional[str] = None
    title_pick_photo_url: Optional[str] = None
    season_pick_photo_url: Optional[str] = None
    quality_pick_photo_url: Optional[str] = None
    codec_pick_photo_url: Optional[str] = None
    episode_pick_photo_url: Optional[str] = None
    title_pick_caption: str = "🎞 <b>{title}</b>\n\nName button එක tap කරලා next step එකට යන්න."
    season_pick_caption: str = "📺 <b>{title}</b>\n\nSeason එක තෝරන්න."
    quality_pick_caption: str = "📦 <b>{title}</b>\n\nQuality එක තෝරන්න."
    codec_pick_caption: str = "⚙️ <b>{title}</b>\n\nCodec + File Size button එක තෝරන්න."
    episode_pick_caption: str = "🎬 <b>{title}</b>\n\nEpisode එක තෝරන්න."
    download_ready_caption: str = "🍿 <b>{title}</b>\n\nDownload button එකෙන් inbox එකට file එක ගන්න."
    search_hub_caption_template: str = (
        "🔎 <b>{query}</b>\n\n"
        "🎬 Movies: <b>{movie_count}</b>    📺 TV Series: <b>{series_count}</b>\n"
        "🔒 මේ buttons වැඩ කරන්නේ search කරපු user ට විතරයි.\n"
        "{hint_line}"
    )
    movie_tab_button_text: str = "🎬 Movies ({movie_count})"
    series_tab_button_text: str = "📺 TV Series ({series_count})"
    no_results_button_text: str = "❌ No results"
    movie_title_button_text: str = "🎞 {title}{year_label}"
    series_title_button_text: str = "📺 {title}{year_label}"
    quality_button_text: str = "📦 {quality}"
    codec_size_button_text: str = "⚙️ {codec} • {size}"
    season_button_text: str = "🗂 Season {season}"
    episode_button_text: str = "🎬 E{episode_label}"
    prev_button_text: str = "⬅️ Prev"
    next_button_text: str = "Next ➡️"
    download_button_text: str = "⬇️ Download to Inbox"
    open_inbox_button_text: str = "📩 Open Bot Inbox"
    admin_manage_movies_button_text: str = "🎬 Manage Movies"
    admin_manage_series_button_text: str = "📺 Manage Series"
    admin_sync_series_button_text: str = "📥 Sync Series Post"
    admin_sync_movie_button_text: str = "📥 Sync Movie Post"
    admin_poster_tools_button_text: str = "🖼 Poster Tools"
    admin_edit_name_button_text: str = "🎞 Edit Name"
    admin_manage_variants_button_text: str = "🎚 Manage Quality / Codec"
    admin_delete_title_button_text: str = "🗑 Delete This Title"
    admin_back_home_button_text: str = "⬅️ Admin Home"
    admin_auto_refresh_poster_button_text: str = "♻️ Auto Refresh Poster"
    admin_remove_poster_button_text: str = "🧹 Remove Poster"
    admin_manual_poster_url_button_text: str = "🔗 Set Manual Poster URL"
    admin_back_button_text: str = "⬅️ Back"
    admin_confirm_delete_button_text: str = "✅ Yes, Delete"
    admin_cancel_button_text: str = "❌ Cancel"
    admin_change_quality_button_text: str = "📦 Change Quality"
    admin_change_codec_button_text: str = "⚙️ Change Codec"
    admin_delete_file_button_text: str = "🗑 Delete This File"


def get_settings() -> Settings:
    api_id = os.getenv("API_ID")
    api_hash = os.getenv("API_HASH")
    bot_token = os.getenv("BOT_TOKEN")
    mongo_uri = os.getenv("MONGO_URI")

    missing = [
        name
        for name, value in {
            "API_ID": api_id,
            "API_HASH": api_hash,
            "BOT_TOKEN": bot_token,
            "MONGO_URI": mongo_uri,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

    return Settings(
        api_id=int(api_id),
        api_hash=api_hash,
        bot_token=bot_token,
        mongo_uri=mongo_uri,
        database_name=os.getenv("DATABASE_NAME", "telegram_media_bot"),
        tmdb_api_key=os.getenv("TMDB_API_KEY"),
        tmdb_bearer_token=os.getenv("TMDB_BEARER_TOKEN"),
        omdb_api_key=os.getenv("OMDB_API_KEY"),
        admins=_split_int_csv(os.getenv("ADMINS")),
        source_channels=_split_int_csv(os.getenv("SOURCE_CHANNELS")),
        movie_source_channels=_split_int_csv(os.getenv("MOVIE_SOURCE_CHANNELS")),
        series_source_channels=_split_int_csv(os.getenv("SERIES_SOURCE_CHANNELS")),
        user_group_ids=_split_int_csv(os.getenv("USER_GROUP_IDS")),
        log_chat_id=int(os.getenv("LOG_CHAT_ID")) if os.getenv("LOG_CHAT_ID") else None,
        series_info_channel_id=int(os.getenv("SERIES_INFO_CHANNEL_ID")) if os.getenv("SERIES_INFO_CHANNEL_ID") else None,
        bot_username=os.getenv("BOT_USERNAME"),
        max_search_results=int(os.getenv("MAX_SEARCH_RESULTS", "8")),
        result_page_size=int(os.getenv("RESULT_PAGE_SIZE", "10")),
        browser_placeholder_photo_url=os.getenv("BROWSER_PLACEHOLDER_PHOTO_URL"),
        search_hub_photo_url=os.getenv("SEARCH_HUB_PHOTO_URL"),
        title_pick_photo_url=os.getenv("TITLE_PICK_PHOTO_URL"),
        season_pick_photo_url=os.getenv("SEASON_PICK_PHOTO_URL"),
        quality_pick_photo_url=os.getenv("QUALITY_PICK_PHOTO_URL"),
        codec_pick_photo_url=os.getenv("CODEC_PICK_PHOTO_URL"),
        episode_pick_photo_url=os.getenv("EPISODE_PICK_PHOTO_URL"),
        title_pick_caption=os.getenv("TITLE_PICK_CAPTION", "🎞 <b>{title}</b>\n\nName button එක tap කරලා next step එකට යන්න."),
        season_pick_caption=os.getenv("SEASON_PICK_CAPTION", "📺 <b>{title}</b>\n\nSeason එක තෝරන්න."),
        quality_pick_caption=os.getenv("QUALITY_PICK_CAPTION", "📦 <b>{title}</b>\n\nQuality එක තෝරන්න."),
        codec_pick_caption=os.getenv("CODEC_PICK_CAPTION", "⚙️ <b>{title}</b>\n\nCodec + File Size button එක තෝරන්න."),
        episode_pick_caption=os.getenv("EPISODE_PICK_CAPTION", "🎬 <b>{title}</b>\n\nEpisode එක තෝරන්න."),
        download_ready_caption=os.getenv("DOWNLOAD_READY_CAPTION", "🍿 <b>{title}</b>\n\nDownload button එකෙන් inbox එකට file එක ගන්න."),
        search_hub_caption_template=os.getenv("SEARCH_HUB_CAPTION_TEMPLATE", "🔎 <b>{query}</b>\n\n🎬 Movies: <b>{movie_count}</b>    📺 TV Series: <b>{series_count}</b>\n🔒 මේ buttons වැඩ කරන්නේ search කරපු user ට විතරයි.\n{hint_line}"),
        movie_tab_button_text=os.getenv("MOVIE_TAB_BUTTON_TEXT", "🎬 Movies ({movie_count})"),
        series_tab_button_text=os.getenv("SERIES_TAB_BUTTON_TEXT", "📺 TV Series ({series_count})"),
        no_results_button_text=os.getenv("NO_RESULTS_BUTTON_TEXT", "❌ No results"),
        movie_title_button_text=os.getenv("MOVIE_TITLE_BUTTON_TEXT", "🎞 {title}{year_label}"),
        series_title_button_text=os.getenv("SERIES_TITLE_BUTTON_TEXT", "📺 {title}{year_label}"),
        quality_button_text=os.getenv("QUALITY_BUTTON_TEXT", "📦 {quality}"),
        codec_size_button_text=os.getenv("CODEC_SIZE_BUTTON_TEXT", "⚙️ {codec} • {size}"),
        season_button_text=os.getenv("SEASON_BUTTON_TEXT", "🗂 Season {season}"),
        episode_button_text=os.getenv("EPISODE_BUTTON_TEXT", "🎬 E{episode_label}"),
        prev_button_text=os.getenv("PREV_BUTTON_TEXT", "⬅️ Prev"),
        next_button_text=os.getenv("NEXT_BUTTON_TEXT", "Next ➡️"),
        download_button_text=os.getenv("DOWNLOAD_BUTTON_TEXT", "⬇️ Download to Inbox"),
        open_inbox_button_text=os.getenv("OPEN_INBOX_BUTTON_TEXT", "📩 Open Bot Inbox"),
        admin_manage_movies_button_text=os.getenv("ADMIN_MANAGE_MOVIES_BUTTON_TEXT", "🎬 Manage Movies"),
        admin_manage_series_button_text=os.getenv("ADMIN_MANAGE_SERIES_BUTTON_TEXT", "📺 Manage Series"),
        admin_sync_series_button_text=os.getenv("ADMIN_SYNC_SERIES_BUTTON_TEXT", "📥 Sync Series Post"),
        admin_sync_movie_button_text=os.getenv("ADMIN_SYNC_MOVIE_BUTTON_TEXT", "📥 Sync Movie Post"),
        admin_poster_tools_button_text=os.getenv("ADMIN_POSTER_TOOLS_BUTTON_TEXT", "🖼 Poster Tools"),
        admin_edit_name_button_text=os.getenv("ADMIN_EDIT_NAME_BUTTON_TEXT", "🎞 Edit Name"),
        admin_manage_variants_button_text=os.getenv("ADMIN_MANAGE_VARIANTS_BUTTON_TEXT", "🎚 Manage Quality / Codec"),
        admin_delete_title_button_text=os.getenv("ADMIN_DELETE_TITLE_BUTTON_TEXT", "🗑 Delete This Title"),
        admin_back_home_button_text=os.getenv("ADMIN_BACK_HOME_BUTTON_TEXT", "⬅️ Admin Home"),
        admin_auto_refresh_poster_button_text=os.getenv("ADMIN_AUTO_REFRESH_POSTER_BUTTON_TEXT", "♻️ Auto Refresh Poster"),
        admin_remove_poster_button_text=os.getenv("ADMIN_REMOVE_POSTER_BUTTON_TEXT", "🧹 Remove Poster"),
        admin_manual_poster_url_button_text=os.getenv("ADMIN_MANUAL_POSTER_URL_BUTTON_TEXT", "🔗 Set Manual Poster URL"),
        admin_back_button_text=os.getenv("ADMIN_BACK_BUTTON_TEXT", "⬅️ Back"),
        admin_confirm_delete_button_text=os.getenv("ADMIN_CONFIRM_DELETE_BUTTON_TEXT", "✅ Yes, Delete"),
        admin_cancel_button_text=os.getenv("ADMIN_CANCEL_BUTTON_TEXT", "❌ Cancel"),
        admin_change_quality_button_text=os.getenv("ADMIN_CHANGE_QUALITY_BUTTON_TEXT", "📦 Change Quality"),
        admin_change_codec_button_text=os.getenv("ADMIN_CHANGE_CODEC_BUTTON_TEXT", "⚙️ Change Codec"),
        admin_delete_file_button_text=os.getenv("ADMIN_DELETE_FILE_BUTTON_TEXT", "🗑 Delete This File"),
    )
