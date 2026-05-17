# Locked Retrieval Validation Plan

## 결론

`HD-LOCKED-RETRIEVAL-001`의 결론은 locked test를 지금 실행하지 않는 것이다.

이번 단계는 locked retrieval 검증을 실행하기 전 승인 조건, 후보, metric, stop condition, public/private 경계, data mart grain을 고정하는 계획이다. locked split은 최종 확인용이므로 이 결과를 보고 threshold, router, prompt, chunking을 다시 튜닝하지 않는다.

이 문서는 public-safe 계획 문서다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

## 현재 상태

| 항목 | 값 |
| --- | --- |
| work_id | `HD-LOCKED-RETRIEVAL-001` |
| depends_on | `HD-API-ROUTER-005` |
| locked_test_execution_count | 0 |
| solar_call_count | 0 |
| planned_locked_query_count | 35 |
| planned_query_type_count | 7 |
| planned_retrieval_candidate_count | 2 |
| planned_generation_candidate_count | 0 |
| cuda_required_for_future_run | true |
| current_decision | `ready_for_locked_retrieval_approval_review` |

## 담당 관점 회의 결과

| 담당 관점 | 판단 |
| --- | --- |
| RAG 아키텍처 | locked test는 최종 검증용이다. active route default enable 전에는 retrieval 후보만 제한해 평가한다. |
| Retrieval | 기본 후보는 `dense_multilingual_e5_small_voice_rewrite`, relationship 후보는 `relationship_hybrid_weighted_e5_v1`만 허용한다. |
| Evaluation | dev에서 기각한 HyDE, GraphRAG-lite, RAPTOR-lite, place_story boost를 locked에서 재선정하면 split contamination이다. |
| Generation | 이번 locked gate는 retrieval 검증이다. Solar Pro 3 generation live 비교는 포함하지 않는다. |
| Data warehouse | 실제 실행 시 grain은 `run_id + query_id + candidate_id + metric_name`으로 둔다. public mart에는 query text를 넣지 않는다. |
| Security | locked payload, raw answer, evidence text, private artifact path는 public 산출물에서 금지한다. |
| Portfolio | locked test를 실행하지 않았다는 사실 자체가 중요한 통제다. 실행 전 gate를 문서화한 점을 강조한다. |
| 외부 감사 | 지금 바로 locked metric을 실행하면 결과 기반 튜닝 유혹이 생긴다. 먼저 승인 조건을 고정하는 결정은 타당하다. |

## Locked Test 사용 원칙

허용:

- 최종 후보 1회성 확인
- query type별 aggregate metric
- paired comparison
- confidence interval 기반 claim 검토
- latency/cost 악화 기록

금지:

- locked 결과를 보고 threshold 수정
- locked 결과를 보고 chunking 재설계
- locked 결과를 보고 prompt 수정
- locked 결과를 보고 query rewrite rule 추가
- raw query, raw evidence, raw answer 공개
- production 성능 검증 완료 주장

## 평가 후보

| candidate_id | 역할 | locked 실행 여부 | 판단 |
| --- | --- | --- | --- |
| `dense_multilingual_e5_small_voice_rewrite` | 현재 기본 retrieval 후보 | 승인 후 실행 가능 | baseline |
| `relationship_hybrid_weighted_e5_v1` | relationship 전용 route 후보 | 승인 후 relationship subset에서만 실행 가능 | candidate |
| `hyde_larger_live_candidate` | HyDE route | 실행 금지 | dev 40에서 MRR/nDCG/latency 악화 |
| `graphrag_lite_entity_path_v1` | GraphRAG-lite | 실행 금지 | dev input-only 개선 없음 |
| `raptor_lite_summary_node_v1` | RAPTOR-lite | 실행 금지 | dev input-only 개선 없음 |
| `place_story_guarded_boost_v1` | place_story boost | 실행 금지 | locked readiness에서 candidate 선택 0 |

## 통과 기준

### Retrieval Gate

| metric | 기준 |
| --- | --- |
| `locked_query_count` | 35 |
| `query_type_breakdown_count` | 7 |
| `target_resolvability_fail_count` | 0 |
| `no_answer_candidate_route_count` | 0 |
| `false_hybrid_route_count` | 0 |
| `Recall@5` | baseline 대비 하락 없음 또는 하락 사유 명시 |
| `MRR` | baseline 대비 하락 없음 또는 하락 사유 명시 |
| `nDCG@5` | baseline 대비 하락 없음 또는 하락 사유 명시 |
| `latency_p95_ms` | 50ms 미만 증가 또는 악화 사유 명시 |
| `citation_recoverability` | 0.990000 이상 |

