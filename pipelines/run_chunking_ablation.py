from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.chunking import (
    ChildChunk,
    ChunkingPolicy,
    ParentChildChunkingResult,
    build_parent_child_chunks,
    chunking_report_to_dict,
    collect_chunking_gate_failures,
)
from app.domain.data_contracts import NormalizedBlock
from app.domain.retrieval import (
    REQUIRED_QUERY_TYPES,
    QueryType,
    RetrievalDocument,
    RetrievalEvalItem,
    RetrievalJudgment,
    RetrievalMetricSummary,
    RetrievalRunResult,
    build_retrieval_document_from_child,
    load_retrieval_eval_jsonl,
)
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    collect_public_retrieval_artifact_failures,
    measure_public_retrieval_artifact_quality,
    public_path_alias,
)
from app.domain.source_inventory import write_json
from app.infrastructure.index.bm25 import Bm25Retriever
from pipelines.build_parent_child_chunks import (
    _apply_public_leakage_metrics,
    load_chunking_policy,
    recover_block_texts_from_source,
)


DEFAULT_NORMALIZED_BLOCKS_PATH = (
    Path("private_data") / "reports" / "normalized_blocks.json"
)
DEFAULT_BASELINE_CHUNKS_PATH = (
    Path("private_data") / "reports" / "parent_child_chunks.json"
)
DEFAULT_DEV_DATASET_PATH = (
    Path("private_data") / "evals" / "datasets" / "retrieval_eval_dev.jsonl"
)
DEFAULT_CONFIG_PATH = Path("configs/chunking.default.yaml")
DEFAULT_EXPERIMENT_DIR = Path("private_data") / "experiments" / "chunking_ablation"
DEFAULT_REPORT_PATH = Path("evals/reports/chunking_ablation_report.md")
CHUNKING_ABLATION_REPORT_VERSION = "chunking-ablation-report/v1"
CHUNKING_ABLATION_RUN_PREFIX = "chunking-ablation"
SUPPORTED_VARIANTS: tuple[str, ...] = ("C0", "C1", "C2")
DEFAULT_TOP_K = 5


VariantId = Literal["C0", "C1", "C2"]
GoldTargetKind = Literal["child", "parent", "doc"]


class ChunkingAblationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ChunkingVariantConfig(ChunkingAblationModel):
    variant_id: VariantId
    label: str
    description: str
    child_min_chars: int = Field(ge=1)
    child_target_chars: int = Field(ge=1)
    child_max_chars: int = Field(ge=1)
    child_overlap_blocks: int = Field(ge=0)


class ChunkingAblationQueryTypeMetric(ChunkingAblationModel):
    variant_id: VariantId
    query_type: QueryType
    query_count: int = Field(ge=0)
    recall_at_1: float = Field(ge=0.0, le=1.0)
    recall_at_3: float = Field(ge=0.0, le=1.0)
    recall_at_5: float = Field(ge=0.0, le=1.0)
    mrr: float = Field(ge=0.0, le=1.0)
    ndcg_at_5: float = Field(ge=0.0, le=1.0)
    latency_p95_ms: float = Field(ge=0.0)
    abstain_with_candidate_count: int = Field(ge=0)


class ChunkingAblationVariantResult(ChunkingAblationModel):
    variant_id: VariantId
    label: str
    description: str
    private_chunks_path_alias: str
    private_results_path_alias: str
    chunking_run_id: str
    gate_status: str
    gate_failures: list[str]
    parent_chunk_count: int = Field(ge=0)
    child_chunk_count: int = Field(ge=0)
    indexed_document_count: int = Field(ge=0)
    child_length_p50: int = Field(ge=0)
    child_length_p95: int = Field(ge=0)
    child_max_chars: int = Field(ge=1)
    parent_length_p50: int = Field(ge=0)
    parent_length_p95: int = Field(ge=0)
    micro_parent_count: int = Field(ge=0)
    citation_recoverability: float = Field(ge=0.0, le=1.0)
    retrievable_block_coverage: float = Field(ge=0.0, le=1.0)
    duplicate_child_text_hash_count: int = Field(ge=0)
    replacement_char_child_rate: float = Field(ge=0.0, le=1.0)
    metric_summary: RetrievalMetricSummary
    query_type_breakdown: list[ChunkingAblationQueryTypeMetric]
    candidate_winner: bool


class ChunkingAblationReport(ChunkingAblationModel):
    report_version: str = CHUNKING_ABLATION_REPORT_VERSION
    run_id: str
    generated_at_utc: str
    dataset_path: str
    normalized_blocks_path_alias: str
    baseline_chunks_path_alias: str
    experiment_artifact_alias: str
    method: str = "bm25"
    split: str = "dev"
    top_k: int = Field(ge=1)
    baseline_variant_id: VariantId = "C0"
    selected_variant_id: VariantId
    selection_reason: str
    dataset_query_count: int = Field(ge=0)
    variants: list[ChunkingAblationVariantResult]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


@dataclass(frozen=True)
class _VariantArtifacts:
    result: ParentChildChunkingResult
    documents: list[RetrievalDocument]
    results: list[RetrievalRunResult]
    private_chunks_path: Path
    private_results_path: Path


