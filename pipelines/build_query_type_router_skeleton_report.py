from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.application.query_type_router import (
    DEFAULT_RETRIEVAL_CANDIDATE_ID,
    NO_ANSWER_ROUTE_POLICY_ID,
    QUERY_TYPE_ROUTER_POLICY_ID,
    RELATIONSHIP_RETRIEVAL_CANDIDATE_ID,
    RELATIONSHIP_ROUTE_POLICY_ID,
    QueryTypeRouter,
    build_query_type_router_public_rows,
)
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    collect_public_retrieval_artifact_failures,
    measure_public_retrieval_artifact_quality,
)


QUERY_TYPE_ROUTER_SKELETON_REPORT_VERSION = "query-type-router-skeleton-report/v1"
DEFAULT_REPORT_PATH = Path("evals/reports/query_type_router_skeleton_report.md")


class QueryTypeRouterSkeletonModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class QueryTypeRouterSkeletonSummary(QueryTypeRouterSkeletonModel):
    query_type_count: int = Field(ge=0)
    router_policy_count: int = Field(ge=0)
    route_policy_count: int = Field(ge=0)
    should_retrieve_count: int = Field(ge=0)
    abstain_first_count: int = Field(ge=0)
    dense_default_count: int = Field(ge=0)
    relationship_hybrid_count: int = Field(ge=0)
    rejected_candidate_count: int = Field(ge=0)
    live_solar_call_count: int = Field(ge=0)
    cuda_required: bool = False


class QueryTypeRouterSkeletonReport(QueryTypeRouterSkeletonModel):
    report_version: str = QUERY_TYPE_ROUTER_SKELETON_REPORT_VERSION
    run_id: str = "HD-ROUTER-002"
    router_policy_id: str = QUERY_TYPE_ROUTER_POLICY_ID
    summary: QueryTypeRouterSkeletonSummary
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def build_report(
    *,
    report_path: Path = DEFAULT_REPORT_PATH,
) -> QueryTypeRouterSkeletonReport:
    rows = build_query_type_router_public_rows(QueryTypeRouter())
    provisional_quality = measure_public_retrieval_artifact_quality(
        report_version=QUERY_TYPE_ROUTER_SKELETON_REPORT_VERSION,
        run_id="query-type-router-skeleton",
        result_rows=rows,
        report_text="",
    )
    provisional = _build_report_from_rows(rows=rows, output_quality=provisional_quality)
    report_text = build_query_type_router_skeleton_report_markdown(provisional, rows=rows)
    quality = measure_public_retrieval_artifact_quality(
        report_version=QUERY_TYPE_ROUTER_SKELETON_REPORT_VERSION,
        run_id="query-type-router-skeleton",
        result_rows=rows,
        report_text=report_text,
    )
    report = _build_report_from_rows(rows=rows, output_quality=quality)
    failures = collect_query_type_router_skeleton_failures(report)
    if failures:
        raise ValueError(f"query type router skeleton gate failed: {failures}")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        build_query_type_router_skeleton_report_markdown(report, rows=rows),
        encoding="utf-8",
    )
    print(
        "query_type_router_skeleton "
        "status=PASS "
        f"query_type_count={report.summary.query_type_count} "
        f"relationship_hybrid_count={report.summary.relationship_hybrid_count} "
        f"abstain_first_count={report.summary.abstain_first_count} "
        f"live_solar_call_count={report.summary.live_solar_call_count}"
    )
    return report


def collect_query_type_router_skeleton_failures(
    report: QueryTypeRouterSkeletonReport,
) -> list[str]:
    failures = collect_public_retrieval_artifact_failures(report.output_quality)
    summary = report.summary
    if summary.query_type_count != 7:
        failures.append("unexpected_query_type_count")
    if summary.router_policy_count != 1:
        failures.append("unexpected_router_policy_count")
    if summary.abstain_first_count != 1:
        failures.append("abstain_first_route_missing")
    if summary.relationship_hybrid_count != 1:
        failures.append("relationship_hybrid_route_missing")
    if summary.dense_default_count != 5:
        failures.append("dense_default_route_count_mismatch")
    if summary.live_solar_call_count:
        failures.append("live_solar_call_detected")
    if summary.cuda_required:
        failures.append("unexpected_cuda_requirement")
    return failures


