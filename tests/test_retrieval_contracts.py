from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.domain.chunking import ChildChunk, ChunkSourceRef
from app.domain.data_contracts import ElementReference, PageSpan
from app.domain.retrieval import (
    RetrievedCandidate,
    RetrievalDocument,
    RetrievalEvalItem,
    RetrievalJudgment,
    RetrievalQuery,
    RetrievalRunResult,
    build_retrieval_document_from_child,
    compute_retrieval_metrics,
    load_retrieval_eval_jsonl,
)


def _page_span() -> PageSpan:
    return PageSpan(
        page_local_start=1,
        page_local_end=1,
        page_global_start=10,
        page_global_end=10,
    )


def _child_chunk() -> ChildChunk:
    return ChildChunk(
        child_id="parent-doc-00001-00-child-0000",
        parent_id="parent-doc-00001-00",
        doc_id="doc-one",
        doc_title="Doc One",
        parser_run_id="parser-run",
        source_block_ids=["block-one"],
        context_block_ids=["heading-one"],
        page_span=_page_span(),
        text_hash="a" * 64,
        text_length=350,
        element_type_mix={"paragraph": 1},
        citation_refs=[
            ChunkSourceRef(
                block_id="block-one",
                doc_id="doc-one",
                element_type="paragraph",
                page_span=_page_span(),
                element_refs=[
                    ElementReference(
                        element_id="element-one",
                        element_type="paragraph",
                        element_index=1,
                    )
                ],
                source_file_name="doc-one.pdf",
                text_hash="b" * 64,
                text_length=350,
                quality_flags=[],
            )
        ],
        quality_flags=[],
        public_allowed=False,
        text="private body text",
        context_text="private heading text",
    )


def _eval_item() -> RetrievalEvalItem:
    return RetrievalEvalItem(
        query=RetrievalQuery(
            query_id="q-one",
            query_type="place_fact",
            query_text="경복궁 근거를 찾아줘",
            language="ko",
            expected_behavior="retrieve",
        ),
        judgments=[
            RetrievalJudgment(
                query_id="q-one",
                relevant_child_ids=["child-hit"],
                relevant_parent_ids=["parent-hit"],
                relevant_doc_ids=["doc-hit"],
                relevance_grade=3,
                rationale_summary="expected target ids only",
            )
        ],
    )


def test_build_retrieval_document_from_child_preserves_citation_metadata() -> None:
    child = _child_chunk()

    document = build_retrieval_document_from_child(child, include_private_text=True)

    assert document.retrieval_doc_id == child.child_id
    assert document.child_id == child.child_id
    assert document.parent_id == child.parent_id
    assert document.citation_block_ids == ["block-one"]
    assert document.search_text == "private body text"
    assert document.context_text == "private heading text"


def test_public_retrieval_document_rejects_private_text() -> None:
    with pytest.raises(ValidationError):
        RetrievalDocument(
            retrieval_doc_id="child-one",
            child_id="child-one",
            parent_id="parent-one",
            doc_id="doc-one",
            doc_title="Doc One",
            page_span=_page_span(),
            source_block_ids=["block-one"],
            text_hash="a" * 64,
            text_length=10,
            element_type_mix={"paragraph": 1},
            citation_block_ids=["block-one"],
            public_allowed=True,
            search_text="must not be public",
        )


def test_retrieval_eval_item_validates_expected_behavior() -> None:
    with pytest.raises(ValidationError):
        RetrievalEvalItem(
            query=RetrievalQuery(
                query_id="q-bad",
                query_type="no_answer",
                query_text="실시간 막차 시간 알려줘",
                language="ko",
                expected_behavior="abstain",
            ),
            judgments=[
                RetrievalJudgment(
                    query_id="q-bad",
                    relevant_doc_ids=["doc-one"],
                    rationale_summary="no-answer must not include positive judgment",
                )
            ],
        )


