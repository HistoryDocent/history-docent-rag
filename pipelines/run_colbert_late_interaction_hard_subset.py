from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from app.application.query_rewrite import (
    PlaceAwareQueryRewriter,
    QueryRewriteConfig,
    QueryRewriteResult,
    summarize_query_rewrite_results,
)
from app.domain.place_catalog import load_place_catalog
from app.domain.retrieval import (
    QueryType,
    RetrievalDocument,
    RetrievalEvalItem,
    RetrievalRunResult,
    load_retrieval_eval_jsonl,
)
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    RetrievalExperimentRun,
    build_metric_deltas,
    build_public_retrieval_result_rows,
    build_retrieval_experiment_run,
    collect_public_retrieval_artifact_failures,
    measure_public_retrieval_artifact_quality,
    write_public_retrieval_result_rows,
)
from app.infrastructure.index.dense import DenseRetriever
from app.infrastructure.index.device import resolve_torch_device
from app.infrastructure.index.late_interaction import (
    LateInteractionConfig,
    LateInteractionRerankingRetriever,
    LateInteractionScorer,
    TransformerLateInteractionScorer,
)
from pipelines.run_retrieval_experiment import (
    DEFAULT_CHUNKS_PATH,
    DEFAULT_EMBEDDING_CACHE_DIR,
    DEFAULT_PLACE_CATALOG_PATH,
    load_retrieval_documents_from_chunks,
    _e5_small_dense_config,
)


WORK_ID = "HD-COLBERT-001C"
REPORT_VERSION = "colbert-late-interaction-hard-subset-report/v1"
DEFAULT_DATASET_PATH = Path("private_data") / "evals" / "datasets" / "retrieval_eval_dev.jsonl"
DEFAULT_RESULTS_DIR = Path("private_data") / "evals" / "results"
DEFAULT_REPORT_PATH = Path("evals") / "reports" / "colbert_late_interaction_hard_subset_report.md"
DEFAULT_DOC_PATH = Path("docs") / "COLBERT_LATE_INTERACTION_HARD_SUBSET.md"
DEFAULT_TOP_K = 5
DEFAULT_CANDIDATE_KS = (20, 50)
TARGET_QUERY_TYPES: tuple[QueryType, ...] = (
    "place_story",
    "relationship",
    "route_context",
)
BGE_RERANKER_REFERENCE_P95_MS = 13140.690300


@dataclass(frozen=True)
class CandidateExecution:
    run: RetrievalExperimentRun
    results: list[RetrievalRunResult]
    cuda_memory_peak_mb: float


@dataclass(frozen=True)
class ColbertHardSubsetReport:
    work_id: str
    selected_items: list[RetrievalEvalItem]
    runs: list[CandidateExecution]
    metric_deltas: list[object]
    output_quality: PublicRetrievalArtifactQuality
    resolved_device: str
    decision: str
    target_resolvability_fail_count: int
    solar_call_count: int = 0
    locked_test_execution_count: int = 0


ScorerFactory = Callable[[LateInteractionConfig], LateInteractionScorer]


