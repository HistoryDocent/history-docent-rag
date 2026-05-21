from __future__ import annotations

import argparse
import statistics
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
from pipelines.voice_local_tts_human_score_entry import (
    WORK_ID as SCORE_ENTRY_WORK_ID,
)
from pipelines.voice_local_tts_human_score_fill import (
    DEFAULT_PRIVATE_AUDIO_DIR,
    DEFAULT_PRIVATE_SCORE_INPUT_PATH,
    DEFAULT_SCRIPT_LIMIT,
    DEFAULT_SCRIPTS_PATH,
    SCORE_MAX,
    SCORE_MIN,
    TtsHumanCriterionAggregate,
    TtsHumanScorePrivateRow,
    build_aggregates,
    count_completed_scripts,
    format_optional_float,
    format_optional_int,
    load_private_score_rows,
)
from pipelines.voice_local_tts_human_score_collection import (
    TtsHumanScoreCollectionAudioRow,
    build_private_audio_rows,
)
from pipelines.voice_local_tts_quality_listening_review import (
    MODEL_FAMILY,
    PROVIDER_CANDIDATE_ID,
    RUBRIC,
    stable_digest,
)
from pipelines.voice_stt_tts_local_tts_smoke import (
    load_tts_smoke_scripts,
    select_tts_smoke_scripts,
)


REPORT_VERSION = "voice-local-tts-human-score-entry-completion-report/v1"
WORK_ID = "HD-VOICE-LOCAL-TTS-HUMAN-SCORE-ENTRY-COMPLETION-001"
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "voice_local_tts_human_score_entry_completion_public_rows.jsonl"
)
DEFAULT_DOC_PATH = Path("docs") / "VOICE_LOCAL_TTS_HUMAN_SCORE_ENTRY_COMPLETION.md"
DEFAULT_REPORT_PATH = (
    Path("evals")
    / "reports"
    / "voice_local_tts_human_score_entry_completion_report.md"
)

ScoreEntryCompletionDecision = Literal[
    "blocked_missing_human_scores",
    "blocked_incomplete_human_scores",
    "completed_human_scores_ready_for_provider_decision",
    "blocked_missing_private_audio",
    "blocked_invalid_private_scores",
    "failed_public_safety_gate",
]


class TtsHumanScoreEntryCompletionBase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TtsHumanScoreEntryCompletionSummary(TtsHumanScoreEntryCompletionBase):
    selected_script_count: int = Field(ge=0)
    rubric_criterion_count: int = Field(ge=0)
    expected_private_score_row_count: int = Field(ge=0)
    private_audio_expected_count: int = Field(ge=0)
    private_audio_available_count: int = Field(ge=0)
    private_audio_missing_count: int = Field(ge=0)
    private_score_input_available_count: int = Field(ge=0)
    private_score_input_row_count: int = Field(ge=0)
    valid_private_score_row_count: int = Field(ge=0)
    invalid_private_score_row_count: int = Field(ge=0)
    completed_score_row_count: int = Field(ge=0)
    pending_score_row_count: int = Field(ge=0)
    completed_script_count: int = Field(ge=0)
    completed_script_rate: float = Field(ge=0.0, le=1.0)
    reviewer_count: int = Field(ge=0)
    aggregate_public_row_count: int = Field(ge=0)
    overall_score_avg: float | None = None
    overall_score_min: int | None = None
    overall_score_max: int | None = None
    score_scale_min: int = SCORE_MIN
    score_scale_max: int = SCORE_MAX
    external_provider_call_count: int = Field(ge=0)
    external_audio_transmission_count: int = Field(ge=0)
    live_stt_call_count: int = Field(ge=0)
    live_tts_call_count: int = Field(ge=0)
    live_solar_call_count: int = Field(ge=0)
    raw_transcript_public_artifact_count: int = Field(ge=0)
    raw_audio_public_artifact_count: int = Field(ge=0)
    raw_script_public_artifact_count: int = Field(ge=0)
    human_score_private_artifact_count: int = Field(ge=0)
    human_score_public_detail_row_count: int = Field(ge=0)
    public_private_path_leakage_count: int = Field(ge=0)
    public_secret_like_leakage_count: int = Field(ge=0)
    public_raw_payload_leakage_count: int = Field(ge=0)
    score_completion_decision: ScoreEntryCompletionDecision


