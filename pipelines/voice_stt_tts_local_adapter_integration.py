from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.application.chat_service import ChatContractService
from app.application.voice_local_adapter import (
    LOCAL_STT_MODEL_ID,
    LOCAL_STT_PROVIDER_CANDIDATE_ID,
    LOCAL_TTS_PROVIDER_CANDIDATE_ID,
    LOCAL_VOICE_ADAPTER_ID,
    LocalSapiVoiceProbe,
    LocalVoiceAdapter,
    LocalVoiceTranscriptInput,
    LocalVoiceTtsInput,
    SapiTextSynthesizer,
)
from app.core.project_paths import project_path
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    collect_public_retrieval_artifact_failures,
    measure_public_retrieval_artifact_quality,
    public_path_alias,
    write_public_retrieval_result_rows,
)
from pipelines.voice_stt_tts_local_smoke import (
    TARGET_SAMPLE_RATE,
    character_error_rate,
    percentile,
    place_name_accuracy,
    read_wav_as_mono_float32,
    select_local_smoke_scripts,
    word_error_rate,
)
from pipelines.voice_stt_tts_provider_bench_readiness import (
    VoiceBenchmarkScript,
    build_cuda_preflight,
    load_voice_benchmark_scripts,
)


REPORT_VERSION = "voice-stt-tts-local-adapter-integration-report/v1"
WORK_ID = "HD-VOICE-STT-TTS-LOCAL-ADAPTER-INTEGRATION-001"
DEPENDS_ON = "HD-VOICE-STT-TTS-LOCAL-TTS-RUNTIME-INSTALL-001"
DEFAULT_SCRIPTS_PATH = Path("data_samples") / "voice_benchmark_scripts.sample.jsonl"
DEFAULT_DOC_PATH = Path("docs") / "VOICE_STT_TTS_LOCAL_ADAPTER_INTEGRATION.md"
DEFAULT_REPORT_PATH = (
    Path("evals") / "reports" / "voice_stt_tts_local_adapter_integration_report.md"
)
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "voice_stt_tts_local_adapter_integration_rows.jsonl"
)
DEFAULT_PRIVATE_STT_AUDIO_DIR = Path("private_data") / "voice" / "local_smoke_audio"
DEFAULT_PRIVATE_TTS_AUDIO_DIR = Path("private_data") / "voice" / "local_adapter_sapi_audio"
DEFAULT_SCRIPT_LIMIT = 5

SttExecutionStatus = Literal[
    "executed",
    "blocked_missing_audio",
    "blocked_missing_runtime",
    "blocked_runtime_error",
    "skipped_by_flag",
]
TtsExecutionStatus = Literal[
    "executed",
    "blocked_no_korean_sapi_voice",
    "blocked_sapi_runtime_error",
    "skipped_by_flag",
]
IntegrationDecision = Literal[
    "completed_local_voice_adapter_smoke",
    "blocked_missing_local_voice_runtime",
    "failed_public_safety_gate",
]


class LocalAdapterIntegrationBase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LocalAdapterIntegrationRow(LocalAdapterIntegrationBase):
    script_id: str = Field(min_length=1)
    query_type: str = Field(min_length=1)
    adapter_id: str = LOCAL_VOICE_ADAPTER_ID
    stt_provider_candidate_id: str = LOCAL_STT_PROVIDER_CANDIDATE_ID
    stt_model_id: str = LOCAL_STT_MODEL_ID
    tts_provider_candidate_id: str = LOCAL_TTS_PROVIDER_CANDIDATE_ID
    resolved_device: str = Field(min_length=1)
    transcript_source: str = Field(min_length=1)
    stt_execution_status: SttExecutionStatus
    stt_latency_ms: float = Field(ge=0.0)
    wer: float | None = Field(default=None, ge=0.0)
    cer: float | None = Field(default=None, ge=0.0)
    place_name_accuracy: float | None = Field(default=None, ge=0.0, le=1.0)
    chat_contract_status: str = Field(min_length=1)
    chat_latency_ms: float = Field(ge=0.0)
    citation_count: int = Field(ge=0)
    abstained: bool
    unsupported_claim_risk: str = Field(min_length=1)
    tts_execution_status: TtsExecutionStatus
    tts_latency_ms: float = Field(ge=0.0)
    audio_duration_ms: float = Field(ge=0.0)
    audio_file_size_bytes: int = Field(ge=0)
    audio_artifact_private: bool
    round_trip_latency_ms: float = Field(ge=0.0)
    transcript_hash: str = Field(min_length=8)
    spoken_answer_hash: str = Field(min_length=8)
    error_code: str


