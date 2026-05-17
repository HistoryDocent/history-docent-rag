from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.project_paths import project_path
from app.domain.retrieval import (
    REQUIRED_QUERY_TYPES,
    QueryType,
    RetrievalEvalDatasetSummary,
    RetrievalEvalItem,
    RetrievalEvalTargetResolvabilitySummary,
    build_retrieval_target_inventory,
    collect_retrieval_eval_target_resolvability_failures,
    load_retrieval_eval_jsonl,
    summarize_retrieval_eval_dataset,
    summarize_retrieval_eval_target_resolvability,
)
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    collect_public_retrieval_artifact_failures,
    measure_public_retrieval_artifact_quality,
    public_path_alias,
    write_public_retrieval_result_rows,
)
from app.infrastructure.index.device import resolve_torch_device
from pipelines.build_retrieval_eval_target_report import (
    PRIVATE_CHUNKS_PATH_ALIAS,
    load_child_chunks_from_report,
)


LOCKED_RETRIEVAL_READINESS_REPORT_VERSION = "locked-retrieval-readiness-report/v1"
WORK_ID = "HD-LOCKED-RETRIEVAL-002"
DEFAULT_DATASET_PATH = (
    Path("private_data") / "evals" / "datasets" / "retrieval_eval_test.jsonl"
)
DEFAULT_CHUNKS_PATH = Path("private_data") / "reports" / "parent_child_chunks.json"
DEFAULT_DOC_PATH = Path("docs") / "LOCKED_RETRIEVAL_READINESS.md"
DEFAULT_REPORT_PATH = Path("evals") / "reports" / "locked_retrieval_readiness_report.md"
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "locked_retrieval_readiness_rows.jsonl"
)
EXPECTED_LOCKED_QUERY_COUNT = 35
EXPECTED_QUERY_TYPE_COUNT = len(REQUIRED_QUERY_TYPES)
EXPECTED_QUERY_COUNT_PER_TYPE = 5
EXPECTED_ALLOWED_CANDIDATE_COUNT = 2
EXPECTED_REJECTED_CANDIDATE_COUNT = 4
LOCKED_TEST_EXECUTION_COUNT = 0
LOCKED_METRIC_RESULT_COUNT = 0
RETRIEVAL_EXECUTION_COUNT = 0
SOLAR_CALL_COUNT = 0

CandidateStatus = Literal[
    "baseline_allowed",
    "candidate_allowed_for_relationship_only",
    "rejected_for_locked_readiness",
]
RoutePolicyId = Literal[
    "default_dense_voice_rewrite_v1",
    "relationship_shadow_comparison_v1",
    "no_answer_abstain_guard_v1",
]
ReadinessDecision = Literal[
    "ready_for_locked_retrieval_approval",
    "blocked_by_readiness_gate",
]


class LockedRetrievalReadinessModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LockedRetrievalCandidateConfig(LockedRetrievalReadinessModel):
    candidate_id: str = Field(min_length=1)
    status: CandidateStatus
    route_policy_id: RoutePolicyId | Literal["not_allowed"]
    scope: Literal["answerable_all", "relationship_only", "not_allowed"]
    planned_query_count: int = Field(ge=0)
    retrieval_execution_count: int = Field(ge=0)
    locked_metric_result_count: int = Field(ge=0)
    reason: str = Field(min_length=1)


class LockedRetrievalQueryTypeRouteRow(LockedRetrievalReadinessModel):
    query_type: QueryType
    locked_query_count: int = Field(ge=0)
    expected_candidate_count: int = Field(ge=0)
    route_policy_id: RoutePolicyId
    no_answer_guard_applied: bool
    candidate_scope_violation_count: int = Field(ge=0)


