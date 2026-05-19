from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.project_paths import project_path
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    collect_public_retrieval_artifact_failures,
    measure_public_retrieval_artifact_quality,
    public_path_alias,
    write_public_retrieval_result_rows,
)
from pipelines.voice_stt_tts_azure_credential_preflight import (
    AZURE_CREDENTIAL_ENV_NAMES,
    AZURE_SOURCE_CHECKS,
    DEFAULT_ENV_PATH,
    PROVIDER_CANDIDATE_ID,
    build_credential_checks,
)
from pipelines.voice_stt_tts_azure_smoke_execution import (
    AzureSmokeMetricPlanRow,
    build_metric_plan_rows,
)
from pipelines.voice_stt_tts_managed_provider_smoke import (
    CLIENT_SECRET_EXPOSURE_COUNT,
    DEFAULT_SCRIPT_LIMIT,
    MAX_STT_CALLS_PER_PROVIDER,
    MAX_TTS_CALLS_PER_PROVIDER,
    RAW_AUDIO_PUBLIC_ARTIFACT_COUNT,
    RAW_PAYLOAD_PUBLIC_ARTIFACT_COUNT,
    RAW_TRANSCRIPT_PUBLIC_ARTIFACT_COUNT,
)
from pipelines.voice_stt_tts_provider_bench_readiness import DEFAULT_SCRIPTS_PATH


REPORT_VERSION = "voice-stt-tts-azure-credential-ready-smoke-approval-report/v1"
WORK_ID = "HD-VOICE-STT-TTS-AZURE-CREDENTIAL-READY-AND-SMOKE-APPROVAL-001"
DEPENDS_ON = "HD-VOICE-STT-TTS-AZURE-SMOKE-EXECUTION-001"
NEXT_WORK_ID = "HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-001"
DEFAULT_DOC_PATH = (
    Path("docs") / "VOICE_STT_TTS_AZURE_CREDENTIAL_READY_AND_SMOKE_APPROVAL.md"
)
DEFAULT_REPORT_PATH = (
    Path("evals")
    / "reports"
    / "voice_stt_tts_azure_credential_ready_and_smoke_approval_report.md"
)
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "voice_stt_tts_azure_credential_ready_and_smoke_approval_rows.jsonl"
)

ApprovalDecision = Literal[
    "blocked_missing_azure_credentials",
    "blocked_source_recheck_incomplete",
    "blocked_missing_user_external_call_approval",
    "blocked_by_public_safety_gate",
    "ready_for_actual_azure_smoke_execution",
]


class AzureCredentialReadyApprovalModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AzureCredentialReadySourceRow(AzureCredentialReadyApprovalModel):
    source_check_type: str = Field(min_length=1)
    recheck_required_before_execution: bool
    recheck_completed_for_execution: bool


class AzureCredentialReadyApprovalSummary(AzureCredentialReadyApprovalModel):
    provider_candidate_count: int = Field(ge=0)
    first_provider_candidate_is_azure: bool
    credential_env_var_name_count: int = Field(ge=0)
    credential_present_count: int = Field(ge=0)
    credential_missing_count: int = Field(ge=0)
    azure_credential_ready: bool
    credential_value_public_exposure_count: int = Field(ge=0)
    planned_script_count: int = Field(ge=0)
    planned_stt_call_count: int = Field(ge=0)
    planned_tts_call_count: int = Field(ge=0)
    call_cap_enforced: bool
    source_recheck_required_before_execution_count: int = Field(ge=0)
    source_recheck_completed_for_execution_count: int = Field(ge=0)
    region_confirmation_completed: bool
    retention_confirmation_completed: bool
    cost_confirmation_completed: bool
    user_external_call_approval_recorded: bool
    azure_smoke_execution_ready: bool
    azure_smoke_execution_approved: bool
    managed_provider_api_call_count: int = Field(ge=0)
    external_audio_transmission_count: int = Field(ge=0)
    live_stt_call_count: int = Field(ge=0)
    live_tts_call_count: int = Field(ge=0)
    live_solar_call_count: int = Field(ge=0)
    raw_audio_public_artifact_count: int = Field(ge=0)
    raw_transcript_public_artifact_count: int = Field(ge=0)
    raw_payload_public_artifact_count: int = Field(ge=0)
    client_secret_exposure_count: int = Field(ge=0)
    public_private_path_leakage_count: int = Field(ge=0)
    public_secret_like_leakage_count: int = Field(ge=0)
    public_raw_payload_leakage_count: int = Field(ge=0)
    approval_decision: ApprovalDecision


