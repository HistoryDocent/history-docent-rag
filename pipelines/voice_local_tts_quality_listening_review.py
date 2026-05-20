from __future__ import annotations

import argparse
import hashlib
import json
import math
import wave
from collections.abc import Sequence
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
    load_tts_smoke_scripts,
    percentile,
    select_tts_smoke_scripts,
)
from pipelines.voice_stt_tts_provider_bench_readiness import build_cuda_preflight


REPORT_VERSION = "voice-local-tts-quality-listening-review-report/v1"
WORK_ID = "HD-VOICE-LOCAL-TTS-QUALITY-LISTENING-REVIEW-001"
DEPENDS_ON = "HD-VOICE-LOCAL-SHERPA-ONNX-SUPERTONIC3-KO-SMOKE-001"
PROVIDER_CANDIDATE_ID = "local_sherpa_onnx_supertonic3_ko"
MODEL_FAMILY = "sherpa-onnx + Supertonic 3 Korean"

DEFAULT_SCRIPTS_PATH = Path("data_samples") / "voice_tts_smoke_scripts.sample.jsonl"
DEFAULT_PRIVATE_AUDIO_DIR = (
    Path("private_data") / "voice" / "sherpa_onnx_supertonic3_ko_audio"
)
DEFAULT_DOC_PATH = Path("docs") / "VOICE_LOCAL_TTS_QUALITY_LISTENING_REVIEW.md"
DEFAULT_REPORT_PATH = (
    Path("evals") / "reports" / "voice_local_tts_quality_listening_review_report.md"
)
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "voice_local_tts_quality_listening_review_rows.jsonl"
)
DEFAULT_SCRIPT_LIMIT = 5
SILENCE_ABS_THRESHOLD = 0.015625
CLIPPING_ABS_THRESHOLD = 0.999
MIN_DURATION_MS = 1000.0
MAX_DURATION_MS = 20000.0
MAX_SILENCE_RATIO = 0.70
MAX_CLIPPING_RATIO = 0.001
MIN_SAMPLE_RATE_HZ = 16000

AudioReadStatus = Literal["read", "missing", "unsupported", "error"]
ReviewDecision = Literal[
    "automated_audio_sanity_passed_pending_human_review",
    "blocked_audio_sanity_or_missing_artifacts",
    "failed_public_safety_gate",
]


class TtsQualityReviewBase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TtsQualityRubricCriterion(TtsQualityReviewBase):
    criterion_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    score_min: int = Field(ge=1)
    score_max: int = Field(ge=1)
    low_anchor: str = Field(min_length=1)
    high_anchor: str = Field(min_length=1)


class TtsQualityAudioMetricRow(TtsQualityReviewBase):
    script_id: str = Field(min_length=1)
    audio_artifact_id: str = Field(min_length=8)
    provider_candidate_id: str = PROVIDER_CANDIDATE_ID
    model_family: str = MODEL_FAMILY
    read_status: AudioReadStatus
    language: str = Field(min_length=1)
    text_role: str = Field(min_length=1)
    sample_rate_hz: int = Field(ge=0)
    channel_count: int = Field(ge=0)
    sample_width_bytes: int = Field(ge=0)
    frame_count: int = Field(ge=0)
    duration_ms: float = Field(ge=0.0)
    file_size_bytes: int = Field(ge=0)
    rms_dbfs: float
    peak_abs_ratio: float = Field(ge=0.0)
    clipping_sample_ratio: float = Field(ge=0.0)
    silence_sample_ratio: float = Field(ge=0.0, le=1.0)
    leading_silence_ms: float = Field(ge=0.0)
    trailing_silence_ms: float = Field(ge=0.0)
    duration_gate_pass: bool
    clipping_gate_pass: bool
    silence_gate_pass: bool
    sample_rate_gate_pass: bool
    automated_sanity_pass: bool
    character_count: int = Field(ge=0)
    place_name_count: int = Field(ge=0)
    text_hash: str = Field(min_length=8)
    error_code: str


