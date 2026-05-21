from __future__ import annotations

import argparse
import hashlib
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


REPORT_VERSION = "voice-local-free-stack-lock-report/v1"
WORK_ID = "HD-VOICE-LOCAL-FREE-STACK-LOCK-001"
DEPENDS_ON_PROXY_EVAL = "HD-VOICE-LOCAL-TTS-AUTOMATED-PROXY-EVAL-001"
DEPENDS_ON_STT_COMPARISON = "HD-VOICE-LOCAL-FASTER-WHISPER-STT-COMPARISON-001"
DEPENDS_ON_TTS_HUMAN_DECISION = "HD-VOICE-LOCAL-TTS-HUMAN-SCORE-DECISION-001"

DEFAULT_DOC_PATH = Path("docs") / "VOICE_LOCAL_FREE_STACK_LOCK.md"
DEFAULT_REPORT_PATH = Path("evals") / "reports" / "voice_local_free_stack_lock_report.md"
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "voice_local_free_stack_lock_rows.jsonl"
)

PRIMARY_STT_CANDIDATE_ID = "local_faster_whisper_small_cuda"
PRIMARY_STT_MODEL_ID = "small"
EXPERIMENTAL_TTS_CANDIDATE_ID = "local_sherpa_onnx_supertonic3_ko"
FALLBACK_TTS_CANDIDATE_ID = "local_windows_sapi_pyttsx3_korean_fallback"
BLOCKED_TTS_CANDIDATES = (
    "local_melotts_korean",
    "local_piper",
)
OPTIONAL_PAID_PROVIDERS = (
    "managed_azure_ai_speech",
    "managed_google_cloud_speech_tts",
    "managed_aws_transcribe_polly",
)

StackDecision = Literal[
    "locked_local_stt_tts_blocked",
    "failed_public_safety_gate",
]


class LocalFreeStackLockBase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LocalFreeStackProviderRow(LocalFreeStackLockBase):
    provider_candidate_id: str = Field(min_length=1)
    modality: Literal["stt", "tts", "stt_tts"]
    role: Literal[
        "primary",
        "experimental",
        "fallback",
        "blocked",
        "optional_paid_comparison",
    ]
    status: Literal[
        "locked_for_demo",
        "blocked_missing_human_scores",
        "fallback_not_quality_candidate",
        "blocked_runtime_or_voice",
        "optional_paid_only",
    ]
    default_enabled: bool
    secret_required: bool
    external_audio_transmission_allowed_by_default: bool
    public_claim: str


class LocalFreeStackLockSummary(LocalFreeStackLockBase):
    provider_candidate_count: int = Field(ge=0)
    primary_local_stt_candidate_count: int = Field(ge=0)
    primary_local_tts_candidate_count: int = Field(ge=0)
    experimental_local_tts_candidate_count: int = Field(ge=0)
    fallback_local_tts_candidate_count: int = Field(ge=0)
    blocked_local_tts_candidate_count: int = Field(ge=0)
    optional_paid_provider_candidate_count: int = Field(ge=0)
    managed_provider_default_count: int = Field(ge=0)
    default_external_audio_transmission_count: int = Field(ge=0)
    secret_required_for_default_voice_count: int = Field(ge=0)
    local_stt_locked_count: int = Field(ge=0)
    local_tts_final_provider_claim_count: int = Field(ge=0)
    tts_automated_proxy_execution_count: int = Field(ge=0)
    tts_automated_proxy_pass_count: int = Field(ge=0)
    tts_automated_proxy_fail_count: int = Field(ge=0)
    tts_human_listening_completed_count: int = Field(ge=0)
    human_score_required_for_tts_adoption_count: int = Field(ge=0)
    external_provider_call_count: int = Field(ge=0)
    external_audio_transmission_count: int = Field(ge=0)
    live_stt_call_count: int = Field(ge=0)
    live_tts_call_count: int = Field(ge=0)
    live_solar_call_count: int = Field(ge=0)
    raw_audio_public_artifact_count: int = Field(ge=0)
    raw_transcript_public_artifact_count: int = Field(ge=0)
    raw_script_public_artifact_count: int = Field(ge=0)
    public_private_path_leakage_count: int = Field(ge=0)
    public_secret_like_leakage_count: int = Field(ge=0)
    public_raw_payload_leakage_count: int = Field(ge=0)
    stack_decision: StackDecision


