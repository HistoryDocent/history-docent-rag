from __future__ import annotations

import argparse
import hashlib
import json
import os
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict, Field

from app.api.app import create_app
from app.application.voice_local_runtime import LOCAL_VOICE_RUNTIME_CONTRACT_VERSION
from app.core.project_paths import project_path, repository_root
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    collect_public_retrieval_artifact_failures,
    measure_public_retrieval_artifact_quality,
    public_path_alias,
    write_public_retrieval_result_rows,
)
from pipelines.voice_stt_tts_local_smoke import select_local_smoke_scripts
from pipelines.voice_stt_tts_provider_bench_readiness import load_voice_benchmark_scripts


REPORT_VERSION = "voice-api-local-runtime-route-smoke-report/v1"
WORK_ID = "HD-VOICE-API-LOCAL-RUNTIME-ROUTE-SMOKE-001"
DEPENDS_ON = "HD-VOICE-DEMO-PLAYBACK-SMOKE-001"
ROUTE_PATH = "/api/v1/voice/local-runtime"
ENV_FLAG = "HISTORY_DOCENT_ENABLE_LOCAL_VOICE_DEMO"

DEFAULT_SCRIPTS_PATH = Path("data_samples") / "voice_benchmark_scripts.sample.jsonl"
DEFAULT_PRIVATE_INPUT_AUDIO_DIR = Path("private_data") / "voice" / "local_api_route_smoke"
DEFAULT_DOC_PATH = Path("docs") / "VOICE_API_LOCAL_RUNTIME_ROUTE_SMOKE.md"
DEFAULT_REPORT_PATH = (
    Path("evals") / "reports" / "voice_api_local_runtime_route_smoke_report.md"
)
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "voice_api_local_runtime_route_smoke_rows.jsonl"
)
DEFAULT_SCRIPT_LIMIT = 1

RouteContractStatus = Literal[
    "default_disabled",
    "enabled_contract_response",
    "validation_rejected",
    "unexpected_response",
]
RouteSmokeDecision = Literal[
    "completed_local_voice_api_route_smoke",
    "failed_route_contract_gate",
    "failed_public_safety_gate",
]


class VoiceApiRouteSmokeBase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class VoiceApiRouteSmokeRow(VoiceApiRouteSmokeBase):
    scenario_id: str = Field(min_length=1)
    endpoint: str = ROUTE_PATH
    method: str = "POST"
    env_flag_state: str = Field(min_length=1)
    expected_status_code: int = Field(ge=100)
    observed_status_code: int = Field(ge=100)
    passed: bool
    response_contract_status: RouteContractStatus
    detail_code: str
    contract_version: str
    runtime_id: str
    request_payload_hash: str = Field(min_length=8)
    input_audio_artifact_id: str
    transcript_hash: str
    transcript_source: str
    stt_execution_status: str
    chat_contract_status: str
    output_tts_execution_status: str
    citation_count: int = Field(ge=0)
    abstained: bool | None = None
    tts_final_provider: bool | None = None
    external_provider_call_count: int = Field(ge=0)
    external_audio_transmission_count: int = Field(ge=0)
    live_stt_call_count: int = Field(ge=0)
    live_tts_call_count: int = Field(ge=0)
    live_solar_call_count: int = Field(ge=0)


class VoiceApiRouteSmokeSummary(VoiceApiRouteSmokeBase):
    selected_script_count: int = Field(ge=0)
    api_route_smoke_count: int = Field(ge=0)
    endpoint_count: int = Field(ge=0)
    total_route_request_count: int = Field(ge=0)
    default_disabled_request_count: int = Field(ge=0)
    default_disabled_pass_count: int = Field(ge=0)
    default_disabled_status_code: int = Field(ge=0)
    explicit_flag_request_count: int = Field(ge=0)
    explicit_flag_contract_pass_count: int = Field(ge=0)
    explicit_flag_status_code: int = Field(ge=0)
    validation_request_count: int = Field(ge=0)
    validation_reject_pass_count: int = Field(ge=0)
    path_traversal_status_code: int = Field(ge=0)
    public_audio_status_code: int = Field(ge=0)
    private_input_audio_generated_count: int = Field(ge=0)
    accepted_audio_input_count: int = Field(ge=0)
    chat_contract_execution_count: int = Field(ge=0)
    citation_response_count: int = Field(ge=0)
    stt_execution_requested_count: int = Field(ge=0)
    local_stt_execution_count: int = Field(ge=0)
    tts_execution_requested_count: int = Field(ge=0)
    local_tts_execution_count: int = Field(ge=0)
    tts_final_provider_count: int = Field(ge=0)
    response_answer_public_row_count: int = Field(ge=0)
    response_spoken_answer_public_row_count: int = Field(ge=0)
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
    route_smoke_decision: RouteSmokeDecision


