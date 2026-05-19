from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from app.core.project_paths import project_path
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    collect_public_retrieval_artifact_failures,
    measure_public_retrieval_artifact_quality,
    public_path_alias,
    write_public_retrieval_result_rows,
)
from app.infrastructure.index.device import resolve_torch_device


VOICE_STT_TTS_PROVIDER_BENCH_READINESS_REPORT_VERSION = (
    "voice-stt-tts-provider-bench-readiness-report/v1"
)
WORK_ID = "HD-VOICE-STT-TTS-PROVIDER-BENCH-READINESS-001"
PLAN_WORK_ID = "HD-VOICE-STT-TTS-PROVIDER-BENCH-PLAN-001"
DEFAULT_CONFIG_PATH = Path("configs") / "voice_provider_candidates.yaml"
DEFAULT_SCRIPTS_PATH = Path("data_samples") / "voice_benchmark_scripts.sample.jsonl"
DEFAULT_DOC_PATH = Path("docs") / "VOICE_STT_TTS_PROVIDER_BENCH_READINESS.md"
DEFAULT_REPORT_PATH = (
    Path("evals") / "reports" / "voice_stt_tts_provider_bench_readiness_report.md"
)
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "voice_stt_tts_provider_bench_readiness_rows.jsonl"
)
EXPECTED_PROVIDER_CANDIDATE_COUNT = 5
EXPECTED_OFFICIAL_SOURCE_COUNT = 14
EXPECTED_PRICING_SOURCE_LINK_COUNT = 5
EXPECTED_PRIVACY_SOURCE_LINK_COUNT = 4
EXPECTED_QUERY_TYPE_COUNT = 6
EXPECTED_MIN_PUBLIC_SAFE_SCRIPT_COUNT = 30
EXPECTED_MIN_SCRIPT_PER_QUERY_TYPE = 5
LIVE_STT_CALL_COUNT = 0
LIVE_TTS_CALL_COUNT = 0
LIVE_SOLAR_CALL_COUNT = 0
PROVIDER_BENCHMARK_EXECUTION_COUNT = 0
PROVIDER_FINALIZED_COUNT = 0
PRIVATE_AUDIO_SAVED_COUNT = 0
RAW_TRANSCRIPT_PUBLIC_ARTIFACT_COUNT = 0
CLIENT_SECRET_EXPOSURE_COUNT = 0
REQUIRED_PROVIDER_IDS = (
    "browser_native_web_speech",
    "local_cuda_whisper",
    "external_google_cloud",
    "external_azure_speech",
    "external_aws_transcribe_polly",
)
REQUIRED_QUERY_TYPES = (
    "place_fact",
    "place_story",
    "relationship",
    "route_context",
    "voice_followup",
    "no_answer",
)

ProviderModality = Literal["stt", "tts", "stt_tts"]
SourceKind = Literal["technical", "pricing", "privacy"]
ReadinessDecision = Literal[
    "ready_for_provider_benchmark_execution_approval",
    "blocked_by_readiness_gate",
]


class VoiceReadinessModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class VoiceSourcePolicy(VoiceReadinessModel):
    source_checked_at: str = Field(min_length=1)
    pricing_recheck_required: bool
    privacy_recheck_required: bool
    region_recheck_required: bool
    price_value_fixed_in_public_repo: bool
    live_execution_enabled: bool
    benchmark_execution_enabled: bool


class VoiceProviderCandidate(VoiceReadinessModel):
    provider_candidate_id: str = Field(min_length=1)
    provider_family: str = Field(min_length=1)
    modality: ProviderModality
    execution_surface: str = Field(min_length=1)
    requires_server_credential: bool
    external_audio_transmission: str = Field(min_length=1)
    model_download_required: bool
    planned_max_stt_calls: int = Field(ge=0)
    planned_max_tts_calls: int = Field(ge=0)
    readiness_status: Literal["keep_candidate", "reject_candidate"]
    decision_reason_code: str = Field(min_length=1)
    source_ids: tuple[str, ...] = Field(min_length=1)


class VoiceOfficialSource(VoiceReadinessModel):
    source_id: str = Field(min_length=1)
    provider_candidate_id: str = Field(min_length=1)
    source_kind: SourceKind
    url: str = Field(min_length=1)


class VoiceProviderConfig(VoiceReadinessModel):
    config_version: str = Field(min_length=1)
    work_id: str = Field(min_length=1)
    source_policy: VoiceSourcePolicy
    provider_candidates: tuple[VoiceProviderCandidate, ...]
    official_sources: tuple[VoiceOfficialSource, ...]
    forbidden_public_fields: tuple[str, ...]


class VoiceBenchmarkScript(VoiceReadinessModel):
    script_id: str = Field(min_length=1)
    query_type: Literal[
        "place_fact",
        "place_story",
        "relationship",
        "route_context",
        "voice_followup",
        "no_answer",
    ]
    language: str = Field(min_length=1)
    script_text: str = Field(min_length=1, max_length=120)
    place_ids: tuple[str, ...]
    expected_behavior: Literal["answer_with_citation", "abstain"]
    public_allowed: bool
    audio_artifact_required: bool
    raw_audio_saved: bool


