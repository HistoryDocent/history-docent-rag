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
from pipelines.voice_local_tts_human_score_collection import (
    WORK_ID as SCORE_COLLECTION_WORK_ID,
)
from pipelines.voice_local_tts_human_score_collection import (
    TtsHumanScoreCollectionAudioRow,
    build_private_audio_rows,
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
    TtsHumanScoreTemplateRow,
    build_aggregates,
    build_template_rows,
    count_completed_scripts,
    format_optional_float,
    format_optional_int,
    load_private_score_rows,
    write_private_score_template,
)
from pipelines.voice_local_tts_human_score_fill import (
    WORK_ID as SCORE_FILL_WORK_ID,
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


REPORT_VERSION = "voice-local-tts-human-score-entry-report/v1"
WORK_ID = "HD-VOICE-LOCAL-TTS-HUMAN-SCORE-ENTRY-001"
DEFAULT_PRIVATE_SCORE_ENTRY_GUIDE_PATH = (
    Path("private_data")
    / "evals"
    / "inputs"
    / "voice_local_tts_human_score_entry_guide.md"
)
DEFAULT_PRIVATE_SCORE_ENTRY_DRAFT_PATH = (
    Path("private_data")
    / "evals"
    / "inputs"
    / "voice_local_tts_human_scores.entry.template.jsonl"
)
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "voice_local_tts_human_score_entry_public_rows.jsonl"
)
DEFAULT_DOC_PATH = Path("docs") / "VOICE_LOCAL_TTS_HUMAN_SCORE_ENTRY.md"
DEFAULT_REPORT_PATH = (
    Path("evals") / "reports" / "voice_local_tts_human_score_entry_report.md"
)

ScoreEntryDecision = Literal[
    "pending_manual_score_entry",
    "human_scores_entered_pending_provider_decision",
    "blocked_missing_private_audio",
    "blocked_invalid_private_scores",
    "failed_public_safety_gate",
]


class TtsHumanScoreEntryBase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TtsHumanScoreEntrySummary(TtsHumanScoreEntryBase):
    selected_script_count: int = Field(ge=0)
    rubric_criterion_count: int = Field(ge=0)
    expected_private_score_row_count: int = Field(ge=0)
    private_audio_expected_count: int = Field(ge=0)
    private_audio_available_count: int = Field(ge=0)
    private_audio_missing_count: int = Field(ge=0)
    private_score_entry_guide_created_count: int = Field(ge=0)
    private_score_entry_draft_created_count: int = Field(ge=0)
    private_score_entry_draft_row_count: int = Field(ge=0)
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
    score_entry_decision: ScoreEntryDecision


