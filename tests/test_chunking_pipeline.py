from __future__ import annotations

import json
from pathlib import Path

from app.domain.chunking import collect_chunking_gate_failures
from app.domain.source_inventory import collect_private_path_leakage
from pipelines.build_parent_child_chunks import build_parent_child_chunks_from_files
from pipelines.build_parent_child_chunks import (
    _apply_public_leakage_metrics,
    _count_forbidden_public_sample_fields,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _block_payload(
    *,
    block_id: str,
    element_type: str,
    page: int,
    text_hash: str,
    text_length: int,
) -> dict[str, object]:
    return {
        "block_id": block_id,
        "doc_id": "doc-one",
        "doc_title": "Doc One",
        "parser_run_id": "upstage-parser-test",
        "element_type": element_type,
        "page_span": {
            "page_local_start": page,
            "page_local_end": page,
            "page_global_start": page,
            "page_global_end": page,
        },
        "element_refs": [
            {"element_id": block_id, "element_type": element_type, "element_index": 0}
        ],
        "text_hash": text_hash,
        "text_length": text_length,
        "provenance": {
            "source_file_name": "doc-one.pdf",
            "parser_artifact_path_alias": "PARSER_DIR/doc-one/document_analysis_results.json",
            "extraction_method": "upstage_parser",
        },
        "quality_flags": [],
        "public_allowed": False,
    }


def test_build_parent_child_chunks_from_files(tmp_path: Path) -> None:
    normalized_blocks_path = tmp_path / "normalized_blocks.json"
    _write_json(
        normalized_blocks_path,
        {
            "normalized_blocks": [
                _block_payload(
                    block_id="heading",
                    element_type="heading1",
                    page=0,
                    text_hash="a" * 64,
                    text_length=20,
                ),
                _block_payload(
                    block_id="body-one",
                    element_type="paragraph",
                    page=0,
                    text_hash="b" * 64,
                    text_length=320,
                ),
                _block_payload(
                    block_id="footer-one",
                    element_type="footer",
                    page=0,
                    text_hash="c" * 64,
                    text_length=10,
                ),
            ]
        },
    )

    result = build_parent_child_chunks_from_files(normalized_blocks_path=normalized_blocks_path)
    sample = result.report.to_public_sample(parents=result.parents, children=result.children)

    assert result.report.quality_summary.parent_chunk_count == 1
    assert result.report.quality_summary.child_chunk_count == 1
    assert result.report.quality_summary.retrievable_block_coverage == 1.0
    assert result.report.quality_summary.citation_recoverability == 1.0
    assert collect_chunking_gate_failures(result.report) == []
    assert collect_private_path_leakage(sample, [tmp_path]) == []
    assert "source_root" not in sample
    assert "child_ids" not in json.dumps(sample, ensure_ascii=False)


def test_public_sample_leakage_metrics_are_measured(tmp_path: Path) -> None:
    result = build_parent_child_chunks_from_files(
        normalized_blocks_path=_write_minimal_normalized_blocks(tmp_path)
    )
    unsafe_sample = {
        "child_chunks": [
            {
                "child_id": "child-one",
                "text": "raw text must be counted",
                "path": str(tmp_path),
            }
        ]
    }
    updated = _apply_public_leakage_metrics(
        result=result,
        public_sample=unsafe_sample,
        private_roots=[tmp_path],
        repo_root=tmp_path,
    )

    assert _count_forbidden_public_sample_fields(unsafe_sample) == 1
    assert updated.report.quality_summary.public_sample_raw_text_count == 1
    assert updated.report.quality_summary.public_sample_private_path_count == 1
    assert "public_sample_raw_text_count" in collect_chunking_gate_failures(updated.report)


def _write_minimal_normalized_blocks(tmp_path: Path) -> Path:
    normalized_blocks_path = tmp_path / "minimal_normalized_blocks.json"
    _write_json(
        normalized_blocks_path,
        {
            "normalized_blocks": [
                _block_payload(
                    block_id="heading",
                    element_type="heading1",
                    page=0,
                    text_hash="a" * 64,
                    text_length=20,
                ),
                _block_payload(
                    block_id="body-one",
                    element_type="paragraph",
                    page=0,
                    text_hash="b" * 64,
                    text_length=320,
                ),
            ]
        },
    )
    return normalized_blocks_path
