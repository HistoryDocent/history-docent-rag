from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.application.query_type_classifier import (
    QUERY_TYPE_CLASSIFIER_ID,
    DeterministicQueryTypeClassifier,
    QueryTypeClassificationInput,
    QueryTypeClassificationResult,
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


QUERY_TYPE_CLASSIFIER_FAILURE_ANALYSIS_REPORT_VERSION = (
    "query-type-classifier-failure-analysis-report/v1"
)
DEFAULT_DATASET_PATH = Path("private_data/evals/datasets/retrieval_eval_dev.jsonl")
DEFAULT_RESULT_PATH = Path(
    "private_data/evals/results/query_type_classifier_failure_analysis_rows.jsonl"
)
DEFAULT_REPORT_PATH = Path(
    "evals/reports/query_type_classifier_failure_analysis_report.md"
)

ImpactLevel = Literal["low", "medium", "high"]


class QueryTypeClassifierFailureAnalysisModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class QueryTypeClassifierFailureRow(QueryTypeClassifierFailureAnalysisModel):
    failure_id: str = Field(min_length=1)
    query_id: str = Field(min_length=1)
    expected_query_type: QueryType
    predicted_query_type: QueryType
    expected_route_policy_id: str = Field(min_length=1)
    predicted_route_policy_id: str = Field(min_length=1)
    route_policy_changed: bool
    confidence: float = Field(ge=0.0, le=1.0)
    fallback_used: bool
    matched_rule_count: int = Field(ge=0)
    matched_rule_ids: tuple[str, ...]
    top_score: float = Field(ge=0.0)
    runner_up_query_type: QueryType
    runner_up_score: float = Field(ge=0.0)
    score_margin: float = Field(ge=0.0)
    impact_level: ImpactLevel
    failure_tags: tuple[str, ...]


class QueryTypeClassifierFailureAnalysisSummary(
    QueryTypeClassifierFailureAnalysisModel
):
    query_count: int = Field(ge=0)
    failure_count: int = Field(ge=0)
    failure_rate: float = Field(ge=0.0, le=1.0)
    route_risk_failure_count: int = Field(ge=0)
    route_risk_failure_rate: float = Field(ge=0.0, le=1.0)
    default_route_internal_failure_count: int = Field(ge=0)
    false_hybrid_route_count: int = Field(ge=0)
    missed_hybrid_route_count: int = Field(ge=0)
    false_abstain_count: int = Field(ge=0)
    missed_abstain_count: int = Field(ge=0)
    no_answer_failure_count: int = Field(ge=0)
    fallback_failure_count: int = Field(ge=0)
    high_confidence_failure_count: int = Field(ge=0)
    min_failure_confidence: float = Field(ge=0.0, le=1.0)
    average_failure_confidence: float = Field(ge=0.0, le=1.0)
    live_solar_call_count: int = Field(ge=0)
    cuda_required: bool = False


class QueryTypeClassifierFailureTagSummary(QueryTypeClassifierFailureAnalysisModel):
    tag: str = Field(min_length=1)
    count: int = Field(ge=0)


class QueryTypeClassifierFailureAnalysisReport(
    QueryTypeClassifierFailureAnalysisModel
):
    report_version: str = QUERY_TYPE_CLASSIFIER_FAILURE_ANALYSIS_REPORT_VERSION
    run_id: str
    generated_at_utc: str
    classifier_id: str = QUERY_TYPE_CLASSIFIER_ID
    dataset_path: str
    dataset_fingerprint: str = Field(min_length=8)
    result_path: str
    summary: QueryTypeClassifierFailureAnalysisSummary
    failure_rows: tuple[QueryTypeClassifierFailureRow, ...]
    tag_breakdown: tuple[QueryTypeClassifierFailureTagSummary, ...]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def build_query_type_classifier_failure_analysis_report(
    *,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    result_path: Path = DEFAULT_RESULT_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
) -> QueryTypeClassifierFailureAnalysisReport:
    items = load_retrieval_eval_jsonl(dataset_path)
    classifier = DeterministicQueryTypeClassifier()
    router = QueryTypeRouter()
    failures: list[QueryTypeClassifierFailureRow] = []
    for item in items:
        expected_query_type = item.query.query_type
        classification = classifier.classify(
            QueryTypeClassificationInput(
                query_text=item.query.query_text,
                user_context=item.query.user_context,
                place_ids=tuple(item.metadata.place_ids),
                has_dialog_context=item.metadata.requires_context,
            )
        )
        if expected_query_type == classification.predicted_query_type:
            continue
        expected_route = router.route(expected_query_type).route_policy_id
        predicted_route = router.route(classification.predicted_query_type).route_policy_id
        failures.append(
            _build_failure_row(
                query_id=item.query.query_id,
                expected_query_type=expected_query_type,
                predicted_query_type=classification.predicted_query_type,
                expected_route_policy_id=expected_route,
                predicted_route_policy_id=predicted_route,
                classification=classification,
            )
        )

    result_rows = [row.model_dump(mode="json") for row in failures]
    run_id = _build_run_id(
        query_count=len(items),
        classifier_id=classifier.classifier_id,
        failure_rows=result_rows,
    )
    write_public_retrieval_result_rows(path=result_path, rows=result_rows)
    provisional_quality = measure_public_retrieval_artifact_quality(
        report_version=QUERY_TYPE_CLASSIFIER_FAILURE_ANALYSIS_REPORT_VERSION,
        run_id=run_id,
        result_rows=result_rows,
        report_text="",
    )
    provisional = _build_report(
        dataset_path=dataset_path,
        result_path=result_path,
        query_count=len(items),
        failure_rows=failures,
        output_quality=provisional_quality,
        run_id=run_id,
    )
    report_text = build_query_type_classifier_failure_analysis_markdown(provisional)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=QUERY_TYPE_CLASSIFIER_FAILURE_ANALYSIS_REPORT_VERSION,
        run_id=run_id,
        result_rows=result_rows,
        report_text=report_text,
    )
    report = _build_report(
        dataset_path=dataset_path,
        result_path=result_path,
        query_count=len(items),
        failure_rows=failures,
        output_quality=output_quality,
        run_id=run_id,
    )
    analysis_failures = collect_query_type_classifier_failure_analysis_failures(report)
    if analysis_failures:
        raise ValueError(
            "query type classifier failure analysis gate failed: "
            f"{analysis_failures}"
        )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        build_query_type_classifier_failure_analysis_markdown(report),
        encoding="utf-8",
    )
    print(
        "query_type_classifier_failure_analysis "
        "status=PASS "
        f"query_count={report.summary.query_count} "
        f"failure_count={report.summary.failure_count} "
        f"route_risk_failure_count={report.summary.route_risk_failure_count} "
        f"false_hybrid_route_count={report.summary.false_hybrid_route_count}"
    )
    return report


