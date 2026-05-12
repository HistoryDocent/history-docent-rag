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
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    measure_public_retrieval_artifact_quality,
)
from app.infrastructure.index.device import resolve_torch_device
from pipelines.run_place_story_target_grain_coverage import (
    PlaceStoryTargetGrainCoverageRow,
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
    _run_strategy_for_item,
    _validate_private_rows_path,
    _write_jsonl_rows,
)
from pipelines.run_solar_live_generation_smoke import DEFAULT_CHUNKS_PATH, DEFAULT_DATASET_PATH


PLACE_STORY_FULL_DEV_GENERATION_INPUT_IMPACT_REPORT_VERSION = (
    "place-story-full-dev-generation-input-impact-report/v1"
)
DEFAULT_REPORT_PATH = (
    Path("evals")
    / "reports"
    / "place_story_full_dev_generation_input_impact_report.md"
)
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "place_story_full_dev_generation_input_impact_rows.jsonl"
)
FULL_DEV_STRATEGIES: tuple[StrategyId, ...] = (
    BASELINE_STRATEGY_ID,
    "parent_doc_context_boost",
)

SelectionDecision = Literal[
    "promote_to_generation_input_eval",
    "keep_candidate_for_hard_subset_only",
    "reject_candidate",
]


class PlaceStoryFullDevModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PlaceStoryFullDevStrategySummary(PlaceStoryFullDevModel):
    strategy_id: StrategyId
    query_count: int = Field(ge=0)
    target_child_recall_at_1: float = Field(ge=0.0, le=1.0)
    target_child_recall_at_3: float = Field(ge=0.0, le=1.0)
    target_child_recall_at_5: float = Field(ge=0.0, le=1.0)
    target_parent_recall_at_1: float = Field(ge=0.0, le=1.0)
    target_parent_recall_at_3: float = Field(ge=0.0, le=1.0)
    target_parent_recall_at_5: float = Field(ge=0.0, le=1.0)
    target_doc_recall_at_5: float = Field(ge=0.0, le=1.0)
    child_or_parent_recall_at_5: float = Field(ge=0.0, le=1.0)
    generation_input_ready_rate: float = Field(ge=0.0, le=1.0)
    doc_only_covered_count: int = Field(ge=0)
    full_grain_miss_count: int = Field(ge=0)
    hard_case_count: int = Field(ge=0)
    mrr: float = Field(ge=0.0, le=1.0)
    ndcg_at_5: float = Field(ge=0.0, le=1.0)
    latency_p95_ms: float = Field(ge=0.0)
    citation_recoverability_avg: float = Field(ge=0.0, le=1.0)
    evidence_order_relevance_proxy_avg: float = Field(ge=0.0, le=1.0)
    duplicate_parent_rate_avg: float = Field(ge=0.0, le=1.0)
    duplicate_doc_rate_avg: float = Field(ge=0.0, le=1.0)


class PlaceStoryGenerationInputImpactDelta(PlaceStoryFullDevModel):
    compared_strategy_id: StrategyId
    baseline_strategy_id: StrategyId = BASELINE_STRATEGY_ID
    child_or_parent_recall_at_5_delta: float
    generation_input_ready_rate_delta: float
    target_child_recall_at_5_delta: float
    target_parent_recall_at_5_delta: float
    target_doc_recall_at_5_delta: float
    doc_only_covered_count_delta: int
    full_grain_miss_count_delta: int
    hard_case_count_delta: int
    mrr_delta: float
    ndcg_at_5_delta: float
    latency_p95_ms_delta: float
    citation_recoverability_avg_delta: float
    evidence_order_relevance_proxy_avg_delta: float
    duplicate_parent_rate_avg_delta: float
    direct_evidence_improved_query_count: int = Field(ge=0)
    direct_evidence_regressed_query_count: int = Field(ge=0)
    doc_only_to_direct_query_count: int = Field(ge=0)
    direct_to_doc_only_or_miss_query_count: int = Field(ge=0)


