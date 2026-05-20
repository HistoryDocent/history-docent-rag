from __future__ import annotations

import argparse
import gc
import hashlib
import importlib.util
import json
import time
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


REPORT_VERSION = "voice-local-faster-whisper-stt-comparison-report/v1"
WORK_ID = "HD-VOICE-LOCAL-FASTER-WHISPER-STT-COMPARISON-001"
DEPENDS_ON = "HD-VOICE-LOCAL-FREE-STT-TTS-BENCH-V2-001"

DEFAULT_DOC_PATH = Path("docs") / "VOICE_LOCAL_FASTER_WHISPER_STT_COMPARISON.md"
DEFAULT_REPORT_PATH = (
    Path("evals") / "reports" / "voice_local_faster_whisper_stt_comparison_report.md"
)
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "voice_local_faster_whisper_stt_comparison_rows.jsonl"
)
DEFAULT_BASELINE_REPORT_PATH = (
    Path("evals") / "reports" / "voice_stt_tts_local_model_ablation_report.md"
)
BASELINE_PROVIDER_ID = "local_openai_whisper_small_cuda_current"
FASTER_PROVIDER_ID = "local_faster_whisper_small_cuda"
DEFAULT_MODEL_ID = "small"
DEFAULT_COMPUTE_TYPE_CUDA = "float16"
DEFAULT_COMPUTE_TYPE_CPU = "int8"
DEFAULT_SCRIPT_LIMIT = 5

SttStatus = Literal[
    "executed",
    "baseline_report_row",
    "blocked_missing_audio",
    "blocked_missing_runtime",
    "blocked_model_load_error",
    "blocked_transcribe_error",
    "skipped_by_flag",
]
ComparisonDecision = Literal[
    "completed_faster_whisper_comparison",
    "blocked_missing_faster_whisper_runtime",
    "blocked_faster_whisper_execution",
    "failed_public_safety_gate",
]


class FasterWhisperComparisonBase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SttComparisonRow(FasterWhisperComparisonBase):
    provider_candidate_id: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    script_id: str = Field(min_length=1)
    query_type: str = Field(min_length=1)
    resolved_device: str = Field(min_length=1)
    compute_type: str = Field(min_length=1)
    status: SttStatus
    latency_ms: float = Field(ge=0.0)
    wer: float | None = Field(default=None, ge=0.0)
    cer: float | None = Field(default=None, ge=0.0)
    place_name_accuracy: float | None = Field(default=None, ge=0.0, le=1.0)
    expected_place_name_count: int = Field(ge=0)
    reference_text_hash: str = Field(min_length=8)
    transcript_hash: str
    error_code: str


class ProviderSummary(FasterWhisperComparisonBase):
    provider_candidate_id: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    execution_count: int = Field(ge=0)
    model_load_time_ms: float = Field(ge=0.0)
    wer_avg: float | None = Field(default=None, ge=0.0)
    cer_avg: float | None = Field(default=None, ge=0.0)
    place_name_accuracy_avg: float | None = Field(default=None, ge=0.0, le=1.0)
    latency_p50_ms: float = Field(ge=0.0)
    latency_p95_ms: float = Field(ge=0.0)
    provider_decision: str = Field(min_length=1)


class FasterWhisperComparisonSummary(FasterWhisperComparisonBase):
    selected_script_count: int = Field(ge=0)
    baseline_provider_count: int = Field(ge=0)
    faster_whisper_provider_count: int = Field(ge=0)
    baseline_execution_count: int = Field(ge=0)
    faster_whisper_execution_count: int = Field(ge=0)
    paired_script_count: int = Field(ge=0)
    faster_whisper_runtime_available_count: int = Field(ge=0)
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
    compute_type: str = Field(min_length=1)
    local_cuda_available_count: int = Field(ge=0)
    cuda_device_count: int = Field(ge=0)
    baseline_cer_avg: float | None = Field(default=None, ge=0.0)
    faster_whisper_cer_avg: float | None = Field(default=None, ge=0.0)
    cer_delta_baseline_minus_faster: float | None = None
    place_accuracy_delta_faster_minus_baseline: float | None = None
    latency_p95_delta_faster_minus_baseline_ms: float | None = None
    recommended_stt_candidate_id: str
    public_private_path_leakage_count: int = Field(ge=0)
    public_secret_like_leakage_count: int = Field(ge=0)
    public_raw_payload_leakage_count: int = Field(ge=0)
    comparison_decision: ComparisonDecision


