from __future__ import annotations

import json
import re
import wave
from pathlib import Path

from app.application.voice_local_adapter import LocalSapiVoiceProbe
from pipelines.voice_local_e2e_eval import (
    WORK_ID,
    collect_voice_local_e2e_failures,
    run_voice_local_e2e_eval,
)


DOC_PATH = Path("docs/VOICE_LOCAL_E2E_EVAL.md")
REPORT_PATH = Path("evals/reports/voice_local_e2e_eval_report.md")
README_PATH = Path("README.md")
TODO_PATH = Path("docs/TODO.md")
LEDGER_PATH = Path("docs/RAG_DECISION_LEDGER.md")
CHECKLIST_PATH = Path("docs/CHECKLIST.md")
WBS_PATH = Path("docs/WBS.md")
ROADMAP_PATH = Path("docs/ROADMAP.md")
PROVIDER_DECISION_PATH = Path("docs/VOICE_PROVIDER_DECISION.md")
REQUIRED_LINKS = (
    "docs/VOICE_LOCAL_E2E_EVAL.md",
    "evals/reports/voice_local_e2e_eval_report.md",
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
    "production 음성 관광 앱 완성",
    "STT/TTS 품질 최종 검증 완료",
    "실제 관광객 음성 품질 검증 완료",
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


def test_voice_local_e2e_runner_executes_injected_local_tts() -> None:
    report = run_voice_local_e2e_eval(
        doc_path=Path("private_data") / "test_outputs" / "voice_local_e2e_doc.md",
        report_path=Path("private_data") / "test_outputs" / "voice_local_e2e_report.md",
        result_rows_path=Path("private_data")
        / "test_outputs"
        / "voice_local_e2e_rows.jsonl",
        private_input_audio_dir=Path("private_data")
        / "test_outputs"
        / "voice_local_e2e_input_audio",
        private_output_audio_dir=Path("private_data")
        / "test_outputs"
        / "voice_local_e2e_output_audio",
        execute_local_stt=False,
        execute_local_tts=True,
        voice_probe=_fake_voice_probe(),
        sapi_text_synthesizer=_fake_sapi_text_synthesizer,
    )

    assert collect_voice_local_e2e_failures(report, require_local_execution=False) == []
    assert report.summary.selected_script_count == 30
    assert report.summary.public_safe_script_count == 30
    assert report.summary.query_type_count == 6
    assert report.summary.script_per_query_type_min_count == 5
    assert report.summary.input_tts_generation_count == 30
    assert report.summary.output_tts_generation_count == 30
    assert report.summary.private_input_audio_generated_count == 30
    assert report.summary.private_output_audio_generated_count == 30
    assert report.summary.chat_contract_execution_count == 30
    assert report.summary.expected_behavior_pass_count == 30
    assert report.summary.external_provider_call_count == 0
    assert report.summary.external_audio_transmission_count == 0
    assert report.summary.raw_audio_public_artifact_count == 0
    assert report.summary.raw_transcript_public_artifact_count == 0
    assert report.summary.public_private_path_leakage_count == 0
    assert report.summary.public_secret_like_leakage_count == 0
    assert report.summary.public_raw_payload_leakage_count == 0
    assert report.summary.e2e_decision == "completed_local_voice_e2e_regression"

    rows = [
        json.loads(line)
        for line in (Path("private_data") / "test_outputs" / "voice_local_e2e_rows.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(rows) == 36
    assert all("script_text" not in row for row in rows)
    assert all("raw_audio" not in row for row in rows)
    assert all("raw_transcript" not in row for row in rows)
    assert all("audio_path" not in row for row in rows)


def test_voice_local_e2e_docs_are_registered_and_public_safe() -> None:
    assert DOC_PATH.exists()
    assert REPORT_PATH.exists()

    readme = README_PATH.read_text(encoding="utf-8")
    todo = TODO_PATH.read_text(encoding="utf-8")
    ledger = LEDGER_PATH.read_text(encoding="utf-8")

    for link in REQUIRED_LINKS:
        assert link in readme
        assert Path(link).exists()

    assert "- [x] local voice E2E regression evaluation" in todo
    assert WORK_ID in ledger
    assert "voice_local_e2e_eval" in ledger

    for path in PUBLIC_SCAN_PATHS:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)
        assert "private_data/" not in text


def test_voice_local_e2e_report_records_quantitative_gates() -> None:
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert WORK_ID in report
    assert "selected_script_count | 30" in report
    assert "query_type_count | 6" in report
    assert "script_per_query_type_min_count | 5" in report
    assert "input_tts_generation_count | 30" in report
    assert "local_stt_execution_count | 30" in report
    assert "local_cuda_whisper_call_count | 30" in report
    assert "chat_contract_execution_count | 30" in report
    assert "expected_behavior_pass_count | 30" in report
    assert "output_tts_generation_count | 30" in report
    assert "private_input_audio_generated_count | 30" in report
    assert "private_output_audio_generated_count | 30" in report
    assert "external_provider_call_count | 0" in report
    assert "external_audio_transmission_count | 0" in report
    assert "live_stt_call_count | 0" in report
    assert "live_tts_call_count | 0" in report
    assert "live_solar_call_count | 0" in report
    assert "raw_audio_public_artifact_count | 0" in report
    assert "raw_transcript_public_artifact_count | 0" in report
    assert "External audit | PASS" in report


def test_voice_local_e2e_keeps_forbidden_claims_forbidden() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    forbidden_section = doc.split("## Claim Boundary", maxsplit=1)[1]

    for claim in FORBIDDEN_CLAIMS:
        assert claim in forbidden_section
