from __future__ import annotations

import argparse
import hashlib
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.application.citation_rag import CitationRagAnswerAssembler, CitationRagAssemblerConfig
from app.core.project_paths import project_path
from app.domain.generation import CitationRagAnswer
from app.domain.generation_eval import (
    GenerationEvalInput,
    GenerationEvalRecord,
    GenerationEvalReport,
    GenerationEvalUsage,
    build_generation_eval_dataset_fingerprint,
    build_generation_eval_records,
    build_generation_eval_report,
)
from app.domain.retrieval import QueryType
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    measure_public_retrieval_artifact_quality,
)
from app.providers.llm.base import CitationDraftProvider, CitationDraftRequest
from pipelines.run_place_story_guarded_boost_comparison import (
    BASELINE_STRATEGY_ID,
    CANDIDATE_STRATEGY_ID,
    GUARDED_BOOST_STRATEGY_ID,
    ROUTER_POLICY_ID,
    build_guarded_route_row,
    _records_by_query_id,
)
from pipelines.run_place_story_top_rank_coverage_repair import (
    DEFAULT_CANDIDATE_K,
    DEFAULT_EMBEDDING_CACHE_DIR,
    DEFAULT_PLACE_CATALOG_PATH,
    DEFAULT_TOP_K,
    _build_execution_context,
    _load_place_story_dev_items,
    _validate_private_rows_path,
    _write_jsonl_rows,
)
from pipelines.run_place_story_generation_input_only_eval import (
    _StrategyInputBundle,
    _build_strategy_input_bundle,
    _load_child_chunks_by_id,
)
from pipelines.run_solar_generation_baseline import (
    DEFAULT_ENV_FILE_PATH,
    load_env_file_into_process,
)
from pipelines.run_solar_guarded_boost_live_dry_run import (
    ANSWER_CONTRACT_VERSION,
    ANSWER_POLICY_ID,
    DEFAULT_LIVE_CALL_HARD_CAP,
    DEFAULT_REPORT_PATH as DEFAULT_DRY_RUN_REPORT_PATH,
    DEFAULT_RESULT_ROWS_PATH as DEFAULT_DRY_RUN_RESULT_ROWS_PATH,
    ENDPOINT_ALIAS,
    MODEL_ID,
    PROVIDER_CONFIG_ID_ALIAS,
    SOLAR_GUARDED_BOOST_LIVE_DRY_RUN_REPORT_VERSION,
    SolarGuardedBoostLiveDryRunReport,
    collect_solar_guarded_boost_live_dry_run_failures,
    run_solar_guarded_boost_live_dry_run,
    _bundles_by_query_id,
)
from pipelines.run_solar_live_generation_smoke import (
    DEFAULT_CHUNKS_PATH,
    DEFAULT_DATASET_PATH,
    SolarLiveProviderUsageTotals,
    _ProviderRunContext,
    _answer_provider_kind,
    _build_provider_context,
    _format_query_type_summary_row,
    build_evidence_context,
)


SOLAR_GUARDED_BOOST_LIVE_COMPARISON_READINESS_REPORT_VERSION = (
    "solar-guarded-boost-live-comparison-readiness/v1"
)
SOLAR_GUARDED_BOOST_LIVE_COMPARISON_REPORT_VERSION = (
    "solar-guarded-boost-live-comparison-report/v1"
)
DEFAULT_REPORT_PATH = (
    Path("evals")
    / "reports"
    / "solar_guarded_boost_live_comparison_readiness_report.md"
)
DEFAULT_LIVE_REPORT_PATH = (
    Path("evals")
    / "reports"
    / "solar_guarded_boost_live_comparison_report.md"
)
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "solar_guarded_boost_live_comparison_readiness_rows.jsonl"
)
DEFAULT_LIVE_RESULT_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "solar_guarded_boost_live_comparison_rows.jsonl"
)
DEFAULT_LIVE_PREFLIGHT_DRY_RUN_REPORT_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "solar_guarded_boost_live_comparison_preflight_dry_run_report.md"
)

ExecutionMode = Literal["dry_run_only"]
ReadinessDecision = Literal[
    "ready_for_live_execution_approval",
    "blocked_before_live_execution",
]


class SolarGuardedBoostLiveComparisonModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SolarGuardedBoostLiveComparisonGateSummary(SolarGuardedBoostLiveComparisonModel):
    execution_mode: ExecutionMode
    live_execution_requested: bool
    live_execution_confirmed: bool
    live_call_executed: bool
    approval_required_for_live: bool
    dry_run_gate_passed: bool
    call_cap_passed: bool
    public_safety_passed: bool
    expected_total_live_call_count: int = Field(ge=0)
    live_call_hard_cap: int = Field(ge=1)
    baseline_live_call_count: int = Field(ge=0)
    candidate_live_call_count: int = Field(ge=0)
    reused_candidate_count: int = Field(ge=0)
    changed_candidate_input_count: int = Field(ge=0)
    solar_call_count: int = Field(ge=0)
    readiness_decision: ReadinessDecision


class SolarGuardedBoostLiveComparisonReadinessReport(
    SolarGuardedBoostLiveComparisonModel,
):
    report_version: str = SOLAR_GUARDED_BOOST_LIVE_COMPARISON_READINESS_REPORT_VERSION
    readiness_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    dry_run_report_version: str = Field(min_length=1)
    dry_run_id: str = Field(min_length=1)
    dataset_path_alias: str = Field(min_length=1)
    chunks_path_alias: str = Field(min_length=1)
    baseline_strategy_id: str = Field(min_length=1)
    candidate_strategy_id: str = Field(min_length=1)
    guarded_strategy_id: str = Field(min_length=1)
    router_policy_id: str = Field(min_length=1)
    answer_contract_version: str = Field(min_length=1)
    answer_policy_id: str = Field(min_length=1)
    provider_config_id_alias: str = Field(min_length=1)
    endpoint_alias: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    top_k: int = Field(ge=1)
    candidate_k: int = Field(ge=1)
    max_context_chars: int = Field(ge=1)
    resolved_device: str = Field(min_length=1)
    gate_summary: SolarGuardedBoostLiveComparisonGateSummary
    reuse_decision_distribution: dict[str, int]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


class SolarGuardedBoostLiveCallSummary(SolarGuardedBoostLiveComparisonModel):
    query_count: int = Field(ge=0)
    baseline_live_call_count: int = Field(ge=0)
    candidate_live_call_count: int = Field(ge=0)
    reused_candidate_count: int = Field(ge=0)
    changed_candidate_input_count: int = Field(ge=0)
    expected_total_live_call_count: int = Field(ge=0)
    actual_solar_call_count: int = Field(ge=0)
    live_call_hard_cap: int = Field(ge=1)
    baseline_prompt_tokens: int = Field(ge=0)
    baseline_completion_tokens: int = Field(ge=0)
    baseline_total_tokens: int = Field(ge=0)
    candidate_prompt_tokens: int = Field(ge=0)
    candidate_completion_tokens: int = Field(ge=0)
    candidate_total_tokens: int = Field(ge=0)
    total_prompt_tokens: int = Field(ge=0)
    total_completion_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    estimated_cost: float = Field(ge=0.0)


class SolarGuardedBoostLivePairDelta(SolarGuardedBoostLiveComparisonModel):
    query_id: str = Field(min_length=1)
    query_type: QueryType
    route_decision: str = Field(min_length=1)
    reuse_decision: str = Field(min_length=1)
    baseline_correct_with_evidence: bool
    candidate_correct_with_evidence: bool
    correct_with_evidence_delta: int
    baseline_citation_precision: float = Field(ge=0.0, le=1.0)
    candidate_citation_precision: float = Field(ge=0.0, le=1.0)
    citation_precision_delta: float
    baseline_citation_recall: float = Field(ge=0.0, le=1.0)
    candidate_citation_recall: float = Field(ge=0.0, le=1.0)
    citation_recall_delta: float
    baseline_unsupported_claim: bool
    candidate_unsupported_claim: bool
    unsupported_claim_delta: int
    baseline_citation_count: int = Field(ge=0)
    candidate_citation_count: int = Field(ge=0)
    citation_count_delta: int
    latency_ms_delta: float


class SolarGuardedBoostLiveQueryTypeDelta(SolarGuardedBoostLiveComparisonModel):
    query_type: QueryType
    eval_count: int = Field(ge=0)
    correct_with_evidence_delta: float
    citation_precision_delta: float
    citation_recall_delta: float
    unsupported_claim_rate_delta: float
    latency_p95_ms_delta: float


