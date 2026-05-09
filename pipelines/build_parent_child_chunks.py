from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from app.domain.chunking import (
    ChunkingPolicy,
    ParentChildChunkingResult,
    build_parent_child_chunks,
    chunking_report_to_dict,
    collect_chunking_gate_failures,
    collect_chunking_gate_failures_from_summary,
)
from app.domain.data_contracts import NormalizedBlock
from app.domain.normalization import (
    _coerce_page_number,
    _extract_element_text,
    _resolve_element_type,
)
from app.domain.source_inventory import write_json


DEFAULT_NORMALIZED_BLOCKS_REPORT = Path("private_data/reports/normalized_blocks.json")
DEFAULT_CONFIG = Path("configs/chunking.default.yaml")
DEFAULT_PRIVATE_CHUNKS = Path("private_data/reports/parent_child_chunks.json")
DEFAULT_PRIVATE_REPORT = Path("private_data/reports/chunking_quality_report.json")
DEFAULT_PUBLIC_SAMPLE = Path("data_samples/chunking_quality_sample.json")


def build_parent_child_chunks_from_files(
    *,
    normalized_blocks_path: Path = DEFAULT_NORMALIZED_BLOCKS_REPORT,
    config_path: Path = DEFAULT_CONFIG,
    source_root: Path | None = None,
    public_sample_raw_text_count: int = 0,
    public_sample_private_path_count: int = 0,
    public_candidate_path_secret_leakage_count: int = 0,
) -> ParentChildChunkingResult:
    payload = _load_json(normalized_blocks_path)
    blocks = [
        NormalizedBlock.model_validate(block)
        for block in payload.get("normalized_blocks", [])
    ]
    policy = load_chunking_policy(config_path)
    block_text_by_id = (
        recover_block_texts_from_source(source_root=source_root, blocks=blocks)
        if source_root is not None
        else {}
    )
    result = build_parent_child_chunks(
        blocks=blocks,
        policy=policy,
        block_text_by_id=block_text_by_id,
        private_roots=[source_root] if source_root is not None else [],
        public_sample_raw_text_count=public_sample_raw_text_count,
        public_sample_private_path_count=public_sample_private_path_count,
        public_candidate_path_secret_leakage_count=public_candidate_path_secret_leakage_count,
    )
    preliminary_public_sample = result.report.to_public_sample(
        parents=result.parents,
        children=result.children,
    )
    return _apply_public_leakage_metrics(
        result=result,
        public_sample=preliminary_public_sample,
        private_roots=[source_root] if source_root is not None else [],
        repo_root=Path.cwd(),
    )


def load_chunking_policy(config_path: Path) -> ChunkingPolicy:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError("chunking config must be a mapping")
    parent_policy = _mapping(config.get("parent_policy"))
    child_policy = _mapping(config.get("child_policy"))
    citation_policy = _mapping(config.get("citation_policy"))
    quality_gates = _mapping(config.get("blocking_quality_gates"))
    coverage_policy = _mapping(config.get("coverage_policy"))
    return ChunkingPolicy(
        boundary_element_types=set(parent_policy.get("boundary_element_types", ["heading1"])),
        context_metadata_element_types=set(
            child_policy.get("context_metadata_element_types", ["heading1"])
        ),
        excluded_from_retrieval_element_types=set(
            child_policy.get("excluded_from_retrieval_element_types", ["header", "footer"])
        ),
        front_matter_parent_title=str(
            parent_policy.get("front_matter_parent_title", "front_matter")
        ),
        parent_soft_max_chars=int(parent_policy.get("soft_max_chars", 6000)),
        child_min_chars=int(child_policy.get("min_chars", 250)),
        child_target_chars=int(child_policy.get("target_chars", 700)),
        child_max_chars=int(child_policy.get("max_chars", 1100)),
        child_overlap_blocks=int(child_policy.get("overlap_blocks", 1)),
        short_block_threshold_chars=int(child_policy.get("short_block_threshold_chars", 20)),
        minimum_citation_recoverability=float(
            citation_policy.get(
                "minimum_citation_recoverability",
                quality_gates.get("minimum_citation_recoverability", 1.0),
            )
        ),
        minimum_retrievable_block_coverage=float(
            quality_gates.get("minimum_retrievable_block_coverage", 1.0)
        ),
    ).model_copy(
        update={
            "context_metadata_element_types": set(
                coverage_policy.get(
                    "exclude_element_types_from_denominator",
                    child_policy.get("context_metadata_element_types", ["heading1"]),
                )
            )
            & set(child_policy.get("context_metadata_element_types", ["heading1"]))
            or set(child_policy.get("context_metadata_element_types", ["heading1"]))
        }
    )


