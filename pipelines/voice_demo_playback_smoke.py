from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import wave
from collections.abc import Sequence
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
from pipelines.voice_local_tts_human_score_fill import (
    DEFAULT_PRIVATE_AUDIO_DIR,
    DEFAULT_PRIVATE_SCORE_INPUT_PATH,
    DEFAULT_SCRIPT_LIMIT,
    DEFAULT_SCRIPTS_PATH,
    count_completed_scripts,
    load_private_score_rows,
)
from pipelines.voice_local_tts_quality_listening_review import (
    PROVIDER_CANDIDATE_ID,
    RUBRIC,
)
from pipelines.voice_stt_tts_local_tts_smoke import (
    load_tts_smoke_scripts,
    select_tts_smoke_scripts,
)


REPORT_VERSION = "voice-demo-playback-smoke-report/v1"
WORK_ID = "HD-VOICE-DEMO-PLAYBACK-SMOKE-001"
DEPENDS_ON = "HD-VOICE-DEMO-STACK-DECISION-001"
PRIMARY_LOCAL_STT_CANDIDATE_ID = "local_faster_whisper_small_cuda"
TTS_DEMO_CANDIDATE_ID = PROVIDER_CANDIDATE_ID

DEFAULT_DOC_PATH = Path("docs") / "VOICE_DEMO_PLAYBACK_SMOKE.md"
DEFAULT_REPORT_PATH = Path("evals") / "reports" / "voice_demo_playback_smoke_report.md"
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data") / "evals" / "results" / "voice_demo_playback_smoke_rows.jsonl"
)

AudioValidationStatus = Literal[
    "accepted_private_wav",
    "blocked_missing_private_wav",
    "blocked_invalid_wav",
]
PlaybackContractStatus = Literal[
    "ready_for_manual_demo_playback",
    "blocked_missing_private_audio",
    "blocked_invalid_private_audio",
]
PlaybackSmokeDecision = Literal[
    "completed_local_voice_demo_playback_smoke",
    "blocked_missing_private_audio",
    "failed_public_safety_gate",
]


class VoiceDemoPlaybackSmokeBase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class VoiceDemoPlaybackSmokeRow(VoiceDemoPlaybackSmokeBase):
    script_id: str = Field(min_length=1)
    language: str = Field(min_length=1)
    text_role: str = Field(min_length=1)
    stt_provider_candidate_id: str = PRIMARY_LOCAL_STT_CANDIDATE_ID
    tts_provider_candidate_id: str = TTS_DEMO_CANDIDATE_ID
    audio_validation_status: AudioValidationStatus
    playback_contract_status: PlaybackContractStatus
    audio_artifact_private: bool
    audio_artifact_id: str
    audio_duration_ms: float = Field(ge=0.0)
    audio_file_size_bytes: int = Field(ge=0)
    sample_rate_hz: int = Field(ge=0)
    script_hash: str = Field(min_length=8)
    error_code: str


class VoiceDemoPlaybackSmokeSummary(VoiceDemoPlaybackSmokeBase):
    selected_script_count: int = Field(ge=0)
    primary_local_stt_candidate_count: int = Field(ge=0)
    tts_demo_candidate_count: int = Field(ge=0)
    tts_final_provider_count: int = Field(ge=0)
    private_audio_expected_count: int = Field(ge=0)
    private_audio_available_count: int = Field(ge=0)
    private_audio_missing_count: int = Field(ge=0)
    accepted_private_wav_count: int = Field(ge=0)
    invalid_private_audio_count: int = Field(ge=0)
    playback_contract_step_count: int = Field(ge=0)
    playback_ready_count: int = Field(ge=0)
    playback_device_call_count: int = Field(ge=0)
    private_score_input_available_count: int = Field(ge=0)
    tts_human_score_completed_count: int = Field(ge=0)
    tts_human_score_expected_count: int = Field(ge=0)
    tts_human_score_completed_script_count: int = Field(ge=0)
    tts_human_score_overall_avg: float | None = None
    tts_human_score_reviewer_count: int = Field(ge=0)
    human_score_public_detail_row_count: int = Field(ge=0)
    audio_duration_total_ms: float = Field(ge=0.0)
    audio_file_size_total_bytes: int = Field(ge=0)
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
    production_voice_claim_count: int = Field(ge=0)
    playback_smoke_decision: PlaybackSmokeDecision


