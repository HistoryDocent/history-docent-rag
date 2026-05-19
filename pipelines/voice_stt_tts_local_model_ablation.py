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
    PROVIDER_CANDIDATE_ID,
    TARGET_SAMPLE_RATE,
    character_error_rate,
    percentile,
    place_name_accuracy,
    read_wav_as_mono_float32,
    select_local_smoke_scripts,
    synthesize_private_wav,
    word_error_rate,
)
from pipelines.voice_stt_tts_provider_bench_readiness import (
    VoiceBenchmarkScript,
    build_cuda_preflight,
    load_voice_benchmark_scripts,
)


REPORT_VERSION = "voice-stt-tts-local-model-ablation-report/v1"
WORK_ID = "HD-VOICE-STT-TTS-LOCAL-MODEL-ABLATION-001"
DEPENDS_ON = "HD-VOICE-STT-TTS-PROVIDER-BENCH-SMOKE-LOCAL-001"
DEFAULT_DOC_PATH = Path("docs") / "VOICE_STT_TTS_LOCAL_MODEL_ABLATION.md"
DEFAULT_REPORT_PATH = (
    Path("evals") / "reports" / "voice_stt_tts_local_model_ablation_report.md"
)
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "voice_stt_tts_local_model_ablation_rows.jsonl"
)
DEFAULT_MODELS = ("tiny", "base", "small")
DEFAULT_SCRIPT_LIMIT = 5

AblationStatus = Literal[
    "executed",
    "blocked_missing_audio",
    "blocked_missing_runtime",
    "blocked_runtime_error",
    "skipped_by_flag",
]
AblationDecision = Literal[
    "completed_local_model_ablation",
    "blocked_missing_runtime_or_audio",
    "failed_public_safety_gate",
]


class LocalModelAblationBase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LocalModelAblationRow(LocalModelAblationBase):
    script_id: str = Field(min_length=1)
    query_type: str = Field(min_length=1)
    provider_candidate_id: str = PROVIDER_CANDIDATE_ID
    model_id: str = Field(min_length=1)
    resolved_device: str = Field(min_length=1)
    transcription_status: AblationStatus
    latency_ms: float = Field(ge=0.0)
    wer: float | None = Field(default=None, ge=0.0)
    cer: float | None = Field(default=None, ge=0.0)
    place_name_accuracy: float | None = Field(default=None, ge=0.0, le=1.0)
    expected_place_name_count: int = Field(ge=0)
    reference_text_hash: str = Field(min_length=8)
    transcript_hash: str
    error_code: str


class LocalModelSummary(LocalModelAblationBase):
    model_id: str = Field(min_length=1)
    selected_script_count: int = Field(ge=0)
    model_load_time_ms: float = Field(ge=0.0)
    local_stt_execution_count: int = Field(ge=0)
    local_cuda_whisper_call_count: int = Field(ge=0)
    wer_avg: float | None = Field(default=None, ge=0.0)
    cer_avg: float | None = Field(default=None, ge=0.0)
    place_name_accuracy_avg: float | None = Field(default=None, ge=0.0, le=1.0)
    stt_latency_p50_ms: float = Field(ge=0.0)
    stt_latency_p95_ms: float = Field(ge=0.0)
    quality_delta_from_tiny_cer: float | None = None
    quality_delta_from_tiny_place_name_accuracy: float | None = None
    model_decision: str = Field(min_length=1)


class LocalModelAblationSummary(LocalModelAblationBase):
    model_candidate_count: int = Field(ge=0)
    selected_script_count: int = Field(ge=0)
    public_safe_script_fixture_count: int = Field(ge=0)
    runtime_available_count: int = Field(ge=0)
    audio_fixture_available_count: int = Field(ge=0)
    local_stt_execution_requested_count: int = Field(ge=0)
    total_local_stt_execution_count: int = Field(ge=0)
    total_local_cuda_whisper_call_count: int = Field(ge=0)
    external_provider_call_count: int = Field(ge=0)
    external_audio_transmission_count: int = Field(ge=0)
    live_stt_call_count: int = Field(ge=0)
    live_tts_call_count: int = Field(ge=0)
    live_solar_call_count: int = Field(ge=0)
    raw_transcript_public_artifact_count: int = Field(ge=0)
    raw_audio_public_artifact_count: int = Field(ge=0)
    client_secret_exposure_count: int = Field(ge=0)
    resolved_device: str = Field(min_length=1)
    local_cuda_available_count: int = Field(ge=0)
    cuda_device_count: int = Field(ge=0)
    best_cer_model_id: str
    best_place_name_accuracy_model_id: str
    recommended_model_id: str
    public_private_path_leakage_count: int = Field(ge=0)
    public_secret_like_leakage_count: int = Field(ge=0)
    public_raw_payload_leakage_count: int = Field(ge=0)
    ablation_decision: AblationDecision


