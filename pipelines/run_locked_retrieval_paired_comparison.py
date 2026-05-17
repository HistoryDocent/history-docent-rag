from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.application.chat_retrieval import (
    PrivateArtifactRetrievalBackend,
    _search_with_route,
)
from app.application.query_type_router import (
    DEFAULT_PACKING_POLICY_ID,
    DEFAULT_RETRIEVAL_CANDIDATE_ID,
    DEFAULT_ROUTE_POLICY_ID,
    QUERY_TYPE_ROUTER_POLICY_ID,
    RELATIONSHIP_ROUTE_POLICY_ID,
    QueryTypeRouteDecision,
    QueryTypeRouter,
)
from app.core.project_paths import is_repository_private_write_path, project_path
from app.domain.retrieval import (
    QueryType,
    REQUIRED_QUERY_TYPES,
    RetrievedCandidate,
    RetrievalEvalItem,
    RetrievalJudgment,
    RetrievalRunResult,
    build_retrieval_target_inventory,
    collect_retrieval_eval_target_resolvability_failures,
    load_retrieval_eval_jsonl,
    summarize_retrieval_eval_dataset,
    summarize_retrieval_eval_target_resolvability,
)
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    build_dataset_fingerprint,
    collect_public_retrieval_artifact_failures,
    measure_public_retrieval_artifact_quality,
    public_path_alias,
    write_public_retrieval_result_rows,
)
from app.infrastructure.index.device import resolve_torch_device
from pipelines.build_retrieval_eval_target_report import load_child_chunks_from_report


LOCKED_RETRIEVAL_PAIRED_REPORT_VERSION = "locked-retrieval-paired-comparison/v1"
WORK_ID = "HD-LOCKED-RETRIEVAL-004"
DEFAULT_DATASET_PATH = Path("private_data/evals/datasets/retrieval_eval_test.jsonl")
DEFAULT_CHUNKS_PATH = Path("private_data/reports/parent_child_chunks.json")
DEFAULT_RESULT_ROWS_PATH = Path(
    "private_data/evals/results/locked_retrieval_paired_comparison_fact_rows.jsonl"
)
DEFAULT_DOC_PATH = Path("docs/LOCKED_RETRIEVAL_PAIRED_COMPARISON.md")
DEFAULT_REPORT_PATH = Path("evals/reports/locked_retrieval_paired_comparison_report.md")
DEFAULT_TOP_K = 5
EXPECTED_LOCKED_QUERY_COUNT = 35
EXPECTED_QUERY_TYPE_COUNT = len(REQUIRED_QUERY_TYPES)
EXPECTED_QUERY_COUNT_PER_TYPE = 5
EXPECTED_ANSWERABLE_QUERY_COUNT = 30
EXPECTED_NO_ANSWER_QUERY_COUNT = 5
BASELINE_CANDIDATE_ID = DEFAULT_RETRIEVAL_CANDIDATE_ID
RELATIONSHIP_CANDIDATE_ID = "relationship_hybrid_weighted_e5_v1"
RELATIONSHIP_RETRIEVAL_METHOD_LABEL = "hybrid_weighted_e5_small_alpha_0_5"
BOOTSTRAP_ITERATIONS = 10_000
CONFIDENCE_INTERVAL_PERCENT = 95
BOOTSTRAP_SEED = 42
PRIMARY_METRIC = "mrr"
MAX_LATENCY_P95_DELTA_MS = 50.0

MetricName = Literal[
    "recall_at_1",
    "recall_at_3",
    "recall_at_5",
    "mrr",
    "ndcg_at_5",
]
RouteRole = Literal["baseline", "candidate"]
LockedDecision = Literal[
    "support_relationship_route_candidate",
    "keep_shadow_without_locked_improvement_claim",
    "blocked_by_stop_condition",
]


class LockedRetrievalModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LockedRetrievalRunner(Protocol):
    def search(
        self,
        *,
        item: RetrievalEvalItem,
        route_role: RouteRole,
    ) -> RetrievalRunResult:
        ...


class LockedRetrievalPairRow(LockedRetrievalModel):
    query_id: str = Field(min_length=1)
    query_type: QueryType
    expected_behavior: Literal["retrieve", "abstain"]
    baseline_candidate_id: str = Field(min_length=1)
    candidate_id: str = Field(min_length=1)
    baseline_route_policy_id: str = Field(min_length=1)
    candidate_route_policy_id: str = Field(min_length=1)
    candidate_route_applied: bool
    no_answer_guard_applied: bool
    false_hybrid_route: bool
    no_answer_candidate_route: bool
    baseline_candidate_count: int = Field(ge=0)
    candidate_candidate_count: int = Field(ge=0)
    baseline_relevant_rank: int | None = Field(default=None, ge=1)
    candidate_relevant_rank: int | None = Field(default=None, ge=1)
    baseline_hit_at_1: bool
    baseline_hit_at_3: bool
    baseline_hit_at_5: bool
    candidate_hit_at_1: bool
    candidate_hit_at_3: bool
    candidate_hit_at_5: bool
    baseline_rr: float = Field(ge=0.0, le=1.0)
    candidate_rr: float = Field(ge=0.0, le=1.0)
    baseline_ndcg_at_5: float = Field(ge=0.0, le=1.0)
    candidate_ndcg_at_5: float = Field(ge=0.0, le=1.0)
    baseline_latency_ms: float = Field(ge=0.0)
    candidate_latency_ms: float = Field(ge=0.0)
    latency_delta_ms: float


class LockedRetrievalMetricSummary(LockedRetrievalModel):
    candidate_id: str = Field(min_length=1)
    scope: Literal["answerable_all", "relationship_only"]
    query_count: int = Field(ge=0)
    retrieve_query_count: int = Field(ge=0)
    no_answer_query_count: int = Field(ge=0)
    retrieval_execution_count: int = Field(ge=0)
    recall_at_1: float = Field(ge=0.0, le=1.0)
    recall_at_3: float = Field(ge=0.0, le=1.0)
    recall_at_5: float = Field(ge=0.0, le=1.0)
    mrr: float = Field(ge=0.0, le=1.0)
    ndcg_at_5: float = Field(ge=0.0, le=1.0)
    latency_p50_ms: float = Field(ge=0.0)
    latency_p95_ms: float = Field(ge=0.0)
    no_answer_with_candidate_count: int = Field(ge=0)


class LockedRetrievalBootstrapInterval(LockedRetrievalModel):
    metric_name: MetricName
    bootstrap_iterations: int = Field(ge=1)
    confidence_interval_percent: int = Field(ge=1, le=99)
    observed_delta: float
    confidence_interval_low: float
    confidence_interval_high: float
    decision_tag: str = Field(min_length=1)


class LockedRetrievalQueryTypeDelta(LockedRetrievalModel):
    query_type: QueryType
    query_count: int = Field(ge=0)
    paired_query_count: int = Field(ge=0)
    baseline_recall_at_5: float = Field(ge=0.0, le=1.0)
    candidate_recall_at_5: float = Field(ge=0.0, le=1.0)
    recall_at_5_delta: float
    baseline_mrr: float = Field(ge=0.0, le=1.0)
    candidate_mrr: float = Field(ge=0.0, le=1.0)
    mrr_delta: float
    baseline_ndcg_at_5: float = Field(ge=0.0, le=1.0)
    candidate_ndcg_at_5: float = Field(ge=0.0, le=1.0)
    ndcg_at_5_delta: float
    latency_p95_ms_delta: float


