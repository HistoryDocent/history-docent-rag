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
from app.application.query_type_route_guard import (
    RELATIONSHIP_ROUTE_GUARD_POLICY_ID,
    RelationshipRouteGuard,
    RelationshipRouteGuardInput,
)
from app.application.query_type_router import QueryTypeRouter
from app.domain.retrieval import QueryType, load_retrieval_eval_jsonl
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    build_dataset_fingerprint,
    collect_public_retrieval_artifact_failures,
    measure_public_retrieval_artifact_quality,
    public_path_alias,
    write_public_retrieval_result_rows,
)


RELATIONSHIP_ROUTE_GUARD_EVAL_REPORT_VERSION = "relationship-route-guard-eval-report/v1"
DEFAULT_DATASET_PATH = Path("private_data/evals/datasets/retrieval_eval_dev.jsonl")
DEFAULT_RESULT_PATH = Path(
    "private_data/evals/results/relationship_route_guard_eval_rows.jsonl"
)
DEFAULT_REPORT_PATH = Path("evals/reports/relationship_route_guard_eval_report.md")


class RelationshipRouteGuardEvalModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RelationshipRouteGuardEvalSummary(RelationshipRouteGuardEvalModel):
    query_count: int = Field(ge=0)
    baseline_correct_count: int = Field(ge=0)
    guarded_correct_count: int = Field(ge=0)
    baseline_accuracy: float = Field(ge=0.0, le=1.0)
    guarded_accuracy: float = Field(ge=0.0, le=1.0)
    accuracy_delta: float
    baseline_route_policy_correct_count: int = Field(ge=0)
    guarded_route_policy_correct_count: int = Field(ge=0)
    baseline_route_policy_accuracy: float = Field(ge=0.0, le=1.0)
    guarded_route_policy_accuracy: float = Field(ge=0.0, le=1.0)
    route_policy_accuracy_delta: float
    baseline_false_hybrid_route_count: int = Field(ge=0)
    guarded_false_hybrid_route_count: int = Field(ge=0)
    false_hybrid_route_delta: int
    baseline_missed_hybrid_route_count: int = Field(ge=0)
    guarded_missed_hybrid_route_count: int = Field(ge=0)
    no_answer_route_regression_count: int = Field(ge=0)
    guard_applied_count: int = Field(ge=0)
    active_route_applied_count: int = Field(ge=0)
    live_solar_call_count: int = Field(ge=0)
    cuda_required: bool = False


class RelationshipRouteGuardTagSummary(RelationshipRouteGuardEvalModel):
    tag: str = Field(min_length=1)
    count: int = Field(ge=0)


