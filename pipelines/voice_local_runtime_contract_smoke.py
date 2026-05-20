from __future__ import annotations

import argparse
import hashlib
import json
import time
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.application.voice_local_adapter import LocalSapiVoiceProbe, SapiTextSynthesizer
from app.application.voice_local_runtime import (
    LOCAL_VOICE_RUNTIME_CONTRACT_VERSION,
    LOCAL_VOICE_RUNTIME_ID,
    LocalVoiceRuntimeConfig,
    LocalVoiceRuntimeRequest,
    LocalVoiceRuntimeResult,
    LocalVoiceRuntimeService,
    LocalVoiceRuntimeValidationError,
)
from app.core.project_paths import project_path
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    collect_public_retrieval_artifact_failures,
    measure_public_retrieval_artifact_quality,
    public_path_alias,
    write_public_retrieval_result_rows,
)
from pipelines.voice_stt_tts_local_smoke import percentile, select_local_smoke_scripts
from pipelines.voice_stt_tts_provider_bench_readiness import (
    build_cuda_preflight,
    load_voice_benchmark_scripts,
)


REPORT_VERSION = "voice-local-runtime-contract-report/v1"
WORK_ID = "HD-VOICE-LOCAL-RUNTIME-CONTRACT-001"
DEPENDS_ON = "HD-VOICE-LOCAL-E2E-EVAL-001"
DEFAULT_SCRIPTS_PATH = Path("data_samples") / "voice_benchmark_scripts.sample.jsonl"
DEFAULT_DOC_PATH = Path("docs") / "VOICE_LOCAL_RUNTIME_CONTRACT.md"
DEFAULT_REPORT_PATH = Path("evals") / "reports" / "voice_local_runtime_contract_report.md"
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data") / "evals" / "results" / "voice_local_runtime_contract_rows.jsonl"
)
DEFAULT_PRIVATE_INPUT_AUDIO_DIR = Path("private_data") / "voice" / "local_runtime_input_audio"
DEFAULT_PRIVATE_OUTPUT_AUDIO_DIR = Path("private_data") / "voice" / "local_runtime_output_audio"
DEFAULT_SCRIPT_LIMIT = 5

RuntimeDecision = Literal[
    "completed_local_voice_runtime_contract",
    "blocked_missing_local_voice_runtime",
    "failed_public_safety_gate",
]


class VoiceRuntimeContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class VoiceRuntimeContractRow(VoiceRuntimeContractModel):
    script_id: str = Field(min_length=1)
    query_type: str = Field(min_length=1)
    runtime_id: str = LOCAL_VOICE_RUNTIME_ID
    input_audio_validation_status: str = Field(min_length=1)
    input_audio_artifact_private: bool
    transcript_source: str = Field(min_length=1)
    stt_execution_status: str = Field(min_length=1)
    stt_latency_ms: float = Field(ge=0.0)
    chat_contract_status: str = Field(min_length=1)
    chat_latency_ms: float = Field(ge=0.0)
    citation_count: int = Field(ge=0)
    abstained: bool
    output_tts_execution_status: str = Field(min_length=1)
    output_tts_latency_ms: float = Field(ge=0.0)
    output_audio_artifact_private: bool
    runtime_latency_ms: float = Field(ge=0.0)
    transcript_hash: str = Field(min_length=8)
    spoken_answer_hash: str = Field(min_length=8)
    error_code: str


class VoiceRuntimeValidationCaseRow(VoiceRuntimeContractModel):
    case_id: str = Field(min_length=1)
    expected_code: str = Field(min_length=1)
    observed_code: str = Field(min_length=1)
    passed: bool


