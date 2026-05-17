from __future__ import annotations

import json
import re
from pathlib import Path

from app.domain.retrieval import FORBIDDEN_PUBLIC_EVAL_FIELDS, RetrievalEvalItem
from pipelines.run_hyde_subset_readiness import (
    HYDE_SUBSET_READINESS_REPORT_VERSION,
    build_hyde_subset_readiness_rows,
    build_hyde_subset_readiness_summary,
    collect_hyde_subset_readiness_failures,
    run_hyde_subset_readiness,
)


def test_hyde_subset_readiness_writes_public_safe_report(tmp_path: Path) -> None:
    dataset_path = _write_fixture_dataset(tmp_path)
    doc_path = tmp_path / "HYDE_SUBSET_READINESS.md"
    report_path = tmp_path / "hyde_subset_readiness_report.md"
    rows_path = tmp_path / "hyde_subset_readiness_rows.jsonl"

    report = run_hyde_subset_readiness(
        dataset_path=dataset_path,
        doc_path=doc_path,
        report_path=report_path,
        result_rows_path=rows_path,
    )
    doc_text = doc_path.read_text(encoding="utf-8")
    report_text = report_path.read_text(encoding="utf-8")
    rows = [json.loads(line) for line in rows_path.read_text(encoding="utf-8").splitlines()]

    assert report.report_version == HYDE_SUBSET_READINESS_REPORT_VERSION
    assert collect_hyde_subset_readiness_failures(report) == []
    assert report.summary.query_count == 5
    assert report.summary.query_type_count == 4
    assert report.summary.answerable_query_count == 4
    assert report.summary.no_answer_query_count == 1
    assert report.summary.hyde_candidate_query_count == 4
    assert report.summary.no_answer_guard_query_count == 1
    assert report.summary.expected_hyde_generation_live_call_count == 4
    assert report.summary.live_call_hard_cap == 10
    assert report.summary.solar_call_count == 0
    assert report.summary.readiness_decision == "ready_for_hyde_live_approval"
    assert report.output_quality.public_raw_text_leakage_count == 0
    assert report.output_quality.private_path_leakage_count == 0
    assert report.output_quality.secret_like_leakage_count == 0
    assert report.output_quality.forbidden_result_field_count == 0
    assert "| readiness_decision | `ready_for_hyde_live_approval` |" in doc_text
    assert "| public_raw_text_leakage_count | 0 |" in report_text
    assert all(FORBIDDEN_PUBLIC_EVAL_FIELDS.isdisjoint(row.keys()) for row in rows)


def test_hyde_subset_readiness_blocks_no_answer_hyde_generation(
    tmp_path: Path,
) -> None:
    dataset_path = _write_fixture_dataset(tmp_path)
    rows = build_hyde_subset_readiness_rows(dataset_path=dataset_path)
    by_query_type = {row.query_type: row for row in rows}

    assert by_query_type["no_answer"].hyde_candidate_id == "blocked_for_no_answer_guard"
    assert by_query_type["no_answer"].hyde_generation_live_call_required is False
    assert by_query_type["no_answer"].expected_hyde_generation_call_count == 0
    assert by_query_type["no_answer"].no_answer_guard_applied is True
    assert by_query_type["relationship"].baseline_candidate_id == (
        "hybrid_weighted_e5_small_alpha_0_5_reference"
    )


def test_hyde_subset_readiness_blocks_hard_cap_violation(tmp_path: Path) -> None:
    dataset_path = _write_fixture_dataset(tmp_path)
    rows = build_hyde_subset_readiness_rows(dataset_path=dataset_path)
    summary = build_hyde_subset_readiness_summary(
        rows=rows,
        live_call_hard_cap=1,
    )

    assert summary.hard_cap_exceeded is True
    assert summary.readiness_decision == "blocked_by_readiness_gate"


def test_hyde_subset_readiness_public_docs_are_sanitized() -> None:
    public_paths = (
        Path("docs/HYDE_SUBSET_READINESS.md"),
        Path("evals/reports/hyde_subset_readiness_report.md"),
    )

    for path in public_paths:
        text = path.read_text(encoding="utf-8")
        assert "raw query" in text
        assert "chunk text" in text
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\\s*=", text)
        assert all(f"`{field}`" not in text for field in FORBIDDEN_PUBLIC_EVAL_FIELDS)


def _write_fixture_dataset(tmp_path: Path) -> Path:
    dataset_path = tmp_path / "retrieval_eval_dev.jsonl"
    dataset_path.write_text(
        "\n".join(
            _eval_item(
                query_id=query_id,
                query_type=query_type,
                expected_behavior=expected_behavior,
                answerability=answerability,
            ).model_dump_json()
            for query_id, query_type, expected_behavior, answerability in (
                (
                    "q-dev-place-story-001",
                    "place_story",
                    "retrieve",
                    "answerable",
                ),
                (
                    "q-dev-place-story-008",
                    "place_story",
                    "retrieve",
                    "answerable",
                ),
                (
                    "q-dev-relationship-008",
                    "relationship",
                    "retrieve",
                    "answerable",
                ),
                ("q-dev-overview-010", "overview", "retrieve", "answerable"),
                ("q-dev-no-answer-001", "no_answer", "abstain", "unanswerable"),
            )
        )
        + "\n",
        encoding="utf-8",
    )
    return dataset_path


def _eval_item(
    *,
    query_id: str,
    query_type: str,
    expected_behavior: str,
    answerability: str,
) -> RetrievalEvalItem:
    judgments = []
    if expected_behavior == "retrieve":
        judgments.append(
            {
                "query_id": query_id,
                "relevant_child_ids": [f"fixture-child-{query_id}"],
                "relevant_parent_ids": [f"fixture-parent-{query_id}"],
                "relevant_doc_ids": [f"fixture-doc-{query_id}"],
                "relevance_grade": 3,
                "rationale_summary": "fixture target",
                "public_allowed": True,
            },
        )
    return RetrievalEvalItem.model_validate(
        {
            "dataset_version": "retrieval-eval-dataset/v2",
            "query": {
                "query_id": query_id,
                "query_type": query_type,
                "query_text": f"fixture query {query_id}",
                "language": "ko",
                "expected_behavior": expected_behavior,
                "user_context": None,
                "public_allowed": True,
            },
            "judgments": judgments,
            "metadata": {
                "split": "dev",
                "difficulty": "hard",
                "place_ids": ["gyeongbokgung"],
                "requires_context": False,
                "answerability": answerability,
                "review_status": "reviewed",
            },
        },
    )
