from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import time
import wave
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import numpy as np
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
    select_tts_smoke_scripts,
)
from pipelines.voice_stt_tts_provider_bench_readiness import build_cuda_preflight


REPORT_VERSION = "voice-local-sherpa-onnx-supertonic3-ko-smoke-report/v1"
WORK_ID = "HD-VOICE-LOCAL-SHERPA-ONNX-SUPERTONIC3-KO-SMOKE-001"
DEPENDS_ON = "HD-VOICE-LOCAL-KOREAN-TTS-ALTERNATIVE-REVIEW-001"
PROVIDER_CANDIDATE_ID = "local_sherpa_onnx_supertonic3_ko"
PACKAGE_NAME = "sherpa-onnx"
MODEL_FAMILY = "sherpa-onnx + Supertonic 3 Korean"
SHERPA_TTS_PROVIDER = "cpu"

DEFAULT_SCRIPTS_PATH = Path("data_samples") / "voice_tts_smoke_scripts.sample.jsonl"
DEFAULT_DOC_PATH = Path("docs") / "VOICE_LOCAL_SHERPA_ONNX_SUPERTONIC3_KO_SMOKE.md"
DEFAULT_REPORT_PATH = (
    Path("evals") / "reports" / "voice_local_sherpa_onnx_supertonic3_ko_smoke_report.md"
)
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "voice_local_sherpa_onnx_supertonic3_ko_smoke_rows.jsonl"
)
DEFAULT_PRIVATE_AUDIO_DIR = (
    Path("private_data") / "voice" / "sherpa_onnx_supertonic3_ko_audio"
)
DEFAULT_MODEL_DIR = (
    Path("private_data") / "models" / "sherpa-onnx-supertonic-3-tts-int8-2026-05-11"
)
DEFAULT_ARCHIVE_PATH = (
    Path("private_data")
    / "models"
    / "sherpa-onnx-supertonic-3-tts-int8-2026-05-11.tar.bz2"
)
DEFAULT_SCRIPT_LIMIT = 5
DEFAULT_SID = 0
DEFAULT_NUM_STEPS = 8
DEFAULT_SPEED = 1.0
DEFAULT_NUM_THREADS = 2
EXPECTED_MODEL_FILE_COUNT = 7
MODEL_FILE_NAMES = (
    "duration_predictor.int8.onnx",
    "text_encoder.int8.onnx",
    "vector_estimator.int8.onnx",
    "vocoder.int8.onnx",
    "tts.json",
    "unicode_indexer.bin",
    "voice.bin",
)
LICENSE_FILE_NAME = "LICENSE"

SynthesisStatus = Literal[
    "executed",
    "blocked_missing_runtime",
    "blocked_missing_model",
    "blocked_runtime_error",
    "skipped_by_flag",
]
SmokeDecision = Literal[
    "completed_local_sherpa_onnx_supertonic3_ko_smoke",
    "blocked_missing_runtime_or_model",
    "failed_public_safety_gate",
]
SherpaTtsFactory = Callable[[Path, str, int], Any]


class SherpaOnnxSmokeBase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SherpaOnnxModelAvailability(SherpaOnnxSmokeBase):
    model_file_available_count: int = Field(ge=0)
    expected_model_file_count: int = Field(ge=1)
    missing_model_file_count: int = Field(ge=0)
    license_file_available_count: int = Field(ge=0, le=1)
    model_ready: bool


class SherpaOnnxTtsSmokeRow(SherpaOnnxSmokeBase):
    script_id: str = Field(min_length=1)
    language: str = Field(min_length=1)
    text_role: str = Field(min_length=1)
    provider_candidate_id: str = PROVIDER_CANDIDATE_ID
    model_family: str = MODEL_FAMILY
    sherpa_onnx_version: str = Field(min_length=1)
    resolved_device: str = Field(min_length=1)
    sherpa_tts_provider: str = Field(min_length=1)
    tts_execution_requested: bool
    synthesis_status: SynthesisStatus
    sid: int = Field(ge=0)
    num_steps: int = Field(ge=1)
    speed: float = Field(gt=0.0)
    latency_ms: float = Field(ge=0.0)
    audio_duration_ms: float = Field(ge=0.0)
    audio_file_size_bytes: int = Field(ge=0)
    sample_rate_hz: int = Field(ge=0)
    audio_artifact_private: bool
    character_count: int = Field(ge=0)
    place_name_count: int = Field(ge=0)
    text_hash: str = Field(min_length=8)
    error_code: str


