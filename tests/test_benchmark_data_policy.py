from __future__ import annotations

from pathlib import Path

from app.domain.retrieval import (
    RetrievalEvalDatasetSummary,
    RetrievalEvalExpansionSummary,
    RetrievalEvalExpansionTypeRow,
    RetrievalEvalTargetResolvabilitySummary,
)
from pipelines.build_retrieval_eval_dataset_report import (
    build_retrieval_eval_dataset_report_markdown,
)
from pipelines.build_retrieval_eval_expansion_report import (
    build_retrieval_eval_expansion_report_markdown,
)
from pipelines.build_retrieval_eval_target_report import (
    build_retrieval_eval_target_report_markdown,
)


def test_gitignore_blocks_full_retrieval_benchmark_datasets() -> None:
    gitignore = Path(".gitignore").read_text(encoding="utf-8")

    expected_patterns = [
        "private_data/evals/",
        "evals/datasets/retrieval_eval_dev*.jsonl",
        "evals/datasets/retrieval_eval_test*.jsonl",
    ]

    assert [pattern for pattern in expected_patterns if pattern not in gitignore] == []


def test_data_policy_defines_public_sample_and_private_benchmark_boundary() -> None:
    policy = Path("docs/DATA_POLICY.md").read_text(encoding="utf-8")

    expected_fragments = [
        "retrieval benchmark는 public sample과 private full benchmark를 분리한다.",
        "private_data/evals/datasets/retrieval_eval_dev.jsonl",
        "private_data/evals/datasets/retrieval_eval_test.jsonl",
        "원문 문장 직접 인용",
        "paraphrase rationale",
        "짧은 원문 인용 여부는 자동 검출만으로 충분하지 않으므로 human review에서 확인한다.",
    ]

    assert [fragment for fragment in expected_fragments if fragment not in policy] == []


def test_retrieval_docs_do_not_place_full_test_benchmark_in_public_dataset_path() -> None:
    docs = "\n".join(
        [
            Path("docs/RETRIEVAL_EVAL_DATASET.md").read_text(encoding="utf-8"),
            Path("docs/RETRIEVAL_ABLATION_PLAN.md").read_text(encoding="utf-8"),
            Path("README.md").read_text(encoding="utf-8"),
        ]
    )

    assert "private_data/evals/datasets/retrieval_eval_dev.jsonl" in docs
    assert "private_data/evals/datasets/retrieval_eval_test.jsonl" in docs
    assert "`evals/datasets/retrieval_eval_dev.jsonl`" not in docs
    assert "`evals/datasets/retrieval_eval_test.jsonl`" not in docs


def test_public_reports_describe_private_benchmark_paths_as_aliases() -> None:
    report_text = "\n".join(
        [
            Path("evals/reports/retrieval_eval_dataset_report.md").read_text(
                encoding="utf-8"
            ),
            Path("evals/reports/retrieval_eval_target_resolvability_report.md").read_text(
                encoding="utf-8"
            ),
            Path("evals/reports/retrieval_eval_expansion_report.md").read_text(
                encoding="utf-8"
            ),
        ]
    )

    assert "full benchmark path는 public report에서 alias로만 표기한다." in report_text
    assert "`private_data/evals/datasets/`" not in report_text
    assert "private_data/evals/datasets/retrieval_eval_dev.jsonl" not in report_text
    assert "private_data/evals/datasets/retrieval_eval_test.jsonl" not in report_text


def test_dataset_report_redacts_private_benchmark_dataset_path() -> None:
    markdown = build_retrieval_eval_dataset_report_markdown(
        summary=_dataset_summary(),
        dataset_path=Path("private_data/evals/datasets/retrieval_eval_dev.jsonl"),
    )

    assert "private_data/evals/datasets/retrieval_eval_dev.jsonl" not in markdown
    assert "<private retrieval eval dataset: retrieval_eval_dev.jsonl>" in markdown


def test_target_report_redacts_private_benchmark_dataset_path() -> None:
    markdown = build_retrieval_eval_target_report_markdown(
        summary=_target_summary(),
        dataset_path=Path("private_data/evals/datasets/retrieval_eval_test.jsonl"),
        chunks_path_alias="<private parent_child_chunks report>",
    )

    assert "private_data/evals/datasets/retrieval_eval_test.jsonl" not in markdown
    assert "<private retrieval eval dataset: retrieval_eval_test.jsonl>" in markdown


