from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Protocol

import httpx
from pydantic import BaseModel, ConfigDict, Field

from app.application.chat_retrieval import (
    PrivateArtifactRetrievalBackend,
    _retrieval_method_label,
    _search_with_route,
)
from app.core.project_paths import project_path
from app.domain.retrieval import (
    QueryType,
    RetrievedCandidate,
    RetrievalEvalItem,
    RetrievalRunResult,
    load_retrieval_eval_jsonl,
)
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    collect_public_retrieval_artifact_failures,
    measure_public_retrieval_artifact_quality,
    public_path_alias,
    write_public_retrieval_result_rows,
)
from app.infrastructure.index.device import resolve_torch_device
from app.providers.llm.base import (
    LlmProviderRequestError,
    LlmProviderResponseError,
    LlmProviderUsage,
)
from app.providers.llm.solar_pro_3 import (
    RETRYABLE_STATUS_CODES,
    SolarPro3ProviderConfig,
)
from pipelines.run_hyde_subset_readiness import (
    DEFAULT_LIVE_CALL_HARD_CAP,
    DEFAULT_QUERY_IDS,
    HYDE_CANDIDATE_ID,
    NO_ANSWER_GUARD_CANDIDATE_ID,
    PROMPT_POLICY_ID,
    build_hyde_subset_readiness_rows,
    build_hyde_subset_readiness_summary,
    _readiness_id,
)
from pipelines.run_solar_generation_baseline import (
    DEFAULT_ENV_FILE_PATH,
    load_env_file_into_process,
)
from pipelines.run_solar_live_generation_smoke import (
    DEFAULT_CHUNKS_PATH,
    DEFAULT_DATASET_PATH,
    DEFAULT_PACKING_POLICY_ID,
    _provider_endpoint_alias as _solar_provider_endpoint_alias,
    _validate_result_rows_path,
)


HYDE_LIVE_PAIRED_RETRIEVAL_REPORT_VERSION = (
    "hyde-live-paired-retrieval-comparison-report/v1"
)
WORK_ID = "HD-HYDE-001B"
DEFAULT_DOC_PATH = Path("docs") / "HYDE_LIVE_PAIRED_RETRIEVAL_COMPARISON.md"
DEFAULT_REPORT_PATH = (
    Path("evals") / "reports" / "hyde_live_paired_retrieval_comparison_report.md"
)
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "hyde_live_paired_retrieval_comparison_rows.jsonl"
)
DEFAULT_TOP_K = 5
HYDE_MAX_OUTPUT_TOKENS = 500
HYDE_TEXT_MAX_CHARS = 1200

HydeAdoptionDecision = Literal[
    "keep_hyde_candidate_for_larger_eval",
    "reject_hyde_for_now",
]
HydeProviderKind = Literal["solar_pro_3", "fake"]


class HydeLiveModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class HydeGenerationOutput(HydeLiveModel):
    query_id: str = Field(min_length=1)
    provider: HydeProviderKind
    model_id: str = Field(min_length=1)
    provider_config_id: str = Field(min_length=1)
    generated_text: str = Field(min_length=1)
    generated_text_hash: str = Field(min_length=12)
    generated_text_length: int = Field(ge=1)
    finish_reason: str | None = None
    usage: LlmProviderUsage


class HydeTextProvider(Protocol):
    @property
    def provider_config_id(self) -> str:
        ...

    @property
    def provider(self) -> HydeProviderKind:
        ...

    @property
    def model_id(self) -> str:
        ...

    def generate_hyde(self, item: RetrievalEvalItem) -> HydeGenerationOutput:
        ...


class HydeRetrievalRunner(Protocol):
    def search_baseline(self, item: RetrievalEvalItem) -> tuple[str, RetrievalRunResult]:
        ...

    def search_hyde(
        self,
        item: RetrievalEvalItem,
        *,
        generated_text: str,
    ) -> tuple[str, RetrievalRunResult]:
        ...


class HydePairRow(HydeLiveModel):
    query_id: str = Field(min_length=1)
    query_type: QueryType
    expected_behavior: Literal["retrieve", "abstain"]
    baseline_candidate_id: str = Field(min_length=1)
    hyde_candidate_id: str = Field(min_length=1)
    baseline_route_method: str = Field(min_length=1)
    hyde_route_method: str = Field(min_length=1)
    baseline_retrieval_run_required: bool
    hyde_generation_live_call_required: bool
    hyde_retrieval_run_required: bool
    no_answer_guard_applied: bool
    baseline_candidate_count: int = Field(ge=0)
    hyde_candidate_count: int = Field(ge=0)
    baseline_relevant_rank: int | None = Field(default=None, ge=1)
    hyde_relevant_rank: int | None = Field(default=None, ge=1)
    baseline_hit_at_1: bool
    baseline_hit_at_3: bool
    baseline_hit_at_5: bool
    hyde_hit_at_1: bool
    hyde_hit_at_3: bool
    hyde_hit_at_5: bool
    baseline_latency_ms: float = Field(ge=0.0)
    hyde_generation_latency_ms: float = Field(ge=0.0)
    hyde_retrieval_latency_ms: float = Field(ge=0.0)
    hyde_total_latency_ms: float = Field(ge=0.0)
    hyde_generated_text_hash: str | None = None
    hyde_generated_text_length: int = Field(default=0, ge=0)
    hyde_generation_request_count: int = Field(ge=0)
    solar_api_call_count: int = Field(ge=0)
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    estimated_cost: float = Field(ge=0.0)


class HydeMetricSummary(HydeLiveModel):
    candidate_id: str = Field(min_length=1)
    query_count: int = Field(ge=0)
    retrieve_query_count: int = Field(ge=0)
    no_answer_query_count: int = Field(ge=0)
    recall_at_1: float = Field(ge=0.0, le=1.0)
    recall_at_3: float = Field(ge=0.0, le=1.0)
    recall_at_5: float = Field(ge=0.0, le=1.0)
    mrr: float = Field(ge=0.0, le=1.0)
    ndcg_at_5: float = Field(ge=0.0, le=1.0)
    latency_p95_ms: float = Field(ge=0.0)
    no_answer_with_candidate_count: int = Field(ge=0)


class HydeComparisonSummary(HydeLiveModel):
    query_count: int = Field(ge=0)
    answerable_query_count: int = Field(ge=0)
    no_answer_query_count: int = Field(ge=0)
    baseline_retrieval_run_count: int = Field(ge=0)
    hyde_retrieval_run_count: int = Field(ge=0)
    hyde_generation_request_count: int = Field(ge=0)
    no_answer_guard_query_count: int = Field(ge=0)
    solar_api_call_count: int = Field(ge=0)
    live_call_hard_cap: int = Field(ge=1)
    hard_cap_exceeded: bool
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    estimated_cost: float = Field(ge=0.0)
    recall_at_1_delta: float
    recall_at_3_delta: float
    recall_at_5_delta: float
    mrr_delta: float
    ndcg_at_5_delta: float
    latency_p95_ms_delta: float
    adoption_decision: HydeAdoptionDecision


