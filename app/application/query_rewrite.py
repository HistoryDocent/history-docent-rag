from __future__ import annotations

import time
import re
from dataclasses import dataclass

from app.domain.place_catalog import Place, PlaceCatalog
from app.domain.retrieval import QueryType, RetrievalEvalItem


QUERY_REWRITE_STRATEGY_ID = "place-aware-deterministic-v1"
QUERY_REWRITE_TARGET_TYPES: tuple[QueryType, ...] = (
    "place_fact",
    "place_story",
    "route_context",
    "voice_followup",
)
_ASCII_ALNUM_PATTERN = re.compile(r"[0-9a-z]")


@dataclass(frozen=True)
class QueryRewriteConfig:
    strategy_id: str = QUERY_REWRITE_STRATEGY_ID
    target_query_types: tuple[QueryType, ...] = QUERY_REWRITE_TARGET_TYPES
    max_aliases_per_place: int = 4
    max_related_places: int = 3
    max_context_chars: int = 240
    include_related_places_for_route: bool = True
    include_intent_terms: bool = True

    def __post_init__(self) -> None:
        if self.max_aliases_per_place < 1:
            raise ValueError("max_aliases_per_place must be >= 1")
        if self.max_related_places < 0:
            raise ValueError("max_related_places must be >= 0")
        if self.max_context_chars < 0:
            raise ValueError("max_context_chars must be >= 0")


@dataclass(frozen=True)
class QueryRewriteResult:
    query_id: str
    query_type: QueryType
    original_query_text: str
    rewritten_query_text: str
    changed: bool
    applied_rules: tuple[str, ...]
    place_ids: tuple[str, ...]
    latency_ms: float
    invalid_json: bool = False


class PlaceAwareQueryRewriter:
    def __init__(
        self,
        *,
        catalog: PlaceCatalog,
        config: QueryRewriteConfig | None = None,
    ) -> None:
        self.catalog = catalog
        self.config = config or QueryRewriteConfig()
        self._place_by_id = {place.place_id: place for place in catalog.places}
        self._alias_to_place_ids = _build_alias_index(catalog)

    def rewrite(self, item: RetrievalEvalItem) -> QueryRewriteResult:
        started = time.perf_counter()
        query = item.query
        query_text = query.query_text.strip()
        applied_rules: list[str] = []
        if query.expected_behavior == "abstain" or query.query_type == "no_answer":
            applied_rules.append("no_answer_guard")
            return self._result(
                item=item,
                rewritten_query_text=query_text,
                place_ids=(),
                applied_rules=applied_rules,
                started=started,
            )
        if query.query_type not in self.config.target_query_types:
            applied_rules.append("query_type_passthrough")
            return self._result(
                item=item,
                rewritten_query_text=query_text,
                place_ids=(),
                applied_rules=applied_rules,
                started=started,
            )

        place_ids = self._collect_place_ids(item)
        if place_ids:
            applied_rules.append("place_alias_expansion")
        context_text = self._context_text(item)
        if query.query_type == "voice_followup" and context_text:
            applied_rules.append("voice_context_expansion")
        related_terms = self._related_place_terms(
            place_ids=place_ids,
            query_type=query.query_type,
        )
        if related_terms:
            applied_rules.append("route_related_place_expansion")
        intent_terms = self._intent_terms(query.query_type)
        if intent_terms:
            applied_rules.append("query_type_intent_terms")

        segments = [
            query_text,
            context_text,
            self._place_terms_text(place_ids),
            "관련 장소: " + " ".join(related_terms) if related_terms else "",
            "검색 의도: " + " ".join(intent_terms) if intent_terms else "",
        ]
        rewritten_query_text = _join_unique_segments(segments)
        if not applied_rules:
            applied_rules.append("no_rewrite_signal")
        return self._result(
            item=item,
            rewritten_query_text=rewritten_query_text,
            place_ids=place_ids,
            applied_rules=applied_rules,
            started=started,
        )

    def _collect_place_ids(self, item: RetrievalEvalItem) -> tuple[str, ...]:
        detected: list[str] = []
        for place_id in item.metadata.place_ids:
            if place_id in self._place_by_id:
                detected.append(place_id)
        search_space = " ".join(
            part
            for part in (item.query.query_text, item.query.user_context or "")
            if part
        )
        normalized = _normalize_lookup_text(search_space)
        for alias, place_ids in self._alias_to_place_ids.items():
            if _alias_matches(alias=alias, normalized_text=normalized):
                detected.extend(place_ids)
        return _unique(detected)

    def _context_text(self, item: RetrievalEvalItem) -> str:
        if not item.query.user_context or self.config.max_context_chars == 0:
            return ""
        context = " ".join(item.query.user_context.split())
        if len(context) > self.config.max_context_chars:
            context = context[: self.config.max_context_chars].rstrip()
        return f"이전 맥락: {context}"

    def _place_terms_text(self, place_ids: tuple[str, ...]) -> str:
        terms: list[str] = []
        for place_id in place_ids:
            place = self._place_by_id.get(place_id)
            if place is None:
                continue
            terms.extend(_place_alias_terms(place, self.config.max_aliases_per_place))
        if not terms:
            return ""
        return "장소 단서: " + " ".join(_unique(terms))

    def _related_place_terms(
        self,
        *,
        place_ids: tuple[str, ...],
        query_type: QueryType,
    ) -> list[str]:
        if (
            not self.config.include_related_places_for_route
            or query_type != "route_context"
        ):
            return []
        related_place_ids: list[str] = []
        for place_id in place_ids:
            place = self._place_by_id.get(place_id)
            if place is None:
                continue
            related_place_ids.extend(place.related_place_ids)
            related_place_ids.extend(
                relation.target_place_id for relation in place.relations
            )
        terms: list[str] = []
        for related_place_id in _unique(related_place_ids)[: self.config.max_related_places]:
            related_place = self._place_by_id.get(related_place_id)
            if related_place is not None:
                terms.append(related_place.canonical_name)
        return terms

    def _intent_terms(self, query_type: QueryType) -> tuple[str, ...]:
        if not self.config.include_intent_terms:
            return ()
        if query_type == "place_fact":
            return ("한양", "조선", "역사", "장소")
        if query_type == "place_story":
            return ("한양", "조선", "역사 이야기", "관광 설명")
        if query_type == "route_context":
            return ("한양", "서울", "동선", "연결")
        if query_type == "voice_followup":
            return ("한양", "조선", "이전 맥락", "장소")
        return ()

    def _result(
        self,
        *,
        item: RetrievalEvalItem,
        rewritten_query_text: str,
        place_ids: tuple[str, ...],
        applied_rules: list[str],
        started: float,
    ) -> QueryRewriteResult:
        original = item.query.query_text.strip()
        return QueryRewriteResult(
            query_id=item.query.query_id,
            query_type=item.query.query_type,
            original_query_text=original,
            rewritten_query_text=rewritten_query_text,
            changed=rewritten_query_text != original,
            applied_rules=tuple(_unique(applied_rules)),
            place_ids=place_ids,
            latency_ms=round((time.perf_counter() - started) * 1000, 6),
        )


