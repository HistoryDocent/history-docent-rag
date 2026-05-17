from __future__ import annotations

import re
from pathlib import Path


PUBLIC_SCAN_PATHS = (
    Path("README.md"),
    Path("docs/SUBMISSION_READY_CHECKLIST.md"),
    Path("evals/reports/submission_ready_report.md"),
)
REQUIRED_LOCAL_LINKS = (
    "docs/SUBMISSION_READY_CHECKLIST.md",
    "evals/reports/submission_ready_report.md",
)
EXPECTED_NOTEBOOKS = tuple(f"notebooks/{index:02d}_{name}.ipynb" for index, name in (
    (0, "project_scope"),
    (1, "data_manifest_audit"),
    (2, "parser_quality_check"),
    (3, "normalized_blocks_validation"),
    (4, "chunking_quality_analysis"),
    (5, "place_catalog_validation"),
    (6, "bm25_baseline_evaluation"),
    (7, "dense_hybrid_retrieval_comparison"),
    (8, "query_rewrite_ablation"),
    (9, "parent_child_retrieval_ablation"),
    (10, "citation_rag_generation_eval"),
    (11, "raptor_lite_experiment"),
    (12, "graphrag_lite_experiment"),
    (13, "final_ablation_report"),
))


def test_submission_ready_docs_exist_and_are_sanitized() -> None:
    for path in PUBLIC_SCAN_PATHS:
        text = path.read_text(encoding="utf-8")

        assert "chunk text" in text
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)
        assert "private_data/" not in text


def test_submission_ready_records_quantitative_and_qualitative_gates() -> None:
    checklist = Path("docs/SUBMISSION_READY_CHECKLIST.md").read_text(encoding="utf-8")
    report = Path("evals/reports/submission_ready_report.md").read_text(encoding="utf-8")

    assert "`HD-SUBMISSION-READY-001`" in checklist
    assert "제출 전 자동 검증" in checklist
    assert "담당 관점 감사" in checklist
    assert "checked_readme_local_link_missing_count | 0" in report
    assert "notebook_numbered_skeleton_count | 14" in report
    assert "forbidden_claim_as_success_count | 0" in report
    assert "fact_submission_ready_gate" in report


def test_submission_ready_readme_links_are_registered() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    for local_link in REQUIRED_LOCAL_LINKS:
        assert local_link in readme
        assert Path(local_link).exists()


def test_submission_ready_notebook_skeleton_exists() -> None:
    for notebook_path in EXPECTED_NOTEBOOKS:
        assert Path(notebook_path).exists()


def test_submission_ready_keeps_forbidden_claims_as_forbidden_only() -> None:
    checklist = Path("docs/SUBMISSION_READY_CHECKLIST.md").read_text(encoding="utf-8")
    forbidden_section = checklist.split("## 금지 Claim 유지", maxsplit=1)[1]

    assert "production 성능 검증 완료" in forbidden_section
    assert "locked test에서 최종 성능 개선 입증" in forbidden_section
    assert "음성 관광 앱 완성" in forbidden_section
