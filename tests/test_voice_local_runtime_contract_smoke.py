from __future__ import annotations

import json
import re
import wave
from pathlib import Path

from app.application.voice_local_adapter import LocalSapiVoiceProbe
from pipelines.voice_local_runtime_contract_smoke import (
    DEFAULT_SCRIPT_LIMIT,
    WORK_ID,
    collect_runtime_contract_failures,
    run_voice_local_runtime_contract_smoke,
)


DOC_PATH = Path("docs/VOICE_LOCAL_RUNTIME_CONTRACT.md")
REPORT_PATH = Path("evals/reports/voice_local_runtime_contract_report.md")
README_PATH = Path("README.md")
TODO_PATH = Path("docs/TODO.md")
LEDGER_PATH = Path("docs/RAG_DECISION_LEDGER.md")
CHECKLIST_PATH = Path("docs/CHECKLIST.md")
WBS_PATH = Path("docs/WBS.md")
ROADMAP_PATH = Path("docs/ROADMAP.md")
PROVIDER_DECISION_PATH = Path("docs/VOICE_PROVIDER_DECISION.md")
REQUIRED_LINKS = (
    "docs/VOICE_LOCAL_RUNTIME_CONTRACT.md",
    "evals/reports/voice_local_runtime_contract_report.md",
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
    "실제 관광객 음성 품질 검증 완료",
    "STT/TTS provider 최종 확정",
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
        wav_file.writeframes(b"\x00\x00" * 1600)


def test_voice_local_runtime_contract_smoke_runner_executes_with_injected_tts() -> None:
    report = run_voice_local_runtime_contract_smoke(
        doc_path=Path("private_data") / "test_outputs" / "voice_runtime_contract_doc.md",
        report_path=Path("private_data")
        / "test_outputs"
        / "voice_runtime_contract_report.md",
        result_rows_path=Path("private_data")
        / "test_outputs"
        / "voice_runtime_contract_rows.jsonl",
        private_input_audio_dir=Path("private_data")
        / "test_outputs"
        / "voice_runtime_contract_input_audio",
        private_output_audio_dir=Path("private_data")
        / "test_outputs"
        / "voice_runtime_contract_output_audio",
        execute_local_tts=True,
        voice_probe=_fake_voice_probe(),
        sapi_text_synthesizer=_fake_sapi_text_synthesizer,
    )

    assert collect_runtime_contract_failures(report) == []
    assert report.summary.selected_script_count == DEFAULT_SCRIPT_LIMIT
    assert report.summary.local_voice_runtime_contract_count == 1
    assert report.summary.api_route_contract_count == 1
    assert report.summary.accepted_audio_input_count == DEFAULT_SCRIPT_LIMIT
    assert report.summary.validation_reject_case_count == 3
    assert report.summary.validation_reject_pass_count == 3
    assert report.summary.chat_contract_execution_count == DEFAULT_SCRIPT_LIMIT
    assert report.summary.local_tts_execution_count == DEFAULT_SCRIPT_LIMIT
    assert report.summary.private_input_audio_generated_count == DEFAULT_SCRIPT_LIMIT
    assert report.summary.private_output_audio_generated_count == DEFAULT_SCRIPT_LIMIT
    assert report.summary.external_provider_call_count == 0
    assert report.summary.external_audio_transmission_count == 0
    assert report.summary.raw_audio_public_artifact_count == 0
    assert report.summary.raw_transcript_public_artifact_count == 0
    assert report.summary.public_private_path_leakage_count == 0
    assert report.summary.public_secret_like_leakage_count == 0
    assert report.summary.public_raw_payload_leakage_count == 0
    assert report.summary.runtime_decision == "completed_local_voice_runtime_contract"

    rows = [
        json.loads(line)
        for line in (Path("private_data") / "test_outputs" / "voice_runtime_contract_rows.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(rows) == DEFAULT_SCRIPT_LIMIT + 3
    assert all("fallback_transcript_text" not in row for row in rows)
    assert all("answer" not in row for row in rows)
    assert all("spoken_answer" not in row for row in rows)
    assert all("input_audio_path" not in row for row in rows)


def test_voice_local_runtime_contract_docs_are_registered_and_public_safe() -> None:
    assert DOC_PATH.exists()
    assert REPORT_PATH.exists()

    readme = README_PATH.read_text(encoding="utf-8")
    todo = TODO_PATH.read_text(encoding="utf-8")
    ledger = LEDGER_PATH.read_text(encoding="utf-8")

    for link in REQUIRED_LINKS:
        assert link in readme
        assert Path(link).exists()

    assert "- [x] local voice runtime contract" in todo
    assert WORK_ID in ledger
    assert "voice_local_runtime_contract" in ledger

    for path in PUBLIC_SCAN_PATHS:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)
        assert "private_data/" not in text


def test_voice_local_runtime_contract_report_records_quantitative_gates() -> None:
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert WORK_ID in report
    assert "selected_script_count | 5" in report
    assert "local_voice_runtime_contract_count | 1" in report
    assert "api_route_contract_count | 1" in report
    assert "accepted_audio_input_count | 5" in report
    assert "validation_reject_case_count | 3" in report
    assert "validation_reject_pass_count | 3" in report
    assert "chat_contract_execution_count | 5" in report
    assert "external_provider_call_count | 0" in report
    assert "external_audio_transmission_count | 0" in report
    assert "raw_audio_public_artifact_count | 0" in report
    assert "raw_transcript_public_artifact_count | 0" in report
    assert "External audit | PASS" in report


def test_voice_local_runtime_contract_keeps_forbidden_claims_forbidden() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    forbidden_section = doc.split("## Claim Boundary", maxsplit=1)[1]

    for claim in FORBIDDEN_CLAIMS:
        assert claim in forbidden_section
