from __future__ import annotations

import json
from pathlib import Path

from app.domain.retrieval import FORBIDDEN_PUBLIC_EVAL_FIELDS
from pipelines.run_graphrag_lite_relationship_plan import (
    GRAPHRAG_LITE_RELATIONSHIP_PLAN_REPORT_VERSION,
    build_graphrag_lite_plan_summary,
    build_graphrag_lite_strategy_rows,
    collect_graphrag_lite_relationship_plan_failures,
    run_graphrag_lite_relationship_plan,
)


def test_graphrag_lite_relationship_plan_writes_public_safe_report(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "graphrag_lite_relationship_plan_report.md"
    rows_path = tmp_path / "graphrag_lite_relationship_plan_rows.jsonl"

    report = run_graphrag_lite_relationship_plan(
        report_path=report_path,
        result_rows_path=rows_path,
    )
    markdown = report_path.read_text(encoding="utf-8")
    rows = [json.loads(line) for line in rows_path.read_text(encoding="utf-8").splitlines()]

    assert report.report_version == GRAPHRAG_LITE_RELATIONSHIP_PLAN_REPORT_VERSION
    assert report.summary.planned_query_type_count == 1
    assert report.summary.planned_dev_query_count == 10
    assert report.summary.planned_test_query_count == 5
    assert report.summary.baseline_count == 1
    assert report.summary.candidate_count == 2
    assert report.summary.planned_solar_call_count == 0
    assert report.summary.decision == "ready_for_graphrag_lite_input_only_approval"
    assert {row.query_type for row in report.strategy_rows} == {"relationship"}
    assert {row.final_citation_source for row in report.strategy_rows} == {"source_child_chunk"}
    assert collect_graphrag_lite_relationship_plan_failures(report) == []
    assert report.output_quality.public_raw_text_leakage_count == 0
    assert report.output_quality.private_path_leakage_count == 0
    assert report.output_quality.secret_like_leakage_count == 0
    assert "GraphRAG-lite는 기본 RAG pipeline이 아니라" in markdown
    assert "성능 개선" in markdown
    assert all(FORBIDDEN_PUBLIC_EVAL_FIELDS.isdisjoint(row.keys()) for row in rows)


def test_graphrag_lite_relationship_plan_summary_blocks_public_raw_text() -> None:
    rows = tuple(
        row.model_copy(update={"raw_text_public_allowed": True})
        if row.strategy_id == "graphrag_lite_entity_path_v1"
        else row
        for row in build_graphrag_lite_strategy_rows()
    )
    summary = build_graphrag_lite_plan_summary(rows)

    assert summary.planned_raw_text_public_count == 1
    assert summary.decision == "blocked"