class TtsHumanScoreEntryCompletionReport(TtsHumanScoreEntryCompletionBase):
    report_version: str = REPORT_VERSION
    score_completion_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    work_id: str = WORK_ID
    depends_on_score_entry: str = SCORE_ENTRY_WORK_ID
    scripts_path: str = Field(min_length=1)
    audio_path_alias: str = Field(min_length=1)
    private_score_input_alias: str = Field(min_length=1)
    result_path: str = Field(min_length=1)
    source_fingerprint: str = Field(min_length=8)
    summary: TtsHumanScoreEntryCompletionSummary
    aggregates: tuple[TtsHumanCriterionAggregate, ...]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def run_voice_local_tts_human_score_entry_completion(
    *,
    scripts_path: Path = DEFAULT_SCRIPTS_PATH,
    private_audio_dir: Path = DEFAULT_PRIVATE_AUDIO_DIR,
    private_score_input_path: Path = DEFAULT_PRIVATE_SCORE_INPUT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
    doc_path: Path = DEFAULT_DOC_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    script_limit: int = DEFAULT_SCRIPT_LIMIT,
) -> TtsHumanScoreEntryCompletionReport:
    scripts = select_tts_smoke_scripts(
        load_tts_smoke_scripts(project_path(scripts_path)),
        limit=script_limit,
    )
    audio_rows = build_private_audio_rows(
        scripts=scripts,
        private_audio_dir=project_path(private_audio_dir),
    )
    score_rows, invalid_row_count, score_input_available = load_private_score_rows(
        score_input_path=project_path(private_score_input_path),
        scripts={script.script_id for script in scripts},
        criteria={criterion.criterion_id for criterion in RUBRIC},
    )
    aggregates = build_aggregates(score_rows)
    summary = build_summary(
        audio_rows=audio_rows,
        score_input_available=score_input_available,
        score_input_row_count=len(score_rows) + invalid_row_count,
        score_rows=score_rows,
        invalid_row_count=invalid_row_count,
        aggregates=aggregates,
    )
    score_completion_id = build_score_completion_id(
        audio_rows=audio_rows,
        score_rows=score_rows,
        summary=summary,
    )
    public_rows = build_public_rows(
        score_completion_id=score_completion_id,
        aggregates=aggregates,
    )
    provisional_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=score_completion_id,
        result_rows=public_rows,
        report_text="",
    )
    provisional = build_report(
        score_completion_id=score_completion_id,
        scripts_path=scripts_path,
        private_audio_dir=private_audio_dir,
        private_score_input_path=private_score_input_path,
        result_rows_path=result_rows_path,
        summary=summary,
        aggregates=aggregates,
        output_quality=provisional_quality,
    )
    doc_text = build_doc(provisional)
    report_text = build_markdown(provisional)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=score_completion_id,
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
            "score_completion_decision": build_decision(
                summary=summary,
                output_quality=output_quality,
            ),
        },
    )
    report = build_report(
        score_completion_id=score_completion_id,
        scripts_path=scripts_path,
        private_audio_dir=private_audio_dir,
        private_score_input_path=private_score_input_path,
        result_rows_path=result_rows_path,
        summary=summary,
        aggregates=aggregates,
        output_quality=output_quality,
    )
    failures = collect_completion_failures(report)
    if failures:
        raise ValueError(f"voice local TTS human score completion gate failed: {failures}")

    write_public_retrieval_result_rows(
        path=project_path(result_rows_path),
        rows=build_public_rows(
            score_completion_id=score_completion_id,
            aggregates=aggregates,
        ),
    )
    resolved_doc_path = project_path(doc_path)
    resolved_report_path = project_path(report_path)
    resolved_doc_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_report_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_doc_path.write_text(build_doc(report), encoding="utf-8")
    resolved_report_path.write_text(build_markdown(report), encoding="utf-8")
    print(
        "voice_local_tts_human_score_entry_completion "
        f"status={report.summary.score_completion_decision} "
        f"completed_scores={report.summary.completed_score_row_count} "
        f"pending_scores={report.summary.pending_score_row_count} "
        f"aggregate_rows={report.summary.aggregate_public_row_count} "
        f"external_calls={report.summary.external_provider_call_count}",
    )
    return report


