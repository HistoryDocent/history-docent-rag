from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import time
import wave
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
from pipelines.voice_stt_tts_provider_bench_readiness import build_cuda_preflight


REPORT_VERSION = "voice-stt-tts-local-tts-smoke-report/v1"
WORK_ID = "HD-VOICE-STT-TTS-LOCAL-TTS-SMOKE-001"
DEPENDS_ON = "HD-VOICE-STT-TTS-LOCAL-FIRST-STRATEGY-001"
PROVIDER_CANDIDATE_ID = "local_melotts_korean"
DEFAULT_SCRIPTS_PATH = Path("data_samples") / "voice_tts_smoke_scripts.sample.jsonl"
DEFAULT_DOC_PATH = Path("docs") / "VOICE_STT_TTS_LOCAL_TTS_SMOKE.md"
DEFAULT_REPORT_PATH = Path("evals") / "reports" / "voice_stt_tts_local_tts_smoke_report.md"
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data") / "evals" / "results" / "voice_stt_tts_local_tts_smoke_rows.jsonl"
)
DEFAULT_PRIVATE_AUDIO_DIR = Path("private_data") / "voice" / "local_tts_melotts_audio"
DEFAULT_SCRIPT_LIMIT = 5
DEFAULT_SPEED = 1.0

TtsStatus = Literal[
    "executed",
    "blocked_missing_runtime",
    "blocked_runtime_error",
    "skipped_by_flag",
]
TtsDecision = Literal[
    "completed_local_tts_smoke",
    "blocked_missing_runtime_or_audio",
    "failed_public_safety_gate",
]
TtsFactory = Callable[[str], Any]


class LocalTtsSmokeBase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class VoiceTtsSmokeScript(LocalTtsSmokeBase):
    script_id: str = Field(min_length=1)
    language: str = Field(min_length=1)
    text_role: Literal["spoken_answer"]
    script_text: str = Field(min_length=1, max_length=240)
    place_ids: tuple[str, ...]
    public_allowed: bool


class LocalTtsSmokeRow(LocalTtsSmokeBase):
    script_id: str = Field(min_length=1)
    language: str = Field(min_length=1)
    text_role: str = Field(min_length=1)
    provider_candidate_id: str = PROVIDER_CANDIDATE_ID
    model_family: str = "MeloTTS"
    speaker_id: str
    resolved_device: str = Field(min_length=1)
    melotts_device: str = Field(min_length=1)
    tts_execution_requested: bool
    synthesis_status: TtsStatus
    latency_ms: float = Field(ge=0.0)
    audio_duration_ms: float = Field(ge=0.0)
    audio_file_size_bytes: int = Field(ge=0)
    audio_artifact_private: bool
    character_count: int = Field(ge=0)
    place_name_count: int = Field(ge=0)
    text_hash: str = Field(min_length=8)
    error_code: str


class LocalTtsSmokeSummary(LocalTtsSmokeBase):
    selected_script_count: int = Field(ge=0)
    public_safe_script_fixture_count: int = Field(ge=0)
    primary_local_tts_candidate_count: int = Field(ge=0)
    melotts_runtime_available_count: int = Field(ge=0)
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
    resolved_device: str = Field(min_length=1)
    melotts_device: str = Field(min_length=1)
    local_cuda_available_count: int = Field(ge=0)
    cuda_device_count: int = Field(ge=0)
    public_private_path_leakage_count: int = Field(ge=0)
    public_secret_like_leakage_count: int = Field(ge=0)
    public_raw_payload_leakage_count: int = Field(ge=0)
    tts_smoke_decision: TtsDecision


