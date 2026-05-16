# Query Type Router Decision

## 결론

`query-type router`는 production 기본값으로 완성됐다고 주장하지 않는다.

다만 다음 구현 단계의 route policy는 고정한다. 기본 answerable query는 `dense_multilingual_e5_small_voice_rewrite`를 유지하고, `relationship`은 `hybrid_weighted_e5_small_alpha_0_5`를 제한적 route 후보로 채택한다. `place_story`의 guarded boost는 locked readiness에서 candidate 선택 0건이므로 production route로 채택하지 않고 dev-only 실험선으로 보관한다.

이 문서는 public-safe 의사결정 문서다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 담당 관점 회의 결과

| 담당 관점 | 판단 |
| --- | --- |
| RAG 아키텍처 | 단일 retrieval이 모든 query type에서 최선이라는 주장은 근거가 부족하다. router는 필요하지만 route 수를 최소화한다. |
| Retrieval | relationship은 hybrid weighted E5가 top-k와 rank 품질에서 dense voice rewrite보다 낫다. 나머지는 dense voice rewrite 유지가 더 안전하다. |
| Generation | place_story guarded boost는 live-dev-subset에서 citation recall만 소폭 올렸고 locked readiness에서 treatment가 없었다. 기본 route 채택 근거가 부족하다. |
| Evaluation | 이 판단은 dev-only, live-dev-subset, locked-readiness-only 근거를 분리한다. locked 성능 개선 표현은 금지한다. |
| Data warehouse | router decision fact의 grain은 `router_decision_id + query_type + route_policy_id + candidate_id + metric_family + claim_boundary`로 둔다. |
| Security | public 문서에는 집계 metric, candidate id, decision tag만 남긴다. 원문과 private artifact path는 금지한다. |
| Portfolio | 강점은 기법을 많이 붙인 것이 아니라 query type별로 채택, 보류, 기각을 분리한 점이다. |
| 외부 감사 | relationship route 후보만 제한 채택하고 place_story route는 보류한 판단이 과장 위험을 줄인다. |

## Router Policy v1

| query_type | route_policy_id | retrieval/evidence policy | decision | claim_boundary |
| --- | --- | --- | --- | --- |
| `no_answer` | `abstain_first_v1` | 검색 후보가 있어도 no-answer contract 우선 | keep policy | dev-label boundary |
| `overview` | `default_dense_voice_rewrite_v1` | `dense_multilingual_e5_small_voice_rewrite` + `P0_rank_order` | keep default | dev-only |
| `place_fact` | `default_dense_voice_rewrite_v1` | `dense_multilingual_e5_small_voice_rewrite` + `P0_rank_order` | keep default | dev-only |
| `place_story` | `default_dense_voice_rewrite_v1` | `dense_multilingual_e5_small_voice_rewrite` + `P0_rank_order` | keep default | dev-only |
| `relationship` | `relationship_hybrid_weighted_e5_v1` | `hybrid_weighted_e5_small_alpha_0_5` + source chunk citation | adopt route candidate | dev-input-only |
| `route_context` | `default_dense_voice_rewrite_v1` | `dense_multilingual_e5_small_voice_rewrite` + `P0_rank_order` | keep default | dev-only |
| `voice_followup` | `default_dense_voice_rewrite_v1` | `dense_multilingual_e5_small_voice_rewrite` + voice deterministic rewrite | keep default | dev-only |

해석:

- `relationship`만 별도 route 후보로 둔다.
- `place_story_guarded_boost_v1`은 production route 후보에서 제외하고 dev-only limited generalization 사례로 보관한다.
- `no_answer`는 retrieval metric으로 성능을 주장하지 않는다. 검색 후보 반환 여부보다 abstention contract와 hallucination 방지가 우선이다.

## 정량 근거

### 기본 후보

`dense_multilingual_e5_small_voice_rewrite`는 private dev 70개에서 전체 기준 가장 안정적인 non-rerank 후보였다.

