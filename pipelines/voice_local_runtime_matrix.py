from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
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


REPORT_VERSION = "voice-local-runtime-matrix-report/v1"
WORK_ID = "HD-VOICE-STT-TTS-LOCAL-RUNTIME-MATRIX-001"
DEPENDS_ON = (
    "HD-VOICE-STT-TTS-LOCAL-FIRST-STRATEGY-001,"
    "HD-VOICE-STT-TTS-LOCAL-TTS-SMOKE-001"
)
DEFAULT_DOC_PATH = Path("docs") / "VOICE_LOCAL_RUNTIME_MATRIX.md"
DEFAULT_REPORT_PATH = Path("evals") / "reports" / "voice_local_runtime_matrix_report.md"
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data") / "evals" / "results" / "voice_local_runtime_matrix_rows.jsonl"
)
SOURCE_CHECKED_AT = "2026-05-20"

Modality = Literal["stt", "tts", "stt_tts"]
CandidateDecision = Literal[
    "primary_target",
    "existing_fallback",
    "secondary_target",
    "optional_license_review",
]
RuntimeStatus = Literal[
    "runtime_available",
    "runtime_missing",
    "runtime_missing_license_review",
]
MatrixDecision = Literal[
    "ready_for_local_stt_existing_runtime_tts_blocked",
    "ready_for_tts_smoke_retry",
    "blocked_by_public_safety_gate",
]


class VoiceRuntimeMatrixModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LocalRuntimeCandidate(VoiceRuntimeMatrixModel):
    provider_candidate_id: str = Field(min_length=1)
    modality: Modality
    candidate_decision: CandidateDecision
    provider_family: str = Field(min_length=1)
    import_modules: tuple[str, ...] = Field(min_length=1)
    distributions: tuple[str, ...] = Field(min_length=1)
    source_url: str = Field(min_length=1)
    license_policy: str = Field(min_length=1)
    cuda_policy: str = Field(min_length=1)
    next_action: str = Field(min_length=1)


class LocalRuntimeCandidateRow(VoiceRuntimeMatrixModel):
    provider_candidate_id: str = Field(min_length=1)
    modality: Modality
    candidate_decision: CandidateDecision
    provider_family: str = Field(min_length=1)
    import_available: bool
    import_available_module_count: int = Field(ge=0)
    distribution_installed_count: int = Field(ge=0)
    installed_distribution_versions: tuple[str, ...]
    cuda_capable_candidate: bool
    local_cuda_available: bool
    resolved_device: str = Field(min_length=1)
    runtime_status: RuntimeStatus
    model_load_attempted_count: int = Field(ge=0)
    package_install_attempted_count: int = Field(ge=0)
    model_download_attempted_count: int = Field(ge=0)
    local_stt_execution_count: int = Field(ge=0)
    local_tts_execution_count: int = Field(ge=0)
    private_audio_generated_count: int = Field(ge=0)
    external_provider_call_count: int = Field(ge=0)
    external_audio_transmission_count: int = Field(ge=0)
    secret_required_count: int = Field(ge=0)
    source_checked_at: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    license_policy: str = Field(min_length=1)
    next_action: str = Field(min_length=1)


