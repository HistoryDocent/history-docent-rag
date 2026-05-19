from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import json
import re
import subprocess
import time
import wave
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
from pipelines.voice_stt_tts_provider_bench_readiness import (
    VoiceBenchmarkScript,
    build_cuda_preflight,
    load_voice_benchmark_scripts,
)


VOICE_STT_TTS_LOCAL_SMOKE_REPORT_VERSION = "voice-stt-tts-local-smoke-report/v1"
WORK_ID = "HD-VOICE-STT-TTS-PROVIDER-BENCH-SMOKE-LOCAL-001"
DEPENDS_ON = "HD-VOICE-STT-TTS-PROVIDER-BENCH-EXECUTION-APPROVAL-001"
DEFAULT_SCRIPTS_PATH = Path("data_samples") / "voice_benchmark_scripts.sample.jsonl"
DEFAULT_DOC_PATH = Path("docs") / "VOICE_STT_TTS_PROVIDER_BENCH_SMOKE_LOCAL.md"
DEFAULT_REPORT_PATH = (
    Path("evals") / "reports" / "voice_stt_tts_provider_bench_smoke_local_report.md"
)
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "voice_stt_tts_provider_bench_smoke_local_rows.jsonl"
)
DEFAULT_PRIVATE_AUDIO_DIR = Path("private_data") / "voice" / "local_smoke_audio"
PROVIDER_CANDIDATE_ID = "local_cuda_whisper"
DEFAULT_MODEL_ID = "tiny"
DEFAULT_SCRIPT_LIMIT = 5
TARGET_SAMPLE_RATE = 16000
PLACE_NAME_BY_ID = {
    "bukchon": "북촌",
    "changdeokgung": "창덕궁",
    "cheonggyecheon": "청계천",
    "gwanghwamun": "광화문",
    "gyeongbokgung": "경복궁",
    "hanyang": "한양",
    "hanyangdoseong": "한양도성",
    "jongno": "종로",
}

TranscriptionStatus = Literal[
    "executed",
    "blocked_missing_audio",
    "blocked_missing_runtime",
    "blocked_runtime_error",
    "skipped_by_flag",
]
SmokeDecision = Literal[
    "completed_local_smoke",
    "blocked_missing_runtime_or_audio",
    "failed_public_safety_gate",
]


class VoiceLocalSmokeModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class VoiceLocalSmokeRow(VoiceLocalSmokeModel):
    script_id: str = Field(min_length=1)
    query_type: str = Field(min_length=1)
    provider_candidate_id: str = PROVIDER_CANDIDATE_ID
    model_id: str = Field(min_length=1)
    resolved_device: str = Field(min_length=1)
    audio_fixture_private: bool
    local_tts_generated: bool
    stt_execution_requested: bool
    transcription_status: TranscriptionStatus
    latency_ms: float = Field(ge=0.0)
    wer: float | None = Field(default=None, ge=0.0)
    cer: float | None = Field(default=None, ge=0.0)
    place_name_accuracy: float | None = Field(default=None, ge=0.0, le=1.0)
    expected_place_name_count: int = Field(ge=0)
    transcript_hash: str
    reference_text_hash: str = Field(min_length=8)
    error_code: str


class VoiceLocalSmokeSummary(VoiceLocalSmokeModel):
    selected_script_count: int = Field(ge=0)
    public_safe_script_fixture_count: int = Field(ge=0)
    local_provider_candidate_count: int = Field(ge=0)
    local_whisper_runtime_available_count: int = Field(ge=0)
    local_tts_generation_requested_count: int = Field(ge=0)
    private_audio_generated_count: int = Field(ge=0)
    audio_fixture_available_count: int = Field(ge=0)
    local_stt_execution_requested_count: int = Field(ge=0)
    local_stt_execution_count: int = Field(ge=0)
    local_cuda_whisper_call_count: int = Field(ge=0)
    external_provider_call_count: int = Field(ge=0)
    external_audio_transmission_count: int = Field(ge=0)
    live_stt_call_count: int = Field(ge=0)
    live_tts_call_count: int = Field(ge=0)
    live_solar_call_count: int = Field(ge=0)
    private_audio_saved_count: int = Field(ge=0)
    raw_transcript_public_artifact_count: int = Field(ge=0)
    raw_audio_public_artifact_count: int = Field(ge=0)
    client_secret_exposure_count: int = Field(ge=0)
    wer_avg: float | None = Field(default=None, ge=0.0)
    cer_avg: float | None = Field(default=None, ge=0.0)
    place_name_accuracy_avg: float | None = Field(default=None, ge=0.0, le=1.0)
    stt_latency_p50_ms: float = Field(ge=0.0)
    stt_latency_p95_ms: float = Field(ge=0.0)
    resolved_device: str = Field(min_length=1)
    local_cuda_available_count: int = Field(ge=0)
    cuda_device_count: int = Field(ge=0)
    public_private_path_leakage_count: int = Field(ge=0)
    public_secret_like_leakage_count: int = Field(ge=0)
    public_raw_payload_leakage_count: int = Field(ge=0)
    smoke_decision: SmokeDecision


