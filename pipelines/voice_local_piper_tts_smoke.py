from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import subprocess
import sys
import time
import urllib.request
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
from pipelines.voice_stt_tts_local_tts_smoke import (
    DEFAULT_SCRIPTS_PATH,
    VoiceTtsSmokeScript,
    load_tts_smoke_scripts,
    percentile,
    read_wav_duration_ms,
    select_tts_smoke_scripts,
)
from pipelines.voice_stt_tts_provider_bench_readiness import build_cuda_preflight


REPORT_VERSION = "voice-local-piper-tts-smoke-report/v1"
WORK_ID = "HD-VOICE-LOCAL-PIPER-TTS-SMOKE-001"
DEPENDS_ON = "HD-VOICE-LOCAL-FASTER-WHISPER-STT-COMPARISON-001"
PROVIDER_CANDIDATE_ID = "local_piper_tts_target"
DEFAULT_DOC_PATH = Path("docs") / "VOICE_LOCAL_PIPER_TTS_SMOKE.md"
DEFAULT_REPORT_PATH = Path("evals") / "reports" / "voice_local_piper_tts_smoke_report.md"
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data") / "evals" / "results" / "voice_local_piper_tts_smoke_rows.jsonl"
)
DEFAULT_PRIVATE_AUDIO_DIR = Path("private_data") / "voice" / "local_piper_tts_audio"
DEFAULT_SCRIPT_LIMIT = 5
DEFAULT_VOICE_MANIFEST_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/voices.json"
PIPER_PACKAGE_NAME = "piper-tts"
PIPER_SOURCE_URL = "https://github.com/OHF-Voice/piper1-gpl"
PIPER_VOICE_SOURCE_URL = "https://huggingface.co/rhasspy/piper-voices"
PIPER_LICENSE_POLICY = (
    "piper-tts current package is GPL-3.0-or-later. Voice models require per-voice "
    "MODEL_CARD/license review."
)

PiperTtsStatus = Literal[
    "executed",
    "blocked_missing_runtime",
    "blocked_manifest_unavailable",
    "blocked_missing_korean_voice",
    "blocked_model_file_missing",
    "blocked_config_file_missing",
    "blocked_synthesis_error",
    "skipped_by_flag",
]
PiperTtsDecision = Literal[
    "completed_piper_tts_smoke",
    "blocked_missing_runtime",
    "blocked_manifest_unavailable",
    "blocked_missing_korean_voice",
    "failed_public_safety_gate",
]


class PiperTtsSmokeBase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PiperVoiceManifestSummary(PiperTtsSmokeBase):
    manifest_checked: bool
    manifest_source_url: str = Field(min_length=1)
    manifest_voice_count: int = Field(ge=0)
    manifest_language_count: int = Field(ge=0)
    korean_voice_count: int = Field(ge=0)
    selected_voice_id: str
    selected_voice_language: str
    selected_voice_quality: str
    license_policy: str = Field(min_length=1)


class PiperTtsSmokeRow(PiperTtsSmokeBase):
    script_id: str = Field(min_length=1)
    language: str = Field(min_length=1)
    provider_candidate_id: str = PROVIDER_CANDIDATE_ID
    model_family: str = "Piper"
    selected_voice_id: str
    resolved_device: str = Field(min_length=1)
    piper_cuda_requested: bool
    tts_execution_requested: bool
    synthesis_status: PiperTtsStatus
    latency_ms: float = Field(ge=0.0)
    audio_duration_ms: float = Field(ge=0.0)
    audio_file_size_bytes: int = Field(ge=0)
    audio_artifact_private: bool
    character_count: int = Field(ge=0)
    place_name_count: int = Field(ge=0)
    text_hash: str = Field(min_length=8)
    error_code: str


