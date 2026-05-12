from __future__ import annotations

import argparse
from pathlib import Path

from app.application.citation_rag import (
    CitationRagAnswerAssembler,
    build_contract_only_draft,
)
from app.application.evidence_packing import EvidencePack, PackedEvidence
from app.domain.generation import (
    build_citation_rag_contract_report,
    build_citation_rag_contract_report_markdown,
    collect_citation_rag_contract_failures,
)
from app.domain.retrieval import RetrievalEvalItem


DEFAULT_REPORT_PATH = Path("evals/reports/citation_rag_answer_contract_report.md")


def build_report(
    *,
    report_path: Path = DEFAULT_REPORT_PATH,
) -> None:
    assembler = CitationRagAnswerAssembler()
    answers = [
        assembler.assemble(
            item=_eval_item(
                query_id="q-contract-answer",
                query_type="place_story",
                expected_behavior="retrieve",
            ),
            evidence_pack=_evidence_pack(
                query_id="q-contract-answer",
                query_type="place_story",
            ),
            draft=build_contract_only_draft(
                answer="경복궁은 한양의 중심 궁궐로, 조선의 출발점을 설명하기 좋은 장소입니다.",
                spoken_answer="경복궁은 조선의 시작과 한양의 중심을 함께 보여주는 장소입니다.",
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
    provisional_report = build_citation_rag_contract_report(answers=answers)
    report_text = build_citation_rag_contract_report_markdown(provisional_report)
    report = build_citation_rag_contract_report(
        answers=answers,
        report_text=report_text,
    )
    failures = collect_citation_rag_contract_failures(
        report.summary,
        report.output_quality,
    )
    if failures:
        raise ValueError(f"citation RAG contract report gate failed: {failures}")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        build_citation_rag_contract_report_markdown(report),
        encoding="utf-8",
    )
    print(
        "citation_rag_contract "
        "status=PASS "
        f"answer_count={report.summary.answer_count} "
        f"citation_count={report.summary.citation_count} "
        f"citation_recoverability={report.summary.citation_recoverability_rate:.6f} "
        f"failures={len(failures)}"
    )


def _eval_item(
    *,
    query_id: str,
    query_type: str,
    expected_behavior: str,
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
                "place_ids": ["gyeongbokgung"]
                if expected_behavior == "retrieve"
                else [],
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
    query_id: str,
    query_type: str,
    evidence: tuple[PackedEvidence, ...] | None = None,
) -> EvidencePack:
    default_evidence = (
        PackedEvidence(
            pack_rank=1,
            source_rank=1,
            retrieval_doc_id="child-palace",
            child_id="child-palace",
            parent_id="parent-palace",
            doc_id="doc-palace",
            score=1.0,
            estimated_chars=500,
            source_block_ids=("block-palace",),
            citation_block_ids=("block-palace",),
            citation_recoverable=True,
            packing_reason="retrieval_rank_order",
        ),
    )
    return EvidencePack(
        query_id=query_id,
        query_type=query_type,
        policy_id="P0_rank_order",
        context_budget_chars=4200,
        total_estimated_chars=500 if evidence is None else sum(
            item.estimated_chars for item in evidence
        ),
        evidence=default_evidence if evidence is None else evidence,
        target_child_covered=True,
        target_parent_covered=True,
        target_doc_covered=True,
        evidence_order_relevance_proxy=1.0,
    )


def main() -> int:
    args = _parse_args()
    build_report(report_path=args.report)
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build citation RAG answer contract public-safe report."
    )
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())

