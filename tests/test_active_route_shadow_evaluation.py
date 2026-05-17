from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app.application.query_type_router import RELATIONSHIP_ROUTE_POLICY_ID
from app.domain.retrieval import (
    FORBIDDEN_PUBLIC_EVAL_FIELDS,
    QueryType,
    RetrievedCandidate,
    RetrievalEvalItem,
    RetrievalRunResult,
)
from pipelines import run_active_route_shadow_evaluation as active_route_eval
from pipelines.run_active_route_shadow_evaluation import (
    ACTIVE_ROUTE_SHADOW_EVAL_REPORT_VERSION,
    collect_active_route_shadow_evaluation_failures,
    run_active_route_shadow_evaluation,
)


def test_active_route_shadow_evaluation_writes_public_safe_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        active_route_eval,
        "is_repository_private_write_path",
        lambda path: True,
    )
    dataset_path = _write_fixture_dataset(tmp_path)
    doc_path = tmp_path / "ACTIVE_ROUTE_SHADOW_EVALUATION.md"
    report_path = tmp_path / "active_route_shadow_evaluation_report.md"
    rows_path = tmp_path / "private_data" / "evals" / "results" / "rows.jsonl"

    report = run_active_route_shadow_evaluation(
        dataset_path=dataset_path,
        chunks_path=tmp_path / "unused_chunks.json",
        result_rows_path=rows_path,
        doc_path=doc_path,
        report_path=report_path,
        retrieval_runner=_FakeActiveRouteRunner(),
    )
    rows = [json.loads(line) for line in rows_path.read_text(encoding="utf-8").splitlines()]
    doc_text = doc_path.read_text(encoding="utf-8")
    report_text = report_path.read_text(encoding="utf-8")

    assert report.report_version == ACTIVE_ROUTE_SHADOW_EVAL_REPORT_VERSION
    assert collect_active_route_shadow_evaluation_failures(report) == []
    assert report.comparison_summary.query_count == 4
    assert report.comparison_summary.routed_candidate_query_count == 1
    assert report.comparison_summary.false_hybrid_route_count == 0
    assert report.comparison_summary.no_answer_candidate_route_count == 0
    assert report.comparison_summary.active_route_applied_count == 0
    assert report.comparison_summary.live_solar_call_count == 0
    assert report.comparison_summary.recall_at_5_delta > 0
    assert report.comparison_summary.relationship_recall_at_5_delta > 0
    assert report.comparison_summary.shadow_decision == (
        "ready_for_active_route_dry_run_contract"
    )
    assert report.output_quality.public_raw_text_leakage_count == 0
    assert report.output_quality.private_path_leakage_count == 0
    assert report.output_quality.secret_like_leakage_count == 0
    assert report.output_quality.forbidden_result_field_count == 0
    assert any(row["row_type"] == "query_shadow_result" for row in rows)
    assert any(
        row["row_type"] == "query_shadow_result"
        and row["shadow_route_policy_id"] == RELATIONSHIP_ROUTE_POLICY_ID
        for row in rows
    )
    assert all(FORBIDDEN_PUBLIC_EVAL_FIELDS.isdisjoint(row.keys()) for row in rows)
    assert "raw query" in doc_text
    assert "| public_raw_text_leakage_count | 0 |" in report_text


def test_active_route_shadow_evaluation_blocks_private_text_from_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        active_route_eval,
        "is_repository_private_write_path",
        lambda path: True,
    )
    private_query_text = "창덕궁이 태종 시기 권력 기억과 연결되는 이유를 설명할 근거를 찾아줘"
    dataset_path = _write_fixture_dataset(
        tmp_path,
        override_query_text=private_query_text,
    )
    doc_path = tmp_path / "doc.md"
    report_path = tmp_path / "report.md"
    rows_path = tmp_path / "private_data" / "evals" / "results" / "rows.jsonl"

    run_active_route_shadow_evaluation(
        dataset_path=dataset_path,
        chunks_path=tmp_path / "unused_chunks.json",
        result_rows_path=rows_path,
        doc_path=doc_path,
        report_path=report_path,
        retrieval_runner=_FakeActiveRouteRunner(),
    )

    for path in (doc_path, report_path, rows_path):
        text = path.read_text(encoding="utf-8")
        assert private_query_text not in text
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\\s*=", text)