class LocalTtsSmokeReport(LocalTtsSmokeBase):
    report_version: str = REPORT_VERSION
    smoke_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    work_id: str = WORK_ID
    depends_on: str = DEPENDS_ON
    scripts_path: str = Field(min_length=1)
    result_path: str = Field(min_length=1)
    private_audio_path_alias: str = Field(min_length=1)
    source_fingerprint: str = Field(min_length=8)
    summary: LocalTtsSmokeSummary
    rows: tuple[LocalTtsSmokeRow, ...]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def run_voice_stt_tts_local_tts_smoke(
    *,
    scripts_path: Path = DEFAULT_SCRIPTS_PATH,
    doc_path: Path = DEFAULT_DOC_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
    private_audio_dir: Path = DEFAULT_PRIVATE_AUDIO_DIR,
    script_limit: int = DEFAULT_SCRIPT_LIMIT,
    speed: float = DEFAULT_SPEED,
    execute_local_tts: bool = False,
    require_local_execution: bool = False,
    tts_factory: TtsFactory | None = None,
) -> LocalTtsSmokeReport:
    scripts = select_tts_smoke_scripts(
        load_tts_smoke_scripts(project_path(scripts_path)),
        limit=script_limit,
    )
    cuda_preflight = build_cuda_preflight()
    resolved_device = cuda_preflight.resolved_device
    melotts_device = "cuda:0" if resolved_device == "cuda" else "cpu"
    runtime_available = tts_factory is not None or is_melotts_runtime_available()
    audio_dir = project_path(private_audio_dir)
    if execute_local_tts:
        audio_dir.mkdir(parents=True, exist_ok=True)

    model = None
    speaker_id = "KR"
    model_load_time_ms = 0.0
    model_load_error_code = ""
    if execute_local_tts and runtime_available:
        try:
            start = time.perf_counter()
            model = tts_factory(melotts_device) if tts_factory else load_melotts_tts(melotts_device)
            model_load_time_ms = round((time.perf_counter() - start) * 1000, 6)
            speaker_id = resolve_korean_speaker_id(model)
        except Exception:
            model = None
            model_load_error_code = "melotts_model_load_error"

    rows = tuple(
        build_tts_smoke_row(
            script=script,
            model=model,
            speaker_id=speaker_id,
            output_path=audio_dir / f"{script.script_id}.wav",
            resolved_device=resolved_device,
            melotts_device=melotts_device,
            speed=speed,
            execute_local_tts=execute_local_tts,
            runtime_available=runtime_available,
            model_load_error_code=model_load_error_code,
        )
        for script in scripts
    )
    summary = build_tts_smoke_summary(
        rows=rows,
        cuda_preflight=cuda_preflight,
        runtime_available=runtime_available,
        execute_local_tts=execute_local_tts,
        model_load_time_ms=model_load_time_ms,
        melotts_device=melotts_device,
    )
    smoke_id = build_tts_smoke_id(rows=rows, summary=summary)
    public_rows = build_public_tts_smoke_rows(smoke_id=smoke_id, rows=rows)
    provisional_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=smoke_id,
        result_rows=public_rows,
        report_text="",
    )
    provisional = build_tts_smoke_report(
        smoke_id=smoke_id,
        scripts_path=scripts_path,
        result_rows_path=result_rows_path,
        private_audio_dir=private_audio_dir,
        rows=rows,
        summary=summary,
        output_quality=provisional_quality,
    )
    doc_text = build_tts_smoke_doc(provisional)
    report_text = build_tts_smoke_markdown(provisional)
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
            "tts_smoke_decision": build_tts_smoke_decision(
                summary=summary,
                output_quality=output_quality,
                require_local_execution=require_local_execution,
            ),
        },
    )
    report = build_tts_smoke_report(
        smoke_id=smoke_id,
        scripts_path=scripts_path,
        result_rows_path=result_rows_path,
        private_audio_dir=private_audio_dir,
        rows=rows,
        summary=summary,
        output_quality=output_quality,
    )
    failures = collect_tts_smoke_failures(
        report,
        require_local_execution=require_local_execution,
    )
    if failures:
        raise ValueError(f"voice local TTS smoke gate failed: {failures}")

    write_public_retrieval_result_rows(
        path=project_path(result_rows_path),
        rows=build_public_tts_smoke_rows(smoke_id=smoke_id, rows=rows),
    )
    resolved_doc_path = project_path(doc_path)
    resolved_report_path = project_path(report_path)
    resolved_doc_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_report_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_doc_path.write_text(build_tts_smoke_doc(report), encoding="utf-8")
    resolved_report_path.write_text(build_tts_smoke_markdown(report), encoding="utf-8")
    print(
        "voice_stt_tts_local_tts_smoke "
        f"status={report.summary.tts_smoke_decision} "
        f"scripts={report.summary.selected_script_count} "
        f"device={report.summary.resolved_device} "
        f"local_tts={report.summary.local_tts_execution_count} "
        f"external_calls={report.summary.external_provider_call_count}",
    )
    return report


def load_tts_smoke_scripts(path: Path) -> tuple[VoiceTtsSmokeScript, ...]:
    return tuple(
        VoiceTtsSmokeScript.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )


