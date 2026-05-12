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

from app.application.evidence_packing import (
    EvidencePack,
    EvidencePacker,
    build_candidates_by_query_id,
    build_evidence_corpus_from_chunks_payload,
)
from app.application.query_rewrite import (
    PlaceAwareQueryRewriter,
    QueryRewriteConfig,
    QueryRewriteResult,
)
from app.core.project_paths import (
    has_private_data_segment,
    is_repository_private_artifact_path,
    is_repository_private_write_path,
    project_path,
)
from app.domain.place_catalog import PlaceCatalog, load_place_catalog
from app.domain.retrieval import (
    RetrievalDocument,
    RetrievalEvalItem,
    RetrievalRunResult,
    load_retrieval_eval_jsonl,
)
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    measure_public_retrieval_artifact_quality,
)
from app.infrastructure.index.dense import DenseRetrievalConfig, DenseRetriever
from pipelines.run_retrieval_experiment import load_retrieval_documents_from_chunks
from pipelines.run_solar_live_generation_smoke import DEFAULT_CHUNKS_PATH, DEFAULT_DATASET_PATH
from pipelines.run_place_story_target_grain_coverage import (
    PlaceStoryTargetGrainCoverageRow,
    build_place_story_target_grain_coverage_row,
)


PLACE_STORY_TOP_RANK_COVERAGE_REPAIR_REPORT_VERSION = (
    "place-story-top-rank-coverage-repair-report/v1"
)
DEFAULT_PLACE_CATALOG_PATH = Path("data_samples") / "place_catalog_seed.json"
DEFAULT_EMBEDDING_CACHE_DIR = Path("private_data") / "embeddings" / "place_story_repair"
DEFAULT_REPORT_PATH = (
    Path("evals") / "reports" / "place_story_top_rank_coverage_repair_report.md"
)
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "place_story_top_rank_coverage_repair_rows.jsonl"
)
DEFAULT_TOP_K = 5
DEFAULT_CANDIDATE_K = 20

StrategyId = Literal[
    "baseline_dense_e5_voice_rewrite",
    "place_story_rewrite_v2",
    "parent_doc_context_boost",
]
SelectionDecision = Literal["adopt_candidate", "reject_candidates", "needs_more_diagnosis"]

STRATEGY_ORDER: tuple[StrategyId, ...] = (
    "baseline_dense_e5_voice_rewrite",
    "place_story_rewrite_v2",
    "parent_doc_context_boost",
)
BASELINE_STRATEGY_ID: StrategyId = "baseline_dense_e5_voice_rewrite"
STORY_TERMS: tuple[str, ...] = (
    "이야기",
    "배경",
    "일화",
    "사건",
    "인물",
    "왕",
    "조선",
    "한양",
    "역사",
)


class PlaceStoryRepairModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PlaceStoryRepairStrategySummary(PlaceStoryRepairModel):
    strategy_id: StrategyId
    query_count: int = Field(ge=0)
    hard_subset_query_count: int = Field(ge=0)
    target_child_recall_at_1: float = Field(ge=0.0, le=1.0)
    target_child_recall_at_3: float = Field(ge=0.0, le=1.0)
    target_child_recall_at_5: float = Field(ge=0.0, le=1.0)
    target_parent_recall_at_1: float = Field(ge=0.0, le=1.0)
    target_parent_recall_at_3: float = Field(ge=0.0, le=1.0)
    target_parent_recall_at_5: float = Field(ge=0.0, le=1.0)
    target_doc_recall_at_5: float = Field(ge=0.0, le=1.0)
    child_or_parent_recall_at_5: float = Field(ge=0.0, le=1.0)
    doc_only_covered_count: int = Field(ge=0)
    full_grain_miss_count: int = Field(ge=0)
    hard_case_count: int = Field(ge=0)
    mrr: float = Field(ge=0.0, le=1.0)
    ndcg_at_5: float = Field(ge=0.0, le=1.0)
    latency_p95_ms: float = Field(ge=0.0)
    citation_recoverability_avg: float = Field(ge=0.0, le=1.0)
    query_rewrite_changed_count: int = Field(ge=0)


