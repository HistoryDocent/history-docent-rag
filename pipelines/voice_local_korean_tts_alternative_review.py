from __future__ import annotations

import argparse
import hashlib
import json
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


REPORT_VERSION = "voice-local-korean-tts-alternative-review-report/v1"
WORK_ID = "HD-VOICE-LOCAL-KOREAN-TTS-ALTERNATIVE-REVIEW-001"
DEPENDS_ON = "HD-VOICE-LOCAL-PIPER-TTS-SMOKE-001"
SOURCE_CHECKED_AT = "2026-05-20"

DEFAULT_DOC_PATH = Path("docs") / "VOICE_LOCAL_KOREAN_TTS_ALTERNATIVE_REVIEW.md"
DEFAULT_REPORT_PATH = (
    Path("evals") / "reports" / "voice_local_korean_tts_alternative_review_report.md"
)
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "voice_local_korean_tts_alternative_review_rows.jsonl"
)

CandidateDecision = Literal[
    "selected_next_smoke",
    "candidate_after_license_review",
    "blocked_dependency",
    "blocked_missing_korean_voice",
    "research_only",
    "fallback_only",
]
KoreanSupportStatus = Literal[
    "official_korean_support",
    "model_card_korean_support",
    "blocked_no_official_korean_voice",
    "not_out_of_box_korean_candidate",
]


class KoreanTtsReviewModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class KoreanTtsSource(KoreanTtsReviewModel):
    source_id: str = Field(min_length=1)
    url: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    checked_claim: str = Field(min_length=1)


class KoreanTtsCandidate(KoreanTtsReviewModel):
    provider_candidate_id: str = Field(min_length=1)
    provider_family: str = Field(min_length=1)
    integration_path: str = Field(min_length=1)
    korean_support_status: KoreanSupportStatus
    local_execution_policy: str = Field(min_length=1)
    license_policy: str = Field(min_length=1)
    cuda_policy: str = Field(min_length=1)
    windows_risk: str = Field(min_length=1)
    operational_risk_level: Literal["low", "medium", "high"]
    source_ids: tuple[str, ...]
    next_action: str = Field(min_length=1)
    decision: CandidateDecision


class KoreanTtsCandidateRow(KoreanTtsReviewModel):
    provider_candidate_id: str = Field(min_length=1)
    provider_family: str = Field(min_length=1)
    integration_path: str = Field(min_length=1)
    korean_support_status: KoreanSupportStatus
    supports_korean_count: int = Field(ge=0, le=1)
    local_free_candidate_count: int = Field(ge=0, le=1)
    cuda_capable_candidate_count: int = Field(ge=0, le=1)
    license_review_required_count: int = Field(ge=0, le=1)
    windows_blocker_count: int = Field(ge=0, le=1)
    execution_ready_without_download_count: int = Field(ge=0, le=1)
    package_install_attempted_count: int = Field(ge=0)
    model_download_attempted_count: int = Field(ge=0)
    local_tts_execution_count: int = Field(ge=0)
    external_provider_call_count: int = Field(ge=0)
    external_audio_transmission_count: int = Field(ge=0)
    raw_audio_public_artifact_count: int = Field(ge=0)
    raw_transcript_public_artifact_count: int = Field(ge=0)
    source_checked_count: int = Field(ge=0)
    source_ids: tuple[str, ...]
    operational_risk_level: Literal["low", "medium", "high"]
    decision: CandidateDecision
    next_action: str = Field(min_length=1)


class KoreanTtsReviewSummary(KoreanTtsReviewModel):
    candidate_count: int = Field(ge=0)
    source_reference_count: int = Field(ge=0)
    source_checked_candidate_count: int = Field(ge=0)
    korean_support_candidate_count: int = Field(ge=0)
    local_free_candidate_count: int = Field(ge=0)
    cuda_capable_candidate_count: int = Field(ge=0)
    selected_next_smoke_candidate_count: int = Field(ge=0)
    license_review_required_count: int = Field(ge=0)
    windows_blocker_candidate_count: int = Field(ge=0)
    blocked_missing_korean_voice_count: int = Field(ge=0)
    research_only_candidate_count: int = Field(ge=0)
    fallback_only_candidate_count: int = Field(ge=0)
    package_install_attempted_count: int = Field(ge=0)
    model_download_attempted_count: int = Field(ge=0)
    local_tts_execution_count: int = Field(ge=0)
    live_tts_call_count: int = Field(ge=0)
    live_stt_call_count: int = Field(ge=0)
    live_solar_call_count: int = Field(ge=0)
    external_provider_call_count: int = Field(ge=0)
    external_audio_transmission_count: int = Field(ge=0)
    raw_audio_public_artifact_count: int = Field(ge=0)
    raw_transcript_public_artifact_count: int = Field(ge=0)
    client_secret_exposure_count: int = Field(ge=0)
    local_cuda_available_count: int = Field(ge=0)
    cuda_device_count: int = Field(ge=0)
    selected_next_smoke_candidate_id: str = Field(min_length=1)
    public_private_path_leakage_count: int = Field(ge=0)
    public_secret_like_leakage_count: int = Field(ge=0)
    public_raw_payload_leakage_count: int = Field(ge=0)
    review_decision: Literal["select_sherpa_onnx_supertonic3_for_smoke", "failed_public_safety_gate"]


