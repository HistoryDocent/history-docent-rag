from __future__ import annotations

import re
import time
from dataclasses import dataclass

from rank_bm25 import BM25Okapi  # type: ignore[import-untyped]

from app.domain.retrieval import (
    QueryType,
    RetrievedCandidate,
    RetrievalDocument,
    RetrievalRunResult,
)


_TOKEN_PATTERN = re.compile(r"[0-9A-Za-z가-힣]+")


def bm25_tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in _TOKEN_PATTERN.finditer(text)]


@dataclass(frozen=True)
class Bm25Retriever:
    documents: tuple[RetrievalDocument, ...]
    tokenized_corpus: tuple[list[str], ...]
    index: BM25Okapi

    @classmethod
    def from_documents(cls, documents: list[RetrievalDocument]) -> "Bm25Retriever":
        if not documents:
            raise ValueError("BM25 retriever requires at least one document")
        tokenized_corpus = tuple(
            bm25_tokenize(_build_searchable_text(document)) for document in documents
        )
        return cls(
            documents=tuple(documents),
            tokenized_corpus=tokenized_corpus,
            index=BM25Okapi(list(tokenized_corpus)),
        )

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
        query_tokens = bm25_tokenize(query_text)
        scores = self.index.get_scores(query_tokens)
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
            method="bm25",
            candidates=candidates,
            latency_ms=elapsed_ms,
        )


def _build_searchable_text(document: RetrievalDocument) -> str:
    parts = [
        document.doc_title,
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
