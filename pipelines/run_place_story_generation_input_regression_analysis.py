from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.project_paths import project_path
from app.domain.generation_eval import (
    GenerationEvalInput,
    GenerationEvalRecord,
    GenerationEvalUsage,
    build_generation_eval_records,
)
from app.domain.retrieval import QueryType
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    measure_public_retrieval_artifact_quality,
)
from app.infrastructure.index.device import resolve_torch_device
from pipelines.run_place_story_generation_input_only_eval import (
    DEFAULT_MAX_CONTEXT_CHARS,
    INPUT_ONLY_PROVIDER_CONFIG_ID,
    _StrategyInputBundle,
    _build_strategy_input_bundle,
    _load_child_chunks_by_id,
)
from pipelines.run_place_story_top_rank_coverage_repair import (
    BASELINE_STRATEGY_ID,
    DEFAULT_CANDIDATE_K,
    DEFAULT_EMBEDDING_CACHE_DIR,
    DEFAULT_PLACE_CATALOG_PATH,
    DEFAULT_TOP_K,
    StrategyId,
    _build_execution_context,
    _load_place_story_dev_items,
    _validate_private_rows_path,
    _write_jsonl_rows,
)
from pipelines.run_solar_live_generation_smoke import DEFAULT_CHUNKS_PATH, DEFAULT_DATASET_PATH


PLACE_STORY_INPUT_REGRESSION_REPORT_VERSION = (
    "place-story-generation-input-regression-analysis/v1"
)
DEFAULT_REPORT_PATH = (
    Path("evals")
    / "reports"
    / "place_story_generation_input_regression_analysis_report.md"
)
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "place_story_generation_input_regression_analysis_rows.jsonl"
)
CANDIDATE_STRATEGY_ID: StrategyId = "parent_doc_context_boost"


class PlaceStoryInputRegressionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PlaceStoryInputRegressionRow(PlaceStoryInputRegressionModel):
    query_id: str = Field(min_length=1)
    query_type: QueryType
    split: str = Field(min_length=1)
    baseline_direct_ready: bool
    candidate_direct_ready: bool
    direct_ready_delta: int = Field(ge=-1, le=1)
    baseline_correct_with_evidence: bool
    candidate_correct_with_evidence: bool
    correct_with_evidence_delta: int = Field(ge=-1, le=1)
    citation_precision_delta: float
    citation_recall_delta: float
    evidence_order_delta: float
    citation_count_delta: int
    evidence_count_delta: int
    context_char_delta: int
    input_latency_delta_ms: float
    regression_tags: tuple[str, ...]
    recommendation: str = Field(min_length=1)


class PlaceStoryInputRegressionSummary(PlaceStoryInputRegressionModel):
    query_count: int = Field(ge=0)
    direct_ready_gain_count: int = Field(ge=0)
    direct_ready_loss_count: int = Field(ge=0)
    correct_with_evidence_regression_count: int = Field(ge=0)
    citation_precision_regression_count: int = Field(ge=0)
    citation_recall_gain_count: int = Field(ge=0)
    evidence_order_regression_count: int = Field(ge=0)
    mixed_tradeoff_count: int = Field(ge=0)
    guardrail_required_count: int = Field(ge=0)
    input_latency_improved_count: int = Field(ge=0)
    solar_call_count: int = Field(ge=0)
    recommended_decision: str = Field(min_length=1)


