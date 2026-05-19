from __future__ import annotations

import argparse
import hashlib
import json
import os
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
from pipelines.voice_stt_tts_managed_provider_smoke import (
    CLIENT_SECRET_EXPOSURE_COUNT,
    DEFAULT_SCRIPT_LIMIT,
    EXTERNAL_AUDIO_TRANSMISSION_COUNT,
    LIVE_SOLAR_CALL_COUNT,
    LIVE_STT_CALL_COUNT,
    LIVE_TTS_CALL_COUNT,
    MANAGED_PROVIDER_API_CALL_COUNT,
    MAX_STT_CALLS_PER_PROVIDER,
    MAX_TTS_CALLS_PER_PROVIDER,
    RAW_AUDIO_PUBLIC_ARTIFACT_COUNT,
    RAW_PAYLOAD_PUBLIC_ARTIFACT_COUNT,
    RAW_TRANSCRIPT_PUBLIC_ARTIFACT_COUNT,
)
from pipelines.voice_stt_tts_provider_bench_readiness import DEFAULT_SCRIPTS_PATH


REPORT_VERSION = "voice-stt-tts-azure-credential-preflight-report/v1"
WORK_ID = "HD-VOICE-STT-TTS-AZURE-CREDENTIAL-PREFLIGHT-001"
DEPENDS_ON = "HD-VOICE-STT-TTS-AZURE-MANAGED-SMOKE-READINESS-001"
NEXT_WORK_ID = "HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-001"
PROVIDER_CANDIDATE_ID = "managed_azure_ai_speech"
DEFAULT_ENV_PATH = Path(".env")
DEFAULT_DOC_PATH = Path("docs") / "VOICE_STT_TTS_AZURE_CREDENTIAL_PREFLIGHT.md"
DEFAULT_REPORT_PATH = (
    Path("evals") / "reports" / "voice_stt_tts_azure_credential_preflight_report.md"
)
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "voice_stt_tts_azure_credential_preflight_rows.jsonl"
)
AZURE_CREDENTIAL_ENV_NAMES = ("AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION")
AZURE_SOURCE_CHECKS = (
    (
        "region_resource_binding",
        "https://learn.microsoft.com/en-us/azure/ai-services/speech-service/regions",
    ),
    (
        "pricing_billing_unit",
        "https://azure.microsoft.com/en-us/pricing/details/speech/",
    ),
    (
        "korean_language_support",
        "https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=stt-tts",
    ),
    (
        "stt_data_privacy_security",
        "https://learn.microsoft.com/en-us/azure/foundry/responsible-ai/speech-service/speech-to-text/data-privacy-security",
    ),
    (
        "tts_data_privacy_security",
        "https://learn.microsoft.com/en-us/azure/foundry/responsible-ai/speech-service/text-to-speech/data-privacy-security",
    ),
)
MANAGED_PROVIDER_EXECUTION_REQUESTED_COUNT = 0
CREDENTIAL_VALUE_PUBLIC_EXPOSURE_COUNT = 0
SOURCE_RECHECK_COMPLETED_COUNT = 0

CredentialStatus = Literal["missing", "present"]
CredentialPreflightDecision = Literal[
    "ready_for_selected_provider_smoke_execution_approval",
    "blocked_missing_azure_credentials",
    "blocked_by_public_safety_gate",
]


class AzureCredentialPreflightModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AzureCredentialCheckRow(AzureCredentialPreflightModel):
    env_name: str = Field(min_length=1)
    credential_status: CredentialStatus
    value_public_exposure_count: int = Field(ge=0)


class AzureSourceCheckRow(AzureCredentialPreflightModel):
    source_check_type: str = Field(min_length=1)
    url: str = Field(min_length=1)
    recheck_required_before_execution: bool
    recheck_completed_for_execution: bool