class RelationshipRouteGuardEvalReport(RelationshipRouteGuardEvalModel):
    report_version: str = RELATIONSHIP_ROUTE_GUARD_EVAL_REPORT_VERSION
    run_id: str
    generated_at_utc: str
    classifier_id: str = QUERY_TYPE_CLASSIFIER_ID
    guard_policy_id: str = RELATIONSHIP_ROUTE_GUARD_POLICY_ID
    dataset_path: str
    dataset_fingerprint: str = Field(min_length=8)
    result_path: str
    summary: RelationshipRouteGuardEvalSummary
    guard_tag_breakdown: tuple[RelationshipRouteGuardTagSummary, ...]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def build_relationship_route_guard_eval_report(
    *,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    result_path: Path = DEFAULT_RESULT_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
) -> RelationshipRouteGuardEvalReport:
    items = load_retrieval_eval_jsonl(dataset_path)
    classifier = DeterministicQueryTypeClassifier()
    guard = RelationshipRouteGuard()
    router = QueryTypeRouter()
    rows: list[dict[str, Any]] = []
    for item in items:
        classification = classifier.classify(
            QueryTypeClassificationInput(
                query_text=item.query.query_text,
                user_context=item.query.user_context,
                place_ids=tuple(item.metadata.place_ids),
                has_dialog_context=item.metadata.requires_context,
            )
        )
        guard_decision = guard.apply(
            RelationshipRouteGuardInput(
                query_text=item.query.query_text,
                classification=classification,
            )
        )
        expected_query_type = item.query.query_type
        expected_route = router.route(expected_query_type).route_policy_id
        baseline_route = router.route(classification.predicted_query_type).route_policy_id
        guarded_route = router.route(guard_decision.guarded_query_type).route_policy_id
        rows.append(
            {
                "query_id": item.query.query_id,
                "expected_query_type": expected_query_type,
                "baseline_predicted_query_type": classification.predicted_query_type,
                "guarded_query_type": guard_decision.guarded_query_type,
                "expected_route_policy_id": expected_route,
                "baseline_route_policy_id": baseline_route,
                "guarded_route_policy_id": guarded_route,
                "baseline_correct": expected_query_type == classification.predicted_query_type,
                "guarded_correct": expected_query_type == guard_decision.guarded_query_type,
                "baseline_route_policy_correct": expected_route == baseline_route,
                "guarded_route_policy_correct": expected_route == guarded_route,
                "baseline_false_hybrid_route": _is_false_hybrid(
                    expected_query_type=expected_query_type,
                    predicted_query_type=classification.predicted_query_type,
                ),
                "guarded_false_hybrid_route": _is_false_hybrid(
                    expected_query_type=expected_query_type,
                    predicted_query_type=guard_decision.guarded_query_type,
                ),
                "baseline_missed_hybrid_route": _is_missed_hybrid(
                    expected_query_type=expected_query_type,
                    predicted_query_type=classification.predicted_query_type,
                ),
                "guarded_missed_hybrid_route": _is_missed_hybrid(
                    expected_query_type=expected_query_type,
                    predicted_query_type=guard_decision.guarded_query_type,
                ),
                "no_answer_route_regression": _is_no_answer_route_regression(
                    expected_query_type=expected_query_type,
                    guarded_query_type=guard_decision.guarded_query_type,
                ),
                "guard_applied": guard_decision.guard_applied,
                "guard_reason_tags": guard_decision.guard_reason_tags,
                "relationship_score": guard_decision.relationship_score,
                "fallback_query_type": guard_decision.fallback_query_type,
                "fallback_score": guard_decision.fallback_score,
                "score_margin": guard_decision.score_margin,
                "confidence": classification.confidence,
                "matched_rule_count": len(classification.matched_rule_ids),
                "active_route_applied": False,
            }
        )

    run_id = _build_run_id(rows=rows)
    write_public_retrieval_result_rows(path=result_path, rows=rows)
    provisional_quality = measure_public_retrieval_artifact_quality(
        report_version=RELATIONSHIP_ROUTE_GUARD_EVAL_REPORT_VERSION,
        run_id=run_id,
        result_rows=rows,
        report_text="",
    )
    provisional = _build_report_from_rows(
        rows=rows,
        dataset_path=dataset_path,
        result_path=result_path,
        output_quality=provisional_quality,
        run_id=run_id,
    )
    report_text = build_relationship_route_guard_eval_report_markdown(provisional)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=RELATIONSHIP_ROUTE_GUARD_EVAL_REPORT_VERSION,
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
    failures = collect_relationship_route_guard_eval_failures(report)
    if failures:
        raise ValueError(f"relationship route guard eval gate failed: {failures}")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        build_relationship_route_guard_eval_report_markdown(report),
        encoding="utf-8",
    )
    print(
        "relationship_route_guard_eval "
        "status=PASS "
        f"query_count={report.summary.query_count} "
        f"baseline_false_hybrid={report.summary.baseline_false_hybrid_route_count} "
        f"guarded_false_hybrid={report.summary.guarded_false_hybrid_route_count} "
        f"guarded_route_policy_accuracy={report.summary.guarded_route_policy_accuracy:.6f}"
    )
    return report


def collect_relationship_route_guard_eval_failures(
    report: RelationshipRouteGuardEvalReport,
) -> list[str]:
    failures = collect_public_retrieval_artifact_failures(report.output_quality)
    summary = report.summary
    if summary.query_count <= 0:
        failures.append("empty_query_set")
    if summary.guarded_false_hybrid_route_count > summary.baseline_false_hybrid_route_count:
        failures.append("false_hybrid_route_regression")
    if summary.guarded_missed_hybrid_route_count > summary.baseline_missed_hybrid_route_count:
        failures.append("missed_hybrid_route_regression")
    if summary.guarded_route_policy_accuracy < summary.baseline_route_policy_accuracy:
        failures.append("route_policy_accuracy_regression")
    if summary.no_answer_route_regression_count:
        failures.append("no_answer_route_regression")
    if summary.active_route_applied_count:
        failures.append("active_route_applied")
    if summary.live_solar_call_count:
        failures.append("live_solar_call_detected")
    if summary.cuda_required:
        failures.append("unexpected_cuda_requirement")
    return failures


