from __future__ import annotations

import re
from pathlib import Path

from app.domain.retrieval import FORBIDDEN_PUBLIC_EVAL_FIELDS
from pipelines.build_portfolio_failure_analysis_report import (
    build_portfolio_failure_analysis_report,
    collect_portfolio_failure_analysis_failures,
)


PUBLIC_DOC_PATHS = (
    Path("docs/PORTFOLIO_FAILURE_ANALYSIS.md"),
    Path("evals/reports/portfolio_failure_analysis_report.md"),
)


def test_portfolio_failure_analysis_public_docs_exist_and_are_sanitized() -> None:
    for path in PUBLIC_DOC_PATHS:
        text = path.read_text(encoding="utf-8")
        assert "raw query" in text
        assert "chunk text" in text
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\\s*=", text)
        assert all(f"`{field}`" not in text for field in FORBIDDEN_PUBLIC_EVAL_FIELDS)


def test_portfolio_failure_analysis_records_ten_public_safe_cases() -> None:
    doc = Path("docs/PORTFOLIO_FAILURE_ANALYSIS.md").read_text(encoding="utf-8")
    report = Path("evals/reports/portfolio_failure_analysis_report.md").read_text(
        encoding="utf-8",
    )

    assert "전체 청킹 비교 테스트를 다시 열지 않는다" in doc
    assert "| case_count | 10 |" in doc
    assert "| unique_query_count | 10 |" in doc
    assert "| chunk_boundary_audit_candidate_count | 1 |" in doc
    assert "| reopen_global_chunking_count | 0 |" in doc
    assert "`q-dev-place-story-001`" in doc
    assert "`q-dev-no-answer-001`" in doc
    assert "portfolio-failure-analysis-report/v1" in report
    assert "| result_row_count | 10 |" in report
    assert "| public_raw_text_leakage_count | 0 |" in report


def test_portfolio_failure_analysis_report_gate_passes(tmp_path: Path) -> None:
    report = build_portfolio_failure_analysis_report(
        doc_path=tmp_path / "portfolio_failure_analysis.md",
        report_path=tmp_path / "portfolio_failure_analysis_report.md",
        result_path=tmp_path / "portfolio_failure_analysis_rows.jsonl",
    )

    assert collect_portfolio_failure_analysis_failures(report) == []
    assert report.summary.case_count == 10
    assert report.summary.unique_query_count == 10
    assert report.summary.reopen_global_chunking_count == 0
    assert report.summary.live_solar_call_count_for_this_report == 0
    assert not report.summary.cuda_required