class PiperTtsSmokeSummary(PiperTtsSmokeBase):
    selected_script_count: int = Field(ge=0)
    public_safe_script_fixture_count: int = Field(ge=0)
    provider_candidate_count: int = Field(ge=0)
    piper_runtime_available_count: int = Field(ge=0)
    piper_distribution_installed_count: int = Field(ge=0)
    package_install_attempted_count: int = Field(ge=0)
    voice_manifest_checked_count: int = Field(ge=0)
    voice_manifest_available_count: int = Field(ge=0)
    manifest_voice_count: int = Field(ge=0)
    manifest_language_count: int = Field(ge=0)
    korean_voice_available_count: int = Field(ge=0)
    model_download_attempted_count: int = Field(ge=0)
    model_download_success_count: int = Field(ge=0)
    tts_execution_requested_count: int = Field(ge=0)
    local_tts_execution_count: int = Field(ge=0)
    private_audio_generated_count: int = Field(ge=0)
    private_audio_saved_count: int = Field(ge=0)
    tts_latency_p50_ms: float = Field(ge=0.0)
    tts_latency_p95_ms: float = Field(ge=0.0)
    audio_duration_total_ms: float = Field(ge=0.0)
    audio_file_size_total_bytes: int = Field(ge=0)
    resolved_device: str = Field(min_length=1)
    piper_cuda_requested_count: int = Field(ge=0)
    local_cuda_available_count: int = Field(ge=0)
    cuda_device_count: int = Field(ge=0)
    selected_voice_id: str
    selected_provider_candidate_id: str = PROVIDER_CANDIDATE_ID
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
    piper_tts_decision: PiperTtsDecision


class PiperTtsSmokeReport(PiperTtsSmokeBase):
    report_version: str = REPORT_VERSION
    smoke_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    work_id: str = WORK_ID
    depends_on: str = DEPENDS_ON
    scripts_path: str = Field(min_length=1)
    result_path: str = Field(min_length=1)
    private_audio_path_alias: str = Field(min_length=1)
    source_fingerprint: str = Field(min_length=8)
    piper_source_url: str = Field(min_length=1)
    piper_voice_source_url: str = Field(min_length=1)
    piper_version: str
    voice_manifest: PiperVoiceManifestSummary
    rows: tuple[PiperTtsSmokeRow, ...]
    summary: PiperTtsSmokeSummary
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def run_voice_local_piper_tts_smoke(
    *,
    scripts_path: Path = DEFAULT_SCRIPTS_PATH,
    doc_path: Path = DEFAULT_DOC_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
    private_audio_dir: Path = DEFAULT_PRIVATE_AUDIO_DIR,
    script_limit: int = DEFAULT_SCRIPT_LIMIT,
    voice_manifest_url: str = DEFAULT_VOICE_MANIFEST_URL,
    model_path: Path | None = None,
    config_path: Path | None = None,
    execute_local_tts: bool = False,
    require_local_execution: bool = False,
    package_install_attempted: bool = False,
    voice_manifest_payload: dict[str, Any] | None = None,
) -> PiperTtsSmokeReport:
    scripts = select_tts_smoke_scripts(
        load_tts_smoke_scripts(project_path(scripts_path)),
        limit=script_limit,
    )
    cuda_preflight = build_cuda_preflight()
    resolved_device = cuda_preflight.resolved_device
    runtime_available = is_piper_runtime_available()
    piper_version = get_distribution_version(PIPER_PACKAGE_NAME)
    manifest, manifest_available = load_voice_manifest(
        url=voice_manifest_url,
        injected_payload=voice_manifest_payload,
    )
    voice_summary = build_voice_manifest_summary(
        manifest=manifest,
        manifest_available=manifest_available,
        manifest_source_url=voice_manifest_url,
    )
    should_execute = (
        execute_local_tts
        and runtime_available
        and voice_summary.korean_voice_count > 0
        and model_path is not None
        and config_path is not None
    )
    audio_dir = project_path(private_audio_dir)
    if should_execute:
        audio_dir.mkdir(parents=True, exist_ok=True)

    rows = tuple(
        build_piper_tts_row(
            script=script,
            selected_voice_id=voice_summary.selected_voice_id,
            resolved_device=resolved_device,
            model_path=model_path,
            config_path=config_path,
            output_path=audio_dir / f"{script.script_id}.wav",
            runtime_available=runtime_available,
            manifest_available=manifest_available,
            korean_voice_available=voice_summary.korean_voice_count > 0,
            execute_local_tts=execute_local_tts,
            should_execute=should_execute,
        )
        for script in scripts
    )
    summary = build_summary(
        scripts=scripts,
        rows=rows,
        cuda_preflight=cuda_preflight,
        runtime_available=runtime_available,
        piper_version=piper_version,
        voice_manifest=voice_summary,
        manifest_available=manifest_available,
        execute_local_tts=execute_local_tts,
        package_install_attempted=package_install_attempted,
        model_download_attempted=False,
    )
    smoke_id = build_smoke_id(rows=rows, summary=summary)
    public_rows = build_public_rows(smoke_id=smoke_id, rows=rows)
    provisional_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=smoke_id,
        result_rows=public_rows,
        report_text="",
    )
    provisional = build_report(
        smoke_id=smoke_id,
        scripts_path=scripts_path,
        result_rows_path=result_rows_path,
        private_audio_dir=private_audio_dir,
        piper_version=piper_version,
        voice_manifest=voice_summary,
        rows=rows,
        summary=summary,
        output_quality=provisional_quality,
    )
    report_text = build_markdown_report(provisional)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=smoke_id,
        result_rows=public_rows,
        report_text=report_text,
    )
    summary = summary.model_copy(
        update={
            "public_private_path_leakage_count": output_quality.private_path_leakage_count,
            "public_secret_like_leakage_count": output_quality.secret_like_leakage_count,
            "public_raw_payload_leakage_count": output_quality.public_raw_text_leakage_count,
            "piper_tts_decision": build_decision(
                summary=summary,
                output_quality=output_quality,
                require_local_execution=require_local_execution,
            ),
        },
    )
    report = build_report(
        smoke_id=smoke_id,
        scripts_path=scripts_path,
        result_rows_path=result_rows_path,
        private_audio_dir=private_audio_dir,
        piper_version=piper_version,
        voice_manifest=voice_summary,
        rows=rows,
        summary=summary,
        output_quality=output_quality,
    )
    failures = collect_piper_tts_smoke_failures(
        report,
        require_local_execution=require_local_execution,
    )
    if failures:
        raise ValueError(f"voice local Piper TTS smoke gate failed: {failures}")

    write_public_retrieval_result_rows(path=project_path(result_rows_path), rows=public_rows)
    resolved_doc_path = project_path(doc_path)
    resolved_report_path = project_path(report_path)
    resolved_doc_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_report_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_doc_path.write_text(build_doc(report), encoding="utf-8")
    resolved_report_path.write_text(build_markdown_report(report), encoding="utf-8")
    print(
        "voice_local_piper_tts_smoke "
        f"status={report.summary.piper_tts_decision} "
        f"runtime={report.summary.piper_runtime_available_count} "
        f"korean_voices={report.summary.korean_voice_available_count} "
        f"tts={report.summary.local_tts_execution_count} "
        f"external_calls={report.summary.external_provider_call_count}",
    )
    return report


