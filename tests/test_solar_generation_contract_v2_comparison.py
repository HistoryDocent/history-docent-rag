from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.domain.retrieval import FORBIDDEN_PUBLIC_EVAL_FIELDS
from pipelines.run_solar_generation_contract_v2_comparison import (
    DEFAULT_QUERY_TYPES,
    SOLAR_GENERATION_BASELINE_ANSWER_POLICY_ID,
    SOLAR_GENERATION_CONTRACT_V2_ANSWER_POLICY_ID,
    build_fake_generation_contract_v2_comparison_inputs,
    build_public_solar_generation_contract_v2_comparison_rows,
    build_solar_generation_contract_v2_comparison_report,
    collect_solar_generation_contract_v2_comparison_failures,
    run_solar_generation_contract_v2_comparison,
    validate_generation_contract_v2_comparison_inputs,
)


def test_solar_generation_contract_v2_comparison_writes_public_safe_report(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "solar_generation_contract_v2_comparison_report.md"
    rows_path = tmp_path / "solar_generation_contract_v2_comparison_results.jsonl"

    report = run_solar_generation_contract_v2_comparison(
        report_path=report_path,
        result_rows_path=rows_path,
    )
    markdown = report_path.read_text(encoding="utf-8")
    rows = [json.loads(line) for line in rows_path.read_text(encoding="utf-8").splitlines()]

    assert report.report_version == "solar-generation-contract-v2-comparison-report/v1"
    assert report.baseline_report.summary.eval_count == len(DEFAULT_QUERY_TYPES)
    assert report.candidate_report.summary.eval_count == len(DEFAULT_QUERY_TYPES)
    assert report.baseline_report.summary.solar_call_count == 0
    assert report.candidate_report.summary.solar_call_count == 0
    assert report.candidate_report.summary.citation_precision == 1.0
    assert report.baseline_report.summary.citation_precision == 0.333333
    assert collect_solar_generation_contract_v2_comparison_failures(report) == []
    assert report.output_quality.public_raw_text_leakage_count == 0
    assert report.output_quality.private_path_leakage_count == 0
    assert report.output_quality.secret_like_leakage_count == 0
    assert "fake provider 기반 contract 비교" in markdown
    assert "최종 성능 개선 주장이 아니다" in markdown
    assert "fixture answer" not in markdown
    assert all(FORBIDDEN_PUBLIC_EVAL_FIELDS.isdisjoint(row.keys()) for row in rows)


def test_solar_generation_contract_v2_comparison_uses_identical_pairing() -> None:
    baseline_inputs, candidate_inputs = build_fake_generation_contract_v2_comparison_inputs()

    validate_generation_contract_v2_comparison_inputs(
        baseline_inputs=baseline_inputs,
        candidate_inputs=candidate_inputs,
    )

    with pytest.raises(ValueError, match="identical query_id set"):
        validate_generation_contract_v2_comparison_inputs(
            baseline_inputs=baseline_inputs,
            candidate_inputs=candidate_inputs[:-1],
        )


def test_solar_generation_contract_v2_comparison_rows_are_query_grain() -> None:
    baseline_inputs, candidate_inputs = build_fake_generation_contract_v2_comparison_inputs()

    report = build_solar_generation_contract_v2_comparison_report(
        baseline_inputs=baseline_inputs,
        candidate_inputs=candidate_inputs,
    )
    rows = build_public_solar_generation_contract_v2_comparison_rows(report)
    answerable_rows = [row for row in rows if row["query_type"] != "no_answer"]

    assert len(rows) == len(DEFAULT_QUERY_TYPES)
    assert {row["baseline_answer_policy_id"] for row in rows} == {
        SOLAR_GENERATION_BASELINE_ANSWER_POLICY_ID,
    }
    assert {row["candidate_answer_policy_id"] for row in rows} == {
        SOLAR_GENERATION_CONTRACT_V2_ANSWER_POLICY_ID,
    }
    assert all(row["citation_precision_delta"] == 0.666667 for row in answerable_rows)
    assert all(row["citation_count_delta"] == -2 for row in answerable_rows)
    assert rows[0]["query_id"].startswith("q-fake-")
