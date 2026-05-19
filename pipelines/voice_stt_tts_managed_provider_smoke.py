from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter
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
from pipelines.voice_stt_tts_provider_bench_readiness import (
    DEFAULT_SCRIPTS_PATH,
    VoiceBenchmarkScript,
    load_voice_benchmark_scripts,
)


REPORT_VERSION = "voice-stt-tts-managed-provider-smoke-execution-harness-report/v1"
WORK_ID = "HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-EXECUTION-HARNESS-001"
DEPENDS_ON = "HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-APPROVAL-001"
NEXT_WORK_ID = "HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-001"
DEFAULT_DOC_PATH = (
    Path("docs") / "VOICE_STT_TTS_MANAGED_PROVIDER_SMOKE_EXECUTION_HARNESS.md"
)
DEFAULT_REPORT_PATH = (
    Path("evals")
    / "reports"
    / "voice_stt_tts_managed_provider_smoke_execution_harness_report.md"
)
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "voice_stt_tts_managed_provider_smoke_execution_harness_rows.jsonl"
)
DEFAULT_SCRIPT_LIMIT = 3
EXPECTED_PROVIDER_COUNT = 3
MAX_STT_CALLS_PER_PROVIDER = 3
MAX_TTS_CALLS_PER_PROVIDER = 3
MANAGED_PROVIDER_API_CALL_COUNT = 0
EXTERNAL_AUDIO_TRANSMISSION_COUNT = 0
LIVE_STT_CALL_COUNT = 0
LIVE_TTS_CALL_COUNT = 0
LIVE_SOLAR_CALL_COUNT = 0
RAW_AUDIO_PUBLIC_ARTIFACT_COUNT = 0
RAW_TRANSCRIPT_PUBLIC_ARTIFACT_COUNT = 0
RAW_PAYLOAD_PUBLIC_ARTIFACT_COUNT = 0
CLIENT_SECRET_EXPOSURE_COUNT = 0

ProviderModality = Literal["stt", "stt_tts"]
SourceType = Literal["pricing", "privacy", "data_usage"]
HarnessDecision = Literal[
    "ready_for_separate_managed_smoke_execution_approval",
    "blocked_by_harness_gate",
]


class ManagedSmokeModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ManagedProviderPlan(ManagedSmokeModel):
    provider_candidate_id: str = Field(min_length=1)
    provider_family: str = Field(min_length=1)
    modality: ProviderModality
    planned_max_stt_calls: int = Field(ge=0, le=MAX_STT_CALLS_PER_PROVIDER)
    planned_max_tts_calls: int = Field(ge=0, le=MAX_TTS_CALLS_PER_PROVIDER)
    credential_env_names: tuple[str, ...]
    source_recheck_required: bool
    region_recheck_required: bool
    retention_recheck_required: bool
    external_audio_transmission_if_executed: bool


class ManagedProviderSource(ManagedSmokeModel):
    provider_candidate_id: str = Field(min_length=1)
    source_type: SourceType
    url: str = Field(min_length=1)
    recheck_required_before_execution: bool


class ManagedCredentialPreflight(ManagedSmokeModel):
    provider_candidate_id: str = Field(min_length=1)
    credential_env_var_count: int = Field(ge=0)
    credential_present_count: int = Field(ge=0)
    credential_value_public_exposure_count: int = Field(ge=0)
    credential_preflight_status: Literal["dry_run_not_required", "ready_if_user_approves"]


class ManagedSmokePlanRow(ManagedSmokeModel):
    provider_candidate_id: str = Field(min_length=1)
    script_id: str = Field(min_length=1)
    query_type: str = Field(min_length=1)
    planned_stt_call_count: int = Field(ge=0, le=1)
    planned_tts_call_count: int = Field(ge=0, le=1)
    actual_stt_call_count: int = Field(ge=0)
    actual_tts_call_count: int = Field(ge=0)
    managed_provider_api_call_count: int = Field(ge=0)
    external_audio_transmission_count: int = Field(ge=0)
    reference_text_hash: str = Field(min_length=8)
    row_status: Literal["dry_run_planned"]


