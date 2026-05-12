from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from pydantic import Field

from app.application.chat_retrieval import ChatRetrievalBackend, PrivateArtifactRetrievalBackend
from app.core.project_paths import project_path
from app.domain.chunking import ChildChunk
from app.domain.generation import CitationRagAnswer
from app.domain.generation_eval import (
    GenerationEvalInput,
    GenerationEvalReport,
    GenerationEvalUsage,
    build_generation_eval_dataset_fingerprint,
    build_generation_eval_records,
    build_generation_eval_report,
    collect_generation_eval_harness_failures,
)
from app.domain.retrieval import QueryType, RetrievalEvalItem, load_retrieval_eval_jsonl
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    measure_public_retrieval_artifact_quality,
)
from app.providers.llm.base import CitationDraftProvider
from app.providers.llm.solar_pro_3 import (
    CitationDraftSchemaVersion,
    SolarPro3CitationDraftProvider,
    SolarPro3ProviderConfig,
)
from pipelines.run_solar_generation_baseline import (
    DEFAULT_ENV_FILE_PATH,
    load_env_file_into_process,
    select_generation_baseline_items,
)
from pipelines.run_solar_generation_contract_v2_comparison import (
    DEFAULT_QUERY_TYPES,
    DEFAULT_RETRIEVAL_RUN_LABEL,
    SOLAR_GENERATION_BASELINE_ANSWER_POLICY_ID,
    SOLAR_GENERATION_CONTRACT_V2_ANSWER_POLICY_ID,
    GenerationPolicyPairDelta,
    GenerationPolicyQueryTypeDelta,
    SolarGenerationContractV2ComparisonModel,
    build_generation_policy_pair_deltas,
    build_generation_policy_query_type_deltas,
    build_public_solar_generation_contract_v2_comparison_rows_from_deltas,
    build_solar_generation_contract_v2_comparison_id,
    validate_generation_contract_v2_comparison_inputs,
)
from pipelines.run_solar_live_generation_smoke import (
    DEFAULT_CHUNKS_PATH,
    DEFAULT_DATASET_PATH,
    DEFAULT_PACKING_POLICY_ID,
    SolarLiveProviderUsageTotals,
    _ProviderRunContext,
    _answer_smoke_item,
    _build_eval_inputs,
    _build_provider_context,
    _format_query_type_summary_row,
    _load_child_chunks_by_id,
    _validate_result_rows_path,
    write_jsonl_rows,
)


SOLAR_GENERATION_CONTRACT_V2_LIVE_COMPARISON_REPORT_VERSION = (
    "solar-generation-contract-v2-live-comparison-report/v1"
)
DEFAULT_REPORT_PATH = (
    Path("evals")
    / "reports"
    / "solar_generation_contract_v2_live_comparison_report.md"
)
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "solar_generation_contract_v2_live_comparison_results.jsonl"
)


@dataclass(frozen=True)
class SolarGenerationContractV2LiveRunContext:
    dataset_path_alias: str
    chunks_path_alias: str
    retrieval_run_label: str
    packing_policy_id: str
    query_types: tuple[QueryType, ...]
    per_query_type: int
    baseline_usage_totals: SolarLiveProviderUsageTotals
    candidate_usage_totals: SolarLiveProviderUsageTotals
    baseline_model_id: str
    candidate_model_id: str
    baseline_endpoint_alias: str
    candidate_endpoint_alias: str


