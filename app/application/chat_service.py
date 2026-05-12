from __future__ import annotations

import hashlib
import json
import time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.application.citation_rag import (
    CitationRagAnswerAssembler,
    CitationRagAssemblerConfig,
    build_contract_only_draft,
)
from app.application.evidence_packing import EvidencePack, PackedEvidence
from app.domain.generation import AnswerProviderKind, CitationRagAnswer
from app.domain.retrieval import (
    LanguageCode,
    QueryType,
    RetrievalEvalItem,
)


CHAT_SERVICE_POLICY_ID = "chat-citation-rag-contract-v1"
CHAT_SERVICE_MODEL_ID = "contract-only"
CHAT_API_DEFAULT_PLACE_ID = "seoul-hanyang"

ChatProviderMode = Literal["contract_only", "solar_pro_3"]


class ChatServiceModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ChatCommand(ChatServiceModel):
    request_id: str = Field(min_length=1)
    query: str = Field(min_length=1, max_length=1000)
    language: LanguageCode = "ko"
    query_type: QueryType = "place_story"
    place_context: tuple[str, ...] = Field(default_factory=tuple)
    voice_mode: bool = False
    provider_mode: ChatProviderMode = "contract_only"


class ChatUsage(ChatServiceModel):
    input_chars: int = Field(ge=0)
    evidence_count: int = Field(ge=0)
    estimated_context_chars: int = Field(ge=0)
    provider_call_count: int = Field(ge=0)
    solar_call_count: int = Field(ge=0)
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    estimated_cost: float = Field(default=0.0, ge=0.0)


class ChatServiceResult(ChatServiceModel):
    request_id: str = Field(min_length=1)
    answer: CitationRagAnswer
    usage: ChatUsage
    latency_ms: float = Field(ge=0.0)


class ChatProviderUnavailableError(RuntimeError):
    """Raised when the API contract deliberately blocks a live provider path."""


class ChatContractService:
    def __init__(self, *, provider: AnswerProviderKind = "contract_only") -> None:
        self.provider = provider
        self.assembler = CitationRagAnswerAssembler(
            config=CitationRagAssemblerConfig(
                answer_policy_id=CHAT_SERVICE_POLICY_ID,
                provider=provider,
                model_id=CHAT_SERVICE_MODEL_ID,
            )
        )

    def handle(self, command: ChatCommand) -> ChatServiceResult:
        started = time.perf_counter()
        if command.provider_mode != "contract_only":
            raise ChatProviderUnavailableError(
                "Solar Pro 3 live generation is disabled for the public API contract."
            )
        item = _build_eval_item(command)
        evidence_pack = _build_evidence_pack(command)
        draft = None if command.query_type == "no_answer" else _build_draft(command)
        answer = self.assembler.assemble(
            item=item,
            evidence_pack=evidence_pack,
            draft=draft,
            place_ids=tuple(command.place_context) or tuple(item.metadata.place_ids),
        )
        latency_ms = round((time.perf_counter() - started) * 1000, 6)
        return ChatServiceResult(
            request_id=command.request_id,
            answer=answer,
            usage=ChatUsage(
                input_chars=len(command.query),
                evidence_count=len(evidence_pack.evidence),
                estimated_context_chars=evidence_pack.total_estimated_chars,
                provider_call_count=0,
                solar_call_count=0,
            ),
            latency_ms=latency_ms,
        )