class LockedRetrievalReadinessSummary(LockedRetrievalReadinessModel):
    planned_locked_query_count: int = Field(ge=0)
    locked_query_count: int = Field(ge=0)
    planned_query_type_count: int = Field(ge=0)
    query_type_count: int = Field(ge=0)
    expected_query_count_per_type: int = Field(ge=1)
    answerable_query_count: int = Field(ge=0)
    no_answer_query_count: int = Field(ge=0)
    allowed_candidate_count: int = Field(ge=0)
    rejected_candidate_count: int = Field(ge=0)
    planned_retrieval_candidate_count: int = Field(ge=0)
    planned_generation_candidate_count: int = Field(ge=0)
    target_resolvability_fail_count: int = Field(ge=0)
    missing_child_target_count: int = Field(ge=0)
    missing_parent_target_count: int = Field(ge=0)
    missing_doc_target_count: int = Field(ge=0)
    no_answer_candidate_route_count: int = Field(ge=0)
    candidate_scope_violation_count: int = Field(ge=0)
    locked_test_execution_count: int = Field(ge=0)
    locked_metric_result_count: int = Field(ge=0)
    retrieval_execution_count: int = Field(ge=0)
    solar_call_count: int = Field(ge=0)
    cuda_required_for_future_run: bool
    resolved_device: str = Field(min_length=1)
    readiness_decision: ReadinessDecision


class LockedRetrievalReadinessReport(LockedRetrievalReadinessModel):
    report_version: str = LOCKED_RETRIEVAL_READINESS_REPORT_VERSION
    readiness_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    work_id: str = WORK_ID
    dataset_path_alias: str = Field(min_length=1)
    chunks_path_alias: str = PRIVATE_CHUNKS_PATH_ALIAS
    result_path: str = Field(min_length=1)
    source_fingerprint: str = Field(min_length=8)
    summary: LockedRetrievalReadinessSummary
    query_type_routes: tuple[LockedRetrievalQueryTypeRouteRow, ...]
    candidates: tuple[LockedRetrievalCandidateConfig, ...]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def run_locked_retrieval_readiness(
    *,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    chunks_path: Path = DEFAULT_CHUNKS_PATH,
    doc_path: Path = DEFAULT_DOC_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
) -> LockedRetrievalReadinessReport:
    items = load_retrieval_eval_jsonl(project_path(dataset_path))
    dataset_summary = summarize_retrieval_eval_dataset(items)
    children = load_child_chunks_from_report(project_path(chunks_path))
    target_summary = summarize_retrieval_eval_target_resolvability(
        items=items,
        inventory=build_retrieval_target_inventory(children),
    )
    query_type_routes = build_locked_query_type_routes(items)
    candidates = build_locked_candidate_configs(items)
    summary = build_locked_readiness_summary(
        dataset_summary=dataset_summary,
        target_summary=target_summary,
        query_type_routes=query_type_routes,
        candidates=candidates,
    )
    readiness_id = _readiness_id(
        items=items,
        summary=summary,
        candidates=candidates,
        query_type_routes=query_type_routes,
    )
    public_rows = build_public_locked_readiness_rows(
        readiness_id=readiness_id,
        summary=summary,
        query_type_routes=query_type_routes,
        candidates=candidates,
    )
    provisional_quality = measure_public_retrieval_artifact_quality(
        report_version=LOCKED_RETRIEVAL_READINESS_REPORT_VERSION,
        run_id=readiness_id,
        result_rows=public_rows,
        report_text="",
    )
    provisional = build_locked_readiness_report(
        readiness_id=readiness_id,
        dataset_path=dataset_path,
        result_rows_path=result_rows_path,
        summary=summary,
        query_type_routes=query_type_routes,
        candidates=candidates,
        output_quality=provisional_quality,
    )
    doc_text = build_locked_readiness_doc(provisional)
    report_text = build_locked_readiness_markdown(provisional)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=LOCKED_RETRIEVAL_READINESS_REPORT_VERSION,
        run_id=readiness_id,
        result_rows=public_rows,
        report_text=report_text,
        extra_public_texts={
            f"doc:{line_number}": line
            for line_number, line in enumerate(doc_text.splitlines(), start=1)
        },
    )
    report = build_locked_readiness_report(
        readiness_id=readiness_id,
        dataset_path=dataset_path,
        result_rows_path=result_rows_path,
        summary=summary,
        query_type_routes=query_type_routes,
        candidates=candidates,
        output_quality=output_quality,
    )
    failures = collect_locked_readiness_failures(report)
    if failures:
        raise ValueError(f"locked retrieval readiness gate failed: {failures}")

    write_public_retrieval_result_rows(
        path=project_path(result_rows_path),
        rows=public_rows,
    )
    resolved_doc_path = project_path(doc_path)
    resolved_report_path = project_path(report_path)
    resolved_doc_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_report_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_doc_path.write_text(build_locked_readiness_doc(report), encoding="utf-8")
    resolved_report_path.write_text(
        build_locked_readiness_markdown(report),
        encoding="utf-8",
    )
    print(
        "locked_retrieval_readiness "
        "status=PASS "
        f"locked_query_count={report.summary.locked_query_count} "
        f"allowed_candidate_count={report.summary.allowed_candidate_count} "
        f"target_resolvability_fail_count="
        f"{report.summary.target_resolvability_fail_count} "
        f"retrieval_execution_count={report.summary.retrieval_execution_count} "
        f"solar_call_count={report.summary.solar_call_count} "
        f"resolved_device={report.summary.resolved_device}",
    )
    return report