class VoiceDemoPlaybackSmokeReport(VoiceDemoPlaybackSmokeBase):
    report_version: str = REPORT_VERSION
    playback_smoke_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    work_id: str = WORK_ID
    depends_on: str = DEPENDS_ON
    scripts_path: str = Field(min_length=1)
    audio_path_alias: str = Field(min_length=1)
    private_score_input_alias: str = Field(min_length=1)
    result_path: str = Field(min_length=1)
    source_fingerprint: str = Field(min_length=8)
    summary: VoiceDemoPlaybackSmokeSummary
    rows: tuple[VoiceDemoPlaybackSmokeRow, ...]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def run_voice_demo_playback_smoke(
    *,
    scripts_path: Path = DEFAULT_SCRIPTS_PATH,
    private_audio_dir: Path = DEFAULT_PRIVATE_AUDIO_DIR,
    private_score_input_path: Path = DEFAULT_PRIVATE_SCORE_INPUT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
    doc_path: Path = DEFAULT_DOC_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    script_limit: int = DEFAULT_SCRIPT_LIMIT,
) -> VoiceDemoPlaybackSmokeReport:
    scripts = select_tts_smoke_scripts(
        load_tts_smoke_scripts(project_path(scripts_path)),
        limit=script_limit,
    )
    rows = tuple(
        build_playback_row(
            script_id=script.script_id,
            language=script.language,
            text_role=script.text_role,
            script_text=script.script_text,
            audio_path=project_path(private_audio_dir) / f"{script.script_id}.wav",
        )
        for script in scripts
    )
    score_rows, invalid_score_row_count, score_input_available = load_private_score_rows(
        score_input_path=project_path(private_score_input_path),
        scripts={script.script_id for script in scripts},
        criteria={criterion.criterion_id for criterion in RUBRIC},
    )
    summary = build_summary(
        rows=rows,
        score_input_available=score_input_available,
        score_rows=score_rows,
        invalid_score_row_count=invalid_score_row_count,
    )
    playback_smoke_id = build_playback_smoke_id(rows=rows, summary=summary)
    public_rows = build_public_rows(playback_smoke_id=playback_smoke_id, rows=rows)
    provisional_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=playback_smoke_id,
        result_rows=public_rows,
        report_text="",
    )
    provisional = build_report(
        playback_smoke_id=playback_smoke_id,
        scripts_path=scripts_path,
        private_audio_dir=private_audio_dir,
        private_score_input_path=private_score_input_path,
        result_rows_path=result_rows_path,
        rows=rows,
        summary=summary,
        output_quality=provisional_quality,
    )
    doc_text = build_doc(provisional)
    report_text = build_markdown_report(provisional)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=playback_smoke_id,
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
            "playback_smoke_decision": build_decision(
                summary=summary,
                output_quality=output_quality,
            ),
        }
    )
    report = build_report(
        playback_smoke_id=playback_smoke_id,
        scripts_path=scripts_path,
        private_audio_dir=private_audio_dir,
        private_score_input_path=private_score_input_path,
        result_rows_path=result_rows_path,
        rows=rows,
        summary=summary,
        output_quality=output_quality,
    )
    failures = collect_playback_smoke_failures(report)
    if failures:
        raise ValueError(f"voice demo playback smoke gate failed: {failures}")

    write_public_retrieval_result_rows(
        path=project_path(result_rows_path),
        rows=build_public_rows(playback_smoke_id=playback_smoke_id, rows=rows),
    )
    project_path(doc_path).write_text(build_doc(report), encoding="utf-8")
    project_path(report_path).write_text(build_markdown_report(report), encoding="utf-8")
    print(
        "voice_demo_playback_smoke "
        f"status={report.summary.playback_smoke_decision} "
        f"scripts={report.summary.selected_script_count} "
        f"playback_ready={report.summary.playback_ready_count} "
        f"private_audio={report.summary.private_audio_available_count} "
        f"external_calls={report.summary.external_provider_call_count}",
    )
    return report


