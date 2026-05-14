from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.project_paths import project_path
from app.domain.retrieval import QueryType
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    measure_public_retrieval_artifact_quality,
)
from app.infrastructure.index.device import resolve_torch_device
from pipelines.run_place_story_generation_input_only_eval import (
    DEFAULT_MAX_CONTEXT_CHARS,
    _StrategyInputBundle,
    _build_strategy_input_bundle,
    _load_child_chunks_by_id,
)
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
from pipelines.run_solar_live_generation_smoke import (
    DEFAULT_CHUNKS_PATH,
    DEFAULT_DATASET_PATH,
    build_evidence_context,
)


SOLAR_GUARDED_BOOST_LIVE_DRY_RUN_REPORT_VERSION = (
    "solar-guarded-boost-live-dry-run/v1"
)
DEFAULT_REPORT_PATH = (
    Path("evals") / "reports" / "solar_guarded_boost_live_dry_run_report.md"
)
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "solar_guarded_boost_live_dry_run_rows.jsonl"
)
DEFAULT_LIVE_CALL_HARD_CAP = 20
ANSWER_CONTRACT_VERSION = "citation-rag-answer/v1"
ANSWER_POLICY_ID = "solar-guarded-boost-live-v1"
MODEL_ID = "solar-pro3"
PROVIDER_CONFIG_ID_ALIAS = "<solar-pro3-v1-live-config>"
ENDPOINT_ALIAS = "api.upstage.ai/v1/chat/completions"
SYSTEM_PROMPT_VERSION = "solar-pro3-citation-rag-draft-v1"

DryRunReuseDecision = Literal[
    "reuse_baseline_result",
    "candidate_live_call_required",
    "no_live_call_required",
]


class SolarGuardedBoostDryRunModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SolarGuardedBoostDryRunRow(SolarGuardedBoostDryRunModel):
    query_id: str = Field(min_length=1)
    query_type: QueryType
    split: str = Field(min_length=1)
    baseline_strategy_id: str = Field(min_length=1)
    candidate_strategy_id: str = Field(min_length=1)
    selected_strategy_id: str = Field(min_length=1)
    router_policy_id: str = Field(min_length=1)
    route_decision: str = Field(min_length=1)
    reuse_decision: DryRunReuseDecision
    baseline_input_fingerprint: str = Field(min_length=8)
    guarded_input_fingerprint: str = Field(min_length=8)
    input_fingerprint_equal: bool
    baseline_live_call_required: bool
    candidate_live_call_required: bool
    baseline_context_char_count: int = Field(ge=0)
    guarded_context_char_count: int = Field(ge=0)
    baseline_evidence_count: int = Field(ge=0)
    guarded_evidence_count: int = Field(ge=0)


class SolarGuardedBoostDryRunSummary(SolarGuardedBoostDryRunModel):
    query_count: int = Field(ge=0)
    baseline_live_call_count: int = Field(ge=0)
    candidate_live_call_count: int = Field(ge=0)
    expected_total_live_call_count: int = Field(ge=0)
    live_call_hard_cap: int = Field(ge=1)
    reused_candidate_count: int = Field(ge=0)
    changed_candidate_input_count: int = Field(ge=0)
    selected_candidate_count: int = Field(ge=0)
    guardrail_block_count: int = Field(ge=0)
    solar_call_count: int = Field(ge=0)
    hard_cap_exceeded: bool