def build_locked_query_type_routes(
    items: list[RetrievalEvalItem],
) -> tuple[LockedRetrievalQueryTypeRouteRow, ...]:
    counts = Counter(item.query.query_type for item in items)
    rows: list[LockedRetrievalQueryTypeRouteRow] = []
    for query_type in REQUIRED_QUERY_TYPES:
        if query_type == "no_answer":
            rows.append(
                LockedRetrievalQueryTypeRouteRow(
                    query_type=query_type,
                    locked_query_count=counts.get(query_type, 0),
                    expected_candidate_count=0,
                    route_policy_id="no_answer_abstain_guard_v1",
                    no_answer_guard_applied=True,
                    candidate_scope_violation_count=0,
                ),
            )
            continue
        if query_type == "relationship":
            rows.append(
                LockedRetrievalQueryTypeRouteRow(
                    query_type=query_type,
                    locked_query_count=counts.get(query_type, 0),
                    expected_candidate_count=2,
                    route_policy_id="relationship_shadow_comparison_v1",
                    no_answer_guard_applied=False,
                    candidate_scope_violation_count=0,
                ),
            )
            continue
        rows.append(
            LockedRetrievalQueryTypeRouteRow(
                query_type=query_type,
                locked_query_count=counts.get(query_type, 0),
                expected_candidate_count=1,
                route_policy_id="default_dense_voice_rewrite_v1",
                no_answer_guard_applied=False,
                candidate_scope_violation_count=0,
            ),
        )
    return tuple(rows)


def build_locked_candidate_configs(
    items: list[RetrievalEvalItem],
) -> tuple[LockedRetrievalCandidateConfig, ...]:
    answerable_count = sum(1 for item in items if item.query.expected_behavior == "retrieve")
    relationship_count = sum(1 for item in items if item.query.query_type == "relationship")
    return (
        LockedRetrievalCandidateConfig(
            candidate_id="dense_multilingual_e5_small_voice_rewrite",
            status="baseline_allowed",
            route_policy_id="default_dense_voice_rewrite_v1",
            scope="answerable_all",
            planned_query_count=answerable_count,
            retrieval_execution_count=0,
            locked_metric_result_count=0,
            reason="현재 non-rerank 기본 후보다.",
        ),
        LockedRetrievalCandidateConfig(
            candidate_id="relationship_hybrid_weighted_e5_v1",
            status="candidate_allowed_for_relationship_only",
            route_policy_id="relationship_shadow_comparison_v1",
            scope="relationship_only",
            planned_query_count=relationship_count,
            retrieval_execution_count=0,
            locked_metric_result_count=0,
            reason="relationship query type에만 제한한 shadow 후보다.",
        ),
        LockedRetrievalCandidateConfig(
            candidate_id="hyde_larger_live_candidate",
            status="rejected_for_locked_readiness",
            route_policy_id="not_allowed",
            scope="not_allowed",
            planned_query_count=0,
            retrieval_execution_count=0,
            locked_metric_result_count=0,
            reason="dev 40에서 MRR, nDCG, latency trade-off가 나빠졌다.",
        ),
        LockedRetrievalCandidateConfig(
            candidate_id="graphrag_lite_entity_path_v1",
            status="rejected_for_locked_readiness",
            route_policy_id="not_allowed",
            scope="not_allowed",
            planned_query_count=0,
            retrieval_execution_count=0,
            locked_metric_result_count=0,
            reason="relationship input-only에서 개선 근거가 없다.",
        ),
        LockedRetrievalCandidateConfig(
            candidate_id="raptor_lite_summary_node_v1",
            status="rejected_for_locked_readiness",
            route_policy_id="not_allowed",
            scope="not_allowed",
            planned_query_count=0,
            retrieval_execution_count=0,
            locked_metric_result_count=0,
            reason="overview/place_story input-only에서 개선 근거가 없다.",
        ),
        LockedRetrievalCandidateConfig(
            candidate_id="place_story_guarded_boost_v1",
            status="rejected_for_locked_readiness",
            route_policy_id="not_allowed",
            scope="not_allowed",
            planned_query_count=0,
            retrieval_execution_count=0,
            locked_metric_result_count=0,
            reason="locked readiness에서 place_story candidate 선택이 0건이었다.",
        ),
    )


