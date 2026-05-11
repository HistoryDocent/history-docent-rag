from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from app.core.project_paths import (
    has_private_data_segment,
    is_repository_private_artifact_path,
    is_repository_private_write_path,
)
from app.application.query_rewrite import (
    PlaceAwareQueryRewriter,
    QueryRewriteConfig,
    QueryRewriteResult,
    summarize_query_rewrite_results,
)
from app.domain.chunking import ChildChunk
from app.domain.place_catalog import PlaceCatalog, load_place_catalog
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
from app.infrastructure.index.hybrid import (
    HybridFusionMethod,
    HybridRetrievalConfig,
    HybridRetriever,
)
from app.infrastructure.index.reranker import (
    CrossEncoderReranker,
    RerankerConfig,
    RerankingRetriever,
)


DEFAULT_CHUNKS_PATH = Path("private_data") / "reports" / "parent_child_chunks.json"
DEFAULT_DATASET_PATH = Path("evals/datasets/retrieval_eval_seed.jsonl")
DEFAULT_RESULTS_DIR = Path("evals/results")
DEFAULT_REPORT_PATH = Path("evals/reports/retrieval_harness_report.md")
DEFAULT_NOTEBOOK_PATH = Path("notebooks/07_dense_hybrid_retrieval_comparison.ipynb")
DEFAULT_EMBEDDING_CACHE_DIR = Path("private_data") / "embeddings"
DEFAULT_PLACE_CATALOG_PATH = Path("data_samples/place_catalog_seed.json")
DEFAULT_TOP_K = 5
SUPPORTED_METHOD_KEYS: tuple[str, ...] = (
    "bm25",
    "dense",
    "dense_bge_m3",
    "dense_multilingual_e5_small",
    "dense_multilingual_e5_large",
    "dense_multilingual_e5_large_instruct",
    "dense_paraphrase_multilingual_minilm",
    "hybrid_rrf",
    "hybrid_weighted",
    "hybrid_weighted_alpha_0_3",
    "hybrid_weighted_alpha_0_5",
    "hybrid_weighted_alpha_0_7",
    "hybrid_rrf_e5_small",
    "hybrid_weighted_e5_small_alpha_0_3",
    "hybrid_weighted_e5_small_alpha_0_5",
    "hybrid_rrf_bge_m3",
    "hybrid_weighted_bge_m3_alpha_0_3",
    "dense_multilingual_e5_small_rerank_bge_m3_top20",
    "dense_multilingual_e5_small_rerank_bge_m3_top30",
    "dense_multilingual_e5_small_rerank_bge_m3_top50",
    "dense_multilingual_e5_small_place_rewrite",
    "dense_multilingual_e5_small_voice_rewrite",
    "hybrid_weighted_e5_small_alpha_0_5_rerank_bge_m3_top20",
    "hybrid_weighted_e5_small_alpha_0_5_rerank_bge_m3_top30",
    "hybrid_weighted_e5_small_alpha_0_5_rerank_bge_m3_top50",
)


@dataclass(frozen=True)
class _MethodPlan:
    method_key: str
    method: RetrievalMethod
    run_label: str
    dense_config: DenseRetrievalConfig | None = None
    hybrid_config: HybridRetrievalConfig | None = None
    reranker_config: RerankerConfig | None = None
    query_rewrite_config: QueryRewriteConfig | None = None


@dataclass(frozen=True)
class _MethodRunArtifacts:
    method_run: RetrievalExperimentRun
    result_rows: list[dict[str, object]]


@dataclass(frozen=True)
class _MethodExecution:
    results: list[RetrievalRunResult]
    method_config_summary: dict[str, str | int | float | bool]


