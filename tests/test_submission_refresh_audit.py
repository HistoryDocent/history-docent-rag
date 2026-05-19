from __future__ import annotations

import re
from pathlib import Path


DOC_PATH = Path("docs/SUBMISSION_REFRESH_AUDIT.md")
REPORT_PATH = Path("evals/reports/submission_refresh_audit_report.md")
README_PATH = Path("README.md")
REQUIRED_LINKS = (
    "docs/SUBMISSION_REFRESH_AUDIT.md",
    "evals/reports/submission_refresh_audit_report.md",
)
REQUIRED_SCREENSHOTS = (
    Path("evals/reports/assets/voice_ui_visual_qa_desktop_answerable.jpg"),
    Path("evals/reports/assets/voice_ui_visual_qa_mobile_no_answer.jpg"),
    Path("evals/reports/assets/voice_ui_visual_qa_desktop_error.jpg"),
)
PUBLIC_SCAN_PATHS = (
    README_PATH,
    DOC_PATH,
    REPORT_PATH,
    Path("docs/PORTFOLIO_DEMO_RUNBOOK.md"),
    Path("docs/RAG_DECISION_LEDGER.md"),
    Path("docs/SUBMISSION_READY_CHECKLIST.md"),
)
FORBIDDEN_CLAIMS = (
    "production 성능 검증 완료",
    "locked test에서 최종 성능 개선 입증",
    "GraphRAG로 성능 개선",
    "RAPTOR로 성능 개선",
    "HyDE로 최종 검색 성능 개선",
    "Solar Pro 3 답변 품질 최종 개선",
    "음성 관광 앱 완성",
    "전체 도서 데이터 공개",
)


def test_submission_refresh_docs_exist_and_are_sanitized() -> None:
    assert DOC_PATH.exists()
    assert REPORT_PATH.exists()

    for path in PUBLIC_SCAN_PATHS:
        text = path.read_text(encoding="utf-8")

        assert "chunk text" in text
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)
        assert "private_data/" not in text


def test_submission_refresh_readme_links_and_artifacts_exist() -> None:
    readme = README_PATH.read_text(encoding="utf-8")

    for link in REQUIRED_LINKS:
        assert link in readme
        assert Path(link).exists()

    for screenshot in REQUIRED_SCREENSHOTS:
        assert screenshot.exists()
        assert screenshot.stat().st_size > 0


def test_submission_refresh_records_required_commands() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")

    required_commands = (
        "pytest -q",
        "ruff check .",
        "git diff --check",
        "npm run check",
        "npm audit --audit-level=high",
        "rg -n",
        "_collect_public_candidate_path_secret_leaks",
        "git status -sb",
    )
    for command in required_commands:
        assert command in doc


def test_submission_refresh_keeps_forbidden_claims_as_forbidden() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    forbidden_section = doc.split("## 금지 Claim", maxsplit=1)[1]

    for claim in FORBIDDEN_CLAIMS:
        assert claim in forbidden_section


def test_submission_refresh_report_records_quantitative_and_qualitative_gates() -> None:
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert "submission_refresh_audit_document_count | 1" in report
    assert "submission_refresh_report_count | 1" in report
    assert "required_readme_link_count | 2" in report
    assert "required_demo_artifact_count | 3" in report
    assert "forbidden_claim_count | 8" in report
    assert "verification_command_count | 8" in report
    assert "markdown_link_missing_count | 0" in report
    assert "screenshot_artifact_missing_count | 0" in report
    assert "public_private_path_leakage_count | 0" in report
    assert "public_secret_like_leakage_count | 0" in report
    assert "public_env_assignment_leakage_count | 0" in report
    assert "public_raw_payload_leakage_count | 0" in report
    assert "live_solar_call_count | 0" in report
    assert "retrieval_execution_count | 0" in report
    assert "private_corpus_required_count | 0" in report
    assert "External audit | PASS" in report
    assert "fact_submission_refresh_gate" in report