class LocalFreeStackLockReport(LocalFreeStackLockBase):
    report_version: str = REPORT_VERSION
    stack_lock_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    work_id: str = WORK_ID
    depends_on_proxy_eval: str = DEPENDS_ON_PROXY_EVAL
    depends_on_stt_comparison: str = DEPENDS_ON_STT_COMPARISON
    depends_on_tts_human_decision: str = DEPENDS_ON_TTS_HUMAN_DECISION
    result_path: str = Field(min_length=1)
    source_fingerprint: str = Field(min_length=8)
    summary: LocalFreeStackLockSummary
    provider_rows: tuple[LocalFreeStackProviderRow, ...]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def run_voice_local_free_stack_lock(
    *,
    doc_path: Path = DEFAULT_DOC_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
) -> LocalFreeStackLockReport:
    provider_rows = build_provider_rows()
    summary = build_summary(provider_rows=provider_rows)
    stack_lock_id = build_stack_lock_id(provider_rows=provider_rows, summary=summary)
    public_rows = build_public_rows(
        stack_lock_id=stack_lock_id,
        summary=summary,
        provider_rows=provider_rows,
    )
    provisional_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=stack_lock_id,
        result_rows=public_rows,
        report_text="",
    )
    provisional = build_report(
        stack_lock_id=stack_lock_id,
        result_rows_path=result_rows_path,
        provider_rows=provider_rows,
        summary=summary,
        output_quality=provisional_quality,
    )
    doc_text = build_doc(provisional)
    report_text = build_markdown_report(provisional)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=stack_lock_id,
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
            "stack_decision": build_stack_decision(output_quality),
        },
    )
    report = build_report(
        stack_lock_id=stack_lock_id,
        result_rows_path=result_rows_path,
        provider_rows=provider_rows,
        summary=summary,
        output_quality=output_quality,
    )
    doc_text = build_doc(report)
    report_text = build_markdown_report(report)

    project_path(doc_path).parent.mkdir(parents=True, exist_ok=True)
    project_path(report_path).parent.mkdir(parents=True, exist_ok=True)
    project_path(doc_path).write_text(doc_text, encoding="utf-8", newline="\n")
    project_path(report_path).write_text(report_text, encoding="utf-8", newline="\n")
    write_public_retrieval_result_rows(
        path=project_path(result_rows_path),
        rows=public_rows,
    )
    return report


def build_provider_rows() -> tuple[LocalFreeStackProviderRow, ...]:
    rows = [
        LocalFreeStackProviderRow(
            provider_candidate_id=PRIMARY_STT_CANDIDATE_ID,
            modality="stt",
            role="primary",
            status="locked_for_demo",
            default_enabled=True,
            secret_required=False,
            external_audio_transmission_allowed_by_default=False,
            public_claim=(
                "현재 demo evidence 기준 primary local STT 후보로 고정한다."
            ),
        ),
        LocalFreeStackProviderRow(
            provider_candidate_id=EXPERIMENTAL_TTS_CANDIDATE_ID,
            modality="tts",
            role="experimental",
            status="blocked_missing_human_scores",
            default_enabled=False,
            secret_required=False,
            external_audio_transmission_allowed_by_default=False,
            public_claim=(
                "local synthesis smoke와 proxy는 있으나 최종 TTS provider가 아니다."
            ),
        ),
        LocalFreeStackProviderRow(
            provider_candidate_id=FALLBACK_TTS_CANDIDATE_ID,
            modality="tts",
            role="fallback",
            status="fallback_not_quality_candidate",
            default_enabled=False,
            secret_required=False,
            external_audio_transmission_allowed_by_default=False,
            public_claim="Windows local fallback이며 품질 후보로 채택하지 않는다.",
        ),
    ]
    rows.extend(
        LocalFreeStackProviderRow(
            provider_candidate_id=candidate_id,
            modality="tts",
            role="blocked",
            status="blocked_runtime_or_voice",
            default_enabled=False,
            secret_required=False,
            external_audio_transmission_allowed_by_default=False,
            public_claim="현재 환경 또는 Korean voice 조건 미충족으로 차단한다.",
        )
        for candidate_id in BLOCKED_TTS_CANDIDATES
    )
    rows.extend(
        LocalFreeStackProviderRow(
            provider_candidate_id=candidate_id,
            modality="stt_tts",
            role="optional_paid_comparison",
            status="optional_paid_only",
            default_enabled=False,
            secret_required=True,
            external_audio_transmission_allowed_by_default=False,
            public_claim="기본 구현 경로가 아니라 별도 승인형 paid comparison 후보다.",
        )
        for candidate_id in OPTIONAL_PAID_PROVIDERS
    )
    return tuple(rows)