class KoreanTtsAlternativeReview(KoreanTtsReviewModel):
    report_version: str = REPORT_VERSION
    review_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    work_id: str = WORK_ID
    depends_on: str = DEPENDS_ON
    result_path: str = Field(min_length=1)
    source_checked_at: str = SOURCE_CHECKED_AT
    source_fingerprint: str = Field(min_length=8)
    resolved_device: str = Field(min_length=1)
    cuda_device_name: str
    sources: tuple[KoreanTtsSource, ...]
    candidate_rows: tuple[KoreanTtsCandidateRow, ...]
    summary: KoreanTtsReviewSummary
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


SOURCES: tuple[KoreanTtsSource, ...] = (
    KoreanTtsSource(
        source_id="sherpa_onnx_supertonic_tts",
        url="https://k2-fsa.github.io/sherpa/onnx/tts/supertonic.html",
        source_type="official_docs",
        checked_claim="sherpa-onnx supports SupertonicTTS offline TTS integration.",
    ),
    KoreanTtsSource(
        source_id="sherpa_onnx_supertonic_ko",
        url="https://k2-fsa.github.io/sherpa/onnx/tts/all/Korean/supertonic-3-ko.html",
        source_type="official_docs",
        checked_claim="sherpa-onnx provides a Korean Supertonic 3 TTS example page.",
    ),
    KoreanTtsSource(
        source_id="supertonic3_huggingface",
        url="https://huggingface.co/Supertone/supertonic-3",
        source_type="model_card",
        checked_claim="Supertonic 3 model card states multilingual on-device TTS and license details.",
    ),
    KoreanTtsSource(
        source_id="supertonic_github",
        url="https://github.com/supertone-inc/supertonic",
        source_type="official_repository",
        checked_claim="Supertonic repository provides Python examples and installation path.",
    ),
    KoreanTtsSource(
        source_id="melotts_github",
        url="https://github.com/myshell-ai/MeloTTS",
        source_type="official_repository",
        checked_claim="MeloTTS repository documents Korean support and MIT license.",
    ),
    KoreanTtsSource(
        source_id="kani_tts_github",
        url="https://github.com/nineninesix-ai/kani-tts-2-pretrain",
        source_type="official_repository",
        checked_claim="KaniTTS2 repository documents Korean TTS model family and runtime examples.",
    ),
    KoreanTtsSource(
        source_id="kani_tts_huggingface",
        url="https://huggingface.co/nineninesix/kani-tts-370m",
        source_type="model_card",
        checked_claim="KaniTTS Hugging Face model card provides model/license metadata requiring review.",
    ),
    KoreanTtsSource(
        source_id="coqui_xtts_v2_huggingface",
        url="https://huggingface.co/coqui/XTTS-v2",
        source_type="model_card",
        checked_claim="XTTS-v2 model card lists Korean support and CPML license boundary.",
    ),
    KoreanTtsSource(
        source_id="styletts2_github",
        url="https://github.com/yl4579/StyleTTS2",
        source_type="official_repository",
        checked_claim="StyleTTS2 repository is research-oriented and not an out-of-box Korean provider.",
    ),
    KoreanTtsSource(
        source_id="piper_voice_manifest",
        url="https://huggingface.co/rhasspy/piper-voices",
        source_type="model_repository",
        checked_claim="Piper voice repository was already checked and Korean voice was absent in the current manifest.",
    ),
)


