from __future__ import annotations

import json
import re
from pathlib import Path
from types import SimpleNamespace

import numpy as np

import pipelines.voice_local_sherpa_onnx_supertonic3_ko_smoke as sherpa_smoke


DOC_PATH = Path("docs/VOICE_LOCAL_SHERPA_ONNX_SUPERTONIC3_KO_SMOKE.md")
REPORT_PATH = Path("evals/reports/voice_local_sherpa_onnx_supertonic3_ko_smoke_report.md")
README_PATH = Path("README.md")
TODO_PATH = Path("docs/TODO.md")
LEDGER_PATH = Path("docs/RAG_DECISION_LEDGER.md")
CHECKLIST_PATH = Path("docs/CHECKLIST.md")
WBS_PATH = Path("docs/WBS.md")
ROADMAP_PATH = Path("docs/ROADMAP.md")
VOICE_DECISION_PATH = Path("docs/VOICE_PROVIDER_DECISION.md")
SCRIPTS_PATH = Path("data_samples/voice_tts_smoke_scripts.sample.jsonl")
REQUIRED_LINKS = (
    "docs/VOICE_LOCAL_SHERPA_ONNX_SUPERTONIC3_KO_SMOKE.md",
    "evals/reports/voice_local_sherpa_onnx_supertonic3_ko_smoke_report.md",
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
    "무료 로컬 TTS 최종 provider 확정",
    "Supertonic 3 음성 품질 우수 검증 완료",
    "production 음성 관광 앱 완성",
    "CUDA TTS acceleration 검증 완료",
)


class _FakeAudio:
    sample_rate = 44100
    samples = np.zeros(4410, dtype=np.float32)


class _FakeSherpaTts:
    use_generation_config = False

    def generate(self, text: str, *, sid: int, speed: float) -> _FakeAudio:
        assert text
        assert sid == 0
        assert speed == 1.0
        return _FakeAudio()


def _fake_tts_factory(model_dir: Path, provider: str, num_threads: int) -> _FakeSherpaTts:
    assert provider == "cpu"
    assert num_threads == 2
    assert model_dir.exists()
    return _FakeSherpaTts()


def _create_fake_model_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for file_name in sherpa_smoke.MODEL_FILE_NAMES:
        (path / file_name).write_text("fixture", encoding="utf-8")
    (path / sherpa_smoke.LICENSE_FILE_NAME).write_text("fixture license", encoding="utf-8")


