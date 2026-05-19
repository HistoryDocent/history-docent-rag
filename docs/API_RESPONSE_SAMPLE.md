# API Response Sample

## 결론

`HD-API-SAMPLE-001`은 FastAPI `/api/v1/chat`의 public-safe 응답 예시를 고정한다.

이 문서는 API 계약 설명용이다. 검색 성능, Solar Pro 3 답변 품질, production routing, 음성 앱 완성 주장이 아니다.

아래 sample은 fixture/synthetic 값만 사용한다. raw query, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 응답 계약 핵심

| 구분 | 필드 |
| --- | --- |
| answer contract | `answer`, `spoken_answer`, `citations`, `evidence_ids`, `abstained`, `unsupported_claim_risk` |
| citation trace | `child_id`, `parent_id`, `doc_id`, `source_block_ids`, `citation_block_ids`, `citation_recoverable` |
| retrieval state | `usage.retrieval_mode`, `usage.retrieval_method`, `usage.route_policy_id`, `usage.retrieval_candidate_count` |
| provider boundary | `provider`, `model_id`, `usage.solar_call_count` |
| router dry-run | `classifier_router_dry_run`, `guarded_route_candidate`, `active_route_flag_dry_run` |

## Answerable Response Sample

```json
{
  "contract_version": "chat-api/v1",
  "rag_contract_version": "citation-rag-answer/v1",
  "request_id": "sample-place-story-001",
  "query_id": "sample-place-story-001",
  "query_type": "place_story",
  "answer": "이 문장은 공개용 합성 샘플입니다. 실제 도서 원문이나 private 평가 질문을 사용하지 않고, 화면 답변이 citation과 함께 반환되는 구조만 보여줍니다.",
  "spoken_answer": "공개용 샘플 음성 답변입니다. 실제 역사 해설은 검색과 Solar Pro 3 검증 뒤 연결됩니다.",
  "citations": [
    {
      "citation_id": "citation-sample-001",
      "evidence_id": "evidence-sample-001",
      "child_id": "sample-child-001",
      "parent_id": "sample-parent-001",
      "doc_id": "sample-doc-001",
      "source_rank": 1,
      "pack_rank": 1,
      "source_block_ids": ["sample-block-001"],
      "citation_block_ids": ["sample-block-001"],
      "citation_recoverable": true
    }
  ],
  "evidence_ids": ["evidence-sample-001"],
  "place_ids": ["seoul-hanyang"],
  "abstained": false,
  "unsupported_claim_risk": "low",
  "provider": "contract_only",
  "model_id": "contract-only",
  "answer_policy_id": "chat-citation-rag-contract-v1",
  "latency_ms": 0.0,
  "public_allowed": true,
  "usage": {
    "input_chars": 32,
    "evidence_count": 1,
    "estimated_context_chars": 320,
    "retrieval_mode": "retrieval_backed",
    "retrieval_method": "fixture_retrieval",
    "route_policy_id": "default_dense_voice_rewrite_v1",
    "route_candidate_id": "dense_multilingual_e5_small_voice_rewrite",
    "route_claim_boundary": "dev-only",
    "retrieval_candidate_count": 1,
    "retrieval_latency_ms": 0.0,
    "query_rewrite_changed": false,
    "query_rewrite_latency_ms": 0.0,
    "provider_call_count": 0,
    "solar_call_count": 0,
    "prompt_tokens": null,
    "completion_tokens": null,
    "total_tokens": null,
    "estimated_cost": 0.0
  },
  "classifier_router_dry_run": {
    "dry_run_policy_id": "chat-classifier-router-dry-run-v1",
    "enabled": true,
    "classifier_id": "deterministic-query-type-classifier-v1",
    "predicted_query_type": "place_story",
    "confidence": 0.82,
    "fallback_used": false,
    "matched_rule_count": 2,
    "predicted_route_policy_id": "default_dense_voice_rewrite_v1",
    "predicted_route_candidate_id": "dense_multilingual_e5_small_voice_rewrite",
    "predicted_route_claim_boundary": "dev-only",
    "predicted_should_retrieve": true,
    "active_query_type": "place_story",
    "active_route_policy_id": "default_dense_voice_rewrite_v1",
    "active_route_candidate_id": "dense_multilingual_e5_small_voice_rewrite",
    "active_route_claim_boundary": "dev-only",
    "route_policy_changed": false,
    "active_route_applied": false,
    "latency_ms": 0.0,
    "guarded_route_candidate": {
      "guard_policy_id": "relationship-route-guard-v1",
      "guarded_query_type": "place_story",
      "route_policy_id": "default_dense_voice_rewrite_v1",
      "route_candidate_id": "dense_multilingual_e5_small_voice_rewrite",
      "route_claim_boundary": "dev-only",
      "should_retrieve": true,
      "guard_applied": false,
      "guard_reason_tags": [],
      "route_policy_changed": false,
      "score_margin": 0.0
    },
    "active_route_flag_dry_run": {
      "flag_policy_id": "chat-active-route-flag-dry-run-v1",
      "enabled": false,
      "mode": "disabled",
      "requested_mode": "disabled",
      "default_enabled": false,
      "selected_query_type": "place_story",
      "selected_route_policy_id": "default_dense_voice_rewrite_v1",
      "selected_route_candidate_id": "dense_multilingual_e5_small_voice_rewrite",
      "selected_route_claim_boundary": "dev-only",
      "selected_should_retrieve": true,
      "guard_policy_id": "relationship-route-guard-v1",
      "guarded_query_type": "place_story",
      "guard_applied": false,
      "route_policy_changed": false,
      "fallback_reason_tag": "feature_flag_disabled",
      "active_route_applied": false,
      "shadow_decision_ref": "active-route-shadow-evaluation-dev70-v1"
    }
  }
}
```

