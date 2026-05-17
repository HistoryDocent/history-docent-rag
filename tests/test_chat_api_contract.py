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
    active_route_flag = dry_run["active_route_flag_dry_run"]
    assert active_route_flag["flag_policy_id"] == "chat-active-route-flag-dry-run-v1"
    assert active_route_flag["enabled"] is False
    assert active_route_flag["mode"] == "disabled"
    assert active_route_flag["default_enabled"] is False
    assert active_route_flag["active_route_applied"] is False
    assert active_route_flag["fallback_reason_tag"] == "feature_flag_disabled"
    guarded_route = dry_run["guarded_route_candidate"]
    assert guarded_route["guard_policy_id"] == "relationship-route-guard-v1"
    assert guarded_route["guarded_query_type"] == dry_run["predicted_query_type"]
    assert guarded_route["guard_applied"] is False


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
    guarded_route = dry_run["guarded_route_candidate"]
    assert guarded_route["guarded_query_type"] == "relationship"
    assert guarded_route["route_policy_id"] == "relationship_hybrid_weighted_e5_v1"
    assert guarded_route["guard_applied"] is False
    assert guarded_route["route_policy_changed"] is True
    active_route_flag = dry_run["active_route_flag_dry_run"]
    assert active_route_flag["enabled"] is False
    assert active_route_flag["selected_query_type"] == "relationship"
    assert active_route_flag["selected_route_policy_id"] == (
        "relationship_hybrid_weighted_e5_v1"
    )
    assert active_route_flag["route_policy_changed"] is True
    assert active_route_flag["active_route_applied"] is False


def test_chat_endpoint_active_route_shadow_flag_does_not_change_active_route() -> None:
    response = _client().post(
        "/api/v1/chat",
        json={
            "request_id": "api-test-active-route-shadow",
            "query": "경복궁과 창덕궁은 왕권 정통성과 어떤 관계로 연결돼?",
            "query_type": "overview",
            "language": "ko",
            "place_context": ["gyeongbokgung", "changdeokgung"],
            "active_route_mode": "shadow",
        },
    )

    assert response.status_code == 200
    body = response.json()
    dry_run = body["classifier_router_dry_run"]
    active_route_flag = dry_run["active_route_flag_dry_run"]
    assert body["usage"]["route_policy_id"] == "default_dense_voice_rewrite_v1"
    assert dry_run["active_route_policy_id"] == body["usage"]["route_policy_id"]
    assert dry_run["active_route_applied"] is False
    assert active_route_flag["enabled"] is True
    assert active_route_flag["mode"] == "shadow"
    assert active_route_flag["default_enabled"] is False
    assert active_route_flag["selected_query_type"] == "relationship"
    assert active_route_flag["selected_route_policy_id"] == (
        "relationship_hybrid_weighted_e5_v1"
    )
    assert active_route_flag["route_policy_changed"] is True
    assert active_route_flag["fallback_reason_tag"] == "shadow_only_candidate_route"
    assert active_route_flag["active_route_applied"] is False


def test_chat_endpoint_exposes_guarded_route_candidate_without_active_route_change() -> None:
    response = _client().post(
        "/api/v1/chat",
        json={
            "request_id": "api-test-guarded-route",
            "query": "창덕궁이 태종 시기 권력 기억과 연결되는 이유를 설명할 근거를 찾아줘",
            "query_type": "place_fact",
            "language": "ko",
            "place_context": ["changdeokgung", "taejong-memory"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    dry_run = body["classifier_router_dry_run"]
    guarded_route = dry_run["guarded_route_candidate"]
    assert dry_run["predicted_query_type"] == "relationship"
    assert dry_run["predicted_route_policy_id"] == "relationship_hybrid_weighted_e5_v1"
    assert guarded_route["guarded_query_type"] == "place_fact"
    assert guarded_route["route_policy_id"] == "default_dense_voice_rewrite_v1"
    assert guarded_route["guard_applied"] is True
    assert "block_fact_reason_risk" in guarded_route["guard_reason_tags"]
    assert guarded_route["route_policy_changed"] is False
    assert dry_run["active_route_applied"] is False
    assert body["usage"]["route_policy_id"] == "default_dense_voice_rewrite_v1"


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
    assert row["guard_policy_id"] == "relationship-route-guard-v1"
    assert row["guarded_route_candidate_id"] == "dense_multilingual_e5_small_voice_rewrite"
    assert row["guard_applied"] is False
    assert row["active_route_flag_policy_id"] == "chat-active-route-flag-dry-run-v1"
    assert row["active_route_flag_enabled"] is False
    assert row["active_route_flag_default_enabled"] is False
    assert row["active_route_fallback_reason_tag"] == "feature_flag_disabled"
    assert row["active_route_applied"] is False


def test_chat_api_contract_report_gate_passes(tmp_path) -> None:
    report = build_report(report_path=tmp_path / "chat_api_contract_report.md")

    assert collect_chat_api_contract_failures(report) == []
    assert report.summary.request_count == 6
    assert report.summary.success_count == 4
    assert report.summary.validation_error_count == 1
    assert report.summary.provider_unavailable_count == 1
    assert report.summary.classifier_dry_run_count == 4
    assert report.summary.classifier_active_route_applied_count == 0
    assert report.summary.classifier_guarded_route_candidate_count == 4
    assert report.summary.classifier_guard_applied_count == 1
    assert report.summary.active_route_flag_dry_run_count == 4
    assert report.summary.active_route_flag_enabled_count == 1
    assert report.summary.active_route_flag_applied_count == 0
    assert report.summary.active_route_flag_default_enabled_count == 0
    assert report.summary.live_solar_call_count == 0
    assert report.output_quality.public_raw_text_leakage_count == 0
    assert report.output_quality.private_path_leakage_count == 0


def test_chat_api_contract_smoke_rows_are_public_safe() -> None:
    rows = run_contract_smoke_rows()

    assert {row["case_id"] for row in rows} == {
        "answerable_contract",
        "active_route_shadow_flag",
        "guarded_route_candidate",
        "no_answer_contract",
        "validation_error",
        "solar_disabled",
    }
    assert all("query" not in row for row in rows)
    assert all("answer" not in row for row in rows)
