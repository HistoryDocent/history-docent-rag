from __future__ import annotations

import re
from pathlib import Path


DOC_PATH = Path("docs/SUBMISSION_REFRESH_AUDIT_V2.md")
REPORT_PATH = Path("evals/reports/submission_refresh_audit_v2_report.md")
README_PATH = Path("README.md")

REQUIRED_README_LINKS = (
    "docs/SUBMISSION_REFRESH_AUDIT_V2.md",
    "evals/reports/submission_refresh_audit_v2_report.md",
    "docs/PORTFOLIO_DEMO_RUNBOOK.md",
    "evals/reports/portfolio_demo_runbook_refresh_report.md",
)

REQUIRED_ARTIFACTS = (
    Path("README.md"),
    Path("docs/PORTFOLIO_DEMO_RUNBOOK.md"),
    Path("evals/reports/portfolio_demo_runbook_report.md"),
    Path("evals/reports/portfolio_demo_runbook_refresh_report.md"),
    Path("docs/VOICE_DEMO_PLAYBACK_SMOKE.md"),
    Path("evals/reports/voice_demo_playback_smoke_report.md"),
    Path("docs/VOICE_API_LOCAL_RUNTIME_ROUTE_SMOKE.md"),
    Path("evals/reports/voice_api_local_runtime_route_smoke_report.md"),
    Path("docs/RAG_DECISION_LEDGER.md"),
    Path("evals/reports/assets/voice_ui_visual_qa_desktop_answerable.jpg"),
    Path("evals/reports/assets/voice_ui_visual_qa_mobile_no_answer.jpg"),
    Path("evals/reports/assets/voice_ui_visual_qa_desktop_error.jpg"),
)

PUBLIC_SCAN_PATHS = (
    README_PATH,
    DOC_PATH,
    REPORT_PATH,
    Path("docs/PORTFOLIO_DEMO_RUNBOOK.md"),
    Path("evals/reports/portfolio_demo_runbook_refresh_report.md"),
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


def test_submission_refresh_audit_v2_docs_exist_and_are_sanitized() -> None:
    assert DOC_PATH.exists()
    assert REPORT_PATH.exists()

    for path in PUBLIC_SCAN_PATHS:
        text = path.read_text(encoding="utf-8")

        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)
        assert "private_data/" not in text


def test_submission_refresh_audit_v2_readme_links_and_artifacts_exist() -> None:
    readme = README_PATH.read_text(encoding="utf-8")

    for link in REQUIRED_README_LINKS:
        assert link in readme
        assert Path(link).exists()

    for artifact in REQUIRED_ARTIFACTS:
        assert artifact.exists()
        assert artifact.stat().st_size > 0


def test_submission_refresh_audit_v2_records_required_commands() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")

    required_commands = (
        "pytest -q",
        "ruff check .",
        "git diff --check",
        "tests/test_submission_refresh_audit_v2.py",
        "npm run check",
        "npm audit --audit-level=high",
        "rg -n",
        "_collect_public_candidate_path_secret_leaks",
        "git status -sb",
    )
    for command in required_commands:
        assert command in doc


def test_submission_refresh_audit_v2_keeps_forbidden_claims_as_forbidden() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    forbidden_section = doc.split("## 금지 Claim", maxsplit=1)[1]

    for claim in FORBIDDEN_CLAIMS:
        assert claim in forbidden_section


def test_submission_refresh_audit_v2_report_records_gates() -> None:
    report = REPORT_PATH.read_text(encoding="utf-8")

    expected_metrics = (
        "submission_refresh_audit_v2_document_count | 1",
        "submission_refresh_audit_v2_report_count | 1",
        "regression_test_file_count | 1",
        "required_readme_link_count | 4",
        "required_demo_artifact_count | 12",
        "required_voice_artifact_count | 4",
        "required_screenshot_artifact_count | 3",
        "forbidden_claim_count | 13",
        "verification_command_count | 9",
        "markdown_link_missing_count | 0",
        "demo_artifact_missing_count | 0",
        "screenshot_artifact_missing_count | 0",
        "public_private_path_leakage_count | 0",
        "public_secret_like_leakage_count | 0",
        "public_env_assignment_leakage_count | 0",
        "public_raw_payload_leakage_count | 0",
        "public_raw_audio_transcript_leakage_count | 0",
        "live_solar_call_count | 0",
        "retrieval_execution_count | 0",
        "external_provider_call_count | 0",
        "external_audio_transmission_count | 0",
        "private_corpus_required_count | 0",
        "production_voice_app_claim_count | 0",
    )
    for metric in expected_metrics:
        assert metric in report

    assert "External audit | PASS" in report
    assert "fact_submission_refresh_gate_v2" in report