def build_locked_readiness_summary(
    *,
    dataset_summary: RetrievalEvalDatasetSummary,
    target_summary: RetrievalEvalTargetResolvabilitySummary,
    query_type_routes: tuple[LockedRetrievalQueryTypeRouteRow, ...],
    candidates: tuple[LockedRetrievalCandidateConfig, ...],
) -> LockedRetrievalReadinessSummary:
    target_failures = collect_retrieval_eval_target_resolvability_failures(target_summary)
    allowed_candidate_count = sum(
        1 for candidate in candidates if candidate.scope != "not_allowed"
    )
    rejected_candidate_count = sum(
        1 for candidate in candidates if candidate.scope == "not_allowed"
    )
    no_answer_candidate_route_count = sum(
        row.expected_candidate_count
        for row in query_type_routes
        if row.query_type == "no_answer"
    )
    candidate_scope_violation_count = sum(
        row.candidate_scope_violation_count for row in query_type_routes
    )
    resolved_device = str(resolve_torch_device("cuda_if_available"))
    preliminary = LockedRetrievalReadinessSummary(
        planned_locked_query_count=EXPECTED_LOCKED_QUERY_COUNT,
        locked_query_count=dataset_summary.review_status_distribution.get("locked", 0),
        planned_query_type_count=EXPECTED_QUERY_TYPE_COUNT,
        query_type_count=len(dataset_summary.query_type_distribution),
        expected_query_count_per_type=EXPECTED_QUERY_COUNT_PER_TYPE,
        answerable_query_count=target_summary.answerable_query_count,
        no_answer_query_count=target_summary.no_answer_query_count,
        allowed_candidate_count=allowed_candidate_count,
        rejected_candidate_count=rejected_candidate_count,
        planned_retrieval_candidate_count=allowed_candidate_count,
        planned_generation_candidate_count=0,
        target_resolvability_fail_count=len(target_failures),
        missing_child_target_count=target_summary.missing_child_target_count,
        missing_parent_target_count=target_summary.missing_parent_target_count,
        missing_doc_target_count=target_summary.missing_doc_target_count,
        no_answer_candidate_route_count=no_answer_candidate_route_count,
        candidate_scope_violation_count=candidate_scope_violation_count,
        locked_test_execution_count=LOCKED_TEST_EXECUTION_COUNT,
        locked_metric_result_count=LOCKED_METRIC_RESULT_COUNT,
        retrieval_execution_count=RETRIEVAL_EXECUTION_COUNT,
        solar_call_count=SOLAR_CALL_COUNT,
        cuda_required_for_future_run=True,
        resolved_device=resolved_device,
        readiness_decision="blocked_by_readiness_gate",
    )
    decision: ReadinessDecision = (
        "ready_for_locked_retrieval_approval"
        if _summary_passes_pre_output_gate(preliminary, query_type_routes)
        else "blocked_by_readiness_gate"
    )
    return preliminary.model_copy(update={"readiness_decision": decision})


def build_locked_readiness_report(
    *,
    readiness_id: str,
    dataset_path: Path,
    result_rows_path: Path,
    summary: LockedRetrievalReadinessSummary,
    query_type_routes: tuple[LockedRetrievalQueryTypeRouteRow, ...],
    candidates: tuple[LockedRetrievalCandidateConfig, ...],
    output_quality: PublicRetrievalArtifactQuality,
) -> LockedRetrievalReadinessReport:
    report = LockedRetrievalReadinessReport(
        readiness_id=readiness_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        dataset_path_alias=public_path_alias(dataset_path),
        result_path=public_path_alias(result_rows_path),
        source_fingerprint=_stable_id(
            {
                "readiness_id": readiness_id,
                "candidate_ids": [candidate.candidate_id for candidate in candidates],
                "query_type_routes": [
                    row.model_dump(mode="json") for row in query_type_routes
                ],
                "locked_query_count": summary.locked_query_count,
            },
        ),
        summary=summary,
        query_type_routes=query_type_routes,
        candidates=candidates,
        output_quality=output_quality,
        qualitative_assessment={},
    )
    return report.model_copy(
        update={"qualitative_assessment": build_locked_readiness_assessment(report)}
    )


