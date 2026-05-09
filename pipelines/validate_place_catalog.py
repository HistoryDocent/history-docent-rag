from __future__ import annotations

import argparse
from pathlib import Path

from app.domain.place_catalog import (
    PlaceCatalogReport,
    build_place_catalog_report,
    build_place_catalog_report_markdown,
    collect_place_catalog_gate_failures,
    load_place_catalog,
)


DEFAULT_CATALOG_PATH = Path("data_samples/place_catalog_seed.json")
DEFAULT_REPORT_PATH = Path("evals/reports/place_catalog_validation_report.md")


def validate_place_catalog(
    *,
    catalog_path: Path = DEFAULT_CATALOG_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
) -> PlaceCatalogReport:
    catalog = load_place_catalog(catalog_path)
    report = build_place_catalog_report(catalog)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(build_place_catalog_report_markdown(report), encoding="utf-8")
    return report


def main() -> int:
    args = _parse_args()
    report = validate_place_catalog(
        catalog_path=args.catalog,
        report_path=args.report,
    )
    failures = collect_place_catalog_gate_failures(report)
    summary = report.quality_summary
    print(
        "place_catalog "
        f"status={'PASS' if not failures else 'FAIL'} "
        f"place_count={summary.place_count} "
        f"alias_count={summary.alias_count} "
        f"relation_count={summary.relation_count} "
        f"failures={len(failures)}"
    )
    return 0 if not failures else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate public place catalog seed.")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