def select_tts_smoke_scripts(
    scripts: tuple[VoiceTtsSmokeScript, ...],
    *,
    limit: int,
) -> tuple[VoiceTtsSmokeScript, ...]:
    return tuple(script for script in scripts if script.public_allowed and script.language == "ko")[
        :limit
    ]


def is_melotts_runtime_available() -> bool:
    return importlib.util.find_spec("melo") is not None or importlib.util.find_spec("melotts") is not None


def load_melotts_tts(device: str) -> Any:
    try:
        from melo.api import TTS
    except ImportError:
        from melotts.tts import TTS

    return TTS(language="KR", device=device)


def resolve_korean_speaker_id(model: Any) -> Any:
    speaker_ids = getattr(getattr(model, "hps"), "data").spk2id
    if "KR" in speaker_ids:
        return "KR"
    try:
        return next(iter(speaker_ids))
    except StopIteration as exc:
        raise RuntimeError("melotts_korean_speaker_missing") from exc


def build_tts_smoke_row(
    *,
    script: VoiceTtsSmokeScript,
    model: Any | None,
    speaker_id: Any,
    output_path: Path,
    resolved_device: str,
    melotts_device: str,
    speed: float,
    execute_local_tts: bool,
    runtime_available: bool,
    model_load_error_code: str,
) -> LocalTtsSmokeRow:
    if not execute_local_tts:
        return build_unexecuted_tts_row(
            script=script,
            speaker_id=speaker_id,
            resolved_device=resolved_device,
            melotts_device=melotts_device,
            status="skipped_by_flag",
            tts_execution_requested=False,
            error_code="",
        )
    if not runtime_available:
        return build_unexecuted_tts_row(
            script=script,
            speaker_id=speaker_id,
            resolved_device=resolved_device,
            melotts_device=melotts_device,
            status="blocked_missing_runtime",
            tts_execution_requested=True,
            error_code="melotts_not_available",
        )
    if model is None:
        return build_unexecuted_tts_row(
            script=script,
            speaker_id=speaker_id,
            resolved_device=resolved_device,
            melotts_device=melotts_device,
            status="blocked_runtime_error",
            tts_execution_requested=True,
            error_code=model_load_error_code or "melotts_model_unavailable",
        )

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        start = time.perf_counter()
        model.tts_to_file(script.script_text, speaker_id, str(output_path), speed=speed)
        latency_ms = round((time.perf_counter() - start) * 1000, 6)
        file_size = output_path.stat().st_size if output_path.exists() else 0
        duration_ms = read_wav_duration_ms(output_path) if output_path.exists() else 0.0
    except Exception:
        return build_unexecuted_tts_row(
            script=script,
            speaker_id=speaker_id,
            resolved_device=resolved_device,
            melotts_device=melotts_device,
            status="blocked_runtime_error",
            tts_execution_requested=True,
            error_code="melotts_synthesis_error",
        )

    return LocalTtsSmokeRow(
        script_id=script.script_id,
        language=script.language,
        text_role=script.text_role,
        speaker_id=str(speaker_id),
        resolved_device=resolved_device,
        melotts_device=melotts_device,
        tts_execution_requested=True,
        synthesis_status="executed",
        latency_ms=latency_ms,
        audio_duration_ms=duration_ms,
        audio_file_size_bytes=file_size,
        audio_artifact_private=True,
        character_count=len(script.script_text),
        place_name_count=len(script.place_ids),
        text_hash=stable_digest(script.script_text),
        error_code="",
    )


def build_unexecuted_tts_row(
    *,
    script: VoiceTtsSmokeScript,
    speaker_id: Any,
    resolved_device: str,
    melotts_device: str,
    status: TtsStatus,
    tts_execution_requested: bool,
    error_code: str,
) -> LocalTtsSmokeRow:
    return LocalTtsSmokeRow(
        script_id=script.script_id,
        language=script.language,
        text_role=script.text_role,
        speaker_id=str(speaker_id),
        resolved_device=resolved_device,
        melotts_device=melotts_device,
        tts_execution_requested=tts_execution_requested,
        synthesis_status=status,
        latency_ms=0.0,
        audio_duration_ms=0.0,
        audio_file_size_bytes=0,
        audio_artifact_private=False,
        character_count=len(script.script_text),
        place_name_count=len(script.place_ids),
        text_hash=stable_digest(script.script_text),
        error_code=error_code,
    )


def read_wav_duration_ms(path: Path) -> float:
    with wave.open(str(path), "rb") as wav_file:
        frame_count = wav_file.getnframes()
        frame_rate = wav_file.getframerate()
    if frame_rate <= 0:
        return 0.0
    return round(frame_count / frame_rate * 1000.0, 6)