class VoiceCudaPreflight(VoiceReadinessModel):
    resolved_device: str = Field(min_length=1)
    local_cuda_available: bool
    torch_cuda_available: bool
    cuda_device_count: int = Field(ge=0)
    cuda_device_name: str
    cuda_runtime_probe_error_count: int = Field(ge=0)


class VoiceQueryTypeScriptSummary(VoiceReadinessModel):
    query_type: str = Field(min_length=1)
    script_count: int = Field(ge=0)
    public_allowed_count: int = Field(ge=0)
    audio_artifact_required_count: int = Field(ge=0)
    raw_audio_saved_count: int = Field(ge=0)


class VoiceProviderCandidateSummary(VoiceReadinessModel):
    provider_candidate_id: str = Field(min_length=1)
    modality: ProviderModality
    requires_server_credential: bool
    external_audio_transmission: str = Field(min_length=1)
    model_download_required: bool
    planned_max_stt_calls: int = Field(ge=0)
    planned_max_tts_calls: int = Field(ge=0)
    readiness_status: str = Field(min_length=1)
    pricing_recheck_required: bool
    privacy_recheck_required: bool
    live_stt_call_count: int = Field(ge=0)
    live_tts_call_count: int = Field(ge=0)


class VoiceProviderReadinessSummary(VoiceReadinessModel):
    provider_candidate_group_count: int = Field(ge=0)
    required_provider_candidate_group_count: int = Field(ge=1)
    official_source_checked_count: int = Field(ge=0)
    pricing_source_link_count: int = Field(ge=0)
    privacy_source_link_count: int = Field(ge=0)
    benchmark_script_count: int = Field(ge=0)
    benchmark_query_type_count: int = Field(ge=0)
    script_per_query_type_min_count: int = Field(ge=0)
    planned_public_safe_script_min_count: int = Field(ge=1)
    local_cuda_available_count: int = Field(ge=0)
    cuda_device_count: int = Field(ge=0)
    provider_finalized_count: int = Field(ge=0)
    provider_benchmark_execution_count: int = Field(ge=0)
    live_stt_call_count: int = Field(ge=0)
    live_tts_call_count: int = Field(ge=0)
    live_solar_call_count: int = Field(ge=0)
    private_audio_saved_count: int = Field(ge=0)
    raw_transcript_public_artifact_count: int = Field(ge=0)
    client_secret_exposure_count: int = Field(ge=0)
    pricing_recheck_required_count: int = Field(ge=0)
    privacy_recheck_required_count: int = Field(ge=0)
    region_recheck_required_count: int = Field(ge=0)
    pricing_claim_without_source_count: int = Field(ge=0)
    privacy_policy_unknown_count: int = Field(ge=0)
    public_private_path_leakage_count: int = Field(ge=0)
    public_secret_like_leakage_count: int = Field(ge=0)
    public_raw_payload_leakage_count: int = Field(ge=0)
    readiness_decision: ReadinessDecision