def test_sherpa_onnx_supertonic3_ko_smoke_runner_public_safe_contract(
    tmp_path: Path,
    monkeypatch,
) -> None:
    model_dir = tmp_path / "model"
    archive_path = tmp_path / "model.tar.bz2"
    archive_path.write_bytes(b"fixture")
    _create_fake_model_dir(model_dir)
    monkeypatch.setattr(
        sherpa_smoke,
        "build_cuda_preflight",
        lambda: SimpleNamespace(
            resolved_device="cuda",
            cuda_device_name="NVIDIA GeForce RTX 4080 SUPER",
            local_cuda_available=True,
            torch_cuda_available=True,
            cuda_device_count=1,
            cuda_runtime_probe_error_count=0,
        ),
    )
    monkeypatch.setattr(sherpa_smoke, "resolve_sherpa_onnx_version", lambda: "1.13.2")

    report = sherpa_smoke.run_voice_local_sherpa_onnx_supertonic3_ko_smoke(
        doc_path=tmp_path / "VOICE_LOCAL_SHERPA_ONNX_SUPERTONIC3_KO_SMOKE.md",
        report_path=tmp_path / "voice_local_sherpa_onnx_supertonic3_ko_smoke_report.md",
        result_rows_path=tmp_path / "voice_local_sherpa_onnx_supertonic3_ko_smoke_rows.jsonl",
        private_audio_dir=tmp_path / "audio",
        model_dir=model_dir,
        archive_path=archive_path,
        execute_local_tts=True,
        require_local_execution=True,
        package_install_attempted=True,
        model_download_attempted=True,
        model_download_success=True,
        tts_factory=_fake_tts_factory,
    )

    assert sherpa_smoke.collect_sherpa_onnx_tts_smoke_failures(
        report,
        require_local_execution=True,
    ) == []
    assert report.summary.selected_script_count == 5
    assert report.summary.package_install_attempted_count == 1
    assert report.summary.package_install_success_count == 1
    assert report.summary.sherpa_runtime_available_count == 1
    assert report.summary.model_download_attempted_count == 1
    assert report.summary.model_download_success_count == 1
    assert report.summary.model_file_available_count == 7
    assert report.summary.model_license_recorded_count == 1
    assert report.summary.local_tts_execution_count == 5
    assert report.summary.local_cuda_tts_call_count == 0
    assert report.summary.private_audio_generated_count == 5
    assert report.summary.private_audio_saved_count == 5
    assert report.summary.sample_rate_hz == 44100
    assert report.summary.resolved_device == "cuda"
    assert report.summary.sherpa_tts_provider == "cpu"
    assert report.summary.external_provider_call_count == 0
    assert report.summary.external_audio_transmission_count == 0
    assert report.summary.raw_audio_public_artifact_count == 0
    assert report.summary.raw_transcript_public_artifact_count == 0
    assert (
        report.summary.tts_smoke_decision
        == "completed_local_sherpa_onnx_supertonic3_ko_smoke"
    )

    rows = [
        json.loads(line)
        for line in (tmp_path / "voice_local_sherpa_onnx_supertonic3_ko_smoke_rows.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(rows) == 5
    assert all(row["provider_candidate_id"] == "local_sherpa_onnx_supertonic3_ko" for row in rows)
    assert all(row["synthesis_status"] == "executed" for row in rows)
    assert all("script_text" not in row for row in rows)
    assert all("raw_transcript" not in row for row in rows)
    assert all("raw_audio" not in row for row in rows)
    assert all("audio_path" not in row for row in rows)


def test_sherpa_onnx_smoke_docs_record_execution() -> None:
    assert DOC_PATH.exists()
    assert REPORT_PATH.exists()
    assert SCRIPTS_PATH.exists()

    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert sherpa_smoke.WORK_ID in doc
    assert sherpa_smoke.WORK_ID in report
    assert "package_install_attempted_count | 1" in report
    assert "package_install_success_count | 1" in report
    assert "sherpa_runtime_available_count | 1" in report
    assert "model_download_attempted_count | 1" in report
    assert "model_download_success_count | 1" in report
    assert "model_file_available_count | 7" in report
    assert "model_license_recorded_count | 1" in report
    assert "local_tts_execution_count | 5" in report
    assert "local_cuda_tts_call_count | 0" in report
    assert "external_provider_call_count | 0" in report
    assert "external_audio_transmission_count | 0" in report
    assert "raw_audio_public_artifact_count | 0" in report
    assert "raw_transcript_public_artifact_count | 0" in report
    assert "public_private_path_leakage_count | 0" in report
    assert "public_secret_like_leakage_count | 0" in report
    assert "public_raw_payload_leakage_count | 0" in report
    assert (
        "tts_smoke_decision | `completed_local_sherpa_onnx_supertonic3_ko_smoke`"
        in report
    )
    assert "External audit | PASS" in report


def test_sherpa_onnx_smoke_registered_and_public_safe() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    todo = TODO_PATH.read_text(encoding="utf-8")
    ledger = LEDGER_PATH.read_text(encoding="utf-8")

    for link in REQUIRED_LINKS:
        assert link in readme
        assert Path(link).exists()

    assert "- [x] optional sherpa-onnx Supertonic 3 Korean TTS smoke" in todo
    assert "- [x] optional TTS quality listening review" in todo
    assert "- [ ] optional human TTS listening score fill" in todo
    assert sherpa_smoke.WORK_ID in ledger
    assert "voice_local_sherpa_onnx_supertonic3_ko_smoke" in ledger

    for path in PUBLIC_SCAN_PATHS:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"private_data[/\\]", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)


def test_sherpa_onnx_smoke_keeps_forbidden_claims_forbidden() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    forbidden_section = doc.split("## Claim Boundary", maxsplit=1)[1]

    for claim in FORBIDDEN_CLAIMS:
        assert claim in forbidden_section