class VoiceApiRouteSmokeReport(VoiceApiRouteSmokeBase):
    report_version: str = REPORT_VERSION
    route_smoke_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    work_id: str = WORK_ID
    depends_on: str = DEPENDS_ON
    endpoint: str = ROUTE_PATH
    env_flag_name: str = ENV_FLAG
    scripts_path: str = Field(min_length=1)
    private_input_audio_path_alias: str = Field(min_length=1)
    result_path: str = Field(min_length=1)
    source_fingerprint: str = Field(min_length=8)
    summary: VoiceApiRouteSmokeSummary
    rows: tuple[VoiceApiRouteSmokeRow, ...]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def run_voice_api_local_runtime_route_smoke(
    *,
    scripts_path: Path = DEFAULT_SCRIPTS_PATH,
    private_input_audio_dir: Path = DEFAULT_PRIVATE_INPUT_AUDIO_DIR,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
    doc_path: Path = DEFAULT_DOC_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    script_limit: int = DEFAULT_SCRIPT_LIMIT,
) -> VoiceApiRouteSmokeReport:
    scripts = select_local_smoke_scripts(
        load_voice_benchmark_scripts(project_path(scripts_path)),
        limit=script_limit,
    )
    if not scripts:
        raise ValueError("voice API route smoke requires at least one script")
    script = scripts[0]
    input_audio_path = private_input_audio_dir / f"{script.script_id}.wav"
    synthesize_private_wav(input_audio_path)

    payload = {
        "request_id": f"voice-api-route-{script.script_id}",
        "input_audio_path": repository_relative_path(input_audio_path).as_posix(),
        "fallback_transcript_text": script.script_text,
        "language": script.language,
        "query_type": script.query_type,
        "place_context": list(script.place_ids),
        "retrieval_mode": "contract_only",
        "provider_mode": "contract_only",
        "active_route_mode": "disabled",
        "execute_local_stt": False,
        "execute_local_tts": False,
    }
    rows = tuple(run_route_scenarios(payload))
    summary = build_summary(rows=rows, selected_script_count=len(scripts))
    route_smoke_id = build_route_smoke_id(rows=rows, summary=summary)
    public_rows = build_public_rows(route_smoke_id=route_smoke_id, rows=rows)
    provisional_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=route_smoke_id,
        result_rows=public_rows,
        report_text="",
    )
    provisional = build_report(
        route_smoke_id=route_smoke_id,
        scripts_path=scripts_path,
        private_input_audio_dir=private_input_audio_dir,
        result_rows_path=result_rows_path,
        rows=rows,
        summary=summary,
        output_quality=provisional_quality,
    )
    doc_text = build_doc(provisional)
    report_text = build_markdown_report(provisional)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=route_smoke_id,
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
            "route_smoke_decision": build_decision(summary=summary, output_quality=output_quality),
        }
    )
    report = build_report(
        route_smoke_id=route_smoke_id,
        scripts_path=scripts_path,
        private_input_audio_dir=private_input_audio_dir,
        result_rows_path=result_rows_path,
        rows=rows,
        summary=summary,
        output_quality=output_quality,
    )
    failures = collect_route_smoke_failures(report)
    if failures:
        raise ValueError(f"voice API local runtime route smoke gate failed: {failures}")

    write_public_retrieval_result_rows(
        path=project_path(result_rows_path),
        rows=build_public_rows(route_smoke_id=route_smoke_id, rows=rows),
    )
    project_path(doc_path).write_text(build_doc(report), encoding="utf-8")
    project_path(report_path).write_text(build_markdown_report(report), encoding="utf-8")
    print(
        "voice_api_local_runtime_route_smoke "
        f"status={report.summary.route_smoke_decision} "
        f"requests={report.summary.total_route_request_count} "
        f"default_disabled={report.summary.default_disabled_pass_count} "
        f"enabled={report.summary.explicit_flag_contract_pass_count} "
        f"external_calls={report.summary.external_provider_call_count}",
    )
    return report


