from __future__ import annotations

import json
import math
import re
import wave
from pathlib import Path
from types import SimpleNamespace

import numpy as np

import pipelines.voice_local_tts_automated_proxy_eval as proxy_eval


DOC_PATH = Path("docs/VOICE_LOCAL_TTS_AUTOMATED_PROXY_EVAL.md")
REPORT_PATH = Path("evals/reports/voice_local_tts_automated_proxy_eval_report.md")
README_PATH = Path("README.md")
TODO_PATH = Path("docs/TODO.md")
LEDGER_PATH = Path("docs/RAG_DECISION_LEDGER.md")
CHECKLIST_PATH = Path("docs/CHECKLIST.md")
WBS_PATH = Path("docs/WBS.md")
ROADMAP_PATH = Path("docs/ROADMAP.md")
VOICE_DECISION_PATH = Path("docs/VOICE_PROVIDER_DECISION.md")
REQUIRED_LINKS = (
    "docs/VOICE_LOCAL_TTS_AUTOMATED_PROXY_EVAL.md",
    "evals/reports/voice_local_tts_automated_proxy_eval_report.md",
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
    "사람 청취 점수 입력 완료",
    "자동 proxy가 사람 평가를 대체한다",
    "무료 로컬 TTS 최종 provider 확정",
    "Supertonic 3 음성 품질 우수 검증 완료",
    "실제 관광객 음성 품질 검증 완료",
    "production 음성 관광 앱 완성",
)


def _write_tone_wav(path: Path, *, sample_rate: int = 44100, duration_ms: int = 1400) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sample_count = int(sample_rate * duration_ms / 1000)
    timeline = np.arange(sample_count, dtype=np.float32) / sample_rate
    tone = 0.25 * np.sin(2.0 * math.pi * 440.0 * timeline)
    pcm = np.clip(tone * 32767.0, -32768, 32767).astype("<i2")
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm.tobytes())


def _write_fixture_audio(audio_dir: Path) -> None:
    for index in range(1, 6):
        _write_tone_wav(audio_dir / f"tts-smoke-docent-{index:03d}.wav")


def test_tts_automated_proxy_eval_runner_public_safe_contract(
    tmp_path: Path,
    monkeypatch,
) -> None:
    audio_dir = tmp_path / "audio"
    _write_fixture_audio(audio_dir)
    monkeypatch.setattr(
        proxy_eval,
        "build_cuda_preflight",
        lambda: SimpleNamespace(
            resolved_device="cuda",
            local_cuda_available=True,
            cuda_device_count=1,
        ),
    )

    report = proxy_eval.run_voice_local_tts_automated_proxy_eval(
        private_audio_dir=audio_dir,
        doc_path=tmp_path / "VOICE_LOCAL_TTS_AUTOMATED_PROXY_EVAL.md",
        report_path=tmp_path / "voice_local_tts_automated_proxy_eval_report.md",
        result_rows_path=tmp_path / "voice_local_tts_automated_proxy_eval_rows.jsonl",
        execute_local_stt=True,
        transcriber=lambda script, _audio_path: (script.script_text, 12.5),
    )

    assert proxy_eval.collect_proxy_eval_failures(report, require_local_stt=False) == []
    assert report.summary.selected_script_count == 5
    assert report.summary.audio_file_available_count == 5
    assert report.summary.automated_audio_sanity_pass_count == 5
    assert report.summary.local_stt_runtime_available_count == 1
    assert report.summary.local_stt_execution_requested_count == 5
    assert report.summary.local_stt_execution_count == 5
    assert report.summary.local_cuda_stt_call_count == 5
    assert report.summary.proxy_metric_pass_count == 5
    assert report.summary.proxy_metric_fail_count == 0
    assert report.summary.cer_avg == 0.0
    assert report.summary.char_f1_avg == 1.0
    assert report.summary.sequence_similarity_avg == 1.0
    assert report.summary.human_listening_completed_count == 0
    assert report.summary.external_provider_call_count == 0
    assert report.summary.external_audio_transmission_count == 0
    assert report.summary.raw_audio_public_artifact_count == 0
    assert report.summary.raw_transcript_public_artifact_count == 0
    assert report.summary.raw_script_public_artifact_count == 0
    assert report.summary.proxy_decision == "automated_proxy_passed_not_human_score"

    rows = [
        json.loads(line)
        for line in (tmp_path / "voice_local_tts_automated_proxy_eval_rows.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(rows) == 5
    assert all(row["tts_provider_candidate_id"] == "local_sherpa_onnx_supertonic3_ko" for row in rows)
    assert all(row["stt_provider_candidate_id"] == "local_faster_whisper_small_cuda" for row in rows)
    assert all(row["proxy_status"] == "executed" for row in rows)
    assert all(row["char_f1"] == 1.0 for row in rows)
    assert all("script_text" not in row for row in rows)
    assert all("raw_transcript" not in row for row in rows)
    assert all("raw_audio" not in row for row in rows)
    assert all("audio_path" not in row for row in rows)
    assert all("private_audio_dir" not in row for row in rows)


def test_tts_automated_proxy_eval_docs_record_execution_result() -> None:
    assert DOC_PATH.exists()
    assert REPORT_PATH.exists()

    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert proxy_eval.WORK_ID in doc
    assert proxy_eval.WORK_ID in report
    assert "selected_script_count | 5" in report
    assert "audio_file_available_count | 5" in report
    assert "automated_audio_sanity_pass_count | 5" in report
    assert "local_stt_runtime_available_count | 1" in report
    assert "local_stt_execution_requested_count | 5" in report
    assert "local_stt_execution_count | 5" in report
    assert "local_cuda_stt_call_count | 5" in report
    assert "proxy_metric_pass_count | 4" in report
    assert "proxy_metric_fail_count | 1" in report
    assert "human_listening_completed_count | 0" in report
    assert "human_score_public_detail_row_count | 0" in report
    assert "external_provider_call_count | 0" in report
    assert "external_audio_transmission_count | 0" in report
    assert "raw_audio_public_artifact_count | 0" in report
    assert "raw_transcript_public_artifact_count | 0" in report
    assert "raw_script_public_artifact_count | 0" in report
    assert "public_private_path_leakage_count | 0" in report
    assert "public_secret_like_leakage_count | 0" in report
    assert "public_raw_payload_leakage_count | 0" in report
    assert "proxy_decision | `automated_proxy_failed_quality_threshold`" in report
    assert "External audit | PASS" in report
    assert "이 결과는 human listening score가 아니다" in report
    assert "TTS 음질 최종 판단이나 provider 채택이 아니다" in doc


def test_tts_automated_proxy_eval_registered_and_public_safe() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    todo = TODO_PATH.read_text(encoding="utf-8")
    ledger = LEDGER_PATH.read_text(encoding="utf-8")

    for link in REQUIRED_LINKS:
        assert link in readme
        assert Path(link).exists()

    assert "- [x] optional TTS automated proxy evaluation" in todo
    assert proxy_eval.WORK_ID in ledger
    assert "voice_local_tts_automated_proxy_eval" in ledger

    for path in PUBLIC_SCAN_PATHS:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"private_data[/\\]", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)


def test_tts_automated_proxy_eval_keeps_forbidden_claims_forbidden() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    forbidden_section = doc.split("## Claim Boundary", maxsplit=1)[1]

    for claim in FORBIDDEN_CLAIMS:
        assert claim in forbidden_section