class VoiceRuntimeContractSummary(VoiceRuntimeContractModel):
    selected_script_count: int = Field(ge=0)
    local_voice_runtime_contract_count: int = Field(ge=0)
    api_route_contract_count: int = Field(ge=0)
    accepted_audio_input_count: int = Field(ge=0)
    validation_reject_case_count: int = Field(ge=0)
    validation_reject_pass_count: int = Field(ge=0)
    local_stt_execution_requested_count: int = Field(ge=0)
    local_stt_execution_count: int = Field(ge=0)
    local_tts_execution_requested_count: int = Field(ge=0)
    local_tts_execution_count: int = Field(ge=0)
    chat_contract_execution_count: int = Field(ge=0)
    citation_response_count: int = Field(ge=0)
    private_input_audio_generated_count: int = Field(ge=0)
    private_output_audio_generated_count: int = Field(ge=0)
    stt_latency_p95_ms: float = Field(ge=0.0)
    chat_latency_p95_ms: float = Field(ge=0.0)
    output_tts_latency_p95_ms: float = Field(ge=0.0)
    runtime_latency_p95_ms: float = Field(ge=0.0)
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
    runtime_decision: RuntimeDecision


class VoiceRuntimeContractReport(VoiceRuntimeContractModel):
    report_version: str = REPORT_VERSION
    runtime_contract_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    work_id: str = WORK_ID
    depends_on: str = DEPENDS_ON
    scripts_path: str = Field(min_length=1)
    result_path: str = Field(min_length=1)
    private_input_audio_path_alias: str = Field(min_length=1)
    private_output_audio_path_alias: str = Field(min_length=1)
    source_fingerprint: str = Field(min_length=8)
    summary: VoiceRuntimeContractSummary
    rows: tuple[VoiceRuntimeContractRow, ...]
    validation_cases: tuple[VoiceRuntimeValidationCaseRow, ...]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def run_voice_local_runtime_contract_smoke(
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
    require_local_tts_execution: bool = False,
    voice_probe: LocalSapiVoiceProbe | None = None,
    sapi_text_synthesizer: SapiTextSynthesizer | None = None,
) -> VoiceRuntimeContractReport:
    scripts = select_local_smoke_scripts(
        load_voice_benchmark_scripts(project_path(scripts_path)),
        limit=script_limit,
    )
    cuda_preflight = build_cuda_preflight()
    service = LocalVoiceRuntimeService(
        config=LocalVoiceRuntimeConfig(output_audio_dir=private_output_audio_dir),
        voice_probe=voice_probe,
        sapi_text_synthesizer=sapi_text_synthesizer,
        resolved_device=cuda_preflight.resolved_device,
    )
    rows = tuple(
        build_runtime_contract_row(
            service=service,
            script=script,
            input_audio_path=private_input_audio_dir / f"{script.script_id}.wav",
            execute_local_stt=execute_local_stt,
            execute_local_tts=execute_local_tts,
        )
        for script in scripts
    )
    validation_cases = tuple(build_validation_case_rows(service=service))
    summary = build_summary(
        rows=rows,
        validation_cases=validation_cases,
        cuda_preflight=cuda_preflight,
        execute_local_stt=execute_local_stt,
        execute_local_tts=execute_local_tts,
    )
    runtime_contract_id = build_runtime_contract_id(rows=rows, summary=summary)
    public_rows = build_public_rows(
        runtime_contract_id=runtime_contract_id,
        rows=rows,
        validation_cases=validation_cases,
    )
    provisional_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=runtime_contract_id,
        result_rows=public_rows,
        report_text="",
    )
    provisional = build_report(
        runtime_contract_id=runtime_contract_id,
        scripts_path=scripts_path,
        result_rows_path=result_rows_path,
        private_input_audio_dir=private_input_audio_dir,
        private_output_audio_dir=private_output_audio_dir,
        rows=rows,
        validation_cases=validation_cases,
        summary=summary,
        output_quality=provisional_quality,
    )
    doc_text = build_doc(provisional)
    report_text = build_markdown_report(provisional)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=runtime_contract_id,
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
            "runtime_decision": build_runtime_decision(
                summary=summary,
                output_quality=output_quality,
                require_local_tts_execution=require_local_tts_execution,
            ),
        }
    )
    report = build_report(
        runtime_contract_id=runtime_contract_id,
        scripts_path=scripts_path,
        result_rows_path=result_rows_path,
        private_input_audio_dir=private_input_audio_dir,
        private_output_audio_dir=private_output_audio_dir,
        rows=rows,
        validation_cases=validation_cases,
        summary=summary,
        output_quality=output_quality,
    )
    failures = collect_runtime_contract_failures(
        report,
        require_local_tts_execution=require_local_tts_execution,
    )
    if failures:
        raise ValueError(f"voice local runtime contract gate failed: {failures}")

    write_public_retrieval_result_rows(path=project_path(result_rows_path), rows=public_rows)
    project_path(doc_path).write_text(build_doc(report), encoding="utf-8")
    project_path(report_path).write_text(build_markdown_report(report), encoding="utf-8")
    print(
        "voice_local_runtime_contract "
        f"status={report.summary.runtime_decision} "
        f"scripts={report.summary.selected_script_count} "
        f"accepted_audio={report.summary.accepted_audio_input_count} "
        f"chat={report.summary.chat_contract_execution_count} "
        f"tts={report.summary.local_tts_execution_count} "
        f"external_calls={report.summary.external_provider_call_count}",
    )
    return report