## No-answer Response Sample

```json
{
  "contract_version": "chat-api/v1",
  "rag_contract_version": "citation-rag-answer/v1",
  "request_id": "sample-no-answer-001",
  "query_id": "sample-no-answer-001",
  "query_type": "no_answer",
  "answer": "제공된 근거 안에서는 답변할 수 없습니다.",
  "spoken_answer": "지금 근거로는 답변하기 어렵습니다.",
  "citations": [],
  "evidence_ids": [],
  "place_ids": [],
  "abstained": true,
  "unsupported_claim_risk": "low",
  "provider": "contract_only",
  "model_id": "contract-only",
  "answer_policy_id": "chat-citation-rag-contract-v1",
  "latency_ms": 0.0,
  "public_allowed": true,
  "usage": {
    "input_chars": 28,
    "evidence_count": 0,
    "estimated_context_chars": 0,
    "retrieval_mode": "retrieval_backed",
    "retrieval_method": "fixture_retrieval",
    "route_policy_id": "no_answer_abstain_first_v1",
    "route_candidate_id": "no_answer_abstain",
    "route_claim_boundary": "contract-only",
    "retrieval_candidate_count": 0,
    "retrieval_latency_ms": 0.0,
    "query_rewrite_changed": false,
    "query_rewrite_latency_ms": 0.0,
    "provider_call_count": 0,
    "solar_call_count": 0,
    "prompt_tokens": null,
    "completion_tokens": null,
    "total_tokens": null,
    "estimated_cost": 0.0
  },
  "classifier_router_dry_run": {
    "dry_run_policy_id": "chat-classifier-router-dry-run-v1",
    "enabled": true,
    "classifier_id": "deterministic-query-type-classifier-v1",
    "predicted_query_type": "no_answer",
    "confidence": 0.9,
    "fallback_used": false,
    "matched_rule_count": 1,
    "predicted_route_policy_id": "no_answer_abstain_first_v1",
    "predicted_route_candidate_id": "no_answer_abstain",
    "predicted_route_claim_boundary": "contract-only",
    "predicted_should_retrieve": false,
    "active_query_type": "no_answer",
    "active_route_policy_id": "no_answer_abstain_first_v1",
    "active_route_candidate_id": "no_answer_abstain",
    "active_route_claim_boundary": "contract-only",
    "route_policy_changed": false,
    "active_route_applied": false,
    "latency_ms": 0.0,
    "guarded_route_candidate": {
      "guard_policy_id": "relationship-route-guard-v1",
      "guarded_query_type": "no_answer",
      "route_policy_id": "no_answer_abstain_first_v1",
      "route_candidate_id": "no_answer_abstain",
      "route_claim_boundary": "contract-only",
      "should_retrieve": false,
      "guard_applied": false,
      "guard_reason_tags": [],
      "route_policy_changed": false,
      "score_margin": 0.0
    },
    "active_route_flag_dry_run": {
      "flag_policy_id": "chat-active-route-flag-dry-run-v1",
      "enabled": false,
      "mode": "disabled",
      "requested_mode": "disabled",
      "default_enabled": false,
      "selected_query_type": "no_answer",
      "selected_route_policy_id": "no_answer_abstain_first_v1",
      "selected_route_candidate_id": "no_answer_abstain",
      "selected_route_claim_boundary": "contract-only",
      "selected_should_retrieve": false,
      "guard_policy_id": "relationship-route-guard-v1",
      "guarded_query_type": "no_answer",
      "guard_applied": false,
      "route_policy_changed": false,
      "fallback_reason_tag": "feature_flag_disabled",
      "active_route_applied": false,
      "shadow_decision_ref": "active-route-shadow-evaluation-dev70-v1"
    }
  }
}
```