class AzureCredentialPreflightSummary(AzureCredentialPreflightModel):
    provider_candidate_count: int = Field(ge=0)
    first_provider_candidate_is_azure: bool
    planned_script_count: int = Field(ge=0)
    planned_stt_call_count: int = Field(ge=0)
    planned_tts_call_count: int = Field(ge=0)
    call_cap_enforced: bool
    azure_credential_ready: bool
    credential_env_var_name_count: int = Field(ge=0)
    credential_present_count: int = Field(ge=0)
    credential_missing_count: int = Field(ge=0)
    credential_value_public_exposure_count: int = Field(ge=0)
    managed_provider_execution_requested_count: int = Field(ge=0)
    managed_provider_api_call_count: int = Field(ge=0)
    external_audio_transmission_count: int = Field(ge=0)
    live_stt_call_count: int = Field(ge=0)
    live_tts_call_count: int = Field(ge=0)
    live_solar_call_count: int = Field(ge=0)
    official_source_reference_count: int = Field(ge=0)
    source_recheck_required_before_execution_count: int = Field(ge=0)
    source_recheck_completed_for_execution_count: int = Field(ge=0)
    region_recheck_required_count: int = Field(ge=0)
    retention_recheck_required_count: int = Field(ge=0)
    cost_confirmation_required_count: int = Field(ge=0)
    raw_audio_public_artifact_count: int = Field(ge=0)
    raw_transcript_public_artifact_count: int = Field(ge=0)
    raw_payload_public_artifact_count: int = Field(ge=0)
    client_secret_exposure_count: int = Field(ge=0)
    public_private_path_leakage_count: int = Field(ge=0)
    public_secret_like_leakage_count: int = Field(ge=0)
    public_raw_payload_leakage_count: int = Field(ge=0)
    preflight_decision: CredentialPreflightDecision


