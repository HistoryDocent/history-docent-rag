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
from app.domain.generation_eval import (
    GenerationEvalInput,
    GenerationEvalRecord,
    GenerationEvalReport,
    GenerationEvalUsage,
    build_generation_eval_records,
    build_generation_eval_report,
    collect_generation_eval_harness_failures,
)
from app.domain.retrieval import QueryType
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    measure_public_retrieval_artifact_quality,
)
from app.infrastructure.index.device import resolve_torch_device
from pipelines.run_place_story_generation_input_only_eval import (
    DEFAULT_MAX_CONTEXT_CHARS,
    INPUT_ONLY_PROVIDER_CONFIG_ID,
    _StrategyInputBundle,
    _build_strategy_input_bundle,
    _load_child_chunks_by_id,
)
from pipelines.run_place_story_top_rank_coverage_repair import (
    BASELINE_STRATEGY_ID,
    DEFAULT_CANDIDATE_K,
    DEFAULT_EMBEDDING_CACHE_DIR,
    DEFAULT_PLACE_CATALOG_PATH,
    DEFAULT_TOP_K,
    StrategyId,
    _build_execution_context,
    _load_place_story_dev_items,
    _validate_private_rows_path,
    _write_jsonl_rows,
)
from pipelines.run_solar_live_generation_smoke import DEFAULT_CHUNKS_PATH, DEFAULT_DATASET_PATH


PLACE_STORY_GUARDED_BOOST_REPORT_VERSION = "place-story-guarded-boost-comparison/v1"
DEFAULT_REPORT_PATH = (
    Path("evals") / "reports" / "place_story_guarded_boost_comparison_report.md"
)
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "place_story_guarded_boost_comparison_rows.jsonl"
)
CANDIDATE_STRATEGY_ID: StrategyId = "parent_doc_context_boost"
ALWAYS_BOOST_STRATEGY_ID = "parent_doc_context_boost_always"
GUARDED_BOOST_STRATEGY_ID = "parent_doc_context_boost_guarded"
ROUTER_POLICY_ID = "place_story_guarded_boost_v1"
MIN_EVIDENCE_ORDER = 0.4
MAX_EVIDENCE_ORDER_DROP = -0.5
MAX_DUPLICATE_PARENT_RATE_DELTA = 0.2

ComparisonStrategyId = Literal[
    "baseline_dense_e5_voice_rewrite",
    "parent_doc_context_boost_always",
    "parent_doc_context_boost_guarded",
]
RouteDecision = Literal[
    "use_baseline_no_candidate_gain",
    "use_candidate_direct_gain",
    "use_baseline_precision_guardrail",
    "use_baseline_correctness_guardrail",
    "use_baseline_doc_guardrail",
    "manual_review_required",
]


class PlaceStoryGuardedBoostModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class GuardedRouteRow(PlaceStoryGuardedBoostModel):
    query_id: str = Field(min_length=1)
    query_type: QueryType
    split: str = Field(min_length=1)
    router_policy_id: str = Field(min_length=1)
    route_decision: RouteDecision
    selected_strategy_id: ComparisonStrategyId
    blocked: bool
    block_reason_tags: tuple[str, ...]
    direct_ready_delta: int = Field(ge=-1, le=1)
    correct_with_evidence_delta: int = Field(ge=-1, le=1)
    citation_precision_delta: float
    citation_recall_delta: float
    evidence_order_delta: float
    duplicate_parent_rate_delta: float
    input_latency_delta_ms: float
    candidate_doc_covered: bool
    candidate_context_buildable: bool


class GuardedBoostStrategySummary(PlaceStoryGuardedBoostModel):
    strategy_id: ComparisonStrategyId
    eval_count: int = Field(ge=0)
    selected_candidate_count: int = Field(ge=0)
    guardrail_block_count: int = Field(ge=0)
    context_build_success_rate: float = Field(ge=0.0, le=1.0)
    direct_ready_rate: float = Field(ge=0.0, le=1.0)
    correct_with_evidence_rate: float = Field(ge=0.0, le=1.0)
    citation_precision: float = Field(ge=0.0, le=1.0)
    citation_recall: float = Field(ge=0.0, le=1.0)
    doc_coverage_rate: float = Field(ge=0.0, le=1.0)
    evidence_order_relevance_proxy_avg: float = Field(ge=0.0, le=1.0)
    duplicate_parent_rate_avg: float = Field(ge=0.0, le=1.0)
    avg_evidence_count: float = Field(ge=0.0)
    input_latency_p95_ms: float = Field(ge=0.0)
    solar_call_count: int = Field(ge=0)


