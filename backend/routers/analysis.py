"""Analysis endpoints: JSON analyze + multipart upload. Both share one pipeline:

validate → (parse only, never execute) → rules → metrics → scoring → report.
"""

from __future__ import annotations

import asyncio
import os
import re

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile

from analyzers.engine import EmptySourceError, UnsupportedLanguageError, analyze_code
from lib import store
from lib import rate_limit as limiter
from models.analysis import AnalysisReport, AnalyzeRequest

router = APIRouter()


def rate_limit(request: Request) -> None:
    """Sliding-window limiter shared by every endpoint that runs analysis."""
    forwarded = request.headers.get("x-forwarded-for", "")
    ip = forwarded.split(",")[0].strip() or (request.client.host if request.client else "unknown")
    if not limiter.allow(ip):
        raise HTTPException(
            status_code=429,
            detail="Too many analyses in a short time. Please wait a minute and try again.",
        )


def sanitize_file_name(name: str | None, default: str = "untitled.py") -> str:
    base = os.path.basename(name or "").strip()
    base = re.sub(r"[^\w.\- ]", "_", base)[:120].strip()
    return base or default


async def analyze_payload(code: str, file_name: str, language: str) -> AnalysisReport:
    """Validate + analyze one source string. Shared by /analyze, /analyze/upload, /history."""
    settings = await asyncio.to_thread(store.get_settings)
    max_bytes = int(settings["max_file_size_bytes"])
    if len(code.encode("utf-8")) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Source exceeds the maximum size of {max_bytes // 1024} KB "
            "(adjust it in Settings).",
        )
    try:
        report = await asyncio.to_thread(
            analyze_code, code, file_name, language, settings["disabled_rules"]
        )
    except EmptySourceError:
        raise HTTPException(status_code=400, detail="Please provide source code to analyze.")
    except UnsupportedLanguageError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return report


@router.post("/analyze", response_model=AnalysisReport)
async def analyze(payload: AnalyzeRequest, _rl: None = Depends(rate_limit)) -> AnalysisReport:
    file_name = sanitize_file_name(payload.file_name)
    return await analyze_payload(payload.code, file_name, payload.language)


@router.post("/analyze/upload", response_model=AnalysisReport)
async def analyze_upload(
    file: UploadFile,
    language: str = Form("python"),
    _rl: None = Depends(rate_limit),
) -> AnalysisReport:
    settings = await asyncio.to_thread(store.get_settings)
    max_bytes = int(settings["max_file_size_bytes"])

    raw_name = file.filename or ""
    if not raw_name.lower().endswith(".py"):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. SENTINEL currently supports Python files.",
        )

    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"The uploaded file exceeds the maximum size of {max_bytes // 1024} KB "
            "(adjust it in Settings).",
        )
    if not content.strip():
        raise HTTPException(status_code=400, detail="Please provide source code to analyze.")
    try:
        code = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is not valid UTF-8 text and cannot be analyzed.",
        )

    return await analyze_payload(code, sanitize_file_name(raw_name, "uploaded.py"), language)
