from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.data_contracts import ElementReference, NormalizedBlock, PageSpan
from app.domain.source_inventory import collect_private_path_leakage


CHUNKING_REPORT_VERSION = "chunking-quality/v1"


class ChunkingModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ChunkSourceRef(ChunkingModel):
    block_id: str = Field(min_length=1)
    doc_id: str = Field(min_length=1)
    element_type: str = Field(min_length=1)
    page_span: PageSpan
    element_refs: list[ElementReference] = Field(min_length=1)
    source_file_name: str = Field(min_length=1)
    text_hash: str = Field(min_length=32)
    text_length: int = Field(ge=0)
    quality_flags: list[str] = Field(default_factory=list)


class ParentChunk(ChunkingModel):
    parent_id: str = Field(min_length=1)
    doc_id: str = Field(min_length=1)
    doc_title: str = Field(min_length=1)
    parser_run_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    heading_block_id: str | None = None
    source_block_ids: list[str] = Field(min_length=1)
    page_span: PageSpan
    child_ids: list[str] = Field(default_factory=list)
    text_length: int = Field(ge=0)
    quality_flags: list[str] = Field(default_factory=list)
    public_allowed: bool = False


class ChildChunk(ChunkingModel):
    child_id: str = Field(min_length=1)
    parent_id: str = Field(min_length=1)
    doc_id: str = Field(min_length=1)
    doc_title: str = Field(min_length=1)
    parser_run_id: str = Field(min_length=1)
    source_block_ids: list[str] = Field(min_length=1)
    context_block_ids: list[str] = Field(default_factory=list)
    page_span: PageSpan
    text_hash: str = Field(min_length=32)
    text_length: int = Field(ge=0)
    element_type_mix: dict[str, int]
    citation_refs: list[ChunkSourceRef] = Field(min_length=1)
    quality_flags: list[str] = Field(default_factory=list)
    public_allowed: bool = False
    text: str | None = None
    context_text: str | None = None

    @model_validator(mode="after")
    def validate_citation_refs_cover_sources(self) -> "ChildChunk":
        ref_ids = [ref.block_id for ref in self.citation_refs]
        missing = [block_id for block_id in self.source_block_ids if block_id not in ref_ids]
        if missing:
            raise ValueError("citation_refs must cover source_block_ids")
        return self

    def to_public_sample(self) -> dict[str, Any]:
        return {
            "child_id": self.child_id,
            "parent_id": self.parent_id,
            "doc_id": self.doc_id,
            "doc_title": self.doc_title,
            "source_block_ids": self.source_block_ids,
            "page_span": self.page_span.model_dump(),
            "text_hash": self.text_hash,
            "text_length": self.text_length,
            "element_type_mix": self.element_type_mix,
            "quality_flags": self.quality_flags,
            "public_allowed": self.public_allowed,
        }


