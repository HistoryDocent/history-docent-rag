from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.application.chat_retrieval import ChatRetrievalBackend, PrivateArtifactRetrievalBackend
from app.core.project_paths import project_path
from app.domain.chunking import ChildChunk
from app.domain.generation import CitationRagAnswer
from app.domain.generation_eval import (
    GenerationEvalInput,
    GenerationEvalReport,
    GenerationEvalUsage,
    build_generation_eval_dataset_fingerprint,
    build_generation_eval_records,
    build_generation_eval_report,
    collect_generation_eval_harness_failures,
)
from app.domain.retrieval import QueryType, RetrievalEvalItem, load_retrieval_eval_jsonl
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    measure_public_retrieval_artifact_quality,
)
from app.providers.llm.base import CitationDraftProvider
from app.providers.llm.solar_pro_3 import (
    CitationDraftPromptPolicyId,
    CitationDraftSchemaVersion,
    SolarPro3CitationDraftProvider,
    SolarPro3ProviderConfig,
)
from pipelines.run_solar_generation_baseline import (
    DEFAULT_ENV_FILE_PATH,
    DEFAULT_QUERY_TYPES,
    SOLAR_GENERATION_BASELINE_ANSWER_POLICY_ID,
    load_env_file_into_process,
    select_generation_baseline_items,
)
from pipelines.run_solar_generation_contract_v2_comparison import (
    DEFAULT_PACKING_POLICY_ID,
    DEFAULT_RETRIEVAL_RUN_LABEL,
    GenerationPolicyPairDelta,
    GenerationPolicyQueryTypeDelta,
    build_generation_policy_pair_deltas,
    build_generation_policy_query_type_deltas,
    build_solar_generation_contract_v2_comparison_id,
)
from pipelines.run_solar_generation_v2_prompt_policy_validator import (
    build_fake_prompt_policy_validation_inputs,
    build_prompt_policy_validation_report,
)
from pipelines.run_solar_generation_v2_repaired_dry_run_readiness import (
    DEFAULT_LIVE_CALL_HARD_CAP,
    REPAIR_ID,
    RepairedRouteDecision,
    SolarGenerationV2RepairedDryRunRow,
    build_solar_generation_v2_repaired_dry_run_readiness_report,
    collect_solar_generation_v2_repaired_dry_run_failures,
)
from pipelines.run_solar_live_generation_smoke import (
    DEFAULT_CHUNKS_PATH,
    DEFAULT_DATASET_PATH,
    SolarLiveProviderUsageTotals,
    _ProviderRunContext,
    _answer_smoke_item,
    _build_eval_inputs,
    _format_query_type_summary_row,
    _load_child_chunks_by_id,
    _provider_endpoint_alias,
    _provider_kind,
    _provider_model_id,
    _validate_result_rows_path,
    write_jsonl_rows,
)


SOLAR_GENERATION_V2_REPAIRED_LIVE_COMPARISON_REPORT_VERSION = (
    "solar-generation-v2-repaired-live-comparison-report/v1"
)
SOLAR_GENERATION_V2_REPAIRED_ANSWER_POLICY_ID = "solar-generation-v2-repaired"
SOLAR_GENERATION_V2_REPAIRED_PROMPT_POLICY_ID: CitationDraftPromptPolicyId = (
    "v2_repair_coverage_floor"
)
DEFAULT_REPORT_PATH = (
    Path("evals") / "reports" / "solar_generation_v2_repaired_live_comparison_report.md"
)
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "solar_generation_v2_repaired_live_comparison_results.jsonl"
)

AdoptionDecision = Literal[
    "promote_repaired_v2_for_next_gate",
    "reject_repaired_v2_default",
]


@dataclass(frozen=True)
class SolarGenerationV2RepairedLiveRunContext:
    dataset_path_alias: str
    chunks_path_alias: str
    retrieval_run_label: str
    packing_policy_id: str
    repair_id: str
    prompt_policy_id: str
    query_types: tuple[QueryType, ...]
    per_query_type: int
    live_call_hard_cap: int
    baseline_usage_totals: SolarLiveProviderUsageTotals
    repaired_usage_totals: SolarLiveProviderUsageTotals
    baseline_model_id: str
    repaired_model_id: str
    baseline_endpoint_alias: str
    repaired_endpoint_alias: str


class SolarGenerationV2RepairedLiveModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SolarGenerationV2RepairedLiveRouteRow(SolarGenerationV2RepairedLiveModel):
    query_id: str = Field(min_length=1)
    query_type: QueryType
    route_decision: RepairedRouteDecision
    validation_status: str = Field(min_length=1)
    prompt_policy_id: str = Field(min_length=1)
    baseline_live_call_required: bool
    repaired_live_call_required: bool
    fallback_reused_baseline_answer: bool
    expected_live_call_count: int = Field(ge=0)
    actual_baseline_solar_call_count: int = Field(ge=0)
    actual_repaired_solar_call_count: int = Field(ge=0)


class SolarGenerationV2RepairedLiveCallSummary(SolarGenerationV2RepairedLiveModel):
    route_count: int = Field(ge=0)
    repaired_candidate_route_count: int = Field(ge=0)
    v1_fallback_route_count: int = Field(ge=0)
    no_answer_route_count: int = Field(ge=0)
    baseline_live_call_count: int = Field(ge=0)
    repaired_candidate_live_call_count: int = Field(ge=0)
    no_answer_live_call_count: int = Field(ge=0)
    expected_total_live_call_count: int = Field(ge=0)
    actual_total_solar_call_count: int = Field(ge=0)
    live_call_hard_cap: int = Field(ge=1)
    hard_cap_exceeded: bool
    correct_with_evidence_delta: float
    citation_precision_delta: float
    citation_recall_delta: float
    unsupported_claim_rate_delta: float
    abstention_accuracy_delta: float
    latency_p95_ms_delta: float
    adoption_decision: AdoptionDecision