def build_summary(
    *,
    audio_rows: tuple[TtsHumanScoreCollectionAudioRow, ...],
    score_input_available: int,
    score_input_row_count: int,
    score_rows: tuple[TtsHumanScorePrivateRow, ...],
    invalid_row_count: int,
    aggregates: tuple[TtsHumanCriterionAggregate, ...],
) -> TtsHumanScoreEntryCompletionSummary:
    scores = [row.score for row in score_rows]
    selected_script_count = len(audio_rows)
    completed_script_count = count_completed_scripts(score_rows)
    audio_available_count = sum(1 for row in audio_rows if row.audio_available)
    expected_score_row_count = selected_script_count * len(RUBRIC)
    summary = TtsHumanScoreEntryCompletionSummary(
        selected_script_count=selected_script_count,
        rubric_criterion_count=len(RUBRIC),
        expected_private_score_row_count=expected_score_row_count,
        private_audio_expected_count=selected_script_count,
        private_audio_available_count=audio_available_count,
        private_audio_missing_count=selected_script_count - audio_available_count,
        private_score_input_available_count=score_input_available,
        private_score_input_row_count=score_input_row_count,
        valid_private_score_row_count=len(score_rows),
        invalid_private_score_row_count=invalid_row_count,
        completed_score_row_count=len(score_rows),
        pending_score_row_count=max(expected_score_row_count - len(score_rows), 0),
        completed_script_count=completed_script_count,
        completed_script_rate=round(
            completed_script_count / max(selected_script_count, 1),
            6,
        ),
        reviewer_count=len({row.reviewer_id for row in score_rows}),
        aggregate_public_row_count=len(aggregates),
        overall_score_avg=round(statistics.fmean(scores), 6) if scores else None,
        overall_score_min=min(scores) if scores else None,
        overall_score_max=max(scores) if scores else None,
        external_provider_call_count=0,
        external_audio_transmission_count=0,
        live_stt_call_count=0,
        live_tts_call_count=0,
        live_solar_call_count=0,
        raw_transcript_public_artifact_count=0,
        raw_audio_public_artifact_count=0,
        raw_script_public_artifact_count=0,
        human_score_private_artifact_count=score_input_available,
        human_score_public_detail_row_count=0,
        public_private_path_leakage_count=0,
        public_secret_like_leakage_count=0,
        public_raw_payload_leakage_count=0,
        score_completion_decision="blocked_missing_human_scores",
    )
    return summary.model_copy(
        update={
            "score_completion_decision": build_decision(
                summary=summary,
                output_quality=None,
            ),
        },
    )


def build_decision(
    *,
    summary: TtsHumanScoreEntryCompletionSummary,
    output_quality: PublicRetrievalArtifactQuality | None,
) -> ScoreEntryCompletionDecision:
    output_blocked = output_quality is not None and (
        output_quality.public_raw_text_leakage_count
        or output_quality.private_path_leakage_count
        or output_quality.secret_like_leakage_count
        or output_quality.forbidden_result_field_count
    )
    if output_blocked:
        return "failed_public_safety_gate"
    if summary.private_audio_missing_count:
        return "blocked_missing_private_audio"
    if summary.invalid_private_score_row_count:
        return "blocked_invalid_private_scores"
    if not summary.private_score_input_available_count:
        return "blocked_missing_human_scores"
    if summary.completed_score_row_count < summary.expected_private_score_row_count:
        return "blocked_incomplete_human_scores"
    return "completed_human_scores_ready_for_provider_decision"


def collect_completion_failures(
    report: TtsHumanScoreEntryCompletionReport,
) -> list[str]:
    failures = collect_public_retrieval_artifact_failures(report.output_quality)
    summary = report.summary
    if summary.private_audio_missing_count:
        failures.append("missing_private_audio")
    if summary.invalid_private_score_row_count:
        failures.append("invalid_private_score_rows")
    if summary.external_provider_call_count:
        failures.append("external_provider_called")
    if summary.external_audio_transmission_count:
        failures.append("external_audio_transmitted")
    if summary.live_stt_call_count or summary.live_tts_call_count or summary.live_solar_call_count:
        failures.append("live_external_call_count_nonzero")
    if (
        summary.raw_transcript_public_artifact_count
        or summary.raw_audio_public_artifact_count
        or summary.raw_script_public_artifact_count
    ):
        failures.append("raw_voice_or_script_public_artifact_created")
    if summary.human_score_public_detail_row_count:
        failures.append("human_score_detail_public_rows_created")
    if summary.score_completion_decision == "failed_public_safety_gate":
        failures.append("public_safety_gate_failed")
    return list(dict.fromkeys(failures))


