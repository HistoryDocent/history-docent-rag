from __future__ import annotations

from app.domain.data_contracts import PageSpan
from app.domain.retrieval import RetrievalDocument
from app.infrastructure.index.bm25 import Bm25Retriever, bm25_tokenize


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
        public_allowed=False,
        search_text=search_text,
    )


def test_bm25_tokenize_keeps_korean_and_ascii_terms() -> None:
    tokens = bm25_tokenize("경복궁과 Gyeongbokgung, 한양-천도 1394년")

    assert "경복궁과" in tokens
    assert "gyeongbokgung" in tokens
    assert "한양" in tokens
    assert "천도" in tokens
    assert "1394년" in tokens


def test_bm25_retriever_ranks_matching_document_first() -> None:
    retriever = Bm25Retriever.from_documents(
        [
            _document(
                child_id="child-palace",
                parent_id="parent-palace",
                doc_id="doc-joseon",
                search_text="경복궁 한양 천도 정도전 조선 건국 왕권",
            ),
            _document(
                child_id="child-modern",
                parent_id="parent-modern",
                doc_id="doc-modern",
                search_text="근대 도시 철도 신문 학교",
            ),
        ]
    )

    result = retriever.search(
        query_id="q-one",
        query_type="relationship",
        query_text="경복궁 한양 천도 정도전",
        top_k=2,
    )

    assert result.method == "bm25"
    assert result.query_id == "q-one"
    assert result.candidates[0].child_id == "child-palace"
    assert result.candidates[0].rank == 1
    assert result.candidates[1].rank == 2


def test_bm25_retriever_uses_metadata_without_returning_private_text() -> None:
    retriever = Bm25Retriever.from_documents(
        [
            _document(
                child_id="child-one",
                parent_id="parent-one",
                doc_id="doc-one",
                search_text="private source text 경복궁",
            )
        ]
    )

    result = retriever.search(
        query_id="q-one",
        query_type="place_fact",
        query_text="경복궁",
        top_k=1,
    )
    candidate_payload = result.candidates[0].model_dump()

    assert "private source text" not in str(candidate_payload)
    assert set(candidate_payload) == {
        "rank",
        "retrieval_doc_id",
        "child_id",
        "parent_id",
        "doc_id",
        "score",
    }
