from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.project_paths import (
    is_repository_private_artifact_path,
    project_path,
    repository_root,
)
from app.domain.retrieval import (
    FORBIDDEN_PUBLIC_EVAL_FIELDS,
    QueryType,
    RetrievalDocument,
    RetrievalEvalItem,
    RetrievalMetricSummary,
    RetrievalMethod,
    RetrievalRunResult,
    compute_retrieval_metrics,
)


RETRIEVAL_EXPERIMENT_REPORT_VERSION = "retrieval-experiment-report/v1"
RETRIEVAL_HARNESS_RUN_PREFIX = "retrieval-harness"
PRIVATE_CHUNKS_PATH_ALIAS = "<private parent_child_chunks report>"
MAX_PUBLIC_TEXT_VALUE_LENGTH = 600
SECRET_VALUE_MARKERS = (
    "sk-",
    "api_" + "key=",
    "api" + "key=",
    "ghp_",
    "github_pat_",
    "hf_",
    "xoxb-",
    "bearer ",
    "pass" + "word=",
    "to" + "ken=",
    "sec" + "ret=",
)
_PRIVATE_PATH_PATTERN = re.compile(r"([A-Za-z]:[\\/]|\\\\[^\\/]+[\\/][^\\/]+)")
_POSIX_PRIVATE_PATH_PATTERN = re.compile(
    r"(^|\s)/(home|users|mnt|var|tmp|private|runner|workspace|root)/",
    re.IGNORECASE,
)
_LINE_KEY_PATTERN = re.compile(r"^(?P<artifact>.+):(?P<line_number>[0-9]+)$")
_CODE_LIKE_LINE_MARKERS = (
    "Path(",
    " = ",
    "    ",
    "{",
    "}",
    "```",
    "|",
    "report_",
    "result_",
    "metric",
    "contains_",
    "assert ",
    "from ",
    "import ",
)
METHOD_CONFIG_REPORT_KEYS = (
    "method",
    "top_k",
    "encoder_id",
    "encoder_backend",
    "model_name",
    "query_rewrite",
    "query_rewrite_strategy",
    "query_rewrite_target_types",
    "query_rewrite_changed_count",
    "query_rewrite_invalid_json_count",
    "query_rewrite_invalid_json_rate",
    "query_rewrite_no_answer_guard_count",
    "query_rewrite_latency_p95_ms",
    "query_rewrite_solar_call_count",
    "dense_encoder_id",
    "dense_encoder_backend",
    "dense_model_name",
    "dense_weight_alpha",
    "fusion",
    "retrieval_candidate_k",
    "reranking",
    "base_run_label",
    "reranker_id",
    "reranker_backend",
    "reranker_model_name",
)


class RetrievalExperimentModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class QueryTypeMetricSummary(RetrievalExperimentModel):
    run_label: str = Field(min_length=1)
    method: RetrievalMethod
    query_type: QueryType
    query_count: int = Field(ge=0)
    recall_at_1: float = Field(ge=0.0, le=1.0)
    recall_at_3: float = Field(ge=0.0, le=1.0)
    recall_at_5: float = Field(ge=0.0, le=1.0)
    mrr: float = Field(ge=0.0, le=1.0)
    ndcg_at_5: float = Field(ge=0.0, le=1.0)
    latency_p95_ms: float = Field(ge=0.0)
    abstain_with_candidate_count: int = Field(ge=0)


class RetrievalMetricDelta(RetrievalExperimentModel):
    baseline_run_label: str = Field(min_length=1)
    baseline_method: RetrievalMethod
    compared_run_label: str = Field(min_length=1)
    compared_method: RetrievalMethod
    recall_at_1_delta: float
    recall_at_3_delta: float
    recall_at_5_delta: float
    mrr_delta: float
    ndcg_at_5_delta: float
    latency_p95_ms_delta: float


class PublicRetrievalArtifactQuality(RetrievalExperimentModel):
    result_row_count: int = Field(ge=0)
    report_version: str
    run_id: str
    public_raw_text_leakage_count: int = Field(ge=0)
    private_path_leakage_count: int = Field(ge=0)
    secret_like_leakage_count: int = Field(ge=0)
    forbidden_result_field_count: int = Field(ge=0)


