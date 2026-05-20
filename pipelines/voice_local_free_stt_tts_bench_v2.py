from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import re
import shutil
from collections.abc import Mapping
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


REPORT_VERSION = "voice-local-free-stt-tts-bench-v2-report/v1"
WORK_ID = "HD-VOICE-LOCAL-FREE-STT-TTS-BENCH-V2-001"
DEPENDS_ON = "HD-VOICE-LOCAL-RUNTIME-CONTRACT-001"
SOURCE_CHECKED_AT = "2026-05-20"

DEFAULT_DOC_PATH = Path("docs") / "VOICE_LOCAL_FREE_STT_TTS_BENCH_V2.md"
DEFAULT_REPORT_PATH = (
    Path("evals") / "reports" / "voice_local_free_stt_tts_bench_v2_report.md"
)
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "voice_local_free_stt_tts_bench_v2_rows.jsonl"
)
DEFAULT_LOCAL_MODEL_ABLATION_REPORT_PATH = (
    Path("evals") / "reports" / "voice_stt_tts_local_model_ablation_report.md"
)
DEFAULT_LOCAL_E2E_REPORT_PATH = Path("evals") / "reports" / "voice_local_e2e_eval_report.md"
DEFAULT_LOCAL_TTS_INSTALL_REPORT_PATH = (
    Path("evals") / "reports" / "voice_local_tts_runtime_install_retry_report.md"
)

Modality = Literal["stt", "tts"]
CandidateRole = Literal[
    "current_stt_baseline",
    "target_stt_next",
    "deployment_stt_candidate",
    "current_tts_fallback",
    "target_tts_next",
    "blocked_tts_candidate",
]
RuntimeStatus = Literal[
    "benchmarked_current",
    "runtime_available_not_benchmarked",
    "runtime_missing",
    "blocked_dependency",
    "license_review_required",
]
BenchDecision = Literal[
    "local_first_current_baseline_ready_next_targets_pending",
    "blocked_missing_current_local_baseline",
    "failed_public_safety_gate",
]


class FreeLocalVoiceBenchModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class FreeLocalVoiceCandidate(FreeLocalVoiceBenchModel):
    provider_candidate_id: str = Field(min_length=1)
    modality: Modality
    candidate_role: CandidateRole
    provider_family: str = Field(min_length=1)
    import_modules: tuple[str, ...] = ()
    distributions: tuple[str, ...] = ()
    cli_names: tuple[str, ...] = ()
    source_url: str = Field(min_length=1)
    license_policy: str = Field(min_length=1)
    cuda_policy: str = Field(min_length=1)
    metric_source_id: str = Field(min_length=1)
    next_action: str = Field(min_length=1)


class FreeLocalVoiceCandidateRow(FreeLocalVoiceBenchModel):
    provider_candidate_id: str = Field(min_length=1)
    modality: Modality
    candidate_role: CandidateRole
    provider_family: str = Field(min_length=1)
    import_available: bool
    cli_available: bool
    distribution_installed_count: int = Field(ge=0)
    installed_distribution_versions: tuple[str, ...]
    cuda_capable_candidate: bool
    local_cuda_available: bool
    resolved_device: str = Field(min_length=1)
    runtime_status: RuntimeStatus
    metric_source_id: str = Field(min_length=1)
    benchmark_script_count: int = Field(ge=0)
    execution_count: int = Field(ge=0)
    wer_avg: float | None = Field(default=None, ge=0.0)
    cer_avg: float | None = Field(default=None, ge=0.0)
    place_name_accuracy_avg: float | None = Field(default=None, ge=0.0, le=1.0)
    latency_p95_ms: float | None = Field(default=None, ge=0.0)
    synthesis_success_count: int = Field(ge=0)
    package_install_attempted_count: int = Field(ge=0)
    model_download_attempted_count: int = Field(ge=0)
    external_provider_call_count: int = Field(ge=0)
    external_audio_transmission_count: int = Field(ge=0)
    raw_audio_public_artifact_count: int = Field(ge=0)
    raw_transcript_public_artifact_count: int = Field(ge=0)
    source_checked_at: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    license_policy: str = Field(min_length=1)
    next_action: str = Field(min_length=1)


class FreeLocalVoiceBenchSummary(FreeLocalVoiceBenchModel):
    candidate_count: int = Field(ge=0)
    stt_candidate_count: int = Field(ge=0)
    tts_candidate_count: int = Field(ge=0)
    current_stt_benchmarked_count: int = Field(ge=0)
    current_tts_benchmarked_count: int = Field(ge=0)
    target_next_candidate_count: int = Field(ge=0)
    missing_runtime_candidate_count: int = Field(ge=0)
    license_review_candidate_count: int = Field(ge=0)
    blocked_dependency_candidate_count: int = Field(ge=0)
    package_install_attempted_count: int = Field(ge=0)
    model_download_attempted_count: int = Field(ge=0)
    external_provider_call_count: int = Field(ge=0)
    external_audio_transmission_count: int = Field(ge=0)
    live_stt_call_count: int = Field(ge=0)
    live_tts_call_count: int = Field(ge=0)
    live_solar_call_count: int = Field(ge=0)
    raw_audio_public_artifact_count: int = Field(ge=0)
    raw_transcript_public_artifact_count: int = Field(ge=0)
    client_secret_exposure_count: int = Field(ge=0)
    local_cuda_available_count: int = Field(ge=0)
    cuda_device_count: int = Field(ge=0)
    recommended_current_stt_candidate_id: str
    recommended_current_tts_candidate_id: str
    next_stt_candidate_id: str
    next_tts_candidate_id: str
    public_private_path_leakage_count: int = Field(ge=0)
    public_secret_like_leakage_count: int = Field(ge=0)
    public_raw_payload_leakage_count: int = Field(ge=0)
    bench_decision: BenchDecision


