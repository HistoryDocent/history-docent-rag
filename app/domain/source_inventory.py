from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPORT_VERSION = "source-inventory/v1"
REPLACEMENT_CHAR = "\ufffd"
UNTITLED_MARKER = "[무제]"
PRIVATE_PATH_MARKER = "<private_path>"


@dataclass(frozen=True)
class SourceInventoryPaths:
    source_root: Path
    pdf_dir: Path
    parser_dir: Path
    legacy_chunk_file: Path | None = None

    @classmethod
    def from_source_root(cls, source_root: str | Path) -> "SourceInventoryPaths":
        root = Path(source_root)
        return cls(
            source_root=root,
            pdf_dir=root / "00_PDF_history",
            parser_dir=root / "01_Data_Preprocessing",
            legacy_chunk_file=root / "02_Chunking" / "output" / "all_chunks.json",
        )


@dataclass(frozen=True)
class PdfFileInventory:
    file_name: str
    size_bytes: int
    sha256: str

    def to_public_sample(self) -> dict[str, Any]:
        return {
            "file_name": self.file_name,
            "size_bytes": self.size_bytes,
            "sha256_prefix": self.sha256[:12],
        }


@dataclass(frozen=True)
class PdfSummary:
    pdf_dir_exists: bool
    pdf_count: int
    files: list[PdfFileInventory]

    def to_public_sample(self) -> dict[str, Any]:
        return {
            "pdf_dir_exists": self.pdf_dir_exists,
            "pdf_count": self.pdf_count,
            "files": [file.to_public_sample() for file in self.files],
        }


@dataclass(frozen=True)
class ParserDocumentInventory:
    document_id: str
    document_title: str
    document_dir_name: str
    artifact_counts_by_extension: dict[str, int]
    zero_byte_file_count: int
    batch_json_count: int
    batch_pdf_count: int
    document_analysis_present: bool
    document_analysis_size_bytes: int | None
    document_analysis_sha256: str | None
    document_analysis_top_level_keys: list[str]
    page_element_page_count: int | None
    page_element_total_count: int | None
    private_path_reference_count: int
    quality_warnings: list[str] = field(default_factory=list)

    def to_public_sample(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "document_title": self.document_title,
            "document_dir_name": self.document_dir_name,
            "artifact_counts_by_extension": self.artifact_counts_by_extension,
            "zero_byte_file_count": self.zero_byte_file_count,
            "batch_json_count": self.batch_json_count,
            "batch_pdf_count": self.batch_pdf_count,
            "document_analysis_present": self.document_analysis_present,
            "document_analysis_size_bytes": self.document_analysis_size_bytes,
            "document_analysis_sha256_prefix": (
                self.document_analysis_sha256[:12] if self.document_analysis_sha256 else None
            ),
            "document_analysis_top_level_keys": self.document_analysis_top_level_keys,
            "page_element_page_count": self.page_element_page_count,
            "page_element_total_count": self.page_element_total_count,
            "private_path_reference_count": self.private_path_reference_count,
            "quality_warnings": self.quality_warnings,
        }


