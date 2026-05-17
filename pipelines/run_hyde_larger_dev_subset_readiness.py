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
from app.domain.retrieval import QueryType, RetrievalEvalItem, load_retrieval_eval_jsonl
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    collect_public_retrieval_artifact_failures,
    measure_public_retrieval_artifact_quality,
    public_path_alias,
    write_public_retrieval_result_rows,
)
from app.infrastructure.index.device import resolve_torch_device
from pipelines.run_hyde_subset_readiness import (
    HYDE_CANDIDATE_ID,
    MODEL_ID,
    NO_ANSWER_GUARD_CANDIDATE_ID,
    PROMPT_POLICY_ID,
)
from pipelines.run_solar_live_generation_smoke import DEFAULT_DATASET_PATH


HYDE_LARGER_DEV_SUBSET_READINESS_REPORT_VERSION = (
    "hyde-larger-dev-subset-readiness-report/v1"
)
WORK_ID = "HD-HYDE-001C"
TARGET_QUERY_TYPES: tuple[QueryType, ...] = (
    "overview",
    "place_story",
    "relationship",
    "no_answer",
)
DEFAULT_EXPECTED_QUERY_COUNT_PER_TYPE = 10
DEFAULT_LIVE_CALL_HARD_CAP = 40
DEFAULT_DOC_PATH = Path("docs") / "HYDE_LARGER_DEV_SUBSET_READINESS.md"
DEFAULT_REPORT_PATH = (
    Path("evals") / "reports" / "hyde_larger_dev_subset_readiness_report.md"
)
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "hyde_larger_dev_subset_readiness_rows.jsonl"
)

SelectionReason = Literal[
    "overview_live_gain_followup",
    "place_story_retrieval_miss_followup",
    "relationship_mrr_regression_check",
    "no_answer_hallucination_guard",
]
ReadinessStatus = Literal["ready_for_live_approval", "blocked_by_no_answer_guard"]
ReadinessDecision = Literal[
    "ready_for_hyde_larger_live_approval",
    "blocked_by_readiness_gate",
]


class HydeLargerDevReadinessModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class HydeLargerDevReadinessRow(HydeLargerDevReadinessModel):
    readiness_id: str = Field(min_length=1)
    query_id: str = Field(min_length=1)
    query_type: QueryType
    expected_behavior: Literal["retrieve", "abstain"]
    split_scope: Literal["dev-only"]
    review_status: Literal["reviewed"]
    selection_strategy_id: str = Field(min_length=1)
    selection_reason: SelectionReason
    baseline_candidate_id: str = Field(min_length=1)
    hyde_candidate_id: str = Field(min_length=1)
    prompt_policy_id: str = Field(min_length=1)
    final_citation_source: Literal["source_child_chunk", "no_answer_abstain_guard"]
    baseline_retrieval_run_required: bool
    hyde_retrieval_run_required: bool
    hyde_generation_live_call_required: bool
    expected_hyde_generation_call_count: int = Field(ge=0)
    no_answer_guard_applied: bool
    public_raw_payload_allowed: bool
    readiness_status: ReadinessStatus
    claim_boundary: Literal["larger-dev-readiness-only"]


class HydeLargerDevQueryTypeSummary(HydeLargerDevReadinessModel):
    query_type: QueryType
    query_count: int = Field(ge=0)
    answerable_query_count: int = Field(ge=0)
    no_answer_query_count: int = Field(ge=0)
    expected_hyde_generation_live_call_count: int = Field(ge=0)
    no_answer_guard_query_count: int = Field(ge=0)
    baseline_candidate_id: str = Field(min_length=1)
    hyde_candidate_id: str = Field(min_length=1)