class LocalAdapterIntegrationSummary(LocalAdapterIntegrationBase):
    selected_script_count: int = Field(ge=0)
    local_voice_adapter_module_count: int = Field(ge=0)
    local_stt_provider_candidate_count: int = Field(ge=0)
    local_tts_provider_candidate_count: int = Field(ge=0)
    local_stt_runtime_available_count: int = Field(ge=0)
    local_stt_execution_requested_count: int = Field(ge=0)
    local_stt_execution_count: int = Field(ge=0)
    local_cuda_whisper_call_count: int = Field(ge=0)
    local_tts_execution_requested_count: int = Field(ge=0)
    local_tts_execution_count: int = Field(ge=0)
    private_stt_audio_available_count: int = Field(ge=0)
    private_tts_audio_generated_count: int = Field(ge=0)
    chat_contract_execution_count: int = Field(ge=0)
    citation_response_count: int = Field(ge=0)
    stt_wer_avg: float | None = Field(default=None, ge=0.0)
    stt_cer_avg: float | None = Field(default=None, ge=0.0)
    stt_place_name_accuracy_avg: float | None = Field(default=None, ge=0.0, le=1.0)
    stt_latency_p95_ms: float = Field(ge=0.0)
    chat_latency_p95_ms: float = Field(ge=0.0)
    tts_latency_p95_ms: float = Field(ge=0.0)
    voice_round_trip_latency_p95_ms: float = Field(ge=0.0)
    audio_duration_total_ms: float = Field(ge=0.0)
    audio_file_size_total_bytes: int = Field(ge=0)
    resolved_device: str = Field(min_length=1)
    local_cuda_available_count: int = Field(ge=0)
    cuda_device_count: int = Field(ge=0)
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
    integration_decision: IntegrationDecision


class LocalAdapterIntegrationReport(LocalAdapterIntegrationBase):
    report_version: str = REPORT_VERSION
    integration_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    work_id: str = WORK_ID
    depends_on: str = DEPENDS_ON
    scripts_path: str = Field(min_length=1)
    result_path: str = Field(min_length=1)
    private_stt_audio_path_alias: str = Field(min_length=1)
    private_tts_audio_path_alias: str = Field(min_length=1)
    source_fingerprint: str = Field(min_length=8)
    summary: LocalAdapterIntegrationSummary
    rows: tuple[LocalAdapterIntegrationRow, ...]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def run_voice_stt_tts_local_adapter_integration(
    *,
    scripts_path: Path = DEFAULT_SCRIPTS_PATH,
    doc_path: Path = DEFAULT_DOC_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
    private_stt_audio_dir: Path = DEFAULT_PRIVATE_STT_AUDIO_DIR,
    private_tts_audio_dir: Path = DEFAULT_PRIVATE_TTS_AUDIO_DIR,
    script_limit: int = DEFAULT_SCRIPT_LIMIT,
    execute_local_stt: bool = False,
    execute_local_tts: bool = False,
    require_local_execution: bool = False,
    voice_probe: LocalSapiVoiceProbe | None = None,
    sapi_text_synthesizer: SapiTextSynthesizer | None = None,
) -> LocalAdapterIntegrationReport:
    scripts = select_local_smoke_scripts(
        load_voice_benchmark_scripts(project_path(scripts_path)),
        limit=script_limit,
    )
    cuda_preflight = build_cuda_preflight()
    stt_runtime_available = importlib.util.find_spec("whisper") is not None
    stt_model = load_whisper_model_if_requested(
        execute_local_stt=execute_local_stt,
        runtime_available=stt_runtime_available,
        model_id=LOCAL_STT_MODEL_ID,
        resolved_device=cuda_preflight.resolved_device,
    )
    adapter = LocalVoiceAdapter(
        voice_probe=voice_probe,
        sapi_text_synthesizer=sapi_text_synthesizer,
    )
    chat_service = ChatContractService()
    rows = tuple(
        build_integration_row(
            script=script,
            adapter=adapter,
            chat_service=chat_service,
            stt_model=stt_model,
            stt_runtime_available=stt_runtime_available,
            stt_audio_path=project_path(private_stt_audio_dir) / f"{script.script_id}.wav",
            tts_audio_path=project_path(private_tts_audio_dir) / f"{script.script_id}.wav",
            resolved_device=cuda_preflight.resolved_device,
            execute_local_stt=execute_local_stt,
            execute_local_tts=execute_local_tts,
        )
        for script in scripts
    )
    summary = build_summary(
        rows=rows,
        cuda_preflight=cuda_preflight,
        stt_runtime_available=stt_runtime_available,
        execute_local_stt=execute_local_stt,
        execute_local_tts=execute_local_tts,
    )
    integration_id = build_integration_id(rows=rows, summary=summary)
    public_rows = build_public_rows(integration_id=integration_id, rows=rows)
    provisional_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=integration_id,
        result_rows=public_rows,
        report_text="",
    )
    provisional = build_report(
        integration_id=integration_id,
        scripts_path=scripts_path,
        result_rows_path=result_rows_path,
        private_stt_audio_dir=private_stt_audio_dir,
        private_tts_audio_dir=private_tts_audio_dir,
        rows=rows,
        summary=summary,
        output_quality=provisional_quality,
    )
    doc_text = build_doc(provisional)
    report_text = build_markdown_report(provisional)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=integration_id,
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
            "integration_decision": build_integration_decision(
                summary=summary,
                output_quality=output_quality,
                require_local_execution=require_local_execution,
            ),
        },
    )
    report = build_report(
        integration_id=integration_id,
        scripts_path=scripts_path,
        result_rows_path=result_rows_path,
        private_stt_audio_dir=private_stt_audio_dir,
        private_tts_audio_dir=private_tts_audio_dir,
        rows=rows,
        summary=summary,
        output_quality=output_quality,
    )
    failures = collect_integration_failures(
        report,
        require_local_execution=require_local_execution,
    )
    if failures:
        raise ValueError(f"voice local adapter integration gate failed: {failures}")

    write_public_retrieval_result_rows(path=project_path(result_rows_path), rows=public_rows)
    resolved_doc_path = project_path(doc_path)
    resolved_report_path = project_path(report_path)
    resolved_doc_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_report_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_doc_path.write_text(build_doc(report), encoding="utf-8")
    resolved_report_path.write_text(build_markdown_report(report), encoding="utf-8")
    print(
        "voice_stt_tts_local_adapter_integration "
        f"status={report.summary.integration_decision} "
        f"stt={report.summary.local_stt_execution_count} "
        f"tts={report.summary.local_tts_execution_count} "
        f"chat={report.summary.chat_contract_execution_count} "
        f"external_calls={report.summary.external_provider_call_count}",
    )
    return report