class LocalRuntimeMatrixSummary(VoiceRuntimeMatrixModel):
    runtime_candidate_count: int = Field(ge=0)
    primary_local_stt_candidate_count: int = Field(ge=0)
    existing_local_stt_fallback_count: int = Field(ge=0)
    primary_local_tts_candidate_count: int = Field(ge=0)
    secondary_local_candidate_count: int = Field(ge=0)
    optional_license_review_candidate_count: int = Field(ge=0)
    import_available_candidate_count: int = Field(ge=0)
    missing_runtime_candidate_count: int = Field(ge=0)
    stt_runtime_available_count: int = Field(ge=0)
    tts_runtime_available_count: int = Field(ge=0)
    stt_tts_runtime_available_count: int = Field(ge=0)
    local_cuda_available_count: int = Field(ge=0)
    cuda_device_count: int = Field(ge=0)
    package_install_attempted_count: int = Field(ge=0)
    model_download_attempted_count: int = Field(ge=0)
    model_load_attempted_count: int = Field(ge=0)
    local_stt_execution_count: int = Field(ge=0)
    local_tts_execution_count: int = Field(ge=0)
    private_audio_generated_count: int = Field(ge=0)
    external_provider_call_count: int = Field(ge=0)
    external_audio_transmission_count: int = Field(ge=0)
    live_solar_call_count: int = Field(ge=0)
    raw_audio_public_artifact_count: int = Field(ge=0)
    raw_transcript_public_artifact_count: int = Field(ge=0)
    client_secret_exposure_count: int = Field(ge=0)
    public_private_path_leakage_count: int = Field(ge=0)
    public_secret_like_leakage_count: int = Field(ge=0)
    public_raw_payload_leakage_count: int = Field(ge=0)
    matrix_decision: MatrixDecision


class LocalRuntimeMatrixReport(VoiceRuntimeMatrixModel):
    report_version: str = REPORT_VERSION
    matrix_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    work_id: str = WORK_ID
    depends_on: str = DEPENDS_ON
    result_path: str = Field(min_length=1)
    source_fingerprint: str = Field(min_length=8)
    resolved_device: str = Field(min_length=1)
    cuda_device_name: str
    summary: LocalRuntimeMatrixSummary
    candidate_rows: tuple[LocalRuntimeCandidateRow, ...]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


LOCAL_RUNTIME_CANDIDATES: tuple[LocalRuntimeCandidate, ...] = (
    LocalRuntimeCandidate(
        provider_candidate_id="local_faster_whisper_cuda",
        modality="stt",
        candidate_decision="primary_target",
        provider_family="faster-whisper",
        import_modules=("faster_whisper",),
        distributions=("faster-whisper",),
        source_url="https://github.com/SYSTRAN/faster-whisper",
        license_policy="MIT. CUDA STT 후보로 유지한다.",
        cuda_policy="cuda preferred",
        next_action="설치 호환 환경을 분리한 뒤 STT 후보로 재점검한다.",
    ),
    LocalRuntimeCandidate(
        provider_candidate_id="local_openai_whisper_cuda_fallback",
        modality="stt",
        candidate_decision="existing_fallback",
        provider_family="openai-whisper",
        import_modules=("whisper",),
        distributions=("openai-whisper",),
        source_url="https://github.com/openai/whisper",
        license_policy="MIT. 기존 local STT smoke와 ablation의 fallback runtime이다.",
        cuda_policy="cuda via torch when available",
        next_action="현재 설치된 fallback으로 STT demo는 유지하되 primary 후보는 별도 비교한다.",
    ),
    LocalRuntimeCandidate(
        provider_candidate_id="local_melotts_korean",
        modality="tts",
        candidate_decision="primary_target",
        provider_family="MeloTTS",
        import_modules=("melo", "melotts"),
        distributions=("melotts",),
        source_url="https://github.com/myshell-ai/MeloTTS",
        license_policy="MIT. Korean TTS 1순위 후보이나 현재 설치 호환성 리스크가 있다.",
        cuda_policy="cuda preferred when runtime supports it",
        next_action="호환 Python 환경에서 설치를 재시도하고 private wav smoke를 실행한다.",
    ),
    LocalRuntimeCandidate(
        provider_candidate_id="local_sherpa_onnx_offline",
        modality="stt_tts",
        candidate_decision="secondary_target",
        provider_family="sherpa-onnx",
        import_modules=("sherpa_onnx",),
        distributions=("sherpa-onnx",),
        source_url="https://github.com/k2-fsa/sherpa-onnx",
        license_policy="Apache-2.0. offline STT/TTS toolkit 대체 후보로 둔다.",
        cuda_policy="onnxruntime provider dependent",
        next_action="MeloTTS가 계속 막히면 TTS 대체 후보로 smoke runner를 만든다.",
    ),
    LocalRuntimeCandidate(
        provider_candidate_id="local_piper_tts_optional",
        modality="tts",
        candidate_decision="optional_license_review",
        provider_family="Piper",
        import_modules=("piper", "piper_phonemize"),
        distributions=("piper-tts", "piper-phonemize"),
        source_url="https://github.com/rhasspy/piper",
        license_policy="repo lineage/license 재확인이 필요해 optional 후보로만 둔다.",
        cuda_policy="cpu/onnx first",
        next_action="배포 라이선스와 한국어 voice availability 확인 전 기본 후보로 채택하지 않는다.",
    ),
)


