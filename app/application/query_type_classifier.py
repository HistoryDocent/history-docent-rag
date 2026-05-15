from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.retrieval import QueryType, REQUIRED_QUERY_TYPES


QUERY_TYPE_CLASSIFIER_ID = "deterministic_query_type_classifier_v1"
FALLBACK_QUERY_TYPE: QueryType = "place_fact"
_ASCII_ALNUM_PATTERN = re.compile(r"[0-9a-z]", re.IGNORECASE)
_ROUTE_FROM_TO_PATTERN = re.compile(
    r".+(에서).+(로|으로).+(가|가는|걸|이동|지나|이어)",
)


class QueryTypeClassifierModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class QueryTypeClassificationInput(QueryTypeClassifierModel):
    query_text: str = Field(min_length=1)
    user_context: str | None = None
    place_ids: tuple[str, ...] = Field(default_factory=tuple)
    has_dialog_context: bool = False


class QueryTypeClassificationResult(QueryTypeClassifierModel):
    classifier_id: str = QUERY_TYPE_CLASSIFIER_ID
    predicted_query_type: QueryType
    confidence: float = Field(ge=0.0, le=1.0)
    fallback_used: bool
    matched_rule_ids: tuple[str, ...] = Field(default_factory=tuple)
    candidate_scores: dict[QueryType, float]
    latency_ms: float = Field(ge=0.0)


@dataclass(frozen=True)
class _SignalRule:
    rule_id: str
    query_type: QueryType
    phrases: tuple[str, ...] = ()
    patterns: tuple[re.Pattern[str], ...] = ()
    weight: float = 1.0


class DeterministicQueryTypeClassifier:
    def __init__(self, *, classifier_id: str = QUERY_TYPE_CLASSIFIER_ID) -> None:
        self.classifier_id = classifier_id

    def classify(
        self,
        value: QueryTypeClassificationInput | dict[str, Any],
    ) -> QueryTypeClassificationResult:
        started = time.perf_counter()
        item = QueryTypeClassificationInput.model_validate(value)
        query_text = _normalize(item.query_text)
        scores: dict[QueryType, float] = {query_type: 0.0 for query_type in REQUIRED_QUERY_TYPES}
        matched_rules: list[str] = []

        for rule in _SIGNAL_RULES:
            count = _count_rule_matches(rule, query_text=query_text)
            if count:
                scores[rule.query_type] += rule.weight * count
                matched_rules.append(rule.rule_id)

        if item.place_ids:
            scores["place_fact"] += 0.5
            matched_rules.append("place_ids_fact_default")
            if len(item.place_ids) >= 2:
                scores["relationship"] += 0.35
                matched_rules.append("multi_place_relationship_hint")

        if _looks_like_voice_followup(
            query_text=query_text,
            has_dialog_context=item.has_dialog_context,
        ):
            scores["voice_followup"] += 5.0
            matched_rules.append("short_deictic_dialog_followup")

        if _looks_like_route_context(query_text):
            scores["route_context"] += 3.0
            matched_rules.append("route_from_to_pattern")

        predicted, top_score, runner_up_score = _select_query_type(scores)
        fallback_used = top_score <= 0.0
        if fallback_used:
            predicted = FALLBACK_QUERY_TYPE
            top_score = 0.0
            matched_rules.append("fallback_place_fact")

        confidence = _confidence(
            top_score=top_score,
            runner_up_score=runner_up_score,
            fallback_used=fallback_used,
        )
        latency_ms = round((time.perf_counter() - started) * 1000, 6)
        return QueryTypeClassificationResult(
            classifier_id=self.classifier_id,
            predicted_query_type=predicted,
            confidence=confidence,
            fallback_used=fallback_used,
            matched_rule_ids=tuple(_unique(matched_rules)),
            candidate_scores={key: round(value, 6) for key, value in scores.items()},
            latency_ms=latency_ms,
        )


