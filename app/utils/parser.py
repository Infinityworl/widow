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

NOISE_PATTERNS = [
    r"\b(480p|720p|1080p|2160p|4k)\b",
    r"\b(10bit|8bit|hi10p)\b",
    r"\b(x264|x265|h264|h265|hevc|av1)\b",
    r"\b(web[ ._-]?dl|web[ ._-]?rip|bluray|blu[ ._-]?ray|brrip|bdrip|dvdrip|hdrip|hdcam|cam|remux)\b",
    r"\b(aac2?\.?(?:0)?|aac|ddp(?:5\.1|7\.1)?|dd(?:5\.1|7\.1)?|ac3|eac3|dts(?:[ ._-]?hd)?|truehd|atmos|opus|mp3|flac)\b",
    r"\b(6ch|2ch|5\.1|7\.1)\b",
    r"\b(psa|yts|ytsmx|rarbg|galaxyrg|evo|ettv|tgx|pahe|pahe\.in|yify|amzn|nf|dsnp|hmax|proper|repack|extended|uncut|multi|dubbed|dual[ ._-]?audio|sample|torrentgalaxy|www\.[^\s]+)\b",
    r"\b(mkv|mp4|avi)\b",
]


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


def _clean_title_candidate(candidate: str) -> str:
    candidate = re.sub(r"\.[A-Za-z0-9]{2,4}$", "", candidate)
    candidate = re.sub(r"\[[^\]]*\]", " ", candidate)
    candidate = re.sub(r"\([^)]*\)", " ", candidate)
    candidate = re.sub(r"[._]+", " ", candidate)
    candidate = re.sub(r"\bS\d{1,2}E\d{1,3}\b", " ", candidate, flags=re.I)
    candidate = re.sub(r"\bSeason\s*\d{1,2}\b", " ", candidate, flags=re.I)
    candidate = re.sub(r"\bEpisode\s*\d{1,3}\b", " ", candidate, flags=re.I)
    candidate = re.sub(r"\b(19\d{2}|20\d{2}|21\d{2})\b", " ", candidate, flags=re.I)
    for pattern in NOISE_PATTERNS:
        candidate = re.sub(pattern, " ", candidate, flags=re.I)
    candidate = re.sub(r"\b\d{3,4}\s*mb\b", " ", candidate, flags=re.I)
    candidate = re.sub(r"\b\d+(?:\.\d+)?\s*gb\b", " ", candidate, flags=re.I)
    candidate = re.sub(r"\bpart\s*\d+\b", " ", candidate, flags=re.I)
    candidate = re.sub(r"\bvol\s*\d+\b", " ", candidate, flags=re.I)
    candidate = re.sub(r"\b(?:in|com|org|net)\b", " ", candidate, flags=re.I)
    candidate = re.sub(r"\s+", " ", candidate).strip(" -_.")
    return candidate


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
    candidate = _clean_title_candidate(candidate)
    return candidate or "Unknown Title"


def _guess_season_episode(text: str, file_name: str | None) -> tuple[Optional[int], Optional[int]]:
    joined = f"{text}\n{file_name or ''}"
    pair_match = re.search(r"\bS(\d{1,2})E(\d{1,3})\b", joined, flags=re.I)
    if pair_match:
        return int(pair_match.group(1)), int(pair_match.group(2))
    season_match = re.search(r"(?:season\s*[:\-]?\s*|\bS)(\d{1,2})\b", joined, flags=re.I)
    episode_match = re.search(r"(?:episode\s*[:\-]?\s*|\bE)(\d{1,3})\b", joined, flags=re.I)
    season = int(season_match.group(1)) if season_match else None
    episode = int(episode_match.group(1)) if episode_match else None
    return season, episode


def _extract_size_label(text: str) -> Optional[str]:
    mb = re.search(r"\b(\d{3,4})\s*MB\b", text, flags=re.I)
    if mb:
        return f"{mb.group(1)}MB"
    gb = re.search(r"\b(\d+(?:\.\d+)?)\s*GB\b", text, flags=re.I)
    if gb:
        return f"{gb.group(1)}GB"
    return None


def parse_channel_message(message: Message) -> Optional[ParsedMedia]:
    media = message.video or message.document
    if media is None:
        return None

    caption = message.caption or ""
    file_name = getattr(media, "file_name", None)
    combined_text = f"{caption}\n{file_name or ''}"
    parsed_lines = _parse_kv_lines(caption)

    title = _guess_title(caption, file_name)
    season, episode = _guess_season_episode(caption, file_name)
    media_type = parsed_lines.get("media_type", _guess_media_type(combined_text)).lower()
    year = int(parsed_lines["year"]) if parsed_lines.get("year", "").isdigit() else extract_year(combined_text)
    quality = parsed_lines.get("quality") or extract_quality(combined_text) or "720p"
    codec = parsed_lines.get("codec") or extract_codec(combined_text) or "x264"
    language = parsed_lines.get("language")
    size_label = parsed_lines.get("size_label") or _extract_size_label(combined_text)

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