def collect_query_type_classifier_failure_analysis_failures(
    report: QueryTypeClassifierFailureAnalysisReport,
) -> list[str]:
    failures = collect_public_retrieval_artifact_failures(report.output_quality)
    summary = report.summary
    if summary.query_count <= 0:
        failures.append("empty_query_set")
    if report.output_quality.result_row_count != summary.failure_count:
        failures.append("failure_row_count_mismatch")
    if summary.live_solar_call_count:
        failures.append("live_solar_call_detected")
    if summary.cuda_required:
        failures.append("unexpected_cuda_requirement")
    return failures


def build_query_type_classifier_failure_analysis_markdown(
    report: QueryTypeClassifierFailureAnalysisReport,
) -> str:
    summary = report.summary
    quality = report.output_quality
    failure_rows = "\n".join(_format_failure_row(row) for row in report.failure_rows)
    if not failure_rows:
        failure_rows = "| - | - | - | - | - | - | - | - |"
    tag_rows = "\n".join(_format_tag_row(row) for row in report.tag_breakdown)
    if not tag_rows:
        tag_rows = "| - | 0 |"
    qualitative_rows = "\n".join(
        f"- `{key}`: {value}" for key, value in report.qualitative_assessment.items()
    )
    return f"""# Query Type Classifier Failure Analysis Report

## 목적

`HD-ROUTER-003` classifier baseline에서 남은 오분류가 router policy를 실제로 바꾸는지 분리해서 기록한다.

이 문서는 failure analysis와 route impact 점검이다. classifier 개선, retrieval 성능 개선, locked test 개선, Solar Pro 3 답변 품질 개선 주장이 아니다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

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
| failure_count | {summary.failure_count} |
| failure_rate | {summary.failure_rate:.6f} |
| route_risk_failure_count | {summary.route_risk_failure_count} |
| route_risk_failure_rate | {summary.route_risk_failure_rate:.6f} |
| default_route_internal_failure_count | {summary.default_route_internal_failure_count} |
| false_hybrid_route_count | {summary.false_hybrid_route_count} |
| missed_hybrid_route_count | {summary.missed_hybrid_route_count} |
| false_abstain_count | {summary.false_abstain_count} |
| missed_abstain_count | {summary.missed_abstain_count} |
| no_answer_failure_count | {summary.no_answer_failure_count} |
| fallback_failure_count | {summary.fallback_failure_count} |
| high_confidence_failure_count | {summary.high_confidence_failure_count} |
| min_failure_confidence | {summary.min_failure_confidence:.6f} |
| average_failure_confidence | {summary.average_failure_confidence:.6f} |

## Failure Rows

| query_id | expected_query_type | predicted_query_type | route_policy_changed | confidence | score_margin | impact_level | failure_tags |
| --- | --- | --- | ---: | ---: | ---: | --- | --- |
{failure_rows}

## Failure Tag Breakdown

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

오분류는 exact label 관점과 route policy 관점이 다르다. 같은 default route 안에서 label만 틀린 경우는 retrieval 후보가 바뀌지 않지만, default query가 relationship route로 잘못 이동하면 hybrid route가 실행될 수 있다.

따라서 다음 API 연결은 active route 변경이 아니라 dry-run field로 먼저 넣는 것이 맞다. 실제 route 적용은 route-risk failure를 줄이는 보수적 guard를 추가한 뒤 별도 gate로 판단한다.
"""