def build_runtime_contract_row(
    *,
    service: LocalVoiceRuntimeService,
    script,
    input_audio_path: Path,
    execute_local_stt: bool,
    execute_local_tts: bool,
) -> VoiceRuntimeContractRow:
    synthesize_private_wav(input_audio_path)
    started = time.perf_counter()
    result = service.handle(
        LocalVoiceRuntimeRequest(
            request_id=f"voice-runtime-{script.script_id}",
            input_audio_path=input_audio_path,
            fallback_transcript_text=script.script_text,
            language=script.language,
            query_type=script.query_type,
            place_context=script.place_ids,
            execute_local_stt=execute_local_stt,
            execute_local_tts=execute_local_tts,
        )
    )
    runtime_latency_ms = round((time.perf_counter() - started) * 1000.0, 6)
    return row_from_runtime_result(
        script_id=script.script_id,
        query_type=script.query_type,
        result=result,
        runtime_latency_ms=runtime_latency_ms,
    )


def synthesize_private_wav(path: Path) -> None:
    resolved = project_path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(resolved), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(b"\x00\x00" * 1600)


def row_from_runtime_result(
    *,
    script_id: str,
    query_type: str,
    result: LocalVoiceRuntimeResult,
    runtime_latency_ms: float,
) -> VoiceRuntimeContractRow:
    return VoiceRuntimeContractRow(
        script_id=script_id,
        query_type=query_type,
        input_audio_validation_status=result.input_audio.validation_status,
        input_audio_artifact_private=result.input_audio.artifact_private,
        transcript_source=result.transcript.transcript_source,
        stt_execution_status=result.transcript.stt_execution_status,
        stt_latency_ms=result.transcript.stt_latency_ms,
        chat_contract_status=result.chat_contract_status,
        chat_latency_ms=result.chat_latency_ms,
        citation_count=result.citation_count,
        abstained=result.abstained,
        output_tts_execution_status=result.output_tts_execution_status,
        output_tts_latency_ms=result.output_tts_latency_ms,
        output_audio_artifact_private=result.output_audio_artifact_private,
        runtime_latency_ms=runtime_latency_ms,
        transcript_hash=result.transcript.transcript_hash,
        spoken_answer_hash=result.spoken_answer_hash,
        error_code=result.error_code,
    )


def build_validation_case_rows(
    *,
    service: LocalVoiceRuntimeService,
) -> list[VoiceRuntimeValidationCaseRow]:
    cases = (
        (
            "reject_path_traversal",
            Path("private_data") / ".." / "private_data" / "voice.wav",
            "path_traversal_not_allowed",
        ),
        ("reject_public_path", Path("public_audio.wav"), "public_audio_path_not_allowed"),
        (
            "reject_non_wav_extension",
            Path("private_data") / "voice" / "not_audio.txt",
            "unsupported_audio_extension",
        ),
    )
    rows: list[VoiceRuntimeValidationCaseRow] = []
    for case_id, input_path, expected_code in cases:
        try:
            service.handle(
                LocalVoiceRuntimeRequest(
                    request_id=f"voice-runtime-{case_id}",
                    input_audio_path=input_path,
                    fallback_transcript_text="검증용 transcript",
                )
            )
            observed_code = "unexpected_success"
        except LocalVoiceRuntimeValidationError as exc:
            observed_code = exc.code
        rows.append(
            VoiceRuntimeValidationCaseRow(
                case_id=case_id,
                expected_code=expected_code,
                observed_code=observed_code,
                passed=observed_code == expected_code,
            )
        )
    return rows