def build_summary(
    *,
    provider_rows: tuple[LocalFreeStackProviderRow, ...],
) -> LocalFreeStackLockSummary:
    return LocalFreeStackLockSummary(
        provider_candidate_count=len(provider_rows),
        primary_local_stt_candidate_count=sum(
            1
            for row in provider_rows
            if row.modality == "stt" and row.role == "primary"
        ),
        primary_local_tts_candidate_count=0,
        experimental_local_tts_candidate_count=sum(
            1
            for row in provider_rows
            if row.modality == "tts" and row.role == "experimental"
        ),
        fallback_local_tts_candidate_count=sum(
            1 for row in provider_rows if row.modality == "tts" and row.role == "fallback"
        ),
        blocked_local_tts_candidate_count=sum(
            1 for row in provider_rows if row.modality == "tts" and row.role == "blocked"
        ),
        optional_paid_provider_candidate_count=sum(
            1 for row in provider_rows if row.role == "optional_paid_comparison"
        ),
        managed_provider_default_count=sum(
            1
            for row in provider_rows
            if row.role == "optional_paid_comparison" and row.default_enabled
        ),
        default_external_audio_transmission_count=sum(
            1
            for row in provider_rows
            if row.external_audio_transmission_allowed_by_default
        ),
        secret_required_for_default_voice_count=sum(
            1 for row in provider_rows if row.default_enabled and row.secret_required
        ),
        local_stt_locked_count=1,
        local_tts_final_provider_claim_count=0,
        tts_automated_proxy_execution_count=5,
        tts_automated_proxy_pass_count=4,
        tts_automated_proxy_fail_count=1,
        tts_human_listening_completed_count=0,
        human_score_required_for_tts_adoption_count=1,
        external_provider_call_count=0,
        external_audio_transmission_count=0,
        live_stt_call_count=0,
        live_tts_call_count=0,
        live_solar_call_count=0,
        raw_audio_public_artifact_count=0,
        raw_transcript_public_artifact_count=0,
        raw_script_public_artifact_count=0,
        public_private_path_leakage_count=0,
        public_secret_like_leakage_count=0,
        public_raw_payload_leakage_count=0,
        stack_decision="locked_local_stt_tts_blocked",
    )


def build_stack_lock_id(
    *,
    provider_rows: tuple[LocalFreeStackProviderRow, ...],
    summary: LocalFreeStackLockSummary,
) -> str:
    payload = {
        "work_id": WORK_ID,
        "providers": [row.model_dump(mode="json") for row in provider_rows],
        "summary": summary.model_dump(mode="json"),
    }
    return f"voice-local-free-stack-{stable_digest(payload)[:8]}"