class AzureCredentialReadyApprovalReport(AzureCredentialReadyApprovalModel):
    report_version: str = REPORT_VERSION
    approval_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    work_id: str = WORK_ID
    depends_on: str = DEPENDS_ON
    next_work_id: str = NEXT_WORK_ID
    provider_candidate_id: str = PROVIDER_CANDIDATE_ID
    env_path_status: Literal["present", "missing"]
    scripts_path: str = Field(min_length=1)
    result_path: str = Field(min_length=1)
    source_fingerprint: str = Field(min_length=8)
    source_rechecks: tuple[AzureCredentialReadySourceRow, ...]
    metric_plan_rows: tuple[AzureSmokeMetricPlanRow, ...]
    summary: AzureCredentialReadyApprovalSummary
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def run_voice_stt_tts_azure_credential_ready_and_smoke_approval(
    *,
    env_path: Path = DEFAULT_ENV_PATH,
    scripts_path: Path = DEFAULT_SCRIPTS_PATH,
    doc_path: Path = DEFAULT_DOC_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
    source_recheck_completed: bool = False,
    region_confirmation_completed: bool = False,
    retention_confirmation_completed: bool = False,
    cost_confirmation_completed: bool = False,
    user_external_call_approval_recorded: bool = False,
) -> AzureCredentialReadyApprovalReport:
    credential_checks = build_credential_checks(env_path=env_path)
    source_rechecks = build_source_rechecks(completed=source_recheck_completed)
    metric_rows = build_metric_plan_rows()
    summary = build_summary(
        credential_checks=credential_checks,
        source_rechecks=source_rechecks,
        region_confirmation_completed=region_confirmation_completed,
        retention_confirmation_completed=retention_confirmation_completed,
        cost_confirmation_completed=cost_confirmation_completed,
        user_external_call_approval_recorded=user_external_call_approval_recorded,
    )
    approval_id = build_approval_id(
        source_rechecks=source_rechecks,
        metric_rows=metric_rows,
        summary=summary,
    )
    public_rows = build_public_rows(
        approval_id=approval_id,
        source_rechecks=source_rechecks,
        metric_rows=metric_rows,
        summary=summary,
    )
    provisional_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=approval_id,
        result_rows=public_rows,
        report_text="",
    )
    provisional = build_report(
        approval_id=approval_id,
        env_path=env_path,
        scripts_path=scripts_path,
        result_rows_path=result_rows_path,
        source_rechecks=source_rechecks,
        metric_rows=metric_rows,
        summary=summary,
        output_quality=provisional_quality,
    )
    doc_text = build_doc_markdown(provisional)
    report_text = build_report_markdown(provisional)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=approval_id,
        result_rows=public_rows,
        report_text=report_text,
        extra_public_texts={
            f"doc:{line_number}": line
            for line_number, line in enumerate(doc_text.splitlines(), start=1)
        },
    )
    summary = summary.model_copy(
        update={
            "public_private_path_leakage_count": output_quality.private_path_leakage_count,
            "public_secret_like_leakage_count": output_quality.secret_like_leakage_count,
            "public_raw_payload_leakage_count": output_quality.public_raw_text_leakage_count,
            "approval_decision": build_approval_decision(
                summary=summary,
                output_quality=output_quality,
            ),
        },
    )
    report = build_report(
        approval_id=approval_id,
        env_path=env_path,
        scripts_path=scripts_path,
        result_rows_path=result_rows_path,
        source_rechecks=source_rechecks,
        metric_rows=metric_rows,
        summary=summary,
        output_quality=output_quality,
    )
    failures = collect_azure_credential_ready_and_smoke_approval_failures(report)
    if failures:
        raise ValueError(f"Azure credential ready smoke approval gate failed: {failures}")

    write_public_retrieval_result_rows(
        path=project_path(result_rows_path),
        rows=build_public_rows(
            approval_id=approval_id,
            source_rechecks=source_rechecks,
            metric_rows=metric_rows,
            summary=summary,
        ),
    )
    resolved_doc_path = project_path(doc_path)
    resolved_report_path = project_path(report_path)
    resolved_doc_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_report_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_doc_path.write_text(build_doc_markdown(report), encoding="utf-8")
    resolved_report_path.write_text(build_report_markdown(report), encoding="utf-8")
    print(
        "voice_stt_tts_azure_credential_ready_and_smoke_approval "
        "status=PASS "
        f"decision={report.summary.approval_decision} "
        f"azure_credential_ready={str(report.summary.azure_credential_ready).lower()} "
        f"azure_smoke_execution_approved="
        f"{str(report.summary.azure_smoke_execution_approved).lower()} "
        f"managed_provider_api_calls={report.summary.managed_provider_api_call_count} "
        f"external_audio_transmissions={report.summary.external_audio_transmission_count}",
    )
    return report


