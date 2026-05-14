from __future__ import annotations

import json
from pathlib import Path

from app.domain.data_contracts import PageSpan
from app.domain.retrieval import (
    FORBIDDEN_PUBLIC_EVAL_FIELDS,
    RetrievedCandidate,
    RetrievalDocument,
    RetrievalEvalItem,
    RetrievalRunResult,
)
from pipelines.run_graphrag_lite_relationship_input_only import (
    BASELINE_STRATEGY_ID,
    GRAPHRAG_LITE_RELATIONSHIP_INPUT_ONLY_REPORT_VERSION,
    collect_graphrag_lite_relationship_input_only_failures,
    load_baseline_results_from_public_rows,
    run_graphrag_lite_relationship_input_only,
)


def test_graphrag_lite_relationship_input_only_writes_public_safe_report(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "graphrag_lite_relationship_input_only_report.md"
    rows_path = tmp_path / "graphrag_lite_relationship_input_only_rows.jsonl"
    items = _eval_items()
    documents = _documents()
    baseline_results = _baseline_results()

    report = run_graphrag_lite_relationship_input_only(
        report_path=report_path,
        result_rows_path=rows_path,
        items=items,
        documents=documents,
        baseline_results=baseline_results,
        expected_relationship_dev_query_count=2,
    )
    markdown = report_path.read_text(encoding="utf-8")
    rows = [json.loads(line) for line in rows_path.read_text(encoding="utf-8").splitlines()]

    assert report.report_version == GRAPHRAG_LITE_RELATIONSHIP_INPUT_ONLY_REPORT_VERSION
    assert report.summary.relationship_dev_query_count == 2
    assert report.summary.expected_relationship_dev_query_count == 2
    assert report.summary.baseline_count == 1
    assert report.summary.candidate_count == 2
    assert report.summary.solar_call_count == 0
    assert report.summary.min_citation_recoverability == 1.0
    assert report.output_quality.public_raw_text_leakage_count == 0
    assert report.output_quality.private_path_leakage_count == 0
    assert report.output_quality.secret_like_leakage_count == 0
    assert collect_graphrag_lite_relationship_input_only_failures(report) == []
    assert {row.strategy_id for row in report.metric_rows} == {
        BASELINE_STRATEGY_ID,
        "graphrag_lite_entity_path_v1",
        "graphrag_lite_community_hint_v1",
    }
    assert "정도전" not in markdown
    assert "훈민정음" not in markdown
    assert all(FORBIDDEN_PUBLIC_EVAL_FIELDS.isdisjoint(row.keys()) for row in rows)


def test_load_baseline_results_from_public_rows_filters_relationship_items(
    tmp_path: Path,
) -> None:
    rows_path = tmp_path / "baseline_rows.jsonl"
    rows = [
        {
            "run_id": "run-one",
            "method": "hybrid_weighted",
            "query_id": "q-rel-1",
            "query_type": "relationship",
            "latency_ms": 12.5,
            "rank": 1,
            "retrieval_doc_id": "child-palace",
            "child_id": "child-palace",
            "parent_id": "parent-palace",
            "doc_id": "doc-palace",
            "score": 0.9,
        },
        {
            "run_id": "run-one",
            "method": "hybrid_weighted",
            "query_id": "q-place-fact",
            "query_type": "place_fact",
            "latency_ms": 11.0,
            "rank": 1,
            "retrieval_doc_id": "child-other",
            "child_id": "child-other",
            "parent_id": "parent-other",
            "doc_id": "doc-other",
            "score": 0.8,
        },
    ]
    rows_path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )

    results = load_baseline_results_from_public_rows(
        path=rows_path,
        items=[_eval_items()[0]],
    )

    assert len(results) == 1
    assert results[0].query_id == "q-rel-1"
    assert results[0].query_type == "relationship"
    assert results[0].latency_ms == 12.5
    assert [candidate.child_id for candidate in results[0].candidates] == ["child-palace"]


