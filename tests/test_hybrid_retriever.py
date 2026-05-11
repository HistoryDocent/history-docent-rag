from __future__ import annotations

from dataclasses import dataclass

from app.domain.data_contracts import PageSpan
from app.domain.retrieval import (
    QueryType,
    RetrievedCandidate,
    RetrievalDocument,
    RetrievalRunResult,
)
from app.infrastructure.index.dense import DenseRetrievalConfig
from app.infrastructure.index.hybrid import HybridRetrievalConfig, HybridRetriever


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


def _candidate(identifier: str, *, rank: int, score: float) -> RetrievedCandidate:
    return RetrievedCandidate(
        rank=rank,
        retrieval_doc_id=identifier,
        child_id=identifier,
        parent_id=f"parent-{identifier}",
        doc_id=f"doc-{identifier}",
        score=score,
    )


@dataclass(frozen=True)
class _FakeRetriever:
    method: str
    candidates: list[RetrievedCandidate]

    def search(
        self,
        *,
        query_id: str,
        query_type: QueryType,
        query_text: str,
        top_k: int,
    ) -> RetrievalRunResult:
        return RetrievalRunResult(
            query_id=query_id,
            query_type=query_type,
            method=self.method,  # type: ignore[arg-type]
            candidates=self.candidates[:top_k],
            latency_ms=1.0,
        )


@dataclass(frozen=True)
class _FakeDenseRetriever(_FakeRetriever):
    embedding_dim: int = 8


def test_hybrid_weighted_alpha_controls_bm25_dense_balance() -> None:
    documents = [_doc("doc-a"), _doc("doc-b")]
    bm25 = _FakeRetriever(
        method="bm25",
        candidates=[
            _candidate("doc-a", rank=1, score=10.0),
            _candidate("doc-b", rank=2, score=1.0),
        ],
    )
    dense = _FakeDenseRetriever(
        method="dense",
        candidates=[
            _candidate("doc-b", rank=1, score=1.0),
            _candidate("doc-a", rank=2, score=0.2),
        ],
    )

    bm25_weighted = HybridRetriever(
        documents=tuple(documents),
        bm25_retriever=bm25,  # type: ignore[arg-type]
        dense_retriever=dense,  # type: ignore[arg-type]
        config=HybridRetrievalConfig(method="hybrid_weighted", alpha=0.3),
    )
    dense_weighted = HybridRetriever(
        documents=tuple(documents),
        bm25_retriever=bm25,  # type: ignore[arg-type]
        dense_retriever=dense,  # type: ignore[arg-type]
        config=HybridRetrievalConfig(method="hybrid_weighted", alpha=0.7),
    )

    bm25_result = bm25_weighted.search(
        query_id="q1",
        query_type="place_fact",
        query_text="경복궁",
        top_k=2,
    )
    dense_result = dense_weighted.search(
        query_id="q1",
        query_type="place_fact",
        query_text="경복궁",
        top_k=2,
    )

    assert bm25_result.method == "hybrid_weighted"
    assert [candidate.retrieval_doc_id for candidate in bm25_result.candidates] == [
        "doc-a",
        "doc-b",
    ]
    assert [candidate.retrieval_doc_id for candidate in dense_result.candidates] == [
        "doc-b",
        "doc-a",
    ]


def test_hybrid_rrf_returns_union_with_deterministic_ranks() -> None:
    documents = [_doc("doc-a"), _doc("doc-b"), _doc("doc-c")]
    retriever = HybridRetriever(
        documents=tuple(documents),
        bm25_retriever=_FakeRetriever(
            method="bm25",
            candidates=[
                _candidate("doc-a", rank=1, score=2.0),
                _candidate("doc-b", rank=2, score=1.0),
            ],
        ),  # type: ignore[arg-type]
        dense_retriever=_FakeDenseRetriever(
            method="dense",
            candidates=[
                _candidate("doc-c", rank=1, score=0.9),
                _candidate("doc-a", rank=2, score=0.8),
            ],
        ),  # type: ignore[arg-type]
        config=HybridRetrievalConfig(method="hybrid_rrf", candidate_k=2, rrf_k=60),
    )

    result = retriever.search(
        query_id="q1",
        query_type="relationship",
        query_text="정도전 관계",
        top_k=3,
    )

    assert result.method == "hybrid_rrf"
    assert [candidate.rank for candidate in result.candidates] == [1, 2, 3]
    assert {candidate.retrieval_doc_id for candidate in result.candidates} == {
        "doc-a",
        "doc-b",
        "doc-c",
    }


def test_hybrid_config_summary_records_dense_boundary() -> None:
    config = HybridRetrievalConfig(
        method="hybrid_rrf",
        dense_config=DenseRetrievalConfig(n_components=32),
    )

    summary = config.to_method_config_summary(top_k=5, embedding_dim=32)

    assert summary["method"] == "hybrid_rrf"
    assert summary["fusion"] == "reciprocal_rank_fusion"
    assert summary["candidate_k"] == 50
    assert summary["rrf_k"] == 60
    assert summary["dense_encoder_id"] == "sklearn-tfidf-svd-v1"
    assert summary["dense_embedding_dim"] == 32