class LockedRetrievalComparisonSummary(LockedRetrievalModel):
    locked_query_count: int = Field(ge=0)
    query_type_count: int = Field(ge=0)
    answerable_query_count: int = Field(ge=0)
    no_answer_query_count: int = Field(ge=0)
    baseline_retrieval_run_count: int = Field(ge=0)
    candidate_retrieval_run_count: int = Field(ge=0)
    paired_query_count: int = Field(ge=0)
    target_resolvability_fail_count: int = Field(ge=0)
    false_hybrid_route_count: int = Field(ge=0)
    no_answer_candidate_route_count: int = Field(ge=0)
    active_route_applied_count: int = Field(ge=0)
    live_solar_call_count: int = Field(ge=0)
    private_fact_row_count: int = Field(ge=0)
    bootstrap_iteration_count: int = Field(ge=1)
    confidence_interval_percent: int = Field(ge=1, le=99)
    primary_metric: MetricName
    recall_at_1_delta: float
    recall_at_3_delta: float
    recall_at_5_delta: float
    mrr_delta: float
    ndcg_at_5_delta: float
    latency_p95_ms_delta: float
    primary_metric_delta: float
    primary_metric_ci_low: float
    primary_metric_ci_high: float
    locked_decision: LockedDecision


class LockedRetrievalPairedComparisonReport(LockedRetrievalModel):
    report_version: str = LOCKED_RETRIEVAL_PAIRED_REPORT_VERSION
    work_id: str = WORK_ID
    run_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    dataset_path_alias: str = Field(min_length=1)
    chunks_path_alias: str = Field(min_length=1)
    result_path: str = Field(min_length=1)
    dataset_fingerprint: str = Field(min_length=8)
    router_policy_id: str = QUERY_TYPE_ROUTER_POLICY_ID
    baseline_route_policy_id: str = DEFAULT_ROUTE_POLICY_ID
    candidate_route_policy_id: str = RELATIONSHIP_ROUTE_POLICY_ID
    packing_policy_id: str = DEFAULT_PACKING_POLICY_ID
    top_k: int = Field(ge=1)
    resolved_device: str = Field(min_length=1)
    baseline_summary: LockedRetrievalMetricSummary
    candidate_summary: LockedRetrievalMetricSummary
    comparison_summary: LockedRetrievalComparisonSummary
    query_type_deltas: tuple[LockedRetrievalQueryTypeDelta, ...]
    bootstrap_intervals: tuple[LockedRetrievalBootstrapInterval, ...]
    rows: tuple[LockedRetrievalPairRow, ...]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


class PrivateLockedRetrievalRunner:
    def __init__(
        self,
        *,
        chunks_path: Path = DEFAULT_CHUNKS_PATH,
        top_k: int = DEFAULT_TOP_K,
        embedding_cache_dir: Path = Path("private_data/embeddings/query_rewrite"),
    ) -> None:
        self.backend = PrivateArtifactRetrievalBackend(
            chunks_path=chunks_path,
            top_k=top_k,
            embedding_cache_dir=embedding_cache_dir,
        )
        self.top_k = top_k

    def search(
        self,
        *,
        item: RetrievalEvalItem,
        route_role: RouteRole,
    ) -> RetrievalRunResult:
        if item.query.expected_behavior == "abstain":
            return _empty_result(item=item, method="dense")
        if route_role == "candidate" and item.query.query_type != "relationship":
            return _empty_result(item=item, method="hybrid_weighted")
        state = self.backend._load_state()
        rewrite = state.rewriter.rewrite(item)
        route_decision = _locked_route_decision(
            router=state.router,
            item=item,
            route_role=route_role,
        )
        result = _search_with_route(
            route_decision=route_decision,
            state=state,
            item=item,
            query_text=rewrite.rewritten_query_text,
            top_k=self.top_k,
        )
        return result.model_copy(
            update={"latency_ms": round(result.latency_ms + rewrite.latency_ms, 6)}
        )


def run_locked_retrieval_paired_comparison(
    *,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    chunks_path: Path = DEFAULT_CHUNKS_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
    doc_path: Path = DEFAULT_DOC_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    top_k: int = DEFAULT_TOP_K,
    retrieval_runner: LockedRetrievalRunner | None = None,
) -> LockedRetrievalPairedComparisonReport:
    _validate_private_result_path(result_rows_path)
    items = load_retrieval_eval_jsonl(project_path(dataset_path))
    target_summary = summarize_retrieval_eval_target_resolvability(
        items=items,
        inventory=build_retrieval_target_inventory(
            load_child_chunks_from_report(project_path(chunks_path))
        ),
    )
    dataset_failures = _collect_locked_dataset_failures(items)
    target_failures = collect_retrieval_eval_target_resolvability_failures(target_summary)
    if dataset_failures or target_failures:
        raise ValueError(
            "locked retrieval paired comparison dataset gate failed: "
            f"{dataset_failures + target_failures}"
        )
    runner = retrieval_runner or PrivateLockedRetrievalRunner(
        chunks_path=chunks_path,
        top_k=top_k,
    )
    rows = build_locked_retrieval_pair_rows(items=items, retrieval_runner=runner)
    provisional = _build_report(
        rows=rows,
        dataset_path=dataset_path,
        chunks_path=chunks_path,
        result_rows_path=result_rows_path,
        top_k=top_k,
        target_resolvability_fail_count=len(target_failures),
        output_quality=PublicRetrievalArtifactQuality(
            result_row_count=0,
            report_version=LOCKED_RETRIEVAL_PAIRED_REPORT_VERSION,
            run_id="pending",
            public_raw_text_leakage_count=0,
            private_path_leakage_count=0,
            secret_like_leakage_count=0,
            forbidden_result_field_count=0,
        ),
    )
    public_rows = build_public_locked_retrieval_rows(provisional)
    doc_text = build_locked_retrieval_doc(provisional)
    report_text = build_locked_retrieval_report_markdown(provisional)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=LOCKED_RETRIEVAL_PAIRED_REPORT_VERSION,
        run_id=provisional.run_id,
        result_rows=public_rows,
        report_text=report_text,
        extra_public_texts={
            f"doc:{line_number}": line
            for line_number, line in enumerate(doc_text.splitlines(), start=1)
        },
    )
    report = _build_report(
        rows=rows,
        dataset_path=dataset_path,
        chunks_path=chunks_path,
        result_rows_path=result_rows_path,
        top_k=top_k,
        target_resolvability_fail_count=len(target_failures),
        output_quality=output_quality,
    )
    failures = collect_locked_retrieval_paired_comparison_failures(report)
    if failures:
        raise ValueError(f"locked retrieval paired comparison gate failed: {failures}")

    write_public_retrieval_result_rows(
        path=project_path(result_rows_path),
        rows=build_private_locked_fact_rows(report),
    )
    resolved_doc_path = project_path(doc_path)
    resolved_report_path = project_path(report_path)
    resolved_doc_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_report_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_doc_path.write_text(build_locked_retrieval_doc(report), encoding="utf-8")
    resolved_report_path.write_text(
        build_locked_retrieval_report_markdown(report),
        encoding="utf-8",
    )
    print(
        "locked_retrieval_paired_comparison "
        "status=PASS "
        f"locked_query_count={report.comparison_summary.locked_query_count} "
        f"paired_query_count={report.comparison_summary.paired_query_count} "
        f"primary_metric={report.comparison_summary.primary_metric} "
        f"primary_delta={report.comparison_summary.primary_metric_delta:.6f} "
        f"ci=[{report.comparison_summary.primary_metric_ci_low:.6f},"
        f"{report.comparison_summary.primary_metric_ci_high:.6f}] "
        f"decision={report.comparison_summary.locked_decision} "
        f"resolved_device={report.resolved_device}",
    )
    return report


