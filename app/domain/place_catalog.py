from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


PLACE_CATALOG_VERSION = "place-catalog/v1"
PLACE_CATALOG_REPORT_VERSION = "place-catalog-validation/v1"
MINIMUM_PLACE_COUNT = 8
MINIMUM_ALIAS_COUNT = 20
MAX_PUBLIC_NAME_LENGTH = 80
MAX_PUBLIC_ALIAS_LENGTH = 80
MAX_PUBLIC_RATIONALE_LENGTH = 80
MAX_PUBLIC_TAG_LENGTH = 40
MAX_PUBLIC_STRING_LENGTH = 120

PlaceCategory = Literal[
    "palace",
    "gate_square",
    "shrine",
    "district",
    "city_wall",
    "mountain",
    "route_anchor",
    "other",
]
AliasLanguage = Literal["ko", "en", "hanja", "mixed"]
AliasType = Literal["primary", "alternative", "tourism", "historic", "transliteration"]
RelationType = Literal[
    "nearby",
    "route_neighbor",
    "historical_context",
    "same_area",
    "viewpoint",
]
SourcePolicy = Literal["manual_public_seed"]

FORBIDDEN_PUBLIC_PLACE_FIELDS: frozenset[str] = frozenset(
    {
        "answer",
        "answer_text",
        "content",
        "context_text",
        "description",
        "excerpt",
        "html",
        "markdown",
        "quote",
        "raw_text",
        "search_text",
        "source_text",
        "text",
    }
)
SECRET_VALUE_MARKERS = (
    "sk-",
    "api_" + "key=",
    "api" + "key=",
    "ghp_",
    "github_pat_",
    "hf_",
    "xoxb-",
    "bearer ",
    "pass" + "word=",
    "to" + "ken=",
    "sec" + "ret=",
)
_PLACE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_TAG_PATTERN = re.compile(r"^[a-z0-9_]+$")
_WINDOWS_PATH_PATTERN = re.compile(r"([A-Za-z]:[\\/]|\\\\[^\\/]+[\\/][^\\/]+)")
_POSIX_PRIVATE_PATH_PATTERN = re.compile(
    r"(^|\s)/(home|users|mnt|var|tmp|private|runner|workspace|root)/",
    re.IGNORECASE,
)


class PlaceCatalogModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PlaceAlias(PlaceCatalogModel):
    alias: str = Field(min_length=1, max_length=MAX_PUBLIC_ALIAS_LENGTH)
    language: AliasLanguage
    alias_type: AliasType

    @field_validator("alias")
    @classmethod
    def validate_alias(cls, value: str) -> str:
        return _validate_single_line(value, "alias")


class PlaceRelation(PlaceCatalogModel):
    target_place_id: str = Field(min_length=1)
    relation_type: RelationType
    rationale: str = Field(min_length=1, max_length=MAX_PUBLIC_RATIONALE_LENGTH)

    @field_validator("target_place_id")
    @classmethod
    def validate_target_place_id(cls, value: str) -> str:
        return _validate_place_id(value)

    @field_validator("rationale")
    @classmethod
    def validate_rationale(cls, value: str) -> str:
        return _validate_single_line(value, "rationale")


class Place(PlaceCatalogModel):
    place_id: str = Field(min_length=1)
    canonical_name: str = Field(min_length=1, max_length=MAX_PUBLIC_NAME_LENGTH)
    category: PlaceCategory
    aliases: list[PlaceAlias] = Field(min_length=1)
    related_place_ids: list[str] = Field(default_factory=list)
    relations: list[PlaceRelation] = Field(default_factory=list)
    tour_context_tags: list[str] = Field(default_factory=list)
    source_policy: SourcePolicy = "manual_public_seed"
    public_allowed: bool = True

    @field_validator("place_id")
    @classmethod
    def validate_place_id(cls, value: str) -> str:
        return _validate_place_id(value)

    @field_validator("canonical_name")
    @classmethod
    def validate_canonical_name(cls, value: str) -> str:
        return _validate_single_line(value, "canonical_name")

    @field_validator("related_place_ids")
    @classmethod
    def validate_related_place_ids(cls, values: list[str]) -> list[str]:
        return [_validate_place_id(value) for value in values]

    @field_validator("tour_context_tags")
    @classmethod
    def validate_tour_context_tags(cls, values: list[str]) -> list[str]:
        validated: list[str] = []
        for value in values:
            _validate_single_line(value, "tour_context_tag")
            if len(value) > MAX_PUBLIC_TAG_LENGTH:
                raise ValueError("tour_context_tag is too long for public seed")
            if not _TAG_PATTERN.fullmatch(value):
                raise ValueError("tour_context_tag must use lowercase letters, digits, and underscores")
            validated.append(value)
        return validated


