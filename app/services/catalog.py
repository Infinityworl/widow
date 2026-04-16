from __future__ import annotations

from typing import Any, Dict, Optional

from bson import ObjectId

from app.db import Database
from app.services.tmdb import MetadataService
from app.utils.parser import ParsedMedia
from app.utils.text import normalize_title


class CatalogService:
    def __init__(self, db: Database, metadata: MetadataService) -> None:
        self.db = db
        self.metadata = metadata

    async def ingest_parsed_media(self, parsed: ParsedMedia, force_media_type: Optional[str] = None) -> Dict[str, Any]:
        media_type = force_media_type or parsed.media_type
        metadata = await self.metadata.search(parsed.title, media_type, parsed.year)
        canonical_title = metadata.get("title") if metadata and metadata.get("title") else parsed.title
        aliases = {parsed.title, canonical_title}
        if metadata and metadata.get("original_title"):
            aliases.add(metadata["original_title"])

        title_doc = {
            "media_type": media_type,
            "title": canonical_title,
            "normalized_title": normalize_title(canonical_title),
            "aliases": list(aliases),
            "year": metadata.get("year") if metadata else parsed.year,
            "tmdb_id": metadata.get("tmdb_id") if metadata else None,
            "imdb_id": metadata.get("imdb_id") if metadata else None,
            "overview": metadata.get("overview") if metadata else None,
            "poster_url": metadata.get("poster_url") if metadata else None,
            "poster_source": metadata.get("poster_source") if metadata else None,
            "vote_average": metadata.get("vote_average") if metadata else None,
        }
        title_id = await self.db.upsert_title(title_doc)
        media_doc = {
            "title_id": title_id,
            "media_type": media_type,
            "season": parsed.season,
            "episode": parsed.episode,
            "quality": parsed.quality,
            "codec": parsed.codec,
            "language": parsed.language,
            "size_label": parsed.size_label,
            "file_name": parsed.file_name,
            "caption": parsed.caption,
            "source_chat_id": parsed.source_chat_id,
            "source_message_id": parsed.source_message_id,
            "telegram_file_id": parsed.file_id,
            "file_unique_id": parsed.file_unique_id,
            "media_kind": parsed.media_kind,
        }
        media_file_id = await self.db.upsert_media_file(media_doc)
        title = await self.db.get_title(title_id)
        return {"title_id": str(title_id), "media_file_id": str(media_file_id), "title": title}

    async def get_title_details(self, title_id: str) -> Optional[Dict[str, Any]]:
        return await self.db.get_title(title_id)

    async def get_media_file_by_id(self, media_file_id: str) -> Optional[Dict[str, Any]]:
        return await self.db.get_media_file(ObjectId(media_file_id))
