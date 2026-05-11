from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from app.core.project_paths import (
    has_private_data_segment,
    is_repository_private_artifact_path,
    is_repository_private_write_path,
)
from app.domain.chunking import ChildChunk
from app.domain.retrieval import (
    RetrievalDocument,
    RetrievalEvalItem,
    RetrievalMethod,
    RetrievalRunResult,
    build_retrieval_document_from_child,
    load_retrieval_eval_jsonl,
)
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    RETRIEVAL_EXPERIMENT_REPORT_VERSION,
    RetrievalComparisonReport,
    RetrievalExperimentRun,
    build_public_retrieval_result_rows,
    build_retrieval_comparison_report,
    build_retrieval_experiment_run,
    build_retrieval_harness_report_markdown,
    collect_public_retrieval_artifact_failures,
    measure_public_retrieval_artifact_quality,
    write_public_retrieval_result_rows,
)
from app.infrastructure.index.bm25 import Bm25Retriever
from app.infrastructure.index.dense import DenseRetrievalConfig, DenseRetriever
from app.infrastructure.index.hybrid import HybridRetrievalConfig, HybridRetriever


DEFAULT_CHUNKS_PATH = Path("private_data") / "reports" / "parent_child_chunks.json"
DEFAULT_DATASET_PATH = Path("evals/datasets/retrieval_eval_seed.jsonl")
DEFAULT_RESULTS_DIR = Path("evals/results")
DEFAULT_REPORT_PATH = Path("evals/reports/retrieval_harness_report.md")
DEFAULT_NOTEBOOK_PATH = Path("notebooks/07_dense_hybrid_retrieval_comparison.ipynb")
DEFAULT_EMBEDDING_CACHE_DIR = Path("private_data") / "embeddings"
DEFAULT_TOP_K = 5
SUPPORTED_METHOD_KEYS: tuple[str, ...] = (
    "bm25",
    "dense",
    "hybrid_rrf",
    "hybrid_weighted",
    "hybrid_weighted_alpha_0_3",
    "hybrid_weighted_alpha_0_5",
    "hybrid_weighted_alpha_0_7",
)


@dataclass(frozen=True)
class _MethodPlan:
    method_key: str
    method: RetrievalMethod
    run_label: str
    hybrid_config: HybridRetrievalConfig | None = None


@dataclass(frozen=True)
class _MethodRunArtifacts:
    method_run: RetrievalExperimentRun
    result_rows: list[dict[str, object]]


@dataclass(frozen=True)
class _MethodExecution:
    results: list[RetrievalRunResult]
    method_config_summary: dict[str, str | int | float | bool]


def run_retrieval_experiment(
    *,
    chunks_path: Path = DEFAULT_CHUNKS_PATH,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    results_dir: Path = DEFAULT_RESULTS_DIR,
    report_path: Path = DEFAULT_REPORT_PATH,
    notebook_path: Path | None = DEFAULT_NOTEBOOK_PATH,
    methods: list[str] | None = None,
    top_k: int = DEFAULT_TOP_K,
    embedding_cache_dir: Path = DEFAULT_EMBEDDING_CACHE_DIR,
) -> RetrievalComparisonReport:
    method_plans = _build_method_plans(methods or ["bm25"])
    items = load_retrieval_eval_jsonl(dataset_path)
    _validate_dataset_policy(items=items)
    _validate_private_artifact_policy(
        chunks_path=chunks_path,
        dataset_path=dataset_path,
        results_dir=results_dir,
        embedding_cache_dir=embedding_cache_dir,
        method_plans=method_plans,
    )
    documents = load_retrieval_documents_from_chunks(chunks_path)
    artifacts = [
        _run_method(
            plan=plan,
            items=items,
            documents=documents,
            results_dir=results_dir,
            top_k=top_k,
            embedding_cache_dir=embedding_cache_dir,
        )
        for plan in method_plans
    ]
    result_rows = [
        row for artifact in artifacts for row in artifact.result_rows
    ]
    method_runs = [artifact.method_run for artifact in artifacts]
    provisional_quality = measure_public_retrieval_artifact_quality(
        report_version=RETRIEVAL_EXPERIMENT_REPORT_VERSION,
        run_id="pending",
        result_rows=result_rows,
        report_text="",
        extra_public_texts=_load_optional_public_texts([notebook_path]),
    )
    report = build_retrieval_comparison_report(
        dataset_path=dataset_path,
        method_runs=method_runs,
        output_quality=provisional_quality,
        baseline_method="bm25",
    )
    report_text = build_retrieval_harness_report_markdown(report)
    final_quality = measure_public_retrieval_artifact_quality(
        report_version=RETRIEVAL_EXPERIMENT_REPORT_VERSION,
        run_id=report.comparison_id,
        result_rows=result_rows,
        report_text=report_text,
        extra_public_texts=_load_optional_public_texts([notebook_path]),
    )
    report = report.model_copy(update={"output_quality": final_quality})
    report_text = build_retrieval_harness_report_markdown(report)
    _validate_public_output_quality(final_quality)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_text, encoding="utf-8")
    return report


