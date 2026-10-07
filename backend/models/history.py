"""Pydantic v2 models for the analysis-history endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class HistoryCreateRequest(BaseModel):
    code: str
    file_name: str = "untitled.py"
    language: str = "python"


class HistorySummary(BaseModel):
    id: str
    created_at: datetime
    file_name: str
    language: str
    overall_score: int | None
    security_score: int | None
    total_issues: int
    critical_issues: int
    high_issues: int
    medium_issues: int
    low_issues: int
    info_issues: int
