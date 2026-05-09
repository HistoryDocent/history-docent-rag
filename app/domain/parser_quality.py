from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.data_contracts import NormalizedBlock
from app.domain.source_inventory import collect_private_path_leakage


PARSER_QUALITY_VERSION = "parser-quality/v1"
DEFAULT_SHORT_BLOCK_THRESHOLD = 20
DEFAULT_LONG_BLOCK_THRESHOLD = 1200


class ParserQualityModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ParserQualityInput(ParserQualityModel):
    normalized_blocks: list[NormalizedBlock]
    parser_page_count_by_doc: dict[str, int] = Field(default_factory=dict)
    private_roots: list[Path] = Field(default_factory=list)
    expected_document_count: int | None = Field(default=None, ge=0)
    short_block_threshold: int = DEFAULT_SHORT_BLOCK_THRESHOLD
    long_block_threshold: int = DEFAULT_LONG_BLOCK_THRESHOLD


class TextLengthStats(ParserQualityModel):
    min: int
    max: int
    mean: float
    p50: int
    p90: int
    p95: int


class ParserQualitySummary(ParserQualityModel):
    document_count: int
    expected_document_count: int | None = None
    normalized_block_count: int
    short_block_threshold: int
    long_block_threshold: int
    short_block_count: int
    long_block_count: int
    duplicate_text_hash_count: int
    duplicate_block_id_count: int
    replacement_char_block_count: int
    empty_element_refs_count: int
    invalid_page_range_count: int
    missing_provenance_count: int
    private_path_leakage_count: int


class ParserQualityReport(ParserQualityModel):
    report_version: str = PARSER_QUALITY_VERSION
    quality_summary: ParserQualitySummary
    block_count_by_doc: dict[str, int]
    block_count_by_element_type: dict[str, int]
    page_count_by_doc: dict[str, int]
    page_coverage_by_doc: dict[str, dict[str, int | None]]
    text_length_stats: TextLengthStats
    quality_warnings: list[str]

    def to_public_sample(self, *, max_documents: int = 5) -> dict[str, Any]:
        doc_items = list(self.block_count_by_doc.items())[:max_documents]
        selected_doc_ids = {doc_id for doc_id, _ in doc_items}
        return {
            "report_version": self.report_version,
            "source_root": "<private_path>",
            "quality_summary": self.quality_summary.model_dump(),
            "block_count_by_doc": dict(doc_items),
            "block_count_by_element_type": self.block_count_by_element_type,
            "page_count_by_doc": {
                doc_id: self.page_count_by_doc[doc_id]
                for doc_id in selected_doc_ids
                if doc_id in self.page_count_by_doc
            },
            "page_coverage_by_doc": {
                doc_id: self.page_coverage_by_doc[doc_id]
                for doc_id in selected_doc_ids
                if doc_id in self.page_coverage_by_doc
            },
            "text_length_stats": self.text_length_stats.model_dump(),
            "quality_warnings": self.quality_warnings,
            "data_policy": {
                "public_sample_contains_source_text": False,
                "public_sample_contains_private_paths": False,
                "full_source_data_storage": "private_data only",
            },
        }


def build_parser_quality_report(parser_input: ParserQualityInput) -> ParserQualityReport:
    blocks = parser_input.normalized_blocks
    block_count_by_doc = _count_by_doc(blocks)
    page_count_by_doc = _count_pages_by_doc(blocks)
    page_coverage = _build_page_coverage(
        blocks=blocks,
        parser_page_count_by_doc=parser_input.parser_page_count_by_doc,
    )
    text_lengths = [block.text_length for block in blocks]
    summary = _build_quality_summary(parser_input)
    quality_warnings = collect_parser_quality_gate_failures_from_summary(summary)

    return ParserQualityReport(
        quality_summary=summary,
        block_count_by_doc=block_count_by_doc,
        block_count_by_element_type=_count_by_element_type(blocks),
        page_count_by_doc=page_count_by_doc,
        page_coverage_by_doc=page_coverage,
        text_length_stats=_build_text_length_stats(text_lengths),
        quality_warnings=quality_warnings,
    )


def collect_parser_quality_gate_failures(report: ParserQualityReport) -> list[str]:
    return collect_parser_quality_gate_failures_from_summary(report.quality_summary)


def collect_parser_quality_gate_failures_from_summary(
    summary: ParserQualitySummary,
) -> list[str]:
    failures: list[str] = []
    if (
        summary.expected_document_count is not None
        and summary.document_count != summary.expected_document_count
    ):
        failures.append("document_count_mismatch")
    if summary.normalized_block_count == 0:
        failures.append("normalized_block_count_zero")
    if summary.duplicate_block_id_count:
        failures.append("duplicate_block_ids")
    if summary.invalid_page_range_count:
        failures.append("invalid_page_range")
    if summary.empty_element_refs_count:
        failures.append("empty_element_refs")
    if summary.missing_provenance_count:
        failures.append("missing_provenance")
    if summary.private_path_leakage_count:
        failures.append("private_path_leakage")
    return failures


