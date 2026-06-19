"""Evidence location and validation for investment memos."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from difflib import SequenceMatcher
import re
from collections.abc import Sequence

from backend.config import get_settings
from backend.models.schemas import (
    EvidenceItem,
    InvestmentMemo,
    MonitoringRule,
    ValuationScenario,
)


_WHITESPACE_RE = re.compile(r"\s+")


class EvidenceValidationError(ValueError):
    """Raised when memo evidence cannot be located in supplied source text."""


@dataclass(frozen=True)
class SourceDocument:
    """Source text supplied to the memo validator."""

    source: str
    text: str
    published_date: date | None = None


@dataclass(frozen=True)
class _NormalizedText:
    text: str
    offsets: list[int]


@dataclass(frozen=True)
class _EvidenceMatch:
    start_offset: int
    end_offset: int
    score: float


def normalize_whitespace(text: str) -> str:
    """Collapse all whitespace runs to single spaces and trim the result."""

    return _WHITESPACE_RE.sub(" ", text).strip()


def _normalize_with_offsets(text: str) -> _NormalizedText:
    normalized_chars: list[str] = []
    offsets: list[int] = []
    pending_space_offset: int | None = None
    seen_non_space = False

    for offset, char in enumerate(text):
        if char.isspace():
            if seen_non_space and pending_space_offset is None:
                pending_space_offset = offset
            continue

        if pending_space_offset is not None:
            normalized_chars.append(" ")
            offsets.append(pending_space_offset)
            pending_space_offset = None

        normalized_chars.append(char)
        offsets.append(offset)
        seen_non_space = True

    return _NormalizedText(text="".join(normalized_chars), offsets=offsets)


def _original_offsets(normalized: _NormalizedText, start: int, end: int) -> tuple[int, int]:
    if start < 0 or end <= start or end > len(normalized.offsets):
        raise EvidenceValidationError("Evidence match produced invalid offsets")

    return normalized.offsets[start], normalized.offsets[end - 1] + 1


def _candidate_fuzzy_starts(quote: str, source: str) -> set[int]:
    starts: set[int] = set()
    matcher = SequenceMatcher(None, quote, source, autojunk=False)
    for block in matcher.get_matching_blocks():
        if block.size == 0:
            continue
        aligned_start = block.b - block.a
        for delta in range(-5, 6):
            starts.add(max(0, min(len(source), aligned_start + delta)))
    return starts


def _fuzzy_locate(quote: str, source: str) -> tuple[int, int, float] | None:
    if not quote or not source:
        return None

    quote_length = len(quote)
    length_delta = max(5, quote_length // 10)
    min_length = max(1, quote_length - length_delta)
    max_length = min(len(source), quote_length + length_delta)
    best: tuple[int, int, float] | None = None

    for start in _candidate_fuzzy_starts(quote, source):
        if start >= len(source):
            continue

        for length in range(min_length, max_length + 1):
            end = start + length
            if end > len(source):
                break
            candidate = source[start:end]
            score = SequenceMatcher(None, quote, candidate, autojunk=False).ratio()
            if best is None or score > best[2]:
                best = (start, end, score)

    return best


def _locate_normalized_quote(
    normalized_quote: str,
    normalized_source: _NormalizedText,
) -> _EvidenceMatch | None:
    exact_start = normalized_source.text.find(normalized_quote)
    if exact_start >= 0:
        exact_end = exact_start + len(normalized_quote)
        start_offset, end_offset = _original_offsets(
            normalized_source,
            exact_start,
            exact_end,
        )
        return _EvidenceMatch(
            start_offset=start_offset,
            end_offset=end_offset,
            score=1.0,
        )

    fuzzy = _fuzzy_locate(normalized_quote, normalized_source.text)
    if fuzzy is None:
        return None

    fuzzy_start, fuzzy_end, score = fuzzy
    start_offset, end_offset = _original_offsets(
        normalized_source,
        fuzzy_start,
        fuzzy_end,
    )
    return _EvidenceMatch(
        start_offset=start_offset,
        end_offset=end_offset,
        score=score,
    )


def _source_documents_by_name(
    source_documents: Sequence[SourceDocument],
) -> dict[str, list[SourceDocument]]:
    documents_by_name: dict[str, list[SourceDocument]] = {}
    for document in source_documents:
        normalized_source_name = normalize_whitespace(document.source)
        documents_by_name.setdefault(normalized_source_name, []).append(document)
    return documents_by_name


def locate_evidence_item(
    evidence: EvidenceItem,
    source_documents: Sequence[SourceDocument],
    threshold: float | None = None,
) -> EvidenceItem:
    """Validate and enrich one evidence item against supplied source documents."""

    match_threshold = (
        get_settings().quote_match_threshold if threshold is None else threshold
    )
    if not 0 <= match_threshold <= 1:
        raise ValueError("Evidence match threshold must be between 0 and 1")

    documents_by_name = _source_documents_by_name(source_documents)
    normalized_source_name = normalize_whitespace(evidence.source)
    matching_documents = documents_by_name.get(normalized_source_name, [])
    if not matching_documents:
        raise EvidenceValidationError(
            f"No supplied source text found for evidence source: {evidence.source}"
        )

    normalized_quote = normalize_whitespace(evidence.quote)
    if not normalized_quote:
        raise EvidenceValidationError("Evidence quote is empty after normalization")

    best_match: _EvidenceMatch | None = None
    for document in matching_documents:
        normalized_source = _normalize_with_offsets(document.text)
        located = _locate_normalized_quote(normalized_quote, normalized_source)
        if located is not None and (
            best_match is None or located.score > best_match.score
        ):
            best_match = located

    if best_match is None or best_match.score < match_threshold:
        score = 0.0 if best_match is None else best_match.score
        raise EvidenceValidationError(
            "Evidence quote could not be located above threshold "
            f"{match_threshold:.2f} in source {evidence.source!r}; "
            f"best score was {score:.3f}"
        )

    return evidence.model_copy(
        update={
            "source": normalized_source_name,
            "normalized_quote": normalized_quote,
            "located_start_offset": best_match.start_offset,
            "located_end_offset": best_match.end_offset,
            "match_score": best_match.score,
        }
    )


def _validate_evidence_list(
    evidence_items: Sequence[EvidenceItem],
    source_documents: Sequence[SourceDocument],
    threshold: float,
) -> list[EvidenceItem]:
    return [
        locate_evidence_item(
            evidence,
            source_documents=source_documents,
            threshold=threshold,
        )
        for evidence in evidence_items
    ]


def _validate_monitoring_rules(
    rules: Sequence[MonitoringRule],
    source_documents: Sequence[SourceDocument],
    threshold: float,
) -> list[MonitoringRule]:
    return [
        rule.model_copy(
            update={
                "evidence": _validate_evidence_list(
                    rule.evidence,
                    source_documents=source_documents,
                    threshold=threshold,
                )
            }
        )
        for rule in rules
    ]


def _validate_valuation_scenario(
    scenario: ValuationScenario,
    source_documents: Sequence[SourceDocument],
    threshold: float,
) -> ValuationScenario:
    return scenario.model_copy(
        update={
            "supporting_evidence": _validate_evidence_list(
                scenario.supporting_evidence,
                source_documents=source_documents,
                threshold=threshold,
            )
        }
    )


def validate_memo_evidence(
    memo: InvestmentMemo,
    source_documents: Sequence[SourceDocument],
    threshold: float | None = None,
) -> InvestmentMemo:
    """Validate and enrich every evidence item in an investment memo."""

    match_threshold = (
        get_settings().quote_match_threshold if threshold is None else threshold
    )
    if not source_documents:
        raise EvidenceValidationError("At least one source document is required")

    observations = [
        observation.model_copy(
            update={
                "evidence": _validate_evidence_list(
                    observation.evidence,
                    source_documents=source_documents,
                    threshold=match_threshold,
                )
            }
        )
        for observation in memo.observations
    ]

    adversarial_research = memo.adversarial_research.model_copy(
        update={
            "evidence_for_variant_view": _validate_evidence_list(
                memo.adversarial_research.evidence_for_variant_view,
                source_documents=source_documents,
                threshold=match_threshold,
            ),
            "evidence_against_variant_view": _validate_evidence_list(
                memo.adversarial_research.evidence_against_variant_view,
                source_documents=source_documents,
                threshold=match_threshold,
            ),
        }
    )

    valuation_range = memo.valuation_range.model_copy(
        update={
            "bear": _validate_valuation_scenario(
                memo.valuation_range.bear,
                source_documents=source_documents,
                threshold=match_threshold,
            ),
            "base": _validate_valuation_scenario(
                memo.valuation_range.base,
                source_documents=source_documents,
                threshold=match_threshold,
            ),
            "bull": _validate_valuation_scenario(
                memo.valuation_range.bull,
                source_documents=source_documents,
                threshold=match_threshold,
            ),
        }
    )

    monitoring_rules = memo.monitoring_rules.model_copy(
        update={
            "green_flags": _validate_monitoring_rules(
                memo.monitoring_rules.green_flags,
                source_documents=source_documents,
                threshold=match_threshold,
            ),
            "yellow_flags": _validate_monitoring_rules(
                memo.monitoring_rules.yellow_flags,
                source_documents=source_documents,
                threshold=match_threshold,
            ),
            "red_flags": _validate_monitoring_rules(
                memo.monitoring_rules.red_flags,
                source_documents=source_documents,
                threshold=match_threshold,
            ),
        }
    )

    return memo.model_copy(
        update={
            "observations": observations,
            "adversarial_research": adversarial_research,
            "valuation_range": valuation_range,
            "monitoring_rules": monitoring_rules,
        }
    )


__all__ = [
    "EvidenceValidationError",
    "SourceDocument",
    "locate_evidence_item",
    "normalize_whitespace",
    "validate_memo_evidence",
]