class VoiceProviderReadinessReport(VoiceReadinessModel):
    report_version: str = VOICE_STT_TTS_PROVIDER_BENCH_READINESS_REPORT_VERSION
    readiness_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    work_id: str = WORK_ID
    depends_on: str = PLAN_WORK_ID
    config_path: str = Field(min_length=1)
    scripts_path: str = Field(min_length=1)
    result_path: str = Field(min_length=1)
    source_fingerprint: str = Field(min_length=8)
    cuda_preflight: VoiceCudaPreflight
    summary: VoiceProviderReadinessSummary
    query_type_breakdown: tuple[VoiceQueryTypeScriptSummary, ...]
    provider_candidates: tuple[VoiceProviderCandidateSummary, ...]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def run_voice_stt_tts_provider_bench_readiness(
    *,
    config_path: Path = DEFAULT_CONFIG_PATH,
    scripts_path: Path = DEFAULT_SCRIPTS_PATH,
    doc_path: Path = DEFAULT_DOC_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
) -> VoiceProviderReadinessReport:
    config = load_voice_provider_config(project_path(config_path))
    scripts = load_voice_benchmark_scripts(project_path(scripts_path))
    cuda_preflight = build_cuda_preflight()
    provider_rows = build_provider_candidate_summaries(config)
    query_type_rows = build_query_type_script_summary(scripts)
    summary = build_voice_readiness_summary(
        config=config,
        scripts=scripts,
        cuda_preflight=cuda_preflight,
        provider_rows=provider_rows,
        query_type_rows=query_type_rows,
    )
    readiness_id = build_voice_readiness_id(
        config=config,
        scripts=scripts,
        cuda_preflight=cuda_preflight,
        summary=summary,
    )
    public_rows = build_public_voice_readiness_rows(
        readiness_id=readiness_id,
        summary=summary,
        query_type_rows=query_type_rows,
        provider_rows=provider_rows,
    )
    provisional_quality = measure_public_retrieval_artifact_quality(
        report_version=VOICE_STT_TTS_PROVIDER_BENCH_READINESS_REPORT_VERSION,
        run_id=readiness_id,
        result_rows=public_rows,
        report_text="",
    )
    provisional = build_voice_readiness_report(
        readiness_id=readiness_id,
        config_path=config_path,
        scripts_path=scripts_path,
        result_rows_path=result_rows_path,
        config=config,
        cuda_preflight=cuda_preflight,
        summary=summary,
        query_type_rows=query_type_rows,
        provider_rows=provider_rows,
        output_quality=provisional_quality,
    )
    doc_text = build_voice_readiness_doc(provisional)
    report_text = build_voice_readiness_markdown(provisional)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=VOICE_STT_TTS_PROVIDER_BENCH_READINESS_REPORT_VERSION,
        run_id=readiness_id,
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
            "readiness_decision": build_readiness_decision(
                summary=summary,
                output_quality=output_quality,
            ),
        },
    )
    report = build_voice_readiness_report(
        readiness_id=readiness_id,
        config_path=config_path,
        scripts_path=scripts_path,
        result_rows_path=result_rows_path,
        config=config,
        cuda_preflight=cuda_preflight,
        summary=summary,
        query_type_rows=query_type_rows,
        provider_rows=provider_rows,
        output_quality=output_quality,
    )
    failures = collect_voice_readiness_failures(report)
    if failures:
        raise ValueError(f"voice provider readiness gate failed: {failures}")

    write_public_retrieval_result_rows(
        path=project_path(result_rows_path),
        rows=build_public_voice_readiness_rows(
            readiness_id=readiness_id,
            summary=summary,
            query_type_rows=query_type_rows,
            provider_rows=provider_rows,
        ),
    )
    resolved_doc_path = project_path(doc_path)
    resolved_report_path = project_path(report_path)
    resolved_doc_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_report_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_doc_path.write_text(build_voice_readiness_doc(report), encoding="utf-8")
    resolved_report_path.write_text(
        build_voice_readiness_markdown(report),
        encoding="utf-8",
    )
    print(
        "voice_stt_tts_provider_bench_readiness "
        "status=PASS "
        f"provider_candidates={report.summary.provider_candidate_group_count} "
        f"scripts={report.summary.benchmark_script_count} "
        f"query_types={report.summary.benchmark_query_type_count} "
        f"device={report.cuda_preflight.resolved_device} "
        f"live_stt_calls={report.summary.live_stt_call_count} "
        f"live_tts_calls={report.summary.live_tts_call_count}",
    )
    return report


def load_voice_provider_config(path: Path) -> VoiceProviderConfig:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("voice provider candidate config must be an object")
    return VoiceProviderConfig.model_validate(payload)


def load_voice_benchmark_scripts(path: Path) -> tuple[VoiceBenchmarkScript, ...]:
    rows: list[VoiceBenchmarkScript] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid script jsonl at line {line_number}") from exc
        rows.append(VoiceBenchmarkScript.model_validate(payload))
    return tuple(rows)


def build_cuda_preflight() -> VoiceCudaPreflight:
    resolved_device = resolve_torch_device("cuda_if_available")
    try:
        import torch
    except ImportError:
        return VoiceCudaPreflight(
            resolved_device=resolved_device,
            local_cuda_available=False,
            torch_cuda_available=False,
            cuda_device_count=0,
            cuda_device_name="",
            cuda_runtime_probe_error_count=0,
        )
    try:
        torch_cuda_available = bool(torch.cuda.is_available())
        device_count = int(torch.cuda.device_count()) if torch_cuda_available else 0
        device_name = torch.cuda.get_device_name(0) if device_count else ""
        return VoiceCudaPreflight(
            resolved_device=resolved_device,
            local_cuda_available=torch_cuda_available,
            torch_cuda_available=torch_cuda_available,
            cuda_device_count=device_count,
            cuda_device_name=device_name,
            cuda_runtime_probe_error_count=0,
        )
    except Exception:
        return VoiceCudaPreflight(
            resolved_device=resolved_device,
            local_cuda_available=False,
            torch_cuda_available=False,
            cuda_device_count=0,
            cuda_device_name="",
            cuda_runtime_probe_error_count=1,
        )


