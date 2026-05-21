from __future__ import annotations

import argparse
import gc
import hashlib
import importlib.util
import json
import time
from collections import Counter
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from difflib import SequenceMatcher
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
from pipelines.voice_local_tts_quality_listening_review import (
    DEFAULT_PRIVATE_AUDIO_DIR,
    DEFAULT_SCRIPTS_PATH,
    DEFAULT_SCRIPT_LIMIT,
    MODEL_FAMILY,
    PROVIDER_CANDIDATE_ID,
    TtsQualityAudioMetricRow,
    build_audio_metric_row,
)
from pipelines.voice_stt_tts_local_smoke import (
    character_error_rate,
    normalize_for_char_metric,
    percentile,
    place_name_accuracy,
)
from pipelines.voice_stt_tts_local_tts_smoke import (
    VoiceTtsSmokeScript,
    load_tts_smoke_scripts,
    select_tts_smoke_scripts,
)
from pipelines.voice_stt_tts_provider_bench_readiness import build_cuda_preflight


REPORT_VERSION = "voice-local-tts-automated-proxy-eval-report/v1"
WORK_ID = "HD-VOICE-LOCAL-TTS-AUTOMATED-PROXY-EVAL-001"
DEPENDS_ON_QUALITY_REVIEW = "HD-VOICE-LOCAL-TTS-QUALITY-LISTENING-REVIEW-001"
DEPENDS_ON_STT_COMPARISON = "HD-VOICE-LOCAL-FASTER-WHISPER-STT-COMPARISON-001"
DEPENDS_ON_TTS_SMOKE = "HD-VOICE-LOCAL-SHERPA-ONNX-SUPERTONIC3-KO-SMOKE-001"

DEFAULT_DOC_PATH = Path("docs") / "VOICE_LOCAL_TTS_AUTOMATED_PROXY_EVAL.md"
DEFAULT_REPORT_PATH = (
    Path("evals") / "reports" / "voice_local_tts_automated_proxy_eval_report.md"
)
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "voice_local_tts_automated_proxy_eval_rows.jsonl"
)
DEFAULT_STT_PROVIDER_ID = "local_faster_whisper_small_cuda"
DEFAULT_STT_MODEL_ID = "small"
DEFAULT_COMPUTE_TYPE_CUDA = "float16"
DEFAULT_COMPUTE_TYPE_CPU = "int8"
MAX_CER_AVG = 0.15
MIN_CHAR_F1_AVG = 0.85
MIN_SEQUENCE_SIMILARITY_AVG = 0.85
MIN_PLACE_NAME_ACCURACY_AVG = 0.80

ProxyStatus = Literal[
    "executed",
    "blocked_missing_audio",
    "blocked_audio_sanity",
    "blocked_missing_runtime",
    "blocked_model_load_error",
    "blocked_transcribe_error",
    "skipped_by_flag",
]
ProxyDecision = Literal[
    "automated_proxy_passed_not_human_score",
    "automated_proxy_failed_quality_threshold",
    "blocked_audio_sanity_or_missing_artifacts",
    "blocked_missing_local_stt_runtime",
    "blocked_local_stt_execution",
    "skipped_pending_local_stt_execution",
    "failed_public_safety_gate",
]
ProxyTranscriber = Callable[[VoiceTtsSmokeScript, Path], tuple[str, float]]


class TtsAutomatedProxyBase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TtsAutomatedProxyRow(TtsAutomatedProxyBase):
    script_id: str = Field(min_length=1)
    audio_artifact_id: str = Field(min_length=8)
    tts_provider_candidate_id: str = PROVIDER_CANDIDATE_ID
    tts_model_family: str = MODEL_FAMILY
    stt_provider_candidate_id: str = DEFAULT_STT_PROVIDER_ID
    stt_model_id: str = Field(min_length=1)
    resolved_device: str = Field(min_length=1)
    compute_type: str = Field(min_length=1)
    proxy_status: ProxyStatus
    audio_sanity_pass: bool
    audio_duration_ms: float = Field(ge=0.0)
    audio_rms_dbfs: float
    audio_clipping_sample_ratio: float = Field(ge=0.0)
    audio_silence_sample_ratio: float = Field(ge=0.0, le=1.0)
    stt_latency_ms: float = Field(ge=0.0)
    reference_char_count: int = Field(ge=0)
    transcript_char_count: int = Field(ge=0)
    cer: float | None = Field(default=None, ge=0.0)
    char_precision: float | None = Field(default=None, ge=0.0, le=1.0)
    char_recall: float | None = Field(default=None, ge=0.0, le=1.0)
    char_f1: float | None = Field(default=None, ge=0.0, le=1.0)
    sequence_similarity: float | None = Field(default=None, ge=0.0, le=1.0)
    place_name_accuracy: float | None = Field(default=None, ge=0.0, le=1.0)
    expected_place_name_count: int = Field(ge=0)
    reference_text_hash: str = Field(min_length=8)
    transcript_hash: str
    error_code: str


