# Solar Pro 3 Guarded Boost Locked Readiness Next Gate 판단

## 결론

`place_story_guarded_boost_v1`은 production 기본값으로 채택하지 않는다.

locked `place_story` readiness dry-run은 gate를 통과했지만, candidate가 자동 선택된 query가 0건이다. 따라서 locked live paired comparison을 실행해도 baseline과 candidate의 실제 차이를 검증할 수 없다.

다음 단계는 청킹 비교 재개가 아니라, `guarded_boost` 실험선을 dev-only 근거로 보관하고 Solar Pro 3 generation v2 prompt repair 계획으로 돌아가는 것이다.

## 담당 관점 회의 결과

| 담당 관점 | 판단 |
| --- | --- |
| RAG 아키텍처 | router가 locked set에서 candidate를 0건 선택했으므로 production routing 후보로는 근거가 부족하다. |
| Retrieval | target resolvability와 citation recoverability는 정상이다. 청킹 재개 조건은 충족하지 않는다. |
| Generation | candidate live call이 0건이라 Solar Pro 3 live paired comparison을 실행해도 generation 품질 차이를 볼 수 없다. |
| Evaluation | locked test 결과를 보고 threshold를 완화하면 test split을 튜닝에 사용하게 된다. threshold 재튜닝은 금지한다. |
| Data warehouse | next gate decision fact는 `decision_id + split + query_type + router_policy_id + metric_family` grain으로 기록한다. |
| Security | public artifact에는 raw query, raw answer, raw evidence, prompt, chunk text, private path, secret을 기록하지 않는다. |
| Portfolio | 강점은 candidate를 억지로 채택하지 않고, locked gate에서 부정적 결과를 정직하게 해석한 점이다. |
| 외부 감사 | locked live 보류와 production 채택 보류는 타당하다. |

## 사용 근거

HD-SOLAR-022 locked readiness dry-run 결과:

| metric | value |
| --- | ---: |
| locked_place_story_query_count | 5 |
| route_decision_computed_count | 5 |
| selected_candidate_count | 0 |
| guardrail_block_count | 5 |
| manual_review_count | 0 |
| baseline_live_call_count | 5 |
| candidate_live_call_count | 0 |
| expected_total_live_call_count | 5 |
| live_call_hard_cap | 20 |
| reused_candidate_count | 5 |
| changed_candidate_input_count | 0 |
| citation_recoverability_min | 1.000000 |
| target_resolvability_fail_count | 0 |
| missing_child_target_count | 0 |
| missing_parent_target_count | 0 |
| missing_doc_target_count | 0 |
| solar_call_count | 0 |
| readiness_decision | `ready_without_candidate_live_call` |

Route decision 분포:

| route_decision | count |
| --- | ---: |
| `use_baseline_no_candidate_gain` | 4 |
| `use_baseline_precision_guardrail` | 1 |

## 선택지 판단

| 선택지 | 판단 | 이유 |
| --- | --- | --- |
| locked live paired comparison 실행 | 기각 | candidate live call 대상이 0건이라 paired treatment가 없다. |
| router threshold 완화 | 기각 | locked test 결과를 기준으로 threshold를 조정하면 test split 오염이다. |
| production 기본값 채택 | 기각 | locked set에서 candidate 적용 폭이 0건이라 운영 가치가 입증되지 않았다. |
| 청킹 비교 재개 | 기각 | target resolvability fail 0, citation recoverability 1.000000이라 청킹 구조 실패 신호가 없다. |
| dev-only 실험 결과로 보관 | 채택 | dev hard-case에서는 안전한 1건 이득이 있었지만 locked set 일반화 근거는 부족하다. |
| generation v2 prompt repair 계획으로 복귀 | 채택 | place_story retrieval repair 실험선이 stop gate에 도달했으므로 generation 실패 원인으로 돌아간다. |

## Next Gate Decision

| 항목 | 결정 |
| --- | --- |
| locked live paired comparison | 보류 |
| 추가 Solar Pro 3 호출 | 보류 |
| router threshold 수정 | 금지 |
| production 기본값 채택 | 기각 |
| 청킹 비교 재개 | 보류 |
| guarded boost 실험선 | dev-only limited generalization으로 보관 |
| 다음 작업 | Solar Pro 3 generation v2 prompt repair 계획 작성 |

## 정량 Gate

이 판단은 다음 gate를 기준으로 한다.

| gate | 기준 | 결과 |
| --- | --- | --- |
| locked scope | `place_story` locked subset 5건 | PASS |
| route computation | query 수와 route decision 수 일치 | PASS |
| treatment availability | candidate live call 대상 > 0 | FAIL |
| target resolvability | fail count 0 | PASS |
| citation recoverability | min >= 0.990000 | PASS |
| call budget | expected calls <= 20 | PASS |
| Solar call boundary | 이번 판단에서 추가 call 0 | PASS |
| public safety | raw/private/secret leakage 0 | PASS |