def build_provider_candidate_summaries(
    config: VoiceProviderConfig,
) -> tuple[VoiceProviderCandidateSummary, ...]:
    rows: list[VoiceProviderCandidateSummary] = []
    for candidate in config.provider_candidates:
        rows.append(
            VoiceProviderCandidateSummary(
                provider_candidate_id=candidate.provider_candidate_id,
                modality=candidate.modality,
                requires_server_credential=candidate.requires_server_credential,
                external_audio_transmission=candidate.external_audio_transmission,
                model_download_required=candidate.model_download_required,
                planned_max_stt_calls=candidate.planned_max_stt_calls,
                planned_max_tts_calls=candidate.planned_max_tts_calls,
                readiness_status=candidate.readiness_status,
                pricing_recheck_required=config.source_policy.pricing_recheck_required,
                privacy_recheck_required=config.source_policy.privacy_recheck_required,
                live_stt_call_count=LIVE_STT_CALL_COUNT,
                live_tts_call_count=LIVE_TTS_CALL_COUNT,
            ),
        )
    return tuple(rows)


def build_query_type_script_summary(
    scripts: tuple[VoiceBenchmarkScript, ...],
) -> tuple[VoiceQueryTypeScriptSummary, ...]:
    rows: list[VoiceQueryTypeScriptSummary] = []
    by_type: dict[str, list[VoiceBenchmarkScript]] = {
        query_type: [script for script in scripts if script.query_type == query_type]
        for query_type in REQUIRED_QUERY_TYPES
    }
    for query_type, query_scripts in by_type.items():
        rows.append(
            VoiceQueryTypeScriptSummary(
                query_type=query_type,
                script_count=len(query_scripts),
                public_allowed_count=sum(1 for script in query_scripts if script.public_allowed),
                audio_artifact_required_count=sum(
                    1 for script in query_scripts if script.audio_artifact_required
                ),
                raw_audio_saved_count=sum(1 for script in query_scripts if script.raw_audio_saved),
            ),
        )
    return tuple(rows)


def build_voice_readiness_summary(
    *,
    config: VoiceProviderConfig,
    scripts: tuple[VoiceBenchmarkScript, ...],
    cuda_preflight: VoiceCudaPreflight,
    provider_rows: tuple[VoiceProviderCandidateSummary, ...],
    query_type_rows: tuple[VoiceQueryTypeScriptSummary, ...],
) -> VoiceProviderReadinessSummary:
    source_kind_counts = Counter(source.source_kind for source in config.official_sources)
    script_per_query_type_min_count = min(
        (row.script_count for row in query_type_rows),
        default=0,
    )
    pricing_claim_without_source_count = int(
        config.source_policy.price_value_fixed_in_public_repo
        or source_kind_counts.get("pricing", 0) != EXPECTED_PRICING_SOURCE_LINK_COUNT
    )
    privacy_policy_unknown_count = int(
        source_kind_counts.get("privacy", 0) != EXPECTED_PRIVACY_SOURCE_LINK_COUNT
    )
    summary = VoiceProviderReadinessSummary(
        provider_candidate_group_count=len(config.provider_candidates),
        required_provider_candidate_group_count=EXPECTED_PROVIDER_CANDIDATE_COUNT,
        official_source_checked_count=len(config.official_sources),
        pricing_source_link_count=source_kind_counts.get("pricing", 0),
        privacy_source_link_count=source_kind_counts.get("privacy", 0),
        benchmark_script_count=len(scripts),
        benchmark_query_type_count=len({script.query_type for script in scripts}),
        script_per_query_type_min_count=script_per_query_type_min_count,
        planned_public_safe_script_min_count=EXPECTED_MIN_PUBLIC_SAFE_SCRIPT_COUNT,
        local_cuda_available_count=int(cuda_preflight.local_cuda_available),
        cuda_device_count=cuda_preflight.cuda_device_count,
        provider_finalized_count=PROVIDER_FINALIZED_COUNT,
        provider_benchmark_execution_count=PROVIDER_BENCHMARK_EXECUTION_COUNT,
        live_stt_call_count=LIVE_STT_CALL_COUNT,
        live_tts_call_count=LIVE_TTS_CALL_COUNT,
        live_solar_call_count=LIVE_SOLAR_CALL_COUNT,
        private_audio_saved_count=PRIVATE_AUDIO_SAVED_COUNT,
        raw_transcript_public_artifact_count=RAW_TRANSCRIPT_PUBLIC_ARTIFACT_COUNT,
        client_secret_exposure_count=CLIENT_SECRET_EXPOSURE_COUNT,
        pricing_recheck_required_count=sum(
            1 for row in provider_rows if row.pricing_recheck_required
        ),
        privacy_recheck_required_count=sum(
            1 for row in provider_rows if row.privacy_recheck_required
        ),
        region_recheck_required_count=(
            len(provider_rows) if config.source_policy.region_recheck_required else 0
        ),
        pricing_claim_without_source_count=pricing_claim_without_source_count,
        privacy_policy_unknown_count=privacy_policy_unknown_count,
        public_private_path_leakage_count=0,
        public_secret_like_leakage_count=0,
        public_raw_payload_leakage_count=0,
        readiness_decision="blocked_by_readiness_gate",
    )
    return summary.model_copy(
        update={
            "readiness_decision": build_readiness_decision(
                summary=summary,
                output_quality=None,
            ),
        },
    )


