from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.generation import (
    CITATION_RAG_ANSWER_CONTRACT_VERSION,
    Citation,
    CitationRagAnswer,
)
from app.domain.retrieval import ExpectedBehavior, QueryType, RetrievalEvalItem
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    measure_public_retrieval_artifact_quality,
)


GENERATION_EVAL_REPORT_VERSION = "generation-eval-report/v1"
GENERATION_EVAL_RUN_PREFIX = "generation-eval"


class GenerationEvalModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class GenerationEvalUsage(GenerationEvalModel):
    latency_ms: float = Field(default=0.0, ge=0.0)
    solar_call_count: int = Field(default=0, ge=0)
    estimated_cost: float = Field(default=0.0, ge=0.0)


class GenerationEvalInput(GenerationEvalModel):
    item: RetrievalEvalItem
    answer: CitationRagAnswer
    packing_policy_id: str = Field(min_length=1)
    retrieval_run_label: str = Field(default="unknown", min_length=1)
    provider_config_id: str = Field(default="contract-only", min_length=1)
    usage: GenerationEvalUsage = Field(default_factory=GenerationEvalUsage)


class GenerationEvalRecord(GenerationEvalModel):
    generation_run_id: str = Field(min_length=1)
    answer_fingerprint: str = Field(min_length=8)
    query_id: str = Field(min_length=1)
    query_type: QueryType
    split: str = Field(min_length=1)
    expected_behavior: ExpectedBehavior
    answer_policy_id: str = Field(min_length=1)
    packing_policy_id: str = Field(min_length=1)
    retrieval_run_label: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    provider_config_id: str = Field(min_length=1)
    abstained: bool
    correct_with_evidence: bool
    abstention_correct: bool
    citation_precision: float = Field(ge=0.0, le=1.0)
    citation_recall: float = Field(ge=0.0, le=1.0)
    place_relevance: float = Field(ge=0.0, le=1.0)
    docent_usefulness: float = Field(ge=0.0, le=1.0)
    spoken_answer_naturalness: float = Field(ge=0.0, le=1.0)
    unsupported_claim: bool
    unsupported_claim_risk: str = Field(min_length=1)
    citation_count: int = Field(ge=0)
    evidence_id_count: int = Field(ge=0)
    place_id_count: int = Field(ge=0)
    answer_chars: int = Field(ge=0)
    spoken_answer_chars: int = Field(ge=0)
    latency_ms: float = Field(ge=0.0)
    solar_call_count: int = Field(ge=0)
    estimated_cost: float = Field(ge=0.0)


class GenerationEvalSummary(GenerationEvalModel):
    eval_count: int = Field(ge=0)
    answerable_count: int = Field(ge=0)
    no_answer_count: int = Field(ge=0)
    answered_count: int = Field(ge=0)
    abstained_count: int = Field(ge=0)
    correct_with_evidence_rate: float = Field(ge=0.0, le=1.0)
    citation_precision: float = Field(ge=0.0, le=1.0)
    citation_recall: float = Field(ge=0.0, le=1.0)
    place_relevance: float = Field(ge=0.0, le=1.0)
    docent_usefulness: float = Field(ge=0.0, le=1.0)
    spoken_answer_naturalness: float = Field(ge=0.0, le=1.0)
    unsupported_claim_rate: float = Field(ge=0.0, le=1.0)
    abstention_accuracy: float = Field(ge=0.0, le=1.0)
    latency_p95_ms: float = Field(ge=0.0)
    solar_call_count: int = Field(ge=0)
    estimated_cost: float = Field(ge=0.0)
    answer_policy_count: int = Field(ge=0)
    provider_distribution: dict[str, int]
    missing_citation_count: int = Field(ge=0)
    unsupported_high_count: int = Field(ge=0)


class GenerationEvalQueryTypeSummary(GenerationEvalModel):
    query_type: QueryType
    eval_count: int = Field(ge=0)
    answerable_count: int = Field(ge=0)
    correct_with_evidence_rate: float = Field(ge=0.0, le=1.0)
    citation_precision: float = Field(ge=0.0, le=1.0)
    citation_recall: float = Field(ge=0.0, le=1.0)
    place_relevance: float = Field(ge=0.0, le=1.0)
    docent_usefulness: float = Field(ge=0.0, le=1.0)
    spoken_answer_naturalness: float = Field(ge=0.0, le=1.0)
    unsupported_claim_rate: float = Field(ge=0.0, le=1.0)
    abstention_accuracy: float = Field(ge=0.0, le=1.0)
    latency_p95_ms: float = Field(ge=0.0)