class SolarGenerationV2RepairedLiveComparisonReport(SolarGenerationV2RepairedLiveModel):
    report_version: str = SOLAR_GENERATION_V2_REPAIRED_LIVE_COMPARISON_REPORT_VERSION
    comparison_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    dataset_fingerprint: str = Field(min_length=8)
    readiness_id: str = Field(min_length=1)
    repair_id: str = Field(min_length=1)
    retrieval_run_label: str = Field(min_length=1)
    packing_policy_id: str = Field(min_length=1)
    baseline_answer_policy_id: str = Field(min_length=1)
    repaired_answer_policy_id: str = Field(min_length=1)
    repaired_prompt_policy_id: str = Field(min_length=1)
    baseline_provider_config_id: str = Field(min_length=1)
    repaired_provider_config_id: str = Field(min_length=1)
    baseline_report: GenerationEvalReport
    repaired_report: GenerationEvalReport
    paired_deltas: tuple[GenerationPolicyPairDelta, ...]
    query_type_deltas: tuple[GenerationPolicyQueryTypeDelta, ...]
    route_rows: tuple[SolarGenerationV2RepairedLiveRouteRow, ...]
    route_decision_distribution: dict[str, int]
    live_call_summary: SolarGenerationV2RepairedLiveCallSummary
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def run_solar_generation_v2_repaired_live_comparison(
    *,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    chunks_path: Path = DEFAULT_CHUNKS_PATH,
    env_file_path: Path | None = DEFAULT_ENV_FILE_PATH,
    per_query_type: int = 1,
    query_types: tuple[QueryType, ...] = DEFAULT_QUERY_TYPES,
    live_call_hard_cap: int = DEFAULT_LIVE_CALL_HARD_CAP,
    retrieval_backend: ChatRetrievalBackend | None = None,
    baseline_draft_provider: CitationDraftProvider | None = None,
    repaired_draft_provider: CitationDraftProvider | None = None,
) -> SolarGenerationV2RepairedLiveComparisonReport:
    _validate_result_rows_path(result_rows_path)
    readiness = build_solar_generation_v2_repaired_dry_run_readiness_report(
        validation_report=build_prompt_policy_validation_report(
            inputs=build_fake_prompt_policy_validation_inputs(),
        ),
        live_call_hard_cap=live_call_hard_cap,
    )
    readiness_failures = collect_solar_generation_v2_repaired_dry_run_failures(readiness)
    if readiness_failures:
        raise ValueError(f"repaired v2 readiness gate failed: {readiness_failures}")
    if (
        baseline_draft_provider is None or repaired_draft_provider is None
    ) and env_file_path is not None:
        load_env_file_into_process(env_file_path)

    baseline_provider, baseline_context = _build_live_provider_context(
        baseline_draft_provider,
        schema_version="v1",
    )
    repaired_provider, repaired_context = _build_live_provider_context(
        repaired_draft_provider,
        schema_version="v2",
        prompt_policy_id=SOLAR_GENERATION_V2_REPAIRED_PROMPT_POLICY_ID,
    )
    resolved_dataset_path = project_path(dataset_path)
    resolved_chunks_path = project_path(chunks_path)
    items = select_generation_baseline_items(
        load_retrieval_eval_jsonl(resolved_dataset_path),
        query_types=query_types,
        per_query_type=per_query_type,
    )
    _validate_selected_items_against_readiness(items=items, readiness_rows=readiness.rows)
    child_chunks_by_id = _load_child_chunks_by_id(resolved_chunks_path)
    backend = retrieval_backend or PrivateArtifactRetrievalBackend(chunks_path=chunks_path)

    baseline_inputs, baseline_answers, baseline_usage_by_query_id, baseline_usage_totals = (
        _build_baseline_inputs(
            items=items,
            retrieval_backend=backend,
            draft_provider=baseline_provider,
            child_chunks_by_id=child_chunks_by_id,
            provider_context=baseline_context,
        )
    )
    repaired_inputs, repaired_usage_totals = _build_repaired_inputs(
        items=items,
        retrieval_backend=backend,
        draft_provider=repaired_provider,
        child_chunks_by_id=child_chunks_by_id,
        provider_context=repaired_context,
        route_by_query_id={row.query_id: row for row in readiness.rows},
        baseline_answers=baseline_answers,
        baseline_usage_by_query_id=baseline_usage_by_query_id,
    )
    context = SolarGenerationV2RepairedLiveRunContext(
        dataset_path_alias="<private retrieval eval dataset: retrieval_eval_dev.jsonl>",
        chunks_path_alias="<private parent_child_chunks report>",
        retrieval_run_label=DEFAULT_RETRIEVAL_RUN_LABEL,
        packing_policy_id=DEFAULT_PACKING_POLICY_ID,
        repair_id=REPAIR_ID,
        prompt_policy_id=SOLAR_GENERATION_V2_REPAIRED_PROMPT_POLICY_ID,
        query_types=query_types,
        per_query_type=per_query_type,
        live_call_hard_cap=live_call_hard_cap,
        baseline_usage_totals=baseline_usage_totals,
        repaired_usage_totals=repaired_usage_totals,
        baseline_model_id=baseline_context.model_id,
        repaired_model_id=repaired_context.model_id,
        baseline_endpoint_alias=baseline_context.endpoint_alias,
        repaired_endpoint_alias=repaired_context.endpoint_alias,
    )
    provisional = build_solar_generation_v2_repaired_live_comparison_report(
        baseline_inputs=baseline_inputs,
        repaired_inputs=repaired_inputs,
        readiness_rows=readiness.rows,
        readiness_id=readiness.readiness_id,
        context=context,
    )
    provisional_markdown = build_solar_generation_v2_repaired_live_comparison_markdown(
        provisional,
        context=context,
    )
    report = build_solar_generation_v2_repaired_live_comparison_report(
        baseline_inputs=baseline_inputs,
        repaired_inputs=repaired_inputs,
        readiness_rows=readiness.rows,
        readiness_id=readiness.readiness_id,
        context=context,
        report_text=provisional_markdown,
    )
    failures = collect_solar_generation_v2_repaired_live_comparison_failures(report)
    if failures:
        raise ValueError(
            f"solar generation v2 repaired live comparison gate failed: {failures}",
        )

    rows = build_public_solar_generation_v2_repaired_live_comparison_rows(report)
    write_jsonl_rows(path=result_rows_path, rows=rows)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        build_solar_generation_v2_repaired_live_comparison_markdown(
            report,
            context=context,
        ),
        encoding="utf-8",
    )
    return report


