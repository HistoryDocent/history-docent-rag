from __future__ import annotations

import json
from pathlib import Path

from app.application.chat_retrieval import StaticRetrievalBackend
from app.domain.retrieval import FORBIDDEN_PUBLIC_EVAL_FIELDS, RetrievalEvalItem
from pipelines.run_place_story_target_grain_coverage import (
    PLACE_STORY_TARGET_GRAIN_COVERAGE_REPORT_VERSION,
    build_place_story_target_grain_coverage_row,
    collect_place_story_target_grain_coverage_failures,
    run_place_story_target_grain_coverage,
)


def test_place_story_target_grain_coverage_writes_public_safe_report(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "retrieval_eval_dev.jsonl"
    report_path = tmp_path / "place_story_target_grain_coverage_report.md"
    result_rows_path = tmp_path / "place_story_target_grain_coverage_rows.jsonl"
    raw_query = "테스트 원문 질문: 경복궁 이야기를 들려줘"
    items = [
        _eval_item(
            query_id="q-dev-place-story-001",
            raw_query=raw_query,
            child_ids=["fixture-child-gyeongbokgung"],
            parent_ids=["fixture-parent-palace"],
            doc_ids=["fixture-doc-history"],
        ),
        _eval_item(
            query_id="q-dev-place-story-002",
            raw_query="두 번째 원문 질문",
            child_ids=["missing-child"],
            parent_ids=["fixture-parent-palace"],
            doc_ids=["fixture-doc-history"],
        ),
    ]
    dataset_path.write_text(
        "\n".join(item.model_dump_json() for item in items) + "\n",
        encoding="utf-8",
    )

    report = run_place_story_target_grain_coverage(
        dataset_path=dataset_path,
        chunks_path=tmp_path / "unused_chunks.json",
        report_path=report_path,
        result_rows_path=result_rows_path,
        retrieval_backend=StaticRetrievalBackend(),
    )
    markdown = report_path.read_text(encoding="utf-8")
    rows = [
        json.loads(line)
        for line in result_rows_path.read_text(encoding="utf-8").splitlines()
    ]

    assert report.report_version == PLACE_STORY_TARGET_GRAIN_COVERAGE_REPORT_VERSION
    assert report.summary.analyzed_query_count == 2
    assert report.summary.target_child_covered_count == 1
    assert report.summary.target_parent_covered_count == 2
    assert report.summary.target_doc_covered_count == 2
    assert report.summary.target_child_recall_at_5 == 0.5
    assert report.summary.target_parent_recall_at_5 == 1.0
    assert report.summary.target_doc_recall_at_5 == 1.0
    assert report.summary.hard_case_count == 1
    assert report.summary.recommended_decision == "inspect_judgment_target_grain"
    assert collect_place_story_target_grain_coverage_failures(report) == []
    assert report.output_quality.public_raw_text_leakage_count == 0
    assert report.output_quality.private_path_leakage_count == 0
    assert report.output_quality.secret_like_leakage_count == 0
    assert raw_query not in markdown
    assert "target_too_narrow" in markdown
    assert all(FORBIDDEN_PUBLIC_EVAL_FIELDS.isdisjoint(row.keys()) for row in rows)


def test_place_story_target_grain_row_classifies_target_too_narrow() -> None:
    item = _eval_item(
        query_id="q-dev-place-story-002",
        raw_query="경복궁 이야기를 들려줘",
        child_ids=["missing-child"],
        parent_ids=["fixture-parent-palace"],
        doc_ids=["fixture-doc-history"],
    )
    retrieval = StaticRetrievalBackend().retrieve(command=_command_like(), item=item)

    row = build_place_story_target_grain_coverage_row(
        item=item,
        evidence_pack=retrieval.evidence_pack,
        retrieval_method=retrieval.retrieval_method,
        retrieval_candidate_count=retrieval.retrieval_candidate_count,
        total_latency_ms=retrieval.retrieval_latency_ms,
        query_rewrite_changed=False,
        query_rewrite_applied_rule_count=0,
    )

    assert row.target_child_covered is False
    assert row.target_parent_covered is True
    assert row.target_doc_covered is True
    assert row.target_parent_min_retrieval_rank == 1
    assert row.target_doc_min_retrieval_rank == 1
    assert row.hard_case is True
    assert "target_too_narrow" in row.failure_tags
    assert row.next_action == "judgment target grain과 parent/doc context coverage를 점검한다."


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
    raw_query: str,
    child_ids: list[str],
    parent_ids: list[str],
    doc_ids: list[str],
) -> RetrievalEvalItem:
    return RetrievalEvalItem.model_validate(
        {
            "dataset_version": "retrieval-eval-dataset/v2",
            "query": {
                "query_id": query_id,
                "query_type": "place_story",
                "query_text": raw_query,
                "language": "ko",
                "expected_behavior": "retrieve",
                "user_context": None,
                "public_allowed": True,
            },
            "judgments": [
                {
                    "query_id": query_id,
                    "relevant_child_ids": child_ids,
                    "relevant_parent_ids": parent_ids,
                    "relevant_doc_ids": doc_ids,
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
