from __future__ import annotations

import hashlib
import html
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.domain.data_contracts import (
    BlockProvenance,
    ElementReference,
    NormalizedBlock,
    PageSpan,
)
from app.domain.source_inventory import collect_private_path_leakage


NORMALIZED_BLOCKS_VERSION = "normalized-blocks/v1"


@dataclass(frozen=True)
class NormalizationInput:
    doc_id: str
    doc_title: str
    source_file_name: str
    parser_run_id: str
    parser_artifact_path_alias: str
    analysis_path: Path
    page_global_offset: int = 0


@dataclass(frozen=True)
class NormalizationQualitySummary:
    document_count: int
    normalized_block_count: int
    skipped_empty_text_element_count: int
    duplicate_block_id_count: int
    negative_page_global_count: int
    invalid_page_range_count: int
    empty_element_refs_count: int
    missing_text_hash_count: int
    negative_text_length_count: int
    private_path_leakage_count: int


def build_normalized_blocks_from_analysis(
    normalization_input: NormalizationInput,
) -> tuple[list[NormalizedBlock], NormalizationQualitySummary]:
    payload = _load_json(normalization_input.analysis_path)
    page_elements = payload.get("page_elements") if isinstance(payload, dict) else None
    if not isinstance(page_elements, dict):
        return [], _build_quality_summary(
            document_count=1,
            blocks=[],
            skipped_empty_text_element_count=0,
            private_roots=[normalization_input.analysis_path.parent],
        )

    blocks: list[NormalizedBlock] = []
    skipped_empty_text = 0
    for page_key in sorted(page_elements.keys(), key=_page_sort_key):
        page_payload = page_elements.get(page_key)
        if not isinstance(page_payload, dict):
            continue
        page_local = _coerce_page_number(page_key)
        page_global = normalization_input.page_global_offset + page_local
        for group_name in ("text_elements", "table_elements"):
            group = page_payload.get(group_name)
            if not isinstance(group, list):
                continue
            for element_index, element in enumerate(group):
                if not isinstance(element, dict):
                    continue
                text = _extract_element_text(element)
                if not text:
                    skipped_empty_text += 1
                    continue
                blocks.append(
                    _build_block(
                        normalization_input=normalization_input,
                        element=element,
                        element_index=element_index,
                        group_name=group_name,
                        page_local=page_local,
                        page_global=page_global,
                        text=text,
                    )
                )

    summary = _build_quality_summary(
        document_count=1,
        blocks=blocks,
        skipped_empty_text_element_count=skipped_empty_text,
        private_roots=[normalization_input.analysis_path.parent],
    )
    return blocks, summary


def build_normalized_blocks_sample(
    blocks: list[NormalizedBlock],
    quality_summary: NormalizationQualitySummary | dict[str, Any],
    *,
    max_blocks: int = 3,
) -> dict[str, Any]:
    summary_payload = (
        asdict(quality_summary)
        if isinstance(quality_summary, NormalizationQualitySummary)
        else quality_summary
    )
    return {
        "report_version": NORMALIZED_BLOCKS_VERSION,
        "source_root": "<private_path>",
        "normalized_blocks": [block.to_public_sample() for block in blocks[:max_blocks]],
        "quality_summary": summary_payload,
        "data_policy": {
            "public_sample_contains_source_text": False,
            "public_sample_contains_private_paths": False,
            "full_source_data_storage": "private_data only",
        },
    }


def collect_normalized_block_gate_failures(
    blocks: list[NormalizedBlock],
    quality_summary: NormalizationQualitySummary | dict[str, Any],
) -> list[str]:
    summary = (
        asdict(quality_summary)
        if isinstance(quality_summary, NormalizationQualitySummary)
        else quality_summary
    )
    failures: list[str] = []
    if not blocks:
        failures.append("normalized_block_count_zero")
    if summary.get("duplicate_block_id_count", 0):
        failures.append("duplicate_block_ids")
    if summary.get("negative_page_global_count", 0):
        failures.append("negative_page_global")
    if summary.get("invalid_page_range_count", 0):
        failures.append("invalid_page_range")
    if summary.get("empty_element_refs_count", 0):
        failures.append("empty_element_refs")
    if summary.get("missing_text_hash_count", 0):
        failures.append("missing_text_hash")
    if summary.get("negative_text_length_count", 0):
        failures.append("negative_text_length")
    if summary.get("private_path_leakage_count", 0):
        failures.append("private_path_leakage")
    return failures


