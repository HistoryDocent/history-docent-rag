from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

import pytest

from app.domain.retrieval import (
    FORBIDDEN_PUBLIC_EVAL_FIELDS,
    RetrievedCandidate,
    RetrievalEvalItem,
    RetrievalRunResult,
)
from app.providers.llm.base import LlmProviderUsage
from pipelines.run_hyde_live_paired_retrieval_comparison import HydeGenerationOutput
from pipelines.run_hyde_larger_dev_subset_readiness import TARGET_QUERY_TYPES
from pipelines.run_hyde_larger_live_paired_retrieval_comparison import (
    HYDE_LARGER_LIVE_PAIRED_RETRIEVAL_REPORT_VERSION,
    WORK_ID,
    collect_hyde_larger_live_paired_retrieval_failures,
    run_hyde_larger_live_paired_retrieval_comparison,
)


def test_hyde_larger_live_paired_retrieval_writes_public_safe_report(
    tmp_path: Path,
) -> None:
    dataset_path = _write_fixture_dataset(tmp_path)
    doc_path = tmp_path / "HYDE_LARGER_LIVE_PAIRED_RETRIEVAL_COMPARISON.md"
    report_path = tmp_path / "hyde_larger_live_paired_retrieval_comparison_report.md"
    rows_path = tmp_path / "hyde_larger_live_paired_retrieval_comparison_rows.jsonl"

    report = run_hyde_larger_live_paired_retrieval_comparison(
        dataset_path=dataset_path,
        chunks_path=tmp_path / "unused_chunks.json",
        env_file_path=None,
        doc_path=doc_path,
        report_path=report_path,
        result_rows_path=rows_path,
        expected_query_count_per_type=2,
        hyde_provider=_FakeHydeProvider(),
        retrieval_runner=_FakeRetrievalRunner(),
    )
    doc_text = doc_path.read_text(encoding="utf-8")
    report_text = report_path.read_text(encoding="utf-8")
    rows = [json.loads(line) for line in rows_path.read_text(encoding="utf-8").splitlines()]

    assert report.report_version == HYDE_LARGER_LIVE_PAIRED_RETRIEVAL_REPORT_VERSION
    assert report.work_id == WORK_ID
    assert collect_hyde_larger_live_paired_retrieval_failures(
        report,
        expected_query_count_per_type=2,
    ) == []
    assert report.comparison_summary.query_count == 8
    assert report.comparison_summary.hyde_generation_request_count == 6
    assert report.comparison_summary.no_answer_guard_query_count == 2
    assert report.comparison_summary.solar_api_call_count == 6
    assert report.comparison_summary.recall_at_5_delta > 0
    assert report.output_quality.public_raw_text_leakage_count == 0
    assert report.output_quality.private_path_leakage_count == 0
    assert report.output_quality.secret_like_leakage_count == 0
    assert report.output_quality.forbidden_result_field_count == 0
    assert "| query_count | 8 |" in doc_text
    assert "| public_raw_text_leakage_count | 0 |" in report_text
    assert any(row["row_type"] == "query_type_delta" for row in rows)
    assert all(FORBIDDEN_PUBLIC_EVAL_FIELDS.isdisjoint(row.keys()) for row in rows)


def test_hyde_larger_live_blocks_no_answer_generation(
    tmp_path: Path,
) -> None:
    provider = _FakeHydeProvider()
    report = run_hyde_larger_live_paired_retrieval_comparison(
        dataset_path=_write_fixture_dataset(tmp_path),
        chunks_path=tmp_path / "unused_chunks.json",
        env_file_path=None,
        doc_path=tmp_path / "doc.md",
        report_path=tmp_path / "report.md",
        result_rows_path=tmp_path / "rows.jsonl",
        expected_query_count_per_type=2,
        hyde_provider=provider,
        retrieval_runner=_FakeRetrievalRunner(),
    )
    no_answer_rows = [row for row in report.rows if row.query_type == "no_answer"]

    assert provider.call_count == 6
    assert len(no_answer_rows) == 2
    assert all(row.no_answer_guard_applied for row in no_answer_rows)
    assert all(row.hyde_generation_request_count == 0 for row in no_answer_rows)
    assert all(row.solar_api_call_count == 0 for row in no_answer_rows)
    assert all(row.hyde_candidate_count == 0 for row in no_answer_rows)
    assert all(row.hyde_candidate_id == "blocked_for_no_answer_guard" for row in no_answer_rows)


def test_hyde_larger_live_blocks_hard_cap_before_provider_calls(
    tmp_path: Path,
) -> None:
    provider = _FakeHydeProvider()

    with pytest.raises(ValueError, match="not ready|hard cap"):
        run_hyde_larger_live_paired_retrieval_comparison(
            dataset_path=_write_fixture_dataset(tmp_path),
            chunks_path=tmp_path / "unused_chunks.json",
            env_file_path=None,
            doc_path=tmp_path / "doc.md",
            report_path=tmp_path / "report.md",
            result_rows_path=tmp_path / "rows.jsonl",
            expected_query_count_per_type=2,
            live_call_hard_cap=1,
            hyde_provider=provider,
            retrieval_runner=_FakeRetrievalRunner(),
        )

    assert provider.call_count == 0


