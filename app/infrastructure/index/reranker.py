from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Literal, Protocol

import numpy as np

from app.domain.retrieval import (
    QueryType,
    RetrievedCandidate,
    RetrievalDocument,
    RetrievalMethod,
    RetrievalRunResult,
)
from app.infrastructure.index.device import resolve_torch_device


RerankerBackend = Literal["sentence_transformers_cross_encoder"]


class Retriever(Protocol):
    def search(
        self,
        *,
        query_id: str,
        query_type: QueryType,
        query_text: str,
        top_k: int,
    ) -> RetrievalRunResult:
        ...


class PairwiseReranker(Protocol):
    def score(self, query_text: str, documents: list[RetrievalDocument]) -> list[float]:
        ...


@dataclass(frozen=True)
class RerankerConfig:
    reranker_id: str = "bge-reranker-v2-m3"
    backend: RerankerBackend = "sentence_transformers_cross_encoder"
    model_name: str = "BAAI/bge-reranker-v2-m3"
    device: str = "auto"
    batch_size: int = 16
    candidate_k: int = 30
    include_doc_title: bool = True
    include_context_text: bool = True
    max_passage_chars: int = 1800
    show_progress_bar: bool = False

    def __post_init__(self) -> None:
        if self.candidate_k < 1:
            raise ValueError("candidate_k must be >= 1")
        if self.batch_size < 1:
            raise ValueError("batch_size must be >= 1")
        if self.max_passage_chars < 1:
            raise ValueError("max_passage_chars must be >= 1")

    def to_method_config_summary(
        self,
        *,
        base_summary: dict[str, str | int | float | bool],
        top_k: int,
        base_run_label: str,
    ) -> dict[str, str | int | float | bool]:
        summary = dict(base_summary)
        summary.update(
            {
                "top_k": top_k,
                "base_run_label": base_run_label,
                "retrieval_candidate_k": self.candidate_k,
                "reranking": True,
                "reranker_id": self.reranker_id,
                "reranker_backend": self.backend,
                "reranker_model_name": self.model_name,
                "reranker_device": self.device,
                "reranker_resolved_device": resolve_torch_device(self.device),
                "reranker_batch_size": self.batch_size,
                "reranker_include_doc_title": self.include_doc_title,
                "reranker_include_context_text": self.include_context_text,
                "reranker_max_passage_chars": self.max_passage_chars,
            }
        )
        return summary


@dataclass(frozen=True)
class CrossEncoderReranker:
    config: RerankerConfig
    model: Any

    @classmethod
    def from_config(cls, config: RerankerConfig) -> "CrossEncoderReranker":
        return cls(config=config, model=_load_cross_encoder_model(config))

    def score(self, query_text: str, documents: list[RetrievalDocument]) -> list[float]:
        if not documents:
            return []
        pairs = [
            (query_text, _build_reranker_passage(document, self.config))
            for document in documents
        ]
        scores = self.model.predict(
            pairs,
            batch_size=self.config.batch_size,
            show_progress_bar=self.config.show_progress_bar,
        )
        return [float(score) for score in np.asarray(scores, dtype=np.float32).tolist()]


@dataclass(frozen=True)
class RerankingRetriever:
    documents: tuple[RetrievalDocument, ...]
    base_retriever: Retriever
    base_method: RetrievalMethod
    reranker: PairwiseReranker
    config: RerankerConfig

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
        candidate_k = max(top_k, self.config.candidate_k)
        base_result = self.base_retriever.search(
            query_id=query_id,
            query_type=query_type,
            query_text=query_text,
            top_k=candidate_k,
        )
        documents_by_id = {
            document.retrieval_doc_id: document for document in self.documents
        }
        candidate_documents = [
            documents_by_id[candidate.retrieval_doc_id]
            for candidate in base_result.candidates
            if candidate.retrieval_doc_id in documents_by_id
        ]
        if not candidate_documents:
            return RetrievalRunResult(
                query_id=query_id,
                query_type=query_type,
                method=self.base_method,
                candidates=[],
                latency_ms=round((time.perf_counter() - started) * 1000, 6),
            )
        reranker_scores = self.reranker.score(query_text, candidate_documents)
        base_rank_by_id = {
            candidate.retrieval_doc_id: candidate.rank
            for candidate in base_result.candidates
        }
        scored = [
            _RerankedDocument(
                document=document,
                score=score,
                base_rank=base_rank_by_id.get(document.retrieval_doc_id, candidate_k + 1),
            )
            for document, score in zip(candidate_documents, reranker_scores, strict=True)
        ]
        scored.sort(
            key=lambda item: (
                -item.score,
                item.base_rank,
                item.document.retrieval_doc_id,
            )
        )
        candidates = [
            _candidate_from_document(
                rank=rank,
                document=item.document,
                score=item.score,
            )
            for rank, item in enumerate(scored[:top_k], start=1)
        ]
        return RetrievalRunResult(
            query_id=query_id,
            query_type=query_type,
            method=self.base_method,
            candidates=candidates,
            latency_ms=round((time.perf_counter() - started) * 1000, 6),
        )


@dataclass(frozen=True)
class _RerankedDocument:
    document: RetrievalDocument
    score: float
    base_rank: int


def _build_reranker_passage(
    document: RetrievalDocument,
    config: RerankerConfig,
) -> str:
    parts = [
        document.doc_title if config.include_doc_title else "",
        document.search_text or "",
        document.context_text if config.include_context_text else "",
    ]
    passage = "\n".join(part for part in parts if part)
    return passage[: config.max_passage_chars]


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


def _load_cross_encoder_model(config: RerankerConfig) -> Any:
    try:
        from sentence_transformers import CrossEncoder
    except ImportError as exc:
        raise ImportError(
            "sentence-transformers is required for CrossEncoder reranker. "
            "Install the neural optional dependency."
        ) from exc
    return CrossEncoder(config.model_name, device=resolve_torch_device(config.device))
