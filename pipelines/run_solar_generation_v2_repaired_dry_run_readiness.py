from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.project_paths import (
    has_private_data_segment,
    is_repository_private_artifact_path,
    is_repository_private_write_path,
)
from app.domain.retrieval import QueryType
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    measure_public_retrieval_artifact_quality,
)
from app.infrastructure.index.device import resolve_torch_device
from pipelines.run_solar_generation_v2_prompt_policy_validator import (
    DEFAULT_QUERY_TYPES,
    PromptPolicyId,
    PromptPolicyValidationReport,
    PromptPolicyValidationRow,
    ValidationStatus,
    build_fake_prompt_policy_validation_inputs,
    build_prompt_policy_validation_report,
)
from pipelines.run_solar_live_generation_smoke import write_jsonl_rows


SOLAR_GENERATION_V2_REPAIRED_DRY_RUN_READINESS_REPORT_VERSION = (
    "solar-generation-v2-repaired-dry-run-readiness-report/v1"
)
DEFAULT_REPORT_PATH = (
    Path("evals") / "reports" / "solar_generation_v2_repaired_dry_run_readiness_report.md"
)
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "solar_generation_v2_repaired_dry_run_readiness_rows.jsonl"
)
DEFAULT_LIVE_CALL_HARD_CAP = 20
REPAIR_ID = "solar_generation_v2_repaired_prompt_policy_v1"
BASELINE_ANSWER_POLICY_ID = "solar-generation-v1-baseline"
REPAIRED_ANSWER_POLICY_ID = "solar-generation-v2-repaired"
ANSWER_CONTRACT_VERSION = "citation-rag-answer/v2"
SYSTEM_PROMPT_VERSION = "solar-pro3-citation-rag-draft-v2-repaired"
MODEL_ID = "solar-pro3"
PROVIDER_CONFIG_ID_ALIAS = "<solar-pro3-repaired-v2-live-config>"
ENDPOINT_ALIAS = "api.upstage.ai/v1/chat/completions"
DEV_SUBSET_QUERY_ID_BY_TYPE: dict[QueryType, str] = {
    "place_fact": "q-dev-place-fact-001",
    "place_story": "q-dev-place-story-001",
    "relationship": "q-dev-relationship-001",
    "overview": "q-dev-overview-001",
    "route_context": "q-dev-route-context-001",
    "voice_followup": "q-dev-voice-followup-001",
    "no_answer": "q-dev-no-answer-001",
}

RepairedRouteDecision = Literal[
    "use_repaired_v2_candidate",
    "use_v1_fallback",
    "abstain_no_live_call",
    "blocked_by_validator_failure",
]
RepairedReuseDecision = Literal[
    "baseline_and_repaired_live_call_required",
    "baseline_only_v1_fallback",
    "no_live_call_required",
    "blocked_no_live_call",
]
ReadinessDecision = Literal[
    "ready_for_repaired_v2_live_approval",
    "blocked_by_readiness_gate",
]


class SolarGenerationV2RepairedDryRunReadinessModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SolarGenerationV2RepairedDryRunRow(
    SolarGenerationV2RepairedDryRunReadinessModel,
):
    query_id: str = Field(min_length=1)
    validation_query_id: str = Field(min_length=1)
    query_type: QueryType
    prompt_policy_id: PromptPolicyId
    validation_status: ValidationStatus
    route_decision: RepairedRouteDecision
    reuse_decision: RepairedReuseDecision
    baseline_input_fingerprint: str = Field(min_length=8)
    repaired_input_fingerprint: str = Field(min_length=8)
    baseline_live_call_required: bool
    repaired_live_call_required: bool
    expected_live_call_count: int = Field(ge=0)
    selected_evidence_count: int = Field(ge=0)
    min_required_evidence_count: int = Field(ge=0)
    available_evidence_count: int = Field(ge=0)
    invalid_rank_count: int = Field(ge=0)
    v1_fallback_allowed: bool
    solar_call_count: int = Field(default=0, ge=0)
    validation_tags: tuple[str, ...]