def build_relationship_route_guard_eval_report_markdown(
    report: RelationshipRouteGuardEvalReport,
) -> str:
    summary = report.summary
    quality = report.output_quality
    tag_rows = "\n".join(_format_tag_row(row) for row in report.guard_tag_breakdown)
    if not tag_rows:
        tag_rows = "| - | 0 |"
    qualitative_rows = "\n".join(
        f"- `{key}`: {value}" for key, value in report.qualitative_assessment.items()
    )
    return f"""# Relationship Route Guard Eval Report

## 목적

`HD-CLASSIFIER-005`는 classifier가 `relationship`을 예측했을 때 hybrid route로 바로 보내기 전 보수적 guard가 false hybrid route를 줄이는지 검증한다.

이 문서는 classifier/router guard 평가다. active routing 적용, retrieval 성능 개선, locked test 개선, Solar Pro 3 답변 품질 개선 주장이 아니다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| run_id | `{report.run_id}` |
| classifier_id | `{report.classifier_id}` |
| guard_policy_id | `{report.guard_policy_id}` |
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
| baseline_correct_count | {summary.baseline_correct_count} |
| guarded_correct_count | {summary.guarded_correct_count} |
| baseline_accuracy | {summary.baseline_accuracy:.6f} |
| guarded_accuracy | {summary.guarded_accuracy:.6f} |
| accuracy_delta | {summary.accuracy_delta:.6f} |
| baseline_route_policy_correct_count | {summary.baseline_route_policy_correct_count} |
| guarded_route_policy_correct_count | {summary.guarded_route_policy_correct_count} |
| baseline_route_policy_accuracy | {summary.baseline_route_policy_accuracy:.6f} |
| guarded_route_policy_accuracy | {summary.guarded_route_policy_accuracy:.6f} |
| route_policy_accuracy_delta | {summary.route_policy_accuracy_delta:.6f} |
| baseline_false_hybrid_route_count | {summary.baseline_false_hybrid_route_count} |
| guarded_false_hybrid_route_count | {summary.guarded_false_hybrid_route_count} |
| false_hybrid_route_delta | {summary.false_hybrid_route_delta} |
| baseline_missed_hybrid_route_count | {summary.baseline_missed_hybrid_route_count} |
| guarded_missed_hybrid_route_count | {summary.guarded_missed_hybrid_route_count} |
| no_answer_route_regression_count | {summary.no_answer_route_regression_count} |
| guard_applied_count | {summary.guard_applied_count} |
| active_route_applied_count | {summary.active_route_applied_count} |

## Guard Tag Breakdown

| tag | count |
| --- | ---: |
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

## 해석

relationship route guard는 active route 적용 전 안전장치다. 이번 결과가 좋아도 production routing 완료나 최종 성능 개선으로 표현하지 않는다.

다음 단계는 API dry-run field에 guarded route 후보를 노출하거나, 더 넓은 dev/test set에서 guard regression을 확인하는 것이다.
"""


def _build_report_from_rows(
    *,
    rows: list[dict[str, Any]],
    dataset_path: Path,
    result_path: Path,
    output_quality: PublicRetrievalArtifactQuality,
    run_id: str,
) -> RelationshipRouteGuardEvalReport:
    summary = _summarize_rows(rows)
    return RelationshipRouteGuardEvalReport(
        run_id=run_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        dataset_path=public_path_alias(dataset_path),
        dataset_fingerprint=build_dataset_fingerprint(load_retrieval_eval_jsonl(dataset_path)),
        result_path=public_path_alias(result_path),
        summary=summary,
        guard_tag_breakdown=tuple(_build_guard_tag_breakdown(rows)),
        output_quality=output_quality,
        qualitative_assessment=_build_qualitative_assessment(
            summary=summary,
            output_quality=output_quality,
        ),
    )


def _summarize_rows(rows: list[dict[str, Any]]) -> RelationshipRouteGuardEvalSummary:
    query_count = len(rows)
    baseline_correct_count = _count_true(rows, "baseline_correct")
    guarded_correct_count = _count_true(rows, "guarded_correct")
    baseline_route_policy_correct_count = _count_true(rows, "baseline_route_policy_correct")
    guarded_route_policy_correct_count = _count_true(rows, "guarded_route_policy_correct")
    baseline_false_hybrid_route_count = _count_true(rows, "baseline_false_hybrid_route")
    guarded_false_hybrid_route_count = _count_true(rows, "guarded_false_hybrid_route")
    baseline_missed_hybrid_route_count = _count_true(rows, "baseline_missed_hybrid_route")
    guarded_missed_hybrid_route_count = _count_true(rows, "guarded_missed_hybrid_route")
    baseline_accuracy = _ratio(baseline_correct_count, query_count)
    guarded_accuracy = _ratio(guarded_correct_count, query_count)
    baseline_route_policy_accuracy = _ratio(
        baseline_route_policy_correct_count,
        query_count,
    )
    guarded_route_policy_accuracy = _ratio(
        guarded_route_policy_correct_count,
        query_count,
    )
    return RelationshipRouteGuardEvalSummary(
        query_count=query_count,
        baseline_correct_count=baseline_correct_count,
        guarded_correct_count=guarded_correct_count,
        baseline_accuracy=baseline_accuracy,
        guarded_accuracy=guarded_accuracy,
        accuracy_delta=round(guarded_accuracy - baseline_accuracy, 6),
        baseline_route_policy_correct_count=baseline_route_policy_correct_count,
        guarded_route_policy_correct_count=guarded_route_policy_correct_count,
        baseline_route_policy_accuracy=baseline_route_policy_accuracy,
        guarded_route_policy_accuracy=guarded_route_policy_accuracy,
        route_policy_accuracy_delta=round(
            guarded_route_policy_accuracy - baseline_route_policy_accuracy,
            6,
        ),
        baseline_false_hybrid_route_count=baseline_false_hybrid_route_count,
        guarded_false_hybrid_route_count=guarded_false_hybrid_route_count,
        false_hybrid_route_delta=(
            guarded_false_hybrid_route_count - baseline_false_hybrid_route_count
        ),
        baseline_missed_hybrid_route_count=baseline_missed_hybrid_route_count,
        guarded_missed_hybrid_route_count=guarded_missed_hybrid_route_count,
        no_answer_route_regression_count=_count_true(rows, "no_answer_route_regression"),
        guard_applied_count=_count_true(rows, "guard_applied"),
        active_route_applied_count=_count_true(rows, "active_route_applied"),
        live_solar_call_count=0,
        cuda_required=False,
    )


