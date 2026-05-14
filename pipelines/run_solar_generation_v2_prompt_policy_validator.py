from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.application.evidence_packing import EvidencePack, PackedEvidence
from app.core.project_paths import (
    has_private_data_segment,
    is_repository_private_artifact_path,
    is_repository_private_write_path,
)
from app.domain.generation import CitationRagDraftV2
from app.domain.retrieval import QueryType, RetrievalEvalItem
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    measure_public_retrieval_artifact_quality,
)
from pipelines.run_solar_live_generation_smoke import write_jsonl_rows


SOLAR_GENERATION_V2_PROMPT_POLICY_VALIDATOR_REPORT_VERSION = (
    "solar-generation-v2-prompt-policy-validator-report/v1"
)
DEFAULT_REPORT_PATH = (
    Path("evals") / "reports" / "solar_generation_v2_prompt_policy_validator_report.md"
)
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "solar_generation_v2_prompt_policy_validator_rows.jsonl"
)

PromptPolicyId = Literal[
    "v2_repair_coverage_floor",
    "v2_repair_risk_aware_selection",
    "v2_repair_query_type_router",
]
ValidationStatus = Literal["pass", "fallback_required", "fail"]
ReadinessDecision = Literal[
    "ready_for_repaired_prompt_dry_run",
    "reject_repaired_prompt_policy",
]

MIN_EVIDENCE_BY_QUERY_TYPE: dict[QueryType, int] = {
    "place_fact": 1,
    "place_story": 2,
    "relationship": 2,
    "overview": 2,
    "route_context": 1,
    "voice_followup": 2,
    "no_answer": 0,
}
FALLBACK_ALLOWED_QUERY_TYPES: frozenset[QueryType] = frozenset(
    {
        "place_story",
        "relationship",
        "voice_followup",
    },
)
DEFAULT_QUERY_TYPES: tuple[QueryType, ...] = (
    "place_fact",
    "place_story",
    "relationship",
    "overview",
    "route_context",
    "voice_followup",
    "no_answer",
)


class SolarGenerationV2PromptPolicyValidatorModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PromptPolicyValidationInput(SolarGenerationV2PromptPolicyValidatorModel):
    item: RetrievalEvalItem
    evidence_pack: EvidencePack
    prompt_policy_id: PromptPolicyId
    draft: CitationRagDraftV2 | None = None
    fake_provider_config_id: str = Field(
        default="fake-solar-generation-v2-repair-validator",
        min_length=1,
    )


class PromptPolicyValidationRow(SolarGenerationV2PromptPolicyValidatorModel):
    query_id: str = Field(min_length=1)
    query_type: QueryType
    prompt_policy_id: PromptPolicyId
    validation_status: ValidationStatus
    selected_evidence_count: int = Field(ge=0)
    min_required_evidence_count: int = Field(ge=0)
    available_evidence_count: int = Field(ge=0)
    invalid_rank_count: int = Field(ge=0)
    evidence_floor_violation: bool
    coverage_intent_violation: bool
    unsupported_risk_violation: bool
    v1_fallback_allowed: bool
    solar_call_count: int = Field(default=0, ge=0)
    validation_tags: tuple[str, ...]
    next_action: str = Field(min_length=1)


class PromptPolicyValidationSummary(SolarGenerationV2PromptPolicyValidatorModel):
    row_count: int = Field(ge=0)
    query_type_policy_count: int = Field(ge=0)
    prompt_policy_count: int = Field(ge=0)
    pass_count: int = Field(ge=0)
    fallback_required_count: int = Field(ge=0)
    fail_count: int = Field(ge=0)
    invalid_rank_count: int = Field(ge=0)
    evidence_floor_violation_count: int = Field(ge=0)
    coverage_intent_violation_count: int = Field(ge=0)
    unsupported_risk_violation_count: int = Field(ge=0)
    no_answer_abstain_pass_count: int = Field(ge=0)
    live_solar_call_count: int = Field(ge=0)
    readiness_decision: ReadinessDecision


class PromptPolicyValidationQueryTypeSummary(SolarGenerationV2PromptPolicyValidatorModel):
    query_type: QueryType
    row_count: int = Field(ge=0)
    pass_count: int = Field(ge=0)
    fallback_required_count: int = Field(ge=0)
    fail_count: int = Field(ge=0)
    min_required_evidence_count: int = Field(ge=0)


