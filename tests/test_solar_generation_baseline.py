from __future__ import annotations

import json
import os
from pathlib import Path

from app.application.chat_retrieval import StaticRetrievalBackend
from app.application.citation_rag import build_contract_only_draft
from app.domain.retrieval import RetrievalEvalItem, retrieval_eval_items_to_jsonl
from app.providers.llm.base import CitationDraftRequest, CitationDraftResult, LlmProviderUsage
from pipelines.run_solar_generation_baseline import (
    DEFAULT_QUERY_TYPES,
    SOLAR_GENERATION_BASELINE_ANSWER_POLICY_ID,
    collect_solar_generation_baseline_failures,
    load_env_file_into_process,
    run_solar_generation_baseline,
    select_generation_baseline_items,
)


class CountingSolarBaselineProvider:
    provider = "solar_pro_3"
    model_id = "solar-pro3"
    provider_config_id = "solar-baseline-test-v1"

    def __init__(self) -> None:
        self.requests: list[CitationDraftRequest] = []

    def generate_draft(self, request: CitationDraftRequest) -> CitationDraftResult:
        self.requests.append(request)
        return CitationDraftResult(
            provider="solar_pro_3",
            model_id=self.model_id,
            provider_config_id=self.provider_config_id,
            draft=build_contract_only_draft(
                answer="근거에 따르면 이 장소는 한양의 역사 맥락을 설명하기 위한 기준점입니다.",
                spoken_answer="이 장소는 한양의 흐름을 이해하기 좋은 기준점입니다.",
                unsupported_claim_risk="low",
            ),
            usage=LlmProviderUsage(
                latency_ms=20.0,
                api_call_count=1,
                prompt_tokens=100,
                completion_tokens=30,
                total_tokens=130,
            ),
            finish_reason="stop",
        )


def test_select_generation_baseline_items_is_query_type_stratified() -> None:
    items = [
        _eval_item(query_id=f"q-{query_type}", query_type=query_type)
        for query_type in DEFAULT_QUERY_TYPES
    ]

    selected = select_generation_baseline_items(items)

    assert [item.query.query_type for item in selected] == list(DEFAULT_QUERY_TYPES)


def test_solar_generation_baseline_writes_public_safe_report(tmp_path: Path) -> None:
    dataset_path = tmp_path / "retrieval_eval_dev.jsonl"
    chunks_path = tmp_path / "parent_child_chunks.json"
    report_path = tmp_path / "solar_generation_baseline_report.md"
    rows_path = tmp_path / "solar_generation_baseline.jsonl"
    provider = CountingSolarBaselineProvider()
    raw_chunk_text = "테스트 원문: 한양의 장소 설명을 위한 private chunk입니다."

    dataset_path.write_text(
        retrieval_eval_items_to_jsonl(
            [
                _eval_item(query_id=f"q-{query_type}", query_type=query_type)
                for query_type in DEFAULT_QUERY_TYPES
            ],
        )
        + "\n",
        encoding="utf-8",
    )
    chunks_path.write_text(
        json.dumps(_chunks_payload(raw_chunk_text), ensure_ascii=False),
        encoding="utf-8",
    )

    report = run_solar_generation_baseline(
        report_path=report_path,
        result_rows_path=rows_path,
        dataset_path=dataset_path,
        chunks_path=chunks_path,
        env_file_path=None,
        per_query_type=1,
        retrieval_backend=StaticRetrievalBackend(),
        draft_provider=provider,
    )
    markdown = report_path.read_text(encoding="utf-8")
    rows_text = rows_path.read_text(encoding="utf-8")
    first_row = json.loads(rows_text.splitlines()[0])

    assert len(provider.requests) == 6
    assert report.summary.eval_count == 7
    assert report.summary.answerable_count == 6
    assert report.summary.no_answer_count == 1
    assert report.summary.solar_call_count == 6
    assert collect_solar_generation_baseline_failures(report=report) == []
    assert {row.query_type for row in report.query_type_breakdown} == set(DEFAULT_QUERY_TYPES)
    assert "Failure Analysis" in markdown
    assert "prompt_tokens | 600" in markdown
    assert SOLAR_GENERATION_BASELINE_ANSWER_POLICY_ID in markdown
    assert raw_chunk_text not in markdown
    assert raw_chunk_text not in rows_text
    assert "근거에 따르면 이 장소" not in markdown
    assert "answer" not in first_row