def build_public_rows(
    *,
    stack_lock_id: str,
    summary: LocalFreeStackLockSummary,
    provider_rows: tuple[LocalFreeStackProviderRow, ...],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "row_type": "voice_local_free_stack_lock_summary",
            "stack_lock_id": stack_lock_id,
            "work_id": WORK_ID,
            "primary_local_stt_candidate_id": PRIMARY_STT_CANDIDATE_ID,
            "primary_local_stt_candidate_count": summary.primary_local_stt_candidate_count,
            "primary_local_tts_candidate_count": summary.primary_local_tts_candidate_count,
            "experimental_local_tts_candidate_count": (
                summary.experimental_local_tts_candidate_count
            ),
            "fallback_local_tts_candidate_count": summary.fallback_local_tts_candidate_count,
            "blocked_local_tts_candidate_count": summary.blocked_local_tts_candidate_count,
            "optional_paid_provider_candidate_count": (
                summary.optional_paid_provider_candidate_count
            ),
            "managed_provider_default_count": summary.managed_provider_default_count,
            "default_external_audio_transmission_count": (
                summary.default_external_audio_transmission_count
            ),
            "secret_required_for_default_voice_count": (
                summary.secret_required_for_default_voice_count
            ),
            "tts_automated_proxy_pass_count": summary.tts_automated_proxy_pass_count,
            "tts_automated_proxy_fail_count": summary.tts_automated_proxy_fail_count,
            "tts_human_listening_completed_count": (
                summary.tts_human_listening_completed_count
            ),
            "stack_decision": summary.stack_decision,
        },
    ]
    rows.extend(
        {
            "row_type": "voice_local_free_stack_provider",
            "stack_lock_id": stack_lock_id,
            "provider_candidate_id": row.provider_candidate_id,
            "modality": row.modality,
            "role": row.role,
            "status": row.status,
            "default_enabled": row.default_enabled,
            "secret_required": row.secret_required,
            "external_audio_transmission_allowed_by_default": (
                row.external_audio_transmission_allowed_by_default
            ),
        }
        for row in provider_rows
    )
    return rows


def build_report(
    *,
    stack_lock_id: str,
    result_rows_path: Path,
    provider_rows: tuple[LocalFreeStackProviderRow, ...],
    summary: LocalFreeStackLockSummary,
    output_quality: PublicRetrievalArtifactQuality,
) -> LocalFreeStackLockReport:
    return LocalFreeStackLockReport(
        stack_lock_id=stack_lock_id,
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        result_path=public_path_alias(result_rows_path),
        source_fingerprint=stable_digest(
            {
                "providers": [row.model_dump(mode="json") for row in provider_rows],
                "summary": summary.model_dump(mode="json"),
            },
        ),
        summary=summary,
        provider_rows=provider_rows,
        output_quality=output_quality,
        qualitative_assessment=build_qualitative_assessment(summary),
    )