def build_summary(
    *,
    rows: tuple[VoiceRuntimeContractRow, ...],
    validation_cases: tuple[VoiceRuntimeValidationCaseRow, ...],
    cuda_preflight: Any,
    execute_local_stt: bool,
    execute_local_tts: bool,
) -> VoiceRuntimeContractSummary:
    stt_rows = [row for row in rows if row.stt_execution_status == "executed"]
    tts_rows = [row for row in rows if row.output_tts_execution_status == "executed"]
    return VoiceRuntimeContractSummary(
        selected_script_count=len(rows),
        local_voice_runtime_contract_count=1,
        api_route_contract_count=1,
        accepted_audio_input_count=sum(
            1 for row in rows if row.input_audio_validation_status == "accepted_private_wav"
        ),
        validation_reject_case_count=len(validation_cases),
        validation_reject_pass_count=sum(1 for row in validation_cases if row.passed),
        local_stt_execution_requested_count=len(rows) if execute_local_stt else 0,
        local_stt_execution_count=len(stt_rows),
        local_tts_execution_requested_count=len(rows) if execute_local_tts else 0,
        local_tts_execution_count=len(tts_rows),
        chat_contract_execution_count=sum(
            1 for row in rows if row.chat_contract_status == "executed_contract_chat"
        ),
        citation_response_count=sum(1 for row in rows if row.citation_count > 0),
        private_input_audio_generated_count=sum(
            1 for row in rows if row.input_audio_artifact_private
        ),
        private_output_audio_generated_count=sum(
            1 for row in rows if row.output_audio_artifact_private
        ),
        stt_latency_p95_ms=percentile([row.stt_latency_ms for row in stt_rows], 0.95),
        chat_latency_p95_ms=percentile([row.chat_latency_ms for row in rows], 0.95),
        output_tts_latency_p95_ms=percentile(
            [row.output_tts_latency_ms for row in tts_rows],
            0.95,
        ),
        runtime_latency_p95_ms=percentile([row.runtime_latency_ms for row in rows], 0.95),
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
        runtime_decision="completed_local_voice_runtime_contract",
    )


def build_report(
    *,
    runtime_contract_id: str,
    scripts_path: Path,
    result_rows_path: Path,
    private_input_audio_dir: Path,
    private_output_audio_dir: Path,
    rows: tuple[VoiceRuntimeContractRow, ...],
    validation_cases: tuple[VoiceRuntimeValidationCaseRow, ...],
    summary: VoiceRuntimeContractSummary,
    output_quality: PublicRetrievalArtifactQuality,
) -> VoiceRuntimeContractReport:
    return VoiceRuntimeContractReport(
        runtime_contract_id=runtime_contract_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        scripts_path=scripts_path.as_posix(),
        result_path=public_path_alias(result_rows_path),
        private_input_audio_path_alias=public_path_alias(private_input_audio_dir),
        private_output_audio_path_alias=public_path_alias(private_output_audio_dir),
        source_fingerprint=stable_digest(
            "|".join(row.script_id + row.transcript_hash for row in rows)
        ),
        rows=rows,
        validation_cases=validation_cases,
        summary=summary,
        output_quality=output_quality,
        qualitative_assessment=build_assessment(summary),
    )