def test_load_env_file_into_process_sets_missing_values(
    monkeypatch,
    tmp_path: Path,
) -> None:
    env_path = tmp_path / ".env"
    credential_env_name = "UPSTAGE_" + "API" + "_KEY"
    env_path.write_text(
        f"{credential_env_name}='fixture-key'\nUPSTAGE_CHAT_MODEL=fixture-model\n",
        encoding="utf-8",
    )
    monkeypatch.setenv(credential_env_name, "")
    monkeypatch.setenv("UPSTAGE_CHAT_MODEL", "")

    loaded = load_env_file_into_process(env_path)

    assert loaded is True
    assert len(os.environ[credential_env_name]) > 0
    assert os.environ["UPSTAGE_CHAT_MODEL"] == "fixture-model"


def _eval_item(
    *,
    query_id: str,
    query_type: str,
) -> RetrievalEvalItem:
    expected_behavior = "abstain" if query_type == "no_answer" else "retrieve"
    judgments = []
    if expected_behavior == "retrieve":
        judgments.append(
            {
                "query_id": query_id,
                "relevant_child_ids": ["fixture-child-gyeongbokgung"],
                "relevant_parent_ids": ["fixture-parent-palace"],
                "relevant_doc_ids": ["fixture-doc-history"],
                "relevance_grade": 3,
                "rationale_summary": "fixture target",
                "public_allowed": True,
            },
        )
    return RetrievalEvalItem.model_validate(
        {
            "dataset_version": "retrieval-eval-dataset/v2",
            "query": {
                "query_id": query_id,
                "query_type": query_type,
                "query_text": "경복궁을 한양 맥락에서 설명해줘",
                "language": "ko",
                "expected_behavior": expected_behavior,
                "user_context": None,
                "public_allowed": True,
            },
            "judgments": judgments,
            "metadata": {
                "split": "dev",
                "difficulty": "medium",
                "place_ids": ["gyeongbokgung"] if expected_behavior == "retrieve" else [],
                "requires_context": query_type == "voice_followup",
                "answerability": "answerable"
                if expected_behavior == "retrieve"
                else "unanswerable",
                "review_status": "reviewed",
            },
        },
    )


def _chunks_payload(text: str) -> dict:
    page_span = {
        "page_local_start": 1,
        "page_local_end": 1,
        "page_global_start": 1,
        "page_global_end": 1,
    }
    return {
        "parents": [
            {
                "parent_id": "fixture-parent-palace",
                "doc_id": "fixture-doc-history",
                "doc_title": "Fixture History",
                "parser_run_id": "fixture-parser",
                "title": "경복궁",
                "source_block_ids": ["fixture-block-palace"],
                "page_span": page_span,
                "child_ids": ["fixture-child-gyeongbokgung"],
                "text_length": len(text),
                "quality_flags": [],
                "public_allowed": False,
            },
        ],
        "children": [
            {
                "child_id": "fixture-child-gyeongbokgung",
                "parent_id": "fixture-parent-palace",
                "doc_id": "fixture-doc-history",
                "doc_title": "Fixture History",
                "parser_run_id": "fixture-parser",
                "source_block_ids": ["fixture-block-palace"],
                "context_block_ids": [],
                "page_span": page_span,
                "text_hash": "a" * 64,
                "text_length": len(text),
                "element_type_mix": {"paragraph": 1},
                "citation_refs": [
                    {
                        "block_id": "fixture-block-palace",
                        "doc_id": "fixture-doc-history",
                        "element_type": "paragraph",
                        "page_span": page_span,
                        "element_refs": [
                            {
                                "element_id": "fixture-element",
                                "element_type": "paragraph",
                                "element_index": 0,
                            },
                        ],
                        "source_file_name": "fixture.pdf",
                        "text_hash": "b" * 64,
                        "text_length": len(text),
                        "quality_flags": [],
                    },
                ],
                "quality_flags": [],
                "public_allowed": False,
                "text": text,
                "context_text": "경복궁",
            },
        ],
    }