class GenerationEvalReport(GenerationEvalModel):
    report_version: str = GENERATION_EVAL_REPORT_VERSION
    answer_contract_version: str = CITATION_RAG_ANSWER_CONTRACT_VERSION
    eval_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    dataset_fingerprint: str = Field(min_length=8)
    summary: GenerationEvalSummary
    query_type_breakdown: tuple[GenerationEvalQueryTypeSummary, ...]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def build_generation_eval_records(
    inputs: list[GenerationEvalInput],
) -> list[GenerationEvalRecord]:
    _validate_generation_eval_inputs(inputs)
    return [_build_generation_eval_record(item) for item in inputs]


def build_generation_eval_report(
    *,
    inputs: list[GenerationEvalInput],
    report_text: str = "",
) -> GenerationEvalReport:
    records = build_generation_eval_records(inputs)
    eval_id = build_generation_eval_id(records)
    public_rows = build_public_generation_eval_rows(records=records)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=GENERATION_EVAL_REPORT_VERSION,
        run_id=eval_id,
        result_rows=public_rows,
        report_text=report_text,
    )
    summary = summarize_generation_eval_records(records)
    return GenerationEvalReport(
        eval_id=eval_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        dataset_fingerprint=build_generation_eval_dataset_fingerprint(inputs),
        summary=summary,
        query_type_breakdown=tuple(summarize_generation_eval_query_types(records)),
        output_quality=output_quality,
        qualitative_assessment=build_generation_eval_qualitative_assessment(
            summary=summary,
            output_quality=output_quality,
        ),
    )


def summarize_generation_eval_records(
    records: list[GenerationEvalRecord],
) -> GenerationEvalSummary:
    answerable_records = [
        record for record in records if record.expected_behavior == "retrieve"
    ]
    return GenerationEvalSummary(
        eval_count=len(records),
        answerable_count=len(answerable_records),
        no_answer_count=sum(
            1 for record in records if record.expected_behavior == "abstain"
        ),
        answered_count=sum(1 for record in records if not record.abstained),
        abstained_count=sum(1 for record in records if record.abstained),
        correct_with_evidence_rate=_rate_or_zero(
            sum(1 for record in answerable_records if record.correct_with_evidence),
            len(answerable_records),
        ),
        citation_precision=_mean_or_zero(
            [record.citation_precision for record in answerable_records],
        ),
        citation_recall=_mean_or_zero(
            [record.citation_recall for record in answerable_records],
        ),
        place_relevance=_mean([record.place_relevance for record in records]),
        docent_usefulness=_mean([record.docent_usefulness for record in records]),
        spoken_answer_naturalness=_mean(
            [record.spoken_answer_naturalness for record in records],
        ),
        unsupported_claim_rate=_rate(
            sum(1 for record in records if record.unsupported_claim),
            len(records),
        ),
        abstention_accuracy=_rate(
            sum(1 for record in records if record.abstention_correct),
            len(records),
        ),
        latency_p95_ms=_percentile(
            [record.latency_ms for record in records],
            0.95,
        ),
        solar_call_count=sum(record.solar_call_count for record in records),
        estimated_cost=round(sum(record.estimated_cost for record in records), 6),
        answer_policy_count=len({record.answer_policy_id for record in records}),
        provider_distribution=dict(
            sorted(Counter(record.provider for record in records).items()),
        ),
        missing_citation_count=sum(
            1
            for record in records
            if record.expected_behavior == "retrieve"
            and not record.abstained
            and record.citation_count == 0
        ),
        unsupported_high_count=sum(
            1 for record in records if record.unsupported_claim_risk == "high"
        ),
    )


