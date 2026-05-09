from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.domain.place_catalog import (
    PLACE_CATALOG_VERSION,
    Place,
    PlaceAlias,
    PlaceCatalog,
    PlaceRelation,
    build_place_catalog_report,
    collect_place_catalog_gate_failures,
    load_place_catalog,
)


def _place(
    place_id: str,
    canonical_name: str,
    *,
    aliases: list[str],
    related_place_ids: list[str] | None = None,
    relations: list[PlaceRelation] | None = None,
    tour_context_tags: list[str] | None = None,
) -> Place:
    return Place(
        place_id=place_id,
        canonical_name=canonical_name,
        category="palace",
        aliases=[
            PlaceAlias(alias=alias, language="ko", alias_type="alternative")
            for alias in aliases
        ],
        related_place_ids=related_place_ids or [],
        relations=relations or [],
        tour_context_tags=tour_context_tags or ["joseon"],
        source_policy="manual_public_seed",
        public_allowed=True,
    )


def test_place_catalog_seed_passes_gate() -> None:
    catalog = load_place_catalog(Path("data_samples/place_catalog_seed.json"))

    report = build_place_catalog_report(catalog)

    assert catalog.catalog_version == PLACE_CATALOG_VERSION
    assert report.quality_summary.place_count >= 8
    assert report.quality_summary.alias_count >= 20
    assert report.quality_summary.duplicate_place_id_count == 0
    assert report.quality_summary.duplicate_alias_count == 0
    assert report.quality_summary.unknown_related_place_count == 0
    assert report.quality_summary.self_relation_count == 0
    assert report.quality_summary.public_raw_text_leakage_count == 0
    assert report.quality_summary.private_path_leakage_count == 0
    assert report.quality_summary.secret_like_leakage_count == 0
    assert collect_place_catalog_gate_failures(report) == []


def test_place_catalog_schema_rejects_raw_text_field() -> None:
    with pytest.raises(ValidationError):
        PlaceCatalog.model_validate(
            {
                "catalog_version": PLACE_CATALOG_VERSION,
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
                        "tour_context_tags": ["joseon"],
                        "source_policy": "manual_public_seed",
                        "public_allowed": True,
                        "raw_text": "public repo에 들어가면 안 되는 필드",
                    }
                ],
            }
        )


def test_place_catalog_detects_duplicate_alias() -> None:
    catalog = PlaceCatalog(
        places=[
            _place("gyeongbokgung", "경복궁", aliases=["경복궁"]),
            _place("gwanghwamun", "광화문", aliases=["경복궁"]),
        ]
    )

    report = build_place_catalog_report(catalog)

    assert report.quality_summary.duplicate_alias_count == 1
    assert "duplicate_alias" in collect_place_catalog_gate_failures(report)


def test_place_catalog_detects_unknown_related_place() -> None:
    catalog = PlaceCatalog(
        places=[
            _place(
                "gyeongbokgung",
                "경복궁",
                aliases=["경복궁"],
                related_place_ids=["missing-place"],
                relations=[
                    PlaceRelation(
                        target_place_id="missing-place",
                        relation_type="route_neighbor",
                        rationale="동선 연결 대상이 catalog에 없다.",
                    )
                ],
            )
        ]
    )

    report = build_place_catalog_report(catalog)

    assert report.quality_summary.unknown_related_place_count == 1
    assert "unknown_related_place" in collect_place_catalog_gate_failures(report)


def test_place_catalog_detects_private_path_and_secret_like_values() -> None:
    private_path = "C:" + "\\private\\source.pdf"
    posix_private_path = "/" + "home/runner/work/private/source.pdf"
    marker_value = "api_" + "key=redacted"
    provider_marker = "ghp_" + "redacted"
    catalog = PlaceCatalog(
        places=[
            _place(
                "gyeongbokgung",
                "경복궁",
                aliases=["경복궁"],
                relations=[
                    PlaceRelation(
                        target_place_id="gyeongbokgung",
                        relation_type="historical_context",
                        rationale=f"{private_path} {marker_value}",
                    ),
                    PlaceRelation(
                        target_place_id="gyeongbokgung",
                        relation_type="nearby",
                        rationale=f"{posix_private_path} {provider_marker}",
                    )
                ],
            )
        ]
    )

    report = build_place_catalog_report(catalog)

    assert report.quality_summary.private_path_leakage_count == 2
    assert report.quality_summary.secret_like_leakage_count == 2
    assert "private_path_leakage" in collect_place_catalog_gate_failures(report)
    assert "secret_like_leakage" in collect_place_catalog_gate_failures(report)