def run_chunking_ablation(
    *,
    normalized_blocks_path: Path = DEFAULT_NORMALIZED_BLOCKS_PATH,
    baseline_chunks_path: Path = DEFAULT_BASELINE_CHUNKS_PATH,
    dataset_path: Path = DEFAULT_DEV_DATASET_PATH,
    config_path: Path = DEFAULT_CONFIG_PATH,
    source_root: Path,
    experiment_dir: Path = DEFAULT_EXPERIMENT_DIR,
    report_path: Path = DEFAULT_REPORT_PATH,
    variants: list[str] | None = None,
    top_k: int = DEFAULT_TOP_K,
) -> ChunkingAblationReport:
    items = load_retrieval_eval_jsonl(dataset_path)
    _validate_dev_only_dataset(items)
    selected_variant_ids = _validate_variants(variants or list(SUPPORTED_VARIANTS))
    base_policy = load_chunking_policy(config_path)
    blocks = _load_normalized_blocks(normalized_blocks_path)
    block_text_by_id = recover_block_texts_from_source(source_root=source_root, blocks=blocks)
    if not block_text_by_id:
        raise ValueError("source_root did not recover any private block text")
    baseline_children = _load_children_from_chunks(baseline_chunks_path)
    baseline_child_by_id = {child.child_id: child for child in baseline_children}
    baseline_children_by_parent_id = _group_children_by_parent_id(baseline_children)
    baseline_children_by_doc_id = _group_children_by_doc_id(baseline_children)

    artifacts_by_variant: dict[str, _VariantArtifacts] = {}
    variant_results: list[ChunkingAblationVariantResult] = []
    for variant_id in selected_variant_ids:
        config = _variant_config(variant_id, base_policy)
        policy = _policy_for_variant(base_policy=base_policy, config=config)
        artifacts = _run_variant(
            variant_config=config,
            policy=policy,
            blocks=blocks,
            block_text_by_id=block_text_by_id,
            items=items,
            experiment_dir=experiment_dir,
            top_k=top_k,
        )
        artifacts_by_variant[variant_id] = artifacts
        variant_results.append(
            _build_variant_result(
                variant_config=config,
                artifacts=artifacts,
                items=items,
                baseline_child_by_id=baseline_child_by_id,
                baseline_children_by_parent_id=baseline_children_by_parent_id,
                baseline_children_by_doc_id=baseline_children_by_doc_id,
            )
        )

    selected_variant_id, selection_reason = _select_variant(variant_results)
    provisional_report = _build_report(
        dataset_path=dataset_path,
        normalized_blocks_path=normalized_blocks_path,
        baseline_chunks_path=baseline_chunks_path,
        experiment_dir=experiment_dir,
        top_k=top_k,
        selected_variant_id=selected_variant_id,
        selection_reason=selection_reason,
        items=items,
        variants=variant_results,
        output_quality=_empty_output_quality(),
    )
    report_text = build_chunking_ablation_report_markdown(provisional_report)
    final_quality = measure_public_retrieval_artifact_quality(
        report_version=CHUNKING_ABLATION_REPORT_VERSION,
        run_id=provisional_report.run_id,
        result_rows=[],
        report_text=report_text,
    )
    _validate_public_output_quality(final_quality)
    report = provisional_report.model_copy(update={"output_quality": final_quality})
    report_text = build_chunking_ablation_report_markdown(report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_text, encoding="utf-8")
    return report


def build_chunking_ablation_report_markdown(report: ChunkingAblationReport) -> str:
    variant_rows = "\n".join(_format_variant_row(variant) for variant in report.variants)
    query_type_rows = "\n".join(
        _format_query_type_row(metric)
        for variant in report.variants
        for metric in variant.query_type_breakdown
    )
    gate_rows = "\n".join(_format_gate_row(variant) for variant in report.variants)
    quality = report.output_quality
    qualitative_rows = "\n".join(
        f"- `{key}`: {value}" for key, value in report.qualitative_assessment.items()
    )
    return f"""# Chunking Ablation Report

## 목적

BM25 retriever를 고정한 상태에서 parent-child chunking 단위가 retrieval metric에 미치는 영향을 비교한다.

이 리포트는 성능 개선 확정 결과가 아니다. Dense, Hybrid, Reranker 실험 전에 검색 단위를 먼저 검증하기 위한 dev-only ablation 기록이다.

locked test split은 사용하지 않는다. test split은 최종 확인 전까지 튜닝 의사결정에 사용하지 않는다.

full chunk text와 raw run result는 public repository에 저장하지 않는다. public report에는 alias와 집계 수치만 남긴다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| run_id | `{report.run_id}` |
| generated_at_utc | `{report.generated_at_utc}` |
| method | `{report.method}` |
| split | `{report.split}` |
| top_k | {report.top_k} |
| dataset_query_count | {report.dataset_query_count} |
| dataset_path | `{report.dataset_path}` |
| normalized_blocks_path_alias | `{report.normalized_blocks_path_alias}` |
| baseline_chunks_path_alias | `{report.baseline_chunks_path_alias}` |
| experiment_artifact_alias | `{report.experiment_artifact_alias}` |
| baseline_variant_id | `{report.baseline_variant_id}` |
| selected_variant_id | `{report.selected_variant_id}` |
| selection_reason | `{report.selection_reason}` |

## 정량 리포트

| variant | label | gate | parents | children | indexed_docs | child_p50 | child_p95 | max_chars | citation_recoverability | retrievable_coverage | duplicate_text_hash | replacement_char_rate | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | latency_p95_ms | no_answer_candidates | candidate_winner |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
{variant_rows}

## Query Type Breakdown

| variant | query_type | query_count | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | latency_p95_ms | no_answer_candidates |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{query_type_rows}

## Chunking Gate Result

| variant | gate_status | gate_failures |
| --- | --- | --- |
{gate_rows}

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | {quality.result_row_count} |
| public_raw_text_leakage_count | {quality.public_raw_text_leakage_count} |
| private_path_leakage_count | {quality.private_path_leakage_count} |
| secret_like_leakage_count | {quality.secret_like_leakage_count} |
| forbidden_result_field_count | {quality.forbidden_result_field_count} |

## 정성 리포트

{qualitative_rows}

## 해석

이번 실험은 BM25와 dev split만 사용한다.

variant 간 child_id가 달라지므로 gold child target을 baseline source block target으로 변환해 평가했다. child target은 baseline gold child의 source_block_ids 전체를 포함한 새 chunk만 relevant hit로 계산한다.

`selected_variant_id`는 다음 단계 후보일 뿐 최종 성능 개선 주장이 아니다. locked test와 generation 평가 전에는 포트폴리오에서 개선 확정 표현을 사용하지 않는다.
"""


