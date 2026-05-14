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
from itertools import combinations
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


GRAPHRAG_LITE_RELATIONSHIP_INPUT_ONLY_REPORT_VERSION = (
    "graphrag-lite-relationship-input-only-report/v1"
)
BASELINE_METHOD_KEY = "hybrid_weighted_e5_small_alpha_0_5"
BASELINE_STRATEGY_ID = "hybrid_weighted_e5_small_alpha_0_5_reference"
ENTITY_PATH_STRATEGY_ID = "graphrag_lite_entity_path_v1"
COMMUNITY_HINT_STRATEGY_ID = "graphrag_lite_community_hint_v1"
DEFAULT_TOP_K = 5
DEFAULT_EXPECTED_RELATIONSHIP_DEV_QUERY_COUNT = 10
DEFAULT_CHUNKS_PATH = Path("private_data") / "reports" / "parent_child_chunks.json"
DEFAULT_DATASET_PATH = Path("private_data") / "evals" / "datasets" / "retrieval_eval_dev.jsonl"
DEFAULT_BASELINE_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / f"retrieval_experiment_{BASELINE_METHOD_KEY}_results.jsonl"
)
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data") / "evals" / "results" / "graphrag_lite_relationship_input_only_rows.jsonl"
)
DEFAULT_REPORT_PATH = Path("evals") / "reports" / "graphrag_lite_relationship_input_only_report.md"
TARGET_RECALL_AT_5_DELTA = 0.03
TARGET_MRR_DELTA = 0.03
TARGET_NDCG_AT_5_DELTA = 0.03
MIN_CITATION_RECOVERABILITY = 0.99
MAX_LATENCY_P95_MS = 2500.0
MAX_QUERY_TOKEN_COUNT = 14
MAX_EXPANDED_TOKEN_COUNT = 24
MAX_DIRECT_DOCS_PER_TERM = 350
MAX_GRAPH_CANDIDATE_POOL_SIZE = 120

GraphRagLiteRole = Literal["baseline", "candidate"]
GraphRagLiteDecision = Literal[
    "promote_graphrag_lite_next_gate",
    "reject_graphrag_lite_default",
    "blocked",
]

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
        "관계",
        "설명",
        "알려",
        "말해",
        "차이",
        "영향",
        "이유",
        "사이",
        "history",
        "docent",
    }
)
_RELATION_HINT_TOKENS = frozenset(
    {
        "권력",
        "정치",
        "왕",
        "왕조",
        "신하",
        "궁궐",
        "도성",
        "천도",
        "개혁",
        "전쟁",
        "제도",
        "사건",
        "인물",
        "장소",
        "한양",
        "조선",
    }
)


class GraphRagLiteRelationshipInputOnlyModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class GraphRagLiteMetricRow(GraphRagLiteRelationshipInputOnlyModel):
    strategy_id: str = Field(min_length=1)
    role: GraphRagLiteRole
    query_type: Literal["relationship"]
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
    graph_candidate_pool_count: int = Field(ge=0)
    source_citation_only: bool
    solar_call_count: int = Field(ge=0)
    claim_boundary: Literal["dev_input_only"]


class GraphRagLiteInputOnlySummary(GraphRagLiteRelationshipInputOnlyModel):
    relationship_dev_query_count: int = Field(ge=0)
    expected_relationship_dev_query_count: int = Field(ge=0)
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
    decision: GraphRagLiteDecision


class GraphRagLiteRelationshipInputOnlyReport(
    GraphRagLiteRelationshipInputOnlyModel,
):
    report_version: str = GRAPHRAG_LITE_RELATIONSHIP_INPUT_ONLY_REPORT_VERSION
    run_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    dataset_path: str = Field(min_length=1)
    chunks_path_alias: str = Field(min_length=1)
    baseline_rows_path_alias: str = Field(min_length=1)
    result_rows_path_alias: str = Field(min_length=1)
    summary: GraphRagLiteInputOnlySummary
    metric_rows: tuple[GraphRagLiteMetricRow, ...]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


@dataclass(frozen=True)
class _GraphRagLiteIndex:
    documents_by_id: dict[str, RetrievalDocument]
    tokens_by_doc_id: dict[str, frozenset[str]]
    token_to_doc_ids: dict[str, frozenset[str]]