class AzureCredentialPreflightReport(AzureCredentialPreflightModel):
    report_version: str = REPORT_VERSION
    preflight_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    work_id: str = WORK_ID
    depends_on: str = DEPENDS_ON
    next_work_id: str = NEXT_WORK_ID
    provider_candidate_id: str = PROVIDER_CANDIDATE_ID
    env_path_status: Literal["present", "missing"]
    scripts_path: str = Field(min_length=1)
    result_path: str = Field(min_length=1)
    source_fingerprint: str = Field(min_length=8)
    credential_checks: tuple[AzureCredentialCheckRow, ...]
    source_checks: tuple[AzureSourceCheckRow, ...]
    summary: AzureCredentialPreflightSummary
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def run_voice_stt_tts_azure_credential_preflight(
    *,
    env_path: Path = DEFAULT_ENV_PATH,
    scripts_path: Path = DEFAULT_SCRIPTS_PATH,
    doc_path: Path = DEFAULT_DOC_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
    execute_managed_provider: bool = False,
) -> AzureCredentialPreflightReport:
    if execute_managed_provider:
        raise ValueError(
            "Azure provider execution is blocked in credential preflight; "
            "run the selected-provider smoke work order after source recheck and approval",
        )

    credential_checks = build_credential_checks(env_path=env_path)
    source_checks = build_source_checks()
    summary = build_summary(credential_checks=credential_checks, source_checks=source_checks)
    preflight_id = build_preflight_id(
        credential_checks=credential_checks,
        source_checks=source_checks,
        summary=summary,
    )
    public_rows = build_public_rows(
        preflight_id=preflight_id,
        credential_checks=credential_checks,
        source_checks=source_checks,
        summary=summary,
    )
    provisional_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=preflight_id,
        result_rows=public_rows,
        report_text="",
    )
    provisional = build_report(
        preflight_id=preflight_id,
        env_path=env_path,
        scripts_path=scripts_path,
        result_rows_path=result_rows_path,
        credential_checks=credential_checks,
        source_checks=source_checks,
        summary=summary,
        output_quality=provisional_quality,
    )
    doc_text = build_doc_markdown(provisional)
    report_text = build_report_markdown(provisional)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=preflight_id,
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
            "preflight_decision": build_preflight_decision(
                summary=summary,
                output_quality=output_quality,
            ),
        },
    )
    report = build_report(
        preflight_id=preflight_id,
        env_path=env_path,
        scripts_path=scripts_path,
        result_rows_path=result_rows_path,
        credential_checks=credential_checks,
        source_checks=source_checks,
        summary=summary,
        output_quality=output_quality,
    )
    failures = collect_azure_credential_preflight_failures(report)
    if failures:
        raise ValueError(f"Azure credential preflight gate failed: {failures}")

    write_public_retrieval_result_rows(
        path=project_path(result_rows_path),
        rows=build_public_rows(
            preflight_id=preflight_id,
            credential_checks=credential_checks,
            source_checks=source_checks,
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
        "voice_stt_tts_azure_credential_preflight "
        "status=PASS "
        f"azure_credential_ready={str(report.summary.azure_credential_ready).lower()} "
        f"credential_present={report.summary.credential_present_count} "
        f"credential_missing={report.summary.credential_missing_count} "
        f"managed_provider_api_calls={report.summary.managed_provider_api_call_count} "
        f"external_audio_transmissions={report.summary.external_audio_transmission_count}",
    )
    return report


def build_credential_checks(*, env_path: Path) -> tuple[AzureCredentialCheckRow, ...]:
    env_file_values = _read_env_file_values(env_path)
    rows: list[AzureCredentialCheckRow] = []
    for env_name in AZURE_CREDENTIAL_ENV_NAMES:
        is_present = bool(os.environ.get(env_name) or env_file_values.get(env_name))
        rows.append(
            AzureCredentialCheckRow(
                env_name=env_name,
                credential_status="present" if is_present else "missing",
                value_public_exposure_count=CREDENTIAL_VALUE_PUBLIC_EXPOSURE_COUNT,
            ),
        )
    return tuple(rows)


def build_source_checks() -> tuple[AzureSourceCheckRow, ...]:
    return tuple(
        AzureSourceCheckRow(
            source_check_type=source_check_type,
            url=url,
            recheck_required_before_execution=True,
            recheck_completed_for_execution=False,
        )
        for source_check_type, url in AZURE_SOURCE_CHECKS
    )


def build_summary(
    *,
    credential_checks: tuple[AzureCredentialCheckRow, ...],
    source_checks: tuple[AzureSourceCheckRow, ...],
) -> AzureCredentialPreflightSummary:
    credential_present_count = sum(
        1 for row in credential_checks if row.credential_status == "present"
    )
    credential_missing_count = len(credential_checks) - credential_present_count
    azure_credential_ready = credential_missing_count == 0
    call_cap_enforced = (
        DEFAULT_SCRIPT_LIMIT <= MAX_STT_CALLS_PER_PROVIDER
        and DEFAULT_SCRIPT_LIMIT <= MAX_TTS_CALLS_PER_PROVIDER
    )
    summary = AzureCredentialPreflightSummary(
        provider_candidate_count=1,
        first_provider_candidate_is_azure=True,
        planned_script_count=DEFAULT_SCRIPT_LIMIT,
        planned_stt_call_count=DEFAULT_SCRIPT_LIMIT,
        planned_tts_call_count=DEFAULT_SCRIPT_LIMIT,
        call_cap_enforced=call_cap_enforced,
        azure_credential_ready=azure_credential_ready,
        credential_env_var_name_count=len(credential_checks),
        credential_present_count=credential_present_count,
        credential_missing_count=credential_missing_count,
        credential_value_public_exposure_count=sum(
            row.value_public_exposure_count for row in credential_checks
        ),
        managed_provider_execution_requested_count=MANAGED_PROVIDER_EXECUTION_REQUESTED_COUNT,
        managed_provider_api_call_count=MANAGED_PROVIDER_API_CALL_COUNT,
        external_audio_transmission_count=EXTERNAL_AUDIO_TRANSMISSION_COUNT,
        live_stt_call_count=LIVE_STT_CALL_COUNT,
        live_tts_call_count=LIVE_TTS_CALL_COUNT,
        live_solar_call_count=LIVE_SOLAR_CALL_COUNT,
        official_source_reference_count=len(source_checks),
        source_recheck_required_before_execution_count=sum(
            1 for row in source_checks if row.recheck_required_before_execution
        ),
        source_recheck_completed_for_execution_count=SOURCE_RECHECK_COMPLETED_COUNT,
        region_recheck_required_count=1,
        retention_recheck_required_count=1,
        cost_confirmation_required_count=1,
        raw_audio_public_artifact_count=RAW_AUDIO_PUBLIC_ARTIFACT_COUNT,
        raw_transcript_public_artifact_count=RAW_TRANSCRIPT_PUBLIC_ARTIFACT_COUNT,
        raw_payload_public_artifact_count=RAW_PAYLOAD_PUBLIC_ARTIFACT_COUNT,
        client_secret_exposure_count=CLIENT_SECRET_EXPOSURE_COUNT,
        public_private_path_leakage_count=0,
        public_secret_like_leakage_count=0,
        public_raw_payload_leakage_count=0,
        preflight_decision="blocked_missing_azure_credentials",
    )
    return summary.model_copy(
        update={
            "preflight_decision": build_preflight_decision(
                summary=summary,
                output_quality=None,
            ),
        },
    )


def build_preflight_decision(
    *,
    summary: AzureCredentialPreflightSummary,
    output_quality: PublicRetrievalArtifactQuality | None,
) -> CredentialPreflightDecision:
    public_safety_passed = output_quality is None or not collect_public_retrieval_artifact_failures(
        output_quality,
    )
    base_gate_passed = (
        summary.provider_candidate_count == 1
        and summary.first_provider_candidate_is_azure
        and summary.planned_script_count == DEFAULT_SCRIPT_LIMIT
        and summary.planned_stt_call_count <= MAX_STT_CALLS_PER_PROVIDER
        and summary.planned_tts_call_count <= MAX_TTS_CALLS_PER_PROVIDER
        and summary.call_cap_enforced
        and summary.managed_provider_execution_requested_count == 0
        and summary.managed_provider_api_call_count == 0
        and summary.external_audio_transmission_count == 0
        and summary.live_stt_call_count == 0
        and summary.live_tts_call_count == 0
        and summary.live_solar_call_count == 0
        and summary.credential_value_public_exposure_count == 0
        and summary.raw_audio_public_artifact_count == 0
        and summary.raw_transcript_public_artifact_count == 0
        and summary.raw_payload_public_artifact_count == 0
        and summary.client_secret_exposure_count == 0
        and public_safety_passed
    )
    if not base_gate_passed:
        return "blocked_by_public_safety_gate"
    if summary.azure_credential_ready:
        return "ready_for_selected_provider_smoke_execution_approval"
    return "blocked_missing_azure_credentials"


def build_report(
    *,
    preflight_id: str,
    env_path: Path,
    scripts_path: Path,
    result_rows_path: Path,
    credential_checks: tuple[AzureCredentialCheckRow, ...],
    source_checks: tuple[AzureSourceCheckRow, ...],
    summary: AzureCredentialPreflightSummary,
    output_quality: PublicRetrievalArtifactQuality,
) -> AzureCredentialPreflightReport:
    report = AzureCredentialPreflightReport(
        preflight_id=preflight_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        env_path_status="present" if project_path(env_path).exists() else "missing",
        scripts_path=public_path_alias(scripts_path),
        result_path=public_path_alias(result_rows_path),
        source_fingerprint=_stable_digest(
            {
                "credential_checks": [
                    row.model_dump(mode="json") for row in credential_checks
                ],
                "source_checks": [row.model_dump(mode="json") for row in source_checks],
            },
        ),
        credential_checks=credential_checks,
        source_checks=source_checks,
        summary=summary,
        output_quality=output_quality,
        qualitative_assessment={},
    )
    return report.model_copy(
        update={"qualitative_assessment": build_qualitative_assessment(report)},
    )


def build_public_rows(
    *,
    preflight_id: str,
    credential_checks: tuple[AzureCredentialCheckRow, ...],
    source_checks: tuple[AzureSourceCheckRow, ...],
    summary: AzureCredentialPreflightSummary,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "row_type": "summary",
            "preflight_id": preflight_id,
            "provider_candidate_id": PROVIDER_CANDIDATE_ID,
            "azure_credential_ready": summary.azure_credential_ready,
            "credential_present_count": summary.credential_present_count,
            "credential_missing_count": summary.credential_missing_count,
            "managed_provider_api_call_count": summary.managed_provider_api_call_count,
            "external_audio_transmission_count": summary.external_audio_transmission_count,
            "source_recheck_completed_for_execution_count": (
                summary.source_recheck_completed_for_execution_count
            ),
            "preflight_decision": summary.preflight_decision,
        },
    ]
    rows.extend(
        {
            "row_type": "credential_check",
            "preflight_id": preflight_id,
            "provider_candidate_id": PROVIDER_CANDIDATE_ID,
            "env_name": row.env_name,
            "credential_status": row.credential_status,
            "value_public_exposure_count": row.value_public_exposure_count,
        }
        for row in credential_checks
    )
    rows.extend(
        {
            "row_type": "source_check",
            "preflight_id": preflight_id,
            "provider_candidate_id": PROVIDER_CANDIDATE_ID,
            "source_check_type": row.source_check_type,
            "recheck_required_before_execution": row.recheck_required_before_execution,
            "recheck_completed_for_execution": row.recheck_completed_for_execution,
        }
        for row in source_checks
    )
    return rows