class PromptPolicyValidationReport(SolarGenerationV2PromptPolicyValidatorModel):
    report_version: str = SOLAR_GENERATION_V2_PROMPT_POLICY_VALIDATOR_REPORT_VERSION
    validation_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    source_plan_alias: str = "docs/SOLAR_GENERATION_V2_PROMPT_REPAIR_PLAN.md"
    validator_stage: str = "fake_provider_validator"
    summary: PromptPolicyValidationSummary
    query_type_breakdown: tuple[PromptPolicyValidationQueryTypeSummary, ...]
    validation_rows: tuple[PromptPolicyValidationRow, ...]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def run_solar_generation_v2_prompt_policy_validator(
    *,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
) -> PromptPolicyValidationReport:
    _validate_result_rows_path(result_rows_path)
    inputs = build_fake_prompt_policy_validation_inputs()
    provisional_report = build_prompt_policy_validation_report(inputs=inputs)
    provisional_markdown = build_prompt_policy_validation_markdown(provisional_report)
    report = build_prompt_policy_validation_report(
        inputs=inputs,
        report_text=provisional_markdown,
    )
    failures = collect_prompt_policy_validation_failures(report)
    if failures:
        raise ValueError(f"solar generation v2 prompt policy validator gate failed: {failures}")

    rows = build_public_prompt_policy_validation_rows(report)
    write_jsonl_rows(path=result_rows_path, rows=rows)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        build_prompt_policy_validation_markdown(report),
        encoding="utf-8",
    )
    return report


def build_prompt_policy_validation_report(
    *,
    inputs: list[PromptPolicyValidationInput],
    report_text: str = "",
) -> PromptPolicyValidationReport:
    rows = tuple(validate_prompt_policy_input(item) for item in inputs)
    public_rows = build_public_prompt_policy_validation_rows_from_rows(rows)
    validation_id = build_prompt_policy_validation_id(rows)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=SOLAR_GENERATION_V2_PROMPT_POLICY_VALIDATOR_REPORT_VERSION,
        run_id=validation_id,
        result_rows=public_rows,
        report_text=report_text,
    )
    report = PromptPolicyValidationReport(
        validation_id=validation_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        summary=build_prompt_policy_validation_summary(rows),
        query_type_breakdown=tuple(build_query_type_breakdown(rows)),
        validation_rows=rows,
        output_quality=output_quality,
        qualitative_assessment={},
    )
    return report.model_copy(
        update={
            "qualitative_assessment": build_prompt_policy_validation_qualitative_assessment(
                report,
            ),
        },
    )


def validate_prompt_policy_input(
    item: PromptPolicyValidationInput,
) -> PromptPolicyValidationRow:
    _validate_input_shape(item)
    query_type = item.item.query.query_type
    min_required = MIN_EVIDENCE_BY_QUERY_TYPE[query_type]
    available_ranks = {evidence.pack_rank for evidence in item.evidence_pack.evidence}
    fallback_allowed = query_type in FALLBACK_ALLOWED_QUERY_TYPES

    if item.item.query.expected_behavior == "abstain":
        return _validate_abstain_input(
            item=item,
            min_required=min_required,
            available_ranks=available_ranks,
        )

    if item.draft is None:
        return _row(
            item=item,
            status="fail",
            selected_count=0,
            min_required=min_required,
            available_count=len(available_ranks),
            invalid_rank_count=0,
            evidence_floor_violation=True,
            coverage_intent_violation=False,
            unsupported_risk_violation=True,
            fallback_allowed=fallback_allowed,
            tags=("missing_draft", "evidence_floor_violation"),
            next_action="v2 draft를 생성하지 못했으므로 repaired prompt 후보를 실행하지 않는다.",
        )

    selected_ranks = tuple(item.draft.used_evidence_pack_ranks)
    invalid_rank_count = sum(1 for rank in selected_ranks if rank not in available_ranks)
    selected_count = len(selected_ranks)
    evidence_floor_violation = selected_count < min_required
    coverage_intent_violation = min_required >= 2 and item.draft.coverage_intent != "multi_evidence"
    unsupported_risk_violation = (
        evidence_floor_violation or coverage_intent_violation
    ) and item.draft.unsupported_claim_risk == "low"
    tags = _validation_tags(
        item=item,
        invalid_rank_count=invalid_rank_count,
        evidence_floor_violation=evidence_floor_violation,
        coverage_intent_violation=coverage_intent_violation,
        unsupported_risk_violation=unsupported_risk_violation,
    )
    status = _validation_status(
        item=item,
        invalid_rank_count=invalid_rank_count,
        evidence_floor_violation=evidence_floor_violation,
        coverage_intent_violation=coverage_intent_violation,
        fallback_allowed=fallback_allowed,
    )
    return _row(
        item=item,
        status=status,
        selected_count=selected_count,
        min_required=min_required,
        available_count=len(available_ranks),
        invalid_rank_count=invalid_rank_count,
        evidence_floor_violation=evidence_floor_violation,
        coverage_intent_violation=coverage_intent_violation,
        unsupported_risk_violation=unsupported_risk_violation,
        fallback_allowed=fallback_allowed,
        tags=tuple(tags),
        next_action=_next_action(status=status, query_type=query_type),
    )


