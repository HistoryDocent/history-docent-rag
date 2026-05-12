from __future__ import annotations

from app.application.evidence_packing import (
    EvidencePacker,
    build_candidates_by_query_id,
    build_evidence_corpus_from_chunks_payload,
    build_evidence_packs,
    summarize_packs_by_policy,
)
from app.domain.retrieval import RetrievalEvalItem


def _chunks_payload() -> dict[str, object]:
    return {
        "parents": [
            {
                "parent_id": "parent-palace",
                "child_ids": ["child-neighbor", "child-target"],
            },
            {
                "parent_id": "parent-market",
                "child_ids": ["child-market"],
            },
        ],
        "children": [
            _child(
                child_id="child-neighbor",
                parent_id="parent-palace",
                doc_id="doc-palace",
                text_length=400,
            ),
            _child(
                child_id="child-target",
                parent_id="parent-palace",
                doc_id="doc-palace",
                text_length=420,
            ),
            _child(
                child_id="child-market",
                parent_id="parent-market",
                doc_id="doc-market",
                text_length=380,
            ),
        ],
    }


def _child(
    *,
    child_id: str,
    parent_id: str,
    doc_id: str,
    text_length: int,
) -> dict[str, object]:
    return {
        "child_id": child_id,
        "parent_id": parent_id,
        "doc_id": doc_id,
        "text_length": text_length,
        "source_block_ids": [f"block-{child_id}"],
        "citation_refs": [{"block_id": f"block-{child_id}"}],
        "quality_flags": [],
    }


def _eval_item(
    *,
    query_id: str = "q-one",
    query_type: str = "place_story",
    expected_behavior: str = "retrieve",
    child_id: str = "child-target",
    parent_id: str = "parent-palace",
    doc_id: str = "doc-palace",
) -> RetrievalEvalItem:
    judgments = []
    if expected_behavior == "retrieve":
        judgments.append(
            {
                "query_id": query_id,
                "relevant_child_ids": [child_id],
                "relevant_parent_ids": [parent_id],
                "relevant_doc_ids": [doc_id],
                "relevance_grade": 3,
                "rationale_summary": "id only",
                "public_allowed": True,
            }
        )
    return RetrievalEvalItem.model_validate(
        {
            "dataset_version": "retrieval-eval-dataset/v2",
            "query": {
                "query_id": query_id,
                "query_type": query_type,
                "query_text": "경복궁 이야기를 설명해줘",
                "language": "ko",
                "expected_behavior": expected_behavior,
                "public_allowed": True,
            },
            "judgments": judgments,
            "metadata": {
                "split": "dev",
                "difficulty": "medium",
                "place_ids": ["gyeongbokgung"] if expected_behavior == "retrieve" else [],
                "requires_context": query_type == "voice_followup",
                "answerability": "answerable"
                if expected_behavior == "retrieve"
                else "unanswerable",
                "review_status": "reviewed",
            },
        }
    )


def test_parent_expansion_can_recover_target_sibling_child() -> None:
    corpus = build_evidence_corpus_from_chunks_payload(_chunks_payload())
    candidates_by_query_id = build_candidates_by_query_id(
        result_rows=[
            {
                "query_id": "q-one",
                "query_type": "place_story",
                "rank": 1,
                "retrieval_doc_id": "child-neighbor",
                "child_id": "child-neighbor",
                "parent_id": "parent-palace",
                "doc_id": "doc-palace",
                "score": 1.0,
            }
        ],
        corpus=corpus,
    )
    item = _eval_item()
    packs = build_evidence_packs(
        items=[item],
        candidates_by_query_id=candidates_by_query_id,
        corpus=corpus,
        policy_ids=["P0_rank_order", "P1_parent_expansion"],
    )

    p0 = next(pack for pack in packs if pack.policy_id == "P0_rank_order")
    p1 = next(pack for pack in packs if pack.policy_id == "P1_parent_expansion")

    assert p0.target_child_covered is False
    assert p1.target_child_covered is True
    assert [row.child_id for row in p1.evidence] == ["child-neighbor", "child-target"]
    assert p1.citation_recoverability == 1.0


def test_mmr_diversity_prefers_new_parent_when_scores_tie() -> None:
    corpus = build_evidence_corpus_from_chunks_payload(_chunks_payload())
    candidates_by_query_id = build_candidates_by_query_id(
        result_rows=[
            {
                "query_id": "q-one",
                "rank": 1,
                "retrieval_doc_id": "child-neighbor",
                "child_id": "child-neighbor",
                "parent_id": "parent-palace",
                "doc_id": "doc-palace",
                "score": 1.0,
            },
            {
                "query_id": "q-one",
                "rank": 2,
                "retrieval_doc_id": "child-target",
                "child_id": "child-target",
                "parent_id": "parent-palace",
                "doc_id": "doc-palace",
                "score": 1.0,
            },
            {
                "query_id": "q-one",
                "rank": 3,
                "retrieval_doc_id": "child-market",
                "child_id": "child-market",
                "parent_id": "parent-market",
                "doc_id": "doc-market",
                "score": 1.0,
            },
        ],
        corpus=corpus,
    )
    packer = EvidencePacker(corpus=corpus)
    pack = packer.pack(
        item=_eval_item(),
        candidates=candidates_by_query_id["q-one"],
        policy_id="P3_mmr_diversity",
    )

    assert [row.parent_id for row in pack.evidence[:2]] == [
        "parent-palace",
        "parent-market",
    ]


def test_no_answer_query_packs_no_evidence() -> None:
    corpus = build_evidence_corpus_from_chunks_payload(_chunks_payload())
    item = _eval_item(
        query_id="q-no-answer",
        query_type="no_answer",
        expected_behavior="abstain",
    )
    packs = build_evidence_packs(
        items=[item],
        candidates_by_query_id={"q-no-answer": list(corpus.children_by_id.values())},
        corpus=corpus,
        policy_ids=["P0_rank_order", "P4_voice_compact"],
    )
    summaries = summarize_packs_by_policy(items=[item], packs=packs)

    assert all(not pack.evidence for pack in packs)
    assert all(summary.abstain_with_evidence_count == 0 for summary in summaries)
