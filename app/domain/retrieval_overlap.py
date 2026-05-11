from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.retrieval import QueryType, RetrievalEvalItem
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    public_path_alias,
)


RETRIEVAL_OVERLAP_REPORT_VERSION = "retrieval-overlap-analysis/v1"
OverlapHitGroup = Literal["both_hit", "bm25_only", "dense_only", "both_fail", "abstain"]
HybridDecision = Literal[
    "proceed_to_hybrid_rrf",
    "stop_d0_hybrid",
]


class RetrievalOverlapModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RetrievalOverlapQueryRow(RetrievalOverlapModel):
    query_id: str
    query_type: QueryType
    expected_behavior: str
    bm25_hit: bool
    dense_hit: bool
    oracle_union_hit: bool
    hit_group: OverlapHitGroup


class RetrievalOverlapMetricSummary(RetrievalOverlapModel):
    query_count: int = Field(ge=0)
    retrieve_query_count: int = Field(ge=0)
    abstain_query_count: int = Field(ge=0)
    bm25_only_hit_count: int = Field(ge=0)
    dense_only_hit_count: int = Field(ge=0)
    both_hit_count: int = Field(ge=0)
    both_fail_count: int = Field(ge=0)
    oracle_union_hit_count: int = Field(ge=0)
    bm25_recall_at_5: float = Field(ge=0.0, le=1.0)
    dense_recall_at_5: float = Field(ge=0.0, le=1.0)
    oracle_union_recall_at_5: float = Field(ge=0.0, le=1.0)
    oracle_union_delta_vs_bm25: float
    dense_only_share: float = Field(ge=0.0, le=1.0)
    bm25_abstain_with_candidate_count: int = Field(ge=0)
    dense_abstain_with_candidate_count: int = Field(ge=0)


class RetrievalOverlapQueryTypeSummary(RetrievalOverlapModel):
    query_type: QueryType
    query_count: int = Field(ge=0)
    retrieve_query_count: int = Field(ge=0)
    abstain_query_count: int = Field(ge=0)
    bm25_only_hit_count: int = Field(ge=0)
    dense_only_hit_count: int = Field(ge=0)
    both_hit_count: int = Field(ge=0)
    both_fail_count: int = Field(ge=0)
    oracle_union_hit_count: int = Field(ge=0)
    bm25_recall_at_5: float = Field(ge=0.0, le=1.0)
    dense_recall_at_5: float = Field(ge=0.0, le=1.0)
    oracle_union_recall_at_5: float = Field(ge=0.0, le=1.0)


class RetrievalOverlapReport(RetrievalOverlapModel):
    report_version: str = RETRIEVAL_OVERLAP_REPORT_VERSION
    analysis_id: str
    generated_at_utc: str
    dataset_path: str
    result_paths: list[str]
    methods: list[str]
    top_k: int = Field(ge=1)
    metric_summary: RetrievalOverlapMetricSummary
    query_type_breakdown: list[RetrievalOverlapQueryTypeSummary]
    hybrid_decision: HybridDecision
    qualitative_assessment: dict[str, str]
    output_quality: PublicRetrievalArtifactQuality


def build_retrieval_overlap_report(
    *,
    dataset_path: Path,
    result_paths: list[Path],
    items: list[RetrievalEvalItem],
    result_rows: list[dict[str, Any]],
    top_k: int = 5,
    output_quality: PublicRetrievalArtifactQuality,
) -> RetrievalOverlapReport:
    query_rows = build_overlap_query_rows(
        items=items,
        result_rows=result_rows,
        top_k=top_k,
    )
    metric_summary = build_overlap_metric_summary(
        items=items,
        result_rows=result_rows,
        query_rows=query_rows,
    )
    query_type_breakdown = build_overlap_query_type_breakdown(query_rows)
    decision = choose_hybrid_decision(metric_summary)
    analysis_id = build_overlap_analysis_id(
        items=items,
        result_rows=result_rows,
        top_k=top_k,
    )
    return RetrievalOverlapReport(
        analysis_id=analysis_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        dataset_path=public_path_alias(dataset_path),
        result_paths=[public_path_alias(path) for path in result_paths],
        methods=["bm25", "dense"],
        top_k=top_k,
        metric_summary=metric_summary,
        query_type_breakdown=query_type_breakdown,
        hybrid_decision=decision,
        qualitative_assessment=build_overlap_qualitative_assessment(
            metric_summary=metric_summary,
            hybrid_decision=decision,
        ),
        output_quality=output_quality,
    )