### 개선 주장 Gate

최종 개선 주장은 다음 조건을 모두 만족할 때만 허용한다.

| 조건 | 기준 |
| --- | --- |
| paired comparison | 같은 locked query set에서 baseline/candidate 비교 |
| bootstrap | 10,000회 |
| confidence interval | 95% CI |
| primary metric | `Recall@5`, `MRR`, `nDCG@5` 중 사전 지정 |
| safety metric | no-answer 후보 route 0 |
| latency/cost | 악화 시 명시 |
| public-safe gate | leakage 0 |

## Stop Condition

다음 중 하나라도 발생하면 locked 실행을 중단하고 결과를 최종 성능 주장에 쓰지 않는다.

- target resolvability failure 발생
- no-answer query가 retrieval candidate route로 이동
- relationship 이외 query가 hybrid route로 이동
- public artifact에 raw text 계열 필드 포함
- secret 또는 private path 의심 문자열 포함
- candidate latency가 baseline 대비 p95 50ms 이상 악화되고 품질 개선이 불명확
- 실행 중 후보 변경 필요성이 발견됨

## Data Mart 설계

실제 locked run을 실행할 때 fact grain은 `run_id + query_id + candidate_id + metric_name`이다.

| table | grain | 설명 |
| --- | --- | --- |
| `fact_locked_retrieval_eval` | `run_id + query_id + candidate_id + metric_name` | candidate별 metric 결과 |
| `dim_locked_eval_run` | `run_id` | run config, model/device, claim boundary |
| `dim_retrieval_candidate` | `candidate_id` | retrieval method, route policy, feature flag |
| `dim_query_type` | `query_type` | 7개 query type |
| `fact_locked_public_summary` | `run_id + candidate_id + query_type + metric_name` | public-safe aggregate |

public summary 허용 필드:

- `run_id`
- `candidate_id`
- `query_type`
- `metric_name`
- `metric_value`
- `delta_value`
- `latency_p95_ms`
- `decision_tag`
- `claim_boundary`

금지 필드:

- raw query
- raw answer
- raw evidence
- prompt
- chunk text
- private file path
- secret

## 작업 명령 지시서

| id | depends_on | scope | acceptance_tests | risk_level | rollback_plan |
| --- | --- | --- | --- | --- | --- |
| `HD-LOCKED-RETRIEVAL-001` | `HD-API-ROUTER-005` | locked retrieval 검증 승인 계획 문서화 | plan/report/test 존재, locked 실행 0, Solar call 0, leakage 0 | High | 문서/리포트/test 변경 revert |
| `HD-LOCKED-RETRIEVAL-002` | `HD-LOCKED-RETRIEVAL-001` | locked retrieval readiness dry-run runner | private locked target resolvability, expected route/candidate count, CUDA device 확인, execution 0 | High | runner/report revert |
| `HD-LOCKED-RETRIEVAL-003` | `HD-LOCKED-RETRIEVAL-002` | locked retrieval paired comparison 실행 여부 승인 | live/locked 실행 승인서, stop condition 재확인 | High | 실행 전 문서 revert |
| `HD-LOCKED-RETRIEVAL-004` | `HD-LOCKED-RETRIEVAL-003` | locked retrieval paired comparison runner 실행 | 별도 승인 후 paired metric, bootstrap, public-safe summary | High | private result 폐기, public summary revert |

## Claim Boundary

허용 표현:

- locked retrieval 검증 승인 계획을 수립했다.
- locked split은 아직 실행하지 않았다.
- locked split 결과를 튜닝에 사용하지 않도록 stop condition을 고정했다.
- locked retrieval readiness에서 target resolvability와 route/candidate count를 실행 없이 검증했다.
- locked retrieval paired comparison 실행 승인 조건을 문서화했다.
- future locked run은 CUDA 사용 가능 시 CUDA로 실행한다.

금지 표현:

- locked test에서 retrieval 성능 개선을 입증했다.
- relationship route가 production에 적용됐다.
- active routing이 기본 활성화됐다.
- HyDE, GraphRAG-lite, RAPTOR-lite가 locked에서 개선됐다.
- Solar Pro 3 답변 품질이 locked에서 개선됐다.

## 외부 감사 결론

확인된 주요 문제는 없다.

남은 리스크:

- locked test는 아직 실행하지 않았다.
- 향후 locked 결과를 보고 후보를 수정하면 test split 오염이 된다.
- retrieval metric이 좋아도 generation 품질 개선을 자동으로 의미하지 않는다.
- active route default enable은 별도 승인 전까지 금지해야 한다.
