from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.project_paths import project_path
from app.domain.retrieval import QueryType
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    measure_public_retrieval_artifact_quality,
)
from pipelines.run_place_story_generation_input_only_eval import (
    DEFAULT_MAX_CONTEXT_CHARS,
    _StrategyInputBundle,
    _build_strategy_input_bundle,
    _load_child_chunks_by_id,
)
from pipelines.run_place_story_guarded_boost_comparison import (
    BASELINE_STRATEGY_ID,
    CANDIDATE_STRATEGY_ID,
    GUARDED_BOOST_STRATEGY_ID,
    ROUTER_POLICY_ID,
    GuardedRouteRow,
    build_guarded_route_row,
    _bundles_by_query_id,
    _records_by_query_id,
)
from pipelines.run_place_story_top_rank_coverage_repair import (
    DEFAULT_CANDIDATE_K,
    DEFAULT_EMBEDDING_CACHE_DIR,
    DEFAULT_PLACE_CATALOG_PATH,
    DEFAULT_TOP_K,
    _build_execution_context,
    _load_place_story_dev_items,
    _validate_private_rows_path,
    _write_jsonl_rows,
)
from pipelines.run_solar_guarded_boost_live_dry_run import ANSWER_POLICY_ID
from pipelines.run_solar_live_generation_smoke import DEFAULT_CHUNKS_PATH, DEFAULT_DATASET_PATH


SOLAR_GUARDED_BOOST_HARD_CASE_VALIDATION_REPORT_VERSION = (
    "solar-guarded-boost-hard-case-validation/v1"
)
DEFAULT_REPORT_PATH = (
    Path("evals")
    / "reports"
    / "solar_guarded_boost_hard_case_validation_report.md"
)
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "solar_guarded_boost_hard_case_validation_rows.jsonl"
)
DEFAULT_LIVE_PAIRED_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "solar_guarded_boost_live_comparison_rows.jsonl"
)
EXPECTED_PLACE_STORY_QUERY_COUNT = 10

HardCaseBucket = Literal[
    "candidate_direct_gain",
    "correctness_guardrail",
    "doc_guardrail",
    "precision_guardrail",
    "manual_review_required",
    "no_candidate_gain_control",
]
ValidationDecision = Literal[
    "keep_guarded_router_for_next_runner",
    "needs_router_threshold_tuning_before_live",
    "blocked_by_validation_gate",
]


class SolarGuardedBoostHardCaseValidationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LivePairedMetricRow(SolarGuardedBoostHardCaseValidationModel):
    query_id: str = Field(min_length=1)
    query_type: QueryType
    route_decision: str = Field(min_length=1)
    reuse_decision: str = Field(min_length=1)
    baseline_strategy_id: str = Field(min_length=1)
    candidate_strategy_id: str = Field(min_length=1)
    baseline_correct_with_evidence: bool
    candidate_correct_with_evidence: bool
    correct_with_evidence_delta: int
    baseline_citation_precision: float = Field(ge=0.0, le=1.0)
    candidate_citation_precision: float = Field(ge=0.0, le=1.0)
    citation_precision_delta: float
    baseline_citation_recall: float = Field(ge=0.0, le=1.0)
    candidate_citation_recall: float = Field(ge=0.0, le=1.0)
    citation_recall_delta: float
    unsupported_claim_delta: int
    baseline_citation_count: int = Field(ge=0)
    candidate_citation_count: int = Field(ge=0)
    citation_count_delta: int
    latency_ms_delta: float


class GuardedBoostHardCaseValidationRow(SolarGuardedBoostHardCaseValidationModel):
    query_id: str = Field(min_length=1)
    query_type: QueryType
    split: str = Field(min_length=1)
    hard_case_bucket: HardCaseBucket
    route_decision: str = Field(min_length=1)
    live_route_decision: str = Field(min_length=1)
    route_decision_matched_live: bool
    selected_strategy_id: str = Field(min_length=1)
    blocked: bool
    selected_candidate: bool
    reuse_decision: str = Field(min_length=1)
    candidate_live_call_required: bool
    direct_ready_delta: int = Field(ge=-1, le=1)
    input_correct_with_evidence_delta: int = Field(ge=-1, le=1)
    input_citation_precision_delta: float
    input_citation_recall_delta: float
    evidence_order_delta: float
    duplicate_parent_rate_delta: float
    selected_citation_recoverability: float = Field(ge=0.0, le=1.0)
    candidate_doc_covered: bool
    candidate_context_buildable: bool
    live_correct_with_evidence_delta: int
    live_citation_precision_delta: float
    live_citation_recall_delta: float
    live_unsupported_claim_delta: int
    live_latency_ms_delta: float
    qualitative_tags: tuple[str, ...]


