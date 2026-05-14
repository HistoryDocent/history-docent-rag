from __future__ import annotations

import re
from pathlib import Path

from app.domain.retrieval import FORBIDDEN_PUBLIC_EVAL_FIELDS


PUBLIC_DOC_PATHS = (
    Path("docs/RAG_DECISION_LEDGER.md"),
    Path("evals/reports/final_ablation_status_report.md"),
)


def test_rag_decision_ledger_public_docs_exist_and_are_sanitized() -> None:
    for path in PUBLIC_DOC_PATHS:
        text = path.read_text(encoding="utf-8")

        assert "raw query" in text
        assert "chunk text" in text
        assert "private path" in text
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\\s*=", text)
        assert all(f"`{field}`" not in text for field in FORBIDDEN_PUBLIC_EVAL_FIELDS)


def test_rag_decision_ledger_records_core_decisions() -> None:
    ledger = Path("docs/RAG_DECISION_LEDGER.md").read_text(encoding="utf-8")
    report = Path("evals/reports/final_ablation_status_report.md").read_text(
        encoding="utf-8",
    )

    assert "`C0 current parent-child`" in ledger
    assert "`dense_multilingual_e5_small_voice_rewrite`" in ledger
    assert "`graphrag_lite_entity_path_v1`" in ledger
    assert "reject_default" in ledger
    assert "`HD-ROUTER-001`" in ledger
    assert "청킹 비교도 지금 다시 열지 않는다" in report
