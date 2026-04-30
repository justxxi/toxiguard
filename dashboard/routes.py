from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from core.database import get_daily, get_events, get_stats, set_threshold

router = APIRouter(prefix="/api")


class ThresholdIn(BaseModel):
    threshold: float = Field(ge=0.0, le=1.0)


@router.get("/stats/{chat_id}")
async def stats(chat_id: int) -> dict:
    data = await get_stats(chat_id)
    data["daily"] = await get_daily(chat_id)
    return data


@router.get("/events/{chat_id}")
async def events(chat_id: int, limit: int = 50) -> list[dict]:
    return await get_events(chat_id, limit=limit)


@router.get("/top/{chat_id}")
async def top(chat_id: int) -> list[dict]:
    return (await get_stats(chat_id))["top_offenders"]


@router.post("/settings/{chat_id}/threshold")
async def update_threshold(chat_id: int, body: ThresholdIn) -> dict:
    return {"threshold": await set_threshold(chat_id, body.threshold)}
