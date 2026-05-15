from __future__ import annotations

from app.application.query_type_classifier import (
    FALLBACK_QUERY_TYPE,
    QUERY_TYPE_CLASSIFIER_ID,
    DeterministicQueryTypeClassifier,
    QueryTypeClassificationInput,
)


def test_query_type_classifier_detects_all_core_query_types() -> None:
    classifier = DeterministicQueryTypeClassifier()
    cases = [
        (
            "경복궁이 조선 초 새 수도의 상징으로 세워진 배경을 설명할 근거를 찾아줘",
            "place_fact",
            False,
        ),
        (
            "광화문 광장에서 세종 이야기를 관광객에게 짧고 흥미롭게 들려줄 근거를 찾아줘",
            "place_story",
            False,
        ),
        (
            "정도전과 이방원의 갈등이 경복궁과 창덕궁 선택에 어떻게 남았는지 찾아줘",
            "relationship",
            False,
        ),
        (
            "조선 초기 궁궐과 종묘가 왕권을 보여주는 방식을 요약할 근거를 찾아줘",
            "overview",
            False,
        ),
        (
            "광화문에서 경복궁을 지나 종묘로 가는 동선에서 설명할 근거를 찾아줘",
            "route_context",
            True,
        ),
        (
            "그 사람이 왜 그 궁을 피했어?",
            "voice_followup",
            True,
        ),
        (
            "오늘 경복궁 야간개장 입장권이 몇 장 남았어?",
            "no_answer",
            False,
        ),
    ]

    for query, expected, has_context in cases:
        result = classifier.classify(
            QueryTypeClassificationInput(
                query_text=query,
                has_dialog_context=has_context,
                place_ids=("gyeongbokgung",),
            )
        )

        assert result.classifier_id == QUERY_TYPE_CLASSIFIER_ID
        assert result.predicted_query_type == expected
        assert result.confidence >= 0.5
        assert result.matched_rule_ids


def test_query_type_classifier_prefers_route_over_dialog_context_for_movement() -> None:
    result = DeterministicQueryTypeClassifier().classify(
        {
            "query_text": "덕수궁에서 정동길과 남산 방향으로 이동하며 설명할 근거를 찾아줘",
            "has_dialog_context": True,
            "place_ids": ("deoksugung", "namsan"),
        }
    )

    assert result.predicted_query_type == "route_context"


def test_query_type_classifier_uses_public_safe_fallback() -> None:
    result = DeterministicQueryTypeClassifier().classify(
        {"query_text": "설명할 근거를 찾아줘"}
    )

    assert result.predicted_query_type == FALLBACK_QUERY_TYPE
    assert result.fallback_used is True
    assert "fallback_place_fact" in result.matched_rule_ids
    assert "설명할 근거" not in result.model_dump_json()