def build_source_rechecks(
    *,
    completed: bool,
) -> tuple[AzureCredentialReadySourceRow, ...]:
    return tuple(
        AzureCredentialReadySourceRow(
            source_check_type=source_check_type,
            recheck_required_before_execution=True,
            recheck_completed_for_execution=completed,
        )
        for source_check_type, _url in AZURE_SOURCE_CHECKS
    )


def build_summary(
    *,
    credential_checks: tuple[Any, ...],
    source_rechecks: tuple[AzureCredentialReadySourceRow, ...],
    region_confirmation_completed: bool,
    retention_confirmation_completed: bool,
    cost_confirmation_completed: bool,
    user_external_call_approval_recorded: bool,
) -> AzureCredentialReadyApprovalSummary:
    credential_present_count = sum(
        1 for row in credential_checks if row.credential_status == "present"
    )
    credential_missing_count = len(credential_checks) - credential_present_count
    azure_credential_ready = credential_missing_count == 0
    source_recheck_completed_count = sum(
        1 for row in source_rechecks if row.recheck_completed_for_execution
    )
    call_cap_enforced = (
        DEFAULT_SCRIPT_LIMIT <= MAX_STT_CALLS_PER_PROVIDER
        and DEFAULT_SCRIPT_LIMIT <= MAX_TTS_CALLS_PER_PROVIDER
    )
    azure_smoke_execution_ready = (
        azure_credential_ready
        and source_recheck_completed_count == len(source_rechecks)
        and region_confirmation_completed
        and retention_confirmation_completed
        and cost_confirmation_completed
        and user_external_call_approval_recorded
        and call_cap_enforced
    )
    summary = AzureCredentialReadyApprovalSummary(
        provider_candidate_count=1,
        first_provider_candidate_is_azure=True,
        credential_env_var_name_count=len(AZURE_CREDENTIAL_ENV_NAMES),
        credential_present_count=credential_present_count,
        credential_missing_count=credential_missing_count,
        azure_credential_ready=azure_credential_ready,
        credential_value_public_exposure_count=0,
        planned_script_count=DEFAULT_SCRIPT_LIMIT,
        planned_stt_call_count=DEFAULT_SCRIPT_LIMIT,
        planned_tts_call_count=DEFAULT_SCRIPT_LIMIT,
        call_cap_enforced=call_cap_enforced,
        source_recheck_required_before_execution_count=sum(
            1 for row in source_rechecks if row.recheck_required_before_execution
        ),
        source_recheck_completed_for_execution_count=source_recheck_completed_count,
        region_confirmation_completed=region_confirmation_completed,
        retention_confirmation_completed=retention_confirmation_completed,
        cost_confirmation_completed=cost_confirmation_completed,
        user_external_call_approval_recorded=user_external_call_approval_recorded,
        azure_smoke_execution_ready=azure_smoke_execution_ready,
        azure_smoke_execution_approved=azure_smoke_execution_ready,
        managed_provider_api_call_count=0,
        external_audio_transmission_count=0,
        live_stt_call_count=0,
        live_tts_call_count=0,
        live_solar_call_count=0,
        raw_audio_public_artifact_count=RAW_AUDIO_PUBLIC_ARTIFACT_COUNT,
        raw_transcript_public_artifact_count=RAW_TRANSCRIPT_PUBLIC_ARTIFACT_COUNT,
        raw_payload_public_artifact_count=RAW_PAYLOAD_PUBLIC_ARTIFACT_COUNT,
        client_secret_exposure_count=CLIENT_SECRET_EXPOSURE_COUNT,
        public_private_path_leakage_count=0,
        public_secret_like_leakage_count=0,
        public_raw_payload_leakage_count=0,
        approval_decision="blocked_missing_azure_credentials",
    )
    return summary.model_copy(
        update={
            "approval_decision": build_approval_decision(
                summary=summary,
                output_quality=None,
            ),
        },
    )