class HydeLargerDevReadinessSummary(HydeLargerDevReadinessModel):
    query_count: int = Field(ge=0)
    query_type_count: int = Field(ge=0)
    target_query_type_count: int = Field(ge=0)
    expected_query_count_per_type: int = Field(ge=1)
    answerable_query_count: int = Field(ge=0)
    no_answer_query_count: int = Field(ge=0)
    hyde_candidate_query_count: int = Field(ge=0)
    no_answer_guard_query_count: int = Field(ge=0)
    baseline_retrieval_run_count: int = Field(ge=0)
    hyde_retrieval_run_count: int = Field(ge=0)
    expected_hyde_generation_live_call_count: int = Field(ge=0)
    live_call_hard_cap: int = Field(ge=1)
    hard_cap_exceeded: bool
    live_execution_requested: bool
    live_execution_confirmed: bool
    solar_call_count: int = Field(ge=0)
    cuda_required: bool
    readiness_decision: ReadinessDecision


class HydeLargerDevSubsetReadinessReport(HydeLargerDevReadinessModel):
    report_version: str = HYDE_LARGER_DEV_SUBSET_READINESS_REPORT_VERSION
    readiness_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    work_id: str = WORK_ID
    model_id: str = Field(min_length=1)
    prompt_policy_id: str = Field(min_length=1)
    dataset_path_alias: str = Field(min_length=1)
    result_path: str = Field(min_length=1)
    source_fingerprint: str = Field(min_length=8)
    resolved_device: str = Field(min_length=1)
    selection_strategy_id: str = Field(min_length=1)
    summary: HydeLargerDevReadinessSummary
    query_type_breakdown: tuple[HydeLargerDevQueryTypeSummary, ...]
    rows: tuple[HydeLargerDevReadinessRow, ...]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def run_hyde_larger_dev_subset_readiness(
    *,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    target_query_types: tuple[QueryType, ...] = TARGET_QUERY_TYPES,
    expected_query_count_per_type: int = DEFAULT_EXPECTED_QUERY_COUNT_PER_TYPE,
    live_call_hard_cap: int = DEFAULT_LIVE_CALL_HARD_CAP,
    doc_path: Path = DEFAULT_DOC_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
) -> HydeLargerDevSubsetReadinessReport:
    rows = build_hyde_larger_dev_readiness_rows(
        dataset_path=dataset_path,
        target_query_types=target_query_types,
        expected_query_count_per_type=expected_query_count_per_type,
    )
    summary = build_hyde_larger_dev_readiness_summary(
        rows=rows,
        target_query_types=target_query_types,
        expected_query_count_per_type=expected_query_count_per_type,
        live_call_hard_cap=live_call_hard_cap,
    )
    readiness_id = _readiness_id(rows=rows, summary=summary)
    public_rows = build_public_hyde_larger_dev_readiness_rows(
        readiness_id=readiness_id,
        summary=summary,
        rows=rows,
    )
    provisional_quality = measure_public_retrieval_artifact_quality(
        report_version=HYDE_LARGER_DEV_SUBSET_READINESS_REPORT_VERSION,
        run_id=readiness_id,
        result_rows=public_rows,
        report_text="",
    )
    provisional = build_hyde_larger_dev_readiness_report(
        readiness_id=readiness_id,
        dataset_path=dataset_path,
        result_rows_path=result_rows_path,
        rows=rows,
        summary=summary,
        output_quality=provisional_quality,
    )
    doc_text = build_hyde_larger_dev_readiness_doc(provisional)
    report_text = build_hyde_larger_dev_readiness_markdown(provisional)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=HYDE_LARGER_DEV_SUBSET_READINESS_REPORT_VERSION,
        run_id=readiness_id,
        result_rows=public_rows,
        report_text=report_text,
        extra_public_texts={
            f"doc:{line_number}": line
            for line_number, line in enumerate(doc_text.splitlines(), start=1)
        },
    )
    report = build_hyde_larger_dev_readiness_report(
        readiness_id=readiness_id,
        dataset_path=dataset_path,
        result_rows_path=result_rows_path,
        rows=rows,
        summary=summary,
        output_quality=output_quality,
    )
    failures = collect_hyde_larger_dev_readiness_failures(report)
    if failures:
        raise ValueError(f"HyDE larger dev subset readiness gate failed: {failures}")

    write_public_retrieval_result_rows(
        path=project_path(result_rows_path),
        rows=public_rows,
    )
    resolved_doc_path = project_path(doc_path)
    resolved_report_path = project_path(report_path)
    resolved_doc_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_report_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_doc_path.write_text(
        build_hyde_larger_dev_readiness_doc(report),
        encoding="utf-8",
    )
    resolved_report_path.write_text(
        build_hyde_larger_dev_readiness_markdown(report),
        encoding="utf-8",
    )
    print(
        "hyde_larger_dev_subset_readiness "
        "status=PASS "
        f"query_count={report.summary.query_count} "
        f"expected_hyde_generation_live_call_count="
        f"{report.summary.expected_hyde_generation_live_call_count} "
        f"no_answer_guard_query_count={report.summary.no_answer_guard_query_count} "
        f"decision={report.summary.readiness_decision}",
    )
    return report


