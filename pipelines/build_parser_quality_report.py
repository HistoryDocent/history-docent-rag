from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.domain.data_contracts import NormalizedBlock
from app.domain.parser_quality import (
    ParserQualityInput,
    ParserQualityReport,
    build_parser_quality_report,
    collect_parser_quality_gate_failures,
    parser_quality_report_to_dict,
)
from app.domain.source_inventory import write_json


DEFAULT_NORMALIZED_BLOCKS_REPORT = (
    Path("private_data") / "reports" / "normalized_blocks.json"
)
DEFAULT_DATA_MANIFEST_REPORT = Path("private_data") / "reports" / "data_manifest.json"
DEFAULT_PRIVATE_REPORT = Path("private_data") / "reports" / "parser_quality_report.json"
DEFAULT_PUBLIC_SAMPLE = Path("data_samples/parser_quality_sample.json")


def build_parser_quality_report_from_files(
    *,
    normalized_blocks_path: Path = DEFAULT_NORMALIZED_BLOCKS_REPORT,
    data_manifest_path: Path = DEFAULT_DATA_MANIFEST_REPORT,
    expected_document_count: int | None = None,
) -> ParserQualityReport:
    normalized_blocks_payload = _load_json(normalized_blocks_path)
    manifest_payload = _load_json(data_manifest_path) if data_manifest_path.exists() else {}
    blocks = [
        NormalizedBlock.model_validate(block)
        for block in normalized_blocks_payload.get("normalized_blocks", [])
    ]
    page_count_by_doc = _extract_parser_page_count_by_doc(manifest_payload)
    return build_parser_quality_report(
        ParserQualityInput(
            normalized_blocks=blocks,
            parser_page_count_by_doc=page_count_by_doc,
            private_roots=[
                normalized_blocks_path.parent,
                data_manifest_path.parent,
            ],
            expected_document_count=expected_document_count,
        )
    )


def main() -> int:
    args = _parse_args()
    report = build_parser_quality_report_from_files(
        normalized_blocks_path=args.normalized_blocks_report,
        data_manifest_path=args.data_manifest_report,
        expected_document_count=args.expected_document_count,
    )
    private_payload = parser_quality_report_to_dict(report)
    public_payload = report.to_public_sample(max_documents=args.max_public_documents)

    private_roots = [
        args.normalized_blocks_report.parent,
        args.data_manifest_report.parent,
    ]
    write_json(args.private_report, private_payload)
    write_json(
        args.public_sample,
        public_payload,
        private_roots=private_roots,
        public_safe=True,
    )

    failures = collect_parser_quality_gate_failures(report)
    status = "PASS" if not failures else "FAIL"
    summary = report.quality_summary
    print(
        "parser_quality "
        f"status={status} "
        f"documents={summary.document_count} "
        f"blocks={summary.normalized_block_count} "
        f"short_blocks={summary.short_block_count} "
        f"long_blocks={summary.long_block_count} "
        f"duplicate_hashes={summary.duplicate_text_hash_count} "
        f"failures={len(failures)}"
    )
    return 0 if not failures else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build parser and NormalizedBlock quality metrics before chunking."
    )
    parser.add_argument(
        "--normalized-blocks-report",
        type=Path,
        default=DEFAULT_NORMALIZED_BLOCKS_REPORT,
    )
    parser.add_argument(
        "--data-manifest-report",
        type=Path,
        default=DEFAULT_DATA_MANIFEST_REPORT,
    )
    parser.add_argument("--private-report", type=Path, default=DEFAULT_PRIVATE_REPORT)
    parser.add_argument("--public-sample", type=Path, default=DEFAULT_PUBLIC_SAMPLE)
    parser.add_argument("--max-public-documents", type=int, default=5)
    parser.add_argument("--expected-document-count", type=int, default=12)
    return parser.parse_args()


def _extract_parser_page_count_by_doc(manifest_payload: dict[str, Any]) -> dict[str, int]:
    page_counts: dict[str, int] = {}
    for artifact in manifest_payload.get("parser_artifacts", []):
        if artifact.get("artifact_kind") != "document_analysis":
            continue
        doc_id = artifact.get("doc_id")
        page_count = artifact.get("page_count")
        if isinstance(doc_id, str) and isinstance(page_count, int):
            page_counts[doc_id] = page_count
    return page_counts


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
