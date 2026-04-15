from __future__ import annotations

import html
import re
import unicodedata
from difflib import SequenceMatcher
from typing import Iterable, Optional

QUALITY_ORDER = ["480p", "720p", "1080p", "2160p", "4k"]
KNOWN_CODECS = ["x264", "x265", "h264", "h265", "hevc", "av1"]


def slugify(value: str) -> str:
    value = normalize_title(value)
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")



def normalize_title(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = value.lower()
    value = re.sub(r"[\[](){}]", " ", value)
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()



def best_similarity(query: str, candidates: Iterable[str]) -> float:
    query_norm = normalize_title(query)
    return max((SequenceMatcher(None, query_norm, normalize_title(item)).ratio() for item in candidates), default=0.0)



def extract_year(text: str) -> Optional[int]:
    match = re.search(r"\b(19\d{2}|20\d{2}|21\d{2})\b", text)
    return int(match.group(1)) if match else None



def extract_quality(text: str) -> Optional[str]:
    lowered = text.lower()
    if "2160p" in lowered:
        return "2160p"
    if re.search(r"\b4k\b", lowered):
        return "4k"
    if "1080p" in lowered:
        return "1080p"
    if "720p" in lowered:
        return "720p"
    if "480p" in lowered:
        return "480p"
    return None



def extract_codec(text: str) -> Optional[str]:
    lowered = text.lower()
    for codec in KNOWN_CODECS:
        if codec in lowered:
            return codec.upper() if codec in {"hevc", "av1"} else codec
    return None



def sort_qualities(qualities: Iterable[str]) -> list[str]:
    def sort_key(item: str) -> tuple[int, str]:
        lowered = item.lower()
        try:
            index = QUALITY_ORDER.index(lowered)
        except ValueError:
            index = len(QUALITY_ORDER)
        return index, lowered

    return sorted({quality for quality in qualities if quality}, key=sort_key)



def media_type_label(media_type: str) -> str:
    return "TV Series" if media_type == "series" else "Movie"



def _apply_template(template: str, **values: object) -> str:
    safe_values = {key: ("-" if value in {None, ""} else str(value)) for key, value in values.items()}
    try:
        return template.format(**safe_values)
    except Exception:
        return template



def build_search_hub_caption(query: str, *, movie_count: int = 0, series_count: int = 0, active_type: str | None = None) -> str:
    lines = [f"🔎 <b>{html.escape(query)}</b>"]
    lines.append("")
    lines.append(f"🎬 Movies: <b>{movie_count}</b>    📺 TV Series: <b>{series_count}</b>")
    lines.append("🔒 මේ buttons වැඩ කරන්නේ search කරපු user ට විතරයි.")
    if active_type == "series":
        lines.append("📺 TV Series button එක ඔබලා name button එකක් තෝරන්න.")
    elif active_type == "movie":
        lines.append("🎬 Movies button එක ඔබලා movie name button එකක් තෝරන්න.")
    else:
        lines.append("🎛 පහළ buttons වලින් Movies හරි TV Series හරි තෝරන්න.")
    return "\n".join(lines)



def build_stage_caption(
    settings,
    title: dict,
    *,
    stage: str,
    season: int | None = None,
    quality: str | None = None,
    codec: str | None = None,
    size_label: str | None = None,
    episode: int | None = None,
) -> str:
    title_text = title.get("title", "Unknown Title")
    year = title.get("year")

    if stage == "title":
        template = settings.title_pick_caption
    elif stage == "season":
        template = settings.season_pick_caption
    elif stage == "quality":
        template = settings.quality_pick_caption
    elif stage == "codec":
        template = settings.codec_pick_caption
    elif stage == "episode":
        template = settings.episode_pick_caption
    else:
        template = settings.download_ready_caption

    lines = [
        _apply_template(
            template,
            title=title_text,
            year=year,
            media_type=media_type_label(title.get("media_type", "movie")),
            season=season,
            quality=quality,
            codec=codec,
            size=size_label,
            episode=episode,
        )
    ]

    if stage != "download":
        lines.append("")
        lines.append("🔒 මේ buttons වැඩ කරන්නේ search කරපු user ට විතරයි.")
        return "\n".join(lines)

    meta_parts: list[str] = []
    if year:
        meta_parts.append(str(year))
    meta_parts.append(media_type_label(title.get("media_type", "movie")))
    if title.get("vote_average"):
        try:
            meta_parts.append(f"⭐ {float(title['vote_average']):.1f}")
        except (TypeError, ValueError):
            pass
    if meta_parts:
        lines.append("")
        lines.append(" • ".join(meta_parts))

    detail_parts: list[str] = []
    if season is not None:
        detail_parts.append(f"Season {season}")
    if episode is not None:
        detail_parts.append(f"Episode {episode}")
    if quality:
        detail_parts.append(quality)
    if codec:
        detail_parts.append(codec)
    if size_label:
        detail_parts.append(size_label)
    if detail_parts:
        lines.append("🧩 " + " • ".join(detail_parts))

    overview = (title.get("overview") or "").strip()
    if overview:
        lines.append("")
        lines.append(html.escape(overview[:500] + ("..." if len(overview) > 500 else "")))

    lines.append("")
    lines.append("⬇️ Download button එක ඔබලා file එක bot inbox එකට ගන්න.")
    lines.append("🔒 මේ buttons වැඩ කරන්නේ search කරපු user ට විතරයි.")
    return "\n".join(lines)



def build_inbox_intro_caption(
    title: dict,
    *,
    season: int | None = None,
    episode: int | None = None,
    quality: str | None = None,
    codec: str | None = None,
    size_label: str | None = None,
) -> str:
    lines = [f"📩 <b>{html.escape(title.get('title', 'Unknown Title'))}</b>"]
    meta: list[str] = []
    if title.get("year"):
        meta.append(str(title["year"]))
    meta.append(media_type_label(title.get("media_type", "movie")))
    lines.append(" • ".join(meta))

    detail_parts: list[str] = []
    if season is not None:
        detail_parts.append(f"Season {season}")
    if episode is not None:
        detail_parts.append(f"Episode {episode}")
    if quality:
        detail_parts.append(quality)
    if codec:
        detail_parts.append(codec)
    if size_label:
        detail_parts.append(size_label)
    if detail_parts:
        lines.append("🧩 " + " • ".join(detail_parts))

    lines.append("")
    lines.append("✨ ඔයා තෝරපු file එක මේ inbox එකට ආවා.")
    lines.append("⬇️ ඊළඟ message එකේ තියෙන file එක download කරගන්න.")
    lines.append("🔁 ආයෙ group එකට යන්න ඕන නැහැ — මේ inbox එකෙන්ම ගන්න පුළුවන්.")
    return "\n".join(lines)



def build_inbox_reply_text(title: dict) -> str:
    return (
        f"✅ <b>{html.escape(title.get('title', 'Unknown Title'))}</b> ready.\n"
        "⬇️ මේ file එක tap කරලා Telegram download button එක ඔබන්න.\n"
        "📁 Download වෙලා ඉවර වුණාම gallery හරි files app එකෙන් open කරගන්න."
    )



def build_group_delivery_text(title: dict) -> str:
    return (
        f"📩 <b>{html.escape(title.get('title', 'Unknown Title'))}</b> file එක bot inbox එකට යැව්වා.\n"
        "Bot private chat එක open කරලා file එක download කරගන්න."
    )



def build_start_needed_text(bot_username: str | None) -> str:
    if bot_username:
        return (
            "📩 File එක inbox එකට යවන්න, මුලින් bot private chat එක open කරලා <b>Start</b> කරන්න.\n"
            "ඊට පස්සේ ආයෙ same button එක ඔබන්න."
        )
    return "📩 File එක inbox එකට යවන්න, මුලින් bot private chat එකේ Start කරන්න."



def build_admin_title_caption(title: dict) -> str:
    lines = [f"🛠 <b>{html.escape(title.get('title', 'Unknown Title'))}</b>"]
    meta = [media_type_label(title.get("media_type", "movie"))]
    if title.get("year"):
        meta.append(str(title["year"]))
    if title.get("poster_source"):
        meta.append(f"Poster: {html.escape(str(title['poster_source']).upper())}")
    lines.append(" • ".join(meta))
    lines.append("")
    lines.append("Edit කරන්න button එකක් ඔබලා, ඊළඟට එන bot message එකට text reply කරන්න.")
    return "\n".join(lines)



def build_variant_label(item: dict) -> str:
    parts: list[str] = []
    if item.get("season") is not None:
        parts.append(f"S{int(item['season']):02d}")
    if item.get("episode") is not None:
        parts.append(f"E{int(item['episode']):02d}")
    if item.get("quality"):
        parts.append(str(item["quality"]))
    if item.get("codec"):
        parts.append(str(item["codec"]))
    if item.get("size_label"):
        parts.append(str(item["size_label"]))
    return " • ".join(parts) if parts else str(item.get("_id"))



def build_variant_button_text(item: dict) -> str:
    codec = str(item.get("codec") or "Unknown Codec")
    size_label = str(item.get("size_label") or "Size ?")
    return f"⚙️ {codec} • {size_label}"