| metric | value |
| --- | ---: |
| Recall@1 | 0.700000 |
| Recall@3 | 0.800000 |
| Recall@5 | 0.850000 |
| MRR | 0.758056 |
| nDCG@5 | 0.615293 |
| latency_p95_ms | 19.560200 |

### Query Type별 기본 후보 지표

| query_type | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | latency_p95_ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `overview` | 0.700000 | 0.800000 | 0.800000 | 0.750000 | 0.610343 | 16.004600 |
| `place_fact` | 0.800000 | 1.000000 | 1.000000 | 0.900000 | 0.783397 | 15.779200 |
| `place_story` | 0.600000 | 0.600000 | 0.600000 | 0.600000 | 0.438900 | 15.156600 |
| `relationship` | 0.700000 | 0.800000 | 0.800000 | 0.750000 | 0.652090 | 15.566600 |
| `route_context` | 0.700000 | 0.800000 | 0.900000 | 0.753333 | 0.533275 | 15.828100 |
| `voice_followup` | 0.700000 | 0.800000 | 1.000000 | 0.795000 | 0.673753 | 20.991400 |

### Relationship Route 후보

`relationship` dev 10개에서는 `hybrid_weighted_e5_small_alpha_0_5`가 기본 후보보다 Recall@3, Recall@5, MRR, nDCG@5가 높았다.

| candidate_id | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | latency_p95_ms | decision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `dense_multilingual_e5_small_voice_rewrite` | 0.700000 | 0.800000 | 0.800000 | 0.750000 | 0.652090 | 15.566600 | baseline |
| `hybrid_weighted_e5_small_alpha_0_5` | 0.700000 | 1.000000 | 1.000000 | 0.833333 | 0.709355 | 26.850500 | route candidate |

주의:

- 이 route는 relationship query type에 한정한다.
- 전체 query default로 hybrid를 채택하지 않는다.
- GraphRAG-lite는 relationship input-only에서 hybrid reference를 넘지 못했으므로 route 후보가 아니다.

### Place Story Guarded Boost 판단

`place_story_guarded_boost_v1`은 dev live subset에서 citation recall만 소폭 개선했지만 locked readiness에서 candidate 선택이 0건이었다.

| scope | metric | value |
| --- | --- | ---: |
| live dev subset 10 | Correct-with-Evidence delta | 0.000000 |
| live dev subset 10 | citation_precision delta | 0.000000 |
| live dev subset 10 | citation_recall delta | 0.028572 |
| live dev subset 10 | unsupported_claim_rate delta | 0.000000 |
| live dev subset 10 | candidate_live_call_count | 1 |
| locked readiness 5 | selected_candidate_count | 0 |
| locked readiness 5 | candidate_live_call_count | 0 |
| locked readiness 5 | citation_recoverability_min | 1.000000 |

판단:

- dev-only limited generalization 사례로 보관한다.
- production 기본 route로 채택하지 않는다.
- locked 결과를 보고 threshold를 완화하지 않는다.

## GraphRAG-lite와 RAPTOR-lite 위치

GraphRAG-lite는 relationship 질문에서 별도 후보로 실험했지만, hybrid reference 대비 nDCG@5가 개선되지 않았다. 따라서 router v1의 relationship route는 GraphRAG가 아니라 hybrid weighted E5다.

RAPTOR-lite도 overview/place_story input-only 비교에서 baseline 대비 Recall/MRR 개선이 없고 nDCG@5가 하락했다. 따라서 router v1에는 넣지 않는다.

## Router Implementation Boundary

이번 결정은 route policy 문서화다. 아직 다음을 주장하지 않는다.

- query type classifier production 완료
- production routing 완료
- locked test 성능 개선
- Solar Pro 3 답변 품질 개선
- 통계적으로 유의미한 최종 개선

router skeleton은 deterministic query type label을 입력으로 받는다. classifier는 `HD-ROUTER-003`에서 baseline으로 구현했지만 production routing 완료 주장은 아니다.