class HardCaseBucketSummary(SolarGuardedBoostHardCaseValidationModel):
    hard_case_bucket: HardCaseBucket
    query_count: int = Field(ge=0)
    selected_candidate_count: int = Field(ge=0)
    blocked_count: int = Field(ge=0)
    candidate_live_call_required_count: int = Field(ge=0)
    route_mismatch_count: int = Field(ge=0)
    live_correct_delta_min: int
    live_precision_delta_min: float
    live_recall_delta_avg: float
    live_unsupported_delta_max: int
    evidence_order_delta_min: float
    selected_citation_recoverability_min: float = Field(ge=0.0, le=1.0)


class HardCaseValidationSummary(SolarGuardedBoostHardCaseValidationModel):
    expected_query_count: int = Field(ge=1)
    query_count: int = Field(ge=0)
    bucket_coverage_count: int = Field(ge=0)
    hard_case_bucket_count: int = Field(ge=0)
    selected_candidate_count: int = Field(ge=0)
    guardrail_block_count: int = Field(ge=0)
    manual_review_count: int = Field(ge=0)
    doc_guardrail_count: int = Field(ge=0)
    precision_guardrail_count: int = Field(ge=0)
    no_candidate_gain_control_count: int = Field(ge=0)
    candidate_live_call_required_count: int = Field(ge=0)
    live_reference_row_count: int = Field(ge=0)
    route_decision_mismatch_count: int = Field(ge=0)
    selected_candidate_safety_passed: bool
    manual_review_block_passed: bool
    doc_guardrail_block_passed: bool
    citation_recoverability_min: float = Field(ge=0.0, le=1.0)
    solar_call_count: int = Field(ge=0)
    validation_decision: ValidationDecision


class SolarGuardedBoostHardCaseValidationReport(
    SolarGuardedBoostHardCaseValidationModel,
):
    report_version: str = SOLAR_GUARDED_BOOST_HARD_CASE_VALIDATION_REPORT_VERSION
    validation_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    dataset_path_alias: str = Field(min_length=1)
    chunks_path_alias: str = Field(min_length=1)
    live_paired_rows_path_alias: str = Field(min_length=1)
    baseline_strategy_id: str = Field(min_length=1)
    candidate_strategy_id: str = Field(min_length=1)
    guarded_strategy_id: str = Field(min_length=1)
    router_policy_id: str = Field(min_length=1)
    answer_policy_id: str = Field(min_length=1)
    top_k: int = Field(ge=1)
    candidate_k: int = Field(ge=1)
    max_context_chars: int = Field(ge=1)
    resolved_device: str = Field(min_length=1)
    summary: HardCaseValidationSummary
    bucket_summaries: tuple[HardCaseBucketSummary, ...]
    rows: tuple[GuardedBoostHardCaseValidationRow, ...]
    bucket_distribution: dict[str, int]
    qualitative_assessment: dict[str, str]
    output_quality: PublicRetrievalArtifactQuality


def run_solar_guarded_boost_hard_case_validation(
    *,
    chunks_path: Path = DEFAULT_CHUNKS_PATH,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    live_paired_rows_path: Path = DEFAULT_LIVE_PAIRED_ROWS_PATH,
    place_catalog_path: Path = DEFAULT_PLACE_CATALOG_PATH,
    embedding_cache_dir: Path = DEFAULT_EMBEDDING_CACHE_DIR,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
    top_k: int = DEFAULT_TOP_K,
    candidate_k: int = DEFAULT_CANDIDATE_K,
    max_context_chars: int = DEFAULT_MAX_CONTEXT_CHARS,
    expected_query_count: int = EXPECTED_PLACE_STORY_QUERY_COUNT,
) -> SolarGuardedBoostHardCaseValidationReport:
    _validate_private_rows_path(result_rows_path, label="result")
    live_rows = load_live_paired_metric_rows(live_paired_rows_path)
    items = _load_place_story_dev_items(dataset_path=dataset_path)
    context = _build_execution_context(
        chunks_path=chunks_path,
        place_catalog_path=place_catalog_path,
        embedding_cache_dir=embedding_cache_dir,
    )
    child_chunks_by_id = _load_child_chunks_by_id(chunks_path)
    baseline_bundles = tuple(
        _build_strategy_input_bundle(
            item=item,
            strategy_id=BASELINE_STRATEGY_ID,
            context=context,
            child_chunks_by_id=child_chunks_by_id,
            top_k=top_k,
            candidate_k=candidate_k,
            max_context_chars=max_context_chars,
        )
        for item in items
    )
    candidate_bundles = tuple(
        _build_strategy_input_bundle(
            item=item,
            strategy_id=CANDIDATE_STRATEGY_ID,
            context=context,
            child_chunks_by_id=child_chunks_by_id,
            top_k=top_k,
            candidate_k=candidate_k,
            max_context_chars=max_context_chars,
        )
        for item in items
    )

    provisional = build_solar_guarded_boost_hard_case_validation_report(
        baseline_bundles=baseline_bundles,
        candidate_bundles=candidate_bundles,
        live_rows=live_rows,
        top_k=top_k,
        candidate_k=candidate_k,
        max_context_chars=max_context_chars,
        expected_query_count=expected_query_count,
    )
    public_rows = build_public_solar_guarded_boost_hard_case_validation_rows(provisional)
    markdown = build_solar_guarded_boost_hard_case_validation_markdown(provisional)
    report = build_solar_guarded_boost_hard_case_validation_report(
        baseline_bundles=baseline_bundles,
        candidate_bundles=candidate_bundles,
        live_rows=live_rows,
        top_k=top_k,
        candidate_k=candidate_k,
        max_context_chars=max_context_chars,
        expected_query_count=expected_query_count,
        result_rows=public_rows,
        report_text=markdown,
    )
    failures = collect_solar_guarded_boost_hard_case_validation_failures(report)
    if failures:
        raise ValueError(f"solar guarded boost hard-case validation gate failed: {failures}")

    _write_jsonl_rows(
        path=result_rows_path,
        rows=build_public_solar_guarded_boost_hard_case_validation_rows(report),
    )
    resolved_report_path = project_path(report_path)
    resolved_report_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_report_path.write_text(
        build_solar_guarded_boost_hard_case_validation_markdown(report),
        encoding="utf-8",
    )
    return report


