from __future__ import annotations

from fastapi import APIRouter, Depends

from trustai_api.deps import get_settings_dep
from trustai_api.routes.utils import list_packs
from trustai_api.schemas import PacksResponse
from trustai_api.settings import Settings

router = APIRouter()


@router.get("/v1/packs", response_model=PacksResponse)
def packs(settings: Settings = Depends(get_settings_dep)) -> dict:
    return {"packs": list_packs(settings)}
