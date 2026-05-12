from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path

from app.application.chat_retrieval import ChatRetrievalBackend, PrivateArtifactRetrievalBackend
from app.core.project_paths import project_path
from app.domain.generation import CitationRagAnswer
from app.domain.generation_eval import (
    GenerationEvalReport,
    GenerationEvalUsage,
    build_generation_eval_records,
    build_generation_eval_report,
    build_public_generation_eval_rows,
    collect_generation_eval_harness_failures,
)
from app.domain.retrieval import QueryType, RetrievalEvalItem, load_retrieval_eval_jsonl
from app.providers.llm.base import CitationDraftProvider
from pipelines.run_solar_live_generation_smoke import (
    DEFAULT_CHUNKS_PATH,
    DEFAULT_DATASET_PATH,
    DEFAULT_PACKING_POLICY_ID,
    DEFAULT_RETRIEVAL_RUN_LABEL,
    SolarLiveProviderUsageTotals,
    _answer_smoke_item,
    _build_eval_inputs,
    _build_provider_context,
    _format_query_type_summary_row,
    _load_child_chunks_by_id,
    _validate_result_rows_path,
    write_jsonl_rows,
)


SOLAR_GENERATION_BASELINE_REPORT_VERSION = "solar-generation-baseline-report/v1"
SOLAR_GENERATION_BASELINE_ANSWER_POLICY_ID = "solar-generation-baseline-v1"
DEFAULT_REPORT_PATH = Path("evals") / "reports" / "solar_generation_baseline_report.md"
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data") / "evals" / "results" / "solar_generation_baseline_results.jsonl"
)
DEFAULT_ENV_FILE_PATH = Path(".env")
DEFAULT_QUERY_TYPES: tuple[QueryType, ...] = (
    "place_fact",
    "place_story",
    "relationship",
    "overview",
    "route_context",
    "voice_followup",
    "no_answer",
)
SOLAR_CHAT_LATENCY_SLO_MS = 8000.0


@dataclass(frozen=True)
class SolarGenerationBaselineRunContext:
    dataset_path_alias: str
    chunks_path_alias: str
    retrieval_run_label: str
    packing_policy_id: str
    answer_policy_id: str
    provider_config_id: str
    model_id: str
    endpoint_alias: str
    query_types: tuple[QueryType, ...]
    per_query_type: int
    usage_totals: SolarLiveProviderUsageTotals


def run_solar_generation_baseline(
    *,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    chunks_path: Path = DEFAULT_CHUNKS_PATH,
    env_file_path: Path | None = DEFAULT_ENV_FILE_PATH,
    per_query_type: int = 1,
    query_types: tuple[QueryType, ...] = DEFAULT_QUERY_TYPES,
    retrieval_backend: ChatRetrievalBackend | None = None,
    draft_provider: CitationDraftProvider | None = None,
) -> GenerationEvalReport:
    """Run a query-type stratified private Solar Pro 3 generation baseline."""
    _validate_result_rows_path(result_rows_path)
    if draft_provider is None and env_file_path is not None:
        load_env_file_into_process(env_file_path)
    provider, provider_context = _build_provider_context(draft_provider)
    resolved_dataset_path = project_path(dataset_path)
    resolved_chunks_path = project_path(chunks_path)
    items = select_generation_baseline_items(
        load_retrieval_eval_jsonl(resolved_dataset_path),
        query_types=query_types,
        per_query_type=per_query_type,
    )
    child_chunks_by_id = _load_child_chunks_by_id(resolved_chunks_path)
    backend = retrieval_backend or PrivateArtifactRetrievalBackend(chunks_path=chunks_path)

    answers: list[CitationRagAnswer] = []
    usage_by_query_id: dict[str, GenerationEvalUsage] = {}
    usage_totals = SolarLiveProviderUsageTotals()

    for item in items:
        answer, usage, provider_usage = _answer_smoke_item(
            item=item,
            retrieval_backend=backend,
            draft_provider=provider,
            child_chunks_by_id=child_chunks_by_id,
            provider_context=provider_context,
            answer_policy_id=SOLAR_GENERATION_BASELINE_ANSWER_POLICY_ID,
        )
        answers.append(answer)
        usage_by_query_id[item.query.query_id] = usage
        usage_totals = usage_totals.add(provider_usage)

    inputs = _build_eval_inputs(
        items=items,
        answers=answers,
        provider_config_id=provider_context.provider_config_id,
        usage_by_query_id=usage_by_query_id,
    )
    context = SolarGenerationBaselineRunContext(
        dataset_path_alias="<private retrieval eval dataset: retrieval_eval_dev.jsonl>",
        chunks_path_alias="<private parent_child_chunks report>",
        retrieval_run_label=DEFAULT_RETRIEVAL_RUN_LABEL,
        packing_policy_id=DEFAULT_PACKING_POLICY_ID,
        answer_policy_id=SOLAR_GENERATION_BASELINE_ANSWER_POLICY_ID,
        provider_config_id=provider_context.provider_config_id,
        model_id=provider_context.model_id,
        endpoint_alias=provider_context.endpoint_alias,
        query_types=query_types,
        per_query_type=per_query_type,
        usage_totals=usage_totals,
    )
    provisional = build_generation_eval_report(inputs=inputs)
    provisional_markdown = build_solar_generation_baseline_report_markdown(
        report=provisional,
        context=context,
    )
    report = build_generation_eval_report(
        inputs=inputs,
        report_text=provisional_markdown,
    )
    markdown = build_solar_generation_baseline_report_markdown(
        report=report,
        context=context,
    )
    failures = collect_solar_generation_baseline_failures(
        report=report,
        expected_query_types=query_types,
    )
    if failures:
        raise ValueError(f"solar generation baseline gate failed: {failures}")

    rows = build_public_generation_eval_rows(
        records=build_generation_eval_records(inputs),
    )
    write_jsonl_rows(path=result_rows_path, rows=rows)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(markdown, encoding="utf-8")
    return report


