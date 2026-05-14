from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.project_paths import project_path
from app.domain.retrieval import (
    RetrievedCandidate,
    RetrievalDocument,
    RetrievalEvalItem,
    RetrievalMetricSummary,
    RetrievalRunResult,
    compute_retrieval_metrics,
    load_retrieval_eval_jsonl,
)
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    collect_public_retrieval_artifact_failures,
    measure_public_retrieval_artifact_quality,
    public_path_alias,
    write_public_retrieval_result_rows,
)
from pipelines.run_retrieval_experiment import (
    DEFAULT_EMBEDDING_CACHE_DIR,
    DEFAULT_PLACE_CATALOG_PATH,
    _ExecutionContext,
    _build_method_plans,
    _execute_method,
    load_retrieval_documents_from_chunks,
)


RAPTOR_LITE_INPUT_ONLY_REPORT_VERSION = "raptor-lite-input-only-report/v1"
BASELINE_METHOD_KEY = "dense_multilingual_e5_small_voice_rewrite"
BASELINE_STRATEGY_ID = "dense_multilingual_e5_small_voice_rewrite_reference"
PARENT_SUMMARY_STRATEGY_ID = "raptor_lite_parent_summary_v1"
SUMMARY_NODE_STRATEGY_ID = "raptor_lite_summary_node_v1"
TARGET_QUERY_TYPES: tuple[Literal["overview", "place_story"], ...] = (
    "overview",
    "place_story",
)
DEFAULT_TOP_K = 5
DEFAULT_EXPECTED_TARGET_DEV_QUERY_COUNT = 20
DEFAULT_CHUNKS_PATH = Path("private_data") / "reports" / "parent_child_chunks.json"
DEFAULT_DATASET_PATH = Path("private_data") / "evals" / "datasets" / "retrieval_eval_dev.jsonl"
DEFAULT_BASELINE_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / f"retrieval_experiment_{BASELINE_METHOD_KEY}_results.jsonl"
)
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data") / "evals" / "results" / "raptor_lite_input_only_rows.jsonl"
)
DEFAULT_REPORT_PATH = Path("evals") / "reports" / "raptor_lite_input_only_report.md"
TARGET_RECALL_AT_5_DELTA = 0.03
TARGET_MRR_DELTA = 0.03
TARGET_NDCG_AT_5_DELTA = 0.03
MIN_CITATION_RECOVERABILITY = 0.99
MAX_LATENCY_P95_MS = 2500.0
MAX_QUERY_TOKEN_COUNT = 18
MAX_EXPANDED_TOKEN_COUNT = 32
MAX_GROUPS_PER_TERM = 250
MAX_GROUP_POOL_SIZE = 160

RaptorLiteRole = Literal["baseline", "candidate"]
RaptorLiteQueryScope = Literal["combined", "overview", "place_story"]
RaptorLiteDecision = Literal[
    "promote_raptor_lite_next_gate",
    "reject_raptor_lite_default",
    "blocked",
]
RaptorLiteGroupType = Literal["parent", "doc"]

_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9가-힣]{2,}")
_STOPWORDS = frozenset(
    {
        "그리고",
        "그러나",
        "그래서",
        "대한",
        "대해",
        "무엇",
        "어떤",
        "어떻게",
        "왜",
        "있어",
        "있는",
        "했다",
        "한다",
        "관련",
        "설명",
        "알려",
        "말해",
        "이야기",
        "근거",
        "짧게",
        "서울",
        "한양",
        "관광",
        "도슨트",
        "history",
        "docent",
    }
)
_NARRATIVE_HINT_TOKENS = frozenset(
    {
        "배경",
        "사건",
        "일화",
        "인물",
        "정치",
        "왕",
        "궁궐",
        "도성",
        "변화",
        "문화",
        "제도",
        "생활",
        "조선",
        "근대",
        "광화문",
        "경복궁",
        "종로",
        "북촌",
    }
)


class RaptorLiteModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RaptorLiteMetricRow(RaptorLiteModel):
    strategy_id: str = Field(min_length=1)
    role: RaptorLiteRole
    query_scope: RaptorLiteQueryScope
    query_count: int = Field(ge=0)
    result_count: int = Field(ge=0)
    missing_result_count: int = Field(ge=0)
    recall_at_1: float = Field(ge=0.0, le=1.0)
    recall_at_3: float = Field(ge=0.0, le=1.0)
    recall_at_5: float = Field(ge=0.0, le=1.0)
    mrr: float = Field(ge=0.0, le=1.0)
    ndcg_at_5: float = Field(ge=0.0, le=1.0)
    latency_p95_ms: float = Field(ge=0.0)
    citation_recoverability: float = Field(ge=0.0, le=1.0)
    recall_at_5_delta: float
    mrr_delta: float
    ndcg_at_5_delta: float
    latency_p95_ms_delta: float
    summary_group_pool_count: int = Field(ge=0)
    source_citation_only: bool
    solar_call_count: int = Field(ge=0)
    claim_boundary: Literal["dev_input_only"]


class RaptorLiteInputOnlySummary(RaptorLiteModel):
    target_dev_query_count: int = Field(ge=0)
    expected_target_dev_query_count: int = Field(ge=0)
    query_type_counts: dict[str, int]
    strategy_count: int = Field(ge=0)
    baseline_count: int = Field(ge=0)
    candidate_count: int = Field(ge=0)
    best_strategy_id: str = Field(min_length=1)
    baseline_strategy_id: str = Field(min_length=1)
    promoted_candidate_count: int = Field(ge=0)
    solar_call_count: int = Field(ge=0)
    min_citation_recoverability: float = Field(ge=0.0, le=1.0)
    target_recall_at_5_delta: float
    target_mrr_delta: float
    target_ndcg_at_5_delta: float
    max_latency_p95_ms: float = Field(ge=0.0)
    decision: RaptorLiteDecision


class RaptorLiteInputOnlyReport(RaptorLiteModel):
    report_version: str = RAPTOR_LITE_INPUT_ONLY_REPORT_VERSION
    run_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    dataset_path: str = Field(min_length=1)
    chunks_path_alias: str = Field(min_length=1)
    baseline_rows_path_alias: str = Field(min_length=1)
    result_rows_path_alias: str = Field(min_length=1)
    summary: RaptorLiteInputOnlySummary
    metric_rows: tuple[RaptorLiteMetricRow, ...]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


@dataclass(frozen=True)
class _RaptorLiteGroup:
    group_id: str
    group_type: RaptorLiteGroupType
    document_ids: tuple[str, ...]
    tokens: frozenset[str]


@dataclass(frozen=True)
class _RaptorLiteIndex:
    documents_by_id: dict[str, RetrievalDocument]
    tokens_by_doc_id: dict[str, frozenset[str]]
    parent_groups: dict[str, _RaptorLiteGroup]
    doc_groups: dict[str, _RaptorLiteGroup]
    token_to_parent_ids: dict[str, frozenset[str]]
    token_to_doc_group_ids: dict[str, frozenset[str]]


