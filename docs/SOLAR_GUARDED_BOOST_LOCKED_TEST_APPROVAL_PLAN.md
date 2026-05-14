# Solar Pro 3 Guarded Boost Locked Test 승인 계획

## 결론

아직 locked test를 실행하지 않는다.

`place_story_guarded_boost_v1`은 dev-only next gate 후보로 유지한다. 다음 단계는 locked test를 바로 소모하는 것이 아니라, locked test 실행 전 승인 조건, call budget, 중단 조건, 결과 해석 경계를 고정하는 것이다.

현재 추천 순서는 다음이다.

1. `locked_test_readiness_dry_run`: locked test query id와 target grain만 사용해 실행 가능성, call budget, public-safe output gate를 확인한다. Solar Pro 3 호출은 0회다.
2. `locked_test_live_paired_comparison`: 별도 명시 승인 후에만 실행한다. 범위는 `place_story` locked subset으로 제한한다.
3. `production_default_decision`: locked test, generation metric, 비용, latency, public-safe gate를 통과한 뒤 별도 문서에서 판단한다.

## 담당 관점 회의 결과

| 담당 관점 | 판단 |
| --- | --- |
| RAG 아키텍처 | locked test는 최종 검증 자산이므로 실행 전 dry-run gate가 필요하다. |
| Retrieval | 현재 후보는 `place_story` 전용 router다. locked test도 전체 query type이 아니라 `place_story` subset부터 제한해야 한다. |
| Generation | live Solar Pro 3 비교는 baseline과 candidate의 동일 query paired comparison으로만 허용한다. |
| Evaluation | dev 결과를 근거로 locked test 개선 주장을 하면 안 된다. locked test 실행 전 approval artifact가 필요하다. |
| Data warehouse | approval plan과 live eval fact grain을 분리한다. 승인 문서에는 raw text를 저장하지 않는다. |
| Security | raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 public artifact에 기록하지 않는다. |
| Portfolio | 강점은 “최종 검증셋을 아끼고 승인 gate를 둔 실험 운영”이다. 성능 과장보다 평가 설계가 더 설득력 있다. |
| 외부 감사 | locked test 실행 자체보다 실행 조건 문서화가 먼저인 판단은 타당하다. |

## 현재 근거

사용 가능한 근거:

| source | 역할 |
| --- | --- |
| HD-SOLAR-016 live paired comparison | private dev `place_story` 10개에서 baseline/candidate live metric 비교 |
| HD-SOLAR-019 hard-case validation | route decision, bucket coverage, selected candidate safety 확인 |
| HD-SOLAR-020 router threshold decision | threshold 유지, 완화/강화 기각 판단 |

핵심 정량 근거:

| metric | value |
| --- | ---: |
| dev_place_story_query_count | 10 |
| selected_candidate_count | 1 |
| guardrail_block_count | 9 |
| manual_review_count | 2 |
| route_decision_mismatch_count | 0 |
| live_correct_with_evidence_delta | 0.000000 |
| live_citation_precision_delta | 0.000000 |
| live_citation_recall_delta | 0.028572 |
| live_unsupported_claim_delta | 0.000000 |
| citation_recoverability_min | 1.000000 |

해석:

- 현재 후보는 dev-only next gate 후보로는 충분하다.
- locked test 실행은 가능하지만, 즉시 실행하면 test split 소모 리스크가 있다.
- locked test는 `place_story` router 검증에만 사용하고, 전체 RAG 성능 개선 주장은 별도 final ablation에서만 허용한다.

## 실행 모드

| mode | 목적 | Solar call | locked test 사용 | 기본 판단 |
| --- | --- | ---: | --- | --- |
| `approval_plan_only` | 승인 조건 문서화 | 0 | 0 | 이번 단계 |
| `locked_test_readiness_dry_run` | query id, split, route 가능성, call budget 검증 | 0 | 제한적 metadata만 사용 | 다음 추천 작업 |
| `locked_test_live_paired_comparison` | baseline vs guarded candidate live generation 비교 | 명시 승인 후 제한 | `place_story` subset만 사용 | 후순위 |
| `production_default_decision` | 기본 정책 채택 여부 판단 | 추가 승인 필요 | locked 결과 포함 | 최종 판단 단계 |

