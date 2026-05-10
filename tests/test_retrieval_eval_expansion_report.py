from __future__ import annotations

import json
from pathlib import Path

from app.domain.chunking import ChildChunk, ChunkSourceRef
from app.domain.data_contracts import ElementReference, PageSpan
from app.domain.retrieval import (
    REQUIRED_QUERY_TYPES,
    RetrievalEvalItem,
    RetrievalEvalMetadata,
    RetrievalTargetInventory,
    RetrievalJudgment,
    RetrievalQuery,
    build_retrieval_target_inventory,
    collect_retrieval_eval_expansion_readiness_failures,
    load_retrieval_eval_jsonl,
    summarize_retrieval_eval_dataset,
    summarize_retrieval_eval_expansion,
    summarize_retrieval_eval_target_resolvability,
)
from pipelines.build_retrieval_eval_expansion_report import (
    build_retrieval_eval_expansion_report,
    build_retrieval_eval_expansion_report_markdown,
)
from pipelines.build_retrieval_eval_target_report import PRIVATE_CHUNKS_PATH_ALIAS


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
    child_id: str = "child-a",
    parent_id: str = "parent-a",
    doc_id: str = "doc-a",
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
                relevant_child_ids=[child_id],
                relevant_parent_ids=[parent_id],
                relevant_doc_ids=[doc_id],
                relevance_grade=3,
                rationale_summary="target ids only",
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


def test_retrieval_eval_expansion_summary_matches_seed_targets() -> None:
    items = load_retrieval_eval_jsonl(Path("evals/datasets/retrieval_eval_seed.jsonl"))

    summary = summarize_retrieval_eval_expansion(items)

    assert summary.target_query_count == 105
    assert summary.current_query_count == 14
    assert summary.overall_shortfall_count == 91
    assert summary.seed_query_count == 14
    assert summary.dev_query_count == 0
    assert summary.test_query_count == 0
    assert summary.dev_test_target_query_count == 105
    assert summary.dev_test_current_query_count == 0
    assert summary.dev_test_shortfall_count == 105
    assert summary.draft_query_count == 0
    assert summary.reviewed_query_count == 14
    assert summary.locked_query_count == 0
    assert summary.public_raw_text_leakage_count == 0
    assert summary.private_path_leakage_count == 0
    assert summary.secret_like_leakage_count == 0
    assert collect_retrieval_eval_expansion_readiness_failures(summary) == [
        "overall_query_target_shortfall",
        "missing_dev_split",
        "missing_test_split",
        "dev_query_type_target_shortfall",
        "test_query_type_target_shortfall",
    ]
    assert {
        query_type: row.total_shortfall_count
        for query_type, row in summary.query_type_rows.items()
    } == {query_type: 13 for query_type in REQUIRED_QUERY_TYPES}


def test_retrieval_eval_expansion_report_markdown_matches_seed_counts() -> None:
    items = load_retrieval_eval_jsonl(Path("evals/datasets/retrieval_eval_seed.jsonl"))
    dataset_summary = summarize_retrieval_eval_dataset(items)
    expansion_summary = summarize_retrieval_eval_expansion(items)
    target_summary = summarize_retrieval_eval_target_resolvability(
        items=[],
        inventory=RetrievalTargetInventory(),
    )

    markdown = build_retrieval_eval_expansion_report_markdown(
        dataset_summary=dataset_summary,
        expansion_summary=expansion_summary,
        target_summary=target_summary,
        dataset_path=Path("evals/datasets/retrieval_eval_seed.jsonl"),
        chunks_path_alias=PRIVATE_CHUNKS_PATH_ALIAS,
    )

    assert "| authoring_status | `PASS` |" in markdown
    assert "| expansion_readiness_status | `INCOMPLETE` |" in markdown
    assert "| target_query_count | 105 |" in markdown
    assert "| current_query_count | 14 |" in markdown
    assert "| overall_shortfall_count | 91 |" in markdown
    assert "| dev_test_shortfall_count | 105 |" in markdown
    assert "| place_fact | 2 | 0 | 0 | 10 | 5 | 10 | 5 | 2 | 15 | 13 |" in markdown
    assert "overall_query_target_shortfall" in markdown


def test_retrieval_eval_expansion_report_describes_dev_only_progress() -> None:
    items = [
        _eval_item(query_id=f"q-dev-place-fact-{index:03d}").model_copy(
            update={
                "metadata": _eval_item().metadata.model_copy(
                    update={"split": "dev", "review_status": "draft"}
                )
            }
        )
        for index in range(1, 6)
    ]
    dataset_summary = summarize_retrieval_eval_dataset(items)
    expansion_summary = summarize_retrieval_eval_expansion(items)
    target_summary = summarize_retrieval_eval_target_resolvability(
        items=items,
        inventory=build_retrieval_target_inventory([_child()]),
    )

    markdown = build_retrieval_eval_expansion_report_markdown(
        dataset_summary=dataset_summary,
        expansion_summary=expansion_summary,
        target_summary=target_summary,
        dataset_path=Path("private_data/evals/datasets/retrieval_eval_dev.jsonl"),
        chunks_path_alias=PRIVATE_CHUNKS_PATH_ALIAS,
    )

    assert "<private retrieval eval dataset: retrieval_eval_dev.jsonl>" in markdown
    assert "현재 입력 평가셋은 dev 5개로 구성되어 있으며 총 5개다." in markdown
    assert "| dev_query_count | 5 |" in markdown
    assert "| draft_query_count | 5 |" in markdown
    assert "다음 작성 우선순위는 dev 부족분이 남은" in markdown
    assert "query type별 private dev 부족분을 채워 dev 10개씩 맞춘다." in markdown
    assert "private_data/evals/datasets/retrieval_eval_dev.jsonl" not in markdown


