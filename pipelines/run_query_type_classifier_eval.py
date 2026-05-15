from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.application.query_type_classifier import (
    QUERY_TYPE_CLASSIFIER_ID,
    DeterministicQueryTypeClassifier,
    QueryTypeClassificationInput,
)
from app.application.query_type_router import QueryTypeRouter
from app.domain.retrieval import QueryType, REQUIRED_QUERY_TYPES, load_retrieval_eval_jsonl
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    build_dataset_fingerprint,
    collect_public_retrieval_artifact_failures,
    measure_public_retrieval_artifact_quality,
    public_path_alias,
    write_public_retrieval_result_rows,
)


QUERY_TYPE_CLASSIFIER_EVAL_REPORT_VERSION = "query-type-classifier-eval-report/v1"
DEFAULT_DATASET_PATH = Path("private_data/evals/datasets/retrieval_eval_dev.jsonl")
DEFAULT_RESULT_PATH = Path("private_data/evals/results/query_type_classifier_eval_rows.jsonl")
DEFAULT_REPORT_PATH = Path("evals/reports/query_type_classifier_eval_report.md")
MIN_ACCURACY = 0.80
MIN_MACRO_F1 = 0.80
MIN_ROUTE_POLICY_ACCURACY = 0.95
MAX_FALLBACK_RATE = 0.30


class QueryTypeClassifierEvalModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class QueryTypeClassifierClassMetric(QueryTypeClassifierEvalModel):
    query_type: QueryType
    support: int = Field(ge=0)
    predicted_count: int = Field(ge=0)
    true_positive_count: int = Field(ge=0)
    precision: float = Field(ge=0.0, le=1.0)
    recall: float = Field(ge=0.0, le=1.0)
    f1: float = Field(ge=0.0, le=1.0)


class QueryTypeClassifierConfusionCell(QueryTypeClassifierEvalModel):
    expected_query_type: QueryType
    predicted_query_type: QueryType
    count: int = Field(ge=0)


class QueryTypeClassifierEvalSummary(QueryTypeClassifierEvalModel):
    query_count: int = Field(ge=0)
    query_type_count: int = Field(ge=0)
    correct_count: int = Field(ge=0)
    accuracy: float = Field(ge=0.0, le=1.0)
    macro_precision: float = Field(ge=0.0, le=1.0)
    macro_recall: float = Field(ge=0.0, le=1.0)
    macro_f1: float = Field(ge=0.0, le=1.0)
    route_policy_correct_count: int = Field(ge=0)
    route_policy_accuracy: float = Field(ge=0.0, le=1.0)
    fallback_count: int = Field(ge=0)
    fallback_rate: float = Field(ge=0.0, le=1.0)
    min_confidence: float = Field(ge=0.0, le=1.0)
    average_confidence: float = Field(ge=0.0, le=1.0)
    live_solar_call_count: int = Field(ge=0)
    cuda_required: bool = False


