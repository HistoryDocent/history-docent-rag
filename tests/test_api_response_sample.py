from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


DOC_PATH = Path("docs/API_RESPONSE_SAMPLE.md")
REPORT_PATH = Path("evals/reports/api_response_sample_report.md")


def test_api_response_sample_docs_exist_and_are_sanitized() -> None:
    for path in (DOC_PATH, REPORT_PATH, Path("README.md")):
        text = path.read_text(encoding="utf-8")

        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\\s*=", text)
        assert "private_data/" not in text
        assert "chunk text" in text


def test_api_response_sample_json_blocks_are_parseable() -> None:
    blocks = _json_blocks(DOC_PATH.read_text(encoding="utf-8"))

    assert len(blocks) == 5
    parsed = [json.loads(block) for block in blocks]
    assert all(isinstance(payload, dict) for payload in parsed)


def test_api_response_sample_records_required_answer_contract_fields() -> None:
    samples = _sample_payloads()
    answerable = samples["sample-place-story-001"]
    no_answer = samples["sample-no-answer-001"]

    for payload in (answerable, no_answer):
        assert payload["contract_version"] == "chat-api/v1"
        assert payload["rag_contract_version"] == "citation-rag-answer/v1"
        assert "answer" in payload
        assert "spoken_answer" in payload
        assert "citations" in payload
        assert "evidence_ids" in payload
        assert payload["provider"] == "contract_only"
        assert payload["model_id"] == "contract-only"
        assert payload["usage"]["solar_call_count"] == 0
        assert payload["classifier_router_dry_run"]["active_route_applied"] is False

    assert answerable["abstained"] is False
    assert answerable["citations"][0]["citation_recoverable"] is True
    assert answerable["evidence_ids"] == ["evidence-sample-001"]
    assert no_answer["abstained"] is True
    assert no_answer["citations"] == []
    assert no_answer["evidence_ids"] == []


def test_api_response_sample_records_dry_run_and_error_boundaries() -> None:
    samples = _sample_payloads()
    answerable = samples["sample-place-story-001"]
    dry_run = answerable["classifier_router_dry_run"]
    active_route_flag = dry_run["active_route_flag_dry_run"]

    assert dry_run["guarded_route_candidate"]["guard_policy_id"] == (
        "relationship-route-guard-v1"
    )
    assert active_route_flag["flag_policy_id"] == "chat-active-route-flag-dry-run-v1"
    assert active_route_flag["default_enabled"] is False
    assert active_route_flag["active_route_applied"] is False
    assert active_route_flag["fallback_reason_tag"] == "feature_flag_disabled"

    error_codes = {
        payload["error"]["code"]
        for payload in _json_payloads()
        if isinstance(payload.get("error"), dict)
    }
    assert error_codes == {"validation_error", "provider_unavailable"}


def test_api_response_sample_report_records_public_gate() -> None:
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert "json_sample_block_count | 5" in report
    assert "answerable_response_sample_count | 1" in report
    assert "no_answer_response_sample_count | 1" in report
    assert "error_envelope_sample_count | 2" in report
    assert "public_raw_text_leakage_count | 0" in report
    assert "active_route_applied_count | 0" in report
    assert "`HD-PORTFOLIO-QA-001`" in report


def _json_blocks(text: str) -> list[str]:
    return re.findall(r"```json\n(.*?)\n```", text, flags=re.DOTALL)


def _json_payloads() -> list[dict[str, Any]]:
    return [json.loads(block) for block in _json_blocks(DOC_PATH.read_text(encoding="utf-8"))]


def _sample_payloads() -> dict[str, dict[str, Any]]:
    return {
        payload["request_id"]: payload
        for payload in _json_payloads()
        if "request_id" in payload
    }