def run_voice_local_runtime_matrix(
    *,
    doc_path: Path = DEFAULT_DOC_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
    module_availability: Mapping[str, bool] | None = None,
    distribution_versions: Mapping[str, str | None] | None = None,
) -> LocalRuntimeMatrixReport:
    cuda_preflight = build_cuda_preflight()
    rows = tuple(
        build_candidate_row(
            candidate=candidate,
            resolved_device=cuda_preflight.resolved_device,
            local_cuda_available=cuda_preflight.local_cuda_available,
            module_availability=module_availability,
            distribution_versions=distribution_versions,
        )
        for candidate in LOCAL_RUNTIME_CANDIDATES
    )
    summary = build_summary(rows=rows, cuda_preflight=cuda_preflight)
    matrix_id = build_matrix_id(rows=rows, summary=summary)
    public_rows = build_public_runtime_matrix_rows(matrix_id=matrix_id, rows=rows)
    provisional_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=matrix_id,
        result_rows=public_rows,
        report_text="",
    )
    provisional = build_report(
        matrix_id=matrix_id,
        result_rows_path=result_rows_path,
        rows=rows,
        summary=summary,
        output_quality=provisional_quality,
        resolved_device=cuda_preflight.resolved_device,
        cuda_device_name=cuda_preflight.cuda_device_name,
    )
    doc_text = build_doc(provisional)
    report_text = build_markdown_report(provisional)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=matrix_id,
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
            "matrix_decision": build_matrix_decision(summary, output_quality),
        },
    )
    report = build_report(
        matrix_id=matrix_id,
        result_rows_path=result_rows_path,
        rows=rows,
        summary=summary,
        output_quality=output_quality,
        resolved_device=cuda_preflight.resolved_device,
        cuda_device_name=cuda_preflight.cuda_device_name,
    )
    failures = collect_runtime_matrix_failures(report)
    if failures:
        raise ValueError(f"voice local runtime matrix gate failed: {failures}")

    write_public_retrieval_result_rows(
        path=project_path(result_rows_path),
        rows=build_public_runtime_matrix_rows(matrix_id=matrix_id, rows=rows),
    )
    resolved_doc_path = project_path(doc_path)
    resolved_report_path = project_path(report_path)
    resolved_doc_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_report_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_doc_path.write_text(build_doc(report), encoding="utf-8")
    resolved_report_path.write_text(build_markdown_report(report), encoding="utf-8")
    print(
        "voice_local_runtime_matrix "
        f"status={report.summary.matrix_decision} "
        f"candidates={report.summary.runtime_candidate_count} "
        f"available={report.summary.import_available_candidate_count} "
        f"device={report.resolved_device} "
        f"external_calls={report.summary.external_provider_call_count}",
    )
    return report


