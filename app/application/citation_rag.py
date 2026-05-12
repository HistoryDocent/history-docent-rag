from __future__ import annotations

from dataclasses import dataclass

from app.application.evidence_packing import EvidencePack, PackedEvidence
from app.domain.generation import (
    AnswerProviderKind,
    Citation,
    CitationRagAnswer,
    CitationRagDraft,
    CitationRagDraftV2,
    UnsupportedClaimRisk,
    build_citation_id,
    build_evidence_id,
)
from app.domain.retrieval import RetrievalEvalItem


DEFAULT_ANSWER_POLICY_ID = "citation-rag-contract-v1"
DEFAULT_MODEL_ID = "contract-only"
DEFAULT_ABSTAIN_ANSWER = "현재 보유한 근거로는 답변하지 않겠습니다."
DEFAULT_ABSTAIN_SPOKEN_ANSWER = "지금 가진 자료로는 확실하게 답하기 어렵습니다."


@dataclass(frozen=True)
class CitationRagAssemblerConfig:
    answer_policy_id: str = DEFAULT_ANSWER_POLICY_ID
    provider: AnswerProviderKind = "contract_only"
    model_id: str = DEFAULT_MODEL_ID
    abstain_answer: str = DEFAULT_ABSTAIN_ANSWER
    abstain_spoken_answer: str = DEFAULT_ABSTAIN_SPOKEN_ANSWER

    def __post_init__(self) -> None:
        if not self.answer_policy_id.strip():
            raise ValueError("answer_policy_id must not be empty")
        if not self.model_id.strip():
            raise ValueError("model_id must not be empty")


class CitationRagAnswerAssembler:
    def __init__(
        self,
        *,
        config: CitationRagAssemblerConfig | None = None,
    ) -> None:
        self.config = config or CitationRagAssemblerConfig()

    def assemble(
        self,
        *,
        item: RetrievalEvalItem,
        evidence_pack: EvidencePack,
        draft: CitationRagDraft | None = None,
        place_ids: tuple[str, ...] | None = None,
    ) -> CitationRagAnswer:
        if evidence_pack.query_id != item.query.query_id:
            raise ValueError("evidence_pack query_id must match eval item query_id")
        if evidence_pack.query_type != item.query.query_type:
            raise ValueError("evidence_pack query_type must match eval item query_type")
        if item.query.expected_behavior == "abstain" or not evidence_pack.evidence:
            return self._abstained_answer(item=item, place_ids=place_ids or ())
        if draft is None:
            raise ValueError("answer draft is required for non-abstained answer")
        citation_evidence = _select_citation_evidence(
            evidence_pack=evidence_pack,
            draft=draft,
        )
        citations = tuple(
            _citation_from_evidence(
                query_id=item.query.query_id,
                evidence=evidence,
            )
            for evidence in citation_evidence
        )
        evidence_ids = tuple(citation.evidence_id for citation in citations)
        return CitationRagAnswer(
            answer_policy_id=self.config.answer_policy_id,
            provider=self.config.provider,
            model_id=self.config.model_id,
            query_id=item.query.query_id,
            query_type=item.query.query_type,
            answer=draft.answer.strip(),
            spoken_answer=draft.spoken_answer.strip(),
            citations=citations,
            evidence_ids=evidence_ids,
            place_ids=place_ids or tuple(item.metadata.place_ids),
            abstained=False,
            unsupported_claim_risk=draft.unsupported_claim_risk,
        )

    def _abstained_answer(
        self,
        *,
        item: RetrievalEvalItem,
        place_ids: tuple[str, ...],
    ) -> CitationRagAnswer:
        return CitationRagAnswer(
            answer_policy_id=self.config.answer_policy_id,
            provider=self.config.provider,
            model_id=self.config.model_id,
            query_id=item.query.query_id,
            query_type=item.query.query_type,
            answer=self.config.abstain_answer,
            spoken_answer=self.config.abstain_spoken_answer,
            citations=(),
            evidence_ids=(),
            place_ids=place_ids or tuple(item.metadata.place_ids),
            abstained=True,
            unsupported_claim_risk="low",
        )


def build_contract_only_draft(
    *,
    answer: str,
    spoken_answer: str,
    unsupported_claim_risk: UnsupportedClaimRisk = "medium",
) -> CitationRagDraft:
    return CitationRagDraft(
        answer=answer,
        spoken_answer=spoken_answer,
        unsupported_claim_risk=unsupported_claim_risk,
    )


def _citation_from_evidence(
    *,
    query_id: str,
    evidence: PackedEvidence,
) -> Citation:
    evidence_id = build_evidence_id(
        query_id=query_id,
        child_id=evidence.child_id,
        pack_rank=evidence.pack_rank,
    )
    return Citation(
        citation_id=build_citation_id(
            query_id=query_id,
            evidence_id=evidence_id,
            pack_rank=evidence.pack_rank,
        ),
        evidence_id=evidence_id,
        child_id=evidence.child_id,
        parent_id=evidence.parent_id,
        doc_id=evidence.doc_id,
        source_rank=evidence.source_rank,
        pack_rank=evidence.pack_rank,
        source_block_ids=evidence.source_block_ids,
        citation_block_ids=evidence.citation_block_ids,
        citation_recoverable=evidence.citation_recoverable,
    )


def _select_citation_evidence(
    *,
    evidence_pack: EvidencePack,
    draft: CitationRagDraft,
) -> tuple[PackedEvidence, ...]:
    if not isinstance(draft, CitationRagDraftV2):
        return evidence_pack.evidence

    evidence_by_rank = {evidence.pack_rank: evidence for evidence in evidence_pack.evidence}
    missing_ranks = sorted(
        rank for rank in draft.used_evidence_pack_ranks if rank not in evidence_by_rank
    )
    if missing_ranks:
        joined_ranks = ", ".join(str(rank) for rank in missing_ranks)
        raise ValueError(f"used_evidence_pack_ranks must exist in evidence_pack: {joined_ranks}")
    return tuple(evidence_by_rank[rank] for rank in draft.used_evidence_pack_ranks)
