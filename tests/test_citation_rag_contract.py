from __future__ import annotations

import pytest

from app.application.citation_rag import (
    CitationRagAnswerAssembler,
    build_contract_only_draft,
)
from app.application.evidence_packing import EvidencePack, PackedEvidence
from app.domain.generation import (
    Citation,
    CitationRagAnswer,
    CitationRagDraft,
    build_citation_rag_contract_report,
    collect_citation_rag_contract_failures,
    summarize_citation_rag_answers,
)
from app.domain.retrieval import RetrievalEvalItem


def _eval_item(
    *,
    query_id: str = "q-contract-answer",
    query_type: str = "place_story",
    expected_behavior: str = "retrieve",
) -> RetrievalEvalItem:
    judgments = []
    if expected_behavior == "retrieve":
        judgments.append(
            {
                "query_id": query_id,
                "relevant_child_ids": ["child-palace"],
                "relevant_parent_ids": ["parent-palace"],
                "relevant_doc_ids": ["doc-palace"],
                "relevance_grade": 3,
                "rationale_summary": "id only",
                "public_allowed": True,
            }
        )
    return RetrievalEvalItem.model_validate(
        {
            "dataset_version": "retrieval-eval-dataset/v2",
            "query": {
                "query_id": query_id,
                "query_type": query_type,
                "query_text": "경복궁은 왜 중요한 장소야?",
                "language": "ko",
                "expected_behavior": expected_behavior,
                "public_allowed": True,
            },
            "judgments": judgments,
            "metadata": {
                "split": "dev",
                "difficulty": "medium",
                "place_ids": ["gyeongbokgung"] if expected_behavior == "retrieve" else [],
                "requires_context": query_type == "voice_followup",
                "answerability": "answerable"
                if expected_behavior == "retrieve"
                else "unanswerable",
                "review_status": "reviewed",
            },
        }
    )


def _evidence_pack(
    *,
    query_id: str = "q-contract-answer",
    query_type: str = "place_story",
    evidence: tuple[PackedEvidence, ...] | None = None,
) -> EvidencePack:
    return EvidencePack(
        query_id=query_id,
        query_type=query_type,
        policy_id="P0_rank_order",
        context_budget_chars=4200,
        total_estimated_chars=500,
        evidence=evidence
        if evidence is not None
        else (
            PackedEvidence(
                pack_rank=1,
                source_rank=1,
                retrieval_doc_id="child-palace",
                child_id="child-palace",
                parent_id="parent-palace",
                doc_id="doc-palace",
                score=0.99,
                estimated_chars=500,
                source_block_ids=("block-palace",),
                citation_block_ids=("block-palace",),
                citation_recoverable=True,
                packing_reason="retrieval_rank_order",
            ),
        ),
        target_child_covered=True,
        target_parent_covered=True,
        target_doc_covered=True,
        evidence_order_relevance_proxy=1.0,
    )


def test_citation_rag_assembler_builds_answer_contract_from_packed_evidence() -> None:
    assembler = CitationRagAnswerAssembler()
    answer = assembler.assemble(
        item=_eval_item(),
        evidence_pack=_evidence_pack(),
        draft=build_contract_only_draft(
            answer="경복궁은 한양의 중심 궁궐로, 조선의 정치적 출발점을 설명하기 좋은 장소입니다.",
            spoken_answer="경복궁은 조선의 시작과 한양의 중심을 함께 보여주는 장소입니다.",
            unsupported_claim_risk="low",
        ),
    )

    assert answer.contract_version == "citation-rag-answer/v1"
    assert answer.abstained is False
    assert answer.evidence_ids == (answer.citations[0].evidence_id,)
    assert answer.citations[0].child_id == "child-palace"
    assert answer.citations[0].source_block_ids == ("block-palace",)
    assert answer.place_ids == ("gyeongbokgung",)
    assert answer.unsupported_claim_risk == "low"