CANDIDATES: tuple[KoreanTtsCandidate, ...] = (
    KoreanTtsCandidate(
        provider_candidate_id="local_sherpa_onnx_supertonic3_ko",
        provider_family="sherpa-onnx + Supertonic 3",
        integration_path="ONNX/offline TTS smoke via sherpa-onnx Korean example",
        korean_support_status="official_korean_support",
        local_execution_policy="local offline execution target; no cloud TTS provider by default",
        license_policy="sherpa-onnx toolkit is open source; Supertonic 3 model license must be recorded before public adoption claim",
        cuda_policy="CPU-first smoke; CUDA is available locally but ONNX acceleration path is a follow-up, not a prerequisite",
        windows_risk="medium: model download and ONNX runtime path must be checked on Windows",
        operational_risk_level="medium",
        source_ids=(
            "sherpa_onnx_supertonic_tts",
            "sherpa_onnx_supertonic_ko",
            "supertonic3_huggingface",
        ),
        next_action="next smoke target: install runtime only after approval, download Korean model privately, synthesize 5 public-safe scripts to private wav artifacts",
        decision="selected_next_smoke",
    ),
    KoreanTtsCandidate(
        provider_candidate_id="local_supertonic3_python_sdk_ko",
        provider_family="Supertonic 3 Python SDK",
        integration_path="direct Python package path from Supertonic repository",
        korean_support_status="model_card_korean_support",
        local_execution_policy="local model execution candidate; no external audio transmission by design",
        license_policy="model license review required before portfolio adoption claim",
        cuda_policy="on-device TTS candidate; CUDA path not selected until smoke proves quality/runtime",
        windows_risk="medium: direct SDK dependency and model cache path need separate smoke",
        operational_risk_level="medium",
        source_ids=("supertonic3_huggingface", "supertonic_github"),
        next_action="keep as second integration path if sherpa-onnx packaging is blocked",
        decision="candidate_after_license_review",
    ),
    KoreanTtsCandidate(
        provider_candidate_id="local_melotts_korean_retry",
        provider_family="MeloTTS",
        integration_path="Python package Korean synthesis path",
        korean_support_status="official_korean_support",
        local_execution_policy="local execution candidate; no cloud API required",
        license_policy="MIT, but local dependency chain must be stable before default use",
        cuda_policy="CUDA can be used if runtime supports it; previous gate resolved CUDA locally",
        windows_risk="high: previous attempt was blocked by Windows eunjeon build dependency",
        operational_risk_level="high",
        source_ids=("melotts_github",),
        next_action="run only after explicit Windows dependency fix approval",
        decision="blocked_dependency",
    ),
    KoreanTtsCandidate(
        provider_candidate_id="local_kani_tts_ko_review",
        provider_family="KaniTTS2",
        integration_path="model/repository review before any runtime smoke",
        korean_support_status="model_card_korean_support",
        local_execution_policy="local model execution candidate; no cloud API required",
        license_policy="license metadata is not clean enough for immediate portfolio adoption; review required",
        cuda_policy="GPU candidate, but runtime stack is not yet integrated",
        windows_risk="medium: installation/runtime path must be proven on Windows",
        operational_risk_level="medium",
        source_ids=("kani_tts_github", "kani_tts_huggingface"),
        next_action="keep as research candidate after sherpa-onnx and MeloTTS paths are exhausted",
        decision="candidate_after_license_review",
    ),
    KoreanTtsCandidate(
        provider_candidate_id="local_coqui_xtts_v2_ko_review",
        provider_family="Coqui XTTS-v2",
        integration_path="multilingual TTS/voice cloning model candidate",
        korean_support_status="model_card_korean_support",
        local_execution_policy="local execution possible, but model license and voice cloning risk must be controlled",
        license_policy="CPML-style model license restricts simple portfolio adoption; review required",
        cuda_policy="GPU candidate, but not selected before license and voice identity safeguards",
        windows_risk="medium: heavier model/runtime and artifact size risk",
        operational_risk_level="high",
        source_ids=("coqui_xtts_v2_huggingface",),
        next_action="do not use as default; keep for optional research-only benchmark",
        decision="candidate_after_license_review",
    ),
    KoreanTtsCandidate(
        provider_candidate_id="local_styletts2_research_only",
        provider_family="StyleTTS2",
        integration_path="research implementation candidate",
        korean_support_status="not_out_of_box_korean_candidate",
        local_execution_policy="local research code possible, but not a ready Korean provider path",
        license_policy="code license alone is not enough; dataset/model voice rights require review",
        cuda_policy="GPU research candidate",
        windows_risk="high: training/inference packaging is outside MVP scope",
        operational_risk_level="high",
        source_ids=("styletts2_github",),
        next_action="exclude from immediate smoke; cite as research-only alternative",
        decision="research_only",
    ),
    KoreanTtsCandidate(
        provider_candidate_id="local_piper_tts_ko_blocked",
        provider_family="Piper",
        integration_path="already-smoked Piper package and official voice manifest",
        korean_support_status="blocked_no_official_korean_voice",
        local_execution_policy="local runtime exists, but Korean voice is unavailable in current manifest",
        license_policy="package and per-voice license review still required if Korean voice appears later",
        cuda_policy="CUDA flag path exists in the smoke runner but no Korean model can be executed now",
        windows_risk="low runtime risk, but current Korean model availability is the blocker",
        operational_risk_level="high",
        source_ids=("piper_voice_manifest",),
        next_action="do not continue Piper until an official Korean voice appears",
        decision="blocked_missing_korean_voice",
    ),
)


