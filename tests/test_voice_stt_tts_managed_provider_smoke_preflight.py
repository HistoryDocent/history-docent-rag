from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from pipelines.voice_stt_tts_managed_provider_smoke import MANAGED_PROVIDER_PLANS
from pipelines.voice_stt_tts_managed_provider_smoke_preflight import (
    NEXT_WORK_ID,
    WORK_ID,
    collect_managed_provider_smoke_preflight_failures,
    run_voice_stt_tts_managed_provider_smoke_preflight,
)


DOC_PATH = Path("docs/VOICE_STT_TTS_MANAGED_PROVIDER_SMOKE_PREFLIGHT.md")
REPORT_PATH = Path(
    "evals/reports/voice_stt_tts_managed_provider_smoke_preflight_report.md"
)
README_PATH = Path("README.md")
TODO_PATH = Path("docs/TODO.md")
LEDGER_PATH = Path("docs/RAG_DECISION_LEDGER.md")
CHECKLIST_PATH = Path("docs/CHECKLIST.md")
WBS_PATH = Path("docs/WBS.md")
ROADMAP_PATH = Path("docs/ROADMAP.md")
REQUIRED_LINKS = (
    "docs/VOICE_STT_TTS_MANAGED_PROVIDER_SMOKE_PREFLIGHT.md",
    "evals/reports/voice_stt_tts_managed_provider_smoke_preflight_report.md",
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
    "credential_env_names",
)
FORBIDDEN_CLAIMS = (
    "provider 최종 선택 완료",
    "managed provider STT/TTS 품질 검증 완료",
    "외부 provider benchmark 완료",
    "production voice service 준비 완료",
    "managed provider 비용/정책 최신 확인 완료",
)


def _clear_managed_provider_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for plan in MANAGED_PROVIDER_PLANS:
        for name in plan.credential_env_names:
            monkeypatch.delenv(name, raising=False)


def test_managed_provider_smoke_preflight_missing_credentials_is_public_safe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_managed_provider_env(monkeypatch)

    report = run_voice_stt_tts_managed_provider_smoke_preflight(
        doc_path=tmp_path / "VOICE_STT_TTS_MANAGED_PROVIDER_SMOKE_PREFLIGHT.md",
        report_path=(
            tmp_path / "voice_stt_tts_managed_provider_smoke_preflight_report.md"
        ),
        result_rows_path=(
            tmp_path / "voice_stt_tts_managed_provider_smoke_preflight_rows.jsonl"
        ),
    )

    assert collect_managed_provider_smoke_preflight_failures(report) == []
    assert report.summary.provider_candidate_count == 3
    assert report.summary.selected_script_count == 3
    assert report.summary.call_cap_enforced is True
    assert report.summary.executable_provider_candidate_count == 0
    assert report.summary.recommended_first_provider_count == 0
    assert report.summary.preflight_decision == "preflight_complete_missing_credentials"
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
            tmp_path / "voice_stt_tts_managed_provider_smoke_preflight_rows.jsonl"
        )
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(rows) == 4
    for row in rows:
        for field in FORBIDDEN_ROW_FIELDS:
            assert field not in row


def test_managed_provider_smoke_preflight_recommends_only_one_ready_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_managed_provider_env(monkeypatch)
    monkeypatch.setenv("AZURE_SPEECH_KEY", "fixture-azure-key-present")
    monkeypatch.setenv("AZURE_SPEECH_REGION", "fixture-azure-region-present")

    report = run_voice_stt_tts_managed_provider_smoke_preflight(
        doc_path=tmp_path / "doc.md",
        report_path=tmp_path / "report.md",
        result_rows_path=tmp_path / "rows.jsonl",
    )

    assert collect_managed_provider_smoke_preflight_failures(report) == []
    assert report.summary.executable_provider_candidate_count == 1
    assert report.summary.recommended_first_provider_count == 1
    assert report.summary.preflight_decision == "ready_for_selected_provider_smoke_approval"
    assert report.recommended_targets[0].provider_candidate_id == "managed_azure_ai_speech"
    assert report.recommended_targets[0].planned_script_count == 3
    assert report.recommended_targets[0].planned_stt_call_count == 3
    assert report.recommended_targets[0].planned_tts_call_count == 3
    assert report.summary.source_recheck_completed_count == 0
    assert report.summary.managed_provider_api_call_count == 0
    assert report.summary.external_audio_transmission_count == 0

    doc_text = (tmp_path / "doc.md").read_text(encoding="utf-8")
    report_text = (tmp_path / "report.md").read_text(encoding="utf-8")
    rows_text = (tmp_path / "rows.jsonl").read_text(encoding="utf-8")
    assert "fixture-azure-key-present" not in doc_text
    assert "fixture-azure-region-present" not in doc_text
    assert "fixture-azure-key-present" not in report_text
    assert "fixture-azure-region-present" not in report_text
    assert "fixture-azure-key-present" not in rows_text
    assert "fixture-azure-region-present" not in rows_text


def test_managed_provider_smoke_preflight_blocks_actual_execution(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="blocked in preflight"):
        run_voice_stt_tts_managed_provider_smoke_preflight(
            doc_path=tmp_path / "doc.md",
            report_path=tmp_path / "report.md",
            result_rows_path=tmp_path / "rows.jsonl",
            execute_managed_provider=True,
        )


def test_managed_provider_smoke_preflight_docs_record_zero_call_result() -> None:
    assert DOC_PATH.exists()
    assert REPORT_PATH.exists()

    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert WORK_ID in doc
    assert WORK_ID in report
    assert NEXT_WORK_ID in doc
    assert NEXT_WORK_ID in report
    assert "provider_candidate_count | 3" in report
    assert "selected_script_count | 3" in report
    assert "call_cap_enforced | true" in report
    assert "recommended_first_provider_count | 0" in report
    assert "managed_provider_execution_requested_count | 0" in report
    assert "managed_provider_api_call_count | 0" in report
    assert "external_audio_transmission_count | 0" in report
    assert "live_stt_call_count | 0" in report
    assert "live_tts_call_count | 0" in report
    assert "live_solar_call_count | 0" in report
    assert "credential_value_public_exposure_count | 0" in report
    assert "raw_audio_public_artifact_count | 0" in report
    assert "raw_transcript_public_artifact_count | 0" in report
    assert "raw_payload_public_artifact_count | 0" in report
    assert "External Audit" in report


def test_managed_provider_smoke_preflight_is_registered_and_public_safe() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    todo = TODO_PATH.read_text(encoding="utf-8")
    ledger = LEDGER_PATH.read_text(encoding="utf-8")

    for link in REQUIRED_LINKS:
        assert link in readme
        assert Path(link).exists()

    assert "- [x] optional voice STT/TTS managed provider smoke preflight" in todo
    assert "- [ ] optional voice STT/TTS managed provider smoke execution" in todo
    assert WORK_ID in ledger
    assert NEXT_WORK_ID in ledger
    assert "executable_provider_candidate_count=0" in ledger
    assert "recommended_first_provider_count=0" in ledger
    assert "managed_provider_api_call_count=0" in ledger
    assert "external_audio_transmission_count=0" in ledger

    for path in PUBLIC_SCAN_PATHS:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)
        assert "private_data/" not in text


def test_managed_provider_smoke_preflight_keeps_forbidden_claims_forbidden() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    forbidden_section = doc.split("금지 claim:", maxsplit=1)[1]

    for claim in FORBIDDEN_CLAIMS:
        assert claim in forbidden_section