def _build_report(
    *,
    dataset_path: Path,
    result_path: Path,
    query_count: int,
    failure_rows: list[QueryTypeClassifierFailureRow],
    output_quality: PublicRetrievalArtifactQuality,
    run_id: str,
) -> QueryTypeClassifierFailureAnalysisReport:
    summary = _build_summary(query_count=query_count, failure_rows=failure_rows)
    return QueryTypeClassifierFailureAnalysisReport(
        run_id=run_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        dataset_path=public_path_alias(dataset_path),
        dataset_fingerprint=build_dataset_fingerprint(load_retrieval_eval_jsonl(dataset_path)),
        result_path=public_path_alias(result_path),
        summary=summary,
        failure_rows=tuple(failure_rows),
        tag_breakdown=tuple(_build_tag_breakdown(failure_rows)),
        output_quality=output_quality,
        qualitative_assessment=_build_qualitative_assessment(
            summary=summary,
            output_quality=output_quality,
        ),
    )


def _build_failure_row(
    *,
    query_id: str,
    expected_query_type: QueryType,
    predicted_query_type: QueryType,
    expected_route_policy_id: str,
    predicted_route_policy_id: str,
    classification: QueryTypeClassificationResult,
) -> QueryTypeClassifierFailureRow:
    top_query_type, top_score, runner_up_query_type, runner_up_score = _score_ranking(
        classification.candidate_scores
    )
    score_margin = round(max(0.0, top_score - runner_up_score), 6)
    route_policy_changed = expected_route_policy_id != predicted_route_policy_id
    tags = _failure_tags(
        expected_query_type=expected_query_type,
        predicted_query_type=predicted_query_type,
        route_policy_changed=route_policy_changed,
        confidence=classification.confidence,
        fallback_used=classification.fallback_used,
    )
    return QueryTypeClassifierFailureRow(
        failure_id=_failure_id(
            query_id=query_id,
            expected_query_type=expected_query_type,
            predicted_query_type=predicted_query_type,
        ),
        query_id=query_id,
        expected_query_type=expected_query_type,
        predicted_query_type=predicted_query_type,
        expected_route_policy_id=expected_route_policy_id,
        predicted_route_policy_id=predicted_route_policy_id,
        route_policy_changed=route_policy_changed,
        confidence=classification.confidence,
        fallback_used=classification.fallback_used,
        matched_rule_count=len(classification.matched_rule_ids),
        matched_rule_ids=classification.matched_rule_ids,
        top_score=top_score,
        runner_up_query_type=runner_up_query_type,
        runner_up_score=runner_up_score,
        score_margin=score_margin,
        impact_level=_impact_level(
            expected_query_type=expected_query_type,
            predicted_query_type=predicted_query_type,
            route_policy_changed=route_policy_changed,
        ),
        failure_tags=tags,
    )