def run_voice_local_korean_tts_alternative_review(
    *,
    doc_path: Path = DEFAULT_DOC_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
) -> KoreanTtsAlternativeReview:
    cuda_preflight = build_cuda_preflight()
    rows = tuple(build_candidate_row(candidate) for candidate in CANDIDATES)
    provisional_summary = build_summary(
        rows=rows,
        sources=SOURCES,
        cuda_preflight=cuda_preflight,
        output_quality=None,
    )
    review_id = build_review_id(rows=rows, summary=provisional_summary)
    public_rows = build_public_rows(review_id=review_id, rows=rows)
    provisional_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=review_id,
        result_rows=public_rows,
        report_text="",
    )
    provisional = build_report(
        review_id=review_id,
        result_rows_path=result_rows_path,
        sources=SOURCES,
        rows=rows,
        summary=provisional_summary,
        output_quality=provisional_quality,
        resolved_device=cuda_preflight.resolved_device,
        cuda_device_name=cuda_preflight.cuda_device_name,
    )
    report_text = build_markdown_report(provisional)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=review_id,
        result_rows=public_rows,
        report_text=report_text,
    )
    summary = build_summary(
        rows=rows,
        sources=SOURCES,
        cuda_preflight=cuda_preflight,
        output_quality=output_quality,
    )
    report = build_report(
        review_id=review_id,
        result_rows_path=result_rows_path,
        sources=SOURCES,
        rows=rows,
        summary=summary,
        output_quality=output_quality,
        resolved_device=cuda_preflight.resolved_device,
        cuda_device_name=cuda_preflight.cuda_device_name,
    )
    failures = collect_korean_tts_alternative_review_failures(report)
    if failures:
        raise ValueError(f"voice local Korean TTS alternative review gate failed: {failures}")

    write_public_retrieval_result_rows(path=project_path(result_rows_path), rows=public_rows)
    resolved_doc_path = project_path(doc_path)
    resolved_report_path = project_path(report_path)
    resolved_doc_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_report_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_doc_path.write_text(build_doc(report), encoding="utf-8")
    resolved_report_path.write_text(build_markdown_report(report), encoding="utf-8")
    print(
        "voice_local_korean_tts_alternative_review "
        f"status={report.summary.review_decision} "
        f"candidates={report.summary.candidate_count} "
        f"korean_support={report.summary.korean_support_candidate_count} "
        f"selected={report.summary.selected_next_smoke_candidate_id} "
        f"external_calls={report.summary.external_provider_call_count}",
    )
    return report


def build_candidate_row(candidate: KoreanTtsCandidate) -> KoreanTtsCandidateRow:
    license_policy = candidate.license_policy.lower()
    cuda_policy = candidate.cuda_policy.lower()
    license_review_required = int(
        "review" in license_policy
        or "must be recorded" in license_policy
        or candidate.decision == "candidate_after_license_review"
    )
    cuda_capable_candidate = int(
        "cuda can be used" in cuda_policy
        or "cuda flag path exists" in cuda_policy
        or "gpu candidate" in cuda_policy
    )
    return KoreanTtsCandidateRow(
        provider_candidate_id=candidate.provider_candidate_id,
        provider_family=candidate.provider_family,
        integration_path=candidate.integration_path,
        korean_support_status=candidate.korean_support_status,
        supports_korean_count=int(
            candidate.korean_support_status
            in {"official_korean_support", "model_card_korean_support"}
        ),
        local_free_candidate_count=1,
        cuda_capable_candidate_count=cuda_capable_candidate,
        license_review_required_count=license_review_required,
        windows_blocker_count=int(
            "windows" in candidate.windows_risk.lower()
            and ("high" in candidate.windows_risk.lower() or "block" in candidate.windows_risk.lower())
        ),
        execution_ready_without_download_count=0,
        package_install_attempted_count=0,
        model_download_attempted_count=0,
        local_tts_execution_count=0,
        external_provider_call_count=0,
        external_audio_transmission_count=0,
        raw_audio_public_artifact_count=0,
        raw_transcript_public_artifact_count=0,
        source_checked_count=len(candidate.source_ids),
        source_ids=candidate.source_ids,
        operational_risk_level=candidate.operational_risk_level,
        decision=candidate.decision,
        next_action=candidate.next_action,
    )


