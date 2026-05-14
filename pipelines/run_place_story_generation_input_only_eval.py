from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.application.citation_rag import (
    CitationRagAnswerAssembler,
    CitationRagAssemblerConfig,
    build_contract_only_draft,
)
from app.application.evidence_packing import EvidencePack
from app.domain.chunking import ChildChunk
from app.domain.generation import CitationRagAnswer
from app.domain.generation_eval import (
    GenerationEvalInput,
    GenerationEvalReport,
    GenerationEvalUsage,
    build_generation_eval_report,
    collect_generation_eval_harness_failures,
)
from app.domain.retrieval import RetrievalEvalItem
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    measure_public_retrieval_artifact_quality,
)
from app.core.project_paths import project_path
from app.infrastructure.index.device import resolve_torch_device
from pipelines.run_place_story_top_rank_coverage_repair import (
    BASELINE_STRATEGY_ID,
    DEFAULT_CANDIDATE_K,
    DEFAULT_EMBEDDING_CACHE_DIR,
    DEFAULT_PLACE_CATALOG_PATH,
    DEFAULT_TOP_K,
    StrategyId,
    _build_execution_context,
    _load_place_story_dev_items,
    _pack_retrieval_result,
    _rewrite_for_strategy,
    _validate_private_rows_path,
    _write_jsonl_rows,
    rerank_with_parent_doc_context_boost,
)
from pipelines.run_solar_live_generation_smoke import DEFAULT_CHUNKS_PATH, DEFAULT_DATASET_PATH


PLACE_STORY_GENERATION_INPUT_ONLY_REPORT_VERSION = (
    "place-story-generation-input-only-eval-report/v1"
)
DEFAULT_REPORT_PATH = (
    Path("evals") / "reports" / "place_story_generation_input_only_eval_report.md"
)
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "place_story_generation_input_only_eval_rows.jsonl"
)
DEFAULT_MAX_CONTEXT_CHARS = 11000
INPUT_ONLY_ANSWER_POLICY_ID = "place-story-generation-input-only-v1"
INPUT_ONLY_PROVIDER_CONFIG_ID = "contract-only-input-eval-v1"
INPUT_ONLY_MODEL_ID = "input-only-citation-assembly"
INPUT_ONLY_STRATEGIES: tuple[StrategyId, ...] = (
    BASELINE_STRATEGY_ID,
    "parent_doc_context_boost",
)


class PlaceStoryInputOnlyModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EvidenceInputStats(PlaceStoryInputOnlyModel):
    query_id: str = Field(min_length=1)
    strategy_id: StrategyId
    evidence_count: int = Field(ge=0)
    private_text_available_count: int = Field(ge=0)
    context_buildable: bool
    context_char_count: int = Field(ge=0)
    truncated_evidence_count: int = Field(ge=0)
    context_budget_violation: bool
    direct_evidence_ready: bool
    citation_recoverability: float = Field(ge=0.0, le=1.0)
    evidence_order_relevance_proxy: float = Field(ge=0.0, le=1.0)


class PlaceStoryInputOnlyStrategySummary(PlaceStoryInputOnlyModel):
    strategy_id: StrategyId
    eval_count: int = Field(ge=0)
    context_build_success_rate: float = Field(ge=0.0, le=1.0)
    direct_evidence_ready_rate: float = Field(ge=0.0, le=1.0)
    correct_with_evidence_rate: float = Field(ge=0.0, le=1.0)
    citation_precision: float = Field(ge=0.0, le=1.0)
    citation_recall: float = Field(ge=0.0, le=1.0)
    citation_recoverability_avg: float = Field(ge=0.0, le=1.0)
    evidence_order_relevance_proxy_avg: float = Field(ge=0.0, le=1.0)
    avg_evidence_count: float = Field(ge=0.0)
    avg_context_chars: float = Field(ge=0.0)
    context_chars_p95: float = Field(ge=0.0)
    truncated_query_count: int = Field(ge=0)
    missing_citation_count: int = Field(ge=0)
    unsupported_high_count: int = Field(ge=0)
    input_latency_p95_ms: float = Field(ge=0.0)
    solar_call_count: int = Field(ge=0)