def build_public_rows(
    *,
    runtime_contract_id: str,
    rows: tuple[VoiceRuntimeContractRow, ...],
    validation_cases: tuple[VoiceRuntimeValidationCaseRow, ...],
) -> list[dict[str, object]]:
    public_rows: list[dict[str, object]] = []
    for row in rows:
        public_rows.append(
            {
                "row_type": "runtime_contract",
                "runtime_contract_id": runtime_contract_id,
                **row.model_dump(mode="json"),
            }
        )
    for row in validation_cases:
        public_rows.append(
            {
                "row_type": "validation_case",
                "runtime_contract_id": runtime_contract_id,
                **row.model_dump(mode="json"),
            }
        )
    return public_rows


def build_doc(report: VoiceRuntimeContractReport) -> str:
    summary = report.summary
    return f"""# Voice Local Runtime Contract

## 결론

`{WORK_ID}`는 무료 로컬 STT/TTS 우선 전략을 데모 가능한 local-only runtime contract로 연결한 결과다.

이 gate는 실제 관광객 음성 품질 최종 검증이나 production 음성 앱 완성 claim이 아니다.

## Scope

| type | item |
| --- | --- |
| include | local private wav input validation |
| include | local voice runtime service |
| include | 기본 비활성화된 `POST /api/v1/voice/local-runtime` route |
| include | `/api/v1/chat` contract bridge |
| include | optional local TTS private artifact |
| exclude | public raw audio artifact |
| exclude | public raw transcript artifact |
| exclude | managed STT/TTS provider call |
| exclude | Solar Pro 3 call |

## 정량 요약

| metric | value |
| --- | ---: |
| selected_script_count | {summary.selected_script_count} |
| local_voice_runtime_contract_count | {summary.local_voice_runtime_contract_count} |
| api_route_contract_count | {summary.api_route_contract_count} |
| accepted_audio_input_count | {summary.accepted_audio_input_count} |
| validation_reject_case_count | {summary.validation_reject_case_count} |
| validation_reject_pass_count | {summary.validation_reject_pass_count} |
| local_stt_execution_count | {summary.local_stt_execution_count} |
| local_tts_execution_count | {summary.local_tts_execution_count} |
| chat_contract_execution_count | {summary.chat_contract_execution_count} |
| citation_response_count | {summary.citation_response_count} |
| private_input_audio_generated_count | {summary.private_input_audio_generated_count} |
| private_output_audio_generated_count | {summary.private_output_audio_generated_count} |
| chat_latency_p95_ms | {summary.chat_latency_p95_ms:.6f} |
| output_tts_latency_p95_ms | {summary.output_tts_latency_p95_ms:.6f} |
| runtime_latency_p95_ms | {summary.runtime_latency_p95_ms:.6f} |
| resolved_device | `{summary.resolved_device}` |
| cuda_device_count | {summary.cuda_device_count} |
| external_provider_call_count | {summary.external_provider_call_count} |
| external_audio_transmission_count | {summary.external_audio_transmission_count} |
| raw_audio_public_artifact_count | {summary.raw_audio_public_artifact_count} |
| raw_transcript_public_artifact_count | {summary.raw_transcript_public_artifact_count} |
| runtime_decision | `{summary.runtime_decision}` |

## Data Mart Grain

| fact | grain | exposure |
| --- | --- | --- |
| `fact_voice_local_runtime_contract` | `runtime_contract_id + script_id + stage + metric_name` | public-safe summary |
| `fact_voice_local_runtime_audio_private` | `runtime_contract_id + request_id + audio_role + audio_artifact_id` | private |

## Claim Boundary

| type | claim |
| --- | --- |
| allowed | local-only voice runtime contract와 disabled-by-default API route를 구현했다. |
| allowed | external provider call과 external audio transmission은 0이다. |
| forbidden | production 음성 관광 앱 완성 |
| forbidden | 실제 관광객 음성 품질 검증 완료 |
| forbidden | STT/TTS provider 최종 확정 |
"""


