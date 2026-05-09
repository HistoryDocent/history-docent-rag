from __future__ import annotations

import json
from pathlib import Path

from app.domain.normalization import collect_normalized_block_gate_failures
from app.domain.source_inventory import collect_private_path_leakage, write_json
from pipelines.build_normalized_blocks import build_normalized_blocks_report


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _build_fixture_source_root(tmp_path: Path) -> Path:
    source_root = tmp_path / "History_Docent"
    pdf_dir = source_root / "00_PDF_history"
    parser_dir = source_root / "01_Data_Preprocessing"
    pdf_dir.mkdir(parents=True)

    for index, doc_name in enumerate(("doc-one", "doc-two")):
        (pdf_dir / f"{doc_name}.pdf").write_bytes(f"%PDF {doc_name}".encode())
        doc_dir = parser_dir / doc_name
        _write_json(
            doc_dir / "document_analysis_results.json",
            {
                "page_elements": {
                    "0": {
                        "text_elements": [
                            {
                                "id": index * 10,
                                "category": "paragraph",
                                "page": 0,
                                "content": {"text": f"{doc_name} private source text"},
                            }
                        ],
                        "table_elements": [],
                        "image_elements": [],
                    }
                }
            },
        )
    return source_root


def test_build_normalized_blocks_report_from_source_root(tmp_path: Path) -> None:
    source_root = _build_fixture_source_root(tmp_path)

    report = build_normalized_blocks_report(source_root)

    assert report["quality_summary"]["document_count"] == 2
    assert report["quality_summary"]["normalized_block_count"] == 2
    assert report["quality_summary"]["duplicate_block_id_count"] == 0
    assert report["quality_summary"]["empty_element_refs_count"] == 0
    assert report["quality_summary"]["private_path_leakage_count"] == 0
    assert collect_normalized_block_gate_failures(
        report["normalized_blocks"],
        report["quality_summary"],
    ) == []


def test_normalized_blocks_report_public_sample_is_safe(
    tmp_path: Path,
) -> None:
    source_root = _build_fixture_source_root(tmp_path)
    report = build_normalized_blocks_report(source_root)
    sample = report["public_sample"]
    serialized = json.dumps(sample, ensure_ascii=False)

    assert "private source text" not in serialized
    assert str(source_root) not in serialized
    assert collect_private_path_leakage(sample, [source_root]) == []

    write_json(
        tmp_path / "normalized_blocks_sample.json",
        sample,
        private_roots=[source_root],
        public_safe=True,
    )
