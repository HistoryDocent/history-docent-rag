from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.application.evidence_packing import (
    EVIDENCE_PACKING_REPORT_VERSION,
    EvidencePackingComparisonReport,
    EvidencePackingPolicyId,
    build_candidates_by_query_id,
    build_evidence_corpus_from_chunks_payload,
    build_evidence_packing_comparison_report,
    build_evidence_packing_report_markdown,
    build_evidence_packs,
    build_public_evidence_packing_rows,
)
from app.core.project_paths import (
    has_private_data_segment,
    is_repository_private_artifact_path,
    is_repository_private_write_path,
)
from app.domain.retrieval import RetrievalEvalItem, load_retrieval_eval_jsonl
from app.domain.retrieval_experiment import (
    collect_public_retrieval_artifact_failures,
    measure_public_retrieval_artifact_quality,
)


DEFAULT_CHUNKS_PATH = Path("private_data") / "reports" / "parent_child_chunks.json"
DEFAULT_DATASET_PATH = (
    Path("private_data") / "evals" / "datasets" / "retrieval_eval_dev.jsonl"
)
DEFAULT_RETRIEVAL_RESULTS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "retrieval_experiment_dense_multilingual_e5_small_voice_rewrite_results.jsonl"
)
DEFAULT_PACKING_ROWS_PATH = (
    Path("private_data") / "evals" / "results" / "evidence_packing_comparison_results.jsonl"
)
DEFAULT_REPORT_PATH = Path("evals/reports/evidence_packing_comparison_report.md")
DEFAULT_POLICIES = (
    "P0_rank_order",
    "P1_parent_expansion",
    "P2_best_first_with_parent",
    "P3_mmr_diversity",
    "P4_voice_compact",
)


def run_evidence_packing_experiment(
    *,
    chunks_path: Path = DEFAULT_CHUNKS_PATH,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    retrieval_results_path: Path = DEFAULT_RETRIEVAL_RESULTS_PATH,
    packing_rows_path: Path = DEFAULT_PACKING_ROWS_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    policies: list[EvidencePackingPolicyId] | None = None,
) -> EvidencePackingComparisonReport:
    policy_ids = policies or list(DEFAULT_POLICIES)
    items = load_retrieval_eval_jsonl(dataset_path)
    _validate_dataset_policy(items)
    _validate_artifact_policy(
        chunks_path=chunks_path,
        dataset_path=dataset_path,
        retrieval_results_path=retrieval_results_path,
        packing_rows_path=packing_rows_path,
    )
    chunks_payload = json.loads(chunks_path.read_text(encoding="utf-8"))
    corpus = build_evidence_corpus_from_chunks_payload(chunks_payload)
    retrieval_rows = load_jsonl_rows(retrieval_results_path)
    candidates_by_query_id = build_candidates_by_query_id(
        result_rows=retrieval_rows,
        corpus=corpus,
    )
    packs = build_evidence_packs(
        items=items,
        candidates_by_query_id=candidates_by_query_id,
        corpus=corpus,
        policy_ids=policy_ids,
    )
    provisional_report = build_evidence_packing_comparison_report(
        items=items,
        packs=packs,
        dataset_path=dataset_path,
        retrieval_result_path=retrieval_results_path,
        result_rows=[],
        corpus=corpus,
    )
    packing_rows = build_public_evidence_packing_rows(
        comparison_id=provisional_report.comparison_id,
        packs=packs,
    )
    provisional_report = provisional_report.model_copy(
        update={
            "output_quality": measure_public_retrieval_artifact_quality(
                report_version=EVIDENCE_PACKING_REPORT_VERSION,
                run_id=provisional_report.comparison_id,
                result_rows=packing_rows,
                report_text="",
            )
        },
    )
    report_text = build_evidence_packing_report_markdown(provisional_report)
    final_quality = measure_public_retrieval_artifact_quality(
        report_version=EVIDENCE_PACKING_REPORT_VERSION,
        run_id=provisional_report.comparison_id,
        result_rows=packing_rows,
        report_text=report_text,
    )
    report = provisional_report.model_copy(update={"output_quality": final_quality})
    report_text = build_evidence_packing_report_markdown(report)
    failures = collect_public_retrieval_artifact_failures(report.output_quality)
    if failures:
        raise ValueError(f"evidence packing public output gate failed: {failures}")
    write_jsonl_rows(path=packing_rows_path, rows=packing_rows)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_text, encoding="utf-8")
    return report