class HydeQueryTypeDelta(HydeLiveModel):
    query_type: QueryType
    query_count: int = Field(ge=0)
    baseline_recall_at_5: float = Field(ge=0.0, le=1.0)
    hyde_recall_at_5: float = Field(ge=0.0, le=1.0)
    recall_at_5_delta: float
    baseline_mrr: float = Field(ge=0.0, le=1.0)
    hyde_mrr: float = Field(ge=0.0, le=1.0)
    mrr_delta: float


class HydeLivePairedRetrievalReport(HydeLiveModel):
    report_version: str = HYDE_LIVE_PAIRED_RETRIEVAL_REPORT_VERSION
    comparison_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    work_id: str = WORK_ID
    readiness_id: str = Field(min_length=1)
    dataset_path_alias: str = Field(min_length=1)
    chunks_path_alias: str = Field(min_length=1)
    result_path: str = Field(min_length=1)
    provider: HydeProviderKind
    provider_config_id: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    endpoint_alias: str = Field(min_length=1)
    prompt_policy_id: str = Field(min_length=1)
    packing_policy_id: str = Field(min_length=1)
    top_k: int = Field(ge=1)
    resolved_device: str = Field(min_length=1)
    source_fingerprint: str = Field(min_length=8)
    baseline_summary: HydeMetricSummary
    hyde_summary: HydeMetricSummary
    comparison_summary: HydeComparisonSummary
    query_type_deltas: tuple[HydeQueryTypeDelta, ...]
    rows: tuple[HydePairRow, ...]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


@dataclass(frozen=True)
class _SolarHydeProvider:
    config: SolarPro3ProviderConfig
    client: httpx.Client | None = None

    @property
    def provider_config_id(self) -> str:
        return self.config.provider_config_id

    @property
    def provider(self) -> HydeProviderKind:
        return "solar_pro_3"

    @property
    def model_id(self) -> str:
        return self.config.model_id

    def generate_hyde(self, item: RetrievalEvalItem) -> HydeGenerationOutput:
        payload = _build_hyde_payload(item=item, config=self.config)
        started = time.perf_counter()
        response_payload = _post_with_retries(
            payload=payload,
            config=self.config,
            client=self.client,
        )
        latency_ms = round((time.perf_counter() - started) * 1000, 6)
        text = _parse_hyde_text(_extract_message_content(response_payload))
        usage_payload = response_payload.get("usage", {})
        usage = LlmProviderUsage(
            latency_ms=latency_ms,
            api_call_count=int(response_payload.get("_api_call_count") or 1),
            prompt_tokens=_safe_int(usage_payload.get("prompt_tokens")),
            completion_tokens=_safe_int(usage_payload.get("completion_tokens")),
            total_tokens=_safe_int(usage_payload.get("total_tokens")),
            estimated_cost=_estimate_cost(usage_payload=usage_payload, config=self.config),
        )
        return HydeGenerationOutput(
            query_id=item.query.query_id,
            provider="solar_pro_3",
            model_id=str(response_payload.get("model") or self.config.model_id),
            provider_config_id=self.provider_config_id,
            generated_text=text,
            generated_text_hash=_text_hash(text),
            generated_text_length=len(text),
            finish_reason=_extract_finish_reason(response_payload),
            usage=usage,
        )


class PrivateHydeRetrievalRunner:
    def __init__(
        self,
        *,
        chunks_path: Path = DEFAULT_CHUNKS_PATH,
        top_k: int = DEFAULT_TOP_K,
    ) -> None:
        self.backend = PrivateArtifactRetrievalBackend(chunks_path=chunks_path, top_k=top_k)
        self.top_k = top_k

    def search_baseline(self, item: RetrievalEvalItem) -> tuple[str, RetrievalRunResult]:
        state = self.backend._load_state()
        route = state.router.route(item.query.query_type)
        if item.query.expected_behavior == "abstain" or not route.should_retrieve:
            return _retrieval_method_label(route), _empty_result(item=item)
        rewrite = state.rewriter.rewrite(item)
        result = _search_with_route(
            route_decision=route,
            state=state,
            item=item,
            query_text=rewrite.rewritten_query_text,
            top_k=self.top_k,
        )
        result = result.model_copy(
            update={"latency_ms": round(result.latency_ms + rewrite.latency_ms, 6)}
        )
        return _retrieval_method_label(route), result

    def search_hyde(
        self,
        item: RetrievalEvalItem,
        *,
        generated_text: str,
    ) -> tuple[str, RetrievalRunResult]:
        state = self.backend._load_state()
        route = state.router.route(item.query.query_type)
        if item.query.expected_behavior == "abstain" or not route.should_retrieve:
            return _retrieval_method_label(route), _empty_result(item=item)
        result = _search_with_route(
            route_decision=route,
            state=state,
            item=item,
            query_text=_build_hyde_retrieval_query(item=item, generated_text=generated_text),
            top_k=self.top_k,
        )
        return _retrieval_method_label(route), result