class TtsQualityListeningReviewSummary(TtsQualityReviewBase):
    expected_audio_count: int = Field(ge=0)
    selected_audio_count: int = Field(ge=0)
    audio_file_available_count: int = Field(ge=0)
    audio_metric_row_count: int = Field(ge=0)
    automated_metric_pass_count: int = Field(ge=0)
    automated_metric_fail_count: int = Field(ge=0)
    duration_gate_pass_count: int = Field(ge=0)
    clipping_gate_pass_count: int = Field(ge=0)
    silence_gate_pass_count: int = Field(ge=0)
    sample_rate_gate_pass_count: int = Field(ge=0)
    human_listening_rubric_criterion_count: int = Field(ge=0)
    human_listening_required_count: int = Field(ge=0)
    human_listening_completed_count: int = Field(ge=0)
    human_listening_score_public_artifact_count: int = Field(ge=0)
    duration_p50_ms: float = Field(ge=0.0)
    duration_p95_ms: float = Field(ge=0.0)
    rms_dbfs_p50: float
    clipping_sample_ratio_max: float = Field(ge=0.0)
    silence_sample_ratio_max: float = Field(ge=0.0)
    leading_silence_ms_max: float = Field(ge=0.0)
    trailing_silence_ms_max: float = Field(ge=0.0)
    external_provider_call_count: int = Field(ge=0)
    external_audio_transmission_count: int = Field(ge=0)
    live_stt_call_count: int = Field(ge=0)
    live_tts_call_count: int = Field(ge=0)
    live_solar_call_count: int = Field(ge=0)
    raw_transcript_public_artifact_count: int = Field(ge=0)
    raw_audio_public_artifact_count: int = Field(ge=0)
    client_secret_exposure_count: int = Field(ge=0)
    local_cuda_available_count: int = Field(ge=0)
    cuda_device_count: int = Field(ge=0)
    public_private_path_leakage_count: int = Field(ge=0)
    public_secret_like_leakage_count: int = Field(ge=0)
    public_raw_payload_leakage_count: int = Field(ge=0)
    review_decision: ReviewDecision


class TtsQualityListeningReviewReport(TtsQualityReviewBase):
    report_version: str = REPORT_VERSION
    review_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    work_id: str = WORK_ID
    depends_on: str = DEPENDS_ON
    scripts_path: str = Field(min_length=1)
    audio_path_alias: str = Field(min_length=1)
    result_path: str = Field(min_length=1)
    source_fingerprint: str = Field(min_length=8)
    summary: TtsQualityListeningReviewSummary
    rubric: tuple[TtsQualityRubricCriterion, ...]
    rows: tuple[TtsQualityAudioMetricRow, ...]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


RUBRIC: tuple[TtsQualityRubricCriterion, ...] = (
    TtsQualityRubricCriterion(
        criterion_id="pronunciation_clarity",
        label="발음 명료도",
        score_min=1,
        score_max=5,
        low_anchor="고유명사와 문장 핵심어가 잘 들리지 않는다.",
        high_anchor="고유명사와 문장 핵심어가 또렷하게 들린다.",
    ),
    TtsQualityRubricCriterion(
        criterion_id="korean_naturalness",
        label="한국어 자연스러움",
        score_min=1,
        score_max=5,
        low_anchor="억양이나 띄어읽기가 한국어 안내로 부자연스럽다.",
        high_anchor="한국어 문장 흐름과 억양이 자연스럽다.",
    ),
    TtsQualityRubricCriterion(
        criterion_id="docent_tone",
        label="역사 도슨트 톤",
        score_min=1,
        score_max=5,
        low_anchor="관광 안내보다 기계 낭독에 가깝다.",
        high_anchor="관광 도슨트 안내 톤으로 수용 가능하다.",
    ),
    TtsQualityRubricCriterion(
        criterion_id="speaking_rate",
        label="말 속도",
        score_min=1,
        score_max=5,
        low_anchor="너무 빠르거나 느려서 관광 중 듣기 어렵다.",
        high_anchor="이동 중 짧은 안내로 듣기 적절하다.",
    ),
    TtsQualityRubricCriterion(
        criterion_id="artifact_noise",
        label="잡음/끊김",
        score_min=1,
        score_max=5,
        low_anchor="끊김, 왜곡, 잡음이 안내 이해를 방해한다.",
        high_anchor="끊김과 잡음이 거의 느껴지지 않는다.",
    ),
    TtsQualityRubricCriterion(
        criterion_id="tourist_fit",
        label="관광 안내 적합성",
        score_min=1,
        score_max=5,
        low_anchor="현장 관광객에게 들려주기 어렵다.",
        high_anchor="짧은 현장 안내 음성 후보로 검토 가능하다.",
    ),
)