class PlaceStoryInputRegressionAnalysisReport(PlaceStoryInputRegressionModel):
    report_version: str = PLACE_STORY_INPUT_REGRESSION_REPORT_VERSION
    analysis_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    dataset_path_alias: str = Field(min_length=1)
    chunks_path_alias: str = Field(min_length=1)
    baseline_strategy_id: StrategyId
    candidate_strategy_id: StrategyId
    top_k: int = Field(ge=1)
    candidate_k: int = Field(ge=1)
    max_context_chars: int = Field(ge=1)
    resolved_device: str = Field(min_length=1)
    summary: PlaceStoryInputRegressionSummary
    tag_distribution: dict[str, int]
    query_rows: tuple[PlaceStoryInputRegressionRow, ...]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def run_place_story_generation_input_regression_analysis(
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
) -> PlaceStoryInputRegressionAnalysisReport:
    _validate_private_rows_path(result_rows_path, label="result")
    items = _load_place_story_dev_items(dataset_path=dataset_path)
    context = _build_execution_context(
        chunks_path=chunks_path,
        place_catalog_path=place_catalog_path,
        embedding_cache_dir=embedding_cache_dir,
    )
    child_chunks_by_id = _load_child_chunks_by_id(chunks_path)
    bundles_by_strategy = {
        BASELINE_STRATEGY_ID: tuple(
            _build_strategy_input_bundle(
                item=item,
                strategy_id=BASELINE_STRATEGY_ID,
                context=context,
                child_chunks_by_id=child_chunks_by_id,
                top_k=top_k,
                candidate_k=candidate_k,
                max_context_chars=max_context_chars,
            )
            for item in items
        ),
        CANDIDATE_STRATEGY_ID: tuple(
            _build_strategy_input_bundle(
                item=item,
                strategy_id=CANDIDATE_STRATEGY_ID,
                context=context,
                child_chunks_by_id=child_chunks_by_id,
                top_k=top_k,
                candidate_k=candidate_k,
                max_context_chars=max_context_chars,
            )
            for item in items
        ),
    }
    provisional = build_place_story_input_regression_analysis_report(
        bundles_by_strategy=bundles_by_strategy,
        top_k=top_k,
        candidate_k=candidate_k,
        max_context_chars=max_context_chars,
    )
    provisional_rows = build_public_place_story_input_regression_rows(provisional)
    provisional_text = build_place_story_input_regression_markdown(provisional)
    report = build_place_story_input_regression_analysis_report(
        bundles_by_strategy=bundles_by_strategy,
        top_k=top_k,
        candidate_k=candidate_k,
        max_context_chars=max_context_chars,
        result_rows=provisional_rows,
        report_text=provisional_text,
    )
    failures = collect_place_story_input_regression_failures(report)
    if failures:
        raise ValueError(f"place_story input regression analysis gate failed: {failures}")

    _write_jsonl_rows(
        path=result_rows_path,
        rows=build_public_place_story_input_regression_rows(report),
    )
    resolved_report_path = project_path(report_path)
    resolved_report_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_report_path.write_text(
        build_place_story_input_regression_markdown(report),
        encoding="utf-8",
    )
    return report


def build_place_story_input_regression_analysis_report(
    *,
    bundles_by_strategy: dict[StrategyId, tuple[_StrategyInputBundle, ...]],
    top_k: int,
    candidate_k: int,
    max_context_chars: int,
    result_rows: list[dict[str, Any]] | None = None,
    report_text: str = "",
) -> PlaceStoryInputRegressionAnalysisReport:
    baseline_bundles = _bundles_by_query_id(bundles_by_strategy[BASELINE_STRATEGY_ID])
    candidate_bundles = _bundles_by_query_id(bundles_by_strategy[CANDIDATE_STRATEGY_ID])
    baseline_records = _records_by_query_id(
        strategy_id=BASELINE_STRATEGY_ID,
        bundles=tuple(baseline_bundles.values()),
    )
    candidate_records = _records_by_query_id(
        strategy_id=CANDIDATE_STRATEGY_ID,
        bundles=tuple(candidate_bundles.values()),
    )
    rows = tuple(
        build_input_regression_row(
            baseline_bundle=baseline_bundles[query_id],
            candidate_bundle=candidate_bundles[query_id],
            baseline_record=baseline_records[query_id],
            candidate_record=candidate_records[query_id],
        )
        for query_id in sorted(baseline_bundles)
    )
    summary = build_input_regression_summary(
        rows=rows,
        solar_call_count=sum(
            record.solar_call_count
            for record in [*baseline_records.values(), *candidate_records.values()]
        ),
    )
    tag_distribution = build_tag_distribution(rows)
    analysis_id = _analysis_id(rows)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=PLACE_STORY_INPUT_REGRESSION_REPORT_VERSION,
        run_id=analysis_id,
        result_rows=result_rows or [],
        report_text=report_text,
    )
    report = PlaceStoryInputRegressionAnalysisReport(
        analysis_id=analysis_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        dataset_path_alias="<private retrieval eval dataset: retrieval_eval_dev.jsonl>",
        chunks_path_alias="<private parent_child_chunks report>",
        baseline_strategy_id=BASELINE_STRATEGY_ID,
        candidate_strategy_id=CANDIDATE_STRATEGY_ID,
        top_k=top_k,
        candidate_k=candidate_k,
        max_context_chars=max_context_chars,
        resolved_device=resolve_torch_device("auto"),
        summary=summary,
        tag_distribution=tag_distribution,
        query_rows=rows,
        output_quality=output_quality,
        qualitative_assessment={},
    )
    return report.model_copy(
        update={
            "qualitative_assessment": build_input_regression_qualitative_assessment(report),
        },
    )