def collect_azure_credential_preflight_failures(
    report: AzureCredentialPreflightReport,
) -> list[str]:
    failures = collect_public_retrieval_artifact_failures(report.output_quality)
    summary = report.summary
    if summary.preflight_decision == "blocked_by_public_safety_gate":
        failures.append("public_safety_gate_blocked")
    if summary.provider_candidate_count != 1:
        failures.append("provider_candidate_count_mismatch")
    if not summary.first_provider_candidate_is_azure:
        failures.append("first_provider_is_not_azure")
    if summary.planned_script_count != DEFAULT_SCRIPT_LIMIT:
        failures.append("planned_script_count_mismatch")
    if not summary.call_cap_enforced:
        failures.append("call_cap_not_enforced")
    if summary.managed_provider_execution_requested_count:
        failures.append("managed_provider_execution_requested")
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


def build_doc_markdown(report: AzureCredentialPreflightReport) -> str:
    summary = report.summary
    credential_rows = "\n".join(
        _format_credential_row(row) for row in report.credential_checks
    )
    source_rows = "\n".join(_format_source_doc_row(row) for row in report.source_checks)
    return f"""# Voice STT/TTS Azure Credential Preflight

`{WORK_ID}`는 Azure managed STT/TTS smoke 실행 전 credential 존재 여부와 source 재확인 조건을 자동 점검한다.

결론: 이 단계는 Azure API를 호출하지 않는다. credential 값, raw audio, raw transcript, provider payload도 public artifact에 기록하지 않는다.

## Scope

| field | value |
| --- | --- |
| work_id | `{WORK_ID}` |
| depends_on | `{DEPENDS_ON}` |
| next_work_id | `{NEXT_WORK_ID}` |
| provider_candidate_id | `{PROVIDER_CANDIDATE_ID}` |
| azure_credential_ready | {str(summary.azure_credential_ready).lower()} |
| managed_provider_api_call_count | {summary.managed_provider_api_call_count} |
| external_audio_transmission_count | {summary.external_audio_transmission_count} |
| preflight_decision | `{summary.preflight_decision}` |

## Credential Check

credential 값은 읽더라도 출력하지 않는다. 아래 표는 존재 여부만 기록한다.

| env name | status | value exposure |
| --- | --- | ---: |
{credential_rows}

## Source Recheck

실제 smoke 직전 같은 날짜에 다시 확인한다. 이 preflight는 최신 가격/정책 확인 완료 claim이 아니다.

| source_check_type | source reference | execution gate |
| --- | --- | --- |
{source_rows}

## Quantitative Gate

| metric | value |
| --- | ---: |
| provider_candidate_count | {summary.provider_candidate_count} |
| first_provider_candidate_is_azure | {str(summary.first_provider_candidate_is_azure).lower()} |
| planned_script_count | {summary.planned_script_count} |
| planned_stt_call_count | {summary.planned_stt_call_count} |
| planned_tts_call_count | {summary.planned_tts_call_count} |
| call_cap_enforced | {str(summary.call_cap_enforced).lower()} |
| azure_credential_ready | {str(summary.azure_credential_ready).lower()} |
| credential_env_var_name_count | {summary.credential_env_var_name_count} |
| credential_present_count | {summary.credential_present_count} |
| credential_missing_count | {summary.credential_missing_count} |
| credential_value_public_exposure_count | {summary.credential_value_public_exposure_count} |
| managed_provider_execution_requested_count | {summary.managed_provider_execution_requested_count} |
| managed_provider_api_call_count | {summary.managed_provider_api_call_count} |
| external_audio_transmission_count | {summary.external_audio_transmission_count} |
| official_source_reference_count | {summary.official_source_reference_count} |
| source_recheck_required_before_execution_count | {summary.source_recheck_required_before_execution_count} |
| source_recheck_completed_for_execution_count | {summary.source_recheck_completed_for_execution_count} |
| region_recheck_required_count | {summary.region_recheck_required_count} |
| retention_recheck_required_count | {summary.retention_recheck_required_count} |
| cost_confirmation_required_count | {summary.cost_confirmation_required_count} |
| raw_audio_public_artifact_count | {summary.raw_audio_public_artifact_count} |
| raw_transcript_public_artifact_count | {summary.raw_transcript_public_artifact_count} |
| raw_payload_public_artifact_count | {summary.raw_payload_public_artifact_count} |
| client_secret_exposure_count | {summary.client_secret_exposure_count} |

## Data Mart

| table | grain | visibility |
| --- | --- | --- |
| `fact_voice_azure_credential_preflight` | `preflight_id + provider_candidate_id` | public aggregate |
| `fact_voice_azure_credential_check` | `preflight_id + env_name` | public aggregate |
| `fact_voice_azure_source_check` | `preflight_id + source_check_type` | public aggregate |
| `fact_voice_managed_smoke_private_payload` | `run_id + provider_candidate_id + script_id` | private only |

## Claim Boundary

허용 claim:

- Azure credential preflight를 구현했다.

- Azure API call과 external audio transmission은 0회다.

- credential 값은 public artifact에 기록하지 않았다.

- 실제 Azure smoke는 credential 준비, source 재확인, 사용자 별도 승인 뒤에만 가능하다.

금지 claim:

- Azure STT/TTS 품질 검증 완료

- Azure managed provider smoke 실행 완료

- Azure 비용/정책 최신 확인 완료

- production voice service 준비 완료

- 외부 audio 전송 검증 완료
"""