class SolarGuardedBoostLiveDryRunReport(SolarGuardedBoostDryRunModel):
    report_version: str = SOLAR_GUARDED_BOOST_LIVE_DRY_RUN_REPORT_VERSION
    dry_run_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
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
    summary: SolarGuardedBoostDryRunSummary
    rows: tuple[SolarGuardedBoostDryRunRow, ...]
    reuse_decision_distribution: dict[str, int]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def run_solar_guarded_boost_live_dry_run(
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
    live_call_hard_cap: int = DEFAULT_LIVE_CALL_HARD_CAP,
) -> SolarGuardedBoostLiveDryRunReport:
    _validate_private_rows_path(result_rows_path, label="result")
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
    provisional = build_solar_guarded_boost_live_dry_run_report(
        baseline_bundles=baseline_bundles,
        candidate_bundles=candidate_bundles,
        top_k=top_k,
        candidate_k=candidate_k,
        max_context_chars=max_context_chars,
        live_call_hard_cap=live_call_hard_cap,
        child_chunks_by_id=child_chunks_by_id,
    )
    provisional_rows = build_public_solar_guarded_boost_live_dry_run_rows(provisional)
    provisional_text = build_solar_guarded_boost_live_dry_run_markdown(provisional)
    report = build_solar_guarded_boost_live_dry_run_report(
        baseline_bundles=baseline_bundles,
        candidate_bundles=candidate_bundles,
        top_k=top_k,
        candidate_k=candidate_k,
        max_context_chars=max_context_chars,
        live_call_hard_cap=live_call_hard_cap,
        child_chunks_by_id=child_chunks_by_id,
        result_rows=provisional_rows,
        report_text=provisional_text,
    )
    failures = collect_solar_guarded_boost_live_dry_run_failures(report)
    if failures:
        raise ValueError(f"solar guarded boost live dry-run gate failed: {failures}")

    _write_jsonl_rows(
        path=result_rows_path,
        rows=build_public_solar_guarded_boost_live_dry_run_rows(report),
    )
    resolved_report_path = project_path(report_path)
    resolved_report_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_report_path.write_text(
        build_solar_guarded_boost_live_dry_run_markdown(report),
        encoding="utf-8",
    )
    return report


def build_solar_guarded_boost_live_dry_run_report(
    *,
    baseline_bundles: tuple[_StrategyInputBundle, ...],
    candidate_bundles: tuple[_StrategyInputBundle, ...],
    top_k: int,
    candidate_k: int,
    max_context_chars: int,
    live_call_hard_cap: int,
    child_chunks_by_id: dict[str, Any],
    result_rows: list[dict[str, Any]] | None = None,
    report_text: str = "",
) -> SolarGuardedBoostLiveDryRunReport:
    baseline_by_query = _bundles_by_query_id(baseline_bundles)
    candidate_by_query = _bundles_by_query_id(candidate_bundles)
    baseline_records = _records_by_query_id(
        strategy_id=BASELINE_STRATEGY_ID,
        bundles=baseline_bundles,
    )
    candidate_records = _records_by_query_id(
        strategy_id=CANDIDATE_STRATEGY_ID,
        bundles=candidate_bundles,
    )
    route_rows = tuple(
        build_guarded_route_row(
            baseline_bundle=baseline_by_query[query_id],
            candidate_bundle=candidate_by_query[query_id],
            baseline_record=baseline_records[query_id],
            candidate_record=candidate_records[query_id],
        )
        for query_id in sorted(baseline_by_query)
    )
    rows = tuple(
        build_solar_guarded_boost_live_dry_run_row(
            baseline_bundle=baseline_by_query[route.query_id],
            candidate_bundle=candidate_by_query[route.query_id],
            selected_strategy_id=route.selected_strategy_id,
            route_decision=route.route_decision,
            child_chunks_by_id=child_chunks_by_id,
            max_context_chars=max_context_chars,
        )
        for route in route_rows
    )
    summary = build_solar_guarded_boost_live_dry_run_summary(
        rows=rows,
        live_call_hard_cap=live_call_hard_cap,
    )
    dry_run_id = _dry_run_id(rows=rows, summary=summary)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=SOLAR_GUARDED_BOOST_LIVE_DRY_RUN_REPORT_VERSION,
        run_id=dry_run_id,
        result_rows=result_rows or [],
        report_text=report_text,
    )
    report = SolarGuardedBoostLiveDryRunReport(
        dry_run_id=dry_run_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        dataset_path_alias="<private retrieval eval dataset: retrieval_eval_dev.jsonl>",
        chunks_path_alias="<private parent_child_chunks report>",
        baseline_strategy_id=BASELINE_STRATEGY_ID,
        candidate_strategy_id=CANDIDATE_STRATEGY_ID,
        guarded_strategy_id=GUARDED_BOOST_STRATEGY_ID,
        router_policy_id=ROUTER_POLICY_ID,
        answer_contract_version=ANSWER_CONTRACT_VERSION,
        answer_policy_id=ANSWER_POLICY_ID,
        provider_config_id_alias=PROVIDER_CONFIG_ID_ALIAS,
        endpoint_alias=ENDPOINT_ALIAS,
        model_id=MODEL_ID,
        top_k=top_k,
        candidate_k=candidate_k,
        max_context_chars=max_context_chars,
        resolved_device=resolve_torch_device("auto"),
        summary=summary,
        rows=rows,
        reuse_decision_distribution=dict(
            sorted(Counter(row.reuse_decision for row in rows).items()),
        ),
        output_quality=output_quality,
        qualitative_assessment={},
    )
    return report.model_copy(
        update={
            "qualitative_assessment": build_solar_guarded_boost_dry_run_assessment(
                report,
            ),
        },
    )


