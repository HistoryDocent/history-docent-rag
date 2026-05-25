from __future__ import annotations

import re
from pathlib import Path

from pipelines.voice_api_local_runtime_route_smoke import (
    WORK_ID,
    run_voice_api_local_runtime_route_smoke,
)


DOC_PATH = Path("docs/VOICE_API_LOCAL_RUNTIME_ROUTE_SMOKE.md")
REPORT_PATH = Path("evals/reports/voice_api_local_runtime_route_smoke_report.md")
README_PATH = Path("README.md")
LEDGER_PATH = Path("docs/RAG_DECISION_LEDGER.md")
TODO_PATH = Path("docs/TODO.md")
WBS_PATH = Path("docs/WBS.md")
ROADMAP_PATH = Path("docs/ROADMAP.md")
CHECKLIST_PATH = Path("docs/CHECKLIST.md")
DEMO_STACK_DOC_PATH = Path("docs/VOICE_DEMO_STACK_DECISION.md")

DOC_LINK = "docs/VOICE_API_LOCAL_RUNTIME_ROUTE_SMOKE.md"
REPORT_LINK = "evals/reports/voice_api_local_runtime_route_smoke_report.md"


def test_voice_api_local_runtime_route_smoke_runner_writes_public_safe_outputs(
    tmp_path: Path,
) -> None:
    report = run_voice_api_local_runtime_route_smoke(
        doc_path=tmp_path / "voice_api_local_runtime_route_smoke.md",
        report_path=tmp_path / "voice_api_local_runtime_route_smoke_report.md",
        result_rows_path=tmp_path / "voice_api_local_runtime_route_smoke_rows.jsonl",
        private_input_audio_dir=Path("private_data")
        / "test_outputs"
        / "voice_api_local_runtime_route_smoke",
    )

    assert report.work_id == WORK_ID
    assert report.summary.route_smoke_decision == "completed_local_voice_api_route_smoke"
    assert report.summary.total_route_request_count == 4
    assert report.summary.default_disabled_pass_count == 1
    assert report.summary.default_disabled_status_code == 403
    assert report.summary.explicit_flag_contract_pass_count == 1
    assert report.summary.explicit_flag_status_code == 200
    assert report.summary.validation_request_count == 2
    assert report.summary.validation_reject_pass_count == 2
    assert report.summary.path_traversal_status_code == 422
    assert report.summary.public_audio_status_code == 400
    assert report.summary.accepted_audio_input_count == 1
    assert report.summary.chat_contract_execution_count == 1
    assert report.summary.external_provider_call_count == 0
    assert report.summary.external_audio_transmission_count == 0
    assert report.summary.response_answer_public_row_count == 0
    assert report.summary.response_spoken_answer_public_row_count == 0

    result_rows = (tmp_path / "voice_api_local_runtime_route_smoke_rows.jsonl").read_text(
        encoding="utf-8"
    )
    assert "fallback_transcript_text" not in result_rows
    assert '"answer"' not in result_rows
    assert '"spoken_answer"' not in result_rows
    assert "private_data/" not in result_rows


def test_voice_api_local_runtime_route_smoke_docs_record_current_state() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert WORK_ID in doc
    assert WORK_ID in report
    assert "completed_local_voice_api_route_smoke" in report
    assert "/api/v1/voice/local-runtime" in doc
    assert "default_disabled_pass_count | 1" in report
    assert "default_disabled_status_code | 403" in report
    assert "explicit_flag_contract_pass_count | 1" in report
    assert "explicit_flag_status_code | 200" in report
    assert "validation_reject_pass_count | 2" in report
    assert "path_traversal_status_code | 422" in report
    assert "public_audio_status_code | 400" in report
    assert "accepted_audio_input_count | 1" in report
    assert "external_provider_call_count | 0" in report
    assert "external_audio_transmission_count | 0" in report
    assert "response_answer_public_row_count | 0" in report
    assert "response_spoken_answer_public_row_count | 0" in report
    assert "voice_api_local_runtime_route_smoke_failures=[]" in report


def test_voice_api_local_runtime_route_smoke_registered_in_public_docs() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    ledger = LEDGER_PATH.read_text(encoding="utf-8")
    todo = TODO_PATH.read_text(encoding="utf-8")
    wbs = WBS_PATH.read_text(encoding="utf-8")
    roadmap = ROADMAP_PATH.read_text(encoding="utf-8")
    checklist = CHECKLIST_PATH.read_text(encoding="utf-8")
    demo_stack = DEMO_STACK_DOC_PATH.read_text(encoding="utf-8")

    assert DOC_LINK in readme
    assert REPORT_LINK in readme
    assert WORK_ID in readme
    assert WORK_ID in ledger
    assert WORK_ID in wbs
    assert WORK_ID in checklist
    assert "optional local voice API route smoke" in todo
    assert "local voice API route smoke" in roadmap
    assert "HD-VOICE-API-LOCAL-RUNTIME-ROUTE-SMOKE-001" in demo_stack


def test_voice_api_local_runtime_route_smoke_public_artifacts_are_sanitized() -> None:
    for path in (
        DOC_PATH,
        REPORT_PATH,
        README_PATH,
        LEDGER_PATH,
        TODO_PATH,
        WBS_PATH,
        ROADMAP_PATH,
        CHECKLIST_PATH,
        DEMO_STACK_DOC_PATH,
    ):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"private_data[/\\]", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)


def test_voice_api_local_runtime_route_smoke_keeps_forbidden_claims_forbidden() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    forbidden_section = doc.split("Claim Boundary", maxsplit=1)[1]

    forbidden_claims = [
        "production 음성 관광 앱 완성",
        "실제 관광객 음성 품질 검증 완료",
        "STT/TTS provider 최종 확정",
        "microphone capture 구현 완료",
        "speaker playback 구현 완료",
    ]
    for claim in forbidden_claims:
        assert f"| forbidden | {claim} |" in forbidden_section
