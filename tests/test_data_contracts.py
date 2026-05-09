from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from app.domain.data_contracts import (
    BlockProvenance,
    DataManifest,
    ElementReference,
    ManifestQualitySummary,
    NormalizedBlock,
    PageSpan,
    ParserArtifact,
    ParserRun,
    SourceDocument,
    collect_manifest_gate_failures,
)


def test_normalized_block_schema_requires_non_negative_page_global() -> None:
    with pytest.raises(ValidationError):
        NormalizedBlock(
            block_id="block-doc-one-000001",
            doc_id="doc-one",
            doc_title="Doc One",
            parser_run_id="upstage-parser-test",
            element_type="paragraph",
            page_span=PageSpan(page_local_start=1, page_local_end=1, page_global_start=-1),
            element_refs=[ElementReference(element_id="element-1", element_type="paragraph")],
            text_hash="a" * 64,
            text_length=42,
            provenance=BlockProvenance(
                source_file_name="doc-one.pdf",
                parser_artifact_path_alias="PARSER_DIR/doc-one/document_analysis_results.json",
                extraction_method="upstage_parser",
            ),
            quality_flags=[],
            public_allowed=False,
        )


def test_data_manifest_gate_detects_duplicate_doc_id() -> None:
    document = SourceDocument(
        doc_id="doc-one",
        doc_title="Doc One",
        source_file_name="doc-one.pdf",
        source_sha256_prefix="abc123",
        source_size_bytes=100,
        public_allowed=False,
    )
    manifest = DataManifest(
        generated_at_utc="2026-05-10T00:00:00+00:00",
        source_alias="History_Docent",
        source_documents=[document, document],
        parser_runs=[
            ParserRun(
                parser_run_id="upstage-parser-test",
                parser_model="upstage-document-parse",
                source_alias="History_Docent",
                document_count=2,
                artifact_count=1,
                created_at_utc="2026-05-10T00:00:00+00:00",
            )
        ],
        parser_artifacts=[
            ParserArtifact(
                parser_run_id="upstage-parser-test",
                doc_id="doc-one",
                artifact_kind="document_analysis",
                parser_artifact_path_alias="PARSER_DIR/doc-one/document_analysis_results.json",
                file_name="document_analysis_results.json",
                size_bytes=1000,
                sha256_prefix="def456",
                top_level_keys=["page_elements"],
                page_count=1,
                private_path_reference_count=0,
                public_allowed=False,
            )
        ],
        normalized_blocks=[],
        quality_summary=ManifestQualitySummary(
            source_document_count=2,
            parser_artifact_count=1,
            normalized_block_count=0,
            duplicate_doc_id_count=1,
            required_field_null_count=0,
            private_path_leakage_count=0,
            negative_page_global_count=0,
        ),
        quality_warnings=["duplicate_doc_ids"],
    )

    assert "duplicate_doc_ids" in collect_manifest_gate_failures(manifest)


def test_public_manifest_sample_excludes_raw_text_and_private_paths() -> None:
    block = NormalizedBlock(
        block_id="block-doc-one-000001",
        doc_id="doc-one",
        doc_title="Doc One",
        parser_run_id="upstage-parser-test",
        element_type="paragraph",
        page_span=PageSpan(page_local_start=1, page_local_end=1, page_global_start=1),
        element_refs=[ElementReference(element_id="element-1", element_type="paragraph")],
        text_hash="b" * 64,
        text_length=42,
        provenance=BlockProvenance(
            source_file_name="doc-one.pdf",
            parser_artifact_path_alias="PARSER_DIR/doc-one/document_analysis_results.json",
            extraction_method="upstage_parser",
        ),
        quality_flags=["sample_only"],
        public_allowed=False,
    )

    serialized = json.dumps(block.to_public_sample(), ensure_ascii=False)

    assert "raw_text" not in serialized
    assert "F:" not in serialized
    assert block.text_hash in serialized
