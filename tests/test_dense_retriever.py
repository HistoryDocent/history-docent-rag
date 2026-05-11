from __future__ import annotations

from pathlib import Path

import pytest

from app.core import project_paths
from app.domain.data_contracts import PageSpan
from app.domain.retrieval import RetrievalDocument
import app.infrastructure.index.dense as dense_module
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


class _FakeSentenceTransformerModel:
    def encode(
        self,
        texts: list[str],
        *,
        batch_size: int,
        convert_to_numpy: bool,
        normalize_embeddings: bool,
        show_progress_bar: bool,
    ) -> object:
        del batch_size, convert_to_numpy, normalize_embeddings, show_progress_bar
        import numpy as np

        vectors = []
        for text in texts:
            if "경복궁" in text or "궁궐" in text:
                vectors.append([1.0, 0.0, 0.0])
            elif "시장" in text:
                vectors.append([0.0, 1.0, 0.0])
            else:
                vectors.append([0.0, 0.0, 1.0])
        return np.asarray(vectors, dtype=np.float32)


def test_sentence_transformer_dense_retriever_uses_prefixes_and_private_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(project_paths, "_REPOSITORY_ROOT", tmp_path)
    monkeypatch.setattr(
        dense_module,
        "_load_sentence_transformer_model",
        lambda config: _FakeSentenceTransformerModel(),
    )
    cache_dir = tmp_path / "private_data" / "embeddings"
    documents = [
        _doc("child-a", "경복궁 한양 정도전 궁궐 정치"),
        _doc("child-b", "시장 상업 물건 사람"),
        _doc("child-c", "지하철 막차 환승 시간표"),
    ]

    retriever = DenseRetriever.from_documents(
        documents,
        config=DenseRetrievalConfig(
            encoder_id="fake-neural",
            backend="sentence_transformers",
            model_name="fake/model",
            query_prefix="query: ",
            document_prefix="passage: ",
            batch_size=4,
        ),
        cache_dir=cache_dir,
    )
    result = retriever.search(
        query_id="q-palace",
        query_type="place_fact",
        query_text="경복궁 궁궐",
        top_k=2,
    )

    assert result.method == "dense"
    assert result.candidates[0].child_id == "child-a"
    assert retriever.embedding_dim == 3
    assert list(cache_dir.glob("dense-*.npz"))
    manifest = list(cache_dir.glob("dense-*.manifest.json"))[0].read_text(
        encoding="utf-8"
    )
    assert "fake-neural" in manifest
    assert "private source text" not in manifest
    assert str(tmp_path) not in manifest
