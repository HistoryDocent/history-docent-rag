from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.application.citation_rag import CitationRagAnswerAssembler, CitationRagAssemblerConfig
from app.application.evidence_packing import EvidencePack, EvidencePackingPolicyId, PackedEvidence
from app.core.project_paths import (
    has_private_data_segment,
    is_repository_private_artifact_path,
    is_repository_private_write_path,
)
from app.domain.generation import CitationRagAnswer, CitationRagDraft, CitationRagDraftV2
from app.domain.generation_eval import (
    GenerationEvalInput,
    GenerationEvalRecord,
    GenerationEvalReport,
    GenerationEvalUsage,
    build_generation_eval_dataset_fingerprint,
    build_generation_eval_records,
    build_generation_eval_report,
    collect_generation_eval_harness_failures,
)
from app.domain.retrieval import QueryType, RetrievalEvalItem
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    measure_public_retrieval_artifact_quality,
)


SOLAR_GENERATION_CONTRACT_V2_COMPARISON_REPORT_VERSION = (
    "solar-generation-contract-v2-comparison-report/v1"
)
SOLAR_GENERATION_BASELINE_ANSWER_POLICY_ID = "solar-generation-baseline-v1"
SOLAR_GENERATION_CONTRACT_V2_ANSWER_POLICY_ID = "solar-generation-contract-v2"
DEFAULT_RETRIEVAL_RUN_LABEL = "dense_multilingual_e5_small_voice_rewrite"
DEFAULT_PACKING_POLICY_ID: EvidencePackingPolicyId = "P0_rank_order"
DEFAULT_QUERY_TYPES: tuple[QueryType, ...] = (
    "place_fact",
    "place_story",
    "relationship",
    "overview",
    "route_context",
    "voice_followup",
    "no_answer",
)
DEFAULT_REPORT_PATH = Path("evals/reports/solar_generation_contract_v2_comparison_report.md")
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "solar_generation_contract_v2_comparison_results.jsonl"
)


class SolarGenerationContractV2ComparisonModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class GenerationPolicyPairDelta(SolarGenerationContractV2ComparisonModel):
    query_id: str = Field(min_length=1)
    query_type: QueryType
    v1_correct_with_evidence: bool
    v2_correct_with_evidence: bool
    correct_with_evidence_delta: int
    v1_citation_precision: float = Field(ge=0.0, le=1.0)
    v2_citation_precision: float = Field(ge=0.0, le=1.0)
    citation_precision_delta: float
    v1_citation_recall: float = Field(ge=0.0, le=1.0)
    v2_citation_recall: float = Field(ge=0.0, le=1.0)
    citation_recall_delta: float
    v1_unsupported_claim: bool
    v2_unsupported_claim: bool
    unsupported_claim_delta: int
    v1_citation_count: int = Field(ge=0)
    v2_citation_count: int = Field(ge=0)
    citation_count_delta: int
    latency_ms_delta: float


class GenerationPolicyQueryTypeDelta(SolarGenerationContractV2ComparisonModel):
    query_type: QueryType
    eval_count: int = Field(ge=0)
    correct_with_evidence_delta: float
    citation_precision_delta: float
    citation_recall_delta: float
    unsupported_claim_rate_delta: float
    latency_p95_ms_delta: float


