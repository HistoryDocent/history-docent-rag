from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from app.application.evidence_packing import (
    EvidencePack,
    EvidencePacker,
    PackedEvidence,
    build_candidates_by_query_id,
    build_evidence_corpus_from_chunks_payload,
)
from app.application.query_rewrite import PlaceAwareQueryRewriter, QueryRewriteConfig
from app.core.project_paths import project_path
from app.domain.chunking import ChildChunk
from app.domain.place_catalog import load_place_catalog
from app.domain.retrieval import (
    LanguageCode,
    QueryType,
    RetrievalEvalItem,
    RetrievalRunResult,
    build_retrieval_document_from_child,
)
from app.infrastructure.index.dense import DenseRetrievalConfig, DenseRetriever
from app.infrastructure.index.dense import SentenceTransformerEncoder


ChatRetrievalMode = Literal["contract_only", "retrieval_backed"]
ChatRetrievalMethod = Literal[
    "contract_fixture",
    "fixture_retrieval",
    "dense_multilingual_e5_small_voice_rewrite",
]


class ChatRetrievalModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ChatRetrievalCommand(Protocol):
    request_id: str
    query: str
    language: LanguageCode
    query_type: QueryType
    place_context: tuple[str, ...]
    voice_mode: bool
    user_context: str | None


class ChatRetrievalOutcome(ChatRetrievalModel):
    evidence_pack: EvidencePack
    retrieval_method: ChatRetrievalMethod
    retrieval_candidate_count: int = Field(ge=0)
    retrieval_latency_ms: float = Field(ge=0.0)
    query_rewrite_changed: bool = False
    query_rewrite_latency_ms: float = Field(default=0.0, ge=0.0)
    query_rewrite_applied_rules: tuple[str, ...] = Field(default_factory=tuple)
    place_ids: tuple[str, ...] = Field(default_factory=tuple)


class ChatRetrievalUnavailableError(RuntimeError):
    """Raised when retrieval-backed mode cannot load the private retrieval backend."""


class ChatRetrievalBackend(Protocol):
    def retrieve(
        self,
        *,
        command: ChatRetrievalCommand,
        item: RetrievalEvalItem,
    ) -> ChatRetrievalOutcome:
        ...


class StaticRetrievalBackend:
    def retrieve(
        self,
        *,
        command: ChatRetrievalCommand,
        item: RetrievalEvalItem,
    ) -> ChatRetrievalOutcome:
        started = time.perf_counter()
        if item.query.expected_behavior == "abstain":
            pack = _empty_pack(item=item)
            return ChatRetrievalOutcome(
                evidence_pack=pack,
                retrieval_method="fixture_retrieval",
                retrieval_candidate_count=0,
                retrieval_latency_ms=_elapsed_ms(started),
                place_ids=tuple(command.place_context),
            )
        evidence = PackedEvidence(
            pack_rank=1,
            source_rank=1,
            retrieval_doc_id="fixture-child-gyeongbokgung",
            child_id="fixture-child-gyeongbokgung",
            parent_id="fixture-parent-palace",
            doc_id="fixture-doc-history",
            score=1.0,
            estimated_chars=360,
            source_block_ids=("fixture-block-palace",),
            citation_block_ids=("fixture-block-palace",),
            citation_recoverable=True,
            packing_reason="retrieval_backed_fixture",
        )
        pack = EvidencePack(
            query_id=item.query.query_id,
            query_type=item.query.query_type,
            policy_id="P0_rank_order",
            context_budget_chars=4200,
            total_estimated_chars=evidence.estimated_chars,
            evidence=(evidence,),
            target_child_covered=True,
            target_parent_covered=True,
            target_doc_covered=True,
            evidence_order_relevance_proxy=1.0,
        )
        return ChatRetrievalOutcome(
            evidence_pack=pack,
            retrieval_method="fixture_retrieval",
            retrieval_candidate_count=1,
            retrieval_latency_ms=_elapsed_ms(started),
            place_ids=tuple(command.place_context) or ("gyeongbokgung",),
        )