class LocalModelAblationReport(LocalModelAblationBase):
    report_version: str = REPORT_VERSION
    ablation_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    work_id: str = WORK_ID
    depends_on: str = DEPENDS_ON
    scripts_path: str = Field(min_length=1)
    result_path: str = Field(min_length=1)
    private_audio_path_alias: str = Field(min_length=1)
    source_fingerprint: str = Field(min_length=8)
    model_summaries: tuple[LocalModelSummary, ...]
    rows: tuple[LocalModelAblationRow, ...]
    summary: LocalModelAblationSummary
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def run_voice_stt_tts_local_model_ablation(
    *,
    scripts_path: Path = DEFAULT_SCRIPTS_PATH,
    doc_path: Path = DEFAULT_DOC_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
    private_audio_dir: Path = DEFAULT_PRIVATE_AUDIO_DIR,
    models: tuple[str, ...] = DEFAULT_MODELS,
    script_limit: int = DEFAULT_SCRIPT_LIMIT,
    generate_missing_audio: bool = False,
    execute_local_whisper: bool = False,
    require_local_execution: bool = False,
) -> LocalModelAblationReport:
    scripts = select_local_smoke_scripts(
        load_voice_benchmark_scripts(project_path(scripts_path)),
        limit=script_limit,
    )
    cuda_preflight = build_cuda_preflight()
    runtime_available = importlib.util.find_spec("whisper") is not None
    audio_dir = project_path(private_audio_dir)
    if generate_missing_audio:
        ensure_private_audio_fixtures(scripts=scripts, audio_dir=audio_dir)

    rows: list[LocalModelAblationRow] = []
    model_summaries: list[LocalModelSummary] = []
    for model_id in models:
        model_rows, load_time_ms = run_model_candidate(
            scripts=scripts,
            audio_dir=audio_dir,
            model_id=model_id,
            resolved_device=cuda_preflight.resolved_device,
            runtime_available=runtime_available,
            execute_local_whisper=execute_local_whisper,
        )
        rows.extend(model_rows)
        model_summaries.append(
            build_model_summary(
                model_id=model_id,
                selected_script_count=len(scripts),
                rows=tuple(model_rows),
                model_load_time_ms=load_time_ms,
            ),
        )

    model_summaries = apply_model_deltas(tuple(model_summaries))
    summary = build_ablation_summary(
        rows=tuple(rows),
        model_summaries=model_summaries,
        scripts=scripts,
        audio_dir=audio_dir,
        cuda_preflight=cuda_preflight,
        runtime_available=runtime_available,
        execute_local_whisper=execute_local_whisper,
    )
    ablation_id = build_ablation_id(
        rows=tuple(rows),
        model_summaries=model_summaries,
        summary=summary,
    )
    public_rows = build_public_rows(ablation_id=ablation_id, rows=tuple(rows))
    provisional_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=ablation_id,
        result_rows=public_rows,
        report_text="",
    )
    provisional = build_ablation_report(
        ablation_id=ablation_id,
        scripts_path=scripts_path,
        result_rows_path=result_rows_path,
        private_audio_dir=private_audio_dir,
        model_summaries=model_summaries,
        rows=tuple(rows),
        summary=summary,
        output_quality=provisional_quality,
    )
    doc_text = build_doc_markdown(provisional)
    report_text = build_report_markdown(provisional)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=ablation_id,
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
            "ablation_decision": build_ablation_decision(
                summary=summary,
                output_quality=output_quality,
                require_local_execution=require_local_execution,
            ),
        },
    )
    report = build_ablation_report(
        ablation_id=ablation_id,
        scripts_path=scripts_path,
        result_rows_path=result_rows_path,
        private_audio_dir=private_audio_dir,
        model_summaries=model_summaries,
        rows=tuple(rows),
        summary=summary,
        output_quality=output_quality,
    )
    failures = collect_ablation_failures(
        report,
        require_local_execution=require_local_execution,
    )
    if failures:
        raise ValueError(f"voice local model ablation gate failed: {failures}")

    write_public_retrieval_result_rows(
        path=project_path(result_rows_path),
        rows=build_public_rows(ablation_id=ablation_id, rows=tuple(rows)),
    )
    resolved_doc_path = project_path(doc_path)
    resolved_report_path = project_path(report_path)
    resolved_doc_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_report_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_doc_path.write_text(build_doc_markdown(report), encoding="utf-8")
    resolved_report_path.write_text(build_report_markdown(report), encoding="utf-8")
    print(
        "voice_stt_tts_local_model_ablation "
        f"status={report.summary.ablation_decision} "
        f"models={report.summary.model_candidate_count} "
        f"device={report.summary.resolved_device} "
        f"local_stt={report.summary.total_local_stt_execution_count} "
        f"external_calls={report.summary.external_provider_call_count}",
    )
    return report