def run_hyde_live_paired_retrieval_comparison(
    *,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    chunks_path: Path = DEFAULT_CHUNKS_PATH,
    env_file_path: Path | None = DEFAULT_ENV_FILE_PATH,
    doc_path: Path = DEFAULT_DOC_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
    query_ids: tuple[str, ...] = DEFAULT_QUERY_IDS,
    live_call_hard_cap: int = DEFAULT_LIVE_CALL_HARD_CAP,
    top_k: int = DEFAULT_TOP_K,
    hyde_provider: HydeTextProvider | None = None,
    retrieval_runner: HydeRetrievalRunner | None = None,
) -> HydeLivePairedRetrievalReport:
    _validate_result_rows_path(result_rows_path)
    readiness_rows = build_hyde_subset_readiness_rows(
        dataset_path=dataset_path,
        query_ids=query_ids,
    )
    readiness_summary = build_hyde_subset_readiness_summary(
        rows=readiness_rows,
        live_call_hard_cap=live_call_hard_cap,
    )
    readiness_id = _readiness_id(rows=readiness_rows, summary=readiness_summary)
    if readiness_summary.readiness_decision != "ready_for_hyde_live_approval":
        raise ValueError("HyDE readiness gate is not ready for live approval")
    if hyde_provider is None and env_file_path is not None:
        load_env_file_into_process(env_file_path)
    provider = hyde_provider or _SolarHydeProvider(config=SolarPro3ProviderConfig.from_env())
    runner = retrieval_runner or PrivateHydeRetrievalRunner(
        chunks_path=chunks_path,
        top_k=top_k,
    )
    items_by_id = {
        item.query.query_id: item
        for item in load_retrieval_eval_jsonl(project_path(dataset_path))
    }
    items = [items_by_id[query_id] for query_id in query_ids]
    rows = _build_pair_rows(
        items=items,
        provider=provider,
        retrieval_runner=runner,
    )
    report = _build_report(
        readiness_id=readiness_id,
        dataset_path=dataset_path,
        chunks_path=chunks_path,
        result_rows_path=result_rows_path,
        provider=provider,
        rows=rows,
        top_k=top_k,
        live_call_hard_cap=live_call_hard_cap,
        output_quality=PublicRetrievalArtifactQuality(
            result_row_count=0,
            report_version=HYDE_LIVE_PAIRED_RETRIEVAL_REPORT_VERSION,
            run_id="pending",
            public_raw_text_leakage_count=0,
            private_path_leakage_count=0,
            secret_like_leakage_count=0,
            forbidden_result_field_count=0,
        ),
    )
    public_rows = build_public_hyde_live_result_rows(report)
    doc_text = build_hyde_live_comparison_doc(report)
    report_text = build_hyde_live_comparison_markdown(report)
    quality = measure_public_retrieval_artifact_quality(
        report_version=HYDE_LIVE_PAIRED_RETRIEVAL_REPORT_VERSION,
        run_id=report.comparison_id,
        result_rows=public_rows,
        report_text=report_text,
        extra_public_texts={
            f"doc:{line_number}": line
            for line_number, line in enumerate(doc_text.splitlines(), start=1)
        },
    )
    report = _build_report(
        readiness_id=readiness_id,
        dataset_path=dataset_path,
        chunks_path=chunks_path,
        result_rows_path=result_rows_path,
        provider=provider,
        rows=rows,
        top_k=top_k,
        live_call_hard_cap=live_call_hard_cap,
        output_quality=quality,
    )
    failures = collect_hyde_live_paired_retrieval_failures(report)
    if failures:
        raise ValueError(f"HyDE live paired retrieval gate failed: {failures}")
    public_rows = build_public_hyde_live_result_rows(report)
    write_public_retrieval_result_rows(
        path=project_path(result_rows_path),
        rows=public_rows,
    )
    resolved_doc_path = project_path(doc_path)
    resolved_report_path = project_path(report_path)
    resolved_doc_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_report_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_doc_path.write_text(build_hyde_live_comparison_doc(report), encoding="utf-8")
    resolved_report_path.write_text(
        build_hyde_live_comparison_markdown(report),
        encoding="utf-8",
    )
    print(
        "hyde_live_paired_retrieval "
        "status=PASS "
        f"query_count={report.comparison_summary.query_count} "
        f"hyde_generation_request_count="
        f"{report.comparison_summary.hyde_generation_request_count} "
        f"solar_api_call_count={report.comparison_summary.solar_api_call_count} "
        f"recall_at_5_delta={report.comparison_summary.recall_at_5_delta:.6f} "
        f"decision={report.comparison_summary.adoption_decision}",
    )
    return report


def _build_pair_rows(
    *,
    items: list[RetrievalEvalItem],
    provider: HydeTextProvider,
    retrieval_runner: HydeRetrievalRunner,
) -> tuple[HydePairRow, ...]:
    rows: list[HydePairRow] = []
    for item in items:
        baseline_method, baseline_result = retrieval_runner.search_baseline(item)
        no_answer = item.query.query_type == "no_answer"
        generation: HydeGenerationOutput | None = None
        hyde_method = "abstain_first_v1" if no_answer else baseline_method
        hyde_result = _empty_result(item=item)
        if not no_answer:
            generation = provider.generate_hyde(item)
            hyde_method, hyde_result = retrieval_runner.search_hyde(
                item,
                generated_text=generation.generated_text,
            )
        rows.append(
            _build_pair_row(
                item=item,
                baseline_method=baseline_method,
                hyde_method=hyde_method,
                baseline_result=baseline_result,
                hyde_result=hyde_result,
                generation=generation,
            )
        )
    return tuple(rows)


def _build_pair_row(
    *,
    item: RetrievalEvalItem,
    baseline_method: str,
    hyde_method: str,
    baseline_result: RetrievalRunResult,
    hyde_result: RetrievalRunResult,
    generation: HydeGenerationOutput | None,
) -> HydePairRow:
    baseline_rank = _relevant_rank(item, baseline_result.candidates)
    hyde_rank = _relevant_rank(item, hyde_result.candidates)
    usage = generation.usage if generation else LlmProviderUsage()
    hyde_generation_latency = usage.latency_ms if generation else 0.0
    hyde_retrieval_latency = hyde_result.latency_ms if generation else 0.0
    return HydePairRow(
        query_id=item.query.query_id,
        query_type=item.query.query_type,
        expected_behavior=item.query.expected_behavior,
        baseline_candidate_id=baseline_method,
        hyde_candidate_id=NO_ANSWER_GUARD_CANDIDATE_ID
        if item.query.query_type == "no_answer"
        else HYDE_CANDIDATE_ID,
        baseline_route_method=baseline_method,
        hyde_route_method=hyde_method,
        baseline_retrieval_run_required=True,
        hyde_generation_live_call_required=generation is not None,
        hyde_retrieval_run_required=generation is not None,
        no_answer_guard_applied=item.query.query_type == "no_answer",
        baseline_candidate_count=len(baseline_result.candidates),
        hyde_candidate_count=len(hyde_result.candidates),
        baseline_relevant_rank=baseline_rank,
        hyde_relevant_rank=hyde_rank,
        baseline_hit_at_1=_covered_at(baseline_rank, 1),
        baseline_hit_at_3=_covered_at(baseline_rank, 3),
        baseline_hit_at_5=_covered_at(baseline_rank, 5),
        hyde_hit_at_1=_covered_at(hyde_rank, 1),
        hyde_hit_at_3=_covered_at(hyde_rank, 3),
        hyde_hit_at_5=_covered_at(hyde_rank, 5),
        baseline_latency_ms=baseline_result.latency_ms,
        hyde_generation_latency_ms=hyde_generation_latency,
        hyde_retrieval_latency_ms=hyde_retrieval_latency,
        hyde_total_latency_ms=round(hyde_generation_latency + hyde_retrieval_latency, 6),
        hyde_generated_text_hash=generation.generated_text_hash if generation else None,
        hyde_generated_text_length=generation.generated_text_length if generation else 0,
        hyde_generation_request_count=1 if generation else 0,
        solar_api_call_count=usage.api_call_count,
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        total_tokens=usage.total_tokens,
        estimated_cost=usage.estimated_cost,
    )