class TtsHumanScoreEntryReport(TtsHumanScoreEntryBase):
    report_version: str = REPORT_VERSION
    score_entry_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    work_id: str = WORK_ID
    depends_on_score_collection: str = SCORE_COLLECTION_WORK_ID
    depends_on_score_fill: str = SCORE_FILL_WORK_ID
    scripts_path: str = Field(min_length=1)
    audio_path_alias: str = Field(min_length=1)
    private_score_entry_guide_alias: str = Field(min_length=1)
    private_score_entry_draft_alias: str = Field(min_length=1)
    private_score_input_alias: str = Field(min_length=1)
    result_path: str = Field(min_length=1)
    source_fingerprint: str = Field(min_length=8)
    summary: TtsHumanScoreEntrySummary
    aggregates: tuple[TtsHumanCriterionAggregate, ...]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def run_voice_local_tts_human_score_entry(
    *,
    scripts_path: Path = DEFAULT_SCRIPTS_PATH,
    private_audio_dir: Path = DEFAULT_PRIVATE_AUDIO_DIR,
    private_score_entry_guide_path: Path = DEFAULT_PRIVATE_SCORE_ENTRY_GUIDE_PATH,
    private_score_entry_draft_path: Path = DEFAULT_PRIVATE_SCORE_ENTRY_DRAFT_PATH,
    private_score_input_path: Path = DEFAULT_PRIVATE_SCORE_INPUT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
    doc_path: Path = DEFAULT_DOC_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    script_limit: int = DEFAULT_SCRIPT_LIMIT,
) -> TtsHumanScoreEntryReport:
    scripts = select_tts_smoke_scripts(
        load_tts_smoke_scripts(project_path(scripts_path)),
        limit=script_limit,
    )
    audio_rows = build_private_audio_rows(
        scripts=scripts,
        private_audio_dir=project_path(private_audio_dir),
    )
    draft_rows = build_template_rows(scripts)
    guide_created_count = write_private_score_entry_guide(
        path=project_path(private_score_entry_guide_path),
        audio_rows=audio_rows,
        private_score_entry_draft_path=private_score_entry_draft_path,
        private_score_input_path=private_score_input_path,
    )
    draft_created_count = write_private_score_template(
        path=project_path(private_score_entry_draft_path),
        rows=draft_rows,
    )
    score_rows, invalid_row_count, score_input_available = load_private_score_rows(
        score_input_path=project_path(private_score_input_path),
        scripts={script.script_id for script in scripts},
        criteria={criterion.criterion_id for criterion in RUBRIC},
    )
    aggregates = build_aggregates(score_rows)
    summary = build_summary(
        audio_rows=audio_rows,
        guide_created_count=guide_created_count,
        draft_created_count=draft_created_count,
        draft_row_count=len(draft_rows),
        score_input_available=score_input_available,
        score_input_row_count=len(score_rows) + invalid_row_count,
        score_rows=score_rows,
        invalid_row_count=invalid_row_count,
        aggregates=aggregates,
    )
    score_entry_id = build_score_entry_id(
        audio_rows=audio_rows,
        draft_rows=draft_rows,
        score_rows=score_rows,
        summary=summary,
    )
    public_rows = build_public_rows(score_entry_id=score_entry_id, aggregates=aggregates)
    provisional_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=score_entry_id,
        result_rows=public_rows,
        report_text="",
    )
    provisional = build_report(
        score_entry_id=score_entry_id,
        scripts_path=scripts_path,
        private_audio_dir=private_audio_dir,
        private_score_entry_guide_path=private_score_entry_guide_path,
        private_score_entry_draft_path=private_score_entry_draft_path,
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
        run_id=score_entry_id,
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
            "score_entry_decision": build_decision(
                summary=summary,
                output_quality=output_quality,
            ),
        },
    )
    report = build_report(
        score_entry_id=score_entry_id,
        scripts_path=scripts_path,
        private_audio_dir=private_audio_dir,
        private_score_entry_guide_path=private_score_entry_guide_path,
        private_score_entry_draft_path=private_score_entry_draft_path,
        private_score_input_path=private_score_input_path,
        result_rows_path=result_rows_path,
        summary=summary,
        aggregates=aggregates,
        output_quality=output_quality,
    )
    failures = collect_entry_failures(report)
    if failures:
        raise ValueError(f"voice local TTS human score entry gate failed: {failures}")

    write_public_retrieval_result_rows(
        path=project_path(result_rows_path),
        rows=build_public_rows(score_entry_id=score_entry_id, aggregates=aggregates),
    )
    resolved_doc_path = project_path(doc_path)
    resolved_report_path = project_path(report_path)
    resolved_doc_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_report_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_doc_path.write_text(build_doc(report), encoding="utf-8")
    resolved_report_path.write_text(build_markdown(report), encoding="utf-8")
    print(
        "voice_local_tts_human_score_entry "
        f"status={report.summary.score_entry_decision} "
        f"audio_available={report.summary.private_audio_available_count} "
        f"draft_rows={report.summary.private_score_entry_draft_row_count} "
        f"completed_scores={report.summary.completed_score_row_count} "
        f"external_calls={report.summary.external_provider_call_count}",
    )
    return report


def write_private_score_entry_guide(
    *,
    path: Path,
    audio_rows: tuple[TtsHumanScoreCollectionAudioRow, ...],
    private_score_entry_draft_path: Path,
    private_score_input_path: Path,
) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        build_private_score_entry_guide(
            audio_rows=audio_rows,
            private_score_entry_draft_path=private_score_entry_draft_path,
            private_score_input_path=private_score_input_path,
        ),
        encoding="utf-8",
    )
    return 1


def build_private_score_entry_guide(
    *,
    audio_rows: tuple[TtsHumanScoreCollectionAudioRow, ...],
    private_score_entry_draft_path: Path,
    private_score_input_path: Path,
) -> str:
    rubric_rows = "\n".join(
        (
            f"| {criterion.criterion_id} | {criterion.label} | "
            f"{criterion.score_min}-{criterion.score_max} | "
            f"{criterion.low_anchor} | {criterion.high_anchor} |"
        )
        for criterion in RUBRIC
    )
    audio_rows_text = "\n".join(
        (
            f"| {row.script_id} | {row.audio_file_name} | "
            f"{'yes' if row.audio_available else 'no'} | "
            f"{row.script_text} |"
        )
        for row in audio_rows
    )
    return f"""# Voice Local TTS Human Score Entry Guide

이 문서는 private 청취 점수 입력용이다. public repo에 commit하지 않는다.

## 입력 파일

| item | path |
| --- | --- |
| score draft | `{private_score_entry_draft_path.as_posix()}` |
| score input target | `{private_score_input_path.as_posix()}` |

## 작성 규칙

1. draft를 복사해 score input target에 저장한다.
2. 각 wav를 끝까지 듣는다.
3. 모든 row의 `reviewer_id`, `score`, `reviewed_at_utc`, `reviewer_note`를 채운다.
4. `score`는 1-5 정수만 허용한다.
5. 입력 후 entry runner를 다시 실행해 aggregate report만 public에 반영한다.

## Rubric

| criterion_id | label | score_range | low_anchor | high_anchor |
| --- | --- | --- | --- | --- |
{rubric_rows}

## Audio Checklist

| script_id | audio_file_name | available | reference_script |
| --- | --- | --- | --- |
{audio_rows_text}
"""