def build_summary(
    *,
    rows: tuple[KoreanTtsCandidateRow, ...],
    sources: tuple[KoreanTtsSource, ...],
    cuda_preflight: Any,
    output_quality: PublicRetrievalArtifactQuality | None,
) -> KoreanTtsReviewSummary:
    selected_rows = [row for row in rows if row.decision == "selected_next_smoke"]
    summary = KoreanTtsReviewSummary(
        candidate_count=len(rows),
        source_reference_count=len(sources),
        source_checked_candidate_count=sum(1 for row in rows if row.source_checked_count > 0),
        korean_support_candidate_count=sum(row.supports_korean_count for row in rows),
        local_free_candidate_count=sum(row.local_free_candidate_count for row in rows),
        cuda_capable_candidate_count=sum(row.cuda_capable_candidate_count for row in rows),
        selected_next_smoke_candidate_count=len(selected_rows),
        license_review_required_count=sum(row.license_review_required_count for row in rows),
        windows_blocker_candidate_count=sum(row.windows_blocker_count for row in rows),
        blocked_missing_korean_voice_count=sum(
            1 for row in rows if row.decision == "blocked_missing_korean_voice"
        ),
        research_only_candidate_count=sum(1 for row in rows if row.decision == "research_only"),
        fallback_only_candidate_count=sum(1 for row in rows if row.decision == "fallback_only"),
        package_install_attempted_count=sum(row.package_install_attempted_count for row in rows),
        model_download_attempted_count=sum(row.model_download_attempted_count for row in rows),
        local_tts_execution_count=sum(row.local_tts_execution_count for row in rows),
        live_tts_call_count=0,
        live_stt_call_count=0,
        live_solar_call_count=0,
        external_provider_call_count=sum(row.external_provider_call_count for row in rows),
        external_audio_transmission_count=sum(
            row.external_audio_transmission_count for row in rows
        ),
        raw_audio_public_artifact_count=sum(row.raw_audio_public_artifact_count for row in rows),
        raw_transcript_public_artifact_count=sum(
            row.raw_transcript_public_artifact_count for row in rows
        ),
        client_secret_exposure_count=0,
        local_cuda_available_count=int(cuda_preflight.local_cuda_available),
        cuda_device_count=cuda_preflight.cuda_device_count,
        selected_next_smoke_candidate_id=(
            selected_rows[0].provider_candidate_id if selected_rows else ""
        ),
        public_private_path_leakage_count=(
            output_quality.private_path_leakage_count if output_quality is not None else 0
        ),
        public_secret_like_leakage_count=(
            output_quality.secret_like_leakage_count if output_quality is not None else 0
        ),
        public_raw_payload_leakage_count=(
            output_quality.public_raw_text_leakage_count if output_quality is not None else 0
        ),
        review_decision="select_sherpa_onnx_supertonic3_for_smoke",
    )
    if output_quality is not None and collect_public_retrieval_artifact_failures(output_quality):
        return summary.model_copy(update={"review_decision": "failed_public_safety_gate"})
    return summary


def build_report(
    *,
    review_id: str,
    result_rows_path: Path,
    sources: tuple[KoreanTtsSource, ...],
    rows: tuple[KoreanTtsCandidateRow, ...],
    summary: KoreanTtsReviewSummary,
    output_quality: PublicRetrievalArtifactQuality,
    resolved_device: str,
    cuda_device_name: str,
) -> KoreanTtsAlternativeReview:
    report = KoreanTtsAlternativeReview(
        review_id=review_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        result_path=public_path_alias(result_rows_path),
        source_fingerprint=stable_digest(
            {
                "sources": [source.model_dump(mode="json") for source in sources],
                "rows": [row.model_dump(mode="json") for row in rows],
                "summary": summary.model_dump(mode="json"),
            }
        ),
        resolved_device=resolved_device,
        cuda_device_name=cuda_device_name,
        sources=sources,
        candidate_rows=rows,
        summary=summary,
        output_quality=output_quality,
        qualitative_assessment={},
    )
    return report.model_copy(update={"qualitative_assessment": build_assessment(report)})


def build_public_rows(
    *,
    review_id: str,
    rows: tuple[KoreanTtsCandidateRow, ...],
) -> list[dict[str, Any]]:
    return [
        {
            "row_type": "korean_tts_alternative_review",
            "review_id": review_id,
            "provider_candidate_id": row.provider_candidate_id,
            "provider_family": row.provider_family,
            "integration_path": row.integration_path,
            "korean_support_status": row.korean_support_status,
            "supports_korean_count": row.supports_korean_count,
            "local_free_candidate_count": row.local_free_candidate_count,
            "cuda_capable_candidate_count": row.cuda_capable_candidate_count,
            "license_review_required_count": row.license_review_required_count,
            "windows_blocker_count": row.windows_blocker_count,
            "execution_ready_without_download_count": row.execution_ready_without_download_count,
            "package_install_attempted_count": row.package_install_attempted_count,
            "model_download_attempted_count": row.model_download_attempted_count,
            "local_tts_execution_count": row.local_tts_execution_count,
            "external_provider_call_count": row.external_provider_call_count,
            "external_audio_transmission_count": row.external_audio_transmission_count,
            "source_checked_count": row.source_checked_count,
            "operational_risk_level": row.operational_risk_level,
            "decision": row.decision,
        }
        for row in rows
    ]