def build_fake_prompt_policy_validation_inputs() -> list[PromptPolicyValidationInput]:
    inputs: list[PromptPolicyValidationInput] = []
    for query_type in DEFAULT_QUERY_TYPES:
        item = _fake_eval_item(query_type=query_type)
        evidence_pack = _fake_evidence_pack(item)
        prompt_policy_id = _prompt_policy_for_query_type(query_type)
        draft = (
            None
            if item.query.expected_behavior == "abstain"
            else _fake_repaired_v2_draft(query_type)
        )
        inputs.append(
            PromptPolicyValidationInput(
                item=item,
                evidence_pack=evidence_pack,
                prompt_policy_id=prompt_policy_id,
                draft=draft,
            ),
        )
    return inputs


def build_prompt_policy_validation_summary(
    rows: tuple[PromptPolicyValidationRow, ...],
) -> PromptPolicyValidationSummary:
    fail_count = sum(1 for row in rows if row.validation_status == "fail")
    live_solar_call_count = sum(row.solar_call_count for row in rows)
    return PromptPolicyValidationSummary(
        row_count=len(rows),
        query_type_policy_count=len({row.query_type for row in rows}),
        prompt_policy_count=len({row.prompt_policy_id for row in rows}),
        pass_count=sum(1 for row in rows if row.validation_status == "pass"),
        fallback_required_count=sum(
            1 for row in rows if row.validation_status == "fallback_required"
        ),
        fail_count=fail_count,
        invalid_rank_count=sum(row.invalid_rank_count for row in rows),
        evidence_floor_violation_count=sum(1 for row in rows if row.evidence_floor_violation),
        coverage_intent_violation_count=sum(1 for row in rows if row.coverage_intent_violation),
        unsupported_risk_violation_count=sum(1 for row in rows if row.unsupported_risk_violation),
        no_answer_abstain_pass_count=sum(
            1 for row in rows if row.query_type == "no_answer" and row.validation_status == "pass"
        ),
        live_solar_call_count=live_solar_call_count,
        readiness_decision=(
            "ready_for_repaired_prompt_dry_run"
            if fail_count == 0 and live_solar_call_count == 0
            else "reject_repaired_prompt_policy"
        ),
    )


def build_query_type_breakdown(
    rows: tuple[PromptPolicyValidationRow, ...],
) -> list[PromptPolicyValidationQueryTypeSummary]:
    breakdown: list[PromptPolicyValidationQueryTypeSummary] = []
    for query_type in sorted({row.query_type for row in rows}):
        query_rows = [row for row in rows if row.query_type == query_type]
        breakdown.append(
            PromptPolicyValidationQueryTypeSummary(
                query_type=query_type,
                row_count=len(query_rows),
                pass_count=sum(1 for row in query_rows if row.validation_status == "pass"),
                fallback_required_count=sum(
                    1 for row in query_rows if row.validation_status == "fallback_required"
                ),
                fail_count=sum(1 for row in query_rows if row.validation_status == "fail"),
                min_required_evidence_count=MIN_EVIDENCE_BY_QUERY_TYPE[query_type],
            ),
        )
    return breakdown


def build_public_prompt_policy_validation_rows(
    report: PromptPolicyValidationReport,
) -> list[dict[str, Any]]:
    return build_public_prompt_policy_validation_rows_from_rows(report.validation_rows)