def _build_quality_summary(parser_input: ParserQualityInput) -> ParserQualitySummary:
    blocks = parser_input.normalized_blocks
    block_ids = [block.block_id for block in blocks]
    text_hashes = [block.text_hash for block in blocks]
    private_path_leaks = collect_private_path_leakage(
        [block.model_dump() for block in blocks],
        parser_input.private_roots,
    )
    return ParserQualitySummary(
        document_count=len({block.doc_id for block in blocks}),
        expected_document_count=parser_input.expected_document_count,
        normalized_block_count=len(blocks),
        short_block_threshold=parser_input.short_block_threshold,
        long_block_threshold=parser_input.long_block_threshold,
        short_block_count=sum(
            1 for block in blocks if block.text_length < parser_input.short_block_threshold
        ),
        long_block_count=sum(
            1 for block in blocks if block.text_length > parser_input.long_block_threshold
        ),
        duplicate_text_hash_count=_duplicate_count(text_hashes),
        duplicate_block_id_count=_duplicate_count(block_ids),
        replacement_char_block_count=sum(
            1 for block in blocks if "replacement_character" in block.quality_flags
        ),
        empty_element_refs_count=sum(1 for block in blocks if not block.element_refs),
        invalid_page_range_count=sum(1 for block in blocks if _has_invalid_page_range(block)),
        missing_provenance_count=sum(1 for block in blocks if block.provenance is None),
        private_path_leakage_count=len(private_path_leaks),
    )


def _count_by_doc(blocks: list[NormalizedBlock]) -> dict[str, int]:
    return dict(sorted(Counter(block.doc_id for block in blocks).items()))


def _count_by_element_type(blocks: list[NormalizedBlock]) -> dict[str, int]:
    return dict(sorted(Counter(block.element_type for block in blocks).items()))


def _count_pages_by_doc(blocks: list[NormalizedBlock]) -> dict[str, int]:
    pages_by_doc: dict[str, set[int]] = defaultdict(set)
    for block in blocks:
        pages_by_doc[block.doc_id].add(block.page_span.page_local_start)
    return dict(sorted((doc_id, len(pages)) for doc_id, pages in pages_by_doc.items()))


def _build_page_coverage(
    *,
    blocks: list[NormalizedBlock],
    parser_page_count_by_doc: dict[str, int],
) -> dict[str, dict[str, int | None]]:
    pages_by_doc: dict[str, set[int]] = defaultdict(set)
    for block in blocks:
        pages_by_doc[block.doc_id].add(block.page_span.page_local_start)

    coverage: dict[str, dict[str, int | None]] = {}
    for doc_id in sorted(pages_by_doc.keys()):
        pages = pages_by_doc[doc_id]
        parser_page_count = parser_page_count_by_doc.get(doc_id)
        missing_page_count = (
            max(parser_page_count - len(pages), 0) if parser_page_count is not None else None
        )
        coverage[doc_id] = {
            "parser_page_count": parser_page_count,
            "covered_page_count": len(pages),
            "missing_page_count": missing_page_count,
            "min_page_local": min(pages) if pages else None,
            "max_page_local": max(pages) if pages else None,
        }
    return coverage


def _build_text_length_stats(text_lengths: list[int]) -> TextLengthStats:
    if not text_lengths:
        return TextLengthStats(min=0, max=0, mean=0.0, p50=0, p90=0, p95=0)

    sorted_lengths = sorted(text_lengths)
    return TextLengthStats(
        min=sorted_lengths[0],
        max=sorted_lengths[-1],
        mean=round(mean(sorted_lengths), 2),
        p50=_percentile(sorted_lengths, 0.5),
        p90=_percentile(sorted_lengths, 0.9),
        p95=_percentile(sorted_lengths, 0.95),
    )


def _percentile(sorted_values: list[int], percentile: float) -> int:
    if not sorted_values:
        return 0
    index = round((len(sorted_values) - 1) * percentile)
    return sorted_values[index]


def _duplicate_count(values: list[str]) -> int:
    return len(values) - len(set(values))


def _has_invalid_page_range(block: NormalizedBlock) -> bool:
    page_span = block.page_span
    return (
        page_span.page_local_end < page_span.page_local_start
        or (
            page_span.page_global_end is not None
            and page_span.page_global_end < page_span.page_global_start
        )
    )


def parser_quality_report_to_dict(report: ParserQualityReport) -> dict[str, Any]:
    return {
        "report_version": report.report_version,
        "quality_summary": report.quality_summary.model_dump(),
        "block_count_by_doc": report.block_count_by_doc,
        "block_count_by_element_type": report.block_count_by_element_type,
        "page_count_by_doc": report.page_count_by_doc,
        "page_coverage_by_doc": report.page_coverage_by_doc,
        "text_length_stats": report.text_length_stats.model_dump(),
        "quality_warnings": report.quality_warnings,
    }