class GuardedBoostStrategyDelta(PlaceStoryGuardedBoostModel):
    compared_strategy_id: ComparisonStrategyId
    baseline_strategy_id: ComparisonStrategyId = BASELINE_STRATEGY_ID
    direct_ready_rate_delta: float
    correct_with_evidence_rate_delta: float
    citation_precision_delta: float
    citation_recall_delta: float
    doc_coverage_rate_delta: float
    evidence_order_relevance_proxy_avg_delta: float
    duplicate_parent_rate_avg_delta: float
    input_latency_p95_ms_delta: float


class PlaceStoryGuardedBoostComparisonReport(PlaceStoryGuardedBoostModel):
    report_version: str = PLACE_STORY_GUARDED_BOOST_REPORT_VERSION
    comparison_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    dataset_path_alias: str = Field(min_length=1)
    chunks_path_alias: str = Field(min_length=1)
    baseline_strategy_id: ComparisonStrategyId
    candidate_strategy_id: StrategyId
    router_policy_id: str = Field(min_length=1)
    top_k: int = Field(ge=1)
    candidate_k: int = Field(ge=1)
    max_context_chars: int = Field(ge=1)
    resolved_device: str = Field(min_length=1)
    strategy_summaries: tuple[GuardedBoostStrategySummary, ...]
    strategy_deltas: tuple[GuardedBoostStrategyDelta, ...]
    route_rows: tuple[GuardedRouteRow, ...]
    route_decision_distribution: dict[str, int]
    selected_strategy_id: ComparisonStrategyId
    selection_decision: str = Field(min_length=1)
    generation_eval_reports: dict[str, GenerationEvalReport]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def run_place_story_guarded_boost_comparison(
    *,
    chunks_path: Path = DEFAULT_CHUNKS_PATH,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    place_catalog_path: Path = DEFAULT_PLACE_CATALOG_PATH,
    embedding_cache_dir: Path = DEFAULT_EMBEDDING_CACHE_DIR,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
    top_k: int = DEFAULT_TOP_K,
    candidate_k: int = DEFAULT_CANDIDATE_K,
    max_context_chars: int = DEFAULT_MAX_CONTEXT_CHARS,
) -> PlaceStoryGuardedBoostComparisonReport:
    _validate_private_rows_path(result_rows_path, label="result")
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

    provisional = build_place_story_guarded_boost_comparison_report(
        baseline_bundles=baseline_bundles,
        candidate_bundles=candidate_bundles,
        top_k=top_k,
        candidate_k=candidate_k,
        max_context_chars=max_context_chars,
    )
    provisional_rows = build_public_place_story_guarded_boost_rows(provisional)
    provisional_text = build_place_story_guarded_boost_markdown(provisional)
    report = build_place_story_guarded_boost_comparison_report(
        baseline_bundles=baseline_bundles,
        candidate_bundles=candidate_bundles,
        top_k=top_k,
        candidate_k=candidate_k,
        max_context_chars=max_context_chars,
        result_rows=provisional_rows,
        report_text=provisional_text,
    )
    failures = collect_place_story_guarded_boost_failures(report)
    if failures:
        raise ValueError(f"place_story guarded boost comparison gate failed: {failures}")

    _write_jsonl_rows(
        path=result_rows_path,
        rows=build_public_place_story_guarded_boost_rows(report),
    )
    resolved_report_path = project_path(report_path)
    resolved_report_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_report_path.write_text(
        build_place_story_guarded_boost_markdown(report),
        encoding="utf-8",
    )
    return report