def build_public_prompt_policy_validation_rows_from_rows(
    rows: tuple[PromptPolicyValidationRow, ...],
) -> list[dict[str, Any]]:
    return [
        {
            "query_id": row.query_id,
            "query_type": row.query_type,
            "prompt_policy_id": row.prompt_policy_id,
            "validation_status": row.validation_status,
            "selected_evidence_count": row.selected_evidence_count,
            "min_required_evidence_count": row.min_required_evidence_count,
            "available_evidence_count": row.available_evidence_count,
            "invalid_rank_count": row.invalid_rank_count,
            "evidence_floor_violation": row.evidence_floor_violation,
            "coverage_intent_violation": row.coverage_intent_violation,
            "unsupported_risk_violation": row.unsupported_risk_violation,
            "v1_fallback_allowed": row.v1_fallback_allowed,
            "solar_call_count": row.solar_call_count,
            "validation_tags": list(row.validation_tags),
        }
        for row in rows
    ]


def collect_prompt_policy_validation_failures(
    report: PromptPolicyValidationReport,
) -> list[str]:
    failures: list[str] = []
    if report.summary.row_count == 0:
        failures.append("empty_prompt_policy_validation")
    if report.summary.query_type_policy_count < len(DEFAULT_QUERY_TYPES):
        failures.append("missing_query_type_policy")
    if report.summary.fail_count:
        failures.append("prompt_policy_validation_failed")
    if report.summary.live_solar_call_count:
        failures.append("validator_must_not_call_solar")
    if report.output_quality.public_raw_text_leakage_count:
        failures.append("public_raw_text_leakage")
    if report.output_quality.private_path_leakage_count:
        failures.append("private_path_leakage")
    if report.output_quality.secret_like_leakage_count:
        failures.append("secret_like_leakage")
    if report.output_quality.forbidden_result_field_count:
        failures.append("forbidden_public_result_fields")
    return failures


def build_prompt_policy_validation_markdown(report: PromptPolicyValidationReport) -> str:
    summary = report.summary
    quality = report.output_quality
    prompt_policy_distribution = Counter(row.prompt_policy_id for row in report.validation_rows)
    prompt_policy_rows = "\n".join(
        f"| {policy_id} | {count} |"
        for policy_id, count in sorted(prompt_policy_distribution.items())
    )
    query_type_rows = "\n".join(_format_query_type_row(row) for row in report.query_type_breakdown)
    validation_rows = "\n".join(_format_validation_row(row) for row in report.validation_rows)
    qualitative_rows = "\n".join(
        f"- `{key}`: {value}" for key, value in report.qualitative_assessment.items()
    )
    return f"""# Solar Pro 3 Generation v2 Prompt Policy Validator Report

## 목적

HD-SOLAR-025에서 repaired v2 prompt policy가 Solar Pro 3 live 호출 전에 selected evidence floor, risk aware selection, query type fallback 규칙을 만족하는지 검증한다.

이 리포트는 fake provider/validator 결과다. Solar Pro 3 호출, live generation 재평가, 청킹 비교 테스트는 수행하지 않았다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| validation_id | `{report.validation_id}` |
| generated_at_utc | `{report.generated_at_utc}` |
| source_plan | `{report.source_plan_alias}` |
| validator_stage | `{report.validator_stage}` |

## 정량 리포트

| metric | value |
| --- | ---: |
| row_count | {summary.row_count} |
| query_type_policy_count | {summary.query_type_policy_count} |
| prompt_policy_count | {summary.prompt_policy_count} |
| pass_count | {summary.pass_count} |
| fallback_required_count | {summary.fallback_required_count} |
| fail_count | {summary.fail_count} |
| invalid_rank_count | {summary.invalid_rank_count} |
| evidence_floor_violation_count | {summary.evidence_floor_violation_count} |
| coverage_intent_violation_count | {summary.coverage_intent_violation_count} |
| unsupported_risk_violation_count | {summary.unsupported_risk_violation_count} |
| no_answer_abstain_pass_count | {summary.no_answer_abstain_pass_count} |
| live_solar_call_count | {summary.live_solar_call_count} |
| readiness_decision | `{summary.readiness_decision}` |

## Prompt Policy Distribution

| prompt_policy_id | count |
| --- | ---: |
{prompt_policy_rows}

## Query Type Breakdown

| query_type | rows | pass | fallback_required | fail | min_required_evidence |
| --- | ---: | ---: | ---: | ---: | ---: |
{query_type_rows}

## Validation Rows

| query_id | query_type | prompt_policy_id | status | selected | min_required | available | invalid_rank | tags |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- |
{validation_rows}

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

청킹 비교 테스트는 계속 보류한다.

repaired v2 prompt policy는 fake provider/validator 단계에서 fail 없이 통과했으며, `place_story`는 v1 fallback이 필요한 monitor case로 분리됐다. 다음 단계는 Solar Pro 3 live 호출 없이 repaired v2 dry-run/readiness runner를 구현하는 것이다.
"""