def _documents() -> list[RetrievalDocument]:
    return [
        _document(
            child_id="child-palace",
            parent_id="parent-palace",
            doc_id="doc-palace",
            search_text="정도전 한양 천도 경복궁 궁궐 정치 관계",
        ),
        _document(
            child_id="child-king",
            parent_id="parent-king",
            doc_id="doc-king",
            search_text="세종 집현전 훈민정음 제도 개혁 관계",
        ),
        _document(
            child_id="child-market",
            parent_id="parent-market",
            doc_id="doc-market",
            search_text="종로 시장 상업 거리 생활 문화",
        ),
    ]


def _document(
    *,
    child_id: str,
    parent_id: str,
    doc_id: str,
    search_text: str,
) -> RetrievalDocument:
    return RetrievalDocument(
        retrieval_doc_id=child_id,
        child_id=child_id,
        parent_id=parent_id,
        doc_id=doc_id,
        doc_title=doc_id,
        page_span=PageSpan(
            page_local_start=1,
            page_local_end=1,
            page_global_start=1,
            page_global_end=1,
        ),
        source_block_ids=[f"block-{child_id}"],
        context_block_ids=[],
        text_hash="a" * 64,
        text_length=len(search_text),
        element_type_mix={"paragraph": 1},
        citation_block_ids=[f"block-{child_id}"],
        quality_flags=[],
        public_allowed=False,
        search_text=search_text,
        context_text=None,
    )


def _eval_items() -> list[RetrievalEvalItem]:
    return [
        RetrievalEvalItem.model_validate(
            _eval_item_payload(
                query_id="q-rel-1",
                query_text="정도전과 한양 천도 관계",
                child_id="child-palace",
                parent_id="parent-palace",
                doc_id="doc-palace",
            )
        ),
        RetrievalEvalItem.model_validate(
            _eval_item_payload(
                query_id="q-rel-2",
                query_text="세종과 집현전의 관계",
                child_id="child-king",
                parent_id="parent-king",
                doc_id="doc-king",
            )
        ),
    ]


def _eval_item_payload(
    *,
    query_id: str,
    query_text: str,
    child_id: str,
    parent_id: str,
    doc_id: str,
) -> dict[str, object]:
    return {
        "dataset_version": "retrieval-eval-dataset/v2",
        "query": {
            "query_id": query_id,
            "query_type": "relationship",
            "query_text": query_text,
            "language": "ko",
            "expected_behavior": "retrieve",
            "user_context": None,
            "public_allowed": True,
        },
        "judgments": [
            {
                "query_id": query_id,
                "relevant_child_ids": [child_id],
                "relevant_parent_ids": [parent_id],
                "relevant_doc_ids": [doc_id],
                "relevance_grade": 3,
                "rationale_summary": "target ids only",
                "public_allowed": True,
            }
        ],
        "metadata": {
            "split": "dev",
            "difficulty": "medium",
            "place_ids": [],
            "requires_context": False,
            "answerability": "answerable",
            "review_status": "reviewed",
        },
    }


def _baseline_results() -> list[RetrievalRunResult]:
    return [
        RetrievalRunResult(
            query_id="q-rel-1",
            query_type="relationship",
            method="hybrid_weighted",
            candidates=[
                _candidate(
                    rank=1,
                    child_id="child-market",
                    parent_id="parent-market",
                    doc_id="doc-market",
                    score=0.8,
                ),
                _candidate(
                    rank=2,
                    child_id="child-palace",
                    parent_id="parent-palace",
                    doc_id="doc-palace",
                    score=0.7,
                ),
            ],
            latency_ms=10.0,
        ),
        RetrievalRunResult(
            query_id="q-rel-2",
            query_type="relationship",
            method="hybrid_weighted",
            candidates=[
                _candidate(
                    rank=1,
                    child_id="child-market",
                    parent_id="parent-market",
                    doc_id="doc-market",
                    score=0.8,
                ),
                _candidate(
                    rank=2,
                    child_id="child-king",
                    parent_id="parent-king",
                    doc_id="doc-king",
                    score=0.7,
                ),
            ],
            latency_ms=11.0,
        ),
    ]


def _candidate(
    *,
    rank: int,
    child_id: str,
    parent_id: str,
    doc_id: str,
    score: float,
) -> RetrievedCandidate:
    return RetrievedCandidate(
        rank=rank,
        retrieval_doc_id=child_id,
        child_id=child_id,
        parent_id=parent_id,
        doc_id=doc_id,
        score=score,
    )
