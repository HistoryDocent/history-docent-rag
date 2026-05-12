from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

from app.domain.retrieval import QueryType
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    measure_public_retrieval_artifact_quality,
)


CITATION_RAG_ANSWER_CONTRACT_VERSION = "citation-rag-answer/v1"
CITATION_RAG_CONTRACT_REPORT_VERSION = "citation-rag-contract-report/v1"

UnsupportedClaimRisk = Literal["low", "medium", "high"]
AnswerProviderKind = Literal["contract_only", "fake", "solar_pro_3"]
CoverageIntent = Literal["focused", "multi_evidence", "abstain"]
EvidencePackRank = Annotated[StrictInt, Field(ge=1)]

_PRIVATE_PATH_PATTERN = re.compile(r"([A-Za-z]:[\\/]|\\\\[^\\/]+[\\/][^\\/]+)")
_POSIX_PRIVATE_PATH_PATTERN = re.compile(
    r"(^|\s)/(home|users|mnt|var|tmp|private|runner|workspace|root)/",
    re.IGNORECASE,
)
_SECRET_VALUE_MARKERS = (
    "sk-",
    "api_" + "key=",
    "api" + "key=",
    "ghp_",
    "github_pat_",
    "hf_",
    "xoxb-",
    "bearer ",
    "pass" + "word=",
    "to" + "ken=",
    "sec" + "ret=",
)


class GenerationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CitationRagDraft(GenerationModel):
    answer: str = Field(min_length=1, max_length=4000)
    spoken_answer: str = Field(min_length=1, max_length=1200)
    unsupported_claim_risk: UnsupportedClaimRisk = "medium"

    @model_validator(mode="after")
    def validate_public_text_safety(self) -> "CitationRagDraft":
        _validate_public_text_value(self.answer, field_name="answer")
        _validate_public_text_value(self.spoken_answer, field_name="spoken_answer")
        return self


class CitationRagDraftV2(CitationRagDraft):
    used_evidence_pack_ranks: tuple[EvidencePackRank, ...] = Field(
        min_length=1,
        max_length=10,
    )
    coverage_intent: CoverageIntent

    @model_validator(mode="after")
    def validate_selected_evidence_contract(self) -> "CitationRagDraftV2":
        if len(self.used_evidence_pack_ranks) != len(set(self.used_evidence_pack_ranks)):
            raise ValueError("used_evidence_pack_ranks must be unique")
        return self


class Citation(GenerationModel):
    citation_id: str = Field(min_length=1)
    evidence_id: str = Field(min_length=1)
    child_id: str = Field(min_length=1)
    parent_id: str = Field(min_length=1)
    doc_id: str = Field(min_length=1)
    source_rank: int = Field(ge=1)
    pack_rank: int = Field(ge=1)
    source_block_ids: tuple[str, ...] = Field(min_length=1)
    citation_block_ids: tuple[str, ...] = Field(min_length=1)
    citation_recoverable: bool = True

    @model_validator(mode="after")
    def validate_citation_backtracking(self) -> "Citation":
        if not set(self.source_block_ids).issubset(set(self.citation_block_ids)):
            raise ValueError("citation_block_ids must cover source_block_ids")
        if not self.citation_recoverable:
            raise ValueError("citation must be recoverable for public answer contract")
        return self