def build_solar_guarded_boost_live_dry_run_row(
    *,
    baseline_bundle: _StrategyInputBundle,
    candidate_bundle: _StrategyInputBundle,
    selected_strategy_id: str,
    route_decision: str,
    child_chunks_by_id: dict[str, Any],
    max_context_chars: int,
) -> SolarGuardedBoostDryRunRow:
    guarded_bundle = (
        candidate_bundle
        if selected_strategy_id == GUARDED_BOOST_STRATEGY_ID
        else baseline_bundle
    )
    baseline_request = build_dry_run_request_fingerprint(
        bundle=baseline_bundle,
        child_chunks_by_id=child_chunks_by_id,
        max_context_chars=max_context_chars,
    )
    guarded_request = build_dry_run_request_fingerprint(
        bundle=guarded_bundle,
        child_chunks_by_id=child_chunks_by_id,
        max_context_chars=max_context_chars,
    )
    baseline_call_required = _live_call_required(baseline_bundle)
    candidate_call_required = (
        baseline_call_required
        and selected_strategy_id == GUARDED_BOOST_STRATEGY_ID
        and baseline_request["input_fingerprint"] != guarded_request["input_fingerprint"]
    )
    reuse_decision = _reuse_decision(
        baseline_call_required=baseline_call_required,
        candidate_call_required=candidate_call_required,
        input_fingerprint_equal=(
            baseline_request["input_fingerprint"] == guarded_request["input_fingerprint"]
        ),
    )
    return SolarGuardedBoostDryRunRow(
        query_id=baseline_bundle.item.query.query_id,
        query_type=baseline_bundle.item.query.query_type,
        split=baseline_bundle.item.metadata.split,
        baseline_strategy_id=BASELINE_STRATEGY_ID,
        candidate_strategy_id=CANDIDATE_STRATEGY_ID,
        selected_strategy_id=selected_strategy_id,
        router_policy_id=ROUTER_POLICY_ID,
        route_decision=route_decision,
        reuse_decision=reuse_decision,
        baseline_input_fingerprint=baseline_request["input_fingerprint"],
        guarded_input_fingerprint=guarded_request["input_fingerprint"],
        input_fingerprint_equal=(
            baseline_request["input_fingerprint"] == guarded_request["input_fingerprint"]
        ),
        baseline_live_call_required=baseline_call_required,
        candidate_live_call_required=candidate_call_required,
        baseline_context_char_count=int(baseline_request["context_char_count"]),
        guarded_context_char_count=int(guarded_request["context_char_count"]),
        baseline_evidence_count=len(baseline_bundle.evidence_pack.evidence),
        guarded_evidence_count=len(guarded_bundle.evidence_pack.evidence),
    )


def build_dry_run_request_fingerprint(
    *,
    bundle: _StrategyInputBundle,
    child_chunks_by_id: dict[str, Any],
    max_context_chars: int,
) -> dict[str, str | int]:
    evidence_context = build_evidence_context(
        retrieval=type(
            "_DryRunRetrieval",
            (),
            {"evidence_pack": bundle.evidence_pack},
        )(),
        child_chunks_by_id=child_chunks_by_id,
        max_chars=max_context_chars,
    )
    payload = {
        "answer_contract_version": ANSWER_CONTRACT_VERSION,
        "answer_policy_id": ANSWER_POLICY_ID,
        "system_prompt_version": SYSTEM_PROMPT_VERSION,
        "model_id": MODEL_ID,
        "query_id": bundle.item.query.query_id,
        "query_type": bundle.item.query.query_type,
        "query_text": bundle.item.query.query_text,
        "evidence_context": evidence_context,
        "place_ids": tuple(bundle.item.metadata.place_ids),
        "language": bundle.item.query.language,
        "max_context_chars": max_context_chars,
    }
    return {
        "input_fingerprint": _stable_digest(payload, length=16),
        "context_char_count": len(evidence_context),
    }