def build_place_story_guarded_boost_comparison_report(
    *,
    baseline_bundles: tuple[_StrategyInputBundle, ...],
    candidate_bundles: tuple[_StrategyInputBundle, ...],
    top_k: int,
    candidate_k: int,
    max_context_chars: int,
    result_rows: list[dict[str, Any]] | None = None,
    report_text: str = "",
) -> PlaceStoryGuardedBoostComparisonReport:
    baseline_by_query = _bundles_by_query_id(baseline_bundles)
    candidate_by_query = _bundles_by_query_id(candidate_bundles)
    baseline_records = _records_by_query_id(
        strategy_id=BASELINE_STRATEGY_ID,
        bundles=baseline_bundles,
    )
    candidate_records = _records_by_query_id(
        strategy_id=ALWAYS_BOOST_STRATEGY_ID,
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
    guarded_bundles = tuple(
        candidate_by_query[row.query_id]
        if row.selected_strategy_id == GUARDED_BOOST_STRATEGY_ID
        else baseline_by_query[row.query_id]
        for row in route_rows
    )
    generation_reports = {
        BASELINE_STRATEGY_ID: _generation_eval_report_for_bundles(
            strategy_id=BASELINE_STRATEGY_ID,
            bundles=baseline_bundles,
        ),
        ALWAYS_BOOST_STRATEGY_ID: _generation_eval_report_for_bundles(
            strategy_id=ALWAYS_BOOST_STRATEGY_ID,
            bundles=candidate_bundles,
        ),
        GUARDED_BOOST_STRATEGY_ID: _generation_eval_report_for_bundles(
            strategy_id=GUARDED_BOOST_STRATEGY_ID,
            bundles=guarded_bundles,
        ),
    }
    bundles_by_strategy = {
        BASELINE_STRATEGY_ID: baseline_bundles,
        ALWAYS_BOOST_STRATEGY_ID: candidate_bundles,
        GUARDED_BOOST_STRATEGY_ID: guarded_bundles,
    }
    summaries = tuple(
        build_guarded_strategy_summary(
            strategy_id=strategy_id,
            bundles=bundles_by_strategy[strategy_id],
            generation_report=generation_reports[strategy_id],
            route_rows=route_rows,
        )
        for strategy_id in (
            BASELINE_STRATEGY_ID,
            ALWAYS_BOOST_STRATEGY_ID,
            GUARDED_BOOST_STRATEGY_ID,
        )
    )
    deltas = tuple(build_guarded_strategy_deltas(summaries))
    selected_strategy_id, selection_decision = _select_guarded_strategy(summaries)
    comparison_id = _comparison_id(route_rows=route_rows, summaries=summaries)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=PLACE_STORY_GUARDED_BOOST_REPORT_VERSION,
        run_id=comparison_id,
        result_rows=result_rows or [],
        report_text=report_text,
    )
    report = PlaceStoryGuardedBoostComparisonReport(
        comparison_id=comparison_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        dataset_path_alias="<private retrieval eval dataset: retrieval_eval_dev.jsonl>",
        chunks_path_alias="<private parent_child_chunks report>",
        baseline_strategy_id=BASELINE_STRATEGY_ID,
        candidate_strategy_id=CANDIDATE_STRATEGY_ID,
        router_policy_id=ROUTER_POLICY_ID,
        top_k=top_k,
        candidate_k=candidate_k,
        max_context_chars=max_context_chars,
        resolved_device=resolve_torch_device("auto"),
        strategy_summaries=summaries,
        strategy_deltas=deltas,
        route_rows=route_rows,
        route_decision_distribution=_route_decision_distribution(route_rows),
        selected_strategy_id=selected_strategy_id,
        selection_decision=selection_decision,
        generation_eval_reports={str(key): value for key, value in generation_reports.items()},
        output_quality=output_quality,
        qualitative_assessment={},
    )
    return report.model_copy(
        update={"qualitative_assessment": build_guarded_qualitative_assessment(report)},
    )


def build_guarded_route_row(
    *,
    baseline_bundle: _StrategyInputBundle,
    candidate_bundle: _StrategyInputBundle,
    baseline_record: GenerationEvalRecord,
    candidate_record: GenerationEvalRecord,
) -> GuardedRouteRow:
    block_reason_tags = build_guardrail_block_reason_tags(
        baseline_bundle=baseline_bundle,
        candidate_bundle=candidate_bundle,
        baseline_record=baseline_record,
        candidate_record=candidate_record,
    )
    route_decision = _route_decision(block_reason_tags)
    candidate_selected = route_decision == "use_candidate_direct_gain"
    return GuardedRouteRow(
        query_id=baseline_record.query_id,
        query_type=baseline_record.query_type,
        split=baseline_record.split,
        router_policy_id=ROUTER_POLICY_ID,
        route_decision=route_decision,
        selected_strategy_id=(
            GUARDED_BOOST_STRATEGY_ID if candidate_selected else BASELINE_STRATEGY_ID
        ),
        blocked=not candidate_selected,
        block_reason_tags=block_reason_tags,
        direct_ready_delta=_bool_delta(
            baseline_bundle.input_stats.direct_evidence_ready,
            candidate_bundle.input_stats.direct_evidence_ready,
        ),
        correct_with_evidence_delta=_bool_delta(
            baseline_record.correct_with_evidence,
            candidate_record.correct_with_evidence,
        ),
        citation_precision_delta=round(
            candidate_record.citation_precision - baseline_record.citation_precision,
            6,
        ),
        citation_recall_delta=round(
            candidate_record.citation_recall - baseline_record.citation_recall,
            6,
        ),
        evidence_order_delta=round(
            candidate_bundle.input_stats.evidence_order_relevance_proxy
            - baseline_bundle.input_stats.evidence_order_relevance_proxy,
            6,
        ),
        duplicate_parent_rate_delta=round(
            candidate_bundle.evidence_pack.duplicate_parent_rate
            - baseline_bundle.evidence_pack.duplicate_parent_rate,
            6,
        ),
        input_latency_delta_ms=round(
            candidate_bundle.input_latency_ms - baseline_bundle.input_latency_ms,
            6,
        ),
        candidate_doc_covered=candidate_bundle.evidence_pack.target_doc_covered,
        candidate_context_buildable=candidate_bundle.input_stats.context_buildable,
    )


