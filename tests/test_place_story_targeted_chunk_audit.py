from __future__ import annotations

import json
import re
from pathlib import Path

from app.domain.retrieval import FORBIDDEN_PUBLIC_EVAL_FIELDS, RetrievalEvalItem
from pipelines.run_place_story_targeted_chunk_audit import (
    PLACE_STORY_TARGETED_CHUNK_AUDIT_REPORT_VERSION,
    collect_place_story_targeted_chunk_audit_failures,
    run_place_story_targeted_chunk_audit,
)


def test_place_story_targeted_chunk_audit_writes_public_safe_report(
    tmp_path: Path,
) -> None:
    inputs = _write_fixture_inputs(tmp_path)
    doc_path = tmp_path / "PLACE_STORY_TARGETED_CHUNK_AUDIT.md"
    report_path = tmp_path / "place_story_targeted_chunk_audit_report.md"
    result_rows_path = tmp_path / "place_story_targeted_chunk_audit_rows.jsonl"

    report = run_place_story_targeted_chunk_audit(
        dataset_path=inputs["dataset"],
        chunks_path=inputs["chunks"],
        hard_case_rows_path=inputs["hard_case_rows"],
        doc_path=doc_path,
        report_path=report_path,
        result_rows_path=result_rows_path,
    )
    doc_text = doc_path.read_text(encoding="utf-8")
    report_text = report_path.read_text(encoding="utf-8")
    rows = [
        json.loads(line)
        for line in result_rows_path.read_text(encoding="utf-8").splitlines()
    ]

    assert report.report_version == PLACE_STORY_TARGETED_CHUNK_AUDIT_REPORT_VERSION
    assert collect_place_story_targeted_chunk_audit_failures(report) == []
    assert report.summary.audit_case_count == 1
    assert report.summary.target_child_exists_rate == 1.0
    assert report.summary.target_parent_exists_rate == 1.0
    assert report.summary.target_child_parent_membership_rate == 1.0
    assert report.summary.target_child_citation_ref_rate == 1.0
    assert report.summary.chunk_generation_loss_count == 0
    assert report.summary.chunk_boundary_defect_count == 0
    assert report.summary.parser_noise_observed_count == 1
    assert report.summary.retrieved_target_child_count == 0
    assert report.summary.retrieved_target_parent_count == 0
    assert report.summary.retrieved_target_doc_count == 1
    assert report.summary.reopen_global_chunking_count == 0
    assert report.summary.recommended_decision == "do_not_reopen_global_chunking"
    assert report.output_quality.public_raw_text_leakage_count == 0
    assert report.output_quality.private_path_leakage_count == 0
    assert report.output_quality.secret_like_leakage_count == 0
    assert report.output_quality.forbidden_result_field_count == 0
    assert "| recommended_decision | `do_not_reopen_global_chunking` |" in doc_text
    assert "| public_raw_text_leakage_count | 0 |" in report_text
    assert all(FORBIDDEN_PUBLIC_EVAL_FIELDS.isdisjoint(row.keys()) for row in rows)


def test_place_story_targeted_chunk_audit_public_docs_are_sanitized() -> None:
    public_paths = (
        Path("docs/PLACE_STORY_TARGETED_CHUNK_AUDIT.md"),
        Path("evals/reports/place_story_targeted_chunk_audit_report.md"),
    )

    for path in public_paths:
        text = path.read_text(encoding="utf-8")
        assert "raw query" in text
        assert "chunk text" in text
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\\s*=", text)
        assert all(f"`{field}`" not in text for field in FORBIDDEN_PUBLIC_EVAL_FIELDS)


def _write_fixture_inputs(tmp_path: Path) -> dict[str, Path]:
    dataset_path = tmp_path / "retrieval_eval_dev.jsonl"
    chunks_path = tmp_path / "parent_child_chunks.json"
    hard_case_rows_path = tmp_path / "place_story_hard_case_analysis_rows.jsonl"
    dataset_path.write_text(_eval_item().model_dump_json() + "\n", encoding="utf-8")
    chunks_path.write_text(
        json.dumps(
            {
                "parents": [
                    {
                        "parent_id": "fixture-parent-palace",
                        "child_ids": ["fixture-child-story"],
                        "quality_flags": ["replacement_character"],
                    },
                ],
                "children": [
                    {
                        "child_id": "fixture-child-story",
                        "parent_id": "fixture-parent-palace",
                        "doc_id": "fixture-doc-history",
                        "text_length": 321,
                        "citation_refs": [{"source_block_id": "fixture-block-001"}],
                        "quality_flags": ["replacement_character"],
                        "page_span": {
                            "page_local_start": 1,
                            "page_local_end": 1,
                            "page_global_start": 10,
                            "page_global_end": 10,
                        },
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    hard_case_rows_path.write_text(
        json.dumps(
            {
                "query_id": "q-dev-place-story-001",
                "target_child_covered": False,
                "target_parent_covered": False,
                "target_doc_covered": True,
                "target_min_retrieval_rank": 5,
                "target_min_pack_rank": 5,
                "root_cause_decision": "target_grain_mismatch",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "dataset": dataset_path,
        "chunks": chunks_path,
        "hard_case_rows": hard_case_rows_path,
    }


def _eval_item() -> RetrievalEvalItem:
    return RetrievalEvalItem.model_validate(
        {
            "dataset_version": "retrieval-eval-dataset/v2",
            "query": {
                "query_id": "q-dev-place-story-001",
                "query_type": "place_story",
                "query_text": "fixture public-safe query text",
                "language": "ko",
                "expected_behavior": "retrieve",
                "user_context": None,
                "public_allowed": True,
            },
            "judgments": [
                {
                    "query_id": "q-dev-place-story-001",
                    "relevant_child_ids": ["fixture-child-story"],
                    "relevant_parent_ids": ["fixture-parent-palace"],
                    "relevant_doc_ids": ["fixture-doc-history"],
                    "relevance_grade": 3,
                    "rationale_summary": "fixture target",
                    "public_allowed": True,
                },
            ],
            "metadata": {
                "split": "dev",
                "difficulty": "hard",
                "place_ids": ["gyeongbokgung"],
                "requires_context": False,
                "answerability": "answerable",
                "review_status": "reviewed",
            },
        },
    )
