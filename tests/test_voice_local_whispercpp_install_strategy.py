from __future__ import annotations

import re
from pathlib import Path


DOC_PATH = Path("docs/VOICE_LOCAL_WHISPERCPP_INSTALL_STRATEGY.md")
REPORT_PATH = Path("evals/reports/voice_local_whispercpp_install_strategy_report.md")
README_PATH = Path("README.md")

REQUIRED_README_LINKS = (
    "docs/VOICE_LOCAL_WHISPERCPP_INSTALL_STRATEGY.md",
    "evals/reports/voice_local_whispercpp_install_strategy_report.md",
)

PUBLIC_SCAN_PATHS = (
    README_PATH,
    DOC_PATH,
    REPORT_PATH,
    Path("docs/VOICE_LOCAL_WHISPERCPP_INSTALL_READINESS.md"),
    Path("docs/RAG_DECISION_LEDGER.md"),
    Path("docs/TODO.md"),
    Path("docs/WBS.md"),
    Path("docs/ROADMAP.md"),
    Path("docs/CHECKLIST.md"),
    Path("docs/VOICE_DEMO_STACK_DECISION.md"),
)

FORBIDDEN_CLAIMS = (
    "`whisper.cpp` 설치 완료",
    "`whisper.cpp` CUDA build 완료",
    "`ggml` model 다운로드 완료",
    "`whisper.cpp` STT 실행 성공",
    "`whisper.cpp` production STT provider 확정",
    "STT/TTS production 품질 검증 완료",
    "실제 관광객 음성 품질 검증 완료",
    "음성 관광 앱 완성",
    "GitHub push 완료",
)


def test_whispercpp_install_strategy_docs_exist_and_are_sanitized() -> None:
    assert DOC_PATH.exists()
    assert REPORT_PATH.exists()

    for path in PUBLIC_SCAN_PATHS:
        text = path.read_text(encoding="utf-8")

        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"private_data[/\\]", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)


def test_whispercpp_install_strategy_readme_links_exist() -> None:
    readme = README_PATH.read_text(encoding="utf-8")

    for link in REQUIRED_README_LINKS:
        assert link in readme
        assert Path(link).exists()


def test_whispercpp_install_strategy_selects_defer_strategy_without_execution() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    required_phrases = (
        "HD-VOICE-LOCAL-WHISPERCPP-INSTALL-STRATEGY-001",
        "HD-VOICE-LOCAL-WHISPERCPP-INSTALL-READINESS-001",
        "strategy_option_count | 3",
        "selected_strategy_count | 1",
        "selected_keep_faster_whisper_count | 1",
        "selected_source_build_count | 0",
        "selected_prebuilt_binary_count | 0",
        "source_provenance_recheck_required_count | 1",
        "binary_provenance_recheck_required_count | 1",
        "model_provenance_recheck_required_count | 1",
        "toolchain_blocker_retained_count | 1",
        "runtime_build_attempted_count | 0",
        "model_download_attempted_count | 0",
        "local_stt_execution_count | 0",
        "external_provider_call_count | 0",
        "push_command_execution_count | 0",
        "selected_strategy | `defer_whispercpp_keep_faster_whisper_primary`",
        "HD-GITHUB-PUSH-EXECUTION-001",
        "HD-VOICE-LOCAL-WHISPERCPP-INSTALL-EXECUTION-001",
    )
    for phrase in required_phrases:
        assert phrase in doc or phrase in report

    assert "External audit | PASS" in report
    assert "fact_voice_local_whispercpp_install_strategy" in report


def test_whispercpp_install_strategy_keeps_forbidden_claims_forbidden() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")
    doc_forbidden_section = doc.split("## 말하면 안 되는 문장", maxsplit=1)[1]
    report_forbidden_section = report.split("## 금지:", maxsplit=1)[1]

    for claim in FORBIDDEN_CLAIMS:
        assert claim in doc_forbidden_section
        assert claim in report_forbidden_section