def build_hyde_larger_dev_readiness_rows(
    *,
    dataset_path: Path,
    target_query_types: tuple[QueryType, ...] = TARGET_QUERY_TYPES,
    expected_query_count_per_type: int = DEFAULT_EXPECTED_QUERY_COUNT_PER_TYPE,
) -> tuple[HydeLargerDevReadinessRow, ...]:
    items = load_retrieval_eval_jsonl(project_path(dataset_path))
    selected = [
        item
        for item in sorted(items, key=lambda item: item.query.query_id)
        if item.metadata.split == "dev"
        and item.metadata.review_status == "reviewed"
        and item.query.query_type in target_query_types
    ]
    counts = Counter(item.query.query_type for item in selected)
    missing = [
        query_type
        for query_type in target_query_types
        if counts.get(query_type, 0) != expected_query_count_per_type
    ]
    if missing:
        raise ValueError(
            "HyDE larger dev subset requires exact query count per type: "
            f"{missing}",
        )
    return tuple(
        _build_row(item=item, expected_query_count_per_type=expected_query_count_per_type)
        for item in selected
    )


def build_hyde_larger_dev_readiness_summary(
    *,
    rows: tuple[HydeLargerDevReadinessRow, ...],
    target_query_types: tuple[QueryType, ...] = TARGET_QUERY_TYPES,
    expected_query_count_per_type: int = DEFAULT_EXPECTED_QUERY_COUNT_PER_TYPE,
    live_call_hard_cap: int = DEFAULT_LIVE_CALL_HARD_CAP,
) -> HydeLargerDevReadinessSummary:
    expected_calls = sum(row.expected_hyde_generation_call_count for row in rows)
    counts = Counter(row.query_type for row in rows)
    has_expected_distribution = all(
        counts.get(query_type, 0) == expected_query_count_per_type
        for query_type in target_query_types
    )
    hard_cap_exceeded = expected_calls > live_call_hard_cap
    decision: ReadinessDecision = (
        "ready_for_hyde_larger_live_approval"
        if rows
        and has_expected_distribution
        and not hard_cap_exceeded
        and all(not row.public_raw_payload_allowed for row in rows)
        and all(
            row.no_answer_guard_applied
            for row in rows
            if row.query_type == "no_answer"
        )
        else "blocked_by_readiness_gate"
    )
    return HydeLargerDevReadinessSummary(
        query_count=len(rows),
        query_type_count=len(set(counts)),
        target_query_type_count=len(target_query_types),
        expected_query_count_per_type=expected_query_count_per_type,
        answerable_query_count=sum(1 for row in rows if row.expected_behavior == "retrieve"),
        no_answer_query_count=sum(1 for row in rows if row.query_type == "no_answer"),
        hyde_candidate_query_count=sum(1 for row in rows if row.hyde_retrieval_run_required),
        no_answer_guard_query_count=sum(1 for row in rows if row.no_answer_guard_applied),
        baseline_retrieval_run_count=sum(
            1 for row in rows if row.baseline_retrieval_run_required
        ),
        hyde_retrieval_run_count=sum(1 for row in rows if row.hyde_retrieval_run_required),
        expected_hyde_generation_live_call_count=expected_calls,
        live_call_hard_cap=live_call_hard_cap,
        hard_cap_exceeded=hard_cap_exceeded,
        live_execution_requested=False,
        live_execution_confirmed=False,
        solar_call_count=0,
        cuda_required=False,
        readiness_decision=decision,
    )


