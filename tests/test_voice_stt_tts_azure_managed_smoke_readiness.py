from __future__ import annotations

import re
from pathlib import Path


DOC_PATH = Path("docs/VOICE_STT_TTS_AZURE_MANAGED_SMOKE_READINESS.md")
REPORT_PATH = Path(
    "evals/reports/voice_stt_tts_azure_managed_smoke_readiness_report.md"
)
ENV_EXAMPLE_PATH = Path(".env.example")
README_PATH = Path("README.md")
TODO_PATH = Path("docs/TODO.md")
LEDGER_PATH = Path("docs/RAG_DECISION_LEDGER.md")
CHECKLIST_PATH = Path("docs/CHECKLIST.md")
WBS_PATH = Path("docs/WBS.md")
ROADMAP_PATH = Path("docs/ROADMAP.md")
REQUIRED_LINKS = (
    "docs/VOICE_STT_TTS_AZURE_MANAGED_SMOKE_READINESS.md",
    "evals/reports/voice_stt_tts_azure_managed_smoke_readiness_report.md",
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
)
FORBIDDEN_CLAIMS = (
    "Azure STT/TTS 품질 검증 완료",
    "managed provider benchmark 완료",
    "Azure 비용/정책 최신 확인 완료",
    "production voice service 준비 완료",
    "외부 audio 전송 검증 완료",
)


def test_azure_managed_smoke_readiness_artifacts_exist_and_record_zero_call() -> None:
    assert DOC_PATH.exists()
    assert REPORT_PATH.exists()

    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert "HD-VOICE-STT-TTS-AZURE-MANAGED-SMOKE-READINESS-001" in doc
    assert "HD-VOICE-STT-TTS-AZURE-MANAGED-SMOKE-READINESS-001" in report
    assert "first_managed_provider_candidate | `managed_azure_ai_speech`" in report
    assert "planned_script_count | 3" in report
    assert "planned_stt_call_count | 3" in report
    assert "planned_tts_call_count | 3" in report
    assert "managed_provider_api_call_count | 0" in report
    assert "external_audio_transmission_count | 0" in report
    assert "live_stt_call_count | 0" in report
    assert "live_tts_call_count | 0" in report
    assert "live_solar_call_count | 0" in report
    assert "credential_value_public_exposure_count | 0" in report
    assert "raw_audio_public_artifact_count | 0" in report
    assert "raw_transcript_public_artifact_count | 0" in report
    assert "raw_payload_public_artifact_count | 0" in report
    assert "External Audit" in report


def test_env_example_documents_azure_key_names_without_values() -> None:
    text = ENV_EXAMPLE_PATH.read_text(encoding="utf-8")

    assert "AZURE_SPEECH_KEY=" in text
    assert "AZURE_SPEECH_REGION=" in text
    assert not re.search(r"AZURE_SPEECH_KEY=.+", text)
    assert not re.search(r"AZURE_SPEECH_REGION=.+", text)


def test_azure_managed_smoke_readiness_is_registered_and_public_safe() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    todo = TODO_PATH.read_text(encoding="utf-8")
    ledger = LEDGER_PATH.read_text(encoding="utf-8")

    for link in REQUIRED_LINKS:
        assert link in readme
        assert Path(link).exists()

    assert "- [x] optional voice STT/TTS Azure managed smoke readiness" in todo
    assert "- [ ] optional voice STT/TTS managed provider smoke execution" in todo
    assert "HD-VOICE-STT-TTS-AZURE-MANAGED-SMOKE-READINESS-001" in ledger
    assert "first_managed_provider_candidate=managed_azure_ai_speech" in ledger
    assert "managed_provider_api_call_count=0" in ledger
    assert "external_audio_transmission_count=0" in ledger

    for path in PUBLIC_SCAN_PATHS:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)
        assert "private_data/" not in text


def test_azure_managed_smoke_readiness_keeps_forbidden_claims_forbidden() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    forbidden_section = doc.split("금지 claim:", maxsplit=1)[1]

    for claim in FORBIDDEN_CLAIMS:
        assert claim in forbidden_section