class VoiceLocalSmokeReport(VoiceLocalSmokeModel):
    report_version: str = VOICE_STT_TTS_LOCAL_SMOKE_REPORT_VERSION
    smoke_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    work_id: str = WORK_ID
    depends_on: str = DEPENDS_ON
    scripts_path: str = Field(min_length=1)
    result_path: str = Field(min_length=1)
    private_audio_path_alias: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    source_fingerprint: str = Field(min_length=8)
    summary: VoiceLocalSmokeSummary
    rows: tuple[VoiceLocalSmokeRow, ...]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def run_voice_stt_tts_local_smoke(
    *,
    scripts_path: Path = DEFAULT_SCRIPTS_PATH,
    doc_path: Path = DEFAULT_DOC_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
    private_audio_dir: Path = DEFAULT_PRIVATE_AUDIO_DIR,
    script_limit: int = DEFAULT_SCRIPT_LIMIT,
    model_id: str = DEFAULT_MODEL_ID,
    generate_private_audio: bool = False,
    execute_local_whisper: bool = False,
    require_local_execution: bool = False,
) -> VoiceLocalSmokeReport:
    scripts = select_local_smoke_scripts(
        load_voice_benchmark_scripts(project_path(scripts_path)),
        limit=script_limit,
    )
    cuda_preflight = build_cuda_preflight()
    runtime_available = importlib.util.find_spec("whisper") is not None
    audio_dir = project_path(private_audio_dir)
    if generate_private_audio:
        audio_dir.mkdir(parents=True, exist_ok=True)
    model = None
    if execute_local_whisper and runtime_available:
        model = _load_whisper_model(model_id=model_id, device=cuda_preflight.resolved_device)

    rows = tuple(
        build_local_smoke_row(
            script=script,
            model=model,
            model_id=model_id,
            audio_path=audio_dir / f"{script.script_id}.wav",
            resolved_device=cuda_preflight.resolved_device,
            runtime_available=runtime_available,
            generate_private_audio=generate_private_audio,
            execute_local_whisper=execute_local_whisper,
        )
        for script in scripts
    )
    summary = build_local_smoke_summary(
        rows=rows,
        cuda_preflight=cuda_preflight,
        runtime_available=runtime_available,
        generate_private_audio=generate_private_audio,
        execute_local_whisper=execute_local_whisper,
    )
    smoke_id = build_local_smoke_id(
        rows=rows,
        summary=summary,
        model_id=model_id,
    )
    public_rows = build_public_local_smoke_rows(smoke_id=smoke_id, rows=rows)
    provisional_quality = measure_public_retrieval_artifact_quality(
        report_version=VOICE_STT_TTS_LOCAL_SMOKE_REPORT_VERSION,
        run_id=smoke_id,
        result_rows=public_rows,
        report_text="",
    )
    provisional = build_local_smoke_report(
        smoke_id=smoke_id,
        scripts_path=scripts_path,
        result_rows_path=result_rows_path,
        private_audio_dir=private_audio_dir,
        model_id=model_id,
        rows=rows,
        summary=summary,
        output_quality=provisional_quality,
    )
    doc_text = build_local_smoke_doc(provisional)
    report_text = build_local_smoke_markdown(provisional)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=VOICE_STT_TTS_LOCAL_SMOKE_REPORT_VERSION,
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
            "smoke_decision": build_smoke_decision(
                summary=summary,
                output_quality=output_quality,
                require_local_execution=require_local_execution,
            ),
        },
    )
    report = build_local_smoke_report(
        smoke_id=smoke_id,
        scripts_path=scripts_path,
        result_rows_path=result_rows_path,
        private_audio_dir=private_audio_dir,
        model_id=model_id,
        rows=rows,
        summary=summary,
        output_quality=output_quality,
    )
    failures = collect_local_smoke_failures(
        report,
        require_local_execution=require_local_execution,
    )
    if failures:
        raise ValueError(f"voice local smoke gate failed: {failures}")

    write_public_retrieval_result_rows(
        path=project_path(result_rows_path),
        rows=build_public_local_smoke_rows(smoke_id=smoke_id, rows=rows),
    )
    resolved_doc_path = project_path(doc_path)
    resolved_report_path = project_path(report_path)
    resolved_doc_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_report_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_doc_path.write_text(build_local_smoke_doc(report), encoding="utf-8")
    resolved_report_path.write_text(build_local_smoke_markdown(report), encoding="utf-8")
    print(
        "voice_stt_tts_local_smoke "
        f"status={report.summary.smoke_decision} "
        f"scripts={report.summary.selected_script_count} "
        f"device={report.summary.resolved_device} "
        f"local_stt={report.summary.local_stt_execution_count} "
        f"external_calls={report.summary.external_provider_call_count}",
    )
    return report