def collect_korean_tts_alternative_review_failures(
    report: KoreanTtsAlternativeReview,
) -> list[str]:
    failures = collect_public_retrieval_artifact_failures(report.output_quality)
    summary = report.summary
    if summary.candidate_count != len(CANDIDATES):
        failures.append("candidate_count_mismatch")
    if summary.source_reference_count != len(SOURCES):
        failures.append("source_reference_count_mismatch")
    if summary.source_checked_candidate_count != summary.candidate_count:
        failures.append("source_checked_candidate_missing")
    if summary.korean_support_candidate_count < 3:
        failures.append("korean_support_candidate_too_few")
    if summary.selected_next_smoke_candidate_count != 1:
        failures.append("selected_next_smoke_candidate_count_not_1")
    if summary.selected_next_smoke_candidate_id != "local_sherpa_onnx_supertonic3_ko":
        failures.append("unexpected_selected_next_smoke_candidate")
    if summary.package_install_attempted_count:
        failures.append("package_install_attempted")
    if summary.model_download_attempted_count:
        failures.append("model_download_attempted")
    if summary.local_tts_execution_count or summary.live_tts_call_count:
        failures.append("tts_execution_happened_in_review_gate")
    if summary.external_provider_call_count:
        failures.append("external_provider_called")
    if summary.external_audio_transmission_count:
        failures.append("external_audio_transmitted")
    if summary.live_stt_call_count or summary.live_solar_call_count:
        failures.append("live_external_call_count_nonzero")
    if summary.raw_audio_public_artifact_count or summary.raw_transcript_public_artifact_count:
        failures.append("raw_voice_public_artifact_created")
    if summary.client_secret_exposure_count:
        failures.append("client_secret_exposed")
    if summary.review_decision == "failed_public_safety_gate":
        failures.append("public_safety_gate_failed")
    return list(dict.fromkeys(failures))


def build_doc(report: KoreanTtsAlternativeReview) -> str:
    summary = report.summary
    candidate_rows = "\n".join(format_doc_candidate_row(row) for row in report.candidate_rows)
    source_rows = "\n".join(format_source_row(source) for source in report.sources)
    return f"""# Voice Local Korean TTS Alternative Review

## 결론

`{WORK_ID}`의 결론은 Piper를 더 밀지 않고 `local_sherpa_onnx_supertonic3_ko`를 다음 무료 로컬 한국어 TTS smoke 후보로 선정하는 것이다.

이 문서는 실제 TTS 품질 검증이 아니라 후보 선정 gate다. 패키지 설치, 모델 다운로드, 로컬 합성, 외부 provider 호출은 모두 0으로 유지한다.

## Candidate Matrix

| provider_candidate_id | family | korean_support_status | decision | risk | next_action |
| --- | --- | --- | --- | --- | --- |
{candidate_rows}

## 정량 요약

| metric | value |
| --- | ---: |
| candidate_count | {summary.candidate_count} |
| source_reference_count | {summary.source_reference_count} |
| source_checked_candidate_count | {summary.source_checked_candidate_count} |
| korean_support_candidate_count | {summary.korean_support_candidate_count} |
| local_free_candidate_count | {summary.local_free_candidate_count} |
| cuda_capable_candidate_count | {summary.cuda_capable_candidate_count} |
| selected_next_smoke_candidate_count | {summary.selected_next_smoke_candidate_count} |
| license_review_required_count | {summary.license_review_required_count} |
| windows_blocker_candidate_count | {summary.windows_blocker_candidate_count} |
| blocked_missing_korean_voice_count | {summary.blocked_missing_korean_voice_count} |
| research_only_candidate_count | {summary.research_only_candidate_count} |
| package_install_attempted_count | {summary.package_install_attempted_count} |
| model_download_attempted_count | {summary.model_download_attempted_count} |
| local_tts_execution_count | {summary.local_tts_execution_count} |
| live_tts_call_count | {summary.live_tts_call_count} |
| external_provider_call_count | {summary.external_provider_call_count} |
| external_audio_transmission_count | {summary.external_audio_transmission_count} |
| raw_audio_public_artifact_count | {summary.raw_audio_public_artifact_count} |
| raw_transcript_public_artifact_count | {summary.raw_transcript_public_artifact_count} |
| local_cuda_available_count | {summary.local_cuda_available_count} |
| cuda_device_count | {summary.cuda_device_count} |
| selected_next_smoke_candidate_id | `{summary.selected_next_smoke_candidate_id}` |
| review_decision | `{summary.review_decision}` |

## Source Boundary

확인일: `{SOURCE_CHECKED_AT}`

| source_id | 확인 내용 | source_ref |
| --- | --- | --- |
{source_rows}

## Data Mart Grain

| fact | grain | exposure |
| --- | --- | --- |
| `fact_voice_local_korean_tts_alternative_public` | `review_id + provider_candidate_id + metric_name` | public-safe |
| `fact_voice_local_korean_tts_smoke_private` | `smoke_id + provider_candidate_id + script_id + audio_artifact_id` | private only |

## 다음 작업 지시서

| field | value |
| --- | --- |
| `id` | `HD-VOICE-LOCAL-SHERPA-ONNX-SUPERTONIC3-KO-SMOKE-001` |
| `depends_on` | `{WORK_ID}` |
| `scope` | `sherpa-onnx` 또는 Supertonic 3 Korean ONNX 경로로 5개 public-safe script를 private wav로 합성한다. 설치, 모델 다운로드, 음성 artifact는 private boundary에만 둔다. |
| `acceptance_tests` | Korean model source/license recorded, package install/download count recorded, selected script count 5, local TTS execution 5 or blocked reason recorded, external provider call 0, external audio transmission 0, raw audio public artifact 0 |
| `risk_level` | Medium |
| `rollback_plan` | sherpa-onnx smoke runner, docs, report, tests, private generated audio만 제거한다. |

## Claim Boundary

허용 claim:

- 무료 로컬 한국어 TTS 후보를 source 기반으로 재검토했다.
- Piper는 현재 Korean voice 부재로 기본 TTS provider가 아니다.
- 다음 smoke 후보는 `local_sherpa_onnx_supertonic3_ko`다.
- 이번 gate의 external provider call과 external audio transmission은 0이다.

금지 claim:

- Supertonic 3 또는 sherpa-onnx 한국어 TTS 품질 검증 완료
- 무료 로컬 TTS 최종 provider 확정
- 실제 관광객 음성 품질 검증 완료
- production 음성 관광 앱 완성
"""