def load_live_paired_metric_rows(path: Path) -> tuple[LivePairedMetricRow, ...]:
    resolved_path = project_path(path)
    rows: list[LivePairedMetricRow] = []
    with resolved_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(LivePairedMetricRow.model_validate(json.loads(line)))
    return tuple(rows)


def build_solar_guarded_boost_hard_case_validation_report(
    *,
    baseline_bundles: tuple[_StrategyInputBundle, ...],
    candidate_bundles: tuple[_StrategyInputBundle, ...],
    live_rows: tuple[LivePairedMetricRow, ...],
    top_k: int,
    candidate_k: int,
    max_context_chars: int,
    expected_query_count: int,
    result_rows: list[dict[str, Any]] | None = None,
    report_text: str = "",
) -> SolarGuardedBoostHardCaseValidationReport:
    baseline_by_query = _bundles_by_query_id(baseline_bundles)
    candidate_by_query = _bundles_by_query_id(candidate_bundles)
    baseline_records = _records_by_query_id(
        strategy_id=BASELINE_STRATEGY_ID,
        bundles=baseline_bundles,
    )
    candidate_records = _records_by_query_id(
        strategy_id=CANDIDATE_STRATEGY_ID,
        bundles=candidate_bundles,
    )
    route_rows = tuple(
        build_guarded_route_row(
            baseline_bundle=baseline_by_query[query_id],
            candidate_bundle=candidate_by_query[query_id],
            baseline_record=baseline_records[query_id],
            candidate_record=candidate_records[query_id],
        )
        for query_id in sorted(baseline_by_query)
    )
    live_by_query = {row.query_id: row for row in live_rows}
    rows = tuple(
        build_hard_case_validation_row(
            route_row=route_row,
            baseline_bundle=baseline_by_query[route_row.query_id],
            candidate_bundle=candidate_by_query[route_row.query_id],
            live_row=live_by_query[route_row.query_id],
        )
        for route_row in route_rows
    )
    bucket_summaries = tuple(build_bucket_summaries(rows))
    summary = build_hard_case_validation_summary(
        rows=rows,
        expected_query_count=expected_query_count,
        live_reference_row_count=len(live_rows),
    )
    validation_id = build_hard_case_validation_id(rows=rows, summary=summary)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=SOLAR_GUARDED_BOOST_HARD_CASE_VALIDATION_REPORT_VERSION,
        run_id=validation_id,
        result_rows=result_rows or [],
        report_text=report_text,
    )
    report = SolarGuardedBoostHardCaseValidationReport(
        validation_id=validation_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        dataset_path_alias="<private retrieval eval dataset: retrieval_eval_dev.jsonl>",
        chunks_path_alias="<private parent_child_chunks report>",
        live_paired_rows_path_alias="<private public-safe live paired metric rows>",
        baseline_strategy_id=BASELINE_STRATEGY_ID,
        candidate_strategy_id=CANDIDATE_STRATEGY_ID,
        guarded_strategy_id=GUARDED_BOOST_STRATEGY_ID,
        router_policy_id=ROUTER_POLICY_ID,
        answer_policy_id=ANSWER_POLICY_ID,
        top_k=top_k,
        candidate_k=candidate_k,
        max_context_chars=max_context_chars,
        resolved_device=_resolved_device_from_bundles(baseline_bundles, candidate_bundles),
        summary=summary,
        bucket_summaries=bucket_summaries,
        rows=rows,
        bucket_distribution=dict(
            sorted(Counter(row.hard_case_bucket for row in rows).items()),
        ),
        qualitative_assessment={},
        output_quality=output_quality,
    )
    return report.model_copy(
        update={
            "qualitative_assessment": build_hard_case_validation_assessment(report),
        },
    )


