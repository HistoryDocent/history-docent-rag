# Solar Pro 3 Guarded Boost Router Threshold 판단

## 결론

`place_story_guarded_boost_v1`의 router threshold는 현재 그대로 유지한다.

단, 이 결정은 production 기본값 채택이 아니다. 현재 근거는 private `place_story` dev 10개와 HD-SOLAR-016 live paired metric row, HD-SOLAR-019 hard-case validation 결과다. locked test 통과, bootstrap confidence interval, 전체 서비스 성능 개선 주장은 아직 금지한다.

## 담당 관점 회의 결과

| 담당 관점 | 판단 |
| --- | --- |
| RAG 아키텍처 | threshold를 완화하지 않는다. manual review 2건은 recall gain이 있어도 evidence order regression이 커서 자동 채택하면 위험하다. |
| Retrieval | 현재 router는 candidate 1건만 통과시켰고 route mismatch가 0이다. threshold를 강화하면 유일한 direct gain을 잃을 가능성이 있다. |
| Generation | live 결과에서 Correct-with-Evidence, citation precision, unsupported claim이 하락하지 않았지만, changed input은 1건뿐이다. production 채택 근거로는 부족하다. |
| Evaluation | 현재 threshold는 dev hard-case gate를 통과했다. 다음 gate는 threshold 변경이 아니라 locked test 전 의사결정과 claim boundary 고정이다. |
| Data warehouse | threshold decision fact는 `decision_id + router_policy_id + validation_id + metric_family` grain으로 기록한다. |
| Security | raw query, raw answer, raw evidence, prompt, chunk text, private path, secret은 public artifact에 기록하지 않는다. |
| Portfolio | “threshold를 무리하게 튜닝하지 않고 보수적으로 유지했다”는 판단 과정이 강점이다. |
| 외부 감사 | threshold 유지 판단은 타당하다. 다만 sample size와 changed input 수가 작아 production 채택은 보류해야 한다. |

## 사용 근거

HD-SOLAR-019 hard-case validation 결과:

| metric | value |
| --- | ---: |
| query_count | 10 |
| bucket_coverage_count | 10 |
| hard_case_bucket_count | 6 |
| selected_candidate_count | 1 |
| guardrail_block_count | 9 |
| manual_review_count | 2 |
| doc_guardrail_count | 1 |
| precision_guardrail_count | 2 |
| no_candidate_gain_control_count | 3 |
| candidate_live_call_required_count | 1 |
| route_decision_mismatch_count | 0 |
| selected_candidate_safety_passed | True |
| manual_review_block_passed | True |
| doc_guardrail_block_passed | True |
| citation_recoverability_min | 1.000000 |
| solar_call_count | 0 |
| validation_decision | `keep_guarded_router_for_next_runner` |

HD-SOLAR-016 live paired comparison 결과:

| metric | baseline | guarded candidate | delta |
| --- | ---: | ---: | ---: |
| Correct-with-Evidence | 0.900000 | 0.900000 | 0.000000 |
| citation_precision | 0.580000 | 0.580000 | 0.000000 |
| citation_recall | 0.481309 | 0.509881 | 0.028572 |
| unsupported_claim_rate | 0.100000 | 0.100000 | 0.000000 |
| latency_p95_ms | 5066.690100 | 5455.679600 | 388.989500 |

## Threshold 선택지

| 선택지 | 판단 | 이유 |
| --- | --- | --- |
| threshold 완화 | 기각 | `manual_review_required` 2건은 input recall gain이 있지만 evidence order delta가 `-0.666667`이다. 자동 채택하면 citation 선택과 답변 근거성이 흔들릴 수 있다. |
| threshold 강화 | 기각 | 현재 유일한 `candidate_direct_gain` 1건에서 live citation recall gain `+0.285715`가 확인됐다. 더 강화하면 이 이득을 잃을 수 있다. |
| threshold 유지 | 채택 | route mismatch 0, selected candidate safety pass, manual review block pass, doc guardrail block pass를 만족한다. |

## 유지할 Router 규칙

유지:

- `use_candidate_direct_gain`만 자동 candidate 선택으로 둔다.
- `manual_review_required`는 자동 선택하지 않는다.
- `use_baseline_correctness_guardrail`은 baseline 유지한다.
- `use_baseline_doc_guardrail`은 baseline 유지한다.
- `use_baseline_precision_guardrail`은 baseline 유지한다.
- `use_baseline_no_candidate_gain`은 baseline 유지한다.

변경하지 않는 threshold:

| threshold | 현재 판단 |
| --- | --- |
| candidate direct evidence gain 필요 | 유지 |
| doc coverage loss 차단 | 유지 |
| correctness proxy regression 차단 | 유지 |
| precision regression without recall gain 차단 | 유지 |
| evidence order hard drop 차단 | 유지 |
| duplicate parent over limit 차단 | 유지 |

## 정량 Gate

이 판단은 다음 gate를 만족했기 때문에 통과한다.