def build_summary(
    *,
    audio_rows: tuple[TtsHumanScoreCollectionAudioRow, ...],
    guide_created_count: int,
    draft_created_count: int,
    draft_row_count: int,
    score_input_available: int,
    score_input_row_count: int,
    score_rows: tuple[TtsHumanScorePrivateRow, ...],
    invalid_row_count: int,
    aggregates: tuple[TtsHumanCriterionAggregate, ...],
) -> TtsHumanScoreEntrySummary:
    scores = [row.score for row in score_rows]
    selected_script_count = len(audio_rows)
    completed_script_count = count_completed_scripts(score_rows)
    audio_available_count = sum(1 for row in audio_rows if row.audio_available)
    expected_score_row_count = selected_script_count * len(RUBRIC)
    summary = TtsHumanScoreEntrySummary(
        selected_script_count=selected_script_count,
        rubric_criterion_count=len(RUBRIC),
        expected_private_score_row_count=expected_score_row_count,
        private_audio_expected_count=selected_script_count,
        private_audio_available_count=audio_available_count,
        private_audio_missing_count=selected_script_count - audio_available_count,
        private_score_entry_guide_created_count=guide_created_count,
        private_score_entry_draft_created_count=draft_created_count,
        private_score_entry_draft_row_count=draft_row_count,
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
        human_score_private_artifact_count=2 + score_input_available,
        human_score_public_detail_row_count=0,
        public_private_path_leakage_count=0,
        public_secret_like_leakage_count=0,
        public_raw_payload_leakage_count=0,
        score_entry_decision="pending_manual_score_entry",
    )
    return summary.model_copy(
        update={
            "score_entry_decision": build_decision(
                summary=summary,
                output_quality=None,
            ),
        },
    )


def build_decision(
    *,
    summary: TtsHumanScoreEntrySummary,
    output_quality: PublicRetrievalArtifactQuality | None,
) -> ScoreEntryDecision:
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
    if summary.completed_score_row_count == summary.expected_private_score_row_count:
        return "human_scores_entered_pending_provider_decision"
    return "pending_manual_score_entry"


def collect_entry_failures(report: TtsHumanScoreEntryReport) -> list[str]:
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
    if summary.score_entry_decision == "failed_public_safety_gate":
        failures.append("public_safety_gate_failed")
    return list(dict.fromkeys(failures))


