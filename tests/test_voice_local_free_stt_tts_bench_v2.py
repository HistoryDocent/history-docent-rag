from __future__ import annotations

import json
import re
from pathlib import Path

from pipelines.voice_local_free_stt_tts_bench_v2 import (
    WORK_ID,
    collect_free_local_voice_bench_failures,
    run_voice_local_free_stt_tts_bench_v2,
)


DOC_PATH = Path("docs/VOICE_LOCAL_FREE_STT_TTS_BENCH_V2.md")
REPORT_PATH = Path("evals/reports/voice_local_free_stt_tts_bench_v2_report.md")
README_PATH = Path("README.md")
TODO_PATH = Path("docs/TODO.md")
LEDGER_PATH = Path("docs/RAG_DECISION_LEDGER.md")
CHECKLIST_PATH = Path("docs/CHECKLIST.md")
WBS_PATH = Path("docs/WBS.md")
ROADMAP_PATH = Path("docs/ROADMAP.md")
VOICE_DECISION_PATH = Path("docs/VOICE_PROVIDER_DECISION.md")
REQUIRED_LINKS = (
    "docs/VOICE_LOCAL_FREE_STT_TTS_BENCH_V2.md",
    "evals/reports/voice_local_free_stt_tts_bench_v2_report.md",
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
    "`faster-whisper`가 현재 baseline보다 우수하다는 주장",
    "`Piper`가 최종 TTS provider라는 주장",
    "Windows SAPI fallback이 production 품질 provider라는 주장",
    "무료 로컬 음성 관광 앱 완성",
    "실제 관광객 음성 품질 검증 완료",
)


def test_free_local_voice_bench_v2_runner_public_safe_contract(tmp_path: Path) -> None:
    report = run_voice_local_free_stt_tts_bench_v2(
        doc_path=tmp_path / "VOICE_LOCAL_FREE_STT_TTS_BENCH_V2.md",
        report_path=tmp_path / "voice_local_free_stt_tts_bench_v2_report.md",
        result_rows_path=tmp_path / "voice_local_free_stt_tts_bench_v2_rows.jsonl",
        module_availability={
            "whisper": True,
            "faster_whisper": False,
            "pyttsx3": True,
            "piper": False,
            "piper_phonemize": False,
            "melo": False,
            "melotts": False,
        },
        distribution_versions={
            "openai-whisper": "20250625",
            "faster-whisper": None,
            "pyttsx3": "2.99",
            "piper-tts": None,
            "piper-phonemize": None,
            "melotts": None,
        },
        cli_availability={"whisper-cli": False, "whisper.cpp": False},
    )

    assert collect_free_local_voice_bench_failures(report) == []
    assert report.summary.candidate_count == 6
    assert report.summary.stt_candidate_count == 3
    assert report.summary.tts_candidate_count == 3
    assert report.summary.current_stt_benchmarked_count == 1
    assert report.summary.current_tts_benchmarked_count == 1
    assert report.summary.external_provider_call_count == 0
    assert report.summary.external_audio_transmission_count == 0
    assert report.summary.live_stt_call_count == 0
    assert report.summary.live_tts_call_count == 0
    assert report.summary.live_solar_call_count == 0
    assert report.summary.raw_audio_public_artifact_count == 0
    assert report.summary.raw_transcript_public_artifact_count == 0
    assert report.summary.recommended_current_stt_candidate_id == (
        "local_openai_whisper_small_cuda_current"
    )
    assert report.summary.recommended_current_tts_candidate_id == (
        "local_windows_sapi_pyttsx3_korean_fallback"
    )
    assert report.summary.next_stt_candidate_id == "local_faster_whisper_cuda_target"
    assert report.summary.next_tts_candidate_id == "local_piper_tts_target"

    rows = [
        json.loads(line)
        for line in (tmp_path / "voice_local_free_stt_tts_bench_v2_rows.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(rows) == 6
    assert all("script_text" not in row for row in rows)
    assert all("raw_transcript" not in row for row in rows)
    assert all("raw_audio" not in row for row in rows)
    assert all("audio_path" not in row for row in rows)


def test_free_local_voice_bench_v2_docs_record_current_baseline() -> None:
    assert DOC_PATH.exists()
    assert REPORT_PATH.exists()

    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert WORK_ID in doc
    assert WORK_ID in report
    assert "candidate_count | 6" in report
    assert "stt_candidate_count | 3" in report
    assert "tts_candidate_count | 3" in report
    assert "current_stt_benchmarked_count | 1" in report
    assert "current_tts_benchmarked_count | 1" in report
    assert "external_provider_call_count | 0" in report
    assert "external_audio_transmission_count | 0" in report
    assert "live_stt_call_count | 0" in report
    assert "live_tts_call_count | 0" in report
    assert "live_solar_call_count | 0" in report
    assert "raw_audio_public_artifact_count | 0" in report
    assert "raw_transcript_public_artifact_count | 0" in report
    assert "recommended_current_stt_candidate_id | `local_openai_whisper_small_cuda_current`" in report
    assert (
        "recommended_current_tts_candidate_id | `local_windows_sapi_pyttsx3_korean_fallback`"
        in report
    )
    assert "next_stt_candidate_id | `local_faster_whisper_cuda_target`" in report
    assert "next_tts_candidate_id | `local_piper_tts_target`" in report
    assert "bench_decision | `local_first_current_baseline_ready_next_targets_pending`" in report
    assert "External audit | PASS" in report


def test_free_local_voice_bench_v2_registered_and_public_safe() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    todo = TODO_PATH.read_text(encoding="utf-8")
    ledger = LEDGER_PATH.read_text(encoding="utf-8")

    for link in REQUIRED_LINKS:
        assert link in readme
        assert Path(link).exists()

    assert "- [x] local free STT/TTS bench v2" in todo
    assert WORK_ID in ledger

    for path in PUBLIC_SCAN_PATHS:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)


def test_free_local_voice_bench_v2_keeps_forbidden_claims_forbidden() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    forbidden_section = doc.split("금지 claim:", maxsplit=1)[1]

    for claim in FORBIDDEN_CLAIMS:
        assert claim in forbidden_section