class SolarGenerationV2RepairedDryRunSummary(
    SolarGenerationV2RepairedDryRunReadinessModel,
):
    expected_query_count: int = Field(ge=1)
    query_count: int = Field(ge=0)
    query_type_count: int = Field(ge=0)
    validation_pass_count: int = Field(ge=0)
    validation_fallback_required_count: int = Field(ge=0)
    validation_fail_count: int = Field(ge=0)
    repaired_candidate_route_count: int = Field(ge=0)
    v1_fallback_route_count: int = Field(ge=0)
    blocked_route_count: int = Field(ge=0)
    baseline_live_call_count: int = Field(ge=0)
    repaired_candidate_live_call_count: int = Field(ge=0)
    no_answer_live_call_count: int = Field(ge=0)
    expected_total_live_call_count: int = Field(ge=0)
    live_call_hard_cap: int = Field(ge=1)
    live_execution_requested: bool
    live_execution_confirmed: bool
    hard_cap_exceeded: bool
    solar_call_count: int = Field(ge=0)
    public_raw_text_leakage_count: int = Field(ge=0)
    private_path_leakage_count: int = Field(ge=0)
    secret_like_leakage_count: int = Field(ge=0)
    forbidden_result_field_count: int = Field(ge=0)
    readiness_decision: ReadinessDecision


class SolarGenerationV2RepairedDryRunQueryTypeSummary(
    SolarGenerationV2RepairedDryRunReadinessModel,
):
    query_type: QueryType
    row_count: int = Field(ge=0)
    route_decision: RepairedRouteDecision
    expected_live_call_count: int = Field(ge=0)


class SolarGenerationV2RepairedDryRunReadinessReport(
    SolarGenerationV2RepairedDryRunReadinessModel,
):
    report_version: str = SOLAR_GENERATION_V2_REPAIRED_DRY_RUN_READINESS_REPORT_VERSION
    readiness_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    source_plan_alias: str = "docs/SOLAR_GENERATION_V2_PROMPT_REPAIR_PLAN.md"
    validation_id: str = Field(min_length=1)
    repair_id: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    provider_config_id_alias: str = Field(min_length=1)
    endpoint_alias: str = Field(min_length=1)
    answer_contract_version: str = Field(min_length=1)
    baseline_answer_policy_id: str = Field(min_length=1)
    repaired_answer_policy_id: str = Field(min_length=1)
    system_prompt_version: str = Field(min_length=1)
    resolved_device: str = Field(min_length=1)
    summary: SolarGenerationV2RepairedDryRunSummary
    query_type_breakdown: tuple[SolarGenerationV2RepairedDryRunQueryTypeSummary, ...]
    rows: tuple[SolarGenerationV2RepairedDryRunRow, ...]
    route_decision_distribution: dict[str, int]
    reuse_decision_distribution: dict[str, int]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def run_solar_generation_v2_repaired_dry_run_readiness(
    *,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
    live_call_hard_cap: int = DEFAULT_LIVE_CALL_HARD_CAP,
) -> SolarGenerationV2RepairedDryRunReadinessReport:
    _validate_result_rows_path(result_rows_path)
    validation_report = build_prompt_policy_validation_report(
        inputs=build_fake_prompt_policy_validation_inputs(),
    )
    provisional = build_solar_generation_v2_repaired_dry_run_readiness_report(
        validation_report=validation_report,
        live_call_hard_cap=live_call_hard_cap,
    )
    provisional_rows = build_public_solar_generation_v2_repaired_dry_run_rows(
        provisional,
    )
    provisional_text = build_solar_generation_v2_repaired_dry_run_markdown(
        provisional,
    )
    report = build_solar_generation_v2_repaired_dry_run_readiness_report(
        validation_report=validation_report,
        live_call_hard_cap=live_call_hard_cap,
        result_rows=provisional_rows,
        report_text=provisional_text,
    )
    failures = collect_solar_generation_v2_repaired_dry_run_failures(report)
    if failures:
        raise ValueError(
            f"solar generation v2 repaired dry-run readiness gate failed: {failures}",
        )

    write_jsonl_rows(
        path=result_rows_path,
        rows=build_public_solar_generation_v2_repaired_dry_run_rows(report),
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        build_solar_generation_v2_repaired_dry_run_markdown(report),
        encoding="utf-8",
    )
    return report


