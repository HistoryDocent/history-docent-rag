from __future__ import annotations

import re
from pathlib import Path


README_PATH = Path("README.md")
DOC_PATH = Path("docs/README_LANDING_POLISH.md")
REPORT_PATH = Path("evals/reports/readme_landing_polish_report.md")

PUBLIC_SCAN_PATHS = (
    README_PATH,
    DOC_PATH,
    REPORT_PATH,
    Path("docs/PORTFOLIO_FINAL_PACKAGE_INDEX.md"),
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


def test_readme_landing_polish_docs_exist_and_are_sanitized() -> None:
    assert DOC_PATH.exists()
    assert REPORT_PATH.exists()

    for path in PUBLIC_SCAN_PATHS:
        text = path.read_text(encoding="utf-8")

        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)
        assert "private_data/" not in text


def test_readme_landing_polish_first_screen_sections() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    top = readme.split("## 상세 결과 요약", maxsplit=1)[0]

    required_phrases = (
        "## 60초 요약",
        "## 바로 볼 문서",
        "## 현재 공개 가능한 결론",
        "평가 기반 RAG 의사결정 구조",
        "production 음성 앱 아님",
        "docs/PORTFOLIO_FINAL_PACKAGE_INDEX.md",
        "docs/SUBMISSION_REFRESH_AUDIT_V2.md",
    )
    for phrase in required_phrases:
        assert phrase in top

    assert top.count("| ") >= 15
    assert "## 상세 결과 요약" in readme


def test_readme_landing_polish_preserves_detailed_metrics() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    detail = readme.split("## 상세 결과 요약", maxsplit=1)[1]

    required_phrases = (
        "chunking",
        "dense_multilingual_e5_small",
        "portfolio final package index",
        "voice API local runtime route smoke",
        "README landing polish",
        "top_summary_table_row_count / first_open_link_count",
        "docs/README_LANDING_POLISH.md",
        "evals/reports/readme_landing_polish_report.md",
    )
    for phrase in required_phrases:
        assert phrase in detail


def test_readme_landing_polish_keeps_forbidden_claims_as_forbidden() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")
    doc_forbidden_section = doc.split("## 금지 Claim", maxsplit=1)[1]
    report_forbidden_section = report.split("## 금지:", maxsplit=1)[1]

    for claim in FORBIDDEN_CLAIMS:
        assert claim in doc_forbidden_section
        assert claim in report_forbidden_section


def test_readme_landing_polish_report_records_gates() -> None:
    report = REPORT_PATH.read_text(encoding="utf-8")

    expected_metrics = (
        "readme_landing_polish_document_count | 1",
        "readme_landing_polish_report_count | 1",
        "regression_test_file_count | 1",
        "top_summary_table_row_count | 6",
        "first_open_link_count | 5",
        "detailed_metrics_preserved_count | 1",
        "forbidden_claim_count | 13",
        "required_readme_link_count | 2",
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
    assert "fact_readme_landing_polish" in report
