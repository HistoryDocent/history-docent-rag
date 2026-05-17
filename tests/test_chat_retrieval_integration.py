from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.app import create_app
from app.api.v1.chat import get_chat_service
from app.application.chat_retrieval import StaticRetrievalBackend
from app.application.chat_service import ChatContractService
from pipelines.build_chat_retrieval_integration_report import (
    build_report,
    collect_chat_retrieval_integration_failures,
    run_integration_smoke_rows,
)


def _client_with_static_retrieval() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_chat_service] = lambda: ChatContractService(
        retrieval_backend=StaticRetrievalBackend(),
    )
    return TestClient(app, raise_server_exceptions=False)


def test_chat_endpoint_retrieval_backed_mode_returns_packed_evidence() -> None:
    response = _client_with_static_retrieval().post(
        "/api/v1/chat",
        json={
            "request_id": "api-test-retrieval-backed",
            "query": "경복궁을 한양 맥락에서 설명해줘",
            "query_type": "place_story",
            "language": "ko",
            "place_context": ["gyeongbokgung"],
            "retrieval_mode": "retrieval_backed",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["abstained"] is False
    assert body["citations"][0]["child_id"] == "fixture-child-gyeongbokgung"
    assert body["evidence_ids"] == [body["citations"][0]["evidence_id"]]
    assert body["usage"]["retrieval_mode"] == "retrieval_backed"
    assert body["usage"]["retrieval_method"] == "fixture_retrieval"
    assert body["usage"]["retrieval_candidate_count"] == 1
    assert body["usage"]["solar_call_count"] == 0
    assert body["classifier_router_dry_run"]["active_route_applied"] is False
    assert (
        body["classifier_router_dry_run"]["active_route_policy_id"]
        == body["usage"]["route_policy_id"]
    )


def test_chat_endpoint_retrieval_backed_no_answer_abstains() -> None:
    response = _client_with_static_retrieval().post(
        "/api/v1/chat",
        json={
            "request_id": "api-test-retrieval-no-answer",
            "query": "이 자료에 없는 현대 스포츠 기록을 알려줘",
            "query_type": "no_answer",
            "retrieval_mode": "retrieval_backed",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["abstained"] is True
    assert body["citations"] == []
    assert body["usage"]["retrieval_mode"] == "retrieval_backed"
    assert body["usage"]["retrieval_candidate_count"] == 0
    assert body["classifier_router_dry_run"]["active_route_applied"] is False


def test_chat_retrieval_integration_report_gate_passes(tmp_path) -> None:
    report = build_report(report_path=tmp_path / "chat_retrieval_integration_report.md")

    assert collect_chat_retrieval_integration_failures(report) == []
    assert report.summary.request_count == 3
    assert report.summary.retrieval_backed_request_count == 2
    assert report.summary.retrieval_success_count == 1
    assert report.summary.classifier_dry_run_count == 3
    assert report.summary.classifier_active_route_applied_count == 0
    assert report.summary.live_solar_call_count == 0
    assert report.output_quality.public_raw_text_leakage_count == 0
    assert report.output_quality.private_path_leakage_count == 0


def test_chat_retrieval_integration_rows_do_not_include_raw_text() -> None:
    rows = run_integration_smoke_rows()

    assert all("query" not in row for row in rows)
    assert all("answer" not in row for row in rows)
    assert all("spoken_answer" not in row for row in rows)
    assert any(row.get("retrieval_mode") == "retrieval_backed" for row in rows)
