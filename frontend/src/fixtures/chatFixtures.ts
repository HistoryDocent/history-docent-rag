import type { ChatResponse } from "../types/chat";

export const answerableFixture: ChatResponse = {
  contract_version: "chat-api/v1",
  request_id: "fixture-answerable-001",
  query_id: "fixture-query-001",
  query_type: "place_story",
  answer:
    "경복궁은 조선 왕조가 한양을 수도로 삼은 뒤 국가 운영의 중심을 보여주는 장소입니다. 광화문과 궁궐 축을 함께 보면 왕권, 의례, 도시 계획이 한 공간에 배치된 방식을 이해할 수 있습니다.",
  spoken_answer:
    "경복궁은 조선이 한양을 수도로 삼은 뒤 왕권과 의례를 도시 중심에 배치한 장소입니다. 광화문에서 궁궐 축을 따라 보면 한양의 정치 공간이 어떻게 설계됐는지 쉽게 느낄 수 있습니다.",
  citations: [
    {
      citation_id: "cite-fixture-001",
      evidence_id: "evidence-fixture-001",
      child_id: "child-fixture-001",
      parent_id: "parent-fixture-001",
      doc_id: "doc-public-sample-001",
      source_rank: 1,
      pack_rank: 1,
      source_block_ids: ["block-fixture-001"],
      citation_block_ids: ["block-fixture-001"],
      citation_recoverable: true,
    },
  ],
  evidence_ids: ["evidence-fixture-001"],
  place_ids: ["gyeongbokgung", "gwanghwamun"],
  abstained: false,
  unsupported_claim_risk: "low",
  usage: {
    retrieval_mode: "contract_only",
    route_policy_id: "dense_multilingual_e5_small_voice_rewrite",
    retrieval_candidate_count: 5,
    solar_call_count: 0,
  },
  classifier_router_dry_run: {
    active_route_applied: false,
    guarded_route_candidate: {
      guard_applied: false,
      route_policy_id: "default_dense_voice_rewrite",
      route_candidate_id: "dense_multilingual_e5_small_voice_rewrite",
    },
  },
};

export const noAnswerFixture: ChatResponse = {
  contract_version: "chat-api/v1",
  request_id: "fixture-no-answer-001",
  query_id: "fixture-query-002",
  query_type: "no_answer",
  answer:
    "현재 공개 fixture 기준으로는 이 질문에 답할 근거가 충분하지 않습니다. 장소나 시대를 더 구체적으로 묻는 질문으로 바꿔 주세요.",
  spoken_answer:
    "지금 근거로는 답하기 어렵습니다. 장소나 시대를 더 구체적으로 알려주시면 다시 찾아볼 수 있습니다.",
  citations: [],
  evidence_ids: [],
  place_ids: [],
  abstained: true,
  unsupported_claim_risk: "low",
  usage: {
    retrieval_mode: "contract_only",
    route_policy_id: null,
    retrieval_candidate_count: 0,
    solar_call_count: 0,
  },
  classifier_router_dry_run: {
    active_route_applied: false,
    guarded_route_candidate: {
      guard_applied: true,
      route_policy_id: "no_answer_abstain_first",
      route_candidate_id: "abstain_first",
    },
  },
};
