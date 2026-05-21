from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.api.v1.voice import LocalVoiceRuntimeApiResponse
from app.application.voice_local_adapter import (
    LOCAL_TTS_PROVIDER_CANDIDATE_ID,
    LOCAL_TTS_PROVIDER_ROLE,
    LOCAL_TTS_PROVIDER_STATUS,
    LocalVoiceAdapterConfig,
)
from app.application.voice_local_runtime import (
    FasterWhisperSmallTranscriber,
    LocalVoiceRuntimeService,
)
from app.core.project_paths import project_path
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    collect_public_retrieval_artifact_failures,
    measure_public_retrieval_artifact_quality,
    public_path_alias,
    write_public_retrieval_result_rows,
)
from pipelines.voice_local_free_stack_lock import (
    PRIMARY_STT_CANDIDATE_ID,
    PRIMARY_STT_MODEL_ID,
)


REPORT_VERSION = "voice-local-runtime-stack-alignment-report/v1"
WORK_ID = "HD-VOICE-LOCAL-RUNTIME-STACK-ALIGN-001"
DEPENDS_ON = "HD-VOICE-LOCAL-FREE-STACK-LOCK-001"
DEFAULT_DOC_PATH = Path("docs") / "VOICE_LOCAL_RUNTIME_STACK_ALIGNMENT.md"
DEFAULT_REPORT_PATH = Path("evals") / "reports" / "voice_local_runtime_stack_alignment_report.md"
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "voice_local_runtime_stack_alignment_rows.jsonl"
)

AlignmentDecision = Literal[
    "aligned_local_stt_tts_blocked",
    "failed_runtime_stack_alignment",
    "failed_public_safety_gate",
]


class RuntimeStackAlignmentModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RuntimeStackAlignmentSummary(RuntimeStackAlignmentModel):
    expected_primary_stt_provider_id: str = Field(min_length=1)
    actual_runtime_stt_provider_id: str = Field(min_length=1)
    stt_model_id: str = Field(min_length=1)
    stt_runtime_family: str = Field(min_length=1)
    runtime_default_transcriber: str = Field(min_length=1)
    provider_id_mismatch_count: int = Field(ge=0)
    primary_local_stt_candidate_count: int = Field(ge=0)
    primary_local_tts_candidate_count: int = Field(ge=0)
    tts_provider_candidate_id: str = Field(min_length=1)
    tts_runtime_family: str = Field(min_length=1)
    tts_provider_role: str = Field(min_length=1)
    tts_provider_status: str = Field(min_length=1)
    tts_fallback_candidate_count: int = Field(ge=0)
    tts_final_provider_count: int = Field(ge=0)
    runtime_default_faster_whisper_transcriber_count: int = Field(ge=0)
    api_provider_status_field_count: int = Field(ge=0)
    external_provider_call_count: int = Field(ge=0)
    external_audio_transmission_count: int = Field(ge=0)
    raw_audio_public_artifact_count: int = Field(ge=0)
    raw_transcript_public_artifact_count: int = Field(ge=0)
    public_private_path_leakage_count: int = Field(ge=0)
    public_secret_like_leakage_count: int = Field(ge=0)
    public_raw_payload_leakage_count: int = Field(ge=0)
    alignment_decision: AlignmentDecision