def select_generation_baseline_items(
    items: list[RetrievalEvalItem],
    *,
    query_types: tuple[QueryType, ...] = DEFAULT_QUERY_TYPES,
    per_query_type: int = 1,
) -> list[RetrievalEvalItem]:
    if per_query_type <= 0:
        raise ValueError("per_query_type must be positive")
    selected: list[RetrievalEvalItem] = []
    for query_type in query_types:
        candidates = sorted(
            (item for item in items if item.query.query_type == query_type),
            key=lambda item: item.query.query_id,
        )
        if len(candidates) < per_query_type:
            raise ValueError(f"not enough generation baseline items for {query_type}")
        selected.extend(candidates[:per_query_type])
    return selected


def load_env_file_into_process(path: Path, *, override: bool = False) -> bool:
    env_path = project_path(path)
    if not env_path.exists():
        return False
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        if override or not os.environ.get(key):
            os.environ[key] = value
    return True


def build_solar_generation_baseline_report_markdown(
    *,
    report: GenerationEvalReport,
    context: SolarGenerationBaselineRunContext,
) -> str:
    summary = report.summary
    quality = report.output_quality
    breakdown_rows = "\n".join(
        _format_query_type_summary_row(row) for row in report.query_type_breakdown
    )
    failure_rows = "\n".join(_format_failure_row(row) for row in report.query_type_breakdown)
    qualitative_rows = "\n".join(
        f"- `{key}`: {value}" for key, value in report.qualitative_assessment.items()
    )
    query_type_text = ", ".join(context.query_types)
    return f"""# Solar Pro 3 Generation Baseline Report

## 목적

private dev stratified subset에서 Solar Pro 3 citation RAG generation baseline을 고정한다.

이 문서는 최종 품질 개선 주장이 아니다. prompt 개선, answer contract 개선, rerank/packing 변경의 비교 기준선을 만들기 위한 baseline이다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{SOLAR_GENERATION_BASELINE_REPORT_VERSION}` |
| generation_eval_report_version | `{report.report_version}` |
| answer_contract_version | `{report.answer_contract_version}` |
| eval_id | `{report.eval_id}` |
| generated_at_utc | `{report.generated_at_utc}` |
| dataset_fingerprint | `{report.dataset_fingerprint}` |
| dataset_path | `{context.dataset_path_alias}` |
| chunks_path | `{context.chunks_path_alias}` |
| retrieval_run_label | `{context.retrieval_run_label}` |
| packing_policy_id | `{context.packing_policy_id}` |
| answer_policy_id | `{context.answer_policy_id}` |
| provider_config_id | `{context.provider_config_id}` |
| endpoint_alias | `{context.endpoint_alias}` |
| model_id | `{context.model_id}` |
| per_query_type | {context.per_query_type} |
| query_types | `{query_type_text}` |

## 정량 리포트

| metric | value |
| --- | ---: |
| eval_count | {summary.eval_count} |
| answerable_count | {summary.answerable_count} |
| no_answer_count | {summary.no_answer_count} |
| answered_count | {summary.answered_count} |
| abstained_count | {summary.abstained_count} |
| Correct-with-Evidence | {summary.correct_with_evidence_rate:.6f} |
| citation_precision | {summary.citation_precision:.6f} |
| citation_recall | {summary.citation_recall:.6f} |
| place_relevance | {summary.place_relevance:.6f} |
| docent_usefulness | {summary.docent_usefulness:.6f} |
| spoken_answer_naturalness | {summary.spoken_answer_naturalness:.6f} |
| unsupported_claim_rate | {summary.unsupported_claim_rate:.6f} |
| abstention_accuracy | {summary.abstention_accuracy:.6f} |
| latency_p95_ms | {summary.latency_p95_ms:.6f} |
| solar_call_count | {summary.solar_call_count} |
| prompt_tokens | {context.usage_totals.prompt_tokens} |
| completion_tokens | {context.usage_totals.completion_tokens} |
| total_tokens | {context.usage_totals.total_tokens} |
| estimated_cost | {summary.estimated_cost:.6f} |
| missing_citation_count | {summary.missing_citation_count} |
| unsupported_high_count | {summary.unsupported_high_count} |

## Query Type Breakdown

| query_type | eval_count | answerable_count | Correct-with-Evidence | citation_precision | citation_recall | place_relevance | docent_usefulness | spoken_answer_naturalness | unsupported_claim_rate | abstention_accuracy | latency_p95_ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{breakdown_rows}

## Failure Analysis

| query_type | failure_tags |
| --- | --- |
{failure_rows}

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

이 baseline은 query type별 1건으로 live generation 경로와 실패 유형을 관찰하는 기준선이다.

다음 단계의 prompt 또는 answer contract 개선은 이 report와 같은 query set, 같은 retrieval label, 같은 packing policy에서 paired comparison으로만 주장한다.
"""