def build_input_regression_row(
    *,
    baseline_bundle: _StrategyInputBundle,
    candidate_bundle: _StrategyInputBundle,
    baseline_record: GenerationEvalRecord,
    candidate_record: GenerationEvalRecord,
) -> PlaceStoryInputRegressionRow:
    tags = build_regression_tags(
        baseline_bundle=baseline_bundle,
        candidate_bundle=candidate_bundle,
        baseline_record=baseline_record,
        candidate_record=candidate_record,
    )
    return PlaceStoryInputRegressionRow(
        query_id=baseline_record.query_id,
        query_type=baseline_record.query_type,
        split=baseline_record.split,
        baseline_direct_ready=baseline_bundle.input_stats.direct_evidence_ready,
        candidate_direct_ready=candidate_bundle.input_stats.direct_evidence_ready,
        direct_ready_delta=_bool_delta(
            baseline_bundle.input_stats.direct_evidence_ready,
            candidate_bundle.input_stats.direct_evidence_ready,
        ),
        baseline_correct_with_evidence=baseline_record.correct_with_evidence,
        candidate_correct_with_evidence=candidate_record.correct_with_evidence,
        correct_with_evidence_delta=_bool_delta(
            baseline_record.correct_with_evidence,
            candidate_record.correct_with_evidence,
        ),
        citation_precision_delta=round(
            candidate_record.citation_precision - baseline_record.citation_precision,
            6,
        ),
        citation_recall_delta=round(
            candidate_record.citation_recall - baseline_record.citation_recall,
            6,
        ),
        evidence_order_delta=round(
            candidate_bundle.input_stats.evidence_order_relevance_proxy
            - baseline_bundle.input_stats.evidence_order_relevance_proxy,
            6,
        ),
        citation_count_delta=(
            candidate_record.citation_count - baseline_record.citation_count
        ),
        evidence_count_delta=(
            candidate_bundle.input_stats.evidence_count
            - baseline_bundle.input_stats.evidence_count
        ),
        context_char_delta=(
            candidate_bundle.input_stats.context_char_count
            - baseline_bundle.input_stats.context_char_count
        ),
        input_latency_delta_ms=round(
            candidate_bundle.input_latency_ms - baseline_bundle.input_latency_ms,
            6,
        ),
        regression_tags=tags,
        recommendation=_row_recommendation(tags),
    )


def build_regression_tags(
    *,
    baseline_bundle: _StrategyInputBundle,
    candidate_bundle: _StrategyInputBundle,
    baseline_record: GenerationEvalRecord,
    candidate_record: GenerationEvalRecord,
) -> tuple[str, ...]:
    tags: list[str] = []
    if (
        candidate_bundle.input_stats.direct_evidence_ready
        and not baseline_bundle.input_stats.direct_evidence_ready
    ):
        tags.append("direct_ready_gain")
    if (
        baseline_bundle.input_stats.direct_evidence_ready
        and not candidate_bundle.input_stats.direct_evidence_ready
    ):
        tags.append("direct_ready_loss")
    if candidate_record.citation_precision < baseline_record.citation_precision:
        tags.append("citation_precision_regression")
    if candidate_record.citation_recall > baseline_record.citation_recall:
        tags.append("citation_recall_gain")
    if candidate_record.citation_recall < baseline_record.citation_recall:
        tags.append("citation_recall_regression")
    if candidate_record.correct_with_evidence and not baseline_record.correct_with_evidence:
        tags.append("correctness_gain")
    if baseline_record.correct_with_evidence and not candidate_record.correct_with_evidence:
        tags.append("correctness_regression")
    if (
        candidate_bundle.input_stats.evidence_order_relevance_proxy
        < baseline_bundle.input_stats.evidence_order_relevance_proxy
    ):
        tags.append("evidence_order_regression")
    if candidate_bundle.input_latency_ms < baseline_bundle.input_latency_ms:
        tags.append("latency_improved")
    if (
        {"direct_ready_gain", "citation_recall_gain"} & set(tags)
        and {"citation_precision_regression", "correctness_regression"} & set(tags)
    ):
        tags.append("mixed_tradeoff")
    if {"correctness_regression", "direct_ready_loss"} & set(tags):
        tags.append("guardrail_required")
    if not tags:
        tags.append("no_material_change")
    return tuple(tags)