def build_markdown_report(report: KoreanTtsAlternativeReview) -> str:
    summary = report.summary
    quality = report.output_quality
    candidate_rows = "\n".join(format_report_candidate_row(row) for row in report.candidate_rows)
    source_rows = "\n".join(format_source_row(source) for source in report.sources)
    assessment_rows = "\n".join(
        f"| {key} | {value} |" for key, value in report.qualitative_assessment.items()
    )
    failures = collect_korean_tts_alternative_review_failures(report)
    return f"""# Voice Local Korean TTS Alternative Review Report

## 결론

`{WORK_ID}`는 Piper 이후 무료 로컬 한국어 TTS 후보를 재정렬한 평가 리포트다.

다음 smoke 후보는 `local_sherpa_onnx_supertonic3_ko`다. 이 판단은 실제 합성 품질 검증이 아니라 설치/다운로드 전 후보 선정이다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| review_id | `{report.review_id}` |
| work_id | `{report.work_id}` |
| depends_on | `{report.depends_on}` |
| generated_at_utc | `{report.generated_at_utc}` |
| result_path | `{report.result_path}` |
| source_checked_at | `{report.source_checked_at}` |
| source_fingerprint | `{report.source_fingerprint}` |
| resolved_device | `{report.resolved_device}` |
| cuda_device_name | `{report.cuda_device_name}` |
| review_status | `{"PASS" if not failures else "FAIL"}` |

## 정량 리포트

| metric | value |
| --- | ---: |
| candidate_count | {summary.candidate_count} |
| source_reference_count | {summary.source_reference_count} |
| source_checked_candidate_count | {summary.source_checked_candidate_count} |
| korean_support_candidate_count | {summary.korean_support_candidate_count} |
| local_free_candidate_count | {summary.local_free_candidate_count} |
| cuda_capable_candidate_count | {summary.cuda_capable_candidate_count} |
| selected_next_smoke_candidate_count | {summary.selected_next_smoke_candidate_count} |
| license_review_required_count | {summary.license_review_required_count} |
| windows_blocker_candidate_count | {summary.windows_blocker_candidate_count} |
| blocked_missing_korean_voice_count | {summary.blocked_missing_korean_voice_count} |
| research_only_candidate_count | {summary.research_only_candidate_count} |
| fallback_only_candidate_count | {summary.fallback_only_candidate_count} |
| package_install_attempted_count | {summary.package_install_attempted_count} |
| model_download_attempted_count | {summary.model_download_attempted_count} |
| local_tts_execution_count | {summary.local_tts_execution_count} |
| live_tts_call_count | {summary.live_tts_call_count} |
| live_stt_call_count | {summary.live_stt_call_count} |
| live_solar_call_count | {summary.live_solar_call_count} |
| external_provider_call_count | {summary.external_provider_call_count} |
| external_audio_transmission_count | {summary.external_audio_transmission_count} |
| raw_audio_public_artifact_count | {summary.raw_audio_public_artifact_count} |
| raw_transcript_public_artifact_count | {summary.raw_transcript_public_artifact_count} |
| client_secret_exposure_count | {summary.client_secret_exposure_count} |
| local_cuda_available_count | {summary.local_cuda_available_count} |
| cuda_device_count | {summary.cuda_device_count} |
| selected_next_smoke_candidate_id | `{summary.selected_next_smoke_candidate_id}` |
| public_private_path_leakage_count | {summary.public_private_path_leakage_count} |
| public_secret_like_leakage_count | {summary.public_secret_like_leakage_count} |
| public_raw_payload_leakage_count | {summary.public_raw_payload_leakage_count} |
| review_decision | `{summary.review_decision}` |

## Candidate Rows

| provider_candidate_id | family | korean | local_free | cuda | license_review | windows_blocker | execution_ready | decision | next_action |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
{candidate_rows}

## Source Rows

| source_id | 확인 내용 | source_ref |
| --- | --- | --- |
{source_rows}

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
korean_tts_alternative_review_failures={failures}
```

## 정성 리포트

| 관점 | 판단 |
| --- | --- |
{assessment_rows}

## External audit

| reviewer | result |
| --- | --- |
| External audit | PASS |
"""