def _run_variant(
    *,
    variant_config: ChunkingVariantConfig,
    policy: ChunkingPolicy,
    blocks: list[NormalizedBlock],
    block_text_by_id: dict[str, str],
    items: list[RetrievalEvalItem],
    experiment_dir: Path,
    top_k: int,
) -> _VariantArtifacts:
    result = build_parent_child_chunks(
        blocks=blocks,
        policy=policy,
        block_text_by_id=block_text_by_id,
    )
    public_sample = result.report.to_public_sample(
        parents=result.parents,
        children=result.children,
    )
    result = _apply_public_leakage_metrics(
        result=result,
        public_sample=public_sample,
        private_roots=[],
        repo_root=Path.cwd(),
    )
    private_chunks_path = experiment_dir / f"{variant_config.variant_id}_parent_child_chunks.json"
    private_results_path = experiment_dir / f"{variant_config.variant_id}_bm25_results.jsonl"
    write_json(
        private_chunks_path,
        chunking_report_to_dict(result=result, include_text=True),
    )
    documents = [
        build_retrieval_document_from_child(child, include_private_text=True)
        for child in result.children
        if child.text
    ]
    if not documents:
        raise ValueError(f"{variant_config.variant_id} produced no searchable documents")
    retriever = Bm25Retriever.from_documents(documents)
    results = [
        retriever.search(
            query_id=item.query.query_id,
            query_type=item.query.query_type,
            query_text=item.query.query_text,
            top_k=top_k,
        )
        for item in items
    ]
    _write_private_result_rows(
        path=private_results_path,
        variant_id=variant_config.variant_id,
        results=results,
    )
    return _VariantArtifacts(
        result=result,
        documents=documents,
        results=results,
        private_chunks_path=private_chunks_path,
        private_results_path=private_results_path,
    )


def _build_variant_result(
    *,
    variant_config: ChunkingVariantConfig,
    artifacts: _VariantArtifacts,
    items: list[RetrievalEvalItem],
    baseline_child_by_id: dict[str, ChildChunk],
    baseline_children_by_parent_id: dict[str, list[ChildChunk]],
    baseline_children_by_doc_id: dict[str, list[ChildChunk]],
) -> ChunkingAblationVariantResult:
    child_by_id = {child.child_id: child for child in artifacts.result.children}
    metric_summary = compute_source_block_retrieval_metrics(
        items=items,
        results=artifacts.results,
        candidate_child_by_id=child_by_id,
        baseline_child_by_id=baseline_child_by_id,
        baseline_children_by_parent_id=baseline_children_by_parent_id,
        baseline_children_by_doc_id=baseline_children_by_doc_id,
    )
    breakdown = compute_source_block_query_type_breakdown(
        variant_id=variant_config.variant_id,
        items=items,
        results=artifacts.results,
        candidate_child_by_id=child_by_id,
        baseline_child_by_id=baseline_child_by_id,
        baseline_children_by_parent_id=baseline_children_by_parent_id,
        baseline_children_by_doc_id=baseline_children_by_doc_id,
    )
    summary = artifacts.result.report.quality_summary
    gate_failures = collect_chunking_gate_failures(artifacts.result.report)
    return ChunkingAblationVariantResult(
        variant_id=variant_config.variant_id,
        label=variant_config.label,
        description=variant_config.description,
        private_chunks_path_alias=f"<private chunking ablation chunks: {variant_config.variant_id}>",
        private_results_path_alias=f"<private chunking ablation results: {variant_config.variant_id}>",
        chunking_run_id=artifacts.result.report.chunking_run_id,
        gate_status="PASS" if not gate_failures else "FAIL",
        gate_failures=gate_failures,
        parent_chunk_count=summary.parent_chunk_count,
        child_chunk_count=summary.child_chunk_count,
        indexed_document_count=len(artifacts.documents),
        child_length_p50=summary.child_length_p50,
        child_length_p95=summary.child_length_p95,
        child_max_chars=variant_config.child_max_chars,
        parent_length_p50=summary.parent_length_p50,
        parent_length_p95=summary.parent_length_p95,
        micro_parent_count=summary.micro_parent_count,
        citation_recoverability=summary.citation_recoverability,
        retrievable_block_coverage=summary.retrievable_block_coverage,
        duplicate_child_text_hash_count=summary.duplicate_child_text_hash_count,
        replacement_char_child_rate=summary.replacement_char_child_rate,
        metric_summary=metric_summary,
        query_type_breakdown=breakdown,
        candidate_winner=False,
    )


