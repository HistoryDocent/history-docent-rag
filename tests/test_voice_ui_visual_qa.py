from __future__ import annotations

import re
import struct
from pathlib import Path


DOC_PATH = Path("docs/VOICE_UI_VISUAL_QA.md")
REPORT_PATH = Path("evals/reports/voice_ui_visual_qa_report.md")
ASSET_DIR = Path("evals/reports/assets")
SCREENSHOTS = {
    "voice_ui_visual_qa_desktop_answerable.jpg": (1280, 800),
    "voice_ui_visual_qa_mobile_no_answer.jpg": (390, 844),
    "voice_ui_visual_qa_desktop_error.jpg": (1280, 800),
}


def _jpeg_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data[:2] == b"\xff\xd8"

    index = 2
    sof_markers = {
        0xC0,
        0xC1,
        0xC2,
        0xC3,
        0xC5,
        0xC6,
        0xC7,
        0xC9,
        0xCA,
        0xCB,
        0xCD,
        0xCE,
        0xCF,
    }

    while index < len(data) - 1:
        if data[index] != 0xFF:
            index += 1
            continue

        while index < len(data) and data[index] == 0xFF:
            index += 1
        marker = data[index]
        index += 1

        if marker in {0xD8, 0xD9, 0x01} or 0xD0 <= marker <= 0xD7:
            continue

        segment_length = struct.unpack(">H", data[index : index + 2])[0]
        if marker in sof_markers:
            height = struct.unpack(">H", data[index + 3 : index + 5])[0]
            width = struct.unpack(">H", data[index + 5 : index + 7])[0]
            return width, height

        index += segment_length

    raise AssertionError(f"JPEG dimensions not found: {path}")


def test_voice_ui_visual_qa_docs_and_report_are_sanitized() -> None:
    for path in (
        DOC_PATH,
        REPORT_PATH,
        Path("README.md"),
        Path("docs/RAG_DECISION_LEDGER.md"),
        Path("docs/CHECKLIST.md"),
        Path("docs/TODO.md"),
    ):
        text = path.read_text(encoding="utf-8")

        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)
        assert "private_data/" not in text


def test_voice_ui_visual_qa_report_records_required_metrics() -> None:
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert "visual_qa_scenario_count | 3" in report
    assert "visual_qa_viewport_class_count | 2" in report
    assert "screenshot_artifact_count | 3" in report
    assert "desktop_answerable_citation_item_count | 1" in report
    assert "mobile_no_answer_workspace_single_column | true" in report
    assert "mobile_no_answer_citation_item_count | 0" in report
    assert "desktop_error_sanitized_error_visible | true" in report
    assert "desktop_error_raw_error_leaked | false" in report
    assert "live_solar_call_count | 0" in report
    assert "retrieval_execution_count | 0" in report
    assert "External audit | PASS" in report
    assert "fact_voice_ui_visual_qa" in report


def test_voice_ui_visual_qa_screenshot_artifacts_exist_with_expected_dimensions() -> None:
    for filename, expected_dimensions in SCREENSHOTS.items():
        path = ASSET_DIR / filename

        assert path.exists()
        assert path.stat().st_size > 1000
        assert _jpeg_dimensions(path) == expected_dimensions


def test_voice_ui_visual_qa_artifacts_do_not_contain_secret_markers() -> None:
    for filename in SCREENSHOTS:
        data = (ASSET_DIR / filename).read_bytes()

        assert b"UPSTAGE_API_KEY" not in data
        assert b"private_data/" not in data