class PlaceStoryInputOnlyDelta(PlaceStoryInputOnlyModel):
    compared_strategy_id: StrategyId
    baseline_strategy_id: StrategyId = BASELINE_STRATEGY_ID
    context_build_success_rate_delta: float
    direct_evidence_ready_rate_delta: float
    correct_with_evidence_rate_delta: float
    citation_precision_delta: float
    citation_recall_delta: float
    evidence_order_relevance_proxy_avg_delta: float
    avg_evidence_count_delta: float
    avg_context_chars_delta: float
    truncated_query_count_delta: int
    missing_citation_count_delta: int
    input_latency_p95_ms_delta: float


class PlaceStoryGenerationInputOnlyEvalReport(PlaceStoryInputOnlyModel):
    report_version: str = PLACE_STORY_GENERATION_INPUT_ONLY_REPORT_VERSION
    comparison_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    dataset_path_alias: str = Field(min_length=1)
    chunks_path_alias: str = Field(min_length=1)
    top_k: int = Field(ge=1)
    candidate_k: int = Field(ge=1)
    max_context_chars: int = Field(ge=1)
    resolved_device: str = Field(min_length=1)
    strategy_summaries: tuple[PlaceStoryInputOnlyStrategySummary, ...]
    strategy_deltas: tuple[PlaceStoryInputOnlyDelta, ...]
    selected_strategy_id: StrategyId
    decision: str = Field(min_length=1)
    generation_eval_reports: dict[str, GenerationEvalReport]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


@dataclass(frozen=True)
class _StrategyInputBundle:
    item: RetrievalEvalItem
    strategy_id: StrategyId
    evidence_pack: EvidencePack
    input_stats: EvidenceInputStats
    answer: CitationRagAnswer
    input_latency_ms: float


def run_place_story_generation_input_only_eval(
    *,
    chunks_path: Path = DEFAULT_CHUNKS_PATH,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    place_catalog_path: Path = DEFAULT_PLACE_CATALOG_PATH,
    embedding_cache_dir: Path = DEFAULT_EMBEDDING_CACHE_DIR,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
    top_k: int = DEFAULT_TOP_K,
    candidate_k: int = DEFAULT_CANDIDATE_K,
    max_context_chars: int = DEFAULT_MAX_CONTEXT_CHARS,
) -> PlaceStoryGenerationInputOnlyEvalReport:
    _validate_private_rows_path(result_rows_path, label="result")
    items = _load_place_story_dev_items(dataset_path=dataset_path)
    context = _build_execution_context(
        chunks_path=chunks_path,
        place_catalog_path=place_catalog_path,
        embedding_cache_dir=embedding_cache_dir,
    )
    child_chunks_by_id = _load_child_chunks_by_id(chunks_path)
    bundles_by_strategy = {
        strategy_id: tuple(
            _build_strategy_input_bundle(
                item=item,
                strategy_id=strategy_id,
                context=context,
                child_chunks_by_id=child_chunks_by_id,
                top_k=top_k,
                candidate_k=candidate_k,
                max_context_chars=max_context_chars,
            )
            for item in items
        )
        for strategy_id in INPUT_ONLY_STRATEGIES
    }

    provisional = build_place_story_generation_input_only_eval_report(
        bundles_by_strategy=bundles_by_strategy,
        top_k=top_k,
        candidate_k=candidate_k,
        max_context_chars=max_context_chars,
    )
    provisional_rows = build_public_place_story_generation_input_only_rows(provisional)
    provisional_text = build_place_story_generation_input_only_markdown(provisional)
    report = build_place_story_generation_input_only_eval_report(
        bundles_by_strategy=bundles_by_strategy,
        top_k=top_k,
        candidate_k=candidate_k,
        max_context_chars=max_context_chars,
        result_rows=provisional_rows,
        report_text=provisional_text,
    )
    failures = collect_place_story_generation_input_only_failures(report)
    if failures:
        raise ValueError(f"place_story generation input-only gate failed: {failures}")

    _write_jsonl_rows(
        path=result_rows_path,
        rows=build_public_place_story_generation_input_only_rows(report),
    )
    resolved_report_path = project_path(report_path)
    resolved_report_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_report_path.write_text(
        build_place_story_generation_input_only_markdown(report),
        encoding="utf-8",
    )
    return report