@dataclass
class _ExecutionContext:
    bm25_retriever: Bm25Retriever | None = None
    dense_retrievers: dict[str, DenseRetriever] = field(default_factory=dict)
    rerankers: dict[str, CrossEncoderReranker] = field(default_factory=dict)
    place_catalogs: dict[str, PlaceCatalog] = field(default_factory=dict)


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
    place_catalog_path: Path = DEFAULT_PLACE_CATALOG_PATH,
) -> RetrievalComparisonReport:
    method_plans = _build_method_plans(methods or ["bm25"])
    items = load_retrieval_eval_jsonl(dataset_path)
    _validate_dataset_policy(items=items)
    _validate_private_artifact_policy(
        chunks_path=chunks_path,
        dataset_path=dataset_path,
        results_dir=results_dir,
        embedding_cache_dir=embedding_cache_dir,
        place_catalog_path=place_catalog_path,
        method_plans=method_plans,
    )
    documents = load_retrieval_documents_from_chunks(chunks_path)
    execution_context = _ExecutionContext()
    artifacts: list[_MethodRunArtifacts] = []
    for plan in method_plans:
        artifacts.append(
            _run_method(
                plan=plan,
                items=items,
                documents=documents,
                results_dir=results_dir,
                top_k=top_k,
                embedding_cache_dir=embedding_cache_dir,
                place_catalog_path=place_catalog_path,
                execution_context=execution_context,
            )
        )
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
    place_catalog_path: Path,
    execution_context: _ExecutionContext,
) -> _MethodRunArtifacts:
    execution = _execute_method(
        plan=plan,
        items=items,
        documents=documents,
        top_k=top_k,
        embedding_cache_dir=embedding_cache_dir,
        place_catalog_path=place_catalog_path,
        execution_context=execution_context,
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
    place_catalog_path: Path,
    execution_context: _ExecutionContext,
) -> _MethodExecution:
    method = plan.method
    if plan.reranker_config is not None:
        return _execute_reranked_method(
            plan=plan,
            items=items,
            documents=documents,
            top_k=top_k,
            embedding_cache_dir=embedding_cache_dir,
            place_catalog_path=place_catalog_path,
            execution_context=execution_context,
        )
    if method == "bm25":
        retriever = _get_bm25_retriever(
            execution_context=execution_context,
            documents=documents,
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
            method_config_summary=_method_config_summary(method=method, top_k=top_k),
        )
    if method == "dense":
        config = plan.dense_config or DenseRetrievalConfig()
        retriever = _get_dense_retriever(
            execution_context=execution_context,
            documents=documents,
            config=config,
            embedding_cache_dir=embedding_cache_dir,
        )
        rewrites = _rewrite_items_if_needed(
            plan=plan,
            items=items,
            place_catalog_path=place_catalog_path,
            execution_context=execution_context,
        )
        return _MethodExecution(
            results=[
                _search_with_optional_rewrite(
                    retriever=retriever,
                    item=item,
                    rewrite=rewrite,
                    top_k=top_k,
                )
                for item, rewrite in zip(items, rewrites, strict=True)
            ],
            method_config_summary=_with_query_rewrite_summary(
                config.to_method_config_summary(
                    top_k=top_k,
                    embedding_dim=retriever.embedding_dim,
                ),
                plan=plan,
                rewrites=rewrites,
            ),
        )
    if plan.hybrid_config is not None:
        dense_retriever = _get_dense_retriever(
            execution_context=execution_context,
            documents=documents,
            config=plan.hybrid_config.dense_config,
            embedding_cache_dir=embedding_cache_dir,
        )
        retriever = HybridRetriever(
            documents=tuple(documents),
            bm25_retriever=_get_bm25_retriever(
                execution_context=execution_context,
                documents=documents,
            ),
            dense_retriever=dense_retriever,
            config=plan.hybrid_config,
        )
        rewrites = _rewrite_items_if_needed(
            plan=plan,
            items=items,
            place_catalog_path=place_catalog_path,
            execution_context=execution_context,
        )
        return _MethodExecution(
            results=[
                _search_with_optional_rewrite(
                    retriever=retriever,
                    item=item,
                    rewrite=rewrite,
                    top_k=top_k,
                )
                for item, rewrite in zip(items, rewrites, strict=True)
            ],
            method_config_summary=_with_query_rewrite_summary(
                plan.hybrid_config.to_method_config_summary(
                    top_k=top_k,
                    embedding_dim=retriever.embedding_dim,
                ),
                plan=plan,
                rewrites=rewrites,
            ),
        )
    raise ValueError(f"method is not implemented in retrieval experiment runner: {method}")