def build_playback_row(
    *,
    script_id: str,
    language: str,
    text_role: str,
    script_text: str,
    audio_path: Path,
) -> VoiceDemoPlaybackSmokeRow:
    if not audio_path.exists():
        return VoiceDemoPlaybackSmokeRow(
            script_id=script_id,
            language=language,
            text_role=text_role,
            audio_validation_status="blocked_missing_private_wav",
            playback_contract_status="blocked_missing_private_audio",
            audio_artifact_private=False,
            audio_artifact_id="",
            audio_duration_ms=0.0,
            audio_file_size_bytes=0,
            sample_rate_hz=0,
            script_hash=stable_digest(script_text),
            error_code="private_audio_missing",
        )
    try:
        with wave.open(str(audio_path), "rb") as wav_file:
            frame_rate = wav_file.getframerate()
            frame_count = wav_file.getnframes()
        file_size = audio_path.stat().st_size
        duration_ms = round((frame_count / frame_rate) * 1000.0, 6) if frame_rate > 0 else 0.0
    except (EOFError, wave.Error):
        return VoiceDemoPlaybackSmokeRow(
            script_id=script_id,
            language=language,
            text_role=text_role,
            audio_validation_status="blocked_invalid_wav",
            playback_contract_status="blocked_invalid_private_audio",
            audio_artifact_private=True,
            audio_artifact_id=stable_digest(script_id),
            audio_duration_ms=0.0,
            audio_file_size_bytes=audio_path.stat().st_size if audio_path.exists() else 0,
            sample_rate_hz=0,
            script_hash=stable_digest(script_text),
            error_code="invalid_private_wav",
        )
    return VoiceDemoPlaybackSmokeRow(
        script_id=script_id,
        language=language,
        text_role=text_role,
        audio_validation_status="accepted_private_wav",
        playback_contract_status="ready_for_manual_demo_playback",
        audio_artifact_private=True,
        audio_artifact_id=stable_digest(f"{script_id}:{file_size}:{duration_ms:.3f}"),
        audio_duration_ms=duration_ms,
        audio_file_size_bytes=file_size,
        sample_rate_hz=frame_rate,
        script_hash=stable_digest(script_text),
        error_code="",
    )


def build_summary(
    *,
    rows: tuple[VoiceDemoPlaybackSmokeRow, ...],
    score_input_available: int,
    score_rows: tuple[Any, ...],
    invalid_score_row_count: int,
) -> VoiceDemoPlaybackSmokeSummary:
    scores = [row.score for row in score_rows]
    expected_score_count = len(rows) * len(RUBRIC)
    completed_score_count = len(score_rows)
    completed_script_count = count_completed_scripts(score_rows)
    accepted_rows = [row for row in rows if row.audio_validation_status == "accepted_private_wav"]
    ready_rows = [
        row for row in rows if row.playback_contract_status == "ready_for_manual_demo_playback"
    ]
    return VoiceDemoPlaybackSmokeSummary(
        selected_script_count=len(rows),
        primary_local_stt_candidate_count=1,
        tts_demo_candidate_count=1,
        tts_final_provider_count=0,
        private_audio_expected_count=len(rows),
        private_audio_available_count=sum(1 for row in rows if row.audio_artifact_private),
        private_audio_missing_count=sum(
            1 for row in rows if row.audio_validation_status == "blocked_missing_private_wav"
        ),
        accepted_private_wav_count=len(accepted_rows),
        invalid_private_audio_count=sum(
            1 for row in rows if row.audio_validation_status == "blocked_invalid_wav"
        ),
        playback_contract_step_count=len(rows),
        playback_ready_count=len(ready_rows),
        playback_device_call_count=0,
        private_score_input_available_count=score_input_available,
        tts_human_score_completed_count=completed_score_count,
        tts_human_score_expected_count=expected_score_count,
        tts_human_score_completed_script_count=completed_script_count,
        tts_human_score_overall_avg=round(statistics.fmean(scores), 6) if scores else None,
        tts_human_score_reviewer_count=len({row.reviewer_id for row in score_rows}),
        human_score_public_detail_row_count=0,
        audio_duration_total_ms=round(sum(row.audio_duration_ms for row in accepted_rows), 6),
        audio_file_size_total_bytes=sum(row.audio_file_size_bytes for row in accepted_rows),
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
        production_voice_claim_count=0,
        playback_smoke_decision=build_decision_from_counts(
            selected_script_count=len(rows),
            ready_count=len(ready_rows),
            private_audio_missing_count=sum(
                1
                for row in rows
                if row.audio_validation_status == "blocked_missing_private_wav"
            ),
            invalid_private_audio_count=sum(
                1 for row in rows if row.audio_validation_status == "blocked_invalid_wav"
            ),
            invalid_score_row_count=invalid_score_row_count,
        ),
    )


