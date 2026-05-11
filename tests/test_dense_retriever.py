from __future__ import annotations

from pathlib import Path

import pytest

from app.core import project_paths
from app.domain.data_contracts import PageSpan
from app.domain.retrieval import RetrievalDocument
from app.infrastructure.index.dense import DenseRetrievalConfig, DenseRetriever


def _doc(identifier: str, text: str) -> RetrievalDocument:
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
        context_block_ids=[],
        text_hash=identifier[-1] * 64,
        text_length=len(text),
        element_type_mix={"paragraph": 1},
        citation_block_ids=[f"block-{identifier}"],
        quality_flags=[],
        public_allowed=False,
        search_text=text,
        context_text=None,
    )


def test_dense_retriever_returns_ranked_candidates_and_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(project_paths, "_REPOSITORY_ROOT", tmp_path)
    cache_dir = tmp_path / "private_data" / "embeddings"
    documents = [
        _doc("child-a", "경복궁 한양 정도전 궁궐 정치"),
        _doc("child-b", "시장 상업 물건 사람"),
        _doc("child-c", "지하철 막차 환승 시간표"),
    ]

    retriever = DenseRetriever.from_documents(
        documents,
        config=DenseRetrievalConfig(n_components=2, max_features=100),
        cache_dir=cache_dir,
    )
    result = retriever.search(
        query_id="q-palace",
        query_type="place_fact",
        query_text="경복궁 궁궐 정도전",
        top_k=2,
    )

    assert result.method == "dense"
    assert result.candidates[0].child_id == "child-a"
    assert result.candidates[0].rank == 1
    assert len(result.candidates) == 2
    assert retriever.embedding_dim >= 1
    assert list(cache_dir.glob("dense-*.npz"))
    assert list(cache_dir.glob("dense-*.manifest.json"))


def test_dense_retriever_rejects_invalid_inputs() -> None:
    try:
        DenseRetriever.from_documents([])
    except ValueError as error:
        assert "at least one document" in str(error)
    else:
        raise AssertionError("DenseRetriever accepted empty documents")

    retriever = DenseRetriever.from_documents(
        [_doc("child-a", "경복궁 한양")],
        config=DenseRetrievalConfig(n_components=2, max_features=100),
    )

    try:
        retriever.search(
            query_id="q",
            query_type="place_fact",
            query_text="경복궁",
            top_k=0,
        )
    except ValueError as error:
        assert "top_k" in str(error)
    else:
        raise AssertionError("DenseRetriever accepted invalid top_k")


def test_dense_retriever_rejects_public_embedding_cache_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(project_paths, "_REPOSITORY_ROOT", tmp_path)

    with pytest.raises(ValueError, match="repository private_data"):
        DenseRetriever.from_documents(
            [_doc("child-a", "경복궁 한양")],
            config=DenseRetrievalConfig(n_components=2, max_features=100),
            cache_dir=tmp_path / "embeddings",
        )

    assert not (tmp_path / "embeddings").exists()