def _build_report(
    *,
    readiness_id: str,
    dataset_path: Path,
    chunks_path: Path,
    result_rows_path: Path,
    provider: HydeTextProvider,
    rows: tuple[HydePairRow, ...],
    top_k: int,
    live_call_hard_cap: int,
    output_quality: PublicRetrievalArtifactQuality,
) -> HydeLivePairedRetrievalReport:
    baseline_summary = _metric_summary(rows=rows, candidate_id="baseline_route_reference")
    hyde_summary = _metric_summary(rows=rows, candidate_id=HYDE_CANDIDATE_ID)
    comparison_summary = _comparison_summary(
        rows=rows,
        baseline=baseline_summary,
        hyde=hyde_summary,
        live_call_hard_cap=live_call_hard_cap,
    )
    report = HydeLivePairedRetrievalReport(
        comparison_id=_comparison_id(readiness_id=readiness_id, rows=rows),
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        readiness_id=readiness_id,
        dataset_path_alias=public_path_alias(dataset_path),
        chunks_path_alias="<private parent_child_chunks report>",
        result_path=public_path_alias(result_rows_path),
        provider=provider.provider,
        provider_config_id=provider.provider_config_id,
        model_id=provider.model_id,
        endpoint_alias=_provider_endpoint_alias(provider)
        if provider.provider == "solar_pro_3"
        else "fake-provider",
        prompt_policy_id=PROMPT_POLICY_ID,
        packing_policy_id=DEFAULT_PACKING_POLICY_ID,
        top_k=top_k,
        resolved_device=str(resolve_torch_device("cuda_if_available")),
        source_fingerprint=_stable_id(
            {
                "readiness_id": readiness_id,
                "dataset_path": str(dataset_path),
                "chunks_path": str(chunks_path),
                "query_ids": [row.query_id for row in rows],
                "top_k": top_k,
            }
        ),
        baseline_summary=baseline_summary,
        hyde_summary=hyde_summary,
        comparison_summary=comparison_summary,
        query_type_deltas=_query_type_deltas(rows),
        rows=rows,
        output_quality=output_quality,
        qualitative_assessment={},
    )
    return report.model_copy(
        update={"qualitative_assessment": _qualitative_assessment(report)}
    )


def build_public_hyde_live_result_rows(
    report: HydeLivePairedRetrievalReport,
) -> list[dict[str, Any]]:
    summary = report.comparison_summary
    rows: list[dict[str, Any]] = [
        {
            "row_type": "summary",
            "comparison_id": report.comparison_id,
            "work_id": report.work_id,
            "query_count": summary.query_count,
            "answerable_query_count": summary.answerable_query_count,
            "no_answer_query_count": summary.no_answer_query_count,
            "baseline_retrieval_run_count": summary.baseline_retrieval_run_count,
            "hyde_retrieval_run_count": summary.hyde_retrieval_run_count,
            "hyde_generation_request_count": summary.hyde_generation_request_count,
            "no_answer_guard_query_count": summary.no_answer_guard_query_count,
            "solar_api_call_count": summary.solar_api_call_count,
            "live_call_hard_cap": summary.live_call_hard_cap,
            "hard_cap_exceeded": summary.hard_cap_exceeded,
            "recall_at_5_delta": summary.recall_at_5_delta,
            "mrr_delta": summary.mrr_delta,
            "ndcg_at_5_delta": summary.ndcg_at_5_delta,
            "latency_p95_ms_delta": summary.latency_p95_ms_delta,
            "adoption_decision": summary.adoption_decision,
        }
    ]
    rows.extend(
        {
            "row_type": "candidate_metric",
            "comparison_id": report.comparison_id,
            "candidate_id": candidate.candidate_id,
            "query_count": candidate.query_count,
            "retrieve_query_count": candidate.retrieve_query_count,
            "no_answer_query_count": candidate.no_answer_query_count,
            "recall_at_1": candidate.recall_at_1,
            "recall_at_3": candidate.recall_at_3,
            "recall_at_5": candidate.recall_at_5,
            "mrr": candidate.mrr,
            "ndcg_at_5": candidate.ndcg_at_5,
            "latency_p95_ms": candidate.latency_p95_ms,
            "no_answer_with_candidate_count": candidate.no_answer_with_candidate_count,
        }
        for candidate in (report.baseline_summary, report.hyde_summary)
    )
    rows.extend(
        {
            "row_type": "query_pair",
            "comparison_id": report.comparison_id,
            "query_id": row.query_id,
            "query_type": row.query_type,
            "expected_behavior": row.expected_behavior,
            "baseline_candidate_id": row.baseline_candidate_id,
            "hyde_candidate_id": row.hyde_candidate_id,
            "baseline_relevant_rank": row.baseline_relevant_rank,
            "hyde_relevant_rank": row.hyde_relevant_rank,
            "baseline_hit_at_5": row.baseline_hit_at_5,
            "hyde_hit_at_5": row.hyde_hit_at_5,
            "no_answer_guard_applied": row.no_answer_guard_applied,
            "hyde_generated_text_hash": row.hyde_generated_text_hash,
            "hyde_generated_text_length": row.hyde_generated_text_length,
            "hyde_generation_request_count": row.hyde_generation_request_count,
            "solar_api_call_count": row.solar_api_call_count,
            "baseline_latency_ms": row.baseline_latency_ms,
            "hyde_total_latency_ms": row.hyde_total_latency_ms,
        }
        for row in report.rows
    )
    return rows


def collect_hyde_live_paired_retrieval_failures(
    report: HydeLivePairedRetrievalReport,
) -> list[str]:
    failures = collect_public_retrieval_artifact_failures(report.output_quality)
    summary = report.comparison_summary
    if summary.query_count != len(DEFAULT_QUERY_IDS):
        failures.append("query_count_mismatch")
    if summary.hyde_generation_request_count != 4:
        failures.append("hyde_generation_request_count_mismatch")
    if summary.no_answer_guard_query_count != 1:
        failures.append("no_answer_guard_count_mismatch")
    if any(row.query_type == "no_answer" and row.hyde_generation_request_count for row in report.rows):
        failures.append("no_answer_hyde_generation_executed")
    if any(row.query_type == "no_answer" and row.hyde_candidate_count for row in report.rows):
        failures.append("no_answer_hyde_retrieval_executed")
    if summary.hard_cap_exceeded:
        failures.append("live_call_hard_cap_exceeded")
    if summary.solar_api_call_count > summary.live_call_hard_cap:
        failures.append("solar_api_call_count_exceeds_hard_cap")
    if report.output_quality.forbidden_result_field_count:
        failures.append("forbidden_public_result_field")
    return failures