def build_solar_generation_v2_repaired_live_comparison_report(
    *,
    baseline_inputs: list[GenerationEvalInput],
    repaired_inputs: list[GenerationEvalInput],
    readiness_rows: tuple[SolarGenerationV2RepairedDryRunRow, ...],
    readiness_id: str,
    context: SolarGenerationV2RepairedLiveRunContext,
    report_text: str = "",
) -> SolarGenerationV2RepairedLiveComparisonReport:
    _validate_repaired_live_inputs(
        baseline_inputs=baseline_inputs,
        repaired_inputs=repaired_inputs,
    )
    baseline_report = build_generation_eval_report(inputs=baseline_inputs)
    repaired_report = build_generation_eval_report(inputs=repaired_inputs)
    baseline_records = build_generation_eval_records(baseline_inputs)
    repaired_records = build_generation_eval_records(repaired_inputs)
    paired_deltas = tuple(
        build_generation_policy_pair_deltas(
            baseline_records=baseline_records,
            candidate_records=repaired_records,
        ),
    )
    query_type_deltas = tuple(build_generation_policy_query_type_deltas(paired_deltas))
    route_rows = tuple(
        build_repaired_live_route_row(
            readiness_row=row,
            baseline_inputs=baseline_inputs,
            repaired_inputs=repaired_inputs,
        )
        for row in readiness_rows
        if row.query_id in {item.item.query.query_id for item in baseline_inputs}
    )
    live_call_summary = build_repaired_live_call_summary(
        route_rows=route_rows,
        baseline_report=baseline_report,
        repaired_report=repaired_report,
        live_call_hard_cap=context.live_call_hard_cap,
    )
    public_rows = build_public_solar_generation_v2_repaired_live_rows_from_parts(
        paired_deltas=paired_deltas,
        route_rows=route_rows,
    )
    comparison_id = build_solar_generation_contract_v2_comparison_id(
        baseline_records=baseline_records,
        candidate_records=repaired_records,
    )
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=SOLAR_GENERATION_V2_REPAIRED_LIVE_COMPARISON_REPORT_VERSION,
        run_id=comparison_id,
        result_rows=public_rows,
        report_text=report_text,
    )
    report = SolarGenerationV2RepairedLiveComparisonReport(
        comparison_id=comparison_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        dataset_fingerprint=build_generation_eval_dataset_fingerprint(baseline_inputs),
        readiness_id=readiness_id,
        repair_id=context.repair_id,
        retrieval_run_label=context.retrieval_run_label,
        packing_policy_id=context.packing_policy_id,
        baseline_answer_policy_id=SOLAR_GENERATION_BASELINE_ANSWER_POLICY_ID,
        repaired_answer_policy_id=SOLAR_GENERATION_V2_REPAIRED_ANSWER_POLICY_ID,
        repaired_prompt_policy_id=context.prompt_policy_id,
        baseline_provider_config_id=_single_provider_config_id(
            baseline_inputs,
            field_name="baseline_provider_config_id",
        ),
        repaired_provider_config_id=_single_provider_config_id(
            repaired_inputs,
            field_name="repaired_provider_config_id",
        ),
        baseline_report=baseline_report,
        repaired_report=repaired_report,
        paired_deltas=paired_deltas,
        query_type_deltas=query_type_deltas,
        route_rows=route_rows,
        route_decision_distribution=dict(
            sorted(Counter(row.route_decision for row in route_rows).items()),
        ),
        live_call_summary=live_call_summary,
        output_quality=output_quality,
        qualitative_assessment={},
    )
    return report.model_copy(
        update={
            "qualitative_assessment": build_repaired_live_qualitative_assessment(report),
        },
    )


def build_repaired_live_route_row(
    *,
    readiness_row: SolarGenerationV2RepairedDryRunRow,
    baseline_inputs: list[GenerationEvalInput],
    repaired_inputs: list[GenerationEvalInput],
) -> SolarGenerationV2RepairedLiveRouteRow:
    baseline_by_query_id = {item.item.query.query_id: item for item in baseline_inputs}
    repaired_by_query_id = {item.item.query.query_id: item for item in repaired_inputs}
    baseline = baseline_by_query_id[readiness_row.query_id]
    repaired = repaired_by_query_id[readiness_row.query_id]
    return SolarGenerationV2RepairedLiveRouteRow(
        query_id=readiness_row.query_id,
        query_type=readiness_row.query_type,
        route_decision=readiness_row.route_decision,
        validation_status=readiness_row.validation_status,
        prompt_policy_id=readiness_row.prompt_policy_id,
        baseline_live_call_required=readiness_row.baseline_live_call_required,
        repaired_live_call_required=readiness_row.repaired_live_call_required,
        fallback_reused_baseline_answer=readiness_row.route_decision == "use_v1_fallback",
        expected_live_call_count=readiness_row.expected_live_call_count,
        actual_baseline_solar_call_count=baseline.usage.solar_call_count,
        actual_repaired_solar_call_count=repaired.usage.solar_call_count,
    )