def build_approval_decision(
    *,
    summary: AzureCredentialReadyApprovalSummary,
    output_quality: PublicRetrievalArtifactQuality | None,
) -> ApprovalDecision:
    public_safety_passed = output_quality is None or not collect_public_retrieval_artifact_failures(
        output_quality,
    )
    zero_call_boundary = (
        summary.managed_provider_api_call_count == 0
        and summary.external_audio_transmission_count == 0
        and summary.live_stt_call_count == 0
        and summary.live_tts_call_count == 0
        and summary.live_solar_call_count == 0
        and summary.raw_audio_public_artifact_count == 0
        and summary.raw_transcript_public_artifact_count == 0
        and summary.raw_payload_public_artifact_count == 0
        and summary.client_secret_exposure_count == 0
        and summary.credential_value_public_exposure_count == 0
    )
    if not public_safety_passed or not zero_call_boundary:
        return "blocked_by_public_safety_gate"
    if not summary.azure_credential_ready:
        return "blocked_missing_azure_credentials"
    if (
        summary.source_recheck_completed_for_execution_count
        != summary.source_recheck_required_before_execution_count
        or not summary.region_confirmation_completed
        or not summary.retention_confirmation_completed
        or not summary.cost_confirmation_completed
    ):
        return "blocked_source_recheck_incomplete"
    if not summary.user_external_call_approval_recorded:
        return "blocked_missing_user_external_call_approval"
    return "ready_for_actual_azure_smoke_execution"


def build_report(
    *,
    approval_id: str,
    env_path: Path,
    scripts_path: Path,
    result_rows_path: Path,
    source_rechecks: tuple[AzureCredentialReadySourceRow, ...],
    metric_rows: tuple[AzureSmokeMetricPlanRow, ...],
    summary: AzureCredentialReadyApprovalSummary,
    output_quality: PublicRetrievalArtifactQuality,
) -> AzureCredentialReadyApprovalReport:
    report = AzureCredentialReadyApprovalReport(
        approval_id=approval_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        env_path_status="present" if project_path(env_path).exists() else "missing",
        scripts_path=public_path_alias(scripts_path),
        result_path=public_path_alias(result_rows_path),
        source_fingerprint=_stable_digest(
            {
                "source_rechecks": [
                    row.model_dump(mode="json") for row in source_rechecks
                ],
                "metric_rows": [row.model_dump(mode="json") for row in metric_rows],
            },
        ),
        source_rechecks=source_rechecks,
        metric_plan_rows=metric_rows,
        summary=summary,
        output_quality=output_quality,
        qualitative_assessment={},
    )
    return report.model_copy(
        update={"qualitative_assessment": build_qualitative_assessment(report)},
    )