def build_overlap_query_rows(
    *,
    items: list[RetrievalEvalItem],
    result_rows: list[dict[str, Any]],
    top_k: int = 5,
) -> list[RetrievalOverlapQueryRow]:
    rows_by_method_query = _build_result_rows_by_method_query(result_rows)
    query_rows: list[RetrievalOverlapQueryRow] = []
    for item in items:
        bm25_hit = _query_has_relevant_candidate(
            item=item,
            rows=rows_by_method_query.get(("bm25", item.query.query_id), []),
            top_k=top_k,
        )
        dense_hit = _query_has_relevant_candidate(
            item=item,
            rows=rows_by_method_query.get(("dense", item.query.query_id), []),
            top_k=top_k,
        )
        hit_group = _build_hit_group(
            expected_behavior=item.query.expected_behavior,
            bm25_hit=bm25_hit,
            dense_hit=dense_hit,
        )
        query_rows.append(
            RetrievalOverlapQueryRow(
                query_id=item.query.query_id,
                query_type=item.query.query_type,
                expected_behavior=item.query.expected_behavior,
                bm25_hit=bm25_hit,
                dense_hit=dense_hit,
                oracle_union_hit=bm25_hit or dense_hit,
                hit_group=hit_group,
            )
        )
    return query_rows


def build_overlap_metric_summary(
    *,
    items: list[RetrievalEvalItem],
    result_rows: list[dict[str, Any]],
    query_rows: list[RetrievalOverlapQueryRow],
) -> RetrievalOverlapMetricSummary:
    retrieve_rows = [
        row for row in query_rows if row.expected_behavior == "retrieve"
    ]
    abstain_items = [
        item for item in items if item.query.expected_behavior == "abstain"
    ]
    rows_by_method_query = _build_result_rows_by_method_query(result_rows)
    retrieve_count = len(retrieve_rows)
    bm25_hit_count = sum(1 for row in retrieve_rows if row.bm25_hit)
    dense_hit_count = sum(1 for row in retrieve_rows if row.dense_hit)
    oracle_union_hit_count = sum(1 for row in retrieve_rows if row.oracle_union_hit)
    bm25_recall_at_5 = _safe_ratio(bm25_hit_count, retrieve_count)
    dense_recall_at_5 = _safe_ratio(dense_hit_count, retrieve_count)
    oracle_union_recall_at_5 = _safe_ratio(oracle_union_hit_count, retrieve_count)
    dense_only_hit_count = _count_hit_group(retrieve_rows, "dense_only")
    return RetrievalOverlapMetricSummary(
        query_count=len(query_rows),
        retrieve_query_count=retrieve_count,
        abstain_query_count=len(abstain_items),
        bm25_only_hit_count=_count_hit_group(retrieve_rows, "bm25_only"),
        dense_only_hit_count=dense_only_hit_count,
        both_hit_count=_count_hit_group(retrieve_rows, "both_hit"),
        both_fail_count=_count_hit_group(retrieve_rows, "both_fail"),
        oracle_union_hit_count=oracle_union_hit_count,
        bm25_recall_at_5=bm25_recall_at_5,
        dense_recall_at_5=dense_recall_at_5,
        oracle_union_recall_at_5=oracle_union_recall_at_5,
        oracle_union_delta_vs_bm25=round(
            oracle_union_recall_at_5 - bm25_recall_at_5,
            6,
        ),
        dense_only_share=_safe_ratio(dense_only_hit_count, retrieve_count),
        bm25_abstain_with_candidate_count=_count_abstain_with_candidates(
            abstain_items,
            rows_by_method_query,
            "bm25",
        ),
        dense_abstain_with_candidate_count=_count_abstain_with_candidates(
            abstain_items,
            rows_by_method_query,
            "dense",
        ),
    )