def _search_with_optional_rewrite(
    *,
    retriever: DenseRetriever | HybridRetriever,
    item: RetrievalEvalItem,
    rewrite: QueryRewriteResult | None,
    top_k: int,
) -> RetrievalRunResult:
    query_text = rewrite.rewritten_query_text if rewrite is not None else item.query.query_text
    result = retriever.search(
        query_id=item.query.query_id,
        query_type=item.query.query_type,
        query_text=query_text,
        top_k=top_k,
    )
    if rewrite is None:
        return result
    return result.model_copy(
        update={"latency_ms": round(result.latency_ms + rewrite.latency_ms, 6)}
    )


def _rewrite_items_if_needed(
    *,
    plan: _MethodPlan,
    items: list[RetrievalEvalItem],
    place_catalog_path: Path,
    execution_context: _ExecutionContext,
) -> list[QueryRewriteResult | None]:
    if plan.query_rewrite_config is None:
        return [None for _item in items]
    catalog = _get_place_catalog(
        execution_context=execution_context,
        place_catalog_path=place_catalog_path,
    )
    rewriter = PlaceAwareQueryRewriter(
        catalog=catalog,
        config=plan.query_rewrite_config,
    )
    return [rewriter.rewrite(item) for item in items]


def _with_query_rewrite_summary(
    method_config_summary: dict[str, str | int | float | bool],
    *,
    plan: _MethodPlan,
    rewrites: list[QueryRewriteResult | None],
) -> dict[str, str | int | float | bool]:
    if plan.query_rewrite_config is None:
        return method_config_summary
    rewrite_results = [rewrite for rewrite in rewrites if rewrite is not None]
    return {
        **method_config_summary,
        **summarize_query_rewrite_results(
            config=plan.query_rewrite_config,
            results=rewrite_results,
        ),
    }


def _execute_reranked_method(
    *,
    plan: _MethodPlan,
    items: list[RetrievalEvalItem],
    documents: list[RetrievalDocument],
    top_k: int,
    embedding_cache_dir: Path,
    place_catalog_path: Path,
    execution_context: _ExecutionContext,
) -> _MethodExecution:
    config = plan.reranker_config
    if config is None:
        raise ValueError("reranked method requires reranker_config")
    if plan.method == "dense":
        dense_config = plan.dense_config or DenseRetrievalConfig()
        base_retriever = _get_dense_retriever(
            execution_context=execution_context,
            documents=documents,
            config=dense_config,
            embedding_cache_dir=embedding_cache_dir,
        )
        base_summary = dense_config.to_method_config_summary(
            top_k=config.candidate_k,
            embedding_dim=base_retriever.embedding_dim,
        )
    elif plan.hybrid_config is not None:
        dense_retriever = _get_dense_retriever(
            execution_context=execution_context,
            documents=documents,
            config=plan.hybrid_config.dense_config,
            embedding_cache_dir=embedding_cache_dir,
        )
        base_retriever = HybridRetriever(
            documents=tuple(documents),
            bm25_retriever=_get_bm25_retriever(
                execution_context=execution_context,
                documents=documents,
            ),
            dense_retriever=dense_retriever,
            config=plan.hybrid_config,
        )
        base_summary = plan.hybrid_config.to_method_config_summary(
            top_k=config.candidate_k,
            embedding_dim=base_retriever.embedding_dim,
        )
    else:
        raise ValueError("reranked method requires dense_config or hybrid_config")
    reranked_retriever = RerankingRetriever(
        documents=tuple(documents),
        base_retriever=base_retriever,
        base_method=plan.method,
        reranker=_get_reranker(
            execution_context=execution_context,
            config=config,
        ),
        config=config,
    )
    rewrites = _rewrite_items_if_needed(
        plan=plan,
        items=items,
        place_catalog_path=place_catalog_path,
        execution_context=execution_context,
    )
    return _MethodExecution(
        results=[
            _search_reranked_with_optional_rewrite(
                reranked_retriever=reranked_retriever,
                item=item,
                rewrite=rewrite,
                top_k=top_k,
            )
            for item, rewrite in zip(items, rewrites, strict=True)
        ],
        method_config_summary=_with_query_rewrite_summary(
            config.to_method_config_summary(
                base_summary=base_summary,
                top_k=top_k,
                base_run_label=_base_run_label_for_reranked_plan(plan),
            ),
            plan=plan,
            rewrites=rewrites,
        ),
    )