class SolarGenerationContractV2LiveComparisonReport(
    SolarGenerationContractV2ComparisonModel,
):
    report_version: str = SOLAR_GENERATION_CONTRACT_V2_LIVE_COMPARISON_REPORT_VERSION
    comparison_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    dataset_fingerprint: str = Field(min_length=8)
    retrieval_run_label: str = Field(min_length=1)
    packing_policy_id: str = Field(min_length=1)
    baseline_answer_policy_id: str = Field(min_length=1)
    candidate_answer_policy_id: str = Field(min_length=1)
    baseline_provider_config_id: str = Field(min_length=1)
    candidate_provider_config_id: str = Field(min_length=1)
    baseline_report: GenerationEvalReport
    candidate_report: GenerationEvalReport
    paired_deltas: tuple[GenerationPolicyPairDelta, ...]
    query_type_deltas: tuple[GenerationPolicyQueryTypeDelta, ...]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def run_solar_generation_contract_v2_live_comparison(
    *,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    chunks_path: Path = DEFAULT_CHUNKS_PATH,
    env_file_path: Path | None = DEFAULT_ENV_FILE_PATH,
    per_query_type: int = 1,
    query_types: tuple[QueryType, ...] = DEFAULT_QUERY_TYPES,
    retrieval_backend: ChatRetrievalBackend | None = None,
    baseline_draft_provider: CitationDraftProvider | None = None,
    candidate_draft_provider: CitationDraftProvider | None = None,
) -> SolarGenerationContractV2LiveComparisonReport:
    """Run private retrieval-backed live Solar Pro 3 v1/v2 paired comparison.

    Public artifacts contain only aggregate metrics and public-safe deltas. Raw query
    text, raw answers, evidence text, chunk text, private paths, and secrets are never
    written to the public report.
    """
    _validate_result_rows_path(result_rows_path)
    if (
        (baseline_draft_provider is None or candidate_draft_provider is None)
        and env_file_path is not None
    ):
        load_env_file_into_process(env_file_path)

    baseline_provider, baseline_context = _build_live_provider_context(
        baseline_draft_provider,
        schema_version="v1",
    )
    candidate_provider, candidate_context = _build_live_provider_context(
        candidate_draft_provider,
        schema_version="v2",
    )
    resolved_dataset_path = project_path(dataset_path)
    resolved_chunks_path = project_path(chunks_path)
    items = select_generation_baseline_items(
        load_retrieval_eval_jsonl(resolved_dataset_path),
        query_types=query_types,
        per_query_type=per_query_type,
    )
    child_chunks_by_id = _load_child_chunks_by_id(resolved_chunks_path)
    backend = retrieval_backend or PrivateArtifactRetrievalBackend(chunks_path=chunks_path)

    baseline_inputs, baseline_usage_totals = _build_policy_inputs(
        items=items,
        retrieval_backend=backend,
        draft_provider=baseline_provider,
        child_chunks_by_id=child_chunks_by_id,
        provider_context=baseline_context,
        answer_policy_id=SOLAR_GENERATION_BASELINE_ANSWER_POLICY_ID,
    )
    candidate_inputs, candidate_usage_totals = _build_policy_inputs(
        items=items,
        retrieval_backend=backend,
        draft_provider=candidate_provider,
        child_chunks_by_id=child_chunks_by_id,
        provider_context=candidate_context,
        answer_policy_id=SOLAR_GENERATION_CONTRACT_V2_ANSWER_POLICY_ID,
    )
    context = SolarGenerationContractV2LiveRunContext(
        dataset_path_alias="<private retrieval eval dataset: retrieval_eval_dev.jsonl>",
        chunks_path_alias="<private parent_child_chunks report>",
        retrieval_run_label=DEFAULT_RETRIEVAL_RUN_LABEL,
        packing_policy_id=DEFAULT_PACKING_POLICY_ID,
        query_types=query_types,
        per_query_type=per_query_type,
        baseline_usage_totals=baseline_usage_totals,
        candidate_usage_totals=candidate_usage_totals,
        baseline_model_id=baseline_context.model_id,
        candidate_model_id=candidate_context.model_id,
        baseline_endpoint_alias=baseline_context.endpoint_alias,
        candidate_endpoint_alias=candidate_context.endpoint_alias,
    )
    provisional_report = build_solar_generation_contract_v2_live_comparison_report(
        baseline_inputs=baseline_inputs,
        candidate_inputs=candidate_inputs,
        context=context,
    )
    provisional_markdown = build_solar_generation_contract_v2_live_comparison_markdown(
        provisional_report,
        context=context,
    )
    report = build_solar_generation_contract_v2_live_comparison_report(
        baseline_inputs=baseline_inputs,
        candidate_inputs=candidate_inputs,
        context=context,
        report_text=provisional_markdown,
    )
    markdown = build_solar_generation_contract_v2_live_comparison_markdown(
        report,
        context=context,
    )
    failures = collect_solar_generation_contract_v2_live_comparison_failures(report)
    if failures:
        raise ValueError(
            f"solar generation contract v2 live comparison gate failed: {failures}",
        )

    rows = build_public_solar_generation_contract_v2_comparison_rows_from_deltas(
        report.paired_deltas,
    )
    write_jsonl_rows(path=result_rows_path, rows=rows)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(markdown, encoding="utf-8")
    return report