def build_prompt_policy_validation_qualitative_assessment(
    report: PromptPolicyValidationReport,
) -> dict[str, str]:
    failures = collect_prompt_policy_validation_failures(report)
    return {
        "validator_scope": (
            "selected evidence rank, query type별 evidence floor, fallback rule만 검증했다."
        ),
        "provider_boundary": (
            "fake provider draft만 사용했고 Solar Pro 3 live API는 호출하지 않았다."
        ),
        "chunking_boundary": (
            "target resolvability와 citation recoverability가 정상이라 청킹 비교를 재개하지 않는다."
        ),
        "data_grain": (
            "fact grain은 repair_id-query_type-prompt_policy_id-eval_stage-metric_family다."
        ),
        "security_boundary": (
            "public report에는 raw prompt, raw answer, raw evidence, query text, private path, secret을 저장하지 않는다."
        ),
        "next_action": (
            "HD-SOLAR-026 repaired v2 dry-run/readiness runner를 구현한다."
            if not failures
            else "validator failure를 먼저 수정한다."
        ),
        "gate_status": "PASS" if not failures else f"FAIL: {', '.join(failures)}",
    }


def build_prompt_policy_validation_id(
    rows: tuple[PromptPolicyValidationRow, ...],
) -> str:
    payload = [
        {
            "query_id": row.query_id,
            "query_type": row.query_type,
            "prompt_policy_id": row.prompt_policy_id,
            "validation_status": row.validation_status,
            "tags": row.validation_tags,
        }
        for row in sorted(rows, key=lambda item: item.query_id)
    ]
    digest = _stable_digest(payload)[:8]
    return f"solar-generation-v2-prompt-policy-validator-q{len(rows)}-{digest}"


def _validate_abstain_input(
    *,
    item: PromptPolicyValidationInput,
    min_required: int,
    available_ranks: set[int],
) -> PromptPolicyValidationRow:
    failures: list[str] = []
    if item.draft is not None:
        failures.append("unexpected_draft_for_abstain")
    if available_ranks:
        failures.append("abstain_with_evidence")
    status: ValidationStatus = "fail" if failures else "pass"
    tags = tuple(failures or ["no_answer_abstain_path"])
    return _row(
        item=item,
        status=status,
        selected_count=0,
        min_required=min_required,
        available_count=len(available_ranks),
        invalid_rank_count=0,
        evidence_floor_violation=bool(failures),
        coverage_intent_violation=False,
        unsupported_risk_violation=False,
        fallback_allowed=False,
        tags=tags,
        next_action=(
            "abstain path를 유지하고 Solar Pro 3를 호출하지 않는다."
            if status == "pass"
            else "no-answer 입력은 draft와 evidence 없이 abstain해야 한다."
        ),
    )


def _validation_tags(
    *,
    item: PromptPolicyValidationInput,
    invalid_rank_count: int,
    evidence_floor_violation: bool,
    coverage_intent_violation: bool,
    unsupported_risk_violation: bool,
) -> list[str]:
    tags: list[str] = []
    query_type = item.item.query.query_type
    if invalid_rank_count:
        tags.append("invalid_evidence_rank")
    if evidence_floor_violation:
        tags.append("evidence_floor_violation")
    if coverage_intent_violation:
        tags.append("coverage_intent_violation")
    if unsupported_risk_violation:
        tags.append("unsupported_risk_too_low")
    if item.prompt_policy_id == "v2_repair_query_type_router" and query_type == "place_story":
        tags.append("v1_fallback_required")
        tags.append("monitor_only_query_type")
    if not tags:
        tags.append("policy_pass")
    return tags