def build_place_story_generation_input_only_eval_report(
    *,
    bundles_by_strategy: dict[StrategyId, tuple[_StrategyInputBundle, ...]],
    top_k: int,
    candidate_k: int,
    max_context_chars: int,
    result_rows: list[dict[str, Any]] | None = None,
    report_text: str = "",
) -> PlaceStoryGenerationInputOnlyEvalReport:
    generation_reports = {
        strategy_id: _generation_eval_report_for_bundles(
            strategy_id=strategy_id,
            bundles=bundles,
        )
        for strategy_id, bundles in bundles_by_strategy.items()
    }
    summaries = tuple(
        build_input_only_strategy_summary(
            strategy_id=strategy_id,
            bundles=bundles_by_strategy[strategy_id],
            generation_report=generation_reports[strategy_id],
        )
        for strategy_id in INPUT_ONLY_STRATEGIES
        if strategy_id in bundles_by_strategy
    )
    deltas = tuple(build_input_only_deltas(summaries))
    selected_strategy_id, decision = _select_input_only_strategy(summaries, deltas)
    comparison_id = _comparison_id(bundles_by_strategy)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=PLACE_STORY_GENERATION_INPUT_ONLY_REPORT_VERSION,
        run_id=comparison_id,
        result_rows=result_rows or [],
        report_text=report_text,
    )
    report = PlaceStoryGenerationInputOnlyEvalReport(
        comparison_id=comparison_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        dataset_path_alias="<private retrieval eval dataset: retrieval_eval_dev.jsonl>",
        chunks_path_alias="<private parent_child_chunks report>",
        top_k=top_k,
        candidate_k=candidate_k,
        max_context_chars=max_context_chars,
        resolved_device=resolve_torch_device("auto"),
        strategy_summaries=summaries,
        strategy_deltas=deltas,
        selected_strategy_id=selected_strategy_id,
        decision=decision,
        generation_eval_reports={str(key): value for key, value in generation_reports.items()},
        output_quality=output_quality,
        qualitative_assessment={},
    )
    return report.model_copy(
        update={"qualitative_assessment": build_input_only_qualitative_assessment(report)},
    )


def build_input_only_strategy_summary(
    *,
    strategy_id: StrategyId,
    bundles: tuple[_StrategyInputBundle, ...],
    generation_report: GenerationEvalReport,
) -> PlaceStoryInputOnlyStrategySummary:
    stats = [bundle.input_stats for bundle in bundles]
    summary = generation_report.summary
    return PlaceStoryInputOnlyStrategySummary(
        strategy_id=strategy_id,
        eval_count=len(bundles),
        context_build_success_rate=_mean_bool([item.context_buildable for item in stats]),
        direct_evidence_ready_rate=_mean_bool([item.direct_evidence_ready for item in stats]),
        correct_with_evidence_rate=summary.correct_with_evidence_rate,
        citation_precision=summary.citation_precision,
        citation_recall=summary.citation_recall,
        citation_recoverability_avg=_mean_float(
            [item.citation_recoverability for item in stats],
        ),
        evidence_order_relevance_proxy_avg=_mean_float(
            [item.evidence_order_relevance_proxy for item in stats],
        ),
        avg_evidence_count=_mean_float([float(item.evidence_count) for item in stats]),
        avg_context_chars=_mean_float([float(item.context_char_count) for item in stats]),
        context_chars_p95=_percentile_float(
            [float(item.context_char_count) for item in stats],
            0.95,
        ),
        truncated_query_count=sum(1 for item in stats if item.truncated_evidence_count > 0),
        missing_citation_count=summary.missing_citation_count,
        unsupported_high_count=summary.unsupported_high_count,
        input_latency_p95_ms=summary.latency_p95_ms,
        solar_call_count=summary.solar_call_count,
    )


