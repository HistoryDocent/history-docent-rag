from __future__ import annotations

from app.application.query_type_classifier import (
    DeterministicQueryTypeClassifier,
    QueryTypeClassificationInput,
)
from app.application.query_type_route_guard import (
    RelationshipRouteGuard,
    RelationshipRouteGuardInput,
)


def test_relationship_route_guard_blocks_fact_reason_false_hybrid() -> None:
    classifier = DeterministicQueryTypeClassifier()
    guard = RelationshipRouteGuard()
    classification = classifier.classify(
        QueryTypeClassificationInput(
            query_text="창덕궁이 태종 시기 권력 기억과 연결되는 이유를 설명할 근거를 찾아줘",
            place_ids=("changdeokgung", "taejong-memory"),
        )
    )

    decision = guard.apply(
        RelationshipRouteGuardInput(
            query_text="창덕궁이 태종 시기 권력 기억과 연결되는 이유를 설명할 근거를 찾아줘",
            classification=classification,
        )
    )

    assert classification.predicted_query_type == "relationship"
    assert decision.guard_applied is True
    assert decision.guarded_query_type == "place_fact"
    assert "block_fact_reason_risk" in decision.guard_reason_tags


def test_relationship_route_guard_keeps_strong_relationship_intent() -> None:
    classifier = DeterministicQueryTypeClassifier()
    guard = RelationshipRouteGuard()
    query = "정도전과 이방원의 갈등이 경복궁과 창덕궁 선택에 어떻게 남았는지 찾아줘"
    classification = classifier.classify(
        QueryTypeClassificationInput(
            query_text=query,
            place_ids=("gyeongbokgung", "changdeokgung"),
        )
    )

    decision = guard.apply(
        RelationshipRouteGuardInput(query_text=query, classification=classification)
    )

    assert classification.predicted_query_type == "relationship"
    assert decision.guard_applied is False
    assert decision.guarded_query_type == "relationship"
    assert decision.guard_reason_tags == ("allow_strong_relationship_intent",)


def test_relationship_route_guard_blocks_overview_tie_risk() -> None:
    classifier = DeterministicQueryTypeClassifier()
    guard = RelationshipRouteGuard()
    query = "덕수궁과 정동 일대에서 대한제국부터 외교권 침탈까지 이어지는 흐름을 찾아줘"
    classification = classifier.classify(
        QueryTypeClassificationInput(
            query_text=query,
            place_ids=("deoksugung",),
        )
    )

    decision = guard.apply(
        RelationshipRouteGuardInput(query_text=query, classification=classification)
    )

    assert classification.predicted_query_type == "relationship"
    assert decision.guard_applied is True
    assert decision.guarded_query_type == "overview"
    assert "block_overview_tie_risk" in decision.guard_reason_tags