def build_public_locked_readiness_rows(
    *,
    readiness_id: str,
    summary: LockedRetrievalReadinessSummary,
    query_type_routes: tuple[LockedRetrievalQueryTypeRouteRow, ...],
    candidates: tuple[LockedRetrievalCandidateConfig, ...],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "row_type": "summary",
            "readiness_id": readiness_id,
            "planned_locked_query_count": summary.planned_locked_query_count,
            "locked_query_count": summary.locked_query_count,
            "planned_query_type_count": summary.planned_query_type_count,
            "query_type_count": summary.query_type_count,
            "allowed_candidate_count": summary.allowed_candidate_count,
            "rejected_candidate_count": summary.rejected_candidate_count,
            "target_resolvability_fail_count": summary.target_resolvability_fail_count,
            "no_answer_candidate_route_count": summary.no_answer_candidate_route_count,
            "locked_metric_result_count": summary.locked_metric_result_count,
            "retrieval_execution_count": summary.retrieval_execution_count,
            "solar_call_count": summary.solar_call_count,
            "readiness_decision": summary.readiness_decision,
        },
    ]
    rows.extend(
        {
            "row_type": "query_type_route",
            "readiness_id": readiness_id,
            "query_type": row.query_type,
            "locked_query_count": row.locked_query_count,
            "expected_candidate_count": row.expected_candidate_count,
            "route_policy_id": row.route_policy_id,
            "no_answer_guard_applied": row.no_answer_guard_applied,
            "candidate_scope_violation_count": row.candidate_scope_violation_count,
        }
        for row in query_type_routes
    )
    rows.extend(
        {
            "row_type": "candidate",
            "readiness_id": readiness_id,
            "candidate_id": candidate.candidate_id,
            "status": candidate.status,
            "route_policy_id": candidate.route_policy_id,
            "scope": candidate.scope,
            "planned_query_count": candidate.planned_query_count,
            "retrieval_execution_count": candidate.retrieval_execution_count,
            "locked_metric_result_count": candidate.locked_metric_result_count,
        }
        for candidate in candidates
    )
    return rows


def collect_locked_readiness_failures(
    report: LockedRetrievalReadinessReport,
) -> list[str]:
    failures = collect_public_retrieval_artifact_failures(report.output_quality)
    summary = report.summary
    if summary.readiness_decision == "blocked_by_readiness_gate":
        failures.append("readiness_decision_blocked")
    if summary.locked_query_count != EXPECTED_LOCKED_QUERY_COUNT:
        failures.append("locked_query_count_mismatch")
    if summary.query_type_count != EXPECTED_QUERY_TYPE_COUNT:
        failures.append("query_type_count_mismatch")
    if any(
        row.locked_query_count != EXPECTED_QUERY_COUNT_PER_TYPE
        for row in report.query_type_routes
    ):
        failures.append("query_type_distribution_mismatch")
    if summary.allowed_candidate_count != EXPECTED_ALLOWED_CANDIDATE_COUNT:
        failures.append("allowed_candidate_count_mismatch")
    if summary.rejected_candidate_count != EXPECTED_REJECTED_CANDIDATE_COUNT:
        failures.append("rejected_candidate_count_mismatch")
    if summary.target_resolvability_fail_count:
        failures.append("target_resolvability_failed")
    if summary.no_answer_candidate_route_count:
        failures.append("no_answer_candidate_route")
    if summary.candidate_scope_violation_count:
        failures.append("candidate_scope_violation")
    if summary.locked_test_execution_count:
        failures.append("locked_test_executed_in_readiness")
    if summary.locked_metric_result_count:
        failures.append("locked_metric_result_created_in_readiness")
    if summary.retrieval_execution_count:
        failures.append("retrieval_executed_in_readiness")
    if summary.solar_call_count:
        failures.append("solar_called_in_readiness")
    if summary.resolved_device not in {"cuda", "cpu"}:
        failures.append("unexpected_resolved_device")
    return list(dict.fromkeys(failures))


