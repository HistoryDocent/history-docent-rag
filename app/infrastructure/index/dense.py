from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal, Protocol

import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from app.core.project_paths import is_repository_private_write_path
from app.domain.retrieval import (
    QueryType,
    RetrievedCandidate,
    RetrievalDocument,
    RetrievalRunResult,
)
from app.infrastructure.index.bm25 import bm25_tokenize


DENSE_ENCODER_ID = "sklearn-tfidf-svd-v1"
DenseEncoderBackend = Literal["sklearn_tfidf_svd", "sentence_transformers"]


class DenseEncoder(Protocol):
    def fit_transform(self, texts: list[str]) -> np.ndarray:
        ...

    def transform(self, texts: list[str]) -> np.ndarray:
        ...


@dataclass(frozen=True)
class DenseRetrievalConfig:
    encoder_id: str = DENSE_ENCODER_ID
    backend: DenseEncoderBackend = "sklearn_tfidf_svd"
    model_name: str | None = None
    device: str = "cpu"
    batch_size: int = 16
    query_prefix: str = ""
    document_prefix: str = ""
    show_progress_bar: bool = False
    n_components: int = 128
    max_features: int = 50000
    ngram_min: int = 1
    ngram_max: int = 2
    normalize_embeddings: bool = True
    include_doc_title: bool = True
    random_state: int = 42

    def to_method_config_summary(
        self,
        *,
        top_k: int,
        embedding_dim: int,
    ) -> dict[str, str | int | float | bool]:
        summary: dict[str, str | int | float | bool] = {
            "method": "dense",
            "top_k": top_k,
            "encoder_id": self.encoder_id,
            "encoder_backend": self.backend,
            "embedding_dim": embedding_dim,
            "normalize_embeddings": self.normalize_embeddings,
            "include_doc_title": self.include_doc_title,
            "query_rewrite": False,
            "reranking": False,
        }
        if self.backend == "sklearn_tfidf_svd":
            summary.update(
                {
                    "n_components": self.n_components,
                    "max_features": self.max_features,
                    "ngram_range": f"{self.ngram_min}-{self.ngram_max}",
                    "random_state": self.random_state,
                }
            )
        else:
            summary.update(
                {
                    "model_name": self.model_name or self.encoder_id,
                    "device": self.device,
                    "batch_size": self.batch_size,
                    "query_prefix_enabled": bool(self.query_prefix),
                    "document_prefix_enabled": bool(self.document_prefix),
                }
            )
        return summary


@dataclass
class SklearnTfidfSvdEncoder:
    config: DenseRetrievalConfig
    vectorizer: TfidfVectorizer | None = None
    svd: TruncatedSVD | None = None

    def fit_transform(self, texts: list[str]) -> np.ndarray:
        if not texts:
            raise ValueError("dense encoder requires at least one text")
        self.vectorizer = TfidfVectorizer(
            tokenizer=bm25_tokenize,
            token_pattern=None,
            lowercase=False,
            max_features=self.config.max_features,
            ngram_range=(self.config.ngram_min, self.config.ngram_max),
        )
        tfidf = self.vectorizer.fit_transform(texts)
        feature_count = tfidf.shape[1]
        sample_count = tfidf.shape[0]
        component_count = min(
            self.config.n_components,
            max(0, feature_count - 1),
            max(0, sample_count - 1),
        )
        if component_count >= 1:
            self.svd = TruncatedSVD(
                n_components=component_count,
                random_state=self.config.random_state,
            )
            embeddings = self.svd.fit_transform(tfidf)
        else:
            self.svd = None
            embeddings = tfidf.toarray()
        return _normalize_if_needed(
            np.asarray(embeddings, dtype=np.float32),
            normalize_embeddings=self.config.normalize_embeddings,
        )

    def transform(self, texts: list[str]) -> np.ndarray:
        if self.vectorizer is None:
            raise ValueError("dense encoder must be fitted before transform")
        tfidf = self.vectorizer.transform(texts)
        if self.svd is not None:
            embeddings = self.svd.transform(tfidf)
        else:
            embeddings = tfidf.toarray()
        return _normalize_if_needed(
            np.asarray(embeddings, dtype=np.float32),
            normalize_embeddings=self.config.normalize_embeddings,
        )


@dataclass
class SentenceTransformerEncoder:
    config: DenseRetrievalConfig
    model: Any | None = None

    def fit_transform(self, texts: list[str]) -> np.ndarray:
        if not texts:
            raise ValueError("dense encoder requires at least one text")
        self.model = _load_sentence_transformer_model(self.config)
        return self._encode(texts, prefix=self.config.document_prefix)

    def transform(self, texts: list[str]) -> np.ndarray:
        if self.model is None:
            raise ValueError("dense encoder must be fitted before transform")
        return self._encode(texts, prefix=self.config.query_prefix)

    def _encode(self, texts: list[str], *, prefix: str) -> np.ndarray:
        if self.model is None:
            raise ValueError("dense encoder must be fitted before transform")
        prefixed_texts = [f"{prefix}{text}" for text in texts]
        embeddings = self.model.encode(
            prefixed_texts,
            batch_size=self.config.batch_size,
            convert_to_numpy=True,
            normalize_embeddings=self.config.normalize_embeddings,
            show_progress_bar=self.config.show_progress_bar,
        )
        return np.asarray(embeddings, dtype=np.float32)