def _search_reranked_with_optional_rewrite(
    *,
    reranked_retriever: RerankingRetriever,
    item: RetrievalEvalItem,
    rewrite: QueryRewriteResult | None,
    top_k: int,
) -> RetrievalRunResult:
    query_text = rewrite.rewritten_query_text if rewrite is not None else item.query.query_text
    result = reranked_retriever.search(
        query_id=item.query.query_id,
        query_type=item.query.query_type,
        query_text=query_text,
        top_k=top_k,
    )
    if rewrite is None:
        return result
    return result.model_copy(
        update={"latency_ms": round(result.latency_ms + rewrite.latency_ms, 6)}
    )


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
    if method_key == "dense_bge_m3":
        return _neural_dense_plan(
            method_key=method_key,
            encoder_id="bge-m3",
            model_name="BAAI/bge-m3",
        )
    if method_key == "dense_multilingual_e5_small":
        return _neural_dense_plan(
            method_key=method_key,
            encoder_id="multilingual-e5-small",
            model_name="intfloat/multilingual-e5-small",
            query_prefix="query: ",
            document_prefix="passage: ",
        )
    if method_key == "dense_multilingual_e5_large":
        return _neural_dense_plan(
            method_key=method_key,
            encoder_id="multilingual-e5-large",
            model_name="intfloat/multilingual-e5-large",
            query_prefix="query: ",
            document_prefix="passage: ",
            batch_size=8,
        )
    if method_key == "dense_multilingual_e5_large_instruct":
        return _neural_dense_plan(
            method_key=method_key,
            encoder_id="multilingual-e5-large-instruct",
            model_name="intfloat/multilingual-e5-large-instruct",
            query_prefix="Instruct: Given a web search query, retrieve relevant passages that answer the query\nQuery: ",
            document_prefix="",
            batch_size=8,
        )
    if method_key == "dense_paraphrase_multilingual_minilm":
        return _neural_dense_plan(
            method_key=method_key,
            encoder_id="paraphrase-multilingual-minilm-l12-v2",
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        )
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
    if method_key == "hybrid_rrf_e5_small":
        return _hybrid_plan_with_dense_config(
            method_key=method_key,
            method="hybrid_rrf",
            dense_config=_e5_small_dense_config(),
        )
    if method_key == "hybrid_weighted_e5_small_alpha_0_3":
        return _hybrid_plan_with_dense_config(
            method_key=method_key,
            method="hybrid_weighted",
            dense_config=_e5_small_dense_config(),
            alpha=0.3,
        )
    if method_key == "hybrid_weighted_e5_small_alpha_0_5":
        return _hybrid_plan_with_dense_config(
            method_key=method_key,
            method="hybrid_weighted",
            dense_config=_e5_small_dense_config(),
            alpha=0.5,
        )
    if method_key == "hybrid_rrf_bge_m3":
        return _hybrid_plan_with_dense_config(
            method_key=method_key,
            method="hybrid_rrf",
            dense_config=_bge_m3_dense_config(),
        )
    if method_key == "hybrid_weighted_bge_m3_alpha_0_3":
        return _hybrid_plan_with_dense_config(
            method_key=method_key,
            method="hybrid_weighted",
            dense_config=_bge_m3_dense_config(),
            alpha=0.3,
        )
    if method_key == "dense_multilingual_e5_small_rerank_bge_m3_top20":
        return _reranked_dense_plan(method_key=method_key, candidate_k=20)
    if method_key == "dense_multilingual_e5_small_rerank_bge_m3_top30":
        return _reranked_dense_plan(method_key=method_key, candidate_k=30)
    if method_key == "dense_multilingual_e5_small_rerank_bge_m3_top50":
        return _reranked_dense_plan(method_key=method_key, candidate_k=50)
    if method_key == "dense_multilingual_e5_small_place_rewrite":
        return _MethodPlan(
            method_key=method_key,
            method="dense",
            run_label=method_key,
            dense_config=_e5_small_dense_config(),
            query_rewrite_config=QueryRewriteConfig(),
        )
    if method_key == "dense_multilingual_e5_small_voice_rewrite":
        return _MethodPlan(
            method_key=method_key,
            method="dense",
            run_label=method_key,
            dense_config=_e5_small_dense_config(),
            query_rewrite_config=QueryRewriteConfig(
                strategy_id="voice-followup-deterministic-v1",
                target_query_types=("voice_followup",),
            ),
        )
    if method_key == "hybrid_weighted_e5_small_alpha_0_5_rerank_bge_m3_top20":
        return _reranked_hybrid_plan(method_key=method_key, candidate_k=20)
    if method_key == "hybrid_weighted_e5_small_alpha_0_5_rerank_bge_m3_top30":
        return _reranked_hybrid_plan(method_key=method_key, candidate_k=30)
    if method_key == "hybrid_weighted_e5_small_alpha_0_5_rerank_bge_m3_top50":
        return _reranked_hybrid_plan(method_key=method_key, candidate_k=50)
    raise ValueError(f"unsupported retrieval methods: {[method_key]}")