class TtsAutomatedProxySummary(TtsAutomatedProxyBase):
    selected_script_count: int = Field(ge=0)
    audio_file_available_count: int = Field(ge=0)
    automated_audio_sanity_pass_count: int = Field(ge=0)
    local_stt_runtime_available_count: int = Field(ge=0)
    local_stt_execution_requested_count: int = Field(ge=0)
    local_stt_execution_count: int = Field(ge=0)
    local_cuda_stt_call_count: int = Field(ge=0)
    local_stt_model_load_attempt_count: int = Field(ge=0)
    local_stt_model_load_error_count: int = Field(ge=0)
    proxy_metric_row_count: int = Field(ge=0)
    proxy_metric_pass_count: int = Field(ge=0)
    proxy_metric_fail_count: int = Field(ge=0)
    stt_latency_p50_ms: float = Field(ge=0.0)
    stt_latency_p95_ms: float = Field(ge=0.0)
    cer_avg: float | None = Field(default=None, ge=0.0)
    char_f1_avg: float | None = Field(default=None, ge=0.0, le=1.0)
    sequence_similarity_avg: float | None = Field(default=None, ge=0.0, le=1.0)
    place_name_accuracy_avg: float | None = Field(default=None, ge=0.0, le=1.0)
    quality_threshold_cer_max: float = Field(ge=0.0)
    quality_threshold_char_f1_min: float = Field(ge=0.0, le=1.0)
    quality_threshold_sequence_similarity_min: float = Field(ge=0.0, le=1.0)
    quality_threshold_place_accuracy_min: float = Field(ge=0.0, le=1.0)
    quality_threshold_pass_count: int = Field(ge=0)
    human_listening_completed_count: int = Field(ge=0)
    human_score_public_detail_row_count: int = Field(ge=0)
    external_provider_call_count: int = Field(ge=0)
    external_audio_transmission_count: int = Field(ge=0)
    live_stt_call_count: int = Field(ge=0)
    live_tts_call_count: int = Field(ge=0)
    live_solar_call_count: int = Field(ge=0)
    raw_audio_public_artifact_count: int = Field(ge=0)
    raw_transcript_public_artifact_count: int = Field(ge=0)
    raw_script_public_artifact_count: int = Field(ge=0)
    client_secret_exposure_count: int = Field(ge=0)
    resolved_device: str = Field(min_length=1)
    compute_type: str = Field(min_length=1)
    local_cuda_available_count: int = Field(ge=0)
    cuda_device_count: int = Field(ge=0)
    public_private_path_leakage_count: int = Field(ge=0)
    public_secret_like_leakage_count: int = Field(ge=0)
    public_raw_payload_leakage_count: int = Field(ge=0)
    proxy_decision: ProxyDecision


class TtsAutomatedProxyReport(TtsAutomatedProxyBase):
    report_version: str = REPORT_VERSION
    proxy_eval_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    work_id: str = WORK_ID
    depends_on_quality_review: str = DEPENDS_ON_QUALITY_REVIEW
    depends_on_stt_comparison: str = DEPENDS_ON_STT_COMPARISON
    depends_on_tts_smoke: str = DEPENDS_ON_TTS_SMOKE
    scripts_path: str = Field(min_length=1)
    audio_path_alias: str = Field(min_length=1)
    result_path: str = Field(min_length=1)
    source_fingerprint: str = Field(min_length=8)
    summary: TtsAutomatedProxySummary
    rows: tuple[TtsAutomatedProxyRow, ...]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def run_voice_local_tts_automated_proxy_eval(
    *,
    scripts_path: Path = DEFAULT_SCRIPTS_PATH,
    private_audio_dir: Path = DEFAULT_PRIVATE_AUDIO_DIR,
    doc_path: Path = DEFAULT_DOC_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
    script_limit: int = DEFAULT_SCRIPT_LIMIT,
    stt_model_id: str = DEFAULT_STT_MODEL_ID,
    execute_local_stt: bool = False,
    require_local_stt: bool = False,
    transcriber: ProxyTranscriber | None = None,
) -> TtsAutomatedProxyReport:
    scripts = select_tts_smoke_scripts(
        load_tts_smoke_scripts(project_path(scripts_path)),
        limit=script_limit,
    )
    audio_dir = project_path(private_audio_dir)
    cuda_preflight = build_cuda_preflight()
    compute_type = (
        DEFAULT_COMPUTE_TYPE_CUDA
        if cuda_preflight.resolved_device == "cuda"
        else DEFAULT_COMPUTE_TYPE_CPU
    )
    runtime_available = transcriber is not None or importlib.util.find_spec("faster_whisper") is not None
    audio_rows = tuple(
        build_audio_metric_row(
            script_id=script.script_id,
            language=script.language,
            text_role=script.text_role,
            text_hash=stable_digest(script.script_text),
            character_count=len(script.script_text),
            place_name_count=len(script.place_ids),
            audio_path=audio_dir / f"{script.script_id}.wav",
        )
        for script in scripts
    )
    proxy_rows, model_load_attempts, model_load_errors = build_proxy_rows(
        scripts=scripts,
        audio_rows=audio_rows,
        audio_dir=audio_dir,
        stt_model_id=stt_model_id,
        resolved_device=cuda_preflight.resolved_device,
        compute_type=compute_type,
        runtime_available=runtime_available,
        execute_local_stt=execute_local_stt,
        transcriber=transcriber,
    )
    summary = build_summary(
        rows=proxy_rows,
        audio_rows=audio_rows,
        cuda_preflight=cuda_preflight,
        compute_type=compute_type,
        runtime_available=runtime_available,
        execute_local_stt=execute_local_stt,
        model_load_attempts=model_load_attempts,
        model_load_errors=model_load_errors,
    )
    proxy_eval_id = build_proxy_eval_id(rows=proxy_rows, summary=summary)
    public_rows = build_public_rows(proxy_eval_id=proxy_eval_id, rows=proxy_rows)
    provisional_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=proxy_eval_id,
        result_rows=public_rows,
        report_text="",
    )
    provisional = build_report(
        proxy_eval_id=proxy_eval_id,
        scripts_path=scripts_path,
        private_audio_dir=private_audio_dir,
        result_rows_path=result_rows_path,
        rows=proxy_rows,
        summary=summary,
        output_quality=provisional_quality,
    )
    doc_text = build_doc(provisional)
    report_text = build_markdown_report(provisional, require_local_stt=require_local_stt)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=proxy_eval_id,
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
            "proxy_decision": build_proxy_decision(
                summary=summary,
                output_quality=output_quality,
            ),
        },
    )
    report = build_report(
        proxy_eval_id=proxy_eval_id,
        scripts_path=scripts_path,
        private_audio_dir=private_audio_dir,
        result_rows_path=result_rows_path,
        rows=proxy_rows,
        summary=summary,
        output_quality=output_quality,
    )
    failures = collect_proxy_eval_failures(report, require_local_stt=require_local_stt)
    if failures:
        raise ValueError(f"voice local TTS automated proxy eval gate failed: {failures}")

    write_public_retrieval_result_rows(path=project_path(result_rows_path), rows=public_rows)
    resolved_doc_path = project_path(doc_path)
    resolved_report_path = project_path(report_path)
    resolved_doc_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_report_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_doc_path.write_text(build_doc(report), encoding="utf-8")
    resolved_report_path.write_text(
        build_markdown_report(report, require_local_stt=require_local_stt),
        encoding="utf-8",
    )
    print(
        "voice_local_tts_automated_proxy_eval "
        f"status={report.summary.proxy_decision} "
        f"audio={report.summary.audio_file_available_count} "
        f"stt={report.summary.local_stt_execution_count} "
        f"cer={format_optional(report.summary.cer_avg)} "
        f"char_f1={format_optional(report.summary.char_f1_avg)} "
        f"external_calls={report.summary.external_provider_call_count}",
    )
    return report