class RetrievalExperimentRun(RetrievalExperimentModel):
    run_id: str
    run_label: str = Field(min_length=1)
    method: RetrievalMethod
    top_k: int = Field(ge=1)
    dataset_fingerprint: str = Field(min_length=8)
    corpus_fingerprint: str = Field(min_length=8)
    method_config_fingerprint: str = Field(min_length=8)
    method_config_summary: dict[str, str | int | float | bool]
    result_path: str
    indexed_document_count: int = Field(ge=0)
    dataset_query_count: int = Field(ge=0)
    metric_summary: RetrievalMetricSummary
    query_type_breakdown: list[QueryTypeMetricSummary]


class RetrievalComparisonReport(RetrievalExperimentModel):
    report_version: str = RETRIEVAL_EXPERIMENT_REPORT_VERSION
    comparison_id: str
    generated_at_utc: str
    dataset_path: str
    dataset_fingerprint: str = Field(min_length=8)
    corpus_fingerprint: str = Field(min_length=8)
    top_k: int = Field(ge=1)
    chunks_path_alias: str = PRIVATE_CHUNKS_PATH_ALIAS
    baseline_method: RetrievalMethod
    method_runs: list[RetrievalExperimentRun] = Field(min_length=1)
    metric_deltas: list[RetrievalMetricDelta]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def build_retrieval_experiment_run(
    *,
    method: RetrievalMethod,
    run_label: str | None = None,
    top_k: int,
    items: list[RetrievalEvalItem],
    documents: list[RetrievalDocument],
    results: list[RetrievalRunResult],
    result_path: Path,
    method_config_summary: dict[str, str | int | float | bool] | None = None,
) -> RetrievalExperimentRun:
    label = run_label or method
    run_id = build_retrieval_run_id(
        method=method,
        run_label=label,
        items=items,
        documents=documents,
    )
    config_summary = method_config_summary or {"method": method, "top_k": top_k}
    return RetrievalExperimentRun(
        run_id=run_id,
        run_label=label,
        method=method,
        top_k=top_k,
        dataset_fingerprint=build_dataset_fingerprint(items),
        corpus_fingerprint=build_corpus_fingerprint(documents),
        method_config_fingerprint=build_method_config_fingerprint(config_summary),
        method_config_summary=config_summary,
        result_path=public_path_alias(result_path),
        indexed_document_count=len(documents),
        dataset_query_count=len(items),
        metric_summary=compute_retrieval_metrics(
            items=items,
            results=results,
            method=method,
        ),
        query_type_breakdown=compute_query_type_metric_breakdown(
            items=items,
            results=results,
            method=method,
            run_label=label,
        ),
    )


def build_retrieval_comparison_report(
    *,
    dataset_path: Path,
    method_runs: list[RetrievalExperimentRun],
    output_quality: PublicRetrievalArtifactQuality,
    baseline_method: RetrievalMethod = "bm25",
) -> RetrievalComparisonReport:
    if not method_runs:
        raise ValueError("retrieval comparison requires at least one method run")
    validate_comparison_invariants(
        method_runs=method_runs,
        baseline_method=baseline_method,
    )
    first_run = method_runs[0]
    comparison_id = build_retrieval_comparison_id(method_runs)
    metric_deltas = build_metric_deltas(
        method_runs=method_runs,
        baseline_method=baseline_method,
    )
    return RetrievalComparisonReport(
        comparison_id=comparison_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        dataset_path=public_path_alias(dataset_path),
        dataset_fingerprint=first_run.dataset_fingerprint,
        corpus_fingerprint=first_run.corpus_fingerprint,
        top_k=first_run.top_k,
        baseline_method=baseline_method,
        method_runs=method_runs,
        metric_deltas=metric_deltas,
        output_quality=output_quality,
        qualitative_assessment=build_qualitative_assessment(
            method_runs=method_runs,
            metric_deltas=metric_deltas,
            baseline_method=baseline_method,
        ),
    )


def validate_comparison_invariants(
    *,
    method_runs: list[RetrievalExperimentRun],
    baseline_method: RetrievalMethod,
) -> None:
    methods = [run.method for run in method_runs]
    run_labels = [run.run_label for run in method_runs]
    if len(run_labels) != len(set(run_labels)):
        raise ValueError("retrieval comparison run labels must be unique")
    if baseline_method not in set(methods):
        raise ValueError("baseline method must be included in method_runs")
    if len({run.dataset_fingerprint for run in method_runs}) != 1:
        raise ValueError("all retrieval method runs must use the same dataset fingerprint")
    if len({run.corpus_fingerprint for run in method_runs}) != 1:
        raise ValueError("all retrieval method runs must use the same corpus fingerprint")
    if len({run.top_k for run in method_runs}) != 1:
        raise ValueError("all retrieval method runs must use the same top_k")


