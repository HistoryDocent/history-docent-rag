from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.domain.chunking import ChildChunk, ChunkSourceRef
from app.domain.data_contracts import ElementReference, PageSpan
from app.domain.retrieval import (
    REQUIRED_QUERY_TYPES,
    RetrievalEvalItem,
    RetrievalEvalMetadata,
    RetrievalJudgment,
    RetrievalQuery,
    build_retrieval_target_inventory,
    load_retrieval_eval_jsonl,
    summarize_retrieval_eval_dataset,
    summarize_retrieval_eval_expansion,
    summarize_retrieval_eval_target_resolvability,
)
from pipelines.build_retrieval_eval_review_report import (
    build_retrieval_eval_review_report,
    build_retrieval_eval_review_report_markdown,
)
from pipelines.build_retrieval_eval_target_report import (
    PRIVATE_CHUNKS_PATH_ALIAS,
    load_child_chunks_from_report,
)


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
        text_length=len("private searchable text"),
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
                text_length=len("private searchable text"),
                quality_flags=[],
            )
        ],
        quality_flags=[],
        public_allowed=False,
        text="private searchable text",
        context_text=None,
    )


def _eval_item(
    *,
    query_type: str,
    index: int,
    review_status: str = "reviewed",
) -> RetrievalEvalItem:
    query_id = f"q-dev-{query_type}-{index:03d}"
    if query_type == "no_answer":
        return RetrievalEvalItem(
            query=RetrievalQuery(
                query_id=query_id,
                query_type="no_answer",
                query_text="오늘 실시간 예약 가능 여부를 알려줘",
                language="ko",
                expected_behavior="abstain",
                user_context="사용자는 실시간 운영 정보를 요청했다.",
            ),
            judgments=[],
            metadata=RetrievalEvalMetadata(
                split="dev",
                difficulty="easy",
                place_ids=["gyeongbokgung"],
                requires_context=False,
                answerability="unanswerable",
                review_status=review_status,
            ),
        )
    requires_context = query_type == "voice_followup"
    return RetrievalEvalItem(
        query=RetrievalQuery(
            query_id=query_id,
            query_type=query_type,
            query_text="경복궁 설명에 필요한 근거를 찾아줘"
            if not requires_context
            else "그 궁은 왜 중요해?",
            language="ko",
            expected_behavior="retrieve",
            user_context="이전 발화는 경복궁과 조선 초 수도 설계였다."
            if requires_context
            else None,
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
            split="dev",
            difficulty="medium",
            place_ids=["gyeongbokgung"],
            requires_context=requires_context,
            answerability="answerable",
            review_status=review_status,
        ),
    )


def _review_items(*, review_status: str = "reviewed") -> list[RetrievalEvalItem]:
    return [
        _eval_item(query_type=query_type, index=index, review_status=review_status)
        for query_type in REQUIRED_QUERY_TYPES
        for index in range(1, 6)
    ]


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )


def test_review_report_markdown_passes_for_reviewed_dev_items() -> None:
    child = _child()
    items = _review_items()
    dataset_summary = summarize_retrieval_eval_dataset(items)
    expansion_summary = summarize_retrieval_eval_expansion(items)
    target_summary = summarize_retrieval_eval_target_resolvability(
        items=items,
        inventory=build_retrieval_target_inventory([child]),
    )

    markdown = build_retrieval_eval_review_report_markdown(
        items=items,
        dataset_summary=dataset_summary,
        expansion_summary=expansion_summary,
        target_summary=target_summary,
        dataset_path=Path("private_data/evals/datasets/retrieval_eval_dev.jsonl"),
        chunks_path_alias=PRIVATE_CHUNKS_PATH_ALIAS,
    )

    assert "| review_gate_status | `PASS` |" in markdown
    assert "| query_count | 35 |" in markdown
    assert "| reviewed_query_count | 35 |" in markdown
    assert "| draft_query_count | 0 |" in markdown
    assert "| voice_followup_context_missing_count | 0 |" in markdown
    assert "| answerable_without_child_target_count | 0 |" in markdown
    assert "| missing_child_target_count | 0 |" in markdown
    assert "| place_fact | 5 | 0 | 5 | 0 | 10 | 5 |" in markdown
    assert "expected_behavior=abstain" in markdown
    assert "모두 짧은 지시어형 질문" not in markdown
    assert "판단 요약인지 확인했다" not in markdown
    assert "<private retrieval eval dataset: retrieval_eval_dev.jsonl>" in markdown
    assert "private_data/evals/datasets/retrieval_eval_dev.jsonl" not in markdown