class CitationRagAnswer(GenerationModel):
    contract_version: str = CITATION_RAG_ANSWER_CONTRACT_VERSION
    answer_policy_id: str = Field(min_length=1)
    provider: AnswerProviderKind
    model_id: str = Field(min_length=1)
    query_id: str = Field(min_length=1)
    query_type: QueryType
    answer: str = Field(min_length=1, max_length=4000)
    spoken_answer: str = Field(min_length=1, max_length=1200)
    citations: tuple[Citation, ...] = Field(default_factory=tuple)
    evidence_ids: tuple[str, ...] = Field(default_factory=tuple)
    place_ids: tuple[str, ...] = Field(default_factory=tuple)
    abstained: bool
    unsupported_claim_risk: UnsupportedClaimRisk
    public_allowed: bool = True

    @model_validator(mode="after")
    def validate_answer_contract(self) -> "CitationRagAnswer":
        if self.contract_version != CITATION_RAG_ANSWER_CONTRACT_VERSION:
            raise ValueError(f"contract_version must be {CITATION_RAG_ANSWER_CONTRACT_VERSION}")
        _validate_public_text_value(self.answer, field_name="answer")
        _validate_public_text_value(self.spoken_answer, field_name="spoken_answer")
        if len(self.evidence_ids) != len(set(self.evidence_ids)):
            raise ValueError("evidence_ids must be unique")
        citation_ids = [citation.citation_id for citation in self.citations]
        if len(citation_ids) != len(set(citation_ids)):
            raise ValueError("citation_ids must be unique")
        citation_evidence_ids = tuple(citation.evidence_id for citation in self.citations)
        if self.abstained:
            if self.citations or self.evidence_ids:
                raise ValueError("abstained answer must not include citations or evidence_ids")
            if self.unsupported_claim_risk == "high":
                raise ValueError("abstained answer should not carry high unsupported risk")
            return self
        if not self.citations:
            raise ValueError("non-abstained answer requires citations")
        if not self.evidence_ids:
            raise ValueError("non-abstained answer requires evidence_ids")
        if citation_evidence_ids != self.evidence_ids:
            raise ValueError("evidence_ids must match citation evidence_id order")
        if self.unsupported_claim_risk == "high":
            raise ValueError("high unsupported risk answer must abstain or be regenerated")
        return self


class CitationRagContractSummary(GenerationModel):
    answer_count: int = Field(ge=0)
    answered_count: int = Field(ge=0)
    abstained_count: int = Field(ge=0)
    citation_count: int = Field(ge=0)
    evidence_id_count: int = Field(ge=0)
    citation_recoverability_rate: float = Field(ge=0.0, le=1.0)
    answer_policy_count: int = Field(ge=0)
    provider_distribution: dict[str, int]
    unsupported_high_count: int = Field(ge=0)
    missing_citation_count: int = Field(ge=0)
    public_raw_text_leakage_count: int = Field(ge=0)
    private_path_leakage_count: int = Field(ge=0)
    secret_like_leakage_count: int = Field(ge=0)


class CitationRagContractReport(GenerationModel):
    report_version: str = CITATION_RAG_CONTRACT_REPORT_VERSION
    contract_version: str = CITATION_RAG_ANSWER_CONTRACT_VERSION
    summary: CitationRagContractSummary
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def build_citation_id(*, query_id: str, evidence_id: str, pack_rank: int) -> str:
    digest = _stable_digest(
        {
            "query_id": query_id,
            "evidence_id": evidence_id,
            "pack_rank": pack_rank,
        },
    )[:8]
    return f"cit-{pack_rank:02d}-{digest}"


def build_evidence_id(*, query_id: str, child_id: str, pack_rank: int) -> str:
    digest = _stable_digest(
        {
            "query_id": query_id,
            "child_id": child_id,
            "pack_rank": pack_rank,
        },
    )[:8]
    return f"ev-{pack_rank:02d}-{digest}"


def summarize_citation_rag_answers(
    answers: list[CitationRagAnswer],
) -> CitationRagContractSummary:
    citation_count = sum(len(answer.citations) for answer in answers)
    recoverable_count = sum(
        1 for answer in answers for citation in answer.citations if citation.citation_recoverable
    )
    payload = [answer.model_dump(mode="json") for answer in answers]
    return CitationRagContractSummary(
        answer_count=len(answers),
        answered_count=sum(1 for answer in answers if not answer.abstained),
        abstained_count=sum(1 for answer in answers if answer.abstained),
        citation_count=citation_count,
        evidence_id_count=sum(len(answer.evidence_ids) for answer in answers),
        citation_recoverability_rate=_safe_ratio(recoverable_count, citation_count),
        answer_policy_count=len({answer.answer_policy_id for answer in answers}),
        provider_distribution=dict(
            sorted(Counter(answer.provider for answer in answers).items()),
        ),
        unsupported_high_count=sum(
            1 for answer in answers if answer.unsupported_claim_risk == "high"
        ),
        missing_citation_count=sum(
            1 for answer in answers if not answer.abstained and not answer.citations
        ),
        public_raw_text_leakage_count=0,
        private_path_leakage_count=_count_private_path_leakage(payload),
        secret_like_leakage_count=_count_secret_like_leakage(payload),
    )