def summarize_generation_eval_query_types(
    records: list[GenerationEvalRecord],
) -> list[GenerationEvalQueryTypeSummary]:
    rows: list[GenerationEvalQueryTypeSummary] = []
    for query_type in sorted({record.query_type for record in records}):
        subset = [record for record in records if record.query_type == query_type]
        answerable_subset = [
            record for record in subset if record.expected_behavior == "retrieve"
        ]
        rows.append(
            GenerationEvalQueryTypeSummary(
                query_type=query_type,
                eval_count=len(subset),
                answerable_count=len(answerable_subset),
                correct_with_evidence_rate=_rate_or_zero(
                    sum(
                        1
                        for record in answerable_subset
                        if record.correct_with_evidence
                    ),
                    len(answerable_subset),
                ),
                citation_precision=_mean_or_zero(
                    [record.citation_precision for record in answerable_subset],
                ),
                citation_recall=_mean_or_zero(
                    [record.citation_recall for record in answerable_subset],
                ),
                place_relevance=_mean([record.place_relevance for record in subset]),
                docent_usefulness=_mean(
                    [record.docent_usefulness for record in subset],
                ),
                spoken_answer_naturalness=_mean(
                    [record.spoken_answer_naturalness for record in subset],
                ),
                unsupported_claim_rate=_rate(
                    sum(1 for record in subset if record.unsupported_claim),
                    len(subset),
                ),
                abstention_accuracy=_rate(
                    sum(1 for record in subset if record.abstention_correct),
                    len(subset),
                ),
                latency_p95_ms=_percentile(
                    [record.latency_ms for record in subset],
                    0.95,
                ),
            ),
        )
    return rows


def build_public_generation_eval_rows(
    *,
    records: list[GenerationEvalRecord],
) -> list[dict[str, Any]]:
    return [
        {
            "generation_run_id": record.generation_run_id,
            "answer_fingerprint": record.answer_fingerprint,
            "query_id": record.query_id,
            "query_type": record.query_type,
            "split": record.split,
            "expected_behavior": record.expected_behavior,
            "answer_policy_id": record.answer_policy_id,
            "packing_policy_id": record.packing_policy_id,
            "retrieval_run_label": record.retrieval_run_label,
            "provider": record.provider,
            "model_id": record.model_id,
            "provider_config_id": record.provider_config_id,
            "abstained": record.abstained,
            "correct_with_evidence": record.correct_with_evidence,
            "abstention_correct": record.abstention_correct,
            "citation_precision": record.citation_precision,
            "citation_recall": record.citation_recall,
            "place_relevance": record.place_relevance,
            "docent_usefulness": record.docent_usefulness,
            "spoken_answer_naturalness": record.spoken_answer_naturalness,
            "unsupported_claim": record.unsupported_claim,
            "unsupported_claim_risk": record.unsupported_claim_risk,
            "citation_count": record.citation_count,
            "evidence_id_count": record.evidence_id_count,
            "place_id_count": record.place_id_count,
            "answer_chars": record.answer_chars,
            "spoken_answer_chars": record.spoken_answer_chars,
            "latency_ms": record.latency_ms,
            "solar_call_count": record.solar_call_count,
            "estimated_cost": record.estimated_cost,
        }
        for record in records
    ]


def build_generation_eval_report_markdown(report: GenerationEvalReport) -> str:
    summary = report.summary
    quality = report.output_quality
    breakdown_rows = "\n".join(
        _format_query_type_summary_row(row) for row in report.query_type_breakdown
    )
    qualitative_rows = "\n".join(
        f"- `{key}`: {value}" for key, value in report.qualitative_assessment.items()
    )
    return f"""# Generation Evaluation Harness Report

## 목적

Citation RAG answer contract 결과를 Solar Pro 3 provider 연결 전에 평가 가능한 metric으로 고정한다.

이 문서는 답변 품질 개선 주장이 아니다. 현재 리포트는 harness smoke 결과이며, 실제 품질 주장은 private dev/test generation 실행과 paired comparison 이후에만 가능하다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| answer_contract_version | `{report.answer_contract_version}` |
| eval_id | `{report.eval_id}` |
| generated_at_utc | `{report.generated_at_utc}` |
| dataset_fingerprint | `{report.dataset_fingerprint}` |

## 정량 리포트

| metric | value |
| --- | ---: |
| eval_count | {summary.eval_count} |
| answerable_count | {summary.answerable_count} |
| no_answer_count | {summary.no_answer_count} |
| answered_count | {summary.answered_count} |
| abstained_count | {summary.abstained_count} |
| Correct-with-Evidence | {summary.correct_with_evidence_rate:.6f} |
| citation_precision | {summary.citation_precision:.6f} |
| citation_recall | {summary.citation_recall:.6f} |
| place_relevance | {summary.place_relevance:.6f} |
| docent_usefulness | {summary.docent_usefulness:.6f} |
| spoken_answer_naturalness | {summary.spoken_answer_naturalness:.6f} |
| unsupported_claim_rate | {summary.unsupported_claim_rate:.6f} |
| abstention_accuracy | {summary.abstention_accuracy:.6f} |
| latency_p95_ms | {summary.latency_p95_ms:.6f} |
| solar_call_count | {summary.solar_call_count} |
| estimated_cost | {summary.estimated_cost:.6f} |
| missing_citation_count | {summary.missing_citation_count} |
| unsupported_high_count | {summary.unsupported_high_count} |

## Query Type Breakdown

| query_type | eval_count | answerable_count | Correct-with-Evidence | citation_precision | citation_recall | place_relevance | docent_usefulness | spoken_answer_naturalness | unsupported_claim_rate | abstention_accuracy | latency_p95_ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{breakdown_rows}

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

현재 단계는 generation 평가 harness 구현이다.

다음 단계에서 Solar Pro 3 provider를 연결하되, 이 metric과 public-safe output gate를 그대로 사용한다.
"""


