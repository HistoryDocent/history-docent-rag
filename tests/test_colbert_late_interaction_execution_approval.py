from __future__ import annotations

import re
from pathlib import Path


PUBLIC_DOC_PATHS = (
    Path("docs/COLBERT_LATE_INTERACTION_EXECUTION_APPROVAL.md"),
    Path("evals/reports/colbert_late_interaction_execution_approval_report.md"),
    Path("README.md"),
)


def test_colbert_execution_approval_docs_exist_and_are_sanitized() -> None:
    for path in PUBLIC_DOC_PATHS:
        text = path.read_text(encoding="utf-8")

        assert "chunk text" in text
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)
        assert "private_data/" not in text


def test_colbert_execution_approval_records_no_execution_boundary() -> None:
    doc = Path("docs/COLBERT_LATE_INTERACTION_EXECUTION_APPROVAL.md").read_text(
        encoding="utf-8",
    )
    report = Path(
        "evals/reports/colbert_late_interaction_execution_approval_report.md",
    ).read_text(encoding="utf-8")

    assert "`HD-COLBERT-001B`" in doc
    assert "expected_retrieval_execution_scope | `dev-hard-subset-only`" in doc
    assert "actual_retrieval_execution_count | 0" in doc
    assert "locked_test_execution_count | 0" in doc
    assert "solar_call_count | 0" in doc
    assert "expected_retrieval_execution_scope_dev_hard_subset_only | 1" in report
    assert "actual_retrieval_execution_count | 0" in report
    assert "locked_test_execution_count | 0" in report
    assert "solar_call_count | 0" in report


def test_colbert_execution_approval_records_cuda_candidates_and_metrics() -> None:
    doc = Path("docs/COLBERT_LATE_INTERACTION_EXECUTION_APPROVAL.md").read_text(
        encoding="utf-8",
    )
    report = Path(
        "evals/reports/colbert_late_interaction_execution_approval_report.md",
    ).read_text(encoding="utf-8")

    assert "`NVIDIA GeForce RTX 4080 SUPER`" in doc
    assert "CUDA availability | available" in doc
    assert "candidate_k | `20`, `50`" in doc
    assert "`Recall@5`" in doc
    assert "`MRR`" in doc
    assert "`nDCG@5`" in doc
    assert "`latency_p95_ms`" in doc
    assert "`cuda_memory_peak_mb`" in doc
    assert "cuda_available_flag | 1" in report
    assert "candidate_k_count | 2" in report
    assert "planned_metric_count | 5" in report


def test_colbert_execution_approval_records_data_mart_and_next_gate() -> None:
    report = Path(
        "evals/reports/colbert_late_interaction_execution_approval_report.md",
    ).read_text(encoding="utf-8")

    assert "fact_colbert_late_interaction_execution_approval" in report
    assert (
        "experiment_id + execution_scope + query_bucket + candidate_id + metric_family "
        "+ claim_boundary"
    ) in report
    assert "public_private_path_leakage_count | 0" in report
    assert "public_secret_like_leakage_count | 0" in report
    assert "public_raw_payload_leakage_count | 0" in report
    assert "`HD-COLBERT-001C`" in report


def test_colbert_execution_approval_keeps_forbidden_claims_as_forbidden_only() -> None:
    doc = Path("docs/COLBERT_LATE_INTERACTION_EXECUTION_APPROVAL.md").read_text(
        encoding="utf-8",
    )
    forbidden_section = doc.split("금지:", maxsplit=1)[1]

    assert "ColBERT로 retrieval 성능 개선" in forbidden_section
    assert "ColBERT를 production route에 적용" in forbidden_section
    assert "locked test에서 ColBERT 개선 입증" in forbidden_section
