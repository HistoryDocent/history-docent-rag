from __future__ import annotations

import json
from pathlib import Path

from app.domain.chunking import (
    ChunkingPolicy,
    build_parent_child_chunks,
    collect_chunking_gate_failures,
)
from app.domain.data_contracts import (
    BlockProvenance,
    ElementReference,
    NormalizedBlock,
    PageSpan,
)
from app.domain.source_inventory import collect_private_path_leakage, write_json


def _block(
    *,
    block_id: str,
    element_type: str,
    page: int,
    text_length: int,
    text_hash: str,
    quality_flags: list[str] | None = None,
) -> NormalizedBlock:
    return NormalizedBlock(
        block_id=block_id,
        doc_id="doc-one",
        doc_title="Doc One",
        parser_run_id="upstage-parser-test",
        element_type=element_type,
        page_span=PageSpan(page_local_start=page, page_local_end=page, page_global_start=page),
        element_refs=[
            ElementReference(
                element_id=f"{block_id}-e",
                element_type=element_type,
                element_index=0,
            )
        ],
        text_hash=text_hash,
        text_length=text_length,
        provenance=BlockProvenance(
            source_file_name="doc-one.pdf",
            parser_artifact_path_alias="PARSER_DIR/doc-one/document_analysis_results.json",
            extraction_method="upstage_parser",
        ),
        quality_flags=quality_flags or [],
        public_allowed=False,
    )


def test_build_parent_child_chunks_preserves_retrievable_coverage() -> None:
    blocks = [
        _block(block_id="b-heading", element_type="heading1", page=0, text_length=30, text_hash="a" * 64),
        _block(block_id="b-one", element_type="paragraph", page=0, text_length=200, text_hash="b" * 64),
        _block(block_id="b-footer", element_type="footer", page=0, text_length=10, text_hash="c" * 64),
        _block(block_id="b-two", element_type="paragraph", page=1, text_length=240, text_hash="d" * 64),
        _block(block_id="b-table", element_type="table", page=1, text_length=280, text_hash="e" * 64),
    ]
    text_by_id = {block.block_id: f"text for {block.block_id}" for block in blocks}

    result = build_parent_child_chunks(blocks=blocks, block_text_by_id=text_by_id)
    summary = result.report.quality_summary

    assert summary.parent_chunk_count == 1
    assert summary.child_chunk_count >= 1
    assert summary.retrievable_block_count == 3
    assert summary.covered_retrievable_block_count == 3
    assert summary.retrievable_block_coverage == 1.0
    assert summary.citation_recoverability == 1.0
    assert summary.header_footer_retrieval_child_count == 0
    assert summary.table_provenance_loss_count == 0
    assert collect_chunking_gate_failures(result.report) == []
    assert "b-footer" not in {
        block_id for child in result.children for block_id in child.source_block_ids
    }
    assert result.children[0].context_block_ids == ["b-heading"]
    assert result.children[0].context_text == "text for b-heading"
    assert result.children[0].text is not None
    assert result.children[0].text.startswith("text for b-heading")


def test_chunking_public_sample_is_redacted(tmp_path: Path) -> None:
    blocks = [
        _block(block_id="b-heading", element_type="heading1", page=0, text_length=30, text_hash="a" * 64),
        _block(block_id="b-one", element_type="paragraph", page=0, text_length=300, text_hash="b" * 64),
    ]
    result = build_parent_child_chunks(
        blocks=blocks,
        policy=ChunkingPolicy(child_min_chars=100, child_target_chars=200, child_max_chars=500),
        block_text_by_id={"b-heading": "secret heading", "b-one": "private source text"},
        private_roots=[tmp_path],
    )

    sample = result.report.to_public_sample(parents=result.parents, children=result.children)
    serialized = json.dumps(sample, ensure_ascii=False)

    assert "private source text" not in serialized
    assert '"text":' not in serialized
    assert collect_private_path_leakage(sample, [tmp_path]) == []

    write_json(
        tmp_path / "chunking_quality_sample.json",
        sample,
        private_roots=[tmp_path],
        public_safe=True,
    )


def test_chunking_sorts_blocks_by_page_before_parenting() -> None:
    blocks = [
        _block(block_id="body-two", element_type="paragraph", page=2, text_length=300, text_hash="d" * 64),
        _block(block_id="heading", element_type="heading1", page=0, text_length=30, text_hash="a" * 64),
        _block(block_id="body-one", element_type="paragraph", page=1, text_length=300, text_hash="b" * 64),
    ]

    result = build_parent_child_chunks(blocks=blocks)

    assert result.parents[0].source_block_ids == ["heading", "body-one", "body-two"]


