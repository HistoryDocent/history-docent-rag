from __future__ import annotations

from types import SimpleNamespace

from app.application.evidence_packing import EvidencePack, PackedEvidence
from app.domain.retrieval import FORBIDDEN_PUBLIC_EVAL_FIELDS
from app.domain.retrieval_experiment import PublicRetrievalArtifactQuality
from pipelines.run_place_story_guarded_boost_comparison import (
    BASELINE_STRATEGY_ID,
    GUARDED_BOOST_STRATEGY_ID,
    ROUTER_POLICY_ID,
)
from pipelines.run_solar_guarded_boost_live_dry_run import (
    build_solar_guarded_boost_live_dry_run_row,
)
from pipelines.run_solar_guarded_boost_locked_test_readiness import (
    SOLAR_GUARDED_BOOST_LOCKED_TEST_READINESS_REPORT_VERSION,
    SolarGuardedBoostLockedReadinessReport,
    build_public_solar_guarded_boost_locked_readiness_rows,
    build_solar_guarded_boost_locked_readiness_summary,
    collect_solar_guarded_boost_locked_readiness_failures,
)


def test_locked_readiness_summary_allows_zero_candidate_call_without_failure() -> None:
    row = build_solar_guarded_boost_live_dry_run_row(
        baseline_bundle=_bundle(child_id="child-1", split="test"),
        candidate_bundle=_bundle(child_id="child-2", split="test"),
        selected_strategy_id=BASELINE_STRATEGY_ID,
        route_decision="use_baseline_no_candidate_gain",
        child_chunks_by_id=_children(),
        max_context_chars=11000,
    )
    summary = build_solar_guarded_boost_locked_readiness_summary(
        rows=(row,),
        baseline_bundles=(_bundle(child_id="child-1", split="test"),),
        candidate_bundles=(_bundle(child_id="child-2", split="test"),),
        expected_query_count=1,
        live_call_hard_cap=20,
        target_summary=_target_summary(),
        target_failure_count=0,
    )
    report = _report(rows=(row,), summary=summary)

    assert summary.readiness_decision == "ready_without_candidate_live_call"
    assert summary.solar_call_count == 0
    assert collect_solar_guarded_boost_locked_readiness_failures(report) == []


def test_locked_readiness_summary_marks_candidate_live_approval_ready() -> None:
    row = build_solar_guarded_boost_live_dry_run_row(
        baseline_bundle=_bundle(child_id="child-1", split="test"),
        candidate_bundle=_bundle(child_id="child-2", split="test"),
        selected_strategy_id=GUARDED_BOOST_STRATEGY_ID,
        route_decision="use_candidate_direct_gain",
        child_chunks_by_id=_children(),
        max_context_chars=11000,
    )
    summary = build_solar_guarded_boost_locked_readiness_summary(
        rows=(row,),
        baseline_bundles=(_bundle(child_id="child-1", split="test"),),
        candidate_bundles=(_bundle(child_id="child-2", split="test"),),
        expected_query_count=1,
        live_call_hard_cap=20,
        target_summary=_target_summary(),
        target_failure_count=0,
    )

    assert summary.readiness_decision == "ready_for_live_execution_approval"
    assert summary.candidate_live_call_count == 1
    assert summary.expected_total_live_call_count == 2


def test_locked_readiness_public_rows_are_sanitized() -> None:
    row = build_solar_guarded_boost_live_dry_run_row(
        baseline_bundle=_bundle(child_id="child-1", split="test"),
        candidate_bundle=_bundle(child_id="child-1", split="test"),
        selected_strategy_id=BASELINE_STRATEGY_ID,
        route_decision="use_baseline_no_candidate_gain",
        child_chunks_by_id=_children(),
        max_context_chars=11000,
    )
    summary = build_solar_guarded_boost_locked_readiness_summary(
        rows=(row,),
        baseline_bundles=(_bundle(child_id="child-1", split="test"),),
        candidate_bundles=(_bundle(child_id="child-1", split="test"),),
        expected_query_count=1,
        live_call_hard_cap=20,
        target_summary=_target_summary(),
        target_failure_count=0,
    )
    public_rows = build_public_solar_guarded_boost_locked_readiness_rows(
        _report(rows=(row,), summary=summary),
    )

    assert public_rows
    assert all(FORBIDDEN_PUBLIC_EVAL_FIELDS.isdisjoint(row.keys()) for row in public_rows)


