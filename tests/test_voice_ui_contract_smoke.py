from __future__ import annotations

import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.app import create_app


DOC_PATH = Path("docs/VOICE_UI_CONTRACT_SMOKE.md")
REPORT_PATH = Path("evals/reports/voice_ui_contract_smoke_report.md")
FRONTEND_CLIENT_PATH = Path("frontend/src/lib/chatClient.ts")
FRONTEND_CLIENT_TEST_PATH = Path("frontend/src/lib/chatClient.test.ts")
FRONTEND_SMOKE_SCRIPT_PATH = Path("frontend/scripts/contractSmoke.mjs")


def test_voice_ui_contract_smoke_docs_and_code_are_sanitized() -> None:
    for path in (
        DOC_PATH,
        REPORT_PATH,
        FRONTEND_CLIENT_PATH,
        FRONTEND_CLIENT_TEST_PATH,
        FRONTEND_SMOKE_SCRIPT_PATH,
        Path("README.md"),
    ):
        text = path.read_text(encoding="utf-8")

        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\\s*=", text)
        assert "private_data/" not in text


def test_fastapi_contract_only_smoke_answerable_and_no_answer() -> None:
    client = TestClient(create_app(), raise_server_exceptions=False)

    answerable = client.post(
        "/api/v1/chat",
        json={
            "request_id": "voice-ui-contract-smoke-answerable",
            "query": "경복궁을 한양 맥락에서 짧게 설명해줘",
            "language": "ko",
            "query_type": "place_story",
            "place_context": ["gyeongbokgung"],
            "voice_mode": True,
            "retrieval_mode": "contract_only",
            "provider_mode": "contract_only",
            "active_route_mode": "disabled",
        },
    )
    no_answer = client.post(
        "/api/v1/chat",
        json={
            "request_id": "voice-ui-contract-smoke-no-answer",
            "query": "이 자료에 없는 현대 스포츠 기록을 알려줘",
            "language": "ko",
            "query_type": "no_answer",
            "place_context": [],
            "voice_mode": True,
            "retrieval_mode": "contract_only",
            "provider_mode": "contract_only",
            "active_route_mode": "disabled",
        },
    )

    assert answerable.status_code == 200
    assert no_answer.status_code == 200

    answerable_body = answerable.json()
    no_answer_body = no_answer.json()

    assert answerable_body["abstained"] is False
    assert len(answerable_body["citations"]) == 1
    assert answerable_body["spoken_answer"]
    assert answerable_body["usage"]["solar_call_count"] == 0
    assert answerable_body["classifier_router_dry_run"]["active_route_applied"] is False

    assert no_answer_body["abstained"] is True
    assert no_answer_body["citations"] == []
    assert no_answer_body["usage"]["solar_call_count"] == 0


def test_frontend_contract_smoke_wiring_is_recorded() -> None:
    vite_config = Path("frontend/vite.config.ts").read_text(encoding="utf-8")
    client = FRONTEND_CLIENT_PATH.read_text(encoding="utf-8")
    client_test = FRONTEND_CLIENT_TEST_PATH.read_text(encoding="utf-8")
    smoke_script = FRONTEND_SMOKE_SCRIPT_PATH.read_text(encoding="utf-8")

    assert '"/api"' in vite_config
    assert '"http://127.0.0.1:8000"' in vite_config
    assert "VITE_HISTORY_DOCENT_CHAT_MODE" in client
    assert "resolveChatEndpoint" in client
    assert "mode: \"backend\"" in client_test
    assert "npm run smoke:contract" in Path("docs/VOICE_UI_CONTRACT_SMOKE.md").read_text(
        encoding="utf-8",
    )
    assert "live_solar_call_count" in smoke_script


def test_voice_ui_contract_smoke_report_records_gates() -> None:
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert "frontend_proxy_route_count | 1" in report
    assert "frontend_backend_mode_unit_test_count | 4" in report
    assert "backend_contract_smoke_request_count | 2" in report
    assert "backend_answerable_status_code | 200" in report
    assert "backend_no_answer_status_code | 200" in report
    assert "backend_active_route_applied_count | 0" in report
    assert "live_solar_call_count | 0" in report
    assert "retrieval_execution_count | 0" in report
    assert "External audit | PASS" in report
    assert "fact_voice_ui_contract_smoke" in report
