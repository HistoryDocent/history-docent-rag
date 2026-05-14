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
from app.domain.retrieval import (
    RetrievalEvalItem,
    build_retrieval_target_inventory,
    collect_retrieval_eval_target_resolvability_failures,
    load_retrieval_eval_jsonl,
    summarize_retrieval_eval_target_resolvability,
)
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    measure_public_retrieval_artifact_quality,
)
from app.infrastructure.index.device import resolve_torch_device
from pipelines.run_place_story_generation_input_only_eval import (
    DEFAULT_MAX_CONTEXT_CHARS,
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
    _validate_private_rows_path,
    _write_jsonl_rows,
)
from pipelines.run_solar_guarded_boost_live_dry_run import (
    ANSWER_CONTRACT_VERSION,
    ANSWER_POLICY_ID,
    ENDPOINT_ALIAS,
    MODEL_ID,
    PROVIDER_CONFIG_ID_ALIAS,
    SolarGuardedBoostDryRunRow,
    build_public_solar_guarded_boost_live_dry_run_rows,
    build_solar_guarded_boost_live_dry_run_row,
)
from pipelines.run_solar_live_generation_smoke import DEFAULT_CHUNKS_PATH


SOLAR_GUARDED_BOOST_LOCKED_TEST_READINESS_REPORT_VERSION = (
    "solar-guarded-boost-locked-test-readiness/v1"
)
DEFAULT_DATASET_PATH = Path("private_data") / "evals" / "datasets" / "retrieval_eval_test.jsonl"
DEFAULT_REPORT_PATH = (
    Path("evals") / "reports" / "solar_guarded_boost_locked_test_readiness_report.md"
)
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "solar_guarded_boost_locked_test_readiness_rows.jsonl"
)
DEFAULT_LIVE_CALL_HARD_CAP = 20
EXPECTED_LOCKED_PLACE_STORY_QUERY_COUNT = 5

ReadinessDecision = Literal[
    "ready_for_live_execution_approval",
    "ready_without_candidate_live_call",
    "blocked_by_readiness_gate",
]


class SolarGuardedBoostLockedReadinessModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SolarGuardedBoostLockedReadinessSummary(
    SolarGuardedBoostLockedReadinessModel,
):
    expected_query_count: int = Field(ge=1)
    locked_place_story_query_count: int = Field(ge=0)
    route_decision_computed_count: int = Field(ge=0)
    selected_candidate_count: int = Field(ge=0)
    guardrail_block_count: int = Field(ge=0)
    manual_review_count: int = Field(ge=0)
    baseline_live_call_count: int = Field(ge=0)
    candidate_live_call_count: int = Field(ge=0)
    expected_total_live_call_count: int = Field(ge=0)
    live_call_hard_cap: int = Field(ge=1)
    reused_candidate_count: int = Field(ge=0)
    changed_candidate_input_count: int = Field(ge=0)
    citation_recoverability_min: float = Field(ge=0.0, le=1.0)
    target_resolvability_fail_count: int = Field(ge=0)
    missing_child_target_count: int = Field(ge=0)
    missing_parent_target_count: int = Field(ge=0)
    missing_doc_target_count: int = Field(ge=0)
    public_raw_text_leakage_count: int = Field(ge=0)
    private_path_leakage_count: int = Field(ge=0)
    secret_like_leakage_count: int = Field(ge=0)
    solar_call_count: int = Field(ge=0)
    live_execution_requested: bool
    live_execution_confirmed: bool
    hard_cap_exceeded: bool
    readiness_decision: ReadinessDecision


class SolarGuardedBoostLockedReadinessReport(
    SolarGuardedBoostLockedReadinessModel,
):
    report_version: str = SOLAR_GUARDED_BOOST_LOCKED_TEST_READINESS_REPORT_VERSION
    readiness_id: str = Field(min_length=1)
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
    summary: SolarGuardedBoostLockedReadinessSummary
    rows: tuple[SolarGuardedBoostDryRunRow, ...]
    route_decision_distribution: dict[str, int]
    reuse_decision_distribution: dict[str, int]
    output_quality: PublicRetrievalArtifactQuality
    qualitative_assessment: dict[str, str]


