from __future__ import annotations

import hashlib
import time
import wave
from collections.abc import Callable
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.application.chat_service import ChatCommand, ChatProviderMode
from app.application.chat_retrieval import ChatRetrievalMode
from app.core.project_paths import is_repository_private_write_path, project_path
from app.domain.retrieval import LanguageCode, QueryType


LOCAL_VOICE_ADAPTER_CONTRACT_VERSION = "local-voice-adapter/v1"
LOCAL_VOICE_ADAPTER_ID = "local_voice_adapter_v1"
LOCAL_STT_PROVIDER_CANDIDATE_ID = "local_faster_whisper_small_cuda"
LOCAL_STT_RUNTIME_FAMILY = "faster-whisper via CTranslate2"
LOCAL_TTS_PROVIDER_CANDIDATE_ID = "local_windows_sapi_pyttsx3_korean_fallback"
LOCAL_STT_MODEL_ID = "small"
LOCAL_TTS_RUNTIME_FAMILY = "Windows SAPI via pyttsx3"
LOCAL_TTS_PROVIDER_ROLE = "fallback"
LOCAL_TTS_PROVIDER_STATUS = "fallback_not_quality_candidate"
LOCAL_TTS_FINAL_PROVIDER = False

TranscriptSource = Literal["public_safe_fixture", "local_faster_whisper", "local_whisper"]
TtsExecutionStatus = Literal[
    "executed",
    "blocked_no_korean_sapi_voice",
    "blocked_sapi_runtime_error",
    "skipped_by_flag",
]

SapiTextSynthesizer = Callable[[str, Path, str], None]


class LocalVoiceAdapterBase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LocalVoiceAdapterConfig(LocalVoiceAdapterBase):
    adapter_id: str = LOCAL_VOICE_ADAPTER_ID
    contract_version: str = LOCAL_VOICE_ADAPTER_CONTRACT_VERSION
    stt_provider_candidate_id: str = LOCAL_STT_PROVIDER_CANDIDATE_ID
    stt_runtime_family: str = LOCAL_STT_RUNTIME_FAMILY
    stt_model_id: str = LOCAL_STT_MODEL_ID
    tts_provider_candidate_id: str = LOCAL_TTS_PROVIDER_CANDIDATE_ID
    tts_runtime_family: str = LOCAL_TTS_RUNTIME_FAMILY
    tts_provider_role: str = LOCAL_TTS_PROVIDER_ROLE
    tts_provider_status: str = LOCAL_TTS_PROVIDER_STATUS
    tts_final_provider: bool = LOCAL_TTS_FINAL_PROVIDER
    claim_boundary: str = "local-smoke-only"


class LocalVoiceTranscriptInput(LocalVoiceAdapterBase):
    request_id: str = Field(min_length=1)
    transcript_text: str = Field(min_length=1, max_length=1000)
    transcript_source: TranscriptSource
    language: LanguageCode = "ko"
    query_type: QueryType = "place_fact"
    place_context: tuple[str, ...] = Field(default_factory=tuple)
    retrieval_mode: ChatRetrievalMode = "contract_only"
    provider_mode: ChatProviderMode = "contract_only"


class LocalVoiceChatBridge(LocalVoiceAdapterBase):
    request_id: str = Field(min_length=1)
    adapter_id: str = LOCAL_VOICE_ADAPTER_ID
    transcript_source: TranscriptSource
    transcript_hash: str = Field(min_length=8)
    transcript_char_count: int = Field(ge=0)
    stt_provider_candidate_id: str = LOCAL_STT_PROVIDER_CANDIDATE_ID
    stt_runtime_family: str = LOCAL_STT_RUNTIME_FAMILY
    stt_model_id: str = LOCAL_STT_MODEL_ID
    voice_mode: bool = True
    retrieval_mode: ChatRetrievalMode
    provider_mode: ChatProviderMode
    chat_command: ChatCommand


class LocalVoiceTtsInput(LocalVoiceAdapterBase):
    request_id: str = Field(min_length=1)
    spoken_answer: str = Field(min_length=1)
    language: LanguageCode = "ko"