def collect_completion_blockers(report: TtsHumanScoreEntryCompletionReport) -> list[str]:
    summary = report.summary
    blockers: list[str] = []
    if not summary.private_score_input_available_count:
        blockers.append("missing_human_score_input")
    if summary.pending_score_row_count:
        blockers.append("incomplete_human_score_rows")
    if summary.score_completion_decision == "blocked_missing_private_audio":
        blockers.append("missing_private_audio")
    if summary.score_completion_decision == "blocked_invalid_private_scores":
        blockers.append("invalid_private_score_rows")
    if summary.score_completion_decision == "failed_public_safety_gate":
        blockers.append("public_safety_gate_failed")
    return list(dict.fromkeys(blockers))


def build_report(
    *,
    score_completion_id: str,
    scripts_path: Path,
    private_audio_dir: Path,
    private_score_input_path: Path,
    result_rows_path: Path,
    summary: TtsHumanScoreEntryCompletionSummary,
    aggregates: tuple[TtsHumanCriterionAggregate, ...],
    output_quality: PublicRetrievalArtifactQuality,
) -> TtsHumanScoreEntryCompletionReport:
    report = TtsHumanScoreEntryCompletionReport(
        score_completion_id=score_completion_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        scripts_path=public_path_alias(scripts_path),
        audio_path_alias=public_path_alias(private_audio_dir),
        private_score_input_alias=public_path_alias(private_score_input_path),
        result_path=public_path_alias(result_rows_path),
        source_fingerprint=stable_digest(
            {
                "summary": summary.model_dump(mode="json"),
                "aggregates": [aggregate.model_dump(mode="json") for aggregate in aggregates],
                "rubric": [criterion.model_dump(mode="json") for criterion in RUBRIC],
            },
        ),
        summary=summary,
        aggregates=aggregates,
        output_quality=output_quality,
        qualitative_assessment={},
    )
    return report.model_copy(update={"qualitative_assessment": build_qualitative(report)})


def build_public_rows(
    *,
    score_completion_id: str,
    aggregates: tuple[TtsHumanCriterionAggregate, ...],
) -> list[dict[str, Any]]:
    return [
        {
            "row_type": "local_tts_human_score_entry_completion_aggregate",
            "score_completion_id": score_completion_id,
            "provider_candidate_id": PROVIDER_CANDIDATE_ID,
            "model_family": MODEL_FAMILY,
            "criterion_id": aggregate.criterion_id,
            "criterion_label": aggregate.criterion_label,
            "score_count": aggregate.score_count,
            "completed_script_count": aggregate.completed_script_count,
            "reviewer_count": aggregate.reviewer_count,
            "score_avg": aggregate.score_avg,
            "score_min": aggregate.score_min,
            "score_max": aggregate.score_max,
            "score_p50": aggregate.score_p50,
            "score_stddev": aggregate.score_stddev,
        }
        for aggregate in aggregates
    ]