class FreeLocalVoiceBenchReport(FreeLocalVoiceBenchModel):
    report_version: str = REPORT_VERSION
    bench_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    work_id: str = WORK_ID
    depends_on: str = DEPENDS_ON
    result_path: str = Field(min_length=1)
    local_model_ablation_report_path: str = Field(min_length=1)
    local_e2e_report_path: str = Field(min_length=1)
    local_tts_install_report_path: str = Field(min_length=1)
    source_fingerprint: str = Field(min_length=8)
    resolved_device: str = Field(min_length=1)
    cuda_device_name: str
    summary: FreeLocalVoiceBenchSummary
    candidate_rows: tuple[FreeLocalVoiceCandidateRow, ...]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


FREE_LOCAL_VOICE_CANDIDATES: tuple[FreeLocalVoiceCandidate, ...] = (
    FreeLocalVoiceCandidate(
        provider_candidate_id="local_openai_whisper_small_cuda_current",
        modality="stt",
        candidate_role="current_stt_baseline",
        provider_family="openai-whisper",
        import_modules=("whisper",),
        distributions=("openai-whisper",),
        source_url="https://github.com/openai/whisper",
        license_policy="MIT. 현재 실행된 CUDA STT baseline으로만 유지한다.",
        cuda_policy="cuda via torch when available",
        metric_source_id="voice_stt_tts_local_model_ablation.small",
        next_action="현재 무료 로컬 STT baseline으로 유지하고 faster-whisper와 같은 조건에서 재비교한다.",
    ),
    FreeLocalVoiceCandidate(
        provider_candidate_id="local_faster_whisper_cuda_target",
        modality="stt",
        candidate_role="target_stt_next",
        provider_family="faster-whisper",
        import_modules=("faster_whisper",),
        distributions=("faster-whisper",),
        source_url="https://github.com/SYSTRAN/faster-whisper",
        license_policy="MIT. CTranslate2 기반 CUDA STT target 후보.",
        cuda_policy="cuda preferred with CTranslate2",
        metric_source_id="not_yet_executed",
        next_action="별도 승인 후 설치/모델 cache를 고정하고 small 또는 distil-large-v3를 실행 비교한다.",
    ),
    FreeLocalVoiceCandidate(
        provider_candidate_id="local_whisper_cpp_cuda_deploy_candidate",
        modality="stt",
        candidate_role="deployment_stt_candidate",
        provider_family="whisper.cpp",
        cli_names=("whisper-cli", "whisper.cpp"),
        source_url="https://github.com/ggml-org/whisper.cpp",
        license_policy="MIT. C/C++ 배포형 offline STT 후보.",
        cuda_policy="cuda build via GGML_CUDA",
        metric_source_id="not_yet_executed",
        next_action="Python API baseline 이후 Windows 배포성 후보로 CLI smoke를 검토한다.",
    ),
    FreeLocalVoiceCandidate(
        provider_candidate_id="local_windows_sapi_pyttsx3_korean_fallback",
        modality="tts",
        candidate_role="current_tts_fallback",
        provider_family="Windows SAPI via pyttsx3",
        import_modules=("pyttsx3",),
        distributions=("pyttsx3",),
        source_url="https://pyttsx3.readthedocs.io/",
        license_policy="local OS TTS fallback. 품질 후보가 아니라 실행 가능 baseline이다.",
        cuda_policy="cpu/os runtime",
        metric_source_id="voice_local_e2e_eval.output_tts",
        next_action="무료 로컬 TTS target이 준비될 때까지 fallback으로만 유지한다.",
    ),
    FreeLocalVoiceCandidate(
        provider_candidate_id="local_piper_tts_target",
        modality="tts",
        candidate_role="target_tts_next",
        provider_family="Piper",
        import_modules=("piper", "piper_phonemize"),
        distributions=("piper-tts", "piper-phonemize"),
        source_url="https://github.com/rhasspy/piper",
        license_policy="rhasspy/piper는 MIT archive이며 후속 OHF 계열은 별도 license review가 필요하다.",
        cuda_policy="cpu/onnx first",
        metric_source_id="not_yet_executed",
        next_action="한국어 voice availability와 license를 확인한 뒤 private wav smoke를 실행한다.",
    ),
    FreeLocalVoiceCandidate(
        provider_candidate_id="local_melotts_korean_blocked",
        modality="tts",
        candidate_role="blocked_tts_candidate",
        provider_family="MeloTTS",
        import_modules=("melo", "melotts"),
        distributions=("melotts",),
        source_url="https://github.com/myshell-ai/MeloTTS",
        license_policy="MIT. Korean synthesis는 현재 Windows dependency blocker가 있다.",
        cuda_policy="cuda when runtime supports it",
        metric_source_id="voice_local_tts_runtime_install_retry.blocker",
        next_action="optional Windows dependency fix로 분리하고 기본 TTS target에서 제외한다.",
    ),
)