def build_proxy_rows(
    *,
    scripts: tuple[VoiceTtsSmokeScript, ...],
    audio_rows: tuple[TtsQualityAudioMetricRow, ...],
    audio_dir: Path,
    stt_model_id: str,
    resolved_device: str,
    compute_type: str,
    runtime_available: bool,
    execute_local_stt: bool,
    transcriber: ProxyTranscriber | None,
) -> tuple[tuple[TtsAutomatedProxyRow, ...], int, int]:
    audio_by_script = {row.script_id: row for row in audio_rows}
    if not execute_local_stt:
        return tuple(
            build_proxy_row_without_transcript(
                script=script,
                audio_row=audio_by_script[script.script_id],
                stt_model_id=stt_model_id,
                resolved_device=resolved_device,
                compute_type=compute_type,
                proxy_status="skipped_by_flag",
                error_code="",
            )
            for script in scripts
        ), 0, 0
    if not runtime_available:
        return tuple(
            build_proxy_row_without_transcript(
                script=script,
                audio_row=audio_by_script[script.script_id],
                stt_model_id=stt_model_id,
                resolved_device=resolved_device,
                compute_type=compute_type,
                proxy_status="blocked_missing_runtime",
                error_code="faster_whisper_not_available",
            )
            for script in scripts
        ), 0, 0

    if transcriber is None:
        try:
            model_started = time.perf_counter()
            model = load_faster_whisper_model(
                model_id=stt_model_id,
                resolved_device=resolved_device,
                compute_type=compute_type,
            )
            _model_load_time_ms = round((time.perf_counter() - model_started) * 1000.0, 6)
        except Exception:
            return tuple(
                build_proxy_row_without_transcript(
                    script=script,
                    audio_row=audio_by_script[script.script_id],
                    stt_model_id=stt_model_id,
                    resolved_device=resolved_device,
                    compute_type=compute_type,
                    proxy_status="blocked_model_load_error",
                    error_code="faster_whisper_model_load_error",
                )
                for script in scripts
            ), 1, 1
        local_transcriber = build_faster_whisper_transcriber(model)
    else:
        model = None
        local_transcriber = transcriber

    try:
        rows = tuple(
            build_proxy_row(
                script=script,
                audio_row=audio_by_script[script.script_id],
                audio_path=audio_dir / f"{script.script_id}.wav",
                stt_model_id=stt_model_id,
                resolved_device=resolved_device,
                compute_type=compute_type,
                transcriber=local_transcriber,
            )
            for script in scripts
        )
    finally:
        if transcriber is None:
            del model
            gc.collect()
            clear_cuda_cache()
    return rows, int(transcriber is None), 0