def collect_citation_rag_contract_failures(
    summary: CitationRagContractSummary,
    output_quality: PublicRetrievalArtifactQuality | None = None,
) -> list[str]:
    failures: list[str] = []
    if summary.answer_count == 0:
        failures.append("empty_answer_contract_sample")
    if summary.missing_citation_count:
        failures.append("missing_citations")
    if summary.citation_recoverability_rate < 1.0:
        failures.append("citation_recoverability_below_1")
    if summary.unsupported_high_count:
        failures.append("unsupported_high_answers")
    if summary.private_path_leakage_count:
        failures.append("private_path_leakage")
    if summary.secret_like_leakage_count:
        failures.append("secret_like_leakage")
    if output_quality is not None:
        if output_quality.public_raw_text_leakage_count:
            failures.append("public_raw_text_leakage")
        if output_quality.private_path_leakage_count:
            failures.append("public_output_private_path_leakage")
        if output_quality.secret_like_leakage_count:
            failures.append("public_output_secret_like_leakage")
        if output_quality.forbidden_result_field_count:
            failures.append("forbidden_public_result_fields")
    return failures


def build_public_citation_rag_answer_rows(
    answers: list[CitationRagAnswer],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for answer in answers:
        rows.append(
            {
                "contract_version": answer.contract_version,
                "answer_policy_id": answer.answer_policy_id,
                "provider": answer.provider,
                "model_id": answer.model_id,
                "query_id": answer.query_id,
                "query_type": answer.query_type,
                "abstained": answer.abstained,
                "unsupported_claim_risk": answer.unsupported_claim_risk,
                "answer_chars": len(answer.answer),
                "spoken_answer_chars": len(answer.spoken_answer),
                "citation_count": len(answer.citations),
                "evidence_id_count": len(answer.evidence_ids),
                "place_id_count": len(answer.place_ids),
                "citation_recoverability_rate": _safe_ratio(
                    sum(1 for citation in answer.citations if citation.citation_recoverable),
                    len(answer.citations),
                ),
            },
        )
    return rows


def build_citation_rag_contract_report(
    *,
    answers: list[CitationRagAnswer],
    report_text: str = "",
) -> CitationRagContractReport:
    public_rows = build_public_citation_rag_answer_rows(answers)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=CITATION_RAG_CONTRACT_REPORT_VERSION,
        run_id="citation-rag-contract",
        result_rows=public_rows,
        report_text=report_text,
    )
    summary = summarize_citation_rag_answers(answers)
    return CitationRagContractReport(
        summary=summary,
        output_quality=output_quality,
        qualitative_assessment=build_citation_rag_contract_qualitative_assessment(
            summary=summary,
            output_quality=output_quality,
        ),
    )


