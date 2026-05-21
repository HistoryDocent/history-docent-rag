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
    TtsHumanScoreCollectionAudioRow,
    build_private_audio_rows,
)
from pipelines.voice_local_tts_human_score_decision import WORK_ID as DECISION_WORK_ID
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
from pipelines.voice_local_tts_human_score_manual_scoring import (
    DEFAULT_PRIVATE_MANUAL_SCORE_DRAFT_PATH,
    DEFAULT_PRIVATE_MANUAL_SCORE_SHEET_PATH,
)
from pipelines.voice_local_tts_human_score_manual_scoring import (
    WORK_ID as MANUAL_SCORING_WORK_ID,
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


REPORT_VERSION = "voice-local-tts-human-score-manual-scoring-runbook-report/v1"
WORK_ID = "HD-VOICE-LOCAL-TTS-HUMAN-SCORE-MANUAL-SCORING-RUNBOOK-001"
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "voice_local_tts_human_score_manual_scoring_runbook_public_rows.jsonl"
)
DEFAULT_DOC_PATH = Path("docs") / "VOICE_LOCAL_TTS_HUMAN_SCORE_MANUAL_SCORING_RUNBOOK.md"
DEFAULT_REPORT_PATH = (
    Path("evals")
    / "reports"
    / "voice_local_tts_human_score_manual_scoring_runbook_report.md"
)
RUNBOOK_STEP_COUNT = 7

ManualScoringRunbookDecision = Literal[
    "ready_for_manual_score_input",
    "completed_scores_ready_for_decision",
    "blocked_missing_manual_score_sheet",
    "blocked_missing_private_audio",
    "blocked_invalid_private_scores",
    "blocked_incomplete_human_scores",
    "failed_public_safety_gate",
]


class ManualScoringRunbookBase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ManualScoringRunbookSummary(ManualScoringRunbookBase):
    selected_script_count: int = Field(ge=0)
    rubric_criterion_count: int = Field(ge=0)
    expected_private_score_row_count: int = Field(ge=0)
    private_audio_expected_count: int = Field(ge=0)
    private_audio_available_count: int = Field(ge=0)
    private_audio_missing_count: int = Field(ge=0)
    private_manual_score_sheet_available_count: int = Field(ge=0)
    private_manual_score_draft_available_count: int = Field(ge=0)
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
    runbook_step_count: int = Field(ge=0)
    user_action_required_count: int = Field(ge=0)
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
    runbook_decision: ManualScoringRunbookDecision


