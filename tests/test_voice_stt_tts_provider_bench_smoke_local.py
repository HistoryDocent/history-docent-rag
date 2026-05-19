from __future__ import annotations

import json
import re
from pathlib import Path

from pipelines.voice_stt_tts_local_smoke import (
    WORK_ID,
    collect_local_smoke_failures,
    run_voice_stt_tts_local_smoke,
)


DOC_PATH = Path("docs/VOICE_STT_TTS_PROVIDER_BENCH_SMOKE_LOCAL.md")
REPORT_PATH = Path("evals/reports/voice_stt_tts_provider_bench_smoke_local_report.md")
README_PATH = Path("README.md")
TODO_PATH = Path("docs/TODO.md")
LEDGER_PATH = Path("docs/RAG_DECISION_LEDGER.md")
CHECKLIST_PATH = Path("docs/CHECKLIST.md")
WBS_PATH = Path("docs/WBS.md")
ROADMAP_PATH = Path("docs/ROADMAP.md")
REQUIRED_LINKS = (
    "docs/VOICE_STT_TTS_PROVIDER_BENCH_SMOKE_LOCAL.md",
    "evals/reports/voice_stt_tts_provider_bench_smoke_local_report.md",
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
    "provider 최종 선택 완료",
    "STT/TTS 품질 검증 완료",
    "음성 관광 앱 완성",
    "external provider benchmark 성능 개선 입증",
)


def test_voice_local_smoke_runner_has_safe_contract_without_execution(
    tmp_path: Path,
) -> None:
    report = run_voice_stt_tts_local_smoke(
        doc_path=tmp_path / "VOICE_STT_TTS_PROVIDER_BENCH_SMOKE_LOCAL.md",
        report_path=tmp_path / "voice_stt_tts_provider_bench_smoke_local_report.md",
        result_rows_path=tmp_path / "voice_stt_tts_provider_bench_smoke_local_rows.jsonl",
        private_audio_dir=tmp_path / "audio",
        generate_private_audio=False,
        execute_local_whisper=False,
        require_local_execution=False,
    )

    assert collect_local_smoke_failures(report, require_local_execution=False) == []
    assert report.summary.selected_script_count == 5
    assert report.summary.local_provider_candidate_count == 1
    assert report.summary.local_stt_execution_count == 0
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
        for line in (tmp_path / "voice_stt_tts_provider_bench_smoke_local_rows.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(rows) == 5
    assert all("script_text" not in row for row in rows)
    assert all("raw_transcript" not in row for row in rows)
    assert all("raw_audio" not in row for row in rows)
    assert all("audio_path" not in row for row in rows)


def test_voice_local_smoke_docs_record_actual_cuda_smoke_result() -> None:
    assert DOC_PATH.exists()
    assert REPORT_PATH.exists()

    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert WORK_ID in doc
    assert WORK_ID in report
    assert "local_stt_execution_count | 5" in report
    assert "local_cuda_whisper_call_count | 5" in report
    assert "external_provider_call_count | 0" in report
    assert "external_audio_transmission_count | 0" in report
    assert "live_stt_call_count | 0" in report
    assert "live_tts_call_count | 0" in report
    assert "live_solar_call_count | 0" in report
    assert "raw_transcript_public_artifact_count | 0" in report
    assert "raw_audio_public_artifact_count | 0" in report
    assert "resolved_device | `cuda`" in report
    assert "smoke_status | `completed_local_smoke`" in report
    assert "wer_avg" in report
    assert "cer_avg" in report
    assert "place_name_accuracy_avg" in report
    assert "stt_latency_p95_ms" in report
    assert "External audit | PASS" in report


def test_voice_local_smoke_is_registered_and_public_safe() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    todo = TODO_PATH.read_text(encoding="utf-8")
    ledger = LEDGER_PATH.read_text(encoding="utf-8")

    for link in REQUIRED_LINKS:
        assert link in readme
        assert Path(link).exists()

    assert "- [x] optional voice STT/TTS provider benchmark smoke execution" in todo
    assert "HD-VOICE-STT-TTS-PROVIDER-BENCH-MANAGED-SMOKE-APPROVAL-001" in ledger
    assert "voice_stt_tts_provider_bench_smoke_local" in ledger

    for path in PUBLIC_SCAN_PATHS:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)
        assert "private_data/" not in text


def test_voice_local_smoke_keeps_forbidden_claims_forbidden() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    forbidden_section = doc.split("## Claim Boundary", maxsplit=1)[1]

    for claim in FORBIDDEN_CLAIMS:
        assert claim in forbidden_section