class SolarGuardedBoostLiveComparisonReport(SolarGuardedBoostLiveComparisonModel):
    report_version: str = SOLAR_GUARDED_BOOST_LIVE_COMPARISON_REPORT_VERSION
    comparison_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    dataset_fingerprint: str = Field(min_length=8)
    dry_run_id: str = Field(min_length=1)
    dataset_path_alias: str = Field(min_length=1)
    chunks_path_alias: str = Field(min_length=1)
    baseline_strategy_id: str = Field(min_length=1)
    candidate_strategy_id: str = Field(min_length=1)
    guarded_strategy_id: str = Field(min_length=1)
    router_policy_id: str = Field(min_length=1)
    answer_contract_version: str = Field(min_length=1)
    answer_policy_id: str = Field(min_length=1)
    provider_config_id: str = Field(min_length=1)
    endpoint_alias: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    top_k: int = Field(ge=1)
    candidate_k: int = Field(ge=1)
    max_context_chars: int = Field(ge=1)
    live_call_summary: SolarGuardedBoostLiveCallSummary
    baseline_report: GenerationEvalReport
    candidate_report: GenerationEvalReport
    paired_deltas: tuple[SolarGuardedBoostLivePairDelta, ...]
    query_type_deltas: tuple[SolarGuardedBoostLiveQueryTypeDelta, ...]
    adoption_decision: str = Field(min_length=1)
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


@dataclass(frozen=True)
class _LiveAnswerResult:
    answer: CitationRagAnswer
    usage: GenerationEvalUsage
    provider_usage: Any


def run_solar_guarded_boost_live_comparison(
    *,
    chunks_path: Path = DEFAULT_CHUNKS_PATH,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    place_catalog_path: Path = DEFAULT_PLACE_CATALOG_PATH,
    embedding_cache_dir: Path = DEFAULT_EMBEDDING_CACHE_DIR,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
    dry_run_report_path: Path = DEFAULT_DRY_RUN_REPORT_PATH,
    dry_run_result_rows_path: Path = DEFAULT_DRY_RUN_RESULT_ROWS_PATH,
    top_k: int = DEFAULT_TOP_K,
    candidate_k: int = DEFAULT_CANDIDATE_K,
    max_context_chars: int = 11000,
    live_call_hard_cap: int = DEFAULT_LIVE_CALL_HARD_CAP,
    execute_live: bool = False,
    confirm_live_execution: bool = False,
) -> SolarGuardedBoostLiveComparisonReadinessReport:
    validate_live_execution_request(
        execute_live=execute_live,
        confirm_live_execution=confirm_live_execution,
    )
    _validate_private_rows_path(result_rows_path, label="result")
    dry_run_report = run_solar_guarded_boost_live_dry_run(
        chunks_path=chunks_path,
        dataset_path=dataset_path,
        place_catalog_path=place_catalog_path,
        embedding_cache_dir=embedding_cache_dir,
        report_path=dry_run_report_path,
        result_rows_path=dry_run_result_rows_path,
        top_k=top_k,
        candidate_k=candidate_k,
        max_context_chars=max_context_chars,
        live_call_hard_cap=live_call_hard_cap,
    )
    provisional = build_solar_guarded_boost_live_comparison_readiness_report(
        dry_run_report=dry_run_report,
        live_execution_requested=execute_live,
        live_execution_confirmed=confirm_live_execution,
    )
    provisional_rows = build_public_solar_guarded_boost_live_comparison_rows(
        provisional,
    )
    provisional_text = build_solar_guarded_boost_live_comparison_markdown(provisional)
    report = build_solar_guarded_boost_live_comparison_readiness_report(
        dry_run_report=dry_run_report,
        live_execution_requested=execute_live,
        live_execution_confirmed=confirm_live_execution,
        result_rows=provisional_rows,
        report_text=provisional_text,
    )
    failures = collect_solar_guarded_boost_live_comparison_failures(report)
    if failures:
        raise ValueError(
            f"solar guarded boost live comparison readiness gate failed: {failures}",
        )

    _write_jsonl_rows(
        path=result_rows_path,
        rows=build_public_solar_guarded_boost_live_comparison_rows(report),
    )
    resolved_report_path = project_path(report_path)
    resolved_report_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_report_path.write_text(
        build_solar_guarded_boost_live_comparison_markdown(report),
        encoding="utf-8",
    )
    return report


def run_solar_guarded_boost_live_paired_comparison(
    *,
    chunks_path: Path = DEFAULT_CHUNKS_PATH,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    place_catalog_path: Path = DEFAULT_PLACE_CATALOG_PATH,
    embedding_cache_dir: Path = DEFAULT_EMBEDDING_CACHE_DIR,
    report_path: Path = DEFAULT_LIVE_REPORT_PATH,
    result_rows_path: Path = DEFAULT_LIVE_RESULT_ROWS_PATH,
    dry_run_report_path: Path = DEFAULT_LIVE_PREFLIGHT_DRY_RUN_REPORT_PATH,
    dry_run_result_rows_path: Path = DEFAULT_DRY_RUN_RESULT_ROWS_PATH,
    env_file_path: Path | None = DEFAULT_ENV_FILE_PATH,
    top_k: int = DEFAULT_TOP_K,
    candidate_k: int = DEFAULT_CANDIDATE_K,
    max_context_chars: int = 11000,
    live_call_hard_cap: int = DEFAULT_LIVE_CALL_HARD_CAP,
    execute_live: bool = False,
    confirm_live_execution: bool = False,
    draft_provider: CitationDraftProvider | None = None,
) -> SolarGuardedBoostLiveComparisonReport:
    validate_live_execution_approval(
        execute_live=execute_live,
        confirm_live_execution=confirm_live_execution,
    )
    _validate_private_rows_path(result_rows_path, label="result")
    if draft_provider is None and env_file_path is not None:
        load_env_file_into_process(env_file_path)

    dry_run_report = run_solar_guarded_boost_live_dry_run(
        chunks_path=chunks_path,
        dataset_path=dataset_path,
        place_catalog_path=place_catalog_path,
        embedding_cache_dir=embedding_cache_dir,
        report_path=dry_run_report_path,
        result_rows_path=dry_run_result_rows_path,
        top_k=top_k,
        candidate_k=candidate_k,
        max_context_chars=max_context_chars,
        live_call_hard_cap=live_call_hard_cap,
    )
    dry_run_failures = collect_solar_guarded_boost_live_dry_run_failures(dry_run_report)
    if dry_run_failures:
        raise ValueError(
            f"solar guarded boost live preflight dry-run failed: {dry_run_failures}",
        )
    if dry_run_report.summary.expected_total_live_call_count > live_call_hard_cap:
        raise ValueError("expected live call count exceeds hard cap")

    provider, provider_context = _build_provider_context(draft_provider)
    items = _load_place_story_dev_items(dataset_path=dataset_path)
    context = _build_execution_context(
        chunks_path=chunks_path,
        place_catalog_path=place_catalog_path,
        embedding_cache_dir=embedding_cache_dir,
    )
    child_chunks_by_id = _load_child_chunks_by_id(chunks_path)
    baseline_bundles = tuple(
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
    )
    candidate_bundles = tuple(
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
    )
    baseline_inputs, candidate_inputs, live_summary = build_live_generation_inputs(
        baseline_bundles=baseline_bundles,
        candidate_bundles=candidate_bundles,
        dry_run_report=dry_run_report,
        draft_provider=provider,
        provider_context=provider_context,
        child_chunks_by_id=child_chunks_by_id,
        max_context_chars=max_context_chars,
    )
    provisional_report = build_solar_guarded_boost_live_paired_comparison_report(
        baseline_inputs=baseline_inputs,
        candidate_inputs=candidate_inputs,
        dry_run_report=dry_run_report,
        provider_context=provider_context,
        live_call_summary=live_summary,
    )
    provisional_text = build_solar_guarded_boost_live_paired_comparison_markdown(
        provisional_report,
    )
    report = build_solar_guarded_boost_live_paired_comparison_report(
        baseline_inputs=baseline_inputs,
        candidate_inputs=candidate_inputs,
        dry_run_report=dry_run_report,
        provider_context=provider_context,
        live_call_summary=live_summary,
        report_text=provisional_text,
    )
    failures = collect_solar_guarded_boost_live_paired_comparison_failures(report)
    if failures:
        raise ValueError(
            f"solar guarded boost live paired comparison gate failed: {failures}",
        )

    _write_jsonl_rows(
        path=result_rows_path,
        rows=build_public_solar_guarded_boost_live_paired_comparison_rows(report),
    )
    resolved_report_path = project_path(report_path)
    resolved_report_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_report_path.write_text(
        build_solar_guarded_boost_live_paired_comparison_markdown(report),
        encoding="utf-8",
    )
    return report