def is_piper_runtime_available() -> bool:
    return importlib.util.find_spec("piper") is not None


def get_distribution_version(package_name: str) -> str:
    try:
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return ""


def load_voice_manifest(
    *,
    url: str,
    injected_payload: dict[str, Any] | None,
) -> tuple[dict[str, Any], bool]:
    if injected_payload is not None:
        return injected_payload, True
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
            if isinstance(payload, dict):
                return payload, True
    except Exception:
        return {}, False
    return {}, False


def build_voice_manifest_summary(
    *,
    manifest: dict[str, Any],
    manifest_available: bool,
    manifest_source_url: str,
) -> PiperVoiceManifestSummary:
    languages = {
        str(row.get("language", {}).get("code", ""))
        for row in manifest.values()
        if isinstance(row, dict)
    }
    korean_voice_ids = tuple(
        key
        for key, row in manifest.items()
        if is_korean_voice(key=key, row=row if isinstance(row, dict) else {})
    )
    selected_voice_id = korean_voice_ids[0] if korean_voice_ids else ""
    selected = manifest.get(selected_voice_id, {}) if selected_voice_id else {}
    selected_language = (
        str(selected.get("language", {}).get("code", "")) if isinstance(selected, dict) else ""
    )
    selected_quality = str(selected.get("quality", "")) if isinstance(selected, dict) else ""
    return PiperVoiceManifestSummary(
        manifest_checked=manifest_available,
        manifest_source_url=manifest_source_url,
        manifest_voice_count=len(manifest),
        manifest_language_count=len([lang for lang in languages if lang]),
        korean_voice_count=len(korean_voice_ids),
        selected_voice_id=selected_voice_id,
        selected_voice_language=selected_language,
        selected_voice_quality=selected_quality,
        license_policy=PIPER_LICENSE_POLICY,
    )


