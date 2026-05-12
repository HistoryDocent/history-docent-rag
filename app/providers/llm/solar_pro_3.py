from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass
from typing import Any, Literal

import httpx

from app.domain.generation import CitationRagDraft, CitationRagDraftV2
from app.providers.llm.base import (
    CitationDraftRequest,
    CitationDraftResult,
    LlmProviderConfigError,
    LlmProviderRequestError,
    LlmProviderResponseError,
    LlmProviderUsage,
    build_citation_rag_draft_schema,
    build_citation_rag_draft_v2_schema,
)


DEFAULT_UPSTAGE_BASE_URL = "https://api.upstage.ai/v1"
DEFAULT_SOLAR_PRO_3_MODEL_ID = "solar-pro3"
DEFAULT_SOLAR_PRO_3_TIMEOUT_SECONDS = 30.0
DEFAULT_SOLAR_PRO_3_MAX_RETRIES = 2
DEFAULT_SOLAR_PRO_3_MAX_TOKENS = 700
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
CitationDraftSchemaVersion = Literal["v1", "v2"]


@dataclass(frozen=True)
class SolarPro3ProviderConfig:
    credential: str
    base_url: str = DEFAULT_UPSTAGE_BASE_URL
    model_id: str = DEFAULT_SOLAR_PRO_3_MODEL_ID
    timeout_seconds: float = DEFAULT_SOLAR_PRO_3_TIMEOUT_SECONDS
    max_retries: int = DEFAULT_SOLAR_PRO_3_MAX_RETRIES
    max_tokens: int = DEFAULT_SOLAR_PRO_3_MAX_TOKENS
    temperature: float = 0.2
    top_p: float = 0.95
    reasoning_effort: str = "minimal"
    cost_per_1k_input_tokens: float = 0.0
    cost_per_1k_output_tokens: float = 0.0
    draft_schema_version: CitationDraftSchemaVersion = "v1"

    def __post_init__(self) -> None:
        if not self.credential.strip():
            raise LlmProviderConfigError("UPSTAGE_API_KEY is required")
        if not self.base_url.strip():
            raise LlmProviderConfigError("UPSTAGE_BASE_URL must not be empty")
        if not self.model_id.strip():
            raise LlmProviderConfigError("UPSTAGE_CHAT_MODEL must not be empty")
        if self.timeout_seconds <= 0:
            raise LlmProviderConfigError("PROVIDER_TIMEOUT_SECONDS must be positive")
        if self.max_retries < 0:
            raise LlmProviderConfigError("PROVIDER_MAX_RETRIES must be >= 0")
        if self.max_tokens <= 0:
            raise LlmProviderConfigError("RAG_MAX_OUTPUT_TOKENS must be positive")
        if self.draft_schema_version not in ("v1", "v2"):
            raise LlmProviderConfigError("draft_schema_version must be v1 or v2")

    @classmethod
    def from_env(
        cls,
        *,
        draft_schema_version: CitationDraftSchemaVersion = "v1",
    ) -> "SolarPro3ProviderConfig":
        return cls(
            credential=os.environ.get("UPSTAGE_API_KEY", ""),
            base_url=os.environ.get("UPSTAGE_BASE_URL", DEFAULT_UPSTAGE_BASE_URL),
            model_id=os.environ.get("UPSTAGE_CHAT_MODEL", DEFAULT_SOLAR_PRO_3_MODEL_ID),
            timeout_seconds=_float_env(
                "PROVIDER_TIMEOUT_SECONDS",
                DEFAULT_SOLAR_PRO_3_TIMEOUT_SECONDS,
            ),
            max_retries=_int_env(
                "PROVIDER_MAX_RETRIES",
                DEFAULT_SOLAR_PRO_3_MAX_RETRIES,
            ),
            max_tokens=_int_env(
                "RAG_MAX_OUTPUT_TOKENS",
                DEFAULT_SOLAR_PRO_3_MAX_TOKENS,
            ),
            draft_schema_version=draft_schema_version,
        )

    @property
    def endpoint(self) -> str:
        return f"{self.base_url.rstrip('/')}/chat/completions"

    @property
    def provider_config_id(self) -> str:
        payload = {
            "base_url": self.base_url.rstrip("/"),
            "model_id": self.model_id,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "reasoning_effort": self.reasoning_effort,
            "structured_output": f"citation_rag_draft_schema_{self.draft_schema_version}",
        }
        digest = hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"),
        ).hexdigest()[:10]
        return f"solar-pro-3-{digest}"

    @property
    def public_config_summary(self) -> dict[str, str | int | float | bool]:
        return {
            "provider": "solar_pro_3",
            "base_url_alias": _public_endpoint_alias(self.base_url.rstrip("/")),
            "model_id": self.model_id,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "reasoning_effort": self.reasoning_effort,
            "response_format": "json_schema",
            "draft_schema_version": self.draft_schema_version,
            "api_key_source": "environment",
        }