def build_solar_generation_contract_v2_live_comparison_report(
    *,
    baseline_inputs: list[GenerationEvalInput],
    candidate_inputs: list[GenerationEvalInput],
    context: SolarGenerationContractV2LiveRunContext,
    report_text: str = "",
) -> SolarGenerationContractV2LiveComparisonReport:
    validate_generation_contract_v2_comparison_inputs(
        baseline_inputs=baseline_inputs,
        candidate_inputs=candidate_inputs,
    )
    baseline_report = build_generation_eval_report(inputs=baseline_inputs)
    candidate_report = build_generation_eval_report(inputs=candidate_inputs)
    baseline_records = build_generation_eval_records(baseline_inputs)
    candidate_records = build_generation_eval_records(candidate_inputs)
    paired_deltas = tuple(
        build_generation_policy_pair_deltas(
            baseline_records=baseline_records,
            candidate_records=candidate_records,
        ),
    )
    query_type_deltas = tuple(build_generation_policy_query_type_deltas(paired_deltas))
    public_rows = build_public_solar_generation_contract_v2_comparison_rows_from_deltas(
        paired_deltas,
    )
    comparison_id = build_solar_generation_contract_v2_comparison_id(
        baseline_records=baseline_records,
        candidate_records=candidate_records,
    )
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=SOLAR_GENERATION_CONTRACT_V2_LIVE_COMPARISON_REPORT_VERSION,
        run_id=comparison_id,
        result_rows=public_rows,
        report_text=report_text,
    )
    report = SolarGenerationContractV2LiveComparisonReport(
        comparison_id=comparison_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        dataset_fingerprint=build_generation_eval_dataset_fingerprint(baseline_inputs),
        retrieval_run_label=context.retrieval_run_label,
        packing_policy_id=context.packing_policy_id,
        baseline_answer_policy_id=SOLAR_GENERATION_BASELINE_ANSWER_POLICY_ID,
        candidate_answer_policy_id=SOLAR_GENERATION_CONTRACT_V2_ANSWER_POLICY_ID,
        baseline_provider_config_id=_single_provider_config_id(
            baseline_inputs,
            field_name="baseline_provider_config_id",
        ),
        candidate_provider_config_id=_single_provider_config_id(
            candidate_inputs,
            field_name="candidate_provider_config_id",
        ),
        baseline_report=baseline_report,
        candidate_report=candidate_report,
        paired_deltas=paired_deltas,
        query_type_deltas=query_type_deltas,
        output_quality=output_quality,
        qualitative_assessment={},
    )
    return report.model_copy(
        update={
            "qualitative_assessment": build_live_comparison_qualitative_assessment(report),
        },
    )


def collect_solar_generation_contract_v2_live_comparison_failures(
    report: SolarGenerationContractV2LiveComparisonReport,
) -> list[str]:
    failures: list[str] = []
    failures.extend(
        f"baseline_{failure}"
        for failure in collect_generation_eval_harness_failures(report.baseline_report)
    )
    failures.extend(
        f"candidate_{failure}"
        for failure in collect_generation_eval_harness_failures(report.candidate_report)
    )
    if report.baseline_report.summary.eval_count != report.candidate_report.summary.eval_count:
        failures.append("mismatched_eval_count")
    if not report.paired_deltas:
        failures.append("empty_paired_delta")
    if report.baseline_report.summary.solar_call_count == 0:
        failures.append("baseline_solar_live_call_missing")
    if report.candidate_report.summary.solar_call_count == 0:
        failures.append("candidate_solar_live_call_missing")
    if report.output_quality.public_raw_text_leakage_count:
        failures.append("public_raw_text_leakage")
    if report.output_quality.private_path_leakage_count:
        failures.append("private_path_leakage")
    if report.output_quality.secret_like_leakage_count:
        failures.append("secret_like_leakage")
    if report.output_quality.forbidden_result_field_count:
        failures.append("forbidden_public_result_fields")
    return failures