def _build_guard_tag_breakdown(
    rows: list[dict[str, Any]],
) -> list[RelationshipRouteGuardTagSummary]:
    counter: Counter[str] = Counter(
        tag for row in rows for tag in row.get("guard_reason_tags", ())
    )
    return [
        RelationshipRouteGuardTagSummary(tag=tag, count=count)
        for tag, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    ]


def _build_qualitative_assessment(
    *,
    summary: RelationshipRouteGuardEvalSummary,
    output_quality: PublicRetrievalArtifactQuality,
) -> dict[str, str]:
    failures = collect_public_retrieval_artifact_failures(output_quality)
    guard_effect = (
        f"false hybrid route는 {summary.baseline_false_hybrid_route_count}건에서 "
        f"{summary.guarded_false_hybrid_route_count}건으로 변했다."
    )
    return {
        "guard_scope": (
            "`relationship` 예측에만 보수적 guard를 적용한다. 다른 query type은 변경하지 않는다."
        ),
        "guard_effect": guard_effect,
        "regression_boundary": (
            "missed hybrid, no-answer route regression, route policy accuracy regression을 gate로 본다."
        ),
        "api_boundary": (
            "이번 평가는 active route 적용이 아니다. API active_route_applied는 0이어야 한다."
        ),
        "security_boundary": (
            "result row와 report에는 query id, label, route id, score, guard tag만 저장한다."
        ),
        "execution_boundary": (
            "deterministic CPU 평가다. Solar Pro 3 호출과 CUDA 연산을 사용하지 않는다."
        ),
        "data_mart_grain": (
            "fact_relationship_route_guard_eval grain은 run_id + query_id + guard_policy_id다."
        ),
        "gate_status": "PASS" if not failures else f"FAIL: {', '.join(failures)}",
        "external_audit": (
            "guard가 false hybrid를 줄여도 production routing 완료로 표현하면 안 된다."
        ),
    }


def _is_false_hybrid(
    *,
    expected_query_type: QueryType,
    predicted_query_type: QueryType,
) -> bool:
    return predicted_query_type == "relationship" and expected_query_type != "relationship"


def _is_missed_hybrid(
    *,
    expected_query_type: QueryType,
    predicted_query_type: QueryType,
) -> bool:
    return expected_query_type == "relationship" and predicted_query_type != "relationship"


def _is_no_answer_route_regression(
    *,
    expected_query_type: QueryType,
    guarded_query_type: QueryType,
) -> bool:
    return (expected_query_type == "no_answer") != (guarded_query_type == "no_answer")


def _build_run_id(*, rows: list[dict[str, Any]]) -> str:
    digest_source = {
        "guard_policy_id": RELATIONSHIP_ROUTE_GUARD_POLICY_ID,
        "query_ids": [row["query_id"] for row in rows],
        "baseline_predicted_query_types": [
            row["baseline_predicted_query_type"] for row in rows
        ],
        "guarded_query_types": [row["guarded_query_type"] for row in rows],
    }
    digest = hashlib.sha256(
        json.dumps(digest_source, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:8]
    return f"relationship-route-guard-q{len(rows)}-{digest}"


def _format_tag_row(row: RelationshipRouteGuardTagSummary) -> str:
    return f"| `{row.tag}` | {row.count} |"


def _count_true(rows: list[dict[str, Any]], field: str) -> int:
    return sum(1 for row in rows if row.get(field) is True)


def _ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 6)


def main() -> int:
    args = _parse_args()
    build_relationship_route_guard_eval_report(
        dataset_path=args.dataset,
        result_path=args.results,
        report_path=args.report,
    )
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run relationship route guard evaluation.",
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULT_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
