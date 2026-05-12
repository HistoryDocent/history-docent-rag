from __future__ import annotations

from pathlib import Path

from app.domain.data_contracts import PageSpan
from app.domain.place_catalog import PlaceCatalog
from app.domain.retrieval import (
    RetrievedCandidate,
    RetrievalDocument,
    RetrievalEvalItem,
    RetrievalRunResult,
)
from pipelines.run_place_story_target_grain_coverage import (
    build_place_story_target_grain_coverage_row,
)
from pipelines.run_place_story_top_rank_coverage_repair import (
    BASELINE_STRATEGY_ID,
    build_place_story_top_rank_coverage_repair_report,
    build_strategy_deltas,
    build_strategy_summary,
    collect_place_story_top_rank_coverage_repair_failures,
    rerank_with_parent_doc_context_boost,
)
from app.application.chat_retrieval import StaticRetrievalBackend


def test_parent_doc_context_boost_promotes_place_matched_candidate() -> None:
    item = _eval_item(query_id="q-dev-place-story-001")
    weak = _document(
        child_id="weak-child",
        parent_id="weak-parent",
        doc_id="weak-doc",
        search_text="다른 장소의 일반 설명",
    )
    matched = _document(
        child_id="matched-child",
        parent_id="matched-parent",
        doc_id="matched-doc",
        search_text="경복궁 조선 역사 이야기",
    )
    result = RetrievalRunResult(
        query_id=item.query.query_id,
        query_type="place_story",
        method="dense",
        latency_ms=1.0,
        candidates=[
            _candidate(rank=1, document=weak, score=0.50),
            _candidate(rank=2, document=matched, score=0.45),
        ],
    )

    reranked = rerank_with_parent_doc_context_boost(
        item=item,
        result=result,
        document_by_child_id={weak.child_id: weak, matched.child_id: matched},
        catalog=_catalog(),
        top_k=2,
    )

    assert reranked.candidates[0].child_id == "matched-child"
    assert reranked.candidates[0].rank == 1


def test_repair_report_selects_improved_candidate_and_stays_public_safe() -> None:
    item = _eval_item(query_id="q-dev-place-story-001")
    baseline_pack = StaticRetrievalBackend().retrieve(
        command=_command_like(),
        item=_eval_item(
            query_id="q-dev-place-story-001",
            child_ids=["missing-child"],
            parent_ids=["missing-parent"],
            doc_ids=["fixture-doc-history"],
        ),
    ).evidence_pack
    improved_pack = StaticRetrievalBackend().retrieve(
        command=_command_like(),
        item=item,
    ).evidence_pack
    baseline_row = build_place_story_target_grain_coverage_row(
        item=_eval_item(
            query_id="q-dev-place-story-001",
            child_ids=["missing-child"],
            parent_ids=["missing-parent"],
            doc_ids=["fixture-doc-history"],
        ),
        evidence_pack=baseline_pack,
        retrieval_method=BASELINE_STRATEGY_ID,
        retrieval_candidate_count=1,
        total_latency_ms=1.0,
        query_rewrite_changed=False,
        query_rewrite_applied_rule_count=0,
    ).model_copy(update={"retrieval_run_label": BASELINE_STRATEGY_ID})
    improved_row = build_place_story_target_grain_coverage_row(
        item=item,
        evidence_pack=improved_pack,
        retrieval_method="place_story_rewrite_v2",
        retrieval_candidate_count=1,
        total_latency_ms=2.0,
        query_rewrite_changed=True,
        query_rewrite_applied_rule_count=2,
    ).model_copy(update={"retrieval_run_label": "place_story_rewrite_v2"})
    rows_by_strategy = {
        BASELINE_STRATEGY_ID: (baseline_row,),
        "place_story_rewrite_v2": (improved_row,),
        "parent_doc_context_boost": (baseline_row.model_copy(
            update={"retrieval_run_label": "parent_doc_context_boost"},
        ),),
    }

    report = build_place_story_top_rank_coverage_repair_report(
        rows_by_strategy=rows_by_strategy,
        hard_subset_query_ids=("q-dev-place-story-001",),
        chunks_path=Path("private_data") / "reports" / "parent_child_chunks.json",
        dataset_path=Path("private_data") / "evals" / "datasets" / "retrieval_eval_dev.jsonl",
        place_catalog_path=Path("data_samples") / "place_catalog_seed.json",
        top_k=5,
        candidate_k=20,
        result_rows=[],
        report_text="",
    )

    assert report.selection_decision == "adopt_candidate"
    assert report.selected_strategy_id == "place_story_rewrite_v2"
    assert collect_place_story_top_rank_coverage_repair_failures(report) == []


