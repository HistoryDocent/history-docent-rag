from __future__ import annotations

import hashlib
import importlib.util
import time
import wave
from pathlib import Path
from typing import Literal, Protocol, cast

from pydantic import BaseModel, ConfigDict, Field

from app.application.chat_service import (
    ChatActiveRouteMode,
    ChatContractService,
    ChatProviderMode,
)
from app.application.chat_retrieval import ChatRetrievalMode
from app.application.voice_local_adapter import (
    LOCAL_STT_MODEL_ID,
    LOCAL_STT_PROVIDER_CANDIDATE_ID,
    LOCAL_STT_RUNTIME_FAMILY,
    LOCAL_TTS_FINAL_PROVIDER,
    LOCAL_TTS_PROVIDER_CANDIDATE_ID,
    LOCAL_TTS_PROVIDER_ROLE,
    LOCAL_TTS_PROVIDER_STATUS,
    LOCAL_TTS_RUNTIME_FAMILY,
    LOCAL_VOICE_ADAPTER_ID,
    LocalSapiVoiceProbe,
    LocalVoiceAdapter,
    LocalVoiceTranscriptInput,
    LocalVoiceTtsInput,
    SapiTextSynthesizer,
    TranscriptSource,
    read_wav_duration_ms,
)
from app.core.project_paths import is_repository_private_artifact_path, project_path
from app.domain.generation import AnswerProviderKind, UnsupportedClaimRisk
from app.domain.retrieval import LanguageCode, QueryType
from app.infrastructure.index.device import resolve_torch_device


LOCAL_VOICE_RUNTIME_CONTRACT_VERSION = "local-voice-runtime/v1"
LOCAL_VOICE_RUNTIME_ID = "local_voice_runtime_v1"
DEFAULT_MAX_AUDIO_BYTES = 10 * 1024 * 1024
DEFAULT_MAX_AUDIO_DURATION_MS = 30_000.0

VoiceRuntimeSttStatus = Literal[
    "executed",
    "skipped_by_flag",
    "blocked_missing_runtime",
    "blocked_runtime_error",
]
VoiceRuntimeTtsStatus = Literal[
    "executed",
    "blocked_no_korean_sapi_voice",
    "blocked_sapi_runtime_error",
    "skipped_by_flag",
]


class LocalVoiceRuntimeModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LocalVoiceRuntimeConfig(LocalVoiceRuntimeModel):
    contract_version: str = LOCAL_VOICE_RUNTIME_CONTRACT_VERSION
    runtime_id: str = LOCAL_VOICE_RUNTIME_ID
    adapter_id: str = LOCAL_VOICE_ADAPTER_ID
    max_input_audio_bytes: int = Field(default=DEFAULT_MAX_AUDIO_BYTES, ge=1)
    max_input_audio_duration_ms: float = Field(
        default=DEFAULT_MAX_AUDIO_DURATION_MS,
        gt=0.0,
    )
    output_audio_dir: Path = Path("private_data") / "voice" / "local_runtime_output_audio"


class LocalVoiceRuntimeRequest(LocalVoiceRuntimeModel):
    request_id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9._-]+$")
    input_audio_path: Path
    fallback_transcript_text: str = Field(min_length=1, max_length=1000)
    language: LanguageCode = "ko"
    query_type: QueryType = "place_story"
    place_context: tuple[str, ...] = Field(default_factory=tuple)
    retrieval_mode: ChatRetrievalMode = "contract_only"
    provider_mode: ChatProviderMode = "contract_only"
    active_route_mode: ChatActiveRouteMode = "disabled"
    execute_local_stt: bool = False
    execute_local_tts: bool = False


class LocalVoiceAudioInput(LocalVoiceRuntimeModel):
    artifact_id: str = Field(min_length=8)
    artifact_private: bool
    file_size_bytes: int = Field(ge=0)
    duration_ms: float = Field(ge=0.0)
    validation_status: str = Field(min_length=1)


class LocalVoiceTranscriptRuntime(LocalVoiceRuntimeModel):
    transcript_source: str = Field(min_length=1)
    stt_execution_status: VoiceRuntimeSttStatus
    stt_latency_ms: float = Field(ge=0.0)
    transcript_hash: str = Field(min_length=8)
    transcript_char_count: int = Field(ge=0)
    error_code: str


