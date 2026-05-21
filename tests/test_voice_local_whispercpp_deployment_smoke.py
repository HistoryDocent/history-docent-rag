from __future__ import annotations

import json
import re
from pathlib import Path

import pipelines.voice_local_whispercpp_deployment_smoke as whispercpp


DOC_PATH = Path("docs/VOICE_LOCAL_WHISPERCPP_DEPLOYMENT_SMOKE.md")
REPORT_PATH = Path("evals/reports/voice_local_whispercpp_deployment_smoke_report.md")
README_PATH = Path("README.md")
TODO_PATH = Path("docs/TODO.md")
LEDGER_PATH = Path("docs/RAG_DECISION_LEDGER.md")
CHECKLIST_PATH = Path("docs/CHECKLIST.md")
WBS_PATH = Path("docs/WBS.md")
ROADMAP_PATH = Path("docs/ROADMAP.md")
VOICE_DECISION_PATH = Path("docs/VOICE_PROVIDER_DECISION.md")
REQUIRED_LINKS = (
    "docs/VOICE_LOCAL_WHISPERCPP_DEPLOYMENT_SMOKE.md",
    "evals/reports/voice_local_whispercpp_deployment_smoke_report.md",
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
    VOICE_DECISION_PATH,
)
FORBIDDEN_CLAIMS = (
    "`whisper.cpp`가 production 최종 STT provider라는 주장",
    "`whisper.cpp` CUDA 실행이 실제로 성공했다는 주장, 성공 row가 없을 때",
    "STT/TTS 품질 최종 검증 완료",
    "실제 관광객 음성 품질 검증 완료",
    "음성 관광 앱 완성",
)