def run_solar_guarded_boost_locked_test_readiness(
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
    expected_query_count: int = EXPECTED_LOCKED_PLACE_STORY_QUERY_COUNT,
) -> SolarGuardedBoostLockedReadinessReport:
    _validate_private_rows_path(result_rows_path, label="result")
    items = _load_place_story_locked_test_items(dataset_path=dataset_path)
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
    target_failures = collect_retrieval_eval_target_resolvability_failures(
        summarize_retrieval_eval_target_resolvability(
            items=items,
            inventory=build_retrieval_target_inventory(list(child_chunks_by_id.values())),
        ),
    )
    target_summary = summarize_retrieval_eval_target_resolvability(
        items=items,
        inventory=build_retrieval_target_inventory(list(child_chunks_by_id.values())),
    )
    provisional = build_solar_guarded_boost_locked_test_readiness_report(
        baseline_bundles=baseline_bundles,
        candidate_bundles=candidate_bundles,
        target_summary=target_summary,
        target_failure_count=len(target_failures),
        top_k=top_k,
        candidate_k=candidate_k,
        max_context_chars=max_context_chars,
        live_call_hard_cap=live_call_hard_cap,
        expected_query_count=expected_query_count,
        child_chunks_by_id=child_chunks_by_id,
    )
    provisional_rows = build_public_solar_guarded_boost_locked_readiness_rows(
        provisional,
    )
    provisional_text = build_solar_guarded_boost_locked_readiness_markdown(provisional)
    report = build_solar_guarded_boost_locked_test_readiness_report(
        baseline_bundles=baseline_bundles,
        candidate_bundles=candidate_bundles,
        target_summary=target_summary,
        target_failure_count=len(target_failures),
        top_k=top_k,
        candidate_k=candidate_k,
        max_context_chars=max_context_chars,
        live_call_hard_cap=live_call_hard_cap,
        expected_query_count=expected_query_count,
        child_chunks_by_id=child_chunks_by_id,
        result_rows=provisional_rows,
        report_text=provisional_text,
    )
    failures = collect_solar_guarded_boost_locked_readiness_failures(report)
    if failures:
        raise ValueError(f"solar guarded boost locked readiness gate failed: {failures}")

    _write_jsonl_rows(
        path=result_rows_path,
        rows=build_public_solar_guarded_boost_locked_readiness_rows(report),
    )
    resolved_report_path = project_path(report_path)
    resolved_report_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_report_path.write_text(
        build_solar_guarded_boost_locked_readiness_markdown(report),
        encoding="utf-8",
    )
    return report


def build_solar_guarded_boost_locked_test_readiness_report(
    *,
    baseline_bundles: tuple[Any, ...],
    candidate_bundles: tuple[Any, ...],
    target_summary: Any,
    target_failure_count: int,
    top_k: int,
    candidate_k: int,
    max_context_chars: int,
    live_call_hard_cap: int,
    expected_query_count: int,
    child_chunks_by_id: dict[str, Any],
    result_rows: list[dict[str, Any]] | None = None,
    report_text: str = "",
) -> SolarGuardedBoostLockedReadinessReport:
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
    summary = build_solar_guarded_boost_locked_readiness_summary(
        rows=rows,
        baseline_bundles=baseline_bundles,
        candidate_bundles=candidate_bundles,
        expected_query_count=expected_query_count,
        live_call_hard_cap=live_call_hard_cap,
        target_summary=target_summary,
        target_failure_count=target_failure_count,
    )
    readiness_id = _readiness_id(rows=rows, summary=summary)
    output_quality = measure_public_retrieval_artifact_quality(
        report_version=SOLAR_GUARDED_BOOST_LOCKED_TEST_READINESS_REPORT_VERSION,
        run_id=readiness_id,
        result_rows=result_rows or [],
        report_text=report_text,
    )
    summary = summary.model_copy(
        update={
            "public_raw_text_leakage_count": output_quality.public_raw_text_leakage_count,
            "private_path_leakage_count": output_quality.private_path_leakage_count,
            "secret_like_leakage_count": output_quality.secret_like_leakage_count,
            "readiness_decision": _readiness_decision(
                summary=summary,
                output_quality=output_quality,
            ),
        },
    )
    report = SolarGuardedBoostLockedReadinessReport(
        readiness_id=readiness_id,
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        dataset_path_alias="<private retrieval eval dataset: retrieval_eval_test.jsonl>",
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
        route_decision_distribution=dict(
            sorted(Counter(row.route_decision for row in rows).items()),
        ),
        reuse_decision_distribution=dict(
            sorted(Counter(row.reuse_decision for row in rows).items()),
        ),
        output_quality=output_quality,
        qualitative_assessment={},
    )
    return report.model_copy(
        update={
            "qualitative_assessment": build_solar_guarded_boost_locked_assessment(
                report,
            ),
        },
    )