def build_hyde_live_comparison_doc(report: HydeLivePairedRetrievalReport) -> str:
    summary = report.comparison_summary
    row_text = "\n".join(_format_doc_pair_row(row) for row in report.rows)
    return f"""# HyDE Live Paired Retrieval Comparison

## 결론

`HD-HYDE-001B`는 Solar Pro 3 HyDE live paired retrieval comparison이다.

이 문서는 HyDE 성능 개선 확정 주장이 아니다. dev subset 5개에서 baseline route와 HyDE query expansion 후보를 같은 target judgment로 비교한 결과다.

raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 정량 요약

| metric | value |
| --- | ---: |
| query_count | {summary.query_count} |
| answerable_query_count | {summary.answerable_query_count} |
| no_answer_query_count | {summary.no_answer_query_count} |
| baseline_retrieval_run_count | {summary.baseline_retrieval_run_count} |
| hyde_retrieval_run_count | {summary.hyde_retrieval_run_count} |
| hyde_generation_request_count | {summary.hyde_generation_request_count} |
| no_answer_guard_query_count | {summary.no_answer_guard_query_count} |
| solar_api_call_count | {summary.solar_api_call_count} |
| live_call_hard_cap | {summary.live_call_hard_cap} |
| Recall@5 delta | {summary.recall_at_5_delta:.6f} |
| MRR delta | {summary.mrr_delta:.6f} |
| nDCG@5 delta | {summary.ndcg_at_5_delta:.6f} |
| latency_p95_ms delta | {summary.latency_p95_ms_delta:.6f} |
| adoption_decision | `{summary.adoption_decision}` |

## Candidate Summary

| candidate | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | latency_p95_ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | {report.baseline_summary.recall_at_1:.6f} | {report.baseline_summary.recall_at_3:.6f} | {report.baseline_summary.recall_at_5:.6f} | {report.baseline_summary.mrr:.6f} | {report.baseline_summary.ndcg_at_5:.6f} | {report.baseline_summary.latency_p95_ms:.6f} |
| HyDE | {report.hyde_summary.recall_at_1:.6f} | {report.hyde_summary.recall_at_3:.6f} | {report.hyde_summary.recall_at_5:.6f} | {report.hyde_summary.mrr:.6f} | {report.hyde_summary.ndcg_at_5:.6f} | {report.hyde_summary.latency_p95_ms:.6f} |

## Query Pair Rows

| query_id | query_type | baseline_rank | hyde_rank | baseline@5 | hyde@5 | no_answer_guard | hyde_call |
| --- | --- | ---: | ---: | --- | --- | --- | ---: |
{row_text}

## 실행 경계

| boundary | value |
| --- | --- |
| readiness_id | `{report.readiness_id}` |
| model | `{report.model_id}` |
| prompt_policy | `{report.prompt_policy_id}` |
| provider | `{report.provider}` |
| resolved_device | `{report.resolved_device}` |
| final citation | source child chunk only |
| no-answer policy | HyDE generation blocked |
| claim boundary | live-dev-subset |

## Claim Boundary

| claim | allowed |
| --- | --- |
| HyDE live paired retrieval comparison을 dev subset 5개에서 실행했다 | yes |
| no-answer query는 HyDE generation과 retrieval에서 차단했다 | yes |
| Solar Pro 3 HyDE generation request는 4회다 | yes |
| HyDE로 최종 retrieval 성능이 개선됐다 | no |
| no-answer hallucination 문제가 해결됐다 | no |
| locked test 개선을 입증했다 | no |
| production routing을 검증했다 | no |
"""


def build_hyde_live_comparison_markdown(
    report: HydeLivePairedRetrievalReport,
) -> str:
    summary = report.comparison_summary
    quality = report.output_quality
    query_type_rows = "\n".join(_format_query_type_delta_row(row) for row in report.query_type_deltas)
    pair_rows = "\n".join(_format_report_pair_row(row) for row in report.rows)
    qualitative_rows = "\n".join(
        f"- `{key}`: {value}" for key, value in report.qualitative_assessment.items()
    )
    return f"""# HyDE Live Paired Retrieval Comparison Report

## 목적

`HD-HYDE-001B`는 `HD-HYDE-001A` readiness에서 고정한 5개 query subset으로 Solar Pro 3 HyDE query expansion이 retrieval metric을 개선하는지 paired 비교한다.

이 리포트는 최종 성능 개선 주장이 아니다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| comparison_id | `{report.comparison_id}` |
| work_id | `{report.work_id}` |
| readiness_id | `{report.readiness_id}` |
| generated_at_utc | `{report.generated_at_utc}` |
| dataset_path | `{report.dataset_path_alias}` |
| chunks_path | `{report.chunks_path_alias}` |
| result_path | `{report.result_path}` |
| provider | `{report.provider}` |
| provider_config_id | `{report.provider_config_id}` |
| endpoint_alias | `{report.endpoint_alias}` |
| model_id | `{report.model_id}` |
| prompt_policy_id | `{report.prompt_policy_id}` |
| packing_policy_id | `{report.packing_policy_id}` |
| top_k | {report.top_k} |
| resolved_device | `{report.resolved_device}` |
| source_fingerprint | `{report.source_fingerprint}` |

## 정량 리포트

| metric | value |
| --- | ---: |
| query_count | {summary.query_count} |
| answerable_query_count | {summary.answerable_query_count} |
| no_answer_query_count | {summary.no_answer_query_count} |
| baseline_retrieval_run_count | {summary.baseline_retrieval_run_count} |
| hyde_retrieval_run_count | {summary.hyde_retrieval_run_count} |
| hyde_generation_request_count | {summary.hyde_generation_request_count} |
| no_answer_guard_query_count | {summary.no_answer_guard_query_count} |
| solar_api_call_count | {summary.solar_api_call_count} |
| live_call_hard_cap | {summary.live_call_hard_cap} |
| hard_cap_exceeded | {str(summary.hard_cap_exceeded).lower()} |
| prompt_tokens | {summary.prompt_tokens} |
| completion_tokens | {summary.completion_tokens} |
| total_tokens | {summary.total_tokens} |
| estimated_cost | {summary.estimated_cost:.6f} |
| recall_at_1_delta | {summary.recall_at_1_delta:.6f} |
| recall_at_3_delta | {summary.recall_at_3_delta:.6f} |
| recall_at_5_delta | {summary.recall_at_5_delta:.6f} |
| mrr_delta | {summary.mrr_delta:.6f} |
| ndcg_at_5_delta | {summary.ndcg_at_5_delta:.6f} |
| latency_p95_ms_delta | {summary.latency_p95_ms_delta:.6f} |
| adoption_decision | `{summary.adoption_decision}` |

## Candidate Metrics

| candidate | query_count | retrieve_query_count | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | latency_p95_ms | no_answer_with_candidate_count |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | {report.baseline_summary.query_count} | {report.baseline_summary.retrieve_query_count} | {report.baseline_summary.recall_at_1:.6f} | {report.baseline_summary.recall_at_3:.6f} | {report.baseline_summary.recall_at_5:.6f} | {report.baseline_summary.mrr:.6f} | {report.baseline_summary.ndcg_at_5:.6f} | {report.baseline_summary.latency_p95_ms:.6f} | {report.baseline_summary.no_answer_with_candidate_count} |
| HyDE | {report.hyde_summary.query_count} | {report.hyde_summary.retrieve_query_count} | {report.hyde_summary.recall_at_1:.6f} | {report.hyde_summary.recall_at_3:.6f} | {report.hyde_summary.recall_at_5:.6f} | {report.hyde_summary.mrr:.6f} | {report.hyde_summary.ndcg_at_5:.6f} | {report.hyde_summary.latency_p95_ms:.6f} | {report.hyde_summary.no_answer_with_candidate_count} |

## Query Type Delta

| query_type | query_count | baseline Recall@5 | HyDE Recall@5 | Recall@5 delta | baseline MRR | HyDE MRR | MRR delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{query_type_rows}

## Query Pair Rows

| query_id | query_type | baseline_route | hyde_route | baseline_rank | hyde_rank | baseline@5 | hyde@5 | hyde_hash | hyde_len | solar_api_call |
| --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: | ---: |
{pair_rows}

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

HyDE는 live-dev-subset에서만 비교했다. 이 결과는 locked test 또는 production 성능 개선 주장이 아니다.
"""