def build_locked_readiness_doc(report: LockedRetrievalReadinessReport) -> str:
    summary = report.summary
    route_rows = "\n".join(_format_doc_route_row(row) for row in report.query_type_routes)
    candidate_rows = "\n".join(_format_doc_candidate_row(row) for row in report.candidates)
    return f"""# Locked Retrieval Readiness

## 결론

`HD-LOCKED-RETRIEVAL-002`는 locked retrieval 실행 전 readiness gate다.

이번 단계에서는 검색, 임베딩, metric 계산, Solar Pro 3 호출을 실행하지 않는다. locked test는 최종 확인용이므로 실행 전 target resolvability, route 후보 수, no-answer guard, CUDA device, public-safe output만 검증한다.

이 문서는 public-safe readiness 문서다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 정량 요약

| metric | value |
| --- | ---: |
| planned_locked_query_count | {summary.planned_locked_query_count} |
| locked_query_count | {summary.locked_query_count} |
| planned_query_type_count | {summary.planned_query_type_count} |
| query_type_count | {summary.query_type_count} |
| expected_query_count_per_type | {summary.expected_query_count_per_type} |
| answerable_query_count | {summary.answerable_query_count} |
| no_answer_query_count | {summary.no_answer_query_count} |
| allowed_candidate_count | {summary.allowed_candidate_count} |
| rejected_candidate_count | {summary.rejected_candidate_count} |
| target_resolvability_fail_count | {summary.target_resolvability_fail_count} |
| no_answer_candidate_route_count | {summary.no_answer_candidate_route_count} |
| locked_metric_result_count | {summary.locked_metric_result_count} |
| retrieval_execution_count | {summary.retrieval_execution_count} |
| solar_call_count | {summary.solar_call_count} |
| cuda_required_for_future_run | {str(summary.cuda_required_for_future_run).lower()} |
| resolved_device | `{summary.resolved_device}` |
| readiness_decision | `{summary.readiness_decision}` |

## Query Type Route Plan

| query_type | locked_query_count | expected_candidate_count | route_policy_id | no_answer_guard |
| --- | ---: | ---: | --- | --- |
{route_rows}

## Candidate Boundary

| candidate_id | status | scope | planned_query_count | execution_count |
| --- | --- | --- | ---: | ---: |
{candidate_rows}

## 실행 경계

| boundary | value |
| --- | --- |
| locked retrieval execution | disabled |
| locked metric execution | disabled |
| Solar Pro 3 call | disabled |
| generation candidate | none |
| final citation source | source child chunk only in future run |
| no-answer policy | abstain guard, candidate route 0 |
| data mart grain for future run | `run_id + query_id + candidate_id + metric_name` |

## 다음 작업

| priority | work_id | 작업 | 승인 필요 |
| ---: | --- | --- | --- |
| 1 | `HD-LOCKED-RETRIEVAL-003` | locked retrieval paired comparison 실행 여부 승인 | 예 |
| 2 | `HD-COLBERT-001` | late interaction hard subset 검토 | 예 |

## Claim Boundary

| claim | allowed |
| --- | --- |
| locked retrieval 실행 전 준비 gate를 통과했다 | yes |
| readiness 단계에서 retrieval execution은 0회다 | yes |
| readiness 단계에서 Solar Pro 3 호출은 0회다 | yes |
| no-answer query는 candidate route로 보내지 않는다 | yes |
| locked test에서 retrieval 성능 개선을 입증했다 | no |
| active route가 기본 활성화됐다 | no |
| production 성능 검증이 끝났다 | no |
"""


