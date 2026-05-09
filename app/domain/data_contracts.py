from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


DATA_MANIFEST_VERSION = "data-manifest/v1"
PRIVATE_PATH_MARKER = "<private_path>"


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SourceDocument(ContractModel):
    doc_id: str = Field(min_length=1)
    doc_title: str = Field(min_length=1)
    source_file_name: str = Field(min_length=1)
    source_sha256_prefix: str = Field(min_length=6)
    source_size_bytes: int = Field(ge=1)
    public_allowed: bool = False


class ParserRun(ContractModel):
    parser_run_id: str = Field(min_length=1)
    parser_model: str = Field(min_length=1)
    source_alias: str = Field(min_length=1)
    document_count: int = Field(ge=0)
    artifact_count: int = Field(ge=0)
    created_at_utc: str = Field(min_length=1)


class ParserArtifact(ContractModel):
    parser_run_id: str = Field(min_length=1)
    doc_id: str = Field(min_length=1)
    artifact_kind: Literal["document_analysis", "batch_json", "batch_pdf"]
    parser_artifact_path_alias: str = Field(min_length=1)
    file_name: str = Field(min_length=1)
    size_bytes: int = Field(ge=0)
    sha256_prefix: str = Field(min_length=6)
    top_level_keys: list[str] = Field(default_factory=list)
    page_count: int | None = Field(default=None, ge=0)
    private_path_reference_count: int = Field(ge=0)
    public_allowed: bool = False

    @field_validator("parser_artifact_path_alias")
    @classmethod
    def reject_absolute_path_alias(cls, value: str) -> str:
        normalized = value.replace("\\", "/")
        if ":" in normalized or normalized.startswith("/"):
            raise ValueError("parser_artifact_path_alias must not be an absolute path")
        return value


class PageSpan(ContractModel):
    page_local_start: int = Field(ge=0)
    page_local_end: int = Field(ge=0)
    page_global_start: int = Field(ge=0)
    page_global_end: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_page_order(self) -> "PageSpan":
        global_end = self.page_global_end
        if self.page_local_end < self.page_local_start:
            raise ValueError("page_local_end must be greater than or equal to page_local_start")
        if global_end is not None and global_end < self.page_global_start:
            raise ValueError("page_global_end must be greater than or equal to page_global_start")
        return self


class ElementReference(ContractModel):
    element_id: str = Field(min_length=1)
    element_type: str = Field(min_length=1)
    element_index: int | None = Field(default=None, ge=0)


class BlockProvenance(ContractModel):
    source_file_name: str = Field(min_length=1)
    parser_artifact_path_alias: str = Field(min_length=1)
    extraction_method: Literal["upstage_parser", "manual_seed", "derived_summary"]

    @field_validator("parser_artifact_path_alias")
    @classmethod
    def reject_absolute_path_alias(cls, value: str) -> str:
        normalized = value.replace("\\", "/")
        if ":" in normalized or normalized.startswith("/"):
            raise ValueError("parser_artifact_path_alias must not be an absolute path")
        return value


class NormalizedBlock(ContractModel):
    block_id: str = Field(min_length=1)
    doc_id: str = Field(min_length=1)
    doc_title: str = Field(min_length=1)
    parser_run_id: str = Field(min_length=1)
    element_type: str = Field(min_length=1)
    page_span: PageSpan
    element_refs: list[ElementReference] = Field(min_length=1)
    text_hash: str = Field(min_length=32)
    text_length: int = Field(ge=0)
    provenance: BlockProvenance
    quality_flags: list[str] = Field(default_factory=list)
    public_allowed: bool = False

    def to_public_sample(self) -> dict[str, Any]:
        return self.model_dump()


class ManifestQualitySummary(ContractModel):
    source_document_count: int = Field(ge=0)
    parser_artifact_count: int = Field(ge=0)
    normalized_block_count: int = Field(ge=0)
    duplicate_doc_id_count: int = Field(ge=0)
    required_field_null_count: int = Field(ge=0)
    private_path_leakage_count: int = Field(ge=0)
    negative_page_global_count: int = Field(ge=0)


class DataManifest(ContractModel):
    report_version: str = DATA_MANIFEST_VERSION
    generated_at_utc: str = Field(min_length=1)
    source_alias: str = Field(min_length=1)
    source_documents: list[SourceDocument]
    parser_runs: list[ParserRun]
    parser_artifacts: list[ParserArtifact]
    normalized_blocks: list[NormalizedBlock] = Field(default_factory=list)
    quality_summary: ManifestQualitySummary
    quality_warnings: list[str] = Field(default_factory=list)

    def to_public_sample(
        self,
        *,
        max_documents: int = 3,
        max_artifacts: int = 3,
        max_blocks: int = 3,
    ) -> dict[str, Any]:
        return {
            "report_version": self.report_version,
            "generated_at_utc": self.generated_at_utc,
            "source_alias": self.source_alias,
            "source_root": PRIVATE_PATH_MARKER,
            "source_documents": [
                document.model_dump() for document in self.source_documents[:max_documents]
            ],
            "parser_runs": [parser_run.model_dump() for parser_run in self.parser_runs],
            "parser_artifacts": [
                artifact.model_dump() for artifact in self.parser_artifacts[:max_artifacts]
            ],
            "normalized_blocks": [
                block.to_public_sample() for block in self.normalized_blocks[:max_blocks]
            ],
            "quality_summary": self.quality_summary.model_dump(),
            "quality_warnings": self.quality_warnings,
            "data_policy": {
                "public_sample_contains_source_text": False,
                "public_sample_contains_private_paths": False,
                "full_source_data_storage": "private_data only",
            },
        }


def collect_manifest_gate_failures(manifest: DataManifest) -> list[str]:
    failures: list[str] = []
    if manifest.quality_summary.duplicate_doc_id_count:
        failures.append("duplicate_doc_ids")
    if manifest.quality_summary.required_field_null_count:
        failures.append("required_field_nulls")
    if manifest.quality_summary.private_path_leakage_count:
        failures.append("private_path_leakage")
    if manifest.quality_summary.negative_page_global_count:
        failures.append("negative_page_global")
    return failures