def build_repaired_live_call_summary(
    *,
    route_rows: tuple[SolarGenerationV2RepairedLiveRouteRow, ...],
    baseline_report: GenerationEvalReport,
    repaired_report: GenerationEvalReport,
    live_call_hard_cap: int,
) -> SolarGenerationV2RepairedLiveCallSummary:
    expected_total = sum(row.expected_live_call_count for row in route_rows)
    actual_total = (
        baseline_report.summary.solar_call_count + repaired_report.summary.solar_call_count
    )
    correct_delta = (
        repaired_report.summary.correct_with_evidence_rate
        - baseline_report.summary.correct_with_evidence_rate
    )
    precision_delta = (
        repaired_report.summary.citation_precision - baseline_report.summary.citation_precision
    )
    recall_delta = repaired_report.summary.citation_recall - baseline_report.summary.citation_recall
    unsupported_delta = (
        repaired_report.summary.unsupported_claim_rate
        - baseline_report.summary.unsupported_claim_rate
    )
    abstention_delta = (
        repaired_report.summary.abstention_accuracy - baseline_report.summary.abstention_accuracy
    )
    latency_delta = repaired_report.summary.latency_p95_ms - baseline_report.summary.latency_p95_ms
    return SolarGenerationV2RepairedLiveCallSummary(
        route_count=len(route_rows),
        repaired_candidate_route_count=sum(
            1 for row in route_rows if row.route_decision == "use_repaired_v2_candidate"
        ),
        v1_fallback_route_count=sum(
            1 for row in route_rows if row.route_decision == "use_v1_fallback"
        ),
        no_answer_route_count=sum(
            1 for row in route_rows if row.route_decision == "abstain_no_live_call"
        ),
        baseline_live_call_count=baseline_report.summary.solar_call_count,
        repaired_candidate_live_call_count=repaired_report.summary.solar_call_count,
        no_answer_live_call_count=sum(
            row.actual_baseline_solar_call_count + row.actual_repaired_solar_call_count
            for row in route_rows
            if row.query_type == "no_answer"
        ),
        expected_total_live_call_count=expected_total,
        actual_total_solar_call_count=actual_total,
        live_call_hard_cap=live_call_hard_cap,
        hard_cap_exceeded=actual_total > live_call_hard_cap or expected_total > live_call_hard_cap,
        correct_with_evidence_delta=round(correct_delta, 6),
        citation_precision_delta=round(precision_delta, 6),
        citation_recall_delta=round(recall_delta, 6),
        unsupported_claim_rate_delta=round(unsupported_delta, 6),
        abstention_accuracy_delta=round(abstention_delta, 6),
        latency_p95_ms_delta=round(latency_delta, 6),
        adoption_decision=_adoption_decision(
            correct_delta=correct_delta,
            precision_delta=precision_delta,
            recall_delta=recall_delta,
            unsupported_delta=unsupported_delta,
            abstention_delta=abstention_delta,
        ),
    )


def build_public_solar_generation_v2_repaired_live_comparison_rows(
    report: SolarGenerationV2RepairedLiveComparisonReport,
) -> list[dict[str, Any]]:
    return build_public_solar_generation_v2_repaired_live_rows_from_parts(
        paired_deltas=report.paired_deltas,
        route_rows=report.route_rows,
    )


def build_public_solar_generation_v2_repaired_live_rows_from_parts(
    *,
    paired_deltas: tuple[GenerationPolicyPairDelta, ...],
    route_rows: tuple[SolarGenerationV2RepairedLiveRouteRow, ...],
) -> list[dict[str, Any]]:
    route_by_query_id = {row.query_id: row for row in route_rows}
    return [
        {
            "query_id": delta.query_id,
            "query_type": delta.query_type,
            "baseline_answer_policy_id": SOLAR_GENERATION_BASELINE_ANSWER_POLICY_ID,
            "repaired_answer_policy_id": SOLAR_GENERATION_V2_REPAIRED_ANSWER_POLICY_ID,
            "route_decision": route_by_query_id[delta.query_id].route_decision,
            "fallback_reused_baseline_answer": (
                route_by_query_id[delta.query_id].fallback_reused_baseline_answer
            ),
            "baseline_solar_call_count": (
                route_by_query_id[delta.query_id].actual_baseline_solar_call_count
            ),
            "repaired_solar_call_count": (
                route_by_query_id[delta.query_id].actual_repaired_solar_call_count
            ),
            "v1_correct_with_evidence": delta.v1_correct_with_evidence,
            "repaired_correct_with_evidence": delta.v2_correct_with_evidence,
            "correct_with_evidence_delta": delta.correct_with_evidence_delta,
            "v1_citation_precision": delta.v1_citation_precision,
            "repaired_citation_precision": delta.v2_citation_precision,
            "citation_precision_delta": delta.citation_precision_delta,
            "v1_citation_recall": delta.v1_citation_recall,
            "repaired_citation_recall": delta.v2_citation_recall,
            "citation_recall_delta": delta.citation_recall_delta,
            "unsupported_claim_delta": delta.unsupported_claim_delta,
            "v1_citation_count": delta.v1_citation_count,
            "repaired_citation_count": delta.v2_citation_count,
            "citation_count_delta": delta.citation_count_delta,
            "latency_ms_delta": delta.latency_ms_delta,
        }
        for delta in paired_deltas
    ]