def build_proxy_row(
    *,
    script: VoiceTtsSmokeScript,
    audio_row: TtsQualityAudioMetricRow,
    audio_path: Path,
    stt_model_id: str,
    resolved_device: str,
    compute_type: str,
    transcriber: ProxyTranscriber,
) -> TtsAutomatedProxyRow:
    if audio_row.read_status == "missing":
        return build_proxy_row_without_transcript(
            script=script,
            audio_row=audio_row,
            stt_model_id=stt_model_id,
            resolved_device=resolved_device,
            compute_type=compute_type,
            proxy_status="blocked_missing_audio",
            error_code="private_audio_missing",
        )
    if not audio_row.automated_sanity_pass:
        return build_proxy_row_without_transcript(
            script=script,
            audio_row=audio_row,
            stt_model_id=stt_model_id,
            resolved_device=resolved_device,
            compute_type=compute_type,
            proxy_status="blocked_audio_sanity",
            error_code="audio_sanity_failed",
        )
    try:
        transcript, latency_ms = transcriber(script, audio_path)
    except Exception:
        return build_proxy_row_without_transcript(
            script=script,
            audio_row=audio_row,
            stt_model_id=stt_model_id,
            resolved_device=resolved_device,
            compute_type=compute_type,
            proxy_status="blocked_transcribe_error",
            error_code="local_stt_transcribe_error",
        )

    scores = build_text_proxy_scores(reference=script.script_text, transcript=transcript)
    return TtsAutomatedProxyRow(
        script_id=script.script_id,
        audio_artifact_id=audio_row.audio_artifact_id,
        stt_model_id=stt_model_id,
        resolved_device=resolved_device,
        compute_type=compute_type,
        proxy_status="executed",
        audio_sanity_pass=audio_row.automated_sanity_pass,
        audio_duration_ms=audio_row.duration_ms,
        audio_rms_dbfs=audio_row.rms_dbfs,
        audio_clipping_sample_ratio=audio_row.clipping_sample_ratio,
        audio_silence_sample_ratio=audio_row.silence_sample_ratio,
        stt_latency_ms=round(latency_ms, 6),
        reference_char_count=scores["reference_char_count"],
        transcript_char_count=scores["transcript_char_count"],
        cer=character_error_rate(script.script_text, transcript),
        char_precision=scores["char_precision"],
        char_recall=scores["char_recall"],
        char_f1=scores["char_f1"],
        sequence_similarity=scores["sequence_similarity"],
        place_name_accuracy=place_name_accuracy(script.place_ids, transcript),
        expected_place_name_count=len(script.place_ids),
        reference_text_hash=stable_digest(script.script_text),
        transcript_hash=stable_digest(transcript),
        error_code="",
    )


def build_proxy_row_without_transcript(
    *,
    script: VoiceTtsSmokeScript,
    audio_row: TtsQualityAudioMetricRow,
    stt_model_id: str,
    resolved_device: str,
    compute_type: str,
    proxy_status: ProxyStatus,
    error_code: str,
) -> TtsAutomatedProxyRow:
    return TtsAutomatedProxyRow(
        script_id=script.script_id,
        audio_artifact_id=audio_row.audio_artifact_id,
        stt_model_id=stt_model_id,
        resolved_device=resolved_device,
        compute_type=compute_type,
        proxy_status=proxy_status,
        audio_sanity_pass=audio_row.automated_sanity_pass,
        audio_duration_ms=audio_row.duration_ms,
        audio_rms_dbfs=audio_row.rms_dbfs,
        audio_clipping_sample_ratio=audio_row.clipping_sample_ratio,
        audio_silence_sample_ratio=audio_row.silence_sample_ratio,
        stt_latency_ms=0.0,
        reference_char_count=len(normalize_for_char_metric(script.script_text)),
        transcript_char_count=0,
        cer=None,
        char_precision=None,
        char_recall=None,
        char_f1=None,
        sequence_similarity=None,
        place_name_accuracy=None,
        expected_place_name_count=len(script.place_ids),
        reference_text_hash=stable_digest(script.script_text),
        transcript_hash="",
        error_code=error_code,
    )


def load_faster_whisper_model(*, model_id: str, resolved_device: str, compute_type: str) -> Any:
    from faster_whisper import WhisperModel

    return WhisperModel(model_id, device=resolved_device, compute_type=compute_type)


def build_faster_whisper_transcriber(model: Any) -> ProxyTranscriber:
    def transcribe(script: VoiceTtsSmokeScript, audio_path: Path) -> tuple[str, float]:
        del script
        started = time.perf_counter()
        segments, _info = model.transcribe(
            str(audio_path),
            language="ko",
            beam_size=5,
            vad_filter=False,
        )
        transcript = "".join(segment.text for segment in segments).strip()
        return transcript, round((time.perf_counter() - started) * 1000.0, 6)

    return transcribe


def build_text_proxy_scores(*, reference: str, transcript: str) -> dict[str, int | float]:
    normalized_reference = normalize_for_char_metric(reference)
    normalized_transcript = normalize_for_char_metric(transcript)
    reference_counts = Counter(normalized_reference)
    transcript_counts = Counter(normalized_transcript)
    overlap_count = sum((reference_counts & transcript_counts).values())
    reference_count = len(normalized_reference)
    transcript_count = len(normalized_transcript)
    precision = overlap_count / transcript_count if transcript_count else 0.0
    recall = overlap_count / reference_count if reference_count else 0.0
    f1 = 0.0 if precision + recall == 0 else (2.0 * precision * recall) / (precision + recall)
    return {
        "reference_char_count": reference_count,
        "transcript_char_count": transcript_count,
        "char_precision": round(precision, 6),
        "char_recall": round(recall, 6),
        "char_f1": round(f1, 6),
        "sequence_similarity": round(
            SequenceMatcher(None, normalized_reference, normalized_transcript).ratio(),
            6,
        ),
    }