## Locked Test 사용 조건

locked test는 다음 조건을 모두 만족할 때만 사용한다.

| condition | 기준 |
| --- | --- |
| scope lock | `query_type=place_story` subset으로 제한 |
| strategy lock | baseline은 `dense_multilingual_e5_small_voice_rewrite + P0_rank_order`, candidate는 `place_story_guarded_boost_v1` |
| router lock | HD-SOLAR-020 threshold 그대로 사용 |
| prompt lock | answer contract와 prompt policy를 실행 전 고정 |
| approval lock | live Solar Pro 3 호출 전 별도 승인 필요 |
| output lock | public report는 aggregate metric과 sanitized tag만 허용 |
| no tuning lock | locked test 결과를 본 뒤 threshold를 재튜닝하지 않음 |

## Call Budget

기본 방침:

- 이번 HD-SOLAR-021 문서 작업의 `planned_solar_call_count`는 0이다.
- 다음 dry-run 작업의 `planned_solar_call_count`도 0이다.
- live paired comparison은 별도 승인 없이는 실행하지 않는다.

future live 실행 hard cap:

| budget item | limit |
| --- | ---: |
| `expected_total_live_call_count` | <= 20 |
| `baseline_live_call_count` | `locked_place_story_query_count` 이하 |
| `candidate_live_call_count` | router가 candidate를 선택한 query 수 이하 |
| `no_answer_live_call_count` | 0 |
| `unexpected_retry_count` | 0 |

`expected_total_live_call_count > 20`이면 실행하지 않고 계획을 다시 작성한다.

## Stop Condition

다음 중 하나라도 발생하면 locked test live 실행을 중단한다.

| stop condition | 조치 |
| --- | --- |
| 명시 승인 없음 | live 실행 금지 |
| `UPSTAGE_API_KEY` 없음 | live 실행 금지 |
| expected live call hard cap 초과 | 실행 금지, 계획 재작성 |
| locked split schema mismatch | 실행 금지, test manifest 점검 |
| target resolvability 실패 | 실행 금지, target mapping 점검 |
| prompt 또는 answer contract 변경 미고정 | 실행 금지 |
| raw output public write 가능성 | 실행 금지 |
| private path leakage count > 0 | report 폐기 |
| secret-like leakage count > 0 | report 폐기 및 key rotation 대상 |
| candidate selected count = 0 | live candidate 비교 보류, input-only report만 남김 |
| unsupported claim regression 확인 | candidate 채택 보류 |
| citation precision regression 확인 | candidate 채택 보류 |

## 정량 Gate

### Readiness dry-run gate

| metric | pass 기준 |
| --- | ---: |
| locked_place_story_query_count | > 0 |
| route_decision_computed_count | query count와 동일 |
| selected_candidate_count | 기록 필수 |
| expected_total_live_call_count | <= 20 |
| citation_recoverability_min | >= 0.990000 |
| target_resolvability_fail_count | 0 |
| solar_call_count | 0 |
| public_raw_text_leakage_count | 0 |
| private_path_leakage_count | 0 |
| secret_like_leakage_count | 0 |

### Future live paired gate

| metric | pass 기준 |
| --- | --- |
| `Correct-with-Evidence` | baseline보다 하락하지 않음 |
| `citation_precision` | baseline보다 하락하지 않음 |
| `citation_recall` | baseline 이상 |
| `unsupported_claim_rate` | baseline보다 증가하지 않음 |
| `place_relevance` | baseline보다 하락하지 않음 |
| `latency_p95_ms` | 증가분과 원인 설명 필수 |
| `solar_call_count` | approved budget 이하 |
| `public leakage` | raw/private/secret 모두 0 |

## 정성 Gate

public report에는 다음 tag만 허용한다.

