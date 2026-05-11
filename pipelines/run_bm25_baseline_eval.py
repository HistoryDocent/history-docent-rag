from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.chunking import ChildChunk
from app.domain.retrieval import (
    FORBIDDEN_PUBLIC_EVAL_FIELDS,
    QueryType,
    RetrievalDocument,
    RetrievalEvalItem,
    RetrievalMetricSummary,
    RetrievalRunResult,
    build_retrieval_document_from_child,
    compute_retrieval_metrics,
    load_retrieval_eval_jsonl,
)
from app.infrastructure.index.bm25 import Bm25Retriever


DEFAULT_CHUNKS_PATH = Path("private_data") / "reports" / "parent_child_chunks.json"
DEFAULT_DATASET_PATH = Path("evals/datasets/retrieval_eval_seed.jsonl")
DEFAULT_RESULTS_PATH = Path("evals/results/bm25_baseline_results.jsonl")
DEFAULT_REPORT_PATH = Path("evals/reports/bm25_baseline_report.md")
BM25_BASELINE_REPORT_VERSION = "bm25-baseline-report/v1"
BM25_RUN_ID_PREFIX = "bm25-baseline"
SECRET_VALUE_MARKERS = (
    "sk-",
    "api_" + "key=",
    "api" + "key=",
    "pass" + "word=",
    "to" + "ken=",
    "sec" + "ret=",
)


class Bm25EvalModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class QueryTypeMetricSummary(Bm25EvalModel):
    query_type: QueryType
    query_count: int = Field(ge=0)
    recall_at_1: float = Field(ge=0.0, le=1.0)
    recall_at_3: float = Field(ge=0.0, le=1.0)
    recall_at_5: float = Field(ge=0.0, le=1.0)
    mrr: float = Field(ge=0.0, le=1.0)
    ndcg_at_5: float = Field(ge=0.0, le=1.0)
    latency_p95_ms: float = Field(ge=0.0)
    abstain_with_candidate_count: int = Field(ge=0)


class PublicRetrievalOutputQuality(Bm25EvalModel):
    result_row_count: int = Field(ge=0)
    report_version: str
    run_id: str
    public_raw_text_leakage_count: int = Field(ge=0)
    private_path_leakage_count: int = Field(ge=0)
    secret_like_leakage_count: int = Field(ge=0)
    forbidden_result_field_count: int = Field(ge=0)


class Bm25BaselineReport(Bm25EvalModel):
    report_version: str = BM25_BASELINE_REPORT_VERSION
    run_id: str
    generated_at_utc: str
    dataset_path: str
    chunks_path_alias: str
    result_path: str
    method: str = "bm25"
    top_k: int = Field(ge=1)
    indexed_document_count: int = Field(ge=0)
    dataset_query_count: int = Field(ge=0)
    metric_summary: RetrievalMetricSummary
    query_type_breakdown: list[QueryTypeMetricSummary]
    output_quality: PublicRetrievalOutputQuality
    qualitative_assessment: dict[str, str]


@dataclass(frozen=True)
class _RunArtifacts:
    items: list[RetrievalEvalItem]
    documents: list[RetrievalDocument]
    results: list[RetrievalRunResult]
    metric_summary: RetrievalMetricSummary
    query_type_breakdown: list[QueryTypeMetricSummary]


def run_bm25_baseline_eval(
    *,
    chunks_path: Path = DEFAULT_CHUNKS_PATH,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    results_path: Path = DEFAULT_RESULTS_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    top_k: int = 5,
) -> Bm25BaselineReport:
    artifacts = _run_eval(
        chunks_path=chunks_path,
        dataset_path=dataset_path,
        top_k=top_k,
    )
    run_id = _build_run_id(artifacts)
    result_rows = _public_result_rows(run_id=run_id, results=artifacts.results)
    _write_jsonl(results_path, result_rows)
    output_quality = _measure_public_output_quality(
        run_id=run_id,
        result_rows=result_rows,
        report_text="",
    )
    report = Bm25BaselineReport(
        run_id=run_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        dataset_path=_public_path_alias(dataset_path),
        chunks_path_alias="<private parent_child_chunks report>",
        result_path=_public_path_alias(results_path),
        top_k=top_k,
        indexed_document_count=len(artifacts.documents),
        dataset_query_count=len(artifacts.items),
        metric_summary=artifacts.metric_summary,
        query_type_breakdown=artifacts.query_type_breakdown,
        output_quality=output_quality,
        qualitative_assessment=_build_qualitative_assessment(
            metric_summary=artifacts.metric_summary,
            query_type_breakdown=artifacts.query_type_breakdown,
        ),
    )
    report_text = build_bm25_baseline_report_markdown(report)
    final_output_quality = _measure_public_output_quality(
        run_id=run_id,
        result_rows=result_rows,
        report_text=report_text,
    )
    report = report.model_copy(update={"output_quality": final_output_quality})
    report_text = build_bm25_baseline_report_markdown(report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_text, encoding="utf-8")
    return report