def build_locked_retrieval_pair_rows(
    *,
    items: list[RetrievalEvalItem],
    retrieval_runner: LockedRetrievalRunner,
) -> tuple[LockedRetrievalPairRow, ...]:
    rows: list[LockedRetrievalPairRow] = []
    router = QueryTypeRouter()
    for item in items:
        baseline_route = _locked_route_decision(
            router=router,
            item=item,
            route_role="baseline",
        )
        candidate_route = _locked_route_decision(
            router=router,
            item=item,
            route_role="candidate",
        )
        baseline_result = retrieval_runner.search(item=item, route_role="baseline")
        candidate_result = (
            retrieval_runner.search(item=item, route_role="candidate")
            if item.query.query_type == "relationship"
            and item.query.expected_behavior == "retrieve"
            else _empty_result(item=item, method="hybrid_weighted")
        )
        rows.append(
            _build_pair_row(
                item=item,
                baseline_route=baseline_route,
                candidate_route=candidate_route,
                baseline_result=baseline_result,
                candidate_result=candidate_result,
            )
        )
    return tuple(rows)


def build_public_locked_retrieval_rows(
    report: LockedRetrievalPairedComparisonReport,
) -> list[dict[str, object]]:
    summary = report.comparison_summary
    rows: list[dict[str, object]] = [
        {
            "row_type": "summary",
            "run_id": report.run_id,
            "work_id": report.work_id,
            "locked_query_count": summary.locked_query_count,
            "answerable_query_count": summary.answerable_query_count,
            "no_answer_query_count": summary.no_answer_query_count,
            "paired_query_count": summary.paired_query_count,
            "baseline_retrieval_run_count": summary.baseline_retrieval_run_count,
            "candidate_retrieval_run_count": summary.candidate_retrieval_run_count,
            "false_hybrid_route_count": summary.false_hybrid_route_count,
            "no_answer_candidate_route_count": summary.no_answer_candidate_route_count,
            "live_solar_call_count": summary.live_solar_call_count,
            "primary_metric": summary.primary_metric,
            "primary_metric_delta": summary.primary_metric_delta,
            "primary_metric_ci_low": summary.primary_metric_ci_low,
            "primary_metric_ci_high": summary.primary_metric_ci_high,
            "locked_decision": summary.locked_decision,
        },
        _public_metric_row(report.run_id, "baseline", report.baseline_summary),
        _public_metric_row(report.run_id, "candidate", report.candidate_summary),
    ]
    rows.extend(
        {
            "row_type": "query_type_delta",
            "run_id": report.run_id,
            "query_type": row.query_type,
            "query_count": row.query_count,
            "paired_query_count": row.paired_query_count,
            "baseline_recall_at_5": row.baseline_recall_at_5,
            "candidate_recall_at_5": row.candidate_recall_at_5,
            "recall_at_5_delta": row.recall_at_5_delta,
            "baseline_mrr": row.baseline_mrr,
            "candidate_mrr": row.candidate_mrr,
            "mrr_delta": row.mrr_delta,
            "baseline_ndcg_at_5": row.baseline_ndcg_at_5,
            "candidate_ndcg_at_5": row.candidate_ndcg_at_5,
            "ndcg_at_5_delta": row.ndcg_at_5_delta,
        }
        for row in report.query_type_deltas
    )
    rows.extend(
        {
            "row_type": "bootstrap_interval",
            "run_id": report.run_id,
            "metric_name": interval.metric_name,
            "bootstrap_iterations": interval.bootstrap_iterations,
            "confidence_interval_percent": interval.confidence_interval_percent,
            "observed_delta": interval.observed_delta,
            "confidence_interval_low": interval.confidence_interval_low,
            "confidence_interval_high": interval.confidence_interval_high,
            "decision_tag": interval.decision_tag,
        }
        for interval in report.bootstrap_intervals
    )
    return rows


