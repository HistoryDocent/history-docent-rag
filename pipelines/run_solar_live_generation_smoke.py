from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.application.chat_retrieval import (
    ChatRetrievalBackend,
    ChatRetrievalOutcome,
    PrivateArtifactRetrievalBackend,
)
from app.application.chat_service import ChatCommand
from app.application.citation_rag import CitationRagAnswerAssembler, CitationRagAssemblerConfig
from app.core.project_paths import (
    has_private_data_segment,
    is_repository_private_artifact_path,
    is_repository_private_write_path,
    project_path,
)
from app.domain.chunking import ChildChunk
from app.domain.generation import AnswerProviderKind, CitationRagAnswer
from app.domain.generation_eval import (
    GenerationEvalInput,
    GenerationEvalReport,
    GenerationEvalUsage,
    build_generation_eval_records,
    build_generation_eval_report,
    build_public_generation_eval_rows,
    collect_generation_eval_harness_failures,
)
from app.domain.retrieval import RetrievalEvalItem, load_retrieval_eval_jsonl
from app.providers.llm.base import CitationDraftProvider, CitationDraftRequest
from app.providers.llm.solar_pro_3 import SolarPro3CitationDraftProvider, SolarPro3ProviderConfig


SOLAR_LIVE_GENERATION_SMOKE_REPORT_VERSION = "solar-live-generation-smoke-report/v1"
SOLAR_LIVE_ANSWER_POLICY_ID = "solar-live-generation-smoke-v1"
DEFAULT_DATASET_PATH = Path("private_data") / "evals" / "datasets" / "retrieval_eval_dev.jsonl"
DEFAULT_CHUNKS_PATH = Path("private_data") / "reports" / "parent_child_chunks.json"
DEFAULT_REPORT_PATH = Path("evals") / "reports" / "solar_live_generation_smoke_report.md"
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data") / "evals" / "results" / "solar_live_generation_smoke_results.jsonl"
)
DEFAULT_RETRIEVAL_RUN_LABEL = "dense_multilingual_e5_small_voice_rewrite"
DEFAULT_PACKING_POLICY_ID = "P0_rank_order"
DEFAULT_CONTEXT_CHAR_LIMIT = 11000


@dataclass(frozen=True)
class SolarLiveProviderUsageTotals:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0

    def add(self, result_usage) -> "SolarLiveProviderUsageTotals":
        return SolarLiveProviderUsageTotals(
            prompt_tokens=self.prompt_tokens + int(result_usage.prompt_tokens),
            completion_tokens=self.completion_tokens + int(result_usage.completion_tokens),
            total_tokens=self.total_tokens + int(result_usage.total_tokens),
            estimated_cost=round(
                self.estimated_cost + float(result_usage.estimated_cost),
                6,
            ),
        )


@dataclass(frozen=True)
class SolarLiveSmokeRunContext:
    dataset_path_alias: str
    chunks_path_alias: str
    retrieval_run_label: str
    packing_policy_id: str
    provider_config_id: str
    model_id: str
    endpoint_alias: str
    answerable_limit: int
    no_answer_limit: int
    usage_totals: SolarLiveProviderUsageTotals


