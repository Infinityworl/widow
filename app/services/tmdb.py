from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from app.config import Settings
from app.utils.text import best_similarity, extract_year


class MetadataService:
    TMDB_BASE_URL = "https://api.themoviedb.org/3"
    TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"
    OMDB_BASE_URL = "https://www.omdbapi.com/"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.tmdb_enabled = bool(settings.tmdb_api_key or settings.tmdb_bearer_token)
        self.omdb_enabled = bool(settings.omdb_api_key)

    def _tmdb_headers(self) -> dict[str, str]:
        headers = {"accept": "application/json"}
        if self.settings.tmdb_bearer_token:
            headers["Authorization"] = f"Bearer {self.settings.tmdb_bearer_token}"
        return headers

    def _tmdb_params(self) -> dict[str, str]:
        return {"api_key": self.settings.tmdb_api_key} if self.settings.tmdb_api_key else {}

    async def _search_tmdb(self, title: str, media_type: str, year: Optional[int]) -> Optional[Dict[str, Any]]:
        if not self.tmdb_enabled:
            return None

        endpoint = "/search/movie" if media_type == "movie" else "/search/tv"
        params = {**self._tmdb_params(), "query": title, "include_adult": "false", "language": "en-US"}
        if year and media_type == "movie":
            params["year"] = str(year)
        if year and media_type == "series":
            params["first_air_date_year"] = str(year)

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(f"{self.TMDB_BASE_URL}{endpoint}", params=params, headers=self._tmdb_headers())
            response.raise_for_status()
            data = response.json()

        results = data.get("results", [])
        if not results:
            return None

        best_item: Optional[Dict[str, Any]] = None
        best_score = -1.0
        for item in results[:10]:
            names = [item.get("title") or item.get("name") or ""]
            if item.get("original_title"):
                names.append(item["original_title"])
            if item.get("original_name"):
                names.append(item["original_name"])
            score = best_similarity(title, names)
            date_field = item.get("release_date") or item.get("first_air_date") or ""
            item_year = extract_year(date_field)
            if year and item_year == year:
                score += 0.30
            if item.get("poster_path"):
                score += 0.10
            if score > best_score:
                best_score = score
                best_item = item

        if not best_item:
            return None

        poster_url = None
        if best_item.get("poster_path"):
            poster_url = f"{self.TMDB_IMAGE_BASE}{best_item['poster_path']}"

        return {
            "source": "tmdb",
            "tmdb_id": best_item.get("id"),
            "title": best_item.get("title") or best_item.get("name"),
            "original_title": best_item.get("original_title") or best_item.get("original_name"),
            "overview": best_item.get("overview"),
            "poster_url": poster_url,
            "vote_average": best_item.get("vote_average"),
            "popularity": best_item.get("popularity"),
            "year": year or extract_year(best_item.get("release_date") or best_item.get("first_air_date") or ""),
        }

    async def _search_omdb(self, title: str, media_type: str, year: Optional[int]) -> Optional[Dict[str, Any]]:
        if not self.omdb_enabled:
            return None

        params = {
            "apikey": self.settings.omdb_api_key,
            "t": title,
            "type": "series" if media_type == "series" else "movie",
            "plot": "short",
        }
        if year:
            params["y"] = str(year)

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(self.OMDB_BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

        if data.get("Response") != "True":
            return None

        poster_url = data.get("Poster")
        if poster_url == "N/A":
            poster_url = None

        imdb_rating: Optional[float] = None
        try:
            imdb_rating = float(data["imdbRating"])
        except (KeyError, TypeError, ValueError):
            imdb_rating = None

        omdb_year = extract_year(str(data.get("Year") or ""))

        return {
            "source": "omdb",
            "imdb_id": data.get("imdbID"),
            "title": data.get("Title"),
            "original_title": data.get("Title"),
            "overview": data.get("Plot") if data.get("Plot") != "N/A" else None,
            "poster_url": poster_url,
            "vote_average": imdb_rating,
            "year": year or omdb_year,
        }

    async def search(self, title: str, media_type: str, year: Optional[int] = None) -> Optional[Dict[str, Any]]:
        tmdb_data = await self._search_tmdb(title, media_type, year)
        omdb_data = await self._search_omdb(title, media_type, year)

        if not tmdb_data and not omdb_data:
            return None

        if tmdb_data and omdb_data:
            combined = dict(tmdb_data)
            if omdb_data.get("poster_url") and not combined.get("poster_url"):
                combined["poster_url"] = omdb_data["poster_url"]
                combined["poster_source"] = "omdb"
            else:
                combined["poster_source"] = "tmdb" if combined.get("poster_url") else None
            combined["imdb_id"] = omdb_data.get("imdb_id")
            if not combined.get("overview"):
                combined["overview"] = omdb_data.get("overview")
            if not combined.get("title"):
                combined["title"] = omdb_data.get("title")
            if not combined.get("original_title"):
                combined["original_title"] = omdb_data.get("original_title")
            if not combined.get("vote_average"):
                combined["vote_average"] = omdb_data.get("vote_average")
            if not combined.get("year"):
                combined["year"] = omdb_data.get("year")
            return combined

        single = tmdb_data or omdb_data or {}
        if single.get("source") == "tmdb" and single.get("poster_url"):
            single["poster_source"] = "tmdb"
        elif single.get("source") == "omdb" and single.get("poster_url"):
            single["poster_source"] = "omdb"
        return single
