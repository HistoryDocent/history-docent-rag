from __future__ import annotations

from app.application.query_rewrite import (
    PlaceAwareQueryRewriter,
    QueryRewriteConfig,
    summarize_query_rewrite_results,
)
from app.domain.place_catalog import PlaceCatalog
from app.domain.retrieval import RetrievalEvalItem


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
                        },
                        {
                            "alias": "Gyeongbokgung Palace",
                            "language": "en",
                            "alias_type": "tourism",
                        },
                    ],
                    "related_place_ids": ["gwanghwamun"],
                    "relations": [
                        {
                            "target_place_id": "gwanghwamun",
                            "relation_type": "route_neighbor",
                            "rationale": "궁궐 진입 동선",
                        }
                    ],
                    "tour_context_tags": ["palace"],
                    "source_policy": "manual_public_seed",
                    "public_allowed": True,
                },
                {
                    "place_id": "gwanghwamun",
                    "canonical_name": "광화문",
                    "category": "gate_square",
                    "aliases": [
                        {
                            "alias": "광화문",
                            "language": "ko",
                            "alias_type": "primary",
                        }
                    ],
                    "related_place_ids": ["gyeongbokgung"],
                    "relations": [
                        {
                            "target_place_id": "gyeongbokgung",
                            "relation_type": "route_neighbor",
                            "rationale": "궁궐 진입 동선",
                        }
                    ],
                    "tour_context_tags": ["gate"],
                    "source_policy": "manual_public_seed",
                    "public_allowed": True,
                },
            ],
        }
    )


def _eval_item(
    *,
    query_type: str,
    query_text: str,
    expected_behavior: str = "retrieve",
    user_context: str | None = None,
    place_ids: list[str] | None = None,
) -> RetrievalEvalItem:
    judgments = []
    if expected_behavior == "retrieve":
        judgments.append(
            {
                "query_id": "q-one",
                "relevant_child_ids": ["child-palace"],
                "relevant_parent_ids": ["parent-palace"],
                "relevant_doc_ids": ["doc-joseon"],
                "relevance_grade": 3,
                "rationale_summary": "id only",
                "public_allowed": True,
            }
        )
    return RetrievalEvalItem.model_validate(
        {
            "dataset_version": "retrieval-eval-dataset/v2",
            "query": {
                "query_id": "q-one",
                "query_type": query_type,
                "query_text": query_text,
                "language": "ko",
                "expected_behavior": expected_behavior,
                "user_context": user_context,
                "public_allowed": True,
            },
            "judgments": judgments,
            "metadata": {
                "split": "dev",
                "difficulty": "medium",
                "place_ids": place_ids or [],
                "requires_context": query_type == "voice_followup",
                "answerability": "unanswerable"
                if expected_behavior == "abstain"
                else "answerable",
                "review_status": "reviewed",
            },
        }
    )


def test_place_aware_rewrite_expands_alias_from_context() -> None:
    rewriter = PlaceAwareQueryRewriter(catalog=_catalog())
    result = rewriter.rewrite(
        _eval_item(
            query_type="voice_followup",
            query_text="여기는 왜 중요해?",
            user_context="현재 위치는 Gyeongbokgung Palace",
        )
    )

    assert result.changed is True
    assert result.place_ids == ("gyeongbokgung",)
    assert "경복궁" in result.rewritten_query_text
    assert "Gyeongbokgung Palace" in result.rewritten_query_text
    assert "voice_context_expansion" in result.applied_rules


def test_route_context_rewrite_adds_related_places() -> None:
    rewriter = PlaceAwareQueryRewriter(catalog=_catalog())
    result = rewriter.rewrite(
        _eval_item(
            query_type="route_context",
            query_text="궁궐 입구 동선을 설명해줘",
            place_ids=["gyeongbokgung"],
        )
    )

    assert result.changed is True
    assert result.place_ids == ("gyeongbokgung",)
    assert "광화문" in result.rewritten_query_text
    assert "route_related_place_expansion" in result.applied_rules


def test_no_answer_query_is_not_rewritten() -> None:
    rewriter = PlaceAwareQueryRewriter(catalog=_catalog())
    result = rewriter.rewrite(
        _eval_item(
            query_type="no_answer",
            query_text="오늘 지하철 막차 시간 알려줘",
            expected_behavior="abstain",
        )
    )

    assert result.changed is False
    assert result.rewritten_query_text == "오늘 지하철 막차 시간 알려줘"
    assert result.place_ids == ()
    assert result.applied_rules == ("no_answer_guard",)


def test_ascii_alias_does_not_match_inside_longer_token() -> None:
    rewriter = PlaceAwareQueryRewriter(catalog=_catalog())
    result = rewriter.rewrite(
        _eval_item(
            query_type="voice_followup",
            query_text="여기는 왜 중요해?",
            user_context="현재 위치 힌트는 notgyeongbokgungpalace 문자열",
        )
    )

    assert result.place_ids == ()
    assert "경복궁" not in result.rewritten_query_text


def test_query_rewrite_summary_has_deterministic_zero_llm_cost() -> None:
    rewriter = PlaceAwareQueryRewriter(catalog=_catalog())
    results = [
        rewriter.rewrite(
            _eval_item(
                query_type="voice_followup",
                query_text="여기는 왜 중요해?",
                user_context="현재 위치는 Gyeongbokgung Palace",
            )
        ),
        rewriter.rewrite(
            _eval_item(
                query_type="no_answer",
                query_text="오늘 지하철 막차 시간 알려줘",
                expected_behavior="abstain",
            )
        ),
    ]

    summary = summarize_query_rewrite_results(
        config=QueryRewriteConfig(),
        results=results,
    )

    assert summary["query_rewrite"] is True
    assert summary["query_rewrite_changed_count"] == 1
    assert summary["query_rewrite_invalid_json_count"] == 0
    assert summary["query_rewrite_solar_call_count"] == 0
