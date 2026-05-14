from __future__ import annotations

import pytest

from app.domain.retrieval import FORBIDDEN_PUBLIC_EVAL_FIELDS
from app.domain.retrieval_experiment import PublicRetrievalArtifactQuality
from pipelines.run_place_story_guarded_boost_comparison import (
    BASELINE_STRATEGY_ID,
    GUARDED_BOOST_STRATEGY_ID,
    ROUTER_POLICY_ID,
)
from pipelines.run_solar_guarded_boost_live_comparison import (
    SolarGuardedBoostLivePairDelta,
    build_public_solar_guarded_boost_live_paired_comparison_rows_from_deltas,
    build_public_solar_guarded_boost_live_comparison_rows,
    build_solar_guarded_boost_live_comparison_readiness_report,
    collect_solar_guarded_boost_live_comparison_failures,
    validate_live_execution_approval,
    validate_live_execution_request,
)
from pipelines.run_solar_guarded_boost_live_dry_run import (
    SOLAR_GUARDED_BOOST_LIVE_DRY_RUN_REPORT_VERSION,
    SolarGuardedBoostDryRunRow,
    SolarGuardedBoostDryRunSummary,
    SolarGuardedBoostLiveDryRunReport,
)


def test_readiness_report_keeps_live_execution_blocked_by_default() -> None:
    report = build_solar_guarded_boost_live_comparison_readiness_report(
        dry_run_report=_dry_run_report(),
        live_execution_requested=False,
        live_execution_confirmed=False,
    )

    assert report.gate_summary.readiness_decision == "ready_for_live_execution_approval"
    assert report.gate_summary.live_call_executed is False
    assert report.gate_summary.solar_call_count == 0
    assert report.gate_summary.expected_total_live_call_count == 11
    assert report.gate_summary.candidate_live_call_count == 1
    assert not collect_solar_guarded_boost_live_comparison_failures(report)


def test_public_readiness_rows_are_sanitized() -> None:
    report = build_solar_guarded_boost_live_comparison_readiness_report(
        dry_run_report=_dry_run_report(),
        live_execution_requested=False,
        live_execution_confirmed=False,
    )

    public_rows = build_public_solar_guarded_boost_live_comparison_rows(report)

    assert public_rows
    assert all(FORBIDDEN_PUBLIC_EVAL_FIELDS.isdisjoint(row.keys()) for row in public_rows)


def test_live_execution_request_is_blocked_until_next_approval_stage() -> None:
    with pytest.raises(PermissionError):
        validate_live_execution_request(
            execute_live=True,
            confirm_live_execution=True,
        )

    with pytest.raises(ValueError):
        validate_live_execution_request(
            execute_live=False,
            confirm_live_execution=True,
        )


def test_live_execution_approval_requires_double_confirmation() -> None:
    validate_live_execution_approval(
        execute_live=True,
        confirm_live_execution=True,
    )

    with pytest.raises(PermissionError):
        validate_live_execution_approval(
            execute_live=True,
            confirm_live_execution=False,
        )

    with pytest.raises(PermissionError):
        validate_live_execution_approval(
            execute_live=False,
            confirm_live_execution=True,
        )


def test_live_paired_public_rows_are_sanitized() -> None:
    rows = build_public_solar_guarded_boost_live_paired_comparison_rows_from_deltas(
        (
            SolarGuardedBoostLivePairDelta(
                query_id="q-dev-place-story-001",
                query_type="place_story",
                route_decision="reuse_baseline_result",
                reuse_decision="reuse_baseline_result",
                baseline_correct_with_evidence=True,
                candidate_correct_with_evidence=True,
                correct_with_evidence_delta=0,
                baseline_citation_precision=0.5,
                candidate_citation_precision=0.5,
                citation_precision_delta=0.0,
                baseline_citation_recall=0.5,
                candidate_citation_recall=0.5,
                citation_recall_delta=0.0,
                baseline_unsupported_claim=False,
                candidate_unsupported_claim=False,
                unsupported_claim_delta=0,
                baseline_citation_count=5,
                candidate_citation_count=5,
                citation_count_delta=0,
                latency_ms_delta=0.0,
            ),
        ),
    )

    assert rows
    assert all(FORBIDDEN_PUBLIC_EVAL_FIELDS.isdisjoint(row.keys()) for row in rows)