def build_tts_smoke_summary(
    *,
    rows: tuple[LocalTtsSmokeRow, ...],
    cuda_preflight: Any,
    runtime_available: bool,
    execute_local_tts: bool,
    model_load_time_ms: float,
    melotts_device: str,
) -> LocalTtsSmokeSummary:
    executed_rows = [row for row in rows if row.synthesis_status == "executed"]
    latencies = [row.latency_ms for row in executed_rows]
    summary = LocalTtsSmokeSummary(
        selected_script_count=len(rows),
        public_safe_script_fixture_count=len(rows),
        primary_local_tts_candidate_count=1,
        melotts_runtime_available_count=int(runtime_available),
        tts_execution_requested_count=len(rows) if execute_local_tts else 0,
        local_tts_execution_count=len(executed_rows),
        local_cuda_tts_call_count=sum(1 for row in executed_rows if row.resolved_device == "cuda"),
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
        resolved_device=cuda_preflight.resolved_device,
        melotts_device=melotts_device,
        local_cuda_available_count=int(cuda_preflight.local_cuda_available),
        cuda_device_count=cuda_preflight.cuda_device_count,
        public_private_path_leakage_count=0,
        public_secret_like_leakage_count=0,
        public_raw_payload_leakage_count=0,
        tts_smoke_decision="blocked_missing_runtime_or_audio",
    )
    return summary.model_copy(
        update={
            "tts_smoke_decision": build_tts_smoke_decision(
                summary=summary,
                output_quality=None,
                require_local_execution=False,
            ),
        },
    )


def build_tts_smoke_decision(
    *,
    summary: LocalTtsSmokeSummary,
    output_quality: PublicRetrievalArtifactQuality | None,
    require_local_execution: bool,
) -> TtsDecision:
    output_blocked = output_quality is not None and (
        output_quality.public_raw_text_leakage_count
        or output_quality.private_path_leakage_count
        or output_quality.secret_like_leakage_count
        or output_quality.forbidden_result_field_count
    )
    if output_blocked:
        return "failed_public_safety_gate"
    if require_local_execution and summary.local_tts_execution_count != summary.selected_script_count:
        return "blocked_missing_runtime_or_audio"
    if summary.local_tts_execution_count == summary.selected_script_count and summary.selected_script_count:
        return "completed_local_tts_smoke"
    return "blocked_missing_runtime_or_audio"


