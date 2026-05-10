from __future__ import annotations

import json
import re
from pathlib import Path


def test_retrieval_harness_report_matches_public_results() -> None:
    report = Path("evals/reports/retrieval_harness_report.md").read_text(encoding="utf-8")
    baseline_report = Path("evals/reports/bm25_baseline_report.md").read_text(
        encoding="utf-8"
    )
    rows = [
        json.loads(line)
        for line in Path("evals/results/retrieval_experiment_bm25_results.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]

    assert len(rows) == 70
    assert len({row["query_id"] for row in rows}) == 14
    assert {row["method"] for row in rows} == {"bm25"}
    assert "| result_row_count | 70 |" in report
    assert _harness_summary_metrics(report) == _baseline_summary_metrics(baseline_report)
    assert _harness_query_type_rows(report) == _baseline_query_type_rows(baseline_report)
    assert "| bm25 | bm25 | 0.000000 | 0.000000 | 0.000000 |" in report
    assert "성능 개선 주장이 아니다" in report
    assert "dataset_fingerprint" in report
    assert "corpus_fingerprint" in report


def test_retrieval_harness_public_artifacts_do_not_include_private_text_fields() -> None:
    result_text = Path("evals/results/retrieval_experiment_bm25_results.jsonl").read_text(
        encoding="utf-8"
    )
    report_text = Path("evals/reports/retrieval_harness_report.md").read_text(
        encoding="utf-8"
    )

    assert '"text"' not in result_text
    assert "search_text" not in result_text
    assert "context_text" not in result_text
    assert "source_text" not in result_text
    assert "raw_text" not in result_text
    assert "private_path_leakage_count | 0" in report_text
    assert "private_data/" not in report_text
    assert "F:" not in result_text
    assert "C:" not in result_text


def test_dense_hybrid_notebook_uses_private_artifact_alias() -> None:
    notebook = Path("notebooks/07_dense_hybrid_retrieval_comparison.ipynb").read_text(
        encoding="utf-8"
    )

    assert "../private_data/reports/parent_child_chunks.json" not in notebook
    assert "private_data/" not in notebook
    assert "F:" not in notebook
    assert "C:" not in notebook
    assert "\\\\" not in notebook
    assert "<private parent_child_chunks report>" in notebook


def _baseline_summary_metrics(report: str) -> dict[str, str]:
    metric_names = ["Recall@1", "Recall@3", "Recall@5", "MRR", "nDCG@5"]
    return {
        metric_name: _extract_metric_table_value(report, metric_name)
        for metric_name in metric_names
    }


def _harness_summary_metrics(report: str) -> dict[str, str]:
    row = next(
        line
        for line in report.splitlines()
        if line.startswith("| bm25 | 14 | 12 | 2 | 14 | 0 |")
    )
    columns = [column.strip() for column in row.strip("|").split("|")]
    return {
        "Recall@1": columns[6],
        "Recall@3": columns[7],
        "Recall@5": columns[8],
        "MRR": columns[9],
        "nDCG@5": columns[10],
    }


def _baseline_query_type_rows(report: str) -> dict[str, tuple[str, str, str, str, str]]:
    rows: dict[str, tuple[str, str, str, str, str]] = {}
    for line in report.splitlines():
        if not re.match(r"^\| (no_answer|overview|place_fact|place_story|relationship|route_context|voice_followup) \|", line):
            continue
        columns = [column.strip() for column in line.strip("|").split("|")]
        rows[columns[0]] = (columns[2], columns[3], columns[4], columns[5], columns[6])
    return rows


def _harness_query_type_rows(report: str) -> dict[str, tuple[str, str, str, str, str]]:
    rows: dict[str, tuple[str, str, str, str, str]] = {}
    for line in report.splitlines():
        if not line.startswith("| bm25 |"):
            continue
        columns = [column.strip() for column in line.strip("|").split("|")]
        if len(columns) != 10 or columns[1] not in {
            "no_answer",
            "overview",
            "place_fact",
            "place_story",
            "relationship",
            "route_context",
            "voice_followup",
        }:
            continue
        rows[columns[1]] = (columns[3], columns[4], columns[5], columns[6], columns[7])
    return rows


def _extract_metric_table_value(report: str, metric_name: str) -> str:
    match = re.search(rf"^\| {re.escape(metric_name)} \| ([0-9.]+) \|$", report, re.MULTILINE)
    if match is None:
        raise AssertionError(f"missing metric in baseline report: {metric_name}")
    return match.group(1)