def build_hard_case_validation_row(
    *,
    route_row: GuardedRouteRow,
    baseline_bundle: _StrategyInputBundle,
    candidate_bundle: _StrategyInputBundle,
    live_row: LivePairedMetricRow,
) -> GuardedBoostHardCaseValidationRow:
    hard_case_bucket = bucket_for_route_decision(route_row.route_decision)
    selected_bundle = (
        candidate_bundle
        if route_row.selected_strategy_id == GUARDED_BOOST_STRATEGY_ID
        else baseline_bundle
    )
    selected_candidate = route_row.selected_strategy_id == GUARDED_BOOST_STRATEGY_ID
    candidate_live_call_required = live_row.reuse_decision == "candidate_live_call_required"
    return GuardedBoostHardCaseValidationRow(
        query_id=route_row.query_id,
        query_type=route_row.query_type,
        split=route_row.split,
        hard_case_bucket=hard_case_bucket,
        route_decision=route_row.route_decision,
        live_route_decision=live_row.route_decision,
        route_decision_matched_live=route_row.route_decision == live_row.route_decision,
        selected_strategy_id=route_row.selected_strategy_id,
        blocked=route_row.blocked,
        selected_candidate=selected_candidate,
        reuse_decision=live_row.reuse_decision,
        candidate_live_call_required=candidate_live_call_required,
        direct_ready_delta=route_row.direct_ready_delta,
        input_correct_with_evidence_delta=route_row.correct_with_evidence_delta,
        input_citation_precision_delta=route_row.citation_precision_delta,
        input_citation_recall_delta=route_row.citation_recall_delta,
        evidence_order_delta=route_row.evidence_order_delta,
        duplicate_parent_rate_delta=route_row.duplicate_parent_rate_delta,
        selected_citation_recoverability=selected_bundle.evidence_pack.citation_recoverability,
        candidate_doc_covered=route_row.candidate_doc_covered,
        candidate_context_buildable=route_row.candidate_context_buildable,
        live_correct_with_evidence_delta=live_row.correct_with_evidence_delta,
        live_citation_precision_delta=live_row.citation_precision_delta,
        live_citation_recall_delta=live_row.citation_recall_delta,
        live_unsupported_claim_delta=live_row.unsupported_claim_delta,
        live_latency_ms_delta=live_row.latency_ms_delta,
        qualitative_tags=build_hard_case_qualitative_tags(
            bucket=hard_case_bucket,
            route_row=route_row,
            live_row=live_row,
        ),
    )


def bucket_for_route_decision(route_decision: str) -> HardCaseBucket:
    mapping: dict[str, HardCaseBucket] = {
        "use_candidate_direct_gain": "candidate_direct_gain",
        "use_baseline_correctness_guardrail": "correctness_guardrail",
        "use_baseline_doc_guardrail": "doc_guardrail",
        "use_baseline_precision_guardrail": "precision_guardrail",
        "manual_review_required": "manual_review_required",
        "use_baseline_no_candidate_gain": "no_candidate_gain_control",
    }
    try:
        return mapping[route_decision]
    except KeyError as exc:
        raise ValueError(f"unknown guarded boost route decision: {route_decision}") from exc


def build_hard_case_qualitative_tags(
    *,
    bucket: HardCaseBucket,
    route_row: GuardedRouteRow,
    live_row: LivePairedMetricRow,
) -> tuple[str, ...]:
    tags: list[str] = []
    if bucket == "candidate_direct_gain":
        tags.append("safe_direct_gain")
    elif bucket == "correctness_guardrail":
        tags.append("blocked_correctness_risk")
    elif bucket == "doc_guardrail":
        tags.append("blocked_doc_loss")
    elif bucket == "precision_guardrail":
        tags.append("blocked_precision_or_order_risk")
    elif bucket == "manual_review_required":
        tags.append("manual_review_kept_blocked")
    elif bucket == "no_candidate_gain_control":
        tags.append("control_no_gain")
    if route_row.route_decision != live_row.route_decision:
        tags.append("needs_router_threshold_tuning")
    if live_row.reuse_decision == "candidate_live_call_required":
        tags.append("candidate_live_reference_available")
    if live_row.citation_recall_delta > 0:
        tags.append("live_citation_recall_gain")
    if live_row.citation_precision_delta < 0 or live_row.unsupported_claim_delta > 0:
        tags.append("live_safety_regression")
    return tuple(tags)


def build_bucket_summaries(
    rows: tuple[GuardedBoostHardCaseValidationRow, ...],
) -> list[HardCaseBucketSummary]:
    summaries: list[HardCaseBucketSummary] = []
    for bucket in sorted({row.hard_case_bucket for row in rows}):
        subset = [row for row in rows if row.hard_case_bucket == bucket]
        summaries.append(
            HardCaseBucketSummary(
                hard_case_bucket=bucket,
                query_count=len(subset),
                selected_candidate_count=sum(row.selected_candidate for row in subset),
                blocked_count=sum(row.blocked for row in subset),
                candidate_live_call_required_count=sum(
                    row.candidate_live_call_required for row in subset
                ),
                route_mismatch_count=sum(
                    not row.route_decision_matched_live for row in subset
                ),
                live_correct_delta_min=min(
                    row.live_correct_with_evidence_delta for row in subset
                ),
                live_precision_delta_min=min(
                    row.live_citation_precision_delta for row in subset
                ),
                live_recall_delta_avg=round(
                    _mean_float([row.live_citation_recall_delta for row in subset]),
                    6,
                ),
                live_unsupported_delta_max=max(
                    row.live_unsupported_claim_delta for row in subset
                ),
                evidence_order_delta_min=min(row.evidence_order_delta for row in subset),
                selected_citation_recoverability_min=min(
                    row.selected_citation_recoverability for row in subset
                ),
            ),
        )
    return summaries


