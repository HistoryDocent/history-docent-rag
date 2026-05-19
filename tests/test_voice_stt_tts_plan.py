from __future__ import annotations

import re
from pathlib import Path


DOC_PATH = Path("docs/VOICE_STT_TTS_PLAN.md")
REPORT_PATH = Path("evals/reports/voice_stt_tts_plan_report.md")
README_PATH = Path("README.md")
TODO_PATH = Path("docs/TODO.md")
LEDGER_PATH = Path("docs/RAG_DECISION_LEDGER.md")
REQUIRED_LINKS = (
    "docs/VOICE_STT_TTS_PLAN.md",
    "evals/reports/voice_stt_tts_plan_report.md",
)
PUBLIC_SCAN_PATHS = (
    README_PATH,
    DOC_PATH,
    REPORT_PATH,
    TODO_PATH,
    LEDGER_PATH,
    Path("docs/CHECKLIST.md"),
    Path("docs/WBS.md"),
    Path("docs/ROADMAP.md"),
)
FORBIDDEN_CLAIMS = (
    "production 성능 검증 완료",
    "locked test에서 최종 성능 개선 입증",
    "GraphRAG로 성능 개선",
    "RAPTOR로 성능 개선",
    "HyDE로 최종 검색 성능 개선",
    "Solar Pro 3 답변 품질 최종 개선",
    "음성 관광 앱 완성",
    "STT/TTS 품질 검증 완료",
    "전체 도서 데이터 공개",
)


def test_voice_stt_tts_plan_docs_exist_and_are_sanitized() -> None:
    assert DOC_PATH.exists()
    assert REPORT_PATH.exists()

    for path in PUBLIC_SCAN_PATHS:
        text = path.read_text(encoding="utf-8")

        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)
        assert "private_data/" not in text


def test_voice_stt_tts_plan_readme_and_todo_are_registered() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    todo = TODO_PATH.read_text(encoding="utf-8")
    ledger = LEDGER_PATH.read_text(encoding="utf-8")

    for link in REQUIRED_LINKS:
        assert link in readme
        assert Path(link).exists()

    assert "- [x] optional voice STT/TTS planning" in todo
    assert "- [x] optional voice STT/TTS contract skeleton" in todo
    assert "- [x] optional voice STT/TTS provider benchmark plan" in todo
    assert "- [x] optional voice STT/TTS provider benchmark readiness" in todo
    assert "- [x] optional voice STT/TTS provider benchmark execution approval" in todo
    assert "- [x] optional voice STT/TTS provider benchmark smoke execution" in todo
    assert "- [ ] optional voice STT/TTS managed provider smoke approval" in todo
    assert "HD-VOICE-STT-TTS-PROVIDER-BENCH-READINESS-001" in ledger
    assert "HD-VOICE-STT-TTS-PROVIDER-BENCH-SMOKE-LOCAL-001" in ledger


def test_voice_stt_tts_plan_records_scope_and_boundaries() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")

    assert "## 범위" in doc
    assert "## 목표 사용자 흐름" in doc
    assert "## Architecture Boundary" in doc
    assert "## Provider 선택 기준" in doc
    assert "## 개인정보와 보안 정책" in doc
    assert "## 평가 기준" in doc
    assert "## Failure Mode" in doc
    assert "HD-VOICE-STT-TTS-CONTRACT-001" in doc
    assert "provider는 아직 확정하지 않는다" in doc
    assert "`/api/v1/chat`는 음성 binary를 직접 받지 않는다" in doc
    assert "fact_voice_stt_tts_plan" in doc


def test_voice_stt_tts_plan_keeps_forbidden_claims_as_forbidden() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    forbidden_section = doc.split("## 금지 Claim", maxsplit=1)[1]

    for claim in FORBIDDEN_CLAIMS:
        assert claim in forbidden_section


def test_voice_stt_tts_plan_report_records_quantitative_gates() -> None:
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert "voice_stt_tts_plan_document_count | 1" in report
    assert "voice_stt_tts_plan_report_count | 1" in report
    assert "planned_voice_flow_count | 7" in report
    assert "provider_candidate_group_count | 3" in report
    assert "privacy_control_count | 9" in report
    assert "privacy_risk_count | 8" in report
    assert "failure_mode_count | 12" in report
    assert "eval_metric_count | 12" in report
    assert "provider_finalized_count | 0" in report
    assert "live_stt_call_count | 0" in report
    assert "live_tts_call_count | 0" in report
    assert "live_solar_call_count | 0" in report
    assert "private_audio_saved_count | 0" in report
    assert "retrieval_execution_count | 0" in report
    assert "public_private_path_leakage_count | 0" in report
    assert "public_secret_like_leakage_count | 0" in report
    assert "public_raw_payload_leakage_count | 0" in report
    assert "External audit | PASS" in report
    assert "fact_voice_stt_tts_plan" in report