def build_guardrail_block_reason_tags(
    *,
    baseline_bundle: _StrategyInputBundle,
    candidate_bundle: _StrategyInputBundle,
    baseline_record: GenerationEvalRecord,
    candidate_record: GenerationEvalRecord,
) -> tuple[str, ...]:
    reasons: list[str] = []
    candidate_direct_ready = candidate_bundle.input_stats.direct_evidence_ready
    baseline_direct_ready = baseline_bundle.input_stats.direct_evidence_ready
    candidate_recall_gain = candidate_record.citation_recall > baseline_record.citation_recall
    gain_tags: list[str] = []
    if candidate_direct_ready and not baseline_direct_ready:
        gain_tags.append("direct_ready_gain")
    if candidate_recall_gain:
        gain_tags.append("citation_recall_gain")
    if not candidate_direct_ready:
        reasons.append("candidate_direct_missing")
    if baseline_direct_ready and not candidate_recall_gain:
        reasons.append("no_candidate_gain")
    if not candidate_bundle.evidence_pack.target_doc_covered:
        reasons.append("doc_coverage_loss")
    if (
        not candidate_bundle.input_stats.context_buildable
        or candidate_bundle.input_stats.truncated_evidence_count > 0
        or candidate_bundle.input_stats.context_budget_violation
    ):
        reasons.append("context_unstable")
    if baseline_record.correct_with_evidence and not candidate_record.correct_with_evidence:
        reasons.append("correctness_regression")
    if (
        candidate_record.citation_precision < baseline_record.citation_precision
        and candidate_record.citation_recall <= baseline_record.citation_recall
    ):
        reasons.append("precision_regression_without_recall_gain")
    evidence_order_delta = (
        candidate_bundle.input_stats.evidence_order_relevance_proxy
        - baseline_bundle.input_stats.evidence_order_relevance_proxy
    )
    if candidate_bundle.input_stats.evidence_order_relevance_proxy < MIN_EVIDENCE_ORDER:
        reasons.append("low_evidence_order")
    if evidence_order_delta < MAX_EVIDENCE_ORDER_DROP:
        reasons.append("evidence_order_drop")
    duplicate_parent_delta = (
        candidate_bundle.evidence_pack.duplicate_parent_rate
        - baseline_bundle.evidence_pack.duplicate_parent_rate
    )
    if duplicate_parent_delta > MAX_DUPLICATE_PARENT_RATE_DELTA:
        reasons.append("duplicate_parent_over_limit")
    if reasons:
        reasons.extend(gain_tags)
    else:
        reasons.append("candidate_passed_guardrail")
    return tuple(reasons)


def build_guarded_strategy_summary(
    *,
    strategy_id: ComparisonStrategyId,
    bundles: tuple[_StrategyInputBundle, ...],
    generation_report: GenerationEvalReport,
    route_rows: tuple[GuardedRouteRow, ...],
) -> GuardedBoostStrategySummary:
    summary = generation_report.summary
    input_stats = [bundle.input_stats for bundle in bundles]
    selected_candidate_count = (
        len(bundles)
        if strategy_id == ALWAYS_BOOST_STRATEGY_ID
        else sum(
            1
            for row in route_rows
            if row.selected_strategy_id == GUARDED_BOOST_STRATEGY_ID
        )
        if strategy_id == GUARDED_BOOST_STRATEGY_ID
        else 0
    )
    return GuardedBoostStrategySummary(
        strategy_id=strategy_id,
        eval_count=len(bundles),
        selected_candidate_count=selected_candidate_count,
        guardrail_block_count=(
            sum(1 for row in route_rows if row.blocked)
            if strategy_id == GUARDED_BOOST_STRATEGY_ID
            else 0
        ),
        context_build_success_rate=_mean_bool([item.context_buildable for item in input_stats]),
        direct_ready_rate=_mean_bool([item.direct_evidence_ready for item in input_stats]),
        correct_with_evidence_rate=summary.correct_with_evidence_rate,
        citation_precision=summary.citation_precision,
        citation_recall=summary.citation_recall,
        doc_coverage_rate=_mean_bool([bundle.evidence_pack.target_doc_covered for bundle in bundles]),
        evidence_order_relevance_proxy_avg=_mean_float(
            [item.evidence_order_relevance_proxy for item in input_stats],
        ),
        duplicate_parent_rate_avg=_mean_float(
            [bundle.evidence_pack.duplicate_parent_rate for bundle in bundles],
        ),
        avg_evidence_count=_mean_float([float(item.evidence_count) for item in input_stats]),
        input_latency_p95_ms=summary.latency_p95_ms,
        solar_call_count=summary.solar_call_count,
    )