def build_hyde_larger_dev_readiness_report(
    *,
    readiness_id: str,
    dataset_path: Path,
    result_rows_path: Path,
    rows: tuple[HydeLargerDevReadinessRow, ...],
    summary: HydeLargerDevReadinessSummary,
    output_quality: PublicRetrievalArtifactQuality,
) -> HydeLargerDevSubsetReadinessReport:
    rows_with_id = tuple(
        row.model_copy(update={"readiness_id": readiness_id}) for row in rows
    )
    report = HydeLargerDevSubsetReadinessReport(
        readiness_id=readiness_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        model_id=MODEL_ID,
        prompt_policy_id=PROMPT_POLICY_ID,
        dataset_path_alias=public_path_alias(dataset_path),
        result_path=public_path_alias(result_rows_path),
        source_fingerprint=_stable_id(
            {
                "query_ids": [row.query_id for row in rows_with_id],
                "query_types": [row.query_type for row in rows_with_id],
                "live_call_hard_cap": summary.live_call_hard_cap,
            },
        ),
        resolved_device=str(resolve_torch_device("cuda_if_available")),
        selection_strategy_id=_selection_strategy_id(
            expected_query_count_per_type=summary.expected_query_count_per_type,
        ),
        summary=summary,
        query_type_breakdown=build_hyde_larger_dev_query_type_breakdown(rows_with_id),
        rows=rows_with_id,
        output_quality=output_quality,
        qualitative_assessment={},
    )
    return report.model_copy(
        update={"qualitative_assessment": build_hyde_larger_dev_assessment(report)},
    )


def build_hyde_larger_dev_query_type_breakdown(
    rows: tuple[HydeLargerDevReadinessRow, ...],
) -> tuple[HydeLargerDevQueryTypeSummary, ...]:
    summaries: list[HydeLargerDevQueryTypeSummary] = []
    for query_type in TARGET_QUERY_TYPES:
        subset = [row for row in rows if row.query_type == query_type]
        if not subset:
            continue
        summaries.append(
            HydeLargerDevQueryTypeSummary(
                query_type=query_type,
                query_count=len(subset),
                answerable_query_count=sum(
                    1 for row in subset if row.expected_behavior == "retrieve"
                ),
                no_answer_query_count=sum(1 for row in subset if row.query_type == "no_answer"),
                expected_hyde_generation_live_call_count=sum(
                    row.expected_hyde_generation_call_count for row in subset
                ),
                no_answer_guard_query_count=sum(
                    1 for row in subset if row.no_answer_guard_applied
                ),
                baseline_candidate_id=subset[0].baseline_candidate_id,
                hyde_candidate_id=subset[0].hyde_candidate_id,
            ),
        )
    return tuple(summaries)