def build_solar_generation_v2_repaired_dry_run_readiness_report(
    *,
    validation_report: PromptPolicyValidationReport,
    live_call_hard_cap: int = DEFAULT_LIVE_CALL_HARD_CAP,
    result_rows: list[dict[str, Any]] | None = None,
    report_text: str = "",
) -> SolarGenerationV2RepairedDryRunReadinessReport:
    rows = tuple(
        build_solar_generation_v2_repaired_dry_run_row(row)
        for row in validation_report.validation_rows
    )
    summary = build_solar_generation_v2_repaired_dry_run_summary(
        rows=rows,
        live_call_hard_cap=live_call_hard_cap,
    )
    readiness_id = _readiness_id(rows=rows, summary=summary)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=SOLAR_GENERATION_V2_REPAIRED_DRY_RUN_READINESS_REPORT_VERSION,
        run_id=readiness_id,
        result_rows=result_rows or [],
        report_text=report_text,
    )
    summary = summary.model_copy(
        update={
            "public_raw_text_leakage_count": output_quality.public_raw_text_leakage_count,
            "private_path_leakage_count": output_quality.private_path_leakage_count,
            "secret_like_leakage_count": output_quality.secret_like_leakage_count,
            "forbidden_result_field_count": output_quality.forbidden_result_field_count,
            "readiness_decision": _readiness_decision(
                summary=summary,
                output_quality=output_quality,
            ),
        },
    )
    report = SolarGenerationV2RepairedDryRunReadinessReport(
        readiness_id=readiness_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        validation_id=validation_report.validation_id,
        repair_id=REPAIR_ID,
        model_id=MODEL_ID,
        provider_config_id_alias=PROVIDER_CONFIG_ID_ALIAS,
        endpoint_alias=ENDPOINT_ALIAS,
        answer_contract_version=ANSWER_CONTRACT_VERSION,
        baseline_answer_policy_id=BASELINE_ANSWER_POLICY_ID,
        repaired_answer_policy_id=REPAIRED_ANSWER_POLICY_ID,
        system_prompt_version=SYSTEM_PROMPT_VERSION,
        resolved_device=resolve_torch_device("auto"),
        summary=summary,
        query_type_breakdown=tuple(build_query_type_breakdown(rows)),
        rows=rows,
        route_decision_distribution=dict(
            sorted(Counter(row.route_decision for row in rows).items()),
        ),
        reuse_decision_distribution=dict(
            sorted(Counter(row.reuse_decision for row in rows).items()),
        ),
        output_quality=output_quality,
        qualitative_assessment={},
    )
    return report.model_copy(
        update={
            "qualitative_assessment": (
                build_solar_generation_v2_repaired_dry_run_assessment(report)
            ),
        },
    )


def build_solar_generation_v2_repaired_dry_run_row(
    validation_row: PromptPolicyValidationRow,
) -> SolarGenerationV2RepairedDryRunRow:
    query_id = DEV_SUBSET_QUERY_ID_BY_TYPE[validation_row.query_type]
    route_decision = _route_decision(validation_row)
    baseline_live_call_required = route_decision in {
        "use_repaired_v2_candidate",
        "use_v1_fallback",
    }
    repaired_live_call_required = route_decision == "use_repaired_v2_candidate"
    expected_live_call_count = int(baseline_live_call_required) + int(
        repaired_live_call_required,
    )
    return SolarGenerationV2RepairedDryRunRow(
        query_id=query_id,
        validation_query_id=validation_row.query_id,
        query_type=validation_row.query_type,
        prompt_policy_id=validation_row.prompt_policy_id,
        validation_status=validation_row.validation_status,
        route_decision=route_decision,
        reuse_decision=_reuse_decision(route_decision),
        baseline_input_fingerprint=_request_fingerprint(
            validation_row=validation_row,
            query_id=query_id,
            answer_policy_id=BASELINE_ANSWER_POLICY_ID,
        ),
        repaired_input_fingerprint=_request_fingerprint(
            validation_row=validation_row,
            query_id=query_id,
            answer_policy_id=REPAIRED_ANSWER_POLICY_ID,
        ),
        baseline_live_call_required=baseline_live_call_required,
        repaired_live_call_required=repaired_live_call_required,
        expected_live_call_count=expected_live_call_count,
        selected_evidence_count=validation_row.selected_evidence_count,
        min_required_evidence_count=validation_row.min_required_evidence_count,
        available_evidence_count=validation_row.available_evidence_count,
        invalid_rank_count=validation_row.invalid_rank_count,
        v1_fallback_allowed=validation_row.v1_fallback_allowed,
        solar_call_count=0,
        validation_tags=validation_row.validation_tags,
    )


