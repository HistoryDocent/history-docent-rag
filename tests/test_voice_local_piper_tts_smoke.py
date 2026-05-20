from __future__ import annotations

import json
import re
import wave
from pathlib import Path
from types import SimpleNamespace

import pipelines.voice_local_piper_tts_smoke as piper_smoke
from pipelines.voice_stt_tts_local_tts_smoke import VoiceTtsSmokeScript


DOC_PATH = Path("docs/VOICE_LOCAL_PIPER_TTS_SMOKE.md")
REPORT_PATH = Path("evals/reports/voice_local_piper_tts_smoke_report.md")
README_PATH = Path("README.md")
TODO_PATH = Path("docs/TODO.md")
LEDGER_PATH = Path("docs/RAG_DECISION_LEDGER.md")
CHECKLIST_PATH = Path("docs/CHECKLIST.md")
WBS_PATH = Path("docs/WBS.md")
ROADMAP_PATH = Path("docs/ROADMAP.md")
VOICE_DECISION_PATH = Path("docs/VOICE_PROVIDER_DECISION.md")
REQUIRED_LINKS = (
    "docs/VOICE_LOCAL_PIPER_TTS_SMOKE.md",
    "evals/reports/voice_local_piper_tts_smoke_report.md",
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
    VOICE_DECISION_PATH,
)
FORBIDDEN_CLAIMS = (
    "Piper가 Korean TTS provider로 채택됐다는 주장",
    "Piper 한국어 합성 품질 검증 완료",
    "무료 로컬 음성 관광 앱 완성",
    "실제 관광객 음성 품질 검증 완료",
)


def test_piper_tts_smoke_runner_public_safe_contract(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(piper_smoke, "is_piper_runtime_available", lambda: True)
    monkeypatch.setattr(piper_smoke, "get_distribution_version", lambda _: "1.4.2")
    monkeypatch.setattr(
        piper_smoke,
        "build_cuda_preflight",
        lambda: SimpleNamespace(
            resolved_device="cuda",
            local_cuda_available=True,
            cuda_device_count=1,
        ),
    )
    manifest = {
        "en_US-test-low": {"language": {"code": "en_US", "family": "en"}, "quality": "low"},
        "ja_JP-test-low": {"language": {"code": "ja_JP", "family": "ja"}, "quality": "low"},
    }

    report = piper_smoke.run_voice_local_piper_tts_smoke(
        doc_path=tmp_path / "VOICE_LOCAL_PIPER_TTS_SMOKE.md",
        report_path=tmp_path / "voice_local_piper_tts_smoke_report.md",
        result_rows_path=tmp_path / "voice_local_piper_tts_smoke_rows.jsonl",
        execute_local_tts=True,
        require_local_execution=False,
        package_install_attempted=True,
        voice_manifest_payload=manifest,
    )

    assert piper_smoke.collect_piper_tts_smoke_failures(
        report,
        require_local_execution=False,
    ) == []
    assert report.summary.selected_script_count == 5
    assert report.summary.piper_runtime_available_count == 1
    assert report.summary.piper_distribution_installed_count == 1
    assert report.summary.package_install_attempted_count == 1
    assert report.summary.manifest_voice_count == 2
    assert report.summary.manifest_language_count == 2
    assert report.summary.korean_voice_available_count == 0
    assert report.summary.model_download_attempted_count == 0
    assert report.summary.local_tts_execution_count == 0
    assert report.summary.external_provider_call_count == 0
    assert report.summary.external_audio_transmission_count == 0
    assert report.summary.raw_audio_public_artifact_count == 0
    assert report.summary.raw_transcript_public_artifact_count == 0
    assert report.summary.piper_tts_decision == "blocked_missing_korean_voice"

    rows = [
        json.loads(line)
        for line in (tmp_path / "voice_local_piper_tts_smoke_rows.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(rows) == 5
    assert all(row["synthesis_status"] == "blocked_missing_korean_voice" for row in rows)
    assert all(row["error_code"] == "piper_korean_voice_missing" for row in rows)
    assert all("script_text" not in row for row in rows)
    assert all("raw_transcript" not in row for row in rows)
    assert all("raw_audio" not in row for row in rows)
    assert all("audio_path" not in row for row in rows)


def test_piper_tts_row_uses_cuda_flag_when_execution_is_allowed(
    tmp_path: Path,
    monkeypatch,
) -> None:
    commands: list[list[str]] = []
    model_path = tmp_path / "voice.onnx"
    config_path = tmp_path / "voice.onnx.json"
    output_path = tmp_path / "out.wav"
    model_path.write_bytes(b"placeholder")
    config_path.write_text("{}", encoding="utf-8")

    def fake_run(command, **kwargs):
        commands.append(command)
        with wave.open(str(output_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            wav_file.writeframes(b"\x00\x00" * 160)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(piper_smoke.subprocess, "run", fake_run)
    script = VoiceTtsSmokeScript(
        script_id="tts-smoke-docent-test",
        language="ko",
        text_role="spoken_answer",
        script_text="경복궁에서 한양의 중심을 짧게 설명합니다.",
        place_ids=("gyeongbokgung",),
        public_allowed=True,
    )

    row = piper_smoke.build_piper_tts_row(
        script=script,
        selected_voice_id="ko_KR-test-low",
        resolved_device="cuda",
        model_path=model_path,
        config_path=config_path,
        output_path=output_path,
        runtime_available=True,
        manifest_available=True,
        korean_voice_available=True,
        execute_local_tts=True,
        should_execute=True,
    )

    assert row.synthesis_status == "executed"
    assert row.piper_cuda_requested is True
    assert commands
    assert "--cuda" in commands[0]


def test_piper_tts_smoke_docs_record_manifest_blocker() -> None:
    assert DOC_PATH.exists()
    assert REPORT_PATH.exists()

    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert piper_smoke.WORK_ID in doc
    assert piper_smoke.WORK_ID in report
    assert "piper_runtime_available_count | 1" in report
    assert "piper_distribution_installed_count | 1" in report
    assert "manifest_voice_count | 161" in report
    assert "manifest_language_count | 49" in report
    assert "korean_voice_available_count | 0" in report
    assert "local_tts_execution_count | 0" in report
    assert "external_provider_call_count | 0" in report
    assert "external_audio_transmission_count | 0" in report
    assert "raw_audio_public_artifact_count | 0" in report
    assert "raw_transcript_public_artifact_count | 0" in report
    assert "public_private_path_leakage_count | 0" in report
    assert "public_secret_like_leakage_count | 0" in report
    assert "public_raw_payload_leakage_count | 0" in report
    assert "piper_tts_decision | `blocked_missing_korean_voice`" in report
    assert "External audit | PASS" in report


def test_piper_tts_smoke_registered_and_public_safe() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    todo = TODO_PATH.read_text(encoding="utf-8")
    ledger = LEDGER_PATH.read_text(encoding="utf-8")

    for link in REQUIRED_LINKS:
        assert link in readme
        assert Path(link).exists()

    assert "- [x] local Piper TTS smoke" in todo
    assert piper_smoke.WORK_ID in ledger

    for path in PUBLIC_SCAN_PATHS:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"private_data[/\\]", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)


def test_piper_tts_smoke_keeps_forbidden_claims_forbidden() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    forbidden_section = doc.split("금지 claim:", maxsplit=1)[1]

    for claim in FORBIDDEN_CLAIMS:
        assert claim in forbidden_section