def _validation_status(
    *,
    item: PromptPolicyValidationInput,
    invalid_rank_count: int,
    evidence_floor_violation: bool,
    coverage_intent_violation: bool,
    fallback_allowed: bool,
) -> ValidationStatus:
    query_type = item.item.query.query_type
    if invalid_rank_count:
        return "fail"
    if item.prompt_policy_id == "v2_repair_query_type_router" and query_type == "place_story":
        return "fallback_required"
    if evidence_floor_violation or coverage_intent_violation:
        return "fallback_required" if fallback_allowed else "fail"
    return "pass"


def _row(
    *,
    item: PromptPolicyValidationInput,
    status: ValidationStatus,
    selected_count: int,
    min_required: int,
    available_count: int,
    invalid_rank_count: int,
    evidence_floor_violation: bool,
    coverage_intent_violation: bool,
    unsupported_risk_violation: bool,
    fallback_allowed: bool,
    tags: tuple[str, ...],
    next_action: str,
) -> PromptPolicyValidationRow:
    return PromptPolicyValidationRow(
        query_id=item.item.query.query_id,
        query_type=item.item.query.query_type,
        prompt_policy_id=item.prompt_policy_id,
        validation_status=status,
        selected_evidence_count=selected_count,
        min_required_evidence_count=min_required,
        available_evidence_count=available_count,
        invalid_rank_count=invalid_rank_count,
        evidence_floor_violation=evidence_floor_violation,
        coverage_intent_violation=coverage_intent_violation,
        unsupported_risk_violation=unsupported_risk_violation,
        v1_fallback_allowed=fallback_allowed,
        solar_call_count=0,
        validation_tags=tags,
        next_action=next_action,
    )


def _next_action(*, status: ValidationStatus, query_type: QueryType) -> str:
    if status == "pass":
        return "repaired v2 dry-run 후보로 유지한다."
    if status == "fallback_required":
        if query_type == "place_story":
            return "place_story는 v1 fallback monitor case로 분리한다."
        return "v1 fallback 또는 evidence floor 보정 후 dry-run에 넣는다."
    return "validator failure를 수정하기 전까지 live 비교를 금지한다."


def _validate_input_shape(item: PromptPolicyValidationInput) -> None:
    if item.evidence_pack.query_id != item.item.query.query_id:
        raise ValueError("evidence_pack query_id must match eval item query_id")
    if item.evidence_pack.query_type != item.item.query.query_type:
        raise ValueError("evidence_pack query_type must match eval item query_type")


def _prompt_policy_for_query_type(query_type: QueryType) -> PromptPolicyId:
    if query_type == "place_story":
        return "v2_repair_query_type_router"
    if query_type in {"relationship", "voice_followup", "overview"}:
        return "v2_repair_coverage_floor"
    return "v2_repair_risk_aware_selection"


def _fake_repaired_v2_draft(query_type: QueryType) -> CitationRagDraftV2:
    ranks = (1, 2) if MIN_EVIDENCE_BY_QUERY_TYPE[query_type] >= 2 else (1,)
    return CitationRagDraftV2(
        answer=f"{query_type} fixture answer for repaired v2 validator.",
        spoken_answer=f"{query_type} fixture spoken answer.",
        used_evidence_pack_ranks=ranks,
        coverage_intent="multi_evidence" if len(ranks) >= 2 else "focused",
        unsupported_claim_risk="low",
    )


def _fake_eval_item(*, query_type: QueryType) -> RetrievalEvalItem:
    expected_behavior = "abstain" if query_type == "no_answer" else "retrieve"
    query_id = f"q-validator-{query_type}-001"
    judgments = []
    if expected_behavior == "retrieve":
        judgments.append(
            {
                "query_id": query_id,
                "relevant_child_ids": [f"child-{query_type}-target"],
                "relevant_parent_ids": [f"parent-{query_type}-target"],
                "relevant_doc_ids": [f"doc-{query_type}-target"],
                "relevance_grade": 3,
                "rationale_summary": "public-safe fixture target id",
                "public_allowed": True,
            },
        )
    return RetrievalEvalItem.model_validate(
        {
            "dataset_version": "retrieval-eval-dataset/v2",
            "query": {
                "query_id": query_id,
                "query_type": query_type,
                "query_text": f"{query_type} validator fixture query",
                "language": "ko",
                "expected_behavior": expected_behavior,
                "public_allowed": True,
            },
            "judgments": judgments,
            "metadata": {
                "split": "dev",
                "difficulty": "medium",
                "place_ids": ["gyeongbokgung"] if expected_behavior == "retrieve" else [],
                "requires_context": query_type == "voice_followup",
                "answerability": "answerable"
                if expected_behavior == "retrieve"
                else "unanswerable",
                "review_status": "reviewed",
            },
        },
    )