def collect_generation_eval_harness_failures(
    report: GenerationEvalReport,
) -> list[str]:
    failures: list[str] = []
    if report.summary.eval_count == 0:
        failures.append("empty_generation_eval")
    if report.summary.missing_citation_count:
        failures.append("missing_citations")
    if report.summary.unsupported_high_count:
        failures.append("unsupported_high_answers")
    if report.output_quality.public_raw_text_leakage_count:
        failures.append("public_raw_text_leakage")
    if report.output_quality.private_path_leakage_count:
        failures.append("private_path_leakage")
    if report.output_quality.secret_like_leakage_count:
        failures.append("secret_like_leakage")
    if report.output_quality.forbidden_result_field_count:
        failures.append("forbidden_public_result_fields")
    return failures


def build_generation_eval_qualitative_assessment(
    *,
    summary: GenerationEvalSummary,
    output_quality: PublicRetrievalArtifactQuality,
) -> dict[str, str]:
    failures = []
    if summary.eval_count == 0:
        failures.append("empty_generation_eval")
    if output_quality.public_raw_text_leakage_count:
        failures.append("public_raw_text_leakage")
    if output_quality.private_path_leakage_count:
        failures.append("private_path_leakage")
    if output_quality.secret_like_leakage_count:
        failures.append("secret_like_leakage")
    if summary.solar_call_count:
        cost_boundary = (
            f"Solar Pro 3 호출 {summary.solar_call_count}회를 기록했다. "
            "estimated_cost는 provider 설정의 단가가 0이면 0으로 남을 수 있다."
        )
    else:
        cost_boundary = (
            "현재 smoke run은 Solar Pro 3를 호출하지 않아 "
            "solar_call_count와 estimated_cost가 0이다."
        )
    return {
        "harness_scope": (
            "CitationRagAnswer를 query grain의 정량 metric으로 변환하는 평가 계층을 구현했다."
        ),
        "metric_boundary": (
            "Correct-with-Evidence와 citation 지표는 answerable query만 품질 판단에 사용한다."
        ),
        "abstain_boundary": (
            "no_answer query는 abstention_accuracy로 분리해 corpus 밖 질문 환각을 감시한다."
        ),
        "cost_boundary": cost_boundary,
        "public_policy": (
            "public row와 report에는 원문 evidence, chunk text, raw answer text를 저장하지 않는다."
        ),
        "gate_status": "PASS" if not failures else f"FAIL: {', '.join(failures)}",
    }


def build_generation_eval_id(records: list[GenerationEvalRecord]) -> str:
    payload = [
        {
            "answer_fingerprint": record.answer_fingerprint,
            "query_id": record.query_id,
            "answer_policy_id": record.answer_policy_id,
            "packing_policy_id": record.packing_policy_id,
            "provider": record.provider,
            "model_id": record.model_id,
        }
        for record in sorted(records, key=lambda item: item.query_id)
    ]
    digest = _stable_digest(payload)[:8]
    return f"{GENERATION_EVAL_RUN_PREFIX}-q{len(records)}-{digest}"


def build_generation_eval_dataset_fingerprint(
    inputs: list[GenerationEvalInput],
) -> str:
    payload = [
        item.item.model_dump(mode="json")
        for item in sorted(inputs, key=lambda row: row.item.query.query_id)
    ]
    return _stable_digest(payload)