def compute_source_block_retrieval_metrics(
    *,
    items: list[RetrievalEvalItem],
    results: list[RetrievalRunResult],
    candidate_child_by_id: dict[str, ChildChunk],
    baseline_child_by_id: dict[str, ChildChunk],
    baseline_children_by_parent_id: dict[str, list[ChildChunk]],
    baseline_children_by_doc_id: dict[str, list[ChildChunk]],
) -> RetrievalMetricSummary:
    results_by_query_id = {result.query_id: result for result in results}
    retrieve_items = [
        item for item in items if item.query.expected_behavior == "retrieve"
    ]
    abstain_items = [
        item for item in items if item.query.expected_behavior == "abstain"
    ]
    recall_at_1_values = [
        _source_block_recall_at_k(
            item=item,
            result=results_by_query_id.get(item.query.query_id),
            candidate_child_by_id=candidate_child_by_id,
            baseline_child_by_id=baseline_child_by_id,
            baseline_children_by_parent_id=baseline_children_by_parent_id,
            baseline_children_by_doc_id=baseline_children_by_doc_id,
            k=1,
        )
        for item in retrieve_items
    ]
    recall_at_3_values = [
        _source_block_recall_at_k(
            item=item,
            result=results_by_query_id.get(item.query.query_id),
            candidate_child_by_id=candidate_child_by_id,
            baseline_child_by_id=baseline_child_by_id,
            baseline_children_by_parent_id=baseline_children_by_parent_id,
            baseline_children_by_doc_id=baseline_children_by_doc_id,
            k=3,
        )
        for item in retrieve_items
    ]
    recall_at_5_values = [
        _source_block_recall_at_k(
            item=item,
            result=results_by_query_id.get(item.query.query_id),
            candidate_child_by_id=candidate_child_by_id,
            baseline_child_by_id=baseline_child_by_id,
            baseline_children_by_parent_id=baseline_children_by_parent_id,
            baseline_children_by_doc_id=baseline_children_by_doc_id,
            k=5,
        )
        for item in retrieve_items
    ]
    mrr_values = [
        _source_block_reciprocal_rank(
            item=item,
            result=results_by_query_id.get(item.query.query_id),
            candidate_child_by_id=candidate_child_by_id,
            baseline_child_by_id=baseline_child_by_id,
            baseline_children_by_parent_id=baseline_children_by_parent_id,
            baseline_children_by_doc_id=baseline_children_by_doc_id,
        )
        for item in retrieve_items
    ]
    ndcg_values = [
        _source_block_ndcg_at_k(
            item=item,
            result=results_by_query_id.get(item.query.query_id),
            candidate_child_by_id=candidate_child_by_id,
            baseline_child_by_id=baseline_child_by_id,
            baseline_children_by_parent_id=baseline_children_by_parent_id,
            baseline_children_by_doc_id=baseline_children_by_doc_id,
            k=5,
        )
        for item in retrieve_items
    ]
    latencies = [result.latency_ms for result in results]
    return RetrievalMetricSummary(
        method="bm25",
        query_count=len(items),
        retrieve_query_count=len(retrieve_items),
        abstain_query_count=len(abstain_items),
        result_count=len(results),
        missing_result_count=sum(
            1 for item in items if item.query.query_id not in results_by_query_id
        ),
        recall_at_1=_mean(recall_at_1_values),
        recall_at_3=_mean(recall_at_3_values),
        recall_at_5=_mean(recall_at_5_values),
        mrr=_mean(mrr_values),
        ndcg_at_5=_mean(ndcg_values),
        latency_p50_ms=_percentile(latencies, 0.5),
        latency_p95_ms=_percentile(latencies, 0.95),
        abstain_with_candidate_count=sum(
            1
            for item in abstain_items
            if results_by_query_id.get(item.query.query_id)
            and results_by_query_id[item.query.query_id].candidates
        ),
    )


def compute_source_block_query_type_breakdown(
    *,
    variant_id: VariantId,
    items: list[RetrievalEvalItem],
    results: list[RetrievalRunResult],
    candidate_child_by_id: dict[str, ChildChunk],
    baseline_child_by_id: dict[str, ChildChunk],
    baseline_children_by_parent_id: dict[str, list[ChildChunk]],
    baseline_children_by_doc_id: dict[str, list[ChildChunk]],
) -> list[ChunkingAblationQueryTypeMetric]:
    result: list[ChunkingAblationQueryTypeMetric] = []
    for query_type in REQUIRED_QUERY_TYPES:
        subset_items = [item for item in items if item.query.query_type == query_type]
        subset_query_ids = {item.query.query_id for item in subset_items}
        subset_results = [run for run in results if run.query_id in subset_query_ids]
        metric = compute_source_block_retrieval_metrics(
            items=subset_items,
            results=subset_results,
            candidate_child_by_id=candidate_child_by_id,
            baseline_child_by_id=baseline_child_by_id,
            baseline_children_by_parent_id=baseline_children_by_parent_id,
            baseline_children_by_doc_id=baseline_children_by_doc_id,
        )
        result.append(
            ChunkingAblationQueryTypeMetric(
                variant_id=variant_id,
                query_type=query_type,
                query_count=metric.query_count,
                recall_at_1=metric.recall_at_1,
                recall_at_3=metric.recall_at_3,
                recall_at_5=metric.recall_at_5,
                mrr=metric.mrr,
                ndcg_at_5=metric.ndcg_at_5,
                latency_p95_ms=metric.latency_p95_ms,
                abstain_with_candidate_count=metric.abstain_with_candidate_count,
            )
        )
    return result