def build_public_rows(
    *,
    approval_id: str,
    source_rechecks: tuple[AzureCredentialReadySourceRow, ...],
    metric_rows: tuple[AzureSmokeMetricPlanRow, ...],
    summary: AzureCredentialReadyApprovalSummary,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "row_type": "summary",
            "approval_id": approval_id,
            "provider_candidate_id": PROVIDER_CANDIDATE_ID,
            "azure_credential_ready": summary.azure_credential_ready,
            "azure_smoke_execution_ready": summary.azure_smoke_execution_ready,
            "azure_smoke_execution_approved": summary.azure_smoke_execution_approved,
            "approval_decision": summary.approval_decision,
            "managed_provider_api_call_count": summary.managed_provider_api_call_count,
            "external_audio_transmission_count": (
                summary.external_audio_transmission_count
            ),
        },
    ]
    rows.extend(
        {
            "row_type": "source_recheck",
            "approval_id": approval_id,
            "provider_candidate_id": PROVIDER_CANDIDATE_ID,
            "source_check_type": row.source_check_type,
            "recheck_required_before_execution": row.recheck_required_before_execution,
            "recheck_completed_for_execution": row.recheck_completed_for_execution,
        }
        for row in source_rechecks
    )
    rows.extend(
        {
            "row_type": "metric_plan",
            "approval_id": approval_id,
            "provider_candidate_id": PROVIDER_CANDIDATE_ID,
            "metric_name": row.metric_name,
            "metric_family": row.metric_family,
            "value_status": row.value_status,
        }
        for row in metric_rows
    )
    return rows


def collect_azure_credential_ready_and_smoke_approval_failures(
    report: AzureCredentialReadyApprovalReport,
) -> list[str]:
    failures = collect_public_retrieval_artifact_failures(report.output_quality)
    summary = report.summary
    if summary.approval_decision == "blocked_by_public_safety_gate":
        failures.append("public_safety_gate_blocked")
    if summary.provider_candidate_count != 1:
        failures.append("provider_candidate_count_mismatch")
    if not summary.first_provider_candidate_is_azure:
        failures.append("first_provider_is_not_azure")
    if summary.credential_env_var_name_count != len(AZURE_CREDENTIAL_ENV_NAMES):
        failures.append("credential_env_var_name_count_mismatch")
    if summary.planned_script_count != DEFAULT_SCRIPT_LIMIT:
        failures.append("planned_script_count_mismatch")
    if not summary.call_cap_enforced:
        failures.append("call_cap_not_enforced")
    if summary.managed_provider_api_call_count:
        failures.append("managed_provider_api_called")
    if summary.external_audio_transmission_count:
        failures.append("external_audio_transmitted")
    if summary.live_stt_call_count:
        failures.append("live_stt_called")
    if summary.live_tts_call_count:
        failures.append("live_tts_called")
    if summary.live_solar_call_count:
        failures.append("live_solar_called")
    if summary.credential_value_public_exposure_count:
        failures.append("credential_value_public_exposed")
    if summary.raw_audio_public_artifact_count:
        failures.append("raw_audio_public_artifact_created")
    if summary.raw_transcript_public_artifact_count:
        failures.append("raw_transcript_public_artifact_created")
    if summary.raw_payload_public_artifact_count:
        failures.append("raw_payload_public_artifact_created")
    if summary.client_secret_exposure_count:
        failures.append("client_secret_exposed")
    return list(dict.fromkeys(failures))


