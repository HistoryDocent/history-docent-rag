from __future__ import annotations

import json
from pathlib import Path

from app.domain.retrieval import FORBIDDEN_PUBLIC_EVAL_FIELDS
from pipelines.run_solar_generation_v2_tradeoff_analysis import (
    SOLAR_GENERATION_V2_TRADEOFF_ANALYSIS_REPORT_VERSION,
    build_solar_generation_v2_tradeoff_diagnostic_row,
    collect_solar_generation_v2_tradeoff_analysis_failures,
    run_solar_generation_v2_tradeoff_analysis,
)
from pipelines.run_solar_generation_v2_tradeoff_analysis import (
    SolarGenerationV2PairedMetricRow,
)


def test_solar_generation_v2_tradeoff_analysis_writes_public_safe_report(
    tmp_path: Path,
) -> None:
    source_rows_path = tmp_path / "solar_generation_contract_v2_live_results.jsonl"
    report_path = tmp_path / "solar_generation_v2_tradeoff_analysis_report.md"
    result_rows_path = tmp_path / "solar_generation_v2_tradeoff_rows.jsonl"
    source_rows_path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in _source_rows()) + "\n",
        encoding="utf-8",
    )

    report = run_solar_generation_v2_tradeoff_analysis(
        source_rows_path=source_rows_path,
        report_path=report_path,
        result_rows_path=result_rows_path,
    )
    markdown = report_path.read_text(encoding="utf-8")
    rows = [
        json.loads(line)
        for line in result_rows_path.read_text(encoding="utf-8").splitlines()
    ]

    assert report.report_version == SOLAR_GENERATION_V2_TRADEOFF_ANALYSIS_REPORT_VERSION
    assert report.summary.row_count == 3
    assert report.summary.answerable_row_count == 2
    assert report.summary.precision_gain_count == 1
    assert report.summary.correctness_regression_count == 1
    assert report.summary.unsupported_regression_count == 1
    assert report.summary.adoption_decision == "reject_default_contract"
    assert collect_solar_generation_v2_tradeoff_analysis_failures(report) == []
    assert report.output_quality.public_raw_text_leakage_count == 0
    assert report.output_quality.private_path_leakage_count == 0
    assert report.output_quality.secret_like_leakage_count == 0
    assert "채택하지 않는다" in markdown
    assert "raw query" in markdown
    assert "테스트 원문" not in markdown
    assert all(FORBIDDEN_PUBLIC_EVAL_FIELDS.isdisjoint(row.keys()) for row in rows)


def test_solar_generation_v2_tradeoff_tags_blocker_case() -> None:
    row = SolarGenerationV2PairedMetricRow.model_validate(
        {
            **_base_row(),
            "query_id": "q-dev-place-story-001",
            "query_type": "place_story",
            "correct_with_evidence_delta": -1,
            "citation_precision_delta": -0.2,
            "citation_recall_delta": -0.125,
            "unsupported_claim_delta": 1,
            "citation_count_delta": -4,
            "latency_ms_delta": 865.5607,
        },
    )

    diagnostic = build_solar_generation_v2_tradeoff_diagnostic_row(row)

    assert diagnostic.failure_surface == "generation_contract_candidate"
    assert diagnostic.adoption_blocker is True
    assert "correctness_regression" in diagnostic.diagnostic_tags
    assert "unsupported_claim_regression" in diagnostic.diagnostic_tags
    assert "evidence_over_pruning_risk" in diagnostic.diagnostic_tags
    assert "retrieval hard-case" in diagnostic.next_action


def _source_rows() -> list[dict]:
    return [
        {
            **_base_row(),
            "query_id": "q-dev-place-fact-001",
            "query_type": "place_fact",
            "citation_precision_delta": 0.8,
            "citation_count_delta": -4,
            "latency_ms_delta": -11115.0529,
        },
        {
            **_base_row(),
            "query_id": "q-dev-place-story-001",
            "query_type": "place_story",
            "correct_with_evidence_delta": -1,
            "citation_precision_delta": -0.2,
            "citation_recall_delta": -0.125,
            "unsupported_claim_delta": 1,
            "citation_count_delta": -4,
            "latency_ms_delta": 865.5607,
        },
        {
            **_base_row(),
            "query_id": "q-dev-no-answer-001",
            "query_type": "no_answer",
            "v1_correct_with_evidence": False,
            "v2_correct_with_evidence": False,
            "citation_count_delta": 0,
            "latency_ms_delta": -0.0014,
        },
    ]


def _base_row() -> dict:
    return {
        "baseline_answer_policy_id": "solar-generation-baseline-v1",
        "candidate_answer_policy_id": "solar-generation-contract-v2",
        "query_id": "q-dev-fixture-001",
        "query_type": "place_fact",
        "v1_correct_with_evidence": True,
        "v2_correct_with_evidence": True,
        "correct_with_evidence_delta": 0,
        "v1_citation_precision": 0.2,
        "v2_citation_precision": 1.0,
        "citation_precision_delta": 0.0,
        "v1_citation_recall": 0.5,
        "v2_citation_recall": 0.5,
        "citation_recall_delta": 0.0,
        "unsupported_claim_delta": 0,
        "v1_citation_count": 5,
        "v2_citation_count": 1,
        "citation_count_delta": 0,
        "latency_ms_delta": 0.0,
    }