def _source_block_recall_at_k(
    *,
    item: RetrievalEvalItem,
    result: RetrievalRunResult | None,
    candidate_child_by_id: dict[str, ChildChunk],
    baseline_child_by_id: dict[str, ChildChunk],
    baseline_children_by_parent_id: dict[str, list[ChildChunk]],
    baseline_children_by_doc_id: dict[str, list[ChildChunk]],
    k: int,
) -> float:
    if result is None:
        return 0.0
    return (
        1.0
        if any(
            _candidate_source_block_relevance(
                candidate_child=candidate_child_by_id.get(candidate.child_id),
                item=item,
                baseline_child_by_id=baseline_child_by_id,
                baseline_children_by_parent_id=baseline_children_by_parent_id,
                baseline_children_by_doc_id=baseline_children_by_doc_id,
            )
            > 0
            for candidate in result.candidates[:k]
        )
        else 0.0
    )


def _source_block_reciprocal_rank(
    *,
    item: RetrievalEvalItem,
    result: RetrievalRunResult | None,
    candidate_child_by_id: dict[str, ChildChunk],
    baseline_child_by_id: dict[str, ChildChunk],
    baseline_children_by_parent_id: dict[str, list[ChildChunk]],
    baseline_children_by_doc_id: dict[str, list[ChildChunk]],
) -> float:
    if result is None:
        return 0.0
    for candidate in result.candidates:
        if (
            _candidate_source_block_relevance(
                candidate_child=candidate_child_by_id.get(candidate.child_id),
                item=item,
                baseline_child_by_id=baseline_child_by_id,
                baseline_children_by_parent_id=baseline_children_by_parent_id,
                baseline_children_by_doc_id=baseline_children_by_doc_id,
            )
            > 0
        ):
            return round(1 / candidate.rank, 6)
    return 0.0


def _source_block_ndcg_at_k(
    *,
    item: RetrievalEvalItem,
    result: RetrievalRunResult | None,
    candidate_child_by_id: dict[str, ChildChunk],
    baseline_child_by_id: dict[str, ChildChunk],
    baseline_children_by_parent_id: dict[str, list[ChildChunk]],
    baseline_children_by_doc_id: dict[str, list[ChildChunk]],
    k: int,
) -> float:
    if result is None:
        return 0.0
    gold_groups = _gold_source_block_groups(
        item=item,
        baseline_child_by_id=baseline_child_by_id,
        baseline_children_by_parent_id=baseline_children_by_parent_id,
        baseline_children_by_doc_id=baseline_children_by_doc_id,
    )
    used_group_indexes: set[int] = set()
    gains: list[int] = []
    for candidate in result.candidates[:k]:
        candidate_child = candidate_child_by_id.get(candidate.child_id)
        if candidate_child is None:
            gains.append(0)
            continue
        matched_index: int | None = None
        matched_grade = 0
        for group_index, group in enumerate(gold_groups):
            if group_index in used_group_indexes:
                continue
            if _candidate_matches_gold_group(candidate_child=candidate_child, group=group):
                grade = int(group["relevance_grade"])
                if grade > matched_grade:
                    matched_grade = grade
                    matched_index = group_index
        if matched_index is not None:
            used_group_indexes.add(matched_index)
        gains.append(matched_grade)
    ideal_gains = sorted([int(group["relevance_grade"]) for group in gold_groups], reverse=True)[
        :k
    ]
    ideal_gains.extend([0] * max(0, k - len(ideal_gains)))
    idcg = _dcg(ideal_gains)
    if idcg == 0:
        return 0.0
    return min(1.0, round(_dcg(gains) / idcg, 6))


def _candidate_source_block_relevance(
    *,
    candidate_child: ChildChunk | None,
    item: RetrievalEvalItem,
    baseline_child_by_id: dict[str, ChildChunk],
    baseline_children_by_parent_id: dict[str, list[ChildChunk]],
    baseline_children_by_doc_id: dict[str, list[ChildChunk]],
) -> int:
    if candidate_child is None:
        return 0
    max_grade = 0
    for group in _gold_source_block_groups(
        item=item,
        baseline_child_by_id=baseline_child_by_id,
        baseline_children_by_parent_id=baseline_children_by_parent_id,
        baseline_children_by_doc_id=baseline_children_by_doc_id,
    ):
        if _candidate_matches_gold_group(candidate_child=candidate_child, group=group):
            max_grade = max(max_grade, int(group["relevance_grade"]))
    return max_grade


def _candidate_matches_gold_group(
    *,
    candidate_child: ChildChunk | None,
    group: dict[str, Any],
) -> bool:
    if candidate_child is None:
        return False
    target_kind = group["target_kind"]
    target_ids = set(group["target_ids"])
    if target_kind == "child":
        gold_source_block_ids = set(group["source_block_ids"])
        return gold_source_block_ids.issubset(set(candidate_child.source_block_ids))
    if target_kind == "parent":
        return candidate_child.parent_id in target_ids
    if target_kind == "doc":
        return candidate_child.doc_id in target_ids
    return False


def _gold_source_block_groups(
    *,
    item: RetrievalEvalItem,
    baseline_child_by_id: dict[str, ChildChunk],
    baseline_children_by_parent_id: dict[str, list[ChildChunk]],
    baseline_children_by_doc_id: dict[str, list[ChildChunk]],
) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for judgment in item.judgments:
        groups.extend(
            _gold_groups_for_judgment(
                judgment=judgment,
                baseline_child_by_id=baseline_child_by_id,
                baseline_children_by_parent_id=baseline_children_by_parent_id,
                baseline_children_by_doc_id=baseline_children_by_doc_id,
            )
        )
    return groups