def build_hard_case_validation_summary(
    *,
    rows: tuple[GuardedBoostHardCaseValidationRow, ...],
    expected_query_count: int,
    live_reference_row_count: int,
) -> HardCaseValidationSummary:
    selected_rows = [row for row in rows if row.selected_candidate]
    manual_rows = [row for row in rows if row.hard_case_bucket == "manual_review_required"]
    doc_guardrail_rows = [row for row in rows if row.hard_case_bucket == "doc_guardrail"]
    citation_recoverability_min = (
        min(row.selected_citation_recoverability for row in rows) if rows else 0.0
    )
    selected_candidate_safety_passed = all(
        row.live_correct_with_evidence_delta >= 0
        and row.live_citation_precision_delta >= 0
        and row.live_citation_recall_delta >= 0
        and row.live_unsupported_claim_delta <= 0
        and row.evidence_order_delta >= 0
        for row in selected_rows
    )
    manual_review_block_passed = all(not row.selected_candidate for row in manual_rows)
    doc_guardrail_block_passed = all(not row.selected_candidate for row in doc_guardrail_rows)
    route_mismatch_count = sum(not row.route_decision_matched_live for row in rows)
    validation_decision = select_validation_decision(
        rows=rows,
        expected_query_count=expected_query_count,
        selected_candidate_safety_passed=selected_candidate_safety_passed,
        manual_review_block_passed=manual_review_block_passed,
        doc_guardrail_block_passed=doc_guardrail_block_passed,
        citation_recoverability_min=citation_recoverability_min,
        route_mismatch_count=route_mismatch_count,
    )
    return HardCaseValidationSummary(
        expected_query_count=expected_query_count,
        query_count=len(rows),
        bucket_coverage_count=sum(1 for row in rows if row.hard_case_bucket),
        hard_case_bucket_count=len({row.hard_case_bucket for row in rows}),
        selected_candidate_count=sum(row.selected_candidate for row in rows),
        guardrail_block_count=sum(row.blocked for row in rows),
        manual_review_count=len(manual_rows),
        doc_guardrail_count=sum(row.hard_case_bucket == "doc_guardrail" for row in rows),
        precision_guardrail_count=sum(
            row.hard_case_bucket == "precision_guardrail" for row in rows
        ),
        no_candidate_gain_control_count=sum(
            row.hard_case_bucket == "no_candidate_gain_control" for row in rows
        ),
        candidate_live_call_required_count=sum(
            row.candidate_live_call_required for row in rows
        ),
        live_reference_row_count=live_reference_row_count,
        route_decision_mismatch_count=route_mismatch_count,
        selected_candidate_safety_passed=selected_candidate_safety_passed,
        manual_review_block_passed=manual_review_block_passed,
        doc_guardrail_block_passed=doc_guardrail_block_passed,
        citation_recoverability_min=round(citation_recoverability_min, 6),
        solar_call_count=0,
        validation_decision=validation_decision,
    )


def select_validation_decision(
    *,
    rows: tuple[GuardedBoostHardCaseValidationRow, ...],
    expected_query_count: int,
    selected_candidate_safety_passed: bool,
    manual_review_block_passed: bool,
    doc_guardrail_block_passed: bool,
    citation_recoverability_min: float,
    route_mismatch_count: int,
) -> ValidationDecision:
    if (
        not rows
        or len(rows) != expected_query_count
        or citation_recoverability_min < 0.99
        or not selected_candidate_safety_passed
        or not manual_review_block_passed
        or not doc_guardrail_block_passed
    ):
        return "blocked_by_validation_gate"
    if route_mismatch_count:
        return "needs_router_threshold_tuning_before_live"
    return "keep_guarded_router_for_next_runner"


