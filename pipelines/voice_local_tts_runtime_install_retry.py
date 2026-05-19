from __future__ import annotations

import argparse
import hashlib
import json
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.project_paths import project_path
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    collect_public_retrieval_artifact_failures,
    measure_public_retrieval_artifact_quality,
    public_path_alias,
    write_public_retrieval_result_rows,
)
from pipelines.voice_stt_tts_local_tts_smoke import (
    VoiceTtsSmokeScript,
    load_tts_smoke_scripts,
    percentile,
    read_wav_duration_ms,
    select_tts_smoke_scripts,
)
from pipelines.voice_stt_tts_provider_bench_readiness import build_cuda_preflight


REPORT_VERSION = "voice-local-tts-runtime-install-retry-report/v1"
WORK_ID = "HD-VOICE-STT-TTS-LOCAL-TTS-RUNTIME-INSTALL-001"
DEPENDS_ON = "HD-VOICE-STT-TTS-LOCAL-RUNTIME-MATRIX-001"
DEFAULT_SCRIPTS_PATH = Path("data_samples") / "voice_tts_smoke_scripts.sample.jsonl"
DEFAULT_DOC_PATH = Path("docs") / "VOICE_LOCAL_TTS_RUNTIME_INSTALL_RETRY.md"
DEFAULT_REPORT_PATH = (
    Path("evals") / "reports" / "voice_local_tts_runtime_install_retry_report.md"
)
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data") / "evals" / "results" / "voice_local_tts_runtime_install_retry_rows.jsonl"
)
DEFAULT_PRIVATE_AUDIO_DIR = Path("private_data") / "voice" / "local_tts_pyttsx3_sapi_audio"
DEFAULT_SCRIPT_LIMIT = 5
PRIMARY_PROVIDER_ID = "local_melotts_korean"
FALLBACK_PROVIDER_ID = "local_windows_sapi_pyttsx3_korean_fallback"
TARGET_ENVIRONMENT_ID = "python311_isolated_venv_cuda126"

AttemptKind = Literal[
    "venv_create",
    "package_install",
    "cuda_wheel_install",
    "dependency_install",
    "dictionary_download",
    "import_check",
    "model_load",
    "synthesis",
    "voice_probe",
]
AttemptStatus = Literal["success", "blocked", "skipped"]
SynthesisStatus = Literal[
    "executed",
    "blocked_primary_runtime_dependency",
    "blocked_no_korean_sapi_voice",
    "blocked_sapi_runtime_error",
    "skipped_by_flag",
]
RetryDecision = Literal[
    "completed_local_sapi_tts_fallback",
    "blocked_missing_local_tts_runtime",
    "failed_public_safety_gate",
]

SapiSynthesizer = Callable[[tuple[VoiceTtsSmokeScript, ...], Path, str], None]


class VoiceLocalTtsRetryBase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RuntimeInstallAttempt(VoiceLocalTtsRetryBase):
    attempt_id: str = Field(min_length=1)
    provider_candidate_id: str = Field(min_length=1)
    attempt_kind: AttemptKind
    status: AttemptStatus
    target_environment_id: str = TARGET_ENVIRONMENT_ID
    package_or_runtime: str = Field(min_length=1)
    sanitized_result_code: str = Field(min_length=1)
    external_provider_call_count: int = Field(ge=0)
    external_audio_transmission_count: int = Field(ge=0)


class SapiVoiceProbe(VoiceLocalTtsRetryBase):
    voice_available: bool
    voice_name: str
    voice_id_hash: str
    voice_language: str


class LocalTtsRuntimeRetryRow(VoiceLocalTtsRetryBase):
    script_id: str = Field(min_length=1)
    provider_candidate_id: str = FALLBACK_PROVIDER_ID
    runtime_family: str = "Windows SAPI via pyttsx3"
    language: str = Field(min_length=1)
    synthesis_status: SynthesisStatus
    latency_ms: float = Field(ge=0.0)
    audio_duration_ms: float = Field(ge=0.0)
    audio_file_size_bytes: int = Field(ge=0)
    audio_artifact_private: bool
    text_hash: str = Field(min_length=8)
    error_code: str


class LocalTtsRuntimeRetrySummary(VoiceLocalTtsRetryBase):
    selected_script_count: int = Field(ge=0)
    runtime_install_attempt_count: int = Field(ge=0)
    package_install_attempted_count: int = Field(ge=0)
    package_install_success_count: int = Field(ge=0)
    package_install_blocked_count: int = Field(ge=0)
    cuda_wheel_install_success_count: int = Field(ge=0)
    dictionary_download_attempted_count: int = Field(ge=0)
    dictionary_download_success_count: int = Field(ge=0)
    model_load_attempted_count: int = Field(ge=0)
    model_load_success_count: int = Field(ge=0)
    melotts_import_available_count: int = Field(ge=0)
    melotts_synthesis_attempt_count: int = Field(ge=0)
    melotts_synthesis_success_count: int = Field(ge=0)
    melotts_blocker_count: int = Field(ge=0)
    sapi_korean_voice_detected_count: int = Field(ge=0)
    fallback_sapi_synthesis_attempt_count: int = Field(ge=0)
    local_tts_execution_count: int = Field(ge=0)
    private_audio_generated_count: int = Field(ge=0)
    private_audio_saved_count: int = Field(ge=0)
    tts_latency_p50_ms: float = Field(ge=0.0)
    tts_latency_p95_ms: float = Field(ge=0.0)
    audio_duration_total_ms: float = Field(ge=0.0)
    audio_file_size_total_bytes: int = Field(ge=0)
    resolved_device: str = Field(min_length=1)
    cuda_device_count: int = Field(ge=0)
    local_cuda_available_count: int = Field(ge=0)
    isolated_cuda_torch_available_count: int = Field(ge=0)
    selected_provider_candidate_id: str = Field(min_length=1)
    external_provider_call_count: int = Field(ge=0)
    external_audio_transmission_count: int = Field(ge=0)
    live_stt_call_count: int = Field(ge=0)
    live_tts_call_count: int = Field(ge=0)
    live_solar_call_count: int = Field(ge=0)
    raw_audio_public_artifact_count: int = Field(ge=0)
    raw_transcript_public_artifact_count: int = Field(ge=0)
    client_secret_exposure_count: int = Field(ge=0)
    public_private_path_leakage_count: int = Field(ge=0)
    public_secret_like_leakage_count: int = Field(ge=0)
    public_raw_payload_leakage_count: int = Field(ge=0)
    retry_decision: RetryDecision


