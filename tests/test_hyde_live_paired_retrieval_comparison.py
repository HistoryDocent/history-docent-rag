from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

from app.domain.retrieval import (
    FORBIDDEN_PUBLIC_EVAL_FIELDS,
    RetrievedCandidate,
    RetrievalEvalItem,
    RetrievalRunResult,
)
from app.providers.llm.base import LlmProviderUsage
from pipelines.run_hyde_live_paired_retrieval_comparison import (
    HYDE_LIVE_PAIRED_RETRIEVAL_REPORT_VERSION,
    HydeGenerationOutput,
    collect_hyde_live_paired_retrieval_failures,
    run_hyde_live_paired_retrieval_comparison,
)


def test_hyde_live_paired_retrieval_writes_public_safe_report(
    tmp_path: Path,
) -> None:
    dataset_path = _write_fixture_dataset(tmp_path)
    doc_path = tmp_path / "HYDE_LIVE_PAIRED_RETRIEVAL_COMPARISON.md"
    report_path = tmp_path / "hyde_live_paired_retrieval_comparison_report.md"
    rows_path = tmp_path / "hyde_live_paired_retrieval_comparison_rows.jsonl"

    report = run_hyde_live_paired_retrieval_comparison(
        dataset_path=dataset_path,
        chunks_path=tmp_path / "unused_chunks.json",
        env_file_path=None,
        doc_path=doc_path,
        report_path=report_path,
        result_rows_path=rows_path,
        hyde_provider=_FakeHydeProvider(),
        retrieval_runner=_FakeRetrievalRunner(),
    )
    doc_text = doc_path.read_text(encoding="utf-8")
    report_text = report_path.read_text(encoding="utf-8")
    rows = [json.loads(line) for line in rows_path.read_text(encoding="utf-8").splitlines()]

    assert report.report_version == HYDE_LIVE_PAIRED_RETRIEVAL_REPORT_VERSION
    assert collect_hyde_live_paired_retrieval_failures(report) == []
    assert report.comparison_summary.query_count == 5
    assert report.comparison_summary.hyde_generation_request_count == 4
    assert report.comparison_summary.no_answer_guard_query_count == 1
    assert report.comparison_summary.solar_api_call_count == 4
    assert report.comparison_summary.recall_at_5_delta > 0
    assert report.comparison_summary.adoption_decision == (
        "keep_hyde_candidate_for_larger_eval"
    )
    assert report.output_quality.public_raw_text_leakage_count == 0
    assert report.output_quality.private_path_leakage_count == 0
    assert report.output_quality.secret_like_leakage_count == 0
    assert report.output_quality.forbidden_result_field_count == 0
    assert "raw query" in doc_text
    assert "| public_raw_text_leakage_count | 0 |" in report_text
    assert all(FORBIDDEN_PUBLIC_EVAL_FIELDS.isdisjoint(row.keys()) for row in rows)


def test_hyde_live_paired_retrieval_blocks_no_answer_generation(
    tmp_path: Path,
) -> None:
    dataset_path = _write_fixture_dataset(tmp_path)
    report = run_hyde_live_paired_retrieval_comparison(
        dataset_path=dataset_path,
        chunks_path=tmp_path / "unused_chunks.json",
        env_file_path=None,
        doc_path=tmp_path / "doc.md",
        report_path=tmp_path / "report.md",
        result_rows_path=tmp_path / "rows.jsonl",
        hyde_provider=_FakeHydeProvider(),
        retrieval_runner=_FakeRetrievalRunner(),
    )
    no_answer = next(row for row in report.rows if row.query_type == "no_answer")

    assert no_answer.no_answer_guard_applied is True
    assert no_answer.hyde_generation_request_count == 0
    assert no_answer.solar_api_call_count == 0
    assert no_answer.hyde_candidate_count == 0
    assert no_answer.hyde_candidate_id == "blocked_for_no_answer_guard"


def test_hyde_live_paired_retrieval_public_docs_are_sanitized(
    tmp_path: Path,
) -> None:
    dataset_path = _write_fixture_dataset(tmp_path)
    doc_path = tmp_path / "doc.md"
    report_path = tmp_path / "report.md"
    run_hyde_live_paired_retrieval_comparison(
        dataset_path=dataset_path,
        chunks_path=tmp_path / "unused_chunks.json",
        env_file_path=None,
        doc_path=doc_path,
        report_path=report_path,
        result_rows_path=tmp_path / "rows.jsonl",
        hyde_provider=_FakeHydeProvider(),
        retrieval_runner=_FakeRetrievalRunner(),
    )

    for path in (doc_path, report_path):
        text = path.read_text(encoding="utf-8")
        assert "chunk text" in text
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\\s*=", text)
        assert all(f"`{field}`" not in text for field in FORBIDDEN_PUBLIC_EVAL_FIELDS)


class _FakeHydeProvider:
    provider: Literal["fake"] = "fake"
    model_id = "fake-solar-pro3-hyde"
    provider_config_id = "fake-hyde-provider-v1"

    def generate_hyde(self, item: RetrievalEvalItem) -> HydeGenerationOutput:
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
        ranks = {
            "q-dev-place-story-001": None,
            "q-dev-place-story-008": 2,
            "q-dev-relationship-008": 3,
            "q-dev-overview-010": None,
        }
        return _route_label(item), _result(item=item, relevant_rank=ranks.get(item.query.query_id))

    def search_hyde(
        self,
        item: RetrievalEvalItem,
        *,
        generated_text: str,
    ) -> tuple[str, RetrievalRunResult]:
        assert generated_text
        ranks = {
            "q-dev-place-story-001": 1,
            "q-dev-place-story-008": 2,
            "q-dev-relationship-008": 2,
            "q-dev-overview-010": 5,
        }
        return _route_label(item), _result(item=item, relevant_rank=ranks.get(item.query.query_id))


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
    if item.query.expected_behavior == "abstain":
        candidates = []
    return RetrievalRunResult(
        query_id=item.query.query_id,
        query_type=item.query.query_type,
        method="hybrid_weighted" if item.query.query_type == "relationship" else "dense",
        candidates=candidates,
        latency_ms=10.0,
    )


def _write_fixture_dataset(tmp_path: Path) -> Path:
    dataset_path = tmp_path / "retrieval_eval_dev.jsonl"
    dataset_path.write_text(
        "\n".join(
            _eval_item(
                query_id=query_id,
                query_type=query_type,
                expected_behavior=expected_behavior,
                answerability=answerability,
            ).model_dump_json()
            for query_id, query_type, expected_behavior, answerability in (
                (
                    "q-dev-place-story-001",
                    "place_story",
                    "retrieve",
                    "answerable",
                ),
                (
                    "q-dev-place-story-008",
                    "place_story",
                    "retrieve",
                    "answerable",
                ),
                (
                    "q-dev-relationship-008",
                    "relationship",
                    "retrieve",
                    "answerable",
                ),
                ("q-dev-overview-010", "overview", "retrieve", "answerable"),
                ("q-dev-no-answer-001", "no_answer", "abstain", "unanswerable"),
            )
        )
        + "\n",
        encoding="utf-8",
    )
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
