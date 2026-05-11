from __future__ import annotations

from pathlib import Path

from app.domain.retrieval import RetrievalEvalItem
from app.domain.retrieval_experiment import (
    measure_public_retrieval_artifact_quality,
)
from app.domain.retrieval_overlap import (
    RETRIEVAL_OVERLAP_REPORT_VERSION,
    build_overlap_analysis_id,
    build_overlap_metric_summary,
    build_overlap_query_rows,
    build_public_overlap_result_rows,
    build_retrieval_overlap_report,
    build_retrieval_overlap_report_markdown,
    choose_hybrid_decision,
)


def _eval_item(
    *,
    query_id: str,
    query_type: str,
    expected_behavior: str,
    child_id: str | None = None,
) -> RetrievalEvalItem:
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
    return RetrievalEvalItem.model_validate(
        {
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
                "split": "dev",
                "difficulty": "medium",
                "place_ids": [],
                "requires_context": query_type in {"route_context", "voice_followup"},
                "answerability": "unanswerable"
                if expected_behavior == "abstain"
                else "answerable",
                "review_status": "reviewed",
            },
        }
    )


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


def test_build_overlap_metric_summary_and_report() -> None:
    items = [
        _eval_item(
            query_id="q-bm25-only",
            query_type="place_fact",
            expected_behavior="retrieve",
            child_id="child-a",
        ),
        _eval_item(
            query_id="q-dense-only",
            query_type="relationship",
            expected_behavior="retrieve",
            child_id="child-b",
        ),
        _eval_item(
            query_id="q-both",
            query_type="overview",
            expected_behavior="retrieve",
            child_id="child-c",
        ),
        _eval_item(
            query_id="q-fail",
            query_type="voice_followup",
            expected_behavior="retrieve",
            child_id="child-d",
        ),
        _eval_item(
            query_id="q-no-answer",
            query_type="no_answer",
            expected_behavior="abstain",
        ),
    ]
    result_rows = [
        _result_row(
            method="bm25",
            query_id="q-bm25-only",
            query_type="place_fact",
            rank=1,
            child_id="child-a",
        ),
        _result_row(
            method="dense",
            query_id="q-bm25-only",
            query_type="place_fact",
            rank=1,
            child_id="child-x",
        ),
        _result_row(
            method="bm25",
            query_id="q-dense-only",
            query_type="relationship",
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
            method="bm25",
            query_id="q-both",
            query_type="overview",
            rank=1,
            child_id="child-c",
        ),
        _result_row(
            method="dense",
            query_id="q-both",
            query_type="overview",
            rank=1,
            child_id="child-c",
        ),
        _result_row(
            method="bm25",
            query_id="q-fail",
            query_type="voice_followup",
            rank=1,
            child_id="child-x",
        ),
        _result_row(
            method="dense",
            query_id="q-fail",
            query_type="voice_followup",
            rank=1,
            child_id="child-y",
        ),
        _result_row(
            method="bm25",
            query_id="q-no-answer",
            query_type="no_answer",
            rank=1,
            child_id="child-x",
        ),
        _result_row(
            method="dense",
            query_id="q-no-answer",
            query_type="no_answer",
            rank=1,
            child_id="child-y",
        ),
    ]

    query_rows = build_overlap_query_rows(items=items, result_rows=result_rows)
    metric = build_overlap_metric_summary(
        items=items,
        result_rows=result_rows,
        query_rows=query_rows,
    )
    analysis_id = build_overlap_analysis_id(
        items=items,
        result_rows=result_rows,
        top_k=5,
    )
    public_rows = build_public_overlap_result_rows(
        analysis_id=analysis_id,
        query_rows=query_rows,
    )
    quality = measure_public_retrieval_artifact_quality(
        report_version=RETRIEVAL_OVERLAP_REPORT_VERSION,
        run_id=analysis_id,
        result_rows=public_rows,
        report_text="",
    )
    report = build_retrieval_overlap_report(
        dataset_path=Path("private_data/evals/datasets/retrieval_eval_dev.jsonl"),
        result_paths=[
            Path("private_data/evals/results/retrieval_experiment_bm25_results.jsonl"),
            Path("private_data/evals/results/retrieval_experiment_dense_results.jsonl"),
        ],
        items=items,
        result_rows=result_rows,
        output_quality=quality,
    )
    markdown = build_retrieval_overlap_report_markdown(report)

    assert metric.bm25_only_hit_count == 1
    assert metric.dense_only_hit_count == 1
    assert metric.both_hit_count == 1
    assert metric.both_fail_count == 1
    assert metric.bm25_recall_at_5 == 0.5
    assert metric.dense_recall_at_5 == 0.5
    assert metric.oracle_union_recall_at_5 == 0.75
    assert choose_hybrid_decision(metric) == "proceed_to_hybrid_rrf"
    assert quality.public_raw_text_leakage_count == 0
    assert "Hybrid 성능 개선 주장이 아니다" in markdown
    assert "query q-" not in markdown