| tag | 의미 |
| --- | --- |
| `safe_direct_gain` | candidate가 직접 근거를 보강하고 safety metric 하락이 없음 |
| `baseline_retained_by_guardrail` | guardrail 때문에 baseline 유지 |
| `manual_review_required` | 자동 채택 금지, human review 후보 |
| `no_candidate_gain_control` | candidate 이득 없음 |
| `live_call_not_approved` | live 실행 승인 없음 |
| `live_call_budget_blocked` | call budget 초과로 중단 |
| `locked_test_claim_limited` | locked test 결과라도 전체 production claim은 아님 |

## Data Mart 설계

approval plan fact와 live eval fact를 분리한다.

| fact | grain | 목적 |
| --- | --- | --- |
| `fact_guarded_boost_locked_test_approval` | `approval_plan_id + split + query_type + execution_mode + approval_gate_id` | 실행 전 승인 조건과 중단 조건 기록 |
| `fact_guarded_boost_locked_readiness` | `run_id + query_id + router_policy_id + execution_mode` | dry-run route decision, call budget, leakage gate 기록 |
| `fact_guarded_boost_locked_live_eval` | `run_id + query_id + strategy_id + router_policy_id + answer_policy_id` | future live paired metric 기록 |

dimension 후보:

- `dim_approval_plan`
- `dim_eval_split`
- `dim_query_type`
- `dim_execution_mode`
- `dim_router_policy`
- `dim_answer_policy`
- `dim_public_safety_gate`

free-text query, raw answer, raw evidence, prompt, chunk text, private path, secret은 warehouse fact에 저장하지 않는다.

## Claim Boundary

쓸 수 있는 표현:

- dev `place_story` 결과를 바탕으로 locked test 실행 전 approval gate를 설계했다.
- locked test를 바로 소모하지 않고 dry-run gate와 call budget을 분리했다.
- live Solar Pro 3 호출은 별도 승인 전까지 0회로 제한했다.
- public report에는 raw text, private path, secret을 남기지 않도록 gate를 고정했다.

쓰면 안 되는 표현:

- locked test에서 성능을 입증했다.
- 최종 RAG 성능이 개선됐다.
- production 기본값으로 채택했다.
- 통계적으로 유의미한 개선을 확인했다.
- GraphRAG, RAPTOR-lite보다 우수하다고 검증했다.

## 다음 작업 지시서

| id | depends_on | scope | acceptance_tests | risk_level | rollback_plan |
| --- | --- | --- | --- | --- | --- |
| HD-SOLAR-022 | HD-SOLAR-021 | guarded boost locked test readiness dry-run runner 구현 | Solar call 0, expected live call count <= 20, target resolvability fail 0, public leakage 0, pytest 통과 | Medium | runner/report revert |
| HD-SOLAR-023 | HD-SOLAR-022 + 별도 승인 | guarded boost locked `place_story` live paired comparison 실행 | approved call budget 이하, paired metric report, raw/private/secret leakage 0, claim boundary 기록 | High | candidate 미채택, live report 폐기 |

## Non-goal

- 이번 단계에서 locked test를 실행하지 않는다.
- 이번 단계에서 Solar Pro 3를 호출하지 않는다.
- 이번 단계에서 router threshold를 수정하지 않는다.
- 이번 단계에서 prompt를 수정하지 않는다.
- 이번 단계에서 청킹 ablation을 재개하지 않는다.
- 이번 단계에서 production 기본값으로 채택하지 않는다.

## 외부 감사 결론

| 감사 항목 | 결과 |
| --- | --- |
| locked test 보호 | PASS. live 실행 전 dry-run gate를 둔다. |
| 비용 통제 | PASS. 이번 단계와 다음 dry-run은 Solar call 0이다. |
| 변수 통제 | PASS. router threshold와 strategy를 고정한다. |
| public boundary | PASS. raw/private/secret 공개 금지 조건을 유지한다. |
| claim boundary | PASS. locked test 전후 claim을 분리했다. |
| production claim | PASS. production 채택을 명시적으로 보류했다. |

## 결정

HD-SOLAR-021은 문서 gate로 통과한다.

다음 추천 작업은 HD-SOLAR-022 `guarded boost locked test readiness dry-run runner` 구현이다. 이 runner는 locked test live 실행이 아니라, Solar Pro 3 호출 0회로 실행 가능성, call budget, public-safe gate만 확인한다.