def _build_eval_item(command: ChatCommand) -> RetrievalEvalItem:
    expected_behavior = "abstain" if command.query_type == "no_answer" else "retrieve"
    place_ids = list(command.place_context) or (
        [] if expected_behavior == "abstain" else [CHAT_API_DEFAULT_PLACE_ID]
    )
    judgments = []
    if expected_behavior == "retrieve":
        judgments.append(
            {
                "query_id": command.request_id,
                "relevant_child_ids": [_contract_child_id(command)],
                "relevant_parent_ids": [_contract_parent_id(command)],
                "relevant_doc_ids": [_contract_doc_id(command)],
                "relevance_grade": 3,
                "rationale_summary": "api contract id target",
                "public_allowed": True,
            }
        )
    return RetrievalEvalItem.model_validate(
        {
            "dataset_version": "retrieval-eval-dataset/v2",
            "query": {
                "query_id": command.request_id,
                "query_type": command.query_type,
                "query_text": command.query,
                "language": command.language,
                "expected_behavior": expected_behavior,
                "public_allowed": True,
            },
            "judgments": judgments,
            "metadata": {
                "split": "dev",
                "difficulty": "medium",
                "place_ids": place_ids,
                "requires_context": command.query_type == "voice_followup",
                "answerability": (
                    "unanswerable" if expected_behavior == "abstain" else "answerable"
                ),
                "review_status": "reviewed",
            },
        }
    )


def _build_evidence_pack(command: ChatCommand) -> EvidencePack:
    if command.query_type == "no_answer":
        return EvidencePack(
            query_id=command.request_id,
            query_type=command.query_type,
            policy_id="P0_rank_order",
            context_budget_chars=4200,
            total_estimated_chars=0,
            evidence=(),
            target_child_covered=False,
            target_parent_covered=False,
            target_doc_covered=False,
            evidence_order_relevance_proxy=0.0,
        )
    evidence = PackedEvidence(
        pack_rank=1,
        source_rank=1,
        retrieval_doc_id=_contract_child_id(command),
        child_id=_contract_child_id(command),
        parent_id=_contract_parent_id(command),
        doc_id=_contract_doc_id(command),
        score=1.0,
        estimated_chars=320,
        source_block_ids=(_contract_block_id(command),),
        citation_block_ids=(_contract_block_id(command),),
        citation_recoverable=True,
        packing_reason="api_contract_smoke",
    )
    return EvidencePack(
        query_id=command.request_id,
        query_type=command.query_type,
        policy_id="P0_rank_order",
        context_budget_chars=4200,
        total_estimated_chars=evidence.estimated_chars,
        evidence=(evidence,),
        target_child_covered=True,
        target_parent_covered=True,
        target_doc_covered=True,
        evidence_order_relevance_proxy=1.0,
    )


def _build_draft(command: ChatCommand):
    if command.language == "en":
        return build_contract_only_draft(
            answer=(
                "This is a chat API contract response. The current run validates "
                "answer, spoken_answer, evidence IDs, and recoverable citations "
                "before live retrieval and Solar Pro 3 generation are enabled."
            ),
            spoken_answer=(
                "This is a contract check response. Live historical guidance will "
                "be connected after retrieval and Solar Pro 3 validation."
            ),
            unsupported_claim_risk="low",
        )
    return build_contract_only_draft(
        answer=(
            "이 응답은 chat API 계약 검증용입니다. 실제 검색과 Solar Pro 3 생성 연결 "
            "전에는 answer, spoken_answer, evidence ID, 복구 가능한 citation 구조만 "
            "검증합니다."
        ),
        spoken_answer=(
            "현재는 챗 API 계약 검증 응답입니다. 실제 역사 설명은 검색과 "
            "Solar Pro 3 검증 뒤 연결합니다."
        ),
        unsupported_claim_risk="low",
    )


def _contract_child_id(command: ChatCommand) -> str:
    return f"api-contract-child-{_command_digest(command)}"


def _contract_parent_id(command: ChatCommand) -> str:
    return f"api-contract-parent-{_command_digest(command)}"


def _contract_doc_id(command: ChatCommand) -> str:
    return f"api-contract-doc-{_command_digest(command)}"


def _contract_block_id(command: ChatCommand) -> str:
    return f"api-contract-block-{_command_digest(command)}"


def _command_digest(command: ChatCommand) -> str:
    payload = {
        "request_id": command.request_id,
        "query_type": command.query_type,
        "place_context": command.place_context,
    }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:8]
