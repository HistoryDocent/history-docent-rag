from __future__ import annotations

import json
import re
from pathlib import Path
from types import SimpleNamespace

import pipelines.voice_local_korean_tts_alternative_review as tts_review


DOC_PATH = Path("docs/VOICE_LOCAL_KOREAN_TTS_ALTERNATIVE_REVIEW.md")
REPORT_PATH = Path("evals/reports/voice_local_korean_tts_alternative_review_report.md")
README_PATH = Path("README.md")
TODO_PATH = Path("docs/TODO.md")
LEDGER_PATH = Path("docs/RAG_DECISION_LEDGER.md")
CHECKLIST_PATH = Path("docs/CHECKLIST.md")
WBS_PATH = Path("docs/WBS.md")
ROADMAP_PATH = Path("docs/ROADMAP.md")
VOICE_DECISION_PATH = Path("docs/VOICE_PROVIDER_DECISION.md")
REQUIRED_LINKS = (
    "docs/VOICE_LOCAL_KOREAN_TTS_ALTERNATIVE_REVIEW.md",
    "evals/reports/voice_local_korean_tts_alternative_review_report.md",
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
    "Supertonic 3 또는 sherpa-onnx 한국어 TTS 품질 검증 완료",
    "무료 로컬 TTS 최종 provider 확정",
    "실제 관광객 음성 품질 검증 완료",
    "production 음성 관광 앱 완성",
)


def test_korean_tts_alternative_review_runner_public_safe_contract(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        tts_review,
        "build_cuda_preflight",
        lambda: SimpleNamespace(
            resolved_device="cuda",
            cuda_device_name="NVIDIA GeForce RTX 4080 SUPER",
            local_cuda_available=True,
            cuda_device_count=1,
        ),
    )

    report = tts_review.run_voice_local_korean_tts_alternative_review(
        doc_path=tmp_path / "VOICE_LOCAL_KOREAN_TTS_ALTERNATIVE_REVIEW.md",
        report_path=tmp_path / "voice_local_korean_tts_alternative_review_report.md",
        result_rows_path=tmp_path / "voice_local_korean_tts_alternative_review_rows.jsonl",
    )

    assert tts_review.collect_korean_tts_alternative_review_failures(report) == []
    assert report.summary.candidate_count == 7
    assert report.summary.source_reference_count == 10
    assert report.summary.source_checked_candidate_count == 7
    assert report.summary.korean_support_candidate_count >= 5
    assert report.summary.selected_next_smoke_candidate_count == 1
    assert report.summary.selected_next_smoke_candidate_id == "local_sherpa_onnx_supertonic3_ko"
    assert report.summary.package_install_attempted_count == 0
    assert report.summary.model_download_attempted_count == 0
    assert report.summary.local_tts_execution_count == 0
    assert report.summary.live_tts_call_count == 0
    assert report.summary.external_provider_call_count == 0
    assert report.summary.external_audio_transmission_count == 0
    assert report.summary.raw_audio_public_artifact_count == 0
    assert report.summary.raw_transcript_public_artifact_count == 0
    assert report.summary.review_decision == "select_sherpa_onnx_supertonic3_for_smoke"

    rows = [
        json.loads(line)
        for line in (tmp_path / "voice_local_korean_tts_alternative_review_rows.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(rows) == 7
    assert [row for row in rows if row["decision"] == "selected_next_smoke"][0][
        "provider_candidate_id"
    ] == "local_sherpa_onnx_supertonic3_ko"
    assert all("script_text" not in row for row in rows)
    assert all("raw_transcript" not in row for row in rows)
    assert all("raw_audio" not in row for row in rows)
    assert all("audio_path" not in row for row in rows)


def test_korean_tts_alternative_review_docs_record_selected_candidate() -> None:
    assert DOC_PATH.exists()
    assert REPORT_PATH.exists()

    doc = DOC_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert tts_review.WORK_ID in doc
    assert tts_review.WORK_ID in report
    assert "candidate_count | 7" in report
    assert "source_reference_count | 10" in report
    assert "source_checked_candidate_count | 7" in report
    assert "selected_next_smoke_candidate_count | 1" in report
    assert "selected_next_smoke_candidate_id | `local_sherpa_onnx_supertonic3_ko`" in report
    assert "package_install_attempted_count | 0" in report
    assert "model_download_attempted_count | 0" in report
    assert "local_tts_execution_count | 0" in report
    assert "live_tts_call_count | 0" in report
    assert "external_provider_call_count | 0" in report
    assert "external_audio_transmission_count | 0" in report
    assert "raw_audio_public_artifact_count | 0" in report
    assert "raw_transcript_public_artifact_count | 0" in report
    assert "public_private_path_leakage_count | 0" in report
    assert "public_secret_like_leakage_count | 0" in report
    assert "public_raw_payload_leakage_count | 0" in report
    assert "review_decision | `select_sherpa_onnx_supertonic3_for_smoke`" in report
    assert "External audit | PASS" in report


def test_korean_tts_alternative_review_registered_and_public_safe() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    todo = TODO_PATH.read_text(encoding="utf-8")
    ledger = LEDGER_PATH.read_text(encoding="utf-8")

    for link in REQUIRED_LINKS:
        assert link in readme
        assert Path(link).exists()

    assert "- [x] optional Korean TTS alternative review" in todo
    assert "- [ ] optional sherpa-onnx Supertonic 3 Korean TTS smoke" in todo
    assert tts_review.WORK_ID in ledger

    for path in PUBLIC_SCAN_PATHS:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"private_data[/\\]", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)


def test_korean_tts_alternative_review_keeps_forbidden_claims_forbidden() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    forbidden_section = doc.split("금지 claim:", maxsplit=1)[1]

    for claim in FORBIDDEN_CLAIMS:
        assert claim in forbidden_section