def collect_solar_generation_baseline_failures(
    *,
    report: GenerationEvalReport,
    expected_query_types: tuple[QueryType, ...] = DEFAULT_QUERY_TYPES,
) -> list[str]:
    failures = collect_generation_eval_harness_failures(report)
    present_query_types = {row.query_type for row in report.query_type_breakdown}
    missing_query_types = set(expected_query_types) - present_query_types
    if missing_query_types:
        failures.append("missing_query_type_breakdown")
    if report.summary.answerable_count == 0:
        failures.append("answerable_baseline_case_missing")
    if report.summary.solar_call_count == 0:
        failures.append("solar_live_call_missing")
    return failures


def _format_failure_row(row) -> str:
    tags: list[str] = []
    if row.answerable_count and row.correct_with_evidence_rate < 1.0:
        tags.append("correct_with_evidence_gap")
    if row.answerable_count and row.citation_precision < 0.5:
        tags.append("low_citation_precision")
    if row.answerable_count and row.citation_recall < 0.5:
        tags.append("low_citation_recall")
    if row.spoken_answer_naturalness < 1.0:
        tags.append("spoken_answer_naturalness_gap")
    if row.unsupported_claim_rate > 0:
        tags.append("unsupported_claim")
    if row.latency_p95_ms > SOLAR_CHAT_LATENCY_SLO_MS and row.answerable_count:
        tags.append("latency_slo_exceeded")
    if not tags:
        tags.append("none")
    return f"| {row.query_type} | `{', '.join(tags)}` |"


def main() -> int:
    args = _parse_args()
    query_types = tuple(args.query_types) if args.query_types else DEFAULT_QUERY_TYPES
    report = run_solar_generation_baseline(
        report_path=args.report,
        result_rows_path=args.result_rows,
        dataset_path=args.dataset,
        chunks_path=args.chunks,
        env_file_path=args.env_file,
        per_query_type=args.per_query_type,
        query_types=query_types,
    )
    failures = collect_solar_generation_baseline_failures(
        report=report,
        expected_query_types=query_types,
    )
    print(
        "solar_generation_baseline "
        f"status={'PASS' if not failures else 'FAIL'} "
        f"eval_count={report.summary.eval_count} "
        f"correct_with_evidence={report.summary.correct_with_evidence_rate:.6f} "
        f"citation_precision={report.summary.citation_precision:.6f} "
        f"abstention_accuracy={report.summary.abstention_accuracy:.6f} "
        f"latency_p95_ms={report.summary.latency_p95_ms:.6f} "
        f"solar_call_count={report.summary.solar_call_count} "
        f"failures={len(failures)}",
    )
    return 0 if not failures else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run private Solar Pro 3 generation baseline by query type.",
    )
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--result-rows", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS_PATH)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE_PATH)
    parser.add_argument("--per-query-type", type=int, default=1)
    parser.add_argument("--query-types", nargs="*", choices=DEFAULT_QUERY_TYPES)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