class LocalVoiceRuntimeResult(LocalVoiceRuntimeModel):
    contract_version: str = LOCAL_VOICE_RUNTIME_CONTRACT_VERSION
    runtime_id: str = LOCAL_VOICE_RUNTIME_ID
    adapter_id: str = LOCAL_VOICE_ADAPTER_ID
    request_id: str = Field(min_length=1)
    resolved_device: str = Field(min_length=1)
    stt_provider_candidate_id: str = LOCAL_STT_PROVIDER_CANDIDATE_ID
    stt_runtime_family: str = LOCAL_STT_RUNTIME_FAMILY
    stt_model_id: str = LOCAL_STT_MODEL_ID
    tts_provider_candidate_id: str = LOCAL_TTS_PROVIDER_CANDIDATE_ID
    tts_runtime_family: str = LOCAL_TTS_RUNTIME_FAMILY
    tts_provider_role: str = LOCAL_TTS_PROVIDER_ROLE
    tts_provider_status: str = LOCAL_TTS_PROVIDER_STATUS
    tts_final_provider: bool = LOCAL_TTS_FINAL_PROVIDER
    input_audio: LocalVoiceAudioInput
    transcript: LocalVoiceTranscriptRuntime
    chat_contract_status: str = Field(min_length=1)
    chat_latency_ms: float = Field(ge=0.0)
    chat_request_id: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    spoken_answer: str = Field(min_length=1)
    citation_count: int = Field(ge=0)
    abstained: bool
    unsupported_claim_risk: UnsupportedClaimRisk
    provider: AnswerProviderKind
    model_id: str = Field(min_length=1)
    output_tts_execution_status: VoiceRuntimeTtsStatus
    output_tts_latency_ms: float = Field(ge=0.0)
    output_audio_artifact_id: str
    output_audio_artifact_private: bool
    output_audio_duration_ms: float = Field(ge=0.0)
    output_audio_file_size_bytes: int = Field(ge=0)
    spoken_answer_hash: str = Field(min_length=8)
    external_provider_call_count: int = Field(ge=0)
    external_audio_transmission_count: int = Field(ge=0)
    live_stt_call_count: int = Field(ge=0)
    live_tts_call_count: int = Field(ge=0)
    live_solar_call_count: int = Field(ge=0)
    error_code: str


class LocalVoiceRuntimeValidationError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class LocalVoiceTranscriber(Protocol):
    def transcribe(
        self,
        *,
        audio_path: Path,
        language: LanguageCode,
        resolved_device: str,
    ) -> str:
        ...


class FasterWhisperSmallTranscriber:
    def __init__(self, *, model_id: str = LOCAL_STT_MODEL_ID) -> None:
        self.model_id = model_id
        self._model = None
        self._model_runtime_key = ""

    def transcribe(
        self,
        *,
        audio_path: Path,
        language: LanguageCode,
        resolved_device: str,
    ) -> str:
        if importlib.util.find_spec("faster_whisper") is None:
            raise LocalVoiceRuntimeValidationError("local_faster_whisper_runtime_missing")
        model = self._load_model(resolved_device)
        segments, _info = model.transcribe(
            str(audio_path),
            language="ko" if language in {"ko", "mixed"} else "en",
        )
        return " ".join(segment.text.strip() for segment in segments).strip()

    def _load_model(self, resolved_device: str):
        compute_type = "float16" if resolved_device == "cuda" else "int8"
        runtime_key = f"{resolved_device}:{compute_type}"
        if self._model is None or self._model_runtime_key != runtime_key:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(
                self.model_id,
                device=resolved_device,
                compute_type=compute_type,
            )
            self._model_runtime_key = runtime_key
        return self._model


WhisperSmallTranscriber = FasterWhisperSmallTranscriber