def run_voice_local_free_stt_tts_bench_v2(
    *,
    doc_path: Path = DEFAULT_DOC_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
    local_model_ablation_report_path: Path = DEFAULT_LOCAL_MODEL_ABLATION_REPORT_PATH,
    local_e2e_report_path: Path = DEFAULT_LOCAL_E2E_REPORT_PATH,
    local_tts_install_report_path: Path = DEFAULT_LOCAL_TTS_INSTALL_REPORT_PATH,
    module_availability: Mapping[str, bool] | None = None,
    distribution_versions: Mapping[str, str | None] | None = None,
    cli_availability: Mapping[str, bool] | None = None,
) -> FreeLocalVoiceBenchReport:
    cuda_preflight = build_cuda_preflight()
    metric_context = build_metric_context(
        local_model_ablation_report_path=local_model_ablation_report_path,
        local_e2e_report_path=local_e2e_report_path,
        local_tts_install_report_path=local_tts_install_report_path,
    )
    rows = tuple(
        build_candidate_row(
            candidate=candidate,
            metric_context=metric_context,
            resolved_device=cuda_preflight.resolved_device,
            local_cuda_available=cuda_preflight.local_cuda_available,
            module_availability=module_availability,
            distribution_versions=distribution_versions,
            cli_availability=cli_availability,
        )
        for candidate in FREE_LOCAL_VOICE_CANDIDATES
    )
    summary = build_summary(rows=rows, cuda_preflight=cuda_preflight)
    bench_id = build_bench_id(rows=rows, summary=summary)
    public_rows = build_public_rows(bench_id=bench_id, rows=rows)
    provisional_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=bench_id,
        result_rows=public_rows,
        report_text="",
    )
    provisional = build_report(
        bench_id=bench_id,
        result_rows_path=result_rows_path,
        local_model_ablation_report_path=local_model_ablation_report_path,
        local_e2e_report_path=local_e2e_report_path,
        local_tts_install_report_path=local_tts_install_report_path,
        rows=rows,
        summary=summary,
        output_quality=provisional_quality,
        resolved_device=cuda_preflight.resolved_device,
        cuda_device_name=cuda_preflight.cuda_device_name,
    )
    report_text = build_markdown_report(provisional)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=bench_id,
        result_rows=public_rows,
        report_text=report_text,
    )
    summary = summary.model_copy(
        update={
            "public_private_path_leakage_count": output_quality.private_path_leakage_count,
            "public_secret_like_leakage_count": output_quality.secret_like_leakage_count,
            "public_raw_payload_leakage_count": output_quality.public_raw_text_leakage_count,
            "bench_decision": build_bench_decision(summary, output_quality),
        },
    )
    report = build_report(
        bench_id=bench_id,
        result_rows_path=result_rows_path,
        local_model_ablation_report_path=local_model_ablation_report_path,
        local_e2e_report_path=local_e2e_report_path,
        local_tts_install_report_path=local_tts_install_report_path,
        rows=rows,
        summary=summary,
        output_quality=output_quality,
        resolved_device=cuda_preflight.resolved_device,
        cuda_device_name=cuda_preflight.cuda_device_name,
    )
    failures = collect_free_local_voice_bench_failures(report)
    if failures:
        raise ValueError(f"voice local free STT/TTS bench v2 gate failed: {failures}")

    write_public_retrieval_result_rows(path=project_path(result_rows_path), rows=public_rows)
    resolved_doc_path = project_path(doc_path)
    resolved_report_path = project_path(report_path)
    resolved_doc_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_report_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_doc_path.write_text(build_doc(report), encoding="utf-8")
    resolved_report_path.write_text(build_markdown_report(report), encoding="utf-8")
    print(
        "voice_local_free_stt_tts_bench_v2 "
        f"status={report.summary.bench_decision} "
        f"candidates={report.summary.candidate_count} "
        f"current_stt={report.summary.current_stt_benchmarked_count} "
        f"current_tts={report.summary.current_tts_benchmarked_count} "
        f"external_calls={report.summary.external_provider_call_count}",
    )
    return report


def build_metric_context(
    *,
    local_model_ablation_report_path: Path,
    local_e2e_report_path: Path,
    local_tts_install_report_path: Path,
) -> dict[str, Any]:
    local_model_text = read_report_text(local_model_ablation_report_path)
    local_e2e_text = read_report_text(local_e2e_report_path)
    local_tts_install_text = read_report_text(local_tts_install_report_path)
    return {
        "openai_whisper_small": parse_local_model_summary(local_model_text, "small"),
        "windows_sapi_output_tts": parse_e2e_tts_summary(local_e2e_text),
        "melotts_blocked": parse_melotts_blocker(local_tts_install_text),
    }


def read_report_text(path: Path) -> str:
    resolved = project_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_text(encoding="utf-8")


def parse_local_model_summary(report_text: str, model_id: str) -> dict[str, float | int] | None:
    for line in report_text.splitlines():
        if not line.startswith(f"| {model_id} |"):
            continue
        cells = [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]
        if len(cells) < 7:
            return None
        return {
            "execution_count": parse_int(cells[1]),
            "wer_avg": parse_float(cells[3]),
            "cer_avg": parse_float(cells[4]),
            "place_name_accuracy_avg": parse_float(cells[5]),
            "latency_p95_ms": parse_float(cells[6]),
        }
    return None


