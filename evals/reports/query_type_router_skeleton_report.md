# Query Type Router Skeleton Report

## 목적

`HD-ROUTER-001`에서 고정한 query type별 route policy를 deterministic router skeleton으로 구현했는지 검증한다.

이 문서는 runtime branch contract 검증이다. 검색 성능 개선, locked test 개선, Solar Pro 3 답변 품질 개선 주장이 아니다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `query-type-router-skeleton-report/v1` |
| run_id | `HD-ROUTER-002` |
| router_policy_id | `query_type_router_v1` |
| solar_call_count | 0 |
| cuda_required | false |

## 정량 리포트

| metric | value |
| --- | ---: |
| query_type_count | 7 |
| router_policy_count | 1 |
| route_policy_count | 3 |
| should_retrieve_count | 6 |
| abstain_first_count | 1 |
| dense_default_count | 5 |
| relationship_hybrid_count | 1 |
| rejected_candidate_count | 3 |
| live_solar_call_count | 0 |

## Route Table

| query_type | route_policy_id | selected_candidate_id | execution_mode | should_retrieve | decision | claim_boundary |
| --- | --- | --- | --- | ---: | --- | --- |
| `place_fact` | `default_dense_voice_rewrite_v1` | `dense_multilingual_e5_small_voice_rewrite` | `dense` | true | `keep_default` | dev-only |
| `place_story` | `default_dense_voice_rewrite_v1` | `dense_multilingual_e5_small_voice_rewrite` | `dense` | true | `keep_default` | dev-only |
| `relationship` | `relationship_hybrid_weighted_e5_v1` | `hybrid_weighted_e5_small_alpha_0_5` | `hybrid_weighted` | true | `adopt_route_candidate` | dev-input-only |
| `overview` | `default_dense_voice_rewrite_v1` | `dense_multilingual_e5_small_voice_rewrite` | `dense` | true | `keep_default` | dev-only |
| `route_context` | `default_dense_voice_rewrite_v1` | `dense_multilingual_e5_small_voice_rewrite` | `dense` | true | `keep_default` | dev-only |
| `voice_followup` | `default_dense_voice_rewrite_v1` | `dense_multilingual_e5_small_voice_rewrite` | `dense` | true | `keep_default` | dev-only |
| `no_answer` | `abstain_first_v1` | `abstain_contract` | `abstain` | false | `keep_abstain_first` | dev-label boundary |

## Public Output Gate

| metric | value |
| --- | ---: |
| result_row_count | 7 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `router_scope`: query type label이 이미 주어진다는 전제에서 route table branch만 검증했다.
- `relationship_branch`: relationship query type은 hybrid weighted E5 route candidate로 분기한다.
- `no_answer_branch`: no_answer query type은 retrieval보다 abstain-first policy를 우선한다.
- `default_branch`: overview, place_fact, place_story, route_context, voice_followup은 dense voice rewrite default route를 유지한다.
- `security_boundary`: public row와 report에는 query, answer, evidence text, chunk text를 저장하지 않는다.
- `execution_boundary`: 이번 report에서 Solar Pro 3 호출과 CUDA 연산은 필요하지 않다.
- `gate_status`: PASS
- `external_audit`: router skeleton은 구현됐지만 classifier와 locked performance claim은 아직 없다.
- `summary_counts`: route_policy_count=3, relationship_hybrid_count=1

## 해석

router skeleton은 query type label을 이미 알고 있다는 전제에서만 동작한다. query type classifier, Solar Pro 3 generation, locked 성능 개선은 별도 gate에서 검증해야 한다.
