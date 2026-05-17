from __future__ import annotations

import json
import re
from pathlib import Path

from app.domain.retrieval import FORBIDDEN_PUBLIC_EVAL_FIELDS, RetrievalEvalItem
from pipelines.run_hyde_larger_dev_subset_readiness import (
    HYDE_LARGER_DEV_SUBSET_READINESS_REPORT_VERSION,
    TARGET_QUERY_TYPES,
    build_hyde_larger_dev_readiness_rows,
    build_hyde_larger_dev_readiness_summary,
    collect_hyde_larger_dev_readiness_failures,
    run_hyde_larger_dev_subset_readiness,
)


def test_hyde_larger_dev_subset_readiness_writes_public_safe_report(
    tmp_path: Path,
) -> None:
    dataset_path = _write_fixture_dataset(tmp_path)
    doc_path = tmp_path / "HYDE_LARGER_DEV_SUBSET_READINESS.md"
    report_path = tmp_path / "hyde_larger_dev_subset_readiness_report.md"
    rows_path = tmp_path / "hyde_larger_dev_subset_readiness_rows.jsonl"

    report = run_hyde_larger_dev_subset_readiness(
        dataset_path=dataset_path,
        expected_query_count_per_type=2,
        doc_path=doc_path,
        report_path=report_path,
        result_rows_path=rows_path,
    )
    doc_text = doc_path.read_text(encoding="utf-8")
    report_text = report_path.read_text(encoding="utf-8")
    rows = [json.loads(line) for line in rows_path.read_text(encoding="utf-8").splitlines()]

    assert report.report_version == HYDE_LARGER_DEV_SUBSET_READINESS_REPORT_VERSION
    assert collect_hyde_larger_dev_readiness_failures(report) == []
    assert report.summary.query_count == 8
    assert report.summary.target_query_type_count == 4
    assert report.summary.expected_query_count_per_type == 2
    assert report.summary.answerable_query_count == 6
    assert report.summary.no_answer_query_count == 2
    assert report.summary.expected_hyde_generation_live_call_count == 6
    assert report.summary.no_answer_guard_query_count == 2
    assert report.summary.solar_call_count == 0
    assert report.summary.readiness_decision == "ready_for_hyde_larger_live_approval"
    assert report.output_quality.public_raw_text_leakage_count == 0
    assert report.output_quality.private_path_leakage_count == 0
    assert report.output_quality.secret_like_leakage_count == 0
    assert report.output_quality.forbidden_result_field_count == 0
    assert "| readiness_decision | `ready_for_hyde_larger_live_approval` |" in doc_text
    assert "| public_raw_text_leakage_count | 0 |" in report_text
    assert all(FORBIDDEN_PUBLIC_EVAL_FIELDS.isdisjoint(row.keys()) for row in rows)


def test_hyde_larger_dev_subset_readiness_blocks_no_answer_generation(
    tmp_path: Path,
) -> None:
    dataset_path = _write_fixture_dataset(tmp_path)
    rows = build_hyde_larger_dev_readiness_rows(
        dataset_path=dataset_path,
        expected_query_count_per_type=2,
    )
    no_answer_rows = [row for row in rows if row.query_type == "no_answer"]
    answerable_rows = [row for row in rows if row.query_type != "no_answer"]

    assert len(no_answer_rows) == 2
    assert all(row.hyde_candidate_id == "blocked_for_no_answer_guard" for row in no_answer_rows)
    assert all(not row.hyde_generation_live_call_required for row in no_answer_rows)
    assert all(row.expected_hyde_generation_call_count == 0 for row in no_answer_rows)
    assert all(row.no_answer_guard_applied for row in no_answer_rows)
    assert all(row.hyde_generation_live_call_required for row in answerable_rows)
    assert {
        row.query_type for row in rows
    } == set(TARGET_QUERY_TYPES)


def test_hyde_larger_dev_subset_readiness_blocks_hard_cap_violation(
    tmp_path: Path,
) -> None:
    dataset_path = _write_fixture_dataset(tmp_path)
    rows = build_hyde_larger_dev_readiness_rows(
        dataset_path=dataset_path,
        expected_query_count_per_type=2,
    )
    summary = build_hyde_larger_dev_readiness_summary(
        rows=rows,
        expected_query_count_per_type=2,
        live_call_hard_cap=1,
    )

    assert summary.hard_cap_exceeded is True
    assert summary.readiness_decision == "blocked_by_readiness_gate"


def test_hyde_larger_dev_subset_readiness_public_docs_are_sanitized() -> None:
    public_paths = (
        Path("docs/HYDE_LARGER_DEV_SUBSET_READINESS.md"),
        Path("evals/reports/hyde_larger_dev_subset_readiness_report.md"),
    )

    for path in public_paths:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        assert "raw query" in text
        assert "chunk text" in text
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\\s*=", text)
        assert all(f"`{field}`" not in text for field in FORBIDDEN_PUBLIC_EVAL_FIELDS)


def _write_fixture_dataset(tmp_path: Path) -> Path:
    dataset_path = tmp_path / "retrieval_eval_dev.jsonl"
    payloads = []
    for query_type in TARGET_QUERY_TYPES:
        for index in range(1, 3):
            expected_behavior = "abstain" if query_type == "no_answer" else "retrieve"
            answerability = "unanswerable" if query_type == "no_answer" else "answerable"
            payloads.append(
                _eval_item(
                    query_id=f"q-dev-{query_type}-{index:03d}",
                    query_type=query_type,
                    expected_behavior=expected_behavior,
                    answerability=answerability,
                ).model_dump_json(),
            )
    dataset_path.write_text("\n".join(payloads) + "\n", encoding="utf-8")
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