@dataclass(frozen=True)
class _GraphRagLiteCandidateRun:
    results: list[RetrievalRunResult]
    pool_counts_by_query_id: dict[str, int]


def run_graphrag_lite_relationship_input_only(
    *,
    chunks_path: Path = DEFAULT_CHUNKS_PATH,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    baseline_rows_path: Path = DEFAULT_BASELINE_ROWS_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    top_k: int = DEFAULT_TOP_K,
    expected_relationship_dev_query_count: int = (DEFAULT_EXPECTED_RELATIONSHIP_DEV_QUERY_COUNT),
    force_recompute_baseline: bool = False,
    embedding_cache_dir: Path = DEFAULT_EMBEDDING_CACHE_DIR,
    place_catalog_path: Path = DEFAULT_PLACE_CATALOG_PATH,
    items: list[RetrievalEvalItem] | None = None,
    documents: list[RetrievalDocument] | None = None,
    baseline_results: list[RetrievalRunResult] | None = None,
) -> GraphRagLiteRelationshipInputOnlyReport:
    if top_k != 5:
        raise ValueError("GraphRAG-lite relationship gate is fixed to top_k=5")
    loaded_items = items or load_retrieval_eval_jsonl(project_path(dataset_path))
    relationship_items = _relationship_dev_items(loaded_items)
    loaded_documents = documents or load_retrieval_documents_from_chunks(
        project_path(chunks_path),
    )
    baseline = baseline_results or _load_or_recompute_baseline_results(
        items=relationship_items,
        documents=loaded_documents,
        baseline_rows_path=project_path(baseline_rows_path),
        force_recompute_baseline=force_recompute_baseline,
        top_k=top_k,
        embedding_cache_dir=project_path(embedding_cache_dir),
        place_catalog_path=project_path(place_catalog_path),
    )
    index = _build_graphrag_lite_index(loaded_documents)
    entity_path_run = _build_graphrag_lite_candidate_results(
        strategy_id=ENTITY_PATH_STRATEGY_ID,
        items=relationship_items,
        baseline_results=baseline,
        index=index,
        top_k=top_k,
    )
    community_hint_run = _build_graphrag_lite_candidate_results(
        strategy_id=COMMUNITY_HINT_STRATEGY_ID,
        items=relationship_items,
        baseline_results=baseline,
        index=index,
        top_k=top_k,
    )
    strategy_results = {
        BASELINE_STRATEGY_ID: baseline,
        ENTITY_PATH_STRATEGY_ID: entity_path_run.results,
        COMMUNITY_HINT_STRATEGY_ID: community_hint_run.results,
    }
    graph_pool_counts_by_strategy = {
        BASELINE_STRATEGY_ID: {},
        ENTITY_PATH_STRATEGY_ID: entity_path_run.pool_counts_by_query_id,
        COMMUNITY_HINT_STRATEGY_ID: community_hint_run.pool_counts_by_query_id,
    }
    report = build_graphrag_lite_relationship_input_only_report(
        items=relationship_items,
        documents=loaded_documents,
        strategy_results=strategy_results,
        graph_pool_counts_by_strategy=graph_pool_counts_by_strategy,
        dataset_path=dataset_path,
        chunks_path=chunks_path,
        baseline_rows_path=baseline_rows_path,
        result_rows_path=result_rows_path,
        expected_relationship_dev_query_count=expected_relationship_dev_query_count,
    )
    failures = collect_graphrag_lite_relationship_input_only_failures(report)
    if failures and report.summary.decision != "blocked":
        report = _with_blocked_decision(report)
    final_failures = collect_graphrag_lite_relationship_input_only_failures(report)
    if final_failures:
        raise ValueError(f"graphrag-lite relationship input-only gate failed: {final_failures}")
    public_rows = build_public_graphrag_lite_input_only_rows(
        report=report,
        items=relationship_items,
        strategy_results=strategy_results,
    )
    write_public_retrieval_result_rows(path=project_path(result_rows_path), rows=public_rows)
    report_path = project_path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        build_graphrag_lite_relationship_input_only_markdown(report),
        encoding="utf-8",
    )
    print(
        "graphrag_lite_relationship_input_only "
        "status=PASS "
        f"relationship_dev_query_count={report.summary.relationship_dev_query_count} "
        f"candidate_count={report.summary.candidate_count} "
        f"best_strategy_id={report.summary.best_strategy_id} "
        f"decision={report.summary.decision}",
    )
    return report


