"""Pydantic v2 models for the app-settings endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AppSettings(BaseModel):
    max_file_size_bytes: int
    disabled_rules: list[str]


class AppSettingsUpdate(BaseModel):
    max_file_size_bytes: int | None = Field(default=None, ge=10_000, le=10_000_000)
    disabled_rules: list[str] | None = None
