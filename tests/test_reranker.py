from __future__ import annotations

from dataclasses import dataclass

from app.domain.data_contracts import PageSpan
from app.domain.retrieval import RetrievalDocument, RetrievalRunResult
from app.infrastructure.index.reranker import (
    RerankerConfig,
    RerankingRetriever,
)


def _document(*, doc_id: str, text: str) -> RetrievalDocument:
    return RetrievalDocument(
        retrieval_doc_id=doc_id,
        child_id=doc_id,
        parent_id=f"parent-{doc_id}",
        doc_id=f"doc-{doc_id}",
        doc_title=f"title-{doc_id}",
        page_span=PageSpan(
            page_local_start=1,
            page_local_end=1,
            page_global_start=1,
            page_global_end=1,
        ),
        source_block_ids=[f"block-{doc_id}"],
        text_hash="a" * 64,
        text_length=len(text),
        element_type_mix={"paragraph": 1},
        citation_block_ids=[f"block-{doc_id}"],
        public_allowed=False,
        search_text=text,
    )


@dataclass(frozen=True)
class _FakeBaseRetriever:
    documents: tuple[RetrievalDocument, ...]

    def search(
        self,
        *,
        query_id: str,
        query_type: str,
        query_text: str,
        top_k: int,
    ) -> RetrievalRunResult:
        del query_text
        return RetrievalRunResult(
            query_id=query_id,
            query_type=query_type,
            method="dense",
            candidates=[
                {
                    "rank": rank,
                    "retrieval_doc_id": document.retrieval_doc_id,
                    "child_id": document.child_id,
                    "parent_id": document.parent_id,
                    "doc_id": document.doc_id,
                    "score": float(100 - rank),
                }
                for rank, document in enumerate(self.documents[:top_k], start=1)
            ],
            latency_ms=1.0,
        )


@dataclass(frozen=True)
class _FakeReranker:
    def score(self, query_text: str, documents: list[RetrievalDocument]) -> list[float]:
        del query_text
        return [10.0 if "정답" in (document.search_text or "") else 1.0 for document in documents]


def test_reranking_reorders_candidates_and_preserves_result_contract() -> None:
    first = _document(doc_id="child-first", text="무관한 후보")
    second = _document(doc_id="child-second", text="정답 후보")
    retriever = RerankingRetriever(
        documents=(first, second),
        base_retriever=_FakeBaseRetriever((first, second)),
        base_method="dense",
        reranker=_FakeReranker(),
        config=RerankerConfig(candidate_k=2),
    )

    result = retriever.search(
        query_id="q-one",
        query_type="place_fact",
        query_text="정답",
        top_k=1,
    )

    assert result.method == "dense"
    assert result.candidates[0].retrieval_doc_id == "child-second"
    assert result.candidates[0].rank == 1
    assert result.candidates[0].score == 10.0


def test_reranker_config_summary_marks_reranking_enabled() -> None:
    summary = RerankerConfig(candidate_k=30).to_method_config_summary(
        base_summary={
            "method": "dense",
            "top_k": 30,
            "encoder_id": "multilingual-e5-small",
            "reranking": False,
        },
        top_k=5,
        base_run_label="dense_multilingual_e5_small",
    )

    assert summary["top_k"] == 5
    assert summary["retrieval_candidate_k"] == 30
    assert summary["reranking"] is True
    assert summary["base_run_label"] == "dense_multilingual_e5_small"
    assert summary["reranker_model_name"] == "BAAI/bge-reranker-v2-m3"