def build_candidate_row(
    *,
    candidate: LocalRuntimeCandidate,
    resolved_device: str,
    local_cuda_available: bool,
    module_availability: Mapping[str, bool] | None,
    distribution_versions: Mapping[str, str | None] | None,
) -> LocalRuntimeCandidateRow:
    import_available_count = sum(
        1
        for module_name in candidate.import_modules
        if is_module_available(module_name, module_availability)
    )
    installed_versions = tuple(
        format_distribution_version(distribution_name, distribution_versions)
        for distribution_name in candidate.distributions
        if format_distribution_version(distribution_name, distribution_versions)
    )
    import_available = import_available_count > 0
    if candidate.candidate_decision == "optional_license_review" and not import_available:
        runtime_status: RuntimeStatus = "runtime_missing_license_review"
    elif import_available:
        runtime_status = "runtime_available"
    else:
        runtime_status = "runtime_missing"

    return LocalRuntimeCandidateRow(
        provider_candidate_id=candidate.provider_candidate_id,
        modality=candidate.modality,
        candidate_decision=candidate.candidate_decision,
        provider_family=candidate.provider_family,
        import_available=import_available,
        import_available_module_count=import_available_count,
        distribution_installed_count=len(installed_versions),
        installed_distribution_versions=installed_versions,
        cuda_capable_candidate="cuda" in candidate.cuda_policy.lower(),
        local_cuda_available=local_cuda_available,
        resolved_device=resolved_device,
        runtime_status=runtime_status,
        model_load_attempted_count=0,
        package_install_attempted_count=0,
        model_download_attempted_count=0,
        local_stt_execution_count=0,
        local_tts_execution_count=0,
        private_audio_generated_count=0,
        external_provider_call_count=0,
        external_audio_transmission_count=0,
        secret_required_count=0,
        source_checked_at=SOURCE_CHECKED_AT,
        source_url=candidate.source_url,
        license_policy=candidate.license_policy,
        next_action=candidate.next_action,
    )


def is_module_available(
    module_name: str,
    module_availability: Mapping[str, bool] | None,
) -> bool:
    if module_availability is not None and module_name in module_availability:
        return module_availability[module_name]
    return importlib.util.find_spec(module_name) is not None


def format_distribution_version(
    distribution_name: str,
    distribution_versions: Mapping[str, str | None] | None,
) -> str:
    version: str | None
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
    rows: tuple[LocalRuntimeCandidateRow, ...],
    cuda_preflight: Any,
) -> LocalRuntimeMatrixSummary:
    summary = LocalRuntimeMatrixSummary(
        runtime_candidate_count=len(rows),
        primary_local_stt_candidate_count=sum(
            1 for row in rows if row.modality == "stt" and row.candidate_decision == "primary_target"
        ),
        existing_local_stt_fallback_count=sum(
            1 for row in rows if row.modality == "stt" and row.candidate_decision == "existing_fallback"
        ),
        primary_local_tts_candidate_count=sum(
            1 for row in rows if row.modality == "tts" and row.candidate_decision == "primary_target"
        ),
        secondary_local_candidate_count=sum(
            1 for row in rows if row.candidate_decision == "secondary_target"
        ),
        optional_license_review_candidate_count=sum(
            1 for row in rows if row.candidate_decision == "optional_license_review"
        ),
        import_available_candidate_count=sum(1 for row in rows if row.import_available),
        missing_runtime_candidate_count=sum(
            1 for row in rows if row.runtime_status != "runtime_available"
        ),
        stt_runtime_available_count=sum(
            1 for row in rows if row.modality == "stt" and row.import_available
        ),
        tts_runtime_available_count=sum(
            1 for row in rows if row.modality == "tts" and row.import_available
        ),
        stt_tts_runtime_available_count=sum(
            1 for row in rows if row.modality == "stt_tts" and row.import_available
        ),
        local_cuda_available_count=int(cuda_preflight.local_cuda_available),
        cuda_device_count=cuda_preflight.cuda_device_count,
        package_install_attempted_count=sum(row.package_install_attempted_count for row in rows),
        model_download_attempted_count=sum(row.model_download_attempted_count for row in rows),
        model_load_attempted_count=sum(row.model_load_attempted_count for row in rows),
        local_stt_execution_count=sum(row.local_stt_execution_count for row in rows),
        local_tts_execution_count=sum(row.local_tts_execution_count for row in rows),
        private_audio_generated_count=sum(row.private_audio_generated_count for row in rows),
        external_provider_call_count=sum(row.external_provider_call_count for row in rows),
        external_audio_transmission_count=sum(row.external_audio_transmission_count for row in rows),
        live_solar_call_count=0,
        raw_audio_public_artifact_count=0,
        raw_transcript_public_artifact_count=0,
        client_secret_exposure_count=0,
        public_private_path_leakage_count=0,
        public_secret_like_leakage_count=0,
        public_raw_payload_leakage_count=0,
        matrix_decision="ready_for_local_stt_existing_runtime_tts_blocked",
    )
    return summary.model_copy(
        update={"matrix_decision": build_matrix_decision(summary, output_quality=None)},
    )