def build_public_hyde_larger_dev_readiness_rows(
    *,
    readiness_id: str,
    summary: HydeLargerDevReadinessSummary,
    rows: tuple[HydeLargerDevReadinessRow, ...],
) -> list[dict[str, Any]]:
    public_rows: list[dict[str, Any]] = [
        {
            "row_type": "summary",
            "readiness_id": readiness_id,
            "query_count": summary.query_count,
            "query_type_count": summary.query_type_count,
            "target_query_type_count": summary.target_query_type_count,
            "expected_query_count_per_type": summary.expected_query_count_per_type,
            "answerable_query_count": summary.answerable_query_count,
            "no_answer_query_count": summary.no_answer_query_count,
            "hyde_candidate_query_count": summary.hyde_candidate_query_count,
            "no_answer_guard_query_count": summary.no_answer_guard_query_count,
            "expected_hyde_generation_live_call_count": (
                summary.expected_hyde_generation_live_call_count
            ),
            "live_call_hard_cap": summary.live_call_hard_cap,
            "hard_cap_exceeded": summary.hard_cap_exceeded,
            "live_execution_requested": summary.live_execution_requested,
            "live_execution_confirmed": summary.live_execution_confirmed,
            "solar_call_count": summary.solar_call_count,
            "cuda_required": summary.cuda_required,
            "readiness_decision": summary.readiness_decision,
        },
    ]
    public_rows.extend(
        {
            "row_type": "query_type_summary",
            "readiness_id": readiness_id,
            "query_type": summary_row.query_type,
            "query_count": summary_row.query_count,
            "answerable_query_count": summary_row.answerable_query_count,
            "no_answer_query_count": summary_row.no_answer_query_count,
            "expected_hyde_generation_live_call_count": (
                summary_row.expected_hyde_generation_live_call_count
            ),
            "no_answer_guard_query_count": summary_row.no_answer_guard_query_count,
            "baseline_candidate_id": summary_row.baseline_candidate_id,
            "hyde_candidate_id": summary_row.hyde_candidate_id,
        }
        for summary_row in build_hyde_larger_dev_query_type_breakdown(rows)
    )
    public_rows.extend(
        {
            "row_type": "query_readiness",
            "readiness_id": readiness_id,
            "query_id": row.query_id,
            "query_type": row.query_type,
            "expected_behavior": row.expected_behavior,
            "split_scope": row.split_scope,
            "review_status": row.review_status,
            "selection_strategy_id": row.selection_strategy_id,
            "selection_reason": row.selection_reason,
            "baseline_candidate_id": row.baseline_candidate_id,
            "hyde_candidate_id": row.hyde_candidate_id,
            "expected_hyde_generation_call_count": (
                row.expected_hyde_generation_call_count
            ),
            "no_answer_guard_applied": row.no_answer_guard_applied,
            "readiness_status": row.readiness_status,
            "claim_boundary": row.claim_boundary,
        }
        for row in rows
    )
    return public_rows


def collect_hyde_larger_dev_readiness_failures(
    report: HydeLargerDevSubsetReadinessReport,
) -> list[str]:
    failures = collect_public_retrieval_artifact_failures(report.output_quality)
    summary = report.summary
    if summary.readiness_decision == "blocked_by_readiness_gate":
        failures.append("readiness_decision_blocked")
    if summary.query_count != summary.target_query_type_count * summary.expected_query_count_per_type:
        failures.append("query_count_mismatch")
    if summary.query_type_count != summary.target_query_type_count:
        failures.append("target_query_type_count_mismatch")
    if summary.expected_hyde_generation_live_call_count > summary.live_call_hard_cap:
        failures.append("live_call_hard_cap_exceeded")
    if summary.solar_call_count:
        failures.append("solar_call_executed_in_readiness")
    if summary.live_execution_requested or summary.live_execution_confirmed:
        failures.append("live_execution_enabled_in_readiness")
    if any(row.public_raw_payload_allowed for row in report.rows):
        failures.append("public_raw_payload_allowed")
    if any(
        row.query_type == "no_answer" and not row.no_answer_guard_applied
        for row in report.rows
    ):
        failures.append("no_answer_guard_missing")
    if any(
        row.query_type == "no_answer" and row.hyde_generation_live_call_required
        for row in report.rows
    ):
        failures.append("no_answer_hyde_live_call_planned")
    if any(
        row.query_type != "no_answer" and not row.hyde_generation_live_call_required
        for row in report.rows
    ):
        failures.append("answerable_hyde_live_call_missing")
    return failures