def _metric_summary(
    *,
    rows: tuple[HydePairRow, ...],
    candidate_id: str,
) -> HydeMetricSummary:
    retrieve_rows = [row for row in rows if row.expected_behavior == "retrieve"]
    no_answer_rows = [row for row in rows if row.expected_behavior == "abstain"]
    ranks = [
        row.hyde_relevant_rank
        if candidate_id == HYDE_CANDIDATE_ID
        else row.baseline_relevant_rank
        for row in retrieve_rows
    ]
    latencies = [
        row.hyde_total_latency_ms
        if candidate_id == HYDE_CANDIDATE_ID
        else row.baseline_latency_ms
        for row in rows
    ]
    return HydeMetricSummary(
        candidate_id=candidate_id,
        query_count=len(rows),
        retrieve_query_count=len(retrieve_rows),
        no_answer_query_count=len(no_answer_rows),
        recall_at_1=_mean_bool(_covered_at(rank, 1) for rank in ranks),
        recall_at_3=_mean_bool(_covered_at(rank, 3) for rank in ranks),
        recall_at_5=_mean_bool(_covered_at(rank, 5) for rank in ranks),
        mrr=_mean_float([0.0 if rank is None else round(1 / rank, 6) for rank in ranks]),
        ndcg_at_5=_ndcg_from_rows(rows=retrieve_rows, candidate_id=candidate_id),
        latency_p95_ms=_percentile(latencies, 0.95),
        no_answer_with_candidate_count=sum(
            1
            for row in no_answer_rows
            if (
                row.hyde_candidate_count
                if candidate_id == HYDE_CANDIDATE_ID
                else row.baseline_candidate_count
            )
        ),
    )


def _comparison_summary(
    *,
    rows: tuple[HydePairRow, ...],
    baseline: HydeMetricSummary,
    hyde: HydeMetricSummary,
    live_call_hard_cap: int,
) -> HydeComparisonSummary:
    solar_api_call_count = sum(row.solar_api_call_count for row in rows)
    decision: HydeAdoptionDecision = (
        "keep_hyde_candidate_for_larger_eval"
        if hyde.recall_at_5 > baseline.recall_at_5
        and hyde.ndcg_at_5 >= baseline.ndcg_at_5
        else "reject_hyde_for_now"
    )
    return HydeComparisonSummary(
        query_count=len(rows),
        answerable_query_count=sum(1 for row in rows if row.expected_behavior == "retrieve"),
        no_answer_query_count=sum(1 for row in rows if row.expected_behavior == "abstain"),
        baseline_retrieval_run_count=sum(1 for row in rows if row.baseline_retrieval_run_required),
        hyde_retrieval_run_count=sum(1 for row in rows if row.hyde_retrieval_run_required),
        hyde_generation_request_count=sum(row.hyde_generation_request_count for row in rows),
        no_answer_guard_query_count=sum(1 for row in rows if row.no_answer_guard_applied),
        solar_api_call_count=solar_api_call_count,
        live_call_hard_cap=live_call_hard_cap,
        hard_cap_exceeded=solar_api_call_count > live_call_hard_cap,
        prompt_tokens=sum(row.prompt_tokens for row in rows),
        completion_tokens=sum(row.completion_tokens for row in rows),
        total_tokens=sum(row.total_tokens for row in rows),
        estimated_cost=round(sum(row.estimated_cost for row in rows), 6),
        recall_at_1_delta=round(hyde.recall_at_1 - baseline.recall_at_1, 6),
        recall_at_3_delta=round(hyde.recall_at_3 - baseline.recall_at_3, 6),
        recall_at_5_delta=round(hyde.recall_at_5 - baseline.recall_at_5, 6),
        mrr_delta=round(hyde.mrr - baseline.mrr, 6),
        ndcg_at_5_delta=round(hyde.ndcg_at_5 - baseline.ndcg_at_5, 6),
        latency_p95_ms_delta=round(hyde.latency_p95_ms - baseline.latency_p95_ms, 6),
        adoption_decision=decision,
    )