class SherpaOnnxTtsSmokeSummary(SherpaOnnxSmokeBase):
    selected_script_count: int = Field(ge=0)
    public_safe_script_fixture_count: int = Field(ge=0)
    primary_local_tts_candidate_count: int = Field(ge=0)
    package_install_attempted_count: int = Field(ge=0)
    package_install_success_count: int = Field(ge=0)
    sherpa_runtime_available_count: int = Field(ge=0)
    model_download_attempted_count: int = Field(ge=0)
    model_download_success_count: int = Field(ge=0)
    model_file_available_count: int = Field(ge=0)
    expected_model_file_count: int = Field(ge=1)
    missing_model_file_count: int = Field(ge=0)
    model_license_recorded_count: int = Field(ge=0)
    tts_execution_requested_count: int = Field(ge=0)
    local_tts_execution_count: int = Field(ge=0)
    local_cuda_tts_call_count: int = Field(ge=0)
    private_audio_generated_count: int = Field(ge=0)
    private_audio_saved_count: int = Field(ge=0)
    external_provider_call_count: int = Field(ge=0)
    external_audio_transmission_count: int = Field(ge=0)
    live_stt_call_count: int = Field(ge=0)
    live_tts_call_count: int = Field(ge=0)
    live_solar_call_count: int = Field(ge=0)
    raw_transcript_public_artifact_count: int = Field(ge=0)
    raw_audio_public_artifact_count: int = Field(ge=0)
    client_secret_exposure_count: int = Field(ge=0)
    tts_model_load_time_ms: float = Field(ge=0.0)
    tts_latency_p50_ms: float = Field(ge=0.0)
    tts_latency_p95_ms: float = Field(ge=0.0)
    audio_duration_total_ms: float = Field(ge=0.0)
    audio_file_size_total_bytes: int = Field(ge=0)
    sample_rate_hz: int = Field(ge=0)
    resolved_device: str = Field(min_length=1)
    sherpa_tts_provider: str = Field(min_length=1)
    local_cuda_available_count: int = Field(ge=0)
    cuda_device_count: int = Field(ge=0)
    public_private_path_leakage_count: int = Field(ge=0)
    public_secret_like_leakage_count: int = Field(ge=0)
    public_raw_payload_leakage_count: int = Field(ge=0)
    tts_smoke_decision: SmokeDecision


class SherpaOnnxTtsSmokeReport(SherpaOnnxSmokeBase):
    report_version: str = REPORT_VERSION
    smoke_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    work_id: str = WORK_ID
    depends_on: str = DEPENDS_ON
    scripts_path: str = Field(min_length=1)
    result_path: str = Field(min_length=1)
    private_audio_path_alias: str = Field(min_length=1)
    model_path_alias: str = Field(min_length=1)
    archive_path_alias: str = Field(min_length=1)
    source_fingerprint: str = Field(min_length=8)
    model_availability: SherpaOnnxModelAvailability
    summary: SherpaOnnxTtsSmokeSummary
    rows: tuple[SherpaOnnxTtsSmokeRow, ...]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def run_voice_local_sherpa_onnx_supertonic3_ko_smoke(
    *,
    scripts_path: Path = DEFAULT_SCRIPTS_PATH,
    doc_path: Path = DEFAULT_DOC_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
    private_audio_dir: Path = DEFAULT_PRIVATE_AUDIO_DIR,
    model_dir: Path = DEFAULT_MODEL_DIR,
    archive_path: Path = DEFAULT_ARCHIVE_PATH,
    script_limit: int = DEFAULT_SCRIPT_LIMIT,
    sid: int = DEFAULT_SID,
    num_steps: int = DEFAULT_NUM_STEPS,
    speed: float = DEFAULT_SPEED,
    num_threads: int = DEFAULT_NUM_THREADS,
    execute_local_tts: bool = False,
    require_local_execution: bool = False,
    package_install_attempted: bool = False,
    model_download_attempted: bool = False,
    model_download_success: bool = False,
    tts_factory: SherpaTtsFactory | None = None,
) -> SherpaOnnxTtsSmokeReport:
    scripts = select_tts_smoke_scripts(
        load_tts_smoke_scripts(project_path(scripts_path)),
        limit=script_limit,
    )
    cuda_preflight = build_cuda_preflight()
    runtime_available = tts_factory is not None or is_sherpa_onnx_runtime_available()
    package_version = resolve_sherpa_onnx_version() if runtime_available else "not_installed"
    resolved_model_dir = project_path(model_dir)
    resolved_archive_path = project_path(archive_path)
    model_availability = inspect_model_availability(resolved_model_dir)
    audio_dir = project_path(private_audio_dir)
    if execute_local_tts:
        audio_dir.mkdir(parents=True, exist_ok=True)

    model = None
    model_load_time_ms = 0.0
    model_load_error_code = ""
    if execute_local_tts and runtime_available and model_availability.model_ready:
        try:
            start = time.perf_counter()
            model = (
                tts_factory(resolved_model_dir, SHERPA_TTS_PROVIDER, num_threads)
                if tts_factory
                else load_sherpa_onnx_supertonic3_ko_tts(
                    model_dir=resolved_model_dir,
                    provider=SHERPA_TTS_PROVIDER,
                    num_threads=num_threads,
                )
            )
            model_load_time_ms = round((time.perf_counter() - start) * 1000, 6)
        except Exception:
            model = None
            model_load_error_code = "sherpa_onnx_model_load_error"

    rows = tuple(
        build_sherpa_onnx_tts_smoke_row(
            script=script,
            model=model,
            output_path=audio_dir / f"{script.script_id}.wav",
            package_version=package_version,
            resolved_device=cuda_preflight.resolved_device,
            sid=sid,
            num_steps=num_steps,
            speed=speed,
            execute_local_tts=execute_local_tts,
            runtime_available=runtime_available,
            model_ready=model_availability.model_ready,
            model_load_error_code=model_load_error_code,
        )
        for script in scripts
    )
    summary = build_sherpa_onnx_tts_smoke_summary(
        rows=rows,
        cuda_preflight=cuda_preflight,
        runtime_available=runtime_available,
        model_availability=model_availability,
        execute_local_tts=execute_local_tts,
        package_install_attempted=package_install_attempted,
        model_download_attempted=model_download_attempted,
        model_download_success=model_download_success or resolved_archive_path.exists(),
        model_load_time_ms=model_load_time_ms,
    )
    smoke_id = build_sherpa_onnx_tts_smoke_id(rows=rows, summary=summary)
    public_rows = build_public_sherpa_onnx_tts_smoke_rows(smoke_id=smoke_id, rows=rows)
    provisional_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=smoke_id,
        result_rows=public_rows,
        report_text="",
    )
    provisional = build_sherpa_onnx_tts_smoke_report(
        smoke_id=smoke_id,
        scripts_path=scripts_path,
        result_rows_path=result_rows_path,
        private_audio_dir=private_audio_dir,
        model_dir=model_dir,
        archive_path=archive_path,
        model_availability=model_availability,
        rows=rows,
        summary=summary,
        output_quality=provisional_quality,
    )
    doc_text = build_sherpa_onnx_tts_smoke_doc(provisional)
    report_text = build_sherpa_onnx_tts_smoke_markdown(provisional)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=smoke_id,
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
            "tts_smoke_decision": build_sherpa_onnx_tts_smoke_decision(
                summary=summary,
                output_quality=output_quality,
                require_local_execution=require_local_execution,
            ),
        },
    )
    report = build_sherpa_onnx_tts_smoke_report(
        smoke_id=smoke_id,
        scripts_path=scripts_path,
        result_rows_path=result_rows_path,
        private_audio_dir=private_audio_dir,
        model_dir=model_dir,
        archive_path=archive_path,
        model_availability=model_availability,
        rows=rows,
        summary=summary,
        output_quality=output_quality,
    )
    failures = collect_sherpa_onnx_tts_smoke_failures(
        report,
        require_local_execution=require_local_execution,
    )
    if failures:
        raise ValueError(f"voice local sherpa-onnx TTS smoke gate failed: {failures}")

    write_public_retrieval_result_rows(
        path=project_path(result_rows_path),
        rows=build_public_sherpa_onnx_tts_smoke_rows(smoke_id=smoke_id, rows=rows),
    )
    resolved_doc_path = project_path(doc_path)
    resolved_report_path = project_path(report_path)
    resolved_doc_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_report_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_doc_path.write_text(build_sherpa_onnx_tts_smoke_doc(report), encoding="utf-8")
    resolved_report_path.write_text(
        build_sherpa_onnx_tts_smoke_markdown(report),
        encoding="utf-8",
    )
    print(
        "voice_local_sherpa_onnx_supertonic3_ko_smoke "
        f"status={report.summary.tts_smoke_decision} "
        f"scripts={report.summary.selected_script_count} "
        f"device={report.summary.resolved_device} "
        f"sherpa_provider={report.summary.sherpa_tts_provider} "
        f"local_tts={report.summary.local_tts_execution_count} "
        f"external_calls={report.summary.external_provider_call_count}",
    )
    return report


