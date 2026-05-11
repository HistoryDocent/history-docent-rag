from __future__ import annotations

from pathlib import Path

import pytest

from app.core import project_paths
from app.domain.data_contracts import PageSpan
from app.domain.retrieval import (
    QueryType,
    RetrievedCandidate,
    RetrievalDocument,
    RetrievalEvalItem,
    RetrievalMethod,
    RetrievalRunResult,
)
from app.domain.retrieval_experiment import (
    RETRIEVAL_EXPERIMENT_REPORT_VERSION,
    build_metric_deltas,
    build_public_retrieval_result_rows,
    build_retrieval_comparison_report,
    build_retrieval_experiment_run,
    collect_public_retrieval_artifact_failures,
    compute_query_type_metric_breakdown,
    measure_public_retrieval_artifact_quality,
    public_path_alias,
)


def _doc(identifier: str) -> RetrievalDocument:
    return RetrievalDocument(
        retrieval_doc_id=identifier,
        child_id=identifier,
        parent_id=f"parent-{identifier}",
        doc_id=f"doc-{identifier}",
        doc_title=f"Doc {identifier}",
        page_span=PageSpan(
            page_local_start=1,
            page_local_end=1,
            page_global_start=1,
            page_global_end=1,
        ),
        source_block_ids=[f"block-{identifier}"],
        text_hash="a" * 64,
        text_length=100,
        element_type_mix={"paragraph": 1},
        citation_block_ids=[f"block-{identifier}"],
        public_allowed=False,
    )


def _item(query_id: str, query_type: QueryType, child_id: str) -> RetrievalEvalItem:
    return RetrievalEvalItem.model_validate(
        {
            "dataset_version": "retrieval-eval-dataset/v2",
            "query": {
                "query_id": query_id,
                "query_type": query_type,
                "query_text": f"{query_id} text",
                "language": "ko",
                "expected_behavior": "retrieve",
                "public_allowed": True,
            },
            "judgments": [
                {
                    "query_id": query_id,
                    "relevant_child_ids": [child_id],
                    "relevant_parent_ids": [],
                    "relevant_doc_ids": [],
                    "relevance_grade": 3,
                    "rationale_summary": "id-only public judgment",
                    "public_allowed": True,
                }
            ],
            "metadata": {
                "split": "dev",
                "difficulty": "hard" if query_type == "route_context" else "medium",
                "place_ids": ["gyeongbokgung"],
                "requires_context": query_type in {"route_context", "voice_followup"},
                "answerability": "answerable",
                "review_status": "draft",
            },
        }
    )


def _result(
    query_id: str,
    query_type: QueryType,
    method: RetrievalMethod,
    child_id: str,
) -> RetrievalRunResult:
    return RetrievalRunResult(
        query_id=query_id,
        query_type=query_type,
        method=method,
        candidates=[
            RetrievedCandidate(
                rank=1,
                retrieval_doc_id=child_id,
                child_id=child_id,
                parent_id=f"parent-{child_id}",
                doc_id=f"doc-{child_id}",
                score=1.0,
            )
        ],
        latency_ms=1.0,
    )


def test_query_type_breakdown_and_metric_delta_use_common_schema() -> None:
    items = [
        _item("q-place", "place_fact", "child-a"),
        _item("q-route", "route_context", "child-b"),
    ]
    documents = [_doc("child-a"), _doc("child-b")]
    bm25_results = [
        _result("q-place", "place_fact", "bm25", "child-a"),
        _result("q-route", "route_context", "bm25", "child-b"),
    ]
    dense_results = [
        _result("q-place", "place_fact", "dense", "child-b"),
        _result("q-route", "route_context", "dense", "child-b"),
    ]

    breakdown = compute_query_type_metric_breakdown(
        items=items,
        results=bm25_results,
        method="bm25",
    )
    bm25_run = build_retrieval_experiment_run(
        method="bm25",
        top_k=1,
        items=items,
        documents=documents,
        results=bm25_results,
        result_path=Path("evals/results/retrieval_experiment_bm25_results.jsonl"),
    )
    dense_run = build_retrieval_experiment_run(
        method="dense",
        top_k=1,
        items=items,
        documents=documents,
        results=dense_results,
        result_path=Path("evals/results/retrieval_experiment_dense_results.jsonl"),
    )
    deltas = build_metric_deltas(method_runs=[bm25_run, dense_run], baseline_method="bm25")

    assert {item.query_type for item in breakdown} == {"place_fact", "route_context"}
    assert bm25_run.metric_summary.recall_at_1 == 1.0
    assert dense_run.metric_summary.recall_at_1 == 0.5
    assert deltas[0].compared_method == "bm25"
    assert deltas[0].recall_at_5_delta == 0.0
    assert deltas[1].compared_method == "dense"
    assert deltas[1].recall_at_5_delta == -0.5