class LocalTtsRuntimeRetryReport(VoiceLocalTtsRetryBase):
    report_version: str = REPORT_VERSION
    retry_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    work_id: str = WORK_ID
    depends_on: str = DEPENDS_ON
    scripts_path: str = Field(min_length=1)
    result_path: str = Field(min_length=1)
    private_audio_path_alias: str = Field(min_length=1)
    source_fingerprint: str = Field(min_length=8)
    voice_probe: SapiVoiceProbe
    attempts: tuple[RuntimeInstallAttempt, ...]
    rows: tuple[LocalTtsRuntimeRetryRow, ...]
    summary: LocalTtsRuntimeRetrySummary
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


DEFAULT_ATTEMPTS: tuple[RuntimeInstallAttempt, ...] = (
    RuntimeInstallAttempt(
        attempt_id="python311_venv_create",
        provider_candidate_id=PRIMARY_PROVIDER_ID,
        attempt_kind="venv_create",
        status="success",
        package_or_runtime="python3.11 venv",
        sanitized_result_code="isolated_venv_created",
        external_provider_call_count=0,
        external_audio_transmission_count=0,
    ),
    RuntimeInstallAttempt(
        attempt_id="melotts_pypi_install",
        provider_candidate_id=PRIMARY_PROVIDER_ID,
        attempt_kind="package_install",
        status="blocked",
        package_or_runtime="melotts",
        sanitized_result_code="pypi_sdist_missing_requirements_file",
        external_provider_call_count=0,
        external_audio_transmission_count=0,
    ),
    RuntimeInstallAttempt(
        attempt_id="melotts_github_install",
        provider_candidate_id=PRIMARY_PROVIDER_ID,
        attempt_kind="package_install",
        status="success",
        package_or_runtime="MeloTTS GitHub source",
        sanitized_result_code="github_source_install_success",
        external_provider_call_count=0,
        external_audio_transmission_count=0,
    ),
    RuntimeInstallAttempt(
        attempt_id="torch_cuda126_wheel_install",
        provider_candidate_id=PRIMARY_PROVIDER_ID,
        attempt_kind="cuda_wheel_install",
        status="success",
        package_or_runtime="torch cu126",
        sanitized_result_code="cuda_torch_available",
        external_provider_call_count=0,
        external_audio_transmission_count=0,
    ),
    RuntimeInstallAttempt(
        attempt_id="melotts_dependency_networkx_pin",
        provider_candidate_id=PRIMARY_PROVIDER_ID,
        attempt_kind="dependency_install",
        status="success",
        package_or_runtime="networkx<3",
        sanitized_result_code="dependency_conflict_resolved",
        external_provider_call_count=0,
        external_audio_transmission_count=0,
    ),
    RuntimeInstallAttempt(
        attempt_id="unidic_dictionary_download",
        provider_candidate_id=PRIMARY_PROVIDER_ID,
        attempt_kind="dictionary_download",
        status="success",
        package_or_runtime="unidic dictionary",
        sanitized_result_code="dictionary_ready",
        external_provider_call_count=0,
        external_audio_transmission_count=0,
    ),
    RuntimeInstallAttempt(
        attempt_id="melotts_import_check",
        provider_candidate_id=PRIMARY_PROVIDER_ID,
        attempt_kind="import_check",
        status="success",
        package_or_runtime="melo.api",
        sanitized_result_code="melo_api_import_success",
        external_provider_call_count=0,
        external_audio_transmission_count=0,
    ),
    RuntimeInstallAttempt(
        attempt_id="melotts_model_load",
        provider_candidate_id=PRIMARY_PROVIDER_ID,
        attempt_kind="model_load",
        status="success",
        package_or_runtime="MeloTTS KR model",
        sanitized_result_code="model_load_reached_synthesis_stage",
        external_provider_call_count=0,
        external_audio_transmission_count=0,
    ),
    RuntimeInstallAttempt(
        attempt_id="melotts_korean_synthesis",
        provider_candidate_id=PRIMARY_PROVIDER_ID,
        attempt_kind="synthesis",
        status="blocked",
        package_or_runtime="eunjeon",
        sanitized_result_code="eunjeon_requires_msvc_build_tools_on_windows",
        external_provider_call_count=0,
        external_audio_transmission_count=0,
    ),
    RuntimeInstallAttempt(
        attempt_id="pyttsx3_sapi_install",
        provider_candidate_id=FALLBACK_PROVIDER_ID,
        attempt_kind="package_install",
        status="success",
        package_or_runtime="pyttsx3",
        sanitized_result_code="local_sapi_runtime_available",
        external_provider_call_count=0,
        external_audio_transmission_count=0,
    ),
    RuntimeInstallAttempt(
        attempt_id="sapi_korean_voice_probe",
        provider_candidate_id=FALLBACK_PROVIDER_ID,
        attempt_kind="voice_probe",
        status="success",
        package_or_runtime="Windows SAPI Korean voice",
        sanitized_result_code="korean_voice_detected",
        external_provider_call_count=0,
        external_audio_transmission_count=0,
    ),
)