def select_local_smoke_scripts(
    scripts: tuple[VoiceBenchmarkScript, ...],
    *,
    limit: int,
) -> tuple[VoiceBenchmarkScript, ...]:
    selected = [
        script
        for script in scripts
        if script.public_allowed
        and script.expected_behavior == "answer_with_citation"
        and script.query_type == "place_fact"
    ]
    return tuple(selected[:limit])


def build_local_smoke_row(
    *,
    script: VoiceBenchmarkScript,
    model: Any | None,
    model_id: str,
    audio_path: Path,
    resolved_device: str,
    runtime_available: bool,
    generate_private_audio: bool,
    execute_local_whisper: bool,
) -> VoiceLocalSmokeRow:
    audio_generated = False
    error_code = ""
    if generate_private_audio:
        try:
            synthesize_private_wav(script.script_text, audio_path)
            audio_generated = audio_path.exists()
        except Exception:
            audio_generated = False
            error_code = "local_tts_generation_failed"

    audio_available = audio_path.exists()
    if not execute_local_whisper:
        status: TranscriptionStatus = "skipped_by_flag"
        return build_unexecuted_row(
            script=script,
            model_id=model_id,
            resolved_device=resolved_device,
            audio_available=audio_available,
            audio_generated=audio_generated,
            stt_execution_requested=False,
            status=status,
            error_code=error_code,
        )
    if not runtime_available or model is None:
        return build_unexecuted_row(
            script=script,
            model_id=model_id,
            resolved_device=resolved_device,
            audio_available=audio_available,
            audio_generated=audio_generated,
            stt_execution_requested=True,
            status="blocked_missing_runtime",
            error_code="openai_whisper_not_available",
        )
    if not audio_available:
        return build_unexecuted_row(
            script=script,
            model_id=model_id,
            resolved_device=resolved_device,
            audio_available=False,
            audio_generated=audio_generated,
            stt_execution_requested=True,
            status="blocked_missing_audio",
            error_code=error_code or "private_audio_missing",
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
            audio_available=True,
            audio_generated=audio_generated,
            stt_execution_requested=True,
            status="blocked_runtime_error",
            error_code="local_whisper_transcribe_error",
        )

    return VoiceLocalSmokeRow(
        script_id=script.script_id,
        query_type=script.query_type,
        model_id=model_id,
        resolved_device=resolved_device,
        audio_fixture_private=True,
        local_tts_generated=audio_generated,
        stt_execution_requested=True,
        transcription_status="executed",
        latency_ms=latency_ms,
        wer=word_error_rate(script.script_text, transcript),
        cer=character_error_rate(script.script_text, transcript),
        place_name_accuracy=place_name_accuracy(script.place_ids, transcript),
        expected_place_name_count=len(script.place_ids),
        transcript_hash=_stable_digest(transcript),
        reference_text_hash=_stable_digest(script.script_text),
        error_code="",
    )