class SolarGenerationContractV2ComparisonReport(SolarGenerationContractV2ComparisonModel):
    report_version: str = SOLAR_GENERATION_CONTRACT_V2_COMPARISON_REPORT_VERSION
    comparison_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    dataset_fingerprint: str = Field(min_length=8)
    retrieval_run_label: str = Field(min_length=1)
    packing_policy_id: str = Field(min_length=1)
    baseline_answer_policy_id: str = Field(min_length=1)
    candidate_answer_policy_id: str = Field(min_length=1)
    baseline_provider_config_id: str = Field(min_length=1)
    candidate_provider_config_id: str = Field(min_length=1)
    baseline_report: GenerationEvalReport
    candidate_report: GenerationEvalReport
    paired_deltas: tuple[GenerationPolicyPairDelta, ...]
    query_type_deltas: tuple[GenerationPolicyQueryTypeDelta, ...]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def run_solar_generation_contract_v2_comparison(
    *,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
) -> SolarGenerationContractV2ComparisonReport:
    _validate_result_rows_path(result_rows_path)
    baseline_inputs, candidate_inputs = build_fake_generation_contract_v2_comparison_inputs()
    provisional_report = build_solar_generation_contract_v2_comparison_report(
        baseline_inputs=baseline_inputs,
        candidate_inputs=candidate_inputs,
    )
    provisional_markdown = build_solar_generation_contract_v2_comparison_report_markdown(
        provisional_report,
    )
    report = build_solar_generation_contract_v2_comparison_report(
        baseline_inputs=baseline_inputs,
        candidate_inputs=candidate_inputs,
        report_text=provisional_markdown,
    )
    markdown = build_solar_generation_contract_v2_comparison_report_markdown(report)
    failures = collect_solar_generation_contract_v2_comparison_failures(report)
    if failures:
        raise ValueError(f"solar generation contract v2 comparison gate failed: {failures}")

    rows = build_public_solar_generation_contract_v2_comparison_rows(report)
    write_jsonl_rows(path=result_rows_path, rows=rows)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(markdown, encoding="utf-8")
    return report


def build_solar_generation_contract_v2_comparison_report(
    *,
    baseline_inputs: list[GenerationEvalInput],
    candidate_inputs: list[GenerationEvalInput],
    report_text: str = "",
) -> SolarGenerationContractV2ComparisonReport:
    validate_generation_contract_v2_comparison_inputs(
        baseline_inputs=baseline_inputs,
        candidate_inputs=candidate_inputs,
    )
    baseline_report = build_generation_eval_report(inputs=baseline_inputs)
    candidate_report = build_generation_eval_report(inputs=candidate_inputs)
    baseline_records = build_generation_eval_records(baseline_inputs)
    candidate_records = build_generation_eval_records(candidate_inputs)
    paired_deltas = tuple(
        build_generation_policy_pair_deltas(
            baseline_records=baseline_records,
            candidate_records=candidate_records,
        ),
    )
    query_type_deltas = tuple(build_generation_policy_query_type_deltas(paired_deltas))
    public_rows = build_public_solar_generation_contract_v2_comparison_rows_from_deltas(
        paired_deltas,
    )
    comparison_id = build_solar_generation_contract_v2_comparison_id(
        baseline_records=baseline_records,
        candidate_records=candidate_records,
    )
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=SOLAR_GENERATION_CONTRACT_V2_COMPARISON_REPORT_VERSION,
        run_id=comparison_id,
        result_rows=public_rows,
        report_text=report_text,
    )
    report = SolarGenerationContractV2ComparisonReport(
        comparison_id=comparison_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        dataset_fingerprint=build_generation_eval_dataset_fingerprint(baseline_inputs),
        retrieval_run_label=_single_value(
            [item.retrieval_run_label for item in baseline_inputs],
            field_name="retrieval_run_label",
        ),
        packing_policy_id=_single_value(
            [item.packing_policy_id for item in baseline_inputs],
            field_name="packing_policy_id",
        ),
        baseline_answer_policy_id=SOLAR_GENERATION_BASELINE_ANSWER_POLICY_ID,
        candidate_answer_policy_id=SOLAR_GENERATION_CONTRACT_V2_ANSWER_POLICY_ID,
        baseline_provider_config_id=_single_value(
            [item.provider_config_id for item in baseline_inputs],
            field_name="baseline_provider_config_id",
        ),
        candidate_provider_config_id=_single_value(
            [item.provider_config_id for item in candidate_inputs],
            field_name="candidate_provider_config_id",
        ),
        baseline_report=baseline_report,
        candidate_report=candidate_report,
        paired_deltas=paired_deltas,
        query_type_deltas=query_type_deltas,
        output_quality=output_quality,
        qualitative_assessment={},
    )
    return report.model_copy(
        update={
            "qualitative_assessment": build_solar_generation_contract_v2_qualitative_assessment(
                report,
            ),
        },
    )