def collect_solar_generation_v2_repaired_live_comparison_failures(
    report: SolarGenerationV2RepairedLiveComparisonReport,
) -> list[str]:
    failures: list[str] = []
    failures.extend(
        f"baseline_{failure}"
        for failure in collect_generation_eval_harness_failures(report.baseline_report)
    )
    failures.extend(
        f"repaired_{failure}"
        for failure in collect_generation_eval_harness_failures(report.repaired_report)
    )
    summary = report.live_call_summary
    if report.baseline_report.summary.eval_count != report.repaired_report.summary.eval_count:
        failures.append("mismatched_eval_count")
    if not report.paired_deltas:
        failures.append("empty_paired_delta")
    if summary.route_count != report.baseline_report.summary.eval_count:
        failures.append("route_count_mismatch")
    if summary.baseline_live_call_count != sum(
        1 for row in report.route_rows if row.baseline_live_call_required
    ):
        failures.append("baseline_live_call_count_mismatch")
    if summary.repaired_candidate_live_call_count != sum(
        1 for row in report.route_rows if row.repaired_live_call_required
    ):
        failures.append("repaired_live_call_count_mismatch")
    if summary.no_answer_live_call_count:
        failures.append("no_answer_live_call_must_be_zero")
    if summary.actual_total_solar_call_count != summary.expected_total_live_call_count:
        failures.append("actual_live_call_count_mismatch")
    if summary.hard_cap_exceeded:
        failures.append("live_call_hard_cap_exceeded")
    if report.output_quality.public_raw_text_leakage_count:
        failures.append("public_raw_text_leakage")
    if report.output_quality.private_path_leakage_count:
        failures.append("private_path_leakage")
    if report.output_quality.secret_like_leakage_count:
        failures.append("secret_like_leakage")
    if report.output_quality.forbidden_result_field_count:
        failures.append("forbidden_public_result_fields")
    return failures


