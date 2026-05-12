from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.application.chat_retrieval import StaticRetrievalBackend
from app.application.citation_rag import build_contract_only_draft
from app.domain.retrieval import RetrievalEvalItem, retrieval_eval_items_to_jsonl
from app.providers.llm.base import (
    CitationDraftRequest,
    CitationDraftResult,
    LlmProviderConfigError,
    LlmProviderUsage,
)
from pipelines.run_solar_live_generation_smoke import (
    build_evidence_context,
    collect_solar_live_generation_smoke_failures,
    run_solar_live_generation_smoke,
)


class CountingSolarDraftProvider:
    provider = "solar_pro_3"
    model_id = "solar-pro3"
    provider_config_id = "solar-live-test-v1"

    def __init__(self) -> None:
        self.requests: list[CitationDraftRequest] = []

    def generate_draft(self, request: CitationDraftRequest) -> CitationDraftResult:
        self.requests.append(request)
        return CitationDraftResult(
            provider="solar_pro_3",
            model_id=self.model_id,
            provider_config_id=self.provider_config_id,
            draft=build_contract_only_draft(
                answer="경복궁은 조선의 중심 궁궐이라는 근거를 바탕으로 설명할 수 있습니다.",
                spoken_answer="경복궁은 조선의 중심 궁궐이라는 점을 현장에서 짚어볼 수 있습니다.",
                unsupported_claim_risk="low",
            ),
            usage=LlmProviderUsage(
                latency_ms=15.0,
                api_call_count=1,
                prompt_tokens=120,
                completion_tokens=40,
                total_tokens=160,
            ),
            finish_reason="stop",
        )


def test_solar_live_generation_smoke_uses_provider_and_writes_public_safe_report(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "retrieval_eval_dev.jsonl"
    chunks_path = tmp_path / "parent_child_chunks.json"
    report_path = tmp_path / "solar_live_generation_smoke_report.md"
    rows_path = tmp_path / "solar_live.jsonl"
    provider = CountingSolarDraftProvider()
    raw_chunk_text = "테스트 원문: 경복궁은 조선의 중심 궁궐이라는 설명을 담은 private chunk입니다."

    dataset_path.write_text(
        retrieval_eval_items_to_jsonl(
            [
                _eval_item(
                    query_id="q-live-answer",
                    query_type="place_story",
                    expected_behavior="retrieve",
                ),
                _eval_item(
                    query_id="q-live-no-answer",
                    query_type="no_answer",
                    expected_behavior="abstain",
                ),
            ],
        )
        + "\n",
        encoding="utf-8",
    )
    chunks_path.write_text(
        json.dumps(_chunks_payload(raw_chunk_text), ensure_ascii=False),
        encoding="utf-8",
    )

    report = run_solar_live_generation_smoke(
        report_path=report_path,
        result_rows_path=rows_path,
        dataset_path=dataset_path,
        chunks_path=chunks_path,
        answerable_limit=1,
        no_answer_limit=1,
        retrieval_backend=StaticRetrievalBackend(),
        draft_provider=provider,
    )
    markdown = report_path.read_text(encoding="utf-8")
    rows_text = rows_path.read_text(encoding="utf-8")

    assert len(provider.requests) == 1
    assert raw_chunk_text in provider.requests[0].evidence_context
    assert collect_solar_live_generation_smoke_failures(report) == []
    assert report.summary.eval_count == 2
    assert report.summary.solar_call_count == 1
    assert report.summary.correct_with_evidence_rate == 1.0
    assert report.summary.abstention_accuracy == 1.0
    assert report.output_quality.public_raw_text_leakage_count == 0
    assert "prompt_tokens | 120" in markdown
    assert raw_chunk_text not in markdown
    assert raw_chunk_text not in rows_text
    assert "경복궁은 조선의 중심 궁궐이라는 근거" not in markdown
    assert "answer" not in json.loads(rows_text.splitlines()[0])


def test_solar_live_generation_smoke_requires_api_key_when_provider_not_injected(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("UPSTAGE_API_KEY", raising=False)

    with pytest.raises(LlmProviderConfigError, match="UPSTAGE_API_KEY"):
        run_solar_live_generation_smoke(
            report_path=tmp_path / "report.md",
            result_rows_path=tmp_path / "rows.jsonl",
            dataset_path=tmp_path / "missing.jsonl",
            chunks_path=tmp_path / "missing_chunks.json",
        )


def test_build_evidence_context_rejects_missing_private_text() -> None:
    retrieval = StaticRetrievalBackend().retrieve(
        command=_command_like(),
        item=_eval_item(
            query_id="q-live-answer",
            query_type="place_story",
            expected_behavior="retrieve",
        ),
    )

    with pytest.raises(ValueError, match="private text"):
        build_evidence_context(retrieval=retrieval, child_chunks_by_id={})


def _command_like():
    class Command:
        request_id = "q-live-answer"
        query = "경복궁을 설명해줘"
        language = "ko"
        query_type = "place_story"
        place_context = ("gyeongbokgung",)
        voice_mode = False
        user_context = None

    return Command()


def _eval_item(
    *,
    query_id: str,
    query_type: str,
    expected_behavior: str,
) -> RetrievalEvalItem:
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
                "requires_context": False,
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
