from __future__ import annotations

import re
from pathlib import Path


DOC_PATH = Path("docs/VOICE_STT_TTS_AZURE_SMOKE_EXECUTION_APPROVAL.md")
REPORT_PATH = Path(
    "evals/reports/voice_stt_tts_azure_smoke_execution_approval_report.md"
)
README_PATH = Path("README.md")
TODO_PATH = Path("docs/TODO.md")
LEDGER_PATH = Path("docs/RAG_DECISION_LEDGER.md")
CHECKLIST_PATH = Path("docs/CHECKLIST.md")
WBS_PATH = Path("docs/WBS.md")
ROADMAP_PATH = Path("docs/ROADMAP.md")
WORK_ID = "HD-VOICE-STT-TTS-AZURE-SMOKE-EXECUTION-APPROVAL-001"
NEXT_WORK_ID = "HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-001"
REQUIRED_LINKS = (
    "docs/VOICE_STT_TTS_AZURE_SMOKE_EXECUTION_APPROVAL.md",
    "evals/reports/voice_stt_tts_azure_smoke_execution_approval_report.md",
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
REQUIRED_FACT_TABLES = (
    "fact_voice_azure_smoke_execution_approval",
    "fact_voice_azure_smoke_source_recheck",
    "fact_voice_azure_smoke_private_stt_eval",
    "fact_voice_azure_smoke_private_tts_eval",
    "fact_voice_azure_smoke_public_summary",
)
FORBIDDEN_CLAIMS = (
    "Azure STT/TTS 품질 검증 완료",
    "Azure managed provider smoke 실행 완료",
    "Azure provider 최종 선택 완료",
    "production voice service 준비 완료",
    "외부 audio 전송 검증 완료",
)


def test_azure_smoke_execution_approval_docs_exist_and_defer_execution() -> None:
    assert DOC_PATH.exists()
    assert REPORT_PATH.exists()

    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert WORK_ID in doc
    assert WORK_ID in report
    assert NEXT_WORK_ID in doc
    assert NEXT_WORK_ID in report
    assert "`azure_credential_ready` | `false`" in doc
    assert "`azure_smoke_execution_approved` | `false`" in doc
    assert "azure_credential_ready | false" in report
    assert "azure_smoke_execution_approved | false" in report
    assert "approval_decision | `blocked_missing_azure_credentials`" in report
    assert "managed_provider_api_call_count | 0" in report
    assert "external_audio_transmission_count | 0" in report
    assert "live_stt_call_count | 0" in report
    assert "live_tts_call_count | 0" in report
    assert "live_solar_call_count | 0" in report


def test_azure_smoke_execution_approval_sets_call_and_source_gates() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert "provider_candidate_count | 1" in report
    assert "first_provider_candidate_is_azure | true" in report
    assert "planned_script_count | 3" in report
    assert "planned_stt_call_count | 3" in report
    assert "planned_tts_call_count | 3" in report
    assert "call_cap_enforced | true" in report
    assert "source_recheck_required_before_execution_count | 5" in report
    assert "source_recheck_completed_for_execution_count | 0" in report
    assert "region_recheck_required_count | 1" in report
    assert "retention_recheck_required_count | 1" in report
    assert "cost_confirmation_required_count | 1" in report
    assert "credential_value_public_exposure_count | 0" in report
    assert "raw_audio_public_artifact_count | 0" in report
    assert "raw_transcript_public_artifact_count | 0" in report
    assert "raw_payload_public_artifact_count | 0" in report

    for metric in (
        "wer",
        "cer",
        "place_name_accuracy",
        "stt_latency_p95_ms",
        "tts_latency_p95_ms",
        "estimated_stt_cost",
        "estimated_tts_cost",
    ):
        assert metric in doc
        assert metric in report


def test_azure_smoke_execution_approval_documents_grain_and_stop_conditions() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    for fact_table in REQUIRED_FACT_TABLES:
        assert fact_table in doc
        assert fact_table in report

    assert "AZURE_SPEECH_KEY" in doc
    assert "AZURE_SPEECH_REGION" in doc
    assert "사용자 별도 실행 승인이 없는 경우" in doc
    assert "HD-VOICE-STT-TTS-AZURE-SMOKE-EXECUTION-001" in doc


def test_azure_smoke_execution_approval_is_registered_and_public_safe() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    todo = TODO_PATH.read_text(encoding="utf-8")
    ledger = LEDGER_PATH.read_text(encoding="utf-8")

    for link in REQUIRED_LINKS:
        assert link in readme
        assert Path(link).exists()

    assert "- [x] optional voice STT/TTS Azure smoke execution approval" in todo
    assert "- [ ] optional voice STT/TTS managed provider smoke execution" in todo
    assert WORK_ID in ledger
    assert NEXT_WORK_ID in ledger
    assert "azure_credential_ready=false" in ledger
    assert "azure_smoke_execution_approved=false" in ledger
    assert "managed_provider_api_call_count=0" in ledger
    assert "external_audio_transmission_count=0" in ledger

    for path in PUBLIC_SCAN_PATHS:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)
        assert "private_data/" not in text


def test_azure_smoke_execution_approval_keeps_forbidden_claims_forbidden() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    forbidden_section = doc.split("금지 claim:", maxsplit=1)[1]

    for claim in FORBIDDEN_CLAIMS:
        assert claim in forbidden_section