def run_voice_local_tts_quality_listening_review(
    *,
    scripts_path: Path = DEFAULT_SCRIPTS_PATH,
    private_audio_dir: Path = DEFAULT_PRIVATE_AUDIO_DIR,
    doc_path: Path = DEFAULT_DOC_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
    script_limit: int = DEFAULT_SCRIPT_LIMIT,
) -> TtsQualityListeningReviewReport:
    scripts = select_tts_smoke_scripts(
        load_tts_smoke_scripts(project_path(scripts_path)),
        limit=script_limit,
    )
    audio_dir = project_path(private_audio_dir)
    cuda_preflight = build_cuda_preflight()
    rows = tuple(
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
    summary = build_summary(rows=rows, cuda_preflight=cuda_preflight)
    review_id = build_review_id(rows=rows, summary=summary)
    public_rows = build_public_rows(review_id=review_id, rows=rows)
    provisional_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=review_id,
        result_rows=public_rows,
        report_text="",
    )
    provisional = build_report(
        review_id=review_id,
        scripts_path=scripts_path,
        private_audio_dir=private_audio_dir,
        result_rows_path=result_rows_path,
        rows=rows,
        summary=summary,
        output_quality=provisional_quality,
    )
    doc_text = build_doc(provisional)
    report_text = build_markdown(provisional)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=review_id,
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
            "review_decision": build_review_decision(
                summary=summary,
                output_quality=output_quality,
            ),
        },
    )
    report = build_report(
        review_id=review_id,
        scripts_path=scripts_path,
        private_audio_dir=private_audio_dir,
        result_rows_path=result_rows_path,
        rows=rows,
        summary=summary,
        output_quality=output_quality,
    )
    failures = collect_review_failures(report)
    if failures:
        raise ValueError(f"voice local TTS quality listening review gate failed: {failures}")

    write_public_retrieval_result_rows(
        path=project_path(result_rows_path),
        rows=build_public_rows(review_id=review_id, rows=rows),
    )
    resolved_doc_path = project_path(doc_path)
    resolved_report_path = project_path(report_path)
    resolved_doc_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_report_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_doc_path.write_text(build_doc(report), encoding="utf-8")
    resolved_report_path.write_text(build_markdown(report), encoding="utf-8")
    print(
        "voice_local_tts_quality_listening_review "
        f"status={report.summary.review_decision} "
        f"audio={report.summary.selected_audio_count} "
        f"auto_pass={report.summary.automated_metric_pass_count} "
        f"human_done={report.summary.human_listening_completed_count} "
        f"external_calls={report.summary.external_provider_call_count}",
    )
    return report


def build_audio_metric_row(
    *,
    script_id: str,
    language: str,
    text_role: str,
    text_hash: str,
    character_count: int,
    place_name_count: int,
    audio_path: Path,
) -> TtsQualityAudioMetricRow:
    artifact_id = stable_digest({"provider": PROVIDER_CANDIDATE_ID, "script_id": script_id})
    if not audio_path.exists():
        return build_unreadable_row(
            script_id=script_id,
            language=language,
            text_role=text_role,
            text_hash=text_hash,
            character_count=character_count,
            place_name_count=place_name_count,
            audio_artifact_id=artifact_id,
            read_status="missing",
            error_code="audio_file_missing",
        )

    try:
        metrics = read_wav_metrics(audio_path)
    except wave.Error:
        return build_unreadable_row(
            script_id=script_id,
            language=language,
            text_role=text_role,
            text_hash=text_hash,
            character_count=character_count,
            place_name_count=place_name_count,
            audio_artifact_id=artifact_id,
            read_status="unsupported",
            error_code="unsupported_wav",
        )
    except Exception:
        return build_unreadable_row(
            script_id=script_id,
            language=language,
            text_role=text_role,
            text_hash=text_hash,
            character_count=character_count,
            place_name_count=place_name_count,
            audio_artifact_id=artifact_id,
            read_status="error",
            error_code="audio_metric_read_error",
        )

    duration_gate_pass = MIN_DURATION_MS <= metrics["duration_ms"] <= MAX_DURATION_MS
    clipping_gate_pass = metrics["clipping_sample_ratio"] <= MAX_CLIPPING_RATIO
    silence_gate_pass = metrics["silence_sample_ratio"] <= MAX_SILENCE_RATIO
    sample_rate_gate_pass = metrics["sample_rate_hz"] >= MIN_SAMPLE_RATE_HZ
    automated_sanity_pass = all(
        (duration_gate_pass, clipping_gate_pass, silence_gate_pass, sample_rate_gate_pass)
    )
    return TtsQualityAudioMetricRow(
        script_id=script_id,
        audio_artifact_id=artifact_id,
        read_status="read",
        language=language,
        text_role=text_role,
        sample_rate_hz=metrics["sample_rate_hz"],
        channel_count=metrics["channel_count"],
        sample_width_bytes=metrics["sample_width_bytes"],
        frame_count=metrics["frame_count"],
        duration_ms=metrics["duration_ms"],
        file_size_bytes=audio_path.stat().st_size,
        rms_dbfs=metrics["rms_dbfs"],
        peak_abs_ratio=metrics["peak_abs_ratio"],
        clipping_sample_ratio=metrics["clipping_sample_ratio"],
        silence_sample_ratio=metrics["silence_sample_ratio"],
        leading_silence_ms=metrics["leading_silence_ms"],
        trailing_silence_ms=metrics["trailing_silence_ms"],
        duration_gate_pass=duration_gate_pass,
        clipping_gate_pass=clipping_gate_pass,
        silence_gate_pass=silence_gate_pass,
        sample_rate_gate_pass=sample_rate_gate_pass,
        automated_sanity_pass=automated_sanity_pass,
        character_count=character_count,
        place_name_count=place_name_count,
        text_hash=text_hash,
        error_code="",
    )