@dataclass(frozen=True)
class _RaptorLiteCandidateRun:
    results: list[RetrievalRunResult]
    pool_counts_by_query_id: dict[str, int]


def run_raptor_lite_input_only(
    *,
    chunks_path: Path = DEFAULT_CHUNKS_PATH,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    baseline_rows_path: Path = DEFAULT_BASELINE_ROWS_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    top_k: int = DEFAULT_TOP_K,
    expected_target_dev_query_count: int = DEFAULT_EXPECTED_TARGET_DEV_QUERY_COUNT,
    force_recompute_baseline: bool = False,
    embedding_cache_dir: Path = DEFAULT_EMBEDDING_CACHE_DIR,
    place_catalog_path: Path = DEFAULT_PLACE_CATALOG_PATH,
    items: list[RetrievalEvalItem] | None = None,
    documents: list[RetrievalDocument] | None = None,
    baseline_results: list[RetrievalRunResult] | None = None,
) -> RaptorLiteInputOnlyReport:
    if top_k != 5:
        raise ValueError("RAPTOR-lite input-only gate is fixed to top_k=5")
    loaded_items = items or load_retrieval_eval_jsonl(project_path(dataset_path))
    target_items = _target_dev_items(loaded_items)
    loaded_documents = documents or load_retrieval_documents_from_chunks(
        project_path(chunks_path),
    )
    baseline = baseline_results or _load_or_recompute_baseline_results(
        items=target_items,
        documents=loaded_documents,
        baseline_rows_path=project_path(baseline_rows_path),
        force_recompute_baseline=force_recompute_baseline,
        top_k=top_k,
        embedding_cache_dir=project_path(embedding_cache_dir),
        place_catalog_path=project_path(place_catalog_path),
    )
    index = _build_raptor_lite_index(loaded_documents)
    parent_summary_run = _build_raptor_lite_candidate_results(
        strategy_id=PARENT_SUMMARY_STRATEGY_ID,
        items=target_items,
        baseline_results=baseline,
        index=index,
        top_k=top_k,
    )
    summary_node_run = _build_raptor_lite_candidate_results(
        strategy_id=SUMMARY_NODE_STRATEGY_ID,
        items=target_items,
        baseline_results=baseline,
        index=index,
        top_k=top_k,
    )
    strategy_results = {
        BASELINE_STRATEGY_ID: baseline,
        PARENT_SUMMARY_STRATEGY_ID: parent_summary_run.results,
        SUMMARY_NODE_STRATEGY_ID: summary_node_run.results,
    }
    group_pool_counts_by_strategy = {
        BASELINE_STRATEGY_ID: {},
        PARENT_SUMMARY_STRATEGY_ID: parent_summary_run.pool_counts_by_query_id,
        SUMMARY_NODE_STRATEGY_ID: summary_node_run.pool_counts_by_query_id,
    }
    report = build_raptor_lite_input_only_report(
        items=target_items,
        documents=loaded_documents,
        strategy_results=strategy_results,
        group_pool_counts_by_strategy=group_pool_counts_by_strategy,
        dataset_path=dataset_path,
        chunks_path=chunks_path,
        baseline_rows_path=baseline_rows_path,
        result_rows_path=result_rows_path,
        expected_target_dev_query_count=expected_target_dev_query_count,
    )
    failures = collect_raptor_lite_input_only_failures(report)
    if failures and report.summary.decision != "blocked":
        report = _with_blocked_decision(report)
    final_failures = collect_raptor_lite_input_only_failures(report)
    if final_failures:
        raise ValueError(f"RAPTOR-lite input-only gate failed: {final_failures}")
    public_rows = build_public_raptor_lite_input_only_rows(
        report=report,
        items=target_items,
        strategy_results=strategy_results,
    )
    write_public_retrieval_result_rows(path=project_path(result_rows_path), rows=public_rows)
    resolved_report_path = project_path(report_path)
    resolved_report_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_report_path.write_text(
        build_raptor_lite_input_only_markdown(report),
        encoding="utf-8",
    )
    print(
        "raptor_lite_input_only "
        "status=PASS "
        f"target_dev_query_count={report.summary.target_dev_query_count} "
        f"candidate_count={report.summary.candidate_count} "
        f"best_strategy_id={report.summary.best_strategy_id} "
        f"decision={report.summary.decision}",
    )
    return report


def build_raptor_lite_input_only_report(
    *,
    items: list[RetrievalEvalItem],
    documents: list[RetrievalDocument],
    strategy_results: dict[str, list[RetrievalRunResult]],
    group_pool_counts_by_strategy: dict[str, dict[str, int]] | None = None,
    dataset_path: Path,
    chunks_path: Path,
    baseline_rows_path: Path,
    result_rows_path: Path,
    expected_target_dev_query_count: int,
) -> RaptorLiteInputOnlyReport:
    metric_rows = build_raptor_lite_metric_rows(
        items=items,
        documents=documents,
        strategy_results=strategy_results,
        group_pool_counts_by_strategy=group_pool_counts_by_strategy or {},
    )
    summary = build_raptor_lite_input_only_summary(
        items=items,
        metric_rows=metric_rows,
        expected_target_dev_query_count=expected_target_dev_query_count,
    )
    run_id = build_raptor_lite_input_only_run_id(items=items, metric_rows=metric_rows)
    public_rows = _build_public_rows_for_quality(
        run_id=run_id,
        summary=summary,
        metric_rows=metric_rows,
        items=items,
        strategy_results=strategy_results,
    )
    provisional_quality = measure_public_retrieval_artifact_quality(
        report_version=RAPTOR_LITE_INPUT_ONLY_REPORT_VERSION,
        run_id=run_id,
        result_rows=public_rows,
        report_text="",
    )
    report = RaptorLiteInputOnlyReport(
        run_id=run_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        dataset_path=public_path_alias(dataset_path),
        chunks_path_alias=public_path_alias(chunks_path),
        baseline_rows_path_alias=public_path_alias(baseline_rows_path),
        result_rows_path_alias=public_path_alias(result_rows_path),
        summary=summary,
        metric_rows=metric_rows,
        output_quality=provisional_quality,
        qualitative_assessment={},
    )
    report = report.model_copy(
        update={"qualitative_assessment": build_raptor_lite_qualitative_assessment(report)},
    )
    report_text = build_raptor_lite_input_only_markdown(report)
    final_quality = measure_public_retrieval_artifact_quality(
        report_version=RAPTOR_LITE_INPUT_ONLY_REPORT_VERSION,
        run_id=run_id,
        result_rows=public_rows,
        report_text=report_text,
    )
    report = report.model_copy(update={"output_quality": final_quality})
    return report.model_copy(
        update={"qualitative_assessment": build_raptor_lite_qualitative_assessment(report)},
    )