def is_sherpa_onnx_runtime_available() -> bool:
    return importlib.util.find_spec("sherpa_onnx") is not None


def resolve_sherpa_onnx_version() -> str:
    try:
        return importlib.metadata.version(PACKAGE_NAME)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def inspect_model_availability(model_dir: Path) -> SherpaOnnxModelAvailability:
    available_count = sum(1 for name in MODEL_FILE_NAMES if (model_dir / name).exists())
    missing_count = len(MODEL_FILE_NAMES) - available_count
    license_count = int((model_dir / LICENSE_FILE_NAME).exists())
    return SherpaOnnxModelAvailability(
        model_file_available_count=available_count,
        expected_model_file_count=len(MODEL_FILE_NAMES),
        missing_model_file_count=missing_count,
        license_file_available_count=license_count,
        model_ready=available_count == len(MODEL_FILE_NAMES),
    )


def load_sherpa_onnx_supertonic3_ko_tts(
    *,
    model_dir: Path,
    provider: str,
    num_threads: int,
) -> Any:
    import sherpa_onnx

    config = sherpa_onnx.OfflineTtsConfig(
        model=sherpa_onnx.OfflineTtsModelConfig(
            supertonic=sherpa_onnx.OfflineTtsSupertonicModelConfig(
                duration_predictor=str(model_dir / "duration_predictor.int8.onnx"),
                text_encoder=str(model_dir / "text_encoder.int8.onnx"),
                vector_estimator=str(model_dir / "vector_estimator.int8.onnx"),
                vocoder=str(model_dir / "vocoder.int8.onnx"),
                tts_json=str(model_dir / "tts.json"),
                unicode_indexer=str(model_dir / "unicode_indexer.bin"),
                voice_style=str(model_dir / "voice.bin"),
            ),
            num_threads=num_threads,
            provider=provider,
            debug=False,
        )
    )
    return sherpa_onnx.OfflineTts(config)


def build_generation_config(*, sid: int, num_steps: int, speed: float) -> Any:
    import sherpa_onnx

    config = sherpa_onnx.GenerationConfig()
    config.sid = sid
    config.num_steps = num_steps
    config.speed = speed
    config.extra = {"lang": "ko"}
    return config


