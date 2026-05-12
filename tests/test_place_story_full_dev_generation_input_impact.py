from __future__ import annotations

from pathlib import Path

from pipelines.run_place_story_full_dev_generation_input_impact import (
    BASELINE_STRATEGY_ID,
    build_full_dev_strategy_deltas,
    build_full_dev_strategy_summary,
    build_place_story_full_dev_generation_input_impact_report,
    collect_place_story_full_dev_generation_input_impact_failures,
)
from pipelines.run_place_story_target_grain_coverage import (
    PlaceStoryTargetGrainCoverageRow,
)


def test_full_dev_summary_tracks_generation_input_ready_rate() -> None:
    rows = (
        _row(query_id="q-1", child_rank=1, parent_rank=None, doc_rank=1),
        _row(query_id="q-2", child_rank=None, parent_rank=None, doc_rank=2),
    )

    summary = build_full_dev_strategy_summary(
        strategy_id=BASELINE_STRATEGY_ID,
        rows=rows,
    )

    assert summary.query_count == 2
    assert summary.child_or_parent_recall_at_5 == 0.5
    assert summary.generation_input_ready_rate == 0.5
    assert summary.doc_only_covered_count == 1


def test_full_dev_delta_counts_direct_evidence_improvement_and_regression() -> None:
    baseline_rows = (
        _row(query_id="q-1", child_rank=None, parent_rank=None, doc_rank=2),
        _row(query_id="q-2", child_rank=1, parent_rank=None, doc_rank=1),
    )
    candidate_rows = (
        _row(query_id="q-1", child_rank=3, parent_rank=None, doc_rank=3),
        _row(query_id="q-2", child_rank=None, parent_rank=None, doc_rank=None),
    )
    rows_by_strategy = {
        BASELINE_STRATEGY_ID: baseline_rows,
        "parent_doc_context_boost": candidate_rows,
    }
    summaries = (
        build_full_dev_strategy_summary(
            strategy_id=BASELINE_STRATEGY_ID,
            rows=baseline_rows,
        ),
        build_full_dev_strategy_summary(
            strategy_id="parent_doc_context_boost",
            rows=candidate_rows,
        ),
    )

    deltas = build_full_dev_strategy_deltas(rows_by_strategy, summaries)
    candidate_delta = deltas[1]

    assert candidate_delta.direct_evidence_improved_query_count == 1
    assert candidate_delta.direct_evidence_regressed_query_count == 1
    assert candidate_delta.doc_only_to_direct_query_count == 1
    assert candidate_delta.direct_to_doc_only_or_miss_query_count == 1


def test_full_dev_report_stays_public_safe() -> None:
    baseline_rows = (_row(query_id="q-1", child_rank=None, parent_rank=None, doc_rank=2),)
    candidate_rows = (_row(query_id="q-1", child_rank=1, parent_rank=None, doc_rank=1),)
    report = build_place_story_full_dev_generation_input_impact_report(
        rows_by_strategy={
            BASELINE_STRATEGY_ID: baseline_rows,
            "parent_doc_context_boost": candidate_rows,
        },
        chunks_path=Path("private_data") / "reports" / "parent_child_chunks.json",
        dataset_path=Path("private_data") / "evals" / "datasets" / "retrieval_eval_dev.jsonl",
        place_catalog_path=Path("data_samples") / "place_catalog_seed.json",
        top_k=5,
        candidate_k=20,
        result_rows=[],
        report_text="",
    )

    assert report.selection_decision == "promote_to_generation_input_eval"
    assert report.selected_strategy_id == "parent_doc_context_boost"
    assert collect_place_story_full_dev_generation_input_impact_failures(report) == []


def _row(
    *,
    query_id: str,
    child_rank: int | None,
    parent_rank: int | None,
    doc_rank: int | None,
) -> PlaceStoryTargetGrainCoverageRow:
    any_rank = min(
        [rank for rank in (child_rank, parent_rank, doc_rank) if rank is not None],
        default=None,
    )
    hard_case = child_rank is None and parent_rank is None
    failure_tags = ("no_hard_case",) if not hard_case else ("target_too_narrow",)
    return PlaceStoryTargetGrainCoverageRow(
        query_id=query_id,
        query_type="place_story",
        retrieval_run_label=BASELINE_STRATEGY_ID,
        retrieval_method=BASELINE_STRATEGY_ID,
        retrieval_candidate_count=5,
        packed_evidence_count=5,
        total_latency_ms=1.0,
        target_child_covered=child_rank is not None,
        target_parent_covered=parent_rank is not None,
        target_doc_covered=doc_rank is not None,
        target_child_min_retrieval_rank=child_rank,
        target_parent_min_retrieval_rank=parent_rank,
        target_doc_min_retrieval_rank=doc_rank,
        target_child_min_pack_rank=child_rank,
        target_parent_min_pack_rank=parent_rank,
        target_doc_min_pack_rank=doc_rank,
        any_target_min_retrieval_rank=any_rank,
        any_target_min_pack_rank=any_rank,
        reciprocal_rank=0.0 if any_rank is None else round(1.0 / any_rank, 6),
        ndcg_at_5=0.0 if any_rank is None else 1.0,
        citation_recoverability=1.0,
        evidence_order_relevance_proxy=0.0 if any_rank is None else 1.0,
        duplicate_parent_rate=0.0,
        duplicate_doc_rate=0.0,
        query_rewrite_changed=False,
        query_rewrite_applied_rule_count=0,
        hard_case=hard_case,
        failure_tags=failure_tags,
        next_action="fixture",
    )