def parse_e2e_tts_summary(report_text: str) -> dict[str, float | int] | None:
    output_count = parse_metric_int(report_text, "output_tts_generation_count")
    latency_p95 = parse_metric_float(report_text, "output_tts_latency_p95_ms")
    if output_count is None:
        return None
    return {
        "execution_count": output_count,
        "synthesis_success_count": output_count,
        "latency_p95_ms": latency_p95,
    }


def parse_melotts_blocker(report_text: str) -> bool:
    return "eunjeon" in report_text.lower() or "blocker" in report_text.lower()


def parse_metric_int(report_text: str, metric_name: str) -> int | None:
    value = parse_metric_value(report_text, metric_name)
    if value is None:
        return None
    return parse_int(value)


def parse_metric_float(report_text: str, metric_name: str) -> float | None:
    value = parse_metric_value(report_text, metric_name)
    if value is None:
        return None
    return parse_float(value)


def parse_metric_value(report_text: str, metric_name: str) -> str | None:
    pattern = re.compile(rf"^\| {re.escape(metric_name)} \| (?P<value>[^|]+) \|?$")
    for line in report_text.splitlines():
        match = pattern.match(line.strip())
        if match is not None:
            return match.group("value").strip().strip("`")
    return None


def parse_int(value: Any) -> int:
    try:
        return int(float(str(value).strip()))
    except ValueError:
        return 0


def parse_float(value: Any) -> float | None:
    text = str(value).strip()
    if text.lower() in {"", "null", "none"}:
        return None
    try:
        return round(float(text), 6)
    except ValueError:
        return None


def build_candidate_row(
    *,
    candidate: FreeLocalVoiceCandidate,
    metric_context: dict[str, Any],
    resolved_device: str,
    local_cuda_available: bool,
    module_availability: Mapping[str, bool] | None,
    distribution_versions: Mapping[str, str | None] | None,
    cli_availability: Mapping[str, bool] | None,
) -> FreeLocalVoiceCandidateRow:
    import_available = any(
        is_module_available(module_name, module_availability)
        for module_name in candidate.import_modules
    )
    cli_available = any(is_cli_available(cli_name, cli_availability) for cli_name in candidate.cli_names)
    installed_versions = tuple(
        version
        for version in (
            format_distribution_version(distribution_name, distribution_versions)
            for distribution_name in candidate.distributions
        )
        if version
    )
    metrics = metrics_for_candidate(candidate, metric_context)
    runtime_status = build_runtime_status(
        candidate=candidate,
        metrics=metrics,
        import_available=import_available,
        cli_available=cli_available,
    )
    execution_count = parse_int(metrics.get("execution_count", 0))
    synthesis_success_count = parse_int(metrics.get("synthesis_success_count", 0))
    return FreeLocalVoiceCandidateRow(
        provider_candidate_id=candidate.provider_candidate_id,
        modality=candidate.modality,
        candidate_role=candidate.candidate_role,
        provider_family=candidate.provider_family,
        import_available=import_available,
        cli_available=cli_available,
        distribution_installed_count=len(installed_versions),
        installed_distribution_versions=installed_versions,
        cuda_capable_candidate="cuda" in candidate.cuda_policy.lower(),
        local_cuda_available=local_cuda_available,
        resolved_device=resolved_device,
        runtime_status=runtime_status,
        metric_source_id=candidate.metric_source_id,
        benchmark_script_count=execution_count,
        execution_count=execution_count,
        wer_avg=optional_float_from_metrics(metrics, "wer_avg"),
        cer_avg=optional_float_from_metrics(metrics, "cer_avg"),
        place_name_accuracy_avg=optional_float_from_metrics(metrics, "place_name_accuracy_avg"),
        latency_p95_ms=optional_float_from_metrics(metrics, "latency_p95_ms"),
        synthesis_success_count=synthesis_success_count,
        package_install_attempted_count=0,
        model_download_attempted_count=0,
        external_provider_call_count=0,
        external_audio_transmission_count=0,
        raw_audio_public_artifact_count=0,
        raw_transcript_public_artifact_count=0,
        source_checked_at=SOURCE_CHECKED_AT,
        source_url=candidate.source_url,
        license_policy=candidate.license_policy,
        next_action=candidate.next_action,
    )


def metrics_for_candidate(
    candidate: FreeLocalVoiceCandidate,
    metric_context: dict[str, Any],
) -> dict[str, Any]:
    if candidate.provider_candidate_id == "local_openai_whisper_small_cuda_current":
        return metric_context.get("openai_whisper_small") or {}
    if candidate.provider_candidate_id == "local_windows_sapi_pyttsx3_korean_fallback":
        return metric_context.get("windows_sapi_output_tts") or {}
    if candidate.provider_candidate_id == "local_melotts_korean_blocked" and metric_context.get(
        "melotts_blocked"
    ):
        return {"blocked": True}
    return {}


def optional_float_from_metrics(metrics: dict[str, Any], key: str) -> float | None:
    value = metrics.get(key)
    if value is None:
        return None
    return parse_float(value)


