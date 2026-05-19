from __future__ import annotations

import re
from pathlib import Path


DOC_PATH = Path("docs/VOICE_STT_TTS_CONTRACT.md")
REPORT_PATH = Path("evals/reports/voice_stt_tts_contract_report.md")
README_PATH = Path("README.md")
TODO_PATH = Path("docs/TODO.md")
LEDGER_PATH = Path("docs/RAG_DECISION_LEDGER.md")
ADAPTER_PATH = Path("frontend/src/lib/voiceAdapters.ts")
ADAPTER_TEST_PATH = Path("frontend/src/lib/voiceAdapters.test.ts")
APP_TEST_PATH = Path("frontend/src/App.test.tsx")
REQUIRED_LINKS = (
    "docs/VOICE_STT_TTS_CONTRACT.md",
    "evals/reports/voice_stt_tts_contract_report.md",
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


def test_voice_stt_tts_contract_docs_exist_and_are_sanitized() -> None:
    assert DOC_PATH.exists()
    assert REPORT_PATH.exists()
    assert ADAPTER_PATH.exists()
    assert ADAPTER_TEST_PATH.exists()

    for path in PUBLIC_SCAN_PATHS:
        text = path.read_text(encoding="utf-8")

        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)
        assert "private_data/" not in text


def test_voice_stt_tts_contract_readme_todo_and_ledger_are_registered() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    todo = TODO_PATH.read_text(encoding="utf-8")
    ledger = LEDGER_PATH.read_text(encoding="utf-8")

    for link in REQUIRED_LINKS:
        assert link in readme
        assert Path(link).exists()

    assert "- [x] optional voice STT/TTS contract skeleton" in todo
    assert "- [x] optional voice STT/TTS provider benchmark plan" in todo
    assert "- [x] optional voice STT/TTS provider benchmark readiness" in todo
    assert "- [x] optional voice STT/TTS provider benchmark execution approval" in todo
    assert "- [x] optional voice STT/TTS provider benchmark smoke execution" in todo
    assert "- [ ] optional voice STT/TTS managed provider smoke approval" in todo
    assert "HD-VOICE-STT-TTS-PROVIDER-BENCH-READINESS-001" in ledger
    assert "HD-VOICE-STT-TTS-PROVIDER-BENCH-SMOKE-LOCAL-001" in ledger


def test_voice_adapter_contract_blocks_provider_calls() -> None:
    adapter = ADAPTER_PATH.read_text(encoding="utf-8")
    app_test = APP_TEST_PATH.read_text(encoding="utf-8")

    assert "mode: VoiceAdapterMode" in adapter
    assert "disabled_by_contract" in adapter
    assert "liveSttCallCount: 0" in adapter
    assert "liveTtsCallCount: 0" in adapter
    assert "providerFinalizedCount: 0" in adapter
    assert "privateAudioSavedCount: 0" in adapter
    assert "rawTranscriptPublicArtifactCount: 0" in adapter
    assert "speechSynthesis.speak" not in adapter
    assert "new SpeechSynthesisUtterance" not in adapter
    assert "음성 입력 contract only" in app_test
    assert "voice calls: 0/0" in app_test


def test_voice_stt_tts_contract_keeps_forbidden_claims_as_forbidden() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    forbidden_section = doc.split("## 금지 Claim", maxsplit=1)[1]

    for claim in FORBIDDEN_CLAIMS:
        assert claim in forbidden_section


def test_voice_stt_tts_contract_report_records_gates() -> None:
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert "voice_stt_tts_contract_document_count | 1" in report
    assert "voice_stt_tts_contract_report_count | 1" in report
    assert "frontend_adapter_module_count | 1" in report
    assert "frontend_adapter_unit_test_count | 2" in report
    assert "frontend_ui_voice_contract_test_count | 1" in report
    assert "frontend_total_voice_contract_test_count | 3" in report
    assert "provider_finalized_count | 0" in report
    assert "live_stt_call_count | 0" in report
    assert "live_tts_call_count | 0" in report
    assert "live_solar_call_count | 0" in report
    assert "private_audio_saved_count | 0" in report
    assert "raw_transcript_public_artifact_count | 0" in report
    assert "client_secret_exposure_count | 0" in report
    assert "mic_capture_implemented_count | 0" in report
    assert "browser_tts_playback_call_count | 0" in report
    assert "public_private_path_leakage_count | 0" in report
    assert "public_secret_like_leakage_count | 0" in report
    assert "public_raw_payload_leakage_count | 0" in report
    assert "External audit | PASS" in report
    assert "fact_voice_stt_tts_contract" in report