class PlaceCatalog(PlaceCatalogModel):
    catalog_version: str = PLACE_CATALOG_VERSION
    places: list[Place] = Field(min_length=1)


class PlaceCatalogQualitySummary(PlaceCatalogModel):
    place_count: int = Field(ge=0)
    alias_count: int = Field(ge=0)
    relation_count: int = Field(ge=0)
    minimum_place_count: int = Field(default=MINIMUM_PLACE_COUNT, ge=0)
    minimum_alias_count: int = Field(default=MINIMUM_ALIAS_COUNT, ge=0)
    duplicate_place_id_count: int = Field(ge=0)
    duplicate_canonical_name_count: int = Field(ge=0)
    duplicate_alias_count: int = Field(ge=0)
    unknown_related_place_count: int = Field(ge=0)
    self_relation_count: int = Field(ge=0)
    place_without_relation_count: int = Field(ge=0)
    place_without_context_tag_count: int = Field(ge=0)
    public_false_count: int = Field(ge=0)
    public_raw_text_leakage_count: int = Field(ge=0)
    private_path_leakage_count: int = Field(ge=0)
    secret_like_leakage_count: int = Field(ge=0)


class PlaceCatalogReport(PlaceCatalogModel):
    report_version: str = PLACE_CATALOG_REPORT_VERSION
    catalog_version: str
    generated_at_utc: str
    quality_summary: PlaceCatalogQualitySummary
    place_count_by_category: dict[str, int]
    alias_count_by_language: dict[str, int]
    relation_count_by_type: dict[str, int]
    qualitative_assessment: dict[str, str]


def load_place_catalog(path: Path) -> PlaceCatalog:
    return PlaceCatalog.model_validate_json(path.read_text(encoding="utf-8"))


def place_catalog_to_json(catalog: PlaceCatalog) -> str:
    return json.dumps(
        catalog.model_dump(mode="json"),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )


def build_place_catalog_report(catalog: PlaceCatalog) -> PlaceCatalogReport:
    payload = catalog.model_dump(mode="json")
    place_ids = [place.place_id for place in catalog.places]
    canonical_names = [place.canonical_name for place in catalog.places]
    aliases = [alias.alias for place in catalog.places for alias in place.aliases]
    related_targets = _collect_related_targets(catalog)

    quality_summary = PlaceCatalogQualitySummary(
        place_count=len(catalog.places),
        alias_count=len(aliases),
        relation_count=sum(len(place.relations) for place in catalog.places),
        duplicate_place_id_count=_count_duplicate_extra_values(place_ids),
        duplicate_canonical_name_count=_count_duplicate_extra_values(canonical_names),
        duplicate_alias_count=_count_duplicate_extra_values(
            [_normalize_alias(alias) for alias in aliases]
        ),
        unknown_related_place_count=len(
            sorted(target for target in related_targets if target not in set(place_ids))
        ),
        self_relation_count=sum(
            _count_self_references(place) for place in catalog.places
        ),
        place_without_relation_count=sum(
            1
            for place in catalog.places
            if not place.related_place_ids and not place.relations
        ),
        place_without_context_tag_count=sum(
            1 for place in catalog.places if not place.tour_context_tags
        ),
        public_false_count=sum(1 for place in catalog.places if not place.public_allowed),
        public_raw_text_leakage_count=(
            _count_forbidden_public_fields(payload)
            + _count_source_text_like_public_values(payload)
        ),
        private_path_leakage_count=sum(
            1 for value in _iter_string_values(payload) if _contains_private_path(value)
        ),
        secret_like_leakage_count=sum(
            1 for value in _iter_string_values(payload) if _contains_secret_like_value(value)
        ),
    )

    return PlaceCatalogReport(
        catalog_version=catalog.catalog_version,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        quality_summary=quality_summary,
        place_count_by_category=dict(
            sorted(Counter(place.category for place in catalog.places).items())
        ),
        alias_count_by_language=dict(
            sorted(
                Counter(
                    alias.language for place in catalog.places for alias in place.aliases
                ).items()
            )
        ),
        relation_count_by_type=dict(
            sorted(
                Counter(
                    relation.relation_type
                    for place in catalog.places
                    for relation in place.relations
                ).items()
            )
        ),
        qualitative_assessment=_build_qualitative_assessment(quality_summary),
    )