def run_solar_live_generation_smoke(
    *,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_rows_path: Path = DEFAULT_RESULT_ROWS_PATH,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    chunks_path: Path = DEFAULT_CHUNKS_PATH,
    answerable_limit: int = 2,
    no_answer_limit: int = 1,
    retrieval_backend: ChatRetrievalBackend | None = None,
    draft_provider: CitationDraftProvider | None = None,
) -> GenerationEvalReport:
    """Run a small private retrieval-backed Solar Pro 3 generation smoke.

    The public report intentionally stores only aggregate metrics and public-safe rows.
    Raw query text, raw evidence text, raw answers, and secret values are never written.
    """
    _validate_result_rows_path(result_rows_path)
    provider, provider_context = _build_provider_context(draft_provider)
    resolved_dataset_path = project_path(dataset_path)
    resolved_chunks_path = project_path(chunks_path)
    items = _select_smoke_items(
        load_retrieval_eval_jsonl(resolved_dataset_path),
        answerable_limit=answerable_limit,
        no_answer_limit=no_answer_limit,
    )
    child_chunks_by_id = _load_child_chunks_by_id(resolved_chunks_path)
    backend = retrieval_backend or PrivateArtifactRetrievalBackend(chunks_path=chunks_path)
    answers: list[CitationRagAnswer] = []
    usage_by_query_id: dict[str, GenerationEvalUsage] = {}
    usage_totals = SolarLiveProviderUsageTotals()

    for item in items:
        answer, usage, provider_usage_totals = _answer_smoke_item(
            item=item,
            retrieval_backend=backend,
            draft_provider=provider,
            child_chunks_by_id=child_chunks_by_id,
            provider_context=provider_context,
        )
        answers.append(answer)
        usage_by_query_id[item.query.query_id] = usage
        usage_totals = usage_totals.add(provider_usage_totals)

    inputs = _build_eval_inputs(
        items=items,
        answers=answers,
        provider_config_id=provider_context.provider_config_id,
        usage_by_query_id=usage_by_query_id,
    )
    context = provider_context.with_usage_totals(
        answerable_limit=answerable_limit,
        no_answer_limit=no_answer_limit,
        usage_totals=usage_totals,
    )
    provisional = build_generation_eval_report(inputs=inputs)
    provisional_markdown = build_solar_live_generation_smoke_report_markdown(
        report=provisional,
        context=context,
    )
    report = build_generation_eval_report(
        inputs=inputs,
        report_text=provisional_markdown,
    )
    markdown = build_solar_live_generation_smoke_report_markdown(
        report=report,
        context=context,
    )
    failures = collect_solar_live_generation_smoke_failures(report)
    if failures:
        raise ValueError(f"solar live generation smoke gate failed: {failures}")

    rows = build_public_generation_eval_rows(
        records=build_generation_eval_records(inputs),
    )
    write_jsonl_rows(path=result_rows_path, rows=rows)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(markdown, encoding="utf-8")
    return report


def build_solar_live_generation_smoke_report_markdown(
    *,
    report: GenerationEvalReport,
    context: SolarLiveSmokeRunContext,
) -> str:
    summary = report.summary
    quality = report.output_quality
    breakdown_rows = "\n".join(
        _format_query_type_summary_row(row) for row in report.query_type_breakdown
    )
    qualitative_rows = "\n".join(
        f"- `{key}`: {value}" for key, value in report.qualitative_assessment.items()
    )
    return f"""# Solar Pro 3 Live Generation Smoke Report

## 목적

private retrieval 결과를 Solar Pro 3 structured output provider에 연결해 citation RAG answer contract와 generation eval harness가 실제 provider 호출을 견디는지 확인한다.

이 문서는 최종 답변 품질 개선 주장이 아니다. 작은 smoke subset이며, retrieval hit 여부와 답변 품질 판단은 추후 dev/test paired comparison에서 분리한다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{SOLAR_LIVE_GENERATION_SMOKE_REPORT_VERSION}` |
| generation_eval_report_version | `{report.report_version}` |
| answer_contract_version | `{report.answer_contract_version}` |
| eval_id | `{report.eval_id}` |
| generated_at_utc | `{report.generated_at_utc}` |
| dataset_fingerprint | `{report.dataset_fingerprint}` |
| dataset_path | `{context.dataset_path_alias}` |
| chunks_path | `{context.chunks_path_alias}` |
| retrieval_run_label | `{context.retrieval_run_label}` |
| packing_policy_id | `{context.packing_policy_id}` |
| provider_config_id | `{context.provider_config_id}` |
| endpoint_alias | `{context.endpoint_alias}` |
| model_id | `{context.model_id}` |
| answerable_limit | {context.answerable_limit} |
| no_answer_limit | {context.no_answer_limit} |

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

이 smoke는 live provider 연결과 public-safe 평가 산출물 생성을 검증한다. 답변 원문과 evidence 원문은 report/result row에 저장하지 않는다.

다음 단계에서는 같은 generation eval harness로 chunking, retrieval, rerank, generation 조합을 고정된 dev/test set에서 비교한다.
"""


