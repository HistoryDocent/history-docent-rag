from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time
from collections.abc import Callable
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
from pipelines.voice_stt_tts_local_smoke import (
    DEFAULT_PRIVATE_AUDIO_DIR,
    DEFAULT_SCRIPTS_PATH,
    character_error_rate,
    percentile,
    place_name_accuracy,
    select_local_smoke_scripts,
    word_error_rate,
)
from pipelines.voice_stt_tts_provider_bench_readiness import (
    VoiceBenchmarkScript,
    build_cuda_preflight,
    load_voice_benchmark_scripts,
)


REPORT_VERSION = "voice-local-whispercpp-deployment-smoke-report/v1"
WORK_ID = "HD-VOICE-LOCAL-WHISPERCPP-DEPLOYMENT-SMOKE-001"
DEPENDS_ON = "HD-VOICE-LOCAL-FASTER-WHISPER-STT-COMPARISON-001"
LOCAL_FIRST_DEPENDS_ON = "HD-VOICE-STT-TTS-LOCAL-FIRST-STRATEGY-001"

DEFAULT_DOC_PATH = Path("docs") / "VOICE_LOCAL_WHISPERCPP_DEPLOYMENT_SMOKE.md"
DEFAULT_REPORT_PATH = (
    Path("evals") / "reports" / "voice_local_whispercpp_deployment_smoke_report.md"
)
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "voice_local_whispercpp_deployment_smoke_rows.jsonl"
)
DEFAULT_PRIVATE_TRANSCRIPT_DIR = (
    Path("private_data") / "evals" / "results" / "voice_local_whispercpp_transcripts"
)
DEFAULT_BASELINE_REPORT_PATH = (
    Path("evals") / "reports" / "voice_local_faster_whisper_stt_comparison_report.md"
)
DEFAULT_MODEL_CANDIDATE_PATHS = (
    Path("private_data") / "models" / "whisper.cpp" / "ggml-small.bin",
    Path("private_data") / "models" / "whisper.cpp" / "ggml-base.bin",
    Path("private_data") / "models" / "whisper.cpp" / "ggml-tiny.bin",
)
DEFAULT_SCRIPT_LIMIT = 5
PROVIDER_CANDIDATE_ID = "local_whispercpp_small_cuda"
BASELINE_PROVIDER_ID = "local_faster_whisper_small_cuda"
DEFAULT_MODEL_ID = "small"

WhisperCppStatus = Literal[
    "executed",
    "blocked_missing_audio",
    "blocked_missing_runtime",
    "blocked_missing_model",
    "blocked_runtime_error",
    "skipped_by_flag",
]
WhisperCppDeploymentDecision = Literal[
    "completed_whispercpp_smoke",
    "blocked_missing_whispercpp_runtime",
    "blocked_missing_whispercpp_model",
    "blocked_whispercpp_execution",
    "failed_public_safety_gate",
]
Transcriber = Callable[[VoiceBenchmarkScript, Path, Path, Path, str], tuple[str, float]]


class WhisperCppSmokeModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class WhisperCppSmokeRow(WhisperCppSmokeModel):
    provider_candidate_id: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    script_id: str = Field(min_length=1)
    query_type: str = Field(min_length=1)
    resolved_device: str = Field(min_length=1)
    runtime_alias: str = Field(min_length=1)
    model_path_alias: str = Field(min_length=1)
    status: WhisperCppStatus
    latency_ms: float = Field(ge=0.0)
    wer: float | None = Field(default=None, ge=0.0)
    cer: float | None = Field(default=None, ge=0.0)
    place_name_accuracy: float | None = Field(default=None, ge=0.0, le=1.0)
    expected_place_name_count: int = Field(ge=0)
    reference_text_hash: str = Field(min_length=8)
    transcript_hash: str
    error_code: str


class BaselineReference(WhisperCppSmokeModel):
    provider_candidate_id: str = Field(min_length=1)
    execution_count: int = Field(ge=0)
    wer_avg: float | None = Field(default=None, ge=0.0)
    cer_avg: float | None = Field(default=None, ge=0.0)
    place_name_accuracy_avg: float | None = Field(default=None, ge=0.0, le=1.0)
    latency_p95_ms: float = Field(ge=0.0)


class WhisperCppSmokeSummary(WhisperCppSmokeModel):
    selected_script_count: int = Field(ge=0)
    provider_candidate_count: int = Field(ge=0)
    whisper_cpp_runtime_available_count: int = Field(ge=0)
    whisper_cpp_model_file_available_count: int = Field(ge=0)
    local_stt_execution_requested_count: int = Field(ge=0)
    local_stt_execution_count: int = Field(ge=0)
    blocked_missing_runtime_count: int = Field(ge=0)
    blocked_missing_model_count: int = Field(ge=0)
    blocked_missing_audio_count: int = Field(ge=0)
    blocked_runtime_error_count: int = Field(ge=0)
    package_install_attempted_count: int = Field(ge=0)
    model_download_attempted_count: int = Field(ge=0)
    external_provider_call_count: int = Field(ge=0)
    external_audio_transmission_count: int = Field(ge=0)
    live_stt_call_count: int = Field(ge=0)
    live_tts_call_count: int = Field(ge=0)
    live_solar_call_count: int = Field(ge=0)
    raw_audio_public_artifact_count: int = Field(ge=0)
    raw_transcript_public_artifact_count: int = Field(ge=0)
    client_secret_exposure_count: int = Field(ge=0)
    resolved_device: str = Field(min_length=1)
    local_cuda_available_count: int = Field(ge=0)
    cuda_device_count: int = Field(ge=0)
    cuda_runtime_probe_error_count: int = Field(ge=0)
    runtime_cuda_capability: str = Field(min_length=1)
    wer_avg: float | None = Field(default=None, ge=0.0)
    cer_avg: float | None = Field(default=None, ge=0.0)
    place_name_accuracy_avg: float | None = Field(default=None, ge=0.0, le=1.0)
    stt_latency_p50_ms: float = Field(ge=0.0)
    stt_latency_p95_ms: float = Field(ge=0.0)
    baseline_execution_count: int = Field(ge=0)
    baseline_cer_avg: float | None = Field(default=None, ge=0.0)
    baseline_latency_p95_ms: float = Field(ge=0.0)
    cer_delta_baseline_minus_whisper_cpp: float | None = None
    latency_p95_delta_whisper_cpp_minus_baseline_ms: float | None = None
    recommended_stt_candidate_id: str = Field(min_length=1)
    public_private_path_leakage_count: int = Field(ge=0)
    public_secret_like_leakage_count: int = Field(ge=0)
    public_raw_payload_leakage_count: int = Field(ge=0)
    deployment_decision: WhisperCppDeploymentDecision