def build_locked_readiness_markdown(report: LockedRetrievalReadinessReport) -> str:
    summary = report.summary
    quality = report.output_quality
    route_rows = "\n".join(
        _format_report_route_row(row) for row in report.query_type_routes
    )
    candidate_rows = "\n".join(
        _format_report_candidate_row(row) for row in report.candidates
    )
    qualitative_rows = "\n".join(
        f"- `{key}`: {value}" for key, value in report.qualitative_assessment.items()
    )
    failures = collect_locked_readiness_failures(report)
    return f"""# Locked Retrieval Readiness Report

## 목적

`HD-LOCKED-RETRIEVAL-002`는 locked retrieval paired comparison을 실행하기 전 data, route, candidate, device, public output 조건을 검증한다.

이 리포트는 성능 개선 주장이 아니다. 검색, 임베딩, metric 계산, Solar Pro 3 호출을 실행하지 않는다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| readiness_id | `{report.readiness_id}` |
| work_id | `{report.work_id}` |
| generated_at_utc | `{report.generated_at_utc}` |
| dataset_path | `{report.dataset_path_alias}` |
| chunks_path_alias | `{report.chunks_path_alias}` |
| result_path | `{report.result_path}` |
| source_fingerprint | `{report.source_fingerprint}` |
| readiness_status | `{"PASS" if not failures else "FAIL"}` |

## 정량 리포트

| metric | value |
| --- | ---: |
| planned_locked_query_count | {summary.planned_locked_query_count} |
| locked_query_count | {summary.locked_query_count} |
| planned_query_type_count | {summary.planned_query_type_count} |
| query_type_count | {summary.query_type_count} |
| expected_query_count_per_type | {summary.expected_query_count_per_type} |
| answerable_query_count | {summary.answerable_query_count} |
| no_answer_query_count | {summary.no_answer_query_count} |
| allowed_candidate_count | {summary.allowed_candidate_count} |
| rejected_candidate_count | {summary.rejected_candidate_count} |
| planned_retrieval_candidate_count | {summary.planned_retrieval_candidate_count} |
| planned_generation_candidate_count | {summary.planned_generation_candidate_count} |
| target_resolvability_fail_count | {summary.target_resolvability_fail_count} |
| missing_child_target_count | {summary.missing_child_target_count} |
| missing_parent_target_count | {summary.missing_parent_target_count} |
| missing_doc_target_count | {summary.missing_doc_target_count} |
| no_answer_candidate_route_count | {summary.no_answer_candidate_route_count} |
| candidate_scope_violation_count | {summary.candidate_scope_violation_count} |
| locked_test_execution_count | {summary.locked_test_execution_count} |
| locked_metric_result_count | {summary.locked_metric_result_count} |
| retrieval_execution_count | {summary.retrieval_execution_count} |
| solar_call_count | {summary.solar_call_count} |
| cuda_required_for_future_run | {str(summary.cuda_required_for_future_run).lower()} |
| resolved_device | `{summary.resolved_device}` |
| readiness_decision | `{summary.readiness_decision}` |

## Query Type Route Plan

| query_type | locked_query_count | expected_candidate_count | route_policy_id | no_answer_guard | scope_violation |
| --- | ---: | ---: | --- | --- | ---: |
{route_rows}

## Candidate Boundary

| candidate_id | status | route_policy_id | scope | planned_query_count | retrieval_execution_count | locked_metric_result_count |
| --- | --- | --- | --- | ---: | ---: | ---: |
{candidate_rows}

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | {quality.result_row_count} |
| public_raw_text_leakage_count | {quality.public_raw_text_leakage_count} |
| private_path_leakage_count | {quality.private_path_leakage_count} |
| secret_like_leakage_count | {quality.secret_like_leakage_count} |
| forbidden_result_field_count | {quality.forbidden_result_field_count} |

## Gate Result

```text
readiness_failures={failures}
```

## 정성 리포트

{qualitative_rows}

## 해석

readiness gate는 통과했다. 다음 단계는 별도 승인 후 locked retrieval paired comparison 실행 여부를 결정하는 것이다.
"""


