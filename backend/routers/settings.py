"""App settings: max upload size + rule toggles. Validated against the registry."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

from analyzers.engine import all_rules
from lib import store
from models.settings import AppSettings, AppSettingsUpdate

router = APIRouter()


@router.get("/settings", response_model=AppSettings)
async def get_app_settings() -> AppSettings:
    settings = await asyncio.to_thread(store.get_settings)
    return AppSettings(**settings)


@router.put("/settings", response_model=AppSettings)
async def update_app_settings(payload: AppSettingsUpdate) -> AppSettings:
    patch: dict = {}
    if payload.max_file_size_bytes is not None:
        patch["max_file_size_bytes"] = store.clamp_file_size(payload.max_file_size_bytes)
    if payload.disabled_rules is not None:
        known = {rule.rule_id for rule in all_rules()}
        unknown = [rule_id for rule_id in payload.disabled_rules if rule_id not in known]
        if unknown:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown rule id(s): {', '.join(unknown[:10])}",
            )
        patch["disabled_rules"] = payload.disabled_rules
    settings = await asyncio.to_thread(store.update_settings, patch)
    return AppSettings(**settings)