def build_solar_guarded_boost_locked_readiness_summary(
    *,
    rows: tuple[SolarGuardedBoostDryRunRow, ...],
    baseline_bundles: tuple[Any, ...],
    candidate_bundles: tuple[Any, ...],
    expected_query_count: int,
    live_call_hard_cap: int,
    target_summary: Any,
    target_failure_count: int,
) -> SolarGuardedBoostLockedReadinessSummary:
    baseline_live_call_count = sum(1 for row in rows if row.baseline_live_call_required)
    candidate_live_call_count = sum(1 for row in rows if row.candidate_live_call_required)
    expected_total = baseline_live_call_count + candidate_live_call_count
    selected_recoverability = [
        _bundle_citation_recoverability(
            candidate_bundles[index]
            if row.selected_strategy_id == GUARDED_BOOST_STRATEGY_ID
            else baseline_bundles[index],
        )
        for index, row in enumerate(rows)
    ]
    provisional_summary = SolarGuardedBoostLockedReadinessSummary(
        expected_query_count=expected_query_count,
        locked_place_story_query_count=len(rows),
        route_decision_computed_count=len(rows),
        selected_candidate_count=sum(
            1 for row in rows if row.selected_strategy_id == GUARDED_BOOST_STRATEGY_ID
        ),
        guardrail_block_count=sum(
            1 for row in rows if row.selected_strategy_id == BASELINE_STRATEGY_ID
        ),
        manual_review_count=sum(
            1 for row in rows if row.route_decision == "manual_review_required"
        ),
        baseline_live_call_count=baseline_live_call_count,
        candidate_live_call_count=candidate_live_call_count,
        expected_total_live_call_count=expected_total,
        live_call_hard_cap=live_call_hard_cap,
        reused_candidate_count=sum(
            1 for row in rows if row.reuse_decision == "reuse_baseline_result"
        ),
        changed_candidate_input_count=sum(1 for row in rows if not row.input_fingerprint_equal),
        citation_recoverability_min=(
            min(selected_recoverability) if selected_recoverability else 0.0
        ),
        target_resolvability_fail_count=target_failure_count,
        missing_child_target_count=target_summary.missing_child_target_count,
        missing_parent_target_count=target_summary.missing_parent_target_count,
        missing_doc_target_count=target_summary.missing_doc_target_count,
        public_raw_text_leakage_count=0,
        private_path_leakage_count=0,
        secret_like_leakage_count=0,
        solar_call_count=0,
        live_execution_requested=False,
        live_execution_confirmed=False,
        hard_cap_exceeded=expected_total > live_call_hard_cap,
        readiness_decision="blocked_by_readiness_gate",
    )
    return provisional_summary.model_copy(
        update={
            "readiness_decision": _readiness_decision(
                summary=provisional_summary,
                output_quality=None,
            ),
        },
    )


def build_public_solar_guarded_boost_locked_readiness_rows(
    report: SolarGuardedBoostLockedReadinessReport,
) -> list[dict[str, Any]]:
    rows = [
        {
            "readiness_id": report.readiness_id,
            "row_type": "summary",
            "locked_place_story_query_count": (report.summary.locked_place_story_query_count),
            "route_decision_computed_count": (report.summary.route_decision_computed_count),
            "selected_candidate_count": report.summary.selected_candidate_count,
            "guardrail_block_count": report.summary.guardrail_block_count,
            "manual_review_count": report.summary.manual_review_count,
            "baseline_live_call_count": report.summary.baseline_live_call_count,
            "candidate_live_call_count": report.summary.candidate_live_call_count,
            "expected_total_live_call_count": (report.summary.expected_total_live_call_count),
            "live_call_hard_cap": report.summary.live_call_hard_cap,
            "citation_recoverability_min": report.summary.citation_recoverability_min,
            "target_resolvability_fail_count": (report.summary.target_resolvability_fail_count),
            "solar_call_count": report.summary.solar_call_count,
            "live_execution_requested": report.summary.live_execution_requested,
            "live_execution_confirmed": report.summary.live_execution_confirmed,
            "hard_cap_exceeded": report.summary.hard_cap_exceeded,
            "readiness_decision": report.summary.readiness_decision,
        },
    ]
    rows.extend(
        {
            **row,
            "readiness_id": report.readiness_id,
            "row_type": (
                "query_locked_readiness" if row["row_type"] == "query_dry_run" else row["row_type"]
            ),
        }
        for row in build_public_solar_guarded_boost_live_dry_run_rows(
            _as_live_dry_run_compatible_report(report),
        )
        if row["row_type"] == "query_dry_run"
    )
    return rows


