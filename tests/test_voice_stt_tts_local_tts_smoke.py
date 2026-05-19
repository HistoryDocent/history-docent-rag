from __future__ import annotations

import json
import re
import wave
from pathlib import Path

from pipelines.voice_stt_tts_local_tts_smoke import (
    WORK_ID,
    collect_tts_smoke_failures,
    run_voice_stt_tts_local_tts_smoke,
)


DOC_PATH = Path("docs/VOICE_STT_TTS_LOCAL_TTS_SMOKE.md")
REPORT_PATH = Path("evals/reports/voice_stt_tts_local_tts_smoke_report.md")
README_PATH = Path("README.md")
TODO_PATH = Path("docs/TODO.md")
LEDGER_PATH = Path("docs/RAG_DECISION_LEDGER.md")
CHECKLIST_PATH = Path("docs/CHECKLIST.md")
WBS_PATH = Path("docs/WBS.md")
ROADMAP_PATH = Path("docs/ROADMAP.md")
SCRIPTS_PATH = Path("data_samples/voice_tts_smoke_scripts.sample.jsonl")
REQUIRED_LINKS = (
    "docs/VOICE_STT_TTS_LOCAL_TTS_SMOKE.md",
    "evals/reports/voice_stt_tts_local_tts_smoke_report.md",
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
    "MeloTTS가 최종 provider로 확정",
    "무료 로컬 TTS 품질 검증 완료",
    "Azure보다 local TTS가 품질 우수",
    "음성 관광 앱 완성",
)


class _FakeHpsData:
    spk2id = {"KR": 0}


class _FakeHps:
    data = _FakeHpsData()


class _FakeMeloTTS:
    hps = _FakeHps()

    def tts_to_file(
        self,
        text: str,
        speaker_id: int,
        output_path: str,
        *,
        speed: float,
    ) -> None:
        del text, speaker_id, speed
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            wav_file.writeframes(b"\x00\x00" * 160)


def _fake_tts_factory(device: str) -> _FakeMeloTTS:
    assert device in {"cuda:0", "cpu"}
    return _FakeMeloTTS()


def test_local_tts_smoke_runner_has_safe_contract_without_execution(
    tmp_path: Path,
) -> None:
    report = run_voice_stt_tts_local_tts_smoke(
        doc_path=tmp_path / "VOICE_STT_TTS_LOCAL_TTS_SMOKE.md",
        report_path=tmp_path / "voice_stt_tts_local_tts_smoke_report.md",
        result_rows_path=tmp_path / "voice_stt_tts_local_tts_smoke_rows.jsonl",
        private_audio_dir=tmp_path / "audio",
        execute_local_tts=False,
        require_local_execution=False,
    )

    assert collect_tts_smoke_failures(report, require_local_execution=False) == []
    assert report.summary.selected_script_count == 5
    assert report.summary.primary_local_tts_candidate_count == 1
    assert report.summary.tts_execution_requested_count == 0
    assert report.summary.local_tts_execution_count == 0
    assert report.summary.external_provider_call_count == 0
    assert report.summary.external_audio_transmission_count == 0
    assert report.summary.live_stt_call_count == 0
    assert report.summary.live_tts_call_count == 0
    assert report.summary.live_solar_call_count == 0
    assert report.summary.raw_transcript_public_artifact_count == 0
    assert report.summary.raw_audio_public_artifact_count == 0
    assert report.summary.client_secret_exposure_count == 0
    assert report.summary.public_private_path_leakage_count == 0
    assert report.summary.public_secret_like_leakage_count == 0
    assert report.summary.public_raw_payload_leakage_count == 0
    assert report.summary.resolved_device in {"cuda", "cpu"}

    rows = [
        json.loads(line)
        for line in (tmp_path / "voice_stt_tts_local_tts_smoke_rows.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(rows) == 5
    assert all("script_text" not in row for row in rows)
    assert all("raw_transcript" not in row for row in rows)
    assert all("raw_audio" not in row for row in rows)
    assert all("audio_path" not in row for row in rows)


def test_local_tts_smoke_runner_executes_with_injected_local_tts(
    tmp_path: Path,
) -> None:
    report = run_voice_stt_tts_local_tts_smoke(
        doc_path=tmp_path / "VOICE_STT_TTS_LOCAL_TTS_SMOKE.md",
        report_path=tmp_path / "voice_stt_tts_local_tts_smoke_report.md",
        result_rows_path=tmp_path / "voice_stt_tts_local_tts_smoke_rows.jsonl",
        private_audio_dir=tmp_path / "audio",
        execute_local_tts=True,
        require_local_execution=True,
        tts_factory=_fake_tts_factory,
    )

    assert collect_tts_smoke_failures(report, require_local_execution=True) == []
    assert report.summary.selected_script_count == 5
    assert report.summary.melotts_runtime_available_count == 1
    assert report.summary.tts_execution_requested_count == 5
    assert report.summary.local_tts_execution_count == 5
    assert report.summary.private_audio_generated_count == 5
    assert report.summary.private_audio_saved_count == 5
    assert report.summary.tts_latency_p95_ms > 0
    assert report.summary.audio_duration_total_ms > 0
    assert report.summary.audio_file_size_total_bytes > 0
    assert report.summary.external_provider_call_count == 0
    assert report.summary.external_audio_transmission_count == 0
    assert report.summary.tts_smoke_decision == "completed_local_tts_smoke"


def test_local_tts_smoke_docs_are_registered_and_public_safe() -> None:
    assert DOC_PATH.exists()
    assert REPORT_PATH.exists()
    assert SCRIPTS_PATH.exists()

    readme = README_PATH.read_text(encoding="utf-8")
    todo = TODO_PATH.read_text(encoding="utf-8")
    ledger = LEDGER_PATH.read_text(encoding="utf-8")

    for link in REQUIRED_LINKS:
        assert link in readme
        assert Path(link).exists()

    assert "- [x] local voice TTS smoke execution" in todo
    assert WORK_ID in ledger
    assert "voice_stt_tts_local_tts_smoke" in ledger

    for path in PUBLIC_SCAN_PATHS:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)
        assert "private_data/" not in text


def test_local_tts_smoke_report_records_quantitative_gates() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert WORK_ID in doc
    assert WORK_ID in report
    assert "selected_script_count | 5" in report
    assert "primary_local_tts_candidate_count | 1" in report
    assert "external_provider_call_count | 0" in report
    assert "external_audio_transmission_count | 0" in report
    assert "live_stt_call_count | 0" in report
    assert "live_tts_call_count | 0" in report
    assert "live_solar_call_count | 0" in report
    assert "raw_transcript_public_artifact_count | 0" in report
    assert "raw_audio_public_artifact_count | 0" in report
    assert "tts_latency_p50_ms" in report
    assert "tts_latency_p95_ms" in report
    assert "audio_duration_total_ms" in report
    assert "resolved_device | `cuda`" in report
    assert "melotts_device | `cuda:0`" in report
    assert "External audit | PASS" in report


def test_local_tts_smoke_keeps_forbidden_claims_forbidden() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    forbidden_section = doc.split("## Claim Boundary", maxsplit=1)[1]

    for claim in FORBIDDEN_CLAIMS:
        assert claim in forbidden_section