def collect_place_catalog_gate_failures(report: PlaceCatalogReport) -> list[str]:
    return _collect_place_catalog_gate_failures_from_summary(report.quality_summary)


def _collect_place_catalog_gate_failures_from_summary(
    summary: PlaceCatalogQualitySummary,
) -> list[str]:
    failures: list[str] = []
    if summary.place_count < summary.minimum_place_count:
        failures.append("place_count_below_minimum")
    if summary.alias_count < summary.minimum_alias_count:
        failures.append("alias_count_below_minimum")
    if summary.duplicate_place_id_count:
        failures.append("duplicate_place_id")
    if summary.duplicate_canonical_name_count:
        failures.append("duplicate_canonical_name")
    if summary.duplicate_alias_count:
        failures.append("duplicate_alias")
    if summary.unknown_related_place_count:
        failures.append("unknown_related_place")
    if summary.self_relation_count:
        failures.append("self_relation")
    if summary.place_without_relation_count:
        failures.append("place_without_relation")
    if summary.place_without_context_tag_count:
        failures.append("place_without_context_tag")
    if summary.public_false_count:
        failures.append("public_false")
    if summary.public_raw_text_leakage_count:
        failures.append("public_raw_text_leakage")
    if summary.private_path_leakage_count:
        failures.append("private_path_leakage")
    if summary.secret_like_leakage_count:
        failures.append("secret_like_leakage")
    return failures


def build_place_catalog_report_markdown(report: PlaceCatalogReport) -> str:
    summary = report.quality_summary
    category_rows = _dict_to_markdown_rows(report.place_count_by_category)
    alias_rows = _dict_to_markdown_rows(report.alias_count_by_language)
    relation_rows = _dict_to_markdown_rows(report.relation_count_by_type)
    qualitative_rows = "\n".join(
        f"- `{key}`: {value}" for key, value in report.qualitative_assessment.items()
    )
    return f"""# Place Catalog Validation Report

## 목적

서울/한양 관광 도슨트 RAG에서 사용할 장소 기준 catalog를 검증한다.

이 문서는 retrieval 성능 개선 주장이 아니다. query rewrite, place-aware retrieval, route-aware retrieval에서 참조할 public-safe seed 데이터의 무결성 기록이다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| catalog_version | `{report.catalog_version}` |
| generated_at_utc | `{report.generated_at_utc}` |
| catalog_path | `data_samples/place_catalog_seed.json` |

## 정량 리포트

| metric | value |
| --- | ---: |
| place_count | {summary.place_count} |
| alias_count | {summary.alias_count} |
| relation_count | {summary.relation_count} |
| minimum_place_count | {summary.minimum_place_count} |
| minimum_alias_count | {summary.minimum_alias_count} |
| duplicate_place_id_count | {summary.duplicate_place_id_count} |
| duplicate_canonical_name_count | {summary.duplicate_canonical_name_count} |
| duplicate_alias_count | {summary.duplicate_alias_count} |
| unknown_related_place_count | {summary.unknown_related_place_count} |
| self_relation_count | {summary.self_relation_count} |
| place_without_relation_count | {summary.place_without_relation_count} |
| place_without_context_tag_count | {summary.place_without_context_tag_count} |
| public_false_count | {summary.public_false_count} |
| public_raw_text_leakage_count | {summary.public_raw_text_leakage_count} |
| private_path_leakage_count | {summary.private_path_leakage_count} |
| secret_like_leakage_count | {summary.secret_like_leakage_count} |

## Category Breakdown

| category | count |
| --- | ---: |
{category_rows}

## Alias Language Breakdown

| language | count |
| --- | ---: |
{alias_rows}

## Relation Type Breakdown

| relation_type | count |
| --- | ---: |
{relation_rows}

## 정성 리포트

{qualitative_rows}

## 해석

place catalog는 원문 도서 내용을 복제하지 않는 수동 seed다.

이번 gate가 확인하는 것은 장소 ID, 별칭, 관계 target, public seed 정책의 기계적 무결성이다. 역사 설명문 생성 품질은 이후 citation RAG generation eval에서 별도로 측정한다.

허용 필드 내부의 임의 원문 유출은 길이와 줄바꿈 기반 휴리스틱으로 통제한다. 전체 원문 대조 감사는 parser/chunk private artifact 단계에서 별도로 수행한다.
"""