def test_expansion_report_redacts_private_benchmark_dataset_path() -> None:
    markdown = build_retrieval_eval_expansion_report_markdown(
        dataset_summary=_dataset_summary(),
        expansion_summary=_expansion_summary(),
        target_summary=_target_summary(),
        dataset_path=Path("private_data/evals/datasets/retrieval_eval_dev.jsonl"),
        chunks_path_alias="<private parent_child_chunks report>",
    )

    assert "private_data/evals/datasets/retrieval_eval_dev.jsonl" not in markdown
    assert "<private retrieval eval dataset: retrieval_eval_dev.jsonl>" in markdown


def _dataset_summary() -> RetrievalEvalDatasetSummary:
    return RetrievalEvalDatasetSummary(
        dataset_version="retrieval-eval-dataset/v2",
        query_count=0,
        query_type_distribution={},
        split_distribution={},
        query_type_by_split={},
        difficulty_distribution={},
        answerability_distribution={},
        review_status_distribution={},
        judgment_count=0,
        retrieve_query_count=0,
        abstain_query_count=0,
        dataset_version_mismatch_count=0,
        query_type_min_shortfall_count=0,
        dev_query_count=0,
        test_query_count=0,
        dev_target_shortfall_count=70,
        test_target_shortfall_count=35,
        duplicate_query_id_count=0,
        missing_metadata_count=0,
        answerability_mismatch_count=0,
        voice_followup_context_missing_count=0,
        requires_context_count=0,
        place_id_count=0,
        missing_required_query_type_count=0,
        missing_expected_target_count=0,
        judgment_query_mismatch_count=0,
        public_raw_text_leakage_count=0,
        private_path_leakage_count=0,
    )


def _target_summary() -> RetrievalEvalTargetResolvabilitySummary:
    return RetrievalEvalTargetResolvabilitySummary(
        query_count=0,
        judgment_count=0,
        answerable_query_count=0,
        no_answer_query_count=0,
        searchable_child_count=0,
        searchable_parent_count=0,
        searchable_doc_count=0,
        judgment_target_count=0,
        child_target_count=0,
        resolved_child_target_count=0,
        missing_child_target_count=0,
        parent_target_count=0,
        resolved_parent_target_count=0,
        missing_parent_target_count=0,
        doc_target_count=0,
        resolved_doc_target_count=0,
        missing_doc_target_count=0,
        answerable_without_child_or_parent_target_count=0,
        no_answer_with_positive_target_count=0,
        public_raw_text_leakage_count=0,
        private_path_leakage_count=0,
        secret_like_leakage_count=0,
    )


def _expansion_summary() -> RetrievalEvalExpansionSummary:
    row = RetrievalEvalExpansionTypeRow(
        query_type="place_fact",
        seed_query_count=0,
        dev_query_count=0,
        test_query_count=0,
        target_dev_query_count=10,
        target_test_query_count=5,
        target_total_query_count=15,
        current_total_query_count=0,
        dev_shortfall_count=10,
        test_shortfall_count=5,
        total_shortfall_count=15,
    )
    return RetrievalEvalExpansionSummary(
        dataset_version="retrieval-eval-dataset/v2",
        target_query_count=15,
        current_query_count=0,
        overall_shortfall_count=15,
        seed_query_count=0,
        dev_query_count=0,
        test_query_count=0,
        dev_test_target_query_count=15,
        dev_test_current_query_count=0,
        dev_test_shortfall_count=15,
        draft_query_count=0,
        reviewed_query_count=0,
        locked_query_count=0,
        review_status_distribution={},
        query_type_rows={
            "place_fact": row,
            "place_story": row.model_copy(update={"query_type": "place_story"}),
            "relationship": row.model_copy(update={"query_type": "relationship"}),
            "overview": row.model_copy(update={"query_type": "overview"}),
            "route_context": row.model_copy(update={"query_type": "route_context"}),
            "voice_followup": row.model_copy(update={"query_type": "voice_followup"}),
            "no_answer": row.model_copy(update={"query_type": "no_answer"}),
        },
        public_raw_text_leakage_count=0,
        private_path_leakage_count=0,
        secret_like_leakage_count=0,
    )
