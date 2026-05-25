from __future__ import annotations

import re
from pathlib import Path


DOC_PATH = Path("docs/VOICE_LOCAL_WHISPERCPP_DEPLOYMENT_RETRY.md")
REPORT_PATH = Path("evals/reports/voice_local_whispercpp_deployment_retry_report.md")
README_PATH = Path("README.md")

REQUIRED_README_LINKS = (
    "docs/VOICE_LOCAL_WHISPERCPP_DEPLOYMENT_RETRY.md",
    "evals/reports/voice_local_whispercpp_deployment_retry_report.md",
)

PUBLIC_SCAN_PATHS = (
    README_PATH,
    DOC_PATH,
    REPORT_PATH,
    Path("docs/VOICE_LOCAL_WHISPERCPP_DEPLOYMENT_SMOKE.md"),
    Path("docs/RAG_DECISION_LEDGER.md"),
    Path("docs/TODO.md"),
    Path("docs/WBS.md"),
    Path("docs/ROADMAP.md"),
    Path("docs/CHECKLIST.md"),
    Path("docs/VOICE_DEMO_STACK_DECISION.md"),
)

FORBIDDEN_CLAIMS = (
    "`whisper.cpp` CUDA 실행 성공",
    "`whisper.cpp` production STT provider 확정",
    "`whisper.cpp`가 faster-whisper보다 우수함",
    "STT/TTS production 품질 검증 완료",
    "실제 관광객 음성 품질 검증 완료",
    "음성 관광 앱 완성",
    "GitHub push 완료",
)


def test_whispercpp_deployment_retry_docs_exist_and_are_sanitized() -> None:
    assert DOC_PATH.exists()
    assert REPORT_PATH.exists()

    for path in PUBLIC_SCAN_PATHS:
        text = path.read_text(encoding="utf-8")

        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"private_data[/\\]", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)


def test_whispercpp_deployment_retry_readme_links_exist() -> None:
    readme = README_PATH.read_text(encoding="utf-8")

    for link in REQUIRED_README_LINKS:
        assert link in readme
        assert Path(link).exists()


def test_whispercpp_deployment_retry_records_current_blocker_metrics() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    required_phrases = (
        "HD-VOICE-LOCAL-WHISPERCPP-DEPLOYMENT-RETRY-001",
        "HD-VOICE-LOCAL-WHISPERCPP-DEPLOYMENT-SMOKE-001",
        "whisper_cpp_runtime_available_count | 0",
        "whisper_cpp_model_file_available_count | 0",
        "local_cuda_available_count | 1",
        "local_stt_execution_requested_count | 5",
        "local_stt_execution_count | 0",
        "package_install_attempted_count | 0",
        "model_download_attempted_count | 0",
        "external_provider_call_count | 0",
        "external_audio_transmission_count | 0",
        "push_command_execution_count | 0",
        "deployment_decision | `still_blocked_missing_whispercpp_runtime`",
        "recommended_stt_candidate_id | `local_faster_whisper_small_cuda`",
        "HD-VOICE-LOCAL-WHISPERCPP-INSTALL-APPROVAL-001",
    )
    for phrase in required_phrases:
        assert phrase in doc or phrase in report

    assert "External audit | PASS" in report
    assert "fact_voice_local_whispercpp_deployment_retry" in report


def test_whispercpp_deployment_retry_keeps_forbidden_claims_forbidden() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")
    doc_forbidden_section = doc.split("## 말하면 안 되는 문장", maxsplit=1)[1]
    report_forbidden_section = report.split("## 금지:", maxsplit=1)[1]

    for claim in FORBIDDEN_CLAIMS:
        assert claim in doc_forbidden_section
        assert claim in report_forbidden_section
