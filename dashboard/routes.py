from __future__ import annotations

from fastapi import APIRouter

from core.database import get_daily, get_events, get_stats, set_threshold
from dashboard.schemas import EventOut, Offender, StatsOut, ThresholdIn, ThresholdOut

router = APIRouter(prefix="/api")


@router.get("/stats", response_model=StatsOut)
async def stats_all() -> StatsOut:
    data = await get_stats()
    return StatsOut(
        total=data["total"],
        by_category=data["by_category"],
        top_offenders=[Offender(**o) for o in data["top_offenders"]],
        daily=[{"day": d["day"], "count": d["count"]} for d in await get_daily()],
    )


@router.get("/stats/{chat_id}", response_model=StatsOut)
async def stats(chat_id: int) -> StatsOut:
    data = await get_stats(chat_id)
    return StatsOut(
        total=data["total"],
        by_category=data["by_category"],
        top_offenders=[Offender(**o) for o in data["top_offenders"]],
        daily=[{"day": d["day"], "count": d["count"]} for d in await get_daily(chat_id)],
    )


@router.get("/events", response_model=list[EventOut])
async def events_all(limit: int = 50) -> list[EventOut]:
    return [EventOut(**e) for e in await get_events(limit=limit)]


@router.get("/events/{chat_id}", response_model=list[EventOut])
async def events(chat_id: int, limit: int = 50) -> list[EventOut]:
    return [EventOut(**e) for e in await get_events(chat_id, limit=limit)]


@router.get("/top", response_model=list[Offender])
async def top_all() -> list[Offender]:
    return [Offender(**o) for o in (await get_stats())["top_offenders"]]


@router.get("/top/{chat_id}", response_model=list[Offender])
async def top(chat_id: int) -> list[Offender]:
    return [Offender(**o) for o in (await get_stats(chat_id))["top_offenders"]]


@router.post("/settings/{chat_id}/threshold", response_model=ThresholdOut)
async def update_threshold(chat_id: int, body: ThresholdIn) -> ThresholdOut:
    return ThresholdOut(threshold=await set_threshold(chat_id, body.threshold))


@router.get("/health", include_in_schema=False)
async def health() -> dict:
    return {"status": "ok"}
