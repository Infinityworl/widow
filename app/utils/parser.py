from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from pyrogram.types import Message

from app.utils.text import extract_codec, extract_quality, extract_year, normalize_title


@dataclass(slots=True)
class ParsedMedia:
    media_type: str
    title: str
    normalized_title: str
    year: Optional[int]
    quality: str
    codec: str
    season: Optional[int]
    episode: Optional[int]
    language: Optional[str]
    size_label: Optional[str]
    file_name: Optional[str]
    caption: str
    source_chat_id: int
    source_message_id: int
    file_id: str
    file_unique_id: Optional[str]
    media_kind: str


KEY_ALIASES = {
    "type": "media_type",
    "category": "media_type",
    "title": "title",
    "name": "title",
    "movie": "title",
    "series": "title",
    "show": "title",
    "year": "year",
    "quality": "quality",
    "codec": "codec",
    "season": "season",
    "episode": "episode",
    "lang": "language",
    "language": "language",
    "size": "size_label",
}



def _parse_kv_lines(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        clean = line.strip().lstrip("#")
        if not clean:
            continue
        if ":" in clean:
            key, value = clean.split(":", 1)
        elif "-" in clean and len(clean.split("-", 1)[0]) < 15:
            key, value = clean.split("-", 1)
        else:
            continue
        key = key.strip().lower().replace(" ", "")
        value = value.strip()
        mapped = KEY_ALIASES.get(key)
        if mapped and value:
            result[mapped] = value
    return result



def _guess_media_type(text: str) -> str:
    lowered = text.lower()
    if "#series" in lowered or "type: series" in lowered or re.search(r"\bs\d{1,2}e\d{1,2}\b", lowered):
        return "series"
    return "movie"



def _guess_title(text: str, file_name: str | None) -> str:
    parsed = _parse_kv_lines(text)
    if parsed.get("title"):
        return parsed["title"].strip()

    first_meaningful = None
    for line in text.splitlines():
        clean = line.strip().lstrip("#")
        if not clean:
            continue
        if ":" in clean or clean.lower() in {"movie", "series"}:
            continue
        if len(clean) > 2:
            first_meaningful = clean
            break

    candidate = first_meaningful or (file_name or "")
    candidate = re.sub(r"\b(19\d{2}|20\d{2}|21\d{2})\b", "", candidate, flags=re.I)
    candidate = re.sub(r"\b(480p|720p|1080p|2160p|4k|x264|x265|h264|h265|hevc|av1)\b", "", candidate, flags=re.I)
    candidate = re.sub(r"\bS\d{1,2}E\d{1,2}\b", "", candidate, flags=re.I)
    candidate = re.sub(r"[._-]+", " ", candidate)
    candidate = re.sub(r"\s+", " ", candidate).strip(" -_.")
    return candidate or "Unknown Title"



def _guess_season_episode(text: str, file_name: str | None) -> tuple[Optional[int], Optional[int]]:
    joined = f"{text}\n{file_name or ''}"

    season_match = re.search(r"(?:season\s*[:\-]?\s*|\bS)(\d{1,2})\b", joined, flags=re.I)
    episode_match = re.search(r"(?:episode\s*[:\-]?\s*|\bE)(\d{1,3})\b", joined, flags=re.I)
    pair_match = re.search(r"\bS(\d{1,2})E(\d{1,3})\b", joined, flags=re.I)

    if pair_match:
        return int(pair_match.group(1)), int(pair_match.group(2))

    season = int(season_match.group(1)) if season_match else None
    episode = int(episode_match.group(1)) if episode_match else None
    return season, episode



def parse_channel_message(message: Message) -> Optional[ParsedMedia]:
    media = message.video or message.document
    if media is None:
        return None

    caption = message.caption or ""
    file_name = getattr(media, "file_name", None)
    parsed_lines = _parse_kv_lines(caption)

    title = _guess_title(caption, file_name)
    season, episode = _guess_season_episode(caption, file_name)
    media_type = parsed_lines.get("media_type", _guess_media_type(f"{caption}\n{file_name or ''}")).lower()
    year = int(parsed_lines["year"]) if parsed_lines.get("year", "").isdigit() else extract_year(f"{caption}\n{file_name or ''}")
    quality = parsed_lines.get("quality") or extract_quality(f"{caption}\n{file_name or ''}") or "720p"
    codec = parsed_lines.get("codec") or extract_codec(f"{caption}\n{file_name or ''}") or "x264"
    language = parsed_lines.get("language")
    size_label = parsed_lines.get("size_label")

    source_chat_id = getattr(getattr(message, "forward_from_chat", None), "id", None) or message.chat.id
    source_message_id = getattr(message, "forward_from_message_id", None) or message.id

    return ParsedMedia(
        media_type="series" if media_type == "series" else "movie",
        title=title,
        normalized_title=normalize_title(title),
        year=year,
        quality=quality,
        codec=codec,
        season=season,
        episode=episode,
        language=language,
        size_label=size_label,
        file_name=file_name,
        caption=caption,
        source_chat_id=source_chat_id,
        source_message_id=source_message_id,
        file_id=media.file_id,
        file_unique_id=getattr(media, "file_unique_id", None),
        media_kind="video" if message.video else "document",
    )
