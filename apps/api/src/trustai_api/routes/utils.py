from __future__ import annotations

from fastapi import HTTPException

from trustai_api.settings import Settings


def list_packs(settings: Settings) -> list[str]:
    if not settings.storage_root.exists():
        return []
    return sorted([path.name for path in settings.storage_root.iterdir() if path.is_dir()])


def resolve_pack(settings: Settings, pack_header: str | None) -> str:
    available = list_packs(settings)
    pack = pack_header or "general"
    if pack not in available:
        raise HTTPException(
            status_code=400,
            detail={"message": "Invalid pack", "available_packs": available},
        )
    return pack