## Error Envelope Samples

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed.",
    "details": [
      {
        "field": "query",
        "message": "query must not be blank"
      }
    ]
  }
}
```

```json
{
  "error": {
    "code": "provider_unavailable",
    "message": "Solar Pro 3 live generation is disabled for the public API contract."
  }
}
```

## Public Report Row Sample

public report row에는 화면 답변과 음성 답변 본문을 저장하지 않는다. report grain은 API smoke case 단위이며 route label, citation count, provider count만 남긴다.

```json
{
  "contract_version": "chat-api/v1",
  "rag_contract_version": "citation-rag-answer/v1",
  "query_type": "place_story",
  "provider": "contract_only",
  "model_id": "contract-only",
  "answer_policy_id": "chat-citation-rag-contract-v1",
  "abstained": false,
  "unsupported_claim_risk": "low",
  "retrieval_mode": "retrieval_backed",
  "retrieval_method": "fixture_retrieval",
  "route_policy_id": "default_dense_voice_rewrite_v1",
  "route_candidate_id": "dense_multilingual_e5_small_voice_rewrite",
  "citation_count": 1,
  "evidence_id_count": 1,
  "place_id_count": 1,
  "classifier_dry_run_enabled": true,
  "classifier_active_route_applied": false,
  "guard_policy_id": "relationship-route-guard-v1",
  "guard_applied": false,
  "active_route_flag_enabled": false,
  "active_route_flag_default_enabled": false,
  "active_route_applied": false,
  "solar_call_count": 0
}
```

## Claim Boundary

허용 표현:

- `/api/v1/chat` 응답 계약 sample을 작성했다.
- `answer`와 `spoken_answer`를 분리하는 구조를 보여준다.
- citation trace와 public report row의 차이를 설명한다.
- active route는 dry-run/shadow 관찰 필드로만 노출한다.

금지 표현:

- Solar Pro 3 live 답변 품질 검증 완료
- production routing 적용 완료
- 실제 관광 음성 앱 완성
- private corpus 원문 기반 sample 공개
- locked test에서 active route 개선 입증

## 다음 작업

`HD-PORTFOLIO-QA-001`, ColBERT hard subset, voice UI visual QA, portfolio demo runbook, public repository audit refresh는 완료됐다. 다음 작업은 `HD-PORTFOLIO-REHEARSAL-001`이다.

다음 작업은 새 실험이 아니라 제출용 설명 리허설이다. README 기반 3분 설명, 기각 후보 설명, 금지 claim 회피를 확인한다.