def validate_generation_contract_v2_comparison_inputs(
    *,
    baseline_inputs: list[GenerationEvalInput],
    candidate_inputs: list[GenerationEvalInput],
) -> None:
    if not baseline_inputs or not candidate_inputs:
        raise ValueError("generation contract v2 comparison requires non-empty inputs")
    baseline_by_query_id = {item.item.query.query_id: item for item in baseline_inputs}
    candidate_by_query_id = {item.item.query.query_id: item for item in candidate_inputs}
    if set(baseline_by_query_id) != set(candidate_by_query_id):
        raise ValueError("v1/v2 paired comparison requires identical query_id set")
    if build_generation_eval_dataset_fingerprint(
        baseline_inputs,
    ) != build_generation_eval_dataset_fingerprint(candidate_inputs):
        raise ValueError("v1/v2 paired comparison requires identical eval dataset")
    for query_id, baseline in baseline_by_query_id.items():
        candidate = candidate_by_query_id[query_id]
        if baseline.item.query.query_type != candidate.item.query.query_type:
            raise ValueError("v1/v2 paired comparison requires identical query_type")
        if baseline.packing_policy_id != candidate.packing_policy_id:
            raise ValueError("v1/v2 paired comparison requires identical packing_policy_id")
        if baseline.retrieval_run_label != candidate.retrieval_run_label:
            raise ValueError("v1/v2 paired comparison requires identical retrieval_run_label")
    _require_answer_policy(
        baseline_inputs,
        expected=SOLAR_GENERATION_BASELINE_ANSWER_POLICY_ID,
        label="baseline",
    )
    _require_answer_policy(
        candidate_inputs,
        expected=SOLAR_GENERATION_CONTRACT_V2_ANSWER_POLICY_ID,
        label="candidate",
    )


def build_generation_policy_pair_deltas(
    *,
    baseline_records: list[GenerationEvalRecord],
    candidate_records: list[GenerationEvalRecord],
) -> list[GenerationPolicyPairDelta]:
    candidate_by_query_id = {record.query_id: record for record in candidate_records}
    deltas: list[GenerationPolicyPairDelta] = []
    for baseline in sorted(baseline_records, key=lambda record: record.query_id):
        candidate = candidate_by_query_id[baseline.query_id]
        deltas.append(
            GenerationPolicyPairDelta(
                query_id=baseline.query_id,
                query_type=baseline.query_type,
                v1_correct_with_evidence=baseline.correct_with_evidence,
                v2_correct_with_evidence=candidate.correct_with_evidence,
                correct_with_evidence_delta=int(candidate.correct_with_evidence)
                - int(baseline.correct_with_evidence),
                v1_citation_precision=baseline.citation_precision,
                v2_citation_precision=candidate.citation_precision,
                citation_precision_delta=round(
                    candidate.citation_precision - baseline.citation_precision,
                    6,
                ),
                v1_citation_recall=baseline.citation_recall,
                v2_citation_recall=candidate.citation_recall,
                citation_recall_delta=round(
                    candidate.citation_recall - baseline.citation_recall,
                    6,
                ),
                v1_unsupported_claim=baseline.unsupported_claim,
                v2_unsupported_claim=candidate.unsupported_claim,
                unsupported_claim_delta=int(candidate.unsupported_claim)
                - int(baseline.unsupported_claim),
                v1_citation_count=baseline.citation_count,
                v2_citation_count=candidate.citation_count,
                citation_count_delta=candidate.citation_count - baseline.citation_count,
                latency_ms_delta=round(candidate.latency_ms - baseline.latency_ms, 6),
            ),
        )
    return deltas


def build_generation_policy_query_type_deltas(
    paired_deltas: tuple[GenerationPolicyPairDelta, ...],
) -> list[GenerationPolicyQueryTypeDelta]:
    grouped: dict[QueryType, list[GenerationPolicyPairDelta]] = defaultdict(list)
    for delta in paired_deltas:
        grouped[delta.query_type].append(delta)
    return [
        GenerationPolicyQueryTypeDelta(
            query_type=query_type,
            eval_count=len(rows),
            correct_with_evidence_delta=_mean_float(
                [float(row.correct_with_evidence_delta) for row in rows],
            ),
            citation_precision_delta=_mean_float(
                [row.citation_precision_delta for row in rows],
            ),
            citation_recall_delta=_mean_float([row.citation_recall_delta for row in rows]),
            unsupported_claim_rate_delta=_mean_float(
                [float(row.unsupported_claim_delta) for row in rows],
            ),
            latency_p95_ms_delta=_max_float([row.latency_ms_delta for row in rows]),
        )
        for query_type, rows in sorted(grouped.items())
    ]