class PlaceStoryRepairDelta(PlaceStoryRepairModel):
    compared_strategy_id: StrategyId
    baseline_strategy_id: StrategyId = BASELINE_STRATEGY_ID
    child_or_parent_recall_at_5_delta: float
    target_child_recall_at_5_delta: float
    target_parent_recall_at_5_delta: float
    target_doc_recall_at_5_delta: float
    doc_only_covered_count_delta: int
    full_grain_miss_count_delta: int
    hard_case_count_delta: int
    mrr_delta: float
    ndcg_at_5_delta: float
    latency_p95_ms_delta: float


class PlaceStoryTopRankCoverageRepairReport(PlaceStoryRepairModel):
    report_version: str = PLACE_STORY_TOP_RANK_COVERAGE_REPAIR_REPORT_VERSION
    comparison_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    dataset_path_alias: str = Field(min_length=1)
    chunks_path_alias: str = Field(min_length=1)
    place_catalog_path: str = Field(min_length=1)
    top_k: int = Field(ge=1)
    candidate_k: int = Field(ge=1)
    hard_subset_query_ids: tuple[str, ...]
    strategy_summaries: tuple[PlaceStoryRepairStrategySummary, ...]
    strategy_deltas: tuple[PlaceStoryRepairDelta, ...]
    selected_strategy_id: StrategyId
    selection_decision: SelectionDecision
    selection_reason: str = Field(min_length=1)
    failure_tag_distribution_by_strategy: dict[str, dict[str, int]]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


@dataclass(frozen=True)
class _StrategyExecutionContext:
    documents: list[RetrievalDocument]
    document_by_child_id: dict[str, RetrievalDocument]
    retriever: DenseRetriever
    packer: EvidencePacker
    catalog: PlaceCatalog
    rewriter: PlaceAwareQueryRewriter


def run_place_story_top_rank_coverage_repair(
    *,
    chunks_path: Path = DEFAULT_CHUNKS_PATH,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    place_catalog_path: Path = DEFAULT_PLACE_CATALOG_PATH,
    embedding_cache_dir: Path = DEFAULT_EMBEDDING_CACHE_DIR,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
    top_k: int = DEFAULT_TOP_K,
    candidate_k: int = DEFAULT_CANDIDATE_K,
) -> PlaceStoryTopRankCoverageRepairReport:
    _validate_private_rows_path(result_rows_path, label="result")
    items = _load_place_story_dev_items(dataset_path=dataset_path)
    context = _build_execution_context(
        chunks_path=chunks_path,
        place_catalog_path=place_catalog_path,
        embedding_cache_dir=embedding_cache_dir,
    )
    rows_by_strategy: dict[StrategyId, tuple[PlaceStoryTargetGrainCoverageRow, ...]] = {}
    for strategy_id in STRATEGY_ORDER:
        rows_by_strategy[strategy_id] = tuple(
            _run_strategy_for_item(
                item=item,
                strategy_id=strategy_id,
                context=context,
                top_k=top_k,
                candidate_k=candidate_k,
            )
            for item in items
        )

    hard_subset_query_ids = _hard_subset_query_ids(rows_by_strategy[BASELINE_STRATEGY_ID])
    provisional = build_place_story_top_rank_coverage_repair_report(
        rows_by_strategy=rows_by_strategy,
        hard_subset_query_ids=hard_subset_query_ids,
        chunks_path=chunks_path,
        dataset_path=dataset_path,
        place_catalog_path=place_catalog_path,
        top_k=top_k,
        candidate_k=candidate_k,
    )
    provisional_rows = build_public_place_story_top_rank_coverage_repair_rows(provisional)
    provisional_text = build_place_story_top_rank_coverage_repair_markdown(provisional)
    report = build_place_story_top_rank_coverage_repair_report(
        rows_by_strategy=rows_by_strategy,
        hard_subset_query_ids=hard_subset_query_ids,
        chunks_path=chunks_path,
        dataset_path=dataset_path,
        place_catalog_path=place_catalog_path,
        top_k=top_k,
        candidate_k=candidate_k,
        result_rows=provisional_rows,
        report_text=provisional_text,
    )
    failures = collect_place_story_top_rank_coverage_repair_failures(report)
    if failures:
        raise ValueError(f"place story top-rank coverage repair gate failed: {failures}")

    result_rows = build_public_place_story_top_rank_coverage_repair_rows(report)
    _write_jsonl_rows(path=result_rows_path, rows=result_rows)
    resolved_report_path = project_path(report_path)
    resolved_report_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_report_path.write_text(
        build_place_story_top_rank_coverage_repair_markdown(report),
        encoding="utf-8",
    )
    return report