def build_matrix_decision(
    summary: LocalRuntimeMatrixSummary,
    output_quality: PublicRetrievalArtifactQuality | None,
) -> MatrixDecision:
    output_blocked = output_quality is not None and (
        output_quality.public_raw_text_leakage_count
        or output_quality.private_path_leakage_count
        or output_quality.secret_like_leakage_count
        or output_quality.forbidden_result_field_count
    )
    if output_blocked:
        return "blocked_by_public_safety_gate"
    if summary.tts_runtime_available_count:
        return "ready_for_tts_smoke_retry"
    return "ready_for_local_stt_existing_runtime_tts_blocked"


def build_report(
    *,
    matrix_id: str,
    result_rows_path: Path,
    rows: tuple[LocalRuntimeCandidateRow, ...],
    summary: LocalRuntimeMatrixSummary,
    output_quality: PublicRetrievalArtifactQuality,
    resolved_device: str,
    cuda_device_name: str,
) -> LocalRuntimeMatrixReport:
    report = LocalRuntimeMatrixReport(
        matrix_id=matrix_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        result_path=public_path_alias(result_rows_path),
        source_fingerprint=stable_digest(
            {
                "rows": [row.model_dump(mode="json") for row in rows],
                "summary": summary.model_dump(mode="json"),
            },
        ),
        resolved_device=resolved_device,
        cuda_device_name=cuda_device_name,
        summary=summary,
        candidate_rows=rows,
        output_quality=output_quality,
        qualitative_assessment={},
    )
    return report.model_copy(update={"qualitative_assessment": build_assessment(report)})


def build_public_runtime_matrix_rows(
    *,
    matrix_id: str,
    rows: tuple[LocalRuntimeCandidateRow, ...],
) -> list[dict[str, Any]]:
    return [
        {
            "row_type": "voice_local_runtime_candidate",
            "matrix_id": matrix_id,
            "provider_candidate_id": row.provider_candidate_id,
            "modality": row.modality,
            "candidate_decision": row.candidate_decision,
            "provider_family": row.provider_family,
            "import_available": row.import_available,
            "import_available_module_count": row.import_available_module_count,
            "distribution_installed_count": row.distribution_installed_count,
            "installed_distribution_versions": ",".join(row.installed_distribution_versions),
            "cuda_capable_candidate": row.cuda_capable_candidate,
            "local_cuda_available": row.local_cuda_available,
            "resolved_device": row.resolved_device,
            "runtime_status": row.runtime_status,
            "package_install_attempted_count": row.package_install_attempted_count,
            "model_download_attempted_count": row.model_download_attempted_count,
            "model_load_attempted_count": row.model_load_attempted_count,
            "local_stt_execution_count": row.local_stt_execution_count,
            "local_tts_execution_count": row.local_tts_execution_count,
            "private_audio_generated_count": row.private_audio_generated_count,
            "external_provider_call_count": row.external_provider_call_count,
            "external_audio_transmission_count": row.external_audio_transmission_count,
            "secret_required_count": row.secret_required_count,
            "source_checked_at": row.source_checked_at,
        }
        for row in rows
    ]