def test_review_report_markdown_fails_when_draft_items_remain() -> None:
    child = _child()
    items = _review_items(review_status="draft")
    dataset_summary = summarize_retrieval_eval_dataset(items)
    expansion_summary = summarize_retrieval_eval_expansion(items)
    target_summary = summarize_retrieval_eval_target_resolvability(
        items=items,
        inventory=build_retrieval_target_inventory([child]),
    )

    markdown = build_retrieval_eval_review_report_markdown(
        items=items,
        dataset_summary=dataset_summary,
        expansion_summary=expansion_summary,
        target_summary=target_summary,
        dataset_path=Path("private_data/evals/datasets/retrieval_eval_dev.jsonl"),
        chunks_path_alias=PRIVATE_CHUNKS_PATH_ALIAS,
    )

    assert "| review_gate_status | `FAIL` |" in markdown
    assert "| draft_query_count | 35 |" in markdown
    assert "draft_queries_remaining" in markdown
    assert "unreviewed_queries_remaining" in markdown
    assert "dev_review_status_not_reviewed" in markdown


def test_review_report_markdown_fails_when_first_batch_count_is_short() -> None:
    child = _child()
    items = [
        _eval_item(query_type=query_type, index=index)
        for query_type in REQUIRED_QUERY_TYPES
        for index in range(1, 3)
    ]
    dataset_summary = summarize_retrieval_eval_dataset(items)
    expansion_summary = summarize_retrieval_eval_expansion(items)
    target_summary = summarize_retrieval_eval_target_resolvability(
        items=items,
        inventory=build_retrieval_target_inventory([child]),
    )

    markdown = build_retrieval_eval_review_report_markdown(
        items=items,
        dataset_summary=dataset_summary,
        expansion_summary=expansion_summary,
        target_summary=target_summary,
        dataset_path=Path("private_data/evals/datasets/retrieval_eval_dev.jsonl"),
        chunks_path_alias=PRIVATE_CHUNKS_PATH_ALIAS,
    )

    assert "| review_gate_status | `FAIL` |" in markdown
    assert "| query_count | 14 |" in markdown
    assert "private_dev_first_review_query_count_mismatch" in markdown
    assert "private_dev_first_review_query_type_count_mismatch" in markdown


def test_review_report_pipeline_writes_public_safe_report(tmp_path: Path) -> None:
    chunks_path = tmp_path / "parent_child_chunks.json"
    dataset_path = tmp_path / "retrieval_eval_dev.jsonl"
    report_path = tmp_path / "review_report.md"
    child = _child()
    items = _review_items()
    _write_json(
        chunks_path,
        {
            "report_version": "chunking-quality/v1",
            "chunking_run_id": "chunking-test",
            "children": [child.model_dump(mode="json")],
        },
    )
    _write_jsonl(dataset_path, [item.model_dump(mode="json") for item in items])

    summary = build_retrieval_eval_review_report(
        dataset_path=dataset_path,
        chunks_path=chunks_path,
        report_path=report_path,
    )
    report = report_path.read_text(encoding="utf-8")

    assert summary.reviewed_query_count == 35
    assert "| review_gate_status | `PASS` |" in report
    assert "private searchable text" not in report
    assert str(chunks_path) not in report
    assert str(dataset_path).replace("\\", "/") not in report
    assert "<private retrieval eval dataset: retrieval_eval_dev.jsonl>" in report


def test_checked_in_private_dev_review_report_matches_private_dataset_when_available() -> None:
    dataset_path = Path("private_data/evals/datasets/retrieval_eval_dev.jsonl")
    chunks_path = Path("private_data/reports/parent_child_chunks.json")
    report_path = Path("evals/reports/retrieval_eval_private_dev_review_report.md")
    if not dataset_path.exists() or not chunks_path.exists():
        pytest.skip("private retrieval eval dataset is not available")

    items = load_retrieval_eval_jsonl(dataset_path)
    children = load_child_chunks_from_report(chunks_path)
    dataset_summary = summarize_retrieval_eval_dataset(items)
    expansion_summary = summarize_retrieval_eval_expansion(items)
    target_summary = summarize_retrieval_eval_target_resolvability(
        items=items,
        inventory=build_retrieval_target_inventory(children),
    )
    report = report_path.read_text(encoding="utf-8")
    expected_report = build_retrieval_eval_review_report_markdown(
        items=items,
        dataset_summary=dataset_summary,
        expansion_summary=expansion_summary,
        target_summary=target_summary,
        dataset_path=dataset_path,
        chunks_path_alias=PRIVATE_CHUNKS_PATH_ALIAS,
    )

    assert report == expected_report
    assert f"| query_count | {dataset_summary.query_count} |" in report
    assert f"| reviewed_query_count | {expansion_summary.reviewed_query_count} |" in report
    assert f"| draft_query_count | {expansion_summary.draft_query_count} |" in report
    assert f"| judgment_target_count | {target_summary.judgment_target_count} |" in report
    assert "| review_gate_status | `PASS` |" in report
    assert "| place_fact | 5 | 0 | 5 | 0 | 10 | 5 |" in report