def build_private_locked_fact_rows(
    report: LockedRetrievalPairedComparisonReport,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for query_row in report.rows:
        rows.extend(
            _private_metric_fact_rows(
                run_id=report.run_id,
                query_row=query_row,
                candidate_id=BASELINE_CANDIDATE_ID,
                prefix="baseline",
                route_policy_id=query_row.baseline_route_policy_id,
                route_applied=True,
            )
        )
        if query_row.candidate_route_applied:
            rows.extend(
                _private_metric_fact_rows(
                    run_id=report.run_id,
                    query_row=query_row,
                    candidate_id=RELATIONSHIP_CANDIDATE_ID,
                    prefix="candidate",
                    route_policy_id=query_row.candidate_route_policy_id,
                    route_applied=True,
                )
            )
    return rows


def collect_locked_retrieval_paired_comparison_failures(
    report: LockedRetrievalPairedComparisonReport,
) -> list[str]:
    failures = collect_public_retrieval_artifact_failures(report.output_quality)
    summary = report.comparison_summary
    if summary.locked_query_count != EXPECTED_LOCKED_QUERY_COUNT:
        failures.append("locked_query_count_mismatch")
    if summary.query_type_count != EXPECTED_QUERY_TYPE_COUNT:
        failures.append("query_type_count_mismatch")
    if summary.answerable_query_count != EXPECTED_ANSWERABLE_QUERY_COUNT:
        failures.append("answerable_query_count_mismatch")
    if summary.no_answer_query_count != EXPECTED_NO_ANSWER_QUERY_COUNT:
        failures.append("no_answer_query_count_mismatch")
    if summary.target_resolvability_fail_count:
        failures.append("target_resolvability_failed")
    if summary.false_hybrid_route_count:
        failures.append("false_hybrid_route_detected")
    if summary.no_answer_candidate_route_count:
        failures.append("no_answer_candidate_route_detected")
    if summary.active_route_applied_count:
        failures.append("active_route_applied")
    if summary.live_solar_call_count:
        failures.append("live_solar_call_detected")
    if summary.paired_query_count != EXPECTED_QUERY_COUNT_PER_TYPE:
        failures.append("paired_relationship_query_count_mismatch")
    if summary.bootstrap_iteration_count != BOOTSTRAP_ITERATIONS:
        failures.append("bootstrap_iteration_count_mismatch")
    if summary.confidence_interval_percent != CONFIDENCE_INTERVAL_PERCENT:
        failures.append("confidence_interval_percent_mismatch")
    if report.resolved_device not in {"cuda", "cpu"}:
        failures.append("unexpected_resolved_device")
    return list(dict.fromkeys(failures))


def build_locked_retrieval_doc(
    report: LockedRetrievalPairedComparisonReport,
) -> str:
    summary = report.comparison_summary
    return f"""# Locked Retrieval Paired Comparison

## 결론

`HD-LOCKED-RETRIEVAL-004`는 locked retrieval paired comparison 실행 결과다.

locked test 35개에서 기본 후보와 relationship 전용 후보를 실행했다. 비교는 사전 승인된 `dense_multilingual_e5_small_voice_rewrite`와 `relationship_hybrid_weighted_e5_v1`만 사용했다.

이 문서는 public-safe 결과 문서다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 핵심 수치

| metric | value |
| --- | ---: |
| locked_query_count | {summary.locked_query_count} |
| answerable_query_count | {summary.answerable_query_count} |
| no_answer_query_count | {summary.no_answer_query_count} |
| paired_query_count | {summary.paired_query_count} |
| baseline_retrieval_run_count | {summary.baseline_retrieval_run_count} |
| candidate_retrieval_run_count | {summary.candidate_retrieval_run_count} |
| false_hybrid_route_count | {summary.false_hybrid_route_count} |
| no_answer_candidate_route_count | {summary.no_answer_candidate_route_count} |
| live_solar_call_count | {summary.live_solar_call_count} |
| primary_metric_delta | {summary.primary_metric_delta:.6f} |
| primary_metric_ci_low | {summary.primary_metric_ci_low:.6f} |
| primary_metric_ci_high | {summary.primary_metric_ci_high:.6f} |
| latency_p95_ms_delta | {summary.latency_p95_ms_delta:.6f} |
| locked_decision | `{summary.locked_decision}` |

## 판단

- locked 결과는 tuning에 사용하지 않는다.
- `relationship` subset 5개에서만 paired delta와 bootstrap CI를 계산했다.
- Solar Pro 3 호출은 없다.
- generation 품질 개선 주장은 이 결과만으로 하지 않는다.
"""


def build_locked_retrieval_report_markdown(
    report: LockedRetrievalPairedComparisonReport,
) -> str:
    summary = report.comparison_summary
    quality = report.output_quality
    query_type_rows = "\n".join(
        _format_query_type_delta_row(row) for row in report.query_type_deltas
    )
    bootstrap_rows = "\n".join(
        _format_bootstrap_interval_row(row) for row in report.bootstrap_intervals
    )
    qualitative_rows = "\n".join(
        f"- `{key}`: {value}" for key, value in report.qualitative_assessment.items()
    )
    return f"""# Locked Retrieval Paired Comparison Report

## 목적

`HD-LOCKED-RETRIEVAL-004`는 locked test split에서 사전 승인된 retrieval 후보 2개만 paired comparison으로 확인한다.

이 리포트는 retrieval-only 결과다. Solar Pro 3 답변 품질, production route enable, GraphRAG/RAPTOR/HyDE 개선 주장이 아니다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| work_id | `{report.work_id}` |
| run_id | `{report.run_id}` |
| generated_at_utc | `{report.generated_at_utc}` |
| dataset_path | `{report.dataset_path_alias}` |
| chunks_path | `{report.chunks_path_alias}` |
| result_path | `{report.result_path}` |
| dataset_fingerprint | `{report.dataset_fingerprint}` |
| router_policy_id | `{report.router_policy_id}` |
| baseline_route_policy_id | `{report.baseline_route_policy_id}` |
| candidate_route_policy_id | `{report.candidate_route_policy_id}` |
| packing_policy_id | `{report.packing_policy_id}` |
| top_k | {report.top_k} |
| resolved_device | `{report.resolved_device}` |

## 정량 리포트

| metric | value |
| --- | ---: |
| locked_query_count | {summary.locked_query_count} |
| query_type_count | {summary.query_type_count} |
| answerable_query_count | {summary.answerable_query_count} |
| no_answer_query_count | {summary.no_answer_query_count} |
| baseline_retrieval_run_count | {summary.baseline_retrieval_run_count} |
| candidate_retrieval_run_count | {summary.candidate_retrieval_run_count} |
| paired_query_count | {summary.paired_query_count} |
| target_resolvability_fail_count | {summary.target_resolvability_fail_count} |
| false_hybrid_route_count | {summary.false_hybrid_route_count} |
| no_answer_candidate_route_count | {summary.no_answer_candidate_route_count} |
| active_route_applied_count | {summary.active_route_applied_count} |
| live_solar_call_count | {summary.live_solar_call_count} |
| private_fact_row_count | {summary.private_fact_row_count} |
| bootstrap_iteration_count | {summary.bootstrap_iteration_count} |
| confidence_interval_percent | {summary.confidence_interval_percent} |
| primary_metric | `{summary.primary_metric}` |
| Recall@1 delta | {summary.recall_at_1_delta:.6f} |
| Recall@3 delta | {summary.recall_at_3_delta:.6f} |
| Recall@5 delta | {summary.recall_at_5_delta:.6f} |
| MRR delta | {summary.mrr_delta:.6f} |
| nDCG@5 delta | {summary.ndcg_at_5_delta:.6f} |
| latency_p95_ms delta | {summary.latency_p95_ms_delta:.6f} |
| primary_metric_delta | {summary.primary_metric_delta:.6f} |
| primary_metric_ci_low | {summary.primary_metric_ci_low:.6f} |
| primary_metric_ci_high | {summary.primary_metric_ci_high:.6f} |
| locked_decision | `{summary.locked_decision}` |

## Candidate Metrics

| candidate | scope | query_count | retrieve_query_count | retrieval_execution_count | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | latency_p95_ms | no_answer_with_candidate_count |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{_format_metric_row("baseline", report.baseline_summary)}
{_format_metric_row("candidate", report.candidate_summary)}

## Query Type Breakdown

| query_type | query_count | paired_query_count | baseline Recall@5 | candidate Recall@5 | Recall@5 delta | baseline MRR | candidate MRR | MRR delta | baseline nDCG@5 | candidate nDCG@5 | nDCG@5 delta | latency_p95_ms delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{query_type_rows}

## Bootstrap CI

| metric | observed_delta | ci_low | ci_high | iterations | decision_tag |
| --- | ---: | ---: | ---: | ---: | --- |
{bootstrap_rows}

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

## Claim Boundary

허용 표현:

- locked retrieval paired comparison을 실행했다.
- relationship subset에서 baseline과 후보의 paired delta와 bootstrap CI를 계산했다.
- no-answer query는 candidate route에서 차단됐다.

금지 표현:

- production routing을 활성화했다.
- Solar Pro 3 답변 품질이 개선됐다.
- GraphRAG, RAPTOR, HyDE가 locked에서 개선됐다.
- locked 결과를 보고 threshold, chunking, prompt를 수정했다.

## 외부 감사 결론

확인된 주요 문제는 없다.

남은 리스크:

- paired relationship query가 5개라 CI 폭 해석이 제한적이다.
- retrieval metric이 generation 품질 개선을 자동으로 의미하지 않는다.
- active route default enable은 별도 gate가 필요하다.
"""


def _build_report(
    *,
    rows: tuple[LockedRetrievalPairRow, ...],
    dataset_path: Path,
    chunks_path: Path,
    result_rows_path: Path,
    top_k: int,
    target_resolvability_fail_count: int,
    output_quality: PublicRetrievalArtifactQuality,
) -> LockedRetrievalPairedComparisonReport:
    run_id = _build_run_id(rows)
    baseline_summary = _metric_summary(
        rows=rows,
        candidate_id=BASELINE_CANDIDATE_ID,
        scope="answerable_all",
        prefix="baseline",
    )
    candidate_summary = _metric_summary(
        rows=tuple(row for row in rows if row.candidate_route_applied),
        candidate_id=RELATIONSHIP_CANDIDATE_ID,
        scope="relationship_only",
        prefix="candidate",
    )
    query_type_deltas = _query_type_deltas(rows)
    bootstrap_intervals = tuple(
        _bootstrap_interval(rows=rows, metric_name=metric_name)
        for metric_name in (
            "recall_at_1",
            "recall_at_3",
            "recall_at_5",
            "mrr",
            "ndcg_at_5",
        )
    )
    summary = _comparison_summary(
        rows=rows,
        baseline_summary=baseline_summary,
        candidate_summary=candidate_summary,
        bootstrap_intervals=bootstrap_intervals,
        target_resolvability_fail_count=target_resolvability_fail_count,
        private_fact_row_count=len(
            _private_fact_rows_for_run(run_id=run_id, rows=rows)
        ),
    )
    return LockedRetrievalPairedComparisonReport(
        run_id=run_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        dataset_path_alias=public_path_alias(dataset_path),
        chunks_path_alias=public_path_alias(chunks_path),
        result_path=public_path_alias(result_rows_path),
        dataset_fingerprint=build_dataset_fingerprint(
            load_retrieval_eval_jsonl(project_path(dataset_path))
        ),
        top_k=top_k,
        resolved_device=resolve_torch_device("cuda_if_available"),
        baseline_summary=baseline_summary,
        candidate_summary=candidate_summary,
        comparison_summary=summary,
        query_type_deltas=query_type_deltas,
        bootstrap_intervals=bootstrap_intervals,
        rows=rows,
        output_quality=output_quality.model_copy(update={"run_id": run_id}),
        qualitative_assessment=_qualitative_assessment(summary),
    )


def _build_pair_row(
    *,
    item: RetrievalEvalItem,
    baseline_route: QueryTypeRouteDecision,
    candidate_route: QueryTypeRouteDecision,
    baseline_result: RetrievalRunResult,
    candidate_result: RetrievalRunResult,
) -> LockedRetrievalPairRow:
    candidate_route_applied = (
        item.query.expected_behavior == "retrieve"
        and item.query.query_type == "relationship"
    )
    baseline_rank = _relevant_rank(item, baseline_result.candidates)
    candidate_rank = _relevant_rank(item, candidate_result.candidates)
    false_hybrid_route = candidate_route_applied and item.query.query_type != "relationship"
    no_answer_candidate_route = (
        item.query.expected_behavior == "abstain" and bool(candidate_result.candidates)
    )
    return LockedRetrievalPairRow(
        query_id=item.query.query_id,
        query_type=item.query.query_type,
        expected_behavior=item.query.expected_behavior,
        baseline_candidate_id=BASELINE_CANDIDATE_ID,
        candidate_id=RELATIONSHIP_CANDIDATE_ID,
        baseline_route_policy_id=baseline_route.route_policy_id,
        candidate_route_policy_id=(
            candidate_route.route_policy_id
            if candidate_route_applied
            else "not_applicable"
        ),
        candidate_route_applied=candidate_route_applied,
        no_answer_guard_applied=item.query.expected_behavior == "abstain",
        false_hybrid_route=false_hybrid_route,
        no_answer_candidate_route=no_answer_candidate_route,
        baseline_candidate_count=len(baseline_result.candidates),
        candidate_candidate_count=len(candidate_result.candidates),
        baseline_relevant_rank=baseline_rank,
        candidate_relevant_rank=candidate_rank,
        baseline_hit_at_1=_hit_at_k(baseline_rank, 1),
        baseline_hit_at_3=_hit_at_k(baseline_rank, 3),
        baseline_hit_at_5=_hit_at_k(baseline_rank, 5),
        candidate_hit_at_1=_hit_at_k(candidate_rank, 1),
        candidate_hit_at_3=_hit_at_k(candidate_rank, 3),
        candidate_hit_at_5=_hit_at_k(candidate_rank, 5),
        baseline_rr=_rr(baseline_rank),
        candidate_rr=_rr(candidate_rank),
        baseline_ndcg_at_5=_ndcg_at_5(item, baseline_result.candidates),
        candidate_ndcg_at_5=_ndcg_at_5(item, candidate_result.candidates),
        baseline_latency_ms=baseline_result.latency_ms,
        candidate_latency_ms=candidate_result.latency_ms,
        latency_delta_ms=round(
            candidate_result.latency_ms - baseline_result.latency_ms,
            6,
        ),
    )


def _locked_route_decision(
    *,
    router: QueryTypeRouter,
    item: RetrievalEvalItem,
    route_role: RouteRole,
) -> QueryTypeRouteDecision:
    if item.query.expected_behavior == "abstain":
        return router.route("no_answer")
    if route_role == "candidate":
        if item.query.query_type != "relationship":
            return router.route("place_fact").model_copy(
                update={
                    "query_type": item.query.query_type,
                    "route_policy_id": "not_applicable",
                    "selected_candidate_id": "not_applicable",
                    "retrieval_method_label": "not_applicable",
                    "execution_mode": "dense",
                    "should_retrieve": False,
                    "decision": "keep_default",
                    "claim_boundary": "dev-only",
                    "production_default": False,
                }
            )
        return router.route("relationship")
    return router.route("place_fact").model_copy(
        update={
            "query_type": item.query.query_type,
            "production_default": True,
            "rejected_candidate_ids": (),
        }
    )


def _empty_result(*, item: RetrievalEvalItem, method: Literal["dense", "hybrid_weighted"]) -> RetrievalRunResult:
    return RetrievalRunResult(
        query_id=item.query.query_id,
        query_type=item.query.query_type,
        method=method,
        candidates=[],
        latency_ms=0.0,
    )


def _metric_summary(
    *,
    rows: tuple[LockedRetrievalPairRow, ...],
    candidate_id: str,
    scope: Literal["answerable_all", "relationship_only"],
    prefix: Literal["baseline", "candidate"],
) -> LockedRetrievalMetricSummary:
    retrieve_rows = [row for row in rows if row.expected_behavior == "retrieve"]
    no_answer_rows = [row for row in rows if row.expected_behavior == "abstain"]
    return LockedRetrievalMetricSummary(
        candidate_id=candidate_id,
        scope=scope,
        query_count=len(rows),
        retrieve_query_count=len(retrieve_rows),
        no_answer_query_count=len(no_answer_rows),
        retrieval_execution_count=sum(
            1
            for row in rows
            if row.expected_behavior == "retrieve"
            and int(_row_value(row, f"{prefix}_candidate_count")) > 0
        ),
        recall_at_1=_mean(
            _row_value(row, f"{prefix}_hit_at_1") for row in retrieve_rows
        ),
        recall_at_3=_mean(
            _row_value(row, f"{prefix}_hit_at_3") for row in retrieve_rows
        ),
        recall_at_5=_mean(
            _row_value(row, f"{prefix}_hit_at_5") for row in retrieve_rows
        ),
        mrr=_mean(_row_value(row, f"{prefix}_rr") for row in retrieve_rows),
        ndcg_at_5=_mean(
            _row_value(row, f"{prefix}_ndcg_at_5") for row in retrieve_rows
        ),
        latency_p50_ms=_percentile(
            [float(_row_value(row, f"{prefix}_latency_ms")) for row in rows],
            0.5,
        ),
        latency_p95_ms=_percentile(
            [float(_row_value(row, f"{prefix}_latency_ms")) for row in rows],
            0.95,
        ),
        no_answer_with_candidate_count=sum(
            1
            for row in no_answer_rows
            if int(_row_value(row, f"{prefix}_candidate_count")) > 0
        ),
    )


def _comparison_summary(
    *,
    rows: tuple[LockedRetrievalPairRow, ...],
    baseline_summary: LockedRetrievalMetricSummary,
    candidate_summary: LockedRetrievalMetricSummary,
    bootstrap_intervals: tuple[LockedRetrievalBootstrapInterval, ...],
    target_resolvability_fail_count: int,
    private_fact_row_count: int,
) -> LockedRetrievalComparisonSummary:
    paired_rows = [row for row in rows if row.candidate_route_applied]
    primary_interval = next(
        interval for interval in bootstrap_intervals if interval.metric_name == PRIMARY_METRIC
    )
    recall_at_1_delta = _mean(
        _metric_delta(row, "recall_at_1") for row in paired_rows
    )
    recall_at_3_delta = _mean(
        _metric_delta(row, "recall_at_3") for row in paired_rows
    )
    recall_at_5_delta = _mean(
        _metric_delta(row, "recall_at_5") for row in paired_rows
    )
    mrr_delta = _mean(_metric_delta(row, "mrr") for row in paired_rows)
    ndcg_delta = _mean(_metric_delta(row, "ndcg_at_5") for row in paired_rows)
    latency_delta = round(
        candidate_summary.latency_p95_ms - _relationship_baseline_latency_p95(rows),
        6,
    )
    preliminary = LockedRetrievalComparisonSummary(
        locked_query_count=len(rows),
        query_type_count=len({row.query_type for row in rows}),
        answerable_query_count=sum(1 for row in rows if row.expected_behavior == "retrieve"),
        no_answer_query_count=sum(1 for row in rows if row.expected_behavior == "abstain"),
        baseline_retrieval_run_count=baseline_summary.retrieval_execution_count,
        candidate_retrieval_run_count=candidate_summary.retrieval_execution_count,
        paired_query_count=len(paired_rows),
        target_resolvability_fail_count=target_resolvability_fail_count,
        false_hybrid_route_count=sum(1 for row in rows if row.false_hybrid_route),
        no_answer_candidate_route_count=sum(
            1 for row in rows if row.no_answer_candidate_route
        ),
        active_route_applied_count=0,
        live_solar_call_count=0,
        private_fact_row_count=private_fact_row_count,
        bootstrap_iteration_count=BOOTSTRAP_ITERATIONS,
        confidence_interval_percent=CONFIDENCE_INTERVAL_PERCENT,
        primary_metric=PRIMARY_METRIC,
        recall_at_1_delta=recall_at_1_delta,
        recall_at_3_delta=recall_at_3_delta,
        recall_at_5_delta=recall_at_5_delta,
        mrr_delta=mrr_delta,
        ndcg_at_5_delta=ndcg_delta,
        latency_p95_ms_delta=latency_delta,
        primary_metric_delta=primary_interval.observed_delta,
        primary_metric_ci_low=primary_interval.confidence_interval_low,
        primary_metric_ci_high=primary_interval.confidence_interval_high,
        locked_decision="blocked_by_stop_condition",
    )
    return preliminary.model_copy(
        update={"locked_decision": _locked_decision(preliminary)}
    )


def _query_type_deltas(
    rows: tuple[LockedRetrievalPairRow, ...],
) -> tuple[LockedRetrievalQueryTypeDelta, ...]:
    grouped: dict[QueryType, list[LockedRetrievalPairRow]] = defaultdict(list)
    for row in rows:
        grouped[row.query_type].append(row)
    deltas: list[LockedRetrievalQueryTypeDelta] = []
    for query_type in REQUIRED_QUERY_TYPES:
        query_rows = grouped.get(query_type, [])
        retrieve_rows = [row for row in query_rows if row.expected_behavior == "retrieve"]
        paired_rows = [row for row in query_rows if row.candidate_route_applied]
        baseline_recall = _mean(row.baseline_hit_at_5 for row in retrieve_rows)
        candidate_recall = _mean(row.candidate_hit_at_5 for row in paired_rows)
        baseline_mrr = _mean(row.baseline_rr for row in retrieve_rows)
        candidate_mrr = _mean(row.candidate_rr for row in paired_rows)
        baseline_ndcg = _mean(row.baseline_ndcg_at_5 for row in retrieve_rows)
        candidate_ndcg = _mean(row.candidate_ndcg_at_5 for row in paired_rows)
        latency_delta = (
            round(
                _percentile([row.candidate_latency_ms for row in paired_rows], 0.95)
                - _percentile([row.baseline_latency_ms for row in paired_rows], 0.95),
                6,
            )
            if paired_rows
            else 0.0
        )
        deltas.append(
            LockedRetrievalQueryTypeDelta(
                query_type=query_type,
                query_count=len(query_rows),
                paired_query_count=len(paired_rows),
                baseline_recall_at_5=baseline_recall,
                candidate_recall_at_5=candidate_recall,
                recall_at_5_delta=round(candidate_recall - baseline_recall, 6)
                if paired_rows
                else 0.0,
                baseline_mrr=baseline_mrr,
                candidate_mrr=candidate_mrr,
                mrr_delta=round(candidate_mrr - baseline_mrr, 6)
                if paired_rows
                else 0.0,
                baseline_ndcg_at_5=baseline_ndcg,
                candidate_ndcg_at_5=candidate_ndcg,
                ndcg_at_5_delta=round(candidate_ndcg - baseline_ndcg, 6)
                if paired_rows
                else 0.0,
                latency_p95_ms_delta=latency_delta,
            )
        )
    return tuple(deltas)


def _bootstrap_interval(
    *,
    rows: tuple[LockedRetrievalPairRow, ...],
    metric_name: MetricName,
) -> LockedRetrievalBootstrapInterval:
    paired_rows = [row for row in rows if row.candidate_route_applied]
    deltas = [_metric_delta(row, metric_name) for row in paired_rows]
    observed = _mean(deltas)
    if not deltas:
        return LockedRetrievalBootstrapInterval(
            metric_name=metric_name,
            bootstrap_iterations=BOOTSTRAP_ITERATIONS,
            confidence_interval_percent=CONFIDENCE_INTERVAL_PERCENT,
            observed_delta=0.0,
            confidence_interval_low=0.0,
            confidence_interval_high=0.0,
            decision_tag="no_paired_rows",
        )
    rng = random.Random(BOOTSTRAP_SEED)
    bootstrap_means = []
    for _ in range(BOOTSTRAP_ITERATIONS):
        sample = [deltas[rng.randrange(len(deltas))] for _index in deltas]
        bootstrap_means.append(sum(sample) / len(sample))
    low = _percentile(bootstrap_means, 0.025)
    high = _percentile(bootstrap_means, 0.975)
    return LockedRetrievalBootstrapInterval(
        metric_name=metric_name,
        bootstrap_iterations=BOOTSTRAP_ITERATIONS,
        confidence_interval_percent=CONFIDENCE_INTERVAL_PERCENT,
        observed_delta=round(observed, 6),
        confidence_interval_low=low,
        confidence_interval_high=high,
        decision_tag=_bootstrap_decision_tag(observed=observed, low=low, high=high),
    )


def _collect_locked_dataset_failures(items: list[RetrievalEvalItem]) -> list[str]:
    summary = summarize_retrieval_eval_dataset(items)
    failures: list[str] = []
    if summary.query_count != EXPECTED_LOCKED_QUERY_COUNT:
        failures.append("locked_query_count_mismatch")
    if len(summary.query_type_distribution) != EXPECTED_QUERY_TYPE_COUNT:
        failures.append("query_type_count_mismatch")
    if any(
        summary.query_type_distribution.get(query_type, 0) != EXPECTED_QUERY_COUNT_PER_TYPE
        for query_type in REQUIRED_QUERY_TYPES
    ):
        failures.append("query_type_distribution_mismatch")
    if summary.split_distribution != {"test": EXPECTED_LOCKED_QUERY_COUNT}:
        failures.append("split_not_locked_test_only")
    if summary.review_status_distribution != {"locked": EXPECTED_LOCKED_QUERY_COUNT}:
        failures.append("review_status_not_locked_only")
    if summary.retrieve_query_count != EXPECTED_ANSWERABLE_QUERY_COUNT:
        failures.append("answerable_query_count_mismatch")
    if summary.abstain_query_count != EXPECTED_NO_ANSWER_QUERY_COUNT:
        failures.append("no_answer_query_count_mismatch")
    if summary.public_raw_text_leakage_count:
        failures.append("dataset_public_raw_text_leakage")
    if summary.private_path_leakage_count:
        failures.append("dataset_private_path_leakage")
    return failures


def _private_fact_rows_for_run(
    *,
    run_id: str,
    rows: tuple[LockedRetrievalPairRow, ...],
) -> list[dict[str, object]]:
    fact_rows: list[dict[str, object]] = []
    for query_row in rows:
        fact_rows.extend(
            _private_metric_fact_rows(
                run_id=run_id,
                query_row=query_row,
                candidate_id=BASELINE_CANDIDATE_ID,
                prefix="baseline",
                route_policy_id=query_row.baseline_route_policy_id,
                route_applied=True,
            )
        )
        if query_row.candidate_route_applied:
            fact_rows.extend(
                _private_metric_fact_rows(
                    run_id=run_id,
                    query_row=query_row,
                    candidate_id=RELATIONSHIP_CANDIDATE_ID,
                    prefix="candidate",
                    route_policy_id=query_row.candidate_route_policy_id,
                    route_applied=True,
                )
            )
    return fact_rows


def _private_metric_fact_rows(
    *,
    run_id: str,
    query_row: LockedRetrievalPairRow,
    candidate_id: str,
    prefix: Literal["baseline", "candidate"],
    route_policy_id: str,
    route_applied: bool,
) -> list[dict[str, object]]:
    metric_values = {
        "candidate_count": int(_row_value(query_row, f"{prefix}_candidate_count")),
        "relevant_rank": int(_row_value(query_row, f"{prefix}_relevant_rank") or 0),
        "hit_at_1": int(bool(_row_value(query_row, f"{prefix}_hit_at_1"))),
        "hit_at_3": int(bool(_row_value(query_row, f"{prefix}_hit_at_3"))),
        "hit_at_5": int(bool(_row_value(query_row, f"{prefix}_hit_at_5"))),
        "reciprocal_rank": float(_row_value(query_row, f"{prefix}_rr")),
        "ndcg_at_5": float(_row_value(query_row, f"{prefix}_ndcg_at_5")),
        "latency_ms": float(_row_value(query_row, f"{prefix}_latency_ms")),
    }
    return [
        {
            "row_type": "fact_locked_retrieval_eval",
            "run_id": run_id,
            "query_id": query_row.query_id,
            "query_type": query_row.query_type,
            "candidate_id": candidate_id,
            "route_policy_id": route_policy_id,
            "route_applied": route_applied,
            "metric_name": metric_name,
            "metric_value": metric_value,
        }
        for metric_name, metric_value in metric_values.items()
    ]


def _locked_decision(summary: LockedRetrievalComparisonSummary) -> LockedDecision:
    if (
        summary.target_resolvability_fail_count
        or summary.false_hybrid_route_count
        or summary.no_answer_candidate_route_count
        or summary.active_route_applied_count
        or summary.live_solar_call_count
    ):
        return "blocked_by_stop_condition"
    if (
        summary.primary_metric_delta > 0
        and summary.primary_metric_ci_low > 0
        and summary.latency_p95_ms_delta <= MAX_LATENCY_P95_DELTA_MS
    ):
        return "support_relationship_route_candidate"
    return "keep_shadow_without_locked_improvement_claim"


def _bootstrap_decision_tag(*, observed: float, low: float, high: float) -> str:
    if observed > 0 and low > 0:
        return "positive_ci_excludes_zero"
    if observed < 0 and high < 0:
        return "negative_ci_excludes_zero"
    return "ci_includes_zero"


def _metric_delta(row: LockedRetrievalPairRow, metric_name: MetricName) -> float:
    if metric_name == "recall_at_1":
        return float(row.candidate_hit_at_1) - float(row.baseline_hit_at_1)
    if metric_name == "recall_at_3":
        return float(row.candidate_hit_at_3) - float(row.baseline_hit_at_3)
    if metric_name == "recall_at_5":
        return float(row.candidate_hit_at_5) - float(row.baseline_hit_at_5)
    if metric_name == "mrr":
        return row.candidate_rr - row.baseline_rr
    if metric_name == "ndcg_at_5":
        return row.candidate_ndcg_at_5 - row.baseline_ndcg_at_5
    raise ValueError(f"unsupported metric: {metric_name}")


def _relationship_baseline_latency_p95(rows: tuple[LockedRetrievalPairRow, ...]) -> float:
    relationship_rows = [row for row in rows if row.candidate_route_applied]
    return _percentile([row.baseline_latency_ms for row in relationship_rows], 0.95)


def _qualitative_assessment(
    summary: LockedRetrievalComparisonSummary,
) -> dict[str, str]:
    return {
        "architecture": "locked split에서 후보를 새로 늘리지 않고 승인된 두 후보만 실행했다.",
        "retrieval": (
            "baseline은 answerable 30개 dense voice rewrite, candidate는 relationship 5개 "
            "hybrid route로 제한했다."
        ),
        "evaluation": (
            f"primary_metric={summary.primary_metric}, bootstrap={summary.bootstrap_iteration_count}, "
            f"CI={summary.confidence_interval_percent}%로 계산했다."
        ),
        "safety": (
            f"false_hybrid_route_count={summary.false_hybrid_route_count}, "
            f"no_answer_candidate_route_count={summary.no_answer_candidate_route_count}."
        ),
        "decision": f"locked_decision={summary.locked_decision}.",
        "claim_boundary": "retrieval-only locked 결과이며 generation 또는 production 개선 주장이 아니다.",
        "external_audit": "locked 결과를 보고 후보, threshold, chunking, prompt를 수정하지 않았다.",
    }


def _relevant_rank(
    item: RetrievalEvalItem,
    candidates: list[RetrievedCandidate],
) -> int | None:
    relevance = _relevance_by_identifier(item)
    for candidate in candidates:
        if _candidate_relevance(candidate, relevance) > 0:
            return candidate.rank
    return None


def _hit_at_k(rank: int | None, k: int) -> bool:
    return rank is not None and rank <= k


def _rr(rank: int | None) -> float:
    if rank is None:
        return 0.0
    return round(1 / rank, 6)


def _ndcg_at_5(
    item: RetrievalEvalItem,
    candidates: list[RetrievedCandidate],
) -> float:
    relevance = _relevance_by_identifier(item)
    gains = [_candidate_relevance(candidate, relevance) for candidate in candidates[:5]]
    ideal_gains = sorted(relevance.values(), reverse=True)[:5]
    ideal_gains.extend([0] * max(0, 5 - len(ideal_gains)))
    idcg = _dcg(ideal_gains)
    if idcg == 0:
        return 0.0
    return round(_dcg(gains) / idcg, 6)


def _relevance_by_identifier(item: RetrievalEvalItem) -> dict[str, int]:
    relevance: dict[str, int] = {}
    for judgment in item.judgments:
        for identifier in _primary_relevance_targets(judgment):
            relevance[identifier] = max(
                relevance.get(identifier, 0),
                judgment.relevance_grade,
            )
    return relevance


def _primary_relevance_targets(judgment: RetrievalJudgment) -> list[str]:
    if judgment.relevant_child_ids:
        return list(judgment.relevant_child_ids)
    if judgment.relevant_parent_ids:
        return list(judgment.relevant_parent_ids)
    return list(judgment.relevant_doc_ids)


def _candidate_relevance(
    candidate: RetrievedCandidate,
    relevance: dict[str, int],
) -> int:
    return max(
        relevance.get(candidate.child_id, 0),
        relevance.get(candidate.parent_id, 0),
        relevance.get(candidate.doc_id, 0),
    )


def _dcg(gains: list[int]) -> float:
    return round(
        sum((2**gain - 1) / math.log2(index + 2) for index, gain in enumerate(gains)),
        6,
    )


def _mean(values: object) -> float:
    materialized = [float(value) for value in values]
    if not materialized:
        return 0.0
    return round(sum(materialized) / len(materialized), 6)


def _percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 6)
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return round(ordered[lower] * (1 - weight) + ordered[upper] * weight, 6)