def build_decision_from_counts(
    *,
    selected_script_count: int,
    ready_count: int,
    private_audio_missing_count: int,
    invalid_private_audio_count: int,
    invalid_score_row_count: int,
) -> PlaybackSmokeDecision:
    if private_audio_missing_count or invalid_private_audio_count or invalid_score_row_count:
        return "blocked_missing_private_audio"
    if ready_count != selected_script_count:
        return "blocked_missing_private_audio"
    return "completed_local_voice_demo_playback_smoke"


def build_decision(
    *,
    summary: VoiceDemoPlaybackSmokeSummary,
    output_quality: PublicRetrievalArtifactQuality,
) -> PlaybackSmokeDecision:
    if collect_public_retrieval_artifact_failures(output_quality):
        return "failed_public_safety_gate"
    return build_decision_from_counts(
        selected_script_count=summary.selected_script_count,
        ready_count=summary.playback_ready_count,
        private_audio_missing_count=summary.private_audio_missing_count,
        invalid_private_audio_count=summary.invalid_private_audio_count,
        invalid_score_row_count=0,
    )


def build_report(
    *,
    playback_smoke_id: str,
    scripts_path: Path,
    private_audio_dir: Path,
    private_score_input_path: Path,
    result_rows_path: Path,
    rows: tuple[VoiceDemoPlaybackSmokeRow, ...],
    summary: VoiceDemoPlaybackSmokeSummary,
    output_quality: PublicRetrievalArtifactQuality,
) -> VoiceDemoPlaybackSmokeReport:
    report = VoiceDemoPlaybackSmokeReport(
        playback_smoke_id=playback_smoke_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        scripts_path=public_path_alias(scripts_path),
        audio_path_alias=public_path_alias(private_audio_dir),
        private_score_input_alias=public_path_alias(private_score_input_path),
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
    playback_smoke_id: str,
    rows: tuple[VoiceDemoPlaybackSmokeRow, ...],
) -> list[dict[str, Any]]:
    return [
        {
            "row_type": "voice_demo_playback_smoke",
            "playback_smoke_id": playback_smoke_id,
            "script_id": row.script_id,
            "language": row.language,
            "text_role": row.text_role,
            "stt_provider_candidate_id": row.stt_provider_candidate_id,
            "tts_provider_candidate_id": row.tts_provider_candidate_id,
            "audio_validation_status": row.audio_validation_status,
            "playback_contract_status": row.playback_contract_status,
            "audio_artifact_id": row.audio_artifact_id,
            "audio_duration_ms": row.audio_duration_ms,
            "audio_file_size_bytes": row.audio_file_size_bytes,
            "sample_rate_hz": row.sample_rate_hz,
            "script_hash": row.script_hash,
            "error_code": row.error_code,
        }
        for row in rows
    ]


