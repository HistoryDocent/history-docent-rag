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
from app.application.chat_retrieval import (
    ChatRetrievalBackend,
    ChatRetrievalMode,
    ChatRetrievalOutcome,
    PrivateArtifactRetrievalBackend,
)
from app.application.query_type_router import QueryTypeRouter
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
    user_context: str | None = Field(default=None, max_length=600)
    retrieval_mode: ChatRetrievalMode = "contract_only"
    provider_mode: ChatProviderMode = "contract_only"


class ChatUsage(ChatServiceModel):
    input_chars: int = Field(ge=0)
    evidence_count: int = Field(ge=0)
    estimated_context_chars: int = Field(ge=0)
    retrieval_mode: ChatRetrievalMode = "contract_only"
    retrieval_method: str | None = None
    route_policy_id: str | None = None
    route_candidate_id: str | None = None
    route_claim_boundary: str | None = None
    retrieval_candidate_count: int = Field(default=0, ge=0)
    retrieval_latency_ms: float = Field(default=0.0, ge=0.0)
    query_rewrite_changed: bool = False
    query_rewrite_latency_ms: float = Field(default=0.0, ge=0.0)
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
    def __init__(
        self,
        *,
        provider: AnswerProviderKind = "contract_only",
        retrieval_backend: ChatRetrievalBackend | None = None,
    ) -> None:
        self.provider = provider
        self.retrieval_backend = retrieval_backend or PrivateArtifactRetrievalBackend()
        self.router = QueryTypeRouter()
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
        route_decision = self.router.route(command.query_type)
        if command.retrieval_mode == "retrieval_backed":
            retrieval = self.retrieval_backend.retrieve(command=command, item=item)
            evidence_pack = retrieval.evidence_pack
            draft = (
                None
                if not evidence_pack.evidence
                else _build_retrieval_backed_draft(command, retrieval)
            )
            place_ids = retrieval.place_ids or tuple(item.metadata.place_ids)
        else:
            retrieval = None
            evidence_pack = _build_contract_evidence_pack(command)
            draft = None if command.query_type == "no_answer" else _build_contract_draft(command)
            place_ids = tuple(command.place_context) or tuple(item.metadata.place_ids)
        answer = self.assembler.assemble(
            item=item,
            evidence_pack=evidence_pack,
            draft=draft,
            place_ids=place_ids,
        )
        latency_ms = round((time.perf_counter() - started) * 1000, 6)
        return ChatServiceResult(
            request_id=command.request_id,
            answer=answer,
            usage=_build_usage(
                command=command,
                evidence_pack=evidence_pack,
                retrieval=retrieval,
                route_policy_id=(
                    retrieval.route_policy_id if retrieval is not None else route_decision.route_policy_id
                ),
                route_candidate_id=(
                    retrieval.route_candidate_id
                    if retrieval is not None
                    else route_decision.selected_candidate_id
                ),
                route_claim_boundary=(
                    retrieval.route_claim_boundary
                    if retrieval is not None
                    else route_decision.claim_boundary
                ),
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
                "user_context": command.user_context,
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


def _build_contract_evidence_pack(command: ChatCommand) -> EvidencePack:
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


def _build_contract_draft(command: ChatCommand):
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


def _build_retrieval_backed_draft(
    command: ChatCommand,
    retrieval: ChatRetrievalOutcome,
):
    evidence_count = len(retrieval.evidence_pack.evidence)
    if command.language == "en":
        return build_contract_only_draft(
            answer=(
                f"The API retrieved {evidence_count} citation-ready evidence item. "
                "This response validates retrieval, evidence packing, and citation "
                "assembly before live Solar Pro 3 generation is enabled."
            ),
            spoken_answer=(
                "I found citation-ready evidence. Live historical narration will be "
                "enabled after Solar Pro 3 validation."
            ),
            unsupported_claim_risk="low",
        )
    return build_contract_only_draft(
        answer=(
            f"검색 결과에서 citation으로 복구 가능한 근거 {evidence_count}개를 찾았고, "
            "evidence packing과 citation answer 조립까지 연결했습니다. 현재 문장은 "
            "Solar Pro 3 live 생성 전 검증용입니다."
        ),
        spoken_answer=(
            "근거 검색과 citation 연결까지 확인했습니다. 실제 역사 해설 문장은 "
            "Solar Pro 3 검증 뒤 연결합니다."
        ),
        unsupported_claim_risk="low",
    )


def _build_usage(
    *,
    command: ChatCommand,
    evidence_pack: EvidencePack,
    retrieval: ChatRetrievalOutcome | None,
    route_policy_id: str,
    route_candidate_id: str,
    route_claim_boundary: str,
) -> ChatUsage:
    return ChatUsage(
        input_chars=len(command.query),
        evidence_count=len(evidence_pack.evidence),
        estimated_context_chars=evidence_pack.total_estimated_chars,
        retrieval_mode=command.retrieval_mode,
        retrieval_method=retrieval.retrieval_method if retrieval is not None else "contract_fixture",
        route_policy_id=route_policy_id,
        route_candidate_id=route_candidate_id,
        route_claim_boundary=route_claim_boundary,
        retrieval_candidate_count=(
            retrieval.retrieval_candidate_count if retrieval is not None else 0
        ),
        retrieval_latency_ms=retrieval.retrieval_latency_ms if retrieval is not None else 0.0,
        query_rewrite_changed=(
            retrieval.query_rewrite_changed if retrieval is not None else False
        ),
        query_rewrite_latency_ms=(
            retrieval.query_rewrite_latency_ms if retrieval is not None else 0.0
        ),
        provider_call_count=0,
        solar_call_count=0,
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