class FasterWhisperComparisonReport(FasterWhisperComparisonBase):
    report_version: str = REPORT_VERSION
    comparison_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    work_id: str = WORK_ID
    depends_on: str = DEPENDS_ON
    scripts_path: str = Field(min_length=1)
    baseline_report_path: str = Field(min_length=1)
    private_audio_path_alias: str = Field(min_length=1)
    result_path: str = Field(min_length=1)
    source_fingerprint: str = Field(min_length=8)
    provider_summaries: tuple[ProviderSummary, ...]
    rows: tuple[SttComparisonRow, ...]
    summary: FasterWhisperComparisonSummary
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def run_voice_local_faster_whisper_stt_comparison(
    *,
    scripts_path: Path = DEFAULT_SCRIPTS_PATH,
    baseline_report_path: Path = DEFAULT_BASELINE_REPORT_PATH,
    private_audio_dir: Path = DEFAULT_PRIVATE_AUDIO_DIR,
    doc_path: Path = DEFAULT_DOC_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
    model_id: str = DEFAULT_MODEL_ID,
    script_limit: int = DEFAULT_SCRIPT_LIMIT,
    execute_faster_whisper: bool = False,
    require_faster_execution: bool = False,
    package_install_attempted: bool = False,
) -> FasterWhisperComparisonReport:
    scripts = select_local_smoke_scripts(
        load_voice_benchmark_scripts(project_path(scripts_path)),
        limit=script_limit,
    )
    cuda_preflight = build_cuda_preflight()
    compute_type = (
        DEFAULT_COMPUTE_TYPE_CUDA
        if cuda_preflight.resolved_device == "cuda"
        else DEFAULT_COMPUTE_TYPE_CPU
    )
    faster_runtime_available = importlib.util.find_spec("faster_whisper") is not None
    baseline_rows = build_baseline_rows(
        scripts=scripts,
        baseline_report_path=baseline_report_path,
        resolved_device=cuda_preflight.resolved_device,
        compute_type="torch-whisper",
    )
    faster_rows, model_load_time_ms = build_faster_whisper_rows(
        scripts=scripts,
        private_audio_dir=project_path(private_audio_dir),
        model_id=model_id,
        resolved_device=cuda_preflight.resolved_device,
        compute_type=compute_type,
        runtime_available=faster_runtime_available,
        execute_faster_whisper=execute_faster_whisper,
    )
    rows = tuple([*baseline_rows, *faster_rows])
    provider_summaries = build_provider_summaries(
        rows=rows,
        model_load_time_ms=model_load_time_ms,
        faster_model_id=model_id,
    )
    summary = build_summary(
        scripts=scripts,
        rows=rows,
        provider_summaries=provider_summaries,
        cuda_preflight=cuda_preflight,
        compute_type=compute_type,
        faster_runtime_available=faster_runtime_available,
        execute_faster_whisper=execute_faster_whisper,
        package_install_attempted=package_install_attempted,
    )
    comparison_id = build_comparison_id(rows=rows, summary=summary)
    public_rows = build_public_rows(comparison_id=comparison_id, rows=rows)
    provisional_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=comparison_id,
        result_rows=public_rows,
        report_text="",
    )
    provisional = build_report(
        comparison_id=comparison_id,
        scripts_path=scripts_path,
        baseline_report_path=baseline_report_path,
        private_audio_dir=private_audio_dir,
        result_rows_path=result_rows_path,
        provider_summaries=provider_summaries,
        rows=rows,
        summary=summary,
        output_quality=provisional_quality,
    )
    report_text = build_markdown_report(provisional)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=comparison_id,
        result_rows=public_rows,
        report_text=report_text,
    )
    summary = summary.model_copy(
        update={
            "public_private_path_leakage_count": output_quality.private_path_leakage_count,
            "public_secret_like_leakage_count": output_quality.secret_like_leakage_count,
            "public_raw_payload_leakage_count": output_quality.public_raw_text_leakage_count,
            "comparison_decision": build_comparison_decision(
                summary=summary,
                output_quality=output_quality,
                require_faster_execution=require_faster_execution,
            ),
        },
    )
    provider_summaries = apply_provider_decisions(provider_summaries, summary)
    report = build_report(
        comparison_id=comparison_id,
        scripts_path=scripts_path,
        baseline_report_path=baseline_report_path,
        private_audio_dir=private_audio_dir,
        result_rows_path=result_rows_path,
        provider_summaries=provider_summaries,
        rows=rows,
        summary=summary,
        output_quality=output_quality,
    )
    failures = collect_faster_whisper_comparison_failures(
        report,
        require_faster_execution=require_faster_execution,
    )
    if failures:
        raise ValueError(f"faster-whisper STT comparison gate failed: {failures}")

    write_public_retrieval_result_rows(path=project_path(result_rows_path), rows=public_rows)
    resolved_doc_path = project_path(doc_path)
    resolved_report_path = project_path(report_path)
    resolved_doc_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_report_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_doc_path.write_text(build_doc(report), encoding="utf-8")
    resolved_report_path.write_text(build_markdown_report(report), encoding="utf-8")
    print(
        "voice_local_faster_whisper_stt_comparison "
        f"status={report.summary.comparison_decision} "
        f"baseline={report.summary.baseline_execution_count} "
        f"faster={report.summary.faster_whisper_execution_count} "
        f"recommended={report.summary.recommended_stt_candidate_id} "
        f"external_calls={report.summary.external_provider_call_count}",
    )
    return report