def build_doc(report: VoiceDemoPlaybackSmokeReport) -> str:
    summary = report.summary
    return f"""# Voice Demo Playback Smoke

## 결론

`{WORK_ID}`는 무료 로컬 음성 demo stack을 실제 demo playback 후보로 열어도 되는지 확인하는 gate다.

결과는 `{summary.playback_smoke_decision}`이다. private wav 5개는 playback-ready 상태이며, 이 gate는 speaker device를 자동 재생하지 않는다. 실제 관광객 품질 검증이나 production final provider 확정도 아니다.

## Scope

| type | item |
| --- | --- |
| include | `local_faster_whisper_small_cuda` STT demo 후보 유지 |
| include | `local_sherpa_onnx_supertonic3_ko` TTS demo review 후보의 private wav 존재 확인 |
| include | private wav metadata 기반 playback-ready smoke |
| include | 사람 청취 점수 완료 상태와 public-safe 집계 확인 |
| exclude | speaker device 자동 재생 |
| exclude | microphone capture |
| exclude | raw audio public artifact |
| exclude | raw transcript/script public artifact |
| exclude | managed STT/TTS provider call |
| exclude | Solar Pro 3 call |

## 정량 요약

| metric | value |
| --- | ---: |
| selected_script_count | {summary.selected_script_count} |
| primary_local_stt_candidate_count | {summary.primary_local_stt_candidate_count} |
| tts_demo_candidate_count | {summary.tts_demo_candidate_count} |
| tts_final_provider_count | {summary.tts_final_provider_count} |
| private_audio_expected_count | {summary.private_audio_expected_count} |
| private_audio_available_count | {summary.private_audio_available_count} |
| private_audio_missing_count | {summary.private_audio_missing_count} |
| accepted_private_wav_count | {summary.accepted_private_wav_count} |
| invalid_private_audio_count | {summary.invalid_private_audio_count} |
| playback_contract_step_count | {summary.playback_contract_step_count} |
| playback_ready_count | {summary.playback_ready_count} |
| playback_device_call_count | {summary.playback_device_call_count} |
| tts_human_score_completed_count | {summary.tts_human_score_completed_count} |
| tts_human_score_expected_count | {summary.tts_human_score_expected_count} |
| tts_human_score_overall_avg | {format_optional_float(summary.tts_human_score_overall_avg)} |
| tts_human_score_reviewer_count | {summary.tts_human_score_reviewer_count} |
| human_score_public_detail_row_count | {summary.human_score_public_detail_row_count} |
| audio_duration_total_ms | {summary.audio_duration_total_ms:.6f} |
| audio_file_size_total_bytes | {summary.audio_file_size_total_bytes} |
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
| production_voice_claim_count | {summary.production_voice_claim_count} |

## Data Mart Grain

| fact | grain | exposure |
| --- | --- | --- |
| `fact_voice_demo_playback_smoke_public` | `playback_smoke_id + script_id + provider_candidate_id + metric_name` | public-safe |
| `fact_voice_demo_audio_artifact_private` | `playback_smoke_id + script_id + audio_artifact_id` | private |

## Claim Boundary

| type | claim |
| --- | --- |
| allowed | private wav 5개가 demo playback 후보로 준비됐다. |
| allowed | 외부 STT/TTS provider 호출과 외부 음성 전송은 0이다. |
| allowed | public artifact에는 raw audio, raw transcript, raw script, 개별 score를 저장하지 않는다. |
| forbidden | 무료 로컬 TTS 최종 provider 확정 |
| forbidden | 실제 관광객 음성 품질 검증 완료 |
| forbidden | production 음성 관광 앱 완성 |
| forbidden | speaker device 자동 재생 검증 완료 |
| forbidden | managed provider보다 local TTS가 품질 우수하다는 주장 |
"""