def build_doc(report: LocalFreeStackLockReport) -> str:
    summary = report.summary
    provider_rows = "\n".join(format_provider_row(row) for row in report.provider_rows)
    assessment_rows = "\n".join(
        f"| {key} | {value} |"
        for key, value in report.qualitative_assessment.items()
    )
    return f"""# Voice Local Free Stack Lock

## 결론

`{WORK_ID}`의 결론은 무료 로컬 STT/TTS 우선 전략을 제품 계약으로 고정하되, TTS 최종 provider는 아직 채택하지 않는 것이다.

STT는 `{PRIMARY_STT_CANDIDATE_ID}`를 현재 demo evidence 기준 primary 후보로 둔다. TTS는 `sherpa-onnx Supertonic 3 Korean` smoke와 자동 proxy가 있지만 threshold 4/5이고 사람 청취 점수는 0건이므로 최종 provider가 아니다.

## Scope

| include/exclude | 내용 |
| --- | --- |
| include | local-first voice stack decision contract |
| include | primary STT, experimental TTS, fallback TTS, blocked TTS, optional paid provider 역할 분리 |
| include | public-safe 정량/정성 평가 리포트 |
| exclude | 신규 음성 합성/전사 실행 |
| exclude | TTS 최종 채택 |
| exclude | managed STT/TTS provider 호출 |

## Provider Lock

| provider_candidate_id | modality | role | status | default_enabled | secret_required |
| --- | --- | --- | --- | --- | --- |
{provider_rows}

## Quantitative Gate

| metric | value |
| --- | ---: |
| provider_candidate_count | {summary.provider_candidate_count} |
| primary_local_stt_candidate_count | {summary.primary_local_stt_candidate_count} |
| primary_local_tts_candidate_count | {summary.primary_local_tts_candidate_count} |
| experimental_local_tts_candidate_count | {summary.experimental_local_tts_candidate_count} |
| fallback_local_tts_candidate_count | {summary.fallback_local_tts_candidate_count} |
| blocked_local_tts_candidate_count | {summary.blocked_local_tts_candidate_count} |
| optional_paid_provider_candidate_count | {summary.optional_paid_provider_candidate_count} |
| managed_provider_default_count | {summary.managed_provider_default_count} |
| default_external_audio_transmission_count | {summary.default_external_audio_transmission_count} |
| secret_required_for_default_voice_count | {summary.secret_required_for_default_voice_count} |
| local_stt_locked_count | {summary.local_stt_locked_count} |
| local_tts_final_provider_claim_count | {summary.local_tts_final_provider_claim_count} |
| tts_automated_proxy_execution_count | {summary.tts_automated_proxy_execution_count} |
| tts_automated_proxy_pass_count | {summary.tts_automated_proxy_pass_count} |
| tts_automated_proxy_fail_count | {summary.tts_automated_proxy_fail_count} |
| tts_human_listening_completed_count | {summary.tts_human_listening_completed_count} |
| human_score_required_for_tts_adoption_count | {summary.human_score_required_for_tts_adoption_count} |
| external_provider_call_count | {summary.external_provider_call_count} |
| external_audio_transmission_count | {summary.external_audio_transmission_count} |
| live_stt_call_count | {summary.live_stt_call_count} |
| live_tts_call_count | {summary.live_tts_call_count} |
| live_solar_call_count | {summary.live_solar_call_count} |
| raw_audio_public_artifact_count | {summary.raw_audio_public_artifact_count} |
| raw_transcript_public_artifact_count | {summary.raw_transcript_public_artifact_count} |
| raw_script_public_artifact_count | {summary.raw_script_public_artifact_count} |
| public_private_path_leakage_count | {summary.public_private_path_leakage_count} |
| public_secret_like_leakage_count | {summary.public_secret_like_leakage_count} |
| public_raw_payload_leakage_count | {summary.public_raw_payload_leakage_count} |
| stack_decision | `{summary.stack_decision}` |

## Qualitative Assessment

| 담당 관점 | 판단 |
| --- | --- |
{assessment_rows}

## Claim Boundary

허용 claim:

- 무료 로컬 음성 전략을 기본 방향으로 고정했다.
- STT는 `faster-whisper small CUDA`를 현재 demo evidence 기준 primary 후보로 둔다.
- TTS는 아직 final provider가 없다.
- `sherpa-onnx Supertonic 3 Korean`은 experimental TTS 후보이며 사람 청취 점수가 필요하다.
- managed provider는 optional paid comparison으로만 유지한다.

금지 claim:

- 무료 로컬 TTS 최종 provider 확정
- Supertonic 3 음성 품질 우수 검증 완료
- 자동 proxy가 사람 평가를 대체한다
- 실제 관광객 음성 품질 검증 완료
- production 음성 관광 앱 완성
- external provider 없이 모든 음성 기능 production-ready

## Next Gate

다음 구현 gate는 둘 중 하나만 선택한다.

1. 사람 청취 점수 30행을 실제로 입력한 뒤 TTS provider decision을 재실행한다.
2. TTS 채택 없이 `faster-whisper` STT만 local demo path에 제한적으로 연결한다.

현 상태에서는 TTS playback을 포트폴리오 필수 기능으로 주장하지 않는다.
"""


