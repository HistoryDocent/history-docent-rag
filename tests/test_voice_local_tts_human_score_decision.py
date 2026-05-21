from __future__ import annotations

import json
import re
from pathlib import Path

import pipelines.voice_local_tts_human_score_decision as decision


DOC_PATH = Path("docs/VOICE_LOCAL_TTS_HUMAN_SCORE_DECISION.md")
REPORT_PATH = Path("evals/reports/voice_local_tts_human_score_decision_report.md")
README_PATH = Path("README.md")
TODO_PATH = Path("docs/TODO.md")
LEDGER_PATH = Path("docs/RAG_DECISION_LEDGER.md")
CHECKLIST_PATH = Path("docs/CHECKLIST.md")
WBS_PATH = Path("docs/WBS.md")
ROADMAP_PATH = Path("docs/ROADMAP.md")
VOICE_DECISION_PATH = Path("docs/VOICE_PROVIDER_DECISION.md")
REQUIRED_LINKS = (
    "docs/VOICE_LOCAL_TTS_HUMAN_SCORE_DECISION.md",
    "evals/reports/voice_local_tts_human_score_decision_report.md",
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


def _write_completed_private_scores(path: Path, score: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as output:
        for script_index in range(1, 6):
            script_id = f"tts-smoke-docent-{script_index:03d}"
            for criterion in decision.RUBRIC:
                output.write(
                    json.dumps(
                        {
                            "provider_candidate_id": decision.PROVIDER_CANDIDATE_ID,
                            "script_id": script_id,
                            "criterion_id": criterion.criterion_id,
                            "reviewer_id": "reviewer_001",
                            "score": score,
                            "reviewed_at_utc": "2026-05-21T00:00:00+00:00",
                            "reviewer_note": "fixture private note",
                            "public_allowed": False,
                            "raw_private_payload": "must be ignored",
                        },
                        ensure_ascii=False,
                    )
                    + "\n",
                )


def test_human_score_decision_blocks_missing_scores(tmp_path: Path) -> None:
    audio_dir = tmp_path / "audio"
    _write_fixture_audio_files(audio_dir)

    report = decision.run_voice_local_tts_human_score_decision(
        private_audio_dir=audio_dir,
        private_score_input_path=tmp_path / "missing_scores.jsonl",
        doc_path=tmp_path / "VOICE_LOCAL_TTS_HUMAN_SCORE_DECISION.md",
        report_path=tmp_path / "voice_local_tts_human_score_decision_report.md",
        result_rows_path=tmp_path / "voice_local_tts_human_score_decision_rows.jsonl",
    )

    assert decision.collect_decision_failures(report) == []
    assert decision.collect_decision_blockers(report) == [
        "missing_human_score_input",
    ]
    assert report.summary.selected_script_count == 5
    assert report.summary.rubric_criterion_count == 6
    assert report.summary.expected_private_score_row_count == 30
    assert report.summary.private_audio_available_count == 5
    assert report.summary.private_audio_missing_count == 0
    assert report.summary.private_score_input_available_count == 0
    assert report.summary.completed_score_row_count == 0
    assert report.summary.pending_score_row_count == 30
    assert report.summary.aggregate_public_row_count == 6
    assert report.summary.provider_decision_public_row_count == 1
    assert report.summary.external_provider_call_count == 0
    assert report.summary.external_audio_transmission_count == 0
    assert report.summary.human_score_public_detail_row_count == 0
    assert report.summary.provider_decision == "blocked_missing_human_scores"

    public_rows = [
        json.loads(line)
        for line in (tmp_path / "voice_local_tts_human_score_decision_rows.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(public_rows) == 7
    assert public_rows[0]["row_type"] == "local_tts_human_score_provider_decision_summary"
    assert public_rows[0]["provider_decision"] == "blocked_missing_human_scores"
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


def test_human_score_decision_accepts_completed_high_scores(tmp_path: Path) -> None:
    audio_dir = tmp_path / "audio"
    score_input_path = tmp_path / "scores.jsonl"
    _write_fixture_audio_files(audio_dir)
    _write_completed_private_scores(score_input_path, score=4)

    report = decision.run_voice_local_tts_human_score_decision(
        private_audio_dir=audio_dir,
        private_score_input_path=score_input_path,
        doc_path=tmp_path / "VOICE_LOCAL_TTS_HUMAN_SCORE_DECISION.md",
        report_path=tmp_path / "voice_local_tts_human_score_decision_report.md",
        result_rows_path=tmp_path / "voice_local_tts_human_score_decision_rows.jsonl",
    )

    assert decision.collect_decision_failures(report) == []
    assert decision.collect_decision_blockers(report) == []
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
    assert report.summary.criterion_below_accept_threshold_count == 0
    assert report.summary.provider_decision == "candidate_accepted_for_demo_review"
    assert all(row.score_count == 5 for row in report.aggregates)
    assert all(row.score_avg == 4.0 for row in report.aggregates)


def test_human_score_decision_rejects_low_scores(tmp_path: Path) -> None:
    audio_dir = tmp_path / "audio"
    score_input_path = tmp_path / "scores.jsonl"
    _write_fixture_audio_files(audio_dir)
    _write_completed_private_scores(score_input_path, score=2)

    report = decision.run_voice_local_tts_human_score_decision(
        private_audio_dir=audio_dir,
        private_score_input_path=score_input_path,
        doc_path=tmp_path / "VOICE_LOCAL_TTS_HUMAN_SCORE_DECISION.md",
        report_path=tmp_path / "voice_local_tts_human_score_decision_report.md",
        result_rows_path=tmp_path / "voice_local_tts_human_score_decision_rows.jsonl",
    )

    assert decision.collect_decision_failures(report) == []
    assert decision.collect_decision_blockers(report) == [
        "human_score_quality_below_reject_threshold",
    ]
    assert report.summary.completed_score_row_count == 30
    assert report.summary.overall_score_avg == 2.0
    assert report.summary.criterion_below_reject_threshold_count == 6
    assert report.summary.provider_decision == "candidate_rejected_by_human_scores"


def test_human_score_decision_docs_record_current_blocked_state() -> None:
    assert DOC_PATH.exists()
    assert REPORT_PATH.exists()

    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert decision.WORK_ID in doc
    assert decision.WORK_ID in report
    assert "private_audio_available_count | 5" in report
    assert "private_score_input_available_count | 0" in report
    assert "completed_score_row_count | 0" in report
    assert "pending_score_row_count | 30" in report
    assert "aggregate_public_row_count | 6" in report
    assert "provider_decision_public_row_count | 1" in report
    assert "external_provider_call_count | 0" in report
    assert "external_audio_transmission_count | 0" in report
    assert "human_score_public_detail_row_count | 0" in report
    assert "provider_decision | `blocked_missing_human_scores`" in report
    assert "tts_human_score_decision_blockers=[" in report
    assert "External audit | PASS" in report
    assert "최종 provider 확정으로 보지 않는다" in doc


def test_human_score_decision_registered_and_public_safe() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    todo = TODO_PATH.read_text(encoding="utf-8")
    ledger = LEDGER_PATH.read_text(encoding="utf-8")

    for link in REQUIRED_LINKS:
        assert link in readme
        assert Path(link).exists()

    assert "- [x] optional human TTS listening score provider decision gate" in todo
    assert "- [ ] optional human TTS listening score manual scoring" in todo
    assert decision.WORK_ID in ledger
    assert "voice_local_tts_human_score_decision" in ledger

    for path in PUBLIC_SCAN_PATHS:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"private_data[/\\]", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)


def test_human_score_decision_keeps_forbidden_claims_forbidden() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    forbidden_section = doc.split("## Claim Boundary", maxsplit=1)[1]

    for claim in FORBIDDEN_CLAIMS:
        assert claim in forbidden_section