def build_guarded_strategy_deltas(
    summaries: tuple[GuardedBoostStrategySummary, ...],
) -> list[GuardedBoostStrategyDelta]:
    baseline = next(
        summary for summary in summaries if summary.strategy_id == BASELINE_STRATEGY_ID
    )
    return [
        GuardedBoostStrategyDelta(
            compared_strategy_id=summary.strategy_id,
            direct_ready_rate_delta=round(
                summary.direct_ready_rate - baseline.direct_ready_rate,
                6,
            ),
            correct_with_evidence_rate_delta=round(
                summary.correct_with_evidence_rate
                - baseline.correct_with_evidence_rate,
                6,
            ),
            citation_precision_delta=round(
                summary.citation_precision - baseline.citation_precision,
                6,
            ),
            citation_recall_delta=round(
                summary.citation_recall - baseline.citation_recall,
                6,
            ),
            doc_coverage_rate_delta=round(
                summary.doc_coverage_rate - baseline.doc_coverage_rate,
                6,
            ),
            evidence_order_relevance_proxy_avg_delta=round(
                summary.evidence_order_relevance_proxy_avg
                - baseline.evidence_order_relevance_proxy_avg,
                6,
            ),
            duplicate_parent_rate_avg_delta=round(
                summary.duplicate_parent_rate_avg
                - baseline.duplicate_parent_rate_avg,
                6,
            ),
            input_latency_p95_ms_delta=round(
                summary.input_latency_p95_ms - baseline.input_latency_p95_ms,
                6,
            ),
        )
        for summary in summaries
    ]


