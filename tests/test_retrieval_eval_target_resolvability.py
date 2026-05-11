from __future__ import annotations

import json
from pathlib import Path

from app.domain.chunking import ChildChunk, ChunkSourceRef
from app.domain.data_contracts import ElementReference, PageSpan
from app.domain.retrieval import (
    RetrievalEvalItem,
    RetrievalEvalMetadata,
    RetrievalEvalTargetResolvabilitySummary,
    RetrievalJudgment,
    RetrievalQuery,
    build_retrieval_target_inventory,
    collect_retrieval_eval_target_resolvability_failures,
    summarize_retrieval_eval_target_resolvability,
)
from pipelines.build_retrieval_eval_target_report import (
    build_retrieval_eval_target_report,
    build_retrieval_eval_target_report_markdown,
)


def _page_span() -> PageSpan:
    return PageSpan(
        page_local_start=1,
        page_local_end=1,
        page_global_start=1,
        page_global_end=1,
    )


def _child(
    *,
    child_id: str = "child-a",
    parent_id: str = "parent-a",
    doc_id: str = "doc-a",
    text: str = "private searchable text",
) -> ChildChunk:
    return ChildChunk(
        child_id=child_id,
        parent_id=parent_id,
        doc_id=doc_id,
        doc_title=doc_id,
        parser_run_id="parser-run",
        source_block_ids=[f"block-{child_id}"],
        context_block_ids=[],
        page_span=_page_span(),
        text_hash="a" * 64,
        text_length=len(text),
        element_type_mix={"paragraph": 1},
        citation_refs=[
            ChunkSourceRef(
                block_id=f"block-{child_id}",
                doc_id=doc_id,
                element_type="paragraph",
                page_span=_page_span(),
                element_refs=[
                    ElementReference(
                        element_id=f"element-{child_id}",
                        element_type="paragraph",
                        element_index=1,
                    )
                ],
                source_file_name=f"{doc_id}.pdf",
                text_hash="b" * 64,
                text_length=len(text),
                quality_flags=[],
            )
        ],
        quality_flags=[],
        public_allowed=False,
        text=text,
        context_text=None,
    )