_SIGNAL_RULES: tuple[_SignalRule, ...] = (
    _SignalRule(
        rule_id="no_answer_live_or_action_request",
        query_type="no_answer",
        phrases=(
            "오늘",
            "지금",
            "현재",
            "실시간",
            "예약",
            "입장권",
            "몇 장 남았",
            "대기 시간",
            "빈자리",
            "시간표",
            "결제",
            "교통 통제",
            "혼잡도",
            "live crowd",
            "current air quality",
            "right now",
        ),
        weight=2.5,
    ),
    _SignalRule(
        rule_id="route_movement_terms",
        query_type="route_context",
        phrases=(
            "동선",
            "걸으며",
            "걸을 때",
            "이동하며",
            "방향으로",
            "지나",
            "가는 길",
            "이어갈",
            "이어지는 궁궐",
            "도심 동선",
        ),
        weight=1.8,
    ),
    _SignalRule(
        rule_id="relationship_connection_terms",
        query_type="relationship",
        phrases=(
            "관계",
            "연결",
            "갈등",
            "어떻게 연결",
            "어떻게 이어",
            "이어지는 흐름",
            "영향",
            "비교",
            "복권",
        ),
        weight=1.6,
    ),
    _SignalRule(
        rule_id="place_story_narrative_terms",
        query_type="place_story",
        phrases=(
            "이야기",
            "흥미",
            "현장감",
            "들려",
            "풀어",
            "관광객",
            "짧게 설명",
            "앞에서",
            "걸으며",
        ),
        weight=1.7,
    ),
    _SignalRule(
        rule_id="overview_summary_terms",
        query_type="overview",
        phrases=(
            "개괄",
            "요약",
            "큰 흐름",
            "공간 흐름",
            "도심 공간",
            "시대마다",
            "전체",
            "일대",
            "권역",
        ),
        weight=1.6,
    ),
    _SignalRule(
        rule_id="place_fact_factual_terms",
        query_type="place_fact",
        phrases=(
            "배경",
            "의미",
            "이름",
            "정통성",
            "세워진",
            "뒷받침",
            "자료",
            "순서",
            "요지",
        ),
        weight=1.5,
    ),
)


def _normalize(value: str) -> str:
    return " ".join(value.casefold().split())


def _count_rule_matches(rule: _SignalRule, *, query_text: str) -> int:
    search_text = query_text
    count = 0
    for phrase in rule.phrases:
        normalized_phrase = _normalize(phrase)
        if _phrase_matches(phrase=normalized_phrase, search_text=search_text):
            count += 1
    count += sum(1 for pattern in rule.patterns if pattern.search(search_text))
    return count


def _phrase_matches(*, phrase: str, search_text: str) -> bool:
    if not phrase:
        return False
    if not _ASCII_ALNUM_PATTERN.search(phrase):
        return phrase in search_text
    pattern = re.compile(
        rf"(?<![0-9a-z]){re.escape(phrase)}(?![0-9a-z])",
        re.IGNORECASE,
    )
    return pattern.search(search_text) is not None


def _looks_like_voice_followup(*, query_text: str, has_dialog_context: bool) -> bool:
    if not has_dialog_context:
        return False
    compact = query_text.replace(" ", "")
    if len(compact) > 28:
        return False
    deictic_terms = ("그", "거기", "그곳", "아까", "방금", "이거", "저거")
    followup_terms = ("왜", "누가", "뭐", "무엇", "어떻게", "나와", "했어", "거야")
    return any(term in query_text for term in deictic_terms) and any(
        term in query_text for term in followup_terms
    )


def _looks_like_route_context(query_text: str) -> bool:
    return bool(_ROUTE_FROM_TO_PATTERN.search(query_text))


def _select_query_type(scores: dict[QueryType, float]) -> tuple[QueryType, float, float]:
    priority: dict[QueryType, int] = {
        "no_answer": 0,
        "voice_followup": 1,
        "route_context": 2,
        "relationship": 3,
        "place_story": 4,
        "overview": 5,
        "place_fact": 6,
    }
    ordered = sorted(
        scores.items(),
        key=lambda item: (-item[1], priority[item[0]]),
    )
    top_type, top_score = ordered[0]
    runner_up_score = ordered[1][1] if len(ordered) > 1 else 0.0
    return top_type, top_score, runner_up_score


def _confidence(*, top_score: float, runner_up_score: float, fallback_used: bool) -> float:
    if fallback_used:
        return 0.35
    margin = max(0.0, top_score - runner_up_score)
    return round(min(0.99, 0.5 + (top_score / 12.0) + (margin / 8.0)), 6)


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        if value in seen:
            continue
        unique_values.append(value)
        seen.add(value)
    return unique_values