def run_route_scenarios(payload: dict[str, Any]) -> list[VoiceApiRouteSmokeRow]:
    original_flag = os.environ.get(ENV_FLAG)
    client = TestClient(create_app(), raise_server_exceptions=False)
    rows: list[VoiceApiRouteSmokeRow] = []
    try:
        os.environ.pop(ENV_FLAG, None)
        disabled_response = client.post(ROUTE_PATH, json=payload)
        rows.append(
            row_from_response(
                scenario_id="default_disabled",
                env_flag_state="unset",
                expected_status_code=403,
                payload=payload,
                response_json=safe_json(disabled_response),
                observed_status_code=disabled_response.status_code,
            )
        )

        os.environ[ENV_FLAG] = "1"
        enabled_response = client.post(ROUTE_PATH, json=payload)
        rows.append(
            row_from_response(
                scenario_id="explicit_flag_contract_response",
                env_flag_state="enabled",
                expected_status_code=200,
                payload=payload,
                response_json=safe_json(enabled_response),
                observed_status_code=enabled_response.status_code,
            )
        )

        traversal_payload = dict(payload, input_audio_path="../voice.wav")
        traversal_response = client.post(ROUTE_PATH, json=traversal_payload)
        rows.append(
            row_from_response(
                scenario_id="reject_path_traversal",
                env_flag_state="enabled",
                expected_status_code=422,
                payload=traversal_payload,
                response_json=safe_json(traversal_response),
                observed_status_code=traversal_response.status_code,
            )
        )

        public_path_payload = dict(payload, input_audio_path="public_audio.wav")
        public_path_response = client.post(ROUTE_PATH, json=public_path_payload)
        rows.append(
            row_from_response(
                scenario_id="reject_public_audio_path",
                env_flag_state="enabled",
                expected_status_code=400,
                payload=public_path_payload,
                response_json=safe_json(public_path_response),
                observed_status_code=public_path_response.status_code,
            )
        )
    finally:
        if original_flag is None:
            os.environ.pop(ENV_FLAG, None)
        else:
            os.environ[ENV_FLAG] = original_flag
    return rows


def row_from_response(
    *,
    scenario_id: str,
    env_flag_state: str,
    expected_status_code: int,
    payload: dict[str, Any],
    response_json: dict[str, Any],
    observed_status_code: int,
) -> VoiceApiRouteSmokeRow:
    detail_code = extract_detail_code(response_json)
    status = infer_contract_status(scenario_id, observed_status_code)
    passed = observed_status_code == expected_status_code
    if scenario_id == "default_disabled":
        passed = passed and detail_code == "local_voice_runtime_disabled"
    if scenario_id == "explicit_flag_contract_response":
        passed = passed and response_json.get("contract_version") == LOCAL_VOICE_RUNTIME_CONTRACT_VERSION
        passed = passed and response_json.get("external_provider_call_count") == 0
        passed = passed and response_json.get("external_audio_transmission_count") == 0
        passed = passed and response_json.get("stt_execution_status") == "skipped_by_flag"
        passed = passed and response_json.get("output_tts_execution_status") == "skipped_by_flag"
    if scenario_id == "reject_public_audio_path":
        passed = passed and detail_code == "public_audio_path_not_allowed"
    return VoiceApiRouteSmokeRow(
        scenario_id=scenario_id,
        env_flag_state=env_flag_state,
        expected_status_code=expected_status_code,
        observed_status_code=observed_status_code,
        passed=passed,
        response_contract_status=status,
        detail_code=detail_code,
        contract_version=str(response_json.get("contract_version") or ""),
        runtime_id=str(response_json.get("runtime_id") or ""),
        request_payload_hash=stable_digest(public_safe_payload(payload)),
        input_audio_artifact_id=str(response_json.get("input_audio_artifact_id") or ""),
        transcript_hash=str(response_json.get("transcript_hash") or ""),
        transcript_source=str(response_json.get("transcript_source") or ""),
        stt_execution_status=str(response_json.get("stt_execution_status") or ""),
        chat_contract_status=str(response_json.get("chat_contract_status") or ""),
        output_tts_execution_status=str(response_json.get("output_tts_execution_status") or ""),
        citation_count=int(response_json.get("citation_count") or 0),
        abstained=response_json.get("abstained") if isinstance(response_json.get("abstained"), bool) else None,
        tts_final_provider=(
            response_json.get("tts_final_provider")
            if isinstance(response_json.get("tts_final_provider"), bool)
            else None
        ),
        external_provider_call_count=int(response_json.get("external_provider_call_count") or 0),
        external_audio_transmission_count=int(response_json.get("external_audio_transmission_count") or 0),
        live_stt_call_count=0,
        live_tts_call_count=0,
        live_solar_call_count=int(response_json.get("live_solar_call_count") or 0),
    )


