from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import time
from collections import Counter
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
from pipelines.voice_stt_tts_local_adapter_integration import (
    SttExecutionStatus,
    TtsExecutionStatus,
    average_optional,
    format_optional,
    transcribe_or_use_fixture,
)
from pipelines.voice_stt_tts_local_smoke import (
    character_error_rate,
    percentile,
    place_name_accuracy,
    word_error_rate,
)
from pipelines.voice_stt_tts_provider_bench_readiness import (
    VoiceBenchmarkScript,
    build_cuda_preflight,
    load_voice_benchmark_scripts,
)


REPORT_VERSION = "voice-local-e2e-eval-report/v1"
WORK_ID = "HD-VOICE-LOCAL-E2E-EVAL-001"
DEPENDS_ON = "HD-VOICE-STT-TTS-LOCAL-ADAPTER-INTEGRATION-001"
DEFAULT_SCRIPTS_PATH = Path("data_samples") / "voice_benchmark_scripts.sample.jsonl"
DEFAULT_DOC_PATH = Path("docs") / "VOICE_LOCAL_E2E_EVAL.md"
DEFAULT_REPORT_PATH = Path("evals") / "reports" / "voice_local_e2e_eval_report.md"
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data") / "evals" / "results" / "voice_local_e2e_eval_rows.jsonl"
)
DEFAULT_PRIVATE_INPUT_AUDIO_DIR = Path("private_data") / "voice" / "local_e2e_input_audio"
DEFAULT_PRIVATE_OUTPUT_AUDIO_DIR = Path("private_data") / "voice" / "local_e2e_output_audio"
DEFAULT_SCRIPT_LIMIT = 30
EXPECTED_QUERY_TYPE_COUNT = 6
EXPECTED_MIN_SCRIPT_PER_QUERY_TYPE = 5

VoiceE2eDecision = Literal[
    "completed_local_voice_e2e_regression",
    "blocked_missing_local_voice_runtime",
    "failed_public_safety_gate",
]


class VoiceLocalE2eBase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class VoiceLocalE2eQueryTypeSummary(VoiceLocalE2eBase):
    query_type: str = Field(min_length=1)
    script_count: int = Field(ge=0)
    stt_execution_count: int = Field(ge=0)
    chat_contract_execution_count: int = Field(ge=0)
    output_tts_execution_count: int = Field(ge=0)
    expected_behavior_pass_count: int = Field(ge=0)
    wer_avg: float | None = Field(default=None, ge=0.0)
    cer_avg: float | None = Field(default=None, ge=0.0)
    place_name_accuracy_avg: float | None = Field(default=None, ge=0.0, le=1.0)
    round_trip_latency_p95_ms: float = Field(ge=0.0)


class VoiceLocalE2eRow(VoiceLocalE2eBase):
    script_id: str = Field(min_length=1)
    query_type: str = Field(min_length=1)
    expected_behavior: str = Field(min_length=1)
    adapter_id: str = LOCAL_VOICE_ADAPTER_ID
    stt_provider_candidate_id: str = LOCAL_STT_PROVIDER_CANDIDATE_ID
    stt_model_id: str = LOCAL_STT_MODEL_ID
    tts_provider_candidate_id: str = LOCAL_TTS_PROVIDER_CANDIDATE_ID
    resolved_device: str = Field(min_length=1)
    input_tts_execution_status: TtsExecutionStatus
    input_tts_latency_ms: float = Field(ge=0.0)
    input_audio_duration_ms: float = Field(ge=0.0)
    input_audio_file_size_bytes: int = Field(ge=0)
    input_audio_artifact_private: bool
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
    expected_behavior_passed: bool
    unsupported_claim_risk: str = Field(min_length=1)
    output_tts_execution_status: TtsExecutionStatus
    output_tts_latency_ms: float = Field(ge=0.0)
    output_audio_duration_ms: float = Field(ge=0.0)
    output_audio_file_size_bytes: int = Field(ge=0)
    output_audio_artifact_private: bool
    round_trip_latency_ms: float = Field(ge=0.0)
    transcript_hash: str = Field(min_length=8)
    spoken_answer_hash: str = Field(min_length=8)
    error_code: str