class ManagedProviderSmokeSummary(ManagedSmokeModel):
    dry_run_default: bool
    managed_provider_execution_requested_count: int = Field(ge=0)
    provider_candidate_count: int = Field(ge=0)
    selected_script_count: int = Field(ge=0)
    planned_max_stt_calls_per_provider: int = Field(ge=0)
    planned_max_tts_calls_per_provider: int = Field(ge=0)
    planned_stt_call_count_total: int = Field(ge=0)
    planned_tts_call_count_total: int = Field(ge=0)
    planned_external_audio_transmission_if_executed_count: int = Field(ge=0)
    call_cap_enforced: bool
    managed_provider_api_call_count: int = Field(ge=0)
    external_audio_transmission_count: int = Field(ge=0)
    live_stt_call_count: int = Field(ge=0)
    live_tts_call_count: int = Field(ge=0)
    live_solar_call_count: int = Field(ge=0)
    official_source_count: int = Field(ge=0)
    pricing_source_recheck_required_count: int = Field(ge=0)
    privacy_source_recheck_required_count: int = Field(ge=0)
    region_recheck_required_count: int = Field(ge=0)
    retention_recheck_required_count: int = Field(ge=0)
    source_recheck_completed_count: int = Field(ge=0)
    credential_env_var_name_count: int = Field(ge=0)
    credential_present_count: int = Field(ge=0)
    credential_value_public_exposure_count: int = Field(ge=0)
    raw_audio_public_artifact_count: int = Field(ge=0)
    raw_transcript_public_artifact_count: int = Field(ge=0)
    raw_payload_public_artifact_count: int = Field(ge=0)
    client_secret_exposure_count: int = Field(ge=0)
    public_private_path_leakage_count: int = Field(ge=0)
    public_secret_like_leakage_count: int = Field(ge=0)
    public_raw_payload_leakage_count: int = Field(ge=0)
    harness_decision: HarnessDecision


class ManagedProviderSmokeHarnessReport(ManagedSmokeModel):
    report_version: str = REPORT_VERSION
    harness_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    work_id: str = WORK_ID
    depends_on: str = DEPENDS_ON
    next_work_id: str = NEXT_WORK_ID
    scripts_path: str = Field(min_length=1)
    result_path: str = Field(min_length=1)
    source_fingerprint: str = Field(min_length=8)
    provider_plans: tuple[ManagedProviderPlan, ...]
    official_sources: tuple[ManagedProviderSource, ...]
    credential_preflight: tuple[ManagedCredentialPreflight, ...]
    planned_rows: tuple[ManagedSmokePlanRow, ...]
    summary: ManagedProviderSmokeSummary
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


MANAGED_PROVIDER_PLANS = (
    ManagedProviderPlan(
        provider_candidate_id="managed_google_cloud_speech_to_text",
        provider_family="google_cloud",
        modality="stt",
        planned_max_stt_calls=3,
        planned_max_tts_calls=0,
        credential_env_names=("GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_CLOUD_PROJECT"),
        source_recheck_required=True,
        region_recheck_required=True,
        retention_recheck_required=True,
        external_audio_transmission_if_executed=True,
    ),
    ManagedProviderPlan(
        provider_candidate_id="managed_azure_ai_speech",
        provider_family="azure_ai_speech",
        modality="stt_tts",
        planned_max_stt_calls=3,
        planned_max_tts_calls=3,
        credential_env_names=("AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION"),
        source_recheck_required=True,
        region_recheck_required=True,
        retention_recheck_required=True,
        external_audio_transmission_if_executed=True,
    ),
    ManagedProviderPlan(
        provider_candidate_id="managed_aws_transcribe_polly",
        provider_family="aws_transcribe_polly",
        modality="stt_tts",
        planned_max_stt_calls=3,
        planned_max_tts_calls=3,
        credential_env_names=("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION"),
        source_recheck_required=True,
        region_recheck_required=True,
        retention_recheck_required=True,
        external_audio_transmission_if_executed=True,
    ),
)

MANAGED_PROVIDER_SOURCES = (
    ManagedProviderSource(
        provider_candidate_id="managed_google_cloud_speech_to_text",
        source_type="pricing",
        url="https://cloud.google.com/speech-to-text/pricing",
        recheck_required_before_execution=True,
    ),
    ManagedProviderSource(
        provider_candidate_id="managed_google_cloud_speech_to_text",
        source_type="privacy",
        url="https://docs.cloud.google.com/speech-to-text/docs/v1/data-logging",
        recheck_required_before_execution=True,
    ),
    ManagedProviderSource(
        provider_candidate_id="managed_google_cloud_speech_to_text",
        source_type="data_usage",
        url="https://docs.cloud.google.com/speech-to-text/docs/v1/data-usage-faq",
        recheck_required_before_execution=True,
    ),
    ManagedProviderSource(
        provider_candidate_id="managed_azure_ai_speech",
        source_type="pricing",
        url="https://azure.microsoft.com/en-us/pricing/details/speech/",
        recheck_required_before_execution=True,
    ),
    ManagedProviderSource(
        provider_candidate_id="managed_azure_ai_speech",
        source_type="privacy",
        url=(
            "https://learn.microsoft.com/en-us/azure/foundry/responsible-ai/"
            "speech-service/speech-to-text/data-privacy-security"
        ),
        recheck_required_before_execution=True,
    ),
    ManagedProviderSource(
        provider_candidate_id="managed_aws_transcribe_polly",
        source_type="pricing",
        url="https://aws.amazon.com/transcribe/pricing/",
        recheck_required_before_execution=True,
    ),
    ManagedProviderSource(
        provider_candidate_id="managed_aws_transcribe_polly",
        source_type="privacy",
        url="https://docs.aws.amazon.com/transcribe/latest/dg/data-protection.html",
        recheck_required_before_execution=True,
    ),
    ManagedProviderSource(
        provider_candidate_id="managed_aws_transcribe_polly",
        source_type="pricing",
        url="https://aws.amazon.com/polly/pricing/",
        recheck_required_before_execution=True,
    ),
    ManagedProviderSource(
        provider_candidate_id="managed_aws_transcribe_polly",
        source_type="privacy",
        url="https://docs.aws.amazon.com/polly/latest/dg/data-protection.html",
        recheck_required_before_execution=True,
    ),
)