class _FakeActiveRouteRunner:
    def search(
        self,
        *,
        item: RetrievalEvalItem,
        route_decision: object,
    ) -> RetrievalRunResult:
        if item.query.expected_behavior == "abstain":
            return _result(item=item, relevant_rank=None, method="dense")
        if getattr(route_decision, "route_policy_id") == RELATIONSHIP_ROUTE_POLICY_ID:
            return _result(item=item, relevant_rank=1, method="hybrid_weighted")
        ranks = {
            "q-place-fact-001": 1,
            "q-relationship-001": None,
            "q-place-fact-guard-001": 1,
        }
        return _result(
            item=item,
            relevant_rank=ranks.get(item.query.query_id),
            method="dense",
        )


def _write_fixture_dataset(
    tmp_path: Path,
    *,
    override_query_text: str | None = None,
) -> Path:
    items = (
        _eval_item(
            query_id="q-place-fact-001",
            query_type="place_fact",
            query_text=override_query_text or "경복궁 이름의 의미를 근거와 함께 찾아줘",
        ),
        _eval_item(
            query_id="q-relationship-001",
            query_type="relationship",
            query_text=(
                "정도전과 이방원의 갈등이 경복궁과 창덕궁 선택에 어떻게 남았는지 찾아줘"
            ),
        ),
        _eval_item(
            query_id="q-place-fact-guard-001",
            query_type="place_fact",
            query_text=(
                "창덕궁이 태종 시기 권력 기억과 연결되는 이유를 설명할 근거를 찾아줘"
            ),
        ),
        _eval_item(
            query_id="q-no-answer-001",
            query_type="no_answer",
            query_text="오늘 경복궁 야간개장 입장권이 몇 장 남았어?",
            answerable=False,
        ),
    )
    dataset_path = tmp_path / "retrieval_eval_dev.jsonl"
    dataset_path.write_text(
        "\n".join(item.model_dump_json() for item in items) + "\n",
        encoding="utf-8",
    )
    return dataset_path


def _eval_item(
    *,
    query_id: str,
    query_type: QueryType,
    query_text: str,
    answerable: bool = True,
) -> RetrievalEvalItem:
    judgments = []
    if answerable:
        judgments.append(
            {
                "query_id": query_id,
                "relevant_child_ids": [f"fixture-child-{query_id}"],
                "relevant_parent_ids": [f"fixture-parent-{query_id}"],
                "relevant_doc_ids": [f"fixture-doc-{query_id}"],
                "relevance_grade": 3,
                "rationale_summary": "fixture target id",
                "public_allowed": True,
            },
        )
    return RetrievalEvalItem.model_validate(
        {
            "dataset_version": "retrieval-eval-dataset/v2",
            "query": {
                "query_id": query_id,
                "query_type": query_type,
                "query_text": query_text,
                "language": "ko",
                "expected_behavior": "retrieve" if answerable else "abstain",
                "user_context": "public-safe fixture context",
                "public_allowed": True,
            },
            "judgments": judgments,
            "metadata": {
                "split": "dev",
                "difficulty": "medium",
                "place_ids": ["gyeongbokgung", "changdeokgung"],
                "requires_context": False,
                "answerability": "answerable" if answerable else "unanswerable",
                "review_status": "reviewed",
            },
        },
    )


def _result(
    *,
    item: RetrievalEvalItem,
    relevant_rank: int | None,
    method: str,
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
    if relevant_rank is None:
        candidates = []
    return RetrievalRunResult(
        query_id=item.query.query_id,
        query_type=item.query.query_type,
        method=method,
        candidates=candidates,
        latency_ms=10.0,
    )