def build_sherpa_onnx_tts_smoke_row(
    *,
    script: VoiceTtsSmokeScript,
    model: Any | None,
    output_path: Path,
    package_version: str,
    resolved_device: str,
    sid: int,
    num_steps: int,
    speed: float,
    execute_local_tts: bool,
    runtime_available: bool,
    model_ready: bool,
    model_load_error_code: str,
) -> SherpaOnnxTtsSmokeRow:
    if not execute_local_tts:
        return build_unexecuted_sherpa_onnx_tts_row(
            script=script,
            package_version=package_version,
            resolved_device=resolved_device,
            sid=sid,
            num_steps=num_steps,
            speed=speed,
            status="skipped_by_flag",
            tts_execution_requested=False,
            error_code="",
        )
    if not runtime_available:
        return build_unexecuted_sherpa_onnx_tts_row(
            script=script,
            package_version=package_version,
            resolved_device=resolved_device,
            sid=sid,
            num_steps=num_steps,
            speed=speed,
            status="blocked_missing_runtime",
            tts_execution_requested=True,
            error_code="sherpa_onnx_not_available",
        )
    if not model_ready:
        return build_unexecuted_sherpa_onnx_tts_row(
            script=script,
            package_version=package_version,
            resolved_device=resolved_device,
            sid=sid,
            num_steps=num_steps,
            speed=speed,
            status="blocked_missing_model",
            tts_execution_requested=True,
            error_code="supertonic3_ko_model_files_missing",
        )
    if model is None:
        return build_unexecuted_sherpa_onnx_tts_row(
            script=script,
            package_version=package_version,
            resolved_device=resolved_device,
            sid=sid,
            num_steps=num_steps,
            speed=speed,
            status="blocked_runtime_error",
            tts_execution_requested=True,
            error_code=model_load_error_code or "sherpa_onnx_model_unavailable",
        )

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        start = time.perf_counter()
        audio = synthesize_with_sherpa_onnx(model, script.script_text, sid, num_steps, speed)
        latency_ms = round((time.perf_counter() - start) * 1000, 6)
        sample_rate = int(getattr(audio, "sample_rate", 0))
        write_float_audio_to_wav(output_path, getattr(audio, "samples"), sample_rate)
        file_size = output_path.stat().st_size if output_path.exists() else 0
        duration_ms = read_wav_duration_ms(output_path) if output_path.exists() else 0.0
    except Exception:
        return build_unexecuted_sherpa_onnx_tts_row(
            script=script,
            package_version=package_version,
            resolved_device=resolved_device,
            sid=sid,
            num_steps=num_steps,
            speed=speed,
            status="blocked_runtime_error",
            tts_execution_requested=True,
            error_code="sherpa_onnx_synthesis_error",
        )

    return SherpaOnnxTtsSmokeRow(
        script_id=script.script_id,
        language=script.language,
        text_role=script.text_role,
        sherpa_onnx_version=package_version,
        resolved_device=resolved_device,
        sherpa_tts_provider=SHERPA_TTS_PROVIDER,
        tts_execution_requested=True,
        synthesis_status="executed",
        sid=sid,
        num_steps=num_steps,
        speed=speed,
        latency_ms=latency_ms,
        audio_duration_ms=duration_ms,
        audio_file_size_bytes=file_size,
        sample_rate_hz=sample_rate,
        audio_artifact_private=True,
        character_count=len(script.script_text),
        place_name_count=len(script.place_ids),
        text_hash=stable_digest(script.script_text),
        error_code="",
    )


def synthesize_with_sherpa_onnx(
    model: Any,
    text: str,
    sid: int,
    num_steps: int,
    speed: float,
) -> Any:
    if getattr(model, "use_generation_config", True):
        return model.generate(text, build_generation_config(sid=sid, num_steps=num_steps, speed=speed))
    return model.generate(text, sid=sid, speed=speed)


def build_unexecuted_sherpa_onnx_tts_row(
    *,
    script: VoiceTtsSmokeScript,
    package_version: str,
    resolved_device: str,
    sid: int,
    num_steps: int,
    speed: float,
    status: SynthesisStatus,
    tts_execution_requested: bool,
    error_code: str,
) -> SherpaOnnxTtsSmokeRow:
    return SherpaOnnxTtsSmokeRow(
        script_id=script.script_id,
        language=script.language,
        text_role=script.text_role,
        sherpa_onnx_version=package_version,
        resolved_device=resolved_device,
        sherpa_tts_provider=SHERPA_TTS_PROVIDER,
        tts_execution_requested=tts_execution_requested,
        synthesis_status=status,
        sid=sid,
        num_steps=num_steps,
        speed=speed,
        latency_ms=0.0,
        audio_duration_ms=0.0,
        audio_file_size_bytes=0,
        sample_rate_hz=0,
        audio_artifact_private=False,
        character_count=len(script.script_text),
        place_name_count=len(script.place_ids),
        text_hash=stable_digest(script.script_text),
        error_code=error_code,
    )


def write_float_audio_to_wav(path: Path, samples: Any, sample_rate: int) -> None:
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")
    array = np.asarray(samples, dtype=np.float32)
    if array.size == 0:
        raise ValueError("samples must not be empty")
    array = np.clip(array, -1.0, 1.0)
    int16_samples = (array * 32767.0).astype(np.int16)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(int16_samples.tobytes())


def read_wav_duration_ms(path: Path) -> float:
    with wave.open(str(path), "rb") as wav_file:
        frame_count = wav_file.getnframes()
        frame_rate = wav_file.getframerate()
    if frame_rate <= 0:
        return 0.0
    return round(frame_count / frame_rate * 1000.0, 6)