def test_locked_readiness_failures_catch_target_resolvability_failure() -> None:
    row = build_solar_guarded_boost_live_dry_run_row(
        baseline_bundle=_bundle(child_id="child-1", split="test"),
        candidate_bundle=_bundle(child_id="child-2", split="test"),
        selected_strategy_id=BASELINE_STRATEGY_ID,
        route_decision="use_baseline_no_candidate_gain",
        child_chunks_by_id=_children(),
        max_context_chars=11000,
    )
    summary = build_solar_guarded_boost_locked_readiness_summary(
        rows=(row,),
        baseline_bundles=(_bundle(child_id="child-1", split="test"),),
        candidate_bundles=(_bundle(child_id="child-2", split="test"),),
        expected_query_count=1,
        live_call_hard_cap=20,
        target_summary=_target_summary(missing_child_target_count=1),
        target_failure_count=1,
    )
    report = _report(rows=(row,), summary=summary)

    failures = collect_solar_guarded_boost_locked_readiness_failures(report)

    assert "target_resolvability_failed" in failures
    assert summary.readiness_decision == "blocked_by_readiness_gate"


def _report(
    *,
    rows,
    summary,
) -> SolarGuardedBoostLockedReadinessReport:
    return SolarGuardedBoostLockedReadinessReport(
        readiness_id="solar-guarded-boost-locked-ready-q1-fixture",
        generated_at_utc="2026-05-14T00:00:00+00:00",
        dataset_path_alias="<private retrieval eval dataset: retrieval_eval_test.jsonl>",
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
        rows=rows,
        route_decision_distribution={"use_baseline_no_candidate_gain": 1},
        reuse_decision_distribution={"reuse_baseline_result": 1},
        output_quality=PublicRetrievalArtifactQuality(
            result_row_count=0,
            report_version=SOLAR_GUARDED_BOOST_LOCKED_TEST_READINESS_REPORT_VERSION,
            run_id="fixture",
            public_raw_text_leakage_count=0,
            private_path_leakage_count=0,
            secret_like_leakage_count=0,
            forbidden_result_field_count=0,
        ),
        qualitative_assessment={},
    )


def _bundle(*, child_id: str, split: str):
    return SimpleNamespace(
        item=SimpleNamespace(
            query=SimpleNamespace(
                query_id="q-test-place-story-001",
                query_type="place_story",
                query_text="fixture query",
                expected_behavior="retrieve",
                language="ko",
            ),
            metadata=SimpleNamespace(place_ids=("place-gyeongbokgung",), split=split),
        ),
        evidence_pack=EvidencePack(
            query_id="q-test-place-story-001",
            query_type="place_story",
            policy_id="P0_rank_order",
            context_budget_chars=11000,
            total_estimated_chars=120,
            evidence=(
                PackedEvidence(
                    pack_rank=1,
                    source_rank=1,
                    retrieval_doc_id=f"retrieval-{child_id}",
                    child_id=child_id,
                    parent_id=f"parent-{child_id}",
                    doc_id="doc-1",
                    score=1.0,
                    estimated_chars=120,
                    source_block_ids=("block-1",),
                    citation_block_ids=("block-1",),
                    citation_recoverable=True,
                    packing_reason="fixture",
                ),
            ),
            target_child_covered=True,
            target_parent_covered=True,
            target_doc_covered=True,
            evidence_order_relevance_proxy=1.0,
        ),
        input_stats=SimpleNamespace(context_buildable=True),
    )


def _children():
    return {
        "child-1": SimpleNamespace(
            text="fixture evidence one",
            page_span=SimpleNamespace(
                page_global_start=1,
                page_global_end=1,
            ),
        ),
        "child-2": SimpleNamespace(
            text="fixture evidence two",
            page_span=SimpleNamespace(
                page_global_start=2,
                page_global_end=2,
            ),
        ),
    }


def _target_summary(*, missing_child_target_count: int = 0):
    return SimpleNamespace(
        missing_child_target_count=missing_child_target_count,
        missing_parent_target_count=0,
        missing_doc_target_count=0,
    )