class LocalVoiceRuntimeService:
    def __init__(
        self,
        *,
        config: LocalVoiceRuntimeConfig | None = None,
        adapter: LocalVoiceAdapter | None = None,
        chat_service: ChatContractService | None = None,
        transcriber: LocalVoiceTranscriber | None = None,
        voice_probe: LocalSapiVoiceProbe | None = None,
        sapi_text_synthesizer: SapiTextSynthesizer | None = None,
        resolved_device: str | None = None,
    ) -> None:
        self.config = config or LocalVoiceRuntimeConfig()
        self.adapter = adapter or LocalVoiceAdapter(
            voice_probe=voice_probe,
            sapi_text_synthesizer=sapi_text_synthesizer,
        )
        self.chat_service = chat_service or ChatContractService()
        self.transcriber = transcriber or FasterWhisperSmallTranscriber()
        self.resolved_device = resolved_device or resolve_torch_device("cuda_if_available")

    def handle(self, request: LocalVoiceRuntimeRequest) -> LocalVoiceRuntimeResult:
        audio = validate_local_voice_audio_input(
            request.input_audio_path,
            max_bytes=self.config.max_input_audio_bytes,
            max_duration_ms=self.config.max_input_audio_duration_ms,
        )
        transcript_text, transcript = self._build_transcript(request, audio_path=project_path(request.input_audio_path))
        bridge = self.adapter.build_chat_command(
            LocalVoiceTranscriptInput(
                request_id=request.request_id,
                transcript_text=transcript_text,
                transcript_source=cast(TranscriptSource, transcript.transcript_source),
                language=request.language,
                query_type=request.query_type,
                place_context=request.place_context,
                retrieval_mode=request.retrieval_mode,
                provider_mode=request.provider_mode,
            )
        )
        chat_started = time.perf_counter()
        chat_result = self.chat_service.handle(
            bridge.chat_command.model_copy(
                update={"active_route_mode": request.active_route_mode},
            ),
        )
        chat_latency_ms = round((time.perf_counter() - chat_started) * 1000.0, 6)
        tts_result = self.adapter.synthesize_spoken_answer(
            LocalVoiceTtsInput(
                request_id=request.request_id,
                spoken_answer=chat_result.answer.spoken_answer,
                language=request.language,
            ),
            output_path=self._output_audio_path(request.request_id),
            execute_tts=request.execute_local_tts,
        )
        output_artifact_id = (
            stable_digest_text(f"{request.request_id}:{tts_result.spoken_answer_hash}")
            if tts_result.audio_artifact_private
            else ""
        )
        return LocalVoiceRuntimeResult(
            request_id=request.request_id,
            resolved_device=self.resolved_device,
            stt_runtime_family=self.adapter.config.stt_runtime_family,
            tts_runtime_family=self.adapter.config.tts_runtime_family,
            tts_provider_role=self.adapter.config.tts_provider_role,
            tts_provider_status=self.adapter.config.tts_provider_status,
            tts_final_provider=self.adapter.config.tts_final_provider,
            input_audio=audio,
            transcript=transcript,
            chat_contract_status="executed_contract_chat",
            chat_latency_ms=chat_latency_ms,
            chat_request_id=chat_result.request_id,
            answer=chat_result.answer.answer,
            spoken_answer=chat_result.answer.spoken_answer,
            citation_count=len(chat_result.answer.citations),
            abstained=chat_result.answer.abstained,
            unsupported_claim_risk=chat_result.answer.unsupported_claim_risk,
            provider=chat_result.answer.provider,
            model_id=chat_result.answer.model_id,
            output_tts_execution_status=tts_result.synthesis_status,
            output_tts_latency_ms=tts_result.latency_ms,
            output_audio_artifact_id=output_artifact_id,
            output_audio_artifact_private=tts_result.audio_artifact_private,
            output_audio_duration_ms=tts_result.audio_duration_ms,
            output_audio_file_size_bytes=tts_result.audio_file_size_bytes,
            spoken_answer_hash=tts_result.spoken_answer_hash,
            external_provider_call_count=0,
            external_audio_transmission_count=0,
            live_stt_call_count=0,
            live_tts_call_count=0,
            live_solar_call_count=chat_result.usage.solar_call_count,
            error_code=transcript.error_code or tts_result.error_code,
        )

    def _build_transcript(
        self,
        request: LocalVoiceRuntimeRequest,
        *,
        audio_path: Path,
    ) -> tuple[str, LocalVoiceTranscriptRuntime]:
        if not request.execute_local_stt:
            return request.fallback_transcript_text, LocalVoiceTranscriptRuntime(
                transcript_source="public_safe_fixture",
                stt_execution_status="skipped_by_flag",
                stt_latency_ms=0.0,
                transcript_hash=stable_digest_text(request.fallback_transcript_text),
                transcript_char_count=len(request.fallback_transcript_text),
                error_code="",
            )
        try:
            started = time.perf_counter()
            transcript_text = self.transcriber.transcribe(
                audio_path=audio_path,
                language=request.language,
                resolved_device=self.resolved_device,
            )
            latency_ms = round((time.perf_counter() - started) * 1000.0, 6)
        except LocalVoiceRuntimeValidationError as exc:
            return request.fallback_transcript_text, LocalVoiceTranscriptRuntime(
                transcript_source="public_safe_fixture",
                stt_execution_status="blocked_missing_runtime",
                stt_latency_ms=0.0,
                transcript_hash=stable_digest_text(request.fallback_transcript_text),
                transcript_char_count=len(request.fallback_transcript_text),
                error_code=exc.code,
            )
        except Exception:
            return request.fallback_transcript_text, LocalVoiceTranscriptRuntime(
                transcript_source="public_safe_fixture",
                stt_execution_status="blocked_runtime_error",
                stt_latency_ms=0.0,
                transcript_hash=stable_digest_text(request.fallback_transcript_text),
                transcript_char_count=len(request.fallback_transcript_text),
                error_code="local_faster_whisper_transcribe_error",
            )
        transcript_text = transcript_text or request.fallback_transcript_text
        return transcript_text, LocalVoiceTranscriptRuntime(
            transcript_source="local_faster_whisper",
            stt_execution_status="executed",
            stt_latency_ms=latency_ms,
            transcript_hash=stable_digest_text(transcript_text),
            transcript_char_count=len(transcript_text),
            error_code="",
        )

    def _output_audio_path(self, request_id: str) -> Path:
        return project_path(self.config.output_audio_dir) / f"{request_id}.wav"