def build_report_markdown(report: AzureCredentialPreflightReport) -> str:
    summary = report.summary
    quality = report.output_quality
    credential_rows = "\n".join(
        _format_credential_row(row) for row in report.credential_checks
    )
    source_rows = "\n".join(_format_source_report_row(row) for row in report.source_checks)
    qualitative_rows = "\n".join(
        f"| {key} | {value} |" for key, value in report.qualitative_assessment.items()
    )
    failures = collect_azure_credential_preflight_failures(report)
    return f"""# Voice STT/TTS Azure Credential Preflight Report

`{WORK_ID}`는 {"PASS" if not failures else "FAIL"}다.

이번 report는 Azure AI Speech 실제 smoke 결과가 아니라 credential/source preflight 결과다.

## Execution Info

| field | value |
| --- | --- |
| report_version | `{report.report_version}` |
| preflight_id | `{report.preflight_id}` |
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
| planned_script_count | {summary.planned_script_count} |
| planned_stt_call_count | {summary.planned_stt_call_count} |
| planned_tts_call_count | {summary.planned_tts_call_count} |
| call_cap_enforced | {str(summary.call_cap_enforced).lower()} |
| azure_credential_ready | {str(summary.azure_credential_ready).lower()} |
| credential_env_var_name_count | {summary.credential_env_var_name_count} |
| credential_present_count | {summary.credential_present_count} |
| credential_missing_count | {summary.credential_missing_count} |
| credential_value_public_exposure_count | {summary.credential_value_public_exposure_count} |
| managed_provider_execution_requested_count | {summary.managed_provider_execution_requested_count} |
| managed_provider_api_call_count | {summary.managed_provider_api_call_count} |
| external_audio_transmission_count | {summary.external_audio_transmission_count} |
| live_stt_call_count | {summary.live_stt_call_count} |
| live_tts_call_count | {summary.live_tts_call_count} |
| live_solar_call_count | {summary.live_solar_call_count} |
| official_source_reference_count | {summary.official_source_reference_count} |
| source_recheck_required_before_execution_count | {summary.source_recheck_required_before_execution_count} |
| source_recheck_completed_for_execution_count | {summary.source_recheck_completed_for_execution_count} |
| region_recheck_required_count | {summary.region_recheck_required_count} |
| retention_recheck_required_count | {summary.retention_recheck_required_count} |
| cost_confirmation_required_count | {summary.cost_confirmation_required_count} |
| raw_audio_public_artifact_count | {summary.raw_audio_public_artifact_count} |
| raw_transcript_public_artifact_count | {summary.raw_transcript_public_artifact_count} |
| raw_payload_public_artifact_count | {summary.raw_payload_public_artifact_count} |
| client_secret_exposure_count | {summary.client_secret_exposure_count} |
| public_private_path_leakage_count | {summary.public_private_path_leakage_count} |
| public_secret_like_leakage_count | {summary.public_secret_like_leakage_count} |
| public_raw_payload_leakage_count | {summary.public_raw_payload_leakage_count} |
| preflight_decision | `{summary.preflight_decision}` |

## Credential Check

| env name | status | value exposure |
| --- | --- | ---: |
{credential_rows}

## Source Check

| source_check_type | recheck_required | recheck_completed |
| --- | --- | --- |
{source_rows}

## Public Safety

| metric | value |
| --- | ---: |
| result_row_count | {quality.result_row_count} |
| public_raw_text_leakage_count | {quality.public_raw_text_leakage_count} |
| private_path_leakage_count | {quality.private_path_leakage_count} |
| secret_like_leakage_count | {quality.secret_like_leakage_count} |
| forbidden_result_field_count | {quality.forbidden_result_field_count} |

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
| source/region/retention/cost 재확인 필요 상태 기록 | PASS |
"""