def build_public_place_story_guarded_boost_rows(
    report: PlaceStoryGuardedBoostComparisonReport,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for summary in report.strategy_summaries:
        rows.append(
            {
                "comparison_id": report.comparison_id,
                "row_type": "strategy_summary",
                "strategy_id": summary.strategy_id,
                "eval_count": summary.eval_count,
                "selected_candidate_count": summary.selected_candidate_count,
                "guardrail_block_count": summary.guardrail_block_count,
                "context_build_success_rate": summary.context_build_success_rate,
                "direct_ready_rate": summary.direct_ready_rate,
                "correct_with_evidence_rate": summary.correct_with_evidence_rate,
                "citation_precision": summary.citation_precision,
                "citation_recall": summary.citation_recall,
                "doc_coverage_rate": summary.doc_coverage_rate,
                "evidence_order_relevance_proxy_avg": (
                    summary.evidence_order_relevance_proxy_avg
                ),
                "duplicate_parent_rate_avg": summary.duplicate_parent_rate_avg,
                "avg_evidence_count": summary.avg_evidence_count,
                "input_latency_p95_ms": summary.input_latency_p95_ms,
                "solar_call_count": summary.solar_call_count,
            },
        )
    for delta in report.strategy_deltas:
        rows.append(
            {
                "comparison_id": report.comparison_id,
                "row_type": "strategy_delta",
                "strategy_id": delta.compared_strategy_id,
                "baseline_strategy_id": delta.baseline_strategy_id,
                "direct_ready_rate_delta": delta.direct_ready_rate_delta,
                "correct_with_evidence_rate_delta": (
                    delta.correct_with_evidence_rate_delta
                ),
                "citation_precision_delta": delta.citation_precision_delta,
                "citation_recall_delta": delta.citation_recall_delta,
                "doc_coverage_rate_delta": delta.doc_coverage_rate_delta,
                "evidence_order_relevance_proxy_avg_delta": (
                    delta.evidence_order_relevance_proxy_avg_delta
                ),
                "duplicate_parent_rate_avg_delta": delta.duplicate_parent_rate_avg_delta,
                "input_latency_p95_ms_delta": delta.input_latency_p95_ms_delta,
            },
        )
    rows.extend(
        {
            "comparison_id": report.comparison_id,
            "row_type": "route_decision",
            "query_id": row.query_id,
            "query_type": row.query_type,
            "split": row.split,
            "router_policy_id": row.router_policy_id,
            "route_decision": row.route_decision,
            "selected_strategy_id": row.selected_strategy_id,
            "blocked": row.blocked,
            "block_reason_tags": row.block_reason_tags,
            "direct_ready_delta": row.direct_ready_delta,
            "correct_with_evidence_delta": row.correct_with_evidence_delta,
            "citation_precision_delta": row.citation_precision_delta,
            "citation_recall_delta": row.citation_recall_delta,
            "evidence_order_delta": row.evidence_order_delta,
            "duplicate_parent_rate_delta": row.duplicate_parent_rate_delta,
            "input_latency_delta_ms": row.input_latency_delta_ms,
        }
        for row in report.route_rows
    )
    return rows


def collect_place_story_guarded_boost_failures(
    report: PlaceStoryGuardedBoostComparisonReport,
) -> list[str]:
    failures: list[str] = []
    if not report.strategy_summaries:
        failures.append("empty_strategy_summaries")
    if any(summary.solar_call_count for summary in report.strategy_summaries):
        failures.append("solar_call_count_must_be_zero")
    for strategy_id, generation_report in report.generation_eval_reports.items():
        failures.extend(
            f"{strategy_id}:{failure}"
            for failure in collect_generation_eval_harness_failures(generation_report)
            if failure != "missing_citations"
        )
    if report.output_quality.public_raw_text_leakage_count:
        failures.append("public_raw_text_leakage")
    if report.output_quality.private_path_leakage_count:
        failures.append("private_path_leakage")
    if report.output_quality.secret_like_leakage_count:
        failures.append("secret_like_leakage")
    if report.output_quality.forbidden_result_field_count:
        failures.append("forbidden_public_result_fields")
    return failures


def build_place_story_guarded_boost_markdown(
    report: PlaceStoryGuardedBoostComparisonReport,
) -> str:
    summary_rows = "\n".join(_format_summary_row(row) for row in report.strategy_summaries)
    delta_rows = "\n".join(_format_delta_row(row) for row in report.strategy_deltas)
    route_rows = "\n".join(_format_route_row(row) for row in report.route_rows)
    decision_rows = "\n".join(
        f"| `{decision}` | {count} |"
        for decision, count in report.route_decision_distribution.items()
    )
    qualitative_rows = "\n".join(
        f"- `{key}`: {value}" for key, value in report.qualitative_assessment.items()
    )
    quality = report.output_quality
    return f"""# Place Story Guarded Boost Comparison Report

## 목적

`parent_doc_context_boost`를 전체 적용하지 않고 guardrail/router로 제한했을 때 input-only 품질이 어떻게 변하는지 비교한다.

이 문서는 Solar Pro 3 live generation 결과가 아니다. raw query, raw evidence, prompt, answer text는 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| comparison_id | `{report.comparison_id}` |
| generated_at_utc | `{report.generated_at_utc}` |
| dataset_path | `{report.dataset_path_alias}` |
| chunks_path | `{report.chunks_path_alias}` |
| baseline_strategy_id | `{report.baseline_strategy_id}` |
| candidate_strategy_id | `{report.candidate_strategy_id}` |
| router_policy_id | `{report.router_policy_id}` |
| top_k | {report.top_k} |
| candidate_k | {report.candidate_k} |
| max_context_chars | {report.max_context_chars} |
| resolved_device | `{report.resolved_device}` |
| selected_strategy_id | `{report.selected_strategy_id}` |
| selection_decision | `{report.selection_decision}` |

## Strategy Summary

| strategy_id | eval_count | selected_candidate | blocked | context_build | direct_ready | Correct-with-Evidence | citation_precision | citation_recall | doc_coverage | evidence_order | duplicate_parent | avg_evidence | latency_p95_ms | solar_calls |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{summary_rows}

## Baseline Delta

| compared_strategy_id | direct_ready delta | Correct delta | precision delta | recall delta | doc delta | evidence_order delta | duplicate_parent delta | latency_p95_ms delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{delta_rows}

## Route Decision Distribution

| route_decision | count |
| --- | ---: |
{decision_rows}

## Query-level Sanitized Routes

| query_id | decision | selected | blocked | direct_delta | correct_delta | precision_delta | recall_delta | order_delta | reason_tags |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
{route_rows}

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

{_conclusion_text(report)}
"""


def build_guarded_qualitative_assessment(
    report: PlaceStoryGuardedBoostComparisonReport,
) -> dict[str, str]:
    return {
        "comparison_scope": (
            "baseline, always_boost, guarded_boost를 같은 place_story dev query set에서 비교했다."
        ),
        "guardrail_boundary": (
            "guarded_boost는 candidate가 hard block 조건을 통과할 때만 candidate evidence를 사용한다."
        ),
        "llm_call_boundary": "Solar Pro 3 호출 없이 input-only citation assembly만 평가했다.",
        "data_mart_grain": (
            "`fact_place_story_guarded_boost`의 grain은 query-router_policy-candidate_strategy다."
        ),
        "security_boundary": (
            "public artifact에는 raw query, raw evidence, prompt, answer text를 기록하지 않는다."
        ),
        "next_action": _next_action(report),
    }


def _generation_eval_report_for_bundles(
    *,
    strategy_id: str,
    bundles: tuple[_StrategyInputBundle, ...],
) -> GenerationEvalReport:
    return build_generation_eval_report(
        inputs=[
            GenerationEvalInput(
                item=bundle.item,
                answer=bundle.answer,
                packing_policy_id=bundle.evidence_pack.policy_id,
                retrieval_run_label=strategy_id,
                provider_config_id=INPUT_ONLY_PROVIDER_CONFIG_ID,
                usage=GenerationEvalUsage(latency_ms=bundle.input_latency_ms),
            )
            for bundle in bundles
        ],
    )


def _records_by_query_id(
    *,
    strategy_id: str,
    bundles: tuple[_StrategyInputBundle, ...],
) -> dict[str, GenerationEvalRecord]:
    records = build_generation_eval_records(
        inputs=[
            GenerationEvalInput(
                item=bundle.item,
                answer=bundle.answer,
                packing_policy_id=bundle.evidence_pack.policy_id,
                retrieval_run_label=strategy_id,
                provider_config_id=INPUT_ONLY_PROVIDER_CONFIG_ID,
                usage=GenerationEvalUsage(latency_ms=bundle.input_latency_ms),
            )
            for bundle in bundles
        ],
    )
    return {record.query_id: record for record in records}


def _route_decision(block_reason_tags: tuple[str, ...]) -> RouteDecision:
    reason_set = set(block_reason_tags)
    if reason_set == {"candidate_passed_guardrail"}:
        return "use_candidate_direct_gain"
    if "correctness_regression" in reason_set:
        return "use_baseline_correctness_guardrail"
    if "doc_coverage_loss" in reason_set:
        return "use_baseline_doc_guardrail"
    if {
        "precision_regression_without_recall_gain",
        "low_evidence_order",
        "evidence_order_drop",
        "duplicate_parent_over_limit",
    } & reason_set:
        if "citation_recall_gain" in reason_set or "direct_ready_gain" in reason_set:
            return "manual_review_required"
        return "use_baseline_precision_guardrail"
    return "use_baseline_no_candidate_gain"


def _select_guarded_strategy(
    summaries: tuple[GuardedBoostStrategySummary, ...],
) -> tuple[ComparisonStrategyId, str]:
    baseline = next(item for item in summaries if item.strategy_id == BASELINE_STRATEGY_ID)
    guarded = next(item for item in summaries if item.strategy_id == GUARDED_BOOST_STRATEGY_ID)
    if (
        guarded.correct_with_evidence_rate >= baseline.correct_with_evidence_rate
        and guarded.citation_precision >= baseline.citation_precision
        and guarded.citation_recall >= baseline.citation_recall
        and guarded.direct_ready_rate >= baseline.direct_ready_rate
        and guarded.selected_candidate_count > 0
    ):
        return GUARDED_BOOST_STRATEGY_ID, "promote_guarded_to_live_plan_review"
    if (
        guarded.correct_with_evidence_rate >= baseline.correct_with_evidence_rate
        and guarded.citation_precision >= baseline.citation_precision
    ):
        return GUARDED_BOOST_STRATEGY_ID, "guardrail_safe_but_too_conservative"
    return BASELINE_STRATEGY_ID, "reject_guardrail_policy"


def _route_decision_distribution(
    route_rows: tuple[GuardedRouteRow, ...],
) -> dict[str, int]:
    return dict(sorted(Counter(row.route_decision for row in route_rows).items()))


def _bundles_by_query_id(
    bundles: tuple[_StrategyInputBundle, ...],
) -> dict[str, _StrategyInputBundle]:
    return {bundle.item.query.query_id: bundle for bundle in bundles}


def _comparison_id(
    *,
    route_rows: tuple[GuardedRouteRow, ...],
    summaries: tuple[GuardedBoostStrategySummary, ...],
) -> str:
    payload = {
        "route_rows": [row.model_dump(mode="json") for row in route_rows],
        "summaries": [row.model_dump(mode="json") for row in summaries],
    }
    digest = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"),
    ).hexdigest()[:8]
    return f"place-story-guarded-boost-q{len(route_rows)}-{digest}"


