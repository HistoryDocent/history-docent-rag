from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from pipelines.voice_stt_tts_azure_credential_preflight import (
    NEXT_WORK_ID,
    WORK_ID,
    collect_azure_credential_preflight_failures,
    run_voice_stt_tts_azure_credential_preflight,
)


DOC_PATH = Path("docs/VOICE_STT_TTS_AZURE_CREDENTIAL_PREFLIGHT.md")
REPORT_PATH = Path("evals/reports/voice_stt_tts_azure_credential_preflight_report.md")
README_PATH = Path("README.md")
TODO_PATH = Path("docs/TODO.md")
LEDGER_PATH = Path("docs/RAG_DECISION_LEDGER.md")
CHECKLIST_PATH = Path("docs/CHECKLIST.md")
WBS_PATH = Path("docs/WBS.md")
ROADMAP_PATH = Path("docs/ROADMAP.md")
REQUIRED_LINKS = (
    "docs/VOICE_STT_TTS_AZURE_CREDENTIAL_PREFLIGHT.md",
    "evals/reports/voice_stt_tts_azure_credential_preflight_report.md",
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
    "credential_value",
    "raw_audio",
    "raw_transcript",
    "raw_payload",
    "audio_path",
)
FORBIDDEN_CLAIMS = (
    "Azure STT/TTS 품질 검증 완료",
    "Azure managed provider smoke 실행 완료",
    "Azure 비용/정책 최신 확인 완료",
    "production voice service 준비 완료",
    "외부 audio 전송 검증 완료",
)


def test_azure_credential_preflight_missing_credentials_is_public_safe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AZURE_SPEECH_KEY", raising=False)
    monkeypatch.delenv("AZURE_SPEECH_REGION", raising=False)

    report = run_voice_stt_tts_azure_credential_preflight(
        env_path=tmp_path / ".env",
        doc_path=tmp_path / "doc.md",
        report_path=tmp_path / "report.md",
        result_rows_path=tmp_path / "rows.jsonl",
    )

    assert collect_azure_credential_preflight_failures(report) == []
    assert report.summary.azure_credential_ready is False
    assert report.summary.credential_present_count == 0
    assert report.summary.credential_missing_count == 2
    assert report.summary.preflight_decision == "blocked_missing_azure_credentials"
    assert report.summary.managed_provider_api_call_count == 0
    assert report.summary.external_audio_transmission_count == 0
    assert report.summary.live_stt_call_count == 0
    assert report.summary.live_tts_call_count == 0
    assert report.summary.live_solar_call_count == 0
    assert report.summary.credential_value_public_exposure_count == 0
    assert report.summary.raw_audio_public_artifact_count == 0
    assert report.summary.raw_transcript_public_artifact_count == 0
    assert report.summary.raw_payload_public_artifact_count == 0
    assert report.summary.public_private_path_leakage_count == 0
    assert report.summary.public_secret_like_leakage_count == 0
    assert report.summary.public_raw_payload_leakage_count == 0

    rows = [
        json.loads(line)
        for line in (tmp_path / "rows.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(rows) == 8
    for row in rows:
        for field in FORBIDDEN_ROW_FIELDS:
            assert field not in row


def test_azure_credential_preflight_reads_env_without_public_value_exposure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AZURE_SPEECH_KEY", raising=False)
    monkeypatch.delenv("AZURE_SPEECH_REGION", raising=False)
    env_path = tmp_path / ".env"
    env_path.write_text(
        "AZURE_SPEECH_KEY=fixture-azure-secret-value\n"
        "AZURE_SPEECH_REGION=koreacentral\n",
        encoding="utf-8",
    )

    report = run_voice_stt_tts_azure_credential_preflight(
        env_path=env_path,
        doc_path=tmp_path / "doc.md",
        report_path=tmp_path / "report.md",
        result_rows_path=tmp_path / "rows.jsonl",
    )

    assert collect_azure_credential_preflight_failures(report) == []
    assert report.summary.azure_credential_ready is True
    assert report.summary.credential_present_count == 2
    assert report.summary.credential_missing_count == 0
    assert (
        report.summary.preflight_decision
        == "ready_for_selected_provider_smoke_execution_approval"
    )
    assert report.summary.managed_provider_api_call_count == 0
    assert report.summary.external_audio_transmission_count == 0

    public_text = "\n".join(
        [
            (tmp_path / "doc.md").read_text(encoding="utf-8"),
            (tmp_path / "report.md").read_text(encoding="utf-8"),
            (tmp_path / "rows.jsonl").read_text(encoding="utf-8"),
        ],
    )
    assert "fixture-azure-secret-value" not in public_text
    assert "koreacentral" not in public_text


def test_azure_credential_preflight_blocks_actual_execution(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="blocked in credential preflight"):
        run_voice_stt_tts_azure_credential_preflight(
            env_path=tmp_path / ".env",
            doc_path=tmp_path / "doc.md",
            report_path=tmp_path / "report.md",
            result_rows_path=tmp_path / "rows.jsonl",
            execute_managed_provider=True,
        )


def test_azure_credential_preflight_docs_record_current_zero_call_result() -> None:
    assert DOC_PATH.exists()
    assert REPORT_PATH.exists()

    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert WORK_ID in doc
    assert WORK_ID in report
    assert NEXT_WORK_ID in doc
    assert NEXT_WORK_ID in report
    assert "provider_candidate_count | 1" in report
    assert "first_provider_candidate_is_azure | true" in report
    assert "planned_script_count | 3" in report
    assert "planned_stt_call_count | 3" in report
    assert "planned_tts_call_count | 3" in report
    assert "azure_credential_ready | false" in report
    assert "credential_env_var_name_count | 2" in report
    assert "credential_present_count | 0" in report
    assert "credential_missing_count | 2" in report
    assert "managed_provider_api_call_count | 0" in report
    assert "external_audio_transmission_count | 0" in report
    assert "live_stt_call_count | 0" in report
    assert "live_tts_call_count | 0" in report
    assert "live_solar_call_count | 0" in report
    assert "source_recheck_required_before_execution_count | 5" in report
    assert "source_recheck_completed_for_execution_count | 0" in report
    assert "credential_value_public_exposure_count | 0" in report
    assert "raw_audio_public_artifact_count | 0" in report
    assert "raw_transcript_public_artifact_count | 0" in report
    assert "raw_payload_public_artifact_count | 0" in report
    assert "External Audit" in report


def test_azure_credential_preflight_is_registered_and_public_safe() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    todo = TODO_PATH.read_text(encoding="utf-8")
    ledger = LEDGER_PATH.read_text(encoding="utf-8")

    for link in REQUIRED_LINKS:
        assert link in readme
        assert Path(link).exists()

    assert "- [x] optional voice STT/TTS Azure credential preflight" in todo
    assert "- [ ] optional voice STT/TTS managed provider smoke execution" in todo
    assert WORK_ID in ledger
    assert NEXT_WORK_ID in ledger
    assert "azure_credential_ready=false" in ledger
    assert "credential_present_count=0" in ledger
    assert "credential_missing_count=2" in ledger
    assert "managed_provider_api_call_count=0" in ledger
    assert "external_audio_transmission_count=0" in ledger

    for path in PUBLIC_SCAN_PATHS:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)
        assert "private_data/" not in text


def test_azure_credential_preflight_keeps_forbidden_claims_forbidden() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    forbidden_section = doc.split("금지 claim:", maxsplit=1)[1]

    for claim in FORBIDDEN_CLAIMS:
        assert claim in forbidden_section