def build_qualitative_assessment(report: AzureCredentialPreflightReport) -> dict[str, str]:
    if report.summary.azure_credential_ready:
        operations_boundary = (
            "credential 존재 여부는 충족됐지만 source, region, retention, cost 재확인과 "
            "사용자 별도 승인 전에는 실제 smoke를 실행하지 않는다."
        )
    else:
        operations_boundary = (
            "Azure credential이 준비되지 않아 실제 managed smoke는 보류 상태다."
        )
    return {
        "security_boundary": "credential 값, raw audio, raw transcript, provider payload를 public artifact에 기록하지 않는다.",
        "eval_boundary": "이번 결과는 credential/source preflight이며 Azure STT/TTS 품질 비교가 아니다.",
        "data_mart_boundary": "preflight, credential check, source check, private payload grain을 분리했다.",
        "operations_boundary": operations_boundary,
    }


def build_preflight_id(
    *,
    credential_checks: tuple[AzureCredentialCheckRow, ...],
    source_checks: tuple[AzureSourceCheckRow, ...],
    summary: AzureCredentialPreflightSummary,
) -> str:
    return "azure-credential-preflight-" + _stable_digest(
        {
            "credential_checks": [
                row.model_dump(mode="json") for row in credential_checks
            ],
            "source_checks": [row.model_dump(mode="json") for row in source_checks],
            "summary": summary.model_dump(mode="json"),
        },
    )