def _validate_generation_eval_inputs(inputs: list[GenerationEvalInput]) -> None:
    query_ids: list[str] = []
    for item in inputs:
        query = item.item.query
        answer = item.answer
        if query.query_id != answer.query_id:
            raise ValueError("generation eval item query_id must match answer query_id")
        if query.query_type != answer.query_type:
            raise ValueError("generation eval item query_type must match answer query_type")
        query_ids.append(query.query_id)
    if len(query_ids) != len(set(query_ids)):
        raise ValueError("generation eval query_id values must be unique")


def _build_generation_eval_record(
    item: GenerationEvalInput,
) -> GenerationEvalRecord:
    answer = item.answer
    eval_item = item.item
    expected_behavior = eval_item.query.expected_behavior
    citation_precision = _citation_precision(eval_item, answer)
    citation_recall = _citation_recall(eval_item, answer)
    correct_with_evidence = (
        expected_behavior == "retrieve"
        and not answer.abstained
        and bool(answer.citations)
        and citation_precision > 0
        and citation_recall > 0
        and answer.unsupported_claim_risk != "high"
    )
    abstention_correct = (
        answer.abstained
        if expected_behavior == "abstain"
        else not answer.abstained
    )
    place_relevance = _place_relevance(eval_item, answer)
    spoken_answer_naturalness = _spoken_answer_naturalness(answer)
    unsupported_claim = _unsupported_claim(
        expected_behavior=expected_behavior,
        answer=answer,
        citation_precision=citation_precision,
    )
    answer_fingerprint = _stable_digest(
        {
            "answer": answer.answer,
            "spoken_answer": answer.spoken_answer,
            "citations": [citation.citation_id for citation in answer.citations],
        },
    )
    generation_run_id = _generation_run_id(
        answer=answer,
        answer_fingerprint=answer_fingerprint,
        packing_policy_id=item.packing_policy_id,
        provider_config_id=item.provider_config_id,
    )
    return GenerationEvalRecord(
        generation_run_id=generation_run_id,
        answer_fingerprint=answer_fingerprint,
        query_id=answer.query_id,
        query_type=answer.query_type,
        split=eval_item.metadata.split,
        expected_behavior=expected_behavior,
        answer_policy_id=answer.answer_policy_id,
        packing_policy_id=item.packing_policy_id,
        retrieval_run_label=item.retrieval_run_label,
        provider=answer.provider,
        model_id=answer.model_id,
        provider_config_id=item.provider_config_id,
        abstained=answer.abstained,
        correct_with_evidence=correct_with_evidence,
        abstention_correct=abstention_correct,
        citation_precision=citation_precision,
        citation_recall=citation_recall,
        place_relevance=place_relevance,
        docent_usefulness=_docent_usefulness(
            expected_behavior=expected_behavior,
            correct_with_evidence=correct_with_evidence,
            abstention_correct=abstention_correct,
            place_relevance=place_relevance,
            spoken_answer_naturalness=spoken_answer_naturalness,
            unsupported_claim=unsupported_claim,
            answer=answer,
        ),
        spoken_answer_naturalness=spoken_answer_naturalness,
        unsupported_claim=unsupported_claim,
        unsupported_claim_risk=answer.unsupported_claim_risk,
        citation_count=len(answer.citations),
        evidence_id_count=len(answer.evidence_ids),
        place_id_count=len(answer.place_ids),
        answer_chars=len(answer.answer),
        spoken_answer_chars=len(answer.spoken_answer),
        latency_ms=item.usage.latency_ms,
        solar_call_count=item.usage.solar_call_count,
        estimated_cost=item.usage.estimated_cost,
    )


def _citation_precision(
    item: RetrievalEvalItem,
    answer: CitationRagAnswer,
) -> float:
    if answer.abstained:
        return 1.0 if not answer.citations else 0.0
    if not answer.citations:
        return 0.0
    target_refs = _target_refs(item)
    if not target_refs:
        return 1.0
    relevant_count = sum(
        1 for citation in answer.citations if _citation_refs(citation) & target_refs
    )
    return _rate(relevant_count, len(answer.citations))


def _citation_recall(
    item: RetrievalEvalItem,
    answer: CitationRagAnswer,
) -> float:
    target_refs = _target_refs(item)
    if not target_refs:
        return 1.0 if answer.abstained else 0.0
    covered_refs: set[str] = set()
    for citation in answer.citations:
        covered_refs.update(_citation_refs(citation) & target_refs)
    return _rate(len(covered_refs), len(target_refs))