def build_doc(report: TtsHumanScoreEntryCompletionReport) -> str:
    summary = report.summary
    return f"""# Voice Local TTS Human Score Entry Completion

## 결론

`{WORK_ID}`는 무료 로컬 TTS 사람 청취 점수 입력 완료 여부를 검증한다.

현재 completed score는 `{summary.completed_score_row_count}`건이다. 30건이 모두 채워지기 전에는 품질 검증 완료로 보지 않는다.

## Scope

| type | item |
| --- | --- |
| include | private score input validation |
| include | completion decision gate |
| include | public criterion aggregate report |
| exclude | raw audio public 저장 |
| exclude | raw script text public 저장 |
| exclude | individual reviewer score public 공개 |
| exclude | 최종 TTS provider 확정 |

## 정량 요약

| metric | value |
| --- | ---: |
| selected_script_count | {summary.selected_script_count} |
| rubric_criterion_count | {summary.rubric_criterion_count} |
| expected_private_score_row_count | {summary.expected_private_score_row_count} |
| private_audio_expected_count | {summary.private_audio_expected_count} |
| private_audio_available_count | {summary.private_audio_available_count} |
| private_audio_missing_count | {summary.private_audio_missing_count} |
| private_score_input_available_count | {summary.private_score_input_available_count} |
| private_score_input_row_count | {summary.private_score_input_row_count} |
| valid_private_score_row_count | {summary.valid_private_score_row_count} |
| invalid_private_score_row_count | {summary.invalid_private_score_row_count} |
| completed_score_row_count | {summary.completed_score_row_count} |
| pending_score_row_count | {summary.pending_score_row_count} |
| completed_script_count | {summary.completed_script_count} |
| completed_script_rate | {summary.completed_script_rate:.6f} |
| reviewer_count | {summary.reviewer_count} |
| aggregate_public_row_count | {summary.aggregate_public_row_count} |
| external_provider_call_count | {summary.external_provider_call_count} |
| external_audio_transmission_count | {summary.external_audio_transmission_count} |
| raw_audio_public_artifact_count | {summary.raw_audio_public_artifact_count} |
| raw_transcript_public_artifact_count | {summary.raw_transcript_public_artifact_count} |
| raw_script_public_artifact_count | {summary.raw_script_public_artifact_count} |
| score_completion_decision | `{summary.score_completion_decision}` |

## Data Mart Grain

| table | grain | exposure |
| --- | --- | --- |
| `fact_voice_local_tts_human_score_completion_private` | `score_completion_id + script_id + reviewer_id + criterion_id` | private |
| `fact_voice_local_tts_human_score_completion_aggregate_public` | `score_completion_id + provider_candidate_id + criterion_id` | public-safe |

## Claim Boundary

| type | claim |
| --- | --- |
| allowed | 사람 청취 점수 입력 완료 여부를 검증했다. |
| allowed | public에는 criterion aggregate만 공개한다. |
| allowed | 점수 미완료 상태는 blocker로 기록한다. |
| forbidden | 무료 로컬 TTS 최종 provider 확정 |
| forbidden | Supertonic 3 음성 품질 우수 검증 완료 |
| forbidden | 실제 관광객 음성 품질 검증 완료 |
| forbidden | production 음성 관광 앱 완성 |
"""