def build_hyde_larger_dev_readiness_doc(
    report: HydeLargerDevSubsetReadinessReport,
) -> str:
    summary = report.summary
    breakdown_rows = "\n".join(
        _format_doc_breakdown_row(row) for row in report.query_type_breakdown
    )
    return f"""# HyDE Larger Dev Subset Readiness

## 결론

`HD-HYDE-001C`는 HyDE larger dev subset live 비교 전 readiness gate다.

청킹 비교는 다시 열지 않는다. 이번 단계는 dev 70 중 HyDE 후보성이 있는 query type만 확대하고 Solar Pro 3 호출 예산과 no-answer guard를 고정한다.

이 문서는 public-safe readiness 문서다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 정량 요약

| metric | value |
| --- | ---: |
| query_count | {summary.query_count} |
| target_query_type_count | {summary.target_query_type_count} |
| expected_query_count_per_type | {summary.expected_query_count_per_type} |
| answerable_query_count | {summary.answerable_query_count} |
| no_answer_query_count | {summary.no_answer_query_count} |
| hyde_candidate_query_count | {summary.hyde_candidate_query_count} |
| no_answer_guard_query_count | {summary.no_answer_guard_query_count} |
| expected_hyde_generation_live_call_count | {summary.expected_hyde_generation_live_call_count} |
| live_call_hard_cap | {summary.live_call_hard_cap} |
| hard_cap_exceeded | {str(summary.hard_cap_exceeded).lower()} |
| solar_call_count | {summary.solar_call_count} |
| cuda_required | {str(summary.cuda_required).lower()} |
| readiness_decision | `{summary.readiness_decision}` |

## Query Type Plan

| query_type | query_count | answerable | no_answer | expected_live_call | no_answer_guard | baseline | hyde_candidate |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
{breakdown_rows}

## 실행 경계

| boundary | value |
| --- | --- |
| live execution | disabled |
| model | `{report.model_id}` |
| prompt policy | `{report.prompt_policy_id}` |
| selection strategy | `{report.selection_strategy_id}` |
| resolved_device | `{report.resolved_device}` |
| final citation | source child chunk only |
| no-answer policy | HyDE generation blocked |
| claim boundary | larger-dev-readiness-only |

## 다음 작업

| priority | work_id | 작업 | 승인 필요 |
| ---: | --- | --- | --- |
| 1 | `HD-HYDE-001D` | HyDE larger dev live paired retrieval comparison | 예 |
| 2 | `HD-API-ROUTER-003` | active routing 적용 판단 계획 | 예 |

## Claim Boundary

| claim | allowed |
| --- | --- |
| HyDE larger live 비교 전 query type 범위와 call budget을 고정했다 | yes |
| readiness 단계에서 Solar Pro 3 live 호출은 0회다 | yes |
| no-answer query 10개는 HyDE generation 후보에서 차단했다 | yes |
| HyDE로 최종 retrieval 성능이 개선됐다 | no |
| no-answer hallucination 문제가 해결됐다 | no |
| locked test 개선을 입증했다 | no |
| production routing을 검증했다 | no |
"""