def test_citation_rag_assembler_abstains_without_evidence_for_no_answer_query() -> None:
    assembler = CitationRagAnswerAssembler()
    answer = assembler.assemble(
        item=_eval_item(
            query_id="q-contract-abstain",
            query_type="no_answer",
            expected_behavior="abstain",
        ),
        evidence_pack=_evidence_pack(
            query_id="q-contract-abstain",
            query_type="no_answer",
            evidence=(),
        ),
    )

    assert answer.abstained is True
    assert answer.citations == ()
    assert answer.evidence_ids == ()
    assert answer.unsupported_claim_risk == "low"


def test_non_abstained_answer_requires_draft_and_citations() -> None:
    assembler = CitationRagAnswerAssembler()

    with pytest.raises(ValueError, match="answer draft is required"):
        assembler.assemble(item=_eval_item(), evidence_pack=_evidence_pack())

    with pytest.raises(ValueError, match="non-abstained answer requires citations"):
        CitationRagAnswer(
            answer_policy_id="citation-rag-contract-v1",
            provider="fake",
            model_id="fake-model",
            query_id="q-contract-answer",
            query_type="place_story",
            answer="근거가 있는 답변입니다.",
            spoken_answer="근거가 있는 답변입니다.",
            citations=(),
            evidence_ids=(),
            place_ids=("gyeongbokgung",),
            abstained=False,
            unsupported_claim_risk="low",
        )


def test_citation_contract_rejects_unrecoverable_or_mismatched_citations() -> None:
    with pytest.raises(ValueError, match="citation_block_ids must cover source_block_ids"):
        Citation(
            citation_id="cit-one",
            evidence_id="ev-one",
            child_id="child-palace",
            parent_id="parent-palace",
            doc_id="doc-palace",
            source_rank=1,
            pack_rank=1,
            source_block_ids=("block-palace",),
            citation_block_ids=("block-other",),
            citation_recoverable=True,
        )

    with pytest.raises(ValueError, match="citation must be recoverable"):
        Citation(
            citation_id="cit-one",
            evidence_id="ev-one",
            child_id="child-palace",
            parent_id="parent-palace",
            doc_id="doc-palace",
            source_rank=1,
            pack_rank=1,
            source_block_ids=("block-palace",),
            citation_block_ids=("block-palace",),
            citation_recoverable=False,
        )


def test_answer_contract_rejects_private_path_and_secret_like_text() -> None:
    with pytest.raises(ValueError, match="private path"):
        CitationRagDraft(
            answer="F" + ":\\raw\\source.pdf",
            spoken_answer="안전한 음성 답변",
        )

    with pytest.raises(ValueError, match="secret-like"):
        CitationRagDraft(
            answer="안전한 답변",
            spoken_answer="s" + "k-proj-secret",
        )


def test_citation_rag_contract_report_has_public_safe_aggregate_rows() -> None:
    assembler = CitationRagAnswerAssembler()
    answers = [
        assembler.assemble(
            item=_eval_item(),
            evidence_pack=_evidence_pack(),
            draft=build_contract_only_draft(
                answer="경복궁은 한양의 중심 궁궐입니다.",
                spoken_answer="경복궁은 한양의 중심 궁궐입니다.",
                unsupported_claim_risk="low",
            ),
        ),
        assembler.assemble(
            item=_eval_item(
                query_id="q-contract-abstain",
                query_type="no_answer",
                expected_behavior="abstain",
            ),
            evidence_pack=_evidence_pack(
                query_id="q-contract-abstain",
                query_type="no_answer",
                evidence=(),
            ),
        ),
    ]
    summary = summarize_citation_rag_answers(answers)
    report = build_citation_rag_contract_report(answers=answers)

    assert summary.answer_count == 2
    assert summary.answered_count == 1
    assert summary.abstained_count == 1
    assert summary.citation_recoverability_rate == 1.0
    assert collect_citation_rag_contract_failures(summary, report.output_quality) == []
    assert report.output_quality.public_raw_text_leakage_count == 0
    assert report.output_quality.private_path_leakage_count == 0