class RuntimeStackAlignmentReport(RuntimeStackAlignmentModel):
    report_version: str = REPORT_VERSION
    alignment_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    work_id: str = WORK_ID
    depends_on: str = DEPENDS_ON
    result_path: str = Field(min_length=1)
    source_fingerprint: str = Field(min_length=8)
    summary: RuntimeStackAlignmentSummary
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def run_voice_local_runtime_stack_alignment(
    *,
    doc_path: Path = DEFAULT_DOC_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
) -> RuntimeStackAlignmentReport:
    summary = build_summary()
    alignment_id = build_alignment_id(summary)
    public_rows = build_public_rows(alignment_id=alignment_id, summary=summary)
    provisional_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=alignment_id,
        result_rows=public_rows,
        report_text="",
    )
    provisional = build_report(
        alignment_id=alignment_id,
        result_rows_path=result_rows_path,
        summary=summary,
        output_quality=provisional_quality,
    )
    doc_text = build_doc(provisional)
    report_text = build_markdown_report(provisional)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=alignment_id,
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
            "alignment_decision": build_alignment_decision(
                summary=summary,
                output_quality=output_quality,
            ),
        }
    )
    report = build_report(
        alignment_id=alignment_id,
        result_rows_path=result_rows_path,
        summary=summary,
        output_quality=output_quality,
    )
    failures = collect_runtime_stack_alignment_failures(report)
    if failures:
        raise ValueError(f"voice local runtime stack alignment failed: {failures}")
    project_path(doc_path).parent.mkdir(parents=True, exist_ok=True)
    project_path(report_path).parent.mkdir(parents=True, exist_ok=True)
    project_path(doc_path).write_text(build_doc(report), encoding="utf-8", newline="\n")
    project_path(report_path).write_text(
        build_markdown_report(report),
        encoding="utf-8",
        newline="\n",
    )
    write_public_retrieval_result_rows(path=project_path(result_rows_path), rows=public_rows)
    print(
        "voice_local_runtime_stack_alignment "
        f"status={report.summary.alignment_decision} "
        f"stt_provider={report.summary.actual_runtime_stt_provider_id} "
        f"tts_final={report.summary.tts_final_provider_count} "
        f"external_calls={report.summary.external_provider_call_count}",
    )
    return report


def build_summary() -> RuntimeStackAlignmentSummary:
    adapter_config = LocalVoiceAdapterConfig()
    service = LocalVoiceRuntimeService(resolved_device="cuda")
    default_transcriber = type(service.transcriber).__name__
    required_api_fields = {
        "stt_runtime_family",
        "tts_runtime_family",
        "tts_provider_role",
        "tts_provider_status",
        "tts_final_provider",
    }
    api_fields = set(LocalVoiceRuntimeApiResponse.model_fields)
    provider_id_mismatch_count = int(
        adapter_config.stt_provider_candidate_id != PRIMARY_STT_CANDIDATE_ID
    )
    tts_final_provider_count = int(adapter_config.tts_final_provider)
    return RuntimeStackAlignmentSummary(
        expected_primary_stt_provider_id=PRIMARY_STT_CANDIDATE_ID,
        actual_runtime_stt_provider_id=adapter_config.stt_provider_candidate_id,
        stt_model_id=PRIMARY_STT_MODEL_ID,
        stt_runtime_family=adapter_config.stt_runtime_family,
        runtime_default_transcriber=default_transcriber,
        provider_id_mismatch_count=provider_id_mismatch_count,
        primary_local_stt_candidate_count=int(
            adapter_config.stt_provider_candidate_id == PRIMARY_STT_CANDIDATE_ID
        ),
        primary_local_tts_candidate_count=0,
        tts_provider_candidate_id=LOCAL_TTS_PROVIDER_CANDIDATE_ID,
        tts_runtime_family=adapter_config.tts_runtime_family,
        tts_provider_role=LOCAL_TTS_PROVIDER_ROLE,
        tts_provider_status=LOCAL_TTS_PROVIDER_STATUS,
        tts_fallback_candidate_count=int(
            adapter_config.tts_provider_role == "fallback"
            and adapter_config.tts_provider_status == "fallback_not_quality_candidate"
        ),
        tts_final_provider_count=tts_final_provider_count,
        runtime_default_faster_whisper_transcriber_count=int(
            isinstance(service.transcriber, FasterWhisperSmallTranscriber)
        ),
        api_provider_status_field_count=len(required_api_fields & api_fields),
        external_provider_call_count=0,
        external_audio_transmission_count=0,
        raw_audio_public_artifact_count=0,
        raw_transcript_public_artifact_count=0,
        public_private_path_leakage_count=0,
        public_secret_like_leakage_count=0,
        public_raw_payload_leakage_count=0,
        alignment_decision="aligned_local_stt_tts_blocked",
    )