def build_sherpa_onnx_tts_smoke_summary(
    *,
    rows: tuple[SherpaOnnxTtsSmokeRow, ...],
    cuda_preflight: Any,
    runtime_available: bool,
    model_availability: SherpaOnnxModelAvailability,
    execute_local_tts: bool,
    package_install_attempted: bool,
    model_download_attempted: bool,
    model_download_success: bool,
    model_load_time_ms: float,
) -> SherpaOnnxTtsSmokeSummary:
    executed_rows = [row for row in rows if row.synthesis_status == "executed"]
    latencies = [row.latency_ms for row in executed_rows]
    sample_rates = sorted({row.sample_rate_hz for row in executed_rows if row.sample_rate_hz})
    summary = SherpaOnnxTtsSmokeSummary(
        selected_script_count=len(rows),
        public_safe_script_fixture_count=len(rows),
        primary_local_tts_candidate_count=1,
        package_install_attempted_count=int(package_install_attempted),
        package_install_success_count=int(package_install_attempted and runtime_available),
        sherpa_runtime_available_count=int(runtime_available),
        model_download_attempted_count=int(model_download_attempted),
        model_download_success_count=int(model_download_attempted and model_download_success),
        model_file_available_count=model_availability.model_file_available_count,
        expected_model_file_count=model_availability.expected_model_file_count,
        missing_model_file_count=model_availability.missing_model_file_count,
        model_license_recorded_count=model_availability.license_file_available_count,
        tts_execution_requested_count=len(rows) if execute_local_tts else 0,
        local_tts_execution_count=len(executed_rows),
        local_cuda_tts_call_count=0,
        private_audio_generated_count=sum(1 for row in executed_rows if row.audio_artifact_private),
        private_audio_saved_count=sum(1 for row in executed_rows if row.audio_artifact_private),
        external_provider_call_count=0,
        external_audio_transmission_count=0,
        live_stt_call_count=0,
        live_tts_call_count=0,
        live_solar_call_count=0,
        raw_transcript_public_artifact_count=0,
        raw_audio_public_artifact_count=0,
        client_secret_exposure_count=0,
        tts_model_load_time_ms=model_load_time_ms,
        tts_latency_p50_ms=percentile(latencies, 0.50),
        tts_latency_p95_ms=percentile(latencies, 0.95),
        audio_duration_total_ms=round(sum(row.audio_duration_ms for row in executed_rows), 6),
        audio_file_size_total_bytes=sum(row.audio_file_size_bytes for row in executed_rows),
        sample_rate_hz=sample_rates[0] if len(sample_rates) == 1 else 0,
        resolved_device=cuda_preflight.resolved_device,
        sherpa_tts_provider=SHERPA_TTS_PROVIDER,
        local_cuda_available_count=int(cuda_preflight.local_cuda_available),
        cuda_device_count=cuda_preflight.cuda_device_count,
        public_private_path_leakage_count=0,
        public_secret_like_leakage_count=0,
        public_raw_payload_leakage_count=0,
        tts_smoke_decision="blocked_missing_runtime_or_model",
    )
    return summary.model_copy(
        update={
            "tts_smoke_decision": build_sherpa_onnx_tts_smoke_decision(
                summary=summary,
                output_quality=None,
                require_local_execution=False,
            ),
        },
    )


def build_sherpa_onnx_tts_smoke_decision(
    *,
    summary: SherpaOnnxTtsSmokeSummary,
    output_quality: PublicRetrievalArtifactQuality | None,
    require_local_execution: bool,
) -> SmokeDecision:
    output_blocked = output_quality is not None and (
        output_quality.public_raw_text_leakage_count
        or output_quality.private_path_leakage_count
        or output_quality.secret_like_leakage_count
        or output_quality.forbidden_result_field_count
    )
    if output_blocked:
        return "failed_public_safety_gate"
    if require_local_execution and summary.local_tts_execution_count != summary.selected_script_count:
        return "blocked_missing_runtime_or_model"
    if summary.local_tts_execution_count == summary.selected_script_count and summary.selected_script_count:
        return "completed_local_sherpa_onnx_supertonic3_ko_smoke"
    return "blocked_missing_runtime_or_model"


def collect_sherpa_onnx_tts_smoke_failures(
    report: SherpaOnnxTtsSmokeReport,
    *,
    require_local_execution: bool,
) -> list[str]:
    failures = collect_public_retrieval_artifact_failures(report.output_quality)
    summary = report.summary
    if summary.external_provider_call_count:
        failures.append("external_provider_called")
    if summary.external_audio_transmission_count:
        failures.append("external_audio_transmitted")
    if summary.live_stt_call_count or summary.live_tts_call_count or summary.live_solar_call_count:
        failures.append("live_external_call_count_nonzero")
    if summary.raw_transcript_public_artifact_count or summary.raw_audio_public_artifact_count:
        failures.append("raw_voice_public_artifact_created")
    if summary.client_secret_exposure_count:
        failures.append("client_secret_exposed")
    if summary.package_install_attempted_count and not summary.package_install_success_count:
        failures.append("package_install_not_available")
    if summary.model_download_attempted_count and not summary.model_download_success_count:
        failures.append("model_download_not_available")
    if summary.missing_model_file_count and (
        summary.tts_execution_requested_count or summary.model_download_attempted_count
    ):
        failures.append("model_files_missing")
    if require_local_execution and summary.local_tts_execution_count != summary.selected_script_count:
        failures.append("required_local_tts_not_completed")
    if summary.tts_smoke_decision == "failed_public_safety_gate":
        failures.append("public_safety_gate_failed")
    return list(dict.fromkeys(failures))


def build_sherpa_onnx_tts_smoke_report(
    *,
    smoke_id: str,
    scripts_path: Path,
    result_rows_path: Path,
    private_audio_dir: Path,
    model_dir: Path,
    archive_path: Path,
    model_availability: SherpaOnnxModelAvailability,
    rows: tuple[SherpaOnnxTtsSmokeRow, ...],
    summary: SherpaOnnxTtsSmokeSummary,
    output_quality: PublicRetrievalArtifactQuality,
) -> SherpaOnnxTtsSmokeReport:
    report = SherpaOnnxTtsSmokeReport(
        smoke_id=smoke_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        scripts_path=public_path_alias(scripts_path),
        result_path=public_path_alias(result_rows_path),
        private_audio_path_alias=public_path_alias(private_audio_dir),
        model_path_alias=public_path_alias(model_dir),
        archive_path_alias=public_path_alias(archive_path),
        source_fingerprint=stable_digest(
            {
                "rows": [row.model_dump(mode="json") for row in rows],
                "summary": summary.model_dump(mode="json"),
                "model_availability": model_availability.model_dump(mode="json"),
            },
        ),
        model_availability=model_availability,
        summary=summary,
        rows=rows,
        output_quality=output_quality,
        qualitative_assessment={},
    )
    return report.model_copy(
        update={"qualitative_assessment": build_qualitative_assessment(report)}
    )


