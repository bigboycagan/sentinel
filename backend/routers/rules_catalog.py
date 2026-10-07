"""Rules catalog: served straight from the rule registry (single source of truth)."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter

from analyzers.engine import all_rules
from models.analysis import RuleMeta

router = APIRouter()


@router.get("/rules", response_model=List[RuleMeta])
async def list_rules() -> List[RuleMeta]:
    rules = sorted(all_rules(), key=lambda r: r.rule_id)
    return [
        RuleMeta(
            rule_id=rule.rule_id,
            title=rule.title,
            category=rule.category,
            severity=rule.severity,
            description=rule.description,
            recommendation=rule.recommendation,
            language=rule.language,
        )
        for rule in rules
    ]