class PlaceStoryFullDevGenerationInputImpactReport(PlaceStoryFullDevModel):
    report_version: str = PLACE_STORY_FULL_DEV_GENERATION_INPUT_IMPACT_REPORT_VERSION
    comparison_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    dataset_path_alias: str = Field(min_length=1)
    chunks_path_alias: str = Field(min_length=1)
    place_catalog_path: str = Field(min_length=1)
    top_k: int = Field(ge=1)
    candidate_k: int = Field(ge=1)
    resolved_device: str = Field(min_length=1)
    strategy_summaries: tuple[PlaceStoryFullDevStrategySummary, ...]
    strategy_deltas: tuple[PlaceStoryGenerationInputImpactDelta, ...]
    selected_strategy_id: StrategyId
    selection_decision: SelectionDecision
    selection_reason: str = Field(min_length=1)
    failure_tag_distribution_by_strategy: dict[str, dict[str, int]]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def run_place_story_full_dev_generation_input_impact(
    *,
    chunks_path: Path = DEFAULT_CHUNKS_PATH,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    place_catalog_path: Path = DEFAULT_PLACE_CATALOG_PATH,
    embedding_cache_dir: Path = DEFAULT_EMBEDDING_CACHE_DIR,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
    top_k: int = DEFAULT_TOP_K,
    candidate_k: int = DEFAULT_CANDIDATE_K,
) -> PlaceStoryFullDevGenerationInputImpactReport:
    _validate_private_rows_path(result_rows_path, label="result")
    items = _load_place_story_dev_items(dataset_path=dataset_path)
    context = _build_execution_context(
        chunks_path=chunks_path,
        place_catalog_path=place_catalog_path,
        embedding_cache_dir=embedding_cache_dir,
    )
    rows_by_strategy = {
        strategy_id: tuple(
            _run_strategy_for_item(
                item=item,
                strategy_id=strategy_id,
                context=context,
                top_k=top_k,
                candidate_k=candidate_k,
            )
            for item in items
        )
        for strategy_id in FULL_DEV_STRATEGIES
    }

    provisional = build_place_story_full_dev_generation_input_impact_report(
        rows_by_strategy=rows_by_strategy,
        chunks_path=chunks_path,
        dataset_path=dataset_path,
        place_catalog_path=place_catalog_path,
        top_k=top_k,
        candidate_k=candidate_k,
    )
    provisional_rows = build_public_place_story_full_dev_generation_input_impact_rows(
        provisional,
    )
    provisional_text = build_place_story_full_dev_generation_input_impact_markdown(
        provisional,
    )
    report = build_place_story_full_dev_generation_input_impact_report(
        rows_by_strategy=rows_by_strategy,
        chunks_path=chunks_path,
        dataset_path=dataset_path,
        place_catalog_path=place_catalog_path,
        top_k=top_k,
        candidate_k=candidate_k,
        result_rows=provisional_rows,
        report_text=provisional_text,
    )
    failures = collect_place_story_full_dev_generation_input_impact_failures(report)
    if failures:
        raise ValueError(f"place story full dev input impact gate failed: {failures}")

    _write_jsonl_rows(
        path=result_rows_path,
        rows=build_public_place_story_full_dev_generation_input_impact_rows(report),
    )
    resolved_report_path = project_path(report_path)
    resolved_report_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_report_path.write_text(
        build_place_story_full_dev_generation_input_impact_markdown(report),
        encoding="utf-8",
    )
    return report


