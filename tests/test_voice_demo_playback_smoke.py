from __future__ import annotations

import re
from pathlib import Path

from pipelines.voice_demo_playback_smoke import (
    WORK_ID,
    run_voice_demo_playback_smoke,
)


DOC_PATH = Path("docs/VOICE_DEMO_PLAYBACK_SMOKE.md")
REPORT_PATH = Path("evals/reports/voice_demo_playback_smoke_report.md")
README_PATH = Path("README.md")
LEDGER_PATH = Path("docs/RAG_DECISION_LEDGER.md")
TODO_PATH = Path("docs/TODO.md")
WBS_PATH = Path("docs/WBS.md")
ROADMAP_PATH = Path("docs/ROADMAP.md")
CHECKLIST_PATH = Path("docs/CHECKLIST.md")

DOC_LINK = "docs/VOICE_DEMO_PLAYBACK_SMOKE.md"
REPORT_LINK = "evals/reports/voice_demo_playback_smoke_report.md"


def test_voice_demo_playback_smoke_runner_writes_public_safe_outputs(tmp_path: Path) -> None:
    report = run_voice_demo_playback_smoke(
        doc_path=tmp_path / "voice_demo_playback_smoke.md",
        report_path=tmp_path / "voice_demo_playback_smoke_report.md",
        result_rows_path=tmp_path / "voice_demo_playback_smoke_rows.jsonl",
    )

    assert report.work_id == WORK_ID
    assert report.summary.playback_smoke_decision == "completed_local_voice_demo_playback_smoke"
    assert report.summary.selected_script_count == 5
    assert report.summary.private_audio_available_count == 5
    assert report.summary.accepted_private_wav_count == 5
    assert report.summary.playback_ready_count == 5
    assert report.summary.playback_device_call_count == 0
    assert report.summary.external_provider_call_count == 0
    assert report.summary.external_audio_transmission_count == 0
    assert report.summary.raw_audio_public_artifact_count == 0
    assert report.summary.raw_transcript_public_artifact_count == 0
    assert report.summary.human_score_public_detail_row_count == 0
    assert report.summary.tts_human_score_completed_count == 30
    assert report.summary.tts_human_score_overall_avg == 5.0


def test_voice_demo_playback_smoke_docs_record_current_state() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert WORK_ID in doc
    assert WORK_ID in report
    assert "completed_local_voice_demo_playback_smoke" in report
    assert "local_faster_whisper_small_cuda" in doc
    assert "local_sherpa_onnx_supertonic3_ko" in doc
    assert "private_audio_available_count | 5" in report
    assert "playback_ready_count | 5" in report
    assert "playback_device_call_count | 0" in report
    assert "tts_final_provider_count | 0" in report
    assert "tts_human_score_completed_count | 30" in report
    assert "tts_human_score_overall_avg | 5.000000" in report
    assert "human_score_public_detail_row_count | 0" in report
    assert "external_provider_call_count | 0" in report
    assert "external_audio_transmission_count | 0" in report
    assert "voice_demo_playback_smoke_failures=[]" in report


def test_voice_demo_playback_smoke_registered_in_public_docs() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    ledger = LEDGER_PATH.read_text(encoding="utf-8")
    todo = TODO_PATH.read_text(encoding="utf-8")
    wbs = WBS_PATH.read_text(encoding="utf-8")
    roadmap = ROADMAP_PATH.read_text(encoding="utf-8")
    checklist = CHECKLIST_PATH.read_text(encoding="utf-8")

    assert DOC_LINK in readme
    assert REPORT_LINK in readme
    assert WORK_ID in readme
    assert WORK_ID in ledger
    assert WORK_ID in wbs
    assert WORK_ID in checklist
    assert "optional local voice demo playback smoke" in todo
    assert "playback-ready" in roadmap


def test_voice_demo_playback_smoke_public_artifacts_are_sanitized() -> None:
    for path in (
        DOC_PATH,
        REPORT_PATH,
        README_PATH,
        LEDGER_PATH,
        TODO_PATH,
        WBS_PATH,
        ROADMAP_PATH,
        CHECKLIST_PATH,
    ):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"private_data[/\\]", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)


def test_voice_demo_playback_smoke_keeps_forbidden_claims_forbidden() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    forbidden_section = doc.split("Claim Boundary", maxsplit=1)[1]

    forbidden_claims = [
        "무료 로컬 TTS 최종 provider 확정",
        "실제 관광객 음성 품질 검증 완료",
        "production 음성 관광 앱 완성",
        "speaker device 자동 재생 검증 완료",
        "managed provider보다 local TTS가 품질 우수하다는 주장",
    ]
    for claim in forbidden_claims:
        assert f"| forbidden | {claim} |" in forbidden_section