def _validate_place_id(value: str) -> str:
    if not _PLACE_ID_PATTERN.fullmatch(value):
        raise ValueError("place_id must use lowercase letters, digits, and hyphens")
    return value


def _validate_single_line(value: str, field_name: str) -> str:
    if "\n" in value or "\r" in value:
        raise ValueError(f"{field_name} must be a single-line public seed value")
    return value


def _count_duplicate_extra_values(values: list[str]) -> int:
    return sum(count - 1 for count in Counter(values).values() if count > 1)


def _normalize_alias(value: str) -> str:
    return " ".join(value.casefold().split())


def _collect_related_targets(catalog: PlaceCatalog) -> set[str]:
    targets: set[str] = set()
    for place in catalog.places:
        targets.update(place.related_place_ids)
        targets.update(relation.target_place_id for relation in place.relations)
    return targets


def _count_self_references(place: Place) -> int:
    related_self_count = sum(
        1 for target_place_id in place.related_place_ids if target_place_id == place.place_id
    )
    relation_self_count = sum(
        1 for relation in place.relations if relation.target_place_id == place.place_id
    )
    return related_self_count + relation_self_count


def _build_qualitative_assessment(
    summary: PlaceCatalogQualitySummary,
) -> dict[str, str]:
    return {
        "catalog_scope": (
            "경복궁, 광화문, 종묘, 창덕궁, 북촌, 한양도성, 남산, 덕수궁, 종로를 "
            "서울/한양 관광 도슨트의 초기 장소 기준으로 고정했다."
        ),
        "public_policy": (
            "원문 PDF, parser text, chunk text를 포함하지 않고 장소명, alias, 관계 ID만 공개한다."
        ),
        "gate_result": (
            "hard gate 통과"
            if not _collect_place_catalog_gate_failures_from_summary(summary)
            else "hard gate 실패"
        ),
        "retrieval_use": (
            "다음 단계에서 place-aware query rewrite와 retrieval failure analysis의 기준 dimension으로 사용한다."
        ),
    }


def _dict_to_markdown_rows(values: dict[str, int]) -> str:
    if not values:
        return "| none | 0 |"
    return "\n".join(f"| {key} | {value} |" for key, value in values.items())


def _count_forbidden_public_fields(payload: Any) -> int:
    if isinstance(payload, dict):
        count = sum(1 for key in payload if str(key) in FORBIDDEN_PUBLIC_PLACE_FIELDS)
        return count + sum(
            _count_forbidden_public_fields(value) for value in payload.values()
        )
    if isinstance(payload, list | tuple):
        return sum(_count_forbidden_public_fields(item) for item in payload)
    return 0


def _count_source_text_like_public_values(payload: Any) -> int:
    return sum(1 for value in _iter_string_values(payload) if _is_source_text_like(value))


def _is_source_text_like(value: str) -> bool:
    stripped = value.strip()
    return bool(
        ("\n" in stripped)
        or ("\r" in stripped)
        or len(stripped) > MAX_PUBLIC_STRING_LENGTH
    )


def _contains_private_path(value: str) -> bool:
    normalized = value.replace("/", "\\")
    return bool(
        _WINDOWS_PATH_PATTERN.search(normalized)
        or _POSIX_PRIVATE_PATH_PATTERN.search(value)
    )


def _contains_secret_like_value(value: str) -> bool:
    lowered = value.lower()
    return any(marker in lowered for marker in SECRET_VALUE_MARKERS)


def _iter_string_values(payload: Any) -> list[str]:
    if isinstance(payload, str):
        return [payload]
    if isinstance(payload, dict):
        values: list[str] = []
        for key, value in payload.items():
            values.extend(_iter_string_values(str(key)))
            values.extend(_iter_string_values(value))
        return values
    if isinstance(payload, list | tuple | set):
        values = []
        for item in payload:
            values.extend(_iter_string_values(item))
        return values
    return []