def build_graphrag_lite_relationship_input_only_report(
    *,
    items: list[RetrievalEvalItem],
    documents: list[RetrievalDocument],
    strategy_results: dict[str, list[RetrievalRunResult]],
    graph_pool_counts_by_strategy: dict[str, dict[str, int]] | None = None,
    dataset_path: Path,
    chunks_path: Path,
    baseline_rows_path: Path,
    result_rows_path: Path,
    expected_relationship_dev_query_count: int,
) -> GraphRagLiteRelationshipInputOnlyReport:
    metric_rows = build_graphrag_lite_metric_rows(
        items=items,
        documents=documents,
        strategy_results=strategy_results,
        graph_pool_counts_by_strategy=graph_pool_counts_by_strategy or {},
    )
    summary = build_graphrag_lite_input_only_summary(
        metric_rows=metric_rows,
        relationship_dev_query_count=len(items),
        expected_relationship_dev_query_count=expected_relationship_dev_query_count,
    )
    run_id = build_graphrag_lite_relationship_input_only_run_id(
        items=items,
        metric_rows=metric_rows,
    )
    public_rows = _build_public_rows_for_quality(
        run_id=run_id,
        summary=summary,
        metric_rows=metric_rows,
        items=items,
        strategy_results=strategy_results,
    )
    provisional_quality = measure_public_retrieval_artifact_quality(
        report_version=GRAPHRAG_LITE_RELATIONSHIP_INPUT_ONLY_REPORT_VERSION,
        run_id=run_id,
        result_rows=public_rows,
        report_text="",
    )
    report = GraphRagLiteRelationshipInputOnlyReport(
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
        update={
            "qualitative_assessment": build_graphrag_lite_input_only_qualitative_assessment(
                report,
            ),
        },
    )
    report_text = build_graphrag_lite_relationship_input_only_markdown(report)
    final_quality = measure_public_retrieval_artifact_quality(
        report_version=GRAPHRAG_LITE_RELATIONSHIP_INPUT_ONLY_REPORT_VERSION,
        run_id=run_id,
        result_rows=public_rows,
        report_text=report_text,
    )
    report = report.model_copy(update={"output_quality": final_quality})
    return report.model_copy(
        update={
            "qualitative_assessment": build_graphrag_lite_input_only_qualitative_assessment(
                report,
            ),
        },
    )


def build_graphrag_lite_metric_rows(
    *,
    items: list[RetrievalEvalItem],
    documents: list[RetrievalDocument],
    strategy_results: dict[str, list[RetrievalRunResult]],
    graph_pool_counts_by_strategy: dict[str, dict[str, int]] | None = None,
) -> tuple[GraphRagLiteMetricRow, ...]:
    if BASELINE_STRATEGY_ID not in strategy_results:
        raise ValueError("baseline strategy result is required")
    baseline_metric = compute_retrieval_metrics(
        items=items,
        results=strategy_results[BASELINE_STRATEGY_ID],
        method="hybrid_weighted",
    )
    rows: list[GraphRagLiteMetricRow] = []
    for strategy_id, results in strategy_results.items():
        role: GraphRagLiteRole = "baseline" if strategy_id == BASELINE_STRATEGY_ID else "candidate"
        metric = compute_retrieval_metrics(
            items=items,
            results=results,
            method="hybrid_weighted",
        )
        rows.append(
            _build_metric_row(
                strategy_id=strategy_id,
                role=role,
                metric=metric,
                baseline_metric=baseline_metric,
                documents=documents,
                results=results,
                graph_pool_counts=((graph_pool_counts_by_strategy or {}).get(strategy_id, {})),
            )
        )
    return tuple(rows)


