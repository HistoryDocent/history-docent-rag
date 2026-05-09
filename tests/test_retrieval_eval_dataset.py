from __future__ import annotations

from pathlib import Path

from app.domain.retrieval import (
    REQUIRED_QUERY_TYPES,
    collect_retrieval_eval_dataset_failures,
    load_retrieval_eval_jsonl,
    summarize_retrieval_eval_dataset,
)


def test_retrieval_eval_seed_dataset_passes_public_gate() -> None:
    items = load_retrieval_eval_jsonl(Path("evals/datasets/retrieval_eval_seed.jsonl"))

    summary = summarize_retrieval_eval_dataset(items)

    assert summary.dataset_version == "retrieval-eval-dataset/v1"
    assert summary.query_count == 14
    assert summary.judgment_count == 12
    assert summary.retrieve_query_count == 12
    assert summary.abstain_query_count == 2
    assert summary.query_type_distribution == {
        query_type: 2 for query_type in REQUIRED_QUERY_TYPES
    }
    assert summary.missing_required_query_type_count == 0
    assert summary.missing_expected_target_count == 0
    assert summary.judgment_query_mismatch_count == 0
    assert summary.public_raw_text_leakage_count == 0
    assert summary.private_path_leakage_count == 0
    assert collect_retrieval_eval_dataset_failures(summary) == []


def test_retrieval_eval_seed_uses_only_public_safe_judgment_fields() -> None:
    items = load_retrieval_eval_jsonl(Path("evals/datasets/retrieval_eval_seed.jsonl"))

    for item in items:
        assert item.query.public_allowed is True
        for judgment in item.judgments:
            assert judgment.public_allowed is True
            assert judgment.rationale_summary
            assert not any("\n" in target for target in judgment.relevant_child_ids)
            assert not any("\n" in target for target in judgment.relevant_parent_ids)
            assert not any("\n" in target for target in judgment.relevant_doc_ids)


def test_retrieval_eval_dataset_doc_matches_seed_summary() -> None:
    items = load_retrieval_eval_jsonl(Path("evals/datasets/retrieval_eval_seed.jsonl"))
    summary = summarize_retrieval_eval_dataset(items)
    doc = Path("docs/RETRIEVAL_EVAL_DATASET.md").read_text(encoding="utf-8")

    expected_fragments = [
        f"| query_count | {summary.query_count} |",
        f"| judgment_count | {summary.judgment_count} |",
        f"| retrieve_query_count | {summary.retrieve_query_count} |",
        f"| abstain_query_count | {summary.abstain_query_count} |",
        f"| query_type_count | {len(summary.query_type_distribution)} |",
        f"| missing_required_query_type_count | {summary.missing_required_query_type_count} |",
        f"| missing_expected_target_count | {summary.missing_expected_target_count} |",
        f"| judgment_query_mismatch_count | {summary.judgment_query_mismatch_count} |",
        f"| public_raw_text_leakage_count | {summary.public_raw_text_leakage_count} |",
        f"| private_path_leakage_count | {summary.private_path_leakage_count} |",
    ]

    assert [fragment for fragment in expected_fragments if fragment not in doc] == []
