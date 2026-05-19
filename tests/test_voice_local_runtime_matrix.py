from __future__ import annotations

import json
import re
from pathlib import Path

from pipelines.voice_local_runtime_matrix import (
    LOCAL_RUNTIME_CANDIDATES,
    WORK_ID,
    collect_runtime_matrix_failures,
    run_voice_local_runtime_matrix,
)


DOC_PATH = Path("docs/VOICE_LOCAL_RUNTIME_MATRIX.md")
REPORT_PATH = Path("evals/reports/voice_local_runtime_matrix_report.md")
README_PATH = Path("README.md")
TODO_PATH = Path("docs/TODO.md")
LEDGER_PATH = Path("docs/RAG_DECISION_LEDGER.md")
CHECKLIST_PATH = Path("docs/CHECKLIST.md")
WBS_PATH = Path("docs/WBS.md")
ROADMAP_PATH = Path("docs/ROADMAP.md")
PROVIDER_DECISION_PATH = Path("docs/VOICE_PROVIDER_DECISION.md")
REQUIRED_LINKS = (
    "docs/VOICE_LOCAL_RUNTIME_MATRIX.md",
    "evals/reports/voice_local_runtime_matrix_report.md",
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
    "무료 로컬 TTS 품질 검증 완료",
    "MeloTTS가 최종 provider로 확정",
    "faster-whisper가 현재 환경에서 실행 가능",
    "production 음성 관광 앱 완성",
)


def test_runtime_matrix_runner_records_public_safe_preflight(
    tmp_path: Path,
) -> None:
    report = run_voice_local_runtime_matrix(
        doc_path=tmp_path / "VOICE_LOCAL_RUNTIME_MATRIX.md",
        report_path=tmp_path / "voice_local_runtime_matrix_report.md",
        result_rows_path=tmp_path / "voice_local_runtime_matrix_rows.jsonl",
        module_availability={
            "faster_whisper": False,
            "whisper": True,
            "melo": False,
            "melotts": False,
            "sherpa_onnx": False,
            "piper": False,
            "piper_phonemize": False,
        },
        distribution_versions={
            "faster-whisper": None,
            "openai-whisper": "20250625",
            "melotts": None,
            "sherpa-onnx": None,
            "piper-tts": None,
            "piper-phonemize": None,
        },
    )

    assert collect_runtime_matrix_failures(report) == []
    assert report.summary.runtime_candidate_count == len(LOCAL_RUNTIME_CANDIDATES)
    assert report.summary.primary_local_stt_candidate_count == 1
    assert report.summary.existing_local_stt_fallback_count == 1
    assert report.summary.primary_local_tts_candidate_count == 1
    assert report.summary.import_available_candidate_count == 1
    assert report.summary.stt_runtime_available_count == 1
    assert report.summary.tts_runtime_available_count == 0
    assert report.summary.package_install_attempted_count == 0
    assert report.summary.model_download_attempted_count == 0
    assert report.summary.model_load_attempted_count == 0
    assert report.summary.local_stt_execution_count == 0
    assert report.summary.local_tts_execution_count == 0
    assert report.summary.external_provider_call_count == 0
    assert report.summary.external_audio_transmission_count == 0
    assert report.summary.raw_audio_public_artifact_count == 0
    assert report.summary.raw_transcript_public_artifact_count == 0
    assert report.summary.client_secret_exposure_count == 0
    assert report.summary.public_private_path_leakage_count == 0
    assert report.summary.public_secret_like_leakage_count == 0
    assert report.summary.public_raw_payload_leakage_count == 0

    rows = [
        json.loads(line)
        for line in (tmp_path / "voice_local_runtime_matrix_rows.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(rows) == len(LOCAL_RUNTIME_CANDIDATES)
    assert all("script_text" not in row for row in rows)
    assert all("raw_audio" not in row for row in rows)
    assert all("raw_transcript" not in row for row in rows)
    assert all("audio_path" not in row for row in rows)


def test_runtime_matrix_docs_are_registered_and_public_safe() -> None:
    assert DOC_PATH.exists()
    assert REPORT_PATH.exists()

    readme = README_PATH.read_text(encoding="utf-8")
    todo = TODO_PATH.read_text(encoding="utf-8")
    ledger = LEDGER_PATH.read_text(encoding="utf-8")

    for link in REQUIRED_LINKS:
        assert link in readme
        assert Path(link).exists()

    assert "- [x] local voice runtime candidate matrix" in todo
    assert WORK_ID in ledger
    assert "voice_local_runtime_matrix" in ledger

    for path in PUBLIC_SCAN_PATHS:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)
        assert "private_data/" not in text


def test_runtime_matrix_report_records_quantitative_gates() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert WORK_ID in doc
    assert WORK_ID in report
    assert "runtime_candidate_count | 5" in report
    assert "primary_local_stt_candidate_count | 1" in report
    assert "existing_local_stt_fallback_count | 1" in report
    assert "primary_local_tts_candidate_count | 1" in report
    assert "package_install_attempted_count | 0" in report
    assert "model_download_attempted_count | 0" in report
    assert "model_load_attempted_count | 0" in report
    assert "local_stt_execution_count | 0" in report
    assert "local_tts_execution_count | 0" in report
    assert "external_provider_call_count | 0" in report
    assert "external_audio_transmission_count | 0" in report
    assert "raw_audio_public_artifact_count | 0" in report
    assert "raw_transcript_public_artifact_count | 0" in report
    assert "client_secret_exposure_count | 0" in report
    assert "resolved_device | `cuda`" in report
    assert "local_openai_whisper_cuda_fallback" in report
    assert "local_melotts_korean" in report
    assert "External audit | PASS" in report


def test_runtime_matrix_keeps_forbidden_claims_forbidden() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    forbidden_section = doc.split("## Claim Boundary", maxsplit=1)[1]

    for claim in FORBIDDEN_CLAIMS:
        assert claim in forbidden_section
