from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipelines.run_evidence_packing_experiment import run_evidence_packing_experiment


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )


def _chunks_payload() -> dict[str, object]:
    return {
        "parents": [
            {
                "parent_id": "parent-palace",
                "child_ids": ["child-neighbor", "child-target"],
            }
        ],
        "children": [
            {
                "child_id": "child-neighbor",
                "parent_id": "parent-palace",
                "doc_id": "doc-palace",
                "text_length": 400,
                "source_block_ids": ["block-neighbor"],
                "citation_refs": [{"block_id": "block-neighbor"}],
                "quality_flags": [],
            },
            {
                "child_id": "child-target",
                "parent_id": "parent-palace",
                "doc_id": "doc-palace",
                "text_length": 420,
                "source_block_ids": ["block-target"],
                "citation_refs": [{"block_id": "block-target"}],
                "quality_flags": [],
            },
        ],
    }


def _eval_item_payload(
    *,
    split: str = "dev",
    review_status: str = "reviewed",
) -> dict[str, object]:
    return {
        "dataset_version": "retrieval-eval-dataset/v2",
        "query": {
            "query_id": "q-one",
            "query_type": "place_story",
            "query_text": "경복궁 이야기를 설명해줘",
            "language": "ko",
            "expected_behavior": "retrieve",
            "public_allowed": True,
        },
        "judgments": [
            {
                "query_id": "q-one",
                "relevant_child_ids": ["child-target"],
                "relevant_parent_ids": ["parent-palace"],
                "relevant_doc_ids": ["doc-palace"],
                "relevance_grade": 3,
                "rationale_summary": "id only",
                "public_allowed": True,
            }
        ],
        "metadata": {
            "split": split,
            "difficulty": "medium",
            "place_ids": ["gyeongbokgung"],
            "requires_context": False,
            "answerability": "answerable",
            "review_status": review_status,
        },
    }


def _retrieval_result_rows() -> list[dict[str, object]]:
    return [
        {
            "run_id": "retrieval-test",
            "method": "dense",
            "query_id": "q-one",
            "query_type": "place_story",
            "latency_ms": 1.0,
            "rank": 1,
            "retrieval_doc_id": "child-neighbor",
            "child_id": "child-neighbor",
            "parent_id": "parent-palace",
            "doc_id": "doc-palace",
            "score": 1.0,
        }
    ]


def test_run_evidence_packing_experiment_writes_report_and_rows(tmp_path: Path) -> None:
    chunks_path = tmp_path / "parent_child_chunks.json"
    dataset_path = tmp_path / "retrieval_eval_dev.jsonl"
    retrieval_results_path = tmp_path / "retrieval_results.jsonl"
    packing_rows_path = tmp_path / "evidence_packing_results.jsonl"
    report_path = tmp_path / "evidence_packing_report.md"
    _write_json(chunks_path, _chunks_payload())
    _write_jsonl(dataset_path, [_eval_item_payload()])
    _write_jsonl(retrieval_results_path, _retrieval_result_rows())

    report = run_evidence_packing_experiment(
        chunks_path=chunks_path,
        dataset_path=dataset_path,
        retrieval_results_path=retrieval_results_path,
        packing_rows_path=packing_rows_path,
        report_path=report_path,
        policies=["P0_rank_order", "P1_parent_expansion"],
    )
    markdown = report_path.read_text(encoding="utf-8")
    rows_text = packing_rows_path.read_text(encoding="utf-8")

    assert report.report_version == "evidence-packing-report/v1"
    assert [summary.policy_id for summary in report.policy_summaries] == [
        "P0_rank_order",
        "P1_parent_expansion",
    ]
    assert report.policy_summaries[1].target_child_covered_rate == 1.0
    assert report.output_quality.public_raw_text_leakage_count == 0
    assert report.output_quality.private_path_leakage_count == 0
    assert "## 정량 리포트" in markdown
    assert "## 정성 리포트" in markdown
    assert "private source text" not in markdown
    assert "private source text" not in rows_text


def test_evidence_packing_experiment_rejects_locked_test_split(
    tmp_path: Path,
) -> None:
    chunks_path = tmp_path / "parent_child_chunks.json"
    dataset_path = tmp_path / "retrieval_eval_test.jsonl"
    retrieval_results_path = tmp_path / "retrieval_results.jsonl"
    _write_json(chunks_path, _chunks_payload())
    _write_jsonl(
        dataset_path,
        [_eval_item_payload(split="test", review_status="locked")],
    )
    _write_jsonl(retrieval_results_path, _retrieval_result_rows())

    with pytest.raises(ValueError, match="locked/test split"):
        run_evidence_packing_experiment(
            chunks_path=chunks_path,
            dataset_path=dataset_path,
            retrieval_results_path=retrieval_results_path,
            packing_rows_path=tmp_path / "packing_rows.jsonl",
            report_path=tmp_path / "report.md",
        )