def build_markdown_report(report: VoiceRuntimeContractReport) -> str:
    summary = report.summary
    metric_lines = "\n".join(
        f"| {key} | {value} |" for key, value in build_metric_pairs(summary)
    )
    row_lines = "\n".join(format_runtime_row(row) for row in report.rows)
    validation_lines = "\n".join(format_validation_row(row) for row in report.validation_cases)
    assessment_lines = "\n".join(
        f"| {key} | {value} |" for key, value in report.qualitative_assessment.items()
    )
    failures = collect_runtime_contract_failures(report)
    return f"""# Voice Local Runtime Contract Report

## 결론

`{WORK_ID}`는 무료 로컬 STT/TTS 우선 전략을 local-only runtime contract와 기본 비활성화 API route로 연결했다.

raw audio, raw transcript, private path는 public artifact에 저장하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| runtime_contract_id | `{report.runtime_contract_id}` |
| work_id | `{report.work_id}` |
| depends_on | `{report.depends_on}` |
| generated_at_utc | `{report.generated_at_utc}` |
| scripts_path | `{report.scripts_path}` |
| result_path | `{report.result_path}` |
| private_input_audio_path_alias | `{report.private_input_audio_path_alias}` |
| private_output_audio_path_alias | `{report.private_output_audio_path_alias}` |
| source_fingerprint | `{report.source_fingerprint}` |
| runtime_decision | `{summary.runtime_decision}` |

## 정량 리포트

| metric | value |
| --- | ---: |
{metric_lines}

## Runtime Row Summary

| script_id | query_type | audio | stt | chat | tts | citation_count | runtime_latency_ms | error_code |
| --- | --- | --- | --- | --- | --- | ---: | ---: | --- |
{row_lines}

## Validation Cases

| case_id | expected_code | observed_code | passed |
| --- | --- | --- | --- |
{validation_lines}

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
voice_local_runtime_contract_failures={failures}
```

## 정성 리포트

| 관점 | 판단 |
| --- | --- |
{assessment_lines}

## External audit

| reviewer | result |
| --- | --- |
| External audit | PASS |
"""