def build_input_regression_summary(
    *,
    rows: tuple[PlaceStoryInputRegressionRow, ...],
    solar_call_count: int,
) -> PlaceStoryInputRegressionSummary:
    recommended_decision = _summary_decision(rows)
    return PlaceStoryInputRegressionSummary(
        query_count=len(rows),
        direct_ready_gain_count=_count_tag(rows, "direct_ready_gain"),
        direct_ready_loss_count=_count_tag(rows, "direct_ready_loss"),
        correct_with_evidence_regression_count=_count_tag(
            rows,
            "correctness_regression",
        ),
        citation_precision_regression_count=_count_tag(
            rows,
            "citation_precision_regression",
        ),
        citation_recall_gain_count=_count_tag(rows, "citation_recall_gain"),
        evidence_order_regression_count=_count_tag(rows, "evidence_order_regression"),
        mixed_tradeoff_count=_count_tag(rows, "mixed_tradeoff"),
        guardrail_required_count=_count_tag(rows, "guardrail_required"),
        input_latency_improved_count=_count_tag(rows, "latency_improved"),
        solar_call_count=solar_call_count,
        recommended_decision=recommended_decision,
    )


def build_tag_distribution(
    rows: tuple[PlaceStoryInputRegressionRow, ...],
) -> dict[str, int]:
    return dict(
        sorted(
            Counter(tag for row in rows for tag in row.regression_tags).items(),
        ),
    )


def build_public_place_story_input_regression_rows(
    report: PlaceStoryInputRegressionAnalysisReport,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "analysis_id": report.analysis_id,
            "row_type": "summary",
            "query_count": report.summary.query_count,
            "direct_ready_gain_count": report.summary.direct_ready_gain_count,
            "direct_ready_loss_count": report.summary.direct_ready_loss_count,
            "correct_with_evidence_regression_count": (
                report.summary.correct_with_evidence_regression_count
            ),
            "citation_precision_regression_count": (
                report.summary.citation_precision_regression_count
            ),
            "citation_recall_gain_count": report.summary.citation_recall_gain_count,
            "evidence_order_regression_count": (
                report.summary.evidence_order_regression_count
            ),
            "mixed_tradeoff_count": report.summary.mixed_tradeoff_count,
            "guardrail_required_count": report.summary.guardrail_required_count,
            "input_latency_improved_count": report.summary.input_latency_improved_count,
            "solar_call_count": report.summary.solar_call_count,
            "recommended_decision": report.summary.recommended_decision,
        },
    ]
    rows.extend(
        {
            "analysis_id": report.analysis_id,
            "row_type": "query_regression",
            "query_id": row.query_id,
            "query_type": row.query_type,
            "split": row.split,
            "direct_ready_delta": row.direct_ready_delta,
            "correct_with_evidence_delta": row.correct_with_evidence_delta,
            "citation_precision_delta": row.citation_precision_delta,
            "citation_recall_delta": row.citation_recall_delta,
            "evidence_order_delta": row.evidence_order_delta,
            "citation_count_delta": row.citation_count_delta,
            "evidence_count_delta": row.evidence_count_delta,
            "context_char_delta": row.context_char_delta,
            "input_latency_delta_ms": row.input_latency_delta_ms,
            "regression_tags": row.regression_tags,
            "recommendation": row.recommendation,
        }
        for row in report.query_rows
    )
    return rows


