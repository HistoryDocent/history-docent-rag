from __future__ import annotations

import re
import wave
from pathlib import Path

from app.application.voice_local_adapter import (
    LOCAL_TTS_PROVIDER_CANDIDATE_ID,
    LocalSapiVoiceProbe,
    LocalVoiceAdapter,
    LocalVoiceTranscriptInput,
)
from pipelines.voice_stt_tts_local_adapter_integration import (
    WORK_ID,
    collect_integration_failures,
    run_voice_stt_tts_local_adapter_integration,
)


DOC_PATH = Path("docs/VOICE_STT_TTS_LOCAL_ADAPTER_INTEGRATION.md")
REPORT_PATH = Path("evals/reports/voice_stt_tts_local_adapter_integration_report.md")
README_PATH = Path("README.md")
TODO_PATH = Path("docs/TODO.md")
LEDGER_PATH = Path("docs/RAG_DECISION_LEDGER.md")
CHECKLIST_PATH = Path("docs/CHECKLIST.md")
WBS_PATH = Path("docs/WBS.md")
ROADMAP_PATH = Path("docs/ROADMAP.md")
REQUIRED_LINKS = (
    "docs/VOICE_STT_TTS_LOCAL_ADAPTER_INTEGRATION.md",
    "evals/reports/voice_stt_tts_local_adapter_integration_report.md",
)
PUBLIC_SCAN_PATHS = (
    README_PATH,
    DOC_PATH,
    REPORT_PATH,
    TODO_PATH,
    LEDGER_PATH,
    CHECKLIST_PATH,
    WBS_PATH,
    ROADMAP_PATH,
)
FORBIDDEN_CLAIMS = (
    "production 음성 관광 앱 완성",
    "STT/TTS 품질 최종 검증 완료",
    "MeloTTS가 최종 provider로 확정",
    "Windows SAPI가 최종 provider로 확정",
)


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
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(b"\x00\x00" * 640)


def test_local_voice_adapter_builds_chat_command_without_provider_calls() -> None:
    adapter = LocalVoiceAdapter(voice_probe=_fake_voice_probe())
    bridge = adapter.build_chat_command(
        LocalVoiceTranscriptInput(
            request_id="voice-adapter-unit",
            transcript_text="경복궁은 왜 조선의 중심 궁궐이었어?",
            transcript_source="public_safe_fixture",
            query_type="place_fact",
            place_context=("gyeongbokgung",),
        )
    )

    assert bridge.chat_command.voice_mode is True
    assert bridge.chat_command.provider_mode == "contract_only"
    assert bridge.chat_command.retrieval_mode == "contract_only"
    assert bridge.stt_model_id == "small"
    assert bridge.transcript_hash


def test_local_adapter_integration_runner_executes_injected_sapi() -> None:
    report = run_voice_stt_tts_local_adapter_integration(
        doc_path=Path("private_data") / "test_outputs" / "local_adapter_doc.md",
        report_path=Path("private_data") / "test_outputs" / "local_adapter_report.md",
        result_rows_path=Path("private_data")
        / "test_outputs"
        / "local_adapter_rows.jsonl",
        private_tts_audio_dir=Path("private_data") / "test_outputs" / "local_adapter_audio",
        execute_local_stt=False,
        execute_local_tts=True,
        voice_probe=_fake_voice_probe(),
        sapi_text_synthesizer=_fake_sapi_text_synthesizer,
    )

    assert collect_integration_failures(report) == []
    assert report.summary.selected_script_count == 5
    assert report.summary.local_voice_adapter_module_count == 1
    assert report.summary.local_stt_provider_candidate_count == 1
    assert report.summary.local_tts_provider_candidate_count == 1
    assert report.summary.chat_contract_execution_count == 5
    assert report.summary.local_tts_execution_count == 5
    assert report.summary.private_tts_audio_generated_count == 5
    assert report.summary.external_provider_call_count == 0
    assert report.summary.external_audio_transmission_count == 0
    assert report.summary.raw_audio_public_artifact_count == 0
    assert report.summary.raw_transcript_public_artifact_count == 0
    assert report.summary.integration_decision == "completed_local_voice_adapter_smoke"
    assert all(row.tts_provider_candidate_id == LOCAL_TTS_PROVIDER_CANDIDATE_ID for row in report.rows)
    assert all(row.spoken_answer_hash for row in report.rows)


def test_local_adapter_integration_docs_are_registered_and_public_safe() -> None:
    assert DOC_PATH.exists()
    assert REPORT_PATH.exists()

    readme = README_PATH.read_text(encoding="utf-8")
    todo = TODO_PATH.read_text(encoding="utf-8")
    ledger = LEDGER_PATH.read_text(encoding="utf-8")

    for link in REQUIRED_LINKS:
        assert link in readme
        assert Path(link).exists()

    assert "- [x] voice STT/TTS local adapter integration with selected local fallback" in todo
    assert WORK_ID in ledger
    assert "voice_stt_tts_local_adapter_integration" in ledger

    for path in PUBLIC_SCAN_PATHS:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)
        assert "private_data/" not in text


def test_local_adapter_integration_report_records_quantitative_gates() -> None:
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert WORK_ID in report
    assert "local_voice_adapter_module_count | 1" in report
    assert "local_stt_runtime_available_count | 1" in report
    assert "local_stt_execution_count | 5" in report
    assert "local_cuda_whisper_call_count | 5" in report
    assert "local_tts_execution_count | 5" in report
    assert "private_tts_audio_generated_count | 5" in report
    assert "chat_contract_execution_count | 5" in report
    assert "citation_response_count | 5" in report
    assert "external_provider_call_count | 0" in report
    assert "external_audio_transmission_count | 0" in report
    assert "live_stt_call_count | 0" in report
    assert "live_tts_call_count | 0" in report
    assert "live_solar_call_count | 0" in report
    assert "raw_audio_public_artifact_count | 0" in report
    assert "raw_transcript_public_artifact_count | 0" in report
    assert "External audit | PASS" in report


def test_local_adapter_integration_keeps_forbidden_claims_forbidden() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    forbidden_section = doc.split("## Claim Boundary", maxsplit=1)[1]

    for claim in FORBIDDEN_CLAIMS:
        assert claim in forbidden_section