def _gold_groups_for_judgment(
    *,
    judgment: RetrievalJudgment,
    baseline_child_by_id: dict[str, ChildChunk],
    baseline_children_by_parent_id: dict[str, list[ChildChunk]],
    baseline_children_by_doc_id: dict[str, list[ChildChunk]],
) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    if judgment.relevant_child_ids:
        for child_id in judgment.relevant_child_ids:
            child = baseline_child_by_id.get(child_id)
            if child is not None:
                groups.append(
                    _gold_group(
                        target_kind="child",
                        target_id=child_id,
                        source_block_ids=set(child.source_block_ids),
                        relevance_grade=judgment.relevance_grade,
                    )
                )
        return groups
    if judgment.relevant_parent_ids:
        for parent_id in judgment.relevant_parent_ids:
            source_block_ids = _source_block_ids_for_children(
                baseline_children_by_parent_id.get(parent_id, [])
            )
            if source_block_ids:
                groups.append(
                    _gold_group(
                        target_kind="parent",
                        target_id=parent_id,
                        source_block_ids=source_block_ids,
                        relevance_grade=judgment.relevance_grade,
                    )
                )
        return groups
    for doc_id in judgment.relevant_doc_ids:
        source_block_ids = _source_block_ids_for_children(
            baseline_children_by_doc_id.get(doc_id, [])
        )
        if source_block_ids:
            groups.append(
                _gold_group(
                    target_kind="doc",
                    target_id=doc_id,
                    source_block_ids=source_block_ids,
                    relevance_grade=judgment.relevance_grade,
                )
            )
    return groups


def _source_block_ids_for_children(children: list[ChildChunk]) -> set[str]:
    block_ids: set[str] = set()
    for child in children:
        block_ids.update(child.source_block_ids)
    return block_ids


def _gold_group(
    *,
    target_kind: GoldTargetKind,
    target_id: str,
    source_block_ids: set[str],
    relevance_grade: int,
) -> dict[str, Any]:
    return {
        "target_kind": target_kind,
        "target_ids": [target_id],
        "source_block_ids": source_block_ids,
        "relevance_grade": relevance_grade,
    }


def _build_report(
    *,
    dataset_path: Path,
    normalized_blocks_path: Path,
    baseline_chunks_path: Path,
    experiment_dir: Path,
    top_k: int,
    selected_variant_id: VariantId,
    selection_reason: str,
    items: list[RetrievalEvalItem],
    variants: list[ChunkingAblationVariantResult],
    output_quality: PublicRetrievalArtifactQuality,
) -> ChunkingAblationReport:
    run_id = _build_run_id(variants)
    return ChunkingAblationReport(
        run_id=run_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        dataset_path=_public_dataset_path_alias(dataset_path),
        normalized_blocks_path_alias=_private_artifact_alias(normalized_blocks_path),
        baseline_chunks_path_alias=_private_artifact_alias(baseline_chunks_path),
        experiment_artifact_alias=f"<private chunking ablation artifacts: {experiment_dir.name}>",
        top_k=top_k,
        selected_variant_id=selected_variant_id,
        selection_reason=selection_reason,
        dataset_query_count=len(items),
        variants=_mark_candidate_winner(
            variants=variants,
            selected_variant_id=selected_variant_id,
        ),
        output_quality=output_quality,
        qualitative_assessment=_build_qualitative_assessment(
            variants=variants,
            selected_variant_id=selected_variant_id,
            selection_reason=selection_reason,
        ),
    )


def _select_variant(
    variants: list[ChunkingAblationVariantResult],
) -> tuple[VariantId, str]:
    baseline = _variant_by_id(variants, "C0")
    eligible = [
        variant
        for variant in variants
        if _variant_passes_selection_gate(variant, baseline)
        and (
            variant.metric_summary.recall_at_5 > baseline.metric_summary.recall_at_5
            or variant.metric_summary.mrr > baseline.metric_summary.mrr
        )
    ]
    if not eligible:
        return "C0", "C1/C2가 selection gate와 개선 조건을 동시에 충족하지 못해 C0를 유지한다."
    selected = sorted(
        eligible,
        key=lambda variant: (
            variant.metric_summary.recall_at_5,
            variant.metric_summary.mrr,
            variant.metric_summary.ndcg_at_5,
            -variant.metric_summary.latency_p95_ms,
        ),
        reverse=True,
    )[0]
    return (
        selected.variant_id,
        (
            f"{selected.variant_id}가 selection gate를 통과하고 "
            "Recall@5 또는 MRR 개선 조건을 충족했다."
        ),
    )


def _variant_passes_selection_gate(
    variant: ChunkingAblationVariantResult,
    baseline: ChunkingAblationVariantResult,
) -> bool:
    return (
        variant.gate_status == "PASS"
        and variant.citation_recoverability >= 0.99
        and variant.child_length_p95 <= variant.child_max_chars
        and variant.metric_summary.abstain_with_candidate_count
        <= baseline.metric_summary.abstain_with_candidate_count
    )


def _mark_candidate_winner(
    *,
    variants: list[ChunkingAblationVariantResult],
    selected_variant_id: VariantId,
) -> list[ChunkingAblationVariantResult]:
    return [
        variant.model_copy(
            update={"candidate_winner": variant.variant_id == selected_variant_id}
        )
        for variant in variants
    ]