def validate_live_execution_request(
    *,
    execute_live: bool,
    confirm_live_execution: bool,
) -> None:
    if confirm_live_execution and not execute_live:
        raise ValueError("confirm_live_execution requires execute_live")
    if execute_live:
        raise PermissionError(
            "live Solar Pro 3 execution is blocked in HD-SOLAR-015; "
            "request HD-SOLAR-016 approval before enabling live calls",
        )


def validate_live_execution_approval(
    *,
    execute_live: bool,
    confirm_live_execution: bool,
) -> None:
    if not execute_live:
        raise PermissionError("live execution requires --execute-live")
    if not confirm_live_execution:
        raise PermissionError("live execution requires --confirm-live-execution")


def build_solar_guarded_boost_live_comparison_readiness_report(
    *,
    dry_run_report: SolarGuardedBoostLiveDryRunReport,
    live_execution_requested: bool,
    live_execution_confirmed: bool,
    result_rows: list[dict[str, Any]] | None = None,
    report_text: str = "",
) -> SolarGuardedBoostLiveComparisonReadinessReport:
    gate_summary = build_live_comparison_gate_summary(
        dry_run_report=dry_run_report,
        live_execution_requested=live_execution_requested,
        live_execution_confirmed=live_execution_confirmed,
    )
    readiness_id = _readiness_id(
        dry_run_id=dry_run_report.dry_run_id,
        gate_summary=gate_summary,
    )
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=SOLAR_GUARDED_BOOST_LIVE_COMPARISON_READINESS_REPORT_VERSION,
        run_id=readiness_id,
        result_rows=result_rows or [],
        report_text=report_text,
    )
    report = SolarGuardedBoostLiveComparisonReadinessReport(
        readiness_id=readiness_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        dry_run_report_version=SOLAR_GUARDED_BOOST_LIVE_DRY_RUN_REPORT_VERSION,
        dry_run_id=dry_run_report.dry_run_id,
        dataset_path_alias=dry_run_report.dataset_path_alias,
        chunks_path_alias=dry_run_report.chunks_path_alias,
        baseline_strategy_id=BASELINE_STRATEGY_ID,
        candidate_strategy_id=CANDIDATE_STRATEGY_ID,
        guarded_strategy_id=GUARDED_BOOST_STRATEGY_ID,
        router_policy_id=ROUTER_POLICY_ID,
        answer_contract_version=ANSWER_CONTRACT_VERSION,
        answer_policy_id=ANSWER_POLICY_ID,
        provider_config_id_alias=PROVIDER_CONFIG_ID_ALIAS,
        endpoint_alias=ENDPOINT_ALIAS,
        model_id=MODEL_ID,
        top_k=dry_run_report.top_k,
        candidate_k=dry_run_report.candidate_k,
        max_context_chars=dry_run_report.max_context_chars,
        resolved_device=dry_run_report.resolved_device,
        gate_summary=gate_summary,
        reuse_decision_distribution=dry_run_report.reuse_decision_distribution,
        output_quality=output_quality,
        qualitative_assessment={},
    )
    return report.model_copy(
        update={
            "qualitative_assessment": build_live_comparison_readiness_assessment(report),
        },
    )


def build_live_comparison_gate_summary(
    *,
    dry_run_report: SolarGuardedBoostLiveDryRunReport,
    live_execution_requested: bool,
    live_execution_confirmed: bool,
) -> SolarGuardedBoostLiveComparisonGateSummary:
    dry_run_failures = collect_solar_guarded_boost_live_dry_run_failures(dry_run_report)
    dry_run_gate_passed = not dry_run_failures
    call_cap_passed = not dry_run_report.summary.hard_cap_exceeded
    public_safety_passed = (
        dry_run_report.output_quality.public_raw_text_leakage_count == 0
        and dry_run_report.output_quality.private_path_leakage_count == 0
        and dry_run_report.output_quality.secret_like_leakage_count == 0
        and dry_run_report.output_quality.forbidden_result_field_count == 0
    )
    ready = (
        dry_run_gate_passed
        and call_cap_passed
        and public_safety_passed
        and dry_run_report.summary.solar_call_count == 0
    )
    return SolarGuardedBoostLiveComparisonGateSummary(
        execution_mode="dry_run_only",
        live_execution_requested=live_execution_requested,
        live_execution_confirmed=live_execution_confirmed,
        live_call_executed=False,
        approval_required_for_live=True,
        dry_run_gate_passed=dry_run_gate_passed,
        call_cap_passed=call_cap_passed,
        public_safety_passed=public_safety_passed,
        expected_total_live_call_count=(
            dry_run_report.summary.expected_total_live_call_count
        ),
        live_call_hard_cap=dry_run_report.summary.live_call_hard_cap,
        baseline_live_call_count=dry_run_report.summary.baseline_live_call_count,
        candidate_live_call_count=dry_run_report.summary.candidate_live_call_count,
        reused_candidate_count=dry_run_report.summary.reused_candidate_count,
        changed_candidate_input_count=(
            dry_run_report.summary.changed_candidate_input_count
        ),
        solar_call_count=0,
        readiness_decision=(
            "ready_for_live_execution_approval"
            if ready
            else "blocked_before_live_execution"
        ),
    )


def build_live_generation_inputs(
    *,
    baseline_bundles: tuple[_StrategyInputBundle, ...],
    candidate_bundles: tuple[_StrategyInputBundle, ...],
    dry_run_report: SolarGuardedBoostLiveDryRunReport,
    draft_provider: CitationDraftProvider,
    provider_context: _ProviderRunContext,
    child_chunks_by_id: dict[str, Any],
    max_context_chars: int,
) -> tuple[
    list[GenerationEvalInput],
    list[GenerationEvalInput],
    SolarGuardedBoostLiveCallSummary,
]:
    baseline_by_query = _bundles_by_query_id(baseline_bundles)
    candidate_by_query = _bundles_by_query_id(candidate_bundles)
    dry_run_by_query = {row.query_id: row for row in dry_run_report.rows}
    baseline_records = _records_by_query_id(
        strategy_id=BASELINE_STRATEGY_ID,
        bundles=baseline_bundles,
    )
    candidate_records = _records_by_query_id(
        strategy_id=CANDIDATE_STRATEGY_ID,
        bundles=candidate_bundles,
    )
    route_rows = {
        query_id: build_guarded_route_row(
            baseline_bundle=baseline_by_query[query_id],
            candidate_bundle=candidate_by_query[query_id],
            baseline_record=baseline_records[query_id],
            candidate_record=candidate_records[query_id],
        )
        for query_id in sorted(baseline_by_query)
    }

    baseline_inputs: list[GenerationEvalInput] = []
    candidate_inputs: list[GenerationEvalInput] = []
    baseline_results: dict[str, _LiveAnswerResult] = {}
    baseline_usage_totals = SolarLiveProviderUsageTotals()
    candidate_usage_totals = SolarLiveProviderUsageTotals()

    for query_id in sorted(baseline_by_query):
        baseline_bundle = baseline_by_query[query_id]
        baseline_result = answer_strategy_bundle_with_provider(
            bundle=baseline_bundle,
            draft_provider=draft_provider,
            provider_context=provider_context,
            child_chunks_by_id=child_chunks_by_id,
            max_context_chars=max_context_chars,
        )
        baseline_results[query_id] = baseline_result
        baseline_usage_totals = baseline_usage_totals.add(baseline_result.provider_usage)
        baseline_inputs.append(
            generation_input_for_bundle(
                bundle=baseline_bundle,
                answer=baseline_result.answer,
                retrieval_run_label=BASELINE_STRATEGY_ID,
                provider_config_id=provider_context.provider_config_id,
                usage=baseline_result.usage,
            ),
        )

    for query_id in sorted(candidate_by_query):
        route = route_rows[query_id]
        dry_run_row = dry_run_by_query[query_id]
        baseline_result = baseline_results[query_id]
        guarded_bundle = (
            candidate_by_query[query_id]
            if route.selected_strategy_id == GUARDED_BOOST_STRATEGY_ID
            else baseline_by_query[query_id]
        )
        if dry_run_row.candidate_live_call_required:
            candidate_result = answer_strategy_bundle_with_provider(
                bundle=guarded_bundle,
                draft_provider=draft_provider,
                provider_context=provider_context,
                child_chunks_by_id=child_chunks_by_id,
                max_context_chars=max_context_chars,
            )
            candidate_usage_totals = candidate_usage_totals.add(
                candidate_result.provider_usage,
            )
        else:
            candidate_result = reuse_baseline_answer_result(baseline_result)
        candidate_inputs.append(
            generation_input_for_bundle(
                bundle=guarded_bundle,
                answer=candidate_result.answer,
                retrieval_run_label=GUARDED_BOOST_STRATEGY_ID,
                provider_config_id=provider_context.provider_config_id,
                usage=candidate_result.usage,
            ),
        )

    live_summary = build_live_call_summary(
        dry_run_report=dry_run_report,
        baseline_usage_totals=baseline_usage_totals,
        candidate_usage_totals=candidate_usage_totals,
        actual_baseline_solar_call_count=sum(
            item.usage.solar_call_count for item in baseline_inputs
        ),
        actual_candidate_solar_call_count=sum(
            item.usage.solar_call_count for item in candidate_inputs
        ),
    )
    return baseline_inputs, candidate_inputs, live_summary