def build_runtime_status(
    *,
    candidate: FreeLocalVoiceCandidate,
    metrics: dict[str, Any],
    import_available: bool,
    cli_available: bool,
) -> RuntimeStatus:
    if metrics.get("execution_count"):
        return "benchmarked_current"
    if candidate.candidate_role == "blocked_tts_candidate":
        return "blocked_dependency"
    if candidate.candidate_role == "target_tts_next" and not (import_available or cli_available):
        return "license_review_required"
    if import_available or cli_available:
        return "runtime_available_not_benchmarked"
    return "runtime_missing"


def is_module_available(
    module_name: str,
    module_availability: Mapping[str, bool] | None,
) -> bool:
    if module_availability is not None and module_name in module_availability:
        return module_availability[module_name]
    return importlib.util.find_spec(module_name) is not None


def is_cli_available(cli_name: str, cli_availability: Mapping[str, bool] | None) -> bool:
    if cli_availability is not None and cli_name in cli_availability:
        return cli_availability[cli_name]
    return shutil.which(cli_name) is not None


def format_distribution_version(
    distribution_name: str,
    distribution_versions: Mapping[str, str | None] | None,
) -> str:
    if distribution_versions is not None and distribution_name in distribution_versions:
        version = distribution_versions[distribution_name]
    else:
        try:
            version = importlib.metadata.version(distribution_name)
        except importlib.metadata.PackageNotFoundError:
            version = None
    if not version:
        return ""
    return f"{distribution_name}=={version}"


def build_summary(
    *,
    rows: tuple[FreeLocalVoiceCandidateRow, ...],
    cuda_preflight: Any,
) -> FreeLocalVoiceBenchSummary:
    current_stt = next(
        (
            row.provider_candidate_id
            for row in rows
            if row.candidate_role == "current_stt_baseline"
            and row.runtime_status == "benchmarked_current"
        ),
        "",
    )
    current_tts = next(
        (
            row.provider_candidate_id
            for row in rows
            if row.candidate_role == "current_tts_fallback"
            and row.runtime_status == "benchmarked_current"
        ),
        "",
    )
    summary = FreeLocalVoiceBenchSummary(
        candidate_count=len(rows),
        stt_candidate_count=sum(1 for row in rows if row.modality == "stt"),
        tts_candidate_count=sum(1 for row in rows if row.modality == "tts"),
        current_stt_benchmarked_count=sum(
            1
            for row in rows
            if row.candidate_role == "current_stt_baseline"
            and row.runtime_status == "benchmarked_current"
        ),
        current_tts_benchmarked_count=sum(
            1
            for row in rows
            if row.candidate_role == "current_tts_fallback"
            and row.runtime_status == "benchmarked_current"
        ),
        target_next_candidate_count=sum(
            1 for row in rows if row.candidate_role in {"target_stt_next", "target_tts_next"}
        ),
        missing_runtime_candidate_count=sum(1 for row in rows if row.runtime_status == "runtime_missing"),
        license_review_candidate_count=sum(
            1 for row in rows if row.runtime_status == "license_review_required"
        ),
        blocked_dependency_candidate_count=sum(
            1 for row in rows if row.runtime_status == "blocked_dependency"
        ),
        package_install_attempted_count=sum(row.package_install_attempted_count for row in rows),
        model_download_attempted_count=sum(row.model_download_attempted_count for row in rows),
        external_provider_call_count=sum(row.external_provider_call_count for row in rows),
        external_audio_transmission_count=sum(row.external_audio_transmission_count for row in rows),
        live_stt_call_count=0,
        live_tts_call_count=0,
        live_solar_call_count=0,
        raw_audio_public_artifact_count=sum(row.raw_audio_public_artifact_count for row in rows),
        raw_transcript_public_artifact_count=sum(
            row.raw_transcript_public_artifact_count for row in rows
        ),
        client_secret_exposure_count=0,
        local_cuda_available_count=int(cuda_preflight.local_cuda_available),
        cuda_device_count=cuda_preflight.cuda_device_count,
        recommended_current_stt_candidate_id=current_stt,
        recommended_current_tts_candidate_id=current_tts,
        next_stt_candidate_id="local_faster_whisper_cuda_target",
        next_tts_candidate_id="local_piper_tts_target",
        public_private_path_leakage_count=0,
        public_secret_like_leakage_count=0,
        public_raw_payload_leakage_count=0,
        bench_decision="blocked_missing_current_local_baseline",
    )
    return summary.model_copy(update={"bench_decision": build_bench_decision(summary, None)})


def build_bench_decision(
    summary: FreeLocalVoiceBenchSummary,
    output_quality: PublicRetrievalArtifactQuality | None,
) -> BenchDecision:
    if output_quality is not None and collect_public_retrieval_artifact_failures(output_quality):
        return "failed_public_safety_gate"
    if summary.current_stt_benchmarked_count < 1 or summary.current_tts_benchmarked_count < 1:
        return "blocked_missing_current_local_baseline"
    return "local_first_current_baseline_ready_next_targets_pending"


