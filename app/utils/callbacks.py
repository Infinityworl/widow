from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class CallbackPayload:
    action: str
    title_id: str = ""
    season: Optional[int] = None
    episode: Optional[int] = None
    quality: Optional[str] = None
    codec: Optional[str] = None
    page: int = 0
    media_file_id: Optional[str] = None
    media_type: Optional[str] = None


def encode(parts: list[str | int | None]) -> str:
    return "|".join(str(part) for part in parts if part is not None)


def decode(data: str) -> CallbackPayload:
    parts = data.split("|")
    action = parts[0]
    if action == "pick":
        return CallbackPayload(action=action, title_id=parts[1])
    if action == "st":
        return CallbackPayload(action=action, media_type=parts[1], page=int(parts[2]) if len(parts) > 2 else 0)
    if action == "mq":
        return CallbackPayload(action=action, title_id=parts[1], quality=parts[2])
    if action == "mqp":
        return CallbackPayload(action=action, title_id=parts[1], page=int(parts[2]))
    if action == "mvp":
        return CallbackPayload(action=action, title_id=parts[1], quality=parts[2], page=int(parts[3]))
    if action == "mv":
        return CallbackPayload(action=action, title_id=parts[1], media_file_id=parts[2])
    if action == "dl":
        return CallbackPayload(action=action, title_id=parts[1], media_file_id=parts[2])
    if action == "ss":
        return CallbackPayload(action=action, title_id=parts[1], season=int(parts[2]), page=int(parts[3]) if len(parts) > 3 else 0)
    if action == "sp":
        return CallbackPayload(action=action, title_id=parts[1], season=int(parts[2]), page=int(parts[3]))
    if action == "se":
        return CallbackPayload(action=action, title_id=parts[1], season=int(parts[2]), episode=int(parts[3]))
    if action == "eq":
        return CallbackPayload(action=action, title_id=parts[1], season=int(parts[2]), episode=int(parts[3]), quality=parts[4])
    if action == "eqp":
        return CallbackPayload(action=action, title_id=parts[1], season=int(parts[2]), episode=int(parts[3]), page=int(parts[4]))
    if action == "evp":
        return CallbackPayload(action=action, title_id=parts[1], season=int(parts[2]), episode=int(parts[3]), quality=parts[4], page=int(parts[5]))
    if action == "ev":
        return CallbackPayload(action=action, title_id=parts[1], media_file_id=parts[2])
    raise ValueError(f"Unknown callback data: {data}")