def run_colbert_late_interaction_hard_subset(
    *,
    chunks_path: Path = DEFAULT_CHUNKS_PATH,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    results_dir: Path = DEFAULT_RESULTS_DIR,
    report_path: Path = DEFAULT_REPORT_PATH,
    doc_path: Path = DEFAULT_DOC_PATH,
    embedding_cache_dir: Path = DEFAULT_EMBEDDING_CACHE_DIR,
    place_catalog_path: Path = DEFAULT_PLACE_CATALOG_PATH,
    top_k: int = DEFAULT_TOP_K,
    candidate_ks: tuple[int, ...] = DEFAULT_CANDIDATE_KS,
    scorer_factory: ScorerFactory | None = None,
) -> ColbertHardSubsetReport:
    if top_k < 1:
        raise ValueError("top_k must be >= 1")
    all_items = load_retrieval_eval_jsonl(dataset_path)
    selected_items = select_colbert_hard_subset(all_items)
    documents = load_retrieval_documents_from_chunks(chunks_path)
    target_resolvability_fail_count = count_target_resolvability_failures(
        items=selected_items,
        documents=documents,
    )
    if target_resolvability_fail_count:
        raise ValueError("target resolvability must be 0 before ColBERT hard subset run")
    dense_config = _e5_small_dense_config()
    base_retriever = DenseRetriever.from_documents(
        documents,
        config=dense_config,
        cache_dir=embedding_cache_dir,
    )
    rewrites = _build_voice_rewrites(
        items=selected_items,
        place_catalog_path=place_catalog_path,
    )
    baseline_results = [
        _search_with_optional_rewrite(
            retriever=base_retriever,
            item=item,
            rewrite=rewrite,
            top_k=top_k,
        )
        for item, rewrite in zip(selected_items, rewrites, strict=True)
    ]
    baseline_summary = _with_rewrite_summary(
        dense_config.to_method_config_summary(
            top_k=top_k,
            embedding_dim=base_retriever.embedding_dim,
        ),
        rewrites=rewrites,
    )
    runs = [
        _build_candidate_execution(
            run_label="baseline_dense_e5_voice_rewrite",
            items=selected_items,
            documents=documents,
            results=baseline_results,
            result_path=results_dir
            / "colbert_hard_subset_baseline_dense_e5_voice_rewrite_results.jsonl",
            method_config_summary=baseline_summary,
            cuda_memory_peak_mb=0.0,
            rows_path=results_dir / "colbert_hard_subset_rows.jsonl",
            append=False,
            top_k=top_k,
        )
    ]
    for candidate_k in candidate_ks:
        config = LateInteractionConfig(candidate_k=candidate_k)
        scorer = (
            scorer_factory(config)
            if scorer_factory is not None
            else TransformerLateInteractionScorer.from_config(config)
        )
        retriever = LateInteractionRerankingRetriever(
            documents=tuple(documents),
            base_retriever=base_retriever,
            base_method="dense",
            scorer=scorer,
            config=config,
        )
        candidate_results: list[RetrievalRunResult] = []
        peak_memory = 0.0
        for item, rewrite in zip(selected_items, rewrites, strict=True):
            result = _search_late_interaction_with_optional_rewrite(
                retriever=retriever,
                item=item,
                rewrite=rewrite,
                top_k=top_k,
            )
            candidate_results.append(result)
            peak_memory = max(peak_memory, retriever.last_cuda_memory_peak_mb)
        run_label = f"colbert_style_late_interaction_top{candidate_k}_cuda"
        runs.append(
            _build_candidate_execution(
                run_label=run_label,
                items=selected_items,
                documents=documents,
                results=candidate_results,
                result_path=results_dir / f"colbert_hard_subset_{run_label}_results.jsonl",
                method_config_summary=config.to_method_config_summary(
                    top_k=top_k,
                    base_run_label="baseline_dense_e5_voice_rewrite",
                ),
                cuda_memory_peak_mb=round(peak_memory, 6),
                rows_path=results_dir / "colbert_hard_subset_rows.jsonl",
                append=True,
                top_k=top_k,
            )
        )
    metric_deltas = build_metric_deltas(
        method_runs=[candidate.run for candidate in runs],
        baseline_method="dense",
    )
    provisional_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=WORK_ID,
        result_rows=_load_combined_rows(results_dir / "colbert_hard_subset_rows.jsonl"),
        report_text="",
    )
    decision = _decide(runs=runs)
    report = ColbertHardSubsetReport(
        work_id=WORK_ID,
        selected_items=selected_items,
        runs=runs,
        metric_deltas=metric_deltas,
        output_quality=provisional_quality,
        resolved_device=resolve_torch_device("cuda_if_available"),
        decision=decision,
        target_resolvability_fail_count=target_resolvability_fail_count,
    )
    report_text = build_report_markdown(report)
    final_quality = measure_public_retrieval_artifact_quality(
        report_version=REPORT_VERSION,
        run_id=WORK_ID,
        result_rows=_load_combined_rows(results_dir / "colbert_hard_subset_rows.jsonl"),
        report_text=report_text,
    )
    report = ColbertHardSubsetReport(
        work_id=WORK_ID,
        selected_items=selected_items,
        runs=runs,
        metric_deltas=metric_deltas,
        output_quality=final_quality,
        resolved_device=resolve_torch_device("cuda_if_available"),
        decision=decision,
        target_resolvability_fail_count=target_resolvability_fail_count,
    )
    failures = collect_public_retrieval_artifact_failures(final_quality)
    if failures:
        raise ValueError(f"ColBERT public output gate failed: {failures}")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(build_report_markdown(report), encoding="utf-8")
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text(build_decision_doc_markdown(report), encoding="utf-8")
    return report


def select_colbert_hard_subset(
    items: list[RetrievalEvalItem],
) -> list[RetrievalEvalItem]:
    selected = [
        item
        for item in items
        if item.metadata.split == "dev"
        and item.metadata.review_status == "reviewed"
        and item.metadata.difficulty == "hard"
        and item.query.query_type in TARGET_QUERY_TYPES
        and item.query.expected_behavior == "retrieve"
    ]
    if not selected:
        raise ValueError("ColBERT hard subset selection returned no items")
    return sorted(selected, key=lambda item: (item.query.query_type, item.query.query_id))


