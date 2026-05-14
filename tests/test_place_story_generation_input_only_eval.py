from __future__ import annotations

from app.application.evidence_packing import EvidencePack, PackedEvidence
from app.domain.chunking import ChildChunk
from app.domain.data_contracts import ElementReference, PageSpan
from pipelines.run_place_story_generation_input_only_eval import (
    BASELINE_STRATEGY_ID,
    PlaceStoryInputOnlyStrategySummary,
    _select_input_only_strategy,
    build_evidence_input_stats,
    build_input_only_deltas,
    build_input_only_strategy_summary,
)
from tests.test_place_story_top_rank_coverage_repair import _eval_item


def test_evidence_input_stats_reports_context_buildability() -> None:
    item = _eval_item(query_id="q-dev-place-story-001")
    evidence_pack = _evidence_pack(child_id="fixture-child-gyeongbokgung")
    stats = build_evidence_input_stats(
        item=item,
        strategy_id=BASELINE_STRATEGY_ID,
        evidence_pack=evidence_pack,
        child_chunks_by_id={
            "fixture-child-gyeongbokgung": _child_chunk(
                child_id="fixture-child-gyeongbokgung",
                text="경복궁은 조선의 중심 궁궐이라는 설명입니다.",
            )
        },
        max_context_chars=1000,
    )

    assert stats.context_buildable is True
    assert stats.private_text_available_count == 1
    assert stats.direct_evidence_ready is True
    assert stats.context_char_count > 0


def test_input_only_deltas_compare_generation_eval_proxy_metrics() -> None:
    baseline_summary = build_input_only_strategy_summary(
        strategy_id=BASELINE_STRATEGY_ID,
        bundles=(),
        generation_report=_fake_generation_report(
            correct=0.6,
            precision=0.5,
            recall=0.4,
        ),
    )
    candidate_summary = build_input_only_strategy_summary(
        strategy_id="parent_doc_context_boost",
        bundles=(),
        generation_report=_fake_generation_report(
            correct=0.7,
            precision=0.6,
            recall=0.5,
        ),
    )

    deltas = build_input_only_deltas((baseline_summary, candidate_summary))

    assert deltas[1].correct_with_evidence_rate_delta == 0.1
    assert deltas[1].citation_precision_delta == 0.1
    assert deltas[1].citation_recall_delta == 0.1


def test_input_only_selection_keeps_precision_regression_as_tradeoff() -> None:
    baseline = _input_summary(
        strategy_id=BASELINE_STRATEGY_ID,
        direct_ready=0.6,
        correct=0.9,
        precision=0.58,
        recall=0.48,
    )
    candidate = _input_summary(
        strategy_id="parent_doc_context_boost",
        direct_ready=0.7,
        correct=0.8,
        precision=0.55,
        recall=0.56,
    )
    deltas = tuple(build_input_only_deltas((baseline, candidate)))

    selected, decision = _select_input_only_strategy((baseline, candidate), deltas)

    assert selected == "parent_doc_context_boost"
    assert decision == "keep_as_tradeoff_candidate"


def _evidence_pack(*, child_id: str) -> EvidencePack:
    return EvidencePack(
        query_id="q-dev-place-story-001",
        query_type="place_story",
        policy_id="P0_rank_order",
        context_budget_chars=4200,
        total_estimated_chars=200,
        evidence=(
            PackedEvidence(
                pack_rank=1,
                source_rank=1,
                retrieval_doc_id=child_id,
                child_id=child_id,
                parent_id="fixture-parent-palace",
                doc_id="fixture-doc-history",
                score=1.0,
                estimated_chars=200,
                source_block_ids=("block-one",),
                citation_block_ids=("block-one",),
                citation_recoverable=True,
                packing_reason="fixture",
            ),
        ),
        target_child_covered=True,
        target_parent_covered=True,
        target_doc_covered=True,
        evidence_order_relevance_proxy=1.0,
    )


def _child_chunk(*, child_id: str, text: str) -> ChildChunk:
    page_span = PageSpan(
        page_local_start=1,
        page_local_end=1,
        page_global_start=1,
        page_global_end=1,
    )
    return ChildChunk(
        child_id=child_id,
        parent_id="fixture-parent-palace",
        doc_id="fixture-doc-history",
        doc_title="fixture",
        parser_run_id="parser-run",
        source_block_ids=("block-one",),
        context_block_ids=(),
        page_span=page_span,
        text_hash="a" * 64,
        text_length=len(text),
        element_type_mix={"paragraph": 1},
        citation_refs=(
            {
                "block_id": "block-one",
                "doc_id": "fixture-doc-history",
                "element_type": "paragraph",
                "page_span": page_span.model_dump(),
                "element_refs": [
                    ElementReference(
                        element_id="element-one",
                        element_type="paragraph",
                        element_index=1,
                    ).model_dump()
                ],
                "source_file_name": "fixture.pdf",
                "text_hash": "b" * 64,
                "text_length": len(text),
                "quality_flags": [],
            },
        ),
        quality_flags=(),
        public_allowed=False,
        text=text,
        context_text=None,
    )


def _fake_generation_report(*, correct: float, precision: float, recall: float):
    class Summary:
        correct_with_evidence_rate = correct
        citation_precision = precision
        citation_recall = recall
        missing_citation_count = 0
        unsupported_high_count = 0
        latency_p95_ms = 0.0
        solar_call_count = 0

    class Report:
        summary = Summary()

    return Report()


def _input_summary(
    *,
    strategy_id,
    direct_ready: float,
    correct: float,
    precision: float,
    recall: float,
) -> PlaceStoryInputOnlyStrategySummary:
    return PlaceStoryInputOnlyStrategySummary(
        strategy_id=strategy_id,
        eval_count=10,
        context_build_success_rate=1.0,
        direct_evidence_ready_rate=direct_ready,
        correct_with_evidence_rate=correct,
        citation_precision=precision,
        citation_recall=recall,
        citation_recoverability_avg=1.0,
        evidence_order_relevance_proxy_avg=0.7,
        avg_evidence_count=5.0,
        avg_context_chars=4300.0,
        context_chars_p95=4700.0,
        truncated_query_count=0,
        missing_citation_count=0,
        unsupported_high_count=0,
        input_latency_p95_ms=10.0,
        solar_call_count=0,
    )