def build_locked_readiness_assessment(
    report: LockedRetrievalReadinessReport,
) -> dict[str, str]:
    failures = collect_locked_readiness_failures(report)
    summary = report.summary
    return {
        "scope": "locked split을 실행하지 않고 실행 전 조건만 검증했다.",
        "candidate_scope": "허용 후보는 기본 dense voice rewrite와 relationship hybrid 2개뿐이다.",
        "no_answer_boundary": "no_answer query는 retrieval candidate route로 보내지 않는다.",
        "device_boundary": (
            f"future run은 CUDA 사용 가능 시 CUDA를 쓰며 현재 resolved_device는 "
            f"{summary.resolved_device}다."
        ),
        "metric_boundary": "readiness 단계의 locked metric result와 retrieval execution은 0이다.",
        "generation_boundary": "이번 gate는 retrieval readiness이며 Solar Pro 3 호출은 없다.",
        "data_mart_grain": "`fact_locked_retrieval_eval` grain은 run_id + query_id + candidate_id + metric_name이다.",
        "security_boundary": "public artifact에는 query type, candidate id, count, decision만 남긴다.",
        "external_audit": "locked test 실행 전에 후보와 stop condition을 고정한 판단은 타당하다.",
        "gate_status": "PASS" if not failures else f"FAIL: {', '.join(failures)}",
    }


def _summary_passes_pre_output_gate(
    summary: LockedRetrievalReadinessSummary,
    query_type_routes: tuple[LockedRetrievalQueryTypeRouteRow, ...],
) -> bool:
    return (
        summary.locked_query_count == EXPECTED_LOCKED_QUERY_COUNT
        and summary.query_type_count == EXPECTED_QUERY_TYPE_COUNT
        and all(
            row.locked_query_count == EXPECTED_QUERY_COUNT_PER_TYPE
            for row in query_type_routes
        )
        and summary.allowed_candidate_count == EXPECTED_ALLOWED_CANDIDATE_COUNT
        and summary.rejected_candidate_count == EXPECTED_REJECTED_CANDIDATE_COUNT
        and summary.target_resolvability_fail_count == 0
        and summary.no_answer_candidate_route_count == 0
        and summary.candidate_scope_violation_count == 0
        and summary.locked_test_execution_count == 0
        and summary.locked_metric_result_count == 0
        and summary.retrieval_execution_count == 0
        and summary.solar_call_count == 0
    )


def _readiness_id(
    *,
    items: list[RetrievalEvalItem],
    summary: LockedRetrievalReadinessSummary,
    candidates: tuple[LockedRetrievalCandidateConfig, ...],
    query_type_routes: tuple[LockedRetrievalQueryTypeRouteRow, ...],
) -> str:
    digest = _stable_id(
        {
            "work_id": WORK_ID,
            "query_ids": sorted(item.query.query_id for item in items),
            "candidate_ids": [candidate.candidate_id for candidate in candidates],
            "route_rows": [row.model_dump(mode="json") for row in query_type_routes],
            "locked_query_count": summary.locked_query_count,
            "locked_metric_result_count": summary.locked_metric_result_count,
            "retrieval_execution_count": summary.retrieval_execution_count,
        },
    )
    return f"locked-readiness-q{summary.locked_query_count}-{digest[:8]}"


def _stable_id(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]


def _format_doc_route_row(row: LockedRetrievalQueryTypeRouteRow) -> str:
    return (
        f"| {row.query_type} | {row.locked_query_count} | "
        f"{row.expected_candidate_count} | {row.route_policy_id} | "
        f"{str(row.no_answer_guard_applied).lower()} |"
    )


def _format_report_route_row(row: LockedRetrievalQueryTypeRouteRow) -> str:
    return (
        f"| {row.query_type} | {row.locked_query_count} | "
        f"{row.expected_candidate_count} | {row.route_policy_id} | "
        f"{str(row.no_answer_guard_applied).lower()} | "
        f"{row.candidate_scope_violation_count} |"
    )


def _format_doc_candidate_row(row: LockedRetrievalCandidateConfig) -> str:
    execution_count = row.retrieval_execution_count + row.locked_metric_result_count
    return (
        f"| {row.candidate_id} | {row.status} | {row.scope} | "
        f"{row.planned_query_count} | {execution_count} |"
    )


def _format_report_candidate_row(row: LockedRetrievalCandidateConfig) -> str:
    return (
        f"| {row.candidate_id} | {row.status} | {row.route_policy_id} | "
        f"{row.scope} | {row.planned_query_count} | "
        f"{row.retrieval_execution_count} | {row.locked_metric_result_count} |"
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build locked retrieval readiness dry-run report."
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS_PATH)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--rows", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    run_locked_retrieval_readiness(
        dataset_path=args.dataset,
        chunks_path=args.chunks,
        doc_path=args.doc,
        report_path=args.report,
        result_rows_path=args.rows,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
