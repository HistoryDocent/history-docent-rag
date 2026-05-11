from __future__ import annotations

import argparse
from pathlib import Path

from app.core.project_paths import (
    has_private_data_segment,
    is_repository_private_artifact_path,
)
from app.domain.retrieval import RetrievalEvalItem, load_retrieval_eval_jsonl
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    collect_public_retrieval_artifact_failures,
    load_public_retrieval_result_rows,
    measure_public_retrieval_artifact_quality,
)
from app.domain.retrieval_overlap import (
    RETRIEVAL_OVERLAP_REPORT_VERSION,
    RetrievalOverlapReport,
    build_overlap_analysis_id,
    build_overlap_query_rows,
    build_public_overlap_result_rows,
    build_retrieval_overlap_report,
    build_retrieval_overlap_report_markdown,
)
from pipelines.run_retrieval_experiment import (
    DEFAULT_CHUNKS_PATH,
    DEFAULT_EMBEDDING_CACHE_DIR,
    DEFAULT_TOP_K,
    run_retrieval_experiment,
)


DEFAULT_DATASET_PATH = Path("private_data") / "evals" / "datasets" / "retrieval_eval_dev.jsonl"
DEFAULT_RESULTS_DIR = Path("private_data") / "evals" / "results"
DEFAULT_HARNESS_REPORT_PATH = Path("evals") / "reports" / "dense_retrieval_baseline_report.md"
DEFAULT_OVERLAP_REPORT_PATH = Path("evals") / "reports" / "retrieval_overlap_analysis_report.md"
OVERLAP_METHODS = ("bm25", "dense")


def analyze_retrieval_overlap(
    *,
    chunks_path: Path = DEFAULT_CHUNKS_PATH,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    results_dir: Path = DEFAULT_RESULTS_DIR,
    report_path: Path = DEFAULT_OVERLAP_REPORT_PATH,
    harness_report_path: Path = DEFAULT_HARNESS_REPORT_PATH,
    embedding_cache_dir: Path = DEFAULT_EMBEDDING_CACHE_DIR,
    top_k: int = DEFAULT_TOP_K,
    execute_retrieval: bool = True,
) -> RetrievalOverlapReport:
    result_paths = [
        results_dir / f"retrieval_experiment_{method}_results.jsonl"
        for method in OVERLAP_METHODS
    ]
    _validate_overlap_artifact_policy(
        dataset_path=dataset_path,
        result_paths=result_paths,
    )
    if execute_retrieval:
        run_retrieval_experiment(
            chunks_path=chunks_path,
            dataset_path=dataset_path,
            results_dir=results_dir,
            report_path=harness_report_path,
            methods=list(OVERLAP_METHODS),
            top_k=top_k,
            embedding_cache_dir=embedding_cache_dir,
        )
    items = load_retrieval_eval_jsonl(dataset_path)
    _validate_dataset_policy(items)
    result_rows = _load_result_rows(result_paths)
    query_rows = build_overlap_query_rows(
        items=items,
        result_rows=result_rows,
        top_k=top_k,
    )
    analysis_id = build_overlap_analysis_id(
        items=items,
        result_rows=result_rows,
        top_k=top_k,
    )
    public_overlap_rows = build_public_overlap_result_rows(
        analysis_id=analysis_id,
        query_rows=query_rows,
    )
    provisional_quality = measure_public_retrieval_artifact_quality(
        report_version=RETRIEVAL_OVERLAP_REPORT_VERSION,
        run_id=analysis_id,
        result_rows=public_overlap_rows,
        report_text="",
    )
    report = build_retrieval_overlap_report(
        dataset_path=dataset_path,
        result_paths=result_paths,
        items=items,
        result_rows=result_rows,
        top_k=top_k,
        output_quality=provisional_quality,
    )
    report_text = build_retrieval_overlap_report_markdown(report)
    final_quality = measure_public_retrieval_artifact_quality(
        report_version=RETRIEVAL_OVERLAP_REPORT_VERSION,
        run_id=report.analysis_id,
        result_rows=public_overlap_rows,
        report_text=report_text,
    )
    _validate_public_output_quality(final_quality)
    report = report.model_copy(update={"output_quality": final_quality})
    report_text = build_retrieval_overlap_report_markdown(report)
    _validate_public_output_quality(final_quality)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_text, encoding="utf-8")
    return report