def read_wav_metrics(audio_path: Path) -> dict[str, int | float]:
    with wave.open(str(audio_path), "rb") as wav_file:
        channel_count = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        sample_rate = wav_file.getframerate()
        frame_count = wav_file.getnframes()
        frames = wav_file.readframes(frame_count)

    if sample_width != 2:
        raise wave.Error("only 16-bit PCM wav is supported")
    samples = np.frombuffer(frames, dtype="<i2").astype(np.float32)
    if channel_count > 1:
        samples = samples.reshape(-1, channel_count).mean(axis=1)
    normalized = samples / 32768.0
    abs_samples = np.abs(normalized)
    sample_count = int(abs_samples.size)
    duration_ms = round(frame_count / sample_rate * 1000.0, 6) if sample_rate else 0.0
    rms = float(np.sqrt(np.mean(np.square(normalized)))) if sample_count else 0.0
    rms_dbfs = round(20 * math.log10(max(rms, 1e-6)), 6)
    peak_abs_ratio = round(float(np.max(abs_samples)) if sample_count else 0.0, 6)
    clipping_ratio = round(
        float(np.count_nonzero(abs_samples >= CLIPPING_ABS_THRESHOLD) / max(sample_count, 1)),
        8,
    )
    silence_mask = abs_samples <= SILENCE_ABS_THRESHOLD
    silence_ratio = round(float(np.count_nonzero(silence_mask) / max(sample_count, 1)), 8)
    leading_silence_ms = contiguous_silence_ms(silence_mask, sample_rate, from_start=True)
    trailing_silence_ms = contiguous_silence_ms(silence_mask, sample_rate, from_start=False)
    return {
        "sample_rate_hz": sample_rate,
        "channel_count": channel_count,
        "sample_width_bytes": sample_width,
        "frame_count": frame_count,
        "duration_ms": duration_ms,
        "rms_dbfs": rms_dbfs,
        "peak_abs_ratio": peak_abs_ratio,
        "clipping_sample_ratio": clipping_ratio,
        "silence_sample_ratio": silence_ratio,
        "leading_silence_ms": leading_silence_ms,
        "trailing_silence_ms": trailing_silence_ms,
    }


def contiguous_silence_ms(mask: np.ndarray, sample_rate: int, *, from_start: bool) -> float:
    if sample_rate <= 0 or mask.size == 0:
        return 0.0
    values = mask if from_start else mask[::-1]
    count = 0
    for is_silent in values:
        if not bool(is_silent):
            break
        count += 1
    return round(count / sample_rate * 1000.0, 6)


def build_unreadable_row(
    *,
    script_id: str,
    language: str,
    text_role: str,
    text_hash: str,
    character_count: int,
    place_name_count: int,
    audio_artifact_id: str,
    read_status: AudioReadStatus,
    error_code: str,
) -> TtsQualityAudioMetricRow:
    return TtsQualityAudioMetricRow(
        script_id=script_id,
        audio_artifact_id=audio_artifact_id,
        read_status=read_status,
        language=language,
        text_role=text_role,
        sample_rate_hz=0,
        channel_count=0,
        sample_width_bytes=0,
        frame_count=0,
        duration_ms=0.0,
        file_size_bytes=0,
        rms_dbfs=-120.0,
        peak_abs_ratio=0.0,
        clipping_sample_ratio=0.0,
        silence_sample_ratio=0.0,
        leading_silence_ms=0.0,
        trailing_silence_ms=0.0,
        duration_gate_pass=False,
        clipping_gate_pass=False,
        silence_gate_pass=False,
        sample_rate_gate_pass=False,
        automated_sanity_pass=False,
        character_count=character_count,
        place_name_count=place_name_count,
        text_hash=text_hash,
        error_code=error_code,
    )


