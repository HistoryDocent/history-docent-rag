from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from pipelines.voice_stt_tts_managed_provider_smoke import (
    NEXT_WORK_ID,
    WORK_ID,
    collect_managed_provider_smoke_harness_failures,
    run_voice_stt_tts_managed_provider_smoke_harness,
)


DOC_PATH = Path("docs/VOICE_STT_TTS_MANAGED_PROVIDER_SMOKE_EXECUTION_HARNESS.md")
REPORT_PATH = Path(
    "evals/reports/voice_stt_tts_managed_provider_smoke_execution_harness_report.md"
)
README_PATH = Path("README.md")
TODO_PATH = Path("docs/TODO.md")
LEDGER_PATH = Path("docs/RAG_DECISION_LEDGER.md")
CHECKLIST_PATH = Path("docs/CHECKLIST.md")
WBS_PATH = Path("docs/WBS.md")
ROADMAP_PATH = Path("docs/ROADMAP.md")
REQUIRED_LINKS = (
    "docs/VOICE_STT_TTS_MANAGED_PROVIDER_SMOKE_EXECUTION_HARNESS.md",
    "evals/reports/voice_stt_tts_managed_provider_smoke_execution_harness_report.md",
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
FORBIDDEN_ROW_FIELDS = (
    "script_text",
    "raw_transcript",
    "raw_audio",
    "raw_payload",
    "credential_value",
    "audio_path",
)
FORBIDDEN_CLAIMS = (
    "provider 최종 선택 완료",
    "STT/TTS 품질 검증 완료",
    "음성 관광 앱 완성",
    "managed provider benchmark 성능 개선 입증",
    "production voice service 준비 완료",
)


def test_managed_provider_smoke_harness_runner_is_dry_run_and_public_safe(
    tmp_path: Path,
) -> None:
    report = run_voice_stt_tts_managed_provider_smoke_harness(
        doc_path=tmp_path / "VOICE_STT_TTS_MANAGED_PROVIDER_SMOKE_EXECUTION_HARNESS.md",
        report_path=(
            tmp_path / "voice_stt_tts_managed_provider_smoke_execution_harness_report.md"
        ),
        result_rows_path=(
            tmp_path / "voice_stt_tts_managed_provider_smoke_execution_harness_rows.jsonl"
        ),
    )

    assert collect_managed_provider_smoke_harness_failures(report) == []
    assert report.summary.dry_run_default is True
    assert report.summary.provider_candidate_count == 3
    assert report.summary.selected_script_count == 3
    assert report.summary.call_cap_enforced is True
    assert report.summary.managed_provider_execution_requested_count == 0
    assert report.summary.managed_provider_api_call_count == 0
    assert report.summary.external_audio_transmission_count == 0
    assert report.summary.live_stt_call_count == 0
    assert report.summary.live_tts_call_count == 0
    assert report.summary.live_solar_call_count == 0
    assert report.summary.credential_value_public_exposure_count == 0
    assert report.summary.raw_audio_public_artifact_count == 0
    assert report.summary.raw_transcript_public_artifact_count == 0
    assert report.summary.raw_payload_public_artifact_count == 0
    assert report.summary.client_secret_exposure_count == 0
    assert report.summary.public_private_path_leakage_count == 0
    assert report.summary.public_secret_like_leakage_count == 0
    assert report.summary.public_raw_payload_leakage_count == 0

    rows = [
        json.loads(line)
        for line in (
            tmp_path / "voice_stt_tts_managed_provider_smoke_execution_harness_rows.jsonl"
        )
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(rows) == 16
    for row in rows:
        for field in FORBIDDEN_ROW_FIELDS:
            assert field not in row


def test_managed_provider_smoke_harness_blocks_actual_execution(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="blocked in this harness gate"):
        run_voice_stt_tts_managed_provider_smoke_harness(
            doc_path=tmp_path / "doc.md",
            report_path=tmp_path / "report.md",
            result_rows_path=tmp_path / "rows.jsonl",
            execute_managed_provider=True,
        )


def test_managed_provider_smoke_harness_docs_record_zero_call_result() -> None:
    assert DOC_PATH.exists()
    assert REPORT_PATH.exists()

    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert WORK_ID in doc
    assert WORK_ID in report
    assert NEXT_WORK_ID in doc
    assert NEXT_WORK_ID in report
    assert "dry_run_default | true" in report
    assert "managed_provider_execution_requested_count | 0" in report
    assert "provider_candidate_count | 3" in report
    assert "selected_script_count | 3" in report
    assert "call_cap_enforced | true" in report
    assert "managed_provider_api_call_count | 0" in report
    assert "external_audio_transmission_count | 0" in report
    assert "live_stt_call_count | 0" in report
    assert "live_tts_call_count | 0" in report
    assert "live_solar_call_count | 0" in report
    assert "raw_audio_public_artifact_count | 0" in report
    assert "raw_transcript_public_artifact_count | 0" in report
    assert "raw_payload_public_artifact_count | 0" in report
    assert "credential_value_public_exposure_count | 0" in report
    assert "External Audit" in report


def test_managed_provider_smoke_harness_is_registered_and_public_safe() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    todo = TODO_PATH.read_text(encoding="utf-8")
    ledger = LEDGER_PATH.read_text(encoding="utf-8")

    for link in REQUIRED_LINKS:
        assert link in readme
        assert Path(link).exists()

    assert "- [x] optional voice STT/TTS managed provider smoke execution harness" in todo
    assert "- [ ] optional voice STT/TTS managed provider smoke execution" in todo
    assert WORK_ID in ledger
    assert NEXT_WORK_ID in ledger
    assert "dry_run_default=true" in ledger
    assert "call_cap_enforced=true" in ledger
    assert "managed_provider_api_call_count=0" in ledger
    assert "external_audio_transmission_count=0" in ledger

    for path in PUBLIC_SCAN_PATHS:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)
        assert "private_data/" not in text


def test_managed_provider_smoke_harness_keeps_forbidden_claims_forbidden() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    forbidden_section = doc.split("## Claim Boundary", maxsplit=1)[1]

    for claim in FORBIDDEN_CLAIMS:
        assert claim in forbidden_section