def _query_type_deltas(rows: tuple[HydePairRow, ...]) -> tuple[HydeQueryTypeDelta, ...]:
    deltas: list[HydeQueryTypeDelta] = []
    for query_type in sorted({row.query_type for row in rows}):
        subset = tuple(row for row in rows if row.query_type == query_type)
        baseline = _metric_summary(rows=subset, candidate_id="baseline_route_reference")
        hyde = _metric_summary(rows=subset, candidate_id=HYDE_CANDIDATE_ID)
        deltas.append(
            HydeQueryTypeDelta(
                query_type=query_type,
                query_count=len(subset),
                baseline_recall_at_5=baseline.recall_at_5,
                hyde_recall_at_5=hyde.recall_at_5,
                recall_at_5_delta=round(hyde.recall_at_5 - baseline.recall_at_5, 6),
                baseline_mrr=baseline.mrr,
                hyde_mrr=hyde.mrr,
                mrr_delta=round(hyde.mrr - baseline.mrr, 6),
            )
        )
    return tuple(deltas)


def _qualitative_assessment(report: HydeLivePairedRetrievalReport) -> dict[str, str]:
    failures = collect_hyde_live_paired_retrieval_failures(report)
    return {
        "scope": "HD-HYDE-001A에서 고정한 5개 query subset만 비교했다.",
        "llm_call_boundary": "answerable query 4개만 Solar Pro 3 HyDE generation을 실행한다.",
        "no_answer_boundary": "no_answer query는 HyDE generation과 retrieval을 모두 차단한다.",
        "retrieval_boundary": "baseline과 HyDE 모두 같은 chunk corpus, 같은 top_k, 같은 route family를 사용한다.",
        "latency_boundary": "HyDE latency는 generation latency와 retrieval latency를 합산한다.",
        "cuda_boundary": "retrieval embedding 경로는 사용 가능하면 CUDA를 사용하며 report에 resolved_device를 기록한다.",
        "data_mart_grain": "`fact_hyde_live_pair` grain은 comparison_id + query_id + candidate_id다.",
        "security_boundary": "public artifact에는 raw query, raw HyDE text, prompt, evidence text를 남기지 않는다.",
        "external_audit": "subset이 작아 개선이 보이더라도 larger dev/locked test 전 채택 주장은 금지한다.",
        "gate_status": "PASS" if not failures else f"FAIL: {', '.join(failures)}",
    }


def _build_hyde_payload(
    *,
    item: RetrievalEvalItem,
    config: SolarPro3ProviderConfig,
) -> dict[str, Any]:
    return {
        "model": config.model_id,
        "messages": [
            {
                "role": "system",
                "content": (
                    "당신은 RAG 검색 성능 개선을 위한 HyDE query expansion 작성자입니다. "
                    "사용자 질문에 직접 답하지 말고, 검색에 도움이 되는 짧은 가상 근거 문단만 작성합니다. "
                    "출처, 페이지, 인용 표기는 만들지 않습니다. JSON schema만 반환합니다."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"query_id: {item.query.query_id}\n"
                    f"query_type: {item.query.query_type}\n"
                    f"language: {item.query.language}\n"
                    f"place_ids: {', '.join(item.metadata.place_ids) or 'unknown'}\n"
                    f"question: {item.query.query_text}\n\n"
                    "작성 규칙:\n"
                    "- 한국어 역사 도슨트 검색에 도움이 되는 가상 문단을 작성합니다.\n"
                    "- 질문의 지명, 인물, 사건, 시대 단서를 보존합니다.\n"
                    "- 확실하지 않은 세부 고유명사나 숫자를 새로 만들지 않습니다.\n"
                    "- 2~4문장, 1200자 이하로 작성합니다.\n"
                ),
            },
        ],
        "max_tokens": min(config.max_tokens, HYDE_MAX_OUTPUT_TOKENS),
        "temperature": 0.1,
        "top_p": config.top_p,
        "reasoning_effort": config.reasoning_effort,
        "stream": False,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "hyde_query_expansion",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "hypothetical_retrieval_text": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": HYDE_TEXT_MAX_CHARS,
                        }
                    },
                    "required": ["hypothetical_retrieval_text"],
                    "additionalProperties": False,
                },
            },
        },
    }


def _post_with_retries(
    *,
    payload: dict[str, Any],
    config: SolarPro3ProviderConfig,
    client: httpx.Client | None,
) -> dict[str, Any]:
    call_count = 0
    last_error: Exception | None = None
    for attempt in range(config.max_retries + 1):
        call_count += 1
        try:
            response = _post_once(payload=payload, config=config, client=client)
            response["_api_call_count"] = call_count
            return response
        except LlmProviderRequestError as exc:
            last_error = exc
            if attempt >= config.max_retries:
                raise
    raise LlmProviderRequestError("Solar Pro 3 HyDE request failed") from last_error