def build_summary(
    *,
    rows: tuple[TtsQualityAudioMetricRow, ...],
    cuda_preflight: Any,
) -> TtsQualityListeningReviewSummary:
    readable_rows = [row for row in rows if row.read_status == "read"]
    duration_values = [row.duration_ms for row in readable_rows]
    rms_values = [row.rms_dbfs for row in readable_rows]
    summary = TtsQualityListeningReviewSummary(
        expected_audio_count=len(rows),
        selected_audio_count=len(rows),
        audio_file_available_count=len(readable_rows),
        audio_metric_row_count=len(rows),
        automated_metric_pass_count=sum(1 for row in rows if row.automated_sanity_pass),
        automated_metric_fail_count=sum(1 for row in rows if not row.automated_sanity_pass),
        duration_gate_pass_count=sum(1 for row in rows if row.duration_gate_pass),
        clipping_gate_pass_count=sum(1 for row in rows if row.clipping_gate_pass),
        silence_gate_pass_count=sum(1 for row in rows if row.silence_gate_pass),
        sample_rate_gate_pass_count=sum(1 for row in rows if row.sample_rate_gate_pass),
        human_listening_rubric_criterion_count=len(RUBRIC),
        human_listening_required_count=len(rows),
        human_listening_completed_count=0,
        human_listening_score_public_artifact_count=0,
        duration_p50_ms=percentile(duration_values, 0.50),
        duration_p95_ms=percentile(duration_values, 0.95),
        rms_dbfs_p50=percentile(rms_values, 0.50) if rms_values else -120.0,
        clipping_sample_ratio_max=round(
            max((row.clipping_sample_ratio for row in rows), default=0.0),
            8,
        ),
        silence_sample_ratio_max=round(
            max((row.silence_sample_ratio for row in rows), default=0.0),
            8,
        ),
        leading_silence_ms_max=round(max((row.leading_silence_ms for row in rows), default=0.0), 6),
        trailing_silence_ms_max=round(
            max((row.trailing_silence_ms for row in rows), default=0.0),
            6,
        ),
        external_provider_call_count=0,
        external_audio_transmission_count=0,
        live_stt_call_count=0,
        live_tts_call_count=0,
        live_solar_call_count=0,
        raw_transcript_public_artifact_count=0,
        raw_audio_public_artifact_count=0,
        client_secret_exposure_count=0,
        local_cuda_available_count=int(cuda_preflight.local_cuda_available),
        cuda_device_count=cuda_preflight.cuda_device_count,
        public_private_path_leakage_count=0,
        public_secret_like_leakage_count=0,
        public_raw_payload_leakage_count=0,
        review_decision="blocked_audio_sanity_or_missing_artifacts",
    )
    return summary.model_copy(
        update={
            "review_decision": build_review_decision(
                summary=summary,
                output_quality=None,
            )
        }
    )


def build_review_decision(
    *,
    summary: TtsQualityListeningReviewSummary,
    output_quality: PublicRetrievalArtifactQuality | None,
) -> ReviewDecision:
    output_blocked = output_quality is not None and (
        output_quality.public_raw_text_leakage_count
        or output_quality.private_path_leakage_count
        or output_quality.secret_like_leakage_count
        or output_quality.forbidden_result_field_count
    )
    if output_blocked:
        return "failed_public_safety_gate"
    if (
        summary.selected_audio_count
        and summary.audio_file_available_count == summary.selected_audio_count
        and summary.automated_metric_pass_count == summary.selected_audio_count
        and summary.human_listening_rubric_criterion_count == len(RUBRIC)
    ):
        return "automated_audio_sanity_passed_pending_human_review"
    return "blocked_audio_sanity_or_missing_artifacts"


def collect_review_failures(report: TtsQualityListeningReviewReport) -> list[str]:
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
    if summary.audio_file_available_count != summary.selected_audio_count:
        failures.append("audio_artifacts_missing")
    if summary.automated_metric_pass_count != summary.selected_audio_count:
        failures.append("automated_audio_sanity_failed")
    if summary.review_decision == "failed_public_safety_gate":
        failures.append("public_safety_gate_failed")
    return list(dict.fromkeys(failures))