def build_query_type_router_skeleton_report_markdown(
    report: QueryTypeRouterSkeletonReport,
    *,
    rows: list[dict[str, Any]],
) -> str:
    summary = report.summary
    quality = report.output_quality
    route_rows = "\n".join(_format_route_row(row) for row in rows)
    qualitative_rows = "\n".join(
        f"- `{key}`: {value}" for key, value in report.qualitative_assessment.items()
    )
    return f"""# Query Type Router Skeleton Report

## 목적

`HD-ROUTER-001`에서 고정한 query type별 route policy를 deterministic router skeleton으로 구현했는지 검증한다.

이 문서는 runtime branch contract 검증이다. 검색 성능 개선, locked test 개선, Solar Pro 3 답변 품질 개선 주장이 아니다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| run_id | `{report.run_id}` |
| router_policy_id | `{report.router_policy_id}` |
| solar_call_count | {summary.live_solar_call_count} |
| cuda_required | {str(summary.cuda_required).lower()} |

## 정량 리포트

| metric | value |
| --- | ---: |
| query_type_count | {summary.query_type_count} |
| router_policy_count | {summary.router_policy_count} |
| route_policy_count | {summary.route_policy_count} |
| should_retrieve_count | {summary.should_retrieve_count} |
| abstain_first_count | {summary.abstain_first_count} |
| dense_default_count | {summary.dense_default_count} |
| relationship_hybrid_count | {summary.relationship_hybrid_count} |
| rejected_candidate_count | {summary.rejected_candidate_count} |
| live_solar_call_count | {summary.live_solar_call_count} |

## Route Table

| query_type | route_policy_id | selected_candidate_id | execution_mode | should_retrieve | decision | claim_boundary |
| --- | --- | --- | --- | ---: | --- | --- |
{route_rows}

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

router skeleton은 query type label을 이미 알고 있다는 전제에서만 동작한다. query type classifier, Solar Pro 3 generation, locked 성능 개선은 별도 gate에서 검증해야 한다.
"""


def _build_report_from_rows(
    *,
    rows: list[dict[str, Any]],
    output_quality: PublicRetrievalArtifactQuality,
) -> QueryTypeRouterSkeletonReport:
    summary = _summarize_rows(rows)
    return QueryTypeRouterSkeletonReport(
        summary=summary,
        output_quality=output_quality,
        qualitative_assessment=_build_qualitative_assessment(
            summary=summary,
            output_quality=output_quality,
        ),
    )


def _summarize_rows(rows: list[dict[str, Any]]) -> QueryTypeRouterSkeletonSummary:
    route_policy_ids = {
        str(row["route_policy_id"])
        for row in rows
        if isinstance(row.get("route_policy_id"), str)
    }
    router_policy_ids = {
        str(row["router_policy_id"])
        for row in rows
        if isinstance(row.get("router_policy_id"), str)
    }
    return QueryTypeRouterSkeletonSummary(
        query_type_count=len(rows),
        router_policy_count=len(router_policy_ids),
        route_policy_count=len(route_policy_ids),
        should_retrieve_count=sum(1 for row in rows if row.get("should_retrieve") is True),
        abstain_first_count=sum(
            1 for row in rows if row.get("route_policy_id") == NO_ANSWER_ROUTE_POLICY_ID
        ),
        dense_default_count=sum(
            1
            for row in rows
            if row.get("selected_candidate_id") == DEFAULT_RETRIEVAL_CANDIDATE_ID
        ),
        relationship_hybrid_count=sum(
            1
            for row in rows
            if row.get("route_policy_id") == RELATIONSHIP_ROUTE_POLICY_ID
            and row.get("selected_candidate_id") == RELATIONSHIP_RETRIEVAL_CANDIDATE_ID
        ),
        rejected_candidate_count=sum(
            int(row.get("rejected_candidate_count") or 0) for row in rows
        ),
        live_solar_call_count=0,
        cuda_required=False,
    )


def _build_qualitative_assessment(
    *,
    summary: QueryTypeRouterSkeletonSummary,
    output_quality: PublicRetrievalArtifactQuality,
) -> dict[str, str]:
    failures = collect_public_retrieval_artifact_failures(output_quality)
    return {
        "router_scope": (
            "query type label이 이미 주어진다는 전제에서 route table branch만 검증했다."
        ),
        "relationship_branch": (
            "relationship query type은 hybrid weighted E5 route candidate로 분기한다."
        ),
        "no_answer_branch": (
            "no_answer query type은 retrieval보다 abstain-first policy를 우선한다."
        ),
        "default_branch": (
            "overview, place_fact, place_story, route_context, voice_followup은 "
            "dense voice rewrite default route를 유지한다."
        ),
        "security_boundary": (
            "public row와 report에는 query, answer, evidence text, chunk text를 저장하지 않는다."
        ),
        "execution_boundary": (
            "이번 report에서 Solar Pro 3 호출과 CUDA 연산은 필요하지 않다."
        ),
        "gate_status": "PASS" if not failures else f"FAIL: {', '.join(failures)}",
        "external_audit": (
            "router skeleton은 구현됐지만 classifier와 locked performance claim은 아직 없다."
        ),
        "summary_counts": (
            f"route_policy_count={summary.route_policy_count}, "
            f"relationship_hybrid_count={summary.relationship_hybrid_count}"
        ),
    }


def _format_route_row(row: dict[str, Any]) -> str:
    return (
        f"| `{row['query_type']}` | `{row['route_policy_id']}` | "
        f"`{row['selected_candidate_id']}` | `{row['execution_mode']}` | "
        f"{str(row['should_retrieve']).lower()} | `{row['decision']}` | "
        f"{row['claim_boundary']} |"
    )


def main() -> int:
    args = _parse_args()
    build_report(report_path=args.report)
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build query type router skeleton public-safe report."
    )
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