def validate_local_voice_audio_input(
    input_audio_path: Path,
    *,
    max_bytes: int = DEFAULT_MAX_AUDIO_BYTES,
    max_duration_ms: float = DEFAULT_MAX_AUDIO_DURATION_MS,
) -> LocalVoiceAudioInput:
    if input_audio_path.is_absolute():
        raise LocalVoiceRuntimeValidationError("absolute_audio_path_not_allowed")
    if any(part == ".." for part in input_audio_path.parts):
        raise LocalVoiceRuntimeValidationError("path_traversal_not_allowed")
    if input_audio_path.suffix.lower() != ".wav":
        raise LocalVoiceRuntimeValidationError("unsupported_audio_extension")
    resolved = project_path(input_audio_path)
    if not is_repository_private_artifact_path(input_audio_path):
        raise LocalVoiceRuntimeValidationError("public_audio_path_not_allowed")
    if not resolved.exists():
        raise LocalVoiceRuntimeValidationError("audio_file_missing")
    file_size = resolved.stat().st_size
    if file_size <= 0:
        raise LocalVoiceRuntimeValidationError("audio_file_empty")
    if file_size > max_bytes:
        raise LocalVoiceRuntimeValidationError("audio_file_too_large")
    try:
        duration_ms = read_wav_duration_ms(resolved)
    except (EOFError, wave.Error):
        raise LocalVoiceRuntimeValidationError("invalid_wav_file") from None
    if duration_ms <= 0.0:
        raise LocalVoiceRuntimeValidationError("invalid_wav_file")
    if duration_ms > max_duration_ms:
        raise LocalVoiceRuntimeValidationError("audio_duration_too_long")
    return LocalVoiceAudioInput(
        artifact_id=stable_digest_text(f"{resolved.name}:{file_size}:{duration_ms:.3f}"),
        artifact_private=True,
        file_size_bytes=file_size,
        duration_ms=duration_ms,
        validation_status="accepted_private_wav",
    )


def public_voice_runtime_row(result: LocalVoiceRuntimeResult) -> dict[str, object]:
    return {
        "contract_version": result.contract_version,
        "runtime_id": result.runtime_id,
        "adapter_id": result.adapter_id,
        "request_id": result.request_id,
        "resolved_device": result.resolved_device,
        "stt_provider_candidate_id": result.stt_provider_candidate_id,
        "stt_runtime_family": result.stt_runtime_family,
        "stt_model_id": result.stt_model_id,
        "tts_provider_candidate_id": result.tts_provider_candidate_id,
        "tts_runtime_family": result.tts_runtime_family,
        "tts_provider_role": result.tts_provider_role,
        "tts_provider_status": result.tts_provider_status,
        "tts_final_provider": result.tts_final_provider,
        "input_audio_artifact_id": result.input_audio.artifact_id,
        "input_audio_artifact_private": result.input_audio.artifact_private,
        "input_audio_file_size_bytes": result.input_audio.file_size_bytes,
        "input_audio_duration_ms": result.input_audio.duration_ms,
        "input_audio_validation_status": result.input_audio.validation_status,
        "transcript_source": result.transcript.transcript_source,
        "stt_execution_status": result.transcript.stt_execution_status,
        "stt_latency_ms": result.transcript.stt_latency_ms,
        "transcript_hash": result.transcript.transcript_hash,
        "transcript_char_count": result.transcript.transcript_char_count,
        "chat_contract_status": result.chat_contract_status,
        "chat_latency_ms": result.chat_latency_ms,
        "citation_count": result.citation_count,
        "abstained": result.abstained,
        "unsupported_claim_risk": result.unsupported_claim_risk,
        "provider": result.provider,
        "model_id": result.model_id,
        "output_tts_execution_status": result.output_tts_execution_status,
        "output_tts_latency_ms": result.output_tts_latency_ms,
        "output_audio_artifact_id": result.output_audio_artifact_id,
        "output_audio_artifact_private": result.output_audio_artifact_private,
        "output_audio_duration_ms": result.output_audio_duration_ms,
        "output_audio_file_size_bytes": result.output_audio_file_size_bytes,
        "spoken_answer_hash": result.spoken_answer_hash,
        "external_provider_call_count": result.external_provider_call_count,
        "external_audio_transmission_count": result.external_audio_transmission_count,
        "live_stt_call_count": result.live_stt_call_count,
        "live_tts_call_count": result.live_tts_call_count,
        "live_solar_call_count": result.live_solar_call_count,
        "error_code": result.error_code,
    }


def stable_digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
