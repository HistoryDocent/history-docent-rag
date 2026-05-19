from __future__ import annotations

import json
import re
import wave
from pathlib import Path

from pipelines.voice_local_tts_runtime_install_retry import (
    FALLBACK_PROVIDER_ID,
    WORK_ID,
    SapiVoiceProbe,
    collect_retry_failures,
    run_voice_local_tts_runtime_install_retry,
)
from pipelines.voice_stt_tts_local_tts_smoke import VoiceTtsSmokeScript


DOC_PATH = Path("docs/VOICE_LOCAL_TTS_RUNTIME_INSTALL_RETRY.md")
REPORT_PATH = Path("evals/reports/voice_local_tts_runtime_install_retry_report.md")
README_PATH = Path("README.md")
TODO_PATH = Path("docs/TODO.md")
LEDGER_PATH = Path("docs/RAG_DECISION_LEDGER.md")
CHECKLIST_PATH = Path("docs/CHECKLIST.md")
WBS_PATH = Path("docs/WBS.md")
ROADMAP_PATH = Path("docs/ROADMAP.md")
PROVIDER_DECISION_PATH = Path("docs/VOICE_PROVIDER_DECISION.md")
SCRIPTS_PATH = Path("data_samples/voice_tts_smoke_scripts.sample.jsonl")
REQUIRED_LINKS = (
    "docs/VOICE_LOCAL_TTS_RUNTIME_INSTALL_RETRY.md",
    "evals/reports/voice_local_tts_runtime_install_retry_report.md",
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
    PROVIDER_DECISION_PATH,
)
FORBIDDEN_CLAIMS = (
    "MeloTTS가 최종 provider로 확정",
    "pyttsx3가 최종 provider로 확정",
    "무료 로컬 TTS 품질 검증 완료",
    "production 음성 관광 앱 완성",
)


def _fake_voice_probe() -> SapiVoiceProbe:
    return SapiVoiceProbe(
        voice_available=True,
        voice_name="Fake Korean SAPI Voice",
        voice_id_hash="fake-voice",
        voice_language="ko-KR",
    )


def _fake_sapi_synthesizer(
    scripts: tuple[VoiceTtsSmokeScript, ...],
    audio_dir: Path,
    voice_name: str,
) -> None:
    assert voice_name == "Fake Korean SAPI Voice"
    audio_dir.mkdir(parents=True, exist_ok=True)
    for script in scripts:
        with wave.open(str(audio_dir / f"{script.script_id}.wav"), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            wav_file.writeframes(b"\x00\x00" * 320)


def test_local_tts_runtime_retry_runner_executes_injected_sapi(
    tmp_path: Path,
) -> None:
    report = run_voice_local_tts_runtime_install_retry(
        doc_path=tmp_path / "VOICE_LOCAL_TTS_RUNTIME_INSTALL_RETRY.md",
        report_path=tmp_path / "voice_local_tts_runtime_install_retry_report.md",
        result_rows_path=tmp_path / "voice_local_tts_runtime_install_retry_rows.jsonl",
        private_audio_dir=tmp_path / "audio",
        execute_sapi_tts=True,
        voice_probe=_fake_voice_probe(),
        sapi_synthesizer=_fake_sapi_synthesizer,
    )

    assert collect_retry_failures(report) == []
    assert report.summary.selected_script_count == 5
    assert report.summary.runtime_install_attempt_count >= 10
    assert report.summary.package_install_attempted_count >= 4
    assert report.summary.cuda_wheel_install_success_count == 1
    assert report.summary.dictionary_download_success_count == 1
    assert report.summary.melotts_import_available_count == 1
    assert report.summary.melotts_synthesis_attempt_count == 1
    assert report.summary.melotts_synthesis_success_count == 0
    assert report.summary.melotts_blocker_count >= 1
    assert report.summary.sapi_korean_voice_detected_count == 1
    assert report.summary.fallback_sapi_synthesis_attempt_count == 5
    assert report.summary.local_tts_execution_count == 5
    assert report.summary.private_audio_generated_count == 5
    assert report.summary.private_audio_saved_count == 5
    assert report.summary.audio_duration_total_ms > 0
    assert report.summary.audio_file_size_total_bytes > 0
    assert report.summary.selected_provider_candidate_id == FALLBACK_PROVIDER_ID
    assert report.summary.external_provider_call_count == 0
    assert report.summary.external_audio_transmission_count == 0
    assert report.summary.live_stt_call_count == 0
    assert report.summary.live_tts_call_count == 0
    assert report.summary.live_solar_call_count == 0
    assert report.summary.raw_audio_public_artifact_count == 0
    assert report.summary.raw_transcript_public_artifact_count == 0
    assert report.summary.client_secret_exposure_count == 0
    assert report.summary.public_private_path_leakage_count == 0
    assert report.summary.public_secret_like_leakage_count == 0
    assert report.summary.public_raw_payload_leakage_count == 0
    assert report.summary.retry_decision == "completed_local_sapi_tts_fallback"

    rows = [
        json.loads(line)
        for line in (tmp_path / "voice_local_tts_runtime_install_retry_rows.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(rows) == report.summary.runtime_install_attempt_count + 5
    assert all("script_text" not in row for row in rows)
    assert all("raw_audio" not in row for row in rows)
    assert all("raw_transcript" not in row for row in rows)
    assert all("audio_path" not in row for row in rows)


def test_local_tts_runtime_retry_docs_are_registered_and_public_safe() -> None:
    assert DOC_PATH.exists()
    assert REPORT_PATH.exists()
    assert SCRIPTS_PATH.exists()

    readme = README_PATH.read_text(encoding="utf-8")
    todo = TODO_PATH.read_text(encoding="utf-8")
    ledger = LEDGER_PATH.read_text(encoding="utf-8")

    for link in REQUIRED_LINKS:
        assert link in readme
        assert Path(link).exists()

    assert "- [x] local TTS runtime candidate install/retry from matrix" in todo
    assert "- [x] local MeloTTS runtime install and retry smoke execution" in todo
    assert WORK_ID in ledger
    assert "voice_local_tts_runtime_install_retry" in ledger

    for path in PUBLIC_SCAN_PATHS:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)
        assert "private_data/" not in text


def test_local_tts_runtime_retry_report_records_quantitative_gates() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert WORK_ID in doc
    assert WORK_ID in report
    assert "runtime_install_attempt_count | 11" in report
    assert "melotts_import_available_count | 1" in report
    assert "melotts_synthesis_success_count | 0" in report
    assert "sapi_korean_voice_detected_count | 1" in report
    assert "fallback_sapi_synthesis_attempt_count | 5" in report
    assert "local_tts_execution_count | 5" in report
    assert "private_audio_generated_count | 5" in report
    assert "external_provider_call_count | 0" in report
    assert "external_audio_transmission_count | 0" in report
    assert "live_stt_call_count | 0" in report
    assert "live_tts_call_count | 0" in report
    assert "live_solar_call_count | 0" in report
    assert "raw_audio_public_artifact_count | 0" in report
    assert "raw_transcript_public_artifact_count | 0" in report
    assert "client_secret_exposure_count | 0" in report
    assert "resolved_device | `cuda`" in report
    assert "isolated_cuda_torch_available_count | 1" in report
    assert f"selected_provider_candidate_id | `{FALLBACK_PROVIDER_ID}`" in report
    assert "External audit | PASS" in report


def test_local_tts_runtime_retry_keeps_forbidden_claims_forbidden() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    forbidden_section = doc.split("## Claim Boundary", maxsplit=1)[1]

    for claim in FORBIDDEN_CLAIMS:
        assert claim in forbidden_section
