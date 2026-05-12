from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.application.chat_retrieval import StaticRetrievalBackend
from app.application.citation_rag import build_contract_only_draft
from app.domain.generation import CitationRagDraft, CitationRagDraftV2
from app.domain.retrieval import FORBIDDEN_PUBLIC_EVAL_FIELDS, RetrievalEvalItem
from app.providers.llm.base import (
    CitationDraftRequest,
    CitationDraftResult,
    LlmProviderUsage,
)
from pipelines.run_solar_generation_contract_v2_live_comparison import (
    SOLAR_GENERATION_CONTRACT_V2_LIVE_COMPARISON_REPORT_VERSION,
    collect_solar_generation_contract_v2_live_comparison_failures,
    run_solar_generation_contract_v2_live_comparison,
)


@dataclass
class CountingDraftProvider:
    draft: CitationRagDraft
    provider_config_id: str
    provider: str = "solar_pro_3"
    model_id: str = "solar-pro3"

    def __post_init__(self) -> None:
        self.requests: list[CitationDraftRequest] = []

    def generate_draft(self, request: CitationDraftRequest) -> CitationDraftResult:
        self.requests.append(request)
        return CitationDraftResult(
            provider=self.provider,
            model_id=self.model_id,
            provider_config_id=self.provider_config_id,
            draft=self.draft,
            usage=LlmProviderUsage(
                latency_ms=10.0,
                api_call_count=1,
                prompt_tokens=100,
                completion_tokens=30,
                total_tokens=130,
            ),
            finish_reason="stop",
        )


def test_solar_generation_contract_v2_live_comparison_is_public_safe(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "retrieval_eval_dev.jsonl"
    chunks_path = tmp_path / "parent_child_chunks.json"
    report_path = tmp_path / "solar_generation_contract_v2_live_comparison_report.md"
    rows_path = tmp_path / "solar_generation_contract_v2_live_results.jsonl"
    raw_chunk_text = "테스트 원문: 경복궁은 조선의 중심 궁궐이라는 private chunk입니다."
    baseline_provider = CountingDraftProvider(
        draft=build_contract_only_draft(
            answer="경복궁은 조선의 중심 궁궐이라는 근거를 바탕으로 설명할 수 있습니다.",
            spoken_answer="경복궁은 조선의 중심 궁궐이라는 점을 현장에서 짚어볼 수 있습니다.",
            unsupported_claim_risk="low",
        ),
        provider_config_id="solar-live-v1-test",
    )
    candidate_provider = CountingDraftProvider(
        draft=CitationRagDraftV2(
            answer="경복궁은 조선의 중심 궁궐이라는 근거를 바탕으로 설명할 수 있습니다.",
            spoken_answer="경복궁은 조선의 중심 궁궐이라는 점을 현장에서 짚어볼 수 있습니다.",
            used_evidence_pack_ranks=(1,),
            coverage_intent="focused",
            unsupported_claim_risk="low",
        ),
        provider_config_id="solar-live-v2-test",
    )

    dataset_path.write_text(
        "\n".join(
            [
                _eval_item_jsonl(
                    query_id="q-live-place-story",
                    query_type="place_story",
                    expected_behavior="retrieve",
                ),
                _eval_item_jsonl(
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

    report = run_solar_generation_contract_v2_live_comparison(
        report_path=report_path,
        result_rows_path=rows_path,
        dataset_path=dataset_path,
        chunks_path=chunks_path,
        per_query_type=1,
        query_types=("place_story", "no_answer"),
        retrieval_backend=StaticRetrievalBackend(),
        baseline_draft_provider=baseline_provider,
        candidate_draft_provider=candidate_provider,
    )
    markdown = report_path.read_text(encoding="utf-8")
    rows = [json.loads(line) for line in rows_path.read_text(encoding="utf-8").splitlines()]

    assert report.report_version == SOLAR_GENERATION_CONTRACT_V2_LIVE_COMPARISON_REPORT_VERSION
    assert len(baseline_provider.requests) == 1
    assert len(candidate_provider.requests) == 1
    assert raw_chunk_text in baseline_provider.requests[0].evidence_context
    assert raw_chunk_text in candidate_provider.requests[0].evidence_context
    assert report.baseline_report.summary.eval_count == 2
    assert report.candidate_report.summary.eval_count == 2
    assert report.baseline_report.summary.solar_call_count == 1
    assert report.candidate_report.summary.solar_call_count == 1
    assert collect_solar_generation_contract_v2_live_comparison_failures(report) == []
    assert report.output_quality.public_raw_text_leakage_count == 0
    assert report.output_quality.private_path_leakage_count == 0
    assert report.output_quality.secret_like_leakage_count == 0
    assert "Solar Pro 3 실제 호출" in markdown
    assert raw_chunk_text not in markdown
    assert "경복궁은 조선의 중심 궁궐이라는 근거" not in markdown
    assert all(FORBIDDEN_PUBLIC_EVAL_FIELDS.isdisjoint(row.keys()) for row in rows)


def _eval_item_jsonl(
    *,
    query_id: str,
    query_type: str,
    expected_behavior: str,
) -> str:
    return _eval_item(
        query_id=query_id,
        query_type=query_type,
        expected_behavior=expected_behavior,
    ).model_dump_json()


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