def run_voice_stt_tts_managed_provider_smoke_harness(
    *,
    scripts_path: Path = DEFAULT_SCRIPTS_PATH,
    doc_path: Path = DEFAULT_DOC_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
    script_limit: int = DEFAULT_SCRIPT_LIMIT,
    execute_managed_provider: bool = False,
) -> ManagedProviderSmokeHarnessReport:
    if execute_managed_provider:
        raise ValueError(
            "managed provider execution is blocked in this harness gate; "
            "run the separate managed smoke execution work order after approval",
        )

    scripts = select_managed_smoke_scripts(
        load_voice_benchmark_scripts(project_path(scripts_path)),
        limit=script_limit,
    )
    credential_rows = build_credential_preflight(MANAGED_PROVIDER_PLANS)
    planned_rows = build_plan_rows(MANAGED_PROVIDER_PLANS, scripts)
    summary = build_summary(
        scripts=scripts,
        provider_plans=MANAGED_PROVIDER_PLANS,
        sources=MANAGED_PROVIDER_SOURCES,
        credential_rows=credential_rows,
        planned_rows=planned_rows,
        execute_managed_provider=execute_managed_provider,
    )
    harness_id = build_harness_id(
        provider_plans=MANAGED_PROVIDER_PLANS,
        sources=MANAGED_PROVIDER_SOURCES,
        planned_rows=planned_rows,
        summary=summary,
    )
    public_rows = build_public_rows(
        harness_id=harness_id,
        summary=summary,
        provider_plans=MANAGED_PROVIDER_PLANS,
        credential_rows=credential_rows,
        planned_rows=planned_rows,
    )
    provisional_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=harness_id,
        result_rows=public_rows,
        report_text="",
    )
    provisional = build_report(
        harness_id=harness_id,
        scripts_path=scripts_path,
        result_rows_path=result_rows_path,
        provider_plans=MANAGED_PROVIDER_PLANS,
        sources=MANAGED_PROVIDER_SOURCES,
        credential_rows=credential_rows,
        planned_rows=planned_rows,
        summary=summary,
        output_quality=provisional_quality,
    )
    doc_text = build_doc_markdown(provisional)
    report_text = build_report_markdown(provisional)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=harness_id,
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
            "harness_decision": build_harness_decision(
                summary=summary,
                output_quality=output_quality,
            ),
        },
    )
    report = build_report(
        harness_id=harness_id,
        scripts_path=scripts_path,
        result_rows_path=result_rows_path,
        provider_plans=MANAGED_PROVIDER_PLANS,
        sources=MANAGED_PROVIDER_SOURCES,
        credential_rows=credential_rows,
        planned_rows=planned_rows,
        summary=summary,
        output_quality=output_quality,
    )
    failures = collect_managed_provider_smoke_harness_failures(report)
    if failures:
        raise ValueError(f"managed provider smoke harness gate failed: {failures}")

    write_public_retrieval_result_rows(
        path=project_path(result_rows_path),
        rows=build_public_rows(
            harness_id=harness_id,
            summary=summary,
            provider_plans=MANAGED_PROVIDER_PLANS,
            credential_rows=credential_rows,
            planned_rows=planned_rows,
        ),
    )
    resolved_doc_path = project_path(doc_path)
    resolved_report_path = project_path(report_path)
    resolved_doc_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_report_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_doc_path.write_text(build_doc_markdown(report), encoding="utf-8")
    resolved_report_path.write_text(build_report_markdown(report), encoding="utf-8")
    print(
        "voice_stt_tts_managed_provider_smoke_harness "
        "status=PASS "
        f"providers={report.summary.provider_candidate_count} "
        f"scripts={report.summary.selected_script_count} "
        f"managed_provider_api_calls={report.summary.managed_provider_api_call_count} "
        f"external_audio_transmissions={report.summary.external_audio_transmission_count}",
    )
    return report


def select_managed_smoke_scripts(
    scripts: tuple[VoiceBenchmarkScript, ...],
    *,
    limit: int,
) -> tuple[VoiceBenchmarkScript, ...]:
    eligible = [
        script
        for script in scripts
        if script.public_allowed
        and script.expected_behavior == "answer_with_citation"
        and not script.raw_audio_saved
    ]
    return tuple(eligible[:limit])


