from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.application.query_type_classifier import QueryTypeClassificationResult
from app.domain.retrieval import QueryType, REQUIRED_QUERY_TYPES


RELATIONSHIP_ROUTE_GUARD_POLICY_ID = "relationship-route-guard-v1"


class QueryTypeRouteGuardModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RelationshipRouteGuardInput(QueryTypeRouteGuardModel):
    query_text: str = Field(min_length=1)
    classification: QueryTypeClassificationResult


class RelationshipRouteGuardDecision(QueryTypeRouteGuardModel):
    guard_policy_id: str = RELATIONSHIP_ROUTE_GUARD_POLICY_ID
    original_query_type: QueryType
    guarded_query_type: QueryType
    guard_applied: bool
    guard_reason_tags: tuple[str, ...]
    relationship_score: float = Field(ge=0.0)
    fallback_query_type: QueryType
    fallback_score: float = Field(ge=0.0)
    score_margin: float
    strong_relationship_intent: bool
    overview_tie_risk: bool
    fact_reason_risk: bool


class RelationshipRouteGuard:
    def __init__(self, *, guard_policy_id: str = RELATIONSHIP_ROUTE_GUARD_POLICY_ID) -> None:
        self.guard_policy_id = guard_policy_id

    def apply(
        self,
        value: RelationshipRouteGuardInput | dict[str, Any],
    ) -> RelationshipRouteGuardDecision:
        item = RelationshipRouteGuardInput.model_validate(value)
        classification = item.classification
        fallback_query_type, fallback_score = _highest_non_relationship_score(
            classification.candidate_scores
        )
        relationship_score = round(
            classification.candidate_scores.get("relationship", 0.0),
            6,
        )
        score_margin = round(relationship_score - fallback_score, 6)
        strong_relationship_intent = _has_strong_relationship_intent(item.query_text)
        overview_tie_risk = _has_overview_tie_risk(
            classification=classification,
            relationship_score=relationship_score,
        )
        fact_reason_risk = _has_fact_reason_risk(
            query_text=item.query_text,
            strong_relationship_intent=strong_relationship_intent,
        )

        if classification.predicted_query_type != "relationship":
            return RelationshipRouteGuardDecision(
                guard_policy_id=self.guard_policy_id,
                original_query_type=classification.predicted_query_type,
                guarded_query_type=classification.predicted_query_type,
                guard_applied=False,
                guard_reason_tags=("not_relationship_prediction",),
                relationship_score=relationship_score,
                fallback_query_type=fallback_query_type,
                fallback_score=fallback_score,
                score_margin=score_margin,
                strong_relationship_intent=strong_relationship_intent,
                overview_tie_risk=overview_tie_risk,
                fact_reason_risk=fact_reason_risk,
            )

        guard_tags = _guard_tags(
            strong_relationship_intent=strong_relationship_intent,
            overview_tie_risk=overview_tie_risk,
            fact_reason_risk=fact_reason_risk,
        )
        guard_applied = overview_tie_risk or fact_reason_risk or not strong_relationship_intent
        return RelationshipRouteGuardDecision(
            guard_policy_id=self.guard_policy_id,
            original_query_type=classification.predicted_query_type,
            guarded_query_type=(
                fallback_query_type if guard_applied else classification.predicted_query_type
            ),
            guard_applied=guard_applied,
            guard_reason_tags=guard_tags,
            relationship_score=relationship_score,
            fallback_query_type=fallback_query_type,
            fallback_score=fallback_score,
            score_margin=score_margin,
            strong_relationship_intent=strong_relationship_intent,
            overview_tie_risk=overview_tie_risk,
            fact_reason_risk=fact_reason_risk,
        )


def _highest_non_relationship_score(scores: dict[QueryType, float]) -> tuple[QueryType, float]:
    priority: dict[QueryType, int] = {
        "no_answer": 0,
        "voice_followup": 1,
        "route_context": 2,
        "overview": 3,
        "place_story": 4,
        "place_fact": 5,
        "relationship": 6,
    }
    ordered = sorted(
        (
            (query_type, score)
            for query_type, score in scores.items()
            if query_type != "relationship"
        ),
        key=lambda item: (-item[1], priority[item[0]]),
    )
    if not ordered:
        return "place_fact", 0.0
    query_type, score = ordered[0]
    return query_type, round(score, 6)


def _has_overview_tie_risk(
    *,
    classification: QueryTypeClassificationResult,
    relationship_score: float,
) -> bool:
    overview_score = classification.candidate_scores.get("overview", 0.0)
    score_margin = relationship_score - overview_score
    return (
        "overview_summary_terms" in classification.matched_rule_ids
        and overview_score > 0.0
        and score_margin <= 0.35
    )


def _has_fact_reason_risk(
    *,
    query_text: str,
    strong_relationship_intent: bool,
) -> bool:
    normalized = _normalize(query_text)
    if strong_relationship_intent:
        return False
    return any(term in normalized for term in ("이유", "왜", "배경"))


def _has_strong_relationship_intent(query_text: str) -> bool:
    normalized = _normalize(query_text)
    phrases = (
        "관계",
        "갈등",
        "어떻게 연결",
        "어떻게 이어",
        "이어지는 흐름",
        "이어지는지",
        "이어졌",
        "영향",
        "비교",
        "복권",
        "배치",
        "선택",
        "움직임",
        "행진",
        "연결해서",
        "연결할 근거",
    )
    return any(phrase in normalized for phrase in phrases)


def _guard_tags(
    *,
    strong_relationship_intent: bool,
    overview_tie_risk: bool,
    fact_reason_risk: bool,
) -> tuple[str, ...]:
    tags: list[str] = []
    if overview_tie_risk:
        tags.append("block_overview_tie_risk")
    if fact_reason_risk:
        tags.append("block_fact_reason_risk")
    if not strong_relationship_intent:
        tags.append("block_weak_relationship_intent")
    if not tags:
        tags.append("allow_strong_relationship_intent")
    return tuple(tags)


def _normalize(value: str) -> str:
    return " ".join(value.casefold().split())


def required_guarded_query_types() -> tuple[QueryType, ...]:
    return REQUIRED_QUERY_TYPES