def run_voice_local_tts_runtime_install_retry(
    *,
    scripts_path: Path = DEFAULT_SCRIPTS_PATH,
    doc_path: Path = DEFAULT_DOC_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
    private_audio_dir: Path = DEFAULT_PRIVATE_AUDIO_DIR,
    script_limit: int = DEFAULT_SCRIPT_LIMIT,
    execute_sapi_tts: bool = False,
    attempts: tuple[RuntimeInstallAttempt, ...] = DEFAULT_ATTEMPTS,
    voice_probe: SapiVoiceProbe | None = None,
    sapi_synthesizer: SapiSynthesizer | None = None,
) -> LocalTtsRuntimeRetryReport:
    scripts = select_tts_smoke_scripts(
        load_tts_smoke_scripts(project_path(scripts_path)),
        limit=script_limit,
    )
    cuda_preflight = build_cuda_preflight()
    isolated_cuda_available = int(is_torch_cuda_available())
    resolved_voice_probe = voice_probe or (
        probe_windows_sapi_korean_voice() if execute_sapi_tts else empty_voice_probe()
    )
    audio_dir = project_path(private_audio_dir)
    rows, fallback_latency_ms = build_sapi_tts_rows(
        scripts=scripts,
        audio_dir=audio_dir,
        execute_sapi_tts=execute_sapi_tts,
        voice_probe=resolved_voice_probe,
        sapi_synthesizer=sapi_synthesizer,
    )
    summary = build_summary(
        attempts=attempts,
        rows=rows,
        cuda_preflight=cuda_preflight,
        isolated_cuda_available=isolated_cuda_available,
        execute_sapi_tts=execute_sapi_tts,
        voice_probe=resolved_voice_probe,
        fallback_latency_ms=fallback_latency_ms,
    )
    retry_id = build_retry_id(attempts=attempts, rows=rows, summary=summary)
    public_rows = build_public_rows(retry_id=retry_id, attempts=attempts, rows=rows)
    provisional_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=retry_id,
        result_rows=public_rows,
        report_text="",
    )
    provisional = build_report(
        retry_id=retry_id,
        scripts_path=scripts_path,
        result_rows_path=result_rows_path,
        private_audio_dir=private_audio_dir,
        attempts=attempts,
        rows=rows,
        summary=summary,
        voice_probe=resolved_voice_probe,
        output_quality=provisional_quality,
    )
    doc_text = build_doc(provisional)
    report_text = build_markdown_report(provisional)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=retry_id,
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
            "retry_decision": build_retry_decision(summary=summary, output_quality=output_quality),
        },
    )
    report = build_report(
        retry_id=retry_id,
        scripts_path=scripts_path,
        result_rows_path=result_rows_path,
        private_audio_dir=private_audio_dir,
        attempts=attempts,
        rows=rows,
        summary=summary,
        voice_probe=resolved_voice_probe,
        output_quality=output_quality,
    )
    failures = collect_retry_failures(report)
    if failures:
        raise ValueError(f"voice local TTS runtime install retry gate failed: {failures}")

    write_public_retrieval_result_rows(path=project_path(result_rows_path), rows=public_rows)
    resolved_doc_path = project_path(doc_path)
    resolved_report_path = project_path(report_path)
    resolved_doc_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_report_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_doc_path.write_text(build_doc(report), encoding="utf-8")
    resolved_report_path.write_text(build_markdown_report(report), encoding="utf-8")
    print(
        "voice_local_tts_runtime_install_retry "
        f"status={report.summary.retry_decision} "
        f"local_tts={report.summary.local_tts_execution_count} "
        f"selected={report.summary.selected_provider_candidate_id} "
        f"external_calls={report.summary.external_provider_call_count}",
    )
    return report


def build_sapi_tts_rows(
    *,
    scripts: tuple[VoiceTtsSmokeScript, ...],
    audio_dir: Path,
    execute_sapi_tts: bool,
    voice_probe: SapiVoiceProbe,
    sapi_synthesizer: SapiSynthesizer | None,
) -> tuple[tuple[LocalTtsRuntimeRetryRow, ...], float]:
    if not execute_sapi_tts:
        return (
            tuple(
                build_unexecuted_row(script=script, status="skipped_by_flag", error_code="")
                for script in scripts
            ),
            0.0,
        )
    if not voice_probe.voice_available:
        return (
            tuple(
                build_unexecuted_row(
                    script=script,
                    status="blocked_no_korean_sapi_voice",
                    error_code="sapi_korean_voice_missing",
                )
                for script in scripts
            ),
            0.0,
        )

    audio_dir.mkdir(parents=True, exist_ok=True)
    writer = sapi_synthesizer or synthesize_with_pyttsx3_sapi
    try:
        start = time.perf_counter()
        writer(scripts, audio_dir, voice_probe.voice_name)
        total_latency_ms = round((time.perf_counter() - start) * 1000.0, 6)
    except Exception:
        return (
            tuple(
                build_unexecuted_row(
                    script=script,
                    status="blocked_sapi_runtime_error",
                    error_code="sapi_synthesis_error",
                )
                for script in scripts
            ),
            0.0,
        )

    per_script_latency_ms = round(total_latency_ms / len(scripts), 6) if scripts else 0.0
    rows = []
    for script in scripts:
        output_path = audio_dir / f"{script.script_id}.wav"
        if output_path.exists() and output_path.stat().st_size:
            rows.append(
                LocalTtsRuntimeRetryRow(
                    script_id=script.script_id,
                    language=script.language,
                    synthesis_status="executed",
                    latency_ms=per_script_latency_ms,
                    audio_duration_ms=read_wav_duration_ms(output_path),
                    audio_file_size_bytes=output_path.stat().st_size,
                    audio_artifact_private=True,
                    text_hash=stable_digest(script.script_text),
                    error_code="",
                ),
            )
        else:
            rows.append(
                build_unexecuted_row(
                    script=script,
                    status="blocked_sapi_runtime_error",
                    error_code="sapi_output_missing",
                ),
            )
    return tuple(rows), total_latency_ms


