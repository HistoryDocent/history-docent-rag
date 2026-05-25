from __future__ import annotations

import re
from pathlib import Path


DOC_PATH = Path("docs/PORTFOLIO_FINAL_PACKAGE_INDEX.md")
REPORT_PATH = Path("evals/reports/portfolio_final_package_index_report.md")
README_PATH = Path("README.md")

REQUIRED_README_LINKS = (
    "docs/PORTFOLIO_FINAL_PACKAGE_INDEX.md",
    "evals/reports/portfolio_final_package_index_report.md",
)

REQUIRED_ARTIFACTS = (
    Path("README.md"),
    Path("docs/FINAL_ABLATION_REPORT.md"),
    Path("docs/API_RESPONSE_SAMPLE.md"),
    Path("docs/PORTFOLIO_DEMO_RUNBOOK.md"),
    Path("docs/VOICE_DEMO_STACK_DECISION.md"),
    Path("docs/VOICE_DEMO_PLAYBACK_SMOKE.md"),
    Path("docs/VOICE_API_LOCAL_RUNTIME_ROUTE_SMOKE.md"),
    Path("docs/SUBMISSION_REFRESH_AUDIT_V2.md"),
    Path("evals/reports/final_ablation_report.md"),
    Path("evals/reports/portfolio_demo_runbook_refresh_report.md"),
    Path("evals/reports/submission_refresh_audit_v2_report.md"),
)

PUBLIC_SCAN_PATHS = (
    DOC_PATH,
    REPORT_PATH,
    README_PATH,
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


def test_portfolio_final_package_index_docs_exist_and_are_sanitized() -> None:
    assert DOC_PATH.exists()
    assert REPORT_PATH.exists()

    for path in PUBLIC_SCAN_PATHS:
        text = path.read_text(encoding="utf-8")

        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)
        assert "private_data/" not in text


def test_portfolio_final_package_index_readme_links_and_artifacts_exist() -> None:
    readme = README_PATH.read_text(encoding="utf-8")

    for link in REQUIRED_README_LINKS:
        assert link in readme
        assert Path(link).exists()

    for artifact in REQUIRED_ARTIFACTS:
        assert artifact.exists()
        assert artifact.stat().st_size > 0


def test_portfolio_final_package_index_records_submission_flow() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")

    required_phrases = (
        "HD-PORTFOLIO-FINAL-PACKAGE-INDEX-001",
        "제출자가 먼저 열 문서",
        "최종 제출 evidence map",
        "면접에서 말할 순서",
        "README.md",
        "docs/FINAL_ABLATION_REPORT.md",
        "docs/API_RESPONSE_SAMPLE.md",
        "docs/PORTFOLIO_DEMO_RUNBOOK.md",
        "docs/VOICE_DEMO_STACK_DECISION.md",
        "docs/VOICE_DEMO_PLAYBACK_SMOKE.md",
        "docs/VOICE_API_LOCAL_RUNTIME_ROUTE_SMOKE.md",
        "docs/SUBMISSION_REFRESH_AUDIT_V2.md",
    )
    for phrase in required_phrases:
        assert phrase in doc


def test_portfolio_final_package_index_records_required_commands() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")

    required_commands = (
        "pytest -q",
        "ruff check .",
        "git diff --check",
        "npm run check",
        "npm audit --audit-level=high",
        "tests/test_portfolio_final_package_index.py",
        "rg -n",
    )
    for command in required_commands:
        assert command in doc


def test_portfolio_final_package_index_keeps_forbidden_claims_as_forbidden() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")
    doc_forbidden_section = doc.split("## 금지 Claim", maxsplit=1)[1]
    report_forbidden_section = report.split("금지:", maxsplit=1)[1]

    for claim in FORBIDDEN_CLAIMS:
        assert claim in doc_forbidden_section
        assert claim in report_forbidden_section


def test_portfolio_final_package_index_report_records_gates() -> None:
    report = REPORT_PATH.read_text(encoding="utf-8")

    expected_metrics = (
        "final_package_index_document_count | 1",
        "final_package_index_report_count | 1",
        "regression_test_file_count | 1",
        "first_open_artifact_count | 8",
        "evidence_family_count | 6",
        "primary_doc_link_count | 13",
        "primary_report_link_count | 11",
        "interview_step_count | 8",
        "verification_command_count | 7",
        "forbidden_claim_count | 13",
        "required_readme_link_count | 2",
        "required_artifact_missing_count | 0",
        "public_private_path_leakage_count | 0",
        "public_secret_like_leakage_count | 0",
        "public_raw_payload_leakage_count | 0",
        "public_raw_audio_transcript_leakage_count | 0",
        "production_success_claim_count | 0",
        "production_voice_app_claim_count | 0",
    )
    for metric in expected_metrics:
        assert metric in report

    assert "External audit | PASS" in report
    assert "fact_portfolio_final_package_index" in report
