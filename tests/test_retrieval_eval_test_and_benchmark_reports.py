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
from pipelines.build_retrieval_eval_private_benchmark_report import (
    build_retrieval_eval_private_benchmark_report,
    build_retrieval_eval_private_benchmark_report_markdown,
)
from pipelines.build_retrieval_eval_target_report import (
    PRIVATE_CHUNKS_PATH_ALIAS,
    load_child_chunks_from_report,
)
from pipelines.build_retrieval_eval_test_lock_report import (
    build_retrieval_eval_test_lock_report,
    build_retrieval_eval_test_lock_report_markdown,
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
    split: str,
    review_status: str,
    index: int,
) -> RetrievalEvalItem:
    query_id = f"q-{split}-{query_type}-{index:03d}"
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
                split=split,
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
            split=split,
            difficulty="medium",
            place_ids=["gyeongbokgung"],
            requires_context=requires_context,
            answerability="answerable",
            review_status=review_status,
        ),
    )


def _eval_items(
    *,
    split: str,
    review_status: str,
    per_type: int,
) -> list[RetrievalEvalItem]:
    return [
        _eval_item(
            query_type=query_type,
            split=split,
            review_status=review_status,
            index=index,
        )
        for query_type in REQUIRED_QUERY_TYPES
        for index in range(1, per_type + 1)
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


def _private_eval_dataset_path(file_name: str) -> Path:
    return Path("private_data") / "evals" / "datasets" / file_name


def _private_chunks_path() -> Path:
    return Path("private_data") / "reports" / "parent_child_chunks.json"


def test_test_lock_report_markdown_passes_for_locked_test_items() -> None:
    child = _child()
    items = _eval_items(split="test", review_status="locked", per_type=5)
    dataset_summary = summarize_retrieval_eval_dataset(items)
    expansion_summary = summarize_retrieval_eval_expansion(items)
    target_summary = summarize_retrieval_eval_target_resolvability(
        items=items,
        inventory=build_retrieval_target_inventory([child]),
    )

    markdown = build_retrieval_eval_test_lock_report_markdown(
        items=items,
        dataset_summary=dataset_summary,
        expansion_summary=expansion_summary,
        target_summary=target_summary,
        dataset_path=_private_eval_dataset_path("retrieval_eval_test.jsonl"),
        chunks_path_alias=PRIVATE_CHUNKS_PATH_ALIAS,
    )

    assert "| test_lock_gate_status | `PASS` |" in markdown
    assert "| query_count | 35 |" in markdown
    assert "| test_query_count | 35 |" in markdown
    assert "| answerable_query_count | 30 |" in markdown
    assert "| no_answer_query_count | 5 |" in markdown
    assert "| locked_query_count | 35 |" in markdown
    assert "| missing_child_target_count | 0 |" in markdown
    assert "| place_fact | 5 | 0 | 0 | 5 | 5 | 0 |" in markdown
    assert "<private retrieval eval dataset: retrieval_eval_test.jsonl>" in markdown
    assert _private_eval_dataset_path("retrieval_eval_test.jsonl").as_posix() not in markdown


def test_test_lock_report_markdown_fails_when_status_is_not_locked() -> None:
    child = _child()
    items = _eval_items(split="test", review_status="reviewed", per_type=5)
    dataset_summary = summarize_retrieval_eval_dataset(items)
    expansion_summary = summarize_retrieval_eval_expansion(items)
    target_summary = summarize_retrieval_eval_target_resolvability(
        items=items,
        inventory=build_retrieval_target_inventory([child]),
    )

    markdown = build_retrieval_eval_test_lock_report_markdown(
        items=items,
        dataset_summary=dataset_summary,
        expansion_summary=expansion_summary,
        target_summary=target_summary,
        dataset_path=_private_eval_dataset_path("retrieval_eval_test.jsonl"),
        chunks_path_alias=PRIVATE_CHUNKS_PATH_ALIAS,
    )

    assert "| test_lock_gate_status | `FAIL` |" in markdown
    assert "| reviewed_query_count | 35 |" in markdown
    assert "test_review_status_not_locked" in markdown


def test_test_lock_report_markdown_fails_for_missing_target_and_public_safety() -> None:
    child = _child()
    items = _eval_items(split="test", review_status="locked", per_type=5)
    unsafe_query = items[0].query.model_copy(
        update={"query_text": "검수용 private path " + "C:" + "\\private\\source.pdf"}
    )
    items[0] = items[0].model_copy(update={"query": unsafe_query})
    dataset_summary = summarize_retrieval_eval_dataset(items)
    expansion_summary = summarize_retrieval_eval_expansion(items)
    target_summary = summarize_retrieval_eval_target_resolvability(
        items=items,
        inventory=build_retrieval_target_inventory(
            [
                child.model_copy(
                    update={
                        "child_id": "other-child",
                        "parent_id": "other-parent",
                        "doc_id": "other-doc",
                    }
                )
            ]
        ),
    )

    markdown = build_retrieval_eval_test_lock_report_markdown(
        items=items,
        dataset_summary=dataset_summary,
        expansion_summary=expansion_summary,
        target_summary=target_summary,
        dataset_path=_private_eval_dataset_path("retrieval_eval_test.jsonl"),
        chunks_path_alias=PRIVATE_CHUNKS_PATH_ALIAS,
    )

    assert "| test_lock_gate_status | `FAIL` |" in markdown
    assert "missing_child_targets" in markdown
    assert "missing_parent_targets" in markdown
    assert "missing_doc_targets" in markdown
    assert "private_path_leakage" in markdown
    assert "C:" + "\\private\\source.pdf" not in markdown


def test_test_lock_report_pipeline_writes_public_safe_report(tmp_path: Path) -> None:
    chunks_path = tmp_path / "parent_child_chunks.json"
    dataset_path = tmp_path / "retrieval_eval_test.jsonl"
    report_path = tmp_path / "test_lock_report.md"
    child = _child()
    items = _eval_items(split="test", review_status="locked", per_type=5)
    _write_json(
        chunks_path,
        {
            "report_version": "chunking-quality/v1",
            "chunking_run_id": "chunking-test",
            "children": [child.model_dump(mode="json")],
        },
    )
    _write_jsonl(dataset_path, [item.model_dump(mode="json") for item in items])

    summary = build_retrieval_eval_test_lock_report(
        dataset_path=dataset_path,
        chunks_path=chunks_path,
        report_path=report_path,
    )
    report = report_path.read_text(encoding="utf-8")

    assert summary.locked_query_count == 35
    assert "| test_lock_gate_status | `PASS` |" in report
    assert "private searchable text" not in report
    assert str(chunks_path) not in report
    assert str(dataset_path).replace("\\", "/") not in report
    assert "<private retrieval eval dataset: retrieval_eval_test.jsonl>" in report


def test_checked_in_private_test_lock_report_matches_private_dataset_when_available() -> None:
    dataset_path = _private_eval_dataset_path("retrieval_eval_test.jsonl")
    chunks_path = _private_chunks_path()
    report_path = Path("evals/reports/retrieval_eval_private_test_lock_report.md")
    if not dataset_path.exists() or not chunks_path.exists():
        pytest.skip("private retrieval eval test dataset is not available")

    items = load_retrieval_eval_jsonl(dataset_path)
    children = load_child_chunks_from_report(chunks_path)
    dataset_summary = summarize_retrieval_eval_dataset(items)
    expansion_summary = summarize_retrieval_eval_expansion(items)
    target_summary = summarize_retrieval_eval_target_resolvability(
        items=items,
        inventory=build_retrieval_target_inventory(children),
    )
    report = report_path.read_text(encoding="utf-8")
    expected_report = build_retrieval_eval_test_lock_report_markdown(
        items=items,
        dataset_summary=dataset_summary,
        expansion_summary=expansion_summary,
        target_summary=target_summary,
        dataset_path=dataset_path,
        chunks_path_alias=PRIVATE_CHUNKS_PATH_ALIAS,
    )

    assert report == expected_report
    assert "| test_lock_gate_status | `PASS` |" in report
    assert "| query_count | 35 |" in report
    assert "| locked_query_count | 35 |" in report


def test_private_benchmark_report_markdown_passes_for_dev_and_test_items() -> None:
    child = _child()
    items = _eval_items(split="dev", review_status="reviewed", per_type=10) + _eval_items(
        split="test",
        review_status="locked",
        per_type=5,
    )
    dataset_summary = summarize_retrieval_eval_dataset(items)
    expansion_summary = summarize_retrieval_eval_expansion(items)
    target_summary = summarize_retrieval_eval_target_resolvability(
        items=items,
        inventory=build_retrieval_target_inventory([child]),
    )

    markdown = build_retrieval_eval_private_benchmark_report_markdown(
        items=items,
        dataset_summary=dataset_summary,
        expansion_summary=expansion_summary,
        target_summary=target_summary,
        dev_dataset_path=_private_eval_dataset_path("retrieval_eval_dev.jsonl"),
        test_dataset_path=_private_eval_dataset_path("retrieval_eval_test.jsonl"),
        chunks_path_alias=PRIVATE_CHUNKS_PATH_ALIAS,
    )

    assert "| benchmark_readiness_status | `PASS` |" in markdown
    assert "| current_query_count | 105 |" in markdown
    assert "| dev_query_count | 70 |" in markdown
    assert "| test_query_count | 35 |" in markdown
    assert "| answerable_query_count | 90 |" in markdown
    assert "| no_answer_query_count | 15 |" in markdown
    assert "| reviewed_query_count | 70 |" in markdown
    assert "| locked_query_count | 35 |" in markdown
    assert "| place_fact | 10 | 5 | 0 | 10 | 5 | 10 | 5 | 0 | 0 |" in markdown
    assert "<private retrieval eval dataset: retrieval_eval_dev.jsonl>" in markdown
    assert "<private retrieval eval dataset: retrieval_eval_test.jsonl>" in markdown


def test_private_benchmark_report_markdown_fails_when_test_split_is_missing() -> None:
    child = _child()
    items = _eval_items(split="dev", review_status="reviewed", per_type=10)
    dataset_summary = summarize_retrieval_eval_dataset(items)
    expansion_summary = summarize_retrieval_eval_expansion(items)
    target_summary = summarize_retrieval_eval_target_resolvability(
        items=items,
        inventory=build_retrieval_target_inventory([child]),
    )

    markdown = build_retrieval_eval_private_benchmark_report_markdown(
        items=items,
        dataset_summary=dataset_summary,
        expansion_summary=expansion_summary,
        target_summary=target_summary,
        dev_dataset_path=_private_eval_dataset_path("retrieval_eval_dev.jsonl"),
        test_dataset_path=_private_eval_dataset_path("retrieval_eval_test.jsonl"),
        chunks_path_alias=PRIVATE_CHUNKS_PATH_ALIAS,
    )

    assert "| benchmark_readiness_status | `FAIL` |" in markdown
    assert "missing_test_split" in markdown
    assert "private_benchmark_test_query_count_mismatch" in markdown


def test_private_benchmark_report_markdown_fails_for_missing_target_and_public_safety() -> None:
    child = _child()
    items = _eval_items(split="dev", review_status="reviewed", per_type=10) + _eval_items(
        split="test",
        review_status="locked",
        per_type=5,
    )
    unsafe_query = items[-1].query.model_copy(
        update={"query_text": "검수용 private path " + "F:" + "\\private\\source.pdf"}
    )
    items[-1] = items[-1].model_copy(update={"query": unsafe_query})
    dataset_summary = summarize_retrieval_eval_dataset(items)
    expansion_summary = summarize_retrieval_eval_expansion(items)
    target_summary = summarize_retrieval_eval_target_resolvability(
        items=items,
        inventory=build_retrieval_target_inventory(
            [
                child.model_copy(
                    update={
                        "child_id": "other-child",
                        "parent_id": "other-parent",
                        "doc_id": "other-doc",
                    }
                )
            ]
        ),
    )

    markdown = build_retrieval_eval_private_benchmark_report_markdown(
        items=items,
        dataset_summary=dataset_summary,
        expansion_summary=expansion_summary,
        target_summary=target_summary,
        dev_dataset_path=_private_eval_dataset_path("retrieval_eval_dev.jsonl"),
        test_dataset_path=_private_eval_dataset_path("retrieval_eval_test.jsonl"),
        chunks_path_alias=PRIVATE_CHUNKS_PATH_ALIAS,
    )

    assert "| benchmark_readiness_status | `FAIL` |" in markdown
    assert "missing_child_targets" in markdown
    assert "missing_parent_targets" in markdown
    assert "missing_doc_targets" in markdown
    assert "private_path_leakage" in markdown
    assert "F:" + "\\private\\source.pdf" not in markdown


def test_private_benchmark_report_pipeline_writes_public_safe_report(
    tmp_path: Path,
) -> None:
    chunks_path = tmp_path / "parent_child_chunks.json"
    dev_dataset_path = tmp_path / "retrieval_eval_dev.jsonl"
    test_dataset_path = tmp_path / "retrieval_eval_test.jsonl"
    report_path = tmp_path / "benchmark_report.md"
    child = _child()
    dev_items = _eval_items(split="dev", review_status="reviewed", per_type=10)
    test_items = _eval_items(split="test", review_status="locked", per_type=5)
    _write_json(
        chunks_path,
        {
            "report_version": "chunking-quality/v1",
            "chunking_run_id": "chunking-test",
            "children": [child.model_dump(mode="json")],
        },
    )
    _write_jsonl(dev_dataset_path, [item.model_dump(mode="json") for item in dev_items])
    _write_jsonl(test_dataset_path, [item.model_dump(mode="json") for item in test_items])

    summary = build_retrieval_eval_private_benchmark_report(
        dev_dataset_path=dev_dataset_path,
        test_dataset_path=test_dataset_path,
        chunks_path=chunks_path,
        report_path=report_path,
    )
    report = report_path.read_text(encoding="utf-8")

    assert summary.current_query_count == 105
    assert "| benchmark_readiness_status | `PASS` |" in report
    assert "private searchable text" not in report
    assert str(chunks_path) not in report
    assert str(dev_dataset_path).replace("\\", "/") not in report
    assert str(test_dataset_path).replace("\\", "/") not in report
    assert "<private retrieval eval dataset: retrieval_eval_dev.jsonl>" in report
    assert "<private retrieval eval dataset: retrieval_eval_test.jsonl>" in report


def test_checked_in_private_benchmark_report_matches_private_datasets_when_available() -> None:
    dev_dataset_path = _private_eval_dataset_path("retrieval_eval_dev.jsonl")
    test_dataset_path = _private_eval_dataset_path("retrieval_eval_test.jsonl")
    chunks_path = _private_chunks_path()
    report_path = Path(
        "evals/reports/retrieval_eval_private_benchmark_readiness_report.md"
    )
    if (
        not dev_dataset_path.exists()
        or not test_dataset_path.exists()
        or not chunks_path.exists()
    ):
        pytest.skip("private retrieval eval benchmark datasets are not available")

    items = load_retrieval_eval_jsonl(dev_dataset_path) + load_retrieval_eval_jsonl(
        test_dataset_path
    )
    children = load_child_chunks_from_report(chunks_path)
    dataset_summary = summarize_retrieval_eval_dataset(items)
    expansion_summary = summarize_retrieval_eval_expansion(items)
    target_summary = summarize_retrieval_eval_target_resolvability(
        items=items,
        inventory=build_retrieval_target_inventory(children),
    )
    report = report_path.read_text(encoding="utf-8")
    expected_report = build_retrieval_eval_private_benchmark_report_markdown(
        items=items,
        dataset_summary=dataset_summary,
        expansion_summary=expansion_summary,
        target_summary=target_summary,
        dev_dataset_path=dev_dataset_path,
        test_dataset_path=test_dataset_path,
        chunks_path_alias=PRIVATE_CHUNKS_PATH_ALIAS,
    )

    assert report == expected_report
    assert "| benchmark_readiness_status | `PASS` |" in report
    assert "| current_query_count | 105 |" in report
    assert "| dev_query_count | 70 |" in report
    assert "| test_query_count | 35 |" in report
