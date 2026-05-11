from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core import project_paths
from app.domain.retrieval_experiment import collect_public_retrieval_artifact_failures
import pipelines.analyze_retrieval_overlap as overlap_pipeline
from pipelines.analyze_retrieval_overlap import analyze_retrieval_overlap


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )


def _eval_item_payload(
    *,
    query_id: str,
    query_type: str,
    expected_behavior: str,
    child_id: str | None = None,
    split: str = "dev",
    review_status: str = "reviewed",
) -> dict[str, object]:
    judgments: list[dict[str, object]] = []
    if expected_behavior == "retrieve":
        judgments.append(
            {
                "query_id": query_id,
                "relevant_child_ids": [child_id],
                "relevant_parent_ids": [f"parent-{child_id}"],
                "relevant_doc_ids": [f"doc-{child_id}"],
                "relevance_grade": 3,
                "rationale_summary": "target ids only",
                "public_allowed": True,
            }
        )
    return {
        "dataset_version": "retrieval-eval-dataset/v2",
        "query": {
            "query_id": query_id,
            "query_type": query_type,
            "query_text": f"query {query_id}",
            "language": "ko",
            "expected_behavior": expected_behavior,
            "user_context": None,
            "public_allowed": True,
        },
        "judgments": judgments,
        "metadata": {
            "split": split,
            "difficulty": "medium",
            "place_ids": [],
            "requires_context": query_type in {"route_context", "voice_followup"},
            "answerability": "unanswerable"
            if expected_behavior == "abstain"
            else "answerable",
            "review_status": review_status,
        },
    }


def _result_row(
    *,
    method: str,
    query_id: str,
    query_type: str,
    rank: int,
    child_id: str,
) -> dict[str, object]:
    return {
        "run_id": f"run-{method}",
        "method": method,
        "query_id": query_id,
        "query_type": query_type,
        "latency_ms": 1.0,
        "rank": rank,
        "retrieval_doc_id": child_id,
        "child_id": child_id,
        "parent_id": f"parent-{child_id}",
        "doc_id": f"doc-{child_id}",
        "score": 1.0,
    }


def test_analyze_retrieval_overlap_writes_public_safe_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(project_paths, "_REPOSITORY_ROOT", tmp_path)
    dataset_path = tmp_path / "private_data" / "evals" / "datasets" / "retrieval_eval_dev.jsonl"
    results_dir = tmp_path / "private_data" / "evals" / "results"
    report_path = tmp_path / "evals" / "reports" / "retrieval_overlap_analysis_report.md"
    _write_jsonl(
        dataset_path,
        [
            _eval_item_payload(
                query_id="q-bm25-only",
                query_type="place_fact",
                expected_behavior="retrieve",
                child_id="child-a",
            ),
            _eval_item_payload(
                query_id="q-dense-only",
                query_type="relationship",
                expected_behavior="retrieve",
                child_id="child-b",
            ),
            _eval_item_payload(
                query_id="q-no-answer",
                query_type="no_answer",
                expected_behavior="abstain",
            ),
        ],
    )
    _write_jsonl(
        results_dir / "retrieval_experiment_bm25_results.jsonl",
        [
            _result_row(
                method="bm25",
                query_id="q-bm25-only",
                query_type="place_fact",
                rank=1,
                child_id="child-a",
            ),
            _result_row(
                method="bm25",
                query_id="q-dense-only",
                query_type="relationship",
                rank=1,
                child_id="child-x",
            ),
            _result_row(
                method="bm25",
                query_id="q-no-answer",
                query_type="no_answer",
                rank=1,
                child_id="child-x",
            ),
        ],
    )
    _write_jsonl(
        results_dir / "retrieval_experiment_dense_results.jsonl",
        [
            _result_row(
                method="dense",
                query_id="q-bm25-only",
                query_type="place_fact",
                rank=1,
                child_id="child-x",
            ),
            _result_row(
                method="dense",
                query_id="q-dense-only",
                query_type="relationship",
                rank=1,
                child_id="child-b",
            ),
            _result_row(
                method="dense",
                query_id="q-no-answer",
                query_type="no_answer",
                rank=1,
                child_id="child-y",
            ),
        ],
    )

    report = analyze_retrieval_overlap(
        dataset_path=dataset_path,
        results_dir=results_dir,
        report_path=report_path,
        execute_retrieval=False,
    )
    markdown = report_path.read_text(encoding="utf-8")

    assert report.metric_summary.bm25_only_hit_count == 1
    assert report.metric_summary.dense_only_hit_count == 1
    assert report.metric_summary.oracle_union_recall_at_5 == 1.0
    assert report.hybrid_decision == "proceed_to_hybrid_rrf"
    assert report.output_quality.private_path_leakage_count == 0
    assert collect_public_retrieval_artifact_failures(report.output_quality) == []
    assert "## 정량 리포트" in markdown
    assert "## 정성 리포트" in markdown
    assert "<private retrieval eval dataset: retrieval_eval_dev.jsonl>" in markdown
    assert str(dataset_path) not in markdown