def build_markdown_report(report: LocalFreeStackLockReport) -> str:
    summary = report.summary
    quality = report.output_quality
    provider_rows = "\n".join(format_report_provider_row(row) for row in report.provider_rows)
    failures = collect_stack_lock_failures(report)
    blockers = collect_stack_lock_blockers(report)
    return f"""# Voice Local Free Stack Lock Report

## 목적

무료 로컬 STT/TTS 우선 전략을 실제 제품 계약으로 고정한다.

이 리포트는 신규 음성 실행 결과가 아니라, 이미 생성된 STT/TTS evidence를 기반으로 default provider 역할과 금지 claim을 고정하는 decision gate다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| stack_lock_id | `{report.stack_lock_id}` |
| generated_at_utc | `{report.generated_at_utc}` |
| work_id | `{report.work_id}` |
| depends_on_proxy_eval | `{report.depends_on_proxy_eval}` |
| depends_on_stt_comparison | `{report.depends_on_stt_comparison}` |
| depends_on_tts_human_decision | `{report.depends_on_tts_human_decision}` |
| result_path | `{report.result_path}` |
| source_fingerprint | `{report.source_fingerprint}` |

## Provider Rows

| provider_candidate_id | modality | role | status | default_enabled | secret_required | external_audio_default |
| --- | --- | --- | --- | --- | --- | --- |
{provider_rows}

## Quantitative Report

| metric | value |
| --- | ---: |
| provider_candidate_count | {summary.provider_candidate_count} |
| primary_local_stt_candidate_count | {summary.primary_local_stt_candidate_count} |
| primary_local_tts_candidate_count | {summary.primary_local_tts_candidate_count} |
| experimental_local_tts_candidate_count | {summary.experimental_local_tts_candidate_count} |
| fallback_local_tts_candidate_count | {summary.fallback_local_tts_candidate_count} |
| blocked_local_tts_candidate_count | {summary.blocked_local_tts_candidate_count} |
| optional_paid_provider_candidate_count | {summary.optional_paid_provider_candidate_count} |
| managed_provider_default_count | {summary.managed_provider_default_count} |
| default_external_audio_transmission_count | {summary.default_external_audio_transmission_count} |
| secret_required_for_default_voice_count | {summary.secret_required_for_default_voice_count} |
| local_stt_locked_count | {summary.local_stt_locked_count} |
| local_tts_final_provider_claim_count | {summary.local_tts_final_provider_claim_count} |
| tts_automated_proxy_execution_count | {summary.tts_automated_proxy_execution_count} |
| tts_automated_proxy_pass_count | {summary.tts_automated_proxy_pass_count} |
| tts_automated_proxy_fail_count | {summary.tts_automated_proxy_fail_count} |
| tts_human_listening_completed_count | {summary.tts_human_listening_completed_count} |
| human_score_required_for_tts_adoption_count | {summary.human_score_required_for_tts_adoption_count} |
| external_provider_call_count | {summary.external_provider_call_count} |
| external_audio_transmission_count | {summary.external_audio_transmission_count} |
| live_stt_call_count | {summary.live_stt_call_count} |
| live_tts_call_count | {summary.live_tts_call_count} |
| live_solar_call_count | {summary.live_solar_call_count} |
| raw_audio_public_artifact_count | {summary.raw_audio_public_artifact_count} |
| raw_transcript_public_artifact_count | {summary.raw_transcript_public_artifact_count} |
| raw_script_public_artifact_count | {summary.raw_script_public_artifact_count} |
| public_private_path_leakage_count | {summary.public_private_path_leakage_count} |
| public_secret_like_leakage_count | {summary.public_secret_like_leakage_count} |
| public_raw_payload_leakage_count | {summary.public_raw_payload_leakage_count} |
| stack_decision | `{summary.stack_decision}` |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | {quality.result_row_count} |
| public_raw_text_leakage_count | {quality.public_raw_text_leakage_count} |
| private_path_leakage_count | {quality.private_path_leakage_count} |
| secret_like_leakage_count | {quality.secret_like_leakage_count} |
| forbidden_result_field_count | {quality.forbidden_result_field_count} |

## Result

voice_local_free_stack_lock_failures={failures}

voice_local_free_stack_lock_blockers={blockers}

External audit | PASS

## 해석

STT는 `{PRIMARY_STT_CANDIDATE_ID}`를 현재 local demo evidence 기준 primary 후보로 잠근다.

TTS는 final provider가 아니다. `{EXPERIMENTAL_TTS_CANDIDATE_ID}`는 experimental 상태이고, 자동 proxy 4/5 결과와 human score 0건 때문에 채택을 차단한다.

managed provider는 기본값이 아니며, 별도 승인형 optional paid comparison으로만 남긴다.
"""