def build_graphrag_lite_input_only_summary(
    *,
    metric_rows: tuple[GraphRagLiteMetricRow, ...],
    relationship_dev_query_count: int,
    expected_relationship_dev_query_count: int,
) -> GraphRagLiteInputOnlySummary:
    if not metric_rows:
        raise ValueError("GraphRAG-lite input-only report requires metric rows")
    candidate_rows = [row for row in metric_rows if row.role == "candidate"]
    best_row = max(
        metric_rows,
        key=lambda row: (row.ndcg_at_5, row.mrr, row.recall_at_5, -row.latency_p95_ms),
    )
    promoted_candidates = [
        row
        for row in candidate_rows
        if row.citation_recoverability >= MIN_CITATION_RECOVERABILITY
        and row.latency_p95_ms <= MAX_LATENCY_P95_MS
        and (
            row.recall_at_5_delta >= TARGET_RECALL_AT_5_DELTA
            or row.mrr_delta >= TARGET_MRR_DELTA
            or row.ndcg_at_5_delta >= TARGET_NDCG_AT_5_DELTA
        )
    ]
    decision: GraphRagLiteDecision = (
        "promote_graphrag_lite_next_gate" if promoted_candidates else "reject_graphrag_lite_default"
    )
    return GraphRagLiteInputOnlySummary(
        relationship_dev_query_count=relationship_dev_query_count,
        expected_relationship_dev_query_count=expected_relationship_dev_query_count,
        strategy_count=len(metric_rows),
        baseline_count=sum(1 for row in metric_rows if row.role == "baseline"),
        candidate_count=len(candidate_rows),
        best_strategy_id=best_row.strategy_id,
        baseline_strategy_id=BASELINE_STRATEGY_ID,
        promoted_candidate_count=len(promoted_candidates),
        solar_call_count=sum(row.solar_call_count for row in metric_rows),
        min_citation_recoverability=min(row.citation_recoverability for row in metric_rows),
        target_recall_at_5_delta=TARGET_RECALL_AT_5_DELTA,
        target_mrr_delta=TARGET_MRR_DELTA,
        target_ndcg_at_5_delta=TARGET_NDCG_AT_5_DELTA,
        max_latency_p95_ms=MAX_LATENCY_P95_MS,
        decision=decision,
    )