def build_credential_preflight(
    provider_plans: tuple[ManagedProviderPlan, ...],
) -> tuple[ManagedCredentialPreflight, ...]:
    rows: list[ManagedCredentialPreflight] = []
    for plan in provider_plans:
        present_count = sum(1 for name in plan.credential_env_names if os.environ.get(name))
        rows.append(
            ManagedCredentialPreflight(
                provider_candidate_id=plan.provider_candidate_id,
                credential_env_var_count=len(plan.credential_env_names),
                credential_present_count=present_count,
                credential_value_public_exposure_count=0,
                credential_preflight_status=(
                    "ready_if_user_approves"
                    if present_count == len(plan.credential_env_names)
                    else "dry_run_not_required"
                ),
            ),
        )
    return tuple(rows)


def build_plan_rows(
    provider_plans: tuple[ManagedProviderPlan, ...],
    scripts: tuple[VoiceBenchmarkScript, ...],
) -> tuple[ManagedSmokePlanRow, ...]:
    rows: list[ManagedSmokePlanRow] = []
    for plan in provider_plans:
        for script in scripts:
            rows.append(
                ManagedSmokePlanRow(
                    provider_candidate_id=plan.provider_candidate_id,
                    script_id=script.script_id,
                    query_type=script.query_type,
                    planned_stt_call_count=int(plan.planned_max_stt_calls > 0),
                    planned_tts_call_count=int(plan.planned_max_tts_calls > 0),
                    actual_stt_call_count=LIVE_STT_CALL_COUNT,
                    actual_tts_call_count=LIVE_TTS_CALL_COUNT,
                    managed_provider_api_call_count=MANAGED_PROVIDER_API_CALL_COUNT,
                    external_audio_transmission_count=EXTERNAL_AUDIO_TRANSMISSION_COUNT,
                    reference_text_hash=_stable_digest(
                        {
                            "script_id": script.script_id,
                            "script_text": script.script_text,
                        },
                    ),
                    row_status="dry_run_planned",
                ),
            )
    return tuple(rows)


def build_summary(
    *,
    scripts: tuple[VoiceBenchmarkScript, ...],
    provider_plans: tuple[ManagedProviderPlan, ...],
    sources: tuple[ManagedProviderSource, ...],
    credential_rows: tuple[ManagedCredentialPreflight, ...],
    planned_rows: tuple[ManagedSmokePlanRow, ...],
    execute_managed_provider: bool,
) -> ManagedProviderSmokeSummary:
    source_type_counts = Counter(source.source_type for source in sources)
    planned_stt_by_provider = {
        plan.provider_candidate_id: sum(
            row.planned_stt_call_count
            for row in planned_rows
            if row.provider_candidate_id == plan.provider_candidate_id
        )
        for plan in provider_plans
    }
    planned_tts_by_provider = {
        plan.provider_candidate_id: sum(
            row.planned_tts_call_count
            for row in planned_rows
            if row.provider_candidate_id == plan.provider_candidate_id
        )
        for plan in provider_plans
    }
    call_cap_enforced = (
        all(count <= MAX_STT_CALLS_PER_PROVIDER for count in planned_stt_by_provider.values())
        and all(count <= MAX_TTS_CALLS_PER_PROVIDER for count in planned_tts_by_provider.values())
        and all(plan.planned_max_stt_calls <= MAX_STT_CALLS_PER_PROVIDER for plan in provider_plans)
        and all(plan.planned_max_tts_calls <= MAX_TTS_CALLS_PER_PROVIDER for plan in provider_plans)
    )
    credential_env_var_name_count = sum(row.credential_env_var_count for row in credential_rows)
    credential_present_count = sum(row.credential_present_count for row in credential_rows)
    credential_value_public_exposure_count = sum(
        row.credential_value_public_exposure_count for row in credential_rows
    )
    summary = ManagedProviderSmokeSummary(
        dry_run_default=True,
        managed_provider_execution_requested_count=int(execute_managed_provider),
        provider_candidate_count=len(provider_plans),
        selected_script_count=len(scripts),
        planned_max_stt_calls_per_provider=MAX_STT_CALLS_PER_PROVIDER,
        planned_max_tts_calls_per_provider=MAX_TTS_CALLS_PER_PROVIDER,
        planned_stt_call_count_total=sum(planned_stt_by_provider.values()),
        planned_tts_call_count_total=sum(planned_tts_by_provider.values()),
        planned_external_audio_transmission_if_executed_count=sum(
            planned_stt_by_provider.values(),
        ),
        call_cap_enforced=call_cap_enforced,
        managed_provider_api_call_count=MANAGED_PROVIDER_API_CALL_COUNT,
        external_audio_transmission_count=EXTERNAL_AUDIO_TRANSMISSION_COUNT,
        live_stt_call_count=LIVE_STT_CALL_COUNT,
        live_tts_call_count=LIVE_TTS_CALL_COUNT,
        live_solar_call_count=LIVE_SOLAR_CALL_COUNT,
        official_source_count=len(sources),
        pricing_source_recheck_required_count=source_type_counts["pricing"],
        privacy_source_recheck_required_count=(
            source_type_counts["privacy"] + source_type_counts["data_usage"]
        ),
        region_recheck_required_count=sum(1 for plan in provider_plans if plan.region_recheck_required),
        retention_recheck_required_count=sum(
            1 for plan in provider_plans if plan.retention_recheck_required
        ),
        source_recheck_completed_count=0,
        credential_env_var_name_count=credential_env_var_name_count,
        credential_present_count=credential_present_count,
        credential_value_public_exposure_count=credential_value_public_exposure_count,
        raw_audio_public_artifact_count=RAW_AUDIO_PUBLIC_ARTIFACT_COUNT,
        raw_transcript_public_artifact_count=RAW_TRANSCRIPT_PUBLIC_ARTIFACT_COUNT,
        raw_payload_public_artifact_count=RAW_PAYLOAD_PUBLIC_ARTIFACT_COUNT,
        client_secret_exposure_count=CLIENT_SECRET_EXPOSURE_COUNT,
        public_private_path_leakage_count=0,
        public_secret_like_leakage_count=0,
        public_raw_payload_leakage_count=0,
        harness_decision="blocked_by_harness_gate",
    )
    return summary.model_copy(
        update={
            "harness_decision": build_harness_decision(
                summary=summary,
                output_quality=None,
            ),
        },
    )