def collect_public_retrieval_output_failures(
    output_quality: PublicRetrievalOutputQuality,
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


def build_bm25_baseline_report_markdown(report: Bm25BaselineReport) -> str:
    metric = report.metric_summary
    breakdown_rows = "\n".join(
        "| "
        f"{item.query_type} | {item.query_count} | {item.recall_at_1:.6f} | "
        f"{item.recall_at_3:.6f} | {item.recall_at_5:.6f} | {item.mrr:.6f} | "
        f"{item.ndcg_at_5:.6f} | {item.latency_p95_ms:.6f} | "
        f"{item.abstain_with_candidate_count} |"
        for item in report.query_type_breakdown
    )
    quality = report.output_quality
    qualitative_rows = "\n".join(
        f"- `{key}`: {value}" for key, value in report.qualitative_assessment.items()
    )
    return f"""# BM25 Baseline Report

## 목적

BM25 lexical retrieval을 seed 평가셋에서 측정한다.

이 문서는 성능 개선 주장이 아니다. Dense, Hybrid, query rewrite 비교를 위한 기준선 기록이다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| run_id | `{report.run_id}` |
| generated_at_utc | `{report.generated_at_utc}` |
| method | `{report.method}` |
| top_k | {report.top_k} |
| indexed_document_count | {report.indexed_document_count} |
| dataset_query_count | {report.dataset_query_count} |
| chunks_path_alias | `{report.chunks_path_alias}` |
| dataset_path | `{report.dataset_path}` |
| result_path | `{report.result_path}` |

## 정량 리포트

| metric | value |
| --- | ---: |
| query_count | {metric.query_count} |
| retrieve_query_count | {metric.retrieve_query_count} |
| abstain_query_count | {metric.abstain_query_count} |
| result_count | {metric.result_count} |
| missing_result_count | {metric.missing_result_count} |
| Recall@1 | {metric.recall_at_1:.6f} |
| Recall@3 | {metric.recall_at_3:.6f} |
| Recall@5 | {metric.recall_at_5:.6f} |
| MRR | {metric.mrr:.6f} |
| nDCG@5 | {metric.ndcg_at_5:.6f} |
| latency_p50_ms | {metric.latency_p50_ms:.6f} |
| latency_p95_ms | {metric.latency_p95_ms:.6f} |
| abstain_with_candidate_count | {metric.abstain_with_candidate_count} |

## Query Type Breakdown

| query_type | query_count | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | latency_p95_ms | abstain_with_candidate_count |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{breakdown_rows}

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

BM25는 query rewrite, place expansion, dense retrieval, reranking을 적용하지 않은 lexical baseline이다.

`voice_followup`, 영어 query, route형 질문은 이후 query rewrite와 hybrid retrieval의 개선 여지가 큰 영역으로 본다.

`no_answer` 질문에서 후보를 반환하는 것은 BM25의 한계로 기록한다. 최종 RAG에서는 no-answer detector와 answer contract에서 다시 통제해야 한다.
"""


def _run_eval(
    *,
    chunks_path: Path,
    dataset_path: Path,
    top_k: int,
) -> _RunArtifacts:
    items = load_retrieval_eval_jsonl(dataset_path)
    documents = load_retrieval_documents_from_chunks(chunks_path)
    retriever = Bm25Retriever.from_documents(documents)
    results = [
        retriever.search(
            query_id=item.query.query_id,
            query_type=item.query.query_type,
            query_text=item.query.query_text,
            top_k=top_k,
        )
        for item in items
    ]
    metric_summary = compute_retrieval_metrics(
        items=items,
        results=results,
        method="bm25",
    )
    return _RunArtifacts(
        items=items,
        documents=documents,
        results=results,
        metric_summary=metric_summary,
        query_type_breakdown=_compute_query_type_breakdown(items=items, results=results),
    )


def load_retrieval_documents_from_chunks(chunks_path: Path) -> list[RetrievalDocument]:
    payload = json.loads(chunks_path.read_text(encoding="utf-8"))
    children_payload = payload.get("children")
    if not isinstance(children_payload, list):
        raise ValueError("parent_child_chunks payload must include children list")
    documents: list[RetrievalDocument] = []
    for child_payload in children_payload:
        child = ChildChunk.model_validate(child_payload)
        if not child.text:
            continue
        documents.append(
            build_retrieval_document_from_child(child, include_private_text=True)
        )
    if not documents:
        raise ValueError("no searchable child chunks found")
    return documents


def _compute_query_type_breakdown(
    *,
    items: list[RetrievalEvalItem],
    results: list[RetrievalRunResult],
) -> list[QueryTypeMetricSummary]:
    query_types = sorted({item.query.query_type for item in items})
    summaries: list[QueryTypeMetricSummary] = []
    for query_type in query_types:
        subset_items = [item for item in items if item.query.query_type == query_type]
        subset_results = [
            result for result in results if result.query_type == query_type
        ]
        metric = compute_retrieval_metrics(
            items=subset_items,
            results=subset_results,
            method="bm25",
        )
        summaries.append(
            QueryTypeMetricSummary(
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


def _public_result_rows(
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


def _measure_public_output_quality(
    *,
    run_id: str,
    result_rows: list[dict[str, Any]],
    report_text: str,
) -> PublicRetrievalOutputQuality:
    payload: Any = {"results": result_rows, "report_text": report_text}
    string_values = _iter_string_values(payload)
    return PublicRetrievalOutputQuality(
        result_row_count=len(result_rows),
        report_version=BM25_BASELINE_REPORT_VERSION,
        run_id=run_id,
        public_raw_text_leakage_count=_count_forbidden_public_fields(payload),
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


def _build_qualitative_assessment(
    *,
    metric_summary: RetrievalMetricSummary,
    query_type_breakdown: list[QueryTypeMetricSummary],
) -> dict[str, str]:
    breakdown = {item.query_type: item for item in query_type_breakdown}
    weakest = min(
        [item for item in query_type_breakdown if item.query_type != "no_answer"],
        key=lambda item: (item.recall_at_5, item.mrr, item.ndcg_at_5),
    )
    return {
        "baseline_scope": (
            "BM25 lexical baseline만 측정했다. query rewrite, dense retrieval, hybrid retrieval은 제외했다."
        ),
        "overall_retrieval": (
            f"Recall@5={metric_summary.recall_at_5:.6f}, "
            f"MRR={metric_summary.mrr:.6f}, nDCG@5={metric_summary.ndcg_at_5:.6f}."
        ),
        "weakest_query_type": (
            f"{weakest.query_type}: Recall@5={weakest.recall_at_5:.6f}, "
            f"MRR={weakest.mrr:.6f}."
        ),
        "abstention_scope": (
            "no_answer는 retrieval recall 대상이 아니라 후보 반환 여부를 보는 abstention risk로 분리한다."
        ),
        "voice_followup_risk": _format_optional_breakdown(
            breakdown.get("voice_followup"),
            "voice_followup",
        ),
        "no_answer_risk": _format_no_answer_risk(breakdown.get("no_answer")),
        "next_step": (
            "Dense retrieval과 Hybrid retrieval을 같은 seed 평가셋에서 비교하고, "
            "query rewrite는 별도 ablation으로 검증한다."
        ),
    }


def _format_optional_breakdown(
    summary: QueryTypeMetricSummary | None,
    query_type: str,
) -> str:
    if summary is None:
        return f"{query_type} query가 없어 평가하지 못했다."
    return (
        f"{query_type}: Recall@5={summary.recall_at_5:.6f}, "
        f"MRR={summary.mrr:.6f}. lexical query만 사용했다."
    )


def _format_no_answer_risk(summary: QueryTypeMetricSummary | None) -> str:
    if summary is None:
        return "no_answer query가 없어 평가하지 못했다."
    return (
        f"no_answer 후보 반환 수={summary.abstain_with_candidate_count}. "
        "BM25는 검색기이므로 corpus 밖 질문을 독립적으로 거절하지 못한다."
    )


def _build_run_id(artifacts: _RunArtifacts) -> str:
    digest_source = {
        "query_ids": [item.query.query_id for item in artifacts.items],
        "query_texts": [item.query.query_text for item in artifacts.items],
        "document_ids": [document.retrieval_doc_id for document in artifacts.documents],
    }
    digest = hashlib.sha256(
        json.dumps(digest_source, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:8]
    return (
        f"{BM25_RUN_ID_PREFIX}-q{len(artifacts.items)}-d{len(artifacts.documents)}-{digest}"
    )


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def _public_path_alias(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.name


def _count_forbidden_public_fields(payload: Any) -> int:
    if isinstance(payload, dict):
        count = sum(1 for key in payload if str(key) in FORBIDDEN_PUBLIC_EVAL_FIELDS)
        return count + sum(_count_forbidden_public_fields(value) for value in payload.values())
    if isinstance(payload, list | tuple):
        return sum(_count_forbidden_public_fields(item) for item in payload)
    return 0


def _contains_private_path(value: str) -> bool:
    normalized = value.replace("/", "\\")
    return bool((":\\" in normalized) or normalized.startswith("\\\\"))


def _contains_secret_like_value(value: str) -> bool:
    lowered = value.lower()
    return any(marker in lowered for marker in SECRET_VALUE_MARKERS)


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


def main() -> int:
    args = _parse_args()
    report = run_bm25_baseline_eval(
        chunks_path=args.chunks,
        dataset_path=args.dataset,
        results_path=args.results,
        report_path=args.report,
        top_k=args.top_k,
    )
    failures = collect_public_retrieval_output_failures(report.output_quality)
    print(
        "bm25_baseline "
        f"status={'PASS' if not failures else 'FAIL'} "
        f"query_count={report.metric_summary.query_count} "
        f"recall_at_5={report.metric_summary.recall_at_5:.6f} "
        f"mrr={report.metric_summary.mrr:.6f} "
        f"ndcg_at_5={report.metric_summary.ndcg_at_5:.6f} "
        f"latency_p95_ms={report.metric_summary.latency_p95_ms:.6f} "
        f"failures={len(failures)}"
    )
    return 0 if not failures else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run BM25 baseline retrieval evaluation.")
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS_PATH)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--top-k", type=int, default=5)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