def collect_solar_live_generation_smoke_failures(
    report: GenerationEvalReport,
) -> list[str]:
    failures = collect_generation_eval_harness_failures(report)
    if report.summary.answerable_count == 0:
        failures.append("answerable_smoke_case_missing")
    if report.summary.solar_call_count == 0:
        failures.append("solar_live_call_missing")
    return failures


def write_jsonl_rows(*, path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)
    path.write_text(payload + "\n", encoding="utf-8")


@dataclass(frozen=True)
class _ProviderRunContext:
    provider_config_id: str
    provider_kind: AnswerProviderKind
    model_id: str
    endpoint_alias: str

    def with_usage_totals(
        self,
        *,
        answerable_limit: int,
        no_answer_limit: int,
        usage_totals: SolarLiveProviderUsageTotals,
    ) -> SolarLiveSmokeRunContext:
        return SolarLiveSmokeRunContext(
            dataset_path_alias="<private retrieval eval dataset: retrieval_eval_dev.jsonl>",
            chunks_path_alias="<private parent_child_chunks report>",
            retrieval_run_label=DEFAULT_RETRIEVAL_RUN_LABEL,
            packing_policy_id=DEFAULT_PACKING_POLICY_ID,
            provider_config_id=self.provider_config_id,
            model_id=self.model_id,
            endpoint_alias=self.endpoint_alias,
            answerable_limit=answerable_limit,
            no_answer_limit=no_answer_limit,
            usage_totals=usage_totals,
        )


def _build_provider_context(
    draft_provider: CitationDraftProvider | None,
) -> tuple[CitationDraftProvider, _ProviderRunContext]:
    if draft_provider is not None:
        return draft_provider, _ProviderRunContext(
            provider_config_id=draft_provider.provider_config_id,
            provider_kind=_provider_kind(draft_provider),
            model_id=_provider_model_id(draft_provider),
            endpoint_alias=_provider_endpoint_alias(draft_provider),
        )
    config = SolarPro3ProviderConfig.from_env()
    provider = SolarPro3CitationDraftProvider(config=config)
    return provider, _ProviderRunContext(
        provider_config_id=config.provider_config_id,
        provider_kind="solar_pro_3",
        model_id=config.model_id,
        endpoint_alias=config.endpoint.replace("https://", "").replace("http://", ""),
    )


def _answer_smoke_item(
    *,
    item: RetrievalEvalItem,
    retrieval_backend: ChatRetrievalBackend,
    draft_provider: CitationDraftProvider,
    child_chunks_by_id: dict[str, ChildChunk],
    provider_context: _ProviderRunContext,
) -> tuple[CitationRagAnswer, GenerationEvalUsage, Any]:
    started = time.perf_counter()
    command = _command_from_item(item)
    retrieval = retrieval_backend.retrieve(command=command, item=item)
    assembler = _assembler(
        provider=provider_context.provider_kind,
        model_id=provider_context.model_id,
    )
    provider_usage = SolarLiveProviderUsageTotals()

    if item.query.expected_behavior == "abstain" or not retrieval.evidence_pack.evidence:
        answer = assembler.assemble(
            item=item,
            evidence_pack=retrieval.evidence_pack,
            place_ids=retrieval.place_ids or tuple(item.metadata.place_ids),
        )
        return answer, _usage(started=started, solar_call_count=0), provider_usage

    evidence_context = build_evidence_context(
        retrieval=retrieval,
        child_chunks_by_id=child_chunks_by_id,
    )
    result = draft_provider.generate_draft(
        CitationDraftRequest(
            query_id=item.query.query_id,
            query_type=item.query.query_type,
            query_text=item.query.query_text,
            evidence_context=evidence_context,
            place_ids=tuple(retrieval.place_ids or tuple(item.metadata.place_ids)),
            language=item.query.language,
        ),
    )
    answer = _assembler(
        provider=_answer_provider_kind(result.provider),
        model_id=result.model_id,
    ).assemble(
        item=item,
        evidence_pack=retrieval.evidence_pack,
        draft=result.draft,
        place_ids=retrieval.place_ids or tuple(item.metadata.place_ids),
    )
    return (
        answer,
        _usage(
            started=started,
            solar_call_count=result.usage.api_call_count,
            estimated_cost=result.usage.estimated_cost,
        ),
        result.usage,
    )


