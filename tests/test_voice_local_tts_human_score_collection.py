from __future__ import annotations

import json
import re
from pathlib import Path

import pipelines.voice_local_tts_human_score_collection as collection


DOC_PATH = Path("docs/VOICE_LOCAL_TTS_HUMAN_SCORE_COLLECTION.md")
REPORT_PATH = Path("evals/reports/voice_local_tts_human_score_collection_report.md")
README_PATH = Path("README.md")
TODO_PATH = Path("docs/TODO.md")
LEDGER_PATH = Path("docs/RAG_DECISION_LEDGER.md")
CHECKLIST_PATH = Path("docs/CHECKLIST.md")
WBS_PATH = Path("docs/WBS.md")
ROADMAP_PATH = Path("docs/ROADMAP.md")
VOICE_DECISION_PATH = Path("docs/VOICE_PROVIDER_DECISION.md")
REQUIRED_LINKS = (
    "docs/VOICE_LOCAL_TTS_HUMAN_SCORE_COLLECTION.md",
    "evals/reports/voice_local_tts_human_score_collection_report.md",
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
            for criterion in collection.RUBRIC:
                output.write(
                    json.dumps(
                        {
                            "provider_candidate_id": collection.PROVIDER_CANDIDATE_ID,
                            "script_id": script_id,
                            "audio_file_name": f"{script_id}.wav",
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


def test_human_score_collection_runner_ready_public_safe_contract(tmp_path: Path) -> None:
    audio_dir = tmp_path / "audio"
    _write_fixture_audio_files(audio_dir)

    report = collection.run_voice_local_tts_human_score_collection(
        private_audio_dir=audio_dir,
        private_listening_manifest_path=tmp_path / "collection_manifest.jsonl",
        private_listening_guide_path=tmp_path / "collection_guide.md",
        private_score_template_path=tmp_path / "scores.template.jsonl",
        private_score_input_path=tmp_path / "missing_scores.jsonl",
        doc_path=tmp_path / "VOICE_LOCAL_TTS_HUMAN_SCORE_COLLECTION.md",
        report_path=tmp_path / "voice_local_tts_human_score_collection_report.md",
        result_rows_path=tmp_path / "voice_local_tts_human_score_collection_rows.jsonl",
    )

    assert collection.collect_collection_failures(report) == []
    assert report.summary.selected_script_count == 5
    assert report.summary.rubric_criterion_count == 6
    assert report.summary.expected_private_score_row_count == 30
    assert report.summary.private_audio_expected_count == 5
    assert report.summary.private_audio_available_count == 5
    assert report.summary.private_audio_missing_count == 0
    assert report.summary.private_listening_manifest_created_count == 1
    assert report.summary.private_listening_manifest_row_count == 5
    assert report.summary.private_listening_guide_created_count == 1
    assert report.summary.private_score_template_created_count == 1
    assert report.summary.private_score_template_row_count == 30
    assert report.summary.private_score_input_available_count == 0
    assert report.summary.completed_score_row_count == 0
    assert report.summary.pending_score_row_count == 30
    assert report.summary.aggregate_public_row_count == 6
    assert report.summary.human_score_public_detail_row_count == 0
    assert report.summary.external_provider_call_count == 0
    assert report.summary.external_audio_transmission_count == 0
    assert report.summary.raw_audio_public_artifact_count == 0
    assert report.summary.raw_transcript_public_artifact_count == 0
    assert report.summary.raw_script_public_artifact_count == 0
    assert report.summary.public_private_path_leakage_count == 0
    assert report.summary.public_secret_like_leakage_count == 0
    assert report.summary.public_raw_payload_leakage_count == 0
    assert report.summary.score_collection_decision == "ready_for_private_human_collection"

    manifest_rows = [
        json.loads(line)
        for line in (tmp_path / "collection_manifest.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(manifest_rows) == 5
    assert all(row["audio_available"] is True for row in manifest_rows)
    assert all(row["public_allowed"] is False for row in manifest_rows)
    assert all("script_text" in row for row in manifest_rows)

    guide = (tmp_path / "collection_guide.md").read_text(encoding="utf-8")
    assert "Voice Local TTS Human Score Collection Guide" in guide
    assert "경복궁은 조선의 중심 궁궐" in guide

    public_rows = [
        json.loads(line)
        for line in (tmp_path / "voice_local_tts_human_score_collection_rows.jsonl")
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


def test_human_score_collection_runner_aggregates_completed_private_scores(
    tmp_path: Path,
) -> None:
    audio_dir = tmp_path / "audio"
    score_input_path = tmp_path / "scores.jsonl"
    _write_fixture_audio_files(audio_dir)
    _write_completed_private_scores(score_input_path)

    report = collection.run_voice_local_tts_human_score_collection(
        private_audio_dir=audio_dir,
        private_listening_manifest_path=tmp_path / "collection_manifest.jsonl",
        private_listening_guide_path=tmp_path / "collection_guide.md",
        private_score_template_path=tmp_path / "scores.template.jsonl",
        private_score_input_path=score_input_path,
        doc_path=tmp_path / "VOICE_LOCAL_TTS_HUMAN_SCORE_COLLECTION.md",
        report_path=tmp_path / "voice_local_tts_human_score_collection_report.md",
        result_rows_path=tmp_path / "voice_local_tts_human_score_collection_rows.jsonl",
    )

    assert collection.collect_collection_failures(report) == []
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
        report.summary.score_collection_decision
        == "human_scores_collected_pending_provider_decision"
    )
    assert all(row.score_count == 5 for row in report.aggregates)
    assert all(row.score_avg == 4.0 for row in report.aggregates)


def test_human_score_collection_docs_record_ready_state() -> None:
    assert DOC_PATH.exists()
    assert REPORT_PATH.exists()

    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert collection.WORK_ID in doc
    assert collection.WORK_ID in report
    assert "private_audio_expected_count | 5" in report
    assert "private_audio_available_count | 5" in report
    assert "private_audio_missing_count | 0" in report
    assert "private_listening_manifest_created_count | 1" in report
    assert "private_listening_manifest_row_count | 5" in report
    assert "private_listening_guide_created_count | 1" in report
    assert "private_score_template_row_count | 30" in report
    assert "completed_score_row_count | 0" in report
    assert "pending_score_row_count | 30" in report
    assert "aggregate_public_row_count | 6" in report
    assert "external_provider_call_count | 0" in report
    assert "raw_audio_public_artifact_count | 0" in report
    assert "raw_transcript_public_artifact_count | 0" in report
    assert "raw_script_public_artifact_count | 0" in report
    assert "human_score_public_detail_row_count | 0" in report
    assert "public_private_path_leakage_count | 0" in report
    assert "score_collection_decision | `ready_for_private_human_collection`" in report
    assert "External audit | PASS" in report
    assert "품질 검증 완료로 보지 않는다" in doc


def test_human_score_collection_registered_and_public_safe() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    todo = TODO_PATH.read_text(encoding="utf-8")
    ledger = LEDGER_PATH.read_text(encoding="utf-8")

    for link in REQUIRED_LINKS:
        assert link in readme
        assert Path(link).exists()

    assert "- [x] optional human TTS listening score collection workflow" in todo
    assert "- [x] optional human TTS listening score entry tool" in todo
    assert "- [ ] optional human TTS listening score entry completion" in todo
    assert collection.WORK_ID in ledger
    assert "voice_local_tts_human_score_collection" in ledger

    for path in PUBLIC_SCAN_PATHS:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"private_data[/\\]", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)


def test_human_score_collection_keeps_forbidden_claims_forbidden() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    forbidden_section = doc.split("## Claim Boundary", maxsplit=1)[1]

    for claim in FORBIDDEN_CLAIMS:
        assert claim in forbidden_section