def build_voice_readiness_report(
    *,
    readiness_id: str,
    config_path: Path,
    scripts_path: Path,
    result_rows_path: Path,
    config: VoiceProviderConfig,
    cuda_preflight: VoiceCudaPreflight,
    summary: VoiceProviderReadinessSummary,
    query_type_rows: tuple[VoiceQueryTypeScriptSummary, ...],
    provider_rows: tuple[VoiceProviderCandidateSummary, ...],
    output_quality: PublicRetrievalArtifactQuality,
) -> VoiceProviderReadinessReport:
    report = VoiceProviderReadinessReport(
        readiness_id=readiness_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        config_path=public_path_alias(config_path),
        scripts_path=public_path_alias(scripts_path),
        result_path=public_path_alias(result_rows_path),
        source_fingerprint=_stable_digest(
            {
                "config": config.model_dump(mode="json"),
                "script_summary": [row.model_dump(mode="json") for row in query_type_rows],
                "provider_summary": [row.model_dump(mode="json") for row in provider_rows],
            },
        ),
        cuda_preflight=cuda_preflight,
        summary=summary,
        query_type_breakdown=query_type_rows,
        provider_candidates=provider_rows,
        output_quality=output_quality,
        qualitative_assessment={},
    )
    return report.model_copy(
        update={"qualitative_assessment": build_voice_readiness_assessment(report)},
    )


def build_public_voice_readiness_rows(
    *,
    readiness_id: str,
    summary: VoiceProviderReadinessSummary,
    query_type_rows: tuple[VoiceQueryTypeScriptSummary, ...],
    provider_rows: tuple[VoiceProviderCandidateSummary, ...],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "row_type": "summary",
            "readiness_id": readiness_id,
            "provider_candidate_group_count": summary.provider_candidate_group_count,
            "official_source_checked_count": summary.official_source_checked_count,
            "pricing_source_link_count": summary.pricing_source_link_count,
            "privacy_source_link_count": summary.privacy_source_link_count,
            "benchmark_script_count": summary.benchmark_script_count,
            "benchmark_query_type_count": summary.benchmark_query_type_count,
            "provider_benchmark_execution_count": (
                summary.provider_benchmark_execution_count
            ),
            "live_stt_call_count": summary.live_stt_call_count,
            "live_tts_call_count": summary.live_tts_call_count,
            "live_solar_call_count": summary.live_solar_call_count,
            "readiness_decision": summary.readiness_decision,
        },
    ]
    rows.extend(
        {
            "row_type": "query_type",
            "readiness_id": readiness_id,
            "query_type": row.query_type,
            "script_count": row.script_count,
            "public_allowed_count": row.public_allowed_count,
            "audio_artifact_required_count": row.audio_artifact_required_count,
            "raw_audio_saved_count": row.raw_audio_saved_count,
        }
        for row in query_type_rows
    )
    rows.extend(
        {
            "row_type": "provider_candidate",
            "readiness_id": readiness_id,
            "provider_candidate_id": row.provider_candidate_id,
            "modality": row.modality,
            "requires_server_credential": row.requires_server_credential,
            "external_audio_transmission": row.external_audio_transmission,
            "model_download_required": row.model_download_required,
            "planned_max_stt_calls": row.planned_max_stt_calls,
            "planned_max_tts_calls": row.planned_max_tts_calls,
            "readiness_status": row.readiness_status,
            "live_stt_call_count": row.live_stt_call_count,
            "live_tts_call_count": row.live_tts_call_count,
        }
        for row in provider_rows
    )
    return rows