def build_evidence_context(
    *,
    retrieval: ChatRetrievalOutcome,
    child_chunks_by_id: dict[str, ChildChunk],
    max_chars: int = DEFAULT_CONTEXT_CHAR_LIMIT,
) -> str:
    chunks: list[str] = []
    remaining = max_chars
    for evidence in retrieval.evidence_pack.evidence:
        child = child_chunks_by_id.get(evidence.child_id)
        if child is None or not child.text:
            continue
        header = (
            f"[evidence:{evidence.pack_rank}] "
            f"child_id={evidence.child_id} "
            f"doc_id={evidence.doc_id} "
            f"page_global={child.page_span.page_global_start}-{child.page_span.page_global_end}"
        )
        body = child.text.strip()
        candidate = f"{header}\n{body}"
        if len(candidate) > remaining:
            candidate = candidate[: max(0, remaining - 3)].rstrip() + "..."
        if candidate.strip():
            chunks.append(candidate)
            remaining -= len(candidate) + 2
        if remaining <= 0:
            break
    context = "\n\n".join(chunks).strip()
    if not context:
        raise ValueError("selected evidence does not have private text for Solar context")
    return context


def _select_smoke_items(
    items: list[RetrievalEvalItem],
    *,
    answerable_limit: int,
    no_answer_limit: int,
) -> list[RetrievalEvalItem]:
    answerable_items = [item for item in items if item.query.expected_behavior == "retrieve"][
        :answerable_limit
    ]
    no_answer_items = [item for item in items if item.query.expected_behavior == "abstain"][
        :no_answer_limit
    ]
    if len(answerable_items) < answerable_limit:
        raise ValueError("private dev dataset does not contain enough answerable smoke items")
    if no_answer_limit and len(no_answer_items) < no_answer_limit:
        raise ValueError("private dev dataset does not contain enough no_answer smoke items")
    return answerable_items + no_answer_items


def _load_child_chunks_by_id(path: Path) -> dict[str, ChildChunk]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    children_payload = payload.get("children")
    if not isinstance(children_payload, list):
        raise ValueError("parent_child_chunks payload must include children list")
    children = [ChildChunk.model_validate(child) for child in children_payload]
    return {child.child_id: child for child in children}


def _build_eval_inputs(
    *,
    items: list[RetrievalEvalItem],
    answers: list[CitationRagAnswer],
    provider_config_id: str,
    usage_by_query_id: dict[str, GenerationEvalUsage],
) -> list[GenerationEvalInput]:
    items_by_query_id = {item.query.query_id: item for item in items}
    return [
        GenerationEvalInput(
            item=items_by_query_id[answer.query_id],
            answer=answer,
            packing_policy_id=DEFAULT_PACKING_POLICY_ID,
            retrieval_run_label=DEFAULT_RETRIEVAL_RUN_LABEL,
            provider_config_id=provider_config_id,
            usage=usage_by_query_id.get(answer.query_id, GenerationEvalUsage()),
        )
        for answer in answers
    ]


def _command_from_item(item: RetrievalEvalItem) -> ChatCommand:
    return ChatCommand(
        request_id=item.query.query_id,
        query=item.query.query_text,
        language=item.query.language,
        query_type=item.query.query_type,
        place_context=tuple(item.metadata.place_ids),
        voice_mode=item.query.query_type == "voice_followup",
        user_context=item.query.user_context,
        retrieval_mode="retrieval_backed",
        provider_mode="contract_only",
    )