| gate | 기준 | 결과 |
| --- | --- | --- |
| route coverage | 10/10 query bucket 매핑 | PASS |
| route stability | route decision mismatch 0 | PASS |
| selected candidate safety | Correct, precision, unsupported 악화 없음 | PASS |
| manual review block | manual review 2건 자동 선택 0 | PASS |
| doc guardrail block | doc guardrail 1건 자동 선택 0 | PASS |
| citation recoverability | min >= 0.990000 | PASS |
| live call boundary | 추가 Solar call 0 | PASS |
| public safety | raw/private/secret leakage 0 | PASS |

## 정성 Gate

| tag | count | 판단 |
| --- | ---: | --- |
| `safe_direct_gain` | 1 | 현재 threshold가 보존해야 할 이득 |
| `manual_review_kept_blocked` | 2 | threshold 완화 금지 근거 |
| `blocked_correctness_risk` | 1 | correctness guardrail 유지 근거 |
| `blocked_doc_loss` | 1 | doc guardrail 유지 근거 |
| `blocked_precision_or_order_risk` | 2 | precision/order guardrail 유지 근거 |
| `control_no_gain` | 3 | baseline 유지 control |

## Data Mart 설계

`fact_guarded_boost_threshold_decision`의 grain은 `decision_id + router_policy_id + validation_id + metric_family`다.

| field | 설명 |
| --- | --- |
| `decision_id` | threshold 판단 id |
| `router_policy_id` | `place_story_guarded_boost_v1` |
| `validation_id` | hard-case validation run id |
| `metric_family` | safety, recall, latency, public_boundary 등 |
| `decision` | keep, relax, tighten 중 하나 |
| `decision_reason_tag` | public-safe 판단 tag |
| `baseline_value` | 비교 기준 값 |
| `candidate_value` | 후보 값 |
| `delta_value` | 차이 |
| `claim_boundary` | dev-only, locked-test-needed 등 |

dimension 후보:

- `dim_router_policy`
- `dim_validation_run`
- `dim_metric_family`
- `dim_decision_status`
- `dim_eval_split`

free-text query, raw answer, raw evidence, prompt, chunk text는 fact에 저장하지 않는다.

## 포트폴리오 메시지

쓸 수 있는 표현:

- `place_story` hard-case에서 retrieval boost의 이득과 부작용을 분리했다.
- router threshold를 완화하지 않고, 안전 gate를 통과한 1건만 자동 선택하도록 유지했다.
- dev hard-case validation에서 route mismatch 0, manual review 자동 선택 0, 추가 Solar call 0을 확인했다.
- public report에는 raw text와 private path를 남기지 않았다.

쓰면 안 되는 표현:

- 최종 RAG 성능을 개선했다.
- production 기본 retrieval 정책으로 채택했다.
- locked test에서 성능을 입증했다.
- 통계적으로 유의미한 개선을 검증했다.
- 청킹이 최적인 것으로 확정했다.

## 다음 작업 지시서

| id | depends_on | scope | acceptance_tests | risk_level | rollback_plan |
| --- | --- | --- | --- | --- | --- |
| HD-SOLAR-021 | HD-SOLAR-020 | guarded boost locked test 실행 전 승인 계획 작성 | locked test 사용 조건, call budget, stop condition, claim boundary 문서화 | Medium | 문서 revert |
| HD-SOLAR-022 | HD-SOLAR-021 승인 | locked test 또는 expanded dev 검증 실행 여부 결정 | 추가 Solar call 전 명시 승인, public-safe report, leakage 0 | High | candidate 미채택, report revert |

## Non-goal

- 이번 단계에서 청킹 ablation을 다시 실행하지 않는다.
- 이번 단계에서 Solar Pro 3를 추가 호출하지 않는다.
- 이번 단계에서 router threshold를 수정하지 않는다.
- 이번 단계에서 locked test split을 사용하지 않는다.
- 이번 단계에서 production 기본값으로 채택하지 않는다.

## 외부 감사 결론

| 감사 항목 | 결과 |
| --- | --- |
| 변수 통제 | PASS. HD-SOLAR-019 결과를 기준으로 판단했다. |
| threshold 판단 | PASS. 완화/강화/유지 선택지를 비교했다. |
| public boundary | PASS. raw/private/secret 공개 금지 조건을 유지했다. |
| 비용 통제 | PASS. 추가 Solar Pro 3 호출 0회다. |
| 결과 해석 | PASS with caution. dev-only 판단임을 명시했다. |
| production claim | PASS. production 채택을 보류했다. |

## 결정

`place_story_guarded_boost_v1` threshold는 유지한다.

다음 작업은 locked test 실행이 아니라 HD-SOLAR-021에서 locked test 또는 expanded dev 검증을 위한 승인 계획을 작성하는 것이다.

## HD-SOLAR-021 계획 결과

[Solar Pro 3 Guarded Boost Locked Test Approval Plan](SOLAR_GUARDED_BOOST_LOCKED_TEST_APPROVAL_PLAN.md)에 locked test 실행 전 승인 조건을 고정했다.

결정:

- locked test를 즉시 실행하지 않는다.
- 다음 작업은 Solar Pro 3 호출 0회의 readiness dry-run runner 구현이다.
- future live paired comparison은 `place_story` locked subset으로 제한한다.
- live 실행은 별도 명시 승인 후에만 허용한다.
- production 기본값 채택은 계속 보류한다.