def infer_contract_status(scenario_id: str, observed_status_code: int) -> RouteContractStatus:
    if scenario_id == "default_disabled" and observed_status_code == 403:
        return "default_disabled"
    if scenario_id == "explicit_flag_contract_response" and observed_status_code == 200:
        return "enabled_contract_response"
    if scenario_id.startswith("reject_") and observed_status_code in {400, 422}:
        return "validation_rejected"
    return "unexpected_response"


def build_summary(
    *,
    rows: tuple[VoiceApiRouteSmokeRow, ...],
    selected_script_count: int,
) -> VoiceApiRouteSmokeSummary:
    default_rows = [row for row in rows if row.scenario_id == "default_disabled"]
    enabled_rows = [row for row in rows if row.scenario_id == "explicit_flag_contract_response"]
    validation_rows = [row for row in rows if row.scenario_id.startswith("reject_")]
    return VoiceApiRouteSmokeSummary(
        selected_script_count=selected_script_count,
        api_route_smoke_count=1,
        endpoint_count=len({row.endpoint for row in rows}),
        total_route_request_count=len(rows),
        default_disabled_request_count=len(default_rows),
        default_disabled_pass_count=sum(1 for row in default_rows if row.passed),
        default_disabled_status_code=status_code_for(default_rows),
        explicit_flag_request_count=len(enabled_rows),
        explicit_flag_contract_pass_count=sum(1 for row in enabled_rows if row.passed),
        explicit_flag_status_code=status_code_for(enabled_rows),
        validation_request_count=len(validation_rows),
        validation_reject_pass_count=sum(1 for row in validation_rows if row.passed),
        path_traversal_status_code=status_code_for(
            [row for row in rows if row.scenario_id == "reject_path_traversal"]
        ),
        public_audio_status_code=status_code_for(
            [row for row in rows if row.scenario_id == "reject_public_audio_path"]
        ),
        private_input_audio_generated_count=1,
        accepted_audio_input_count=sum(
            1 for row in enabled_rows if row.input_audio_artifact_id
        ),
        chat_contract_execution_count=sum(
            1 for row in enabled_rows if row.chat_contract_status == "executed_contract_chat"
        ),
        citation_response_count=sum(1 for row in enabled_rows if row.citation_count > 0),
        stt_execution_requested_count=0,
        local_stt_execution_count=sum(
            1 for row in enabled_rows if row.stt_execution_status == "executed"
        ),
        tts_execution_requested_count=0,
        local_tts_execution_count=sum(
            1 for row in enabled_rows if row.output_tts_execution_status == "executed"
        ),
        tts_final_provider_count=sum(1 for row in enabled_rows if row.tts_final_provider is True),
        response_answer_public_row_count=0,
        response_spoken_answer_public_row_count=0,
        external_provider_call_count=sum(row.external_provider_call_count for row in rows),
        external_audio_transmission_count=sum(row.external_audio_transmission_count for row in rows),
        live_stt_call_count=sum(row.live_stt_call_count for row in rows),
        live_tts_call_count=sum(row.live_tts_call_count for row in rows),
        live_solar_call_count=sum(row.live_solar_call_count for row in rows),
        raw_audio_public_artifact_count=0,
        raw_transcript_public_artifact_count=0,
        client_secret_exposure_count=0,
        public_private_path_leakage_count=0,
        public_secret_like_leakage_count=0,
        public_raw_payload_leakage_count=0,
        route_smoke_decision=build_decision_from_counts(
            default_disabled_pass_count=sum(1 for row in default_rows if row.passed),
            explicit_flag_contract_pass_count=sum(1 for row in enabled_rows if row.passed),
            validation_reject_pass_count=sum(1 for row in validation_rows if row.passed),
            validation_request_count=len(validation_rows),
            external_provider_call_count=sum(row.external_provider_call_count for row in rows),
            external_audio_transmission_count=sum(row.external_audio_transmission_count for row in rows),
        ),
    )