def build_public_solar_generation_contract_v2_comparison_rows(
    report: SolarGenerationContractV2ComparisonReport,
) -> list[dict[str, Any]]:
    return build_public_solar_generation_contract_v2_comparison_rows_from_deltas(
        report.paired_deltas,
    )


def build_public_solar_generation_contract_v2_comparison_rows_from_deltas(
    paired_deltas: tuple[GenerationPolicyPairDelta, ...],
) -> list[dict[str, Any]]:
    return [
        {
            "query_id": delta.query_id,
            "query_type": delta.query_type,
            "baseline_answer_policy_id": SOLAR_GENERATION_BASELINE_ANSWER_POLICY_ID,
            "candidate_answer_policy_id": SOLAR_GENERATION_CONTRACT_V2_ANSWER_POLICY_ID,
            "v1_correct_with_evidence": delta.v1_correct_with_evidence,
            "v2_correct_with_evidence": delta.v2_correct_with_evidence,
            "correct_with_evidence_delta": delta.correct_with_evidence_delta,
            "v1_citation_precision": delta.v1_citation_precision,
            "v2_citation_precision": delta.v2_citation_precision,
            "citation_precision_delta": delta.citation_precision_delta,
            "v1_citation_recall": delta.v1_citation_recall,
            "v2_citation_recall": delta.v2_citation_recall,
            "citation_recall_delta": delta.citation_recall_delta,
            "unsupported_claim_delta": delta.unsupported_claim_delta,
            "v1_citation_count": delta.v1_citation_count,
            "v2_citation_count": delta.v2_citation_count,
            "citation_count_delta": delta.citation_count_delta,
            "latency_ms_delta": delta.latency_ms_delta,
        }
        for delta in paired_deltas
    ]


def collect_solar_generation_contract_v2_comparison_failures(
    report: SolarGenerationContractV2ComparisonReport,
) -> list[str]:
    failures: list[str] = []
    failures.extend(
        f"baseline_{failure}"
        for failure in collect_generation_eval_harness_failures(report.baseline_report)
    )
    failures.extend(
        f"candidate_{failure}"
        for failure in collect_generation_eval_harness_failures(report.candidate_report)
    )
    if report.baseline_report.summary.eval_count != report.candidate_report.summary.eval_count:
        failures.append("mismatched_eval_count")
    if not report.paired_deltas:
        failures.append("empty_paired_delta")
    if report.output_quality.public_raw_text_leakage_count:
        failures.append("public_raw_text_leakage")
    if report.output_quality.private_path_leakage_count:
        failures.append("private_path_leakage")
    if report.output_quality.secret_like_leakage_count:
        failures.append("secret_like_leakage")
    if report.output_quality.forbidden_result_field_count:
        failures.append("forbidden_public_result_fields")
    if (
        report.baseline_report.summary.solar_call_count
        or report.candidate_report.summary.solar_call_count
    ):
        failures.append("fake_comparison_must_not_call_solar")
    return failures


