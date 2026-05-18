from __future__ import annotations

import re
from pathlib import Path


FRONTEND_PATHS = (
    Path("frontend/package.json"),
    Path("frontend/src/components/DocentApp.tsx"),
    Path("frontend/src/lib/chatClient.ts"),
    Path("frontend/src/fixtures/chatFixtures.ts"),
    Path("frontend/src/types/chat.ts"),
    Path("frontend/src/App.test.tsx"),
)
DOC_PATH = Path("docs/VOICE_UI_SKELETON.md")
REPORT_PATH = Path("evals/reports/voice_ui_skeleton_report.md")


def test_voice_ui_skeleton_files_exist_and_are_sanitized() -> None:
    for path in (*FRONTEND_PATHS, DOC_PATH, REPORT_PATH, Path("README.md")):
        text = path.read_text(encoding="utf-8")

        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\\s*=", text)
        assert "private_data/" not in text


def test_voice_ui_skeleton_records_scope_and_no_live_call_boundary() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert "`HD-VOICE-UI-002`" in doc
    assert "`HD-VOICE-UI-003`" in doc
    assert "live_solar_call_count | 0" in report
    assert "backend_endpoint_added_count | 0" in report
    assert "retrieval_execution_count | 0" in report
    assert "stt_tts_production_claim_count | 0" in report


def test_voice_ui_skeleton_maps_required_api_fields() -> None:
    types = Path("frontend/src/types/chat.ts").read_text(encoding="utf-8")
    app = Path("frontend/src/components/DocentApp.tsx").read_text(encoding="utf-8")

    for field in (
        "query",
        "language",
        "place_context",
        "voice_mode",
        "answer",
        "spoken_answer",
        "citations",
        "evidence_ids",
        "place_ids",
        "abstained",
        "unsupported_claim_risk",
        "active_route_applied",
        "guard_applied",
    ):
        assert field in types or field in app


def test_voice_ui_skeleton_has_frontend_regression_tests() -> None:
    frontend_test = Path("frontend/src/App.test.tsx").read_text(encoding="utf-8")

    assert "renders answerable fixture" in frontend_test
    assert "renders no-answer state" in frontend_test
    assert "renders sanitized API error state" in frontend_test
    assert "renders voice fallback controls" in frontend_test
    assert "ui_state_test_count | 5" in REPORT_PATH.read_text(encoding="utf-8")


def test_voice_ui_skeleton_report_records_data_mart_and_audit() -> None:
    report = REPORT_PATH.read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "fact_voice_ui_skeleton_eval" in report
    assert "work_id + ui_state_id + component_id + test_id + claim_boundary" in report
    assert "External audit | PASS" in report
    assert "Voice UI Skeleton" in readme
    assert "public_private_path_leakage_count | 0" in report
    assert "public_secret_like_leakage_count | 0" in report
    assert "public_raw_payload_leakage_count | 0" in report