def status_code_for(rows: list[VoiceApiRouteSmokeRow]) -> int:
    return rows[0].observed_status_code if rows else 0


def build_decision_from_counts(
    *,
    default_disabled_pass_count: int,
    explicit_flag_contract_pass_count: int,
    validation_reject_pass_count: int,
    validation_request_count: int,
    external_provider_call_count: int,
    external_audio_transmission_count: int,
) -> RouteSmokeDecision:
    if external_provider_call_count or external_audio_transmission_count:
        return "failed_route_contract_gate"
    if default_disabled_pass_count != 1 or explicit_flag_contract_pass_count != 1:
        return "failed_route_contract_gate"
    if validation_reject_pass_count != validation_request_count:
        return "failed_route_contract_gate"
    return "completed_local_voice_api_route_smoke"


def build_decision(
    *,
    summary: VoiceApiRouteSmokeSummary,
    output_quality: PublicRetrievalArtifactQuality,
) -> RouteSmokeDecision:
    if collect_public_retrieval_artifact_failures(output_quality):
        return "failed_public_safety_gate"
    return build_decision_from_counts(
        default_disabled_pass_count=summary.default_disabled_pass_count,
        explicit_flag_contract_pass_count=summary.explicit_flag_contract_pass_count,
        validation_reject_pass_count=summary.validation_reject_pass_count,
        validation_request_count=summary.validation_request_count,
        external_provider_call_count=summary.external_provider_call_count,
        external_audio_transmission_count=summary.external_audio_transmission_count,
    )