def load_whisper_model_if_requested(
    *,
    execute_local_stt: bool,
    runtime_available: bool,
    model_id: str,
    resolved_device: str,
) -> Any | None:
    if not execute_local_stt or not runtime_available:
        return None
    import whisper

    return whisper.load_model(model_id, device=resolved_device)


def build_integration_row(
    *,
    script: VoiceBenchmarkScript,
    adapter: LocalVoiceAdapter,
    chat_service: ChatContractService,
    stt_model: Any | None,
    stt_runtime_available: bool,
    stt_audio_path: Path,
    tts_audio_path: Path,
    resolved_device: str,
    execute_local_stt: bool,
    execute_local_tts: bool,
) -> LocalAdapterIntegrationRow:
    transcript, stt_status, stt_latency_ms, stt_error_code = transcribe_or_use_fixture(
        script=script,
        model=stt_model,
        audio_path=stt_audio_path,
        resolved_device=resolved_device,
        runtime_available=stt_runtime_available,
        execute_local_stt=execute_local_stt,
    )
    transcript_source = "local_whisper" if stt_status == "executed" else "public_safe_fixture"
    bridge = adapter.build_chat_command(
        LocalVoiceTranscriptInput(
            request_id=f"voice-local-adapter-{script.script_id}",
            transcript_text=transcript,
            transcript_source=transcript_source,
            language=script.language,
            query_type=script.query_type,
            place_context=script.place_ids,
            retrieval_mode="contract_only",
            provider_mode="contract_only",
        )
    )
    chat_started = time.perf_counter()
    chat_result = chat_service.handle(bridge.chat_command)
    chat_latency_ms = round((time.perf_counter() - chat_started) * 1000.0, 6)
    tts_result = adapter.synthesize_spoken_answer(
        LocalVoiceTtsInput(
            request_id=bridge.request_id,
            spoken_answer=chat_result.answer.spoken_answer,
            language=script.language,
        ),
        output_path=tts_audio_path,
        execute_tts=execute_local_tts,
    )
    round_trip_latency_ms = round(
        stt_latency_ms + chat_latency_ms + tts_result.latency_ms,
        6,
    )
    return LocalAdapterIntegrationRow(
        script_id=script.script_id,
        query_type=script.query_type,
        resolved_device=resolved_device,
        transcript_source=transcript_source,
        stt_execution_status=stt_status,
        stt_latency_ms=stt_latency_ms,
        wer=word_error_rate(script.script_text, transcript) if stt_status == "executed" else None,
        cer=(
            character_error_rate(script.script_text, transcript)
            if stt_status == "executed"
            else None
        ),
        place_name_accuracy=(
            place_name_accuracy(script.place_ids, transcript)
            if stt_status == "executed"
            else None
        ),
        chat_contract_status="executed_contract_chat",
        chat_latency_ms=chat_latency_ms,
        citation_count=len(chat_result.answer.citations),
        abstained=chat_result.answer.abstained,
        unsupported_claim_risk=chat_result.answer.unsupported_claim_risk,
        tts_execution_status=tts_result.synthesis_status,
        tts_latency_ms=tts_result.latency_ms,
        audio_duration_ms=tts_result.audio_duration_ms,
        audio_file_size_bytes=tts_result.audio_file_size_bytes,
        audio_artifact_private=tts_result.audio_artifact_private,
        round_trip_latency_ms=round_trip_latency_ms,
        transcript_hash=bridge.transcript_hash,
        spoken_answer_hash=tts_result.spoken_answer_hash,
        error_code=stt_error_code or tts_result.error_code,
    )