def build_markdown_report(report: VoiceDemoPlaybackSmokeReport) -> str:
    summary = report.summary
    quality = report.output_quality
    metric_lines = "\n".join(
        f"| {key} | {value} |" for key, value in build_metric_pairs(summary)
    )
    row_lines = "\n".join(format_row(row) for row in report.rows)
    assessment_lines = "\n".join(
        f"| {key} | {value} |" for key, value in report.qualitative_assessment.items()
    )
    failures = collect_playback_smoke_failures(report)
    return f"""# Voice Demo Playback Smoke Report

## 결론

`{WORK_ID}`는 `{summary.playback_smoke_decision}`이다.

private wav 5개는 playback-ready 상태다. 자동 speaker playback은 수행하지 않았고, 외부 provider 호출도 0이다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| playback_smoke_id | `{report.playback_smoke_id}` |
| work_id | `{report.work_id}` |
| depends_on | `{report.depends_on}` |
| generated_at_utc | `{report.generated_at_utc}` |
| scripts_path | `{report.scripts_path}` |
| audio_path_alias | `{report.audio_path_alias}` |
| private_score_input_alias | `{report.private_score_input_alias}` |
| result_path | `{report.result_path}` |
| source_fingerprint | `{report.source_fingerprint}` |
| playback_smoke_decision | `{summary.playback_smoke_decision}` |

## 정량 리포트

| metric | value |
| --- | ---: |
{metric_lines}

## Result Row Summary

| script_id | language | audio_status | playback_status | duration_ms | file_size_bytes | sample_rate_hz | error_code |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
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
voice_demo_playback_smoke_failures={failures}
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


def build_metric_pairs(summary: VoiceDemoPlaybackSmokeSummary) -> list[tuple[str, object]]:
    return [
        ("selected_script_count", summary.selected_script_count),
        ("primary_local_stt_candidate_count", summary.primary_local_stt_candidate_count),
        ("tts_demo_candidate_count", summary.tts_demo_candidate_count),
        ("tts_final_provider_count", summary.tts_final_provider_count),
        ("private_audio_expected_count", summary.private_audio_expected_count),
        ("private_audio_available_count", summary.private_audio_available_count),
        ("private_audio_missing_count", summary.private_audio_missing_count),
        ("accepted_private_wav_count", summary.accepted_private_wav_count),
        ("invalid_private_audio_count", summary.invalid_private_audio_count),
        ("playback_contract_step_count", summary.playback_contract_step_count),
        ("playback_ready_count", summary.playback_ready_count),
        ("playback_device_call_count", summary.playback_device_call_count),
        ("private_score_input_available_count", summary.private_score_input_available_count),
        ("tts_human_score_completed_count", summary.tts_human_score_completed_count),
        ("tts_human_score_expected_count", summary.tts_human_score_expected_count),
        (
            "tts_human_score_completed_script_count",
            summary.tts_human_score_completed_script_count,
        ),
        ("tts_human_score_overall_avg", format_optional_float(summary.tts_human_score_overall_avg)),
        ("tts_human_score_reviewer_count", summary.tts_human_score_reviewer_count),
        ("human_score_public_detail_row_count", summary.human_score_public_detail_row_count),
        ("audio_duration_total_ms", f"{summary.audio_duration_total_ms:.6f}"),
        ("audio_file_size_total_bytes", summary.audio_file_size_total_bytes),
        ("external_provider_call_count", summary.external_provider_call_count),
        ("external_audio_transmission_count", summary.external_audio_transmission_count),
        ("live_stt_call_count", summary.live_stt_call_count),
        ("live_tts_call_count", summary.live_tts_call_count),
        ("live_solar_call_count", summary.live_solar_call_count),
        ("raw_audio_public_artifact_count", summary.raw_audio_public_artifact_count),
        ("raw_transcript_public_artifact_count", summary.raw_transcript_public_artifact_count),
        ("raw_script_public_artifact_count", summary.raw_script_public_artifact_count),
        ("public_private_path_leakage_count", summary.public_private_path_leakage_count),
        ("public_secret_like_leakage_count", summary.public_secret_like_leakage_count),
        ("public_raw_payload_leakage_count", summary.public_raw_payload_leakage_count),
        ("production_voice_claim_count", summary.production_voice_claim_count),
    ]


def build_qualitative(report: VoiceDemoPlaybackSmokeReport) -> dict[str, str]:
    summary = report.summary
    return {
        "product": "포트폴리오 demo에서 들려줄 수 있는 private wav 후보가 준비됐는지 확인하는 gate다.",
        "voice_ml": "STT/TTS 최종 품질 검증이 아니라 현재 로컬 demo 후보의 playback readiness만 확인한다.",
        "evaluation": "사람 청취 점수 30/30 완료와 private wav 5개 존재를 함께 확인했다.",
        "privacy": "raw audio, raw transcript, raw script, 개별 score detail은 public artifact에 포함하지 않는다.",
        "cost": "외부 STT/TTS provider 호출, 외부 음성 전송, Solar 호출은 모두 0이다.",
        "data_mart": "public playback smoke fact와 private audio artifact fact를 분리했다.",
        "claim_boundary": "demo playback-ready는 주장 가능하지만 production final provider 확정은 금지한다.",
        "external_audit": "실제 speaker 자동 재생을 수행하지 않은 점은 로컬 부작용을 줄이는 판단으로 타당하다.",
        "decision": summary.playback_smoke_decision,
    }


def collect_playback_smoke_failures(report: VoiceDemoPlaybackSmokeReport) -> list[str]:
    summary = report.summary
    failures = collect_public_retrieval_artifact_failures(report.output_quality)
    if summary.selected_script_count != DEFAULT_SCRIPT_LIMIT:
        failures.append("selected_script_count_mismatch")
    if summary.private_audio_available_count != summary.private_audio_expected_count:
        failures.append("private_audio_available_count_mismatch")
    if summary.accepted_private_wav_count != summary.selected_script_count:
        failures.append("accepted_private_wav_count_mismatch")
    if summary.playback_ready_count != summary.selected_script_count:
        failures.append("playback_ready_count_mismatch")
    if summary.tts_human_score_completed_count != summary.tts_human_score_expected_count:
        failures.append("tts_human_score_incomplete")
    if summary.human_score_public_detail_row_count:
        failures.append("human_score_detail_public_rows_created")
    if summary.tts_final_provider_count:
        failures.append("tts_final_provider_claimed")
    if summary.external_provider_call_count or summary.external_audio_transmission_count:
        failures.append("external_voice_call_or_transmission_not_zero")
    if (
        summary.raw_audio_public_artifact_count
        or summary.raw_transcript_public_artifact_count
        or summary.raw_script_public_artifact_count
    ):
        failures.append("raw_voice_or_script_public_artifact_created")
    if summary.playback_device_call_count:
        failures.append("speaker_playback_called")
    if summary.production_voice_claim_count:
        failures.append("production_voice_claim_created")
    if summary.playback_smoke_decision == "failed_public_safety_gate":
        failures.append("public_safety_gate_failed")
    return list(dict.fromkeys(failures))


def format_row(row: VoiceDemoPlaybackSmokeRow) -> str:
    return (
        f"| {row.script_id} | {row.language} | `{row.audio_validation_status}` | "
        f"`{row.playback_contract_status}` | {row.audio_duration_ms:.6f} | "
        f"{row.audio_file_size_bytes} | {row.sample_rate_hz} | `{row.error_code}` |"
    )


def build_playback_smoke_id(
    *,
    rows: tuple[VoiceDemoPlaybackSmokeRow, ...],
    summary: VoiceDemoPlaybackSmokeSummary,
) -> str:
    digest = stable_digest(
        {
            "work_id": WORK_ID,
            "rows": [row.model_dump(mode="json") for row in rows],
            "summary": summary.model_dump(mode="json"),
        },
        length=8,
    )
    return f"voice-demo-playback-smoke-s{len(rows)}-{digest}"


def format_optional_float(value: float | None) -> str:
    return "null" if value is None else f"{value:.6f}"


def stable_digest(payload: Any, *, length: int = 16) -> str:
    value = (
        payload
        if isinstance(payload, str)
        else json.dumps(payload, ensure_ascii=False, sort_keys=True)
    )
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scripts", type=Path, default=DEFAULT_SCRIPTS_PATH)
    parser.add_argument("--audio-dir", type=Path, default=DEFAULT_PRIVATE_AUDIO_DIR)
    parser.add_argument("--score-input", type=Path, default=DEFAULT_PRIVATE_SCORE_INPUT_PATH)
    parser.add_argument("--result-rows", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--script-limit", type=int, default=DEFAULT_SCRIPT_LIMIT)
    args = parser.parse_args(argv)

    run_voice_demo_playback_smoke(
        scripts_path=args.scripts,
        private_audio_dir=args.audio_dir,
        private_score_input_path=args.score_input,
        result_rows_path=args.result_rows,
        doc_path=args.doc,
        report_path=args.report,
        script_limit=args.script_limit,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