def build_solar_generation_contract_v2_comparison_report_markdown(
    report: SolarGenerationContractV2ComparisonReport,
) -> str:
    baseline = report.baseline_report.summary
    candidate = report.candidate_report.summary
    quality = report.output_quality
    paired_rows = "\n".join(_format_pair_delta_row(delta) for delta in report.paired_deltas)
    query_type_rows = "\n".join(
        _format_query_type_delta_row(delta) for delta in report.query_type_deltas
    )
    qualitative_rows = "\n".join(
        f"- `{key}`: {value}" for key, value in report.qualitative_assessment.items()
    )
    return f"""# Solar Pro 3 Generation Contract v2 Comparison Report

## 목적

`CitationRagDraft` v1과 `CitationRagDraftV2` selected evidence contract를 같은 query set, 같은 retrieval label, 같은 evidence packing policy에서 비교한다.

이 문서는 fake provider 기반 contract 비교다. live Solar Pro 3 호출 결과가 아니며, 최종 성능 개선 주장이 아니다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| comparison_id | `{report.comparison_id}` |
| generated_at_utc | `{report.generated_at_utc}` |
| dataset_fingerprint | `{report.dataset_fingerprint}` |
| retrieval_run_label | `{report.retrieval_run_label}` |
| packing_policy_id | `{report.packing_policy_id}` |
| baseline_answer_policy_id | `{report.baseline_answer_policy_id}` |
| candidate_answer_policy_id | `{report.candidate_answer_policy_id}` |
| baseline_provider_config_id | `{report.baseline_provider_config_id}` |
| candidate_provider_config_id | `{report.candidate_provider_config_id}` |
| live_solar_call_count | {baseline.solar_call_count + candidate.solar_call_count} |

## 정량 리포트

| metric | v1 baseline | v2 candidate | delta |
| --- | ---: | ---: | ---: |
| eval_count | {baseline.eval_count} | {candidate.eval_count} | {candidate.eval_count - baseline.eval_count} |
| Correct-with-Evidence | {baseline.correct_with_evidence_rate:.6f} | {candidate.correct_with_evidence_rate:.6f} | {candidate.correct_with_evidence_rate - baseline.correct_with_evidence_rate:.6f} |
| citation_precision | {baseline.citation_precision:.6f} | {candidate.citation_precision:.6f} | {candidate.citation_precision - baseline.citation_precision:.6f} |
| citation_recall | {baseline.citation_recall:.6f} | {candidate.citation_recall:.6f} | {candidate.citation_recall - baseline.citation_recall:.6f} |
| unsupported_claim_rate | {baseline.unsupported_claim_rate:.6f} | {candidate.unsupported_claim_rate:.6f} | {candidate.unsupported_claim_rate - baseline.unsupported_claim_rate:.6f} |
| abstention_accuracy | {baseline.abstention_accuracy:.6f} | {candidate.abstention_accuracy:.6f} | {candidate.abstention_accuracy - baseline.abstention_accuracy:.6f} |
| latency_p95_ms | {baseline.latency_p95_ms:.6f} | {candidate.latency_p95_ms:.6f} | {candidate.latency_p95_ms - baseline.latency_p95_ms:.6f} |
| solar_call_count | {baseline.solar_call_count} | {candidate.solar_call_count} | {candidate.solar_call_count - baseline.solar_call_count} |

## Paired Delta

| query_id | query_type | Correct delta | citation_precision delta | citation_recall delta | unsupported_claim delta | citation_count delta | latency_ms delta |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
{paired_rows}

## Query Type Delta

| query_type | eval_count | Correct delta | citation_precision delta | citation_recall delta | unsupported_claim_rate delta | latency_p95_ms delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
{query_type_rows}

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

이번 결과는 selected evidence contract가 citation 수와 precision metric에 어떤 영향을 주는지 확인하는 fake provider gate다.

다음 단계에서만 같은 7개 query set, 같은 retrieval label, 같은 packing policy로 live Solar Pro 3 paired comparison을 실행한다.
"""


