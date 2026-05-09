from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.domain.data_contracts import collect_manifest_gate_failures
from app.domain.source_inventory import collect_private_path_leakage, write_json
from pipelines.build_data_manifest import build_data_manifest


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


@pytest.fixture()
def fixture_source_root(tmp_path: Path) -> Path:
    source_root = tmp_path / "History_Docent"
    pdf_dir = source_root / "00_PDF_history"
    parser_dir = source_root / "01_Data_Preprocessing"
    pdf_dir.mkdir(parents=True)

    for doc_name in ("doc-one", "doc-two"):
        (pdf_dir / f"{doc_name}.pdf").write_bytes(f"%PDF {doc_name}".encode())
        doc_dir = parser_dir / doc_name
        data_dir = doc_dir / "data"
        data_dir.mkdir(parents=True)
        (data_dir / f"{doc_name}_0000_0009.pdf").write_bytes(b"%PDF batch")
        _write_json(
            data_dir / f"{doc_name}_0000_0009.json",
            {
                "api": "document-parse",
                "content": "raw parser text must not be copied to manifest sample",
                "elements": [{"id": "element-1", "type": "paragraph"}],
                "model": "upstage",
                "ocr": {},
                "usage": {},
            },
        )
        _write_json(
            doc_dir / "document_analysis_results.json",
            {
                "filepath": str(pdf_dir / f"{doc_name}.pdf"),
                "batch_size": 10,
                "page_numbers": [0, 1],
                "page_elements": {"0": [{"id": "p0-e1"}], "1": [{"id": "p1-e1"}]},
                "texts": ["raw parser text must not be copied to manifest sample"],
            },
        )

    return source_root


def test_build_data_manifest_from_source_root(fixture_source_root: Path) -> None:
    manifest = build_data_manifest(fixture_source_root)

    assert manifest.source_alias == "History_Docent"
    assert len(manifest.source_documents) == 2
    assert len(manifest.parser_runs) == 1
    assert len(manifest.parser_artifacts) == 2
    assert manifest.normalized_blocks == []
    assert manifest.quality_summary.duplicate_doc_id_count == 0
    assert manifest.quality_summary.required_field_null_count == 0
    assert manifest.quality_summary.private_path_leakage_count == 0
    assert collect_manifest_gate_failures(manifest) == []


def test_data_manifest_public_sample_is_redacted(
    fixture_source_root: Path,
    tmp_path: Path,
) -> None:
    manifest = build_data_manifest(fixture_source_root)
    sample = manifest.to_public_sample(max_documents=1, max_artifacts=1)
    serialized = json.dumps(sample, ensure_ascii=False)

    assert str(fixture_source_root) not in serialized
    assert "raw parser text must not be copied to manifest sample" not in serialized
    assert "source_documents" in sample
    assert len(sample["source_documents"]) == 1
    assert len(sample["parser_artifacts"]) == 1
    assert collect_private_path_leakage(sample, [fixture_source_root]) == []

    write_json(
        tmp_path / "data_manifest_sample.json",
        sample,
        private_roots=[fixture_source_root],
        public_safe=True,
    )