def _fake_evidence_pack(item: RetrievalEvalItem) -> EvidencePack:
    if item.query.expected_behavior == "abstain":
        return EvidencePack(
            query_id=item.query.query_id,
            query_type=item.query.query_type,
            policy_id="P0_rank_order",
            context_budget_chars=4200,
            total_estimated_chars=0,
            evidence=(),
            target_child_covered=False,
            target_parent_covered=False,
            target_doc_covered=False,
            evidence_order_relevance_proxy=1.0,
        )
    evidence = tuple(
        _packed_evidence(
            pack_rank=rank,
            query_type=item.query.query_type,
            suffix="target" if rank == 1 else f"support-{rank}",
        )
        for rank in range(1, 4)
    )
    return EvidencePack(
        query_id=item.query.query_id,
        query_type=item.query.query_type,
        policy_id="P0_rank_order",
        context_budget_chars=4200,
        total_estimated_chars=sum(row.estimated_chars for row in evidence),
        evidence=evidence,
        target_child_covered=True,
        target_parent_covered=True,
        target_doc_covered=True,
        evidence_order_relevance_proxy=1.0,
    )


def _packed_evidence(*, pack_rank: int, query_type: QueryType, suffix: str) -> PackedEvidence:
    return PackedEvidence(
        pack_rank=pack_rank,
        source_rank=pack_rank,
        retrieval_doc_id=f"child-{query_type}-{suffix}",
        child_id=f"child-{query_type}-{suffix}",
        parent_id=f"parent-{query_type}-{suffix}",
        doc_id=f"doc-{query_type}-{suffix}",
        score=1.0 - (pack_rank * 0.01),
        estimated_chars=320,
        source_block_ids=(f"block-{query_type}-{suffix}",),
        citation_block_ids=(f"block-{query_type}-{suffix}",),
        citation_recoverable=True,
        packing_reason="retrieval_rank_order",
    )


def _format_query_type_row(row: PromptPolicyValidationQueryTypeSummary) -> str:
    return (
        f"| {row.query_type} | {row.row_count} | {row.pass_count} | "
        f"{row.fallback_required_count} | {row.fail_count} | "
        f"{row.min_required_evidence_count} |"
    )


def _format_validation_row(row: PromptPolicyValidationRow) -> str:
    tags = ", ".join(row.validation_tags)
    return (
        f"| {row.query_id} | {row.query_type} | {row.prompt_policy_id} | "
        f"{row.validation_status} | {row.selected_evidence_count} | "
        f"{row.min_required_evidence_count} | {row.available_evidence_count} | "
        f"{row.invalid_rank_count} | {tags} |"
    )


def _validate_result_rows_path(path: Path) -> None:
    if has_private_data_segment(path) and not is_repository_private_artifact_path(path):
        raise ValueError("private_data result rows must stay under repository private_data")
    if has_private_data_segment(path) and not is_repository_private_write_path(path):
        raise ValueError("private validator rows must be written under private_data")


def _stable_digest(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"),
    ).hexdigest()[:16]


def main() -> int:
    args = _parse_args()
    report = run_solar_generation_v2_prompt_policy_validator(
        report_path=args.report,
        result_rows_path=args.result_rows,
    )
    failures = collect_prompt_policy_validation_failures(report)
    print(
        "solar_generation_v2_prompt_policy_validator "
        f"status={'PASS' if not failures else 'FAIL'} "
        f"row_count={report.summary.row_count} "
        f"fallback_required_count={report.summary.fallback_required_count} "
        f"fail_count={report.summary.fail_count} "
        f"solar_call_count={report.summary.live_solar_call_count} "
        f"readiness_decision={report.summary.readiness_decision}",
    )
    return 0 if not failures else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate repaired Solar Pro 3 v2 prompt policy without live calls.",
    )
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--result-rows", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
