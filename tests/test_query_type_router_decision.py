from __future__ import annotations

import re
from pathlib import Path

from app.domain.retrieval import FORBIDDEN_PUBLIC_EVAL_FIELDS


PUBLIC_DOC_PATHS = (
    Path("docs/QUERY_TYPE_ROUTER_DECISION.md"),
    Path("evals/reports/query_type_router_decision_report.md"),
)


def test_query_type_router_decision_docs_exist_and_are_sanitized() -> None:
    for path in PUBLIC_DOC_PATHS:
        text = path.read_text(encoding="utf-8")

        assert "raw query" in text
        assert "raw answer" in text
        assert "chunk text" in text
        assert "private path" in text
        assert "secret" in text
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\\s*=", text)
        assert all(f"`{field}`" not in text for field in FORBIDDEN_PUBLIC_EVAL_FIELDS)


def test_query_type_router_decision_records_core_policy() -> None:
    decision = Path("docs/QUERY_TYPE_ROUTER_DECISION.md").read_text(
        encoding="utf-8",
    )
    report = Path("evals/reports/query_type_router_decision_report.md").read_text(
        encoding="utf-8",
    )

    assert "`query_type_router_v1`" in report
    assert "`dense_multilingual_e5_small_voice_rewrite`" in decision
    assert "`relationship_hybrid_weighted_e5_v1`" in decision
    assert "`hybrid_weighted_e5_small_alpha_0_5`" in report
    assert "reject production route" in report
    assert "runtime router 구현이 아니다" in report
    assert "production 기본 route로 채택하지 않는다" in decision


def test_query_type_router_decision_keeps_claim_boundaries() -> None:
    report = Path("evals/reports/query_type_router_decision_report.md").read_text(
        encoding="utf-8",
    )

    assert "live_solar_call_count_for_this_report | 0" in report
    assert "dev-input-only" in report
    assert "live-dev-subset" in report
    assert "locked-readiness-only" in report
    assert "GraphRAG가 relationship에 효과적이다" in report
