from __future__ import annotations

import json
import re
from pathlib import Path

import pipelines.voice_local_tts_human_score_fill as score_fill


DOC_PATH = Path("docs/VOICE_LOCAL_TTS_HUMAN_SCORE_FILL.md")
REPORT_PATH = Path("evals/reports/voice_local_tts_human_score_fill_report.md")
README_PATH = Path("README.md")
TODO_PATH = Path("docs/TODO.md")
LEDGER_PATH = Path("docs/RAG_DECISION_LEDGER.md")
CHECKLIST_PATH = Path("docs/CHECKLIST.md")
WBS_PATH = Path("docs/WBS.md")
ROADMAP_PATH = Path("docs/ROADMAP.md")
VOICE_DECISION_PATH = Path("docs/VOICE_PROVIDER_DECISION.md")
REQUIRED_LINKS = (
    "docs/VOICE_LOCAL_TTS_HUMAN_SCORE_FILL.md",
    "evals/reports/voice_local_tts_human_score_fill_report.md",
)
PUBLIC_SCAN_PATHS = (
    README_PATH,
    DOC_PATH,
    REPORT_PATH,
    TODO_PATH,
    LEDGER_PATH,
    CHECKLIST_PATH,
    WBS_PATH,
    ROADMAP_PATH,
    VOICE_DECISION_PATH,
)
FORBIDDEN_CLAIMS = (
    "무료 로컬 TTS 최종 provider 확정",
    "Supertonic 3 음성 품질 우수 검증 완료",
    "실제 관광객 음성 품질 검증 완료",
    "production 음성 관광 앱 완성",
)


