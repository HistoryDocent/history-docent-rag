from __future__ import annotations

from pathlib import Path

from app.domain.retrieval import QueryType, RetrievalEvalItem
from pipelines.run_query_type_classifier_failure_analysis import (
    build_query_type_classifier_failure_analysis_report,
    collect_query_type_classifier_failure_analysis_failures,
)


def test_query_type_classifier_failure_analysis_report_gate_passes(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "retrieval_eval_dev.jsonl"
    result_path = tmp_path / "query_type_classifier_failure_rows.jsonl"
    report_path = tmp_path / "query_type_classifier_failure_report.md"
    dataset_path.write_text(
        "\n".join(
            item.model_dump_json()
            for item in (
                _eval_item(
                    query_id="q1",
                    query_type="overview",
                    query_text="경복궁과 종묘가 어떻게 연결되는지 요약할 근거를 찾아줘",
                ),
                _eval_item(
                    query_id="q2",
                    query_type="no_answer",
                    query_text="오늘 경복궁 야간개장 입장권이 몇 장 남았어?",
                    answerable=False,
                ),
            )
        )
        + "\n",
        encoding="utf-8",
    )

    report = build_query_type_classifier_failure_analysis_report(
        dataset_path=dataset_path,
        result_path=result_path,
        report_path=report_path,
    )

    assert collect_query_type_classifier_failure_analysis_failures(report) == []
    assert report.summary.query_count == 2
    assert report.summary.failure_count == 1
    assert report.summary.route_risk_failure_count == 1
    assert report.summary.false_hybrid_route_count == 1
    assert report.summary.false_abstain_count == 0
    assert report.summary.live_solar_call_count == 0
    assert report.output_quality.public_raw_text_leakage_count == 0
    assert report.output_quality.private_path_leakage_count == 0


def test_query_type_classifier_failure_analysis_writes_public_safe_rows(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "retrieval_eval_dev.jsonl"
    result_path = tmp_path / "query_type_classifier_failure_rows.jsonl"
    report_path = tmp_path / "query_type_classifier_failure_report.md"
    private_query_text = "경복궁과 종묘가 어떻게 연결되는지 요약할 근거를 찾아줘"
    dataset_path.write_text(
        _eval_item(
            query_id="q1",
            query_type="overview",
            query_text=private_query_text,
        ).model_dump_json()
        + "\n",
        encoding="utf-8",
    )

    report = build_query_type_classifier_failure_analysis_report(
        dataset_path=dataset_path,
        result_path=result_path,
        report_path=report_path,
    )
    result_text = result_path.read_text(encoding="utf-8")
    report_text = report_path.read_text(encoding="utf-8")

    assert report.summary.failure_count == 1
    assert private_query_text not in result_text
    assert private_query_text not in report_text
    assert "false_hybrid_route" in result_text
    assert "raw query" in report_text


def _eval_item(
    *,
    query_id: str,
    query_type: QueryType,
    query_text: str,
    requires_context: bool = False,
    answerable: bool = True,
) -> RetrievalEvalItem:
    if answerable:
        judgments = [
            {
                "query_id": query_id,
                "relevant_child_ids": ["child-1"],
                "relevant_parent_ids": ["parent-1"],
                "relevant_doc_ids": ["doc-1"],
                "relevance_grade": 2,
                "rationale_summary": "public-safe fixture target id",
                "public_allowed": True,
            }
        ]
        expected_behavior = "retrieve"
        answerability = "answerable"
    else:
        judgments = []
        expected_behavior = "abstain"
        answerability = "unanswerable"
    return RetrievalEvalItem.model_validate(
        {
            "query": {
                "query_id": query_id,
                "query_type": query_type,
                "query_text": query_text,
                "language": "ko",
                "expected_behavior": expected_behavior,
                "user_context": "public-safe fixture context",
                "public_allowed": True,
            },
            "judgments": judgments,
            "metadata": {
                "split": "dev",
                "difficulty": "easy",
                "place_ids": ["gyeongbokgung", "jongmyo"],
                "requires_context": requires_context,
                "answerability": answerability,
                "review_status": "reviewed",
            },
        }
    )