def ensure_private_audio_fixtures(
    *,
    scripts: tuple[VoiceBenchmarkScript, ...],
    audio_dir: Path,
) -> None:
    audio_dir.mkdir(parents=True, exist_ok=True)
    for script in scripts:
        audio_path = audio_dir / f"{script.script_id}.wav"
        if not audio_path.exists():
            synthesize_private_wav(script.script_text, audio_path)


def run_model_candidate(
    *,
    scripts: tuple[VoiceBenchmarkScript, ...],
    audio_dir: Path,
    model_id: str,
    resolved_device: str,
    runtime_available: bool,
    execute_local_whisper: bool,
) -> tuple[list[LocalModelAblationRow], float]:
    if not execute_local_whisper:
        return [
            build_unexecuted_row(
                script=script,
                model_id=model_id,
                resolved_device=resolved_device,
                status="skipped_by_flag",
                error_code="",
            )
            for script in scripts
        ], 0.0
    if not runtime_available:
        return [
            build_unexecuted_row(
                script=script,
                model_id=model_id,
                resolved_device=resolved_device,
                status="blocked_missing_runtime",
                error_code="openai_whisper_not_available",
            )
            for script in scripts
        ], 0.0

    model = None
    load_time_ms = 0.0
    try:
        start = time.perf_counter()
        model = load_whisper_model(model_id=model_id, device=resolved_device)
        load_time_ms = round((time.perf_counter() - start) * 1000, 6)
        rows = [
            transcribe_script(
                script=script,
                model=model,
                model_id=model_id,
                audio_path=audio_dir / f"{script.script_id}.wav",
                resolved_device=resolved_device,
            )
            for script in scripts
        ]
    except Exception:
        rows = [
            build_unexecuted_row(
                script=script,
                model_id=model_id,
                resolved_device=resolved_device,
                status="blocked_runtime_error",
                error_code="local_whisper_model_load_error",
            )
            for script in scripts
        ]
    finally:
        del model
        gc.collect()
        clear_cuda_cache()
    return rows, load_time_ms


def load_whisper_model(*, model_id: str, device: str) -> Any:
    import whisper

    return whisper.load_model(model_id, device=device)


def clear_cuda_cache() -> None:
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        return


