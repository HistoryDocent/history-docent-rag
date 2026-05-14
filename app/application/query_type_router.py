from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.retrieval import QueryType, REQUIRED_QUERY_TYPES


QUERY_TYPE_ROUTER_POLICY_ID = "query_type_router_v1"
DEFAULT_ROUTE_POLICY_ID = "default_dense_voice_rewrite_v1"
RELATIONSHIP_ROUTE_POLICY_ID = "relationship_hybrid_weighted_e5_v1"
NO_ANSWER_ROUTE_POLICY_ID = "abstain_first_v1"
DEFAULT_RETRIEVAL_CANDIDATE_ID = "dense_multilingual_e5_small_voice_rewrite"
RELATIONSHIP_RETRIEVAL_CANDIDATE_ID = "hybrid_weighted_e5_small_alpha_0_5"
NO_ANSWER_CANDIDATE_ID = "abstain_contract"
DEFAULT_PACKING_POLICY_ID = "P0_rank_order"
VOICE_REWRITE_STRATEGY_ID = "voice-followup-deterministic-v1"

RouteExecutionMode = Literal["abstain", "dense", "hybrid_weighted"]
RouteDecision = Literal[
    "keep_abstain_first",
    "keep_default",
    "adopt_route_candidate",
]
RouteClaimBoundary = Literal["dev-label boundary", "dev-only", "dev-input-only"]


class QueryTypeRouterModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class QueryTypeRouteDecision(QueryTypeRouterModel):
    router_policy_id: str = QUERY_TYPE_ROUTER_POLICY_ID
    query_type: QueryType
    route_policy_id: str = Field(min_length=1)
    selected_candidate_id: str = Field(min_length=1)
    retrieval_method_label: str = Field(min_length=1)
    execution_mode: RouteExecutionMode
    packing_policy_id: str = DEFAULT_PACKING_POLICY_ID
    should_retrieve: bool
    query_rewrite_strategy_id: str | None = None
    decision: RouteDecision
    claim_boundary: RouteClaimBoundary
    rejected_candidate_ids: tuple[str, ...] = Field(default_factory=tuple)
    decision_reason_tag: str = Field(min_length=1)
    production_default: bool = False


class QueryTypeRouter:
    def route(self, query_type: QueryType) -> QueryTypeRouteDecision:
        if query_type == "no_answer":
            return QueryTypeRouteDecision(
                query_type=query_type,
                route_policy_id=NO_ANSWER_ROUTE_POLICY_ID,
                selected_candidate_id=NO_ANSWER_CANDIDATE_ID,
                retrieval_method_label=NO_ANSWER_ROUTE_POLICY_ID,
                execution_mode="abstain",
                should_retrieve=False,
                query_rewrite_strategy_id=None,
                decision="keep_abstain_first",
                claim_boundary="dev-label boundary",
                decision_reason_tag="no_answer_abstain_contract_first",
                production_default=True,
            )
        if query_type == "relationship":
            return QueryTypeRouteDecision(
                query_type=query_type,
                route_policy_id=RELATIONSHIP_ROUTE_POLICY_ID,
                selected_candidate_id=RELATIONSHIP_RETRIEVAL_CANDIDATE_ID,
                retrieval_method_label=RELATIONSHIP_RETRIEVAL_CANDIDATE_ID,
                execution_mode="hybrid_weighted",
                should_retrieve=True,
                query_rewrite_strategy_id=None,
                decision="adopt_route_candidate",
                claim_boundary="dev-input-only",
                rejected_candidate_ids=(
                    "graphrag_lite_entity_path_v1",
                    "graphrag_lite_community_hint_v1",
                ),
                decision_reason_tag="relationship_hybrid_topk_rank_gain",
                production_default=False,
            )
        rejected_candidates: tuple[str, ...] = ()
        if query_type == "place_story":
            rejected_candidates = ("place_story_guarded_boost_v1",)
        return QueryTypeRouteDecision(
            query_type=query_type,
            route_policy_id=DEFAULT_ROUTE_POLICY_ID,
            selected_candidate_id=DEFAULT_RETRIEVAL_CANDIDATE_ID,
            retrieval_method_label=DEFAULT_RETRIEVAL_CANDIDATE_ID,
            execution_mode="dense",
            should_retrieve=True,
            query_rewrite_strategy_id=VOICE_REWRITE_STRATEGY_ID,
            decision="keep_default",
            claim_boundary="dev-only",
            rejected_candidate_ids=rejected_candidates,
            decision_reason_tag="default_dense_voice_rewrite_retained",
            production_default=True,
        )

    def route_all(self) -> tuple[QueryTypeRouteDecision, ...]:
        return tuple(self.route(query_type) for query_type in REQUIRED_QUERY_TYPES)


def build_query_type_router_public_rows(
    router: QueryTypeRouter | None = None,
) -> list[dict[str, str | int | bool | None]]:
    active_router = router or QueryTypeRouter()
    rows: list[dict[str, str | int | bool | None]] = []
    for decision in active_router.route_all():
        rows.append(
            {
                "router_policy_id": decision.router_policy_id,
                "query_type": decision.query_type,
                "route_policy_id": decision.route_policy_id,
                "selected_candidate_id": decision.selected_candidate_id,
                "retrieval_method_label": decision.retrieval_method_label,
                "execution_mode": decision.execution_mode,
                "packing_policy_id": decision.packing_policy_id,
                "should_retrieve": decision.should_retrieve,
                "query_rewrite_strategy_id": decision.query_rewrite_strategy_id,
                "decision": decision.decision,
                "claim_boundary": decision.claim_boundary,
                "rejected_candidate_count": len(decision.rejected_candidate_ids),
                "decision_reason_tag": decision.decision_reason_tag,
                "production_default": decision.production_default,
            }
        )
    return rows
