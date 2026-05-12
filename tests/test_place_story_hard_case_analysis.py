from __future__ import annotations

import json
from pathlib import Path

from app.application.chat_retrieval import StaticRetrievalBackend
from app.domain.retrieval import FORBIDDEN_PUBLIC_EVAL_FIELDS, RetrievalEvalItem
from pipelines.run_place_story_hard_case_analysis import (
    PLACE_STORY_HARD_CASE_ANALYSIS_REPORT_VERSION,
    build_place_story_hard_case_diagnostic_row,
    collect_place_story_hard_case_analysis_failures,
    run_place_story_hard_case_analysis,
)
from pipelines.run_solar_generation_v2_tradeoff_analysis import (
    SolarGenerationV2PairedMetricRow,
)


def test_place_story_hard_case_analysis_writes_public_safe_report(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "retrieval_eval_dev.jsonl"
    generation_rows_path = tmp_path / "solar_generation_contract_v2_live_results.jsonl"
    report_path = tmp_path / "place_story_hard_case_analysis_report.md"
    result_rows_path = tmp_path / "place_story_hard_case_rows.jsonl"
    raw_query = "테스트 원문 질문: 경복궁 이야기를 들려줘"

    dataset_path.write_text(
        _eval_item(
            query_id="q-dev-place-story-001",
            query_type="place_story",
            raw_query=raw_query,
        ).model_dump_json()
        + "\n",
        encoding="utf-8",
    )
    generation_rows_path.write_text(
        json.dumps(_generation_row(), ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    report = run_place_story_hard_case_analysis(
        query_id="q-dev-place-story-001",
        dataset_path=dataset_path,
        chunks_path=tmp_path / "unused_chunks.json",
        generation_rows_path=generation_rows_path,
        report_path=report_path,
        result_rows_path=result_rows_path,
        retrieval_backend=StaticRetrievalBackend(),
    )
    markdown = report_path.read_text(encoding="utf-8")
    rows = [
        json.loads(line)
        for line in result_rows_path.read_text(encoding="utf-8").splitlines()
    ]

    assert report.report_version == PLACE_STORY_HARD_CASE_ANALYSIS_REPORT_VERSION
    assert report.summary.analyzed_query_count == 1
    assert report.summary.target_child_covered_count == 1
    assert report.summary.target_parent_covered_count == 1
    assert report.summary.target_doc_covered_count == 1
    assert report.summary.generation_regression_count == 1
    assert report.summary.root_cause_decision == "generation_contract_candidate"
    assert collect_place_story_hard_case_analysis_failures(report) == []
    assert report.output_quality.public_raw_text_leakage_count == 0
    assert report.output_quality.private_path_leakage_count == 0
    assert report.output_quality.secret_like_leakage_count == 0
    assert raw_query not in markdown
    assert "generation_contract_candidate" in markdown
    assert all(FORBIDDEN_PUBLIC_EVAL_FIELDS.isdisjoint(row.keys()) for row in rows)


def test_place_story_hard_case_diagnostic_identifies_generation_contract_candidate() -> None:
    item = _eval_item(
        query_id="q-dev-place-story-001",
        query_type="place_story",
        raw_query="경복궁 이야기를 들려줘",
    )
    retrieval = StaticRetrievalBackend().retrieve(
        command=_command_like(),
        item=item,
    )
    generation_row = SolarGenerationV2PairedMetricRow.model_validate(_generation_row())

    diagnostic = build_place_story_hard_case_diagnostic_row(
        item=item,
        evidence_pack=retrieval.evidence_pack,
        retrieval_method=retrieval.retrieval_method,
        retrieval_candidate_count=retrieval.retrieval_candidate_count,
        query_rewrite_changed=False,
        query_rewrite_applied_rule_count=0,
        generation_row=generation_row,
    )

    assert diagnostic.target_child_covered is True
    assert diagnostic.target_parent_covered is True
    assert diagnostic.target_doc_covered is True
    assert diagnostic.target_min_retrieval_rank == 1
    assert diagnostic.target_min_pack_rank == 1
    assert diagnostic.generation_correctness_regression is True
    assert diagnostic.generation_unsupported_regression is True
    assert diagnostic.root_cause_decision == "generation_contract_candidate"
    assert "target_child_in_pack" in diagnostic.diagnostic_tags
    assert "generation_correctness_regression" in diagnostic.diagnostic_tags


def _command_like():
    class Command:
        request_id = "q-dev-place-story-001"
        query = "경복궁 이야기를 들려줘"
        language = "ko"
        query_type = "place_story"
        place_context = ("gyeongbokgung",)
        voice_mode = False
        user_context = None

    return Command()


def _eval_item(
    *,
    query_id: str,
    query_type: str,
    raw_query: str,
) -> RetrievalEvalItem:
    return RetrievalEvalItem.model_validate(
        {
            "dataset_version": "retrieval-eval-dataset/v2",
            "query": {
                "query_id": query_id,
                "query_type": query_type,
                "query_text": raw_query,
                "language": "ko",
                "expected_behavior": "retrieve",
                "user_context": None,
                "public_allowed": True,
            },
            "judgments": [
                {
                    "query_id": query_id,
                    "relevant_child_ids": ["fixture-child-gyeongbokgung"],
                    "relevant_parent_ids": ["fixture-parent-palace"],
                    "relevant_doc_ids": ["fixture-doc-history"],
                    "relevance_grade": 3,
                    "rationale_summary": "fixture target",
                    "public_allowed": True,
                },
            ],
            "metadata": {
                "split": "dev",
                "difficulty": "medium",
                "place_ids": ["gyeongbokgung"],
                "requires_context": False,
                "answerability": "answerable",
                "review_status": "reviewed",
            },
        },
    )


def _generation_row() -> dict:
    return {
        "baseline_answer_policy_id": "solar-generation-baseline-v1",
        "candidate_answer_policy_id": "solar-generation-contract-v2",
        "query_id": "q-dev-place-story-001",
        "query_type": "place_story",
        "v1_correct_with_evidence": True,
        "v2_correct_with_evidence": False,
        "correct_with_evidence_delta": -1,
        "v1_citation_precision": 0.2,
        "v2_citation_precision": 0.0,
        "citation_precision_delta": -0.2,
        "v1_citation_recall": 0.125,
        "v2_citation_recall": 0.0,
        "citation_recall_delta": -0.125,
        "unsupported_claim_delta": 1,
        "v1_citation_count": 5,
        "v2_citation_count": 1,
        "citation_count_delta": -4,
        "latency_ms_delta": 865.5607,
    }