def _eval_item(
    *,
    query_id: str = "q-one",
    child_ids: list[str] | None = None,
    parent_ids: list[str] | None = None,
    doc_ids: list[str] | None = None,
    rationale_summary: str = "target ids only",
) -> RetrievalEvalItem:
    return RetrievalEvalItem(
        query=RetrievalQuery(
            query_id=query_id,
            query_type="place_fact",
            query_text="경복궁 근거를 찾아줘",
            language="ko",
            expected_behavior="retrieve",
        ),
        judgments=[
            RetrievalJudgment(
                query_id=query_id,
                relevant_child_ids=child_ids or [],
                relevant_parent_ids=parent_ids or [],
                relevant_doc_ids=doc_ids or [],
                relevance_grade=3,
                rationale_summary=rationale_summary,
            )
        ],
        metadata=RetrievalEvalMetadata(
            split="seed",
            difficulty="medium",
            place_ids=["gyeongbokgung"],
            requires_context=False,
            answerability="answerable",
            review_status="reviewed",
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


def _private_eval_dataset_path(file_name: str = "retrieval_eval_dev.jsonl") -> Path:
    return Path("private_data") / "evals" / "datasets" / file_name


def test_target_resolvability_detects_missing_child_parent_and_doc_targets() -> None:
    inventory = build_retrieval_target_inventory([_child()])
    item = _eval_item(
        child_ids=["child-a", "child-missing"],
        parent_ids=["parent-a", "parent-missing"],
        doc_ids=["doc-a", "doc-missing"],
    )

    summary = summarize_retrieval_eval_target_resolvability(
        items=[item],
        inventory=inventory,
    )

    assert summary.judgment_target_count == 6
    assert summary.resolved_child_target_count == 1
    assert summary.missing_child_target_count == 1
    assert summary.resolved_parent_target_count == 1
    assert summary.missing_parent_target_count == 1
    assert summary.resolved_doc_target_count == 1
    assert summary.missing_doc_target_count == 1
    assert collect_retrieval_eval_target_resolvability_failures(summary) == [
        "missing_child_targets",
        "missing_parent_targets",
        "missing_doc_targets",
    ]


def test_target_resolvability_requires_child_or_parent_target_for_answerable_query() -> None:
    inventory = build_retrieval_target_inventory([_child()])
    item = _eval_item(doc_ids=["doc-a"])

    summary = summarize_retrieval_eval_target_resolvability(
        items=[item],
        inventory=inventory,
    )

    assert summary.answerable_without_child_or_parent_target_count == 1
    assert "answerable_without_child_or_parent_target" in (
        collect_retrieval_eval_target_resolvability_failures(summary)
    )


def test_target_resolvability_failure_collector_flags_no_answer_positive_target() -> None:
    summary = RetrievalEvalTargetResolvabilitySummary(
        query_count=1,
        judgment_count=1,
        answerable_query_count=0,
        no_answer_query_count=1,
        searchable_child_count=1,
        searchable_parent_count=1,
        searchable_doc_count=1,
        judgment_target_count=1,
        child_target_count=1,
        resolved_child_target_count=1,
        missing_child_target_count=0,
        parent_target_count=0,
        resolved_parent_target_count=0,
        missing_parent_target_count=0,
        doc_target_count=0,
        resolved_doc_target_count=0,
        missing_doc_target_count=0,
        answerable_without_child_or_parent_target_count=0,
        no_answer_with_positive_target_count=1,
        public_raw_text_leakage_count=0,
        private_path_leakage_count=0,
        secret_like_leakage_count=0,
    )

    assert "no_answer_with_positive_target" in (
        collect_retrieval_eval_target_resolvability_failures(summary)
    )


def test_target_resolvability_detects_public_secret_like_and_long_text_values() -> None:
    inventory = build_retrieval_target_inventory([_child()])
    item = _eval_item(
        child_ids=["child-a"],
        rationale_summary=(
            ("가" * 601)
            + (" s" + "k-proj-secret ")
            + ("C:" + "\\private\\source.pdf")
        ),
    )

    summary = summarize_retrieval_eval_target_resolvability(
        items=[item],
        inventory=inventory,
    )

    assert summary.public_raw_text_leakage_count == 1
    assert summary.private_path_leakage_count == 1
    assert summary.secret_like_leakage_count == 1
    assert "public_raw_text_leakage" in (
        collect_retrieval_eval_target_resolvability_failures(summary)
    )
    assert "secret_like_leakage" in (
        collect_retrieval_eval_target_resolvability_failures(summary)
    )
    assert "private_path_leakage" in (
        collect_retrieval_eval_target_resolvability_failures(summary)
    )


def test_target_inventory_ignores_non_searchable_children() -> None:
    inventory = build_retrieval_target_inventory(
        [
            _child(
                child_id="child-empty",
                parent_id="parent-empty",
                doc_id="doc-empty",
                text="",
            )
        ]
    )
    item = _eval_item(
        child_ids=["child-empty"],
        parent_ids=["parent-empty"],
        doc_ids=["doc-empty"],
    )

    summary = summarize_retrieval_eval_target_resolvability(
        items=[item],
        inventory=inventory,
    )

    assert summary.searchable_child_count == 0
    assert summary.missing_child_target_count == 1
    assert summary.missing_parent_target_count == 1
    assert summary.missing_doc_target_count == 1


def test_target_report_pipeline_writes_public_safe_report(tmp_path: Path) -> None:
    chunks_path = tmp_path / "parent_child_chunks.json"
    dataset_path = tmp_path / "retrieval_eval_seed.jsonl"
    report_path = tmp_path / "target_report.md"
    child = _child(text="private source text 경복궁 한양")
    item = _eval_item(
        child_ids=[child.child_id],
        parent_ids=[child.parent_id],
        doc_ids=[child.doc_id],
    )
    _write_json(
        chunks_path,
        {
            "report_version": "chunking-quality/v1",
            "chunking_run_id": "chunking-test",
            "children": [child.model_dump(mode="json")],
        },
    )
    _write_jsonl(dataset_path, [item.model_dump(mode="json")])

    summary = build_retrieval_eval_target_report(
        chunks_path=chunks_path,
        dataset_path=dataset_path,
        report_path=report_path,
    )
    report = report_path.read_text(encoding="utf-8")

    assert summary.missing_child_target_count == 0
    assert summary.missing_parent_target_count == 0
    assert summary.missing_doc_target_count == 0
    assert collect_retrieval_eval_target_resolvability_failures(summary) == []
    assert "| target_resolvability_status | `PASS` |" in report
    assert "| judgment_target_count | 3 |" in report
    assert "private source text" not in report
    assert str(chunks_path) not in report
    assert str(dataset_path).replace("\\", "/") not in report


def test_target_report_points_completed_private_dev_to_benchmark_readiness() -> None:
    summary = RetrievalEvalTargetResolvabilitySummary(
        query_count=70,
        judgment_count=60,
        answerable_query_count=60,
        no_answer_query_count=10,
        searchable_child_count=10,
        searchable_parent_count=10,
        searchable_doc_count=3,
        judgment_target_count=120,
        child_target_count=60,
        resolved_child_target_count=60,
        missing_child_target_count=0,
        parent_target_count=40,
        resolved_parent_target_count=40,
        missing_parent_target_count=0,
        doc_target_count=20,
        resolved_doc_target_count=20,
        missing_doc_target_count=0,
        answerable_without_child_or_parent_target_count=0,
        no_answer_with_positive_target_count=0,
        public_raw_text_leakage_count=0,
        private_path_leakage_count=0,
        secret_like_leakage_count=0,
    )

    markdown = build_retrieval_eval_target_report_markdown(
        summary=summary,
        dataset_path=_private_eval_dataset_path(),
        chunks_path_alias="<private parent_child_chunks report>",
    )

    assert "private test lock report를 확인한다." in markdown
    assert "private benchmark readiness report를 확인한다." in markdown
    assert "private dev/test 평가 문항을 query type별로 확장한다." not in markdown
    assert _private_eval_dataset_path().as_posix() not in markdown


def test_target_report_points_completed_private_test_to_ablation_runner() -> None:
    summary = RetrievalEvalTargetResolvabilitySummary(
        query_count=35,
        judgment_count=30,
        answerable_query_count=30,
        no_answer_query_count=5,
        searchable_child_count=10,
        searchable_parent_count=10,
        searchable_doc_count=3,
        judgment_target_count=90,
        child_target_count=30,
        resolved_child_target_count=30,
        missing_child_target_count=0,
        parent_target_count=30,
        resolved_parent_target_count=30,
        missing_parent_target_count=0,
        doc_target_count=30,
        resolved_doc_target_count=30,
        missing_doc_target_count=0,
        answerable_without_child_or_parent_target_count=0,
        no_answer_with_positive_target_count=0,
        public_raw_text_leakage_count=0,
        private_path_leakage_count=0,
        secret_like_leakage_count=0,
    )
    dataset_path = Path("private_data") / "evals" / "datasets" / "retrieval_eval_test.jsonl"

    markdown = build_retrieval_eval_target_report_markdown(
        summary=summary,
        dataset_path=dataset_path,
        chunks_path_alias="<private parent_child_chunks report>",
    )

    assert "private benchmark readiness report를 확인한다." in markdown
    assert "BM25 기준 chunking ablation runner를 구현한다." in markdown
    assert "private dev/test 평가 문항을 query type별로 확장한다." not in markdown
    assert dataset_path.as_posix() not in markdown


def test_target_report_blocks_next_steps_when_target_gate_fails() -> None:
    summary = RetrievalEvalTargetResolvabilitySummary(
        query_count=70,
        judgment_count=60,
        answerable_query_count=60,
        no_answer_query_count=10,
        searchable_child_count=10,
        searchable_parent_count=10,
        searchable_doc_count=3,
        judgment_target_count=120,
        child_target_count=60,
        resolved_child_target_count=59,
        missing_child_target_count=1,
        parent_target_count=40,
        resolved_parent_target_count=40,
        missing_parent_target_count=0,
        doc_target_count=20,
        resolved_doc_target_count=20,
        missing_doc_target_count=0,
        answerable_without_child_or_parent_target_count=0,
        no_answer_with_positive_target_count=0,
        public_raw_text_leakage_count=1,
        private_path_leakage_count=0,
        secret_like_leakage_count=0,
    )

    markdown = build_retrieval_eval_target_report_markdown(
        summary=summary,
        dataset_path=_private_eval_dataset_path(),
        chunks_path_alias="<private parent_child_chunks report>",
    )

    assert "| target_resolvability_status | `FAIL` |" in markdown
    assert "target resolvability failure를 먼저 해소한다." in markdown
    assert "private test lock report를 확인한다." not in markdown