def load_retrieval_documents_from_chunks(chunks_path: Path) -> list[RetrievalDocument]:
    payload = json.loads(chunks_path.read_text(encoding="utf-8"))
    children_payload = payload.get("children")
    if not isinstance(children_payload, list):
        raise ValueError("parent_child_chunks payload must include children list")
    documents: list[RetrievalDocument] = []
    for child_payload in children_payload:
        child = ChildChunk.model_validate(child_payload)
        if not child.text:
            continue
        documents.append(
            build_retrieval_document_from_child(child, include_private_text=True)
        )
    if not documents:
        raise ValueError("no searchable child chunks found")
    return documents


def _run_method(
    *,
    plan: _MethodPlan,
    items: list[RetrievalEvalItem],
    documents: list[RetrievalDocument],
    results_dir: Path,
    top_k: int,
    embedding_cache_dir: Path,
) -> _MethodRunArtifacts:
    execution = _execute_method(
        plan=plan,
        items=items,
        documents=documents,
        top_k=top_k,
        embedding_cache_dir=embedding_cache_dir,
    )
    result_path = results_dir / f"retrieval_experiment_{plan.run_label}_results.jsonl"
    method_run = build_retrieval_experiment_run(
        method=plan.method,
        run_label=plan.run_label,
        top_k=top_k,
        items=items,
        documents=documents,
        results=execution.results,
        result_path=result_path,
        method_config_summary=execution.method_config_summary,
    )
    result_rows = build_public_retrieval_result_rows(
        run_id=method_run.run_id,
        results=execution.results,
    )
    _validate_public_output_quality(
        measure_public_retrieval_artifact_quality(
            report_version=RETRIEVAL_EXPERIMENT_REPORT_VERSION,
            run_id=method_run.run_id,
            result_rows=result_rows,
            report_text="",
        )
    )
    write_public_retrieval_result_rows(path=result_path, rows=result_rows)
    return _MethodRunArtifacts(method_run=method_run, result_rows=result_rows)


def _execute_method(
    *,
    plan: _MethodPlan,
    items: list[RetrievalEvalItem],
    documents: list[RetrievalDocument],
    top_k: int,
    embedding_cache_dir: Path,
) -> _MethodExecution:
    method = plan.method
    if method == "bm25":
        retriever = Bm25Retriever.from_documents(documents)
        return _MethodExecution(
            results=[
                retriever.search(
                    query_id=item.query.query_id,
                    query_type=item.query.query_type,
                    query_text=item.query.query_text,
                    top_k=top_k,
                )
                for item in items
            ],
            method_config_summary=_method_config_summary(method=method, top_k=top_k),
        )
    if method == "dense":
        config = DenseRetrievalConfig()
        retriever = DenseRetriever.from_documents(
            documents,
            config=config,
            cache_dir=embedding_cache_dir,
        )
        return _MethodExecution(
            results=[
                retriever.search(
                    query_id=item.query.query_id,
                    query_type=item.query.query_type,
                    query_text=item.query.query_text,
                    top_k=top_k,
                )
                for item in items
            ],
            method_config_summary=config.to_method_config_summary(
                top_k=top_k,
                embedding_dim=retriever.embedding_dim,
            ),
        )
    if plan.hybrid_config is not None:
        retriever = HybridRetriever.from_documents(
            documents,
            config=plan.hybrid_config,
            dense_cache_dir=embedding_cache_dir,
        )
        return _MethodExecution(
            results=[
                retriever.search(
                    query_id=item.query.query_id,
                    query_type=item.query.query_type,
                    query_text=item.query.query_text,
                    top_k=top_k,
                )
                for item in items
            ],
            method_config_summary=plan.hybrid_config.to_method_config_summary(
                top_k=top_k,
                embedding_dim=retriever.embedding_dim,
            ),
        )
    raise ValueError(f"method is not implemented in retrieval experiment runner: {method}")


def _build_method_plans(methods: list[str]) -> list[_MethodPlan]:
    if not methods:
        raise ValueError("at least one retrieval method is required")
    unsupported = [method for method in methods if method not in SUPPORTED_METHOD_KEYS]
    if unsupported:
        raise ValueError(f"unsupported retrieval methods: {unsupported}")
    plans = [_method_plan_from_key(method) for method in methods]
    run_labels = [plan.run_label for plan in plans]
    if len(run_labels) != len(set(run_labels)):
        raise ValueError("retrieval method run labels must be unique")
    return plans


def _method_plan_from_key(method_key: str) -> _MethodPlan:
    if method_key == "bm25":
        return _MethodPlan(method_key=method_key, method="bm25", run_label="bm25")
    if method_key == "dense":
        return _MethodPlan(method_key=method_key, method="dense", run_label="dense")
    if method_key == "hybrid_rrf":
        return _MethodPlan(
            method_key=method_key,
            method="hybrid_rrf",
            run_label="hybrid_rrf",
            hybrid_config=HybridRetrievalConfig(method="hybrid_rrf"),
        )
    if method_key == "hybrid_weighted":
        return _weighted_hybrid_plan(method_key=method_key, alpha=0.5)
    if method_key == "hybrid_weighted_alpha_0_3":
        return _weighted_hybrid_plan(method_key=method_key, alpha=0.3)
    if method_key == "hybrid_weighted_alpha_0_5":
        return _weighted_hybrid_plan(method_key=method_key, alpha=0.5)
    if method_key == "hybrid_weighted_alpha_0_7":
        return _weighted_hybrid_plan(method_key=method_key, alpha=0.7)
    raise ValueError(f"unsupported retrieval methods: {[method_key]}")