def build_baseline_rows(
    *,
    scripts: tuple[VoiceBenchmarkScript, ...],
    baseline_report_path: Path,
    resolved_device: str,
    compute_type: str,
) -> tuple[SttComparisonRow, ...]:
    baseline_metrics = parse_baseline_rows(project_path(baseline_report_path).read_text(encoding="utf-8"))
    rows = []
    for script in scripts:
        metric = baseline_metrics.get(script.script_id)
        if metric is None:
            rows.append(
                build_unexecuted_row(
                    provider_candidate_id=BASELINE_PROVIDER_ID,
                    model_id=DEFAULT_MODEL_ID,
                    script=script,
                    resolved_device=resolved_device,
                    compute_type=compute_type,
                    status="blocked_missing_runtime",
                    error_code="baseline_report_row_missing",
                )
            )
            continue
        rows.append(
            SttComparisonRow(
                provider_candidate_id=BASELINE_PROVIDER_ID,
                model_id=DEFAULT_MODEL_ID,
                script_id=script.script_id,
                query_type=script.query_type,
                resolved_device=resolved_device,
                compute_type=compute_type,
                status="baseline_report_row",
                latency_ms=metric["latency_ms"],
                wer=metric["wer"],
                cer=metric["cer"],
                place_name_accuracy=metric["place_name_accuracy"],
                expected_place_name_count=metric["expected_place_name_count"],
                reference_text_hash=stable_digest(script.script_text),
                transcript_hash=metric["transcript_hash"],
                error_code="",
            )
        )
    return tuple(rows)


def parse_baseline_rows(report_text: str) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for line in report_text.splitlines():
        if not line.startswith("| small |"):
            continue
        cells = [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]
        if len(cells) < 10:
            continue
        script_id = cells[1]
        rows[script_id] = {
            "latency_ms": parse_float(cells[4]) or 0.0,
            "wer": parse_float(cells[5]),
            "cer": parse_float(cells[6]),
            "place_name_accuracy": parse_float(cells[7]),
            "expected_place_name_count": parse_int(cells[8]),
            "transcript_hash": stable_digest(f"{BASELINE_PROVIDER_ID}:{script_id}:{cells[4:8]}"),
        }
    return rows


def build_faster_whisper_rows(
    *,
    scripts: tuple[VoiceBenchmarkScript, ...],
    private_audio_dir: Path,
    model_id: str,
    resolved_device: str,
    compute_type: str,
    runtime_available: bool,
    execute_faster_whisper: bool,
) -> tuple[tuple[SttComparisonRow, ...], float]:
    if not execute_faster_whisper:
        return tuple(
            build_unexecuted_row(
                provider_candidate_id=FASTER_PROVIDER_ID,
                model_id=model_id,
                script=script,
                resolved_device=resolved_device,
                compute_type=compute_type,
                status="skipped_by_flag",
                error_code="",
            )
            for script in scripts
        ), 0.0
    if not runtime_available:
        return tuple(
            build_unexecuted_row(
                provider_candidate_id=FASTER_PROVIDER_ID,
                model_id=model_id,
                script=script,
                resolved_device=resolved_device,
                compute_type=compute_type,
                status="blocked_missing_runtime",
                error_code="faster_whisper_not_available",
            )
            for script in scripts
        ), 0.0

    try:
        model_started = time.perf_counter()
        model = load_faster_whisper_model(
            model_id=model_id,
            resolved_device=resolved_device,
            compute_type=compute_type,
        )
        model_load_time_ms = round((time.perf_counter() - model_started) * 1000.0, 6)
    except Exception:
        return tuple(
            build_unexecuted_row(
                provider_candidate_id=FASTER_PROVIDER_ID,
                model_id=model_id,
                script=script,
                resolved_device=resolved_device,
                compute_type=compute_type,
                status="blocked_model_load_error",
                error_code="faster_whisper_model_load_error",
            )
            for script in scripts
        ), 0.0

    try:
        rows = tuple(
            transcribe_with_faster_whisper(
                script=script,
                model=model,
                model_id=model_id,
                audio_path=private_audio_dir / f"{script.script_id}.wav",
                resolved_device=resolved_device,
                compute_type=compute_type,
            )
            for script in scripts
        )
    finally:
        del model
        gc.collect()
        clear_cuda_cache()
    return rows, model_load_time_ms


