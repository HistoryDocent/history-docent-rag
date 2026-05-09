from __future__ import annotations

import json
from pathlib import Path

from app.domain.normalization import (
    NormalizationInput,
    build_normalized_blocks_from_analysis,
    build_normalized_blocks_sample,
    collect_normalized_block_gate_failures,
)
from app.domain.source_inventory import collect_private_path_leakage


def _write_analysis(path: Path) -> None:
    payload = {
        "page_elements": {
            "0": {
                "text_elements": [
                    {
                        "id": 10,
                        "category": "paragraph",
                        "page": 0,
                        "content": {
                            "text": "Raw text must not appear in the public sample.",
                            "markdown": "Raw text must not appear in the public sample.",
                        },
                    }
                ],
                "table_elements": [
                    {
                        "id": 11,
                        "category": "table",
                        "page": 0,
                        "content": {"markdown": "| a | b |", "text": ""},
                    }
                ],
                "image_elements": [
                    {
                        "id": 12,
                        "category": "figure",
                        "page": 0,
                        "content": {"text": "image text should be ignored"},
                    }
                ],
            },
            "1": {
                "text_elements": [
                    {
                        "id": 20,
                        "category": "heading1",
                        "page": 1,
                        "content": {"text": "Second page heading"},
                    }
                ],
                "table_elements": [],
                "image_elements": [],
            },
        }
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_build_normalized_blocks_from_analysis(tmp_path: Path) -> None:
    analysis_path = tmp_path / "document_analysis_results.json"
    _write_analysis(analysis_path)

    blocks, summary = build_normalized_blocks_from_analysis(
        NormalizationInput(
            doc_id="doc-one",
            doc_title="Doc One",
            source_file_name="doc-one.pdf",
            parser_run_id="upstage-parser-test",
            parser_artifact_path_alias="PARSER_DIR/doc-one/document_analysis_results.json",
            analysis_path=analysis_path,
            page_global_offset=100,
        )
    )

    assert len(blocks) == 3
    assert summary.normalized_block_count == 3
    assert summary.skipped_empty_text_element_count == 0
    assert blocks[0].block_id == "block-doc-one-000100-paragraph-10"
    assert blocks[0].page_span.page_local_start == 0
    assert blocks[0].page_span.page_global_start == 100
    assert blocks[0].element_refs[0].element_id == "10"
    assert blocks[1].element_type == "table"
    assert blocks[2].page_span.page_global_start == 101
    assert collect_normalized_block_gate_failures(blocks, summary) == []


def test_normalized_blocks_public_sample_is_redacted(tmp_path: Path) -> None:
    analysis_path = tmp_path / "document_analysis_results.json"
    _write_analysis(analysis_path)
    blocks, summary = build_normalized_blocks_from_analysis(
        NormalizationInput(
            doc_id="doc-one",
            doc_title="Doc One",
            source_file_name="doc-one.pdf",
            parser_run_id="upstage-parser-test",
            parser_artifact_path_alias="PARSER_DIR/doc-one/document_analysis_results.json",
            analysis_path=analysis_path,
            page_global_offset=0,
        )
    )

    sample = build_normalized_blocks_sample(blocks, summary, max_blocks=2)
    serialized = json.dumps(sample, ensure_ascii=False)

    assert "Raw text must not appear in the public sample." not in serialized
    assert str(tmp_path) not in serialized
    assert collect_private_path_leakage(sample, [tmp_path]) == []