def build_place_story_top_rank_coverage_repair_report(
    *,
    rows_by_strategy: dict[StrategyId, tuple[PlaceStoryTargetGrainCoverageRow, ...]],
    hard_subset_query_ids: tuple[str, ...],
    chunks_path: Path,
    dataset_path: Path,
    place_catalog_path: Path,
    top_k: int,
    candidate_k: int,
    result_rows: list[dict[str, Any]] | None = None,
    report_text: str = "",
) -> PlaceStoryTopRankCoverageRepairReport:
    strategy_summaries = tuple(
        build_strategy_summary(
            strategy_id=strategy_id,
            rows=_rows_for_hard_subset(rows_by_strategy[strategy_id], hard_subset_query_ids),
            hard_subset_query_count=len(hard_subset_query_ids),
        )
        for strategy_id in STRATEGY_ORDER
        if strategy_id in rows_by_strategy
    )
    deltas = build_strategy_deltas(strategy_summaries)
    selected_strategy_id, decision, reason = _select_strategy(strategy_summaries, deltas)
    comparison_id = _comparison_id(
        rows_by_strategy=rows_by_strategy,
        hard_subset_query_ids=hard_subset_query_ids,
    )
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=PLACE_STORY_TOP_RANK_COVERAGE_REPAIR_REPORT_VERSION,
        run_id=comparison_id,
        result_rows=result_rows or [],
        report_text=report_text,
    )
    report = PlaceStoryTopRankCoverageRepairReport(
        comparison_id=comparison_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        dataset_path_alias="<private retrieval eval dataset: retrieval_eval_dev.jsonl>",
        chunks_path_alias="<private parent_child_chunks report>",
        place_catalog_path=place_catalog_path.as_posix(),
        top_k=top_k,
        candidate_k=candidate_k,
        hard_subset_query_ids=hard_subset_query_ids,
        strategy_summaries=strategy_summaries,
        strategy_deltas=tuple(deltas),
        selected_strategy_id=selected_strategy_id,
        selection_decision=decision,
        selection_reason=reason,
        failure_tag_distribution_by_strategy=_failure_tag_distribution_by_strategy(
            rows_by_strategy=rows_by_strategy,
            hard_subset_query_ids=hard_subset_query_ids,
        ),
        output_quality=output_quality,
        qualitative_assessment={},
    )
    return report.model_copy(
        update={
            "qualitative_assessment": build_place_story_repair_qualitative_assessment(
                report,
            )
        },
    )


def build_strategy_summary(
    *,
    strategy_id: StrategyId,
    rows: tuple[PlaceStoryTargetGrainCoverageRow, ...],
    hard_subset_query_count: int,
) -> PlaceStoryRepairStrategySummary:
    return PlaceStoryRepairStrategySummary(
        strategy_id=strategy_id,
        query_count=len(rows),
        hard_subset_query_count=hard_subset_query_count,
        target_child_recall_at_1=_recall_at(rows, grain="child", k=1),
        target_child_recall_at_3=_recall_at(rows, grain="child", k=3),
        target_child_recall_at_5=_recall_at(rows, grain="child", k=5),
        target_parent_recall_at_1=_recall_at(rows, grain="parent", k=1),
        target_parent_recall_at_3=_recall_at(rows, grain="parent", k=3),
        target_parent_recall_at_5=_recall_at(rows, grain="parent", k=5),
        target_doc_recall_at_5=_recall_at(rows, grain="doc", k=5),
        child_or_parent_recall_at_5=_mean_bool(
            [
                _covered_at(row.target_child_min_retrieval_rank, 5)
                or _covered_at(row.target_parent_min_retrieval_rank, 5)
                for row in rows
            ],
        ),
        doc_only_covered_count=sum(
            1
            for row in rows
            if row.target_doc_covered
            and not row.target_child_covered
            and not row.target_parent_covered
        ),
        full_grain_miss_count=sum(
            1
            for row in rows
            if not row.target_child_covered
            and not row.target_parent_covered
            and not row.target_doc_covered
        ),
        hard_case_count=sum(1 for row in rows if row.hard_case),
        mrr=_mean_float([row.reciprocal_rank for row in rows]),
        ndcg_at_5=_mean_float([row.ndcg_at_5 for row in rows]),
        latency_p95_ms=_percentile_float([row.total_latency_ms for row in rows], 0.95),
        citation_recoverability_avg=_mean_float(
            [row.citation_recoverability for row in rows],
        ),
        query_rewrite_changed_count=sum(1 for row in rows if row.query_rewrite_changed),
    )