def answer_strategy_bundle_with_provider(
    *,
    bundle: _StrategyInputBundle,
    draft_provider: CitationDraftProvider,
    provider_context: _ProviderRunContext,
    child_chunks_by_id: dict[str, Any],
    max_context_chars: int,
) -> _LiveAnswerResult:
    started = time.perf_counter()
    assembler = _assembler(
        provider=provider_context.provider_kind,
        model_id=provider_context.model_id,
    )
    zero_provider_usage = _zero_provider_usage()
    if bundle.item.query.expected_behavior == "abstain" or not bundle.evidence_pack.evidence:
        answer = assembler.assemble(
            item=bundle.item,
            evidence_pack=bundle.evidence_pack,
            place_ids=tuple(bundle.item.metadata.place_ids),
        )
        return _LiveAnswerResult(
            answer=answer,
            usage=GenerationEvalUsage(
                latency_ms=round((time.perf_counter() - started) * 1000, 6),
                solar_call_count=0,
            ),
            provider_usage=zero_provider_usage,
        )

    evidence_context = build_evidence_context(
        retrieval=type(
            "_GuardedBoostLiveRetrieval",
            (),
            {"evidence_pack": bundle.evidence_pack},
        )(),
        child_chunks_by_id=child_chunks_by_id,
        max_chars=max_context_chars,
    )
    result = draft_provider.generate_draft(
        CitationDraftRequest(
            query_id=bundle.item.query.query_id,
            query_type=bundle.item.query.query_type,
            query_text=bundle.item.query.query_text,
            evidence_context=evidence_context,
            place_ids=tuple(bundle.item.metadata.place_ids),
            language=bundle.item.query.language,
        ),
    )
    answer = _assembler(
        provider=_answer_provider_kind(result.provider),
        model_id=result.model_id,
    ).assemble(
        item=bundle.item,
        evidence_pack=bundle.evidence_pack,
        draft=result.draft,
        place_ids=tuple(bundle.item.metadata.place_ids),
    )
    return _LiveAnswerResult(
        answer=answer,
        usage=GenerationEvalUsage(
            latency_ms=result.usage.latency_ms,
            solar_call_count=result.usage.api_call_count,
            estimated_cost=result.usage.estimated_cost,
        ),
        provider_usage=result.usage,
    )


def reuse_baseline_answer_result(
    baseline_result: _LiveAnswerResult,
) -> _LiveAnswerResult:
    return _LiveAnswerResult(
        answer=baseline_result.answer,
        usage=GenerationEvalUsage(
            latency_ms=baseline_result.usage.latency_ms,
            solar_call_count=0,
            estimated_cost=0.0,
        ),
        provider_usage=_zero_provider_usage(),
    )


def generation_input_for_bundle(
    *,
    bundle: _StrategyInputBundle,
    answer: CitationRagAnswer,
    retrieval_run_label: str,
    provider_config_id: str,
    usage: GenerationEvalUsage,
) -> GenerationEvalInput:
    return GenerationEvalInput(
        item=bundle.item,
        answer=answer,
        packing_policy_id=bundle.evidence_pack.policy_id,
        retrieval_run_label=retrieval_run_label,
        provider_config_id=provider_config_id,
        usage=usage,
    )


def build_live_call_summary(
    *,
    dry_run_report: SolarGuardedBoostLiveDryRunReport,
    baseline_usage_totals: SolarLiveProviderUsageTotals,
    candidate_usage_totals: SolarLiveProviderUsageTotals,
    actual_baseline_solar_call_count: int,
    actual_candidate_solar_call_count: int,
) -> SolarGuardedBoostLiveCallSummary:
    total_prompt_tokens = (
        baseline_usage_totals.prompt_tokens + candidate_usage_totals.prompt_tokens
    )
    total_completion_tokens = (
        baseline_usage_totals.completion_tokens
        + candidate_usage_totals.completion_tokens
    )
    total_tokens = baseline_usage_totals.total_tokens + candidate_usage_totals.total_tokens
    return SolarGuardedBoostLiveCallSummary(
        query_count=dry_run_report.summary.query_count,
        baseline_live_call_count=dry_run_report.summary.baseline_live_call_count,
        candidate_live_call_count=dry_run_report.summary.candidate_live_call_count,
        reused_candidate_count=dry_run_report.summary.reused_candidate_count,
        changed_candidate_input_count=dry_run_report.summary.changed_candidate_input_count,
        expected_total_live_call_count=(
            dry_run_report.summary.expected_total_live_call_count
        ),
        actual_solar_call_count=(
            actual_baseline_solar_call_count + actual_candidate_solar_call_count
        ),
        live_call_hard_cap=dry_run_report.summary.live_call_hard_cap,
        baseline_prompt_tokens=baseline_usage_totals.prompt_tokens,
        baseline_completion_tokens=baseline_usage_totals.completion_tokens,
        baseline_total_tokens=baseline_usage_totals.total_tokens,
        candidate_prompt_tokens=candidate_usage_totals.prompt_tokens,
        candidate_completion_tokens=candidate_usage_totals.completion_tokens,
        candidate_total_tokens=candidate_usage_totals.total_tokens,
        total_prompt_tokens=total_prompt_tokens,
        total_completion_tokens=total_completion_tokens,
        total_tokens=total_tokens,
        estimated_cost=round(
            baseline_usage_totals.estimated_cost + candidate_usage_totals.estimated_cost,
            6,
        ),
    )


def build_solar_guarded_boost_live_paired_comparison_report(
    *,
    baseline_inputs: list[GenerationEvalInput],
    candidate_inputs: list[GenerationEvalInput],
    dry_run_report: SolarGuardedBoostLiveDryRunReport,
    provider_context: _ProviderRunContext,
    live_call_summary: SolarGuardedBoostLiveCallSummary,
    report_text: str = "",
) -> SolarGuardedBoostLiveComparisonReport:
    validate_live_paired_comparison_inputs(
        baseline_inputs=baseline_inputs,
        candidate_inputs=candidate_inputs,
    )
    baseline_report = build_generation_eval_report(inputs=baseline_inputs)
    candidate_report = build_generation_eval_report(inputs=candidate_inputs)
    baseline_records = build_generation_eval_records(baseline_inputs)
    candidate_records = build_generation_eval_records(candidate_inputs)
    paired_deltas = tuple(
        build_guarded_boost_live_pair_deltas(
            baseline_records=baseline_records,
            candidate_records=candidate_records,
            dry_run_report=dry_run_report,
        ),
    )
    query_type_deltas = tuple(build_guarded_boost_live_query_type_deltas(paired_deltas))
    public_rows = build_public_solar_guarded_boost_live_paired_comparison_rows_from_deltas(
        paired_deltas,
    )
    comparison_id = build_guarded_boost_live_comparison_id(
        baseline_records=baseline_records,
        candidate_records=candidate_records,
        dry_run_id=dry_run_report.dry_run_id,
    )
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=SOLAR_GUARDED_BOOST_LIVE_COMPARISON_REPORT_VERSION,
        run_id=comparison_id,
        result_rows=public_rows,
        report_text=report_text,
    )
    report = SolarGuardedBoostLiveComparisonReport(
        comparison_id=comparison_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        dataset_fingerprint=build_generation_eval_dataset_fingerprint(baseline_inputs),
        dry_run_id=dry_run_report.dry_run_id,
        dataset_path_alias=dry_run_report.dataset_path_alias,
        chunks_path_alias=dry_run_report.chunks_path_alias,
        baseline_strategy_id=BASELINE_STRATEGY_ID,
        candidate_strategy_id=CANDIDATE_STRATEGY_ID,
        guarded_strategy_id=GUARDED_BOOST_STRATEGY_ID,
        router_policy_id=ROUTER_POLICY_ID,
        answer_contract_version=ANSWER_CONTRACT_VERSION,
        answer_policy_id=ANSWER_POLICY_ID,
        provider_config_id=provider_context.provider_config_id,
        endpoint_alias=provider_context.endpoint_alias,
        model_id=provider_context.model_id,
        top_k=dry_run_report.top_k,
        candidate_k=dry_run_report.candidate_k,
        max_context_chars=dry_run_report.max_context_chars,
        live_call_summary=live_call_summary,
        baseline_report=baseline_report,
        candidate_report=candidate_report,
        paired_deltas=paired_deltas,
        query_type_deltas=query_type_deltas,
        adoption_decision=select_guarded_boost_adoption_decision(
            baseline_report=baseline_report,
            candidate_report=candidate_report,
        ),
        output_quality=output_quality,
        qualitative_assessment={},
    )
    return report.model_copy(
        update={
            "qualitative_assessment": build_guarded_boost_live_assessment(report),
        },
    )