@dataclass(frozen=True)
class _PrivateRetrievalState:
    retriever: DenseRetriever
    corpus: object
    rewriter: PlaceAwareQueryRewriter


class PrivateArtifactRetrievalBackend:
    def __init__(
        self,
        *,
        chunks_path: Path = Path("private_data") / "reports" / "parent_child_chunks.json",
        place_catalog_path: Path = Path("data_samples") / "place_catalog_seed.json",
        embedding_cache_dir: Path = Path("private_data") / "embeddings" / "query_rewrite",
        top_k: int = 5,
    ) -> None:
        self.chunks_path = chunks_path
        self.place_catalog_path = place_catalog_path
        self.embedding_cache_dir = embedding_cache_dir
        self.top_k = top_k
        self._state: _PrivateRetrievalState | None = None

    def retrieve(
        self,
        *,
        command: ChatRetrievalCommand,
        item: RetrievalEvalItem,
    ) -> ChatRetrievalOutcome:
        if item.query.expected_behavior == "abstain":
            return ChatRetrievalOutcome(
                evidence_pack=_empty_pack(item=item),
                retrieval_method="dense_multilingual_e5_small_voice_rewrite",
                retrieval_candidate_count=0,
                retrieval_latency_ms=0.0,
                place_ids=tuple(command.place_context),
            )
        state = self._load_state()
        rewrite = state.rewriter.rewrite(item)
        result = state.retriever.search(
            query_id=item.query.query_id,
            query_type=item.query.query_type,
            query_text=rewrite.rewritten_query_text,
            top_k=self.top_k,
        )
        pack = _pack_retrieval_result(
            item=item,
            result=result,
            corpus=state.corpus,
        )
        return ChatRetrievalOutcome(
            evidence_pack=pack,
            retrieval_method="dense_multilingual_e5_small_voice_rewrite",
            retrieval_candidate_count=len(result.candidates),
            retrieval_latency_ms=result.latency_ms,
            query_rewrite_changed=rewrite.changed,
            query_rewrite_latency_ms=rewrite.latency_ms,
            query_rewrite_applied_rules=rewrite.applied_rules,
            place_ids=rewrite.place_ids or tuple(command.place_context),
        )

    def _load_state(self) -> _PrivateRetrievalState:
        if self._state is not None:
            return self._state
        chunks_path = project_path(self.chunks_path)
        place_catalog_path = project_path(self.place_catalog_path)
        embedding_cache_dir = project_path(self.embedding_cache_dir)
        if not chunks_path.exists():
            raise ChatRetrievalUnavailableError(
                "private parent_child_chunks artifact is required for retrieval_backed mode"
            )
        payload = json.loads(chunks_path.read_text(encoding="utf-8"))
        children_payload = payload.get("children")
        if not isinstance(children_payload, list):
            raise ChatRetrievalUnavailableError(
                "parent_child_chunks artifact must include children list"
            )
        documents = []
        for child_payload in children_payload:
            child = ChildChunk.model_validate(child_payload)
            if child.text:
                documents.append(
                    build_retrieval_document_from_child(
                        child,
                        include_private_text=True,
                    )
                )
        if not documents:
            raise ChatRetrievalUnavailableError("no searchable child chunks found")
        config = _e5_small_dense_config()
        retriever = _load_cached_dense_retriever(
            documents=documents,
            config=config,
            embedding_cache_dir=embedding_cache_dir,
        ) or DenseRetriever.from_documents(
            documents,
            config=config,
            cache_dir=embedding_cache_dir,
        )
        catalog = load_place_catalog(place_catalog_path)
        self._state = _PrivateRetrievalState(
            retriever=retriever,
            corpus=build_evidence_corpus_from_chunks_payload(payload),
            rewriter=PlaceAwareQueryRewriter(
                catalog=catalog,
                config=QueryRewriteConfig(
                    strategy_id="voice-followup-deterministic-v1",
                    target_query_types=("voice_followup",),
                ),
            ),
        )
        return self._state