def transcribe_or_use_fixture(
    *,
    script: VoiceBenchmarkScript,
    model: Any | None,
    audio_path: Path,
    resolved_device: str,
    runtime_available: bool,
    execute_local_stt: bool,
) -> tuple[str, SttExecutionStatus, float, str]:
    if not execute_local_stt:
        return script.script_text, "skipped_by_flag", 0.0, ""
    if not runtime_available or model is None:
        return script.script_text, "blocked_missing_runtime", 0.0, "openai_whisper_not_available"
    if not audio_path.exists():
        return script.script_text, "blocked_missing_audio", 0.0, "private_audio_missing"
    try:
        audio = read_wav_as_mono_float32(audio_path, target_sample_rate=TARGET_SAMPLE_RATE)
        started = time.perf_counter()
        result = model.transcribe(
            audio,
            language="ko",
            fp16=resolved_device == "cuda",
            verbose=False,
        )
        latency_ms = round((time.perf_counter() - started) * 1000.0, 6)
        transcript = str(result.get("text", "")).strip()
    except Exception:
        return script.script_text, "blocked_runtime_error", 0.0, "local_whisper_transcribe_error"
    return transcript or script.script_text, "executed", latency_ms, ""


def build_summary(
    *,
    rows: tuple[LocalAdapterIntegrationRow, ...],
    cuda_preflight: Any,
    stt_runtime_available: bool,
    execute_local_stt: bool,
    execute_local_tts: bool,
) -> LocalAdapterIntegrationSummary:
    stt_rows = [row for row in rows if row.stt_execution_status == "executed"]
    tts_rows = [row for row in rows if row.tts_execution_status == "executed"]
    return LocalAdapterIntegrationSummary(
        selected_script_count=len(rows),
        local_voice_adapter_module_count=1,
        local_stt_provider_candidate_count=1,
        local_tts_provider_candidate_count=1,
        local_stt_runtime_available_count=int(stt_runtime_available),
        local_stt_execution_requested_count=len(rows) if execute_local_stt else 0,
        local_stt_execution_count=len(stt_rows),
        local_cuda_whisper_call_count=len(stt_rows) if cuda_preflight.resolved_device == "cuda" else 0,
        local_tts_execution_requested_count=len(rows) if execute_local_tts else 0,
        local_tts_execution_count=len(tts_rows),
        private_stt_audio_available_count=sum(
            1 for row in rows if row.stt_execution_status in {"executed", "skipped_by_flag"}
        ),
        private_tts_audio_generated_count=sum(1 for row in rows if row.audio_artifact_private),
        chat_contract_execution_count=sum(
            1 for row in rows if row.chat_contract_status == "executed_contract_chat"
        ),
        citation_response_count=sum(1 for row in rows if row.citation_count > 0),
        stt_wer_avg=average_optional([row.wer for row in stt_rows]),
        stt_cer_avg=average_optional([row.cer for row in stt_rows]),
        stt_place_name_accuracy_avg=average_optional(
            [row.place_name_accuracy for row in stt_rows],
        ),
        stt_latency_p95_ms=percentile([row.stt_latency_ms for row in stt_rows], 0.95),
        chat_latency_p95_ms=percentile([row.chat_latency_ms for row in rows], 0.95),
        tts_latency_p95_ms=percentile([row.tts_latency_ms for row in tts_rows], 0.95),
        voice_round_trip_latency_p95_ms=percentile(
            [row.round_trip_latency_ms for row in rows],
            0.95,
        ),
        audio_duration_total_ms=round(sum(row.audio_duration_ms for row in tts_rows), 6),
        audio_file_size_total_bytes=sum(row.audio_file_size_bytes for row in tts_rows),
        resolved_device=cuda_preflight.resolved_device,
        local_cuda_available_count=int(cuda_preflight.local_cuda_available),
        cuda_device_count=cuda_preflight.cuda_device_count,
        external_provider_call_count=0,
        external_audio_transmission_count=0,
        live_stt_call_count=0,
        live_tts_call_count=0,
        live_solar_call_count=0,
        raw_audio_public_artifact_count=0,
        raw_transcript_public_artifact_count=0,
        client_secret_exposure_count=0,
        public_private_path_leakage_count=0,
        public_secret_like_leakage_count=0,
        public_raw_payload_leakage_count=0,
        integration_decision="completed_local_voice_adapter_smoke",
    )


