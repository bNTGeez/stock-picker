"""Backend service package."""

from backend.services.manual_memo_generator import (
    CompanyMetadata,
    InvalidMemoEvidenceError,
    InvalidMemoJSONError,
    InvalidMemoSchemaError,
    ManualMemoGenerationError,
    ManualMemoGenerator,
    ManualMemoLLM,
    ManualMemoRequest,
    ManualSourceExcerpt,
    REASONING_CHAIN,
    build_manual_memo_prompt,
    parse_investment_memo_response,
    source_documents_from_request,
)
from backend.services.memo_quality_gate import (
    MINIMUM_AVERAGE_SCORE,
    MINIMUM_CRITERION_SCORE,
    MemoQualityGateResult,
    PHASE_3_RUBRIC,
    QUALITATIVE_ONLY_CRITERIA_UNTIL_PHASE_4,
    evaluate_memo_quality_gate,
)

__all__ = [
    "CompanyMetadata",
    "InvalidMemoEvidenceError",
    "InvalidMemoJSONError",
    "InvalidMemoSchemaError",
    "ManualMemoGenerationError",
    "ManualMemoGenerator",
    "ManualMemoLLM",
    "ManualMemoRequest",
    "ManualSourceExcerpt",
    "MemoQualityGateResult",
    "MINIMUM_AVERAGE_SCORE",
    "MINIMUM_CRITERION_SCORE",
    "PHASE_3_RUBRIC",
    "QUALITATIVE_ONLY_CRITERIA_UNTIL_PHASE_4",
    "REASONING_CHAIN",
    "build_manual_memo_prompt",
    "evaluate_memo_quality_gate",
    "parse_investment_memo_response",
    "source_documents_from_request",
]