class LocalSapiVoiceProbe(LocalVoiceAdapterBase):
    voice_available: bool
    voice_name: str
    voice_id_hash: str
    voice_language: str


class LocalVoiceTtsResult(LocalVoiceAdapterBase):
    request_id: str = Field(min_length=1)
    provider_candidate_id: str = LOCAL_TTS_PROVIDER_CANDIDATE_ID
    runtime_family: str = LOCAL_TTS_RUNTIME_FAMILY
    provider_role: str = LOCAL_TTS_PROVIDER_ROLE
    provider_status: str = LOCAL_TTS_PROVIDER_STATUS
    final_provider: bool = LOCAL_TTS_FINAL_PROVIDER
    synthesis_status: TtsExecutionStatus
    latency_ms: float = Field(ge=0.0)
    audio_duration_ms: float = Field(ge=0.0)
    audio_file_size_bytes: int = Field(ge=0)
    audio_artifact_private: bool
    spoken_answer_hash: str = Field(min_length=8)
    error_code: str


class LocalVoiceAdapter:
    def __init__(
        self,
        *,
        config: LocalVoiceAdapterConfig | None = None,
        voice_probe: LocalSapiVoiceProbe | None = None,
        sapi_text_synthesizer: SapiTextSynthesizer | None = None,
    ) -> None:
        self.config = config or LocalVoiceAdapterConfig()
        self.voice_probe = voice_probe
        self.sapi_text_synthesizer = sapi_text_synthesizer or synthesize_text_with_pyttsx3_sapi

    def build_chat_command(self, transcript_input: LocalVoiceTranscriptInput) -> LocalVoiceChatBridge:
        command = ChatCommand(
            request_id=transcript_input.request_id,
            query=transcript_input.transcript_text,
            language=transcript_input.language,
            query_type=transcript_input.query_type,
            place_context=transcript_input.place_context,
            voice_mode=True,
            retrieval_mode=transcript_input.retrieval_mode,
            provider_mode=transcript_input.provider_mode,
            active_route_mode="disabled",
        )
        return LocalVoiceChatBridge(
            request_id=transcript_input.request_id,
            transcript_source=transcript_input.transcript_source,
            transcript_hash=stable_digest(transcript_input.transcript_text),
            transcript_char_count=len(transcript_input.transcript_text),
            stt_provider_candidate_id=self.config.stt_provider_candidate_id,
            stt_runtime_family=self.config.stt_runtime_family,
            stt_model_id=self.config.stt_model_id,
            retrieval_mode=transcript_input.retrieval_mode,
            provider_mode=transcript_input.provider_mode,
            chat_command=command,
        )

    def synthesize_spoken_answer(
        self,
        tts_input: LocalVoiceTtsInput,
        *,
        output_path: Path,
        execute_tts: bool,
    ) -> LocalVoiceTtsResult:
        if not execute_tts:
            return build_tts_result(
                tts_input=tts_input,
                status="skipped_by_flag",
                latency_ms=0.0,
                output_path=output_path,
                audio_artifact_private=False,
                error_code="",
            )

        resolved_output_path = project_path(output_path)
        if not is_repository_private_write_path(resolved_output_path):
            raise ValueError("local voice TTS output must be under repository private_data")

        voice_probe = self.voice_probe or probe_windows_sapi_korean_voice()
        if not voice_probe.voice_available:
            return build_tts_result(
                tts_input=tts_input,
                status="blocked_no_korean_sapi_voice",
                latency_ms=0.0,
                output_path=resolved_output_path,
                audio_artifact_private=False,
                error_code="sapi_korean_voice_missing",
            )

        try:
            started = time.perf_counter()
            self.sapi_text_synthesizer(tts_input.spoken_answer, resolved_output_path, voice_probe.voice_name)
            latency_ms = round((time.perf_counter() - started) * 1000.0, 6)
        except Exception:
            return build_tts_result(
                tts_input=tts_input,
                status="blocked_sapi_runtime_error",
                latency_ms=0.0,
                output_path=resolved_output_path,
                audio_artifact_private=False,
                error_code="sapi_synthesis_error",
            )

        if not resolved_output_path.exists() or not resolved_output_path.stat().st_size:
            return build_tts_result(
                tts_input=tts_input,
                status="blocked_sapi_runtime_error",
                latency_ms=0.0,
                output_path=resolved_output_path,
                audio_artifact_private=False,
                error_code="sapi_output_missing",
            )

        return build_tts_result(
            tts_input=tts_input,
            status="executed",
            latency_ms=latency_ms,
            output_path=resolved_output_path,
            audio_artifact_private=True,
            error_code="",
        )