def _post_once(
    *,
    payload: dict[str, Any],
    config: SolarPro3ProviderConfig,
    client: httpx.Client | None,
) -> dict[str, Any]:
    active_client = client or httpx.Client(timeout=config.timeout_seconds)
    close_client = client is None
    try:
        response = active_client.post(
            config.endpoint,
            headers={
                "Authorization": f"Bearer {config.credential}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
    except httpx.TimeoutException as exc:
        raise LlmProviderRequestError("Solar Pro 3 HyDE request timed out") from exc
    except httpx.HTTPError as exc:
        raise LlmProviderRequestError("Solar Pro 3 HyDE request failed") from exc
    finally:
        if close_client:
            active_client.close()
    if response.status_code in RETRYABLE_STATUS_CODES:
        raise LlmProviderRequestError(
            f"Solar Pro 3 HyDE retryable status: {response.status_code}"
        )
    if response.status_code >= 400:
        raise LlmProviderRequestError(
            f"Solar Pro 3 HyDE non-retryable status: {response.status_code}"
        )
    try:
        parsed = response.json()
    except ValueError as exc:
        raise LlmProviderResponseError("Solar Pro 3 HyDE response is not JSON") from exc
    if not isinstance(parsed, dict):
        raise LlmProviderResponseError("Solar Pro 3 HyDE response must be an object")
    return parsed


def _extract_message_content(response_payload: dict[str, Any]) -> str:
    choices = response_payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise LlmProviderResponseError("Solar Pro 3 HyDE response choices missing")
    first = choices[0]
    if not isinstance(first, dict):
        raise LlmProviderResponseError("Solar Pro 3 HyDE choice must be an object")
    message = first.get("message")
    if not isinstance(message, dict):
        raise LlmProviderResponseError("Solar Pro 3 HyDE message missing")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise LlmProviderResponseError("Solar Pro 3 HyDE content missing")
    return content


def _parse_hyde_text(content: str) -> str:
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:].strip()
    try:
        payload = json.loads(stripped)
    except ValueError as exc:
        raise LlmProviderResponseError("Solar Pro 3 HyDE content is not JSON") from exc
    if not isinstance(payload, dict):
        raise LlmProviderResponseError("Solar Pro 3 HyDE JSON must be an object")
    value = payload.get("hypothetical_retrieval_text")
    if not isinstance(value, str) or not value.strip():
        raise LlmProviderResponseError("Solar Pro 3 HyDE text missing")
    text = " ".join(value.split())
    return text[:HYDE_TEXT_MAX_CHARS]


def _extract_finish_reason(response_payload: dict[str, Any]) -> str | None:
    choices = response_payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    first = choices[0]
    if not isinstance(first, dict):
        return None
    value = first.get("finish_reason")
    return str(value) if value is not None else None


def _provider_endpoint_alias(provider: HydeTextProvider) -> str:
    config = getattr(provider, "config", None)
    if config is None:
        return "unknown"
    return _provider_endpoint_alias_from_config(config)


def _provider_endpoint_alias_from_config(config: SolarPro3ProviderConfig) -> str:
    return _solar_provider_endpoint_alias(type("_Provider", (), {"config": config})())


def _build_hyde_retrieval_query(
    *,
    item: RetrievalEvalItem,
    generated_text: str,
) -> str:
    return f"{item.query.query_text}\n{generated_text}"


def _empty_result(*, item: RetrievalEvalItem) -> RetrievalRunResult:
    return RetrievalRunResult(
        query_id=item.query.query_id,
        query_type=item.query.query_type,
        method="dense",
        candidates=[],
        latency_ms=0.0,
    )


def _relevant_rank(
    item: RetrievalEvalItem,
    candidates: list[RetrievedCandidate],
) -> int | None:
    for candidate in candidates:
        if _candidate_relevance(item, candidate) > 0:
            return candidate.rank
    return None


def _candidate_relevance(item: RetrievalEvalItem, candidate: RetrievedCandidate) -> int:
    relevance_by_identifier: dict[str, int] = {}
    for judgment in item.judgments:
        targets = (
            judgment.relevant_child_ids
            or judgment.relevant_parent_ids
            or judgment.relevant_doc_ids
        )
        for target in targets:
            relevance_by_identifier[target] = max(
                relevance_by_identifier.get(target, 0),
                judgment.relevance_grade,
            )
    return max(
        relevance_by_identifier.get(candidate.child_id, 0),
        relevance_by_identifier.get(candidate.parent_id, 0),
        relevance_by_identifier.get(candidate.doc_id, 0),
    )


def _ndcg_from_rows(
    *,
    rows: list[HydePairRow],
    candidate_id: str,
) -> float:
    values = []
    for row in rows:
        rank = (
            row.hyde_relevant_rank
            if candidate_id == HYDE_CANDIDATE_ID
            else row.baseline_relevant_rank
        )
        values.append(0.0 if rank is None or rank > 5 else round(1 / math.log2(rank + 1), 6))
    return _mean_float(values)


def _covered_at(rank: int | None, k: int) -> bool:
    return rank is not None and rank <= k


def _mean_bool(values: Any) -> float:
    bools = list(values)
    if not bools:
        return 0.0
    return round(sum(1 for value in bools if value) / len(bools), 6)


def _mean_float(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 6)


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = round((len(sorted_values) - 1) * percentile)
    return round(sorted_values[index], 6)


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _estimate_cost(
    *,
    usage_payload: dict[str, Any],
    config: SolarPro3ProviderConfig,
) -> float:
    prompt_tokens = _safe_int(usage_payload.get("prompt_tokens"))
    completion_tokens = _safe_int(usage_payload.get("completion_tokens"))
    return round(
        (prompt_tokens / 1000) * config.cost_per_1k_input_tokens
        + (completion_tokens / 1000) * config.cost_per_1k_output_tokens,
        6,
    )


def _text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _stable_id(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:12]


def _comparison_id(*, readiness_id: str, rows: tuple[HydePairRow, ...]) -> str:
    digest = _stable_id(
        {
            "readiness_id": readiness_id,
            "query_ids": [row.query_id for row in rows],
            "hyde_hashes": [row.hyde_generated_text_hash for row in rows],
            "solar_api_call_count": sum(row.solar_api_call_count for row in rows),
        }
    )
    return f"hyde-live-paired-q{len(rows)}-c{sum(row.hyde_generation_request_count for row in rows)}-{digest}"


def _format_doc_pair_row(row: HydePairRow) -> str:
    return (
        f"| `{row.query_id}` | `{row.query_type}` | "
        f"{_rank_text(row.baseline_relevant_rank)} | {_rank_text(row.hyde_relevant_rank)} | "
        f"{str(row.baseline_hit_at_5).lower()} | {str(row.hyde_hit_at_5).lower()} | "
        f"{str(row.no_answer_guard_applied).lower()} | {row.hyde_generation_request_count} |"
    )


def _format_report_pair_row(row: HydePairRow) -> str:
    return (
        f"| `{row.query_id}` | `{row.query_type}` | `{row.baseline_route_method}` | "
        f"`{row.hyde_route_method}` | {_rank_text(row.baseline_relevant_rank)} | "
        f"{_rank_text(row.hyde_relevant_rank)} | {str(row.baseline_hit_at_5).lower()} | "
        f"{str(row.hyde_hit_at_5).lower()} | "
        f"`{row.hyde_generated_text_hash or 'blocked'}` | "
        f"{row.hyde_generated_text_length} | {row.solar_api_call_count} |"
    )


def _format_query_type_delta_row(row: HydeQueryTypeDelta) -> str:
    return (
        f"| `{row.query_type}` | {row.query_count} | "
        f"{row.baseline_recall_at_5:.6f} | {row.hyde_recall_at_5:.6f} | "
        f"{row.recall_at_5_delta:.6f} | {row.baseline_mrr:.6f} | "
        f"{row.hyde_mrr:.6f} | {row.mrr_delta:.6f} |"
    )


def _rank_text(rank: int | None) -> str:
    return "0" if rank is None else str(rank)


def main() -> int:
    args = _parse_args()
    report = run_hyde_live_paired_retrieval_comparison(
        dataset_path=args.dataset,
        chunks_path=args.chunks,
        env_file_path=args.env_file,
        doc_path=args.doc,
        report_path=args.report,
        result_rows_path=args.results,
        query_ids=tuple(args.query_id or DEFAULT_QUERY_IDS),
        live_call_hard_cap=args.live_call_hard_cap,
        top_k=args.top_k,
    )
    return 0 if not collect_hyde_live_paired_retrieval_failures(report) else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Solar Pro 3 HyDE live paired retrieval comparison.",
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS_PATH)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE_PATH)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    parser.add_argument("--query-id", action="append", default=None)
    parser.add_argument(
        "--live-call-hard-cap",
        type=int,
        default=DEFAULT_LIVE_CALL_HARD_CAP,
    )
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