def _pack_retrieval_result(
    *,
    item: RetrievalEvalItem,
    result: RetrievalRunResult,
    corpus: object,
) -> EvidencePack:
    candidates_by_query_id = build_candidates_by_query_id(
        result_rows=[
            {
                "query_id": result.query_id,
                "query_type": result.query_type,
                "rank": candidate.rank,
                "retrieval_doc_id": candidate.retrieval_doc_id,
                "child_id": candidate.child_id,
                "parent_id": candidate.parent_id,
                "doc_id": candidate.doc_id,
                "score": candidate.score,
            }
            for candidate in result.candidates
        ],
        corpus=corpus,
    )
    packer = EvidencePacker(corpus=corpus)
    return packer.pack(
        item=item,
        candidates=candidates_by_query_id.get(item.query.query_id, []),
        policy_id="P0_rank_order",
    )


def _empty_pack(*, item: RetrievalEvalItem) -> EvidencePack:
    return EvidencePack(
        query_id=item.query.query_id,
        query_type=item.query.query_type,
        policy_id="P0_rank_order",
        context_budget_chars=4200,
        total_estimated_chars=0,
        evidence=(),
        target_child_covered=False,
        target_parent_covered=False,
        target_doc_covered=False,
        evidence_order_relevance_proxy=0.0,
    )


def _e5_small_dense_config() -> DenseRetrievalConfig:
    return DenseRetrievalConfig(
        encoder_id="multilingual-e5-small",
        backend="sentence_transformers",
        model_name="intfloat/multilingual-e5-small",
        query_prefix="query: ",
        document_prefix="passage: ",
    )


def _load_cached_dense_retriever(
    *,
    documents: list,
    config: DenseRetrievalConfig,
    embedding_cache_dir: Path,
) -> DenseRetriever | None:
    if not embedding_cache_dir.exists():
        return None
    document_ids = [document.retrieval_doc_id for document in documents]
    for manifest_path in sorted(embedding_cache_dir.glob("*.manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("encoder_id") != config.encoder_id:
            continue
        if manifest.get("document_count") != len(documents):
            continue
        vector_path = manifest_path.with_suffix("").with_suffix(".npz")
        if not vector_path.exists():
            continue
        try:
            embeddings = _load_document_embeddings(
                vector_path=vector_path,
                expected_document_ids=document_ids,
            )
            encoder = _load_sentence_transformer_encoder(config)
        except (ImportError, ValueError, OSError):
            continue
        return DenseRetriever(
            documents=tuple(documents),
            document_embeddings=embeddings,
            encoder=encoder,
            config=config,
            embedding_cache_manifest={
                key: value
                for key, value in manifest.items()
                if isinstance(value, str | int | float | bool)
            },
        )
    return None


def _load_document_embeddings(
    *,
    vector_path: Path,
    expected_document_ids: list[str],
) -> np.ndarray:
    loaded = np.load(vector_path, allow_pickle=True)
    embeddings = np.asarray(loaded["document_embeddings"], dtype=np.float32)
    cached_ids = [str(item) for item in loaded["document_ids"].tolist()]
    if cached_ids == expected_document_ids:
        return embeddings
    if set(cached_ids) != set(expected_document_ids):
        raise ValueError("cached dense embedding ids do not match documents")
    index_by_id = {document_id: index for index, document_id in enumerate(cached_ids)}
    return np.asarray(
        [embeddings[index_by_id[document_id]] for document_id in expected_document_ids],
        dtype=np.float32,
    )


def _load_sentence_transformer_encoder(
    config: DenseRetrievalConfig,
) -> SentenceTransformerEncoder:
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as error:
        raise ImportError(
            "sentence-transformers is required for cached neural retrieval"
        ) from error
    encoder = SentenceTransformerEncoder(config=config)
    encoder.model = SentenceTransformer(config.model_name or config.encoder_id, device=config.device)
    return encoder


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 6)