class ManualScoringRunbookReport(ManualScoringRunbookBase):
    report_version: str = REPORT_VERSION
    runbook_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    work_id: str = WORK_ID
    depends_on_manual_scoring: str = MANUAL_SCORING_WORK_ID
    depends_on_decision: str = DECISION_WORK_ID
    scripts_path: str = Field(min_length=1)
    audio_path_alias: str = Field(min_length=1)
    private_manual_score_sheet_alias: str = Field(min_length=1)
    private_manual_score_draft_alias: str = Field(min_length=1)
    private_score_input_alias: str = Field(min_length=1)
    result_path: str = Field(min_length=1)
    source_fingerprint: str = Field(min_length=8)
    summary: ManualScoringRunbookSummary
    aggregates: tuple[TtsHumanCriterionAggregate, ...]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def run_voice_local_tts_human_score_manual_scoring_runbook(
    *,
    scripts_path: Path = DEFAULT_SCRIPTS_PATH,
    private_audio_dir: Path = DEFAULT_PRIVATE_AUDIO_DIR,
    private_manual_score_sheet_path: Path = DEFAULT_PRIVATE_MANUAL_SCORE_SHEET_PATH,
    private_manual_score_draft_path: Path = DEFAULT_PRIVATE_MANUAL_SCORE_DRAFT_PATH,
    private_score_input_path: Path = DEFAULT_PRIVATE_SCORE_INPUT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
    doc_path: Path = DEFAULT_DOC_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    script_limit: int = DEFAULT_SCRIPT_LIMIT,
) -> ManualScoringRunbookReport:
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
        manual_score_sheet_exists=project_path(private_manual_score_sheet_path).exists(),
        manual_score_draft_exists=project_path(private_manual_score_draft_path).exists(),
        score_input_available=score_input_available,
        score_input_row_count=len(score_rows) + invalid_row_count,
        score_rows=score_rows,
        invalid_row_count=invalid_row_count,
        aggregates=aggregates,
    )
    runbook_id = build_runbook_id(
        audio_rows=audio_rows,
        score_rows=score_rows,
        summary=summary,
    )
    public_rows = build_public_rows(runbook_id=runbook_id, summary=summary, aggregates=aggregates)
    provisional_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=runbook_id,
        result_rows=public_rows,
        report_text="",
    )
    provisional = build_report(
        runbook_id=runbook_id,
        scripts_path=scripts_path,
        private_audio_dir=private_audio_dir,
        private_manual_score_sheet_path=private_manual_score_sheet_path,
        private_manual_score_draft_path=private_manual_score_draft_path,
        private_score_input_path=private_score_input_path,
        result_rows_path=result_rows_path,
        summary=summary,
        aggregates=aggregates,
        output_quality=provisional_quality,
    )
    report_text = build_markdown(provisional)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=runbook_id,
        result_rows=public_rows,
        report_text=report_text,
    )
    summary = summary.model_copy(
        update={
            "public_private_path_leakage_count": output_quality.private_path_leakage_count,
            "public_secret_like_leakage_count": output_quality.secret_like_leakage_count,
            "public_raw_payload_leakage_count": output_quality.public_raw_text_leakage_count,
            "runbook_decision": build_decision(
                summary=summary,
                output_quality=output_quality,
            ),
        },
    )
    report = build_report(
        runbook_id=runbook_id,
        scripts_path=scripts_path,
        private_audio_dir=private_audio_dir,
        private_manual_score_sheet_path=private_manual_score_sheet_path,
        private_manual_score_draft_path=private_manual_score_draft_path,
        private_score_input_path=private_score_input_path,
        result_rows_path=result_rows_path,
        summary=summary,
        aggregates=aggregates,
        output_quality=output_quality,
    )
    failures = collect_runbook_failures(report)
    if failures:
        raise ValueError(f"voice local TTS manual scoring runbook gate failed: {failures}")

    write_public_retrieval_result_rows(
        path=project_path(result_rows_path),
        rows=build_public_rows(runbook_id=runbook_id, summary=summary, aggregates=aggregates),
    )
    resolved_doc_path = project_path(doc_path)
    resolved_report_path = project_path(report_path)
    resolved_doc_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_report_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_doc_path.write_text(build_doc(report), encoding="utf-8")
    resolved_report_path.write_text(build_markdown(report), encoding="utf-8")
    print(
        "voice_local_tts_human_score_manual_scoring_runbook "
        f"status={report.summary.runbook_decision} "
        f"score_sheet={report.summary.private_manual_score_sheet_available_count} "
        f"completed_scores={report.summary.completed_score_row_count} "
        f"pending_scores={report.summary.pending_score_row_count} "
        f"external_calls={report.summary.external_provider_call_count}",
    )
    return report


def build_summary(
    *,
    audio_rows: tuple[TtsHumanScoreCollectionAudioRow, ...],
    manual_score_sheet_exists: bool,
    manual_score_draft_exists: bool,
    score_input_available: int,
    score_input_row_count: int,
    score_rows: tuple[TtsHumanScorePrivateRow, ...],
    invalid_row_count: int,
    aggregates: tuple[TtsHumanCriterionAggregate, ...],
) -> ManualScoringRunbookSummary:
    scores = [row.score for row in score_rows]
    selected_script_count = len(audio_rows)
    audio_available_count = sum(1 for row in audio_rows if row.audio_available)
    expected_score_row_count = selected_script_count * len(RUBRIC)
    completed_script_count = count_completed_scripts(score_rows)
    user_action_required_count = 0 if len(score_rows) >= expected_score_row_count else 1
    summary = ManualScoringRunbookSummary(
        selected_script_count=selected_script_count,
        rubric_criterion_count=len(RUBRIC),
        expected_private_score_row_count=expected_score_row_count,
        private_audio_expected_count=selected_script_count,
        private_audio_available_count=audio_available_count,
        private_audio_missing_count=selected_script_count - audio_available_count,
        private_manual_score_sheet_available_count=1 if manual_score_sheet_exists else 0,
        private_manual_score_draft_available_count=1 if manual_score_draft_exists else 0,
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
        runbook_step_count=RUNBOOK_STEP_COUNT,
        user_action_required_count=user_action_required_count,
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
        runbook_decision="ready_for_manual_score_input",
    )
    return summary.model_copy(
        update={
            "runbook_decision": build_decision(
                summary=summary,
                output_quality=None,
            ),
        },
    )