def build_doc_markdown(report: AzureCredentialReadyApprovalReport) -> str:
    summary = report.summary
    source_rows = "\n".join(_format_source_row(row) for row in report.source_rechecks)
    metric_rows = "\n".join(_format_metric_row(row) for row in report.metric_plan_rows)
    return f"""# Voice STT/TTS Azure Credential Ready And Smoke Approval

## 결론

`{WORK_ID}`는 Azure credential 준비 여부와 실제 smoke 승인 가능성을 점검한다.

현재 `approval_decision={summary.approval_decision}`이며, Azure API call과 external audio transmission은 0회다.

이 gate는 실제 Azure STT/TTS smoke가 아니라, credential/source/region/retention/cost/user approval이 모두 충족됐는지 판정하는 마지막 zero-call approval gate다.

## Approval Status

| field | value |
| --- | --- |
| `work_id` | `{report.work_id}` |
| `depends_on` | `{report.depends_on}` |
| `next_work_id` | `{report.next_work_id}` |
| `provider_candidate_id` | `{report.provider_candidate_id}` |
| `azure_credential_ready` | `{str(summary.azure_credential_ready).lower()}` |
| `azure_smoke_execution_ready` | `{str(summary.azure_smoke_execution_ready).lower()}` |
| `azure_smoke_execution_approved` | `{str(summary.azure_smoke_execution_approved).lower()}` |
| `approval_decision` | `{summary.approval_decision}` |
| `managed_provider_api_call_count` | `{summary.managed_provider_api_call_count}` |
| `external_audio_transmission_count` | `{summary.external_audio_transmission_count}` |
| `live_stt_call_count` | `{summary.live_stt_call_count}` |
| `live_tts_call_count` | `{summary.live_tts_call_count}` |
| `live_solar_call_count` | `{summary.live_solar_call_count}` |

## Required Credentials

- `AZURE_SPEECH_KEY`
- `AZURE_SPEECH_REGION`

## Source Recheck

| source_check_type | required | completed |
| --- | --- | --- |
{source_rows}

## Metric Plan

| metric | family | status |
| --- | --- | --- |
{metric_rows}

## Data Mart Grain

| table | grain | visibility |
| --- | --- | --- |
| `fact_voice_azure_credential_ready_approval` | `approval_id + provider_candidate_id` | public aggregate |
| `fact_voice_azure_credential_ready_source_recheck` | `approval_id + source_check_type` | public aggregate |
| `fact_voice_azure_credential_ready_metric_plan` | `approval_id + provider_candidate_id + metric_name` | public aggregate |
| `fact_voice_azure_smoke_private_stt_eval` | `run_id + provider_candidate_id + script_id + metric_name` | private only |
| `fact_voice_azure_smoke_private_tts_eval` | `run_id + provider_candidate_id + script_id + metric_name` | private only |
| `fact_voice_azure_smoke_public_summary` | `run_id + provider_candidate_id + metric_name` | public aggregate |

## Stop Conditions

- `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION` 중 하나라도 missing인 경우

- source, region, retention, cost 재확인이 완료되지 않은 경우

- 사용자 별도 external call 승인이 없는 경우

- raw audio, raw transcript, provider payload가 public artifact에 남을 가능성이 있는 경우

- 비용 cap 또는 quota 상태가 불명확한 경우

## Claim Boundary

허용 claim:

- Azure credential ready와 smoke approval gate를 구현했다.

- 현재 Azure API call과 external audio transmission은 0회다.

- credential 값과 raw audio/transcript/payload는 public artifact에 기록하지 않았다.

- 실제 Azure smoke는 credential, source, region, retention, cost, 사용자 external call 승인이 모두 충족될 때만 가능하다.

금지 claim:

- Azure STT/TTS 품질 검증 완료
- Azure managed provider smoke 실행 완료
- Azure provider 최종 선택 완료
- production voice service 준비 완료
- 외부 audio 전송 검증 완료
"""