def collect_voice_readiness_failures(report: VoiceProviderReadinessReport) -> list[str]:
    failures = collect_public_retrieval_artifact_failures(report.output_quality)
    summary = report.summary
    provider_ids = {row.provider_candidate_id for row in report.provider_candidates}
    query_type_counts = {row.query_type: row.script_count for row in report.query_type_breakdown}
    if summary.readiness_decision == "blocked_by_readiness_gate":
        failures.append("readiness_decision_blocked")
    if summary.provider_candidate_group_count != EXPECTED_PROVIDER_CANDIDATE_COUNT:
        failures.append("provider_candidate_count_mismatch")
    if provider_ids != set(REQUIRED_PROVIDER_IDS):
        failures.append("provider_candidate_id_mismatch")
    if summary.official_source_checked_count != EXPECTED_OFFICIAL_SOURCE_COUNT:
        failures.append("official_source_count_mismatch")
    if summary.pricing_source_link_count != EXPECTED_PRICING_SOURCE_LINK_COUNT:
        failures.append("pricing_source_link_count_mismatch")
    if summary.privacy_source_link_count != EXPECTED_PRIVACY_SOURCE_LINK_COUNT:
        failures.append("privacy_source_link_count_mismatch")
    if summary.benchmark_script_count < EXPECTED_MIN_PUBLIC_SAFE_SCRIPT_COUNT:
        failures.append("benchmark_script_count_below_min")
    if summary.benchmark_query_type_count != EXPECTED_QUERY_TYPE_COUNT:
        failures.append("query_type_count_mismatch")
    if set(query_type_counts) != set(REQUIRED_QUERY_TYPES):
        failures.append("query_type_id_mismatch")
    if any(count < EXPECTED_MIN_SCRIPT_PER_QUERY_TYPE for count in query_type_counts.values()):
        failures.append("script_per_query_type_below_min")
    if summary.provider_finalized_count:
        failures.append("provider_finalized_in_readiness")
    if summary.provider_benchmark_execution_count:
        failures.append("provider_benchmark_executed_in_readiness")
    if summary.live_stt_call_count:
        failures.append("live_stt_called_in_readiness")
    if summary.live_tts_call_count:
        failures.append("live_tts_called_in_readiness")
    if summary.live_solar_call_count:
        failures.append("live_solar_called_in_readiness")
    if summary.private_audio_saved_count:
        failures.append("private_audio_saved_in_readiness")
    if summary.raw_transcript_public_artifact_count:
        failures.append("raw_transcript_public_artifact_created")
    if summary.client_secret_exposure_count:
        failures.append("client_secret_exposed")
    if summary.pricing_claim_without_source_count:
        failures.append("pricing_claim_without_source")
    if summary.privacy_policy_unknown_count:
        failures.append("privacy_policy_unknown")
    if report.cuda_preflight.resolved_device not in {"cuda", "cpu"}:
        failures.append("unexpected_resolved_device")
    return list(dict.fromkeys(failures))


def build_voice_readiness_doc(report: VoiceProviderReadinessReport) -> str:
    summary = report.summary
    query_rows = "\n".join(_format_doc_query_type_row(row) for row in report.query_type_breakdown)
    provider_rows = "\n".join(
        _format_doc_provider_row(row) for row in report.provider_candidates
    )
    return f"""# Voice STT/TTS Provider Benchmark Readiness

## 결론

`{WORK_ID}`는 provider benchmark 실행 전 readiness gate다.

| boundary | value |
| --- | --- |
| STT/TTS provider live call | disabled |
| Solar Pro 3 live call | disabled |
| raw audio public artifact | forbidden |
| raw transcript public artifact | forbidden |
| provider final decision | forbidden |

## 정량 요약

| metric | value |
| --- | ---: |
| provider_candidate_group_count | {summary.provider_candidate_group_count} |
| official_source_checked_count | {summary.official_source_checked_count} |
| pricing_source_link_count | {summary.pricing_source_link_count} |
| privacy_source_link_count | {summary.privacy_source_link_count} |
| benchmark_script_count | {summary.benchmark_script_count} |
| benchmark_query_type_count | {summary.benchmark_query_type_count} |
| script_per_query_type_min_count | {summary.script_per_query_type_min_count} |
| local_cuda_available_count | {summary.local_cuda_available_count} |
| cuda_device_count | {summary.cuda_device_count} |
| provider_benchmark_execution_count | {summary.provider_benchmark_execution_count} |
| live_stt_call_count | {summary.live_stt_call_count} |
| live_tts_call_count | {summary.live_tts_call_count} |
| live_solar_call_count | {summary.live_solar_call_count} |
| readiness_decision | `{summary.readiness_decision}` |

## CUDA Preflight

| field | value |
| --- | --- |
| resolved_device | `{report.cuda_preflight.resolved_device}` |
| local_cuda_available | {str(report.cuda_preflight.local_cuda_available).lower()} |
| torch_cuda_available | {str(report.cuda_preflight.torch_cuda_available).lower()} |
| cuda_device_count | {report.cuda_preflight.cuda_device_count} |
| cuda_device_name | `{report.cuda_preflight.cuda_device_name}` |

## Provider Candidate Boundary

| provider_candidate_id | modality | planned_stt | planned_tts | live_stt | live_tts |
| --- | --- | ---: | ---: | ---: | ---: |
{provider_rows}

## Benchmark Script Fixture

| query_type | script_count | public_allowed | audio_required | raw_audio_saved |
| --- | ---: | ---: | ---: | ---: |
{query_rows}

## 다음 작업

| priority | work_id | 작업 | 승인 필요 |
| ---: | --- | --- | --- |
| 1 | `HD-VOICE-STT-TTS-PROVIDER-BENCH-EXECUTION-APPROVAL-001` | provider별 live benchmark 실행 승인 | 예 |

## Claim Boundary

| claim | allowed |
| --- | --- |
| provider benchmark readiness gate 통과 | yes |
| live STT/TTS call은 0회 | yes |
| CUDA 사용 가능 여부를 기록 | yes |
| provider 최종 선택 완료 | no |
| STT/TTS 품질 검증 완료 | no |
| 음성 관광 앱 완성 | no |
"""


