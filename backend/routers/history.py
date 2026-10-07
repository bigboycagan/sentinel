"""Analysis history. Scoped to an anonymous httpOnly session cookie (no accounts).

POST /history re-analyzes the submitted code server-side and stores the report
— so a saved entry is always a genuine engine result, and the source code
itself is never persisted.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import List

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response

from lib import store
from models.analysis import AnalysisReport
from models.history import HistoryCreateRequest, HistorySummary
from routers.analysis import analyze_payload, rate_limit

router = APIRouter()

COOKIE_NAME = "sentinel_sid"
ONE_YEAR = 365 * 24 * 3600


async def require_sid(
    response: Response,
    sentinel_sid: str | None = Cookie(default=None),
) -> str:
    sid = sentinel_sid or str(uuid.uuid4())
    response.set_cookie(
        COOKIE_NAME,
        sid,
        httponly=True,
        samesite="lax",
        max_age=ONE_YEAR,
        path="/",
    )
    return sid


@router.get("/history", response_model=List[HistorySummary])
async def list_history(sid: str = Depends(require_sid)) -> List[HistorySummary]:
    rows = await asyncio.to_thread(store.list_analyses, sid)
    return [HistorySummary(**row) for row in rows]


@router.post("/history", response_model=HistorySummary)
async def save_history(
    payload: HistoryCreateRequest,
    sid: str = Depends(require_sid),
    _rl: None = Depends(rate_limit),
) -> HistorySummary:
    report = await analyze_payload(payload.code, payload.file_name, payload.language)
    summary = await asyncio.to_thread(store.save_analysis, sid, report.model_dump(mode="json"))
    return HistorySummary(**summary)


@router.get("/history/{analysis_id}", response_model=AnalysisReport)
async def get_history(analysis_id: str, sid: str = Depends(require_sid)) -> AnalysisReport:
    row = await asyncio.to_thread(store.get_analysis, sid, analysis_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Analysis not found in your history.")
    return AnalysisReport(**row["report"])


@router.delete("/history/{analysis_id}")
async def delete_history(analysis_id: str, sid: str = Depends(require_sid)) -> dict:
    deleted = await asyncio.to_thread(store.delete_analysis, sid, analysis_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Analysis not found in your history.")
    return {"ok": True}


@router.delete("/history")
async def clear_history(sid: str = Depends(require_sid)) -> dict:
    deleted = await asyncio.to_thread(store.clear_analyses, sid)
    return {"deleted": deleted}
