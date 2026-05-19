from __future__ import annotations

import re
from pathlib import Path


DOC_PATH = Path("docs/PORTFOLIO_REHEARSAL.md")
REPORT_PATH = Path("evals/reports/portfolio_rehearsal_report.md")
README_PATH = Path("README.md")
REQUIRED_LINKS = (
    "docs/PORTFOLIO_REHEARSAL.md",
    "evals/reports/portfolio_rehearsal_report.md",
)
PUBLIC_SCAN_PATHS = (
    README_PATH,
    DOC_PATH,
    REPORT_PATH,
    Path("docs/PORTFOLIO_QA.md"),
    Path("docs/PORTFOLIO_RESULT_SUMMARY.md"),
    Path("docs/RAG_DECISION_LEDGER.md"),
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
REJECTED_CANDIDATES = (
    "C1 smaller child",
    "BGE-M3",
    "BGE reranker",
    "GraphRAG-lite",
    "RAPTOR-lite",
    "HyDE",
    "active route",
    "Solar Pro 3 repaired v2",
)


def test_portfolio_rehearsal_docs_exist_and_are_sanitized() -> None:
    assert DOC_PATH.exists()
    assert REPORT_PATH.exists()

    for path in PUBLIC_SCAN_PATHS:
        text = path.read_text(encoding="utf-8")

        assert "chunk text" in text
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)
        assert "private_data/" not in text


def test_portfolio_rehearsal_readme_links_are_registered() -> None:
    readme = README_PATH.read_text(encoding="utf-8")

    for link in REQUIRED_LINKS:
        assert link in readme
        assert Path(link).exists()


def test_portfolio_rehearsal_scripts_and_demo_order_are_recorded() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")

    assert "## 30초 요약" in doc
    assert "## 3분 설명 스크립트" in doc
    assert "## Demo 순서" in doc
    assert "## 면접 질문 답변" in doc
    assert "## 리허설 채점표" in doc
    assert "README.md" in doc
    assert "docs/FINAL_ABLATION_REPORT.md" in doc
    assert "docs/API_RESPONSE_SAMPLE.md" in doc
    assert "docs/PORTFOLIO_DEMO_RUNBOOK.md" in doc


def test_portfolio_rehearsal_explains_rejected_candidates() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")

    for candidate in REJECTED_CANDIDATES:
        assert candidate in doc

    assert "기각 후보 설명 체크" in doc


def test_portfolio_rehearsal_keeps_forbidden_claims_as_forbidden() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    forbidden_section = doc.split("## 금지 Claim", maxsplit=1)[1]

    for claim in FORBIDDEN_CLAIMS:
        assert claim in forbidden_section


def test_portfolio_rehearsal_report_records_gates() -> None:
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert "portfolio_rehearsal_document_count | 1" in report
    assert "portfolio_rehearsal_report_count | 1" in report
    assert "thirty_second_script_count | 1" in report
    assert "three_minute_section_count | 6" in report
    assert "interview_answer_count | 12" in report
    assert "rejected_candidate_explained_count | 8" in report
    assert "demo_step_count | 5" in report
    assert "allowed_claim_count | 8" in report
    assert "forbidden_claim_count | 8" in report
    assert "live_solar_call_count | 0" in report
    assert "retrieval_execution_count | 0" in report
    assert "private_corpus_required_count | 0" in report
    assert "public_private_path_leakage_count | 0" in report
    assert "public_secret_like_leakage_count | 0" in report
    assert "public_raw_payload_leakage_count | 0" in report
    assert "External audit | PASS" in report
    assert "fact_portfolio_rehearsal" in report
