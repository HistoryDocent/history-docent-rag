from __future__ import annotations

import re
from pathlib import Path


DOC_PATH = Path("docs/VOICE_STT_TTS_MANAGED_PROVIDER_SMOKE_APPROVAL.md")
REPORT_PATH = Path(
    "evals/reports/voice_stt_tts_managed_provider_smoke_approval_report.md"
)
README_PATH = Path("README.md")
TODO_PATH = Path("docs/TODO.md")
LEDGER_PATH = Path("docs/RAG_DECISION_LEDGER.md")
CHECKLIST_PATH = Path("docs/CHECKLIST.md")
WBS_PATH = Path("docs/WBS.md")
ROADMAP_PATH = Path("docs/ROADMAP.md")
WORK_ID = "HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-APPROVAL-001"
NEXT_WORK_ID = "HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-001"
REQUIRED_LINKS = (
    "docs/VOICE_STT_TTS_MANAGED_PROVIDER_SMOKE_APPROVAL.md",
    "evals/reports/voice_stt_tts_managed_provider_smoke_approval_report.md",
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
    "provider 최종 선택 완료",
    "STT/TTS 품질 검증 완료",
    "음성 관광 앱 완성",
    "managed provider benchmark 성능 개선 입증",
    "production voice service 준비 완료",
)


def test_managed_provider_smoke_approval_docs_exist_and_record_zero_call_gate() -> None:
    assert DOC_PATH.exists()
    assert REPORT_PATH.exists()

    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert WORK_ID in doc
    assert WORK_ID in report
    assert NEXT_WORK_ID in doc
    assert NEXT_WORK_ID in report
    assert "managed_provider_execution_approved | false" in report
    assert "managed_provider_api_call_count | 0" in report
    assert "external_audio_transmission_count | 0" in report
    assert "live_stt_call_count | 0" in report
    assert "live_tts_call_count | 0" in report
    assert "live_solar_call_count | 0" in report
    assert "raw_audio_public_artifact_count | 0" in report
    assert "raw_transcript_public_artifact_count | 0" in report
    assert "raw_payload_public_artifact_count | 0" in report
    assert "client_secret_exposure_count | 0" in report


def test_managed_provider_smoke_approval_records_comparison_plan_and_sources() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert "planned_provider_count | 3" in report
    assert "planned_max_stt_calls_per_provider | 3" in report
    assert "planned_max_tts_calls_per_provider | 3" in report
    assert "official_source_count | 9" in report
    assert doc.count("https://") >= 9
    assert "`managed_google_cloud_speech_to_text`" in doc
    assert "`managed_azure_ai_speech`" in doc
    assert "`managed_aws_transcribe_polly`" in doc
    assert "`local_cuda_whisper_small`" in doc
    assert "WER, CER, place_name_accuracy" in doc
    assert "voice_round_trip_latency_p95_ms" in doc
    assert "fact_voice_managed_provider_public_summary" in doc


def test_managed_provider_smoke_approval_is_registered_and_public_safe() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    todo = TODO_PATH.read_text(encoding="utf-8")
    ledger = LEDGER_PATH.read_text(encoding="utf-8")

    for link in REQUIRED_LINKS:
        assert link in readme
        assert Path(link).exists()

    assert "- [x] optional voice STT/TTS managed provider smoke approval" in todo
    assert "- [ ] optional voice STT/TTS managed provider smoke execution" in todo
    assert WORK_ID in ledger
    assert NEXT_WORK_ID in ledger
    assert "managed_provider_execution_approved=false" in ledger
    assert "managed_provider_api_call_count=0" in ledger
    assert "external_audio_transmission_count=0" in ledger

    for path in PUBLIC_SCAN_PATHS:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)
        assert "private_data/" not in text


def test_managed_provider_smoke_approval_keeps_forbidden_claims_forbidden() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    forbidden_section = doc.split("## Claim Boundary", maxsplit=1)[1]

    for claim in FORBIDDEN_CLAIMS:
        assert claim in forbidden_section