## 구현 상태

`HD-ROUTER-002`에서 deterministic query type router skeleton을 구현했다.

구현 경계:

- query type label은 이미 주어진다고 가정한다.
- `relationship`은 `relationship_hybrid_weighted_e5_v1` route로 분기한다.
- `no_answer`는 `abstain_first_v1` route로 분기한다.
- 나머지 answerable query type은 `default_dense_voice_rewrite_v1` route를 유지한다.
- query type classifier, locked 성능 개선, Solar Pro 3 답변 품질 개선은 아직 주장하지 않는다.

근거 리포트:

- `evals/reports/query_type_router_skeleton_report.md`

## Classifier 구현 상태

`HD-ROUTER-003`에서 deterministic query type classifier baseline을 구현했다.

구현 경계:

- 실제 API 입력처럼 query type label이 없는 상태를 가정한다.
- Solar Pro 3 호출과 CUDA 연산은 사용하지 않는다.
- public report에는 query id, label, metric만 남긴다.
- private dev 70개 기준 통과이며 production routing 품질 주장은 아니다.

정량 결과:

| metric | value |
| --- | ---: |
| query_count | 70 |
| accuracy | 0.957143 |
| macro_f1 | 0.956818 |
| route_policy_accuracy | 0.971429 |
| fallback_count | 0 |
| public_raw_text_leakage_count | 0 |

근거 문서:

- `docs/QUERY_TYPE_CLASSIFIER_PLAN.md`
- `evals/reports/query_type_classifier_eval_report.md`

## Data Mart 설계

`fact_query_type_router_decision`의 grain은 `router_decision_id + query_type + route_policy_id + candidate_id + metric_family + claim_boundary`다.

| field | 설명 |
| --- | --- |
| `router_decision_id` | stable router decision id |
| `query_type` | overview, place_fact, place_story, relationship 등 |
| `route_policy_id` | route policy stable id |
| `candidate_id` | retrieval, packing, generation, abstain policy 후보 |
| `metric_family` | retrieval, citation, generation, latency, safety, cost |
| `metric_value` | public-safe aggregate metric |
| `decision` | keep_default, adopt_route_candidate, reject_route, keep_dev_only |
| `claim_boundary` | dev-only, dev-input-only, live-dev-subset, locked-readiness-only |
| `evidence_artifact` | public-safe report path |

금지 필드:

- raw query
- raw answer
- raw evidence
- prompt
- chunk text
- private file path
- secret

## 다음 작업 지시서

| id | depends_on | scope | acceptance_tests | risk_level | rollback_plan |
| --- | --- | --- | --- | --- | --- |
| HD-CLASSIFIER-004 | HD-ROUTER-003 | classifier 오분류 3개 failure analysis | route impact tag, public-safe report, raw query 0 | Medium | report/module 변경 revert |
| HD-API-ROUTER-001 | HD-CLASSIFIER-004 | `/chat` classifier/router dry-run 연결 | contract test, leakage 0, retrieval regression 0 | Medium | API field 제거 |
| HD-CLASSIFIER-005 | HD-CLASSIFIER-004 | relationship false hybrid route guard 설계 | route-risk 재평가, active route 미적용, public report | Medium | guard module revert |
| HD-HYDE-001 | HD-ROUTER-003 | HyDE overview/relationship subset 비교 | Solar call budget, hallucination guard, public report | High | HyDE candidate 미채택 |

## 외부 감사 결론

확인된 주요 문제는 없다.

남은 리스크:

- route policy는 dev/input-only 근거가 중심이다.
- relationship hybrid route는 generation 품질까지 검증한 결론이 아니다.
- place_story guarded boost는 locked readiness에서 treatment가 없어 production route로 부적합하다.
- query type classifier는 baseline만 구현됐으므로 실제 API routing 완성으로 표현하면 안 된다.