def build_raptor_lite_metric_rows(
    *,
    items: list[RetrievalEvalItem],
    documents: list[RetrievalDocument],
    strategy_results: dict[str, list[RetrievalRunResult]],
    group_pool_counts_by_strategy: dict[str, dict[str, int]] | None = None,
) -> tuple[RaptorLiteMetricRow, ...]:
    if BASELINE_STRATEGY_ID not in strategy_results:
        raise ValueError("baseline strategy result is required")
    scopes: tuple[RaptorLiteQueryScope, ...] = ("combined", "overview", "place_story")
    baseline_metrics = {
        scope: compute_retrieval_metrics(
            items=_items_for_scope(items, scope),
            results=_results_for_scope(strategy_results[BASELINE_STRATEGY_ID], scope),
            method="dense",
        )
        for scope in scopes
    }
    rows: list[RaptorLiteMetricRow] = []
    for strategy_id, results in strategy_results.items():
        role: RaptorLiteRole = "baseline" if strategy_id == BASELINE_STRATEGY_ID else "candidate"
        for scope in scopes:
            metric = compute_retrieval_metrics(
                items=_items_for_scope(items, scope),
                results=_results_for_scope(results, scope),
                method="dense",
            )
            rows.append(
                _build_metric_row(
                    strategy_id=strategy_id,
                    role=role,
                    query_scope=scope,
                    metric=metric,
                    baseline_metric=baseline_metrics[scope],
                    documents=documents,
                    results=_results_for_scope(results, scope),
                    group_pool_counts=((group_pool_counts_by_strategy or {}).get(strategy_id, {})),
                )
            )
    return tuple(rows)


def build_raptor_lite_input_only_summary(
    *,
    items: list[RetrievalEvalItem],
    metric_rows: tuple[RaptorLiteMetricRow, ...],
    expected_target_dev_query_count: int,
) -> RaptorLiteInputOnlySummary:
    if not metric_rows:
        raise ValueError("RAPTOR-lite input-only report requires metric rows")
    combined_rows = [row for row in metric_rows if row.query_scope == "combined"]
    candidate_rows = [row for row in combined_rows if row.role == "candidate"]
    best_row = max(
        combined_rows,
        key=lambda row: (row.ndcg_at_5, row.mrr, row.recall_at_5, -row.latency_p95_ms),
    )
    promoted_candidates = [
        row
        for row in candidate_rows
        if row.citation_recoverability >= MIN_CITATION_RECOVERABILITY
        and row.latency_p95_ms <= MAX_LATENCY_P95_MS
        and _has_no_query_type_recall_regression(
            strategy_id=row.strategy_id,
            metric_rows=metric_rows,
        )
        and (
            row.recall_at_5_delta >= TARGET_RECALL_AT_5_DELTA
            or row.mrr_delta >= TARGET_MRR_DELTA
            or row.ndcg_at_5_delta >= TARGET_NDCG_AT_5_DELTA
        )
    ]
    decision: RaptorLiteDecision = (
        "promote_raptor_lite_next_gate" if promoted_candidates else "reject_raptor_lite_default"
    )
    strategy_ids = {row.strategy_id for row in combined_rows}
    query_type_counts = Counter(item.query.query_type for item in items)
    return RaptorLiteInputOnlySummary(
        target_dev_query_count=len(items),
        expected_target_dev_query_count=expected_target_dev_query_count,
        query_type_counts=dict(sorted(query_type_counts.items())),
        strategy_count=len(strategy_ids),
        baseline_count=1 if BASELINE_STRATEGY_ID in strategy_ids else 0,
        candidate_count=len(strategy_ids - {BASELINE_STRATEGY_ID}),
        best_strategy_id=best_row.strategy_id,
        baseline_strategy_id=BASELINE_STRATEGY_ID,
        promoted_candidate_count=len(promoted_candidates),
        solar_call_count=sum(row.solar_call_count for row in combined_rows),
        min_citation_recoverability=min(row.citation_recoverability for row in metric_rows),
        target_recall_at_5_delta=TARGET_RECALL_AT_5_DELTA,
        target_mrr_delta=TARGET_MRR_DELTA,
        target_ndcg_at_5_delta=TARGET_NDCG_AT_5_DELTA,
        max_latency_p95_ms=MAX_LATENCY_P95_MS,
        decision=decision,
    )


def build_public_raptor_lite_input_only_rows(
    *,
    report: RaptorLiteInputOnlyReport,
    items: list[RetrievalEvalItem],
    strategy_results: dict[str, list[RetrievalRunResult]],
) -> list[dict[str, Any]]:
    return _build_public_rows_for_quality(
        run_id=report.run_id,
        summary=report.summary,
        metric_rows=report.metric_rows,
        items=items,
        strategy_results=strategy_results,
    )


def collect_raptor_lite_input_only_failures(
    report: RaptorLiteInputOnlyReport,
) -> list[str]:
    failures: list[str] = []
    failures.extend(collect_public_retrieval_artifact_failures(report.output_quality))
    summary = report.summary
    if summary.decision == "blocked":
        failures.append("input_only_decision_blocked")
    if summary.target_dev_query_count != summary.expected_target_dev_query_count:
        failures.append("target_dev_query_count_mismatch")
    if summary.baseline_count != 1:
        failures.append("baseline_count_must_be_one")
    if summary.candidate_count < 2:
        failures.append("candidate_count_must_be_at_least_two")
    if summary.solar_call_count != 0:
        failures.append("solar_call_count_must_be_zero")
    if summary.min_citation_recoverability < MIN_CITATION_RECOVERABILITY:
        failures.append("citation_recoverability_below_gate")
    for row in report.metric_rows:
        if row.query_scope not in {"combined", *TARGET_QUERY_TYPES}:
            failures.append("unsupported_query_scope_present")
        if row.result_count != row.query_count:
            failures.append(f"{row.strategy_id}_{row.query_scope}_missing_results")
        if not row.source_citation_only:
            failures.append(f"{row.strategy_id}_{row.query_scope}_non_source_citation_candidate")
    return failures