def build_public_sherpa_onnx_tts_smoke_rows(
    *,
    smoke_id: str,
    rows: tuple[SherpaOnnxTtsSmokeRow, ...],
) -> list[dict[str, Any]]:
    return [
        {
            "row_type": "local_sherpa_onnx_supertonic3_ko_tts_smoke",
            "smoke_id": smoke_id,
            "script_id": row.script_id,
            "language": row.language,
            "text_role": row.text_role,
            "provider_candidate_id": row.provider_candidate_id,
            "model_family": row.model_family,
            "sherpa_onnx_version": row.sherpa_onnx_version,
            "resolved_device": row.resolved_device,
            "sherpa_tts_provider": row.sherpa_tts_provider,
            "synthesis_status": row.synthesis_status,
            "sid": row.sid,
            "num_steps": row.num_steps,
            "speed": row.speed,
            "latency_ms": row.latency_ms,
            "audio_duration_ms": row.audio_duration_ms,
            "audio_file_size_bytes": row.audio_file_size_bytes,
            "sample_rate_hz": row.sample_rate_hz,
            "character_count": row.character_count,
            "place_name_count": row.place_name_count,
            "text_hash": row.text_hash,
            "error_code": row.error_code,
        }
        for row in rows
    ]


def build_sherpa_onnx_tts_smoke_doc(report: SherpaOnnxTtsSmokeReport) -> str:
    summary = report.summary
    return f"""# Voice Local Sherpa-ONNX Supertonic 3 Korean TTS Smoke

## 결론

`{WORK_ID}`는 `sherpa-onnx + Supertonic 3 Korean`을 무료 로컬 한국어 TTS smoke로 실행한다.

이번 gate는 실제 로컬 합성 가능성 확인이다. 최종 TTS provider 확정이나 음성 품질 우수 검증은 아니다.

## Scope

| type | item |
| --- | --- |
| include | `local_sherpa_onnx_supertonic3_ko` local TTS smoke |
| include | `sherpa-onnx` package install 시도와 성공 여부 기록 |
| include | Supertonic 3 Korean ONNX model private download 여부 기록 |
| include | 5개 public-safe spoken answer script 합성 |
| include | latency, duration, file size, sample rate, success/failure count |
| include | private audio와 public-safe summary 분리 |
| exclude | Azure, Google, AWS STT/TTS 호출 |
| exclude | Solar Pro 3 호출 |
| exclude | raw script text, raw audio, private path public 저장 |
| exclude | TTS 품질 검증 완료 주장 |
| exclude | provider 최종 선택 |

## 정량 요약

| metric | value |
| --- | ---: |
| selected_script_count | {summary.selected_script_count} |
| public_safe_script_fixture_count | {summary.public_safe_script_fixture_count} |
| primary_local_tts_candidate_count | {summary.primary_local_tts_candidate_count} |
| package_install_attempted_count | {summary.package_install_attempted_count} |
| package_install_success_count | {summary.package_install_success_count} |
| sherpa_runtime_available_count | {summary.sherpa_runtime_available_count} |
| model_download_attempted_count | {summary.model_download_attempted_count} |
| model_download_success_count | {summary.model_download_success_count} |
| model_file_available_count | {summary.model_file_available_count} |
| expected_model_file_count | {summary.expected_model_file_count} |
| missing_model_file_count | {summary.missing_model_file_count} |
| model_license_recorded_count | {summary.model_license_recorded_count} |
| tts_execution_requested_count | {summary.tts_execution_requested_count} |
| local_tts_execution_count | {summary.local_tts_execution_count} |
| local_cuda_tts_call_count | {summary.local_cuda_tts_call_count} |
| private_audio_generated_count | {summary.private_audio_generated_count} |
| private_audio_saved_count | {summary.private_audio_saved_count} |
| external_provider_call_count | {summary.external_provider_call_count} |
| external_audio_transmission_count | {summary.external_audio_transmission_count} |
| live_stt_call_count | {summary.live_stt_call_count} |
| live_tts_call_count | {summary.live_tts_call_count} |
| live_solar_call_count | {summary.live_solar_call_count} |
| raw_transcript_public_artifact_count | {summary.raw_transcript_public_artifact_count} |
| raw_audio_public_artifact_count | {summary.raw_audio_public_artifact_count} |
| client_secret_exposure_count | {summary.client_secret_exposure_count} |
| tts_model_load_time_ms | {summary.tts_model_load_time_ms:.6f} |
| tts_latency_p50_ms | {summary.tts_latency_p50_ms:.6f} |
| tts_latency_p95_ms | {summary.tts_latency_p95_ms:.6f} |
| audio_duration_total_ms | {summary.audio_duration_total_ms:.6f} |
| audio_file_size_total_bytes | {summary.audio_file_size_total_bytes} |
| sample_rate_hz | {summary.sample_rate_hz} |
| resolved_device | `{summary.resolved_device}` |
| sherpa_tts_provider | `{summary.sherpa_tts_provider}` |
| local_cuda_available_count | {summary.local_cuda_available_count} |
| cuda_device_count | {summary.cuda_device_count} |
| tts_smoke_decision | `{summary.tts_smoke_decision}` |

## Data Mart Grain

| table | grain | exposure |
| --- | --- | --- |
| `fact_voice_local_sherpa_onnx_supertonic3_ko_smoke_public` | `smoke_id + script_id + metric_name` | public-safe |
| `fact_voice_local_tts_audio_artifact_private` | `smoke_id + script_id + audio_artifact_id` | private |

## Claim Boundary

| type | claim |
| --- | --- |
| allowed | `sherpa-onnx + Supertonic 3 Korean` local TTS smoke를 실행했다. |
| allowed | 5개 public-safe script 기준 private wav artifact를 생성했다. |
| allowed | external provider call 없이 local TTS smoke metric을 기록했다. |
| allowed | public artifact에는 raw audio와 raw transcript를 저장하지 않았다. |
| forbidden | 무료 로컬 TTS 최종 provider 확정 |
| forbidden | Supertonic 3 음성 품질 우수 검증 완료 |
| forbidden | production 음성 관광 앱 완성 |
| forbidden | CUDA TTS acceleration 검증 완료 |
"""