def build_place_story_full_dev_generation_input_impact_report(
    *,
    rows_by_strategy: dict[StrategyId, tuple[PlaceStoryTargetGrainCoverageRow, ...]],
    chunks_path: Path,
    dataset_path: Path,
    place_catalog_path: Path,
    top_k: int,
    candidate_k: int,
    result_rows: list[dict[str, Any]] | None = None,
    report_text: str = "",
) -> PlaceStoryFullDevGenerationInputImpactReport:
    summaries = tuple(
        build_full_dev_strategy_summary(
            strategy_id=strategy_id,
            rows=rows_by_strategy[strategy_id],
        )
        for strategy_id in FULL_DEV_STRATEGIES
        if strategy_id in rows_by_strategy
    )
    deltas = tuple(build_full_dev_strategy_deltas(rows_by_strategy, summaries))
    selected_strategy_id, decision, reason = _select_full_dev_strategy(summaries, deltas)
    comparison_id = _comparison_id(rows_by_strategy)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=PLACE_STORY_FULL_DEV_GENERATION_INPUT_IMPACT_REPORT_VERSION,
        run_id=comparison_id,
        result_rows=result_rows or [],
        report_text=report_text,
    )
    report = PlaceStoryFullDevGenerationInputImpactReport(
        comparison_id=comparison_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        dataset_path_alias="<private retrieval eval dataset: retrieval_eval_dev.jsonl>",
        chunks_path_alias="<private parent_child_chunks report>",
        place_catalog_path=place_catalog_path.as_posix(),
        top_k=top_k,
        candidate_k=candidate_k,
        resolved_device=resolve_torch_device("auto"),
        strategy_summaries=summaries,
        strategy_deltas=deltas,
        selected_strategy_id=selected_strategy_id,
        selection_decision=decision,
        selection_reason=reason,
        failure_tag_distribution_by_strategy=_failure_tag_distribution_by_strategy(
            rows_by_strategy,
        ),
        output_quality=output_quality,
        qualitative_assessment={},
    )
    return report.model_copy(
        update={
            "qualitative_assessment": build_full_dev_qualitative_assessment(report),
        },
    )


def build_full_dev_strategy_summary(
    *,
    strategy_id: StrategyId,
    rows: tuple[PlaceStoryTargetGrainCoverageRow, ...],
) -> PlaceStoryFullDevStrategySummary:
    return PlaceStoryFullDevStrategySummary(
        strategy_id=strategy_id,
        query_count=len(rows),
        target_child_recall_at_1=_recall_at(rows, grain="child", k=1),
        target_child_recall_at_3=_recall_at(rows, grain="child", k=3),
        target_child_recall_at_5=_recall_at(rows, grain="child", k=5),
        target_parent_recall_at_1=_recall_at(rows, grain="parent", k=1),
        target_parent_recall_at_3=_recall_at(rows, grain="parent", k=3),
        target_parent_recall_at_5=_recall_at(rows, grain="parent", k=5),
        target_doc_recall_at_5=_recall_at(rows, grain="doc", k=5),
        child_or_parent_recall_at_5=_mean_bool(
            [_direct_evidence_covered(row) for row in rows],
        ),
        generation_input_ready_rate=_mean_bool(
            [
                _direct_evidence_covered(row)
                and row.citation_recoverability >= 1.0
                for row in rows
            ],
        ),
        doc_only_covered_count=sum(1 for row in rows if _doc_only_covered(row)),
        full_grain_miss_count=sum(1 for row in rows if _full_grain_miss(row)),
        hard_case_count=sum(1 for row in rows if row.hard_case),
        mrr=_mean_float([row.reciprocal_rank for row in rows]),
        ndcg_at_5=_mean_float([row.ndcg_at_5 for row in rows]),
        latency_p95_ms=_percentile_float([row.total_latency_ms for row in rows], 0.95),
        citation_recoverability_avg=_mean_float(
            [row.citation_recoverability for row in rows],
        ),
        evidence_order_relevance_proxy_avg=_mean_float(
            [row.evidence_order_relevance_proxy for row in rows],
        ),
        duplicate_parent_rate_avg=_mean_float(
            [row.duplicate_parent_rate for row in rows],
        ),
        duplicate_doc_rate_avg=_mean_float([row.duplicate_doc_rate for row in rows]),
    )