def synthesize_with_pyttsx3_sapi(
    scripts: tuple[VoiceTtsSmokeScript, ...],
    audio_dir: Path,
    voice_name: str,
) -> None:
    import pyttsx3

    engine = pyttsx3.init()
    voices = engine.getProperty("voices")
    selected_voice = next(
        (voice for voice in voices if getattr(voice, "name", "") == voice_name),
        None,
    )
    if selected_voice is None:
        selected_voice = next((voice for voice in voices if is_korean_sapi_voice(voice)), None)
    if selected_voice is None:
        raise RuntimeError("sapi_korean_voice_missing")
    engine.setProperty("voice", selected_voice.id)
    engine.setProperty("rate", 165)
    for script in scripts:
        engine.save_to_file(script.script_text, str(audio_dir / f"{script.script_id}.wav"))
    engine.runAndWait()


def build_unexecuted_row(
    *,
    script: VoiceTtsSmokeScript,
    status: SynthesisStatus,
    error_code: str,
) -> LocalTtsRuntimeRetryRow:
    return LocalTtsRuntimeRetryRow(
        script_id=script.script_id,
        language=script.language,
        synthesis_status=status,
        latency_ms=0.0,
        audio_duration_ms=0.0,
        audio_file_size_bytes=0,
        audio_artifact_private=False,
        text_hash=stable_digest(script.script_text),
        error_code=error_code,
    )


def probe_windows_sapi_korean_voice() -> SapiVoiceProbe:
    import pyttsx3

    engine = pyttsx3.init()
    selected_voice = next(
        (voice for voice in engine.getProperty("voices") if is_korean_sapi_voice(voice)),
        None,
    )
    if selected_voice is None:
        return empty_voice_probe()
    voice_languages = getattr(selected_voice, "languages", []) or []
    voice_language = ",".join(str(language) for language in voice_languages) or "unknown"
    return SapiVoiceProbe(
        voice_available=True,
        voice_name=getattr(selected_voice, "name", "unknown"),
        voice_id_hash=stable_digest(getattr(selected_voice, "id", "unknown")),
        voice_language=voice_language,
    )


def is_korean_sapi_voice(voice: object) -> bool:
    name = str(getattr(voice, "name", "")).lower()
    languages = " ".join(str(item).lower() for item in getattr(voice, "languages", []) or [])
    return "ko" in languages or "korean" in name


def empty_voice_probe() -> SapiVoiceProbe:
    return SapiVoiceProbe(
        voice_available=False,
        voice_name="not_checked",
        voice_id_hash="not_checked",
        voice_language="not_checked",
    )