def _read_env_file_values(env_path: Path) -> dict[str, str]:
    resolved_path = project_path(env_path)
    if not resolved_path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in resolved_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key in AZURE_CREDENTIAL_ENV_NAMES and value:
            values[key] = value
    return values


def _format_credential_row(row: AzureCredentialCheckRow) -> str:
    return (
        f"| `{row.env_name}` | `{row.credential_status}` | "
        f"{row.value_public_exposure_count} |"
    )


def _format_source_doc_row(row: AzureSourceCheckRow) -> str:
    return (
        f"| `{row.source_check_type}` | official Azure source in readiness doc | "
        "recheck before execution |"
    )


def _format_source_report_row(row: AzureSourceCheckRow) -> str:
    return (
        f"| `{row.source_check_type}` | "
        f"{str(row.recheck_required_before_execution).lower()} | "
        f"{str(row.recheck_completed_for_execution).lower()} |"
    )


def _stable_digest(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"),
    ).hexdigest()[:16]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Azure STT/TTS credential preflight without API calls.",
    )
    parser.add_argument("--env", type=Path, default=DEFAULT_ENV_PATH)
    parser.add_argument("--scripts", type=Path, default=DEFAULT_SCRIPTS_PATH)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--result-rows", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    parser.add_argument(
        "--execute-managed-provider",
        action="store_true",
        help="Blocked in this preflight gate; actual execution needs separate approval.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_voice_stt_tts_azure_credential_preflight(
        env_path=args.env,
        scripts_path=args.scripts,
        doc_path=args.doc,
        report_path=args.report,
        result_rows_path=args.result_rows,
        execute_managed_provider=args.execute_managed_provider,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
