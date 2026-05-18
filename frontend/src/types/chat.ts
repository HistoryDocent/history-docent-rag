export type LanguageCode = "ko" | "en" | "mixed";
export type QueryType =
  | "place_fact"
  | "place_story"
  | "relationship"
  | "overview"
  | "route_context"
  | "voice_followup"
  | "no_answer";

export type UnsupportedClaimRisk = "low" | "medium" | "high";

export interface ChatRequest {
  request_id?: string;
  query: string;
  language: LanguageCode;
  query_type: QueryType;
  place_context: string[];
  voice_mode: boolean;
  retrieval_mode: "contract_only" | "private_artifact";
  provider_mode: "contract_only" | "solar_pro_3";
  active_route_mode: "disabled" | "shadow";
}

export interface ChatCitation {
  citation_id: string;
  evidence_id: string;
  child_id: string;
  parent_id: string;
  doc_id: string;
  source_rank: number;
  pack_rank: number;
  source_block_ids: string[];
  citation_block_ids: string[];
  citation_recoverable: boolean;
}

export interface ChatUsage {
  retrieval_mode: string;
  route_policy_id: string | null;
  retrieval_candidate_count: number;
  solar_call_count: number;
}

export interface ChatRouterDryRun {
  active_route_applied: boolean;
  guarded_route_candidate: {
    guard_applied: boolean;
    route_policy_id: string;
    route_candidate_id: string;
  };
}

export interface ChatResponse {
  contract_version: string;
  request_id: string;
  query_id: string;
  query_type: QueryType;
  answer: string;
  spoken_answer: string;
  citations: ChatCitation[];
  evidence_ids: string[];
  place_ids: string[];
  abstained: boolean;
  unsupported_claim_risk: UnsupportedClaimRisk;
  usage: ChatUsage;
  classifier_router_dry_run: ChatRouterDryRun;
}