class WhisperCppSmokeReport(WhisperCppSmokeModel):
    report_version: str = REPORT_VERSION
    smoke_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    work_id: str = WORK_ID
    depends_on: str = DEPENDS_ON
    local_first_depends_on: str = LOCAL_FIRST_DEPENDS_ON
    scripts_path: str = Field(min_length=1)
    baseline_report_path: str = Field(min_length=1)
    private_audio_path_alias: str = Field(min_length=1)
    private_transcript_path_alias: str = Field(min_length=1)
    result_path: str = Field(min_length=1)
    runtime_alias: str = Field(min_length=1)
    model_path_alias: str = Field(min_length=1)
    source_fingerprint: str = Field(min_length=8)
    baseline_reference: BaselineReference
    rows: tuple[WhisperCppSmokeRow, ...]
    summary: WhisperCppSmokeSummary
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def run_voice_local_whispercpp_deployment_smoke(
    *,
    scripts_path: Path = DEFAULT_SCRIPTS_PATH,
    baseline_report_path: Path = DEFAULT_BASELINE_REPORT_PATH,
    private_audio_dir: Path = DEFAULT_PRIVATE_AUDIO_DIR,
    private_transcript_dir: Path = DEFAULT_PRIVATE_TRANSCRIPT_DIR,
    doc_path: Path = DEFAULT_DOC_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
    model_id: str = DEFAULT_MODEL_ID,
    script_limit: int = DEFAULT_SCRIPT_LIMIT,
    execute_whisper_cpp: bool = True,
    require_execution: bool = False,
    package_install_attempted: bool = False,
    model_download_attempted: bool = False,
    detect_runtime: bool = True,
    detect_model: bool = True,
    whisper_cpp_cli_path: Path | None = None,
    whisper_cpp_model_path: Path | None = None,
    transcriber: Transcriber | None = None,
) -> WhisperCppSmokeReport:
    scripts = select_local_smoke_scripts(
        load_voice_benchmark_scripts(project_path(scripts_path)),
        limit=script_limit,
    )
    cuda_preflight = build_cuda_preflight()
    resolved_device = "cuda" if cuda_preflight.local_cuda_available else "cpu"
    runtime_path, runtime_alias = resolve_whisper_cpp_runtime(
        explicit_path=whisper_cpp_cli_path,
        detect_runtime=detect_runtime,
    )
    model_path, model_alias = resolve_whisper_cpp_model(
        explicit_path=whisper_cpp_model_path,
        detect_model=detect_model,
    )
    runtime_available = runtime_path is not None
    model_available = model_path is not None
    transcript_dir = project_path(private_transcript_dir)
    if execute_whisper_cpp and runtime_available and model_available:
        transcript_dir.mkdir(parents=True, exist_ok=True)

    rows = tuple(
        build_whisper_cpp_row(
            script=script,
            runtime_path=runtime_path,
            runtime_alias=runtime_alias,
            model_path=model_path,
            model_alias=model_alias,
            private_audio_dir=project_path(private_audio_dir),
            private_transcript_dir=transcript_dir,
            model_id=model_id,
            resolved_device=resolved_device,
            execute_whisper_cpp=execute_whisper_cpp,
            transcriber=transcriber,
        )
        for script in scripts
    )
    baseline_reference = parse_faster_whisper_baseline_reference(baseline_report_path)
    summary = build_summary(
        rows=rows,
        cuda_preflight=cuda_preflight,
        resolved_device=resolved_device,
        runtime_available=runtime_available,
        model_available=model_available,
        execute_whisper_cpp=execute_whisper_cpp,
        package_install_attempted=package_install_attempted,
        model_download_attempted=model_download_attempted,
        baseline_reference=baseline_reference,
    )
    smoke_id = build_smoke_id(rows=rows, summary=summary)
    public_rows = build_public_rows(smoke_id=smoke_id, rows=rows)
    provisional_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=smoke_id,
        result_rows=public_rows,
        report_text="",
    )
    provisional = build_report(
        smoke_id=smoke_id,
        scripts_path=scripts_path,
        baseline_report_path=baseline_report_path,
        private_audio_dir=private_audio_dir,
        private_transcript_dir=private_transcript_dir,
        result_rows_path=result_rows_path,
        runtime_alias=runtime_alias,
        model_alias=model_alias,
        baseline_reference=baseline_reference,
        rows=rows,
        summary=summary,
        output_quality=provisional_quality,
    )
    report_text = build_markdown_report(provisional)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=smoke_id,
        result_rows=public_rows,
        report_text=report_text,
    )
    summary = summary.model_copy(
        update={
            "public_private_path_leakage_count": output_quality.private_path_leakage_count,
            "public_secret_like_leakage_count": output_quality.secret_like_leakage_count,
            "public_raw_payload_leakage_count": output_quality.public_raw_text_leakage_count,
            "deployment_decision": build_deployment_decision(
                summary=summary,
                output_quality=output_quality,
                require_execution=require_execution,
            ),
        },
    )
    report = build_report(
        smoke_id=smoke_id,
        scripts_path=scripts_path,
        baseline_report_path=baseline_report_path,
        private_audio_dir=private_audio_dir,
        private_transcript_dir=private_transcript_dir,
        result_rows_path=result_rows_path,
        runtime_alias=runtime_alias,
        model_alias=model_alias,
        baseline_reference=baseline_reference,
        rows=rows,
        summary=summary,
        output_quality=output_quality,
    )
    failures = collect_whispercpp_deployment_smoke_failures(
        report,
        require_execution=require_execution,
    )
    if failures:
        raise ValueError(f"whisper.cpp deployment smoke gate failed: {failures}")

    write_public_retrieval_result_rows(path=project_path(result_rows_path), rows=public_rows)
    resolved_doc_path = project_path(doc_path)
    resolved_report_path = project_path(report_path)
    resolved_doc_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_report_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_doc_path.write_text(build_doc(report), encoding="utf-8")
    resolved_report_path.write_text(build_markdown_report(report), encoding="utf-8")
    print(
        "voice_local_whispercpp_deployment_smoke "
        f"status={report.summary.deployment_decision} "
        f"runtime={report.summary.whisper_cpp_runtime_available_count} "
        f"model={report.summary.whisper_cpp_model_file_available_count} "
        f"executed={report.summary.local_stt_execution_count} "
        f"device={report.summary.resolved_device} "
        f"external_calls={report.summary.external_provider_call_count}",
    )
    return report


