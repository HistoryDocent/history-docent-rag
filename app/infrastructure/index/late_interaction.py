from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Protocol

import torch

from app.domain.retrieval import (
    QueryType,
    RetrievedCandidate,
    RetrievalDocument,
    RetrievalMethod,
    RetrievalRunResult,
)
from app.infrastructure.index.device import resolve_torch_device
from app.infrastructure.index.dense import _build_searchable_text, DenseRetrievalConfig


class BaseRetriever(Protocol):
    def search(
        self,
        *,
        query_id: str,
        query_type: QueryType,
        query_text: str,
        top_k: int,
    ) -> RetrievalRunResult:
        ...


class LateInteractionScorer(Protocol):
    def score(
        self,
        query_text: str,
        documents: list[RetrievalDocument],
    ) -> "LateInteractionScoreBatch":
        ...


@dataclass(frozen=True)
class LateInteractionScoreBatch:
    scores: list[float]
    cuda_memory_peak_mb: float


@dataclass(frozen=True)
class LateInteractionConfig:
    scorer_id: str = "colbert-style-e5-small-maxsim-v1"
    model_name: str = "intfloat/multilingual-e5-small"
    device: str = "cuda_if_available"
    batch_size: int = 8
    candidate_k: int = 20
    query_prefix: str = "query: "
    document_prefix: str = "passage: "
    include_doc_title: bool = True
    include_context_text: bool = True
    max_query_tokens: int = 64
    max_document_tokens: int = 192
    max_passage_chars: int = 1800

    def __post_init__(self) -> None:
        if self.batch_size < 1:
            raise ValueError("batch_size must be >= 1")
        if self.candidate_k < 1:
            raise ValueError("candidate_k must be >= 1")
        if self.max_query_tokens < 1:
            raise ValueError("max_query_tokens must be >= 1")
        if self.max_document_tokens < 1:
            raise ValueError("max_document_tokens must be >= 1")
        if self.max_passage_chars < 1:
            raise ValueError("max_passage_chars must be >= 1")

    def to_method_config_summary(
        self,
        *,
        top_k: int,
        base_run_label: str,
    ) -> dict[str, str | int | float | bool]:
        return {
            "method": "dense",
            "top_k": top_k,
            "base_run_label": base_run_label,
            "retrieval_candidate_k": self.candidate_k,
            "reranking": True,
            "late_interaction": True,
            "late_interaction_scorer_id": self.scorer_id,
            "late_interaction_model_name": self.model_name,
            "late_interaction_device": self.device,
            "late_interaction_resolved_device": resolve_torch_device(self.device),
            "late_interaction_batch_size": self.batch_size,
            "late_interaction_max_query_tokens": self.max_query_tokens,
            "late_interaction_max_document_tokens": self.max_document_tokens,
            "late_interaction_include_context_text": self.include_context_text,
        }


@dataclass(frozen=True)
class TransformerLateInteractionScorer:
    config: LateInteractionConfig
    tokenizer: Any
    model: Any

    @classmethod
    def from_config(
        cls,
        config: LateInteractionConfig,
    ) -> "TransformerLateInteractionScorer":
        tokenizer, model = _load_transformer_model(config)
        model.eval()
        return cls(config=config, tokenizer=tokenizer, model=model)

    def score(
        self,
        query_text: str,
        documents: list[RetrievalDocument],
    ) -> LateInteractionScoreBatch:
        if not documents:
            return LateInteractionScoreBatch(scores=[], cuda_memory_peak_mb=0.0)
        device = torch.device(resolve_torch_device(self.config.device))
        if device.type == "cuda":
            torch.cuda.reset_peak_memory_stats(device)
        query_embeddings, query_mask = self._encode(
            [f"{self.config.query_prefix}{query_text}"],
            max_length=self.config.max_query_tokens,
            device=device,
        )
        query_embedding = query_embeddings[0]
        query_token_mask = query_mask[0]
        scores: list[float] = []
        for start in range(0, len(documents), self.config.batch_size):
            batch_documents = documents[start : start + self.config.batch_size]
            passages = [
                f"{self.config.document_prefix}{_build_late_interaction_passage(document, self.config)}"
                for document in batch_documents
            ]
            doc_embeddings, doc_mask = self._encode(
                passages,
                max_length=self.config.max_document_tokens,
                device=device,
            )
            batch_scores = _maxsim_scores(
                query_embedding=query_embedding,
                query_mask=query_token_mask,
                document_embeddings=doc_embeddings,
                document_mask=doc_mask,
            )
            scores.extend(batch_scores.detach().cpu().tolist())
        peak_mb = (
            round(torch.cuda.max_memory_allocated(device) / (1024 * 1024), 6)
            if device.type == "cuda"
            else 0.0
        )
        return LateInteractionScoreBatch(
            scores=[round(float(score), 6) for score in scores],
            cuda_memory_peak_mb=peak_mb,
        )

    def _encode(
        self,
        texts: list[str],
        *,
        max_length: int,
        device: torch.device,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        encoded = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=max_length,
            return_tensors="pt",
        )
        encoded = {key: value.to(device) for key, value in encoded.items()}
        with torch.no_grad():
            output = self.model(**encoded)
        embeddings = torch.nn.functional.normalize(output.last_hidden_state, p=2, dim=-1)
        return embeddings, encoded["attention_mask"].bool()


