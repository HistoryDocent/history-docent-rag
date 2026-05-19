from __future__ import annotations

import re
from pathlib import Path


DOC_PATH = Path("docs/VOICE_STT_TTS_PROVIDER_BENCH_EXECUTION_APPROVAL.md")
REPORT_PATH = Path(
    "evals/reports/voice_stt_tts_provider_bench_execution_approval_report.md",
)
README_PATH = Path("README.md")
TODO_PATH = Path("docs/TODO.md")
LEDGER_PATH = Path("docs/RAG_DECISION_LEDGER.md")
CHECKLIST_PATH = Path("docs/CHECKLIST.md")
WBS_PATH = Path("docs/WBS.md")
ROADMAP_PATH = Path("docs/ROADMAP.md")
REQUIRED_LINKS = (
    "docs/VOICE_STT_TTS_PROVIDER_BENCH_EXECUTION_APPROVAL.md",
    "evals/reports/voice_stt_tts_provider_bench_execution_approval_report.md",
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
REQUIRED_PROVIDER_IDS = (
    "browser_native_web_speech",
    "local_cuda_whisper",
    "external_google_cloud",
    "external_azure_speech",
    "external_aws_transcribe_polly",
)
REQUIRED_FACT_TABLES = (
    "fact_voice_provider_benchmark_run",
    "fact_voice_stt_eval_private",
    "fact_voice_tts_eval_private",
    "fact_voice_e2e_eval_private",
    "fact_voice_provider_public_summary",
)
FORBIDDEN_CLAIMS = (
    "provider 최종 선택 완료",
    "STT/TTS 품질 검증 완료",
    "음성 관광 앱 완성",
)


def test_execution_approval_docs_exist_and_defer_execution() -> None:
    assert DOC_PATH.exists()
    assert REPORT_PATH.exists()

    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert "HD-VOICE-STT-TTS-PROVIDER-BENCH-EXECUTION-APPROVAL-001" in doc
    assert "HD-VOICE-STT-TTS-PROVIDER-BENCH-EXECUTION-APPROVAL-001" in report
    assert "provider_benchmark_execution_approved` | `false`" in doc
    assert "provider_benchmark_execution_approved | false" in report
    assert "provider_benchmark_execution_count | 0" in report
    assert "live_stt_call_count | 0" in report
    assert "live_tts_call_count | 0" in report
    assert "live_solar_call_count | 0" in report
    assert "실제 STT/TTS call은 0" in report


def test_execution_approval_sets_metric_and_call_gates() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert "provider_candidate_group_count | 5" in report
    assert "public_safe_script_fixture_count | 30" in report
    assert "planned_smoke_script_count_per_low_risk_provider | 5" in report
    assert "planned_smoke_script_count_per_external_provider | 3" in report
    assert "planned_full_benchmark_script_count | 30" in report
    assert "pricing_recheck_required_count | 5" in report
    assert "privacy_recheck_required_count | 5" in report
    assert "region_recheck_required_count | 5" in report
    assert "source_recheck_incomplete_provider_count | 5" in report

    for metric in (
        "wer",
        "cer",
        "place_name_accuracy",
        "tts_latency_p95_ms",
        "voice_round_trip_latency_p95_ms",
        "rag_answer_contract_preserved_rate",
    ):
        assert metric in doc


def test_execution_approval_limits_provider_scope_and_grain() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    for provider_id in REQUIRED_PROVIDER_IDS:
        assert provider_id in doc
        assert provider_id in report

    for fact_table in REQUIRED_FACT_TABLES:
        assert fact_table in doc
        assert fact_table in report

    assert "HD-VOICE-STT-TTS-PROVIDER-BENCH-SMOKE-EXECUTION-001" in doc
    assert "HD-VOICE-STT-TTS-PROVIDER-BENCH-SMOKE-EXECUTION-001" in report


def test_execution_approval_registered_and_sanitized() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    todo = TODO_PATH.read_text(encoding="utf-8")
    ledger = LEDGER_PATH.read_text(encoding="utf-8")

    for link in REQUIRED_LINKS:
        assert link in readme
        assert Path(link).exists()

    assert "- [x] optional voice STT/TTS provider benchmark execution approval" in todo
    assert "- [x] optional voice STT/TTS provider benchmark smoke execution" in todo
    assert "- [x] optional voice STT/TTS managed provider smoke approval" in todo
    assert "- [ ] optional voice STT/TTS managed provider smoke execution" in todo
    assert "HD-VOICE-STT-TTS-PROVIDER-BENCH-SMOKE-LOCAL-001" in ledger

    for path in PUBLIC_SCAN_PATHS:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)
        assert "private_data/" not in text


def test_execution_approval_keeps_forbidden_claims_forbidden() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    forbidden_section = doc.split("## Claim Boundary", maxsplit=1)[1]

    for claim in FORBIDDEN_CLAIMS:
        assert claim in forbidden_section