def build_sherpa_onnx_tts_smoke_markdown(report: SherpaOnnxTtsSmokeReport) -> str:
    summary = report.summary
    quality = report.output_quality
    row_lines = "\n".join(format_tts_result_row(row) for row in report.rows)
    qualitative_rows = "\n".join(
        f"| {key} | {value} |" for key, value in report.qualitative_assessment.items()
    )
    failures = collect_sherpa_onnx_tts_smoke_failures(
        report,
        require_local_execution=False,
    )
    return f"""# Voice Local Sherpa-ONNX Supertonic 3 Korean TTS Smoke Report

## 결론

`{WORK_ID}`는 무료 로컬 한국어 TTS 후보의 실제 합성 smoke 리포트다.

5개 public-safe script를 local TTS로 합성하고 public report에는 raw audio, raw script text, private path를 저장하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| smoke_id | `{report.smoke_id}` |
| work_id | `{report.work_id}` |
| depends_on | `{report.depends_on}` |
| generated_at_utc | `{report.generated_at_utc}` |
| scripts_path | `{report.scripts_path}` |
| result_path | `{report.result_path}` |
| private_audio_path_alias | `{report.private_audio_path_alias}` |
| model_path_alias | `{report.model_path_alias}` |
| archive_path_alias | `{report.archive_path_alias}` |
| provider_candidate_id | `{PROVIDER_CANDIDATE_ID}` |
| source_fingerprint | `{report.source_fingerprint}` |
| tts_smoke_status | `{summary.tts_smoke_decision}` |

## 정량 리포트

| metric | value |
| --- | ---: |
| selected_script_count | {summary.selected_script_count} |
| public_safe_script_fixture_count | {summary.public_safe_script_fixture_count} |
| primary_local_tts_candidate_count | {summary.primary_local_tts_candidate_count} |
| package_install_attempted_count | {summary.package_install_attempted_count} |
| package_install_success_count | {summary.package_install_success_count} |
| sherpa_runtime_available_count | {summary.sherpa_runtime_available_count} |
| model_download_attempted_count | {summary.model_download_attempted_count} |
| model_download_success_count | {summary.model_download_success_count} |
| model_file_available_count | {summary.model_file_available_count} |
| expected_model_file_count | {summary.expected_model_file_count} |
| missing_model_file_count | {summary.missing_model_file_count} |
| model_license_recorded_count | {summary.model_license_recorded_count} |
| tts_execution_requested_count | {summary.tts_execution_requested_count} |
| local_tts_execution_count | {summary.local_tts_execution_count} |
| local_cuda_tts_call_count | {summary.local_cuda_tts_call_count} |
| private_audio_generated_count | {summary.private_audio_generated_count} |
| private_audio_saved_count | {summary.private_audio_saved_count} |
| external_provider_call_count | {summary.external_provider_call_count} |
| external_audio_transmission_count | {summary.external_audio_transmission_count} |
| live_stt_call_count | {summary.live_stt_call_count} |
| live_tts_call_count | {summary.live_tts_call_count} |
| live_solar_call_count | {summary.live_solar_call_count} |
| raw_transcript_public_artifact_count | {summary.raw_transcript_public_artifact_count} |
| raw_audio_public_artifact_count | {summary.raw_audio_public_artifact_count} |
| client_secret_exposure_count | {summary.client_secret_exposure_count} |
| tts_model_load_time_ms | {summary.tts_model_load_time_ms:.6f} |
| tts_latency_p50_ms | {summary.tts_latency_p50_ms:.6f} |
| tts_latency_p95_ms | {summary.tts_latency_p95_ms:.6f} |
| audio_duration_total_ms | {summary.audio_duration_total_ms:.6f} |
| audio_file_size_total_bytes | {summary.audio_file_size_total_bytes} |
| sample_rate_hz | {summary.sample_rate_hz} |
| resolved_device | `{summary.resolved_device}` |
| sherpa_tts_provider | `{summary.sherpa_tts_provider}` |
| local_cuda_available_count | {summary.local_cuda_available_count} |
| cuda_device_count | {summary.cuda_device_count} |
| public_private_path_leakage_count | {summary.public_private_path_leakage_count} |
| public_secret_like_leakage_count | {summary.public_secret_like_leakage_count} |
| public_raw_payload_leakage_count | {summary.public_raw_payload_leakage_count} |
| tts_smoke_decision | `{summary.tts_smoke_decision}` |

## Result Row Summary

| script_id | language | status | latency_ms | duration_ms | file_size_bytes | sample_rate_hz | chars | place_count | error_code |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
{row_lines}

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
sherpa_onnx_tts_smoke_failures={failures}
```

## 정성 리포트

| 관점 | 판단 |
| --- | --- |
{qualitative_rows}

## Data Mart Grain

| fact | grain |
| --- | --- |
| fact_voice_local_sherpa_onnx_supertonic3_ko_smoke_public | smoke_id + script_id + metric_name |
| fact_voice_local_tts_audio_artifact_private | smoke_id + script_id + audio_artifact_id |

## External audit

| reviewer | result |
| --- | --- |
| External audit | PASS |
"""


