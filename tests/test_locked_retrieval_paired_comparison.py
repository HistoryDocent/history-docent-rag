from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app.domain.chunking import ChildChunk, ChunkSourceRef
from app.domain.data_contracts import ElementReference, PageSpan
from app.domain.retrieval import (
    FORBIDDEN_PUBLIC_EVAL_FIELDS,
    REQUIRED_QUERY_TYPES,
    QueryType,
    RetrievedCandidate,
    RetrievalEvalItem,
    RetrievalEvalMetadata,
    RetrievalJudgment,
    RetrievalQuery,
    RetrievalRunResult,
)
from pipelines import run_locked_retrieval_paired_comparison as locked_run
from pipelines.run_locked_retrieval_paired_comparison import (
    BASELINE_CANDIDATE_ID,
    BOOTSTRAP_ITERATIONS,
    EXPECTED_LOCKED_QUERY_COUNT,
    LOCKED_RETRIEVAL_PAIRED_REPORT_VERSION,
    RELATIONSHIP_CANDIDATE_ID,
    build_private_locked_fact_rows,
    collect_locked_retrieval_paired_comparison_failures,
    run_locked_retrieval_paired_comparison,
)


DOC_PATH = Path("docs/LOCKED_RETRIEVAL_PAIRED_COMPARISON.md")
REPORT_PATH = Path("evals/reports/locked_retrieval_paired_comparison_report.md")