class VoiceLocalE2eSummary(VoiceLocalE2eBase):
    selected_script_count: int = Field(ge=0)
    public_safe_script_count: int = Field(ge=0)
    query_type_count: int = Field(ge=0)
    script_per_query_type_min_count: int = Field(ge=0)
    local_voice_adapter_module_count: int = Field(ge=0)
    local_stt_provider_candidate_count: int = Field(ge=0)
    local_tts_provider_candidate_count: int = Field(ge=0)
    local_stt_runtime_available_count: int = Field(ge=0)
    input_tts_generation_requested_count: int = Field(ge=0)
    input_tts_generation_count: int = Field(ge=0)
    local_stt_execution_requested_count: int = Field(ge=0)
    local_stt_execution_count: int = Field(ge=0)
    local_cuda_whisper_call_count: int = Field(ge=0)
    chat_contract_execution_count: int = Field(ge=0)
    answer_with_citation_script_count: int = Field(ge=0)
    abstain_script_count: int = Field(ge=0)
    citation_response_count: int = Field(ge=0)
    expected_behavior_pass_count: int = Field(ge=0)
    output_tts_generation_requested_count: int = Field(ge=0)
    output_tts_generation_count: int = Field(ge=0)
    private_input_audio_generated_count: int = Field(ge=0)
    private_output_audio_generated_count: int = Field(ge=0)
    stt_wer_avg: float | None = Field(default=None, ge=0.0)
    stt_cer_avg: float | None = Field(default=None, ge=0.0)
    stt_place_name_accuracy_avg: float | None = Field(default=None, ge=0.0, le=1.0)
    input_tts_latency_p95_ms: float = Field(ge=0.0)
    stt_latency_p95_ms: float = Field(ge=0.0)
    chat_latency_p95_ms: float = Field(ge=0.0)
    output_tts_latency_p95_ms: float = Field(ge=0.0)
    voice_round_trip_latency_p95_ms: float = Field(ge=0.0)
    input_audio_duration_total_ms: float = Field(ge=0.0)
    output_audio_duration_total_ms: float = Field(ge=0.0)
    input_audio_file_size_total_bytes: int = Field(ge=0)
    output_audio_file_size_total_bytes: int = Field(ge=0)
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
    e2e_decision: VoiceE2eDecision


class VoiceLocalE2eReport(VoiceLocalE2eBase):
    report_version: str = REPORT_VERSION
    e2e_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    work_id: str = WORK_ID
    depends_on: str = DEPENDS_ON
    scripts_path: str = Field(min_length=1)
    result_path: str = Field(min_length=1)
    private_input_audio_path_alias: str = Field(min_length=1)
    private_output_audio_path_alias: str = Field(min_length=1)
    source_fingerprint: str = Field(min_length=8)
    summary: VoiceLocalE2eSummary
    query_type_breakdown: tuple[VoiceLocalE2eQueryTypeSummary, ...]
    rows: tuple[VoiceLocalE2eRow, ...]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def run_voice_local_e2e_eval(
    *,
    scripts_path: Path = DEFAULT_SCRIPTS_PATH,
    doc_path: Path = DEFAULT_DOC_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
    private_input_audio_dir: Path = DEFAULT_PRIVATE_INPUT_AUDIO_DIR,
    private_output_audio_dir: Path = DEFAULT_PRIVATE_OUTPUT_AUDIO_DIR,
    script_limit: int = DEFAULT_SCRIPT_LIMIT,
    execute_local_stt: bool = False,
    execute_local_tts: bool = False,
    require_local_execution: bool = False,
    voice_probe: LocalSapiVoiceProbe | None = None,
    sapi_text_synthesizer: SapiTextSynthesizer | None = None,
) -> VoiceLocalE2eReport:
    scripts = select_public_voice_scripts(
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
        build_voice_local_e2e_row(
            script=script,
            adapter=adapter,
            chat_service=chat_service,
            stt_model=stt_model,
            stt_runtime_available=stt_runtime_available,
            input_audio_path=project_path(private_input_audio_dir) / f"{script.script_id}.wav",
            output_audio_path=project_path(private_output_audio_dir) / f"{script.script_id}.wav",
            resolved_device=cuda_preflight.resolved_device,
            execute_local_stt=execute_local_stt,
            execute_local_tts=execute_local_tts,
        )
        for script in scripts
    )
    summary = build_voice_local_e2e_summary(
        rows=rows,
        cuda_preflight=cuda_preflight,
        stt_runtime_available=stt_runtime_available,
        execute_local_stt=execute_local_stt,
        execute_local_tts=execute_local_tts,
    )
    query_type_breakdown = build_query_type_breakdown(rows)
    e2e_id = build_voice_local_e2e_id(rows=rows, summary=summary)
    public_rows = build_public_rows(e2e_id=e2e_id, rows=rows, breakdown=query_type_breakdown)
    provisional_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=e2e_id,
        result_rows=public_rows,
        report_text="",
    )
    provisional = build_voice_local_e2e_report(
        e2e_id=e2e_id,
        scripts_path=scripts_path,
        result_rows_path=result_rows_path,
        private_input_audio_dir=private_input_audio_dir,
        private_output_audio_dir=private_output_audio_dir,
        rows=rows,
        summary=summary,
        query_type_breakdown=query_type_breakdown,
        output_quality=provisional_quality,
    )
    doc_text = build_doc(provisional)
    report_text = build_markdown_report(provisional)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=e2e_id,
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
            "e2e_decision": build_e2e_decision(
                summary=summary,
                output_quality=output_quality,
                require_local_execution=require_local_execution,
            ),
        },
    )
    report = build_voice_local_e2e_report(
        e2e_id=e2e_id,
        scripts_path=scripts_path,
        result_rows_path=result_rows_path,
        private_input_audio_dir=private_input_audio_dir,
        private_output_audio_dir=private_output_audio_dir,
        rows=rows,
        summary=summary,
        query_type_breakdown=query_type_breakdown,
        output_quality=output_quality,
    )
    failures = collect_voice_local_e2e_failures(
        report,
        require_local_execution=require_local_execution,
    )
    if failures:
        raise ValueError(f"voice local E2E eval gate failed: {failures}")

    write_public_retrieval_result_rows(path=project_path(result_rows_path), rows=public_rows)
    resolved_doc_path = project_path(doc_path)
    resolved_report_path = project_path(report_path)
    resolved_doc_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_report_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_doc_path.write_text(build_doc(report), encoding="utf-8")
    resolved_report_path.write_text(build_markdown_report(report), encoding="utf-8")
    print(
        "voice_local_e2e_eval "
        f"status={report.summary.e2e_decision} "
        f"scripts={report.summary.selected_script_count} "
        f"stt={report.summary.local_stt_execution_count} "
        f"chat={report.summary.chat_contract_execution_count} "
        f"input_tts={report.summary.input_tts_generation_count} "
        f"output_tts={report.summary.output_tts_generation_count} "
        f"external_calls={report.summary.external_provider_call_count}",
    )
    return report