@dataclass
class LateInteractionRerankingRetriever:
    documents: tuple[RetrievalDocument, ...]
    base_retriever: BaseRetriever
    base_method: RetrievalMethod
    scorer: LateInteractionScorer
    config: LateInteractionConfig
    last_cuda_memory_peak_mb: float = 0.0

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
            self.last_cuda_memory_peak_mb = 0.0
            return RetrievalRunResult(
                query_id=query_id,
                query_type=query_type,
                method=self.base_method,
                candidates=[],
                latency_ms=round((time.perf_counter() - started) * 1000, 6),
            )
        score_batch = self.scorer.score(query_text, candidate_documents)
        self.last_cuda_memory_peak_mb = score_batch.cuda_memory_peak_mb
        base_rank_by_id = {
            candidate.retrieval_doc_id: candidate.rank
            for candidate in base_result.candidates
        }
        scored = [
            _LateInteractionRankedDocument(
                document=document,
                score=score,
                base_rank=base_rank_by_id.get(
                    document.retrieval_doc_id,
                    candidate_k + 1,
                ),
            )
            for document, score in zip(
                candidate_documents,
                score_batch.scores,
                strict=True,
            )
        ]
        scored.sort(
            key=lambda item: (
                -item.score,
                item.base_rank,
                item.document.retrieval_doc_id,
            )
        )
        candidates = [
            _candidate_from_document(rank=rank, document=item.document, score=item.score)
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
class _LateInteractionRankedDocument:
    document: RetrievalDocument
    score: float
    base_rank: int


def _maxsim_scores(
    *,
    query_embedding: torch.Tensor,
    query_mask: torch.Tensor,
    document_embeddings: torch.Tensor,
    document_mask: torch.Tensor,
) -> torch.Tensor:
    if query_embedding.ndim != 2:
        raise ValueError("query_embedding must have shape [query_tokens, dim]")
    if document_embeddings.ndim != 3:
        raise ValueError("document_embeddings must have shape [batch, doc_tokens, dim]")
    if document_embeddings.shape[-1] != query_embedding.shape[-1]:
        raise ValueError("query and document embedding dims must match")
    query_mask = query_mask.bool()
    document_mask = document_mask.bool()
    similarities = torch.matmul(
        document_embeddings,
        query_embedding.transpose(0, 1),
    ).transpose(1, 2)
    similarities = similarities.masked_fill(~document_mask[:, None, :], -1_000_000.0)
    max_per_query_item = similarities.max(dim=2).values
    max_per_query_item = max_per_query_item.masked_fill(~query_mask[None, :], 0.0)
    active_query_count = query_mask.sum().clamp(min=1).to(max_per_query_item.dtype)
    return max_per_query_item.sum(dim=1) / active_query_count


def _build_late_interaction_passage(
    document: RetrievalDocument,
    config: LateInteractionConfig,
) -> str:
    dense_config = DenseRetrievalConfig(
        include_doc_title=config.include_doc_title,
    )
    text = _build_searchable_text(document, dense_config)
    if not config.include_context_text and document.context_text:
        text = "\n".join(
            part
            for part in (
                document.doc_title if config.include_doc_title else "",
                document.search_text or "",
            )
            if part
        )
    return text[: config.max_passage_chars]


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


def _load_transformer_model(config: LateInteractionConfig) -> tuple[Any, Any]:
    try:
        from transformers import AutoModel, AutoTokenizer
    except ImportError as exc:
        raise RuntimeError(
            "transformers is required for ColBERT-style late interaction scoring. "
            "Install the neural optional dependencies."
        ) from exc
    device = resolve_torch_device(config.device)
    tokenizer = AutoTokenizer.from_pretrained(config.model_name)
    model = AutoModel.from_pretrained(config.model_name).to(device)
    return tokenizer, model