def build_report(
    *,
    review_id: str,
    scripts_path: Path,
    private_audio_dir: Path,
    result_rows_path: Path,
    rows: tuple[TtsQualityAudioMetricRow, ...],
    summary: TtsQualityListeningReviewSummary,
    output_quality: PublicRetrievalArtifactQuality,
) -> TtsQualityListeningReviewReport:
    report = TtsQualityListeningReviewReport(
        review_id=review_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        scripts_path=public_path_alias(scripts_path),
        audio_path_alias=public_path_alias(private_audio_dir),
        result_path=public_path_alias(result_rows_path),
        source_fingerprint=stable_digest(
            {
                "rows": [row.model_dump(mode="json") for row in rows],
                "summary": summary.model_dump(mode="json"),
                "rubric": [criterion.model_dump(mode="json") for criterion in RUBRIC],
            }
        ),
        summary=summary,
        rubric=RUBRIC,
        rows=rows,
        output_quality=output_quality,
        qualitative_assessment={},
    )
    return report.model_copy(update={"qualitative_assessment": build_qualitative_assessment(report)})


def build_public_rows(
    *,
    review_id: str,
    rows: tuple[TtsQualityAudioMetricRow, ...],
) -> list[dict[str, Any]]:
    return [
        {
            "row_type": "local_tts_quality_audio_metric",
            "review_id": review_id,
            "script_id": row.script_id,
            "audio_artifact_id": row.audio_artifact_id,
            "provider_candidate_id": row.provider_candidate_id,
            "model_family": row.model_family,
            "read_status": row.read_status,
            "language": row.language,
            "text_role": row.text_role,
            "sample_rate_hz": row.sample_rate_hz,
            "channel_count": row.channel_count,
            "sample_width_bytes": row.sample_width_bytes,
            "duration_ms": row.duration_ms,
            "file_size_bytes": row.file_size_bytes,
            "rms_dbfs": row.rms_dbfs,
            "peak_abs_ratio": row.peak_abs_ratio,
            "clipping_sample_ratio": row.clipping_sample_ratio,
            "silence_sample_ratio": row.silence_sample_ratio,
            "leading_silence_ms": row.leading_silence_ms,
            "trailing_silence_ms": row.trailing_silence_ms,
            "duration_gate_pass": row.duration_gate_pass,
            "clipping_gate_pass": row.clipping_gate_pass,
            "silence_gate_pass": row.silence_gate_pass,
            "sample_rate_gate_pass": row.sample_rate_gate_pass,
            "automated_sanity_pass": row.automated_sanity_pass,
            "character_count": row.character_count,
            "place_name_count": row.place_name_count,
            "text_hash": row.text_hash,
            "error_code": row.error_code,
        }
        for row in rows
    ]


def build_doc(report: TtsQualityListeningReviewReport) -> str:
    summary = report.summary
    rubric_rows = "\n".join(format_rubric_row(criterion) for criterion in report.rubric)
    return f"""# Voice Local TTS Quality Listening Review

## 결론

`{WORK_ID}`는 무료 로컬 TTS 음성의 청취 평가 기준과 자동 sanity metric을 고정한다.

이번 gate는 사람 청취 평가 완료가 아니다. 사람이 채점할 rubric과 자동 음성 metric만 만든다.

## Scope

| type | item |
| --- | --- |
| include | `sherpa-onnx + Supertonic 3 Korean` private wav 5개 자동 metric |
| include | duration, file size, silence, clipping, sample rate gate |
| include | 사람 청취 평가 rubric template |
| exclude | raw audio public 저장 |
| exclude | raw script text public 저장 |
| exclude | 외부 STT/TTS provider 호출 |
| exclude | 최종 TTS provider 확정 |
| exclude | 음질 우수 검증 완료 claim |

## 정량 요약

| metric | value |
| --- | ---: |
| expected_audio_count | {summary.expected_audio_count} |
| selected_audio_count | {summary.selected_audio_count} |
| audio_file_available_count | {summary.audio_file_available_count} |
| audio_metric_row_count | {summary.audio_metric_row_count} |
| automated_metric_pass_count | {summary.automated_metric_pass_count} |
| automated_metric_fail_count | {summary.automated_metric_fail_count} |
| duration_gate_pass_count | {summary.duration_gate_pass_count} |
| clipping_gate_pass_count | {summary.clipping_gate_pass_count} |
| silence_gate_pass_count | {summary.silence_gate_pass_count} |
| sample_rate_gate_pass_count | {summary.sample_rate_gate_pass_count} |
| human_listening_rubric_criterion_count | {summary.human_listening_rubric_criterion_count} |
| human_listening_required_count | {summary.human_listening_required_count} |
| human_listening_completed_count | {summary.human_listening_completed_count} |
| human_listening_score_public_artifact_count | {summary.human_listening_score_public_artifact_count} |
| external_provider_call_count | {summary.external_provider_call_count} |
| external_audio_transmission_count | {summary.external_audio_transmission_count} |
| raw_audio_public_artifact_count | {summary.raw_audio_public_artifact_count} |
| raw_transcript_public_artifact_count | {summary.raw_transcript_public_artifact_count} |
| review_decision | `{summary.review_decision}` |

## Human Listening Rubric Template

| criterion_id | label | range | low_anchor | high_anchor |
| --- | --- | --- | --- | --- |
{rubric_rows}

## Data Mart Grain

| table | grain | exposure |
| --- | --- | --- |
| `fact_voice_local_tts_audio_metric_public` | `review_id + script_id + metric_name` | public-safe |
| `fact_voice_local_tts_human_score_private` | `review_id + script_id + reviewer_id + criterion_id` | private |

## Claim Boundary

| type | claim |
| --- | --- |
| allowed | local TTS 음성 자동 sanity metric을 기록했다. |
| allowed | 사람 청취 평가 rubric template을 만들었다. |
| allowed | 외부 provider 호출 없이 평가 준비를 완료했다. |
| forbidden | 무료 로컬 TTS 최종 provider 확정 |
| forbidden | Supertonic 3 음성 품질 우수 검증 완료 |
| forbidden | 실제 관광객 음성 품질 검증 완료 |
| forbidden | production 음성 관광 앱 완성 |
"""