class QueryTypeClassifierEvalReport(QueryTypeClassifierEvalModel):
    report_version: str = QUERY_TYPE_CLASSIFIER_EVAL_REPORT_VERSION
    run_id: str
    generated_at_utc: str
    classifier_id: str = QUERY_TYPE_CLASSIFIER_ID
    dataset_path: str
    dataset_fingerprint: str = Field(min_length=8)
    result_path: str
    summary: QueryTypeClassifierEvalSummary
    class_metrics: tuple[QueryTypeClassifierClassMetric, ...]
    confusion_matrix: tuple[QueryTypeClassifierConfusionCell, ...]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def build_query_type_classifier_eval_report(
    *,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    result_path: Path = DEFAULT_RESULT_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
) -> QueryTypeClassifierEvalReport:
    items = load_retrieval_eval_jsonl(dataset_path)
    classifier = DeterministicQueryTypeClassifier()
    rows = []
    router = QueryTypeRouter()
    for item in items:
        expected_query_type = item.query.query_type
        result = classifier.classify(
            QueryTypeClassificationInput(
                query_text=item.query.query_text,
                user_context=item.query.user_context,
                place_ids=tuple(item.metadata.place_ids),
                has_dialog_context=item.metadata.requires_context,
            )
        )
        expected_route = router.route(expected_query_type).route_policy_id
        predicted_route = router.route(result.predicted_query_type).route_policy_id
        rows.append(
            {
                "query_id": item.query.query_id,
                "expected_query_type": expected_query_type,
                "predicted_query_type": result.predicted_query_type,
                "correct": expected_query_type == result.predicted_query_type,
                "confidence": result.confidence,
                "fallback_used": result.fallback_used,
                "matched_rule_count": len(result.matched_rule_ids),
                "route_expected_policy_id": expected_route,
                "route_predicted_policy_id": predicted_route,
                "route_policy_correct": expected_route == predicted_route,
                "latency_ms": result.latency_ms,
            }
        )

    run_id = _build_run_id(rows=rows, classifier_id=classifier.classifier_id)
    write_public_retrieval_result_rows(path=result_path, rows=rows)

    provisional_quality = measure_public_retrieval_artifact_quality(
        report_version=QUERY_TYPE_CLASSIFIER_EVAL_REPORT_VERSION,
        run_id=run_id,
        result_rows=rows,
        report_text="",
    )
    provisional_report = _build_report_from_rows(
        rows=rows,
        dataset_path=dataset_path,
        result_path=result_path,
        output_quality=provisional_quality,
        run_id=run_id,
    )
    report_text = build_query_type_classifier_eval_report_markdown(provisional_report)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=QUERY_TYPE_CLASSIFIER_EVAL_REPORT_VERSION,
        run_id=run_id,
        result_rows=rows,
        report_text=report_text,
    )
    report = _build_report_from_rows(
        rows=rows,
        dataset_path=dataset_path,
        result_path=result_path,
        output_quality=output_quality,
        run_id=run_id,
    )
    failures = collect_query_type_classifier_eval_failures(report)
    if failures:
        raise ValueError(f"query type classifier eval gate failed: {failures}")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        build_query_type_classifier_eval_report_markdown(report),
        encoding="utf-8",
    )
    print(
        "query_type_classifier_eval "
        "status=PASS "
        f"query_count={report.summary.query_count} "
        f"accuracy={report.summary.accuracy:.6f} "
        f"macro_f1={report.summary.macro_f1:.6f} "
        f"route_policy_accuracy={report.summary.route_policy_accuracy:.6f} "
        f"fallback_count={report.summary.fallback_count}"
    )
    return report


def collect_query_type_classifier_eval_failures(
    report: QueryTypeClassifierEvalReport,
) -> list[str]:
    failures = collect_public_retrieval_artifact_failures(report.output_quality)
    summary = report.summary
    if summary.query_type_count != len(REQUIRED_QUERY_TYPES):
        failures.append("missing_query_type_coverage")
    if summary.accuracy < MIN_ACCURACY:
        failures.append("accuracy_below_gate")
    if summary.macro_f1 < MIN_MACRO_F1:
        failures.append("macro_f1_below_gate")
    if summary.route_policy_accuracy < MIN_ROUTE_POLICY_ACCURACY:
        failures.append("route_policy_accuracy_below_gate")
    if summary.fallback_rate > MAX_FALLBACK_RATE:
        failures.append("fallback_rate_above_gate")
    if summary.live_solar_call_count:
        failures.append("live_solar_call_detected")
    if summary.cuda_required:
        failures.append("unexpected_cuda_requirement")
    if not report.confusion_matrix:
        failures.append("missing_confusion_matrix")
    return failures