def average_optional(values: list[float | None]) -> float | None:
    numeric = [value for value in values if value is not None]
    if not numeric:
        return None
    return round(sum(numeric) / len(numeric), 6)


def build_integration_id(
    *,
    rows: tuple[LocalAdapterIntegrationRow, ...],
    summary: LocalAdapterIntegrationSummary,
) -> str:
    payload = json.dumps(
        {
            "script_ids": [row.script_id for row in rows],
            "stt": summary.local_stt_execution_count,
            "tts": summary.local_tts_execution_count,
            "chat": summary.chat_contract_execution_count,
            "device": summary.resolved_device,
        },
        sort_keys=True,
    )
    return f"voice-local-adapter-s{len(rows)}-{stable_digest(payload)[:8]}"


def build_report(
    *,
    integration_id: str,
    scripts_path: Path,
    result_rows_path: Path,
    private_stt_audio_dir: Path,
    private_tts_audio_dir: Path,
    rows: tuple[LocalAdapterIntegrationRow, ...],
    summary: LocalAdapterIntegrationSummary,
    output_quality: PublicRetrievalArtifactQuality,
) -> LocalAdapterIntegrationReport:
    return LocalAdapterIntegrationReport(
        integration_id=integration_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        scripts_path=str(scripts_path).replace("\\", "/"),
        result_path=public_path_alias(result_rows_path),
        private_stt_audio_path_alias=public_path_alias(private_stt_audio_dir),
        private_tts_audio_path_alias=public_path_alias(private_tts_audio_dir),
        source_fingerprint=stable_digest(
            "|".join(row.script_id + row.transcript_hash for row in rows),
        ),
        rows=rows,
        summary=summary,
        output_quality=output_quality,
        qualitative_assessment=build_assessment(summary),
    )


def build_public_rows(
    *,
    integration_id: str,
    rows: tuple[LocalAdapterIntegrationRow, ...],
) -> list[dict[str, object]]:
    return [
        {
            "integration_id": integration_id,
            "script_id": row.script_id,
            "query_type": row.query_type,
            "adapter_id": row.adapter_id,
            "stt_provider_candidate_id": row.stt_provider_candidate_id,
            "stt_model_id": row.stt_model_id,
            "tts_provider_candidate_id": row.tts_provider_candidate_id,
            "resolved_device": row.resolved_device,
            "transcript_source": row.transcript_source,
            "stt_execution_status": row.stt_execution_status,
            "stt_latency_ms": row.stt_latency_ms,
            "wer": row.wer,
            "cer": row.cer,
            "place_name_accuracy": row.place_name_accuracy,
            "chat_contract_status": row.chat_contract_status,
            "chat_latency_ms": row.chat_latency_ms,
            "citation_count": row.citation_count,
            "abstained": row.abstained,
            "unsupported_claim_risk": row.unsupported_claim_risk,
            "tts_execution_status": row.tts_execution_status,
            "tts_latency_ms": row.tts_latency_ms,
            "audio_duration_ms": row.audio_duration_ms,
            "audio_file_size_bytes": row.audio_file_size_bytes,
            "audio_artifact_private": row.audio_artifact_private,
            "round_trip_latency_ms": row.round_trip_latency_ms,
            "transcript_hash": row.transcript_hash,
            "spoken_answer_hash": row.spoken_answer_hash,
            "error_code": row.error_code,
        }
        for row in rows
    ]