def build_overlap_query_type_breakdown(
    query_rows: list[RetrievalOverlapQueryRow],
) -> list[RetrievalOverlapQueryTypeSummary]:
    query_types = sorted({row.query_type for row in query_rows})
    breakdown: list[RetrievalOverlapQueryTypeSummary] = []
    for query_type in query_types:
        rows = [row for row in query_rows if row.query_type == query_type]
        retrieve_rows = [row for row in rows if row.expected_behavior == "retrieve"]
        retrieve_count = len(retrieve_rows)
        bm25_hit_count = sum(1 for row in retrieve_rows if row.bm25_hit)
        dense_hit_count = sum(1 for row in retrieve_rows if row.dense_hit)
        oracle_union_hit_count = sum(
            1 for row in retrieve_rows if row.oracle_union_hit
        )
        breakdown.append(
            RetrievalOverlapQueryTypeSummary(
                query_type=query_type,
                query_count=len(rows),
                retrieve_query_count=retrieve_count,
                abstain_query_count=sum(
                    1 for row in rows if row.expected_behavior == "abstain"
                ),
                bm25_only_hit_count=_count_hit_group(retrieve_rows, "bm25_only"),
                dense_only_hit_count=_count_hit_group(retrieve_rows, "dense_only"),
                both_hit_count=_count_hit_group(retrieve_rows, "both_hit"),
                both_fail_count=_count_hit_group(retrieve_rows, "both_fail"),
                oracle_union_hit_count=oracle_union_hit_count,
                bm25_recall_at_5=_safe_ratio(bm25_hit_count, retrieve_count),
                dense_recall_at_5=_safe_ratio(dense_hit_count, retrieve_count),
                oracle_union_recall_at_5=_safe_ratio(
                    oracle_union_hit_count,
                    retrieve_count,
                ),
            )
        )
    return breakdown


def build_public_overlap_result_rows(
    *,
    analysis_id: str,
    query_rows: list[RetrievalOverlapQueryRow],
) -> list[dict[str, object]]:
    return [
        {
            "analysis_id": analysis_id,
            "query_id": row.query_id,
            "query_type": row.query_type,
            "expected_behavior": row.expected_behavior,
            "bm25_hit": row.bm25_hit,
            "dense_hit": row.dense_hit,
            "oracle_union_hit": row.oracle_union_hit,
            "hit_group": row.hit_group,
        }
        for row in query_rows
    ]


