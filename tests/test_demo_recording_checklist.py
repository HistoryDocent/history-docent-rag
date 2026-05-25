from __future__ import annotations

import re
from pathlib import Path


DOC_PATH = Path("docs/DEMO_RECORDING_CHECKLIST.md")
REPORT_PATH = Path("evals/reports/demo_recording_checklist_report.md")
README_PATH = Path("README.md")

REQUIRED_README_LINKS = (
    "docs/DEMO_RECORDING_CHECKLIST.md",
    "evals/reports/demo_recording_checklist_report.md",
)

REQUIRED_ARTIFACTS = (
    Path("README.md"),
    Path("docs/PORTFOLIO_WALKTHROUGH_SCRIPT.md"),
    Path("docs/PORTFOLIO_FINAL_PACKAGE_INDEX.md"),
    Path("docs/FINAL_ABLATION_REPORT.md"),
    Path("docs/API_RESPONSE_SAMPLE.md"),
    Path("docs/PORTFOLIO_DEMO_RUNBOOK.md"),
    Path("docs/VOICE_API_LOCAL_RUNTIME_ROUTE_SMOKE.md"),
    Path("docs/SUBMISSION_REFRESH_AUDIT_V2.md"),
)

PUBLIC_SCAN_PATHS = (
    README_PATH,
    DOC_PATH,
    REPORT_PATH,
    Path("docs/PORTFOLIO_WALKTHROUGH_SCRIPT.md"),
    Path("evals/reports/portfolio_walkthrough_script_report.md"),
    Path("docs/RAG_DECISION_LEDGER.md"),
    Path("docs/TODO.md"),
    Path("docs/WBS.md"),
    Path("docs/ROADMAP.md"),
    Path("docs/CHECKLIST.md"),
    Path("docs/VOICE_DEMO_STACK_DECISION.md"),
)

FORBIDDEN_CLAIMS = (
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
)


def test_demo_recording_checklist_docs_exist_and_are_sanitized() -> None:
    assert DOC_PATH.exists()
    assert REPORT_PATH.exists()

    for path in PUBLIC_SCAN_PATHS:
        text = path.read_text(encoding="utf-8")

        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)
        assert "private_data/" not in text


def test_demo_recording_checklist_readme_links_and_artifacts_exist() -> None:
    readme = README_PATH.read_text(encoding="utf-8")

    for link in REQUIRED_README_LINKS:
        assert link in readme
        assert Path(link).exists()

    for artifact in REQUIRED_ARTIFACTS:
        assert artifact.exists()
        assert artifact.stat().st_size > 0


def test_demo_recording_checklist_records_preflight_flow() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")

    required_phrases = (
        "HD-DEMO-RECORDING-CHECKLIST-001",
        "## 녹화 전 화면 순서",
        "## 녹화 전 터미널 Checklist",
        "README.md",
        "docs/PORTFOLIO_WALKTHROUGH_SCRIPT.md",
        "docs/PORTFOLIO_FINAL_PACKAGE_INDEX.md",
        "docs/FINAL_ABLATION_REPORT.md",
        "docs/API_RESPONSE_SAMPLE.md",
        "docs/PORTFOLIO_DEMO_RUNBOOK.md",
        "docs/VOICE_API_LOCAL_RUNTIME_ROUTE_SMOKE.md",
        "docs/SUBMISSION_REFRESH_AUDIT_V2.md",
        "pytest tests/test_demo_recording_checklist.py -q",
        "git status --short",
        "HD-GITHUB-PUSH-READINESS-001",
    )
    for phrase in required_phrases:
        assert phrase in doc


def test_demo_recording_checklist_keeps_forbidden_claims_as_forbidden() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")
    doc_forbidden_section = doc.split("## 말하면 안 되는 문장", maxsplit=1)[1]
    report_forbidden_section = report.split("## 금지:", maxsplit=1)[1]

    for claim in FORBIDDEN_CLAIMS:
        assert claim in doc_forbidden_section
        assert claim in report_forbidden_section


def test_demo_recording_checklist_report_records_gates() -> None:
    report = REPORT_PATH.read_text(encoding="utf-8")

    expected_metrics = (
        "demo_recording_checklist_document_count | 1",
        "demo_recording_checklist_report_count | 1",
        "regression_test_file_count | 1",
        "recording_screen_sequence_count | 8",
        "terminal_preflight_check_count | 8",
        "allowed_claim_count | 5",
        "forbidden_claim_count | 13",
        "recording_artifact_created_count | 0",
        "live_solar_call_count | 0",
        "retrieval_execution_count | 0",
        "external_provider_call_count | 0",
        "external_audio_transmission_count | 0",
        "public_private_path_leakage_count | 0",
        "public_secret_like_leakage_count | 0",
        "public_env_assignment_leakage_count | 0",
        "public_raw_payload_leakage_count | 0",
        "public_raw_audio_transcript_leakage_count | 0",
        "production_success_claim_count | 0",
        "production_voice_app_claim_count | 0",
    )
    for metric in expected_metrics:
        assert metric in report

    assert "External audit | PASS" in report
    assert "fact_demo_recording_preflight" in report