def build_solar_generation_v2_repaired_live_comparison_markdown(
    report: SolarGenerationV2RepairedLiveComparisonReport,
    *,
    context: SolarGenerationV2RepairedLiveRunContext,
) -> str:
    baseline = report.baseline_report.summary
    repaired = report.repaired_report.summary
    call_summary = report.live_call_summary
    quality = report.output_quality
    paired_rows = "\n".join(_format_pair_delta_row(delta) for delta in report.paired_deltas)
    query_type_rows = "\n".join(
        _format_query_type_delta_row(delta) for delta in report.query_type_deltas
    )
    route_rows = "\n".join(_format_route_row(row) for row in report.route_rows)
    route_distribution_rows = "\n".join(
        f"| `{decision}` | {count} |"
        for decision, count in report.route_decision_distribution.items()
    )
    baseline_breakdown_rows = "\n".join(
        _format_query_type_summary_row(row) for row in report.baseline_report.query_type_breakdown
    )
    repaired_breakdown_rows = "\n".join(
        _format_query_type_summary_row(row) for row in report.repaired_report.query_type_breakdown
    )
    qualitative_rows = "\n".join(
        f"- `{key}`: {value}" for key, value in report.qualitative_assessment.items()
    )
    query_type_text = ", ".join(context.query_types)
    return f"""# Solar Pro 3 Generation v2 Repaired Live Comparison Report

## 목적

Solar Pro 3 실제 호출로 v1 baseline과 repaired v2 routed policy를 같은 query set, 같은 retrieval label, 같은 evidence packing policy에서 paired comparison으로 비교한다.

이 문서는 private dev subset 기반 실험 결과다. 최종 성능 개선 주장이 아니라 repaired v2를 기본값으로 채택할 수 있는지 판단하기 위한 근거다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| comparison_id | `{report.comparison_id}` |
| generated_at_utc | `{report.generated_at_utc}` |
| dataset_fingerprint | `{report.dataset_fingerprint}` |
| readiness_id | `{report.readiness_id}` |
| repair_id | `{report.repair_id}` |
| dataset_path | `{context.dataset_path_alias}` |
| chunks_path | `{context.chunks_path_alias}` |
| retrieval_run_label | `{report.retrieval_run_label}` |
| packing_policy_id | `{report.packing_policy_id}` |
| baseline_answer_policy_id | `{report.baseline_answer_policy_id}` |
| repaired_answer_policy_id | `{report.repaired_answer_policy_id}` |
| repaired_prompt_policy_id | `{report.repaired_prompt_policy_id}` |
| baseline_provider_config_id | `{report.baseline_provider_config_id}` |
| repaired_provider_config_id | `{report.repaired_provider_config_id}` |
| baseline_model_id | `{context.baseline_model_id}` |
| repaired_model_id | `{context.repaired_model_id}` |
| baseline_endpoint_alias | `{context.baseline_endpoint_alias}` |
| repaired_endpoint_alias | `{context.repaired_endpoint_alias}` |
| per_query_type | {context.per_query_type} |
| query_types | `{query_type_text}` |

## 정량 리포트

| metric | v1 baseline | repaired v2 routed | delta |
| --- | ---: | ---: | ---: |
| eval_count | {baseline.eval_count} | {repaired.eval_count} | {repaired.eval_count - baseline.eval_count} |
| Correct-with-Evidence | {baseline.correct_with_evidence_rate:.6f} | {repaired.correct_with_evidence_rate:.6f} | {call_summary.correct_with_evidence_delta:.6f} |
| citation_precision | {baseline.citation_precision:.6f} | {repaired.citation_precision:.6f} | {call_summary.citation_precision_delta:.6f} |
| citation_recall | {baseline.citation_recall:.6f} | {repaired.citation_recall:.6f} | {call_summary.citation_recall_delta:.6f} |
| place_relevance | {baseline.place_relevance:.6f} | {repaired.place_relevance:.6f} | {repaired.place_relevance - baseline.place_relevance:.6f} |
| docent_usefulness | {baseline.docent_usefulness:.6f} | {repaired.docent_usefulness:.6f} | {repaired.docent_usefulness - baseline.docent_usefulness:.6f} |
| spoken_answer_naturalness | {baseline.spoken_answer_naturalness:.6f} | {repaired.spoken_answer_naturalness:.6f} | {repaired.spoken_answer_naturalness - baseline.spoken_answer_naturalness:.6f} |
| unsupported_claim_rate | {baseline.unsupported_claim_rate:.6f} | {repaired.unsupported_claim_rate:.6f} | {call_summary.unsupported_claim_rate_delta:.6f} |
| abstention_accuracy | {baseline.abstention_accuracy:.6f} | {repaired.abstention_accuracy:.6f} | {call_summary.abstention_accuracy_delta:.6f} |
| latency_p95_ms | {baseline.latency_p95_ms:.6f} | {repaired.latency_p95_ms:.6f} | {call_summary.latency_p95_ms_delta:.6f} |
| solar_call_count | {baseline.solar_call_count} | {repaired.solar_call_count} | {repaired.solar_call_count - baseline.solar_call_count} |
| prompt_tokens | {context.baseline_usage_totals.prompt_tokens} | {context.repaired_usage_totals.prompt_tokens} | {context.repaired_usage_totals.prompt_tokens - context.baseline_usage_totals.prompt_tokens} |
| completion_tokens | {context.baseline_usage_totals.completion_tokens} | {context.repaired_usage_totals.completion_tokens} | {context.repaired_usage_totals.completion_tokens - context.baseline_usage_totals.completion_tokens} |
| total_tokens | {context.baseline_usage_totals.total_tokens} | {context.repaired_usage_totals.total_tokens} | {context.repaired_usage_totals.total_tokens - context.baseline_usage_totals.total_tokens} |
| estimated_cost | {baseline.estimated_cost:.6f} | {repaired.estimated_cost:.6f} | {repaired.estimated_cost - baseline.estimated_cost:.6f} |
| missing_citation_count | {baseline.missing_citation_count} | {repaired.missing_citation_count} | {repaired.missing_citation_count - baseline.missing_citation_count} |
| unsupported_high_count | {baseline.unsupported_high_count} | {repaired.unsupported_high_count} | {repaired.unsupported_high_count - baseline.unsupported_high_count} |

## Live Call Summary

| metric | value |
| --- | ---: |
| route_count | {call_summary.route_count} |
| repaired_candidate_route_count | {call_summary.repaired_candidate_route_count} |
| v1_fallback_route_count | {call_summary.v1_fallback_route_count} |
| no_answer_route_count | {call_summary.no_answer_route_count} |
| baseline_live_call_count | {call_summary.baseline_live_call_count} |
| repaired_candidate_live_call_count | {call_summary.repaired_candidate_live_call_count} |
| no_answer_live_call_count | {call_summary.no_answer_live_call_count} |
| expected_total_live_call_count | {call_summary.expected_total_live_call_count} |
| actual_total_solar_call_count | {call_summary.actual_total_solar_call_count} |
| live_call_hard_cap | {call_summary.live_call_hard_cap} |
| hard_cap_exceeded | {call_summary.hard_cap_exceeded} |
| adoption_decision | `{call_summary.adoption_decision}` |

## Route Decision Distribution

| route_decision | count |
| --- | ---: |
{route_distribution_rows}

## Route Rows

| query_id | query_type | route_decision | baseline_call | repaired_call | fallback_reused | expected_calls | actual_baseline_calls | actual_repaired_calls |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
{route_rows}

## Baseline Query Type Breakdown

| query_type | eval_count | answerable_count | Correct-with-Evidence | citation_precision | citation_recall | place_relevance | docent_usefulness | spoken_answer_naturalness | unsupported_claim_rate | abstention_accuracy | latency_p95_ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{baseline_breakdown_rows}

## Repaired Query Type Breakdown

| query_type | eval_count | answerable_count | Correct-with-Evidence | citation_precision | citation_recall | place_relevance | docent_usefulness | spoken_answer_naturalness | unsupported_claim_rate | abstention_accuracy | latency_p95_ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{repaired_breakdown_rows}

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

repaired v2 routed policy는 `place_story`를 v1 fallback으로 처리하고, `no_answer`는 provider 호출 없이 abstain한다.

이 결과는 private dev subset의 live paired comparison이다. 포트폴리오에는 채택/기각 판단 과정으로만 쓰고, 최종 개선 주장은 locked test와 confidence interval을 붙인 뒤에만 사용한다.
"""


