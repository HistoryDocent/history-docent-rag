from __future__ import annotations

from types import SimpleNamespace

from app.domain.retrieval import FORBIDDEN_PUBLIC_EVAL_FIELDS
from app.domain.retrieval_experiment import PublicRetrievalArtifactQuality
from pipelines.run_place_story_generation_input_regression_analysis import (
    BASELINE_STRATEGY_ID,
    CANDIDATE_STRATEGY_ID,
    PLACE_STORY_INPUT_REGRESSION_REPORT_VERSION,
    PlaceStoryInputRegressionAnalysisReport,
    PlaceStoryInputRegressionRow,
    build_input_regression_row,
    build_input_regression_summary,
    build_public_place_story_input_regression_rows,
    build_tag_distribution,
)


def test_input_regression_row_tags_mixed_tradeoff_and_guardrail() -> None:
    row = build_input_regression_row(
        baseline_bundle=_bundle(
            direct_ready=False,
            evidence_order=0.8,
            evidence_count=5,
            context_chars=4200,
            latency_ms=12.0,
        ),
        candidate_bundle=_bundle(
            direct_ready=True,
            evidence_order=0.2,
            evidence_count=5,
            context_chars=4100,
            latency_ms=9.0,
        ),
        baseline_record=_record(
            correct=True,
            precision=0.8,
            recall=0.4,
            citation_count=5,
        ),
        candidate_record=_record(
            correct=False,
            precision=0.6,
            recall=0.7,
            citation_count=5,
        ),
    )

    assert row.direct_ready_delta == 1
    assert row.correct_with_evidence_delta == -1
    assert row.citation_precision_delta == -0.2
    assert row.citation_recall_delta == 0.3
    assert "mixed_tradeoff" in row.regression_tags
    assert "guardrail_required" in row.regression_tags
    assert row.recommendation == "exclude_from_candidate_until_guardrail"


def test_input_regression_summary_requires_guardrail_before_live() -> None:
    rows = (
        _row(
            query_id="q-dev-place-story-001",
            tags=("direct_ready_gain", "correctness_regression", "guardrail_required"),
        ),
        _row(query_id="q-dev-place-story-002", tags=("citation_recall_gain",)),
    )

    summary = build_input_regression_summary(rows=rows, solar_call_count=0)

    assert summary.query_count == 2
    assert summary.guardrail_required_count == 1
    assert summary.recommended_decision == "require_guardrail_before_live_generation"


def test_public_input_regression_rows_are_sanitized() -> None:
    rows = (_row(query_id="q-dev-place-story-001", tags=("mixed_tradeoff",)),)
    summary = build_input_regression_summary(rows=rows, solar_call_count=0)
    report = PlaceStoryInputRegressionAnalysisReport(
        analysis_id="place-story-input-regression-q1-fixture",
        generated_at_utc="2026-05-14T00:00:00+00:00",
        dataset_path_alias="<private retrieval eval dataset: retrieval_eval_dev.jsonl>",
        chunks_path_alias="<private parent_child_chunks report>",
        baseline_strategy_id=BASELINE_STRATEGY_ID,
        candidate_strategy_id=CANDIDATE_STRATEGY_ID,
        top_k=5,
        candidate_k=20,
        max_context_chars=11000,
        resolved_device="cuda",
        summary=summary,
        tag_distribution=build_tag_distribution(rows),
        query_rows=rows,
        output_quality=PublicRetrievalArtifactQuality(
            result_row_count=0,
            report_version=PLACE_STORY_INPUT_REGRESSION_REPORT_VERSION,
            run_id="fixture",
            public_raw_text_leakage_count=0,
            private_path_leakage_count=0,
            secret_like_leakage_count=0,
            forbidden_result_field_count=0,
        ),
        qualitative_assessment={},
    )

    public_rows = build_public_place_story_input_regression_rows(report)

    assert public_rows
    assert all(FORBIDDEN_PUBLIC_EVAL_FIELDS.isdisjoint(row.keys()) for row in public_rows)
    assert all("query_id" in row or row["row_type"] == "summary" for row in public_rows)


def _bundle(
    *,
    direct_ready: bool,
    evidence_order: float,
    evidence_count: int,
    context_chars: int,
    latency_ms: float,
):
    return SimpleNamespace(
        input_stats=SimpleNamespace(
            direct_evidence_ready=direct_ready,
            evidence_order_relevance_proxy=evidence_order,
            evidence_count=evidence_count,
            context_char_count=context_chars,
        ),
        input_latency_ms=latency_ms,
    )


def _record(
    *,
    correct: bool,
    precision: float,
    recall: float,
    citation_count: int,
):
    return SimpleNamespace(
        query_id="q-dev-place-story-001",
        query_type="place_story",
        split="dev",
        correct_with_evidence=correct,
        citation_precision=precision,
        citation_recall=recall,
        citation_count=citation_count,
        solar_call_count=0,
    )


def _row(*, query_id: str, tags: tuple[str, ...]) -> PlaceStoryInputRegressionRow:
    return PlaceStoryInputRegressionRow(
        query_id=query_id,
        query_type="place_story",
        split="dev",
        baseline_direct_ready=False,
        candidate_direct_ready=True,
        direct_ready_delta=1,
        baseline_correct_with_evidence=True,
        candidate_correct_with_evidence=True,
        correct_with_evidence_delta=0,
        citation_precision_delta=-0.1,
        citation_recall_delta=0.2,
        evidence_order_delta=-0.3,
        citation_count_delta=0,
        evidence_count_delta=0,
        context_char_delta=-10,
        input_latency_delta_ms=-1.0,
        regression_tags=tags,
        recommendation="manual_review_before_live_call",
    )
