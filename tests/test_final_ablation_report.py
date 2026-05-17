from __future__ import annotations

import re
from pathlib import Path

from app.domain.retrieval import FORBIDDEN_PUBLIC_EVAL_FIELDS


PUBLIC_DOC_PATHS = (
    Path("README.md"),
    Path("docs/FINAL_ABLATION_REPORT.md"),
    Path("evals/reports/final_ablation_report.md"),
)
STRICT_PUBLIC_DOC_PATHS = (
    Path("docs/FINAL_ABLATION_REPORT.md"),
    Path("evals/reports/final_ablation_report.md"),
)


def test_final_ablation_report_public_docs_exist_and_are_sanitized() -> None:
    for path in PUBLIC_DOC_PATHS:
        text = path.read_text(encoding="utf-8")

        assert "chunk text" in text
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\\s*=", text)

    for path in STRICT_PUBLIC_DOC_PATHS:
        text = path.read_text(encoding="utf-8")
        assert all(f"`{field}`" not in text for field in FORBIDDEN_PUBLIC_EVAL_FIELDS)


def test_final_ablation_report_records_default_stack_and_locked_decision() -> None:
    doc = Path("docs/FINAL_ABLATION_REPORT.md").read_text(encoding="utf-8")
    report = Path("evals/reports/final_ablation_report.md").read_text(
        encoding="utf-8",
    )

    assert "`C0 current parent-child`" in doc
    assert "`dense_multilingual_e5_small_voice_rewrite`" in doc
    assert "`P0_rank_order`" in doc
    assert "`solar-generation-baseline-v1`" in report
    assert "locked_primary_metric_delta | -0.100000" in report
    assert "locked_primary_metric_ci_low | -0.300000" in report
    assert "relationship active route | reject default enable" in report


def test_final_ablation_report_keeps_claim_boundary_and_next_gate() -> None:
    doc = Path("docs/FINAL_ABLATION_REPORT.md").read_text(encoding="utf-8")
    report = Path("evals/reports/final_ablation_report.md").read_text(
        encoding="utf-8",
    )

    assert "성능 개선 입증" in doc
    assert "production 성능 검증 완료" in report
    assert "active route 기본 활성화 완료" in report
    assert "`HD-API-SAMPLE-001`" in doc
    assert "`HD-API-SAMPLE-001`" in report