class ChunkingPolicy(ChunkingModel):
    boundary_element_types: set[str] = Field(default_factory=lambda: {"heading1"})
    context_metadata_element_types: set[str] = Field(default_factory=lambda: {"heading1"})
    excluded_from_retrieval_element_types: set[str] = Field(
        default_factory=lambda: {"header", "footer"}
    )
    front_matter_parent_title: str = "front_matter"
    parent_soft_max_chars: int = Field(default=6000, ge=1)
    merge_micro_parent_candidates: bool = False
    micro_parent_merge_max_chars: int = Field(default=250, ge=1)
    child_min_chars: int = Field(default=250, ge=1)
    child_target_chars: int = Field(default=700, ge=1)
    child_max_chars: int = Field(default=1100, ge=1)
    child_overlap_blocks: int = Field(default=1, ge=0)
    short_block_threshold_chars: int = Field(default=20, ge=0)
    minimum_citation_recoverability: float = Field(default=1.0, ge=0.0, le=1.0)
    minimum_retrievable_block_coverage: float = Field(default=1.0, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_child_lengths(self) -> "ChunkingPolicy":
        if self.child_target_chars > self.child_max_chars:
            raise ValueError("child_target_chars must be <= child_max_chars")
        if self.child_min_chars > self.child_max_chars:
            raise ValueError("child_min_chars must be <= child_max_chars")
        return self


class ChunkingQualitySummary(ChunkingModel):
    source_block_count: int = Field(ge=0)
    retrievable_block_count: int = Field(ge=0)
    covered_retrievable_block_count: int = Field(ge=0)
    parent_chunk_count: int = Field(ge=0)
    child_chunk_count: int = Field(ge=0)
    filtered_parent_count: int = Field(ge=0)
    duplicate_parent_id_count: int = Field(ge=0)
    duplicate_child_id_count: int = Field(ge=0)
    orphan_child_count: int = Field(ge=0)
    parent_without_child_count: int = Field(ge=0)
    empty_child_count: int = Field(ge=0)
    missing_source_block_ref_count: int = Field(ge=0)
    unknown_element_ref_count: int = Field(ge=0)
    invalid_page_range_count: int = Field(ge=0)
    cross_document_parent_count: int = Field(ge=0)
    cross_document_child_count: int = Field(ge=0)
    header_footer_retrieval_child_count: int = Field(ge=0)
    table_provenance_loss_count: int = Field(ge=0)
    private_path_leakage_count: int = Field(ge=0)
    public_sample_raw_text_count: int = Field(ge=0)
    public_sample_private_path_count: int = Field(ge=0)
    public_candidate_path_secret_leakage_count: int = Field(ge=0)
    citation_recoverability: float = Field(ge=0.0, le=1.0)
    retrievable_block_coverage: float = Field(ge=0.0, le=1.0)
    child_length_p50: int = Field(ge=0)
    child_length_p95: int = Field(ge=0)
    parent_length_p50: int = Field(ge=0)
    parent_length_p95: int = Field(ge=0)
    micro_parent_count: int = Field(ge=0)
    short_standalone_child_count: int = Field(ge=0)
    replacement_char_child_rate: float = Field(ge=0.0, le=1.0)
    duplicate_child_text_hash_count: int = Field(ge=0)


class ChunkingQualityReport(ChunkingModel):
    report_version: str = CHUNKING_REPORT_VERSION
    chunking_run_id: str
    policy: dict[str, Any]
    quality_summary: ChunkingQualitySummary
    parent_count_by_doc: dict[str, int]
    child_count_by_doc: dict[str, int]
    child_count_by_element_type: dict[str, int]
    quality_warnings: list[str]
    qualitative_assessment: dict[str, str]

    def to_public_sample(
        self,
        *,
        parents: list[ParentChunk],
        children: list[ChildChunk],
        max_parents: int = 3,
        max_children: int = 5,
    ) -> dict[str, Any]:
        return {
            "report_version": self.report_version,
            "chunking_run_id": self.chunking_run_id,
            "quality_summary": self.quality_summary.model_dump(),
            "parent_chunks": [
                _parent_to_public_sample(parent) for parent in parents[:max_parents]
            ],
            "child_chunks": [
                child.to_public_sample() for child in children[:max_children]
            ],
            "parent_count_by_doc": self.parent_count_by_doc,
            "child_count_by_doc": self.child_count_by_doc,
            "child_count_by_element_type": self.child_count_by_element_type,
            "quality_warnings": self.quality_warnings,
            "qualitative_assessment": self.qualitative_assessment,
            "data_policy": {
                "public_sample_contains_source_text": False,
                "public_sample_contains_private_paths": False,
                "full_source_data_storage": "private_data only",
            },
        }


class ParentChildChunkingResult(ChunkingModel):
    parents: list[ParentChunk]
    children: list[ChildChunk]
    report: ChunkingQualityReport


def build_parent_child_chunks(
    *,
    blocks: list[NormalizedBlock],
    policy: ChunkingPolicy | None = None,
    block_text_by_id: Mapping[str, str] | None = None,
    private_roots: list[Any] | None = None,
    public_sample_raw_text_count: int = 0,
    public_sample_private_path_count: int = 0,
    public_candidate_path_secret_leakage_count: int = 0,
) -> ParentChildChunkingResult:
    chunking_policy = policy or ChunkingPolicy()
    ordered_blocks = list(blocks)
    block_texts = block_text_by_id or {}
    parent_candidates = _build_parent_candidates(
        ordered_blocks,
        chunking_policy,
        block_texts,
    )
    if chunking_policy.merge_micro_parent_candidates:
        parent_candidates = _merge_micro_parent_candidates(
            parent_candidates,
            chunking_policy,
        )
    parents: list[ParentChunk] = []
    children: list[ChildChunk] = []
    filtered_parent_count = 0

    for parent_index, candidate in enumerate(parent_candidates):
        for segment_index, segment in enumerate(_split_parent_candidate(candidate, chunking_policy)):
            retrievable_blocks = [
                block for block in segment.blocks if _is_retrievable(block, chunking_policy)
            ]
            if not retrievable_blocks:
                filtered_parent_count += 1
                continue

            parent_id = _build_parent_id(
                doc_id=segment.doc_id,
                parent_index=parent_index,
                segment_index=segment_index,
            )
            child_groups = _build_child_block_groups(retrievable_blocks, chunking_policy)
            parent_child_ids: list[str] = []
            for child_index, child_blocks in enumerate(child_groups):
                child_id = f"{parent_id}-child-{child_index:04d}"
                child = _build_child_chunk(
                    child_id=child_id,
                    parent_id=parent_id,
                    blocks=child_blocks,
                    context_blocks=[
                        block
                        for block in segment.blocks
                        if block.element_type in chunking_policy.context_metadata_element_types
                    ],
                    block_text_by_id=block_texts,
                )
                children.append(child)
                parent_child_ids.append(child.child_id)

            parents.append(
                _build_parent_chunk(
                    parent_id=parent_id,
                    candidate=segment,
                    child_ids=parent_child_ids,
                )
            )

    report = build_chunking_quality_report(
        blocks=ordered_blocks,
        parents=parents,
        children=children,
        policy=chunking_policy,
        filtered_parent_count=filtered_parent_count,
        private_roots=private_roots or [],
        public_sample_raw_text_count=public_sample_raw_text_count,
        public_sample_private_path_count=public_sample_private_path_count,
        public_candidate_path_secret_leakage_count=public_candidate_path_secret_leakage_count,
    )
    return ParentChildChunkingResult(parents=parents, children=children, report=report)


def build_chunking_quality_report(
    *,
    blocks: list[NormalizedBlock],
    parents: list[ParentChunk],
    children: list[ChildChunk],
    policy: ChunkingPolicy,
    filtered_parent_count: int = 0,
    private_roots: list[Any] | None = None,
    public_sample_raw_text_count: int = 0,
    public_sample_private_path_count: int = 0,
    public_candidate_path_secret_leakage_count: int = 0,
) -> ChunkingQualityReport:
    block_by_id = {block.block_id: block for block in blocks}
    retrievable_block_ids = {
        block.block_id for block in blocks if _is_retrievable(block, policy)
    }
    covered_retrievable_block_ids = {
        block_id
        for child in children
        for block_id in child.source_block_ids
        if block_id in retrievable_block_ids
    }
    recoverable_child_count = sum(
        1 for child in children if _is_citation_recoverable(child, block_by_id)
    )
    parent_ids = [parent.parent_id for parent in parents]
    child_ids = [child.child_id for child in children]
    child_lengths = [child.text_length for child in children]
    parent_lengths = [parent.text_length for parent in parents]
    private_payload = {
        "parents": [parent.model_dump() for parent in parents],
        "children": [child.model_dump() for child in children],
    }
    private_path_leakage_count = len(
        collect_private_path_leakage(private_payload, list(private_roots or []))
    )
    summary = ChunkingQualitySummary(
        source_block_count=len(blocks),
        retrievable_block_count=len(retrievable_block_ids),
        covered_retrievable_block_count=len(covered_retrievable_block_ids),
        parent_chunk_count=len(parents),
        child_chunk_count=len(children),
        filtered_parent_count=filtered_parent_count,
        duplicate_parent_id_count=_duplicate_count(parent_ids),
        duplicate_child_id_count=_duplicate_count(child_ids),
        orphan_child_count=sum(1 for child in children if child.parent_id not in set(parent_ids)),
        parent_without_child_count=sum(1 for parent in parents if not parent.child_ids),
        empty_child_count=sum(1 for child in children if not child.source_block_ids or child.text_length <= 0),
        missing_source_block_ref_count=sum(
            1
            for child in children
            for block_id in child.source_block_ids
            if block_id not in block_by_id
        ),
        unknown_element_ref_count=sum(
            1
            for child in children
            for citation_ref in child.citation_refs
            if not citation_ref.element_refs
        ),
        invalid_page_range_count=_count_invalid_page_ranges(parents, children, block_by_id),
        cross_document_parent_count=sum(
            1 for parent in parents if _count_source_docs(parent.source_block_ids, block_by_id) > 1
        ),
        cross_document_child_count=sum(
            1 for child in children if _count_source_docs(child.source_block_ids, block_by_id) > 1
        ),
        header_footer_retrieval_child_count=sum(
            1
            for child in children
            if any(
                (block_by_id[block_id].element_type in policy.excluded_from_retrieval_element_types)
                for block_id in child.source_block_ids
                if block_id in block_by_id
            )
        ),
        table_provenance_loss_count=_count_table_provenance_loss(blocks, children),
        private_path_leakage_count=private_path_leakage_count,
        public_sample_raw_text_count=public_sample_raw_text_count,
        public_sample_private_path_count=public_sample_private_path_count,
        public_candidate_path_secret_leakage_count=public_candidate_path_secret_leakage_count,
        citation_recoverability=_safe_ratio(recoverable_child_count, len(children)),
        retrievable_block_coverage=_safe_ratio(
            len(covered_retrievable_block_ids),
            len(retrievable_block_ids),
        ),
        child_length_p50=_percentile(child_lengths, 0.5),
        child_length_p95=_percentile(child_lengths, 0.95),
        parent_length_p50=_percentile(parent_lengths, 0.5),
        parent_length_p95=_percentile(parent_lengths, 0.95),
        micro_parent_count=sum(1 for length in parent_lengths if length < policy.child_min_chars),
        short_standalone_child_count=_count_short_standalone_children(children, policy),
        replacement_char_child_rate=_safe_ratio(
            sum(
                1
                for child in children
                if any("replacement_character" in ref.quality_flags for ref in child.citation_refs)
            ),
            len(children),
        ),
        duplicate_child_text_hash_count=_duplicate_count(
            [child.text_hash for child in children]
        ),
    )
    warnings = collect_chunking_gate_failures_from_summary(summary, policy)
    qualitative_assessment = _build_qualitative_assessment(summary, warnings)
    return ChunkingQualityReport(
        chunking_run_id=_build_chunking_run_id(blocks=blocks, policy=policy),
        policy=policy.model_dump(mode="json"),
        quality_summary=summary,
        parent_count_by_doc=_count_parents_by_doc(parents),
        child_count_by_doc=_count_children_by_doc(children),
        child_count_by_element_type=_count_children_by_element_type(children),
        quality_warnings=warnings,
        qualitative_assessment=qualitative_assessment,
    )


def collect_chunking_gate_failures(report: ChunkingQualityReport) -> list[str]:
    policy = ChunkingPolicy.model_validate(report.policy)
    return collect_chunking_gate_failures_from_summary(report.quality_summary, policy)


def collect_chunking_gate_failures_from_summary(
    summary: ChunkingQualitySummary,
    policy: ChunkingPolicy,
) -> list[str]:
    failures: list[str] = []
    hard_gate_fields = [
        "duplicate_parent_id_count",
        "duplicate_child_id_count",
        "orphan_child_count",
        "parent_without_child_count",
        "empty_child_count",
        "missing_source_block_ref_count",
        "unknown_element_ref_count",
        "invalid_page_range_count",
        "cross_document_parent_count",
        "cross_document_child_count",
        "header_footer_retrieval_child_count",
        "table_provenance_loss_count",
        "private_path_leakage_count",
        "public_sample_raw_text_count",
        "public_sample_private_path_count",
        "public_candidate_path_secret_leakage_count",
    ]
    payload = summary.model_dump()
    failures.extend(field for field in hard_gate_fields if payload[field])
    if summary.citation_recoverability < policy.minimum_citation_recoverability:
        failures.append("citation_recoverability_below_threshold")
    if summary.retrievable_block_coverage < policy.minimum_retrievable_block_coverage:
        failures.append("retrievable_block_coverage_below_threshold")
    if summary.child_length_p95 > policy.child_max_chars:
        failures.append("child_length_p95_above_max")
    if summary.short_standalone_child_count:
        failures.append("short_standalone_child")
    return failures


def chunking_report_to_dict(
    *,
    result: ParentChildChunkingResult,
    include_text: bool,
) -> dict[str, Any]:
    return {
        "report_version": result.report.report_version,
        "chunking_run_id": result.report.chunking_run_id,
        "policy": result.report.policy,
        "parents": [parent.model_dump() for parent in result.parents],
        "children": [
            child.model_dump(exclude_none=not include_text) for child in result.children
        ],
        "quality_summary": result.report.quality_summary.model_dump(),
        "parent_count_by_doc": result.report.parent_count_by_doc,
        "child_count_by_doc": result.report.child_count_by_doc,
        "child_count_by_element_type": result.report.child_count_by_element_type,
        "quality_warnings": result.report.quality_warnings,
        "qualitative_assessment": result.report.qualitative_assessment,
    }


class _ParentCandidate(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    doc_id: str
    doc_title: str
    parser_run_id: str
    title: str
    heading_block_id: str | None
    blocks: list[NormalizedBlock]


def _build_parent_candidates(
    blocks: list[NormalizedBlock],
    policy: ChunkingPolicy,
    block_text_by_id: Mapping[str, str],
) -> list[_ParentCandidate]:
    candidates: list[_ParentCandidate] = []
    blocks_by_doc: dict[str, list[NormalizedBlock]] = defaultdict(list)
    for block in blocks:
        blocks_by_doc[block.doc_id].append(block)

    for doc_blocks in blocks_by_doc.values():
        doc_blocks = sorted(doc_blocks, key=_block_sort_key)
        current_blocks: list[NormalizedBlock] = []
        current_title = policy.front_matter_parent_title
        current_heading_block_id: str | None = None
        for block in doc_blocks:
            if block.element_type in policy.boundary_element_types:
                if current_blocks:
                    candidates.append(
                        _candidate_from_blocks(
                            blocks=current_blocks,
                            title=current_title,
                            heading_block_id=current_heading_block_id,
                        )
                    )
                current_blocks = [block]
                current_title = block_text_by_id.get(block.block_id, f"heading:{block.block_id}")
                current_heading_block_id = block.block_id
                continue
            if not current_blocks:
                current_title = policy.front_matter_parent_title
                current_heading_block_id = None
            current_blocks.append(block)
        if current_blocks:
            candidates.append(
                _candidate_from_blocks(
                    blocks=current_blocks,
                    title=current_title,
                    heading_block_id=current_heading_block_id,
                )
            )
    return candidates


def _candidate_from_blocks(
    *,
    blocks: list[NormalizedBlock],
    title: str,
    heading_block_id: str | None,
) -> _ParentCandidate:
    first = blocks[0]
    return _ParentCandidate(
        doc_id=first.doc_id,
        doc_title=first.doc_title,
        parser_run_id=first.parser_run_id,
        title=title,
        heading_block_id=heading_block_id,
        blocks=blocks,
    )


def _merge_micro_parent_candidates(
    candidates: list[_ParentCandidate],
    policy: ChunkingPolicy,
) -> list[_ParentCandidate]:
    if not candidates:
        return []
    merged: list[_ParentCandidate] = []
    index = 0
    while index < len(candidates):
        candidate = candidates[index]
        if (
            _is_micro_parent_candidate(candidate, policy)
            and index + 1 < len(candidates)
            and _can_merge_parent_candidates(candidate, candidates[index + 1], policy)
        ):
            merged.append(
                _merge_parent_candidate_pair(candidate, candidates[index + 1])
            )
            index += 2
            continue
        if (
            _is_micro_parent_candidate(candidate, policy)
            and merged
            and _can_merge_parent_candidates(merged[-1], candidate, policy)
        ):
            previous = merged.pop()
            merged.append(_merge_parent_candidate_pair(previous, candidate))
            index += 1
            continue
        merged.append(candidate)
        index += 1
    return merged


def _is_micro_parent_candidate(
    candidate: _ParentCandidate,
    policy: ChunkingPolicy,
) -> bool:
    retrievable_length = _total_length(
        [block for block in candidate.blocks if _is_retrievable(block, policy)]
    )
    return 0 < retrievable_length < policy.micro_parent_merge_max_chars


def _can_merge_parent_candidates(
    left: _ParentCandidate,
    right: _ParentCandidate,
    policy: ChunkingPolicy,
) -> bool:
    return (
        left.doc_id == right.doc_id
        and _total_length([*left.blocks, *right.blocks]) <= policy.parent_soft_max_chars
    )


def _merge_parent_candidate_pair(
    left: _ParentCandidate,
    right: _ParentCandidate,
) -> _ParentCandidate:
    return _candidate_from_blocks(
        blocks=[*left.blocks, *right.blocks],
        title=left.title,
        heading_block_id=left.heading_block_id,
    )


def _split_parent_candidate(
    candidate: _ParentCandidate,
    policy: ChunkingPolicy,
) -> list[_ParentCandidate]:
    if _total_length(candidate.blocks) <= policy.parent_soft_max_chars:
        return [candidate]

    segments: list[_ParentCandidate] = []
    current: list[NormalizedBlock] = []
    for block in candidate.blocks:
        next_length = _total_length([*current, block])
        if (
            current
            and next_length > policy.parent_soft_max_chars
            and any(_is_retrievable(item, policy) for item in current)
        ):
            segments.append(
                _candidate_from_blocks(
                    blocks=current,
                    title=candidate.title,
                    heading_block_id=candidate.heading_block_id,
                )
            )
            current = []
        current.append(block)
    if current:
        segments.append(
            _candidate_from_blocks(
                blocks=current,
                title=candidate.title,
                heading_block_id=candidate.heading_block_id,
            )
        )
    return segments


def _build_child_block_groups(
    blocks: list[NormalizedBlock],
    policy: ChunkingPolicy,
) -> list[list[NormalizedBlock]]:
    groups: list[list[NormalizedBlock]] = []
    current: list[NormalizedBlock] = []
    last_emitted_ids: tuple[str, ...] = ()

    for index, block in enumerate(blocks):
        if (
            current
            and _total_length([*current, block]) > policy.child_max_chars
            and _total_length(current) >= policy.child_min_chars
        ):
            last_emitted_ids = _append_child_group(groups, current, last_emitted_ids)
            current = _overlap_blocks(current, policy.child_overlap_blocks)

        current.append(block)
        if _total_length(current) >= policy.child_target_chars and index < len(blocks) - 1:
            last_emitted_ids = _append_child_group(groups, current, last_emitted_ids)
            current = _overlap_blocks(current, policy.child_overlap_blocks)

    if current:
        if groups and _total_length(current) < policy.child_min_chars:
            merged = _dedupe_blocks([*groups[-1], *current])
            if _total_length(merged) <= policy.child_max_chars:
                groups[-1] = merged
            else:
                _append_child_group(groups, current, last_emitted_ids)
        else:
            _append_child_group(groups, current, last_emitted_ids)

    return groups


def _append_child_group(
    groups: list[list[NormalizedBlock]],
    group: list[NormalizedBlock],
    last_emitted_ids: tuple[str, ...],
) -> tuple[str, ...]:
    deduped = _dedupe_blocks(group)
    group_ids = tuple(block.block_id for block in deduped)
    if group_ids and group_ids != last_emitted_ids:
        groups.append(deduped)
        return group_ids
    return last_emitted_ids


def _overlap_blocks(blocks: list[NormalizedBlock], overlap_count: int) -> list[NormalizedBlock]:
    if overlap_count <= 0:
        return []
    return blocks[-overlap_count:]


def _build_parent_chunk(
    *,
    parent_id: str,
    candidate: _ParentCandidate,
    child_ids: list[str],
) -> ParentChunk:
    return ParentChunk(
        parent_id=parent_id,
        doc_id=candidate.doc_id,
        doc_title=candidate.doc_title,
        parser_run_id=candidate.parser_run_id,
        title=candidate.title,
        heading_block_id=candidate.heading_block_id,
        source_block_ids=[block.block_id for block in candidate.blocks],
        page_span=_merge_page_span(candidate.blocks),
        child_ids=child_ids,
        text_length=_total_length(candidate.blocks),
        quality_flags=_merge_quality_flags(candidate.blocks),
        public_allowed=False,
    )


def _build_child_chunk(
    *,
    child_id: str,
    parent_id: str,
    blocks: list[NormalizedBlock],
    context_blocks: list[NormalizedBlock],
    block_text_by_id: Mapping[str, str],
) -> ChildChunk:
    body_text = _join_child_text(blocks, block_text_by_id)
    context_text = _join_child_text(context_blocks, block_text_by_id)
    child_text = _join_context_and_body_text(context_text, body_text)
    canonical_blocks = [*context_blocks, *blocks]
    text_hash = _hash_text(
        "|".join(f"{block.text_hash}:{block.text_length}" for block in canonical_blocks)
    )
    quality_flags = _merge_quality_flags(blocks)
    if any(block.element_type == "table" for block in blocks):
        quality_flags.append("has_table")
    if child_text is None:
        quality_flags.append("missing_private_text")

    first = blocks[0]
    return ChildChunk(
        child_id=child_id,
        parent_id=parent_id,
        doc_id=first.doc_id,
        doc_title=first.doc_title,
        parser_run_id=first.parser_run_id,
        source_block_ids=[block.block_id for block in blocks],
        context_block_ids=[block.block_id for block in context_blocks],
        page_span=_merge_page_span(blocks),
        text_hash=text_hash,
        text_length=_total_length(canonical_blocks),
        element_type_mix=dict(sorted(Counter(block.element_type for block in blocks).items())),
        citation_refs=[_build_citation_ref(block) for block in blocks],
        quality_flags=quality_flags,
        public_allowed=False,
        text=child_text,
        context_text=context_text,
    )


def _build_citation_ref(block: NormalizedBlock) -> ChunkSourceRef:
    return ChunkSourceRef(
        block_id=block.block_id,
        doc_id=block.doc_id,
        element_type=block.element_type,
        page_span=block.page_span,
        element_refs=block.element_refs,
        source_file_name=block.provenance.source_file_name,
        text_hash=block.text_hash,
        text_length=block.text_length,
        quality_flags=block.quality_flags,
    )


def _join_child_text(
    blocks: list[NormalizedBlock],
    block_text_by_id: Mapping[str, str],
) -> str | None:
    if not block_text_by_id:
        return None
    text_parts = [block_text_by_id.get(block.block_id, "") for block in blocks]
    if any(not part for part in text_parts):
        return None
    return "\n".join(text_parts)


def _join_context_and_body_text(context_text: str | None, body_text: str | None) -> str | None:
    if body_text is None:
        return None
    if context_text:
        return f"{context_text}\n{body_text}"
    return body_text


def _is_retrievable(block: NormalizedBlock, policy: ChunkingPolicy) -> bool:
    return (
        block.text_length > 0
        and block.element_type not in policy.excluded_from_retrieval_element_types
        and block.element_type not in policy.context_metadata_element_types
    )


def _merge_page_span(blocks: list[NormalizedBlock]) -> PageSpan:
    page_global_ends = [
        block.page_span.page_global_end
        for block in blocks
        if block.page_span.page_global_end is not None
    ]
    return PageSpan(
        page_local_start=min(block.page_span.page_local_start for block in blocks),
        page_local_end=max(block.page_span.page_local_end for block in blocks),
        page_global_start=min(block.page_span.page_global_start for block in blocks),
        page_global_end=max(page_global_ends) if page_global_ends else None,
    )


def _total_length(blocks: list[NormalizedBlock]) -> int:
    return sum(block.text_length for block in blocks)


def _merge_quality_flags(blocks: list[NormalizedBlock]) -> list[str]:
    return sorted({flag for block in blocks for flag in block.quality_flags})


def _dedupe_blocks(blocks: list[NormalizedBlock]) -> list[NormalizedBlock]:
    seen: set[str] = set()
    deduped: list[NormalizedBlock] = []
    for block in blocks:
        if block.block_id in seen:
            continue
        deduped.append(block)
        seen.add(block.block_id)
    return deduped


def _is_citation_recoverable(
    child: ChildChunk,
    block_by_id: Mapping[str, NormalizedBlock],
) -> bool:
    for block_id in child.source_block_ids:
        block = block_by_id.get(block_id)
        if block is None:
            return False
        if not block.element_refs or not block.provenance.source_file_name:
            return False
        if not _page_span_covers(child.page_span, block.page_span):
            return False
    return True


def _page_span_covers(outer: PageSpan, inner: PageSpan) -> bool:
    outer_global_end = outer.page_global_end
    inner_global_end = inner.page_global_end
    return (
        outer.page_local_start <= inner.page_local_start
        and outer.page_local_end >= inner.page_local_end
        and outer.page_global_start <= inner.page_global_start
        and (
            outer_global_end is None
            or inner_global_end is None
            or outer_global_end >= inner_global_end
        )
    )


def _count_invalid_page_ranges(
    parents: list[ParentChunk],
    children: list[ChildChunk],
    block_by_id: Mapping[str, NormalizedBlock],
) -> int:
    count = 0
    for parent in parents:
        count += _count_invalid_chunk_page_range(
            page_span=parent.page_span,
            source_block_ids=parent.source_block_ids,
            block_by_id=block_by_id,
        )
    for child in children:
        count += _count_invalid_chunk_page_range(
            page_span=child.page_span,
            source_block_ids=child.source_block_ids,
            block_by_id=block_by_id,
        )
    return count


def _count_invalid_chunk_page_range(
    *,
    page_span: PageSpan,
    source_block_ids: list[str],
    block_by_id: Mapping[str, NormalizedBlock],
) -> int:
    if page_span.page_local_end < page_span.page_local_start:
        return 1
    if page_span.page_global_end is not None and page_span.page_global_end < page_span.page_global_start:
        return 1
    for block_id in source_block_ids:
        block = block_by_id.get(block_id)
        if block is not None and not _page_span_covers(page_span, block.page_span):
            return 1
    return 0


def _count_source_docs(
    source_block_ids: list[str],
    block_by_id: Mapping[str, NormalizedBlock],
) -> int:
    return len(
        {
            block_by_id[block_id].doc_id
            for block_id in source_block_ids
            if block_id in block_by_id
        }
    )


def _count_table_provenance_loss(
    blocks: list[NormalizedBlock],
    children: list[ChildChunk],
) -> int:
    table_block_ids = {block.block_id for block in blocks if block.element_type == "table"}
    cited_table_block_ids = {
        ref.block_id
        for child in children
        for ref in child.citation_refs
        if ref.element_type == "table"
    }
    return len(table_block_ids - cited_table_block_ids)


def _count_short_standalone_children(
    children: list[ChildChunk],
    policy: ChunkingPolicy,
) -> int:
    children_by_parent: dict[str, list[ChildChunk]] = defaultdict(list)
    for child in children:
        children_by_parent[child.parent_id].append(child)
    return sum(
        1
        for child in children
        if child.text_length < policy.child_min_chars
        and len(child.source_block_ids) == 1
        and len(children_by_parent[child.parent_id]) > 1
    )


def _count_parents_by_doc(parents: list[ParentChunk]) -> dict[str, int]:
    return dict(sorted(Counter(parent.doc_id for parent in parents).items()))


def _count_children_by_doc(children: list[ChildChunk]) -> dict[str, int]:
    return dict(sorted(Counter(child.doc_id for child in children).items()))


def _count_children_by_element_type(children: list[ChildChunk]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for child in children:
        counts.update(child.element_type_mix)
    return dict(sorted(counts.items()))


def _parent_to_public_sample(parent: ParentChunk) -> dict[str, Any]:
    return {
        "parent_id": parent.parent_id,
        "doc_id": parent.doc_id,
        "doc_title": parent.doc_title,
        "source_block_ids": parent.source_block_ids,
        "page_span": parent.page_span.model_dump(),
        "text_length": parent.text_length,
        "quality_flags": parent.quality_flags,
        "public_allowed": parent.public_allowed,
    }


def _build_parent_id(*, doc_id: str, parent_index: int, segment_index: int) -> str:
    return f"parent-{_slugify(doc_id)}-{parent_index:05d}-{segment_index:02d}"


def _block_sort_key(block: NormalizedBlock) -> tuple[int, int, int, str]:
    element_index = block.element_refs[0].element_index if block.element_refs else None
    return (
        block.page_span.page_global_start,
        block.page_span.page_local_start,
        element_index if element_index is not None else 0,
        block.block_id,
    )


def _build_chunking_run_id(*, blocks: list[NormalizedBlock], policy: ChunkingPolicy) -> str:
    digest = hashlib.sha256()
    for block in sorted(blocks, key=_block_sort_key):
        block_payload = _stable_json_payload(block.model_dump(mode="json"))
        digest.update(block_payload.encode("utf-8"))
    policy_payload = _stable_json_payload(policy.model_dump(mode="json", exclude_none=True))
    digest.update(policy_payload.encode("utf-8"))
    return f"chunking-{digest.hexdigest()[:12]}"


def _stable_json_payload(value: Any) -> str:
    return json.dumps(_normalize_for_stable_json(value), ensure_ascii=False, sort_keys=True)


def _normalize_for_stable_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _normalize_for_stable_json(item)
            for key, item in sorted(value.items(), key=lambda entry: str(entry[0]))
        }
    if isinstance(value, list):
        normalized_items = [_normalize_for_stable_json(item) for item in value]
        if all(isinstance(item, str | int | float | bool | type(None)) for item in normalized_items):
            return sorted(normalized_items, key=lambda item: str(item))
        return normalized_items
    return value


def _build_qualitative_assessment(
    summary: ChunkingQualitySummary,
    quality_warnings: list[str],
) -> dict[str, str]:
    gate_status = "PASS" if not quality_warnings else "FAIL"
    return {
        "parent_boundary_quality": (
            "heading1 기반 parent boundary를 사용했고 문서 경계를 넘지 않는다."
        ),
        "short_block_merge_quality": (
            f"short_standalone_child_count={summary.short_standalone_child_count}. "
            "짧은 block은 가능한 경우 인접 block과 병합했다."
        ),
        "table_provenance": (
            f"table_provenance_loss_count={summary.table_provenance_loss_count}. "
            "table block은 citation ref로 추적한다."
        ),
        "citation_recovery": (
            f"citation_recoverability={summary.citation_recoverability:.4f}. "
            "최종 citation은 NormalizedBlock 기준으로 복구한다."
        ),
        "remaining_risk": (
            "replacement character와 duplicate text hash는 retrieval 단계에서 실패 분석 항목으로 유지한다."
        ),
        "gate_status": gate_status,
    }


def _percentile(values: list[int], percentile: float) -> int:
    if not values:
        return 0
    sorted_values = sorted(values)
    index = round((len(sorted_values) - 1) * percentile)
    return sorted_values[index]


def _safe_ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 1.0
    return round(numerator / denominator, 6)


def _duplicate_count(values: list[str]) -> int:
    return len(values) - len(set(values))


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _slugify(value: str) -> str:
    import re

    slug = re.sub(r"[^0-9A-Za-z가-힣]+", "-", value).strip("-")
    return slug.lower() or "unknown"