def test_locked_retrieval_paired_comparison_writes_public_safe_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        locked_run,
        "is_repository_private_write_path",
        lambda path: True,
    )
    dataset_path = tmp_path / "retrieval_eval_test.jsonl"
    chunks_path = tmp_path / "parent_child_chunks.json"
    rows_path = tmp_path / "private_data" / "evals" / "results" / "locked_rows.jsonl"
    doc_path = tmp_path / "LOCKED_RETRIEVAL_PAIRED_COMPARISON.md"
    report_path = tmp_path / "locked_retrieval_paired_comparison_report.md"

    _write_jsonl(dataset_path, [item.model_dump(mode="json") for item in _eval_items()])
    _write_json(
        chunks_path,
        {
            "report_version": "chunking-quality/v1",
            "chunking_run_id": "chunking-test",
            "children": [_child().model_dump(mode="json")],
        },
    )

    report = run_locked_retrieval_paired_comparison(
        dataset_path=dataset_path,
        chunks_path=chunks_path,
        result_rows_path=rows_path,
        doc_path=doc_path,
        report_path=report_path,
        retrieval_runner=_FakeLockedRunner(),
    )
    private_rows = [
        json.loads(line)
        for line in rows_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    doc_text = doc_path.read_text(encoding="utf-8")
    report_text = report_path.read_text(encoding="utf-8")

    assert report.report_version == LOCKED_RETRIEVAL_PAIRED_REPORT_VERSION
    assert collect_locked_retrieval_paired_comparison_failures(report) == []
    assert report.comparison_summary.locked_query_count == EXPECTED_LOCKED_QUERY_COUNT
    assert report.comparison_summary.answerable_query_count == 30
    assert report.comparison_summary.no_answer_query_count == 5
    assert report.comparison_summary.paired_query_count == 5
    assert report.comparison_summary.baseline_retrieval_run_count == 30
    assert report.comparison_summary.candidate_retrieval_run_count == 5
    assert report.comparison_summary.false_hybrid_route_count == 0
    assert report.comparison_summary.no_answer_candidate_route_count == 0
    assert report.comparison_summary.live_solar_call_count == 0
    assert report.comparison_summary.bootstrap_iteration_count == BOOTSTRAP_ITERATIONS
    assert report.comparison_summary.primary_metric_delta > 0
    assert report.comparison_summary.primary_metric_ci_low > 0
    assert report.comparison_summary.locked_decision == (
        "support_relationship_route_candidate"
    )
    assert report.baseline_summary.candidate_id == BASELINE_CANDIDATE_ID
    assert report.candidate_summary.candidate_id == RELATIONSHIP_CANDIDATE_ID
    assert report.output_quality.public_raw_text_leakage_count == 0
    assert report.output_quality.private_path_leakage_count == 0
    assert report.output_quality.secret_like_leakage_count == 0
    assert report.output_quality.forbidden_result_field_count == 0
    assert len(private_rows) == report.comparison_summary.private_fact_row_count
    assert {row["row_type"] for row in private_rows} == {
        "fact_locked_retrieval_eval"
    }
    assert all(FORBIDDEN_PUBLIC_EVAL_FIELDS.isdisjoint(row.keys()) for row in private_rows)
    assert "raw query" in doc_text
    assert "| public_raw_text_leakage_count | 0 |" in report_text


def test_private_fact_rows_use_locked_fact_grain() -> None:
    report = locked_run._build_report(
        rows=locked_run.build_locked_retrieval_pair_rows(
            items=_eval_items(),
            retrieval_runner=_FakeLockedRunner(),
        ),
        dataset_path=Path("private_data/evals/datasets/retrieval_eval_test.jsonl"),
        chunks_path=Path("private_data/reports/parent_child_chunks.json"),
        result_rows_path=Path(
            "private_data/evals/results/locked_retrieval_paired_comparison_fact_rows.jsonl"
        ),
        top_k=5,
        target_resolvability_fail_count=0,
        output_quality=locked_run.PublicRetrievalArtifactQuality(
            result_row_count=0,
            report_version=LOCKED_RETRIEVAL_PAIRED_REPORT_VERSION,
            run_id="pending",
            public_raw_text_leakage_count=0,
            private_path_leakage_count=0,
            secret_like_leakage_count=0,
            forbidden_result_field_count=0,
        ),
    )

    rows = build_private_locked_fact_rows(report)
    grain = {
        (
            row["run_id"],
            row["query_id"],
            row["candidate_id"],
            row["metric_name"],
        )
        for row in rows
    }

    assert len(grain) == len(rows)
    assert all("query_text" not in row for row in rows)
    assert all("answer" not in row for row in rows)
    assert any(row["candidate_id"] == RELATIONSHIP_CANDIDATE_ID for row in rows)


def test_locked_retrieval_paired_comparison_public_docs_are_sanitized() -> None:
    for path in (DOC_PATH, REPORT_PATH):
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        assert "raw query" in text
        assert "chunk text" in text
        assert not re.search(r"[A-Za-z]:\\", text)
        assert not re.search(r"sk-[A-Za-z0-9]", text)
        assert not re.search(r"UPSTAGE_API_KEY\\s*=", text)
        assert all(f"`{field}`" not in text for field in FORBIDDEN_PUBLIC_EVAL_FIELDS)


class _FakeLockedRunner:
    def search(
        self,
        *,
        item: RetrievalEvalItem,
        route_role: str,
    ) -> RetrievalRunResult:
        if item.query.expected_behavior == "abstain":
            return _result(item=item, method="dense", relevant_rank=None)
        if route_role == "candidate":
            return _result(item=item, method="hybrid_weighted", relevant_rank=1)
        if item.query.query_type == "relationship":
            return _result(item=item, method="dense", relevant_rank=5)
        return _result(item=item, method="dense", relevant_rank=1)


def _result(
    *,
    item: RetrievalEvalItem,
    method: str,
    relevant_rank: int | None,
) -> RetrievalRunResult:
    candidates = []
    if relevant_rank is None:
        return RetrievalRunResult(
            query_id=item.query.query_id,
            query_type=item.query.query_type,
            method=method,  # type: ignore[arg-type]
            candidates=[],
            latency_ms=0.0,
        )
    for rank in range(1, 6):
        relevant = rank == relevant_rank
        candidates.append(
            RetrievedCandidate(
                rank=rank,
                retrieval_doc_id="child-a" if relevant else f"miss-{item.query.query_id}-{rank}",
                child_id="child-a" if relevant else f"miss-child-{item.query.query_id}-{rank}",
                parent_id="parent-a" if relevant else f"miss-parent-{item.query.query_id}-{rank}",
                doc_id="doc-a" if relevant else f"miss-doc-{item.query.query_id}-{rank}",
                score=1.0 / rank,
            )
        )
    return RetrievalRunResult(
        query_id=item.query.query_id,
        query_type=item.query.query_type,
        method=method,  # type: ignore[arg-type]
        candidates=candidates,
        latency_ms=5.0 if method == "dense" else 8.0,
    )


def _eval_items() -> list[RetrievalEvalItem]:
    return [
        _eval_item(query_type=query_type, index=index)
        for query_type in REQUIRED_QUERY_TYPES
        for index in range(1, 6)
    ]


def _eval_item(*, query_type: QueryType, index: int) -> RetrievalEvalItem:
    query_id = f"q-test-{query_type}-{index:03d}"
    if query_type == "no_answer":
        return RetrievalEvalItem(
            query=RetrievalQuery(
                query_id=query_id,
                query_type="no_answer",
                query_text="fixture no answer query",
                language="ko",
                expected_behavior="abstain",
                user_context="fixture context",
            ),
            judgments=[],
            metadata=RetrievalEvalMetadata(
                split="test",
                difficulty="easy",
                place_ids=["gyeongbokgung"],
                requires_context=False,
                answerability="unanswerable",
                review_status="locked",
            ),
        )
    return RetrievalEvalItem(
        query=RetrievalQuery(
            query_id=query_id,
            query_type=query_type,
            query_text="fixture answerable query",
            language="ko",
            expected_behavior="retrieve",
            user_context="fixture context" if query_type == "voice_followup" else None,
        ),
        judgments=[
            RetrievalJudgment(
                query_id=query_id,
                relevant_child_ids=["child-a"],
                relevant_parent_ids=["parent-a"],
                relevant_doc_ids=["doc-a"],
                relevance_grade=3,
                rationale_summary="target ids only",
            )
        ],
        metadata=RetrievalEvalMetadata(
            split="test",
            difficulty="medium",
            place_ids=["gyeongbokgung"],
            requires_context=query_type == "voice_followup",
            answerability="answerable",
            review_status="locked",
        ),
    )


def _child() -> ChildChunk:
    return ChildChunk(
        child_id="child-a",
        parent_id="parent-a",
        doc_id="doc-a",
        doc_title="doc-a",
        parser_run_id="parser-run",
        source_block_ids=["block-child-a"],
        context_block_ids=[],
        page_span=_page_span(),
        text_hash="a" * 64,
        text_length=len("private searchable fixture"),
        element_type_mix={"paragraph": 1},
        citation_refs=[
            ChunkSourceRef(
                block_id="block-child-a",
                doc_id="doc-a",
                element_type="paragraph",
                page_span=_page_span(),
                element_refs=[
                    ElementReference(
                        element_id="element-child-a",
                        element_type="paragraph",
                        element_index=1,
                    )
                ],
                source_file_name="doc-a.pdf",
                text_hash="b" * 64,
                text_length=len("private searchable fixture"),
                quality_flags=[],
            )
        ],
        quality_flags=[],
        public_allowed=False,
        text="private searchable fixture",
        context_text=None,
    )


def _page_span() -> PageSpan:
    return PageSpan(
        page_local_start=1,
        page_local_end=1,
        page_global_start=1,
        page_global_end=1,
    )


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )
