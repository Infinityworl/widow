from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class CallbackPayload:
    action: str
    title_id: str = ""
    season: Optional[int] = None
    quality: Optional[str] = None
    codec: Optional[str] = None
    page: int = 0
    episode_id: Optional[str] = None
    media_type: Optional[str] = None



def encode(parts: list[str | int | None]) -> str:
    cleaned = [str(part) for part in parts if part is not None]
    return "|".join(cleaned)



def decode(data: str) -> CallbackPayload:
    parts = data.split("|")
    action = parts[0]

    if action == "pick":
        return CallbackPayload(action=action, title_id=parts[1])
    if action == "st":
        return CallbackPayload(action=action, media_type=parts[1])
    if action == "mq":
        return CallbackPayload(action=action, title_id=parts[1], quality=parts[2])
    if action == "mc":
        return CallbackPayload(action=action, title_id=parts[1], quality=parts[2], codec=parts[3])
    if action == "ss":
        return CallbackPayload(action=action, title_id=parts[1], season=int(parts[2]))
    if action == "sq":
        return CallbackPayload(action=action, title_id=parts[1], season=int(parts[2]), quality=parts[3])
    if action == "sc":
        return CallbackPayload(
            action=action,
            title_id=parts[1],
            season=int(parts[2]),
            quality=parts[3],
            codec=parts[4],
            page=int(parts[5]) if len(parts) > 5 else 0,
        )
    if action == "ep":
        return CallbackPayload(action=action, title_id=parts[1], episode_id=parts[2])
    if action == "pg":
        return CallbackPayload(
            action=action,
            title_id=parts[1],
            season=int(parts[2]),
            quality=parts[3],
            codec=parts[4],
            page=int(parts[5]),
        )
    raise ValueError(f"Unknown callback data: {data}")
