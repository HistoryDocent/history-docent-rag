# Locked Retrieval Execution Approval

## 결론

`HD-LOCKED-RETRIEVAL-003`의 결론은 locked retrieval paired comparison을 아직 실행하지 않고, 실행 승인 조건을 먼저 고정하는 것이다.

`HD-LOCKED-RETRIEVAL-002` readiness는 통과했다. 다만 locked split은 최종 확인용이므로 metric 실행 전 후보, metric, stop condition, bootstrap 기준, CUDA 사용 조건, public/private 경계를 한 번 더 잠근다.

이 문서는 public-safe 승인 문서다. raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 기록하지 않는다.

후속 상태: `HD-LOCKED-RETRIEVAL-004`에서 locked retrieval paired comparison은 실행 완료됐다. 이 문서의 실행 0회 수치는 `HD-LOCKED-RETRIEVAL-003` 승인 시점 기록이다.

## 현재 승인 상태

| 항목 | 값 |
| --- | --- |
| work_id | `HD-LOCKED-RETRIEVAL-003` |
| depends_on | `HD-LOCKED-RETRIEVAL-002` |
| approval_decision | `ready_for_user_execution_approval` |
| locked_execution_approved | false |
| retrieval_execution_count | 0 |
| locked_metric_result_count | 0 |
| solar_call_count | 0 |
| cuda_required_for_future_run | true |
| readiness_report | `evals/reports/locked_retrieval_readiness_report.md` |

## 담당 관점 회의 결과

| 담당 관점 | 판단 |
| --- | --- |
| RAG 아키텍처 | locked 실행 전 후보를 2개로 제한한다. 새 retrieval 후보, 새 청킹, 새 prompt는 금지한다. |
| Retrieval | 기본 후보는 `dense_multilingual_e5_small_voice_rewrite`, relationship 후보는 `relationship_hybrid_weighted_e5_v1`만 허용한다. |
| Evaluation | paired comparison, bootstrap 10000회, 95% CI, query type breakdown, no-answer guard를 실행 전 조건으로 둔다. |
| Generation | 이번 gate는 retrieval 비교 승인이다. Solar Pro 3 generation 비교는 포함하지 않는다. |
| Data warehouse | future fact grain은 `run_id + query_id + candidate_id + metric_name`이다. public summary는 aggregate만 허용한다. |
| Security | public artifact에는 count, metric, candidate id, decision tag만 남긴다. 원문 계열 payload는 금지한다. |
| Portfolio | “locked 결과를 바로 튜닝에 쓰지 않도록 승인 gate를 분리했다”를 핵심 메시지로 둔다. |
| 외부 감사 | readiness 통과 후에도 즉시 실행하지 않고 실행 승인서를 두는 흐름은 test split 오염 방지에 타당하다. |

## 실행 후보

| candidate_id | scope | status | locked 실행 조건 |
| --- | --- | --- | --- |
| `dense_multilingual_e5_small_voice_rewrite` | answerable all | baseline_allowed | CUDA 사용 가능 시 CUDA, answerable 30개 대상 |
| `relationship_hybrid_weighted_e5_v1` | relationship only | candidate_allowed | relationship 5개 subset에서만 baseline과 paired 비교 |
| `hyde_larger_live_candidate` | not allowed | rejected | 실행 금지 |
| `graphrag_lite_entity_path_v1` | not allowed | rejected | 실행 금지 |
| `raptor_lite_summary_node_v1` | not allowed | rejected | 실행 금지 |
| `place_story_guarded_boost_v1` | not allowed | rejected | 실행 금지 |

## 정량 승인 기준

| metric | required_value |
| --- | ---: |
| planned_locked_query_count | 35 |
| planned_query_type_count | 7 |
| planned_candidate_count | 2 |
| rejected_candidate_count | 4 |
| planned_generation_candidate_count | 0 |
| planned_solar_call_count | 0 |
| planned_bootstrap_iteration_count | 10000 |
| confidence_interval_percent | 95 |
| retrieval_execution_count | 0 |
| locked_metric_result_count | 0 |
| target_resolvability_fail_count | 0 |
| no_answer_candidate_route_count | 0 |
| false_hybrid_route_count | 0 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |
| forbidden_result_field_count | 0 |

## Metric Plan