def _build_qualitative_assessment(
    *,
    variants: list[ChunkingAblationVariantResult],
    selected_variant_id: VariantId,
    selection_reason: str,
) -> dict[str, str]:
    baseline = _variant_by_id(variants, "C0")
    selected = _variant_by_id(variants, selected_variant_id)
    return {
        "experiment_scope": (
            "BM25 retriever와 private dev split만 사용했다. locked test split은 사용하지 않았다."
        ),
        "target_alignment": (
            "child target은 baseline gold child의 source_block_ids 전체를 포함해야 relevant hit로 계산했다. parent/doc target은 stable identifier로만 계산했다."
        ),
        "baseline_metric": (
            f"C0 Recall@5={baseline.metric_summary.recall_at_5:.6f}, "
            f"MRR={baseline.metric_summary.mrr:.6f}, "
            f"nDCG@5={baseline.metric_summary.ndcg_at_5:.6f}."
        ),
        "selected_metric": (
            f"{selected.variant_id} Recall@5={selected.metric_summary.recall_at_5:.6f}, "
            f"MRR={selected.metric_summary.mrr:.6f}, "
            f"nDCG@5={selected.metric_summary.ndcg_at_5:.6f}."
        ),
        "selection_reason": selection_reason,
        "next_step": (
            "선택 후보를 고정한 뒤 Dense/Hybrid retrieval을 같은 dev/test contract에서 비교한다."
        ),
        "portfolio_boundary": (
            "이번 단계는 청킹 단위 선택 근거다. locked test와 generation 평가 전에는 성능 개선을 확정 주장하지 않는다."
        ),
    }


def _variant_config(
    variant_id: str,
    base_policy: ChunkingPolicy,
) -> ChunkingVariantConfig:
    if variant_id == "C0":
        return ChunkingVariantConfig(
            variant_id="C0",
            label="current parent-child",
            description="현재 기준선 chunking 설정",
            child_min_chars=base_policy.child_min_chars,
            child_target_chars=base_policy.child_target_chars,
            child_max_chars=base_policy.child_max_chars,
            child_overlap_blocks=base_policy.child_overlap_blocks,
        )
    if variant_id == "C1":
        return ChunkingVariantConfig(
            variant_id="C1",
            label="smaller child",
            description="세밀한 사실 질문 precision 개선 가설",
            child_min_chars=180,
            child_target_chars=450,
            child_max_chars=800,
            child_overlap_blocks=1,
        )
    if variant_id == "C2":
        return ChunkingVariantConfig(
            variant_id="C2",
            label="larger child",
            description="story/overview 질문 recall 개선 가설",
            child_min_chars=350,
            child_target_chars=900,
            child_max_chars=1400,
            child_overlap_blocks=1,
        )
    raise ValueError(f"unsupported chunking ablation variant: {variant_id}")


def _policy_for_variant(
    *,
    base_policy: ChunkingPolicy,
    config: ChunkingVariantConfig,
) -> ChunkingPolicy:
    return base_policy.model_copy(
        update={
            "child_min_chars": config.child_min_chars,
            "child_target_chars": config.child_target_chars,
            "child_max_chars": config.child_max_chars,
            "child_overlap_blocks": config.child_overlap_blocks,
        }
    )


def _load_normalized_blocks(path: Path) -> list[NormalizedBlock]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    blocks_payload = payload.get("normalized_blocks")
    if not isinstance(blocks_payload, list):
        raise ValueError("normalized blocks payload must include normalized_blocks list")
    return [NormalizedBlock.model_validate(block) for block in blocks_payload]


def _load_children_from_chunks(path: Path) -> list[ChildChunk]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    children_payload = payload.get("children")
    if not isinstance(children_payload, list):
        raise ValueError("parent child chunks payload must include children list")
    return [ChildChunk.model_validate(child) for child in children_payload]


def _group_children_by_parent_id(children: list[ChildChunk]) -> dict[str, list[ChildChunk]]:
    groups: dict[str, list[ChildChunk]] = defaultdict(list)
    for child in children:
        groups[child.parent_id].append(child)
    return dict(groups)


def _group_children_by_doc_id(children: list[ChildChunk]) -> dict[str, list[ChildChunk]]:
    groups: dict[str, list[ChildChunk]] = defaultdict(list)
    for child in children:
        groups[child.doc_id].append(child)
    return dict(groups)


def _validate_dev_only_dataset(items: list[RetrievalEvalItem]) -> None:
    if not items:
        raise ValueError("chunking ablation requires non-empty dev dataset")
    splits = {item.metadata.split for item in items}
    if splits != {"dev"}:
        raise ValueError("chunking ablation runner must use dev split only")
    review_statuses = {item.metadata.review_status for item in items}
    if review_statuses != {"reviewed"}:
        raise ValueError("chunking ablation runner must use reviewed dev rows only")


def _validate_variants(variants: list[str]) -> list[VariantId]:
    if not variants:
        raise ValueError("at least one chunking variant is required")
    unsupported = [variant for variant in variants if variant not in SUPPORTED_VARIANTS]
    if unsupported:
        raise ValueError(f"unsupported chunking ablation variants: {unsupported}")
    if len(variants) != len(set(variants)):
        raise ValueError("chunking ablation variants must be unique")
    if "C0" not in variants:
        raise ValueError("C0 baseline variant is required")
    return [variant for variant in variants]  # type: ignore[return-value]


def _write_private_result_rows(
    *,
    path: Path,
    variant_id: str,
    results: list[RetrievalRunResult],
) -> None:
    rows: list[dict[str, Any]] = []
    for result in results:
        for candidate in result.candidates:
            rows.append(
                {
                    "variant_id": variant_id,
                    "method": result.method,
                    "query_id": result.query_id,
                    "query_type": result.query_type,
                    "latency_ms": result.latency_ms,
                    "rank": candidate.rank,
                    "child_id": candidate.child_id,
                    "parent_id": candidate.parent_id,
                    "doc_id": candidate.doc_id,
                    "score": candidate.score,
                }
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)
        + "\n",
        encoding="utf-8",
    )


