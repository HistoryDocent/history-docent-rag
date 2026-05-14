from __future__ import annotations

from pathlib import Path

from pipelines.build_query_type_router_skeleton_report import (
    build_report,
    collect_query_type_router_skeleton_failures,
)


def test_query_type_router_skeleton_report_gate_passes(tmp_path: Path) -> None:
    report = build_report(report_path=tmp_path / "query_type_router_skeleton_report.md")

    assert collect_query_type_router_skeleton_failures(report) == []
    assert report.summary.query_type_count == 7
    assert report.summary.relationship_hybrid_count == 1
    assert report.summary.abstain_first_count == 1
    assert report.summary.dense_default_count == 5
    assert report.summary.live_solar_call_count == 0
    assert report.output_quality.public_raw_text_leakage_count == 0
    assert report.output_quality.private_path_leakage_count == 0


def test_query_type_router_skeleton_report_writes_public_safe_markdown(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "query_type_router_skeleton_report.md"
    build_report(report_path=report_path)
    text = report_path.read_text(encoding="utf-8")

    assert "raw query" in text
    assert "chunk text" in text
    assert "Solar Pro 3 호출" in text
    assert "relationship_hybrid_weighted_e5_v1" in text
