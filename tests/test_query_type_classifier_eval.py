from __future__ import annotations

from pathlib import Path

from app.domain.retrieval import QueryType, RetrievalEvalItem
from pipelines.run_query_type_classifier_eval import (
    build_query_type_classifier_eval_report,
    collect_query_type_classifier_eval_failures,
)


def test_query_type_classifier_eval_report_gate_passes(tmp_path: Path) -> None:
    dataset_path = tmp_path / "retrieval_eval_dev.jsonl"
    result_path = tmp_path / "query_type_classifier_eval_rows.jsonl"
    report_path = tmp_path / "query_type_classifier_eval_report.md"
    dataset_path.write_text(
        "\n".join(
            item.model_dump_json()
            for item in (
                _eval_item(
                    query_id="q1",
                    query_type="place_fact",
                    query_text="경복궁이 조선 초 새 수도의 상징으로 세워진 배경을 설명할 근거를 찾아줘",
                ),
                _eval_item(
                    query_id="q2",
                    query_type="place_story",
                    query_text="광화문 광장에서 세종 이야기를 관광객에게 짧고 흥미롭게 들려줄 근거를 찾아줘",
                ),
                _eval_item(
                    query_id="q3",
                    query_type="relationship",
                    query_text="정도전과 이방원의 갈등이 경복궁과 창덕궁 선택에 어떻게 남았는지 찾아줘",
                ),
                _eval_item(
                    query_id="q4",
                    query_type="overview",
                    query_text="조선 초기 궁궐과 종묘가 왕권을 보여주는 방식을 요약할 근거를 찾아줘",
                ),
                _eval_item(
                    query_id="q5",
                    query_type="route_context",
                    query_text="광화문에서 경복궁을 지나 종묘로 가는 동선에서 설명할 근거를 찾아줘",
                    requires_context=True,
                ),
                _eval_item(
                    query_id="q6",
                    query_type="voice_followup",
                    query_text="그 사람이 왜 그 궁을 피했어?",
                    requires_context=True,
                ),
                _eval_item(
                    query_id="q7",
                    query_type="no_answer",
                    query_text="오늘 경복궁 야간개장 입장권이 몇 장 남았어?",
                    answerable=False,
                ),
            )
        )
        + "\n",
        encoding="utf-8",
    )

    report = build_query_type_classifier_eval_report(
        dataset_path=dataset_path,
        result_path=result_path,
        report_path=report_path,
    )

    assert collect_query_type_classifier_eval_failures(report) == []
    assert report.summary.query_count == 7
    assert report.summary.query_type_count == 7
    assert report.summary.accuracy == 1.0
    assert report.summary.macro_f1 == 1.0
    assert report.summary.route_policy_accuracy == 1.0
    assert report.summary.live_solar_call_count == 0
    assert report.output_quality.public_raw_text_leakage_count == 0
    assert report.output_quality.private_path_leakage_count == 0


def test_query_type_classifier_eval_writes_public_safe_artifacts(tmp_path: Path) -> None:
    dataset_path = tmp_path / "retrieval_eval_dev.jsonl"
    result_path = tmp_path / "query_type_classifier_eval_rows.jsonl"
    report_path = tmp_path / "query_type_classifier_eval_report.md"
    dataset_path.write_text(
        _eval_item(
            query_id="q1",
            query_type="place_fact",
            query_text="경복궁이 세워진 배경을 설명할 근거를 찾아줘",
        ).model_dump_json()
        + "\n",
        encoding="utf-8",
    )

    try:
        build_query_type_classifier_eval_report(
            dataset_path=dataset_path,
            result_path=result_path,
            report_path=report_path,
        )
    except ValueError as exc:
        assert "missing_query_type_coverage" in str(exc)

    rows = result_path.read_text(encoding="utf-8")
    report_text = report_path.read_text(encoding="utf-8") if report_path.exists() else ""

    assert "경복궁이 세워진 배경" not in rows
    assert "query_id" in rows
    assert "raw query" in report_text or not report_text


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
                "place_ids": ["gyeongbokgung"],
                "requires_context": requires_context,
                "answerability": answerability,
                "review_status": "reviewed",
            },
        }
    )
