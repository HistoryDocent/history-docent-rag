from __future__ import annotations

from types import SimpleNamespace

from app.domain.retrieval import FORBIDDEN_PUBLIC_EVAL_FIELDS
from app.domain.retrieval_experiment import PublicRetrievalArtifactQuality
from pipelines.run_place_story_guarded_boost_comparison import (
    BASELINE_STRATEGY_ID,
    GUARDED_BOOST_STRATEGY_ID,
    ROUTER_POLICY_ID,
    GuardedRouteRow,
)
from pipelines.run_solar_guarded_boost_hard_case_validation import (
    SOLAR_GUARDED_BOOST_HARD_CASE_VALIDATION_REPORT_VERSION,
    GuardedBoostHardCaseValidationRow,
    HardCaseValidationSummary,
    LivePairedMetricRow,
    SolarGuardedBoostHardCaseValidationReport,
    bucket_for_route_decision,
    build_hard_case_validation_row,
    build_hard_case_validation_summary,
    build_public_solar_guarded_boost_hard_case_validation_rows,
    collect_solar_guarded_boost_hard_case_validation_failures,
)


def test_bucket_mapping_matches_guarded_route_decisions() -> None:
    assert bucket_for_route_decision("use_candidate_direct_gain") == "candidate_direct_gain"
    assert (
        bucket_for_route_decision("use_baseline_correctness_guardrail")
        == "correctness_guardrail"
    )
    assert bucket_for_route_decision("use_baseline_doc_guardrail") == "doc_guardrail"
    assert (
        bucket_for_route_decision("use_baseline_precision_guardrail")
        == "precision_guardrail"
    )
    assert bucket_for_route_decision("manual_review_required") == "manual_review_required"
    assert (
        bucket_for_route_decision("use_baseline_no_candidate_gain")
        == "no_candidate_gain_control"
    )


def test_hard_case_row_keeps_manual_review_blocked() -> None:
    row = build_hard_case_validation_row(
        route_row=_route_row(
            query_id="q-dev-place-story-009",
            route_decision="manual_review_required",
            selected_strategy_id=BASELINE_STRATEGY_ID,
            blocked=True,
            evidence_order_delta=-0.666667,
        ),
        baseline_bundle=_bundle(citation_recoverability=1.0),
        candidate_bundle=_bundle(citation_recoverability=1.0),
        live_row=_live_row(
            query_id="q-dev-place-story-009",
            route_decision="manual_review_required",
            citation_recall_delta=0.0,
        ),
    )

    assert row.hard_case_bucket == "manual_review_required"
    assert row.selected_candidate is False
    assert row.blocked is True
    assert "manual_review_kept_blocked" in row.qualitative_tags


def test_summary_passes_for_safe_candidate_and_blocked_manual_review() -> None:
    rows = (
        build_hard_case_validation_row(
            route_row=_route_row(
                query_id="q-dev-place-story-002",
                route_decision="use_candidate_direct_gain",
                selected_strategy_id=GUARDED_BOOST_STRATEGY_ID,
                blocked=False,
                evidence_order_delta=0.0,
            ),
            baseline_bundle=_bundle(citation_recoverability=1.0),
            candidate_bundle=_bundle(citation_recoverability=1.0),
            live_row=_live_row(
                query_id="q-dev-place-story-002",
                route_decision="use_candidate_direct_gain",
                citation_recall_delta=0.285715,
            ),
        ),
        build_hard_case_validation_row(
            route_row=_route_row(
                query_id="q-dev-place-story-009",
                route_decision="manual_review_required",
                selected_strategy_id=BASELINE_STRATEGY_ID,
                blocked=True,
                evidence_order_delta=-0.666667,
            ),
            baseline_bundle=_bundle(citation_recoverability=1.0),
            candidate_bundle=_bundle(citation_recoverability=1.0),
            live_row=_live_row(
                query_id="q-dev-place-story-009",
                route_decision="manual_review_required",
                citation_recall_delta=0.0,
            ),
        ),
    )

    summary = build_hard_case_validation_summary(
        rows=rows,
        expected_query_count=2,
        live_reference_row_count=2,
    )

    assert summary.validation_decision == "keep_guarded_router_for_next_runner"
    assert summary.selected_candidate_safety_passed is True
    assert summary.manual_review_block_passed is True
    assert summary.solar_call_count == 0


def test_public_validation_rows_are_sanitized() -> None:
    report = _report(
        rows=(
            GuardedBoostHardCaseValidationRow(
                query_id="q-dev-place-story-002",
                query_type="place_story",
                split="dev",
                hard_case_bucket="candidate_direct_gain",
                route_decision="use_candidate_direct_gain",
                live_route_decision="use_candidate_direct_gain",
                route_decision_matched_live=True,
                selected_strategy_id=GUARDED_BOOST_STRATEGY_ID,
                blocked=False,
                selected_candidate=True,
                reuse_decision="candidate_live_call_required",
                candidate_live_call_required=True,
                direct_ready_delta=0,
                input_correct_with_evidence_delta=0,
                input_citation_precision_delta=0.0,
                input_citation_recall_delta=0.285715,
                evidence_order_delta=0.0,
                duplicate_parent_rate_delta=0.0,
                selected_citation_recoverability=1.0,
                candidate_doc_covered=True,
                candidate_context_buildable=True,
                live_correct_with_evidence_delta=0,
                live_citation_precision_delta=0.0,
                live_citation_recall_delta=0.285715,
                live_unsupported_claim_delta=0,
                live_latency_ms_delta=2074.9312,
                qualitative_tags=("safe_direct_gain",),
            ),
        ),
    )

    rows = build_public_solar_guarded_boost_hard_case_validation_rows(report)

    assert rows
    assert all(FORBIDDEN_PUBLIC_EVAL_FIELDS.isdisjoint(row.keys()) for row in rows)


