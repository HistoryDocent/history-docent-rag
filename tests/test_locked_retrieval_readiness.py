from __future__ import annotations

import json
import re
from pathlib import Path

from app.domain.chunking import ChildChunk, ChunkSourceRef
from app.domain.data_contracts import ElementReference, PageSpan
from app.domain.retrieval import (
    FORBIDDEN_PUBLIC_EVAL_FIELDS,
    REQUIRED_QUERY_TYPES,
    RetrievalEvalItem,
    RetrievalEvalMetadata,
    RetrievalJudgment,
    RetrievalQuery,
)
from pipelines.run_locked_retrieval_readiness import (
    EXPECTED_ALLOWED_CANDIDATE_COUNT,
    EXPECTED_LOCKED_QUERY_COUNT,
    EXPECTED_QUERY_TYPE_COUNT,
    EXPECTED_REJECTED_CANDIDATE_COUNT,
    LOCKED_RETRIEVAL_READINESS_REPORT_VERSION,
    build_locked_candidate_configs,
    build_locked_query_type_routes,
    collect_locked_readiness_failures,
    run_locked_retrieval_readiness,
)


DOC_PATH = Path("docs/LOCKED_RETRIEVAL_READINESS.md")
REPORT_PATH = Path("evals/reports/locked_retrieval_readiness_report.md")


def test_locked_retrieval_readiness_writes_public_safe_report(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "retrieval_eval_test.jsonl"
    chunks_path = tmp_path / "parent_child_chunks.json"
    doc_path = tmp_path / "LOCKED_RETRIEVAL_READINESS.md"
    report_path = tmp_path / "locked_retrieval_readiness_report.md"
    rows_path = tmp_path / "locked_retrieval_readiness_rows.jsonl"
    items = _eval_items()
    child = _child()

    _write_jsonl(dataset_path, [item.model_dump(mode="json") for item in items])
    _write_json(
        chunks_path,
        {
            "report_version": "chunking-quality/v1",
            "chunking_run_id": "chunking-test",
            "children": [child.model_dump(mode="json")],
        },
    )

    report = run_locked_retrieval_readiness(
        dataset_path=dataset_path,
        chunks_path=chunks_path,
        doc_path=doc_path,
        report_path=report_path,
        result_rows_path=rows_path,
    )
    doc_text = doc_path.read_text(encoding="utf-8")
    report_text = report_path.read_text(encoding="utf-8")
    rows = [
        json.loads(line)
        for line in rows_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert report.report_version == LOCKED_RETRIEVAL_READINESS_REPORT_VERSION
    assert collect_locked_readiness_failures(report) == []
    assert report.summary.planned_locked_query_count == EXPECTED_LOCKED_QUERY_COUNT
    assert report.summary.locked_query_count == EXPECTED_LOCKED_QUERY_COUNT
    assert report.summary.planned_query_type_count == EXPECTED_QUERY_TYPE_COUNT
    assert report.summary.query_type_count == EXPECTED_QUERY_TYPE_COUNT
    assert report.summary.allowed_candidate_count == EXPECTED_ALLOWED_CANDIDATE_COUNT
    assert report.summary.rejected_candidate_count == EXPECTED_REJECTED_CANDIDATE_COUNT
    assert report.summary.target_resolvability_fail_count == 0
    assert report.summary.no_answer_candidate_route_count == 0
    assert report.summary.locked_metric_result_count == 0
    assert report.summary.retrieval_execution_count == 0
    assert report.summary.solar_call_count == 0
    assert report.summary.resolved_device in {"cuda", "cpu"}
    assert report.summary.readiness_decision == "ready_for_locked_retrieval_approval"
    assert report.output_quality.public_raw_text_leakage_count == 0
    assert report.output_quality.private_path_leakage_count == 0
    assert report.output_quality.secret_like_leakage_count == 0
    assert report.output_quality.forbidden_result_field_count == 0
    assert "| readiness_decision | `ready_for_locked_retrieval_approval` |" in doc_text
    assert "| retrieval_execution_count | 0 |" in report_text
    assert "| solar_call_count | 0 |" in report_text
    assert all(FORBIDDEN_PUBLIC_EVAL_FIELDS.isdisjoint(row.keys()) for row in rows)


def test_locked_retrieval_readiness_candidate_and_route_boundary() -> None:
    items = _eval_items()
    candidates = build_locked_candidate_configs(items)
    query_type_routes = build_locked_query_type_routes(items)
    allowed = [candidate for candidate in candidates if candidate.scope != "not_allowed"]
    rejected = [candidate for candidate in candidates if candidate.scope == "not_allowed"]
    no_answer_routes = [
        row for row in query_type_routes if row.query_type == "no_answer"
    ]
    relationship_routes = [
        row for row in query_type_routes if row.query_type == "relationship"
    ]

    assert [candidate.candidate_id for candidate in allowed] == [
        "dense_multilingual_e5_small_voice_rewrite",
        "relationship_hybrid_weighted_e5_v1",
    ]
    assert len(rejected) == 4
    assert sum(candidate.planned_query_count for candidate in rejected) == 0
    assert no_answer_routes[0].expected_candidate_count == 0
    assert no_answer_routes[0].no_answer_guard_applied is True
    assert relationship_routes[0].expected_candidate_count == 2
    assert all(
        candidate.retrieval_execution_count == 0
        and candidate.locked_metric_result_count == 0
        for candidate in candidates
    )


def test_locked_retrieval_readiness_public_docs_are_sanitized() -> None:
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


def _page_span() -> PageSpan:
    return PageSpan(
        page_local_start=1,
        page_local_end=1,
        page_global_start=1,
        page_global_end=1,
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


def _eval_items() -> list[RetrievalEvalItem]:
    return [
        _eval_item(query_type=query_type, index=index)
        for query_type in REQUIRED_QUERY_TYPES
        for index in range(1, 6)
    ]


def _eval_item(*, query_type: str, index: int) -> RetrievalEvalItem:
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
    requires_context = query_type == "voice_followup"
    return RetrievalEvalItem(
        query=RetrievalQuery(
            query_id=query_id,
            query_type=query_type,
            query_text="fixture answerable query",
            language="ko",
            expected_behavior="retrieve",
            user_context="fixture followup context" if requires_context else None,
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
            requires_context=requires_context,
            answerability="answerable",
            review_status="locked",
        ),
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