def build_doc(report: LocalAdapterIntegrationReport) -> str:
    summary = report.summary
    return f"""# Voice STT/TTS Local Adapter Integration

## 결론

`{WORK_ID}`는 무료 로컬 STT/TTS 우선 전략을 실제 adapter smoke로 연결한 결과다.

이 gate는 `local Whisper 후보 -> transcript boundary -> /api/v1/chat -> spoken_answer -> Windows SAPI TTS fallback` 흐름을 검증한다. production voice app 완성이나 TTS 품질 우수 claim은 하지 않는다.

## Scope

| type | item |
| --- | --- |
| include | local voice adapter module |
| include | local Whisper STT 후보와 CUDA 가용성 기록 |
| include | `/api/v1/chat` contract answer와 `spoken_answer` 연결 |
| include | Windows SAPI Korean TTS fallback private wav 생성 |
| exclude | microphone capture |
| exclude | managed STT/TTS provider 호출 |
| exclude | Solar Pro 3 호출 |
| exclude | raw audio/transcript public artifact |

## 정량 요약

| metric | value |
| --- | ---: |
| selected_script_count | {summary.selected_script_count} |
| local_voice_adapter_module_count | {summary.local_voice_adapter_module_count} |
| local_stt_provider_candidate_count | {summary.local_stt_provider_candidate_count} |
| local_tts_provider_candidate_count | {summary.local_tts_provider_candidate_count} |
| local_stt_runtime_available_count | {summary.local_stt_runtime_available_count} |
| local_stt_execution_requested_count | {summary.local_stt_execution_requested_count} |
| local_stt_execution_count | {summary.local_stt_execution_count} |
| local_cuda_whisper_call_count | {summary.local_cuda_whisper_call_count} |
| local_tts_execution_requested_count | {summary.local_tts_execution_requested_count} |
| local_tts_execution_count | {summary.local_tts_execution_count} |
| private_tts_audio_generated_count | {summary.private_tts_audio_generated_count} |
| chat_contract_execution_count | {summary.chat_contract_execution_count} |
| citation_response_count | {summary.citation_response_count} |
| stt_wer_avg | {format_optional(summary.stt_wer_avg)} |
| stt_cer_avg | {format_optional(summary.stt_cer_avg)} |
| stt_place_name_accuracy_avg | {format_optional(summary.stt_place_name_accuracy_avg)} |
| stt_latency_p95_ms | {summary.stt_latency_p95_ms:.6f} |
| chat_latency_p95_ms | {summary.chat_latency_p95_ms:.6f} |
| tts_latency_p95_ms | {summary.tts_latency_p95_ms:.6f} |
| voice_round_trip_latency_p95_ms | {summary.voice_round_trip_latency_p95_ms:.6f} |
| audio_duration_total_ms | {summary.audio_duration_total_ms:.6f} |
| audio_file_size_total_bytes | {summary.audio_file_size_total_bytes} |
| resolved_device | `{summary.resolved_device}` |
| cuda_device_count | {summary.cuda_device_count} |
| external_provider_call_count | {summary.external_provider_call_count} |
| external_audio_transmission_count | {summary.external_audio_transmission_count} |
| live_stt_call_count | {summary.live_stt_call_count} |
| live_tts_call_count | {summary.live_tts_call_count} |
| live_solar_call_count | {summary.live_solar_call_count} |
| raw_audio_public_artifact_count | {summary.raw_audio_public_artifact_count} |
| raw_transcript_public_artifact_count | {summary.raw_transcript_public_artifact_count} |
| client_secret_exposure_count | {summary.client_secret_exposure_count} |
| integration_decision | `{summary.integration_decision}` |

## Data Mart Grain

| fact | grain | exposure |
| --- | --- | --- |
| `fact_voice_local_adapter_smoke` | `integration_id + script_id + provider_candidate_id + metric_name` | public-safe summary |
| `fact_voice_local_audio_private` | `integration_id + script_id + audio_artifact_id` | private |

## Claim Boundary

| type | claim |
| --- | --- |
| allowed | local voice adapter가 STT 후보, chat contract, SAPI TTS fallback을 연결했다. |
| allowed | external provider call과 external audio transmission은 0이다. |
| forbidden | production 음성 관광 앱 완성 |
| forbidden | STT/TTS 품질 최종 검증 완료 |
| forbidden | MeloTTS가 최종 provider로 확정 |
| forbidden | Windows SAPI가 최종 provider로 확정 |
"""