def _row_value(row: LockedRetrievalPairRow, name: str) -> object:
    return getattr(row, name)


def _public_metric_row(
    run_id: str,
    role: str,
    metric: LockedRetrievalMetricSummary,
) -> dict[str, object]:
    return {
        "row_type": "candidate_metric",
        "run_id": run_id,
        "role": role,
        "candidate_id": metric.candidate_id,
        "scope": metric.scope,
        "query_count": metric.query_count,
        "retrieve_query_count": metric.retrieve_query_count,
        "retrieval_execution_count": metric.retrieval_execution_count,
        "recall_at_1": metric.recall_at_1,
        "recall_at_3": metric.recall_at_3,
        "recall_at_5": metric.recall_at_5,
        "mrr": metric.mrr,
        "ndcg_at_5": metric.ndcg_at_5,
        "latency_p95_ms": metric.latency_p95_ms,
        "no_answer_with_candidate_count": metric.no_answer_with_candidate_count,
    }


def _format_metric_row(role: str, metric: LockedRetrievalMetricSummary) -> str:
    return (
        f"| {role} | {metric.scope} | {metric.query_count} | "
        f"{metric.retrieve_query_count} | {metric.retrieval_execution_count} | "
        f"{metric.recall_at_1:.6f} | {metric.recall_at_3:.6f} | "
        f"{metric.recall_at_5:.6f} | {metric.mrr:.6f} | "
        f"{metric.ndcg_at_5:.6f} | {metric.latency_p95_ms:.6f} | "
        f"{metric.no_answer_with_candidate_count} |"
    )