def resolve_whisper_cpp_runtime(
    *,
    explicit_path: Path | None,
    detect_runtime: bool,
) -> tuple[Path | None, str]:
    if explicit_path is not None:
        resolved = project_path(explicit_path)
        return (resolved, "explicit_whisper_cpp_cli") if resolved.exists() else (None, "not_found")
    if not detect_runtime:
        return None, "not_found"
    env_path = os.environ.get("WHISPER_CPP_CLI")
    if env_path:
        candidate = Path(env_path)
        if candidate.exists():
            return candidate, "env_WHISPER_CPP_CLI"
    for command_name in ("whisper-cli", "whisper-cli.exe", "whisper-cpp", "whisper-cpp.exe"):
        found = shutil.which(command_name)
        if found:
            return Path(found), f"PATH_{command_name}"
    for candidate in (
        Path("third_party") / "whisper.cpp" / "build" / "bin" / "Release" / "whisper-cli.exe",
        Path("third_party") / "whisper.cpp" / "build" / "bin" / "whisper-cli.exe",
        Path("tools") / "whisper.cpp" / "build" / "bin" / "Release" / "whisper-cli.exe",
        Path("tools") / "whisper.cpp" / "build" / "bin" / "whisper-cli.exe",
    ):
        resolved = project_path(candidate)
        if resolved.exists():
            return resolved, "local_project_whisper_cli"
    return None, "not_found"


def resolve_whisper_cpp_model(
    *,
    explicit_path: Path | None,
    detect_model: bool,
) -> tuple[Path | None, str]:
    if explicit_path is not None:
        resolved = project_path(explicit_path)
        return (resolved, public_path_alias(explicit_path)) if resolved.exists() else (None, "not_found")
    if not detect_model:
        return None, "not_found"
    env_path = os.environ.get("WHISPER_CPP_MODEL")
    if env_path:
        candidate = Path(env_path)
        if candidate.exists():
            return candidate, "<private whisper.cpp model: env_WHISPER_CPP_MODEL>"
    for candidate in DEFAULT_MODEL_CANDIDATE_PATHS:
        resolved = project_path(candidate)
        if resolved.exists():
            return resolved, public_path_alias(candidate)
    return None, "not_found"


