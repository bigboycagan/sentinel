"""Pydantic v2 models for the analysis boundary.

The frontend hand-mirrors every model here in frontend/src/lib/types.ts —
keep the two in sync in the same edit (nothing infers across HTTP).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class Finding(BaseModel):
    rule_id: str
    severity: str
    category: str
    title: str
    message: str
    file: str
    line: int
    column: int
    recommendation: str
    code_snippet: str | None = None


class ParseErrorInfo(BaseModel):
    message: str
    line: int
    column: int


class ScoreBreakdown(BaseModel):
    security: int
    quality: int
    complexity: int
    maintainability: int


class SeverityCounts(BaseModel):
    total: int
    critical: int
    high: int
    medium: int
    low: int
    info: int


class FileMetrics(BaseModel):
    total_lines: int
    source_lines: int
    comment_lines: int
    blank_lines: int
    function_count: int
    class_count: int
    max_nesting_depth: int | None = None
    avg_function_length: float | None = None
    avg_complexity: float | None = None
    max_complexity: int | None = None
    maintainability_index: int | None = None


class AnalysisReport(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    file_name: str
    language: str
    analyzed_at: datetime
    scores: ScoreBreakdown | None
    overall_score: int | None
    counts: SeverityCounts
    metrics: FileMetrics
    findings: list[Finding]
    parse_error: ParseErrorInfo | None = None


class AnalyzeRequest(BaseModel):
    code: str
    file_name: str = "untitled.py"
    language: str = "python"


class RuleMeta(BaseModel):
    rule_id: str
    title: str
    category: str
    severity: str
    description: str
    recommendation: str
    language: str


class LanguageOption(BaseModel):
    id: str
    label: str
    extensions: list[str]
