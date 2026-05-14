from __future__ import annotations

import json
from pathlib import Path

from app.domain.generation import CitationRagDraftV2
from app.domain.retrieval import FORBIDDEN_PUBLIC_EVAL_FIELDS
from pipelines.run_solar_generation_v2_prompt_policy_validator import (
    DEFAULT_QUERY_TYPES,
    MIN_EVIDENCE_BY_QUERY_TYPE,
    PromptPolicyValidationInput,
    build_fake_prompt_policy_validation_inputs,
    build_public_prompt_policy_validation_rows,
    build_prompt_policy_validation_report,
    collect_prompt_policy_validation_failures,
    run_solar_generation_v2_prompt_policy_validator,
    validate_prompt_policy_input,
)


def test_prompt_policy_validator_writes_public_safe_report(tmp_path: Path) -> None:
    report_path = tmp_path / "solar_generation_v2_prompt_policy_validator_report.md"
    rows_path = tmp_path / "solar_generation_v2_prompt_policy_validator_rows.jsonl"

    report = run_solar_generation_v2_prompt_policy_validator(
        report_path=report_path,
        result_rows_path=rows_path,
    )
    markdown = report_path.read_text(encoding="utf-8")
    rows = [json.loads(line) for line in rows_path.read_text(encoding="utf-8").splitlines()]

    assert report.report_version == "solar-generation-v2-prompt-policy-validator-report/v1"
    assert report.summary.row_count == len(DEFAULT_QUERY_TYPES)
    assert report.summary.query_type_policy_count == len(DEFAULT_QUERY_TYPES)
    assert report.summary.fail_count == 0
    assert report.summary.fallback_required_count == 1
    assert report.summary.live_solar_call_count == 0
    assert report.summary.readiness_decision == "ready_for_repaired_prompt_dry_run"
    assert collect_prompt_policy_validation_failures(report) == []
    assert report.output_quality.public_raw_text_leakage_count == 0
    assert report.output_quality.private_path_leakage_count == 0
    assert report.output_quality.secret_like_leakage_count == 0
    assert "fake provider/validator" in markdown
    assert "청킹 비교 테스트는 계속 보류" in markdown
    assert "fixture answer" not in markdown
    assert all(FORBIDDEN_PUBLIC_EVAL_FIELDS.isdisjoint(row.keys()) for row in rows)


def test_prompt_policy_validator_accepts_fake_provider_v2_draft() -> None:
    fake_provider_payload = {
        "answer": "경복궁은 선택된 근거를 바탕으로 설명할 수 있습니다.",
        "spoken_answer": "경복궁은 한양의 중심을 이해하기 좋은 장소입니다.",
        "used_evidence_pack_ranks": [1, 2],
        "coverage_intent": "multi_evidence",
        "unsupported_claim_risk": "low",
    }
    base_input = next(
        item
        for item in build_fake_prompt_policy_validation_inputs()
        if item.item.query.query_type == "overview"
    )
    candidate = base_input.model_copy(
        update={
            "draft": CitationRagDraftV2.model_validate(fake_provider_payload),
        },
    )

    row = validate_prompt_policy_input(candidate)

    assert row.validation_status == "pass"
    assert row.selected_evidence_count == MIN_EVIDENCE_BY_QUERY_TYPE["overview"]
    assert row.solar_call_count == 0


def test_prompt_policy_validator_rejects_invalid_rank() -> None:
    base_input = next(
        item
        for item in build_fake_prompt_policy_validation_inputs()
        if item.item.query.query_type == "place_fact"
    )
    invalid = base_input.model_copy(
        update={
            "draft": CitationRagDraftV2(
                answer="선택 근거 rank가 잘못된 fixture 답변입니다.",
                spoken_answer="선택 근거가 잘못됐습니다.",
                used_evidence_pack_ranks=(4,),
                coverage_intent="focused",
                unsupported_claim_risk="low",
            ),
        },
    )

    row = validate_prompt_policy_input(invalid)

    assert row.validation_status == "fail"
    assert row.invalid_rank_count == 1
    assert "invalid_evidence_rank" in row.validation_tags


def test_prompt_policy_validator_requires_multi_evidence_floor() -> None:
    base_input = next(
        item
        for item in build_fake_prompt_policy_validation_inputs()
        if item.item.query.query_type == "overview"
    )
    insufficient = base_input.model_copy(
        update={
            "draft": CitationRagDraftV2(
                answer="근거 하나만 고른 fixture 답변입니다.",
                spoken_answer="근거 하나만 고른 답변입니다.",
                used_evidence_pack_ranks=(1,),
                coverage_intent="focused",
                unsupported_claim_risk="low",
            ),
        },
    )

    row = validate_prompt_policy_input(insufficient)

    assert row.validation_status == "fail"
    assert row.evidence_floor_violation is True
    assert row.coverage_intent_violation is True
    assert row.unsupported_risk_violation is True


def test_prompt_policy_validator_routes_place_story_to_v1_fallback() -> None:
    place_story_input = next(
        item
        for item in build_fake_prompt_policy_validation_inputs()
        if item.item.query.query_type == "place_story"
    )

    row = validate_prompt_policy_input(place_story_input)

    assert row.validation_status == "fallback_required"
    assert row.v1_fallback_allowed is True
    assert "v1_fallback_required" in row.validation_tags
    assert "monitor_only_query_type" in row.validation_tags


def test_prompt_policy_validator_report_rows_are_public_safe() -> None:
    inputs = build_fake_prompt_policy_validation_inputs()
    report = build_prompt_policy_validation_report(inputs=inputs)
    rows = build_public_prompt_policy_validation_rows(report)

    assert collect_prompt_policy_validation_failures(report) == []
    assert rows
    assert all(FORBIDDEN_PUBLIC_EVAL_FIELDS.isdisjoint(row.keys()) for row in rows)
    assert {row["solar_call_count"] for row in rows} == {0}
    assert {row["validation_status"] for row in rows} == {"pass", "fallback_required"}


def test_prompt_policy_validator_rejects_shape_mismatch() -> None:
    base_input = build_fake_prompt_policy_validation_inputs()[0]
    mismatched = PromptPolicyValidationInput(
        item=base_input.item,
        evidence_pack=base_input.evidence_pack.model_copy(
            update={"query_id": "q-other"},
        ),
        prompt_policy_id=base_input.prompt_policy_id,
        draft=base_input.draft,
    )

    try:
        validate_prompt_policy_input(mismatched)
    except ValueError as exc:
        assert "query_id must match" in str(exc)
    else:
        raise AssertionError("shape mismatch must raise ValueError")