def build_solar_generation_contract_v2_live_comparison_markdown(
    report: SolarGenerationContractV2LiveComparisonReport,
    *,
    context: SolarGenerationContractV2LiveRunContext,
) -> str:
    baseline = report.baseline_report.summary
    candidate = report.candidate_report.summary
    quality = report.output_quality
    paired_rows = "\n".join(_format_pair_delta_row(delta) for delta in report.paired_deltas)
    query_type_rows = "\n".join(
        _format_query_type_delta_row(delta) for delta in report.query_type_deltas
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
    query_type_text = ", ".join(context.query_types)
    return f"""# Solar Pro 3 Generation Contract v2 Live Comparison Report

## 목적

Solar Pro 3 실제 호출로 `CitationRagDraft` v1과 `CitationRagDraftV2` selected evidence contract를 같은 query set, 같은 retrieval label, 같은 evidence packing policy에서 paired comparison으로 비교한다.

이 문서는 private dev subset 기반의 실험 결과다. 최종 성능 개선 주장이 아니라 generation contract v2 채택 여부를 판단하기 위한 근거다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| comparison_id | `{report.comparison_id}` |
| generated_at_utc | `{report.generated_at_utc}` |
| dataset_fingerprint | `{report.dataset_fingerprint}` |
| dataset_path | `{context.dataset_path_alias}` |
| chunks_path | `{context.chunks_path_alias}` |
| retrieval_run_label | `{report.retrieval_run_label}` |
| packing_policy_id | `{report.packing_policy_id}` |
| baseline_answer_policy_id | `{report.baseline_answer_policy_id}` |
| candidate_answer_policy_id | `{report.candidate_answer_policy_id}` |
| baseline_provider_config_id | `{report.baseline_provider_config_id}` |
| candidate_provider_config_id | `{report.candidate_provider_config_id}` |
| baseline_model_id | `{context.baseline_model_id}` |
| candidate_model_id | `{context.candidate_model_id}` |
| baseline_endpoint_alias | `{context.baseline_endpoint_alias}` |
| candidate_endpoint_alias | `{context.candidate_endpoint_alias}` |
| per_query_type | {context.per_query_type} |
| query_types | `{query_type_text}` |

## 정량 리포트

| metric | v1 baseline | v2 candidate | delta |
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
| prompt_tokens | {context.baseline_usage_totals.prompt_tokens} | {context.candidate_usage_totals.prompt_tokens} | {context.candidate_usage_totals.prompt_tokens - context.baseline_usage_totals.prompt_tokens} |
| completion_tokens | {context.baseline_usage_totals.completion_tokens} | {context.candidate_usage_totals.completion_tokens} | {context.candidate_usage_totals.completion_tokens - context.baseline_usage_totals.completion_tokens} |
| total_tokens | {context.baseline_usage_totals.total_tokens} | {context.candidate_usage_totals.total_tokens} | {context.candidate_usage_totals.total_tokens - context.baseline_usage_totals.total_tokens} |
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

| query_id | query_type | Correct delta | citation_precision delta | citation_recall delta | unsupported_claim delta | citation_count delta | latency_ms delta |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
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

## 해석

v2는 Solar Pro 3가 선택한 evidence rank만 citation으로 붙이는 계약이다. 따라서 citation precision, citation count, latency/token 변화를 함께 본다.

이번 실험은 locked test가 아니라 private dev subset에서 실행했다. 포트폴리오에는 "채택 후보 검증"으로만 쓰고, 최종 개선 주장은 이후 locked test와 bootstrap confidence interval을 붙인 뒤에만 사용한다.
"""


def build_live_comparison_qualitative_assessment(
    report: SolarGenerationContractV2LiveComparisonReport,
) -> dict[str, str]:
    failures = collect_solar_generation_contract_v2_live_comparison_failures(report)
    latency_delta = (
        report.candidate_report.summary.latency_p95_ms
        - report.baseline_report.summary.latency_p95_ms
    )
    return {
        "comparison_scope": (
            "v1/v2 generation contract만 다르게 두고 query set, retrieval label, packing policy를 고정했다."
        ),
        "provider_boundary": (
            "이번 runner는 Solar Pro 3 live API를 호출한다. no_answer query는 abstain contract로 처리해 provider를 호출하지 않는다."
        ),
        "metric_grain": ("query 단위 paired delta와 query_type delta를 분리해 기록한다."),
        "citation_policy": (
            "v1은 packed evidence 전체를 citation으로 붙이고, v2는 selected evidence rank만 citation으로 붙인다."
        ),
        "latency_cost_boundary": (
            f"candidate latency_p95 delta는 {latency_delta:.6f}ms다. token/cost 변화는 정량 표에서 별도로 판단한다."
        ),
        "place_story_boundary": (
            "`place_story`는 retrieval hard-case 영향을 받기 쉬워 generation contract 개선 판단에서 별도 모니터링한다."
        ),
        "claim_boundary": (
            "현재 결과는 private dev subset의 live paired comparison이며 final production 성능 개선 주장이 아니다."
        ),
        "public_policy": (
            "public report와 result row에는 raw query, raw answer, evidence text, chunk text, private path, secret을 저장하지 않는다."
        ),
        "gate_status": "PASS" if not failures else f"FAIL: {', '.join(failures)}",
    }


def _build_policy_inputs(
    *,
    items: list[RetrievalEvalItem],
    retrieval_backend: ChatRetrievalBackend,
    draft_provider: CitationDraftProvider,
    child_chunks_by_id: dict[str, ChildChunk],
    provider_context: _ProviderRunContext,
    answer_policy_id: str,
) -> tuple[list[GenerationEvalInput], SolarLiveProviderUsageTotals]:
    answers: list[CitationRagAnswer] = []
    usage_by_query_id: dict[str, GenerationEvalUsage] = {}
    usage_totals = SolarLiveProviderUsageTotals()
    for item in items:
        answer, usage, provider_usage = _answer_smoke_item(
            item=item,
            retrieval_backend=retrieval_backend,
            draft_provider=draft_provider,
            child_chunks_by_id=child_chunks_by_id,
            provider_context=provider_context,
            answer_policy_id=answer_policy_id,
        )
        answers.append(answer)
        usage_by_query_id[item.query.query_id] = usage
        usage_totals = usage_totals.add(provider_usage)
    return (
        _build_eval_inputs(
            items=items,
            answers=answers,
            provider_config_id=provider_context.provider_config_id,
            usage_by_query_id=usage_by_query_id,
        ),
        usage_totals,
    )


def _build_live_provider_context(
    draft_provider: CitationDraftProvider | None,
    *,
    schema_version: CitationDraftSchemaVersion,
) -> tuple[CitationDraftProvider, _ProviderRunContext]:
    if draft_provider is not None:
        return _build_provider_context(draft_provider)
    config = SolarPro3ProviderConfig.from_env(draft_schema_version=schema_version)
    provider = SolarPro3CitationDraftProvider(config=config)
    return provider, _ProviderRunContext(
        provider_config_id=config.provider_config_id,
        provider_kind="solar_pro_3",
        model_id=config.model_id,
        endpoint_alias=config.endpoint.replace("https://", "").replace("http://", ""),
    )


def _format_pair_delta_row(delta: GenerationPolicyPairDelta) -> str:
    return (
        f"| {delta.query_id} | {delta.query_type} | "
        f"{delta.correct_with_evidence_delta} | "
        f"{delta.citation_precision_delta:.6f} | "
        f"{delta.citation_recall_delta:.6f} | "
        f"{delta.unsupported_claim_delta} | "
        f"{delta.citation_count_delta} | "
        f"{delta.latency_ms_delta:.6f} |"
    )


def _format_query_type_delta_row(delta: GenerationPolicyQueryTypeDelta) -> str:
    return (
        f"| {delta.query_type} | {delta.eval_count} | "
        f"{delta.correct_with_evidence_delta:.6f} | "
        f"{delta.citation_precision_delta:.6f} | "
        f"{delta.citation_recall_delta:.6f} | "
        f"{delta.unsupported_claim_rate_delta:.6f} | "
        f"{delta.latency_p95_ms_delta:.6f} |"
    )


def _single_provider_config_id(
    inputs: list[GenerationEvalInput],
    *,
    field_name: str,
) -> str:
    values = {item.provider_config_id for item in inputs}
    if len(values) != 1:
        raise ValueError(f"{field_name} must have exactly one value")
    return next(iter(values))


def main() -> int:
    args = _parse_args()
    report = run_solar_generation_contract_v2_live_comparison(
        report_path=args.report,
        result_rows_path=args.result_rows,
        dataset_path=args.dataset,
        chunks_path=args.chunks,
        per_query_type=args.per_query_type,
    )
    failures = collect_solar_generation_contract_v2_live_comparison_failures(report)
    baseline = report.baseline_report.summary
    candidate = report.candidate_report.summary
    print(
        "solar_generation_contract_v2_live_comparison "
        f"status={'PASS' if not failures else 'FAIL'} "
        f"eval_count={baseline.eval_count} "
        f"correct_with_evidence_delta="
        f"{candidate.correct_with_evidence_rate - baseline.correct_with_evidence_rate:.6f} "
        f"citation_precision_delta="
        f"{candidate.citation_precision - baseline.citation_precision:.6f} "
        f"solar_call_count={baseline.solar_call_count + candidate.solar_call_count} "
        f"failures={len(failures)}",
    )
    return 0 if not failures else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run live Solar Pro 3 generation contract v1/v2 paired comparison.",
    )
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--result-rows", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS_PATH)
    parser.add_argument("--per-query-type", type=int, default=1)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