def test_load_retrieval_eval_jsonl_reports_line_number(tmp_path: Path) -> None:
    path = tmp_path / "bad.jsonl"
    path.write_text('{"query": {}\n', encoding="utf-8")

    with pytest.raises(ValueError, match="line 1"):
        load_retrieval_eval_jsonl(path)


def test_compute_retrieval_metrics_uses_same_items_for_bm25_and_later_methods() -> None:
    item = _eval_item()
    abstain_item = RetrievalEvalItem(
        query=RetrievalQuery(
            query_id="q-no-answer",
            query_type="no_answer",
            query_text="오늘 막차 시간 알려줘",
            language="ko",
            expected_behavior="abstain",
        ),
        judgments=[],
    )
    results = [
        RetrievalRunResult(
            query_id="q-one",
            query_type="place_fact",
            method="bm25",
            latency_ms=15,
            candidates=[
                RetrievedCandidate(
                    rank=1,
                    retrieval_doc_id="miss",
                    child_id="child-miss",
                    parent_id="parent-miss",
                    doc_id="doc-miss",
                    score=3.0,
                ),
                RetrievedCandidate(
                    rank=2,
                    retrieval_doc_id="hit",
                    child_id="child-hit",
                    parent_id="parent-hit",
                    doc_id="doc-hit",
                    score=2.0,
                ),
            ],
        ),
        RetrievalRunResult(
            query_id="q-no-answer",
            query_type="no_answer",
            method="bm25",
            latency_ms=30,
            candidates=[],
        ),
    ]

    summary = compute_retrieval_metrics(
        items=[item, abstain_item],
        results=results,
        method="bm25",
    )

    assert summary.query_count == 2
    assert summary.retrieve_query_count == 1
    assert summary.abstain_query_count == 1
    assert summary.result_count == 2
    assert summary.recall_at_1 == 0.0
    assert summary.recall_at_3 == 1.0
    assert summary.recall_at_5 == 1.0
    assert summary.mrr == 0.5
    assert summary.ndcg_at_5 > 0
    assert summary.latency_p50_ms == 15
    assert summary.latency_p95_ms == 30
    assert summary.abstain_with_candidate_count == 0


def test_ndcg_supports_multiple_relevant_child_ids_in_one_judgment() -> None:
    item = RetrievalEvalItem(
        query=RetrievalQuery(
            query_id="q-multi",
            query_type="relationship",
            query_text="경복궁과 한양 천도 관계를 찾아줘",
            language="ko",
            expected_behavior="retrieve",
        ),
        judgments=[
            RetrievalJudgment(
                query_id="q-multi",
                relevant_child_ids=["child-a", "child-b"],
                relevant_parent_ids=["parent-a"],
                relevant_doc_ids=["doc-a"],
                relevance_grade=3,
                rationale_summary="multiple relevant child ids can satisfy one relationship query",
            )
        ],
    )
    result = RetrievalRunResult(
        query_id="q-multi",
        query_type="relationship",
        method="bm25",
        latency_ms=20,
        candidates=[
            RetrievedCandidate(
                rank=1,
                retrieval_doc_id="child-a",
                child_id="child-a",
                parent_id="parent-a",
                doc_id="doc-a",
                score=10.0,
            ),
            RetrievedCandidate(
                rank=2,
                retrieval_doc_id="child-b",
                child_id="child-b",
                parent_id="parent-a",
                doc_id="doc-a",
                score=9.0,
            ),
        ],
    )

    summary = compute_retrieval_metrics(items=[item], results=[result], method="bm25")

    assert summary.ndcg_at_5 == 1.0


def test_compute_retrieval_metrics_rejects_duplicate_query_results() -> None:
    item = _eval_item()
    result = RetrievalRunResult(
        query_id="q-one",
        query_type="place_fact",
        method="bm25",
        latency_ms=15,
        candidates=[],
    )

    with pytest.raises(ValueError, match="unique by method and query_id"):
        compute_retrieval_metrics(
            items=[item],
            results=[result, result],
            method="bm25",
        )