def load_jsonl_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"jsonl row must be an object at line {line_number}")
        rows.append(row)
    return rows


def write_jsonl_rows(*, path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows
    )
    path.write_text(payload + "\n", encoding="utf-8")


def _validate_dataset_policy(items: list[RetrievalEvalItem]) -> None:
    if not items:
        raise ValueError("evidence packing experiment requires a non-empty dataset")
    locked_or_test_query_ids = [
        item.query.query_id
        for item in items
        if item.metadata.split == "test" or item.metadata.review_status == "locked"
    ]
    if locked_or_test_query_ids:
        raise ValueError(
            "evidence packing experiment must not use locked/test split for tuning "
            f"or public reports: {locked_or_test_query_ids[:5]}"
        )
    unreviewed_query_ids = [
        item.query.query_id
        for item in items
        if item.metadata.split in {"seed", "dev"}
        and item.metadata.review_status != "reviewed"
    ]
    if unreviewed_query_ids:
        raise ValueError(
            "evidence packing experiment requires reviewed seed/dev rows only: "
            f"{unreviewed_query_ids[:5]}"
        )


def _validate_artifact_policy(
    *,
    chunks_path: Path,
    dataset_path: Path,
    retrieval_results_path: Path,
    packing_rows_path: Path,
) -> None:
    for path in (chunks_path, dataset_path, retrieval_results_path, packing_rows_path):
        _validate_repository_private_data_boundary(path)
    private_input = any(
        is_repository_private_artifact_path(path)
        for path in (chunks_path, dataset_path, retrieval_results_path)
    )
    if private_input and not is_repository_private_write_path(packing_rows_path):
        raise ValueError("private evidence packing rows must be written under private_data")


def _validate_repository_private_data_boundary(path: Path) -> None:
    if has_private_data_segment(path) and not is_repository_private_artifact_path(path):
        raise ValueError("private_data artifact paths must stay under repository private_data")


def main() -> int:
    args = _parse_args()
    policies = [
        policy.strip()
        for policy in args.policies.split(",")
        if policy.strip()
    ]
    report = run_evidence_packing_experiment(
        chunks_path=args.chunks,
        dataset_path=args.dataset,
        retrieval_results_path=args.retrieval_results,
        packing_rows_path=args.packing_rows,
        report_path=args.report,
        policies=policies,
    )
    best = max(
        report.policy_summaries,
        key=lambda summary: (
            summary.target_parent_covered_rate,
            summary.target_child_covered_rate,
            summary.evidence_order_relevance_proxy,
        ),
    )
    failures = collect_public_retrieval_artifact_failures(report.output_quality)
    print(
        "evidence_packing "
        f"status={'PASS' if not failures else 'FAIL'} "
        f"policies={len(report.policy_summaries)} "
        f"best_policy={best.policy_id} "
        f"target_child_covered={best.target_child_covered_rate:.6f} "
        f"target_parent_covered={best.target_parent_covered_rate:.6f} "
        f"citation_recoverability={best.citation_recoverability_rate:.6f} "
        f"failures={len(failures)}"
    )
    return 0 if not failures else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run evidence packing comparison on fixed retrieval results."
    )
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS_PATH)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument(
        "--retrieval-results",
        type=Path,
        default=DEFAULT_RETRIEVAL_RESULTS_PATH,
    )
    parser.add_argument("--packing-rows", type=Path, default=DEFAULT_PACKING_ROWS_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--policies", type=str, default=",".join(DEFAULT_POLICIES))
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())