def build_raptor_lite_input_only_markdown(report: RaptorLiteInputOnlyReport) -> str:
    summary = report.summary
    quality = report.output_quality
    metric_rows = "\n".join(_format_metric_row(row) for row in report.metric_rows)
    delta_rows = "\n".join(
        _format_delta_row(row)
        for row in report.metric_rows
        if row.role == "candidate" and row.query_scope == "combined"
    )
    qualitative_rows = "\n".join(
        f"- `{key}`: {value}" for key, value in report.qualitative_assessment.items()
    )
    query_type_counts = ", ".join(
        f"{query_type}={count}" for query_type, count in summary.query_type_counts.items()
    )
    conclusion = (
        "RAPTOR-lite 후보는 dev input-only gate를 통과해 다음 locked gate 검토 대상이다."
        if summary.decision == "promote_raptor_lite_next_gate"
        else "RAPTOR-lite 후보는 dev input-only 기준에서 기본 RAG pipeline으로 승격하지 않는다."
    )
    return f"""# RAPTOR-lite Input-only Report

## 결론

{conclusion}

이 결과는 parent/doc summary-like group을 이용해 source child chunk 후보를 재정렬한 검색 입력 비교다. Solar Pro 3 호출, 답변 생성 품질, production 성능 개선 주장이 아니다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| run_id | `{report.run_id}` |
| generated_at_utc | `{report.generated_at_utc}` |
| dataset_path | `{report.dataset_path}` |
| chunks_path_alias | `{report.chunks_path_alias}` |
| baseline_rows_path_alias | `{report.baseline_rows_path_alias}` |
| result_rows_path_alias | `{report.result_rows_path_alias}` |
| target_query_types | `{', '.join(TARGET_QUERY_TYPES)}` |
| query_type_counts | `{query_type_counts}` |
| decision | `{summary.decision}` |
| best_strategy_id | `{summary.best_strategy_id}` |

## 정량 리포트

| strategy_id | role | query_scope | query_count | result_count | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | latency_p95_ms | citation_recoverability | summary_group_pool_count |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{metric_rows}

## Baseline Delta

| strategy_id | Recall@5 delta | MRR delta | nDCG@5 delta | latency_p95_ms delta |
| --- | ---: | ---: | ---: | ---: |
{delta_rows}

## Gate

| metric | value |
| --- | ---: |
| target_dev_query_count | {summary.target_dev_query_count} |
| expected_target_dev_query_count | {summary.expected_target_dev_query_count} |
| strategy_count | {summary.strategy_count} |
| baseline_count | {summary.baseline_count} |
| candidate_count | {summary.candidate_count} |
| promoted_candidate_count | {summary.promoted_candidate_count} |
| solar_call_count | {summary.solar_call_count} |
| min_citation_recoverability | {summary.min_citation_recoverability:.6f} |
| target_recall_at_5_delta | {summary.target_recall_at_5_delta:.6f} |
| target_mrr_delta | {summary.target_mrr_delta:.6f} |
| target_ndcg_at_5_delta | {summary.target_ndcg_at_5_delta:.6f} |
| max_latency_p95_ms | {summary.max_latency_p95_ms:.6f} |

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
"""


def build_raptor_lite_qualitative_assessment(
    report: RaptorLiteInputOnlyReport,
) -> dict[str, str]:
    combined_rows = [row for row in report.metric_rows if row.query_scope == "combined"]
    baseline = next(row for row in combined_rows if row.role == "baseline")
    candidates = [row for row in combined_rows if row.role == "candidate"]
    best_candidate = max(
        candidates,
        key=lambda row: (row.ndcg_at_5, row.mrr, row.recall_at_5, -row.latency_p95_ms),
    )
    return {
        "scope": "overview/place_story dev 20개에 한정한 input-only retrieval 후보 비교다.",
        "baseline": (
            f"{baseline.strategy_id} 기준 Recall@5={baseline.recall_at_5:.6f}, "
            f"MRR={baseline.mrr:.6f}, nDCG@5={baseline.ndcg_at_5:.6f}이다."
        ),
        "candidate_result": (
            f"최고 candidate는 {best_candidate.strategy_id}이며 "
            f"Recall@5 delta={best_candidate.recall_at_5_delta:.6f}, "
            f"MRR delta={best_candidate.mrr_delta:.6f}, "
            f"nDCG@5 delta={best_candidate.ndcg_at_5_delta:.6f}이다."
        ),
        "raptor_boundary": (
            "이번 구현은 LLM 요약 생성이 아니라 parent/doc group의 summary-like token signal만 사용하는 RAPTOR-lite다."
        ),
        "citation_boundary": (
            "summary-like group은 citation이 아니며 최종 후보는 source child chunk id로만 남겼다."
        ),
        "llm_boundary": "Solar Pro 3 호출은 0이다. 생성 품질 평가는 수행하지 않았다.",
        "data_boundary": (
            "public rows는 query id, candidate id, rank, metric, sanitized failure tag만 포함한다."
        ),
        "decision_boundary": (
            "dev input-only 결과이므로 locked test 또는 production 개선으로 표현하지 않는다."
        ),
        "external_audit": (
            "RAPTOR-lite가 유효하려면 overview/place_story에서 top-rank 품질 또는 recall이 기준선보다 올라야 한다."
        ),
        "gate_status": "PASS",
    }


def build_raptor_lite_input_only_run_id(
    *,
    items: list[RetrievalEvalItem],
    metric_rows: tuple[RaptorLiteMetricRow, ...],
) -> str:
    payload = {
        "query_ids": [item.query.query_id for item in items],
        "metric_rows": [row.model_dump(mode="json") for row in metric_rows],
    }
    digest = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:8]
    return f"raptor-lite-input-only-q{len(items)}-{digest}"


def _build_raptor_lite_candidate_results(
    *,
    strategy_id: str,
    items: list[RetrievalEvalItem],
    baseline_results: list[RetrievalRunResult],
    index: _RaptorLiteIndex,
    top_k: int,
) -> _RaptorLiteCandidateRun:
    baseline_by_query_id = {result.query_id: result for result in baseline_results}
    results: list[RetrievalRunResult] = []
    pool_counts_by_query_id: dict[str, int] = {}
    for item in items:
        baseline = baseline_by_query_id.get(item.query.query_id)
        if baseline is None:
            raise ValueError(f"missing baseline result for {item.query.query_id}")
        started = time.perf_counter()
        candidates, pool_count = _rank_raptor_lite_candidates(
            strategy_id=strategy_id,
            item=item,
            baseline=baseline,
            index=index,
            top_k=top_k,
        )
        elapsed_ms = round((time.perf_counter() - started) * 1000, 6)
        results.append(
            RetrievalRunResult(
                query_id=item.query.query_id,
                query_type=item.query.query_type,
                method="dense",
                candidates=candidates,
                latency_ms=round(baseline.latency_ms + elapsed_ms, 6),
            )
        )
        pool_counts_by_query_id[item.query.query_id] = pool_count
    return _RaptorLiteCandidateRun(
        results=results,
        pool_counts_by_query_id=pool_counts_by_query_id,
    )