def collect_solar_guarded_boost_locked_readiness_failures(
    report: SolarGuardedBoostLockedReadinessReport,
) -> list[str]:
    summary = report.summary
    failures: list[str] = []
    if not report.rows:
        failures.append("empty_locked_readiness_rows")
    if summary.locked_place_story_query_count != summary.expected_query_count:
        failures.append("locked_place_story_query_count_mismatch")
    if summary.route_decision_computed_count != summary.locked_place_story_query_count:
        failures.append("route_decision_count_mismatch")
    if summary.solar_call_count != 0:
        failures.append("solar_call_count_must_be_zero")
    if summary.live_execution_requested or summary.live_execution_confirmed:
        failures.append("live_execution_must_remain_blocked")
    if summary.hard_cap_exceeded:
        failures.append("live_call_hard_cap_exceeded")
    if summary.expected_total_live_call_count > summary.live_call_hard_cap:
        failures.append("expected_total_live_call_over_cap")
    if summary.target_resolvability_fail_count:
        failures.append("target_resolvability_failed")
    if summary.citation_recoverability_min < 0.99:
        failures.append("citation_recoverability_below_threshold")
    if report.output_quality.public_raw_text_leakage_count:
        failures.append("public_raw_text_leakage")
    if report.output_quality.private_path_leakage_count:
        failures.append("private_path_leakage")
    if report.output_quality.secret_like_leakage_count:
        failures.append("secret_like_leakage")
    if report.output_quality.forbidden_result_field_count:
        failures.append("forbidden_public_result_fields")
    return failures


def build_solar_guarded_boost_locked_readiness_markdown(
    report: SolarGuardedBoostLockedReadinessReport,
) -> str:
    summary = report.summary
    quality = report.output_quality
    route_rows = "\n".join(
        f"| `{decision}` | {count} |"
        for decision, count in report.route_decision_distribution.items()
    )
    reuse_rows = "\n".join(
        f"| `{decision}` | {count} |"
        for decision, count in report.reuse_decision_distribution.items()
    )
    query_rows = "\n".join(_format_locked_readiness_query_row(row) for row in report.rows)
    qualitative_rows = "\n".join(
        f"- `{key}`: {value}" for key, value in report.qualitative_assessment.items()
    )
    return f"""# Solar Pro 3 Guarded Boost Locked Test Readiness Report

## 목적

`place_story_guarded_boost_v1`을 locked test live paired comparison에 넣기 전에 split, route decision, expected live call budget, target resolvability, public-safe gate를 검증한다.

이 문서는 readiness dry-run 결과다. Solar Pro 3 live 호출은 수행하지 않았고 raw query, raw evidence, prompt, answer text는 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `{report.report_version}` |
| readiness_id | `{report.readiness_id}` |
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
| expected_query_count | {summary.expected_query_count} |
| locked_place_story_query_count | {summary.locked_place_story_query_count} |
| route_decision_computed_count | {summary.route_decision_computed_count} |
| selected_candidate_count | {summary.selected_candidate_count} |
| guardrail_block_count | {summary.guardrail_block_count} |
| manual_review_count | {summary.manual_review_count} |
| baseline_live_call_count | {summary.baseline_live_call_count} |
| candidate_live_call_count | {summary.candidate_live_call_count} |
| expected_total_live_call_count | {summary.expected_total_live_call_count} |
| live_call_hard_cap | {summary.live_call_hard_cap} |
| reused_candidate_count | {summary.reused_candidate_count} |
| changed_candidate_input_count | {summary.changed_candidate_input_count} |
| citation_recoverability_min | {summary.citation_recoverability_min:.6f} |
| target_resolvability_fail_count | {summary.target_resolvability_fail_count} |
| missing_child_target_count | {summary.missing_child_target_count} |
| missing_parent_target_count | {summary.missing_parent_target_count} |
| missing_doc_target_count | {summary.missing_doc_target_count} |
| solar_call_count | {summary.solar_call_count} |
| live_execution_requested | {summary.live_execution_requested} |
| live_execution_confirmed | {summary.live_execution_confirmed} |
| hard_cap_exceeded | {summary.hard_cap_exceeded} |
| readiness_decision | `{summary.readiness_decision}` |

## Route Decision Distribution

| route_decision | count |
| --- | ---: |
{route_rows}

## Reuse Decision Distribution

| reuse_decision | count |
| --- | ---: |
{reuse_rows}

## Query-level Sanitized Readiness

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

{_locked_readiness_conclusion(report)}
"""


