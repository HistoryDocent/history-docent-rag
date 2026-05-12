from __future__ import annotations

import re
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.application.chat_service import (
    ChatCommand,
    ChatContractService,
    ChatProviderMode,
    ChatProviderUnavailableError,
    ChatServiceResult,
    ChatUsage,
)
from app.domain.generation import AnswerProviderKind, UnsupportedClaimRisk
from app.domain.retrieval import LanguageCode, QueryType


CHAT_API_CONTRACT_VERSION = "chat-api/v1"
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,80}$")
_PLACE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,79}$")

router = APIRouter(prefix="/api/v1", tags=["chat"])
_SERVICE = ChatContractService()


class ChatApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ChatRequest(ChatApiModel):
    request_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=80,
        pattern=r"^[A-Za-z0-9._-]+$",
    )
    query: str = Field(min_length=1, max_length=1000)
    language: LanguageCode = "ko"
    query_type: QueryType = "place_story"
    place_context: tuple[str, ...] = Field(default_factory=tuple, max_length=10)
    voice_mode: bool = False
    provider_mode: ChatProviderMode = "contract_only"

    @field_validator("request_id")
    @classmethod
    def validate_request_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not _REQUEST_ID_PATTERN.fullmatch(stripped):
            raise ValueError("request_id must use letters, numbers, dot, dash, underscore")
        return stripped

    @field_validator("query")
    @classmethod
    def strip_query(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("query must not be blank")
        return stripped

    @field_validator("place_context")
    @classmethod
    def validate_place_context(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        cleaned: list[str] = []
        for place_id in value:
            stripped = place_id.strip()
            if not _PLACE_ID_PATTERN.fullmatch(stripped):
                raise ValueError("place_context must contain catalog place ids")
            if stripped not in cleaned:
                cleaned.append(stripped)
        return tuple(cleaned)

    def to_command(self) -> ChatCommand:
        return ChatCommand(
            request_id=self.request_id or f"chat-{uuid.uuid4().hex[:12]}",
            query=self.query,
            language=self.language,
            query_type=self.query_type,
            place_context=self.place_context,
            voice_mode=self.voice_mode,
            provider_mode=self.provider_mode,
        )


class ChatCitation(ChatApiModel):
    citation_id: str = Field(min_length=1)
    evidence_id: str = Field(min_length=1)
    child_id: str = Field(min_length=1)
    parent_id: str = Field(min_length=1)
    doc_id: str = Field(min_length=1)
    source_rank: int = Field(ge=1)
    pack_rank: int = Field(ge=1)
    source_block_ids: tuple[str, ...] = Field(min_length=1)
    citation_block_ids: tuple[str, ...] = Field(min_length=1)
    citation_recoverable: bool


class ChatResponse(ChatApiModel):
    contract_version: str = CHAT_API_CONTRACT_VERSION
    rag_contract_version: str
    request_id: str = Field(min_length=1)
    query_id: str = Field(min_length=1)
    query_type: QueryType
    answer: str = Field(min_length=1)
    spoken_answer: str = Field(min_length=1)
    citations: tuple[ChatCitation, ...] = Field(default_factory=tuple)
    evidence_ids: tuple[str, ...] = Field(default_factory=tuple)
    place_ids: tuple[str, ...] = Field(default_factory=tuple)
    abstained: bool
    unsupported_claim_risk: UnsupportedClaimRisk
    provider: AnswerProviderKind
    model_id: str = Field(min_length=1)
    answer_policy_id: str = Field(min_length=1)
    latency_ms: float = Field(ge=0.0)
    usage: ChatUsage
    public_allowed: bool = True

    @classmethod
    def from_service_result(cls, result: ChatServiceResult) -> "ChatResponse":
        answer = result.answer
        return cls(
            rag_contract_version=answer.contract_version,
            request_id=result.request_id,
            query_id=answer.query_id,
            query_type=answer.query_type,
            answer=answer.answer,
            spoken_answer=answer.spoken_answer,
            citations=tuple(
                ChatCitation.model_validate(citation.model_dump(mode="json"))
                for citation in answer.citations
            ),
            evidence_ids=answer.evidence_ids,
            place_ids=answer.place_ids,
            abstained=answer.abstained,
            unsupported_claim_risk=answer.unsupported_claim_risk,
            provider=answer.provider,
            model_id=answer.model_id,
            answer_policy_id=answer.answer_policy_id,
            latency_ms=result.latency_ms,
            usage=result.usage,
        )


def get_chat_service() -> ChatContractService:
    return _SERVICE


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    responses={
        422: {"description": "Validation error"},
        503: {"description": "Provider unavailable"},
    },
)
def chat(
    request: ChatRequest,
    service: ChatContractService = Depends(get_chat_service),
) -> ChatResponse:
    try:
        result = service.handle(request.to_command())
    except ChatProviderUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "provider_unavailable",
                "message": str(exc),
            },
        ) from exc
    return ChatResponse.from_service_result(result)


def public_chat_response_row(response: dict[str, Any]) -> dict[str, Any]:
    usage = response.get("usage") if isinstance(response.get("usage"), dict) else {}
    citations = response.get("citations") if isinstance(response.get("citations"), list) else []
    return {
        "contract_version": response.get("contract_version"),
        "rag_contract_version": response.get("rag_contract_version"),
        "query_id": response.get("query_id"),
        "query_type": response.get("query_type"),
        "provider": response.get("provider"),
        "model_id": response.get("model_id"),
        "answer_policy_id": response.get("answer_policy_id"),
        "abstained": response.get("abstained"),
        "unsupported_claim_risk": response.get("unsupported_claim_risk"),
        "citation_count": len(citations),
        "evidence_id_count": len(response.get("evidence_ids", [])),
        "place_id_count": len(response.get("place_ids", [])),
        "latency_ms": response.get("latency_ms"),
        "solar_call_count": usage.get("solar_call_count"),
    }