def test_overlap_rejects_private_dataset_with_public_results_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(project_paths, "_REPOSITORY_ROOT", tmp_path)
    dataset_path = tmp_path / "private_data" / "evals" / "datasets" / "retrieval_eval_dev.jsonl"
    _write_jsonl(
        dataset_path,
        [
            _eval_item_payload(
                query_id="q-dev",
                query_type="place_fact",
                expected_behavior="retrieve",
                child_id="child-a",
            )
        ],
    )

    with pytest.raises(ValueError, match="private_data results"):
        analyze_retrieval_overlap(
            dataset_path=dataset_path,
            results_dir=tmp_path / "evals" / "results",
            report_path=tmp_path / "report.md",
            execute_retrieval=False,
        )


def test_overlap_rejects_locked_test_split_when_retrieval_is_skipped(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(project_paths, "_REPOSITORY_ROOT", tmp_path)
    dataset_path = tmp_path / "private_data" / "evals" / "datasets" / "retrieval_eval_test.jsonl"
    results_dir = tmp_path / "private_data" / "evals" / "results"
    _write_jsonl(
        dataset_path,
        [
            _eval_item_payload(
                query_id="q-test",
                query_type="place_fact",
                expected_behavior="retrieve",
                child_id="child-a",
                split="test",
                review_status="locked",
            )
        ],
    )
    for method in ("bm25", "dense"):
        _write_jsonl(
            results_dir / f"retrieval_experiment_{method}_results.jsonl",
            [
                _result_row(
                    method=method,
                    query_id="q-test",
                    query_type="place_fact",
                    rank=1,
                    child_id="child-a",
                )
            ],
        )

    with pytest.raises(ValueError, match="locked/test split"):
        analyze_retrieval_overlap(
            dataset_path=dataset_path,
            results_dir=results_dir,
            report_path=tmp_path / "report.md",
            execute_retrieval=False,
        )


def test_overlap_rejects_unreviewed_rows_when_retrieval_is_skipped(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(project_paths, "_REPOSITORY_ROOT", tmp_path)
    dataset_path = tmp_path / "private_data" / "evals" / "datasets" / "retrieval_eval_dev.jsonl"
    results_dir = tmp_path / "private_data" / "evals" / "results"
    _write_jsonl(
        dataset_path,
        [
            _eval_item_payload(
                query_id="q-dev",
                query_type="place_fact",
                expected_behavior="retrieve",
                child_id="child-a",
                split="dev",
                review_status="draft",
            )
        ],
    )
    for method in ("bm25", "dense"):
        _write_jsonl(
            results_dir / f"retrieval_experiment_{method}_results.jsonl",
            [
                _result_row(
                    method=method,
                    query_id="q-dev",
                    query_type="place_fact",
                    rank=1,
                    child_id="child-a",
                )
            ],
        )

    with pytest.raises(ValueError, match="reviewed seed/dev rows only"):
        analyze_retrieval_overlap(
            dataset_path=dataset_path,
            results_dir=results_dir,
            report_path=tmp_path / "report.md",
            execute_retrieval=False,
        )


def test_overlap_public_output_gate_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(project_paths, "_REPOSITORY_ROOT", tmp_path)
    dataset_path = tmp_path / "private_data" / "evals" / "datasets" / "retrieval_eval_dev.jsonl"
    results_dir = tmp_path / "private_data" / "evals" / "results"
    report_path = tmp_path / "evals" / "reports" / "retrieval_overlap_analysis_report.md"
    _write_jsonl(
        dataset_path,
        [
            _eval_item_payload(
                query_id="q-dev",
                query_type="place_fact",
                expected_behavior="retrieve",
                child_id="child-a",
            )
        ],
    )
    for method in ("bm25", "dense"):
        _write_jsonl(
            results_dir / f"retrieval_experiment_{method}_results.jsonl",
            [
                _result_row(
                    method=method,
                    query_id="q-dev",
                    query_type="place_fact",
                    rank=1,
                    child_id="child-a",
                )
            ],
        )

    def unsafe_markdown(report: object) -> str:
        return "F" + ":\\private_data\\raw\\source.pdf"

    monkeypatch.setattr(
        overlap_pipeline,
        "build_retrieval_overlap_report_markdown",
        unsafe_markdown,
    )

    with pytest.raises(ValueError, match="retrieval overlap public output gate failed"):
        analyze_retrieval_overlap(
            dataset_path=dataset_path,
            results_dir=results_dir,
            report_path=report_path,
            execute_retrieval=False,
        )

    assert not report_path.exists()
