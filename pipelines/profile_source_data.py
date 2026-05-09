from __future__ import annotations

import argparse
from pathlib import Path

from app.domain.source_inventory import (
    SourceInventoryPaths,
    build_source_inventory_report,
    collect_private_path_leakage,
    write_json,
)


DEFAULT_PRIVATE_REPORT = Path("private_data/reports/source_inventory.json")
DEFAULT_PUBLIC_SAMPLE = Path("data_samples/source_inventory_sample.json")


def main() -> int:
    args = _parse_args()
    paths = _build_paths(args)

    report = build_source_inventory_report(paths)
    private_payload = report.to_private_report()
    public_payload = report.to_public_sample(max_documents=args.max_public_documents)

    write_json(args.private_report, private_payload)
    write_json(
        args.public_sample,
        public_payload,
        private_roots=[paths.source_root, paths.pdf_dir, paths.parser_dir],
        public_safe=True,
    )

    leaks = collect_private_path_leakage(public_payload, [paths.source_root])
    status = "PASS" if not leaks and not report.quality_warnings else "REVIEW"
    print(
        "source_inventory "
        f"status={status} "
        f"pdf_count={report.pdf_summary.pdf_count} "
        f"parser_documents={report.parser_summary.document_count} "
        f"document_analysis={report.parser_summary.document_analysis_count} "
        f"zero_byte_files={report.parser_summary.zero_byte_file_count} "
        f"warnings={len(report.quality_warnings)}"
    )
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Profile canonical HistoryDocent source data without exposing raw text."
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        required=True,
        help="Canonical source root containing 00_PDF_history and 01_Data_Preprocessing.",
    )
    parser.add_argument("--pdf-dir", type=Path, default=None)
    parser.add_argument("--parser-dir", type=Path, default=None)
    parser.add_argument("--legacy-chunk-file", type=Path, default=None)
    parser.add_argument("--private-report", type=Path, default=DEFAULT_PRIVATE_REPORT)
    parser.add_argument("--public-sample", type=Path, default=DEFAULT_PUBLIC_SAMPLE)
    parser.add_argument("--max-public-documents", type=int, default=3)
    return parser.parse_args()


def _build_paths(args: argparse.Namespace) -> SourceInventoryPaths:
    defaults = SourceInventoryPaths.from_source_root(args.source_root)
    return SourceInventoryPaths(
        source_root=args.source_root,
        pdf_dir=args.pdf_dir if args.pdf_dir is not None else defaults.pdf_dir,
        parser_dir=args.parser_dir if args.parser_dir is not None else defaults.parser_dir,
        legacy_chunk_file=(
            args.legacy_chunk_file
            if args.legacy_chunk_file is not None
            else defaults.legacy_chunk_file
        ),
    )


if __name__ == "__main__":
    raise SystemExit(main())
