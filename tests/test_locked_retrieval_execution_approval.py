from __future__ import annotations

import re
from pathlib import Path

from app.domain.retrieval import FORBIDDEN_PUBLIC_EVAL_FIELDS


DOC_PATH = Path("docs/LOCKED_RETRIEVAL_EXECUTION_APPROVAL.md")
REPORT_PATH = Path("evals/reports/locked_retrieval_execution_approval_report.md")


def test_locked_retrieval_execution_approval_docs_exist_and_defer_execution() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert "`HD-LOCKED-RETRIEVAL-003`" in doc
    assert "`HD-LOCKED-RETRIEVAL-003`" in report
    assert "locked_execution_approved | false" in report
    assert "retrieval_execution_count | 0" in report
    assert "locked_metric_result_count | 0" in report
    assert "planned_solar_call_count | 0" in report
    assert "solar_call_count | 0" in doc
    assert "성능 개선 주장이 아니다" in report


def test_locked_retrieval_execution_approval_sets_eval_gate() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert "planned_locked_query_count | 35" in report
    assert "planned_query_type_count | 7" in report
    assert "planned_candidate_count | 2" in report
    assert "rejected_candidate_count | 4" in report
    assert "planned_bootstrap_iteration_count | 10000" in report
    assert "confidence_interval_percent | 95" in report
    assert "`Recall@1`, `Recall@3`, `Recall@5`" in doc
    assert "`MRR`, `nDCG@5`" in doc
    assert "bootstrap 10000회" in doc
    assert "95% confidence interval" in doc


def test_locked_retrieval_execution_approval_limits_candidates_and_grain() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    expected_grain = "`run_id + query_id + candidate_id + metric_name`"
    assert "`dense_multilingual_e5_small_voice_rewrite`" in doc
    assert "`relationship_hybrid_weighted_e5_v1`" in doc
    assert "hyde_larger_live_candidate` | rejected" in report
    assert "graphrag_lite_entity_path_v1` | rejected" in report
    assert "raptor_lite_summary_node_v1` | rejected" in report
    assert "place_story_guarded_boost_v1` | rejected" in report
    assert expected_grain in doc
    assert expected_grain in report
    assert "`fact_locked_retrieval_eval`" in doc
    assert "`fact_locked_public_summary`" in doc


def test_locked_retrieval_execution_approval_public_docs_are_sanitized() -> None:
    for path in (DOC_PATH, REPORT_PATH):
        text = path.read_text(encoding="utf-8")

        assert "raw query" in text
        assert "chunk text" in text
        assert "private path" in text
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\\s*=", text)
        assert all(f"`{field}`" not in text for field in FORBIDDEN_PUBLIC_EVAL_FIELDS)

    report = REPORT_PATH.read_text(encoding="utf-8")
    assert "public_raw_text_leakage_count | 0" in report
    assert "private_path_leakage_count | 0" in report
    assert "secret_like_leakage_count | 0" in report
    assert "forbidden_result_field_count | 0" in report