class SolarPro3CitationDraftProvider:
    def __init__(
        self,
        *,
        config: SolarPro3ProviderConfig,
        client: httpx.Client | None = None,
    ) -> None:
        self.config = config
        self._client = client

    @property
    def provider_config_id(self) -> str:
        return self.config.provider_config_id

    def generate_draft(self, request: CitationDraftRequest) -> CitationDraftResult:
        payload = self._build_request_payload(request)
        start = time.perf_counter()
        call_count = 0
        response_payload: dict[str, Any] | None = None
        last_error: Exception | None = None
        for attempt in range(self.config.max_retries + 1):
            call_count += 1
            try:
                response_payload = self._post(payload)
                break
            except LlmProviderRequestError as exc:
                last_error = exc
                if not _should_retry_error(exc) or attempt >= self.config.max_retries:
                    raise
        if response_payload is None:
            raise LlmProviderRequestError("Solar Pro 3 request failed") from last_error
        latency_ms = round((time.perf_counter() - start) * 1000, 6)
        content = _extract_message_content(response_payload)
        draft = _parse_citation_draft(
            content,
            schema_version=self.config.draft_schema_version,
        )
        usage_payload = response_payload.get("usage", {})
        usage = LlmProviderUsage(
            latency_ms=latency_ms,
            api_call_count=call_count,
            prompt_tokens=_safe_int(usage_payload.get("prompt_tokens")),
            completion_tokens=_safe_int(usage_payload.get("completion_tokens")),
            total_tokens=_safe_int(usage_payload.get("total_tokens")),
            estimated_cost=_estimate_cost(
                usage_payload=usage_payload,
                config=self.config,
            ),
        )
        return CitationDraftResult(
            provider="solar_pro_3",
            model_id=str(response_payload.get("model") or self.config.model_id),
            provider_config_id=self.provider_config_id,
            draft=draft,
            usage=usage,
            raw_response_id=_safe_str_or_none(response_payload.get("id")),
            finish_reason=_extract_finish_reason(response_payload),
        )

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        client = self._client or httpx.Client(timeout=self.config.timeout_seconds)
        close_client = self._client is None
        try:
            response = client.post(
                self.config.endpoint,
                headers={
                    "Authorization": f"Bearer {self.config.credential}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        except httpx.TimeoutException as exc:
            raise LlmProviderRequestError("Solar Pro 3 request timed out") from exc
        except httpx.HTTPError as exc:
            raise LlmProviderRequestError("Solar Pro 3 request failed") from exc
        finally:
            if close_client:
                client.close()
        if response.status_code in RETRYABLE_STATUS_CODES:
            raise LlmProviderRequestError(
                f"Solar Pro 3 retryable status: {response.status_code}",
            )
        if response.status_code >= 400:
            raise LlmProviderRequestError(
                f"Solar Pro 3 non-retryable status: {response.status_code}",
            )
        try:
            parsed = response.json()
        except ValueError as exc:
            raise LlmProviderResponseError("Solar Pro 3 response is not JSON") from exc
        if not isinstance(parsed, dict):
            raise LlmProviderResponseError("Solar Pro 3 response must be a JSON object")
        return parsed

    def _build_request_payload(self, request: CitationDraftRequest) -> dict[str, Any]:
        return {
            "model": self.config.model_id,
            "messages": [
                {
                    "role": "system",
                    "content": _system_prompt(self.config.draft_schema_version),
                },
                {
                    "role": "user",
                    "content": _user_prompt(
                        request,
                        schema_version=self.config.draft_schema_version,
                    ),
                },
            ],
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
            "reasoning_effort": self.config.reasoning_effort,
            "stream": False,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": _structured_output_name(self.config.draft_schema_version),
                    "strict": True,
                    "schema": _structured_output_schema(self.config.draft_schema_version),
                },
            },
        }