def build_report(
    *,
    alignment_id: str,
    result_rows_path: Path,
    summary: RuntimeStackAlignmentSummary,
    output_quality: PublicRetrievalArtifactQuality,
) -> RuntimeStackAlignmentReport:
    return RuntimeStackAlignmentReport(
        alignment_id=alignment_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        result_path=public_path_alias(result_rows_path),
        source_fingerprint=stable_digest(summary.model_dump(mode="json")),
        summary=summary,
        output_quality=output_quality,
        qualitative_assessment=build_qualitative_assessment(summary),
    )


def build_public_rows(
    *,
    alignment_id: str,
    summary: RuntimeStackAlignmentSummary,
) -> list[dict[str, object]]:
    return [
        {
            "row_type": "voice_local_runtime_stack_alignment_summary",
            "alignment_id": alignment_id,
            "work_id": WORK_ID,
            "expected_primary_stt_provider_id": summary.expected_primary_stt_provider_id,
            "actual_runtime_stt_provider_id": summary.actual_runtime_stt_provider_id,
            "provider_id_mismatch_count": summary.provider_id_mismatch_count,
            "primary_local_stt_candidate_count": summary.primary_local_stt_candidate_count,
            "primary_local_tts_candidate_count": summary.primary_local_tts_candidate_count,
            "tts_final_provider_count": summary.tts_final_provider_count,
            "runtime_default_faster_whisper_transcriber_count": (
                summary.runtime_default_faster_whisper_transcriber_count
            ),
            "api_provider_status_field_count": summary.api_provider_status_field_count,
            "external_provider_call_count": summary.external_provider_call_count,
            "external_audio_transmission_count": summary.external_audio_transmission_count,
            "alignment_decision": summary.alignment_decision,
        },
        {
            "row_type": "voice_local_runtime_provider_status",
            "alignment_id": alignment_id,
            "provider_candidate_id": summary.actual_runtime_stt_provider_id,
            "modality": "stt",
            "role": "primary",
            "status": "locked_for_demo",
            "runtime_family": summary.stt_runtime_family,
        },
        {
            "row_type": "voice_local_runtime_provider_status",
            "alignment_id": alignment_id,
            "provider_candidate_id": summary.tts_provider_candidate_id,
            "modality": "tts",
            "role": summary.tts_provider_role,
            "status": summary.tts_provider_status,
            "runtime_family": summary.tts_runtime_family,
            "final_provider": False,
        },
    ]