def test_hyde_larger_live_public_docs_are_sanitized() -> None:
    public_paths = (
        Path("docs/HYDE_LARGER_LIVE_PAIRED_RETRIEVAL_COMPARISON.md"),
        Path("evals/reports/hyde_larger_live_paired_retrieval_comparison_report.md"),
    )

    for path in public_paths:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        assert "raw query" in text
        assert "chunk text" in text
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\\s*=", text)
        assert all(f"`{field}`" not in text for field in FORBIDDEN_PUBLIC_EVAL_FIELDS)


class _FakeHydeProvider:
    provider: Literal["fake"] = "fake"
    model_id = "fake-solar-pro3-hyde"
    provider_config_id = "fake-hyde-provider-v1"

    def __init__(self) -> None:
        self.call_count = 0

    def generate_hyde(self, item: RetrievalEvalItem) -> HydeGenerationOutput:
        self.call_count += 1
        text = f"fixture hyde expansion for {item.query.query_id}"
        return HydeGenerationOutput(
            query_id=item.query.query_id,
            provider="fake",
            model_id=self.model_id,
            provider_config_id=self.provider_config_id,
            generated_text=text,
            generated_text_hash="f" * 16,
            generated_text_length=len(text),
            finish_reason="mock",
            usage=LlmProviderUsage(
                latency_ms=100.0,
                api_call_count=1,
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15,
            ),
        )


class _FakeRetrievalRunner:
    def search_baseline(self, item: RetrievalEvalItem) -> tuple[str, RetrievalRunResult]:
        relevant_rank = 2 if item.query.query_id.endswith("001") else None
        return _route_label(item), _result(item=item, relevant_rank=relevant_rank)

    def search_hyde(
        self,
        item: RetrievalEvalItem,
        *,
        generated_text: str,
    ) -> tuple[str, RetrievalRunResult]:
        assert generated_text
        relevant_rank = 1 if not item.query.query_id.endswith("002") else 4
        return _route_label(item), _result(item=item, relevant_rank=relevant_rank)


def _route_label(item: RetrievalEvalItem) -> str:
    if item.query.query_type == "relationship":
        return "hybrid_weighted_e5_small_alpha_0_5"
    if item.query.query_type == "no_answer":
        return "abstain_first_v1"
    return "dense_multilingual_e5_small_voice_rewrite"


def _result(
    *,
    item: RetrievalEvalItem,
    relevant_rank: int | None,
) -> RetrievalRunResult:
    if item.query.expected_behavior == "abstain":
        candidates: list[RetrievedCandidate] = []
    else:
        candidates = []
        for rank in range(1, 6):
            relevant = relevant_rank == rank
            candidates.append(
                RetrievedCandidate(
                    rank=rank,
                    retrieval_doc_id=(
                        f"fixture-child-{item.query.query_id}"
                        if relevant
                        else f"fixture-miss-{item.query.query_id}-{rank}"
                    ),
                    child_id=(
                        f"fixture-child-{item.query.query_id}"
                        if relevant
                        else f"fixture-miss-child-{item.query.query_id}-{rank}"
                    ),
                    parent_id=(
                        f"fixture-parent-{item.query.query_id}"
                        if relevant
                        else f"fixture-miss-parent-{item.query.query_id}-{rank}"
                    ),
                    doc_id=(
                        f"fixture-doc-{item.query.query_id}"
                        if relevant
                        else f"fixture-miss-doc-{item.query.query_id}-{rank}"
                    ),
                    score=1.0 / rank,
                )
            )
    return RetrievalRunResult(
        query_id=item.query.query_id,
        query_type=item.query.query_type,
        method="hybrid_weighted" if item.query.query_type == "relationship" else "dense",
        candidates=candidates,
        latency_ms=10.0,
    )


def _write_fixture_dataset(tmp_path: Path) -> Path:
    dataset_path = tmp_path / "retrieval_eval_dev.jsonl"
    payloads = []
    for query_type in TARGET_QUERY_TYPES:
        for index in range(1, 3):
            expected_behavior = "abstain" if query_type == "no_answer" else "retrieve"
            answerability = "unanswerable" if query_type == "no_answer" else "answerable"
            payloads.append(
                _eval_item(
                    query_id=f"q-dev-{query_type}-{index:03d}",
                    query_type=query_type,
                    expected_behavior=expected_behavior,
                    answerability=answerability,
                ).model_dump_json(),
            )
    dataset_path.write_text("\n".join(payloads) + "\n", encoding="utf-8")
    return dataset_path


def _eval_item(
    *,
    query_id: str,
    query_type: str,
    expected_behavior: str,
    answerability: str,
) -> RetrievalEvalItem:
    judgments = []
    if expected_behavior == "retrieve":
        judgments.append(
            {
                "query_id": query_id,
                "relevant_child_ids": [f"fixture-child-{query_id}"],
                "relevant_parent_ids": [f"fixture-parent-{query_id}"],
                "relevant_doc_ids": [f"fixture-doc-{query_id}"],
                "relevance_grade": 3,
                "rationale_summary": "fixture target",
                "public_allowed": True,
            },
        )
    return RetrievalEvalItem.model_validate(
        {
            "dataset_version": "retrieval-eval-dataset/v2",
            "query": {
                "query_id": query_id,
                "query_type": query_type,
                "query_text": f"fixture query {query_id}",
                "language": "ko",
                "expected_behavior": expected_behavior,
                "user_context": None,
                "public_allowed": True,
            },
            "judgments": judgments,
            "metadata": {
                "split": "dev",
                "difficulty": "hard",
                "place_ids": ["gyeongbokgung"],
                "requires_context": False,
                "answerability": answerability,
                "review_status": "reviewed",
            },
        },
    )