def _bool_delta(baseline: bool, candidate: bool) -> int:
    return int(candidate) - int(baseline)


def _mean_bool(values: list[bool]) -> float:
    if not values:
        return 0.0
    return round(sum(1 for value in values if value) / len(values), 6)


def _mean_float(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 6)


def _format_summary_row(summary: GuardedBoostStrategySummary) -> str:
    return (
        f"| `{summary.strategy_id}` | {summary.eval_count} | "
        f"{summary.selected_candidate_count} | {summary.guardrail_block_count} | "
        f"{summary.context_build_success_rate:.6f} | "
        f"{summary.direct_ready_rate:.6f} | "
        f"{summary.correct_with_evidence_rate:.6f} | "
        f"{summary.citation_precision:.6f} | {summary.citation_recall:.6f} | "
        f"{summary.doc_coverage_rate:.6f} | "
        f"{summary.evidence_order_relevance_proxy_avg:.6f} | "
        f"{summary.duplicate_parent_rate_avg:.6f} | "
        f"{summary.avg_evidence_count:.6f} | "
        f"{summary.input_latency_p95_ms:.6f} | {summary.solar_call_count} |"
    )


def _format_delta_row(delta: GuardedBoostStrategyDelta) -> str:
    return (
        f"| `{delta.compared_strategy_id}` | "
        f"{delta.direct_ready_rate_delta:.6f} | "
        f"{delta.correct_with_evidence_rate_delta:.6f} | "
        f"{delta.citation_precision_delta:.6f} | "
        f"{delta.citation_recall_delta:.6f} | "
        f"{delta.doc_coverage_rate_delta:.6f} | "
        f"{delta.evidence_order_relevance_proxy_avg_delta:.6f} | "
        f"{delta.duplicate_parent_rate_avg_delta:.6f} | "
        f"{delta.input_latency_p95_ms_delta:.6f} |"
    )