def build_report_markdown(report: AzureCredentialReadyApprovalReport) -> str:
    summary = report.summary
    quality = report.output_quality
    source_rows = "\n".join(_format_source_row(row) for row in report.source_rechecks)
    metric_rows = "\n".join(_format_metric_row(row) for row in report.metric_plan_rows)
    qualitative_rows = "\n".join(
        f"| {key} | {value} |" for key, value in report.qualitative_assessment.items()
    )
    failures = collect_azure_credential_ready_and_smoke_approval_failures(report)
    return f"""# Voice STT/TTS Azure Credential Ready And Smoke Approval Report

`{WORK_ID}`는 {"PASS" if not failures else "FAIL"}다.

이번 report는 실제 Azure STT/TTS smoke 결과가 아니라 credential ready와 smoke approval gate 결과다.

## Execution Info

| field | value |
| --- | --- |
| report_version | `{report.report_version}` |
| approval_id | `{report.approval_id}` |
| work_id | `{report.work_id}` |
| depends_on | `{report.depends_on}` |
| next_work_id | `{report.next_work_id}` |
| provider_candidate_id | `{report.provider_candidate_id}` |
| generated_at_utc | `{report.generated_at_utc}` |
| env_path_status | `{report.env_path_status}` |
| scripts_path | `{report.scripts_path}` |
| result_path | `{report.result_path}` |
| source_fingerprint | `{report.source_fingerprint}` |

## Quantitative Evaluation

| metric | value |
| --- | --- |
| provider_candidate_count | {summary.provider_candidate_count} |
| first_provider_candidate_is_azure | {str(summary.first_provider_candidate_is_azure).lower()} |
| credential_env_var_name_count | {summary.credential_env_var_name_count} |
| credential_present_count | {summary.credential_present_count} |
| credential_missing_count | {summary.credential_missing_count} |
| azure_credential_ready | {str(summary.azure_credential_ready).lower()} |
| credential_value_public_exposure_count | {summary.credential_value_public_exposure_count} |
| planned_script_count | {summary.planned_script_count} |
| planned_stt_call_count | {summary.planned_stt_call_count} |
| planned_tts_call_count | {summary.planned_tts_call_count} |
| call_cap_enforced | {str(summary.call_cap_enforced).lower()} |
| source_recheck_required_before_execution_count | {summary.source_recheck_required_before_execution_count} |
| source_recheck_completed_for_execution_count | {summary.source_recheck_completed_for_execution_count} |
| region_confirmation_completed | {str(summary.region_confirmation_completed).lower()} |
| retention_confirmation_completed | {str(summary.retention_confirmation_completed).lower()} |
| cost_confirmation_completed | {str(summary.cost_confirmation_completed).lower()} |
| user_external_call_approval_recorded | {str(summary.user_external_call_approval_recorded).lower()} |
| azure_smoke_execution_ready | {str(summary.azure_smoke_execution_ready).lower()} |
| azure_smoke_execution_approved | {str(summary.azure_smoke_execution_approved).lower()} |
| managed_provider_api_call_count | {summary.managed_provider_api_call_count} |
| external_audio_transmission_count | {summary.external_audio_transmission_count} |
| live_stt_call_count | {summary.live_stt_call_count} |
| live_tts_call_count | {summary.live_tts_call_count} |
| live_solar_call_count | {summary.live_solar_call_count} |
| raw_audio_public_artifact_count | {summary.raw_audio_public_artifact_count} |
| raw_transcript_public_artifact_count | {summary.raw_transcript_public_artifact_count} |
| raw_payload_public_artifact_count | {summary.raw_payload_public_artifact_count} |
| client_secret_exposure_count | {summary.client_secret_exposure_count} |
| public_private_path_leakage_count | {summary.public_private_path_leakage_count} |
| public_secret_like_leakage_count | {summary.public_secret_like_leakage_count} |
| public_raw_payload_leakage_count | {summary.public_raw_payload_leakage_count} |
| approval_decision | `{summary.approval_decision}` |

## Source Recheck

| source_check_type | recheck_required | recheck_completed |
| --- | --- | --- |
{source_rows}

## Metric Plan

| metric | family | status |
| --- | --- | --- |
{metric_rows}

## Public Safety

| metric | value |
| --- | ---: |
| result_row_count | {quality.result_row_count} |
| public_raw_text_leakage_count | {quality.public_raw_text_leakage_count} |
| private_path_leakage_count | {quality.private_path_leakage_count} |
| secret_like_leakage_count | {quality.secret_like_leakage_count} |
| forbidden_result_field_count | {quality.forbidden_result_field_count} |

## Data Mart Grain

| table | grain | visibility |
| --- | --- | --- |
| `fact_voice_azure_credential_ready_approval` | `approval_id + provider_candidate_id` | public aggregate |
| `fact_voice_azure_credential_ready_source_recheck` | `approval_id + source_check_type` | public aggregate |
| `fact_voice_azure_credential_ready_metric_plan` | `approval_id + provider_candidate_id + metric_name` | public aggregate |
| `fact_voice_azure_smoke_private_stt_eval` | `run_id + provider_candidate_id + script_id + metric_name` | private only |
| `fact_voice_azure_smoke_private_tts_eval` | `run_id + provider_candidate_id + script_id + metric_name` | private only |
| `fact_voice_azure_smoke_public_summary` | `run_id + provider_candidate_id + metric_name` | public aggregate |

## Qualitative Evaluation

| item | result |
| --- | --- |
{qualitative_rows}

## External Audit

| audit_item | result |
| --- | --- |
| Azure API call 0 유지 | PASS |
| external audio transmission 0 유지 | PASS |
| credential 값 미기록 | PASS |
| raw audio/transcript/payload public artifact 금지 | PASS |
| credential/source/region/retention/cost/user approval 미충족 시 실행 차단 | PASS |
"""