def build_solar_generation_v2_repaired_dry_run_summary(
    *,
    rows: tuple[SolarGenerationV2RepairedDryRunRow, ...],
    live_call_hard_cap: int,
) -> SolarGenerationV2RepairedDryRunSummary:
    baseline_live_call_count = sum(1 for row in rows if row.baseline_live_call_required)
    repaired_candidate_live_call_count = sum(1 for row in rows if row.repaired_live_call_required)
    expected_total_live_call_count = sum(row.expected_live_call_count for row in rows)
    no_answer_live_call_count = sum(
        row.expected_live_call_count for row in rows if row.query_type == "no_answer"
    )
    provisional = SolarGenerationV2RepairedDryRunSummary(
        expected_query_count=len(DEFAULT_QUERY_TYPES),
        query_count=len(rows),
        query_type_count=len({row.query_type for row in rows}),
        validation_pass_count=sum(1 for row in rows if row.validation_status == "pass"),
        validation_fallback_required_count=sum(
            1 for row in rows if row.validation_status == "fallback_required"
        ),
        validation_fail_count=sum(1 for row in rows if row.validation_status == "fail"),
        repaired_candidate_route_count=sum(
            1 for row in rows if row.route_decision == "use_repaired_v2_candidate"
        ),
        v1_fallback_route_count=sum(1 for row in rows if row.route_decision == "use_v1_fallback"),
        blocked_route_count=sum(
            1 for row in rows if row.route_decision == "blocked_by_validator_failure"
        ),
        baseline_live_call_count=baseline_live_call_count,
        repaired_candidate_live_call_count=repaired_candidate_live_call_count,
        no_answer_live_call_count=no_answer_live_call_count,
        expected_total_live_call_count=expected_total_live_call_count,
        live_call_hard_cap=live_call_hard_cap,
        live_execution_requested=False,
        live_execution_confirmed=False,
        hard_cap_exceeded=expected_total_live_call_count > live_call_hard_cap,
        solar_call_count=sum(row.solar_call_count for row in rows),
        public_raw_text_leakage_count=0,
        private_path_leakage_count=0,
        secret_like_leakage_count=0,
        forbidden_result_field_count=0,
        readiness_decision="blocked_by_readiness_gate",
    )
    return provisional.model_copy(
        update={
            "readiness_decision": _readiness_decision(
                summary=provisional,
                output_quality=None,
            ),
        },
    )


def build_query_type_breakdown(
    rows: tuple[SolarGenerationV2RepairedDryRunRow, ...],
) -> list[SolarGenerationV2RepairedDryRunQueryTypeSummary]:
    breakdown: list[SolarGenerationV2RepairedDryRunQueryTypeSummary] = []
    for query_type in sorted({row.query_type for row in rows}):
        query_rows = [row for row in rows if row.query_type == query_type]
        expected_live_call_count = sum(row.expected_live_call_count for row in query_rows)
        route_decision = query_rows[0].route_decision
        breakdown.append(
            SolarGenerationV2RepairedDryRunQueryTypeSummary(
                query_type=query_type,
                row_count=len(query_rows),
                route_decision=route_decision,
                expected_live_call_count=expected_live_call_count,
            ),
        )
    return breakdown