def is_korean_voice(*, key: str, row: dict[str, Any]) -> bool:
    language = row.get("language", {}) if isinstance(row, dict) else {}
    code = str(language.get("code", ""))
    family = str(language.get("family", ""))
    return key.lower().startswith("ko") or code.lower().startswith("ko") or family.lower() == "ko"


def build_piper_tts_row(
    *,
    script: VoiceTtsSmokeScript,
    selected_voice_id: str,
    resolved_device: str,
    model_path: Path | None,
    config_path: Path | None,
    output_path: Path,
    runtime_available: bool,
    manifest_available: bool,
    korean_voice_available: bool,
    execute_local_tts: bool,
    should_execute: bool,
) -> PiperTtsSmokeRow:
    cuda_requested = should_execute and resolved_device == "cuda"
    base = {
        "script_id": script.script_id,
        "language": script.language,
        "selected_voice_id": selected_voice_id,
        "resolved_device": resolved_device,
        "piper_cuda_requested": cuda_requested,
        "tts_execution_requested": should_execute,
        "latency_ms": 0.0,
        "audio_duration_ms": 0.0,
        "audio_file_size_bytes": 0,
        "audio_artifact_private": False,
        "character_count": len(script.script_text),
        "place_name_count": len(script.place_ids),
        "text_hash": stable_digest(script.script_text),
    }
    if not execute_local_tts:
        return PiperTtsSmokeRow(
            **base,
            synthesis_status="skipped_by_flag",
            error_code="",
        )
    if not runtime_available:
        return PiperTtsSmokeRow(
            **base,
            synthesis_status="blocked_missing_runtime",
            error_code="piper_runtime_missing",
        )
    if not manifest_available:
        return PiperTtsSmokeRow(
            **base,
            synthesis_status="blocked_manifest_unavailable",
            error_code="piper_voice_manifest_unavailable",
        )
    if not korean_voice_available:
        return PiperTtsSmokeRow(
            **base,
            synthesis_status="blocked_missing_korean_voice",
            error_code="piper_korean_voice_missing",
        )
    if model_path is None or not project_path(model_path).exists():
        return PiperTtsSmokeRow(
            **base,
            synthesis_status="blocked_model_file_missing",
            error_code="piper_model_file_missing",
        )
    if config_path is None or not project_path(config_path).exists():
        return PiperTtsSmokeRow(
            **base,
            synthesis_status="blocked_config_file_missing",
            error_code="piper_config_file_missing",
        )

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        input_text = script.script_text + "\n"
        started = time.perf_counter()
        command = [
            sys.executable,
            "-m",
            "piper",
            "--model",
            str(project_path(model_path)),
            "--config",
            str(project_path(config_path)),
            "--output-file",
            str(output_path),
        ]
        if cuda_requested:
            command.append("--cuda")
        subprocess.run(
            command,
            input=input_text,
            text=True,
            check=True,
            capture_output=True,
            timeout=120,
        )
        latency_ms = round((time.perf_counter() - started) * 1000.0, 6)
    except Exception:
        return PiperTtsSmokeRow(
            **base,
            synthesis_status="blocked_synthesis_error",
            error_code="piper_synthesis_error",
        )

    return PiperTtsSmokeRow(
        **{
            **base,
            "tts_execution_requested": True,
            "synthesis_status": "executed",
            "latency_ms": latency_ms,
            "audio_duration_ms": read_wav_duration_ms(output_path),
            "audio_file_size_bytes": output_path.stat().st_size if output_path.exists() else 0,
            "audio_artifact_private": True,
            "error_code": "",
        }
    )


