from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from pipelines.voice_stt_tts_azure_credential_preflight import (
    AZURE_CREDENTIAL_ENV_NAMES,
)
from pipelines.voice_stt_tts_azure_credential_ready_and_smoke_approval import (
    NEXT_WORK_ID,
    WORK_ID,
    collect_azure_credential_ready_and_smoke_approval_failures,
    run_voice_stt_tts_azure_credential_ready_and_smoke_approval,
)


DOC_PATH = Path("docs/VOICE_STT_TTS_AZURE_CREDENTIAL_READY_AND_SMOKE_APPROVAL.md")
REPORT_PATH = Path(
    "evals/reports/voice_stt_tts_azure_credential_ready_and_smoke_approval_report.md",
)
README_PATH = Path("README.md")
TODO_PATH = Path("docs/TODO.md")
LEDGER_PATH = Path("docs/RAG_DECISION_LEDGER.md")
CHECKLIST_PATH = Path("docs/CHECKLIST.md")
WBS_PATH = Path("docs/WBS.md")
ROADMAP_PATH = Path("docs/ROADMAP.md")
REQUIRED_LINKS = (
    "docs/VOICE_STT_TTS_AZURE_CREDENTIAL_READY_AND_SMOKE_APPROVAL.md",
    "evals/reports/voice_stt_tts_azure_credential_ready_and_smoke_approval_report.md",
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
    "Azure STT/TTS 품질 검증 완료",
    "Azure managed provider smoke 실행 완료",
    "Azure provider 최종 선택 완료",
    "production voice service 준비 완료",
    "외부 audio 전송 검증 완료",
)


def _clear_azure_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in AZURE_CREDENTIAL_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)


