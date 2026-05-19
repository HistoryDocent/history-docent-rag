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
from pipelines.voice_stt_tts_managed_provider_smoke import (
    CLIENT_SECRET_EXPOSURE_COUNT,
    DEFAULT_SCRIPT_LIMIT,
    EXPECTED_PROVIDER_COUNT,
    EXTERNAL_AUDIO_TRANSMISSION_COUNT,
    LIVE_SOLAR_CALL_COUNT,
    LIVE_STT_CALL_COUNT,
    LIVE_TTS_CALL_COUNT,
    MANAGED_PROVIDER_API_CALL_COUNT,
    MANAGED_PROVIDER_PLANS,
    MANAGED_PROVIDER_SOURCES,
    MAX_STT_CALLS_PER_PROVIDER,
    MAX_TTS_CALLS_PER_PROVIDER,
    RAW_AUDIO_PUBLIC_ARTIFACT_COUNT,
    RAW_PAYLOAD_PUBLIC_ARTIFACT_COUNT,
    RAW_TRANSCRIPT_PUBLIC_ARTIFACT_COUNT,
    ManagedProviderPlan,
    ManagedProviderSource,
    select_managed_smoke_scripts,
)
from pipelines.voice_stt_tts_provider_bench_readiness import (
    DEFAULT_SCRIPTS_PATH,
    VoiceBenchmarkScript,
    load_voice_benchmark_scripts,
)


REPORT_VERSION = "voice-stt-tts-managed-provider-smoke-preflight-report/v1"
WORK_ID = "HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-PREFLIGHT-001"
DEPENDS_ON = "HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-EXECUTION-HARNESS-001"
NEXT_WORK_ID = "HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-001"
DEFAULT_DOC_PATH = Path("docs") / "VOICE_STT_TTS_MANAGED_PROVIDER_SMOKE_PREFLIGHT.md"
DEFAULT_REPORT_PATH = (
    Path("evals")
    / "reports"
    / "voice_stt_tts_managed_provider_smoke_preflight_report.md"
)
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "voice_stt_tts_managed_provider_smoke_preflight_rows.jsonl"
)
MANAGED_PROVIDER_EXECUTION_REQUESTED_COUNT = 0
SOURCE_RECHECK_COMPLETED_COUNT = 0
CREDENTIAL_VALUE_PUBLIC_EXPOSURE_COUNT = 0
RECOMMENDATION_PRIORITY = (
    "managed_azure_ai_speech",
    "managed_google_cloud_speech_to_text",
    "managed_aws_transcribe_polly",
)

ProviderExecutionFeasibility = Literal[
    "blocked_missing_credentials",
    "eligible_after_source_region_retention_recheck_and_user_approval",
]
PreflightDecision = Literal[
    "ready_for_selected_provider_smoke_approval",
    "preflight_complete_missing_credentials",
    "blocked_by_preflight_gate",
]


class ManagedProviderSmokePreflightModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ManagedProviderPreflightRow(ManagedProviderSmokePreflightModel):
    provider_candidate_id: str = Field(min_length=1)
    provider_family: str = Field(min_length=1)
    modality: str = Field(min_length=1)
    planned_max_stt_calls: int = Field(ge=0, le=MAX_STT_CALLS_PER_PROVIDER)
    planned_max_tts_calls: int = Field(ge=0, le=MAX_TTS_CALLS_PER_PROVIDER)
    credential_env_var_count: int = Field(ge=0)
    credential_present_count: int = Field(ge=0)
    credential_missing_count: int = Field(ge=0)
    credential_ready: bool
    credential_value_public_exposure_count: int = Field(ge=0)
    source_recheck_required_count: int = Field(ge=0)
    pricing_source_recheck_required_count: int = Field(ge=0)
    privacy_source_recheck_required_count: int = Field(ge=0)
    source_recheck_completed_count: int = Field(ge=0)
    region_recheck_required: bool
    retention_recheck_required: bool
    cost_confirmation_required: bool
    external_audio_transmission_if_executed: bool
    provider_execution_feasibility: ProviderExecutionFeasibility


class RecommendedManagedProviderSmokeTarget(ManagedProviderSmokePreflightModel):
    provider_candidate_id: str = Field(min_length=1)
    selection_rank: int = Field(ge=1)
    planned_script_count: int = Field(ge=0)
    planned_stt_call_count: int = Field(ge=0)
    planned_tts_call_count: int = Field(ge=0)
    recommendation_reason: str = Field(min_length=1)