def build_public_solar_generation_v2_repaired_dry_run_rows(
    report: SolarGenerationV2RepairedDryRunReadinessReport,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "readiness_id": report.readiness_id,
            "row_type": "summary",
            "expected_query_count": report.summary.expected_query_count,
            "query_count": report.summary.query_count,
            "query_type_count": report.summary.query_type_count,
            "validation_pass_count": report.summary.validation_pass_count,
            "validation_fallback_required_count": (
                report.summary.validation_fallback_required_count
            ),
            "validation_fail_count": report.summary.validation_fail_count,
            "repaired_candidate_route_count": (report.summary.repaired_candidate_route_count),
            "v1_fallback_route_count": report.summary.v1_fallback_route_count,
            "baseline_live_call_count": report.summary.baseline_live_call_count,
            "repaired_candidate_live_call_count": (
                report.summary.repaired_candidate_live_call_count
            ),
            "no_answer_live_call_count": report.summary.no_answer_live_call_count,
            "expected_total_live_call_count": (report.summary.expected_total_live_call_count),
            "live_call_hard_cap": report.summary.live_call_hard_cap,
            "solar_call_count": report.summary.solar_call_count,
            "hard_cap_exceeded": report.summary.hard_cap_exceeded,
            "readiness_decision": report.summary.readiness_decision,
        },
    ]
    rows.extend(
        {
            "readiness_id": report.readiness_id,
            "row_type": "query_readiness",
            "query_id": row.query_id,
            "validation_query_id": row.validation_query_id,
            "query_type": row.query_type,
            "prompt_policy_id": row.prompt_policy_id,
            "validation_status": row.validation_status,
            "route_decision": row.route_decision,
            "reuse_decision": row.reuse_decision,
            "baseline_input_fingerprint": row.baseline_input_fingerprint,
            "repaired_input_fingerprint": row.repaired_input_fingerprint,
            "baseline_live_call_required": row.baseline_live_call_required,
            "repaired_live_call_required": row.repaired_live_call_required,
            "expected_live_call_count": row.expected_live_call_count,
            "selected_evidence_count": row.selected_evidence_count,
            "min_required_evidence_count": row.min_required_evidence_count,
            "available_evidence_count": row.available_evidence_count,
            "invalid_rank_count": row.invalid_rank_count,
            "v1_fallback_allowed": row.v1_fallback_allowed,
            "solar_call_count": row.solar_call_count,
            "validation_tags": list(row.validation_tags),
        }
        for row in report.rows
    )
    return rows


def collect_solar_generation_v2_repaired_dry_run_failures(
    report: SolarGenerationV2RepairedDryRunReadinessReport,
) -> list[str]:
    summary = report.summary
    failures: list[str] = []
    if not report.rows:
        failures.append("empty_repaired_dry_run_rows")
    if summary.query_count != summary.expected_query_count:
        failures.append("query_count_mismatch")
    if summary.query_type_count != len(DEFAULT_QUERY_TYPES):
        failures.append("query_type_coverage_mismatch")
    if summary.validation_fail_count:
        failures.append("prompt_policy_validation_failed")
    if summary.blocked_route_count:
        failures.append("blocked_route_present")
    if summary.solar_call_count:
        failures.append("solar_call_count_must_be_zero")
    if summary.live_execution_requested or summary.live_execution_confirmed:
        failures.append("live_execution_must_remain_blocked")
    if summary.no_answer_live_call_count:
        failures.append("no_answer_live_call_must_be_zero")
    if summary.hard_cap_exceeded:
        failures.append("live_call_hard_cap_exceeded")
    if summary.expected_total_live_call_count > summary.live_call_hard_cap:
        failures.append("expected_total_live_call_over_cap")
    if summary.repaired_candidate_live_call_count == 0:
        failures.append("repaired_candidate_live_call_count_zero")
    if report.output_quality.public_raw_text_leakage_count:
        failures.append("public_raw_text_leakage")
    if report.output_quality.private_path_leakage_count:
        failures.append("private_path_leakage")
    if report.output_quality.secret_like_leakage_count:
        failures.append("secret_like_leakage")
    if report.output_quality.forbidden_result_field_count:
        failures.append("forbidden_public_result_fields")
    return failures