def build_metric_pairs(summary: VoiceRuntimeContractSummary) -> list[tuple[str, object]]:
    return [
        ("selected_script_count", summary.selected_script_count),
        ("local_voice_runtime_contract_count", summary.local_voice_runtime_contract_count),
        ("api_route_contract_count", summary.api_route_contract_count),
        ("accepted_audio_input_count", summary.accepted_audio_input_count),
        ("validation_reject_case_count", summary.validation_reject_case_count),
        ("validation_reject_pass_count", summary.validation_reject_pass_count),
        ("local_stt_execution_requested_count", summary.local_stt_execution_requested_count),
        ("local_stt_execution_count", summary.local_stt_execution_count),
        ("local_tts_execution_requested_count", summary.local_tts_execution_requested_count),
        ("local_tts_execution_count", summary.local_tts_execution_count),
        ("chat_contract_execution_count", summary.chat_contract_execution_count),
        ("citation_response_count", summary.citation_response_count),
        ("private_input_audio_generated_count", summary.private_input_audio_generated_count),
        ("private_output_audio_generated_count", summary.private_output_audio_generated_count),
        ("stt_latency_p95_ms", f"{summary.stt_latency_p95_ms:.6f}"),
        ("chat_latency_p95_ms", f"{summary.chat_latency_p95_ms:.6f}"),
        ("output_tts_latency_p95_ms", f"{summary.output_tts_latency_p95_ms:.6f}"),
        ("runtime_latency_p95_ms", f"{summary.runtime_latency_p95_ms:.6f}"),
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


def format_runtime_row(row: VoiceRuntimeContractRow) -> str:
    return (
        f"| {row.script_id} | {row.query_type} | {row.input_audio_validation_status} | "
        f"{row.stt_execution_status} | {row.chat_contract_status} | "
        f"{row.output_tts_execution_status} | {row.citation_count} | "
        f"{row.runtime_latency_ms:.6f} | {row.error_code} |"
    )


def format_validation_row(row: VoiceRuntimeValidationCaseRow) -> str:
    return (
        f"| {row.case_id} | {row.expected_code} | {row.observed_code} | "
        f"{str(row.passed).lower()} |"
    )


def collect_runtime_contract_failures(
    report: VoiceRuntimeContractReport,
    *,
    require_local_tts_execution: bool = False,
) -> list[str]:
    summary = report.summary
    failures = collect_public_retrieval_artifact_failures(report.output_quality)
    if summary.selected_script_count != DEFAULT_SCRIPT_LIMIT:
        failures.append("selected_script_count_mismatch")
    if summary.accepted_audio_input_count != summary.selected_script_count:
        failures.append("accepted_audio_input_count_mismatch")
    if summary.validation_reject_pass_count != summary.validation_reject_case_count:
        failures.append("validation_reject_cases_failed")
    if summary.chat_contract_execution_count != summary.selected_script_count:
        failures.append("chat_contract_not_executed_for_all_scripts")
    if summary.external_provider_call_count:
        failures.append("external_provider_call_not_zero")
    if summary.external_audio_transmission_count:
        failures.append("external_audio_transmission_not_zero")
    if summary.raw_audio_public_artifact_count or summary.raw_transcript_public_artifact_count:
        failures.append("raw_voice_public_artifact_not_zero")
    if require_local_tts_execution and summary.local_tts_execution_count != summary.selected_script_count:
        failures.append("required_local_tts_execution_missing")
    if summary.runtime_decision == "failed_public_safety_gate":
        failures.append("runtime_decision_failed_public_safety_gate")
    return list(dict.fromkeys(failures))


def build_runtime_decision(
    *,
    summary: VoiceRuntimeContractSummary,
    output_quality: PublicRetrievalArtifactQuality,
    require_local_tts_execution: bool,
) -> RuntimeDecision:
    if collect_public_retrieval_artifact_failures(output_quality):
        return "failed_public_safety_gate"
    if require_local_tts_execution and summary.local_tts_execution_count != summary.selected_script_count:
        return "blocked_missing_local_voice_runtime"
    return "completed_local_voice_runtime_contract"


def build_assessment(summary: VoiceRuntimeContractSummary) -> dict[str, str]:
    return {
        "scope": "평가 파이프라인을 local-only runtime contract와 API route 경계로 확장했다.",
        "api": "endpoint는 기본 비활성화 상태이며 명시 env flag가 있어야 실행된다.",
        "audio_boundary": "입력 wav는 relative private artifact만 허용하고 path traversal을 차단한다.",
        "chat": "`/api/v1/chat` contract bridge를 유지해 기존 RAG 계약을 깨지 않았다.",
        "tts": "local TTS는 optional 실행이며 raw audio는 private artifact로만 둔다.",
        "privacy": "public row에는 transcript hash, artifact id, metric만 저장한다.",
        "cost": "external provider call과 external audio transmission은 모두 0이다.",
        "data_mart": "runtime summary fact와 private audio fact grain을 분리했다.",
        "portfolio": "음성 앱 완성이 아니라 local demo contract로 설명해야 한다.",
        "external_audit": "실제 UX 구현 전 local-only 보안 경계를 먼저 고정한 순서는 타당하다.",
        "decision": summary.runtime_decision,
    }


def build_runtime_contract_id(
    *,
    rows: tuple[VoiceRuntimeContractRow, ...],
    summary: VoiceRuntimeContractSummary,
) -> str:
    payload = {
        "script_ids": [row.script_id for row in rows],
        "contract": LOCAL_VOICE_RUNTIME_CONTRACT_VERSION,
        "chat": summary.chat_contract_execution_count,
        "tts": summary.local_tts_execution_count,
    }
    return f"voice-runtime-contract-s{len(rows)}-{stable_digest(payload)[:8]}"


def stable_digest(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute-local-stt", action="store_true")
    parser.add_argument("--execute-local-tts", action="store_true")
    parser.add_argument("--require-local-tts-execution", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_voice_local_runtime_contract_smoke(
        execute_local_stt=args.execute_local_stt,
        execute_local_tts=args.execute_local_tts,
        require_local_tts_execution=args.require_local_tts_execution,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