class ManagedProviderSmokePreflightSummary(ManagedProviderSmokePreflightModel):
    provider_candidate_count: int = Field(ge=0)
    selected_script_count: int = Field(ge=0)
    planned_max_stt_calls_per_provider: int = Field(ge=0)
    planned_max_tts_calls_per_provider: int = Field(ge=0)
    call_cap_enforced: bool
    executable_provider_candidate_count: int = Field(ge=0)
    recommended_first_provider_count: int = Field(ge=0, le=1)
    managed_provider_execution_requested_count: int = Field(ge=0)
    managed_provider_api_call_count: int = Field(ge=0)
    external_audio_transmission_count: int = Field(ge=0)
    live_stt_call_count: int = Field(ge=0)
    live_tts_call_count: int = Field(ge=0)
    live_solar_call_count: int = Field(ge=0)
    official_source_count: int = Field(ge=0)
    source_recheck_required_count: int = Field(ge=0)
    pricing_source_recheck_required_count: int = Field(ge=0)
    privacy_source_recheck_required_count: int = Field(ge=0)
    region_recheck_required_count: int = Field(ge=0)
    retention_recheck_required_count: int = Field(ge=0)
    cost_confirmation_required_count: int = Field(ge=0)
    source_recheck_completed_count: int = Field(ge=0)
    credential_env_var_name_count: int = Field(ge=0)
    credential_present_count: int = Field(ge=0)
    credential_missing_count: int = Field(ge=0)
    credential_value_public_exposure_count: int = Field(ge=0)
    raw_audio_public_artifact_count: int = Field(ge=0)
    raw_transcript_public_artifact_count: int = Field(ge=0)
    raw_payload_public_artifact_count: int = Field(ge=0)
    client_secret_exposure_count: int = Field(ge=0)
    public_private_path_leakage_count: int = Field(ge=0)
    public_secret_like_leakage_count: int = Field(ge=0)
    public_raw_payload_leakage_count: int = Field(ge=0)
    preflight_decision: PreflightDecision