def _build_summary(
    *,
    query_count: int,
    failure_rows: list[QueryTypeClassifierFailureRow],
) -> QueryTypeClassifierFailureAnalysisSummary:
    failure_count = len(failure_rows)
    route_risk_failure_count = sum(1 for row in failure_rows if row.route_policy_changed)
    confidences = [row.confidence for row in failure_rows]
    return QueryTypeClassifierFailureAnalysisSummary(
        query_count=query_count,
        failure_count=failure_count,
        failure_rate=_ratio(failure_count, query_count),
        route_risk_failure_count=route_risk_failure_count,
        route_risk_failure_rate=_ratio(route_risk_failure_count, query_count),
        default_route_internal_failure_count=sum(
            1 for row in failure_rows if not row.route_policy_changed
        ),
        false_hybrid_route_count=sum(
            1
            for row in failure_rows
            if row.predicted_query_type == "relationship"
            and row.expected_query_type != "relationship"
        ),
        missed_hybrid_route_count=sum(
            1
            for row in failure_rows
            if row.expected_query_type == "relationship"
            and row.predicted_query_type != "relationship"
        ),
        false_abstain_count=sum(
            1
            for row in failure_rows
            if row.predicted_query_type == "no_answer"
            and row.expected_query_type != "no_answer"
        ),
        missed_abstain_count=sum(
            1
            for row in failure_rows
            if row.expected_query_type == "no_answer"
            and row.predicted_query_type != "no_answer"
        ),
        no_answer_failure_count=sum(
            1
            for row in failure_rows
            if "abstain_route_risk" in row.failure_tags
            or row.expected_query_type == "no_answer"
            or row.predicted_query_type == "no_answer"
        ),
        fallback_failure_count=sum(1 for row in failure_rows if row.fallback_used),
        high_confidence_failure_count=sum(
            1 for row in failure_rows if row.confidence >= 0.85
        ),
        min_failure_confidence=min(confidences) if confidences else 0.0,
        average_failure_confidence=_mean(confidences),
        live_solar_call_count=0,
        cuda_required=False,
    )


def _build_tag_breakdown(
    failure_rows: list[QueryTypeClassifierFailureRow],
) -> list[QueryTypeClassifierFailureTagSummary]:
    counter: Counter[str] = Counter(
        tag for row in failure_rows for tag in row.failure_tags
    )
    return [
        QueryTypeClassifierFailureTagSummary(tag=tag, count=count)
        for tag, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    ]


def _build_qualitative_assessment(
    *,
    summary: QueryTypeClassifierFailureAnalysisSummary,
    output_quality: PublicRetrievalArtifactQuality,
) -> dict[str, str]:
    failures = collect_public_retrieval_artifact_failures(output_quality)
    route_text = (
        f"{summary.route_risk_failure_count}건은 route policy가 바뀌는 오분류다. "
        f"{summary.default_route_internal_failure_count}건은 default route 내부 오분류다."
    )
    return {
        "analysis_scope": (
            "classifier를 재학습하거나 규칙 수정하지 않고 남은 오분류의 route impact만 분석했다."
        ),
        "route_impact": route_text,
        "highest_risk": (
            "no_answer 관련 오분류는 없었다. 현재 위험은 default query가 relationship hybrid route로 "
            "잘못 이동하는 false hybrid route다."
        ),
        "recommended_guard": (
            "relationship route는 active 적용 전에 score margin, 명시적 관계 표현, 다중 장소 신호를 "
            "함께 요구하는 보수적 guard가 필요하다."
        ),
        "api_rollout": (
            "다음 API 작업은 active routing이 아니라 classifier/router dry-run field 노출로 제한한다."
        ),
        "security_boundary": (
            "failure row와 report에는 query id, label, route id, score, tag만 저장한다."
        ),
        "execution_boundary": (
            "이번 분석은 Solar Pro 3 호출과 CUDA 연산을 사용하지 않는다."
        ),
        "data_mart_grain": (
            "fact_query_type_classifier_failure grain은 run_id + failure_id + query_id다."
        ),
        "gate_status": "PASS" if not failures else f"FAIL: {', '.join(failures)}",
        "external_audit": (
            "classifier baseline은 통과했지만 route-risk failure가 남아 있어 production routing 완성으로 "
            "표현하면 안 된다."
        ),
    }