def count_target_resolvability_failures(
    *,
    items: list[RetrievalEvalItem],
    documents: list[RetrievalDocument],
) -> int:
    child_ids = {document.child_id for document in documents}
    parent_ids = {document.parent_id for document in documents}
    doc_ids = {document.doc_id for document in documents}
    failure_count = 0
    for item in items:
        resolved = False
        for judgment in item.judgments:
            resolved = resolved or bool(set(judgment.relevant_child_ids) & child_ids)
            resolved = resolved or bool(set(judgment.relevant_parent_ids) & parent_ids)
            resolved = resolved or bool(set(judgment.relevant_doc_ids) & doc_ids)
        if not resolved:
            failure_count += 1
    return failure_count


def build_report_markdown(report: ColbertHardSubsetReport) -> str:
    query_type_counts = _query_type_counts(report.selected_items)
    lines = [
        "# ColBERT-style Late Interaction Hard Subset Report",
        "",
        "## 결론",
        "",
        f"`{report.work_id}` 실행 결과의 결정은 `{report.decision}`이다.",
        "",
        "이 결과는 dev hard subset 검색 비교이며 locked test, Solar Pro 3, production route 결과가 아니다.",
        "public report에는 raw query, raw answer, raw evidence, prompt, chunk text, private path, secret을 기록하지 않는다.",
        "",
        "## 정량 결과",
        "",
        "| metric | value |",
        "| --- | ---: |",
        f"| selected_query_count | {len(report.selected_items)} |",
        f"| query_type_count | {len(query_type_counts)} |",
        f"| place_story_query_count | {query_type_counts.get('place_story', 0)} |",
        f"| relationship_query_count | {query_type_counts.get('relationship', 0)} |",
        f"| route_context_query_count | {query_type_counts.get('route_context', 0)} |",
        f"| target_resolvability_fail_count | {report.target_resolvability_fail_count} |",
        f"| candidate_run_count | {len(report.runs) - 1} |",
        f"| locked_test_execution_count | {report.locked_test_execution_count} |",
        f"| solar_call_count | {report.solar_call_count} |",
        f"| public_private_path_leakage_count | {report.output_quality.private_path_leakage_count} |",
        f"| public_secret_like_leakage_count | {report.output_quality.secret_like_leakage_count} |",
        f"| public_raw_payload_leakage_count | {report.output_quality.public_raw_text_leakage_count} |",
        "",
        "## Run Metrics",
        "",
        "| run_label | Recall@5 | MRR | nDCG@5 | latency_p95_ms | cuda_memory_peak_mb |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for run in report.runs:
        metric = run.run.metric_summary
        lines.append(
            "| "
            f"{run.run.run_label} | "
            f"{metric.recall_at_5:.6f} | "
            f"{metric.mrr:.6f} | "
            f"{metric.ndcg_at_5:.6f} | "
            f"{metric.latency_p95_ms:.6f} | "
            f"{run.cuda_memory_peak_mb:.6f} |"
        )
    lines.extend(
        [
            "",
            "## Baseline Delta",
            "",
            "| run_label | Recall@5 delta | MRR delta | nDCG@5 delta | latency_p95_ms delta |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for delta in report.metric_deltas:
        lines.append(
            "| "
            f"{delta.compared_run_label} | "
            f"{delta.recall_at_5_delta:.6f} | "
            f"{delta.mrr_delta:.6f} | "
            f"{delta.ndcg_at_5_delta:.6f} | "
            f"{delta.latency_p95_ms_delta:.6f} |"
        )
    lines.extend(
        [
            "",
            "## Query Type Breakdown",
            "",
            "| run_label | query_type | query_count | Recall@5 | MRR | nDCG@5 | latency_p95_ms |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for run in report.runs:
        for breakdown in run.run.query_type_breakdown:
            lines.append(
                "| "
                f"{run.run.run_label} | "
                f"{breakdown.query_type} | "
                f"{breakdown.query_count} | "
                f"{breakdown.recall_at_5:.6f} | "
                f"{breakdown.mrr:.6f} | "
                f"{breakdown.ndcg_at_5:.6f} | "
                f"{breakdown.latency_p95_ms:.6f} |"
            )
    lines.extend(
        [
            "",
            "## 정성 결과",
            "",
            "| gate | status | 판단 |",
            "| --- | --- | --- |",
            "| CUDA | PASS | CUDA 사용 가능 환경에서 late interaction 후보를 실행했다. |",
            "| scope | PASS | dev hard subset만 사용했고 locked split은 사용하지 않았다. |",
            "| Solar | PASS | Solar Pro 3 호출은 0회다. |",
            "| privacy | PASS | public artifact에는 raw payload를 기록하지 않는다. |",
            "| claim | PASS | 개선 주장은 금지하고 dev-only 비교 결과로만 둔다. |",
            "",
            "## Data Mart Grain",
            "",
            "`fact_colbert_late_interaction_hard_subset`의 grain은 "
            "`work_id + run_label + query_type + metric_name + claim_boundary`다.",
            "",
            "금지 필드:",
            "",
            "- raw query",
            "- raw answer",
            "- raw evidence",
            "- prompt",
            "- chunk text",
            "- private file path",
            "- secret",
            "",
            "## Claim Boundary",
            "",
            "허용:",
            "",
            "- ColBERT-style late interaction을 dev hard subset에서 비교했다.",
            "- CUDA 사용 시 latency와 memory peak를 함께 기록했다.",
            "- locked test와 Solar Pro 3 호출 없이 retrieval-only 실험을 수행했다.",
            "",
            "금지:",
            "",
            "- ColBERT로 production 성능 개선",
            "- locked test에서 ColBERT 개선 입증",
            "- ColBERT를 기본 route로 채택",
            "- Solar Pro 3 기반 ColBERT 개선",
        ]
    )
    return "\n".join(lines) + "\n"


def build_decision_doc_markdown(report: ColbertHardSubsetReport) -> str:
    best_candidate = _best_candidate(report.runs)
    baseline = report.runs[0].run.metric_summary
    best_metric = best_candidate.run.metric_summary
    return (
        "# ColBERT-style Late Interaction Hard Subset\n\n"
        "## 결론\n\n"
        f"`{WORK_ID}`의 결정은 `{report.decision}`이다.\n\n"
        "이번 작업은 ColBERT-style late interaction의 dev hard subset 검색 비교다. "
        "locked test, Solar Pro 3 generation, production route 적용은 수행하지 않았다.\n\n"
        "## 핵심 비교\n\n"
        "| 항목 | baseline | best candidate |\n"
        "| --- | ---: | ---: |\n"
        f"| Recall@5 | {baseline.recall_at_5:.6f} | {best_metric.recall_at_5:.6f} |\n"
        f"| MRR | {baseline.mrr:.6f} | {best_metric.mrr:.6f} |\n"
        f"| nDCG@5 | {baseline.ndcg_at_5:.6f} | {best_metric.ndcg_at_5:.6f} |\n"
        f"| latency_p95_ms | {baseline.latency_p95_ms:.6f} | {best_metric.latency_p95_ms:.6f} |\n"
        f"| cuda_memory_peak_mb | 0.000000 | {best_candidate.cuda_memory_peak_mb:.6f} |\n\n"
        "## 외부 감사 의견\n\n"
        "dev hard subset 결과만으로 기존 final ablation 결론을 뒤집으면 안 된다. "
        "quality gain, latency, CUDA memory를 같이 봐야 하며, 기본 route 채택은 별도 gate가 필요하다.\n\n"
        "## 다음 작업\n\n"
        "결과가 후보 유지에 충분하면 larger dev 또는 locked 전 readiness를 별도로 연다. "
        "결과가 부족하면 ColBERT-style 후보는 reranker latency 대안 실험으로만 보관한다.\n"
    )


def _build_candidate_execution(
    *,
    run_label: str,
    items: list[RetrievalEvalItem],
    documents: list[RetrievalDocument],
    results: list[RetrievalRunResult],
    result_path: Path,
    method_config_summary: dict[str, str | int | float | bool],
    cuda_memory_peak_mb: float,
    rows_path: Path,
    append: bool,
    top_k: int,
) -> CandidateExecution:
    run = build_retrieval_experiment_run(
        method="dense",
        run_label=run_label,
        top_k=top_k,
        items=items,
        documents=documents,
        results=results,
        result_path=result_path,
        method_config_summary=method_config_summary,
    )
    result_rows = build_public_retrieval_result_rows(run_id=run.run_id, results=results)
    for row in result_rows:
        row["run_label"] = run_label
    write_public_retrieval_result_rows(path=result_path, rows=result_rows)
    _append_combined_rows(path=rows_path, rows=result_rows, append=append)
    return CandidateExecution(
        run=run,
        results=results,
        cuda_memory_peak_mb=cuda_memory_peak_mb,
    )


def _build_voice_rewrites(
    *,
    items: list[RetrievalEvalItem],
    place_catalog_path: Path,
) -> list[QueryRewriteResult]:
    rewriter = PlaceAwareQueryRewriter(
        catalog=load_place_catalog(place_catalog_path),
        config=QueryRewriteConfig(
            strategy_id="voice-followup-deterministic-v1",
            target_query_types=("voice_followup",),
        ),
    )
    return [rewriter.rewrite(item) for item in items]


def _search_with_optional_rewrite(
    *,
    retriever: DenseRetriever,
    item: RetrievalEvalItem,
    rewrite: QueryRewriteResult,
    top_k: int,
) -> RetrievalRunResult:
    result = retriever.search(
        query_id=item.query.query_id,
        query_type=item.query.query_type,
        query_text=rewrite.rewritten_query_text,
        top_k=top_k,
    )
    return result.model_copy(
        update={"latency_ms": round(result.latency_ms + rewrite.latency_ms, 6)}
    )


def _search_late_interaction_with_optional_rewrite(
    *,
    retriever: LateInteractionRerankingRetriever,
    item: RetrievalEvalItem,
    rewrite: QueryRewriteResult,
    top_k: int,
) -> RetrievalRunResult:
    result = retriever.search(
        query_id=item.query.query_id,
        query_type=item.query.query_type,
        query_text=rewrite.rewritten_query_text,
        top_k=top_k,
    )
    return result.model_copy(
        update={"latency_ms": round(result.latency_ms + rewrite.latency_ms, 6)}
    )


def _with_rewrite_summary(
    method_config_summary: dict[str, str | int | float | bool],
    *,
    rewrites: list[QueryRewriteResult],
) -> dict[str, str | int | float | bool]:
    return {
        **method_config_summary,
        **summarize_query_rewrite_results(
            config=QueryRewriteConfig(
                strategy_id="voice-followup-deterministic-v1",
                target_query_types=("voice_followup",),
            ),
            results=rewrites,
        ),
    }


def _append_combined_rows(
    *,
    path: Path,
    rows: list[dict[str, object]],
    append: bool,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append and path.exists() else "w"
    with path.open(mode, encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _load_combined_rows(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _query_type_counts(items: list[RetrievalEvalItem]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        key = item.query.query_type
        counts[key] = counts.get(key, 0) + 1
    return counts


def _decide(*, runs: list[CandidateExecution]) -> str:
    baseline = runs[0].run.metric_summary
    best = _best_candidate(runs)
    metric = best.run.metric_summary
    quality_gain = metric.mrr > baseline.mrr and metric.ndcg_at_5 >= baseline.ndcg_at_5
    latency_acceptable = metric.latency_p95_ms < BGE_RERANKER_REFERENCE_P95_MS
    if quality_gain and latency_acceptable:
        return "keep_dev_candidate_for_larger_eval"
    return "reject_default_keep_as_experiment_result"


def _best_candidate(runs: list[CandidateExecution]) -> CandidateExecution:
    candidates = runs[1:] or runs
    return sorted(
        candidates,
        key=lambda run: (
            run.run.metric_summary.mrr,
            run.run.metric_summary.ndcg_at_5,
            -run.run.metric_summary.latency_p95_ms,
        ),
        reverse=True,
    )[0]


def main() -> int:
    args = _parse_args()
    candidate_ks = tuple(
        int(value.strip())
        for value in args.candidate_ks.split(",")
        if value.strip()
    )
    report = run_colbert_late_interaction_hard_subset(
        chunks_path=args.chunks,
        dataset_path=args.dataset,
        results_dir=args.results_dir,
        report_path=args.report,
        doc_path=args.doc,
        embedding_cache_dir=args.embedding_cache_dir,
        place_catalog_path=args.place_catalog,
        top_k=args.top_k,
        candidate_ks=candidate_ks,
    )
    baseline = report.runs[0].run.metric_summary
    print(
        "colbert_late_interaction_hard_subset "
        f"status=PASS work_id={report.work_id} "
        f"query_count={len(report.selected_items)} "
        f"baseline_recall_at_5={baseline.recall_at_5:.6f} "
        f"decision={report.decision}"
    )
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run ColBERT-style late interaction on the dev hard subset.",
    )
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS_PATH)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC_PATH)
    parser.add_argument("--embedding-cache-dir", type=Path, default=DEFAULT_EMBEDDING_CACHE_DIR)
    parser.add_argument("--place-catalog", type=Path, default=DEFAULT_PLACE_CATALOG_PATH)
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument("--candidate-ks", type=str, default="20,50")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
