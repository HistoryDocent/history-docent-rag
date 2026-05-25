from __future__ import annotations

import re
from pathlib import Path


DOC_PATH = Path("docs/VOICE_DEMO_STACK_DECISION.md")
REPORT_PATH = Path("evals/reports/voice_demo_stack_decision_report.md")
README_PATH = Path("README.md")
LEDGER_PATH = Path("docs/RAG_DECISION_LEDGER.md")
TODO_PATH = Path("docs/TODO.md")
WBS_PATH = Path("docs/WBS.md")
ROADMAP_PATH = Path("docs/ROADMAP.md")
CHECKLIST_PATH = Path("docs/CHECKLIST.md")
PROVIDER_DECISION_PATH = Path("docs/VOICE_PROVIDER_DECISION.md")
PROVIDER_REPORT_PATH = Path("evals/reports/voice_provider_decision_report.md")

WORK_ID = "HD-VOICE-DEMO-STACK-DECISION-001"
DOC_LINK = "docs/VOICE_DEMO_STACK_DECISION.md"
REPORT_LINK = "evals/reports/voice_demo_stack_decision_report.md"


def test_voice_demo_stack_decision_docs_record_current_state() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert WORK_ID in doc
    assert WORK_ID in report
    assert "local_faster_whisper_small_cuda" in doc
    assert "local_sherpa_onnx_supertonic3_ko" in doc
    assert "tts_demo_candidate_count | 1" in report
    assert "tts_final_provider_count | 0" in report
    assert "tts_human_score_completed_count | 30" in report
    assert "tts_human_score_overall_avg | 5.000000" in report
    assert "human_score_public_detail_row_count | 0" in report
    assert "external_provider_call_count | 0" in report
    assert "external_audio_transmission_count | 0" in report
    assert "production_voice_claim_count | 0" in report
    assert "voice_demo_stack_decision_failures=[]" in report


def test_voice_demo_stack_decision_registered_in_public_docs() -> None:
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
    assert "optional local voice demo stack decision" in todo
    assert "사람 청취 점수 30/30 평균 5.0" in readme
    assert "사람 청취 30/30 평균 5.0" in roadmap


def test_voice_demo_stack_decision_updates_provider_summary_without_overclaim() -> None:
    provider_doc = PROVIDER_DECISION_PATH.read_text(encoding="utf-8")
    provider_report = PROVIDER_REPORT_PATH.read_text(encoding="utf-8")
    readme = README_PATH.read_text(encoding="utf-8")

    assert "tts_demo_candidate_count" in provider_doc
    assert "`tts_demo_candidate_count` | 1" in provider_report
    assert "`tts_human_score_completed_count` | 30" in provider_doc
    assert "`tts_human_score_overall_avg` | 5.000000" in provider_doc
    assert "사람 청취 점수 0/30" not in readme
    assert "production final provider" in readme
    assert "최종 provider 확정이나 production 품질 보증으로 보지는 않는다" in provider_doc


def test_voice_demo_stack_decision_public_artifacts_are_sanitized() -> None:
    for path in (
        DOC_PATH,
        REPORT_PATH,
        README_PATH,
        LEDGER_PATH,
        TODO_PATH,
        WBS_PATH,
        ROADMAP_PATH,
        CHECKLIST_PATH,
        PROVIDER_DECISION_PATH,
        PROVIDER_REPORT_PATH,
    ):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"private_data[/\\]", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)


def test_voice_demo_stack_decision_keeps_forbidden_claims_forbidden() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    forbidden_section = doc.split("금지:", maxsplit=1)[1]

    forbidden_claims = [
        "무료 로컬 TTS 최종 provider 확정",
        "실제 관광객 음성 품질 검증 완료",
        "production 음성 관광 앱 완성",
        "Azure/Google/AWS보다 local TTS가 품질 우수하다는 주장",
    ]
    for claim in forbidden_claims:
        assert claim in forbidden_section