def validate_live_paired_comparison_inputs(
    *,
    baseline_inputs: list[GenerationEvalInput],
    candidate_inputs: list[GenerationEvalInput],
) -> None:
    if not baseline_inputs or not candidate_inputs:
        raise ValueError("guarded boost live comparison requires non-empty inputs")
    baseline_by_query_id = {item.item.query.query_id: item for item in baseline_inputs}
    candidate_by_query_id = {item.item.query.query_id: item for item in candidate_inputs}
    if set(baseline_by_query_id) != set(candidate_by_query_id):
        raise ValueError("guarded boost paired comparison requires identical query ids")
    if build_generation_eval_dataset_fingerprint(
        baseline_inputs,
    ) != build_generation_eval_dataset_fingerprint(candidate_inputs):
        raise ValueError("guarded boost paired comparison requires identical eval dataset")
    for query_id, baseline in baseline_by_query_id.items():
        candidate = candidate_by_query_id[query_id]
        if baseline.item.query.query_type != candidate.item.query.query_type:
            raise ValueError("guarded boost paired comparison requires identical query type")
        if baseline.packing_policy_id != candidate.packing_policy_id:
            raise ValueError("guarded boost paired comparison requires identical packing")


def build_guarded_boost_live_pair_deltas(
    *,
    baseline_records: list[GenerationEvalRecord],
    candidate_records: list[GenerationEvalRecord],
    dry_run_report: SolarGuardedBoostLiveDryRunReport,
) -> list[SolarGuardedBoostLivePairDelta]:
    candidate_by_query_id = {record.query_id: record for record in candidate_records}
    dry_run_by_query_id = {row.query_id: row for row in dry_run_report.rows}
    deltas: list[SolarGuardedBoostLivePairDelta] = []
    for baseline in sorted(baseline_records, key=lambda record: record.query_id):
        candidate = candidate_by_query_id[baseline.query_id]
        dry_run_row = dry_run_by_query_id[baseline.query_id]
        deltas.append(
            SolarGuardedBoostLivePairDelta(
                query_id=baseline.query_id,
                query_type=baseline.query_type,
                route_decision=dry_run_row.route_decision,
                reuse_decision=dry_run_row.reuse_decision,
                baseline_correct_with_evidence=baseline.correct_with_evidence,
                candidate_correct_with_evidence=candidate.correct_with_evidence,
                correct_with_evidence_delta=int(candidate.correct_with_evidence)
                - int(baseline.correct_with_evidence),
                baseline_citation_precision=baseline.citation_precision,
                candidate_citation_precision=candidate.citation_precision,
                citation_precision_delta=round(
                    candidate.citation_precision - baseline.citation_precision,
                    6,
                ),
                baseline_citation_recall=baseline.citation_recall,
                candidate_citation_recall=candidate.citation_recall,
                citation_recall_delta=round(
                    candidate.citation_recall - baseline.citation_recall,
                    6,
                ),
                baseline_unsupported_claim=baseline.unsupported_claim,
                candidate_unsupported_claim=candidate.unsupported_claim,
                unsupported_claim_delta=int(candidate.unsupported_claim)
                - int(baseline.unsupported_claim),
                baseline_citation_count=baseline.citation_count,
                candidate_citation_count=candidate.citation_count,
                citation_count_delta=candidate.citation_count - baseline.citation_count,
                latency_ms_delta=round(candidate.latency_ms - baseline.latency_ms, 6),
            ),
        )
    return deltas


def build_guarded_boost_live_query_type_deltas(
    paired_deltas: tuple[SolarGuardedBoostLivePairDelta, ...],
) -> list[SolarGuardedBoostLiveQueryTypeDelta]:
    query_types = sorted({delta.query_type for delta in paired_deltas})
    rows: list[SolarGuardedBoostLiveQueryTypeDelta] = []
    for query_type in query_types:
        subset = [delta for delta in paired_deltas if delta.query_type == query_type]
        rows.append(
            SolarGuardedBoostLiveQueryTypeDelta(
                query_type=query_type,
                eval_count=len(subset),
                correct_with_evidence_delta=_mean_float(
                    [float(delta.correct_with_evidence_delta) for delta in subset],
                ),
                citation_precision_delta=_mean_float(
                    [delta.citation_precision_delta for delta in subset],
                ),
                citation_recall_delta=_mean_float(
                    [delta.citation_recall_delta for delta in subset],
                ),
                unsupported_claim_rate_delta=_mean_float(
                    [float(delta.unsupported_claim_delta) for delta in subset],
                ),
                latency_p95_ms_delta=_max_float(
                    [delta.latency_ms_delta for delta in subset],
                ),
            ),
        )
    return rows


def build_public_solar_guarded_boost_live_paired_comparison_rows(
    report: SolarGuardedBoostLiveComparisonReport,
) -> list[dict[str, Any]]:
    return build_public_solar_guarded_boost_live_paired_comparison_rows_from_deltas(
        report.paired_deltas,
    )


def build_public_solar_guarded_boost_live_paired_comparison_rows_from_deltas(
    paired_deltas: tuple[SolarGuardedBoostLivePairDelta, ...],
) -> list[dict[str, Any]]:
    return [
        {
            "query_id": delta.query_id,
            "query_type": delta.query_type,
            "baseline_strategy_id": BASELINE_STRATEGY_ID,
            "candidate_strategy_id": GUARDED_BOOST_STRATEGY_ID,
            "route_decision": delta.route_decision,
            "reuse_decision": delta.reuse_decision,
            "baseline_correct_with_evidence": delta.baseline_correct_with_evidence,
            "candidate_correct_with_evidence": delta.candidate_correct_with_evidence,
            "correct_with_evidence_delta": delta.correct_with_evidence_delta,
            "baseline_citation_precision": delta.baseline_citation_precision,
            "candidate_citation_precision": delta.candidate_citation_precision,
            "citation_precision_delta": delta.citation_precision_delta,
            "baseline_citation_recall": delta.baseline_citation_recall,
            "candidate_citation_recall": delta.candidate_citation_recall,
            "citation_recall_delta": delta.citation_recall_delta,
            "unsupported_claim_delta": delta.unsupported_claim_delta,
            "baseline_citation_count": delta.baseline_citation_count,
            "candidate_citation_count": delta.candidate_citation_count,
            "citation_count_delta": delta.citation_count_delta,
            "latency_ms_delta": delta.latency_ms_delta,
        }
        for delta in paired_deltas
    ]


def collect_solar_guarded_boost_live_paired_comparison_failures(
    report: SolarGuardedBoostLiveComparisonReport,
) -> list[str]:
    failures: list[str] = []
    if report.baseline_report.summary.eval_count != report.candidate_report.summary.eval_count:
        failures.append("mismatched_eval_count")
    if not report.paired_deltas:
        failures.append("empty_paired_delta")
    if (
        report.live_call_summary.actual_solar_call_count
        != report.live_call_summary.expected_total_live_call_count
    ):
        failures.append("actual_call_count_mismatch")
    if (
        report.live_call_summary.actual_solar_call_count
        > report.live_call_summary.live_call_hard_cap
    ):
        failures.append("live_call_hard_cap_exceeded")
    if report.output_quality.public_raw_text_leakage_count:
        failures.append("public_raw_text_leakage")
    if report.output_quality.private_path_leakage_count:
        failures.append("private_path_leakage")
    if report.output_quality.secret_like_leakage_count:
        failures.append("secret_like_leakage")
    if report.output_quality.forbidden_result_field_count:
        failures.append("forbidden_public_result_fields")
    return failures