@dataclass(frozen=True)
class DenseRetriever:
    documents: tuple[RetrievalDocument, ...]
    document_embeddings: np.ndarray
    encoder: DenseEncoder
    config: DenseRetrievalConfig
    embedding_cache_manifest: dict[str, str | int | float | bool] | None = None

    @classmethod
    def from_documents(
        cls,
        documents: list[RetrievalDocument],
        *,
        config: DenseRetrievalConfig | None = None,
        cache_dir: Path | None = None,
    ) -> "DenseRetriever":
        if not documents:
            raise ValueError("dense retriever requires at least one document")
        dense_config = config or DenseRetrievalConfig()
        encoder = _build_dense_encoder(dense_config)
        texts = [_build_searchable_text(document, dense_config) for document in documents]
        document_embeddings = encoder.fit_transform(texts)
        manifest = None
        if cache_dir is not None:
            if not is_repository_private_write_path(cache_dir):
                raise ValueError(
                    "dense embedding cache must be under repository private_data"
                )
            manifest = _write_embedding_cache(
                cache_dir=cache_dir,
                documents=documents,
                document_embeddings=document_embeddings,
                config=dense_config,
                embedding_dim=int(document_embeddings.shape[1]),
            )
        return cls(
            documents=tuple(documents),
            document_embeddings=document_embeddings,
            encoder=encoder,
            config=dense_config,
            embedding_cache_manifest=manifest,
        )

    @property
    def embedding_dim(self) -> int:
        return int(self.document_embeddings.shape[1])

    def search(
        self,
        *,
        query_id: str,
        query_type: QueryType,
        query_text: str,
        top_k: int,
    ) -> RetrievalRunResult:
        if top_k < 1:
            raise ValueError("top_k must be >= 1")
        started = time.perf_counter()
        query_embedding = self.encoder.transform([query_text])[0]
        scores = self.document_embeddings @ query_embedding
        candidate_indexes = sorted(
            range(len(scores)),
            key=lambda index: (float(scores[index]), self.documents[index].retrieval_doc_id),
            reverse=True,
        )[:top_k]
        candidates = [
            _candidate_from_document(
                rank=rank,
                document=self.documents[document_index],
                score=float(scores[document_index]),
            )
            for rank, document_index in enumerate(candidate_indexes, start=1)
        ]
        elapsed_ms = round((time.perf_counter() - started) * 1000, 6)
        return RetrievalRunResult(
            query_id=query_id,
            query_type=query_type,
            method="dense",
            candidates=candidates,
            latency_ms=elapsed_ms,
        )


def _build_searchable_text(
    document: RetrievalDocument,
    config: DenseRetrievalConfig,
) -> str:
    parts = [
        document.doc_title if config.include_doc_title else "",
        document.search_text or "",
        document.context_text or "",
    ]
    return "\n".join(part for part in parts if part)


def _candidate_from_document(
    *,
    rank: int,
    document: RetrievalDocument,
    score: float,
) -> RetrievedCandidate:
    return RetrievedCandidate(
        rank=rank,
        retrieval_doc_id=document.retrieval_doc_id,
        child_id=document.child_id,
        parent_id=document.parent_id,
        doc_id=document.doc_id,
        score=round(score, 6),
    )


def _normalize_if_needed(
    embeddings: np.ndarray,
    *,
    normalize_embeddings: bool,
) -> np.ndarray:
    if not normalize_embeddings:
        return embeddings
    return np.asarray(normalize(embeddings, norm="l2", copy=False), dtype=np.float32)


def _write_embedding_cache(
    *,
    cache_dir: Path,
    documents: list[RetrievalDocument],
    document_embeddings: np.ndarray,
    config: DenseRetrievalConfig,
    embedding_dim: int,
) -> dict[str, str | int | float | bool]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_key = _build_cache_key(
        documents=documents,
        config=config,
        embedding_dim=embedding_dim,
    )
    vector_path = cache_dir / f"{cache_key}.npz"
    manifest_path = cache_dir / f"{cache_key}.manifest.json"
    document_ids = np.asarray(
        [document.retrieval_doc_id for document in documents],
        dtype=object,
    )
    np.savez_compressed(
        vector_path,
        document_embeddings=document_embeddings,
        document_ids=document_ids,
    )
    manifest: dict[str, str | int | float | bool] = {
        "cache_version": "dense-embedding-cache/v1",
        "cache_key": cache_key,
        "encoder_id": config.encoder_id,
        "document_count": len(documents),
        "embedding_dim": embedding_dim,
        "document_fingerprint": _stable_digest(
            [
                {
                    "retrieval_doc_id": document.retrieval_doc_id,
                    "text_hash": document.text_hash,
                    "text_length": document.text_length,
                }
                for document in documents
            ]
        ),
        "vector_path_alias": f"<private dense embedding cache: {vector_path.name}>",
        "config_fingerprint": _stable_digest(asdict(config)),
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def _build_cache_key(
    *,
    documents: list[RetrievalDocument],
    config: DenseRetrievalConfig,
    embedding_dim: int,
) -> str:
    payload = {
        "config": asdict(config),
        "embedding_dim": embedding_dim,
        "documents": [
            {
                "retrieval_doc_id": document.retrieval_doc_id,
                "text_hash": document.text_hash,
                "text_length": document.text_length,
            }
            for document in documents
        ],
    }
    return f"dense-{_stable_digest(payload)}"


def _stable_digest(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]


def _build_dense_encoder(config: DenseRetrievalConfig) -> DenseEncoder:
    if config.backend == "sklearn_tfidf_svd":
        return SklearnTfidfSvdEncoder(config=config)
    if config.backend == "sentence_transformers":
        return SentenceTransformerEncoder(config=config)
    raise ValueError(f"unsupported dense encoder backend: {config.backend}")


def _load_sentence_transformer_model(config: DenseRetrievalConfig) -> Any:
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as error:
        raise RuntimeError(
            "sentence-transformers is required for neural dense retrieval. "
            "Install the project with the neural optional dependencies."
        ) from error
    return SentenceTransformer(config.model_name or config.encoder_id, device=config.device)