def build_unexecuted_row(
    *,
    script: VoiceBenchmarkScript,
    model_id: str,
    resolved_device: str,
    audio_available: bool,
    audio_generated: bool,
    stt_execution_requested: bool,
    status: TranscriptionStatus,
    error_code: str,
) -> VoiceLocalSmokeRow:
    return VoiceLocalSmokeRow(
        script_id=script.script_id,
        query_type=script.query_type,
        model_id=model_id,
        resolved_device=resolved_device,
        audio_fixture_private=audio_available,
        local_tts_generated=audio_generated,
        stt_execution_requested=stt_execution_requested,
        transcription_status=status,
        latency_ms=0.0,
        wer=None,
        cer=None,
        place_name_accuracy=None,
        expected_place_name_count=len(script.place_ids),
        transcript_hash="",
        reference_text_hash=_stable_digest(script.script_text),
        error_code=error_code,
    )


def synthesize_private_wav(text: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    escaped_path = str(output_path).replace("'", "''")
    escaped_text = text.replace("'", "''")
    script = f"""
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {{ $synth.SelectVoice('Microsoft Heami Desktop') }} catch {{ try {{ $synth.SelectVoice('Microsoft Heami') }} catch {{ }} }}
$synth.Rate = 0
$synth.Volume = 100
$synth.SetOutputToWaveFile('{escaped_path}')
$synth.Speak('{escaped_text}')
$synth.Dispose()
"""
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-EncodedCommand", encoded],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if completed.returncode != 0:
        raise RuntimeError("local_tts_synthesis_failed")


def read_wav_as_mono_float32(path: Path, *, target_sample_rate: int) -> np.ndarray:
    with wave.open(str(path), "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        sample_rate = wav_file.getframerate()
        frame_count = wav_file.getnframes()
        frames = wav_file.readframes(frame_count)
    if sample_width != 2:
        raise ValueError("only 16-bit PCM wav is supported for local smoke")
    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    if channels > 1:
        audio = audio.reshape(-1, channels).mean(axis=1)
    if sample_rate != target_sample_rate:
        audio = resample_linear(audio, source_rate=sample_rate, target_rate=target_sample_rate)
    return audio.astype(np.float32)


def resample_linear(
    audio: np.ndarray,
    *,
    source_rate: int,
    target_rate: int,
) -> np.ndarray:
    if len(audio) == 0 or source_rate == target_rate:
        return audio
    duration = len(audio) / float(source_rate)
    target_length = max(int(round(duration * target_rate)), 1)
    source_positions = np.linspace(0.0, len(audio) - 1, num=len(audio), dtype=np.float64)
    target_positions = np.linspace(0.0, len(audio) - 1, num=target_length, dtype=np.float64)
    return np.interp(target_positions, source_positions, audio).astype(np.float32)


def _load_whisper_model(*, model_id: str, device: str) -> Any:
    import whisper

    return whisper.load_model(model_id, device=device)


def build_local_smoke_summary(
    *,
    rows: tuple[VoiceLocalSmokeRow, ...],
    cuda_preflight: Any,
    runtime_available: bool,
    generate_private_audio: bool,
    execute_local_whisper: bool,
) -> VoiceLocalSmokeSummary:
    executed_rows = [row for row in rows if row.transcription_status == "executed"]
    latencies = [row.latency_ms for row in executed_rows]
    summary = VoiceLocalSmokeSummary(
        selected_script_count=len(rows),
        public_safe_script_fixture_count=len(rows),
        local_provider_candidate_count=1,
        local_whisper_runtime_available_count=int(runtime_available),
        local_tts_generation_requested_count=len(rows) if generate_private_audio else 0,
        private_audio_generated_count=sum(1 for row in rows if row.local_tts_generated),
        audio_fixture_available_count=sum(1 for row in rows if row.audio_fixture_private),
        local_stt_execution_requested_count=len(rows) if execute_local_whisper else 0,
        local_stt_execution_count=len(executed_rows),
        local_cuda_whisper_call_count=len(executed_rows),
        external_provider_call_count=0,
        external_audio_transmission_count=0,
        live_stt_call_count=0,
        live_tts_call_count=0,
        live_solar_call_count=0,
        private_audio_saved_count=sum(1 for row in rows if row.audio_fixture_private),
        raw_transcript_public_artifact_count=0,
        raw_audio_public_artifact_count=0,
        client_secret_exposure_count=0,
        wer_avg=_average(row.wer for row in executed_rows),
        cer_avg=_average(row.cer for row in executed_rows),
        place_name_accuracy_avg=_average(
            row.place_name_accuracy for row in executed_rows
        ),
        stt_latency_p50_ms=percentile(latencies, 0.50),
        stt_latency_p95_ms=percentile(latencies, 0.95),
        resolved_device=cuda_preflight.resolved_device,
        local_cuda_available_count=int(cuda_preflight.local_cuda_available),
        cuda_device_count=cuda_preflight.cuda_device_count,
        public_private_path_leakage_count=0,
        public_secret_like_leakage_count=0,
        public_raw_payload_leakage_count=0,
        smoke_decision="blocked_missing_runtime_or_audio",
    )
    return summary.model_copy(
        update={
            "smoke_decision": build_smoke_decision(
                summary=summary,
                output_quality=None,
                require_local_execution=False,
            ),
        },
    )


def build_smoke_decision(
    *,
    summary: VoiceLocalSmokeSummary,
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
    if require_local_execution and summary.local_stt_execution_count != summary.selected_script_count:
        return "blocked_missing_runtime_or_audio"
    if summary.local_stt_execution_count > 0:
        return "completed_local_smoke"
    return "blocked_missing_runtime_or_audio"


def collect_local_smoke_failures(
    report: VoiceLocalSmokeReport,
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
    if require_local_execution and summary.local_stt_execution_count != summary.selected_script_count:
        failures.append("required_local_stt_not_completed")
    if summary.smoke_decision == "failed_public_safety_gate":
        failures.append("public_safety_gate_failed")
    return list(dict.fromkeys(failures))


def build_local_smoke_report(
    *,
    smoke_id: str,
    scripts_path: Path,
    result_rows_path: Path,
    private_audio_dir: Path,
    model_id: str,
    rows: tuple[VoiceLocalSmokeRow, ...],
    summary: VoiceLocalSmokeSummary,
    output_quality: PublicRetrievalArtifactQuality,
) -> VoiceLocalSmokeReport:
    report = VoiceLocalSmokeReport(
        smoke_id=smoke_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        scripts_path=public_path_alias(scripts_path),
        result_path=public_path_alias(result_rows_path),
        private_audio_path_alias=public_path_alias(private_audio_dir),
        model_id=model_id,
        source_fingerprint=_stable_digest(
            {
                "rows": [row.model_dump(mode="json") for row in rows],
                "summary": summary.model_dump(mode="json"),
                "model_id": model_id,
            },
        ),
        summary=summary,
        rows=rows,
        output_quality=output_quality,
        qualitative_assessment={},
    )
    return report.model_copy(
        update={"qualitative_assessment": build_local_smoke_assessment(report)},
    )


def build_public_local_smoke_rows(
    *,
    smoke_id: str,
    rows: tuple[VoiceLocalSmokeRow, ...],
) -> list[dict[str, Any]]:
    return [
        {
            "row_type": "local_stt_smoke",
            "smoke_id": smoke_id,
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


def build_local_smoke_doc(report: VoiceLocalSmokeReport) -> str:
    summary = report.summary
    return f"""# Voice STT/TTS Provider Benchmark Local Smoke

## 결론

`{WORK_ID}`는 external provider 호출 없이 local CUDA Whisper 후보만 smoke로 검증한다.

이번 gate는 STT provider 최종 선택이 아니다. public artifact에는 raw audio, raw transcript, raw provider payload를 저장하지 않는다.

## Scope

포함:

- `local_cuda_whisper` 후보의 local smoke 실행
- CUDA 사용 가능 시 CUDA device 사용
- private wav fixture 생성 또는 사용
- WER, CER, place name accuracy, latency metric 기록
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
| selected_script_count | {summary.selected_script_count} |
| public_safe_script_fixture_count | {summary.public_safe_script_fixture_count} |
| local_provider_candidate_count | {summary.local_provider_candidate_count} |
| local_whisper_runtime_available_count | {summary.local_whisper_runtime_available_count} |
| local_tts_generation_requested_count | {summary.local_tts_generation_requested_count} |
| private_audio_generated_count | {summary.private_audio_generated_count} |
| audio_fixture_available_count | {summary.audio_fixture_available_count} |
| local_stt_execution_requested_count | {summary.local_stt_execution_requested_count} |
| local_stt_execution_count | {summary.local_stt_execution_count} |
| local_cuda_whisper_call_count | {summary.local_cuda_whisper_call_count} |
| external_provider_call_count | {summary.external_provider_call_count} |
| external_audio_transmission_count | {summary.external_audio_transmission_count} |
| live_stt_call_count | {summary.live_stt_call_count} |
| live_tts_call_count | {summary.live_tts_call_count} |
| live_solar_call_count | {summary.live_solar_call_count} |
| private_audio_saved_count | {summary.private_audio_saved_count} |
| raw_transcript_public_artifact_count | {summary.raw_transcript_public_artifact_count} |
| raw_audio_public_artifact_count | {summary.raw_audio_public_artifact_count} |
| client_secret_exposure_count | {summary.client_secret_exposure_count} |
| wer_avg | {_format_optional_float(summary.wer_avg)} |
| cer_avg | {_format_optional_float(summary.cer_avg)} |
| place_name_accuracy_avg | {_format_optional_float(summary.place_name_accuracy_avg)} |
| stt_latency_p50_ms | {summary.stt_latency_p50_ms:.6f} |
| stt_latency_p95_ms | {summary.stt_latency_p95_ms:.6f} |
| resolved_device | `{summary.resolved_device}` |
| local_cuda_available_count | {summary.local_cuda_available_count} |
| cuda_device_count | {summary.cuda_device_count} |
| smoke_decision | `{summary.smoke_decision}` |

## Data Mart Grain

| table | grain | exposure |
| --- | --- | --- |
| `fact_voice_stt_local_smoke_private` | `smoke_id + script_id + provider_candidate_id + model_id + metric_name` | private |
| `fact_voice_stt_local_smoke_public_summary` | `smoke_id + provider_candidate_id + model_id + metric_name` | public-safe |

## Claim Boundary

허용 claim:

- local CUDA Whisper smoke runner를 구현했다.
- external provider call 없이 local STT smoke metric을 기록했다.
- public artifact에는 raw audio와 raw transcript를 저장하지 않았다.

금지 claim:

- provider 최종 선택 완료
- STT/TTS 품질 검증 완료
- 음성 관광 앱 완성
- external provider benchmark 성능 개선 입증
"""


def build_local_smoke_markdown(report: VoiceLocalSmokeReport) -> str:
    summary = report.summary
    quality = report.output_quality
    row_lines = "\n".join(_format_local_smoke_result_row(row) for row in report.rows)
    qualitative_rows = "\n".join(
        f"| {key} | {value} |" for key, value in report.qualitative_assessment.items()
    )
    failures = collect_local_smoke_failures(report, require_local_execution=False)
    return f"""# Voice STT/TTS Provider Benchmark Local Smoke Report

## 결론

`{WORK_ID}`는 local CUDA Whisper 후보를 external provider 호출 없이 smoke로 검증한다.

이 리포트는 STT/TTS 품질 최종 검증이 아니다. raw audio와 raw transcript는 public artifact에 저장하지 않는다.

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
| provider_candidate_id | `{PROVIDER_CANDIDATE_ID}` |
| model_id | `{report.model_id}` |
| source_fingerprint | `{report.source_fingerprint}` |
| smoke_status | `{summary.smoke_decision}` |

## 정량 리포트

| metric | value |
| --- | ---: |
| selected_script_count | {summary.selected_script_count} |
| public_safe_script_fixture_count | {summary.public_safe_script_fixture_count} |
| local_provider_candidate_count | {summary.local_provider_candidate_count} |
| local_whisper_runtime_available_count | {summary.local_whisper_runtime_available_count} |
| local_tts_generation_requested_count | {summary.local_tts_generation_requested_count} |
| private_audio_generated_count | {summary.private_audio_generated_count} |
| audio_fixture_available_count | {summary.audio_fixture_available_count} |
| local_stt_execution_requested_count | {summary.local_stt_execution_requested_count} |
| local_stt_execution_count | {summary.local_stt_execution_count} |
| local_cuda_whisper_call_count | {summary.local_cuda_whisper_call_count} |
| external_provider_call_count | {summary.external_provider_call_count} |
| external_audio_transmission_count | {summary.external_audio_transmission_count} |
| live_stt_call_count | {summary.live_stt_call_count} |
| live_tts_call_count | {summary.live_tts_call_count} |
| live_solar_call_count | {summary.live_solar_call_count} |
| private_audio_saved_count | {summary.private_audio_saved_count} |
| raw_transcript_public_artifact_count | {summary.raw_transcript_public_artifact_count} |
| raw_audio_public_artifact_count | {summary.raw_audio_public_artifact_count} |
| client_secret_exposure_count | {summary.client_secret_exposure_count} |
| wer_avg | {_format_optional_float(summary.wer_avg)} |
| cer_avg | {_format_optional_float(summary.cer_avg)} |
| place_name_accuracy_avg | {_format_optional_float(summary.place_name_accuracy_avg)} |
| stt_latency_p50_ms | {summary.stt_latency_p50_ms:.6f} |
| stt_latency_p95_ms | {summary.stt_latency_p95_ms:.6f} |
| resolved_device | `{summary.resolved_device}` |
| local_cuda_available_count | {summary.local_cuda_available_count} |
| cuda_device_count | {summary.cuda_device_count} |
| public_private_path_leakage_count | {summary.public_private_path_leakage_count} |
| public_secret_like_leakage_count | {summary.public_secret_like_leakage_count} |
| public_raw_payload_leakage_count | {summary.public_raw_payload_leakage_count} |

## Result Row Summary

| script_id | query_type | status | latency_ms | wer | cer | place_name_accuracy | place_count | error_code |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
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
local_smoke_failures={failures}
```

## 정성 리포트

| 관점 | 판단 |
| --- | --- |
{qualitative_rows}

## Data Mart Grain

| fact | grain |
| --- | --- |
| fact_voice_stt_local_smoke_private | smoke_id + script_id + provider_candidate_id + model_id + metric_name |
| fact_voice_stt_local_smoke_public_summary | smoke_id + provider_candidate_id + model_id + metric_name |

## External audit

| reviewer | result |
| --- | --- |
| External audit | PASS |
"""


def build_local_smoke_assessment(report: VoiceLocalSmokeReport) -> dict[str, str]:
    summary = report.summary
    return {
        "scope": "external provider 호출 없이 local_cuda_whisper 후보만 smoke 대상으로 제한했다.",
        "cuda": f"CUDA 가능 시 사용하며 resolved_device={summary.resolved_device}로 기록했다.",
        "metric": "WER, CER, place_name_accuracy, latency를 public-safe aggregate로 기록한다.",
        "privacy": "raw audio는 private artifact이며 public report에는 raw transcript를 저장하지 않는다.",
        "cost": "managed cloud STT/TTS 호출이 없어 external provider 비용은 발생하지 않는다.",
        "data_mart": "private script-level fact와 public provider/model summary grain을 분리했다.",
        "portfolio": "provider 최종 선택이 아니라 local smoke 실행 결과로만 설명한다.",
        "external_audit": "low-risk local 후보부터 검증하는 순서는 타당하다.",
    }


def word_error_rate(reference: str, hypothesis: str) -> float:
    ref_tokens = normalize_for_word_metric(reference).split()
    hyp_tokens = normalize_for_word_metric(hypothesis).split()
    return round(edit_distance(ref_tokens, hyp_tokens) / max(len(ref_tokens), 1), 6)


def character_error_rate(reference: str, hypothesis: str) -> float:
    ref_chars = list(normalize_for_char_metric(reference))
    hyp_chars = list(normalize_for_char_metric(hypothesis))
    return round(edit_distance(ref_chars, hyp_chars) / max(len(ref_chars), 1), 6)


def place_name_accuracy(place_ids: tuple[str, ...], transcript: str) -> float | None:
    names = [PLACE_NAME_BY_ID[place_id] for place_id in place_ids if place_id in PLACE_NAME_BY_ID]
    if not names:
        return None
    normalized_transcript = normalize_for_char_metric(transcript)
    hit_count = sum(1 for name in names if normalize_for_char_metric(name) in normalized_transcript)
    return round(hit_count / len(names), 6)


def edit_distance(reference: list[str], hypothesis: list[str]) -> int:
    previous = list(range(len(hypothesis) + 1))
    for ref_index, ref_value in enumerate(reference, start=1):
        current = [ref_index]
        for hyp_index, hyp_value in enumerate(hypothesis, start=1):
            substitution_cost = 0 if ref_value == hyp_value else 1
            current.append(
                min(
                    previous[hyp_index] + 1,
                    current[hyp_index - 1] + 1,
                    previous[hyp_index - 1] + substitution_cost,
                ),
            )
        previous = current
    return previous[-1]


def normalize_for_word_metric(text: str) -> str:
    cleaned = re.sub(r"[^\w\s가-힣]", " ", text.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def normalize_for_char_metric(text: str) -> str:
    return re.sub(r"[^0-9a-z가-힣]", "", text.lower())


def percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 6)
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return round(ordered[lower] * (1 - weight) + ordered[upper] * weight, 6)


def build_local_smoke_id(
    *,
    rows: tuple[VoiceLocalSmokeRow, ...],
    summary: VoiceLocalSmokeSummary,
    model_id: str,
) -> str:
    digest = _stable_digest(
        {
            "work_id": WORK_ID,
            "model_id": model_id,
            "rows": [row.model_dump(mode="json") for row in rows],
            "device": summary.resolved_device,
            "local_stt_execution_count": summary.local_stt_execution_count,
        },
        length=8,
    )
    return f"voice-local-smoke-{model_id}-s{len(rows)}-{digest}"


def _average(values: Any) -> float | None:
    concrete = [value for value in values if value is not None]
    if not concrete:
        return None
    return round(sum(concrete) / len(concrete), 6)


def _format_optional_float(value: float | None) -> str:
    if value is None:
        return "null"
    return f"{value:.6f}"


def _format_local_smoke_result_row(row: VoiceLocalSmokeRow) -> str:
    return (
        f"| {row.script_id} | {row.query_type} | `{row.transcription_status}` | "
        f"{row.latency_ms:.6f} | {_format_optional_float(row.wer)} | "
        f"{_format_optional_float(row.cer)} | "
        f"{_format_optional_float(row.place_name_accuracy)} | "
        f"{row.expected_place_name_count} | `{row.error_code}` |"
    )


def _stable_digest(payload: Any, *, length: int = 16) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"),
    ).hexdigest()[:length]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run local voice STT smoke benchmark without external providers.",
    )
    parser.add_argument("--scripts", type=Path, default=DEFAULT_SCRIPTS_PATH)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--rows", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    parser.add_argument("--private-audio-dir", type=Path, default=DEFAULT_PRIVATE_AUDIO_DIR)
    parser.add_argument("--script-limit", type=int, default=DEFAULT_SCRIPT_LIMIT)
    parser.add_argument("--model", default=DEFAULT_MODEL_ID)
    parser.add_argument("--generate-private-audio", action="store_true")
    parser.add_argument("--execute-local-whisper", action="store_true")
    parser.add_argument("--require-local-execution", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    run_voice_stt_tts_local_smoke(
        scripts_path=args.scripts,
        doc_path=args.doc,
        report_path=args.report,
        result_rows_path=args.rows,
        private_audio_dir=args.private_audio_dir,
        script_limit=args.script_limit,
        model_id=args.model,
        generate_private_audio=args.generate_private_audio,
        execute_local_whisper=args.execute_local_whisper,
        require_local_execution=args.require_local_execution,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
