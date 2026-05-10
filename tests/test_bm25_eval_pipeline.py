from __future__ import annotations

import json
from pathlib import Path

from pipelines.run_bm25_baseline_eval import (
    build_bm25_baseline_report_markdown,
    collect_public_retrieval_output_failures,
    run_bm25_baseline_eval,
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


def _child_payload(
    *,
    child_id: str,
    parent_id: str,
    doc_id: str,
    text: str,
) -> dict[str, object]:
    return {
        "child_id": child_id,
        "parent_id": parent_id,
        "doc_id": doc_id,
        "doc_title": doc_id,
        "parser_run_id": "parser-run",
        "source_block_ids": [f"block-{child_id}"],
        "context_block_ids": [],
        "page_span": {
            "page_local_start": 1,
            "page_local_end": 1,
            "page_global_start": 1,
            "page_global_end": 1,
        },
        "text_hash": "a" * 64,
        "text_length": len(text),
        "element_type_mix": {"paragraph": 1},
        "citation_refs": [
            {
                "block_id": f"block-{child_id}",
                "doc_id": doc_id,
                "element_type": "paragraph",
                "page_span": {
                    "page_local_start": 1,
                    "page_local_end": 1,
                    "page_global_start": 1,
                    "page_global_end": 1,
                },
                "element_refs": [
                    {
                        "element_id": f"element-{child_id}",
                        "element_type": "paragraph",
                        "element_index": 1,
                    }
                ],
                "source_file_name": f"{doc_id}.pdf",
                "text_hash": "b" * 64,
                "text_length": len(text),
                "quality_flags": [],
            }
        ],
        "quality_flags": [],
        "public_allowed": False,
        "text": text,
        "context_text": None,
    }


def _eval_item_payload(
    *,
    query_id: str,
    query_type: str,
    query_text: str,
    expected_behavior: str,
    child_id: str | None = None,
    parent_id: str | None = None,
    doc_id: str | None = None,
) -> dict[str, object]:
    judgments: list[dict[str, object]] = []
    if expected_behavior == "retrieve":
        judgments.append(
            {
                "query_id": query_id,
                "relevant_child_ids": [child_id],
                "relevant_parent_ids": [parent_id],
                "relevant_doc_ids": [doc_id],
                "relevance_grade": 3,
                "rationale_summary": "test judgment ids only",
                "public_allowed": True,
            }
        )
    answerability = "unanswerable" if expected_behavior == "abstain" else "answerable"
    return {
        "dataset_version": "retrieval-eval-dataset/v2",
        "query": {
            "query_id": query_id,
            "query_type": query_type,
            "query_text": query_text,
            "language": "ko",
            "expected_behavior": expected_behavior,
            "user_context": None,
            "public_allowed": True,
        },
        "judgments": judgments,
        "metadata": {
            "split": "dev",
            "difficulty": "hard" if query_type in {"relationship", "route_context"} else "medium",
            "place_ids": ["gyeongbokgung"] if expected_behavior == "retrieve" else [],
            "requires_context": query_type in {"route_context", "voice_followup"},
            "answerability": answerability,
            "review_status": "draft",
        },
    }


def test_run_bm25_baseline_eval_writes_public_safe_results_and_report(tmp_path: Path) -> None:
    chunks_path = tmp_path / "parent_child_chunks.json"
    dataset_path = tmp_path / "retrieval_eval_seed.jsonl"
    results_path = tmp_path / "results.jsonl"
    report_path = tmp_path / "report.md"
    _write_json(
        chunks_path,
        {
            "report_version": "chunking-quality/v1",
            "chunking_run_id": "chunking-test",
            "children": [
                _child_payload(
                    child_id="child-palace",
                    parent_id="parent-palace",
                    doc_id="doc-joseon",
                    text="private source text 경복궁 한양 천도 정도전",
                ),
                _child_payload(
                    child_id="child-modern",
                    parent_id="parent-modern",
                    doc_id="doc-modern",
                    text="private source text 지하철 카페 막차",
                ),
            ],
        },
    )
    _write_jsonl(
        dataset_path,
        [
            _eval_item_payload(
                query_id="q-one",
                query_type="relationship",
                query_text="경복궁 한양 천도 정도전",
                expected_behavior="retrieve",
                child_id="child-palace",
                parent_id="parent-palace",
                doc_id="doc-joseon",
            ),
            _eval_item_payload(
                query_id="q-no-answer",
                query_type="no_answer",
                query_text="오늘 지하철 막차 시간",
                expected_behavior="abstain",
            ),
        ],
    )

    report = run_bm25_baseline_eval(
        chunks_path=chunks_path,
        dataset_path=dataset_path,
        results_path=results_path,
        report_path=report_path,
        top_k=2,
    )

    assert report.metric_summary.method == "bm25"
    assert report.metric_summary.query_count == 2
    assert report.metric_summary.missing_result_count == 0
    assert report.output_quality.public_raw_text_leakage_count == 0
    assert report.output_quality.private_path_leakage_count == 0
    assert collect_public_retrieval_output_failures(report.output_quality) == []
    assert results_path.exists()
    assert report_path.exists()
    assert "private source text" not in results_path.read_text(encoding="utf-8")
    assert "private source text" not in report_path.read_text(encoding="utf-8")


def test_bm25_report_contains_quantitative_and_qualitative_sections(tmp_path: Path) -> None:
    chunks_path = tmp_path / "parent_child_chunks.json"
    dataset_path = tmp_path / "retrieval_eval_seed.jsonl"
    results_path = tmp_path / "results.jsonl"
    report_path = tmp_path / "report.md"
    _write_json(
        chunks_path,
        {
            "report_version": "chunking-quality/v1",
            "chunking_run_id": "chunking-test",
            "children": [
                _child_payload(
                    child_id="child-palace",
                    parent_id="parent-palace",
                    doc_id="doc-joseon",
                    text="경복궁 한양 천도 정도전",
                )
            ],
        },
    )
    _write_jsonl(
        dataset_path,
        [
            _eval_item_payload(
                query_id="q-one",
                query_type="place_fact",
                query_text="경복궁",
                expected_behavior="retrieve",
                child_id="child-palace",
                parent_id="parent-palace",
                doc_id="doc-joseon",
            )
        ],
    )

    report = run_bm25_baseline_eval(
        chunks_path=chunks_path,
        dataset_path=dataset_path,
        results_path=results_path,
        report_path=report_path,
        top_k=1,
    )
    markdown = build_bm25_baseline_report_markdown(report)

    assert "## 정량 리포트" in markdown
    assert "## Query Type Breakdown" in markdown
    assert "## 정성 리포트" in markdown
    assert "성능 개선 주장이 아니다" in markdown
    assert "`weakest_query_type`: no_answer" not in markdown
    assert "`abstention_scope`" in markdown