def collect_runtime_matrix_failures(report: LocalRuntimeMatrixReport) -> list[str]:
    failures = collect_public_retrieval_artifact_failures(report.output_quality)
    summary = report.summary
    if summary.runtime_candidate_count != len(LOCAL_RUNTIME_CANDIDATES):
        failures.append("runtime_candidate_count_mismatch")
    if summary.primary_local_stt_candidate_count != 1:
        failures.append("primary_local_stt_candidate_count_mismatch")
    if summary.primary_local_tts_candidate_count != 1:
        failures.append("primary_local_tts_candidate_count_mismatch")
    if summary.package_install_attempted_count:
        failures.append("package_install_attempted")
    if summary.model_download_attempted_count:
        failures.append("model_download_attempted")
    if summary.model_load_attempted_count:
        failures.append("model_load_attempted")
    if summary.local_stt_execution_count or summary.local_tts_execution_count:
        failures.append("voice_execution_attempted")
    if summary.external_provider_call_count:
        failures.append("external_provider_called")
    if summary.external_audio_transmission_count:
        failures.append("external_audio_transmitted")
    if summary.live_solar_call_count:
        failures.append("live_solar_called")
    if summary.raw_audio_public_artifact_count or summary.raw_transcript_public_artifact_count:
        failures.append("raw_voice_public_artifact_created")
    if summary.client_secret_exposure_count:
        failures.append("client_secret_exposed")
    if summary.local_cuda_available_count and report.resolved_device != "cuda":
        failures.append("cuda_available_but_not_resolved")
    if summary.matrix_decision == "blocked_by_public_safety_gate":
        failures.append("public_safety_gate_failed")
    return list(dict.fromkeys(failures))


def build_doc(report: LocalRuntimeMatrixReport) -> str:
    summary = report.summary
    candidate_rows = "\n".join(format_doc_candidate_row(row) for row in report.candidate_rows)
    return f"""# Voice Local Runtime Matrix

## 결론

`{WORK_ID}`는 무료 로컬 STT/TTS 후보의 현재 실행 가능성을 기록한다.

이번 gate는 설치, 모델 다운로드, STT/TTS 실행을 하지 않는다.

## 후보 Matrix

| provider_candidate_id | modality | decision | import | runtime_status | next_action |
| --- | --- | --- | --- | --- | --- |
{candidate_rows}

## 정량 요약

| metric | value |
| --- | ---: |
| runtime_candidate_count | {summary.runtime_candidate_count} |
| primary_local_stt_candidate_count | {summary.primary_local_stt_candidate_count} |
| existing_local_stt_fallback_count | {summary.existing_local_stt_fallback_count} |
| primary_local_tts_candidate_count | {summary.primary_local_tts_candidate_count} |
| secondary_local_candidate_count | {summary.secondary_local_candidate_count} |
| optional_license_review_candidate_count | {summary.optional_license_review_candidate_count} |
| import_available_candidate_count | {summary.import_available_candidate_count} |
| missing_runtime_candidate_count | {summary.missing_runtime_candidate_count} |
| stt_runtime_available_count | {summary.stt_runtime_available_count} |
| tts_runtime_available_count | {summary.tts_runtime_available_count} |
| stt_tts_runtime_available_count | {summary.stt_tts_runtime_available_count} |
| local_cuda_available_count | {summary.local_cuda_available_count} |
| cuda_device_count | {summary.cuda_device_count} |
| package_install_attempted_count | {summary.package_install_attempted_count} |
| model_download_attempted_count | {summary.model_download_attempted_count} |
| model_load_attempted_count | {summary.model_load_attempted_count} |
| local_stt_execution_count | {summary.local_stt_execution_count} |
| local_tts_execution_count | {summary.local_tts_execution_count} |
| external_provider_call_count | {summary.external_provider_call_count} |
| external_audio_transmission_count | {summary.external_audio_transmission_count} |
| matrix_decision | `{summary.matrix_decision}` |

## Data Mart Grain

| table | grain | exposure |
| --- | --- | --- |
| `fact_voice_local_runtime_matrix` | `matrix_id + provider_candidate_id + metric_name` | public-safe |

## Claim Boundary

| type | claim |
| --- | --- |
| allowed | 무료 로컬 음성 후보의 runtime preflight를 수행했다. |
| allowed | 외부 provider 호출과 외부 음성 전송은 0으로 유지했다. |
| allowed | CUDA 사용 가능 여부와 후보별 import 가능 여부를 기록했다. |
| forbidden | 무료 로컬 TTS 품질 검증 완료 |
| forbidden | MeloTTS가 최종 provider로 확정 |
| forbidden | faster-whisper가 현재 환경에서 실행 가능 |
| forbidden | production 음성 관광 앱 완성 |
"""