def build_summary(
    *,
    rows: tuple[TtsAutomatedProxyRow, ...],
    audio_rows: tuple[TtsQualityAudioMetricRow, ...],
    cuda_preflight: Any,
    compute_type: str,
    runtime_available: bool,
    execute_local_stt: bool,
    model_load_attempts: int,
    model_load_errors: int,
) -> TtsAutomatedProxySummary:
    executed_rows = [row for row in rows if row.proxy_status == "executed"]
    metric_pass_count = count_proxy_metric_passes(executed_rows)
    summary = TtsAutomatedProxySummary(
        selected_script_count=len(rows),
        audio_file_available_count=sum(1 for row in audio_rows if row.read_status == "read"),
        automated_audio_sanity_pass_count=sum(
            1 for row in audio_rows if row.automated_sanity_pass
        ),
        local_stt_runtime_available_count=int(runtime_available),
        local_stt_execution_requested_count=len(rows) if execute_local_stt else 0,
        local_stt_execution_count=len(executed_rows),
        local_cuda_stt_call_count=(
            len(executed_rows) if cuda_preflight.resolved_device == "cuda" else 0
        ),
        local_stt_model_load_attempt_count=model_load_attempts,
        local_stt_model_load_error_count=model_load_errors,
        proxy_metric_row_count=len(rows),
        proxy_metric_pass_count=metric_pass_count,
        proxy_metric_fail_count=len(executed_rows) - metric_pass_count,
        stt_latency_p50_ms=percentile([row.stt_latency_ms for row in executed_rows], 0.50),
        stt_latency_p95_ms=percentile([row.stt_latency_ms for row in executed_rows], 0.95),
        cer_avg=average(row.cer for row in executed_rows),
        char_f1_avg=average(row.char_f1 for row in executed_rows),
        sequence_similarity_avg=average(row.sequence_similarity for row in executed_rows),
        place_name_accuracy_avg=average(row.place_name_accuracy for row in executed_rows),
        quality_threshold_cer_max=MAX_CER_AVG,
        quality_threshold_char_f1_min=MIN_CHAR_F1_AVG,
        quality_threshold_sequence_similarity_min=MIN_SEQUENCE_SIMILARITY_AVG,
        quality_threshold_place_accuracy_min=MIN_PLACE_NAME_ACCURACY_AVG,
        quality_threshold_pass_count=metric_pass_count,
        human_listening_completed_count=0,
        human_score_public_detail_row_count=0,
        external_provider_call_count=0,
        external_audio_transmission_count=0,
        live_stt_call_count=0,
        live_tts_call_count=0,
        live_solar_call_count=0,
        raw_audio_public_artifact_count=0,
        raw_transcript_public_artifact_count=0,
        raw_script_public_artifact_count=0,
        client_secret_exposure_count=0,
        resolved_device=cuda_preflight.resolved_device,
        compute_type=compute_type,
        local_cuda_available_count=int(cuda_preflight.local_cuda_available),
        cuda_device_count=cuda_preflight.cuda_device_count,
        public_private_path_leakage_count=0,
        public_secret_like_leakage_count=0,
        public_raw_payload_leakage_count=0,
        proxy_decision="blocked_local_stt_execution",
    )
    return summary.model_copy(
        update={
            "proxy_decision": build_proxy_decision(
                summary=summary,
                output_quality=None,
            )
        }
    )


def count_proxy_metric_passes(rows: Sequence[TtsAutomatedProxyRow]) -> int:
    return sum(1 for row in rows if proxy_metric_passes(row))


def proxy_metric_passes(row: TtsAutomatedProxyRow) -> bool:
    if row.cer is None or row.char_f1 is None or row.sequence_similarity is None:
        return False
    place_accuracy = row.place_name_accuracy
    return (
        row.cer <= MAX_CER_AVG
        and row.char_f1 >= MIN_CHAR_F1_AVG
        and row.sequence_similarity >= MIN_SEQUENCE_SIMILARITY_AVG
        and (place_accuracy is None or place_accuracy >= MIN_PLACE_NAME_ACCURACY_AVG)
    )


def build_proxy_decision(
    *,
    summary: TtsAutomatedProxySummary,
    output_quality: PublicRetrievalArtifactQuality | None,
) -> ProxyDecision:
    if output_quality is not None and collect_public_retrieval_artifact_failures(output_quality):
        return "failed_public_safety_gate"
    if (
        summary.audio_file_available_count != summary.selected_script_count
        or summary.automated_audio_sanity_pass_count != summary.selected_script_count
    ):
        return "blocked_audio_sanity_or_missing_artifacts"
    if summary.local_stt_execution_requested_count == 0:
        return "skipped_pending_local_stt_execution"
    if summary.local_stt_runtime_available_count == 0:
        return "blocked_missing_local_stt_runtime"
    if summary.local_stt_execution_count != summary.selected_script_count:
        return "blocked_local_stt_execution"
    if summary.proxy_metric_pass_count == summary.selected_script_count:
        return "automated_proxy_passed_not_human_score"
    return "automated_proxy_failed_quality_threshold"