def select_guarded_boost_adoption_decision(
    *,
    baseline_report: GenerationEvalReport,
    candidate_report: GenerationEvalReport,
) -> str:
    baseline = baseline_report.summary
    candidate = candidate_report.summary
    if (
        candidate.correct_with_evidence_rate >= baseline.correct_with_evidence_rate
        and candidate.citation_precision >= baseline.citation_precision
        and candidate.citation_recall > baseline.citation_recall
        and candidate.unsupported_claim_rate <= baseline.unsupported_claim_rate
    ):
        return "promote_guarded_candidate_for_next_gate"
    if candidate.citation_recall > baseline.citation_recall:
        return "keep_as_tradeoff_candidate"
    if (
        candidate.correct_with_evidence_rate < baseline.correct_with_evidence_rate
        or candidate.unsupported_claim_rate > baseline.unsupported_claim_rate
    ):
        return "reject_guarded_candidate"
    return "no_material_live_improvement"


def build_guarded_boost_live_assessment(
    report: SolarGuardedBoostLiveComparisonReport,
) -> dict[str, str]:
    failures = collect_solar_guarded_boost_live_paired_comparison_failures(report)
    recall_gain_count = sum(
        1 for delta in report.paired_deltas if delta.citation_recall_delta > 0
    )
    precision_regression_count = sum(
        1 for delta in report.paired_deltas if delta.citation_precision_delta < 0
    )
    unsupported_regression_count = sum(
        1 for delta in report.paired_deltas if delta.unsupported_claim_delta > 0
    )
    no_material_change_count = sum(
        1
        for delta in report.paired_deltas
        if delta.correct_with_evidence_delta == 0
        and delta.citation_precision_delta == 0
        and delta.citation_recall_delta == 0
        and delta.unsupported_claim_delta == 0
    )
    return {
        "comparison_scope": (
            "`place_story` dev 10개에서 baseline retrieval과 guarded boost retrieval만 다르게 둔 live paired comparison이다."
        ),
        "provider_boundary": (
            "Solar Pro 3 live API를 호출했다. 동일 input fingerprint candidate는 baseline generation 결과를 재사용했다."
        ),
        "metric_grain": (
            "query 단위 paired delta와 query_type delta를 분리해 기록한다."
        ),
        "reuse_policy": (
            f"candidate {report.live_call_summary.reused_candidate_count}건은 baseline 결과를 재사용했고, "
            f"{report.live_call_summary.candidate_live_call_count}건만 추가 호출했다."
        ),
        "qualitative_tags": (
            f"citation_recall_gain={recall_gain_count}, "
            f"citation_precision_regression={precision_regression_count}, "
            f"unsupported_regression={unsupported_regression_count}, "
            f"no_material_change={no_material_change_count}"
        ),
        "adoption_decision": report.adoption_decision,
        "claim_boundary": (
            "현재 결과는 private dev 10건의 live comparison이며 최종 성능 개선 주장이 아니다."
        ),
        "public_policy": (
            "public report와 result row에는 raw query, raw answer, evidence text, chunk text, private path, secret을 저장하지 않는다."
        ),
        "gate_status": "PASS" if not failures else f"FAIL: {', '.join(failures)}",
    }


def build_solar_guarded_boost_live_paired_comparison_markdown(
    report: SolarGuardedBoostLiveComparisonReport,
) -> str:
    baseline = report.baseline_report.summary
    candidate = report.candidate_report.summary
    summary = report.live_call_summary
    quality = report.output_quality
    paired_rows = "\n".join(_format_live_pair_delta_row(delta) for delta in report.paired_deltas)
    query_type_rows = "\n".join(
        _format_live_query_type_delta_row(delta) for delta in report.query_type_deltas
    )
    baseline_breakdown_rows = "\n".join(
        _format_query_type_summary_row(row)
        for row in report.baseline_report.query_type_breakdown
    )
    candidate_breakdown_rows = "\n".join(
        _format_query_type_summary_row(row)
        for row in report.candidate_report.query_type_breakdown
    )
    qualitative_rows = "\n".join(
        f"- `{key}`: {value}" for key, value in report.qualitative_assessment.items()
    )
    return f"""# Solar Pro 3 Guarded Boost Live Comparison Report

## 목적

`parent_doc_context_boost_guarded`가 실제 Solar Pro 3 답변 품질에서도 baseline 대비 도움이 되는지 `place_story` dev 10개에서 paired comparison으로 검증한다.

이 문서는 private dev subset 기반의 실험 결과다. 최종 성능 개선 주장이 아니라 guarded boost 채택 여부를 판단하기 위한 근거다. raw query, raw answer, raw evidence, prompt, chunk text는 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| comparison_id | `{report.comparison_id}` |
| generated_at_utc | `{report.generated_at_utc}` |
| dataset_fingerprint | `{report.dataset_fingerprint}` |
| dry_run_id | `{report.dry_run_id}` |
| dataset_path | `{report.dataset_path_alias}` |
| chunks_path | `{report.chunks_path_alias}` |
| baseline_strategy_id | `{report.baseline_strategy_id}` |
| candidate_strategy_id | `{report.candidate_strategy_id}` |
| guarded_strategy_id | `{report.guarded_strategy_id}` |
| router_policy_id | `{report.router_policy_id}` |
| answer_contract_version | `{report.answer_contract_version}` |
| answer_policy_id | `{report.answer_policy_id}` |
| provider_config_id | `{report.provider_config_id}` |
| endpoint_alias | `{report.endpoint_alias}` |
| model_id | `{report.model_id}` |
| top_k | {report.top_k} |
| candidate_k | {report.candidate_k} |
| max_context_chars | {report.max_context_chars} |

## Live Call Summary

| metric | value |
| --- | ---: |
| query_count | {summary.query_count} |
| baseline_live_call_count | {summary.baseline_live_call_count} |
| candidate_live_call_count | {summary.candidate_live_call_count} |
| reused_candidate_count | {summary.reused_candidate_count} |
| changed_candidate_input_count | {summary.changed_candidate_input_count} |
| expected_total_live_call_count | {summary.expected_total_live_call_count} |
| actual_solar_call_count | {summary.actual_solar_call_count} |
| live_call_hard_cap | {summary.live_call_hard_cap} |
| baseline_prompt_tokens | {summary.baseline_prompt_tokens} |
| baseline_completion_tokens | {summary.baseline_completion_tokens} |
| baseline_total_tokens | {summary.baseline_total_tokens} |
| candidate_prompt_tokens | {summary.candidate_prompt_tokens} |
| candidate_completion_tokens | {summary.candidate_completion_tokens} |
| candidate_total_tokens | {summary.candidate_total_tokens} |
| total_prompt_tokens | {summary.total_prompt_tokens} |
| total_completion_tokens | {summary.total_completion_tokens} |
| total_tokens | {summary.total_tokens} |
| estimated_cost | {summary.estimated_cost:.6f} |

## 정량 리포트

| metric | baseline | guarded candidate | delta |
| --- | ---: | ---: | ---: |
| eval_count | {baseline.eval_count} | {candidate.eval_count} | {candidate.eval_count - baseline.eval_count} |
| Correct-with-Evidence | {baseline.correct_with_evidence_rate:.6f} | {candidate.correct_with_evidence_rate:.6f} | {candidate.correct_with_evidence_rate - baseline.correct_with_evidence_rate:.6f} |
| citation_precision | {baseline.citation_precision:.6f} | {candidate.citation_precision:.6f} | {candidate.citation_precision - baseline.citation_precision:.6f} |
| citation_recall | {baseline.citation_recall:.6f} | {candidate.citation_recall:.6f} | {candidate.citation_recall - baseline.citation_recall:.6f} |
| place_relevance | {baseline.place_relevance:.6f} | {candidate.place_relevance:.6f} | {candidate.place_relevance - baseline.place_relevance:.6f} |
| docent_usefulness | {baseline.docent_usefulness:.6f} | {candidate.docent_usefulness:.6f} | {candidate.docent_usefulness - baseline.docent_usefulness:.6f} |
| spoken_answer_naturalness | {baseline.spoken_answer_naturalness:.6f} | {candidate.spoken_answer_naturalness:.6f} | {candidate.spoken_answer_naturalness - baseline.spoken_answer_naturalness:.6f} |
| unsupported_claim_rate | {baseline.unsupported_claim_rate:.6f} | {candidate.unsupported_claim_rate:.6f} | {candidate.unsupported_claim_rate - baseline.unsupported_claim_rate:.6f} |
| abstention_accuracy | {baseline.abstention_accuracy:.6f} | {candidate.abstention_accuracy:.6f} | {candidate.abstention_accuracy - baseline.abstention_accuracy:.6f} |
| latency_p95_ms | {baseline.latency_p95_ms:.6f} | {candidate.latency_p95_ms:.6f} | {candidate.latency_p95_ms - baseline.latency_p95_ms:.6f} |
| solar_call_count | {baseline.solar_call_count} | {candidate.solar_call_count} | {candidate.solar_call_count - baseline.solar_call_count} |
| estimated_cost | {baseline.estimated_cost:.6f} | {candidate.estimated_cost:.6f} | {candidate.estimated_cost - baseline.estimated_cost:.6f} |
| missing_citation_count | {baseline.missing_citation_count} | {candidate.missing_citation_count} | {candidate.missing_citation_count - baseline.missing_citation_count} |
| unsupported_high_count | {baseline.unsupported_high_count} | {candidate.unsupported_high_count} | {candidate.unsupported_high_count - baseline.unsupported_high_count} |

## Baseline Query Type Breakdown

| query_type | eval_count | answerable_count | Correct-with-Evidence | citation_precision | citation_recall | place_relevance | docent_usefulness | spoken_answer_naturalness | unsupported_claim_rate | abstention_accuracy | latency_p95_ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{baseline_breakdown_rows}

## Candidate Query Type Breakdown

| query_type | eval_count | answerable_count | Correct-with-Evidence | citation_precision | citation_recall | place_relevance | docent_usefulness | spoken_answer_naturalness | unsupported_claim_rate | abstention_accuracy | latency_p95_ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{candidate_breakdown_rows}

## Paired Delta

| query_id | query_type | route_decision | reuse_decision | Correct delta | citation_precision delta | citation_recall delta | unsupported_claim delta | citation_count delta | latency_ms delta |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
{paired_rows}

## Query Type Delta

| query_type | eval_count | Correct delta | citation_precision delta | citation_recall delta | unsupported_claim_rate delta | latency_p95_ms delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
{query_type_rows}

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

## 채택 판단

`{report.adoption_decision}`

## 해석

이번 실험은 locked test가 아니라 private dev `place_story` 10건에서 실행했다. candidate 채택은 Correct-with-Evidence, citation precision, citation recall, unsupported claim, latency/cost를 함께 보고 판단한다.
"""


