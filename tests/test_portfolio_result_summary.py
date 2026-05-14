from __future__ import annotations

import re
from pathlib import Path

from app.domain.retrieval import FORBIDDEN_PUBLIC_EVAL_FIELDS


PUBLIC_DOC_PATHS = (
    Path("README.md"),
    Path("docs/PORTFOLIO_RESULT_SUMMARY.md"),
    Path("evals/reports/portfolio_result_summary_report.md"),
)
STRICT_PUBLIC_DOC_PATHS = (
    Path("docs/PORTFOLIO_RESULT_SUMMARY.md"),
    Path("evals/reports/portfolio_result_summary_report.md"),
)


def test_portfolio_result_summary_public_docs_exist_and_are_sanitized() -> None:
    for path in PUBLIC_DOC_PATHS:
        text = path.read_text(encoding="utf-8")

        assert "raw query" in text or path.name == "README.md"
        assert "chunk text" in text
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\\s*=", text)

    for path in STRICT_PUBLIC_DOC_PATHS:
        text = path.read_text(encoding="utf-8")
        assert all(f"`{field}`" not in text for field in FORBIDDEN_PUBLIC_EVAL_FIELDS)


def test_portfolio_result_summary_records_current_stack_and_decisions() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    summary = Path("docs/PORTFOLIO_RESULT_SUMMARY.md").read_text(encoding="utf-8")
    report = Path("evals/reports/portfolio_result_summary_report.md").read_text(
        encoding="utf-8",
    )

    assert "포트폴리오 결과 요약" in readme
    assert "`dense_multilingual_e5_small_voice_rewrite`" in summary
    assert "`query_type_router_v1`" in summary
    assert "GraphRAG-lite" in summary
    assert "RAPTOR-lite" in summary
    assert "selected_candidate_count | 0" in summary
    assert "summarized_stage_count | 13" in report
    assert "public_raw_text_leakage_count | 0" in report


def test_portfolio_result_summary_keeps_claim_boundaries() -> None:
    summary = Path("docs/PORTFOLIO_RESULT_SUMMARY.md").read_text(encoding="utf-8")
    report = Path("evals/reports/portfolio_result_summary_report.md").read_text(
        encoding="utf-8",
    )

    assert "production 성능 검증 완료" in summary
    assert "locked test에서 최종 성능 개선 입증" in summary
    assert "성능 개선 주장이 아니다" in report
    assert "live_solar_call_count_for_this_report | 0" in report