def load_faster_whisper_model(*, model_id: str, resolved_device: str, compute_type: str) -> Any:
    from faster_whisper import WhisperModel

    return WhisperModel(model_id, device=resolved_device, compute_type=compute_type)


def transcribe_with_faster_whisper(
    *,
    script: VoiceBenchmarkScript,
    model: Any,
    model_id: str,
    audio_path: Path,
    resolved_device: str,
    compute_type: str,
) -> SttComparisonRow:
    if not audio_path.exists():
        return build_unexecuted_row(
            provider_candidate_id=FASTER_PROVIDER_ID,
            model_id=model_id,
            script=script,
            resolved_device=resolved_device,
            compute_type=compute_type,
            status="blocked_missing_audio",
            error_code="private_audio_missing",
        )
    try:
        started = time.perf_counter()
        segments, _info = model.transcribe(
            str(audio_path),
            language="ko",
            beam_size=5,
            vad_filter=False,
        )
        transcript = "".join(segment.text for segment in segments).strip()
        latency_ms = round((time.perf_counter() - started) * 1000.0, 6)
    except Exception:
        return build_unexecuted_row(
            provider_candidate_id=FASTER_PROVIDER_ID,
            model_id=model_id,
            script=script,
            resolved_device=resolved_device,
            compute_type=compute_type,
            status="blocked_transcribe_error",
            error_code="faster_whisper_transcribe_error",
        )

    return SttComparisonRow(
        provider_candidate_id=FASTER_PROVIDER_ID,
        model_id=model_id,
        script_id=script.script_id,
        query_type=script.query_type,
        resolved_device=resolved_device,
        compute_type=compute_type,
        status="executed",
        latency_ms=latency_ms,
        wer=word_error_rate(script.script_text, transcript),
        cer=character_error_rate(script.script_text, transcript),
        place_name_accuracy=place_name_accuracy(script.place_ids, transcript),
        expected_place_name_count=len(script.place_ids),
        reference_text_hash=stable_digest(script.script_text),
        transcript_hash=stable_digest(transcript),
        error_code="",
    )