def build_fake_generation_contract_v2_comparison_inputs() -> tuple[
    list[GenerationEvalInput],
    list[GenerationEvalInput],
]:
    items = [_fake_eval_item(query_type=query_type) for query_type in DEFAULT_QUERY_TYPES]
    baseline_inputs: list[GenerationEvalInput] = []
    candidate_inputs: list[GenerationEvalInput] = []
    for item in items:
        evidence_pack = _fake_evidence_pack(item)
        baseline_answer = _assemble_fake_answer(
            item=item,
            evidence_pack=evidence_pack,
            answer_policy_id=SOLAR_GENERATION_BASELINE_ANSWER_POLICY_ID,
            model_id="fake-solar-pro3-v1",
            draft=_fake_v1_draft(item.query.query_type),
        )
        candidate_draft = (
            None
            if item.query.expected_behavior == "abstain"
            else _fake_v2_draft(item.query.query_type)
        )
        candidate_answer = _assemble_fake_answer(
            item=item,
            evidence_pack=evidence_pack,
            answer_policy_id=SOLAR_GENERATION_CONTRACT_V2_ANSWER_POLICY_ID,
            model_id="fake-solar-pro3-v2",
            draft=candidate_draft,
        )
        baseline_inputs.append(
            _eval_input(
                item=item,
                answer=baseline_answer,
                provider_config_id="fake-solar-generation-v1",
            ),
        )
        candidate_inputs.append(
            _eval_input(
                item=item,
                answer=candidate_answer,
                provider_config_id="fake-solar-generation-v2",
            ),
        )
    return baseline_inputs, candidate_inputs


def build_solar_generation_contract_v2_comparison_id(
    *,
    baseline_records: list[GenerationEvalRecord],
    candidate_records: list[GenerationEvalRecord],
) -> str:
    payload = {
        "baseline": [
            _comparison_id_record(record)
            for record in sorted(baseline_records, key=lambda item: item.query_id)
        ],
        "candidate": [
            _comparison_id_record(record)
            for record in sorted(candidate_records, key=lambda item: item.query_id)
        ],
    }
    digest = _stable_digest(payload)[:8]
    return f"solar-generation-contract-v2-q{len(baseline_records)}-{digest}"


def build_solar_generation_contract_v2_qualitative_assessment(
    report: SolarGenerationContractV2ComparisonReport,
) -> dict[str, str]:
    failures = collect_solar_generation_contract_v2_comparison_failures(report)
    return {
        "comparison_scope": (
            "v1/v2 answer policy만 다르게 두고 query set, retrieval label, packing policy를 고정했다."
        ),
        "provider_boundary": (
            "이번 runner는 fake provider 기반 contract gate다. Solar Pro 3 live API를 호출하지 않았다."
        ),
        "metric_grain": ("query 단위 paired delta와 query_type delta를 분리해 기록한다."),
        "citation_policy": (
            "v1은 packed evidence 전체를 citation으로 붙이고, v2는 selected evidence rank만 citation으로 붙인다."
        ),
        "place_story_boundary": (
            "`place_story`는 fake contract run에는 포함하지만 live 개선 판단에서는 retrieval hard-case monitor로 분리한다."
        ),
        "claim_boundary": (
            "현재 결과는 성능 개선 주장이 아니라 live paired comparison 전의 runner 검증이다."
        ),
        "public_policy": (
            "public report와 result row에는 raw query, raw answer, evidence text, chunk text를 저장하지 않는다."
        ),
        "gate_status": "PASS" if not failures else f"FAIL: {', '.join(failures)}",
    }


def _assemble_fake_answer(
    *,
    item: RetrievalEvalItem,
    evidence_pack: EvidencePack,
    answer_policy_id: str,
    model_id: str,
    draft: CitationRagDraft | None,
) -> CitationRagAnswer:
    assembler = CitationRagAnswerAssembler(
        config=CitationRagAssemblerConfig(
            answer_policy_id=answer_policy_id,
            provider="fake",
            model_id=model_id,
        ),
    )
    return assembler.assemble(
        item=item,
        evidence_pack=evidence_pack,
        draft=draft,
        place_ids=tuple(item.metadata.place_ids),
    )


def _eval_input(
    *,
    item: RetrievalEvalItem,
    answer: CitationRagAnswer,
    provider_config_id: str,
) -> GenerationEvalInput:
    return GenerationEvalInput(
        item=item,
        answer=answer,
        packing_policy_id=DEFAULT_PACKING_POLICY_ID,
        retrieval_run_label=DEFAULT_RETRIEVAL_RUN_LABEL,
        provider_config_id=provider_config_id,
        usage=GenerationEvalUsage(latency_ms=0.0, solar_call_count=0),
    )