def _target_refs(item: RetrievalEvalItem) -> set[str]:
    refs: set[str] = set()
    for judgment in item.judgments:
        refs.update(f"child:{child_id}" for child_id in judgment.relevant_child_ids)
        refs.update(f"parent:{parent_id}" for parent_id in judgment.relevant_parent_ids)
        refs.update(f"doc:{doc_id}" for doc_id in judgment.relevant_doc_ids)
    return refs


def _citation_refs(citation: Citation) -> set[str]:
    return {
        f"child:{citation.child_id}",
        f"parent:{citation.parent_id}",
        f"doc:{citation.doc_id}",
    }


def _place_relevance(
    item: RetrievalEvalItem,
    answer: CitationRagAnswer,
) -> float:
    expected_place_ids = set(item.metadata.place_ids)
    if not expected_place_ids:
        return 1.0
    if answer.abstained:
        return 0.0
    matched = expected_place_ids & set(answer.place_ids)
    return _rate(len(matched), len(expected_place_ids))


def _spoken_answer_naturalness(answer: CitationRagAnswer) -> float:
    spoken = answer.spoken_answer.strip()
    if not spoken:
        return 0.0
    if "\n" in spoken or "\r" in spoken:
        return 0.0
    if any(marker in spoken for marker in ("[", "]", "http://", "https://")):
        return 0.0
    if answer.abstained:
        return 1.0 if 10 <= len(spoken) <= 160 else 0.0
    return 1.0 if 15 <= len(spoken) <= 260 else 0.0


def _docent_usefulness(
    *,
    expected_behavior: ExpectedBehavior,
    correct_with_evidence: bool,
    abstention_correct: bool,
    place_relevance: float,
    spoken_answer_naturalness: float,
    unsupported_claim: bool,
    answer: CitationRagAnswer,
) -> float:
    if expected_behavior == "abstain":
        return 1.0 if abstention_correct and not unsupported_claim else 0.0
    answer_chars = len(answer.answer.strip())
    useful = (
        correct_with_evidence
        and place_relevance > 0
        and spoken_answer_naturalness > 0
        and not unsupported_claim
        and 20 <= answer_chars <= 1200
    )
    return 1.0 if useful else 0.0


def _unsupported_claim(
    *,
    expected_behavior: ExpectedBehavior,
    answer: CitationRagAnswer,
    citation_precision: float,
) -> bool:
    if answer.abstained:
        return False
    if answer.unsupported_claim_risk == "high":
        return True
    return expected_behavior == "retrieve" and citation_precision == 0.0


def _generation_run_id(
    *,
    answer: CitationRagAnswer,
    answer_fingerprint: str,
    packing_policy_id: str,
    provider_config_id: str,
) -> str:
    digest = _stable_digest(
        {
            "query_id": answer.query_id,
            "answer_policy_id": answer.answer_policy_id,
            "packing_policy_id": packing_policy_id,
            "provider": answer.provider,
            "model_id": answer.model_id,
            "provider_config_id": provider_config_id,
            "answer_fingerprint": answer_fingerprint,
        },
    )[:8]
    return f"{GENERATION_EVAL_RUN_PREFIX}-{answer.query_id}-{digest}"


def _format_query_type_summary_row(row: GenerationEvalQueryTypeSummary) -> str:
    return (
        f"| {row.query_type} | {row.eval_count} | {row.answerable_count} | "
        f"{row.correct_with_evidence_rate:.6f} | "
        f"{row.citation_precision:.6f} | {row.citation_recall:.6f} | "
        f"{row.place_relevance:.6f} | {row.docent_usefulness:.6f} | "
        f"{row.spoken_answer_naturalness:.6f} | "
        f"{row.unsupported_claim_rate:.6f} | "
        f"{row.abstention_accuracy:.6f} | {row.latency_p95_ms:.6f} |"
    )


def _mean(values: list[float]) -> float:
    if not values:
        return 1.0
    return round(sum(values) / len(values), 6)


def _mean_or_zero(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 6)


def _rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 1.0
    return round(numerator / denominator, 6)


def _rate_or_zero(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 6)


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = round((len(sorted_values) - 1) * percentile)
    return round(sorted_values[index], 6)


def _stable_digest(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"),
    ).hexdigest()[:16]