def build_harness_decision(
    *,
    summary: ManagedProviderSmokeSummary,
    output_quality: PublicRetrievalArtifactQuality | None,
) -> HarnessDecision:
    public_safety_passed = output_quality is None or not collect_public_retrieval_artifact_failures(
        output_quality,
    )
    if (
        summary.dry_run_default
        and not summary.managed_provider_execution_requested_count
        and summary.provider_candidate_count >= EXPECTED_PROVIDER_COUNT
        and summary.selected_script_count == DEFAULT_SCRIPT_LIMIT
        and summary.call_cap_enforced
        and summary.managed_provider_api_call_count == 0
        and summary.external_audio_transmission_count == 0
        and summary.credential_value_public_exposure_count == 0
        and summary.raw_audio_public_artifact_count == 0
        and summary.raw_transcript_public_artifact_count == 0
        and summary.raw_payload_public_artifact_count == 0
        and public_safety_passed
    ):
        return "ready_for_separate_managed_smoke_execution_approval"
    return "blocked_by_harness_gate"


def build_report(
    *,
    harness_id: str,
    scripts_path: Path,
    result_rows_path: Path,
    provider_plans: tuple[ManagedProviderPlan, ...],
    sources: tuple[ManagedProviderSource, ...],
    credential_rows: tuple[ManagedCredentialPreflight, ...],
    planned_rows: tuple[ManagedSmokePlanRow, ...],
    summary: ManagedProviderSmokeSummary,
    output_quality: PublicRetrievalArtifactQuality,
) -> ManagedProviderSmokeHarnessReport:
    report = ManagedProviderSmokeHarnessReport(
        harness_id=harness_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        scripts_path=public_path_alias(scripts_path),
        result_path=public_path_alias(result_rows_path),
        source_fingerprint=_stable_digest(
            {
                "provider_plans": [row.model_dump(mode="json") for row in provider_plans],
                "sources": [row.model_dump(mode="json") for row in sources],
                "script_ids": [row.script_id for row in planned_rows],
            },
        ),
        provider_plans=provider_plans,
        official_sources=sources,
        credential_preflight=credential_rows,
        planned_rows=planned_rows,
        summary=summary,
        output_quality=output_quality,
        qualitative_assessment={},
    )
    return report.model_copy(
        update={"qualitative_assessment": build_qualitative_assessment(report)},
    )


