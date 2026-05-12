from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.domain.generation import CitationRagDraft, UnsupportedClaimRisk
from app.domain.retrieval import QueryType


class LlmProviderModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CitationDraftRequest(LlmProviderModel):
    query_id: str = Field(min_length=1)
    query_type: QueryType
    query_text: str = Field(min_length=1, max_length=1000)
    evidence_context: str = Field(min_length=1, max_length=12000)
    place_ids: tuple[str, ...] = Field(default_factory=tuple)
    language: str = Field(default="ko", min_length=2, max_length=16)


class LlmProviderUsage(LlmProviderModel):
    latency_ms: float = Field(default=0.0, ge=0.0)
    api_call_count: int = Field(default=0, ge=0)
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    estimated_cost: float = Field(default=0.0, ge=0.0)


class CitationDraftResult(LlmProviderModel):
    provider: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    provider_config_id: str = Field(min_length=1)
    draft: CitationRagDraft
    usage: LlmProviderUsage
    raw_response_id: str | None = None
    finish_reason: str | None = None


class CitationDraftProvider(Protocol):
    @property
    def provider_config_id(self) -> str:
        raise NotImplementedError

    def generate_draft(self, request: CitationDraftRequest) -> CitationDraftResult:
        raise NotImplementedError


class LlmProviderError(RuntimeError):
    pass


class LlmProviderConfigError(LlmProviderError):
    pass


class LlmProviderRequestError(LlmProviderError):
    pass


class LlmProviderResponseError(LlmProviderError):
    pass


@dataclass(frozen=True)
class StaticCitationDraftProvider:
    draft: CitationRagDraft
    provider: str = "fake"
    model_id: str = "fake-model"
    config_id: str = "fake-provider-v1"

    @property
    def provider_config_id(self) -> str:
        return self.config_id

    def generate_draft(self, request: CitationDraftRequest) -> CitationDraftResult:
        return CitationDraftResult(
            provider=self.provider,
            model_id=self.model_id,
            provider_config_id=self.config_id,
            draft=self.draft,
            usage=LlmProviderUsage(),
            finish_reason="mock",
        )


def build_citation_rag_draft_schema() -> dict[str, object]:
    return {
        "type": "object",
        "properties": {
            "answer": {
                "type": "string",
                "minLength": 1,
                "maxLength": 4000,
            },
            "spoken_answer": {
                "type": "string",
                "minLength": 1,
                "maxLength": 1200,
            },
            "unsupported_claim_risk": {
                "type": "string",
                "enum": list(UnsupportedClaimRisk.__args__),
            },
        },
        "required": ["answer", "spoken_answer", "unsupported_claim_risk"],
        "additionalProperties": False,
    }