def test_public_retrieval_rows_and_quality_gate_exclude_private_text() -> None:
    result = _result("q-place", "place_fact", "bm25", "child-a")
    rows = build_public_retrieval_result_rows(
        run_id="retrieval-harness-bm25-test",
        results=[result],
    )
    marker_value = "api_" + "key=redacted"
    provider_marker = "ghp_" + "redacted"
    unsafe_rows = [
        {
            **rows[0],
            "text": "private source body",
            "path": "C:" + "\\private\\source.pdf",
            "marker": marker_value,
        },
        {
            **rows[0],
            "path": "/" + "home/runner/work/private/source.pdf",
            "marker": provider_marker,
        }
    ]

    quality = measure_public_retrieval_artifact_quality(
        report_version=RETRIEVAL_EXPERIMENT_REPORT_VERSION,
        run_id="retrieval-harness-bm25-test",
        result_rows=unsafe_rows,
        report_text="",
        extra_public_texts={
            "long_notebook_line": "가" * 601,
            "multiline_snippet": "line1\nline2",
            "artifact.md:1": "서울의 오래된 궁궐과 도성 이야기를 긴 문장으로 그대로 적은 첫 번째 줄입니다.",
            "artifact.md:2": "왕조의 시작과 수도의 이동을 설명하는 원문성 문장이 이어지는 두 번째 줄입니다.",
            "artifact.md:3": "관광 설명이 아니라 출처 문장을 연속으로 붙여 둔 세 번째 줄입니다. 추가 문장입니다.",
        },
    )

    assert "text" not in rows[0]
    assert "search_text" not in rows[0]
    assert quality.public_raw_text_leakage_count == 4
    assert quality.private_path_leakage_count == 2
    assert quality.secret_like_leakage_count == 2
    assert quality.forbidden_result_field_count == 1
    assert collect_public_retrieval_artifact_failures(quality) == [
        "public_raw_text_leakage",
        "private_path_leakage",
        "secret_like_leakage",
        "forbidden_result_fields",
    ]


def test_retrieval_comparison_report_records_no_improvement_claim() -> None:
    items = [_item("q-place", "place_fact", "child-a")]
    documents = [_doc("child-a")]
    results = [_result("q-place", "place_fact", "bm25", "child-a")]
    run = build_retrieval_experiment_run(
        method="bm25",
        top_k=1,
        items=items,
        documents=documents,
        results=results,
        result_path=Path("evals/results/retrieval_experiment_bm25_results.jsonl"),
    )
    quality = measure_public_retrieval_artifact_quality(
        report_version=RETRIEVAL_EXPERIMENT_REPORT_VERSION,
        run_id="retrieval-harness-bm25-test",
        result_rows=build_public_retrieval_result_rows(run_id=run.run_id, results=results),
        report_text="",
    )

    report = build_retrieval_comparison_report(
        dataset_path=Path("evals/datasets/retrieval_eval_seed.jsonl"),
        method_runs=[run],
        output_quality=quality,
        baseline_method="bm25",
    )

    assert report.report_version == RETRIEVAL_EXPERIMENT_REPORT_VERSION
    assert report.baseline_method == "bm25"
    assert report.metric_deltas[0].compared_method == "bm25"
    assert report.metric_deltas[0].recall_at_5_delta == 0.0
    assert "성능 개선 주장이 아니라" in report.qualitative_assessment["comparison_status"]


