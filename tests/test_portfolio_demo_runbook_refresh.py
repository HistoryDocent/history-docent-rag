from __future__ import annotations

import re
from pathlib import Path


DOC_PATH = Path("docs/PORTFOLIO_DEMO_RUNBOOK.md")
REPORT_PATH = Path("evals/reports/portfolio_demo_runbook_refresh_report.md")


PUBLIC_PATHS = (
    DOC_PATH,
    REPORT_PATH,
    Path("README.md"),
    Path("docs/RAG_DECISION_LEDGER.md"),
    Path("docs/TODO.md"),
    Path("docs/WBS.md"),
    Path("docs/ROADMAP.md"),
    Path("docs/CHECKLIST.md"),
    Path("docs/VOICE_DEMO_STACK_DECISION.md"),
)


def test_portfolio_demo_runbook_refresh_public_artifacts_are_sanitized() -> None:
    for path in PUBLIC_PATHS:
        text = path.read_text(encoding="utf-8")

        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)
        assert "private_data/" not in text


def test_portfolio_demo_runbook_refresh_links_latest_voice_evidence() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")

    required = [
        "HD-VOICE-DEMO-RUNBOOK-REFRESH-001",
        "docs/VOICE_DEMO_STACK_DECISION.md",
        "docs/VOICE_DEMO_PLAYBACK_SMOKE.md",
        "docs/VOICE_API_LOCAL_RUNTIME_ROUTE_SMOKE.md",
        "evals/reports/voice_api_local_runtime_route_smoke_report.md",
        "python -m pipelines.voice_api_local_runtime_route_smoke",
        "local voice route는 기본 비활성화 상태다",
        "explicit local flag에서만 contract-only 응답을 확인했다",
    ]
    for phrase in required:
        assert phrase in doc


def test_portfolio_demo_runbook_refresh_report_records_gates() -> None:
    report = REPORT_PATH.read_text(encoding="utf-8")

    expected_metrics = [
        "refreshed_runbook_document_count | 1",
        "refresh_report_count | 1",
        "regression_test_file_count | 1",
        "demo_step_count | 7",
        "voice_playback_smoke_artifact_count | 2",
        "voice_route_smoke_artifact_count | 2",
        "default_disabled_voice_route_count | 1",
        "explicit_flag_voice_route_contract_count | 1",
        "external_provider_call_count | 0",
        "external_audio_transmission_count | 0",
        "raw_audio_public_artifact_count | 0",
        "raw_transcript_public_artifact_count | 0",
        "production_voice_app_claim_count | 0",
        "forbidden_claim_count | 13",
    ]
    for metric in expected_metrics:
        assert metric in report

    assert "External audit | PASS" in report
    assert "fact_portfolio_demo_runbook_refresh" in report


def test_portfolio_demo_runbook_refresh_keeps_forbidden_claims_in_boundary() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    forbidden_claims = [
        "production 음성 관광 앱 완성",
        "STT/TTS production 품질 검증 완료",
        "STT/TTS provider 최종 확정",
        "실제 관광객 음성 품질 검증 완료",
        "microphone capture 구현 완료",
        "speaker playback 구현 완료",
    ]
    for claim in forbidden_claims:
        assert claim in doc or claim in report

    assert "## 금지 Claim" in doc
    assert "금지:" in report