def build_repaired_live_qualitative_assessment(
    report: SolarGenerationV2RepairedLiveComparisonReport,
) -> dict[str, str]:
    failures = collect_solar_generation_v2_repaired_live_comparison_failures(report)
    return {
        "comparison_scope": (
            "v1 baseline과 repaired v2 routed policy를 같은 query set, retrieval label, packing policy에서 비교했다."
        ),
        "provider_boundary": (
            "이번 runner는 Solar Pro 3 live API를 호출했다. no_answer query는 provider를 호출하지 않았다."
        ),
        "fallback_boundary": (
            "place_story는 repaired v2 후보에서 제외하고 v1 fallback answer를 재사용했다."
        ),
        "metric_grain": (
            "`fact_solar_generation_v2_repaired_live_eval`의 grain은 repair_id-query_id-route_decision-answer_policy_id-metric_family다."
        ),
        "call_budget": (
            f"actual_total_solar_call_count={report.live_call_summary.actual_total_solar_call_count}, "
            f"hard_cap={report.live_call_summary.live_call_hard_cap}로 제한했다."
        ),
        "adoption_boundary": (
            f"adoption_decision={report.live_call_summary.adoption_decision}. dev subset 결과라 production 채택 주장이 아니다."
        ),
        "public_policy": (
            "public report와 result row에는 raw query, raw answer, evidence text, chunk text, private path, secret을 저장하지 않는다."
        ),
        "external_audit": (
            "route/fallback/call budget과 품질 metric을 분리해 비용 통제와 claim boundary를 유지했다."
        ),
        "gate_status": "PASS" if not failures else f"FAIL: {', '.join(failures)}",
    }


def _build_baseline_inputs(
    *,
    items: list[RetrievalEvalItem],
    retrieval_backend: ChatRetrievalBackend,
    draft_provider: CitationDraftProvider,
    child_chunks_by_id: dict[str, ChildChunk],
    provider_context: _ProviderRunContext,
) -> tuple[
    list[GenerationEvalInput],
    dict[str, CitationRagAnswer],
    dict[str, GenerationEvalUsage],
    SolarLiveProviderUsageTotals,
]:
    answers: list[CitationRagAnswer] = []
    usage_by_query_id: dict[str, GenerationEvalUsage] = {}
    usage_totals = SolarLiveProviderUsageTotals()
    for item in items:
        answer, usage, provider_usage = _answer_smoke_item(
            item=item,
            retrieval_backend=retrieval_backend,
            draft_provider=draft_provider,
            child_chunks_by_id=child_chunks_by_id,
            provider_context=provider_context,
            answer_policy_id=SOLAR_GENERATION_BASELINE_ANSWER_POLICY_ID,
        )
        answers.append(answer)
        usage_by_query_id[item.query.query_id] = usage
        usage_totals = usage_totals.add(provider_usage)
    return (
        _build_eval_inputs(
            items=items,
            answers=answers,
            provider_config_id=provider_context.provider_config_id,
            usage_by_query_id=usage_by_query_id,
        ),
        {answer.query_id: answer for answer in answers},
        usage_by_query_id,
        usage_totals,
    )


def _build_repaired_inputs(
    *,
    items: list[RetrievalEvalItem],
    retrieval_backend: ChatRetrievalBackend,
    draft_provider: CitationDraftProvider,
    child_chunks_by_id: dict[str, ChildChunk],
    provider_context: _ProviderRunContext,
    route_by_query_id: dict[str, SolarGenerationV2RepairedDryRunRow],
    baseline_answers: dict[str, CitationRagAnswer],
    baseline_usage_by_query_id: dict[str, GenerationEvalUsage],
) -> tuple[list[GenerationEvalInput], SolarLiveProviderUsageTotals]:
    answers: list[CitationRagAnswer] = []
    usage_by_query_id: dict[str, GenerationEvalUsage] = {}
    usage_totals = SolarLiveProviderUsageTotals()
    for item in items:
        route = route_by_query_id[item.query.query_id]
        if route.route_decision == "use_v1_fallback":
            answers.append(
                _clone_answer_for_repaired_policy(baseline_answers[item.query.query_id]),
            )
            usage_by_query_id[item.query.query_id] = _fallback_usage(
                baseline_usage_by_query_id[item.query.query_id],
            )
            continue
        if route.route_decision == "blocked_by_validator_failure":
            raise ValueError(f"blocked route cannot be executed: {item.query.query_id}")
        answer, usage, provider_usage = _answer_smoke_item(
            item=item,
            retrieval_backend=retrieval_backend,
            draft_provider=draft_provider,
            child_chunks_by_id=child_chunks_by_id,
            provider_context=provider_context,
            answer_policy_id=SOLAR_GENERATION_V2_REPAIRED_ANSWER_POLICY_ID,
        )
        answers.append(answer)
        usage_by_query_id[item.query.query_id] = usage
        usage_totals = usage_totals.add(provider_usage)
    return (
        _build_eval_inputs(
            items=items,
            answers=answers,
            provider_config_id=provider_context.provider_config_id,
            usage_by_query_id=usage_by_query_id,
        ),
        usage_totals,
    )


def _clone_answer_for_repaired_policy(answer: CitationRagAnswer) -> CitationRagAnswer:
    return answer.model_copy(
        update={
            "answer_policy_id": SOLAR_GENERATION_V2_REPAIRED_ANSWER_POLICY_ID,
        },
    )


def _fallback_usage(baseline_usage: GenerationEvalUsage) -> GenerationEvalUsage:
    return GenerationEvalUsage(
        latency_ms=baseline_usage.latency_ms,
        solar_call_count=0,
        estimated_cost=0.0,
    )