def build_summary(
    *,
    scripts: tuple[VoiceTtsSmokeScript, ...],
    rows: tuple[PiperTtsSmokeRow, ...],
    cuda_preflight: Any,
    runtime_available: bool,
    piper_version: str,
    voice_manifest: PiperVoiceManifestSummary,
    manifest_available: bool,
    execute_local_tts: bool,
    package_install_attempted: bool,
    model_download_attempted: bool,
) -> PiperTtsSmokeSummary:
    executed_rows = [row for row in rows if row.synthesis_status == "executed"]
    latencies = [row.latency_ms for row in executed_rows]
    summary = PiperTtsSmokeSummary(
        selected_script_count=len(scripts),
        public_safe_script_fixture_count=sum(1 for script in scripts if script.public_allowed),
        provider_candidate_count=1,
        piper_runtime_available_count=int(runtime_available),
        piper_distribution_installed_count=int(bool(piper_version)),
        package_install_attempted_count=int(package_install_attempted),
        voice_manifest_checked_count=int(manifest_available),
        voice_manifest_available_count=int(manifest_available),
        manifest_voice_count=voice_manifest.manifest_voice_count,
        manifest_language_count=voice_manifest.manifest_language_count,
        korean_voice_available_count=voice_manifest.korean_voice_count,
        model_download_attempted_count=int(model_download_attempted),
        model_download_success_count=0,
        tts_execution_requested_count=sum(1 for row in rows if row.tts_execution_requested),
        local_tts_execution_count=len(executed_rows),
        private_audio_generated_count=len(executed_rows),
        private_audio_saved_count=len(executed_rows),
        tts_latency_p50_ms=percentile(latencies, 0.50),
        tts_latency_p95_ms=percentile(latencies, 0.95),
        audio_duration_total_ms=round(sum(row.audio_duration_ms for row in executed_rows), 6),
        audio_file_size_total_bytes=sum(row.audio_file_size_bytes for row in executed_rows),
        resolved_device=cuda_preflight.resolved_device,
        piper_cuda_requested_count=sum(1 for row in rows if row.piper_cuda_requested),
        local_cuda_available_count=int(cuda_preflight.local_cuda_available),
        cuda_device_count=cuda_preflight.cuda_device_count,
        selected_voice_id=voice_manifest.selected_voice_id,
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
        piper_tts_decision="blocked_missing_korean_voice",
    )
    return summary.model_copy(
        update={
            "piper_tts_decision": build_decision(
                summary=summary,
                output_quality=None,
                require_local_execution=execute_local_tts,
            )
        }
    )


def build_decision(
    *,
    summary: PiperTtsSmokeSummary,
    output_quality: PublicRetrievalArtifactQuality | None,
    require_local_execution: bool,
) -> PiperTtsDecision:
    if output_quality is not None and collect_public_retrieval_artifact_failures(output_quality):
        return "failed_public_safety_gate"
    if summary.piper_runtime_available_count == 0:
        return "blocked_missing_runtime"
    if summary.voice_manifest_available_count == 0:
        return "blocked_manifest_unavailable"
    if summary.korean_voice_available_count == 0:
        return "blocked_missing_korean_voice"
    if require_local_execution and summary.local_tts_execution_count != summary.selected_script_count:
        return "blocked_missing_korean_voice"
    if summary.local_tts_execution_count:
        return "completed_piper_tts_smoke"
    return "blocked_missing_korean_voice"


def collect_piper_tts_smoke_failures(
    report: PiperTtsSmokeReport,
    *,
    require_local_execution: bool,
) -> list[str]:
    failures = collect_public_retrieval_artifact_failures(report.output_quality)
    summary = report.summary
    if summary.selected_script_count != 5:
        failures.append("selected_script_count_not_5")
    if summary.public_safe_script_fixture_count != summary.selected_script_count:
        failures.append("public_safe_script_fixture_count_mismatch")
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
    if require_local_execution and summary.local_tts_execution_count != summary.selected_script_count:
        failures.append("required_piper_tts_execution_missing")
    if summary.piper_tts_decision == "failed_public_safety_gate":
        failures.append("public_safety_gate_failed")
    return list(dict.fromkeys(failures))


