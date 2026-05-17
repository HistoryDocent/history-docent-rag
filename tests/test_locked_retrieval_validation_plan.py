from __future__ import annotations

import re
from pathlib import Path

from app.domain.retrieval import FORBIDDEN_PUBLIC_EVAL_FIELDS


PLAN_PATH = Path("docs/LOCKED_RETRIEVAL_VALIDATION_PLAN.md")
REPORT_PATH = Path("evals/reports/locked_retrieval_validation_plan_report.md")


def test_locked_retrieval_validation_plan_exists_and_defers_execution() -> None:
    plan = PLAN_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert "`HD-LOCKED-RETRIEVAL-001`" in plan
    assert "locked_test_execution_count | 0" in report
    assert "locked_metric_result_count | 0" in report
    assert "solar_call_count | 0" in report
    assert "planned_locked_query_count | 35" in report
    assert "planned_query_type_count | 7" in report


def test_locked_retrieval_validation_plan_limits_candidates() -> None:
    plan = PLAN_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert "`dense_multilingual_e5_small_voice_rewrite`" in plan
    assert "`relationship_hybrid_weighted_e5_v1`" in plan
    assert "hyde_larger_live_candidate` | rejected_for_locked_plan" in report
    assert "graphrag_lite_entity_path_v1` | rejected_for_locked_plan" in report
    assert "raptor_lite_summary_node_v1` | rejected_for_locked_plan" in report
    assert "place_story_guarded_boost_v1` | rejected_for_locked_plan" in report


def test_locked_retrieval_validation_plan_sets_data_mart_grain() -> None:
    plan = PLAN_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    expected_grain = "`run_id + query_id + candidate_id + metric_name`"
    assert expected_grain in plan
    assert expected_grain in report
    assert "`fact_locked_retrieval_eval`" in plan
    assert "`fact_locked_public_summary`" in plan


def test_locked_retrieval_validation_plan_is_public_safe() -> None:
    for path in (PLAN_PATH, REPORT_PATH):
        text = path.read_text(encoding="utf-8")

        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)
        assert all(f"`{field}`" not in text for field in FORBIDDEN_PUBLIC_EVAL_FIELDS)

    report = REPORT_PATH.read_text(encoding="utf-8")
    assert "public_raw_text_leakage_count | 0" in report
    assert "private_path_leakage_count | 0" in report
    assert "secret_like_leakage_count | 0" in report
    assert "forbidden_result_field_count | 0" in report