def _assembler(
    *,
    provider: AnswerProviderKind,
    model_id: str,
) -> CitationRagAnswerAssembler:
    return CitationRagAnswerAssembler(
        config=CitationRagAssemblerConfig(
            answer_policy_id=SOLAR_LIVE_ANSWER_POLICY_ID,
            provider=provider,
            model_id=model_id,
        ),
    )


def _usage(
    *,
    started: float,
    solar_call_count: int,
    estimated_cost: float = 0.0,
) -> GenerationEvalUsage:
    return GenerationEvalUsage(
        latency_ms=round((time.perf_counter() - started) * 1000, 6),
        solar_call_count=solar_call_count,
        estimated_cost=estimated_cost,
    )


def _answer_provider_kind(provider: str) -> AnswerProviderKind:
    if provider == "fake":
        return "fake"
    return "solar_pro_3"


def _provider_kind(provider: CitationDraftProvider) -> AnswerProviderKind:
    value = getattr(provider, "provider", None)
    if value == "fake":
        return "fake"
    return "solar_pro_3"


def _provider_model_id(provider: CitationDraftProvider) -> str:
    value = getattr(provider, "model_id", None)
    if isinstance(value, str) and value:
        return value
    config = getattr(provider, "config", None)
    config_value = getattr(config, "model_id", None)
    if isinstance(config_value, str) and config_value:
        return config_value
    return "solar-pro3"


def _provider_endpoint_alias(provider: CitationDraftProvider) -> str:
    config = getattr(provider, "config", None)
    endpoint = getattr(config, "endpoint", None)
    if isinstance(endpoint, str) and endpoint:
        return endpoint.replace("https://", "").replace("http://", "")
    return "mock"


def _validate_result_rows_path(path: Path) -> None:
    if has_private_data_segment(path) and not is_repository_private_artifact_path(path):
        raise ValueError("private_data result rows must stay under repository private_data")
    if has_private_data_segment(path) and not is_repository_private_write_path(path):
        raise ValueError("private generation eval rows must be written under private_data")


def _format_query_type_summary_row(row) -> str:
    return (
        f"| {row.query_type} | {row.eval_count} | {row.answerable_count} | "
        f"{row.correct_with_evidence_rate:.6f} | "
        f"{row.citation_precision:.6f} | {row.citation_recall:.6f} | "
        f"{row.place_relevance:.6f} | {row.docent_usefulness:.6f} | "
        f"{row.spoken_answer_naturalness:.6f} | "
        f"{row.unsupported_claim_rate:.6f} | "
        f"{row.abstention_accuracy:.6f} | {row.latency_p95_ms:.6f} |"
    )


def main() -> int:
    args = _parse_args()
    report = run_solar_live_generation_smoke(
        report_path=args.report,
        result_rows_path=args.result_rows,
        dataset_path=args.dataset,
        chunks_path=args.chunks,
        answerable_limit=args.answerable_limit,
        no_answer_limit=args.no_answer_limit,
    )
    failures = collect_solar_live_generation_smoke_failures(report)
    print(
        "solar_live_generation_smoke "
        f"status={'PASS' if not failures else 'FAIL'} "
        f"eval_count={report.summary.eval_count} "
        f"correct_with_evidence={report.summary.correct_with_evidence_rate:.6f} "
        f"citation_precision={report.summary.citation_precision:.6f} "
        f"abstention_accuracy={report.summary.abstention_accuracy:.6f} "
        f"solar_call_count={report.summary.solar_call_count} "
        f"failures={len(failures)}",
    )
    return 0 if not failures else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run private retrieval-backed Solar Pro 3 live generation smoke.",
    )
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--result-rows", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS_PATH)
    parser.add_argument("--answerable-limit", type=int, default=2)
    parser.add_argument("--no-answer-limit", type=int, default=1)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
