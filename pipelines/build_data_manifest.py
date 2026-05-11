from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.domain.data_contracts import (
    DataManifest,
    ManifestQualitySummary,
    NormalizedBlock,
    ParserArtifact,
    ParserRun,
    SourceDocument,
    collect_manifest_gate_failures,
)
from app.domain.source_inventory import collect_private_path_leakage, write_json


DEFAULT_PRIVATE_REPORT = Path("private_data") / "reports" / "data_manifest.json"
DEFAULT_PUBLIC_SAMPLE = Path("data_samples/data_manifest_sample.json")
SOURCE_ALIAS = "History_Docent"
PARSER_MODEL = "upstage-document-parse"


def build_data_manifest(
    source_root: str | Path,
    *,
    parser_model: str = PARSER_MODEL,
) -> DataManifest:
    root = Path(source_root)
    pdf_dir = root / "00_PDF_history"
    parser_dir = root / "01_Data_Preprocessing"
    generated_at = _utc_now()
    source_documents = _build_source_documents(pdf_dir)
    parser_run_id = _build_parser_run_id(source_documents, parser_dir)
    parser_artifacts = _build_parser_artifacts(parser_dir, parser_run_id)
    parser_runs = [
        ParserRun(
            parser_run_id=parser_run_id,
            parser_model=parser_model,
            source_alias=SOURCE_ALIAS,
            document_count=len(source_documents),
            artifact_count=len(parser_artifacts),
            created_at_utc=generated_at,
        )
    ]
    normalized_blocks: list[NormalizedBlock] = []
    quality_summary = _build_quality_summary(
        source_documents=source_documents,
        parser_artifacts=parser_artifacts,
        normalized_blocks=normalized_blocks,
        private_roots=[root, pdf_dir, parser_dir],
    )
    quality_warnings = _build_quality_warnings(
        source_documents=source_documents,
        parser_artifacts=parser_artifacts,
        quality_summary=quality_summary,
    )

    return DataManifest(
        generated_at_utc=generated_at,
        source_alias=SOURCE_ALIAS,
        source_documents=source_documents,
        parser_runs=parser_runs,
        parser_artifacts=parser_artifacts,
        normalized_blocks=normalized_blocks,
        quality_summary=quality_summary,
        quality_warnings=quality_warnings,
    )


def main() -> int:
    args = _parse_args()
    manifest = build_data_manifest(args.source_root, parser_model=args.parser_model)
    private_payload = manifest.model_dump()
    public_payload = manifest.to_public_sample(
        max_documents=args.max_public_documents,
        max_artifacts=args.max_public_artifacts,
    )

    write_json(args.private_report, private_payload)
    write_json(
        args.public_sample,
        public_payload,
        private_roots=[
            args.source_root,
            args.source_root / "00_PDF_history",
            args.source_root / "01_Data_Preprocessing",
        ],
        public_safe=True,
    )

    failures = collect_manifest_gate_failures(manifest)
    status = "PASS" if not failures else "FAIL"
    print(
        "data_manifest "
        f"status={status} "
        f"source_documents={len(manifest.source_documents)} "
        f"parser_artifacts={len(manifest.parser_artifacts)} "
        f"normalized_blocks={len(manifest.normalized_blocks)} "
        f"failures={len(failures)} "
        f"warnings={len(manifest.quality_warnings)}"
    )
    return 0 if not failures else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a redaction-safe data manifest from canonical source data."
    )
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--parser-model", default=PARSER_MODEL)
    parser.add_argument("--private-report", type=Path, default=DEFAULT_PRIVATE_REPORT)
    parser.add_argument("--public-sample", type=Path, default=DEFAULT_PUBLIC_SAMPLE)
    parser.add_argument("--max-public-documents", type=int, default=3)
    parser.add_argument("--max-public-artifacts", type=int, default=3)
    return parser.parse_args()


def _build_source_documents(pdf_dir: Path) -> list[SourceDocument]:
    documents: list[SourceDocument] = []
    if not pdf_dir.exists():
        return documents

    for pdf_path in sorted(pdf_dir.glob("*.pdf"), key=lambda item: item.name):
        if not pdf_path.is_file():
            continue
        documents.append(
            SourceDocument(
                doc_id=_slugify(pdf_path.stem),
                doc_title=pdf_path.stem,
                source_file_name=pdf_path.name,
                source_sha256_prefix=_sha256_file(pdf_path)[:12],
                source_size_bytes=pdf_path.stat().st_size,
                public_allowed=False,
            )
        )
    return documents