def _fake_eval_item(*, query_type: QueryType) -> RetrievalEvalItem:
    expected_behavior = "abstain" if query_type == "no_answer" else "retrieve"
    query_id = f"q-fake-{query_type}-001"
    target = _target_ids(query_type)
    judgments = []
    if expected_behavior == "retrieve":
        judgments.append(
            {
                "query_id": query_id,
                "relevant_child_ids": [target["child_id"]],
                "relevant_parent_ids": [target["parent_id"]],
                "relevant_doc_ids": [target["doc_id"]],
                "relevance_grade": 3,
                "rationale_summary": "public-safe fixture target id",
                "public_allowed": True,
            },
        )
    return RetrievalEvalItem.model_validate(
        {
            "dataset_version": "retrieval-eval-dataset/v2",
            "query": {
                "query_id": query_id,
                "query_type": query_type,
                "query_text": f"{query_type} fixture query",
                "language": "ko",
                "expected_behavior": expected_behavior,
                "user_context": None,
                "public_allowed": True,
            },
            "judgments": judgments,
            "metadata": {
                "split": "dev",
                "difficulty": "medium",
                "place_ids": ["gyeongbokgung"] if expected_behavior == "retrieve" else [],
                "requires_context": query_type == "voice_followup",
                "answerability": "answerable"
                if expected_behavior == "retrieve"
                else "unanswerable",
                "review_status": "reviewed",
            },
        },
    )


def _fake_evidence_pack(item: RetrievalEvalItem) -> EvidencePack:
    if item.query.expected_behavior == "abstain":
        return EvidencePack(
            query_id=item.query.query_id,
            query_type=item.query.query_type,
            policy_id=DEFAULT_PACKING_POLICY_ID,
            context_budget_chars=4200,
            total_estimated_chars=0,
            evidence=(),
            target_child_covered=False,
            target_parent_covered=False,
            target_doc_covered=False,
            evidence_order_relevance_proxy=1.0,
        )
    target = _target_ids(item.query.query_type)
    evidence = (
        _packed_evidence(
            pack_rank=1,
            source_rank=1,
            child_id=target["child_id"],
            parent_id=target["parent_id"],
            doc_id=target["doc_id"],
            block_id=f"block-{item.query.query_type}-target",
        ),
        _packed_evidence(
            pack_rank=2,
            source_rank=2,
            child_id=f"child-{item.query.query_type}-distractor-a",
            parent_id=f"parent-{item.query.query_type}-distractor-a",
            doc_id=f"doc-{item.query.query_type}-distractor-a",
            block_id=f"block-{item.query.query_type}-distractor-a",
        ),
        _packed_evidence(
            pack_rank=3,
            source_rank=3,
            child_id=f"child-{item.query.query_type}-distractor-b",
            parent_id=f"parent-{item.query.query_type}-distractor-b",
            doc_id=f"doc-{item.query.query_type}-distractor-b",
            block_id=f"block-{item.query.query_type}-distractor-b",
        ),
    )
    return EvidencePack(
        query_id=item.query.query_id,
        query_type=item.query.query_type,
        policy_id=DEFAULT_PACKING_POLICY_ID,
        context_budget_chars=4200,
        total_estimated_chars=sum(item.estimated_chars for item in evidence),
        evidence=evidence,
        target_child_covered=True,
        target_parent_covered=True,
        target_doc_covered=True,
        evidence_order_relevance_proxy=1.0,
    )


def _packed_evidence(
    *,
    pack_rank: int,
    source_rank: int,
    child_id: str,
    parent_id: str,
    doc_id: str,
    block_id: str,
) -> PackedEvidence:
    return PackedEvidence(
        pack_rank=pack_rank,
        source_rank=source_rank,
        retrieval_doc_id=child_id,
        child_id=child_id,
        parent_id=parent_id,
        doc_id=doc_id,
        score=1.0 - (pack_rank * 0.01),
        estimated_chars=320,
        source_block_ids=(block_id,),
        citation_block_ids=(block_id,),
        citation_recoverable=True,
        packing_reason="retrieval_rank_order",
    )


def _fake_v1_draft(query_type: QueryType) -> CitationRagDraft | None:
    if query_type == "no_answer":
        return None
    return CitationRagDraft(
        answer=f"{query_type} fixture answer with all packed evidence attached as citations.",
        spoken_answer=f"{query_type} fixture spoken answer for selected place context.",
        unsupported_claim_risk="low",
    )