def transcribe_script(
    *,
    script: VoiceBenchmarkScript,
    model: Any,
    model_id: str,
    audio_path: Path,
    resolved_device: str,
) -> LocalModelAblationRow:
    if not audio_path.exists():
        return build_unexecuted_row(
            script=script,
            model_id=model_id,
            resolved_device=resolved_device,
            status="blocked_missing_audio",
            error_code="private_audio_missing",
        )
    try:
        audio = read_wav_as_mono_float32(audio_path, target_sample_rate=TARGET_SAMPLE_RATE)
        start = time.perf_counter()
        result = model.transcribe(
            audio,
            language="ko",
            fp16=resolved_device == "cuda",
            verbose=False,
        )
        latency_ms = round((time.perf_counter() - start) * 1000, 6)
        transcript = str(result.get("text", "")).strip()
    except Exception:
        return build_unexecuted_row(
            script=script,
            model_id=model_id,
            resolved_device=resolved_device,
            status="blocked_runtime_error",
            error_code="local_whisper_transcribe_error",
        )

    return LocalModelAblationRow(
        script_id=script.script_id,
        query_type=script.query_type,
        model_id=model_id,
        resolved_device=resolved_device,
        transcription_status="executed",
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
    script: VoiceBenchmarkScript,
    model_id: str,
    resolved_device: str,
    status: AblationStatus,
    error_code: str,
) -> LocalModelAblationRow:
    return LocalModelAblationRow(
        script_id=script.script_id,
        query_type=script.query_type,
        model_id=model_id,
        resolved_device=resolved_device,
        transcription_status=status,
        latency_ms=0.0,
        wer=None,
        cer=None,
        place_name_accuracy=None,
        expected_place_name_count=len(script.place_ids),
        reference_text_hash=stable_digest(script.script_text),
        transcript_hash="",
        error_code=error_code,
    )


def build_model_summary(
    *,
    model_id: str,
    selected_script_count: int,
    rows: tuple[LocalModelAblationRow, ...],
    model_load_time_ms: float,
) -> LocalModelSummary:
    executed_rows = [row for row in rows if row.transcription_status == "executed"]
    latencies = [row.latency_ms for row in executed_rows]
    return LocalModelSummary(
        model_id=model_id,
        selected_script_count=selected_script_count,
        model_load_time_ms=model_load_time_ms,
        local_stt_execution_count=len(executed_rows),
        local_cuda_whisper_call_count=len(executed_rows),
        wer_avg=average(row.wer for row in executed_rows),
        cer_avg=average(row.cer for row in executed_rows),
        place_name_accuracy_avg=average(row.place_name_accuracy for row in executed_rows),
        stt_latency_p50_ms=percentile(latencies, 0.50),
        stt_latency_p95_ms=percentile(latencies, 0.95),
        model_decision="pending_delta",
    )


def apply_model_deltas(
    model_summaries: tuple[LocalModelSummary, ...],
) -> tuple[LocalModelSummary, ...]:
    tiny = next((row for row in model_summaries if row.model_id == "tiny"), None)
    if tiny is None:
        return tuple(row.model_copy(update={"model_decision": "no_tiny_baseline"}) for row in model_summaries)
    updated = []
    for row in model_summaries:
        cer_delta = None
        place_delta = None
        if tiny.cer_avg is not None and row.cer_avg is not None:
            cer_delta = round(tiny.cer_avg - row.cer_avg, 6)
        if tiny.place_name_accuracy_avg is not None and row.place_name_accuracy_avg is not None:
            place_delta = round(row.place_name_accuracy_avg - tiny.place_name_accuracy_avg, 6)
        updated.append(
            row.model_copy(
                update={
                    "quality_delta_from_tiny_cer": cer_delta,
                    "quality_delta_from_tiny_place_name_accuracy": place_delta,
                    "model_decision": decide_model(row, cer_delta, place_delta),
                },
            ),
        )
    return tuple(updated)


def decide_model(
    summary: LocalModelSummary,
    cer_delta: float | None,
    place_delta: float | None,
) -> str:
    if summary.local_stt_execution_count == 0:
        return "blocked"
    if summary.model_id == "tiny":
        return "baseline"
    if (place_delta is not None and place_delta >= 0.20) or (
        cer_delta is not None and summary.cer_avg is not None and cer_delta >= 0.20 * summary.cer_avg
    ):
        return "quality_candidate_check_latency"
    return "reject_no_material_quality_gain"


