from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.application.citation_rag import (
    CitationRagAnswerAssembler,
    build_contract_only_draft,
)
from app.application.evidence_packing import EvidencePack, PackedEvidence
from app.application.generation_eval import GenerationEvaluationHarness
from app.domain.generation import Citation, CitationRagAnswer
from app.domain.generation_eval import (
    GenerationEvalInput,
    GenerationEvalUsage,
    build_generation_eval_records,
    build_generation_eval_report,
    build_generation_eval_report_markdown,
    build_public_generation_eval_rows,
    collect_generation_eval_harness_failures,
)
from app.domain.retrieval import RetrievalEvalItem
from pipelines.run_generation_eval_harness import run_generation_eval_harness


def _eval_item(
    *,
    query_id: str = "q-generation-answer",
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
            },
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
        },
    )


def _evidence_pack(
    *,
    query_id: str = "q-generation-answer",
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


def _answer() -> CitationRagAnswer:
    assembler = CitationRagAnswerAssembler()
    return assembler.assemble(
        item=_eval_item(),
        evidence_pack=_evidence_pack(),
        draft=build_contract_only_draft(
            answer="경복궁은 한양의 중심 궁궐로, 조선의 정치적 출발점을 설명하기 좋은 장소입니다.",
            spoken_answer="경복궁은 조선의 시작과 한양의 중심을 함께 보여주는 장소입니다.",
            unsupported_claim_risk="low",
        ),
    )


def _wrong_citation_answer() -> CitationRagAnswer:
    citation = Citation(
        citation_id="cit-wrong",
        evidence_id="ev-wrong",
        child_id="child-other",
        parent_id="parent-other",
        doc_id="doc-other",
        source_rank=1,
        pack_rank=1,
        source_block_ids=("block-other",),
        citation_block_ids=("block-other",),
        citation_recoverable=True,
    )
    return CitationRagAnswer(
        answer_policy_id="citation-rag-contract-v1",
        provider="fake",
        model_id="fake-model",
        query_id="q-generation-answer",
        query_type="place_story",
        answer="경복궁에 대한 근거가 부족한 답변입니다.",
        spoken_answer="경복궁에 대한 근거가 부족한 답변입니다.",
        citations=(citation,),
        evidence_ids=("ev-wrong",),
        place_ids=("gyeongbokgung",),
        abstained=False,
        unsupported_claim_risk="low",
    )


def test_generation_eval_scores_correct_answer_with_evidence() -> None:
    report = build_generation_eval_report(
        inputs=[
            GenerationEvalInput(
                item=_eval_item(),
                answer=_answer(),
                packing_policy_id="P0_rank_order",
                retrieval_run_label="dense_multilingual_e5_small_voice_rewrite",
                provider_config_id="contract-only-v1",
                usage=GenerationEvalUsage(latency_ms=12.0),
            ),
        ],
    )

    assert report.summary.eval_count == 1
    assert report.summary.correct_with_evidence_rate == 1.0
    assert report.summary.citation_precision == 1.0
    assert report.summary.citation_recall == 1.0
    assert report.summary.place_relevance == 1.0
    assert report.summary.unsupported_claim_rate == 0.0
    assert report.summary.latency_p95_ms == 12.0


def test_generation_eval_flags_wrong_citation_as_unsupported() -> None:
    report = build_generation_eval_report(
        inputs=[
            GenerationEvalInput(
                item=_eval_item(),
                answer=_wrong_citation_answer(),
                packing_policy_id="P0_rank_order",
                retrieval_run_label="dense_multilingual_e5_small_voice_rewrite",
                provider_config_id="fake-v1",
            ),
        ],
    )

    assert report.summary.correct_with_evidence_rate == 0.0
    assert report.summary.citation_precision == 0.0
    assert report.summary.citation_recall == 0.0
    assert report.summary.unsupported_claim_rate == 1.0


def test_generation_eval_measures_no_answer_abstention() -> None:
    assembler = CitationRagAnswerAssembler()
    item = _eval_item(
        query_id="q-generation-abstain",
        query_type="no_answer",
        expected_behavior="abstain",
    )
    answer = assembler.assemble(
        item=item,
        evidence_pack=_evidence_pack(
            query_id="q-generation-abstain",
            query_type="no_answer",
            evidence=(),
        ),
    )
    report = build_generation_eval_report(
        inputs=[
            GenerationEvalInput(
                item=item,
                answer=answer,
                packing_policy_id="P0_rank_order",
            ),
        ],
    )

    assert report.summary.no_answer_count == 1
    assert report.summary.abstention_accuracy == 1.0
    assert report.summary.docent_usefulness == 1.0
    assert report.summary.solar_call_count == 0


def test_generation_eval_public_rows_do_not_include_raw_answer_text() -> None:
    inputs = [
        GenerationEvalInput(
            item=_eval_item(),
            answer=_answer(),
            packing_policy_id="P0_rank_order",
        ),
    ]
    records = build_generation_eval_records(inputs)
    rows = build_public_generation_eval_rows(records=records)
    report = build_generation_eval_report(inputs=inputs)
    markdown = build_generation_eval_report_markdown(report)

    assert "answer" not in rows[0]
    assert "spoken_answer" not in rows[0]
    assert "경복궁은 한양의 중심 궁궐" not in json.dumps(
        rows,
        ensure_ascii=False,
    )
    assert "경복궁은 한양의 중심 궁궐" not in markdown
    assert collect_generation_eval_harness_failures(report) == []


def test_generation_evaluation_harness_validates_answer_inputs() -> None:
    harness = GenerationEvaluationHarness()
    answer = _answer()

    report = harness.evaluate(
        items_by_query_id={answer.query_id: _eval_item()},
        answers=[answer],
        packing_policy_id="P0_rank_order",
        retrieval_run_label="dense_multilingual_e5_small_voice_rewrite",
        provider_config_id="contract-only-v1",
    )

    assert report.summary.eval_count == 1
    assert report.summary.correct_with_evidence_rate == 1.0

    with pytest.raises(ValueError, match="RetrievalEvalItem"):
        harness.evaluate(
            items_by_query_id={},
            answers=[answer],
            packing_policy_id="P0_rank_order",
            retrieval_run_label="dense_multilingual_e5_small_voice_rewrite",
            provider_config_id="contract-only-v1",
        )


def test_run_generation_eval_harness_writes_public_safe_report(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "generation_eval_harness_report.md"
    rows_path = tmp_path / "generation_eval_harness_results.jsonl"

    report = run_generation_eval_harness(
        report_path=report_path,
        result_rows_path=rows_path,
    )
    markdown = report_path.read_text(encoding="utf-8")
    rows_text = rows_path.read_text(encoding="utf-8")

    assert report.report_version == "generation-eval-report/v1"
    assert report.summary.eval_count == 2
    assert "## 정량 리포트" in markdown
    assert "## 정성 리포트" in markdown
    assert "raw answer text" in markdown
    assert "경복궁은 한양의 중심 궁궐" not in markdown
    assert "경복궁은 한양의 중심 궁궐" not in rows_text