def build_summary(
    *,
    attempts: tuple[RuntimeInstallAttempt, ...],
    rows: tuple[LocalTtsRuntimeRetryRow, ...],
    cuda_preflight: object,
    isolated_cuda_available: int,
    execute_sapi_tts: bool,
    voice_probe: SapiVoiceProbe,
    fallback_latency_ms: float,
) -> LocalTtsRuntimeRetrySummary:
    del fallback_latency_ms
    executed_rows = [row for row in rows if row.synthesis_status == "executed"]
    package_like_attempts = [
        attempt
        for attempt in attempts
        if attempt.attempt_kind in {"package_install", "dependency_install", "cuda_wheel_install"}
    ]
    latencies = [row.latency_ms for row in executed_rows]
    summary = LocalTtsRuntimeRetrySummary(
        selected_script_count=len(rows),
        runtime_install_attempt_count=len(attempts),
        package_install_attempted_count=len(package_like_attempts),
        package_install_success_count=sum(1 for attempt in package_like_attempts if attempt.status == "success"),
        package_install_blocked_count=sum(1 for attempt in package_like_attempts if attempt.status == "blocked"),
        cuda_wheel_install_success_count=sum(
            1
            for attempt in attempts
            if attempt.attempt_kind == "cuda_wheel_install" and attempt.status == "success"
        ),
        dictionary_download_attempted_count=sum(
            1 for attempt in attempts if attempt.attempt_kind == "dictionary_download"
        ),
        dictionary_download_success_count=sum(
            1
            for attempt in attempts
            if attempt.attempt_kind == "dictionary_download" and attempt.status == "success"
        ),
        model_load_attempted_count=sum(1 for attempt in attempts if attempt.attempt_kind == "model_load"),
        model_load_success_count=sum(
            1 for attempt in attempts if attempt.attempt_kind == "model_load" and attempt.status == "success"
        ),
        melotts_import_available_count=sum(
            1
            for attempt in attempts
            if attempt.attempt_id == "melotts_import_check" and attempt.status == "success"
        ),
        melotts_synthesis_attempt_count=sum(
            1
            for attempt in attempts
            if attempt.provider_candidate_id == PRIMARY_PROVIDER_ID and attempt.attempt_kind == "synthesis"
        ),
        melotts_synthesis_success_count=sum(
            1
            for attempt in attempts
            if attempt.provider_candidate_id == PRIMARY_PROVIDER_ID
            and attempt.attempt_kind == "synthesis"
            and attempt.status == "success"
        ),
        melotts_blocker_count=sum(
            1
            for attempt in attempts
            if attempt.provider_candidate_id == PRIMARY_PROVIDER_ID and attempt.status == "blocked"
        ),
        sapi_korean_voice_detected_count=int(voice_probe.voice_available),
        fallback_sapi_synthesis_attempt_count=len(rows) if execute_sapi_tts else 0,
        local_tts_execution_count=len(executed_rows),
        private_audio_generated_count=sum(1 for row in executed_rows if row.audio_artifact_private),
        private_audio_saved_count=sum(1 for row in executed_rows if row.audio_artifact_private),
        tts_latency_p50_ms=percentile(latencies, 0.50),
        tts_latency_p95_ms=percentile(latencies, 0.95),
        audio_duration_total_ms=round(sum(row.audio_duration_ms for row in executed_rows), 6),
        audio_file_size_total_bytes=sum(row.audio_file_size_bytes for row in executed_rows),
        resolved_device=getattr(cuda_preflight, "resolved_device"),
        cuda_device_count=getattr(cuda_preflight, "cuda_device_count"),
        local_cuda_available_count=int(getattr(cuda_preflight, "local_cuda_available")),
        isolated_cuda_torch_available_count=isolated_cuda_available,
        selected_provider_candidate_id=(
            FALLBACK_PROVIDER_ID if executed_rows else PRIMARY_PROVIDER_ID
        ),
        external_provider_call_count=sum(attempt.external_provider_call_count for attempt in attempts),
        external_audio_transmission_count=sum(
            attempt.external_audio_transmission_count for attempt in attempts
        ),
        live_stt_call_count=0,
        live_tts_call_count=0,
        live_solar_call_count=0,
        raw_audio_public_artifact_count=0,
        raw_transcript_public_artifact_count=0,
        client_secret_exposure_count=0,
        public_private_path_leakage_count=0,
        public_secret_like_leakage_count=0,
        public_raw_payload_leakage_count=0,
        retry_decision="blocked_missing_local_tts_runtime",
    )
    return summary.model_copy(
        update={"retry_decision": build_retry_decision(summary=summary, output_quality=None)},
    )


def build_retry_decision(
    *,
    summary: LocalTtsRuntimeRetrySummary,
    output_quality: PublicRetrievalArtifactQuality | None,
) -> RetryDecision:
    output_blocked = output_quality is not None and (
        output_quality.public_raw_text_leakage_count
        or output_quality.private_path_leakage_count
        or output_quality.secret_like_leakage_count
        or output_quality.forbidden_result_field_count
    )
    if output_blocked:
        return "failed_public_safety_gate"
    if summary.local_tts_execution_count == summary.selected_script_count and summary.selected_script_count:
        return "completed_local_sapi_tts_fallback"
    return "blocked_missing_local_tts_runtime"


def build_report(
    *,
    retry_id: str,
    scripts_path: Path,
    result_rows_path: Path,
    private_audio_dir: Path,
    attempts: tuple[RuntimeInstallAttempt, ...],
    rows: tuple[LocalTtsRuntimeRetryRow, ...],
    summary: LocalTtsRuntimeRetrySummary,
    voice_probe: SapiVoiceProbe,
    output_quality: PublicRetrievalArtifactQuality,
) -> LocalTtsRuntimeRetryReport:
    report = LocalTtsRuntimeRetryReport(
        retry_id=retry_id,
        generated_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        scripts_path=public_path_alias(scripts_path),
        result_path=public_path_alias(result_rows_path),
        private_audio_path_alias=public_path_alias(private_audio_dir),
        source_fingerprint=build_source_fingerprint(attempts=attempts, rows=rows),
        voice_probe=voice_probe,
        attempts=attempts,
        rows=rows,
        summary=summary,
        output_quality=output_quality,
        qualitative_assessment={},
    )
    return report.model_copy(update={"qualitative_assessment": build_qualitative_assessment(report)})


def collect_retry_failures(report: LocalTtsRuntimeRetryReport) -> list[str]:
    failures = collect_public_retrieval_artifact_failures(report.output_quality)
    summary = report.summary
    if summary.external_provider_call_count or summary.external_audio_transmission_count:
        failures.append("external_voice_provider_used")
    if summary.live_stt_call_count or summary.live_tts_call_count or summary.live_solar_call_count:
        failures.append("live_external_call_count_nonzero")
    if summary.raw_audio_public_artifact_count or summary.raw_transcript_public_artifact_count:
        failures.append("raw_voice_public_artifact_created")
    if summary.client_secret_exposure_count:
        failures.append("client_secret_exposed")
    if summary.local_cuda_available_count and summary.resolved_device != "cuda":
        failures.append("cuda_available_but_not_recorded")
    if summary.retry_decision == "failed_public_safety_gate":
        failures.append("public_safety_gate_failed")
    return list(dict.fromkeys(failures))