def build_public_graphrag_lite_input_only_rows(
    *,
    report: GraphRagLiteRelationshipInputOnlyReport,
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


def collect_graphrag_lite_relationship_input_only_failures(
    report: GraphRagLiteRelationshipInputOnlyReport,
) -> list[str]:
    failures: list[str] = []
    failures.extend(collect_public_retrieval_artifact_failures(report.output_quality))
    summary = report.summary
    if summary.decision == "blocked":
        failures.append("input_only_decision_blocked")
    if summary.relationship_dev_query_count != summary.expected_relationship_dev_query_count:
        failures.append("relationship_dev_query_count_mismatch")
    if summary.baseline_count != 1:
        failures.append("baseline_count_must_be_one")
    if summary.candidate_count < 2:
        failures.append("candidate_count_must_be_at_least_two")
    if summary.solar_call_count != 0:
        failures.append("solar_call_count_must_be_zero")
    if summary.min_citation_recoverability < MIN_CITATION_RECOVERABILITY:
        failures.append("citation_recoverability_below_gate")
    for row in report.metric_rows:
        if row.query_type != "relationship":
            failures.append("non_relationship_query_type_present")
        if row.result_count != row.query_count:
            failures.append(f"{row.strategy_id}_missing_results")
        if not row.source_citation_only:
            failures.append(f"{row.strategy_id}_non_source_citation_candidate")
    return failures


def build_graphrag_lite_relationship_input_only_markdown(
    report: GraphRagLiteRelationshipInputOnlyReport,
) -> str:
    summary = report.summary
    quality = report.output_quality
    metric_rows = "\n".join(_format_metric_row(row) for row in report.metric_rows)
    delta_rows = "\n".join(
        _format_delta_row(row) for row in report.metric_rows if row.role == "candidate"
    )
    qualitative_rows = "\n".join(
        f"- `{key}`: {value}" for key, value in report.qualitative_assessment.items()
    )
    conclusion = (
        "GraphRAG-lite relationship 후보는 dev input-only gate를 통과해 다음 locked gate "
        "검토 대상이다."
        if summary.decision == "promote_graphrag_lite_next_gate"
        else "GraphRAG-lite relationship 후보는 dev input-only 기준에서 기본 RAG pipeline으로 승격하지 않는다."
    )
    return f"""# GraphRAG-lite Relationship Input-only Report

## 결론

{conclusion}

이 결과는 source child chunk 후보를 재정렬한 검색 입력 비교다. Solar Pro 3 호출, 답변 생성 품질, production 성능 개선 주장이 아니다.

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
| decision | `{summary.decision}` |
| best_strategy_id | `{summary.best_strategy_id}` |

## 정량 리포트

| strategy_id | role | query_count | result_count | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | latency_p95_ms | citation_recoverability | graph_candidate_pool_count |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{metric_rows}

## Baseline Delta

| strategy_id | Recall@5 delta | MRR delta | nDCG@5 delta | latency_p95_ms delta |
| --- | ---: | ---: | ---: | ---: |
{delta_rows}

## Gate

| metric | value |
| --- | ---: |
| relationship_dev_query_count | {summary.relationship_dev_query_count} |
| expected_relationship_dev_query_count | {summary.expected_relationship_dev_query_count} |
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


def build_graphrag_lite_input_only_qualitative_assessment(
    report: GraphRagLiteRelationshipInputOnlyReport,
) -> dict[str, str]:
    failures = collect_graphrag_lite_relationship_input_only_failures(report)
    baseline = next(row for row in report.metric_rows if row.strategy_id == BASELINE_STRATEGY_ID)
    candidates = [row for row in report.metric_rows if row.role == "candidate"]
    best_candidate = max(
        candidates,
        key=lambda row: (row.ndcg_at_5, row.mrr, row.recall_at_5, -row.latency_p95_ms),
    )
    return {
        "scope": "relationship dev 10개에 한정한 input-only retrieval 후보 비교다.",
        "baseline": (
            f"{BASELINE_STRATEGY_ID} 기준 Recall@5={baseline.recall_at_5:.6f}, "
            f"MRR={baseline.mrr:.6f}, nDCG@5={baseline.ndcg_at_5:.6f}이다."
        ),
        "candidate_result": (
            f"최고 candidate는 {best_candidate.strategy_id}이며 "
            f"Recall@5 delta={best_candidate.recall_at_5_delta:.6f}, "
            f"MRR delta={best_candidate.mrr_delta:.6f}, "
            f"nDCG@5 delta={best_candidate.ndcg_at_5_delta:.6f}이다."
        ),
        "citation_boundary": "Graph/community hint는 citation이 아니며 최종 후보는 source child chunk id로만 남겼다.",
        "llm_boundary": "Solar Pro 3 호출은 0이다. 생성 품질 평가는 수행하지 않았다.",
        "data_boundary": "public rows는 query id, candidate id, rank, metric, sanitized failure tag만 포함한다.",
        "decision_boundary": "dev input-only 결과이므로 locked test 또는 production 개선으로 표현하지 않는다.",
        "external_audit": (
            "baseline Recall@5가 이미 높은 경우 GraphRAG-lite는 recall 개선보다 top-rank 품질과 "
            "관계형 실패 복구 여부로만 제한적으로 판단해야 한다."
        ),
        "gate_status": "PASS" if not failures else f"FAIL: {', '.join(failures)}",
    }


def build_graphrag_lite_relationship_input_only_run_id(
    *,
    items: list[RetrievalEvalItem],
    metric_rows: tuple[GraphRagLiteMetricRow, ...],
) -> str:
    payload = {
        "query_ids": [item.query.query_id for item in items],
        "metrics": [
            {
                "strategy_id": row.strategy_id,
                "recall_at_5": row.recall_at_5,
                "mrr": row.mrr,
                "ndcg_at_5": row.ndcg_at_5,
            }
            for row in metric_rows
        ],
    }
    digest = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"),
    ).hexdigest()[:8]
    return f"graphrag-lite-relationship-input-only-q{len(items)}-{digest}"


def _build_graphrag_lite_index(
    documents: list[RetrievalDocument],
) -> _GraphRagLiteIndex:
    documents_by_id = {document.retrieval_doc_id: document for document in documents}
    mutable_token_to_doc_ids: dict[str, set[str]] = defaultdict(set)
    tokens_by_doc_id: dict[str, frozenset[str]] = {}
    for document in documents:
        tokens = frozenset(_document_tokens(document))
        tokens_by_doc_id[document.retrieval_doc_id] = tokens
        for token in tokens:
            mutable_token_to_doc_ids[token].add(document.retrieval_doc_id)
    return _GraphRagLiteIndex(
        documents_by_id=documents_by_id,
        tokens_by_doc_id=tokens_by_doc_id,
        token_to_doc_ids={
            term_name: frozenset(doc_ids) for term_name, doc_ids in mutable_token_to_doc_ids.items()
        },
    )


def _build_graphrag_lite_candidate_results(
    *,
    strategy_id: str,
    items: list[RetrievalEvalItem],
    baseline_results: list[RetrievalRunResult],
    index: _GraphRagLiteIndex,
    top_k: int,
) -> _GraphRagLiteCandidateRun:
    baseline_by_query_id = {result.query_id: result for result in baseline_results}
    results: list[RetrievalRunResult] = []
    pool_counts_by_query_id: dict[str, int] = {}
    for item in items:
        baseline = baseline_by_query_id.get(item.query.query_id)
        if baseline is None:
            baseline = RetrievalRunResult(
                query_id=item.query.query_id,
                query_type=item.query.query_type,
                method="hybrid_weighted",
                candidates=[],
                latency_ms=0.0,
            )
        started = time.perf_counter()
        candidates, pool_count = _rank_graphrag_lite_candidates(
            strategy_id=strategy_id,
            item=item,
            baseline=baseline,
            index=index,
            top_k=top_k,
        )
        pool_counts_by_query_id[item.query.query_id] = pool_count
        latency_ms = baseline.latency_ms + round((time.perf_counter() - started) * 1000, 6)
        results.append(
            RetrievalRunResult(
                query_id=item.query.query_id,
                query_type=item.query.query_type,
                method="hybrid_weighted",
                candidates=candidates,
                latency_ms=round(latency_ms, 6),
            )
        )
    return _GraphRagLiteCandidateRun(
        results=results,
        pool_counts_by_query_id=pool_counts_by_query_id,
    )


def _rank_graphrag_lite_candidates(
    *,
    strategy_id: str,
    item: RetrievalEvalItem,
    baseline: RetrievalRunResult,
    index: _GraphRagLiteIndex,
    top_k: int,
) -> tuple[list[RetrievedCandidate], int]:
    query_tokens = _query_tokens(item)
    expanded_tokens = _expanded_query_tokens(query_tokens=query_tokens, index=index)
    candidate_doc_ids = _candidate_doc_ids_from_tokens(
        query_tokens=query_tokens,
        expanded_tokens=expanded_tokens,
        baseline=baseline,
        index=index,
    )
    baseline_scores = _normalized_baseline_scores(baseline)
    scored: list[tuple[float, str]] = []
    for doc_id in candidate_doc_ids:
        tokens = index.tokens_by_doc_id.get(doc_id, frozenset())
        direct_overlap = len(query_tokens & tokens)
        expanded_overlap = len(expanded_tokens & tokens)
        relation_overlap = len(_RELATION_HINT_TOKENS & tokens)
        pair_overlap = _pair_overlap_count(query_tokens=query_tokens, document_tokens=tokens)
        score = _graph_strategy_score(
            strategy_id=strategy_id,
            baseline_score=baseline_scores.get(doc_id, 0.0),
            direct_overlap=direct_overlap,
            expanded_overlap=expanded_overlap,
            relation_overlap=relation_overlap,
            pair_overlap=pair_overlap,
            query_token_count=len(query_tokens),
            expanded_token_count=len(expanded_tokens),
        )
        scored.append((score, doc_id))
    ranked_doc_ids = [
        doc_id
        for _score, doc_id in sorted(
            scored,
            key=lambda item_score: (item_score[0], item_score[1]),
            reverse=True,
        )[:top_k]
    ]
    candidates = [
        _candidate_from_document(
            rank=rank,
            document=index.documents_by_id[doc_id],
            score=next(score for score, scored_doc_id in scored if scored_doc_id == doc_id),
        )
        for rank, doc_id in enumerate(ranked_doc_ids, start=1)
    ]
    return candidates, len(candidate_doc_ids)


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
    index: _GraphRagLiteIndex,
) -> frozenset[str]:
    neighbor_counts: Counter[str] = Counter()
    for token in query_tokens:
        doc_ids = sorted(index.token_to_doc_ids.get(token, frozenset()))[:MAX_DIRECT_DOCS_PER_TERM]
        for doc_id in doc_ids:
            neighbor_counts.update(index.tokens_by_doc_id.get(doc_id, frozenset()))
    for token in query_tokens:
        neighbor_counts.pop(token, None)
    selected = [
        token
        for token, _count in neighbor_counts.most_common(MAX_EXPANDED_TOKEN_COUNT)
        if token not in _STOPWORDS
    ]
    return frozenset(set(selected) | set(query_tokens))


def _candidate_doc_ids_from_tokens(
    *,
    query_tokens: frozenset[str],
    expanded_tokens: frozenset[str],
    baseline: RetrievalRunResult,
    index: _GraphRagLiteIndex,
) -> frozenset[str]:
    candidate_ids = {candidate.retrieval_doc_id for candidate in baseline.candidates}
    token_scores: Counter[str] = Counter()
    for query_term in query_tokens:
        token_scores[query_term] += 3
    for expanded_term in expanded_tokens:
        if expanded_term not in query_tokens:
            token_scores[expanded_term] += 1
    doc_scores: Counter[str] = Counter()
    for token, token_weight in token_scores.items():
        doc_ids = sorted(index.token_to_doc_ids.get(token, frozenset()))[:MAX_DIRECT_DOCS_PER_TERM]
        for doc_id in doc_ids:
            doc_scores[doc_id] += token_weight
    for doc_id, _score in doc_scores.most_common(MAX_GRAPH_CANDIDATE_POOL_SIZE):
        candidate_ids.add(doc_id)
    return frozenset(doc_id for doc_id in candidate_ids if doc_id in index.documents_by_id)


def _graph_strategy_score(
    *,
    strategy_id: str,
    baseline_score: float,
    direct_overlap: int,
    expanded_overlap: int,
    relation_overlap: int,
    pair_overlap: int,
    query_token_count: int,
    expanded_token_count: int,
) -> float:
    direct_ratio = direct_overlap / max(query_token_count, 1)
    expanded_ratio = expanded_overlap / max(expanded_token_count, 1)
    max_pairs = max(len(list(combinations(range(query_token_count), 2))), 1)
    pair_ratio = pair_overlap / max_pairs
    relation_ratio = min(relation_overlap / 4, 1.0)
    if strategy_id == ENTITY_PATH_STRATEGY_ID:
        return round(
            0.52 * baseline_score + 0.24 * direct_ratio + 0.18 * pair_ratio + 0.06 * relation_ratio,
            9,
        )
    if strategy_id == COMMUNITY_HINT_STRATEGY_ID:
        return round(
            0.46 * baseline_score
            + 0.18 * direct_ratio
            + 0.26 * expanded_ratio
            + 0.10 * relation_ratio,
            9,
        )
    raise ValueError(f"unsupported GraphRAG-lite strategy: {strategy_id}")


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


def _pair_overlap_count(
    *,
    query_tokens: frozenset[str],
    document_tokens: frozenset[str],
) -> int:
    present = query_tokens & document_tokens
    if len(present) < 2:
        return 0
    return len(list(combinations(present, 2)))


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
                method="hybrid_weighted",
                candidates=candidates[:DEFAULT_TOP_K],
                latency_ms=latency,
            )
        )
    return results


def _build_metric_row(
    *,
    strategy_id: str,
    role: GraphRagLiteRole,
    metric: RetrievalMetricSummary,
    baseline_metric: RetrievalMetricSummary,
    documents: list[RetrievalDocument],
    results: list[RetrievalRunResult],
    graph_pool_counts: dict[str, int],
) -> GraphRagLiteMetricRow:
    recoverability = _citation_recoverability(
        documents=documents,
        results=results,
    )
    source_citation_only = recoverability >= 1.0
    return GraphRagLiteMetricRow(
        strategy_id=strategy_id,
        role=role,
        query_type="relationship",
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
        graph_candidate_pool_count=_mean_graph_pool_count(graph_pool_counts),
        source_citation_only=source_citation_only,
        solar_call_count=0,
        claim_boundary="dev_input_only",
    )


def _mean_graph_pool_count(graph_pool_counts: dict[str, int]) -> int:
    pool_counts = list(graph_pool_counts.values())
    if not pool_counts:
        return 0
    return int(round(sum(pool_counts) / len(pool_counts)))


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


def _relationship_dev_items(
    items: list[RetrievalEvalItem],
) -> list[RetrievalEvalItem]:
    return [
        item
        for item in items
        if item.query.query_type == "relationship" and item.metadata.split == "dev"
    ]


def _build_public_rows_for_quality(
    *,
    run_id: str,
    summary: GraphRagLiteInputOnlySummary,
    metric_rows: tuple[GraphRagLiteMetricRow, ...],
    items: list[RetrievalEvalItem],
    strategy_results: dict[str, list[RetrievalRunResult]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "row_type": "summary",
            "run_id": run_id,
            "relationship_dev_query_count": summary.relationship_dev_query_count,
            "expected_relationship_dev_query_count": (
                summary.expected_relationship_dev_query_count
            ),
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
    row: GraphRagLiteMetricRow,
) -> dict[str, Any]:
    return {
        "row_type": "metric",
        "run_id": run_id,
        "strategy_id": row.strategy_id,
        "role": row.role,
        "query_type": row.query_type,
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
        "graph_candidate_pool_count": row.graph_candidate_pool_count,
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
    raise ValueError(f"unknown query_id in GraphRAG-lite public row build: {query_id}")


def _with_blocked_decision(
    report: GraphRagLiteRelationshipInputOnlyReport,
) -> GraphRagLiteRelationshipInputOnlyReport:
    updated_summary = report.summary.model_copy(update={"decision": "blocked"})
    updated_report = report.model_copy(update={"summary": updated_summary})
    return updated_report.model_copy(
        update={
            "qualitative_assessment": build_graphrag_lite_input_only_qualitative_assessment(
                updated_report,
            ),
        }
    )


def _format_metric_row(row: GraphRagLiteMetricRow) -> str:
    return (
        f"| `{row.strategy_id}` | {row.role} | {row.query_count} | {row.result_count} | "
        f"{row.recall_at_1:.6f} | {row.recall_at_3:.6f} | "
        f"{row.recall_at_5:.6f} | {row.mrr:.6f} | {row.ndcg_at_5:.6f} | "
        f"{row.latency_p95_ms:.6f} | {row.citation_recoverability:.6f} | "
        f"{row.graph_candidate_pool_count} |"
    )


def _format_delta_row(row: GraphRagLiteMetricRow) -> str:
    return (
        f"| `{row.strategy_id}` | {row.recall_at_5_delta:.6f} | "
        f"{row.mrr_delta:.6f} | {row.ndcg_at_5_delta:.6f} | "
        f"{row.latency_p95_ms_delta:.6f} |"
    )


def main() -> int:
    args = _parse_args()
    report = run_graphrag_lite_relationship_input_only(
        chunks_path=args.chunks,
        dataset_path=args.dataset,
        baseline_rows_path=args.baseline_rows,
        result_rows_path=args.result_rows,
        report_path=args.report,
        force_recompute_baseline=args.recompute_baseline,
    )
    return 0 if not collect_graphrag_lite_relationship_input_only_failures(report) else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run GraphRAG-lite relationship input-only retrieval comparison.",
    )
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS_PATH)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--baseline-rows", type=Path, default=DEFAULT_BASELINE_ROWS_PATH)
    parser.add_argument("--result-rows", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument(
        "--recompute-baseline",
        action="store_true",
        help="Recompute the E5-small hybrid baseline instead of loading private rows.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
