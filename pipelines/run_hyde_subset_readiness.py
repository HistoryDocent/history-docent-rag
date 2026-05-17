from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.project_paths import project_path
from app.domain.retrieval import QueryType, load_retrieval_eval_jsonl
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    collect_public_retrieval_artifact_failures,
    measure_public_retrieval_artifact_quality,
    public_path_alias,
    write_public_retrieval_result_rows,
)
from app.infrastructure.index.device import resolve_torch_device
from pipelines.run_solar_live_generation_smoke import DEFAULT_DATASET_PATH


HYDE_SUBSET_READINESS_REPORT_VERSION = "hyde-subset-readiness-report/v1"
DEFAULT_QUERY_IDS: tuple[str, ...] = (
    "q-dev-place-story-001",
    "q-dev-place-story-008",
    "q-dev-relationship-008",
    "q-dev-overview-010",
    "q-dev-no-answer-001",
)
DEFAULT_LIVE_CALL_HARD_CAP = 10
DEFAULT_DOC_PATH = Path("docs") / "HYDE_SUBSET_READINESS.md"
DEFAULT_REPORT_PATH = Path("evals") / "reports" / "hyde_subset_readiness_report.md"
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data") / "evals" / "results" / "hyde_subset_readiness_rows.jsonl"
)
MODEL_ID = "solar-pro3"
PROMPT_POLICY_ID = "solar-pro3-hyde-query-expansion-v1"
HYDE_CANDIDATE_ID = "solar_pro3_hyde_v1"
NO_ANSWER_GUARD_CANDIDATE_ID = "blocked_for_no_answer_guard"

SubsetReason = Literal[
    "place_story_targeted_audit_followup",
    "place_story_retrieval_miss",
    "relationship_retrieval_miss",
    "overview_retrieval_miss",
    "no_answer_hallucination_guard",
]
ReadinessStatus = Literal["ready_for_live_approval", "blocked_by_no_answer_guard"]
ReadinessDecision = Literal[
    "ready_for_hyde_live_approval",
    "blocked_by_readiness_gate",
]


class HydeSubsetReadinessModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class HydeSubsetReadinessRow(HydeSubsetReadinessModel):
    readiness_id: str = Field(min_length=1)
    query_id: str = Field(min_length=1)
    query_type: QueryType
    expected_behavior: Literal["retrieve", "abstain"]
    split_scope: str = Field(min_length=1)
    subset_reason: SubsetReason
    baseline_candidate_id: str = Field(min_length=1)
    hyde_candidate_id: str = Field(min_length=1)
    prompt_policy_id: str = Field(min_length=1)
    final_citation_source: Literal["source_child_chunk", "no_answer_abstain_guard"]
    baseline_retrieval_run_required: bool
    hyde_retrieval_run_required: bool
    hyde_generation_live_call_required: bool
    expected_hyde_generation_call_count: int = Field(ge=0)
    no_answer_guard_applied: bool
    hallucination_guard_required: bool
    public_raw_payload_allowed: bool
    readiness_status: ReadinessStatus
    success_gate: str = Field(min_length=1)
    risk_tag: str = Field(min_length=1)
    claim_boundary: str = Field(min_length=1)


class HydeSubsetReadinessSummary(HydeSubsetReadinessModel):
    query_count: int = Field(ge=0)
    query_type_count: int = Field(ge=0)
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


class HydeSubsetReadinessQueryTypeSummary(HydeSubsetReadinessModel):
    query_type: QueryType
    query_count: int = Field(ge=0)
    expected_hyde_generation_live_call_count: int = Field(ge=0)
    no_answer_guard_query_count: int = Field(ge=0)