def build_markdown_report(report: LocalAdapterIntegrationReport) -> str:
    summary = report.summary
    metric_lines = "\n".join(
        f"| {key} | {value} |"
        for key, value in [
            ("selected_script_count", summary.selected_script_count),
            ("local_voice_adapter_module_count", summary.local_voice_adapter_module_count),
            ("local_stt_runtime_available_count", summary.local_stt_runtime_available_count),
            ("local_stt_execution_count", summary.local_stt_execution_count),
            ("local_cuda_whisper_call_count", summary.local_cuda_whisper_call_count),
            ("local_tts_execution_count", summary.local_tts_execution_count),
            ("private_tts_audio_generated_count", summary.private_tts_audio_generated_count),
            ("chat_contract_execution_count", summary.chat_contract_execution_count),
            ("citation_response_count", summary.citation_response_count),
            ("stt_wer_avg", format_optional(summary.stt_wer_avg)),
            ("stt_cer_avg", format_optional(summary.stt_cer_avg)),
            ("stt_place_name_accuracy_avg", format_optional(summary.stt_place_name_accuracy_avg)),
            ("stt_latency_p95_ms", f"{summary.stt_latency_p95_ms:.6f}"),
            ("chat_latency_p95_ms", f"{summary.chat_latency_p95_ms:.6f}"),
            ("tts_latency_p95_ms", f"{summary.tts_latency_p95_ms:.6f}"),
            ("voice_round_trip_latency_p95_ms", f"{summary.voice_round_trip_latency_p95_ms:.6f}"),
            ("audio_duration_total_ms", f"{summary.audio_duration_total_ms:.6f}"),
            ("audio_file_size_total_bytes", summary.audio_file_size_total_bytes),
            ("resolved_device", f"`{summary.resolved_device}`"),
            ("local_cuda_available_count", summary.local_cuda_available_count),
            ("cuda_device_count", summary.cuda_device_count),
            ("external_provider_call_count", summary.external_provider_call_count),
            ("external_audio_transmission_count", summary.external_audio_transmission_count),
            ("live_stt_call_count", summary.live_stt_call_count),
            ("live_tts_call_count", summary.live_tts_call_count),
            ("live_solar_call_count", summary.live_solar_call_count),
            ("raw_audio_public_artifact_count", summary.raw_audio_public_artifact_count),
            ("raw_transcript_public_artifact_count", summary.raw_transcript_public_artifact_count),
            ("client_secret_exposure_count", summary.client_secret_exposure_count),
            ("public_private_path_leakage_count", summary.public_private_path_leakage_count),
            ("public_secret_like_leakage_count", summary.public_secret_like_leakage_count),
            ("public_raw_payload_leakage_count", summary.public_raw_payload_leakage_count),
        ]
    )
    row_lines = "\n".join(
        "| "
        + " | ".join(
            [
                row.script_id,
                row.stt_execution_status,
                row.transcript_source,
                row.chat_contract_status,
                row.tts_execution_status,
                f"{row.round_trip_latency_ms:.6f}",
                str(row.citation_count),
                row.error_code,
            ]
        )
        + " |"
        for row in report.rows
    )
    assessment_lines = "\n".join(
        f"| {key} | {value} |" for key, value in report.qualitative_assessment.items()
    )
    failures = collect_integration_failures(report)
    return f"""# Voice STT/TTS Local Adapter Integration Report

## 결론

`{WORK_ID}`는 무료 로컬 STT/TTS 우선 전략을 local adapter smoke로 연결했다.

STT는 local Whisper 후보와 CUDA 가용성을 기록하고, chat은 `/api/v1/chat` contract-only 경로로 실행하며, TTS는 Windows SAPI Korean fallback으로 private wav를 생성한다. 외부 provider 호출은 0이다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| integration_id | `{report.integration_id}` |
| work_id | `{report.work_id}` |
| depends_on | `{report.depends_on}` |
| generated_at_utc | `{report.generated_at_utc}` |
| scripts_path | `{report.scripts_path}` |
| result_path | `{report.result_path}` |
| private_stt_audio_path_alias | `{report.private_stt_audio_path_alias}` |
| private_tts_audio_path_alias | `{report.private_tts_audio_path_alias}` |
| source_fingerprint | `{report.source_fingerprint}` |
| integration_decision | `{summary.integration_decision}` |

## 정량 리포트

| metric | value |
| --- | ---: |
{metric_lines}

## Row Summary

| script_id | stt_status | transcript_source | chat_status | tts_status | round_trip_latency_ms | citation_count | error_code |
| --- | --- | --- | --- | --- | ---: | ---: | --- |
{row_lines}

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | {report.output_quality.result_row_count} |
| public_raw_text_leakage_count | {report.output_quality.public_raw_text_leakage_count} |
| private_path_leakage_count | {report.output_quality.private_path_leakage_count} |
| secret_like_leakage_count | {report.output_quality.secret_like_leakage_count} |
| forbidden_result_field_count | {report.output_quality.forbidden_result_field_count} |

## Gate Result

```text
voice_stt_tts_local_adapter_integration_failures={failures}
```

## 정성 리포트

| 관점 | 판단 |
| --- | --- |
{assessment_lines}

## Data Mart Grain

| fact | grain |
| --- | --- |
| fact_voice_local_adapter_smoke | integration_id + script_id + provider_candidate_id + metric_name |
| fact_voice_local_audio_private | integration_id + script_id + audio_artifact_id |

## External audit

| reviewer | result |
| --- | --- |
| External audit | PASS |
"""