def build_public_solar_guarded_boost_hard_case_validation_rows(
    report: SolarGuardedBoostHardCaseValidationReport,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "validation_id": report.validation_id,
            "row_type": "summary",
            "expected_query_count": report.summary.expected_query_count,
            "query_count": report.summary.query_count,
            "bucket_coverage_count": report.summary.bucket_coverage_count,
            "hard_case_bucket_count": report.summary.hard_case_bucket_count,
            "selected_candidate_count": report.summary.selected_candidate_count,
            "guardrail_block_count": report.summary.guardrail_block_count,
            "candidate_live_call_required_count": (
                report.summary.candidate_live_call_required_count
            ),
            "route_decision_mismatch_count": (
                report.summary.route_decision_mismatch_count
            ),
            "citation_recoverability_min": report.summary.citation_recoverability_min,
            "solar_call_count": report.summary.solar_call_count,
            "validation_decision": report.summary.validation_decision,
        },
    ]
    rows.extend(
        {
            "validation_id": report.validation_id,
            "row_type": "bucket_summary",
            "hard_case_bucket": summary.hard_case_bucket,
            "query_count": summary.query_count,
            "selected_candidate_count": summary.selected_candidate_count,
            "blocked_count": summary.blocked_count,
            "candidate_live_call_required_count": (
                summary.candidate_live_call_required_count
            ),
            "route_mismatch_count": summary.route_mismatch_count,
            "live_correct_delta_min": summary.live_correct_delta_min,
            "live_precision_delta_min": summary.live_precision_delta_min,
            "live_recall_delta_avg": summary.live_recall_delta_avg,
            "live_unsupported_delta_max": summary.live_unsupported_delta_max,
            "evidence_order_delta_min": summary.evidence_order_delta_min,
            "selected_citation_recoverability_min": (
                summary.selected_citation_recoverability_min
            ),
        }
        for summary in report.bucket_summaries
    )
    rows.extend(
        {
            "validation_id": report.validation_id,
            "row_type": "hard_case_query",
            "query_id": row.query_id,
            "query_type": row.query_type,
            "split": row.split,
            "hard_case_bucket": row.hard_case_bucket,
            "route_decision": row.route_decision,
            "live_route_decision": row.live_route_decision,
            "route_decision_matched_live": row.route_decision_matched_live,
            "selected_strategy_id": row.selected_strategy_id,
            "blocked": row.blocked,
            "selected_candidate": row.selected_candidate,
            "reuse_decision": row.reuse_decision,
            "candidate_live_call_required": row.candidate_live_call_required,
            "direct_ready_delta": row.direct_ready_delta,
            "input_correct_with_evidence_delta": (
                row.input_correct_with_evidence_delta
            ),
            "input_citation_precision_delta": row.input_citation_precision_delta,
            "input_citation_recall_delta": row.input_citation_recall_delta,
            "evidence_order_delta": row.evidence_order_delta,
            "duplicate_parent_rate_delta": row.duplicate_parent_rate_delta,
            "selected_citation_recoverability": row.selected_citation_recoverability,
            "candidate_doc_covered": row.candidate_doc_covered,
            "candidate_context_buildable": row.candidate_context_buildable,
            "live_correct_with_evidence_delta": row.live_correct_with_evidence_delta,
            "live_citation_precision_delta": row.live_citation_precision_delta,
            "live_citation_recall_delta": row.live_citation_recall_delta,
            "live_unsupported_claim_delta": row.live_unsupported_claim_delta,
            "live_latency_ms_delta": row.live_latency_ms_delta,
            "qualitative_tags": row.qualitative_tags,
        }
        for row in report.rows
    )
    return rows


def collect_solar_guarded_boost_hard_case_validation_failures(
    report: SolarGuardedBoostHardCaseValidationReport,
) -> list[str]:
    failures: list[str] = []
    if not report.rows:
        failures.append("empty_validation_rows")
    if report.summary.query_count != report.summary.expected_query_count:
        failures.append("query_count_mismatch")
    if report.summary.bucket_coverage_count != report.summary.query_count:
        failures.append("bucket_coverage_incomplete")
    if report.summary.live_reference_row_count != report.summary.query_count:
        failures.append("live_reference_row_count_mismatch")
    if report.summary.route_decision_mismatch_count:
        failures.append("route_decision_mismatch")
    if not report.summary.selected_candidate_safety_passed:
        failures.append("selected_candidate_safety_failed")
    if not report.summary.manual_review_block_passed:
        failures.append("manual_review_auto_selected")
    if not report.summary.doc_guardrail_block_passed:
        failures.append("doc_guardrail_auto_selected")
    if report.summary.citation_recoverability_min < 0.99:
        failures.append("citation_recoverability_below_0_99")
    if report.summary.solar_call_count:
        failures.append("solar_call_count_must_be_zero")
    if report.output_quality.public_raw_text_leakage_count:
        failures.append("public_raw_text_leakage")
    if report.output_quality.private_path_leakage_count:
        failures.append("private_path_leakage")
    if report.output_quality.secret_like_leakage_count:
        failures.append("secret_like_leakage")
    if report.output_quality.forbidden_result_field_count:
        failures.append("forbidden_public_result_fields")
    return failures


