from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.app import create_app
from app.api.v1.chat import CHAT_API_CONTRACT_VERSION, public_chat_response_row
from pipelines.build_chat_api_contract_report import (
    build_report,
    collect_chat_api_contract_failures,
    run_contract_smoke_rows,
)


def _client() -> TestClient:
    return TestClient(create_app(), raise_server_exceptions=False)


def test_chat_endpoint_returns_citation_response_contract() -> None:
    response = _client().post(
        "/api/v1/chat",
        json={
            "request_id": "api-test-answer",
            "query": "경복궁을 한양 맥락에서 설명해줘",
            "query_type": "place_story",
            "language": "ko",
            "place_context": ["gyeongbokgung"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["contract_version"] == CHAT_API_CONTRACT_VERSION
    assert body["rag_contract_version"] == "citation-rag-answer/v1"
    assert body["request_id"] == "api-test-answer"
    assert body["provider"] == "contract_only"
    assert body["abstained"] is False
    assert body["citations"][0]["citation_recoverable"] is True
    assert body["evidence_ids"] == [body["citations"][0]["evidence_id"]]
    assert body["usage"]["solar_call_count"] == 0
    dry_run = body["classifier_router_dry_run"]
    assert dry_run["enabled"] is True
    assert dry_run["active_query_type"] == "place_story"
    assert dry_run["active_route_applied"] is False
    assert dry_run["active_route_policy_id"] == body["usage"]["route_policy_id"]


def test_chat_endpoint_exposes_classifier_router_dry_run_without_active_route_change() -> None:
    response = _client().post(
        "/api/v1/chat",
        json={
            "request_id": "api-test-router-dry-run",
            "query": "경복궁과 창덕궁은 왕권 정통성과 어떤 관계로 연결돼?",
            "query_type": "overview",
            "language": "ko",
            "place_context": ["gyeongbokgung", "changdeokgung"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    dry_run = body["classifier_router_dry_run"]
    assert body["query_type"] == "overview"
    assert body["usage"]["route_policy_id"] == "default_dense_voice_rewrite_v1"
    assert dry_run["predicted_query_type"] == "relationship"
    assert dry_run["predicted_route_policy_id"] == "relationship_hybrid_weighted_e5_v1"
    assert dry_run["route_policy_changed"] is True
    assert dry_run["active_route_applied"] is False
    assert dry_run["active_route_policy_id"] == body["usage"]["route_policy_id"]


def test_chat_endpoint_abstains_for_no_answer_contract() -> None:
    response = _client().post(
        "/api/v1/chat",
        json={
            "request_id": "api-test-no-answer",
            "query": "이 자료에 없는 현대 스포츠 기록을 알려줘",
            "query_type": "no_answer",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["abstained"] is True
    assert body["citations"] == []
    assert body["evidence_ids"] == []
    assert body["unsupported_claim_risk"] == "low"


def test_chat_endpoint_uses_standard_error_envelope_for_validation() -> None:
    response = _client().post(
        "/api/v1/chat",
        json={
            "request_id": "api-test-validation",
            "query": " ",
            "query_type": "place_story",
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["message"] == "Request validation failed."
    assert body["error"]["details"][0]["field"] == "query"
    assert "traceback" not in str(body).lower()


def test_chat_endpoint_blocks_live_solar_provider_by_default() -> None:
    response = _client().post(
        "/api/v1/chat",
        json={
            "request_id": "api-test-solar-disabled",
            "query": "경복궁을 설명해줘",
            "query_type": "place_story",
            "provider_mode": "solar_pro_3",
        },
    )

    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "provider_unavailable"
    assert "Solar Pro 3" in body["error"]["message"]


def test_public_chat_response_row_excludes_raw_answer_text() -> None:
    response = _client().post(
        "/api/v1/chat",
        json={
            "request_id": "api-test-public-row",
            "query": "경복궁 설명",
            "query_type": "place_story",
        },
    )

    row = public_chat_response_row(response.json())

    assert "answer" not in row
    assert "spoken_answer" not in row
    assert "raw_text" not in row
    assert row["citation_count"] == 1
    assert row["solar_call_count"] == 0
    assert row["classifier_dry_run_enabled"] is True
    assert row["classifier_active_route_applied"] is False


def test_chat_api_contract_report_gate_passes(tmp_path) -> None:
    report = build_report(report_path=tmp_path / "chat_api_contract_report.md")

    assert collect_chat_api_contract_failures(report) == []
    assert report.summary.request_count == 4
    assert report.summary.success_count == 2
    assert report.summary.validation_error_count == 1
    assert report.summary.provider_unavailable_count == 1
    assert report.summary.classifier_dry_run_count == 2
    assert report.summary.classifier_active_route_applied_count == 0
    assert report.summary.live_solar_call_count == 0
    assert report.output_quality.public_raw_text_leakage_count == 0
    assert report.output_quality.private_path_leakage_count == 0


def test_chat_api_contract_smoke_rows_are_public_safe() -> None:
    rows = run_contract_smoke_rows()

    assert {row["case_id"] for row in rows} == {
        "answerable_contract",
        "no_answer_contract",
        "validation_error",
        "solar_disabled",
    }
    assert all("query" not in row for row in rows)
    assert all("answer" not in row for row in rows)
