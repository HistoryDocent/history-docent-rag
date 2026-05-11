from __future__ import annotations

import argparse
from dataclasses import asdict
from pathlib import Path
from typing import Any

from app.domain.data_contracts import NormalizedBlock
from app.domain.normalization import (
    NormalizationInput,
    NormalizationQualitySummary,
    build_normalized_blocks_from_analysis,
    build_normalized_blocks_sample,
    collect_normalized_block_gate_failures,
)
from app.domain.source_inventory import write_json
from pipelines.build_data_manifest import build_data_manifest


DEFAULT_PRIVATE_REPORT = Path("private_data") / "reports" / "normalized_blocks.json"
DEFAULT_PUBLIC_SAMPLE = Path("data_samples/normalized_blocks_sample.json")


def build_normalized_blocks_report(source_root: str | Path) -> dict[str, Any]:
    root = Path(source_root)
    parser_dir = root / "01_Data_Preprocessing"
    manifest = build_data_manifest(root)
    parser_run_id = manifest.parser_runs[0].parser_run_id if manifest.parser_runs else "unknown"
    source_documents_by_id = {document.doc_id: document for document in manifest.source_documents}
    blocks: list[NormalizedBlock] = []
    skipped_empty_text = 0
    page_global_offset = 0
    document_count = 0

    for artifact in manifest.parser_artifacts:
        if artifact.artifact_kind != "document_analysis":
            continue
        source_document = source_documents_by_id.get(artifact.doc_id)
        if source_document is None:
            continue
        analysis_path = parser_dir / source_document.doc_title / "document_analysis_results.json"
        document_blocks, document_summary = build_normalized_blocks_from_analysis(
            NormalizationInput(
                doc_id=source_document.doc_id,
                doc_title=source_document.doc_title,
                source_file_name=source_document.source_file_name,
                parser_run_id=parser_run_id,
                parser_artifact_path_alias=artifact.parser_artifact_path_alias,
                analysis_path=analysis_path,
                page_global_offset=page_global_offset,
            )
        )
        blocks.extend(document_blocks)
        skipped_empty_text += document_summary.skipped_empty_text_element_count
        page_global_offset += artifact.page_count or _max_page_count(document_blocks)
        document_count += 1

    quality_summary = _build_aggregate_summary(
        document_count=document_count,
        blocks=blocks,
        skipped_empty_text_element_count=skipped_empty_text,
    )
    public_sample = build_normalized_blocks_sample(blocks, quality_summary)

    return {
        "report_version": "normalized-blocks/v1",
        "source_alias": manifest.source_alias,
        "parser_run_id": parser_run_id,
        "normalized_blocks": blocks,
        "quality_summary": asdict(quality_summary),
        "quality_warnings": collect_normalized_block_gate_failures(blocks, quality_summary),
        "public_sample": public_sample,
    }


def main() -> int:
    args = _parse_args()
    report = build_normalized_blocks_report(args.source_root)
    blocks: list[NormalizedBlock] = report["normalized_blocks"]
    quality_summary: dict[str, Any] = report["quality_summary"]
    public_sample = build_normalized_blocks_sample(
        blocks,
        quality_summary,
        max_blocks=args.max_public_blocks,
    )
    private_payload = {
        "report_version": report["report_version"],
        "source_alias": report["source_alias"],
        "parser_run_id": report["parser_run_id"],
        "normalized_blocks": [block.model_dump() for block in blocks],
        "quality_summary": quality_summary,
        "quality_warnings": report["quality_warnings"],
    }

    private_roots = [
        args.source_root,
        args.source_root / "00_PDF_history",
        args.source_root / "01_Data_Preprocessing",
    ]
    write_json(args.private_report, private_payload)
    write_json(
        args.public_sample,
        public_sample,
        private_roots=private_roots,
        public_safe=True,
    )

    failures = collect_normalized_block_gate_failures(blocks, quality_summary)
    status = "PASS" if not failures else "FAIL"
    print(
        "normalized_blocks "
        f"status={status} "
        f"documents={quality_summary['document_count']} "
        f"blocks={quality_summary['normalized_block_count']} "
        f"skipped_empty_text={quality_summary['skipped_empty_text_element_count']} "
        f"failures={len(failures)}"
    )
    return 0 if not failures else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build redaction-safe NormalizedBlock metadata from Upstage Parser output."
    )
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--private-report", type=Path, default=DEFAULT_PRIVATE_REPORT)
    parser.add_argument("--public-sample", type=Path, default=DEFAULT_PUBLIC_SAMPLE)
    parser.add_argument("--max-public-blocks", type=int, default=5)
    return parser.parse_args()


def _build_aggregate_summary(
    *,
    document_count: int,
    blocks: list[NormalizedBlock],
    skipped_empty_text_element_count: int,
) -> NormalizationQualitySummary:
    block_ids = [block.block_id for block in blocks]
    return NormalizationQualitySummary(
        document_count=document_count,
        normalized_block_count=len(blocks),
        skipped_empty_text_element_count=skipped_empty_text_element_count,
        duplicate_block_id_count=len(block_ids) - len(set(block_ids)),
        negative_page_global_count=sum(
            1 for block in blocks if block.page_span.page_global_start < 0
        ),
        invalid_page_range_count=sum(
            1
            for block in blocks
            if block.page_span.page_local_end < block.page_span.page_local_start
            or (
                block.page_span.page_global_end is not None
                and block.page_span.page_global_end < block.page_span.page_global_start
            )
        ),
        empty_element_refs_count=sum(1 for block in blocks if not block.element_refs),
        missing_text_hash_count=sum(1 for block in blocks if not block.text_hash),
        negative_text_length_count=sum(1 for block in blocks if block.text_length < 0),
        private_path_leakage_count=0,
    )


def _max_page_count(blocks: list[NormalizedBlock]) -> int:
    if not blocks:
        return 0
    return max(block.page_span.page_local_end for block in blocks) + 1


if __name__ == "__main__":
    raise SystemExit(main())