def build_retrieval_run_id(
    *,
    method: RetrievalMethod,
    run_label: str | None = None,
    items: list[RetrievalEvalItem],
    documents: list[RetrievalDocument],
) -> str:
    label = run_label or method
    digest_source = {
        "method": method,
        "run_label": label,
        "query_ids": [item.query.query_id for item in items],
        "query_texts": [item.query.query_text for item in items],
        "document_ids": [document.retrieval_doc_id for document in documents],
    }
    digest = hashlib.sha256(
        json.dumps(digest_source, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:8]
    return f"{RETRIEVAL_HARNESS_RUN_PREFIX}-{label}-q{len(items)}-d{len(documents)}-{digest}"


def build_dataset_fingerprint(items: list[RetrievalEvalItem]) -> str:
    payload = [
        item.model_dump(mode="json")
        for item in sorted(items, key=lambda item: item.query.query_id)
    ]
    return _stable_digest(payload)


def build_corpus_fingerprint(documents: list[RetrievalDocument]) -> str:
    payload = [
        {
            "retrieval_doc_id": document.retrieval_doc_id,
            "child_id": document.child_id,
            "parent_id": document.parent_id,
            "doc_id": document.doc_id,
            "page_span": document.page_span.model_dump(mode="json"),
            "source_block_ids": document.source_block_ids,
            "citation_block_ids": document.citation_block_ids,
            "text_hash": document.text_hash,
            "text_length": document.text_length,
            "element_type_mix": document.element_type_mix,
        }
        for document in sorted(documents, key=lambda document: document.retrieval_doc_id)
    ]
    return _stable_digest(payload)


def build_method_config_fingerprint(
    method_config_summary: dict[str, str | int | float | bool],
) -> str:
    return _stable_digest(method_config_summary)


def build_retrieval_comparison_id(method_runs: list[RetrievalExperimentRun]) -> str:
    digest_source = [
        {
            "method": run.method,
            "run_label": run.run_label,
            "run_id": run.run_id,
            "top_k": run.top_k,
            "dataset_fingerprint": run.dataset_fingerprint,
            "corpus_fingerprint": run.corpus_fingerprint,
            "method_config_fingerprint": run.method_config_fingerprint,
            "dataset_query_count": run.dataset_query_count,
            "indexed_document_count": run.indexed_document_count,
        }
        for run in method_runs
    ]
    digest = hashlib.sha256(
        json.dumps(digest_source, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:8]
    methods = "-".join(run.run_label for run in method_runs)
    if len(methods) > 160:
        methods = f"m{len(method_runs)}"
    query_count = method_runs[0].dataset_query_count
    return f"{RETRIEVAL_HARNESS_RUN_PREFIX}-{methods}-q{query_count}-{digest}"


def compute_query_type_metric_breakdown(
    *,
    items: list[RetrievalEvalItem],
    results: list[RetrievalRunResult],
    method: RetrievalMethod,
    run_label: str | None = None,
) -> list[QueryTypeMetricSummary]:
    query_types = sorted({item.query.query_type for item in items})
    summaries: list[QueryTypeMetricSummary] = []
    for query_type in query_types:
        subset_items = [item for item in items if item.query.query_type == query_type]
        subset_results = [
            result
            for result in results
            if result.method == method and result.query_type == query_type
        ]
        metric = compute_retrieval_metrics(
            items=subset_items,
            results=subset_results,
            method=method,
        )
        summaries.append(
            QueryTypeMetricSummary(
                run_label=run_label or method,
                method=method,
                query_type=query_type,
                query_count=metric.query_count,
                recall_at_1=metric.recall_at_1,
                recall_at_3=metric.recall_at_3,
                recall_at_5=metric.recall_at_5,
                mrr=metric.mrr,
                ndcg_at_5=metric.ndcg_at_5,
                latency_p95_ms=metric.latency_p95_ms,
                abstain_with_candidate_count=metric.abstain_with_candidate_count,
            )
        )
    return summaries


def build_metric_deltas(
    *,
    method_runs: list[RetrievalExperimentRun],
    baseline_method: RetrievalMethod,
) -> list[RetrievalMetricDelta]:
    baseline = next((run for run in method_runs if run.method == baseline_method), None)
    if baseline is None:
        return []
    baseline_metric = baseline.metric_summary
    deltas: list[RetrievalMetricDelta] = []
    for run in method_runs:
        metric = run.metric_summary
        deltas.append(
            RetrievalMetricDelta(
                baseline_run_label=baseline.run_label,
                baseline_method=baseline_method,
                compared_run_label=run.run_label,
                compared_method=run.method,
                recall_at_1_delta=round(metric.recall_at_1 - baseline_metric.recall_at_1, 6),
                recall_at_3_delta=round(metric.recall_at_3 - baseline_metric.recall_at_3, 6),
                recall_at_5_delta=round(metric.recall_at_5 - baseline_metric.recall_at_5, 6),
                mrr_delta=round(metric.mrr - baseline_metric.mrr, 6),
                ndcg_at_5_delta=round(metric.ndcg_at_5 - baseline_metric.ndcg_at_5, 6),
                latency_p95_ms_delta=round(
                    metric.latency_p95_ms - baseline_metric.latency_p95_ms,
                    6,
                ),
            )
        )
    return deltas


def build_public_retrieval_result_rows(
    *,
    run_id: str,
    results: list[RetrievalRunResult],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for result in results:
        for candidate in result.candidates:
            rows.append(
                {
                    "run_id": run_id,
                    "method": result.method,
                    "query_id": result.query_id,
                    "query_type": result.query_type,
                    "latency_ms": result.latency_ms,
                    "rank": candidate.rank,
                    "retrieval_doc_id": candidate.retrieval_doc_id,
                    "child_id": candidate.child_id,
                    "parent_id": candidate.parent_id,
                    "doc_id": candidate.doc_id,
                    "score": candidate.score,
                }
            )
        if not result.candidates:
            rows.append(
                {
                    "run_id": run_id,
                    "method": result.method,
                    "query_id": result.query_id,
                    "query_type": result.query_type,
                    "latency_ms": result.latency_ms,
                    "rank": None,
                    "retrieval_doc_id": None,
                    "child_id": None,
                    "parent_id": None,
                    "doc_id": None,
                    "score": None,
                }
            )
    return rows


def retrieval_result_rows_to_jsonl(rows: list[dict[str, Any]]) -> str:
    return "\n".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows
    )


def write_public_retrieval_result_rows(
    *,
    path: Path,
    rows: list[dict[str, Any]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(retrieval_result_rows_to_jsonl(rows) + "\n", encoding="utf-8")


def load_public_retrieval_result_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def measure_public_retrieval_artifact_quality(
    *,
    report_version: str,
    run_id: str,
    result_rows: list[dict[str, Any]],
    report_text: str,
    extra_public_texts: dict[str, str] | None = None,
) -> PublicRetrievalArtifactQuality:
    payload: Any = {
        "results": result_rows,
        "report_lines": report_text.splitlines(),
        "extra_public_texts": extra_public_texts or {},
    }
    string_values = _iter_string_values(payload)
    extra_texts = extra_public_texts or {}
    return PublicRetrievalArtifactQuality(
        result_row_count=len(result_rows),
        report_version=report_version,
        run_id=run_id,
        public_raw_text_leakage_count=(
            _count_forbidden_public_fields(result_rows)
            + _count_source_text_like_public_values(payload)
            + _count_multiline_source_like_public_blocks(extra_texts)
        ),
        private_path_leakage_count=sum(
            1 for value in string_values if _contains_private_path(value)
        ),
        secret_like_leakage_count=sum(
            1 for value in string_values if _contains_secret_like_value(value)
        ),
        forbidden_result_field_count=sum(
            1
            for row in result_rows
            for key in row
            if key in FORBIDDEN_PUBLIC_EVAL_FIELDS
        ),
    )


def collect_public_retrieval_artifact_failures(
    output_quality: PublicRetrievalArtifactQuality,
) -> list[str]:
    failures: list[str] = []
    if output_quality.public_raw_text_leakage_count:
        failures.append("public_raw_text_leakage")
    if output_quality.private_path_leakage_count:
        failures.append("private_path_leakage")
    if output_quality.secret_like_leakage_count:
        failures.append("secret_like_leakage")
    if output_quality.forbidden_result_field_count:
        failures.append("forbidden_result_fields")
    return failures


def build_retrieval_harness_report_markdown(
    report: RetrievalComparisonReport,
) -> str:
    method_rows = "\n".join(
        _format_method_metric_row(run) for run in report.method_runs
    )
    method_config_rows = "\n".join(
        _format_method_config_row(run) for run in report.method_runs
    )
    breakdown_rows = "\n".join(
        _format_query_type_metric_row(item)
        for run in report.method_runs
        for item in run.query_type_breakdown
    )
    delta_rows = "\n".join(_format_metric_delta_row(delta) for delta in report.metric_deltas)
    quality = report.output_quality
    qualitative_rows = "\n".join(
        f"- `{key}`: {value}" for key, value in report.qualitative_assessment.items()
    )
    result_path_rows = "\n".join(
        f"| {run.run_label} | `{run.result_path}` |" for run in report.method_runs
    )
    return f"""# Retrieval Harness Report

## 목적

BM25, Dense, Hybrid, Query Rewrite retrieval을 같은 평가셋과 같은 metric으로 비교한다.

이 문서는 성능 개선 주장이 아니다. method별 기준선과 delta를 기록하고, locked test와 generation 평가 전까지는 개선 표현을 사용하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| comparison_id | `{report.comparison_id}` |
| generated_at_utc | `{report.generated_at_utc}` |
| baseline_method | `{report.baseline_method}` |
| method_count | {len(report.method_runs)} |
| top_k | {report.top_k} |
| dataset_fingerprint | `{report.dataset_fingerprint}` |
| corpus_fingerprint | `{report.corpus_fingerprint}` |
| chunks_path_alias | `{report.chunks_path_alias}` |
| dataset_path | `{report.dataset_path}` |
| result_artifact_count | {len(report.method_runs)} |

## Result Artifacts

| run_label | result_path |
| --- | --- |
{result_path_rows}

## Method Config

| run_label | method | config |
| --- | --- | --- |
{method_config_rows}

## 정량 리포트

| run_label | method | query_count | retrieve_query_count | abstain_query_count | result_count | missing_result_count | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | latency_p50_ms | latency_p95_ms | abstain_with_candidate_count |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{method_rows}

## Query Type Breakdown

| run_label | method | query_type | query_count | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | latency_p95_ms | abstain_with_candidate_count |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{breakdown_rows}

## Baseline Delta

| baseline_run_label | baseline_method | compared_run_label | compared_method | Recall@1 delta | Recall@3 delta | Recall@5 delta | MRR delta | nDCG@5 delta | latency_p95_ms delta |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
{delta_rows}

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

현재 harness는 선택한 retrieval method를 공통 실험 형식으로 평가했다.

후속 method를 추가할 때는 dataset, corpus, metric, output gate를 바꾸지 않고 `method` 실행기만 추가한다. 개선 주장은 paired comparison과 bootstrap confidence interval을 붙인 뒤에만 가능하다.
"""


def build_qualitative_assessment(
    *,
    method_runs: list[RetrievalExperimentRun],
    metric_deltas: list[RetrievalMetricDelta],
    baseline_method: RetrievalMethod,
) -> dict[str, str]:
    baseline = next((run for run in method_runs if run.method == baseline_method), None)
    methods = ", ".join(run.run_label for run in method_runs)
    if baseline is None:
        baseline_text = f"{baseline_method} 기준선이 없어 delta를 계산하지 않았다."
    else:
        metric = baseline.metric_summary
        baseline_text = (
            f"{baseline_method}: Recall@5={metric.recall_at_5:.6f}, "
            f"MRR={metric.mrr:.6f}, nDCG@5={metric.ndcg_at_5:.6f}."
        )
    return {
        "harness_scope": (
            f"공통 schema로 평가한 method는 {methods}다."
        ),
        "dense_encoder_boundary": _build_dense_encoder_boundary_text(method_runs),
        "query_rewrite_boundary": _build_query_rewrite_boundary_text(method_runs),
        "reranker_boundary": _build_reranker_boundary_text(method_runs),
        "baseline_reproduction": baseline_text,
        "comparison_status": (
            "현재 delta는 dev 기준 비교 결과다. 성능 개선 주장이 아니라 비교 형식과 후보 성능 기록이다."
        ),
        "public_policy": (
            "public result와 report에는 rank, id, score, metric만 저장하고 검색 본문은 저장하지 않는다."
        ),
        "next_step": (
            _build_next_step_text(method_runs)
        ),
        "delta_row_count": f"{len(metric_deltas)}개 method delta row를 생성했다.",
    }


def public_path_alias(path: Path) -> str:
    resolved = project_path(path).resolve()
    if is_repository_private_artifact_path(path):
        name = resolved.name or path.name
        if name.startswith("retrieval_eval_dev"):
            return f"<private retrieval eval dataset: {name}>"
        if name.startswith("retrieval_eval_test"):
            return f"<private retrieval eval dataset: {name}>"
        return f"<private artifact: {name}>"
    try:
        return resolved.relative_to(repository_root().resolve()).as_posix()
    except ValueError:
        return path.name


def _format_method_metric_row(run: RetrievalExperimentRun) -> str:
    metric = run.metric_summary
    return (
        f"| {run.run_label} | {run.method} | {metric.query_count} | "
        f"{metric.retrieve_query_count} | "
        f"{metric.abstain_query_count} | {metric.result_count} | "
        f"{metric.missing_result_count} | {metric.recall_at_1:.6f} | "
        f"{metric.recall_at_3:.6f} | {metric.recall_at_5:.6f} | "
        f"{metric.mrr:.6f} | {metric.ndcg_at_5:.6f} | "
        f"{metric.latency_p50_ms:.6f} | {metric.latency_p95_ms:.6f} | "
        f"{metric.abstain_with_candidate_count} |"
    )


def _format_query_type_metric_row(item: QueryTypeMetricSummary) -> str:
    return (
        f"| {item.run_label} | {item.method} | {item.query_type} | "
        f"{item.query_count} | "
        f"{item.recall_at_1:.6f} | {item.recall_at_3:.6f} | "
        f"{item.recall_at_5:.6f} | {item.mrr:.6f} | {item.ndcg_at_5:.6f} | "
        f"{item.latency_p95_ms:.6f} | {item.abstain_with_candidate_count} |"
    )


def _format_method_config_row(run: RetrievalExperimentRun) -> str:
    config = ", ".join(
        f"{key}={run.method_config_summary[key]}"
        for key in METHOD_CONFIG_REPORT_KEYS
        if key in run.method_config_summary
    )
    return f"| {run.run_label} | {run.method} | `{config}` |"


def _format_metric_delta_row(delta: RetrievalMetricDelta) -> str:
    return (
        f"| {delta.baseline_run_label} | {delta.baseline_method} | "
        f"{delta.compared_run_label} | {delta.compared_method} | "
        f"{delta.recall_at_1_delta:.6f} | {delta.recall_at_3_delta:.6f} | "
        f"{delta.recall_at_5_delta:.6f} | {delta.mrr_delta:.6f} | "
        f"{delta.ndcg_at_5_delta:.6f} | {delta.latency_p95_ms_delta:.6f} |"
    )


def _build_next_step_text(method_runs: list[RetrievalExperimentRun]) -> str:
    methods = {run.method for run in method_runs}
    query_rewrite_runs = [
        run for run in method_runs if run.method_config_summary.get("query_rewrite") is True
    ]
    reranked_runs = [
        run for run in method_runs if run.method_config_summary.get("reranking") is True
    ]
    neural_hybrid_runs = [
        run
        for run in method_runs
        if run.method in {"hybrid_rrf", "hybrid_weighted"}
        and run.method_config_summary.get("dense_encoder_backend")
        == "sentence_transformers"
    ]
    neural_dense_runs = [
        run
        for run in method_runs
        if run.method_config_summary.get("encoder_backend") == "sentence_transformers"
    ]
    if query_rewrite_runs:
        best = max(
            query_rewrite_runs,
            key=lambda run: (
                run.metric_summary.mrr,
                run.metric_summary.ndcg_at_5,
                run.metric_summary.recall_at_5,
            ),
        )
        return (
            f"Query rewrite 후보 `{best.run_label}`를 Dense 기본 후보와 비교했다. "
            "다음 판단은 evidence packing과 generation eval에서 citation 품질까지 확인한 뒤 한다."
        )
    if reranked_runs:
        best_reranked = max(
            reranked_runs,
            key=lambda run: (
                run.metric_summary.mrr,
                run.metric_summary.ndcg_at_5,
                run.metric_summary.recall_at_5,
            ),
        )
        return (
            f"Reranker 최고 top-rank 후보는 `{best_reranked.run_label}`다. "
            "Dense/Hybrid 원본과 latency trade-off를 비교한 뒤 "
            "locked test와 generation 평가 전까지 최종 개선 주장은 보류한다."
        )
    if neural_hybrid_runs:
        best_hybrid = max(
            neural_hybrid_runs,
            key=lambda run: (
                run.metric_summary.recall_at_5,
                run.metric_summary.mrr,
                run.metric_summary.ndcg_at_5,
            ),
        )
        return (
            f"Neural dense Hybrid 최고 Recall@5 후보는 `{best_hybrid.run_label}`다. "
            "Dense 단독 후보와 top-rank, latency trade-off를 비교한 뒤 "
            "상위 2개 method에만 reranker comparison을 적용한다."
        )
    if neural_dense_runs:
        return (
            "Neural dense 후보 중 BM25보다 Recall@5 또는 MRR이 높은 모델을 "
            "Hybrid/Reranker 비교에 투입하고, latency/cost trade-off를 별도로 기록한다."
        )
    if "dense" in methods and "hybrid_rrf" not in methods and "hybrid_weighted" not in methods:
        return "Dense baseline 결과를 기준으로 Hybrid RRF/Weighted retrieval을 같은 report에 추가한다."
    if "hybrid_rrf" in methods or "hybrid_weighted" in methods:
        baseline = next((run for run in method_runs if run.method == "bm25"), None)
        hybrid_runs = [
            run for run in method_runs if run.method in {"hybrid_rrf", "hybrid_weighted"}
        ]
        if baseline is None:
            return "Hybrid 후보가 있으나 BM25 기준선이 없어 선택 판단을 보류한다."
        passing_hybrid = [
            run
            for run in hybrid_runs
            if (
                run.metric_summary.recall_at_5 > baseline.metric_summary.recall_at_5
                or run.metric_summary.mrr > baseline.metric_summary.mrr
            )
            and run.metric_summary.latency_p95_ms
            <= round(baseline.metric_summary.latency_p95_ms * 1.2, 6)
        ]
        if passing_hybrid:
            labels = ", ".join(run.run_label for run in passing_hybrid)
            return f"선택 gate를 통과한 Hybrid 후보({labels})에만 reranker comparison을 적용한다."
        return (
            "현재 Hybrid 후보는 선택 gate를 통과하지 못했다. BM25를 유지하고 "
            "neural embedding 또는 shared dense index 최적화 후 재실험한다."
        )
    return "Dense retriever와 Hybrid retriever를 같은 report에 추가한 뒤 query type별 delta를 비교한다."


def _build_dense_encoder_boundary_text(method_runs: list[RetrievalExperimentRun]) -> str:
    dense_runs = [
        run
        for run in method_runs
        if run.method == "dense" or "dense_encoder_id" in run.method_config_summary
    ]
    if not dense_runs:
        return "Dense encoder는 아직 실행하지 않았다."
    encoder_ids = sorted({
        str(
            run.method_config_summary.get(
                "encoder_id",
                run.method_config_summary.get("dense_encoder_id", "unknown"),
            )
        )
        for run in dense_runs
    })
    neural_encoder_ids = sorted({
        str(run.method_config_summary.get("encoder_id", "unknown"))
        for run in dense_runs
        if run.method_config_summary.get("encoder_backend") == "sentence_transformers"
    })
    if neural_encoder_ids:
        return (
            f"Dense neural encoder는 {', '.join(neural_encoder_ids)}다. "
            "sentence-transformers backend로 실행했고, embedding vector/cache는 private artifact로만 저장한다."
        )
    return (
        f"Dense v1 encoder는 {', '.join(encoder_ids)}다. "
        "이 결과는 neural embedding 모델인 BGE-M3 또는 multilingual-E5 결과가 아니다."
    )


def _build_reranker_boundary_text(method_runs: list[RetrievalExperimentRun]) -> str:
    reranked_runs = [
        run for run in method_runs if run.method_config_summary.get("reranking") is True
    ]
    if not reranked_runs:
        return "Reranker는 아직 실행하지 않았다."
    best = max(
        reranked_runs,
        key=lambda run: (
            run.metric_summary.mrr,
            run.metric_summary.ndcg_at_5,
            run.metric_summary.recall_at_5,
        ),
    )
    metric = best.metric_summary
    latency_note = (
        "CPU latency가 커서 실서비스 기본 후보로 바로 채택하지 않는다."
        if metric.latency_p95_ms >= 1000.0
        else "제품 SLO 안에서 재검토할 수 있다."
    )
    return (
        f"Reranker 최고 후보는 {best.run_label}: "
        f"Recall@5={metric.recall_at_5:.6f}, MRR={metric.mrr:.6f}, "
        f"nDCG@5={metric.ndcg_at_5:.6f}, "
        f"latency_p95_ms={metric.latency_p95_ms:.6f}. {latency_note}"
    )


def _build_query_rewrite_boundary_text(
    method_runs: list[RetrievalExperimentRun],
) -> str:
    query_rewrite_runs = [
        run for run in method_runs if run.method_config_summary.get("query_rewrite") is True
    ]
    if not query_rewrite_runs:
        return "Query rewrite는 아직 실행하지 않았다."
    best = max(
        query_rewrite_runs,
        key=lambda run: (
            run.metric_summary.mrr,
            run.metric_summary.ndcg_at_5,
            run.metric_summary.recall_at_5,
        ),
    )
    metric = best.metric_summary
    changed_count = best.method_config_summary.get("query_rewrite_changed_count", 0)
    invalid_count = best.method_config_summary.get("query_rewrite_invalid_json_count", 0)
    return (
        f"Query rewrite 최고 후보는 {best.run_label}: "
        f"Recall@5={metric.recall_at_5:.6f}, MRR={metric.mrr:.6f}, "
        f"nDCG@5={metric.ndcg_at_5:.6f}, "
        f"changed_count={changed_count}, invalid_json_count={invalid_count}. "
        "Solar Pro 3 호출 없이 deterministic place/context expansion만 사용했다."
    )


def _count_forbidden_public_fields(payload: Any) -> int:
    if isinstance(payload, dict):
        count = sum(1 for key in payload if str(key) in FORBIDDEN_PUBLIC_EVAL_FIELDS)
        return count + sum(_count_forbidden_public_fields(value) for value in payload.values())
    if isinstance(payload, list | tuple):
        return sum(_count_forbidden_public_fields(item) for item in payload)
    return 0


def _count_source_text_like_public_values(payload: Any) -> int:
    return sum(1 for value in _iter_string_values(payload) if _is_source_text_like(value))


def _is_source_text_like(value: str) -> bool:
    stripped = value.strip()
    return bool(
        ("\n" in stripped)
        or ("\r" in stripped)
        or len(stripped) > MAX_PUBLIC_TEXT_VALUE_LENGTH
    )


def _count_multiline_source_like_public_blocks(extra_public_texts: dict[str, str]) -> int:
    grouped_lines: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for key, value in extra_public_texts.items():
        match = _LINE_KEY_PATTERN.match(key)
        if match is None:
            continue
        grouped_lines[match.group("artifact")].append(
            (int(match.group("line_number")), value)
        )

    count = 0
    for lines in grouped_lines.values():
        consecutive = 0
        previous_line_number: int | None = None
        for line_number, value in sorted(lines):
            if previous_line_number is not None and line_number != previous_line_number + 1:
                consecutive = 0
            if _is_source_like_natural_language_line(value):
                consecutive += 1
                if consecutive == 3:
                    count += 1
            else:
                consecutive = 0
            previous_line_number = line_number
    return count


def _is_source_like_natural_language_line(value: str) -> bool:
    stripped = value.strip().strip('",')
    if len(stripped) < 40:
        return False
    if any(marker in stripped for marker in _CODE_LIKE_LINE_MARKERS):
        return False
    letter_count = sum(1 for char in stripped if char.isalpha() or "가" <= char <= "힣")
    return (letter_count / max(len(stripped), 1)) >= 0.3


def _contains_private_path(value: str) -> bool:
    return bool(
        _PRIVATE_PATH_PATTERN.search(value.replace("/", "\\"))
        or _POSIX_PRIVATE_PATH_PATTERN.search(value)
    )


def _contains_secret_like_value(value: str) -> bool:
    lowered = value.lower()
    return any(marker in lowered for marker in SECRET_VALUE_MARKERS)


def _stable_digest(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]


def _iter_string_values(payload: Any) -> list[str]:
    if isinstance(payload, str):
        return [payload]
    if isinstance(payload, dict):
        values: list[str] = []
        for key, value in payload.items():
            values.extend(_iter_string_values(str(key)))
            values.extend(_iter_string_values(value))
        return values
    if isinstance(payload, list | tuple | set):
        values = []
        for item in payload:
            values.extend(_iter_string_values(item))
        return values
    return []