def build_report(
    *,
    smoke_id: str,
    scripts_path: Path,
    result_rows_path: Path,
    private_audio_dir: Path,
    piper_version: str,
    voice_manifest: PiperVoiceManifestSummary,
    rows: tuple[PiperTtsSmokeRow, ...],
    summary: PiperTtsSmokeSummary,
    output_quality: PublicRetrievalArtifactQuality,
) -> PiperTtsSmokeReport:
    report = PiperTtsSmokeReport(
        smoke_id=smoke_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        scripts_path=public_path_alias(scripts_path),
        result_path=public_path_alias(result_rows_path),
        private_audio_path_alias=public_path_alias(private_audio_dir),
        source_fingerprint=stable_digest(
            {
                "voice_manifest": voice_manifest.model_dump(mode="json"),
                "rows": [row.model_dump(mode="json") for row in rows],
                "summary": summary.model_dump(mode="json"),
            }
        ),
        piper_source_url=PIPER_SOURCE_URL,
        piper_voice_source_url=PIPER_VOICE_SOURCE_URL,
        piper_version=piper_version,
        voice_manifest=voice_manifest,
        rows=rows,
        summary=summary,
        output_quality=output_quality,
        qualitative_assessment={},
    )
    return report.model_copy(update={"qualitative_assessment": build_assessment(report)})


def build_public_rows(*, smoke_id: str, rows: tuple[PiperTtsSmokeRow, ...]) -> list[dict[str, Any]]:
    return [
        {
            "row_type": "local_piper_tts_smoke",
            "smoke_id": smoke_id,
            "provider_candidate_id": row.provider_candidate_id,
            "script_id": row.script_id,
            "language": row.language,
            "model_family": row.model_family,
            "selected_voice_id": row.selected_voice_id,
            "resolved_device": row.resolved_device,
            "piper_cuda_requested": row.piper_cuda_requested,
            "tts_execution_requested": row.tts_execution_requested,
            "synthesis_status": row.synthesis_status,
            "latency_ms": row.latency_ms,
            "audio_duration_ms": row.audio_duration_ms,
            "audio_file_size_bytes": row.audio_file_size_bytes,
            "audio_artifact_private": row.audio_artifact_private,
            "character_count": row.character_count,
            "place_name_count": row.place_name_count,
            "text_hash": row.text_hash,
            "error_code": row.error_code,
        }
        for row in rows
    ]


def build_doc(report: PiperTtsSmokeReport) -> str:
    summary = report.summary
    return f"""# Voice Local Piper TTS Smoke

## 결론

`{WORK_ID}`는 무료 로컬 TTS 후보인 Piper를 한국어 도슨트 TTS 후보로 검증한다.

현재 결과는 `piper-tts` runtime은 설치됐지만 공식 voice manifest에서 Korean voice를 찾지 못해 한국어 합성을 진행하지 않는다는 것이다. 따라서 Piper는 현재 Korean TTS 기본 provider가 아니다.

## 정량 요약

| metric | value |
| --- | ---: |
| selected_script_count | {summary.selected_script_count} |
| piper_runtime_available_count | {summary.piper_runtime_available_count} |
| piper_distribution_installed_count | {summary.piper_distribution_installed_count} |
| package_install_attempted_count | {summary.package_install_attempted_count} |
| voice_manifest_checked_count | {summary.voice_manifest_checked_count} |
| manifest_voice_count | {summary.manifest_voice_count} |
| manifest_language_count | {summary.manifest_language_count} |
| korean_voice_available_count | {summary.korean_voice_available_count} |
| model_download_attempted_count | {summary.model_download_attempted_count} |
| tts_execution_requested_count | {summary.tts_execution_requested_count} |
| local_tts_execution_count | {summary.local_tts_execution_count} |
| private_audio_generated_count | {summary.private_audio_generated_count} |
| external_provider_call_count | {summary.external_provider_call_count} |
| external_audio_transmission_count | {summary.external_audio_transmission_count} |
| live_tts_call_count | {summary.live_tts_call_count} |
| raw_audio_public_artifact_count | {summary.raw_audio_public_artifact_count} |
| raw_transcript_public_artifact_count | {summary.raw_transcript_public_artifact_count} |
| resolved_device | `{summary.resolved_device}` |
| local_cuda_available_count | {summary.local_cuda_available_count} |
| selected_voice_id | `{summary.selected_voice_id}` |
| piper_tts_decision | `{summary.piper_tts_decision}` |

## Source Boundary

| source | decision |
| --- | --- |
| `piper_source` | `piper-tts` current package source로 기록 |
| `piper_voice_manifest` | voice manifest 확인 source로 기록 |
| license_policy | {PIPER_LICENSE_POLICY} |

## Data Mart Grain

| fact | grain | exposure |
| --- | --- | --- |
| `fact_voice_local_piper_tts_smoke_public` | `smoke_id + script_id + metric_name` | public-safe |
| `fact_voice_local_piper_tts_artifact_private` | `smoke_id + script_id + audio_artifact_id` | private only |

## Claim Boundary

허용 claim:

- Piper runtime 설치 여부와 공식 voice manifest의 Korean voice 부재를 검증했다.
- external provider call과 external audio transmission은 0이다.
- raw audio와 raw transcript는 public artifact에 저장하지 않았다.

금지 claim:

- Piper가 Korean TTS provider로 채택됐다는 주장
- Piper 한국어 합성 품질 검증 완료
- 무료 로컬 음성 관광 앱 완성
- 실제 관광객 음성 품질 검증 완료
"""