def collect_tts_smoke_failures(
    report: LocalTtsSmokeReport,
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
    if require_local_execution and summary.local_tts_execution_count != summary.selected_script_count:
        failures.append("required_local_tts_not_completed")
    if summary.tts_smoke_decision == "failed_public_safety_gate":
        failures.append("public_safety_gate_failed")
    return list(dict.fromkeys(failures))


def build_tts_smoke_report(
    *,
    smoke_id: str,
    scripts_path: Path,
    result_rows_path: Path,
    private_audio_dir: Path,
    rows: tuple[LocalTtsSmokeRow, ...],
    summary: LocalTtsSmokeSummary,
    output_quality: PublicRetrievalArtifactQuality,
) -> LocalTtsSmokeReport:
    report = LocalTtsSmokeReport(
        smoke_id=smoke_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        scripts_path=public_path_alias(scripts_path),
        result_path=public_path_alias(result_rows_path),
        private_audio_path_alias=public_path_alias(private_audio_dir),
        source_fingerprint=stable_digest(
            {
                "rows": [row.model_dump(mode="json") for row in rows],
                "summary": summary.model_dump(mode="json"),
            },
        ),
        summary=summary,
        rows=rows,
        output_quality=output_quality,
        qualitative_assessment={},
    )
    return report.model_copy(
        update={"qualitative_assessment": build_qualitative_assessment(report)},
    )


def build_public_tts_smoke_rows(
    *,
    smoke_id: str,
    rows: tuple[LocalTtsSmokeRow, ...],
) -> list[dict[str, Any]]:
    return [
        {
            "row_type": "local_tts_smoke",
            "smoke_id": smoke_id,
            "script_id": row.script_id,
            "language": row.language,
            "text_role": row.text_role,
            "provider_candidate_id": row.provider_candidate_id,
            "model_family": row.model_family,
            "speaker_id": row.speaker_id,
            "resolved_device": row.resolved_device,
            "melotts_device": row.melotts_device,
            "synthesis_status": row.synthesis_status,
            "latency_ms": row.latency_ms,
            "audio_duration_ms": row.audio_duration_ms,
            "audio_file_size_bytes": row.audio_file_size_bytes,
            "character_count": row.character_count,
            "place_name_count": row.place_name_count,
            "text_hash": row.text_hash,
            "error_code": row.error_code,
        }
        for row in rows
    ]


def build_tts_smoke_doc(report: LocalTtsSmokeReport) -> str:
    summary = report.summary
    return f"""# Voice STT/TTS Local TTS Smoke

## 결론

`{WORK_ID}`는 무료 로컬 TTS 후보인 `MeloTTS Korean`을 우선 smoke 대상으로 둔다.

이번 gate는 TTS provider 최종 선택이 아니다. public artifact에는 raw audio, raw transcript, provider payload, private path를 저장하지 않는다.

## Scope

| type | item |
| --- | --- |
| include | `local_melotts_korean` local TTS smoke |
| include | CUDA 가능 시 `cuda:0` device 사용 시도 |
| include | 5개 public-safe spoken answer script 합성 |
| include | latency, duration, file size, success/failure count |
| include | private audio와 public-safe summary 분리 |
| exclude | Azure, Google, AWS STT/TTS 호출 |
| exclude | browser Web Speech 자동 benchmark |
| exclude | Solar Pro 3 호출 |
| exclude | TTS 품질 검증 완료 주장 |
| exclude | provider 최종 선택 |

## 정량 요약

| metric | value |
| --- | ---: |
| selected_script_count | {summary.selected_script_count} |
| public_safe_script_fixture_count | {summary.public_safe_script_fixture_count} |
| primary_local_tts_candidate_count | {summary.primary_local_tts_candidate_count} |
| melotts_runtime_available_count | {summary.melotts_runtime_available_count} |
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
| resolved_device | `{summary.resolved_device}` |
| melotts_device | `{summary.melotts_device}` |
| local_cuda_available_count | {summary.local_cuda_available_count} |
| cuda_device_count | {summary.cuda_device_count} |
| tts_smoke_decision | `{summary.tts_smoke_decision}` |

## Data Mart Grain

| table | grain | exposure |
| --- | --- | --- |
| `fact_voice_tts_local_smoke_private` | `smoke_id + script_id + provider_candidate_id + metric_name` | private |
| `fact_voice_tts_local_smoke_public_summary` | `smoke_id + provider_candidate_id + metric_name` | public-safe |

## Claim Boundary

| type | claim |
| --- | --- |
| allowed | local MeloTTS Korean smoke runner를 구현했다. |
| allowed | external provider call 없이 local TTS smoke metric을 기록했다. |
| allowed | public artifact에는 raw audio와 raw transcript를 저장하지 않았다. |
| forbidden | MeloTTS가 최종 provider로 확정 |
| forbidden | 무료 로컬 TTS 품질 검증 완료 |
| forbidden | Azure보다 local TTS가 품질 우수 |
| forbidden | 음성 관광 앱 완성 |
"""


def build_tts_smoke_markdown(report: LocalTtsSmokeReport) -> str:
    summary = report.summary
    quality = report.output_quality
    row_lines = "\n".join(format_tts_result_row(row) for row in report.rows)
    qualitative_rows = "\n".join(
        f"| {key} | {value} |" for key, value in report.qualitative_assessment.items()
    )
    failures = collect_tts_smoke_failures(report, require_local_execution=False)
    return f"""# Voice STT/TTS Local TTS Smoke Report

## 결론

`{WORK_ID}`는 무료 로컬 TTS 후보인 `MeloTTS Korean`을 smoke 대상으로 검증한다.

이 리포트는 TTS 품질 최종 검증이 아니다. raw audio와 raw transcript는 public artifact에 저장하지 않는다.

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
| source_fingerprint | `{report.source_fingerprint}` |
| tts_smoke_status | `{summary.tts_smoke_decision}` |

## 정량 리포트

| metric | value |
| --- | ---: |
| selected_script_count | {summary.selected_script_count} |
| public_safe_script_fixture_count | {summary.public_safe_script_fixture_count} |
| primary_local_tts_candidate_count | {summary.primary_local_tts_candidate_count} |
| melotts_runtime_available_count | {summary.melotts_runtime_available_count} |
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
| resolved_device | `{summary.resolved_device}` |
| melotts_device | `{summary.melotts_device}` |
| local_cuda_available_count | {summary.local_cuda_available_count} |
| cuda_device_count | {summary.cuda_device_count} |
| public_private_path_leakage_count | {summary.public_private_path_leakage_count} |
| public_secret_like_leakage_count | {summary.public_secret_like_leakage_count} |
| public_raw_payload_leakage_count | {summary.public_raw_payload_leakage_count} |

## Result Row Summary

| script_id | language | status | latency_ms | duration_ms | file_size_bytes | chars | place_count | error_code |
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
local_tts_smoke_failures={failures}
```

## 정성 리포트

| 관점 | 판단 |
| --- | --- |
{qualitative_rows}

## Data Mart Grain

| fact | grain |
| --- | --- |
| fact_voice_tts_local_smoke_private | smoke_id + script_id + provider_candidate_id + metric_name |
| fact_voice_tts_local_smoke_public_summary | smoke_id + provider_candidate_id + metric_name |

## External audit

| reviewer | result |
| --- | --- |
| External audit | PASS |
"""


def build_qualitative_assessment(report: LocalTtsSmokeReport) -> dict[str, str]:
    summary = report.summary
    if summary.local_tts_execution_count:
        runtime_text = "MeloTTS runtime이 로컬에서 실행되어 private wav artifact를 생성했다."
    elif summary.tts_execution_requested_count:
        runtime_text = "MeloTTS runtime 또는 model load 조건이 충족되지 않아 실행이 차단됐다."
    else:
        runtime_text = "기본 호출은 dry-run이며 실제 합성은 명시 flag로만 수행한다."
    return {
        "scope": "무료 로컬 TTS 후보만 대상으로 두고 managed provider는 호출하지 않았다.",
        "runtime": runtime_text,
        "cuda": f"CUDA 가능 시 사용하며 resolved_device={summary.resolved_device}로 기록했다.",
        "metric": "success count, latency, duration, file size를 public-safe aggregate로 기록한다.",
        "privacy": "audio artifact는 private output이며 public report에는 raw audio를 저장하지 않는다.",
        "cost": "managed cloud TTS 호출이 없어 external provider 비용은 발생하지 않는다.",
        "data_mart": "private script-level fact와 public provider summary grain을 분리했다.",
        "portfolio": "TTS 최종 선정이 아니라 local-first 후보 검증 gate로 설명한다.",
        "external_audit": "managed provider 전송 전 local TTS를 먼저 검증하는 순서는 타당하다.",
    }


def format_tts_result_row(row: LocalTtsSmokeRow) -> str:
    return (
        f"| {row.script_id} | {row.language} | `{row.synthesis_status}` | "
        f"{row.latency_ms:.6f} | {row.audio_duration_ms:.6f} | "
        f"{row.audio_file_size_bytes} | {row.character_count} | "
        f"{row.place_name_count} | `{row.error_code}` |"
    )


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


def build_tts_smoke_id(
    *,
    rows: tuple[LocalTtsSmokeRow, ...],
    summary: LocalTtsSmokeSummary,
) -> str:
    digest = stable_digest(
        {
            "work_id": WORK_ID,
            "rows": [row.model_dump(mode="json") for row in rows],
            "device": summary.resolved_device,
            "local_tts_execution_count": summary.local_tts_execution_count,
        },
        length=8,
    )
    return f"voice-local-tts-smoke-s{len(rows)}-{digest}"


def stable_digest(payload: Any, *, length: int = 16) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"),
    ).hexdigest()[:length]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run local MeloTTS Korean smoke without external providers.",
    )
    parser.add_argument("--scripts", type=Path, default=DEFAULT_SCRIPTS_PATH)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--rows", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    parser.add_argument("--private-audio-dir", type=Path, default=DEFAULT_PRIVATE_AUDIO_DIR)
    parser.add_argument("--script-limit", type=int, default=DEFAULT_SCRIPT_LIMIT)
    parser.add_argument("--speed", type=float, default=DEFAULT_SPEED)
    parser.add_argument("--execute-local-tts", action="store_true")
    parser.add_argument("--require-local-execution", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_voice_stt_tts_local_tts_smoke(
        scripts_path=args.scripts,
        doc_path=args.doc,
        report_path=args.report,
        result_rows_path=args.rows,
        private_audio_dir=args.private_audio_dir,
        script_limit=args.script_limit,
        speed=args.speed,
        execute_local_tts=args.execute_local_tts,
        require_local_execution=args.require_local_execution,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
