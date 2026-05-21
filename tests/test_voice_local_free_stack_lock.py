from __future__ import annotations

import json
import re
from pathlib import Path

import pipelines.voice_local_free_stack_lock as stack_lock


DOC_PATH = Path("docs/VOICE_LOCAL_FREE_STACK_LOCK.md")
REPORT_PATH = Path("evals/reports/voice_local_free_stack_lock_report.md")
README_PATH = Path("README.md")
TODO_PATH = Path("docs/TODO.md")
LEDGER_PATH = Path("docs/RAG_DECISION_LEDGER.md")
CHECKLIST_PATH = Path("docs/CHECKLIST.md")
WBS_PATH = Path("docs/WBS.md")
ROADMAP_PATH = Path("docs/ROADMAP.md")
VOICE_DECISION_PATH = Path("docs/VOICE_PROVIDER_DECISION.md")
REQUIRED_LINKS = (
    "docs/VOICE_LOCAL_FREE_STACK_LOCK.md",
    "evals/reports/voice_local_free_stack_lock_report.md",
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
    "자동 proxy가 사람 평가를 대체한다",
    "실제 관광객 음성 품질 검증 완료",
    "production 음성 관광 앱 완성",
)


def test_local_free_stack_lock_runner_public_safe_contract(tmp_path: Path) -> None:
    report = stack_lock.run_voice_local_free_stack_lock(
        doc_path=tmp_path / "VOICE_LOCAL_FREE_STACK_LOCK.md",
        report_path=tmp_path / "voice_local_free_stack_lock_report.md",
        result_rows_path=tmp_path / "voice_local_free_stack_lock_rows.jsonl",
    )

    assert stack_lock.collect_stack_lock_failures(report) == []
    assert stack_lock.collect_stack_lock_blockers(report) == [
        "missing_human_tts_scores",
        "tts_proxy_threshold_not_fully_passed",
    ]
    assert report.summary.provider_candidate_count == 8
    assert report.summary.primary_local_stt_candidate_count == 1
    assert report.summary.primary_local_tts_candidate_count == 0
    assert report.summary.experimental_local_tts_candidate_count == 1
    assert report.summary.fallback_local_tts_candidate_count == 1
    assert report.summary.blocked_local_tts_candidate_count == 2
    assert report.summary.optional_paid_provider_candidate_count == 3
    assert report.summary.managed_provider_default_count == 0
    assert report.summary.default_external_audio_transmission_count == 0
    assert report.summary.secret_required_for_default_voice_count == 0
    assert report.summary.local_stt_locked_count == 1
    assert report.summary.local_tts_final_provider_claim_count == 0
    assert report.summary.tts_automated_proxy_execution_count == 5
    assert report.summary.tts_automated_proxy_pass_count == 4
    assert report.summary.tts_automated_proxy_fail_count == 1
    assert report.summary.tts_human_listening_completed_count == 0
    assert report.summary.external_provider_call_count == 0
    assert report.summary.external_audio_transmission_count == 0
    assert report.summary.stack_decision == "locked_local_stt_tts_blocked"

    public_rows = [
        json.loads(line)
        for line in (tmp_path / "voice_local_free_stack_lock_rows.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(public_rows) == 9
    assert public_rows[0]["row_type"] == "voice_local_free_stack_lock_summary"
    assert public_rows[0]["primary_local_stt_candidate_id"] == (
        stack_lock.PRIMARY_STT_CANDIDATE_ID
    )
    assert public_rows[0]["primary_local_tts_candidate_count"] == 0
    assert all("raw_audio" not in row for row in public_rows)
    assert all("raw_transcript" not in row for row in public_rows)
    assert all("script_text" not in row for row in public_rows)
    assert all("audio_path" not in row for row in public_rows)


def test_local_free_stack_lock_docs_record_current_decision() -> None:
    assert DOC_PATH.exists()
    assert REPORT_PATH.exists()

    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert stack_lock.WORK_ID in doc
    assert stack_lock.WORK_ID in report
    assert "primary_local_stt_candidate_count | 1" in report
    assert "primary_local_tts_candidate_count | 0" in report
    assert "experimental_local_tts_candidate_count | 1" in report
    assert "fallback_local_tts_candidate_count | 1" in report
    assert "optional_paid_provider_candidate_count | 3" in report
    assert "managed_provider_default_count | 0" in report
    assert "default_external_audio_transmission_count | 0" in report
    assert "secret_required_for_default_voice_count | 0" in report
    assert "local_tts_final_provider_claim_count | 0" in report
    assert "tts_automated_proxy_pass_count | 4" in report
    assert "tts_automated_proxy_fail_count | 1" in report
    assert "tts_human_listening_completed_count | 0" in report
    assert "external_provider_call_count | 0" in report
    assert "external_audio_transmission_count | 0" in report
    assert "stack_decision | `locked_local_stt_tts_blocked`" in report
    assert "External audit | PASS" in report
    assert "TTS는 final provider가 아니다" in report
    assert "TTS 최종 provider는 아직 채택하지 않는 것" in doc


def test_local_free_stack_lock_registered_and_public_safe() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    todo = TODO_PATH.read_text(encoding="utf-8")
    ledger = LEDGER_PATH.read_text(encoding="utf-8")

    for link in REQUIRED_LINKS:
        assert link in readme
        assert Path(link).exists()

    assert "- [x] optional local free voice stack lock" in todo
    assert stack_lock.WORK_ID in ledger
    assert "voice_local_free_stack_lock" in ledger

    for path in PUBLIC_SCAN_PATHS:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"private_data[/\\]", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)


def test_local_free_stack_lock_keeps_forbidden_claims_forbidden() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    forbidden_section = doc.split("금지 claim:", maxsplit=1)[1]

    for claim in FORBIDDEN_CLAIMS:
        assert claim in forbidden_section