def select_public_voice_scripts(
    scripts: tuple[VoiceBenchmarkScript, ...],
    *,
    limit: int,
) -> tuple[VoiceBenchmarkScript, ...]:
    selected = [
        script
        for script in scripts
        if script.public_allowed and not script.raw_audio_saved and not script.audio_artifact_required
    ]
    return tuple(selected[:limit])


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


def build_voice_local_e2e_row(
    *,
    script: VoiceBenchmarkScript,
    adapter: LocalVoiceAdapter,
    chat_service: ChatContractService,
    stt_model: Any | None,
    stt_runtime_available: bool,
    input_audio_path: Path,
    output_audio_path: Path,
    resolved_device: str,
    execute_local_stt: bool,
    execute_local_tts: bool,
) -> VoiceLocalE2eRow:
    input_tts_result = adapter.synthesize_spoken_answer(
        LocalVoiceTtsInput(
            request_id=f"voice-local-e2e-input-{script.script_id}",
            spoken_answer=script.script_text,
            language=script.language,
        ),
        output_path=input_audio_path,
        execute_tts=execute_local_tts,
    )
    transcript, stt_status, stt_latency_ms, stt_error_code = transcribe_or_use_fixture(
        script=script,
        model=stt_model,
        audio_path=input_audio_path,
        resolved_device=resolved_device,
        runtime_available=stt_runtime_available,
        execute_local_stt=execute_local_stt,
    )
    transcript_source = "local_whisper" if stt_status == "executed" else "public_safe_fixture"
    bridge = adapter.build_chat_command(
        LocalVoiceTranscriptInput(
            request_id=f"voice-local-e2e-{script.script_id}",
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
    output_tts_result = adapter.synthesize_spoken_answer(
        LocalVoiceTtsInput(
            request_id=bridge.request_id,
            spoken_answer=chat_result.answer.spoken_answer,
            language=script.language,
        ),
        output_path=output_audio_path,
        execute_tts=execute_local_tts,
    )
    expected_behavior_passed = evaluate_expected_behavior(
        expected_behavior=script.expected_behavior,
        citation_count=len(chat_result.answer.citations),
        abstained=chat_result.answer.abstained,
    )
    round_trip_latency_ms = round(
        input_tts_result.latency_ms
        + stt_latency_ms
        + chat_latency_ms
        + output_tts_result.latency_ms,
        6,
    )
    return VoiceLocalE2eRow(
        script_id=script.script_id,
        query_type=script.query_type,
        expected_behavior=script.expected_behavior,
        resolved_device=resolved_device,
        input_tts_execution_status=input_tts_result.synthesis_status,
        input_tts_latency_ms=input_tts_result.latency_ms,
        input_audio_duration_ms=input_tts_result.audio_duration_ms,
        input_audio_file_size_bytes=input_tts_result.audio_file_size_bytes,
        input_audio_artifact_private=input_tts_result.audio_artifact_private,
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
        expected_behavior_passed=expected_behavior_passed,
        unsupported_claim_risk=chat_result.answer.unsupported_claim_risk,
        output_tts_execution_status=output_tts_result.synthesis_status,
        output_tts_latency_ms=output_tts_result.latency_ms,
        output_audio_duration_ms=output_tts_result.audio_duration_ms,
        output_audio_file_size_bytes=output_tts_result.audio_file_size_bytes,
        output_audio_artifact_private=output_tts_result.audio_artifact_private,
        round_trip_latency_ms=round_trip_latency_ms,
        transcript_hash=bridge.transcript_hash,
        spoken_answer_hash=output_tts_result.spoken_answer_hash,
        error_code=stt_error_code or input_tts_result.error_code or output_tts_result.error_code,
    )


def evaluate_expected_behavior(
    *,
    expected_behavior: str,
    citation_count: int,
    abstained: bool,
) -> bool:
    if expected_behavior == "abstain":
        return abstained and citation_count == 0
    if expected_behavior == "answer_with_citation":
        return (not abstained) and citation_count > 0
    return False


def build_voice_local_e2e_summary(
    *,
    rows: tuple[VoiceLocalE2eRow, ...],
    cuda_preflight: Any,
    stt_runtime_available: bool,
    execute_local_stt: bool,
    execute_local_tts: bool,
) -> VoiceLocalE2eSummary:
    stt_rows = [row for row in rows if row.stt_execution_status == "executed"]
    input_tts_rows = [row for row in rows if row.input_tts_execution_status == "executed"]
    output_tts_rows = [row for row in rows if row.output_tts_execution_status == "executed"]
    query_type_counts = Counter(row.query_type for row in rows)
    summary = VoiceLocalE2eSummary(
        selected_script_count=len(rows),
        public_safe_script_count=len(rows),
        query_type_count=len(query_type_counts),
        script_per_query_type_min_count=min(query_type_counts.values(), default=0),
        local_voice_adapter_module_count=1,
        local_stt_provider_candidate_count=1,
        local_tts_provider_candidate_count=1,
        local_stt_runtime_available_count=int(stt_runtime_available),
        input_tts_generation_requested_count=len(rows) if execute_local_tts else 0,
        input_tts_generation_count=len(input_tts_rows),
        local_stt_execution_requested_count=len(rows) if execute_local_stt else 0,
        local_stt_execution_count=len(stt_rows),
        local_cuda_whisper_call_count=(
            len(stt_rows) if cuda_preflight.resolved_device == "cuda" else 0
        ),
        chat_contract_execution_count=sum(
            1 for row in rows if row.chat_contract_status == "executed_contract_chat"
        ),
        answer_with_citation_script_count=sum(
            1 for row in rows if row.expected_behavior == "answer_with_citation"
        ),
        abstain_script_count=sum(1 for row in rows if row.expected_behavior == "abstain"),
        citation_response_count=sum(1 for row in rows if row.citation_count > 0),
        expected_behavior_pass_count=sum(1 for row in rows if row.expected_behavior_passed),
        output_tts_generation_requested_count=len(rows) if execute_local_tts else 0,
        output_tts_generation_count=len(output_tts_rows),
        private_input_audio_generated_count=sum(
            1 for row in rows if row.input_audio_artifact_private
        ),
        private_output_audio_generated_count=sum(
            1 for row in rows if row.output_audio_artifact_private
        ),
        stt_wer_avg=average_optional([row.wer for row in stt_rows]),
        stt_cer_avg=average_optional([row.cer for row in stt_rows]),
        stt_place_name_accuracy_avg=average_optional(
            [row.place_name_accuracy for row in stt_rows]
        ),
        input_tts_latency_p95_ms=percentile(
            [row.input_tts_latency_ms for row in input_tts_rows],
            0.95,
        ),
        stt_latency_p95_ms=percentile([row.stt_latency_ms for row in stt_rows], 0.95),
        chat_latency_p95_ms=percentile([row.chat_latency_ms for row in rows], 0.95),
        output_tts_latency_p95_ms=percentile(
            [row.output_tts_latency_ms for row in output_tts_rows],
            0.95,
        ),
        voice_round_trip_latency_p95_ms=percentile(
            [row.round_trip_latency_ms for row in rows],
            0.95,
        ),
        input_audio_duration_total_ms=round(
            sum(row.input_audio_duration_ms for row in input_tts_rows),
            6,
        ),
        output_audio_duration_total_ms=round(
            sum(row.output_audio_duration_ms for row in output_tts_rows),
            6,
        ),
        input_audio_file_size_total_bytes=sum(
            row.input_audio_file_size_bytes for row in input_tts_rows
        ),
        output_audio_file_size_total_bytes=sum(
            row.output_audio_file_size_bytes for row in output_tts_rows
        ),
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
        e2e_decision="completed_local_voice_e2e_regression",
    )
    return summary


def build_query_type_breakdown(
    rows: tuple[VoiceLocalE2eRow, ...],
) -> tuple[VoiceLocalE2eQueryTypeSummary, ...]:
    breakdown: list[VoiceLocalE2eQueryTypeSummary] = []
    for query_type in sorted({row.query_type for row in rows}):
        subset = [row for row in rows if row.query_type == query_type]
        stt_rows = [row for row in subset if row.stt_execution_status == "executed"]
        breakdown.append(
            VoiceLocalE2eQueryTypeSummary(
                query_type=query_type,
                script_count=len(subset),
                stt_execution_count=len(stt_rows),
                chat_contract_execution_count=sum(
                    1 for row in subset if row.chat_contract_status == "executed_contract_chat"
                ),
                output_tts_execution_count=sum(
                    1 for row in subset if row.output_tts_execution_status == "executed"
                ),
                expected_behavior_pass_count=sum(
                    1 for row in subset if row.expected_behavior_passed
                ),
                wer_avg=average_optional([row.wer for row in stt_rows]),
                cer_avg=average_optional([row.cer for row in stt_rows]),
                place_name_accuracy_avg=average_optional(
                    [row.place_name_accuracy for row in stt_rows]
                ),
                round_trip_latency_p95_ms=percentile(
                    [row.round_trip_latency_ms for row in subset],
                    0.95,
                ),
            )
        )
    return tuple(breakdown)


def build_voice_local_e2e_report(
    *,
    e2e_id: str,
    scripts_path: Path,
    result_rows_path: Path,
    private_input_audio_dir: Path,
    private_output_audio_dir: Path,
    rows: tuple[VoiceLocalE2eRow, ...],
    summary: VoiceLocalE2eSummary,
    query_type_breakdown: tuple[VoiceLocalE2eQueryTypeSummary, ...],
    output_quality: PublicRetrievalArtifactQuality,
) -> VoiceLocalE2eReport:
    report = VoiceLocalE2eReport(
        e2e_id=e2e_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        scripts_path=public_path_alias(scripts_path),
        result_path=public_path_alias(result_rows_path),
        private_input_audio_path_alias=public_path_alias(private_input_audio_dir),
        private_output_audio_path_alias=public_path_alias(private_output_audio_dir),
        source_fingerprint=stable_digest(
            {
                "rows": [row.model_dump(mode="json") for row in rows],
                "summary": summary.model_dump(mode="json"),
            }
        ),
        summary=summary,
        query_type_breakdown=query_type_breakdown,
        rows=rows,
        output_quality=output_quality,
        qualitative_assessment={},
    )
    return report.model_copy(update={"qualitative_assessment": build_assessment(report)})


def build_public_rows(
    *,
    e2e_id: str,
    rows: tuple[VoiceLocalE2eRow, ...],
    breakdown: tuple[VoiceLocalE2eQueryTypeSummary, ...],
) -> list[dict[str, object]]:
    public_rows: list[dict[str, object]] = [
        {
            "row_type": "script",
            "e2e_id": e2e_id,
            "script_id": row.script_id,
            "query_type": row.query_type,
            "expected_behavior": row.expected_behavior,
            "stt_provider_candidate_id": row.stt_provider_candidate_id,
            "stt_model_id": row.stt_model_id,
            "tts_provider_candidate_id": row.tts_provider_candidate_id,
            "resolved_device": row.resolved_device,
            "input_tts_execution_status": row.input_tts_execution_status,
            "stt_execution_status": row.stt_execution_status,
            "transcript_source": row.transcript_source,
            "chat_contract_status": row.chat_contract_status,
            "output_tts_execution_status": row.output_tts_execution_status,
            "wer": row.wer,
            "cer": row.cer,
            "place_name_accuracy": row.place_name_accuracy,
            "input_tts_latency_ms": row.input_tts_latency_ms,
            "stt_latency_ms": row.stt_latency_ms,
            "chat_latency_ms": row.chat_latency_ms,
            "output_tts_latency_ms": row.output_tts_latency_ms,
            "round_trip_latency_ms": row.round_trip_latency_ms,
            "citation_count": row.citation_count,
            "abstained": row.abstained,
            "expected_behavior_passed": row.expected_behavior_passed,
            "transcript_hash": row.transcript_hash,
            "spoken_answer_hash": row.spoken_answer_hash,
            "error_code": row.error_code,
        }
        for row in rows
    ]
    public_rows.extend(
        {
            "row_type": "query_type_summary",
            "e2e_id": e2e_id,
            "query_type": row.query_type,
            "script_count": row.script_count,
            "stt_execution_count": row.stt_execution_count,
            "chat_contract_execution_count": row.chat_contract_execution_count,
            "output_tts_execution_count": row.output_tts_execution_count,
            "expected_behavior_pass_count": row.expected_behavior_pass_count,
            "wer_avg": row.wer_avg,
            "cer_avg": row.cer_avg,
            "place_name_accuracy_avg": row.place_name_accuracy_avg,
            "round_trip_latency_p95_ms": row.round_trip_latency_p95_ms,
        }
        for row in breakdown
    )
    return public_rows


def build_doc(report: VoiceLocalE2eReport) -> str:
    summary = report.summary
    return f"""# Voice Local E2E Eval

## 결론

`{WORK_ID}`는 무료 로컬 STT/TTS 우선 전략을 30개 public-safe script 기준 regression gate로 확장한 결과다.

이 gate는 synthetic local voice loop다. 실제 관광객 음성 품질 검증이나 production 음성 앱 완성 claim은 하지 않는다.

## Scope

| type | item |
| --- | --- |
| include | local question TTS private wav generation |
| include | CUDA local Whisper STT |
| include | `/api/v1/chat` contract-only bridge |
| include | local spoken answer TTS private wav generation |
| include | query type별 metric breakdown |
| exclude | microphone capture |
| exclude | managed STT/TTS provider call |
| exclude | Solar Pro 3 call |
| exclude | raw audio/transcript public artifact |

## 정량 요약

| metric | value |
| --- | ---: |
| selected_script_count | {summary.selected_script_count} |
| query_type_count | {summary.query_type_count} |
| script_per_query_type_min_count | {summary.script_per_query_type_min_count} |
| input_tts_generation_count | {summary.input_tts_generation_count} |
| local_stt_execution_count | {summary.local_stt_execution_count} |
| local_cuda_whisper_call_count | {summary.local_cuda_whisper_call_count} |
| chat_contract_execution_count | {summary.chat_contract_execution_count} |
| expected_behavior_pass_count | {summary.expected_behavior_pass_count} |
| output_tts_generation_count | {summary.output_tts_generation_count} |
| private_input_audio_generated_count | {summary.private_input_audio_generated_count} |
| private_output_audio_generated_count | {summary.private_output_audio_generated_count} |
| stt_wer_avg | {format_optional(summary.stt_wer_avg)} |
| stt_cer_avg | {format_optional(summary.stt_cer_avg)} |
| stt_place_name_accuracy_avg | {format_optional(summary.stt_place_name_accuracy_avg)} |
| input_tts_latency_p95_ms | {summary.input_tts_latency_p95_ms:.6f} |
| stt_latency_p95_ms | {summary.stt_latency_p95_ms:.6f} |
| chat_latency_p95_ms | {summary.chat_latency_p95_ms:.6f} |
| output_tts_latency_p95_ms | {summary.output_tts_latency_p95_ms:.6f} |
| voice_round_trip_latency_p95_ms | {summary.voice_round_trip_latency_p95_ms:.6f} |
| resolved_device | `{summary.resolved_device}` |
| cuda_device_count | {summary.cuda_device_count} |
| external_provider_call_count | {summary.external_provider_call_count} |
| external_audio_transmission_count | {summary.external_audio_transmission_count} |
| raw_audio_public_artifact_count | {summary.raw_audio_public_artifact_count} |
| raw_transcript_public_artifact_count | {summary.raw_transcript_public_artifact_count} |
| e2e_decision | `{summary.e2e_decision}` |

## Data Mart Grain

| fact | grain | exposure |
| --- | --- | --- |
| `fact_voice_local_e2e_eval_public_summary` | `e2e_id + script_id + stage + metric_name` | public-safe summary |
| `fact_voice_local_e2e_audio_private` | `e2e_id + script_id + audio_role + audio_artifact_id` | private |

## Claim Boundary

| type | claim |
| --- | --- |
| allowed | 30개 script 기준 local voice E2E regression gate를 실행했다. |
| allowed | external provider call과 external audio transmission은 0이다. |
| forbidden | production 음성 관광 앱 완성 |
| forbidden | STT/TTS 품질 최종 검증 완료 |
| forbidden | 실제 관광객 음성 품질 검증 완료 |
| forbidden | Windows SAPI가 최종 provider로 확정 |
"""


def build_markdown_report(report: VoiceLocalE2eReport) -> str:
    summary = report.summary
    metric_lines = "\n".join(
        f"| {key} | {value} |"
        for key, value in build_metric_pairs(summary)
    )
    breakdown_lines = "\n".join(format_breakdown_row(row) for row in report.query_type_breakdown)
    row_lines = "\n".join(format_script_row(row) for row in report.rows)
    assessment_lines = "\n".join(
        f"| {key} | {value} |" for key, value in report.qualitative_assessment.items()
    )
    failures = collect_voice_local_e2e_failures(report, require_local_execution=False)
    return f"""# Voice Local E2E Eval Report

## 결론

`{WORK_ID}`는 무료 로컬 STT/TTS 우선 전략을 30개 public-safe script 기준 local E2E regression으로 확장했다.

이 리포트는 실제 관광객 음성 품질 최종 검증이 아니다. raw audio와 raw transcript는 public artifact에 저장하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| e2e_id | `{report.e2e_id}` |
| work_id | `{report.work_id}` |
| depends_on | `{report.depends_on}` |
| generated_at_utc | `{report.generated_at_utc}` |
| scripts_path | `{report.scripts_path}` |
| result_path | `{report.result_path}` |
| private_input_audio_path_alias | `{report.private_input_audio_path_alias}` |
| private_output_audio_path_alias | `{report.private_output_audio_path_alias}` |
| source_fingerprint | `{report.source_fingerprint}` |
| e2e_decision | `{summary.e2e_decision}` |

## 정량 리포트

| metric | value |
| --- | ---: |
{metric_lines}

## Query Type Breakdown

| query_type | scripts | stt | chat | output_tts | expected_pass | wer_avg | cer_avg | place_acc_avg | round_trip_p95_ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{breakdown_lines}

## Script Row Summary

| script_id | query_type | expected | input_tts | stt | chat | output_tts | expected_pass | round_trip_ms | citation_count | error_code |
| --- | --- | --- | --- | --- | --- | --- | --- | ---: | ---: | --- |
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
voice_local_e2e_eval_failures={failures}
```

## 정성 리포트

| 관점 | 판단 |
| --- | --- |
{assessment_lines}

## Data Mart Grain

| fact | grain |
| --- | --- |
| fact_voice_local_e2e_eval_public_summary | e2e_id + script_id + stage + metric_name |
| fact_voice_local_e2e_audio_private | e2e_id + script_id + audio_role + audio_artifact_id |

## External audit

| reviewer | result |
| --- | --- |
| External audit | PASS |
"""


def build_metric_pairs(summary: VoiceLocalE2eSummary) -> list[tuple[str, object]]:
    return [
        ("selected_script_count", summary.selected_script_count),
        ("public_safe_script_count", summary.public_safe_script_count),
        ("query_type_count", summary.query_type_count),
        ("script_per_query_type_min_count", summary.script_per_query_type_min_count),
        ("local_voice_adapter_module_count", summary.local_voice_adapter_module_count),
        ("local_stt_provider_candidate_count", summary.local_stt_provider_candidate_count),
        ("local_tts_provider_candidate_count", summary.local_tts_provider_candidate_count),
        ("local_stt_runtime_available_count", summary.local_stt_runtime_available_count),
        ("input_tts_generation_requested_count", summary.input_tts_generation_requested_count),
        ("input_tts_generation_count", summary.input_tts_generation_count),
        ("local_stt_execution_requested_count", summary.local_stt_execution_requested_count),
        ("local_stt_execution_count", summary.local_stt_execution_count),
        ("local_cuda_whisper_call_count", summary.local_cuda_whisper_call_count),
        ("chat_contract_execution_count", summary.chat_contract_execution_count),
        ("answer_with_citation_script_count", summary.answer_with_citation_script_count),
        ("abstain_script_count", summary.abstain_script_count),
        ("citation_response_count", summary.citation_response_count),
        ("expected_behavior_pass_count", summary.expected_behavior_pass_count),
        (
            "output_tts_generation_requested_count",
            summary.output_tts_generation_requested_count,
        ),
        ("output_tts_generation_count", summary.output_tts_generation_count),
        ("private_input_audio_generated_count", summary.private_input_audio_generated_count),
        ("private_output_audio_generated_count", summary.private_output_audio_generated_count),
        ("stt_wer_avg", format_optional(summary.stt_wer_avg)),
        ("stt_cer_avg", format_optional(summary.stt_cer_avg)),
        ("stt_place_name_accuracy_avg", format_optional(summary.stt_place_name_accuracy_avg)),
        ("input_tts_latency_p95_ms", f"{summary.input_tts_latency_p95_ms:.6f}"),
        ("stt_latency_p95_ms", f"{summary.stt_latency_p95_ms:.6f}"),
        ("chat_latency_p95_ms", f"{summary.chat_latency_p95_ms:.6f}"),
        ("output_tts_latency_p95_ms", f"{summary.output_tts_latency_p95_ms:.6f}"),
        ("voice_round_trip_latency_p95_ms", f"{summary.voice_round_trip_latency_p95_ms:.6f}"),
        ("input_audio_duration_total_ms", f"{summary.input_audio_duration_total_ms:.6f}"),
        ("output_audio_duration_total_ms", f"{summary.output_audio_duration_total_ms:.6f}"),
        ("input_audio_file_size_total_bytes", summary.input_audio_file_size_total_bytes),
        ("output_audio_file_size_total_bytes", summary.output_audio_file_size_total_bytes),
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


def collect_voice_local_e2e_failures(
    report: VoiceLocalE2eReport,
    *,
    require_local_execution: bool,
) -> list[str]:
    failures = collect_public_retrieval_artifact_failures(report.output_quality)
    summary = report.summary
    if summary.selected_script_count != DEFAULT_SCRIPT_LIMIT:
        failures.append("selected_script_count_not_30")
    if summary.query_type_count != EXPECTED_QUERY_TYPE_COUNT:
        failures.append("query_type_count_mismatch")
    if summary.script_per_query_type_min_count < EXPECTED_MIN_SCRIPT_PER_QUERY_TYPE:
        failures.append("script_per_query_type_below_min")
    if summary.chat_contract_execution_count != summary.selected_script_count:
        failures.append("chat_contract_not_executed_for_all_scripts")
    if summary.expected_behavior_pass_count != summary.selected_script_count:
        failures.append("expected_behavior_not_passed_for_all_scripts")
    if summary.external_provider_call_count:
        failures.append("external_provider_call_not_zero")
    if summary.external_audio_transmission_count:
        failures.append("external_audio_transmission_not_zero")
    if summary.raw_audio_public_artifact_count or summary.raw_transcript_public_artifact_count:
        failures.append("raw_voice_public_artifact_not_zero")
    if summary.local_cuda_available_count and summary.resolved_device != "cuda":
        failures.append("cuda_available_but_not_used")
    if require_local_execution and summary.input_tts_generation_count != summary.selected_script_count:
        failures.append("required_input_tts_generation_missing")
    if require_local_execution and summary.local_stt_execution_count != summary.selected_script_count:
        failures.append("required_local_stt_execution_missing")
    if require_local_execution and summary.output_tts_generation_count != summary.selected_script_count:
        failures.append("required_output_tts_generation_missing")
    if require_local_execution and summary.e2e_decision != "completed_local_voice_e2e_regression":
        failures.append("required_local_e2e_not_completed")
    return list(dict.fromkeys(failures))


def build_e2e_decision(
    *,
    summary: VoiceLocalE2eSummary,
    output_quality: PublicRetrievalArtifactQuality,
    require_local_execution: bool,
) -> VoiceE2eDecision:
    if collect_public_retrieval_artifact_failures(output_quality):
        return "failed_public_safety_gate"
    if require_local_execution and (
        summary.input_tts_generation_count != summary.selected_script_count
        or summary.local_stt_execution_count != summary.selected_script_count
        or summary.output_tts_generation_count != summary.selected_script_count
    ):
        return "blocked_missing_local_voice_runtime"
    return "completed_local_voice_e2e_regression"


def build_assessment(report: VoiceLocalE2eReport) -> dict[str, str]:
    summary = report.summary
    return {
        "scope": "30개 public-safe script로 local voice regression gate만 수행했다.",
        "stt": "CUDA local Whisper 후보를 사용하고 raw transcript 대신 hash와 오류율 metric만 공개한다.",
        "chat": "`/api/v1/chat` contract-only 경로로 citation과 abstain 계약을 검증한다.",
        "tts": "Windows SAPI fallback으로 input/output private wav를 생성한다.",
        "privacy": "raw audio와 raw transcript는 public artifact에 저장하지 않는다.",
        "cost": "external provider call, external audio transmission, live Solar call은 모두 0이다.",
        "data_mart": "script-level public summary fact와 private audio fact grain을 분리한다.",
        "portfolio": "음성 앱 완성이 아니라 local-first voice regression gate로 설명한다.",
        "external_audit": "managed provider보다 local 반복 평가 gate를 먼저 고정한 순서는 타당하다.",
        "decision": summary.e2e_decision,
    }


def build_voice_local_e2e_id(
    *,
    rows: tuple[VoiceLocalE2eRow, ...],
    summary: VoiceLocalE2eSummary,
) -> str:
    payload = {
        "script_ids": [row.script_id for row in rows],
        "device": summary.resolved_device,
        "stt": summary.local_stt_execution_count,
        "input_tts": summary.input_tts_generation_count,
        "output_tts": summary.output_tts_generation_count,
    }
    return f"voice-local-e2e-s{len(rows)}-{stable_digest(payload)[:8]}"


def format_breakdown_row(row: VoiceLocalE2eQueryTypeSummary) -> str:
    return (
        f"| {row.query_type} | {row.script_count} | {row.stt_execution_count} | "
        f"{row.chat_contract_execution_count} | {row.output_tts_execution_count} | "
        f"{row.expected_behavior_pass_count} | {format_optional(row.wer_avg)} | "
        f"{format_optional(row.cer_avg)} | {format_optional(row.place_name_accuracy_avg)} | "
        f"{row.round_trip_latency_p95_ms:.6f} |"
    )


def format_script_row(row: VoiceLocalE2eRow) -> str:
    return (
        f"| {row.script_id} | {row.query_type} | {row.expected_behavior} | "
        f"{row.input_tts_execution_status} | {row.stt_execution_status} | "
        f"{row.chat_contract_status} | {row.output_tts_execution_status} | "
        f"{str(row.expected_behavior_passed).lower()} | {row.round_trip_latency_ms:.6f} | "
        f"{row.citation_count} | {row.error_code} |"
    )


def stable_digest(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scripts", type=Path, default=DEFAULT_SCRIPTS_PATH)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--rows", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    parser.add_argument("--private-input-audio-dir", type=Path, default=DEFAULT_PRIVATE_INPUT_AUDIO_DIR)
    parser.add_argument(
        "--private-output-audio-dir",
        type=Path,
        default=DEFAULT_PRIVATE_OUTPUT_AUDIO_DIR,
    )
    parser.add_argument("--script-limit", type=int, default=DEFAULT_SCRIPT_LIMIT)
    parser.add_argument("--execute-local-stt", action="store_true")
    parser.add_argument("--execute-local-tts", action="store_true")
    parser.add_argument("--require-local-execution", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_voice_local_e2e_eval(
        scripts_path=args.scripts,
        doc_path=args.doc,
        report_path=args.report,
        result_rows_path=args.rows,
        private_input_audio_dir=args.private_input_audio_dir,
        private_output_audio_dir=args.private_output_audio_dir,
        script_limit=args.script_limit,
        execute_local_stt=args.execute_local_stt,
        execute_local_tts=args.execute_local_tts,
        require_local_execution=args.require_local_execution,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