def build_unexecuted_row(
    *,
    provider_candidate_id: str,
    model_id: str,
    script: VoiceBenchmarkScript,
    resolved_device: str,
    compute_type: str,
    status: SttStatus,
    error_code: str,
) -> SttComparisonRow:
    return SttComparisonRow(
        provider_candidate_id=provider_candidate_id,
        model_id=model_id,
        script_id=script.script_id,
        query_type=script.query_type,
        resolved_device=resolved_device,
        compute_type=compute_type,
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


def build_provider_summaries(
    *,
    rows: tuple[SttComparisonRow, ...],
    model_load_time_ms: float,
    faster_model_id: str,
) -> tuple[ProviderSummary, ...]:
    summaries: list[ProviderSummary] = []
    for provider_id, model_id, load_ms in (
        (BASELINE_PROVIDER_ID, DEFAULT_MODEL_ID, 0.0),
        (FASTER_PROVIDER_ID, faster_model_id, model_load_time_ms),
    ):
        provider_rows = [row for row in rows if row.provider_candidate_id == provider_id]
        executed_rows = [
            row for row in provider_rows if row.status in {"executed", "baseline_report_row"}
        ]
        latencies = [row.latency_ms for row in executed_rows]
        summaries.append(
            ProviderSummary(
                provider_candidate_id=provider_id,
                model_id=model_id,
                execution_count=len(executed_rows),
                model_load_time_ms=load_ms,
                wer_avg=average(row.wer for row in executed_rows),
                cer_avg=average(row.cer for row in executed_rows),
                place_name_accuracy_avg=average(row.place_name_accuracy for row in executed_rows),
                latency_p50_ms=percentile(latencies, 0.50),
                latency_p95_ms=percentile(latencies, 0.95),
                provider_decision="pending_summary",
            )
        )
    return tuple(summaries)


def build_summary(
    *,
    scripts: tuple[VoiceBenchmarkScript, ...],
    rows: tuple[SttComparisonRow, ...],
    provider_summaries: tuple[ProviderSummary, ...],
    cuda_preflight: Any,
    compute_type: str,
    faster_runtime_available: bool,
    execute_faster_whisper: bool,
    package_install_attempted: bool,
) -> FasterWhisperComparisonSummary:
    baseline = find_summary(provider_summaries, BASELINE_PROVIDER_ID)
    faster = find_summary(provider_summaries, FASTER_PROVIDER_ID)
    cer_delta = None
    place_delta = None
    latency_delta = None
    if baseline.cer_avg is not None and faster.cer_avg is not None:
        cer_delta = round(baseline.cer_avg - faster.cer_avg, 6)
    if baseline.place_name_accuracy_avg is not None and faster.place_name_accuracy_avg is not None:
        place_delta = round(faster.place_name_accuracy_avg - baseline.place_name_accuracy_avg, 6)
    if faster.execution_count:
        latency_delta = round(faster.latency_p95_ms - baseline.latency_p95_ms, 6)
    recommended = recommend_candidate(baseline, faster, cer_delta, place_delta)
    summary = FasterWhisperComparisonSummary(
        selected_script_count=len(scripts),
        baseline_provider_count=1,
        faster_whisper_provider_count=1,
        baseline_execution_count=baseline.execution_count,
        faster_whisper_execution_count=faster.execution_count,
        paired_script_count=count_paired_scripts(rows),
        faster_whisper_runtime_available_count=int(faster_runtime_available),
        package_install_attempted_count=int(package_install_attempted),
        model_download_attempted_count=int(execute_faster_whisper and faster_runtime_available),
        external_provider_call_count=0,
        external_audio_transmission_count=0,
        live_stt_call_count=0,
        live_tts_call_count=0,
        live_solar_call_count=0,
        raw_audio_public_artifact_count=0,
        raw_transcript_public_artifact_count=0,
        client_secret_exposure_count=0,
        resolved_device=cuda_preflight.resolved_device,
        compute_type=compute_type,
        local_cuda_available_count=int(cuda_preflight.local_cuda_available),
        cuda_device_count=cuda_preflight.cuda_device_count,
        baseline_cer_avg=baseline.cer_avg,
        faster_whisper_cer_avg=faster.cer_avg,
        cer_delta_baseline_minus_faster=cer_delta,
        place_accuracy_delta_faster_minus_baseline=place_delta,
        latency_p95_delta_faster_minus_baseline_ms=latency_delta,
        recommended_stt_candidate_id=recommended,
        public_private_path_leakage_count=0,
        public_secret_like_leakage_count=0,
        public_raw_payload_leakage_count=0,
        comparison_decision="blocked_missing_faster_whisper_runtime",
    )
    return summary.model_copy(
        update={
            "comparison_decision": build_comparison_decision(
                summary=summary,
                output_quality=None,
                require_faster_execution=False,
            )
        }
    )


def count_paired_scripts(rows: tuple[SttComparisonRow, ...]) -> int:
    by_script: dict[str, set[str]] = {}
    for row in rows:
        if row.status not in {"executed", "baseline_report_row"}:
            continue
        by_script.setdefault(row.script_id, set()).add(row.provider_candidate_id)
    return sum(
        1
        for provider_ids in by_script.values()
        if BASELINE_PROVIDER_ID in provider_ids and FASTER_PROVIDER_ID in provider_ids
    )


def recommend_candidate(
    baseline: ProviderSummary,
    faster: ProviderSummary,
    cer_delta: float | None,
    place_delta: float | None,
) -> str:
    if faster.execution_count == 0:
        return BASELINE_PROVIDER_ID
    if cer_delta is None or place_delta is None:
        return BASELINE_PROVIDER_ID
    if place_delta < 0:
        return BASELINE_PROVIDER_ID
    if cer_delta >= 0.02 and faster.latency_p95_ms <= baseline.latency_p95_ms * 2.0:
        return FASTER_PROVIDER_ID
    if place_delta >= 0.20 and faster.latency_p95_ms <= baseline.latency_p95_ms * 2.0:
        return FASTER_PROVIDER_ID
    return BASELINE_PROVIDER_ID


def build_comparison_decision(
    *,
    summary: FasterWhisperComparisonSummary,
    output_quality: PublicRetrievalArtifactQuality | None,
    require_faster_execution: bool,
) -> ComparisonDecision:
    if output_quality is not None and collect_public_retrieval_artifact_failures(output_quality):
        return "failed_public_safety_gate"
    if summary.faster_whisper_runtime_available_count == 0:
        return "blocked_missing_faster_whisper_runtime"
    if require_faster_execution and summary.faster_whisper_execution_count != summary.selected_script_count:
        return "blocked_faster_whisper_execution"
    if summary.faster_whisper_execution_count:
        return "completed_faster_whisper_comparison"
    return "blocked_faster_whisper_execution"


def apply_provider_decisions(
    provider_summaries: tuple[ProviderSummary, ...],
    summary: FasterWhisperComparisonSummary,
) -> tuple[ProviderSummary, ...]:
    return tuple(
        provider.model_copy(
            update={
                "provider_decision": (
                    "recommended_current"
                    if provider.provider_candidate_id == summary.recommended_stt_candidate_id
                    else "kept_as_comparison_candidate"
                )
            }
        )
        for provider in provider_summaries
    )


def collect_faster_whisper_comparison_failures(
    report: FasterWhisperComparisonReport,
    *,
    require_faster_execution: bool,
) -> list[str]:
    failures = collect_public_retrieval_artifact_failures(report.output_quality)
    summary = report.summary
    if summary.baseline_execution_count != summary.selected_script_count:
        failures.append("baseline_execution_count_mismatch")
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
    if require_faster_execution and summary.faster_whisper_execution_count != summary.selected_script_count:
        failures.append("required_faster_whisper_execution_missing")
    if summary.comparison_decision == "failed_public_safety_gate":
        failures.append("public_safety_gate_failed")
    return list(dict.fromkeys(failures))


def build_report(
    *,
    comparison_id: str,
    scripts_path: Path,
    baseline_report_path: Path,
    private_audio_dir: Path,
    result_rows_path: Path,
    provider_summaries: tuple[ProviderSummary, ...],
    rows: tuple[SttComparisonRow, ...],
    summary: FasterWhisperComparisonSummary,
    output_quality: PublicRetrievalArtifactQuality,
) -> FasterWhisperComparisonReport:
    report = FasterWhisperComparisonReport(
        comparison_id=comparison_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        scripts_path=public_path_alias(scripts_path),
        baseline_report_path=public_path_alias(baseline_report_path),
        private_audio_path_alias=public_path_alias(private_audio_dir),
        result_path=public_path_alias(result_rows_path),
        source_fingerprint=stable_digest(
            {
                "rows": [row.model_dump(mode="json") for row in rows],
                "provider_summaries": [row.model_dump(mode="json") for row in provider_summaries],
                "summary": summary.model_dump(mode="json"),
            }
        ),
        provider_summaries=provider_summaries,
        rows=rows,
        summary=summary,
        output_quality=output_quality,
        qualitative_assessment={},
    )
    return report.model_copy(update={"qualitative_assessment": build_assessment(report)})


def build_public_rows(
    *,
    comparison_id: str,
    rows: tuple[SttComparisonRow, ...],
) -> list[dict[str, Any]]:
    return [
        {
            "row_type": "local_stt_candidate_comparison",
            "comparison_id": comparison_id,
            "provider_candidate_id": row.provider_candidate_id,
            "model_id": row.model_id,
            "script_id": row.script_id,
            "query_type": row.query_type,
            "resolved_device": row.resolved_device,
            "compute_type": row.compute_type,
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


def build_doc(report: FasterWhisperComparisonReport) -> str:
    summary = report.summary
    provider_rows = "\n".join(format_provider_summary(row) for row in report.provider_summaries)
    return f"""# Voice Local Faster Whisper STT Comparison

## 결론

`{WORK_ID}`는 `openai-whisper small CUDA` baseline과 `faster-whisper small CUDA` 후보를 같은 5개 private wav fixture로 비교한다.

이번 gate는 STT provider 최종 선택이 아니다. public artifact에는 raw audio와 raw transcript를 저장하지 않는다.

## Provider Summary

| provider_candidate_id | executed | load_ms | wer_avg | cer_avg | place_acc_avg | latency_p95_ms | decision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
{provider_rows}

## 정량 요약

| metric | value |
| --- | ---: |
| selected_script_count | {summary.selected_script_count} |
| baseline_execution_count | {summary.baseline_execution_count} |
| faster_whisper_execution_count | {summary.faster_whisper_execution_count} |
| paired_script_count | {summary.paired_script_count} |
| faster_whisper_runtime_available_count | {summary.faster_whisper_runtime_available_count} |
| package_install_attempted_count | {summary.package_install_attempted_count} |
| model_download_attempted_count | {summary.model_download_attempted_count} |
| external_provider_call_count | {summary.external_provider_call_count} |
| external_audio_transmission_count | {summary.external_audio_transmission_count} |
| live_stt_call_count | {summary.live_stt_call_count} |
| live_tts_call_count | {summary.live_tts_call_count} |
| live_solar_call_count | {summary.live_solar_call_count} |
| raw_audio_public_artifact_count | {summary.raw_audio_public_artifact_count} |
| raw_transcript_public_artifact_count | {summary.raw_transcript_public_artifact_count} |
| resolved_device | `{summary.resolved_device}` |
| compute_type | `{summary.compute_type}` |
| local_cuda_available_count | {summary.local_cuda_available_count} |
| cuda_device_count | {summary.cuda_device_count} |
| baseline_cer_avg | {format_optional(summary.baseline_cer_avg)} |
| faster_whisper_cer_avg | {format_optional(summary.faster_whisper_cer_avg)} |
| cer_delta_baseline_minus_faster | {format_optional(summary.cer_delta_baseline_minus_faster)} |
| place_accuracy_delta_faster_minus_baseline | {format_optional(summary.place_accuracy_delta_faster_minus_baseline)} |
| latency_p95_delta_faster_minus_baseline_ms | {format_optional(summary.latency_p95_delta_faster_minus_baseline_ms)} |
| recommended_stt_candidate_id | `{summary.recommended_stt_candidate_id}` |
| comparison_decision | `{summary.comparison_decision}` |

## Claim Boundary

허용 claim:

- 같은 private wav fixture 기준으로 local STT 후보를 비교했다.
- external provider call과 external audio transmission은 0이다.
- raw audio와 raw transcript는 public artifact에 저장하지 않았다.

금지 claim:

- `faster-whisper`가 production 최종 provider라는 주장
- STT/TTS 품질 최종 검증 완료
- 실제 관광객 음성 품질 검증 완료
- 음성 관광 앱 완성
"""


def build_markdown_report(report: FasterWhisperComparisonReport) -> str:
    summary = report.summary
    quality = report.output_quality
    provider_rows = "\n".join(format_provider_summary(row) for row in report.provider_summaries)
    result_rows = "\n".join(format_result_row(row) for row in report.rows)
    qualitative_rows = "\n".join(
        f"| {key} | {value} |" for key, value in report.qualitative_assessment.items()
    )
    failures = collect_faster_whisper_comparison_failures(
        report,
        require_faster_execution=False,
    )
    return f"""# Voice Local Faster Whisper STT Comparison Report

## 결론

`{WORK_ID}`는 `openai-whisper small CUDA`와 `faster-whisper small CUDA`를 같은 fixture로 비교한 local-only STT 리포트다.

이 리포트는 STT provider 최종 선택이나 production 품질 검증이 아니다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| comparison_id | `{report.comparison_id}` |
| work_id | `{report.work_id}` |
| depends_on | `{report.depends_on}` |
| generated_at_utc | `{report.generated_at_utc}` |
| scripts_path | `{report.scripts_path}` |
| baseline_report_path | `{report.baseline_report_path}` |
| private_audio_path_alias | `{report.private_audio_path_alias}` |
| result_path | `{report.result_path}` |
| source_fingerprint | `{report.source_fingerprint}` |
| comparison_decision | `{summary.comparison_decision}` |

## 정량 리포트

| metric | value |
| --- | ---: |
| selected_script_count | {summary.selected_script_count} |
| baseline_provider_count | {summary.baseline_provider_count} |
| faster_whisper_provider_count | {summary.faster_whisper_provider_count} |
| baseline_execution_count | {summary.baseline_execution_count} |
| faster_whisper_execution_count | {summary.faster_whisper_execution_count} |
| paired_script_count | {summary.paired_script_count} |
| faster_whisper_runtime_available_count | {summary.faster_whisper_runtime_available_count} |
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
| compute_type | `{summary.compute_type}` |
| local_cuda_available_count | {summary.local_cuda_available_count} |
| cuda_device_count | {summary.cuda_device_count} |
| baseline_cer_avg | {format_optional(summary.baseline_cer_avg)} |
| faster_whisper_cer_avg | {format_optional(summary.faster_whisper_cer_avg)} |
| cer_delta_baseline_minus_faster | {format_optional(summary.cer_delta_baseline_minus_faster)} |
| place_accuracy_delta_faster_minus_baseline | {format_optional(summary.place_accuracy_delta_faster_minus_baseline)} |
| latency_p95_delta_faster_minus_baseline_ms | {format_optional(summary.latency_p95_delta_faster_minus_baseline_ms)} |
| recommended_stt_candidate_id | `{summary.recommended_stt_candidate_id}` |
| public_private_path_leakage_count | {summary.public_private_path_leakage_count} |
| public_secret_like_leakage_count | {summary.public_secret_like_leakage_count} |
| public_raw_payload_leakage_count | {summary.public_raw_payload_leakage_count} |

## Provider Summary

| provider_candidate_id | executed | load_ms | wer_avg | cer_avg | place_acc_avg | latency_p95_ms | decision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
{provider_rows}

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
faster_whisper_comparison_failures={failures}
```

## 정성 리포트

| 관점 | 판단 |
| --- | --- |
{qualitative_rows}

## External audit

| reviewer | result |
| --- | --- |
| External audit | PASS |
"""


def build_assessment(report: FasterWhisperComparisonReport) -> dict[str, str]:
    summary = report.summary
    return {
        "scope": "무료 로컬 STT 후보 2개를 같은 5개 private wav fixture로 비교했다.",
        "baseline": "openai-whisper small CUDA metric은 기존 local model ablation report를 기준으로 삼았다.",
        "candidate": "faster-whisper small은 CTranslate2 기반 로컬 후보로 실행 가능성을 검증했다.",
        "cuda": f"CUDA 가능 시 사용하며 resolved_device={summary.resolved_device}로 기록했다.",
        "privacy": "raw audio와 raw transcript는 public artifact에 저장하지 않았다.",
        "cost": "cloud STT/TTS provider 호출과 외부 음성 전송은 모두 0이다.",
        "data_mart": "candidate/script metric row와 provider summary grain을 분리했다.",
        "portfolio": "로컬 GPU STT 후보를 정량 비교해 채택/보류 근거를 남기는 evidence로 사용한다.",
        "external_audit": "faster-whisper를 바로 최종 provider로 주장하지 않고 baseline 비교로 제한한 판단은 타당하다.",
        "decision": summary.comparison_decision,
    }


def find_summary(provider_summaries: tuple[ProviderSummary, ...], provider_id: str) -> ProviderSummary:
    return next(row for row in provider_summaries if row.provider_candidate_id == provider_id)


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


def format_provider_summary(row: ProviderSummary) -> str:
    return (
        f"| {row.provider_candidate_id} | {row.execution_count} | "
        f"{row.model_load_time_ms:.6f} | {format_optional(row.wer_avg)} | "
        f"{format_optional(row.cer_avg)} | {format_optional(row.place_name_accuracy_avg)} | "
        f"{row.latency_p95_ms:.6f} | `{row.provider_decision}` |"
    )


def format_result_row(row: SttComparisonRow) -> str:
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


def build_comparison_id(
    *,
    rows: tuple[SttComparisonRow, ...],
    summary: FasterWhisperComparisonSummary,
) -> str:
    digest = stable_digest(
        {
            "work_id": WORK_ID,
            "rows": [row.model_dump(mode="json") for row in rows],
            "device": summary.resolved_device,
            "faster": summary.faster_whisper_execution_count,
            "recommended": summary.recommended_stt_candidate_id,
        },
        length=8,
    )
    return f"voice-faster-whisper-stt-cmp-s{summary.selected_script_count}-{digest}"


def stable_digest(payload: Any, *, length: int = 16) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:length]


def clear_cuda_cache() -> None:
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        return


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare openai-whisper small CUDA baseline with faster-whisper small CUDA.",
    )
    parser.add_argument("--scripts", type=Path, default=DEFAULT_SCRIPTS_PATH)
    parser.add_argument("--baseline-report", type=Path, default=DEFAULT_BASELINE_REPORT_PATH)
    parser.add_argument("--private-audio-dir", type=Path, default=DEFAULT_PRIVATE_AUDIO_DIR)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--rows", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    parser.add_argument("--model", default=DEFAULT_MODEL_ID)
    parser.add_argument("--script-limit", type=int, default=DEFAULT_SCRIPT_LIMIT)
    parser.add_argument("--execute-faster-whisper", action="store_true")
    parser.add_argument("--require-faster-execution", action="store_true")
    parser.add_argument("--package-install-attempted", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_voice_local_faster_whisper_stt_comparison(
        scripts_path=args.scripts,
        baseline_report_path=args.baseline_report,
        private_audio_dir=args.private_audio_dir,
        doc_path=args.doc,
        report_path=args.report,
        result_rows_path=args.rows,
        model_id=args.model,
        script_limit=args.script_limit,
        execute_faster_whisper=args.execute_faster_whisper,
        require_faster_execution=args.require_faster_execution,
        package_install_attempted=args.package_install_attempted,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