def build_retrieval_overlap_report_markdown(
    report: RetrievalOverlapReport,
) -> str:
    metric = report.metric_summary
    query_type_rows = "\n".join(
        _format_query_type_row(row) for row in report.query_type_breakdown
    )
    result_paths = ", ".join(report.result_paths)
    qualitative_rows = "\n".join(
        f"- `{key}`: {value}"
        for key, value in report.qualitative_assessment.items()
    )
    quality = report.output_quality
    return f"""# Retrieval Overlap Analysis Report

## 목적

BM25와 Dense D0가 서로 보완되는지 확인한다.

이 문서는 Hybrid 성능 개선 주장이 아니다. 실제 Hybrid RRF/Weighted 실험 전에 oracle union 상한과 query type별 보완 가능성을 검증하는 중간 리포트다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| analysis_id | `{report.analysis_id}` |
| generated_at_utc | `{report.generated_at_utc}` |
| methods | `{", ".join(report.methods)}` |
| top_k | {report.top_k} |
| dataset_path | `{report.dataset_path}` |
| result_paths | `{result_paths}` |
| hybrid_decision | `{report.hybrid_decision}` |

## 정량 리포트

| metric | value |
| --- | ---: |
| query_count | {metric.query_count} |
| retrieve_query_count | {metric.retrieve_query_count} |
| abstain_query_count | {metric.abstain_query_count} |
| bm25_only_hit_count | {metric.bm25_only_hit_count} |
| dense_only_hit_count | {metric.dense_only_hit_count} |
| both_hit_count | {metric.both_hit_count} |
| both_fail_count | {metric.both_fail_count} |
| oracle_union_hit_count | {metric.oracle_union_hit_count} |
| bm25_recall_at_5 | {metric.bm25_recall_at_5:.6f} |
| dense_recall_at_5 | {metric.dense_recall_at_5:.6f} |
| oracle_union_recall_at_5 | {metric.oracle_union_recall_at_5:.6f} |
| oracle_union_delta_vs_bm25 | {metric.oracle_union_delta_vs_bm25:.6f} |
| dense_only_share | {metric.dense_only_share:.6f} |
| bm25_abstain_with_candidate_count | {metric.bm25_abstain_with_candidate_count} |
| dense_abstain_with_candidate_count | {metric.dense_abstain_with_candidate_count} |

## Query Type Breakdown

| query_type | query_count | retrieve_query_count | abstain_query_count | bm25_only_hit_count | dense_only_hit_count | both_hit_count | both_fail_count | oracle_union_hit_count | bm25_recall_at_5 | dense_recall_at_5 | oracle_union_recall_at_5 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
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

oracle union은 실제 Hybrid 결과가 아니라 BM25와 Dense D0가 동시에 제공할 수 있는 검색 상한이다.

Hybrid 구현 여부는 이 리포트의 보완성 수치로 판단하되, 최종 성능 개선 주장은 별도 Hybrid 실행 결과와 locked test 확인 전까지 금지한다.
"""


def choose_hybrid_decision(
    metric_summary: RetrievalOverlapMetricSummary,
) -> HybridDecision:
    if metric_summary.dense_only_hit_count > 0 and metric_summary.oracle_union_delta_vs_bm25 > 0:
        return "proceed_to_hybrid_rrf"
    return "stop_d0_hybrid"


def build_overlap_qualitative_assessment(
    *,
    metric_summary: RetrievalOverlapMetricSummary,
    hybrid_decision: HybridDecision,
) -> dict[str, str]:
    if hybrid_decision == "proceed_to_hybrid_rrf":
        decision_text = (
            "Dense D0가 BM25 실패 query 일부를 보완했다. "
            "Hybrid RRF/Weighted 실험을 진행할 근거는 있으나 개선 주장은 아직 불가하다."
        )
    else:
        decision_text = (
            "Dense D0의 BM25 보완성이 부족하다. "
            "D0 기반 Hybrid보다 neural embedding 비교가 우선이다."
        )
    return {
        "analysis_scope": "private dev split의 BM25와 Dense D0 top-k 후보 ID만 비교했다.",
        "oracle_union_boundary": (
            "oracle union은 두 method 중 하나라도 정답을 포함했는지 보는 상한이며 실제 retriever가 아니다."
        ),
        "dense_boundary": (
            "Dense D0는 sklearn-tfidf-svd-v1이며 BGE-M3 또는 multilingual-E5 같은 neural embedding 결과가 아니다."
        ),
        "hybrid_decision": decision_text,
        "no_answer_policy": (
            f"no-answer query candidate count는 BM25 {metric_summary.bm25_abstain_with_candidate_count}, "
            f"Dense {metric_summary.dense_abstain_with_candidate_count}로 기록했다."
        ),
        "public_policy": "public report에는 query text, chunk text, raw result body를 저장하지 않는다.",
    }