def build_solar_guarded_boost_locked_assessment(
    report: SolarGuardedBoostLockedReadinessReport,
) -> dict[str, str]:
    return {
        "comparison_scope": (
            "private locked place_story test subset에서 baseline과 guarded retrieval input을 비교했다."
        ),
        "llm_call_boundary": (
            "readiness dry-run 단계라 Solar Pro 3 live 호출은 수행하지 않았고 solar_call_count는 0이다."
        ),
        "test_split_boundary": (
            "locked test는 live 품질 평가가 아니라 route와 call budget readiness 확인에만 사용했다."
        ),
        "call_budget": (
            f"expected_total_live_call_count={report.summary.expected_total_live_call_count}, "
            f"hard_cap={report.summary.live_call_hard_cap}로 제한한다."
        ),
        "data_mart_grain": (
            "`fact_guarded_boost_locked_readiness`의 grain은 run_id-query_id-router_policy_id-execution_mode다."
        ),
        "security_boundary": (
            "public artifact에는 raw query, raw evidence, prompt, answer text, private path, secret을 기록하지 않는다."
        ),
        "next_action": _next_action(report),
    }


def _load_place_story_locked_test_items(*, dataset_path: Path) -> list[RetrievalEvalItem]:
    items = load_retrieval_eval_jsonl(project_path(dataset_path))
    selected = [
        item
        for item in items
        if item.query.query_type == "place_story"
        and item.metadata.split == "test"
        and item.metadata.review_status == "locked"
    ]
    if not selected:
        raise ValueError("guarded boost locked readiness requires locked test rows")
    return selected


def _bundles_by_query_id(bundles: tuple[Any, ...]) -> dict[str, Any]:
    return {bundle.item.query.query_id: bundle for bundle in bundles}


def _bundle_citation_recoverability(bundle: Any) -> float:
    evidence = tuple(bundle.evidence_pack.evidence)
    if not evidence:
        return 0.0
    return round(
        sum(1 for item in evidence if item.citation_recoverable) / len(evidence),
        6,
    )


def _readiness_decision(
    *,
    summary: SolarGuardedBoostLockedReadinessSummary,
    output_quality: PublicRetrievalArtifactQuality | None,
) -> ReadinessDecision:
    output_blocked = output_quality is not None and (
        output_quality.public_raw_text_leakage_count
        or output_quality.private_path_leakage_count
        or output_quality.secret_like_leakage_count
        or output_quality.forbidden_result_field_count
    )
    gate_blocked = (
        summary.locked_place_story_query_count != summary.expected_query_count
        or summary.route_decision_computed_count != summary.locked_place_story_query_count
        or summary.solar_call_count != 0
        or summary.live_execution_requested
        or summary.live_execution_confirmed
        or summary.hard_cap_exceeded
        or summary.target_resolvability_fail_count > 0
        or summary.citation_recoverability_min < 0.99
        or output_blocked
    )
    if gate_blocked:
        return "blocked_by_readiness_gate"
    if summary.candidate_live_call_count == 0:
        return "ready_without_candidate_live_call"
    return "ready_for_live_execution_approval"


def _readiness_id(
    *,
    rows: tuple[SolarGuardedBoostDryRunRow, ...],
    summary: SolarGuardedBoostLockedReadinessSummary,
) -> str:
    payload = {
        "rows": [row.model_dump(mode="json") for row in rows],
        "summary": summary.model_dump(mode="json"),
    }
    digest = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"),
    ).hexdigest()[:8]
    return f"solar-guarded-boost-locked-ready-q{summary.locked_place_story_query_count}-{digest}"


