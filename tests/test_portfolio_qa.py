from __future__ import annotations

import re
from pathlib import Path

from app.domain.retrieval import FORBIDDEN_PUBLIC_EVAL_FIELDS


PUBLIC_DOC_PATHS = (
    Path("docs/PORTFOLIO_QA.md"),
    Path("evals/reports/portfolio_qa_report.md"),
    Path("README.md"),
)
STRICT_PUBLIC_DOC_PATHS = (
    Path("docs/PORTFOLIO_QA.md"),
    Path("evals/reports/portfolio_qa_report.md"),
)


def test_portfolio_qa_docs_exist_and_are_sanitized() -> None:
    for path in PUBLIC_DOC_PATHS:
        text = path.read_text(encoding="utf-8")

        assert "chunk text" in text
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\\s*=", text)
        assert "private_data/" not in text

    for path in STRICT_PUBLIC_DOC_PATHS:
        text = path.read_text(encoding="utf-8")
        assert all(f"`{field}`" not in text for field in FORBIDDEN_PUBLIC_EVAL_FIELDS)


def test_portfolio_qa_records_resume_and_interview_messages() -> None:
    doc = Path("docs/PORTFOLIO_QA.md").read_text(encoding="utf-8")

    assert "제출용 한 줄" in doc
    assert "이력서 프로젝트 문장" in doc
    assert "면접 답변" in doc
    assert "HistoryDocent | 서울/한양 역사 관광 도슨트 RAG 백엔드" in doc
    assert "`/api/v1/chat`" in doc
    assert "`C0 parent-child chunking + dense_multilingual_e5_small_voice_rewrite" in doc
    assert "active route를 바로 켜지 않은 결정" in doc


def test_portfolio_qa_report_records_gates_and_claim_boundaries() -> None:
    report = Path("evals/reports/portfolio_qa_report.md").read_text(encoding="utf-8")

    assert "resume_one_line_count | 1" in report
    assert "resume_bullet_count | 5" in report
    assert "interview_answer_count | 10" in report
    assert "forbidden_claim_count | 0" in report
    assert "public_raw_text_leakage_count | 0" in report
    assert "portfolio_message_id + audience + claim_boundary + evidence_artifact" in report
    assert "`HD-COLBERT-001`" in report


def test_portfolio_qa_keeps_forbidden_claims_as_forbidden_only() -> None:
    doc = Path("docs/PORTFOLIO_QA.md").read_text(encoding="utf-8")

    forbidden_section = doc.split("## 금지 표현", maxsplit=1)[1]
    assert "production 성능 검증 완료" in forbidden_section
    assert "locked test에서 최종 성능 개선 입증" in forbidden_section
    assert "음성 관광 앱 완성" in forbidden_section