def build_report(
    *,
    score_entry_id: str,
    scripts_path: Path,
    private_audio_dir: Path,
    private_score_entry_guide_path: Path,
    private_score_entry_draft_path: Path,
    private_score_input_path: Path,
    result_rows_path: Path,
    summary: TtsHumanScoreEntrySummary,
    aggregates: tuple[TtsHumanCriterionAggregate, ...],
    output_quality: PublicRetrievalArtifactQuality,
) -> TtsHumanScoreEntryReport:
    report = TtsHumanScoreEntryReport(
        score_entry_id=score_entry_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        scripts_path=public_path_alias(scripts_path),
        audio_path_alias=public_path_alias(private_audio_dir),
        private_score_entry_guide_alias=public_path_alias(private_score_entry_guide_path),
        private_score_entry_draft_alias=public_path_alias(private_score_entry_draft_path),
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
    score_entry_id: str,
    aggregates: tuple[TtsHumanCriterionAggregate, ...],
) -> list[dict[str, Any]]:
    return [
        {
            "row_type": "local_tts_human_score_entry_aggregate",
            "score_entry_id": score_entry_id,
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


def build_doc(report: TtsHumanScoreEntryReport) -> str:
    summary = report.summary
    score_status_sentence = (
        "사람 청취 점수 입력이 완료되어 provider decision gate로 넘길 수 있다. 최종 provider 확정과 production 품질 보증은 별도 gate다."
        if summary.pending_score_row_count == 0
        else "품질 검증 완료로 보지 않는다."
    )
    return f"""# Voice Local TTS Human Score Entry

## 결론

`{WORK_ID}`는 무료 로컬 TTS 사람 청취 점수를 private에 입력하는 도구와 public-safe aggregate gate를 만든다.

현재 실제 사람 청취 점수는 `{summary.completed_score_row_count}`건이다. {score_status_sentence}

## Scope

| type | item |
| --- | --- |
| include | private score entry guide |
| include | private score entry draft |
| include | private score input validation |
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
| private_score_entry_guide_created_count | {summary.private_score_entry_guide_created_count} |
| private_score_entry_draft_created_count | {summary.private_score_entry_draft_created_count} |
| private_score_entry_draft_row_count | {summary.private_score_entry_draft_row_count} |
| private_score_input_available_count | {summary.private_score_input_available_count} |
| completed_score_row_count | {summary.completed_score_row_count} |
| pending_score_row_count | {summary.pending_score_row_count} |
| completed_script_count | {summary.completed_script_count} |
| reviewer_count | {summary.reviewer_count} |
| aggregate_public_row_count | {summary.aggregate_public_row_count} |
| external_provider_call_count | {summary.external_provider_call_count} |
| external_audio_transmission_count | {summary.external_audio_transmission_count} |
| raw_audio_public_artifact_count | {summary.raw_audio_public_artifact_count} |
| raw_transcript_public_artifact_count | {summary.raw_transcript_public_artifact_count} |
| raw_script_public_artifact_count | {summary.raw_script_public_artifact_count} |
| score_entry_decision | `{summary.score_entry_decision}` |

## Data Mart Grain

| table | grain | exposure |
| --- | --- | --- |
| `fact_voice_local_tts_human_score_entry_private` | `score_entry_id + script_id + reviewer_id + criterion_id` | private |
| `fact_voice_local_tts_human_score_entry_aggregate_public` | `score_entry_id + provider_candidate_id + criterion_id` | public-safe |

## Claim Boundary

| type | claim |
| --- | --- |
| allowed | 사람 청취 점수 입력 도구와 검증 gate를 만들었다. |
| allowed | public에는 criterion aggregate만 공개한다. |
| allowed | 점수 미입력 상태는 pending으로 기록한다. |
| allowed | 점수 완료 시 aggregate를 provider decision gate 입력으로 사용한다. |
| forbidden | 무료 로컬 TTS 최종 provider 확정 |
| forbidden | Supertonic 3 음성 품질 우수 검증 완료 |
| forbidden | 실제 관광객 음성 품질 검증 완료 |
| forbidden | production 음성 관광 앱 완성 |
"""


def build_markdown(report: TtsHumanScoreEntryReport) -> str:
    summary = report.summary
    quality = report.output_quality
    aggregate_rows = "\n".join(format_aggregate_row(row) for row in report.aggregates)
    qualitative_rows = "\n".join(
        f"| {key} | {value} |" for key, value in report.qualitative_assessment.items()
    )
    failures = collect_entry_failures(report)
    score_status_sentence = (
        "사람 청취 점수 입력은 완료됐지만 최종 provider 확정과 production 품질 보증은 별도 gate다."
        if summary.pending_score_row_count == 0
        else "실제 음질 검증 완료를 주장하지 않는다."
    )
    return f"""# Voice Local TTS Human Score Entry Report

## 결론

`{WORK_ID}`는 human listening score를 private에 입력하고 public aggregate만 공개하는 entry gate다.

현재 completed score가 `{summary.completed_score_row_count}`건이다. {score_status_sentence}

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| score_entry_id | `{report.score_entry_id}` |
| work_id | `{report.work_id}` |
| depends_on_score_collection | `{report.depends_on_score_collection}` |
| depends_on_score_fill | `{report.depends_on_score_fill}` |
| generated_at_utc | `{report.generated_at_utc}` |
| scripts_path | `{report.scripts_path}` |
| audio_path_alias | `{report.audio_path_alias}` |
| private_score_entry_guide_alias | `{report.private_score_entry_guide_alias}` |
| private_score_entry_draft_alias | `{report.private_score_entry_draft_alias}` |
| private_score_input_alias | `{report.private_score_input_alias}` |
| result_path | `{report.result_path}` |
| provider_candidate_id | `{PROVIDER_CANDIDATE_ID}` |
| source_fingerprint | `{report.source_fingerprint}` |
| score_entry_status | `{summary.score_entry_decision}` |

## 정량 리포트

| metric | value |
| --- | ---: |
| selected_script_count | {summary.selected_script_count} |
| rubric_criterion_count | {summary.rubric_criterion_count} |
| expected_private_score_row_count | {summary.expected_private_score_row_count} |
| private_audio_expected_count | {summary.private_audio_expected_count} |
| private_audio_available_count | {summary.private_audio_available_count} |
| private_audio_missing_count | {summary.private_audio_missing_count} |
| private_score_entry_guide_created_count | {summary.private_score_entry_guide_created_count} |
| private_score_entry_draft_created_count | {summary.private_score_entry_draft_created_count} |
| private_score_entry_draft_row_count | {summary.private_score_entry_draft_row_count} |
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
| score_entry_decision | `{summary.score_entry_decision}` |

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
tts_human_score_entry_failures={failures}
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


def build_qualitative(report: TtsHumanScoreEntryReport) -> dict[str, str]:
    summary = report.summary
    score_status = (
        "사람 청취 점수 30건이 입력됐고 entry aggregate는 provider decision gate 입력으로 사용할 수 있다."
        if summary.pending_score_row_count == 0
        else "점수가 모두 입력되기 전에는 TTS 품질 검증 완료로 표현하지 않는다."
    )
    external_audit = (
        "사람 점수 완료 후에도 최종 provider 확정 claim을 분리한 판단은 타당하다."
        if summary.pending_score_row_count == 0
        else "human score 없이 최종 provider 확정을 금지한 판단은 타당하다."
    )
    return {
        "scope": "사람 청취 점수 entry guide, draft, validation gate를 만들었다.",
        "score_status": score_status,
        "privacy": "개별 reviewer score, raw audio, raw script text, private path를 public에 내보내지 않는다.",
        "cost": "외부 STT/TTS provider 호출과 외부 음성 전송은 0이다.",
        "data_mart": "private score entry detail grain과 public aggregate grain을 분리했다.",
        "portfolio": "무료 로컬 TTS 후보의 human evaluation 운영 절차 evidence로 사용한다.",
        "external_audit": external_audit,
        "decision": summary.score_entry_decision,
    }


def format_aggregate_row(row: TtsHumanCriterionAggregate) -> str:
    return (
        f"| {row.criterion_id} | {row.criterion_label} | {row.score_count} | "
        f"{row.completed_script_count} | {row.reviewer_count} | "
        f"{format_optional_float(row.score_avg)} | {format_optional_int(row.score_min)} | "
        f"{format_optional_int(row.score_max)} | {format_optional_float(row.score_p50)} | "
        f"{format_optional_float(row.score_stddev)} |"
    )


def build_score_entry_id(
    *,
    audio_rows: tuple[TtsHumanScoreCollectionAudioRow, ...],
    draft_rows: tuple[TtsHumanScoreTemplateRow, ...],
    score_rows: tuple[TtsHumanScorePrivateRow, ...],
    summary: TtsHumanScoreEntrySummary,
) -> str:
    digest = stable_digest(
        {
            "work_id": WORK_ID,
            "audio_rows": [
                row.model_dump(mode="json", exclude={"script_text"})
                for row in audio_rows
            ],
            "draft_fingerprint": stable_digest(
                [row.model_dump(mode="json") for row in draft_rows],
            ),
            "score_rows": [row.model_dump(mode="json") for row in score_rows],
            "summary": summary.model_dump(mode="json"),
        },
        length=8,
    )
    return f"voice-local-tts-human-score-entry-s{summary.selected_script_count}-{digest}"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build private TTS human score entry guide and public aggregate report.",
    )
    parser.add_argument("--scripts", type=Path, default=DEFAULT_SCRIPTS_PATH)
    parser.add_argument("--private-audio-dir", type=Path, default=DEFAULT_PRIVATE_AUDIO_DIR)
    parser.add_argument("--entry-guide", type=Path, default=DEFAULT_PRIVATE_SCORE_ENTRY_GUIDE_PATH)
    parser.add_argument("--entry-draft", type=Path, default=DEFAULT_PRIVATE_SCORE_ENTRY_DRAFT_PATH)
    parser.add_argument("--score-input", type=Path, default=DEFAULT_PRIVATE_SCORE_INPUT_PATH)
    parser.add_argument("--rows", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--script-limit", type=int, default=DEFAULT_SCRIPT_LIMIT)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    run_voice_local_tts_human_score_entry(
        scripts_path=args.scripts,
        private_audio_dir=args.private_audio_dir,
        private_score_entry_guide_path=args.entry_guide,
        private_score_entry_draft_path=args.entry_draft,
        private_score_input_path=args.score_input,
        result_rows_path=args.rows,
        doc_path=args.doc,
        report_path=args.report,
        script_limit=args.script_limit,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
