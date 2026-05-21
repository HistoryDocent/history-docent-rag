from __future__ import annotations

import json
import re
from pathlib import Path

import pipelines.voice_local_runtime_stack_alignment as alignment

from app.application.voice_local_adapter import (
    LOCAL_STT_PROVIDER_CANDIDATE_ID,
    LOCAL_TTS_FINAL_PROVIDER,
    LOCAL_TTS_PROVIDER_STATUS,
)


DOC_PATH = Path("docs/VOICE_LOCAL_RUNTIME_STACK_ALIGNMENT.md")
REPORT_PATH = Path("evals/reports/voice_local_runtime_stack_alignment_report.md")
README_PATH = Path("README.md")
TODO_PATH = Path("docs/TODO.md")
LEDGER_PATH = Path("docs/RAG_DECISION_LEDGER.md")
CHECKLIST_PATH = Path("docs/CHECKLIST.md")
WBS_PATH = Path("docs/WBS.md")
ROADMAP_PATH = Path("docs/ROADMAP.md")
VOICE_DECISION_PATH = Path("docs/VOICE_PROVIDER_DECISION.md")
REQUIRED_LINKS = (
    "docs/VOICE_LOCAL_RUNTIME_STACK_ALIGNMENT.md",
    "evals/reports/voice_local_runtime_stack_alignment_report.md",
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
    "실제 관광객 음성 품질 검증 완료",
    "production 음성 관광 앱 완성",
)


def test_runtime_stack_alignment_runner_public_safe_contract(tmp_path: Path) -> None:
    report = alignment.run_voice_local_runtime_stack_alignment(
        doc_path=tmp_path / "VOICE_LOCAL_RUNTIME_STACK_ALIGNMENT.md",
        report_path=tmp_path / "voice_local_runtime_stack_alignment_report.md",
        result_rows_path=tmp_path / "voice_local_runtime_stack_alignment_rows.jsonl",
    )

    assert alignment.collect_runtime_stack_alignment_failures(report) == []
    assert report.summary.actual_runtime_stt_provider_id == "local_faster_whisper_small_cuda"
    assert report.summary.provider_id_mismatch_count == 0
    assert report.summary.primary_local_stt_candidate_count == 1
    assert report.summary.primary_local_tts_candidate_count == 0
    assert report.summary.tts_fallback_candidate_count == 1
    assert report.summary.tts_final_provider_count == 0
    assert report.summary.runtime_default_faster_whisper_transcriber_count == 1
    assert report.summary.api_provider_status_field_count == 5
    assert report.summary.external_provider_call_count == 0
    assert report.summary.external_audio_transmission_count == 0
    assert report.summary.alignment_decision == "aligned_local_stt_tts_blocked"

    public_rows = [
        json.loads(line)
        for line in (tmp_path / "voice_local_runtime_stack_alignment_rows.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(public_rows) == 3
    assert all("raw_audio" not in row for row in public_rows)
    assert all("raw_transcript" not in row for row in public_rows)
    assert all("input_audio_path" not in row for row in public_rows)


def test_runtime_stack_alignment_constants_match_stack_lock() -> None:
    assert LOCAL_STT_PROVIDER_CANDIDATE_ID == alignment.PRIMARY_STT_CANDIDATE_ID
    assert LOCAL_TTS_FINAL_PROVIDER is False
    assert LOCAL_TTS_PROVIDER_STATUS == "fallback_not_quality_candidate"


def test_runtime_stack_alignment_docs_registered_and_public_safe() -> None:
    assert DOC_PATH.exists()
    assert REPORT_PATH.exists()

    readme = README_PATH.read_text(encoding="utf-8")
    todo = TODO_PATH.read_text(encoding="utf-8")
    ledger = LEDGER_PATH.read_text(encoding="utf-8")

    for link in REQUIRED_LINKS:
        assert link in readme
        assert Path(link).exists()

    assert "- [x] optional local voice runtime stack alignment" in todo
    assert alignment.WORK_ID in ledger
    assert "voice_local_runtime_stack_alignment" in ledger

    for path in PUBLIC_SCAN_PATHS:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"private_data[/\\]", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)


def test_runtime_stack_alignment_report_records_quantitative_gates() -> None:
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert alignment.WORK_ID in report
    assert "actual_runtime_stt_provider_id | `local_faster_whisper_small_cuda`" in report
    assert "provider_id_mismatch_count | 0" in report
    assert "primary_local_stt_candidate_count | 1" in report
    assert "primary_local_tts_candidate_count | 0" in report
    assert "tts_provider_status | `fallback_not_quality_candidate`" in report
    assert "tts_final_provider_count | 0" in report
    assert "runtime_default_faster_whisper_transcriber_count | 1" in report
    assert "api_provider_status_field_count | 5" in report
    assert "external_provider_call_count | 0" in report
    assert "external_audio_transmission_count | 0" in report
    assert "alignment_decision | `aligned_local_stt_tts_blocked`" in report
    assert "External audit | PASS" in report


def test_runtime_stack_alignment_keeps_forbidden_claims_forbidden() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    forbidden_section = doc.split("금지 claim:", maxsplit=1)[1]

    for claim in FORBIDDEN_CLAIMS:
        assert claim in forbidden_section
