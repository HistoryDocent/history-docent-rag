from __future__ import annotations

from pathlib import Path

from app.domain.retrieval import (
    REQUIRED_QUERY_TYPES,
    collect_retrieval_eval_dataset_failures,
    collect_retrieval_eval_split_readiness_failures,
    load_retrieval_eval_jsonl,
    summarize_retrieval_eval_dataset,
)
from pipelines.build_retrieval_eval_dataset_report import (
    build_retrieval_eval_dataset_report_markdown,
)


def test_retrieval_eval_seed_dataset_passes_public_gate() -> None:
    items = load_retrieval_eval_jsonl(Path("evals/datasets/retrieval_eval_seed.jsonl"))

    summary = summarize_retrieval_eval_dataset(items)

    assert summary.dataset_version == "retrieval-eval-dataset/v2"
    assert summary.query_count == 14
    assert summary.judgment_count == 12
    assert summary.retrieve_query_count == 12
    assert summary.abstain_query_count == 2
    assert summary.query_type_distribution == {
        query_type: 2 for query_type in REQUIRED_QUERY_TYPES
    }
    assert summary.split_distribution == {"seed": 14}
    assert summary.query_type_by_split == {
        "seed": {query_type: 2 for query_type in REQUIRED_QUERY_TYPES}
    }
    assert summary.difficulty_distribution == {"easy": 3, "hard": 8, "medium": 3}
    assert summary.answerability_distribution == {
        "answerable": 12,
        "unanswerable": 2,
    }
    assert summary.review_status_distribution == {"reviewed": 14}
    assert summary.dataset_version_mismatch_count == 0
    assert summary.query_type_min_shortfall_count == 0
    assert summary.dev_query_count == 0
    assert summary.test_query_count == 0
    assert summary.dev_target_shortfall_count == 70
    assert summary.test_target_shortfall_count == 35
    assert summary.duplicate_query_id_count == 0
    assert summary.missing_metadata_count == 0
    assert summary.answerability_mismatch_count == 0
    assert summary.voice_followup_context_missing_count == 0
    assert summary.requires_context_count == 4
    assert summary.place_id_count == 7
    assert summary.missing_required_query_type_count == 0
    assert summary.missing_expected_target_count == 0
    assert summary.judgment_query_mismatch_count == 0
    assert summary.public_raw_text_leakage_count == 0
    assert summary.private_path_leakage_count == 0
    assert collect_retrieval_eval_dataset_failures(summary) == []
    assert collect_retrieval_eval_split_readiness_failures(summary) == [
        "missing_dev_split",
        "missing_test_split",
        "dev_query_type_target_shortfall",
        "test_query_type_target_shortfall",
    ]


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
        assert item.metadata is not None
        assert item.metadata.split == "seed"
        assert item.metadata.review_status == "reviewed"
        if item.query.query_type == "voice_followup":
            assert item.metadata.requires_context is True
        if item.query.query_type == "no_answer":
            assert item.metadata.answerability == "unanswerable"
        else:
            assert item.metadata.answerability == "answerable"


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
        f"| seed_query_count | {summary.split_distribution['seed']} |",
        f"| dataset_version_mismatch_count | {summary.dataset_version_mismatch_count} |",
        f"| query_type_min_shortfall_count | {summary.query_type_min_shortfall_count} |",
        f"| dev_query_count | {summary.dev_query_count} |",
        f"| test_query_count | {summary.test_query_count} |",
        f"| dev_target_shortfall_count | {summary.dev_target_shortfall_count} |",
        f"| test_target_shortfall_count | {summary.test_target_shortfall_count} |",
        f"| duplicate_query_id_count | {summary.duplicate_query_id_count} |",
        f"| missing_metadata_count | {summary.missing_metadata_count} |",
        f"| answerability_mismatch_count | {summary.answerability_mismatch_count} |",
        (
            "| voice_followup_context_missing_count | "
            f"{summary.voice_followup_context_missing_count} |"
        ),
        f"| requires_context_count | {summary.requires_context_count} |",
        f"| place_id_count | {summary.place_id_count} |",
        f"| missing_required_query_type_count | {summary.missing_required_query_type_count} |",
        f"| missing_expected_target_count | {summary.missing_expected_target_count} |",
        f"| judgment_query_mismatch_count | {summary.judgment_query_mismatch_count} |",
        f"| public_raw_text_leakage_count | {summary.public_raw_text_leakage_count} |",
        f"| private_path_leakage_count | {summary.private_path_leakage_count} |",
    ]

    assert [fragment for fragment in expected_fragments if fragment not in doc] == []


def test_retrieval_eval_dataset_report_matches_seed_summary() -> None:
    items = load_retrieval_eval_jsonl(Path("evals/datasets/retrieval_eval_seed.jsonl"))
    summary = summarize_retrieval_eval_dataset(items)
    report = Path("evals/reports/retrieval_eval_dataset_report.md").read_text(
        encoding="utf-8"
    )

    expected_fragments = [
        "| dataset_version | `retrieval-eval-dataset/v2` |",
        "| contract_status | `PASS` |",
        "| split_readiness_status | `FAIL` |",
        f"| query_count | {summary.query_count} |",
        f"| judgment_count | {summary.judgment_count} |",
        f"| dataset_version_mismatch_count | {summary.dataset_version_mismatch_count} |",
        f"| query_type_min_shortfall_count | {summary.query_type_min_shortfall_count} |",
        f"| dev_target_shortfall_count | {summary.dev_target_shortfall_count} |",
        f"| test_target_shortfall_count | {summary.test_target_shortfall_count} |",
        f"| duplicate_query_id_count | {summary.duplicate_query_id_count} |",
        f"| missing_metadata_count | {summary.missing_metadata_count} |",
        f"| answerability_mismatch_count | {summary.answerability_mismatch_count} |",
        (
            "| voice_followup_context_missing_count | "
            f"{summary.voice_followup_context_missing_count} |"
        ),
        f"| requires_context_count | {summary.requires_context_count} |",
        f"| place_id_count | {summary.place_id_count} |",
        "| seed | 14 |",
        "| place_fact | 2 | 0 | 0 | 10 | 5 |",
        "contract_failures=[]",
        "split_readiness_failures=['missing_dev_split', 'missing_test_split'",
    ]

    assert [fragment for fragment in expected_fragments if fragment not in report] == []


def test_retrieval_eval_dataset_gate_fails_when_query_type_below_minimum() -> None:
    items = load_retrieval_eval_jsonl(Path("evals/datasets/retrieval_eval_seed.jsonl"))
    one_missing_place_fact = [
        item for item in items if item.query.query_id != "q-place-fact-002"
    ]
    summary = summarize_retrieval_eval_dataset(one_missing_place_fact)

    assert summary.query_type_min_shortfall_count == 1
    assert "query_type_min_shortfall" in collect_retrieval_eval_dataset_failures(
        summary
    )


def test_retrieval_eval_dataset_report_uses_per_split_counts() -> None:
    items = load_retrieval_eval_jsonl(Path("evals/datasets/retrieval_eval_seed.jsonl"))
    first = items[0]
    dev_copy = first.model_copy(
        update={"metadata": first.metadata.model_copy(update={"split": "dev"})}
    )
    summary = summarize_retrieval_eval_dataset([first, dev_copy])

    markdown = build_retrieval_eval_dataset_report_markdown(
        summary=summary,
        dataset_path=Path("evals/datasets/retrieval_eval_seed.jsonl"),
    )

    assert "| place_fact | 1 | 1 | 0 | 10 | 5 |" in markdown
