from __future__ import annotations

from pyrogram import Client

from app.config import Settings
from app.db import Database
from app.services.catalog import CatalogService
from app.services.tmdb import MetadataService


class MovieBot(Client):
    def __init__(self, settings: Settings) -> None:
        super().__init__(
            name="movie_filter_bot",
            api_id=settings.api_id,
            api_hash=settings.api_hash,
            bot_token=settings.bot_token,
            workdir=".",
            plugins={"root": "app.handlers"},
        )
        self.settings = settings
        self.db_service = Database(settings)
        self.metadata_service = MetadataService(settings)
        self.catalog_service = CatalogService(self.db_service, self.metadata_service)
        self.admin_states: dict[int, dict] = {}
        self.search_sessions: dict[tuple[int, int], dict] = {}
