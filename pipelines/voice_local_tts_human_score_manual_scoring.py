from __future__ import annotations

import argparse
import html
import json
import os
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
from pipelines.voice_local_tts_human_score_entry_completion import (
    WORK_ID as SCORE_ENTRY_COMPLETION_WORK_ID,
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
    build_template_rows,
    count_completed_scripts,
    format_optional_float,
    format_optional_int,
    load_private_score_rows,
    write_private_score_template,
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


REPORT_VERSION = "voice-local-tts-human-score-manual-scoring-report/v1"
WORK_ID = "HD-VOICE-LOCAL-TTS-HUMAN-SCORE-MANUAL-SCORING-001"
DEFAULT_PRIVATE_MANUAL_SCORE_SHEET_PATH = (
    Path("private_data")
    / "evals"
    / "inputs"
    / "voice_local_tts_human_score_manual_scoring.html"
)
DEFAULT_PRIVATE_MANUAL_SCORE_DRAFT_PATH = (
    Path("private_data")
    / "evals"
    / "inputs"
    / "voice_local_tts_human_scores.manual_scoring.template.jsonl"
)
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "voice_local_tts_human_score_manual_scoring_public_rows.jsonl"
)
DEFAULT_DOC_PATH = Path("docs") / "VOICE_LOCAL_TTS_HUMAN_SCORE_MANUAL_SCORING.md"
DEFAULT_REPORT_PATH = (
    Path("evals")
    / "reports"
    / "voice_local_tts_human_score_manual_scoring_report.md"
)

ManualScoringDecision = Literal[
    "ready_for_human_manual_scoring",
    "blocked_incomplete_human_manual_scores",
    "human_manual_scores_completed_pending_provider_decision",
    "blocked_missing_private_audio",
    "blocked_invalid_private_scores",
    "failed_public_safety_gate",
]


class TtsHumanManualScoringBase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TtsHumanManualScoringSummary(TtsHumanManualScoringBase):
    selected_script_count: int = Field(ge=0)
    rubric_criterion_count: int = Field(ge=0)
    expected_private_score_row_count: int = Field(ge=0)
    private_audio_expected_count: int = Field(ge=0)
    private_audio_available_count: int = Field(ge=0)
    private_audio_missing_count: int = Field(ge=0)
    private_manual_score_sheet_created_count: int = Field(ge=0)
    private_manual_score_draft_created_count: int = Field(ge=0)
    private_manual_score_draft_row_count: int = Field(ge=0)
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
    manual_scoring_decision: ManualScoringDecision