def build_public_rows(
    *,
    harness_id: str,
    summary: ManagedProviderSmokeSummary,
    provider_plans: tuple[ManagedProviderPlan, ...],
    credential_rows: tuple[ManagedCredentialPreflight, ...],
    planned_rows: tuple[ManagedSmokePlanRow, ...],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "row_type": "summary",
            "harness_id": harness_id,
            "provider_candidate_count": summary.provider_candidate_count,
            "selected_script_count": summary.selected_script_count,
            "dry_run_default": summary.dry_run_default,
            "call_cap_enforced": summary.call_cap_enforced,
            "managed_provider_api_call_count": summary.managed_provider_api_call_count,
            "external_audio_transmission_count": summary.external_audio_transmission_count,
            "raw_audio_public_artifact_count": summary.raw_audio_public_artifact_count,
            "raw_transcript_public_artifact_count": (
                summary.raw_transcript_public_artifact_count
            ),
            "raw_payload_public_artifact_count": summary.raw_payload_public_artifact_count,
            "harness_decision": summary.harness_decision,
        },
    ]
    rows.extend(
        {
            "row_type": "provider_plan",
            "harness_id": harness_id,
            "provider_candidate_id": plan.provider_candidate_id,
            "provider_family": plan.provider_family,
            "modality": plan.modality,
            "planned_max_stt_calls": plan.planned_max_stt_calls,
            "planned_max_tts_calls": plan.planned_max_tts_calls,
            "credential_env_var_count": len(plan.credential_env_names),
            "source_recheck_required": plan.source_recheck_required,
            "region_recheck_required": plan.region_recheck_required,
            "retention_recheck_required": plan.retention_recheck_required,
        }
        for plan in provider_plans
    )
    rows.extend(
        {
            "row_type": "credential_preflight",
            "harness_id": harness_id,
            "provider_candidate_id": row.provider_candidate_id,
            "credential_env_var_count": row.credential_env_var_count,
            "credential_present_count": row.credential_present_count,
            "credential_value_public_exposure_count": (
                row.credential_value_public_exposure_count
            ),
            "credential_preflight_status": row.credential_preflight_status,
        }
        for row in credential_rows
    )
    rows.extend(
        {
            "row_type": "planned_script",
            "harness_id": harness_id,
            "provider_candidate_id": row.provider_candidate_id,
            "script_id": row.script_id,
            "query_type": row.query_type,
            "planned_stt_call_count": row.planned_stt_call_count,
            "planned_tts_call_count": row.planned_tts_call_count,
            "actual_stt_call_count": row.actual_stt_call_count,
            "actual_tts_call_count": row.actual_tts_call_count,
            "managed_provider_api_call_count": row.managed_provider_api_call_count,
            "external_audio_transmission_count": row.external_audio_transmission_count,
            "reference_text_hash": row.reference_text_hash,
            "row_status": row.row_status,
        }
        for row in planned_rows
    )
    return rows


def collect_managed_provider_smoke_harness_failures(
    report: ManagedProviderSmokeHarnessReport,
) -> list[str]:
    failures = collect_public_retrieval_artifact_failures(report.output_quality)
    summary = report.summary
    if summary.harness_decision == "blocked_by_harness_gate":
        failures.append("harness_decision_blocked")
    if not summary.dry_run_default:
        failures.append("dry_run_default_disabled")
    if summary.managed_provider_execution_requested_count:
        failures.append("managed_provider_execution_requested")
    if summary.provider_candidate_count < EXPECTED_PROVIDER_COUNT:
        failures.append("managed_provider_candidate_count_below_min")
    if summary.selected_script_count != DEFAULT_SCRIPT_LIMIT:
        failures.append("selected_script_count_mismatch")
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


def build_doc_markdown(report: ManagedProviderSmokeHarnessReport) -> str:
    summary = report.summary
    provider_rows = "\n".join(_format_provider_doc_row(row) for row in report.provider_plans)
    credential_rows = "\n".join(
        _format_credential_doc_row(row) for row in report.credential_preflight
    )
    source_rows = "\n".join(_format_source_doc_row(row) for row in report.official_sources)
    return f"""# Voice STT/TTS Managed Provider Smoke Execution Harness

`{WORK_ID}`는 managed provider smoke를 실행하기 위한 harness를 만든다.

결론: 이 단계의 기본값은 dry-run이며 실제 provider API 호출은 0회다.

## Scope

| field | value |
| --- | --- |
| work_id | `{WORK_ID}` |
| depends_on | `{DEPENDS_ON}` |
| next_work_id | `{NEXT_WORK_ID}` |
| dry_run_default | {str(summary.dry_run_default).lower()} |
| managed_provider_api_call_count | {summary.managed_provider_api_call_count} |
| external_audio_transmission_count | {summary.external_audio_transmission_count} |
| harness_decision | `{summary.harness_decision}` |

## Provider Config Schema

| provider_candidate_id | modality | STT cap | TTS cap | credential env names |
| --- | --- | ---: | ---: | --- |
{provider_rows}

## Credential Preflight

값은 기록하지 않고 존재 여부만 집계한다.

| provider_candidate_id | env var count | present count | value exposure |
| --- | ---: | ---: | ---: |
{credential_rows}

## Source Recheck

| provider_candidate_id | source_type | source | recheck |
| --- | --- | --- | --- |
{source_rows}

## Quantitative Gate

| metric | value |
| --- | ---: |
| provider_candidate_count | {summary.provider_candidate_count} |
| selected_script_count | {summary.selected_script_count} |
| planned_max_stt_calls_per_provider | {summary.planned_max_stt_calls_per_provider} |
| planned_max_tts_calls_per_provider | {summary.planned_max_tts_calls_per_provider} |
| planned_stt_call_count_total | {summary.planned_stt_call_count_total} |
| planned_tts_call_count_total | {summary.planned_tts_call_count_total} |
| planned_external_audio_transmission_if_executed_count | {summary.planned_external_audio_transmission_if_executed_count} |
| call_cap_enforced | {str(summary.call_cap_enforced).lower()} |
| managed_provider_api_call_count | {summary.managed_provider_api_call_count} |
| external_audio_transmission_count | {summary.external_audio_transmission_count} |
| raw_audio_public_artifact_count | {summary.raw_audio_public_artifact_count} |
| raw_transcript_public_artifact_count | {summary.raw_transcript_public_artifact_count} |
| raw_payload_public_artifact_count | {summary.raw_payload_public_artifact_count} |
| client_secret_exposure_count | {summary.client_secret_exposure_count} |

## Data Mart

| table | grain | visibility |
| --- | --- | --- |
| `fact_voice_managed_smoke_harness_run` | `harness_id + provider_candidate_id` | public aggregate |
| `fact_voice_managed_smoke_private_payload` | `run_id + provider_candidate_id + script_id` | private only |
| `fact_voice_managed_smoke_public_summary` | `harness_id + provider_candidate_id + metric_family` | public aggregate |

## Claim Boundary

허용 claim:

- managed provider smoke execution harness를 dry-run으로 구현했다.
- managed provider API call과 external audio transmission은 0회다.
- provider별 call cap을 코드 레벨에서 강제한다.

금지 claim:

- provider 최종 선택 완료
- STT/TTS 품질 검증 완료
- 음성 관광 앱 완성
- managed provider benchmark 성능 개선 입증
- production voice service 준비 완료
"""