def build_query_type_classifier_eval_report_markdown(
    report: QueryTypeClassifierEvalReport,
) -> str:
    summary = report.summary
    quality = report.output_quality
    class_rows = "\n".join(_format_class_metric_row(row) for row in report.class_metrics)
    confusion_rows = "\n".join(
        _format_confusion_row(row) for row in report.confusion_matrix
    )
    qualitative_rows = "\n".join(
        f"- `{key}`: {value}" for key, value in report.qualitative_assessment.items()
    )
    return f"""# Query Type Classifier Eval Report

## 목적

실제 API 입력에서 query type label이 직접 주어지지 않는다는 전제를 검증하기 위해 deterministic classifier baseline을 평가한다.

이 문서는 classifier contract와 라우팅 입력 품질 평가다. 검색 성능 개선, locked test 개선, Solar Pro 3 답변 품질 개선 주장이 아니다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| run_id | `{report.run_id}` |
| classifier_id | `{report.classifier_id}` |
| generated_at_utc | `{report.generated_at_utc}` |
| dataset_path | `{report.dataset_path}` |
| dataset_fingerprint | `{report.dataset_fingerprint}` |
| result_path | `{report.result_path}` |
| solar_call_count | {summary.live_solar_call_count} |
| cuda_required | {str(summary.cuda_required).lower()} |

## 정량 리포트

| metric | value |
| --- | ---: |
| query_count | {summary.query_count} |
| query_type_count | {summary.query_type_count} |
| correct_count | {summary.correct_count} |
| accuracy | {summary.accuracy:.6f} |
| macro_precision | {summary.macro_precision:.6f} |
| macro_recall | {summary.macro_recall:.6f} |
| macro_f1 | {summary.macro_f1:.6f} |
| route_policy_correct_count | {summary.route_policy_correct_count} |
| route_policy_accuracy | {summary.route_policy_accuracy:.6f} |
| fallback_count | {summary.fallback_count} |
| fallback_rate | {summary.fallback_rate:.6f} |
| min_confidence | {summary.min_confidence:.6f} |
| average_confidence | {summary.average_confidence:.6f} |

## Query Type Breakdown

| query_type | support | predicted_count | true_positive_count | precision | recall | f1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
{class_rows}

## Confusion Matrix

| expected_query_type | predicted_query_type | count |
| --- | --- | ---: |
{confusion_rows}

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

이 classifier는 Solar Pro 3나 CUDA를 사용하지 않는 deterministic baseline이다. 현재 router skeleton을 실제 API 입력과 연결하기 위한 최소 gate로만 해석한다.

후속 작업에서 오분류 query type이 retrieval 성능을 실제로 떨어뜨리는지 확인해야 한다. 특히 relationship/no_answer 오분류는 route policy 자체가 달라지므로 failure analysis 우선순위가 높다.
"""


def _build_report_from_rows(
    *,
    rows: list[dict[str, Any]],
    dataset_path: Path,
    result_path: Path,
    output_quality: PublicRetrievalArtifactQuality,
    run_id: str,
) -> QueryTypeClassifierEvalReport:
    summary = _summarize_rows(rows)
    return QueryTypeClassifierEvalReport(
        run_id=run_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        dataset_path=public_path_alias(dataset_path),
        dataset_fingerprint=build_dataset_fingerprint(load_retrieval_eval_jsonl(dataset_path)),
        result_path=public_path_alias(result_path),
        summary=summary,
        class_metrics=tuple(_build_class_metrics(rows)),
        confusion_matrix=tuple(_build_confusion_matrix(rows)),
        output_quality=output_quality,
        qualitative_assessment=_build_qualitative_assessment(
            summary=summary,
            output_quality=output_quality,
        ),
    )


def _summarize_rows(rows: list[dict[str, Any]]) -> QueryTypeClassifierEvalSummary:
    query_count = len(rows)
    correct_count = sum(1 for row in rows if row["correct"] is True)
    route_policy_correct_count = sum(
        1 for row in rows if row["route_policy_correct"] is True
    )
    fallback_count = sum(1 for row in rows if row["fallback_used"] is True)
    class_metrics = _build_class_metrics(rows)
    confidences = [float(row["confidence"]) for row in rows]
    return QueryTypeClassifierEvalSummary(
        query_count=query_count,
        query_type_count=len({row["expected_query_type"] for row in rows}),
        correct_count=correct_count,
        accuracy=_ratio(correct_count, query_count),
        macro_precision=_mean([item.precision for item in class_metrics]),
        macro_recall=_mean([item.recall for item in class_metrics]),
        macro_f1=_mean([item.f1 for item in class_metrics]),
        route_policy_correct_count=route_policy_correct_count,
        route_policy_accuracy=_ratio(route_policy_correct_count, query_count),
        fallback_count=fallback_count,
        fallback_rate=_ratio(fallback_count, query_count),
        min_confidence=min(confidences) if confidences else 0.0,
        average_confidence=_mean(confidences),
        live_solar_call_count=0,
        cuda_required=False,
    )


def _build_class_metrics(rows: list[dict[str, Any]]) -> list[QueryTypeClassifierClassMetric]:
    expected_counter = Counter(str(row["expected_query_type"]) for row in rows)
    predicted_counter = Counter(str(row["predicted_query_type"]) for row in rows)
    true_positive_counter = Counter(
        str(row["expected_query_type"])
        for row in rows
        if row["expected_query_type"] == row["predicted_query_type"]
    )
    metrics: list[QueryTypeClassifierClassMetric] = []
    for query_type in REQUIRED_QUERY_TYPES:
        support = expected_counter[query_type]
        predicted_count = predicted_counter[query_type]
        true_positive_count = true_positive_counter[query_type]
        precision = _ratio(true_positive_count, predicted_count)
        recall = _ratio(true_positive_count, support)
        metrics.append(
            QueryTypeClassifierClassMetric(
                query_type=query_type,
                support=support,
                predicted_count=predicted_count,
                true_positive_count=true_positive_count,
                precision=precision,
                recall=recall,
                f1=_f1(precision=precision, recall=recall),
            )
        )
    return metrics


