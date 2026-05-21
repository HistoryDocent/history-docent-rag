from __future__ import annotations

import wave
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.app import create_app
from app.api.v1.voice import get_local_voice_runtime_service
from app.application.voice_local_adapter import LocalSapiVoiceProbe
from app.application.voice_local_runtime import (
    LOCAL_VOICE_RUNTIME_CONTRACT_VERSION,
    LocalVoiceRuntimeRequest,
    LocalVoiceRuntimeService,
    LocalVoiceRuntimeValidationError,
    public_voice_runtime_row,
    validate_local_voice_audio_input,
)


def _write_test_wav(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(b"\x00\x00" * 1600)


def _fake_voice_probe() -> LocalSapiVoiceProbe:
    return LocalSapiVoiceProbe(
        voice_available=True,
        voice_name="Fake Korean SAPI Voice",
        voice_id_hash="fake-voice",
        voice_language="ko-KR",
    )


def _fake_sapi_text_synthesizer(text: str, output_path: Path, voice_name: str) -> None:
    assert text
    assert voice_name == "Fake Korean SAPI Voice"
    _write_test_wav(output_path)


def _service() -> LocalVoiceRuntimeService:
    return LocalVoiceRuntimeService(
        voice_probe=_fake_voice_probe(),
        sapi_text_synthesizer=_fake_sapi_text_synthesizer,
        resolved_device="cuda",
    )


def test_local_voice_runtime_service_accepts_private_wav_and_returns_public_safe_row() -> None:
    audio_path = Path("private_data") / "test_outputs" / "voice_runtime_input.wav"
    _write_test_wav(audio_path)

    result = _service().handle(
        LocalVoiceRuntimeRequest(
            request_id="voice-runtime-unit",
            input_audio_path=audio_path,
            fallback_transcript_text="경복궁은 왜 조선의 중심 궁궐이었어?",
            language="ko",
            query_type="place_fact",
            place_context=("gyeongbokgung",),
            execute_local_stt=False,
            execute_local_tts=True,
        )
    )

    assert result.contract_version == LOCAL_VOICE_RUNTIME_CONTRACT_VERSION
    assert result.stt_provider_candidate_id == "local_faster_whisper_small_cuda"
    assert result.stt_runtime_family == "faster-whisper via CTranslate2"
    assert result.tts_provider_role == "fallback"
    assert result.tts_provider_status == "fallback_not_quality_candidate"
    assert result.tts_final_provider is False
    assert result.input_audio.artifact_private is True
    assert result.transcript.stt_execution_status == "skipped_by_flag"
    assert result.transcript.transcript_source == "public_safe_fixture"
    assert result.chat_contract_status == "executed_contract_chat"
    assert result.citation_count == 1
    assert result.output_tts_execution_status == "executed"
    assert result.output_audio_artifact_private is True
    assert result.external_provider_call_count == 0
    assert result.external_audio_transmission_count == 0
    assert result.live_solar_call_count == 0

    public_row = public_voice_runtime_row(result)
    assert "answer" not in public_row
    assert "spoken_answer" not in public_row
    assert "fallback_transcript_text" not in public_row
    assert "input_audio_path" not in public_row
    assert public_row["input_audio_artifact_private"] is True
    assert public_row["tts_final_provider"] is False
    assert public_row["tts_provider_status"] == "fallback_not_quality_candidate"


def test_local_voice_runtime_audio_validation_rejects_unsafe_inputs() -> None:
    public_wav = Path(".pytest_cache") / "voice_runtime_public.wav"
    _write_test_wav(public_wav)

    cases = {
        Path("private_data") / ".." / "private_data" / "audio.wav": "path_traversal_not_allowed",
        public_wav: "public_audio_path_not_allowed",
        Path("private_data") / "test_outputs" / "not_audio.txt": (
            "unsupported_audio_extension"
        ),
    }

    for path, expected_code in cases.items():
        try:
            validate_local_voice_audio_input(path)
        except LocalVoiceRuntimeValidationError as exc:
            assert exc.code == expected_code
        else:
            raise AssertionError(f"expected validation error for {expected_code}")


def test_local_voice_runtime_api_is_disabled_by_default() -> None:
    response = TestClient(create_app(), raise_server_exceptions=False).post(
        "/api/v1/voice/local-runtime",
        json={
            "request_id": "voice-api-disabled",
            "input_audio_path": "private_data/test_outputs/missing.wav",
            "fallback_transcript_text": "경복궁 설명",
        },
    )

    assert response.status_code == 403
    body = response.json()
    assert body["error"]["code"] == "local_voice_runtime_disabled"
    assert "traceback" not in str(body).lower()


def test_local_voice_runtime_api_executes_when_explicitly_enabled(monkeypatch) -> None:
    audio_path = Path("private_data") / "test_outputs" / "voice_runtime_api_input.wav"
    _write_test_wav(audio_path)
    monkeypatch.setenv("HISTORY_DOCENT_ENABLE_LOCAL_VOICE_DEMO", "1")

    app = create_app()
    app.dependency_overrides[get_local_voice_runtime_service] = _service
    response = TestClient(app, raise_server_exceptions=False).post(
        "/api/v1/voice/local-runtime",
        json={
            "request_id": "voice-api-enabled",
            "input_audio_path": audio_path.as_posix(),
            "fallback_transcript_text": "경복궁은 왜 조선의 중심 궁궐이었어?",
            "language": "ko",
            "query_type": "place_fact",
            "place_context": ["gyeongbokgung"],
            "execute_local_tts": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["contract_version"] == LOCAL_VOICE_RUNTIME_CONTRACT_VERSION
    assert body["request_id"] == "voice-api-enabled"
    assert body["stt_provider_candidate_id"] == "local_faster_whisper_small_cuda"
    assert body["stt_runtime_family"] == "faster-whisper via CTranslate2"
    assert body["tts_provider_role"] == "fallback"
    assert body["tts_provider_status"] == "fallback_not_quality_candidate"
    assert body["tts_final_provider"] is False
    assert body["input_audio_artifact_private"] is True
    assert body["stt_execution_status"] == "skipped_by_flag"
    assert body["chat_contract_status"] == "executed_contract_chat"
    assert body["citation_count"] == 1
    assert body["output_tts_execution_status"] == "executed"
    assert body["external_provider_call_count"] == 0
    assert body["external_audio_transmission_count"] == 0