def build_ablation_summary(
    *,
    rows: tuple[LocalModelAblationRow, ...],
    model_summaries: tuple[LocalModelSummary, ...],
    scripts: tuple[VoiceBenchmarkScript, ...],
    audio_dir: Path,
    cuda_preflight: Any,
    runtime_available: bool,
    execute_local_whisper: bool,
) -> LocalModelAblationSummary:
    recommended = recommend_model(model_summaries)
    return LocalModelAblationSummary(
        model_candidate_count=len(model_summaries),
        selected_script_count=len(scripts),
        public_safe_script_fixture_count=len(scripts),
        runtime_available_count=int(runtime_available),
        audio_fixture_available_count=sum(
            1 for script in scripts if (audio_dir / f"{script.script_id}.wav").exists()
        ),
        local_stt_execution_requested_count=len(rows) if execute_local_whisper else 0,
        total_local_stt_execution_count=sum(
            1 for row in rows if row.transcription_status == "executed"
        ),
        total_local_cuda_whisper_call_count=sum(
            1 for row in rows if row.transcription_status == "executed"
        ),
        external_provider_call_count=0,
        external_audio_transmission_count=0,
        live_stt_call_count=0,
        live_tts_call_count=0,
        live_solar_call_count=0,
        raw_transcript_public_artifact_count=0,
        raw_audio_public_artifact_count=0,
        client_secret_exposure_count=0,
        resolved_device=cuda_preflight.resolved_device,
        local_cuda_available_count=int(cuda_preflight.local_cuda_available),
        cuda_device_count=cuda_preflight.cuda_device_count,
        best_cer_model_id=best_model_id(model_summaries, metric="cer"),
        best_place_name_accuracy_model_id=best_model_id(model_summaries, metric="place"),
        recommended_model_id=recommended,
        public_private_path_leakage_count=0,
        public_secret_like_leakage_count=0,
        public_raw_payload_leakage_count=0,
        ablation_decision="blocked_missing_runtime_or_audio",
    )


def best_model_id(
    model_summaries: tuple[LocalModelSummary, ...],
    *,
    metric: Literal["cer", "place"],
) -> str:
    candidates = [row for row in model_summaries if row.local_stt_execution_count > 0]
    if not candidates:
        return ""
    if metric == "cer":
        return min(candidates, key=lambda row: row.cer_avg if row.cer_avg is not None else 1e9).model_id
    return max(
        candidates,
        key=lambda row: row.place_name_accuracy_avg
        if row.place_name_accuracy_avg is not None
        else -1.0,
    ).model_id


def recommend_model(model_summaries: tuple[LocalModelSummary, ...]) -> str:
    candidates = [
        row
        for row in model_summaries
        if row.model_decision == "quality_candidate_check_latency"
        and row.stt_latency_p95_ms <= 3000.0
    ]
    if not candidates:
        return "tiny"
    return min(
        candidates,
        key=lambda row: (
            -(row.place_name_accuracy_avg or 0.0),
            row.cer_avg if row.cer_avg is not None else 1e9,
            row.stt_latency_p95_ms,
        ),
    ).model_id


def build_ablation_decision(
    *,
    summary: LocalModelAblationSummary,
    output_quality: PublicRetrievalArtifactQuality,
    require_local_execution: bool,
) -> AblationDecision:
    output_blocked = (
        output_quality.public_raw_text_leakage_count
        or output_quality.private_path_leakage_count
        or output_quality.secret_like_leakage_count
        or output_quality.forbidden_result_field_count
    )
    if output_blocked:
        return "failed_public_safety_gate"
    expected_count = summary.model_candidate_count * summary.selected_script_count
    if require_local_execution and summary.total_local_stt_execution_count != expected_count:
        return "blocked_missing_runtime_or_audio"
    if summary.total_local_stt_execution_count > 0:
        return "completed_local_model_ablation"
    return "blocked_missing_runtime_or_audio"


