# Query Type Router Decision Report

## 목적

현재 RAG 실험 결과를 query type별 route policy로 정리한다.

이 리포트는 router 구현 완료나 production 성능 개선 주장이 아니다. dev retrieval, dev input-only, live-dev-subset, locked-readiness-only 근거를 분리해 다음 구현의 route table을 고정한다.

raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| report_version | `query-type-router-decision-report/v1` |
| decision_id | `HD-ROUTER-001` |
| router_policy_id | `query_type_router_v1` |
| generated_from | public-safe aggregate reports |
| default_retrieval_candidate | `dense_multilingual_e5_small_voice_rewrite` |
| relationship_route_candidate | `hybrid_weighted_e5_small_alpha_0_5` |
| place_story_route_candidate | `place_story_guarded_boost_v1` |
| solar_call_count | 0 |
| cuda_required | false |

## 정량 리포트

### 전체 기본 후보

| candidate_id | scope | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | latency_p95_ms | decision |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `dense_multilingual_e5_small_voice_rewrite` | dev 70 | 0.700000 | 0.800000 | 0.850000 | 0.758056 | 0.615293 | 19.560200 | keep default |
| `hybrid_weighted_e5_small_alpha_0_5` | dev 70 | 0.566667 | 0.733333 | 0.783333 | 0.655278 | 0.509310 | 27.547000 | reject global default |

### Query Type별 Route 판단

| query_type | selected_route_policy | selected_candidate | key_metric | value | decision | claim_boundary |
| --- | --- | --- | --- | ---: | --- | --- |
| `no_answer` | `abstain_first_v1` | abstain contract | abstain_with_candidate_count | 10 | keep policy | dev-label boundary |
| `overview` | `default_dense_voice_rewrite_v1` | `dense_multilingual_e5_small_voice_rewrite` | MRR | 0.750000 | keep default | dev-only |
| `place_fact` | `default_dense_voice_rewrite_v1` | `dense_multilingual_e5_small_voice_rewrite` | Recall@5 | 1.000000 | keep default | dev-only |
| `place_story` | `default_dense_voice_rewrite_v1` | `dense_multilingual_e5_small_voice_rewrite` | Recall@5 | 0.600000 | keep default | dev-only |
| `relationship` | `relationship_hybrid_weighted_e5_v1` | `hybrid_weighted_e5_small_alpha_0_5` | Recall@5 | 1.000000 | adopt route candidate | dev-input-only |
| `route_context` | `default_dense_voice_rewrite_v1` | `dense_multilingual_e5_small_voice_rewrite` | Recall@5 | 0.900000 | keep default | dev-only |
| `voice_followup` | `default_dense_voice_rewrite_v1` | `dense_multilingual_e5_small_voice_rewrite` | Recall@5 | 1.000000 | keep default | dev-only |

### Relationship 후보 비교

| candidate_id | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | latency_p95_ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `dense_multilingual_e5_small_voice_rewrite` | 0.700000 | 0.800000 | 0.800000 | 0.750000 | 0.652090 | 15.566600 |
| `hybrid_weighted_e5_small_alpha_0_5` | 0.700000 | 1.000000 | 1.000000 | 0.833333 | 0.709355 | 26.850500 |
| `graphrag_lite_entity_path_v1` | 0.700000 | 1.000000 | 1.000000 | 0.833333 | 0.707299 | 27.580100 |
| `graphrag_lite_community_hint_v1` | 0.700000 | 1.000000 | 1.000000 | 0.833333 | 0.679018 | 27.511100 |

### Place Story 후보 판단

| candidate_id | scope | Correct-with-Evidence delta | citation_precision delta | citation_recall delta | unsupported_claim_rate delta | selected_candidate_count | decision |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `place_story_guarded_boost_v1` | live dev subset 10 | 0.000000 | 0.000000 | 0.028572 | 0.000000 | 1 | keep dev-only |
| `place_story_guarded_boost_v1` | locked readiness 5 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | reject production route |

## Public Output Gate

| metric | value |
| --- | ---: |
| source_report_count | 5 |
| router_policy_count | 4 |
| query_type_count | 7 |
| adopted_route_candidate_count | 1 |
| kept_default_route_count | 5 |
| rejected_production_route_count | 1 |
| live_solar_call_count_for_this_report | 0 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## 정성 리포트

- `default_route`: answerable query의 기본 route는 `dense_multilingual_e5_small_voice_rewrite`로 유지한다.
- `relationship_route`: `relationship`에는 `hybrid_weighted_e5_small_alpha_0_5`를 route 후보로 채택한다. 단, generation 품질과 locked test 개선은 아직 주장하지 않는다.
- `graphrag_boundary`: GraphRAG-lite는 relationship에서 hybrid reference보다 nDCG@5가 낮아 route 후보가 아니다.
- `place_story_boundary`: guarded boost는 dev live subset에서 작은 citation recall 이득만 있었고 locked readiness에서 candidate 선택 0건이므로 production route로 채택하지 않는다.
- `no_answer_boundary`: no-answer는 retrieval hit보다 abstention policy와 unsupported claim 방지가 우선이다.
- `implementation_boundary`: 이번 산출물은 decision report이며 query type classifier나 runtime router 구현이 아니다.
- `cost_boundary`: 이 리포트 생성 과정에서 Solar Pro 3 추가 호출은 없다.
- `public_policy`: public artifact에는 raw query, raw answer, evidence text, prompt, chunk text, private path, secret을 저장하지 않는다.

## Claim Boundary

허용 표현:

- dev 기준 기본 non-rerank 후보는 `dense_multilingual_e5_small_voice_rewrite`다.
- relationship query에는 hybrid weighted E5 route 후보를 둘 근거가 있다.
- GraphRAG-lite는 이번 relationship input-only 비교에서 기본 route로 승격하지 않았다.
- place_story guarded boost는 production 기본 route로 채택하지 않았다.

금지 표현:

- query-type router가 production 성능을 개선했다.
- relationship route가 locked test에서 개선됐다.
- guarded boost가 place_story에 일반화됐다.
- GraphRAG가 relationship에 효과적이다.
- Solar Pro 3 답변 품질이 이 리포트에서 개선됐다.

## Data Mart

`fact_query_type_router_decision`의 grain은 `router_decision_id + query_type + route_policy_id + candidate_id + metric_family + claim_boundary`다.

dimension 후보:

- `dim_query_type`
- `dim_route_policy`
- `dim_retrieval_candidate`
- `dim_generation_policy`
- `dim_metric_family`
- `dim_claim_boundary`

저장 금지:

- raw query
- raw answer
- raw evidence
- prompt
- chunk text
- private file path
- secret

## 채택 판단

`HD-ROUTER-001`은 문서 gate로 통과한다.

다음 구현에서 사용할 route table은 다음으로 고정한다.

| route_group | status |
| --- | --- |
| default answerable route | keep `dense_multilingual_e5_small_voice_rewrite` |
| relationship route | adopt `hybrid_weighted_e5_small_alpha_0_5` as route candidate |
| place_story guarded route | keep dev-only, reject production default |
| GraphRAG-lite route | reject |
| no-answer route | keep abstain-first policy |

## 외부 감사 결론

확인된 주요 문제는 없다.

남은 리스크:

- route policy는 아직 runtime router 구현이 아니다.
- relationship route는 retrieval/input-only 근거이며 generation metric으로 검증되지 않았다.
- place_story guarded boost는 dev에서 제한적 이득만 있고 locked readiness에서 treatment가 없었다.
- no-answer classifier는 별도 구현과 평가가 필요하다.