class ManagedProviderSmokePreflightReport(ManagedProviderSmokePreflightModel):
    report_version: str = REPORT_VERSION
    preflight_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    work_id: str = WORK_ID
    depends_on: str = DEPENDS_ON
    next_work_id: str = NEXT_WORK_ID
    scripts_path: str = Field(min_length=1)
    result_path: str = Field(min_length=1)
    source_fingerprint: str = Field(min_length=8)
    provider_preflight: tuple[ManagedProviderPreflightRow, ...]
    recommended_targets: tuple[RecommendedManagedProviderSmokeTarget, ...]
    summary: ManagedProviderSmokePreflightSummary
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def run_voice_stt_tts_managed_provider_smoke_preflight(
    *,
    scripts_path: Path = DEFAULT_SCRIPTS_PATH,
    doc_path: Path = DEFAULT_DOC_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
    script_limit: int = DEFAULT_SCRIPT_LIMIT,
    execute_managed_provider: bool = False,
) -> ManagedProviderSmokePreflightReport:
    if execute_managed_provider:
        raise ValueError(
            "managed provider execution is blocked in preflight; "
            "run a separate selected-provider smoke work order after approval",
        )

    scripts = select_managed_smoke_scripts(
        load_voice_benchmark_scripts(project_path(scripts_path)),
        limit=script_limit,
    )
    provider_rows = build_provider_preflight_rows(
        provider_plans=MANAGED_PROVIDER_PLANS,
        sources=MANAGED_PROVIDER_SOURCES,
    )
    recommended_targets = build_recommended_targets(
        provider_rows=provider_rows,
        provider_plans=MANAGED_PROVIDER_PLANS,
        scripts=scripts,
    )
    summary = build_summary(
        scripts=scripts,
        provider_plans=MANAGED_PROVIDER_PLANS,
        sources=MANAGED_PROVIDER_SOURCES,
        provider_rows=provider_rows,
        recommended_targets=recommended_targets,
    )
    preflight_id = build_preflight_id(
        provider_rows=provider_rows,
        recommended_targets=recommended_targets,
        summary=summary,
    )
    public_rows = build_public_rows(
        preflight_id=preflight_id,
        provider_rows=provider_rows,
        recommended_targets=recommended_targets,
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
        scripts_path=scripts_path,
        result_rows_path=result_rows_path,
        provider_rows=provider_rows,
        recommended_targets=recommended_targets,
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
        scripts_path=scripts_path,
        result_rows_path=result_rows_path,
        provider_rows=provider_rows,
        recommended_targets=recommended_targets,
        summary=summary,
        output_quality=output_quality,
    )
    failures = collect_managed_provider_smoke_preflight_failures(report)
    if failures:
        raise ValueError(f"managed provider smoke preflight gate failed: {failures}")

    write_public_retrieval_result_rows(
        path=project_path(result_rows_path),
        rows=build_public_rows(
            preflight_id=preflight_id,
            provider_rows=provider_rows,
            recommended_targets=recommended_targets,
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
        "voice_stt_tts_managed_provider_smoke_preflight "
        "status=PASS "
        f"providers={report.summary.provider_candidate_count} "
        f"executable_candidates={report.summary.executable_provider_candidate_count} "
        f"recommended_first_provider_count={report.summary.recommended_first_provider_count} "
        f"managed_provider_api_calls={report.summary.managed_provider_api_call_count} "
        f"external_audio_transmissions={report.summary.external_audio_transmission_count}",
    )
    return report


def build_provider_preflight_rows(
    *,
    provider_plans: tuple[ManagedProviderPlan, ...],
    sources: tuple[ManagedProviderSource, ...],
) -> tuple[ManagedProviderPreflightRow, ...]:
    source_counts = _count_sources_by_provider(sources)
    rows: list[ManagedProviderPreflightRow] = []
    for plan in provider_plans:
        present_count = sum(1 for name in plan.credential_env_names if os.environ.get(name))
        missing_count = len(plan.credential_env_names) - present_count
        credential_ready = missing_count == 0
        counts = source_counts[plan.provider_candidate_id]
        rows.append(
            ManagedProviderPreflightRow(
                provider_candidate_id=plan.provider_candidate_id,
                provider_family=plan.provider_family,
                modality=plan.modality,
                planned_max_stt_calls=plan.planned_max_stt_calls,
                planned_max_tts_calls=plan.planned_max_tts_calls,
                credential_env_var_count=len(plan.credential_env_names),
                credential_present_count=present_count,
                credential_missing_count=missing_count,
                credential_ready=credential_ready,
                credential_value_public_exposure_count=CREDENTIAL_VALUE_PUBLIC_EXPOSURE_COUNT,
                source_recheck_required_count=counts["all"],
                pricing_source_recheck_required_count=counts["pricing"],
                privacy_source_recheck_required_count=counts["privacy"] + counts["data_usage"],
                source_recheck_completed_count=SOURCE_RECHECK_COMPLETED_COUNT,
                region_recheck_required=plan.region_recheck_required,
                retention_recheck_required=plan.retention_recheck_required,
                cost_confirmation_required=True,
                external_audio_transmission_if_executed=(
                    plan.external_audio_transmission_if_executed
                ),
                provider_execution_feasibility=(
                    "eligible_after_source_region_retention_recheck_and_user_approval"
                    if credential_ready
                    else "blocked_missing_credentials"
                ),
            ),
        )
    return tuple(rows)


def build_recommended_targets(
    *,
    provider_rows: tuple[ManagedProviderPreflightRow, ...],
    provider_plans: tuple[ManagedProviderPlan, ...],
    scripts: tuple[VoiceBenchmarkScript, ...],
) -> tuple[RecommendedManagedProviderSmokeTarget, ...]:
    ready_provider_ids = {
        row.provider_candidate_id for row in provider_rows if row.credential_ready
    }
    selected_provider_id = next(
        (
            provider_id
            for provider_id in RECOMMENDATION_PRIORITY
            if provider_id in ready_provider_ids
        ),
        None,
    )
    if selected_provider_id is None:
        return tuple()
    plan_by_id = {plan.provider_candidate_id: plan for plan in provider_plans}
    plan = plan_by_id[selected_provider_id]
    return (
        RecommendedManagedProviderSmokeTarget(
            provider_candidate_id=selected_provider_id,
            selection_rank=1,
            planned_script_count=len(scripts),
            planned_stt_call_count=min(
                len(scripts),
                plan.planned_max_stt_calls,
                MAX_STT_CALLS_PER_PROVIDER,
            ),
            planned_tts_call_count=min(
                len(scripts),
                plan.planned_max_tts_calls,
                MAX_TTS_CALLS_PER_PROVIDER,
            ),
            recommendation_reason=(
                "credential presence is complete; source, region, retention, "
                "cost, and user approval are still required before execution"
            ),
        ),
    )


def build_summary(
    *,
    scripts: tuple[VoiceBenchmarkScript, ...],
    provider_plans: tuple[ManagedProviderPlan, ...],
    sources: tuple[ManagedProviderSource, ...],
    provider_rows: tuple[ManagedProviderPreflightRow, ...],
    recommended_targets: tuple[RecommendedManagedProviderSmokeTarget, ...],
) -> ManagedProviderSmokePreflightSummary:
    source_type_counts = Counter(source.source_type for source in sources)
    call_cap_enforced = (
        all(plan.planned_max_stt_calls <= MAX_STT_CALLS_PER_PROVIDER for plan in provider_plans)
        and all(plan.planned_max_tts_calls <= MAX_TTS_CALLS_PER_PROVIDER for plan in provider_plans)
        and all(
            target.planned_stt_call_count <= MAX_STT_CALLS_PER_PROVIDER
            for target in recommended_targets
        )
        and all(
            target.planned_tts_call_count <= MAX_TTS_CALLS_PER_PROVIDER
            for target in recommended_targets
        )
    )
    summary = ManagedProviderSmokePreflightSummary(
        provider_candidate_count=len(provider_plans),
        selected_script_count=len(scripts),
        planned_max_stt_calls_per_provider=MAX_STT_CALLS_PER_PROVIDER,
        planned_max_tts_calls_per_provider=MAX_TTS_CALLS_PER_PROVIDER,
        call_cap_enforced=call_cap_enforced,
        executable_provider_candidate_count=sum(1 for row in provider_rows if row.credential_ready),
        recommended_first_provider_count=len(recommended_targets),
        managed_provider_execution_requested_count=MANAGED_PROVIDER_EXECUTION_REQUESTED_COUNT,
        managed_provider_api_call_count=MANAGED_PROVIDER_API_CALL_COUNT,
        external_audio_transmission_count=EXTERNAL_AUDIO_TRANSMISSION_COUNT,
        live_stt_call_count=LIVE_STT_CALL_COUNT,
        live_tts_call_count=LIVE_TTS_CALL_COUNT,
        live_solar_call_count=LIVE_SOLAR_CALL_COUNT,
        official_source_count=len(sources),
        source_recheck_required_count=len(sources),
        pricing_source_recheck_required_count=source_type_counts["pricing"],
        privacy_source_recheck_required_count=(
            source_type_counts["privacy"] + source_type_counts["data_usage"]
        ),
        region_recheck_required_count=sum(
            1 for plan in provider_plans if plan.region_recheck_required
        ),
        retention_recheck_required_count=sum(
            1 for plan in provider_plans if plan.retention_recheck_required
        ),
        cost_confirmation_required_count=len(provider_plans),
        source_recheck_completed_count=SOURCE_RECHECK_COMPLETED_COUNT,
        credential_env_var_name_count=sum(row.credential_env_var_count for row in provider_rows),
        credential_present_count=sum(row.credential_present_count for row in provider_rows),
        credential_missing_count=sum(row.credential_missing_count for row in provider_rows),
        credential_value_public_exposure_count=sum(
            row.credential_value_public_exposure_count for row in provider_rows
        ),
        raw_audio_public_artifact_count=RAW_AUDIO_PUBLIC_ARTIFACT_COUNT,
        raw_transcript_public_artifact_count=RAW_TRANSCRIPT_PUBLIC_ARTIFACT_COUNT,
        raw_payload_public_artifact_count=RAW_PAYLOAD_PUBLIC_ARTIFACT_COUNT,
        client_secret_exposure_count=CLIENT_SECRET_EXPOSURE_COUNT,
        public_private_path_leakage_count=0,
        public_secret_like_leakage_count=0,
        public_raw_payload_leakage_count=0,
        preflight_decision="blocked_by_preflight_gate",
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
    summary: ManagedProviderSmokePreflightSummary,
    output_quality: PublicRetrievalArtifactQuality | None,
) -> PreflightDecision:
    public_safety_passed = output_quality is None or not collect_public_retrieval_artifact_failures(
        output_quality,
    )
    base_gate_passed = (
        summary.provider_candidate_count >= EXPECTED_PROVIDER_COUNT
        and summary.selected_script_count == DEFAULT_SCRIPT_LIMIT
        and summary.call_cap_enforced
        and summary.recommended_first_provider_count <= 1
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
        return "blocked_by_preflight_gate"
    if summary.recommended_first_provider_count == 1:
        return "ready_for_selected_provider_smoke_approval"
    return "preflight_complete_missing_credentials"


def build_report(
    *,
    preflight_id: str,
    scripts_path: Path,
    result_rows_path: Path,
    provider_rows: tuple[ManagedProviderPreflightRow, ...],
    recommended_targets: tuple[RecommendedManagedProviderSmokeTarget, ...],
    summary: ManagedProviderSmokePreflightSummary,
    output_quality: PublicRetrievalArtifactQuality,
) -> ManagedProviderSmokePreflightReport:
    report = ManagedProviderSmokePreflightReport(
        preflight_id=preflight_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        scripts_path=public_path_alias(scripts_path),
        result_path=public_path_alias(result_rows_path),
        source_fingerprint=_stable_digest(
            {
                "provider_rows": [row.model_dump(mode="json") for row in provider_rows],
                "recommended_targets": [
                    row.model_dump(mode="json") for row in recommended_targets
                ],
            },
        ),
        provider_preflight=provider_rows,
        recommended_targets=recommended_targets,
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
    provider_rows: tuple[ManagedProviderPreflightRow, ...],
    recommended_targets: tuple[RecommendedManagedProviderSmokeTarget, ...],
    summary: ManagedProviderSmokePreflightSummary,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "row_type": "summary",
            "preflight_id": preflight_id,
            "provider_candidate_count": summary.provider_candidate_count,
            "selected_script_count": summary.selected_script_count,
            "call_cap_enforced": summary.call_cap_enforced,
            "executable_provider_candidate_count": (
                summary.executable_provider_candidate_count
            ),
            "recommended_first_provider_count": summary.recommended_first_provider_count,
            "managed_provider_execution_requested_count": (
                summary.managed_provider_execution_requested_count
            ),
            "managed_provider_api_call_count": summary.managed_provider_api_call_count,
            "external_audio_transmission_count": summary.external_audio_transmission_count,
            "source_recheck_completed_count": summary.source_recheck_completed_count,
            "credential_value_public_exposure_count": (
                summary.credential_value_public_exposure_count
            ),
            "preflight_decision": summary.preflight_decision,
        },
    ]
    rows.extend(
        {
            "row_type": "provider_preflight",
            "preflight_id": preflight_id,
            "provider_candidate_id": row.provider_candidate_id,
            "provider_family": row.provider_family,
            "modality": row.modality,
            "credential_env_var_count": row.credential_env_var_count,
            "credential_present_count": row.credential_present_count,
            "credential_missing_count": row.credential_missing_count,
            "credential_ready": row.credential_ready,
            "source_recheck_required_count": row.source_recheck_required_count,
            "source_recheck_completed_count": row.source_recheck_completed_count,
            "region_recheck_required": row.region_recheck_required,
            "retention_recheck_required": row.retention_recheck_required,
            "cost_confirmation_required": row.cost_confirmation_required,
            "provider_execution_feasibility": row.provider_execution_feasibility,
        }
        for row in provider_rows
    )
    rows.extend(
        {
            "row_type": "recommended_target",
            "preflight_id": preflight_id,
            "provider_candidate_id": row.provider_candidate_id,
            "selection_rank": row.selection_rank,
            "planned_script_count": row.planned_script_count,
            "planned_stt_call_count": row.planned_stt_call_count,
            "planned_tts_call_count": row.planned_tts_call_count,
        }
        for row in recommended_targets
    )
    return rows


def collect_managed_provider_smoke_preflight_failures(
    report: ManagedProviderSmokePreflightReport,
) -> list[str]:
    failures = collect_public_retrieval_artifact_failures(report.output_quality)
    summary = report.summary
    if summary.preflight_decision == "blocked_by_preflight_gate":
        failures.append("preflight_decision_blocked")
    if summary.provider_candidate_count < EXPECTED_PROVIDER_COUNT:
        failures.append("managed_provider_candidate_count_below_min")
    if summary.selected_script_count != DEFAULT_SCRIPT_LIMIT:
        failures.append("selected_script_count_mismatch")
    if not summary.call_cap_enforced:
        failures.append("call_cap_not_enforced")
    if summary.recommended_first_provider_count > 1:
        failures.append("recommended_first_provider_count_above_one")
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


def build_doc_markdown(report: ManagedProviderSmokePreflightReport) -> str:
    summary = report.summary
    provider_rows = "\n".join(
        _format_provider_doc_row(row) for row in report.provider_preflight
    )
    recommendation_rows = _format_recommendation_doc_rows(report.recommended_targets)
    return f"""# Voice STT/TTS Managed Provider Smoke Preflight

`{WORK_ID}`는 managed provider smoke 실행 직전의 credential, source, region, retention, cost preflight를 수행한다.

결론: 이 단계는 외부 provider API를 호출하지 않으며 credential 값도 기록하지 않는다.

## Scope

| field | value |
| --- | --- |
| work_id | `{WORK_ID}` |
| depends_on | `{DEPENDS_ON}` |
| next_work_id | `{NEXT_WORK_ID}` |
| managed_provider_api_call_count | {summary.managed_provider_api_call_count} |
| external_audio_transmission_count | {summary.external_audio_transmission_count} |
| executable_provider_candidate_count | {summary.executable_provider_candidate_count} |
| recommended_first_provider_count | {summary.recommended_first_provider_count} |
| preflight_decision | `{summary.preflight_decision}` |

## Provider Preflight

credential 값은 읽거나 출력하지 않고 환경 변수 존재 여부만 집계한다.

| provider_candidate_id | modality | credential count | present | missing | source recheck | status |
| --- | --- | ---: | ---: | ---: | ---: | --- |
{provider_rows}

## Recommended First Smoke Target

| provider_candidate_id | planned scripts | planned STT | planned TTS | reason |
| --- | ---: | ---: | ---: | --- |
{recommendation_rows}

## Quantitative Gate

| metric | value |
| --- | ---: |
| provider_candidate_count | {summary.provider_candidate_count} |
| selected_script_count | {summary.selected_script_count} |
| planned_max_stt_calls_per_provider | {summary.planned_max_stt_calls_per_provider} |
| planned_max_tts_calls_per_provider | {summary.planned_max_tts_calls_per_provider} |
| call_cap_enforced | {str(summary.call_cap_enforced).lower()} |
| executable_provider_candidate_count | {summary.executable_provider_candidate_count} |
| recommended_first_provider_count | {summary.recommended_first_provider_count} |
| managed_provider_execution_requested_count | {summary.managed_provider_execution_requested_count} |
| managed_provider_api_call_count | {summary.managed_provider_api_call_count} |
| external_audio_transmission_count | {summary.external_audio_transmission_count} |
| official_source_count | {summary.official_source_count} |
| source_recheck_required_count | {summary.source_recheck_required_count} |
| pricing_source_recheck_required_count | {summary.pricing_source_recheck_required_count} |
| privacy_source_recheck_required_count | {summary.privacy_source_recheck_required_count} |
| region_recheck_required_count | {summary.region_recheck_required_count} |
| retention_recheck_required_count | {summary.retention_recheck_required_count} |
| cost_confirmation_required_count | {summary.cost_confirmation_required_count} |
| source_recheck_completed_count | {summary.source_recheck_completed_count} |
| credential_env_var_name_count | {summary.credential_env_var_name_count} |
| credential_present_count | {summary.credential_present_count} |
| credential_missing_count | {summary.credential_missing_count} |
| credential_value_public_exposure_count | {summary.credential_value_public_exposure_count} |
| raw_audio_public_artifact_count | {summary.raw_audio_public_artifact_count} |
| raw_transcript_public_artifact_count | {summary.raw_transcript_public_artifact_count} |
| raw_payload_public_artifact_count | {summary.raw_payload_public_artifact_count} |
| client_secret_exposure_count | {summary.client_secret_exposure_count} |

## Data Mart

| table | grain | visibility |
| --- | --- | --- |
| `fact_voice_managed_smoke_preflight_provider` | `preflight_id + provider_candidate_id` | public aggregate |
| `fact_voice_managed_smoke_preflight_recommendation` | `preflight_id + selection_rank` | public aggregate |
| `fact_voice_managed_smoke_private_payload` | `run_id + provider_candidate_id + script_id` | private only |

## Claim Boundary

허용 claim:

- managed provider smoke 실행 전 preflight를 구현했다.

- managed provider API call과 external audio transmission은 0회다.

- credential 값은 public artifact에 기록하지 않았다.

- 실제 smoke 실행은 source, region, retention, cost 재확인과 별도 승인 뒤에만 가능하다.

금지 claim:

- provider 최종 선택 완료

- managed provider STT/TTS 품질 검증 완료

- 외부 provider benchmark 완료

- production voice service 준비 완료

- managed provider 비용/정책 최신 확인 완료
"""


def build_report_markdown(report: ManagedProviderSmokePreflightReport) -> str:
    summary = report.summary
    quality = report.output_quality
    provider_rows = "\n".join(
        _format_provider_report_row(row) for row in report.provider_preflight
    )
    recommendation_rows = _format_recommendation_report_rows(report.recommended_targets)
    qualitative_rows = "\n".join(
        f"| {key} | {value} |" for key, value in report.qualitative_assessment.items()
    )
    failures = collect_managed_provider_smoke_preflight_failures(report)
    return f"""# Voice STT/TTS Managed Provider Smoke Preflight Report

`{WORK_ID}`는 {"PASS" if not failures else "FAIL"}다.

이번 report는 managed provider 실제 smoke 결과가 아니라 실행 직전 preflight 검증 결과다.

## Execution Info

| field | value |
| --- | --- |
| report_version | `{report.report_version}` |
| preflight_id | `{report.preflight_id}` |
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
| provider_candidate_count | {summary.provider_candidate_count} |
| selected_script_count | {summary.selected_script_count} |
| planned_max_stt_calls_per_provider | {summary.planned_max_stt_calls_per_provider} |
| planned_max_tts_calls_per_provider | {summary.planned_max_tts_calls_per_provider} |
| call_cap_enforced | {str(summary.call_cap_enforced).lower()} |
| executable_provider_candidate_count | {summary.executable_provider_candidate_count} |
| recommended_first_provider_count | {summary.recommended_first_provider_count} |
| managed_provider_execution_requested_count | {summary.managed_provider_execution_requested_count} |
| managed_provider_api_call_count | {summary.managed_provider_api_call_count} |
| external_audio_transmission_count | {summary.external_audio_transmission_count} |
| live_stt_call_count | {summary.live_stt_call_count} |
| live_tts_call_count | {summary.live_tts_call_count} |
| live_solar_call_count | {summary.live_solar_call_count} |
| official_source_count | {summary.official_source_count} |
| source_recheck_required_count | {summary.source_recheck_required_count} |
| pricing_source_recheck_required_count | {summary.pricing_source_recheck_required_count} |
| privacy_source_recheck_required_count | {summary.privacy_source_recheck_required_count} |
| region_recheck_required_count | {summary.region_recheck_required_count} |
| retention_recheck_required_count | {summary.retention_recheck_required_count} |
| cost_confirmation_required_count | {summary.cost_confirmation_required_count} |
| source_recheck_completed_count | {summary.source_recheck_completed_count} |
| credential_env_var_name_count | {summary.credential_env_var_name_count} |
| credential_present_count | {summary.credential_present_count} |
| credential_missing_count | {summary.credential_missing_count} |
| credential_value_public_exposure_count | {summary.credential_value_public_exposure_count} |
| raw_audio_public_artifact_count | {summary.raw_audio_public_artifact_count} |
| raw_transcript_public_artifact_count | {summary.raw_transcript_public_artifact_count} |
| raw_payload_public_artifact_count | {summary.raw_payload_public_artifact_count} |
| client_secret_exposure_count | {summary.client_secret_exposure_count} |
| public_private_path_leakage_count | {summary.public_private_path_leakage_count} |
| public_secret_like_leakage_count | {summary.public_secret_like_leakage_count} |
| public_raw_payload_leakage_count | {summary.public_raw_payload_leakage_count} |
| preflight_decision | `{summary.preflight_decision}` |

## Provider Preflight

| provider_candidate_id | modality | credential present/missing | source recheck | feasibility |
| --- | --- | ---: | ---: | --- |
{provider_rows}

## Recommendation

| provider_candidate_id | planned scripts | planned STT | planned TTS | reason |
| --- | ---: | ---: | ---: | --- |
{recommendation_rows}

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
| recommended first provider 1개 이하 유지 | PASS |
| source/region/retention/cost 재확인 필요 상태 기록 | PASS |
"""


def build_qualitative_assessment(
    report: ManagedProviderSmokePreflightReport,
) -> dict[str, str]:
    if report.summary.recommended_first_provider_count:
        next_step = "추천 provider 1개만 다음 실제 smoke 승인 대상으로 남겼다."
    else:
        next_step = "credential이 준비된 managed provider가 없어 실제 smoke는 보류 상태다."
    return {
        "security_boundary": "credential 값, raw audio, raw transcript, provider payload를 public artifact에 기록하지 않는다.",
        "eval_boundary": "이번 결과는 preflight 검증이며 STT/TTS 품질 비교가 아니다.",
        "data_mart_boundary": "provider grain, recommendation grain, private payload grain을 분리했다.",
        "operations_boundary": next_step,
    }


def build_preflight_id(
    *,
    provider_rows: tuple[ManagedProviderPreflightRow, ...],
    recommended_targets: tuple[RecommendedManagedProviderSmokeTarget, ...],
    summary: ManagedProviderSmokePreflightSummary,
) -> str:
    return "managed-smoke-preflight-" + _stable_digest(
        {
            "provider_rows": [row.model_dump(mode="json") for row in provider_rows],
            "recommended_targets": [
                row.model_dump(mode="json") for row in recommended_targets
            ],
            "summary": summary.model_dump(mode="json"),
        },
    )


def _count_sources_by_provider(
    sources: tuple[ManagedProviderSource, ...],
) -> dict[str, Counter[str]]:
    counts: dict[str, Counter[str]] = {
        plan.provider_candidate_id: Counter() for plan in MANAGED_PROVIDER_PLANS
    }
    for source in sources:
        counts[source.provider_candidate_id]["all"] += 1
        counts[source.provider_candidate_id][source.source_type] += 1
    return counts


def _format_provider_doc_row(row: ManagedProviderPreflightRow) -> str:
    return (
        f"| `{row.provider_candidate_id}` | {row.modality} | "
        f"{row.credential_env_var_count} | {row.credential_present_count} | "
        f"{row.credential_missing_count} | {row.source_recheck_required_count} | "
        f"`{row.provider_execution_feasibility}` |"
    )


def _format_recommendation_doc_rows(
    rows: tuple[RecommendedManagedProviderSmokeTarget, ...],
) -> str:
    if not rows:
        return "| none | 0 | 0 | 0 | credential 준비 후 재실행 필요 |"
    return "\n".join(
        (
            f"| `{row.provider_candidate_id}` | {row.planned_script_count} | "
            f"{row.planned_stt_call_count} | {row.planned_tts_call_count} | "
            f"{row.recommendation_reason} |"
        )
        for row in rows
    )


def _format_provider_report_row(row: ManagedProviderPreflightRow) -> str:
    return (
        f"| `{row.provider_candidate_id}` | {row.modality} | "
        f"{row.credential_present_count}/{row.credential_missing_count} | "
        f"{row.source_recheck_required_count} | "
        f"`{row.provider_execution_feasibility}` |"
    )


def _format_recommendation_report_rows(
    rows: tuple[RecommendedManagedProviderSmokeTarget, ...],
) -> str:
    return _format_recommendation_doc_rows(rows)


def _stable_digest(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"),
    ).hexdigest()[:16]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build managed provider STT/TTS smoke preflight without API calls.",
    )
    parser.add_argument("--scripts", type=Path, default=DEFAULT_SCRIPTS_PATH)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--result-rows", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    parser.add_argument("--script-limit", type=int, default=DEFAULT_SCRIPT_LIMIT)
    parser.add_argument(
        "--execute-managed-provider",
        action="store_true",
        help="Blocked in this preflight gate; actual execution needs separate approval.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_voice_stt_tts_managed_provider_smoke_preflight(
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