def _neural_dense_plan(
    *,
    method_key: str,
    encoder_id: str,
    model_name: str,
    query_prefix: str = "",
    document_prefix: str = "",
    batch_size: int = 16,
) -> _MethodPlan:
    return _MethodPlan(
        method_key=method_key,
        method="dense",
        run_label=method_key,
        dense_config=DenseRetrievalConfig(
            encoder_id=encoder_id,
            backend="sentence_transformers",
            model_name=model_name,
            batch_size=batch_size,
            query_prefix=query_prefix,
            document_prefix=document_prefix,
        ),
    )


def _e5_small_dense_config() -> DenseRetrievalConfig:
    return DenseRetrievalConfig(
        encoder_id="multilingual-e5-small",
        backend="sentence_transformers",
        model_name="intfloat/multilingual-e5-small",
        query_prefix="query: ",
        document_prefix="passage: ",
    )


def _bge_m3_dense_config() -> DenseRetrievalConfig:
    return DenseRetrievalConfig(
        encoder_id="bge-m3",
        backend="sentence_transformers",
        model_name="BAAI/bge-m3",
    )


def _weighted_hybrid_plan(*, method_key: str, alpha: float) -> _MethodPlan:
    alpha_label = str(alpha).replace(".", "_")
    return _MethodPlan(
        method_key=method_key,
        method="hybrid_weighted",
        run_label=f"hybrid_weighted_alpha_{alpha_label}",
        hybrid_config=HybridRetrievalConfig(method="hybrid_weighted", alpha=alpha),
    )


def _hybrid_plan_with_dense_config(
    *,
    method_key: str,
    method: HybridFusionMethod,
    dense_config: DenseRetrievalConfig,
    alpha: float = 0.5,
) -> _MethodPlan:
    return _MethodPlan(
        method_key=method_key,
        method=method,
        run_label=method_key,
        hybrid_config=HybridRetrievalConfig(
            method=method,
            alpha=alpha,
            dense_config=dense_config,
        ),
    )