def build_hyde_larger_dev_readiness_markdown(
    report: HydeLargerDevSubsetReadinessReport,
) -> str:
    summary = report.summary
    quality = report.output_quality
    breakdown_rows = "\n".join(
        _format_report_breakdown_row(row) for row in report.query_type_breakdown
    )
    qualitative_rows = "\n".join(
        f"- `{key}`: {value}" for key, value in report.qualitative_assessment.items()
    )
    return f"""# HyDE Larger Dev Subset Readiness Report

## 목적

`HD-HYDE-001C`는 HyDE live-dev-subset 5개 결과를 확대 검증하기 전 범위, call budget, no-answer guard를 고정한다.

이 리포트는 성능 개선 주장이 아니다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| readiness_id | `{report.readiness_id}` |
| work_id | `{report.work_id}` |
| generated_at_utc | `{report.generated_at_utc}` |
| model_id | `{report.model_id}` |
| prompt_policy_id | `{report.prompt_policy_id}` |
| selection_strategy_id | `{report.selection_strategy_id}` |
| dataset_path | `{report.dataset_path_alias}` |
| result_path | `{report.result_path}` |
| source_fingerprint | `{report.source_fingerprint}` |
| resolved_device | `{report.resolved_device}` |

## 정량 리포트

| metric | value |
| --- | ---: |
| query_count | {summary.query_count} |
| query_type_count | {summary.query_type_count} |
| target_query_type_count | {summary.target_query_type_count} |
| expected_query_count_per_type | {summary.expected_query_count_per_type} |
| answerable_query_count | {summary.answerable_query_count} |
| no_answer_query_count | {summary.no_answer_query_count} |
| hyde_candidate_query_count | {summary.hyde_candidate_query_count} |
| no_answer_guard_query_count | {summary.no_answer_guard_query_count} |
| baseline_retrieval_run_count | {summary.baseline_retrieval_run_count} |
| hyde_retrieval_run_count | {summary.hyde_retrieval_run_count} |
| expected_hyde_generation_live_call_count | {summary.expected_hyde_generation_live_call_count} |
| live_call_hard_cap | {summary.live_call_hard_cap} |
| hard_cap_exceeded | {str(summary.hard_cap_exceeded).lower()} |
| live_execution_requested | {str(summary.live_execution_requested).lower()} |
| live_execution_confirmed | {str(summary.live_execution_confirmed).lower()} |
| solar_call_count | {summary.solar_call_count} |
| cuda_required | {str(summary.cuda_required).lower()} |
| readiness_decision | `{summary.readiness_decision}` |

## Query Type Breakdown

| query_type | query_count | answerable | no_answer | expected_live_call | no_answer_guard | baseline | hyde_candidate |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
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

readiness gate는 통과했다. 다음 단계는 별도 승인 후 `HD-HYDE-001D` live paired retrieval comparison이다.
"""


def build_hyde_larger_dev_assessment(
    report: HydeLargerDevSubsetReadinessReport,
) -> dict[str, str]:
    failures = collect_hyde_larger_dev_readiness_failures(report)
    return {
        "scope": "dev 70 중 overview, place_story, relationship, no_answer 40개만 확대한다.",
        "chunking_boundary": "청킹 비교는 다시 열지 않고 C0 parent-child 기준선을 유지한다.",
        "llm_call_boundary": "readiness 단계에서 Solar Pro 3 live 호출은 수행하지 않는다.",
        "no_answer_boundary": "no_answer query 10개는 HyDE generation과 retrieval 후보에서 차단한다.",
        "retrieval_boundary": "answerable 30개만 HyDE retrieval paired comparison 대상으로 둔다.",
        "citation_boundary": "HyDE 가설은 citation이 아니며 최종 citation은 source child chunk만 허용한다.",
        "cuda_boundary": "readiness는 실행 계획 검증이지만 CUDA 사용 가능 여부를 resolved_device로 기록한다.",
        "data_mart_grain": "`fact_hyde_larger_readiness` grain은 readiness_id + query_id + candidate_id다.",
        "security_boundary": "public artifact에는 query id, type, count, boolean, decision만 남긴다.",
        "external_audit": "5개 subset 결과를 바로 채택하지 않고 40개 readiness로 확대한 판단은 타당하다.",
        "gate_status": "PASS" if not failures else f"FAIL: {', '.join(failures)}",
    }