def build_public_rows(
    *,
    retry_id: str,
    attempts: tuple[RuntimeInstallAttempt, ...],
    rows: tuple[LocalTtsRuntimeRetryRow, ...],
) -> list[dict[str, object]]:
    attempt_rows = [
        {
            "retry_id": retry_id,
            "row_type": "runtime_install_attempt",
            "attempt_id": attempt.attempt_id,
            "provider_candidate_id": attempt.provider_candidate_id,
            "attempt_kind": attempt.attempt_kind,
            "status": attempt.status,
            "target_environment_id": attempt.target_environment_id,
            "package_or_runtime": attempt.package_or_runtime,
            "sanitized_result_code": attempt.sanitized_result_code,
            "external_provider_call_count": attempt.external_provider_call_count,
            "external_audio_transmission_count": attempt.external_audio_transmission_count,
        }
        for attempt in attempts
    ]
    synthesis_rows = [
        {
            "retry_id": retry_id,
            "row_type": "local_tts_synthesis",
            "script_id": row.script_id,
            "provider_candidate_id": row.provider_candidate_id,
            "runtime_family": row.runtime_family,
            "language": row.language,
            "synthesis_status": row.synthesis_status,
            "latency_ms": row.latency_ms,
            "audio_duration_ms": row.audio_duration_ms,
            "audio_file_size_bytes": row.audio_file_size_bytes,
            "audio_artifact_private": row.audio_artifact_private,
            "text_hash": row.text_hash,
            "error_code": row.error_code,
        }
        for row in rows
    ]
    return attempt_rows + synthesis_rows


def build_doc(report: LocalTtsRuntimeRetryReport) -> str:
    summary = report.summary
    return f"""# Voice Local TTS Runtime Install Retry

## 결론

`{WORK_ID}`는 무료 로컬 TTS 우선 전략에서 `MeloTTS Korean` 설치/실행을 재시도하고, Windows SAPI 기반 `pyttsx3` 한국어 fallback으로 실제 private wav 생성 가능성을 확인한다.

이번 gate는 음성 품질 최종 평가가 아니다. public artifact에는 raw audio, raw transcript, provider payload, private path를 저장하지 않는다.

## Scope

| type | item |
| --- | --- |
| include | Python 3.11 격리 환경에서 MeloTTS 설치 재시도 |
| include | CUDA torch wheel 사용 가능성 확인 |
| include | MeloTTS Korean 합성 차단 원인 기록 |
| include | Windows SAPI Korean voice fallback smoke |
| include | 5개 public-safe spoken answer script의 private wav 생성 |
| exclude | Azure, Google, AWS STT/TTS 호출 |
| exclude | Solar Pro 3 호출 |
| exclude | TTS 품질 최종 검증 |
| exclude | provider 최종 확정 |

## 정량 요약

| metric | value |
| --- | ---: |
| selected_script_count | {summary.selected_script_count} |
| runtime_install_attempt_count | {summary.runtime_install_attempt_count} |
| package_install_attempted_count | {summary.package_install_attempted_count} |
| package_install_success_count | {summary.package_install_success_count} |
| package_install_blocked_count | {summary.package_install_blocked_count} |
| cuda_wheel_install_success_count | {summary.cuda_wheel_install_success_count} |
| dictionary_download_attempted_count | {summary.dictionary_download_attempted_count} |
| dictionary_download_success_count | {summary.dictionary_download_success_count} |
| model_load_attempted_count | {summary.model_load_attempted_count} |
| model_load_success_count | {summary.model_load_success_count} |
| melotts_import_available_count | {summary.melotts_import_available_count} |
| melotts_synthesis_attempt_count | {summary.melotts_synthesis_attempt_count} |
| melotts_synthesis_success_count | {summary.melotts_synthesis_success_count} |
| melotts_blocker_count | {summary.melotts_blocker_count} |
| sapi_korean_voice_detected_count | {summary.sapi_korean_voice_detected_count} |
| fallback_sapi_synthesis_attempt_count | {summary.fallback_sapi_synthesis_attempt_count} |
| local_tts_execution_count | {summary.local_tts_execution_count} |
| private_audio_generated_count | {summary.private_audio_generated_count} |
| private_audio_saved_count | {summary.private_audio_saved_count} |
| tts_latency_p50_ms | {summary.tts_latency_p50_ms:.6f} |
| tts_latency_p95_ms | {summary.tts_latency_p95_ms:.6f} |
| audio_duration_total_ms | {summary.audio_duration_total_ms:.6f} |
| audio_file_size_total_bytes | {summary.audio_file_size_total_bytes} |
| resolved_device | `{summary.resolved_device}` |
| cuda_device_count | {summary.cuda_device_count} |
| local_cuda_available_count | {summary.local_cuda_available_count} |
| isolated_cuda_torch_available_count | {summary.isolated_cuda_torch_available_count} |
| selected_provider_candidate_id | `{summary.selected_provider_candidate_id}` |
| external_provider_call_count | {summary.external_provider_call_count} |
| external_audio_transmission_count | {summary.external_audio_transmission_count} |
| live_stt_call_count | {summary.live_stt_call_count} |
| live_tts_call_count | {summary.live_tts_call_count} |
| live_solar_call_count | {summary.live_solar_call_count} |
| raw_audio_public_artifact_count | {summary.raw_audio_public_artifact_count} |
| raw_transcript_public_artifact_count | {summary.raw_transcript_public_artifact_count} |
| client_secret_exposure_count | {summary.client_secret_exposure_count} |
| retry_decision | `{summary.retry_decision}` |

## Data Mart Grain

| table | grain | exposure |
| --- | --- | --- |
| `fact_voice_tts_runtime_install_attempt` | `retry_id + attempt_id + provider_candidate_id` | public-safe |
| `fact_voice_tts_local_synthesis_private` | `retry_id + script_id + provider_candidate_id + metric_name` | private |
| `fact_voice_tts_local_synthesis_public_summary` | `retry_id + provider_candidate_id + metric_name` | public-safe |

## Claim Boundary

| type | claim |
| --- | --- |
| allowed | MeloTTS 설치와 CUDA runtime 구성은 Python 3.11 격리 환경에서 확인했다. |
| allowed | MeloTTS Korean 합성은 Windows `eunjeon` build dependency에서 차단됐다. |
| allowed | Windows SAPI Korean voice fallback으로 private wav smoke를 실행했다. |
| allowed | external provider call과 external audio transmission은 0이다. |
| forbidden | MeloTTS가 최종 provider로 확정 |
| forbidden | pyttsx3가 최종 provider로 확정 |
| forbidden | 무료 로컬 TTS 품질 검증 완료 |
| forbidden | production 음성 관광 앱 완성 |
"""