def test_whispercpp_runner_records_blocker_without_runtime_or_model(tmp_path: Path) -> None:
    report = whispercpp.run_voice_local_whispercpp_deployment_smoke(
        doc_path=tmp_path / "VOICE_LOCAL_WHISPERCPP_DEPLOYMENT_SMOKE.md",
        report_path=tmp_path / "voice_local_whispercpp_deployment_smoke_report.md",
        result_rows_path=tmp_path / "voice_local_whispercpp_deployment_smoke_rows.jsonl",
        private_transcript_dir=tmp_path / "private_transcripts",
        detect_runtime=False,
        detect_model=False,
        execute_whisper_cpp=True,
        require_execution=False,
    )

    assert whispercpp.collect_whispercpp_deployment_smoke_failures(
        report,
        require_execution=False,
    ) == []
    assert report.summary.selected_script_count == 5
    assert report.summary.whisper_cpp_runtime_available_count == 0
    assert report.summary.whisper_cpp_model_file_available_count == 0
    assert report.summary.local_stt_execution_requested_count == 5
    assert report.summary.local_stt_execution_count == 0
    assert report.summary.blocked_missing_runtime_count == 5
    assert report.summary.external_provider_call_count == 0
    assert report.summary.external_audio_transmission_count == 0
    assert report.summary.raw_audio_public_artifact_count == 0
    assert report.summary.raw_transcript_public_artifact_count == 0
    assert report.summary.deployment_decision == "blocked_missing_whispercpp_runtime"

    rows = [
        json.loads(line)
        for line in (tmp_path / "voice_local_whispercpp_deployment_smoke_rows.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(rows) == 5
    assert all(row["status"] == "blocked_missing_runtime" for row in rows)
    assert all("script_text" not in row for row in rows)
    assert all("raw_transcript" not in row for row in rows)
    assert all("raw_audio" not in row for row in rows)
    assert all("audio_path" not in row for row in rows)


def test_whispercpp_runner_supports_comparable_metric_schema_with_stub_execution(
    tmp_path: Path,
) -> None:
    cli_path = tmp_path / "whisper-cli.exe"
    model_path = tmp_path / "ggml-small.bin"
    audio_dir = tmp_path / "audio"
    cli_path.write_text("fixture", encoding="utf-8")
    model_path.write_bytes(b"fixture model")
    audio_dir.mkdir(parents=True)

    scripts = whispercpp.select_local_smoke_scripts(
        whispercpp.load_voice_benchmark_scripts(whispercpp.project_path(whispercpp.DEFAULT_SCRIPTS_PATH)),
        limit=5,
    )
    for script in scripts:
        (audio_dir / f"{script.script_id}.wav").write_bytes(b"fixture wav")

    def fake_transcriber(
        script: whispercpp.VoiceBenchmarkScript,
        _runtime_path: Path,
        _model_path: Path,
        _audio_path: Path,
        _output_prefix: str,
    ) -> tuple[str, float]:
        return script.script_text, 12.0

    report = whispercpp.run_voice_local_whispercpp_deployment_smoke(
        private_audio_dir=audio_dir,
        private_transcript_dir=tmp_path / "private_transcripts",
        doc_path=tmp_path / "VOICE_LOCAL_WHISPERCPP_DEPLOYMENT_SMOKE.md",
        report_path=tmp_path / "voice_local_whispercpp_deployment_smoke_report.md",
        result_rows_path=tmp_path / "voice_local_whispercpp_deployment_smoke_rows.jsonl",
        whisper_cpp_cli_path=cli_path,
        whisper_cpp_model_path=model_path,
        detect_runtime=False,
        detect_model=False,
        transcriber=fake_transcriber,
    )

    assert whispercpp.collect_whispercpp_deployment_smoke_failures(
        report,
        require_execution=False,
    ) == []
    assert report.summary.whisper_cpp_runtime_available_count == 1
    assert report.summary.whisper_cpp_model_file_available_count == 1
    assert report.summary.local_stt_execution_count == 5
    assert report.summary.wer_avg == 0.0
    assert report.summary.cer_avg == 0.0
    assert report.summary.place_name_accuracy_avg == 1.0
    assert report.summary.stt_latency_p95_ms == 12.0
    assert report.summary.external_provider_call_count == 0
    assert report.summary.deployment_decision == "completed_whispercpp_smoke"


def test_whispercpp_docs_record_current_deployment_smoke_result() -> None:
    assert DOC_PATH.exists()
    assert REPORT_PATH.exists()

    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert whispercpp.WORK_ID in doc
    assert whispercpp.WORK_ID in report
    assert "selected_script_count | 5" in report
    assert "whisper_cpp_runtime_available_count | 0" in report
    assert "whisper_cpp_model_file_available_count | 0" in report
    assert "local_stt_execution_requested_count | 5" in report
    assert "local_stt_execution_count | 0" in report
    assert "external_provider_call_count | 0" in report
    assert "external_audio_transmission_count | 0" in report
    assert "raw_audio_public_artifact_count | 0" in report
    assert "raw_transcript_public_artifact_count | 0" in report
    assert "public_private_path_leakage_count | 0" in report
    assert "public_secret_like_leakage_count | 0" in report
    assert "public_raw_payload_leakage_count | 0" in report
    assert "deployment_decision | `blocked_missing_whispercpp_runtime`" in report
    assert "External audit | PASS" in report


def test_whispercpp_registered_and_public_safe() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    todo = TODO_PATH.read_text(encoding="utf-8")
    ledger = LEDGER_PATH.read_text(encoding="utf-8")

    for link in REQUIRED_LINKS:
        assert link in readme
        assert Path(link).exists()

    assert "- [x] optional whisper.cpp local STT deployment smoke" in todo
    assert whispercpp.WORK_ID in ledger
    assert "voice_local_whispercpp_deployment_smoke" in ledger

    for path in PUBLIC_SCAN_PATHS:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"private_data[/\\]", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)


def test_whispercpp_keeps_forbidden_claims_forbidden() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    forbidden_section = doc.split("금지 claim:", maxsplit=1)[1]

    for claim in FORBIDDEN_CLAIMS:
        assert claim in forbidden_section
