from __future__ import annotations

from app.application.query_type_router import (
    DEFAULT_RETRIEVAL_CANDIDATE_ID,
    NO_ANSWER_ROUTE_POLICY_ID,
    RELATIONSHIP_RETRIEVAL_CANDIDATE_ID,
    RELATIONSHIP_ROUTE_POLICY_ID,
    QueryTypeRouter,
    build_query_type_router_public_rows,
)


def test_query_type_router_routes_relationship_to_hybrid_candidate() -> None:
    decision = QueryTypeRouter().route("relationship")

    assert decision.route_policy_id == RELATIONSHIP_ROUTE_POLICY_ID
    assert decision.selected_candidate_id == RELATIONSHIP_RETRIEVAL_CANDIDATE_ID
    assert decision.execution_mode == "hybrid_weighted"
    assert decision.should_retrieve is True
    assert decision.claim_boundary == "dev-input-only"


def test_query_type_router_routes_no_answer_to_abstain_first() -> None:
    decision = QueryTypeRouter().route("no_answer")

    assert decision.route_policy_id == NO_ANSWER_ROUTE_POLICY_ID
    assert decision.execution_mode == "abstain"
    assert decision.should_retrieve is False
    assert decision.selected_candidate_id == "abstain_contract"


def test_query_type_router_keeps_default_for_non_relationship_answerable_types() -> None:
    router = QueryTypeRouter()

    for query_type in ("overview", "place_fact", "place_story", "route_context", "voice_followup"):
        decision = router.route(query_type)
        assert decision.selected_candidate_id == DEFAULT_RETRIEVAL_CANDIDATE_ID
        assert decision.execution_mode == "dense"
        assert decision.should_retrieve is True


def test_query_type_router_public_rows_are_sanitized() -> None:
    rows = build_query_type_router_public_rows()

    assert len(rows) == 7
    assert all("query" not in row for row in rows)
    assert all("answer" not in row for row in rows)
    assert all("raw_text" not in row for row in rows)
    assert any(row["route_policy_id"] == RELATIONSHIP_ROUTE_POLICY_ID for row in rows)