def build_guarded_boost_live_comparison_id(
    *,
    baseline_records: list[GenerationEvalRecord],
    candidate_records: list[GenerationEvalRecord],
    dry_run_id: str,
) -> str:
    payload = {
        "dry_run_id": dry_run_id,
        "baseline": [
            _comparison_id_record(record)
            for record in sorted(baseline_records, key=lambda item: item.query_id)
        ],
        "candidate": [
            _comparison_id_record(record)
            for record in sorted(candidate_records, key=lambda item: item.query_id)
        ],
    }
    digest = _stable_digest(payload)[:8]
    return f"solar-guarded-boost-live-q{len(baseline_records)}-{digest}"


def _comparison_id_record(record: GenerationEvalRecord) -> dict[str, Any]:
    return {
        "query_id": record.query_id,
        "answer_fingerprint": record.answer_fingerprint,
        "answer_policy_id": record.answer_policy_id,
        "retrieval_run_label": record.retrieval_run_label,
        "provider": record.provider,
        "model_id": record.model_id,
    }


def _format_live_pair_delta_row(delta: SolarGuardedBoostLivePairDelta) -> str:
    return (
        f"| {delta.query_id} | {delta.query_type} | {delta.route_decision} | "
        f"{delta.reuse_decision} | {delta.correct_with_evidence_delta} | "
        f"{delta.citation_precision_delta:.6f} | "
        f"{delta.citation_recall_delta:.6f} | "
        f"{delta.unsupported_claim_delta} | {delta.citation_count_delta} | "
        f"{delta.latency_ms_delta:.6f} |"
    )


def _format_live_query_type_delta_row(
    delta: SolarGuardedBoostLiveQueryTypeDelta,
) -> str:
    return (
        f"| {delta.query_type} | {delta.eval_count} | "
        f"{delta.correct_with_evidence_delta:.6f} | "
        f"{delta.citation_precision_delta:.6f} | "
        f"{delta.citation_recall_delta:.6f} | "
        f"{delta.unsupported_claim_rate_delta:.6f} | "
        f"{delta.latency_p95_ms_delta:.6f} |"
    )


def _assembler(
    *,
    provider: str,
    model_id: str,
) -> CitationRagAnswerAssembler:
    return CitationRagAnswerAssembler(
        config=CitationRagAssemblerConfig(
            answer_policy_id=ANSWER_POLICY_ID,
            provider=provider,
            model_id=model_id,
        ),
    )


def _zero_provider_usage() -> SolarLiveProviderUsageTotals:
    return SolarLiveProviderUsageTotals()


def _mean_float(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 6)