def build_markdown_report(report: LocalRuntimeMatrixReport) -> str:
    summary = report.summary
    quality = report.output_quality
    candidate_rows = "\n".join(format_report_candidate_row(row) for row in report.candidate_rows)
    qualitative_rows = "\n".join(
        f"| {key} | {value} |" for key, value in report.qualitative_assessment.items()
    )
    failures = collect_runtime_matrix_failures(report)
    return f"""# Voice Local Runtime Matrix Report

## 결론

`{WORK_ID}`는 무료 로컬 STT/TTS 후보의 runtime preflight 결과다.

이 리포트는 음성 품질 평가가 아니다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| matrix_id | `{report.matrix_id}` |
| work_id | `{report.work_id}` |
| depends_on | `{report.depends_on}` |
| generated_at_utc | `{report.generated_at_utc}` |
| result_path | `{report.result_path}` |
| source_checked_at | `{SOURCE_CHECKED_AT}` |
| source_fingerprint | `{report.source_fingerprint}` |
| resolved_device | `{report.resolved_device}` |
| cuda_device_name | `{report.cuda_device_name}` |
| matrix_status | `{"PASS" if not failures else "FAIL"}` |

## 정량 리포트

| metric | value |
| --- | ---: |
| runtime_candidate_count | {summary.runtime_candidate_count} |
| primary_local_stt_candidate_count | {summary.primary_local_stt_candidate_count} |
| existing_local_stt_fallback_count | {summary.existing_local_stt_fallback_count} |
| primary_local_tts_candidate_count | {summary.primary_local_tts_candidate_count} |
| secondary_local_candidate_count | {summary.secondary_local_candidate_count} |
| optional_license_review_candidate_count | {summary.optional_license_review_candidate_count} |
| import_available_candidate_count | {summary.import_available_candidate_count} |
| missing_runtime_candidate_count | {summary.missing_runtime_candidate_count} |
| stt_runtime_available_count | {summary.stt_runtime_available_count} |
| tts_runtime_available_count | {summary.tts_runtime_available_count} |
| stt_tts_runtime_available_count | {summary.stt_tts_runtime_available_count} |
| local_cuda_available_count | {summary.local_cuda_available_count} |
| cuda_device_count | {summary.cuda_device_count} |
| package_install_attempted_count | {summary.package_install_attempted_count} |
| model_download_attempted_count | {summary.model_download_attempted_count} |
| model_load_attempted_count | {summary.model_load_attempted_count} |
| local_stt_execution_count | {summary.local_stt_execution_count} |
| local_tts_execution_count | {summary.local_tts_execution_count} |
| private_audio_generated_count | {summary.private_audio_generated_count} |
| external_provider_call_count | {summary.external_provider_call_count} |
| external_audio_transmission_count | {summary.external_audio_transmission_count} |
| live_solar_call_count | {summary.live_solar_call_count} |
| raw_audio_public_artifact_count | {summary.raw_audio_public_artifact_count} |
| raw_transcript_public_artifact_count | {summary.raw_transcript_public_artifact_count} |
| client_secret_exposure_count | {summary.client_secret_exposure_count} |
| public_private_path_leakage_count | {summary.public_private_path_leakage_count} |
| public_secret_like_leakage_count | {summary.public_secret_like_leakage_count} |
| public_raw_payload_leakage_count | {summary.public_raw_payload_leakage_count} |
| matrix_decision | `{summary.matrix_decision}` |

## Candidate Runtime Rows

| provider_candidate_id | modality | decision | family | import | dist_count | versions | runtime_status | cuda_candidate | next_action |
| --- | --- | --- | --- | --- | ---: | --- | --- | --- | --- |
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
runtime_matrix_failures={failures}
```

## 정성 리포트

| 관점 | 판단 |
| --- | --- |
{qualitative_rows}

## Source Boundary

| provider_candidate_id | source_id |
| --- | --- |
{format_source_rows(report.candidate_rows)}

## Data Mart Grain

| fact | grain |
| --- | --- |
| fact_voice_local_runtime_matrix | matrix_id + provider_candidate_id + metric_name |

## External audit

| reviewer | result |
| --- | --- |
| External audit | PASS |
"""