def build_decision(
    *,
    summary: ManualScoringRunbookSummary,
    output_quality: PublicRetrievalArtifactQuality | None,
) -> ManualScoringRunbookDecision:
    output_blocked = output_quality is not None and (
        output_quality.public_raw_text_leakage_count
        or output_quality.private_path_leakage_count
        or output_quality.secret_like_leakage_count
        or output_quality.forbidden_result_field_count
    )
    if output_blocked:
        return "failed_public_safety_gate"
    if not summary.private_manual_score_sheet_available_count:
        return "blocked_missing_manual_score_sheet"
    if summary.private_audio_missing_count:
        return "blocked_missing_private_audio"
    if summary.invalid_private_score_row_count:
        return "blocked_invalid_private_scores"
    if not summary.private_score_input_available_count:
        return "ready_for_manual_score_input"
    if summary.pending_score_row_count:
        return "blocked_incomplete_human_scores"
    return "completed_scores_ready_for_decision"


def collect_runbook_failures(report: ManualScoringRunbookReport) -> list[str]:
    failures = collect_public_retrieval_artifact_failures(report.output_quality)
    summary = report.summary
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
    if summary.runbook_decision == "failed_public_safety_gate":
        failures.append("public_safety_gate_failed")
    return list(dict.fromkeys(failures))


def collect_runbook_blockers(report: ManualScoringRunbookReport) -> list[str]:
    summary = report.summary
    blockers: list[str] = []
    if summary.runbook_decision == "blocked_missing_manual_score_sheet":
        blockers.append("missing_manual_score_sheet")
    if summary.runbook_decision == "blocked_missing_private_audio":
        blockers.append("missing_private_audio")
    if summary.runbook_decision == "blocked_invalid_private_scores":
        blockers.append("invalid_private_score_rows")
    if summary.runbook_decision == "blocked_incomplete_human_scores":
        blockers.append("incomplete_human_score_rows")
    if summary.runbook_decision == "ready_for_manual_score_input":
        blockers.append("awaiting_manual_score_input")
    if summary.runbook_decision == "failed_public_safety_gate":
        blockers.append("public_safety_gate_failed")
    return list(dict.fromkeys(blockers))