def build_qualitative_assessment(
    report: AzureCredentialReadyApprovalReport,
) -> dict[str, str]:
    summary = report.summary
    if summary.approval_decision == "blocked_missing_azure_credentials":
        operations_boundary = "Azure credential이 준비되지 않아 실제 smoke 승인으로 넘어가지 않는다."
    elif summary.approval_decision == "blocked_source_recheck_incomplete":
        operations_boundary = "credential은 준비됐더라도 source, region, retention, cost 확인 전에는 실행하지 않는다."
    elif summary.approval_decision == "blocked_missing_user_external_call_approval":
        operations_boundary = "외부 audio 전송과 비용 발생에 대한 별도 승인이 없어 실행하지 않는다."
    else:
        operations_boundary = "모든 zero-call gate가 충족되어 실제 Azure smoke 실행 승인을 받을 수 있다."
    return {
        "security_boundary": "credential 값, raw audio, raw transcript, provider payload를 public artifact에 기록하지 않는다.",
        "eval_boundary": "이번 결과는 approval gate이며 Azure STT/TTS 품질 비교가 아니다.",
        "data_mart_boundary": "approval, source recheck, metric plan, private metric grain을 분리했다.",
        "operations_boundary": operations_boundary,
    }


def build_approval_id(
    *,
    source_rechecks: tuple[AzureCredentialReadySourceRow, ...],
    metric_rows: tuple[AzureSmokeMetricPlanRow, ...],
    summary: AzureCredentialReadyApprovalSummary,
) -> str:
    return "azure-credential-ready-smoke-approval-" + _stable_digest(
        {
            "source_rechecks": [row.model_dump(mode="json") for row in source_rechecks],
            "metric_rows": [row.model_dump(mode="json") for row in metric_rows],
            "summary": summary.model_dump(mode="json"),
        },
    )


def _format_source_row(row: AzureCredentialReadySourceRow) -> str:
    return (
        f"| `{row.source_check_type}` | "
        f"{str(row.recheck_required_before_execution).lower()} | "
        f"{str(row.recheck_completed_for_execution).lower()} |"
    )


def _format_metric_row(row: AzureSmokeMetricPlanRow) -> str:
    return f"| `{row.metric_name}` | `{row.metric_family}` | `{row.value_status}` |"


def _stable_digest(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"),
    ).hexdigest()[:16]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Azure credential-ready smoke approval gate without API calls.",
    )
    parser.add_argument("--env", type=Path, default=DEFAULT_ENV_PATH)
    parser.add_argument("--scripts", type=Path, default=DEFAULT_SCRIPTS_PATH)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--result-rows", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    parser.add_argument("--source-recheck-completed", action="store_true")
    parser.add_argument("--region-confirmed", action="store_true")
    parser.add_argument("--retention-confirmed", action="store_true")
    parser.add_argument("--cost-confirmed", action="store_true")
    parser.add_argument("--user-external-call-approval", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_voice_stt_tts_azure_credential_ready_and_smoke_approval(
        env_path=args.env,
        scripts_path=args.scripts,
        doc_path=args.doc,
        report_path=args.report,
        result_rows_path=args.result_rows,
        source_recheck_completed=args.source_recheck_completed,
        region_confirmation_completed=args.region_confirmed,
        retention_confirmation_completed=args.retention_confirmed,
        cost_confirmation_completed=args.cost_confirmed,
        user_external_call_approval_recorded=args.user_external_call_approval,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
