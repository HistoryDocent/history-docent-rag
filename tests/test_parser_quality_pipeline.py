from __future__ import annotations

import json
from pathlib import Path

from app.domain.parser_quality import collect_parser_quality_gate_failures
from app.domain.source_inventory import collect_private_path_leakage
from pipelines.build_parser_quality_report import build_parser_quality_report_from_files


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_build_parser_quality_report_from_private_reports(tmp_path: Path) -> None:
    normalized_blocks_path = tmp_path / "normalized_blocks.json"
    data_manifest_path = tmp_path / "data_manifest.json"
    block = {
        "block_id": "block-doc-one-000000-paragraph-1",
        "doc_id": "doc-one",
        "doc_title": "Doc One",
        "parser_run_id": "upstage-parser-test",
        "element_type": "paragraph",
        "page_span": {
            "page_local_start": 0,
            "page_local_end": 0,
            "page_global_start": 0,
            "page_global_end": 0,
        },
        "element_refs": [{"element_id": "1", "element_type": "paragraph", "element_index": 0}],
        "text_hash": "d" * 64,
        "text_length": 50,
        "provenance": {
            "source_file_name": "doc-one.pdf",
            "parser_artifact_path_alias": "PARSER_DIR/doc-one/document_analysis_results.json",
            "extraction_method": "upstage_parser",
        },
        "quality_flags": [],
        "public_allowed": False,
    }
    _write_json(
        normalized_blocks_path,
        {
            "report_version": "normalized-blocks/v1",
            "normalized_blocks": [block],
            "quality_summary": {"normalized_block_count": 1},
        },
    )
    _write_json(
        data_manifest_path,
        {
            "parser_artifacts": [
                {
                    "doc_id": "doc-one",
                    "artifact_kind": "document_analysis",
                    "page_count": 1,
                }
            ]
        },
    )

    report = build_parser_quality_report_from_files(
        normalized_blocks_path=normalized_blocks_path,
        data_manifest_path=data_manifest_path,
    )
    sample = report.to_public_sample(max_documents=1)

    assert report.quality_summary.document_count == 1
    assert report.quality_summary.normalized_block_count == 1
    assert report.page_coverage_by_doc["doc-one"]["missing_page_count"] == 0
    assert collect_parser_quality_gate_failures(report) == []
    assert collect_private_path_leakage(sample, [tmp_path]) == []