def build_tts_result(
    *,
    tts_input: LocalVoiceTtsInput,
    status: TtsExecutionStatus,
    latency_ms: float,
    output_path: Path,
    audio_artifact_private: bool,
    error_code: str,
) -> LocalVoiceTtsResult:
    audio_duration_ms = read_wav_duration_ms(output_path) if audio_artifact_private else 0.0
    audio_file_size_bytes = output_path.stat().st_size if audio_artifact_private else 0
    return LocalVoiceTtsResult(
        request_id=tts_input.request_id,
        synthesis_status=status,
        latency_ms=latency_ms,
        audio_duration_ms=audio_duration_ms,
        audio_file_size_bytes=audio_file_size_bytes,
        audio_artifact_private=audio_artifact_private,
        spoken_answer_hash=stable_digest(tts_input.spoken_answer),
        error_code=error_code,
    )


def probe_windows_sapi_korean_voice() -> LocalSapiVoiceProbe:
    try:
        import pyttsx3

        engine = pyttsx3.init()
        voices = engine.getProperty("voices")
    except Exception:
        return LocalSapiVoiceProbe(
            voice_available=False,
            voice_name="",
            voice_id_hash="",
            voice_language="",
        )
    selected_voice = next((voice for voice in voices if is_korean_sapi_voice(voice)), None)
    if selected_voice is None:
        return LocalSapiVoiceProbe(
            voice_available=False,
            voice_name="",
            voice_id_hash="",
            voice_language="",
        )
    voice_id = str(getattr(selected_voice, "id", ""))
    languages = getattr(selected_voice, "languages", [])
    language = ",".join(str(language) for language in languages) or "ko-KR"
    return LocalSapiVoiceProbe(
        voice_available=True,
        voice_name=str(getattr(selected_voice, "name", "Korean SAPI Voice")),
        voice_id_hash=stable_digest(voice_id),
        voice_language=language,
    )


def is_korean_sapi_voice(voice: object) -> bool:
    name = str(getattr(voice, "name", "")).lower()
    voice_id = str(getattr(voice, "id", "")).lower()
    languages = " ".join(str(language).lower() for language in getattr(voice, "languages", []))
    return any(
        marker in f"{name} {voice_id} {languages}"
        for marker in ("ko", "korean", "heami")
    )


def synthesize_text_with_pyttsx3_sapi(text: str, output_path: Path, voice_name: str) -> None:
    import pyttsx3

    output_path.parent.mkdir(parents=True, exist_ok=True)
    engine = pyttsx3.init()
    voices = engine.getProperty("voices")
    selected_voice = next(
        (voice for voice in voices if getattr(voice, "name", "") == voice_name),
        None,
    )
    if selected_voice is None:
        selected_voice = next((voice for voice in voices if is_korean_sapi_voice(voice)), None)
    if selected_voice is None:
        raise RuntimeError("sapi_korean_voice_missing")
    engine.setProperty("voice", selected_voice.id)
    engine.setProperty("rate", 165)
    engine.save_to_file(text, str(output_path))
    engine.runAndWait()


def read_wav_duration_ms(path: Path) -> float:
    if not path.exists() or not path.stat().st_size:
        return 0.0
    with wave.open(str(path), "rb") as wav_file:
        frame_rate = wav_file.getframerate()
        frame_count = wav_file.getnframes()
    if frame_rate <= 0:
        return 0.0
    return round((frame_count / frame_rate) * 1000.0, 6)


def stable_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