실행 승인 후 `HD-LOCKED-RETRIEVAL-004`에서만 다음 metric을 계산한다.

| metric_family | metric | 비교 방식 |
| --- | --- | --- |
| retrieval_quality | `Recall@1`, `Recall@3`, `Recall@5` | paired query set |
| retrieval_quality | `MRR`, `nDCG@5` | paired query set |
| safety | no-answer candidate route count | 반드시 0 |
| routing | false hybrid route count | 반드시 0 |
| latency | `latency_p50_ms`, `latency_p95_ms` | baseline 대비 delta |
| significance | bootstrap CI | 10000회, 95% CI |
| public_safety | leakage counts | 모두 0 |

## 개선 주장 조건

최종 개선 주장은 다음을 모두 만족해야 한다.

1. 같은 locked query set에서 baseline과 candidate를 paired 비교한다.
2. primary metric은 실행 전 `Recall@5`, `MRR`, `nDCG@5` 중 하나로 지정한다.
3. bootstrap 10000회와 95% confidence interval을 계산한다.
4. primary metric 개선이 있어도 latency p95 악화와 no-answer safety를 같이 보고한다.
5. `Correct-with-Evidence`, citation 품질, production 품질 개선은 이 retrieval run만으로 주장하지 않는다.
6. locked 결과를 보고 chunking, prompt, query rewrite, threshold를 수정하지 않는다.

## Stop Condition

다음 중 하나라도 발생하면 실행 결과를 최종 개선 주장에 쓰지 않는다.

- target resolvability failure 발생
- no-answer query가 retrieval candidate route로 이동
- relationship 이외 query가 hybrid route로 이동
- 실행 중 후보, threshold, chunking, prompt 변경 필요성이 발견됨
- public artifact에 원문 계열 payload, private path, secret-like 값 포함
- CUDA 사용 가능 환경에서 CPU fallback이 발생하고 latency 해석이 불가능함
- candidate latency가 baseline 대비 p95 50ms 이상 악화되고 품질 개선이 불명확함

## Data Mart 설계

실제 locked run의 fact grain은 `run_id + query_id + candidate_id + metric_name`이다.

| table | grain | 설명 |
| --- | --- | --- |
| `fact_locked_retrieval_eval` | `run_id + query_id + candidate_id + metric_name` | private metric 결과 |
| `dim_locked_eval_run` | `run_id` | run config, device, claim boundary |
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
- `confidence_interval_low`
- `confidence_interval_high`
- `decision_tag`
- `claim_boundary`

## 작업 명령 지시서

| id | depends_on | scope | acceptance_tests | risk_level | rollback_plan |
| --- | --- | --- | --- | --- | --- |
| `HD-LOCKED-RETRIEVAL-003` | `HD-LOCKED-RETRIEVAL-002` | locked retrieval paired comparison 실행 승인 계획 문서화 | approval doc/report/test 존재, retrieval execution 0, Solar call 0, bootstrap/CI 기준, leakage 0 | High | 문서/리포트/test 변경 revert |
| `HD-LOCKED-RETRIEVAL-004` | `HD-LOCKED-RETRIEVAL-003` | locked retrieval paired comparison runner 실행 | 별도 사용자 승인 후 실행 | High | private result 폐기, public summary revert |

## Claim Boundary

허용 표현:

- locked retrieval paired comparison 실행 승인 조건을 문서화했다.
- readiness는 통과했지만 locked metric은 아직 실행하지 않았다.
- future locked run은 CUDA 사용 가능 시 CUDA로 실행한다.
- locked 결과는 튜닝이 아니라 최종 확인에만 사용한다.

금지 표현:

- locked test에서 retrieval 성능 개선을 입증했다.
- relationship route가 production에 적용됐다.
- active routing이 기본 활성화됐다.
- GraphRAG, RAPTOR, HyDE가 locked에서 개선됐다.
- Solar Pro 3 답변 품질이 locked에서 개선됐다.
- production 성능 검증이 완료됐다.

## 외부 감사 결론

확인된 주요 문제는 없다.

남은 리스크:

- locked metric은 아직 실행하지 않았다.
- 실행 후 결과를 보고 후보를 바꾸면 test split 오염이다.
- retrieval metric이 좋아도 generation 품질 개선을 자동으로 의미하지 않는다.
- active route default enable은 locked retrieval 결과만으로 결정하면 안 된다.
