from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING

from app.config import Settings
from app.utils.text import normalize_title


class Database:
    def __init__(self, settings: Settings) -> None:
        self.client = AsyncIOMotorClient(settings.mongo_uri)
        self.db: AsyncIOMotorDatabase = self.client[settings.database_name]
        self.titles = self.db["titles"]
        self.media_files = self.db["media_files"]

    async def ensure_indexes(self) -> None:
        await self.titles.create_index([("normalized_title", ASCENDING), ("media_type", ASCENDING), ("year", ASCENDING)])
        await self.titles.create_index([("aliases", ASCENDING)])
        await self.titles.create_index([("tmdb_id", ASCENDING), ("media_type", ASCENDING)], sparse=True)
        await self.titles.create_index([("imdb_id", ASCENDING), ("media_type", ASCENDING)], sparse=True)
        await self.titles.create_index([("updated_at", DESCENDING)])
        await self.titles.create_index(
            [("title", "text"), ("aliases", "text"), ("overview", "text")],
            default_language="english",
            name="title_text_idx",
        )
        await self.media_files.create_index([("title_id", ASCENDING), ("media_type", ASCENDING)])
        await self.media_files.create_index([("source_chat_id", ASCENDING), ("source_message_id", ASCENDING)], unique=True)
        await self.media_files.create_index([("file_unique_id", ASCENDING)], sparse=True)
        await self.media_files.create_index([("season", ASCENDING), ("episode", ASCENDING)])
        await self.media_files.create_index([("quality", ASCENDING), ("codec", ASCENDING)])
        await self.media_files.create_index([("created_at", DESCENDING)])

    async def find_title_candidate(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        media_type = payload["media_type"]
        if payload.get("tmdb_id"):
            row = await self.titles.find_one({"tmdb_id": payload["tmdb_id"], "media_type": media_type})
            if row:
                return row
        if payload.get("imdb_id"):
            row = await self.titles.find_one({"imdb_id": payload["imdb_id"], "media_type": media_type})
            if row:
                return row

        normalized_title = payload["normalized_title"]
        year = payload.get("year")
        alias_values = list({normalized_title, *(normalize_title(a) for a in payload.get("aliases", []) if a)})
        or_filters = [{"normalized_title": normalized_title}]
        for alias in alias_values:
            or_filters.append({"aliases": alias})
        base: Dict[str, Any] = {"media_type": media_type, "$or": or_filters}
        if year:
            base["year"] = year
        row = await self.titles.find_one(base)
        if row:
            return row
        if year:
            row = await self.titles.find_one({"media_type": media_type, "$or": or_filters})
            if row:
                return row
        return None

    async def upsert_title(self, payload: Dict[str, Any]) -> ObjectId:
        now = datetime.now(timezone.utc)
        payload["updated_at"] = now
        payload.setdefault("created_at", now)
        payload["aliases"] = [normalize_title(a) for a in payload.get("aliases", []) if a]
        payload["aliases"] = sorted({a for a in payload["aliases"] if a})

        existing = await self.find_title_candidate(payload)
        if existing:
            merged_aliases = sorted({*(existing.get("aliases") or []), *payload.get("aliases", [])})
            updates = dict(payload)
            updates["aliases"] = merged_aliases
            if not updates.get("poster_url") and existing.get("poster_url"):
                updates["poster_url"] = existing.get("poster_url")
                updates["poster_source"] = existing.get("poster_source")
            if not updates.get("overview") and existing.get("overview"):
                updates["overview"] = existing.get("overview")
            if not updates.get("tmdb_id") and existing.get("tmdb_id"):
                updates["tmdb_id"] = existing.get("tmdb_id")
            if not updates.get("imdb_id") and existing.get("imdb_id"):
                updates["imdb_id"] = existing.get("imdb_id")
            if not updates.get("year") and existing.get("year"):
                updates["year"] = existing.get("year")
            await self.titles.update_one({"_id": existing["_id"]}, {"$set": updates})
            return existing["_id"]

        inserted = await self.titles.insert_one(payload)
        return inserted.inserted_id

    async def upsert_media_file(self, payload: Dict[str, Any]) -> ObjectId:
        now = datetime.now(timezone.utc)
        payload["updated_at"] = now
        payload.setdefault("created_at", now)
        finder = {"source_chat_id": payload["source_chat_id"], "source_message_id": payload["source_message_id"]}
        existing = await self.media_files.find_one(finder, {"_id": 1})
        if existing:
            await self.media_files.update_one({"_id": existing["_id"]}, {"$set": payload})
            return existing["_id"]
        inserted = await self.media_files.insert_one(payload)
        return inserted.inserted_id

    async def get_title(self, title_id: str | ObjectId) -> Optional[Dict[str, Any]]:
        object_id = ObjectId(title_id) if isinstance(title_id, str) else title_id
        return await self.titles.find_one({"_id": object_id})

    async def search_titles(self, query: str, media_type: Optional[str] = None, limit: int = 8) -> List[Dict[str, Any]]:
        query = query.strip()
        if not query:
            return []
        normalized = query.lower().strip()
        tokens = [token for token in normalized.replace("-", " ").split() if token]
        regex = {"$regex": normalized, "$options": "i"}
        criteria: Dict[str, Any] = {
            "$or": [
                {"normalized_title": regex},
                {"aliases": regex},
                {"title": {"$regex": query, "$options": "i"}},
            ]
        }
        if media_type:
            criteria["media_type"] = media_type
        docs = await self.titles.find(criteria).sort("updated_at", DESCENDING).to_list(length=50)
        if not docs:
            text_filter: Dict[str, Any] = {"$text": {"$search": query}}
            if media_type:
                text_filter["media_type"] = media_type
            docs = await self.titles.find(text_filter, {"score": {"$meta": "textScore"}}).to_list(length=50)
        scored: List[tuple[float, Dict[str, Any]]] = []
        for doc in docs:
            score = 0.0
            norm_title = doc.get("normalized_title", "")
            aliases = [str(a).lower() for a in doc.get("aliases", [])]
            if normalized == norm_title:
                score += 120
            if norm_title.startswith(normalized):
                score += 60
            if normalized in norm_title:
                score += 40
            for alias in aliases:
                if normalized == alias:
                    score += 100
                if alias.startswith(normalized):
                    score += 50
                if normalized in alias:
                    score += 30
            for token in tokens:
                if token in norm_title:
                    score += 10
                if any(token in alias for alias in aliases):
                    score += 8
            if doc.get("year") and str(doc["year"]) in query:
                score += 20
            if doc.get("score"):
                score += float(doc.get("score", 0)) * 5
            scored.append((score, doc))
        scored.sort(key=lambda item: (item[0], item[1].get("updated_at")), reverse=True)
        return [doc for _, doc in scored[:limit]]

    async def get_available_qualities(self, title_id: str, season: Optional[int] = None, episode: Optional[int] = None) -> List[str]:
        match: Dict[str, Any] = {"title_id": ObjectId(title_id)}
        if season is not None:
            match["season"] = season
        if episode is not None:
            match["episode"] = episode
        pipeline = [{"$match": match}, {"$group": {"_id": "$quality"}}, {"$sort": {"_id": 1}}]
        rows = await self.media_files.aggregate(pipeline).to_list(length=50)
        return [row["_id"] for row in rows if row.get("_id")]

    async def list_movie_variants(self, title_id: str, quality: str, limit: int = 100) -> List[Dict[str, Any]]:
        rows = await self.media_files.find({"title_id": ObjectId(title_id), "quality": quality}).sort("created_at", DESCENDING).to_list(length=limit)
        deduped: list[Dict[str, Any]] = []
        seen: set[tuple[Any, ...]] = set()
        for row in rows:
            key = (row.get("codec"), row.get("size_label"), row.get("file_unique_id"), row.get("telegram_file_id"))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(row)
        return deduped

    async def get_available_seasons(self, title_id: str) -> List[int]:
        pipeline = [{"$match": {"title_id": ObjectId(title_id), "season": {"$ne": None}}}, {"$group": {"_id": "$season"}}, {"$sort": {"_id": 1}}]
        rows = await self.media_files.aggregate(pipeline).to_list(length=100)
        return [int(row["_id"]) for row in rows if row.get("_id") is not None]

    async def get_available_episode_numbers(self, title_id: str, season: int, skip: int = 0, limit: int = 24) -> List[int]:
        pipeline = [
            {"$match": {"title_id": ObjectId(title_id), "season": season, "episode": {"$ne": None}}},
            {"$group": {"_id": "$episode"}},
            {"$sort": {"_id": 1}},
            {"$skip": skip},
            {"$limit": limit},
        ]
        rows = await self.media_files.aggregate(pipeline).to_list(length=limit)
        return [int(row["_id"]) for row in rows if row.get("_id") is not None]

    async def count_available_episode_numbers(self, title_id: str, season: int) -> int:
        pipeline = [{"$match": {"title_id": ObjectId(title_id), "season": season, "episode": {"$ne": None}}}, {"$group": {"_id": "$episode"}}, {"$count": "count"}]
        rows = await self.media_files.aggregate(pipeline).to_list(length=1)
        return int(rows[0]["count"]) if rows else 0

    async def get_episode_qualities(self, title_id: str, season: int, episode: int) -> List[str]:
        pipeline = [{"$match": {"title_id": ObjectId(title_id), "season": season, "episode": episode}}, {"$group": {"_id": "$quality"}}, {"$sort": {"_id": 1}}]
        rows = await self.media_files.aggregate(pipeline).to_list(length=20)
        return [row["_id"] for row in rows if row.get("_id")]

    async def list_episode_variants(self, title_id: str, season: int, episode: int, quality: str, limit: int = 50) -> List[Dict[str, Any]]:
        rows = await self.media_files.find({"title_id": ObjectId(title_id), "season": season, "episode": episode, "quality": quality}).sort("created_at", DESCENDING).to_list(length=limit)
        deduped: list[Dict[str, Any]] = []
        seen: set[tuple[Any, ...]] = set()
        for row in rows:
            key = (row.get("codec"), row.get("size_label"), row.get("file_unique_id"), row.get("telegram_file_id"))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(row)
        return deduped

    async def get_media_file(self, media_file_id: str | ObjectId) -> Optional[Dict[str, Any]]:
        object_id = ObjectId(media_file_id) if isinstance(media_file_id, str) else media_file_id
        return await self.media_files.find_one({"_id": object_id})

    async def list_title_variants(self, title_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        rows = await self.media_files.find({"title_id": ObjectId(title_id)}).sort("created_at", DESCENDING).to_list(length=limit)
        deduped: list[Dict[str, Any]] = []
        seen: set[tuple[Any, ...]] = set()
        for row in rows:
            key = (row.get("season"), row.get("episode"), row.get("quality"), row.get("codec"), row.get("size_label"))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(row)
        return deduped

    async def update_title_fields(self, title_id: str, updates: Dict[str, Any]) -> None:
        updates["updated_at"] = datetime.now(timezone.utc)
        if "title" in updates and updates["title"]:
            updates.setdefault("normalized_title", normalize_title(str(updates["title"])))
        await self.titles.update_one({"_id": ObjectId(title_id)}, {"$set": updates})

    async def update_media_file_fields(self, media_file_id: str, updates: Dict[str, Any]) -> None:
        updates["updated_at"] = datetime.now(timezone.utc)
        await self.media_files.update_one({"_id": ObjectId(media_file_id)}, {"$set": updates})

    async def count_title_files(self, title_id: str) -> int:
        return await self.media_files.count_documents({"title_id": ObjectId(title_id)})

    async def delete_media_file(self, media_file_id: str) -> None:
        await self.media_files.delete_one({"_id": ObjectId(media_file_id)})

    async def delete_title_and_media(self, title_id: str) -> None:
        object_id = ObjectId(title_id)
        await self.media_files.delete_many({"title_id": object_id})
        await self.titles.delete_one({"_id": object_id})

    async def reassign_media_file(self, media_file_id: str, new_title_id: str) -> None:
        await self.update_media_file_fields(media_file_id, {"title_id": ObjectId(new_title_id)})