def test_readiness_blocks_when_call_cap_failed() -> None:
    dry_run = _dry_run_report(
        summary=SolarGuardedBoostDryRunSummary(
            query_count=10,
            baseline_live_call_count=10,
            candidate_live_call_count=11,
            expected_total_live_call_count=21,
            live_call_hard_cap=20,
            reused_candidate_count=0,
            changed_candidate_input_count=11,
            selected_candidate_count=11,
            guardrail_block_count=0,
            solar_call_count=0,
            hard_cap_exceeded=True,
        ),
    )

    report = build_solar_guarded_boost_live_comparison_readiness_report(
        dry_run_report=dry_run,
        live_execution_requested=False,
        live_execution_confirmed=False,
    )

    failures = collect_solar_guarded_boost_live_comparison_failures(report)

    assert report.gate_summary.readiness_decision == "blocked_before_live_execution"
    assert "call_cap_failed" in failures


def _dry_run_report(
    *,
    summary: SolarGuardedBoostDryRunSummary | None = None,
) -> SolarGuardedBoostLiveDryRunReport:
    summary = summary or SolarGuardedBoostDryRunSummary(
        query_count=10,
        baseline_live_call_count=10,
        candidate_live_call_count=1,
        expected_total_live_call_count=11,
        live_call_hard_cap=20,
        reused_candidate_count=9,
        changed_candidate_input_count=1,
        selected_candidate_count=1,
        guardrail_block_count=9,
        solar_call_count=0,
        hard_cap_exceeded=False,
    )
    return SolarGuardedBoostLiveDryRunReport(
        dry_run_id="solar-guarded-boost-dry-q10-fixture",
        generated_at_utc="2026-05-14T00:00:00+00:00",
        dataset_path_alias="<private retrieval eval dataset: retrieval_eval_dev.jsonl>",
        chunks_path_alias="<private parent_child_chunks report>",
        baseline_strategy_id=BASELINE_STRATEGY_ID,
        candidate_strategy_id="parent_doc_context_boost",
        guarded_strategy_id=GUARDED_BOOST_STRATEGY_ID,
        router_policy_id=ROUTER_POLICY_ID,
        answer_contract_version="citation-rag-answer/v1",
        answer_policy_id="solar-guarded-boost-live-v1",
        provider_config_id_alias="<solar-pro3-v1-live-config>",
        endpoint_alias="api.upstage.ai/v1/chat/completions",
        model_id="solar-pro3",
        top_k=5,
        candidate_k=20,
        max_context_chars=11000,
        resolved_device="cuda",
        summary=summary,
        rows=(
            SolarGuardedBoostDryRunRow(
                query_id="q-dev-place-story-001",
                query_type="place_story",
                split="dev",
                baseline_strategy_id=BASELINE_STRATEGY_ID,
                candidate_strategy_id="parent_doc_context_boost",
                selected_strategy_id=BASELINE_STRATEGY_ID,
                router_policy_id=ROUTER_POLICY_ID,
                route_decision="use_baseline_no_candidate_gain",
                reuse_decision="reuse_baseline_result",
                baseline_input_fingerprint="baselinehash0001",
                guarded_input_fingerprint="baselinehash0001",
                input_fingerprint_equal=True,
                baseline_live_call_required=True,
                candidate_live_call_required=False,
                baseline_context_char_count=100,
                guarded_context_char_count=100,
                baseline_evidence_count=5,
                guarded_evidence_count=5,
            ),
            SolarGuardedBoostDryRunRow(
                query_id="q-dev-place-story-002",
                query_type="place_story",
                split="dev",
                baseline_strategy_id=BASELINE_STRATEGY_ID,
                candidate_strategy_id="parent_doc_context_boost",
                selected_strategy_id=GUARDED_BOOST_STRATEGY_ID,
                router_policy_id=ROUTER_POLICY_ID,
                route_decision="use_candidate_direct_gain",
                reuse_decision="candidate_live_call_required",
                baseline_input_fingerprint="baselinehash0002",
                guarded_input_fingerprint="guardedhash0002",
                input_fingerprint_equal=False,
                baseline_live_call_required=True,
                candidate_live_call_required=True,
                baseline_context_char_count=100,
                guarded_context_char_count=120,
                baseline_evidence_count=5,
                guarded_evidence_count=5,
            ),
        ),
        reuse_decision_distribution={
            "candidate_live_call_required": 1,
            "reuse_baseline_result": 9,
        },
        output_quality=PublicRetrievalArtifactQuality(
            result_row_count=11,
            report_version=SOLAR_GUARDED_BOOST_LIVE_DRY_RUN_REPORT_VERSION,
            run_id="fixture",
            public_raw_text_leakage_count=0,
            private_path_leakage_count=0,
            secret_like_leakage_count=0,
            forbidden_result_field_count=0,
        ),
        qualitative_assessment={},
    )