def test_chunking_metrics_do_not_depend_on_private_text_recovery() -> None:
    blocks = [
        _block(block_id="heading", element_type="heading1", page=0, text_length=30, text_hash="a" * 64),
        _block(block_id="body-one", element_type="paragraph", page=0, text_length=300, text_hash="b" * 64),
        _block(block_id="body-two", element_type="paragraph", page=1, text_length=320, text_hash="c" * 64),
    ]

    metadata_only = build_parent_child_chunks(blocks=blocks)
    with_private_text = build_parent_child_chunks(
        blocks=blocks,
        block_text_by_id={
            "heading": "heading text",
            "body-one": "private body one",
            "body-two": "private body two",
        },
    )

    assert metadata_only.report.quality_summary == with_private_text.report.quality_summary
    assert metadata_only.children[0].text_hash == with_private_text.children[0].text_hash
    assert metadata_only.children[0].text_length == with_private_text.children[0].text_length
    assert metadata_only.children[0].text is None
    assert with_private_text.children[0].text is not None


def test_chunking_run_id_is_stable_for_set_based_policy_fields() -> None:
    blocks = [
        _block(block_id="heading", element_type="heading1", page=0, text_length=30, text_hash="a" * 64),
        _block(block_id="body-one", element_type="paragraph", page=0, text_length=300, text_hash="b" * 64),
    ]
    policy_one = ChunkingPolicy(
        boundary_element_types={"heading2", "heading1"},
        context_metadata_element_types={"heading2", "heading1"},
    )
    policy_two = ChunkingPolicy(
        boundary_element_types={"heading1", "heading2"},
        context_metadata_element_types={"heading1", "heading2"},
    )

    result_one = build_parent_child_chunks(blocks=blocks, policy=policy_one)
    result_two = build_parent_child_chunks(blocks=blocks, policy=policy_two)

    assert result_one.report.chunking_run_id == result_two.report.chunking_run_id


def test_chunking_run_id_is_stable_for_input_order() -> None:
    blocks = [
        _block(block_id="heading", element_type="heading1", page=0, text_length=30, text_hash="a" * 64),
        _block(block_id="body-one", element_type="paragraph", page=0, text_length=300, text_hash="b" * 64),
        _block(block_id="body-two", element_type="paragraph", page=1, text_length=320, text_hash="c" * 64),
    ]

    original = build_parent_child_chunks(blocks=blocks)
    shuffled = build_parent_child_chunks(blocks=[blocks[2], blocks[0], blocks[1]])

    assert original.report.chunking_run_id == shuffled.report.chunking_run_id
    assert original.report.quality_summary == shuffled.report.quality_summary


def test_chunking_run_id_changes_when_chunking_relevant_block_contract_changes() -> None:
    heading = _block(
        block_id="heading",
        element_type="heading1",
        page=0,
        text_length=30,
        text_hash="a" * 64,
    )
    body = _block(
        block_id="body-one",
        element_type="paragraph",
        page=0,
        text_length=300,
        text_hash="b" * 64,
    )
    changed_heading = heading.model_copy(update={"element_type": "paragraph"})

    original = build_parent_child_chunks(blocks=[heading, body])
    changed = build_parent_child_chunks(blocks=[changed_heading, body])

    assert original.report.chunking_run_id != changed.report.chunking_run_id


def test_micro_parent_merge_combines_short_heading_sections() -> None:
    blocks = [
        _block(
            block_id="heading-one",
            element_type="heading1",
            page=0,
            text_length=30,
            text_hash="a" * 64,
        ),
        _block(
            block_id="body-short",
            element_type="paragraph",
            page=1,
            text_length=120,
            text_hash="b" * 64,
        ),
        _block(
            block_id="heading-two",
            element_type="heading1",
            page=2,
            text_length=30,
            text_hash="c" * 64,
        ),
        _block(
            block_id="body-normal",
            element_type="paragraph",
            page=3,
            text_length=360,
            text_hash="d" * 64,
        ),
    ]

    baseline = build_parent_child_chunks(blocks=blocks)
    merged = build_parent_child_chunks(
        blocks=blocks,
        policy=ChunkingPolicy(merge_micro_parent_candidates=True),
    )

    assert baseline.report.quality_summary.parent_chunk_count == 2
    assert baseline.report.quality_summary.micro_parent_count == 1
    assert merged.report.quality_summary.parent_chunk_count == 1
    assert merged.report.quality_summary.micro_parent_count == 0
    assert merged.parents[0].source_block_ids == [
        "heading-one",
        "body-short",
        "heading-two",
        "body-normal",
    ]