def build_strategy_deltas(
    summaries: tuple[PlaceStoryRepairStrategySummary, ...],
) -> list[PlaceStoryRepairDelta]:
    baseline = next(
        summary for summary in summaries if summary.strategy_id == BASELINE_STRATEGY_ID
    )
    deltas: list[PlaceStoryRepairDelta] = []
    for summary in summaries:
        deltas.append(
            PlaceStoryRepairDelta(
                compared_strategy_id=summary.strategy_id,
                child_or_parent_recall_at_5_delta=round(
                    summary.child_or_parent_recall_at_5
                    - baseline.child_or_parent_recall_at_5,
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
            ),
        )
    return deltas


def build_public_place_story_top_rank_coverage_repair_rows(
    report: PlaceStoryTopRankCoverageRepairReport,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for summary in report.strategy_summaries:
        rows.append(
            {
                "comparison_id": report.comparison_id,
                "strategy_id": summary.strategy_id,
                "query_count": summary.query_count,
                "hard_subset_query_count": summary.hard_subset_query_count,
                "target_child_recall_at_5": summary.target_child_recall_at_5,
                "target_parent_recall_at_5": summary.target_parent_recall_at_5,
                "target_doc_recall_at_5": summary.target_doc_recall_at_5,
                "child_or_parent_recall_at_5": summary.child_or_parent_recall_at_5,
                "doc_only_covered_count": summary.doc_only_covered_count,
                "full_grain_miss_count": summary.full_grain_miss_count,
                "hard_case_count": summary.hard_case_count,
                "mrr": summary.mrr,
                "ndcg_at_5": summary.ndcg_at_5,
                "latency_p95_ms": summary.latency_p95_ms,
                "citation_recoverability_avg": summary.citation_recoverability_avg,
                "query_rewrite_changed_count": summary.query_rewrite_changed_count,
            },
        )
    return rows


def collect_place_story_top_rank_coverage_repair_failures(
    report: PlaceStoryTopRankCoverageRepairReport,
) -> list[str]:
    failures: list[str] = []
    if not report.hard_subset_query_ids:
        failures.append("empty_hard_subset")
    if report.output_quality.public_raw_text_leakage_count:
        failures.append("public_raw_text_leakage")
    if report.output_quality.private_path_leakage_count:
        failures.append("private_path_leakage")
    if report.output_quality.secret_like_leakage_count:
        failures.append("secret_like_leakage")
    if report.output_quality.forbidden_result_field_count:
        failures.append("forbidden_public_result_fields")
    return failures


def build_place_story_top_rank_coverage_repair_markdown(
    report: PlaceStoryTopRankCoverageRepairReport,
) -> str:
    summary_rows = "\n".join(
        _format_strategy_summary_row(summary) for summary in report.strategy_summaries
    )
    delta_rows = "\n".join(_format_delta_row(delta) for delta in report.strategy_deltas)
    tag_rows = "\n".join(
        _format_tag_distribution_rows(strategy_id, distribution)
        for strategy_id, distribution in report.failure_tag_distribution_by_strategy.items()
    )
    qualitative_rows = "\n".join(
        f"- `{key}`: {value}" for key, value in report.qualitative_assessment.items()
    )
    quality = report.output_quality
    hard_subset = ", ".join(f"`{query_id}`" for query_id in report.hard_subset_query_ids)
    return f"""# Place Story Top-rank Coverage Repair Report

## 목적

`place_story` hard subset에서 top-rank retrieval coverage repair 후보를 비교한다.

이 문서는 청킹 재실험 결과가 아니며 Solar Pro 3 추가 호출도 아니다. 같은 private dev split, 같은 parent-child chunk corpus, 같은 `P0_rank_order` evidence packing을 유지한다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| comparison_id | `{report.comparison_id}` |
| generated_at_utc | `{report.generated_at_utc}` |
| dataset_path | `{report.dataset_path_alias}` |
| chunks_path | `{report.chunks_path_alias}` |
| place_catalog_path | `{report.place_catalog_path}` |
| top_k | {report.top_k} |
| candidate_k | {report.candidate_k} |
| hard_subset_query_count | {len(report.hard_subset_query_ids)} |
| hard_subset_query_ids | {hard_subset} |
| selected_strategy_id | `{report.selected_strategy_id}` |
| selection_decision | `{report.selection_decision}` |
| selection_reason | {report.selection_reason} |

## Strategy Summary

| strategy_id | query_count | child@1 | child@3 | child@5 | parent@1 | parent@3 | parent@5 | doc@5 | child_or_parent@5 | doc_only | full_miss | hard_case | MRR | nDCG@5 | latency_p95_ms | citation | rewrite_changed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{summary_rows}

## Baseline Delta

| compared_strategy_id | child_or_parent@5 delta | child@5 delta | parent@5 delta | doc@5 delta | doc_only delta | full_miss delta | hard_case delta | MRR delta | nDCG@5 delta | latency_p95_ms delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
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


def build_place_story_repair_qualitative_assessment(
    report: PlaceStoryTopRankCoverageRepairReport,
) -> dict[str, str]:
    return {
        "comparison_scope": (
            "baseline, place_story deterministic rewrite v2, parent/doc context boost를 hard subset에서 비교했다."
        ),
        "chunking_decision": (
            "이번 결과는 청킹 재실험이 아니다. chunk corpus와 evidence packing 정책을 고정해 retrieval repair 후보만 비교했다."
        ),
        "selection_boundary": (
            "선택 판단은 private dev hard subset 기준이다. locked test와 generation 평가 전에는 최종 개선 주장으로 쓰지 않는다."
        ),
        "security_boundary": (
            "public report/result에는 raw query, raw evidence, chunk text, private path, secret을 기록하지 않는다."
        ),
        "data_mart_grain": (
            "`fact_place_story_repair`의 grain은 strategy-query이며, 공개 산출물에는 strategy aggregate만 남긴다."
        ),
        "next_action": _next_action_for_report(report),
    }


def rerank_with_parent_doc_context_boost(
    *,
    item: RetrievalEvalItem,
    result: RetrievalRunResult,
    document_by_child_id: dict[str, RetrievalDocument],
    catalog: PlaceCatalog,
    top_k: int,
) -> RetrievalRunResult:
    place_terms = _place_terms(item=item, catalog=catalog)
    boosted = []
    for candidate in result.candidates:
        document = document_by_child_id.get(candidate.child_id)
        if document is None:
            boosted.append((candidate.score, candidate))
            continue
        boost = _parent_doc_context_boost(document=document, place_terms=place_terms)
        boosted.append((candidate.score + boost, candidate))
    reranked = sorted(
        boosted,
        key=lambda item_score: (item_score[0], item_score[1].retrieval_doc_id),
        reverse=True,
    )[:top_k]
    return result.model_copy(
        update={
            "candidates": [
                candidate.model_copy(
                    update={"rank": rank, "score": round(score, 6)},
                )
                for rank, (score, candidate) in enumerate(reranked, start=1)
            ],
        },
    )


def _run_strategy_for_item(
    *,
    item: RetrievalEvalItem,
    strategy_id: StrategyId,
    context: _StrategyExecutionContext,
    top_k: int,
    candidate_k: int,
) -> PlaceStoryTargetGrainCoverageRow:
    rewrite = _rewrite_for_strategy(item=item, strategy_id=strategy_id, context=context)
    search_k = candidate_k if strategy_id == "parent_doc_context_boost" else top_k
    result = context.retriever.search(
        query_id=item.query.query_id,
        query_type=item.query.query_type,
        query_text=rewrite.rewritten_query_text,
        top_k=search_k,
    )
    if strategy_id == "parent_doc_context_boost":
        result = rerank_with_parent_doc_context_boost(
            item=item,
            result=result,
            document_by_child_id=context.document_by_child_id,
            catalog=context.catalog,
            top_k=top_k,
        )
    pack = _pack_retrieval_result(item=item, result=result, packer=context.packer)
    row = build_place_story_target_grain_coverage_row(
        item=item,
        evidence_pack=pack,
        retrieval_method=strategy_id,
        retrieval_candidate_count=len(result.candidates),
        total_latency_ms=round(result.latency_ms + rewrite.latency_ms, 6),
        query_rewrite_changed=rewrite.changed,
        query_rewrite_applied_rule_count=len(rewrite.applied_rules),
    )
    return row.model_copy(update={"retrieval_run_label": strategy_id})


def _rewrite_for_strategy(
    *,
    item: RetrievalEvalItem,
    strategy_id: StrategyId,
    context: _StrategyExecutionContext,
) -> QueryRewriteResult:
    if strategy_id == "place_story_rewrite_v2":
        return context.rewriter.rewrite(item)
    return QueryRewriteResult(
        query_id=item.query.query_id,
        query_type=item.query.query_type,
        original_query_text=item.query.query_text,
        rewritten_query_text=item.query.query_text,
        changed=False,
        applied_rules=("strategy_passthrough",),
        place_ids=tuple(item.metadata.place_ids),
        latency_ms=0.0,
    )


def _pack_retrieval_result(
    *,
    item: RetrievalEvalItem,
    result: RetrievalRunResult,
    packer: EvidencePacker,
) -> EvidencePack:
    candidates_by_query_id = build_candidates_by_query_id(
        result_rows=[
            {
                "query_id": result.query_id,
                "query_type": result.query_type,
                "rank": candidate.rank,
                "retrieval_doc_id": candidate.retrieval_doc_id,
                "child_id": candidate.child_id,
                "parent_id": candidate.parent_id,
                "doc_id": candidate.doc_id,
                "score": candidate.score,
            }
            for candidate in result.candidates
        ],
        corpus=packer.corpus,
    )
    return packer.pack(
        item=item,
        candidates=candidates_by_query_id.get(item.query.query_id, []),
        policy_id="P0_rank_order",
    )


def _build_execution_context(
    *,
    chunks_path: Path,
    place_catalog_path: Path,
    embedding_cache_dir: Path,
) -> _StrategyExecutionContext:
    resolved_chunks_path = project_path(chunks_path)
    chunks_payload = json.loads(resolved_chunks_path.read_text(encoding="utf-8"))
    documents = load_retrieval_documents_from_chunks(resolved_chunks_path)
    config = DenseRetrievalConfig(
        encoder_id="multilingual-e5-small",
        backend="sentence_transformers",
        model_name="intfloat/multilingual-e5-small",
        query_prefix="query: ",
        document_prefix="passage: ",
    )
    retriever = DenseRetriever.from_documents(
        documents,
        config=config,
        cache_dir=project_path(embedding_cache_dir),
    )
    catalog = load_place_catalog(project_path(place_catalog_path))
    return _StrategyExecutionContext(
        documents=documents,
        document_by_child_id={document.child_id: document for document in documents},
        retriever=retriever,
        packer=EvidencePacker(corpus=build_evidence_corpus_from_chunks_payload(chunks_payload)),
        catalog=catalog,
        rewriter=PlaceAwareQueryRewriter(
            catalog=catalog,
            config=QueryRewriteConfig(
                strategy_id="place-story-deterministic-v2",
                target_query_types=("place_story",),
                max_aliases_per_place=6,
                max_related_places=0,
                include_related_places_for_route=False,
                include_intent_terms=True,
            ),
        ),
    )


def _load_place_story_dev_items(*, dataset_path: Path) -> list[RetrievalEvalItem]:
    items = load_retrieval_eval_jsonl(project_path(dataset_path))
    selected = [
        item
        for item in items
        if item.query.query_type == "place_story"
        and item.metadata.split == "dev"
        and item.metadata.review_status == "reviewed"
    ]
    if not selected:
        raise ValueError("place_story repair comparison requires reviewed dev rows")
    return selected


def _hard_subset_query_ids(
    baseline_rows: tuple[PlaceStoryTargetGrainCoverageRow, ...],
) -> tuple[str, ...]:
    return tuple(row.query_id for row in baseline_rows if row.hard_case)


def _rows_for_hard_subset(
    rows: tuple[PlaceStoryTargetGrainCoverageRow, ...],
    hard_subset_query_ids: tuple[str, ...],
) -> tuple[PlaceStoryTargetGrainCoverageRow, ...]:
    hard_query_ids = set(hard_subset_query_ids)
    return tuple(row for row in rows if row.query_id in hard_query_ids)


def _place_terms(*, item: RetrievalEvalItem, catalog: PlaceCatalog) -> tuple[str, ...]:
    place_by_id = {place.place_id: place for place in catalog.places}
    terms: list[str] = []
    for place_id in item.metadata.place_ids:
        place = place_by_id.get(place_id)
        if place is None:
            continue
        terms.append(place.canonical_name)
        terms.extend(alias.alias for alias in place.aliases[:6])
    return _unique(terms)


def _parent_doc_context_boost(
    *,
    document: RetrievalDocument,
    place_terms: tuple[str, ...],
) -> float:
    search_space = " ".join(
        part
        for part in (
            document.doc_title,
            document.search_text or "",
            document.context_text or "",
        )
        if part
    ).casefold()
    place_match_count = sum(
        1 for term in place_terms if term and term.casefold() in search_space
    )
    story_match_count = sum(1 for term in STORY_TERMS if term in search_space)
    place_boost = min(place_match_count * 0.05, 0.10)
    story_boost = min(story_match_count * 0.02, 0.06)
    return round(place_boost + story_boost, 6)


def _select_strategy(
    summaries: tuple[PlaceStoryRepairStrategySummary, ...],
    deltas: list[PlaceStoryRepairDelta],
) -> tuple[StrategyId, SelectionDecision, str]:
    baseline = next(
        summary for summary in summaries if summary.strategy_id == BASELINE_STRATEGY_ID
    )
    candidates = [summary for summary in summaries if summary.strategy_id != BASELINE_STRATEGY_ID]
    selected = max(
        candidates,
        key=lambda summary: (
            summary.child_or_parent_recall_at_5,
            -summary.doc_only_covered_count,
            -summary.full_grain_miss_count,
            summary.mrr,
            summary.ndcg_at_5,
            -summary.latency_p95_ms,
        ),
    )
    selected_delta = next(
        delta for delta in deltas if delta.compared_strategy_id == selected.strategy_id
    )
    improves_direct_evidence = (
        selected.child_or_parent_recall_at_5 > baseline.child_or_parent_recall_at_5
    )
    reduces_doc_only_or_miss = (
        selected.doc_only_covered_count < baseline.doc_only_covered_count
        or selected.full_grain_miss_count < baseline.full_grain_miss_count
    )
    latency_ok = selected_delta.latency_p95_ms_delta <= max(
        100.0,
        baseline.latency_p95_ms,
    )
    if improves_direct_evidence and latency_ok:
        return (
            selected.strategy_id,
            "adopt_candidate",
            "hard subset child_or_parent@5가 baseline보다 개선되어 후보 채택 대상이다.",
        )
    if reduces_doc_only_or_miss and latency_ok:
        return (
            selected.strategy_id,
            "needs_more_diagnosis",
            "직접 근거 recall은 개선되지 않았지만 doc-only/full-miss가 줄어 추가 진단 후보로 둔다.",
        )
    return (
        BASELINE_STRATEGY_ID,
        "reject_candidates",
        "후보가 hard subset의 child_or_parent@5를 개선하지 못해 baseline을 유지한다.",
    )


def _failure_tag_distribution_by_strategy(
    *,
    rows_by_strategy: dict[StrategyId, tuple[PlaceStoryTargetGrainCoverageRow, ...]],
    hard_subset_query_ids: tuple[str, ...],
) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for strategy_id, rows in rows_by_strategy.items():
        counter: Counter[str] = Counter()
        for row in _rows_for_hard_subset(rows, hard_subset_query_ids):
            counter.update(row.failure_tags)
        result[strategy_id] = dict(sorted(counter.items()))
    return result


def _comparison_id(
    *,
    rows_by_strategy: dict[StrategyId, tuple[PlaceStoryTargetGrainCoverageRow, ...]],
    hard_subset_query_ids: tuple[str, ...],
) -> str:
    payload = {
        "hard_subset_query_ids": hard_subset_query_ids,
        "rows": {
            strategy_id: [row.model_dump(mode="json") for row in rows]
            for strategy_id, rows in rows_by_strategy.items()
        },
    }
    digest = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"),
    ).hexdigest()[:8]
    return f"place-story-top-rank-repair-s{len(rows_by_strategy)}-h{len(hard_subset_query_ids)}-{digest}"


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


def _unique(values: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        if value in seen:
            continue
        unique_values.append(value)
        seen.add(value)
    return tuple(unique_values)


def _format_strategy_summary_row(summary: PlaceStoryRepairStrategySummary) -> str:
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
        f"{summary.doc_only_covered_count} | {summary.full_grain_miss_count} | "
        f"{summary.hard_case_count} | {summary.mrr:.6f} | "
        f"{summary.ndcg_at_5:.6f} | {summary.latency_p95_ms:.6f} | "
        f"{summary.citation_recoverability_avg:.6f} | "
        f"{summary.query_rewrite_changed_count} |"
    )


def _format_delta_row(delta: PlaceStoryRepairDelta) -> str:
    return (
        f"| {delta.compared_strategy_id} | "
        f"{delta.child_or_parent_recall_at_5_delta:.6f} | "
        f"{delta.target_child_recall_at_5_delta:.6f} | "
        f"{delta.target_parent_recall_at_5_delta:.6f} | "
        f"{delta.target_doc_recall_at_5_delta:.6f} | "
        f"{delta.doc_only_covered_count_delta} | "
        f"{delta.full_grain_miss_count_delta} | "
        f"{delta.hard_case_count_delta} | {delta.mrr_delta:.6f} | "
        f"{delta.ndcg_at_5_delta:.6f} | {delta.latency_p95_ms_delta:.6f} |"
    )


def _format_tag_distribution_rows(
    strategy_id: str,
    distribution: dict[str, int],
) -> str:
    if not distribution:
        return f"| {strategy_id} | none | 0 |"
    return "\n".join(
        f"| {strategy_id} | {tag} | {count} |"
        for tag, count in distribution.items()
    )


def _next_action_for_report(report: PlaceStoryTopRankCoverageRepairReport) -> str:
    if report.selection_decision == "adopt_candidate":
        return "채택 후보를 full place_story/dev query와 generation eval 전 입력으로 재검증한다."
    if report.selection_decision == "needs_more_diagnosis":
        return "doc-only/full-miss 감소 원인을 query별로 확인한 뒤 조합 후보 실행 여부를 판단한다."
    return "후보를 채택하지 않고 judgment target grain review 또는 다른 retrieval repair 후보를 설계한다."


def _conclusion_text(report: PlaceStoryTopRankCoverageRepairReport) -> str:
    if report.selection_decision == "adopt_candidate":
        return (
            f"`{report.selected_strategy_id}`가 hard subset에서 baseline보다 직접 근거 coverage를 개선했다.\n\n"
            "다만 이 결과는 private dev hard subset 기준이며 locked test와 generation 평가 전 최종 개선 주장이 아니다."
        )
    if report.selection_decision == "needs_more_diagnosis":
        return (
            f"`{report.selected_strategy_id}`는 일부 miss를 줄였지만 직접 근거 recall 개선은 충분하지 않다.\n\n"
            "다음 단계에서 query별 원인을 확인한 뒤 조합 후보 또는 judgment grain review를 결정한다."
        )
    return (
        "이번 후보들은 hard subset에서 baseline보다 직접 근거 coverage를 개선하지 못했다.\n\n"
        "따라서 청킹 재실험으로 바로 돌아가지 않고, judgment target grain review 또는 다른 retrieval repair 후보를 설계한다."
    )


def _validate_private_rows_path(path: Path, *, label: str) -> None:
    if has_private_data_segment(path) and not is_repository_private_artifact_path(path):
        raise ValueError(f"{label} rows must stay under repository private_data")
    if has_private_data_segment(path) and not is_repository_private_write_path(path):
        raise ValueError(f"{label} rows must stay under repository private_data")


def _write_jsonl_rows(*, path: Path, rows: list[dict[str, Any]]) -> None:
    resolved = project_path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    args = _parse_args()
    report = run_place_story_top_rank_coverage_repair(
        chunks_path=args.chunks,
        dataset_path=args.dataset,
        place_catalog_path=args.place_catalog,
        embedding_cache_dir=args.embedding_cache_dir,
        report_path=args.report,
        result_rows_path=args.result_rows,
        top_k=args.top_k,
        candidate_k=args.candidate_k,
    )
    failures = collect_place_story_top_rank_coverage_repair_failures(report)
    selected = next(
        summary
        for summary in report.strategy_summaries
        if summary.strategy_id == report.selected_strategy_id
    )
    print(
        "place_story_top_rank_coverage_repair "
        f"status={'PASS' if not failures else 'FAIL'} "
        f"hard_subset={len(report.hard_subset_query_ids)} "
        f"selected={report.selected_strategy_id} "
        f"decision={report.selection_decision} "
        f"child_or_parent_at_5={selected.child_or_parent_recall_at_5:.6f} "
        f"doc_only={selected.doc_only_covered_count} "
        f"full_miss={selected.full_grain_miss_count} "
        f"failures={len(failures)}",
    )
    return 0 if not failures else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare place_story top-rank retrieval coverage repair candidates.",
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