def _rank_raptor_lite_candidates(
    *,
    strategy_id: str,
    item: RetrievalEvalItem,
    baseline: RetrievalRunResult,
    index: _RaptorLiteIndex,
    top_k: int,
) -> tuple[list[RetrievedCandidate], int]:
    query_tokens = _query_tokens(item)
    expanded_tokens = _expanded_query_tokens(
        query_tokens=query_tokens,
        index=index,
        include_doc_groups=strategy_id == SUMMARY_NODE_STRATEGY_ID,
    )
    baseline_doc_scores = _normalized_baseline_scores(baseline)
    baseline_parent_scores = _aggregate_group_scores(
        baseline_doc_scores,
        index=index,
        group_type="parent",
    )
    baseline_summary_scores = _aggregate_group_scores(
        baseline_doc_scores,
        index=index,
        group_type="doc",
    )
    groups = _candidate_groups_from_tokens(
        strategy_id=strategy_id,
        query_tokens=query_tokens,
        expanded_tokens=expanded_tokens,
        baseline=baseline,
        index=index,
    )
    scored_groups: list[tuple[float, _RaptorLiteGroup]] = []
    for group in groups:
        baseline_score = (
            baseline_parent_scores.get(group.group_id, 0.0)
            if group.group_type == "parent"
            else baseline_summary_scores.get(group.group_id, 0.0)
        )
        score = _raptor_group_score(
            strategy_id=strategy_id,
            group=group,
            baseline_score=baseline_score,
            query_tokens=query_tokens,
            expanded_tokens=expanded_tokens,
        )
        scored_groups.append((score, group))
    ranked_groups = sorted(
        scored_groups,
        key=lambda item_score: (item_score[0], item_score[1].group_id),
        reverse=True,
    )
    selected: list[tuple[float, RetrievalDocument]] = []
    selected_doc_ids: set[str] = set()
    for group_score, group in ranked_groups:
        for document, child_score in _rank_documents_in_group(
            group=group,
            index=index,
            query_tokens=query_tokens,
            expanded_tokens=expanded_tokens,
            baseline_doc_scores=baseline_doc_scores,
            max_children=(2 if strategy_id == SUMMARY_NODE_STRATEGY_ID else 1),
        ):
            if document.retrieval_doc_id in selected_doc_ids:
                continue
            selected.append((round(group_score + 0.25 * child_score, 9), document))
            selected_doc_ids.add(document.retrieval_doc_id)
            if len(selected) >= top_k:
                break
        if len(selected) >= top_k:
            break
    if len(selected) < top_k:
        for candidate in baseline.candidates:
            if candidate.retrieval_doc_id in selected_doc_ids:
                continue
            document = index.documents_by_id.get(candidate.retrieval_doc_id)
            if document is None:
                continue
            selected.append((candidate.score, document))
            selected_doc_ids.add(candidate.retrieval_doc_id)
            if len(selected) >= top_k:
                break
    candidates = [
        _candidate_from_document(rank=rank, document=document, score=score)
        for rank, (score, document) in enumerate(selected[:top_k], start=1)
    ]
    return candidates, len(groups)


def _build_raptor_lite_index(documents: list[RetrievalDocument]) -> _RaptorLiteIndex:
    documents_by_id = {document.retrieval_doc_id: document for document in documents}
    tokens_by_doc_id = {
        document.retrieval_doc_id: frozenset(_document_tokens(document))
        for document in documents
    }
    document_ids_by_parent: dict[str, list[str]] = defaultdict(list)
    document_ids_by_doc: dict[str, list[str]] = defaultdict(list)
    for document in documents:
        document_ids_by_parent[document.parent_id].append(document.retrieval_doc_id)
        document_ids_by_doc[document.doc_id].append(document.retrieval_doc_id)
    parent_groups = {
        parent_id: _build_group(
            group_id=parent_id,
            group_type="parent",
            document_ids=tuple(sorted(document_ids)),
            tokens_by_doc_id=tokens_by_doc_id,
        )
        for parent_id, document_ids in document_ids_by_parent.items()
    }
    doc_groups = {
        _doc_group_id(doc_id): _build_group(
            group_id=_doc_group_id(doc_id),
            group_type="doc",
            document_ids=tuple(sorted(document_ids)),
            tokens_by_doc_id=tokens_by_doc_id,
        )
        for doc_id, document_ids in document_ids_by_doc.items()
    }
    return _RaptorLiteIndex(
        documents_by_id=documents_by_id,
        tokens_by_doc_id=tokens_by_doc_id,
        parent_groups=parent_groups,
        doc_groups=doc_groups,
        token_to_parent_ids=_build_token_to_group_ids(parent_groups),
        token_to_doc_group_ids=_build_token_to_group_ids(doc_groups),
    )


def _build_group(
    *,
    group_id: str,
    group_type: RaptorLiteGroupType,
    document_ids: tuple[str, ...],
    tokens_by_doc_id: dict[str, frozenset[str]],
) -> _RaptorLiteGroup:
    tokens: set[str] = set()
    for document_id in document_ids:
        tokens.update(tokens_by_doc_id.get(document_id, frozenset()))
    return _RaptorLiteGroup(
        group_id=group_id,
        group_type=group_type,
        document_ids=document_ids,
        tokens=frozenset(tokens),
    )


def _build_token_to_group_ids(
    groups: dict[str, _RaptorLiteGroup],
) -> dict[str, frozenset[str]]:
    token_to_ids: dict[str, set[str]] = defaultdict(set)
    for group_id, group in groups.items():
        for token in group.tokens:
            token_to_ids[token].add(group_id)
    return dict((term, frozenset(ids)) for term, ids in token_to_ids.items())


def _query_tokens(item: RetrievalEvalItem) -> frozenset[str]:
    raw_parts = [item.query.query_text, item.query.user_context or ""]
    raw_parts.extend(item.metadata.place_ids)
    counter = Counter(_tokenize(" ".join(raw_parts)))
    selected = [token for token, _count in counter.most_common() if token not in _STOPWORDS][
        :MAX_QUERY_TOKEN_COUNT
    ]
    return frozenset(selected)


def _expanded_query_tokens(
    *,
    query_tokens: frozenset[str],
    index: _RaptorLiteIndex,
    include_doc_groups: bool,
) -> frozenset[str]:
    neighbor_counts: Counter[str] = Counter()
    for token in query_tokens:
        parent_ids = sorted(index.token_to_parent_ids.get(token, frozenset()))[
            :MAX_GROUPS_PER_TERM
        ]
        for parent_id in parent_ids:
            neighbor_counts.update(index.parent_groups[parent_id].tokens)
        if include_doc_groups:
            doc_group_ids = sorted(index.token_to_doc_group_ids.get(token, frozenset()))[
                :MAX_GROUPS_PER_TERM
            ]
            for doc_group_id in doc_group_ids:
                neighbor_counts.update(index.doc_groups[doc_group_id].tokens)
    for token in query_tokens:
        neighbor_counts.pop(token, None)
    selected = [
        token
        for token, _count in neighbor_counts.most_common(MAX_EXPANDED_TOKEN_COUNT)
        if token not in _STOPWORDS
    ]
    return frozenset(set(selected) | set(query_tokens))