def _format_route_row(row: GuardedRouteRow) -> str:
    reasons = ", ".join(f"`{reason}`" for reason in row.block_reason_tags)
    return (
        f"| `{row.query_id}` | `{row.route_decision}` | "
        f"`{row.selected_strategy_id}` | {row.blocked} | "
        f"{row.direct_ready_delta} | {row.correct_with_evidence_delta} | "
        f"{row.citation_precision_delta:.6f} | {row.citation_recall_delta:.6f} | "
        f"{row.evidence_order_delta:.6f} | {reasons} |"
    )


def _next_action(report: PlaceStoryGuardedBoostComparisonReport) -> str:
    if report.selection_decision == "promote_guarded_to_live_plan_review":
        return "Solar Pro 3 live paired comparison 계획을 작성하되 실행 전 별도 승인을 받는다."
    if report.selection_decision == "guardrail_safe_but_too_conservative":
        return "guardrail threshold를 완화할지 또는 hard-case router 조건을 좁힐지 추가 설계한다."
    return "guardrail 정책을 재설계하거나 baseline 유지 결정을 문서화한다."


def _conclusion_text(report: PlaceStoryGuardedBoostComparisonReport) -> str:
    if report.selection_decision == "promote_guarded_to_live_plan_review":
        return (
            "`guarded_boost`는 input-only gate에서 baseline 안전성을 유지하며 candidate 이득을 일부 보존했다."
        )
    if report.selection_decision == "guardrail_safe_but_too_conservative":
        return (
            "`guarded_boost`는 correctness/precision regression을 차단했지만 candidate 적용 폭이 제한적이다. "
            "현재 기준으로는 안전하지만 보수적인 정책이다."
        )
    return "`guarded_boost`는 현재 guardrail 기준에서 baseline보다 안정적이지 않다."


def main() -> int:
    args = _parse_args()
    report = run_place_story_guarded_boost_comparison(
        chunks_path=args.chunks,
        dataset_path=args.dataset,
        place_catalog_path=args.place_catalog,
        embedding_cache_dir=args.embedding_cache_dir,
        report_path=args.report,
        result_rows_path=args.result_rows,
        top_k=args.top_k,
        candidate_k=args.candidate_k,
        max_context_chars=args.max_context_chars,
    )
    failures = collect_place_story_guarded_boost_failures(report)
    guarded = next(
        item
        for item in report.strategy_summaries
        if item.strategy_id == GUARDED_BOOST_STRATEGY_ID
    )
    print(
        "place_story_guarded_boost_comparison "
        f"status={'PASS' if not failures else 'FAIL'} "
        f"decision={report.selection_decision} "
        f"selected_candidate={guarded.selected_candidate_count} "
        f"blocked={guarded.guardrail_block_count} "
        f"device={report.resolved_device} "
        f"failures={len(failures)}",
    )
    return 0 if not failures else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run place_story baseline vs always boost vs guarded boost comparison.",
    )
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS_PATH)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--place-catalog", type=Path, default=DEFAULT_PLACE_CATALOG_PATH)
    parser.add_argument("--embedding-cache-dir", type=Path, default=DEFAULT_EMBEDDING_CACHE_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--result-rows", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument("--candidate-k", type=int, default=DEFAULT_CANDIDATE_K)
    parser.add_argument("--max-context-chars", type=int, default=DEFAULT_MAX_CONTEXT_CHARS)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
