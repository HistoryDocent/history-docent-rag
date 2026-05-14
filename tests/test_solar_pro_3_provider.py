from __future__ import annotations

import json
from typing import Any, cast

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
    assert payload["response_format"]["json_schema"]["name"] == "citation_rag_draft"
    assert payload["response_format"]["json_schema"]["strict"] is True
    assert (
        provider.config.public_config_summary["draft_schema_version"]
        == provider.config.draft_schema_version
    )
    assert provider.config.public_config_summary["prompt_policy_id"] == "default"


def test_solar_provider_v2_builds_structured_request_and_parses_selected_ranks() -> None:
    captured: dict[str, object] = {}
    config = SolarPro3ProviderConfig(
        credential="mock-provider-key",
        base_url=DEFAULT_UPSTAGE_BASE_URL,
        model_id="solar-pro3",
        timeout_seconds=3.0,
        max_retries=1,
        max_tokens=700,
        draft_schema_version="v2",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = json.loads(request.content.decode("utf-8"))
        draft = CitationRagDraftV2(
            answer="경복궁은 한양의 중심축을 설명할 때 사용할 수 있는 근거가 있습니다.",
            spoken_answer="경복궁은 한양의 중심축을 이해하기 좋은 장소입니다.",
            used_evidence_pack_ranks=(1,),
            coverage_intent="focused",
            unsupported_claim_risk="low",
        )
        return httpx.Response(
            status_code=200,
            json={
                "id": "mock-response-v2",
                "model": "solar-pro3",
                "choices": [
                    {
                        "message": {"content": draft.model_dump_json()},
                        "finish_reason": "stop",
                    },
                ],
                "usage": {
                    "prompt_tokens": 12,
                    "completion_tokens": 6,
                    "total_tokens": 18,
                },
            },
        )

    provider = SolarPro3CitationDraftProvider(
        config=config,
        client=_client(handler),
    )
    result = provider.generate_draft(
        _request().model_copy(
            update={
                "evidence_context": "[evidence:1] 테스트 근거\n\n[evidence:2] 보조 근거",
            },
        ),
    )
    payload = captured["payload"]

    assert isinstance(result.draft, CitationRagDraftV2)
    assert result.draft.used_evidence_pack_ranks == (1,)
    assert result.provider_config_id == config.provider_config_id
    assert isinstance(payload, dict)
    assert payload["response_format"]["json_schema"]["name"] == "citation_rag_draft_v2"
    assert payload["response_format"]["json_schema"]["schema"]["required"] == [
        "answer",
        "spoken_answer",
        "used_evidence_pack_ranks",
        "coverage_intent",
        "unsupported_claim_risk",
    ]
    assert (
        "uniqueItems"
        not in payload["response_format"]["json_schema"]["schema"]["properties"][
            "used_evidence_pack_ranks"
        ]
    )
    user_prompt = payload["messages"][1]["content"]
    assert "used_evidence_pack_ranks" in user_prompt
    assert "사용 가능한 evidence rank: 1, 2" in user_prompt


def test_solar_provider_v2_repaired_policy_adds_coverage_rules() -> None:
    captured: dict[str, object] = {}
    config = SolarPro3ProviderConfig(
        credential="mock-provider-key",
        base_url=DEFAULT_UPSTAGE_BASE_URL,
        model_id="solar-pro3",
        timeout_seconds=3.0,
        max_retries=1,
        max_tokens=700,
        draft_schema_version="v2",
        prompt_policy_id="v2_repair_coverage_floor",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = json.loads(request.content.decode("utf-8"))
        draft = CitationRagDraftV2(
            answer="경복궁은 한양의 중심축을 설명할 때 두 근거를 함께 사용할 수 있습니다.",
            spoken_answer="경복궁은 한양의 중심축을 이해하기 좋은 장소입니다.",
            used_evidence_pack_ranks=(1, 2),
            coverage_intent="multi_evidence",
            unsupported_claim_risk="low",
        )
        return httpx.Response(
            status_code=200,
            json={
                "id": "mock-response-v2-repaired",
                "model": "solar-pro3",
                "choices": [{"message": {"content": draft.model_dump_json()}}],
                "usage": {},
            },
        )

    provider = SolarPro3CitationDraftProvider(
        config=config,
        client=_client(handler),
    )
    result = provider.generate_draft(
        _request().model_copy(
            update={
                "query_type": "overview",
                "evidence_context": "[evidence:1] 테스트 근거\n\n[evidence:2] 보조 근거",
            },
        ),
    )
    payload = captured["payload"]

    assert isinstance(result.draft, CitationRagDraftV2)
    assert provider.config.public_config_summary["prompt_policy_id"] == ("v2_repair_coverage_floor")
    assert isinstance(payload, dict)
    assert config.provider_config_id != _config().provider_config_id
    system_prompt = payload["messages"][0]["content"]
    user_prompt = payload["messages"][1]["content"]
    assert "repaired v2 policy" in system_prompt
    assert "최소 used_evidence_pack_ranks 수는 2" in user_prompt
    assert "사용 가능한 evidence rank는 1, 2" in user_prompt


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
    choices = cast(list[dict[str, Any]], response_payload["choices"])
    message = cast(dict[str, str], choices[0]["message"])
    content = message["content"]
    draft = CitationRagDraftV2.model_validate(json.loads(content))
    schema_properties = cast(dict[str, Any], schema["properties"])
    rank_schema = cast(dict[str, Any], schema_properties["used_evidence_pack_ranks"])

    assert rank_schema["uniqueItems"] is True
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
