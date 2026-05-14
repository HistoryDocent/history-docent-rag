from __future__ import annotations

import json
from pathlib import Path

from app.domain.retrieval import FORBIDDEN_PUBLIC_EVAL_FIELDS
from pipelines.run_solar_generation_v2_prompt_policy_validator import (
    DEFAULT_QUERY_TYPES,
    build_fake_prompt_policy_validation_inputs,
    build_prompt_policy_validation_report,
)
from pipelines.run_solar_generation_v2_repaired_dry_run_readiness import (
    SOLAR_GENERATION_V2_REPAIRED_DRY_RUN_READINESS_REPORT_VERSION,
    build_public_solar_generation_v2_repaired_dry_run_rows,
    build_solar_generation_v2_repaired_dry_run_readiness_report,
    build_solar_generation_v2_repaired_dry_run_summary,
    collect_solar_generation_v2_repaired_dry_run_failures,
    run_solar_generation_v2_repaired_dry_run_readiness,
)


def test_repaired_dry_run_readiness_writes_public_safe_report(tmp_path: Path) -> None:
    report_path = tmp_path / "solar_generation_v2_repaired_dry_run_readiness_report.md"
    rows_path = tmp_path / "solar_generation_v2_repaired_dry_run_readiness_rows.jsonl"

    report = run_solar_generation_v2_repaired_dry_run_readiness(
        report_path=report_path,
        result_rows_path=rows_path,
    )
    markdown = report_path.read_text(encoding="utf-8")
    rows = [json.loads(line) for line in rows_path.read_text(encoding="utf-8").splitlines()]

    assert report.report_version == SOLAR_GENERATION_V2_REPAIRED_DRY_RUN_READINESS_REPORT_VERSION
    assert report.summary.query_count == len(DEFAULT_QUERY_TYPES)
    assert report.summary.query_type_count == len(DEFAULT_QUERY_TYPES)
    assert report.summary.baseline_live_call_count == 6
    assert report.summary.repaired_candidate_live_call_count == 5
    assert report.summary.expected_total_live_call_count == 11
    assert report.summary.v1_fallback_route_count == 1
    assert report.summary.no_answer_live_call_count == 0
    assert report.summary.solar_call_count == 0
    assert report.summary.readiness_decision == "ready_for_repaired_v2_live_approval"
    assert collect_solar_generation_v2_repaired_dry_run_failures(report) == []
    assert report.output_quality.public_raw_text_leakage_count == 0
    assert report.output_quality.private_path_leakage_count == 0
    assert report.output_quality.secret_like_leakage_count == 0
    assert "Solar Pro 3 live 호출은 수행하지 않았고" in markdown
    assert "fixture answer" not in markdown
    assert all(FORBIDDEN_PUBLIC_EVAL_FIELDS.isdisjoint(row.keys()) for row in rows)


def test_repaired_dry_run_routes_place_story_to_v1_fallback() -> None:
    validation_report = build_prompt_policy_validation_report(
        inputs=build_fake_prompt_policy_validation_inputs(),
    )
    report = build_solar_generation_v2_repaired_dry_run_readiness_report(
        validation_report=validation_report,
    )
    by_query_type = {row.query_type: row for row in report.rows}

    assert by_query_type["place_story"].route_decision == "use_v1_fallback"
    assert by_query_type["place_story"].baseline_live_call_required is True
    assert by_query_type["place_story"].repaired_live_call_required is False
    assert by_query_type["no_answer"].route_decision == "abstain_no_live_call"
    assert by_query_type["no_answer"].expected_live_call_count == 0


def test_repaired_dry_run_public_rows_are_sanitized() -> None:
    validation_report = build_prompt_policy_validation_report(
        inputs=build_fake_prompt_policy_validation_inputs(),
    )
    report = build_solar_generation_v2_repaired_dry_run_readiness_report(
        validation_report=validation_report,
    )
    public_rows = build_public_solar_generation_v2_repaired_dry_run_rows(report)

    assert public_rows
    assert all(FORBIDDEN_PUBLIC_EVAL_FIELDS.isdisjoint(row.keys()) for row in public_rows)
    assert {row["solar_call_count"] for row in public_rows} == {0}


def test_repaired_dry_run_blocks_validator_failure() -> None:
    validation_report = build_prompt_policy_validation_report(
        inputs=build_fake_prompt_policy_validation_inputs(),
    )
    failed_rows = tuple(
        row.model_copy(update={"validation_status": "fail"})
        if row.query_type == "place_fact"
        else row
        for row in validation_report.validation_rows
    )
    failed_validation_report = validation_report.model_copy(
        update={"validation_rows": failed_rows},
    )
    report = build_solar_generation_v2_repaired_dry_run_readiness_report(
        validation_report=failed_validation_report,
    )
    failures = collect_solar_generation_v2_repaired_dry_run_failures(report)

    assert "prompt_policy_validation_failed" in failures
    assert "blocked_route_present" in failures
    assert report.summary.readiness_decision == "blocked_by_readiness_gate"


def test_repaired_dry_run_blocks_hard_cap_violation() -> None:
    validation_report = build_prompt_policy_validation_report(
        inputs=build_fake_prompt_policy_validation_inputs(),
    )
    report = build_solar_generation_v2_repaired_dry_run_readiness_report(
        validation_report=validation_report,
        live_call_hard_cap=1,
    )
    failures = collect_solar_generation_v2_repaired_dry_run_failures(report)

    assert "live_call_hard_cap_exceeded" in failures
    assert report.summary.readiness_decision == "blocked_by_readiness_gate"


def test_repaired_dry_run_summary_counts_calls() -> None:
    validation_report = build_prompt_policy_validation_report(
        inputs=build_fake_prompt_policy_validation_inputs(),
    )
    rows = tuple(
        report_row
        for report_row in build_solar_generation_v2_repaired_dry_run_readiness_report(
            validation_report=validation_report,
        ).rows
    )
    summary = build_solar_generation_v2_repaired_dry_run_summary(
        rows=rows,
        live_call_hard_cap=20,
    )

    assert summary.validation_pass_count == 6
    assert summary.validation_fallback_required_count == 1
    assert summary.baseline_live_call_count == 6
    assert summary.repaired_candidate_live_call_count == 5
    assert summary.expected_total_live_call_count == 11