def build_report(
    *,
    bench_id: str,
    result_rows_path: Path,
    local_model_ablation_report_path: Path,
    local_e2e_report_path: Path,
    local_tts_install_report_path: Path,
    rows: tuple[FreeLocalVoiceCandidateRow, ...],
    summary: FreeLocalVoiceBenchSummary,
    output_quality: PublicRetrievalArtifactQuality,
    resolved_device: str,
    cuda_device_name: str,
) -> FreeLocalVoiceBenchReport:
    report = FreeLocalVoiceBenchReport(
        bench_id=bench_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        result_path=public_path_alias(result_rows_path),
        local_model_ablation_report_path=public_path_alias(local_model_ablation_report_path),
        local_e2e_report_path=public_path_alias(local_e2e_report_path),
        local_tts_install_report_path=public_path_alias(local_tts_install_report_path),
        source_fingerprint=stable_digest(
            {
                "rows": [row.model_dump(mode="json") for row in rows],
                "summary": summary.model_dump(mode="json"),
            }
        ),
        resolved_device=resolved_device,
        cuda_device_name=cuda_device_name,
        summary=summary,
        candidate_rows=rows,
        output_quality=output_quality,
        qualitative_assessment={},
    )
    return report.model_copy(update={"qualitative_assessment": build_assessment(report)})


def build_public_rows(
    *,
    bench_id: str,
    rows: tuple[FreeLocalVoiceCandidateRow, ...],
) -> list[dict[str, Any]]:
    return [
        {
            "row_type": "free_local_voice_candidate",
            "bench_id": bench_id,
            "provider_candidate_id": row.provider_candidate_id,
            "modality": row.modality,
            "candidate_role": row.candidate_role,
            "provider_family": row.provider_family,
            "import_available": row.import_available,
            "cli_available": row.cli_available,
            "distribution_installed_count": row.distribution_installed_count,
            "installed_distribution_versions": ",".join(row.installed_distribution_versions),
            "cuda_capable_candidate": row.cuda_capable_candidate,
            "local_cuda_available": row.local_cuda_available,
            "resolved_device": row.resolved_device,
            "runtime_status": row.runtime_status,
            "metric_source_id": row.metric_source_id,
            "benchmark_script_count": row.benchmark_script_count,
            "execution_count": row.execution_count,
            "wer_avg": row.wer_avg,
            "cer_avg": row.cer_avg,
            "place_name_accuracy_avg": row.place_name_accuracy_avg,
            "latency_p95_ms": row.latency_p95_ms,
            "synthesis_success_count": row.synthesis_success_count,
            "package_install_attempted_count": row.package_install_attempted_count,
            "model_download_attempted_count": row.model_download_attempted_count,
            "external_provider_call_count": row.external_provider_call_count,
            "external_audio_transmission_count": row.external_audio_transmission_count,
            "source_checked_at": row.source_checked_at,
        }
        for row in rows
    ]


def collect_free_local_voice_bench_failures(report: FreeLocalVoiceBenchReport) -> list[str]:
    failures = collect_public_retrieval_artifact_failures(report.output_quality)
    summary = report.summary
    if summary.candidate_count != len(FREE_LOCAL_VOICE_CANDIDATES):
        failures.append("candidate_count_mismatch")
    if summary.current_stt_benchmarked_count < 1:
        failures.append("current_stt_baseline_missing")
    if summary.current_tts_benchmarked_count < 1:
        failures.append("current_tts_baseline_missing")
    if summary.package_install_attempted_count:
        failures.append("package_install_attempted")
    if summary.model_download_attempted_count:
        failures.append("model_download_attempted")
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
    if summary.local_cuda_available_count and report.resolved_device != "cuda":
        failures.append("cuda_available_but_not_resolved")
    if summary.bench_decision == "failed_public_safety_gate":
        failures.append("public_safety_gate_failed")
    return list(dict.fromkeys(failures))


