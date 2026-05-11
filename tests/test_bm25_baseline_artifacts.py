from __future__ import annotations

import json
from pathlib import Path


def test_bm25_baseline_report_matches_public_results() -> None:
    report = Path("evals/reports/bm25_baseline_report.md").read_text(encoding="utf-8")
    rows = [
        json.loads(line)
        for line in Path("evals/results/bm25_baseline_results.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]

    assert len(rows) == 70
    assert len({row["query_id"] for row in rows}) == 14
    assert "| result_row_count | 70 |" in report
    assert "| missing_result_count | 0 |" in report
    assert "| Recall@5 | 0.250000 |" in report
    assert "| MRR | 0.152778 |" in report
    assert "| nDCG@5 | 0.120124 |" in report


def test_bm25_baseline_public_artifacts_do_not_include_private_text_fields() -> None:
    result_text = Path("evals/results/bm25_baseline_results.jsonl").read_text(encoding="utf-8")
    report_text = Path("evals/reports/bm25_baseline_report.md").read_text(encoding="utf-8")

    assert '"text"' not in result_text
    assert "search_text" not in result_text
    assert "context_text" not in result_text
    assert "source_text" not in result_text
    assert "raw_text" not in result_text
    assert "private_path_leakage_count | 0" in report_text
    assert "private_data/" not in report_text
    assert "F:" not in result_text
    assert "C:" not in result_text


def test_bm25_notebook_uses_private_artifact_alias() -> None:
    notebook = Path("notebooks/06_bm25_baseline_evaluation.ipynb").read_text(
        encoding="utf-8"
    )

    assert "../" + _private_chunks_path() not in notebook
    assert "private_data/" not in notebook
    assert "F:" not in notebook
    assert "C:" not in notebook
    assert "\\\\" not in notebook
    assert "<private parent_child_chunks report>" in notebook


def _private_chunks_path() -> str:
    return "/".join(["private_data", "reports", "parent_child_chunks.json"])