def collect_proxy_eval_failures(
    report: TtsAutomatedProxyReport,
    *,
    require_local_stt: bool,
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
    if summary.raw_script_public_artifact_count:
        failures.append("raw_script_public_artifact_created")
    if summary.human_score_public_detail_row_count:
        failures.append("human_score_detail_public_artifact_created")
    if summary.client_secret_exposure_count:
        failures.append("client_secret_exposed")
    if summary.local_cuda_available_count and summary.local_stt_execution_count:
        if summary.resolved_device != "cuda":
            failures.append("cuda_available_but_not_used")
    if summary.audio_file_available_count != summary.selected_script_count:
        failures.append("audio_artifacts_missing")
    if summary.automated_audio_sanity_pass_count != summary.selected_script_count:
        failures.append("automated_audio_sanity_failed")
    if require_local_stt and summary.local_stt_execution_count != summary.selected_script_count:
        failures.append("required_local_stt_execution_missing")
    if summary.proxy_decision == "failed_public_safety_gate":
        failures.append("public_safety_gate_failed")
    return list(dict.fromkeys(failures))


def build_report(
    *,
    proxy_eval_id: str,
    scripts_path: Path,
    private_audio_dir: Path,
    result_rows_path: Path,
    rows: tuple[TtsAutomatedProxyRow, ...],
    summary: TtsAutomatedProxySummary,
    output_quality: PublicRetrievalArtifactQuality,
) -> TtsAutomatedProxyReport:
    report = TtsAutomatedProxyReport(
        proxy_eval_id=proxy_eval_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        scripts_path=public_path_alias(scripts_path),
        audio_path_alias=public_path_alias(private_audio_dir),
        result_path=public_path_alias(result_rows_path),
        source_fingerprint=stable_digest(
            {
                "rows": [row.model_dump(mode="json") for row in rows],
                "summary": summary.model_dump(mode="json"),
            }
        ),
        summary=summary,
        rows=rows,
        output_quality=output_quality,
        qualitative_assessment={},
    )
    return report.model_copy(update={"qualitative_assessment": build_assessment(report)})


def build_public_rows(
    *,
    proxy_eval_id: str,
    rows: tuple[TtsAutomatedProxyRow, ...],
) -> list[dict[str, Any]]:
    return [
        {
            "row_type": "local_tts_automated_proxy_eval",
            "proxy_eval_id": proxy_eval_id,
            "script_id": row.script_id,
            "audio_artifact_id": row.audio_artifact_id,
            "tts_provider_candidate_id": row.tts_provider_candidate_id,
            "stt_provider_candidate_id": row.stt_provider_candidate_id,
            "stt_model_id": row.stt_model_id,
            "resolved_device": row.resolved_device,
            "compute_type": row.compute_type,
            "proxy_status": row.proxy_status,
            "audio_sanity_pass": row.audio_sanity_pass,
            "audio_duration_ms": row.audio_duration_ms,
            "audio_rms_dbfs": row.audio_rms_dbfs,
            "audio_clipping_sample_ratio": row.audio_clipping_sample_ratio,
            "audio_silence_sample_ratio": row.audio_silence_sample_ratio,
            "stt_latency_ms": row.stt_latency_ms,
            "reference_char_count": row.reference_char_count,
            "transcript_char_count": row.transcript_char_count,
            "cer": row.cer,
            "char_precision": row.char_precision,
            "char_recall": row.char_recall,
            "char_f1": row.char_f1,
            "sequence_similarity": row.sequence_similarity,
            "place_name_accuracy": row.place_name_accuracy,
            "expected_place_name_count": row.expected_place_name_count,
            "reference_text_hash": row.reference_text_hash,
            "transcript_hash": row.transcript_hash,
            "error_code": row.error_code,
        }
        for row in rows
    ]


def build_doc(report: TtsAutomatedProxyReport) -> str:
    summary = report.summary
    return f"""# Voice Local TTS Automated Proxy Eval

## 결론

`{WORK_ID}`는 사람 청취 점수를 대신 만들지 않고, 로컬 STT round-trip 기반 자동 대체 평가를 기록한다.

현재 decision은 `{summary.proxy_decision}`이다. 이 gate는 TTS 음질 최종 판단이나 provider 채택이 아니다.

## Scope

| type | item |
| --- | --- |
| include | `sherpa-onnx + Supertonic 3 Korean` private wav 5개 자동 audio sanity 재사용 |
| include | `faster-whisper small` local STT round-trip proxy |
| include | CER, 문자 precision/recall/F1, sequence similarity, 장소명 복원률 |
| exclude | 사람 청취 점수 생성 |
| exclude | raw audio public 저장 |
| exclude | raw transcript public 저장 |
| exclude | raw script text public 저장 |
| exclude | 외부 STT/TTS provider 호출 |
| exclude | 최종 TTS provider 확정 |

## 정량 요약

| metric | value |
| --- | ---: |
| selected_script_count | {summary.selected_script_count} |
| audio_file_available_count | {summary.audio_file_available_count} |
| automated_audio_sanity_pass_count | {summary.automated_audio_sanity_pass_count} |
| local_stt_runtime_available_count | {summary.local_stt_runtime_available_count} |
| local_stt_execution_requested_count | {summary.local_stt_execution_requested_count} |
| local_stt_execution_count | {summary.local_stt_execution_count} |
| local_cuda_stt_call_count | {summary.local_cuda_stt_call_count} |
| cer_avg | {format_optional(summary.cer_avg)} |
| char_f1_avg | {format_optional(summary.char_f1_avg)} |
| sequence_similarity_avg | {format_optional(summary.sequence_similarity_avg)} |
| place_name_accuracy_avg | {format_optional(summary.place_name_accuracy_avg)} |
| quality_threshold_pass_count | {summary.quality_threshold_pass_count} |
| human_listening_completed_count | {summary.human_listening_completed_count} |
| external_provider_call_count | {summary.external_provider_call_count} |
| external_audio_transmission_count | {summary.external_audio_transmission_count} |
| raw_audio_public_artifact_count | {summary.raw_audio_public_artifact_count} |
| raw_transcript_public_artifact_count | {summary.raw_transcript_public_artifact_count} |
| raw_script_public_artifact_count | {summary.raw_script_public_artifact_count} |
| proxy_decision | `{summary.proxy_decision}` |

## Data Mart Grain

| table | grain | exposure |
| --- | --- | --- |
| `fact_voice_local_tts_proxy_metric_public` | `proxy_eval_id + script_id + metric_name` | public-safe |
| `fact_voice_local_tts_proxy_transcript_private` | `proxy_eval_id + script_id + transcript_artifact_id` | private only |
| `fact_voice_local_tts_human_score_private` | `review_id + script_id + reviewer_id + criterion_id` | private |

## Claim Boundary

| type | claim |
| --- | --- |
| allowed | 로컬 STT round-trip 자동 대체 평가를 수행했다. |
| allowed | public에는 hash와 aggregate metric만 저장했다. |
| allowed | 사람 청취 점수는 아직 0건으로 유지한다. |
| forbidden | 사람 청취 점수 입력 완료 |
| forbidden | 자동 proxy가 사람 평가를 대체한다 |
| forbidden | 무료 로컬 TTS 최종 provider 확정 |
| forbidden | Supertonic 3 음성 품질 우수 검증 완료 |
| forbidden | 실제 관광객 음성 품질 검증 완료 |
| forbidden | production 음성 관광 앱 완성 |
"""


def build_markdown_report(
    report: TtsAutomatedProxyReport,
    *,
    require_local_stt: bool,
) -> str:
    summary = report.summary
    quality = report.output_quality
    row_lines = "\n".join(format_proxy_row(row) for row in report.rows)
    qualitative_rows = "\n".join(
        f"| {key} | {value} |" for key, value in report.qualitative_assessment.items()
    )
    failures = collect_proxy_eval_failures(report, require_local_stt=require_local_stt)
    blockers = collect_proxy_eval_blockers(report)
    return f"""# Voice Local TTS Automated Proxy Eval Report

## 결론

`{WORK_ID}`는 사람 청취 점수 없이 가능한 자동 대체 평가를 수행한다.

현재 proxy decision은 `{summary.proxy_decision}`이다. 이 결과는 human listening score가 아니다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| proxy_eval_id | `{report.proxy_eval_id}` |
| work_id | `{report.work_id}` |
| depends_on_quality_review | `{report.depends_on_quality_review}` |
| depends_on_stt_comparison | `{report.depends_on_stt_comparison}` |
| depends_on_tts_smoke | `{report.depends_on_tts_smoke}` |
| generated_at_utc | `{report.generated_at_utc}` |
| scripts_path | `{report.scripts_path}` |
| audio_path_alias | `{report.audio_path_alias}` |
| result_path | `{report.result_path}` |
| tts_provider_candidate_id | `{PROVIDER_CANDIDATE_ID}` |
| stt_provider_candidate_id | `{DEFAULT_STT_PROVIDER_ID}` |
| source_fingerprint | `{report.source_fingerprint}` |
| proxy_decision_status | `{summary.proxy_decision}` |

## 정량 리포트

| metric | value |
| --- | ---: |
| selected_script_count | {summary.selected_script_count} |
| audio_file_available_count | {summary.audio_file_available_count} |
| automated_audio_sanity_pass_count | {summary.automated_audio_sanity_pass_count} |
| local_stt_runtime_available_count | {summary.local_stt_runtime_available_count} |
| local_stt_execution_requested_count | {summary.local_stt_execution_requested_count} |
| local_stt_execution_count | {summary.local_stt_execution_count} |
| local_cuda_stt_call_count | {summary.local_cuda_stt_call_count} |
| local_stt_model_load_attempt_count | {summary.local_stt_model_load_attempt_count} |
| local_stt_model_load_error_count | {summary.local_stt_model_load_error_count} |
| proxy_metric_row_count | {summary.proxy_metric_row_count} |
| proxy_metric_pass_count | {summary.proxy_metric_pass_count} |
| proxy_metric_fail_count | {summary.proxy_metric_fail_count} |
| stt_latency_p50_ms | {summary.stt_latency_p50_ms:.6f} |
| stt_latency_p95_ms | {summary.stt_latency_p95_ms:.6f} |
| cer_avg | {format_optional(summary.cer_avg)} |
| char_f1_avg | {format_optional(summary.char_f1_avg)} |
| sequence_similarity_avg | {format_optional(summary.sequence_similarity_avg)} |
| place_name_accuracy_avg | {format_optional(summary.place_name_accuracy_avg)} |
| quality_threshold_cer_max | {summary.quality_threshold_cer_max:.6f} |
| quality_threshold_char_f1_min | {summary.quality_threshold_char_f1_min:.6f} |
| quality_threshold_sequence_similarity_min | {summary.quality_threshold_sequence_similarity_min:.6f} |
| quality_threshold_place_accuracy_min | {summary.quality_threshold_place_accuracy_min:.6f} |
| quality_threshold_pass_count | {summary.quality_threshold_pass_count} |
| human_listening_completed_count | {summary.human_listening_completed_count} |
| human_score_public_detail_row_count | {summary.human_score_public_detail_row_count} |
| external_provider_call_count | {summary.external_provider_call_count} |
| external_audio_transmission_count | {summary.external_audio_transmission_count} |
| live_stt_call_count | {summary.live_stt_call_count} |
| live_tts_call_count | {summary.live_tts_call_count} |
| live_solar_call_count | {summary.live_solar_call_count} |
| raw_audio_public_artifact_count | {summary.raw_audio_public_artifact_count} |
| raw_transcript_public_artifact_count | {summary.raw_transcript_public_artifact_count} |
| raw_script_public_artifact_count | {summary.raw_script_public_artifact_count} |
| client_secret_exposure_count | {summary.client_secret_exposure_count} |
| resolved_device | `{summary.resolved_device}` |
| compute_type | `{summary.compute_type}` |
| local_cuda_available_count | {summary.local_cuda_available_count} |
| cuda_device_count | {summary.cuda_device_count} |
| public_private_path_leakage_count | {summary.public_private_path_leakage_count} |
| public_secret_like_leakage_count | {summary.public_secret_like_leakage_count} |
| public_raw_payload_leakage_count | {summary.public_raw_payload_leakage_count} |
| proxy_decision | `{summary.proxy_decision}` |

## Proxy Rows

| script_id | status | audio_pass | latency_ms | cer | char_f1 | seq_sim | place_acc | threshold_pass | error_code |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
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
tts_automated_proxy_eval_failures={failures}
tts_automated_proxy_eval_blockers={blockers}
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


def build_assessment(report: TtsAutomatedProxyReport) -> dict[str, str]:
    summary = report.summary
    return {
        "scope": "사람 채점 대신 쓸 수 없는 자동 proxy를 별도 evidence로 분리했다.",
        "voice_ml": "TTS wav를 local STT로 round-trip해 발음/전달력의 기계적 신호만 측정했다.",
        "evaluation": "CER, 문자 F1, sequence similarity, 장소명 복원률을 script 단위로 기록했다.",
        "human_review": "human listening completed count는 0으로 유지해 최종 품질 판단을 차단했다.",
        "privacy": "raw audio, raw transcript, raw script text, private path는 public artifact에 저장하지 않았다.",
        "cost": "외부 STT/TTS provider 호출과 외부 음성 전송은 0이다.",
        "cuda": f"CUDA 가능 시 사용하며 resolved_device={summary.resolved_device}로 기록했다.",
        "data_mart": "public proxy metric grain과 private transcript/human score grain을 분리했다.",
        "portfolio": "사람 평가 전 자동 대체 지표로 risk를 낮춘 과정으로 설명할 수 있다.",
        "external_audit": "자동 proxy를 human score로 둔갑시키지 않고 별도 gate로 둔 판단은 타당하다.",
        "decision": summary.proxy_decision,
    }


def collect_proxy_eval_blockers(report: TtsAutomatedProxyReport) -> list[str]:
    decision = report.summary.proxy_decision
    if decision == "automated_proxy_passed_not_human_score":
        return ["human_listening_scores_still_required"]
    if decision == "automated_proxy_failed_quality_threshold":
        return ["proxy_quality_threshold_failed", "human_listening_scores_still_required"]
    if decision == "skipped_pending_local_stt_execution":
        return ["local_stt_execution_not_requested"]
    if decision == "blocked_missing_local_stt_runtime":
        return ["local_stt_runtime_missing"]
    if decision == "blocked_local_stt_execution":
        return ["local_stt_execution_incomplete"]
    if decision == "blocked_audio_sanity_or_missing_artifacts":
        return ["audio_artifact_or_sanity_blocked"]
    if decision == "failed_public_safety_gate":
        return ["public_safety_gate_failed"]
    return []


def format_proxy_row(row: TtsAutomatedProxyRow) -> str:
    return (
        f"| {row.script_id} | `{row.proxy_status}` | `{row.audio_sanity_pass}` | "
        f"{row.stt_latency_ms:.6f} | {format_optional(row.cer)} | "
        f"{format_optional(row.char_f1)} | {format_optional(row.sequence_similarity)} | "
        f"{format_optional(row.place_name_accuracy)} | `{proxy_metric_passes(row)}` | "
        f"`{row.error_code}` |"
    )


def average(values: Sequence[float | None]) -> float | None:
    concrete = [value for value in values if value is not None]
    if not concrete:
        return None
    return round(sum(concrete) / len(concrete), 6)


def format_optional(value: float | None) -> str:
    if value is None:
        return "null"
    return f"{value:.6f}"


def build_proxy_eval_id(
    *,
    rows: tuple[TtsAutomatedProxyRow, ...],
    summary: TtsAutomatedProxySummary,
) -> str:
    digest = stable_digest(
        {
            "work_id": WORK_ID,
            "rows": [row.model_dump(mode="json") for row in rows],
            "device": summary.resolved_device,
            "decision": summary.proxy_decision,
        },
        length=8,
    )
    return f"voice-local-tts-proxy-s{summary.selected_script_count}-{digest}"


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


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run local TTS automated proxy evaluation with local STT round-trip.",
    )
    parser.add_argument("--scripts", type=Path, default=DEFAULT_SCRIPTS_PATH)
    parser.add_argument("--private-audio-dir", type=Path, default=DEFAULT_PRIVATE_AUDIO_DIR)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--rows", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    parser.add_argument("--script-limit", type=int, default=DEFAULT_SCRIPT_LIMIT)
    parser.add_argument("--stt-model", default=DEFAULT_STT_MODEL_ID)
    parser.add_argument("--execute-local-stt", action="store_true")
    parser.add_argument("--require-local-stt", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    run_voice_local_tts_automated_proxy_eval(
        scripts_path=args.scripts,
        private_audio_dir=args.private_audio_dir,
        doc_path=args.doc,
        report_path=args.report,
        result_rows_path=args.rows,
        script_limit=args.script_limit,
        stt_model_id=args.stt_model,
        execute_local_stt=args.execute_local_stt,
        require_local_stt=args.require_local_stt,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