def _load_result_rows(result_paths: list[Path]) -> list[dict[str, object]]:
    result_rows: list[dict[str, object]] = []
    for path in result_paths:
        if not path.exists():
            raise ValueError(f"retrieval result file does not exist: {path}")
        result_rows.extend(load_public_retrieval_result_rows(path))
    return result_rows


def _validate_overlap_artifact_policy(
    *,
    dataset_path: Path,
    result_paths: list[Path],
) -> None:
    paths = [dataset_path, *result_paths]
    for path in paths:
        if has_private_data_segment(path) and not is_repository_private_artifact_path(path):
            raise ValueError(
                "private_data artifact paths must stay under repository private_data"
            )
    if is_repository_private_artifact_path(dataset_path):
        for result_path in result_paths:
            if not is_repository_private_artifact_path(result_path):
                raise ValueError(
                    "private retrieval dataset overlap inputs must use private_data results"
                )


def _validate_dataset_policy(items: list[RetrievalEvalItem]) -> None:
    if not items:
        raise ValueError("retrieval overlap analysis requires a non-empty dataset")
    locked_or_test_query_ids = [
        item.query.query_id
        for item in items
        if item.metadata.split == "test" or item.metadata.review_status == "locked"
    ]
    if locked_or_test_query_ids:
        raise ValueError(
            "retrieval overlap analysis must not use locked/test split "
            f"for tuning or public reports: {locked_or_test_query_ids[:5]}"
        )
    unreviewed_query_ids = [
        item.query.query_id
        for item in items
        if item.metadata.split in {"seed", "dev"}
        and item.metadata.review_status != "reviewed"
    ]
    if unreviewed_query_ids:
        raise ValueError(
            "retrieval overlap analysis requires reviewed seed/dev rows only: "
            f"{unreviewed_query_ids[:5]}"
        )


def _validate_public_output_quality(
    output_quality: PublicRetrievalArtifactQuality,
) -> None:
    failures = collect_public_retrieval_artifact_failures(output_quality)
    if failures:
        raise ValueError(f"retrieval overlap public output gate failed: {failures}")


def main() -> int:
    args = _parse_args()
    report = analyze_retrieval_overlap(
        chunks_path=args.chunks,
        dataset_path=args.dataset,
        results_dir=args.results_dir,
        report_path=args.report,
        harness_report_path=args.harness_report,
        embedding_cache_dir=args.embedding_cache_dir,
        top_k=args.top_k,
        execute_retrieval=not args.skip_retrieval,
    )
    failures = collect_public_retrieval_artifact_failures(report.output_quality)
    metric = report.metric_summary
    print(
        "retrieval_overlap "
        f"status={'PASS' if not failures else 'FAIL'} "
        f"query_count={metric.query_count} "
        f"dense_only_hit_count={metric.dense_only_hit_count} "
        f"oracle_union_recall_at_5={metric.oracle_union_recall_at_5:.6f} "
        f"oracle_union_delta_vs_bm25={metric.oracle_union_delta_vs_bm25:.6f} "
        f"hybrid_decision={report.hybrid_decision} "
        f"failures={len(failures)}"
    )
    return 0 if not failures else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze BM25-Dense retrieval complementarity."
    )
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS_PATH)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_OVERLAP_REPORT_PATH)
    parser.add_argument("--harness-report", type=Path, default=DEFAULT_HARNESS_REPORT_PATH)
    parser.add_argument(
        "--embedding-cache-dir",
        type=Path,
        default=DEFAULT_EMBEDDING_CACHE_DIR,
    )
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument(
        "--skip-retrieval",
        action="store_true",
        help="Use existing BM25/Dense result JSONL files instead of re-running retrieval.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