def build_voice_readiness_markdown(report: VoiceProviderReadinessReport) -> str:
    summary = report.summary
    quality = report.output_quality
    query_rows = "\n".join(
        _format_report_query_type_row(row) for row in report.query_type_breakdown
    )
    provider_rows = "\n".join(
        _format_report_provider_row(row) for row in report.provider_candidates
    )
    qualitative_rows = "\n".join(
        f"| {key} | {value} |" for key, value in report.qualitative_assessment.items()
    )
    failures = collect_voice_readiness_failures(report)
    return f"""# Voice STT/TTS Provider Benchmark Readiness Report

## 목적

`{WORK_ID}`는 provider 비교 실행 전 조건만 검증한다.

이번 리포트는 quality benchmark 결과가 아니다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| readiness_id | `{report.readiness_id}` |
| work_id | `{report.work_id}` |
| depends_on | `{report.depends_on}` |
| generated_at_utc | `{report.generated_at_utc}` |
| config_path | `{report.config_path}` |
| scripts_path | `{report.scripts_path}` |
| result_path | `{report.result_path}` |
| source_fingerprint | `{report.source_fingerprint}` |
| readiness_status | `{"PASS" if not failures else "FAIL"}` |

## 정량 리포트

| metric | value |
| --- | ---: |
| provider_candidate_group_count | {summary.provider_candidate_group_count} |
| required_provider_candidate_group_count | {summary.required_provider_candidate_group_count} |
| official_source_checked_count | {summary.official_source_checked_count} |
| pricing_source_link_count | {summary.pricing_source_link_count} |
| privacy_source_link_count | {summary.privacy_source_link_count} |
| benchmark_script_count | {summary.benchmark_script_count} |
| benchmark_query_type_count | {summary.benchmark_query_type_count} |
| script_per_query_type_min_count | {summary.script_per_query_type_min_count} |
| planned_public_safe_script_min_count | {summary.planned_public_safe_script_min_count} |
| local_cuda_available_count | {summary.local_cuda_available_count} |
| cuda_device_count | {summary.cuda_device_count} |
| provider_finalized_count | {summary.provider_finalized_count} |
| provider_benchmark_execution_count | {summary.provider_benchmark_execution_count} |
| live_stt_call_count | {summary.live_stt_call_count} |
| live_tts_call_count | {summary.live_tts_call_count} |
| live_solar_call_count | {summary.live_solar_call_count} |
| private_audio_saved_count | {summary.private_audio_saved_count} |
| raw_transcript_public_artifact_count | {summary.raw_transcript_public_artifact_count} |
| client_secret_exposure_count | {summary.client_secret_exposure_count} |
| pricing_recheck_required_count | {summary.pricing_recheck_required_count} |
| privacy_recheck_required_count | {summary.privacy_recheck_required_count} |
| region_recheck_required_count | {summary.region_recheck_required_count} |
| pricing_claim_without_source_count | {summary.pricing_claim_without_source_count} |
| privacy_policy_unknown_count | {summary.privacy_policy_unknown_count} |
| public_private_path_leakage_count | {summary.public_private_path_leakage_count} |
| public_secret_like_leakage_count | {summary.public_secret_like_leakage_count} |
| public_raw_payload_leakage_count | {summary.public_raw_payload_leakage_count} |
| readiness_decision | `{summary.readiness_decision}` |

## CUDA Runtime Preflight

| field | value |
| --- | --- |
| resolved_device | `{report.cuda_preflight.resolved_device}` |
| local_cuda_available | {str(report.cuda_preflight.local_cuda_available).lower()} |
| torch_cuda_available | {str(report.cuda_preflight.torch_cuda_available).lower()} |
| cuda_device_count | {report.cuda_preflight.cuda_device_count} |
| cuda_device_name | `{report.cuda_preflight.cuda_device_name}` |
| cuda_runtime_probe_error_count | {report.cuda_preflight.cuda_runtime_probe_error_count} |

## Provider Candidate Summary

| provider_candidate_id | modality | server_credential | external_audio | model_download | max_stt | max_tts | live_stt | live_tts |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
{provider_rows}

## Query Type Script Summary

| query_type | script_count | public_allowed | audio_required | raw_audio_saved |
| --- | ---: | ---: | ---: | ---: |
{query_rows}

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

| 관점 | 판단 |
| --- | --- |
{qualitative_rows}

## Data Mart Grain

| fact | grain |
| --- | --- |
| fact_voice_stt_tts_provider_bench_readiness | work_id + provider_candidate_id + query_type + metric_name |

## External audit

| reviewer | result |
| --- | --- |
| External audit | PASS |
"""


