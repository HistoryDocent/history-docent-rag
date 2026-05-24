from __future__ import annotations

import json
import re
from pathlib import Path

import pipelines.voice_local_tts_human_score_manual_scoring as manual


DOC_PATH = Path("docs/VOICE_LOCAL_TTS_HUMAN_SCORE_MANUAL_SCORING.md")
REPORT_PATH = Path("evals/reports/voice_local_tts_human_score_manual_scoring_report.md")
README_PATH = Path("README.md")
TODO_PATH = Path("docs/TODO.md")
LEDGER_PATH = Path("docs/RAG_DECISION_LEDGER.md")
CHECKLIST_PATH = Path("docs/CHECKLIST.md")
WBS_PATH = Path("docs/WBS.md")
ROADMAP_PATH = Path("docs/ROADMAP.md")
VOICE_DECISION_PATH = Path("docs/VOICE_PROVIDER_DECISION.md")
REQUIRED_LINKS = (
    "docs/VOICE_LOCAL_TTS_HUMAN_SCORE_MANUAL_SCORING.md",
    "evals/reports/voice_local_tts_human_score_manual_scoring_report.md",
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


def _write_fixture_audio_files(audio_dir: Path) -> None:
    audio_dir.mkdir(parents=True, exist_ok=True)
    for index in range(1, 6):
        (audio_dir / f"tts-smoke-docent-{index:03d}.wav").write_bytes(b"fixture wav")


def _write_completed_private_scores(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as output:
        for script_index in range(1, 6):
            script_id = f"tts-smoke-docent-{script_index:03d}"
            for criterion in manual.RUBRIC:
                output.write(
                    json.dumps(
                        {
                            "provider_candidate_id": manual.PROVIDER_CANDIDATE_ID,
                            "model_family": manual.MODEL_FAMILY,
                            "script_id": script_id,
                            "criterion_id": criterion.criterion_id,
                            "criterion_label": criterion.label,
                            "reviewer_id": "reviewer_001",
                            "score": 4,
                            "reviewed_at_utc": "2026-05-21T00:00:00+00:00",
                            "reviewer_note": "fixture private note",
                            "public_allowed": False,
                        },
                        ensure_ascii=False,
                    )
                    + "\n",
                )


def test_manual_scoring_runner_creates_private_sheet_without_fake_scores(
    tmp_path: Path,
) -> None:
    audio_dir = tmp_path / "audio"
    _write_fixture_audio_files(audio_dir)

    report = manual.run_voice_local_tts_human_score_manual_scoring(
        private_audio_dir=audio_dir,
        private_manual_score_sheet_path=tmp_path / "manual_score_sheet.html",
        private_manual_score_draft_path=tmp_path / "scores.manual.template.jsonl",
        private_score_input_path=tmp_path / "missing_scores.jsonl",
        doc_path=tmp_path / "VOICE_LOCAL_TTS_HUMAN_SCORE_MANUAL_SCORING.md",
        report_path=tmp_path / "voice_local_tts_human_score_manual_scoring_report.md",
        result_rows_path=tmp_path / "voice_local_tts_human_score_manual_scoring_rows.jsonl",
    )

    assert manual.collect_manual_scoring_failures(report) == []
    assert manual.collect_manual_scoring_blockers(report) == [
        "awaiting_human_manual_scoring",
        "incomplete_human_score_rows",
    ]
    assert report.summary.selected_script_count == 5
    assert report.summary.rubric_criterion_count == 6
    assert report.summary.expected_private_score_row_count == 30
    assert report.summary.private_audio_available_count == 5
    assert report.summary.private_audio_missing_count == 0
    assert report.summary.private_manual_score_sheet_created_count == 1
    assert report.summary.private_manual_score_draft_created_count == 1
    assert report.summary.private_manual_score_draft_row_count == 30
    assert report.summary.private_score_input_available_count == 0
    assert report.summary.completed_score_row_count == 0
    assert report.summary.pending_score_row_count == 30
    assert report.summary.aggregate_public_row_count == 6
    assert report.summary.external_provider_call_count == 0
    assert report.summary.external_audio_transmission_count == 0
    assert report.summary.human_score_public_detail_row_count == 0
    assert report.summary.manual_scoring_decision == "ready_for_human_manual_scoring"

    sheet = (tmp_path / "manual_score_sheet.html").read_text(encoding="utf-8")
    assert "<audio controls" in sheet
    assert "Generate JSONL" in sheet
    assert "Reference script" in sheet

    draft_rows = [
        json.loads(line)
        for line in (tmp_path / "scores.manual.template.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(draft_rows) == 30
    assert all(row["score"] is None for row in draft_rows)
    assert all(row["public_allowed"] is False for row in draft_rows)


def test_manual_scoring_runner_accepts_completed_private_scores(
    tmp_path: Path,
) -> None:
    audio_dir = tmp_path / "audio"
    score_input_path = tmp_path / "scores.jsonl"
    _write_fixture_audio_files(audio_dir)
    _write_completed_private_scores(score_input_path)

    report = manual.run_voice_local_tts_human_score_manual_scoring(
        private_audio_dir=audio_dir,
        private_manual_score_sheet_path=tmp_path / "manual_score_sheet.html",
        private_manual_score_draft_path=tmp_path / "scores.manual.template.jsonl",
        private_score_input_path=score_input_path,
        doc_path=tmp_path / "VOICE_LOCAL_TTS_HUMAN_SCORE_MANUAL_SCORING.md",
        report_path=tmp_path / "voice_local_tts_human_score_manual_scoring_report.md",
        result_rows_path=tmp_path / "voice_local_tts_human_score_manual_scoring_rows.jsonl",
    )

    assert manual.collect_manual_scoring_failures(report) == []
    assert manual.collect_manual_scoring_blockers(report) == []
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
    assert (
        report.summary.manual_scoring_decision
        == "human_manual_scores_completed_pending_provider_decision"
    )
    assert all(row.score_count == 5 for row in report.aggregates)
    assert all(row.score_avg == 4.0 for row in report.aggregates)


def test_manual_scoring_docs_record_completed_state() -> None:
    assert DOC_PATH.exists()
    assert REPORT_PATH.exists()

    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert manual.WORK_ID in doc
    assert manual.WORK_ID in report
    assert "private_manual_score_sheet_created_count | 1" in report
    assert "private_manual_score_draft_created_count | 1" in report
    assert "private_manual_score_draft_row_count | 30" in report
    assert "private_score_input_available_count | 1" in report
    assert "completed_score_row_count | 30" in report
    assert "pending_score_row_count | 0" in report
    assert "overall_score_avg | 5.000000" in report
    assert "aggregate_public_row_count | 6" in report
    assert "external_provider_call_count | 0" in report
    assert "external_audio_transmission_count | 0" in report
    assert "human_score_public_detail_row_count | 0" in report
    assert (
        "manual_scoring_decision | "
        "`human_manual_scores_completed_pending_provider_decision`"
    ) in report
    assert "tts_human_manual_scoring_blockers=[]" in report
    assert "External audit | PASS" in report
    assert "provider decision gate로 넘길 수 있다" in doc


def test_manual_scoring_registered_and_public_safe() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    todo = TODO_PATH.read_text(encoding="utf-8")
    ledger = LEDGER_PATH.read_text(encoding="utf-8")

    for link in REQUIRED_LINKS:
        assert link in readme
        assert Path(link).exists()

    assert "- [x] optional human TTS listening score manual scoring workspace" in todo
    assert "- [x] optional human TTS listening score manual scoring" in todo
    assert manual.WORK_ID in ledger
    assert "voice_local_tts_human_score_manual_scoring" in ledger

    for path in PUBLIC_SCAN_PATHS:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"private_data[/\\]", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)


def test_manual_scoring_keeps_forbidden_claims_forbidden() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    forbidden_section = doc.split("## Claim Boundary", maxsplit=1)[1]

    for claim in FORBIDDEN_CLAIMS:
        assert claim in forbidden_section