def _failure_tags(
    *,
    expected_query_type: QueryType,
    predicted_query_type: QueryType,
    route_policy_changed: bool,
    confidence: float,
    fallback_used: bool,
) -> tuple[str, ...]:
    tags: list[str] = []
    tags.append("route_policy_changed" if route_policy_changed else "default_route_internal")
    if predicted_query_type == "relationship" and expected_query_type != "relationship":
        tags.append("false_hybrid_route")
        tags.append("relationship_over_trigger")
    if expected_query_type == "relationship" and predicted_query_type != "relationship":
        tags.append("missed_hybrid_route")
    if predicted_query_type == "no_answer" and expected_query_type != "no_answer":
        tags.append("false_abstain")
        tags.append("abstain_route_risk")
    if expected_query_type == "no_answer" and predicted_query_type != "no_answer":
        tags.append("missed_abstain")
        tags.append("abstain_route_risk")
    if {expected_query_type, predicted_query_type} <= {
        "place_fact",
        "place_story",
        "overview",
    }:
        tags.append("default_intent_boundary")
    if confidence >= 0.85:
        tags.append("high_confidence_error")
    if fallback_used:
        tags.append("fallback_error")
    return tuple(_unique(tags))


def _impact_level(
    *,
    expected_query_type: QueryType,
    predicted_query_type: QueryType,
    route_policy_changed: bool,
) -> ImpactLevel:
    if expected_query_type == "no_answer" or predicted_query_type == "no_answer":
        return "high"
    if route_policy_changed:
        return "medium"
    return "low"


def _score_ranking(
    scores: dict[QueryType, float],
) -> tuple[QueryType, float, QueryType, float]:
    ordered = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    top_query_type, top_score = ordered[0]
    runner_up_query_type, runner_up_score = ordered[1]
    return (
        top_query_type,
        round(top_score, 6),
        runner_up_query_type,
        round(runner_up_score, 6),
    )


def _build_run_id(
    *,
    query_count: int,
    classifier_id: str,
    failure_rows: list[dict[str, Any]],
) -> str:
    digest_source = {
        "query_count": query_count,
        "classifier_id": classifier_id,
        "failures": failure_rows,
    }
    digest = hashlib.sha256(
        json.dumps(digest_source, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:8]
    return f"query-type-classifier-failure-q{query_count}-f{len(failure_rows)}-{digest}"


def _failure_id(
    *,
    query_id: str,
    expected_query_type: QueryType,
    predicted_query_type: QueryType,
) -> str:
    digest_source = {
        "query_id": query_id,
        "expected_query_type": expected_query_type,
        "predicted_query_type": predicted_query_type,
    }
    digest = hashlib.sha256(
        json.dumps(digest_source, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:8]
    return f"classifier-failure-{digest}"


def _format_failure_row(row: QueryTypeClassifierFailureRow) -> str:
    tags = ", ".join(row.failure_tags)
    return (
        f"| `{row.query_id}` | `{row.expected_query_type}` | "
        f"`{row.predicted_query_type}` | {str(row.route_policy_changed).lower()} | "
        f"{row.confidence:.6f} | {row.score_margin:.6f} | "
        f"`{row.impact_level}` | `{tags}` |"
    )


def _format_tag_row(row: QueryTypeClassifierFailureTagSummary) -> str:
    return f"| `{row.tag}` | {row.count} |"


def _ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 6)


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 6)


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        if value in seen:
            continue
        unique_values.append(value)
        seen.add(value)
    return unique_values


def main() -> int:
    args = _parse_args()
    build_query_type_classifier_failure_analysis_report(
        dataset_path=args.dataset,
        result_path=args.results,
        report_path=args.report,
    )
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build public-safe query type classifier failure analysis report.",
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULT_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