def build_citation_rag_contract_report_markdown(
    report: CitationRagContractReport,
) -> str:
    summary = report.summary
    quality = report.output_quality
    qualitative_rows = "\n".join(
        f"- `{key}`: {value}" for key, value in report.qualitative_assessment.items()
    )
    return f"""# Citation RAG Answer Contract Report

## 목적

Solar Pro 3 generation을 붙이기 전에 citation RAG API 응답 계약을 고정한다.

이 문서는 답변 품질 개선 주장이 아니다. `answer`, `spoken_answer`, `citations`, `evidence_ids`, `place_ids`, `abstained`, `unsupported_claim_risk`가 public-safe 구조로 검증되는지 확인한다.

## 정량 리포트

| metric | value |
| --- | ---: |
| answer_count | {summary.answer_count} |
| answered_count | {summary.answered_count} |
| abstained_count | {summary.abstained_count} |
| citation_count | {summary.citation_count} |
| evidence_id_count | {summary.evidence_id_count} |
| citation_recoverability_rate | {summary.citation_recoverability_rate:.6f} |
| answer_policy_count | {summary.answer_policy_count} |
| unsupported_high_count | {summary.unsupported_high_count} |
| missing_citation_count | {summary.missing_citation_count} |
| private_path_leakage_count | {summary.private_path_leakage_count} |
| secret_like_leakage_count | {summary.secret_like_leakage_count} |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | {quality.result_row_count} |
| public_raw_text_leakage_count | {quality.public_raw_text_leakage_count} |
| private_path_leakage_count | {quality.private_path_leakage_count} |
| secret_like_leakage_count | {quality.secret_like_leakage_count} |
| forbidden_result_field_count | {quality.forbidden_result_field_count} |

## 정성 리포트

{qualitative_rows}

## 해석

현재 단계는 LLM provider 구현이 아니라 응답 계약 고정이다.

다음 단계에서는 이 계약 위에 fake provider, Solar Pro 3 provider, generation evaluation harness를 순서대로 연결한다.
"""


def build_citation_rag_contract_qualitative_assessment(
    *,
    summary: CitationRagContractSummary,
    output_quality: PublicRetrievalArtifactQuality,
) -> dict[str, str]:
    failures = collect_citation_rag_contract_failures(summary, output_quality)
    return {
        "contract_scope": ("citation RAG 응답 필드와 citation backtracking id 계약을 검증했다."),
        "citation_boundary": (
            "citation은 answer text가 아니라 child_id, parent_id, doc_id, source_block_ids, citation_block_ids로 추적한다."
        ),
        "abstain_policy": (
            "no-answer 또는 evidence 없음 상태는 citations 없이 abstained=true로 반환한다."
        ),
        "provider_boundary": (
            "Solar Pro 3 호출은 포함하지 않았다. provider 연결은 다음 단계에서 이 계약을 만족해야 한다."
        ),
        "public_policy": (
            "public report와 result row에는 raw evidence text를 저장하지 않고 aggregate와 id만 남긴다."
        ),
        "gate_status": "PASS" if not failures else f"FAIL: {', '.join(failures)}",
    }


def _validate_public_text_value(value: str, *, field_name: str) -> None:
    if _contains_private_path(value):
        raise ValueError(f"{field_name} must not include private path")
    if _contains_secret_like_value(value):
        raise ValueError(f"{field_name} must not include secret-like value")


def _count_private_path_leakage(payload: Any) -> int:
    return sum(1 for value in _iter_string_values(payload) if _contains_private_path(value))


def _count_secret_like_leakage(payload: Any) -> int:
    return sum(1 for value in _iter_string_values(payload) if _contains_secret_like_value(value))


def _contains_private_path(value: str) -> bool:
    return bool(
        _PRIVATE_PATH_PATTERN.search(value.replace("/", "\\"))
        or _POSIX_PRIVATE_PATH_PATTERN.search(value)
    )


def _contains_secret_like_value(value: str) -> bool:
    lowered = value.lower()
    return any(marker in lowered for marker in _SECRET_VALUE_MARKERS)


def _iter_string_values(payload: Any) -> list[str]:
    if isinstance(payload, str):
        return [payload]
    if isinstance(payload, dict):
        values: list[str] = []
        for key, value in payload.items():
            values.extend(_iter_string_values(str(key)))
            values.extend(_iter_string_values(value))
        return values
    if isinstance(payload, list | tuple | set):
        values = []
        for item in payload:
            values.extend(_iter_string_values(item))
        return values
    return []


def _safe_ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 1.0
    return round(numerator / denominator, 6)


def _stable_digest(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]