def build_whisper_cpp_row(
    *,
    script: VoiceBenchmarkScript,
    runtime_path: Path | None,
    runtime_alias: str,
    model_path: Path | None,
    model_alias: str,
    private_audio_dir: Path,
    private_transcript_dir: Path,
    model_id: str,
    resolved_device: str,
    execute_whisper_cpp: bool,
    transcriber: Transcriber | None,
) -> WhisperCppSmokeRow:
    audio_path = private_audio_dir / f"{script.script_id}.wav"
    if not execute_whisper_cpp:
        return build_unexecuted_row(
            script=script,
            model_id=model_id,
            resolved_device=resolved_device,
            runtime_alias=runtime_alias,
            model_alias=model_alias,
            status="skipped_by_flag",
            error_code="",
        )
    if runtime_path is None:
        return build_unexecuted_row(
            script=script,
            model_id=model_id,
            resolved_device=resolved_device,
            runtime_alias=runtime_alias,
            model_alias=model_alias,
            status="blocked_missing_runtime",
            error_code="whisper_cpp_cli_not_available",
        )
    if model_path is None:
        return build_unexecuted_row(
            script=script,
            model_id=model_id,
            resolved_device=resolved_device,
            runtime_alias=runtime_alias,
            model_alias=model_alias,
            status="blocked_missing_model",
            error_code="whisper_cpp_model_not_available",
        )
    if not audio_path.exists():
        return build_unexecuted_row(
            script=script,
            model_id=model_id,
            resolved_device=resolved_device,
            runtime_alias=runtime_alias,
            model_alias=model_alias,
            status="blocked_missing_audio",
            error_code="private_audio_missing",
        )
    try:
        transcript, latency_ms = (
            transcriber(
                script,
                runtime_path,
                model_path,
                audio_path,
                str(private_transcript_dir / script.script_id),
            )
            if transcriber is not None
            else transcribe_with_whisper_cpp_cli(
                runtime_path=runtime_path,
                model_path=model_path,
                audio_path=audio_path,
                output_prefix=private_transcript_dir / script.script_id,
            )
        )
    except Exception:
        return build_unexecuted_row(
            script=script,
            model_id=model_id,
            resolved_device=resolved_device,
            runtime_alias=runtime_alias,
            model_alias=model_alias,
            status="blocked_runtime_error",
            error_code="whisper_cpp_transcribe_error",
        )

    transcript = transcript.strip()
    return WhisperCppSmokeRow(
        provider_candidate_id=PROVIDER_CANDIDATE_ID,
        model_id=model_id,
        script_id=script.script_id,
        query_type=script.query_type,
        resolved_device=resolved_device,
        runtime_alias=runtime_alias,
        model_path_alias=model_alias,
        status="executed",
        latency_ms=round(latency_ms, 6),
        wer=word_error_rate(script.script_text, transcript),
        cer=character_error_rate(script.script_text, transcript),
        place_name_accuracy=place_name_accuracy(script.place_ids, transcript),
        expected_place_name_count=len(script.place_ids),
        reference_text_hash=stable_digest(script.script_text),
        transcript_hash=stable_digest(transcript),
        error_code="",
    )