def build_solar_provider_public_rows(
    *,
    config: SolarPro3ProviderConfig,
    result: CitationDraftResult,
    live_call_count: int = 0,
) -> list[dict[str, Any]]:
    return [
        {
            "provider": result.provider,
            "model_id": result.model_id,
            "provider_config_id": result.provider_config_id,
            "endpoint_alias": _public_endpoint_alias(config.endpoint),
            "response_format": "json_schema",
            "mock_call_count": result.usage.api_call_count,
            "live_call_count": live_call_count,
            "draft_schema_valid": True,
            "finish_reason": result.finish_reason,
            "latency_ms": result.usage.latency_ms,
            "prompt_tokens": result.usage.prompt_tokens,
            "completion_tokens": result.usage.completion_tokens,
            "total_tokens": result.usage.total_tokens,
            "estimated_cost": result.usage.estimated_cost,
        },
    ]


def _system_prompt(schema_version: CitationDraftSchemaVersion) -> str:
    base_prompt = (
        "당신은 서울/한양 역사 관광 도슨트 RAG 시스템의 답변 초안 작성자입니다. "
        "반드시 제공된 evidence 안에서만 답하고, 모르면 과장하지 않습니다. "
        "화면용 answer와 음성용 spoken_answer를 분리합니다."
    )
    if schema_version == "v1":
        return base_prompt
    return (
        base_prompt
        + " CitationRagDraftV2에서는 실제로 사용한 evidence rank만 "
        "used_evidence_pack_ranks에 기록합니다."
    )


def _user_prompt(
    request: CitationDraftRequest,
    *,
    schema_version: CitationDraftSchemaVersion,
) -> str:
    place_text = ", ".join(request.place_ids) if request.place_ids else "unknown"
    prompt = (
        f"query_id: {request.query_id}\n"
        f"query_type: {request.query_type}\n"
        f"language: {request.language}\n"
        f"place_ids: {place_text}\n"
        f"question: {request.query_text}\n\n"
        "evidence:" + "\n"
        f"{request.evidence_context}\n\n"
        "작성 규칙:\n"
        "- answer는 근거 기반 설명으로 작성합니다.\n"
        "- spoken_answer는 현장에서 듣기 쉬운 짧은 문장으로 작성합니다.\n"
        "- evidence 밖 추론이 섞이면 unsupported_claim_risk를 medium 이상으로 둡니다.\n"
        "- JSON schema만 반환합니다."
    )
    if schema_version == "v1":
        return prompt
    evidence_rank_text = _available_evidence_rank_text(request.evidence_context)
    return (
        prompt
        + "\n"
        + "- used_evidence_pack_ranks는 답변 작성에 실제 사용한 evidence rank만 오름차순으로 넣습니다.\n"
        + "- used_evidence_pack_ranks에는 evidence_context의 [evidence:N]에 존재하는 N만 넣습니다.\n"
        + "- 화면용 answer는 선택한 evidence만 근거로 삼고, 음성용 spoken_answer에는 citation 표기, 대괄호, URL을 넣지 않습니다.\n"
        + "- coverage_intent는 focused, multi_evidence, abstain 중 하나입니다.\n"
        + f"- 사용 가능한 evidence rank: {evidence_rank_text}\n"
    )