@dataclass(frozen=True)
class ParserSummary:
    parser_dir_exists: bool
    document_count: int
    document_analysis_count: int
    zero_byte_file_count: int
    total_batch_json_count: int
    total_batch_pdf_count: int
    extension_counts: dict[str, int]

    def to_public_sample(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LegacyChunkSummary:
    exists: bool
    size_bytes: int | None
    sha256: str | None
    chunk_count: int | None
    chunk_fields: list[str]
    metadata_fields: list[str]
    replacement_char_chunk_count: int
    untitled_like_chunk_count: int
    json_error: str | None = None

    def to_public_sample(self) -> dict[str, Any]:
        return {
            "exists": self.exists,
            "size_bytes": self.size_bytes,
            "sha256_prefix": self.sha256[:12] if self.sha256 else None,
            "chunk_count": self.chunk_count,
            "chunk_fields": self.chunk_fields,
            "metadata_fields": self.metadata_fields,
            "replacement_char_chunk_count": self.replacement_char_chunk_count,
            "untitled_like_chunk_count": self.untitled_like_chunk_count,
            "json_error": self.json_error,
        }


@dataclass(frozen=True)
class SourceInventoryReport:
    report_version: str
    generated_at_utc: str
    source_root: str
    source_root_exists: bool
    pdf_summary: PdfSummary
    parser_summary: ParserSummary
    documents: list[ParserDocumentInventory]
    legacy_chunk_summary: LegacyChunkSummary | None
    quality_warnings: list[str]

    def to_private_report(self) -> dict[str, Any]:
        return asdict(self)

    def to_public_sample(self, max_documents: int = 3) -> dict[str, Any]:
        return {
            "report_version": self.report_version,
            "generated_at_utc": self.generated_at_utc,
            "canonical_source_alias": "History_Docent",
            "source_root": PRIVATE_PATH_MARKER,
            "source_root_exists": self.source_root_exists,
            "pdf_summary": self.pdf_summary.to_public_sample(),
            "parser_summary": self.parser_summary.to_public_sample(),
            "documents": [
                document.to_public_sample() for document in self.documents[:max_documents]
            ],
            "legacy_chunk_summary": (
                self.legacy_chunk_summary.to_public_sample()
                if self.legacy_chunk_summary
                else None
            ),
            "quality_warnings": self.quality_warnings,
            "data_policy": {
                "public_sample_contains_source_text": False,
                "public_sample_contains_private_paths": False,
                "full_source_data_storage": "private_data only",
            },
        }


def build_source_inventory_report(paths: SourceInventoryPaths) -> SourceInventoryReport:
    pdf_summary = _scan_pdf_dir(paths.pdf_dir)
    documents = _scan_parser_documents(paths.parser_dir, private_roots=[paths.source_root])
    parser_summary = _build_parser_summary(paths.parser_dir, documents)
    legacy_chunk_summary = _scan_legacy_chunks(paths.legacy_chunk_file)
    quality_warnings = _build_quality_warnings(
        source_root=paths.source_root,
        pdf_summary=pdf_summary,
        parser_summary=parser_summary,
        legacy_chunk_summary=legacy_chunk_summary,
    )

    return SourceInventoryReport(
        report_version=REPORT_VERSION,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        source_root=str(paths.source_root.resolve()),
        source_root_exists=paths.source_root.exists(),
        pdf_summary=pdf_summary,
        parser_summary=parser_summary,
        documents=documents,
        legacy_chunk_summary=legacy_chunk_summary,
        quality_warnings=quality_warnings,
    )


def write_json(
    path: Path,
    payload: dict[str, Any],
    *,
    private_roots: list[Path] | None = None,
    public_safe: bool = False,
) -> None:
    if public_safe and private_roots:
        leaks = collect_private_path_leakage(payload, private_roots)
        if leaks:
            raise ValueError(f"public JSON contains private path leakage: {leaks[:3]}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def collect_private_path_leakage(payload: Any, private_roots: list[Path]) -> list[str]:
    normalized_values = [_normalize_for_path_scan(value) for value in _iter_string_values(payload)]
    leaks: list[str] = []

    for root in private_roots:
        root_text = str(root)
        if not root_text:
            continue
        normalized_root = _normalize_for_path_scan(root_text)
        if normalized_root and any(normalized_root in value for value in normalized_values):
            leaks.append(root_text)

    return leaks


def _scan_pdf_dir(pdf_dir: Path) -> PdfSummary:
    if not pdf_dir.exists():
        return PdfSummary(pdf_dir_exists=False, pdf_count=0, files=[])

    files = [
        PdfFileInventory(
            file_name=path.name,
            size_bytes=path.stat().st_size,
            sha256=_sha256_file(path),
        )
        for path in sorted(pdf_dir.glob("*.pdf"), key=lambda item: item.name)
        if path.is_file()
    ]
    return PdfSummary(pdf_dir_exists=True, pdf_count=len(files), files=files)


def _scan_parser_documents(
    parser_dir: Path,
    *,
    private_roots: list[Path],
) -> list[ParserDocumentInventory]:
    if not parser_dir.exists():
        return []

    documents: list[ParserDocumentInventory] = []
    for document_dir in sorted(parser_dir.iterdir(), key=lambda item: item.name):
        if not document_dir.is_dir() or document_dir.name == "__pycache__":
            continue
        documents.append(_scan_parser_document(document_dir, private_roots=private_roots))
    return documents


def _scan_parser_document(
    document_dir: Path,
    *,
    private_roots: list[Path],
) -> ParserDocumentInventory:
    files = [path for path in document_dir.rglob("*") if path.is_file()]
    extension_counts = _count_extensions(files)
    zero_byte_file_count = sum(1 for path in files if path.stat().st_size == 0)
    data_dir = document_dir / "data"
    batch_json_files = _find_batch_files(data_dir, ".json")
    batch_pdf_files = _find_batch_files(data_dir, ".pdf")
    analysis_path = document_dir / "document_analysis_results.json"
    analysis_present = analysis_path.exists() and analysis_path.is_file()
    analysis_keys: list[str] = []
    page_element_page_count: int | None = None
    page_element_total_count: int | None = None
    private_path_reference_count = 0
    quality_warnings: list[str] = []
    analysis_size: int | None = None
    analysis_sha256: str | None = None

    if analysis_present:
        analysis_size = analysis_path.stat().st_size
        analysis_sha256 = _sha256_file(analysis_path)
        if analysis_size == 0:
            quality_warnings.append("empty_document_analysis")
        else:
            analysis_payload = _load_json(analysis_path)
            if isinstance(analysis_payload, dict):
                analysis_keys = sorted(str(key) for key in analysis_payload.keys())
                page_element_page_count, page_element_total_count = _count_page_elements(
                    analysis_payload.get("page_elements")
                )
            else:
                quality_warnings.append("document_analysis_not_object")
        private_path_reference_count = _count_private_path_references(
            analysis_path, private_roots
        )
    else:
        quality_warnings.append("missing_document_analysis")

    if zero_byte_file_count:
        quality_warnings.append("zero_byte_files")
    if not batch_json_files:
        quality_warnings.append("missing_batch_json")
    if not batch_pdf_files:
        quality_warnings.append("missing_batch_pdf")
    if private_path_reference_count:
        quality_warnings.append("private_path_references_in_parser_artifact")

    return ParserDocumentInventory(
        document_id=_slugify(document_dir.name),
        document_title=document_dir.name,
        document_dir_name=document_dir.name,
        artifact_counts_by_extension=extension_counts,
        zero_byte_file_count=zero_byte_file_count,
        batch_json_count=len(batch_json_files),
        batch_pdf_count=len(batch_pdf_files),
        document_analysis_present=analysis_present,
        document_analysis_size_bytes=analysis_size,
        document_analysis_sha256=analysis_sha256,
        document_analysis_top_level_keys=analysis_keys,
        page_element_page_count=page_element_page_count,
        page_element_total_count=page_element_total_count,
        private_path_reference_count=private_path_reference_count,
        quality_warnings=quality_warnings,
    )


def _build_parser_summary(
    parser_dir: Path,
    documents: list[ParserDocumentInventory],
) -> ParserSummary:
    extension_counts: dict[str, int] = {}
    if parser_dir.exists():
        extension_counts = _count_extensions([path for path in parser_dir.rglob("*") if path.is_file()])

    return ParserSummary(
        parser_dir_exists=parser_dir.exists(),
        document_count=len(documents),
        document_analysis_count=sum(1 for document in documents if document.document_analysis_present),
        zero_byte_file_count=sum(document.zero_byte_file_count for document in documents),
        total_batch_json_count=sum(document.batch_json_count for document in documents),
        total_batch_pdf_count=sum(document.batch_pdf_count for document in documents),
        extension_counts=extension_counts,
    )


def _scan_legacy_chunks(legacy_chunk_file: Path | None) -> LegacyChunkSummary | None:
    if legacy_chunk_file is None:
        return None
    if not legacy_chunk_file.exists():
        return LegacyChunkSummary(
            exists=False,
            size_bytes=None,
            sha256=None,
            chunk_count=None,
            chunk_fields=[],
            metadata_fields=[],
            replacement_char_chunk_count=0,
            untitled_like_chunk_count=0,
        )

    size_bytes = legacy_chunk_file.stat().st_size
    sha256 = _sha256_file(legacy_chunk_file)
    if size_bytes == 0:
        return LegacyChunkSummary(
            exists=True,
            size_bytes=size_bytes,
            sha256=sha256,
            chunk_count=None,
            chunk_fields=[],
            metadata_fields=[],
            replacement_char_chunk_count=0,
            untitled_like_chunk_count=0,
            json_error="empty_file",
        )

    try:
        payload = _load_json(legacy_chunk_file)
    except json.JSONDecodeError as exc:
        return LegacyChunkSummary(
            exists=True,
            size_bytes=size_bytes,
            sha256=sha256,
            chunk_count=None,
            chunk_fields=[],
            metadata_fields=[],
            replacement_char_chunk_count=0,
            untitled_like_chunk_count=0,
            json_error=f"{exc.__class__.__name__}: {exc.msg}",
        )

    chunks = payload if isinstance(payload, list) else []
    chunk_fields = sorted(
        {str(field) for chunk in chunks if isinstance(chunk, dict) for field in chunk.keys()}
    )
    metadata_fields = sorted(
        {
            str(field)
            for chunk in chunks
            if isinstance(chunk, dict) and isinstance(chunk.get("metadata"), dict)
            for field in chunk["metadata"].keys()
        }
    )
    replacement_char_count = sum(
        1
        for chunk in chunks
        if isinstance(chunk, dict) and REPLACEMENT_CHAR in str(chunk.get("text", ""))
    )
    untitled_like_count = sum(
        1
        for chunk in chunks
        if isinstance(chunk, dict)
        and (
            UNTITLED_MARKER in str(chunk.get("text", ""))
            or UNTITLED_MARKER in json.dumps(chunk.get("metadata", {}), ensure_ascii=False)
        )
    )

    return LegacyChunkSummary(
        exists=True,
        size_bytes=size_bytes,
        sha256=sha256,
        chunk_count=len(chunks),
        chunk_fields=chunk_fields,
        metadata_fields=metadata_fields,
        replacement_char_chunk_count=replacement_char_count,
        untitled_like_chunk_count=untitled_like_count,
    )


def _build_quality_warnings(
    *,
    source_root: Path,
    pdf_summary: PdfSummary,
    parser_summary: ParserSummary,
    legacy_chunk_summary: LegacyChunkSummary | None,
) -> list[str]:
    warnings: list[str] = []
    if not source_root.exists():
        warnings.append("source_root_missing")
    if not pdf_summary.pdf_dir_exists:
        warnings.append("pdf_dir_missing")
    if pdf_summary.pdf_count != 12:
        warnings.append("pdf_count_not_12")
    if not parser_summary.parser_dir_exists:
        warnings.append("parser_dir_missing")
    if parser_summary.document_count != 12:
        warnings.append("parser_document_count_not_12")
    if parser_summary.document_analysis_count != 12:
        warnings.append("document_analysis_count_not_12")
    if parser_summary.zero_byte_file_count:
        warnings.append("parser_zero_byte_files")
    if legacy_chunk_summary is None or not legacy_chunk_summary.exists:
        warnings.append("legacy_chunk_missing")
    elif legacy_chunk_summary.json_error:
        warnings.append("legacy_chunk_invalid")
    return warnings


def _find_batch_files(data_dir: Path, extension: str) -> list[Path]:
    if not data_dir.exists():
        return []

    pattern = re.compile(r"_\d{4}_\d{4}$")
    return [
        path
        for path in sorted(data_dir.glob(f"*{extension}"), key=lambda item: item.name)
        if path.is_file() and pattern.search(path.stem)
    ]


def _count_extensions(files: list[Path]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for path in files:
        extension = path.suffix.lower() if path.suffix else "[none]"
        counts[extension] = counts.get(extension, 0) + 1
    return dict(sorted(counts.items()))


def _count_page_elements(page_elements: Any) -> tuple[int | None, int | None]:
    if not isinstance(page_elements, dict):
        return None, None

    page_count = len(page_elements)
    total_count = 0
    for value in page_elements.values():
        if isinstance(value, list):
            total_count += len(value)
        elif value is not None:
            total_count += 1
    return page_count, total_count


def _count_private_path_references(path: Path, private_roots: list[Path]) -> int:
    text = path.read_text(encoding="utf-8", errors="ignore")
    normalized_text = _normalize_for_path_scan(text)
    count = 0
    for private_root in private_roots:
        normalized_root = _normalize_for_path_scan(str(private_root))
        if normalized_root:
            count += normalized_text.count(normalized_root)
    return count


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _slugify(value: str) -> str:
    slug = re.sub(r"[^0-9A-Za-z가-힣]+", "-", value).strip("-")
    return slug.lower() or "document"


def _normalize_for_path_scan(value: str) -> str:
    return value.replace("\\", "/").lower()


def _iter_string_values(payload: Any) -> list[str]:
    if isinstance(payload, str):
        return [payload]
    if isinstance(payload, dict):
        values: list[str] = []
        for key, value in payload.items():
            values.extend(_iter_string_values(key))
            values.extend(_iter_string_values(value))
        return values
    if isinstance(payload, list | tuple | set):
        values = []
        for item in payload:
            values.extend(_iter_string_values(item))
        return values
    return []