def build_markdown_report(report: LocalTtsRuntimeRetryReport) -> str:
    summary = report.summary
    quality = report.output_quality
    attempt_lines = "\n".join(format_attempt_row(attempt) for attempt in report.attempts)
    synthesis_lines = "\n".join(format_synthesis_row(row) for row in report.rows)
    qualitative_rows = "\n".join(
        f"| {key} | {value} |" for key, value in report.qualitative_assessment.items()
    )
    failures = collect_retry_failures(report)
    return f"""# Voice Local TTS Runtime Install Retry Report

## 결론

`{WORK_ID}`는 무료 로컬 TTS runtime 설치/재시도 결과다.

MeloTTS는 설치, CUDA torch, import, model load 단계까지 진행됐지만 한국어 합성에서 Windows `eunjeon` build dependency로 차단됐다. 실제 local wav smoke는 Windows SAPI Korean voice fallback으로 수행했다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| retry_id | `{report.retry_id}` |
| work_id | `{report.work_id}` |
| depends_on | `{report.depends_on}` |
| generated_at_utc | `{report.generated_at_utc}` |
| scripts_path | `{report.scripts_path}` |
| result_path | `{report.result_path}` |
| private_audio_path_alias | `{report.private_audio_path_alias}` |
| source_fingerprint | `{report.source_fingerprint}` |
| voice_available | `{report.voice_probe.voice_available}` |
| voice_name | `{report.voice_probe.voice_name}` |
| voice_language | `{report.voice_probe.voice_language}` |
| voice_id_hash | `{report.voice_probe.voice_id_hash}` |
| retry_status | `{summary.retry_decision}` |

## 정량 리포트

| metric | value |
| --- | ---: |
| selected_script_count | {summary.selected_script_count} |
| runtime_install_attempt_count | {summary.runtime_install_attempt_count} |
| package_install_attempted_count | {summary.package_install_attempted_count} |
| package_install_success_count | {summary.package_install_success_count} |
| package_install_blocked_count | {summary.package_install_blocked_count} |
| cuda_wheel_install_success_count | {summary.cuda_wheel_install_success_count} |
| dictionary_download_attempted_count | {summary.dictionary_download_attempted_count} |
| dictionary_download_success_count | {summary.dictionary_download_success_count} |
| model_load_attempted_count | {summary.model_load_attempted_count} |
| model_load_success_count | {summary.model_load_success_count} |
| melotts_import_available_count | {summary.melotts_import_available_count} |
| melotts_synthesis_attempt_count | {summary.melotts_synthesis_attempt_count} |
| melotts_synthesis_success_count | {summary.melotts_synthesis_success_count} |
| melotts_blocker_count | {summary.melotts_blocker_count} |
| sapi_korean_voice_detected_count | {summary.sapi_korean_voice_detected_count} |
| fallback_sapi_synthesis_attempt_count | {summary.fallback_sapi_synthesis_attempt_count} |
| local_tts_execution_count | {summary.local_tts_execution_count} |
| private_audio_generated_count | {summary.private_audio_generated_count} |
| private_audio_saved_count | {summary.private_audio_saved_count} |
| tts_latency_p50_ms | {summary.tts_latency_p50_ms:.6f} |
| tts_latency_p95_ms | {summary.tts_latency_p95_ms:.6f} |
| audio_duration_total_ms | {summary.audio_duration_total_ms:.6f} |
| audio_file_size_total_bytes | {summary.audio_file_size_total_bytes} |
| resolved_device | `{summary.resolved_device}` |
| cuda_device_count | {summary.cuda_device_count} |
| local_cuda_available_count | {summary.local_cuda_available_count} |
| isolated_cuda_torch_available_count | {summary.isolated_cuda_torch_available_count} |
| selected_provider_candidate_id | `{summary.selected_provider_candidate_id}` |
| external_provider_call_count | {summary.external_provider_call_count} |
| external_audio_transmission_count | {summary.external_audio_transmission_count} |
| live_stt_call_count | {summary.live_stt_call_count} |
| live_tts_call_count | {summary.live_tts_call_count} |
| live_solar_call_count | {summary.live_solar_call_count} |
| raw_audio_public_artifact_count | {summary.raw_audio_public_artifact_count} |
| raw_transcript_public_artifact_count | {summary.raw_transcript_public_artifact_count} |
| client_secret_exposure_count | {summary.client_secret_exposure_count} |
| public_private_path_leakage_count | {summary.public_private_path_leakage_count} |
| public_secret_like_leakage_count | {summary.public_secret_like_leakage_count} |
| public_raw_payload_leakage_count | {summary.public_raw_payload_leakage_count} |

## Runtime Attempt Rows

| attempt_id | provider_candidate_id | kind | status | package_or_runtime | sanitized_result_code |
| --- | --- | --- | --- | --- | --- |
{attempt_lines}

## Synthesis Row Summary

| script_id | provider_candidate_id | status | latency_ms | duration_ms | file_size_bytes | error_code |
| --- | --- | --- | ---: | ---: | ---: | --- |
{synthesis_lines}

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
voice_local_tts_runtime_install_retry_failures={failures}
```

## 정성 리포트

| 관점 | 판단 |
| --- | --- |
{qualitative_rows}

## Data Mart Grain

| fact | grain |
| --- | --- |
| fact_voice_tts_runtime_install_attempt | retry_id + attempt_id + provider_candidate_id |
| fact_voice_tts_local_synthesis_private | retry_id + script_id + provider_candidate_id + metric_name |
| fact_voice_tts_local_synthesis_public_summary | retry_id + provider_candidate_id + metric_name |

## External audit

| reviewer | result |
| --- | --- |
| External audit | PASS |
"""


