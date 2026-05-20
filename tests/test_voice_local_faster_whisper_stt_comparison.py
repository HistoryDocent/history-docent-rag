from __future__ import annotations

import json
import re
from pathlib import Path

from pipelines.voice_local_faster_whisper_stt_comparison import (
    WORK_ID,
    collect_faster_whisper_comparison_failures,
    run_voice_local_faster_whisper_stt_comparison,
)


DOC_PATH = Path("docs/VOICE_LOCAL_FASTER_WHISPER_STT_COMPARISON.md")
REPORT_PATH = Path("evals/reports/voice_local_faster_whisper_stt_comparison_report.md")
README_PATH = Path("README.md")
TODO_PATH = Path("docs/TODO.md")
LEDGER_PATH = Path("docs/RAG_DECISION_LEDGER.md")
CHECKLIST_PATH = Path("docs/CHECKLIST.md")
WBS_PATH = Path("docs/WBS.md")
ROADMAP_PATH = Path("docs/ROADMAP.md")
VOICE_DECISION_PATH = Path("docs/VOICE_PROVIDER_DECISION.md")
REQUIRED_LINKS = (
    "docs/VOICE_LOCAL_FASTER_WHISPER_STT_COMPARISON.md",
    "evals/reports/voice_local_faster_whisper_stt_comparison_report.md",
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
    "`faster-whisper`가 production 최종 provider라는 주장",
    "STT/TTS 품질 최종 검증 완료",
    "실제 관광객 음성 품질 검증 완료",
    "음성 관광 앱 완성",
)


def test_faster_whisper_stt_comparison_runner_public_safe_contract(tmp_path: Path) -> None:
    report = run_voice_local_faster_whisper_stt_comparison(
        doc_path=tmp_path / "VOICE_LOCAL_FASTER_WHISPER_STT_COMPARISON.md",
        report_path=tmp_path / "voice_local_faster_whisper_stt_comparison_report.md",
        result_rows_path=tmp_path / "voice_local_faster_whisper_stt_comparison_rows.jsonl",
        execute_faster_whisper=False,
        require_faster_execution=False,
    )

    assert collect_faster_whisper_comparison_failures(report, require_faster_execution=False) == []
    assert report.summary.selected_script_count == 5
    assert report.summary.baseline_execution_count == 5
    assert report.summary.faster_whisper_execution_count == 0
    assert report.summary.external_provider_call_count == 0
    assert report.summary.external_audio_transmission_count == 0
    assert report.summary.live_stt_call_count == 0
    assert report.summary.live_tts_call_count == 0
    assert report.summary.live_solar_call_count == 0
    assert report.summary.raw_audio_public_artifact_count == 0
    assert report.summary.raw_transcript_public_artifact_count == 0

    rows = [
        json.loads(line)
        for line in (tmp_path / "voice_local_faster_whisper_stt_comparison_rows.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(rows) == 10
    assert all("script_text" not in row for row in rows)
    assert all("raw_transcript" not in row for row in rows)
    assert all("raw_audio" not in row for row in rows)
    assert all("audio_path" not in row for row in rows)


def test_faster_whisper_stt_comparison_docs_record_execution_result() -> None:
    assert DOC_PATH.exists()
    assert REPORT_PATH.exists()

    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert WORK_ID in doc
    assert WORK_ID in report
    assert "selected_script_count | 5" in report
    assert "baseline_execution_count | 5" in report
    assert "faster_whisper_runtime_available_count | 1" in report
    assert "external_provider_call_count | 0" in report
    assert "external_audio_transmission_count | 0" in report
    assert "live_stt_call_count | 0" in report
    assert "live_tts_call_count | 0" in report
    assert "live_solar_call_count | 0" in report
    assert "raw_audio_public_artifact_count | 0" in report
    assert "raw_transcript_public_artifact_count | 0" in report
    assert "public_private_path_leakage_count | 0" in report
    assert "public_secret_like_leakage_count | 0" in report
    assert "public_raw_payload_leakage_count | 0" in report
    assert "comparison_decision | `completed_faster_whisper_comparison`" in report
    assert "External audit | PASS" in report


def test_faster_whisper_stt_comparison_registered_and_public_safe() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    todo = TODO_PATH.read_text(encoding="utf-8")
    ledger = LEDGER_PATH.read_text(encoding="utf-8")

    for link in REQUIRED_LINKS:
        assert link in readme
        assert Path(link).exists()

    assert "- [x] local faster-whisper STT comparison" in todo
    assert WORK_ID in ledger

    for path in PUBLIC_SCAN_PATHS:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)


def test_faster_whisper_stt_comparison_keeps_forbidden_claims_forbidden() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    forbidden_section = doc.split("금지 claim:", maxsplit=1)[1]

    for claim in FORBIDDEN_CLAIMS:
        assert claim in forbidden_section