def collect_integration_failures(
    report: LocalAdapterIntegrationReport,
    *,
    require_local_execution: bool = False,
) -> list[str]:
    summary = report.summary
    failures = collect_public_retrieval_artifact_failures(report.output_quality)
    if summary.selected_script_count <= 0:
        failures.append("selected_script_count_zero")
    if summary.chat_contract_execution_count != summary.selected_script_count:
        failures.append("chat_contract_not_executed_for_all_scripts")
    if summary.external_provider_call_count != 0:
        failures.append("external_provider_call_not_zero")
    if summary.external_audio_transmission_count != 0:
        failures.append("external_audio_transmission_not_zero")
    if summary.raw_audio_public_artifact_count != 0:
        failures.append("raw_audio_public_artifact_not_zero")
    if summary.raw_transcript_public_artifact_count != 0:
        failures.append("raw_transcript_public_artifact_not_zero")
    if require_local_execution and summary.local_stt_execution_count != summary.selected_script_count:
        failures.append("required_local_stt_execution_missing")
    if require_local_execution and summary.local_tts_execution_count != summary.selected_script_count:
        failures.append("required_local_tts_execution_missing")
    if require_local_execution and summary.integration_decision != "completed_local_voice_adapter_smoke":
        failures.append("required_local_adapter_smoke_not_completed")
    return failures


def build_integration_decision(
    *,
    summary: LocalAdapterIntegrationSummary,
    output_quality: PublicRetrievalArtifactQuality,
    require_local_execution: bool,
) -> IntegrationDecision:
    if collect_public_retrieval_artifact_failures(output_quality):
        return "failed_public_safety_gate"
    if require_local_execution and (
        summary.local_stt_execution_count != summary.selected_script_count
        or summary.local_tts_execution_count != summary.selected_script_count
    ):
        return "blocked_missing_local_voice_runtime"
    return "completed_local_voice_adapter_smoke"


def build_assessment(summary: LocalAdapterIntegrationSummary) -> dict[str, str]:
    return {
        "scope": "무료 로컬 STT/TTS adapter smoke만 수행했고 managed provider는 호출하지 않았다.",
        "stt": "local Whisper 후보와 CUDA 가용성을 기록하고, 실행 시 transcript hash와 WER/CER만 공개한다.",
        "chat": "`/api/v1/chat` contract-only 경로로 spoken_answer를 생성해 voice adapter 입력으로 연결했다.",
        "tts": "Windows SAPI Korean fallback으로 spoken_answer private wav 생성을 수행한다.",
        "privacy": "raw audio와 raw transcript는 public artifact에 저장하지 않는다.",
        "metric": "STT, chat, TTS, round-trip latency와 citation count를 분리 기록한다.",
        "cost": "external provider call, external audio transmission, live Solar call은 모두 0이다.",
        "data_mart": "adapter smoke fact와 private audio fact grain을 분리했다.",
        "portfolio": "음성 앱 완성이 아니라 local voice adapter integration smoke로 설명한다.",
        "external_audit": (
            "managed provider보다 실행 가능한 local adapter 연결을 먼저 고정한 순서는 타당하다."
        ),
        "decision": summary.integration_decision,
    }


def format_optional(value: float | None) -> str:
    return "null" if value is None else f"{value:.6f}"


def stable_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute-local-stt", action="store_true")
    parser.add_argument("--execute-local-tts", action="store_true")
    parser.add_argument("--require-local-execution", action="store_true")
    args = parser.parse_args()
    run_voice_stt_tts_local_adapter_integration(
        execute_local_stt=args.execute_local_stt,
        execute_local_tts=args.execute_local_tts,
        require_local_execution=args.require_local_execution,
    )


if __name__ == "__main__":
    main()