def summarize_query_rewrite_results(
    *,
    config: QueryRewriteConfig,
    results: list[QueryRewriteResult],
) -> dict[str, str | int | float | bool]:
    invalid_count = sum(1 for result in results if result.invalid_json)
    latencies = [result.latency_ms for result in results]
    return {
        "query_rewrite": True,
        "query_rewrite_strategy": config.strategy_id,
        "query_rewrite_target_types": ",".join(config.target_query_types),
        "query_rewrite_success_count": len(results) - invalid_count,
        "query_rewrite_changed_count": sum(1 for result in results if result.changed),
        "query_rewrite_invalid_json_count": invalid_count,
        "query_rewrite_invalid_json_rate": round(
            invalid_count / len(results),
            6,
        )
        if results
        else 0.0,
        "query_rewrite_no_answer_guard_count": sum(
            1 for result in results if "no_answer_guard" in result.applied_rules
        ),
        "query_rewrite_latency_p95_ms": _percentile(latencies, 0.95),
        "query_rewrite_solar_call_count": 0,
    }


def _build_alias_index(catalog: PlaceCatalog) -> dict[str, tuple[str, ...]]:
    index: dict[str, list[str]] = {}
    for place in catalog.places:
        terms = [place.canonical_name]
        terms.extend(alias.alias for alias in place.aliases)
        for term in terms:
            normalized = _normalize_lookup_text(term)
            if normalized:
                index.setdefault(normalized, []).append(place.place_id)
    return {alias: _unique(place_ids) for alias, place_ids in index.items()}


def _place_alias_terms(place: Place, max_aliases: int) -> list[str]:
    terms = [place.canonical_name]
    for alias in place.aliases:
        if alias.alias not in terms:
            terms.append(alias.alias)
        if len(terms) >= max_aliases:
            break
    return terms


def _join_unique_segments(segments: list[str]) -> str:
    normalized_segments = []
    seen: set[str] = set()
    for segment in segments:
        cleaned = " ".join(segment.split())
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        normalized_segments.append(cleaned)
        seen.add(key)
    return " ".join(normalized_segments)


def _normalize_lookup_text(value: str) -> str:
    return " ".join(value.casefold().split())


def _alias_matches(*, alias: str, normalized_text: str) -> bool:
    if not _ASCII_ALNUM_PATTERN.search(alias):
        return alias in normalized_text
    pattern = re.compile(
        rf"(?<![0-9a-z]){re.escape(alias)}(?![0-9a-z])",
        re.IGNORECASE,
    )
    return pattern.search(normalized_text) is not None


def _unique(values: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        if value in seen:
            continue
        unique_values.append(value)
        seen.add(value)
    return tuple(unique_values)


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = round((len(sorted_values) - 1) * percentile)
    return round(sorted_values[index], 6)