def _build_row(
    *,
    item: RetrievalEvalItem,
    expected_query_count_per_type: int,
) -> HydeLargerDevReadinessRow:
    query_type = item.query.query_type
    no_answer = query_type == "no_answer"
    return HydeLargerDevReadinessRow(
        readiness_id="pending",
        query_id=item.query.query_id,
        query_type=query_type,
        expected_behavior=item.query.expected_behavior,
        split_scope="dev-only",
        review_status="reviewed",
        selection_strategy_id=_selection_strategy_id(
            expected_query_count_per_type=expected_query_count_per_type,
        ),
        selection_reason=_selection_reason(query_type),
        baseline_candidate_id=_baseline_candidate_id(query_type),
        hyde_candidate_id=(
            NO_ANSWER_GUARD_CANDIDATE_ID if no_answer else HYDE_CANDIDATE_ID
        ),
        prompt_policy_id=PROMPT_POLICY_ID,
        final_citation_source=(
            "no_answer_abstain_guard" if no_answer else "source_child_chunk"
        ),
        baseline_retrieval_run_required=True,
        hyde_retrieval_run_required=not no_answer,
        hyde_generation_live_call_required=not no_answer,
        expected_hyde_generation_call_count=0 if no_answer else 1,
        no_answer_guard_applied=no_answer,
        public_raw_payload_allowed=False,
        readiness_status=(
            "blocked_by_no_answer_guard" if no_answer else "ready_for_live_approval"
        ),
        claim_boundary="larger-dev-readiness-only",
    )


def _selection_strategy_id(*, expected_query_count_per_type: int) -> str:
    return f"hyde_larger_dev_subset_v1_q{expected_query_count_per_type}_per_type"


def _baseline_candidate_id(query_type: QueryType) -> str:
    if query_type == "relationship":
        return "hybrid_weighted_e5_small_alpha_0_5_reference"
    if query_type == "no_answer":
        return "abstain_first_v1"
    return "dense_multilingual_e5_small_voice_rewrite_reference"


def _selection_reason(query_type: QueryType) -> SelectionReason:
    if query_type == "overview":
        return "overview_live_gain_followup"
    if query_type == "place_story":
        return "place_story_retrieval_miss_followup"
    if query_type == "relationship":
        return "relationship_mrr_regression_check"
    if query_type == "no_answer":
        return "no_answer_hallucination_guard"
    raise ValueError(f"unsupported HyDE larger dev query type: {query_type}")


def _readiness_id(
    *,
    rows: tuple[HydeLargerDevReadinessRow, ...],
    summary: HydeLargerDevReadinessSummary,
) -> str:
    digest = _stable_id(
        {
            "query_ids": [row.query_id for row in rows],
            "query_types": [row.query_type for row in rows],
            "expected_live_call_count": summary.expected_hyde_generation_live_call_count,
            "live_call_hard_cap": summary.live_call_hard_cap,
        },
    )
    return (
        "hyde-larger-dev-readiness-"
        f"q{len(rows)}-c{summary.expected_hyde_generation_live_call_count}-{digest}"
    )


def _stable_id(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"),
    ).hexdigest()[:12]


def _format_doc_breakdown_row(row: HydeLargerDevQueryTypeSummary) -> str:
    return (
        f"| `{row.query_type}` | {row.query_count} | {row.answerable_query_count} | "
        f"{row.no_answer_query_count} | {row.expected_hyde_generation_live_call_count} | "
        f"{row.no_answer_guard_query_count} | `{row.baseline_candidate_id}` | "
        f"`{row.hyde_candidate_id}` |"
    )


def _format_report_breakdown_row(row: HydeLargerDevQueryTypeSummary) -> str:
    return _format_doc_breakdown_row(row)


def main() -> int:
    args = _parse_args()
    report = run_hyde_larger_dev_subset_readiness(
        dataset_path=args.dataset,
        target_query_types=tuple(args.query_type or TARGET_QUERY_TYPES),
        expected_query_count_per_type=args.expected_query_count_per_type,
        live_call_hard_cap=args.live_call_hard_cap,
        doc_path=args.doc,
        report_path=args.report,
        result_rows_path=args.results,
    )
    return 0 if not collect_hyde_larger_dev_readiness_failures(report) else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run public-safe HyDE larger dev subset readiness dry-run.",
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--query-type", action="append", default=None)
    parser.add_argument(
        "--expected-query-count-per-type",
        type=int,
        default=DEFAULT_EXPECTED_QUERY_COUNT_PER_TYPE,
    )
    parser.add_argument(
        "--live-call-hard-cap",
        type=int,
        default=DEFAULT_LIVE_CALL_HARD_CAP,
    )
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