def collect_place_story_input_regression_failures(
    report: PlaceStoryInputRegressionAnalysisReport,
) -> list[str]:
    failures: list[str] = []
    if not report.query_rows:
        failures.append("empty_query_rows")
    if report.summary.solar_call_count:
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


def build_place_story_input_regression_markdown(
    report: PlaceStoryInputRegressionAnalysisReport,
) -> str:
    summary = report.summary
    quality = report.output_quality
    tag_rows = "\n".join(
        f"| `{tag}` | {count} |" for tag, count in report.tag_distribution.items()
    )
    query_rows = "\n".join(_format_query_row(row) for row in report.query_rows)
    qualitative_rows = "\n".join(
        f"- `{key}`: {value}" for key, value in report.qualitative_assessment.items()
    )
    return f"""# Place Story Generation Input Regression Analysis Report

## 목적

`parent_doc_context_boost`가 generation input-only 평가에서 만든 trade-off를 query 단위로 분해한다.

이 문서는 Solar Pro 3 live generation 결과가 아니다. raw query, raw evidence, prompt, answer text는 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| analysis_id | `{report.analysis_id}` |
| generated_at_utc | `{report.generated_at_utc}` |
| dataset_path | `{report.dataset_path_alias}` |
| chunks_path | `{report.chunks_path_alias}` |
| baseline_strategy_id | `{report.baseline_strategy_id}` |
| candidate_strategy_id | `{report.candidate_strategy_id}` |
| top_k | {report.top_k} |
| candidate_k | {report.candidate_k} |
| max_context_chars | {report.max_context_chars} |
| resolved_device | `{report.resolved_device}` |

## 정량 요약

| metric | value |
| --- | ---: |
| query_count | {summary.query_count} |
| direct_ready_gain_count | {summary.direct_ready_gain_count} |
| direct_ready_loss_count | {summary.direct_ready_loss_count} |
| correct_with_evidence_regression_count | {summary.correct_with_evidence_regression_count} |
| citation_precision_regression_count | {summary.citation_precision_regression_count} |
| citation_recall_gain_count | {summary.citation_recall_gain_count} |
| evidence_order_regression_count | {summary.evidence_order_regression_count} |
| mixed_tradeoff_count | {summary.mixed_tradeoff_count} |
| guardrail_required_count | {summary.guardrail_required_count} |
| input_latency_improved_count | {summary.input_latency_improved_count} |
| solar_call_count | {summary.solar_call_count} |
| recommended_decision | `{summary.recommended_decision}` |

## Tag Distribution

| tag | count |
| --- | ---: |
{tag_rows}

## Query-level Sanitized Rows

| query_id | direct_delta | correct_delta | precision_delta | recall_delta | evidence_order_delta | latency_delta_ms | tags | recommendation |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
{query_rows}

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


def build_input_regression_qualitative_assessment(
    report: PlaceStoryInputRegressionAnalysisReport,
) -> dict[str, str]:
    return {
        "comparison_scope": (
            "같은 place_story dev query set에서 baseline과 parent_doc_context_boost를 query grain으로 비교했다."
        ),
        "root_cause_boundary": (
            "raw text를 보지 않는 공개 리포트이므로 root cause는 metric tag 수준의 원인 후보로만 기록한다."
        ),
        "decision_boundary": (
            "candidate는 전체 기본값으로 승격하지 않고 hard-case router 또는 reranking guardrail 후보로 제한한다."
        ),
        "llm_call_boundary": "Solar Pro 3 호출 없이 input-only citation assembly만 평가했다.",
        "data_mart_grain": (
            "`fact_place_story_input_regression`의 grain은 query-pair이며 fact에는 metric delta와 tag만 둔다."
        ),
        "next_action": _next_action(report),
    }


def _records_by_query_id(
    *,
    strategy_id: StrategyId,
    bundles: tuple[_StrategyInputBundle, ...],
) -> dict[str, GenerationEvalRecord]:
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
    return {
        record.query_id: record
        for record in build_generation_eval_records(inputs=inputs)
    }


def _bundles_by_query_id(
    bundles: tuple[_StrategyInputBundle, ...],
) -> dict[str, _StrategyInputBundle]:
    return {bundle.item.query.query_id: bundle for bundle in bundles}


def _summary_decision(rows: tuple[PlaceStoryInputRegressionRow, ...]) -> str:
    if _count_tag(rows, "guardrail_required"):
        return "require_guardrail_before_live_generation"
    if _count_tag(rows, "mixed_tradeoff"):
        return "limit_candidate_to_router_or_hard_subset"
    if _count_tag(rows, "direct_ready_gain") and not _count_tag(
        rows,
        "citation_precision_regression",
    ):
        return "promote_candidate_to_live_plan_review"
    return "keep_baseline_as_default"


def _row_recommendation(tags: tuple[str, ...]) -> str:
    tag_set = set(tags)
    if "guardrail_required" in tag_set:
        return "exclude_from_candidate_until_guardrail"
    if "mixed_tradeoff" in tag_set:
        return "manual_review_before_live_call"
    if "direct_ready_gain" in tag_set and "citation_precision_regression" not in tag_set:
        return "candidate_router_positive"
    if "no_material_change" in tag_set:
        return "keep_baseline"
    return "monitor"


def _next_action(report: PlaceStoryInputRegressionAnalysisReport) -> str:
    if report.summary.recommended_decision == "require_guardrail_before_live_generation":
        return "candidate 적용 조건을 제한하는 reranking guardrail 또는 query router를 먼저 설계한다."
    if report.summary.recommended_decision == "limit_candidate_to_router_or_hard_subset":
        return "candidate를 전체 기본값이 아니라 hard subset/router 후보로 제한하는 계획을 작성한다."
    return "Solar Pro 3 live paired comparison 계획을 작성하되 대량 호출 전 승인을 받는다."


def _conclusion_text(report: PlaceStoryInputRegressionAnalysisReport) -> str:
    if report.summary.recommended_decision == "require_guardrail_before_live_generation":
        return (
            "`parent_doc_context_boost`는 일부 입력을 개선했지만 correctness regression이 있어 "
            "guardrail 없이 live generation에 투입하지 않는다."
        )
    if report.summary.recommended_decision == "limit_candidate_to_router_or_hard_subset":
        return (
            "`parent_doc_context_boost`는 hard-case 보정 후보로 남긴다. "
            "전체 기본 검색 전략으로 승격하지 않는다."
        )
    return (
        "현재 결과만으로는 청킹 재실험보다 candidate 적용 조건을 먼저 정교화하는 것이 우선이다."
    )


def _count_tag(rows: tuple[PlaceStoryInputRegressionRow, ...], tag: str) -> int:
    return sum(1 for row in rows if tag in row.regression_tags)


def _bool_delta(baseline: bool, candidate: bool) -> int:
    return int(candidate) - int(baseline)


def _analysis_id(rows: tuple[PlaceStoryInputRegressionRow, ...]) -> str:
    payload = [row.model_dump(mode="json") for row in rows]
    digest = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"),
    ).hexdigest()[:8]
    return f"place-story-input-regression-q{len(rows)}-{digest}"


def _format_query_row(row: PlaceStoryInputRegressionRow) -> str:
    tags = ", ".join(f"`{tag}`" for tag in row.regression_tags)
    return (
        f"| `{row.query_id}` | {row.direct_ready_delta} | "
        f"{row.correct_with_evidence_delta} | "
        f"{row.citation_precision_delta:.6f} | "
        f"{row.citation_recall_delta:.6f} | "
        f"{row.evidence_order_delta:.6f} | "
        f"{row.input_latency_delta_ms:.6f} | {tags} | "
        f"`{row.recommendation}` |"
    )


def main() -> int:
    args = _parse_args()
    report = run_place_story_generation_input_regression_analysis(
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
    failures = collect_place_story_input_regression_failures(report)
    print(
        "place_story_generation_input_regression_analysis "
        f"status={'PASS' if not failures else 'FAIL'} "
        f"decision={report.summary.recommended_decision} "
        f"mixed_tradeoff={report.summary.mixed_tradeoff_count} "
        f"guardrail_required={report.summary.guardrail_required_count} "
        f"device={report.resolved_device} "
        f"failures={len(failures)}",
    )
    return 0 if not failures else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze place_story input-only regression tags without raw text.",
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