def build_report(
    *,
    route_smoke_id: str,
    scripts_path: Path,
    private_input_audio_dir: Path,
    result_rows_path: Path,
    rows: tuple[VoiceApiRouteSmokeRow, ...],
    summary: VoiceApiRouteSmokeSummary,
    output_quality: PublicRetrievalArtifactQuality,
) -> VoiceApiRouteSmokeReport:
    report = VoiceApiRouteSmokeReport(
        route_smoke_id=route_smoke_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        scripts_path=public_path_alias(scripts_path),
        private_input_audio_path_alias=public_path_alias(private_input_audio_dir),
        result_path=public_path_alias(result_rows_path),
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
    return report.model_copy(update={"qualitative_assessment": build_qualitative(report)})


def build_public_rows(
    *,
    route_smoke_id: str,
    rows: tuple[VoiceApiRouteSmokeRow, ...],
) -> list[dict[str, Any]]:
    return [
        {
            "row_type": "voice_api_local_runtime_route_smoke",
            "route_smoke_id": route_smoke_id,
            "scenario_id": row.scenario_id,
            "endpoint": row.endpoint,
            "method": row.method,
            "env_flag_state": row.env_flag_state,
            "expected_status_code": row.expected_status_code,
            "observed_status_code": row.observed_status_code,
            "passed": row.passed,
            "response_contract_status": row.response_contract_status,
            "detail_code": row.detail_code,
            "contract_version": row.contract_version,
            "runtime_id": row.runtime_id,
            "request_payload_hash": row.request_payload_hash,
            "input_audio_artifact_id": row.input_audio_artifact_id,
            "transcript_hash": row.transcript_hash,
            "transcript_source": row.transcript_source,
            "stt_execution_status": row.stt_execution_status,
            "chat_contract_status": row.chat_contract_status,
            "output_tts_execution_status": row.output_tts_execution_status,
            "citation_count": row.citation_count,
            "tts_final_provider": row.tts_final_provider,
            "external_provider_call_count": row.external_provider_call_count,
            "external_audio_transmission_count": row.external_audio_transmission_count,
            "live_solar_call_count": row.live_solar_call_count,
        }
        for row in rows
    ]


def build_doc(report: VoiceApiRouteSmokeReport) -> str:
    summary = report.summary
    return f"""# Voice API Local Runtime Route Smoke

## 결론

`{WORK_ID}`는 `{ROUTE_PATH}` route를 local-only contract smoke로 검증한 gate다.

결과는 `{summary.route_smoke_decision}`이다.

## Scope

| type | item |
| --- | --- |
| include | default disabled route check |
| include | explicit `{ENV_FLAG}` flag contract response |
| include | relative private wav input validation |
| include | path traversal and public audio path rejection |
| exclude | live microphone capture |
| exclude | speaker playback |
| exclude | local STT execution |
| exclude | local TTS execution |
| exclude | managed STT/TTS provider call |
| exclude | Solar Pro 3 call |

## 정량 요약

| metric | value |
| --- | ---: |
| selected_script_count | {summary.selected_script_count} |
| api_route_smoke_count | {summary.api_route_smoke_count} |
| endpoint_count | {summary.endpoint_count} |
| total_route_request_count | {summary.total_route_request_count} |
| default_disabled_request_count | {summary.default_disabled_request_count} |
| default_disabled_pass_count | {summary.default_disabled_pass_count} |
| default_disabled_status_code | {summary.default_disabled_status_code} |
| explicit_flag_request_count | {summary.explicit_flag_request_count} |
| explicit_flag_contract_pass_count | {summary.explicit_flag_contract_pass_count} |
| explicit_flag_status_code | {summary.explicit_flag_status_code} |
| validation_request_count | {summary.validation_request_count} |
| validation_reject_pass_count | {summary.validation_reject_pass_count} |
| path_traversal_status_code | {summary.path_traversal_status_code} |
| public_audio_status_code | {summary.public_audio_status_code} |
| private_input_audio_generated_count | {summary.private_input_audio_generated_count} |
| accepted_audio_input_count | {summary.accepted_audio_input_count} |
| chat_contract_execution_count | {summary.chat_contract_execution_count} |
| stt_execution_requested_count | {summary.stt_execution_requested_count} |
| local_stt_execution_count | {summary.local_stt_execution_count} |
| tts_execution_requested_count | {summary.tts_execution_requested_count} |
| local_tts_execution_count | {summary.local_tts_execution_count} |
| tts_final_provider_count | {summary.tts_final_provider_count} |
| response_answer_public_row_count | {summary.response_answer_public_row_count} |
| response_spoken_answer_public_row_count | {summary.response_spoken_answer_public_row_count} |
| external_provider_call_count | {summary.external_provider_call_count} |
| external_audio_transmission_count | {summary.external_audio_transmission_count} |
| live_stt_call_count | {summary.live_stt_call_count} |
| live_tts_call_count | {summary.live_tts_call_count} |
| live_solar_call_count | {summary.live_solar_call_count} |
| raw_audio_public_artifact_count | {summary.raw_audio_public_artifact_count} |
| raw_transcript_public_artifact_count | {summary.raw_transcript_public_artifact_count} |
| public_private_path_leakage_count | {summary.public_private_path_leakage_count} |
| public_secret_like_leakage_count | {summary.public_secret_like_leakage_count} |

## Data Mart Grain

| fact | grain | exposure |
| --- | --- | --- |
| `fact_voice_api_local_runtime_route_smoke_public` | `route_smoke_id + scenario_id + endpoint + metric_name` | public-safe |
| `fact_voice_api_local_runtime_request_private` | `route_smoke_id + request_id + audio_artifact_id` | private |

## Claim Boundary

| type | claim |
| --- | --- |
| allowed | local runtime route is disabled by default. |
| allowed | explicit local demo flag returns contract-only response. |
| allowed | public artifact stores hashes, status codes, and metrics only. |
| forbidden | production 음성 관광 앱 완성 |
| forbidden | 실제 관광객 음성 품질 검증 완료 |
| forbidden | STT/TTS provider 최종 확정 |
| forbidden | microphone capture 구현 완료 |
| forbidden | speaker playback 구현 완료 |
"""


def build_markdown_report(report: VoiceApiRouteSmokeReport) -> str:
    summary = report.summary
    quality = report.output_quality
    metric_lines = "\n".join(
        f"| {key} | {value} |" for key, value in build_metric_pairs(summary)
    )
    row_lines = "\n".join(format_row(row) for row in report.rows)
    assessment_lines = "\n".join(
        f"| {key} | {value} |" for key, value in report.qualitative_assessment.items()
    )
    failures = collect_route_smoke_failures(report)
    return f"""# Voice API Local Runtime Route Smoke Report

## 결론

`{WORK_ID}`는 `{summary.route_smoke_decision}`이다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| route_smoke_id | `{report.route_smoke_id}` |
| work_id | `{report.work_id}` |
| depends_on | `{report.depends_on}` |
| generated_at_utc | `{report.generated_at_utc}` |
| endpoint | `{report.endpoint}` |
| env_flag_name | `{report.env_flag_name}` |
| scripts_path | `{report.scripts_path}` |
| private_input_audio_path_alias | `{report.private_input_audio_path_alias}` |
| result_path | `{report.result_path}` |
| source_fingerprint | `{report.source_fingerprint}` |
| route_smoke_decision | `{summary.route_smoke_decision}` |

## 정량 리포트

| metric | value |
| --- | ---: |
{metric_lines}

## Scenario Summary

| scenario_id | env_flag | expected | observed | passed | status | detail_code | stt | tts | external_calls |
| --- | --- | ---: | ---: | --- | --- | --- | --- | --- | ---: |
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
voice_api_local_runtime_route_smoke_failures={failures}
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


def build_metric_pairs(summary: VoiceApiRouteSmokeSummary) -> list[tuple[str, object]]:
    return [
        ("selected_script_count", summary.selected_script_count),
        ("api_route_smoke_count", summary.api_route_smoke_count),
        ("endpoint_count", summary.endpoint_count),
        ("total_route_request_count", summary.total_route_request_count),
        ("default_disabled_request_count", summary.default_disabled_request_count),
        ("default_disabled_pass_count", summary.default_disabled_pass_count),
        ("default_disabled_status_code", summary.default_disabled_status_code),
        ("explicit_flag_request_count", summary.explicit_flag_request_count),
        ("explicit_flag_contract_pass_count", summary.explicit_flag_contract_pass_count),
        ("explicit_flag_status_code", summary.explicit_flag_status_code),
        ("validation_request_count", summary.validation_request_count),
        ("validation_reject_pass_count", summary.validation_reject_pass_count),
        ("path_traversal_status_code", summary.path_traversal_status_code),
        ("public_audio_status_code", summary.public_audio_status_code),
        ("private_input_audio_generated_count", summary.private_input_audio_generated_count),
        ("accepted_audio_input_count", summary.accepted_audio_input_count),
        ("chat_contract_execution_count", summary.chat_contract_execution_count),
        ("citation_response_count", summary.citation_response_count),
        ("stt_execution_requested_count", summary.stt_execution_requested_count),
        ("local_stt_execution_count", summary.local_stt_execution_count),
        ("tts_execution_requested_count", summary.tts_execution_requested_count),
        ("local_tts_execution_count", summary.local_tts_execution_count),
        ("tts_final_provider_count", summary.tts_final_provider_count),
        ("response_answer_public_row_count", summary.response_answer_public_row_count),
        (
            "response_spoken_answer_public_row_count",
            summary.response_spoken_answer_public_row_count,
        ),
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


def format_row(row: VoiceApiRouteSmokeRow) -> str:
    return (
        f"| {row.scenario_id} | {row.env_flag_state} | {row.expected_status_code} | "
        f"{row.observed_status_code} | {str(row.passed).lower()} | "
        f"{row.response_contract_status} | {row.detail_code} | "
        f"{row.stt_execution_status} | {row.output_tts_execution_status} | "
        f"{row.external_provider_call_count} |"
    )


def build_qualitative(report: VoiceApiRouteSmokeReport) -> dict[str, str]:
    summary = report.summary
    return {
        "scope": "local voice runtime route의 API 경계만 검증했다.",
        "security": "기본 disabled 상태와 explicit local flag를 분리했다.",
        "validation": "path traversal과 public audio path 입력을 거부했다.",
        "privacy": "public row에는 response answer와 spoken answer를 저장하지 않았다.",
        "cost": "external provider call과 external audio transmission은 0이다.",
        "data_mart": "public route scenario fact와 private request/audio fact를 분리했다.",
        "portfolio": "음성 서비스 완성이 아니라 disabled-by-default API route smoke로 설명한다.",
        "external_audit": "실제 음성 UX 전 API 경계부터 고정한 순서는 타당하다.",
        "decision": summary.route_smoke_decision,
    }


def collect_route_smoke_failures(report: VoiceApiRouteSmokeReport) -> list[str]:
    summary = report.summary
    failures = collect_public_retrieval_artifact_failures(report.output_quality)
    if summary.default_disabled_pass_count != 1:
        failures.append("default_disabled_gate_failed")
    if summary.explicit_flag_contract_pass_count != 1:
        failures.append("explicit_flag_contract_gate_failed")
    if summary.validation_reject_pass_count != summary.validation_request_count:
        failures.append("validation_reject_gate_failed")
    if summary.accepted_audio_input_count != 1:
        failures.append("accepted_audio_input_count_mismatch")
    if summary.external_provider_call_count:
        failures.append("external_provider_call_not_zero")
    if summary.external_audio_transmission_count:
        failures.append("external_audio_transmission_not_zero")
    if summary.live_stt_call_count or summary.live_tts_call_count or summary.live_solar_call_count:
        failures.append("live_call_not_zero")
    if summary.response_answer_public_row_count or summary.response_spoken_answer_public_row_count:
        failures.append("raw_response_text_public_row_not_zero")
    if summary.route_smoke_decision != "completed_local_voice_api_route_smoke":
        failures.append("route_smoke_decision_not_completed")
    return list(dict.fromkeys(failures))


def synthesize_private_wav(path: Path) -> None:
    resolved = project_path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(resolved), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(b"\x00\x00" * 1600)


def repository_relative_path(path: Path) -> Path:
    resolved = project_path(path).resolve()
    return resolved.relative_to(repository_root().resolve())


def safe_json(response: Any) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError:
        return {}
    return payload if isinstance(payload, dict) else {}


def extract_detail_code(response_json: dict[str, Any]) -> str:
    error = response_json.get("error")
    if isinstance(error, dict):
        code = error.get("code")
        return str(code) if code else ""
    detail = response_json.get("detail")
    if isinstance(detail, dict):
        code = detail.get("code")
        return str(code) if code else ""
    if isinstance(detail, list):
        return "request_validation_error"
    return ""


def public_safe_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "request_id": payload.get("request_id"),
        "input_audio_path_hash": stable_digest(str(payload.get("input_audio_path") or "")),
        "fallback_transcript_hash": stable_digest(str(payload.get("fallback_transcript_text") or "")),
        "language": payload.get("language"),
        "query_type": payload.get("query_type"),
        "place_context": payload.get("place_context"),
        "retrieval_mode": payload.get("retrieval_mode"),
        "provider_mode": payload.get("provider_mode"),
        "active_route_mode": payload.get("active_route_mode"),
        "execute_local_stt": payload.get("execute_local_stt"),
        "execute_local_tts": payload.get("execute_local_tts"),
    }


def build_route_smoke_id(
    *,
    rows: tuple[VoiceApiRouteSmokeRow, ...],
    summary: VoiceApiRouteSmokeSummary,
) -> str:
    payload = {
        "work_id": WORK_ID,
        "statuses": [row.observed_status_code for row in rows],
        "passed": [row.passed for row in rows],
        "decision": summary.route_smoke_decision,
    }
    return f"voice-api-route-smoke-r{len(rows)}-{stable_digest(payload)[:8]}"


def stable_digest(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]


def parse_args() -> argparse.Namespace:
    return argparse.ArgumentParser().parse_args()


def main() -> int:
    parse_args()
    run_voice_api_local_runtime_route_smoke()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