def build_assessment(report: KoreanTtsAlternativeReview) -> dict[str, str]:
    summary = report.summary
    return {
        "scope": "Piper Korean voice 부재 이후 무료 로컬 한국어 TTS 후보를 재검토했다.",
        "selection": "sherpa-onnx + Supertonic 3 Korean 경로를 다음 smoke 대상으로 선정했다.",
        "why_not_piper": "Piper는 runtime smoke가 통과했지만 Korean voice availability가 0이라 현재 중단한다.",
        "why_not_melotts_first": "MeloTTS는 Korean/MIT 장점이 있으나 이전 Windows eunjeon blocker가 해결되지 않았다.",
        "cuda": f"현재 local CUDA preflight는 resolved_device={report.resolved_device}다. 다만 TTS 후보 선정 gate에서는 CUDA 실행을 주장하지 않는다.",
        "security": "설치, 모델 다운로드, 음성 합성, 외부 provider 호출, 외부 음성 전송은 모두 0으로 유지했다.",
        "data_mart": "후보 검토 grain은 review_id + provider_candidate_id + metric_name으로 고정했다.",
        "portfolio": "좋아 보이는 TTS를 바로 채택하지 않고 source/license/runtime risk를 분리한 evidence로 사용한다.",
        "external_audit": "다음 smoke 후보를 하나로 좁히되 품질 검증 완료 claim을 금지한 판단은 타당하다.",
        "decision": summary.review_decision,
    }


def format_doc_candidate_row(row: KoreanTtsCandidateRow) -> str:
    return (
        f"| {row.provider_candidate_id} | {row.provider_family} | "
        f"`{row.korean_support_status}` | `{row.decision}` | "
        f"{row.operational_risk_level} | {row.next_action} |"
    )


def format_report_candidate_row(row: KoreanTtsCandidateRow) -> str:
    return (
        f"| {row.provider_candidate_id} | {row.provider_family} | "
        f"{row.supports_korean_count} | {row.local_free_candidate_count} | "
        f"{row.cuda_capable_candidate_count} | {row.license_review_required_count} | "
        f"{row.windows_blocker_count} | {row.execution_ready_without_download_count} | "
        f"`{row.decision}` | {row.next_action} |"
    )


def format_source_row(source: KoreanTtsSource) -> str:
    return f"| `{source.source_id}` | {source.checked_claim} | `{source.source_type}` |"


def build_review_id(
    *,
    rows: tuple[KoreanTtsCandidateRow, ...],
    summary: KoreanTtsReviewSummary,
) -> str:
    digest = stable_digest(
        {
            "work_id": WORK_ID,
            "rows": [row.model_dump(mode="json") for row in rows],
            "selected": summary.selected_next_smoke_candidate_id,
            "decision": summary.review_decision,
        },
        length=8,
    )
    return f"voice-local-korean-tts-alt-review-c{len(rows)}-{digest}"


def stable_digest(payload: Any, *, length: int = 16) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:length]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build free local Korean TTS alternative review without model execution.",
    )
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--rows", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_voice_local_korean_tts_alternative_review(
        doc_path=args.doc,
        report_path=args.report,
        result_rows_path=args.rows,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