def build_report_markdown(report: ManagedProviderSmokeHarnessReport) -> str:
    summary = report.summary
    quality = report.output_quality
    provider_rows = "\n".join(_format_provider_report_row(row) for row in report.provider_plans)
    planned_rows = "\n".join(_format_planned_report_row(row) for row in report.planned_rows)
    qualitative_rows = "\n".join(
        f"| {key} | {value} |" for key, value in report.qualitative_assessment.items()
    )
    failures = collect_managed_provider_smoke_harness_failures(report)
    return f"""# Voice STT/TTS Managed Provider Smoke Execution Harness Report

`{WORK_ID}`는 {"PASS" if not failures else "FAIL"}다.

이번 report는 managed provider 실제 smoke 결과가 아니라 dry-run execution harness 검증 결과다.

## Execution Info

| field | value |
| --- | --- |
| report_version | `{report.report_version}` |
| harness_id | `{report.harness_id}` |
| work_id | `{report.work_id}` |
| depends_on | `{report.depends_on}` |
| next_work_id | `{report.next_work_id}` |
| generated_at_utc | `{report.generated_at_utc}` |
| scripts_path | `{report.scripts_path}` |
| result_path | `{report.result_path}` |
| source_fingerprint | `{report.source_fingerprint}` |

## Quantitative Evaluation

| metric | value |
| --- | --- |
| dry_run_default | {str(summary.dry_run_default).lower()} |
| managed_provider_execution_requested_count | {summary.managed_provider_execution_requested_count} |
| provider_candidate_count | {summary.provider_candidate_count} |
| selected_script_count | {summary.selected_script_count} |
| planned_max_stt_calls_per_provider | {summary.planned_max_stt_calls_per_provider} |
| planned_max_tts_calls_per_provider | {summary.planned_max_tts_calls_per_provider} |
| planned_stt_call_count_total | {summary.planned_stt_call_count_total} |
| planned_tts_call_count_total | {summary.planned_tts_call_count_total} |
| planned_external_audio_transmission_if_executed_count | {summary.planned_external_audio_transmission_if_executed_count} |
| call_cap_enforced | {str(summary.call_cap_enforced).lower()} |
| managed_provider_api_call_count | {summary.managed_provider_api_call_count} |
| external_audio_transmission_count | {summary.external_audio_transmission_count} |
| live_stt_call_count | {summary.live_stt_call_count} |
| live_tts_call_count | {summary.live_tts_call_count} |
| live_solar_call_count | {summary.live_solar_call_count} |
| official_source_count | {summary.official_source_count} |
| pricing_source_recheck_required_count | {summary.pricing_source_recheck_required_count} |
| privacy_source_recheck_required_count | {summary.privacy_source_recheck_required_count} |
| region_recheck_required_count | {summary.region_recheck_required_count} |
| retention_recheck_required_count | {summary.retention_recheck_required_count} |
| source_recheck_completed_count | {summary.source_recheck_completed_count} |
| credential_env_var_name_count | {summary.credential_env_var_name_count} |
| credential_present_count | {summary.credential_present_count} |
| credential_value_public_exposure_count | {summary.credential_value_public_exposure_count} |
| raw_audio_public_artifact_count | {summary.raw_audio_public_artifact_count} |
| raw_transcript_public_artifact_count | {summary.raw_transcript_public_artifact_count} |
| raw_payload_public_artifact_count | {summary.raw_payload_public_artifact_count} |
| client_secret_exposure_count | {summary.client_secret_exposure_count} |
| public_private_path_leakage_count | {summary.public_private_path_leakage_count} |
| public_secret_like_leakage_count | {summary.public_secret_like_leakage_count} |
| public_raw_payload_leakage_count | {summary.public_raw_payload_leakage_count} |
| harness_decision | `{summary.harness_decision}` |

## Provider Plan

| provider_candidate_id | modality | STT cap | TTS cap | source recheck |
| --- | --- | ---: | ---: | --- |
{provider_rows}

## Planned Rows

| provider_candidate_id | script_id | query_type | planned STT | planned TTS | actual API calls |
| --- | --- | --- | ---: | ---: | ---: |
{planned_rows}

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
| managed provider API call 0 유지 | PASS |
| external audio transmission 0 유지 | PASS |
| credential 값 미기록 | PASS |
| raw audio/transcript/payload public artifact 금지 | PASS |
| 다음 실제 smoke 실행 별도 승인 필요 | PASS |
"""


