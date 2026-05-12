from __future__ import annotations

import json

import httpx
import pytest

from app.domain.generation import CitationRagDraft, CitationRagDraftV2
from app.providers.llm.base import CitationDraftRequest, build_citation_rag_draft_v2_schema
from app.providers.llm.solar_pro_3 import (
    DEFAULT_UPSTAGE_BASE_URL,
    SolarPro3CitationDraftProvider,
    SolarPro3ProviderConfig,
)
from app.providers.llm.base import (
    LlmProviderConfigError,
    LlmProviderRequestError,
    LlmProviderResponseError,
)
from pipelines.build_solar_provider_contract_report import (
    build_solar_provider_contract_report,
)


def _request() -> CitationDraftRequest:
    return CitationDraftRequest(
        query_id="q-solar-test",
        query_type="place_story",
        query_text="경복궁은 왜 중요한 장소야?",
        evidence_context="테스트 evidence",
        place_ids=("gyeongbokgung",),
        language="ko",
    )


def _config() -> SolarPro3ProviderConfig:
    return SolarPro3ProviderConfig(
        credential="mock-provider-key",
        base_url=DEFAULT_UPSTAGE_BASE_URL,
        model_id="solar-pro3",
        timeout_seconds=3.0,
        max_retries=1,
        max_tokens=700,
    )


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_solar_provider_builds_structured_request_and_parses_draft() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["authorization"] = request.headers.get("Authorization")
        captured["payload"] = json.loads(request.content.decode("utf-8"))
        draft = CitationRagDraft(
            answer="경복궁은 조선의 시작과 한양의 중심을 설명하기 좋은 장소입니다.",
            spoken_answer="경복궁은 조선의 시작과 한양의 중심을 함께 보여주는 장소입니다.",
            unsupported_claim_risk="low",
        )
        return httpx.Response(
            status_code=200,
            json={
                "id": "mock-response",
                "model": "solar-pro3",
                "choices": [
                    {
                        "message": {"content": draft.model_dump_json()},
                        "finish_reason": "stop",
                    },
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 15,
                },
            },
        )

    provider = SolarPro3CitationDraftProvider(
        config=_config(),
        client=_client(handler),
    )
    result = provider.generate_draft(_request())
    payload = captured["payload"]

    assert captured["authorization"] == "Bearer mock-provider-key"
    assert result.provider == "solar_pro_3"
    assert result.model_id == "solar-pro3"
    assert result.draft.unsupported_claim_risk == "low"
    assert result.usage.api_call_count == 1
    assert result.usage.total_tokens == 15
    assert isinstance(payload, dict)
    assert payload["model"] == "solar-pro3"
    assert payload["response_format"]["type"] == "json_schema"
    assert payload["response_format"]["json_schema"]["strict"] is True


def test_solar_provider_v2_mock_response_schema_contract() -> None:
    schema = build_citation_rag_draft_v2_schema()
    draft_payload = {
        "answer": "경복궁은 한양 도성의 중심축을 설명할 때 사용할 수 있는 근거가 있습니다.",
        "spoken_answer": "경복궁은 한양의 중심축을 이해하기 좋은 장소입니다.",
        "used_evidence_pack_ranks": [1, 3],
        "coverage_intent": "multi_evidence",
        "unsupported_claim_risk": "low",
    }
    response_payload = {
        "id": "mock-response-v2",
        "model": "solar-pro3",
        "choices": [
            {
                "message": {
                    "content": json.dumps(draft_payload, ensure_ascii=False),
                },
                "finish_reason": "stop",
            },
        ],
        "usage": {
            "prompt_tokens": 20,
            "completion_tokens": 8,
            "total_tokens": 28,
        },
    }
    content = response_payload["choices"][0]["message"]["content"]
    draft = CitationRagDraftV2.model_validate(json.loads(content))

    assert schema["properties"]["used_evidence_pack_ranks"]["uniqueItems"] is True
    assert schema["required"] == [
        "answer",
        "spoken_answer",
        "used_evidence_pack_ranks",
        "coverage_intent",
        "unsupported_claim_risk",
    ]
    assert draft.used_evidence_pack_ranks == (1, 3)
    assert draft.coverage_intent == "multi_evidence"
    assert draft.unsupported_claim_risk == "low"


def test_solar_provider_rejects_missing_api_key() -> None:
    with pytest.raises(LlmProviderConfigError, match="UPSTAGE_API_KEY"):
        SolarPro3ProviderConfig(credential="")


def test_solar_provider_retries_retryable_status() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(status_code=429, json={"error": "retry"})
        draft = CitationRagDraft(
            answer="경복궁은 조선의 시작과 한양의 중심을 설명하기 좋은 장소입니다.",
            spoken_answer="경복궁은 조선의 시작과 한양의 중심을 함께 보여주는 장소입니다.",
            unsupported_claim_risk="low",
        )
        return httpx.Response(
            status_code=200,
            json={
                "id": "mock-response",
                "model": "solar-pro3",
                "choices": [{"message": {"content": draft.model_dump_json()}}],
                "usage": {},
            },
        )

    provider = SolarPro3CitationDraftProvider(
        config=_config(),
        client=_client(handler),
    )
    result = provider.generate_draft(_request())

    assert attempts == 2
    assert result.usage.api_call_count == 2


def test_solar_provider_does_not_retry_auth_error() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(status_code=401, json={"error": "auth"})

    provider = SolarPro3CitationDraftProvider(
        config=_config(),
        client=_client(handler),
    )

    with pytest.raises(LlmProviderRequestError, match="401"):
        provider.generate_draft(_request())
    assert attempts == 1


def test_solar_provider_rejects_invalid_json_content() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            json={
                "id": "mock-response",
                "model": "solar-pro3",
                "choices": [{"message": {"content": "not-json"}}],
                "usage": {},
            },
        )

    provider = SolarPro3CitationDraftProvider(
        config=_config(),
        client=_client(handler),
    )

    with pytest.raises(LlmProviderResponseError, match="not valid JSON"):
        provider.generate_draft(_request())


def test_solar_provider_rejects_schema_invalid_content() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            json={
                "id": "mock-response",
                "model": "solar-pro3",
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "answer": "답변만 있고 음성 답변이 없습니다.",
                                    "unsupported_claim_risk": "low",
                                },
                                ensure_ascii=False,
                            ),
                        },
                    },
                ],
                "usage": {},
            },
        )

    provider = SolarPro3CitationDraftProvider(
        config=_config(),
        client=_client(handler),
    )

    with pytest.raises(LlmProviderResponseError, match="schema"):
        provider.generate_draft(_request())


def test_solar_provider_contract_report_is_public_safe(tmp_path) -> None:
    report_path = tmp_path / "solar_provider_contract.md"
    markdown = build_solar_provider_contract_report(report_path=report_path)
    saved = report_path.read_text(encoding="utf-8")

    assert "Solar Pro 3 Provider Contract Report" in markdown
    assert "live_call_count | 0" in saved
    assert "mock-provider-key" not in saved
    assert "경복궁은 조선의 시작" not in saved
    assert "public_raw_text_leakage_count | 0" in saved
