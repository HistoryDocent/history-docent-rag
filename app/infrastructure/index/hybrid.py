from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.domain.retrieval import (
    QueryType,
    RetrievedCandidate,
    RetrievalDocument,
    RetrievalRunResult,
)
from app.infrastructure.index.bm25 import Bm25Retriever
from app.infrastructure.index.dense import DenseRetrievalConfig, DenseRetriever


HybridFusionMethod = Literal["hybrid_rrf", "hybrid_weighted"]


@dataclass(frozen=True)
class HybridRetrievalConfig:
    method: HybridFusionMethod
    candidate_k: int = 50
    rrf_k: int = 60
    alpha: float = 0.5
    dense_config: DenseRetrievalConfig = DenseRetrievalConfig()

    def __post_init__(self) -> None:
        if self.candidate_k < 1:
            raise ValueError("candidate_k must be >= 1")
        if self.rrf_k < 1:
            raise ValueError("rrf_k must be >= 1")
        if not 0.0 <= self.alpha <= 1.0:
            raise ValueError("alpha must be between 0.0 and 1.0")

    def to_method_config_summary(
        self,
        *,
        top_k: int,
        embedding_dim: int,
    ) -> dict[str, str | int | float | bool]:
        summary: dict[str, str | int | float | bool] = {
            "method": self.method,
            "top_k": top_k,
            "candidate_k": self.candidate_k,
            "fusion": "reciprocal_rank_fusion"
            if self.method == "hybrid_rrf"
            else "minmax_weighted_sum",
            "dense_encoder_id": self.dense_config.encoder_id,
            "dense_embedding_dim": embedding_dim,
            "query_rewrite": False,
            "reranking": False,
        }
        if self.method == "hybrid_rrf":
            summary["rrf_k"] = self.rrf_k
        else:
            summary["dense_weight_alpha"] = self.alpha
            summary["score_normalization"] = "per-method-minmax"
        return summary