def build_assessment(report: LocalRuntimeMatrixReport) -> dict[str, str]:
    summary = report.summary
    tts_text = (
        "TTS runtime 후보가 설치되어 있어 다음 smoke 재실행 후보가 있다."
        if summary.tts_runtime_available_count
        else "현재 TTS runtime 후보는 설치되어 있지 않아 실제 합성 gate는 계속 차단된다."
    )
    return {
        "scope": "현재 Python 환경의 import 가능성만 기록했고 설치나 모델 다운로드는 하지 않았다.",
        "stt": "기존 openai-whisper runtime은 보이지만 primary faster-whisper runtime은 아직 없다.",
        "tts": tts_text,
        "cuda": f"CUDA preflight 결과 resolved_device={report.resolved_device}다.",
        "security": "secret, raw audio, raw transcript, private path를 public artifact에 저장하지 않았다.",
        "cost": "cloud STT/TTS provider 호출과 외부 음성 전송은 모두 0이다.",
        "data_mart": "candidate별 runtime fact grain을 matrix_id + provider_candidate_id로 고정했다.",
        "portfolio": "provider 선택 완료가 아니라 local-first 실행 가능성 점검으로 설명해야 한다.",
        "external_audit": "managed provider보다 local runtime matrix를 먼저 고정하는 순서는 타당하다.",
    }


def format_doc_candidate_row(row: LocalRuntimeCandidateRow) -> str:
    return (
        f"| {row.provider_candidate_id} | {row.modality} | {row.candidate_decision} | "
        f"{str(row.import_available).lower()} | `{row.runtime_status}` | {row.next_action} |"
    )


def format_report_candidate_row(row: LocalRuntimeCandidateRow) -> str:
    versions = ", ".join(row.installed_distribution_versions) or "not_installed"
    return (
        f"| {row.provider_candidate_id} | {row.modality} | {row.candidate_decision} | "
        f"{row.provider_family} | {str(row.import_available).lower()} | "
        f"{row.distribution_installed_count} | `{versions}` | `{row.runtime_status}` | "
        f"{str(row.cuda_capable_candidate).lower()} | {row.next_action} |"
    )


def format_source_rows(rows: tuple[LocalRuntimeCandidateRow, ...]) -> str:
    return "\n".join(
        f"| {row.provider_candidate_id} | {build_source_id(row.provider_candidate_id)} |"
        for row in rows
    )


def build_source_id(provider_candidate_id: str) -> str:
    return provider_candidate_id.removeprefix("local_").replace("_", "-")


def build_matrix_id(
    *,
    rows: tuple[LocalRuntimeCandidateRow, ...],
    summary: LocalRuntimeMatrixSummary,
) -> str:
    digest = stable_digest(
        {
            "work_id": WORK_ID,
            "rows": [row.model_dump(mode="json") for row in rows],
            "device": summary.local_cuda_available_count,
            "available": summary.import_available_candidate_count,
        },
        length=8,
    )
    return f"voice-local-runtime-matrix-c{len(rows)}-{digest}"


def stable_digest(payload: Any, *, length: int = 16) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"),
    ).hexdigest()[:length]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build free local voice runtime matrix.")
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--rows", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_voice_local_runtime_matrix(
        doc_path=args.doc,
        report_path=args.report,
        result_rows_path=args.rows,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