def recover_block_texts_from_source(
    *,
    source_root: Path,
    blocks: list[NormalizedBlock],
) -> dict[str, str]:
    lookup = _build_source_text_lookup(source_root, blocks)
    block_texts: dict[str, str] = {}
    for block in blocks:
        element_ref = block.element_refs[0]
        key = (
            block.doc_id,
            block.page_span.page_local_start,
            element_ref.element_id,
            block.element_type,
        )
        text = lookup.get(key)
        if text:
            block_texts[block.block_id] = text
    return block_texts


def main() -> int:
    args = _parse_args()
    result = build_parent_child_chunks_from_files(
        normalized_blocks_path=args.normalized_blocks_report,
        config_path=args.config,
        source_root=args.source_root,
    )
    preliminary_public_sample = result.report.to_public_sample(
        parents=result.parents,
        children=result.children,
        max_parents=args.max_public_parents,
        max_children=args.max_public_children,
    )
    private_roots = [args.source_root] if args.source_root is not None else []
    result = _apply_public_leakage_metrics(
        result=result,
        public_sample=preliminary_public_sample,
        private_roots=private_roots,
        repo_root=Path.cwd(),
    )
    include_text = args.source_root is not None
    private_chunks_payload = chunking_report_to_dict(result=result, include_text=include_text)
    private_report_payload = {
        "report_version": result.report.report_version,
        "chunking_run_id": result.report.chunking_run_id,
        "policy": result.report.policy,
        "quality_summary": result.report.quality_summary.model_dump(),
        "parent_count_by_doc": result.report.parent_count_by_doc,
        "child_count_by_doc": result.report.child_count_by_doc,
        "child_count_by_element_type": result.report.child_count_by_element_type,
        "quality_warnings": result.report.quality_warnings,
        "qualitative_assessment": result.report.qualitative_assessment,
    }
    public_sample = result.report.to_public_sample(
        parents=result.parents,
        children=result.children,
        max_parents=args.max_public_parents,
        max_children=args.max_public_children,
    )

    write_json(args.private_chunks, private_chunks_payload)
    write_json(args.private_report, private_report_payload)
    write_json(
        args.public_sample,
        public_sample,
        private_roots=private_roots,
        public_safe=True,
    )

    failures = collect_chunking_gate_failures(result.report)
    status = "PASS" if not failures else "FAIL"
    summary = result.report.quality_summary
    print(
        "chunking "
        f"status={status} "
        f"parents={summary.parent_chunk_count} "
        f"children={summary.child_chunk_count} "
        f"retrievable_coverage={summary.retrievable_block_coverage:.4f} "
        f"citation_recoverability={summary.citation_recoverability:.4f} "
        f"child_p95={summary.child_length_p95} "
        f"failures={len(failures)}"
    )
    return 0 if not failures else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build heading-aware parent-child chunks from NormalizedBlock reports."
    )
    parser.add_argument(
        "--normalized-blocks-report",
        type=Path,
        default=DEFAULT_NORMALIZED_BLOCKS_REPORT,
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--source-root", type=Path, default=None)
    parser.add_argument("--private-chunks", type=Path, default=DEFAULT_PRIVATE_CHUNKS)
    parser.add_argument("--private-report", type=Path, default=DEFAULT_PRIVATE_REPORT)
    parser.add_argument("--public-sample", type=Path, default=DEFAULT_PUBLIC_SAMPLE)
    parser.add_argument("--max-public-parents", type=int, default=3)
    parser.add_argument("--max-public-children", type=int, default=5)
    return parser.parse_args()


def _build_source_text_lookup(
    source_root: Path,
    blocks: list[NormalizedBlock],
) -> dict[tuple[str, int, str, str], str]:
    lookup: dict[tuple[str, int, str, str], str] = {}
    doc_titles = {block.doc_id: block.doc_title for block in blocks}
    for doc_id, doc_title in doc_titles.items():
        analysis_path = (
            source_root
            / "01_Data_Preprocessing"
            / doc_title
            / "document_analysis_results.json"
        )
        if not analysis_path.exists():
            continue
        payload = _load_json(analysis_path)
        page_elements = payload.get("page_elements") if isinstance(payload, dict) else None
        if not isinstance(page_elements, dict):
            continue
        for page_key, page_payload in page_elements.items():
            if not isinstance(page_payload, dict):
                continue
            page_local = _coerce_page_number(str(page_key))
            for group_name in ("text_elements", "table_elements"):
                group = page_payload.get(group_name)
                if not isinstance(group, list):
                    continue
                for element in group:
                    if not isinstance(element, dict):
                        continue
                    text = _extract_element_text(element)
                    if not text:
                        continue
                    element_id = str(element.get("id", ""))
                    element_type = _resolve_element_type(element, group_name)
                    lookup[(doc_id, page_local, element_id, element_type)] = text
    return lookup


def _apply_public_leakage_metrics(
    *,
    result: ParentChildChunkingResult,
    public_sample: dict[str, Any],
    private_roots: list[Path],
    repo_root: Path,
) -> ParentChildChunkingResult:
    summary = result.report.quality_summary.model_copy(
        update={
            "public_sample_raw_text_count": _count_forbidden_public_sample_fields(
                public_sample
            ),
            "public_sample_private_path_count": len(
                _collect_private_path_leaks(public_sample, private_roots)
            ),
            "public_candidate_path_secret_leakage_count": len(
                _collect_public_candidate_path_secret_leaks(repo_root)
            ),
        }
    )
    policy = ChunkingPolicy.model_validate(result.report.policy)
    warnings = collect_chunking_gate_failures_from_summary(summary, policy)
    qualitative_assessment = {
        **result.report.qualitative_assessment,
        "gate_status": "PASS" if not warnings else "FAIL",
    }
    report = result.report.model_copy(
        update={
            "quality_summary": summary,
            "quality_warnings": warnings,
            "qualitative_assessment": qualitative_assessment,
        }
    )
    return result.model_copy(update={"report": report})


def _count_forbidden_public_sample_fields(payload: Any) -> int:
    forbidden = {"text", "raw_text", "content", "markdown", "html"}
    if isinstance(payload, dict):
        count = sum(1 for key in payload if str(key) in forbidden)
        return count + sum(_count_forbidden_public_sample_fields(value) for value in payload.values())
    if isinstance(payload, list):
        return sum(_count_forbidden_public_sample_fields(item) for item in payload)
    return 0


def _collect_private_path_leaks(payload: Any, private_roots: list[Path]) -> list[str]:
    from app.domain.source_inventory import collect_private_path_leakage

    return collect_private_path_leakage(payload, private_roots)


def _collect_public_candidate_path_secret_leaks(repo_root: Path) -> list[str]:
    leaks: list[str] = []
    for path in _collect_public_candidate_files(repo_root):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for line_number, line in enumerate(text.splitlines(), start=1):
            if _contains_path_or_secret_leak(line):
                leaks.append(f"{path.relative_to(repo_root)}:{line_number}")
    return leaks


def _collect_public_candidate_files(repo_root: Path) -> list[Path]:
    try:
        completed = subprocess.run(
            ["git", "ls-files", "-co", "--exclude-standard"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return []

    candidates: list[Path] = []
    for line in completed.stdout.splitlines():
        relative = line.strip()
        if not relative or _is_ignored_public_scan_path(relative):
            continue
        path = repo_root / relative
        if path.is_file():
            candidates.append(path)
    return candidates


def _is_ignored_public_scan_path(relative_path: str) -> bool:
    normalized = relative_path.replace("\\", "/")
    return (
        normalized.startswith("private_data/")
        or normalized.startswith(".mypy_cache/")
        or normalized.startswith(".pytest_cache/")
        or normalized.startswith(".ruff_cache/")
        or "__pycache__/" in normalized
    )


def _contains_path_or_secret_leak(line: str) -> bool:
    if re.search(r"[A-Za-z]:\\", line):
        return True
    if re.search(r"sk-[A-Za-z0-9]", line):
        return True
    credential_match = re.search(
        r"(?i)(api[_-]?key|apikey|password|token|secret)\s*[:=]\s*(.+)$",
        line,
    )
    if credential_match is None:
        return False
    value = credential_match.group(2).strip().strip("\"'")
    return bool(value)


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
