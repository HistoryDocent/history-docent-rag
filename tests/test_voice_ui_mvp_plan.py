from __future__ import annotations

import re
from pathlib import Path


DOC_PATH = Path("docs/VOICE_UI_MVP_PLAN.md")
CONTRACT_PATH = Path("docs/VOICE_UI_API_CONTRACT.md")
REPORT_PATH = Path("evals/reports/voice_ui_mvp_plan_report.md")


def test_voice_ui_mvp_docs_exist_and_are_sanitized() -> None:
    for path in (DOC_PATH, CONTRACT_PATH, REPORT_PATH, Path("README.md")):
        text = path.read_text(encoding="utf-8")

        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\\s*=", text)
        assert "private_data/" not in text


def test_voice_ui_mvp_plan_records_scope_and_non_goals() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert "`HD-VOICE-UI-001`" in doc
    assert "`HD-VOICE-UI-002`" in doc
    assert "frontend_implementation_count | 0" in doc
    assert "live_solar_call_count | 0" in doc
    assert "stt_tts_production_claim_count | 0" in doc
    assert "frontend_implementation_count | 0" in report
    assert "live_solar_call_count | 0" in report


def test_voice_ui_api_contract_maps_required_chat_fields() -> None:
    text = CONTRACT_PATH.read_text(encoding="utf-8")

    assert "POST /api/v1/chat" in text
    assert "`query`" in text
    assert "`language`" in text
    assert "`place_context`" in text
    assert "`voice_mode`" in text
    assert "`answer`" in text
    assert "`spoken_answer`" in text
    assert "`citations`" in text
    assert "`evidence_ids`" in text
    assert "`place_ids`" in text
    assert "`abstained`" in text
    assert "`unsupported_claim_risk`" in text
    assert "`usage.route_policy_id`" in text
    assert "`classifier_router_dry_run.active_route_applied`" in text
    assert "`classifier_router_dry_run.guarded_route_candidate.guard_applied`" in text
    assert "`required_api_field_mapping_count=12`" in text


def test_voice_ui_report_records_quantitative_and_qualitative_gates() -> None:
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert "planned_user_journey_count | 3" in report
    assert "planned_screen_count | 5" in report
    assert "required_api_field_mapping_count | 12" in report
    assert "optional_voice_capability_count | 2" in report
    assert "public_private_path_leakage_count | 0" in report
    assert "public_secret_like_leakage_count | 0" in report
    assert "public_raw_payload_leakage_count | 0" in report
    assert "Product scope | PASS" in report
    assert "API contract | PASS" in report
    assert "External audit | PASS" in report


def test_voice_ui_plan_records_data_mart_and_forbidden_claim_boundary() -> None:
    report = REPORT_PATH.read_text(encoding="utf-8")
    forbidden_section = report.split("금지:", maxsplit=1)[1]

    assert "fact_voice_ui_mvp_plan" in report
    assert "work_id + journey_id + screen_id + api_field + claim_boundary" in report
    assert "production voice app 완성" in forbidden_section
    assert "STT/TTS 품질 검증 완료" in forbidden_section
    assert "retrieval 성능 개선" in forbidden_section