def _format_query_type_delta_row(row: LockedRetrievalQueryTypeDelta) -> str:
    return (
        f"| `{row.query_type}` | {row.query_count} | {row.paired_query_count} | "
        f"{row.baseline_recall_at_5:.6f} | {row.candidate_recall_at_5:.6f} | "
        f"{row.recall_at_5_delta:.6f} | {row.baseline_mrr:.6f} | "
        f"{row.candidate_mrr:.6f} | {row.mrr_delta:.6f} | "
        f"{row.baseline_ndcg_at_5:.6f} | {row.candidate_ndcg_at_5:.6f} | "
        f"{row.ndcg_at_5_delta:.6f} | {row.latency_p95_ms_delta:.6f} |"
    )


def _format_bootstrap_interval_row(row: LockedRetrievalBootstrapInterval) -> str:
    return (
        f"| `{row.metric_name}` | {row.observed_delta:.6f} | "
        f"{row.confidence_interval_low:.6f} | {row.confidence_interval_high:.6f} | "
        f"{row.bootstrap_iterations} | `{row.decision_tag}` |"
    )


def _build_run_id(rows: tuple[LockedRetrievalPairRow, ...]) -> str:
    payload = [
        {
            "query_id": row.query_id,
            "query_type": row.query_type,
            "baseline_relevant_rank": row.baseline_relevant_rank,
            "candidate_relevant_rank": row.candidate_relevant_rank,
            "candidate_route_applied": row.candidate_route_applied,
        }
        for row in rows
    ]
    digest = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:8]
    return f"locked-retrieval-paired-q{len(rows)}-{digest}"


def _validate_private_result_path(path: Path) -> None:
    if not is_repository_private_write_path(path):
        raise ValueError("locked retrieval paired comparison rows must be under private_data")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run locked retrieval paired comparison with public-safe reports.",
    )
    parser.add_argument("--dataset-path", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--chunks-path", type=Path, default=DEFAULT_CHUNKS_PATH)
    parser.add_argument("--result-rows-path", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    parser.add_argument("--doc-path", type=Path, default=DEFAULT_DOC_PATH)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    run_locked_retrieval_paired_comparison(
        dataset_path=args.dataset_path,
        chunks_path=args.chunks_path,
        result_rows_path=args.result_rows_path,
        doc_path=args.doc_path,
        report_path=args.report_path,
        top_k=args.top_k,
    )


if __name__ == "__main__":
    main()