def _empty_output_quality() -> PublicRetrievalArtifactQuality:
    return PublicRetrievalArtifactQuality(
        result_row_count=0,
        report_version=CHUNKING_ABLATION_REPORT_VERSION,
        run_id="pending",
        public_raw_text_leakage_count=0,
        private_path_leakage_count=0,
        secret_like_leakage_count=0,
        forbidden_result_field_count=0,
    )


def _validate_public_output_quality(quality: PublicRetrievalArtifactQuality) -> None:
    failures = collect_public_retrieval_artifact_failures(quality)
    if failures:
        raise ValueError(f"chunking ablation public output gate failed: {failures}")


def _build_run_id(variants: list[ChunkingAblationVariantResult]) -> str:
    variant_part = "-".join(variant.variant_id for variant in variants)
    digest_source = [
        {
            "variant_id": variant.variant_id,
            "chunking_run_id": variant.chunking_run_id,
            "query_count": variant.metric_summary.query_count,
            "recall_at_5": variant.metric_summary.recall_at_5,
            "mrr": variant.metric_summary.mrr,
        }
        for variant in variants
    ]
    digest = json.dumps(digest_source, ensure_ascii=False, sort_keys=True)
    import hashlib

    suffix = hashlib.sha256(digest.encode("utf-8")).hexdigest()[:8]
    return f"{CHUNKING_ABLATION_RUN_PREFIX}-{variant_part}-{suffix}"


def _public_dataset_path_alias(path: Path) -> str:
    if path.name.startswith("retrieval_eval_dev"):
        return f"<private retrieval eval dataset: {path.name}>"
    return public_path_alias(path)


def _private_artifact_alias(path: Path) -> str:
    return f"<private artifact: {path.name}>"


def _variant_by_id(
    variants: list[ChunkingAblationVariantResult],
    variant_id: VariantId,
) -> ChunkingAblationVariantResult:
    for variant in variants:
        if variant.variant_id == variant_id:
            return variant
    raise ValueError(f"missing variant: {variant_id}")


def _format_variant_row(variant: ChunkingAblationVariantResult) -> str:
    metric = variant.metric_summary
    return (
        f"| {variant.variant_id} | {variant.label} | {variant.gate_status} | "
        f"{variant.parent_chunk_count} | {variant.child_chunk_count} | "
        f"{variant.indexed_document_count} | {variant.child_length_p50} | "
        f"{variant.child_length_p95} | {variant.child_max_chars} | "
        f"{variant.citation_recoverability:.6f} | "
        f"{variant.retrievable_block_coverage:.6f} | "
        f"{variant.duplicate_child_text_hash_count} | "
        f"{variant.replacement_char_child_rate:.6f} | "
        f"{metric.recall_at_1:.6f} | {metric.recall_at_3:.6f} | "
        f"{metric.recall_at_5:.6f} | {metric.mrr:.6f} | "
        f"{metric.ndcg_at_5:.6f} | {metric.latency_p95_ms:.6f} | "
        f"{metric.abstain_with_candidate_count} | "
        f"{'yes' if variant.candidate_winner else 'no'} |"
    )


def _format_query_type_row(metric: ChunkingAblationQueryTypeMetric) -> str:
    return (
        f"| {metric.variant_id} | {metric.query_type} | {metric.query_count} | "
        f"{metric.recall_at_1:.6f} | {metric.recall_at_3:.6f} | "
        f"{metric.recall_at_5:.6f} | {metric.mrr:.6f} | "
        f"{metric.ndcg_at_5:.6f} | {metric.latency_p95_ms:.6f} | "
        f"{metric.abstain_with_candidate_count} |"
    )


def _format_gate_row(variant: ChunkingAblationVariantResult) -> str:
    return (
        f"| {variant.variant_id} | {variant.gate_status} | "
        f"`{variant.gate_failures}` |"
    )


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 6)


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * percentile)))
    return round(float(ordered[index]), 6)


def _dcg(gains: list[int]) -> float:
    import math

    return sum(gain / math.log2(index + 2) for index, gain in enumerate(gains))


def main() -> int:
    args = _parse_args()
    variants = [variant.strip() for variant in args.variants.split(",") if variant.strip()]
    report = run_chunking_ablation(
        normalized_blocks_path=args.normalized_blocks,
        baseline_chunks_path=args.baseline_chunks,
        dataset_path=args.dataset,
        config_path=args.config,
        source_root=args.source_root,
        experiment_dir=args.experiment_dir,
        report_path=args.report,
        variants=variants,
        top_k=args.top_k,
    )
    failures = collect_public_retrieval_artifact_failures(report.output_quality)
    print(
        "chunking_ablation "
        f"status={'PASS' if not failures else 'FAIL'} "
        f"variants={','.join(variant.variant_id for variant in report.variants)} "
        f"selected_variant_id={report.selected_variant_id} "
        f"query_count={report.dataset_query_count} "
        f"failures={len(failures)}"
    )
    return 0 if not failures else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run BM25 dev-only chunking ablation for C0/C1/C2 variants."
    )
    parser.add_argument("--normalized-blocks", type=Path, default=DEFAULT_NORMALIZED_BLOCKS_PATH)
    parser.add_argument("--baseline-chunks", type=Path, default=DEFAULT_BASELINE_CHUNKS_PATH)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DEV_DATASET_PATH)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--experiment-dir", type=Path, default=DEFAULT_EXPERIMENT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--variants", type=str, default="C0,C1,C2")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