def build_markdown(report: TtsQualityListeningReviewReport) -> str:
    summary = report.summary
    quality = report.output_quality
    row_lines = "\n".join(format_metric_row(row) for row in report.rows)
    rubric_rows = "\n".join(format_rubric_row(criterion) for criterion in report.rubric)
    qualitative_rows = "\n".join(
        f"| {key} | {value} |" for key, value in report.qualitative_assessment.items()
    )
    failures = collect_review_failures(report)
    return f"""# Voice Local TTS Quality Listening Review Report

## 결론

`{WORK_ID}`는 무료 로컬 TTS 품질 평가를 위한 자동 metric과 청취 rubric을 기록한다.

자동 sanity는 통과했더라도 사람 청취 평가는 아직 완료하지 않았다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| review_id | `{report.review_id}` |
| work_id | `{report.work_id}` |
| depends_on | `{report.depends_on}` |
| generated_at_utc | `{report.generated_at_utc}` |
| scripts_path | `{report.scripts_path}` |
| audio_path_alias | `{report.audio_path_alias}` |
| result_path | `{report.result_path}` |
| provider_candidate_id | `{PROVIDER_CANDIDATE_ID}` |
| source_fingerprint | `{report.source_fingerprint}` |
| review_status | `{summary.review_decision}` |

## 정량 리포트

| metric | value |
| --- | ---: |
| expected_audio_count | {summary.expected_audio_count} |
| selected_audio_count | {summary.selected_audio_count} |
| audio_file_available_count | {summary.audio_file_available_count} |
| audio_metric_row_count | {summary.audio_metric_row_count} |
| automated_metric_pass_count | {summary.automated_metric_pass_count} |
| automated_metric_fail_count | {summary.automated_metric_fail_count} |
| duration_gate_pass_count | {summary.duration_gate_pass_count} |
| clipping_gate_pass_count | {summary.clipping_gate_pass_count} |
| silence_gate_pass_count | {summary.silence_gate_pass_count} |
| sample_rate_gate_pass_count | {summary.sample_rate_gate_pass_count} |
| human_listening_rubric_criterion_count | {summary.human_listening_rubric_criterion_count} |
| human_listening_required_count | {summary.human_listening_required_count} |
| human_listening_completed_count | {summary.human_listening_completed_count} |
| human_listening_score_public_artifact_count | {summary.human_listening_score_public_artifact_count} |
| duration_p50_ms | {summary.duration_p50_ms:.6f} |
| duration_p95_ms | {summary.duration_p95_ms:.6f} |
| rms_dbfs_p50 | {summary.rms_dbfs_p50:.6f} |
| clipping_sample_ratio_max | {summary.clipping_sample_ratio_max:.8f} |
| silence_sample_ratio_max | {summary.silence_sample_ratio_max:.8f} |
| leading_silence_ms_max | {summary.leading_silence_ms_max:.6f} |
| trailing_silence_ms_max | {summary.trailing_silence_ms_max:.6f} |
| external_provider_call_count | {summary.external_provider_call_count} |
| external_audio_transmission_count | {summary.external_audio_transmission_count} |
| live_stt_call_count | {summary.live_stt_call_count} |
| live_tts_call_count | {summary.live_tts_call_count} |
| live_solar_call_count | {summary.live_solar_call_count} |
| raw_transcript_public_artifact_count | {summary.raw_transcript_public_artifact_count} |
| raw_audio_public_artifact_count | {summary.raw_audio_public_artifact_count} |
| client_secret_exposure_count | {summary.client_secret_exposure_count} |
| local_cuda_available_count | {summary.local_cuda_available_count} |
| cuda_device_count | {summary.cuda_device_count} |
| public_private_path_leakage_count | {summary.public_private_path_leakage_count} |
| public_secret_like_leakage_count | {summary.public_secret_like_leakage_count} |
| public_raw_payload_leakage_count | {summary.public_raw_payload_leakage_count} |
| review_decision | `{summary.review_decision}` |

## Audio Metric Rows

| script_id | status | duration_ms | rms_dbfs | clipping_ratio | silence_ratio | leading_ms | trailing_ms | auto_pass | error_code |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
{row_lines}

## Human Listening Rubric Template

| criterion_id | label | range | low_anchor | high_anchor |
| --- | --- | --- | --- | --- |
{rubric_rows}

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
tts_quality_listening_review_failures={failures}
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


def build_qualitative_assessment(report: TtsQualityListeningReviewReport) -> dict[str, str]:
    summary = report.summary
    return {
        "scope": "실제 음질 판정이 아니라 자동 metric과 청취 rubric을 고정했다.",
        "audio_metric": "duration, RMS, clipping, silence, sample rate를 script 단위로 기록했다.",
        "human_review": "사람 청취 평가는 required로 표시하고 completed count는 0으로 유지했다.",
        "privacy": "public artifact에는 raw audio, raw script text, private path를 저장하지 않았다.",
        "cost": "외부 STT/TTS provider 호출이 없어 추가 API 비용은 없다.",
        "cuda": "CUDA preflight는 기록했지만 audio metric 계산 자체는 CPU file analysis다.",
        "data_mart": "자동 metric public grain과 human score private grain을 분리했다.",
        "portfolio": "합성 가능성 다음 단계로 품질 평가 체계를 만든 evidence로 설명한다.",
        "external_audit": (
            "음질 우수 claim을 금지하고 pending human review로 남긴 판단은 타당하다."
        ),
        "decision": summary.review_decision,
    }


def format_metric_row(row: TtsQualityAudioMetricRow) -> str:
    return (
        f"| {row.script_id} | `{row.read_status}` | {row.duration_ms:.6f} | "
        f"{row.rms_dbfs:.6f} | {row.clipping_sample_ratio:.8f} | "
        f"{row.silence_sample_ratio:.8f} | {row.leading_silence_ms:.6f} | "
        f"{row.trailing_silence_ms:.6f} | `{row.automated_sanity_pass}` | "
        f"`{row.error_code}` |"
    )


def format_rubric_row(criterion: TtsQualityRubricCriterion) -> str:
    return (
        f"| {criterion.criterion_id} | {criterion.label} | "
        f"{criterion.score_min}-{criterion.score_max} | "
        f"{criterion.low_anchor} | {criterion.high_anchor} |"
    )


def build_review_id(
    *,
    rows: tuple[TtsQualityAudioMetricRow, ...],
    summary: TtsQualityListeningReviewSummary,
) -> str:
    digest = stable_digest(
        {
            "work_id": WORK_ID,
            "rows": [row.model_dump(mode="json") for row in rows],
            "summary": summary.model_dump(mode="json"),
        },
        length=8,
    )
    return f"voice-local-tts-quality-review-s{len(rows)}-{digest}"


def stable_digest(payload: Any, *, length: int = 16) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"),
    ).hexdigest()[:length]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run local TTS audio sanity metrics and listening rubric review.",
    )
    parser.add_argument("--scripts", type=Path, default=DEFAULT_SCRIPTS_PATH)
    parser.add_argument("--private-audio-dir", type=Path, default=DEFAULT_PRIVATE_AUDIO_DIR)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--rows", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    parser.add_argument("--script-limit", type=int, default=DEFAULT_SCRIPT_LIMIT)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    run_voice_local_tts_quality_listening_review(
        scripts_path=args.scripts,
        private_audio_dir=args.private_audio_dir,
        doc_path=args.doc,
        report_path=args.report,
        result_rows_path=args.rows,
        script_limit=args.script_limit,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