def build_qualitative_assessment(
    report: ManagedProviderSmokeHarnessReport,
) -> dict[str, str]:
    return {
        "security_boundary": "credential 값과 provider payload를 public artifact에 기록하지 않는다.",
        "eval_boundary": "이번 결과는 harness 검증이며 STT/TTS 품질 비교가 아니다.",
        "data_mart_boundary": "private payload grain과 public summary grain을 분리했다.",
        "operations_boundary": "기본 실행은 dry-run이고 실제 provider call은 별도 work order로 차단했다.",
    }


def build_harness_id(
    *,
    provider_plans: tuple[ManagedProviderPlan, ...],
    sources: tuple[ManagedProviderSource, ...],
    planned_rows: tuple[ManagedSmokePlanRow, ...],
    summary: ManagedProviderSmokeSummary,
) -> str:
    return "managed-smoke-harness-" + _stable_digest(
        {
            "provider_plans": [row.model_dump(mode="json") for row in provider_plans],
            "sources": [row.model_dump(mode="json") for row in sources],
            "planned_rows": [row.model_dump(mode="json") for row in planned_rows],
            "summary": summary.model_dump(mode="json"),
        },
    )


def _format_provider_doc_row(row: ManagedProviderPlan) -> str:
    env_names = ", ".join(f"`{name}`" for name in row.credential_env_names)
    return (
        f"| `{row.provider_candidate_id}` | {row.modality} | "
        f"{row.planned_max_stt_calls} | {row.planned_max_tts_calls} | {env_names} |"
    )


def _format_credential_doc_row(row: ManagedCredentialPreflight) -> str:
    return (
        f"| `{row.provider_candidate_id}` | {row.credential_env_var_count} | "
        f"{row.credential_present_count} | {row.credential_value_public_exposure_count} |"
    )


def _format_source_doc_row(row: ManagedProviderSource) -> str:
    source_alias = _stable_digest(
        {
            "provider_candidate_id": row.provider_candidate_id,
            "source_type": row.source_type,
            "url": row.url,
        },
    )
    return (
        f"| `{row.provider_candidate_id}` | {row.source_type} | "
        f"`official_source_{source_alias}` | "
        f"{str(row.recheck_required_before_execution).lower()} |"
    )


def _format_provider_report_row(row: ManagedProviderPlan) -> str:
    return (
        f"| `{row.provider_candidate_id}` | {row.modality} | "
        f"{row.planned_max_stt_calls} | {row.planned_max_tts_calls} | "
        f"{str(row.source_recheck_required).lower()} |"
    )


def _format_planned_report_row(row: ManagedSmokePlanRow) -> str:
    return (
        f"| `{row.provider_candidate_id}` | `{row.script_id}` | {row.query_type} | "
        f"{row.planned_stt_call_count} | {row.planned_tts_call_count} | "
        f"{row.managed_provider_api_call_count} |"
    )


def _stable_digest(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"),
    ).hexdigest()[:16]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build managed provider STT/TTS smoke dry-run execution harness.",
    )
    parser.add_argument("--scripts", type=Path, default=DEFAULT_SCRIPTS_PATH)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--result-rows", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    parser.add_argument("--script-limit", type=int, default=DEFAULT_SCRIPT_LIMIT)
    parser.add_argument(
        "--execute-managed-provider",
        action="store_true",
        help="Blocked in this harness gate; actual execution needs a separate approval.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_voice_stt_tts_managed_provider_smoke_harness(
        scripts_path=args.scripts,
        doc_path=args.doc,
        report_path=args.report,
        result_rows_path=args.result_rows,
        script_limit=args.script_limit,
        execute_managed_provider=args.execute_managed_provider,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
