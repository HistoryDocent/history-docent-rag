from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.application.citation_rag import (
    CitationRagAnswerAssembler,
    build_contract_only_draft,
)
from app.application.evidence_packing import EvidencePack, PackedEvidence
from app.core.project_paths import (
    has_private_data_segment,
    is_repository_private_artifact_path,
    is_repository_private_write_path,
)
from app.domain.generation_eval import (
    GenerationEvalInput,
    GenerationEvalReport,
    GenerationEvalUsage,
    build_generation_eval_records,
    build_generation_eval_report,
    build_generation_eval_report_markdown,
    build_public_generation_eval_rows,
    collect_generation_eval_harness_failures,
)
from app.domain.retrieval import RetrievalEvalItem


DEFAULT_REPORT_PATH = Path("evals/reports/generation_eval_harness_report.md")
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data") / "evals" / "results" / "generation_eval_harness_results.jsonl"
)


def run_generation_eval_harness(
    *,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
) -> GenerationEvalReport:
    _validate_result_rows_path(result_rows_path)
    inputs = _build_smoke_inputs()
    provisional_report = build_generation_eval_report(inputs=inputs)
    provisional_markdown = build_generation_eval_report_markdown(provisional_report)
    report = build_generation_eval_report(
        inputs=inputs,
        report_text=provisional_markdown,
    )
    markdown = build_generation_eval_report_markdown(report)
    failures = collect_generation_eval_harness_failures(report)
    if failures:
        raise ValueError(f"generation eval harness gate failed: {failures}")

    records = build_generation_eval_records(inputs)
    rows = build_public_generation_eval_rows(records=records)
    write_jsonl_rows(path=result_rows_path, rows=rows)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(markdown, encoding="utf-8")
    return report


def write_jsonl_rows(*, path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows
    )
    path.write_text(payload + "\n", encoding="utf-8")


def _build_smoke_inputs() -> list[GenerationEvalInput]:
    assembler = CitationRagAnswerAssembler()
    answerable_item = _eval_item(
        query_id="q-generation-answer",
        query_type="place_story",
        expected_behavior="retrieve",
    )
    abstain_item = _eval_item(
        query_id="q-generation-abstain",
        query_type="no_answer",
        expected_behavior="abstain",
    )
    answers = [
        assembler.assemble(
            item=answerable_item,
            evidence_pack=_evidence_pack(
                query_id="q-generation-answer",
                query_type="place_story",
            ),
            draft=build_contract_only_draft(
                answer=(
                    "경복궁은 한양의 중심 궁궐로, 조선의 출발점을 설명하기 좋은 장소입니다."
                ),
                spoken_answer="경복궁은 조선의 시작과 한양의 중심을 함께 보여주는 장소입니다.",
                unsupported_claim_risk="low",
            ),
        ),
        assembler.assemble(
            item=abstain_item,
            evidence_pack=_evidence_pack(
                query_id="q-generation-abstain",
                query_type="no_answer",
                evidence=(),
            ),
        ),
    ]
    items = {
        answerable_item.query.query_id: answerable_item,
        abstain_item.query.query_id: abstain_item,
    }
    return [
        GenerationEvalInput(
            item=items[answer.query_id],
            answer=answer,
            packing_policy_id="P0_rank_order",
            retrieval_run_label="dense_multilingual_e5_small_voice_rewrite",
            provider_config_id="contract-only-v1",
            usage=GenerationEvalUsage(latency_ms=0.0),
        )
        for answer in answers
    ]


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
        total_estimated_chars=500
        if evidence is None
        else sum(item.estimated_chars for item in evidence),
        evidence=default_evidence if evidence is None else evidence,
        target_child_covered=True,
        target_parent_covered=True,
        target_doc_covered=True,
        evidence_order_relevance_proxy=1.0,
    )


def _validate_result_rows_path(path: Path) -> None:
    if has_private_data_segment(path) and not is_repository_private_artifact_path(path):
        raise ValueError("private_data result rows must stay under repository private_data")
    if has_private_data_segment(path) and not is_repository_private_write_path(path):
        raise ValueError("private generation eval rows must be written under private_data")


def main() -> int:
    args = _parse_args()
    report = run_generation_eval_harness(
        report_path=args.report,
        result_rows_path=args.result_rows,
    )
    failures = collect_generation_eval_harness_failures(report)
    print(
        "generation_eval "
        f"status={'PASS' if not failures else 'FAIL'} "
        f"eval_count={report.summary.eval_count} "
        f"correct_with_evidence={report.summary.correct_with_evidence_rate:.6f} "
        f"citation_precision={report.summary.citation_precision:.6f} "
        f"abstention_accuracy={report.summary.abstention_accuracy:.6f} "
        f"solar_call_count={report.summary.solar_call_count} "
        f"failures={len(failures)}",
    )
    return 0 if not failures else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run generation evaluation harness smoke report.",
    )
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--result-rows", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