def _as_live_dry_run_compatible_report(
    report: SolarGuardedBoostLockedReadinessReport,
) -> Any:
    return type(
        "_LiveDryRunCompatibleReport",
        (),
        {
            "dry_run_id": report.readiness_id,
            "rows": report.rows,
            "summary": type(
                "_LiveDryRunCompatibleSummary",
                (),
                {
                    "query_count": report.summary.locked_place_story_query_count,
                    "baseline_live_call_count": report.summary.baseline_live_call_count,
                    "candidate_live_call_count": report.summary.candidate_live_call_count,
                    "expected_total_live_call_count": (
                        report.summary.expected_total_live_call_count
                    ),
                    "live_call_hard_cap": report.summary.live_call_hard_cap,
                    "reused_candidate_count": report.summary.reused_candidate_count,
                    "changed_candidate_input_count": (report.summary.changed_candidate_input_count),
                    "selected_candidate_count": report.summary.selected_candidate_count,
                    "guardrail_block_count": report.summary.guardrail_block_count,
                    "solar_call_count": report.summary.solar_call_count,
                    "hard_cap_exceeded": report.summary.hard_cap_exceeded,
                },
            )(),
        },
    )()


def _format_locked_readiness_query_row(row: SolarGuardedBoostDryRunRow) -> str:
    return (
        f"| `{row.query_id}` | `{row.route_decision}` | "
        f"`{row.selected_strategy_id}` | `{row.reuse_decision}` | "
        f"{row.input_fingerprint_equal} | "
        f"{row.baseline_live_call_required} | {row.candidate_live_call_required} | "
        f"{row.baseline_context_char_count} | {row.guarded_context_char_count} | "
        f"{row.baseline_evidence_count} | {row.guarded_evidence_count} |"
    )


def _next_action(report: SolarGuardedBoostLockedReadinessReport) -> str:
    failures = collect_solar_guarded_boost_locked_readiness_failures(report)
    if failures:
        return "readiness failure를 먼저 수정하고 locked live 실행을 보류한다."
    if report.summary.candidate_live_call_count == 0:
        return "candidate live call 대상이 없어 live paired comparison을 보류하고 dev router를 재검토한다."
    return "별도 승인 후 locked place_story live paired comparison 실행 여부를 판단한다."


def _locked_readiness_conclusion(
    report: SolarGuardedBoostLockedReadinessReport,
) -> str:
    failures = collect_solar_guarded_boost_locked_readiness_failures(report)
    if failures:
        return (
            f"readiness gate가 실패했다: {', '.join(failures)}.\n\n"
            "Solar Pro 3 locked live 호출로 넘어가면 안 된다."
        )
    if report.summary.candidate_live_call_count == 0:
        return (
            "readiness gate는 통과했지만 candidate live call 대상이 없다.\n\n"
            "이 경우 locked live paired comparison은 보류하고 router 적용 폭을 재검토한다."
        )
    return (
        "readiness gate를 통과했다.\n\n"
        "이 결과는 live 품질 개선 주장이 아니라, locked live paired comparison 실행 전 split, route, call budget, public-safe boundary가 계획 범위 안에 있다는 검증이다."
    )


def main() -> int:
    args = _parse_args()
    report = run_solar_guarded_boost_locked_test_readiness(
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
        expected_query_count=args.expected_query_count,
    )
    failures = collect_solar_guarded_boost_locked_readiness_failures(report)
    print(
        "solar_guarded_boost_locked_test_readiness "
        f"status={'PASS' if not failures else 'FAIL'} "
        f"query_count={report.summary.locked_place_story_query_count} "
        f"expected_calls={report.summary.expected_total_live_call_count} "
        f"candidate_calls={report.summary.candidate_live_call_count} "
        f"decision={report.summary.readiness_decision} "
        f"device={report.resolved_device} "
        f"solar_calls={report.summary.solar_call_count} "
        f"failures={len(failures)}",
    )
    return 0 if not failures else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run guarded boost locked test readiness dry-run.",
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
    parser.add_argument(
        "--expected-query-count",
        type=int,
        default=EXPECTED_LOCKED_PLACE_STORY_QUERY_COUNT,
    )
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