def build_full_dev_strategy_deltas(
    rows_by_strategy: dict[StrategyId, tuple[PlaceStoryTargetGrainCoverageRow, ...]],
    summaries: tuple[PlaceStoryFullDevStrategySummary, ...],
) -> list[PlaceStoryGenerationInputImpactDelta]:
    baseline = next(
        summary for summary in summaries if summary.strategy_id == BASELINE_STRATEGY_ID
    )
    baseline_rows = rows_by_strategy[BASELINE_STRATEGY_ID]
    deltas: list[PlaceStoryGenerationInputImpactDelta] = []
    for summary in summaries:
        compared_rows = rows_by_strategy[summary.strategy_id]
        impact = _paired_direct_evidence_impact(
            baseline_rows=baseline_rows,
            compared_rows=compared_rows,
        )
        deltas.append(
            PlaceStoryGenerationInputImpactDelta(
                compared_strategy_id=summary.strategy_id,
                child_or_parent_recall_at_5_delta=round(
                    summary.child_or_parent_recall_at_5
                    - baseline.child_or_parent_recall_at_5,
                    6,
                ),
                generation_input_ready_rate_delta=round(
                    summary.generation_input_ready_rate
                    - baseline.generation_input_ready_rate,
                    6,
                ),
                target_child_recall_at_5_delta=round(
                    summary.target_child_recall_at_5 - baseline.target_child_recall_at_5,
                    6,
                ),
                target_parent_recall_at_5_delta=round(
                    summary.target_parent_recall_at_5
                    - baseline.target_parent_recall_at_5,
                    6,
                ),
                target_doc_recall_at_5_delta=round(
                    summary.target_doc_recall_at_5 - baseline.target_doc_recall_at_5,
                    6,
                ),
                doc_only_covered_count_delta=(
                    summary.doc_only_covered_count - baseline.doc_only_covered_count
                ),
                full_grain_miss_count_delta=(
                    summary.full_grain_miss_count - baseline.full_grain_miss_count
                ),
                hard_case_count_delta=summary.hard_case_count - baseline.hard_case_count,
                mrr_delta=round(summary.mrr - baseline.mrr, 6),
                ndcg_at_5_delta=round(summary.ndcg_at_5 - baseline.ndcg_at_5, 6),
                latency_p95_ms_delta=round(
                    summary.latency_p95_ms - baseline.latency_p95_ms,
                    6,
                ),
                citation_recoverability_avg_delta=round(
                    summary.citation_recoverability_avg
                    - baseline.citation_recoverability_avg,
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
                direct_evidence_improved_query_count=impact[
                    "direct_evidence_improved_query_count"
                ],
                direct_evidence_regressed_query_count=impact[
                    "direct_evidence_regressed_query_count"
                ],
                doc_only_to_direct_query_count=impact["doc_only_to_direct_query_count"],
                direct_to_doc_only_or_miss_query_count=impact[
                    "direct_to_doc_only_or_miss_query_count"
                ],
            ),
        )
    return deltas


def build_public_place_story_full_dev_generation_input_impact_rows(
    report: PlaceStoryFullDevGenerationInputImpactReport,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for summary in report.strategy_summaries:
        rows.append(
            {
                "comparison_id": report.comparison_id,
                "row_type": "strategy_summary",
                "strategy_id": summary.strategy_id,
                "query_count": summary.query_count,
                "child_or_parent_recall_at_5": summary.child_or_parent_recall_at_5,
                "generation_input_ready_rate": summary.generation_input_ready_rate,
                "target_child_recall_at_5": summary.target_child_recall_at_5,
                "target_parent_recall_at_5": summary.target_parent_recall_at_5,
                "target_doc_recall_at_5": summary.target_doc_recall_at_5,
                "doc_only_covered_count": summary.doc_only_covered_count,
                "full_grain_miss_count": summary.full_grain_miss_count,
                "hard_case_count": summary.hard_case_count,
                "mrr": summary.mrr,
                "ndcg_at_5": summary.ndcg_at_5,
                "latency_p95_ms": summary.latency_p95_ms,
                "citation_recoverability_avg": summary.citation_recoverability_avg,
                "evidence_order_relevance_proxy_avg": (
                    summary.evidence_order_relevance_proxy_avg
                ),
                "duplicate_parent_rate_avg": summary.duplicate_parent_rate_avg,
            },
        )
    for delta in report.strategy_deltas:
        rows.append(
            {
                "comparison_id": report.comparison_id,
                "row_type": "strategy_delta",
                "strategy_id": delta.compared_strategy_id,
                "baseline_strategy_id": delta.baseline_strategy_id,
                "child_or_parent_recall_at_5_delta": (
                    delta.child_or_parent_recall_at_5_delta
                ),
                "generation_input_ready_rate_delta": (
                    delta.generation_input_ready_rate_delta
                ),
                "mrr_delta": delta.mrr_delta,
                "ndcg_at_5_delta": delta.ndcg_at_5_delta,
                "latency_p95_ms_delta": delta.latency_p95_ms_delta,
                "direct_evidence_improved_query_count": (
                    delta.direct_evidence_improved_query_count
                ),
                "direct_evidence_regressed_query_count": (
                    delta.direct_evidence_regressed_query_count
                ),
            },
        )
    return rows


def collect_place_story_full_dev_generation_input_impact_failures(
    report: PlaceStoryFullDevGenerationInputImpactReport,
) -> list[str]:
    failures: list[str] = []
    if not report.strategy_summaries:
        failures.append("empty_strategy_summaries")
    if report.output_quality.public_raw_text_leakage_count:
        failures.append("public_raw_text_leakage")
    if report.output_quality.private_path_leakage_count:
        failures.append("private_path_leakage")
    if report.output_quality.secret_like_leakage_count:
        failures.append("secret_like_leakage")
    if report.output_quality.forbidden_result_field_count:
        failures.append("forbidden_public_result_fields")
    return failures


def build_place_story_full_dev_generation_input_impact_markdown(
    report: PlaceStoryFullDevGenerationInputImpactReport,
) -> str:
    summary_rows = "\n".join(_format_summary_row(row) for row in report.strategy_summaries)
    delta_rows = "\n".join(_format_delta_row(row) for row in report.strategy_deltas)
    tag_rows = "\n".join(
        _format_tag_distribution_rows(strategy_id, distribution)
        for strategy_id, distribution in report.failure_tag_distribution_by_strategy.items()
    )
    qualitative_rows = "\n".join(
        f"- `{key}`: {value}" for key, value in report.qualitative_assessment.items()
    )
    quality = report.output_quality
    return f"""# Place Story Full Dev Generation Input Impact Report

## 목적

`parent_doc_context_boost`가 full `place_story` dev query에서 generation 입력 품질을 실제로 개선하는지 검증한다.

이 문서는 청킹 재실험 결과가 아니며 Solar Pro 3 live 호출 결과도 아니다. 같은 private dev split, 같은 parent-child chunk corpus, 같은 `P0_rank_order` evidence packing을 유지한다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| comparison_id | `{report.comparison_id}` |
| generated_at_utc | `{report.generated_at_utc}` |
| dataset_path | `{report.dataset_path_alias}` |
| chunks_path | `{report.chunks_path_alias}` |
| place_catalog_path | `data_samples/place_catalog_seed.json` |
| top_k | {report.top_k} |
| candidate_k | {report.candidate_k} |
| resolved_device | `{report.resolved_device}` |
| selected_strategy_id | `{report.selected_strategy_id}` |
| selection_decision | `{report.selection_decision}` |
| selection_reason | {report.selection_reason} |

## Strategy Summary

| strategy_id | query_count | child@1 | child@3 | child@5 | parent@1 | parent@3 | parent@5 | doc@5 | child_or_parent@5 | input_ready | doc_only | full_miss | hard_case | MRR | nDCG@5 | latency_p95_ms | citation | evidence_order | duplicate_parent |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{summary_rows}

## Baseline Delta

| compared_strategy_id | child_or_parent@5 delta | input_ready delta | child@5 delta | parent@5 delta | doc@5 delta | doc_only delta | full_miss delta | hard_case delta | MRR delta | nDCG@5 delta | latency_p95_ms delta | evidence_order delta | direct improve | direct regress |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{delta_rows}

## Failure Tag Distribution

| strategy_id | failure_tag | count |
| --- | --- | ---: |
{tag_rows}

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


def build_full_dev_qualitative_assessment(
    report: PlaceStoryFullDevGenerationInputImpactReport,
) -> dict[str, str]:
    return {
        "comparison_scope": (
            "baseline과 parent/doc context boost를 full place_story dev query에서 비교했다."
        ),
        "generation_input_boundary": (
            "generation_input_ready는 child 또는 parent 직접 근거가 있고 citation recoverability가 1.0인 query 비율이다."
        ),
        "chunking_decision": (
            "이번 결과는 청킹 재실험이 아니다. chunk corpus와 evidence packing 정책을 고정했다."
        ),
        "selection_boundary": (
            "선택 판단은 private dev 기준이다. locked test와 Solar Pro 3 generation 평가 전 최종 개선 주장으로 쓰지 않는다."
        ),
        "security_boundary": (
            "public report/result에는 raw query, raw evidence, chunk text, private path, secret을 기록하지 않는다."
        ),
        "data_mart_grain": (
            "`fact_place_story_generation_input_impact`의 grain은 strategy-query이며, 공개 산출물에는 strategy aggregate와 paired delta만 남긴다."
        ),
        "next_action": _next_action(report),
    }


def _select_full_dev_strategy(
    summaries: tuple[PlaceStoryFullDevStrategySummary, ...],
    deltas: tuple[PlaceStoryGenerationInputImpactDelta, ...],
) -> tuple[StrategyId, SelectionDecision, str]:
    baseline = next(
        summary for summary in summaries if summary.strategy_id == BASELINE_STRATEGY_ID
    )
    candidate = next(
        summary
        for summary in summaries
        if summary.strategy_id == "parent_doc_context_boost"
    )
    candidate_delta = next(
        delta
        for delta in deltas
        if delta.compared_strategy_id == "parent_doc_context_boost"
    )
    if (
        candidate.child_or_parent_recall_at_5 > baseline.child_or_parent_recall_at_5
        and candidate.generation_input_ready_rate >= baseline.generation_input_ready_rate
        and candidate_delta.direct_evidence_regressed_query_count == 0
    ):
        return (
            "parent_doc_context_boost",
            "promote_to_generation_input_eval",
            "full dev에서 직접 근거 coverage가 개선되고 direct evidence regression이 없어 generation 입력 평가 후보로 승격한다.",
        )
    if candidate_delta.direct_evidence_improved_query_count > (
        candidate_delta.direct_evidence_regressed_query_count
    ):
        return (
            "parent_doc_context_boost",
            "keep_candidate_for_hard_subset_only",
            "개선 query가 더 많지만 full dev 평균 또는 rank 품질 trade-off가 있어 제한 후보로만 유지한다.",
        )
    return (
        BASELINE_STRATEGY_ID,
        "reject_candidate",
        "full dev에서 직접 근거 coverage 개선 근거가 부족해 baseline을 유지한다.",
    )


def _paired_direct_evidence_impact(
    *,
    baseline_rows: tuple[PlaceStoryTargetGrainCoverageRow, ...],
    compared_rows: tuple[PlaceStoryTargetGrainCoverageRow, ...],
) -> dict[str, int]:
    baseline_by_query = {row.query_id: row for row in baseline_rows}
    compared_by_query = {row.query_id: row for row in compared_rows}
    impact = Counter[str]()
    for query_id, baseline_row in baseline_by_query.items():
        compared_row = compared_by_query.get(query_id)
        if compared_row is None:
            continue
        baseline_direct = _direct_evidence_covered(baseline_row)
        compared_direct = _direct_evidence_covered(compared_row)
        if not baseline_direct and compared_direct:
            impact["direct_evidence_improved_query_count"] += 1
        if baseline_direct and not compared_direct:
            impact["direct_evidence_regressed_query_count"] += 1
        if _doc_only_covered(baseline_row) and compared_direct:
            impact["doc_only_to_direct_query_count"] += 1
        if baseline_direct and (_doc_only_covered(compared_row) or _full_grain_miss(compared_row)):
            impact["direct_to_doc_only_or_miss_query_count"] += 1
    return {
        "direct_evidence_improved_query_count": impact[
            "direct_evidence_improved_query_count"
        ],
        "direct_evidence_regressed_query_count": impact[
            "direct_evidence_regressed_query_count"
        ],
        "doc_only_to_direct_query_count": impact["doc_only_to_direct_query_count"],
        "direct_to_doc_only_or_miss_query_count": impact[
            "direct_to_doc_only_or_miss_query_count"
        ],
    }


def _failure_tag_distribution_by_strategy(
    rows_by_strategy: dict[StrategyId, tuple[PlaceStoryTargetGrainCoverageRow, ...]],
) -> dict[str, dict[str, int]]:
    distribution: dict[str, dict[str, int]] = {}
    for strategy_id, rows in rows_by_strategy.items():
        counter: Counter[str] = Counter()
        for row in rows:
            counter.update(row.failure_tags)
        distribution[strategy_id] = dict(sorted(counter.items()))
    return distribution


def _comparison_id(
    rows_by_strategy: dict[StrategyId, tuple[PlaceStoryTargetGrainCoverageRow, ...]],
) -> str:
    payload = {
        strategy_id: [row.model_dump(mode="json") for row in rows]
        for strategy_id, rows in rows_by_strategy.items()
    }
    digest = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"),
    ).hexdigest()[:8]
    query_count = len(next(iter(rows_by_strategy.values()))) if rows_by_strategy else 0
    return f"place-story-full-dev-input-s{len(rows_by_strategy)}-q{query_count}-{digest}"


def _recall_at(
    rows: tuple[PlaceStoryTargetGrainCoverageRow, ...],
    *,
    grain: Literal["child", "parent", "doc"],
    k: int,
) -> float:
    if not rows:
        return 0.0
    return _mean_bool([_covered_at(_rank_for_grain(row, grain), k) for row in rows])


def _rank_for_grain(
    row: PlaceStoryTargetGrainCoverageRow,
    grain: Literal["child", "parent", "doc"],
) -> int | None:
    if grain == "child":
        return row.target_child_min_retrieval_rank
    if grain == "parent":
        return row.target_parent_min_retrieval_rank
    return row.target_doc_min_retrieval_rank


def _direct_evidence_covered(row: PlaceStoryTargetGrainCoverageRow) -> bool:
    return _covered_at(row.target_child_min_retrieval_rank, 5) or _covered_at(
        row.target_parent_min_retrieval_rank,
        5,
    )


def _doc_only_covered(row: PlaceStoryTargetGrainCoverageRow) -> bool:
    return row.target_doc_covered and not row.target_child_covered and not row.target_parent_covered


def _full_grain_miss(row: PlaceStoryTargetGrainCoverageRow) -> bool:
    return not row.target_child_covered and not row.target_parent_covered and not row.target_doc_covered


def _covered_at(rank: int | None, k: int) -> bool:
    return rank is not None and rank <= k


def _mean_bool(values: list[bool]) -> float:
    if not values:
        return 0.0
    return round(sum(1 for value in values if value) / len(values), 6)


def _mean_float(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 6)


def _percentile_float(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = round((len(sorted_values) - 1) * percentile)
    return round(sorted_values[index], 6)


def _format_summary_row(summary: PlaceStoryFullDevStrategySummary) -> str:
    return (
        f"| {summary.strategy_id} | {summary.query_count} | "
        f"{summary.target_child_recall_at_1:.6f} | "
        f"{summary.target_child_recall_at_3:.6f} | "
        f"{summary.target_child_recall_at_5:.6f} | "
        f"{summary.target_parent_recall_at_1:.6f} | "
        f"{summary.target_parent_recall_at_3:.6f} | "
        f"{summary.target_parent_recall_at_5:.6f} | "
        f"{summary.target_doc_recall_at_5:.6f} | "
        f"{summary.child_or_parent_recall_at_5:.6f} | "
        f"{summary.generation_input_ready_rate:.6f} | "
        f"{summary.doc_only_covered_count} | {summary.full_grain_miss_count} | "
        f"{summary.hard_case_count} | {summary.mrr:.6f} | "
        f"{summary.ndcg_at_5:.6f} | {summary.latency_p95_ms:.6f} | "
        f"{summary.citation_recoverability_avg:.6f} | "
        f"{summary.evidence_order_relevance_proxy_avg:.6f} | "
        f"{summary.duplicate_parent_rate_avg:.6f} |"
    )


def _format_delta_row(delta: PlaceStoryGenerationInputImpactDelta) -> str:
    return (
        f"| {delta.compared_strategy_id} | "
        f"{delta.child_or_parent_recall_at_5_delta:.6f} | "
        f"{delta.generation_input_ready_rate_delta:.6f} | "
        f"{delta.target_child_recall_at_5_delta:.6f} | "
        f"{delta.target_parent_recall_at_5_delta:.6f} | "
        f"{delta.target_doc_recall_at_5_delta:.6f} | "
        f"{delta.doc_only_covered_count_delta} | "
        f"{delta.full_grain_miss_count_delta} | "
        f"{delta.hard_case_count_delta} | "
        f"{delta.mrr_delta:.6f} | {delta.ndcg_at_5_delta:.6f} | "
        f"{delta.latency_p95_ms_delta:.6f} | "
        f"{delta.evidence_order_relevance_proxy_avg_delta:.6f} | "
        f"{delta.direct_evidence_improved_query_count} | "
        f"{delta.direct_evidence_regressed_query_count} |"
    )


def _format_tag_distribution_rows(strategy_id: str, distribution: dict[str, int]) -> str:
    if not distribution:
        return f"| {strategy_id} | none | 0 |"
    return "\n".join(
        f"| {strategy_id} | {tag} | {count} |"
        for tag, count in distribution.items()
    )


def _next_action(report: PlaceStoryFullDevGenerationInputImpactReport) -> str:
    if report.selection_decision == "promote_to_generation_input_eval":
        return "같은 query set에서 Solar Pro 3 호출 전 generation input-only 평가를 먼저 수행한다."
    if report.selection_decision == "keep_candidate_for_hard_subset_only":
        return "hard subset 제한 후보로 유지하고 query별 regression 원인을 확인한다."
    return "parent/doc context boost를 기본 후보로 채택하지 않고 judgment grain 또는 chunking 재개 조건을 검토한다."


def _conclusion_text(report: PlaceStoryFullDevGenerationInputImpactReport) -> str:
    if report.selection_decision == "promote_to_generation_input_eval":
        return (
            "`parent_doc_context_boost`는 full place_story dev에서 generation 입력 품질 후보로 승격할 수 있다.\n\n"
            "다만 이 결과는 private dev input-only 기준이며 Solar Pro 3 live generation 개선 주장이 아니다."
        )
    if report.selection_decision == "keep_candidate_for_hard_subset_only":
        return (
            "`parent_doc_context_boost`는 일부 query를 개선하지만 full dev 기본 후보로 고정하기에는 trade-off가 남아 있다.\n\n"
            "다음 단계는 query별 regression 원인 분석이다."
        )
    return (
        "`parent_doc_context_boost`는 full place_story dev에서 baseline보다 안정적인 generation 입력 품질을 만들지 못했다.\n\n"
        "따라서 청킹 재실험으로 바로 돌아가지 않고 judgment grain 또는 다른 retrieval repair 후보를 먼저 검토한다."
    )


def main() -> int:
    args = _parse_args()
    report = run_place_story_full_dev_generation_input_impact(
        chunks_path=args.chunks,
        dataset_path=args.dataset,
        place_catalog_path=args.place_catalog,
        embedding_cache_dir=args.embedding_cache_dir,
        report_path=args.report,
        result_rows_path=args.result_rows,
        top_k=args.top_k,
        candidate_k=args.candidate_k,
    )
    failures = collect_place_story_full_dev_generation_input_impact_failures(report)
    selected = next(
        summary
        for summary in report.strategy_summaries
        if summary.strategy_id == report.selected_strategy_id
    )
    print(
        "place_story_full_dev_generation_input_impact "
        f"status={'PASS' if not failures else 'FAIL'} "
        f"selected={report.selected_strategy_id} "
        f"decision={report.selection_decision} "
        f"query_count={selected.query_count} "
        f"child_or_parent_at_5={selected.child_or_parent_recall_at_5:.6f} "
        f"input_ready={selected.generation_input_ready_rate:.6f} "
        f"device={report.resolved_device} "
        f"failures={len(failures)}",
    )
    return 0 if not failures else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate parent_doc_context_boost impact on full place_story dev generation inputs.",
    )
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS_PATH)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--place-catalog", type=Path, default=DEFAULT_PLACE_CATALOG_PATH)
    parser.add_argument("--embedding-cache-dir", type=Path, default=DEFAULT_EMBEDDING_CACHE_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--result-rows", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument("--candidate-k", type=int, default=DEFAULT_CANDIDATE_K)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