def build_solar_generation_v2_repaired_dry_run_markdown(
    report: SolarGenerationV2RepairedDryRunReadinessReport,
) -> str:
    summary = report.summary
    quality = report.output_quality
    route_rows = "\n".join(
        f"| `{decision}` | {count} |"
        for decision, count in report.route_decision_distribution.items()
    )
    reuse_rows = "\n".join(
        f"| `{decision}` | {count} |"
        for decision, count in report.reuse_decision_distribution.items()
    )
    query_type_rows = "\n".join(_format_query_type_row(row) for row in report.query_type_breakdown)
    query_rows = "\n".join(_format_query_row(row) for row in report.rows)
    qualitative_rows = "\n".join(
        f"- `{key}`: {value}" for key, value in report.qualitative_assessment.items()
    )
    return f"""# Solar Pro 3 Generation v2 Repaired Dry-run Readiness Report

## 목적

HD-SOLAR-026에서 repaired v2 prompt policy를 Solar Pro 3 live paired comparison에 넣기 전에 route, fallback, 예상 live call budget, public-safe gate를 검증한다.

이 리포트는 dry-run readiness 결과다. Solar Pro 3 live 호출은 수행하지 않았고 raw query, raw evidence, raw prompt, raw answer, chunk text는 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| readiness_id | `{report.readiness_id}` |
| generated_at_utc | `{report.generated_at_utc}` |
| source_plan | `{report.source_plan_alias}` |
| validation_id | `{report.validation_id}` |
| repair_id | `{report.repair_id}` |
| model_id | `{report.model_id}` |
| provider_config_id_alias | `{report.provider_config_id_alias}` |
| endpoint_alias | `{report.endpoint_alias}` |
| answer_contract_version | `{report.answer_contract_version}` |
| baseline_answer_policy_id | `{report.baseline_answer_policy_id}` |
| repaired_answer_policy_id | `{report.repaired_answer_policy_id}` |
| system_prompt_version | `{report.system_prompt_version}` |
| resolved_device | `{report.resolved_device}` |

## 정량 리포트

| metric | value |
| --- | ---: |
| expected_query_count | {summary.expected_query_count} |
| query_count | {summary.query_count} |
| query_type_count | {summary.query_type_count} |
| validation_pass_count | {summary.validation_pass_count} |
| validation_fallback_required_count | {summary.validation_fallback_required_count} |
| validation_fail_count | {summary.validation_fail_count} |
| repaired_candidate_route_count | {summary.repaired_candidate_route_count} |
| v1_fallback_route_count | {summary.v1_fallback_route_count} |
| blocked_route_count | {summary.blocked_route_count} |
| baseline_live_call_count | {summary.baseline_live_call_count} |
| repaired_candidate_live_call_count | {summary.repaired_candidate_live_call_count} |
| no_answer_live_call_count | {summary.no_answer_live_call_count} |
| expected_total_live_call_count | {summary.expected_total_live_call_count} |
| live_call_hard_cap | {summary.live_call_hard_cap} |
| live_execution_requested | {summary.live_execution_requested} |
| live_execution_confirmed | {summary.live_execution_confirmed} |
| hard_cap_exceeded | {summary.hard_cap_exceeded} |
| solar_call_count | {summary.solar_call_count} |
| readiness_decision | `{summary.readiness_decision}` |

## Route Decision Distribution

| route_decision | count |
| --- | ---: |
{route_rows}

## Reuse Decision Distribution

| reuse_decision | count |
| --- | ---: |
{reuse_rows}

## Query Type Breakdown

| query_type | rows | route_decision | expected_live_call_count |
| --- | ---: | --- | ---: |
{query_type_rows}

## Query-level Sanitized Readiness

| query_id | query_type | prompt_policy_id | validation | route | reuse | baseline_call | repaired_call | expected_calls | selected | min_required | tags |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
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

## 결론

{_dry_run_conclusion(report)}
"""