def build_overlap_analysis_id(
    *,
    items: list[RetrievalEvalItem],
    result_rows: list[dict[str, Any]],
    top_k: int,
) -> str:
    payload = {
        "top_k": top_k,
        "query_ids": [item.query.query_id for item in items],
        "result_fingerprint": _stable_digest(_public_result_row_fingerprint(result_rows)),
    }
    return f"retrieval-overlap-q{len(items)}-{_stable_digest(payload)[:8]}"


def _build_result_rows_by_method_query(
    result_rows: list[dict[str, Any]],
) -> dict[tuple[str, str], list[dict[str, Any]]]:
    rows_by_method_query: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in result_rows:
        method = str(row.get("method", ""))
        query_id = str(row.get("query_id", ""))
        rows_by_method_query.setdefault((method, query_id), []).append(row)
    return rows_by_method_query


def _query_has_relevant_candidate(
    *,
    item: RetrievalEvalItem,
    rows: list[dict[str, Any]],
    top_k: int,
) -> bool:
    if item.query.expected_behavior != "retrieve":
        return False
    relevant_targets = _primary_relevance_targets(item)
    if not relevant_targets:
        return False
    for row in rows:
        rank = row.get("rank")
        if not isinstance(rank, int) or rank > top_k:
            continue
        identifiers = {
            str(row.get("child_id") or ""),
            str(row.get("parent_id") or ""),
            str(row.get("doc_id") or ""),
        }
        if identifiers & relevant_targets:
            return True
    return False


def _primary_relevance_targets(item: RetrievalEvalItem) -> set[str]:
    targets: set[str] = set()
    for judgment in item.judgments:
        if judgment.relevant_child_ids:
            targets.update(judgment.relevant_child_ids)
        elif judgment.relevant_parent_ids:
            targets.update(judgment.relevant_parent_ids)
        else:
            targets.update(judgment.relevant_doc_ids)
    return targets


def _build_hit_group(
    *,
    expected_behavior: str,
    bm25_hit: bool,
    dense_hit: bool,
) -> OverlapHitGroup:
    if expected_behavior == "abstain":
        return "abstain"
    if bm25_hit and dense_hit:
        return "both_hit"
    if bm25_hit:
        return "bm25_only"
    if dense_hit:
        return "dense_only"
    return "both_fail"


def _count_hit_group(
    rows: list[RetrievalOverlapQueryRow],
    group: OverlapHitGroup,
) -> int:
    return sum(1 for row in rows if row.hit_group == group)


def _count_abstain_with_candidates(
    abstain_items: list[RetrievalEvalItem],
    rows_by_method_query: dict[tuple[str, str], list[dict[str, Any]]],
    method: str,
) -> int:
    count = 0
    for item in abstain_items:
        rows = rows_by_method_query.get((method, item.query.query_id), [])
        if any(isinstance(row.get("rank"), int) for row in rows):
            count += 1
    return count


def _format_query_type_row(row: RetrievalOverlapQueryTypeSummary) -> str:
    return (
        f"| {row.query_type} | {row.query_count} | {row.retrieve_query_count} | "
        f"{row.abstain_query_count} | {row.bm25_only_hit_count} | "
        f"{row.dense_only_hit_count} | {row.both_hit_count} | "
        f"{row.both_fail_count} | {row.oracle_union_hit_count} | "
        f"{row.bm25_recall_at_5:.6f} | {row.dense_recall_at_5:.6f} | "
        f"{row.oracle_union_recall_at_5:.6f} |"
    )


def _public_result_row_fingerprint(
    result_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    fields = ("method", "query_id", "query_type", "rank", "child_id", "parent_id", "doc_id")
    return [
        {field: row.get(field) for field in fields}
        for row in sorted(
            result_rows,
            key=lambda row: (
                str(row.get("method", "")),
                str(row.get("query_id", "")),
                int(row.get("rank") or 9999),
            ),
        )
    ]


def _safe_ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 6)


def _stable_digest(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]