def build_hard_case_validation_assessment(
    report: SolarGuardedBoostHardCaseValidationReport,
) -> dict[str, str]:
    failures = collect_solar_guarded_boost_hard_case_validation_failures(report)
    tag_counts = Counter(tag for row in report.rows for tag in row.qualitative_tags)
    tag_summary = ", ".join(f"{tag}={count}" for tag, count in sorted(tag_counts.items()))
    return {
        "scope": (
            "HD-SOLAR-016 live paired metric rows와 현재 input-only route decision을 결합해 `place_story` dev hard-case를 검증했다."
        ),
        "llm_call_boundary": (
            "이번 runner는 Solar Pro 3를 호출하지 않는다. solar_call_count는 0이다."
        ),
        "metric_grain": (
            "`validation_id + query_id + hard_case_bucket + strategy_id + router_policy_id + answer_policy_id` grain으로 기록한다."
        ),
        "bucket_policy": (
            "route decision을 candidate/direct, correctness/doc/precision guardrail, manual review, no-gain control bucket으로 분리했다."
        ),
        "qualitative_tags": tag_summary,
        "claim_boundary": (
            "이 결과는 dev hard-case route safety 검증이며 final benchmark 또는 production 채택 주장이 아니다."
        ),
        "public_policy": (
            "public report와 result row에는 raw query, raw answer, evidence text, prompt, chunk text, private path, secret을 저장하지 않는다."
        ),
        "gate_status": "PASS" if not failures else f"FAIL: {', '.join(failures)}",
    }


def build_solar_guarded_boost_hard_case_validation_markdown(
    report: SolarGuardedBoostHardCaseValidationReport,
) -> str:
    summary = report.summary
    quality = report.output_quality
    bucket_distribution_rows = "\n".join(
        f"| `{bucket}` | {count} |"
        for bucket, count in report.bucket_distribution.items()
    )
    bucket_rows = "\n".join(
        _format_bucket_summary_row(row) for row in report.bucket_summaries
    )
    validation_rows = "\n".join(_format_validation_row(row) for row in report.rows)
    qualitative_rows = "\n".join(
        f"- `{key}`: {value}" for key, value in report.qualitative_assessment.items()
    )
    return f"""# Solar Pro 3 Guarded Boost Hard-case Validation Report

## 목적

HD-SOLAR-016 live paired comparison 이후 `parent_doc_context_boost_guarded`의 route decision을 추가 dev hard-case bucket으로 검증한다.

이 문서는 Solar Pro 3 추가 호출 결과가 아니다. 기존 public-safe live metric row와 현재 input-only route decision을 결합해 검증하며 raw query, raw answer, raw evidence, prompt, chunk text는 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| validation_id | `{report.validation_id}` |
| generated_at_utc | `{report.generated_at_utc}` |
| dataset_path | `{report.dataset_path_alias}` |
| chunks_path | `{report.chunks_path_alias}` |
| live_paired_rows_path | `{report.live_paired_rows_path_alias}` |
| baseline_strategy_id | `{report.baseline_strategy_id}` |
| candidate_strategy_id | `{report.candidate_strategy_id}` |
| guarded_strategy_id | `{report.guarded_strategy_id}` |
| router_policy_id | `{report.router_policy_id}` |
| answer_policy_id | `{report.answer_policy_id}` |
| top_k | {report.top_k} |
| candidate_k | {report.candidate_k} |
| max_context_chars | {report.max_context_chars} |
| resolved_device | `{report.resolved_device}` |

## 정량 리포트

| metric | value |
| --- | ---: |
| expected_query_count | {summary.expected_query_count} |
| query_count | {summary.query_count} |
| bucket_coverage_count | {summary.bucket_coverage_count} |
| hard_case_bucket_count | {summary.hard_case_bucket_count} |
| selected_candidate_count | {summary.selected_candidate_count} |
| guardrail_block_count | {summary.guardrail_block_count} |
| manual_review_count | {summary.manual_review_count} |
| doc_guardrail_count | {summary.doc_guardrail_count} |
| precision_guardrail_count | {summary.precision_guardrail_count} |
| no_candidate_gain_control_count | {summary.no_candidate_gain_control_count} |
| candidate_live_call_required_count | {summary.candidate_live_call_required_count} |
| live_reference_row_count | {summary.live_reference_row_count} |
| route_decision_mismatch_count | {summary.route_decision_mismatch_count} |
| selected_candidate_safety_passed | {summary.selected_candidate_safety_passed} |
| manual_review_block_passed | {summary.manual_review_block_passed} |
| doc_guardrail_block_passed | {summary.doc_guardrail_block_passed} |
| citation_recoverability_min | {summary.citation_recoverability_min:.6f} |
| solar_call_count | {summary.solar_call_count} |
| validation_decision | `{summary.validation_decision}` |

## Hard-case Bucket Distribution

| bucket | count |
| --- | ---: |
{bucket_distribution_rows}

## Bucket Summary

| bucket | query_count | selected_candidate | blocked | candidate_live_call | route_mismatch | live_correct_min | live_precision_min | live_recall_avg | unsupported_max | order_delta_min | citation_recoverability_min |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{bucket_rows}

## Query-level Sanitized Validation

| query_id | bucket | decision | selected | blocked | reuse | input_correct_delta | input_precision_delta | input_recall_delta | order_delta | live_correct_delta | live_precision_delta | live_recall_delta | unsupported_delta | tags |
| --- | --- | --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
{validation_rows}

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

## 결론

{_validation_conclusion(report)}
"""