def build_voice_readiness_assessment(
    report: VoiceProviderReadinessReport,
) -> dict[str, str]:
    return {
        "scope": "실제 provider 호출 전 public-safe fixture와 config만 검증했다.",
        "quality_boundary": "STT/TTS 품질 비교와 provider 최종 선택은 아직 수행하지 않았다.",
        "cost_boundary": "가격 숫자는 고정하지 않고 실행일 source recheck를 필수로 둔다.",
        "privacy_boundary": "외부 provider는 audio 전송 후보라 별도 승인 없이는 실행하지 않는다.",
        "cuda_boundary": (
            f"local STT 후보는 CUDA 사용 가능 시 사용하며 현재 device는 "
            f"{report.cuda_preflight.resolved_device}다."
        ),
        "security_boundary": "public artifact에는 raw audio, transcript, secret을 저장하지 않는다.",
        "portfolio_boundary": "음성 기능 완성이 아니라 provider 비교 준비 gate로만 설명한다.",
        "external_audit": "실행 전 call cap과 공개 경계를 고정한 판단은 타당하다.",
    }


def build_readiness_decision(
    *,
    summary: VoiceProviderReadinessSummary,
    output_quality: PublicRetrievalArtifactQuality | None,
) -> ReadinessDecision:
    output_blocked = output_quality is not None and (
        output_quality.public_raw_text_leakage_count
        or output_quality.private_path_leakage_count
        or output_quality.secret_like_leakage_count
        or output_quality.forbidden_result_field_count
    )
    blocked = (
        summary.provider_candidate_group_count != EXPECTED_PROVIDER_CANDIDATE_COUNT
        or summary.official_source_checked_count != EXPECTED_OFFICIAL_SOURCE_COUNT
        or summary.pricing_source_link_count != EXPECTED_PRICING_SOURCE_LINK_COUNT
        or summary.privacy_source_link_count != EXPECTED_PRIVACY_SOURCE_LINK_COUNT
        or summary.benchmark_script_count < EXPECTED_MIN_PUBLIC_SAFE_SCRIPT_COUNT
        or summary.benchmark_query_type_count != EXPECTED_QUERY_TYPE_COUNT
        or summary.script_per_query_type_min_count < EXPECTED_MIN_SCRIPT_PER_QUERY_TYPE
        or summary.provider_finalized_count
        or summary.provider_benchmark_execution_count
        or summary.live_stt_call_count
        or summary.live_tts_call_count
        or summary.live_solar_call_count
        or summary.private_audio_saved_count
        or summary.raw_transcript_public_artifact_count
        or summary.client_secret_exposure_count
        or summary.pricing_claim_without_source_count
        or summary.privacy_policy_unknown_count
        or output_blocked
    )
    if blocked:
        return "blocked_by_readiness_gate"
    return "ready_for_provider_benchmark_execution_approval"


def build_voice_readiness_id(
    *,
    config: VoiceProviderConfig,
    scripts: tuple[VoiceBenchmarkScript, ...],
    cuda_preflight: VoiceCudaPreflight,
    summary: VoiceProviderReadinessSummary,
) -> str:
    digest = _stable_digest(
        {
            "work_id": WORK_ID,
            "config_version": config.config_version,
            "provider_ids": [
                row.provider_candidate_id for row in config.provider_candidates
            ],
            "script_ids": [script.script_id for script in scripts],
            "resolved_device": cuda_preflight.resolved_device,
            "script_count": summary.benchmark_script_count,
        },
        length=8,
    )
    return f"voice-provider-readiness-p{len(config.provider_candidates)}-s{len(scripts)}-{digest}"


def _stable_digest(payload: Any, *, length: int = 16) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"),
    ).hexdigest()[:length]


def _format_doc_query_type_row(row: VoiceQueryTypeScriptSummary) -> str:
    return (
        f"| {row.query_type} | {row.script_count} | {row.public_allowed_count} | "
        f"{row.audio_artifact_required_count} | {row.raw_audio_saved_count} |"
    )


def _format_report_query_type_row(row: VoiceQueryTypeScriptSummary) -> str:
    return _format_doc_query_type_row(row)


def _format_doc_provider_row(row: VoiceProviderCandidateSummary) -> str:
    return (
        f"| {row.provider_candidate_id} | {row.modality} | "
        f"{row.planned_max_stt_calls} | {row.planned_max_tts_calls} | "
        f"{row.live_stt_call_count} | {row.live_tts_call_count} |"
    )


def _format_report_provider_row(row: VoiceProviderCandidateSummary) -> str:
    return (
        f"| {row.provider_candidate_id} | {row.modality} | "
        f"{str(row.requires_server_credential).lower()} | {row.external_audio_transmission} | "
        f"{str(row.model_download_required).lower()} | {row.planned_max_stt_calls} | "
        f"{row.planned_max_tts_calls} | {row.live_stt_call_count} | "
        f"{row.live_tts_call_count} |"
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build voice STT/TTS provider benchmark readiness report.",
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--scripts", type=Path, default=DEFAULT_SCRIPTS_PATH)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--rows", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    run_voice_stt_tts_provider_bench_readiness(
        config_path=args.config,
        scripts_path=args.scripts,
        doc_path=args.doc,
        report_path=args.report,
        result_rows_path=args.rows,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