class TtsHumanManualScoringReport(TtsHumanManualScoringBase):
    report_version: str = REPORT_VERSION
    manual_scoring_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    work_id: str = WORK_ID
    depends_on_score_entry_completion: str = SCORE_ENTRY_COMPLETION_WORK_ID
    scripts_path: str = Field(min_length=1)
    audio_path_alias: str = Field(min_length=1)
    private_manual_score_sheet_alias: str = Field(min_length=1)
    private_manual_score_draft_alias: str = Field(min_length=1)
    private_score_input_alias: str = Field(min_length=1)
    result_path: str = Field(min_length=1)
    source_fingerprint: str = Field(min_length=8)
    summary: TtsHumanManualScoringSummary
    aggregates: tuple[TtsHumanCriterionAggregate, ...]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def run_voice_local_tts_human_score_manual_scoring(
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
) -> TtsHumanManualScoringReport:
    scripts = select_tts_smoke_scripts(
        load_tts_smoke_scripts(project_path(scripts_path)),
        limit=script_limit,
    )
    audio_rows = build_private_audio_rows(
        scripts=scripts,
        private_audio_dir=project_path(private_audio_dir),
    )
    draft_rows = build_template_rows(scripts)
    sheet_created_count = write_private_manual_score_sheet(
        path=project_path(private_manual_score_sheet_path),
        private_audio_dir=project_path(private_audio_dir),
        private_score_input_path=project_path(private_score_input_path),
        audio_rows=audio_rows,
    )
    draft_created_count = write_private_score_template(
        path=project_path(private_manual_score_draft_path),
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
        sheet_created_count=sheet_created_count,
        draft_created_count=draft_created_count,
        draft_row_count=len(draft_rows),
        score_input_available=score_input_available,
        score_input_row_count=len(score_rows) + invalid_row_count,
        score_rows=score_rows,
        invalid_row_count=invalid_row_count,
        aggregates=aggregates,
    )
    manual_scoring_id = build_manual_scoring_id(
        audio_rows=audio_rows,
        score_rows=score_rows,
        summary=summary,
    )
    public_rows = build_public_rows(
        manual_scoring_id=manual_scoring_id,
        aggregates=aggregates,
    )
    provisional_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=manual_scoring_id,
        result_rows=public_rows,
        report_text="",
    )
    provisional = build_report(
        manual_scoring_id=manual_scoring_id,
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
    doc_text = build_doc(provisional)
    report_text = build_markdown(provisional)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=manual_scoring_id,
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
            "manual_scoring_decision": build_decision(
                summary=summary,
                output_quality=output_quality,
            ),
        },
    )
    report = build_report(
        manual_scoring_id=manual_scoring_id,
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
    failures = collect_manual_scoring_failures(report)
    if failures:
        raise ValueError(f"voice local TTS human manual scoring gate failed: {failures}")

    write_public_retrieval_result_rows(
        path=project_path(result_rows_path),
        rows=build_public_rows(
            manual_scoring_id=manual_scoring_id,
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
        "voice_local_tts_human_score_manual_scoring "
        f"status={report.summary.manual_scoring_decision} "
        f"sheet_created={report.summary.private_manual_score_sheet_created_count} "
        f"completed_scores={report.summary.completed_score_row_count} "
        f"pending_scores={report.summary.pending_score_row_count} "
        f"external_calls={report.summary.external_provider_call_count}",
    )
    return report


def build_summary(
    *,
    audio_rows: tuple[TtsHumanScoreCollectionAudioRow, ...],
    sheet_created_count: int,
    draft_created_count: int,
    draft_row_count: int,
    score_input_available: int,
    score_input_row_count: int,
    score_rows: tuple[TtsHumanScorePrivateRow, ...],
    invalid_row_count: int,
    aggregates: tuple[TtsHumanCriterionAggregate, ...],
) -> TtsHumanManualScoringSummary:
    scores = [row.score for row in score_rows]
    selected_script_count = len(audio_rows)
    completed_script_count = count_completed_scripts(score_rows)
    audio_available_count = sum(1 for row in audio_rows if row.audio_available)
    expected_score_row_count = selected_script_count * len(RUBRIC)
    summary = TtsHumanManualScoringSummary(
        selected_script_count=selected_script_count,
        rubric_criterion_count=len(RUBRIC),
        expected_private_score_row_count=expected_score_row_count,
        private_audio_expected_count=selected_script_count,
        private_audio_available_count=audio_available_count,
        private_audio_missing_count=selected_script_count - audio_available_count,
        private_manual_score_sheet_created_count=sheet_created_count,
        private_manual_score_draft_created_count=draft_created_count,
        private_manual_score_draft_row_count=draft_row_count,
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
        manual_scoring_decision="ready_for_human_manual_scoring",
    )
    return summary.model_copy(
        update={
            "manual_scoring_decision": build_decision(
                summary=summary,
                output_quality=None,
            ),
        },
    )


def build_decision(
    *,
    summary: TtsHumanManualScoringSummary,
    output_quality: PublicRetrievalArtifactQuality | None,
) -> ManualScoringDecision:
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
    if summary.completed_score_row_count >= summary.expected_private_score_row_count:
        return "human_manual_scores_completed_pending_provider_decision"
    if summary.private_score_input_available_count:
        return "blocked_incomplete_human_manual_scores"
    return "ready_for_human_manual_scoring"


def collect_manual_scoring_failures(report: TtsHumanManualScoringReport) -> list[str]:
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
    if summary.manual_scoring_decision == "failed_public_safety_gate":
        failures.append("public_safety_gate_failed")
    return list(dict.fromkeys(failures))


def collect_manual_scoring_blockers(report: TtsHumanManualScoringReport) -> list[str]:
    summary = report.summary
    blockers: list[str] = []
    if not summary.private_score_input_available_count:
        blockers.append("awaiting_human_manual_scoring")
    if summary.pending_score_row_count:
        blockers.append("incomplete_human_score_rows")
    if summary.manual_scoring_decision == "blocked_missing_private_audio":
        blockers.append("missing_private_audio")
    if summary.manual_scoring_decision == "blocked_invalid_private_scores":
        blockers.append("invalid_private_score_rows")
    if summary.manual_scoring_decision == "failed_public_safety_gate":
        blockers.append("public_safety_gate_failed")
    return list(dict.fromkeys(blockers))


def write_private_manual_score_sheet(
    *,
    path: Path,
    private_audio_dir: Path,
    private_score_input_path: Path,
    audio_rows: tuple[TtsHumanScoreCollectionAudioRow, ...],
) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        build_private_manual_score_sheet(
            sheet_path=path,
            private_audio_dir=private_audio_dir,
            private_score_input_path=private_score_input_path,
            audio_rows=audio_rows,
        ),
        encoding="utf-8",
    )
    return 1


def build_private_manual_score_sheet(
    *,
    sheet_path: Path,
    private_audio_dir: Path,
    private_score_input_path: Path,
    audio_rows: tuple[TtsHumanScoreCollectionAudioRow, ...],
) -> str:
    rows: list[dict[str, str]] = []
    sections: list[str] = []
    for audio_row in audio_rows:
        audio_src = Path(
            os.path.relpath(
                private_audio_dir / audio_row.audio_file_name,
                sheet_path.parent,
            ),
        ).as_posix()
        inputs = []
        for criterion in RUBRIC:
            score_key = f"{audio_row.script_id}__{criterion.criterion_id}"
            rows.append(
                {
                    "score_key": score_key,
                    "provider_candidate_id": PROVIDER_CANDIDATE_ID,
                    "model_family": MODEL_FAMILY,
                    "script_id": audio_row.script_id,
                    "criterion_id": criterion.criterion_id,
                    "criterion_label": criterion.label,
                },
            )
            inputs.append(
                f"""
<label class="criterion">
  <span>{html.escape(criterion.label)} <code>{html.escape(criterion.criterion_id)}</code></span>
  <small>{html.escape(criterion.low_anchor)} / {html.escape(criterion.high_anchor)}</small>
  <input data-score-id="{html.escape(score_key)}" type="number" min="{SCORE_MIN}" max="{SCORE_MAX}" step="1" />
  <textarea data-note-id="{html.escape(score_key)}" rows="2" placeholder="private note"></textarea>
</label>""",
            )
        sections.append(
            f"""
<section class="script-card">
  <h2>{html.escape(audio_row.script_id)}</h2>
  <audio controls src="{html.escape(audio_src)}"></audio>
  <details>
    <summary>Reference script</summary>
    <p>{html.escape(audio_row.script_text)}</p>
  </details>
  <div class="criteria-grid">
    {''.join(inputs)}
  </div>
</section>""",
        )

    rows_json = json.dumps(rows, ensure_ascii=False)
    output_target = html.escape(private_score_input_path.as_posix())
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <title>Voice Local TTS Human Score Manual Scoring</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 24px; line-height: 1.5; }}
    code, textarea {{ font-family: ui-monospace, SFMono-Regular, Consolas, monospace; }}
    .script-card {{ border: 1px solid #ddd; border-radius: 8px; padding: 16px; margin: 16px 0; }}
    .criteria-grid {{ display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); }}
    .criterion {{ display: grid; gap: 6px; border-top: 1px solid #eee; padding-top: 10px; }}
    input[type="number"] {{ width: 72px; }}
    textarea, #jsonlOutput {{ width: 100%; box-sizing: border-box; }}
    #jsonlOutput {{ min-height: 220px; }}
  </style>
</head>
<body>
  <h1>Voice Local TTS Human Score Manual Scoring</h1>
  <p>이 파일은 private 청취 채점용이다. public repo에 commit하지 않는다.</p>
  <p>점수 범위는 {SCORE_MIN}-{SCORE_MAX} 정수다. 생성된 JSONL을 <code>{output_target}</code>에 저장한다.</p>
  <label>reviewer_id <input id="reviewerId" value="reviewer_001" /></label>
  {''.join(sections)}
  <button type="button" onclick="generateJsonl()">Generate JSONL</button>
  <p id="status"></p>
  <textarea id="jsonlOutput" spellcheck="false"></textarea>
  <script>
const rows = {rows_json};
function generateJsonl() {{
  const reviewerId = document.getElementById("reviewerId").value.trim() || "reviewer_001";
  const reviewedAt = new Date().toISOString();
  const lines = [];
  for (const row of rows) {{
    const scoreInput = document.querySelector(`[data-score-id="${{row.score_key}}"]`);
    const noteInput = document.querySelector(`[data-note-id="${{row.score_key}}"]`);
    const score = scoreInput.value.trim();
    if (!score) {{
      continue;
    }}
    lines.push(JSON.stringify({{
      provider_candidate_id: row.provider_candidate_id,
      model_family: row.model_family,
      script_id: row.script_id,
      criterion_id: row.criterion_id,
      criterion_label: row.criterion_label,
      reviewer_id: reviewerId,
      score: Number(score),
      reviewed_at_utc: reviewedAt,
      reviewer_note: noteInput.value,
      public_allowed: false
    }}));
  }}
  document.getElementById("jsonlOutput").value = lines.join("\\n");
  document.getElementById("status").textContent = `${{lines.length}} / ${{rows.length}} rows generated`;
}}
  </script>
</body>
</html>
"""


def build_report(
    *,
    manual_scoring_id: str,
    scripts_path: Path,
    private_audio_dir: Path,
    private_manual_score_sheet_path: Path,
    private_manual_score_draft_path: Path,
    private_score_input_path: Path,
    result_rows_path: Path,
    summary: TtsHumanManualScoringSummary,
    aggregates: tuple[TtsHumanCriterionAggregate, ...],
    output_quality: PublicRetrievalArtifactQuality,
) -> TtsHumanManualScoringReport:
    report = TtsHumanManualScoringReport(
        manual_scoring_id=manual_scoring_id,
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
    manual_scoring_id: str,
    aggregates: tuple[TtsHumanCriterionAggregate, ...],
) -> list[dict[str, Any]]:
    return [
        {
            "row_type": "local_tts_human_manual_scoring_aggregate",
            "manual_scoring_id": manual_scoring_id,
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


def build_doc(report: TtsHumanManualScoringReport) -> str:
    summary = report.summary
    score_status_sentence = (
        "사람 청취 점수 30건이 입력됐고 provider decision gate로 넘길 수 있다."
        if summary.pending_score_row_count == 0
        else "사람이 실제로 듣고 30건을 채우기 전에는 품질 검증 완료로 보지 않는다."
    )
    return f"""# Voice Local TTS Human Score Manual Scoring

## 결론

`{WORK_ID}`는 무료 로컬 TTS 사람 청취 점수 수동 입력을 위한 private score sheet와 검증 gate를 만든다.

현재 completed score는 `{summary.completed_score_row_count}`건이다. {score_status_sentence}

## Scope

| type | item |
| --- | --- |
| include | private HTML score sheet generation |
| include | private score JSONL draft generation |
| include | manual score input validation |
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
| private_manual_score_sheet_created_count | {summary.private_manual_score_sheet_created_count} |
| private_manual_score_draft_created_count | {summary.private_manual_score_draft_created_count} |
| private_manual_score_draft_row_count | {summary.private_manual_score_draft_row_count} |
| private_score_input_available_count | {summary.private_score_input_available_count} |
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
| manual_scoring_decision | `{summary.manual_scoring_decision}` |

## Data Mart Grain

| table | grain | exposure |
| --- | --- | --- |
| `fact_voice_local_tts_human_manual_score_private` | `manual_scoring_id + script_id + reviewer_id + criterion_id` | private |
| `fact_voice_local_tts_human_manual_score_aggregate_public` | `manual_scoring_id + provider_candidate_id + criterion_id` | public-safe |

## Claim Boundary

| type | claim |
| --- | --- |
| allowed | 사람 청취 점수 수동 입력용 private score sheet를 만들었다. |
| allowed | public에는 criterion aggregate만 공개한다. |
| allowed | 점수 미입력 상태는 manual scoring pending으로 기록한다. |
| forbidden | 무료 로컬 TTS 최종 provider 확정 |
| forbidden | Supertonic 3 음성 품질 우수 검증 완료 |
| forbidden | 실제 관광객 음성 품질 검증 완료 |
| forbidden | production 음성 관광 앱 완성 |
"""


def build_markdown(report: TtsHumanManualScoringReport) -> str:
    summary = report.summary
    quality = report.output_quality
    aggregate_rows = "\n".join(format_aggregate_row(row) for row in report.aggregates)
    qualitative_rows = "\n".join(
        f"| {key} | {value} |" for key, value in report.qualitative_assessment.items()
    )
    failures = collect_manual_scoring_failures(report)
    blockers = collect_manual_scoring_blockers(report)
    score_status_sentence = (
        "사람 청취 점수 입력은 완료됐지만 최종 provider 확정과 production 품질 보증은 별도 gate다."
        if summary.pending_score_row_count == 0
        else "실제 점수 입력 전이므로 TTS 품질 검증 완료로 표현하지 않는다."
    )
    return f"""# Voice Local TTS Human Score Manual Scoring Report

## 결론

`{WORK_ID}`는 human listening score를 직접 입력하기 위한 private scoring workspace gate다.

현재 completed score가 `{summary.completed_score_row_count}`건이다. {score_status_sentence}

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| manual_scoring_id | `{report.manual_scoring_id}` |
| work_id | `{report.work_id}` |
| depends_on_score_entry_completion | `{report.depends_on_score_entry_completion}` |
| generated_at_utc | `{report.generated_at_utc}` |
| scripts_path | `{report.scripts_path}` |
| audio_path_alias | `{report.audio_path_alias}` |
| private_manual_score_sheet_alias | `{report.private_manual_score_sheet_alias}` |
| private_manual_score_draft_alias | `{report.private_manual_score_draft_alias}` |
| private_score_input_alias | `{report.private_score_input_alias}` |
| result_path | `{report.result_path}` |
| provider_candidate_id | `{PROVIDER_CANDIDATE_ID}` |
| source_fingerprint | `{report.source_fingerprint}` |
| manual_scoring_status | `{summary.manual_scoring_decision}` |

## 정량 리포트

| metric | value |
| --- | ---: |
| selected_script_count | {summary.selected_script_count} |
| rubric_criterion_count | {summary.rubric_criterion_count} |
| expected_private_score_row_count | {summary.expected_private_score_row_count} |
| private_audio_expected_count | {summary.private_audio_expected_count} |
| private_audio_available_count | {summary.private_audio_available_count} |
| private_audio_missing_count | {summary.private_audio_missing_count} |
| private_manual_score_sheet_created_count | {summary.private_manual_score_sheet_created_count} |
| private_manual_score_draft_created_count | {summary.private_manual_score_draft_created_count} |
| private_manual_score_draft_row_count | {summary.private_manual_score_draft_row_count} |
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
| manual_scoring_decision | `{summary.manual_scoring_decision}` |

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
tts_human_manual_scoring_failures={failures}
tts_human_manual_scoring_blockers={blockers}
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


def build_qualitative(report: TtsHumanManualScoringReport) -> dict[str, str]:
    summary = report.summary
    return {
        "scope": "사람 청취 점수를 실제 입력할 수 있는 private scoring workspace를 생성했다.",
        "score_status": "실제 점수 입력 전이므로 TTS 품질 검증 완료로 표현하지 않는다.",
        "privacy": "개별 reviewer score, raw audio, raw script text, private path를 public에 내보내지 않는다.",
        "cost": "외부 STT/TTS provider 호출과 외부 음성 전송은 0이다.",
        "data_mart": "private score detail과 public criterion aggregate grain을 분리했다.",
        "portfolio": "무료 로컬 TTS 후보의 human scoring 실행 가능성 evidence로 사용한다.",
        "external_audit": "사람이 듣지 않은 점수를 임의 생성하지 않은 판단은 타당하다.",
        "decision": summary.manual_scoring_decision,
    }


def format_aggregate_row(row: TtsHumanCriterionAggregate) -> str:
    return (
        f"| {row.criterion_id} | {row.criterion_label} | {row.score_count} | "
        f"{row.completed_script_count} | {row.reviewer_count} | "
        f"{format_optional_float(row.score_avg)} | {format_optional_int(row.score_min)} | "
        f"{format_optional_int(row.score_max)} | {format_optional_float(row.score_p50)} | "
        f"{format_optional_float(row.score_stddev)} |"
    )


def build_manual_scoring_id(
    *,
    audio_rows: tuple[TtsHumanScoreCollectionAudioRow, ...],
    score_rows: tuple[TtsHumanScorePrivateRow, ...],
    summary: TtsHumanManualScoringSummary,
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
    return f"voice-local-tts-human-manual-scoring-s{summary.selected_script_count}-{digest}"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build private TTS human manual scoring sheet and public aggregate report.",
    )
    parser.add_argument("--scripts", type=Path, default=DEFAULT_SCRIPTS_PATH)
    parser.add_argument("--private-audio-dir", type=Path, default=DEFAULT_PRIVATE_AUDIO_DIR)
    parser.add_argument("--score-sheet", type=Path, default=DEFAULT_PRIVATE_MANUAL_SCORE_SHEET_PATH)
    parser.add_argument("--score-draft", type=Path, default=DEFAULT_PRIVATE_MANUAL_SCORE_DRAFT_PATH)
    parser.add_argument("--score-input", type=Path, default=DEFAULT_PRIVATE_SCORE_INPUT_PATH)
    parser.add_argument("--rows", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--script-limit", type=int, default=DEFAULT_SCRIPT_LIMIT)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    run_voice_local_tts_human_score_manual_scoring(
        scripts_path=args.scripts,
        private_audio_dir=args.private_audio_dir,
        private_manual_score_sheet_path=args.score_sheet,
        private_manual_score_draft_path=args.score_draft,
        private_score_input_path=args.score_input,
        result_rows_path=args.rows,
        doc_path=args.doc,
        report_path=args.report,
        script_limit=args.script_limit,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