@dataclass(frozen=True)
class HybridRetriever:
    documents: tuple[RetrievalDocument, ...]
    bm25_retriever: Bm25Retriever
    dense_retriever: DenseRetriever
    config: HybridRetrievalConfig

    @classmethod
    def from_documents(
        cls,
        documents: list[RetrievalDocument],
        *,
        config: HybridRetrievalConfig,
        dense_cache_dir: Path | None = None,
    ) -> "HybridRetriever":
        if not documents:
            raise ValueError("hybrid retriever requires at least one document")
        return cls(
            documents=tuple(documents),
            bm25_retriever=Bm25Retriever.from_documents(documents),
            dense_retriever=DenseRetriever.from_documents(
                documents,
                config=config.dense_config,
                cache_dir=dense_cache_dir,
            ),
            config=config,
        )

    @property
    def embedding_dim(self) -> int:
        return self.dense_retriever.embedding_dim

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
        bm25_result = self.bm25_retriever.search(
            query_id=query_id,
            query_type=query_type,
            query_text=query_text,
            top_k=candidate_k,
        )
        dense_result = self.dense_retriever.search(
            query_id=query_id,
            query_type=query_type,
            query_text=query_text,
            top_k=candidate_k,
        )
        candidates = self._fuse_candidates(
            bm25_candidates=bm25_result.candidates,
            dense_candidates=dense_result.candidates,
            top_k=top_k,
        )
        elapsed_ms = round((time.perf_counter() - started) * 1000, 6)
        return RetrievalRunResult(
            query_id=query_id,
            query_type=query_type,
            method=self.config.method,
            candidates=candidates,
            latency_ms=elapsed_ms,
        )

    def _fuse_candidates(
        self,
        *,
        bm25_candidates: list[RetrievedCandidate],
        dense_candidates: list[RetrievedCandidate],
        top_k: int,
    ) -> list[RetrievedCandidate]:
        bm25_by_id = _candidate_by_doc_id(bm25_candidates)
        dense_by_id = _candidate_by_doc_id(dense_candidates)
        all_doc_ids = set(bm25_by_id) | set(dense_by_id)
        if not all_doc_ids:
            return []

        bm25_normalized = _normalize_scores(bm25_by_id)
        dense_normalized = _normalize_scores(dense_by_id)
        document_by_id = {
            document.retrieval_doc_id: document for document in self.documents
        }
        ranked = []
        for retrieval_doc_id in all_doc_ids:
            bm25_candidate = bm25_by_id.get(retrieval_doc_id)
            dense_candidate = dense_by_id.get(retrieval_doc_id)
            bm25_rank = bm25_candidate.rank if bm25_candidate is not None else None
            dense_rank = dense_candidate.rank if dense_candidate is not None else None
            ranked.append(
                _FusedCandidate(
                    retrieval_doc_id=retrieval_doc_id,
                    score=self._fused_score(
                        retrieval_doc_id=retrieval_doc_id,
                        bm25_rank=bm25_rank,
                        dense_rank=dense_rank,
                        bm25_normalized=bm25_normalized,
                        dense_normalized=dense_normalized,
                    ),
                    bm25_rank=bm25_rank,
                    dense_rank=dense_rank,
                )
            )
        ranked.sort(
            key=lambda item: (
                -item.score,
                min(
                    item.bm25_rank or self.config.candidate_k + 1,
                    item.dense_rank or self.config.candidate_k + 1,
                ),
                item.bm25_rank or self.config.candidate_k + 1,
                item.dense_rank or self.config.candidate_k + 1,
                item.retrieval_doc_id,
            )
        )
        return [
            _candidate_from_document(
                rank=rank,
                document=document_by_id[fused.retrieval_doc_id],
                score=fused.score,
            )
            for rank, fused in enumerate(ranked[:top_k], start=1)
        ]

    def _fused_score(
        self,
        *,
        retrieval_doc_id: str,
        bm25_rank: int | None,
        dense_rank: int | None,
        bm25_normalized: dict[str, float],
        dense_normalized: dict[str, float],
    ) -> float:
        if self.config.method == "hybrid_rrf":
            return round(
                _rrf_score(rank=bm25_rank, rrf_k=self.config.rrf_k)
                + _rrf_score(rank=dense_rank, rrf_k=self.config.rrf_k),
                6,
            )
        bm25_score = bm25_normalized.get(retrieval_doc_id, 0.0)
        dense_score = dense_normalized.get(retrieval_doc_id, 0.0)
        return round(
            ((1.0 - self.config.alpha) * bm25_score)
            + (self.config.alpha * dense_score),
            6,
        )


@dataclass(frozen=True)
class _FusedCandidate:
    retrieval_doc_id: str
    score: float
    bm25_rank: int | None
    dense_rank: int | None


def _candidate_by_doc_id(
    candidates: list[RetrievedCandidate],
) -> dict[str, RetrievedCandidate]:
    return {candidate.retrieval_doc_id: candidate for candidate in candidates}


def _normalize_scores(
    candidates_by_id: dict[str, RetrievedCandidate],
) -> dict[str, float]:
    if not candidates_by_id:
        return {}
    scores = [candidate.score for candidate in candidates_by_id.values()]
    min_score = min(scores)
    max_score = max(scores)
    if max_score == min_score:
        constant_value = 1.0 if max_score > 0 else 0.0
        return {
            retrieval_doc_id: constant_value
            for retrieval_doc_id in candidates_by_id
        }
    return {
        retrieval_doc_id: round(
            (candidate.score - min_score) / (max_score - min_score),
            6,
        )
        for retrieval_doc_id, candidate in candidates_by_id.items()
    }


def _rrf_score(*, rank: int | None, rrf_k: int) -> float:
    if rank is None:
        return 0.0
    return 1.0 / (rrf_k + rank)


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