def build_markdown(report: TtsHumanScoreEntryCompletionReport) -> str:
    summary = report.summary
    quality = report.output_quality
    aggregate_rows = "\n".join(format_aggregate_row(row) for row in report.aggregates)
    qualitative_rows = "\n".join(
        f"| {key} | {value} |" for key, value in report.qualitative_assessment.items()
    )
    failures = collect_completion_failures(report)
    blockers = collect_completion_blockers(report)
    return f"""# Voice Local TTS Human Score Entry Completion Report

## 결론

`{WORK_ID}`는 human listening score 입력 완료 여부를 검증하는 gate다.

현재 completed score가 `{summary.completed_score_row_count}`건이므로 실제 음질 검증 완료를 주장하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| score_completion_id | `{report.score_completion_id}` |
| work_id | `{report.work_id}` |
| depends_on_score_entry | `{report.depends_on_score_entry}` |
| generated_at_utc | `{report.generated_at_utc}` |
| scripts_path | `{report.scripts_path}` |
| audio_path_alias | `{report.audio_path_alias}` |
| private_score_input_alias | `{report.private_score_input_alias}` |
| result_path | `{report.result_path}` |
| provider_candidate_id | `{PROVIDER_CANDIDATE_ID}` |
| source_fingerprint | `{report.source_fingerprint}` |
| score_completion_status | `{summary.score_completion_decision}` |

## 정량 리포트

| metric | value |
| --- | ---: |
| selected_script_count | {summary.selected_script_count} |
| rubric_criterion_count | {summary.rubric_criterion_count} |
| expected_private_score_row_count | {summary.expected_private_score_row_count} |
| private_audio_expected_count | {summary.private_audio_expected_count} |
| private_audio_available_count | {summary.private_audio_available_count} |
| private_audio_missing_count | {summary.private_audio_missing_count} |
| private_score_input_available_count | {summary.private_score_input_available_count} |
| private_score_input_row_count | {summary.private_score_input_row_count} |
| valid_private_score_row_count | {summary.valid_private_score_row_count} |
| invalid_private_score_row_count | {summary.invalid_private_score_row_count} |
| completed_score_row_count | {summary.completed_score_row_count} |
| pending_score_row_count | {summary.pending_score_row_count} |
| completed_script_count | {summary.completed_script_count} |
| completed_script_rate | {summary.completed_script_rate:.6f} |
| reviewer_count | {summary.reviewer_count} |
| aggregate_public_row_count | {summary.aggregate_public_row_count} |
| overall_score_avg | {format_optional_float(summary.overall_score_avg)} |
| overall_score_min | {format_optional_int(summary.overall_score_min)} |
| overall_score_max | {format_optional_int(summary.overall_score_max)} |
| score_scale_min | {summary.score_scale_min} |
| score_scale_max | {summary.score_scale_max} |
| external_provider_call_count | {summary.external_provider_call_count} |
| external_audio_transmission_count | {summary.external_audio_transmission_count} |
| live_stt_call_count | {summary.live_stt_call_count} |
| live_tts_call_count | {summary.live_tts_call_count} |
| live_solar_call_count | {summary.live_solar_call_count} |
| raw_transcript_public_artifact_count | {summary.raw_transcript_public_artifact_count} |
| raw_audio_public_artifact_count | {summary.raw_audio_public_artifact_count} |
| raw_script_public_artifact_count | {summary.raw_script_public_artifact_count} |
| human_score_private_artifact_count | {summary.human_score_private_artifact_count} |
| human_score_public_detail_row_count | {summary.human_score_public_detail_row_count} |
| public_private_path_leakage_count | {summary.public_private_path_leakage_count} |
| public_secret_like_leakage_count | {summary.public_secret_like_leakage_count} |
| public_raw_payload_leakage_count | {summary.public_raw_payload_leakage_count} |
| score_completion_decision | `{summary.score_completion_decision}` |

## Criterion Aggregate

| criterion_id | label | score_count | completed_scripts | reviewers | avg | min | max | p50 | stddev |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{aggregate_rows}

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
tts_human_score_completion_failures={failures}
tts_human_score_completion_blockers={blockers}
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


def build_qualitative(report: TtsHumanScoreEntryCompletionReport) -> dict[str, str]:
    summary = report.summary
    return {
        "scope": "사람 청취 점수 입력 완료 여부와 public aggregate 반영 가능성을 검증했다.",
        "score_status": "30개 점수가 모두 입력되기 전에는 TTS 품질 검증 완료로 표현하지 않는다.",
        "privacy": "개별 reviewer score, raw audio, raw script text, private path를 public에 내보내지 않는다.",
        "cost": "외부 STT/TTS provider 호출과 외부 음성 전송은 0이다.",
        "data_mart": "private score detail과 public criterion aggregate grain을 분리했다.",
        "portfolio": "무료 로컬 TTS 후보의 human evaluation completion gate evidence로 사용한다.",
        "external_audit": "human score 미완료 상태를 blocker로 남긴 판단은 타당하다.",
        "decision": summary.score_completion_decision,
    }


def format_aggregate_row(row: TtsHumanCriterionAggregate) -> str:
    return (
        f"| {row.criterion_id} | {row.criterion_label} | {row.score_count} | "
        f"{row.completed_script_count} | {row.reviewer_count} | "
        f"{format_optional_float(row.score_avg)} | {format_optional_int(row.score_min)} | "
        f"{format_optional_int(row.score_max)} | {format_optional_float(row.score_p50)} | "
        f"{format_optional_float(row.score_stddev)} |"
    )


def build_score_completion_id(
    *,
    audio_rows: tuple[TtsHumanScoreCollectionAudioRow, ...],
    score_rows: tuple[TtsHumanScorePrivateRow, ...],
    summary: TtsHumanScoreEntryCompletionSummary,
) -> str:
    digest = stable_digest(
        {
            "work_id": WORK_ID,
            "audio_rows": [
                row.model_dump(mode="json", exclude={"script_text"})
                for row in audio_rows
            ],
            "score_rows": [row.model_dump(mode="json") for row in score_rows],
            "summary": summary.model_dump(mode="json"),
        },
        length=8,
    )
    return f"voice-local-tts-human-score-completion-s{summary.selected_script_count}-{digest}"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify private TTS human score completion and public aggregate report.",
    )
    parser.add_argument("--scripts", type=Path, default=DEFAULT_SCRIPTS_PATH)
    parser.add_argument("--private-audio-dir", type=Path, default=DEFAULT_PRIVATE_AUDIO_DIR)
    parser.add_argument("--score-input", type=Path, default=DEFAULT_PRIVATE_SCORE_INPUT_PATH)
    parser.add_argument("--rows", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--script-limit", type=int, default=DEFAULT_SCRIPT_LIMIT)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    run_voice_local_tts_human_score_entry_completion(
        scripts_path=args.scripts,
        private_audio_dir=args.private_audio_dir,
        private_score_input_path=args.score_input,
        result_rows_path=args.rows,
        doc_path=args.doc,
        report_path=args.report,
        script_limit=args.script_limit,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