def _candidate_groups_from_tokens(
    *,
    strategy_id: str,
    query_tokens: frozenset[str],
    expanded_tokens: frozenset[str],
    baseline: RetrievalRunResult,
    index: _RaptorLiteIndex,
) -> tuple[_RaptorLiteGroup, ...]:
    parent_ids: set[str] = set()
    doc_group_ids: set[str] = set()
    for candidate in baseline.candidates:
        document = index.documents_by_id.get(candidate.retrieval_doc_id)
        if document is None:
            continue
        parent_ids.add(document.parent_id)
        doc_group_ids.add(_doc_group_id(document.doc_id))
    token_weights: Counter[str] = Counter()
    for token in query_tokens:
        token_weights[token] += 3
    for token in expanded_tokens:
        if token not in query_tokens:
            token_weights[token] += 1
    parent_scores: Counter[str] = Counter()
    doc_scores: Counter[str] = Counter()
    for token, weight in token_weights.items():
        for parent_id in sorted(index.token_to_parent_ids.get(token, frozenset()))[
            :MAX_GROUPS_PER_TERM
        ]:
            parent_scores[parent_id] += weight
        if strategy_id == SUMMARY_NODE_STRATEGY_ID:
            for doc_group_id in sorted(index.token_to_doc_group_ids.get(token, frozenset()))[
                :MAX_GROUPS_PER_TERM
            ]:
                doc_scores[doc_group_id] += weight
    parent_ids.update(
        parent_id for parent_id, _score in parent_scores.most_common(MAX_GROUP_POOL_SIZE)
    )
    if strategy_id == SUMMARY_NODE_STRATEGY_ID:
        doc_group_ids.update(
            doc_group_id
            for doc_group_id, _score in doc_scores.most_common(MAX_GROUP_POOL_SIZE // 2)
        )
    groups: list[_RaptorLiteGroup] = [
        index.parent_groups[parent_id]
        for parent_id in sorted(parent_ids)
        if parent_id in index.parent_groups
    ]
    if strategy_id == SUMMARY_NODE_STRATEGY_ID:
        groups.extend(
            index.doc_groups[doc_group_id]
            for doc_group_id in sorted(doc_group_ids)
            if doc_group_id in index.doc_groups
        )
    return tuple(groups[:MAX_GROUP_POOL_SIZE])


def _rank_documents_in_group(
    *,
    group: _RaptorLiteGroup,
    index: _RaptorLiteIndex,
    query_tokens: frozenset[str],
    expanded_tokens: frozenset[str],
    baseline_doc_scores: dict[str, float],
    max_children: int,
) -> list[tuple[RetrievalDocument, float]]:
    scored: list[tuple[float, RetrievalDocument]] = []
    for document_id in group.document_ids:
        document = index.documents_by_id[document_id]
        tokens = index.tokens_by_doc_id.get(document_id, frozenset())
        direct_ratio = len(query_tokens & tokens) / max(len(query_tokens), 1)
        expanded_ratio = len(expanded_tokens & tokens) / max(len(expanded_tokens), 1)
        narrative_ratio = min(len(_NARRATIVE_HINT_TOKENS & tokens) / 5, 1.0)
        baseline_score = baseline_doc_scores.get(document_id, 0.0)
        score = round(
            0.50 * baseline_score
            + 0.32 * direct_ratio
            + 0.13 * expanded_ratio
            + 0.05 * narrative_ratio,
            9,
        )
        scored.append((score, document))
    ranked = sorted(
        scored,
        key=lambda item_score: (item_score[0], item_score[1].retrieval_doc_id),
        reverse=True,
    )
    return [(document, score) for score, document in ranked[:max_children]]


def _raptor_group_score(
    *,
    strategy_id: str,
    group: _RaptorLiteGroup,
    baseline_score: float,
    query_tokens: frozenset[str],
    expanded_tokens: frozenset[str],
) -> float:
    direct_ratio = len(query_tokens & group.tokens) / max(len(query_tokens), 1)
    expanded_ratio = len(expanded_tokens & group.tokens) / max(len(expanded_tokens), 1)
    narrative_ratio = min(len(_NARRATIVE_HINT_TOKENS & group.tokens) / 7, 1.0)
    size_penalty = min(math.log(max(len(group.document_ids), 1), 20) * 0.02, 0.10)
    if strategy_id == PARENT_SUMMARY_STRATEGY_ID:
        return round(
            0.48 * baseline_score
            + 0.32 * direct_ratio
            + 0.16 * expanded_ratio
            + 0.04 * narrative_ratio
            - size_penalty,
            9,
        )
    if strategy_id == SUMMARY_NODE_STRATEGY_ID:
        doc_bonus = 0.03 if group.group_type == "doc" else 0.0
        return round(
            0.38 * baseline_score
            + 0.30 * direct_ratio
            + 0.22 * expanded_ratio
            + 0.07 * narrative_ratio
            + doc_bonus
            - size_penalty,
            9,
        )
    raise ValueError(f"unsupported RAPTOR-lite strategy: {strategy_id}")


def _aggregate_group_scores(
    baseline_doc_scores: dict[str, float],
    *,
    index: _RaptorLiteIndex,
    group_type: RaptorLiteGroupType,
) -> dict[str, float]:
    scores: dict[str, float] = {}
    groups = index.parent_groups if group_type == "parent" else index.doc_groups
    for group_id, group in groups.items():
        group_scores = [
            baseline_doc_scores.get(document_id, 0.0)
            for document_id in group.document_ids
            if document_id in baseline_doc_scores
        ]
        if group_scores:
            scores[group_id] = max(group_scores)
    return scores


def _document_tokens(document: RetrievalDocument) -> list[str]:
    return _tokenize(
        "\n".join(
            part
            for part in [
                document.doc_title,
                document.search_text or "",
                document.context_text or "",
            ]
            if part
        )
    )


def _tokenize(text: str) -> list[str]:
    tokens = [match.group(0).lower() for match in _TOKEN_PATTERN.finditer(text)]
    return [token for token in tokens if token not in _STOPWORDS and not token.isdigit()]


def _normalized_baseline_scores(result: RetrievalRunResult) -> dict[str, float]:
    if not result.candidates:
        return {}
    scores = [candidate.score for candidate in result.candidates]
    min_score = min(scores)
    max_score = max(scores)
    normalized: dict[str, float] = {}
    for candidate in result.candidates:
        if math.isclose(max_score, min_score):
            score = 1.0 / candidate.rank
        else:
            score = (candidate.score - min_score) / (max_score - min_score)
        normalized[candidate.retrieval_doc_id] = max(score, 1.0 / (candidate.rank + 1))
    return normalized


def _candidate_from_document(
    *,
    rank: int,
    document: RetrievalDocument,
    score: float,
) -> RetrievedCandidate:
    return RetrievedCandidate(
        rank=rank,
        retrieval_doc_id=document.retrieval_doc_id,
        child_id=document.child_id,
        parent_id=document.parent_id,
        doc_id=document.doc_id,
        score=round(score, 6),
    )


def _target_dev_items(items: list[RetrievalEvalItem]) -> list[RetrievalEvalItem]:
    return [
        item
        for item in items
        if item.query.query_type in TARGET_QUERY_TYPES
        and item.metadata.split == "dev"
        and item.metadata.review_status == "reviewed"
    ]


def _items_for_scope(
    items: list[RetrievalEvalItem],
    scope: RaptorLiteQueryScope,
) -> list[RetrievalEvalItem]:
    if scope == "combined":
        return items
    return [item for item in items if item.query.query_type == scope]


def _results_for_scope(
    results: list[RetrievalRunResult],
    scope: RaptorLiteQueryScope,
) -> list[RetrievalRunResult]:
    if scope == "combined":
        return results
    return [result for result in results if result.query_type == scope]


def _load_or_recompute_baseline_results(
    *,
    items: list[RetrievalEvalItem],
    documents: list[RetrievalDocument],
    baseline_rows_path: Path,
    force_recompute_baseline: bool,
    top_k: int,
    embedding_cache_dir: Path,
    place_catalog_path: Path,
) -> list[RetrievalRunResult]:
    if baseline_rows_path.exists() and not force_recompute_baseline:
        return load_baseline_results_from_public_rows(
            path=baseline_rows_path,
            items=items,
            method="dense",
        )
    plan = _build_method_plans([BASELINE_METHOD_KEY])[0]
    execution = _execute_method(
        plan=plan,
        items=items,
        documents=documents,
        top_k=top_k,
        embedding_cache_dir=embedding_cache_dir,
        place_catalog_path=place_catalog_path,
        execution_context=_ExecutionContext(),
    )
    return execution.results


def load_baseline_results_from_public_rows(
    *,
    path: Path,
    items: list[RetrievalEvalItem],
    method: Literal["dense"] = "dense",
) -> list[RetrievalRunResult]:
    allowed_query_ids = {item.query.query_id for item in items}
    query_type_by_query_id = {item.query.query_id: item.query.query_type for item in items}
    rows_by_query_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        query_id = str(row.get("query_id", ""))
        if query_id in allowed_query_ids:
            rows_by_query_id[query_id].append(row)
    results: list[RetrievalRunResult] = []
    for item in items:
        rows = sorted(
            rows_by_query_id.get(item.query.query_id, []),
            key=lambda row: int(row.get("rank") or 999),
        )
        candidates = [
            RetrievedCandidate(
                rank=int(row["rank"]),
                retrieval_doc_id=str(row["retrieval_doc_id"]),
                child_id=str(row["child_id"]),
                parent_id=str(row["parent_id"]),
                doc_id=str(row["doc_id"]),
                score=float(row["score"]),
            )
            for row in rows
            if row.get("rank") is not None
        ]
        latency = float(rows[0].get("latency_ms", 0.0)) if rows else 0.0
        results.append(
            RetrievalRunResult(
                query_id=item.query.query_id,
                query_type=query_type_by_query_id[item.query.query_id],
                method=method,
                candidates=candidates[:DEFAULT_TOP_K],
                latency_ms=latency,
            )
        )
    return results


def _build_metric_row(
    *,
    strategy_id: str,
    role: RaptorLiteRole,
    query_scope: RaptorLiteQueryScope,
    metric: RetrievalMetricSummary,
    baseline_metric: RetrievalMetricSummary,
    documents: list[RetrievalDocument],
    results: list[RetrievalRunResult],
    group_pool_counts: dict[str, int],
) -> RaptorLiteMetricRow:
    recoverability = _citation_recoverability(documents=documents, results=results)
    return RaptorLiteMetricRow(
        strategy_id=strategy_id,
        role=role,
        query_scope=query_scope,
        query_count=metric.query_count,
        result_count=metric.result_count,
        missing_result_count=metric.missing_result_count,
        recall_at_1=metric.recall_at_1,
        recall_at_3=metric.recall_at_3,
        recall_at_5=metric.recall_at_5,
        mrr=metric.mrr,
        ndcg_at_5=metric.ndcg_at_5,
        latency_p95_ms=metric.latency_p95_ms,
        citation_recoverability=recoverability,
        recall_at_5_delta=round(metric.recall_at_5 - baseline_metric.recall_at_5, 6),
        mrr_delta=round(metric.mrr - baseline_metric.mrr, 6),
        ndcg_at_5_delta=round(metric.ndcg_at_5 - baseline_metric.ndcg_at_5, 6),
        latency_p95_ms_delta=round(
            metric.latency_p95_ms - baseline_metric.latency_p95_ms,
            6,
        ),
        summary_group_pool_count=_mean_group_pool_count(
            group_pool_counts=group_pool_counts,
            results=results,
        ),
        source_citation_only=recoverability >= 1.0,
        solar_call_count=0,
        claim_boundary="dev_input_only",
    )


def _mean_group_pool_count(
    *,
    group_pool_counts: dict[str, int],
    results: list[RetrievalRunResult],
) -> int:
    if not group_pool_counts:
        return 0
    query_ids = {result.query_id for result in results}
    values = [count for query_id, count in group_pool_counts.items() if query_id in query_ids]
    if not values:
        return 0
    return int(round(sum(values) / len(values)))


def _citation_recoverability(
    *,
    documents: list[RetrievalDocument],
    results: list[RetrievalRunResult],
) -> float:
    document_by_id = {document.retrieval_doc_id: document for document in documents}
    candidates = [candidate for result in results for candidate in result.candidates]
    if not candidates:
        return 1.0
    recovered = 0
    for candidate in candidates:
        document = document_by_id.get(candidate.retrieval_doc_id)
        if document and document.child_id == candidate.child_id and document.citation_block_ids:
            recovered += 1
    return round(recovered / len(candidates), 6)


def _has_no_query_type_recall_regression(
    *,
    strategy_id: str,
    metric_rows: tuple[RaptorLiteMetricRow, ...],
) -> bool:
    rows = [
        row
        for row in metric_rows
        if row.strategy_id == strategy_id and row.query_scope in TARGET_QUERY_TYPES
    ]
    return bool(rows) and all(row.recall_at_5_delta >= 0.0 for row in rows)


def _build_public_rows_for_quality(
    *,
    run_id: str,
    summary: RaptorLiteInputOnlySummary,
    metric_rows: tuple[RaptorLiteMetricRow, ...],
    items: list[RetrievalEvalItem],
    strategy_results: dict[str, list[RetrievalRunResult]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "row_type": "summary",
            "run_id": run_id,
            "target_dev_query_count": summary.target_dev_query_count,
            "expected_target_dev_query_count": summary.expected_target_dev_query_count,
            "strategy_count": summary.strategy_count,
            "baseline_count": summary.baseline_count,
            "candidate_count": summary.candidate_count,
            "best_strategy_id": summary.best_strategy_id,
            "promoted_candidate_count": summary.promoted_candidate_count,
            "solar_call_count": summary.solar_call_count,
            "min_citation_recoverability": summary.min_citation_recoverability,
            "decision": summary.decision,
        },
    ]
    rows.extend(_metric_public_row(run_id=run_id, row=row) for row in metric_rows)
    baseline_results = strategy_results.get(BASELINE_STRATEGY_ID, [])
    baseline_rank_by_query_id = {
        result.query_id: _first_relevant_rank(_item_by_query_id(items, result.query_id), result)
        for result in baseline_results
    }
    for strategy_id, results in strategy_results.items():
        for result in results:
            item = _item_by_query_id(items, result.query_id)
            rows.append(
                _query_public_row(
                    run_id=run_id,
                    strategy_id=strategy_id,
                    item=item,
                    result=result,
                    baseline_first_relevant_rank=baseline_rank_by_query_id.get(
                        result.query_id,
                    ),
                )
            )
    return rows


def _metric_public_row(
    *,
    run_id: str,
    row: RaptorLiteMetricRow,
) -> dict[str, Any]:
    return {
        "row_type": "metric",
        "run_id": run_id,
        "strategy_id": row.strategy_id,
        "role": row.role,
        "query_scope": row.query_scope,
        "query_count": row.query_count,
        "result_count": row.result_count,
        "recall_at_1": row.recall_at_1,
        "recall_at_3": row.recall_at_3,
        "recall_at_5": row.recall_at_5,
        "mrr": row.mrr,
        "ndcg_at_5": row.ndcg_at_5,
        "latency_p95_ms": row.latency_p95_ms,
        "citation_recoverability": row.citation_recoverability,
        "recall_at_5_delta": row.recall_at_5_delta,
        "mrr_delta": row.mrr_delta,
        "ndcg_at_5_delta": row.ndcg_at_5_delta,
        "latency_p95_ms_delta": row.latency_p95_ms_delta,
        "summary_group_pool_count": row.summary_group_pool_count,
        "source_citation_only": row.source_citation_only,
        "solar_call_count": row.solar_call_count,
        "claim_boundary": row.claim_boundary,
    }


def _query_public_row(
    *,
    run_id: str,
    strategy_id: str,
    item: RetrievalEvalItem,
    result: RetrievalRunResult,
    baseline_first_relevant_rank: int | None,
) -> dict[str, Any]:
    first_rank = _first_relevant_rank(item, result)
    return {
        "row_type": "query_metric",
        "run_id": run_id,
        "strategy_id": strategy_id,
        "query_id": item.query.query_id,
        "query_type": item.query.query_type,
        "hit_at_1": first_rank == 1,
        "hit_at_3": first_rank is not None and first_rank <= 3,
        "hit_at_5": first_rank is not None and first_rank <= 5,
        "first_relevant_rank": first_rank,
        "baseline_first_relevant_rank": baseline_first_relevant_rank,
        "candidate_count": len(result.candidates),
        "latency_ms": result.latency_ms,
        "top_child_id": result.candidates[0].child_id if result.candidates else None,
        "top_parent_id": result.candidates[0].parent_id if result.candidates else None,
        "failure_tag": _failure_tag(
            first_rank=first_rank,
            baseline_first_rank=baseline_first_relevant_rank,
            is_baseline=strategy_id == BASELINE_STRATEGY_ID,
        ),
        "metric_family": "retrieval",
        "claim_boundary": "dev_input_only",
    }


def _first_relevant_rank(
    item: RetrievalEvalItem,
    result: RetrievalRunResult,
) -> int | None:
    for candidate in result.candidates:
        if _candidate_is_relevant(item=item, candidate=candidate):
            return candidate.rank
    return None


def _candidate_is_relevant(
    *,
    item: RetrievalEvalItem,
    candidate: RetrievedCandidate,
) -> bool:
    child_ids: set[str] = set()
    parent_ids: set[str] = set()
    doc_ids: set[str] = set()
    for judgment in item.judgments:
        child_ids.update(judgment.relevant_child_ids)
        parent_ids.update(judgment.relevant_parent_ids)
        doc_ids.update(judgment.relevant_doc_ids)
    return (
        candidate.child_id in child_ids
        or candidate.parent_id in parent_ids
        or candidate.doc_id in doc_ids
    )


def _failure_tag(
    *,
    first_rank: int | None,
    baseline_first_rank: int | None,
    is_baseline: bool,
) -> str:
    if is_baseline:
        return "none" if first_rank is not None else "baseline_target_not_in_top5"
    if first_rank is None:
        return "candidate_target_not_in_top5"
    if baseline_first_rank is None:
        return "candidate_recovered_baseline_miss"
    if first_rank > baseline_first_rank:
        return "candidate_rank_regression"
    if first_rank < baseline_first_rank:
        return "candidate_rank_improvement"
    return "none"


def _item_by_query_id(
    items: list[RetrievalEvalItem],
    query_id: str,
) -> RetrievalEvalItem:
    for item in items:
        if item.query.query_id == query_id:
            return item
    raise ValueError(f"unknown query_id in RAPTOR-lite public row build: {query_id}")


def _with_blocked_decision(
    report: RaptorLiteInputOnlyReport,
) -> RaptorLiteInputOnlyReport:
    updated_summary = report.summary.model_copy(update={"decision": "blocked"})
    updated_report = report.model_copy(update={"summary": updated_summary})
    return updated_report.model_copy(
        update={"qualitative_assessment": build_raptor_lite_qualitative_assessment(updated_report)}
    )


def _format_metric_row(row: RaptorLiteMetricRow) -> str:
    return (
        f"| `{row.strategy_id}` | {row.role} | {row.query_scope} | "
        f"{row.query_count} | {row.result_count} | "
        f"{row.recall_at_1:.6f} | {row.recall_at_3:.6f} | "
        f"{row.recall_at_5:.6f} | {row.mrr:.6f} | {row.ndcg_at_5:.6f} | "
        f"{row.latency_p95_ms:.6f} | {row.citation_recoverability:.6f} | "
        f"{row.summary_group_pool_count} |"
    )


def _format_delta_row(row: RaptorLiteMetricRow) -> str:
    return (
        f"| `{row.strategy_id}` | {row.recall_at_5_delta:.6f} | "
        f"{row.mrr_delta:.6f} | {row.ndcg_at_5_delta:.6f} | "
        f"{row.latency_p95_ms_delta:.6f} |"
    )


def _doc_group_id(doc_id: str) -> str:
    return f"doc::{doc_id}"


def main() -> int:
    args = _parse_args()
    report = run_raptor_lite_input_only(
        chunks_path=args.chunks,
        dataset_path=args.dataset,
        baseline_rows_path=args.baseline_rows,
        result_rows_path=args.result_rows,
        report_path=args.report,
        force_recompute_baseline=args.recompute_baseline,
    )
    return 0 if not collect_raptor_lite_input_only_failures(report) else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run RAPTOR-lite overview/place_story input-only retrieval comparison.",
    )
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS_PATH)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--baseline-rows", type=Path, default=DEFAULT_BASELINE_ROWS_PATH)
    parser.add_argument("--result-rows", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument(
        "--recompute-baseline",
        action="store_true",
        help="Recompute the E5-small voice rewrite baseline instead of loading private rows.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