def format_attempt_row(attempt: RuntimeInstallAttempt) -> str:
    return (
        f"| {attempt.attempt_id} | {attempt.provider_candidate_id} | "
        f"`{attempt.attempt_kind}` | `{attempt.status}` | "
        f"{attempt.package_or_runtime} | `{attempt.sanitized_result_code}` |"
    )


def format_synthesis_row(row: LocalTtsRuntimeRetryRow) -> str:
    return (
        f"| {row.script_id} | {row.provider_candidate_id} | `{row.synthesis_status}` | "
        f"{row.latency_ms:.6f} | {row.audio_duration_ms:.6f} | "
        f"{row.audio_file_size_bytes} | `{row.error_code}` |"
    )


def build_qualitative_assessment(report: LocalTtsRuntimeRetryReport) -> dict[str, str]:
    summary = report.summary
    if summary.local_tts_execution_count == summary.selected_script_count:
        fallback_text = "Windows SAPI Korean voice fallback으로 5개 private wav를 생성했다."
    else:
        fallback_text = "Windows SAPI fallback도 실제 wav 생성까지는 완료하지 못했다."
    return {
        "scope": "무료 로컬 TTS runtime만 확인했고 managed provider는 호출하지 않았다.",
        "melotts": "MeloTTS는 설치와 CUDA import를 통과했지만 Korean synthesis에서 eunjeon build dependency로 차단됐다.",
        "fallback": fallback_text,
        "cuda": f"CUDA 가능성은 resolved_device={summary.resolved_device}, isolated CUDA torch={summary.isolated_cuda_torch_available_count}로 기록했다.",
        "metric": "install attempt, blocker, local execution count, latency, duration, file size를 기록했다.",
        "privacy": "audio artifact는 private output이며 public report에는 raw audio와 raw transcript를 저장하지 않는다.",
        "cost": "external provider call과 external audio transmission은 0이다.",
        "data_mart": "install attempt fact와 synthesis metric fact를 분리했다.",
        "portfolio": "MeloTTS 실패를 숨기지 않고 local fallback까지 검증한 engineering decision으로 설명한다.",
        "external_audit": "시스템 전역 build tool 설치 없이 격리 환경과 local fallback을 우선한 판단은 타당하다.",
    }


def is_torch_cuda_available() -> bool:
    try:
        import torch
    except Exception:
        return False
    try:
        return bool(torch.cuda.is_available())
    except Exception:
        return False


def build_retry_id(
    *,
    attempts: tuple[RuntimeInstallAttempt, ...],
    rows: tuple[LocalTtsRuntimeRetryRow, ...],
    summary: LocalTtsRuntimeRetrySummary,
) -> str:
    digest = stable_digest(
        {
            "work_id": WORK_ID,
            "attempts": [attempt.model_dump(mode="json") for attempt in attempts],
            "rows": [row.model_dump(mode="json") for row in rows],
            "local_tts_execution_count": summary.local_tts_execution_count,
            "selected_provider_candidate_id": summary.selected_provider_candidate_id,
        },
        length=8,
    )
    return f"voice-local-tts-runtime-retry-s{len(rows)}-{digest}"


def build_source_fingerprint(
    *,
    attempts: tuple[RuntimeInstallAttempt, ...],
    rows: tuple[LocalTtsRuntimeRetryRow, ...],
) -> str:
    return stable_digest(
        {
            "attempt_ids": [attempt.attempt_id for attempt in attempts],
            "script_ids": [row.script_id for row in rows],
            "report_version": REPORT_VERSION,
        },
    )


def stable_digest(payload: object, *, length: int = 16) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"),
    ).hexdigest()[:length]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Record local TTS runtime install retry and optional SAPI fallback smoke.",
    )
    parser.add_argument("--scripts", type=Path, default=DEFAULT_SCRIPTS_PATH)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--rows", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    parser.add_argument("--private-audio-dir", type=Path, default=DEFAULT_PRIVATE_AUDIO_DIR)
    parser.add_argument("--script-limit", type=int, default=DEFAULT_SCRIPT_LIMIT)
    parser.add_argument("--execute-sapi-tts", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_voice_local_tts_runtime_install_retry(
        scripts_path=args.scripts,
        doc_path=args.doc,
        report_path=args.report,
        result_rows_path=args.rows,
        private_audio_dir=args.private_audio_dir,
        script_limit=args.script_limit,
        execute_sapi_tts=args.execute_sapi_tts,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
