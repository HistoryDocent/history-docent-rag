# Chat Retrieval Integration Report

## 목적

FastAPI `/api/v1/chat`의 `retrieval_backed` mode가 retrieval, evidence packing, citation answer assembly를 같은 응답 계약으로 연결하는지 검증한다.

이 문서는 검색 성능 개선 주장이 아니다. public report에서는 fixture retrieval backend로 API integration grain과 leakage gate만 검증한다. private corpus 기반 dense retrieval smoke는 별도 local 검증 대상으로 둔다.

## 정량 리포트

| metric | value |
| --- | ---: |
| request_count | 3 |
| success_count | 3 |
| retrieval_backed_request_count | 2 |
| retrieval_success_count | 1 |
| answered_count | 2 |
| abstained_count | 1 |
| citation_count | 2 |
| evidence_id_count | 2 |
| retrieval_candidate_count | 1 |
| classifier_dry_run_count | 3 |
| classifier_route_policy_changed_count | 1 |
| classifier_active_route_applied_count | 0 |
| classifier_fallback_count | 1 |
| classifier_guarded_route_candidate_count | 3 |
| classifier_guard_applied_count | 0 |
| classifier_guarded_route_policy_changed_count | 1 |
| active_route_flag_dry_run_count | 3 |
| active_route_flag_enabled_count | 1 |
| active_route_flag_shadow_mode_count | 1 |
| active_route_flag_default_enabled_count | 0 |
| active_route_flag_applied_count | 0 |
| active_route_flag_policy_changed_count | 1 |
| live_solar_call_count | 0 |
| latency_p95_ms | 0.901100 |
| retrieval_latency_p95_ms | 0.021800 |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 3 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `integration_scope`: `retrieval_backed` request가 retrieval outcome, evidence packing, citation assembler를 거쳐 동일한 ChatResponse로 반환되는지 검증했다.
- `grain_boundary`: public result row grain은 API smoke case 1건이다. row에는 query/answer/chunk text를 저장하지 않는다.
- `retrieval_boundary`: public report는 fixture retrieval backend를 사용한다. private dense backend는 원문 chunk와 embedding cache를 public에 노출하지 않기 위해 별도 local 경로로만 사용한다.
- `no_answer_policy`: no_answer retrieval_backed request는 evidence 없이 abstained=true를 반환해야 한다.
- `provider_boundary`: Solar Pro 3 live generation은 호출하지 않고, provider_call_count와 solar_call_count를 0으로 유지한다.
- `classifier_router_boundary`: classifier/router dry-run은 API 응답에 포함하지만 retrieval_backed route 선택에는 적용하지 않는다.
- `guarded_route_boundary`: guarded_route_candidate는 관찰 필드이며 retrieval_backed route 선택에는 적용하지 않는다.
- `active_route_flag_boundary`: active_route_mode=shadow 요청에서도 retrieval_backed route는 기존 query_type 기준을 유지하고 active_route_applied=false를 반환한다.
- `gate_status`: PASS

## 해석

`retrieval_backed` mode는 기존 `contract_only` mode를 대체하지 않고 병렬 경로로 추가했다. 검색된 evidence는 `P0_rank_order` packing과 `citation-rag-answer/v1` assembler를 통과해야만 답변에 포함된다.