def _extract_message_content(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise LlmProviderResponseError("Solar Pro 3 response choices are empty")
    first = choices[0]
    if not isinstance(first, dict):
        raise LlmProviderResponseError("Solar Pro 3 choice must be an object")
    message = first.get("message")
    if not isinstance(message, dict):
        raise LlmProviderResponseError("Solar Pro 3 message must be an object")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise LlmProviderResponseError("Solar Pro 3 message content is empty")
    return content


def _extract_finish_reason(payload: dict[str, Any]) -> str | None:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    first = choices[0]
    if not isinstance(first, dict):
        return None
    return _safe_str_or_none(first.get("finish_reason"))


def _parse_citation_draft(
    content: str,
    *,
    schema_version: CitationDraftSchemaVersion,
) -> CitationRagDraft:
    try:
        parsed = json.loads(content)
    except ValueError as exc:
        raise LlmProviderResponseError("Solar Pro 3 content is not valid JSON") from exc
    try:
        if schema_version == "v2":
            return CitationRagDraftV2.model_validate(parsed)
        return CitationRagDraft.model_validate(parsed)
    except ValueError as exc:
        raise LlmProviderResponseError("Solar Pro 3 draft schema validation failed") from exc


def _structured_output_name(schema_version: CitationDraftSchemaVersion) -> str:
    if schema_version == "v2":
        return "citation_rag_draft_v2"
    return "citation_rag_draft"


def _structured_output_schema(schema_version: CitationDraftSchemaVersion) -> dict[str, object]:
    if schema_version == "v2":
        return _provider_compatible_v2_schema()
    return build_citation_rag_draft_schema()


def _provider_compatible_v2_schema() -> dict[str, object]:
    schema = build_citation_rag_draft_v2_schema()
    properties = schema.get("properties")
    if isinstance(properties, dict):
        ranks_schema = properties.get("used_evidence_pack_ranks")
        if isinstance(ranks_schema, dict):
            # Solar Pro 3 validates the response again locally; keep the provider
            # schema conservative to avoid provider-side JSON Schema subset issues.
            ranks_schema.pop("uniqueItems", None)
    return schema


def _available_evidence_rank_text(evidence_context: str) -> str:
    ranks = sorted(
        {
            int(match.group(1))
            for match in re.finditer(r"\[evidence:(\d+)\]", evidence_context)
        },
    )
    if not ranks:
        return "unknown"
    return ", ".join(str(rank) for rank in ranks)


def _should_retry_error(exc: LlmProviderRequestError) -> bool:
    message = str(exc)
    return (
        "Solar Pro 3 retryable status" in message
        or "timed out" in message
    )


def _public_endpoint_alias(endpoint: str) -> str:
    return endpoint.replace("https://", "").replace("http://", "")


def _safe_int(value: Any) -> int:
    if isinstance(value, int):
        return max(value, 0)
    if isinstance(value, float):
        return max(int(value), 0)
    return 0


def _safe_str_or_none(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _estimate_cost(
    *,
    usage_payload: Any,
    config: SolarPro3ProviderConfig,
) -> float:
    if not isinstance(usage_payload, dict):
        return 0.0
    input_tokens = _safe_int(usage_payload.get("prompt_tokens"))
    output_tokens = _safe_int(usage_payload.get("completion_tokens"))
    return round(
        (input_tokens / 1000 * config.cost_per_1k_input_tokens)
        + (output_tokens / 1000 * config.cost_per_1k_output_tokens),
        6,
    )


def _int_env(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None or not value.strip():
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise LlmProviderConfigError(f"{name} must be an integer") from exc


def _float_env(name: str, default: float) -> float:
    value = os.environ.get(name)
    if value is None or not value.strip():
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise LlmProviderConfigError(f"{name} must be a number") from exc