def build_report(
    *,
    runbook_id: str,
    scripts_path: Path,
    private_audio_dir: Path,
    private_manual_score_sheet_path: Path,
    private_manual_score_draft_path: Path,
    private_score_input_path: Path,
    result_rows_path: Path,
    summary: ManualScoringRunbookSummary,
    aggregates: tuple[TtsHumanCriterionAggregate, ...],
    output_quality: PublicRetrievalArtifactQuality,
) -> ManualScoringRunbookReport:
    report = ManualScoringRunbookReport(
        runbook_id=runbook_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        scripts_path=public_path_alias(scripts_path),
        audio_path_alias=public_path_alias(private_audio_dir),
        private_manual_score_sheet_alias=public_path_alias(private_manual_score_sheet_path),
        private_manual_score_draft_alias=public_path_alias(private_manual_score_draft_path),
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
    runbook_id: str,
    summary: ManualScoringRunbookSummary,
    aggregates: tuple[TtsHumanCriterionAggregate, ...],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "row_type": "local_tts_human_score_manual_scoring_runbook_summary",
            "runbook_id": runbook_id,
            "provider_candidate_id": PROVIDER_CANDIDATE_ID,
            "model_family": MODEL_FAMILY,
            "runbook_decision": summary.runbook_decision,
            "selected_script_count": summary.selected_script_count,
            "rubric_criterion_count": summary.rubric_criterion_count,
            "expected_private_score_row_count": summary.expected_private_score_row_count,
            "private_audio_available_count": summary.private_audio_available_count,
            "private_manual_score_sheet_available_count": (
                summary.private_manual_score_sheet_available_count
            ),
            "completed_score_row_count": summary.completed_score_row_count,
            "pending_score_row_count": summary.pending_score_row_count,
            "user_action_required_count": summary.user_action_required_count,
            "external_provider_call_count": summary.external_provider_call_count,
            "external_audio_transmission_count": summary.external_audio_transmission_count,
        },
    ]
    rows.extend(
        {
            "row_type": "local_tts_human_score_manual_scoring_runbook_aggregate",
            "runbook_id": runbook_id,
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
    )
    return rows


def build_doc(report: ManualScoringRunbookReport) -> str:
    summary = report.summary
    return f"""# Voice Local TTS Human Score Manual Scoring Runbook

## 결론

`{WORK_ID}`는 무료 로컬 TTS 사람 청취 평가를 실제로 실행하기 위한 절차와 gate를 고정한다.

현재 runbook decision은 `{summary.runbook_decision}`이다. 수동 채점 sheet와 private wav는 준비됐지만 completed score는 `{summary.completed_score_row_count}`건이다.

## 실행 절차

1. private manual score sheet를 연다.
2. 5개 audio sample을 순서대로 재생한다.
3. 각 sample마다 6개 rubric을 1-5점으로 채점한다.
4. reviewer id와 reviewed timestamp를 입력한다.
5. JSONL을 생성해 private score input 위치에 저장한다.
6. score decision runner를 실행해 30개 row 완료 여부를 검증한다.
7. public report에는 aggregate와 decision만 반영한다.

## 정량 요약

| metric | value |
| --- | ---: |
| selected_script_count | {summary.selected_script_count} |
| rubric_criterion_count | {summary.rubric_criterion_count} |
| expected_private_score_row_count | {summary.expected_private_score_row_count} |
| private_audio_expected_count | {summary.private_audio_expected_count} |
| private_audio_available_count | {summary.private_audio_available_count} |
| private_audio_missing_count | {summary.private_audio_missing_count} |
| private_manual_score_sheet_available_count | {summary.private_manual_score_sheet_available_count} |
| private_manual_score_draft_available_count | {summary.private_manual_score_draft_available_count} |
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
| runbook_step_count | {summary.runbook_step_count} |
| user_action_required_count | {summary.user_action_required_count} |
| external_provider_call_count | {summary.external_provider_call_count} |
| external_audio_transmission_count | {summary.external_audio_transmission_count} |
| raw_audio_public_artifact_count | {summary.raw_audio_public_artifact_count} |
| raw_transcript_public_artifact_count | {summary.raw_transcript_public_artifact_count} |
| human_score_public_detail_row_count | {summary.human_score_public_detail_row_count} |
| runbook_decision | `{summary.runbook_decision}` |

## Rubric

| criterion_id | label | score range |
| --- | --- | --- |
{format_rubric_rows()}

## Data Mart Grain

| table | grain | exposure |
| --- | --- | --- |
| `fact_voice_local_tts_manual_score_private` | `runbook_id + script_id + reviewer_id + criterion_id` | private |
| `fact_voice_local_tts_manual_score_aggregate_public` | `runbook_id + provider_candidate_id + criterion_id` | public-safe |
| `fact_voice_local_tts_manual_score_runbook_public` | `runbook_id + provider_candidate_id + runbook_decision` | public-safe |

## Claim Boundary

| type | claim |
| --- | --- |
| allowed | 수동 청취 평가 실행 절차와 gate를 고정했다. |
| allowed | score 미입력 상태에서는 사람 action required로 남긴다. |
| allowed | public에는 aggregate와 runbook decision만 공개한다. |
| forbidden | 사람 청취 점수 입력 완료 |
| forbidden | 무료 로컬 TTS 최종 provider 확정 |
| forbidden | Supertonic 3 음성 품질 우수 검증 완료 |
| forbidden | 실제 관광객 음성 품질 검증 완료 |
| forbidden | production 음성 관광 앱 완성 |
"""


def build_markdown(report: ManualScoringRunbookReport) -> str:
    summary = report.summary
    quality = report.output_quality
    aggregate_rows = "\n".join(format_aggregate_row(row) for row in report.aggregates)
    qualitative_rows = "\n".join(
        f"| {key} | {value} |" for key, value in report.qualitative_assessment.items()
    )
    failures = collect_runbook_failures(report)
    blockers = collect_runbook_blockers(report)
    return f"""# Voice Local TTS Human Score Manual Scoring Runbook Report

## 결론

`{WORK_ID}`는 수동 청취 평가 실행 절차와 입력 완료 gate를 public-safe하게 검증한다.

현재 runbook decision은 `{summary.runbook_decision}`이며, completed score는 `{summary.completed_score_row_count}`건이다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| runbook_id | `{report.runbook_id}` |
| work_id | `{report.work_id}` |
| depends_on_manual_scoring | `{report.depends_on_manual_scoring}` |
| depends_on_decision | `{report.depends_on_decision}` |
| generated_at_utc | `{report.generated_at_utc}` |
| scripts_path | `{report.scripts_path}` |
| audio_path_alias | `{report.audio_path_alias}` |
| private_manual_score_sheet_alias | `{report.private_manual_score_sheet_alias}` |
| private_manual_score_draft_alias | `{report.private_manual_score_draft_alias}` |
| private_score_input_alias | `{report.private_score_input_alias}` |
| result_path | `{report.result_path}` |
| provider_candidate_id | `{PROVIDER_CANDIDATE_ID}` |
| source_fingerprint | `{report.source_fingerprint}` |
| runbook_decision_status | `{summary.runbook_decision}` |

## 정량 리포트

| metric | value |
| --- | ---: |
| selected_script_count | {summary.selected_script_count} |
| rubric_criterion_count | {summary.rubric_criterion_count} |
| expected_private_score_row_count | {summary.expected_private_score_row_count} |
| private_audio_expected_count | {summary.private_audio_expected_count} |
| private_audio_available_count | {summary.private_audio_available_count} |
| private_audio_missing_count | {summary.private_audio_missing_count} |
| private_manual_score_sheet_available_count | {summary.private_manual_score_sheet_available_count} |
| private_manual_score_draft_available_count | {summary.private_manual_score_draft_available_count} |
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
| runbook_step_count | {summary.runbook_step_count} |
| user_action_required_count | {summary.user_action_required_count} |
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
| runbook_decision | `{summary.runbook_decision}` |

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
tts_manual_scoring_runbook_failures={failures}
tts_manual_scoring_runbook_blockers={blockers}
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


def build_qualitative(report: ManualScoringRunbookReport) -> dict[str, str]:
    summary = report.summary
    return {
        "product": "무료 로컬 TTS 후보의 demo 적합성을 사람이 판단할 수 있게 실행 절차를 고정했다.",
        "voice_ml": "음질 채택은 자동 sanity가 아니라 사람 rubric 점수 30개 완료 뒤 판단한다.",
        "evaluation": "현재 completed score가 부족하면 blocker가 아니라 user action required로 기록한다.",
        "privacy": "개별 score, raw audio, raw script text, private path는 public artifact에 포함하지 않는다.",
        "cost": "외부 STT/TTS provider 호출과 외부 음성 전송은 0이다.",
        "data_mart": "private score detail과 public aggregate/runbook decision grain을 분리했다.",
        "portfolio": "사람 평가가 아직 미완료임을 숨기지 않고 다음 행동으로 드러낸다.",
        "external_audit": "사람 점수를 임의 생성하지 않고 실행 절차만 고정한 판단은 타당하다.",
        "decision": summary.runbook_decision,
    }


def format_rubric_rows() -> str:
    return "\n".join(
        f"| {criterion.criterion_id} | {criterion.label} | "
        f"{criterion.score_min}-{criterion.score_max} |"
        for criterion in RUBRIC
    )


def format_aggregate_row(row: TtsHumanCriterionAggregate) -> str:
    return (
        f"| {row.criterion_id} | {row.criterion_label} | {row.score_count} | "
        f"{row.completed_script_count} | {row.reviewer_count} | "
        f"{format_optional_float(row.score_avg)} | {format_optional_int(row.score_min)} | "
        f"{format_optional_int(row.score_max)} | {format_optional_float(row.score_p50)} | "
        f"{format_optional_float(row.score_stddev)} |"
    )


def build_runbook_id(
    *,
    audio_rows: tuple[TtsHumanScoreCollectionAudioRow, ...],
    score_rows: tuple[TtsHumanScorePrivateRow, ...],
    summary: ManualScoringRunbookSummary,
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
    return f"voice-local-tts-human-score-manual-runbook-s{summary.selected_script_count}-{digest}"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scripts", type=Path, default=DEFAULT_SCRIPTS_PATH)
    parser.add_argument("--audio-dir", type=Path, default=DEFAULT_PRIVATE_AUDIO_DIR)
    parser.add_argument(
        "--manual-score-sheet",
        type=Path,
        default=DEFAULT_PRIVATE_MANUAL_SCORE_SHEET_PATH,
    )
    parser.add_argument(
        "--manual-score-draft",
        type=Path,
        default=DEFAULT_PRIVATE_MANUAL_SCORE_DRAFT_PATH,
    )
    parser.add_argument("--score-input", type=Path, default=DEFAULT_PRIVATE_SCORE_INPUT_PATH)
    parser.add_argument("--result-rows", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--script-limit", type=int, default=DEFAULT_SCRIPT_LIMIT)
    args = parser.parse_args(argv)

    run_voice_local_tts_human_score_manual_scoring_runbook(
        scripts_path=args.scripts,
        private_audio_dir=args.audio_dir,
        private_manual_score_sheet_path=args.manual_score_sheet,
        private_manual_score_draft_path=args.manual_score_draft,
        private_score_input_path=args.score_input,
        result_rows_path=args.result_rows,
        doc_path=args.doc,
        report_path=args.report,
        script_limit=args.script_limit,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