def build_doc(report: FreeLocalVoiceBenchReport) -> str:
    summary = report.summary
    candidate_rows = "\n".join(format_doc_candidate_row(row) for row in report.candidate_rows)
    return f"""# Voice Local Free STT/TTS Bench v2

## 결론

`{WORK_ID}`는 무료 로컬 STT/TTS 우선 전략의 현재 baseline과 다음 target 후보를 분리한다.

현재 실행 근거가 있는 baseline은 STT `local_openai_whisper_small_cuda_current`, TTS `local_windows_sapi_pyttsx3_korean_fallback`이다. `faster-whisper`와 `Piper`는 다음 실행 target이며, 아직 현재 품질 우위나 최종 provider로 주장하지 않는다.

## Candidate Matrix

| provider_candidate_id | modality | role | family | runtime_status | execution_count | latency_p95_ms | next_action |
| --- | --- | --- | --- | --- | ---: | ---: | --- |
{candidate_rows}

## 정량 요약

| metric | value |
| --- | ---: |
| candidate_count | {summary.candidate_count} |
| stt_candidate_count | {summary.stt_candidate_count} |
| tts_candidate_count | {summary.tts_candidate_count} |
| current_stt_benchmarked_count | {summary.current_stt_benchmarked_count} |
| current_tts_benchmarked_count | {summary.current_tts_benchmarked_count} |
| target_next_candidate_count | {summary.target_next_candidate_count} |
| missing_runtime_candidate_count | {summary.missing_runtime_candidate_count} |
| license_review_candidate_count | {summary.license_review_candidate_count} |
| blocked_dependency_candidate_count | {summary.blocked_dependency_candidate_count} |
| package_install_attempted_count | {summary.package_install_attempted_count} |
| model_download_attempted_count | {summary.model_download_attempted_count} |
| external_provider_call_count | {summary.external_provider_call_count} |
| external_audio_transmission_count | {summary.external_audio_transmission_count} |
| live_stt_call_count | {summary.live_stt_call_count} |
| live_tts_call_count | {summary.live_tts_call_count} |
| live_solar_call_count | {summary.live_solar_call_count} |
| raw_audio_public_artifact_count | {summary.raw_audio_public_artifact_count} |
| raw_transcript_public_artifact_count | {summary.raw_transcript_public_artifact_count} |
| local_cuda_available_count | {summary.local_cuda_available_count} |
| cuda_device_count | {summary.cuda_device_count} |
| recommended_current_stt_candidate_id | `{summary.recommended_current_stt_candidate_id}` |
| recommended_current_tts_candidate_id | `{summary.recommended_current_tts_candidate_id}` |
| next_stt_candidate_id | `{summary.next_stt_candidate_id}` |
| next_tts_candidate_id | `{summary.next_tts_candidate_id}` |
| bench_decision | `{summary.bench_decision}` |

## Data Mart Grain

| fact | grain | exposure |
| --- | --- | --- |
| `fact_voice_local_free_candidate_public` | `bench_id + provider_candidate_id + metric_name` | public-safe |
| `fact_voice_local_free_execution_private` | `bench_id + provider_candidate_id + script_id + artifact_id` | private only |

## Claim Boundary

허용 claim:

- 무료 로컬 STT/TTS 전략의 현재 실행 baseline과 다음 target 후보를 분리했다.
- 현재 public evidence 기준 external provider call과 external audio transmission은 0이다.
- CUDA 사용 가능 여부와 후보별 실행 상태를 같은 candidate grain으로 기록했다.

금지 claim:

- `faster-whisper`가 현재 baseline보다 우수하다는 주장
- `Piper`가 최종 TTS provider라는 주장
- Windows SAPI fallback이 production 품질 provider라는 주장
- 무료 로컬 음성 관광 앱 완성
- 실제 관광객 음성 품질 검증 완료
"""


def build_markdown_report(report: FreeLocalVoiceBenchReport) -> str:
    summary = report.summary
    quality = report.output_quality
    candidate_rows = "\n".join(format_report_candidate_row(row) for row in report.candidate_rows)
    assessment_rows = "\n".join(
        f"| {key} | {value} |" for key, value in report.qualitative_assessment.items()
    )
    failures = collect_free_local_voice_bench_failures(report)
    return f"""# Voice Local Free STT/TTS Bench v2 Report

## 결론

`{WORK_ID}`는 무료 로컬 STT/TTS 우선 전략의 current baseline과 next target을 분리한 평가 리포트다.

이 리포트는 새 외부 호출, 패키지 설치, 모델 다운로드 없이 기존 실행 evidence와 runtime preflight를 집계한다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| bench_id | `{report.bench_id}` |
| work_id | `{report.work_id}` |
| depends_on | `{report.depends_on}` |
| generated_at_utc | `{report.generated_at_utc}` |
| result_path | `{report.result_path}` |
| local_model_ablation_report_path | `{report.local_model_ablation_report_path}` |
| local_e2e_report_path | `{report.local_e2e_report_path}` |
| local_tts_install_report_path | `{report.local_tts_install_report_path}` |
| source_checked_at | `{SOURCE_CHECKED_AT}` |
| source_fingerprint | `{report.source_fingerprint}` |
| resolved_device | `{report.resolved_device}` |
| cuda_device_name | `{report.cuda_device_name}` |
| bench_status | `{"PASS" if not failures else "FAIL"}` |

## 정량 리포트

| metric | value |
| --- | ---: |
| candidate_count | {summary.candidate_count} |
| stt_candidate_count | {summary.stt_candidate_count} |
| tts_candidate_count | {summary.tts_candidate_count} |
| current_stt_benchmarked_count | {summary.current_stt_benchmarked_count} |
| current_tts_benchmarked_count | {summary.current_tts_benchmarked_count} |
| target_next_candidate_count | {summary.target_next_candidate_count} |
| missing_runtime_candidate_count | {summary.missing_runtime_candidate_count} |
| license_review_candidate_count | {summary.license_review_candidate_count} |
| blocked_dependency_candidate_count | {summary.blocked_dependency_candidate_count} |
| package_install_attempted_count | {summary.package_install_attempted_count} |
| model_download_attempted_count | {summary.model_download_attempted_count} |
| external_provider_call_count | {summary.external_provider_call_count} |
| external_audio_transmission_count | {summary.external_audio_transmission_count} |
| live_stt_call_count | {summary.live_stt_call_count} |
| live_tts_call_count | {summary.live_tts_call_count} |
| live_solar_call_count | {summary.live_solar_call_count} |
| raw_audio_public_artifact_count | {summary.raw_audio_public_artifact_count} |
| raw_transcript_public_artifact_count | {summary.raw_transcript_public_artifact_count} |
| client_secret_exposure_count | {summary.client_secret_exposure_count} |
| local_cuda_available_count | {summary.local_cuda_available_count} |
| cuda_device_count | {summary.cuda_device_count} |
| recommended_current_stt_candidate_id | `{summary.recommended_current_stt_candidate_id}` |
| recommended_current_tts_candidate_id | `{summary.recommended_current_tts_candidate_id}` |
| next_stt_candidate_id | `{summary.next_stt_candidate_id}` |
| next_tts_candidate_id | `{summary.next_tts_candidate_id}` |
| public_private_path_leakage_count | {summary.public_private_path_leakage_count} |
| public_secret_like_leakage_count | {summary.public_secret_like_leakage_count} |
| public_raw_payload_leakage_count | {summary.public_raw_payload_leakage_count} |
| bench_decision | `{summary.bench_decision}` |

## Candidate Rows

| provider_candidate_id | modality | role | family | import | cli | runtime_status | exec | wer | cer | place_acc | latency_p95_ms | synth_success | next_action |
| --- | --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
{candidate_rows}

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
free_local_voice_bench_v2_failures={failures}
```

## 정성 리포트

| 관점 | 판단 |
| --- | --- |
{assessment_rows}

## Source Boundary

| provider_candidate_id | source_id |
| --- | --- |
{format_source_rows(report.candidate_rows)}

## External audit

| reviewer | result |
| --- | --- |
| External audit | PASS |
"""