@pytest.mark.parametrize(
    "marker_parts",
    [
        ("github", "_pat_", "redacted"),
        ("hf_", "redacted"),
        ("xoxb-", "redacted"),
        ("bear", "er ", "redacted"),
    ],
)
def test_place_catalog_detects_secret_like_marker_variants(
    marker_parts: tuple[str, ...],
) -> None:
    marker_value = "".join(marker_parts)
    catalog = PlaceCatalog(
        places=[
            _place(
                "gyeongbokgung",
                "경복궁",
                aliases=["경복궁"],
                relations=[
                    PlaceRelation(
                        target_place_id="gyeongbokgung",
                        relation_type="historical_context",
                        rationale=f"provider marker {marker_value}",
                    )
                ],
            )
        ]
    )

    report = build_place_catalog_report(catalog)

    assert report.quality_summary.secret_like_leakage_count == 1
    assert "secret_like_leakage" in collect_place_catalog_gate_failures(report)


def test_place_catalog_schema_rejects_source_like_public_values() -> None:
    with pytest.raises(ValidationError):
        PlaceRelation(
            target_place_id="gyeongbokgung",
            relation_type="historical_context",
            rationale="가" * 81,
        )
    with pytest.raises(ValidationError):
        PlaceAlias(alias="경복궁\n원문", language="ko", alias_type="primary")
    with pytest.raises(ValidationError):
        _place("gyeongbokgung", "경복궁", aliases=["경복궁"], tour_context_tags=["조선"])


def test_place_catalog_report_counts_source_like_public_values_defensively() -> None:
    relation = PlaceRelation.model_construct(
        target_place_id="gyeongbokgung",
        relation_type="historical_context",
        rationale="가" * 121,
    )
    place = Place.model_construct(
        place_id="gyeongbokgung",
        canonical_name="경복궁",
        category="palace",
        aliases=[
            PlaceAlias(alias="경복궁", language="ko", alias_type="primary"),
        ],
        related_place_ids=[],
        relations=[relation],
        tour_context_tags=["joseon"],
        source_policy="manual_public_seed",
        public_allowed=True,
    )
    catalog = PlaceCatalog.model_construct(
        catalog_version=PLACE_CATALOG_VERSION,
        places=[place],
    )

    report = build_place_catalog_report(catalog)

    assert report.quality_summary.public_raw_text_leakage_count == 1
    assert "public_raw_text_leakage" in collect_place_catalog_gate_failures(report)


def test_place_catalog_report_matches_seed_summary() -> None:
    catalog = load_place_catalog(Path("data_samples/place_catalog_seed.json"))
    report = build_place_catalog_report(catalog)
    summary = report.quality_summary
    report_text = Path("evals/reports/place_catalog_validation_report.md").read_text(
        encoding="utf-8"
    )

    expected_fragments = [
        *(f"| {key} | {value} |" for key, value in summary.model_dump().items()),
        *(
            f"| {key} | {value} |"
            for key, value in report.place_count_by_category.items()
        ),
        *(
            f"| {key} | {value} |"
            for key, value in report.alias_count_by_language.items()
        ),
        *(
            f"| {key} | {value} |"
            for key, value in report.relation_count_by_type.items()
        ),
        *(
            f"- `{key}`: {value}"
            for key, value in report.qualitative_assessment.items()
        ),
        *(place.canonical_name for place in catalog.places),
    ]

    assert [fragment for fragment in expected_fragments if fragment not in report_text] == []


def test_place_catalog_public_artifacts_do_not_include_private_text_or_paths() -> None:
    public_paths = [
        Path("data_samples/place_catalog_seed.json"),
        Path("evals/reports/place_catalog_validation_report.md"),
        Path("docs/PLACE_CATALOG.md"),
        Path("notebooks/05_place_catalog_validation.ipynb"),
    ]
    public_text = "\n".join(path.read_text(encoding="utf-8") for path in public_paths)

    assert '"raw_text"' not in public_text
    assert '"source_text"' not in public_text
    assert '"context_text"' not in public_text
    assert '"search_text"' not in public_text
    assert "F:" not in public_text
    assert "C:" not in public_text
    assert "/home/" not in public_text
    assert "ghp_" not in public_text
    assert "\\\\" not in public_text
