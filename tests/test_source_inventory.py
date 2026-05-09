from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.domain.source_inventory import (
    SourceInventoryPaths,
    build_source_inventory_report,
    collect_private_path_leakage,
    write_json,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


@pytest.fixture()
def fixture_source_root(tmp_path: Path) -> Path:
    source_root = tmp_path / "History_Docent"
    pdf_dir = source_root / "00_PDF_history"
    parser_dir = source_root / "01_Data_Preprocessing"
    chunk_dir = source_root / "02_Chunking" / "output"

    pdf_dir.mkdir(parents=True)
    (pdf_dir / "doc-one.pdf").write_bytes(b"%PDF doc-one")
    (pdf_dir / "doc-two.pdf").write_bytes(b"%PDF doc-two")

    doc_one_dir = parser_dir / "doc-one"
    doc_two_dir = parser_dir / "doc-two"
    for doc_dir in (doc_one_dir, doc_two_dir):
        (doc_dir / "data").mkdir(parents=True)
        (doc_dir / "data" / f"{doc_dir.name}_0000_0009.pdf").write_bytes(b"%PDF batch")
        _write_json(
            doc_dir / "data" / f"{doc_dir.name}_0000_0009.json",
            {
                "api": "document-parse",
                "content": "copyright source text must never appear in public sample",
                "elements": [{"id": "element-1", "page": 1}],
                "model": "upstage",
                "ocr": {},
                "usage": {},
            },
        )
        _write_json(
            doc_dir / "document_analysis_results.json",
            {
                "filepath": str(pdf_dir / f"{doc_dir.name}.pdf"),
                "batch_size": 10,
                "page_numbers": [0, 1],
                "page_elements": {"0": [{"id": "p0-e1"}], "1": [{"id": "p1-e1"}]},
                "texts": ["copyright source text must never appear in public sample"],
            },
        )
        (doc_dir / f"{doc_dir.name}.pkl").write_bytes(b"pickle")
        (doc_dir / "images").mkdir()
        (doc_dir / "images" / "page_0001.png").write_bytes(b"png")

    _write_json(
        chunk_dir / "all_chunks.json",
        [
            {
                "chunk_id": "chunk-1",
                "metadata": {"source": "doc-one", "page": 1, "type": "text"},
                "text": "normal chunk",
            },
            {
                "chunk_id": "chunk-2",
                "metadata": {"source": "doc-two", "page": 2, "type": "text"},
                "text": "[무제] broken � text",
            },
        ],
    )
    return source_root


def test_build_source_inventory_report_counts_documents(fixture_source_root: Path) -> None:
    paths = SourceInventoryPaths.from_source_root(fixture_source_root)

    report = build_source_inventory_report(paths)

    assert report.source_root_exists is True
    assert report.pdf_summary.pdf_count == 2
    assert report.parser_summary.document_count == 2
    assert report.parser_summary.document_analysis_count == 2
    assert report.parser_summary.zero_byte_file_count == 0
    assert report.legacy_chunk_summary is not None
    assert report.legacy_chunk_summary.chunk_count == 2
    assert report.legacy_chunk_summary.replacement_char_chunk_count == 1
    assert report.legacy_chunk_summary.untitled_like_chunk_count == 1


def test_public_sample_does_not_leak_private_paths_or_source_text(
    fixture_source_root: Path,
) -> None:
    paths = SourceInventoryPaths.from_source_root(fixture_source_root)
    report = build_source_inventory_report(paths)

    sample = report.to_public_sample(max_documents=1)
    serialized = json.dumps(sample, ensure_ascii=False)

    assert str(fixture_source_root) not in serialized
    assert "copyright source text must never appear in public sample" not in serialized
    assert sample["parser_summary"]["document_count"] == 2
    assert len(sample["documents"]) == 1
    assert collect_private_path_leakage(sample, [fixture_source_root]) == []


def test_write_json_rejects_public_private_path_leakage(
    fixture_source_root: Path,
    tmp_path: Path,
) -> None:
    unsafe_payload = {"leak": str(fixture_source_root / "00_PDF_history" / "doc-one.pdf")}

    with pytest.raises(ValueError, match="private path"):
        write_json(
            tmp_path / "source_inventory_sample.json",
            unsafe_payload,
            private_roots=[fixture_source_root],
            public_safe=True,
        )