def _weighted_hybrid_plan(*, method_key: str, alpha: float) -> _MethodPlan:
    alpha_label = str(alpha).replace(".", "_")
    return _MethodPlan(
        method_key=method_key,
        method="hybrid_weighted",
        run_label=f"hybrid_weighted_alpha_{alpha_label}",
        hybrid_config=HybridRetrievalConfig(method="hybrid_weighted", alpha=alpha),
    )


def _validate_public_output_quality(
    output_quality: PublicRetrievalArtifactQuality,
) -> None:
    failures = collect_public_retrieval_artifact_failures(output_quality)
    if failures:
        raise ValueError(f"retrieval public output gate failed: {failures}")


def _validate_dataset_policy(
    *,
    items: list[RetrievalEvalItem],
) -> None:
    if not items:
        raise ValueError("retrieval experiment requires a non-empty dataset")
    locked_or_test_query_ids = [
        item.query.query_id
        for item in items
        if item.metadata.split == "test" or item.metadata.review_status == "locked"
    ]
    if locked_or_test_query_ids:
        raise ValueError(
            "retrieval experiment must not use locked/test split for tuning "
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
            "retrieval experiment requires reviewed seed/dev rows only: "
            f"{unreviewed_query_ids[:5]}"
        )


def _validate_private_artifact_policy(
    *,
    chunks_path: Path,
    dataset_path: Path,
    results_dir: Path,
    embedding_cache_dir: Path,
    method_plans: list[_MethodPlan],
) -> None:
    for path in (chunks_path, dataset_path, results_dir, embedding_cache_dir):
        _validate_repository_private_data_boundary(path)
    private_dataset = is_repository_private_artifact_path(dataset_path)
    private_corpus = is_repository_private_artifact_path(chunks_path)
    if private_dataset and not is_repository_private_write_path(results_dir):
        raise ValueError("private retrieval dataset results must be written under private_data")
    if _uses_dense_index(method_plans) and (private_dataset or private_corpus):
        if not is_repository_private_write_path(embedding_cache_dir):
            raise ValueError(
                "private retrieval corpus embedding cache must be under private_data"
            )


def _uses_dense_index(method_plans: list[_MethodPlan]) -> bool:
    return any(plan.method in {"dense", "hybrid_rrf", "hybrid_weighted"} for plan in method_plans)


def _validate_repository_private_data_boundary(path: Path) -> None:
    if has_private_data_segment(path) and not is_repository_private_artifact_path(path):
        raise ValueError(
            "private_data artifact paths must stay under repository private_data"
        )


def _method_config_summary(
    *,
    method: RetrievalMethod,
    top_k: int,
) -> dict[str, str | int | float | bool]:
    if method == "bm25":
        return {
            "method": "bm25",
            "top_k": top_k,
            "tokenizer": "regex-ko-en-num/v1",
            "query_rewrite": False,
            "reranking": False,
        }
    return {"method": method, "top_k": top_k}


def _load_optional_public_texts(paths: list[Path | None]) -> dict[str, str]:
    texts: dict[str, str] = {}
    for path in paths:
        if path is not None and path.exists():
            for line_number, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(),
                start=1,
            ):
                texts[f"{path.as_posix()}:{line_number}"] = line
    return texts


def main() -> int:
    args = _parse_args()
    methods = [method.strip() for method in args.methods.split(",") if method.strip()]
    report = run_retrieval_experiment(
        chunks_path=args.chunks,
        dataset_path=args.dataset,
        results_dir=args.results_dir,
        report_path=args.report,
        notebook_path=args.notebook,
        methods=methods,
        top_k=args.top_k,
        embedding_cache_dir=args.embedding_cache_dir,
    )
    failures = collect_public_retrieval_artifact_failures(report.output_quality)
    primary_run = report.method_runs[0]
    metric = primary_run.metric_summary
    print(
        "retrieval_harness "
        f"status={'PASS' if not failures else 'FAIL'} "
        f"methods={','.join(run.run_label for run in report.method_runs)} "
        f"query_count={metric.query_count} "
        f"recall_at_5={metric.recall_at_5:.6f} "
        f"mrr={metric.mrr:.6f} "
        f"ndcg_at_5={metric.ndcg_at_5:.6f} "
        f"failures={len(failures)}"
    )
    return 0 if not failures else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run common retrieval evaluation harness."
    )
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS_PATH)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--notebook", type=Path, default=DEFAULT_NOTEBOOK_PATH)
    parser.add_argument("--methods", type=str, default="bm25")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument(
        "--embedding-cache-dir",
        type=Path,
        default=DEFAULT_EMBEDDING_CACHE_DIR,
    )
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