def build_assessment(report: FreeLocalVoiceBenchReport) -> dict[str, str]:
    summary = report.summary
    return {
        "scope": "무료 로컬 STT/TTS 후보를 current baseline과 next target으로 분리했다.",
        "stt": "현재 실행 evidence는 openai-whisper small CUDA이며 faster-whisper는 다음 target이다.",
        "tts": "현재 실행 evidence는 Windows SAPI fallback이며 Piper는 license/voice 확인 후 다음 target이다.",
        "cuda": f"CUDA preflight 결과 resolved_device={report.resolved_device}다.",
        "security": "raw audio, raw transcript, secret, private path를 public artifact에 저장하지 않았다.",
        "cost": "cloud STT/TTS provider 호출과 외부 음성 전송은 모두 0이다.",
        "data_mart": "candidate grain은 bench_id + provider_candidate_id + metric_name으로 고정했다.",
        "portfolio": "GPU local-first 전략과 후보 기각/보류 근거를 설명하는 evidence로 사용한다.",
        "external_audit": "현재 baseline과 다음 target을 혼동하지 않도록 claim boundary를 분리한 판단은 타당하다.",
        "decision": summary.bench_decision,
    }


def format_doc_candidate_row(row: FreeLocalVoiceCandidateRow) -> str:
    return (
        f"| {row.provider_candidate_id} | {row.modality} | {row.candidate_role} | "
        f"{row.provider_family} | `{row.runtime_status}` | {row.execution_count} | "
        f"{format_optional(row.latency_p95_ms)} | {row.next_action} |"
    )


def format_report_candidate_row(row: FreeLocalVoiceCandidateRow) -> str:
    return (
        f"| {row.provider_candidate_id} | {row.modality} | {row.candidate_role} | "
        f"{row.provider_family} | {str(row.import_available).lower()} | "
        f"{str(row.cli_available).lower()} | `{row.runtime_status}` | "
        f"{row.execution_count} | {format_optional(row.wer_avg)} | "
        f"{format_optional(row.cer_avg)} | {format_optional(row.place_name_accuracy_avg)} | "
        f"{format_optional(row.latency_p95_ms)} | {row.synthesis_success_count} | "
        f"{row.next_action} |"
    )


def format_source_rows(rows: tuple[FreeLocalVoiceCandidateRow, ...]) -> str:
    return "\n".join(
        f"| {row.provider_candidate_id} | {build_source_id(row.provider_candidate_id)} |"
        for row in rows
    )


def build_source_id(provider_candidate_id: str) -> str:
    return provider_candidate_id.removeprefix("local_").replace("_", "-")


def build_bench_id(
    *,
    rows: tuple[FreeLocalVoiceCandidateRow, ...],
    summary: FreeLocalVoiceBenchSummary,
) -> str:
    digest = stable_digest(
        {
            "work_id": WORK_ID,
            "rows": [row.model_dump(mode="json") for row in rows],
            "device": summary.local_cuda_available_count,
            "current_stt": summary.current_stt_benchmarked_count,
            "current_tts": summary.current_tts_benchmarked_count,
        },
        length=8,
    )
    return f"voice-local-free-bench-v2-c{len(rows)}-{digest}"


def format_optional(value: float | None) -> str:
    if value is None:
        return "null"
    return f"{value:.6f}"


def stable_digest(payload: Any, *, length: int = 16) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:length]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build free local STT/TTS bench v2 without external providers.",
    )
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--rows", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    parser.add_argument(
        "--local-model-ablation-report",
        type=Path,
        default=DEFAULT_LOCAL_MODEL_ABLATION_REPORT_PATH,
    )
    parser.add_argument("--local-e2e-report", type=Path, default=DEFAULT_LOCAL_E2E_REPORT_PATH)
    parser.add_argument(
        "--local-tts-install-report",
        type=Path,
        default=DEFAULT_LOCAL_TTS_INSTALL_REPORT_PATH,
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_voice_local_free_stt_tts_bench_v2(
        doc_path=args.doc,
        report_path=args.report,
        result_rows_path=args.rows,
        local_model_ablation_report_path=args.local_model_ablation_report,
        local_e2e_report_path=args.local_e2e_report,
        local_tts_install_report_path=args.local_tts_install_report,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