def build_solar_generation_v2_repaired_dry_run_assessment(
    report: SolarGenerationV2RepairedDryRunReadinessReport,
) -> dict[str, str]:
    return {
        "comparison_scope": (
            "기존 7개 query type dev subset 구조에서 repaired v2 route와 call budget만 검증했다."
        ),
        "llm_call_boundary": (
            "readiness dry-run 단계라 Solar Pro 3 live 호출은 수행하지 않았고 solar_call_count는 0이다."
        ),
        "fallback_policy": (
            "place_story는 repaired v2 성공률 계산에서 분리하고 v1 fallback route로 둔다."
        ),
        "no_answer_policy": "no_answer는 abstain path를 유지하며 live call을 요구하지 않는다.",
        "call_budget": (
            f"expected_total_live_call_count={report.summary.expected_total_live_call_count}, "
            f"hard_cap={report.summary.live_call_hard_cap}로 제한한다."
        ),
        "data_mart_grain": (
            "`fact_solar_generation_v2_repaired_readiness`의 grain은 repair_id-query_id-query_type-prompt_policy_id-route_decision이다."
        ),
        "security_boundary": (
            "public artifact에는 raw query, raw evidence, raw prompt, raw answer, chunk text, private path, secret을 기록하지 않는다."
        ),
        "external_audit": (
            "route, call budget, public-safe gate가 분리되어 있어 live 품질 개선 주장으로 과장되지 않는다."
        ),
        "next_action": _next_action(report),
    }


def _route_decision(row: PromptPolicyValidationRow) -> RepairedRouteDecision:
    if row.validation_status == "fail":
        return "blocked_by_validator_failure"
    if row.query_type == "no_answer":
        return "abstain_no_live_call"
    if row.validation_status == "fallback_required":
        return "use_v1_fallback"
    return "use_repaired_v2_candidate"


def _reuse_decision(route_decision: RepairedRouteDecision) -> RepairedReuseDecision:
    if route_decision == "use_repaired_v2_candidate":
        return "baseline_and_repaired_live_call_required"
    if route_decision == "use_v1_fallback":
        return "baseline_only_v1_fallback"
    if route_decision == "abstain_no_live_call":
        return "no_live_call_required"
    return "blocked_no_live_call"


def _readiness_decision(
    *,
    summary: SolarGenerationV2RepairedDryRunSummary,
    output_quality: PublicRetrievalArtifactQuality | None,
) -> ReadinessDecision:
    output_blocked = output_quality is not None and (
        output_quality.public_raw_text_leakage_count
        or output_quality.private_path_leakage_count
        or output_quality.secret_like_leakage_count
        or output_quality.forbidden_result_field_count
    )
    gate_blocked = (
        summary.query_count != summary.expected_query_count
        or summary.query_type_count != len(DEFAULT_QUERY_TYPES)
        or summary.validation_fail_count > 0
        or summary.blocked_route_count > 0
        or summary.solar_call_count > 0
        or summary.live_execution_requested
        or summary.live_execution_confirmed
        or summary.no_answer_live_call_count > 0
        or summary.hard_cap_exceeded
        or summary.repaired_candidate_live_call_count == 0
        or output_blocked
    )
    if gate_blocked:
        return "blocked_by_readiness_gate"
    return "ready_for_repaired_v2_live_approval"


def _request_fingerprint(
    *,
    validation_row: PromptPolicyValidationRow,
    query_id: str,
    answer_policy_id: str,
) -> str:
    payload = {
        "answer_contract_version": ANSWER_CONTRACT_VERSION,
        "answer_policy_id": answer_policy_id,
        "system_prompt_version": SYSTEM_PROMPT_VERSION,
        "model_id": MODEL_ID,
        "query_id": query_id,
        "query_type": validation_row.query_type,
        "prompt_policy_id": validation_row.prompt_policy_id,
        "selected_evidence_count": validation_row.selected_evidence_count,
        "min_required_evidence_count": validation_row.min_required_evidence_count,
        "available_evidence_count": validation_row.available_evidence_count,
        "validation_status": validation_row.validation_status,
    }
    return _stable_digest(payload, length=16)