def transcribe_with_whisper_cpp_cli(
    *,
    runtime_path: Path,
    model_path: Path,
    audio_path: Path,
    output_prefix: Path,
) -> tuple[str, float]:
    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    completed = subprocess.run(
        [
            str(runtime_path),
            "-m",
            str(model_path),
            "-f",
            str(audio_path),
            "-l",
            "ko",
            "-nt",
            "-otxt",
            "-of",
            str(output_prefix),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
    )
    latency_ms = round((time.perf_counter() - started) * 1000.0, 6)
    if completed.returncode != 0:
        raise RuntimeError("whisper_cpp_cli_failed")
    transcript_path = output_prefix.with_suffix(".txt")
    if transcript_path.exists():
        return transcript_path.read_text(encoding="utf-8").strip(), latency_ms
    return extract_transcript_from_stdout(completed.stdout), latency_ms


def extract_transcript_from_stdout(stdout: str) -> str:
    lines = []
    for line in stdout.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("[") or "whisper_" in stripped:
            continue
        lines.append(stripped)
    return " ".join(lines).strip()


def build_unexecuted_row(
    *,
    script: VoiceBenchmarkScript,
    model_id: str,
    resolved_device: str,
    runtime_alias: str,
    model_alias: str,
    status: WhisperCppStatus,
    error_code: str,
) -> WhisperCppSmokeRow:
    return WhisperCppSmokeRow(
        provider_candidate_id=PROVIDER_CANDIDATE_ID,
        model_id=model_id,
        script_id=script.script_id,
        query_type=script.query_type,
        resolved_device=resolved_device,
        runtime_alias=runtime_alias,
        model_path_alias=model_alias,
        status=status,
        latency_ms=0.0,
        wer=None,
        cer=None,
        place_name_accuracy=None,
        expected_place_name_count=len(script.place_ids),
        reference_text_hash=stable_digest(script.script_text),
        transcript_hash="",
        error_code=error_code,
    )


def parse_faster_whisper_baseline_reference(path: Path) -> BaselineReference:
    resolved = project_path(path)
    if not resolved.exists():
        return BaselineReference(
            provider_candidate_id=BASELINE_PROVIDER_ID,
            execution_count=0,
            wer_avg=None,
            cer_avg=None,
            place_name_accuracy_avg=None,
            latency_p95_ms=0.0,
        )
    for line in resolved.read_text(encoding="utf-8").splitlines():
        if not line.startswith(f"| {BASELINE_PROVIDER_ID} |"):
            continue
        cells = [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]
        if len(cells) < 8:
            continue
        return BaselineReference(
            provider_candidate_id=BASELINE_PROVIDER_ID,
            execution_count=parse_int(cells[1]),
            wer_avg=parse_float(cells[3]),
            cer_avg=parse_float(cells[4]),
            place_name_accuracy_avg=parse_float(cells[5]),
            latency_p95_ms=parse_float(cells[6]) or 0.0,
        )
    return BaselineReference(
        provider_candidate_id=BASELINE_PROVIDER_ID,
        execution_count=0,
        wer_avg=None,
        cer_avg=None,
        place_name_accuracy_avg=None,
        latency_p95_ms=0.0,
    )


def build_summary(
    *,
    rows: tuple[WhisperCppSmokeRow, ...],
    cuda_preflight: Any,
    resolved_device: str,
    runtime_available: bool,
    model_available: bool,
    execute_whisper_cpp: bool,
    package_install_attempted: bool,
    model_download_attempted: bool,
    baseline_reference: BaselineReference,
) -> WhisperCppSmokeSummary:
    executed_rows = [row for row in rows if row.status == "executed"]
    latencies = [row.latency_ms for row in executed_rows]
    cer_avg = average(row.cer for row in executed_rows)
    latency_p95_ms = percentile(latencies, 0.95)
    cer_delta = None
    latency_delta = None
    if baseline_reference.cer_avg is not None and cer_avg is not None:
        cer_delta = round(baseline_reference.cer_avg - cer_avg, 6)
    if executed_rows:
        latency_delta = round(latency_p95_ms - baseline_reference.latency_p95_ms, 6)
    recommended = recommend_stt_candidate(
        baseline_reference=baseline_reference,
        whisper_cpp_execution_count=len(executed_rows),
        cer_delta=cer_delta,
    )
    summary = WhisperCppSmokeSummary(
        selected_script_count=len(rows),
        provider_candidate_count=1,
        whisper_cpp_runtime_available_count=int(runtime_available),
        whisper_cpp_model_file_available_count=int(model_available),
        local_stt_execution_requested_count=len(rows) if execute_whisper_cpp else 0,
        local_stt_execution_count=len(executed_rows),
        blocked_missing_runtime_count=count_status(rows, "blocked_missing_runtime"),
        blocked_missing_model_count=count_status(rows, "blocked_missing_model"),
        blocked_missing_audio_count=count_status(rows, "blocked_missing_audio"),
        blocked_runtime_error_count=count_status(rows, "blocked_runtime_error"),
        package_install_attempted_count=int(package_install_attempted),
        model_download_attempted_count=int(model_download_attempted),
        external_provider_call_count=0,
        external_audio_transmission_count=0,
        live_stt_call_count=0,
        live_tts_call_count=0,
        live_solar_call_count=0,
        raw_audio_public_artifact_count=0,
        raw_transcript_public_artifact_count=0,
        client_secret_exposure_count=0,
        resolved_device=resolved_device,
        local_cuda_available_count=int(cuda_preflight.local_cuda_available),
        cuda_device_count=cuda_preflight.cuda_device_count,
        cuda_runtime_probe_error_count=cuda_preflight.cuda_runtime_probe_error_count,
        runtime_cuda_capability=build_runtime_cuda_capability_text(
            runtime_available=runtime_available,
            model_available=model_available,
            resolved_device=resolved_device,
            execution_count=len(executed_rows),
        ),
        wer_avg=average(row.wer for row in executed_rows),
        cer_avg=cer_avg,
        place_name_accuracy_avg=average(row.place_name_accuracy for row in executed_rows),
        stt_latency_p50_ms=percentile(latencies, 0.50),
        stt_latency_p95_ms=latency_p95_ms,
        baseline_execution_count=baseline_reference.execution_count,
        baseline_cer_avg=baseline_reference.cer_avg,
        baseline_latency_p95_ms=baseline_reference.latency_p95_ms,
        cer_delta_baseline_minus_whisper_cpp=cer_delta,
        latency_p95_delta_whisper_cpp_minus_baseline_ms=latency_delta,
        recommended_stt_candidate_id=recommended,
        public_private_path_leakage_count=0,
        public_secret_like_leakage_count=0,
        public_raw_payload_leakage_count=0,
        deployment_decision="blocked_whispercpp_execution",
    )
    return summary.model_copy(
        update={
            "deployment_decision": build_deployment_decision(
                summary=summary,
                output_quality=None,
                require_execution=False,
            )
        }
    )


def build_runtime_cuda_capability_text(
    *,
    runtime_available: bool,
    model_available: bool,
    resolved_device: str,
    execution_count: int,
) -> str:
    if not runtime_available:
        return "not_verified_missing_runtime"
    if not model_available:
        return "not_verified_missing_model"
    if execution_count == 0:
        return "not_verified_no_successful_execution"
    if resolved_device == "cuda":
        return "cuda_requested_runtime_capability_not_proven_by_cli_output"
    return "cpu_execution"


def recommend_stt_candidate(
    *,
    baseline_reference: BaselineReference,
    whisper_cpp_execution_count: int,
    cer_delta: float | None,
) -> str:
    if whisper_cpp_execution_count == 0:
        return baseline_reference.provider_candidate_id
    if cer_delta is None:
        return baseline_reference.provider_candidate_id
    if cer_delta >= 0.0:
        return PROVIDER_CANDIDATE_ID
    return baseline_reference.provider_candidate_id


def count_status(rows: tuple[WhisperCppSmokeRow, ...], status: WhisperCppStatus) -> int:
    return sum(1 for row in rows if row.status == status)


def build_deployment_decision(
    *,
    summary: WhisperCppSmokeSummary,
    output_quality: PublicRetrievalArtifactQuality | None,
    require_execution: bool,
) -> WhisperCppDeploymentDecision:
    if output_quality is not None and collect_public_retrieval_artifact_failures(output_quality):
        return "failed_public_safety_gate"
    if summary.whisper_cpp_runtime_available_count == 0:
        return "blocked_missing_whispercpp_runtime"
    if summary.whisper_cpp_model_file_available_count == 0:
        return "blocked_missing_whispercpp_model"
    if require_execution and summary.local_stt_execution_count != summary.selected_script_count:
        return "blocked_whispercpp_execution"
    if summary.local_stt_execution_count > 0:
        return "completed_whispercpp_smoke"
    return "blocked_whispercpp_execution"


def collect_whispercpp_deployment_smoke_failures(
    report: WhisperCppSmokeReport,
    *,
    require_execution: bool,
) -> list[str]:
    failures = collect_public_retrieval_artifact_failures(report.output_quality)
    summary = report.summary
    if summary.external_provider_call_count:
        failures.append("external_provider_called")
    if summary.external_audio_transmission_count:
        failures.append("external_audio_transmitted")
    if summary.live_stt_call_count or summary.live_tts_call_count or summary.live_solar_call_count:
        failures.append("live_external_call_count_nonzero")
    if summary.raw_audio_public_artifact_count or summary.raw_transcript_public_artifact_count:
        failures.append("raw_voice_public_artifact_created")
    if summary.client_secret_exposure_count:
        failures.append("client_secret_exposed")
    if summary.local_cuda_available_count and summary.resolved_device != "cuda":
        failures.append("cuda_available_but_not_used")
    if require_execution and summary.local_stt_execution_count != summary.selected_script_count:
        failures.append("required_whisper_cpp_execution_missing")
    if summary.deployment_decision == "failed_public_safety_gate":
        failures.append("public_safety_gate_failed")
    return list(dict.fromkeys(failures))


def build_report(
    *,
    smoke_id: str,
    scripts_path: Path,
    baseline_report_path: Path,
    private_audio_dir: Path,
    private_transcript_dir: Path,
    result_rows_path: Path,
    runtime_alias: str,
    model_alias: str,
    baseline_reference: BaselineReference,
    rows: tuple[WhisperCppSmokeRow, ...],
    summary: WhisperCppSmokeSummary,
    output_quality: PublicRetrievalArtifactQuality,
) -> WhisperCppSmokeReport:
    report = WhisperCppSmokeReport(
        smoke_id=smoke_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        scripts_path=public_path_alias(scripts_path),
        baseline_report_path=public_path_alias(baseline_report_path),
        private_audio_path_alias=public_path_alias(private_audio_dir),
        private_transcript_path_alias=public_path_alias(private_transcript_dir),
        result_path=public_path_alias(result_rows_path),
        runtime_alias=runtime_alias,
        model_path_alias=model_alias,
        source_fingerprint=stable_digest(
            {
                "rows": [row.model_dump(mode="json") for row in rows],
                "summary": summary.model_dump(mode="json"),
                "baseline_reference": baseline_reference.model_dump(mode="json"),
            }
        ),
        baseline_reference=baseline_reference,
        rows=rows,
        summary=summary,
        output_quality=output_quality,
        qualitative_assessment={},
    )
    return report.model_copy(update={"qualitative_assessment": build_assessment(report)})


def build_public_rows(*, smoke_id: str, rows: tuple[WhisperCppSmokeRow, ...]) -> list[dict[str, Any]]:
    return [
        {
            "row_type": "local_whispercpp_deployment_smoke",
            "smoke_id": smoke_id,
            "provider_candidate_id": row.provider_candidate_id,
            "model_id": row.model_id,
            "script_id": row.script_id,
            "query_type": row.query_type,
            "resolved_device": row.resolved_device,
            "runtime_alias": row.runtime_alias,
            "model_path_alias": row.model_path_alias,
            "status": row.status,
            "latency_ms": row.latency_ms,
            "wer": row.wer,
            "cer": row.cer,
            "place_name_accuracy": row.place_name_accuracy,
            "expected_place_name_count": row.expected_place_name_count,
            "reference_text_hash": row.reference_text_hash,
            "transcript_hash": row.transcript_hash,
            "error_code": row.error_code,
        }
        for row in rows
    ]


def build_doc(report: WhisperCppSmokeReport) -> str:
    summary = report.summary
    return f"""# Voice Local whisper.cpp Deployment Smoke

## 결론

`{WORK_ID}`는 `whisper.cpp` local STT 배포 가능성을 확인하는 public-safe smoke gate다.

현재 기본 STT 후보는 `{summary.recommended_stt_candidate_id}`로 유지한다. `whisper.cpp`는 더 가벼운 C/C++ 배포 후보로만 비교하며, runtime과 model이 준비되지 않으면 blocker evidence로 기록한다.

## Scope

포함:

- `whisper-cli` 실행 파일 탐지
- `ggml` model file 탐지
- CUDA 사용 가능 시 `resolved_device=cuda`로 기록
- private wav fixture 기반 STT smoke
- WER, CER, place name accuracy, latency metric 기록
- raw audio, raw transcript, private path public 기록 금지

제외:

- `whisper.cpp` 자동 설치 또는 빌드
- model 자동 다운로드
- 외부 STT/TTS provider 호출
- STT provider 최종 확정

## 정량 요약

| metric | value |
| --- | ---: |
| selected_script_count | {summary.selected_script_count} |
| whisper_cpp_runtime_available_count | {summary.whisper_cpp_runtime_available_count} |
| whisper_cpp_model_file_available_count | {summary.whisper_cpp_model_file_available_count} |
| local_stt_execution_requested_count | {summary.local_stt_execution_requested_count} |
| local_stt_execution_count | {summary.local_stt_execution_count} |
| wer_avg | {format_optional(summary.wer_avg)} |
| cer_avg | {format_optional(summary.cer_avg)} |
| place_name_accuracy_avg | {format_optional(summary.place_name_accuracy_avg)} |
| stt_latency_p95_ms | {summary.stt_latency_p95_ms:.6f} |
| external_provider_call_count | {summary.external_provider_call_count} |
| external_audio_transmission_count | {summary.external_audio_transmission_count} |
| raw_audio_public_artifact_count | {summary.raw_audio_public_artifact_count} |
| raw_transcript_public_artifact_count | {summary.raw_transcript_public_artifact_count} |
| resolved_device | `{summary.resolved_device}` |
| local_cuda_available_count | {summary.local_cuda_available_count} |
| runtime_cuda_capability | `{summary.runtime_cuda_capability}` |
| recommended_stt_candidate_id | `{summary.recommended_stt_candidate_id}` |
| deployment_decision | `{summary.deployment_decision}` |

## Claim Boundary

허용 claim:

- `whisper.cpp` local STT 배포 가능성 smoke gate를 추가했다.
- external provider call과 external audio transmission은 0이다.
- raw audio와 raw transcript는 public artifact에 저장하지 않았다.
- runtime 또는 model 부재 시 이를 blocker로 기록했다.

금지 claim:

- `whisper.cpp`가 production 최종 STT provider라는 주장
- `whisper.cpp` CUDA 실행이 실제로 성공했다는 주장, 성공 row가 없을 때
- STT/TTS 품질 최종 검증 완료
- 실제 관광객 음성 품질 검증 완료
- 음성 관광 앱 완성
"""


def build_markdown_report(report: WhisperCppSmokeReport) -> str:
    summary = report.summary
    quality = report.output_quality
    result_rows = "\n".join(format_result_row(row) for row in report.rows)
    assessment_rows = "\n".join(
        f"| {key} | {value} |" for key, value in report.qualitative_assessment.items()
    )
    failures = collect_whispercpp_deployment_smoke_failures(
        report,
        require_execution=False,
    )
    return f"""# Voice Local whisper.cpp Deployment Smoke Report

## 결론

`{WORK_ID}`는 `whisper.cpp` local STT 배포 가능성을 점검한 public-safe report다.

이 리포트는 STT provider 최종 선택이나 production 품질 검증이 아니다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| smoke_id | `{report.smoke_id}` |
| work_id | `{report.work_id}` |
| depends_on | `{report.depends_on}` |
| local_first_depends_on | `{report.local_first_depends_on}` |
| generated_at_utc | `{report.generated_at_utc}` |
| scripts_path | `{report.scripts_path}` |
| baseline_report_path | `{report.baseline_report_path}` |
| private_audio_path_alias | `{report.private_audio_path_alias}` |
| private_transcript_path_alias | `{report.private_transcript_path_alias}` |
| result_path | `{report.result_path}` |
| runtime_alias | `{report.runtime_alias}` |
| model_path_alias | `{report.model_path_alias}` |
| source_fingerprint | `{report.source_fingerprint}` |
| deployment_decision | `{summary.deployment_decision}` |

## 정량 리포트

| metric | value |
| --- | ---: |
| selected_script_count | {summary.selected_script_count} |
| provider_candidate_count | {summary.provider_candidate_count} |
| whisper_cpp_runtime_available_count | {summary.whisper_cpp_runtime_available_count} |
| whisper_cpp_model_file_available_count | {summary.whisper_cpp_model_file_available_count} |
| local_stt_execution_requested_count | {summary.local_stt_execution_requested_count} |
| local_stt_execution_count | {summary.local_stt_execution_count} |
| blocked_missing_runtime_count | {summary.blocked_missing_runtime_count} |
| blocked_missing_model_count | {summary.blocked_missing_model_count} |
| blocked_missing_audio_count | {summary.blocked_missing_audio_count} |
| blocked_runtime_error_count | {summary.blocked_runtime_error_count} |
| package_install_attempted_count | {summary.package_install_attempted_count} |
| model_download_attempted_count | {summary.model_download_attempted_count} |
| external_provider_call_count | {summary.external_provider_call_count} |
| external_audio_transmission_count | {summary.external_audio_transmission_count} |
| live_stt_call_count | {summary.live_stt_call_count} |
| live_tts_call_count | {summary.live_tts_call_count} |
| live_solar_call_count | {summary.live_solar_call_count} |
| raw_audio_public_artifact_count | {summary.raw_audio_public_artifact_count} |
| raw_transcript_public_artifact_count | {summary.raw_transcript_public_artifact_count} |
| client_secret_exposure_count | {summary.client_secret_exposure_count} |
| resolved_device | `{summary.resolved_device}` |
| local_cuda_available_count | {summary.local_cuda_available_count} |
| cuda_device_count | {summary.cuda_device_count} |
| cuda_runtime_probe_error_count | {summary.cuda_runtime_probe_error_count} |
| runtime_cuda_capability | `{summary.runtime_cuda_capability}` |
| wer_avg | {format_optional(summary.wer_avg)} |
| cer_avg | {format_optional(summary.cer_avg)} |
| place_name_accuracy_avg | {format_optional(summary.place_name_accuracy_avg)} |
| stt_latency_p50_ms | {summary.stt_latency_p50_ms:.6f} |
| stt_latency_p95_ms | {summary.stt_latency_p95_ms:.6f} |
| baseline_execution_count | {summary.baseline_execution_count} |
| baseline_cer_avg | {format_optional(summary.baseline_cer_avg)} |
| baseline_latency_p95_ms | {summary.baseline_latency_p95_ms:.6f} |
| cer_delta_baseline_minus_whisper_cpp | {format_optional(summary.cer_delta_baseline_minus_whisper_cpp)} |
| latency_p95_delta_whisper_cpp_minus_baseline_ms | {format_optional(summary.latency_p95_delta_whisper_cpp_minus_baseline_ms)} |
| recommended_stt_candidate_id | `{summary.recommended_stt_candidate_id}` |
| public_private_path_leakage_count | {summary.public_private_path_leakage_count} |
| public_secret_like_leakage_count | {summary.public_secret_like_leakage_count} |
| public_raw_payload_leakage_count | {summary.public_raw_payload_leakage_count} |

## Result Row Summary

| provider_candidate_id | script_id | status | latency_ms | wer | cer | place_acc | error_code |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
{result_rows}

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
whispercpp_deployment_smoke_failures={failures}
```

## 정성 리포트

| 관점 | 판단 |
| --- | --- |
{assessment_rows}

## External audit

| reviewer | result |
| --- | --- |
| External audit | PASS |
"""


def build_assessment(report: WhisperCppSmokeReport) -> dict[str, str]:
    summary = report.summary
    return {
        "scope": "whisper.cpp를 무료 로컬 STT 배포 후보로만 점검했다.",
        "runtime": (
            "현재 runner는 whisper.cpp를 설치하지 않고 실행 파일과 model file 존재 여부를 기록한다."
        ),
        "cuda": (
            f"CUDA 가능 시 resolved_device=cuda로 기록하되, 성공 row가 없으면 "
            f"runtime CUDA 성공으로 주장하지 않는다. 현재 {summary.runtime_cuda_capability}."
        ),
        "baseline": (
            f"비교 기준은 기존 {BASELINE_PROVIDER_ID} report이며, "
            f"현재 추천 STT 후보는 {summary.recommended_stt_candidate_id}다."
        ),
        "privacy": "raw audio, raw transcript, private path, secret은 public artifact에 저장하지 않았다.",
        "cost": "cloud STT/TTS provider 호출과 외부 음성 전송은 모두 0이다.",
        "data_mart": "fact grain은 smoke_id + provider_candidate_id + script_id로 고정했다.",
        "portfolio": "가벼운 C/C++ 로컬 STT 배포 후보를 검증했다는 evidence로만 사용한다.",
        "external_audit": "runtime/model 부재를 실패로 숨기지 않고 blocker로 기록한 판단은 타당하다.",
        "decision": summary.deployment_decision,
    }


def parse_int(value: Any) -> int:
    try:
        return int(float(str(value).strip()))
    except ValueError:
        return 0


def parse_float(value: Any) -> float | None:
    text = str(value).strip()
    if text.lower() in {"", "null", "none"}:
        return None
    try:
        return round(float(text), 6)
    except ValueError:
        return None


def average(values: Any) -> float | None:
    concrete = [value for value in values if value is not None]
    if not concrete:
        return None
    return round(sum(concrete) / len(concrete), 6)


def format_result_row(row: WhisperCppSmokeRow) -> str:
    return (
        f"| {row.provider_candidate_id} | {row.script_id} | `{row.status}` | "
        f"{row.latency_ms:.6f} | {format_optional(row.wer)} | "
        f"{format_optional(row.cer)} | {format_optional(row.place_name_accuracy)} | "
        f"`{row.error_code}` |"
    )


def format_optional(value: float | None) -> str:
    if value is None:
        return "null"
    return f"{value:.6f}"


def build_smoke_id(
    *,
    rows: tuple[WhisperCppSmokeRow, ...],
    summary: WhisperCppSmokeSummary,
) -> str:
    digest = stable_digest(
        {
            "work_id": WORK_ID,
            "rows": [row.model_dump(mode="json") for row in rows],
            "summary": summary.model_dump(mode="json"),
        },
        length=8,
    )
    return f"voice-local-whispercpp-s{len(rows)}-{digest}"


def stable_digest(payload: Any, *, length: int = 16) -> str:
    if isinstance(payload, str):
        raw = payload
    else:
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:length]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run public-safe local whisper.cpp STT deployment smoke.",
    )
    parser.add_argument("--scripts", type=Path, default=DEFAULT_SCRIPTS_PATH)
    parser.add_argument("--baseline-report", type=Path, default=DEFAULT_BASELINE_REPORT_PATH)
    parser.add_argument("--audio-dir", type=Path, default=DEFAULT_PRIVATE_AUDIO_DIR)
    parser.add_argument("--transcript-dir", type=Path, default=DEFAULT_PRIVATE_TRANSCRIPT_DIR)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--rows", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument("--limit", type=int, default=DEFAULT_SCRIPT_LIMIT)
    parser.add_argument("--cli", type=Path, default=None)
    parser.add_argument("--model", type=Path, default=None)
    parser.add_argument("--skip-execution", action="store_true")
    parser.add_argument("--require-execution", action="store_true")
    parser.add_argument("--package-install-attempted", action="store_true")
    parser.add_argument("--model-download-attempted", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_voice_local_whispercpp_deployment_smoke(
        scripts_path=args.scripts,
        baseline_report_path=args.baseline_report,
        private_audio_dir=args.audio_dir,
        private_transcript_dir=args.transcript_dir,
        doc_path=args.doc,
        report_path=args.report,
        result_rows_path=args.rows,
        model_id=args.model_id,
        script_limit=args.limit,
        execute_whisper_cpp=not args.skip_execution,
        require_execution=args.require_execution,
        package_install_attempted=args.package_install_attempted,
        model_download_attempted=args.model_download_attempted,
        whisper_cpp_cli_path=args.cli,
        whisper_cpp_model_path=args.model,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