def build_input_only_deltas(
    summaries: tuple[PlaceStoryInputOnlyStrategySummary, ...],
) -> list[PlaceStoryInputOnlyDelta]:
    baseline = next(
        summary for summary in summaries if summary.strategy_id == BASELINE_STRATEGY_ID
    )
    deltas: list[PlaceStoryInputOnlyDelta] = []
    for summary in summaries:
        deltas.append(
            PlaceStoryInputOnlyDelta(
                compared_strategy_id=summary.strategy_id,
                context_build_success_rate_delta=round(
                    summary.context_build_success_rate
                    - baseline.context_build_success_rate,
                    6,
                ),
                direct_evidence_ready_rate_delta=round(
                    summary.direct_evidence_ready_rate
                    - baseline.direct_evidence_ready_rate,
                    6,
                ),
                correct_with_evidence_rate_delta=round(
                    summary.correct_with_evidence_rate
                    - baseline.correct_with_evidence_rate,
                    6,
                ),
                citation_precision_delta=round(
                    summary.citation_precision - baseline.citation_precision,
                    6,
                ),
                citation_recall_delta=round(
                    summary.citation_recall - baseline.citation_recall,
                    6,
                ),
                evidence_order_relevance_proxy_avg_delta=round(
                    summary.evidence_order_relevance_proxy_avg
                    - baseline.evidence_order_relevance_proxy_avg,
                    6,
                ),
                avg_evidence_count_delta=round(
                    summary.avg_evidence_count - baseline.avg_evidence_count,
                    6,
                ),
                avg_context_chars_delta=round(
                    summary.avg_context_chars - baseline.avg_context_chars,
                    6,
                ),
                truncated_query_count_delta=(
                    summary.truncated_query_count - baseline.truncated_query_count
                ),
                missing_citation_count_delta=(
                    summary.missing_citation_count - baseline.missing_citation_count
                ),
                input_latency_p95_ms_delta=round(
                    summary.input_latency_p95_ms - baseline.input_latency_p95_ms,
                    6,
                ),
            ),
        )
    return deltas


