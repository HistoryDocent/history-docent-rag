from __future__ import annotations

import re
from pathlib import Path


DOC_PATH = Path("docs/PORTFOLIO_DEMO_RUNBOOK.md")
REPORT_PATH = Path("evals/reports/portfolio_demo_runbook_report.md")
REFRESH_REPORT_PATH = Path("evals/reports/portfolio_demo_runbook_refresh_report.md")


def test_portfolio_demo_runbook_docs_are_sanitized() -> None:
    for path in (
        DOC_PATH,
        REPORT_PATH,
        REFRESH_REPORT_PATH,
        Path("README.md"),
        Path("docs/RAG_DECISION_LEDGER.md"),
        Path("docs/SUBMISSION_READY_CHECKLIST.md"),
        Path("docs/TODO.md"),
    ):
        text = path.read_text(encoding="utf-8")

        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)
        assert "private_data/" not in text


def test_portfolio_demo_runbook_records_required_demo_commands() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")

    assert "pytest -q" in doc
    assert "ruff check ." in doc
    assert (
        "pytest tests/test_portfolio_demo_runbook.py tests/test_voice_demo_playback_smoke.py tests/test_voice_api_local_runtime_route_smoke.py -q"
        in doc
    )
    assert "npm run check" in doc
    assert "npm audit --audit-level=high" in doc
    assert "python -m uvicorn app.main:app --host 127.0.0.1 --port 8000" in doc
    assert "python -m pipelines.voice_api_local_runtime_route_smoke" in doc
    assert 'VITE_HISTORY_DOCENT_CHAT_MODE="fixture"' in doc
    assert 'VITE_HISTORY_DOCENT_CHAT_MODE="backend"' in doc
    assert "npm run smoke:contract" in doc
    assert "retrieval_mode = \"contract_only\"" in doc
    assert "provider_mode = \"contract_only\"" in doc


def test_portfolio_demo_runbook_records_claim_boundary() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")

    forbidden_claims = [
        "production 성능 검증 완료",
        "locked test에서 최종 성능 개선 입증",
        "GraphRAG로 성능 개선",
        "RAPTOR로 성능 개선",
        "HyDE로 최종 검색 성능 개선",
        "Solar Pro 3 답변 품질 최종 개선",
        "음성 관광 앱 완성",
        "STT/TTS production 품질 검증 완료",
        "STT/TTS provider 최종 확정",
        "실제 관광객 음성 품질 검증 완료",
        "microphone capture 구현 완료",
        "speaker playback 구현 완료",
        "전체 도서 데이터 공개",
    ]
    for claim in forbidden_claims:
        assert claim in doc

    allowed_claims = [
        "local voice playback smoke에서 private wav 5개가 playback-ready임을 확인했다",
        "local voice API route smoke에서 기본 비활성화와 explicit local flag contract를 확인했다",
        "external provider call과 external audio transmission은 0으로 유지했다",
    ]
    for claim in allowed_claims:
        assert claim in doc

    assert "API key 불필요" in doc
    assert "private corpus 없이" in doc
    assert "live Solar Pro 3 호출은 0" in doc
    assert "local voice route는 기본 비활성화 상태다" in doc
    assert "explicit local flag에서만 contract-only 응답을 확인했다" in doc


def test_portfolio_demo_runbook_report_records_gates() -> None:
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert "demo_runbook_document_count | 1" in report
    assert "demo_step_count | 7" in report
    assert "runbook_command_block_count | 9" in report
    assert "required_artifact_link_count | 7" in report
    assert "forbidden_claim_count | 13" in report
    assert "voice_playback_smoke_artifact_count | 2" in report
    assert "voice_route_smoke_artifact_count | 2" in report
    assert "default_disabled_voice_route_count | 1" in report
    assert "explicit_flag_voice_route_contract_count | 1" in report
    assert "live_solar_call_count | 0" in report
    assert "retrieval_execution_count | 0" in report
    assert "external_provider_call_count | 0" in report
    assert "raw_audio_public_artifact_count | 0" in report
    assert "production_voice_app_claim_count | 0" in report
    assert "private_corpus_required_count | 0" in report
    assert "External audit | PASS" in report
    assert "fact_portfolio_demo_runbook" in report
