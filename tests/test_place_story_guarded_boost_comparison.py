from __future__ import annotations

from types import SimpleNamespace

from app.domain.retrieval import FORBIDDEN_PUBLIC_EVAL_FIELDS
from app.domain.retrieval_experiment import PublicRetrievalArtifactQuality
from pipelines.run_place_story_guarded_boost_comparison import (
    ALWAYS_BOOST_STRATEGY_ID,
    BASELINE_STRATEGY_ID,
    GUARDED_BOOST_STRATEGY_ID,
    PLACE_STORY_GUARDED_BOOST_REPORT_VERSION,
    ROUTER_POLICY_ID,
    GuardedBoostStrategyDelta,
    GuardedBoostStrategySummary,
    PlaceStoryGuardedBoostComparisonReport,
    build_guarded_route_row,
    build_guardrail_block_reason_tags,
    build_public_place_story_guarded_boost_rows,
)


def test_guardrail_blocks_correctness_regression() -> None:
    reasons = build_guardrail_block_reason_tags(
        baseline_bundle=_bundle(
            direct_ready=False,
            doc_covered=True,
            context_buildable=True,
            evidence_order=0.8,
            duplicate_parent_rate=0.0,
        ),
        candidate_bundle=_bundle(
            direct_ready=True,
            doc_covered=True,
            context_buildable=True,
            evidence_order=0.8,
            duplicate_parent_rate=0.0,
        ),
        baseline_record=_record(correct=True, precision=0.8, recall=0.4),
        candidate_record=_record(correct=False, precision=0.8, recall=0.7),
    )

    assert "correctness_regression" in reasons
    assert "direct_ready_gain" in reasons
    assert "citation_recall_gain" in reasons


def test_guarded_route_selects_candidate_when_all_guards_pass() -> None:
    route = build_guarded_route_row(
        baseline_bundle=_bundle(
            direct_ready=False,
            doc_covered=True,
            context_buildable=True,
            evidence_order=0.7,
            duplicate_parent_rate=0.0,
        ),
        candidate_bundle=_bundle(
            direct_ready=True,
            doc_covered=True,
            context_buildable=True,
            evidence_order=0.7,
            duplicate_parent_rate=0.0,
        ),
        baseline_record=_record(correct=True, precision=0.6, recall=0.3),
        candidate_record=_record(correct=True, precision=0.6, recall=0.6),
    )

    assert route.route_decision == "use_candidate_direct_gain"
    assert route.selected_strategy_id == GUARDED_BOOST_STRATEGY_ID
    assert route.blocked is False


def test_public_guarded_boost_rows_are_sanitized() -> None:
    report = PlaceStoryGuardedBoostComparisonReport(
        comparison_id="place-story-guarded-boost-q1-fixture",
        generated_at_utc="2026-05-14T00:00:00+00:00",
        dataset_path_alias="<private retrieval eval dataset: retrieval_eval_dev.jsonl>",
        chunks_path_alias="<private parent_child_chunks report>",
        baseline_strategy_id=BASELINE_STRATEGY_ID,
        candidate_strategy_id="parent_doc_context_boost",
        router_policy_id=ROUTER_POLICY_ID,
        top_k=5,
        candidate_k=20,
        max_context_chars=11000,
        resolved_device="cuda",
        strategy_summaries=(
            _summary(BASELINE_STRATEGY_ID),
            _summary(ALWAYS_BOOST_STRATEGY_ID),
            _summary(GUARDED_BOOST_STRATEGY_ID),
        ),
        strategy_deltas=(
            _delta(BASELINE_STRATEGY_ID),
            _delta(ALWAYS_BOOST_STRATEGY_ID),
            _delta(GUARDED_BOOST_STRATEGY_ID),
        ),
        route_rows=(
            build_guarded_route_row(
                baseline_bundle=_bundle(
                    direct_ready=False,
                    doc_covered=True,
                    context_buildable=True,
                    evidence_order=0.7,
                    duplicate_parent_rate=0.0,
                ),
                candidate_bundle=_bundle(
                    direct_ready=True,
                    doc_covered=True,
                    context_buildable=True,
                    evidence_order=0.7,
                    duplicate_parent_rate=0.0,
                ),
                baseline_record=_record(correct=True, precision=0.6, recall=0.3),
                candidate_record=_record(correct=True, precision=0.6, recall=0.6),
            ),
        ),
        route_decision_distribution={"use_candidate_direct_gain": 1},
        selected_strategy_id=GUARDED_BOOST_STRATEGY_ID,
        selection_decision="promote_guarded_to_live_plan_review",
        generation_eval_reports={},
        output_quality=PublicRetrievalArtifactQuality(
            result_row_count=0,
            report_version=PLACE_STORY_GUARDED_BOOST_REPORT_VERSION,
            run_id="fixture",
            public_raw_text_leakage_count=0,
            private_path_leakage_count=0,
            secret_like_leakage_count=0,
            forbidden_result_field_count=0,
        ),
        qualitative_assessment={},
    )

    public_rows = build_public_place_story_guarded_boost_rows(report)

    assert public_rows
    assert all(FORBIDDEN_PUBLIC_EVAL_FIELDS.isdisjoint(row.keys()) for row in public_rows)


def _bundle(
    *,
    direct_ready: bool,
    doc_covered: bool,
    context_buildable: bool,
    evidence_order: float,
    duplicate_parent_rate: float,
):
    return SimpleNamespace(
        input_stats=SimpleNamespace(
            direct_evidence_ready=direct_ready,
            context_buildable=context_buildable,
            truncated_evidence_count=0,
            context_budget_violation=False,
            evidence_order_relevance_proxy=evidence_order,
        ),
        evidence_pack=SimpleNamespace(
            target_doc_covered=doc_covered,
            duplicate_parent_rate=duplicate_parent_rate,
        ),
        input_latency_ms=1.0,
    )


def _record(*, correct: bool, precision: float, recall: float):
    return SimpleNamespace(
        query_id="q-dev-place-story-001",
        query_type="place_story",
        split="dev",
        correct_with_evidence=correct,
        citation_precision=precision,
        citation_recall=recall,
    )


def _summary(strategy_id) -> GuardedBoostStrategySummary:
    return GuardedBoostStrategySummary(
        strategy_id=strategy_id,
        eval_count=1,
        selected_candidate_count=0,
        guardrail_block_count=0,
        context_build_success_rate=1.0,
        direct_ready_rate=1.0,
        correct_with_evidence_rate=1.0,
        citation_precision=1.0,
        citation_recall=1.0,
        doc_coverage_rate=1.0,
        evidence_order_relevance_proxy_avg=1.0,
        duplicate_parent_rate_avg=0.0,
        avg_evidence_count=5.0,
        input_latency_p95_ms=1.0,
        solar_call_count=0,
    )


def _delta(strategy_id) -> GuardedBoostStrategyDelta:
    return GuardedBoostStrategyDelta(
        compared_strategy_id=strategy_id,
        direct_ready_rate_delta=0.0,
        correct_with_evidence_rate_delta=0.0,
        citation_precision_delta=0.0,
        citation_recall_delta=0.0,
        doc_coverage_rate_delta=0.0,
        evidence_order_relevance_proxy_avg_delta=0.0,
        duplicate_parent_rate_avg_delta=0.0,
        input_latency_p95_ms_delta=0.0,
    )