class HydeSubsetReadinessReport(HydeSubsetReadinessModel):
    report_version: str = HYDE_SUBSET_READINESS_REPORT_VERSION
    readiness_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    work_id: str = "HD-HYDE-001A"
    model_id: str = Field(min_length=1)
    prompt_policy_id: str = Field(min_length=1)
    dataset_path_alias: str = Field(min_length=1)
    result_path: str = Field(min_length=1)
    source_fingerprint: str = Field(min_length=8)
    resolved_device: str = Field(min_length=1)
    summary: HydeSubsetReadinessSummary
    query_type_breakdown: tuple[HydeSubsetReadinessQueryTypeSummary, ...]
    rows: tuple[HydeSubsetReadinessRow, ...]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def run_hyde_subset_readiness(
    *,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    query_ids: tuple[str, ...] = DEFAULT_QUERY_IDS,
    live_call_hard_cap: int = DEFAULT_LIVE_CALL_HARD_CAP,
    doc_path: Path = DEFAULT_DOC_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
) -> HydeSubsetReadinessReport:
    rows = build_hyde_subset_readiness_rows(
        dataset_path=dataset_path,
        query_ids=query_ids,
    )
    summary = build_hyde_subset_readiness_summary(
        rows=rows,
        live_call_hard_cap=live_call_hard_cap,
    )
    readiness_id = _readiness_id(rows=rows, summary=summary)
    public_rows = build_public_hyde_subset_readiness_rows(
        readiness_id=readiness_id,
        summary=summary,
        rows=rows,
    )
    write_public_retrieval_result_rows(
        path=project_path(result_rows_path),
        rows=public_rows,
    )

    provisional_quality = measure_public_retrieval_artifact_quality(
        report_version=HYDE_SUBSET_READINESS_REPORT_VERSION,
        run_id=readiness_id,
        result_rows=public_rows,
        report_text="",
    )
    provisional = build_hyde_subset_readiness_report(
        readiness_id=readiness_id,
        dataset_path=dataset_path,
        result_rows_path=result_rows_path,
        rows=rows,
        summary=summary,
        output_quality=provisional_quality,
    )
    doc_text = build_hyde_subset_readiness_doc(provisional)
    report_text = build_hyde_subset_readiness_markdown(provisional)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=HYDE_SUBSET_READINESS_REPORT_VERSION,
        run_id=readiness_id,
        result_rows=public_rows,
        report_text=report_text,
        extra_public_texts={
            f"doc:{line_number}": line
            for line_number, line in enumerate(doc_text.splitlines(), start=1)
        },
    )
    report = build_hyde_subset_readiness_report(
        readiness_id=readiness_id,
        dataset_path=dataset_path,
        result_rows_path=result_rows_path,
        rows=rows,
        summary=summary,
        output_quality=output_quality,
    )
    failures = collect_hyde_subset_readiness_failures(report)
    if failures:
        raise ValueError(f"HyDE subset readiness gate failed: {failures}")

    resolved_doc_path = project_path(doc_path)
    resolved_report_path = project_path(report_path)
    resolved_doc_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_report_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_doc_path.write_text(build_hyde_subset_readiness_doc(report), encoding="utf-8")
    resolved_report_path.write_text(
        build_hyde_subset_readiness_markdown(report),
        encoding="utf-8",
    )
    print(
        "hyde_subset_readiness "
        "status=PASS "
        f"query_count={report.summary.query_count} "
        f"expected_hyde_generation_live_call_count="
        f"{report.summary.expected_hyde_generation_live_call_count} "
        f"no_answer_guard_query_count={report.summary.no_answer_guard_query_count} "
        f"decision={report.summary.readiness_decision}",
    )
    return report


def build_hyde_subset_readiness_rows(
    *,
    dataset_path: Path,
    query_ids: tuple[str, ...] = DEFAULT_QUERY_IDS,
) -> tuple[HydeSubsetReadinessRow, ...]:
    items_by_id = {
        item.query.query_id: item
        for item in load_retrieval_eval_jsonl(project_path(dataset_path))
    }
    missing = [query_id for query_id in query_ids if query_id not in items_by_id]
    if missing:
        raise ValueError(f"HyDE subset query not found: {missing}")
    placeholder_id = "pending"
    return tuple(
        build_hyde_subset_readiness_row(
            readiness_id=placeholder_id,
            query_id=query_id,
            query_type=items_by_id[query_id].query.query_type,
            expected_behavior=items_by_id[query_id].query.expected_behavior,
        )
        for query_id in query_ids
    )