def test_failures_catch_selected_candidate_safety_regression() -> None:
    bad_row = GuardedBoostHardCaseValidationRow(
        query_id="q-dev-place-story-002",
        query_type="place_story",
        split="dev",
        hard_case_bucket="candidate_direct_gain",
        route_decision="use_candidate_direct_gain",
        live_route_decision="use_candidate_direct_gain",
        route_decision_matched_live=True,
        selected_strategy_id=GUARDED_BOOST_STRATEGY_ID,
        blocked=False,
        selected_candidate=True,
        reuse_decision="candidate_live_call_required",
        candidate_live_call_required=True,
        direct_ready_delta=0,
        input_correct_with_evidence_delta=0,
        input_citation_precision_delta=0.0,
        input_citation_recall_delta=0.1,
        evidence_order_delta=0.0,
        duplicate_parent_rate_delta=0.0,
        selected_citation_recoverability=1.0,
        candidate_doc_covered=True,
        candidate_context_buildable=True,
        live_correct_with_evidence_delta=0,
        live_citation_precision_delta=-0.2,
        live_citation_recall_delta=0.1,
        live_unsupported_claim_delta=0,
        live_latency_ms_delta=1.0,
        qualitative_tags=("live_safety_regression",),
    )
    summary = build_hard_case_validation_summary(
        rows=(bad_row,),
        expected_query_count=1,
        live_reference_row_count=1,
    )
    report = _report(rows=(bad_row,), summary=summary)

    failures = collect_solar_guarded_boost_hard_case_validation_failures(report)

    assert "selected_candidate_safety_failed" in failures


def _route_row(
    *,
    query_id: str,
    route_decision: str,
    selected_strategy_id: str,
    blocked: bool,
    evidence_order_delta: float,
) -> GuardedRouteRow:
    return GuardedRouteRow(
        query_id=query_id,
        query_type="place_story",
        split="dev",
        router_policy_id=ROUTER_POLICY_ID,
        route_decision=route_decision,
        selected_strategy_id=selected_strategy_id,
        blocked=blocked,
        block_reason_tags=("fixture",),
        direct_ready_delta=0,
        correct_with_evidence_delta=0,
        citation_precision_delta=0.0,
        citation_recall_delta=0.0,
        evidence_order_delta=evidence_order_delta,
        duplicate_parent_rate_delta=0.0,
        input_latency_delta_ms=0.0,
        candidate_doc_covered=True,
        candidate_context_buildable=True,
    )


def _live_row(
    *,
    query_id: str,
    route_decision: str,
    citation_recall_delta: float,
) -> LivePairedMetricRow:
    return LivePairedMetricRow(
        query_id=query_id,
        query_type="place_story",
        route_decision=route_decision,
        reuse_decision=(
            "candidate_live_call_required"
            if route_decision == "use_candidate_direct_gain"
            else "reuse_baseline_result"
        ),
        baseline_strategy_id=BASELINE_STRATEGY_ID,
        candidate_strategy_id=GUARDED_BOOST_STRATEGY_ID,
        baseline_correct_with_evidence=True,
        candidate_correct_with_evidence=True,
        correct_with_evidence_delta=0,
        baseline_citation_precision=0.5,
        candidate_citation_precision=0.5,
        citation_precision_delta=0.0,
        baseline_citation_recall=0.5,
        candidate_citation_recall=0.5 + citation_recall_delta,
        citation_recall_delta=citation_recall_delta,
        unsupported_claim_delta=0,
        baseline_citation_count=5,
        candidate_citation_count=5,
        citation_count_delta=0,
        latency_ms_delta=0.0,
    )


def _bundle(*, citation_recoverability: float):
    return SimpleNamespace(
        evidence_pack=SimpleNamespace(citation_recoverability=citation_recoverability),
    )


def _report(
    *,
    rows: tuple[GuardedBoostHardCaseValidationRow, ...],
    summary: HardCaseValidationSummary | None = None,
) -> SolarGuardedBoostHardCaseValidationReport:
    summary = summary or build_hard_case_validation_summary(
        rows=rows,
        expected_query_count=len(rows),
        live_reference_row_count=len(rows),
    )
    return SolarGuardedBoostHardCaseValidationReport(
        validation_id="solar-guarded-boost-hard-case-q1-fixture",
        generated_at_utc="2026-05-14T00:00:00+00:00",
        dataset_path_alias="<private retrieval eval dataset: retrieval_eval_dev.jsonl>",
        chunks_path_alias="<private parent_child_chunks report>",
        live_paired_rows_path_alias="<private public-safe live paired metric rows>",
        baseline_strategy_id=BASELINE_STRATEGY_ID,
        candidate_strategy_id="parent_doc_context_boost",
        guarded_strategy_id=GUARDED_BOOST_STRATEGY_ID,
        router_policy_id=ROUTER_POLICY_ID,
        answer_policy_id="solar-guarded-boost-live-v1",
        top_k=5,
        candidate_k=20,
        max_context_chars=11000,
        resolved_device="cuda",
        summary=summary,
        bucket_summaries=(),
        rows=rows,
        bucket_distribution={},
        qualitative_assessment={},
        output_quality=PublicRetrievalArtifactQuality(
            result_row_count=0,
            report_version=SOLAR_GUARDED_BOOST_HARD_CASE_VALIDATION_REPORT_VERSION,
            run_id="fixture",
            public_raw_text_leakage_count=0,
            private_path_leakage_count=0,
            secret_like_leakage_count=0,
            forbidden_result_field_count=0,
        ),
    )