def build_hard_case_validation_id(
    *,
    rows: tuple[GuardedBoostHardCaseValidationRow, ...],
    summary: HardCaseValidationSummary,
) -> str:
    payload = {
        "query_ids": [row.query_id for row in rows],
        "buckets": [row.hard_case_bucket for row in rows],
        "route_decisions": [row.route_decision for row in rows],
        "decision": summary.validation_decision,
    }
    digest = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"),
    ).hexdigest()[:8]
    return f"solar-guarded-boost-hard-case-q{len(rows)}-{digest}"


def _format_bucket_summary_row(row: HardCaseBucketSummary) -> str:
    return (
        f"| `{row.hard_case_bucket}` | {row.query_count} | "
        f"{row.selected_candidate_count} | {row.blocked_count} | "
        f"{row.candidate_live_call_required_count} | {row.route_mismatch_count} | "
        f"{row.live_correct_delta_min} | {row.live_precision_delta_min:.6f} | "
        f"{row.live_recall_delta_avg:.6f} | {row.live_unsupported_delta_max} | "
        f"{row.evidence_order_delta_min:.6f} | "
        f"{row.selected_citation_recoverability_min:.6f} |"
    )


def _format_validation_row(row: GuardedBoostHardCaseValidationRow) -> str:
    tags = ", ".join(f"`{tag}`" for tag in row.qualitative_tags)
    return (
        f"| `{row.query_id}` | `{row.hard_case_bucket}` | "
        f"`{row.route_decision}` | `{row.selected_strategy_id}` | {row.blocked} | "
        f"`{row.reuse_decision}` | {row.input_correct_with_evidence_delta} | "
        f"{row.input_citation_precision_delta:.6f} | "
        f"{row.input_citation_recall_delta:.6f} | "
        f"{row.evidence_order_delta:.6f} | "
        f"{row.live_correct_with_evidence_delta} | "
        f"{row.live_citation_precision_delta:.6f} | "
        f"{row.live_citation_recall_delta:.6f} | "
        f"{row.live_unsupported_claim_delta} | {tags} |"
    )


def _validation_conclusion(
    report: SolarGuardedBoostHardCaseValidationReport,
) -> str:
    if report.summary.validation_decision == "keep_guarded_router_for_next_runner":
        return (
            "`guarded_boost` hard-case validation gate를 통과했다. 다음 단계는 router threshold를 바꾸지 않고 후속 검증 계획으로 이동하는 것이다."
        )
    if report.summary.validation_decision == "needs_router_threshold_tuning_before_live":
        return (
            "route decision mismatch가 있어 추가 live 검증 전에 router threshold 재점검이 필요하다."
        )
    return "hard-case validation gate가 실패했다. production 채택과 추가 live call을 보류한다."


def _resolved_device_from_bundles(
    baseline_bundles: tuple[_StrategyInputBundle, ...],
    candidate_bundles: tuple[_StrategyInputBundle, ...],
) -> str:
    for bundle in (*baseline_bundles, *candidate_bundles):
        metadata = getattr(bundle.item, "metadata", None)
        if metadata and getattr(metadata, "resolved_device", None):
            return str(metadata.resolved_device)
    try:
        from app.infrastructure.index.device import resolve_torch_device

        return resolve_torch_device("auto")
    except Exception:
        return "unknown"


def _mean_float(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Solar guarded boost hard-case validation without live Solar calls.",
    )
    parser.add_argument("--chunks-path", type=Path, default=DEFAULT_CHUNKS_PATH)
    parser.add_argument("--dataset-path", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument(
        "--live-paired-rows-path",
        type=Path,
        default=DEFAULT_LIVE_PAIRED_ROWS_PATH,
    )
    parser.add_argument("--place-catalog-path", type=Path, default=DEFAULT_PLACE_CATALOG_PATH)
    parser.add_argument("--embedding-cache-dir", type=Path, default=DEFAULT_EMBEDDING_CACHE_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--result-rows-path", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument("--candidate-k", type=int, default=DEFAULT_CANDIDATE_K)
    parser.add_argument("--max-context-chars", type=int, default=DEFAULT_MAX_CONTEXT_CHARS)
    parser.add_argument(
        "--expected-query-count",
        type=int,
        default=EXPECTED_PLACE_STORY_QUERY_COUNT,
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = run_solar_guarded_boost_hard_case_validation(
        chunks_path=args.chunks_path,
        dataset_path=args.dataset_path,
        live_paired_rows_path=args.live_paired_rows_path,
        place_catalog_path=args.place_catalog_path,
        embedding_cache_dir=args.embedding_cache_dir,
        report_path=args.report_path,
        result_rows_path=args.result_rows_path,
        top_k=args.top_k,
        candidate_k=args.candidate_k,
        max_context_chars=args.max_context_chars,
        expected_query_count=args.expected_query_count,
    )
    print(
        "solar guarded boost hard-case validation completed: "
        f"{report.validation_id} decision={report.summary.validation_decision} "
        f"solar_call_count={report.summary.solar_call_count}",
    )


if __name__ == "__main__":
    main()