def _build_parser_run_id(source_documents: list[SourceDocument], parser_dir: Path) -> str:
    digest = hashlib.sha256()
    for document in source_documents:
        digest.update(document.doc_id.encode("utf-8"))
        digest.update(document.source_sha256_prefix.encode("utf-8"))
    if parser_dir.exists():
        for path in sorted(parser_dir.glob("*/document_analysis_results.json")):
            digest.update(path.name.encode("utf-8"))
            digest.update(str(path.stat().st_size).encode("utf-8"))
    return f"upstage-parser-{digest.hexdigest()[:12]}"


def _build_parser_artifacts(parser_dir: Path, parser_run_id: str) -> list[ParserArtifact]:
    if not parser_dir.exists():
        return []

    artifacts: list[ParserArtifact] = []
    for document_dir in sorted(parser_dir.iterdir(), key=lambda item: item.name):
        if not document_dir.is_dir() or document_dir.name == "__pycache__":
            continue
        analysis_path = document_dir / "document_analysis_results.json"
        if not analysis_path.exists():
            continue
        top_level_keys, page_count = _read_analysis_shape(analysis_path)
        artifacts.append(
            ParserArtifact(
                parser_run_id=parser_run_id,
                doc_id=_slugify(document_dir.name),
                artifact_kind="document_analysis",
                parser_artifact_path_alias=(
                    f"PARSER_DIR/{document_dir.name}/document_analysis_results.json"
                ),
                file_name=analysis_path.name,
                size_bytes=analysis_path.stat().st_size,
                sha256_prefix=_sha256_file(analysis_path)[:12],
                top_level_keys=top_level_keys,
                page_count=page_count,
                private_path_reference_count=0,
                public_allowed=False,
            )
        )
    return artifacts


def _read_analysis_shape(path: Path) -> tuple[list[str], int | None]:
    if path.stat().st_size == 0:
        return [], None

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return [], None

    keys = sorted(str(key) for key in payload.keys())
    page_elements = payload.get("page_elements")
    page_count = len(page_elements) if isinstance(page_elements, dict) else None
    return keys, page_count


def _build_quality_summary(
    *,
    source_documents: list[SourceDocument],
    parser_artifacts: list[ParserArtifact],
    normalized_blocks: list[Any],
    private_roots: list[Path],
) -> ManifestQualitySummary:
    doc_ids = [document.doc_id for document in source_documents]
    duplicate_doc_ids = len(doc_ids) - len(set(doc_ids))
    nulls = _count_required_nulls(
        [document.model_dump() for document in source_documents]
        + [artifact.model_dump() for artifact in parser_artifacts]
    )
    public_payload = {
        "source_documents": [document.model_dump() for document in source_documents],
        "parser_artifacts": [artifact.model_dump() for artifact in parser_artifacts],
        "normalized_blocks": normalized_blocks,
    }
    private_path_leaks = collect_private_path_leakage(public_payload, private_roots)

    return ManifestQualitySummary(
        source_document_count=len(source_documents),
        parser_artifact_count=len(parser_artifacts),
        normalized_block_count=len(normalized_blocks),
        duplicate_doc_id_count=duplicate_doc_ids,
        required_field_null_count=nulls,
        private_path_leakage_count=len(private_path_leaks),
        negative_page_global_count=0,
    )


def _build_quality_warnings(
    *,
    source_documents: list[SourceDocument],
    parser_artifacts: list[ParserArtifact],
    quality_summary: ManifestQualitySummary,
) -> list[str]:
    warnings: list[str] = []
    if len(source_documents) != 12:
        warnings.append("source_document_count_not_12")
    if len(parser_artifacts) < len(source_documents):
        warnings.append("parser_artifact_count_less_than_document_count")
    if quality_summary.duplicate_doc_id_count:
        warnings.append("duplicate_doc_ids")
    if quality_summary.required_field_null_count:
        warnings.append("required_field_nulls")
    if quality_summary.private_path_leakage_count:
        warnings.append("private_path_leakage")
    return warnings


def _count_required_nulls(payloads: list[dict[str, Any]]) -> int:
    required_keys = {
        "doc_id",
        "doc_title",
        "source_file_name",
        "source_sha256_prefix",
        "source_size_bytes",
        "parser_run_id",
        "parser_artifact_path_alias",
        "file_name",
        "size_bytes",
        "sha256_prefix",
    }
    count = 0
    for payload in payloads:
        for key in required_keys.intersection(payload.keys()):
            if payload[key] is None:
                count += 1
    return count


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _slugify(value: str) -> str:
    slug = re.sub(r"[^0-9A-Za-z가-힣]+", "-", value).strip("-")
    return slug.lower() or "document"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