def _reranked_dense_plan(*, method_key: str, candidate_k: int) -> _MethodPlan:
    return _MethodPlan(
        method_key=method_key,
        method="dense",
        run_label=method_key,
        dense_config=_e5_small_dense_config(),
        reranker_config=_bge_reranker_config(candidate_k=candidate_k),
    )


def _reranked_hybrid_plan(*, method_key: str, candidate_k: int) -> _MethodPlan:
    return _MethodPlan(
        method_key=method_key,
        method="hybrid_weighted",
        run_label=method_key,
        hybrid_config=HybridRetrievalConfig(
            method="hybrid_weighted",
            alpha=0.5,
            dense_config=_e5_small_dense_config(),
        ),
        reranker_config=_bge_reranker_config(candidate_k=candidate_k),
    )


def _bge_reranker_config(*, candidate_k: int) -> RerankerConfig:
    return RerankerConfig(candidate_k=candidate_k)


def _get_bm25_retriever(
    *,
    execution_context: _ExecutionContext,
    documents: list[RetrievalDocument],
) -> Bm25Retriever:
    if execution_context.bm25_retriever is None:
        execution_context.bm25_retriever = Bm25Retriever.from_documents(documents)
    return execution_context.bm25_retriever


def _get_dense_retriever(
    *,
    execution_context: _ExecutionContext,
    documents: list[RetrievalDocument],
    config: DenseRetrievalConfig,
    embedding_cache_dir: Path,
) -> DenseRetriever:
    cache_key = _dense_config_cache_key(config)
    retriever = execution_context.dense_retrievers.get(cache_key)
    if retriever is None:
        retriever = DenseRetriever.from_documents(
            documents,
            config=config,
            cache_dir=embedding_cache_dir,
        )
        execution_context.dense_retrievers[cache_key] = retriever
    return retriever


def _dense_config_cache_key(config: DenseRetrievalConfig) -> str:
    return json.dumps(asdict(config), ensure_ascii=False, sort_keys=True)


def _get_reranker(
    *,
    execution_context: _ExecutionContext,
    config: RerankerConfig,
) -> CrossEncoderReranker:
    cache_key = _reranker_model_cache_key(config)
    reranker = execution_context.rerankers.get(cache_key)
    if reranker is None:
        reranker = CrossEncoderReranker.from_config(config)
        execution_context.rerankers[cache_key] = reranker
    return reranker


def _get_place_catalog(
    *,
    execution_context: _ExecutionContext,
    place_catalog_path: Path,
) -> PlaceCatalog:
    cache_key = str(place_catalog_path.resolve())
    catalog = execution_context.place_catalogs.get(cache_key)
    if catalog is None:
        catalog = load_place_catalog(place_catalog_path)
        execution_context.place_catalogs[cache_key] = catalog
    return catalog


def _reranker_model_cache_key(config: RerankerConfig) -> str:
    payload = {
        "backend": config.backend,
        "model_name": config.model_name,
        "device": config.device,
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _base_run_label_for_reranked_plan(plan: _MethodPlan) -> str:
    if plan.dense_config is not None:
        if plan.dense_config.encoder_id == "multilingual-e5-small":
            return "dense_multilingual_e5_small"
        return f"dense_{plan.dense_config.encoder_id}"
    if plan.hybrid_config is not None:
        if (
            plan.hybrid_config.method == "hybrid_weighted"
            and plan.hybrid_config.alpha == 0.5
            and plan.hybrid_config.dense_config.encoder_id == "multilingual-e5-small"
        ):
            return "hybrid_weighted_e5_small_alpha_0_5"
        return plan.hybrid_config.method
    return plan.method


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
    place_catalog_path: Path,
    method_plans: list[_MethodPlan],
) -> None:
    for path in (
        chunks_path,
        dataset_path,
        results_dir,
        embedding_cache_dir,
        place_catalog_path,
    ):
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
        place_catalog_path=args.place_catalog,
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
    parser.add_argument(
        "--place-catalog",
        type=Path,
        default=DEFAULT_PLACE_CATALOG_PATH,
    )
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