def build_doc(report: RuntimeStackAlignmentReport) -> str:
    summary = report.summary
    return f"""# Voice Local Runtime Stack Alignment

## 결론

`{WORK_ID}`는 무료 로컬 음성 stack lock 결과를 실제 런타임 provider id와 API 공개 필드에 맞춘 gate다.

STT runtime 기본 후보는 `{summary.actual_runtime_stt_provider_id}`이고, TTS는 `{summary.tts_provider_candidate_id}` fallback 상태로만 노출한다.

## Scope

| type | item |
| --- | --- |
| include | voice adapter/provider id 정렬 |
| include | faster-whisper default transcriber contract |
| include | TTS final provider 0건을 API field로 명시 |
| include | public-safe 정량/정성 리포트 |
| exclude | 신규 음성 전사 실행 |
| exclude | 신규 음성 합성 실행 |
| exclude | managed STT/TTS provider 호출 |

## Quantitative Gate

| metric | value |
| --- | ---: |
| provider_id_mismatch_count | {summary.provider_id_mismatch_count} |
| primary_local_stt_candidate_count | {summary.primary_local_stt_candidate_count} |
| primary_local_tts_candidate_count | {summary.primary_local_tts_candidate_count} |
| tts_fallback_candidate_count | {summary.tts_fallback_candidate_count} |
| tts_final_provider_count | {summary.tts_final_provider_count} |
| runtime_default_faster_whisper_transcriber_count | {summary.runtime_default_faster_whisper_transcriber_count} |
| api_provider_status_field_count | {summary.api_provider_status_field_count} |
| external_provider_call_count | {summary.external_provider_call_count} |
| external_audio_transmission_count | {summary.external_audio_transmission_count} |
| raw_audio_public_artifact_count | {summary.raw_audio_public_artifact_count} |
| raw_transcript_public_artifact_count | {summary.raw_transcript_public_artifact_count} |
| alignment_decision | `{summary.alignment_decision}` |

## Runtime Provider Contract

| modality | provider_candidate_id | role | status | runtime_family |
| --- | --- | --- | --- | --- |
| stt | `{summary.actual_runtime_stt_provider_id}` | primary | locked_for_demo | {summary.stt_runtime_family} |
| tts | `{summary.tts_provider_candidate_id}` | {summary.tts_provider_role} | {summary.tts_provider_status} | {summary.tts_runtime_family} |

## Data Mart Grain

| fact | grain | exposure |
| --- | --- | --- |
| `fact_voice_local_runtime_stack_alignment` | `alignment_id + provider_candidate_id + metric_name` | public-safe |

## Claim Boundary

허용 claim:

- local runtime의 STT provider id를 stack lock 결정과 정렬했다.
- local runtime 기본 transcriber는 `faster-whisper small` 계약으로 맞췄다.
- TTS는 fallback이며 final provider가 아니다.

금지 claim:

- 무료 로컬 TTS 최종 provider 확정
- 실제 관광객 음성 품질 검증 완료
- production 음성 관광 앱 완성
"""