def _fake_v2_draft(query_type: QueryType) -> CitationRagDraftV2:
    return CitationRagDraftV2(
        answer=f"{query_type} fixture answer with selected evidence citations only.",
        spoken_answer=f"{query_type} fixture spoken answer for selected evidence.",
        used_evidence_pack_ranks=(1,),
        coverage_intent="focused",
        unsupported_claim_risk="low",
    )


def _target_ids(query_type: QueryType) -> dict[str, str]:
    return {
        "child_id": f"child-{query_type}-target",
        "parent_id": f"parent-{query_type}-target",
        "doc_id": f"doc-{query_type}-target",
    }


def _format_pair_delta_row(delta: GenerationPolicyPairDelta) -> str:
    return (
        f"| {delta.query_id} | {delta.query_type} | "
        f"{delta.correct_with_evidence_delta} | "
        f"{delta.citation_precision_delta:.6f} | "
        f"{delta.citation_recall_delta:.6f} | "
        f"{delta.unsupported_claim_delta} | "
        f"{delta.citation_count_delta} | "
        f"{delta.latency_ms_delta:.6f} |"
    )


def _format_query_type_delta_row(delta: GenerationPolicyQueryTypeDelta) -> str:
    return (
        f"| {delta.query_type} | {delta.eval_count} | "
        f"{delta.correct_with_evidence_delta:.6f} | "
        f"{delta.citation_precision_delta:.6f} | "
        f"{delta.citation_recall_delta:.6f} | "
        f"{delta.unsupported_claim_rate_delta:.6f} | "
        f"{delta.latency_p95_ms_delta:.6f} |"
    )


def _require_answer_policy(
    inputs: list[GenerationEvalInput],
    *,
    expected: str,
    label: str,
) -> None:
    policies = {item.answer.answer_policy_id for item in inputs}
    if policies != {expected}:
        raise ValueError(f"{label} answer_policy_id must be {expected}")


def _single_value(values: list[str], *, field_name: str) -> str:
    unique_values = set(values)
    if len(unique_values) != 1:
        raise ValueError(f"{field_name} must have exactly one value")
    return next(iter(unique_values))


def _comparison_id_record(record: GenerationEvalRecord) -> dict[str, Any]:
    return {
        "query_id": record.query_id,
        "answer_policy_id": record.answer_policy_id,
        "citation_precision": record.citation_precision,
        "citation_recall": record.citation_recall,
        "citation_count": record.citation_count,
        "provider_config_id": record.provider_config_id,
    }


def _mean_float(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 6)


def _max_float(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(max(values), 6)


def _validate_result_rows_path(path: Path) -> None:
    if has_private_data_segment(path) and not is_repository_private_artifact_path(path):
        raise ValueError("private_data result rows must stay under repository private_data")
    if has_private_data_segment(path) and not is_repository_private_write_path(path):
        raise ValueError("private comparison rows must be written under private_data")


def write_jsonl_rows(*, path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)
    path.write_text(payload + "\n", encoding="utf-8")


def _stable_digest(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"),
    ).hexdigest()[:16]


def main() -> int:
    args = _parse_args()
    report = run_solar_generation_contract_v2_comparison(
        report_path=args.report,
        result_rows_path=args.result_rows,
    )
    failures = collect_solar_generation_contract_v2_comparison_failures(report)
    print(
        "solar_generation_contract_v2_comparison "
        f"status={'PASS' if not failures else 'FAIL'} "
        f"eval_count={report.baseline_report.summary.eval_count} "
        f"citation_precision_delta="
        f"{report.candidate_report.summary.citation_precision - report.baseline_report.summary.citation_precision:.6f} "
        f"solar_call_count={report.baseline_report.summary.solar_call_count + report.candidate_report.summary.solar_call_count} "
        f"failures={len(failures)}",
    )
    return 0 if not failures else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run fake provider Solar Pro 3 generation contract v1/v2 comparison.",
    )
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--result-rows", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