def build_solar_guarded_boost_live_dry_run_summary(
    *,
    rows: tuple[SolarGuardedBoostDryRunRow, ...],
    live_call_hard_cap: int,
) -> SolarGuardedBoostDryRunSummary:
    baseline_live_call_count = sum(1 for row in rows if row.baseline_live_call_required)
    candidate_live_call_count = sum(1 for row in rows if row.candidate_live_call_required)
    expected_total = baseline_live_call_count + candidate_live_call_count
    return SolarGuardedBoostDryRunSummary(
        query_count=len(rows),
        baseline_live_call_count=baseline_live_call_count,
        candidate_live_call_count=candidate_live_call_count,
        expected_total_live_call_count=expected_total,
        live_call_hard_cap=live_call_hard_cap,
        reused_candidate_count=sum(
            1 for row in rows if row.reuse_decision == "reuse_baseline_result"
        ),
        changed_candidate_input_count=sum(
            1 for row in rows if not row.input_fingerprint_equal
        ),
        selected_candidate_count=sum(
            1 for row in rows if row.selected_strategy_id == GUARDED_BOOST_STRATEGY_ID
        ),
        guardrail_block_count=sum(
            1 for row in rows if row.selected_strategy_id == BASELINE_STRATEGY_ID
        ),
        solar_call_count=0,
        hard_cap_exceeded=expected_total > live_call_hard_cap,
    )


def build_public_solar_guarded_boost_live_dry_run_rows(
    report: SolarGuardedBoostLiveDryRunReport,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "dry_run_id": report.dry_run_id,
            "row_type": "summary",
            "query_count": report.summary.query_count,
            "baseline_live_call_count": report.summary.baseline_live_call_count,
            "candidate_live_call_count": report.summary.candidate_live_call_count,
            "expected_total_live_call_count": (
                report.summary.expected_total_live_call_count
            ),
            "live_call_hard_cap": report.summary.live_call_hard_cap,
            "reused_candidate_count": report.summary.reused_candidate_count,
            "changed_candidate_input_count": report.summary.changed_candidate_input_count,
            "selected_candidate_count": report.summary.selected_candidate_count,
            "guardrail_block_count": report.summary.guardrail_block_count,
            "solar_call_count": report.summary.solar_call_count,
            "hard_cap_exceeded": report.summary.hard_cap_exceeded,
        },
    ]
    rows.extend(
        {
            "dry_run_id": report.dry_run_id,
            "row_type": "query_dry_run",
            "query_id": row.query_id,
            "query_type": row.query_type,
            "split": row.split,
            "baseline_strategy_id": row.baseline_strategy_id,
            "candidate_strategy_id": row.candidate_strategy_id,
            "selected_strategy_id": row.selected_strategy_id,
            "router_policy_id": row.router_policy_id,
            "route_decision": row.route_decision,
            "reuse_decision": row.reuse_decision,
            "baseline_input_fingerprint": row.baseline_input_fingerprint,
            "guarded_input_fingerprint": row.guarded_input_fingerprint,
            "input_fingerprint_equal": row.input_fingerprint_equal,
            "baseline_live_call_required": row.baseline_live_call_required,
            "candidate_live_call_required": row.candidate_live_call_required,
            "baseline_context_char_count": row.baseline_context_char_count,
            "guarded_context_char_count": row.guarded_context_char_count,
            "baseline_evidence_count": row.baseline_evidence_count,
            "guarded_evidence_count": row.guarded_evidence_count,
        }
        for row in report.rows
    )
    return rows