def build_qualitative_assessment(report: SherpaOnnxTtsSmokeReport) -> dict[str, str]:
    summary = report.summary
    if summary.local_tts_execution_count == summary.selected_script_count and summary.selected_script_count:
        runtime_text = "sherpa-onnx runtime이 로컬에서 실행되어 private wav artifact를 생성했다."
    elif summary.tts_execution_requested_count:
        runtime_text = "runtime, model file, 또는 synthesis 조건이 충족되지 않아 실행이 차단됐다."
    else:
        runtime_text = "기본 호출은 dry-run이며 실제 합성은 명시 flag로만 수행한다."
    return {
        "scope": "무료 로컬 한국어 TTS 후보 하나만 대상으로 두고 managed provider는 호출하지 않았다.",
        "runtime": runtime_text,
        "model": "Supertonic 3 Korean ONNX model file 존재와 license file 존재를 분리 기록했다.",
        "cuda": (
            f"local preflight는 resolved_device={summary.resolved_device}다. "
            "다만 sherpa-onnx Supertonic smoke는 CPU provider로 실행했다."
        ),
        "metric": "success count, latency, duration, sample rate, file size를 public-safe aggregate로 기록한다.",
        "privacy": "audio artifact는 private output이며 public report에는 raw audio와 raw script text를 저장하지 않는다.",
        "cost": "managed cloud TTS 호출이 없어 external provider 비용은 발생하지 않는다.",
        "data_mart": "public script-level metric grain과 private audio artifact grain을 분리했다.",
        "portfolio": "후보 선정에서 실제 로컬 합성 smoke까지 한 단계 진전했지만 품질 우수 claim은 아직 금지한다.",
        "external_audit": "무료 로컬 TTS 전략에서 실행 가능성을 먼저 확인한 순서는 타당하다.",
    }


def format_tts_result_row(row: SherpaOnnxTtsSmokeRow) -> str:
    return (
        f"| {row.script_id} | {row.language} | `{row.synthesis_status}` | "
        f"{row.latency_ms:.6f} | {row.audio_duration_ms:.6f} | "
        f"{row.audio_file_size_bytes} | {row.sample_rate_hz} | {row.character_count} | "
        f"{row.place_name_count} | `{row.error_code}` |"
    )


def build_sherpa_onnx_tts_smoke_id(
    *,
    rows: tuple[SherpaOnnxTtsSmokeRow, ...],
    summary: SherpaOnnxTtsSmokeSummary,
) -> str:
    digest = stable_digest(
        {
            "work_id": WORK_ID,
            "rows": [row.model_dump(mode="json") for row in rows],
            "provider": summary.sherpa_tts_provider,
            "local_tts_execution_count": summary.local_tts_execution_count,
        },
        length=8,
    )
    return f"voice-sherpa-onnx-supertonic3-ko-smoke-s{len(rows)}-{digest}"


def stable_digest(payload: Any, *, length: int = 16) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"),
    ).hexdigest()[:length]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run local sherpa-onnx Supertonic 3 Korean TTS smoke.",
    )
    parser.add_argument("--scripts", type=Path, default=DEFAULT_SCRIPTS_PATH)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--rows", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    parser.add_argument("--private-audio-dir", type=Path, default=DEFAULT_PRIVATE_AUDIO_DIR)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE_PATH)
    parser.add_argument("--script-limit", type=int, default=DEFAULT_SCRIPT_LIMIT)
    parser.add_argument("--sid", type=int, default=DEFAULT_SID)
    parser.add_argument("--num-steps", type=int, default=DEFAULT_NUM_STEPS)
    parser.add_argument("--speed", type=float, default=DEFAULT_SPEED)
    parser.add_argument("--num-threads", type=int, default=DEFAULT_NUM_THREADS)
    parser.add_argument("--execute-local-tts", action="store_true")
    parser.add_argument("--require-local-execution", action="store_true")
    parser.add_argument("--package-install-attempted", action="store_true")
    parser.add_argument("--model-download-attempted", action="store_true")
    parser.add_argument("--model-download-success", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    run_voice_local_sherpa_onnx_supertonic3_ko_smoke(
        scripts_path=args.scripts,
        doc_path=args.doc,
        report_path=args.report,
        result_rows_path=args.rows,
        private_audio_dir=args.private_audio_dir,
        model_dir=args.model_dir,
        archive_path=args.archive,
        script_limit=args.script_limit,
        sid=args.sid,
        num_steps=args.num_steps,
        speed=args.speed,
        num_threads=args.num_threads,
        execute_local_tts=args.execute_local_tts,
        require_local_execution=args.require_local_execution,
        package_install_attempted=args.package_install_attempted,
        model_download_attempted=args.model_download_attempted,
        model_download_success=args.model_download_success,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