def _max_float(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(max(values), 6)


def _stable_digest(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"),
    ).hexdigest()[:16]


def build_public_solar_guarded_boost_live_comparison_rows(
    report: SolarGuardedBoostLiveComparisonReadinessReport,
) -> list[dict[str, Any]]:
    gate = report.gate_summary
    return [
        {
            "readiness_id": report.readiness_id,
            "row_type": "readiness_summary",
            "dry_run_id": report.dry_run_id,
            "execution_mode": gate.execution_mode,
            "readiness_decision": gate.readiness_decision,
            "live_execution_requested": gate.live_execution_requested,
            "live_execution_confirmed": gate.live_execution_confirmed,
            "live_call_executed": gate.live_call_executed,
            "approval_required_for_live": gate.approval_required_for_live,
            "dry_run_gate_passed": gate.dry_run_gate_passed,
            "call_cap_passed": gate.call_cap_passed,
            "public_safety_passed": gate.public_safety_passed,
            "expected_total_live_call_count": gate.expected_total_live_call_count,
            "live_call_hard_cap": gate.live_call_hard_cap,
            "baseline_live_call_count": gate.baseline_live_call_count,
            "candidate_live_call_count": gate.candidate_live_call_count,
            "reused_candidate_count": gate.reused_candidate_count,
            "changed_candidate_input_count": gate.changed_candidate_input_count,
            "solar_call_count": gate.solar_call_count,
        },
    ]


def collect_solar_guarded_boost_live_comparison_failures(
    report: SolarGuardedBoostLiveComparisonReadinessReport,
) -> list[str]:
    failures: list[str] = []
    gate = report.gate_summary
    if gate.live_call_executed:
        failures.append("live_call_executed_in_readiness_stage")
    if gate.solar_call_count != 0:
        failures.append("solar_call_count_must_be_zero")
    if not gate.dry_run_gate_passed:
        failures.append("dry_run_gate_failed")
    if not gate.call_cap_passed:
        failures.append("call_cap_failed")
    if not gate.public_safety_passed:
        failures.append("dry_run_public_safety_failed")
    if gate.readiness_decision != "ready_for_live_execution_approval":
        failures.append("not_ready_for_live_execution_approval")
    if report.output_quality.public_raw_text_leakage_count:
        failures.append("public_raw_text_leakage")
    if report.output_quality.private_path_leakage_count:
        failures.append("private_path_leakage")
    if report.output_quality.secret_like_leakage_count:
        failures.append("secret_like_leakage")
    if report.output_quality.forbidden_result_field_count:
        failures.append("forbidden_public_result_fields")
    return failures


def build_solar_guarded_boost_live_comparison_markdown(
    report: SolarGuardedBoostLiveComparisonReadinessReport,
) -> str:
    gate = report.gate_summary
    quality = report.output_quality
    qualitative_rows = "\n".join(
        f"- `{key}`: {value}" for key, value in report.qualitative_assessment.items()
    )
    reuse_rows = "\n".join(
        f"| `{decision}` | {count} |"
        for decision, count in report.reuse_decision_distribution.items()
    )
    return f"""# Solar Pro 3 Guarded Boost Live Comparison Readiness Report

## 목적

`parent_doc_context_boost_guarded` live paired comparison runner가 실제 Solar Pro 3 호출 전에 dry-run gate, call cap, public-safe gate를 강제하는지 검증한다.

이 문서는 readiness report다. Solar Pro 3 live 호출은 수행하지 않았고 raw query, raw evidence, prompt, answer text는 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| readiness_id | `{report.readiness_id}` |
| generated_at_utc | `{report.generated_at_utc}` |
| dry_run_report_version | `{report.dry_run_report_version}` |
| dry_run_id | `{report.dry_run_id}` |
| dataset_path | `{report.dataset_path_alias}` |
| chunks_path | `{report.chunks_path_alias}` |
| baseline_strategy_id | `{report.baseline_strategy_id}` |
| candidate_strategy_id | `{report.candidate_strategy_id}` |
| guarded_strategy_id | `{report.guarded_strategy_id}` |
| router_policy_id | `{report.router_policy_id}` |
| answer_contract_version | `{report.answer_contract_version}` |
| answer_policy_id | `{report.answer_policy_id}` |
| provider_config_id_alias | `{report.provider_config_id_alias}` |
| endpoint_alias | `{report.endpoint_alias}` |
| model_id | `{report.model_id}` |
| top_k | {report.top_k} |
| candidate_k | {report.candidate_k} |
| max_context_chars | {report.max_context_chars} |
| resolved_device | `{report.resolved_device}` |

## Gate Summary

| metric | value |
| --- | ---: |
| execution_mode | `{gate.execution_mode}` |
| readiness_decision | `{gate.readiness_decision}` |
| live_execution_requested | {gate.live_execution_requested} |
| live_execution_confirmed | {gate.live_execution_confirmed} |
| live_call_executed | {gate.live_call_executed} |
| approval_required_for_live | {gate.approval_required_for_live} |
| dry_run_gate_passed | {gate.dry_run_gate_passed} |
| call_cap_passed | {gate.call_cap_passed} |
| public_safety_passed | {gate.public_safety_passed} |
| expected_total_live_call_count | {gate.expected_total_live_call_count} |
| live_call_hard_cap | {gate.live_call_hard_cap} |
| baseline_live_call_count | {gate.baseline_live_call_count} |
| candidate_live_call_count | {gate.candidate_live_call_count} |
| reused_candidate_count | {gate.reused_candidate_count} |
| changed_candidate_input_count | {gate.changed_candidate_input_count} |
| solar_call_count | {gate.solar_call_count} |

## Reuse Decision Distribution

| reuse_decision | count |
| --- | ---: |
{reuse_rows}

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

{_readiness_conclusion(report)}
"""


def build_live_comparison_readiness_assessment(
    report: SolarGuardedBoostLiveComparisonReadinessReport,
) -> dict[str, str]:
    return {
        "execution_boundary": (
            "HD-SOLAR-015는 readiness stage이며 Solar Pro 3 live 호출을 수행하지 않는다."
        ),
        "dry_run_gate": (
            "live runner는 실행 전에 dry-run report를 재생성하고 dry-run gate를 통과해야 한다."
        ),
        "call_budget": (
            f"expected_total_live_call_count={report.gate_summary.expected_total_live_call_count}, "
            f"hard_cap={report.gate_summary.live_call_hard_cap}다."
        ),
        "reuse_policy": (
            "guarded input fingerprint가 baseline과 동일한 query는 baseline 결과를 재사용한다."
        ),
        "data_mart_grain": (
            "`fact_solar_guarded_boost_live_eval` grain은 run-query-strategy-answer_contract-router_policy다."
        ),
        "security_boundary": (
            "public artifact에는 raw query, raw evidence, prompt, answer text, private path, secret을 기록하지 않는다."
        ),
        "next_action": _next_action(report),
    }


def _next_action(report: SolarGuardedBoostLiveComparisonReadinessReport) -> str:
    if report.gate_summary.readiness_decision != "ready_for_live_execution_approval":
        return "readiness failure를 먼저 수정하고 live 실행 승인을 요청하지 않는다."
    return "별도 승인 후 HD-SOLAR-016에서 실제 Solar Pro 3 live paired comparison을 실행한다."


def _readiness_conclusion(
    report: SolarGuardedBoostLiveComparisonReadinessReport,
) -> str:
    failures = collect_solar_guarded_boost_live_comparison_failures(report)
    if failures:
        return (
            f"readiness gate가 실패했다: {', '.join(failures)}.\n\n"
            "Solar Pro 3 live 호출로 넘어가면 안 된다."
        )
    return (
        "readiness gate를 통과했다.\n\n"
        "이 결과는 live 품질 개선 주장이 아니라, live 실행 전에 dry-run gate와 call budget을 코드로 강제했다는 검증이다."
    )


def _readiness_id(
    *,
    dry_run_id: str,
    gate_summary: SolarGuardedBoostLiveComparisonGateSummary,
) -> str:
    payload = {
        "dry_run_id": dry_run_id,
        "gate_summary": gate_summary.model_dump(mode="json"),
    }
    digest = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"),
    ).hexdigest()[:8]
    return f"solar-guarded-boost-live-readiness-{digest}"


def main() -> int:
    args = _parse_args()
    if args.execute_live or args.confirm_live_execution:
        report = run_solar_guarded_boost_live_paired_comparison(
            chunks_path=args.chunks,
            dataset_path=args.dataset,
            place_catalog_path=args.place_catalog,
            embedding_cache_dir=args.embedding_cache_dir,
            report_path=args.report or DEFAULT_LIVE_REPORT_PATH,
            result_rows_path=args.result_rows or DEFAULT_LIVE_RESULT_ROWS_PATH,
            dry_run_report_path=(
                args.dry_run_report or DEFAULT_LIVE_PREFLIGHT_DRY_RUN_REPORT_PATH
            ),
            dry_run_result_rows_path=args.dry_run_result_rows,
            env_file_path=args.env_file,
            top_k=args.top_k,
            candidate_k=args.candidate_k,
            max_context_chars=args.max_context_chars,
            live_call_hard_cap=args.live_call_hard_cap,
            execute_live=args.execute_live,
            confirm_live_execution=args.confirm_live_execution,
        )
        failures = collect_solar_guarded_boost_live_paired_comparison_failures(report)
        baseline = report.baseline_report.summary
        candidate = report.candidate_report.summary
        print(
            "solar_guarded_boost_live_comparison "
            f"status={'PASS' if not failures else 'FAIL'} "
            f"decision={report.adoption_decision} "
            f"eval_count={baseline.eval_count} "
            f"correct_with_evidence_delta="
            f"{candidate.correct_with_evidence_rate - baseline.correct_with_evidence_rate:.6f} "
            f"citation_recall_delta="
            f"{candidate.citation_recall - baseline.citation_recall:.6f} "
            f"solar_calls={report.live_call_summary.actual_solar_call_count} "
            f"failures={len(failures)}",
        )
        return 0 if not failures else 1

    report = run_solar_guarded_boost_live_comparison(
        chunks_path=args.chunks,
        dataset_path=args.dataset,
        place_catalog_path=args.place_catalog,
        embedding_cache_dir=args.embedding_cache_dir,
        report_path=args.report or DEFAULT_REPORT_PATH,
        result_rows_path=args.result_rows or DEFAULT_RESULT_ROWS_PATH,
        dry_run_report_path=args.dry_run_report or DEFAULT_DRY_RUN_REPORT_PATH,
        dry_run_result_rows_path=args.dry_run_result_rows,
        top_k=args.top_k,
        candidate_k=args.candidate_k,
        max_context_chars=args.max_context_chars,
        live_call_hard_cap=args.live_call_hard_cap,
        execute_live=args.execute_live,
        confirm_live_execution=args.confirm_live_execution,
    )
    failures = collect_solar_guarded_boost_live_comparison_failures(report)
    print(
        "solar_guarded_boost_live_comparison_readiness "
        f"status={'PASS' if not failures else 'FAIL'} "
        f"decision={report.gate_summary.readiness_decision} "
        f"expected_calls={report.gate_summary.expected_total_live_call_count} "
        f"candidate_calls={report.gate_summary.candidate_live_call_count} "
        f"solar_calls={report.gate_summary.solar_call_count} "
        f"device={report.resolved_device} "
        f"failures={len(failures)}",
    )
    return 0 if not failures else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare Solar Pro 3 guarded boost live paired comparison.",
    )
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS_PATH)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--place-catalog", type=Path, default=DEFAULT_PLACE_CATALOG_PATH)
    parser.add_argument("--embedding-cache-dir", type=Path, default=DEFAULT_EMBEDDING_CACHE_DIR)
    parser.add_argument("--report", type=Path, default=None)
    parser.add_argument("--result-rows", type=Path, default=None)
    parser.add_argument("--dry-run-report", type=Path, default=None)
    parser.add_argument(
        "--dry-run-result-rows",
        type=Path,
        default=DEFAULT_DRY_RUN_RESULT_ROWS_PATH,
    )
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE_PATH)
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument("--candidate-k", type=int, default=DEFAULT_CANDIDATE_K)
    parser.add_argument("--max-context-chars", type=int, default=11000)
    parser.add_argument("--live-call-hard-cap", type=int, default=DEFAULT_LIVE_CALL_HARD_CAP)
    parser.add_argument(
        "--execute-live",
        action="store_true",
        help="Execute HD-SOLAR-016 live Solar Pro 3 paired comparison.",
    )
    parser.add_argument(
        "--confirm-live-execution",
        action="store_true",
        help="Required confirmation for live Solar Pro 3 calls.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
