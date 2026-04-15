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
    )