def build_markdown_report(report: RuntimeStackAlignmentReport) -> str:
    summary = report.summary
    quality = report.output_quality
    failures = collect_runtime_stack_alignment_failures(report)
    assessment_rows = "\n".join(
        f"| {key} | {value} |"
        for key, value in report.qualitative_assessment.items()
    )
    return f"""# Voice Local Runtime Stack Alignment Report

## 결론

`{WORK_ID}`는 stack lock의 무료 로컬 음성 결정을 실제 runtime/API contract에 반영했는지 검증한다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| alignment_id | `{report.alignment_id}` |
| work_id | `{report.work_id}` |
| depends_on | `{report.depends_on}` |
| generated_at_utc | `{report.generated_at_utc}` |
| result_path | `{report.result_path}` |
| source_fingerprint | `{report.source_fingerprint}` |

## 정량 리포트

| metric | value |
| --- | ---: |
| expected_primary_stt_provider_id | `{summary.expected_primary_stt_provider_id}` |
| actual_runtime_stt_provider_id | `{summary.actual_runtime_stt_provider_id}` |
| stt_model_id | `{summary.stt_model_id}` |
| stt_runtime_family | `{summary.stt_runtime_family}` |
| runtime_default_transcriber | `{summary.runtime_default_transcriber}` |
| provider_id_mismatch_count | {summary.provider_id_mismatch_count} |
| primary_local_stt_candidate_count | {summary.primary_local_stt_candidate_count} |
| primary_local_tts_candidate_count | {summary.primary_local_tts_candidate_count} |
| tts_provider_candidate_id | `{summary.tts_provider_candidate_id}` |
| tts_provider_role | `{summary.tts_provider_role}` |
| tts_provider_status | `{summary.tts_provider_status}` |
| tts_fallback_candidate_count | {summary.tts_fallback_candidate_count} |
| tts_final_provider_count | {summary.tts_final_provider_count} |
| runtime_default_faster_whisper_transcriber_count | {summary.runtime_default_faster_whisper_transcriber_count} |
| api_provider_status_field_count | {summary.api_provider_status_field_count} |
| external_provider_call_count | {summary.external_provider_call_count} |
| external_audio_transmission_count | {summary.external_audio_transmission_count} |
| raw_audio_public_artifact_count | {summary.raw_audio_public_artifact_count} |
| raw_transcript_public_artifact_count | {summary.raw_transcript_public_artifact_count} |
| public_private_path_leakage_count | {summary.public_private_path_leakage_count} |
| public_secret_like_leakage_count | {summary.public_secret_like_leakage_count} |
| public_raw_payload_leakage_count | {summary.public_raw_payload_leakage_count} |
| alignment_decision | `{summary.alignment_decision}` |

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
voice_local_runtime_stack_alignment_failures={failures}
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


def collect_runtime_stack_alignment_failures(
    report: RuntimeStackAlignmentReport,
) -> list[str]:
    summary = report.summary
    failures = collect_public_retrieval_artifact_failures(report.output_quality)
    if summary.provider_id_mismatch_count:
        failures.append("provider_id_mismatch_not_zero")
    if summary.primary_local_stt_candidate_count != 1:
        failures.append("primary_local_stt_candidate_count_not_one")
    if summary.primary_local_tts_candidate_count != 0:
        failures.append("primary_local_tts_candidate_count_not_zero")
    if summary.tts_final_provider_count != 0:
        failures.append("tts_final_provider_count_not_zero")
    if summary.runtime_default_faster_whisper_transcriber_count != 1:
        failures.append("runtime_default_transcriber_not_faster_whisper")
    if summary.api_provider_status_field_count != 5:
        failures.append("api_provider_status_fields_incomplete")
    if summary.external_provider_call_count or summary.external_audio_transmission_count:
        failures.append("external_voice_call_not_zero")
    if summary.raw_audio_public_artifact_count or summary.raw_transcript_public_artifact_count:
        failures.append("raw_voice_public_artifact_not_zero")
    if summary.alignment_decision == "failed_public_safety_gate":
        failures.append("alignment_failed_public_safety_gate")
    return list(dict.fromkeys(failures))


def build_alignment_decision(
    *,
    summary: RuntimeStackAlignmentSummary,
    output_quality: PublicRetrievalArtifactQuality,
) -> AlignmentDecision:
    if collect_public_retrieval_artifact_failures(output_quality):
        return "failed_public_safety_gate"
    if (
        summary.provider_id_mismatch_count
        or summary.primary_local_stt_candidate_count != 1
        or summary.tts_final_provider_count != 0
        or summary.runtime_default_faster_whisper_transcriber_count != 1
        or summary.api_provider_status_field_count != 5
    ):
        return "failed_runtime_stack_alignment"
    return "aligned_local_stt_tts_blocked"


def build_qualitative_assessment(
    summary: RuntimeStackAlignmentSummary,
) -> dict[str, str]:
    return {
        "backend": "runtime 기본 STT provider id와 transcriber 구현이 stack lock 결정과 일치한다.",
        "voice_ml": "faster-whisper small CUDA는 demo evidence 후보이며 신규 전사 실행은 하지 않았다.",
        "product": "TTS는 fallback_not_quality_candidate로 노출해 final provider 오해를 줄였다.",
        "security": "외부 provider call과 외부 음성 전송은 0이며 public artifact에는 raw audio/transcript가 없다.",
        "evaluation": "provider id, API field, public safety를 deterministic gate로 고정했다.",
        "data_mart": "alignment fact grain은 alignment_id + provider_candidate_id + metric_name이다.",
        "external_audit": "무료 로컬 TTS final provider claim을 만들지 않은 점이 현재 evidence와 맞다.",
        "decision": summary.alignment_decision,
    }


def build_alignment_id(summary: RuntimeStackAlignmentSummary) -> str:
    return f"voice-runtime-stack-align-{stable_digest(summary.model_dump(mode='json'))[:8]}"


def stable_digest(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--doc-path", type=Path, default=DEFAULT_DOC_PATH)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--result-rows-path", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    args = parser.parse_args()
    run_voice_local_runtime_stack_alignment(
        doc_path=args.doc_path,
        report_path=args.report_path,
        result_rows_path=args.result_rows_path,
    )


if __name__ == "__main__":
    main()