def _write_completed_private_scores(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as output:
        for script_index in range(1, 6):
            script_id = f"tts-smoke-docent-{script_index:03d}"
            for criterion in score_fill.RUBRIC:
                output.write(
                    json.dumps(
                        {
                            "provider_candidate_id": score_fill.PROVIDER_CANDIDATE_ID,
                            "script_id": script_id,
                            "audio_file_name": f"{script_id}.wav",
                            "audio_artifact_id": "fixture-audio-artifact",
                            "criterion_id": criterion.criterion_id,
                            "criterion_label": criterion.label,
                            "reviewer_id": "reviewer_001",
                            "score": 4,
                            "reviewed_at_utc": "2026-05-20T00:00:00+00:00",
                            "reviewer_note": "fixture private note",
                            "public_allowed": False,
                        },
                        ensure_ascii=False,
                    )
                    + "\n",
                )


def test_human_score_fill_runner_pending_public_safe_contract(tmp_path: Path) -> None:
    report = score_fill.run_voice_local_tts_human_score_fill(
        private_audio_dir=tmp_path / "audio",
        private_score_template_path=tmp_path / "scores.template.jsonl",
        private_score_input_path=tmp_path / "missing_scores.jsonl",
        doc_path=tmp_path / "VOICE_LOCAL_TTS_HUMAN_SCORE_FILL.md",
        report_path=tmp_path / "voice_local_tts_human_score_fill_report.md",
        result_rows_path=tmp_path / "voice_local_tts_human_score_fill_rows.jsonl",
    )

    assert score_fill.collect_score_fill_failures(report) == []
    assert report.summary.selected_script_count == 5
    assert report.summary.rubric_criterion_count == 6
    assert report.summary.expected_private_score_row_count == 30
    assert report.summary.private_template_created_count == 1
    assert report.summary.private_template_row_count == 30
    assert report.summary.private_score_input_available_count == 0
    assert report.summary.completed_score_row_count == 0
    assert report.summary.pending_score_row_count == 30
    assert report.summary.completed_script_count == 0
    assert report.summary.reviewer_count == 0
    assert report.summary.aggregate_public_row_count == 6
    assert report.summary.human_score_private_artifact_count == 1
    assert report.summary.human_score_public_detail_row_count == 0
    assert report.summary.external_provider_call_count == 0
    assert report.summary.external_audio_transmission_count == 0
    assert report.summary.raw_audio_public_artifact_count == 0
    assert report.summary.raw_transcript_public_artifact_count == 0
    assert report.summary.raw_script_public_artifact_count == 0
    assert report.summary.public_private_path_leakage_count == 0
    assert report.summary.public_secret_like_leakage_count == 0
    assert report.summary.public_raw_payload_leakage_count == 0
    assert report.summary.score_fill_decision == "pending_private_human_scores"

    template_rows = [
        json.loads(line)
        for line in (tmp_path / "scores.template.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(template_rows) == 30
    assert all(row["public_allowed"] is False for row in template_rows)
    assert all(row["score"] is None for row in template_rows)
    assert all("audio_file_name" in row for row in template_rows)
    assert all("audio_path" not in row for row in template_rows)

    public_rows = [
        json.loads(line)
        for line in (tmp_path / "voice_local_tts_human_score_fill_rows.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(public_rows) == 6
    forbidden_fields = {
        "script_id",
        "reviewer_id",
        "score_detail",
        "raw_audio",
        "raw_transcript",
        "script_text",
        "audio_path",
    }
    assert all(forbidden_fields.isdisjoint(row) for row in public_rows)


def test_human_score_fill_runner_aggregates_completed_private_scores(tmp_path: Path) -> None:
    score_input_path = tmp_path / "scores.jsonl"
    _write_completed_private_scores(score_input_path)

    report = score_fill.run_voice_local_tts_human_score_fill(
        private_audio_dir=tmp_path / "audio",
        private_score_template_path=tmp_path / "scores.template.jsonl",
        private_score_input_path=score_input_path,
        doc_path=tmp_path / "VOICE_LOCAL_TTS_HUMAN_SCORE_FILL.md",
        report_path=tmp_path / "voice_local_tts_human_score_fill_report.md",
        result_rows_path=tmp_path / "voice_local_tts_human_score_fill_rows.jsonl",
    )

    assert score_fill.collect_score_fill_failures(report) == []
    assert report.summary.private_score_input_available_count == 1
    assert report.summary.private_score_input_row_count == 30
    assert report.summary.valid_private_score_row_count == 30
    assert report.summary.invalid_private_score_row_count == 0
    assert report.summary.completed_score_row_count == 30
    assert report.summary.pending_score_row_count == 0
    assert report.summary.completed_script_count == 5
    assert report.summary.completed_script_rate == 1.0
    assert report.summary.reviewer_count == 1
    assert report.summary.overall_score_avg == 4.0
    assert report.summary.score_fill_decision == "human_scores_aggregated_pending_provider_decision"
    assert all(row.score_count == 5 for row in report.aggregates)
    assert all(row.score_avg == 4.0 for row in report.aggregates)


def test_human_score_fill_docs_record_completed_state() -> None:
    assert DOC_PATH.exists()
    assert REPORT_PATH.exists()

    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert score_fill.WORK_ID in doc
    assert score_fill.WORK_ID in report
    assert "expected_private_score_row_count | 30" in report
    assert "private_template_created_count | 1" in report
    assert "private_template_row_count | 30" in report
    assert "private_score_input_available_count | 1" in report
    assert "completed_score_row_count | 30" in report
    assert "pending_score_row_count | 0" in report
    assert "overall_score_avg | 5.000000" in report
    assert "aggregate_public_row_count | 6" in report
    assert "external_provider_call_count | 0" in report
    assert "raw_audio_public_artifact_count | 0" in report
    assert "raw_transcript_public_artifact_count | 0" in report
    assert "raw_script_public_artifact_count | 0" in report
    assert "human_score_public_detail_row_count | 0" in report
    assert "public_private_path_leakage_count | 0" in report
    assert (
        "score_fill_decision | "
        "`human_scores_aggregated_pending_provider_decision`"
    ) in report
    assert "External audit | PASS" in report
    assert "provider decision gate 입력" in doc


def test_human_score_fill_registered_and_public_safe() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    todo = TODO_PATH.read_text(encoding="utf-8")
    ledger = LEDGER_PATH.read_text(encoding="utf-8")

    for link in REQUIRED_LINKS:
        assert link in readme
        assert Path(link).exists()

    assert "- [x] optional human TTS listening score fill framework" in todo
    assert "- [x] optional human TTS listening score collection workflow" in todo
    assert "- [x] optional human TTS listening score entry tool" in todo
    assert "- [x] optional human TTS listening score entry completion verification" in todo
    assert "- [x] optional human TTS listening score manual scoring" in todo
    assert score_fill.WORK_ID in ledger
    assert "voice_local_tts_human_score_fill" in ledger

    for path in PUBLIC_SCAN_PATHS:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"private_data[/\\]", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)


def test_human_score_fill_keeps_forbidden_claims_forbidden() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    forbidden_section = doc.split("## Claim Boundary", maxsplit=1)[1]

    for claim in FORBIDDEN_CLAIMS:
        assert claim in forbidden_section