def build_hyde_subset_readiness_row(
    *,
    readiness_id: str,
    query_id: str,
    query_type: QueryType,
    expected_behavior: Literal["retrieve", "abstain"],
) -> HydeSubsetReadinessRow:
    no_answer = query_type == "no_answer"
    return HydeSubsetReadinessRow(
        readiness_id=readiness_id,
        query_id=query_id,
        query_type=query_type,
        expected_behavior=expected_behavior,
        split_scope="dev-only",
        subset_reason=_subset_reason(query_id=query_id, query_type=query_type),
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
        hallucination_guard_required=True,
        public_raw_payload_allowed=False,
        readiness_status=(
            "blocked_by_no_answer_guard" if no_answer else "ready_for_live_approval"
        ),
        success_gate=_success_gate(query_type),
        risk_tag=_risk_tag(query_type),
        claim_boundary="dev-readiness-only",
    )


def build_hyde_subset_readiness_summary(
    *,
    rows: tuple[HydeSubsetReadinessRow, ...],
    live_call_hard_cap: int = DEFAULT_LIVE_CALL_HARD_CAP,
) -> HydeSubsetReadinessSummary:
    expected_calls = sum(row.expected_hyde_generation_call_count for row in rows)
    hard_cap_exceeded = expected_calls > live_call_hard_cap
    decision: ReadinessDecision = (
        "ready_for_hyde_live_approval"
        if rows
        and not hard_cap_exceeded
        and all(not row.public_raw_payload_allowed for row in rows)
        and all(
            row.no_answer_guard_applied
            for row in rows
            if row.query_type == "no_answer"
        )
        else "blocked_by_readiness_gate"
    )
    return HydeSubsetReadinessSummary(
        query_count=len(rows),
        query_type_count=len({row.query_type for row in rows}),
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


def build_hyde_subset_readiness_report(
    *,
    readiness_id: str,
    dataset_path: Path,
    result_rows_path: Path,
    rows: tuple[HydeSubsetReadinessRow, ...],
    summary: HydeSubsetReadinessSummary,
    output_quality: PublicRetrievalArtifactQuality,
) -> HydeSubsetReadinessReport:
    rows_with_id = tuple(
        row.model_copy(update={"readiness_id": readiness_id}) for row in rows
    )
    report = HydeSubsetReadinessReport(
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
        summary=summary,
        query_type_breakdown=build_hyde_subset_query_type_breakdown(rows_with_id),
        rows=rows_with_id,
        output_quality=output_quality,
        qualitative_assessment={},
    )
    return report.model_copy(
        update={
            "qualitative_assessment": build_hyde_subset_readiness_assessment(report),
        },
    )


def build_hyde_subset_query_type_breakdown(
    rows: tuple[HydeSubsetReadinessRow, ...],
) -> tuple[HydeSubsetReadinessQueryTypeSummary, ...]:
    query_types = sorted({row.query_type for row in rows})
    return tuple(
        HydeSubsetReadinessQueryTypeSummary(
            query_type=query_type,
            query_count=sum(1 for row in rows if row.query_type == query_type),
            expected_hyde_generation_live_call_count=sum(
                row.expected_hyde_generation_call_count
                for row in rows
                if row.query_type == query_type
            ),
            no_answer_guard_query_count=sum(
                1
                for row in rows
                if row.query_type == query_type and row.no_answer_guard_applied
            ),
        )
        for query_type in query_types
    )


def build_public_hyde_subset_readiness_rows(
    *,
    readiness_id: str,
    summary: HydeSubsetReadinessSummary,
    rows: tuple[HydeSubsetReadinessRow, ...],
) -> list[dict[str, Any]]:
    public_rows: list[dict[str, Any]] = [
        {
            "row_type": "summary",
            "readiness_id": readiness_id,
            "query_count": summary.query_count,
            "query_type_count": summary.query_type_count,
            "answerable_query_count": summary.answerable_query_count,
            "no_answer_query_count": summary.no_answer_query_count,
            "hyde_candidate_query_count": summary.hyde_candidate_query_count,
            "no_answer_guard_query_count": summary.no_answer_guard_query_count,
            "baseline_retrieval_run_count": summary.baseline_retrieval_run_count,
            "hyde_retrieval_run_count": summary.hyde_retrieval_run_count,
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
            "row_type": "query_readiness",
            "readiness_id": readiness_id,
            "query_id": row.query_id,
            "query_type": row.query_type,
            "expected_behavior": row.expected_behavior,
            "split_scope": row.split_scope,
            "subset_reason": row.subset_reason,
            "baseline_candidate_id": row.baseline_candidate_id,
            "hyde_candidate_id": row.hyde_candidate_id,
            "final_citation_source": row.final_citation_source,
            "baseline_retrieval_run_required": row.baseline_retrieval_run_required,
            "hyde_retrieval_run_required": row.hyde_retrieval_run_required,
            "hyde_generation_live_call_required": (
                row.hyde_generation_live_call_required
            ),
            "expected_hyde_generation_call_count": (
                row.expected_hyde_generation_call_count
            ),
            "no_answer_guard_applied": row.no_answer_guard_applied,
            "hallucination_guard_required": row.hallucination_guard_required,
            "public_raw_payload_allowed": row.public_raw_payload_allowed,
            "readiness_status": row.readiness_status,
            "risk_tag": row.risk_tag,
            "claim_boundary": row.claim_boundary,
        }
        for row in rows
    )
    return public_rows


def collect_hyde_subset_readiness_failures(
    report: HydeSubsetReadinessReport,
) -> list[str]:
    failures = collect_public_retrieval_artifact_failures(report.output_quality)
    summary = report.summary
    if summary.readiness_decision == "blocked_by_readiness_gate":
        failures.append("readiness_decision_blocked")
    if summary.query_count != len(DEFAULT_QUERY_IDS):
        failures.append("query_count_mismatch")
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
    if any(
        row.query_type != "no_answer"
        and row.final_citation_source != "source_child_chunk"
        for row in report.rows
    ):
        failures.append("final_citation_source_not_child_chunk")
    return failures


def build_hyde_subset_readiness_doc(report: HydeSubsetReadinessReport) -> str:
    summary = report.summary
    query_rows = "\n".join(_format_hyde_doc_query_row(row) for row in report.rows)
    return f"""# HyDE Subset Readiness

## 결론

`HD-HYDE-001A`는 live HyDE 비교 전 readiness gate다.

청킹 비교는 다시 열지 않는다. HyDE는 retrieval miss와 no-answer risk를 분리해 검증하는 비용성 실험 후보로만 둔다.

이 문서는 public-safe readiness 문서다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 정량 요약

| metric | value |
| --- | ---: |
| query_count | {summary.query_count} |
| query_type_count | {summary.query_type_count} |
| answerable_query_count | {summary.answerable_query_count} |
| no_answer_query_count | {summary.no_answer_query_count} |
| hyde_candidate_query_count | {summary.hyde_candidate_query_count} |
| no_answer_guard_query_count | {summary.no_answer_guard_query_count} |
| baseline_retrieval_run_count | {summary.baseline_retrieval_run_count} |
| hyde_retrieval_run_count | {summary.hyde_retrieval_run_count} |
| expected_hyde_generation_live_call_count | {summary.expected_hyde_generation_live_call_count} |
| live_call_hard_cap | {summary.live_call_hard_cap} |
| hard_cap_exceeded | {str(summary.hard_cap_exceeded).lower()} |
| solar_call_count | {summary.solar_call_count} |
| cuda_required | {str(summary.cuda_required).lower()} |
| readiness_decision | `{summary.readiness_decision}` |

## Query Plan

| query_id | query_type | baseline | hyde_candidate | live_call | no_answer_guard | readiness_status |
| --- | --- | --- | --- | ---: | --- | --- |
{query_rows}

## 실행 경계

| boundary | value |
| --- | --- |
| live execution | disabled |
| model | `{report.model_id}` |
| prompt policy | `{report.prompt_policy_id}` |
| final citation | source child chunk only |
| no-answer policy | HyDE generation blocked |
| claim boundary | dev-readiness-only |

## 다음 작업

| priority | work_id | 작업 | 승인 필요 |
| ---: | --- | --- | --- |
| 1 | `HD-HYDE-001B` | Solar Pro 3 HyDE live paired retrieval comparison | 예 |
| 2 | `HD-API-ROUTER-003` | active routing 적용 판단 계획 | 예 |

## Claim Boundary

허용 표현:

- HyDE live 비교 전 subset, call budget, no-answer guard를 고정했다.
- readiness 단계에서 Solar Pro 3 live 호출은 0회다.
- HyDE 성능 개선은 아직 입증하지 않았다.

금지 표현:

- HyDE로 retrieval 성능이 개선됐다.
- no-answer hallucination 문제가 해결됐다.
- locked test 개선을 입증했다.
- production routing을 검증했다.
"""


def build_hyde_subset_readiness_markdown(report: HydeSubsetReadinessReport) -> str:
    summary = report.summary
    quality = report.output_quality
    query_rows = "\n".join(_format_hyde_report_query_row(row) for row in report.rows)
    breakdown_rows = "\n".join(
        _format_hyde_breakdown_row(row) for row in report.query_type_breakdown
    )
    qualitative_rows = "\n".join(
        f"- `{key}`: {value}" for key, value in report.qualitative_assessment.items()
    )
    return f"""# HyDE Subset Readiness Report

## 목적

`HD-HYDE-001A`는 Solar Pro 3 기반 HyDE live 비교를 실행하기 전 subset, call budget, no-answer guard, public-safe gate를 고정한다.

이 리포트는 HyDE 성능 개선 주장이 아니다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| readiness_id | `{report.readiness_id}` |
| work_id | `{report.work_id}` |
| generated_at_utc | `{report.generated_at_utc}` |
| model_id | `{report.model_id}` |
| prompt_policy_id | `{report.prompt_policy_id}` |
| dataset_path | `{report.dataset_path_alias}` |
| result_path | `{report.result_path}` |
| source_fingerprint | `{report.source_fingerprint}` |
| resolved_device | `{report.resolved_device}` |

## 정량 리포트

| metric | value |
| --- | ---: |
| query_count | {summary.query_count} |
| query_type_count | {summary.query_type_count} |
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

| query_type | query_count | expected_hyde_generation_live_call_count | no_answer_guard_query_count |
| --- | ---: | ---: | ---: |
{breakdown_rows}

## Query Readiness Rows

| query_id | query_type | expected_behavior | subset_reason | baseline | hyde_candidate | expected_live_call | guard | status |
| --- | --- | --- | --- | --- | --- | ---: | --- | --- |
{query_rows}

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

readiness gate는 통과했다. 다음 단계는 별도 승인 후 `HD-HYDE-001B` live paired retrieval comparison이다.
"""


def build_hyde_subset_readiness_assessment(
    report: HydeSubsetReadinessReport,
) -> dict[str, str]:
    failures = collect_hyde_subset_readiness_failures(report)
    return {
        "scope": "HyDE live 비교 전 subset과 call budget만 검증한다.",
        "chunking_boundary": "청킹 비교는 다시 열지 않고 C0 parent-child 기준선을 유지한다.",
        "llm_call_boundary": "readiness 단계에서 Solar Pro 3 live 호출은 수행하지 않는다.",
        "no_answer_boundary": "no_answer query는 HyDE generation 후보에서 차단한다.",
        "retrieval_boundary": "answerable query만 baseline retrieval과 HyDE retrieval을 paired 비교 대상으로 둔다.",
        "citation_boundary": "HyDE로 생성한 가설은 citation이 아니며 최종 citation은 source child chunk만 허용한다.",
        "cuda_boundary": "이번 readiness는 LLM call budget 검증이라 CUDA 연산이 필요하지 않다.",
        "data_mart_grain": "`fact_hyde_subset_readiness` grain은 readiness_id + query_id + candidate_id다.",
        "security_boundary": "public artifact에는 id, count, boolean, decision만 남긴다.",
        "external_audit": "live 실행 전에 no-answer guard와 call cap을 고정한 판단은 타당하다.",
        "gate_status": "PASS" if not failures else f"FAIL: {', '.join(failures)}",
    }


def _baseline_candidate_id(query_type: QueryType) -> str:
    if query_type == "relationship":
        return "hybrid_weighted_e5_small_alpha_0_5_reference"
    if query_type == "no_answer":
        return "abstain_first_v1"
    return "dense_multilingual_e5_small_voice_rewrite_reference"


def _subset_reason(*, query_id: str, query_type: QueryType) -> SubsetReason:
    if query_id == "q-dev-place-story-001":
        return "place_story_targeted_audit_followup"
    if query_type == "place_story":
        return "place_story_retrieval_miss"
    if query_type == "relationship":
        return "relationship_retrieval_miss"
    if query_type == "overview":
        return "overview_retrieval_miss"
    if query_type == "no_answer":
        return "no_answer_hallucination_guard"
    raise ValueError(f"unsupported HyDE subset query type: {query_type}")


def _success_gate(query_type: QueryType) -> str:
    if query_type == "no_answer":
        return "abstention is preserved and HyDE live call remains blocked"
    if query_type == "relationship":
        return "Recall/MRR/nDCG improves against hybrid relationship reference"
    return "Recall/MRR/nDCG improves without citation recoverability loss"


def _risk_tag(query_type: QueryType) -> str:
    if query_type == "no_answer":
        return "hypothetical_answer_hallucination"
    if query_type == "relationship":
        return "relationship_bridge_overexpansion"
    if query_type == "overview":
        return "broad_summary_topic_drift"
    if query_type == "place_story":
        return "narrative_context_overexpansion"
    return "hyde_candidate_risk"


def _format_hyde_doc_query_row(row: HydeSubsetReadinessRow) -> str:
    return (
        f"| `{row.query_id}` | `{row.query_type}` | `{row.baseline_candidate_id}` | "
        f"`{row.hyde_candidate_id}` | {row.expected_hyde_generation_call_count} | "
        f"{str(row.no_answer_guard_applied).lower()} | `{row.readiness_status}` |"
    )


def _format_hyde_report_query_row(row: HydeSubsetReadinessRow) -> str:
    return (
        f"| `{row.query_id}` | `{row.query_type}` | `{row.expected_behavior}` | "
        f"`{row.subset_reason}` | `{row.baseline_candidate_id}` | "
        f"`{row.hyde_candidate_id}` | {row.expected_hyde_generation_call_count} | "
        f"{str(row.no_answer_guard_applied).lower()} | `{row.readiness_status}` |"
    )


def _format_hyde_breakdown_row(row: HydeSubsetReadinessQueryTypeSummary) -> str:
    return (
        f"| `{row.query_type}` | {row.query_count} | "
        f"{row.expected_hyde_generation_live_call_count} | "
        f"{row.no_answer_guard_query_count} |"
    )


def _readiness_id(
    *,
    rows: tuple[HydeSubsetReadinessRow, ...],
    summary: HydeSubsetReadinessSummary,
) -> str:
    digest = _stable_id(
        {
            "query_ids": [row.query_id for row in rows],
            "query_types": [row.query_type for row in rows],
            "expected_live_call_count": summary.expected_hyde_generation_live_call_count,
            "live_call_hard_cap": summary.live_call_hard_cap,
        },
    )
    return f"hyde-subset-readiness-q{len(rows)}-c{summary.expected_hyde_generation_live_call_count}-{digest}"


def _stable_id(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"),
    ).hexdigest()[:12]


def main() -> int:
    args = _parse_args()
    report = run_hyde_subset_readiness(
        dataset_path=args.dataset,
        query_ids=tuple(args.query_id or DEFAULT_QUERY_IDS),
        live_call_hard_cap=args.live_call_hard_cap,
        doc_path=args.doc,
        report_path=args.report,
        result_rows_path=args.results,
    )
    return 0 if not collect_hyde_subset_readiness_failures(report) else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run public-safe HyDE subset readiness dry-run.",
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument(
        "--query-id",
        action="append",
        default=None,
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