def build_public_place_story_generation_input_only_rows(
    report: PlaceStoryGenerationInputOnlyEvalReport,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for summary in report.strategy_summaries:
        rows.append(
            {
                "comparison_id": report.comparison_id,
                "row_type": "strategy_summary",
                "strategy_id": summary.strategy_id,
                "eval_count": summary.eval_count,
                "context_build_success_rate": summary.context_build_success_rate,
                "direct_evidence_ready_rate": summary.direct_evidence_ready_rate,
                "correct_with_evidence_rate": summary.correct_with_evidence_rate,
                "citation_precision": summary.citation_precision,
                "citation_recall": summary.citation_recall,
                "citation_recoverability_avg": summary.citation_recoverability_avg,
                "evidence_order_relevance_proxy_avg": (
                    summary.evidence_order_relevance_proxy_avg
                ),
                "avg_evidence_count": summary.avg_evidence_count,
                "avg_context_chars": summary.avg_context_chars,
                "context_chars_p95": summary.context_chars_p95,
                "truncated_query_count": summary.truncated_query_count,
                "input_latency_p95_ms": summary.input_latency_p95_ms,
                "solar_call_count": summary.solar_call_count,
            },
        )
    for delta in report.strategy_deltas:
        rows.append(
            {
                "comparison_id": report.comparison_id,
                "row_type": "strategy_delta",
                "strategy_id": delta.compared_strategy_id,
                "baseline_strategy_id": delta.baseline_strategy_id,
                "direct_evidence_ready_rate_delta": delta.direct_evidence_ready_rate_delta,
                "correct_with_evidence_rate_delta": delta.correct_with_evidence_rate_delta,
                "citation_precision_delta": delta.citation_precision_delta,
                "citation_recall_delta": delta.citation_recall_delta,
                "evidence_order_relevance_proxy_avg_delta": (
                    delta.evidence_order_relevance_proxy_avg_delta
                ),
                "avg_context_chars_delta": delta.avg_context_chars_delta,
                "input_latency_p95_ms_delta": delta.input_latency_p95_ms_delta,
            },
        )
    return rows


def collect_place_story_generation_input_only_failures(
    report: PlaceStoryGenerationInputOnlyEvalReport,
) -> list[str]:
    failures: list[str] = []
    for strategy_id, generation_report in report.generation_eval_reports.items():
        failures.extend(
            f"{strategy_id}:{failure}"
            for failure in collect_generation_eval_harness_failures(generation_report)
            if failure != "missing_citations"
        )
    if any(summary.solar_call_count for summary in report.strategy_summaries):
        failures.append("solar_call_count_must_be_zero")
    if report.output_quality.public_raw_text_leakage_count:
        failures.append("public_raw_text_leakage")
    if report.output_quality.private_path_leakage_count:
        failures.append("private_path_leakage")
    if report.output_quality.secret_like_leakage_count:
        failures.append("secret_like_leakage")
    if report.output_quality.forbidden_result_field_count:
        failures.append("forbidden_public_result_fields")
    return failures


def build_place_story_generation_input_only_markdown(
    report: PlaceStoryGenerationInputOnlyEvalReport,
) -> str:
    summary_rows = "\n".join(_format_summary_row(row) for row in report.strategy_summaries)
    delta_rows = "\n".join(_format_delta_row(row) for row in report.strategy_deltas)
    qualitative_rows = "\n".join(
        f"- `{key}`: {value}" for key, value in report.qualitative_assessment.items()
    )
    quality = report.output_quality
    return f"""# Place Story Generation Input-only Eval Report

## 목적

`parent_doc_context_boost` 적용 후 Solar Pro 3를 호출하기 전에 generation 입력 evidence의 citation 품질과 prompt 입력 안정성을 비교한다.

이 문서는 live LLM 답변 품질 결과가 아니다. dummy draft와 citation assembler를 사용해 evidence 입력만 평가하며 Solar Pro 3 호출 수는 0이어야 한다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| comparison_id | `{report.comparison_id}` |
| generated_at_utc | `{report.generated_at_utc}` |
| dataset_path | `{report.dataset_path_alias}` |
| chunks_path | `{report.chunks_path_alias}` |
| top_k | {report.top_k} |
| candidate_k | {report.candidate_k} |
| max_context_chars | {report.max_context_chars} |
| resolved_device | `{report.resolved_device}` |
| selected_strategy_id | `{report.selected_strategy_id}` |
| decision | {report.decision} |

## Strategy Summary

| strategy_id | eval_count | context_build | direct_ready | Correct-with-Evidence | citation_precision | citation_recall | citation_recoverability | evidence_order | avg_evidence | avg_context_chars | context_chars_p95 | truncated | input_latency_p95_ms | solar_calls |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{summary_rows}

## Baseline Delta

| compared_strategy_id | context_build delta | direct_ready delta | Correct delta | precision delta | recall delta | evidence_order delta | avg_evidence delta | avg_context_chars delta | truncated delta | missing_citation delta | input_latency_p95_ms delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{delta_rows}

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

## 결론

{_conclusion_text(report)}
"""


def build_input_only_qualitative_assessment(
    report: PlaceStoryGenerationInputOnlyEvalReport,
) -> dict[str, str]:
    return {
        "comparison_scope": (
            "baseline과 parent/doc context boost의 generation 입력 evidence만 비교했다."
        ),
        "llm_call_boundary": (
            "Solar Pro 3 live 호출은 수행하지 않았고 solar_call_count는 0이어야 한다."
        ),
        "metric_boundary": (
            "Correct-with-Evidence는 dummy draft에 붙은 citation이 target refs를 덮는지 보는 input-only proxy다."
        ),
        "security_boundary": (
            "raw query, raw evidence, prompt, answer text는 public report/result에 기록하지 않는다."
        ),
        "data_mart_grain": (
            "`fact_place_story_generation_input_only`의 grain은 strategy-query이며 공개 row는 aggregate/delta만 남긴다."
        ),
        "next_action": _next_action(report),
    }


def _build_strategy_input_bundle(
    *,
    item: RetrievalEvalItem,
    strategy_id: StrategyId,
    context,
    child_chunks_by_id: dict[str, ChildChunk],
    top_k: int,
    candidate_k: int,
    max_context_chars: int,
) -> _StrategyInputBundle:
    rewrite = _rewrite_for_strategy(item=item, strategy_id=strategy_id, context=context)
    search_k = candidate_k if strategy_id == "parent_doc_context_boost" else top_k
    result = context.retriever.search(
        query_id=item.query.query_id,
        query_type=item.query.query_type,
        query_text=rewrite.rewritten_query_text,
        top_k=search_k,
    )
    if strategy_id == "parent_doc_context_boost":
        result = rerank_with_parent_doc_context_boost(
            item=item,
            result=result,
            document_by_child_id=context.document_by_child_id,
            catalog=context.catalog,
            top_k=top_k,
        )
    input_latency_ms = round(result.latency_ms + rewrite.latency_ms, 6)
    evidence_pack = _pack_retrieval_result(item=item, result=result, packer=context.packer)
    input_stats = build_evidence_input_stats(
        item=item,
        strategy_id=strategy_id,
        evidence_pack=evidence_pack,
        child_chunks_by_id=child_chunks_by_id,
        max_context_chars=max_context_chars,
    )
    answer = _assemble_input_only_answer(
        item=item,
        evidence_pack=evidence_pack,
    )
    return _StrategyInputBundle(
        item=item,
        strategy_id=strategy_id,
        evidence_pack=evidence_pack,
        input_stats=input_stats,
        answer=answer,
        input_latency_ms=input_latency_ms,
    )


def build_evidence_input_stats(
    *,
    item: RetrievalEvalItem,
    strategy_id: StrategyId,
    evidence_pack: EvidencePack,
    child_chunks_by_id: dict[str, ChildChunk],
    max_context_chars: int,
) -> EvidenceInputStats:
    remaining = max_context_chars
    context_chars = 0
    private_text_available_count = 0
    truncated_count = 0
    for evidence in evidence_pack.evidence:
        child = child_chunks_by_id.get(evidence.child_id)
        if child is None or not child.text:
            continue
        private_text_available_count += 1
        page_end = child.page_span.page_global_end or child.page_span.page_global_start
        header = (
            f"[evidence:{evidence.pack_rank}] "
            f"child_id={evidence.child_id} "
            f"doc_id={evidence.doc_id} "
            f"page_global={child.page_span.page_global_start}-{page_end}"
        )
        candidate_len = len(header) + 1 + len(child.text.strip())
        if candidate_len > remaining:
            truncated_count += 1
            context_chars += max(0, remaining)
            remaining = 0
            break
        context_chars += candidate_len
        remaining -= candidate_len + 2
        if remaining <= 0:
            break
    return EvidenceInputStats(
        query_id=item.query.query_id,
        strategy_id=strategy_id,
        evidence_count=len(evidence_pack.evidence),
        private_text_available_count=private_text_available_count,
        context_buildable=bool(evidence_pack.evidence)
        and private_text_available_count == len(evidence_pack.evidence),
        context_char_count=context_chars,
        truncated_evidence_count=truncated_count,
        context_budget_violation=context_chars > max_context_chars,
        direct_evidence_ready=evidence_pack.target_child_covered
        or evidence_pack.target_parent_covered,
        citation_recoverability=evidence_pack.citation_recoverability,
        evidence_order_relevance_proxy=evidence_pack.evidence_order_relevance_proxy,
    )


def _assemble_input_only_answer(
    *,
    item: RetrievalEvalItem,
    evidence_pack: EvidencePack,
) -> CitationRagAnswer:
    assembler = CitationRagAnswerAssembler(
        config=CitationRagAssemblerConfig(
            answer_policy_id=INPUT_ONLY_ANSWER_POLICY_ID,
            provider="contract_only",
            model_id=INPUT_ONLY_MODEL_ID,
        ),
    )
    if item.query.expected_behavior == "abstain" or not evidence_pack.evidence:
        return assembler.assemble(item=item, evidence_pack=evidence_pack)
    draft = build_contract_only_draft(
        answer="근거 입력 품질만 확인하기 위한 임시 답변입니다.",
        spoken_answer="근거 입력 품질만 확인하는 임시 음성 답변입니다.",
        unsupported_claim_risk="low",
    )
    return assembler.assemble(item=item, evidence_pack=evidence_pack, draft=draft)


def _generation_eval_report_for_bundles(
    *,
    strategy_id: StrategyId,
    bundles: tuple[_StrategyInputBundle, ...],
) -> GenerationEvalReport:
    inputs = [
        GenerationEvalInput(
            item=bundle.item,
            answer=bundle.answer,
            packing_policy_id=bundle.evidence_pack.policy_id,
            retrieval_run_label=strategy_id,
            provider_config_id=INPUT_ONLY_PROVIDER_CONFIG_ID,
            usage=GenerationEvalUsage(latency_ms=bundle.input_latency_ms),
        )
        for bundle in bundles
    ]
    return build_generation_eval_report(inputs=inputs)


def _load_child_chunks_by_id(chunks_path: Path) -> dict[str, ChildChunk]:
    resolved = project_path(chunks_path)
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    children_payload = payload.get("children")
    if not isinstance(children_payload, list):
        raise ValueError("parent_child_chunks payload must include children list")
    children = [ChildChunk.model_validate(child) for child in children_payload]
    return {child.child_id: child for child in children}


def _select_input_only_strategy(
    summaries: tuple[PlaceStoryInputOnlyStrategySummary, ...],
    deltas: tuple[PlaceStoryInputOnlyDelta, ...],
) -> tuple[StrategyId, str]:
    baseline = next(
        summary for summary in summaries if summary.strategy_id == BASELINE_STRATEGY_ID
    )
    candidate = next(
        summary for summary in summaries if summary.strategy_id == "parent_doc_context_boost"
    )
    candidate_delta = next(
        delta for delta in deltas if delta.compared_strategy_id == "parent_doc_context_boost"
    )
    if (
        candidate.direct_evidence_ready_rate > baseline.direct_evidence_ready_rate
        and candidate.citation_recall >= baseline.citation_recall
        and candidate.citation_precision >= baseline.citation_precision
        and candidate.correct_with_evidence_rate >= baseline.correct_with_evidence_rate
        and candidate.context_build_success_rate >= baseline.context_build_success_rate
    ):
        return (
            "parent_doc_context_boost",
            "promote_to_solar_prompt_repair_planning",
        )
    if candidate_delta.direct_evidence_ready_rate_delta > 0:
        return ("parent_doc_context_boost", "keep_as_tradeoff_candidate")
    return (BASELINE_STRATEGY_ID, "reject_candidate")


def _comparison_id(
    bundles_by_strategy: dict[StrategyId, tuple[_StrategyInputBundle, ...]],
) -> str:
    payload = {
        strategy_id: [
            {
                "query_id": bundle.item.query.query_id,
                "evidence_ids": [
                    evidence.child_id for evidence in bundle.evidence_pack.evidence
                ],
                "input_stats": bundle.input_stats.model_dump(mode="json"),
            }
            for bundle in bundles
        ]
        for strategy_id, bundles in bundles_by_strategy.items()
    }
    digest = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"),
    ).hexdigest()[:8]
    query_count = len(next(iter(bundles_by_strategy.values()))) if bundles_by_strategy else 0
    return f"place-story-input-only-s{len(bundles_by_strategy)}-q{query_count}-{digest}"