def test_strategy_summary_and_delta_use_hard_subset_rows() -> None:
    item = _eval_item(query_id="q-dev-place-story-001")
    retrieval = StaticRetrievalBackend().retrieve(command=_command_like(), item=item)
    row = build_place_story_target_grain_coverage_row(
        item=item,
        evidence_pack=retrieval.evidence_pack,
        retrieval_method=BASELINE_STRATEGY_ID,
        retrieval_candidate_count=1,
        total_latency_ms=1.0,
        query_rewrite_changed=False,
        query_rewrite_applied_rule_count=0,
    )
    baseline = build_strategy_summary(
        strategy_id=BASELINE_STRATEGY_ID,
        rows=(row,),
        hard_subset_query_count=1,
    )
    candidate = build_strategy_summary(
        strategy_id="place_story_rewrite_v2",
        rows=(row.model_copy(update={"retrieval_run_label": "place_story_rewrite_v2"}),),
        hard_subset_query_count=1,
    )
    deltas = build_strategy_deltas((baseline, candidate))

    assert baseline.child_or_parent_recall_at_5 == 1.0
    assert deltas[1].compared_strategy_id == "place_story_rewrite_v2"
    assert deltas[1].child_or_parent_recall_at_5_delta == 0.0


def _catalog() -> PlaceCatalog:
    return PlaceCatalog.model_validate(
        {
            "catalog_version": "place-catalog/v1",
            "places": [
                {
                    "place_id": "gyeongbokgung",
                    "canonical_name": "경복궁",
                    "category": "palace",
                    "aliases": [
                        {
                            "alias": "경복궁",
                            "language": "ko",
                            "alias_type": "primary",
                        }
                    ],
                    "related_place_ids": [],
                    "relations": [],
                    "tour_context_tags": ["palace"],
                    "source_policy": "manual_public_seed",
                    "public_allowed": True,
                }
            ],
        }
    )


def _eval_item(
    *,
    query_id: str,
    child_ids: list[str] | None = None,
    parent_ids: list[str] | None = None,
    doc_ids: list[str] | None = None,
) -> RetrievalEvalItem:
    return RetrievalEvalItem.model_validate(
        {
            "dataset_version": "retrieval-eval-dataset/v2",
            "query": {
                "query_id": query_id,
                "query_type": "place_story",
                "query_text": "경복궁 이야기를 들려줘",
                "language": "ko",
                "expected_behavior": "retrieve",
                "user_context": None,
                "public_allowed": True,
            },
            "judgments": [
                {
                    "query_id": query_id,
                    "relevant_child_ids": child_ids or ["fixture-child-gyeongbokgung"],
                    "relevant_parent_ids": parent_ids or ["fixture-parent-palace"],
                    "relevant_doc_ids": doc_ids or ["fixture-doc-history"],
                    "relevance_grade": 3,
                    "rationale_summary": "fixture target",
                    "public_allowed": True,
                }
            ],
            "metadata": {
                "split": "dev",
                "difficulty": "medium",
                "place_ids": ["gyeongbokgung"],
                "requires_context": False,
                "answerability": "answerable",
                "review_status": "reviewed",
            },
        },
    )


def _command_like():
    class Command:
        request_id = "q-dev-place-story-001"
        query = "경복궁 이야기를 들려줘"
        language = "ko"
        query_type = "place_story"
        place_context = ("gyeongbokgung",)
        voice_mode = False
        user_context = None

    return Command()


def _document(
    *,
    child_id: str,
    parent_id: str,
    doc_id: str,
    search_text: str,
) -> RetrievalDocument:
    return RetrievalDocument(
        retrieval_doc_id=child_id,
        child_id=child_id,
        parent_id=parent_id,
        doc_id=doc_id,
        doc_title="fixture",
        page_span=PageSpan(
            page_local_start=1,
            page_local_end=1,
            page_global_start=1,
            page_global_end=1,
        ),
        source_block_ids=[f"{child_id}-block"],
        context_block_ids=[],
        text_hash="a" * 64,
        text_length=len(search_text),
        element_type_mix={"paragraph": 1},
        citation_block_ids=[f"{child_id}-block"],
        quality_flags=[],
        public_allowed=False,
        search_text=search_text,
        context_text=search_text,
    )


def _candidate(
    *,
    rank: int,
    document: RetrievalDocument,
    score: float,
) -> RetrievedCandidate:
    return RetrievedCandidate(
        rank=rank,
        retrieval_doc_id=document.retrieval_doc_id,
        child_id=document.child_id,
        parent_id=document.parent_id,
        doc_id=document.doc_id,
        score=score,
    )
