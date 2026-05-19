from __future__ import annotations

import re
from pathlib import Path


DOC_PATH = Path("docs/VOICE_STT_TTS_PROVIDER_BENCH_PLAN.md")
REPORT_PATH = Path("evals/reports/voice_stt_tts_provider_bench_plan_report.md")
README_PATH = Path("README.md")
TODO_PATH = Path("docs/TODO.md")
LEDGER_PATH = Path("docs/RAG_DECISION_LEDGER.md")
REQUIRED_LINKS = (
    "docs/VOICE_STT_TTS_PROVIDER_BENCH_PLAN.md",
    "evals/reports/voice_stt_tts_provider_bench_plan_report.md",
)
PUBLIC_SCAN_PATHS = (
    README_PATH,
    DOC_PATH,
    REPORT_PATH,
    TODO_PATH,
    LEDGER_PATH,
    Path("docs/CHECKLIST.md"),
    Path("docs/WBS.md"),
    Path("docs/ROADMAP.md"),
)
REQUIRED_CANDIDATES = (
    "browser_native_web_speech",
    "local_cuda_whisper",
    "external_google_cloud",
    "external_azure_speech",
    "external_aws_transcribe_polly",
)
FORBIDDEN_CLAIMS = (
    "production 성능 검증 완료",
    "locked test에서 최종 성능 개선 입증",
    "GraphRAG로 성능 개선",
    "RAPTOR로 성능 개선",
    "HyDE로 최종 검색 성능 개선",
    "Solar Pro 3 답변 품질 최종 개선",
    "음성 관광 앱 완성",
    "STT/TTS 품질 검증 완료",
    "provider 최종 선택 완료",
    "전체 도서 데이터 공개",
)


def test_voice_stt_tts_provider_bench_plan_docs_exist_and_are_sanitized() -> None:
    assert DOC_PATH.exists()
    assert REPORT_PATH.exists()

    for path in PUBLIC_SCAN_PATHS:
        text = path.read_text(encoding="utf-8")

        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)
        assert "private_data/" not in text


def test_voice_stt_tts_provider_bench_plan_registered_in_readme_todo_ledger() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    todo = TODO_PATH.read_text(encoding="utf-8")
    ledger = LEDGER_PATH.read_text(encoding="utf-8")

    for link in REQUIRED_LINKS:
        assert link in readme
        assert Path(link).exists()

    assert "- [x] optional voice STT/TTS provider benchmark plan" in todo
    assert "- [x] optional voice STT/TTS provider benchmark readiness" in todo
    assert "- [x] optional voice STT/TTS provider benchmark execution approval" in todo
    assert "- [x] optional voice STT/TTS provider benchmark smoke execution" in todo
    assert "- [x] optional voice STT/TTS managed provider smoke approval" in todo
    assert "- [ ] optional voice STT/TTS managed provider smoke execution" in todo
    assert "HD-VOICE-STT-TTS-PROVIDER-BENCH-READINESS-001" in ledger
    assert "HD-VOICE-STT-TTS-PROVIDER-BENCH-SMOKE-LOCAL-001" in ledger


def test_voice_stt_tts_provider_bench_plan_records_scope_sources_and_cuda() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")

    assert "## Provider Candidate Groups" in doc
    assert "## 공식 문서 확인" in doc
    assert "## Local CUDA Readiness" in doc
    assert "## Benchmark Dataset Plan" in doc
    assert "## Planned Call Budget" in doc
    assert "## Stop Conditions" in doc
    assert "fact_voice_stt_tts_provider_bench_plan" in doc
    assert "확인일: 2026-05-19" in doc
    assert "NVIDIA GeForce RTX 4080 SUPER" in doc
    assert "`live_stt_call_count` | 0" in doc
    assert "`live_tts_call_count` | 0" in doc
    assert "`live_solar_call_count` | 0" in doc

    for candidate in REQUIRED_CANDIDATES:
        assert candidate in doc


def test_voice_stt_tts_provider_bench_plan_keeps_forbidden_claims_as_forbidden() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    forbidden_section = doc.split("## 금지 Claim", maxsplit=1)[1]

    for claim in FORBIDDEN_CLAIMS:
        assert claim in forbidden_section


def test_voice_stt_tts_provider_bench_plan_report_records_quantitative_gates() -> None:
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert "voice_stt_tts_provider_bench_plan_document_count | 1" in report
    assert "voice_stt_tts_provider_bench_plan_report_count | 1" in report
    assert "provider_candidate_group_count | 5" in report
    assert "official_source_checked_count | 14" in report
    assert "pricing_source_link_count | 5" in report
    assert "privacy_source_link_count | 4" in report
    assert "benchmark_query_type_count | 6" in report
    assert "planned_public_safe_script_min_count | 30" in report
    assert "local_cuda_available_count | 1" in report
    assert "cuda_device_count | 1" in report
    assert "live_stt_call_count | 0" in report
    assert "live_tts_call_count | 0" in report
    assert "live_solar_call_count | 0" in report
    assert "provider_finalized_count | 0" in report
    assert "provider_benchmark_execution_count | 0" in report
    assert "private_audio_saved_count | 0" in report
    assert "raw_transcript_public_artifact_count | 0" in report
    assert "client_secret_exposure_count | 0" in report
    assert "pricing_claim_without_source_count | 0" in report
    assert "privacy_policy_unknown_count | 0" in report
    assert "public_private_path_leakage_count | 0" in report
    assert "public_secret_like_leakage_count | 0" in report
    assert "public_raw_payload_leakage_count | 0" in report
    assert "External audit | PASS" in report
    assert "fact_voice_stt_tts_provider_bench_plan" in report