def test_retrieval_eval_expansion_report_deduplicates_public_safety_failures() -> None:
    child = _child()
    item = _eval_item()
    unsafe_item = item.model_copy(
        update={
            "judgments": [
                item.judgments[0].model_copy(
                    update={
                        "rationale_summary": (
                            ("가" * 601)
                            + (" s" + "k-proj-secret ")
                            + ("C:" + "\\private\\source.pdf")
                        )
                    }
                )
            ]
        }
    )
    dataset_summary = summarize_retrieval_eval_dataset([unsafe_item])
    expansion_summary = summarize_retrieval_eval_expansion([unsafe_item])
    target_summary = summarize_retrieval_eval_target_resolvability(
        items=[unsafe_item],
        inventory=build_retrieval_target_inventory([child]),
    )

    markdown = build_retrieval_eval_expansion_report_markdown(
        dataset_summary=dataset_summary,
        expansion_summary=expansion_summary,
        target_summary=target_summary,
        dataset_path=Path("evals/datasets/retrieval_eval_seed.jsonl"),
        chunks_path_alias=PRIVATE_CHUNKS_PATH_ALIAS,
    )

    assert "| public_raw_text_leakage_count | 1 |" in markdown
    assert "| private_path_leakage_count | 1 |" in markdown
    assert "| secret_like_leakage_count | 1 |" in markdown
    assert (
        "blocking_failures=['missing_required_query_types', "
        "'query_type_min_shortfall', 'public_raw_text_leakage', "
        "'private_path_leakage', 'secret_like_leakage']"
    ) in markdown


def test_checked_in_expansion_docs_match_seed_summary() -> None:
    items = load_retrieval_eval_jsonl(Path("evals/datasets/retrieval_eval_seed.jsonl"))
    summary = summarize_retrieval_eval_expansion(items)
    report = Path("evals/reports/retrieval_eval_expansion_report.md").read_text(
        encoding="utf-8"
    )
    readme = Path("README.md").read_text(encoding="utf-8")
    dataset_doc = Path("docs/RETRIEVAL_EVAL_DATASET.md").read_text(encoding="utf-8")

    expected_fragments = [
        f"`target_query_count={summary.target_query_count}`",
        f"`current_query_count={summary.current_query_count}`",
        f"`overall_shortfall_count={summary.overall_shortfall_count}`",
        f"`dev_test_shortfall_count={summary.dev_test_shortfall_count}`",
    ]
    assert [fragment for fragment in expected_fragments if fragment not in readme] == []

    table_fragments = [
        f"| target_query_count | {summary.target_query_count} |",
        f"| current_query_count | {summary.current_query_count} |",
        f"| overall_shortfall_count | {summary.overall_shortfall_count} |",
        f"| dev_test_shortfall_count | {summary.dev_test_shortfall_count} |",
        "| authoring_status | `PASS` |",
        "| expansion_readiness_status | `INCOMPLETE` |",
    ]
    assert [fragment for fragment in table_fragments if fragment not in report] == []
    assert [fragment for fragment in table_fragments if fragment not in dataset_doc] == []


def test_retrieval_eval_expansion_pipeline_writes_public_safe_report(
    tmp_path: Path,
) -> None:
    chunks_path = tmp_path / "parent_child_chunks.json"
    dataset_path = tmp_path / "retrieval_eval_seed.jsonl"
    report_path = tmp_path / "retrieval_eval_expansion_report.md"
    child = _child(text="private source text 경복궁 한양")
    item = _eval_item()
    _write_json(
        chunks_path,
        {
            "report_version": "chunking-quality/v1",
            "chunking_run_id": "chunking-test",
            "children": [child.model_dump(mode="json")],
        },
    )
    _write_jsonl(dataset_path, [item.model_dump(mode="json")])

    summary = build_retrieval_eval_expansion_report(
        dataset_path=dataset_path,
        chunks_path=chunks_path,
        report_path=report_path,
    )
    report = report_path.read_text(encoding="utf-8")

    assert summary.current_query_count == 1
    assert "| authoring_status | `FAIL` |" in report
    assert "| expansion_readiness_status | `INCOMPLETE` |" in report
    assert "private source text" not in report
    assert str(chunks_path) not in report
    assert str(dataset_path).replace("\\", "/") not in report
    assert "<public retrieval eval dataset: retrieval_eval_seed.jsonl>" in report