def collect_solar_guarded_boost_live_dry_run_failures(
    report: SolarGuardedBoostLiveDryRunReport,
) -> list[str]:
    failures: list[str] = []
    if not report.rows:
        failures.append("empty_dry_run_rows")
    if report.summary.solar_call_count != 0:
        failures.append("solar_call_count_must_be_zero")
    if report.summary.hard_cap_exceeded:
        failures.append("live_call_hard_cap_exceeded")
    if report.summary.candidate_live_call_count == 0:
        failures.append("candidate_live_call_count_zero")
    if report.summary.expected_total_live_call_count > report.summary.live_call_hard_cap:
        failures.append("expected_total_live_call_over_cap")
    if report.output_quality.public_raw_text_leakage_count:
        failures.append("public_raw_text_leakage")
    if report.output_quality.private_path_leakage_count:
        failures.append("private_path_leakage")
    if report.output_quality.secret_like_leakage_count:
        failures.append("secret_like_leakage")
    if report.output_quality.forbidden_result_field_count:
        failures.append("forbidden_public_result_fields")
    return failures


def build_solar_guarded_boost_live_dry_run_markdown(
    report: SolarGuardedBoostLiveDryRunReport,
) -> str:
    summary = report.summary
    quality = report.output_quality
    query_rows = "\n".join(_format_dry_run_query_row(row) for row in report.rows)
    reuse_rows = "\n".join(
        f"| `{decision}` | {count} |"
        for decision, count in report.reuse_decision_distribution.items()
    )
    qualitative_rows = "\n".join(
        f"- `{key}`: {value}" for key, value in report.qualitative_assessment.items()
    )
    return f"""# Solar Pro 3 Guarded Boost Live Dry-run Report

## 목적

`parent_doc_context_boost_guarded`를 Solar Pro 3 live paired comparison에 넣기 전에 input fingerprint, reuse 대상, 예상 live call 수, public-safe gate를 검증한다.

이 문서는 dry-run 결과다. Solar Pro 3 live 호출은 수행하지 않았고 raw query, raw evidence, prompt, answer text는 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| dry_run_id | `{report.dry_run_id}` |
| generated_at_utc | `{report.generated_at_utc}` |
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

## 정량 리포트

| metric | value |
| --- | ---: |
| query_count | {summary.query_count} |
| baseline_live_call_count | {summary.baseline_live_call_count} |
| candidate_live_call_count | {summary.candidate_live_call_count} |
| expected_total_live_call_count | {summary.expected_total_live_call_count} |
| live_call_hard_cap | {summary.live_call_hard_cap} |
| reused_candidate_count | {summary.reused_candidate_count} |
| changed_candidate_input_count | {summary.changed_candidate_input_count} |
| selected_candidate_count | {summary.selected_candidate_count} |
| guardrail_block_count | {summary.guardrail_block_count} |
| solar_call_count | {summary.solar_call_count} |
| hard_cap_exceeded | {summary.hard_cap_exceeded} |

## Reuse Decision Distribution

| reuse_decision | count |
| --- | ---: |
{reuse_rows}

## Query-level Sanitized Dry-run

| query_id | decision | selected_strategy | reuse_decision | fingerprint_equal | baseline_call | candidate_call | baseline_chars | guarded_chars | baseline_evidence | guarded_evidence |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
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

{_dry_run_conclusion(report)}
"""


def build_solar_guarded_boost_dry_run_assessment(
    report: SolarGuardedBoostLiveDryRunReport,
) -> dict[str, str]:
    return {
        "comparison_scope": (
            "private place_story dev query에서 baseline과 guarded retrieval input을 비교했다."
        ),
        "llm_call_boundary": (
            "dry-run 단계라 Solar Pro 3 live 호출은 수행하지 않았고 solar_call_count는 0이다."
        ),
        "reuse_policy": (
            "baseline과 guarded input fingerprint가 동일한 query는 live 실행 시 baseline generation 결과를 재사용한다."
        ),
        "call_budget": (
            f"expected_total_live_call_count={report.summary.expected_total_live_call_count}, "
            f"hard_cap={report.summary.live_call_hard_cap}로 제한한다."
        ),
        "data_mart_grain": (
            "`fact_solar_guarded_boost_live_eval`의 grain은 run-query-strategy-answer_contract-router_policy다."
        ),
        "security_boundary": (
            "public artifact에는 raw query, raw evidence, prompt, answer text, private path, secret을 기록하지 않는다."
        ),
        "next_action": _next_action(report),
    }