def test_azure_credential_ready_approval_missing_credentials_is_public_safe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_azure_env(monkeypatch)

    report = run_voice_stt_tts_azure_credential_ready_and_smoke_approval(
        env_path=tmp_path / "missing.env",
        doc_path=tmp_path / "doc.md",
        report_path=tmp_path / "report.md",
        result_rows_path=tmp_path / "rows.jsonl",
    )

    assert collect_azure_credential_ready_and_smoke_approval_failures(report) == []
    assert report.summary.provider_candidate_count == 1
    assert report.summary.first_provider_candidate_is_azure is True
    assert report.summary.credential_env_var_name_count == 2
    assert report.summary.credential_present_count == 0
    assert report.summary.credential_missing_count == 2
    assert report.summary.azure_credential_ready is False
    assert report.summary.azure_smoke_execution_approved is False
    assert report.summary.approval_decision == "blocked_missing_azure_credentials"
    assert report.summary.managed_provider_api_call_count == 0
    assert report.summary.external_audio_transmission_count == 0
    assert report.summary.live_stt_call_count == 0
    assert report.summary.live_tts_call_count == 0
    assert report.summary.live_solar_call_count == 0
    assert report.summary.raw_audio_public_artifact_count == 0
    assert report.summary.raw_transcript_public_artifact_count == 0
    assert report.summary.raw_payload_public_artifact_count == 0

    rows = [
        json.loads(line)
        for line in (tmp_path / "rows.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(rows) >= 1
    for row in rows:
        for field in FORBIDDEN_ROW_FIELDS:
            assert field not in row


def test_azure_credential_ready_approval_ready_credentials_still_block_without_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_azure_env(monkeypatch)
    monkeypatch.setenv("AZURE_SPEECH_KEY", "fixture-azure-key-present")
    monkeypatch.setenv("AZURE_SPEECH_REGION", "koreacentral")

    report = run_voice_stt_tts_azure_credential_ready_and_smoke_approval(
        doc_path=tmp_path / "doc.md",
        report_path=tmp_path / "report.md",
        result_rows_path=tmp_path / "rows.jsonl",
    )

    assert collect_azure_credential_ready_and_smoke_approval_failures(report) == []
    assert report.summary.azure_credential_ready is True
    assert report.summary.azure_smoke_execution_approved is False
    assert report.summary.approval_decision == "blocked_source_recheck_incomplete"
    assert report.summary.source_recheck_completed_for_execution_count == 0
    assert report.summary.managed_provider_api_call_count == 0
    assert report.summary.external_audio_transmission_count == 0

    public_text = "\n".join(
        [
            (tmp_path / "doc.md").read_text(encoding="utf-8"),
            (tmp_path / "report.md").read_text(encoding="utf-8"),
            (tmp_path / "rows.jsonl").read_text(encoding="utf-8"),
        ],
    )
    assert "fixture-azure-key-present" not in public_text
    assert "koreacentral" not in public_text


def test_azure_credential_ready_approval_all_zero_call_gates_can_be_ready(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_azure_env(monkeypatch)
    monkeypatch.setenv("AZURE_SPEECH_KEY", "fixture-azure-key-present")
    monkeypatch.setenv("AZURE_SPEECH_REGION", "koreacentral")

    report = run_voice_stt_tts_azure_credential_ready_and_smoke_approval(
        doc_path=tmp_path / "doc.md",
        report_path=tmp_path / "report.md",
        result_rows_path=tmp_path / "rows.jsonl",
        source_recheck_completed=True,
        region_confirmation_completed=True,
        retention_confirmation_completed=True,
        cost_confirmation_completed=True,
        user_external_call_approval_recorded=True,
    )

    assert collect_azure_credential_ready_and_smoke_approval_failures(report) == []
    assert report.summary.azure_credential_ready is True
    assert report.summary.azure_smoke_execution_ready is True
    assert report.summary.azure_smoke_execution_approved is True
    assert report.summary.approval_decision == "ready_for_actual_azure_smoke_execution"
    assert report.summary.managed_provider_api_call_count == 0
    assert report.summary.external_audio_transmission_count == 0
    assert report.summary.live_stt_call_count == 0
    assert report.summary.live_tts_call_count == 0
    assert report.summary.live_solar_call_count == 0


def test_azure_credential_ready_approval_docs_record_current_zero_call_result() -> None:
    assert DOC_PATH.exists()
    assert REPORT_PATH.exists()

    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert WORK_ID in doc
    assert WORK_ID in report
    assert NEXT_WORK_ID in doc
    assert NEXT_WORK_ID in report
    assert "azure_credential_ready` | `false`" in doc
    assert "azure_smoke_execution_approved` | `false`" in doc
    assert "azure_credential_ready | false" in report
    assert "azure_smoke_execution_approved | false" in report
    assert "approval_decision | `blocked_missing_azure_credentials`" in report
    assert "managed_provider_api_call_count | 0" in report
    assert "external_audio_transmission_count | 0" in report
    assert "live_stt_call_count | 0" in report
    assert "live_tts_call_count | 0" in report
    assert "live_solar_call_count | 0" in report
    assert "External Audit" in report


def test_azure_credential_ready_approval_is_registered_and_public_safe() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    todo = TODO_PATH.read_text(encoding="utf-8")
    ledger = LEDGER_PATH.read_text(encoding="utf-8")

    for link in REQUIRED_LINKS:
        assert link in readme
        assert Path(link).exists()

    assert "- [x] optional voice STT/TTS Azure credential ready smoke approval" in todo
    assert "- [ ] optional voice STT/TTS managed provider smoke execution" in todo
    assert WORK_ID in ledger
    assert NEXT_WORK_ID in ledger
    assert "azure_credential_ready=false" in ledger
    assert "azure_smoke_execution_approved=false" in ledger
    assert "approval_decision=blocked_missing_azure_credentials" in ledger
    assert "managed_provider_api_call_count=0" in ledger
    assert "external_audio_transmission_count=0" in ledger

    for path in PUBLIC_SCAN_PATHS:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)
        assert "private_data/" not in text


def test_azure_credential_ready_approval_keeps_forbidden_claims_forbidden() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    forbidden_section = doc.split("금지 claim:", maxsplit=1)[1]

    for claim in FORBIDDEN_CLAIMS:
        assert claim in forbidden_section
