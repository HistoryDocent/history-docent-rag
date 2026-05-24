from __future__ import annotations

import json
import math
import re
import wave
from pathlib import Path
from types import SimpleNamespace

import numpy as np

import pipelines.voice_local_tts_quality_listening_review as tts_quality


DOC_PATH = Path("docs/VOICE_LOCAL_TTS_QUALITY_LISTENING_REVIEW.md")
REPORT_PATH = Path("evals/reports/voice_local_tts_quality_listening_review_report.md")
README_PATH = Path("README.md")
TODO_PATH = Path("docs/TODO.md")
LEDGER_PATH = Path("docs/RAG_DECISION_LEDGER.md")
CHECKLIST_PATH = Path("docs/CHECKLIST.md")
WBS_PATH = Path("docs/WBS.md")
ROADMAP_PATH = Path("docs/ROADMAP.md")
VOICE_DECISION_PATH = Path("docs/VOICE_PROVIDER_DECISION.md")
REQUIRED_LINKS = (
    "docs/VOICE_LOCAL_TTS_QUALITY_LISTENING_REVIEW.md",
    "evals/reports/voice_local_tts_quality_listening_review_report.md",
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


def test_tts_quality_listening_review_runner_public_safe_contract(
    tmp_path: Path,
    monkeypatch,
) -> None:
    audio_dir = tmp_path / "audio"
    _write_fixture_audio(audio_dir)
    monkeypatch.setattr(
        tts_quality,
        "build_cuda_preflight",
        lambda: SimpleNamespace(
            local_cuda_available=True,
            cuda_device_count=1,
        ),
    )

    report = tts_quality.run_voice_local_tts_quality_listening_review(
        private_audio_dir=audio_dir,
        doc_path=tmp_path / "VOICE_LOCAL_TTS_QUALITY_LISTENING_REVIEW.md",
        report_path=tmp_path / "voice_local_tts_quality_listening_review_report.md",
        result_rows_path=tmp_path / "voice_local_tts_quality_listening_review_rows.jsonl",
    )

    assert tts_quality.collect_review_failures(report) == []
    assert report.summary.expected_audio_count == 5
    assert report.summary.selected_audio_count == 5
    assert report.summary.audio_file_available_count == 5
    assert report.summary.audio_metric_row_count == 5
    assert report.summary.automated_metric_pass_count == 5
    assert report.summary.automated_metric_fail_count == 0
    assert report.summary.human_listening_rubric_criterion_count == 6
    assert report.summary.human_listening_required_count == 5
    assert report.summary.human_listening_completed_count == 0
    assert report.summary.human_listening_score_public_artifact_count == 0
    assert report.summary.external_provider_call_count == 0
    assert report.summary.external_audio_transmission_count == 0
    assert report.summary.raw_audio_public_artifact_count == 0
    assert report.summary.raw_transcript_public_artifact_count == 0
    assert report.summary.public_private_path_leakage_count == 0
    assert report.summary.public_secret_like_leakage_count == 0
    assert report.summary.public_raw_payload_leakage_count == 0
    assert (
        report.summary.review_decision
        == "automated_audio_sanity_passed_pending_human_review"
    )

    rows = [
        json.loads(line)
        for line in (tmp_path / "voice_local_tts_quality_listening_review_rows.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(rows) == 5
    assert all(row["provider_candidate_id"] == "local_sherpa_onnx_supertonic3_ko" for row in rows)
    assert all(row["automated_sanity_pass"] is True for row in rows)
    assert all("script_text" not in row for row in rows)
    assert all("raw_transcript" not in row for row in rows)
    assert all("raw_audio" not in row for row in rows)
    assert all("audio_path" not in row for row in rows)
    assert all("private_audio_dir" not in row for row in rows)


def test_tts_quality_listening_review_docs_record_pending_human_review() -> None:
    assert DOC_PATH.exists()
    assert REPORT_PATH.exists()

    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert tts_quality.WORK_ID in doc
    assert tts_quality.WORK_ID in report
    assert "expected_audio_count | 5" in report
    assert "selected_audio_count | 5" in report
    assert "audio_file_available_count | 5" in report
    assert "audio_metric_row_count | 5" in report
    assert "automated_metric_pass_count | 5" in report
    assert "automated_metric_fail_count | 0" in report
    assert "human_listening_rubric_criterion_count | 6" in report
    assert "human_listening_required_count | 5" in report
    assert "human_listening_completed_count | 0" in report
    assert "human_listening_score_public_artifact_count | 0" in report
    assert "external_provider_call_count | 0" in report
    assert "external_audio_transmission_count | 0" in report
    assert "raw_audio_public_artifact_count | 0" in report
    assert "raw_transcript_public_artifact_count | 0" in report
    assert "public_private_path_leakage_count | 0" in report
    assert "public_secret_like_leakage_count | 0" in report
    assert "public_raw_payload_leakage_count | 0" in report
    assert (
        "review_decision | `automated_audio_sanity_passed_pending_human_review`"
        in report
    )
    assert "External audit | PASS" in report
    assert "사람 청취 평가는 아직 완료하지 않았다" in report
    assert "사람 청취 평가 완료가 아니다" in doc


def test_tts_quality_listening_review_registered_and_public_safe() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    todo = TODO_PATH.read_text(encoding="utf-8")
    ledger = LEDGER_PATH.read_text(encoding="utf-8")

    for link in REQUIRED_LINKS:
        assert link in readme
        assert Path(link).exists()

    assert "- [x] optional TTS quality listening review" in todo
    assert "- [x] optional human TTS listening score fill framework" in todo
    assert "- [x] optional human TTS listening score collection workflow" in todo
    assert "- [x] optional human TTS listening score entry tool" in todo
    assert "- [x] optional human TTS listening score entry completion verification" in todo
    assert "- [x] optional human TTS listening score manual scoring" in todo
    assert tts_quality.WORK_ID in ledger
    assert "voice_local_tts_quality_listening_review" in ledger

    for path in PUBLIC_SCAN_PATHS:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"private_data[/\\]", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)


def test_tts_quality_listening_review_keeps_forbidden_claims_forbidden() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    forbidden_section = doc.split("## Claim Boundary", maxsplit=1)[1]

    for claim in FORBIDDEN_CLAIMS:
        assert claim in forbidden_section