def _reuse_decision(
    *,
    baseline_call_required: bool,
    candidate_call_required: bool,
    input_fingerprint_equal: bool,
) -> DryRunReuseDecision:
    if not baseline_call_required:
        return "no_live_call_required"
    if candidate_call_required:
        return "candidate_live_call_required"
    if input_fingerprint_equal:
        return "reuse_baseline_result"
    return "no_live_call_required"


def _live_call_required(bundle: _StrategyInputBundle) -> bool:
    return (
        bundle.item.query.expected_behavior != "abstain"
        and bool(bundle.evidence_pack.evidence)
        and bundle.input_stats.context_buildable
    )


def _bundles_by_query_id(
    bundles: tuple[_StrategyInputBundle, ...],
) -> dict[str, _StrategyInputBundle]:
    return {bundle.item.query.query_id: bundle for bundle in bundles}


def _stable_digest(payload: Any, *, length: int = 12) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"),
    ).hexdigest()[:length]


def _dry_run_id(
    *,
    rows: tuple[SolarGuardedBoostDryRunRow, ...],
    summary: SolarGuardedBoostDryRunSummary,
) -> str:
    payload = {
        "rows": [row.model_dump(mode="json") for row in rows],
        "summary": summary.model_dump(mode="json"),
    }
    digest = _stable_digest(payload, length=8)
    return f"solar-guarded-boost-dry-q{summary.query_count}-{digest}"


def _format_dry_run_query_row(row: SolarGuardedBoostDryRunRow) -> str:
    return (
        f"| `{row.query_id}` | `{row.route_decision}` | "
        f"`{row.selected_strategy_id}` | `{row.reuse_decision}` | "
        f"{row.input_fingerprint_equal} | "
        f"{row.baseline_live_call_required} | {row.candidate_live_call_required} | "
        f"{row.baseline_context_char_count} | {row.guarded_context_char_count} | "
        f"{row.baseline_evidence_count} | {row.guarded_evidence_count} |"
    )


def _next_action(report: SolarGuardedBoostLiveDryRunReport) -> str:
    failures = collect_solar_guarded_boost_live_dry_run_failures(report)
    if failures:
        return "dry-run failure를 먼저 수정한 뒤 live 실행 승인 여부를 다시 판단한다."
    return "별도 승인 후 Solar Pro 3 guarded boost live paired comparison runner를 구현하거나 실행한다."


def _dry_run_conclusion(report: SolarGuardedBoostLiveDryRunReport) -> str:
    failures = collect_solar_guarded_boost_live_dry_run_failures(report)
    if failures:
        return (
            f"dry-run gate가 실패했다: {', '.join(failures)}.\n\n"
            "Solar Pro 3 live 호출로 넘어가면 안 된다."
        )
    return (
        "dry-run gate를 통과했다.\n\n"
        "이 결과는 live 품질 개선 주장이 아니라, live paired comparison 실행 전 input reuse와 call budget이 계획 범위 안에 있다는 검증이다."
    )


def main() -> int:
    args = _parse_args()
    report = run_solar_guarded_boost_live_dry_run(
        chunks_path=args.chunks,
        dataset_path=args.dataset,
        place_catalog_path=args.place_catalog,
        embedding_cache_dir=args.embedding_cache_dir,
        report_path=args.report,
        result_rows_path=args.result_rows,
        top_k=args.top_k,
        candidate_k=args.candidate_k,
        max_context_chars=args.max_context_chars,
        live_call_hard_cap=args.live_call_hard_cap,
    )
    failures = collect_solar_guarded_boost_live_dry_run_failures(report)
    print(
        "solar_guarded_boost_live_dry_run "
        f"status={'PASS' if not failures else 'FAIL'} "
        f"expected_calls={report.summary.expected_total_live_call_count} "
        f"candidate_calls={report.summary.candidate_live_call_count} "
        f"reused={report.summary.reused_candidate_count} "
        f"device={report.resolved_device} "
        f"solar_calls={report.summary.solar_call_count} "
        f"failures={len(failures)}",
    )
    return 0 if not failures else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Solar Pro 3 guarded boost live comparison dry-run.",
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
    parser.add_argument("--live-call-hard-cap", type=int, default=DEFAULT_LIVE_CALL_HARD_CAP)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
