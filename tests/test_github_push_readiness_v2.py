from __future__ import annotations

import re
from pathlib import Path


DOC_PATH = Path("docs/GITHUB_PUSH_READINESS_V2.md")
REPORT_PATH = Path("evals/reports/github_push_readiness_v2_report.md")
README_PATH = Path("README.md")

REQUIRED_README_LINKS = (
    "docs/GITHUB_PUSH_READINESS_V2.md",
    "evals/reports/github_push_readiness_v2_report.md",
)

PUBLIC_SCAN_PATHS = (
    README_PATH,
    DOC_PATH,
    REPORT_PATH,
    Path("docs/GITHUB_PUSH_EXECUTION_APPROVAL.md"),
    Path("docs/VOICE_LOCAL_WHISPERCPP_INSTALL_STRATEGY.md"),
    Path("docs/RAG_DECISION_LEDGER.md"),
    Path("docs/TODO.md"),
    Path("docs/WBS.md"),
    Path("docs/ROADMAP.md"),
    Path("docs/CHECKLIST.md"),
    Path("docs/VOICE_DEMO_STACK_DECISION.md"),
)

FORBIDDEN_CLAIMS = (
    "GitHub push 완료",
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


def test_github_push_readiness_v2_docs_exist_and_are_sanitized() -> None:
    assert DOC_PATH.exists()
    assert REPORT_PATH.exists()

    for path in PUBLIC_SCAN_PATHS:
        text = path.read_text(encoding="utf-8")

        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)


def test_github_push_readiness_v2_readme_links_exist() -> None:
    readme = README_PATH.read_text(encoding="utf-8")

    for link in REQUIRED_README_LINKS:
        assert link in readme
        assert Path(link).exists()


def test_github_push_readiness_v2_records_latest_push_preflight() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    required_phrases = (
        "HD-GITHUB-PUSH-READINESS-V2-001",
        "HD-VOICE-LOCAL-WHISPERCPP-INSTALL-STRATEGY-001",
        "HD-GITHUB-PUSH-EXECUTION-APPROVAL-001",
        "https://github.com/HistoryDocent/history-docent-rag.git",
        "d08dc7a",
        "e5ba9a6",
        "279819f",
        "d941682",
        "f77758c",
        "expected_remote_count | 1",
        "current_branch_main_count | 1",
        "worktree_clean_before_readiness_count | 1",
        "local_branch_ahead_origin_main_detected_count | 1",
        "recent_commit_checked_count | 5",
        "tracked_candidate_match_count | 4",
        "tracked_allowed_sample_example_count | 4",
        "tracked_non_example_env_file_count | 0",
        "tracked_forbidden_artifact_count | 0",
        "push_execution_count | 0",
        "external_state_change_count | 0",
        "next_explicit_push_gate_required_count | 1",
        "HD-GITHUB-PUSH-EXECUTION-001",
    )
    for phrase in required_phrases:
        assert phrase in doc or phrase in report

    assert "External audit | PASS" in report
    assert "fact_github_push_readiness_v2" in report


def test_github_push_readiness_v2_keeps_forbidden_claims_as_forbidden() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")
    doc_forbidden_section = doc.split("## 말하면 안 되는 문장", maxsplit=1)[1]
    report_forbidden_section = report.split("## 금지:", maxsplit=1)[1]

    for claim in FORBIDDEN_CLAIMS:
        assert claim in doc_forbidden_section
        assert claim in report_forbidden_section