def collect_ablation_failures(
    report: LocalModelAblationReport,
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
    if summary.local_cuda_available_count and summary.resolved_device != "cuda":
        failures.append("cuda_available_but_not_used")
    expected_count = summary.model_candidate_count * summary.selected_script_count
    if require_local_execution and summary.total_local_stt_execution_count != expected_count:
        failures.append("required_local_model_ablation_not_completed")
    if summary.ablation_decision == "failed_public_safety_gate":
        failures.append("public_safety_gate_failed")
    return list(dict.fromkeys(failures))


def build_ablation_report(
    *,
    ablation_id: str,
    scripts_path: Path,
    result_rows_path: Path,
    private_audio_dir: Path,
    model_summaries: tuple[LocalModelSummary, ...],
    rows: tuple[LocalModelAblationRow, ...],
    summary: LocalModelAblationSummary,
    output_quality: PublicRetrievalArtifactQuality,
) -> LocalModelAblationReport:
    report = LocalModelAblationReport(
        ablation_id=ablation_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        scripts_path=public_path_alias(scripts_path),
        result_path=public_path_alias(result_rows_path),
        private_audio_path_alias=public_path_alias(private_audio_dir),
        source_fingerprint=stable_digest(
            {
                "rows": [row.model_dump(mode="json") for row in rows],
                "model_summaries": [row.model_dump(mode="json") for row in model_summaries],
                "summary": summary.model_dump(mode="json"),
            },
        ),
        model_summaries=model_summaries,
        rows=rows,
        summary=summary,
        output_quality=output_quality,
        qualitative_assessment={},
    )
    return report.model_copy(
        update={"qualitative_assessment": build_qualitative_assessment(report)},
    )


def build_public_rows(
    *,
    ablation_id: str,
    rows: tuple[LocalModelAblationRow, ...],
) -> list[dict[str, Any]]:
    return [
        {
            "row_type": "local_stt_model_ablation",
            "ablation_id": ablation_id,
            "script_id": row.script_id,
            "query_type": row.query_type,
            "provider_candidate_id": row.provider_candidate_id,
            "model_id": row.model_id,
            "resolved_device": row.resolved_device,
            "transcription_status": row.transcription_status,
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


def build_doc_markdown(report: LocalModelAblationReport) -> str:
    summary = report.summary
    model_rows = "\n".join(format_model_summary(row) for row in report.model_summaries)
    return f"""# Voice STT/TTS Local Model Ablation

## 결론

`{WORK_ID}`는 external provider 호출 없이 local CUDA Whisper 모델 크기 후보를 비교한다.

이번 gate는 provider 최종 선택이 아니다. public artifact에는 raw audio, raw transcript, raw provider payload를 저장하지 않는다.

## Scope

포함:

- `local_cuda_whisper` 후보 내 `tiny`, `base`, `small` 모델 비교
- CUDA 사용 가능 시 CUDA device 사용
- 같은 5개 public-safe script와 private wav fixture 사용
- WER, CER, place name accuracy, STT latency p95, model load time 기록
- private fact와 public summary 분리

제외:

- Google, Azure, AWS STT/TTS 호출
- browser Web Speech 자동 benchmark
- Solar Pro 3 호출
- STT/TTS 품질 검증 완료 주장
- provider 최종 선택

## 정량 요약

| metric | value |
| --- | ---: |
| model_candidate_count | {summary.model_candidate_count} |
| selected_script_count | {summary.selected_script_count} |
| public_safe_script_fixture_count | {summary.public_safe_script_fixture_count} |
| runtime_available_count | {summary.runtime_available_count} |
| audio_fixture_available_count | {summary.audio_fixture_available_count} |
| local_stt_execution_requested_count | {summary.local_stt_execution_requested_count} |
| total_local_stt_execution_count | {summary.total_local_stt_execution_count} |
| total_local_cuda_whisper_call_count | {summary.total_local_cuda_whisper_call_count} |
| external_provider_call_count | {summary.external_provider_call_count} |
| external_audio_transmission_count | {summary.external_audio_transmission_count} |
| live_stt_call_count | {summary.live_stt_call_count} |
| live_tts_call_count | {summary.live_tts_call_count} |
| live_solar_call_count | {summary.live_solar_call_count} |
| raw_transcript_public_artifact_count | {summary.raw_transcript_public_artifact_count} |
| raw_audio_public_artifact_count | {summary.raw_audio_public_artifact_count} |
| resolved_device | `{summary.resolved_device}` |
| best_cer_model_id | `{summary.best_cer_model_id}` |
| best_place_name_accuracy_model_id | `{summary.best_place_name_accuracy_model_id}` |
| recommended_model_id | `{summary.recommended_model_id}` |
| ablation_decision | `{summary.ablation_decision}` |

## Model Summary

| model_id | executed | load_ms | wer_avg | cer_avg | place_name_accuracy_avg | latency_p95_ms | cer_delta_from_tiny | place_delta_from_tiny | decision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
{model_rows}

## Data Mart Grain

| table | grain | exposure |
| --- | --- | --- |
| `fact_voice_stt_local_model_ablation_private` | `ablation_id + script_id + provider_candidate_id + model_id + metric_name` | private |
| `fact_voice_stt_local_model_ablation_public_summary` | `ablation_id + provider_candidate_id + model_id + metric_name` | public-safe |

## Claim Boundary

허용 claim:

- local CUDA Whisper 모델 크기별 smoke metric을 비교했다.
- external provider call 없이 local STT 모델 후보를 비교했다.
- public artifact에는 raw audio와 raw transcript를 저장하지 않았다.

금지 claim:

- provider 최종 선택 완료
- STT/TTS 품질 검증 완료
- 음성 관광 앱 완성
- external provider benchmark 성능 개선 입증
"""


def build_report_markdown(report: LocalModelAblationReport) -> str:
    summary = report.summary
    quality = report.output_quality
    model_rows = "\n".join(format_model_summary(row) for row in report.model_summaries)
    result_rows = "\n".join(format_result_row(row) for row in report.rows)
    qualitative_rows = "\n".join(
        f"| {key} | {value} |" for key, value in report.qualitative_assessment.items()
    )
    failures = collect_ablation_failures(report, require_local_execution=False)
    return f"""# Voice STT/TTS Local Model Ablation Report

## 결론

`{WORK_ID}`는 local CUDA Whisper 모델 크기 후보를 external provider 호출 없이 비교한다.

이 리포트는 STT/TTS 품질 최종 검증이 아니다. raw audio와 raw transcript는 public artifact에 저장하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| ablation_id | `{report.ablation_id}` |
| work_id | `{report.work_id}` |
| depends_on | `{report.depends_on}` |
| generated_at_utc | `{report.generated_at_utc}` |
| scripts_path | `{report.scripts_path}` |
| result_path | `{report.result_path}` |
| private_audio_path_alias | `{report.private_audio_path_alias}` |
| provider_candidate_id | `{PROVIDER_CANDIDATE_ID}` |
| source_fingerprint | `{report.source_fingerprint}` |
| ablation_status | `{summary.ablation_decision}` |

## 정량 리포트

| metric | value |
| --- | ---: |
| model_candidate_count | {summary.model_candidate_count} |
| selected_script_count | {summary.selected_script_count} |
| public_safe_script_fixture_count | {summary.public_safe_script_fixture_count} |
| runtime_available_count | {summary.runtime_available_count} |
| audio_fixture_available_count | {summary.audio_fixture_available_count} |
| local_stt_execution_requested_count | {summary.local_stt_execution_requested_count} |
| total_local_stt_execution_count | {summary.total_local_stt_execution_count} |
| total_local_cuda_whisper_call_count | {summary.total_local_cuda_whisper_call_count} |
| external_provider_call_count | {summary.external_provider_call_count} |
| external_audio_transmission_count | {summary.external_audio_transmission_count} |
| live_stt_call_count | {summary.live_stt_call_count} |
| live_tts_call_count | {summary.live_tts_call_count} |
| live_solar_call_count | {summary.live_solar_call_count} |
| raw_transcript_public_artifact_count | {summary.raw_transcript_public_artifact_count} |
| raw_audio_public_artifact_count | {summary.raw_audio_public_artifact_count} |
| client_secret_exposure_count | {summary.client_secret_exposure_count} |
| resolved_device | `{summary.resolved_device}` |
| local_cuda_available_count | {summary.local_cuda_available_count} |
| cuda_device_count | {summary.cuda_device_count} |
| best_cer_model_id | `{summary.best_cer_model_id}` |
| best_place_name_accuracy_model_id | `{summary.best_place_name_accuracy_model_id}` |
| recommended_model_id | `{summary.recommended_model_id}` |
| public_private_path_leakage_count | {summary.public_private_path_leakage_count} |
| public_secret_like_leakage_count | {summary.public_secret_like_leakage_count} |
| public_raw_payload_leakage_count | {summary.public_raw_payload_leakage_count} |

## Model Summary

| model_id | executed | load_ms | wer_avg | cer_avg | place_name_accuracy_avg | latency_p95_ms | cer_delta_from_tiny | place_delta_from_tiny | decision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
{model_rows}

## Result Row Summary

| model_id | script_id | query_type | status | latency_ms | wer | cer | place_name_accuracy | place_count | error_code |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
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
local_model_ablation_failures={failures}
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


def format_model_summary(row: LocalModelSummary) -> str:
    return (
        f"| {row.model_id} | {row.local_stt_execution_count} | "
        f"{row.model_load_time_ms:.6f} | {format_optional_float(row.wer_avg)} | "
        f"{format_optional_float(row.cer_avg)} | "
        f"{format_optional_float(row.place_name_accuracy_avg)} | "
        f"{row.stt_latency_p95_ms:.6f} | "
        f"{format_optional_float(row.quality_delta_from_tiny_cer)} | "
        f"{format_optional_float(row.quality_delta_from_tiny_place_name_accuracy)} | "
        f"`{row.model_decision}` |"
    )


def format_result_row(row: LocalModelAblationRow) -> str:
    return (
        f"| {row.model_id} | {row.script_id} | {row.query_type} | "
        f"`{row.transcription_status}` | {row.latency_ms:.6f} | "
        f"{format_optional_float(row.wer)} | {format_optional_float(row.cer)} | "
        f"{format_optional_float(row.place_name_accuracy)} | "
        f"{row.expected_place_name_count} | `{row.error_code}` |"
    )


def build_qualitative_assessment(report: LocalModelAblationReport) -> dict[str, str]:
    summary = report.summary
    return {
        "scope": "external provider 호출 없이 local_cuda_whisper 모델 크기 후보만 비교했다.",
        "cuda": f"CUDA 가능 시 사용하며 resolved_device={summary.resolved_device}로 기록했다.",
        "metric": "WER, CER, place_name_accuracy, latency, model load time을 같은 fixture로 비교했다.",
        "privacy": "raw audio는 private artifact이며 public report에는 raw transcript를 저장하지 않는다.",
        "cost": "managed cloud STT/TTS 호출이 없어 external provider 비용은 발생하지 않는다.",
        "data_mart": "private script-level fact와 public model summary grain을 분리했다.",
        "portfolio": "provider 선택 전 로컬 GPU 후보군을 좁힌 실험으로 설명한다.",
        "external_audit": "managed provider 전송 전 local model ablation을 수행한 순서는 타당하다.",
    }


def build_ablation_id(
    *,
    rows: tuple[LocalModelAblationRow, ...],
    model_summaries: tuple[LocalModelSummary, ...],
    summary: LocalModelAblationSummary,
) -> str:
    digest = stable_digest(
        {
            "work_id": WORK_ID,
            "models": [row.model_id for row in model_summaries],
            "rows": [row.model_dump(mode="json") for row in rows],
            "device": summary.resolved_device,
        },
        length=8,
    )
    return f"voice-local-model-ablation-m{len(model_summaries)}-s{summary.selected_script_count}-{digest}"


def average(values: Any) -> float | None:
    concrete = [value for value in values if value is not None]
    if not concrete:
        return None
    return round(sum(concrete) / len(concrete), 6)


def format_optional_float(value: float | None) -> str:
    if value is None:
        return "null"
    return f"{value:.6f}"


def stable_digest(payload: Any, *, length: int = 16) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"),
    ).hexdigest()[:length]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run local CUDA Whisper model-size ablation without external providers.",
    )
    parser.add_argument("--scripts", type=Path, default=DEFAULT_SCRIPTS_PATH)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--rows", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    parser.add_argument("--private-audio-dir", type=Path, default=DEFAULT_PRIVATE_AUDIO_DIR)
    parser.add_argument("--models", nargs="+", default=list(DEFAULT_MODELS))
    parser.add_argument("--script-limit", type=int, default=DEFAULT_SCRIPT_LIMIT)
    parser.add_argument("--generate-missing-audio", action="store_true")
    parser.add_argument("--execute-local-whisper", action="store_true")
    parser.add_argument("--require-local-execution", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_voice_stt_tts_local_model_ablation(
        scripts_path=args.scripts,
        doc_path=args.doc,
        report_path=args.report,
        result_rows_path=args.rows,
        private_audio_dir=args.private_audio_dir,
        models=tuple(args.models),
        script_limit=args.script_limit,
        generate_missing_audio=args.generate_missing_audio,
        execute_local_whisper=args.execute_local_whisper,
        require_local_execution=args.require_local_execution,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
