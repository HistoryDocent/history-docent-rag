from __future__ import annotations

import json
from pathlib import Path

from app.domain.data_contracts import (
    BlockProvenance,
    ElementReference,
    NormalizedBlock,
    PageSpan,
)
from app.domain.parser_quality import (
    ParserQualityInput,
    build_parser_quality_report,
    collect_parser_quality_gate_failures,
)
from app.domain.source_inventory import collect_private_path_leakage, write_json


def _block(
    *,
    block_id: str,
    doc_id: str,
    element_type: str,
    page: int,
    text_hash: str,
    text_length: int,
    quality_flags: list[str] | None = None,
) -> NormalizedBlock:
    return NormalizedBlock(
        block_id=block_id,
        doc_id=doc_id,
        doc_title=doc_id,
        parser_run_id="upstage-parser-test",
        element_type=element_type,
        page_span=PageSpan(page_local_start=page, page_local_end=page, page_global_start=page),
        element_refs=[ElementReference(element_id=f"{block_id}-e", element_type=element_type)],
        text_hash=text_hash,
        text_length=text_length,
        provenance=BlockProvenance(
            source_file_name=f"{doc_id}.pdf",
            parser_artifact_path_alias=f"PARSER_DIR/{doc_id}/document_analysis_results.json",
            extraction_method="upstage_parser",
        ),
        quality_flags=quality_flags or [],
        public_allowed=False,
    )


def test_build_parser_quality_report_counts_core_metrics() -> None:
    blocks = [
        _block(
            block_id="block-1",
            doc_id="doc-one",
            element_type="paragraph",
            page=0,
            text_hash="a" * 64,
            text_length=10,
        ),
        _block(
            block_id="block-2",
            doc_id="doc-one",
            element_type="paragraph",
            page=1,
            text_hash="a" * 64,
            text_length=200,
            quality_flags=["replacement_character"],
        ),
        _block(
            block_id="block-3",
            doc_id="doc-two",
            element_type="table",
            page=0,
            text_hash="b" * 64,
            text_length=1400,
        ),
    ]
    report = build_parser_quality_report(
        ParserQualityInput(
            normalized_blocks=blocks,
            parser_page_count_by_doc={"doc-one": 3, "doc-two": 1},
        )
    )

    assert report.quality_summary.document_count == 2
    assert report.quality_summary.normalized_block_count == 3
    assert report.quality_summary.short_block_count == 1
    assert report.quality_summary.long_block_count == 1
    assert report.quality_summary.duplicate_text_hash_count == 1
    assert report.quality_summary.replacement_char_block_count == 1
    assert report.block_count_by_doc == {"doc-one": 2, "doc-two": 1}
    assert report.block_count_by_element_type == {"paragraph": 2, "table": 1}
    assert report.page_coverage_by_doc["doc-one"]["missing_page_count"] == 1
    assert collect_parser_quality_gate_failures(report) == []


def test_parser_quality_public_sample_is_redacted(tmp_path: Path) -> None:
    blocks = [
        _block(
            block_id="block-1",
            doc_id="doc-one",
            element_type="paragraph",
            page=0,
            text_hash="c" * 64,
            text_length=30,
        )
    ]
    report = build_parser_quality_report(ParserQualityInput(normalized_blocks=blocks))
    sample = report.to_public_sample(max_documents=1)
    serialized = json.dumps(sample, ensure_ascii=False)

    assert "raw_text" not in serialized
    assert str(tmp_path) not in serialized
    assert collect_private_path_leakage(sample, [tmp_path]) == []

    write_json(
        tmp_path / "parser_quality_sample.json",
        sample,
        private_roots=[tmp_path],
        public_safe=True,
    )