def _build_live_provider_context(
    draft_provider: CitationDraftProvider | None,
    *,
    schema_version: CitationDraftSchemaVersion,
    prompt_policy_id: CitationDraftPromptPolicyId = "default",
) -> tuple[CitationDraftProvider, _ProviderRunContext]:
    if draft_provider is not None:
        return draft_provider, _ProviderRunContext(
            provider_config_id=draft_provider.provider_config_id,
            provider_kind=_provider_kind(draft_provider),
            model_id=_provider_model_id(draft_provider),
            endpoint_alias=_provider_endpoint_alias(draft_provider),
        )
    config = SolarPro3ProviderConfig.from_env(
        draft_schema_version=schema_version,
        prompt_policy_id=prompt_policy_id,
    )
    provider = SolarPro3CitationDraftProvider(config=config)
    return provider, _ProviderRunContext(
        provider_config_id=config.provider_config_id,
        provider_kind="solar_pro_3",
        model_id=config.model_id,
        endpoint_alias=config.endpoint.replace("https://", "").replace("http://", ""),
    )


def _validate_repaired_live_inputs(
    *,
    baseline_inputs: list[GenerationEvalInput],
    repaired_inputs: list[GenerationEvalInput],
) -> None:
    if not baseline_inputs or not repaired_inputs:
        raise ValueError("repaired live comparison requires non-empty inputs")
    baseline_by_query_id = {item.item.query.query_id: item for item in baseline_inputs}
    repaired_by_query_id = {item.item.query.query_id: item for item in repaired_inputs}
    if set(baseline_by_query_id) != set(repaired_by_query_id):
        raise ValueError("repaired live comparison requires identical query_id set")
    if build_generation_eval_dataset_fingerprint(
        baseline_inputs,
    ) != build_generation_eval_dataset_fingerprint(repaired_inputs):
        raise ValueError("repaired live comparison requires identical eval dataset")
    for query_id, baseline in baseline_by_query_id.items():
        repaired = repaired_by_query_id[query_id]
        if baseline.item.query.query_type != repaired.item.query.query_type:
            raise ValueError("repaired live comparison requires identical query_type")
        if baseline.packing_policy_id != repaired.packing_policy_id:
            raise ValueError("repaired live comparison requires identical packing_policy_id")
        if baseline.retrieval_run_label != repaired.retrieval_run_label:
            raise ValueError("repaired live comparison requires identical retrieval_run_label")
    _require_answer_policy(
        baseline_inputs,
        expected=SOLAR_GENERATION_BASELINE_ANSWER_POLICY_ID,
        label="baseline",
    )
    _require_answer_policy(
        repaired_inputs,
        expected=SOLAR_GENERATION_V2_REPAIRED_ANSWER_POLICY_ID,
        label="repaired",
    )


def _validate_selected_items_against_readiness(
    *,
    items: list[RetrievalEvalItem],
    readiness_rows: tuple[SolarGenerationV2RepairedDryRunRow, ...],
) -> None:
    readiness_by_query_id = {row.query_id: row for row in readiness_rows}
    missing = sorted(
        item.query.query_id for item in items if item.query.query_id not in readiness_by_query_id
    )
    if missing:
        raise ValueError(f"selected query_ids are not in repaired readiness: {missing}")


def _adoption_decision(
    *,
    correct_delta: float,
    precision_delta: float,
    recall_delta: float,
    unsupported_delta: float,
    abstention_delta: float,
) -> AdoptionDecision:
    if (
        correct_delta >= 0
        and precision_delta >= 0
        and recall_delta >= 0
        and unsupported_delta <= 0
        and abstention_delta >= 0
    ):
        return "promote_repaired_v2_for_next_gate"
    return "reject_repaired_v2_default"


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


def _format_route_row(row: SolarGenerationV2RepairedLiveRouteRow) -> str:
    return (
        f"| {row.query_id} | {row.query_type} | `{row.route_decision}` | "
        f"{row.baseline_live_call_required} | {row.repaired_live_call_required} | "
        f"{row.fallback_reused_baseline_answer} | {row.expected_live_call_count} | "
        f"{row.actual_baseline_solar_call_count} | {row.actual_repaired_solar_call_count} |"
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


def _single_provider_config_id(
    inputs: list[GenerationEvalInput],
    *,
    field_name: str,
) -> str:
    values = {item.provider_config_id for item in inputs}
    if len(values) != 1:
        raise ValueError(f"{field_name} must have exactly one value")
    return next(iter(values))


def _stable_digest(payload: Any, *, length: int = 12) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"),
    ).hexdigest()[:length]


def main() -> int:
    args = _parse_args()
    report = run_solar_generation_v2_repaired_live_comparison(
        report_path=args.report,
        result_rows_path=args.result_rows,
        dataset_path=args.dataset,
        chunks_path=args.chunks,
        per_query_type=args.per_query_type,
        live_call_hard_cap=args.live_call_hard_cap,
    )
    failures = collect_solar_generation_v2_repaired_live_comparison_failures(report)
    summary = report.live_call_summary
    print(
        "solar_generation_v2_repaired_live_comparison "
        f"status={'PASS' if not failures else 'FAIL'} "
        f"eval_count={report.baseline_report.summary.eval_count} "
        f"correct_delta={summary.correct_with_evidence_delta:.6f} "
        f"citation_precision_delta={summary.citation_precision_delta:.6f} "
        f"citation_recall_delta={summary.citation_recall_delta:.6f} "
        f"unsupported_delta={summary.unsupported_claim_rate_delta:.6f} "
        f"solar_call_count={summary.actual_total_solar_call_count} "
        f"adoption_decision={summary.adoption_decision} "
        f"failures={len(failures)}",
    )
    return 0 if not failures else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run live Solar Pro 3 generation v1/repaired-v2 paired comparison.",
    )
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--result-rows", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS_PATH)
    parser.add_argument("--per-query-type", type=int, default=1)
    parser.add_argument("--live-call-hard-cap", type=int, default=DEFAULT_LIVE_CALL_HARD_CAP)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
