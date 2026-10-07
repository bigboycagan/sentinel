"""Optional intelligence layer — INTENTIONALLY NOT IMPLEMENTED IN V1.

The engine's contract is: `analyze_code(...) -> AnalysisReport`. A future AI
provider (v3/v4 on the roadmap) would implement this Protocol and post-process
the report — explanations, remediation suggestions — without touching the rule
engine, the scoring, or any analyzer. Nothing in v1 imports or invokes this.

    class LlmExplainer:            # future, behind a feature flag
        def enrich(self, report: AnalysisReport) -> AnalysisReport: ...
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class Explainer(Protocol):
    """Post-processor that decorates an AnalysisReport with AI-derived insight."""

    def enrich(self, report: object) -> object:  # pragma: no cover - future hook
        ...