def test_public_path_alias_redacts_resolved_private_data(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(project_paths, "_REPOSITORY_ROOT", tmp_path)
    alias_path = tmp_path / "public_alias" / "retrieval_eval_dev.jsonl"
    private_resolved = (
        tmp_path
        / "private_data"
        / "evals"
        / "datasets"
        / "retrieval_eval_dev.jsonl"
    )
    original_resolve = Path.resolve

    def fake_resolve(self: Path, *args: object, **kwargs: object) -> Path:
        if self == alias_path:
            return private_resolved
        return original_resolve(self, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", fake_resolve)

    assert (
        public_path_alias(alias_path)
        == "<private retrieval eval dataset: retrieval_eval_dev.jsonl>"
    )


def test_retrieval_comparison_rejects_mismatched_experiment_invariants() -> None:
    items = [_item("q-place", "place_fact", "child-a")]
    documents = [_doc("child-a")]
    results = [_result("q-place", "place_fact", "bm25", "child-a")]
    run = build_retrieval_experiment_run(
        method="bm25",
        top_k=1,
        items=items,
        documents=documents,
        results=results,
        result_path=Path("evals/results/retrieval_experiment_bm25_results.jsonl"),
    )
    mismatched_top_k = run.model_copy(
        update={
            "method": "dense",
            "run_label": "dense-mismatch",
            "run_id": "dense-mismatch",
            "top_k": 2,
            "method_config_fingerprint": "dense-config",
            "method_config_summary": {"method": "dense", "top_k": 2},
        }
    )
    mismatched_dataset = run.model_copy(
        update={
            "method": "dense",
            "run_label": "dense-mismatch",
            "run_id": "dense-mismatch",
            "dataset_fingerprint": "different-dataset",
            "method_config_fingerprint": "dense-config",
            "method_config_summary": {"method": "dense", "top_k": 1},
        }
    )
    mismatched_corpus = run.model_copy(
        update={
            "method": "dense",
            "run_label": "dense-mismatch",
            "run_id": "dense-mismatch",
            "corpus_fingerprint": "different-corpus",
            "method_config_fingerprint": "dense-config",
            "method_config_summary": {"method": "dense", "top_k": 1},
        }
    )
    duplicate_run_label = run.model_copy(
        update={
            "run_id": "bm25-duplicate",
            "method_config_fingerprint": "bm25-alt-config",
            "method_config_summary": {"method": "bm25", "top_k": 1},
        }
    )
    missing_baseline = run.model_copy(
        update={
            "method": "dense",
            "run_label": "dense-only",
            "run_id": "dense-only",
            "method_config_fingerprint": "dense-config",
            "method_config_summary": {"method": "dense", "top_k": 1},
        }
    )
    quality = measure_public_retrieval_artifact_quality(
        report_version=RETRIEVAL_EXPERIMENT_REPORT_VERSION,
        run_id="retrieval-harness-test",
        result_rows=build_public_retrieval_result_rows(run_id=run.run_id, results=results),
        report_text="",
    )

    with pytest.raises(ValueError, match="same top_k"):
        build_retrieval_comparison_report(
            dataset_path=Path("evals/datasets/retrieval_eval_seed.jsonl"),
            method_runs=[run, mismatched_top_k],
            output_quality=quality,
            baseline_method="bm25",
        )
    with pytest.raises(ValueError, match="same dataset fingerprint"):
        build_retrieval_comparison_report(
            dataset_path=Path("evals/datasets/retrieval_eval_seed.jsonl"),
            method_runs=[run, mismatched_dataset],
            output_quality=quality,
            baseline_method="bm25",
        )
    with pytest.raises(ValueError, match="same corpus fingerprint"):
        build_retrieval_comparison_report(
            dataset_path=Path("evals/datasets/retrieval_eval_seed.jsonl"),
            method_runs=[run, mismatched_corpus],
            output_quality=quality,
            baseline_method="bm25",
        )
    with pytest.raises(ValueError, match="run labels must be unique"):
        build_retrieval_comparison_report(
            dataset_path=Path("evals/datasets/retrieval_eval_seed.jsonl"),
            method_runs=[run, duplicate_run_label],
            output_quality=quality,
            baseline_method="bm25",
        )
    with pytest.raises(ValueError, match="baseline method must be included"):
        build_retrieval_comparison_report(
            dataset_path=Path("evals/datasets/retrieval_eval_seed.jsonl"),
            method_runs=[missing_baseline],
            output_quality=quality,
            baseline_method="bm25",
        )