def _build_block(
    *,
    normalization_input: NormalizationInput,
    element: dict[str, Any],
    element_index: int,
    group_name: str,
    page_local: int,
    page_global: int,
    text: str,
) -> NormalizedBlock:
    element_id = str(element.get("id", f"{page_local}-{group_name}-{element_index}"))
    element_type = _resolve_element_type(element, group_name)
    quality_flags = _build_quality_flags(element, text)
    return NormalizedBlock(
        block_id=_build_block_id(
            doc_id=normalization_input.doc_id,
            page_global=page_global,
            element_type=element_type,
            element_id=element_id,
        ),
        doc_id=normalization_input.doc_id,
        doc_title=normalization_input.doc_title,
        parser_run_id=normalization_input.parser_run_id,
        element_type=element_type,
        page_span=PageSpan(
            page_local_start=page_local,
            page_local_end=page_local,
            page_global_start=page_global,
            page_global_end=page_global,
        ),
        element_refs=[
            ElementReference(
                element_id=element_id,
                element_type=element_type,
                element_index=element_index,
            )
        ],
        text_hash=_hash_text(text),
        text_length=len(text),
        provenance=BlockProvenance(
            source_file_name=normalization_input.source_file_name,
            parser_artifact_path_alias=normalization_input.parser_artifact_path_alias,
            extraction_method="upstage_parser",
        ),
        quality_flags=quality_flags,
        public_allowed=False,
    )


def _build_quality_summary(
    *,
    document_count: int,
    blocks: list[NormalizedBlock],
    skipped_empty_text_element_count: int,
    private_roots: list[Path],
) -> NormalizationQualitySummary:
    block_ids = [block.block_id for block in blocks]
    duplicate_block_id_count = len(block_ids) - len(set(block_ids))
    negative_page_global_count = sum(
        1 for block in blocks if block.page_span.page_global_start < 0
    )
    invalid_page_range_count = sum(
        1
        for block in blocks
        if block.page_span.page_local_end < block.page_span.page_local_start
        or (
            block.page_span.page_global_end is not None
            and block.page_span.page_global_end < block.page_span.page_global_start
        )
    )
    empty_element_refs_count = sum(1 for block in blocks if not block.element_refs)
    missing_text_hash_count = sum(1 for block in blocks if not block.text_hash)
    negative_text_length_count = sum(1 for block in blocks if block.text_length < 0)
    private_path_leaks = collect_private_path_leakage(
        [block.model_dump() for block in blocks],
        private_roots,
    )

    return NormalizationQualitySummary(
        document_count=document_count,
        normalized_block_count=len(blocks),
        skipped_empty_text_element_count=skipped_empty_text_element_count,
        duplicate_block_id_count=duplicate_block_id_count,
        negative_page_global_count=negative_page_global_count,
        invalid_page_range_count=invalid_page_range_count,
        empty_element_refs_count=empty_element_refs_count,
        missing_text_hash_count=missing_text_hash_count,
        negative_text_length_count=negative_text_length_count,
        private_path_leakage_count=len(private_path_leaks),
    )


def _extract_element_text(element: dict[str, Any]) -> str:
    content = element.get("content")
    candidates: list[Any] = []
    if isinstance(content, dict):
        candidates.extend([content.get("text"), content.get("markdown"), content.get("html")])
    elif isinstance(content, str):
        candidates.append(content)

    for candidate in candidates:
        if isinstance(candidate, str):
            normalized = _normalize_text(_strip_html(candidate))
            if normalized:
                return normalized
    return ""


def _strip_html(text: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", text)
    return html.unescape(without_tags)


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _resolve_element_type(element: dict[str, Any], group_name: str) -> str:
    category = element.get("category")
    if isinstance(category, str) and category.strip():
        return category.strip().lower()
    if group_name == "table_elements":
        return "table"
    return "text"


def _build_quality_flags(element: dict[str, Any], text: str) -> list[str]:
    flags: list[str] = []
    if "id" not in element:
        flags.append("missing_element_id")
    if "�" in text:
        flags.append("replacement_character")
    if not element.get("category"):
        flags.append("missing_category")
    return flags


def _build_block_id(
    *,
    doc_id: str,
    page_global: int,
    element_type: str,
    element_id: str,
) -> str:
    safe_doc_id = _slugify(doc_id)
    safe_type = _slugify(element_type)
    safe_element_id = _slugify(element_id)
    return f"block-{safe_doc_id}-{page_global:06d}-{safe_type}-{safe_element_id}"


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _coerce_page_number(value: str) -> int:
    try:
        return int(value)
    except ValueError:
        match = re.search(r"\d+", value)
        return int(match.group(0)) if match else 0


def _page_sort_key(value: str) -> tuple[int, str]:
    return (_coerce_page_number(value), value)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^0-9A-Za-z가-힣]+", "-", value).strip("-")
    return slug.lower() or "unknown"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))
