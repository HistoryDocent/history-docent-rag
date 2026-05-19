from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import yaml

from pipelines.voice_stt_tts_provider_bench_readiness import (
    REQUIRED_PROVIDER_IDS,
    REQUIRED_QUERY_TYPES,
    collect_voice_readiness_failures,
    load_voice_benchmark_scripts,
    load_voice_provider_config,
    run_voice_stt_tts_provider_bench_readiness,
)


DOC_PATH = Path("docs/VOICE_STT_TTS_PROVIDER_BENCH_READINESS.md")
REPORT_PATH = Path("evals/reports/voice_stt_tts_provider_bench_readiness_report.md")
CONFIG_PATH = Path("configs/voice_provider_candidates.yaml")
SCRIPTS_PATH = Path("data_samples/voice_benchmark_scripts.sample.jsonl")
README_PATH = Path("README.md")
TODO_PATH = Path("docs/TODO.md")
LEDGER_PATH = Path("docs/RAG_DECISION_LEDGER.md")
REQUIRED_LINKS = (
    "docs/VOICE_STT_TTS_PROVIDER_BENCH_READINESS.md",
    "evals/reports/voice_stt_tts_provider_bench_readiness_report.md",
)
PUBLIC_SCAN_PATHS = (
    README_PATH,
    DOC_PATH,
    REPORT_PATH,
    CONFIG_PATH,
    SCRIPTS_PATH,
    TODO_PATH,
    LEDGER_PATH,
    Path("docs/CHECKLIST.md"),
    Path("docs/WBS.md"),
    Path("docs/ROADMAP.md"),
)
FORBIDDEN_CLAIMS = (
    "provider 최종 선택 완료",
    "STT/TTS 품질 검증 완료",
    "음성 관광 앱 완성",
)


def test_voice_provider_readiness_runner_outputs_pass_report(tmp_path: Path) -> None:
    report = run_voice_stt_tts_provider_bench_readiness(
        doc_path=tmp_path / "VOICE_STT_TTS_PROVIDER_BENCH_READINESS.md",
        report_path=tmp_path / "voice_stt_tts_provider_bench_readiness_report.md",
        result_rows_path=tmp_path / "voice_stt_tts_provider_bench_readiness_rows.jsonl",
    )

    assert collect_voice_readiness_failures(report) == []
    assert report.summary.provider_candidate_group_count == 5
    assert report.summary.official_source_checked_count == 14
    assert report.summary.pricing_source_link_count == 5
    assert report.summary.privacy_source_link_count == 4
    assert report.summary.benchmark_script_count == 30
    assert report.summary.benchmark_query_type_count == 6
    assert report.summary.script_per_query_type_min_count == 5
    assert report.summary.provider_finalized_count == 0
    assert report.summary.provider_benchmark_execution_count == 0
    assert report.summary.live_stt_call_count == 0
    assert report.summary.live_tts_call_count == 0
    assert report.summary.live_solar_call_count == 0
    assert report.summary.private_audio_saved_count == 0
    assert report.summary.raw_transcript_public_artifact_count == 0
    assert report.summary.client_secret_exposure_count == 0
    assert report.summary.public_private_path_leakage_count == 0
    assert report.summary.public_secret_like_leakage_count == 0
    assert report.summary.public_raw_payload_leakage_count == 0
    assert report.summary.readiness_decision == (
        "ready_for_provider_benchmark_execution_approval"
    )
    assert report.cuda_preflight.resolved_device in {"cuda", "cpu"}

    rows = [
        json.loads(line)
        for line in (tmp_path / "voice_stt_tts_provider_bench_readiness_rows.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert rows
    assert all("script_text" not in row for row in rows)
    assert all("raw_transcript" not in row for row in rows)


def test_voice_provider_readiness_config_and_scripts_are_complete() -> None:
    config = load_voice_provider_config(CONFIG_PATH)
    scripts = load_voice_benchmark_scripts(SCRIPTS_PATH)
    config_payload = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))

    assert config.work_id == "HD-VOICE-STT-TTS-PROVIDER-BENCH-READINESS-001"
    assert {row.provider_candidate_id for row in config.provider_candidates} == set(
        REQUIRED_PROVIDER_IDS,
    )
    assert len(config.official_sources) == 14
    assert sum(1 for row in config.official_sources if row.source_kind == "pricing") == 5
    assert sum(1 for row in config.official_sources if row.source_kind == "privacy") == 4
    assert config.source_policy.live_execution_enabled is False
    assert config.source_policy.benchmark_execution_enabled is False
    assert config_payload["source_policy"]["pricing_recheck_required"] is True
    assert config_payload["source_policy"]["privacy_recheck_required"] is True

    counts = Counter(script.query_type for script in scripts)
    assert len(scripts) == 30
    assert set(counts) == set(REQUIRED_QUERY_TYPES)
    assert all(count == 5 for count in counts.values())
    assert all(script.public_allowed for script in scripts)
    assert not any(script.audio_artifact_required for script in scripts)
    assert not any(script.raw_audio_saved for script in scripts)


def test_voice_provider_readiness_docs_are_registered_and_sanitized() -> None:
    assert DOC_PATH.exists()
    assert REPORT_PATH.exists()
    assert CONFIG_PATH.exists()
    assert SCRIPTS_PATH.exists()

    readme = README_PATH.read_text(encoding="utf-8")
    todo = TODO_PATH.read_text(encoding="utf-8")
    ledger = LEDGER_PATH.read_text(encoding="utf-8")

    for link in REQUIRED_LINKS:
        assert link in readme
        assert Path(link).exists()

    assert "- [x] optional voice STT/TTS provider benchmark readiness" in todo
    assert "- [ ] optional voice STT/TTS provider benchmark execution approval" in todo
    assert "HD-VOICE-STT-TTS-PROVIDER-BENCH-EXECUTION-APPROVAL-001" in ledger

    for path in PUBLIC_SCAN_PATHS:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)
        assert "private_data/" not in text


def test_voice_provider_readiness_report_records_quantitative_gates() -> None:
    report = REPORT_PATH.read_text(encoding="utf-8")
    doc = DOC_PATH.read_text(encoding="utf-8")

    assert "provider_candidate_group_count | 5" in report
    assert "official_source_checked_count | 14" in report
    assert "pricing_source_link_count | 5" in report
    assert "privacy_source_link_count | 4" in report
    assert "benchmark_script_count | 30" in report
    assert "benchmark_query_type_count | 6" in report
    assert "script_per_query_type_min_count | 5" in report
    assert "local_cuda_available_count | 1" in report
    assert "cuda_device_count | 1" in report
    assert "provider_finalized_count | 0" in report
    assert "provider_benchmark_execution_count | 0" in report
    assert "live_stt_call_count | 0" in report
    assert "live_tts_call_count | 0" in report
    assert "live_solar_call_count | 0" in report
    assert "private_audio_saved_count | 0" in report
    assert "raw_transcript_public_artifact_count | 0" in report
    assert "client_secret_exposure_count | 0" in report
    assert "pricing_claim_without_source_count | 0" in report
    assert "privacy_policy_unknown_count | 0" in report
    assert "public_private_path_leakage_count | 0" in report
    assert "public_secret_like_leakage_count | 0" in report
    assert "public_raw_payload_leakage_count | 0" in report
    assert "External audit | PASS" in report
    assert "fact_voice_stt_tts_provider_bench_readiness" in report

    forbidden_section = doc.split("## Claim Boundary", maxsplit=1)[1]
    for claim in FORBIDDEN_CLAIMS:
        assert claim in forbidden_section
