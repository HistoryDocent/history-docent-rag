from __future__ import annotations

import re
from pathlib import Path


PUBLIC_DOC_PATHS = (
    Path("docs/COLBERT_LATE_INTERACTION_PLAN.md"),
    Path("evals/reports/colbert_late_interaction_plan_report.md"),
    Path("README.md"),
)


def test_colbert_plan_docs_exist_and_are_sanitized() -> None:
    for path in PUBLIC_DOC_PATHS:
        text = path.read_text(encoding="utf-8")

        assert "chunk text" in text
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\s*=", text)
        assert "private_data/" not in text


def test_colbert_plan_records_scope_and_no_execution_boundary() -> None:
    doc = Path("docs/COLBERT_LATE_INTERACTION_PLAN.md").read_text(encoding="utf-8")
    report = Path("evals/reports/colbert_late_interaction_plan_report.md").read_text(
        encoding="utf-8",
    )

    assert "`HD-COLBERT-001A`" in doc
    assert "plan-only readiness" in doc
    assert "retrieval execution 없음" in doc
    assert "Solar Pro 3 호출 | 0" in doc
    assert "locked test 사용 | 0" in doc
    assert "retrieval_execution_count | 0" in report
    assert "locked_test_execution_count | 0" in report
    assert "solar_call_count | 0" in report


def test_colbert_plan_records_candidates_metrics_and_next_gate() -> None:
    doc = Path("docs/COLBERT_LATE_INTERACTION_PLAN.md").read_text(encoding="utf-8")
    report = Path("evals/reports/colbert_late_interaction_plan_report.md").read_text(
        encoding="utf-8",
    )

    assert "`baseline_dense_e5_voice_rewrite`" in doc
    assert "`bge_cross_encoder_rerank_top20_reference`" in doc
    assert "`colbert_style_late_interaction_top20_cuda`" in doc
    assert "`colbert_style_late_interaction_top50_cuda`" in doc
    assert "`Recall@5`" in doc
    assert "`MRR`" in doc
    assert "`nDCG@5`" in doc
    assert "`latency_p95_ms`" in doc
    assert "planned_candidate_count | 2" in report
    assert "`HD-COLBERT-001B`" in report


def test_colbert_plan_records_data_mart_grain_and_public_safety() -> None:
    report = Path("evals/reports/colbert_late_interaction_plan_report.md").read_text(
        encoding="utf-8",
    )

    assert "fact_colbert_late_interaction_plan" in report
    assert "experiment_id + query_bucket + candidate_id + metric_family + claim_boundary" in report
    assert "public_private_path_leakage_count | 0" in report
    assert "public_secret_like_leakage_count | 0" in report
    assert "public_raw_payload_leakage_count | 0" in report


def test_colbert_plan_keeps_forbidden_claims_as_forbidden_only() -> None:
    doc = Path("docs/COLBERT_LATE_INTERACTION_PLAN.md").read_text(encoding="utf-8")
    forbidden_section = doc.split("금지:", maxsplit=1)[1]

    assert "ColBERT로 retrieval 성능 개선" in forbidden_section
    assert "locked test에서 ColBERT 개선 입증" in forbidden_section
    assert "production route에 ColBERT 적용" in forbidden_section