def _build_confusion_matrix(
    rows: list[dict[str, Any]],
) -> list[QueryTypeClassifierConfusionCell]:
    counter = Counter(
        (str(row["expected_query_type"]), str(row["predicted_query_type"]))
        for row in rows
    )
    cells: list[QueryTypeClassifierConfusionCell] = []
    for expected in REQUIRED_QUERY_TYPES:
        for predicted in REQUIRED_QUERY_TYPES:
            count = counter[(expected, predicted)]
            if not count:
                continue
            cells.append(
                QueryTypeClassifierConfusionCell(
                    expected_query_type=expected,
                    predicted_query_type=predicted,
                    count=count,
                )
            )
    return cells


def _build_qualitative_assessment(
    *,
    summary: QueryTypeClassifierEvalSummary,
    output_quality: PublicRetrievalArtifactQuality,
) -> dict[str, str]:
    failures = collect_public_retrieval_artifact_failures(output_quality)
    metric_gate_failures: list[str] = []
    if summary.accuracy < MIN_ACCURACY:
        metric_gate_failures.append("accuracy")
    if summary.macro_f1 < MIN_MACRO_F1:
        metric_gate_failures.append("macro_f1")
    if summary.route_policy_accuracy < MIN_ROUTE_POLICY_ACCURACY:
        metric_gate_failures.append("route_policy_accuracy")
    if summary.fallback_rate > MAX_FALLBACK_RATE:
        metric_gate_failures.append("fallback_rate")
    all_failures = failures + metric_gate_failures
    return {
        "classifier_scope": (
            "deterministic rules로 query type label을 추정하는 baseline contract 평가다."
        ),
        "router_impact": (
            "exact label과 별도로 route policy accuracy를 기록해 default route 내부 오분류와 "
            "relationship/no_answer route 오분류를 분리했다."
        ),
        "security_boundary": (
            "public row와 report에는 query id, query type label, metric만 저장한다."
        ),
        "execution_boundary": (
            "이번 classifier는 Solar Pro 3 호출과 CUDA 연산을 사용하지 않는다."
        ),
        "data_mart_grain": (
            "fact_query_type_classification grain은 run_id + query_id + classifier_id다."
        ),
        "gate_status": "PASS" if not all_failures else f"FAIL: {', '.join(all_failures)}",
        "external_audit": (
            "classifier는 구현됐지만 production routing 품질이나 locked 성능 개선 주장은 아니다."
        ),
    }


def _build_run_id(*, rows: list[dict[str, Any]], classifier_id: str) -> str:
    digest_source = {
        "classifier_id": classifier_id,
        "query_ids": [row["query_id"] for row in rows],
        "expected_query_types": [row["expected_query_type"] for row in rows],
        "predicted_query_types": [row["predicted_query_type"] for row in rows],
    }
    digest = hashlib.sha256(
        json.dumps(digest_source, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:8]
    return f"query-type-classifier-{classifier_id}-q{len(rows)}-{digest}"


def _format_class_metric_row(row: QueryTypeClassifierClassMetric) -> str:
    return (
        f"| `{row.query_type}` | {row.support} | {row.predicted_count} | "
        f"{row.true_positive_count} | {row.precision:.6f} | "
        f"{row.recall:.6f} | {row.f1:.6f} |"
    )


def _format_confusion_row(row: QueryTypeClassifierConfusionCell) -> str:
    return (
        f"| `{row.expected_query_type}` | `{row.predicted_query_type}` | "
        f"{row.count} |"
    )


def _ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 6)


def _f1(*, precision: float, recall: float) -> float:
    if precision + recall == 0.0:
        return 0.0
    return round((2 * precision * recall) / (precision + recall), 6)


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 6)


def main() -> int:
    args = _parse_args()
    build_query_type_classifier_eval_report(
        dataset_path=args.dataset,
        result_path=args.results,
        report_path=args.report,
    )
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run deterministic query type classifier evaluation.",
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULT_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
