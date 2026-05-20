from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.application.chat_retrieval import ChatRetrievalMode, ChatRetrievalUnavailableError
from app.application.chat_service import (
    ChatActiveRouteMode,
    ChatProviderMode,
    ChatProviderUnavailableError,
)
from app.application.voice_local_runtime import (
    LOCAL_VOICE_RUNTIME_CONTRACT_VERSION,
    LocalVoiceRuntimeRequest,
    LocalVoiceRuntimeResult,
    LocalVoiceRuntimeService,
    LocalVoiceRuntimeValidationError,
)
from app.domain.generation import AnswerProviderKind, UnsupportedClaimRisk
from app.domain.retrieval import LanguageCode, QueryType


router = APIRouter(prefix="/api/v1", tags=["voice"])
_SERVICE = LocalVoiceRuntimeService()


class VoiceApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LocalVoiceRuntimeApiRequest(VoiceApiModel):
    request_id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9._-]+$")
    input_audio_path: str = Field(min_length=1, max_length=240)
    fallback_transcript_text: str = Field(min_length=1, max_length=1000)
    language: LanguageCode = "ko"
    query_type: QueryType = "place_story"
    place_context: tuple[str, ...] = Field(default_factory=tuple, max_length=10)
    retrieval_mode: ChatRetrievalMode = "contract_only"
    provider_mode: ChatProviderMode = "contract_only"
    active_route_mode: ChatActiveRouteMode = "disabled"
    execute_local_stt: bool = False
    execute_local_tts: bool = False

    @field_validator("input_audio_path")
    @classmethod
    def reject_absolute_or_traversal_path(cls, value: str) -> str:
        normalized = value.replace("\\", "/")
        if ":" in normalized or normalized.startswith("/") or ".." in normalized.split("/"):
            raise ValueError("input_audio_path must be a relative private artifact path")
        return normalized

    def to_runtime_request(self) -> LocalVoiceRuntimeRequest:
        return LocalVoiceRuntimeRequest(
            request_id=self.request_id,
            input_audio_path=self.input_audio_path,
            fallback_transcript_text=self.fallback_transcript_text,
            language=self.language,
            query_type=self.query_type,
            place_context=self.place_context,
            retrieval_mode=self.retrieval_mode,
            provider_mode=self.provider_mode,
            active_route_mode=self.active_route_mode,
            execute_local_stt=self.execute_local_stt,
            execute_local_tts=self.execute_local_tts,
        )


class LocalVoiceRuntimeApiResponse(VoiceApiModel):
    contract_version: str = LOCAL_VOICE_RUNTIME_CONTRACT_VERSION
    runtime_id: str
    request_id: str
    resolved_device: str
    stt_provider_candidate_id: str
    tts_provider_candidate_id: str
    input_audio_artifact_id: str
    input_audio_artifact_private: bool
    input_audio_duration_ms: float
    transcript_source: str
    stt_execution_status: str
    transcript_hash: str
    chat_contract_status: str
    answer: str
    spoken_answer: str
    citation_count: int
    abstained: bool
    unsupported_claim_risk: UnsupportedClaimRisk
    provider: AnswerProviderKind
    model_id: str
    output_tts_execution_status: str
    output_audio_artifact_id: str
    output_audio_artifact_private: bool
    external_provider_call_count: int
    external_audio_transmission_count: int
    live_solar_call_count: int
    public_allowed: bool = True

    @classmethod
    def from_runtime_result(cls, result: LocalVoiceRuntimeResult) -> "LocalVoiceRuntimeApiResponse":
        return cls(
            runtime_id=result.runtime_id,
            request_id=result.request_id,
            resolved_device=result.resolved_device,
            stt_provider_candidate_id=result.stt_provider_candidate_id,
            tts_provider_candidate_id=result.tts_provider_candidate_id,
            input_audio_artifact_id=result.input_audio.artifact_id,
            input_audio_artifact_private=result.input_audio.artifact_private,
            input_audio_duration_ms=result.input_audio.duration_ms,
            transcript_source=result.transcript.transcript_source,
            stt_execution_status=result.transcript.stt_execution_status,
            transcript_hash=result.transcript.transcript_hash,
            chat_contract_status=result.chat_contract_status,
            answer=result.answer,
            spoken_answer=result.spoken_answer,
            citation_count=result.citation_count,
            abstained=result.abstained,
            unsupported_claim_risk=result.unsupported_claim_risk,
            provider=result.provider,
            model_id=result.model_id,
            output_tts_execution_status=result.output_tts_execution_status,
            output_audio_artifact_id=result.output_audio_artifact_id,
            output_audio_artifact_private=result.output_audio_artifact_private,
            external_provider_call_count=result.external_provider_call_count,
            external_audio_transmission_count=result.external_audio_transmission_count,
            live_solar_call_count=result.live_solar_call_count,
        )


def get_local_voice_runtime_service() -> LocalVoiceRuntimeService:
    return _SERVICE


def local_voice_runtime_enabled() -> bool:
    return os.getenv("HISTORY_DOCENT_ENABLE_LOCAL_VOICE_DEMO") == "1"


@router.post(
    "/voice/local-runtime",
    response_model=LocalVoiceRuntimeApiResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"description": "Invalid local voice input"},
        403: {"description": "Local voice demo endpoint disabled"},
        503: {"description": "Provider or retrieval unavailable"},
    },
)
def local_voice_runtime(
    request: LocalVoiceRuntimeApiRequest,
    service: LocalVoiceRuntimeService = Depends(get_local_voice_runtime_service),
) -> LocalVoiceRuntimeApiResponse:
    if not local_voice_runtime_enabled():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "local_voice_runtime_disabled",
                "message": "Local voice runtime endpoint is disabled.",
            },
        )
    try:
        result = service.handle(request.to_runtime_request())
    except LocalVoiceRuntimeValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": exc.code,
                "message": "Invalid local voice input.",
            },
        ) from exc
    except ChatProviderUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "provider_unavailable",
                "message": str(exc),
            },
        ) from exc
    except ChatRetrievalUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "retrieval_unavailable",
                "message": str(exc),
            },
        ) from exc
    return LocalVoiceRuntimeApiResponse.from_runtime_result(result)
