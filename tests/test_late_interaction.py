from __future__ import annotations

from dataclasses import dataclass

import torch

from app.domain.data_contracts import PageSpan
from app.domain.retrieval import (
    RetrievedCandidate,
    RetrievalDocument,
    RetrievalRunResult,
)
from app.infrastructure.index.late_interaction import (
    LateInteractionConfig,
    LateInteractionRerankingRetriever,
    LateInteractionScoreBatch,
    _maxsim_scores,
)


def test_maxsim_scores_average_query_token_matches() -> None:
    query_embedding = torch.tensor(
        [
            [1.0, 0.0],
            [0.0, 1.0],
        ],
    )
    query_mask = torch.tensor([True, True])
    document_embeddings = torch.tensor(
        [
            [
                [1.0, 0.0],
                [0.0, 1.0],
            ],
            [
                [1.0, 0.0],
                [1.0, 0.0],
            ],
        ],
    )
    document_mask = torch.tensor(
        [
            [True, True],
            [True, True],
        ],
    )

    scores = _maxsim_scores(
        query_embedding=query_embedding,
        query_mask=query_mask,
        document_embeddings=document_embeddings,
        document_mask=document_mask,
    )

    assert scores.tolist() == [1.0, 0.5]


def test_late_interaction_reranking_reorders_base_candidates() -> None:
    documents = [
        _document("child-a", "parent-a", "doc-a", "first"),
        _document("child-b", "parent-b", "doc-b", "second"),
    ]
    retriever = LateInteractionRerankingRetriever(
        documents=tuple(documents),
        base_retriever=_FakeBaseRetriever(),
        base_method="dense",
        scorer=_FakeLateInteractionScorer(),
        config=LateInteractionConfig(candidate_k=2),
    )

    result = retriever.search(
        query_id="q-1",
        query_type="place_story",
        query_text="query",
        top_k=2,
    )

    assert [candidate.child_id for candidate in result.candidates] == [
        "child-b",
        "child-a",
    ]
    assert result.method == "dense"
    assert retriever.last_cuda_memory_peak_mb == 12.5


@dataclass(frozen=True)
class _FakeBaseRetriever:
    def search(
        self,
        *,
        query_id: str,
        query_type: str,
        query_text: str,
        top_k: int,
    ) -> RetrievalRunResult:
        del query_text
        candidates = [
            RetrievedCandidate(
                rank=1,
                retrieval_doc_id="child-a",
                child_id="child-a",
                parent_id="parent-a",
                doc_id="doc-a",
                score=0.7,
            ),
            RetrievedCandidate(
                rank=2,
                retrieval_doc_id="child-b",
                child_id="child-b",
                parent_id="parent-b",
                doc_id="doc-b",
                score=0.6,
            ),
        ][:top_k]
        return RetrievalRunResult(
            query_id=query_id,
            query_type=query_type,  # type: ignore[arg-type]
            method="dense",
            candidates=candidates,
            latency_ms=1.0,
        )


@dataclass(frozen=True)
class _FakeLateInteractionScorer:
    def score(
        self,
        query_text: str,
        documents: list[RetrievalDocument],
    ) -> LateInteractionScoreBatch:
        del query_text
        score_by_id = {"child-a": 0.1, "child-b": 0.9}
        return LateInteractionScoreBatch(
            scores=[score_by_id[document.child_id] for document in documents],
            cuda_memory_peak_mb=12.5,
        )


def _document(
    child_id: str,
    parent_id: str,
    doc_id: str,
    text: str,
) -> RetrievalDocument:
    return RetrievalDocument(
        retrieval_doc_id=child_id,
        child_id=child_id,
        parent_id=parent_id,
        doc_id=doc_id,
        doc_title="doc title",
        page_span=PageSpan(
            page_local_start=1,
            page_local_end=1,
            page_global_start=1,
            page_global_end=1,
        ),
        source_block_ids=[f"block-{child_id}"],
        text_hash="a" * 32,
        text_length=len(text),
        element_type_mix={"paragraph": 1},
        citation_block_ids=[f"block-{child_id}"],
        search_text=text,
    )