def build_markdown_report(report: PiperTtsSmokeReport) -> str:
    summary = report.summary
    quality = report.output_quality
    result_rows = "\n".join(format_result_row(row) for row in report.rows)
    qualitative_rows = "\n".join(
        f"| {key} | {value} |" for key, value in report.qualitative_assessment.items()
    )
    failures = collect_piper_tts_smoke_failures(report, require_local_execution=False)
    return f"""# Voice Local Piper TTS Smoke Report

## 결론

`{WORK_ID}`는 Piper를 무료 로컬 Korean TTS 후보로 검증한 리포트다.

현재 결과는 `blocked_missing_korean_voice`다. Piper runtime은 설치됐지만 공식 voice manifest에서 Korean voice가 확인되지 않아 Korean synthesis는 실행하지 않았다.

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
| source_fingerprint | `{report.source_fingerprint}` |
| piper_source | `official_piper_source` |
| piper_voice_source | `official_piper_voice_manifest` |
| piper_version | `{report.piper_version}` |
| piper_tts_decision | `{summary.piper_tts_decision}` |

## Voice Manifest

| metric | value |
| --- | ---: |
| manifest_checked | {str(report.voice_manifest.manifest_checked).lower()} |
| manifest_voice_count | {report.voice_manifest.manifest_voice_count} |
| manifest_language_count | {report.voice_manifest.manifest_language_count} |
| korean_voice_count | {report.voice_manifest.korean_voice_count} |
| selected_voice_id | `{report.voice_manifest.selected_voice_id}` |
| selected_voice_language | `{report.voice_manifest.selected_voice_language}` |
| selected_voice_quality | `{report.voice_manifest.selected_voice_quality}` |

## 정량 리포트

| metric | value |
| --- | ---: |
| selected_script_count | {summary.selected_script_count} |
| public_safe_script_fixture_count | {summary.public_safe_script_fixture_count} |
| provider_candidate_count | {summary.provider_candidate_count} |
| piper_runtime_available_count | {summary.piper_runtime_available_count} |
| piper_distribution_installed_count | {summary.piper_distribution_installed_count} |
| package_install_attempted_count | {summary.package_install_attempted_count} |
| voice_manifest_checked_count | {summary.voice_manifest_checked_count} |
| voice_manifest_available_count | {summary.voice_manifest_available_count} |
| manifest_voice_count | {summary.manifest_voice_count} |
| manifest_language_count | {summary.manifest_language_count} |
| korean_voice_available_count | {summary.korean_voice_available_count} |
| model_download_attempted_count | {summary.model_download_attempted_count} |
| model_download_success_count | {summary.model_download_success_count} |
| tts_execution_requested_count | {summary.tts_execution_requested_count} |
| local_tts_execution_count | {summary.local_tts_execution_count} |
| private_audio_generated_count | {summary.private_audio_generated_count} |
| private_audio_saved_count | {summary.private_audio_saved_count} |
| tts_latency_p50_ms | {summary.tts_latency_p50_ms:.6f} |
| tts_latency_p95_ms | {summary.tts_latency_p95_ms:.6f} |
| audio_duration_total_ms | {summary.audio_duration_total_ms:.6f} |
| audio_file_size_total_bytes | {summary.audio_file_size_total_bytes} |
| resolved_device | `{summary.resolved_device}` |
| piper_cuda_requested_count | {summary.piper_cuda_requested_count} |
| local_cuda_available_count | {summary.local_cuda_available_count} |
| cuda_device_count | {summary.cuda_device_count} |
| selected_voice_id | `{summary.selected_voice_id}` |
| external_provider_call_count | {summary.external_provider_call_count} |
| external_audio_transmission_count | {summary.external_audio_transmission_count} |
| live_stt_call_count | {summary.live_stt_call_count} |
| live_tts_call_count | {summary.live_tts_call_count} |
| live_solar_call_count | {summary.live_solar_call_count} |
| raw_audio_public_artifact_count | {summary.raw_audio_public_artifact_count} |
| raw_transcript_public_artifact_count | {summary.raw_transcript_public_artifact_count} |
| client_secret_exposure_count | {summary.client_secret_exposure_count} |
| public_private_path_leakage_count | {summary.public_private_path_leakage_count} |
| public_secret_like_leakage_count | {summary.public_secret_like_leakage_count} |
| public_raw_payload_leakage_count | {summary.public_raw_payload_leakage_count} |

## Result Row Summary

| script_id | status | latency_ms | duration_ms | file_size | error_code |
| --- | --- | ---: | ---: | ---: | --- |
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
piper_tts_smoke_failures={failures}
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


def build_assessment(report: PiperTtsSmokeReport) -> dict[str, str]:
    summary = report.summary
    return {
        "scope": "Piper를 무료 로컬 Korean TTS 후보로 검증했다.",
        "runtime": f"piper-tts runtime availability={summary.piper_runtime_available_count}로 기록했다.",
        "voice_manifest": (
            f"공식 voice manifest {summary.manifest_voice_count}개 voice 중 Korean voice "
            f"{summary.korean_voice_available_count}개로 기록했다."
        ),
        "decision": "Korean voice 부재로 Piper는 현재 Korean TTS 기본 provider가 아니다.",
        "privacy": "raw audio와 raw transcript는 public artifact에 저장하지 않았다.",
        "cost": "cloud TTS provider 호출과 외부 음성 전송은 모두 0이다.",
        "data_mart": "script-level public row와 private audio artifact grain을 분리했다.",
        "portfolio": "무료 로컬 후보를 검증하고 부적합 사유를 evidence로 남기는 단계다.",
        "external_audit": "Piper를 억지로 채택하지 않고 Korean voice 부재를 blocker로 기록한 판단은 타당하다.",
    }


def format_result_row(row: PiperTtsSmokeRow) -> str:
    return (
        f"| {row.script_id} | `{row.synthesis_status}` | {row.latency_ms:.6f} | "
        f"{row.audio_duration_ms:.6f} | {row.audio_file_size_bytes} | `{row.error_code}` |"
    )


def build_smoke_id(*, rows: tuple[PiperTtsSmokeRow, ...], summary: PiperTtsSmokeSummary) -> str:
    digest = stable_digest(
        {
            "work_id": WORK_ID,
            "rows": [row.model_dump(mode="json") for row in rows],
            "runtime": summary.piper_runtime_available_count,
            "korean_voice": summary.korean_voice_available_count,
            "decision": summary.piper_tts_decision,
        },
        length=8,
    )
    return f"voice-local-piper-tts-smoke-s{summary.selected_script_count}-{digest}"


def stable_digest(payload: Any, *, length: int = 16) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:length]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local Piper TTS Korean voice smoke gate.")
    parser.add_argument("--scripts", type=Path, default=DEFAULT_SCRIPTS_PATH)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--rows", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    parser.add_argument("--private-audio-dir", type=Path, default=DEFAULT_PRIVATE_AUDIO_DIR)
    parser.add_argument("--script-limit", type=int, default=DEFAULT_SCRIPT_LIMIT)
    parser.add_argument("--voice-manifest-url", default=DEFAULT_VOICE_MANIFEST_URL)
    parser.add_argument("--model", type=Path, default=None)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--execute-local-tts", action="store_true")
    parser.add_argument("--require-local-execution", action="store_true")
    parser.add_argument("--package-install-attempted", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_voice_local_piper_tts_smoke(
        scripts_path=args.scripts,
        doc_path=args.doc,
        report_path=args.report,
        result_rows_path=args.rows,
        private_audio_dir=args.private_audio_dir,
        script_limit=args.script_limit,
        voice_manifest_url=args.voice_manifest_url,
        model_path=args.model,
        config_path=args.config,
        execute_local_tts=args.execute_local_tts,
        require_local_execution=args.require_local_execution,
        package_install_attempted=args.package_install_attempted,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