def _readiness_id(
    *,
    rows: tuple[SolarGenerationV2RepairedDryRunRow, ...],
    summary: SolarGenerationV2RepairedDryRunSummary,
) -> str:
    payload = {
        "rows": [row.model_dump(mode="json") for row in rows],
        "summary": summary.model_dump(mode="json"),
    }
    digest = _stable_digest(payload, length=8)
    return f"solar-generation-v2-repaired-dry-run-q{summary.query_count}-{digest}"


def _stable_digest(payload: Any, *, length: int = 12) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"),
    ).hexdigest()[:length]


def _format_query_type_row(
    row: SolarGenerationV2RepairedDryRunQueryTypeSummary,
) -> str:
    return (
        f"| {row.query_type} | {row.row_count} | `{row.route_decision}` | "
        f"{row.expected_live_call_count} |"
    )


def _format_query_row(row: SolarGenerationV2RepairedDryRunRow) -> str:
    tags = ", ".join(row.validation_tags)
    return (
        f"| `{row.query_id}` | {row.query_type} | `{row.prompt_policy_id}` | "
        f"`{row.validation_status}` | `{row.route_decision}` | "
        f"`{row.reuse_decision}` | {row.baseline_live_call_required} | "
        f"{row.repaired_live_call_required} | {row.expected_live_call_count} | "
        f"{row.selected_evidence_count} | {row.min_required_evidence_count} | {tags} |"
    )


def _next_action(report: SolarGenerationV2RepairedDryRunReadinessReport) -> str:
    failures = collect_solar_generation_v2_repaired_dry_run_failures(report)
    if failures:
        return "readiness failure를 먼저 수정하고 live paired comparison 승인을 보류한다."
    return "별도 승인 후 repaired v2 Solar Pro 3 live paired comparison 실행 여부를 결정한다."


def _dry_run_conclusion(report: SolarGenerationV2RepairedDryRunReadinessReport) -> str:
    failures = collect_solar_generation_v2_repaired_dry_run_failures(report)
    if failures:
        return (
            f"readiness gate가 실패했다: {', '.join(failures)}.\n\n"
            "Solar Pro 3 live 호출로 넘어가면 안 된다."
        )
    return (
        "readiness gate를 통과했다.\n\n"
        "이 결과는 live 품질 개선 주장이 아니라, repaired v2 live paired comparison 실행 전 route, fallback, call budget, public-safe boundary가 계획 범위 안에 있다는 검증이다."
    )


def _validate_result_rows_path(path: Path) -> None:
    if has_private_data_segment(path) and not is_repository_private_artifact_path(path):
        raise ValueError("private_data result rows must stay under repository private_data")
    if has_private_data_segment(path) and not is_repository_private_write_path(path):
        raise ValueError("private readiness rows must be written under private_data")


def main() -> int:
    args = _parse_args()
    report = run_solar_generation_v2_repaired_dry_run_readiness(
        report_path=args.report,
        result_rows_path=args.result_rows,
        live_call_hard_cap=args.live_call_hard_cap,
    )
    failures = collect_solar_generation_v2_repaired_dry_run_failures(report)
    print(
        "solar_generation_v2_repaired_dry_run_readiness "
        f"status={'PASS' if not failures else 'FAIL'} "
        f"query_count={report.summary.query_count} "
        f"expected_calls={report.summary.expected_total_live_call_count} "
        f"candidate_calls={report.summary.repaired_candidate_live_call_count} "
        f"fallback_routes={report.summary.v1_fallback_route_count} "
        f"decision={report.summary.readiness_decision} "
        f"device={report.resolved_device} "
        f"solar_calls={report.summary.solar_call_count} "
        f"failures={len(failures)}",
    )
    return 0 if not failures else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Solar Pro 3 generation v2 repaired dry-run readiness.",
    )
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--result-rows", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    parser.add_argument("--live-call-hard-cap", type=int, default=DEFAULT_LIVE_CALL_HARD_CAP)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
