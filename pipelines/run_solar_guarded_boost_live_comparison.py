from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.project_paths import project_path
from app.domain.retrieval_experiment import (
    PublicRetrievalArtifactQuality,
    measure_public_retrieval_artifact_quality,
)
from pipelines.run_place_story_guarded_boost_comparison import (
    BASELINE_STRATEGY_ID,
    CANDIDATE_STRATEGY_ID,
    GUARDED_BOOST_STRATEGY_ID,
    ROUTER_POLICY_ID,
)
from pipelines.run_place_story_top_rank_coverage_repair import (
    DEFAULT_CANDIDATE_K,
    DEFAULT_EMBEDDING_CACHE_DIR,
    DEFAULT_PLACE_CATALOG_PATH,
    DEFAULT_TOP_K,
    _validate_private_rows_path,
    _write_jsonl_rows,
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
)
from pipelines.run_solar_live_generation_smoke import DEFAULT_CHUNKS_PATH, DEFAULT_DATASET_PATH


SOLAR_GUARDED_BOOST_LIVE_COMPARISON_READINESS_REPORT_VERSION = (
    "solar-guarded-boost-live-comparison-readiness/v1"
)
DEFAULT_REPORT_PATH = (
    Path("evals")
    / "reports"
    / "solar_guarded_boost_live_comparison_readiness_report.md"
)
DEFAULT_RESULT_ROWS_PATH = (
    Path("private_data")
    / "evals"
    / "results"
    / "solar_guarded_boost_live_comparison_readiness_rows.jsonl"
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
    report = run_solar_guarded_boost_live_comparison(
        chunks_path=args.chunks,
        dataset_path=args.dataset,
        place_catalog_path=args.place_catalog,
        embedding_cache_dir=args.embedding_cache_dir,
        report_path=args.report,
        result_rows_path=args.result_rows,
        dry_run_report_path=args.dry_run_report,
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
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--result-rows", type=Path, default=DEFAULT_RESULT_ROWS_PATH)
    parser.add_argument("--dry-run-report", type=Path, default=DEFAULT_DRY_RUN_REPORT_PATH)
    parser.add_argument(
        "--dry-run-result-rows",
        type=Path,
        default=DEFAULT_DRY_RUN_RESULT_ROWS_PATH,
    )
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument("--candidate-k", type=int, default=DEFAULT_CANDIDATE_K)
    parser.add_argument("--max-context-chars", type=int, default=11000)
    parser.add_argument("--live-call-hard-cap", type=int, default=DEFAULT_LIVE_CALL_HARD_CAP)
    parser.add_argument(
        "--execute-live",
        action="store_true",
        help="Blocked in HD-SOLAR-015. Requires HD-SOLAR-016 approval.",
    )
    parser.add_argument(
        "--confirm-live-execution",
        action="store_true",
        help="Blocked in HD-SOLAR-015. Requires HD-SOLAR-016 approval.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