해석:

- readiness 자체는 통과했다.
- 그러나 treatment availability gate가 실패했기 때문에 live paired comparison으로 넘어가지 않는다.
- 이 실패는 시스템 오류가 아니라, router가 locked set에서 candidate를 선택하지 않았다는 실험 결과다.

## 정성 Gate

| tag | count | 판단 |
| --- | ---: | --- |
| `baseline_retained_by_no_candidate_gain` | 4 | candidate 이득이 없어 baseline 유지 |
| `baseline_retained_by_precision_guardrail` | 1 | precision guardrail 때문에 baseline 유지 |
| `candidate_generalization_not_observed` | 1 | dev 이득이 locked set으로 일반화되지 않음 |
| `locked_live_not_useful` | 1 | candidate treatment가 없어 live 비교 보류 |
| `chunking_restart_not_supported` | 1 | 청킹 재개 근거 없음 |

## Data Mart 설계

`fact_guarded_boost_next_gate_decision`의 grain은 `decision_id + split + query_type + router_policy_id + metric_family`다.

| field | 설명 |
| --- | --- |
| `decision_id` | next gate 판단 id |
| `source_readiness_id` | HD-SOLAR-022 readiness id |
| `split` | `test` |
| `query_type` | `place_story` |
| `router_policy_id` | `place_story_guarded_boost_v1` |
| `metric_family` | treatment_availability, target_resolvability, cost, safety, claim_boundary 등 |
| `decision` | stop_live, keep_dev_only, reject_production_default 등 |
| `metric_value` | public-safe aggregate value |
| `decision_reason_tag` | sanitized reason tag |
| `claim_boundary` | dev-only, locked-readiness-only, no-production-claim 등 |

dimension 후보:

- `dim_next_gate_decision`
- `dim_eval_split`
- `dim_query_type`
- `dim_router_policy`
- `dim_metric_family`
- `dim_claim_boundary`

free-text query, raw answer, raw evidence, prompt, chunk text는 fact에 저장하지 않는다.

## 포트폴리오 메시지

쓸 수 있는 표현:

- dev에서 확인한 retrieval repair 후보를 locked readiness에서 검증했고, candidate 적용 폭이 0건임을 확인했다.
- locked test 결과를 근거로 threshold를 튜닝하지 않고, test split 오염을 방지했다.
- Solar Pro 3 live 호출 없이 locked live 실행 가치가 없음을 사전에 판별했다.
- target resolvability와 citation recoverability가 정상이라 청킹 재실험으로 돌아가지 않았다.
- 부정적 실험 결과를 production 채택 보류 판단으로 연결했다.

쓰면 안 되는 표현:

- locked test에서 성능을 개선했다.
- guarded boost가 production에서 효과적이다.
- 통계적으로 유의미한 개선을 확인했다.
- 청킹이 최적인 것으로 최종 확정했다.
- Solar Pro 3 generation 품질이 개선됐다.

## 다음 작업 지시서

| id | depends_on | scope | acceptance_tests | risk_level | rollback_plan |
| --- | --- | --- | --- | --- | --- |
| HD-SOLAR-024 | HD-SOLAR-023 | Solar Pro 3 generation v2 prompt repair 계획 작성 | v2 실패 원인, prompt repair 후보, no-live-call plan, 정량/정성 gate, public leakage 0 | Medium | 문서 revert |

## Non-goal

- 이번 단계에서 청킹 ablation을 다시 실행하지 않는다.
- 이번 단계에서 Solar Pro 3를 호출하지 않는다.
- 이번 단계에서 locked live paired comparison을 실행하지 않는다.
- 이번 단계에서 router threshold를 수정하지 않는다.
- 이번 단계에서 production 기본값으로 채택하지 않는다.

## 외부 감사 결론

| 감사 항목 | 결과 |
| --- | --- |
| 결과 해석 | PASS. candidate 0건을 개선 근거로 과장하지 않았다. |
| locked test 보호 | PASS. locked 결과를 threshold 튜닝에 사용하지 않는다. |
| 비용 통제 | PASS. 추가 Solar Pro 3 호출 0회다. |
| 청킹 재개 판단 | PASS. 청킹 실패 신호가 없다. |
| public boundary | PASS. raw/private/secret 공개 금지 조건을 유지했다. |
| production claim | PASS. production 채택을 기각했다. |

## 결정

HD-SOLAR-023은 문서 gate로 통과한다.

`place_story_guarded_boost_v1`은 dev-only limited generalization 사례로 보관한다. locked live paired comparison과 production 기본값 채택은 보류/기각하고, 다음 작업은 Solar Pro 3 generation v2 prompt repair 계획 작성이다.