def _mean_bool(values: list[bool]) -> float:
    if not values:
        return 0.0
    return round(sum(1 for value in values if value) / len(values), 6)


def _mean_float(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 6)


def _percentile_float(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = round((len(sorted_values) - 1) * percentile)
    return round(sorted_values[index], 6)


def _format_summary_row(summary: PlaceStoryInputOnlyStrategySummary) -> str:
    return (
        f"| {summary.strategy_id} | {summary.eval_count} | "
        f"{summary.context_build_success_rate:.6f} | "
        f"{summary.direct_evidence_ready_rate:.6f} | "
        f"{summary.correct_with_evidence_rate:.6f} | "
        f"{summary.citation_precision:.6f} | {summary.citation_recall:.6f} | "
        f"{summary.citation_recoverability_avg:.6f} | "
        f"{summary.evidence_order_relevance_proxy_avg:.6f} | "
        f"{summary.avg_evidence_count:.6f} | {summary.avg_context_chars:.6f} | "
        f"{summary.context_chars_p95:.6f} | {summary.truncated_query_count} | "
        f"{summary.input_latency_p95_ms:.6f} | "
        f"{summary.solar_call_count} |"
    )


def _format_delta_row(delta: PlaceStoryInputOnlyDelta) -> str:
    return (
        f"| {delta.compared_strategy_id} | "
        f"{delta.context_build_success_rate_delta:.6f} | "
        f"{delta.direct_evidence_ready_rate_delta:.6f} | "
        f"{delta.correct_with_evidence_rate_delta:.6f} | "
        f"{delta.citation_precision_delta:.6f} | "
        f"{delta.citation_recall_delta:.6f} | "
        f"{delta.evidence_order_relevance_proxy_avg_delta:.6f} | "
        f"{delta.avg_evidence_count_delta:.6f} | "
        f"{delta.avg_context_chars_delta:.6f} | "
        f"{delta.truncated_query_count_delta} | "
        f"{delta.missing_citation_count_delta} | "
        f"{delta.input_latency_p95_ms_delta:.6f} |"
    )


def _next_action(report: PlaceStoryGenerationInputOnlyEvalReport) -> str:
    if report.decision == "promote_to_solar_prompt_repair_planning":
        return "Solar Pro 3 live 호출 전 v2 prompt repair 계획을 문서화한다."
    if report.decision == "keep_as_tradeoff_candidate":
        return "candidate를 trade-off 후보로 유지하고 query별 입력 regression을 점검한다."
    return "candidate를 채택하지 않고 retrieval 또는 judgment grain 후보를 재검토한다."


def _conclusion_text(report: PlaceStoryGenerationInputOnlyEvalReport) -> str:
    if report.decision == "promote_to_solar_prompt_repair_planning":
        return (
            "`parent_doc_context_boost`는 Solar Pro 3 호출 전 input-only gate를 통과했다.\n\n"
            "다만 이 결과는 dummy draft 기반 citation input 평가이며 live generation 품질 개선 주장이 아니다."
        )
    if report.decision == "keep_as_tradeoff_candidate":
        return (
            "`parent_doc_context_boost`는 입력 일부를 개선하지만 trade-off가 남아 있다.\n\n"
            "Solar Pro 3 live 호출 전 query별 regression 확인이 필요하다."
        )
    return (
        "`parent_doc_context_boost`는 input-only 기준에서 baseline보다 안정적이지 않다.\n\n"
        "다음 단계는 retrieval 후보 또는 judgment grain을 재검토하는 것이다."
    )


def main() -> int:
    args = _parse_args()
    report = run_place_story_generation_input_only_eval(
        chunks_path=args.chunks,
        dataset_path=args.dataset,
        place_catalog_path=args.place_catalog,
        embedding_cache_dir=args.embedding_cache_dir,
        report_path=args.report,
        result_rows_path=args.result_rows,
        top_k=args.top_k,
        candidate_k=args.candidate_k,
        max_context_chars=args.max_context_chars,
    )
    failures = collect_place_story_generation_input_only_failures(report)
    selected = next(
        summary
        for summary in report.strategy_summaries
        if summary.strategy_id == report.selected_strategy_id
    )
    print(
        "place_story_generation_input_only_eval "
        f"status={'PASS' if not failures else 'FAIL'} "
        f"selected={report.selected_strategy_id} "
        f"decision={report.decision} "
        f"direct_ready={selected.direct_evidence_ready_rate:.6f} "
        f"citation_recall={selected.citation_recall:.6f} "
        f"device={report.resolved_device} "
        f"failures={len(failures)}",
    )
    return 0 if not failures else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run place_story generation input-only evidence quality evaluation.",
    )
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS_PATH)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--place-catalog", type=Path, default=DEFAULT_PLACE_CATALOG_PATH)
    parser.add_argument("--embedding-cache-dir", type=Path, default=DEFAULT_EMBEDDING_CACHE_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--result-rows", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument("--candidate-k", type=int, default=DEFAULT_CANDIDATE_K)
    parser.add_argument("--max-context-chars", type=int, default=DEFAULT_MAX_CONTEXT_CHARS)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