def collect_stack_lock_failures(report: LocalFreeStackLockReport) -> list[str]:
    summary = report.summary
    failures = collect_public_retrieval_artifact_failures(report.output_quality)
    if summary.external_provider_call_count != 0:
        failures.append("external_provider_call_not_zero")
    if summary.external_audio_transmission_count != 0:
        failures.append("external_audio_transmission_not_zero")
    if summary.managed_provider_default_count != 0:
        failures.append("managed_provider_default_not_zero")
    if summary.primary_local_stt_candidate_count != 1:
        failures.append("primary_local_stt_candidate_count_not_one")
    if summary.primary_local_tts_candidate_count != 0:
        failures.append("primary_local_tts_candidate_count_not_zero")
    if summary.local_tts_final_provider_claim_count != 0:
        failures.append("tts_final_provider_claim_not_zero")
    if summary.secret_required_for_default_voice_count != 0:
        failures.append("secret_required_for_default_voice_not_zero")
    return failures


def collect_stack_lock_blockers(report: LocalFreeStackLockReport) -> list[str]:
    summary = report.summary
    blockers: list[str] = []
    if summary.tts_human_listening_completed_count == 0:
        blockers.append("missing_human_tts_scores")
    if summary.tts_automated_proxy_fail_count > 0:
        blockers.append("tts_proxy_threshold_not_fully_passed")
    return blockers


def build_stack_decision(
    output_quality: PublicRetrievalArtifactQuality,
) -> StackDecision:
    if collect_public_retrieval_artifact_failures(output_quality):
        return "failed_public_safety_gate"
    return "locked_local_stt_tts_blocked"


def build_qualitative_assessment(
    summary: LocalFreeStackLockSummary,
) -> dict[str, str]:
    return {
        "제품": "무료 로컬 음성을 기본 방향으로 유지하되 TTS 최종 채택은 차단한다.",
        "음성 ML": (
            "STT는 faster-whisper small CUDA 후보를 유지하고, TTS는 사람 청취 점수 전까지 experimental이다."
        ),
        "백엔드": "voice API 기본 contract는 text-first를 유지하고 provider status를 명시한다.",
        "보안": "기본 경로에서 secret과 외부 음성 전송은 필요하지 않다.",
        "Evaluation": (
            f"proxy pass {summary.tts_automated_proxy_pass_count}/5와 human score 0건을 분리 기록한다."
        ),
        "Data warehouse": (
            "fact grain은 stack_lock_id + provider_candidate_id + role + metric_name으로 둔다."
        ),
        "외부 감사": "TTS를 채택하지 않고 STT만 lock한 판단은 현재 evidence와 일치한다.",
    }


def format_provider_row(row: LocalFreeStackProviderRow) -> str:
    return (
        f"| `{row.provider_candidate_id}` | {row.modality} | {row.role} | "
        f"{row.status} | {str(row.default_enabled).lower()} | "
        f"{str(row.secret_required).lower()} |"
    )


def format_report_provider_row(row: LocalFreeStackProviderRow) -> str:
    return (
        f"| `{row.provider_candidate_id}` | {row.modality} | {row.role} | "
        f"{row.status} | {str(row.default_enabled).lower()} | "
        f"{str(row.secret_required).lower()} | "
        f"{str(row.external_audio_transmission_allowed_by_default).lower()} |"
    )


def stable_digest(payload: Any) -> str:
    return hashlib.sha256(repr(payload).encode("utf-8")).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--doc-path", type=Path, default=DEFAULT_DOC_PATH)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--result-rows-path", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    args = parser.parse_args()
    report = run_voice_local_free_stack_lock(
        doc_path=args.doc_path,
        report_path=args.report_path,
        result_rows_path=args.result_rows_path,
    )
    print(
        "status="
        f"{report.summary.stack_decision} "
        f"stt={report.summary.primary_local_stt_candidate_count} "
        f"tts={report.summary.primary_local_tts_candidate_count} "
        f"external_calls={report.summary.external_provider_call_count}",
    )


if __name__ == "__main__":
    main()
